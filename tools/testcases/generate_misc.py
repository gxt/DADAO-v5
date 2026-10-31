#!/usr/bin/env python3
"""Generate misc.yaml test vectors for TESTCASES-007t.

Covers the M1 identities in tests/inst/base/misc.yaml:
  - swym_oiii_imm (oiii): encoding + semantic (nop-like, no architectural state change)
  - escape_ciii_cfx (ciii): legality — `imms18[17:1]` is SBZ; non-zero ⇒ ILLI
    (escape legal offsets are 0/+4).  QEMU-side execution of the legal offsets
    is covered by the arch probes (`min_rom_probe_integ044t.py` escape_return,
    `tests/arch/umon/m5_trap_escape.s`): a standalone inst vector starts with
    no valid exception frame, so `escape` would raise CFXESC before the offset
    could be observed.

Spec-first: all encoding words, expected values, and spec_cite derived from
contracts/opcodes.yaml, .tao/contracts/contract-isa.md §13,
contracts/legality_rules.yaml (encode_sbz rule), and
.tao/adr/adr-0004-test-machine.md.

Encoding derivations（**不写死编码**，现场取自 `contracts/opcodes.yaml`）:
  - swym 0: word = `swym_oiii_imm` 的 `value`（immu18 = 0）
    mask=0xFFFC0000 → (value & mask) == value ✓

Note: 原专门非法指令已于 ADR-0012 D3.5 删除（ILLI 异常保留）；
fence 现为 `scope: m9`（SPEC-164t 由 excluded 转入，已实现）。

Output: tests/inst/base/misc.yaml（默认：渲染 + 写盘）。
Check:  python3 tools/testcases/generate_misc.py --check
        （只读：重渲染后与磁盘逐字节比，不一致/缺失 ⇒ rc=1，不写盘）
"""

import argparse
import os
import re
import sys

import yaml

# REPO derived from this file's location (tools/testcases/generate_misc.py)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO, "tests", "inst", "base")
OUT_FILE = os.path.join(OUT_DIR, "misc.yaml")
OPCODES = os.path.join(REPO, "contracts", "opcodes.yaml")

# Harness primitives (single source of truth for the inst test-binary layout).
sys.path.insert(0, os.path.join(REPO, "tools", "testcases", "lib"))
from build_test_binary import (  # noqa: E402
    BINARY_BASE, emit_load_imm64_rd, encode_illi_poison,
)

GENERATOR_PATH = "tools/testcases/generate_misc.py"


def _int(v):
    return v if isinstance(v, int) else int(str(v).strip(), 0)


_BITS_RE = re.compile(r"^\[(\d+):(\d+)\]$")


def _enc(record_id, **fields):
    """Encode a record from contracts/opcodes.yaml (value + field placements).

    `fields` are opcodes.yaml field names (e.g. cfxha / cghb / rchc / rdhd /
    imms18 / immu18 / imms24).  Bit positions come from the record itself, so
    the generator never repeats the encoding layout.
    """
    rec = next(r for r in _load_records() if r["id"] == record_id)
    word = _int(rec["value"])
    by_name = {f["name"]: f for f in rec["fields"]}
    for name, value in fields.items():
        hi, lo = (int(x) for x in _BITS_RE.match(by_name[name]["bits"]).groups())
        word |= (value & ((1 << (hi - lo + 1)) - 1)) << lo
    return word


def _cfx2rc(cfxha, cg, rc, rd):
    return _enc("cfx2rc_crrr_cfx", cfxha=cfxha, cghb=cg, rchc=rc, rdhd=rd)


def _escape(cfxha, imms18):
    return _enc("escape_ciii_cfx", cfxha=cfxha, imms18=imms18)


def _cfx2rd(cfxha, cg, rc, rd):
    return _enc("cfx2rd_crrr_cfx", cfxha=cfxha, cghb=cg, rchc=rc, rdhd=rd)


def _xor_o(dst, a, b):
    return _enc("xor.o_orrr_rd", rdhb=dst, rdhc=a, rdhd=b)


def _br_nz(rd, imms18):
    return _enc("br.nz_riii_rd", rdha=rd, imms18=imms18)


