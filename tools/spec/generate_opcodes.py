#!/usr/bin/env python3
"""从 SimRISC 0.5.3 规范生成 M1 范围机器可读编码表 contracts/opcodes.yaml。

M1 范围：标量整数 + 地址/内存 RD/RB/RA + 控制流 + 测试机所需系统。
M1 范围外（浮点 RF 全部 / 特权 cfx / LR-SC 原子）保留其编码条目并标
`excluded_m1: true`，解码按 ILLI 处理（`decode: ILLI`）——编码已定义但 M1 不实现，
执行即非法指令；UNDI 仅用于架构显式留空的编码（空白单元格）。

来源：
  - spec/SimRISC-00-指令系统设计.md  （QFC 主表 + 6 个 MISC 子表：编码权威）
  - .tao/knowledge/contract-isa.md   （M1 范围与字段/legality 语义）
"""

import os
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_PATH = os.path.join(REPO_ROOT, "contracts", "opcodes.yaml")


# ────────────────────────────── 字段构造 ──────────────────────────────

def _bank_of(name):
    for prefix in ("rd", "rb", "rf", "ra"):
        if name.startswith(prefix):
            return prefix
    return "imm"


def _field(name, bits, role, bank, signed=None):
    d = {"name": name, "bits": bits, "role": role, "bank": bank}
    if signed is not None:
        d["signed"] = signed
    return d


def R(name, bits, role):
    """寄存器字段。"""
    return _field(name, bits, role, _bank_of(name))


def I(name, bits):
    """立即数字段（signed 由 imms*/immu* 前缀决定）。"""
    return _field(name, bits, "imm", "imm", signed=name.startswith("imms"))


def F_ha():
    return _field("ha", "[23:18]", "minor_op", "imm")


def F_wp():
    return _field("wpN", "[17:16]", "wyde_pos", "imm")


def f_rrrr(a, b, c, d, roles=("dst", "src", "src", "src")):
    return [R(a, "[23:18]", roles[0]), R(b, "[17:12]", roles[1]),
            R(c, "[11:6]", roles[2]), R(d, "[5:0]", roles[3])]


def f_rrii(a, b, imm, roles=("dst", "src")):
    return [R(a, "[23:18]", roles[0]), R(b, "[17:12]", roles[1]),
            I(imm + "_hi", "[11:6]"), I(imm + "_lo", "[5:0]")]


def f_rrri(a, b, c, imm, roles=("dst", "src", "src")):
    return [R(a, "[23:18]", roles[0]), R(b, "[17:12]", roles[1]),
            R(c, "[11:6]", roles[2]), I(imm, "[5:0]")]


def f_riii(a, imm, role="dst"):
    return [R(a, "[23:18]", role), I(imm + "_hi", "[17:12]"),
            I(imm + "_mid", "[11:6]"), I(imm + "_lo", "[5:0]")]


def f_iiii(imm):
    return [I(imm + "_b23_18", "[23:18]"), I(imm + "_b17_12", "[17:12]"),
            I(imm + "_b11_6", "[11:6]"), I(imm + "_b5_0", "[5:0]")]


def f_rwii(a, imm, role="dst"):
    return [R(a, "[23:18]", role), F_wp(), I(imm + "_hi", "[15:12]"),
            I(imm + "_mid", "[11:6]"), I(imm + "_lo", "[5:0]")]


def f_orrr(a, b, c, roles=("dst", "src", "src")):
    return [F_ha(), R(a, "[17:12]", roles[0]), R(b, "[11:6]", roles[1]),
            R(c, "[5:0]", roles[2])]


def f_orri(a, b, imm, roles=("dst", "src")):
    return [F_ha(), R(a, "[17:12]", roles[0]), R(b, "[11:6]", roles[1]),
            I(imm, "[5:0]")]


def f_oiii(imm):
    return [F_ha(), I(imm + "_hi", "[17:12]"), I(imm + "_mid", "[11:6]"),
            I(imm + "_lo", "[5:0]")]


def f_crrr():
    return [_field("cfxcode", "[23:18]", "cfxcode", "imm"),
            _field("cghb", "[17:12]", "cfx_cg", "imm"),
            _field("rchc", "[11:6]", "cfx_rc", "imm"),
            R("rdhd", "[5:0]", "dst")]


def f_crii(imm="immu12"):
    return [_field("cfxcode", "[23:18]", "cfxcode", "imm"),
            R("rbhb", "[17:12]", "src"),
            I(imm + "_hi", "[11:6]"), I(imm + "_lo", "[5:0]")]


