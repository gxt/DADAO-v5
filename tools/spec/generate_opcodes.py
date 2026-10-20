#!/usr/bin/env python3
"""从 SimRISC 0.5.4 规范生成范围机器可读编码表 contracts/opcodes.yaml。

每条记录带 `scope` 字段（互斥、穷尽，用户裁定 2026-10-03）：
  - `scope: m1`（156 条）——M1 身份（标量整数 + 地址/内存 RD/RB/RA + 控制流 + 测试机所需系统 + 特权 cfx `trap`/`escape`/`cfx2rd`/`cfx2rc`）；
  - `scope: fp`（60 条）——原生浮点范围（RF 存取/搬移/条件赋值 + MISC-RF 运算/转换/比较），
    独立于 M1，**已实现**（LLVM-029t/030t、QEMU-034t–037t）；
  - `scope: excluded`（27 条）——特权 cfx（仅 `cfxld`/`cfxst`）/ LR-SC（24 条，四宽度 ×
    三存储序）/ fence，暂未归类（`SPEC-115t` 已将 `trap`/`escape`/`cfx2rd`/`cfx2rc`
    re-scope 为 `m1`；`ADR-0034` 将 `lr/sc` 由 8 条重排为 24 条）；
  - `scope: m3`（1 条）——M3 CodeGen 新增指令（ADR-0012 D9.1 `sub.o_orrr_dbb`），
    **非 M1 身份**，不要求 M1 向量覆盖；
  - `scope: m8`（7 条）——新增 ISA 指令（ADR-0012 D10 逐块反转 `rev.o`/`rev.t`/`rev.w`/`rev.b`
    + D11 位扫描/计数 `ctlz`/`cttz`/`ctpop`），
    **非 M1 身份**，与里程碑无绑定（用户 2026-10-14：新增指令与里程碑无绑定关系），不要求 M1 向量覆盖。
  - `scope: m9`（8 条）——新增 ISA 指令 `rol.o`/`rol.t`/`rol.w`/`rol.b`（逻辑循环左移，
    `orrr`/`orri` 两种格式；`ADR-0032` `D4`/`SPEC-152t`），**非 M1 身份**，不要求 M1 向量覆盖。
约定 `scope == "excluded"` ⇒ `decode: ILLI`——编码已定义但尚未实现，执行即非法指令；
`m1`/`fp`/`m3`/`m8`/`m9` 不携带 `decode`（已实现或按各自里程碑实现）；UNDI 仅用于架构显式留空的编码（空白单元格）。

来源：
  - spec/SimRISC-00-指令系统设计.md  （QFC 主表 + 6 个 MISC 子表：编码权威）
  - .tao/contracts/contract-isa.md   （M1 范围与字段/legality 语义）
"""

import os
import yaml
from collections import OrderedDict

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


def R(name, bits, role, bank=None):
    """寄存器字段。"""
    return _field(name, bits, role, bank if bank else _bank_of(name))


def I(name, bits):
    """立即数字段（signed 由 imms*/immu* 前缀决定）。"""
    return _field(name, bits, "imm", "imm", signed=name.startswith("imms"))


def F_wp():
    return _field("wpN", "[17:16]", "wyde_pos", "imm")


# ─── 格式字段构造器（ha 不再作为独立 field；orrr/orri/oiii 的 ha 并入 op） ───

def f_rrrr(a, b, c, d, roles=("dst", "src", "src", "src")):
    return [R(a, "[23:18]", roles[0]), R(b, "[17:12]", roles[1]),
            R(c, "[11:6]", roles[2]), R(d, "[5:0]", roles[3])]


def f_rrii(a, b, imm, roles=("dst", "src")):
    return [R(a, "[23:18]", roles[0]), R(b, "[17:12]", roles[1]),
            I(imm, "[11:0]")]


def f_rrri(a, b, c, imm, roles=("dst", "src", "src")):
    return [R(a, "[23:18]", roles[0]), R(b, "[17:12]", roles[1]),
            R(c, "[11:6]", roles[2]), I(imm, "[5:0]")]


def f_riii(a, imm, role="dst"):
    return [R(a, "[23:18]", role), I(imm, "[17:0]")]


def f_iiii(imm):
    return [I(imm, "[23:0]")]


def f_rwii(a, imm, role="dst"):
    return [R(a, "[23:18]", role), F_wp(), I(imm, "[15:0]")]


def f_orrr(a, b, c, roles=("dst", "src", "src")):
    return [R(a, "[17:12]", roles[0]), R(b, "[11:6]", roles[1]),
            R(c, "[5:0]", roles[2])]


def f_orri(a, b, imm, roles=("dst", "src")):
    return [R(a, "[17:12]", roles[0]), R(b, "[11:6]", roles[1]),
            I(imm, "[5:0]")]


def f_oiii(imm):
    return [I(imm, "[17:0]")]


def f_crrr():
    return [_field("cfxha", "[23:18]", "cfxcode", "imm"),
            R("cghb", "[17:12]", "cfx_cg", "rb"),
            R("rchc", "[11:6]", "cfx_rc", "rc"),
            R("rdhd", "[5:0]", "dst", "rd")]


def f_crii(imm="immu12"):
    return [_field("cfxha", "[23:18]", "cfxcode", "imm"),
            R("rbhb", "[17:12]", "src"),
            I(imm, "[11:0]")]


def f_ciii(imm):
    return [_field("cfxha", "[23:18]", "cfxcode", "imm"),
            I(imm, "[17:0]")]


# ────────────────────────────── id 辅助 ──────────────────────────────

_KNOWN_FMTS = frozenset([
    "rrrr", "rrii", "rrri", "riii", "iiii", "rwii",
    "orrr", "orri", "oiii", "crrr", "crii", "ciii",
])

