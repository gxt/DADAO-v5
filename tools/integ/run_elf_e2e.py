#!/usr/bin/env python3
"""run_elf_e2e.py -- M4 multi-TU / multi-section ELF end-to-end gate (INTEG-016t).

Runs every program in a codegen manifest through the M4 **ELF** pipeline and
compares the **guest process exit code** against the independently-derived
expected value (it does NOT rely on lit exit codes):

    per TU:  llc -march=dadao -filetype=obj  <tu>.ll     -> <tu>.o
    once:    llvm-mc --triple=dadao -filetype=obj \
                 tests/scripts/codegen_crt0.s            -> crt0.o
    link:    ld.lld -T tests/scripts/dadao.lds \
                 crt0.o <tu>.o ... -o <prog>.elf          (ET_EXEC)
    run:     timeout N qemu-system-dadao -M dadao-m1 \
                 -kernel <prog>.elf -display none -nographic
                                                          -> guest exit code

The crt0 `_start` calls `@main` (via an R_DADAO_REL26 relocation resolved by
ld.lld) and writes the returned value to the exit port 0xffff_8000_0000
(ADR-0004 D3); the guest exit code is the low byte.  Unlike the M3 raw-bin
pipeline (run_codegen_e2e.py) this links multiple objects with the target LLD
and loads the resulting ELF directly (contract-elf.md §6.1.2).

Manifest shape (both accepted):
  * multi-TU (m4):  {name, sources: [a.ll, b.ll, ...], expected_exit_code}
  * single-TU (M3): {name: prog.ll, expected_exit_code}

Judgement (fail-closed):
  * guest exit code == expected          -> PASS
  * guest exit code != expected          -> FAIL (mismatch / machine fault)
  * qemu timeout / any build step != 0   -> FAIL

Exit status:
  0  all cases PASS
  1  at least one case FAIL
  2  setup error (missing tool/vector, zero cases executed, bad options)

``--inject`` runs a built-in counter-example self-test: it takes a baseline
PASSing case, flips its expected value, requires the gate to report FAIL, then
restores it and re-runs the whole chain requiring green again.  This proves the
comparison is live (the gate can fail).
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

# Install root (ADR-0016 D9): resolve the host toolchain bin from the single
# source of truth (D7, tools/infra/paths.py) instead of hardcoding .work/build.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
import paths as _dadao_paths  # noqa: E402

_TOOLCHAIN_BIN = str(_dadao_paths.host_toolchain_bin())

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

DEFAULT_LLC = os.path.join(_TOOLCHAIN_BIN, "llc")
DEFAULT_LLVM_MC = os.path.join(_TOOLCHAIN_BIN, "llvm-mc")
DEFAULT_LDLLD = os.path.join(_TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(_TOOLCHAIN_BIN, "qemu-system-dadao")
DEFAULT_CRT0 = "tests/scripts/codegen_crt0.s"
DEFAULT_LDS = "tests/scripts/dadao.lds"
DEFAULT_VECTORS_DIR = "tests/llvm/codegen/m4"
DEFAULT_EXPECTED = "tests/llvm/codegen/m4/expected.yaml"
# Work dir under the SDK test-artifacts root (ADR-0016 D6), resolved through
# the single source of truth (D7, tools/infra/paths.py); never hardcoded.
DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "elf-e2e")
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
        sys.stderr.write("       run 'make install-host' first\n")
        sys.exit(2)


def load_programs(expected_path: str):
    with open(expected_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("programs"), list):
        sys.stderr.write(f"ERROR: {expected_path}: missing 'programs' list\n")
        sys.exit(2)
    programs = []
    for entry in doc["programs"]:
        name = entry["name"]
        sources = entry.get("sources")
        if not sources:
            sources = [name]
        programs.append(
            {
                "name": name,
                "category": entry.get("category", "?"),
                "expected": int(entry["expected_exit_code"]),
                "sources": list(sources),
            }
        )
    if not programs:
        sys.stderr.write(f"ERROR: {expected_path}: zero programs\n")
        sys.exit(2)
    return programs


def _ensure_crt0(tools, work_dir):
    """Assemble crt0 once into <work>/crt0.o; return (path, rc, err)."""
    crt0_o = os.path.join(work_dir, "crt0.o")
    if os.path.isfile(crt0_o):
        return crt0_o, 0, ""
    rc, _out, err, timed = _run(
        [tools["llvm_mc"], "--triple=dadao", "-filetype=obj",
         tools["crt0"], "-o", crt0_o]
    )
    if timed:
        return None, None, "llvm-mc (crt0) timeout"
    return crt0_o, rc, err


def build_and_run(prog, tools, work_dir, timeout, verbose=False):
    """Build one program through the ELF pipeline and run it under QEMU.

    Returns a CaseResult (passed / reason filled in).
    """
    res = CaseResult(prog["name"], prog["category"], prog["expected"])
    stem = os.path.splitext(os.path.basename(prog["name"]))[0]

    # 0. assemble the shared crt0 stub (once)
    crt0_o, crc, cerr = _ensure_crt0(tools, work_dir)
    if crt0_o is None or crc != 0:
        res.reason = f"llvm-mc (crt0) failed (rc={crc})" + (
            f": {cerr.strip()[:200]}" if cerr and cerr.strip() else "")
        return res

    # 1. llc -march=dadao -filetype=obj for each translation unit
    objs = []
    for src in prog["sources"]:
        src_path = os.path.join(tools["vectors_dir"], src)
        if not os.path.isfile(src_path):
            res.reason = f"source not found: {src_path}"
            return res
        obj = os.path.join(work_dir, stem + "." + os.path.splitext(src)[0] + ".o")
        rc, _out, err, timed = _run(
            [tools["llc"], "-march=dadao", "-filetype=obj", src_path, "-o", obj]
        )
        if timed or rc != 0:
            res.reason = f"llc({src}) failed (rc={rc})" + (
                f": {err.strip()[:200]}" if err.strip() else "")
            return res
        objs.append(obj)

    # 2. ld.lld -T dadao.lds crt0.o <objs> -o <prog>.elf
    elf = os.path.join(work_dir, stem + ".elf")
    rc, _out, err, timed = _run(
        [tools["ldlld"], "-T", tools["lds"], crt0_o] + objs + ["-o", elf]
    )
    if timed or rc != 0:
        res.reason = f"ld.lld failed (rc={rc})" + (
            f": {err.strip()[:200]}" if err.strip() else "")
        return res

    # 3. timeout N qemu-system-dadao -M dadao-m1 -kernel <elf> -> guest exit code
    rc, _out, err, timed = _run(
        [
            tools["qemu"],
            "-M", "dadao-m1",
            "-kernel", elf,
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
    # Fault detection (ADR-0004 D3): 0x80..0xFF are machine faults, but expected
    # values may legitimately fall in that range (see INTEG-012t), so only a
    # *mismatch* can be classified as a fault.
    if rc == prog["expected"]:
        res.passed = True
        res.reason = "match"
    elif rc in FAULT_NAMES:
        res.reason = f"machine fault {FAULT_NAMES[rc]} (0x{rc:02X})"
    else:
        res.reason = "exit code mismatch"
    if verbose:
        sys.stdout.write(
            f"    [steps] llc=0 ld.lld=0 qemu={rc} elf={elf}\n"
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
    ap = argparse.ArgumentParser(
        description="M4 multi-TU/multi-section ELF end-to-end gate (INTEG-016t)")
    ap.add_argument("--llc", default=os.environ.get("LLC", DEFAULT_LLC))
    ap.add_argument("--llvm-mc", dest="llvm_mc",
                    default=os.environ.get("LLVM_MC", DEFAULT_LLVM_MC))
    ap.add_argument("--ldlld", default=os.environ.get("LDLLD", DEFAULT_LDLLD))
    ap.add_argument("--qemu", default=os.environ.get("QEMU_SYSTEM_DADAO", DEFAULT_QEMU))
    ap.add_argument("--crt0", default=DEFAULT_CRT0)
    ap.add_argument("--lds", default=DEFAULT_LDS)
    ap.add_argument("--vectors-dir", default=DEFAULT_VECTORS_DIR)
    ap.add_argument("--expected", default=DEFAULT_EXPECTED)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--inject", action="store_true",
                    help="counter-example self-test: flip a baseline-PASSing "
                         "expected value and require the gate to FAIL, then "
                         "restore and re-run the whole chain for green")
    args = ap.parse_args()

    tools = {
        "llc": _abspath(args.llc),
        "llvm_mc": _abspath(args.llvm_mc),
        "ldlld": _abspath(args.ldlld),
        "qemu": _abspath(args.qemu),
        "crt0": _abspath(args.crt0),
        "lds": _abspath(args.lds),
        "vectors_dir": _abspath(args.vectors_dir),
    }
    expected_path = _abspath(args.expected)
    work_dir = _abspath(args.work_dir)

    _require_exec(tools["llc"], "llc")
    _require_exec(tools["llvm_mc"], "llvm-mc")
    _require_exec(tools["ldlld"], "ld.lld")
    _require_exec(tools["qemu"], "qemu-system-dadao")
    if not os.path.isfile(tools["crt0"]):
        sys.stderr.write(f"ERROR: crt0 stub not found: {tools['crt0']}\n")
        sys.exit(2)
    if not os.path.isfile(tools["lds"]):
        sys.stderr.write(f"ERROR: linker script not found: {tools['lds']}\n")
        sys.exit(2)
    if not os.path.isfile(expected_path):
        sys.stderr.write(f"ERROR: expected.yaml not found: {expected_path}\n")
        sys.exit(2)

    os.makedirs(work_dir, exist_ok=True)

    programs = load_programs(expected_path)
    sys.stdout.write(
        f"run_elf_e2e: {len(programs)} programs, work dir {work_dir}\n"
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
        # restore and re-run the whole chain
        prog["expected"] = original
        sys.stdout.write(
            f"RESTORE: case={target.name} expected back to {original}; "
            f"re-running whole chain\n"
        )
        restored = run_suite(programs, tools, work_dir, args.timeout, args.verbose)
        if any(not r.passed for r in restored):
            sys.stderr.write(
                "INJECT: FAIL -- chain did not go green after restoring the "
                "expected value\n"
            )
            return 1
        sys.stdout.write("INJECT: PASS -- gate correctly reported FAIL on the "
                         "wrong expected value and went green again after restore\n")
        # In inject mode the verdict is the self-test itself.
        return 0

    if failed:
        sys.stdout.write("run_elf_e2e: FAIL\n")
        return 1
    sys.stdout.write("run_elf_e2e: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
