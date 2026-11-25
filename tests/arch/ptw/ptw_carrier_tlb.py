#!/usr/bin/env python3
"""arch-ptw-001…015 — TLB / page-table-walk probes (`contract-tlb §11`, K3).

本文件是 `tests/arch/ptw/` 的**载体/生成器**（`m16-testcases-010` 由
`tools/testcases/arch/min_rom_probe_tlb.py` 迁入）：一个驱动、15 个 case、
每个检查一个 BootROM 镜像。期望清单在 `tests/arch/ptw/expected.yaml`；
`check_tlb.py` 是 `run_arch.py` 的驱动入口（`kind: driver`）。

Expectations are derived **at run time from the contracts**, never from the
QEMU implementation (AGENTS.md "Independent oracle"):

  * bitmap bit numbers: `.tao/contracts/contract-see.md` §6.1.1, cross-checked
    against `spec/DADAO-12 §3.6` (two independent tables; a disagreement aborts
    the run);
  * low cause values (`CFXMEM` = `1 << 1`, `CFXPERM` = `1 << 7`, `CFXREG` =
    `1 << 2`) and the **flat bitmap** rules (exactly one bit in the 64-bit
    word, `[15:0]` sync cause with `[63:32]` == 0, PTW bit with `[15:0]` == 0,
    `[31:16]`/`[39]`/`[47:40]`/`[57]`/`[63:58]` reserved): `contract-see §6.1`
    + `ADR-0062 D1/D2/D3`;
  * behaviour (fill only after a fully valid walk, hit does not re-read the
    PTE, `invalid`/`clean`/`flush` semantics, three address scopes,
    `ASID_ANY`/`G`, A/D write-back, writes to PTBR/ASID/`ptw_enable` do not
    invalidate, `ptw_enable = 0` bypass, `VA[47:42] != 0` bypass):
    `.tao/contracts/contract-tlb.md` TLB-05…TLB-43 and
    `spec/DADAO-12 §2.2.1–§2.2.6 / §3.6 / §4.5 / §5.2`.

Carrier: one driver, one boot ROM image per check, body in `cfx_hmon`
(`cfx3`/`hypv`) at the shared prelude's body slot.  The body and every
handler live in the BootROM, i.e. in cfx63's core-internal space, so **code
fetch never depends on PTW**; only the 64 KiB RAM window does.  Result:

  * the code/frames survive `ptw_enable = 0` and an all-zero page table
    (needed by 009/013), and no stack is required;
  * observation stays in-guest: `cfx2rd` of `cfx_hmon` `cg5 rc2/rc4`
    (`excp_cause_id` / `excp_cause_info`), PTE read-back, data markers — no
    `-d cpu` parsing and no host-side oracle;
  * verdict = semihosting SYS_EXIT (`ADR-0004 D5.8`): `0x00` pass,
    the assertion's ordinal inside the image (`0x01`–`0x7F`) = the failed
    assertion (guest FAIL range `0x01`–`0x7F`).

Fault checks install their own `cfx_hmon` hypv vector: the handler asserts the
whole 64-bit `excp_cause_id` (one bit; a PTW bit implies `[15:0]` == 0, a low
cause implies `[63:32]` == 0) / `cause_info`, then
`escape cfx_hmon, [cause_ip, 4]` resumes after the faulting instruction
(`TLB-37`: the `tlb_control` write completes synchronously, so a failed
`clean`/`flush` leaves the entry behind for the next instruction to observe).

Case ↔ contract (`.tao/contracts/contract-tlb.md §11`):

  001 fill + hit (TLB-08/TLB-10) — 002 hit does not re-read the PTE (TLB-07)
  — 003 `invalid`+`VA` (TLB-23) — 004 `invalid`+`range`, `range`&&`size=0` ⇒
  `CFXREG`, `scope=11` ⇒ `CFXREG`, `scope=all` ignores start/size
  (TLB-22/23/24) — 005 `ASID_ANY`/`G` (TLB-05/25/26) — 006 `clean` writes A/D
  back and keeps the entry vs `invalid` not writing back (TLB-17) — 007
  `flush` writes back + deletes, and the write-back failure path (`CFXMEM` +
  `[56] ADWBFAIL`, `cause_info` = PTE PA, entry kept; TLB-16/17/37) — 008
  PTBR/ASID/`ptw_enable` writes do not invalidate (TLB-29) — 009
  `ptw_enable = 0` ⇒ `CFXMEM` (no bitmap bit), TLB bypassed, no entry
  (TLB-41/43) — 010 unmapped page ⇒ `[52] DGPTRAP` (data) / `[48] IGPTRAP`
  (fetch) alone, `CFXMEM` = 0 (TLB-35) — 011 `W=0` write ⇒ `[37] NWPERM`, `R=0`
  read ⇒ `[36] NRPERM`, `X=0` fetch ⇒ `[38] NXPERM`, HSJU `H=0` ⇒
  `[35] NHPERM`, all with `CFXPERM` = 0 (TLB-32/34) — 012 a PTE change needs
  an explicit invalidate
  (TLB-07/18) — 013 `VA[47:42] != 0` bypasses PTW/TLB: `cfx_pmem` SRAM with
  an all-zero page table, reserved cfx ⇒ `CFXMEM` alone with PTW on *and* off
  (TLB-40) — 014 a write-back failure is entry-granular and stops
  the command: the entries before it are processed, the failing one keeps its
  state, the rest are untouched (TLB-37) — 015 `ILLI` at an IP inside the
  memory window: `cause_info` = the instruction word read back through the
  guest TLB page base (`ADR-0004 D5.6` ROM store, `contract-see §6.1`).

A/D write-back failure (007's second half) needs **no implementation-side
injection** here: PTBR points at a page table inside the read-only BootROM, so
the walk reads the leaf PTE but the atomic OR write-back cannot complete —
exactly the `spec/DADAO-12 §4.5` "read succeeds, write fails" case (task book
「载体提示」).  Moving that PTE into writable RAM makes the fault disappear,
which is one of the injected counter-examples used to prove the assertion is
reachable.

Usage:
  ptw_carrier_tlb.py                 # all 15 cases, all checks
  ptw_carrier_tlb.py --only arch-ptw-005
  ptw_carrier_tlb.py --list
  ptw_carrier_tlb.py --selfcheck     # contract tables + expected.yaml
  ptw_carrier_tlb.py --qemu PATH     # QEMU 或 qemu_gem5_shim.py（gem5 承载）
Exit code: 0 iff every requested check passed.
"""

import argparse
import os
import re
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))         # tests/arch/ptw -> repo root
_ARCH_SHARED = os.path.join(_REPO, "tools", "testcases", "arch")
if _ARCH_SHARED not in sys.path:
    sys.path.insert(0, _ARCH_SHARED)      # `node_probe_prelude.py`（跨 scope 共享）
if os.path.join(_REPO, "tools", "testcases", "lib") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "tools", "testcases", "lib"))
if os.path.join(_REPO, "tools", "infra") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "tools", "infra"))
if os.path.join(_REPO, "tests", "shared") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "tests", "shared"))
import node_probe_prelude as P  # noqa: E402
import paths as _paths  # noqa: E402
import signature  # noqa: E402  (签名流机制：解析/比对/word-builder 发射器，单一实现)

DEFAULT_QEMU = P.default_qemu()
QEMU = DEFAULT_QEMU
WORKDIR = os.path.join(P.TMP_ROOT, "arch_ptw_tlb")
SIG_OUT = os.path.join(WORKDIR, "signature.out")
TIMEOUT = 20

# 签名流（m16-testcases-002）：观测点实际值的**唯一载体**（README「观测通道」）。
# 缓冲区在 prelude 的 L1[3] 恒等超页内（0x6000_0000–0x7FFF_FFFF）⇒ 换 PTBR 前/
# 恢复后都可读写；预填数 > 每镜像观测点数，删一条观测 ⇒ 槽保持 0xdeadbeef。
SIG_BUF = 0x7000_0000
SIG_PREFILL = 8
SIG = signature.Emitter(P)

ROM_BASE = P.ROM_BASE

# env 契约里的栈（L1[3] 内；umon 也以 U 允许的同一超页）：与
# `common/env-README.md` 的缺省值相同。
ENV_STACK = 0x61FF_F000

# 该用例在目标模式下需要访问的 cfx（`modes.yaml` 的 `cfx_access`，由驱动传入
# `--cfx-access`；缺省为空 = 不声明、不做权限准备，与 `m16-testcases-017` 前
# 的 hmon 形态一致，hmon 下默认掩码本就允许源 cfx_hmon）。
CFX_ACCESS = []

# ---------------------------------------------------------------------------
# Expectations parsed from the contracts
# ---------------------------------------------------------------------------

CONTRACT_SEE = os.path.join(_REPO, ".tao", "contracts", "contract-see.md")
SPEC_SEE = os.path.join(_REPO, "spec", "DADAO-12-SEE-主管系统运行环境.md")
EXPECTED_YAML = os.path.join(_REPO, "tests", "arch", "ptw", "expected.yaml")

# `| `1 << 1` | `CFXMEM` | ...`      (contract-see §6.1)
_RE_CAUSE = re.compile(r"^\|\s*`1 << (\d+)`\s*\|\s*`([A-Z_]+)`")
# `| `[32]` | wyde2 权限类 | `NUPERM` | HSJU ... |`   (contract-see §6.1.1)
_RE_SUB = re.compile(r"^\|\s*`\[(\d+)\]`\s*\|[^|]*\|\s*`([A-Z_]+)`\s*\|")
# `| `[32]` | NUPERM | trigger ... |`   (spec/DADAO-12 §3.6, 3 columns)
_RE_SPEC_SUB = re.compile(r"^\|\s*`\[(\d+)\]`\s*\|\s*([A-Z_]+)\s*\|")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_contract():
    """Return (cause value by name, bitmap bit by name).

    The encoding is flat (`ADR-0062 D1`): a bitmap bit carries the whole reason
    by itself, so there is no "owning wyde" or target big class to record.
    """
    causes, sub_bits = {}, {}
    for line in _read(CONTRACT_SEE).splitlines():
        m = _RE_CAUSE.match(line)
        if m:
            causes[m.group(2)] = 1 << int(m.group(1))
            continue
        m = _RE_SUB.match(line)
        if m:
            bit, name = int(m.group(1)), m.group(2)
            if name in sub_bits:
                raise SystemExit("ptw_carrier_tlb: duplicate bitmap bit %r"
                                 % name)
            sub_bits[name] = bit
    if not causes or not sub_bits:
        raise SystemExit("ptw_carrier_tlb: cannot parse the contract tables "
                         "(%s §6.1/§6.1.1)" % CONTRACT_SEE)
    # §6.1.1 is the authority; DADAO-12 §3.6 must agree bit by bit.
    spec_bits = {m.group(2): int(m.group(1))
                 for m in (_RE_SPEC_SUB.match(x)
                           for x in _read(SPEC_SEE).splitlines()) if m}
    if not spec_bits:
        raise SystemExit("ptw_carrier_tlb: cannot parse spec/DADAO-12 §3.6")
    diff = sorted(set(spec_bits.items()) ^ set(sub_bits.items()))
    if diff:
        raise SystemExit("ptw_carrier_tlb: contract-see §6.1.1 and "
                         "spec/DADAO-12 §3.6 disagree: %r" % (diff,))
    return causes, sub_bits