# 特例映射：当 mnemonic 的 "-" 后部分是格式（非寄存器组）时，
# 或无 "-" 且字段推断不适用时，从这里取 feature。
# 键为无 "-" 的基础 mnemonic（如 "call-iiii" → 查 "call"）。
_SPECIAL_IDS = {
    # 控制流
    "call": "ra", "jump": "rb", "ret": "ra",
    # 浮点运算/比较（fo*/ft* 前缀 → rf）
    "ftcls": "rf", "ft2fo": "rf", "ft2ft": "rf", "ftroot": "rf",
    "focls": "rf", "fo2ft": "rf", "fo2fo": "rf", "foroot": "rf",
    "ft2it": "rf", "ft2io": "rf", "ft2ut": "rf", "ft2uo": "rf",
    "it2ft": "rf", "io2ft": "rf", "ut2ft": "rf", "uo2ft": "rf",
    "fo2it": "rf", "fo2io": "rf", "fo2ut": "rf", "fo2uo": "rf",
    "it2fo": "rf", "io2fo": "rf", "ut2fo": "rf", "uo2fo": "rf",
    "ftadd": "rf", "ftsub": "rf", "ftmul": "rf", "ftdiv": "rf",
    "ftrem": "rf", "ftsclb": "rf", "ftsgnn": "rf", "ftsgnj": "rf",
    "foadd": "rf", "fosub": "rf", "fomul": "rf", "fodiv": "rf",
    "forem": "rf", "fosclb": "rf", "fosgnn": "rf", "fosgnj": "rf",
    "ftqcmp": "rf", "ftscmp": "rf", "foqcmp": "rf", "foscmp": "rf",
    # 跨寄存器组复制
    "ra2rd": "ra", "rb2rd": "rb", "rf2rd": "rf",
    # 地址运算（rb 变体，在同名 orrr 指令中排第二）
    "add.so": "rb", "sub.so": "rb",
}


def _get_id(mnemonic, fmt, fields):
    """从 mnemonic 中解析 id：mnemonic_format_feature。"""
    parts = mnemonic.split("-")
    if len(parts) == 2:
        base, after = parts[0], parts[1]
        if after in _KNOWN_FMTS:
            # 格式型后缀（如 swym-oiii、call-iiii）→ 查特例表，否则推断
            feature = _SPECIAL_IDS.get(base, _infer_feature(fields, fmt))
        else:
            feature = after  # 寄存器组后缀（如 ld.ub-rd → rd）
    else:
        base = parts[0]
        feature = _SPECIAL_IDS.get(base, _infer_feature(fields, fmt))
    return f"{base}_{fmt}_{feature}"


def _infer_feature(fields, fmt=None):
    # crrr/crii/ciii 的 feature 始终为 "cfx"
    if fmt in ("crrr", "crii", "ciii"):
        return "cfx"
    if not fields:
        return "imm"
    first = fields[0]
    bank = first.get("bank", "imm")
    if bank in ("rd", "rb", "rf", "ra"):
        return bank
    return "imm"


# ────────────────────────────── 记录构造 ──────────────────────────────

def rec(insn, mnemonic, fmt, op, fields, legality, spec_cite, ha=None, scope="m1"):
    """构造一条编码记录。ha 为 None 时为主表指令，否则为 MISC 子表指令。

    scope ∈ {"m1", "fp", "excluded", "m3", "m8"}（必填语义，缺省 m1）。scope == "excluded" 时附
    `decode: ILLI`（编码已定义但尚未实现）；`m1`/`fp`/`m3`/`m8` 不携带 `decode`。
    对于 orrr/orri/oiii 格式，ha 并入 op（op 变为14位）。
    对于其余格式，ha 作为独立操作数 field（由调用方加入 fields 列表）。
    """
    if ha is None:
        mask, value = 0xFF000000, op << 24
    else:
        # ha 并入 op：op(8位) + ha(6位) = 14位
        mask, value = 0xFFFC0000, (op << 24) | (ha << 18)
    insn_id = _get_id(insn, fmt, fields)
    r = {"id": insn_id, "mnemonic": mnemonic, "format": fmt, "op": f"0x{op:02X}"}
    if ha is not None:
        r["ha"] = f"0x{ha:02X}"
    r["mask"] = f"0x{mask:08X}"
    r["value"] = f"0x{value:08X}"
    r["fields"] = fields
    r["legality"] = legality
    r["spec_cite"] = spec_cite
    r["scope"] = scope
    if scope == "excluded":
        r["decode"] = "ILLI"
    return r


# ────────────────────────────── spec 引用 ──────────────────────────────

# 存储（SimRISC-01）
S01_LD = "SimRISC-01 §存取RD寄存器"
S01_RB_LD = "SimRISC-01 §存取RB寄存器"
S01_RA_LD = "SimRISC-01 §存取RA寄存器"

# 寄存器复制（SimRISC-02）
S02_BLK = "SimRISC-02 §寄存器组之间块赋值"
S02_CS = "SimRISC-02 §条件赋值：Conditional Assignment"

# 16位立即数操作（SimRISC-03）
S03_IMM = "SimRISC-03 §立即数常数赋值：Immediate constant"

# 64位数据运算（SimRISC-04）
S04_ADD = "SimRISC-04 §加减操作"
S04_INC = "SimRISC-04 §自增自减"
S04_CMP = "SimRISC-04 §比较操作"
S04_MUL = "SimRISC-04 §乘除操作"
S04_LOG = "SimRISC-04 §Logic operators：逻辑运算"
S04_BIT = "SimRISC-04 §Bit manipulating：位操作指令"

# 64位地址运算（SimRISC-05）
S05_ADD = "SimRISC-05 §加减操作"
S05_INC = "SimRISC-05 §自增自减"
S05_CMP = "SimRISC-05 §比较操作"
# ADR-0029 D1：恢复 aip.si（IP 相对寻址，auipc 式；0x5A 原为 ADR-0012 D5 保留位）
# 指令名 `rela.si` → `aip.si`、正文术语 `PC` → `IP`（用户 2026-10-16 裁定）
S05_PCREL = "SimRISC-05 §IP 相对寻址"

# 控制流（SimRISC-06）
S06_BR = "SimRISC-06 §条件跳转指令"
S06_JMP = "SimRISC-06 §无条件跳转指令"
S06_CALL = "SimRISC-06 §函数调用"
S06_RET = "SimRISC-06 §函数返回"

# 其它（SimRISC-11）
S11_SWYM = "SimRISC-11 §占位指令"

# 待定（SimRISC-12）
S12_FENCE = "SimRISC-12 §fence指令"
S12_LRSC = "SimRISC-12 §LR-SC指令"

# QFC/MISC-RF（SimRISC-00）
S00_QFC = "SimRISC-00 §SimRISC QFC"
S00_MISCRF = "SimRISC-00 §MISC-RF指令编码"

# 常见 legality 片段
LEG_RD_DST = "rdha != rd0"
LEG_RB_DST = "rbha != rb0"
LEG_IMMU6 = "immu6 != 0"
# 仅 ret 适用：rdha == rd0 时 imms18 必须为 0（等价于 !(rdha == rd0 && imms18 != 0)）
LEG_RET_RD0_IMMS18 = "!(rdha == rd0 && imms18 != 0)"


def aligned(n):
    return f"aligned({n})"


