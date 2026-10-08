#!/usr/bin/env python3
"""Run QEMU-based ISA semantic tests for dadao-m1.

Usage:
  python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml
  python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --case 1
  python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --dump
  python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ --batch

Exit code protocol (ADR-0004 D5; SYS_EXIT per ADR-0020 D8):
  0x00       = PASS
  0x01-0x7F  = FAIL (test-defined, reported via semihosting SYS_EXIT)
  0x80-0xFF  = Machine fault (0x87=unmapped, 0x88=ILLI, 0x89=UNDI, etc.)
"""

import argparse
import concurrent.futures
import json
import os
import socket
import subprocess
import sys
import time
import uuid
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# D6/D7/D9 compliance: resolve the install-root toolchain bin via paths.py (the
# single source of truth for install dirs).  The default QEMU binary is taken
# from the install root (ADR-0016 D9) — the install path is never hardcoded (D7).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "tools", "infra"))
import paths as _paths

# Default QEMU binary path: install root (ADR-0016 D9), resolved via paths.py.
DEFAULT_QEMU = str(_paths.host_toolchain_bin() / "qemu-system-dadao")

# Default timeout (seconds) - ADR-0004 D3: 9s harness timeout
DEFAULT_TIMEOUT = 9

# Exit code ranges
EXIT_PASS = 0x00
EXIT_FAIL_MIN = 0x01
EXIT_FAIL_MAX = 0x7F
EXIT_FAULT_MIN = 0x80
EXIT_FAULT_MAX = 0xFF

# Fault code names (ADR-0004 D5.8)
FAULT_NAMES = {
    0x87: "UNMAPPED",
    0x88: "ILLI",
    0x89: "UNDI",
    0x8A: "RASOF",
    0x8B: "RASUF",
    0x8C: "MALIGN",
    0x8D: "IALIGN",
}

# State-dump region (ADR-0009 D7, single source of truth in build_test_binary.py)
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)
from build_test_binary import DUMP_BASE, DUMP_SIZE


def _resolve_artifact_dir(subdir: str = "harness") -> str:
    """Return absolute path to test artifacts subdirectory, creating it if needed."""
    d = str(_paths.test_artifacts_dir() / subdir)
    os.makedirs(d, exist_ok=True)
    return d


def find_qemu():
    """Find QEMU binary."""
    # Check environment variable
    qemu = os.environ.get("QEMU_SYSTEM_DADAO")
    if qemu and os.path.isfile(qemu):
        return qemu

    # Check the install-root default (ADR-0016 D9; absolute, resolved via paths.py)
    if os.path.isfile(DEFAULT_QEMU):
        return DEFAULT_QEMU

    # Try PATH
    import shutil
    qemu = shutil.which("qemu-system-dadao")
    if qemu:
        return qemu

    return None


