#!/usr/bin/env python3
"""`tests/arch/cache/cache_oracle.py` — cfx5（`cfx_cache`）三方 arch 用例的唯一
期望值来源（`m16-testcases-009`）。

四条 case 共用本文件，QEMU / gem5 / RTL 三个承载共用同一份槽序与期望：

  * `arch-cache-001`（hmon/smon/umon，21 槽）：寄存器面 + D 侧单行
    `invalidate`/`clean`/`flush` + I 侧 `invalidate`/`flush` 后取指重取 +
    `cache_enable=0` 的不维护 + 编码 no-op / 无行 PA 无效果 +
    **I+D 同选**（`[15:14] = 11`）的 clean/invalidate/flush 三条合法命令
    （CACHE-21；`ISS-517`）；
  * `arch-cache-002`（hmon/smon/umon，12 槽）：D 侧范围 —— `PA 单行`只碰包含
    `addr_start` 的行、`PA 区间`（相邻两行 + 区间外一行）、`all`；
  * `arch-cache-003`（只 hmon，16 槽）：拒绝面 —— 读 WO、写 RO、保留 rc、
    非法控制字（`[3:2]=11`、`PA 区间` 且 `size=0`）⇒ `CFXREG`，且非法命令
    **不产生任何维护动作**（脏行不被写回/丢弃）；`enable=0` 不抑制编码校验；
  * `arch-cache-004`（只 hmon，`cache-model=off`）：CACHE-27 的 off 分支 ——
    `cfx5` 存在、`cache_exist=0`、寄存器可访问、合法命令被接受且无效果、非法
    编码仍 ⇒ `CFXREG`。

## 判据来源（现场派生，不从实现反推）

  * 寄存器行 / 位定义 / 控制字三维 / 判序 / 范围匹配 / I-D 侧语义：
    `.tao/contracts/contract-cache.md`（CACHE-03/04/06/07/08/09/12/13/14/
    15/16/17/18/19/20/21/23/27）；
  * `CFXREG = 1 << 2`：`contract-see §6.1`（现场解析，不写死）；
  * `cfx2rd`/`cfx2rc`/`set.zw`/`jump` 的编码：`contracts/opcodes.yaml`（现场
    解析：拒绝面的 `cause_info` 期望 = 该指令的编码，不是实现返回值）；
  * 运行模式编码（user/supv/hypv = 0/2/3）：`spec/Kaiwu §7.1`。

**测试激励常量**（数据 pattern、magic、见证值）是本文件的输入，不是从任何
实现反推的期望：它们只决定「写什么」，期望由契约语义推出「读回应是什么」。
"""
from __future__ import annotations

import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]

CFXREG_CONTRACT = ".tao/contracts/contract-see.md"
CACHE_CONTRACT = ".tao/contracts/contract-cache.md"
KAIWU = "spec/Kaiwu-测试机运行环境.md"

CASES = ("arch-cache-001", "arch-cache-002", "arch-cache-003",
         "arch-cache-004")
MODES = ("hmon", "smon", "umon")
CASE_MODES = {
    "arch-cache-001": ("hmon", "smon", "umon"),
    "arch-cache-002": ("hmon", "smon", "umon"),
    # 拒绝面逐条触发同步异常：step5 链在 supv/user 下没有同步异常处理程序
    # （`common/env-README.md`「已知语义边界」）。
    "arch-cache-003": ("hmon",),
    # CACHE-27 的 `cache-model=off` 分支；hmon 用于故障观察。
    "arch-cache-004": ("hmon",),
}
CASE_CACHE_MODEL = {
    "arch-cache-001": "on",
    "arch-cache-002": "on",
    "arch-cache-003": "on",
    "arch-cache-004": "off",
}

# ---- 测试激励（PA = VA，Vast 的 [0,2 GiB) 内存窗口；64 B 行） ---------------
A_R0 = 0x7000_0000          # 区间第 0 行
A_R1 = 0x7000_0040          # 区间第 1 行（相邻）
A_D = 0x7000_1000           # 单行 / all
A_OUT = 0x7000_1100         # 区间外（不被区间命令碰）
A_CODE = 0x7000_2000        # 自修改代码行

PATTERN64 = 0x1234_5678_9ABC_DEF0

# 数据初值（内存）与两组新值（经 D 侧写入）
M_R0 = 0xC0DE_0000_0000_0500
M_R1 = 0xC0DE_0000_0000_0502
M_D = 0xC0DE_0000_0000_0600
M_OUT = 0xC0DE_0000_0000_0604
N_R0 = 0xC0DE_0000_0000_0501
N_R1 = 0xC0DE_0000_0000_0503
N_D = 0xC0DE_0000_0000_0601
N_OUT = 0xC0DE_0000_0000_0605
P_R0 = 0xC0DE_0000_0000_0504
P_R1 = 0xC0DE_0000_0000_0506
P_D = 0xC0DE_0000_0000_0602
N_EN = 0xC0DE_0000_0000_0603

