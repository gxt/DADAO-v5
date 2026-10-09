#!/usr/bin/env python3
"""run_m5_e2e.py -- M5 SEE / semihosting end-to-end gate (TESTCASES-033t).

Runs every program in ``tests/llvm/codegen/m5/expected.yaml`` through the M5
flat-bin pipeline and compares the observed result against the manifest:

    llvm-mc --triple=dadao-unknown-elf -filetype=obj <prog.s> -> <prog>.o
    llvm-objcopy -O binary --only-section=.text  <prog>.o    -> <prog>.bin
    qemu-system-dadao -M dadao-m1 -bios <bootrom.bin> -kernel <prog>.bin \
        -semihosting-config enable=on,target=native,chardev=semi \
        -chardev file,id=semi,path=<console> -d cpu -D <log>
                                                             -> host exit code

The bin is loaded at the RAM@0 base 0x0000_0000_0000 by `-kernel`
(ADR-0004 D2.3 path B; single RAM segment since C1 step2); the SEE bootrom
(`-bios .dadao/tests/bootrom/bootrom.bin`, QEMU-047t) starts at the reset PC
0xffff_ffff_0000, configures the
cfx user exception vector/masks and hands off to the app in *user* mode
(Machine-01 §2).  Every vector carries a hand-derived expectation in the
manifest; the expected values come from `.tao/knowledge/contract-*.md` +
`spec/`, never from QEMU (see ``tools/testcases/validate_m5_vectors.py``).

Judgement (fail-closed), per case:

  * host exit code == ``expected_exit_code``           (else FAIL)
  * semihosting console == ``expected_console``         (when declared)
  * produced host file == ``expected_file``             (when declared)
  * bootrom effective: first ``-d cpu`` block PC == 0xffff_ffff_0000, the
    bootrom-installed cfx_umon user vector is present, and the app is observed
    running in user mode (MODE == 0) in the RAM@0 range

Exit status:
  0  all cases PASS
  1  at least one case FAIL
  2  setup error (missing tool / vector / bootrom, zero cases, bad options)

``--inject`` runs the built-in counter-example self-test: it takes a baseline
PASSing case, flips its expected exit code in memory, requires the gate to FAIL,
then restores it and re-runs the whole suite requiring green again.  This proves
the comparison is live (the gate can fail).
"""

from __future__ import annotations

import argparse
import os
import re
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

# Install root (ADR-0016 D9): resolve the host toolchain bin and the test
# artifact (bootrom) directory from the single source of truth
# (tools/infra/paths.py, ADR-0016 D7) instead of hardcoding .work/build.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
import paths as _dadao_paths  # noqa: E402

_TOOLCHAIN_BIN = str(_dadao_paths.host_toolchain_bin())
_TEST_ARTIFACTS = _dadao_paths.test_artifacts_dir()

# Machine fault exit codes (ADR-0004 D5.8): 0x80 | spec cause bit index.  Used
# only to *explain* a mismatch; the primary comparison is exact.
FAULT_NAMES = {
    0x87: "UNMAPPED",
    0x88: "ILLI",
    0x89: "UNDI",
    0x8A: "RASOF",
    0x8B: "RASUF",
    0x8C: "MALIGN",
    0x8D: "IALIGN",
}

DEFAULT_LLVM_MC = os.path.join(_TOOLCHAIN_BIN, "llvm-mc")
DEFAULT_LLVM_OBJCOPY = os.path.join(_TOOLCHAIN_BIN, "llvm-objcopy")
DEFAULT_QEMU = os.path.join(_TOOLCHAIN_BIN, "qemu-system-dadao")
# Bootrom is produced by `make build-bootrom` into the test-artifacts root
# (QEMU-047t); never hardcode the path.
DEFAULT_BOOTROM = str(_TEST_ARTIFACTS / "bootrom" / "bootrom.bin")
DEFAULT_VECTORS_DIR = "tests/llvm/codegen/m5"
DEFAULT_EXPECTED = "tests/llvm/codegen/m5/expected.yaml"
DEFAULT_WORK_DIR = str(_TEST_ARTIFACTS / "m5-e2e")
DEFAULT_TIMEOUT = 30