CAUSE, SUB_BIT = parse_contract()

# `contract-see §6.1` + `ADR-0062 D1`: flat 64-bit bitmap -- `[15:0]` sync cause
# (with `[63:32]` == 0), or one `[38:32]`/`[56:48]` PTW bit (with `[15:0]` == 0).
LOW16 = 0xFFFF
HIGH32 = 0xFFFF_FFFF_0000_0000      # `[63:32]` -- must be 0 for a low cause
# `ADR-0062 D1` rule 4: these bits are deleted / reserved and always 0.
RESERVED = (0xFFFF << 16) | (1 << 39) | (0xFF << 40) | (1 << 57) | (0x3F << 58)


def sub_one_hot(name):
    """`1 << bit`, `bit` = the **absolute** bit number in `excp_cause_id`.

    `contract-see §6.1.1` lists the bits by absolute number (`DGPTRAP` is
    `[52]`), and the assertions compare the whole 64-bit word, so the value
    stays absolute.
    """
    if name not in SUB_BIT:
        raise SystemExit("ptw_carrier_tlb: %r is not in contract-see §6.1.1"
                         % (name,))
    return 1 << SUB_BIT[name]


# ---------------------------------------------------------------------------
# Machine layout (single source: contracts/machine.yaml + prelude)
# ---------------------------------------------------------------------------

# The prelude leaves PTBR = PT_PA (identity superpages over the 2 GiB RAM
# window) with `ptw_enable = 1` and an empty TLB.  Cases *extend that live
# table*: L1[0] (VA 0…512 MiB) becomes a 64 KiB-page window, L1[3]
# (0x6000_0000…0x7FFF_FFFF) keeps the identity mapping used for data pages,
# page tables and `exit_block` (so `exit_seq` always has a mapping).
PT_L1 = P.PT_PA                  # prelude L1 (extended in place)
L1B = 0x7FF1_0000                # second L1, 64 KiB aligned
L2A = 0x7FF2_0000                # L2 for PT_L1[0]
L2B = 0x7FF3_0000                # L2 for L1B[0]

DA, DB, DC, DD = 0x6000_0000, 0x6100_0000, 0x6200_0000, 0x6300_0000
VA0, VA1, VA2 = 0x0, 0x1_0000, 0x2_0000
PMEM_SRAM = P.PMEM_BASE + 0x1000     # cfx_pmem SRAM staging (prelude-cleared)
RESERVED_CFX = (6 << 42) + 0x40      # cfxha 6..14 / 16..31 / 35..61 are reserved

M1 = 0x1122_3344_5566_7788
M2 = 0x99AA_BBCC_DDEE_FF00
M3 = 0x0F1E_2D3C_4B5A_6978
M4 = 0xA1B2_C3D4_E5F6_0718

# `cfx_ptw` coordinates (`spec/DADAO-12 §4.5`)
PTW_HA = 4
PTBR_CG, PTBR_RC = 9, 0
PTW_ENABLE_CG, PTW_ENABLE_RC = 8, 8
TLB_CG = 12
TLB_CONTROL_RC, TLB_ASID_RC, TLB_START_RC, TLB_SIZE_RC = 0, 1, 2, 3
CAUSE_ID_RC, CAUSE_IP_RC, CAUSE_INFO_RC = 2, 3, 4
EXCP_VECTOR_RC, SWITCH_MODE_RC = 10, 8

# `cfx_ptw_tlb_control` (`TLB-19`): op[1:0], scope[3:2], bit4 = ASID_ANY
OP_NONE, OP_CLEAN, OP_INVALID, OP_FLUSH = 0, 1, 2, 3
SCOPE_ALL, SCOPE_VA, SCOPE_RANGE, SCOPE_RESERVED = 0, 1, 2, 3

PTE_P, PTE_SP, PTE_D, PTE_A = 1, 2, 4, 8
PTE_G, PTE_X, PTE_W, PTE_R = 0x10, 0x20, 0x40, 0x80
PPN_MASK = 0x00FF_FFFF_FFFF_0000
SPPN_MASK = 0x00FF_FFFF_E000_0000

# Registers: rd5/rd6/rd7 observations, rd10/11/12 cause frame, rd15/16/17
# scratch, rb3 address base, rd4 store source (rb16/rd8/rd9 = exit_seq).
SCRATCH, WORK, CREG = 15, 16, 17
RD_CID, RD_INFO, RD_IP, RD_BASE, RD_FAULTS = 10, 11, 12, 13, 14

HAND_OFF = 0x2000                # handler slot, body-relative

# ---------------------------------------------------------------------------
# Run modes (`m16-testcases-019`; `tests/arch/modes.yaml` 的允许集由 run_arch 判)
#
# hmon/smon/umon = hypv/supv/user 的当前模式监视器。进入/退出/权限准备**不**
# 在本文件重写：镜像里放的是共享 `tests/arch/common/env-{hmon,smon,umon}/env.S`
# 汇编出来的 `.env`/`.envtail`/`.envperm` 三段（同一 `env.lds` 布局），载体只
# 负责「固件段（power→hmon→PTW on）+ 本 case 的 body」。
#
# 为什么 body 仍在 ROM 而不在 RAM（与 cache/time/hart/pmem 的 asm body 不同）：
# 本载体的 15 条检查里，007/014 的判据是**只读页表**（A/D 回写失败，`TLB-37`）、
# 015 的判据是**只读内存窗口**的 `ILLI`，都需要一份由载体自己生成、运行期只读的
# ROM 内容；step5 固件的 ROM 内容固定，构造不出这些向量（`m16-testcases-019`
# 实测）。故本载体的 4 MiB 镜像同时承担「固件 + env + body」，ROM 仍是只读面。
# ---------------------------------------------------------------------------
MODES = ("hmon", "smon", "umon")
MODE = "hmon"                    # 由 `--mode` 设定（`main()`）
MODE_ROW = {"hmon": 3, "smon": 2, "umon": 0}       # `DADAO-12 §3.1`–`§3.4`
MONITOR_HA = {"hmon": 3, "smon": 2, "umon": 0}      # `§5.2`：当前模式监视器
MODE_CODE = {"hmon": 3, "smon": 2, "umon": 0}       # `spec/Kaiwu §7.1`

# 测试页 PTE 的 HSJU：H|S|U（`0xD`，J 不测 —— 用户 2026-11-22 裁定）。
# 三种运行模式各自只查自己那位（`DADAO-12 §2.2.5`），同一页在 H/S/U 下都允许
# ⇒ 页表项数值与运行模式无关，签名流三方逐槽比较不必按模式分叉；HSJU 的**拒绝**
# 面（谁缺谁拒）由 `arch-ptw-011` 逐模式单独构造。
HSJU_ALL = 0xD

ENV_DIRS = {mode: os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "common", "env-%s" % mode) for mode in MODES}
ENV_INC = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "common", "env")
ENV_LDS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "common", "env.lds")

# 镜像布局（ROM 内的偏移，`RESET_PC` 相对；env.lds 的四段由 defsym 现场传入）：
#   ENV_BASE + 0x0000 .env     共享环境入口（进入目标模式）
#   ENV_BASE + 0x1000 .body    本 case 的 body（含 handler，HAND_OFF 起）
#   ENV_BASE + 0x4000 .envtail 退出与签名输出
#   ENV_BASE + 0x5000 .envperm 权限准备/还原（只在 hypv 跑）
# body/handler 区 = [0x1000, 0x4000)，即 body 主体 ≤ 0x2000 B、handler ≤ 0x1000 B。
ENV_BASE = P.BOOTROM_BASE + 0x200000
ENV_BODY_OFF = 0x1000
ENV_TAIL_OFF = 0x4000
ENV_PERM_OFF = 0x5000
BODY_BASE = ENV_BASE + ENV_BODY_OFF
ENV_OFF = ENV_BASE - P.RESET_PC          # 预置段 `jump` 的目标（相对 RESET_PC）

# A guest FAIL code is the assertion's ordinal **inside its own image**
# (`0x01`–`0x7F`): every check is a separate boot-ROM image and the driver
# decodes the code against the check it just ran, so the ordinal is unambiguous
# and 15 cases × up to 9 assertions no longer has to fit in one flat scheme
# (that needed 135 > 0x7F, overlapping the machine-fault exit encodings).
MAX_FAIL_CODE = 0x7F


def pte_leaf(pa, hsju=HSJU_ALL, r=True, w=True, x=True, g=False, a=False,
             d=False, frags=0xFF):
    """64 KiB leaf PTE (`spec/DADAO-12 §2.2.4`).

    `hsju` defaults to `H|S|U` so the same test page is allowed in all three
    run modes (`§2.2.5`: only the current mode's bit is consulted); the
    per-mode *denial* vectors pass an explicit mask.
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
    """L1 entry pointing at an L2 table (SP = 0, P = 1)."""
    return (pa & PPN_MASK) | PTE_P


def pte_super(pa, hsju=HSJU_ALL, frags=0xFF):
    """512 MiB identity superpage (`spec/DADAO-12 §2.2.3`)."""
    return (((hsju & 0xF) << 60) | (pa & SPPN_MASK) | ((frags & 0xFF) << 8)
            | PTE_R | PTE_W | PTE_X | PTE_SP | PTE_P)


# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def xor_o(hb, hc, hd):
    """xor.o rdhb, rdhc, rdhd (opc 0x40, ha 0x0A)."""
    return (0x40 << 24) | (0x0A << 18) | (hb << 12) | (hc << 6) | hd


def or_o(hb, hc, hd):
    """or.o rdhb, rdhc, rdhd (opc 0x40, ha 0x09)."""
    return (0x40 << 24) | (0x09 << 18) | (hb << 12) | (hc << 6) | hd


def jump_rrii(rb, rd, off):
    """jump [rb, rd, imms12]: Addr = rb + rd + (imms12 << 2)."""
    imm = off & 0xFFF
    return (0x71 << 24) | (rb << 18) | (rd << 12) | (((imm >> 6) & 0x3F) << 6) | (imm & 0x3F)


def load_rd(rd, val):
    return P.load_rd(rd, val)


def load_rb(rb, val):
    return P.load_rb(rb, val)


# ---------------------------------------------------------------------------
# Guest assertion helpers (each one ends in a reachable FAIL exit)
# ---------------------------------------------------------------------------

class Check:
    """One boot ROM image + the assertion list that names its fail codes."""

    def __init__(self, case_no, case_id, label, desc):
        self.case_no = case_no
        self.case_id = case_id
        self.label = label
        self.desc = desc
        self.s = P.Seq()
        self.fields = []
        self._n = 0
        self.handlers = None
        self.words_at = None
        self.image_at = None     # ROM image offsets (read-only page tables)
        self.rom_at = None       # 复位窗口尾部等 prelude 之外的 ROM 偏移
        self.hmon_extra = None   # words run inside the prelude hmon segment
        self.expect = None       # (low cause name or None, bitmap bit name or None)
        self.sig_want = []       # 签名流期望（每个 `sig_obs` 一项；空 = 不接线）

    def code(self, desc):
        self.fields.append(desc)
        if len(self.fields) > MAX_FAIL_CODE:
            raise SystemExit("ptw_carrier_tlb: case %d/%s has more than %d "
                             "assertions; extend the fail-code scheme"
                             % (self.case_no, self.label, MAX_FAIL_CODE))
        return len(self.fields)

    def label_name(self, stem):
        self._n += 1
        return "%s_%d" % (stem, self._n)

    def body(self):
        """Body words + handlers, padded to the ROM layout's body window."""
        blob = bytearray(P.words_to_bytes(self.s.resolve()))
        for table in (self.handlers or {}, self.words_at or {}):
            for off in sorted(table):
                if off < len(blob):
                    raise SystemExit("ptw_carrier_tlb: %s/%s: offset 0x%x "
                                     "overlaps the body" % (self.case_id,
                                                            self.label, off))
                while len(blob) < off:
                    blob += P.words_to_bytes([P.swym()])
                blob += P.words_to_bytes(table[off])
        window = ENV_TAIL_OFF - ENV_BODY_OFF
        if len(blob) > window:
            raise SystemExit("ptw_carrier_tlb: %s/%s: body+handlers %d B exceed "
                             "the %d B body window"
                             % (self.case_id, self.label, len(blob), window))
        return bytes(blob)