# 自修改代码行第 0 字的 16 位立即数（第 1 字固定为 `jump [rb5]`）。
IMM_OLD = 0x1111
IMM_INVAL = 0x3333
IMM_FLUSH = 0x5555
IMM_RANGE = 0x7777
# I+D 同选（`[15:14] = 11`）的 flush 命令写回的新立即数（CACHE-21）。
IMM_ID = 0x9999

# 见证值：no-op / 无行命令「没有把执行流带走」。
W_MMIO = 0xC0DE_0000_0000_0701
W_SEL0 = 0xC0DE_0000_0000_0702
W_NONE = 0xC0DE_0000_0000_0703
W_CLEAN_ALL = 0xC0DE_0000_0000_0704
W_INVAL_LINE = 0xC0DE_0000_0000_0705
W_FLUSH_RANGE = 0xC0DE_0000_0000_0706

# 无行/不可缓存的 PA（核内 SRAM 地址；任何平台都不该有对应 cache 行）
PA_NOLINE = 0x00FF_FFFF_0101_0100

# 拒绝面使用 `rd6` 写、`rd5` 读（`cause_info` 的指令编码依赖这两个字段）。
CTRL_WRITE_RD = 6
CTRL_READ_RD = 5
EXIST_WRITE_RD = 6


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_REGS = _load("cache_oracle_regs", HERE / "check_cfx5_regs.py")


class OracleError(Exception):
    pass


def facts(root="."):
    root = pathlib.Path(root)
    try:
        regs = _REGS.parse_cache_contract(root)
        cfxreg = 1 << _REGS.parse_cfxreg_bit(root)
        cfx2rd = _REGS.parse_opcode(root, "cfx2rd_crrr_cfx")
        cfx2rc = _REGS.parse_opcode(root, "cfx2rc_crrr_cfx")
        setzw = _REGS.parse_opcode(root, "set.zw_rwii_rd")
        jump = _REGS.parse_opcode(root, "jump_rrii_rb")
    except (SystemExit, OSError) as exc:
        raise OracleError(str(exc))
    # `spec/Kaiwu §7.1` 的运行模式编码（body 实际运行模式由模拟器观测）。
    kaiwu = (root / KAIWU).read_text(encoding="utf-8")
    import re
    m = re.search(r"`bit5:4` 为运行模式——`user`=`(\d+)`、`jail`=`(\d+)`、"
                  r"`supv`=`(\d+)`、`hypv`=`(\d+)`", kaiwu)
    if not m:
        raise OracleError("spec/Kaiwu §7.1: mode encoding sentence not found")
    modes = dict(zip(("user", "jail", "supv", "hypv"),
                     (int(g, 2) for g in m.groups())))
    return {
        "regs": regs, "cfxreg": cfxreg,
        "cfx2rd": cfx2rd, "cfx2rc": cfx2rc,
        "set.zw": setzw, "jump": jump,
        "modes": modes,
    }


def mode_code(f, mode):
    name = {"hmon": "hypv", "smon": "supv", "umon": "user"}[mode]
    return f["modes"][name]


def _encode(f, ident, **fields):
    """按 `contracts/opcodes.yaml` 的字段位域拼一条指令（期望的 cause_info）。"""
    return _REGS.encode(f[ident], **fields)


def cfx_word(f, rc, dst, write=False):
    """`cfx2rd`/`cfx2rc cfx_cache, cg8, rc, dst` 的 32 位编码。"""
    rows = f["regs"]["rows"]
    cg = rows["cfx_cache_exist"][0]
    return _encode(f, "cfx2rc" if write else "cfx2rd",
                   cfxcode=f["regs"]["cfxha"], cfx_cg=cg, cfx_rc=rc, dst=dst)


def _encode_named(op, values):
    """按字段名而不是 role 拼指令：`jump` 的两个字段共用 role `src`。"""
    word = op["value"]
    for field in op["fields"]:
        name = field["name"]
        if name not in values:
            raise OracleError("no value for field %r" % name)
        lo, hi = _REGS._bits_lo_hi(field["bits"])
        value = int(values[name])
        if value < 0 or value >= (1 << (hi - lo + 1)):
            raise OracleError("%r value %#x does not fit %s"
                              % (name, value, field["bits"]))
        word |= value << lo
    return word


