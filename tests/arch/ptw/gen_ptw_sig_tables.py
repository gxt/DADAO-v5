#!/usr/bin/env python3
"""gen_ptw_sig_tables.py — `ptw_sig.S` 的几何与期望值（`m16-chipyard-018`）。

**单一真源**：本文件同时给出

  * 汇编包含文件（`--emit inc`）里的符号（地址/PTE/数据 magic/命令编码）；
  * 宿主判据（`check_ptw_rtl.py`）使用的**签名槽期望**；
  * `--selfcheck`：与 `tests/arch/ptw/expected.yaml`（`m16-testcases-010` 的
    QEMU/gem5 期望，单一真源）逐槽比对，缺项/漂移即 FAIL。

判据来源（不写魔数）：

  * cause 大类位号与子原因位号：`.tao/contracts/contract-see.md` §6.1/§6.1.1，
    并与 `spec/DADAO-12 §3.6` 逐位互校（复用 `check_ptw_regs.bit_table`）；
  * TLB 命令编码（op/scope/ASID_ANY）：`.tao/contracts/contract-tlb.md` TLB-19；
  * 页表几何/PTE 位域：`spec/DADAO-12 §2.2.3/§2.2.4`；
  * `arch-ptw-002/006/007` 的签名槽期望：`tests/arch/ptw/expected.yaml`
    （本文件的 `expected_slots()` 由几何独立算出，`--selfcheck` 双向核对）。

几何取 QEMU/gem5 载体（`ptw_carrier_tlb.py`）的同一组数据地址与 PTE 值，
因此三方的逐槽签名可以**逐字节**比较：RTL 不需要另一套期望。

用法：
  gen_ptw_sig_tables.py --emit inc            # 汇编包含文件（stdout）
  gen_ptw_sig_tables.py --expected [--case N] # 打印期望槽
  gen_ptw_sig_tables.py --selfcheck           # 与 expected.yaml 双向核对
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_REPO = HERE.parents[2]


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "_ptw_regs_checker_for_sig", str(HERE / "check_ptw_regs.py"))
    if spec is None or spec.loader is None:
        raise SystemExit("gen_ptw_sig_tables: 无法加载 check_ptw_regs.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 几何（与 `ptw_carrier_tlb.py` 的 QEMU 场景同一组值）
# ---------------------------------------------------------------------------
PT_L1 = 0x7FF0_0000          # L1 表（64 KiB 对齐，PA）
PT_L2 = 0x7FF2_0000          # L2 表（64 KiB 对齐，PA）
DATA_BASE = 0x6000_0000      # DA；DB/DC 按 QEMU 的 16/32 MiB 偏移
DA, DB, DC = DATA_BASE, 0x6100_0000, 0x6200_0000
DD = 0x6300_0000             # G 条目的第二个目标（case 005）
VA0, VA1 = 0x0, 0x1_0000
VA_BASE = 0x200_0000_0000    # VA = PA + 2 TiB（VA[47:42] = 0）

# 013 的两个地址（各承载的同一组值）：
#   cfx_pmem SRAM 窗口 = cfx32 内部偏移 0x3ff_0000_0000 + 0x1000（`DADAO-12 §4.9`）
#   保留 cfx 的普通 ld：cfxha 6..14 / 16..31 / 35..61（`DADAO-12 §1`）
PMEM_SRAM = (32 << 42) | 0x3FF_0000_1000
RESERVED_CFX = (6 << 42) | 0x40

# 三种运行模式共用的 HSJU（H|S|U；J 不测）
HSJU_ALL = 0xD

# RTL 上运行期**观测不到**的槽：{case: {slot: 观测值}}（登记在
# `tests/arch/expected-divergences.yaml`，`--selfcheck` 双向核对）。
# 当前无登记差异：ADWBFAIL 不做用例（用户 2026-11-25 裁定），`DIV-14` 已删除。
RTL_DIVERGED_SLOTS = {}

M1 = 0x1122_3344_5566_7788
M2 = 0x99AA_BBCC_DDEE_FF00
M3 = 0x0F1E_2D3C_4B5A_6978
M4 = 0xA1B2_C3D4_E5F6_0718

PTE_P, PTE_SP, PTE_D, PTE_A = 1, 2, 4, 8
PTE_G, PTE_X, PTE_W, PTE_R = 0x10, 0x20, 0x40, 0x80
PPN_MASK = 0x00FF_FFFF_FFFF_0000
SPPN_MASK = 0x00FF_FFFF_E000_0000

# `cfx_ptw_tlb_control`（`contract-tlb` TLB-19）：op[1:0]、scope[3:2]、bit4 = ASID_ANY
OP_NONE, OP_CLEAN, OP_INVALID, OP_FLUSH = 0, 1, 2, 3
SCOPE_ALL, SCOPE_VA, SCOPE_RANGE, SCOPE_RESERVED = 0, 1, 2, 3


def pte_leaf(pa, hsju=HSJU_ALL, r=True, w=True, x=True, g=False, a=False,
             d=False, frags=0xFF):
    """64 KiB 叶 PTE（`spec/DADAO-12 §2.2.4`）。

    `HSJU_ALL` = H|S|U：与 QEMU 载体同一组值（同一页在 H/S/U 下都允许，
    所以三方逐槽比较与运行模式无关；J 不测，用户 2026-11-22 裁定）。
    """
    v = ((hsju & 0xF) << 60) | (pa & PPN_MASK) | ((frags & 0xFF) << 8)
    if r:
        v |= PTE_R
    if w:
        v |= PTE_W
    if x:
        v |= PTE_X
    if g:
        v |= PTE_G
    if a:
        v |= PTE_A
    if d:
        v |= PTE_D
    return v | PTE_P


def pte_table(pa):
    """L1 表项：指向下一级表（SP = 0、P = 1）。"""
    return (pa & PPN_MASK) | PTE_P


def pte_super(pa, hsju=HSJU_ALL, frags=0xFF):
    """512 MiB 超页（`spec/DADAO-12 §2.2.3`）。"""
    return (((hsju & 0xF) << 60) | (pa & SPPN_MASK) | ((frags & 0xFF) << 8)
            | PTE_R | PTE_W | PTE_X | PTE_SP | PTE_P)


# 初始 L1：VA 0 → L2；VA 2 TiB → PA 0（超页，供探针自己的表页之外使用）；
# VA 2 TiB + 1.5 GiB → PA 1.5 GiB（超页，覆盖 PT_L1/PT_L2/DA/DB/DC）。
L1_INIT = {
    0x0000: pte_table(PT_L2),
    0x1000: pte_super(0),
    0x1003: pte_super(DATA_BASE),
}

PTE_DA_A0D0 = pte_leaf(DA, a=False, d=False)
PTE_DA_A1D1 = pte_leaf(DA, a=True, d=True)
PTE_DB_A0D0 = pte_leaf(DB, a=False, d=False)
PTE_DC_A0D0 = pte_leaf(DC, a=False, d=False)

PT_L1B = 0x7FF4_0000         # 第二张 L1（case 008：换 PTBR 不隐含失效）
PT_L2B = 0x7FF6_0000         # L1B 的 L2（L1B[0] → L2B[0] = DB 叶 PTE）
L1B_INIT = {0x0000: pte_table(PT_L2B)}
L2B_INIT = {0x0000: PTE_DB_A0D0}

# 每个 case 的初始 L2 表项（索引 = VA[28:16]）
L2_INIT = {
    1: {0: PTE_DA_A0D0},                              # 001 fill + hit
    2: {0: PTE_DA_A0D0},
    3: {0: PTE_DA_A0D0, 1: PTE_DB_A0D0},
    4: {0: PTE_DA_A0D0, 1: PTE_DB_A0D0},
    5: {0: PTE_DA_A0D0, 1: pte_leaf(DB, g=True)},
    6: {0: PTE_DA_A0D0, 1: PTE_DB_A0D0},
    7: {0: PTE_DA_A0D0},
    8: {0: PTE_DA_A0D0, 1: PTE_DB_A0D0},
    9: {0: PTE_DA_A0D0},
    10: {},                                           # 未映射（P=0）
    11: {0: PTE_DA_A0D0},
    12: {0: PTE_DA_A0D0},
    13: {},                                           # cfx 空间旁路：空表 + 保留 cfx
}

CASES = tuple(sorted(L2_INIT))


# ---------------------------------------------------------------------------
# 期望槽（几何独立算出；`--selfcheck` 与 expected.yaml 双向核对）
# ---------------------------------------------------------------------------
def _cause_value(name):
    return 1 << load_checker().bit_table(_REPO)["class"][name]


def expected_slots(case: int) -> list:
    if case == 13:
        # [旁路窗口写后回读, 保留 cfx 的 cause_id（CFXMEM）, cause_info（= 访问地址）]
        return [M1, _cause_value("CFXMEM"), RESERVED_CFX]
    if case == 2:
        # [填充读到的值, 命中读到的值, 被改写后的叶 PTE]
        return [M1, M1, pte_leaf(DB)]
    if case == 6:
        # [clean 前 PTE(A/D=0), clean 回写后 PTE(A/D=1), invalid 后 PTE(A/D=0)]
        return [PTE_DA_A0D0, PTE_DA_A1D1, PTE_DB_A0D0]
    if case == 7:
        # [flush 回写后的 PTE, 删除后重走页表读到的值]（页表在内存里；
        # ADWBFAIL 不做用例，用户 2026-11-25 裁定）
        return [PTE_DA_A1D1, M2]
    return []


def signature_cases() -> dict:
    return {c: expected_slots(c) for c in (2, 6, 7, 13)}


def rtl_slots(case: int) -> list:
    """RTL 承载应产出的槽：规范期望，登记的差异槽换成 RTL 观测值。"""
    slots = list(expected_slots(case))
    for idx, value in (RTL_DIVERGED_SLOTS.get(case) or {}).items():
        slots[idx] = value
    return slots


# ---------------------------------------------------------------------------
# 汇编包含文件
# ---------------------------------------------------------------------------
def _equ(name, value):
    return ".equ %-20s, 0x%016x" % (name, value)


def emit_inc() -> str:
    table = load_checker().bit_table(_REPO)
    cls = table["class"]
    out = [
        "@@ ptw_sig_tables.inc — generated by tests/arch/ptw/gen_ptw_sig_tables.py",
        "@@ Do not edit: geometry, PTEs and cause encodings come from there.",
        "",
        _equ("PT_L1", PT_L1),
        _equ("PT_L2", PT_L2),
        _equ("PT_L1B", PT_L1B),
        _equ("PT_L2B", PT_L2B),
        _equ("VA_BASE", VA_BASE),
        _equ("VA0", VA0),
        _equ("VA1", VA1),
        _equ("VA_DA", VA_BASE + DA),
        _equ("VA_DB", VA_BASE + DB),
        _equ("VA_DC", VA_BASE + DC),
        _equ("PA_DA", DA),
        _equ("PA_DB", DB),
        _equ("PA_DC", DC),
        _equ("VA_DD", VA_BASE + DD),
        _equ("PA_DD", DD),
        _equ("M1", M1),
        _equ("M2", M2),
        _equ("M3", M3),
        _equ("M4", M4),
        _equ("PMEM_SRAM", PMEM_SRAM),
        _equ("RESERVED_CFX", RESERVED_CFX),
        _equ("PTE_DA_A0D0", PTE_DA_A0D0),
        _equ("PTE_DA_A1D1", PTE_DA_A1D1),
        _equ("PTE_DB_A1D1", pte_leaf(DB, a=True, d=True)),
        _equ("PTE_DB_A0D0", PTE_DB_A0D0),
        _equ("PTE_DB_G", pte_leaf(DB, g=True)),
        _equ("PTE_DB_A1D0", pte_leaf(DB, a=True, d=False)),
        _equ("PTE_DB_G_NEW", pte_leaf(DD, g=True)),
        _equ("PTE_DC_A0D0", PTE_DC_A0D0),
        _equ("PTE_DD", pte_leaf(DD)),
        _equ("PTE_W0", pte_leaf(DA, w=False)),
        _equ("PTE_R0", pte_leaf(DA, r=False)),
        _equ("PTE_X0", pte_leaf(DA, x=False)),
        _equ("PTE_H0", pte_leaf(DA, hsju=0x0)),
        _equ("CTL_INVALID_ALL", (OP_INVALID & 3) | ((SCOPE_ALL & 3) << 2) | 0x10),
        _equ("CTL_INVALID_ALL_NOANY",
             (OP_INVALID & 3) | ((SCOPE_ALL & 3) << 2)),
        _equ("CTL_CLEAN_VA",
             (OP_CLEAN & 3) | ((SCOPE_VA & 3) << 2) | 0x10),
        _equ("CTL_INVALID_VA",
             (OP_INVALID & 3) | ((SCOPE_VA & 3) << 2) | 0x10),
        _equ("CTL_FLUSH_VA",
             (OP_FLUSH & 3) | ((SCOPE_VA & 3) << 2) | 0x10),
        _equ("CTL_INVALID_RANGE",
             (OP_INVALID & 3) | ((SCOPE_RANGE & 3) << 2) | 0x10),
        _equ("CTL_INVALID_RESERVED",
             (OP_INVALID & 3) | ((SCOPE_RESERVED & 3) << 2)),
        _equ("CTL_INVALID_RANGE_NOANY",
             (OP_INVALID & 3) | ((SCOPE_RANGE & 3) << 2)),
        "",
        "@@ cause_id 期望（`contract-see §6.1` 大类；`§6.1.1` 高位位图为扁平绝对位号）",
    ]
    for name in ("CFXMEM", "CFXPERM", "CFXREG"):
        out.append(_equ("CAUSE_" + name, 1 << cls[name]))
    # 扁平模型（ADR-0062 D1/D3）：PTW 权限/缺失只置高位位图，低位 cause = 0
    for name in ("DGPTRAP", "IGPTRAP", "NWPERM", "NRPERM", "NXPERM", "NHPERM"):
        out.append(_equ("CAUSE_" + name, 1 << table["sub"][name]))
    # 已删除的否定位：同义映射到非 PTW 的 CFXMEM（旧载体名保留，值按扁平模型）
    out.append(_equ("CAUSE_NONPTW", 1 << cls["CFXMEM"]))
    out += [
        "",
        '.section .ptl1, "aw"',
    ]
    for idx in sorted(L1_INIT):
        out.append(".org 0x%x" % (idx * 8))
        out.append(".dd.o64 0x%016x        @@ L1[%#x]" % (L1_INIT[idx], idx))
    out.append("")
    out.append('.section .ptl1b, "aw"')
    for idx in sorted(L1B_INIT):
        out.append(".org 0x%x" % (idx * 8))
        out.append(".dd.o64 0x%016x        @@ L1B[%#x]" % (L1B_INIT[idx], idx))
    out.append("")
    out.append('.section .ptl2b, "aw"')
    for idx in sorted(L2B_INIT):
        out.append(".org 0x%x" % (idx * 8))
        out.append(".dd.o64 0x%016x        @@ L2B[%d]" % (L2B_INIT[idx], idx))
    out.append("")
    out.append('.section .ptl2, "aw"')
    for case in CASES:
        out.append(".if PTW_CASE == %d" % case)
        for idx in sorted(L2_INIT[case]):
            out.append(".org 0x%x" % (idx * 8))
            out.append(".dd.o64 0x%016x        @@ L2[%d]" % (L2_INIT[case][idx],
                                                            idx))
        if not L2_INIT[case]:
            out.append(".org 0x0")
            out.append(".dd.o64 0")
        out.append(".endif")
        # `.org` 是绝对的；不同 case 的段只保留一个（.if 选择），故可重复。
    # 首行 L2[0..7] 显式定义到 0x40：RTL 的 PA RAM 上电不保证为 0，未写到的 L2 槽
    # 会读到随机 PTE（`m17-chipyard-001`：case 010 的 L2[1] 曾读成 H=1/R=0 ⇒
    # NRPERM）。`.org` 只能前进，故在 case 表项之后补零到 0x40。
    out.append(".org 0x38")
    out.append(".dd.o64 0")
    out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
def selfcheck() -> int:
    import yaml

    problems = []
    path = HERE / "expected.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:                      # noqa: BLE001
        print("gen_ptw_sig_tables: cannot read %s: %s" % (path, exc))
        return 1
    declared = {}
    for entry in doc.get("cases") or []:
        sig = []
        for chk in entry.get("checks") or []:
            sig += [int(v) for v in (chk.get("signature") or [])]
        if sig:
            declared[entry.get("id")] = sig
    live = {}
    for case in (2, 6, 7, 13):
        cid = "arch-ptw-%03d" % case
        live[cid] = expected_slots(case)
        if live[cid] != declared.get(cid):
            problems.append("%s: 几何期望 %r ≠ expected.yaml %r"
                            % (cid, live[cid], declared.get(cid)))
    # RTL 差异必须登记在 expected-divergences.yaml（逐槽、含 close_when）。
    div_path = HERE.parent / "expected-divergences.yaml"
    try:
        div_doc = yaml.safe_load(div_path.read_text(encoding="utf-8"))
    except Exception as exc:                      # noqa: BLE001
        problems.append("cannot read %s: %s" % (div_path, exc))
        div_doc = {}
    registered = {}
    for entry in (div_doc or {}).get("divergences") or []:
        if not isinstance(entry, dict) or "chipyard" not in (
                entry.get("scope") or []):
            continue
        if (entry.get("kind") == "temporary" or entry.get("slots")) \
                and not entry.get("close_when"):
            problems.append("差异 %s 缺 close_when" % entry.get("id"))
        for slot in entry.get("slots") or []:
            if not isinstance(slot, dict):
                continue
            cid = slot.get("case")
            registered.setdefault(cid, {})[int(slot["slot"])] = int(
                slot["chipyard"])
    for case, slots in RTL_DIVERGED_SLOTS.items():
        cid = "arch-ptw-%03d" % case
        if registered.get(cid) != slots:
            problems.append("%s: RTL 差异 %r 与 expected-divergences.yaml %r 不符"
                            % (cid, slots, registered.get(cid)))
    if registered and not RTL_DIVERGED_SLOTS:
        problems.append("expected-divergences.yaml 仍登记 RTL 逐槽例外 %r，"
                        "但本生成器无对应差异（ADWBFAIL 不做用例）" % (registered,))
    extra = sorted(set(declared) - set(live))
    if extra:
        problems.append("expected.yaml 还有已接线签名未在本生成器登记: %r" % extra)
    if problems:
        for p in problems:
            print("  [FAIL] %s" % p)
        print("gen_ptw_sig_tables: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("gen_ptw_sig_tables: selfcheck PASS（%d 条签名 case，%d 槽；"
          "与 expected.yaml 逐槽相同）"
          % (len(live), sum(len(v) for v in live.values())))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", choices=["inc"], default=None)
    ap.add_argument("--expected", action="store_true")
    ap.add_argument("--case", type=int, default=None, help="只打印该 case 的期望槽")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()

    if args.selfcheck:
        return selfcheck()
    if args.expected:
        cases = ([args.case] if args.case is not None
                 else [2, 6, 7, 13])
        for case in cases:
            print("case %d: %s" % (case, ", ".join("%#x" % v
                                                  for v in expected_slots(case))))
        return 0
    if args.emit == "inc":
        sys.stdout.write(emit_inc())
        return 0
    ap.error("--emit inc / --expected / --selfcheck 必填其一")


if __name__ == "__main__":
    sys.exit(main())