def f_ciii(imm):
    return [_field("cfxcode", "[23:18]", "cfxcode", "imm"),
            I(imm + "_hi", "[17:12]"), I(imm + "_mid", "[11:6]"),
            I(imm + "_lo", "[5:0]")]


# ────────────────────────────── 记录构造 ──────────────────────────────

def rec(insn, mnemonic, fmt, op, fields, legality, spec_cite, ha=None, excluded=False):
    """构造一条编码记录。ha 为 None 时为主表指令，否则为 MISC 子表指令。"""
    if ha is None:
        mask, value = 0xFF000000, op << 24
    else:
        mask, value = 0xFFFC0000, (op << 24) | (ha << 18)
    r = {"insn": insn, "mnemonic": mnemonic, "format": fmt, "op": f"0x{op:02X}"}
    if ha is not None:
        r["ha"] = f"0x{ha:02X}"
    r["mask"] = f"0x{mask:08X}"
    r["value"] = f"0x{value:08X}"
    r["fields"] = fields
    r["legality"] = legality
    r["spec_cite"] = spec_cite
    if excluded:
        r["excluded_m1"] = True
        r["decode"] = "ILLI"
    return r


# ────────────────────────────── spec 引用 ──────────────────────────────

S01_LD = "SimRISC-01 §存取RD寄存器"
S01_BLK = "SimRISC-01 §寄存器组之间块赋值"
S01_IMM = "SimRISC-01 §立即数常数赋值：Immediate constant"
S01_CS = "SimRISC-01 §条件赋值：Conditional Assignment"
S01_ADD = "SimRISC-01 §加减操作"
S01_INC = "SimRISC-01 §自增自减"
S01_CMP = "SimRISC-01 §比较操作"
S01_MUL = "SimRISC-01 §乘除操作"
S01_LOG = "SimRISC-01 §Logic operators：逻辑运算"
S01_BIT = "SimRISC-01 §Bit manipulating：位操作指令"

S02_LD = "SimRISC-02 §存取RB寄存器"
S02_RA = "SimRISC-02 §存取RA寄存器"
S02_BLK = "SimRISC-02 §寄存器组之间块赋值"
S02_IMM = "SimRISC-02 §立即数常数赋值：Immediate constant"
S02_ADD = "SimRISC-02 §加减操作"
S02_INC = "SimRISC-02 §自增自减"
S02_CMP = "SimRISC-02 §比较操作"
S02_RELA = "SimRISC-02 §PC相对寻址"
S02_BR = "SimRISC-02 §条件跳转指令"
S02_JMP = "SimRISC-02 §无条件跳转指令"
S02_CALL = "SimRISC-02 §函数调用"
S02_RET = "SimRISC-02 §函数返回"

S04_SWYM = "SimRISC-04 §占位指令"
S04_ILLI = "SimRISC-04 §非法指令"
S04_FENCE = "SimRISC-04 §fence指令"
S04_LRSC = "SimRISC-04 §LR-SC指令"

S00_QFC = "SimRISC-00 §SimRISC QFC"
S00_MISCRF = "SimRISC-00 §MISC-RF指令编码"

# 常见 legality 片段
LEG_RD_DST = "rdha != rd0"
LEG_RB_DST = "rbha != rb0"
LEG_IMMU6 = "immu6 != 0"


def aligned(n):
    return f"aligned({n})"


# ────────────────────────────── 主表指令 ──────────────────────────────