# Reset PC / memory map (ADR-0004 D2 / R3, DADAO-12 §2.1, C1 step2).
RESET_PC = 0xFFFF_FFFF_0000
RAM_BASE = 0x0000_0000_0000
RAM_SIZE = 16 * 1024 * 1024
# The SEE bootrom installs this cfx_umon user exception vector (Rom base + 0x200,
# `escape cfx_umon, [excp_cause_ip, 4]`); its presence proves the config ran.
BOOTROM_USER_VECTOR = "0000ffffffff0200"
USER_MODE = 0


class CaseResult:
    __slots__ = ("name", "category", "expected", "actual", "passed", "reason",
                 "expected_cause", "cmdline",
                 "console_expected", "console_actual", "console_ok")

    def __init__(self, name, category, expected):
        self.name = name
        self.category = category
        self.expected = expected
        self.actual = None
        self.passed = False
        self.reason = ""
        self.expected_cause = None
        self.cmdline = ""
        # Semihosting console capture (chardev file): expected is None when the
        # manifest declares no console expectation for this case.
        self.console_expected = None
        self.console_actual = None
        self.console_ok = None


def _abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def _run(cmd, timeout=None, cwd=None):
    """Run cmd; return (rc, stdout, stderr, timed_out).  The command's own exit
    code is captured directly (no shell pipe, so nothing can swallow it)."""
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, cwd=cwd,
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
        rules = [s for s in entry.get("sources", []) if s.endswith(".s")]
        programs.append({
            "name": entry["name"],
            "category": entry.get("category", "?"),
            "expected": int(entry["expected_exit_code"]),
            "console": entry.get("expected_console"),
            "file": entry.get("expected_file"),
            "cause": entry.get("expected_cause"),
            "source": rules[0] if rules else entry["sources"][0],
        })
    if not programs:
        sys.stderr.write(f"ERROR: {expected_path}: zero programs\n")
        sys.exit(2)
    return programs


def parse_cpu_log(text: str):
    """Return the list of (pc, mode) pairs from a `-d cpu` dump."""
    blocks = []
    pc = None
    for line in text.splitlines():
        m = re.match(r"^PC: ([0-9a-fA-F]+)$", line.strip())
        if m:
            if pc is not None:
                blocks.append((pc, None))
            pc = int(m.group(1), 16)
            continue
        m = re.match(r"^MODE: (\d+)$", line.strip())
        if m and pc is not None:
            blocks.append((pc, int(m.group(1))))
            pc = None
    if pc is not None:
        blocks.append((pc, None))
    return blocks


def check_bootrom(log: str):
    """Return (ok, detail) for the bootrom-effectiveness observation."""
    blocks = parse_cpu_log(log)
    if not blocks:
        return False, "no `-d cpu` dump blocks"
    if blocks[0][0] != RESET_PC:
        return False, f"first PC 0x{blocks[0][0]:x} != reset PC 0x{RESET_PC:x}"
    if BOOTROM_USER_VECTOR not in log:
        return False, "bootrom cfx_umon user vector 0xffff_ffff_0200 not observed"
    user_hit = any(
        RAM_BASE <= pc < RAM_BASE + RAM_SIZE and mode == USER_MODE
        for pc, mode in blocks
    )
    if not user_hit:
        return False, "application not observed running in user mode (MODE==0)"
    return True, "reset PC ok; bootrom user vector set; app entered user mode"