def setzw_word(f, rd, imm):
    return _encode_named(f["set.zw"],
                         {"rdha": rd, "wpN": 0, "immu16": imm & 0xFFFF})


def jump_back_word(f, rb):
    return _encode_named(f["jump"],
                         {"rbha": rb, "rdhb": 0, "imms12": 0})


def control(f, side, op, scope):
    c = f["regs"]
    word = 0
    for name in ("I", "D"):
        if name in side:
            word |= 1 << c["sel_bits"][name]
    word |= c["ops"][op]
    word |= c["scopes"][scope] << 2
    return word


# ---------------------------------------------------------------------------
# 槽序（探针 `SIGUPD` 顺序 == 这里的顺序）
# ---------------------------------------------------------------------------
SLOTS = {
    "arch-cache-001": (
        "exist",
        "enable_reset",
        "enable_write_0",
        "enable_write_3",
        "enable_write_ones",
        "addr_start_ones",
        "addr_start_pattern",
        "addr_size_pattern",
        "d_invalidate_single",
        "d_clean_single",
        "d_flush_single",
        "i_invalidate_single",
        "i_flush_single",
        "i_invalidate_range",
        "enable0_invalidate_noop",
        "mmio_noop",
        "noop_sel0",
        "noop_opnone",
        # I+D 同选（CACHE-21）：探针在 case 1 末尾追加的三条合法命令。
        "id_invalidate_nodrop",
        "id_flush_refetch",
        "id_clean_writeback",
    ),
    "arch-cache-002": (
        "d_line_containing",
        "d_line_other_kept",
        "d_invalidate_range_lo",
        "d_invalidate_range_hi",
        "d_clean_range_lo",
        "d_clean_range_hi",
        "d_flush_range_lo",
        "d_flush_range_hi",
        "d_range_outside_kept",
        "d_invalidate_all",
        "d_clean_all",
        "d_flush_all",
    ),
    "arch-cache-003": (
        "exist",
        "cfxreg_read_ctrl_cause",
        "cfxreg_read_ctrl_info",
        "cfxreg_write_exist_cause",
        "cfxreg_write_exist_info",
        "cfxreg_reserved_rc_cause",
        "cfxreg_reserved_rc_info",
        "cfxreg_scope_reserved_cause",
        "cfxreg_scope_reserved_info",
        "cfxreg_range_zero_cause",
        "cfxreg_range_zero_info",
        "cfxreg_under_enable0_cause",
        "cfxreg_under_enable0_info",
        "illegal_clean_no_writeback",
        "illegal_invalidate_no_drop",
        "exist_after_rejects",
    ),
    "arch-cache-004": (
        "exist",
        "enable_reset",
        "enable_write_3",
        "addr_start_ones",
        "addr_start_pattern",
        "addr_size_pattern",
        "legal_clean_all",
        "legal_invalidate_line",
        "legal_flush_range",
        "data_after_commands",
        "cfxreg_scope_reserved_cause",
        "cfxreg_scope_reserved_info",
        "cfxreg_range_zero_cause",
        "cfxreg_range_zero_info",
        "exist_after",
    ),
}


def slot_labels(case_id):
    if case_id not in SLOTS:
        raise OracleError("unknown case %r" % (case_id,))
    return SLOTS[case_id]