def _illegal_escape_sequence(imms18):
    """Sequence that makes an illegal escape observable as ILLI in the inst harness.

    The harness starts in cfx_power (cfx63, HYPV) with no exception frame, so a
    bare `escape` faults into a monitor vector that is unset => the host would
    see CFXMEM instead of ILLI.  HYPV's monitor is cfx_hmon (cfx3); install a
    discriminator as cfx3's HYPV vector:

      preamble : cfx3.hypv.vector = HANDLER
      BODY     : escape cfx63, <illegal imms18>
      HANDLER  : rd30 = cfx3 cause_id; if rd30 != ILLI -> UNDI word
                 fallthrough: static-ILLI poison word (0x88)

    Legal escape (0/+4) never reaches here.  With the SBZ check present the
    illegal imms18 raises ILLI (cause 0x100) into cfx3 and HANDLER exits 0x88
    (the expected fault).  With the check removed the escape falls through to
    the cfxha/frame check (no frame) => CFXESC into cfx63, whose vector is
    unset => CFXMEM (0x81), so the expected-ILLI case FAILs.
    """
    def addr(i):
        return BINARY_BASE + 4 * i

    # Layout: preamble[0..2], escape[3], HANDLER[4..9], exit section[10...].
    preamble = (emit_load_imm64_rd(22, addr(4))
                + [_cfx2rc(3, 3, 10, 22)])
    body = [_escape(63, imms18)]
    handler = [
        _cfx2rd(3, 5, 2, 30),            # cfx3 cause_id -> rd30
        _enc("set.zw_rwii_rd", rdha=31, wpN=0, immu16=0x0100),  # ILLI one-hot
        _xor_o(30, 30, 31),              # 0 iff cause == ILLI
        _br_nz(30, 2),                   # non-ILLI -> UNDI word (index 9)
        encode_illi_poison(),            # index 8: ILLI path => exit 0x88
        0x00000000,                      # index 9: reserved word => UNDI 0x89
    ]
    seq = preamble + body + handler
    assert len(preamble) == 3, len(preamble)
    assert len(seq) == 10, len(seq)
    return seq