# ---------------------------------------------------------------------------
# Image build: prelude (power -> hmon -> PTW on) + shared env + body
# ---------------------------------------------------------------------------
class SetupError(RuntimeError):
    """缺件/工具链/布局错误（退出码 2，不当作判据失败）。"""


TOOL_NAMES = ("llvm-mc", "ld.lld", "llvm-objcopy")


def toolchain(bin_dir=None):
    bin_dir = os.path.abspath(bin_dir) if bin_dir else _paths.host_toolchain_bin()
    tools = {name: os.path.join(bin_dir, name) for name in TOOL_NAMES}
    for name, path in tools.items():
        if not os.path.isfile(path):
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
    for path in (ENV_LDS, os.path.join(ENV_INC, "cfx_perm.inc")):
        if not os.path.isfile(path):
            raise SetupError("缺件 %s（common/env 环境）" % path)
    return tools


def _run(cmd, timeout=120):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout,
                          stdin=subprocess.DEVNULL)
    return proc.returncode, proc.stdout


def assemble_env(mode, tools, work, sig_slots):
    """Assemble `common/env-<mode>/env.S` at `ENV_BASE`; return the flat bytes.

    The environment is the shared one: entry/exit/exception-vector/permission
    preparation are **not** re-implemented here.  Only the addresses the body
    contract names are passed in (signature buffer/slots, body source, tail,
    plus the umon overrides for a ROM-resident body: no copy, tail in ROM, and
    the L1 entry that is reached through this carrier's PTBR).
    """
    obj = os.path.join(work, "env_%s.o" % mode)
    elf = os.path.join(work, "env_%s.elf" % mode)
    image = os.path.join(work, "env_%s.bin" % mode)
    cmd = [tools["llvm-mc"], "--triple=dadao-unknown-elf", "-filetype=obj",
           "-I", os.path.join(_REPO, "tests", "shared", "asm"),
           "-I", ENV_INC,
           "--defsym", "ENV_SIG_BUF=%#x" % SIG_BUF,
           "--defsym", "ENV_SIG_SLOTS=%d" % sig_slots,
           "--defsym", "ENV_STACK=%#x" % ENV_STACK,
           "--defsym", "ENV_BODY_SRC=%#x" % BODY_BASE,
           "--defsym", "ENV_TAIL=%#x" % (ENV_BASE + ENV_TAIL_OFF)]
    for cfx in CFX_ACCESS:
        cmd += ["--defsym", "ENV_CFX_ACCESS_%d=1" % cfx]
    if MODE != "hmon" and CFX_ACCESS:
        # 同步故障处理程序在「当前模式监视器」名下运行：它对声明的 cfx 的访问
        # 源是 cfx_smon(2)/cfx_umon(0)，环境必须同时清这两位的源掩码
        # （`DADAO-12 §3`：位索引 = 源 cfx、0 = 允许）。
        allow = 0xFFFF_FFFF_FFFF_FFF7 & ~(1 << monitor_cfx())
        if allow >= 1 << 63:            # llvm-mc 只收 64 位有符号整数
            allow -= 1 << 64
        cmd += ["--defsym", "ENV_PERM_ALLOW=%d" % allow]
    if mode == "umon":
        # body 已在 ROM：U 页不需要拷贝；tail 也在 ROM；L1[3] 的 U 位写进本载体
        # 的 L1（PTBR = PT_L1），不是 step5 固件的 PA 0 表。
        cmd += ["--defsym", "ENV_COPY_OCTAS=0",
                "--defsym", "ENV_UENTRY=%#x" % BODY_BASE,
                "--defsym", "ENV_UTAIL=%#x" % (ENV_BASE + ENV_TAIL_OFF),
                "--defsym", "ENV_UPAGE_PTE_PA=%#x" % (PT_L1 + 3 * 8),
                "--defsym", "ENV_TLB_INVALIDATE=1"]
    rc, out = _run(cmd + [os.path.join(ENV_DIRS[mode], "env.S"), "-o", obj])
    if rc != 0:
        raise SetupError("llvm-mc env-%s rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-600:]))
    rc, out = _run([tools["ld.lld"], "-T", ENV_LDS,
                    "--defsym", "ENTRY=%#x" % ENV_BASE,
                    "--defsym", "ENV_BODY_OFF=%#x" % ENV_BODY_OFF,
                    "--defsym", "ENV_TAIL_OFF=%#x" % ENV_TAIL_OFF,
                    "--defsym", "ENV_PERM_OFF=%#x" % ENV_PERM_OFF,
                    obj, "-o", elf])
    if rc != 0:
        raise SetupError("ld.lld env-%s rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-600:]))
    # 只取三段各自的实际字节（`-O binary` 的整段产物把 4 KiB 对齐空洞也算进去，
    # 会把 body 窗口盖住）；再由 `build_image` 按 env.lds 的偏移逐段放置。
    sections = {}
    # 输出段名（`env.lds` 的 `.env : { *(.envcode) }` 等）；三个 env 相同。
    for name, off, limit in ((".env", 0, ENV_BODY_OFF),
                             (".envtail", ENV_TAIL_OFF,
                              ENV_PERM_OFF - ENV_TAIL_OFF),
                             (".envperm", ENV_PERM_OFF,
                              P.BOOTROM_SIZE - ENV_PERM_OFF)):
        out_bin = image + name
        rc, out = _run([tools["llvm-objcopy"], "-O", "binary",
                        "--only-section=" + name, elf, out_bin])
        if rc != 0:
            raise SetupError("llvm-objcopy env-%s %s rc=%d: %s"
                             % (mode, name, rc,
                                out.decode("utf-8", "replace")[-600:]))
        with open(out_bin, "rb") as f:
            blob = f.read()
        if len(blob) > limit:
            raise SetupError("env-%s %s 段 %d B 越过窗口（%d B）"
                             % (mode, name, len(blob), limit))
        sections[name] = (off, blob)
    return sections


def build_image(chk, tools, work):
    """Full 4 MiB boot ROM: prelude + shared env + this check's body."""
    blob = chk.body()
    sections = assemble_env(MODE, tools, work, len(chk.sig_want))
    rom = bytearray(P.build_rom([], image_at=chk.image_at,
                                hmon_extra=chk.hmon_extra, entry=ENV_OFF))
    env_off = ENV_BASE - P.BOOTROM_BASE
    body_off = env_off + ENV_BODY_OFF
    spans = [("body", body_off, body_off + len(blob))]
    for name, (off, section) in sorted(sections.items()):
        spans.append((name, env_off + off, env_off + off + len(section)))
        rom[env_off + off:env_off + off + len(section)] = section
    if body_off + len(blob) > env_off + ENV_TAIL_OFF:
        raise SetupError("body %d B 越过 tail 起点（layout 冲突）" % len(blob))
    rom[body_off:body_off + len(blob)] = blob
    prelude = (P.RESET_PC - P.BOOTROM_BASE,
               P.RESET_PC - P.BOOTROM_BASE + P.BODY_OFF)
    for label, start, end in spans + [("prelude",) + prelude]:
        for off in sorted(chk.image_at or {}):
            span = len(P.words_to_bytes((chk.image_at or {})[off]))
            if start < off + span and off < end:
                raise SetupError("%s 段与 image_at 0x%x 重叠" % (label, off))
    for off in sorted(chk.rom_at or {}):
        words = P.words_to_bytes(chk.rom_at[off])
        if off + len(words) > P.BOOTROM_SIZE:
            raise SetupError("rom_at 0x%x 越过 ROM 末尾" % off)
        for label, start, end in spans + [("prelude",) + prelude]:
            if start < off + len(words) and off < end:
                raise SetupError("rom_at 0x%x 与 %s 段重叠" % (off, label))
        rom[off:off + len(words)] = words
    return bytes(rom)


def _restore_identity(seq):
    """Restore the prelude identity table and `ptw_enable = 1` on `seq`.

    A check may be running with PTBR pointing at another (or an all-zero) table;
    both a failing assertion and the signature dump must still be able to reach
    their blocks instead of turning into an unhandled fault.
    """
    seq.e(*load_rd(CREG, PT_L1 & PPN_MASK))
    seq.e(P.cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, CREG))
    seq.e(*load_rd(CREG, 1))
    seq.e(P.cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, CREG))
    seq.e(*load_rd(CREG, 0x12))            # invalid, all, ASID_ANY
    seq.e(P.cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, CREG))


def _fail_exit(chk, seq, code):
    """Exit with `code` from any guest state (restore the identity map first)."""
    _restore_identity(seq)
    seq.e(*P.exit_seq(code))
    seq.e(P.jump_rel(0))                   # SYS_EXIT must not fall through


def _branch_ok(seq, chk, work, ok_label, code):
    seq.b("z", work, ok_label)
    _fail_exit(chk, seq, code)
    seq.mark(ok_label)


def a_eq(chk, seq, rd, value, desc):
    """Assert rd == value, otherwise exit with this assertion's fail code."""
    code = chk.code(desc)
    ok = chk.label_name("ok")
    seq.e(*load_rd(SCRATCH, value))
    seq.e(xor_o(WORK, rd, SCRATCH))
    _branch_ok(seq, chk, work=WORK, ok_label=ok, code=code)


def a_same(chk, seq, rd1, rd2, desc):
    """Assert rd1 == rd2 (register-to-register, no immediate needed)."""
    code = chk.code(desc)
    ok = chk.label_name("ok")
    seq.e(or_o(WORK, rd1, rd1))
    seq.e(xor_o(WORK, WORK, rd2))
    _branch_ok(seq, chk, work=WORK, ok_label=ok, code=code)


def a_masked(chk, seq, rd, mask, expected, desc):
    """Assert (rd & mask) == expected (masked comparison, no shifts needed)."""
    code = chk.code(desc)
    ok = chk.label_name("ok")
    seq.e(*load_rd(SCRATCH, mask))
    seq.e(P.and_o(WORK, rd, SCRATCH))
    seq.e(*load_rd(SCRATCH, expected))
    seq.e(xor_o(WORK, WORK, SCRATCH))
    _branch_ok(seq, chk, work=WORK, ok_label=ok, code=code)


