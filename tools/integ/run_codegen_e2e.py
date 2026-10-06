#!/usr/bin/env python3
"""run_codegen_e2e.py -- M3 CodeGen end-to-end gate (INTEG-012t).

Runs every program in ``tests/llvm/codegen/expected.yaml`` through the frozen M3
single-TU pipeline and compares the **guest process exit code** against the
independently-derived expected value (it does NOT rely on lit exit codes):

    llc -march=dadao <prog.ll>                 -> <prog>.s
    cat tests/scripts/codegen_crt0.s <prog>.s  -> <prog>.s   (single TU)
    llvm-mc --triple=dadao -filetype=obj       -> <prog>.o
    llvm-objcopy -O binary --only-section=.text-> <prog>.bin
    timeout N qemu-system-dadao -M dadao-m1 -bios trampoline.bin \
            -kernel <prog>.bin -display none -nographic
                                               -> process exit code == guest exit code

The startup stub calls ``@main`` and writes the returned value (rd31) to the
exit port ``0xffff_8000_0000``; the guest exit code is the low byte
(ADR-0003 D5 single TU, ADR-0004 D3 exit port).

Judgement (fail-closed):
  * guest exit code == expected          -> PASS
  * guest exit code != expected          -> FAIL (mismatch / machine fault)
  * qemu timeout / build-step non-zero   -> FAIL

Exit status:
  0  all cases PASS
  1  at least one case FAIL
  2  setup error (missing tool/vector, zero cases executed, bad options)

``--inject`` runs a built-in counter-example self-test: it takes a baseline
PASSing case, flips its expected value in memory, and requires that the gate
then reports FAIL.  This proves the comparison is live (the gate can fail).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required (used elsewhere in the repo)\n")
    sys.exit(2)

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

# Machine fault exit codes (ADR-0004 D5.8): 0x80 | spec cause bit index.
FAULT_NAMES = {
    0x87: "UNMAPPED",
    0x88: "ILLI",
    0x89: "UNDI",
    0x8A: "RASOF",
    0x8B: "RASUF",
    0x8C: "MALIGN",
    0x8D: "IALIGN",
}

DEFAULT_LLC = ".work/build/llvm/bin/llc"
DEFAULT_LLVM_MC = ".work/build/llvm/bin/llvm-mc"
DEFAULT_LLVM_OBJCOPY = ".work/build/llvm/bin/llvm-objcopy"
DEFAULT_QEMU = ".work/build/qemu/qemu-system-dadao"
DEFAULT_TRAMPOLINE = "tests/scripts/trampoline.bin"
DEFAULT_CRT0 = "tests/scripts/codegen_crt0.s"
DEFAULT_VECTORS_DIR = "tests/llvm/codegen"
DEFAULT_EXPECTED = "tests/llvm/codegen/expected.yaml"
DEFAULT_WORK_DIR = "tests/llvm/codegen-e2e"
DEFAULT_TIMEOUT = 30


class CaseResult:
    __slots__ = ("name", "category", "expected", "actual", "passed", "reason")

    def __init__(self, name, category, expected):
        self.name = name
        self.category = category
        self.expected = expected
        self.actual = None
        self.passed = False
        self.reason = ""


def _abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def _run(cmd, timeout=None):
    """Run cmd; return (rc, stdout, stderr, timed_out).

    rc is None when the command timed out.  The command's own exit code is
    captured directly (no shell pipe, so nothing can swallow it).
    """
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
            False,
        )
    except subprocess.TimeoutExpired:
        return None, "", "", True


def _require_exec(path: str, what: str) -> None:
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        sys.stderr.write(f"ERROR: {what} not found / not executable: {path}\n")
        sys.stderr.write("       run 'make build-mc' and 'make build-qemu' first\n")
        sys.exit(2)


def load_programs(expected_path: str):
    with open(expected_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("programs"), list):
        sys.stderr.write(f"ERROR: {expected_path}: missing 'programs' list\n")
        sys.exit(2)
    programs = []
    for entry in doc["programs"]:
        programs.append(
            {
                "name": entry["name"],
                "category": entry.get("category", "?"),
                "expected": int(entry["expected_exit_code"]),
            }
        )
    if not programs:
        sys.stderr.write(f"ERROR: {expected_path}: zero programs\n")
        sys.exit(2)
    return programs


def build_and_run(prog, tools, work_dir, timeout, verbose=False):
    """Build one program through the fixed pipeline and run it under QEMU.

    Returns a CaseResult (passed / reason filled in).
    """
    res = CaseResult(prog["name"], prog["category"], prog["expected"])
    name = prog["name"]
    ll_path = os.path.join(tools["vectors_dir"], name)
    if not os.path.isfile(ll_path):
        res.reason = f"source not found: {ll_path}"
        return res

    stem = os.path.splitext(name)[0]
    prog_s = os.path.join(work_dir, stem + ".prog.s")
    combined_s = os.path.join(work_dir, stem + ".s")
    obj_path = os.path.join(work_dir, stem + ".o")
    bin_path = os.path.join(work_dir, stem + ".bin")

    # 1. llc -march=dadao <prog.ll> -> <prog>.s
    rc, _out, err, timed = _run([tools["llc"], "-march=dadao", ll_path, "-o", prog_s])
    if timed or rc != 0:
        res.reason = f"llc failed (rc={rc})" + (f": {err.strip()[:200]}" if err.strip() else "")
        return res

    # 2. cat crt0.s prog.s -> combined single TU .s
    try:
        with open(tools["crt0"], "rb") as fh:
            crt0_bytes = fh.read()
        with open(prog_s, "rb") as fh:
            prog_bytes = fh.read()
        with open(combined_s, "wb") as fh:
            fh.write(crt0_bytes)
            if not crt0_bytes.endswith(b"\n"):
                fh.write(b"\n")
            fh.write(prog_bytes)
    except OSError as exc:
        res.reason = f"concat failed: {exc}"
        return res

    # 3. llvm-mc --triple=dadao -filetype=obj -> .o
    rc, _out, err, timed = _run(
        [tools["llvm_mc"], "--triple=dadao", "-filetype=obj", combined_s, "-o", obj_path]
    )
    if timed or rc != 0:
        res.reason = f"llvm-mc failed (rc={rc})" + (f": {err.strip()[:200]}" if err.strip() else "")
        return res

    # 4. llvm-objcopy -O binary --only-section=.text -> .bin
    rc, _out, err, timed = _run(
        [tools["llvm_objcopy"], "-O", "binary", "--only-section=.text", obj_path, bin_path]
    )
    if timed or rc != 0:
        res.reason = f"llvm-objcopy failed (rc={rc})" + (f": {err.strip()[:200]}" if err.strip() else "")
        return res

    # 5. timeout N qemu-system-dadao ... -> process exit code == guest exit code
    rc, _out, err, timed = _run(
        [
            tools["qemu"],
            "-M", "dadao-m1",
            "-bios", tools["trampoline"],
            "-kernel", bin_path,
            "-display", "none",
            "-nographic",
        ],
        timeout=timeout,
    )
    if timed:
        res.reason = f"qemu timeout after {timeout}s"
        return res
    res.actual = rc
    if rc is None:
        res.reason = "qemu did not return an exit code"
        return res
    # NOTE on fault detection: the comparison must be primary.  ADR-0004 D3
    # reserves 0x80..0xFF for machine faults, but the TESTCASES-026t expected
    # values include numbers in that range (e.g. 137 == 0x89 == UNDI, 236/238/
    # 246/249).  A guest exit code and a fault code are therefore not always
    # distinguishable from the raw status; we can only classify a *mismatch* as
    # a fault.  See the INTEG-012t findings for the ambiguity.
    if rc == prog["expected"]:
        res.passed = True
        res.reason = "match"
    elif rc in FAULT_NAMES:
        res.reason = f"machine fault {FAULT_NAMES[rc]} (0x{rc:02X})"
    else:
        res.reason = "exit code mismatch"
    if verbose:
        sys.stdout.write(
            f"    [steps] llc=0 llvm-mc=0 llvm-objcopy=0 qemu={rc}\n"
        )
    return res


def run_suite(programs, tools, work_dir, timeout, verbose=False):
    results = []
    for prog in programs:
        res = build_and_run(prog, tools, work_dir, timeout, verbose)
        actual = "?" if res.actual is None else str(res.actual)
        status = "PASS" if res.passed else "FAIL"
        sys.stdout.write(
            f"  {status}  {res.name}  expected={res.expected} actual={actual} "
            f"exit={actual}  ({res.reason})\n"
        )
        sys.stdout.flush()
        results.append(res)
    return results


def main():
    ap = argparse.ArgumentParser(description="M3 CodeGen end-to-end gate (INTEG-012t)")
    ap.add_argument("--llc", default=os.environ.get("LLC", DEFAULT_LLC))
    ap.add_argument("--llvm-mc", dest="llvm_mc",
                    default=os.environ.get("LLVM_MC", DEFAULT_LLVM_MC))
    ap.add_argument("--llvm-objcopy", dest="llvm_objcopy",
                    default=os.environ.get("LLVM_OBJCOPY", DEFAULT_LLVM_OBJCOPY))
    ap.add_argument("--qemu", default=os.environ.get("QEMU_SYSTEM_DADAO", DEFAULT_QEMU))
    ap.add_argument("--trampoline", default=DEFAULT_TRAMPOLINE)
    ap.add_argument("--crt0", default=DEFAULT_CRT0)
    ap.add_argument("--vectors-dir", default=DEFAULT_VECTORS_DIR)
    ap.add_argument("--expected", default=DEFAULT_EXPECTED)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--inject", action="store_true",
                    help="counter-example self-test: flip a baseline-PASSing "
                         "expected value and require the gate to FAIL")
    args = ap.parse_args()

    tools = {
        "llc": _abspath(args.llc),
        "llvm_mc": _abspath(args.llvm_mc),
        "llvm_objcopy": _abspath(args.llvm_objcopy),
        "qemu": _abspath(args.qemu),
        "trampoline": _abspath(args.trampoline),
        "crt0": _abspath(args.crt0),
        "vectors_dir": _abspath(args.vectors_dir),
    }
    expected_path = _abspath(args.expected)
    work_dir = _abspath(args.work_dir)

    _require_exec(tools["llc"], "llc")
    _require_exec(tools["llvm_mc"], "llvm-mc")
    _require_exec(tools["llvm_objcopy"], "llvm-objcopy")
    _require_exec(tools["qemu"], "qemu-system-dadao")
    if not os.path.isfile(tools["trampoline"]):
        sys.stderr.write(f"ERROR: trampoline not found: {tools['trampoline']}\n")
        sys.exit(2)
    if not os.path.isfile(tools["crt0"]):
        sys.stderr.write(f"ERROR: crt0 stub not found: {tools['crt0']}\n")
        sys.exit(2)
    if not os.path.isfile(expected_path):
        sys.stderr.write(f"ERROR: expected.yaml not found: {expected_path}\n")
        sys.exit(2)

    os.makedirs(work_dir, exist_ok=True)

    programs = load_programs(expected_path)
    sys.stdout.write(
        f"run_codegen_e2e: {len(programs)} programs, work dir {work_dir}\n"
    )
    results = run_suite(programs, tools, work_dir, args.timeout, args.verbose)

    failed = [r for r in results if not r.passed]
    sys.stdout.write(
        f"\nResults: {len(results) - len(failed)}/{len(results)} passed, "
        f"{len(failed)} failed\n"
    )

    # ---- counter-example self-test --------------------------------------
    if args.inject:
        passing = [r for r in results if r.passed]
        if not passing:
            sys.stderr.write(
                "INJECT: FAIL -- no baseline-PASSing case to inject into\n"
            )
            return 2
        target = passing[0]
        # locate the source program dict and mutate it in memory only
        prog = next(p for p in programs if p["name"] == target.name)
        original = prog["expected"]
        prog["expected"] = (original + 1) % 256
        sys.stdout.write(
            f"\nINJECT: case={target.name} expected {original} -> {prog['expected']}\n"
        )
        inject_res = build_and_run(prog, tools, work_dir, args.timeout, args.verbose)
        sys.stdout.write(
            f"  {'FAIL' if not inject_res.passed else 'PASS'}  {inject_res.name}  "
            f"expected={inject_res.expected} actual={inject_res.actual} "
            f"exit={inject_res.actual}  ({inject_res.reason})\n"
        )
        if inject_res.passed:
            sys.stderr.write(
                "INJECT: FAIL -- gate did NOT detect the wrong expected value "
                "(comparison is not live)\n"
            )
            return 1
        sys.stdout.write("INJECT: PASS -- gate correctly reported FAIL on the "
                         "wrong expected value\n")
        # In inject mode the verdict is the self-test itself, not the baseline.
        return 0

    if failed:
        sys.stdout.write("run_codegen_e2e: FAIL\n")
        return 1
    sys.stdout.write("run_codegen_e2e: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