def onehot_expr(S):
    """`rev.*`（ADR-0012 D10）的 one-hot 合法集表达式（immu6 的合法档位）。

    合法 `k` = 2 的幂且 `k < S`（排除 `k = S` 恒等档）；`S` = 该后缀的块大小
    （`.o` 64 / `.t` 32 / `.w` 16 / `.b` 8）。表达式只用 `immu6` 一个标识符
    （显式枚举合法档），故 `validate_encoding.py` 的字段引用检查无需豁免函数名。
    """
    vals = [v for v in (1, 2, 4, 8, 16, 32) if v < S]
    return " || ".join(f"immu6 == {v}" for v in vals)


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
                       f_rrii("rfha", "rbhb", "imms12"), [], S00_QFC, scope="fp"))
    records.append(rec("st.t-rf", "st.t", "rrii", 0x17,
                       f_rrii("rfha", "rbhb", "imms12", roles=("src", "src")), [],
                       S00_QFC, scope="fp"))

    # ── 0001-1xxx：RD 单 store（rrii）──
    # 语义变更：st 的 rdha != rd0 已删除（store 的 ha 是源操作数，允许 rd0）
    for op, mnem, align in [(0x18, "st.b", None), (0x19, "st.w", 2), (0x1A, "st.t", 4)]:
        leg = []
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
                       [aligned(8)], S01_LD))
    records.append(rec("ld.o-rb", "ld.o", "rrii", 0x22,
                       f_rrii("rbha", "rbhb", "imms12"),
                       [LEG_RB_DST, aligned(8)], S01_RB_LD))
    records.append(rec("st.o-rb", "st.o", "rrii", 0x23,
                       f_rrii("rbha", "rbhb", "imms12", roles=("src", "src")),
                       [aligned(8)], S01_RB_LD))
    records.append(rec("ld.o-ra", "ld.o", "rrii", 0x24,
                       f_rrii("raha", "rbhb", "imms12"),
                       [aligned(8)], S01_RA_LD))
    records.append(rec("st.o-ra", "st.o", "rrii", 0x25,
                       f_rrii("raha", "rbhb", "imms12", roles=("src", "src")),
                       [aligned(8)], S01_RA_LD))
    records.append(rec("ld.o-rf", "ld.o", "rrii", 0x26,
                       f_rrii("rfha", "rbhb", "imms12"), [], S00_QFC, scope="fp"))
    records.append(rec("st.o-rf", "st.o", "rrii", 0x27,
                       f_rrii("rfha", "rbhb", "imms12", roles=("src", "src")), [],
                       S00_QFC, scope="fp"))

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
                       f_rrri("rfha", "rbhb", "rdhc", "immu6"),
                       [LEG_IMMU6, "rfha + immu6 <= 64"],
                       S00_QFC, scope="fp"))
    records.append(rec("stm.t-rf", "stm.t", "rrri", 0x2F,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6", roles=("src", "src", "src")),
                       [LEG_IMMU6, "rfha + immu6 <= 64"], S00_QFC, scope="fp"))

    # ── 0011-0xxx：RD 多 store（rrri）──
    # 语义变更：stm 的 rdha != rd0 已删除
    for op, mnem, align in [(0x30, "stm.b", None), (0x31, "stm.w", 2), (0x32, "stm.t", 4)]:
        leg = [LEG_IMMU6, "rdha + immu6 <= 64"]
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
                       [LEG_IMMU6, "rdha + immu6 <= 64", aligned(8)], S01_LD))
    records.append(rec("ldm.o-rb", "ldm.o", "rrri", 0x3A,
                       f_rrri("rbha", "rbhb", "rdhc", "immu6"),
                       [LEG_RB_DST, LEG_IMMU6, "rbha + immu6 <= 64", aligned(8)], S01_RB_LD))
    records.append(rec("stm.o-rb", "stm.o", "rrri", 0x3B,
                       f_rrri("rbha", "rbhb", "rdhc", "immu6",
                              roles=("src", "src", "src")),
                       [LEG_IMMU6, "rbha + immu6 <= 64", aligned(8)], S01_RB_LD))
    records.append(rec("ldm.o-ra", "ldm.o", "rrri", 0x3C,
                       f_rrri("raha", "rbhb", "rdhc", "immu6"),
                       [LEG_IMMU6, "raha + immu6 <= 64", aligned(8)], S01_RA_LD))
    records.append(rec("stm.o-ra", "stm.o", "rrri", 0x3D,
                       f_rrri("raha", "rbhb", "rdhc", "immu6",
                              roles=("src", "src", "src")),
                       [LEG_IMMU6, "raha + immu6 <= 64", aligned(8)], S01_RA_LD))
    records.append(rec("ldm.o-rf", "ldm.o", "rrri", 0x3E,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6"),
                       [LEG_IMMU6, "rfha + immu6 <= 64"],
                       S00_QFC, scope="fp"))
    records.append(rec("stm.o-rf", "stm.o", "rrri", 0x3F,
                       f_rrri("rfha", "rbhb", "rdhc", "immu6", roles=("src", "src", "src")),
                       [LEG_IMMU6, "rfha + immu6 <= 64"], S00_QFC, scope="fp"))

    # ── 0100-1xxx：立即数赋值（rwii）──
    records.append(rec("or.w-rd", "or.w", "rwii", 0x48,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S03_IMM))
    records.append(rec("andn.w-rd", "andn.w", "rwii", 0x49,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S03_IMM))
    records.append(rec("or.w-rb", "or.w", "rwii", 0x4A,
                       f_rwii("rbha", "immu16"), [LEG_RB_DST], S03_IMM))
    records.append(rec("andn.w-rb", "andn.w", "rwii", 0x4B,
                       f_rwii("rbha", "immu16"), [LEG_RB_DST], S03_IMM))
    records.append(rec("set.zw-rd", "set.zw", "rwii", 0x4C,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S03_IMM))
    records.append(rec("set.ow-rd", "set.ow", "rwii", 0x4D,
                       f_rwii("rdha", "immu16"), [LEG_RD_DST], S03_IMM))
    records.append(rec("set.zw-rb", "set.zw", "rwii", 0x4E,
                       f_rwii("rbha", "immu16"), [LEG_RB_DST], S03_IMM))
    records.append(rec("set.w-rf", "set.w", "rwii", 0x4F,
                       f_rwii("rfha", "immu16"), [], S00_QFC, scope="fp"))

    # ── 0101-0xxx：加减乘（rrrr，双目的）──
    dual_leg = ["!(rdha == rd0 && rdhb == rd0)", "!(rdha == rdhb && rdha != rd0)"]
    for op, mnem, cite in [
        (0x50, "add.uo", S04_ADD), (0x51, "add.so", S04_ADD),
        (0x52, "sub.uo", S04_ADD), (0x53, "sub.so", S04_ADD),
        (0x54, "mul.uo", S04_MUL), (0x55, "mul.so", S04_MUL),
    ]:
        records.append(rec(f"{mnem}-rd", mnem, "rrrr", op,
                           f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                                  roles=("dst", "dst", "src", "src")),
                           dual_leg, cite))

    # ── 0101-1xxx：自增/相对/比较 ──
    records.append(rec("add.si-rd", "add.si", "riii", 0x59,
                       f_riii("rdha", "imms18"), [LEG_RD_DST], S04_INC))
    # ADR-0029 D1（用户 2026-10-16 授权）：恢复 aip.si（IP 相对寻址）——0x5A 为
    # ADR-0012 D5 保留（不再指派）的编码，故不占新编码位；语义 = rbha = IP + (imms18 << 12)，
    # IP = 该指令自身地址（rb0 读出值，不清低位）；目的 rb0 ⇒ ILLI（dst_rb0）。
    # 指令名 `rela.si` → `aip.si`（用户 2026-10-16 裁定；汇编层操作数按字节写 `imms30`）。
    records.append(rec("aip.si-rb", "aip.si", "riii", 0x5A,
                       f_riii("rbha", "imms18"), [LEG_RB_DST], S05_PCREL))
    records.append(rec("add.si-rb", "add.si", "riii", 0x5B,
                       f_riii("rbha", "imms18"), [LEG_RB_DST], S05_INC))
    records.append(rec("cmp.ui-rd", "cmp.ui", "rrii", 0x5C,
                       f_rrii("rdha", "rdhb", "immu12"), [LEG_RD_DST], S04_CMP))
    records.append(rec("cmp.si-rd", "cmp.si", "rrii", 0x5D,
                       f_rrii("rdha", "rdhb", "imms12"), [LEG_RD_DST], S04_CMP))
    records.append(rec("cs.eq-rf", "cs.eq", "rrrr", 0x5E,
                       f_rrrr("rdha", "rdhb", "rfhc", "rfhd",
                              roles=("src", "src", "dst", "src")),
                       ["rfhc != rf0"], S00_QFC, scope="fp"))
    records.append(rec("cs.ne-rf", "cs.ne", "rrrr", 0x5F,
                       f_rrrr("rdha", "rdhb", "rfhc", "rfhd",
                              roles=("src", "src", "dst", "src")),
                       ["rfhc != rf0"], S00_QFC, scope="fp"))

    # ── 0110-0xxx：条件赋值（rrrr）──
    records.append(rec("cs.n-rd", "cs.n", "rrrr", 0x60,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "dst", "src", "src")),
                       ["rdhb != rd0"], S02_CS))
    records.append(rec("cs.n-rf", "cs.n", "rrrr", 0x61,
                       f_rrrr("rdha", "rfhb", "rfhc", "rfhd",
                              roles=("src", "dst", "src", "src")),
                       ["rfhb != rf0"], S00_QFC, scope="fp"))
    records.append(rec("cs.z-rd", "cs.z", "rrrr", 0x62,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "dst", "src", "src")),
                       ["rdhb != rd0"], S02_CS))
    records.append(rec("cs.z-rf", "cs.z", "rrrr", 0x63,
                       f_rrrr("rdha", "rfhb", "rfhc", "rfhd",
                              roles=("src", "dst", "src", "src")),
                       ["rfhb != rf0"], S00_QFC, scope="fp"))
    records.append(rec("cs.p-rd", "cs.p", "rrrr", 0x64,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "dst", "src", "src")),
                       ["rdhb != rd0"], S02_CS))
    records.append(rec("cs.p-rf", "cs.p", "rrrr", 0x65,
                       f_rrrr("rdha", "rfhb", "rfhc", "rfhd",
                              roles=("src", "dst", "src", "src")),
                       ["rfhb != rf0"], S00_QFC, scope="fp"))
    records.append(rec("cs.eq-rd", "cs.eq", "rrrr", 0x66,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "src", "dst", "src")),
                       ["rdhc != rd0"], S02_CS))
    records.append(rec("cs.ne-rd", "cs.ne", "rrrr", 0x67,
                       f_rrrr("rdha", "rdhb", "rdhc", "rdhd",
                              roles=("src", "src", "dst", "src")),
                       ["rdhc != rd0"], S02_CS))

    # ── 0110-1xxx：条件跳转（rd）──
    for op, mnem in [(0x68, "br.n"), (0x69, "br.nn"), (0x6A, "br.z"),
                     (0x6B, "br.nz"), (0x6C, "br.p"), (0x6D, "br.np")]:
        records.append(rec(f"{mnem}-rd", mnem, "riii", op,
                           f_riii("rdha", "imms18", role="src"), [], S06_BR))
    for op, mnem in [(0x6E, "br.eq"), (0x6F, "br.ne")]:
        records.append(rec(f"{mnem}-rd", mnem, "rrii", op,
                           f_rrii("rdha", "rdhb", "imms12", roles=("src", "src")),
                           [], S06_BR))

    # ── 0111-0xxx：无条件跳转 / 调用 / 返回 / 占位 ──
    records.append(rec("jump-iiii", "jump", "iiii", 0x70,
                       f_iiii("imms24"), [], S06_JMP))
    records.append(rec("jump-rrii", "jump", "rrii", 0x71,
                       f_rrii("rbha", "rdhb", "imms12", roles=("src", "src")),
                       [], S06_JMP))
    records.append(rec("br.z-rb", "br.z", "riii", 0x72,
                       f_riii("rbha", "imms18", role="src"), [], S06_BR))
    records.append(rec("br.nz-rb", "br.nz", "riii", 0x73,
                       f_riii("rbha", "imms18", role="src"), [], S06_BR))
    records.append(rec("call-iiii", "call", "iiii", 0x74,
                       f_iiii("imms24"), [], S06_CALL))
    records.append(rec("call-rrii", "call", "rrii", 0x75,
                       f_rrii("rbha", "rdhb", "imms12", roles=("src", "src")),
                       [], S06_CALL))
    records.append(rec("ret-riii", "ret", "riii", 0x76,
                       f_riii("rdha", "imms18"), [LEG_RET_RD0_IMMS18], S06_RET))

    # ── 0111-1xxx：特权 cfx ──
    # SPEC-115t：trap/escape/cfx2rd/cfx2rc re-scope excluded → m1（已实现，MC 可汇编）。
    # cfxld/cfxst 保持 scope: excluded（SimRISC-12 待定，decode ILLI）。
    records.append(rec("cfx2rd-crrr", "cfx2rd", "crrr", 0x7A,
                       f_crrr(), [], S00_QFC, scope="m1"))
    records.append(rec("cfx2rc-crrr", "cfx2rc", "crrr", 0x7B,
                       f_crrr(), [], S00_QFC, scope="m1"))
    records.append(rec("cfxld-crii", "cfxld", "crii", 0x7C,
                       f_crii("immu12"), [], S00_QFC, scope="excluded"))
    records.append(rec("cfxst-crii", "cfxst", "crii", 0x7D,
                       f_crii("immu12"), [], S00_QFC, scope="excluded"))
    records.append(rec("escape-ciii", "escape", "ciii", 0x7E,
                       f_ciii("imms18"), [], S00_QFC, scope="m1"))
    records.append(rec("trap-ciii", "trap", "ciii", 0x7F,
                       f_ciii("immu18"), [], S00_QFC, scope="m1"))


