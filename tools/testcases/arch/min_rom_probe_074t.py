#!/usr/bin/env python3
"""Min ROM probe for QEMU-074t: cmp.{ut,uw,ub} result is 64-bit (ADR-0037 D1).

Spec sources (expectations derived from these, never from QEMU):
  - .tao/adr/adr-0037-cmp-u-result-64bit.md D1:
        -1 = 0xFFFF_FFFF_FFFF_FFFF, 0 = 0, +1 = 1 ; sources still truncated to
        the width (32/16/8).
  - .tao/contracts/contract-isa.md §10.2/§10.5/§10.6 (高位规则, −1 = 全 1)
  - spec/SimRISC-06: br.n = branch when rdHA is negative (bit 63), target
        `rb0 + (imms18 << 2)`;  spec/SimRISC-08/09/10: cmp.{ut,uw,ub}
  - contracts/opcodes.yaml: encoding base words (cmp.ut 0x41A80000, cmp.uw
        0x42A80000, cmp.ub 0x43A80000, cmp.st/sw/sb/uo for the "unchanged"
        guards, br.n 0x68000000).

Why this probe exists: before ADR-0037 the -1 result was zero-extended to the
operand width (cmp.ut -> 0x00000000FFFFFFFF), so `cmp.ut` + `br.n` silently
took the non-negative path.  The acceptance case below therefore pairs the
value assertion with a `br.n` decision assertion: the value alone cannot show
`br.n` works, and `br.n` alone cannot show the stored result is all-ones.

Case model (every assertion has a reachable FAIL path; all checks end in a
guest exit code, so no `-d cpu` dump parsing is involved):
  * value cases: the guest itself compares the stored result against the
    expected 64-bit constant (`xor.o` + `br.z`, both trusted M1 ops): equal ->
    PASS block, different -> mismatch exit code 0x13.  Covers -1/0/+1 across
    ut/uw/ub, source-truncation witnesses (a 64-bit-bigger left operand must
    still compare as smaller after truncation), and cmp.st/cmp.uo
    "no change" guards;
  * branch cases (guest exit code): `br.n` taken on -1 for ut/uw/ub, and NOT
    taken on cmp.ut +1 / cmp.ut 0; two distinct fail codes (0x11 = wrongly
    not taken, 0x12 = wrongly taken) make the failure direction unambiguous;
  * control: a hand-built 0x00000000FFFFFFFF (the pre-ADR-0037 pattern) must
    NOT satisfy `br.n` — proves the branch cases discriminate the two
    semantics instead of being always-taken/always-not-taken;
  * control: `br.n` on a hand-built all-ones value must be taken — proves the
    branch instruction itself works.

Exit codes: ADR-0004 D5.8 via semihosting SYS_EXIT (PASS = 0x00).
Usage: min_rom_probe_074t.py [--selftest]
"""
import os
import struct
import subprocess
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths  # noqa: E402


def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d


QEMU = ".work/build/qemu/qemu-system-dadao"

PASS_EXIT = 0x00

# ── Instruction encoding ───────────────────────────────────────────────

# base words straight from contracts/opcodes.yaml (`value:` of each entry);
# hb = bits[17:12], hc = bits[11:6], hd = bits[5:0].
CMP_UT = 0x41A80000   # cmp.ut rdhb, rdhc, rdhd
CMP_UW = 0x42A80000   # cmp.uw
CMP_UB = 0x43A80000   # cmp.ub
CMP_ST = 0x41AC0000   # cmp.st (unchanged by ADR-0037)
CMP_SW = 0x42AC0000   # cmp.sw (unchanged)
CMP_SB = 0x43AC0000   # cmp.sb (unchanged)
CMP_UO = 0x40A80000   # cmp.uo (unchanged)
XOR_O = 0x40280000    # xor.o rdhb, rdhc, rdhd (trusted M1 op; ha=0x0A)

ALL_ONES = 0xFFFFFFFFFFFFFFFF


def cmp_insn(base, hb, hc, hd):
    """orrr compare: rdhb(dst), rdhc, rdhd."""
    return struct.pack('>I', base | (hb << 12) | (hc << 6) | hd)


def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) |
                       (mid6 << 6) | lo6)


def encode_rrii(op, ha, hb, imms12):
    imm = imms12 & 0xFFF
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) |
                       ((imm >> 6) << 6) | (imm & 0x3F))


def encode_oiii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))


# M1 setup instructions (trusted, not under test)
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