def build_main_table(records):
    # ── 0001-0xxx：RD 单 load（rrii）──
    for op, mnem, align in [
        (0x10, "ld.ub", None), (0x11, "ld.uw", 2), (0x12, "ld.ut", 4),
        (0x13, "ld.sb", None), (0x14, "ld.sw", 2), (0x15, "ld.st", 4),
    ]:
        leg = [LEG_RD_DST]
        if align:
            leg.append(aligned(align))
        records.append(rec(f"{mnem}-rd", mnem, "rrii", op,
                           f_rrii("rdha", "rbhb", "imms12"), leg, S01_LD))

    # ── 0001-0xxx 末：RF load/store（excluded）──
    records.append(rec("ld.t-rf", "ld.t", "rrii", 0x16,
                       f_rrii("rfha", "rbhb", "imms12"), [], S00_QFC, excluded=True))
    records.append(rec("st.t-rf", "st.t", "rrii", 0x17,
                       f_rrii("rfha", "rbhb", "imms12", roles=("src", "src")), [],
                       S00_QFC, excluded=True))

    # ── 0001-1xxx：RD 单 store（rrii）──
    for op, mnem, align in [(0x18, "st.b", None), (0x19, "st.w", 2), (0x1A, "st.t", 4)]:
        leg = [LEG_RD_DST]
        if align:
            leg.append(aligned(align))
        records.append(rec(f"{mnem}-rd", mnem, "rrii", op,
                           f_rrii("rdha", "rbhb", "imms12", roles=("src", "src")),
                           leg, S01_LD))

    # ── 0010-0xxx：o load/store RD/RB/RA + RF（excluded）──
    records.append(rec("ld.o-rd", "ld.o", "rrii", 0x20,
                       f_rrii("rdha", "rbhb", "imms12"),
                       [LEG_RD_DST, aligned(8)], S01_LD))
    records.append(rec("st.o-rd", "st.o", "rrii", 0x21,
                       f_rrii("rdha", "rbhb", "imms12", roles=("src", "src")),
                       [LEG_RD_DST, aligned(8)], S01_LD))
    records.append(rec("ld.o-rb", "ld.o", "rrii", 0x22,
                       f_rrii("rbha", "rbhb", "imms12"),
                       [LEG_RB_DST, aligned(8)], S02_LD))
    records.append(rec("st.o-rb", "st.o", "rrii", 0x23,
                       f_rrii("rbha", "rbhb", "imms12", roles=("src", "src")),
                       [LEG_RB_DST, aligned(8)], S02_LD))
    records.append(rec("ld.o-ra", "ld.o", "rrii", 0x24,
                       f_rrii("raha", "rbhb", "imms12"),
                       [aligned(8)], S02_RA))
    records.append(rec("st.o-ra", "st.o", "rrii", 0x25,
                       f_rrii("raha", "rbhb", "imms12", roles=("src", "src")),
                       [aligned(8)], S02_RA))
    records.append(rec("ld.o-rf", "ld.o", "rrii", 0x26,
                       f_rrii("rfha", "rbhb", "imms12"), [], S00_QFC, excluded=True))
    records.append(rec("st.o-rf", "st.o", "rrii", 0x27,
                       f_rrii("rfha", "rbhb", "imms12", roles=("src", "src")), [],
                       S00_QFC, excluded=True))

    # ── 0010-1xxx：RD 多 load（rrri）──
    for op, mnem, align in [
        (0x28, "ldm.ub", None), (0x29, "ldm.uw", 2), (0x2A, "ldm.ut", 4),
        (0x2B, "ldm.sb", None), (0x2C, "ldm.sw", 2), (0x2D, "ldm.st", 4),
    ]:
        leg = [LEG_RD_DST, LEG_IMMU6, "rdha + immu6 <= 64"]
        if align:
            leg.append(aligned(align))
        records.append(rec(f"{mnem}-rd", mnem, "rrri", op,
                           f_rrri("rdha", "rbhb", "rdhc", "immu6"), leg, S01_LD))
    records.append(rec("ldm.t-rf", "ldm.t", "rrri", 0x2E,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6"), [],
                       S00_QFC, excluded=True))
    records.append(rec("stm.t-rf", "stm.t", "rrri", 0x2F,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6", roles=("src", "src", "src")),
                       [], S00_QFC, excluded=True))

    # ── 0011-0xxx：RD 多 store（rrri）──
    for op, mnem, align in [(0x30, "stm.b", None), (0x31, "stm.w", 2), (0x32, "stm.t", 4)]:
        leg = [LEG_RD_DST, LEG_IMMU6, "rdha + immu6 <= 64"]
        if align:
            leg.append(aligned(align))
        records.append(rec(f"{mnem}-rd", mnem, "rrri", op,
                           f_rrri("rdha", "rbhb", "rdhc", "immu6",
                                  roles=("src", "src", "src")), leg, S01_LD))

    # ── 0011-1xxx：o 多 load/store RD/RB/RA + RF（excluded）──
    records.append(rec("ldm.o-rd", "ldm.o", "rrri", 0x38,
                       f_rrri("rdha", "rbhb", "rdhc", "immu6"),
                       [LEG_RD_DST, LEG_IMMU6, "rdha + immu6 <= 64", aligned(8)], S01_LD))
    records.append(rec("stm.o-rd", "stm.o", "rrri", 0x39,
                       f_rrri("rdha", "rbhb", "rdhc", "immu6",
                              roles=("src", "src", "src")),
                       [LEG_RD_DST, LEG_IMMU6, "rdha + immu6 <= 64", aligned(8)], S01_LD))
    records.append(rec("ldm.o-rb", "ldm.o", "rrri", 0x3A,
                       f_rrri("rbha", "rbhb", "rdhc", "immu6"),
                       [LEG_RB_DST, LEG_IMMU6, "rbha + immu6 <= 64", aligned(8)], S02_LD))
    records.append(rec("stm.o-rb", "stm.o", "rrri", 0x3B,
                       f_rrri("rbha", "rbhb", "rdhc", "immu6",
                              roles=("src", "src", "src")),
                       [LEG_RB_DST, LEG_IMMU6, "rbha + immu6 <= 64", aligned(8)], S02_LD))
    records.append(rec("ldm.o-ra", "ldm.o", "rrri", 0x3C,
                       f_rrri("raha", "rbhb", "rdhc", "immu6"),
                       [LEG_IMMU6, "raha + immu6 <= 64", aligned(8)], S02_RA))
    records.append(rec("stm.o-ra", "stm.o", "rrri", 0x3D,
                       f_rrri("raha", "rbhb", "rdhc", "immu6",
                              roles=("src", "src", "src")),
                       [LEG_IMMU6, "raha + immu6 <= 64", aligned(8)], S02_RA))
    records.append(rec("ldm.o-rf", "ldm.o", "rrri", 0x3E,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6"), [],
                       S00_QFC, excluded=True))
    records.append(rec("stm.o-rf", "stm.o", "rrri", 0x3F,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6", roles=("src", "src", "src")),
                       [], S00_QFC, excluded=True))

    # ── 0100-1xxx：立即数赋值（rwii）──
    records.append(rec("or.w-rd", "or.w", "rwii", 0x48,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S01_IMM))
    records.append(rec("andn.w-rd", "andn.w", "rwii", 0x49,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S01_IMM))
    records.append(rec("or.w-rb", "or.w", "rwii", 0x4A,
                       f_rwii("rbha", "immu16"), [LEG_RB_DST], S02_IMM))
    records.append(rec("andn.w-rb", "andn.w", "rwii", 0x4B,
                       f_rwii("rbha", "immu16"), [LEG_RB_DST], S02_IMM))
    records.append(rec("set.zw-rd", "set.zw", "rwii", 0x4C,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S01_IMM))
    records.append(rec("set.ow-rd", "set.ow", "rwii", 0x4D,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S01_IMM))
    records.append(rec("set.zw-rb", "set.zw", "rwii", 0x4E,
                       f_rwii("rbha", "immu16"), [LEG_RB_DST], S02_IMM))
    records.append(rec("set.w-rf", "set.w", "rwii", 0x4F,
                       f_rwii("rfha", "immu16"), [], S00_QFC, excluded=True))

    # ── 0101-0xxx：加减乘（rrrr，双目的）──
    dual_leg = ["!(rdha == rd0 && rdhb == rd0)", "!(rdha == rdhb && rdha != rd0)"]
    for op, mnem, cite in [
        (0x50, "add.uo", S01_ADD), (0x51, "add.so", S01_ADD),
        (0x52, "sub.uo", S01_ADD), (0x53, "sub.so", S01_ADD),
        (0x54, "mul.uo", S01_MUL), (0x55, "mul.so", S01_MUL),
    ]:
        records.append(rec(f"{mnem}-rd", mnem, "rrrr", op,
                           f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                                  roles=("dst", "dst", "src", "src")),
                           dual_leg, cite))
    records.append(rec("ftmadd", "ftmadd", "rrrr", 0x56,
                       f_rrrr("rfha", "rfhb", "rfhc", "rfhd"), [],
                       S00_QFC, excluded=True))
    records.append(rec("fomadd", "fomadd", "rrrr", 0x57,
                       f_rrrr("rfha", "rfhb", "rfhc", "rfhd"), [],
                       S00_QFC, excluded=True))

    # ── 0101-1xxx：自增/相对/比较 ──
    records.append(rec("add.si-rd", "add.si", "riii", 0x59,
                       f_riii("rdha", "imms18"), [LEG_RD_DST], S01_INC))
    records.append(rec("rela.si-rb", "rela.si", "riii", 0x5A,
                       f_riii("rbha", "imms18"), [LEG_RB_DST], S02_RELA))
    records.append(rec("add.si-rb", "add.si", "riii", 0x5B,
                       f_riii("rbha", "imms18"), [LEG_RB_DST], S02_INC))
    records.append(rec("cmp.ui-rd", "cmp.ui", "rrii", 0x5C,
                       f_rrii("rdha", "rdhb", "immu12"), [LEG_RD_DST], S01_CMP))
    records.append(rec("cmp.si-rd", "cmp.si", "rrii", 0x5D,
                       f_rrii("rdha", "rdhb", "imms12"), [LEG_RD_DST], S01_CMP))
    records.append(rec("cs.eq-rf", "cs.eq", "rrrr", 0x5E,
                       f_rrrr("rdha", "rdhb", "rfhc", "rfhd",
                              roles=("src", "src", "dst", "src")), [],
                       S00_QFC, excluded=True))
    records.append(rec("cs.ne-rf", "cs.ne", "rrrr", 0x5F,
                       f_rrrr("rdha", "rdhb", "rfhc", "rfhd",
                              roles=("src", "src", "dst", "src")), [],
                       S00_QFC, excluded=True))

    # ── 0110-0xxx：条件赋值（rrrr）──
    records.append(rec("cs.n-rd", "cs.n", "rrrr", 0x60,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "dst", "src", "src")),
                       ["rdhb != rd0"], S01_CS))
    records.append(rec("cs.n-rf", "cs.n", "rrrr", 0x61,
                       f_rrrr("rdha", "rfhb", "rfhc", "rfhd",
                              roles=("src", "dst", "src", "src")), [],
                       S00_QFC, excluded=True))
    records.append(rec("cs.z-rd", "cs.z", "rrrr", 0x62,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "dst", "src", "src")),
                       ["rdhb != rd0"], S01_CS))
    records.append(rec("cs.z-rf", "cs.z", "rrrr", 0x63,
                       f_rrrr("rdha", "rfhb", "rfhc", "rfhd",
                              roles=("src", "dst", "src", "src")), [],
                       S00_QFC, excluded=True))
    records.append(rec("cs.p-rd", "cs.p", "rrrr", 0x64,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "dst", "src", "src")),
                       ["rdhb != rd0"], S01_CS))
    records.append(rec("cs.p-rf", "cs.p", "rrrr", 0x65,
                       f_rrrr("rdha", "rfhb", "rfhc", "rfhd",
                              roles=("src", "dst", "src", "src")), [],
                       S00_QFC, excluded=True))
    records.append(rec("cs.eq-rd", "cs.eq", "rrrr", 0x66,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "src", "dst", "src")),
                       ["rdhc != rd0"], S01_CS))
    records.append(rec("cs.ne-rd", "cs.ne", "rrrr", 0x67,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "src", "dst", "src")),
                       ["rdhc != rd0"], S01_CS))

    # ── 0110-1xxx：条件跳转（rd）──
    for op, mnem in [(0x68, "br.n"), (0x69, "br.nn"), (0x6A, "br.z"),
                     (0x6B, "br.nz"), (0x6C, "br.p"), (0x6D, "br.np")]:
        records.append(rec(f"{mnem}-rd", mnem, "riii", op,
                           f_riii("rdha", "imms18", role="src"), [], S02_BR))
    for op, mnem in [(0x6E, "br.eq"), (0x6F, "br.ne")]:
        records.append(rec(f"{mnem}-rd", mnem, "rrii", op,
                           f_rrii("rdha", "rdhb", "imms12", roles=("src", "src")),
                           [], S02_BR))

    # ── 0111-0xxx：无条件跳转 / 调用 / 返回 / 占位 ──
    records.append(rec("jump-iiii", "jump", "iiii", 0x70,
                       f_iiii("imms24"), [], S02_JMP))
    records.append(rec("jump-rrii", "jump", "rrii", 0x71,
                       f_rrii("rbha", "rdhb", "imms12", roles=("src", "src")),
                       [], S02_JMP))
    records.append(rec("br.z-rb", "br.z", "riii", 0x72,
                       f_riii("rbha", "imms18", role="src"), [], S02_BR))
    records.append(rec("br.nz-rb", "br.nz", "riii", 0x73,
                       f_riii("rbha", "imms18", role="src"), [], S02_BR))
    records.append(rec("call-iiii", "call", "iiii", 0x74,
                       f_iiii("imms24"), [], S02_CALL))
    records.append(rec("call-rrii", "call", "rrii", 0x75,
                       f_rrii("rbha", "rdhb", "imms12", roles=("src", "src")),
                       [], S02_CALL))
    records.append(rec("ret-riii", "ret", "riii", 0x76,
                       f_riii("rdha", "imms18"), [], S02_RET))
    records.append(rec("swym-iiii", "swym", "iiii", 0x77,
                       f_iiii("immu24"), [], S04_SWYM))

    # ── 0111-1xxx：特权 cfx（excluded）──
    records.append(rec("cfx2rd-crrr", "cfx2rd", "crrr", 0x7A,
                       f_crrr(), [], S00_QFC, excluded=True))
    records.append(rec("cfx2rc-crrr", "cfx2rc", "crrr", 0x7B,
                       f_crrr(), [], S00_QFC, excluded=True))
    records.append(rec("cfxld-crii", "cfxld", "crii", 0x7C,
                       f_crii("immu12"), [], S00_QFC, excluded=True))
    records.append(rec("cfxst-crii", "cfxst", "crii", 0x7D,
                       f_crii("immu12"), [], S00_QFC, excluded=True))
    records.append(rec("escape-ciii", "escape", "ciii", 0x7E,
                       f_ciii("imms18"), [], S00_QFC, excluded=True))
    records.append(rec("trap-ciii", "trap", "ciii", 0x7F,
                       f_ciii("immu18"), [], S00_QFC, excluded=True))