# ────────────────────────────── MISC-AMO ──────────────────────────────

def build_misc_amo(records):
    op = 0x77
    # ADR-0034 D1/D2（用户 2026-10-20）：fence 由 000-000 迁至 100-000（ha=0x20）；
    # immu18 = fm[17:12] / pred[11:6] / succ[5:0]（书写仍是 18 位无符号立即数，不拆三段）；
    # fm=0 为唯一已定义值，pred/succ 的高 2 位（[11:10]/[5:4]）SBZ ⇒ 其余保留（ILLI）。
    records.append(rec("fence", "fence", "oiii", op, f_oiii("immu18"),
                       ["immu18[17:12] == 0", "immu18[11:10] == 0", "immu18[5:4] == 0"],
                       S12_FENCE, ha=0x20, scope="excluded"))
    # swym：格式从 iiii 改为 oiii，immu24 改为 immu18；位于 MISC-AMO 100-010（ha=0x22）
    records.append(rec("swym-oiii", "swym", "oiii", op, f_oiii("immu18"),
                       [], S11_SWYM, ha=0x22))
    # ADR-0034 D3/D4/D5（方案 A）：命名 `<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>`（宽度在前）；
    # lr 占 000/001 两行（nn/an/ar，`lr.*.nr` 删除）、sc 占 010/011 两行（nn/nr/ar，
    # `sc.*.an` 删除）；组内宽度顺序 .o → .t → .w → .b。scope 仍 excluded（D7）。
    for prefix, order_ha in (("lr", {"nn": 0x00, "an": 0x04, "ar": 0x08}),
                             ("sc", {"nn": 0x10, "nr": 0x14, "ar": 0x18})):
        for order, base_ha in order_ha.items():
            for i, width in enumerate(("o", "t", "w", "b")):
                mnem = f"{prefix}.{width}.{order}"
                records.append(rec(mnem, mnem, "orrr", op,
                                   f_orrr("rdhb", "rdhc", "rbhd"), [],
                                   S12_LRSC, ha=base_ha + i, scope="excluded"))