def st64(chk, addr, value, rb=3, rd=4):
    chk.s.e(*load_rb(rb, addr))
    chk.s.e(*load_rd(rd, value))
    chk.s.e(P.st_o(rd, rb, 0))


def ld64(chk, addr, rd, rb=3):
    chk.s.e(*load_rb(rb, addr))
    chk.s.e(P.ld_o(rd, rb, 0))


def ld_va(chk, va, rd=5):
    chk.s.e(*load_rb(3, va))
    chk.s.e(P.ld_o(rd, 3, 0))


def st_va(chk, va, value, rd=4):
    chk.s.e(*load_rb(3, va))
    chk.s.e(*load_rd(rd, value))
    chk.s.e(P.st_o(rd, 3, 0))


def jump_va(chk, va):
    chk.s.e(*load_rb(3, va))
    chk.s.e(*load_rd(CREG, 0))
    chk.s.e(jump_rrii(3, CREG, 0))


def tlb_reg(chk, rc, value):
    chk.s.e(*load_rd(CREG, value))
    chk.s.e(P.cfx2rc(PTW_HA, TLB_CG, rc, CREG))


def tlb_cmd(chk, op, scope, asid_any=False, start=None, size=None):
    if start is not None:
        tlb_reg(chk, TLB_START_RC, start)
    if size is not None:
        tlb_reg(chk, TLB_SIZE_RC, size)
    tlb_reg(chk, TLB_CONTROL_RC,
            (op & 0x3) | ((scope & 0x3) << 2) | (0x10 if asid_any else 0))


def set_ptbr(chk, pa):
    chk.s.e(*load_rd(CREG, pa & PPN_MASK))
    chk.s.e(P.cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, CREG))


def set_ptw(chk, on):
    chk.s.e(*load_rd(CREG, 1 if on else 0))
    chk.s.e(P.cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, CREG))


def set_asid(chk, value):
    chk.s.e(*load_rd(CREG, value))
    chk.s.e(P.cfx2rc(PTW_HA, TLB_CG, TLB_ASID_RC, CREG))


def monitor_cfx():
    """`DADAO-12 §5.2`: the current run mode's monitor cfx (U→0, S→2, H→3)."""
    return MONITOR_HA[MODE]


def read_cause(chk, rd=None):
    rd = RD_CID if rd is None else rd
    chk.s.e(P.cfx2rd(monitor_cfx(), 5, CAUSE_ID_RC, rd))


def record_baseline(chk):
    """Snapshot the monitor's pre-existing cause frame before the check runs.

    `hmon`: the prelude's `trap cfx_hmon` frame; `smon`/`umon`: the monitor's
    frame is untouched (0).  Success-path checks then only have to prove that
    no *new* frame appeared: the snapshot's `[63:32]` and every reserved bit
    are asserted to be 0, which is the `contract-see §6.1` + `ADR-0062 D1`
    "a low cause carries no bitmap bit" statement.
    """
    chk.s.e(P.cfx2rd(monitor_cfx(), 5, CAUSE_ID_RC, RD_BASE))
    a_masked(chk, chk.s, RD_BASE, HIGH32 | RESERVED, 0,
             "baseline cause_id carries no bitmap bit and no reserved bit")


def assert_no_new_fault(chk, rd=7):
    read_cause(chk, rd)
    a_same(chk, chk.s, rd, RD_BASE, "no exception: cause_id unchanged")


def install_table(chk, pages, l1=PT_L1, l2=L2A, invalidate=True):
    """L1[0] -> `l2`; `pages` = {L2 index: PTE}; then drop the TLB."""
    for idx in sorted(pages):
        st64(chk, l2 + idx * 8, pages[idx])
    st64(chk, l1, pte_table(l2))
    if invalidate:
        tlb_cmd(chk, OP_INVALID, SCOPE_ALL, asid_any=True)


def install_second_table(chk, pages):
    """L1B[0] -> L2B plus the identity superpage for the exit block."""
    for idx in sorted(pages):
        st64(chk, L2B + idx * 8, pages[idx])
    st64(chk, L1B + 0 * 8, pte_table(L2B))
    st64(chk, L1B + 3 * 8, pte_super(0))


def arm_fault(chk):
    """Zero the fault counter before the access that must fault."""
    chk.s.e(*load_rd(RD_FAULTS, 0))


def a_fault_count(chk, n):
    """The handler must have run exactly `n` times (no silent fall-through)."""
    a_eq(chk, chk.s, RD_FAULTS, n, "the fault handler ran %d time(s)" % n)


def set_handler(chk, words):
    """Install this check's handler as the current run mode monitor's vector.

    `hmon`: `cfx_hmon`'s hypv row (unchanged shape).  `smon`/`umon`: the
    monitor's **own mode row** (`cg2` supv / `cg0` user) plus
    `switch_run_mode = hypv`, so the synchronous exception entered from
    supv/user runs the handler in hypv as that monitor (`DADAO-12 §5.2`
    steps 5-6; same shape as `common/env-umon`'s fail-closed vector).  The
    handler then reads its own `cg5` (self) and resumes with `escape`.
    """
    chk.s.e(*load_rd(22, BODY_BASE + HAND_OFF))
    chk.s.e(P.cfx2rc(monitor_cfx(), MODE_ROW[MODE], EXCP_VECTOR_RC, 22))
    if MODE != "hmon":
        # 处理程序留在**触发模式**（supv/user）：这样它用到的 cfx 掩码/委派与
        # body 完全相同（环境已按该模式行打开），不需要 hypv 行的额外授权。
        chk.s.e(*load_rd(23, MODE_CODE[MODE]))
        chk.s.e(P.cfx2rc(monitor_cfx(), MODE_ROW[MODE], SWITCH_MODE_RC, 23))
    chk.handlers = {HAND_OFF: words}


def unexpected_fault(chk):
    """Any exception on a success-path check is a failure."""
    chk.expect = ("none", None)
    h = P.Seq()
    code = chk.code("no exception expected")
    _fail_exit(chk, h, code)     # restores PTBR/PTW first: a fault may arrive
    return h.resolve()           # with the TLB bypassed or another table live


def fault_handler(chk, cls, sub, info=None, resume=True, post=None):
    """Assert the fault frame, then resume after the faulting instruction.

    Exactly one of the two forms (`ADR-0062 D1/D2`):

      * `cls` = a low sync cause (`CFXMEM` for a non-PTW core access, `CFXREG`,
        `ILLI`), `sub` = `None`  =>  `cause_id == 1 << index`, `[63:32]` == 0;
      * `cls` = `None`, `sub` = a bitmap symbol from `contract-see §6.1.1`
        (`DGPTRAP`, `NWPERM`, `ADWBFAIL`, ...)  =>  `cause_id == 1 << bit`,
        `[15:0]` == 0 (the old parent `CFXMEM`/`CFXPERM` bit is **not** set).
    """
    if (cls is None) == (sub is None):
        raise SystemExit("ptw_carrier_tlb: a fault frame is either a low cause "
                         "or one bitmap bit (cls=%r, sub=%r)" % (cls, sub))
    chk.expect = (cls, sub)
    if sub is None:
        want = CAUSE[cls]
        what = "cause == %s" % cls
    else:
        want = sub_one_hot(sub)
        what = "cause_id == %s alone (bit %d)" % (sub, SUB_BIT[sub])
        if want & RESERVED:
            raise SystemExit("ptw_carrier_tlb: %s is a reserved bit" % sub)
    h = P.Seq()
    h.e(P.add_si(RD_FAULTS, 1))         # entry counter (asserted by the body)
    h.e(P.cfx2rd(monitor_cfx(), 5, CAUSE_ID_RC, RD_CID))
    h.e(P.cfx2rd(monitor_cfx(), 5, CAUSE_INFO_RC, RD_INFO))
    h.e(P.cfx2rd(monitor_cfx(), 5, CAUSE_IP_RC, RD_IP))
    if sub is None:
        a_masked(chk, h, RD_CID, HIGH32, 0,
                 "%s: [63:32] bitmap is 0" % cls)
    else:
        a_masked(chk, h, RD_CID, LOW16, 0,
                 "%s: [15:0] sync cause is 0" % sub)
    a_masked(chk, h, RD_CID, RESERVED, 0,
             "cause_id reserved bits ([31:16]/[39]/[40..47]/[57]/[58..63]) == 0")
    a_eq(chk, h, RD_CID, want, what)
    if info is not None:
        a_eq(chk, h, RD_INFO, info, "cause_info == 0x%x" % info)
    if post:
        h.e(*post)
    if resume:
        h.e(P.escape(monitor_cfx(), 1))  # [cause_ip, +4]
    else:
        _fail_exit(chk, h, 0)           # verdict reached: restore, then pass
    return h.resolve()


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

CASES = []       # [(case_no, case_id, name, desc, builder)]


def case(no, case_id, name, desc):
    def deco(fn):
        CASES.append((no, case_id, name, desc, fn))
        return fn
    return deco


def _new(no, case_id, label, desc):
    return Check(no, case_id, label, desc)


def _finish(chk):
    """Epilogue: hand the address space back, dump the signature, then pass."""
    if chk.sig_want:
        _restore_identity(chk.s)
        SIG.dump(chk.s, SIG_BUF, len(chk.sig_want))
        chk.s.e(*P.exit_seq(0))
        chk.s.e(P.jump_rel(0))
        return chk
    _fail_exit(chk, chk.s, 0)
    return chk


def sig_begin(chk):
    """预填签名区（`SIG_BEGIN`）；每镜像调用一次，放在第一次改页表之前。"""
    SIG.begin(chk.s, SIG_BUF, SIG_PREFILL)


def sig_obs(chk, rd, want):
    """追加一个签名观测点（`SIGUPD rd`）并登记期望值（host 侧 `signature.compare`）。"""
    SIG.upd(chk.s, rd)
    chk.sig_want.append(want)


# -- 001: fill then hit -----------------------------------------------------
@case(1, "arch-ptw-001", "tlb_fill_hit", "fill on the first access, hit on the second")
def _c001(no, cid):
    c = _new(no, cid, "fill_hit", "same page twice: miss+fill, then hit")
    record_baseline(c)
    st64(c, DA, M1)
    install_table(c, {0: pte_leaf(DA)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "1st access (walk+fill) reads the marker")
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M1, "2nd access (hit) reads the same marker")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    return [_finish(c)]


# -- 002: a hit does not re-read the PTE ------------------------------------
@case(2, "arch-ptw-002", "tlb_hit_no_pte_reread",
      "editing the PTE without an invalidate is not observed (TLB-07)")
def _c002(no, cid):
    c = _new(no, cid, "hit_no_reread", "PTE PPN edited between two accesses")
    sig_begin(c)
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    install_table(c, {0: pte_leaf(DA)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "1st access fills from the PTE (PA_A)")
    sig_obs(c, 5, M1)                       # 填充：1st 访问读到 PA_A
    st64(c, L2A + 0, pte_leaf(DB))          # a walk would now yield PA_B
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M1, "2nd access still reads PA_A: the hit did not re-read the PTE")
    sig_obs(c, 6, M1)                       # 命中：PTE 已改，2nd 仍读 PA_A
    ld64(c, L2A + 0, rd=7)
    sig_obs(c, 7, pte_leaf(DB))             # 页表确已改成 PA_B（命中不是靠表没改）
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    return [_finish(c)]