def expected(case_id, root="."):
    f = facts(root)
    c = f["regs"]
    rows = c["rows"]
    exist = c["exist_value"] if CASE_CACHE_MODEL[case_id] == "on" else 0
    pa_mask = (1 << c["pa_bits"]) - 1
    ctrl_rc = rows["cfx_cache_ctrl"][1]
    exist_rc = rows["cfx_cache_exist"][1]
    cfxreg = f["cfxreg"]

    if case_id == "arch-cache-001":
        return [
            exist,
            exist,
            0,
            3,
            exist,
            pa_mask,
            PATTERN64 & pa_mask,
            PATTERN64,
            M_D,                 # invalidate 丢弃脏行 ⇒ 内存旧值
            N_D,                 # clean 写回（再失效后读）⇒ 新值
            P_D,                 # flush 写回（再读）⇒ 新值
            IMM_INVAL,
            IMM_FLUSH,
            IMM_RANGE,
            N_EN,
            W_MMIO,
            W_SEL0,
            W_NONE,
            M_D,                 # I+D 同选 invalidate：脏行不写回 ⇒ 内存旧值
            IMM_ID,              # I+D 同选 flush：I 侧丢弃 + D 侧写回 ⇒ 取新码
            N_D,                 # I+D 同选 clean：I 侧 no-op、D 侧写回
        ]

    if case_id == "arch-cache-002":
        return [
            M_R0,                # 单行只碰包含 addr_start 的行
            N_R1,                # 相邻行保留
            M_R0, M_R1,          # 区间 invalidate 丢弃两行脏数据
            N_R0, N_R1,          # 区间 clean 写回两行
            P_R0, P_R1,          # 区间 flush 写回两行
            N_OUT,               # 区间外的行不被碰
            M_D,                 # all invalidate
            N_D,                 # all clean
            P_D,                 # all flush
        ]

    if case_id == "arch-cache-003":
        return [
            exist,
            cfxreg,
            cfx_word(f, ctrl_rc, CTRL_READ_RD),
            cfxreg,
            cfx_word(f, exist_rc, EXIST_WRITE_RD, write=True),
            cfxreg,
            cfx_word(f, 1, CTRL_READ_RD),
            cfxreg,
            cfx_word(f, ctrl_rc, CTRL_WRITE_RD, write=True),
            cfxreg,
            cfx_word(f, ctrl_rc, CTRL_WRITE_RD, write=True),
            cfxreg,
            cfx_word(f, ctrl_rc, CTRL_WRITE_RD, write=True),
            M_D,                 # 非法 clean 没有写回
            N_D,                 # 非法 invalidate 没有丢弃脏行
            exist,
        ]

    if case_id == "arch-cache-004":
        return [
            0,
            0,
            0,
            pa_mask,
            PATTERN64 & pa_mask,
            PATTERN64,
            W_CLEAN_ALL,
            W_INVAL_LINE,
            W_FLUSH_RANGE,
            N_OUT,               # 无 cache 模型：写到内存，读回新值
            cfxreg,
            cfx_word(f, ctrl_rc, CTRL_WRITE_RD, write=True),
            cfxreg,
            cfx_word(f, ctrl_rc, CTRL_WRITE_RD, write=True),
            0,
        ]

    raise OracleError("unknown case %r" % (case_id,))


def build_include(root="."):
    """汇编期常量（`--defsym` 的批量形式）：探针与判据不各存一份。

    返回 `[(name, value)]`；驱动把它写成 `cache_tables.inc` 交给 `llvm-mc`。
    """
    f = facts(root)
    c = f["regs"]
    out = [
        ("C_EXIST", c["exist_value"]),
        ("C_PA_MASK", (1 << c["pa_bits"]) - 1),
        ("C_PATTERN64", PATTERN64),
        ("A_R0", A_R0), ("A_R1", A_R1), ("A_D", A_D),
        ("A_OUT", A_OUT), ("A_CODE", A_CODE),
        ("M_R0", M_R0), ("M_R1", M_R1), ("M_D", M_D), ("M_OUT", M_OUT),
        ("N_R0", N_R0), ("N_R1", N_R1), ("N_D", N_D), ("N_OUT", N_OUT),
        ("P_R0", P_R0), ("P_R1", P_R1), ("P_D", P_D), ("N_EN", N_EN),
        ("IMM_OLD", IMM_OLD), ("IMM_INVAL", IMM_INVAL),
        ("IMM_FLUSH", IMM_FLUSH), ("IMM_RANGE", IMM_RANGE),
        ("W_MMIO", W_MMIO), ("W_SEL0", W_SEL0), ("W_NONE", W_NONE),
        ("W_CLEAN_ALL", W_CLEAN_ALL), ("W_INVAL_LINE", W_INVAL_LINE),
        ("W_FLUSH_RANGE", W_FLUSH_RANGE),
        ("PA_NOLINE", PA_NOLINE),
        ("WORD_OLD", setzw_word(f, 20, IMM_OLD)),
        ("WORD_INVAL", setzw_word(f, 20, IMM_INVAL)),
        ("WORD_FLUSH", setzw_word(f, 20, IMM_FLUSH)),
        ("WORD_RANGE", setzw_word(f, 20, IMM_RANGE)),
        ("WORD_ID", setzw_word(f, 20, IMM_ID)),
        ("WORD_JUMP", jump_back_word(f, 5)),
    ]
    # 控制字：三个维度分别生成，避免探针里出现裸位号。
    combos = {
        "D_CLEAN_ALL": ("D", "clean", "all"),
        "D_CLEAN_LINE": ("D", "clean", "PA 单行"),
        "D_CLEAN_RANGE": ("D", "clean", "PA 区间"),
        "D_INVAL_ALL": ("D", "invalidate", "all"),
        "D_INVAL_LINE": ("D", "invalidate", "PA 单行"),
        "D_INVAL_RANGE": ("D", "invalidate", "PA 区间"),
        "D_FLUSH_ALL": ("D", "flush", "all"),
        "D_FLUSH_LINE": ("D", "flush", "PA 单行"),
        "D_FLUSH_RANGE": ("D", "flush", "PA 区间"),
        "I_CLEAN_LINE": ("I", "clean", "PA 单行"),
        "I_INVAL_LINE": ("I", "invalidate", "PA 单行"),
        "I_INVAL_RANGE": ("I", "invalidate", "PA 区间"),
        "I_FLUSH_LINE": ("I", "flush", "PA 单行"),
        # I+D 同选（`[15:14] = 11`，CACHE-21）：操作/范围两维两侧共用，
        # 因此「同选 + 合法操作」只有 clean/invalidate/flush 三条命令
        # （两侧各自的语义见 CACHE-19/20）。
        "ID_CLEAN_LINE": ("ID", "clean", "PA 单行"),
        "ID_INVAL_LINE": ("ID", "invalidate", "PA 单行"),
        "ID_FLUSH_LINE": ("ID", "flush", "PA 单行"),
        "I_FLUSH_RANGE": ("I", "flush", "PA 区间"),
        "ID_CLEAN_RESV": ("ID", "clean", "reserved"),
        "D_CLEAN_RESV": ("D", "clean", "reserved"),
        "ID_NONE_RANGE": ("ID", "none", "PA 区间"),
        "NONE_SEL_FLUSH_RESV": ("", "flush", "reserved"),
    }
    for name, (side, op, scope) in combos.items():
        out.append((name, control(f, side, op, scope)))
    return out