def build_and_run(prog, tools, work_dir, timeout, verbose=False):
    res = CaseResult(prog["name"], prog["category"], prog["expected"])
    res.expected_cause = prog.get("cause")
    src = os.path.join(tools["vectors_dir"], prog["source"])
    if not os.path.isfile(src):
        res.reason = f"source not found: {src}"
        return res

    stem = os.path.splitext(os.path.basename(prog["source"]))[0]
    obj = os.path.join(work_dir, stem + ".o")
    bin_path = os.path.join(work_dir, stem + ".bin")
    console_path = os.path.join(work_dir, stem + ".console")
    cpu_log = os.path.join(work_dir, stem + ".cpu.log")

    # 1. llvm-mc -filetype=obj -> .o
    rc, _out, err, timed = _run(
        [tools["llvm_mc"], "--triple=dadao-unknown-elf", "-filetype=obj",
         src, "-o", obj])
    if timed or rc != 0:
        res.reason = f"llvm-mc failed (rc={rc})" + (
            f": {err.strip()[:200]}" if err.strip() else "")
        return res

    # 2. llvm-objcopy -O binary --only-section=.text -> .bin
    rc, _out, err, timed = _run(
        [tools["llvm_objcopy"], "-O", "binary", "--only-section=.text",
         obj, bin_path])
    if timed or rc != 0:
        res.reason = f"llvm-objcopy failed (rc={rc})" + (
            f": {err.strip()[:200]}" if err.strip() else "")
        return res

    # 3. qemu: -bios bootrom + -kernel bin + semihosting (-chardev capture)
    for stale in (console_path, cpu_log):
        if os.path.exists(stale):
            os.remove(stale)
    cmd = [
        tools["qemu"],
        "-M", "dadao-m1",
        "-bios", tools["bootrom"],
        "-kernel", bin_path,
        "-semihosting-config", "enable=on,target=native,chardev=semi",
        "-chardev", "file,id=semi,path=" + console_path,
        "-display", "none",
        "-nographic",
        "-d", "cpu",
        "-D", cpu_log,
    ]
    res.cmdline = " ".join(cmd)
    rc, _out, err, timed = _run(cmd, timeout=timeout, cwd=work_dir)
    if timed:
        res.reason = f"qemu timeout after {timeout}s"
        return res
    res.actual = rc
    if rc is None:
        res.reason = "qemu did not return an exit code"
        return res

    # 4. observations
    console = b""
    if os.path.exists(console_path):
        with open(console_path, "rb") as fh:
            console = fh.read()
    res.console_actual = console
    log = ""
    if os.path.exists(cpu_log):
        with open(cpu_log, "r", encoding="utf-8", errors="replace") as fh:
            log = fh.read()

    problems = []
    if rc != prog["expected"]:
        if rc in FAULT_NAMES:
            problems.append(f"rc=0x{rc:02x} ({FAULT_NAMES[rc]})")
        else:
            problems.append(f"rc={rc} != expected {prog['expected']}")

    if prog["console"] is not None:
        want = prog["console"].encode("latin-1")
        res.console_expected = want
        res.console_ok = (console == want)
        if not res.console_ok:
            problems.append(f"console={console!r} != {want!r}")

    file_expect = prog.get("file")
    if file_expect:
        fpath = os.path.join(work_dir, file_expect["name"])
        got = None
        if os.path.exists(fpath):
            with open(fpath, "rb") as fh:
                got = fh.read()
        want = str(file_expect["contents"]).encode("latin-1")
        if got != want:
            problems.append(f"file {file_expect['name']}={got!r} != {want!r}")

    ok, detail = check_bootrom(log)
    if not ok:
        problems.append(f"bootrom: {detail}")

    if problems:
        res.reason = "; ".join(problems)
    else:
        res.passed = True
        res.reason = "match"
    if verbose:
        sys.stdout.write(f"    [bootrom] {detail}\n")
    return res


def run_suite(programs, tools, work_dir, timeout, verbose=False):
    results = []
    for prog in programs:
        res = build_and_run(prog, tools, work_dir, timeout, verbose)
        actual = "?" if res.actual is None else str(res.actual)
        status = "PASS" if res.passed else "FAIL"
        cause = f" cause={res.expected_cause}" if res.expected_cause else ""
        sys.stdout.write(f"  [qemu] {res.cmdline}\n")
        sys.stdout.write(
            f"  {status}  {res.name}  expected={res.expected} actual={actual} "
            f"exit={actual}{cause}  ({res.reason})\n")
        # Console capture (chardev file) is compared byte-exactly; echo the
        # expected/actual bytes so the comparison is visible in the gate log.
        if res.console_expected is not None:
            verdict = "match" if res.console_ok else "MISMATCH"
            sys.stdout.write(
                f"  console {res.name}  expected={res.console_expected!r} "
                f"actual={res.console_actual!r} {verdict} (byte-exact)\n")
        sys.stdout.flush()
        results.append(res)
    return results