# -- 003: invalid + VA ------------------------------------------------------
@case(3, "arch-ptw-003", "tlb_invalid_va",
      "invalid+VA drops the page containing start only (TLB-23)")
def _c003(no, cid):
    c = _new(no, cid, "invalid_va", "two cached pages, invalidate the first by VA")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    st64(c, DD, M4)
    install_table(c, {0: pte_leaf(DA), 1: pte_leaf(DB)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page X filled (PA_A)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "page Y filled (PA_B)")
    st64(c, L2A + 0, pte_leaf(DC))          # walk for X would now give PA_C
    st64(c, L2A + 8, pte_leaf(DD))          # walk for Y would now give PA_D
    tlb_cmd(c, OP_INVALID, SCOPE_VA, asid_any=True, start=VA0 + 0x40)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M3, "page X re-walked (entry deleted, new PTE visible)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "page Y still hits its entry (out of the VA scope)")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    return [_finish(c)]


# -- 004: invalid + range, illegal operands, scope=all ---------------------
@case(4, "arch-ptw-004", "tlb_invalid_range",
      "invalid+range intersects one page; illegal operands are CFXREG")
def _c004(no, cid):
    out = []

    # (a) range overlapping X only
    c = _new(no, cid, "range_hit", "range [0x8000,0x10000) overlaps page X only")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    st64(c, DD, M4)
    install_table(c, {0: pte_leaf(DA), 1: pte_leaf(DB)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page X filled (PA_A)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "page Y filled (PA_B)")
    st64(c, L2A + 0, pte_leaf(DC))
    st64(c, L2A + 8, pte_leaf(DD))
    tlb_cmd(c, OP_INVALID, SCOPE_RANGE, asid_any=True,
            start=0x8000, size=0x8000)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M3, "page X intersected by the range -> re-walked")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "page Y outside the range -> still a hit")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    out.append(_finish(c))

    # (b) range with size = 0 => CFXREG, and no entry is dropped
    c = _new(no, cid, "range_size0_cfxreg", "range && size == 0 => CFXREG (TLB-24)")
    st64(c, DA, M1)
    st64(c, DC, M3)
    install_table(c, {0: pte_leaf(DA)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page X filled (PA_A)")
    st64(c, L2A + 0, pte_leaf(DC))
    tlb_reg(c, TLB_START_RC, VA0)
    tlb_reg(c, TLB_SIZE_RC, 0)
    set_handler(c, fault_handler(
        c, "CFXREG", None,
        info=P.cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, CREG)))
    arm_fault(c)
    tlb_reg(c, TLB_CONTROL_RC, (OP_INVALID & 3) | ((SCOPE_RANGE & 3) << 2))
    a_fault_count(c, 1)
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M1, "the rejected command dropped nothing (still a hit)")
    out.append(_finish(c))

    # (c) scope = 11 (reserved) => CFXREG
    c = _new(no, cid, "scope_reserved_cfxreg", "scope == 11 => CFXREG (TLB-24)")
    st64(c, DA, M1)
    st64(c, DC, M3)
    install_table(c, {0: pte_leaf(DA)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page X filled (PA_A)")
    st64(c, L2A + 0, pte_leaf(DC))
    set_handler(c, fault_handler(
        c, "CFXREG", None,
        info=P.cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, CREG)))
    arm_fault(c)
    tlb_reg(c, TLB_CONTROL_RC, (OP_INVALID & 3) | ((SCOPE_RESERVED & 3) << 2))
    a_fault_count(c, 1)
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M1, "the rejected command dropped nothing (still a hit)")
    out.append(_finish(c))

    # (d) scope = all ignores start/size
    c = _new(no, cid, "scope_all", "scope=all invalidates both pages ignoring start/size")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    st64(c, DD, M4)
    install_table(c, {0: pte_leaf(DA), 1: pte_leaf(DB)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page X filled (PA_A)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "page Y filled (PA_B)")
    st64(c, L2A + 0, pte_leaf(DC))
    st64(c, L2A + 8, pte_leaf(DD))
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True,
            start=0x3FFF_FFFF_F000, size=0x1000)   # junk window, ignored
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M3, "page X re-walked (all)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M4, "page Y re-walked too (start/size ignored)")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    out.append(_finish(c))
    return out


# -- 005: ASID_ANY and G ---------------------------------------------------
@case(5, "arch-ptw-005", "tlb_asid_g",
      "ASID_ANY=0 leaves G entries, ASID_ANY=1 takes them, G is cross-ASID")
def _c005(no, cid):
    out = []

    # (a) ASID_ANY = 0: the G entry survives, the G=0 entry goes
    c = _new(no, cid, "asid_any0_keeps_g", "ASID_ANY=0 with current ASID 0")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    st64(c, DD, M4)
    install_table(c, {0: pte_leaf(DA), 1: pte_leaf(DB, g=True)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "G=0 entry filled (PA_A)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "G=1 entry filled (PA_B)")
    st64(c, L2A + 0, pte_leaf(DC))
    st64(c, L2A + 8, pte_leaf(DD, g=True))
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=False)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M3, "G=0 / matching ASID entry deleted -> re-walk")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "G=1 entry not touched by ASID_ANY=0")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    out.append(_finish(c))

    # (b) ASID_ANY = 1: both go
    c = _new(no, cid, "asid_any1_takes_g", "ASID_ANY=1 includes G entries")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    st64(c, DD, M4)
    install_table(c, {0: pte_leaf(DA), 1: pte_leaf(DB, g=True)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "G=0 entry filled (PA_A)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "G=1 entry filled (PA_B)")
    st64(c, L2A + 0, pte_leaf(DC))
    st64(c, L2A + 8, pte_leaf(DD, g=True))
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M3, "G=0 entry deleted -> re-walk")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M4, "G=1 entry deleted too -> re-walk")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    out.append(_finish(c))

    # (c) G is reused across ASIDs, G=0 is not
    c = _new(no, cid, "g_cross_asid", "ASID 1: G=0 misses, G=1 hits (TLB-05)")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    st64(c, DD, M4)
    install_table(c, {0: pte_leaf(DA), 1: pte_leaf(DB, g=True)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "G=0 entry filled at ASID 0 (PA_A)")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "G=1 entry filled at ASID 0 (PA_B)")
    st64(c, L2A + 0, pte_leaf(DC))
    st64(c, L2A + 8, pte_leaf(DD, g=True))
    set_asid(c, 1)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M3, "ASID 1: the G=0 entry does not match -> re-walk")
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M2, "ASID 1: the G=1 entry matches -> still PA_B")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    out.append(_finish(c))
    return out


# -- 006: clean writes A/D back and keeps; invalid does neither ------------
@case(6, "arch-ptw-006", "tlb_clean_ad",
      "clean: A/D OR'd back + entry kept; invalid: no write-back + deleted")
def _c006(no, cid):
    c = _new(no, cid, "clean_vs_invalid", "page X cleaned, page Y invalidated")
    sig_begin(c)
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, DC, M3)
    install_table(c, {0: pte_leaf(DA, a=False, d=False),
                      1: pte_leaf(DB, a=False, d=False)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page X read (A pending)")
    st_va(c, VA0, M4)
    ld64(c, L2A + 0, rd=6)
    a_eq(c, c.s, 6, pte_leaf(DA, a=False, d=False),
         "access alone never writes the PTE back (A/D still 0)")
    sig_obs(c, 6, pte_leaf(DA, a=False, d=False))   # clean 前的 PTE（A/D=0）
    tlb_cmd(c, OP_CLEAN, SCOPE_VA, asid_any=True, start=VA0)
    ld64(c, L2A + 0, rd=6)
    a_eq(c, c.s, 6, pte_leaf(DA, a=True, d=True),
         "clean OR'd A=1/D=1 into the PTE (other fields kept)")
    sig_obs(c, 6, pte_leaf(DA, a=True, d=True))     # clean 回写后的 PTE（A/D=1）
    st64(c, L2A + 0, pte_leaf(DC))
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M4, "clean kept the entry (still the old PA_A copy)")
    st_va(c, VA1, M4)
    tlb_cmd(c, OP_INVALID, SCOPE_VA, asid_any=True, start=VA1)
    ld64(c, L2A + 8, rd=6)
    a_eq(c, c.s, 6, pte_leaf(DB, a=False, d=False),
         "invalid does not write A/D back")
    sig_obs(c, 6, pte_leaf(DB, a=False, d=False))   # invalid 不回写（A/D 仍 0）
    st64(c, L2A + 8, pte_leaf(DC))
    ld_va(c, VA1, rd=6)
    a_eq(c, c.s, 6, M3, "invalid deleted the entry -> re-walk to PA_C")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    return [_finish(c)]


# -- 007: flush writes back + deletes; a failed write-back keeps it --------
@case(7, "arch-ptw-007", "tlb_flush_adwb_fail",
      "flush: A/D back + delete; ROM-resident PTE: CFXMEM[56] and the entry stays")
def _c007(no, cid):
    out = []

    # (a) normal flush
    c = _new(no, cid, "flush_ok", "flush writes A/D back and deletes the entry")
    sig_begin(c)
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    install_table(c, {0: pte_leaf(DA, a=False, d=False)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page read (A pending)")
    st_va(c, VA0, M3)
    tlb_cmd(c, OP_FLUSH, SCOPE_VA, asid_any=True, start=VA0)
    ld64(c, L2A + 0, rd=6)
    a_eq(c, c.s, 6, pte_leaf(DA, a=True, d=True),
         "flush OR'd A=1/D=1 into the PTE")
    sig_obs(c, 6, pte_leaf(DA, a=True, d=True))     # flush 回写后的 PTE
    st64(c, L2A + 0, pte_leaf(DB))
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M2, "flush deleted the entry -> re-walk to PA_B")
    sig_obs(c, 5, M2)                               # 删除后重走页表读到 PA_B
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    out.append(_finish(c))

    # (b) write-back failure: the leaf PTE lives in the read-only BootROM
    c = _new(no, cid, "flush_adwbfail", "ROM page table: CFXMEM + [56] ADWBFAIL")
    sig_begin(c)
    c.rom_at = {_ROM_PTE_IMAGE_OFF: list(_ROM_PTE_WORDS)}
    set_handler(c, fault_handler(c, None, "ADWBFAIL", info=_ROM_PTE_PA))
    # PA 0x40 要经 512 MiB 恒等超页写；user 模式下该超页必须也允许 U
    # （HSJU=H|S|U，`DADAO-12 §2.2.5`），否则写侧先吃 `[32] NUPERM`。
    st64(c, PT_L1 + 0 * 8, pte_super(0))
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    st64(c, 0x40, M1)                          # PA 0x40 (identity table)
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    set_ptbr(c, P.RESET_PC)                    # the ROM-resident page table
    ld_va(c, _ROM_VA, rd=5)
    a_eq(c, c.s, 5, M1, "the ROM leaf PTE is readable (fill worked)")
    arm_fault(c)
    tlb_cmd(c, OP_FLUSH, SCOPE_ALL, asid_any=True)   # write-back must fail
    tlb_cmd(c, OP_FLUSH, SCOPE_ALL, asid_any=True)   # still present & dirty
    a_fault_count(c, 2)
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)  # needs no write-back
    ld_va(c, _ROM_VA, rd=6)
    a_eq(c, c.s, 6, M1, "after the failed flush the page is still reachable")
    set_ptw(c, True)
    set_ptbr(c, P.PT_PA)
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    sig_obs(c, RD_INFO, _ROM_PTE_PA)        # cause_info = ROM 里的叶 PTE 物理地址
    sig_obs(c, RD_FAULTS, 2)                # 两次 flush 都失败（条目未删）
    out.append(_finish(c))
    return out


_ROM_L1_IDX = 0x1FFF
_ROM_VA = (_ROM_L1_IDX << 29) | 0x40
_ROM_PTE_PA = P.RESET_PC + _ROM_L1_IDX * 8
_ROM_PTE_IMAGE_OFF = P.RESET_PC - P.BOOTROM_BASE + _ROM_L1_IDX * 8
_ROM_PTE = pte_super(0)
_ROM_PTE_WORDS = [(_ROM_PTE >> 32) & 0xFFFFFFFF, _ROM_PTE & 0xFFFFFFFF]


# -- 008: PTBR / ASID / ptw_enable writes do not invalidate ----------------
@case(8, "arch-ptw-008", "tlb_no_implicit_invalidate",
      "writing PTBR (same/other), ASID, ptw_enable=1 keeps the entry (TLB-29)")
def _c008(no, cid):
    c = _new(no, cid, "no_implicit_invalidate", "four register writes, then an explicit invalid")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    st64(c, L2A + 0, pte_leaf(DA))
    st64(c, PT_L1 + 0 * 8, pte_table(L2A))
    install_second_table(c, {0: pte_leaf(DB)})
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "entry filled from PT_L1 (PA_A)")
    set_ptbr(c, PT_L1)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "PTBR := same value keeps the entry")
    set_ptbr(c, L1B)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "PTBR := another table keeps the entry (no walk happened)")
    set_asid(c, 0)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "ASID := same value keeps the entry")
    set_ptw(c, True)
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "ptw_enable := 1 keeps the entry")
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M2, "the explicit invalidate is what makes PTBR take effect")
    set_ptbr(c, PT_L1)
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    return [_finish(c)]


