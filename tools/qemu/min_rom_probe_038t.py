#!/usr/bin/env python3
"""Min ROM probe for QEMU-038t: FP runtime `dst_rd0` ILLI (15 rd-destination insns).

Spec sources (expectations derived by hand from these, never from QEMU/LLVM):
  - spec/SimRISC-00 §数据寄存器 / §浮点寄存器
  - spec/SimRISC-07 §格式转换指令 / §浮点比较指令 / §浮点分类指令
  - .tao/knowledge/contract-fp.md §3 / §8 / §9 / §12 / §15
  - contracts/legality_rules.yaml `dst_rd0` (active)
  - contracts/fp_semantics.yaml (legality_refs include dst_rd0 for these 15)
Encodings: contracts/opcodes.yaml.  Exit codes: ADR-0004 D5.8 (PASS=0x00, ILLI=0x88).

Instructions under test (15 rd-destination forms, all destination field = a->hb):
  convert_f2i (8): ft2it ft2io ft2ut ft2uo fo2it fo2io fo2ut fo2uo   (orri)
  classify    (2): ftcls focls                                        (orri)
  compare     (4): ftqcmp ftscmp foqcmp foscmp                        (orrr)
  rf_move     (1): rf2rd                                              (orri)

Rule (Spec-first): the destination start register == rd0 ⇒ ILLI (0x88).  This is
checked at translate time, so it is a fault on *execution* of the offending
encoding.  `rd1`.. destinations execute normally; `rf0` as a *source* (rfHC /
rdHC) is unaffected; `rd2rf` (RF destination) is not part of this rule.

Verification channels (same conventions as min_rom_probe_034t/035t/036t/037t):
  * value cases  -> QEMU `-d cpu` dump, parsing the *last* RD[] dump.
  * fault cases  -> process exit code (ILLI 0x88).
  * non-rd0 control cases -> same body + PASS epilogue; must exit 0x00.
  * E2E cases    -> in-ROM compare + SYS_EXIT PASS/FAIL epilogue.

Reverse gate (.work/evidence/QEMU-038t/run.sh --inject) injects one
individually-attributed per-family regression at a time into the implementation
(convert_f2i / classify / compare / rf2rd), requires ONLY that family's rd0
cases to FAIL, restores, rebuilds and requires the probe green again.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

# D6 compliance: resolve probe artifact dir via paths.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths  # noqa: E402


def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d


QEMU = ".work/build/qemu/qemu-system-dadao"

PASS_EXIT = 0x00
ILLI_EXIT = 0x88

ILLI = 0x77000000
SWYM = 0x77880000

# ft / fo operand bit patterns (used only to give executed controls a value)
F0 = 0x00000000
F1 = 0x3F800000
F2 = 0x40000000
F3 = 0x40400000
RF_SCRATCH = 0x1122334455667788

# ── Instruction encoding (op / ha from contracts/opcodes.yaml) ────────────


def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)


def encode_rrii(op, ha, hb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)


def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (hd & 0x3F))


def encode_riii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))


def encode_orrr(op, ha, hb, hc, hd):
    return encode_orri(op, ha, hb, hc, hd)


# M1 integer instructions, used only for setup / assertion (trusted)
def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)


def or_w_rd(rd, wp, immu16):
    return encode_rwii(0x48, rd, wp, immu16)


def set_zw_rb(rb, wp, immu16):
    return encode_rwii(0x4E, rb, wp, immu16)


def or_w_rb(rb, wp, immu16):
    return encode_rwii(0x4A, rb, wp, immu16)


def st_o_rd(rdha, rbhb, imms12):
    return encode_rrii(0x21, rdha, rbhb, imms12)


def cmp_uo_rd(rdhb, rdhc, rdhd):
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


def rd2rf(rfhb, rdhc, hd):
    return encode_orri(0x40, 0x3D, rfhb, rdhc, hd)


def rf2rd(rdhb, rfhc, hd):
    return encode_orri(0x40, 0x3E, rdhb, rfhc, hd)


# ── Instructions under test (ha from contracts/opcodes.yaml) ──────────────
# convert_f2i: orri, op 0x44, hb = rd dest start, hc = rf source start, hd = count

def ft2it(hb, hc, hd):
    return encode_orri(0x44, 0x30, hb, hc, hd)


def ft2io(hb, hc, hd):
    return encode_orri(0x44, 0x31, hb, hc, hd)


def ft2ut(hb, hc, hd):
    return encode_orri(0x44, 0x32, hb, hc, hd)


def ft2uo(hb, hc, hd):
    return encode_orri(0x44, 0x33, hb, hc, hd)


def fo2it(hb, hc, hd):
    return encode_orri(0x44, 0x38, hb, hc, hd)


def fo2io(hb, hc, hd):
    return encode_orri(0x44, 0x39, hb, hc, hd)


def fo2ut(hb, hc, hd):
    return encode_orri(0x44, 0x3A, hb, hc, hd)


def fo2uo(hb, hc, hd):
    return encode_orri(0x44, 0x3B, hb, hc, hd)


# classify: orri, op 0x44
def ftcls(hb, hc, hd):
    return encode_orri(0x44, 0x00, hb, hc, hd)


def focls(hb, hc, hd):
    return encode_orri(0x44, 0x08, hb, hc, hd)


# compare: orrr, op 0x44, hb = rd dest, hc/hd = rf sources
def ftqcmp(hb, hc, hd):
    return encode_orrr(0x44, 0x20, hb, hc, hd)


def ftscmp(hb, hc, hd):
    return encode_orrr(0x44, 0x21, hb, hc, hd)


def foqcmp(hb, hc, hd):
    return encode_orrr(0x44, 0x28, hb, hc, hd)


def foscmp(hb, hc, hd):
    return encode_orrr(0x44, 0x29, hb, hc, hd)


# ── Setup helpers ─────────────────────────────────────────────────────────

def load_imm64_rd(rd, val):
    insns = [set_zw_rd(rd, val & 0xFFFF)]
    for wp in range(1, 4):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            insns.append(or_w_rd(rd, wp, w))
    return insns


def set_rf(rf, val):
    """Load rf[rf] = val (uses rd31 as scratch; rd2rf is trusted here)."""
    return load_imm64_rd(31, val) + [rd2rf(rf, 31, 1)]


# ── Semihosting SYS_EXIT (ADR-0020 D8: replaces the legacy MMIO halt device) ──

SEMI_BLOCK = 0x0000_00FF_F000       # argument block {reason, code}, in RAM
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def trap_ciii(cfxha, immu18):
    return encode_riii(0x7F, cfxha, immu18 & 0x3FFFF)


def semi_exit(code_rd):
    """rb16 = SEMI_BLOCK; block = {0x20026, code_rd}; rd16 = 0x18; trap."""
    return ([set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000)]
            + load_imm64_rd(8, ADP_STOPPED_APPLICATION_EXIT)
            + [st_o_rd(8, 16, 0)]
            + [st_o_rd(code_rd, 16, 8)]
            + load_imm64_rd(16, 0x18)
            + [trap_ciii(0, SEMIHOST_TAG)])


# ── ROM assembly ──────────────────────────────────────────────────────────

TRAMPOLINE = [
    set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),  # rb16 = 0x00000000FF0000 (dead; semi_exit rebuilds it)
    set_zw_rb(17, 0, 0x0000),                          # rb17 = RAM
    encode_rwii(0x4C, 40, 0, 0x0001),                  # rd40 = 1 (TB split)
]


def build_rom(test_insns):
    """Value-case ROM: body + ILLI terminator (RD comparison is the check)."""
    rom = b''.join(TRAMPOLINE) + b''.join(test_insns) + struct.pack('>I', ILLI)
    while len(rom) < 64:
        rom += struct.pack('>I', SWYM)
    return rom


def build_body_rom(test_insns):
    """Fault / control ROM: body + PASS epilogue.

    If the instruction under test does NOT fault (fault case) the PASS epilogue
    reports 0 via SYS_EXIT -> exit 0x00 != 0x88 => FAIL.  For control cases
    the same epilogue is the expected "no fault" exit 0x00; an unexpected fault
    gives 0x88 != 0x00 => FAIL.  Either way every case has a reachable FAIL
    path."""
    return (b''.join(TRAMPOLINE) + b''.join(test_insns) +
            b''.join([set_zw_rd(18, 0)] + semi_exit(18)))


def build_e2e_rom(test_insns):
    return b''.join(TRAMPOLINE) + b''.join(test_insns)


# ── QEMU execution ────────────────────────────────────────────────────────

def run_plain(rom_data, timeout=10):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(b'\x00' * 16)
        kp = f.name
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp, '-semihosting-config', 'enable=on,target=native'],
            capture_output=True, timeout=timeout, text=True)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rp)
        os.unlink(kp)


def run_dcpu(rom_data, timeout=10):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(b'\x00' * 16)
        kp = f.name
    lp = rp + '.cpu.log'
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp,
             '-semihosting-config', 'enable=on,target=native',
             '-d', 'cpu', '-D', lp],
            capture_output=True, timeout=timeout, text=True)
        with open(lp) as lf:
            return r.returncode, lf.read()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rp)
        os.unlink(kp)
        if os.path.exists(lp):
            os.unlink(lp)


def last_reg(log_text, bank, idx):
    pat = re.compile(r'%s\[%02d\]:\s*([0-9a-fA-F]{16})' % (bank, idx))
    m = None
    for mm in pat.finditer(log_text):
        m = mm
    return int(m.group(1), 16) if m else None


def e2e_epilogue(checks, fail_code):
    """checks: list of (actual_rd, expected_rd, flag_rd)."""
    N = len(checks)
    pass_arm = [set_zw_rd(18, 0)] + semi_exit(18)             # PASS: exit 0
    fail_arm = [set_zw_rd(19, fail_code)] + semi_exit(19)     # FAIL: exit fail_code
    P = len(pass_arm)
    insns = []
    for i, (actual, expected, flag) in enumerate(checks):
        offset = 2 * (N - i) + (P - 1)
        insns.append(cmp_uo_rd(flag, actual, expected))
        insns.append(br_nz(flag, offset))
    insns += pass_arm
    insns += fail_arm
    return insns


# ── Case model ────────────────────────────────────────────────────────────

class Case:
    def __init__(self, name, insns, expect_exit=None,
                 expect_rf=None, expect_rd=None, e2e=False):
        self.name = name
        self.insns = insns
        self.expect_exit = expect_exit
        self.expect_rf = expect_rf or {}
        self.expect_rd = expect_rd or {}
        self.e2e = e2e


def value_case(name, insns, expect_rf=None, expect_rd=None):
    body = list(insns) + [br_nz(40, 1)]        # rd40=1 -> taken to terminator, TB split
    return Case(name, body, expect_exit=ILLI_EXIT,
                expect_rf=expect_rf, expect_rd=expect_rd)


# All 15 instruction constructors, keyed by short tag (used by the reverse gate
# to attribute failing cases to a family).
FAMILY_CONVERT = ['ft2it', 'ft2io', 'ft2ut', 'ft2uo',
                  'fo2it', 'fo2io', 'fo2ut', 'fo2uo']
FAMILY_CLASSIFY = ['ftcls', 'focls']
FAMILY_COMPARE = ['ftqcmp', 'ftscmp', 'foqcmp', 'foscmp']
FAMILY_RF2RD = ['rf2rd']

CONSTRUCTORS = {
    'ft2it': ft2it, 'ft2io': ft2io, 'ft2ut': ft2ut, 'ft2uo': ft2uo,
    'fo2it': fo2it, 'fo2io': fo2io, 'fo2ut': fo2ut, 'fo2uo': fo2uo,
    'ftcls': ftcls, 'focls': focls,
    'ftqcmp': ftqcmp, 'ftscmp': ftscmp, 'foqcmp': foqcmp, 'foscmp': foscmp,
    'rf2rd': rf2rd,
}
ALL_15 = FAMILY_CONVERT + FAMILY_CLASSIFY + FAMILY_COMPARE + FAMILY_RF2RD


def encode_under_test(tag, dest, count=1):
    """Encode one of the 15 instructions with destination start `dest`."""
    if tag in ('ftqcmp', 'ftscmp', 'foqcmp', 'foscmp'):
        return CONSTRUCTORS[tag](dest, 8, 9)   # orrr: dest, rfHC, rfHD
    if tag == 'rf2rd':
        return rf2rd(dest, 8, count)           # rdHB dest, rfHC src, count
    return CONSTRUCTORS[tag](dest, 8, count)   # orri: rd dest, rf src, count


CASES = []

# ── fault: destination rd0 -> ILLI 0x88 (one per instruction, 15) ─────────
for _tag in ALL_15:
    CASES.append(Case(f"RD0-{_tag} dest rd0 -> ILLI",
                      [encode_under_test(_tag, 0, 1)], expect_exit=ILLI_EXIT))

# ── fault: multi-register group starting at rd0 {rd0:rd2} (>= 3) ──────────
CASES.append(Case("RD0-GRP ft2it {rd0:rd2} -> ILLI",
                  [encode_under_test('ft2it', 0, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("RD0-GRP ftcls {rd0:rd2} -> ILLI",
                  [encode_under_test('ftcls', 0, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("RD0-GRP rf2rd {rd0:rd2} -> ILLI",
                  [encode_under_test('rf2rd', 0, 3)], expect_exit=ILLI_EXIT))

# ── control: non-rd0 destination must NOT fault (exit 0x00) ───────────────
for _tag in ALL_15:
    CASES.append(Case(f"CTL-{_tag} dest rd1 -> no fault",
                      [encode_under_test(_tag, 1, 1)], expect_exit=PASS_EXIT))
CASES.append(Case("CTL ft2it {rd1:rd3} dest rd1 -> no fault",
                  [encode_under_test('ft2it', 1, 3)], expect_exit=PASS_EXIT))
CASES.append(Case("CTL rf2rd {rd1:rd3} dest rd1 -> no fault",
                  [encode_under_test('rf2rd', 1, 3)], expect_exit=PASS_EXIT))

# ── value: executed non-rd0 result read back via `-d cpu` ─────────────────
CASES.append(value_case(
    "V1 ft2it rd5,rf8,1 (3.0 -> 3)",
    set_rf(8, F3) + [ft2it(5, 8, 1)],
    expect_rd={5: 3}))
CASES.append(value_case(
    "V2 ftcls rd5,rf8,1 (1.0 -> positiveNormal bit6 = 0x40)",
    set_rf(8, F1) + [ftcls(5, 8, 1)],
    expect_rd={5: 0x40}))
CASES.append(value_case(
    "V3 ftqcmp rd5,rf8,rf9 (1.0 < 2.0 -> -1)",
    set_rf(8, F1) + set_rf(9, F2) + [ftqcmp(5, 8, 9)],
    expect_rd={5: 0xFFFFFFFFFFFFFFFF}))
CASES.append(value_case(
    "V4 rf2rd rd20,rf8,1 (full word copy)",
    set_rf(8, RF_SCRATCH) + [rf2rd(20, 8, 1)],
    expect_rd={20: RF_SCRATCH}))

# ── E2E: non-rd0 execution + SYS_EXIT assertion (>= 2) ───────────────────
_e1 = (set_rf(8, F3) + [ft2it(5, 8, 1)] +
       load_imm64_rd(22, 3) + e2e_epilogue([(5, 22, 24)], 0x47))
CASES.append(Case("E1 ft2it rd5,rf8,1 = 3 (SYS_EXIT assertion)", _e1,
                  expect_exit=PASS_EXIT, e2e=True))

_e2 = (set_rf(4, RF_SCRATCH) + [rf2rd(20, 4, 1)] +
       load_imm64_rd(22, RF_SCRATCH) + e2e_epilogue([(20, 22, 24)], 0x48))
CASES.append(Case("E2 rf2rd rd20,rf4,1 full word (SYS_EXIT assertion)", _e2,
                  expect_exit=PASS_EXIT, e2e=True))

_e3 = (set_rf(8, F1) + [ftcls(5, 8, 1)] +
       load_imm64_rd(22, 0x40) + e2e_epilogue([(5, 22, 24)], 0x49))
CASES.append(Case("E3 ftcls rd5,rf8,1 = 0x40 (SYS_EXIT assertion)", _e3,
                  expect_exit=PASS_EXIT, e2e=True))


# ── Runner ────────────────────────────────────────────────────────────────

def run_case(case):
    """Return (ok, detail_lines)."""
    if case.expect_rf or case.expect_rd:
        rom = build_rom(case.insns)
        code, log = run_dcpu(rom)
        if code != case.expect_exit:
            return False, [f"exit=0x{code & 0xFF:02X} (expect 0x{case.expect_exit:02X})"]
        details = []
        ok = True
        for idx, exp in sorted(case.expect_rf.items()):
            got = last_reg(log, 'RF', idx)
            good = got == exp
            ok = ok and good
            details.append(
                f"RF[{idx:02d}] expect=0x{exp:016X} got="
                f"{'0x%016X' % got if got is not None else 'MISSING'} "
                f"{'OK' if good else 'MISMATCH'}")
        for idx, exp in sorted(case.expect_rd.items()):
            got = last_reg(log, 'RD', idx)
            good = got == exp
            ok = ok and good
            details.append(
                f"RD[{idx:02d}] expect=0x{exp:016X} got="
                f"{'0x%016X' % got if got is not None else 'MISSING'} "
                f"{'OK' if good else 'MISMATCH'}")
        return ok, details
    else:
        rom = build_e2e_rom(case.insns) if case.e2e else build_body_rom(case.insns)
        code, stderr = run_plain(rom)
        good = (code == case.expect_exit)
        detail = f"exit=0x{code & 0xFF:02X} (expect 0x{case.expect_exit:02X})"
        if not good and stderr and code != -1:
            detail += f" stderr={stderr[:120]}"
        return good, [detail]


def selftest():
    """Prove every assertion kind has a reachable FAIL path."""
    os.chdir(_REPO_ROOT)
    print("=" * 78)
    print("QEMU-038t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []

    # 1. RD value comparison (wrong expected rd value)
    c1 = value_case("selftest rd-value", set_rf(8, F3) + [ft2it(5, 8, 1)],
                    expect_rd={5: 0xDEAD})
    ok1, _ = run_case(c1)
    results.append(("RD value comparison FAIL path", ok1 is False))

    # 2. fault exit code: a legal non-rd0 op expected to fault runs to exit 0
    c2 = Case("selftest fault", [ft2it(1, 8, 1)], expect_exit=ILLI_EXIT)
    ok2, _ = run_case(c2)
    results.append(("fault exit-code FAIL path", ok2 is False))

    # 3. control exit code: an rd0 op expected NOT to fault actually faults 0x88
    c3 = Case("selftest control", [ft2it(0, 8, 1)], expect_exit=PASS_EXIT)
    ok3, _ = run_case(c3)
    results.append(("no-fault control FAIL path", ok3 is False))

    # 4. E2E SYS_EXIT assertion (wrong expected -> FAIL arm -> exit != 0)
    insns = (set_rf(8, F3) + [ft2it(5, 8, 1)] +
             load_imm64_rd(22, 4) + e2e_epilogue([(5, 22, 24)], 0x4A))
    c4 = Case("selftest e2e", insns, expect_exit=PASS_EXIT, e2e=True)
    ok4, _ = run_case(c4)
    results.append(("E2E SYS_EXIT assertion FAIL path", ok4 is False))

    allok = True
    for name, v in results:
        if not v:
            allok = False
        print(f"  [{'PASS' if v else 'FAIL'}] {name} must be detected as FAIL")

    print(f"\nSelf-test: {'PASS' if allok else 'FAIL'}")
    return 0 if allok else 1


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 78)
    print("QEMU-038t Min ROM Probe (FP runtime dst_rd0 ILLI, 15 rd-dest insns)")
    print("=" * 78)

    passed = failed = 0
    failed_names = []
    for case in CASES:
        ok, details = run_case(case)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
            failed_names.append(case.name)
        print(f"  [{status}] {case.name}")
        for d in details:
            print(f"          {d}")

    print("-" * 78)
    print(f"Main: {passed}/{passed + failed} passed, {failed} failed")
    if failed_names:
        print("Failed:")
        for n in failed_names:
            print(f"  - {n}")
    print(f"\nOverall: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
