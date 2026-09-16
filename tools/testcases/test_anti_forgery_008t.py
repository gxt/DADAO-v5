#!/usr/bin/env python3
"""反造假注入测试（TESTCASES-008t 验收 6）。

在 /tmp/opencode/TESTCASES-008t/ 副本注入 5 类错误，
确认 validator 全部捕获并 exit 1。

用法：python3 tools/testcases/test_anti_forgery_008t.py
"""

import os
import shutil
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORK = "/tmp/opencode/TESTCASES-008t"
ISA_DIR = os.path.join(WORK, "tests", "vectors", "isa")
CONTRACTS_DIR = os.path.join(WORK, "contracts")
VECTORS_DIR = os.path.join(WORK, "tests", "vectors")
VALIDATOR_SRC = os.path.join(REPO, "tools", "testcases", "validate_vectors.py")

PASS_CASES = [
    "- class: legality",
    "  encoding:",
    '    word: "0x08040001"',
    "    reserved: true",
    "  mnemonic: null",
    "  insn: null",
    "  format: null",
    "  input_state: {}",
    "  expected_state: null",
    "  expected_pc: null",
    "  expected_fault: UNDI",
    "  status: active",
    '  spec_cite: "SimRISC-00 §SimRISC QFC; contract-isa §2.9/§8.2"',
    '  notes: "QFC 主表 op=0x08（0000-1xxx 整行 reserved）"',
]

INJECT1 = [line.replace("expected_fault: UNDI", "expected_fault: null")
           for line in PASS_CASES]
INJECT2 = [line.replace("expected_fault: UNDI", "expected_fault: ILLI")
           for line in PASS_CASES]
INJECT3 = [line.replace("0x08040001", "0x10041000")
           for line in PASS_CASES]
INJECT4 = [line.replace("0x08040001", "0x16000000")
           for line in PASS_CASES]
INJECT5 = [line.replace("0x08040001", "0x00000000")
           for line in PASS_CASES]


def setup_workdir():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(ISA_DIR, exist_ok=True)
    os.makedirs(CONTRACTS_DIR, exist_ok=True)
    os.makedirs(VECTORS_DIR, exist_ok=True)
    shutil.copy2(os.path.join(REPO, "contracts", "opcodes.yaml"),
                 os.path.join(CONTRACTS_DIR, "opcodes.yaml"))
    shutil.copy2(os.path.join(REPO, "tests", "vectors", "inventory.md"),
                 os.path.join(VECTORS_DIR, "inventory.md"))
    real_isa = os.path.join(REPO, "tests", "vectors", "isa")
    for fn in os.listdir(real_isa):
        if fn.endswith(".yaml"):
            shutil.copy2(os.path.join(real_isa, fn),
                         os.path.join(ISA_DIR, fn))
    with open(VALIDATOR_SRC) as f:
        src = f.read()
    patched = src.replace(
        '    repo_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))',
        '    repo_dir = "%s"' % WORK
    )
    with open(os.path.join(WORK, "validate_vectors.py"), "w") as f:
        f.write(patched)


def write_case(lines):
    with open(os.path.join(ISA_DIR, "reserved.yaml"), "w") as f:
        f.write("\n".join(lines) + "\n")


def run_validator():
    result = subprocess.run(
        [sys.executable, os.path.join(WORK, "validate_vectors.py")],
        capture_output=True, text=True
    )
    return result.returncode, result.stderr


def main():
    setup_workdir()
    failures = []
    tests = [
        ("inject1: expected_fault=null", INJECT1, "R2"),
        ("inject2: expected_fault=ILLI", INJECT2, "R2"),
        ("inject3: reserved:true + word=M1 (0x10041000=ld.ub-rd)", INJECT3, "R8/M1"),
        ("inject4: reserved:true + word=excluded_m1 (0x16000000=ld.t-rf)", INJECT4, "R8/excluded"),
        ("inject5: word=0x00000000", INJECT5, "R4"),
    ]
    for name, lines, rule in tests:
        write_case(lines)
        code, stderr = run_validator()
        if code == 0:
            failures.append("FAIL %s: exit=0" % name)
            print("FAIL: %s" % name)
        else:
            print("PASS: %s [%s]" % (name, rule))
            for line in stderr.strip().split("\n"):
                if "reserved" in line.lower() or "UNDI" in line or \
                   "word" in line.lower() or "matches defined" in line.lower():
                    print("  -> %s" % line)
                    break

    write_case(PASS_CASES)
    code, _ = run_validator()
    if code != 0:
        failures.append("FAIL valid case: exit=%d" % code)
    else:
        print("PASS: valid reserved case")

    shutil.rmtree(WORK, ignore_errors=True)
    if failures:
        for f in failures:
            print(f)
        sys.exit(1)
    print("\n=== ALL 5 INJECTION + 1 VALID TEST PASSED ===")


if __name__ == "__main__":
    main()