# -- 009: ptw_enable = 0 => CFXMEM (no bitmap bit), TLB bypassed -----------
@case(9, "arch-ptw-009", "ptw_off_direct_cfxmem",
      "ptw_enable=0: CFXMEM alone (no bitmap bit), no TLB lookup, no fill")
def _c009(no, cid):
    out = []

    # (a) an existing entry is not consulted with PTW off
    c = _new(no, cid, "ptw_off_bypasses_tlb", "a cached page still faults with PTW off")
    st64(c, DA, M1)
    install_table(c, {0: pte_leaf(DA)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "page cached with PTW on")
    set_ptw(c, False)
    set_handler(c, fault_handler(c, "CFXMEM", None, info=VA0,
                                post=load_rd(CREG, 1) + [P.cfx2rc(
                                    PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC,
                                    CREG)]))
    arm_fault(c)
    ld_va(c, VA0, rd=5)
    a_fault_count(c, 1)
    out.append(_finish(c))

    # (b) a never-touched page: no entry, no A/D update, later walk is fresh
    c = _new(no, cid, "ptw_off_no_entry", "bypass leaves PTE A/D at 0 and fills nothing")
    st64(c, DB, M2)
    st64(c, DC, M3)
    install_table(c, {1: pte_leaf(DB, a=False, d=False)})
    set_ptw(c, False)
    set_handler(c, fault_handler(c, "CFXMEM", None, info=VA1,
                                post=load_rd(CREG, 1) + [P.cfx2rc(
                                    PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC,
                                    CREG)]))
    arm_fault(c)
    ld_va(c, VA1, rd=5)
    a_fault_count(c, 1)
    ld64(c, L2A + 8, rd=6)
    a_eq(c, c.s, 6, pte_leaf(DB, a=False, d=False),
         "the bypassed access created no entry and updated no A/D bit")
    st64(c, L2A + 8, pte_leaf(DC))
    ld_va(c, VA1, rd=5)
    a_eq(c, c.s, 5, M3, "with PTW back on the access walks to the new PTE")
    out.append(_finish(c))
    return out


# -- 010: ptw_enable = 1 with an unmapped page -----------------------------
@case(10, "arch-ptw-010", "ptw_on_unmapped",
      "L1/L2 P=0: only [52] DGPTRAP (data) / [48] IGPTRAP (fetch), CFXMEM=0")
def _c010(no, cid):
    out = []

    c = _new(no, cid, "data_unmapped", "read of an unmapped page")
    install_table(c, {})                    # L2 entry 2 stays P=0
    set_handler(c, fault_handler(c, None, "DGPTRAP", info=VA2))
    arm_fault(c)
    ld_va(c, VA2, rd=5)
    a_fault_count(c, 1)
    out.append(_finish(c))

    c = _new(no, cid, "fetch_unmapped", "fetch of an unmapped page")
    install_table(c, {})
    set_handler(c, fault_handler(c, None, "IGPTRAP", info=VA2,
                                resume=False))
    jump_va(c, VA2)
    _fail_exit(c, c.s, c.code("the fetch must fault"))
    out.append(c)
    return out


# -- 011: page permission failures => permission bitmap bits -------------
@case(11, "arch-ptw-011", "perm_denied_cfxperm",
      "HSJU / R / W / X: each missing bit gives its own bitmap sub-cause")
def _c011(no, cid):
    """Permission vectors, one check per mode-specific page-access rule.

    `DADAO-12 §2.2.5/§2.2.6`: only the **current run mode's** HSJU bit is
    required (no implicit H-covers-S / S-covers-U widening), and R/W/X are
    orthogonal; when both are violated the HSJU bit wins.  The H axis
    (`NHPERM`) is what hypv needs; supv adds the S axis (`NSPERM`) and user the
    U axis (`NUPERM`), each combined with R/W/X.  Jail is out of scope (user
    ruling 2026-11-22).
    """
    out = []

    def deny(label, desc, sub, pte, access):
        """One denied access: handler asserts the sub-cause, body counts it."""
        c = _new(no, cid, label, desc)
        st64(c, DA, M1)
        install_table(c, {0: pte})
        if access == "fetch":
            set_handler(c, fault_handler(c, None, sub, info=VA0, resume=False))
            jump_va(c, VA0)
            _fail_exit(c, c.s, c.code("the fetch must fault"))
            out.append(c)
            return
        set_handler(c, fault_handler(c, None, sub, info=VA0))
        arm_fault(c)
        if access == "store":
            st_va(c, VA0, M2)
        else:
            ld_va(c, VA0, rd=5)
        a_fault_count(c, 1)
        out.append(_finish(c))

    def allow(label, desc, pte):
        """One allowed access: proves the mask is not over-restrictive."""
        c = _new(no, cid, label, desc)
        st64(c, DA, M1)
        install_table(c, {0: pte})
        set_handler(c, unexpected_fault(c))
        ld_va(c, VA0, rd=5)
        a_eq(c, c.s, 5, M1, desc)
        assert_no_new_fault(c)
        out.append(_finish(c))

    if MODE == "hmon":
        # hypv: H is the required bit (`[35] NHPERM`); HSJU wins over R/W/X.
        deny("nwperm", "store to a W=0 page", "NWPERM",
             pte_leaf(DA, w=False), "store")
        deny("nrperm", "load from an R=0 page", "NRPERM",
             pte_leaf(DA, r=False), "load")
        deny("nxperm", "fetch from an X=0 page", "NXPERM",
             pte_leaf(DA, x=False), "fetch")
        deny("nhperm", "load from a page whose HSJU has no H bit", "NHPERM",
             pte_leaf(DA, hsju=0x0), "load")
        deny("nhperm_before_nwperm",
             "W=0 page without H: HSJU is checked before R/W/X", "NHPERM",
             pte_leaf(DA, hsju=0x0, w=False), "store")
    elif MODE == "smon":
        # supv: S is the required bit (`[34] NSPERM`).  H is not required
        # outside hypv; S and U may both be set (the hardware adds no
        # "S excludes U" rule).
        deny("nwperm", "store to a W=0 page (S allowed)", "NWPERM",
             pte_leaf(DA, w=False), "store")
        deny("nrperm", "load from an R=0 page (S allowed)", "NRPERM",
             pte_leaf(DA, r=False), "load")
        deny("nxperm", "fetch from an X=0 page (S allowed)", "NXPERM",
             pte_leaf(DA, x=False), "fetch")
        deny("nsperm", "load from a page whose HSJU has S=0 (H|U only)",
             "NSPERM", pte_leaf(DA, hsju=0x9), "load")
        deny("nsperm_before_nwperm",
             "W=0 page without S: HSJU is checked before R/W/X", "NSPERM",
             pte_leaf(DA, hsju=0x9, w=False), "store")
        allow("s_plus_u_allowed",
              "S=1 and U=1: supv reads a page that also grants user",
              pte_leaf(DA, hsju=HSJU_ALL))
        allow("s_only_allowed",
              "S=1 without H: hypv's H bit is not required in supv",
              pte_leaf(DA, hsju=0x4))
    else:                                            # umon
        # user: U is the required bit (`[32] NUPERM`).  H is not required
        # outside hypv; a kernel page (H|S) must not be reachable from user.
        deny("nwperm", "store to a W=0 page (U allowed)", "NWPERM",
             pte_leaf(DA, w=False), "store")
        deny("nrperm", "load from an R=0 page (U allowed)", "NRPERM",
             pte_leaf(DA, r=False), "load")
        deny("nxperm", "fetch from an X=0 page (U allowed)", "NXPERM",
             pte_leaf(DA, x=False), "fetch")
        deny("nuperm", "load from a page whose HSJU has U=0 (H|S only)",
             "NUPERM", pte_leaf(DA, hsju=0xC), "load")
        deny("nuperm_before_nxperm",
             "X=0 page without U: HSJU is checked before R/W/X", "NUPERM",
             pte_leaf(DA, hsju=0xC, x=False), "fetch")
        allow("u_plus_s_allowed",
              "U=1 and S=1: user reads a page that also grants supv",
              pte_leaf(DA, hsju=HSJU_ALL))
        allow("u_only_allowed",
              "U=1 without H/S: only the current mode's bit is required",
              pte_leaf(DA, hsju=0x1))
    return out


# -- 012: a PTE change needs an explicit invalidate ------------------------
@case(12, "arch-ptw-012", "pte_change_needs_invalidate",
      "edited PTE is invisible until invalid+VA (TLB-07/TLB-18)")
def _c012(no, cid):
    c = _new(no, cid, "edit_then_invalidate", "old mapping, then the new one")
    record_baseline(c)
    st64(c, DA, M1)
    st64(c, DB, M2)
    install_table(c, {0: pte_leaf(DA)})
    ld_va(c, VA0, rd=5)
    a_eq(c, c.s, 5, M1, "the remap is set up (PA_A)")
    st64(c, L2A + 0, pte_leaf(DB))
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M1, "without an invalidate the old mapping still wins")
    tlb_cmd(c, OP_INVALID, SCOPE_VA, asid_any=True, start=VA0)
    ld_va(c, VA0, rd=6)
    a_eq(c, c.s, 6, M2, "after invalid+VA the new mapping takes effect")
    assert_no_new_fault(c)
    set_handler(c, unexpected_fault(c))
    return [_finish(c)]