def fence():
    return struct.pack('>I', 0x79000000)


def trap_sys_exit():
    return encode_oiii(0x7F, 0x00, SEMIHOST_TAG)


def load_imm64_rd(rd, val):
    """Build an arbitrary 64-bit value in rd (set.zw + or.w words)."""
    insns = [set_zw_rd(rd, val & 0xFFFF)]
    for wp in range(1, 4):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            insns.append(or_w_rd(rd, wp, w))
    return insns


# ── Semihosting SYS_EXIT (ADR-0020 D8) ────────────────────────────────

SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026
CODE_RD = 18            # data register carrying the exit code

# Trampoline: rb1 = stack, rb2 = RAM base, rb16 = semihosting block
# (0xFC00_00FF_F000); block[0] = ADP_Stopped_ApplicationExit, rd16 = 0x18.
TRAMPOLINE = [
    set_zw_rb(1, 0, 0x0000), or_w_rb(1, 1, 0x00FF), or_w_rb(1, 2, 0xFC00),
    set_zw_rb(2, 0, 0x0000), or_w_rb(2, 2, 0xFC00),
    set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),
    or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00),
] + load_imm64_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [
    st_o_rd(8, 16, 0),                              # block[0] = 0x20026
    set_zw_rd(16, 0x0018),                          # rd16 = 0x18 (SYS_EXIT)
]


def semi_exit(code):
    """Store *code* into the argument block and trap SYS_EXIT (2 insns)."""
    return [set_zw_rd(CODE_RD, code)] + [
        st_o_rd(CODE_RD, 16, 8), trap_sys_exit()]


# `cfxld` (op 0x7C, scope=excluded) -> ILLI (exit 0x88): a case that never
# reaches its exit terminator must not look like PASS.
POISON = b'\x7c\x00\x00\x00'


def build_rom(test_insns):
    rom = b''.join(TRAMPOLINE) + b''.join(test_insns) + POISON
    while len(rom) < 64:
        rom += fence()
    return rom


# ── QEMU execution ────────────────────────────────────────────────────

def _write_tmp(data):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(data)
        return f.name


def run_qemu(rom_data, timeout=10):
    rp = _write_tmp(rom_data)
    kp = _write_tmp(fence() * 4)
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp,
             '-semihosting-config', 'enable=on,target=native'],
            capture_output=True, timeout=timeout, text=True)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return -1, 'TIMEOUT'
    finally:
        for p in (rp, kp):
            if os.path.exists(p):
                os.unlink(p)


# ── Case model ────────────────────────────────────────────────────────

class Case:
    def __init__(self, name, insns, expect_exit=PASS_EXIT, fail_desc=""):
        self.name = name
        self.insns = insns
        self.expect_exit = expect_exit
        self.fail_desc = fail_desc


VALUE_FAIL = 0x13       # stored result != expected constant
NOT_TAKEN_FAIL = 0x11   # br.n should have been taken
TAKEN_FAIL = 0x12       # br.n should not have been taken


def _branch_on(cond_insn, expect_taken, fail_code):
    """cond_insn + the two 3-word exit blocks, laid out around a +4 offset.

        p   : <cond> rd, +4
        p+1 : block A (3 words)
        p+4 : block B (3 words)

    expect_taken    -> A = fail(fail_code), B = pass(0)
    expect_not_taken-> A = pass(0), B = fail(fail_code)
    """
    pass_block = semi_exit(PASS_EXIT)
    fail_block = semi_exit(fail_code)
    blocks = fail_block + pass_block if expect_taken else pass_block + fail_block
    return [cond_insn] + blocks


def value_case(name, base, a_val, b_val, expect, fail_desc=""):
    """rd1 = cmp(rd2=a, rd3=b); guest asserts rd1 == expect (64-bit)."""
    setup = load_imm64_rd(2, a_val) + load_imm64_rd(3, b_val) + \
        [cmp_insn(base, 1, 2, 3)] + load_imm64_rd(4, expect)
    body = _branch_on(encode_oiii(0x6A, 5, 4), expect_taken=True,
                      fail_code=VALUE_FAIL)
    # xor.o rd5 = rd1 ^ rd4, then br.z rd5 -> equal iff result matches.
    insns = setup + [struct.pack('>I', XOR_O | (5 << 12) | (1 << 6) | 4)] + body
    return Case(name, insns, expect_exit=PASS_EXIT, fail_desc=fail_desc)