class QMPClient:
    """QEMU Machine Protocol (QMP) client for memory dump."""

    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.sock = None

    def connect(self, timeout=10):
        """Connect to QMP socket and negotiate capabilities."""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)

        # Wait for socket to become available
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.sock.connect(self.socket_path)
                break
            except (ConnectionRefusedError, FileNotFoundError):
                time.sleep(0.1)
        else:
            raise ConnectionError(f"Failed to connect to QMP socket {self.socket_path}")

        # Read QMP greeting
        greeting = self._recv_json()
        if "QMP" not in greeting:
            raise ValueError(f"Unexpected QMP greeting: {greeting}")

        # Send qmp_capabilities
        self._send_json({"execute": "qmp_capabilities"})
        response = self._recv_response()
        if "return" not in response:
            raise ValueError(f"qmp_capabilities failed: {response}")

        return True

    def pmemsave(self, addr, size, filename):
        """Save guest memory to file via pmemsave command.

        Note: filename must be quoted because HMP's size:i uses expression
        parser which treats unquoted leading '/' as division operator.
        """
        cmd = f'pmemsave {addr} {size} "{filename}"'
        self._send_json({
            "execute": "human-monitor-command",
            "arguments": {"command-line": cmd}
        })
        response = self._recv_response()
        ret_str = response["return"]
        # HMP may return error text in "return" field (e.g. "invalid char...")
        if ret_str and "invalid" in ret_str.lower():
            raise ValueError(f"pmemsave HMP error: {ret_str}")
        return ret_str

    def cont(self):
        """Resume guest execution (after -S freeze).

        QMP sends a RESUME event before the return value.
        """
        self._send_json({"execute": "cont"})
        # May receive event(s) before the actual return
        for _ in range(10):
            response = self._recv_json()
            if "return" in response:
                return True
            # Skip async events (e.g. RESUME)
            if "event" in response:
                continue
        raise ValueError(f"cont: no return received (last: {response})")

    def quit(self):
        """Send quit command to QEMU."""
        try:
            self._send_json({"execute": "quit"})
            # QEMU may close socket immediately, ignore errors
            try:
                self._recv_response()
            except Exception:
                pass
        except Exception:
            pass

    def _send_json(self, obj):
        """Send JSON object to QMP socket."""
        data = json.dumps(obj) + "\n"
        self.sock.sendall(data.encode("utf-8"))

    def _recv_response(self):
        """Receive a QMP response, skipping async events.

        Returns the first message with 'return' or 'error' key.
        """
        for _ in range(20):
            msg = self._recv_json()
            if "return" in msg or "error" in msg:
                return msg
            # Skip async events (RESUME, RESET, etc.)
        raise ConnectionError(f"No QMP response after 20 messages (last: {msg})")

    def _recv_json(self):
        """Receive JSON object from QMP socket."""
        data = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
            # Try to parse complete JSON
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                continue
        if data:
            return json.loads(data.decode("utf-8"))
        raise ConnectionError("No data received from QMP socket")

    def close(self):
        """Close QMP socket."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


# Cache of parsed vector YAML: (abspath, mtime_ns, size) -> case list.
# build_binary() is invoked once per case; without this cache the entire
# vector file is re-parsed for every case (O(cases) redundant, GIL-bound
# work that otherwise dominates runtime and defeats parallelism).
_VECTOR_CACHE = {}


def _load_cases(vector_file):
    """Return the parsed case list for a vector YAML file (memoized).

    The vectors are read-only during a run, so the parsed result is cached
    keyed by path + mtime + size. Returning the cached list is safe because
    build_test_binary() deep-copies any case it mutates.
    """
    abspath = os.path.abspath(vector_file)
    st = os.stat(abspath)
    key = (abspath, st.st_mtime_ns, st.st_size)
    cases = _VECTOR_CACHE.get(key)
    if cases is None:
        with open(abspath, "r") as f:
            cases = yaml.safe_load(f)
        # Plain assignment (dict ops are atomic under the GIL). Do NOT clear
        # the cache here: clearing on every miss causes thrashing when
        # multiple worker threads race on different files.
        _VECTOR_CACHE[key] = cases
    return cases


def build_binary(vector_file, case_idx, dump_mode=False):
    """Build test binary for a vector case.

    Returns (binary_path, case_dict) or raises on error.
    """
    # Import build function
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from build_test_binary import build_test_binary as build_blob

    cases = _load_cases(vector_file)

    if not isinstance(cases, list):
        raise ValueError(f"Vector file {vector_file} does not contain a list")

    if case_idx is not None:
        if case_idx >= len(cases):
            raise ValueError(f"Case index {case_idx} out of range (0-{len(cases)-1})")
        case = cases[case_idx]
    else:
        # Find first semantic/encoding/boundary case
        case = None
        for c in cases:
            if c.get("class") in ("semantic", "encoding", "boundary"):
                case = c
                break
        if case is None:
            raise ValueError(f"No semantic/encoding/boundary case found in {vector_file}")

    blob = build_blob(case, trusted_instrs=None, dump_mode=dump_mode)

    # Write to file in D6-compliant artifact directory (no tempfile)
    artifact_dir = _resolve_artifact_dir("harness")
    bin_path = os.path.join(artifact_dir, f"dadao-test-{uuid.uuid4().hex[:8]}.bin")
    with open(bin_path, "wb") as f:
        f.write(blob)

    return bin_path, case


def run_qemu(qemu_bin, trampoline_path, test_bin_path, timeout=DEFAULT_TIMEOUT, dump_mode=False):
    """Run QEMU with the test binary.

    Returns (exit_code, stderr_output, timed_out, dump_file).
    dump_file is path to state dump if dump_mode succeeded, else None.

    Uses Popen (not subprocess.run) so that on timeout, QEMU stays alive
    long enough for QMP dump + quit before being killed.
    """
    cmd = [
        qemu_bin,
        "-machine", "dadao-m1",
        "-nographic",
        "-bios", trampoline_path,
        "-kernel", test_bin_path,
        # SYS_EXIT status reaches the host $? only when semihosting is enabled
        # (ADR-0020 D8; the harness explicitly enables 'native', ADR-0020 D7).
        "-semihosting-config", "enable=on,target=native",
    ]

    dump_file = None
    dump_error = None
    qmp_socket = None

    if dump_mode:
        # Use Unix socket for QMP (more reliable than TCP)
        # D6 compliance: socket in test artifacts directory
        artifact_dir = _resolve_artifact_dir("harness")
        qmp_socket = os.path.join(artifact_dir, f"dadao-qmp-{uuid.uuid4().hex[:8]}.sock")
        cmd.extend(["-qmp", f"unix:{qmp_socket},server=on,wait=off"])
        # Freeze CPU at start; harness will connect via QMP and send cont
        cmd.append("-S")

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # In dump mode with -S, connect to QMP and resume guest immediately
        if dump_mode and qmp_socket:
            try:
                _qmp_connect_and_cont(qmp_socket, timeout=10)
            except Exception as e:
                print(f"  WARNING: QMP connect+cont failed: {e}", file=sys.stderr)
                # QEMU may have already exited; continue to proc.wait

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # QEMU still alive — attempt QMP dump before killing
            if dump_mode and qmp_socket:
                try:
                    dump_file = _attempt_qmp_dump(qmp_socket, timeout=5)
                except Exception as e:
                    dump_error = str(e)
            # Now kill QEMU
            proc.kill()
            proc.wait()
            return -1, "", True, dump_file

        # QEMU exited on its own
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""

        # In dump mode, attempt QMP dump even on normal exit (guest may have
        # entered spin before fault, or exited normally with dump data available)
        if dump_mode and qmp_socket:
            if proc.returncode == 0:
                # Guest exited cleanly — might have been spinning; try dump
                try:
                    dump_file = _attempt_qmp_dump(qmp_socket, timeout=5)
                except Exception as e:
                    dump_error = str(e)

        if dump_error:
            print(f"  WARNING: QMP dump error: {dump_error}", file=sys.stderr)

        return proc.returncode, stderr, False, dump_file

    finally:
        # Ensure QEMU is dead
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait()
        # Clean up QMP socket
        if qmp_socket and os.path.exists(qmp_socket):
            try:
                os.unlink(qmp_socket)
            except OSError:
                pass


def _attempt_qmp_dump(qmp_socket, timeout=5):
    """Attempt to connect to QMP and dump state.

    Returns path to dump file on success.
    Raises on failure (connection error, pmemsave error, file size mismatch).
    """
    qmp = QMPClient(qmp_socket)
    try:
        qmp.connect(timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"QMP connect failed: {e}") from e

    # Create dump file in D6-compliant artifact directory
    dump_dir = os.path.join(_resolve_artifact_dir("harness"), "dumps")
    os.makedirs(dump_dir, exist_ok=True)
    dump_file = os.path.join(dump_dir, "state.bin")

    try:
        qmp.pmemsave(DUMP_BASE, DUMP_SIZE, dump_file)
    except Exception as e:
        qmp.quit()
        qmp.close()
        raise RuntimeError(f"QMP pmemsave failed: {e}") from e

    qmp.quit()
    qmp.close()

    if not os.path.exists(dump_file):
        raise RuntimeError(f"QMP dump file not created: {dump_file}")

    actual_size = os.path.getsize(dump_file)
    if actual_size != DUMP_SIZE:
        raise RuntimeError(f"QMP dump file size mismatch: expected {DUMP_SIZE}, got {actual_size}")

    return dump_file


def _qmp_connect_and_cont(qmp_socket, timeout=10):
    """Connect to QMP, negotiate capabilities, and send cont to resume guest.

    Used in dump mode where QEMU is started with -S (frozen CPU).
    """
    qmp = QMPClient(qmp_socket)
    qmp.connect(timeout=timeout)
    qmp.cont()
    qmp.close()


def interpret_exit_code(exit_code, expected_fault=None, dump_mode=False):
    """Interpret QEMU exit code.

    Returns (status, description).
    """
    if exit_code == -1:
        if dump_mode:
            return "INCONCLUSIVE", "Timeout (guest may be spinning in dump mode)"
        return "INCONCLUSIVE", "Timeout (harness error)"

    if exit_code == EXIT_PASS:
        if expected_fault:
            return "FAIL", f"Expected fault {expected_fault} but got PASS"
        return "PASS", "Test passed"

    if EXIT_FAIL_MIN <= exit_code <= EXIT_FAULT_MAX:
        if expected_fault:
            fault_name = FAULT_NAMES.get(exit_code, f"UNKNOWN(0x{exit_code:02X})")
            if exit_code >= EXIT_FAULT_MIN:
                # Machine fault
                if fault_name == expected_fault:
                    return "PASS", f"Expected {expected_fault}, got {fault_name}"
                else:
                    return "FAIL", f"Expected {expected_fault}, got {fault_name}"
            else:
                # Guest fail code
                return "FAIL", f"Expected fault {expected_fault}, got FAIL(0x{exit_code:02X})"
        else:
            if exit_code >= EXIT_FAULT_MIN:
                fault_name = FAULT_NAMES.get(exit_code, f"UNKNOWN(0x{exit_code:02X})")
                return "FAIL", f"Unexpected fault: {fault_name} (0x{exit_code:02X})"
            else:
                return "FAIL", f"Test failed with code 0x{exit_code:02X}"

    return "FAIL", f"Unknown exit code: 0x{exit_code:02X}"


def run_single_test(qemu_bin, trampoline_path, vector_file, case_idx=None,
                    timeout=DEFAULT_TIMEOUT, dump_mode=False, verbose=False):
    """Run a single test case.

    Returns (status, description, case_dict, dump_file).
    """
    # Build binary
    try:
        bin_path, case = build_binary(vector_file, case_idx, dump_mode)
    except Exception as e:
        return "ERROR", str(e), None, None

    try:
        # Run QEMU
        exit_code, stderr, timed_out, dump_file = run_qemu(
            qemu_bin, trampoline_path, bin_path, timeout, dump_mode
        )

        # Interpret result
        expected_fault = case.get("expected_fault")
        status, desc = interpret_exit_code(exit_code, expected_fault, dump_mode)

        if timed_out:
            status = "INCONCLUSIVE"

        if verbose:
            case_class = case.get("class", "?")
            insn = case.get("id", "?")
            mnemonic = case.get("mnemonic", "?")
            print(f"  Case: {case_class} {mnemonic} ({insn})")
            print(f"  Exit code: 0x{exit_code:02X}" if exit_code >= 0 else f"  Exit code: TIMEOUT")
            print(f"  Status: {status} - {desc}")
            if stderr and status != "PASS":
                print(f"  Stderr: {stderr[:500]}")
            if dump_file:
                print(f"  Dump file: {dump_file}")

        return status, desc, case, dump_file

    finally:
        # Clean up temp file
        try:
            os.unlink(bin_path)
        except OSError:
            pass


def run_batch(qemu_bin, trampoline_path, vector_dir, timeout=DEFAULT_TIMEOUT,
              dump_mode=False, verbose=False, jobs=1):
    """Run all vector files in a directory.

    Cases are executed serially when ``jobs <= 1``. With ``jobs > 1`` the
    runnable cases are dispatched to a ``ThreadPoolExecutor``: once the
    parsed-vector cache above removes the otherwise GIL-bound re-parse, the
    per-case work is dominated by the QEMU subprocess wait (during which the
    GIL is released), so threads parallelize effectively.

    Result aggregation is always deterministic and ordered by
    ``(file order, case order)`` — identical to the serial run — so the
    summary counts and ``fail_details`` are independent of ``jobs``.

    Returns (total, passed, failed, deferred, errors, fail_details).
    """
    total = 0
    deferred = 0

    vector_files = sorted([
        os.path.join(vector_dir, f)
        for f in os.listdir(vector_dir)
        if f.endswith(".yaml")
    ])

    # Ordered plan: ("deferred"|"run", vector_file, fname, case_idx, case).
    # Preserves (file order, case order) so results can be aggregated in
    # deterministic order regardless of completion order.
    plan = []
    for vf in vector_files:
        fname = os.path.basename(vf)
        cases = _load_cases(vf)

        if not isinstance(cases, list):
            print(f"  SKIP {fname}: not a list")
            continue

        for i, case in enumerate(cases):
            total += 1
            if case.get("status", "active") == "deferred":
                deferred += 1
                plan.append(("deferred", vf, fname, i, case))
            else:
                plan.append(("run", vf, fname, i, case))

    # Execute runnable cases (parallel when jobs > 1).
    workers = max(1, jobs)
    if dump_mode and workers > 1:
        # Batch dump mode writes diagnostics to a fixed shared path
        # (<artifact_dir>/harness/dumps/state.bin), which parallel workers
        # would clobber. Fall back to serial to keep dumps correct.
        print("  NOTE: dump mode is not parallel-safe; forcing serial execution",
              file=sys.stderr)
        workers = 1
    run_items = [p for p in plan if p[0] == "run"]
    results = {}
    if run_items:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    run_single_test,
                    qemu_bin, trampoline_path, vf, i, timeout, dump_mode, False,
                )
                for (_, vf, _fname, i, _case) in run_items
            ]
            for idx, future in enumerate(futures):
                results[idx] = future.result()

    # Aggregate in plan order (deterministic).
    passed = 0
    failed = 0
    errors = 0
    fail_details = []
    run_cursor = 0
    for kind, vf, fname, i, case in plan:
        if kind == "deferred":
            if verbose:
                print(f"  DEFERRED {fname}[{i}]: {case.get('mnemonic', '?')}")
            continue

        status, desc, _, _dump_file = results[run_cursor]
        run_cursor += 1

        if verbose:
            # Ordered per-case status line (deterministic; enables
            # machine-readable --jobs equivalence diffs).
            print(f"  {status} {fname}[{i}]")

        if status == "PASS":
            passed += 1
        elif status in ("FAIL", "ERROR"):
            failed += 1
            fail_details.append(f"  FAIL {fname}[{i}]: {desc}")
        elif status == "INCONCLUSIVE":
            errors += 1
            fail_details.append(f"  INCONCLUSIVE {fname}[{i}]: {desc}")
        else:
            failed += 1
            fail_details.append(f"  {status} {fname}[{i}]: {desc}")

    return total, passed, failed, deferred, errors, fail_details


def main():
    parser = argparse.ArgumentParser(description="Run QEMU-based ISA semantic tests")
    parser.add_argument("target", help="Vector YAML file or directory")
    parser.add_argument("--case", type=int, default=None,
                        help="Case index (0-based) for single file mode")
    parser.add_argument("--batch", action="store_true",
                        help="Run all vector files in directory")
    parser.add_argument("--dump", action="store_true",
                        help="Dump mode: spin after dumper, use QMP for state dump")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"QEMU timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--qemu", default=None,
                        help="Path to qemu-system-dadao binary")
    parser.add_argument("--trampoline", default=None,
                        help="Path to trampoline.bin")
    parser.add_argument("--jobs", type=int, default=None,
                        help="Parallel worker count for batch mode "
                             "(default: $JOBS or 1)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    # Parallelism: explicit --jobs wins; else $JOBS; else 1 (serial semantics).
    jobs = args.jobs
    if jobs is None:
        env_jobs = os.environ.get("JOBS")
        if env_jobs:
            try:
                jobs = int(env_jobs)
            except ValueError:
                print(f"Error: invalid JOBS value {env_jobs!r}", file=sys.stderr)
                sys.exit(2)
        else:
            jobs = 1
    if jobs < 1:
        print(f"Error: --jobs must be >= 1 (got {jobs})", file=sys.stderr)
        sys.exit(2)

    # Find QEMU binary
    qemu_bin = args.qemu or find_qemu()
    if not qemu_bin:
        print("Error: qemu-system-dadao not found. Set QEMU_SYSTEM_DADAO or --qemu", file=sys.stderr)
        sys.exit(1)

    # Find trampoline
    if args.trampoline:
        trampoline_path = args.trampoline
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        trampoline_path = os.path.join(script_dir, "trampoline.bin")

    if not os.path.isfile(trampoline_path):
        print(f"Error: trampoline.bin not found at {trampoline_path}", file=sys.stderr)
        print("Run: python3 tests/scripts/gen_trampoline.py", file=sys.stderr)
        sys.exit(1)

    if args.batch or os.path.isdir(args.target):
        # Batch mode
        vector_dir = args.target
        if not os.path.isdir(vector_dir):
            print(f"Error: {vector_dir} is not a directory", file=sys.stderr)
            sys.exit(1)

        print(f"Running batch tests from {vector_dir}...")
        total, passed, failed, deferred, errors, fail_details = run_batch(
            qemu_bin, trampoline_path, vector_dir, args.timeout, args.dump,
            args.verbose, jobs
        )

        print(f"\nResults: {total} total, {passed} passed, {failed} failed, "
              f"{deferred} deferred, {errors} errors")

        if fail_details:
            print("\nFailed tests:")
            for detail in fail_details:
                print(detail)

        # CLI fail-closed (ADR-0009): 0 cases executed or all skipped → exit 2
        executed = total - deferred
        if executed == 0:
            print("ERROR: 0 cases executed (all deferred or no cases)")
            sys.exit(2)
        if failed > 0 or errors > 0:
            sys.exit(1)
        sys.exit(0)

    else:
        # Single file mode
        vector_file = args.target
        if not os.path.isfile(vector_file):
            print(f"Error: {vector_file} not found", file=sys.stderr)
            sys.exit(1)

        status, desc, case, dump_file = run_single_test(
            qemu_bin, trampoline_path, vector_file, args.case,
            args.timeout, args.dump, args.verbose or True
        )

        print(f"\nResult: {status}")
        if desc:
            print(f"  {desc}")
        if dump_file:
            print(f"  Dump file: {dump_file}")

        sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