# -- 013: VA[47:42] != 0 bypasses PTW/TLB ----------------------------------
@case(13, "arch-ptw-013", "cfx_space_bypasses_ptw",
      "cfx-internal space: cfx_pmem SRAM works with an all-zero table; reserved cfx => CFXMEM")
def _c013(no, cid):
    out = []

    # (a) positive: cfx_pmem SRAM with PTW on and an all-zero page table
    c = _new(no, cid, "pmem_bypass", "ld/st to cfx_pmem SRAM, L1 all zero")
    sig_begin(c)
    record_baseline(c)
    st64(c, DA, M1)
    set_handler(c, unexpected_fault(c))
    for idx in range(4):
        st64(c, L1B + idx * 8, 0)
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    set_ptbr(c, L1B)                        # deliberately empty
    ld64(c, PMEM_SRAM, rd=5)
    a_eq(c, c.s, 5, 0, "cfx_pmem SRAM read with an all-zero page table")
    st64(c, PMEM_SRAM, M1)
    ld64(c, PMEM_SRAM, rd=6)
    a_eq(c, c.s, 6, M1, "cfx_pmem SRAM write/read-back with an all-zero page table")
    assert_no_new_fault(c)
    set_ptbr(c, PT_L1)                     # 签名区/退出块要靠恒等表
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    sig_obs(c, 6, M1)                       # 旁路窗口写入后回读（与 RTL 同一值）
    out.append(_finish(c))

    # (b) negative with PTW on: reserved cfx => CFXMEM (no bitmap bit).
    # The handler resumes (`+4`), so the frame can be read back and recorded in
    # the signature stream (three-way: the RTL carrier records the same two
    # values from its `cfx_hmon cg5` frame through the fixed ROM slots).
    c = _new(no, cid, "reserved_cfx_ptw_on", "ld from a reserved cfx (PTW on)")
    sig_begin(c)
    record_baseline(c)
    st64(c, DA, M1)
    set_handler(c, fault_handler(c, "CFXMEM", None, info=RESERVED_CFX))
    arm_fault(c)
    ld_va(c, RESERVED_CFX, rd=5)
    a_fault_count(c, 1)
    read_cause(c, rd=5)
    sig_obs(c, 5, CAUSE["CFXMEM"])           # 低位 cause：CFXMEM
    c.s.e(P.cfx2rd(monitor_cfx(), 5, CAUSE_INFO_RC, rd=6))
    sig_obs(c, 6, RESERVED_CFX)              # cause_info = 访问地址
    out.append(_finish(c))

    # (c) negative with PTW off: identical semantics
    c = _new(no, cid, "reserved_cfx_ptw_off", "ld from a reserved cfx (PTW off)")
    set_ptw(c, False)
    set_handler(c, fault_handler(c, "CFXMEM", None, info=RESERVED_CFX,
                                resume=False))
    arm_fault(c)
    ld_va(c, RESERVED_CFX, rd=5)
    _fail_exit(c, c.s, c.code("the reserved-cfx access must fault"))
    out.append(c)
    return out


# -- 014: an A/D write-back failure is entry-granular, then stops the command
L2C = 0x7FF4_0000                # L1[2] -> L2 for page Z (RAM, 64 KiB aligned)
ROM_L2_IMAGE_OFF = 0x100000      # 64 KiB-aligned page inside the read-only ROM
ROM_L2 = P.BOOTROM_BASE + ROM_L2_IMAGE_OFF
DX, DY, DZ = 0x6400_0000, 0x6500_0000, 0x6600_0000
VX, VY, VZ = 0x0, 1 << 29, 2 << 29


def _three_entries(chk):
    """Cache X, Y, Z with pending A/D; Y's leaf PTE sits in the read-only ROM.

    Entry order = fill order = the order `cfx_ptw_tlb_control` walks them, so
    the first failure is entry 2 (`TLB-37`: entry-granular, stop at the first
    failure).  The L1 table pointer only keeps `PPN[55:16]`, hence a 64 KiB
    aligned ROM page for the leaf.
    """
    st64(chk, DX, M1)
    st64(chk, DY, M2)
    st64(chk, DZ, M3)
    st64(chk, L2A + 0, pte_leaf(DX, a=False, d=False))
    st64(chk, L2C + 0, pte_leaf(DZ, a=False, d=False))
    st64(chk, PT_L1 + 0 * 8, pte_table(L2A))
    st64(chk, PT_L1 + 1 * 8, pte_table(ROM_L2))
    st64(chk, PT_L1 + 2 * 8, pte_table(L2C))
    y = pte_leaf(DY, a=False, d=False)
    chk.image_at = {ROM_L2_IMAGE_OFF: [(y >> 32) & 0xFFFFFFFF,
                                       y & 0xFFFFFFFF]}
    tlb_cmd(chk, OP_INVALID, SCOPE_ALL, asid_any=True)
    ld_va(chk, VX, rd=5)
    st_va(chk, VX, M4)                       # X: A + D pending
    ld_va(chk, VY, rd=6)                     # Y: A pending (leaf is read-only)
    ld_va(chk, VZ, rd=7)
    st_va(chk, VZ, M4)                       # Z: A + D pending


@case(14, "arch-ptw-014", "tlb_control_stop",
      "flush: entries before the failure are processed, the failing one is "
      "kept, the rest are untouched (TLB-37)")
def _c014(no, cid):
    """Entry-granular stop-on-error with three cached, dirty entries.

    "Processed" for `flush` = A/D OR'd back into the PTE (the delete half is
    case 007's normal path); "not processed" = the PTE still has A/D = 0, which
    cannot be confused with a deletion (`TLB-37`).

    `TLB-37` fixes *what* stops (the first failing entry and everything after
    it) but not the walk order; the probe therefore builds the command in
    insertion order (X, Y, Z) and names the failure "entry 2".
    """
    out = []

    # (a) entry 1 was written back, entry 3 was not even looked at.
    c = _new(no, cid, "flush_stop_after",
             "three entries: 1 processed, 2 fails, 3 left untouched")
    record_baseline(c)
    _three_entries(c)
    set_handler(c, fault_handler(c, None, "ADWBFAIL", info=ROM_L2))
    arm_fault(c)
    tlb_cmd(c, OP_FLUSH, SCOPE_ALL, asid_any=True)
    a_fault_count(c, 1)
    ld64(c, L2A + 0, rd=6)
    a_eq(c, c.s, 6, pte_leaf(DX, a=True, d=True),
         "entry 1 (before the failure) was processed: A/D written back")
    ld64(c, L2C + 0, rd=7)
    a_eq(c, c.s, 7, pte_leaf(DZ, a=False, d=False),
         "entry 3 (after the failure) was not processed: its PTE is untouched")
    out.append(_finish(c))

    # (b) the failing entry keeps its translation and its PTE.
    c = _new(no, cid, "flush_stop_kept",
             "three entries: the failed one keeps its translation")
    record_baseline(c)
    _three_entries(c)
    set_handler(c, fault_handler(c, None, "ADWBFAIL", info=ROM_L2))
    arm_fault(c)
    tlb_cmd(c, OP_FLUSH, SCOPE_ALL, asid_any=True)
    a_fault_count(c, 1)
    ld_va(c, VY, rd=6)
    a_eq(c, c.s, 6, M2, "the failed entry kept its state (still a usable hit)")
    ld64(c, ROM_L2, rd=8)
    a_eq(c, c.s, 8, pte_leaf(DY, a=False, d=False),
         "the failed write-back left entry 2's PTE unchanged")
    ld64(c, L2C + 0, rd=7)
    a_eq(c, c.s, 7, pte_leaf(DZ, a=False, d=False),
         "entry 3 (after the failure) was not processed at all")
    out.append(_finish(c))
    return out


# -- 015: ILLI at an IP inside the memory window ---------------------------
VA_P = 5 << 29                   # L1[5]: VA[47:42] == 0, PTW-mapped
L2P = 0x7FF5_0000                # L2 for L1[5] (64 KiB aligned, in RAM)
STUB_PA = 0x7000_0000            # 64 KiB RAM page holding the stub
ROM_STORE = P.ROM_BASE + 0xC000  # read-only ROM byte => ILLI on the store
STUB_INSN = P.st_o(4, 3, 0)      # the faulting instruction itself


def _open_power_mem_mask():
    """`cfx_power` (cfx63) hypv `cfxmem`: clear bit 3 so hmon may store there."""
    words = [P.cfx2rd(63, 3, 1, 20)]
    words += P.load_rd(21, 0xFFF7)
    words += [P.and_o(20, 20, 21)]
    words += [P.cfx2rc(63, 3, 1, 20)]
    return words


@case(15, "arch-ptw-015", "illi_insn_word_window",
      "ILLI at a memory-window IP: cause_info = the instruction word read "
      "back through the guest TLB page base")
def _c015(no, cid):
    c = _new(no, cid, "illi_insn_word_window",
             "ILLI at a memory-window IP: cause_info = the instruction word")
    # Map VA_P -> STUB_PA: L1[5] -> an L2 table, L2[0] -> the 64 KiB leaf.
    st64(c, L2P + 0, pte_leaf(STUB_PA))
    st64(c, PT_L1 + 5 * 8, pte_table(L2P))
    # A store that does *not* fault falls through to this exit code, which is
    # why the "must fault" claim has a reachable FAIL path of its own.
    fall = c.code("the store into the ROM must fault")
    stub = load_rb(3, ROM_STORE) + [STUB_INSN] + P.exit_seq(fall)
    if len(stub) % 2:
        stub += [P.swym()]
    for i in range(0, len(stub), 2):
        st64(c, STUB_PA + 4 * i, (stub[i] << 32) | stub[i + 1])
    tlb_cmd(c, OP_INVALID, SCOPE_ALL, asid_any=True)
    set_handler(c, fault_handler(c, "ILLI", None, info=STUB_INSN,
                                resume=False))
    arm_fault(c)
    jump_va(c, VA_P)
    _fail_exit(c, c.s, fall)
    c.hmon_extra = _open_power_mem_mask()
    return [c]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_all():
    return [(no, cid, name, desc, fn(no, cid))
            for no, cid, name, desc, fn in CASES]


def decode_fail(check, rc):
    """Turn a guest FAIL code back into the assertion it names."""
    if 0xC0 <= rc <= 0xFF:
        # Kaiwu machine-fault exit (spec/Kaiwu §7.1): the cause never entered a
        # monitor, so no `cg5` frame exists to assert.  Report the encoding.
        return ("machine-fault exit 0x%02x (monitor segment: run mode %d, "
                "cause index %d) — the exception did not enter a monitor, so "
                "no cfx_hmon frame exists"
                % (rc, (rc >> 4) & 0x3, rc & 0xF))
    if 0x80 <= rc <= 0xBF:
        return ("cfx-segment exit 0x%02x (cfx %d) — not a monitor frame"
                % (rc, rc & 0x3F))
    if 1 <= rc <= len(check.fields):
        return "assertion %d: %s" % (rc, check.fields[rc - 1])
    return ("fail code %d does not map to this check (it has %d assertions)"
            % (rc, len(check.fields)))