def branch_case(name, base, a_val, b_val, expect_taken, fail_desc=""):
    """cmp under test, then br.n rd1: assert the branch direction."""
    setup = load_imm64_rd(2, a_val) + load_imm64_rd(3, b_val) + \
        [cmp_insn(base, 1, 2, 3)]
    body = _branch_on(encode_oiii(0x68, 1, 4),
                      expect_taken=expect_taken,
                      fail_code=TAKEN_FAIL if not expect_taken else NOT_TAKEN_FAIL)
    return Case(name, setup + body, expect_exit=PASS_EXIT,
                fail_desc=fail_desc)


def br_only_case(name, value_insns, expect_taken, fail_desc=""):
    """Control: br.n on a hand-built register (no cmp under test)."""
    body = _branch_on(encode_oiii(0x68, 1, 4),
                      expect_taken=expect_taken,
                      fail_code=TAKEN_FAIL if not expect_taken else NOT_TAKEN_FAIL)
    return Case(name, value_insns + body, expect_exit=PASS_EXIT,
                fail_desc=fail_desc)


CASES = [
    # ── value: -1 must be 64-bit all-ones (ADR-0037 D1) ───────────────
    value_case("UT-1 cmp.ut(0xA,0x14) -> 0xFFFF_FFFF_FFFF_FFFF",
               CMP_UT, 0xA, 0x14, ALL_ONES,
               "cmp.ut -1 not 64-bit all-ones (zero-extended?)"),
    value_case("UT-2 cmp.ut(0x14,0xA) -> 1", CMP_UT, 0x14, 0xA, 1),
    value_case("UT-3 cmp.ut(0xA,0xA) -> 0", CMP_UT, 0xA, 0xA, 0),
    value_case("UT-4 source truncation: cmp.ut(0xFFFFFFFF_0000000A,0x14) -> all-ones",
               CMP_UT, 0xFFFFFFFF0000000A, 0x14, ALL_ONES,
               "cmp.ut compared more than bits[31:0]"),
    value_case("UW-1 cmp.uw(0xA,0x14) -> all-ones", CMP_UW, 0xA, 0x14, ALL_ONES,
               "cmp.uw -1 not 64-bit all-ones"),
    value_case("UW-2 source truncation: cmp.uw(0x1_0000_000A,0x14) -> all-ones",
               CMP_UW, 0x10000000A, 0x14, ALL_ONES,
               "cmp.uw compared more than bits[15:0]"),
    value_case("UW-3 cmp.uw(0xA,0xA) -> 0", CMP_UW, 0xA, 0xA, 0),
    value_case("UB-1 cmp.ub(0xA,0x14) -> all-ones", CMP_UB, 0xA, 0x14, ALL_ONES,
               "cmp.ub -1 not 64-bit all-ones"),
    value_case("UB-2 source truncation: cmp.ub(0x10A,0x14) -> all-ones",
               CMP_UB, 0x10A, 0x14, ALL_ONES,
               "cmp.ub compared more than bits[7:0]"),
    value_case("UB-3 cmp.ub(0x14,0xA) -> 1", CMP_UB, 0x14, 0xA, 1),
    # ── "do not change" guards ────────────────────────────────────────
    value_case("ST-1 cmp.st(0xA,0x14) -> all-ones (signed unchanged)",
               CMP_ST, 0xA, 0x14, ALL_ONES),
    value_case("SW-1 cmp.sw(0xA,0x14) -> all-ones (signed unchanged)",
               CMP_SW, 0xA, 0x14, ALL_ONES),
    value_case("SB-1 cmp.sb(0xA,0x14) -> all-ones (signed unchanged)",
               CMP_SB, 0xA, 0x14, ALL_ONES),
    value_case("UO-1 cmp.uo(0xA,0x14) -> all-ones (unchanged)",
               CMP_UO, 0xA, 0x14, ALL_ONES),

    # ── branch decisions: the real acceptance for ADR-0037 ────────────
    branch_case("BR-UT-1 cmp.ut(0xA,0x14) -> br.n TAKEN",
                CMP_UT, 0xA, 0x14, expect_taken=True,
                fail_desc="br.n not taken after cmp.ut -1 (zero-extended?)"),
    branch_case("BR-UT-2 cmp.ut(0x14,0xA) -> br.n not taken",
                CMP_UT, 0x14, 0xA, expect_taken=False,
                fail_desc="br.n taken after cmp.ut +1"),
    branch_case("BR-UT-3 cmp.ut(0xA,0xA) -> br.n not taken (zero)",
                CMP_UT, 0xA, 0xA, expect_taken=False,
                fail_desc="br.n taken after cmp.ut 0"),
    branch_case("BR-UW-1 cmp.uw(0xA,0x14) -> br.n TAKEN",
                CMP_UW, 0xA, 0x14, expect_taken=True),
    branch_case("BR-UB-1 cmp.ub(0xA,0x14) -> br.n TAKEN",
                CMP_UB, 0xA, 0x14, expect_taken=True),

    # ── controls: the branch cases must discriminate, not be constant ──
    br_only_case("CTL-1 br.n on 0x00000000FFFFFFFF (old pattern) NOT taken",
                 load_imm64_rd(1, 0x00000000FFFFFFFF), expect_taken=False,
                 fail_desc="br.n treated the zero-extended pattern as negative"),
    br_only_case("CTL-2 br.n on hand-built -1 TAKEN",
                 load_imm64_rd(1, ALL_ONES), expect_taken=True,
                 fail_desc="br.n cannot detect a hand-built -1"),
]