# ────────────────────────────── MISC-AMO ──────────────────────────────

def build_misc_amo(records):
    op = 0x00
    records.append(rec("illi", "illi", "oiii", op, f_oiii("immu18"),
                       [], S04_ILLI, ha=0x00))
    records.append(rec("fence", "fence", "oiii", op, f_oiii("immu18"),
                       ["immu18_hi == 0", "immu18_mid == 0", "immu18_lo[5:4] == 0"],
                       S04_FENCE, ha=0x01))
    # spec MISC-AMO 表：行 010-xxx（lr）/ 011-xxx（sc）→ ha 0x10-0x13 / 0x18-0x1B
    for i, mnem in enumerate(["lr_nn.o", "lr_nr.o", "lr_an.o", "lr_ar.o"]):
        records.append(rec(mnem, mnem, "orrr", op,
                           f_orrr("rdhb", "rdhc", "rbhd"), [],
                           S04_LRSC, ha=0x10 + i, excluded=True))
    for i, mnem in enumerate(["sc_nn.o", "sc_nr.o", "sc_an.o", "sc_ar.o"]):
        records.append(rec(mnem, mnem, "orrr", op,
                           f_orrr("rdhb", "rdhc", "rbhd"), [],
                           S04_LRSC, ha=0x18 + i, excluded=True))