# ────────────────────────────── MISC-octa ──────────────────────────────

def build_misc_octa(records):
    op = 0x40
    for i, mnem in enumerate(["and.o", "or.o", "xor.o", "xnor.o"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S04_LOG, ha=0x08 + i))
    # ADR-0032 D1/D2/D4（SPEC-152t）：ext 迁至 100-000/001（0x20/0x21）；
    # 移位族 shl(010-000/011-000) / rol(010-001/011-001) / shr.u(010/011-010) / shr.s(010/011-011)。
    # rol 为新增指令（scope: m9），符号无关、不带 u/s 后缀。
    for i, mnem in enumerate(["shl.o", "rol.o", "shr.uo", "shr.so"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S04_BIT, ha=0x10 + i,
                           scope=("m9" if mnem.startswith("rol.") else "m1")))
    for i, mnem in enumerate(["shl.o", "rol.o", "shr.uo", "shr.so"]):
        records.append(rec(mnem, mnem, "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                           ["rdhb != rd0"], S04_BIT, ha=0x18 + i,
                           scope=("m9" if mnem.startswith("rol.") else "m1")))
    for i, mnem in enumerate(["ext.uo", "ext.so"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S04_BIT, ha=0x20 + i))
    for i, mnem in enumerate(["ext.uo", "ext.so"]):
        records.append(rec(mnem, mnem, "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                           ["rdhb != rd0"], S04_BIT, ha=0x28 + i))
    # D9.2/D9.3：orrr 单目的 id 后缀 = 操作数 bank 签名（bbd/dbb）
    records.append(rec("add.o-bbd", "add.o", "orrr", op,
                       f_orrr("rbhb", "rbhc", "rdhd"), ["rbhb != rb0"],
                       S05_ADD, ha=0x30))
    records.append(rec("sub.o-bbd", "sub.o", "orrr", op,
                       f_orrr("rbhb", "rbhc", "rdhd"), ["rbhb != rb0"],
                       S05_ADD, ha=0x31))
    records.append(rec("cmp.uo-dbb", "cmp.uo", "orrr", op,
                       f_orrr("rdhb", "rbhc", "rbhd"), ["rdhb != rd0"],
                       S05_CMP, ha=0x32))
    # D9.1：新增 sub.o rdhb, rbhc, rbhd（RB − RB → RD，orrr，dbb 形态）
    # scope: m3（M3 CodeGen 新增，非 M1 身份，不要求 M1 向量覆盖）
    records.append(rec("sub.o-dbb", "sub.o", "orrr", op,
                       f_orrr("rdhb", "rbhc", "rbhd"), ["rdhb != rd0"],
                       S05_ADD, ha=0x33, scope="m3"))
    records.append(rec("cmp.uo", "cmp.uo", "orrr", op,
                       f_orrr("rdhb", "rdhc", "rdhd"), ["rdhb != rd0"],
                       S04_CMP, ha=0x2A))
    records.append(rec("cmp.so", "cmp.so", "orrr", op,
                       f_orrr("rdhb", "rdhc", "rdhd"), ["rdhb != rd0"],
                       S04_CMP, ha=0x2B))
    # 语义变更：rd2rd 新增 no_overlap
    records.append(rec("rd2rd", "rd2rd", "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64",
                        "rdhc + immu6 <= 64", "no_overlap(rdhb, rdhc, immu6)"],
                       S02_BLK, ha=0x2C))
    records.append(rec("rd2ra", "rd2ra", "orri", op, f_orri("rahb", "rdhc", "immu6"),
                       [LEG_IMMU6, "rahb + immu6 <= 64", "rdhc + immu6 <= 64"],
                       S02_BLK, ha=0x2D))
    records.append(rec("ra2rd", "ra2rd", "orri", op, f_orri("rdhb", "rahc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64", "rahc + immu6 <= 64"],
                       S02_BLK, ha=0x2E))
    # 语义变更：rb2rb 新增 no_overlap
    records.append(rec("rb2rb", "rb2rb", "orri", op, f_orri("rbhb", "rbhc", "immu6"),
                       ["rbhb != rb0", LEG_IMMU6, "rbhb + immu6 <= 64",
                        "rbhc + immu6 <= 64", "no_overlap(rbhb, rbhc, immu6)"],
                       S02_BLK, ha=0x34))
    records.append(rec("rd2rb", "rd2rb", "orri", op, f_orri("rbhb", "rdhc", "immu6"),
                       ["rbhb != rb0", LEG_IMMU6, "rbhb + immu6 <= 64", "rdhc + immu6 <= 64"],
                       S02_BLK, ha=0x35))
    records.append(rec("rb2rd", "rb2rd", "orri", op, f_orri("rdhb", "rbhc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64", "rbhc + immu6 <= 64"],
                       S02_BLK, ha=0x36))
    for i, mnem in enumerate(["div.uo", "div.so", "rem.uo", "rem.so"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], S04_MUL, ha=0x38 + i))
    # RF 块赋值（excluded）
    records.append(rec("rd2rf", "rd2rf", "orri", op, f_orri("rfhb", "rdhc", "immu6"),
                       [LEG_IMMU6, "rfhb + immu6 <= 64", "rdhc + immu6 <= 64"],
                       S00_MISCRF, ha=0x3D, scope="fp"))
    records.append(rec("rf2rd", "rf2rd", "orri", op, f_orri("rdhb", "rfhc", "immu6"),
                       ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64",
                        "rfhc + immu6 <= 64"],
                       S00_MISCRF, ha=0x3E, scope="fp"))
    # ADR-0012 D10：新增 rev.o（逐块反转；orri，ha=0x0C → opx `001-100`）
    # scope: m8（新增 ISA 指令，与里程碑无绑定；非 M1 身份，不要求 M1 向量覆盖）
    records.append(rec("rev.o", "rev.o", "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                       ["rdhb != rd0", onehot_expr(64)], S04_BIT,
                       ha=0x0C, scope="m8"))
    # ADR-0012 D11：新增 ctlz/cttz/ctpop（位扫描 / 位计数；orri，ha=0x1D/0x1E/0x1F →
    # opx `011-101`/`011-110`/`011-111`）。**无位宽后缀** ⇒ 借用 MISC-octa 格位，是
    # 「子表 ⇔ 位宽后缀」规则的**例外**（见 spec/SimRISC-00 §4.2 表下说明）。
    # scope: m8（新增 ISA 指令，与里程碑无绑定；非 M1 身份，不要求 M1 向量覆盖）
    # 合法性：hd ∈ 0..63 全部合法 ⇒ 不新增规则；沿用 dst_rd0（rdhb != rd0）。
    for mnem, ha in (("ctpop", 0x1D), ("ctlz", 0x1E), ("cttz", 0x1F)):
        records.append(rec(mnem, mnem, "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                           ["rdhb != rd0"], S04_BIT, ha=ha, scope="m8"))


# ────────────────────────────── MISC 固定位宽子表 ──────────────────────────────

def build_misc_fixed_width(records, op, suffix, nbits, sdoc):
    """suffix: 't'/'w'/'b'；nbits: 31/15/7；sdoc: 对应 SimRISC 文档（SimRISC-08/09/10）。

    SPEC-069t：窄位宽逻辑（and/or/xor/xnor）与窄位宽扩展（ext）已删除（24 条），
    仅保留 shr/shl（位操作）、add/sub（算术）、cmp（比较）、mul/div/rem（乘除余）。
    """
    cite_add = f"{sdoc} §加减操作"
    cite_cmp = f"{sdoc} §比较操作"
    cite_mul = f"{sdoc} §乘除操作"
    cite_bit = f"{sdoc} §Bit manipulating：位操作指令"
    # shr/shl/rol orrr（ADR-0032 D2/D4：shl 010-000、rol 010-001、shr 010-010/011）
    for i, mnem in enumerate([f"shl.{suffix}", f"rol.{suffix}",
                              f"shr.u{suffix}", f"shr.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], cite_bit, ha=0x10 + i,
                           scope=("m9" if mnem.startswith("rol.") else "m1")))
    # shr/shl/rol orri（同上；immu6 越界 ⇒ ILLI，窄位宽沿用 immu6 <= N）
    for i, mnem in enumerate([f"shl.{suffix}", f"rol.{suffix}",
                              f"shr.u{suffix}", f"shr.s{suffix}"]):
        records.append(rec(mnem, mnem, "orri", op, f_orri("rdhb", "rdhc", "immu6"),
                           ["rdhb != rd0", f"immu6 <= {nbits}"], cite_bit,
                           ha=0x18 + i,
                           scope=("m9" if mnem.startswith("rol.") else "m1")))
    # add（ha 0x20-0x21）
    for i, mnem in enumerate([f"add.u{suffix}", f"add.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], cite_add, ha=0x20 + i))
    # sub（ha 0x28-0x29）
    for i, mnem in enumerate([f"sub.u{suffix}", f"sub.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], cite_add, ha=0x28 + i))
    # cmp（ha 0x2A-0x2B）
    for i, mnem in enumerate([f"cmp.u{suffix}", f"cmp.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], cite_cmp, ha=0x2A + i))
    # mul（ha 0x30-0x31）
    for i, mnem in enumerate([f"mul.u{suffix}", f"mul.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], cite_mul, ha=0x30 + i))
    # div/rem（ha 0x38-0x3B）
    for i, mnem in enumerate([f"div.u{suffix}", f"div.s{suffix}",
                              f"rem.u{suffix}", f"rem.s{suffix}"]):
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rdhb", "rdhc", "rdhd"),
                           ["rdhb != rd0"], cite_mul, ha=0x38 + i))
    # ADR-0012 D10：新增 rev.<suffix>（逐块反转；orri，ha=0x0C → opx `001-100`）
    # scope: m8（新增 ISA 指令，与里程碑无绑定；非 M1 身份，不要求 M1 向量覆盖）
    records.append(rec(f"rev.{suffix}", f"rev.{suffix}", "orri", op,
                       f_orri("rdhb", "rdhc", "immu6"),
                       ["rdhb != rd0", onehot_expr(nbits + 1)], cite_bit,
                       ha=0x0C, scope="m8"))


# ────────────────────────────── MISC-RF（全 excluded）──────────────────────────────

def build_misc_rf(records):
    op = 0x44
    # 各族 legality（来源：contract-fp.md §15 + fp_semantics.yaml；SPEC-089t 回填）
    leg_convert_ff = ["rfhb != rf0", LEG_IMMU6, "rfhb + immu6 <= 64",
                      "rfhc + immu6 <= 64", "no_overlap(rfhb, rfhc, immu6)"]
    leg_convert_f2i = ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64"]
    leg_convert_i2f = ["rfhb != rf0", LEG_IMMU6, "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64"]
    leg_root = ["rfhb != rf0", "immu6 == 2"]
    leg_classify = ["rdhb != rd0", LEG_IMMU6, "rdhb + immu6 <= 64",
                    "rfhc + immu6 <= 64"]
    # orri 单目/格式转换类（rf -> rd 或 rd -> rf）
    orri_entries = [
        (0x00, "ftcls", "rdhb", "rfhc", leg_classify),
        (0x01, "ft2fo", "rfhb", "rfhc", leg_convert_ff),
        (0x02, "ft2ft", "rfhb", "rfhc", leg_convert_ff),
        (0x06, "ftroot", "rfhb", "rfhc", leg_root),
        (0x08, "focls", "rdhb", "rfhc", leg_classify),
        (0x09, "fo2ft", "rfhb", "rfhc", leg_convert_ff),
        (0x0A, "fo2fo", "rfhb", "rfhc", leg_convert_ff),
        (0x0E, "foroot", "rfhb", "rfhc", leg_root),
        (0x30, "ft2it", "rdhb", "rfhc", leg_convert_f2i),
        (0x31, "ft2io", "rdhb", "rfhc", leg_convert_f2i),
        (0x32, "ft2ut", "rdhb", "rfhc", leg_convert_f2i),
        (0x33, "ft2uo", "rdhb", "rfhc", leg_convert_f2i),
        (0x34, "it2ft", "rfhb", "rdhc", leg_convert_i2f),
        (0x35, "io2ft", "rfhb", "rdhc", leg_convert_i2f),
        (0x36, "ut2ft", "rfhb", "rdhc", leg_convert_i2f),
        (0x37, "uo2ft", "rfhb", "rdhc", leg_convert_i2f),
        (0x38, "fo2it", "rdhb", "rfhc", leg_convert_f2i),
        (0x39, "fo2io", "rdhb", "rfhc", leg_convert_f2i),
        (0x3A, "fo2ut", "rdhb", "rfhc", leg_convert_f2i),
        (0x3B, "fo2uo", "rdhb", "rfhc", leg_convert_f2i),
        (0x3C, "it2fo", "rfhb", "rdhc", leg_convert_i2f),
        (0x3D, "io2fo", "rfhb", "rdhc", leg_convert_i2f),
        (0x3E, "ut2fo", "rfhb", "rdhc", leg_convert_i2f),
        (0x3F, "uo2fo", "rfhb", "rdhc", leg_convert_i2f),
    ]
    for ha, mnem, dst, src, leg in orri_entries:
        records.append(rec(mnem, mnem, "orri", op, f_orri(dst, src, "immu6"),
                           leg, S00_MISCRF, ha=ha, scope="fp"))
    # orrr 双目运算/符号位操作类（目的 rfHB；无 immu6）
    orrr_entries = [
        (0x10, "ftadd"), (0x11, "ftsub"), (0x12, "ftmul"), (0x13, "ftdiv"),
        (0x14, "ftrem"), (0x15, "ftsclb"), (0x16, "ftsgnn"), (0x17, "ftsgnj"),
        (0x18, "foadd"), (0x19, "fosub"), (0x1A, "fomul"), (0x1B, "fodiv"),
        (0x1C, "forem"), (0x1D, "fosclb"), (0x1E, "fosgnn"), (0x1F, "fosgnj"),
    ]
    for ha, mnem in orrr_entries:
        records.append(rec(mnem, mnem, "orrr", op, f_orrr("rfhb", "rfhc", "rfhd"),
                           ["rfhb != rf0"], S00_MISCRF, ha=ha, scope="fp"))
    # 比较类：目的为 rd
    cmp_entries = [(0x20, "ftqcmp"), (0x21, "ftscmp"), (0x28, "foqcmp"), (0x29, "foscmp")]
    for ha, mnem in cmp_entries:
        records.append(rec(mnem, mnem, "orrr", op,
                           f_orrr("rdhb", "rfhc", "rfhd"), ["rdhb != rd0"],
                           S00_MISCRF, ha=ha, scope="fp"))


# ────────────────────────────── rule_refs 映射 ──────────────────────────────

# legality 表达式 → legality_rules.yaml id 的完整映射。
# 来源：contracts/legality_rules.yaml（SPEC-070t 定稿 15 条 + SPEC-083t 新增 dst_rd0_nonzero = 16 条）。
# 仅映射 opcodes.yaml legality 中实际出现的表达式；
# 运行时/兜底规则（excp_ialign/excp_rasof/excp_rasuf/excp_undi）不由 legality 表达式触发，
# 在 check_rule_refs.py 中通过显式豁免清单处理。
EXPR_TO_RULE = OrderedDict([
    # ── 目的寄存器 ──
    ("rdha != rd0",                               "dst_rd0"),
    ("rdhb != rd0",                               "dst_rd0"),
    ("rdhc != rd0",                               "dst_rd0"),
    ("rbha != rb0",                               "dst_rb0"),
    ("rbhb != rb0",                               "dst_rb0"),
    # ret rdha==rd0 时 imms18 必须为 0（仅 ret 适用）
    ("!(rdha == rd0 && imms18 != 0)",             "dst_rd0_nonzero"),
    # ── 双目的约束 ──
    ("!(rdha == rd0 && rdhb == rd0)",             "dst_dual_same"),
    ("!(rdha == rdhb && rdha != rd0)",            "dst_dual_same"),
    # ── 多寄存器/块赋值范围 ──
    ("immu6 != 0",                                "mreg_zero"),
    ("raha + immu6 <= 64",                        "mreg_range_overflow"),
    ("rahb + immu6 <= 64",                        "mreg_range_overflow"),
    ("rahc + immu6 <= 64",                        "mreg_range_overflow"),
    ("rbha + immu6 <= 64",                        "mreg_range_overflow"),
    ("rbhb + immu6 <= 64",                        "mreg_range_overflow"),
    ("rbhc + immu6 <= 64",                        "mreg_range_overflow"),
    ("rdha + immu6 <= 64",                        "mreg_range_overflow"),
    ("rdhb + immu6 <= 64",                        "mreg_range_overflow"),
    ("rdhc + immu6 <= 64",                        "mreg_range_overflow"),
    # ── 块赋值重叠 ──
    ("no_overlap(rdhb, rdhc, immu6)",             "mreg_range_overlap"),
    ("no_overlap(rbhb, rbhc, immu6)",             "mreg_range_overlap"),
    # ── FP（scope: fp）目的/范围（SPEC-089t；来源 contract-fp.md §15 + fp_semantics.yaml）──
    ("rfhb != rf0",                               "dst_rf0"),
    ("rfhc != rf0",                               "dst_rf0"),
    ("rfha + immu6 <= 64",                        "mreg_range_overflow"),
    ("rfhb + immu6 <= 64",                        "mreg_range_overflow"),
    ("rfhc + immu6 <= 64",                        "mreg_range_overflow"),
    ("no_overlap(rfhb, rfhc, immu6)",             "mreg_range_overlap"),
    ("immu6 == 2",                                "encode_fp_root_n"),
    # ── 对齐 ──
    ("aligned(2)",                                "excp_malign"),
    ("aligned(4)",                                "excp_malign"),
    ("aligned(8)",                                "excp_malign"),
    # ── SBZ / 位域 ──
    ("immu18[17:12] == 0",                        "encode_sbz"),
    ("immu18[11:10] == 0",                        "encode_sbz"),
    ("immu18[11:6] == 0",                         "encode_sbz"),
    ("immu18[5:4] == 0",                          "encode_sbz"),
    ("immu6 <= 7",                                "encode_sbz"),
    ("immu6 <= 15",                               "encode_sbz"),
    ("immu6 <= 31",                               "encode_sbz"),
    ("immu6 <= 63",                               "encode_sbz"),
    # ── one-hot（ADR-0012 D10 rev.*）：immu6 须为 2 的幂且 k < S（排除 k = S 恒等档）──
    ("immu6 == 1 || immu6 == 2 || immu6 == 4 || immu6 == 8 || immu6 == 16 || immu6 == 32",
     "encode_onehot"),
    ("immu6 == 1 || immu6 == 2 || immu6 == 4 || immu6 == 8 || immu6 == 16",
     "encode_onehot"),
    ("immu6 == 1 || immu6 == 2 || immu6 == 4 || immu6 == 8", "encode_onehot"),
    ("immu6 == 1 || immu6 == 2 || immu6 == 4",    "encode_onehot"),
])

def _compute_rule_refs(records):
    """为每条记录计算 rule_refs 字段（list[str]，去重保序）。

    规则：
    - scope == "excluded" ⇒ rule_refs: []（excluded 恒空，含 fence）
    - legality 为空 ⇒ rule_refs: []
    - 否则按 EXPR_TO_RULE 映射每条 legality 表达式；未知表达式触发 RuntimeError。
    """
    for r in records:
        if r.get("scope") == "excluded" or not r.get("legality"):
            r["rule_refs"] = []
            continue
        seen = set()
        refs = []
        for expr in r["legality"]:
            if expr not in EXPR_TO_RULE:
                raise RuntimeError(
                    f"指令 {r['id']}：legality 表达式 {expr!r} 无映射（请更新 EXPR_TO_RULE）")
            rid = EXPR_TO_RULE[expr]
            if rid not in seen:
                seen.add(rid)
                refs.append(rid)
        r["rule_refs"] = refs


# ────────────────────────────── 主流程 ──────────────────────────────

def main():
    records = []
    build_main_table(records)
    build_misc_amo(records)
    build_misc_octa(records)
    build_misc_fixed_width(records, 0x41, "t", 31, "SimRISC-08")
    build_misc_fixed_width(records, 0x42, "w", 15, "SimRISC-09")
    build_misc_fixed_width(records, 0x43, "b", 7, "SimRISC-10")
    build_misc_rf(records)

    _compute_rule_refs(records)

    n_m1 = sum(1 for r in records if r.get("scope") == "m1")
    n_fp = sum(1 for r in records if r.get("scope") == "fp")
    n_ex = sum(1 for r in records if r.get("scope") == "excluded")
    n_m3 = sum(1 for r in records if r.get("scope") == "m3")
    n_m8 = sum(1 for r in records if r.get("scope") == "m8")
    n_m9 = sum(1 for r in records if r.get("scope") == "m9")
    n_with_refs = sum(1 for r in records if r.get("rule_refs"))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# SimRISC 0.5.4 指令编码表（按 scope 划分范围）\n")
        f.write("# 自动生成自 spec/SimRISC-00（QFC 主表 + MISC 子表）与 .tao/contracts/contract-isa.md\n")
        f.write("# M1：标量整数 + 地址/内存 RD/RB/RA + 控制流 + 测试机所需系统\n")
        f.write("# scope: fp 为原生浮点范围（RF 存取/运算/转换/比较/条件赋值），已实现；\n")
        f.write("# scope: excluded 为特权 cfx / LR-SC / fence，尚未实现，\n")
        f.write("#   编码已定义 → ILLI（decode: ILLI）；UNDI 仅用于空白单元格\n")
        f.write("# scope: m3 为 M3 CodeGen 新增指令（ADR-0012 D9.1），非 M1 身份\n")
        f.write("# scope: m8 为新增 ISA 指令（ADR-0012 D10 逐块反转 rev.o/.t/.w/.b + "
                "D11 位扫描/计数 ctlz/cttz/ctpop），非 M1 身份\n")
        f.write("# scope: m9 为新增 ISA 指令（ADR-0032 D4 逻辑循环左移 rol.o/.t/.w/.b），非 M1 身份\n")
        f.write(f"# 共 {len(records)} 条：M1 {n_m1} 条 + scope fp {n_fp} 条"
                f" + scope excluded {n_ex} 条 + scope m3 {n_m3} 条 + scope m8 {n_m8} 条"
                f" + scope m9 {n_m9} 条\n")
        f.write(f"# 有 rule_refs 的指令：{n_with_refs} 条\n\n")
        yaml.dump(records, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"生成完成：{len(records)} 条（M1 {n_m1}，scope fp {n_fp}，scope excluded {n_ex}，"
          f"scope m3 {n_m3}，scope m8 {n_m8}，scope m9 {n_m9}，有 rule_refs {n_with_refs}）-> {OUT_PATH}")


if __name__ == "__main__":
    main()