# ── Runner ────────────────────────────────────────────────────────────

def run_case(case):
    """Return (ok, details)."""
    code, stderr = run_qemu(build_rom(case.insns))
    ok = code == case.expect_exit
    details = ["exit=0x%02X (expect 0x%02X) %s"
               % (code & 0xFF, case.expect_exit,
                  "OK" if ok else "MISMATCH")]
    if not ok and stderr and code != -1:
        details.append("stderr=%s" % stderr.strip()[:120])
    return ok, details


def selftest():
    """Prove each assertion kind has a reachable FAIL path."""
    os.chdir(_REPO_ROOT)
    print("=" * 78)
    print("QEMU-074t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    checks = []

    # (1) in-guest value assertion: expect the *old* zero-extended pattern for
    #     cmp.ut(0xA,0x14) -> the guest must exit VALUE_FAIL (0x13).
    old = value_case("selftest value", CMP_UT, 0xA, 0x14, 0x00000000FFFFFFFF)
    ok, details = run_case(old)
    checks.append(("value comparison detects a zero-extended -1",
                   ok is False and details[0].startswith("exit=0x13"),
                   details))

    # (2) branch assertion: flip the expected direction -> taken path exits 0,
    #     the case expects NOT_TAKEN_FAIL -> must FAIL.
    flipped = branch_case("selftest branch", CMP_UT, 0xA, 0x14,
                          expect_taken=True)
    flipped.expect_exit = TAKEN_FAIL
    ok, details = run_case(flipped)
    checks.append(("branch direction comparison (wrong expectation rejected)",
                   ok is False, details))

    # (3) exit-code assertion: guest exits 0x33, case expects PASS -> must FAIL.
    bad_exit = Case("selftest exit", semi_exit(0x33), expect_exit=PASS_EXIT)
    ok, details = run_case(bad_exit)
    checks.append(("exit-code comparison (0x33 != 0x00)", ok is False, details))

    # (4) poison path: an unterminated case must not look like PASS.
    unterminated = Case("selftest poison", [fence()], expect_exit=PASS_EXIT)
    ok, details = run_case(unterminated)
    checks.append(("missing exit terminator is not PASS", ok is False, details))

    allok = True
    for name, detected, details in checks:
        allok = allok and detected
        print("  [%s] %s" % ("PASS" if detected else "FAIL", name))
        for d in details:
            print("          %s" % d)
    print("\nSelf-test: %s" % ("PASS" if allok else "FAIL"))
    return 0 if allok else 1


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print("ERROR: %s not found. Run 'make build-qemu' first." % QEMU)
        return 1
    print("=" * 78)
    print("QEMU-074t Min ROM Probe (cmp.{ut,uw,ub} 64-bit result, ADR-0037 D1)")
    print("=" * 78)

    passed = failed = 0
    failed_names = []
    for case in CASES:
        ok, details = run_case(case)
        if ok:
            passed += 1
        else:
            failed += 1
            failed_names.append(case.name)
        print("  [%s] %s" % ("PASS" if ok else "FAIL", case.name))
        for d in details:
            print("          %s" % d)
        if not ok and case.fail_desc:
            print("          -> %s" % case.fail_desc)

    print("-" * 78)
    print("Main: %d/%d passed, %d failed" % (passed, passed + failed, failed))
    if failed_names:
        print("Failed:")
        for n in failed_names:
            print("  - %s" % n)
    print("\nOverall: %s" % ("PASS" if failed == 0 else "FAIL"))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