# ────────────────────────────── MISC-octa ──────────────────────────────

def build_misc_octa(records):
    op = 0x40
    for i, mnem in enumerate(["and.o", "or.o", "xor.o", "xnor.o"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_LOG, ha=0x08 + i))
    for i, mnem in enumerate(["ext.uo", "ext.so", "shr.uo", "shr.so", "shl.uo"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_BIT, ha=0x10 + i))
    for i, mnem in enumerate(["ext.uo", "ext.so", "shr.uo", "shr.so", "shl.uo"]):
        records.append(rec(mnem, mnem, "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                           ["rdhb != rd0", "immu6 <= 63"], S01_BIT, ha=0x18 + i))
    records.append(rec("add.so-rb", "add.so", "orrr", op,
                       f_orrr("rbhb", "rbhc", "rdhd"), ["rbhb != rb0"],
                       S02_ADD, ha=0x20))
    records.append(rec("sub.so-rb", "sub.so", "orrr", op,
                       f_orrr("rbhb", "rbhc", "rdhd"), ["rbhb != rb0"],
                       S02_ADD, ha=0x28))
    records.append(rec("cmp.uo-rb", "cmp.uo", "orrr", op,
                       f_orrr("rdhb", "rbhc", "rbhd"), ["rdhb != rd0"],
                       S02_CMP, ha=0x29))
    records.append(rec("cmp.uo", "cmp.uo", "orrr", op,
                       f_orrr("rdhb", "rdhc", "rdhd"), ["rdhb != rd0"],
                       S01_CMP, ha=0x2A))
    records.append(rec("cmp.so", "cmp.so", "orrr", op,
                       f_orrr("rdhb", "rdhc", "rdhd"), ["rdhb != rd0"],
                       S01_CMP, ha=0x2B))
    records.append(rec("rd2rd", "rd2rd", "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64", "rdhc + immu6 <= 64"],
                       S01_BLK, ha=0x2C))
    records.append(rec("rd2ra", "rd2ra", "orri", op, f_orri("rahb", "rdhc", "immu6"),
                       [LEG_IMMU6, "rahb + immu6 <= 64", "rdhc + immu6 <= 64"],
                       S02_BLK, ha=0x2D))
    records.append(rec("ra2rd", "ra2rd", "orri", op, f_orri("rdhb", "rahc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64", "rahc + immu6 <= 64"],
                       S02_BLK, ha=0x2E))
    records.append(rec("rb2rb", "rb2rb", "orri", op, f_orri("rbhb", "rbhc", "immu6"),
                       ["rbhb != rb0", LEG_IMMU6, "rbhb + immu6 <= 64", "rbhc + immu6 <= 64"],
                       S02_BLK, ha=0x34))
    records.append(rec("rd2rb", "rd2rb", "orri", op, f_orri("rbhb", "rdhc", "immu6"),
                       ["rbhb != rb0", LEG_IMMU6, "rbhb + immu6 <= 64", "rdhc + immu6 <= 64"],
                       S02_BLK, ha=0x35))
    records.append(rec("rb2rd", "rb2rd", "orri", op, f_orri("rdhb", "rbhc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64", "rbhc + immu6 <= 64"],
                       S02_BLK, ha=0x36))
    for i, mnem in enumerate(["div.uo", "div.so", "rem.uo", "rem.so"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0", "rdhd != 0"], S01_MUL, ha=0x38 + i))
    # RF 块赋值（excluded）
    records.append(rec("rd2rf", "rd2rf", "orri", op, f_orri("rfhb", "rdhc", "immu6"),
                       [], S00_MISCRF, ha=0x3D, excluded=True))
    records.append(rec("rf2rd", "rf2rd", "orri", op, f_orri("rdhb", "rfhc", "immu6"),
                       [], S00_MISCRF, ha=0x3E, excluded=True))


# ────────────────────────────── MISC 固定位宽子表 ──────────────────────────────

def build_misc_fixed_width(records, op, suffix, nbits):
    """suffix: 't'/'w'/'b'；nbits: 31/15/7。"""
    # 逻辑运算 orrr（ha 0x08-0x0B）
    for i, base in enumerate(["and", "or", "xor", "xnor"]):
        mnem = f"{base}.{suffix}"
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_LOG, ha=0x08 + i))
    # ext/shr/shl orrr（ha 0x10-0x14）
    for i, mnem in enumerate([f"ext.u{suffix}", f"ext.s{suffix}",
                              f"shr.u{suffix}", f"shr.s{suffix}",
                              f"shl.u{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_BIT, ha=0x10 + i))
    # ext/shr/shl orri（ha 0x18-0x1C）
    for i, mnem in enumerate([f"ext.u{suffix}", f"ext.s{suffix}",
                              f"shr.u{suffix}", f"shr.s{suffix}",
                              f"shl.u{suffix}"]):
        records.append(rec(mnem, mnem, "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                           ["rdhb != rd0", f"immu6 <= {nbits}"], S01_BIT, ha=0x18 + i))
    # add（ha 0x20-0x21）
    for i, mnem in enumerate([f"add.u{suffix}", f"add.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_ADD, ha=0x20 + i))
    # sub（ha 0x28-0x29）
    for i, mnem in enumerate([f"sub.u{suffix}", f"sub.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_ADD, ha=0x28 + i))
    # cmp（ha 0x2A-0x2B）
    for i, mnem in enumerate([f"cmp.u{suffix}", f"cmp.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_CMP, ha=0x2A + i))
    # mul（ha 0x30-0x31）
    for i, mnem in enumerate([f"mul.u{suffix}", f"mul.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S01_MUL, ha=0x30 + i))
    # div/rem（ha 0x38-0x3B）
    for i, mnem in enumerate([f"div.u{suffix}", f"div.s{suffix}",
                              f"rem.u{suffix}", f"rem.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0", "rdhd != 0"], S01_MUL, ha=0x38 + i))


# ────────────────────────────── MISC-RF（全 excluded）──────────────────────────────

def build_misc_rf(records):
    op = 0x44
    # orri 单目/格式转换类（rf -> rd 或 rd -> rf）
    orri_entries = [
        (0x00, "ftcls", "rdhb", "rfhc"),
        (0x01, "ft2fo", "rfhb", "rfhc"),
        (0x02, "ft2ft", "rfhb", "rfhc"),
        (0x06, "ftroot", "rfhb", "rfhc"),
        (0x07, "ftlog", "rfhb", "rfhc"),
        (0x08, "focls", "rdhb", "rfhc"),
        (0x09, "fo2ft", "rfhb", "rfhc"),
        (0x0A, "fo2fo", "rfhb", "rfhc"),
        (0x0E, "foroot", "rfhb", "rfhc"),
        (0x0F, "folog", "rfhb", "rfhc"),
        (0x30, "ft2it", "rdhb", "rfhc"),
        (0x31, "ft2io", "rdhb", "rfhc"),
        (0x32, "ft2ut", "rdhb", "rfhc"),
        (0x33, "ft2uo", "rdhb", "rfhc"),
        (0x34, "it2ft", "rfhb", "rdhc"),
        (0x35, "io2ft", "rfhb", "rdhc"),
        (0x36, "ut2ft", "rfhb", "rdhc"),
        (0x37, "uo2ft", "rfhb", "rdhc"),
        (0x38, "fo2it", "rdhb", "rfhc"),
        (0x39, "fo2io", "rdhb", "rfhc"),
        (0x3A, "fo2ut", "rdhb", "rfhc"),
        (0x3B, "fo2uo", "rdhb", "rfhc"),
        (0x3C, "it2fo", "rfhb", "rdhc"),
        (0x3D, "io2fo", "rfhb", "rdhc"),
        (0x3E, "ut2fo", "rfhb", "rdhc"),
        (0x3F, "uo2fo", "rfhb", "rdhc"),
    ]
    for ha, mnem, dst, src in orri_entries:
        records.append(rec(mnem, mnem, "orri", op, f_orri(dst, src, "immu6"),
                           [], S00_MISCRF, ha=ha, excluded=True))
    # orrr 双目运算/比较类
    orrr_entries = [
        (0x10, "ftadd"), (0x11, "ftsub"), (0x12, "ftmul"), (0x13, "ftdiv"),
        (0x14, "ftrem"), (0x15, "ftsclb"), (0x16, "ftsgnn"), (0x17, "ftsgnj"),
        (0x18, "foadd"), (0x19, "fosub"), (0x1A, "fomul"), (0x1B, "fodiv"),
        (0x1C, "forem"), (0x1D, "fosclb"), (0x1E, "fosgnn"), (0x1F, "fosgnj"),
    ]
    for ha, mnem in orrr_entries:
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rfhb", "rfhc", "rfhd"),
                           [], S00_MISCRF, ha=ha, excluded=True))
    # 比较类：目的为 rd
    cmp_entries = [(0x20, "ftqcmp"), (0x21, "ftscmp"), (0x28, "foqcmp"), (0x29, "foscmp")]
    for ha, mnem in cmp_entries:
        records.append(rec(mnem, mnem, "orrr", op,
                           f_orrr("rdhb", "rfhc", "rfhd"), [],
                           S00_MISCRF, ha=ha, excluded=True))


# ────────────────────────────── 主流程 ──────────────────────────────

def main():
    records = []
    build_main_table(records)
    build_misc_amo(records)
    build_misc_octa(records)
    build_misc_fixed_width(records, 0x41, "t", 31)
    build_misc_fixed_width(records, 0x42, "w", 15)
    build_misc_fixed_width(records, 0x43, "b", 7)
    build_misc_rf(records)

    n_m1 = sum(1 for r in records if not r.get("excluded_m1"))
    n_ex = len(records) - n_m1

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# SimRISC 0.5.3 指令编码表（M1 范围）\n")
        f.write("# 自动生成自 spec/SimRISC-00（QFC 主表 + MISC 子表）与 .tao/knowledge/contract-isa.md\n")
        f.write("# M1：标量整数 + 地址/内存 RD/RB/RA + 控制流 + 测试机所需系统\n")
        f.write("# excluded_m1: true 的条目属 M1 范围外（浮点 RF / 特权 cfx / LR-SC），\n")
        f.write("#   M1 不实现但编码已定义 → ILLI（decode: ILLI）；UNDI 仅用于空白单元格\n")
        f.write(f"# 共 {len(records)} 条：M1 内 {n_m1} 条，excluded_m1 {n_ex} 条\n\n")
        yaml.dump(records, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"生成完成：{len(records)} 条（M1 内 {n_m1}，excluded_m1 {n_ex}）-> {OUT_PATH}")


if __name__ == "__main__":
    main()