def _load_records():
    with open(OPCODES, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _swym_encoding():
    """从 opcodes.yaml 现场取 swym 的 mask/value（swym 0 即 value 本身）。"""
    rec = next(r for r in _load_records() if r["id"] == "swym_oiii_imm")
    mask = _int(rec["mask"])
    value = _int(rec["value"])
    word = value  # immu18 = 0
    return word, mask, value


def _escape_encoding():
    """从 opcodes.yaml 现场取 escape 的 mask/value（cfxha=0、imms18=0）。"""
    rec = next(r for r in _load_records() if r["id"] == "escape_ciii_cfx")
    mask = _int(rec["mask"])
    value = _int(rec["value"])
    return mask, value


# ── Encoding words（现场派生；SPEC-164t：OPC-MISC 迁 op 0x47）──────────
SWYM_WORD0, MASK_SWYM, VALUE_SWYM = _swym_encoding()
MASK_ESCAPE, VALUE_ESCAPE = _escape_encoding()


def _hex8(w):
    return "0x%08X" % w


def _verify(word, mask, value):
    assert (word & mask) == value, \
        "encoding verification failed: (0x%08X & 0x%08X) != 0x%08X" % (word, mask, value)


# Verify all encodings before generating
_verify(SWYM_WORD0, MASK_SWYM, VALUE_SWYM)


# escape 非法 imms18（SBZ 违规）：imms18[17:1] != 0 ⇒ ILLI。
# 合法偏移 0/+4 对应 imms18 = 0/1；下列值均落在已定义编码 + 非法字段。
ESCAPE_ILLEGAL_IMMS18 = (
    (0x2, "imms18[1] set"),
    (0x3, "imms18[1:0] = 2'b11"),
    (0x3FFFE, "negative-offset encoding (imms18 sign bit set)"),
    (0x1FFFF, "max 18-bit value"),
)


def _case(mnemonic, insn, fmt, cls, word, input_state, expected_state,
          expected_fault=None, expected_pc=None, spec_cite="", notes="",
          status="active", deferred_reason=None, sequence=None):
    case = {
        "mnemonic": mnemonic,
        "id": insn,
        "format": fmt,
        "class": cls,
        "encoding": {"word": _hex8(word)},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": expected_pc,
        "expected_fault": expected_fault,
        "status": status,
        "deferred_reason": deferred_reason,
        "spec_cite": spec_cite,
        "notes": notes,
    }
    if sequence is not None:
        case["sequence"] = [_hex8(w) for w in sequence]
    return case


def generate():
    cases = []

    # ── swym_oiii_imm ─────────────────────────────────────────────────────
    # F10: encoding case — word matches mask/value, decodable, no fault
    cases.append(_case(
        mnemonic="swym",
        insn="swym_oiii_imm",
        fmt="oiii",
        cls="encoding",
        word=SWYM_WORD0,
        input_state={},
        expected_state=None,
        expected_fault=None,
        expected_pc=None,
        spec_cite="SimRISC-12: 空转指令",
        notes="encoding: swym 0 (nop), word=%s; "
              "opcodes.yaml mask=0x%08X value=0x%08X; "
              "no fault, no architectural state change"
              % (_hex8(SWYM_WORD0), MASK_SWYM, VALUE_SWYM),
    ))

    # F10: semantic case — nop-like, no state change
    cases.append(_case(
        mnemonic="swym",
        insn="swym_oiii_imm",
        fmt="oiii",
        cls="semantic",
        word=SWYM_WORD0,
        input_state={},
        expected_state={},
        expected_fault=None,
        expected_pc=None,
        spec_cite="SimRISC-12: 空转指令",
        notes="semantic: swym 0 (nop); "
              "除 PC 自增外无任何架构副作用（§7.1）; "
              "expected_state={}: no registers/memory changed",
    ))

    # ── escape_ciii_cfx：非法 imms18[17:1] ⇒ ILLI（SPEC-180t）────────────
    for imms18, why in ESCAPE_ILLEGAL_IMMS18:
        # Executed inside the cfx0 handler (valid frame); cfxha=63 is a target
        # mismatch, so with the SBZ check removed the contrast path is CFXESC.
        word = _escape(63, imms18)
        _verify(word, MASK_ESCAPE, VALUE_ESCAPE)
        cases.append(_case(
            mnemonic="escape",
            insn="escape_ciii_cfx",
            fmt="ciii",
            cls="legality",
            word=word,
            input_state={},
            expected_state=None,
            expected_fault="ILLI",
            expected_pc=None,
            spec_cite="SimRISC-11: escape",
            notes="legality: cfxha=63 (current cfx is cfx0), imms18=0x%X (%s); imms18[17:1] != 0 (SBZ) => "
                  "ILLI; legal offsets are 0/+4. Sequence installs a cause_id "
                  "discriminator as cfx3's HYPV monitor vector so monitor-entry "
                  "ILLI is observable (non-ILLI exits via UNDI/CFXMEM)."
                  % (imms18, why),
            sequence=_illegal_escape_sequence(imms18),
        ))

    # ── 原专门非法指令已于 ADR-0012 D3.5 删除（ILLI 异常保留）→ 不再产该向量 ──

    return cases


def _render(cases):
    """渲染 misc.yaml 的完整内容（写盘与 --check 共用，保证同源）。"""
    header = (
        "# Generated by %s — DO NOT EDIT\n"
        "# Source: contracts/opcodes.yaml + contract-isa.md §13 "
        "+ legality_rules.yaml (encode_sbz)\n"
        "# Each case has spec_cite and notes for traceability.\n"
        "# Covers: swym_oiii_imm (oiii) encoding+semantic; "
        "escape_ciii_cfx (ciii) legality (imms18[17:1] SBZ => ILLI)\n"
        "# ADR-0012 D3.5: 原专门非法指令删除（ILLI 异常保留）→ 无对应向量\n"
        "# F10: swym encoding words verified against opcodes.yaml mask/value\n"
        "# Note: fence is scope: m9 (SPEC-164t; implemented)\n"
    ) % GENERATOR_PATH
    return header + yaml.dump(cases, default_flow_style=False, sort_keys=False,
                              allow_unicode=True, width=120)


def write_yaml(cases):
    """Write misc.yaml with a header pointing to this generator."""
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        f.write(_render(cases))


def _check(cases):
    """只读校验：重渲染并与磁盘逐字节比较；不写盘、不建目录。"""
    rel = os.path.join("tests", "inst", "base", "misc.yaml")
    if not os.path.isfile(OUT_FILE):
        print("FAIL %s: missing" % rel, file=sys.stderr)
        print("generate_misc --check: FAIL", file=sys.stderr)
        return 1
    with open(OUT_FILE) as f:
        have = f.read()
    if have != _render(cases):
        print("FAIL %s: mismatch" % rel, file=sys.stderr)
        print("generate_misc --check: FAIL", file=sys.stderr)
        return 1
    print("generate_misc --check: PASS（1 册 byte-identical）")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="生成 misc 向量；--check 只读校验。")
    ap.add_argument("--check", action="store_true",
                    help="只读：重渲染并与 tests/inst/base/misc.yaml 逐字节比较")
    args = ap.parse_args(argv)

    cases = generate()

    if args.check:
        return _check(cases)

    print("Generated %d cases for misc.yaml:" % len(cases))
    for i, c in enumerate(cases):
        print("  [%d] %s %s %s" % (i, c["id"], c["format"], c["class"]))
    write_yaml(cases)
    print("Written to: %s" % OUT_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