def main():
    ap = argparse.ArgumentParser(
        description="M5 SEE/semihosting end-to-end gate (TESTCASES-033t)")
    ap.add_argument("--llvm-mc", dest="llvm_mc",
                    default=os.environ.get("LLVM_MC", DEFAULT_LLVM_MC))
    ap.add_argument("--llvm-objcopy", dest="llvm_objcopy",
                    default=os.environ.get("LLVM_OBJCOPY", DEFAULT_LLVM_OBJCOPY))
    ap.add_argument("--qemu", default=os.environ.get("QEMU_SYSTEM_DADAO", DEFAULT_QEMU))
    ap.add_argument("--bootrom", default=os.environ.get("BOOTROM", DEFAULT_BOOTROM))
    ap.add_argument("--vectors-dir", default=DEFAULT_VECTORS_DIR)
    ap.add_argument("--expected", default=DEFAULT_EXPECTED)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--only", default=None, help="run a single case by name")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--inject", action="store_true",
                    help="counter-example self-test: flip a baseline-PASSing "
                         "expected exit code and require the gate to FAIL, then "
                         "restore and re-run the whole suite for green")
    args = ap.parse_args()

    tools = {
        "llvm_mc": _abspath(args.llvm_mc),
        "llvm_objcopy": _abspath(args.llvm_objcopy),
        "qemu": _abspath(args.qemu),
        "bootrom": _abspath(args.bootrom),
        "vectors_dir": _abspath(args.vectors_dir),
    }
    expected_path = _abspath(args.expected)
    work_dir = _abspath(args.work_dir)

    _require_exec(tools["llvm_mc"], "llvm-mc")
    _require_exec(tools["llvm_objcopy"], "llvm-objcopy")
    _require_exec(tools["qemu"], "qemu-system-dadao")
    if not os.path.isfile(tools["bootrom"]):
        sys.stderr.write(
            f"ERROR: bootrom not found: {tools['bootrom']}\n"
            "       run 'make build-bootrom' first (QEMU-047t)\n")
        sys.exit(2)
    if not os.path.isfile(expected_path):
        sys.stderr.write(f"ERROR: expected.yaml not found: {expected_path}\n")
        sys.exit(2)

    os.makedirs(work_dir, exist_ok=True)

    programs = load_programs(expected_path)
    if args.only:
        programs = [p for p in programs if p["name"] == args.only]
        if not programs:
            sys.stderr.write(f"ERROR: no case named {args.only!r}\n")
            sys.exit(2)

    sys.stdout.write(
        f"run_m5_e2e: {len(programs)} programs, bootrom {tools['bootrom']}, "
        f"work dir {work_dir}\n")
    results = run_suite(programs, tools, work_dir, args.timeout, args.verbose)

    failed = [r for r in results if not r.passed]
    sys.stdout.write(
        f"\nResults: {len(results) - len(failed)}/{len(results)} passed, "
        f"{len(failed)} failed\n")

    # ---- counter-example self-test --------------------------------------
    if args.inject:
        passing = [r for r in results if r.passed]
        if not passing:
            sys.stderr.write("INJECT: FAIL -- no baseline-PASSing case to inject into\n")
            return 2
        target = passing[0]
        prog = next(p for p in programs if p["name"] == target.name)
        original = prog["expected"]
        prog["expected"] = (original + 1) % 256
        sys.stdout.write(
            f"\nINJECT: case={target.name} expected {original} -> {prog['expected']}\n")
        inject_res = build_and_run(prog, tools, work_dir, args.timeout, args.verbose)
        sys.stdout.write(
            f"  {'FAIL' if not inject_res.passed else 'PASS'}  {inject_res.name}  "
            f"expected={inject_res.expected} actual={inject_res.actual} "
            f"exit={inject_res.actual}  ({inject_res.reason})\n")
        if inject_res.passed:
            sys.stderr.write(
                "INJECT: FAIL -- gate did NOT detect the wrong expected value "
                "(comparison is not live)\n")
            return 1
        prog["expected"] = original
        sys.stdout.write(
            f"RESTORE: case={target.name} expected back to {original}; "
            f"re-running whole suite\n")
        restored = run_suite(programs, tools, work_dir, args.timeout, args.verbose)
        if any(not r.passed for r in restored):
            sys.stderr.write(
                "INJECT: FAIL -- suite did not go green after restoring the "
                "expected value\n")
            return 1
        sys.stdout.write("INJECT: PASS -- gate reported FAIL on the wrong expected "
                         "value and went green again after restore\n")
        return 0

    if failed:
        sys.stdout.write("run_m5_e2e: FAIL\n")
        return 1
    sys.stdout.write("run_m5_e2e: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