def run_check(check, qemu, tools=None):
    """Build the mode's image (prelude + env + body), run it, judge the check."""
    image = build_image(check, tools or toolchain(), WORKDIR)
    rc, _log, blob = P.run(image, WORKDIR, qemu=qemu, timeout=TIMEOUT,
                           dump=False, console_out=SIG_OUT)
    if rc is None:
        return False, "TIMEOUT", b""
    if rc != 0:
        return False, decode_fail(check, rc), b""
    if not check.sig_want:
        return True, "ok", b""
    # 判据载体 = 签名流（README「观测通道」）：解析/比对统一走 signature.py
    try:
        got = signature.parse(blob, len(check.sig_want))
    except signature.SignatureError as exc:
        return False, "签名流: %s" % exc, b""
    problems = signature.compare(got, check.sig_want)
    if problems:
        return False, "签名流: " + "; ".join(problems), b""
    return True, "ok", blob


def selected(only):
    """Yield the checks selected by `--only` (case id, case name or id/label)."""
    cases = build_all()
    if only is None:
        for no, cid, name, _desc, checks in cases:
            for chk in checks:
                yield no, cid, name, chk
        return
    if "/" in only:
        want_case, want_label = only.split("/", 1)
    else:
        want_case, want_label = only, None
    for no, cid, name, _desc, checks in cases:
        if want_case not in (cid, name):
            continue
        for chk in checks:
            if want_label is None or chk.label == want_label:
                yield no, cid, name, chk


def selfcheck():
    """Cross-source contract tables + expected.yaml ↔ driver consistency."""
    global MODE
    problems = []
    names = ["NUPERM", "NJPERM", "NSPERM", "NHPERM", "NRPERM", "NWPERM",
             "NXPERM", "IGPTRAP", "ISPTRAP", "IGPFTRAP",
             "ISPFTRAP", "DGPTRAP", "DSPTRAP", "DGPFTRAP", "DSPFTRAP",
             "ADWBFAIL"]
    missing = [n for n in names if n not in SUB_BIT]
    if missing:
        problems.append("contract-see §6.1.1 is missing %r" % (missing,))
    # ADR-0062 D1/D3: permission bits live in [38:32], miss/memory bits in
    # [56:48]; the two "negative" bits [39]/[57] are deleted (must be absent).
    for n in names:
        if n not in SUB_BIT:
            continue
        bit = SUB_BIT[n]
        lo, hi = (32, 38) if n.endswith("PERM") else (48, 56)
        if not lo <= bit <= hi:
            problems.append("%s is bit %d, expected [%d..%d] (ADR-0062 D1)"
                            % (n, bit, lo, hi))
    for dead in ("NCFXPERM", "NONPTW"):
        if dead in SUB_BIT:
            problems.append("contract-see §6.1.1 still lists %s (ADR-0062 D3 "
                            "deletes the bit)" % dead)
    for cls in ("CFXMEM", "CFXPERM"):
        if cls not in CAUSE:
            problems.append("contract-see §6.1 has no %s" % cls)

    # env 段必须齐（三段共用一份布局；缺一份则该模式根本构建不出来）。
    for mode in MODES:
        for path in (os.path.join(ENV_DIRS[mode], "env.S"), ENV_LDS,
                     os.path.join(ENV_INC, "cfx_perm.inc")):
            if not os.path.isfile(path):
                problems.append("缺 env 件（%s）: %s" % (mode, path))

    try:
        import yaml
        with open(EXPECTED_YAML, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except Exception as exc:            # noqa: BLE001 — report, do not mask
        problems.append("cannot read %s: %s" % (EXPECTED_YAML, exc))
        doc = None
    declared = {}
    for entry in (doc or {}).get("cases", []) or []:
        declared[entry.get("id")] = entry

    for mode in MODES:
        MODE = mode
        cases = build_all()
        if len(cases) != 15:
            problems.append("[%s] driver defines %d cases, expected 15"
                            % (mode, len(cases)))
        ids = [cid for _n, cid, _name, _d, _c in cases]
        if len(set(ids)) != len(ids):
            problems.append("[%s] duplicate case ids: %r"
                            % (mode, sorted(ids)))
        for no, cid, name, _desc, checks in cases:
            if no != int(cid.rsplit("-", 1)[1]):
                problems.append("[%s] %s: case number %d does not match the id"
                                % (mode, cid, no))
            labels = [chk.label for chk in checks]
            if len(set(labels)) != len(labels):
                problems.append("[%s] %s: duplicate check labels %r"
                                % (mode, cid, labels))
            for chk in checks:
                if len(chk.fields) == 0:
                    problems.append("[%s] %s/%s has no assertion"
                                    % (mode, cid, chk.label))
                if chk.expect is None:
                    problems.append("[%s] %s/%s declares no expectation"
                                    % (mode, cid, chk.label))
                if len(chk.sig_want) > SIG_PREFILL:
                    problems.append("[%s] %s/%s has %d signature slots > "
                                    "prefill %d" % (mode, cid, chk.label,
                                                    len(chk.sig_want),
                                                    SIG_PREFILL))
        if doc is None:
            continue
        live = {cid: (name, checks) for _n, cid, name, _d, checks in cases}
        for cid in sorted(set(live) - set(declared)):
            problems.append("[%s] expected.yaml misses %s" % (mode, cid))
        for cid in sorted(set(declared) - set(live)):
            problems.append("[%s] expected.yaml declares an unknown case %s"
                            % (mode, cid))
        for cid, (name, checks) in sorted(live.items()):
            entry = declared.get(cid)
            if not entry:
                continue
            if entry.get("only") != name:
                problems.append("[%s] %s: expected.yaml only=%r, driver name=%r"
                                % (mode, cid, entry.get("only"), name))
            # `checks_by_mode.<mode>` 覆盖 `checks`（缺省 = 三种模式同一份）；
            # 运行模式改变的只有**各模式自己的权限位**（011 的 S/U 轴）。
            items = ((entry.get("checks_by_mode") or {}).get(mode)
                     or entry.get("checks") or [])
            def norm(exp):
                return None if exp is None or exp[0] == "none" else exp

            got = {c.label: norm(c.expect) for c in checks}
            want = {}
            for item in items:
                cause = item.get("cause")
                sub = item.get("subcause")
                if cause in (None, "none") and sub is None:
                    want[item.get("label")] = None
                else:
                    # A PTW bitmap fault has `cause: null` + its bitmap symbol:
                    # the old parent `CFXMEM`/`CFXPERM` bit is 0 (ADR-0062 D2).
                    want[item.get("label")] = (
                        None if cause in (None, "none") else cause, sub)
            if got != want:
                problems.append("[%s] %s: checks differ (driver %r vs yaml %r)"
                                % (mode, cid, got, want))
            # 签名流期望：yaml 只是登记（数值真源仍是驱动里的合约派生值），
            # 双向核对 ⇒ 驱动接线与清单不许漂移（m16-testcases-002）。
            sig_decl = {item.get("label"): [int(v)
                                            for v in item.get("signature") or []]
                        for item in items}
            for c in checks:
                want_sig = sig_decl.get(c.label, [])
                if c.sig_want != want_sig:
                    problems.append("[%s] %s/%s: signature differs (driver %r "
                                    "vs yaml %r)" % (mode, cid, c.label,
                                                     c.sig_want, want_sig))
    MODE = "hmon"
    if problems:
        for p in problems:
            print("selfcheck: FAIL %s" % p)
        return 1
    cases = build_all()
    print("selfcheck: PASS (contract-see §6.1.1 == spec/DADAO-12 §3.6; "
          "%d sub-causes, %d causes; %d cases × %d modes)"
          % (len(SUB_BIT), len(CAUSE), len(cases), len(MODES)))
    return 0


def main():
    global QEMU, MODE, CFX_ACCESS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None,
                    help="case id, case name, or <case id>/<check label>")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--mode", default="hmon", choices=list(MODES),
                    help="运行模式（hmon=hypv / smon=supv / umon=user）")
    ap.add_argument("--cfx-access", default=None,
                    help="modes.yaml 的 cfx_access（逗号分隔的 cfxha 十进制；"
                         "环境据此做权限准备）")
    ap.add_argument("--toolchain-bin", default=None,
                    help="llvm-mc/ld.lld/llvm-objcopy 所在目录（缺省 = 安装根）")
    # `run_arch` 的 env 载体参数：本载体的镜像自带 prelude（等价于固件段），
    # 不使用 step5 BootROM，也不测 cache 时序 ⇒ `--bootrom`/`--cache-model`
    # 显式接受后不使用（不静默改变语义）。
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--cache-model", default=None)
    args = ap.parse_args()

    MODE = args.mode
    if args.cfx_access:
        try:
            CFX_ACCESS = [int(x, 0) for x in args.cfx_access.split(",") if x]
        except ValueError:
            print("ptw_carrier_tlb: --cfx-access 需为十进制 cfxha 列表",
                  file=sys.stderr)
            return 2
        if any(not 0 <= c <= 63 for c in CFX_ACCESS) or \
                len(set(CFX_ACCESS)) != len(CFX_ACCESS):
            print("ptw_carrier_tlb: --cfx-access 非法/重复: %r" % (CFX_ACCESS,),
                  file=sys.stderr)
            return 2

    if args.selfcheck:
        return selfcheck()

    cases = build_all()
    if args.list:
        for no, cid, name, desc, checks in cases:
            print("%s  %-28s %s" % (cid, name, desc))
            for chk in checks:
                exp = "none" if chk.expect is None else "/".join(
                    x for x in chk.expect if x)
                print("    %-22s expect=%s  %s" % (chk.label, exp, chk.desc))
        print("%d cases, %d checks" % (len(cases), sum(len(c) for *_x, c in cases)))
        return 0

    QEMU = args.qemu or DEFAULT_QEMU
    if not os.access(QEMU, os.X_OK):
        print("ptw_carrier_tlb: ERROR: qemu not executable: %s" % QEMU)
        return 2
    try:
        tools = toolchain(args.toolchain_bin)
    except SetupError as exc:
        print("ptw_carrier_tlb: SETUP: %s" % exc, file=sys.stderr)
        return 2

    results = selected(args.only)
    npass = nfail = 0
    sig_blobs = []
    try:
        for no, cid, name, chk in results:
            ok, detail, blob = run_check(chk, QEMU, tools)
            print("%s %s/%-22s rc=%s %s"
                  % ("PASS" if ok else "FAIL", cid, chk.label,
                     "0x00" if ok else detail, chk.desc if ok else ""))
            if ok:
                npass += 1
                if blob:
                    sig_blobs.append(blob)
            else:
                nfail += 1
    except SetupError as exc:
        print("ptw_carrier_tlb: SETUP: %s" % exc, file=sys.stderr)
        return 2
    total = npass + nfail
    if total == 0:
        print("ptw_carrier_tlb: no check matched --only %r" % (args.only,))
        return 2
    # `run_arch` 按 expected.yaml 的 checks 顺序拼接比较；每个检查是独立镜像，
    # 这里把同一 case 的全部已接线签名流按检查顺序聚合到同一个产物。
    if sig_blobs:
        with open(SIG_OUT, "wb") as f:
            f.write(b"".join(sig_blobs))
    print("%d/%d checks passed" % (npass, total))
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
