#!/usr/bin/env python3
"""`gen_cfx5_maint_tables.py` — `cfx5_maint.S` 的几何/页表/期望值单一真源
（`m16-chipyard-017`）。

探针与判据不各存一份常量：本模块

  * 定义 PA/VA 布局、magic、控制字（控制字的三维字段从 `contract-cache` §3
    现场解析，不在本文件写死位号）；
  * 生成探针的汇编 include（`--emit inc`：`.equ` 形式的 PA/VA/PTE/magic/
    控制字/间接期望）；
  * 生成判据的期望记录序列（`expected_records()`，顺序 = `cfx5_maint.S`
    的 `__REC` 顺序）。

页表几何取 `contract-tlb`/`DADAO-12`：L1 = `VA[41:29]`、L2 = `VA[28:16]`、
页内 `VA[15:0]`（64 KiB 页），PTE 8 字节大端；VA = PA + 2 TiB（与
`tools/chipyard/dcache/gen_vastdcache_tables.py` 同一窗口）。数据/代码行避开
页表所在的 group 0，且每 group 的行数远小于 8 路，日志里的命中/缺失不会被
无关行挤掉。

布局（PA）：

    0x008000  L1 表项（VA index 0x1000）
    0x010000  L2 表（16 项）
    0x041200  R0：区间测试第 0 行
    0x041240  R1：区间测试第 1 行（与 R0 相邻 ⇒ 同一区间命中两行）
    0x045000  D ：单行/all 测试数据行
    0x081000  CODE：自修改代码行（首条 `set.zw rd20, wp0, <imm>`，
              第二条 `jump [rb5, rd0, 0]`）

记录顺序见 `expected_records()` 的注释（与 `cfx5_maint.S` 的 `__REC` 一一对应）。
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

VA_BASE = 0x200_0000_0000          # kernel window: VA = PA + 2 TiB
PAGE = 0x1_0000

PA_L1E = 0x0_8000                  # L1 entry for VA[41:29] = 0x1000
PA_L2 = 0x1_0000
PA_R0 = 0x4_1200                   # range line 0 (group 72)
PA_R1 = 0x4_1240                   # range line 1 (group 73, adjacent)
PA_D = 0x4_5000                    # single/all data line (group 64)
PA_CODE = 0x8_1000                 # code line (group 64)
# `cache_addr_start` 的 56 位向量（`CACHE-18`/`ISS-534`）：bit48 置位，且
# `[47:0] == PA_D` ⇒ 若维护端口按 48 位截断，单行命令会错误命中 A_D。
PA_HIGH = 0x0001_0000_0004_5000

VA_R0 = VA_BASE + PA_R0
VA_R1 = VA_BASE + PA_R1
VA_D = VA_BASE + PA_D
VA_CODE = VA_BASE + PA_CODE

# `+loadmem` puts the code line in memory before the core starts: the stub's
# first instruction sets rd20 to its 16-bit immediate, the second returns to
# the probe (rb5 = the resume label).  Encoding `set.zw rd20, wp0, 0x1111` =
# 0x4c50_1111, `jump [rb5, rd0, 0]` = 0x7114_0000 (verified with llvm-mc).
STUB_OLD = 0x4C50_1111
STUB_JUMP = 0x7114_0000

# ---- initial memory / values ----------------------------------------------
M_R0 = 0xC0DE_0000_0000_0500
M_R1 = 0xC0DE_0000_0000_0502
M_D = 0xC0DE_0000_0000_0600
N_R0 = 0xC0DE_0000_0000_0501
N_R1 = 0xC0DE_0000_0000_0503
N_D = 0xC0DE_0000_0000_0601
P_R0 = 0xC0DE_0000_0000_0504
P_R1 = 0xC0DE_0000_0000_0506
P_D = 0xC0DE_0000_0000_0602

# Instruction immediates patched into the code line (the data path writes only
# the 16-bit immediate at +2; the jump keeps the line position independent).
IMM = [0x1111, 0x3333, 0x5555, 0x7777, 0x9999, 0xBBBB, 0xDDDD, 0xEEEE,
       0x1234]

# Witnesses that a no-op / no-line command reached its successor (they are not
# semantic expectations: they only prove the instruction did not fault).
MMIO_LINE = 0x00FFFF_FF01_0100      # core-SRAM PA: no cache line can match
W_NONE_SEL = 0xC0DE_0000_0000_0700
W_MMIO = 0xC0DE_0000_0000_0701


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def contract(root: pathlib.Path) -> dict:
    """cfx5 register rows / control-word fields, parsed from the contract."""
    mod = _load("cfx5_regs_oracle", HERE / "check_cfx5_regs.py")
    return mod.parse_cache_contract(root)


def control(c: dict, side: str, op: str, scope: str) -> int:
    """Assemble a `cache_ctrl` word from the contract's field definitions.

    `side` = "I" / "D" / "ID"; `op` / `scope` are the contract names.
    """
    sel_bits = c["sel_bits"]
    word = 0
    for s in ("I", "D"):
        if s in side:
            word |= 1 << sel_bits[s]
    word |= c["ops"][op]
    word |= c["scopes"][scope] << 2
    return word


def pte(pa: int, r: int = 1, w: int = 1, x: int = 1, g: int = 0,
        a: int = 1, d: int = 1, sp: int = 0, p: int = 1,
        frags: int = 0xFF, hsju: int = 0xF) -> int:
    """Assemble a PTE (big-endian value), same field layout as the other Vast
    probes (`DADAO-12` §2.2.1–§2.2.4)."""
    v = (hsju & 0xF) << 60
    v |= pa & (0x00FF_FFFF_FFFF_0000 if sp == 0 else 0x00FF_FFFF_E000_0000)
    v |= (frags & 0xFF) << 8
    v |= (r & 1) << 7
    v |= (w & 1) << 6
    v |= (x & 1) << 5
    v |= (g & 1) << 4
    v |= (a & 1) << 3
    v |= (d & 1) << 2
    v |= (sp & 1) << 1
    v |= (p & 1)
    return v


PTE_L1 = pte(PA_L2)                 # L1 entry -> L2 table
PTE_DATA = pte(0x4_0000)            # page 4: R0/R1/D
PTE_CODE = pte(0x8_0000)            # page 8: the self-modifying code line

L2 = [0] * 16
L2[4] = PTE_DATA
L2[8] = PTE_CODE


def check_geometry() -> None:
    """The probe's observability rests on these; a collision would move a line
    into the page-table group or put more than 8 lines in one group."""
    idx = lambda pa: (pa >> 6) & 0x7F
    data = [PA_R0, PA_R1, PA_D, PA_CODE]
    if any(idx(pa) == 0 for pa in data):
        raise SystemExit("gen_cfx5_maint: a data line is in the page-table group 0")
    if idx(PA_R1) != idx(PA_R0) + 1 or PA_R1 != PA_R0 + 64:
        raise SystemExit("gen_cfx5_maint: R0/R1 are not adjacent 64 B lines")
    if idx(PA_R0) == idx(PA_D):
        raise SystemExit("gen_cfx5_maint: R0 and D share a group")
    if idx(PA_CODE) != idx(PA_D):
        raise SystemExit("gen_cfx5_maint: CODE and D share a group")
    if (PA_R0 & 0xFFFF) + 128 > 0x1_0000 or (PA_R1 & 0xFFFF) + 64 > 0x1_0000:
        raise SystemExit("gen_cfx5_maint: the range crosses its 64 KiB page")
    if L2[4] != pte(0x4_0000) or L2[8] != pte(0x8_0000):
        raise SystemExit("gen_cfx5_maint: L2 does not map pages 4 and 8")
    if (PA_CODE >> 16) != 8 or (PA_R0 >> 16) != 4 or (PA_D >> 16) != 4:
        raise SystemExit("gen_cfx5_maint: a line is outside its mapped page")


def expected_records(root: pathlib.Path) -> list:
    """Expected result-buffer records, in `cfx5_maint.S` `__REC` order.

    A record is `(name, value)`; the probe writes the measured 8 bytes.
    """
    c = contract(root)
    cfxreg = 1 << _load("cfx5_regs_oracle", HERE / "check_cfx5_regs.py") \
        .parse_cfxreg_bit(root)
    recs = []

    def rec(name, value):
        recs.append((name, value & 0xFFFF_FFFF_FFFF_FFFF))

    # ---- A: I side, single line -------------------------------------------
    rec("I: warm-up executes the original immediate", IMM[0])
    rec("I|clean|single keeps the I line (old immediate)", IMM[0])
    rec("I|invalidate|single re-fetches the new immediate", IMM[1])
    rec("I|invalidate|range re-fetches the newer immediate", IMM[2])
    rec("I|flush|single re-fetches the newest immediate", IMM[3])
    # ---- B: D side, single line, observed through the fetch port ----------
    rec("D|invalidate|single discards the dirty line (memory old)", IMM[3])
    rec("D|clean|single writes the dirty line back (memory new)", IMM[5])
    rec("D|flush|single writes back and drops (memory new)", IMM[6])
    rec("D|flush|single: the next D read misses and returns the line word",
        (0x4C50 << 48) | (IMM[6] << 32) | (0x7114 << 16))
    # ---- C: D side, PA range (R0/R1) --------------------------------------
    rec("range: invalidate keeps memory at the old R0", M_R0)
    rec("range: invalidate keeps memory at the old R1", M_R1)
    rec("range: clean wrote R0 back", N_R0)
    rec("range: clean wrote R1 back", N_R1)
    rec("range: flush wrote R0 back", P_R0)
    rec("range: flush wrote R1 back", P_R1)
    # ---- D: D side, all ----------------------------------------------------
    rec("all: invalidate keeps memory at the old D line", M_D)
    rec("all: clean wrote the D line back", N_D)
    rec("all: flush wrote the D line back", P_D)
    # ---- E: enable = 0 / no-line / illegal encodings ----------------------
    rec("enable=0: invalidate was a no-op, clean still sees the dirty line",
        IMM[7])
    rec("no-line PA: commands complete without an exception", W_MMIO)
    # `cache_addr_start` is a full 56-bit PA (CACHE-18): the register read-back
    # must not be truncated, and a single-line command at an address whose low
    # 48 bits alias A_D must not touch that line (ISS-534).
    rec("addr_start: full 56-bit PA read back (not truncated)", PA_HIGH)
    rec("addr_start >=48 bit: the aliasing low line was not touched", N_D)
    rec("no-op: sel=00 with reserved scope completes", W_NONE_SEL)
    # f1: illegal encoding (clean with reserved scope) must not write back
    rec("CFXREG f1: cause_id", cfxreg)
    rec("CFXREG f1: cause_info", _cfx2rc_inst(root, c, rd=7))
    rec("CFXREG f1: the dirty line was not cleaned (memory old)", IMM[7])
    # f2: range with size = 0
    rec("CFXREG f2: cause_id", cfxreg)
    rec("CFXREG f2: cause_info", _cfx2rc_inst(root, c, rd=7))
    rec("CFXREG f2: the illegal command did not drop the dirty line", IMM[8])
    # f3: the same illegal encoding while D is disabled is still checked
    rec("CFXREG f3 (enable=0): cause_id", cfxreg)
    rec("CFXREG f3 (enable=0): cause_info", _cfx2rc_inst(root, c, rd=7))
    return recs


def _cfx2rc_inst(root: pathlib.Path, c: dict, rd: int) -> int:
    mod = _load("cfx5_regs_oracle", HERE / "check_cfx5_regs.py")
    op = mod.parse_opcode(root, "cfx2rc_crrr_cfx")
    ctrl_rc = c["rows"]["cfx_cache_ctrl"][1]
    return mod.encode(op, cfxcode=c["cfxha"],
                      cfx_cg=c["rows"]["cfx_cache_ctrl"][0],
                      cfx_rc=ctrl_rc, dst=rd)


def emit_inc(out, root: pathlib.Path) -> None:
    c = contract(root)
    w = lambda name, value: out.write(".equ %s, 0x%X\n" % (name, value))
    w("VA_BASE", VA_BASE)
    w("VA_R0", VA_R0)
    w("VA_R1", VA_R1)
    w("VA_D", VA_D)
    w("VA_CODE", VA_CODE)
    w("PA_L1E", PA_L1E)
    w("PA_L2", PA_L2)
    w("PA_R0", PA_R0)
    w("PA_R1", PA_R1)
    w("PA_D", PA_D)
    w("PA_CODE", PA_CODE)
    w("PA_HIGH", PA_HIGH)
    w("PTE_L1", PTE_L1)
    w("PTE_DATA", PTE_DATA)
    w("PTE_CODE", PTE_CODE)
    w("STUB_OLD", STUB_OLD)
    w("STUB_JUMP", STUB_JUMP)
    w("M_R0", M_R0)
    w("M_R1", M_R1)
    w("M_D", M_D)
    w("N_R0", N_R0)
    w("N_R1", N_R1)
    w("N_D", N_D)
    w("P_R0", P_R0)
    w("P_R1", P_R1)
    w("P_D", P_D)
    for i, imm in enumerate(IMM):
        w("IMM%d" % i, imm)
    w("CAT_IMM6_WORD", (0x4C50 << 48) | (IMM[6] << 32) | (0x7114 << 16))
    w("MMIO_LINE", MMIO_LINE)
    w("W_NONE_SEL", W_NONE_SEL)
    w("W_MMIO", W_MMIO)

    # Control words: side/operation/scope names from `contract-cache` §3.
    for side in ("I", "D", "ID"):
        for op in ("none", "clean", "invalidate", "flush"):
            for scope, sname in (("all", "ALL"), ("PA 单行", "LINE"),
                                 ("PA 区间", "RANGE")):
                key = "CTRL_%s_%s_%s" % (side, op.upper(), sname)
                w(key, control(c, side, op, scope))
    # Illegal encodings used by the fault cases (scope = reserved) and the
    # unconditional no-ops (`[15:14] = 00`, `op = none`).
    w("CTRL_ID_CLEAN_RESV", control(c, "ID", "clean", "reserved"))
    w("CTRL_D_INVAL_RANGE", control(c, "D", "invalidate", "PA 区间"))
    w("CTRL_D_CLEAN_RESV", control(c, "D", "clean", "reserved"))
    w("CTRL_NOSEL_FLUSH_RESV", control(c, "", "flush", "reserved"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", choices=["inc"], default="inc")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT)
    ap.add_argument("--check-geometry", action="store_true")
    args = ap.parse_args(argv)
    check_geometry()
    if args.check_geometry:
        print("gen_cfx5_maint: geometry ok (no data line in group 0, "
              "R0/R1 adjacent, one range page)")
        return 0
    if args.emit == "inc":
        emit_inc(sys.stdout, args.root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