def emit_inc(root=".", stream=None):
    import sys
    stream = stream or sys.stdout
    for name, value in build_include(root):
        stream.write(".equ\t%s, 0x%x\n" % (name, value))


# ---------------------------------------------------------------------------
# RTL 载体的地址（`cache_rtl.S`）：VA = PA + 2 TiB、64 KiB 页；数据行落在
# L2[4]（页 0x4_0000）与 L2[8]（页 0x8_0000）。槽里只有**值**，所以 RTL 的
# PA 可以与 QEMU/gem5 的 0x7000_0000 不同；`addr_start` 写的是本载体的 PA。
# ---------------------------------------------------------------------------
RTL_VA_BASE = 0x200_0000_0000
RTL_PA_L1E = 0x0_8000          # PA 0 + L1 index 0x1000 * 8
RTL_PA_L2 = 0x1_0000
RTL_PA_R0 = 0x4_1200
RTL_PA_R1 = 0x4_1240
RTL_PA_D = 0x4_5000
RTL_PA_OUT = 0x4_5100
RTL_PA_CODE = 0x8_1000
RTL_A_R0 = RTL_VA_BASE + RTL_PA_R0
RTL_A_R1 = RTL_VA_BASE + RTL_PA_R1
RTL_A_D = RTL_VA_BASE + RTL_PA_D
RTL_A_OUT = RTL_VA_BASE + RTL_PA_OUT
RTL_A_CODE = RTL_VA_BASE + RTL_PA_CODE


def _gen_module():
    return _load("cache_oracle_gen", HERE / "gen_cfx5_maint_tables.py")


def rtl_include(root="."):
    """RTL 探针的汇编期常量（含页表 PTE；PTE 布局复用 cfx5_maint 的生成器）。"""
    gen = _gen_module()
    pte = gen.pte
    out = [
        ("A_R0", RTL_A_R0), ("A_R1", RTL_A_R1), ("A_D", RTL_A_D),
        ("A_OUT", RTL_A_OUT), ("A_CODE", RTL_A_CODE),
        ("PA_R0", RTL_PA_R0), ("PA_R1", RTL_PA_R1),
        ("PA_D", RTL_PA_D), ("PA_OUT", RTL_PA_OUT),
        ("PA_CODE", RTL_PA_CODE),
        ("PAGE_L1E", RTL_PA_L1E), ("PAGE_L2", RTL_PA_L2),
        ("PTE_L1", pte(RTL_PA_L2)),
        ("PTE_DATA", pte(0x4_0000)),
        ("PTE_CODE", pte(0x8_0000)),
    ]
    return out


_RTL_ADDR_NAMES = {"A_R0", "A_R1", "A_D", "A_OUT", "A_CODE"}


def rtl_build_include(root="."):
    out = [(name, value) for name, value in build_include(root)
           if name not in _RTL_ADDR_NAMES]
    out.extend(rtl_include(root))
    return out


def emit_rtl_inc(root=".", stream=None):
    import sys
    stream = stream or sys.stdout
    for name, value in rtl_build_include(root):
        stream.write(".equ\t%s, 0x%x\n" % (name, value))
