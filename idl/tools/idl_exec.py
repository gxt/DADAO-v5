#!/usr/bin/env python3
"""idl_exec.py — SimRISC 执行器核心（`m17-idl-003`）。

范围（与 `m17-idl-004` 的逐指令 trace 分开）：

  * 四寄存器组状态 `rd`/`rb`/`rf`/`ra`、48 位 CPU 地址、大端存储模型；
  * ELF 加载：机器几何/运行布局取 `tools/testcases/lib/machine_profile.py`
    （不另造第二份机器真源）；BootROM 的 hmon 段按 `spec/Kaiwu §6.2` 装入；
  * 取指/译码/执行最小闭环：算术 / 访存 / 控制流 / 寄存器搬移；
  * 最小 trap/monitor：`trap`/`escape` 按 `contract-see` §4/§5（`DADAO-12 §5.2/§5.3`），
    执行 `tests/inst` 的同步异常例（异常经 cfx3 hmon 的「保存-跳转」固件落回用例落点）。

语义来源与口径：

  * 编码（opc/mask/字段位域）只读 `contracts/opcodes.yaml`（机器可读唯一真源）；
  * 每条 operation 的语义按 `idl/SimRISC-*.idl` 的 operation 正文逐句实现，函数上方
    注明 id 与出处（`spec/SimRISC-NN`）；不按 QEMU 源码反推；
  * 异常原因位索引/进入退出流程取 `spec/DADAO-12 §5.2/§5.3`（`contract-see §4`）；
  * 大端存取、`rb0 = IP`、`rf0` 只写 `[33:32]/[4:0]`、`ra0` 布局取 `spec/SimRISC-00`
    §2.2/§2.3.1/§2.4。

CLI：

    python3 idl/tools/idl_exec.py --self-test
    python3 idl/tools/idl_exec.py --elf <elf> [--bootrom <img>] [--init <json>]
        [--max-steps N] [--image-out <file>] [--json-out <file>]

`--self-test` 覆盖寄存器组初值/写回、48 位地址截断、大端读写、RAS 压弹栈、
异常进入、`escape` 帧选择与 `cfx_hart cg15` 异步捕获、semihosting；`--elf` 运行一个
镜像并输出最终架构状态（四组寄存器、退出码、SYS_WRITEC 字节流）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True       # idl/ 由 check-manifests-guard 做目录断言
from idl_paths import REPO as REPO_ROOT
import idl_fp as _fp                 # FP 独立参考模型（`m17-idl-013` 的 07 册封装）

OPCODES = REPO_ROOT / "contracts" / "opcodes.yaml"

MASK48 = (1 << 48) - 1
MASK64 = (1 << 64) - 1

# spec/DADAO-12 §5.2（二）monitor 异常编号：cause = 1 << n。
CAUSE_BIT = {
    "CfxTrap": 0, "CfxMem": 1, "CfxReg": 2, "CfxEsc": 3, "CfxPerm": 7,
    "Illegal": 8, "Undi": 9, "RasOf": 10, "RasUf": 11, "Malign": 12,
    "IAlign": 13,
}
# spec/DADAO-12 §2.1：reserved cfxha 区间（trap/escape/cfx2* ⇒ ILLI；普通 ld/st ⇒ CFXMEM）。
RESERVED_CFX = set(range(6, 15)) | set(range(16, 32)) | set(range(35, 62))
# Tiny 实现的两个 cfx（spec/Kaiwu §3、contract-see §3）。
IMPLEMENTED_CFX = {3: "hmon", 63: "power"}

# cfx_hart（spec/DADAO-12 §4.7）：异步捕获缓冲 `cg15` 的唯一持有者、所有异步源的唯一
# 异步进入目标（ADR-0064 D4/D5；§5.4）。Tiny profile 不实现该 cfx（`IMPLEMENTED_CFX`），
# 本模型仍按 spec 建模捕获语义（`Machine.async_post`/`async_entry`）；自检白盒注入
# hart 的寄存器面后断言。
CFX_HART = 15
CFX_PMEM = 32
# 异步源身份 = 源 cfxha（ADR-0064 D4；§5.4（一））：TIMER = cfx_hart 自身、PMEM_DMA = cfx_pmem。
ASYNC_SRC_TIMER, ASYNC_SRC_PMEM = 1 << CFX_HART, 1 << CFX_PMEM

# cg5 异常现场（spec/DADAO-12 §3.6）：rc0–rc3 入口记录（HW/RO）、rc4/rc5 原因字段
# （HW）、rc8–rc11 出口意图（HW/RW，进入时复制、软件可改、escape 只认这一份）。
CG5_PREV_MODE, CG5_PREV_CFX, CG5_PREV_IP, CG5_PREV_INTR_MASK, \
    CG5_CAUSE_ID, CG5_CAUSE_INFO = 0, 1, 2, 3, 4, 5
CG5_ESC_RUN_MODE, CG5_ESC_CFX_CODE, CG5_ESC_IP, CG5_ESC_INTR_MASK = \
    8, 9, 10, 11
# cg15（spec/DADAO-12 §4.7；ADR-0064 D5/D6）：`cfx_hart` 的异步入口记录/捕获缓冲
# ——rc0–rc5 入口记录（HW/RO）、rc14/rc15 配置（RW），rc6–rc13 reserved（⇒ CFXREG）；
# rc4 为本次源集合、rc5 为原始 pending 汇总（位 = 源 cfxha），无有效位/无 frame_valid。
# `cfx0`–`cfx3`（monitor）只有 `rc3` = 本运行模式异步来源掩码（位 = 源 cfxha，
# 0 = 允许、1 = 屏蔽、复位全 1，按**当前运行模式**取行求值）。
CG15_PREV_MODE, CG15_PREV_CFX, CG15_PREV_IP, CG15_PREV_INTR_MASK, \
    CG15_SRC_FRAME, CG15_SRC_PENDING = 0, 1, 2, 3, 4, 5
CG15_ASYNC_INTR_MASK = 3
CG15_SWITCH, CG15_VECTOR = 14, 15
# cg16 源侧统一中断面（spec/DADAO-12 §4.7/§4.9；ADR-0064 D1–D3）：rc16 mask /
# rc17 pending / rc18 ack（W1C），位 = 该源子事件（当前均只有 bit0）。`cfx_hart`
# 另有 rc0 timer_ctrl（仅 bit0 ENABLE）与 rc1 timer_cmp。只有 `cfx_hart`/`cfx_pmem`
# 实现 cg16，其它 cfx（含 hmon/power）访问 ⇒ CFXREG。
CG16_TIMER_CTRL, CG16_TIMER_CMP = 0, 1
CG16_MASK, CG16_PENDING, CG16_ACK = 16, 17, 18
CG16_SUBEVENT0 = 1          # 子事件 bit0：timer 到期 / DMA 传输结束（DONE|ERROR）
# cg3（spec/DADAO-12 §3.4）：0..3 四类同步来源 mask、12 cg 级授权位图、14 切模式、
# 15 向量；rc4 不定义（ADR-0061 D5 删除 `<mode>_cfx_intr_mask`，访问 ⇒ CFXREG）。
CG3_TRAP, CG3_MEM, CG3_REG, CG3_EXE, CG3_SWITCH, CG3_VECTOR = \
    0, 1, 2, 3, 14, 15
# cg4（§3.5）：0 id、1 version、2 trap_num、3 excp_sync_num、4 excp_async_num、
# 5 escape_num、6 scratch_regs_num。
CG4_TRAP_NUM, CG4_SYNC_NUM, CG4_ASYNC_NUM, CG4_ESCAPE_NUM = 2, 3, 4, 5
# cg7（§3.8）：每 4 个 rc 一个空间块：desc/start/size/attr。
CG7_DESC, CG7_START, CG7_SIZE, CG7_ATTR = 0, 1, 2, 3

SYNC_MASK_POWER = 0xFFFF_FFFF_FFFF_FFF7
SYNC_MASK_HMON = 0x7FFF_FFFF_FFFF_FFF7

# spec/DADAO-12 §3.6 + ADR-0062 D2/D3（扁平位图）：一条异常只置**一位**，`[63:32]` 全 0。
# 旧的 `[57] NONPTW` / `[39] NCFXPERM` 已删除（位保留、恒 0）：
#   * `CFXMEM`（`1 << 1`）= 非 PTW 的核内访存故障，`cause_info` = 被访问的核内地址（D4）；
#   * `CFXPERM`（`1 << 7`）= cfx 来源掩码拒绝，`cause_info` = 触发指令地址（D4）。

MODE_USER, MODE_JAIL, MODE_SUPV, MODE_HYPV = 0, 1, 2, 3
MODE_MONITOR = {MODE_USER: 0, MODE_JAIL: 1, MODE_SUPV: 2, MODE_HYPV: 3}

# spec/SimRISC-00 §2.3.1：rf0 的只读 Quiet NaN 字段（[63:51] 双精 qNaN 位、
# [31:22] 单精 qNaN 位）；复位值由规范位域直接给出，舍入模式/异常状态为 0。
RF0_QNAN_FO = 0b0111111111111 << 51
RF0_QNAN_FT = 0b0111111111 << 22
RF0_RESET = RF0_QNAN_FO | RF0_QNAN_FT

# contract-semihosting §1/§3。
SEMIHOST_TAG = 0x3FF00
SYS_WRITEC, SYS_CLOCK, SYS_EXIT, SYS_EXIT_EXTENDED = 0x03, 0x10, 0x18, 0x20
SYS_WRITE = 0x05
ADP_STOPPED_APP_EXIT = 0x20026


class ExecError(Exception):
    """执行器无法继续（不支持 / 实现错误）；不是 guest 异常。"""


class Fault(Exception):
    """guest 同步异常（精确异常）：cause 名 + cause_info + 可选 cause_ip。"""

    def __init__(self, cause, info=0, cause_ip=None):
        if cause not in CAUSE_BIT:
            raise ExecError("unknown exception cause %r" % (cause,))
        super().__init__(cause)
        self.cause = cause
        self.info = info & MASK64
        self.cause_ip = cause_ip


# ---------------------------------------------------------------------------
# 机器几何：复用测试侧唯一读取层
# ---------------------------------------------------------------------------
def load_machine_profiles():
    """用 tools/testcases/lib/machine_profile.py 读机器几何（唯一真源）。"""
    path = REPO_ROOT / "tools" / "testcases" / "lib" / "machine_profile.py"
    spec = importlib.util.spec_from_file_location("machine_profile", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_artifacts_bin():
    """`bootrom_tiny.bin` 的默认位置（构建产物根；由 paths.py 解析）。"""
    sys.path.insert(0, str(REPO_ROOT / "tools" / "infra"))
    import paths  # noqa: E402
    return paths.test_artifacts_dir() / "bootrom" / "tiny" / "bootrom_tiny.bin"


# ---------------------------------------------------------------------------
# 存储：大端、48 位 CPU 地址、按区域解码
# ---------------------------------------------------------------------------
class Memory:
    """物理存储窗口；地址先截 48 位再按区域解码（spec/DADAO-12 §2.1）。"""

    def __init__(self):
        # name -> [base, size, bytearray, writable, executable, read_only_err]
        self.regions = {}

    def add_region(self, name, base, size, writable=True, executable=True):
        self.regions[name] = [base & MASK48, size, bytearray(size),
                              writable, executable]

    def region_of(self, addr, width=1):
        addr &= MASK48
        for name, (base, size, _data, _w, _x) in self.regions.items():
            if base <= addr and addr + width <= base + size:
                return name, addr - base
        return None, None

    def load(self, addr, blob, writable=True, force=False):
        """把 blob 原样写入某个已登记区域（ELF 段 / BootROM 映像）。

        `force=True` 只用于**初始化装机**（BootROM 映像落在只读区域），
        不是运行期的写通道：guest 的写仍走 `write_memory` 并被拒。
        """
        name, off = self.region_of(addr, len(blob))
        if name is None:
            raise ExecError("load target %#x (%d bytes) outside every region"
                            % (addr, len(blob)))
        region = self.regions[name]
        if not region[3] and not force:
            raise ExecError("load target %#x lands in read-only region %s"
                            % (addr, name))
        region[2][off:off + len(blob)] = blob

    def _read(self, width, addr):
        addr &= MASK48
        name, off = self.region_of(addr, width)
        if name is None:
            # addr[47:42]==0（内存窗口，Tiny 无 PTW）或越界/保留 cfx ⇒ CFXMEM。
            raise Fault("CfxMem", info=addr)
        data = self.regions[name][2]
        chunk = bytes(data[off:off + width])
        return int.from_bytes(chunk, "big")      # 大端（spec/SimRISC-00 §3）

    def _write(self, width, addr, value):
        addr &= MASK48
        name, off = self.region_of(addr, width)
        if name is None:
            raise Fault("CfxMem", info=addr)
        region = self.regions[name]
        if not region[3]:
            # 测试机上写 BootROM 未在用例中出现；显式失败而非静默丢弃。
            raise Fault("CfxMem", info=addr)
        region[2][off:off + width] = (value & ((1 << (8 * width)) - 1)).to_bytes(
            width, "big")

    def read_memory(self, width, addr):
        """IDL 库原语 `read_memory(width, addr)`：大端、零扩展。"""
        if width not in (8, 16, 32, 64):
            raise ExecError("read_memory: unsupported width %r" % (width,))
        return self._read(width // 8, addr)

    def write_memory(self, width, addr, value):
        """IDL 库原语 `write_memory(width, addr, value)`：大端、写低 width 位。"""
        if width not in (8, 16, 32, 64):
            raise ExecError("write_memory: unsupported width %r" % (width,))
        self._write(width // 8, addr, value)

    def fetch(self, addr):
        """取指：指令字定长大端（spec/SimRISC-00 §3），与数据端序注入解耦。"""
        addr &= MASK48
        name, off = self.region_of(addr, 4)
        if name is None:
            raise Fault("CfxMem", info=addr)
        data = self.regions[name][2]
        return ((data[off] << 24) | (data[off + 1] << 16)
                | (data[off + 2] << 8) | data[off + 3])

    def load_bytes(self, addr, count):
        name, off = self.region_of(addr, count)
        if name is None:
            raise Fault("CfxMem", info=addr)
        return bytes(self.regions[name][2][off:off + count])

    def dump_region(self, name):
        return bytes(self.regions[name][2])


def is_naturally_aligned(width, addr):
    """IDL 库原语：宽度（位）的自然对齐（8 位无对齐要求）。"""
    return width == 8 or (addr % (width // 8)) == 0


# ---------------------------------------------------------------------------
# 译码：contracts/opcodes.yaml（唯一编码真源）
# ---------------------------------------------------------------------------
class Insn:
    __slots__ = ("id", "mnemonic", "format", "fields", "word")

    def __init__(self, rec, fields, word):
        self.id = rec["id"]
        self.mnemonic = rec["mnemonic"]
        self.format = rec["format"]
        self.fields = fields
        self.word = word

    def __getitem__(self, name):
        return self.fields[name]

    def __repr__(self):
        return "<Insn %s %r>" % (self.id, self.fields)


_BITS_RE = re.compile(r"^\[(\d+):(\d+)\]$")


class Decoder:
    def __init__(self, path=OPCODES):
        try:
            import yaml
        except ImportError:  # pragma: no cover - 环境问题
            raise ExecError("PyYAML 未安装（contracts/opcodes.yaml 读取需要）")
        records = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        self.entries = []
        for rec in records:
            mask = int(str(rec["mask"]), 0)
            value = int(str(rec["value"]), 0)
            self.entries.append((mask, value, rec))
        if len({(m, v) for m, v, _ in self.entries}) != len(self.entries):
            raise ExecError("opcodes.yaml: (mask, value) 不唯一，无法译码")

    def decode(self, word):
        for mask, value, rec in self.entries:
            if (word & mask) == value:
                return Insn(rec, self._fields(rec, word), word)
        return None

    @staticmethod
    def _fields(rec, word):
        out = {}
        for fld in rec["fields"]:
            m = _BITS_RE.match(fld["bits"])
            if not m:
                raise ExecError("opcodes.yaml: bad bits %r for %s"
                                % (fld["bits"], rec["id"]))
            hi, lo = int(m.group(1)), int(m.group(2))
            width = hi - lo + 1
            raw = (word >> lo) & ((1 << width) - 1)
            if fld.get("signed") and (raw >> (width - 1)):
                raw -= 1 << width
            out[fld["name"]] = raw
        return out


# ---------------------------------------------------------------------------
# 执行器
# ---------------------------------------------------------------------------
def _sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


class Cfx:
    """单个已实现 cfx 的寄存器面（cg3/cg4/cg5/cg7/cg15/cg16，Tiny 只实现 hmon/power）。

    `cfx_hart` 的 cg8 计数面（hart_id/cycle/insn）与 `cfx_pmem` 的 cg15 DMA 引擎面
    不在本模型范围；对它们的访问走通用分支 ⇒ `CFXREG`（与 Tiny 不实现这两个 cfx 一致）。
    """

    def __init__(self, cfxha, vector, switch_mode, sync_mask):
        self.cfxha = cfxha
        self.cg3 = [0] * 16
        for rc in (CG3_TRAP, CG3_MEM, CG3_REG, CG3_EXE):
            self.cg3[rc] = sync_mask
        self.cg3[12] = MASK64           # cg 级授权位图（bit3 硬件固定 1）
        self.cg3[CG3_SWITCH] = switch_mode
        self.cg3[CG3_VECTOR] = vector
        self.cg4 = [0] * 7
        # cg5 入口记录（rc0–rc5）复位 0；出口意图 rc8–rc10 复位 0、rc11 全 1
        # （fail-safe：默认屏蔽所有异步源，§3.6）。
        self.cg5 = [0] * 12
        self.cg5[CG5_ESC_INTR_MASK] = MASK64
        self.cg7 = [0] * 64
        # cg15（ADR-0064 D5/D6）：cfx_hart 持有异步入口记录/捕获缓冲；cfx0–cfx3
        # 只有 rc3 = 本模式异步来源掩码（复位全 1）。None = 该 cfx 不实现 cg15
        # （访问 ⇒ CFXREG；cfx_pmem 的 cg15 DMA 引擎面不在本模型范围）。
        self.cg15 = None
        if cfxha == CFX_HART:
            self.cg15 = [0] * 16
            self.cg15[CG15_SWITCH] = MODE_SUPV   # rc14 复位 2（supv）
        elif cfxha in MODE_MONITOR.values():
            self.cg15 = [0] * 16
            self.cg15[CG15_ASYNC_INTR_MASK] = MASK64
        # cg16（ADR-0064 D1–D3）：只有 cfx_hart 与 cfx_pmem 实现；mask 复位全 1。
        self.cg16 = None
        if cfxha in (CFX_HART, CFX_PMEM):
            self.cg16 = [0] * 19
            self.cg16[CG16_MASK] = MASK64
        # TIMER 硬件状态：是否有一个已 arm 的 deadline 待判定（`cg16 rc1` 写 / 使能即检）。
        self.timer_armed = False

    def set_space(self, block, desc, start, size, attr):
        self.cg7[4 * block + CG7_DESC] = desc
        self.cg7[4 * block + CG7_START] = start
        self.cg7[4 * block + CG7_SIZE] = size
        self.cg7[4 * block + CG7_ATTR] = attr

    def access(self, cg, rc, write, value=0):
        """cfx_read/cfx_write：存在性/读写权限 ⇒ CFXREG（spec/Kaiwa §3 表）。"""
        # cg3（§3.4）：rc0–3 同步来源 mask、rc12 cg 级授权位图、rc14 切模式、rc15 向量；
        # rc4–rc11/rc13 保留（访问 ⇒ CFXREG）。
        if cg == 3 and (0 <= rc <= 3 or rc in (12, CG3_SWITCH, CG3_VECTOR)):
            if write and rc == 12:       # cg 级授权位图：bit3 硬件固定 1
                self.cg3[rc] = (value | (1 << 3)) & MASK64
                return 0
            if write:
                if rc == CG3_VECTOR:
                    self.cg3[rc] = value & ~0x3 & MASK64
                elif rc == CG3_SWITCH:
                    self.cg3[rc] = 3          # Tiny 恒 hypv：写入被忽略，保存值 3
                else:
                    self.cg3[rc] = value & MASK64
                return 0
            return self.cg3[rc]
        if cg == 15 and self.cg15 is not None:
            # cfx_hart：rc0–rc5 入口记录 HW/RO（软件写忽略、不产生异常），
            # rc14/rc15 软件可读写，其余保留（访问 ⇒ CFXREG）。cfx0–cfx3：
            # 只有 rc3 = 异步来源掩码（RW，整 64 位）。
            if self.cfxha == CFX_HART and \
                    (0 <= rc <= 5 or rc in (CG15_SWITCH, CG15_VECTOR)):
                if rc <= 5:
                    if write:
                        return 0
                    return self.cg15[rc]
                if write:
                    if rc == CG15_SWITCH:      # 2 位字段（进入时取 rc14）
                        self.cg15[rc] = value & 0x3
                    else:                      # rc15：48 位核内地址，忽略低 2 位
                        self.cg15[rc] = value & MASK48 & ~0x3
                return self.cg15[rc]
            if self.cfxha in MODE_MONITOR.values() and \
                    rc == CG15_ASYNC_INTR_MASK:
                if write:
                    self.cg15[rc] = value & MASK64
                return self.cg15[rc]
        # cg16（§4.7/§4.9；ADR-0064 D1–D3）：源侧统一中断面。cfx_hart 实现
        # rc0 timer_ctrl（仅 bit0）/ rc1 timer_cmp / rc16 mask / rc17 pending /
        # rc18 ack；cfx_pmem 只有 rc16/17/18。其余 rc 与其它 cfx ⇒ CFXREG。
        if cg == 16 and self.cg16 is not None:
            if self.cfxha == CFX_HART:
                known = 0 <= rc <= 1 or \
                    rc in (CG16_MASK, CG16_PENDING, CG16_ACK)
            else:
                known = rc in (CG16_MASK, CG16_PENDING, CG16_ACK)
            if known:
                if rc == CG16_TIMER_CTRL:
                    if write:
                        self.cg16[rc] = value & 0x1     # 只留 bit0 ENABLE
                    return self.cg16[rc]
                if rc == CG16_TIMER_CMP:
                    if write:
                        self.cg16[rc] = value & MASK64
                    return self.cg16[rc]
                if rc == CG16_MASK:
                    if write:                           # 保留位写忽略
                        self.cg16[rc] = value & CG16_SUBEVENT0
                    return self.cg16[rc]
                if rc == CG16_PENDING:                  # RO：写入 ⇒ CFXREG
                    if write:
                        raise Fault("CfxReg", info=0)
                    return self.cg16[rc]
                # rc18 ack：W1C，读 0；对已清位写 1 为 no-op；保留位忽略。
                if write:
                    self.cg16[CG16_PENDING] &= \
                        ~(value & CG16_SUBEVENT0) & MASK64
                return 0
        if cg == 4 and 0 <= rc <= 6:
            if write:
                raise Fault("CfxReg", info=0)
            return self.cg4[rc]
        # cg5（§3.6）：rc0–rc5 只由硬件写（软件写 ⇒ CFXREG），rc8–rc11 出口意图 RW；
        # rc6/rc7 及其余 rc 保留（访问 ⇒ CFXREG）。
        if cg == 5 and (0 <= rc <= 5 or 8 <= rc <= 11):
            if rc <= 5:
                if write:
                    raise Fault("CfxReg", info=0)
                return self.cg5[rc]
            if write:
                if rc == CG5_ESC_RUN_MODE:
                    self.cg5[rc] = value & 0x3
                elif rc == CG5_ESC_CFX_CODE:
                    self.cg5[rc] = value & 0x3F
                elif rc == CG5_ESC_IP:
                    self.cg5[rc] = value & MASK48 & ~0x3
                else:                     # rc11：整 64 位
                    self.cg5[rc] = value & MASK64
            return self.cg5[rc]
        if cg == 7 and 0 <= rc <= 63:
            if write:
                raise Fault("CfxReg", info=0)
            return self.cg7[rc]
        raise Fault("CfxReg", info=0)


class Machine:
    """RegRAS 用**环形缓冲 + 隐藏基准**（ADR-0012 D7.5 / spec/SimRISC-00 §2.4.3）。

    物理槽 `ra[0]` = `ra0` 头 `{SBZ,RACNT,MRPTR}`（不占窗口、不参与映射）；
    `ra[1..63]` 是环形数据槽。逻辑 RA 下标 `i` 的物理位置由隐藏基准
    `ras_base`（0..62，复位 0，不可架构访问）决定：`1 + (ras_base + i) % 63`
    ——与 QEMU `ra_phys()` / gem5 `ras::phys()` 同式，`call` 压栈 `+1`、
    `ret` 弹栈 `−1`（模 63），因此搬栈只动基准、不搬条目。

    `banks["ra"]` 因此是**物理**视图；架构读写/快照导出（`get`/`set`/
    `snapshot`）一律经 `_ra_phys()` 换算成**逻辑**视图。
    """

    RAS_SLOTS = 63                           # 环形数据槽 ra1..ra63

    def __init__(self, profile, mem):
        self.profile = profile
        self.mem = mem
        self.dec = Decoder()
        self.banks = {b: [0] * 64 for b in ("rd", "rb", "rf", "ra")}
        self.ras_base = 0                    # 隐藏基准（逻辑↔物理换算用，非架构状态）
        self.banks["rf"][0] = RF0_RESET      # spec/SimRISC-00 §2.3.1 只读 qNaN 位
        self.ip = 0
        self.mode = MODE_HYPV
        self.cfx_code = 63
        # cfx_time_value 的白盒注入点（spec/DADAO-12 §4.10）：Tiny 不实现 cfx_time，
        # 定时器语义只在自检里用该值判定「到期边沿」（单位同 `timer_cmp`）。
        self.time_value = 0
        self.steps = 0
        self.halted = False
        self.exit_code = None
        self.output = bytearray()
        # rd8 的「是否有定义」：contract-semihosting §3 里「无返回」的服务
        # 不规定 rd8；QEMU 用 0xdeadbeef 占位（实现约定，不是架构语义），
        # 故运行结果比对时按本标记忽略 rd8（见 idl/tools/idl_exec_parity.py）。
        self.rd8_defined = True
        self.jumped = False
        self.cur_word = 0
        self.last_step = None
        self.semihost_service = None
        # 保留标记：键 = 精确地址 + 访问宽度（spec/SimRISC-12 §1「保留机制」）。
        # 单 hart：`None` = 未设；异常/中断进入与每次 sc 都清（`ISS-443` 已三平台收敛）。
        self.reservation = None
        self.cfx = {}
        hmon_base = profile["hmon_base"]
        self.cfx[3] = Cfx(3, hmon_base, MODE_HYPV, SYNC_MASK_HMON)
        self.cfx[3].set_space(0, 0b00011, 0x3FF_0000_0000, 0x1_0000, 0b111)
        # 启动链 power → hmon：hmon 帧留下 CFXTRAP、prev_mode=hypv、prev_cfx=power，
        # 出口意图 rc8–rc11 按入口记录复制（rc11 = 进入前 hmon 掩码快照）。
        h = self.cfx[3].cg5
        h[CG5_PREV_MODE] = MODE_HYPV
        h[CG5_PREV_CFX] = 63
        h[CG5_PREV_IP] = 0
        h[CG5_PREV_INTR_MASK] = self.cfx[3].cg15[CG15_ASYNC_INTR_MASK]
        h[CG5_CAUSE_ID] = 1 << CAUSE_BIT["CfxTrap"]
        h[CG5_CAUSE_INFO] = 0x30001       # power stub 的 boot_magic（spec/Kaiwu §6.2）
        h[CG5_ESC_RUN_MODE] = h[CG5_PREV_MODE]
        h[CG5_ESC_CFX_CODE] = h[CG5_PREV_CFX]
        h[CG5_ESC_IP] = h[CG5_PREV_IP]
        self.cfx[63] = Cfx(63, profile["bootrom_base"], MODE_HYPV, SYNC_MASK_POWER)
        borom_off = (profile["bootrom_base"] & ((1 << 42) - 1))
        self.cfx[63].set_space(0, 0b00101, borom_off,
                               profile["bootrom_size"], 0b101)

    # -- 寄存器组 ----------------------------------------------------------
    def _ra_phys(self, idx):
        """逻辑 RA 下标 → 物理槽号：`0` = `ra0` 头，其余 `1 + (base + i) % 63`。

        与 QEMU `ra_phys()` / gem5 `ras::phys()` 同式（`i ∈ 1..63`）。
        """
        idx &= 63
        if idx == 0:
            return 0
        return 1 + (self.ras_base + idx) % self.RAS_SLOTS

    def get(self, bank, idx):
        idx &= 63
        if bank == "rd":
            return 0 if idx == 0 else self.banks["rd"][idx]
        if bank == "rb":
            return self.ip & MASK64 if idx == 0 else self.banks["rb"][idx]
        if bank == "rf":
            return self.banks["rf"][idx]
        if bank == "ra":
            return self.banks["ra"][self._ra_phys(idx)]
        raise ExecError("unknown bank %r" % (bank,))

    def set(self, bank, idx, value):
        idx &= 63
        value &= MASK64
        if bank == "rd":
            if idx == 0:
                return                        # rd0 只读 0，写入丢弃
            self.banks["rd"][idx] = value
            return
        if bank == "rb":
            if idx == 0:
                raise ExecError("write to rb0 (IP) reached the register file")
            self.banks["rb"][idx] = value
            return
        if bank == "rf":
            if idx == 0:
                # spec/SimRISC-00 §2.3.1：rf0 只写 [33:32]（舍入）与 [4:0]（状态）。
                old = self.banks["rf"][0]
                self.banks["rf"][0] = ((old & ~((3 << 32) | 0x1F))
                                       | (value & ((3 << 32) | 0x1F)))
            else:
                self.banks["rf"][idx] = value
            return
        if bank == "ra":
            if idx == 0:
                # spec/SimRISC-00 §2.4：ra0[63:54] SBZ 写无效，只写 [53:0]。
                self.banks["ra"][0] = ((self.banks["ra"][0] & 0xFFC0_0000_0000_0000)
                                       | (value & 0x003F_FFFF_FFFF_FFFF))
            else:
                self.banks["ra"][self._ra_phys(idx)] = value
            return
        raise ExecError("unknown bank %r" % (bank,))

    @property
    def racnt(self):
        return (self.banks["ra"][0] >> 48) & 0x3F

    @property
    def mrptr(self):
        return self.banks["ra"][0] & MASK48

    def _set_racnt(self, count):
        ra0 = self.banks["ra"][0]
        self.banks["ra"][0] = (ra0 & ~(0x3F << 48)) | ((count & 0x3F) << 48)

    def _set_mrptr(self, ptr):
        ra0 = self.banks["ra"][0]
        self.banks["ra"][0] = (ra0 & ~MASK48) | (ptr & MASK48)

    def _ras_top(self):
        """逻辑栈顶槽（`ra63`）的物理槽号。"""
        return self._ra_phys(63)

    def ras_push(self, ret_addr):
        """spec/SimRISC-00 §2.4.1 C1–C3b（精确：判定/访存全部先于 RA 修改）。

        环形缓冲：C1/C2 只改栈顶槽；C3a/C3b 只**写一个槽 + 基准 +1**，
        既有条目保持原物理槽（不再整体重排）。
        """
        ret_addr &= MASK48
        n = self.racnt
        top_phys = self._ras_top()
        top = self.banks["ra"][top_phys]
        if n == 0:
            # C1：空栈 ⇒ 直接写逻辑栈顶槽（基准不动）。
            self.banks["ra"][top_phys] = (1 << 48) | ret_addr
            self._set_racnt(1)
            return
        if (top & MASK48) == ret_addr and ((top >> 48) & 0xFFFF) < 0xFFFF:
            # C2：递归折叠（同址）⇒ 栈顶计数 +1。
            self.banks["ra"][top_phys] = top + (1 << 48)
            return
        entry = (1 << 48) | ret_addr
        if n < 63:
            # C3a：基准 +1 让出新的逻辑栈顶槽，只写该槽。
            self.ras_base = (self.ras_base + 1) % self.RAS_SLOTS
            self.banks["ra"][self._ras_top()] = entry
            self._set_racnt(n + 1)
            return
        # C3b：RACNT == 63 ⇒ 栈底（逻辑 1）溢出到 MemRAS；按**旧**基准读栈底。
        ptr = self.mrptr
        if ptr == 0:
            raise Fault("RasOf", info=ret_addr)
        bottom = self.banks["ra"][self._ra_phys(64 - n)]
        newptr = (ptr - 8) & MASK48
        # 先访存（可能精确异常），再改 RA。
        self.mem.write_memory(64, newptr, bottom)
        self.ras_base = (self.ras_base + 1) % self.RAS_SLOTS
        self.banks["ra"][self._ras_top()] = entry
        self._set_mrptr(newptr)

    def ras_pop(self):
        """spec/SimRISC-00 §2.4.2 D1–D4b（精确）。"""
        n = self.racnt
        if n > 0:
            top_phys = self._ras_top()
            top = self.banks["ra"][top_phys]
            cnt = (top >> 48) & 0xFFFF
            if cnt == 0:
                raise Fault("RasUf")
            if cnt > 1:
                # D2：递归折叠 ⇒ 栈顶计数 −1。
                self.banks["ra"][top_phys] = top - (1 << 48)
                return top & MASK48
            # D3：弹出栈顶 ⇒ 基准 −1（既有条目保持原物理槽）。
            target = top & MASK48
            self.ras_base = (self.ras_base + self.RAS_SLOTS
                             - 1) % self.RAS_SLOTS
            self._set_racnt(n - 1)
            return target
        ptr = self.mrptr
        if ptr == 0:
            raise Fault("RasUf")
        entry = self.mem.read_memory(64, ptr)
        cnt = (entry >> 48) & 0xFFFF
        if cnt == 0:
            raise Fault("RasUf")
        target = entry & MASK48
        newptr = (ptr + 8) & MASK48
        if cnt == 1:
            self._set_mrptr(newptr)
            return target
        # D4b（count > 1）：回填逻辑栈顶槽，RACNT = 1（基准不动）。
        self.banks["ra"][self._ras_top()] = ((cnt - 1) << 48) | target
        self._set_mrptr(newptr)
        self._set_racnt(1)
        return target

    # -- 保留标记（spec/SimRISC-12 §1「保留机制」） ------------------------
    def reservation_set(self, ea, width):
        """设本 hart 的保留标记：键 = 精确地址 + 访问宽度（不按 cache line 扩大）。"""
        self.reservation = (ea & MASK48, width)

    def reservation_clear_all(self):
        """清本 hart 的全部保留标记。"""
        self.reservation = None

    def store_conditional(self, ea, width, value):
        """原子「查标记 → 条件写 → 清标记」；返回 0 = 成功 / 1 = 失败。

        spec/SimRISC-12 §1：标记仍在 ⇒ 写内存并返回 0；否则不写内存、返回 1；
        **成败都清**本 hart 全部标记。照 UDB 先例不拆成「先查再写」。
        单 hart 口径（`ISS-440`）：清除侧只列「**另一 hart** 对同址同宽 store」，
        故本 hart 的普通 store 不清标记；异常/中断进入的清理由 `take_exception` 做。
        """
        ea &= MASK48
        if self.reservation != (ea, width):
            self.reservation = None
            return 1
        self.mem.write_memory(width, ea, value)   # 可能精确异常（异常进入清标记）
        self.reservation = None
        return 0

    # -- 控制流 ------------------------------------------------------------
    def jump(self, addr):
        self.ip = addr & MASK64
        self.jumped = True

    # -- 异常进入/退出（spec/DADAO-12 §5.2/§5.3） --------------------------
    def _cfx_or_fail(self, cfxha):
        if cfxha not in IMPLEMENTED_CFX:
            raise Fault("CfxReg", info=0)
        return self.cfx[cfxha]

    def _cfx_perm_denied(self, cfxha, mask_rc):
        """两轴权限的来源 mask 判定（spec/DADAO-12 §3.4 / §5.2(一)）。

        位索引 = **源 cfx**（即当前 `inner_cfx_code`）：0 = 允许、1 = 屏蔽；访问
        自身 cfx（`cfxha == cfx_code`）只绕过 cfx 轴，不查 mask。未实现的 cfx 没有
        寄存器行 ⇒ 本函数判「不拒绝」，存在性由调用方（ILLI/CFXREG）负责。
        本执行器只建模 cg3（hypv）行：Tiny 的运行模式恒 hypv（`spec/Kaiwu §2`），
        cg0–cg2 的行不建模（越界即静默错，故意不做——不是本任务范围）。
        """
        if cfxha == self.cfx_code:
            return False
        cfx = self.cfx.get(cfxha)
        if cfx is None:
            return False
        return ((cfx.cg3[mask_rc] >> self.cfx_code) & 1) != 0

    def _check_cfxexe(self, addr):
        """直接跳转/取指进入**其它** cfx 的 cfxexe 来源掩码（spec/DADAO-12 §3.4 cg3 rc3）。

        核内地址高 6 位 `addr[47:42]` 选中目标 cfx；目标不是当前 cfx 时按其
        `<mode>_cfxexe` 的**源 cfx 位**判定（1 = 屏蔽）。拒绝 ⇒ `CFXPERM`，
        `cause_info` = **目标 IP**（§4.1）。`addr[47:42] = 0` 是内存窗口、不是 cfx；
        本 profile 未实现的 cfx 没有寄存器行 ⇒ 由存储层报 `CFXMEM`，不在此拒绝。
        允许进入时的 `inner_cfx_code` 切换不建模（cfx 内部空间归属属 `cfxmem` 轴，
        单列不在本任务范围；`tests/inst` 无该维度载体）。
        """
        target = (addr & MASK48) >> 42
        if target == 0 or target == self.cfx_code:
            return
        if self._cfx_perm_denied(target, CG3_EXE):
            raise Fault("CfxPerm", info=addr, cause_ip=addr)

    def take_exception(self, cause, cause_ip, info=0, target=None):
        # spec/SimRISC-12 §1「保留机制」：异常/中断进入清本 hart 全部保留标记
        # （`ISS-443` 已由 qemu/gem5/chipyard 三平台收敛；单 hart 无异步中断）。
        self.reservation = None
        if target is None:
            # spec/DADAO-12 §5.2(一)：CFXESC 的目标 = **当前 cfx**（不属于 monitor 路由）；
            # 其余同步异常进当前运行模式的 monitor。
            target = self.cfx_code if cause == "CfxEsc" \
                else MODE_MONITOR.get(self.mode, 3)
        cfx = self.cfx.get(target)
        if cfx is None:
            raise ExecError("exception target cfx %r not implemented" % (target,))
        # §3.6/§5.2 步骤 4：入口记录 = 异常前运行模式、cfx、ip、当前模式 monitor 的
        # `cg15 rc3` 快照；`rc8`–`rc11` 是硬件复制的出口意图（软件随后可改）。
        mon_ha = MODE_MONITOR.get(self.mode, 3)
        mon = self.cfx.get(mon_ha)
        if mon is None or mon.cg15 is None:
            raise ExecError("exception entry: monitor cfx %d for mode %d "
                            "not implemented" % (mon_ha, self.mode))
        prev_mask = mon.cg15[CG15_ASYNC_INTR_MASK] & MASK64
        onehot = 1 << CAUSE_BIT[cause]
        cfx.cg5[CG5_PREV_MODE] = self.mode
        cfx.cg5[CG5_PREV_CFX] = self.cfx_code
        cfx.cg5[CG5_PREV_IP] = cause_ip & MASK64
        cfx.cg5[CG5_PREV_INTR_MASK] = prev_mask
        # ADR-0062 D2/D3：`CFXMEM`/`CFXPERM` 都只置低位那一位，不再叠加任何子原因
        # （`[57] NONPTW` / `[39] NCFXPERM` 已删除）；`cause_info` 口径见 §3.6 / ADR D4。
        cfx.cg5[CG5_CAUSE_ID] = onehot & MASK64
        cfx.cg5[CG5_CAUSE_INFO] = info & MASK64
        cfx.cg5[CG5_ESC_RUN_MODE] = cfx.cg5[CG5_PREV_MODE]
        cfx.cg5[CG5_ESC_CFX_CODE] = cfx.cg5[CG5_PREV_CFX]
        cfx.cg5[CG5_ESC_IP] = cfx.cg5[CG5_PREV_IP]
        cfx.cg5[CG5_ESC_INTR_MASK] = prev_mask
        if cause == "CfxTrap":
            cfx.cg4[CG4_TRAP_NUM] += 1
        else:
            cfx.cg4[CG4_SYNC_NUM] += 1
        # ADR-0061 D5：`trap`/`escape` 不保存、不恢复来源掩码（策略不是现场）；
        # `trap` 只把进入前值抄入出口意图 rc11。
        self.mode = cfx.cg3[CG3_SWITCH]
        self.cfx_code = target
        self.ip = cfx.cg3[CG3_VECTOR] & MASK64
        self.jumped = True
        return cfx

    def escape(self, cfxha):
        """escape 的步骤 0（目标合法性）与步骤 1–3（spec/DADAO-12 §5.1/§5.3）。

        `imms18 != 0` / 保留 cfxha 的 ILLI 在 operation 里先判。这里只认当前 cfx 的
        **出口意图** `cg5 rc8`–`rc11`：`cfxha != 当前 cfx` ⇒ 当前 cfx 的 `CFXESC`；
        目标运行模式不得高于当前模式、目标 cfx 必须已实现、目标模式必须有对应 monitor，
        否则在切换任何状态之前报 `CFXESC`。不设帧有效位（`cg5 rc4 == 0` 也可返回），
        重复 `escape` 由软件负责。成功后 `escape_num` +1，跳 `rc10`，并把 `rc11`
        **整字**写入目标模式 monitor 的 `cg15 rc3`（与切模式/切 cfx/跳转原子完成）。
        """
        cur = self.cfx.get(self.cfx_code)
        if cur is None:
            raise ExecError("escape in unimplemented cfx %r" % (self.cfx_code,))
        if cfxha != self.cfx_code:
            raise Fault("CfxEsc", cause_ip=self.ip)
        target_mode = cur.cg5[CG5_ESC_RUN_MODE] & 0x3
        target_cfx = cur.cg5[CG5_ESC_CFX_CODE] & 0x3F
        if target_mode > self.mode:          # 只允许同级或降权（§5.1）
            raise Fault("CfxEsc", cause_ip=self.ip)
        if target_cfx not in IMPLEMENTED_CFX:   # 目标 cfx 未实现
            raise Fault("CfxEsc", cause_ip=self.ip)
        mon_ha = MODE_MONITOR[target_mode]
        mon = self.cfx.get(mon_ha)
        if mon is None or mon.cg15 is None:  # 目标模式没有对应 monitor（如 jail→jmon）
            raise Fault("CfxEsc", cause_ip=self.ip)
        # 步骤 1–3：恢复运行模式与当前 cfx（rc8/rc9）、escape_num++、跳 rc10、
        # rc11 整字恢复目标模式 monitor 的 cg15 rc3（策略快照由软件写回）。
        cur.cg4[CG4_ESCAPE_NUM] += 1
        self.mode = target_mode
        self.cfx_code = target_cfx
        self.ip = cur.cg5[CG5_ESC_IP] & MASK48 & ~0x3
        mon.cg15[CG15_ASYNC_INTR_MASK] = \
            cur.cg5[CG5_ESC_INTR_MASK] & MASK64
        self.jumped = True

    # -- 异步进入（spec/DADAO-12 §5.4；ADR-0064 D3–D6/D9） -----------------
    def async_mask(self, mode=None):
        """当前运行模式 monitor 的异步来源掩码（`cfx_<monitor>_async_intr_mask`）。

        spec/DADAO-12 §4.1–§4.4/§5.4（一）/ADR-0064 D6：取当前运行模式对应 monitor
        （U→umon、J→jmon、S→smon、H→hmon）的 `cg15 rc3`；位 = 源 cfxha，
        0 = 允许、1 = 屏蔽，复位全 1。monitor 未实现 ⇒ 显式失败（不静默放行）。
        """
        mode = self.mode if mode is None else mode
        mon_ha = MODE_MONITOR[mode & 0x3]
        mon = self.cfx.get(mon_ha)
        if mon is None or mon.cg15 is None:
            raise ExecError("async mask: monitor cfx %d for mode %d not implemented"
                            % (mon_ha, mode))
        return mon.cg15[CG15_ASYNC_INTR_MASK] & MASK64

    def _async_hart(self):
        """`cfx_hart`（异步捕获缓冲持有者）；本 profile 未实现 ⇒ None。"""
        hart = self.cfx.get(CFX_HART)
        if hart is None or hart.cg15 is None:
            return None
        return hart

    def refresh_async_summary(self):
        """把源 `cg16 rc17` 的 pending 汇总到 `cfx_hart cg15 rc5`（位 = 源 cfxha）。

        spec/DADAO-12 §4.7/§5.4（六）/ADR-0064 D4：某源 pending 任一子事件置位
        时置位、该源 pending 全清（ack 后）时落位；异步进入**不改** rc5。
        """
        hart = self._async_hart()
        if hart is None:
            return 0
        summary = 0
        for src_ha in (CFX_HART, CFX_PMEM):
            src = self.cfx.get(src_ha)
            if src is not None and src.cg16 is not None \
                    and src.cg16[CG16_PENDING]:
                summary |= 1 << src_ha
        hart.cg15[CG15_SRC_PENDING] = summary
        return summary

    def async_post(self, src_bits):
        """源侧事件：置各源 `cg16 rc17` 的子事件 bit0（§5.4（四）/ADR-0064 D3）。

        位 = 源 cfxha（`ASYNC_SRC_TIMER` = bit 15、`ASYNC_SRC_PMEM` = bit 32）。
        与当前运行模式是否放行无关——mask 只阻止异步进入，pending 保留到 ack；
        同一源多次事件合并为 bit0（不计数）。TIMER 的正常到期边沿由 `timer_check`
        判定（受 `ENABLE` 门控）；本方法是源事件/白盒注入入口。
        """
        for src_ha in (CFX_HART, CFX_PMEM):
            if not (src_bits >> src_ha) & 1:
                continue
            src = self.cfx.get(src_ha)
            if src is None or src.cg16 is None:
                raise ExecError("async source cfx %d not implemented" % src_ha)
            src.cg16[CG16_PENDING] |= CG16_SUBEVENT0
        self.refresh_async_summary()

    def timer_check(self, now=None):
        """TIMER 到期边沿（spec/DADAO-12 §4.7 `cg16`；ADR-0064 D3）。

        `ENABLE=1` 且有一个已 arm 的 deadline 且 `cfx_time_value >= timer_cmp` ⇒ 置
        pending bit0 一次、随后 disarm（每个已 arm 的 deadline 只置位一次）。
        `ENABLE=0` 时到期不置位；写 `cmp` 只重新 arm，不清 pending。
        """
        hart = self.cfx.get(CFX_HART)
        if hart is None or hart.cg16 is None:
            return False
        now = self.time_value if now is None else now
        if not (hart.cg16[CG16_TIMER_CTRL] & 0x1):
            return False
        if not hart.timer_armed:
            return False
        if now < hart.cg16[CG16_TIMER_CMP]:
            return False
        hart.cg16[CG16_PENDING] |= CG16_SUBEVENT0
        hart.timer_armed = False
        self.refresh_async_summary()
        return True

    def async_ready_sources(self, mon_mask=None):
        """当前指令边界可进入的源集合（位 = 源 cfxha；§5.4（一）/ADR-0064 D4/D9）。

        逐源判定：`(pending & ~源mask) != 0`、当前运行模式 monitor 的
        `cg15 rc3[源 cfxha] == 0`，`TIMER` 还要求 `ENABLE=1`；且**当前运行模式
        ≤ `cfx_hart cg15 rc14`**（运行模式上限）。不满足 ⇒ 该源不进入
        （pending 与 `cg15 rc5` 保留、不报错）。
        """
        hart = self._async_hart()
        if hart is None:
            return 0
        if (self.mode & 0x3) > (hart.cg15[CG15_SWITCH] & 0x3):
            return 0
        mon_mask = self.async_mask() if mon_mask is None else mon_mask
        ready = 0
        for src_ha in (CFX_HART, CFX_PMEM):
            src = self.cfx.get(src_ha)
            if src is None or src.cg16 is None:
                continue
            pending = src.cg16[CG16_PENDING] & CG16_SUBEVENT0
            if not pending:
                continue
            if src.cg16[CG16_MASK] & pending:       # 源自身 gate
                continue
            if src_ha == CFX_HART and \
                    not (src.cg16[CG16_TIMER_CTRL] & 0x1):
                continue                            # TIMER 还要求 ENABLE=1
            if (mon_mask >> src_ha) & 1:            # 运行模式 gate
                continue
            ready |= 1 << src_ha
        return ready

    def cfx_write(self, cfxha, cg, rc, value):
        """cfx2rc：写寄存器并施加机器级副作用（timer arm/使能即检、pending 汇总）。

        存储层语义仍在 `Cfx.access`（存在性/权限 ⇒ CFXREG）；本方法只补硬件行为：
        写 `cg16 rc1` 重新 arm deadline、写 `cg16 rc0` 的 ENABLE 0→1 立即检到期
        （spec/DADAO-12 §4.7；ADR-0064 D3），任一写后刷新 `cg15 rc5` 汇总。
        """
        cfx = self.cfx.get(cfxha)
        if cfx is None:
            raise Fault("CfxReg", info=0)
        prev_enable = 0
        if cfxha == CFX_HART and cfx.cg16 is not None:
            prev_enable = cfx.cg16[CG16_TIMER_CTRL] & 0x1
        cfx.access(cg, rc, True, value)
        if cfxha == CFX_HART and cg == 16:
            if rc == CG16_TIMER_CMP:
                cfx.timer_armed = True               # 写 cmp 只重新 arm
                self.timer_check()
            elif rc == CG16_TIMER_CTRL:
                enable = cfx.cg16[CG16_TIMER_CTRL] & 0x1
                if enable and not prev_enable:       # ENABLE 0→1：使能即检
                    cfx.timer_armed = True
                    self.timer_check()
        self.refresh_async_summary()

    def async_entry(self):
        """指令边界的一次异步进入尝试（spec/DADAO-12 §5.4；ADR-0064 D4–D6/D9）。

        返回 True = 已进入（切到 `cg15 rc14` 运行模式与 `rc15` 向量）。**逐源判定、
        多源合并**：放行源 = `async_ready_sources()`；`src_frame` = 其位并集，
        `excp_async_num` **每次进入 +1**（与源个数无关）。**每次进入整体覆盖**
        `cg15 rc0`–`rc4`（不因 `src_frame != 0` 拒绝，无 frame_valid/活动期）。
        **进入不清源 pending、也不改 `cg15 rc5`**：只有源 `cg16 rc18` 的 W1C 才清。
        写入集合 = `cg15 rc0`–`rc4` + hart 自己的 `cg5 rc8`–`rc11`；**不写** hart
        `cg5 rc0`–`rc3`（入口记录在 `cg15`，§4.7/§5.4）。

        本 profile 无 `cfx_hart` 行（Tiny 不实现，且 TIMER 源即本 cfx）⇒ 没有异步源，
        返回 False（不进入）。
        """
        hart = self._async_hart()
        if hart is None:
            return False
        self.timer_check()                  # 到期边沿在指令边界判定
        self.refresh_async_summary()
        temp_mask = self.async_mask() & MASK64
        allowed = self.async_ready_sources(temp_mask)
        if allowed == 0:
            return False
        prev_ip = self.ip & MASK48 & ~0x3             # 已提交指令之后的 rb0
        hart.cg15[CG15_SRC_FRAME] = allowed           # 捕获快照：整体覆盖
        hart.cg15[CG15_PREV_MODE] = self.mode & 0x3
        hart.cg15[CG15_PREV_CFX] = self.cfx_code & 0x3F
        hart.cg15[CG15_PREV_IP] = prev_ip
        hart.cg15[CG15_PREV_INTR_MASK] = temp_mask
        # 出口意图在 hart 自己的 cg5 rc8–rc11（入口记录不写 cg5 rc0–rc3）。
        hart.cg5[CG5_ESC_RUN_MODE] = self.mode & 0x3
        hart.cg5[CG5_ESC_CFX_CODE] = self.cfx_code & 0x3F
        hart.cg5[CG5_ESC_IP] = prev_ip
        hart.cg5[CG5_ESC_INTR_MASK] = temp_mask
        self.mode = hart.cg15[CG15_SWITCH] & 0x3      # 取 rc14（RW，复位 2 = supv）
        self.cfx_code = CFX_HART
        self.ip = hart.cg15[CG15_VECTOR] & MASK48
        hart.cg4[CG4_ASYNC_NUM] += 1
        self.reservation = None                       # 进入清本 hart 保留标记
        self.jumped = True
        return True

    # -- semihosting（contract-semihosting §1/§4/§5） ----------------------
    def _semihost(self, immu18):
        service = self.get("rd", 16) & 0xFF
        self.semihost_service = service
        if service == SYS_WRITEC:
            ptr = self.get("rb", 16) & MASK48
            self.output.append(self.mem.read_memory(8, ptr) & 0xFF)
            self.rd8_defined = False      # 「无返回」⇒ rd8 未定义
            self.jumped = False
            return
        if service == SYS_CLOCK:
            self.set("rd", 8, 0)
            self.rd8_defined = True
            self.jumped = False
            return
        if service == SYS_WRITE:
            # contract-semihosting §3：SYS_WRITE 返回**未写字节数**。本执行器不提供
            # 块写通道 ⇒ 报「全部未写」（返回请求长度），guest 的 `SIG_DUMP`
            # （tests/shared/asm/signature.inc）据此回退 `SYS_WRITEC` 逐字节路径，
            # 与 QEMU/gem5 实测路径一致（idl/docs/four-way.md）。
            block = self.get("rb", 16) & MASK48
            nbytes = self.mem.read_memory(64, block + 16)
            self.set("rd", 8, nbytes)
            self.rd8_defined = True
            self.jumped = False
            return
        if service in (SYS_EXIT, SYS_EXIT_EXTENDED):
            block = self.get("rb", 16) & MASK48
            reason = self.mem.read_memory(64, block)
            code = self.mem.read_memory(64, block + 8)
            self.halted = True
            if service == SYS_EXIT_EXTENDED:
                self.exit_code = code
            elif reason == ADP_STOPPED_APP_EXIT:
                self.exit_code = code
            else:
                self.exit_code = 1
            self.rd8_defined = False
            return
        raise ExecError("semihosting service %#x 未实现（contract-semihosting §3）"
                        % (service,))

    # -- 主循环 ------------------------------------------------------------
    def step(self, pc_log=None):
        """执行一条指令（含异常进入）；返回 False = 已停机。

        执行观察面（`m17-idl-004` 的逐指令 trace 消费方）：每步结束后
        `self.last_step` = `{pc, word, id, exc, fetch_fault}`——`word`/`id` 为
        `None` 表示没取到指令（取指异常），`exc` 为本步触发的异常三元组或
        `None`。`self.semihost_service` 记录本步执行的 semihosting 服务号。
        """
        if self.halted:
            return False
        self.steps += 1
        cur = self.ip
        self.jumped = False
        self.semihost_service = None
        obs = {"pc": cur, "word": None, "id": None, "exc": None,
               "fetch_fault": False}
        if pc_log is not None:
            pc_log.append(cur)
        try:
            if cur & 0x3:
                raise Fault("IAlign", info=cur, cause_ip=cur)
            self._check_cfxexe(cur)          # 直接跳转/取指进入其它 cfx（§3.4 cg3 rc3）
            word = self.mem.fetch(cur)
            self.cur_word = word
            obs["word"] = word
            obs["fetch_fault"] = False
            insn = self.dec.decode(word)
            if insn is None:
                raise Fault("Undi", info=word, cause_ip=cur)
            obs["id"] = insn.id
            fn = SEMANTICS.get(insn.id)
            if fn is None:
                raise ExecError("operation %s 未实现（m17-idl-003 范围）"
                                % (insn.id,))
            fn(self, insn)
            if not self.jumped and not self.halted:
                self.ip = cur + 4
            if not self.halted:
                # 指令边界：被中断指令已提交（rb0 已更新）⇒ 尝试一次异步进入
                # （spec/DADAO-12 §5.4；ADR-0061 D3/D4）。无 hart/无 pending 时为 no-op。
                self.async_entry()
        except Fault as exc:
            cause_ip = cur if exc.cause_ip is None else exc.cause_ip
            info = exc.info
            if info == 0:
                # spec/DADAO-12 §4.1 cause_info 表：ILLI/UNDI/CFXREG/CFXESC = 指令编码；
                # CFXPERM(cfxtrap/cfx2rd/cfx2rc 拒绝) = 触发指令地址；cfxexe 拒绝 =
                # 目标 IP（由 `_check_cfxexe` 显式给 info）；RASUF = 0。
                if exc.cause in ("Illegal", "Undi", "CfxReg", "CfxEsc"):
                    info = self.cur_word
                elif exc.cause == "CfxPerm":
                    info = cause_ip
            obs["exc"] = {"cause": exc.cause, "info": info,
                          "ip": cause_ip}
            obs["fetch_fault"] = obs["word"] is None
            self.ip = cur
            self.take_exception(exc.cause, cause_ip, info)
        self.last_step = obs
        return not self.halted

    def run(self, max_steps=2_000_000, pc_log=None):
        while not self.halted and self.steps < max_steps:
            if not self.step(pc_log):
                break
        if not self.halted and self.steps >= max_steps:
            raise ExecError("step limit %d reached at ip %#x (no SYS_EXIT)"
                            % (max_steps, self.ip))
        return self.exit_code

    # -- 快照 --------------------------------------------------------------
    def snapshot(self):
        """架构（逻辑）视图：`get("ra", i)` 已按环形映射换算到物理槽。"""
        return {
            "ip": self.ip & MASK64,
            "mode": self.mode,
            "cfx": self.cfx_code,
            "rd": [self.get("rd", i) for i in range(64)],
            "rb": [self.get("rb", i) for i in range(64)],
            "rf": [self.get("rf", i) for i in range(64)],
            "ra": [self.get("ra", i) for i in range(64)],
            "rd8_defined": self.rd8_defined,
        }

    def load_state(self, state):
        """装入初始架构状态（QEMU 观测面）：只写寄存器组，不启发式修正。

        `rf0`/`ra0` 的只读位保持观测值（运行期写入仍走 `set` 的写语义）。
        入口态给的是**逻辑** RA 视图（`ra0` + `ra1..ra63`）⇒ 基准归 0 后按映射
        落到物理槽（环形布局相对基准等价，入口基准本身不影响后续语义）。
        """
        self.ip = state["ip"] & MASK64
        self.mode = state.get("mode", MODE_HYPV) & 0x3
        self.cfx_code = state.get("cfx", 63) & 0x3F
        self.ras_base = 0
        for bank in ("rd", "rb", "rf", "ra"):
            for i, val in enumerate(state[bank]):
                if bank == "rb" and i == 0:
                    continue
                if bank == "rd" and i == 0:
                    continue
                phys = self._ra_phys(i) if bank == "ra" else i
                self.banks[bank][phys] = val & MASK64


# 每个 operation 的语义按 idl/*.idl 的正文实现；id 与 contracts/opcodes.yaml 同源。
SEMANTICS = {}


def sem(*ids):
    def deco(fn):
        for op_id in ids:
            if op_id in SEMANTICS:
                raise ExecError("duplicate semantics for %s" % op_id)
            SEMANTICS[op_id] = fn
        return fn
    return deco


# --- 03-wyde-imm：set.zw / set.ow / set.w / or.w / andn.w ------------------
@sem("set.zw_rwii_rb", "set.zw_rwii_rd")
def _op_set_zw(m, insn):
    bank = "rb" if insn.id.endswith("_rb") else "rd"
    dst = insn["rbha"] if bank == "rb" else insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    wp, imm = insn["wpN"], insn["immu16"]
    m.set(bank, dst, imm << (16 * wp))


@sem("set.ow_rwii_rd")
def _op_set_ow(m, insn):
    dst = insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    wp, imm = insn["wpN"], insn["immu16"]
    m.set("rd", dst, ((MASK64 ^ (0xFFFF << (16 * wp))) | (imm << (16 * wp))))


@sem("set.w_rwii_rf")
def _op_set_w(m, insn):
    dst = insn["rfha"]
    wp, imm = insn["wpN"], insn["immu16"]
    old = m.get("rf", dst)
    m.set("rf", dst, (old & ~(0xFFFF << (16 * wp))) | (imm << (16 * wp)))


@sem("or.w_rwii_rb", "or.w_rwii_rd")
def _op_or_w(m, insn):
    bank = "rb" if insn.id.endswith("_rb") else "rd"
    dst = insn["rbha"] if bank == "rb" else insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    wp = insn["wpN"]
    shift = 16 * wp
    old = m.get(bank, dst)
    m.set(bank, dst, (old & ~(0xFFFF << shift))
          | ((old >> shift & 0xFFFF | insn["immu16"]) << shift))


@sem("andn.w_rwii_rb", "andn.w_rwii_rd")
def _op_andn_w(m, insn):
    bank = "rb" if insn.id.endswith("_rb") else "rd"
    dst = insn["rbha"] if bank == "rb" else insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    shift = 16 * insn["wpN"]
    old = m.get(bank, dst)
    m.set(bank, dst, (old & ~(0xFFFF << shift))
          | (((old >> shift & 0xFFFF) & ~insn["immu16"]) << shift))


# --- 04/08/09/10 算术逻辑 ------------------------------------------------
@sem("add.si_riii_rd", "add.si_riii_rb")
def _op_add_si(m, insn):
    bank = "rb" if insn.id.endswith("_rb") else "rd"
    dst = insn["rbha"] if bank == "rb" else insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    m.set(bank, dst, m.get(bank, dst) + insn["imms18"])


@sem("add.o_orrr_bbd")
def _op_add_o_bbd(m, insn):
    dst = insn["rbhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rb", dst, (m.get("rb", insn["rbhc"]) + m.get("rd", insn["rdhd"]))
          & MASK64)


@sem("sub.o_orrr_dbb")
def _op_sub_o_dbb(m, insn):
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, (m.get("rb", insn["rbhc"]) - m.get("rb", insn["rbhd"]))
          & MASK64)


@sem("add.so_rrrr_rd")
def _op_add_so(m, insn):
    ha, hb = insn["rdha"], insn["rdhb"]
    if ha == hb:
        raise Fault("Illegal")
    total = _sext(m.get("rd", insn["rdhc"]), 64) + \
        _sext(m.get("rd", insn["rdhd"]), 64)
    wide = total & ((1 << 128) - 1)
    m.set("rd", ha, wide >> 64)
    m.set("rd", hb, wide & MASK64)


@sem("mul.so_rrrr_rd")
def _op_mul_so(m, insn):
    ha, hb = insn["rdha"], insn["rdhb"]
    if ha == hb:
        raise Fault("Illegal")
    a = _sext(m.get("rd", insn["rdhc"]), 64)
    b = _sext(m.get("rd", insn["rdhd"]), 64)
    wide = (a * b) & ((1 << 128) - 1)
    m.set("rd", ha, wide >> 64)
    m.set("rd", hb, wide & MASK64)


@sem("add.st_orrr_rd")
def _op_add_st(m, insn):
    # SimRISC-08 §1.1：仅低 32 位参与、进位丢弃，按结果 bit31 符号扩展写满 64 位。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a = m.get("rd", insn["rdhc"]) & 0xFFFF_FFFF
    b = m.get("rd", insn["rdhd"]) & 0xFFFF_FFFF
    m.set("rd", dst, _sext((a + b) & 0xFFFF_FFFF, 32))


@sem("add.ub_orrr_rd")
def _op_add_ub(m, insn):
    # SimRISC-10 §1.1：8 位无符号加，进位丢弃，结果零扩展写满 64 位。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    total = (m.get("rd", insn["rdhc"]) & 0xFF) + \
        (m.get("rd", insn["rdhd"]) & 0xFF)
    m.set("rd", dst, total & 0xFF)


@sem("and.o_orrr_rd")
def _op_and_o(m, insn):
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, m.get("rd", insn["rdhc"]) & m.get("rd", insn["rdhd"]))


@sem("cmp.so_orrr_rd", "cmp.uo_orrr_rd")
def _op_cmp_o(m, insn):
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a = m.get("rd", insn["rdhc"])
    b = m.get("rd", insn["rdhd"])
    if insn.id.startswith("cmp.so"):
        a, b = _sext(a, 64), _sext(b, 64)
    m.set("rd", dst, MASK64 if a < b else (0 if a == b else 1))


@sem("shl.o_orri_rd", "shl.o_orrr_rd")
def _op_shl_o(m, insn):
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    sh = insn["immu6"] if "immu6" in insn.fields else \
        (m.get("rd", insn["rdhd"]) & 0x3F)
    m.set("rd", dst, (m.get("rd", insn["rdhc"]) << sh) & MASK64)


@sem("shr.uo_orri_rd")
def _op_shr_o(m, insn):
    # SimRISC-04：64 位逻辑右移，高位补零，移位量 = immu6（0..63 全合法）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, m.get("rd", insn["rdhc"]) >> insn["immu6"])


@sem("div.so_orrr_rd")
def _op_div_so(m, insn):
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a = m.get("rd", insn["rdhc"])
    b = m.get("rd", insn["rdhd"])
    if b == 0:
        m.set("rd", dst, MASK64)
        return
    if a == 0x8000_0000_0000_0000 and b == MASK64:
        m.set("rd", dst, 0x8000_0000_0000_0000)
        return
    sa, sb = _sext(a, 64), _sext(b, 64)
    q = abs(sa) // abs(sb)
    m.set("rd", dst, (-q if (sa < 0) != (sb < 0) else q) & MASK64)


@sem("ctlz_orri_rd")
def _op_ctlz(m, insn):
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    hi = insn["immu6"]
    src = m.get("rd", insn["rdhc"])
    n = 0
    for bit in range(hi, -1, -1):
        if (src >> bit) & 1:
            break
        n += 1
    m.set("rd", dst, n)


# --- 04-arith-logic-octa（SimRISC-04 §1/§2；m17-idl-007） -----------------
# 说明：本节各 operation 的语义逐条取自 `idl/SimRISC-04.idl` 对应 `# id:` 段；
# 双目的 rrrr 形式（rdHA/rdHB = 结果高/低 64 位）**同一寄存器（含同时为 rd0）⇒ ILLI**。
def _dual_dst(insn):
    ha, hb = insn["rdha"], insn["rdhb"]
    if ha == hb:
        raise Fault("Illegal")
    return ha, hb


@sem("add.uo_rrrr_rd")
def _op_add_uo(m, insn):
    # SimRISC-04 §1：rdHA = 进位（0/1），rdHB = 低 64 位；源先读后写（65 位零扩展加）。
    ha, hb = _dual_dst(insn)
    total = m.get("rd", insn["rdhc"]) + m.get("rd", insn["rdhd"])
    m.set("rd", ha, total >> 64)
    m.set("rd", hb, total & MASK64)


@sem("sub.uo_rrrr_rd")
def _op_sub_uo(m, insn):
    # SimRISC-04 §1：rdHA = 借位（被减数 < 减数 ⇒ 1），rdHB = 低 64 位差。
    ha, hb = _dual_dst(insn)
    a, b = m.get("rd", insn["rdhc"]), m.get("rd", insn["rdhd"])
    m.set("rd", ha, 1 if a < b else 0)
    m.set("rd", hb, (a - b) & MASK64)


@sem("sub.so_rrrr_rd")
def _op_sub_so(m, insn):
    # SimRISC-04 §1：源符号扩展成 65 位相减；高半 = 结果符号扩展（负数 ⇒ 全 1）。
    ha, hb = _dual_dst(insn)
    diff = (_sext(m.get("rd", insn["rdhc"]), 64)
            - _sext(m.get("rd", insn["rdhd"]), 64))
    m.set("rd", ha, MASK64 if diff < 0 else 0)
    m.set("rd", hb, diff & MASK64)


@sem("mul.uo_rrrr_rd")
def _op_mul_uo(m, insn):
    # SimRISC-04 §1：零扩展 64×64 → 128 位精确积；rdHA/rdHB = 高/低 64 位。
    ha, hb = _dual_dst(insn)
    product = m.get("rd", insn["rdhc"]) * m.get("rd", insn["rdhd"])
    m.set("rd", ha, (product >> 64) & MASK64)
    m.set("rd", hb, product & MASK64)


@sem("clmul.o_rrrr_rd")
def _op_clmul(m, insn):
    # SimRISC-04 §2：GF(2) 多项式乘（位间无进位），rdHA/rdHB = 128 位积高/低 64 位。
    ha, hb = _dual_dst(insn)
    a = m.get("rd", insn["rdhc"])
    b = m.get("rd", insn["rdhd"])
    product = 0
    for i in range(64):
        if (b >> i) & 1:
            product ^= a << i
    m.set("rd", ha, (product >> 64) & MASK64)
    m.set("rd", hb, product & MASK64)


@sem("cmp.si_rrii_rd")
def _op_cmp_si(m, insn):
    # SimRISC-04 §1.3：rdHB 与符号扩展的 imms12 有符号比较 → -1/0/1（写满 64 位）。
    dst = insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    a = _sext(m.get("rd", insn["rdhb"]), 64)
    b = insn["imms12"]
    m.set("rd", dst, MASK64 if a < b else (0 if a == b else 1))


@sem("cmp.ui_rrii_rd")
def _op_cmp_ui(m, insn):
    # SimRISC-04 §1.3：rdHB 与零扩展的 immu12 无符号比较 → -1/0/1（写满 64 位）。
    dst = insn["rdha"]
    if dst == 0:
        raise Fault("Illegal")
    a = m.get("rd", insn["rdhb"])
    b = insn["immu12"]
    m.set("rd", dst, MASK64 if a < b else (0 if a == b else 1))


@sem("div.uo_orrr_rd")
def _op_div_uo(m, insn):
    # SimRISC-04 §1.4：64 位无符号除法；除零 ⇒ 定值全 1。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a, b = m.get("rd", insn["rdhc"]), m.get("rd", insn["rdhd"])
    m.set("rd", dst, MASK64 if b == 0 else a // b)


@sem("rem.uo_orrr_rd")
def _op_rem_uo(m, insn):
    # SimRISC-04 §1.4：64 位无符号取余；除零 ⇒ 被除数（零扩展 = 原值）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a, b = m.get("rd", insn["rdhc"]), m.get("rd", insn["rdhd"])
    m.set("rd", dst, a if b == 0 else a % b)


@sem("rem.so_orrr_rd")
def _op_rem_so(m, insn):
    # SimRISC-04 §1.4：有符号取余（余数符号 = 被除数）；除零 ⇒ 被除数，INT64_MIN%-1 ⇒ 0。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a, b = m.get("rd", insn["rdhc"]), m.get("rd", insn["rdhd"])
    if b == 0:
        m.set("rd", dst, a)
    elif a == 0x8000_0000_0000_0000 and b == MASK64:
        m.set("rd", dst, 0)
    else:
        sa, sb = _sext(a, 64), _sext(b, 64)
        r = abs(sa) % abs(sb)
        m.set("rd", dst, (-r if sa < 0 else r) & MASK64)


@sem("or.o_orrr_rd")
def _op_or_o(m, insn):
    # SimRISC-04 §2.1：64 位逐位或（全 64 位参与）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, m.get("rd", insn["rdhc"]) | m.get("rd", insn["rdhd"]))


@sem("xor.o_orrr_rd")
def _op_xor_o(m, insn):
    # SimRISC-04 §2.1：64 位逐位异或（全 64 位参与）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, m.get("rd", insn["rdhc"]) ^ m.get("rd", insn["rdhd"]))


@sem("xnor.o_orrr_rd")
def _op_xnor_o(m, insn):
    # SimRISC-04 §2.1：64 位逐位同或 = 异或取反（源为 rd0 时即另一操作数取反）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, ~(m.get("rd", insn["rdhc"]) ^ m.get("rd", insn["rdhd"]))
          & MASK64)


@sem("shr.uo_orrr_rd")
def _op_shr_uo_orrr(m, insn):
    # SimRISC-04 §2.2：64 位逻辑右移，移位量 = rdHD[5:0]（0..63 全合法）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    sh = m.get("rd", insn["rdhd"]) & 0x3F
    m.set("rd", dst, m.get("rd", insn["rdhc"]) >> sh)


@sem("shr.so_orri_rd")
def _op_shr_so_orri(m, insn):
    # SimRISC-04 §2.2：64 位算术右移，高位补符号位，移位量 = immu6。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, (_sext(m.get("rd", insn["rdhc"]), 64) >> insn["immu6"])
          & MASK64)


@sem("shr.so_orrr_rd")
def _op_shr_so_orrr(m, insn):
    # SimRISC-04 §2.2：64 位算术右移，移位量 = rdHD[5:0]（0..63 全合法）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    sh = m.get("rd", insn["rdhd"]) & 0x3F
    m.set("rd", dst, (_sext(m.get("rd", insn["rdhc"]), 64) >> sh) & MASK64)


def _rol(x, n):
    """SimRISC-04 §2.2.2：(x << n) | (x >> ((64 - n) & 63))；n = 0 时为 x 本身。"""
    return ((x << n) | (x >> ((64 - n) & 63))) & MASK64


@sem("rol.o_orri_rd")
def _op_rol_orri(m, insn):
    # SimRISC-04 §2.2：64 位循环左移，旋转量 = immu6（0..63 全合法）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, _rol(m.get("rd", insn["rdhc"]), insn["immu6"]))


@sem("rol.o_orrr_rd")
def _op_rol_orrr(m, insn):
    # SimRISC-04 §2.2：64 位循环左移，旋转量 = rdHD[5:0]（天然 = n mod 64）。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    n = m.get("rd", insn["rdhd"]) & 0x3F
    m.set("rd", dst, _rol(m.get("rd", insn["rdhc"]), n))


@sem("rev.o_orri_rd")
def _op_rev(m, insn):
    # SimRISC-04 §2.2.1：k 须 one-hot（immu6 ∈ 1..63 且 2 的幂，否则 ILLI）；
    # 把 64 位切成 64/k 个 k 位单元，反转单元顺序（单元内位序不变）。
    dst = insn["rdhb"]
    k = insn["immu6"]
    if dst == 0 or k == 0 or (k & (k - 1)) != 0:
        raise Fault("Illegal")
    n_units = 64 // k
    x = m.get("rd", insn["rdhc"])
    out = 0
    for i in range(64):
        unit, off = divmod(i, k)
        pos = (n_units - 1 - unit) * k + off
        if (x >> i) & 1:
            out |= 1 << pos
    m.set("rd", dst, out)


def _ext_sign(src, hd):
    """SimRISC-04 §2：复制 src[hd:0]、其余位补 src[hd]（符号扩展，hd=63 ⇒ 原值）。"""
    mask = MASK64 >> (63 - hd)
    low = src & mask
    return (low | ~mask) & MASK64 if (src >> hd) & 1 else low


@sem("ext.so_orri_rd")
def _op_ext_so_orri(m, insn):
    # SimRISC-04 §2：hd = immu6，复制源 [hd:0]、其余位符号扩展。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rd", dst, _ext_sign(m.get("rd", insn["rdhc"]), insn["immu6"]))


@sem("ext.so_orrr_rd")
def _op_ext_so_orrr(m, insn):
    # SimRISC-04 §2：hd = rdHD[5:0]（更高位忽略、不触发异常），其余同上。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    hd = m.get("rd", insn["rdhd"]) & 0x3F
    m.set("rd", dst, _ext_sign(m.get("rd", insn["rdhc"]), hd))


@sem("ext.uo_orrr_rd")
def _op_ext_uo_orrr(m, insn):
    # SimRISC-04 §2：hd = rdHD[5:0]，复制源 [hd:0]、其余位零扩展。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    hd = m.get("rd", insn["rdhd"]) & 0x3F
    mask = MASK64 >> (63 - hd)
    m.set("rd", dst, m.get("rd", insn["rdhc"]) & mask)


@sem("cttz_orri_rd")
def _op_cttz(m, insn):
    # SimRISC-12 §3：有效位 rdHC[hd:0] 内从 bit 0 向上数末尾零；全 0 ⇒ hd + 1。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    hi = insn["immu6"]
    src = m.get("rd", insn["rdhc"])
    n = 0
    for bit in range(0, hi + 1):
        if (src >> bit) & 1:
            break
        n += 1
    m.set("rd", dst, n)


@sem("ctpop_orri_rd")
def _op_ctpop(m, insn):
    # SimRISC-12 §3：有效位 rdHC[hd:0] 内 1 的个数；全 0 ⇒ 0。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    hi = insn["immu6"]
    src = m.get("rd", insn["rdhc"]) & ((1 << (hi + 1)) - 1)
    m.set("rd", dst, bin(src).count("1"))


# --- 08/09/10 窄位宽 ALU（SimRISC-08/09/10；m17-idl-008） ------------------
# 语义逐条取自 `idl/SimRISC-08.idl`/`09`/`10` 对应 `# id:` 段；宽度以 `Bits<N>`
# 声明与 `contracts/opcodes.yaml` 字段位域为准（宽度见语言规范册 §1.1；正文已明示「结果宽 =
# 操作数最大宽、高半丢弃」的按正文执行，不按 UDB/RISC-V 补全）。
# orri/orrr 两种形式共用一条实现路径，仅「移位量来源」不同。
_NARROW_MASK = {8: 0xFF, 16: 0xFFFF, 32: 0xFFFF_FFFF}


def _narrow_dst(insn):
    # 附录 B dst_rd0：目的 rdHB = rd0 ⇒ ILLI。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    return dst


def _narrow_src(m, insn, bits):
    # 源取低 bits 位；rd0 读出 0（先读后写：两源在任何写回之前捕获）。
    mask = _NARROW_MASK[bits]
    return (m.get("rd", insn["rdhc"]) & mask,
            m.get("rd", insn["rdhd"]) & mask)


def _narrow_ext(value, bits, signed):
    # .s 变体按 bit(bits−1) 符号扩展到 64 位；.u 变体零扩展。
    return _sext(value, bits) & MASK64 if signed else value & _NARROW_MASK[bits]


def _narrow_addsub(m, insn, bits, signed, sub):
    # SimRISC-08 §1.1 / 09 §1.1 / 10 §1.1：按 size 运算，溢出/借位静默丢弃。
    dst = _narrow_dst(insn)
    a, b = _narrow_src(m, insn, bits)
    r = (a - b if sub else a + b) & _NARROW_MASK[bits]
    m.set("rd", dst, _narrow_ext(r, bits, signed))


def _narrow_cmp(m, insn, bits, signed):
    # SimRISC-08 §1.2 / 09 §1.2 / 10 §1.2：结果 −1/0/+1 写满 64 位。
    dst = _narrow_dst(insn)
    a, b = _narrow_src(m, insn, bits)
    if signed:
        a, b = _sext(a, bits), _sext(b, bits)
    m.set("rd", dst, MASK64 if a < b else (0 if a == b else 1))


def _narrow_mul(m, insn, bits, signed):
    # SimRISC-08 §1.3 / 09 §1.3 / 10 §1.3：积只保留低 bits 位，再按 .s/.u 扩展。
    dst = _narrow_dst(insn)
    a, b = _narrow_src(m, insn, bits)
    r = (a * b) & _NARROW_MASK[bits]
    m.set("rd", dst, _narrow_ext(r, bits, signed))


def _narrow_div(m, insn, bits, signed):
    # SimRISC-08/09/10 §1.3 + SimRISC-04 §1.4 定值表：
    # 除零 .u ⇒ 全 1（低位宽全 1）；.s ⇒ −1，INT_MIN ÷ −1 ⇒ INT_MIN；均不抛异常。
    dst = _narrow_dst(insn)
    mask = _NARROW_MASK[bits]
    a, b = _narrow_src(m, insn, bits)
    if b == 0:
        m.set("rd", dst, MASK64 if signed else mask)
        return
    if signed and a == 1 << (bits - 1) and b == mask:
        m.set("rd", dst, _sext(a, bits) & MASK64)
        return
    if signed:
        sa, sb = _sext(a, bits), _sext(b, bits)
        q = abs(sa) // abs(sb)              # 向零截断
        r = -q if (sa < 0) != (sb < 0) else q
    else:
        r = a // b
    m.set("rd", dst, _narrow_ext(r & mask, bits, signed))


def _narrow_rem(m, insn, bits, signed):
    # 除零 .u ⇒ 被除数（零扩展）；.s ⇒ 被除数（符号扩展），INT_MIN % −1 ⇒ 0；
    # 其余向零截断，余数符号 = 被除数符号（C99）。
    dst = _narrow_dst(insn)
    mask = _NARROW_MASK[bits]
    a, b = _narrow_src(m, insn, bits)
    if b == 0:
        m.set("rd", dst, _narrow_ext(a, bits, signed))
        return
    if signed and a == 1 << (bits - 1) and b == mask:
        m.set("rd", dst, 0)
        return
    if signed:
        sa, sb = _sext(a, bits), _sext(b, bits)
        r = abs(sa) % abs(sb)
        if sa < 0:
            r = -r
    else:
        r = a % b
    m.set("rd", dst, _narrow_ext(r & mask, bits, signed))


def _narrow_shift(m, insn, bits, kind):
    # SimRISC-08 §2 / 09 §2 / 10 §2：orri 立即数（immu6 > N ⇒ ILLI）与 orrr
    # 寄存器（取 rdHD 低 log2(bits) 位，高位忽略、不抛 ILLI）共用本路径。
    dst = _narrow_dst(insn)
    mask = _NARROW_MASK[bits]
    if "immu6" in insn.fields:
        sh = insn["immu6"]
        if sh > bits - 1:                  # N = size − 1；immu6 高位为 SBZ
            raise Fault("Illegal")
    else:
        sh = m.get("rd", insn["rdhd"]) & (bits - 1)
    v = m.get("rd", insn["rdhc"]) & mask
    if kind == "shl":
        m.set("rd", dst, (v << sh) & mask)
    elif kind == "shr.u":
        m.set("rd", dst, v >> sh)
    else:  # shr.s：块内算术右移，目的高半同样符号扩展 bit(bits−1)
        m.set("rd", dst, _narrow_ext((_sext(v, bits) >> sh) & mask,
                                     bits, True))


def _narrow_rol(m, insn, bits):
    # SimRISC-08 §2.2 / 09 §2.2 / 10 §2.2：块内循环左移，只一个方向；
    # dup 右移 bits−shamt 取低 bits（shamt = 0 时右移量 = bits，不越界）。
    dst = _narrow_dst(insn)
    mask = _NARROW_MASK[bits]
    if "immu6" in insn.fields:
        sh = insn["immu6"]
        if sh > bits - 1:                  # N = size − 1；immu6 高位为 SBZ
            raise Fault("Illegal")
    else:
        sh = m.get("rd", insn["rdhd"]) & (bits - 1)
    v = m.get("rd", insn["rdhc"]) & mask
    dup = v | (v << bits)
    m.set("rd", dst, (dup >> (bits - sh)) & mask)


def _rev_units(x, block, unit):
    """64 位源按 block 位分块，块内按 unit 位反转单元顺序（单元内位序不变）。"""
    out = 0
    per_block = block // unit
    for base in range(0, 64, block):
        for i in range(block):
            unit_no, off = divmod(i, unit)
            pos = base + (per_block - 1 - unit_no) * unit + off
            if (x >> (base + i)) & 1:
                out |= 1 << pos
    return out


def _narrow_rev(m, insn, block, legal):
    # SimRISC-08 §2.1 / 09 §2.1 / 10 §2.1：k 须 one-hot 且 k < S（否则 ILLI）；
    # 各块同法处理（不是 64 位整体反序）。
    dst = _narrow_dst(insn)
    k = insn["immu6"]
    if k not in legal:
        raise Fault("Illegal")
    m.set("rd", dst, _rev_units(m.get("rd", insn["rdhc"]), block, k))


def _sem_params(ids, fn, **kw):
    """按族参数化注册：同一实现路径，仅宽度/符号/形式不同（重复注册仍报错）。"""
    def op(m, insn):
        fn(m, insn, **kw)
    for op_id in ids:
        if op_id in SEMANTICS:
            raise ExecError("duplicate semantics for %s" % op_id)
        SEMANTICS[op_id] = op
    return op


# 08-arith-logic-tetra（32 位；add.st 已在上面单独实现）
_sem_params(("add.ut_orrr_rd",), _narrow_addsub, bits=32, signed=False, sub=False)
_sem_params(("sub.ut_orrr_rd",), _narrow_addsub, bits=32, signed=False, sub=True)
_sem_params(("sub.st_orrr_rd",), _narrow_addsub, bits=32, signed=True, sub=True)
_sem_params(("cmp.ut_orrr_rd",), _narrow_cmp, bits=32, signed=False)
_sem_params(("cmp.st_orrr_rd",), _narrow_cmp, bits=32, signed=True)
_sem_params(("mul.ut_orrr_rd",), _narrow_mul, bits=32, signed=False)
_sem_params(("mul.st_orrr_rd",), _narrow_mul, bits=32, signed=True)
_sem_params(("div.ut_orrr_rd",), _narrow_div, bits=32, signed=False)
_sem_params(("div.st_orrr_rd",), _narrow_div, bits=32, signed=True)
_sem_params(("rem.ut_orrr_rd",), _narrow_rem, bits=32, signed=False)
_sem_params(("rem.st_orrr_rd",), _narrow_rem, bits=32, signed=True)
_sem_params(("shl.t_orri_rd", "shl.t_orrr_rd"), _narrow_shift, bits=32, kind="shl")
_sem_params(("shr.ut_orri_rd", "shr.ut_orrr_rd"), _narrow_shift, bits=32,
            kind="shr.u")
_sem_params(("shr.st_orri_rd", "shr.st_orrr_rd"), _narrow_shift, bits=32,
            kind="shr.s")
_sem_params(("rol.t_orri_rd", "rol.t_orrr_rd"), _narrow_rol, bits=32)
_sem_params(("rev.t_orri_rd",), _narrow_rev, block=32, legal=(1, 2, 4, 8, 16))

# 09-arith-logic-wyde（16 位）
_sem_params(("add.sw_orrr_rd",), _narrow_addsub, bits=16, signed=True, sub=False)
_sem_params(("add.uw_orrr_rd",), _narrow_addsub, bits=16, signed=False, sub=False)
_sem_params(("sub.sw_orrr_rd",), _narrow_addsub, bits=16, signed=True, sub=True)
_sem_params(("sub.uw_orrr_rd",), _narrow_addsub, bits=16, signed=False, sub=True)
_sem_params(("cmp.sw_orrr_rd",), _narrow_cmp, bits=16, signed=True)
_sem_params(("cmp.uw_orrr_rd",), _narrow_cmp, bits=16, signed=False)
_sem_params(("mul.sw_orrr_rd",), _narrow_mul, bits=16, signed=True)
_sem_params(("mul.uw_orrr_rd",), _narrow_mul, bits=16, signed=False)
_sem_params(("div.sw_orrr_rd",), _narrow_div, bits=16, signed=True)
_sem_params(("div.uw_orrr_rd",), _narrow_div, bits=16, signed=False)
_sem_params(("rem.sw_orrr_rd",), _narrow_rem, bits=16, signed=True)
_sem_params(("rem.uw_orrr_rd",), _narrow_rem, bits=16, signed=False)
_sem_params(("shl.w_orri_rd", "shl.w_orrr_rd"), _narrow_shift, bits=16, kind="shl")
_sem_params(("shr.uw_orri_rd", "shr.uw_orrr_rd"), _narrow_shift, bits=16,
            kind="shr.u")
_sem_params(("shr.sw_orri_rd", "shr.sw_orrr_rd"), _narrow_shift, bits=16,
            kind="shr.s")
_sem_params(("rol.w_orri_rd", "rol.w_orrr_rd"), _narrow_rol, bits=16)
_sem_params(("rev.w_orri_rd",), _narrow_rev, block=16, legal=(1, 2, 4, 8))

# 10-arith-logic-byte（8 位；add.ub 已在上面单独实现）
_sem_params(("add.sb_orrr_rd",), _narrow_addsub, bits=8, signed=True, sub=False)
_sem_params(("sub.sb_orrr_rd",), _narrow_addsub, bits=8, signed=True, sub=True)
_sem_params(("sub.ub_orrr_rd",), _narrow_addsub, bits=8, signed=False, sub=True)
_sem_params(("cmp.sb_orrr_rd",), _narrow_cmp, bits=8, signed=True)
_sem_params(("cmp.ub_orrr_rd",), _narrow_cmp, bits=8, signed=False)
_sem_params(("mul.sb_orrr_rd",), _narrow_mul, bits=8, signed=True)
_sem_params(("mul.ub_orrr_rd",), _narrow_mul, bits=8, signed=False)
_sem_params(("div.sb_orrr_rd",), _narrow_div, bits=8, signed=True)
_sem_params(("div.ub_orrr_rd",), _narrow_div, bits=8, signed=False)
_sem_params(("rem.sb_orrr_rd",), _narrow_rem, bits=8, signed=True)
_sem_params(("rem.ub_orrr_rd",), _narrow_rem, bits=8, signed=False)
_sem_params(("shl.b_orri_rd", "shl.b_orrr_rd"), _narrow_shift, bits=8, kind="shl")
_sem_params(("shr.ub_orri_rd", "shr.ub_orrr_rd"), _narrow_shift, bits=8,
            kind="shr.u")
_sem_params(("shr.sb_orri_rd", "shr.sb_orrr_rd"), _narrow_shift, bits=8,
            kind="shr.s")
_sem_params(("rol.b_orri_rd", "rol.b_orrr_rd"), _narrow_rol, bits=8)
_sem_params(("rev.b_orri_rd",), _narrow_rev, block=8, legal=(1, 2, 4))


# --- 04（跨册依赖）/ 05-arith-addr ---------------------------------------
@sem("ext.uo_orri_rd")
def _op_ext_uo_orri(m, insn):
    # SimRISC-04 §2：复制源 [immu6:0]、其余位零扩展（immu6 = 63 ⇒ 写满 64 位）。
    # 跨册依赖（04 册正文语义归 `m17-idl-007`，此处只补 006 载体必需的这一条）：
    # 01 册 `ld.t`/`ldm.t` 的载体重用 `ext.uo rd, rd, 31` 读回低 32 位
    # （tests/inst/01-load-store/ld.t_rrii_rf.S 的 TEST_LD_RF_LO32）；
    # 不补这条，01 册这 2 个镜像无法进主清单。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    mask = MASK64 >> (63 - insn["immu6"])
    m.set("rd", dst, m.get("rd", insn["rdhc"]) & mask)


@sem("aip.si_riii_rb")
def _op_aip_si(m, insn):
    dst = insn["rbha"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rb", dst, m.ip + (insn["imms18"] << 12))


@sem("sub.o_orrr_bbd")
def _op_sub_o_bbd(m, insn):
    # SimRISC-05：rb[HB] = rb[HC] - rd[HD]，全 64 位补码减法（不做地址截断）。
    dst = insn["rbhb"]
    if dst == 0:
        raise Fault("Illegal")
    m.set("rb", dst, (m.get("rb", insn["rbhc"])
                      - m.get("rd", insn["rdhd"])) & MASK64)


@sem("cmp.uo_orrr_dbb")
def _op_cmp_uo_dbb(m, insn):
    # SimRISC-05：整 64 位无符号比较 → 小于 -1 / 等于 0 / 大于 1，写满 64 位。
    dst = insn["rdhb"]
    if dst == 0:
        raise Fault("Illegal")
    a, b = m.get("rb", insn["rbhc"]), m.get("rb", insn["rbhd"])
    m.set("rd", dst, MASK64 if a < b else (0 if a == b else 1))


# --- 01-load-store -------------------------------------------------------
# rrii/rrri 的 ha 字段随目的寄存器组改名（rdha/rbha/rfha/raha，contracts/opcodes.yaml）。
_BANK_HA = {"rd": "rdha", "rb": "rbha", "rf": "rfha", "ra": "raha"}
_LD_WIDTH = {mn + suf: bits
             for mn in ("ld", "ldm")
             for suf, bits in ((".sb", 8), (".sw", 16), (".st", 32),
                               (".ub", 8), (".uw", 16), (".ut", 32))}
_ST_WIDTH = {mn + suf: bits
             for mn in ("st", "stm")
             for suf, bits in ((".b", 8), (".w", 16), (".t", 32))}


def _narrow_write(m, bank, idx, bits, value):
    """窄写：只写目的的低 bits 位、高位保持原值（SimRISC-00 §2.3）。

    `ld.t`/`ldm.t` 的 rf 目的只写低 32 位（SimRISC-01 §4）；ra0/rf0 的只读位由
    `Machine.set` 的写语义再收一次（ra0 只写 [53:0]、rf0 只写 [33:32]/[4:0]）。
    """
    mask = (1 << bits) - 1
    m.set(bank, idx, (m.get(bank, idx) & ~mask) | (value & mask))


def _load_one(m, insn, bank, bits, signed, narrow=False):
    """单元素装载（SimRISC-01 §1–§4）：rd/rb 目的 0 号 ⇒ ILLI；对齐按宽度。"""
    dst = insn[_BANK_HA[bank]]
    if bank in ("rd", "rb") and dst == 0:
        raise Fault("Illegal")
    ea = (m.get("rb", insn["rbhb"]) + insn["imms12"]) & MASK48
    if not is_naturally_aligned(bits, ea):
        raise Fault("Malign", info=ea)
    value = m.mem.read_memory(bits, ea)
    if signed and bits < 64:
        value = _sext(value, bits)
    if narrow:
        _narrow_write(m, bank, dst, bits, value)
    else:
        m.set(bank, dst, value)


def _store_one(m, insn, bank, bits):
    """单元素存储（SimRISC-01 §1–§4）：st 允许 0 号作源（读出 0/IP/ra0 位型）。"""
    src = insn[_BANK_HA[bank]]
    ea = (m.get("rb", insn["rbhb"]) + insn["imms12"]) & MASK48
    if not is_naturally_aligned(bits, ea):
        raise Fault("Malign", info=ea)
    m.mem.write_memory(bits, ea, m.get(bank, src))


@sem("ld.o_rrii_rd", "ld.o_rrii_rb", "ld.o_rrii_ra", "ld.o_rrii_rf")
def _op_ld_o(m, insn):
    _load_one(m, insn, insn.id[-2:], 64, False)


@sem("ld.sb_rrii_rd", "ld.sw_rrii_rd", "ld.st_rrii_rd")
def _op_ld_signed(m, insn):
    # SimRISC-01 §1：.sb/.sw/.st 读 8/16/32 位后符号扩展写满 64 位。
    _load_one(m, insn, "rd", _LD_WIDTH[insn.id.split("_")[0]], True)


@sem("ld.ub_rrii_rd", "ld.uw_rrii_rd", "ld.ut_rrii_rd")
def _op_ld_unsigned(m, insn):
    # SimRISC-01 §1：.ub/.uw/.ut 零扩展（.ub 无对齐要求，.uw/.ut 需 2/4 字节对齐）。
    _load_one(m, insn, "rd", _LD_WIDTH[insn.id.split("_")[0]], False)


@sem("ld.t_rrii_rf")
def _op_ld_t_rf(m, insn):
    # SimRISC-01 §4：单精装载只写 rf 低 32 位、高 32 位保持原值；rf0 可作目的。
    _load_one(m, insn, "rf", 32, False, narrow=True)


@sem("st.o_rrii_rd", "st.o_rrii_rb", "st.o_rrii_rf", "st.o_rrii_ra")
def _op_st_o(m, insn):
    _store_one(m, insn, insn.id[-2:], 64)


@sem("st.b_rrii_rd", "st.w_rrii_rd", "st.t_rrii_rd")
def _op_st_narrow(m, insn):
    # SimRISC-01 §1：只把源寄存器的低 8/16/32 位写入存储器。
    _store_one(m, insn, "rd", _ST_WIDTH[insn.id.split("_")[0]])


@sem("st.t_rrii_rf")
def _op_st_t_rf(m, insn):
    # SimRISC-01 §4：单精存储取 rf 源的低 32 位。
    _store_one(m, insn, "rf", 32)


def _ldm(m, insn, bank, bits, signed, idx_overlap=False, base_overlap=False):
    """多元素装载（SimRISC-01 §1–§4）：静态检查全部先于任何元素（精确异常）。"""
    dst, count = insn[_BANK_HA[bank]], insn["immu6"]
    if bank in ("rd", "rb") and dst == 0:
        raise Fault("Illegal")
    if count == 0 or dst + count > 64:
        raise Fault("Illegal")
    # 索引/基址落入同组传送范围 ⇒ ILLI（跨组结构上不可能 ⇒ 不判）。
    if idx_overlap and dst <= insn["rdhc"] < dst + count:
        raise Fault("Illegal")
    if base_overlap and dst <= insn["rbhb"] < dst + count:
        raise Fault("Illegal")
    ea = (m.get("rb", insn["rbhb"]) + m.get("rd", insn["rdhc"])) & MASK48
    if not is_naturally_aligned(bits, ea):
        raise Fault("Malign", info=ea)
    step = bits // 8
    for k in range(count):
        value = m.mem.read_memory(bits, ea)
        if signed and bits < 64:
            value = _sext(value, bits)
        if bank == "rf" and bits == 32:
            _narrow_write(m, "rf", dst + k, 32, value)
        else:
            m.set(bank, dst + k, value)
        ea = (ea + step) & MASK48


@sem("ldm.o_rrri_rd")
def _op_ldm_o_rd(m, insn):
    _ldm(m, insn, "rd", 64, False, idx_overlap=True)


@sem("ldm.o_rrri_rb")
def _op_ldm_o_rb(m, insn):
    _ldm(m, insn, "rb", 64, False, base_overlap=True)


@sem("ldm.o_rrri_ra")
def _op_ldm_o_ra(m, insn):
    _ldm(m, insn, "ra", 64, False)


@sem("ldm.o_rrri_rf")
def _op_ldm_o_rf(m, insn):
    _ldm(m, insn, "rf", 64, False)


@sem("ldm.sb_rrri_rd", "ldm.sw_rrri_rd", "ldm.st_rrri_rd")
def _op_ldm_signed(m, insn):
    _ldm(m, insn, "rd", _LD_WIDTH[insn.id.split("_")[0]], True, idx_overlap=True)


@sem("ldm.ub_rrri_rd", "ldm.uw_rrri_rd", "ldm.ut_rrri_rd")
def _op_ldm_unsigned(m, insn):
    _ldm(m, insn, "rd", _LD_WIDTH[insn.id.split("_")[0]], False, idx_overlap=True)


@sem("ldm.t_rrri_rf")
def _op_ldm_t_rf(m, insn):
    # SimRISC-01 §4：每个元素只写 rf 低 32 位、高 32 位保持；rf0 只写 [4:0]。
    _ldm(m, insn, "rf", 32, False)


def _stm(m, insn, bank, bits):
    """多元素存储（SimRISC-01 §1–§4）：stm 不判 0 号/重叠，只判个数与越界。"""
    src, count = insn[_BANK_HA[bank]], insn["immu6"]
    if count == 0 or src + count > 64:
        raise Fault("Illegal")
    ea = (m.get("rb", insn["rbhb"]) + m.get("rd", insn["rdhc"])) & MASK48
    if not is_naturally_aligned(bits, ea):
        raise Fault("Malign", info=ea)
    step = bits // 8
    for k in range(count):
        m.mem.write_memory(bits, ea, m.get(bank, src + k))
        ea = (ea + step) & MASK48


@sem("stm.o_rrri_rd")
def _op_stm_o_rd(m, insn):
    _stm(m, insn, "rd", 64)


@sem("stm.o_rrri_rb")
def _op_stm_o_rb(m, insn):
    _stm(m, insn, "rb", 64)


@sem("stm.o_rrri_ra")
def _op_stm_o_ra(m, insn):
    _stm(m, insn, "ra", 64)


@sem("stm.o_rrri_rf")
def _op_stm_o_rf(m, insn):
    _stm(m, insn, "rf", 64)


@sem("stm.b_rrri_rd", "stm.w_rrri_rd", "stm.t_rrri_rd")
def _op_stm_narrow(m, insn):
    _stm(m, insn, "rd", _ST_WIDTH[insn.id.split("_")[0]])


@sem("stm.t_rrri_rf")
def _op_stm_t_rf(m, insn):
    _stm(m, insn, "rf", 32)


# --- 02-reg-copy ---------------------------------------------------------
def _block_copy(m, dst_bank, dst, src_bank, src, count,
                overlap=False, dst_zero_allowed=False):
    """SimRISC-02 块复制：静态检查全部先于任何元素（精确异常）。"""
    if not dst_zero_allowed and dst == 0:
        raise Fault("Illegal")
    if count == 0:
        raise Fault("Illegal")
    dst_end, src_end = dst + count, src + count
    if dst_end > 64 or src_end > 64:
        raise Fault("Illegal")
    if overlap and dst < src_end and src < dst_end:
        raise Fault("Illegal")
    for k in range(count):
        m.set(dst_bank, dst + k, m.get(src_bank, src + k))


@sem("rd2rd_orri_rd")
def _op_rd2rd(m, insn):
    _block_copy(m, "rd", insn["rdhb"], "rd", insn["rdhc"], insn["immu6"],
                overlap=True)


@sem("rb2rd_orri_rb")
def _op_rb2rd(m, insn):
    _block_copy(m, "rd", insn["rdhb"], "rb", insn["rbhc"], insn["immu6"])


@sem("rb2rb_orri_rb")
def _op_rb2rb(m, insn):
    # SimRISC-02 §1：同组复制禁任何交集（含完全重合）⇒ mreg_range_overlap。
    _block_copy(m, "rb", insn["rbhb"], "rb", insn["rbhc"], insn["immu6"],
                overlap=True)


@sem("rd2rb_orri_rb")
def _op_rd2rb(m, insn):
    # 跨组复制 ⇒ 源/目的结构上不可能交集，无 mreg_range_overlap 检查。
    _block_copy(m, "rb", insn["rbhb"], "rd", insn["rdhc"], insn["immu6"])


@sem("rf2rd_orri_rf")
def _op_rf2rd(m, insn):
    _block_copy(m, "rd", insn["rdhb"], "rf", insn["rfhc"], insn["immu6"])


@sem("rd2rf_orri_rf")
def _op_rd2rf(m, insn):
    _block_copy(m, "rf", insn["rfhb"], "rd", insn["rdhc"], insn["immu6"],
                dst_zero_allowed=True)


@sem("rf2rf_orri_rf")
def _op_rf2rf(m, insn):
    _block_copy(m, "rf", insn["rfhb"], "rf", insn["rfhc"], insn["immu6"],
                dst_zero_allowed=False, overlap=True)


@sem("ra2rd_orri_ra")
def _op_ra2rd(m, insn):
    _block_copy(m, "rd", insn["rdhb"], "ra", insn["rahc"], insn["immu6"])


@sem("rd2ra_orri_ra")
def _op_rd2ra(m, insn):
    _block_copy(m, "ra", insn["rahb"], "rd", insn["rdhc"], insn["immu6"],
                dst_zero_allowed=True)


@sem("cs.eq_rrrr_rd")
def _op_cs_eq(m, insn):
    dst = insn["rdhc"]
    if dst == 0:
        raise Fault("Illegal")
    if m.get("rd", insn["rdha"]) == m.get("rd", insn["rdhb"]):
        m.set("rd", dst, m.get("rd", insn["rdhd"]))


# SimRISC-02 §2 第一类（有 else）：条件成立 → 目的 = 第二源，否则 = 第三源；
# 条件与两个候选源都在写之前读（「先比较、再赋值」）。
def _cs_select(m, insn, taken, dst_bank, dst_field, then_field, else_field):
    dst = insn[dst_field]
    if dst == 0:
        raise Fault("Illegal")
    src = insn[then_field] if taken else insn[else_field]
    m.set(dst_bank, dst, m.get(dst_bank, src))


def _cs_is_p(v):
    return (v >> 63) == 0 and (v & ((1 << 63) - 1)) != 0


@sem("cs.z_rrrr_rd")
def _op_cs_z_rd(m, insn):
    _cs_select(m, insn, m.get("rd", insn["rdha"]) == 0, "rd",
               "rdhb", "rdhc", "rdhd")


@sem("cs.n_rrrr_rd")
def _op_cs_n_rd(m, insn):
    _cs_select(m, insn, (m.get("rd", insn["rdha"]) >> 63) == 1, "rd",
               "rdhb", "rdhc", "rdhd")


@sem("cs.p_rrrr_rd")
def _op_cs_p_rd(m, insn):
    _cs_select(m, insn, _cs_is_p(m.get("rd", insn["rdha"])), "rd",
               "rdhb", "rdhc", "rdhd")


@sem("cs.z_rrrr_rf")
def _op_cs_z_rf(m, insn):
    _cs_select(m, insn, m.get("rd", insn["rdha"]) == 0, "rf",
               "rfhb", "rfhc", "rfhd")


@sem("cs.n_rrrr_rf")
def _op_cs_n_rf(m, insn):
    _cs_select(m, insn, (m.get("rd", insn["rdha"]) >> 63) == 1, "rf",
               "rfhb", "rfhc", "rfhd")


@sem("cs.p_rrrr_rf")
def _op_cs_p_rf(m, insn):
    _cs_select(m, insn, _cs_is_p(m.get("rd", insn["rdha"])), "rf",
               "rfhb", "rfhc", "rfhd")


@sem("cs.ne_rrrr_rd")
def _op_cs_ne_rd(m, insn):
    # SimRISC-02 §2 第二类（无 else）：目的在第三个操作数，不成立时保持原值。
    dst = insn["rdhc"]
    if dst == 0:
        raise Fault("Illegal")
    if m.get("rd", insn["rdha"]) != m.get("rd", insn["rdhb"]):
        m.set("rd", dst, m.get("rd", insn["rdhd"]))


# --- 06-control-flow -----------------------------------------------------
def _branch(m, insn, taken):
    if taken:
        off = insn["imms18"] << 2 if "imms18" in insn.fields else \
            insn["imms12"] << 2
        m.jump(m.ip + off)


@sem("br.eq_rrii_rd")
def _op_br_eq(m, insn):
    _branch(m, insn, m.get("rd", insn["rdha"]) == m.get("rd", insn["rdhb"]))


@sem("br.ne_rrii_rd")
def _op_br_ne(m, insn):
    _branch(m, insn, m.get("rd", insn["rdha"]) != m.get("rd", insn["rdhb"]))


@sem("br.z_riii_rd", "br.z_riii_rb")
def _op_br_z(m, insn):
    bank = "rb" if insn.id.endswith("_rb") else "rd"
    idx = insn["rbha"] if bank == "rb" else insn["rdha"]
    _branch(m, insn, m.get(bank, idx) == 0)


@sem("br.nz_riii_rd", "br.nz_riii_rb")
def _op_br_nz(m, insn):
    bank = "rb" if insn.id.endswith("_rb") else "rd"
    idx = insn["rbha"] if bank == "rb" else insn["rdha"]
    _branch(m, insn, m.get(bank, idx) != 0)


@sem("br.p_riii_rd")
def _op_br_p(m, insn):
    v = m.get("rd", insn["rdha"])
    _branch(m, insn, (v >> 63) == 0 and (v & ((1 << 63) - 1)) != 0)


@sem("br.n_riii_rd")
def _op_br_n(m, insn):
    _branch(m, insn, (m.get("rd", insn["rdha"]) >> 63) == 1)


@sem("br.nn_riii_rd")
def _op_br_nn(m, insn):
    _branch(m, insn, (m.get("rd", insn["rdha"]) >> 63) == 0)


@sem("br.np_riii_rd")
def _op_br_np(m, insn):
    v = m.get("rd", insn["rdha"])
    _branch(m, insn, (v >> 63) == 1 or v == 0)


@sem("jump_iiii_rb")
def _op_jump_iiii(m, insn):
    m.jump(m.ip + (insn["imms24"] << 2))


@sem("jump_rrii_rb")
def _op_jump_rrii(m, insn):
    m.jump(m.get("rb", insn["rbha"]) + m.get("rd", insn["rdhb"])
           + (insn["imms12"] << 2))


@sem("call_iiii_ra")
def _op_call(m, insn):
    target = m.ip + (insn["imms24"] << 2)
    m.ras_push(m.ip + 4)
    m.jump(target)


@sem("call_rrii_ra")
def _op_call_rrii(m, insn):
    # SimRISC-06 §3：返回地址 = call 自身 + 4（两种形式一致）；目标 = rbHA + rdHB
    # + (SX(imms12) << 2)；rbHA 仅读（为 rb0 时是相对跳转）。
    m.ras_push(m.ip + 4)
    target = (m.get("rb", insn["rbha"]) + m.get("rd", insn["rdhb"])
              + (insn["imms12"] << 2))
    m.jump(target)


@sem("ret_riii_ra")
def _op_ret(m, insn):
    if insn["rdha"] == 0 and insn["imms18"] != 0:
        raise Fault("Illegal")
    target = m.ras_pop()
    m.set("rd", insn["rdha"], insn["imms18"])
    m.jump(target)


# --- 07（本任务只用骨架里的 rf 搬移语义，不做浮点运算） -------------------
# ftsclb 等浮点 operation 不在 m17-idl-003 范围；遇到时显式失败（不静默）。


# --- 11-cfx --------------------------------------------------------------
@sem("cfx2rd_crrr_cfx", "cfx2rc_crrr_cfx")
def _op_cfx2r(m, insn):
    cfxha, cg, rc, rd = (insn["cfxha"], insn["cghb"], insn["rchc"],
                         insn["rdhd"])
    if cfxha in RESERVED_CFX:
        raise Fault("Illegal")
    if cfxha not in IMPLEMENTED_CFX:
        raise Fault("CfxReg")
    cfx = m.cfx[cfxha]
    if m._cfx_perm_denied(cfxha, CG3_REG):    # spec/DADAO-12 §3.4 cg3 rc2：位索引 = 源 cfx
        raise Fault("CfxPerm")                # cause_info = 触发指令地址（step 补，§4.1）
    if insn.id.startswith("cfx2rd"):
        value = cfx.access(cg, rc, False)
    else:
        value = 0
        m.cfx_write(cfxha, cg, rc, m.get("rd", rd))   # 含 timer/pending 硬件副作用
    if insn.id.startswith("cfx2rd"):
        m.set("rd", rd, value)


@sem("trap_ciii_cfx")
def _op_trap(m, insn):
    immu18, cfxha = insn["immu18"], insn["cfxha"]
    if (immu18 >> 8) & 0x3FF == 0x3FF:
        m._semihost(immu18)               # semihosting 短路（contract §1）
        return
    if cfxha in RESERVED_CFX:
        raise Fault("Illegal")
    if cfxha not in IMPLEMENTED_CFX:
        # spec/Kaiwu §3：已分配但本 profile 未实现的 cfx（Tiny：cfx0/1/2/4/5/32…）
        # ⇒ ILLI（与 cfx2rd/cfx2rc 的 CFXREG 不同，见 trap_ciii 用例头）。
        raise Fault("Illegal")
    if m._cfx_perm_denied(cfxha, CG3_TRAP):   # 位索引 = 源 cfx（spec/DADAO-12 §5.2）
        raise Fault("CfxPerm")
    m.take_exception("CfxTrap", m.ip, m.cur_word, target=cfxha)


@sem("escape_ciii_cfx")
def _op_escape(m, insn):
    # spec/SimRISC-11 §3（编码层）：`escape cfxHA` 只提供 cfxha，`imms18` 必须为 0
    # （SBZ）——非 0 ⇒ ILLI；保留 cfxha ⇒ ILLI。两者都先于目标判定与任何状态切换
    # （spec/DADAO-12 §5.1 步骤 0）。旧 `+0/+4` 偏移与 `cg9` 帧选择位作废。
    if insn["imms18"] != 0:
        raise Fault("Illegal")
    cfxha = insn["cfxha"]
    if cfxha in RESERVED_CFX:
        raise Fault("Illegal")
    m.escape(cfxha)


@sem("fence_ciii_cfx")
def _op_fence(m, insn):
    # SimRISC-11 §5：hb = immu18[17:12] 为 SBZ，非零 ⇒ ILLI；保留 cfx ⇒ ILLI；
    # 合法屏障只约束顺序/可见性（Tiny 单 hart、无 DMA/异步观测点 ⇒ IDL v0 不建模），
    # 不改架构状态的 no-op（零掩码是合法 no-op）。
    if (insn["immu18"] >> 12) & 0x3F:
        raise Fault("Illegal")
    if insn["cfxha"] in RESERVED_CFX:
        raise Fault("Illegal")


# --- 12-misc：原子 lr/sc（SimRISC-12 §1）/ 空转 swym（§2）-----------------
# 宽度由助记符的数据宽度后缀给出（.b=8 / .w=16 / .t=32 / .o=64，contract-isa §2.5）。
_ATOMIC_BITS = {"b": 8, "w": 16, "t": 32, "o": 64}


def _atomic_width(insn):
    return _ATOMIC_BITS[insn.mnemonic.split(".")[1]]


def _lr(m, insn):
    """lr（SimRISC-12 §1.1）：先读内存，再清/设保留标记，最后写 rd。"""
    if insn["rdhb"] != 0:                 # hb 为 SBZ，非零 ⇒ ILLI（encode_sbz）
        raise Fault("Illegal")
    bits = _atomic_width(insn)
    ea = m.get("rb", insn["rbhd"]) & MASK48
    if not is_naturally_aligned(bits, ea):
        raise Fault("Malign", info=ea)
    value = m.mem.read_memory(bits, ea)    # 先读：故障时不得改动任何架构状态
    m.reservation_clear_all()              # 本 hart 执行另一条 lr ⇒ 清既有标记
    m.reservation_set(ea, bits)            # 键 = 精确地址 + 访问宽度
    if bits == 64:
        m.set("rd", insn["rdhc"], value)
    else:
        # 窄读只写低 8/16/32 位、rd 高位保持原值（W27：既不零扩展也不符号扩展）。
        _narrow_write(m, "rd", insn["rdhc"], bits, value)


_LR_IDS = (
    "lr.o.nn_orrr_rd", "lr.o.an_orrr_rd", "lr.o.ar_orrr_rd",
    "lr.t.nn_orrr_rd", "lr.t.an_orrr_rd", "lr.t.ar_orrr_rd",
    "lr.w.nn_orrr_rd", "lr.w.an_orrr_rd", "lr.w.ar_orrr_rd",
    "lr.b.nn_orrr_rd", "lr.b.an_orrr_rd", "lr.b.ar_orrr_rd",
)


@sem(*_LR_IDS)
def _op_lr(m, insn):
    _lr(m, insn)


def _sc(m, insn):
    """sc（SimRISC-12 §1.1）：原子「查标记 → 条件写 → 清标记」；0 = 成功、1 = 失败。"""
    dst = insn["rdhb"]                    # 成功/失败结果不可丢弃 ⇒ rd0 为非法
    if dst == 0:
        raise Fault("Illegal")
    bits = _atomic_width(insn)
    ea = m.get("rb", insn["rbhd"]) & MASK48
    if not is_naturally_aligned(bits, ea):
        raise Fault("Malign", info=ea)
    # 源值先读（rdHB == rdHC 时「源先读、结果后写」），成败都返回给 rdHB。
    ok = m.store_conditional(ea, bits, m.get("rd", insn["rdhc"]))
    m.set("rd", dst, ok)


_SC_IDS = (
    "sc.o.nn_orrr_rd", "sc.o.nr_orrr_rd", "sc.o.ar_orrr_rd",
    "sc.t.nn_orrr_rd", "sc.t.nr_orrr_rd", "sc.t.ar_orrr_rd",
    "sc.w.nn_orrr_rd", "sc.w.nr_orrr_rd", "sc.w.ar_orrr_rd",
    "sc.b.nn_orrr_rd", "sc.b.nr_orrr_rd", "sc.b.ar_orrr_rd",
)


@sem(*_SC_IDS)
def _op_sc(m, insn):
    _sc(m, insn)


@sem("swym_oiii_imm")
def _op_swym(m, insn):
    """swym（SimRISC-12 §2）：除 IP 自增外无任何架构副作用。

    `immu18` 只是硬件时延参数（实现时序），散文本节未赋予它访存序/屏障语义，
    故 IDL v0 只做 no-op（IP 自增属取指模型，`Machine.step` 负责）。
    """


# ---------------------------------------------------------------------------
# ELF 加载（复用 machine_profile 的运行布局）
# ---------------------------------------------------------------------------
class Elf:
    def __init__(self, path):
        data = Path(path).read_bytes()
        if len(data) < 64 or data[:4] != b"\x7fELF":
            raise ExecError("not an ELF: %s" % path)
        if data[4] != 2:
            raise ExecError("only ELF64 supported (EI_CLASS=%d)" % data[4])
        if data[5] != 2:
            raise ExecError("only big-endian ELF supported (EI_DATA=%d)"
                            % data[5])
        self.data = data
        (self.e_entry,) = struct.unpack_from(">Q", data, 24)
        (self.e_phoff,) = struct.unpack_from(">Q", data, 32)
        (self.e_phentsize,) = struct.unpack_from(">H", data, 54)
        (self.e_phnum,) = struct.unpack_from(">H", data, 56)
        self.segments = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            p_type, = struct.unpack_from(">I", data, off)
            if p_type != 1:
                continue
            p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from(
                ">QQQQQ", data, off + 8)
            self.segments.append({
                "offset": p_offset, "vaddr": p_vaddr, "paddr": p_paddr,
                "filesz": p_filesz, "memsz": p_memsz,
                "blob": data[p_offset:p_offset + p_filesz],
            })


def new_machine(profile_name="tiny", bootrom=None, elf=None):
    """按 machine_profile 的运行布局造一台 Tiny/Vast 机器。"""
    mp = load_machine_profiles()
    profile = mp.load(profile_name).to_dict()
    profile["hmon_base"] = mp.HMON_BASE      # 机器真源只在 machine_profile.py
    mem = Memory()
    mem.add_region("ram", profile["ram_base"], profile["ram_size"])
    mem.add_region("bootrom", profile["bootrom_base"],
                   profile["bootrom_size"], writable=False)
    mem.add_region("hmon", profile["hmon_base"], 0x1_0000)
    if bootrom is not None:
        _install_bootrom(mem, Path(bootrom), profile)
    machine = Machine(profile, mem)
    return machine


def _install_bootrom(mem, image_path, profile):
    """按 spec/Kaiwu §6.1/§6.2 把 Tiny BootROM 的 hmon 段装进 hmon SRAM。"""
    image = image_path.read_bytes()
    if len(image) != profile["bootrom_size"]:
        raise ExecError("bootrom image is %d bytes, profile expects %d"
                        % (len(image), profile["bootrom_size"]))
    mem.load(profile["bootrom_base"], image, force=True)
    table_off = 0xE000
    magic, version, count = struct.unpack_from(">IHH", image, table_off)
    if magic != 0x44424F54 or version != 1:
        raise ExecError("bootrom image index table: bad magic/version")
    for i in range(count):
        ent = table_off + 16 + i * 32
        etype, flags, offset, size, _reserved = struct.unpack_from(
            ">IIQQQ", image, ent)
        if etype != 1:
            raise ExecError("bootrom table entry %d: type %d != flat"
                            % (i, etype))
        if offset % 8 or size % 8:
            raise ExecError("bootrom table entry %d: unaligned offset/size" % i)
        if size > 0x2000:
            raise ExecError("bootrom table entry %d: segment > 8 KiB" % i)
        mem.load(mem.regions["hmon"][0], image[offset:offset + size])


def load_elf(machine, elf_path):
    elf = Elf(elf_path)
    for seg in elf.segments:
        # 应用镜像只允许落在 RAM（spec/Kaiwu §6.2 装载检查）；hmon/BootROM 段由固件负责。
        name, _off = machine.mem.region_of(seg["paddr"], max(seg["memsz"], 1))
        if name != "ram":
            raise ExecError("ELF segment at %#x does not land in RAM"
                            % seg["paddr"])
        machine.mem.load(seg["paddr"], seg["blob"])
        if seg["memsz"] > seg["filesz"]:
            zero = b"\x00" * (seg["memsz"] - seg["filesz"])
            machine.mem.load(seg["paddr"] + seg["filesz"], zero)
    machine.ip = elf.e_entry
    return elf


# --- 07-floating-point：SimRISC-07（m17-idl-013） ---------------------------
# 语义逐条取自 `idl/SimRISC-07.idl` 的 operation 正文；**值 + `rf0[4:0]` 标志**由
# 独立 spec-exact 参考模型 `idl/tools/idl_fp.py` 给出（精确值一次舍入 + IEEE
# 754-2019 §7.4/§7.5 的 OF/UF/NX 判据），本层只做薄封装：
#
#   * 合法性：目的 `rf0`（`dst_rf0`）/ `rd0`（`dst_rd0`）⇒ ILLI；`immu6` 六档
#     one-hot 或 SBZ、`root` 的 n=2、分类窗口 —— 均由本层显式判（不静默通过）；
#   * 舍入方向：`orrr` 族取 `rf0[33:32]`，`orri` 族取 `immu6` 六档（0x20 = 动态）；
#   * 写宽：ft 族只写低 32 位、高 32 位保持；fo 族整 64 位（contract-fp §1）；
#   * 标志：返回的 `rf0[4:0]` 按 IEEE sticky 语义**并入** FCSR（只置位、不清零、
#     不覆盖 SBZ/只读 qNaN 位）。
#
# `idl_fp` 只作被调用方：本任务不改其语义（缺陷另立任务）。
_FP_MODE_RF0 = (_fp.RNE, _fp.RTZ, _fp.RDN, _fp.RUP)   # rf0[33:32]
_FP_FMT = {32: _fp.FT, 64: _fp.FO}
_FP_MASK = {32: 0xFFFF_FFFF, 64: MASK64}


def _fp_src(m, insn, width, field="rfhc"):
    """读浮点源（ft 只取低 32 位；rf0 作源合法）。"""
    return m.get("rf", insn[field]) & _FP_MASK[width]


def _fp_mode(m):
    """S2D1/S1D1/符号等 `orrr` 族：舍入方向取 rf0[33:32] 四档。"""
    return _FP_MODE_RF0[(m.get("rf", 0) >> 32) & 0x3]


def _fp_mode_imm(m, insn):
    """`orri` 族：immu6 六档 one-hot；0x20 = 动态读 rf0[33:32]；其余 ⇒ ILLI。"""
    legal, mode = _fp.mode_from_onehot(insn["immu6"],
                                       (m.get("rf", 0) >> 32) & 0x3)
    if not legal:
        raise Fault("Illegal")
    return mode


def _fp_dst(insn, field):
    """浮点运算目的：rf 组不得为 rf0（dst_rf0），rd 组不得为 rd0（dst_rd0）。"""
    dst = insn[field]
    if dst == 0:
        raise Fault("Illegal")
    return dst


def _fp_set_flags(m, flags):
    """把本次运算的 rf0[4:0] 并入 FCSR（sticky：只置位、不清零；其它位保持）。"""
    if flags:
        m.set("rf", 0, m.get("rf", 0) | flags)


def _fp_write_rf(m, dst, width, value):
    """ft 族只写低 32 位（高 32 位保持）、fo 族整 64 位（contract-fp §1）。"""
    if width == 32:
        _narrow_write(m, "rf", dst, 32, value)
    else:
        m.set("rf", dst, value)


def _fp_arith(m, insn, width, op):
    """`arith`（§5）：add/sub/mul/div 取 rf0 舍入方向，rem 恒精确且不看舍入。"""
    dst = _fp_dst(insn, "rfhb")
    ew, sw = _FP_FMT[width]
    a = _fp_src(m, insn, width, "rfhc")
    b = _fp_src(m, insn, width, "rfhd")
    if op == "rem":
        res, flags = _fp.rem_exact(ew, sw, a, b)
    elif op == "add":
        res, flags = _fp.add_exact(ew, sw, a, b, False, _fp_mode(m))
    elif op == "sub":
        res, flags = _fp.add_exact(ew, sw, a, b, True, _fp_mode(m))
    elif op == "mul":
        res, flags = _fp.mul_exact(ew, sw, a, b, _fp_mode(m))
    else:
        res, flags = _fp.div_exact(ew, sw, a, b, _fp_mode(m))
    _fp_write_rf(m, dst, width, res)
    _fp_set_flags(m, flags)


def _fp_sclb(m, insn, width):
    """`ftsclb`/`fosclb`（§5）：rfHC × 2^rdHD，指数是 rd 组有符号 64 位整数。"""
    dst = _fp_dst(insn, "rfhb")
    ew, sw = _FP_FMT[width]
    n = _sext(m.get("rd", insn["rdhd"]), 64)
    res, flags = _fp.sclb_exact(ew, sw, _fp_src(m, insn, width), n, _fp_mode(m))
    _fp_write_rf(m, dst, width, res)
    _fp_set_flags(m, flags)


def _fp_root(m, insn, width):
    """`ftroot`/`foroot`（§6）：rootn(x, n)，仅 n=2；舍入方向取 rf0[33:32]。"""
    dst = _fp_dst(insn, "rfhb")
    if insn["immu6"] != 2:
        raise Fault("Illegal")
    ew, sw = _FP_FMT[width]
    res, flags = _fp.sqrt_exact(ew, sw, _fp_src(m, insn, width), _fp_mode(m))
    _fp_write_rf(m, dst, width, res)
    _fp_set_flags(m, flags)


def _fp_sign(m, insn, width, invert):
    """`sign`（§7）：copySign / negate-copySign，纯位操作、不置标志。"""
    dst = _fp_dst(insn, "rfhb")
    hc = _fp_src(m, insn, width, "rfhc")
    hd = _fp_src(m, insn, width, "rfhd")
    _fp_write_rf(m, dst, width, _fp.sign_inject(hc, hd, width - 1, invert))


def _fp_cmp(m, insn, width, signaling):
    """`compare`（§8）：结果 −1/0/+1 或 canonical qNaN 写 rd（整 64 位）。"""
    dst = _fp_dst(insn, "rdhb")
    ew, sw = _FP_FMT[width]
    a = _fp_src(m, insn, width, "rfhc")
    b = _fp_src(m, insn, width, "rfhd")
    res, flags = _fp.cmp_exact(ew, sw, a, b, signaling)
    m.set("rd", dst, res)
    _fp_set_flags(m, flags)


def _fp_minmax(m, insn, width, is_max):
    """`minmax`（§19）：单 NaN 返回那个数、双 NaN 取 canonical qNaN；sNaN ⇒ NV。"""
    dst = _fp_dst(insn, "rfhb")
    ew, sw = _FP_FMT[width]
    a = _fp_src(m, insn, width, "rfhc")
    b = _fp_src(m, insn, width, "rfhd")
    res, flags = _fp.minmax_exact(ew, sw, a, b, is_max)
    _fp_write_rf(m, dst, width, res)
    _fp_set_flags(m, flags)


def _fp_classify(m, insn, width):
    """`classify`（§9）：rd 窗口 ← rf 窗口，[9:0] 十类 one-hot、[63:10] 清零。"""
    dst, count, src = insn["rdhb"], insn["immu6"], insn["rfhc"]
    if dst == 0 or count == 0 or dst + count > 64 or src + count > 64:
        raise Fault("Illegal")
    ew, sw = _FP_FMT[width]
    for k in range(count):
        m.set("rd", dst + k,
              _fp.classify_fn(ew, sw, m.get("rf", src + k) & _FP_MASK[width]))


def _fp_rnd(m, insn, width):
    """`roundint`（§18）：六档 one-hot；只有 `0x20` 在结果 ≠ 输入时置 NX。"""
    dst = _fp_dst(insn, "rfhb")
    mode = _fp_mode_imm(m, insn)
    ew, sw = _FP_FMT[width]
    res, flags = _fp.rnd_exact(ew, sw, _fp_src(m, insn, width), mode,
                               insn["immu6"] == 0x20)
    _fp_write_rf(m, dst, width, res)
    _fp_set_flags(m, flags)


def _fp_f2i(m, insn, width, int_width, signed):
    """`convert_f2i`（§3）：目的 rd 整 64 位；六档 one-hot。"""
    dst = _fp_dst(insn, "rdhb")
    mode = _fp_mode_imm(m, insn)
    ew, sw = _FP_FMT[width]
    res, flags = _fp.f2i_exact(ew, sw, _fp_src(m, insn, width),
                               int_width, signed, mode)
    m.set("rd", dst, res)
    _fp_set_flags(m, flags)


def _fp_i2f(m, insn, width, int_width, signed, exact):
    """`convert_i2f`（§4）：`exact` = 低 6 位为 SBZ（非 0 ⇒ ILLI、不涉舍入）。"""
    dst = _fp_dst(insn, "rfhb")
    if exact:
        if insn["immu6"] != 0:
            raise Fault("Illegal")
        mode = _fp.RNE
    else:
        mode = _fp_mode_imm(m, insn)
    ew, sw = _FP_FMT[width]
    rec, flags = _fp.i2f_exact(int_width, ew, sw, m.get("rd", insn["rdhc"]),
                               signed, mode)
    _fp_write_rf(m, dst, width, _fp.fn_from_recfn(ew, sw, rec))
    _fp_set_flags(m, flags)


def _fp_f2f(m, insn, src_width, exact):
    """`convert_ff`（§2）：`ft2fo`（SBZ、恒精确）/ `fo2ft`（六档、可溢出/下溢）。"""
    dst = _fp_dst(insn, "rfhb")
    dst_width = 64 if src_width == 32 else 32
    if exact:
        if insn["immu6"] != 0:
            raise Fault("Illegal")
        mode = _fp.RNE
    else:
        mode = _fp_mode_imm(m, insn)
    sew, ssw = _FP_FMT[src_width]
    dew, dsw = _FP_FMT[dst_width]
    rec, flags = _fp.f2f_exact(sew, ssw, dew, dsw,
                               _fp_src(m, insn, src_width), mode)
    _fp_write_rf(m, dst, dst_width, _fp.fn_from_recfn(dew, dsw, rec))
    _fp_set_flags(m, flags)


def _fp_fma(m, insn, width):
    """`fma`（§20）：rfHB × rfHC + rfHD，精确和只舍入一次；舍入方向取 rf0。"""
    dst = _fp_dst(insn, "rfha")
    ew, sw = _FP_FMT[width]
    a = _fp_src(m, insn, width, "rfhb")
    b = _fp_src(m, insn, width, "rfhc")
    c = _fp_src(m, insn, width, "rfhd")
    res, flags = _fp.fma_exact(ew, sw, a, b, c, _fp_mode(m))
    _fp_write_rf(m, dst, width, res)
    _fp_set_flags(m, flags)


# arith（§5）：12 条（ft/fo × add/sub/mul/div/rem/sclb）
_sem_params(("ftadd_orrr_rf",), _fp_arith, width=32, op="add")
_sem_params(("ftsub_orrr_rf",), _fp_arith, width=32, op="sub")
_sem_params(("ftmul_orrr_rf",), _fp_arith, width=32, op="mul")
_sem_params(("ftdiv_orrr_rf",), _fp_arith, width=32, op="div")
_sem_params(("ftrem_orrr_rf",), _fp_arith, width=32, op="rem")
_sem_params(("foadd_orrr_rf",), _fp_arith, width=64, op="add")
_sem_params(("fosub_orrr_rf",), _fp_arith, width=64, op="sub")
_sem_params(("fomul_orrr_rf",), _fp_arith, width=64, op="mul")
_sem_params(("fodiv_orrr_rf",), _fp_arith, width=64, op="div")
_sem_params(("forem_orrr_rf",), _fp_arith, width=64, op="rem")
_sem_params(("ftsclb_orrr_rf",), _fp_sclb, width=32)
_sem_params(("fosclb_orrr_rf",), _fp_sclb, width=64)
# root（§6）/ sign（§7）/ minmax（§19）/ fma（§20）
_sem_params(("ftroot_orri_rf",), _fp_root, width=32)
_sem_params(("foroot_orri_rf",), _fp_root, width=64)
_sem_params(("ftsgnj_orrr_rf",), _fp_sign, width=32, invert=False)
_sem_params(("ftsgnn_orrr_rf",), _fp_sign, width=32, invert=True)
_sem_params(("fosgnj_orrr_rf",), _fp_sign, width=64, invert=False)
_sem_params(("fosgnn_orrr_rf",), _fp_sign, width=64, invert=True)
_sem_params(("ftmin_orrr_rf",), _fp_minmax, width=32, is_max=False)
_sem_params(("ftmax_orrr_rf",), _fp_minmax, width=32, is_max=True)
_sem_params(("fomin_orrr_rf",), _fp_minmax, width=64, is_max=False)
_sem_params(("fomax_orrr_rf",), _fp_minmax, width=64, is_max=True)
_sem_params(("ftfma_rrrr_rf",), _fp_fma, width=32)
_sem_params(("fofma_rrrr_rf",), _fp_fma, width=64)
# compare（§8）/ classify（§9）/ roundint（§18）
_sem_params(("ftqcmp_orrr_rf",), _fp_cmp, width=32, signaling=False)
_sem_params(("ftscmp_orrr_rf",), _fp_cmp, width=32, signaling=True)
_sem_params(("foqcmp_orrr_rf",), _fp_cmp, width=64, signaling=False)
_sem_params(("foscmp_orrr_rf",), _fp_cmp, width=64, signaling=True)
_sem_params(("ftcls_orri_rf",), _fp_classify, width=32)
_sem_params(("focls_orri_rf",), _fp_classify, width=64)
_sem_params(("ftrnd_orri_rf",), _fp_rnd, width=32)
_sem_params(("fornd_orri_rf",), _fp_rnd, width=64)
# convert_f2i（§3）：8 条
_sem_params(("ft2it_orri_rf",), _fp_f2i, width=32, int_width=32, signed=True)
_sem_params(("ft2io_orri_rf",), _fp_f2i, width=32, int_width=64, signed=True)
_sem_params(("ft2ut_orri_rf",), _fp_f2i, width=32, int_width=32, signed=False)
_sem_params(("ft2uo_orri_rf",), _fp_f2i, width=32, int_width=64, signed=False)
_sem_params(("fo2it_orri_rf",), _fp_f2i, width=64, int_width=32, signed=True)
_sem_params(("fo2io_orri_rf",), _fp_f2i, width=64, int_width=64, signed=True)
_sem_params(("fo2ut_orri_rf",), _fp_f2i, width=64, int_width=32, signed=False)
_sem_params(("fo2uo_orri_rf",), _fp_f2i, width=64, int_width=64, signed=False)
# convert_i2f（§4）：8 条（it/io/ut/uo 为源整型，ft/fo 为目的格式）
_sem_params(("it2ft_orri_rf",), _fp_i2f, width=32, int_width=32, signed=True,
            exact=False)
_sem_params(("io2ft_orri_rf",), _fp_i2f, width=32, int_width=64, signed=True,
            exact=False)
_sem_params(("ut2ft_orri_rf",), _fp_i2f, width=32, int_width=32, signed=False,
            exact=False)
_sem_params(("uo2ft_orri_rf",), _fp_i2f, width=32, int_width=64, signed=False,
            exact=False)
_sem_params(("it2fo_orri_rf",), _fp_i2f, width=64, int_width=32, signed=True,
            exact=True)
_sem_params(("io2fo_orri_rf",), _fp_i2f, width=64, int_width=64, signed=True,
            exact=False)
_sem_params(("ut2fo_orri_rf",), _fp_i2f, width=64, int_width=32, signed=False,
            exact=True)
_sem_params(("uo2fo_orri_rf",), _fp_i2f, width=64, int_width=64, signed=False,
            exact=False)
# convert_ff（§2）：2 条
_sem_params(("ft2fo_orri_rf",), _fp_f2f, src_width=32, exact=True)
_sem_params(("fo2ft_orri_rf",), _fp_f2f, src_width=64, exact=False)


# ---------------------------------------------------------------------------
# 自检（--self-test）
# ---------------------------------------------------------------------------
def _mk_machine():
    return new_machine("tiny")


def self_test():
    """寄存器组/48 位地址/大端/RAS/异常/semihosting 逐项断言。"""
    checks = []

    def eq(name, got, want):
        ok = got == want
        checks.append((name, ok, got, want))
        if not ok:
            print("SELFTEST FAIL: %s got=%r want=%r" % (name, got, want))

    m = _mk_machine()
    # 1. 四组寄存器初值 / 写回
    eq("banks_zero_init",
       [sum(m.get(b, i) for i in range(1, 64)) for b in ("rd", "rb", "rf", "ra")],
       [0, 0, 0, 0])
    m.set("rd", 5, 0x1234)
    m.set("rb", 6, 0x5678)
    m.set("rf", 7, 0x9ABC)
    m.set("ra", 8, 0xDEF0)
    eq("bank_writeback", [m.get("rd", 5), m.get("rb", 6), m.get("rf", 7),
                          m.get("ra", 8)], [0x1234, 0x5678, 0x9ABC, 0xDEF0])
    eq("rf0_reset_qnan", m.get("rf", 0), 0x7FF800007FC00000)
    m.set("rd", 0, 0xFFFF)
    eq("rd0_read_zero", m.get("rd", 0), 0)
    m.ip = 0xFFFF_FF01_0100
    eq("rb0_reads_ip", m.get("rb", 0), 0xFFFF_FF01_0100)
    rf0 = m.get("rf", 0)
    m.set("rf", 0, 0xFFFF_FFFF_FFFF_FFFF)
    eq("rf0_write_mask",
       (m.get("rf", 0) >> 32) & 0x3, 0x3)
    eq("rf0_preserved_high", m.get("rf", 0) >> 34, rf0 >> 34)
    m.set("ra", 0, 0xFFC0_0000_0000_0000 | (5 << 48) | 0x1234)
    eq("ra0_sbz_and_layout", m.get("ra", 0), (5 << 48) | 0x1234)

    # 2. 大端存储
    addr = 0xFFFF_FF01_5800
    m.mem.write_memory(64, addr, 0x0102_0304_0506_0708)
    eq("big_endian_bytes", list(m.mem.load_bytes(addr, 8)),
       [1, 2, 3, 4, 5, 6, 7, 8])
    eq("big_endian_read64", m.mem.read_memory(64, addr),
       0x0102_0304_0506_0708)
    eq("big_endian_read_ub", m.mem.read_memory(8, addr), 0x01)
    eq("big_endian_read_uw", m.mem.read_memory(16, addr + 2), 0x0304)
    m.mem.write_memory(16, addr + 6, 0xBEEF)
    eq("big_endian_write16", list(m.mem.load_bytes(addr, 8)),
       [1, 2, 3, 4, 5, 6, 0xBE, 0xEF])

    # 3. 48 位地址截断 + 地址空间解码
    #    EA = (rb + imm)[47:0]：高 16 位必须在**对齐判定与访存**之前截掉。用真实
    #    `ld.o`（译码 + 执行路径）做可达断言，不用常量折叠（`addr[63:48]` 置非零）。
    mz = _mk_machine()
    hi16 = 0x1234 << 48
    mz.set("rb", 6, hi16 | 0xFFFF_FF01_5800)
    try:
        _op_ld_o(mz, mz.dec.decode(0x20146004))    # ld.o rd5, [rb6, +4]（64 位错位）
        eq("addr48_ea_truncate", "no-fault", 0xFFFF_FF01_5804)
    except Fault as exc:
        eq("addr48_ea_truncate", (exc.cause, exc.info),
           ("Malign", 0xFFFF_FF01_5804))
    #    存储侧：带高位地址与 48 位地址解码到同一物理字节（Memory 先截 48 位）。
    mz.mem.write_memory(64, 0xFFFF_FF01_5800, 0x5A5A_5A5A_0000_1234)
    try:
        got_mem = hex(mz.mem.read_memory(64, hi16 | 0xFFFF_FF01_5800))
    except Fault as exc:
        got_mem = "fault:" + exc.cause
    eq("addr48_mem_truncate", got_mem, hex(0x5A5A_5A5A_0000_1234))
    try:
        m.mem.read_memory(64, 0x1_0000_0000_0000)
        eq("addr48_zero_window_faults", "no-fault", "CfxMem")
    except Fault as exc:
        eq("addr48_zero_window_faults", exc.cause, "CfxMem")
        eq("addr48_fault_info", exc.info, 0)
    try:
        m.mem.read_memory(64, 0x3800_0000_0000)   # reserved cfxha 14
        eq("reserved_cfx_mem_fault", "no-fault", "CfxMem")
    except Fault as exc:
        eq("reserved_cfx_mem_fault", exc.cause, "CfxMem")

    # 4. RAS 压弹栈
    m2 = _mk_machine()
    m2.ras_push(0x100)
    m2.ras_push(0x200)
    eq("ras_push_count", m2.racnt, 2)
    eq("ras_top", m2.get("ra", 63) & MASK48, 0x200)
    eq("ras_pop1", m2.ras_pop(), 0x200)
    m2.ras_push(0x200)
    m2.ras_push(0x200)
    eq("ras_recursion_fold", (m2.get("ra", 63) >> 48) & 0xFFFF, 2)
    eq("ras_pop_fold", m2.ras_pop(), 0x200)

    # 4b. RegRAS 环形缓冲（ADR-0012 D7.5）：基准 ±1、物理槽不搬移、回绕
    m6 = _mk_machine()
    m6.ras_push(0x100)                       # C1：空栈，基准不动
    eq("ras_ring_base_c1", m6.ras_base, 0)
    m6.ras_push(0x200)                       # C3a：只写一槽 + 基准 +1
    eq("ras_ring_base_c3a", m6.ras_base, 1)
    eq("ras_ring_no_move",
       (m6.banks["ra"][1] & MASK48, m6.banks["ra"][2] & MASK48), (0x100, 0x200))
    eq("ras_ring_logical_window",
       [m6.get("ra", i) & MASK48 for i in (62, 63)], [0x100, 0x200])
    eq("ras_ring_pop", (m6.ras_pop(), m6.ras_base), (0x200, 0))
    m6.ras_push(0x300)
    m6.ras_base = 62                         # 基准 62 再压栈 ⇒ 回绕到 0
    m6.ras_push(0x400)
    eq("ras_ring_wrap_up", (m6.ras_base, m6.get("ra", 63) & MASK48),
       (0, 0x400))
    eq("ras_ring_wrap_down", (m6.ras_pop(), m6.ras_base), (0x400, 62))
    # C3b/D4b：满栈溢出只搬栈底（MemRAS），其余条目物理槽不变
    m8 = _mk_machine()
    for k in range(1, 64):
        m8.set("ra", k, (1 << 48) | (0x1000 + k))
    m8._set_racnt(63)
    m8._set_mrptr(0xFFFF_FF01_7800)
    before = [m8.banks["ra"][i] for i in range(1, 64)]
    m8.ras_push(0x999)
    eq("ras_c3b_racnt", m8.racnt, 63)
    eq("ras_c3b_top", m8.get("ra", 63) & MASK48, 0x999)
    eq("ras_c3b_spill",
       m8.mem.read_memory(64, 0xFFFF_FF01_77F8) & MASK48, 0x1001)
    eq("ras_c3b_bottom", m8.get("ra", 1) & MASK48, 0x1002)
    eq("ras_c3b_one_slot_written",
       [i for i in range(1, 64) if m8.banks["ra"][i] != before[i - 1]], [2])
    m8.mem.write_memory(64, 0xFFFF_FF01_7800, (3 << 48) | 0x777)
    m8._set_racnt(0)
    m8._set_mrptr(0xFFFF_FF01_7800)
    eq("ras_d4b_target", m8.ras_pop(), 0x777)
    eq("ras_d4b_refill", (m8.racnt, m8.get("ra", 63) >> 48), (1, 2))

    # 5. 异常进入：MALIGN ⇒ hmon 向量 + 帧
    m3 = _mk_machine()
    m3.ip = 0xFFFF_FF01_0100
    m3.take_exception("Malign", m3.ip, 0xFFFF_FF01_5804)
    eq("excp_vector", m3.ip, 0x0FFF_0000_0000)
    eq("excp_cfx", m3.cfx_code, 3)
    eq("excp_prev_cfx", m3.cfx[3].cg5[CG5_PREV_CFX], 63)
    eq("excp_cause_onehot", m3.cfx[3].cg5[CG5_CAUSE_ID] & 0xFFFF,
       1 << CAUSE_BIT["Malign"])
    eq("excp_prev_ip", m3.cfx[3].cg5[CG5_PREV_IP], 0xFFFF_FF01_0100)
    eq("excp_prev_intr_mask",
       m3.cfx[3].cg5[CG5_PREV_INTR_MASK], MASK64)

    # 6. semihosting：SYS_WRITEC + SYS_EXIT
    m4 = _mk_machine()
    m4.mem.write_memory(8, 0xFFFF_FF01_7000, ord("A"))
    m4.set("rb", 16, 0xFFFF_FF01_7000)
    m4.set("rd", 16, SYS_WRITEC)
    m4._semihost(SEMIHOST_TAG)
    eq("semihost_writec", bytes(m4.output), b"A")
    block = 0xFFFF_FF01_7800
    m4.mem.write_memory(64, block, ADP_STOPPED_APP_EXIT)
    m4.mem.write_memory(64, block + 8, 7)
    m4.set("rb", 16, block)
    m4.set("rd", 16, SYS_EXIT)
    m4._semihost(SEMIHOST_TAG)
    eq("semihost_exit", (m4.halted, m4.exit_code), (True, 7))

    # 7. SYS_WRITE 不可用 ⇒ 返回「全部未写」（guest 走 SYS_WRITEC 回退）
    m5 = _mk_machine()
    wblock = 0xFFFF_FF01_7800
    m5.mem.write_memory(64, wblock, 1)
    m5.mem.write_memory(64, wblock + 8, 0xFFFF_FF01_7000)
    m5.mem.write_memory(64, wblock + 16, 16)
    m5.set("rb", 16, wblock)
    m5.set("rd", 16, SYS_WRITE)
    m5._semihost(SEMIHOST_TAG)
    eq("semihost_write_unavailable",
       (m5.get("rd", 8), m5.rd8_defined, len(m5.output)), (16, True, 0))

    # 8. cg5/cg15/cg16/cg3 槽位、权限与复位（spec/DADAO-12 §3.4/§3.6/§4.7/§4.9）
    CAUSE_IP6 = 0xFFFF_FF01_0200
    c5 = Cfx(3, 0x0FFF_0000_0000, MODE_HYPV, MASK64)
    eq("cg5_reset_entry", [c5.cg5[i] for i in range(6)], [0] * 6)
    eq("cg5_reset_exit", [c5.cg5[i] for i in range(8, 12)],
       [0, 0, 0, MASK64])
    for rc in range(6):                   # 入口记录 + cause 字段：软件写 ⇒ CFXREG
        try:
            c5.access(5, rc, True, 0x5A)
            eq("cg5_hw_ro_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg5_hw_ro_%d" % rc, exc.cause, "CfxReg")
    for rc in (6, 7, 12, 63):             # rc6/rc7 及其余保留
        try:
            c5.access(5, rc, True, 0)
            eq("cg5_reserved_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg5_reserved_%d" % rc, exc.cause, "CfxReg")
    c5.access(5, CG5_ESC_RUN_MODE, True, 0xFF)
    c5.access(5, CG5_ESC_CFX_CODE, True, 0xFF)
    c5.access(5, CG5_ESC_IP, True, 0xFFFF_FFFF_FFFF_FFFF)
    c5.access(5, CG5_ESC_INTR_MASK, True, 0x1234_5678_9ABC_DEF0)
    eq("cg5_exit_write_mask",
       [c5.access(5, rc, False) for rc in
        (CG5_ESC_RUN_MODE, CG5_ESC_CFX_CODE, CG5_ESC_IP, CG5_ESC_INTR_MASK)],
       [0x3, 0x3F, MASK48 & ~0x3, 0x1234_5678_9ABC_DEF0])

    # cg15/cg16 槽位与复位（spec/DADAO-12 §4.7/§4.9；ADR-0064 D1–D6）
    ch = Cfx(CFX_HART, 0x0FFF_0000_1000, MODE_SUPV, MASK64)
    eq("cg15_reset_switch", ch.cg15[CG15_SWITCH], MODE_SUPV)
    eq("cg15_reset_vector", ch.cg15[CG15_VECTOR], 0)
    eq("cg15_reset_capture", [ch.cg15[i] for i in range(6)], [0] * 6)
    for rc in range(6):                   # 入口记录 + 两个位图：软件写忽略
        ch.access(15, rc, True, 0xFFFF)
        eq("cg15_hw_ro_%d" % rc, ch.cg15[rc], 0)
    for rc in (6, 7, 13, 63):             # rc6–rc13 及其余保留 ⇒ CFXREG
        try:
            ch.access(15, rc, True, 0)
            eq("cg15_reserved_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg15_reserved_%d" % rc, exc.cause, "CfxReg")
    ch.access(15, CG15_SWITCH, True, MODE_JAIL)
    ch.access(15, CG15_VECTOR, True, 0x0FFF_0000_1007)
    eq("cg15_config_write",
       (ch.cg15[CG15_SWITCH], ch.cg15[CG15_VECTOR]),
       (MODE_JAIL, 0x0FFF_0000_1004))

    # 旧 cg9 捕获组、旧 cg8 掩码/定时器面全部归 reserved（访问 ⇒ CFXREG）。
    for cg, rc, name in ((9, 0, "cg9_reserved_0"),
                         (9, 5, "cg9_reserved_5"),
                         (9, 14, "cg9_reserved_14"),
                         (8, 1, "cg8_rc1_reserved"),
                         (8, 4, "cg8_rc4_reserved"),
                         (8, 5, "cg8_rc5_reserved")):
        try:
            ch.access(cg, rc, True, 0)
            eq(name, "no-fault", "CfxReg")
        except Fault as exc:
            eq(name, exc.cause, "CfxReg")

    # monitor 行（cfx0–cfx3）的 cg15：只有 rc3 = 异步来源掩码（复位全 1）。
    hmon0 = Cfx(3, 0x0FFF_0000_0000, MODE_HYPV, MASK64)
    eq("cg15_monitor_mask_reset",
       hmon0.access(15, CG15_ASYNC_INTR_MASK, False), MASK64)
    hmon0.access(15, CG15_ASYNC_INTR_MASK, True, 0xA5)
    eq("cg15_monitor_mask_rw",
       hmon0.access(15, CG15_ASYNC_INTR_MASK, False), 0xA5)
    for rc in (0, 1, 2, 4, 5, 6, 14, 15):
        try:
            hmon0.access(15, rc, True, 0)
            eq("cg15_monitor_reserved_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg15_monitor_reserved_%d" % rc, exc.cause, "CfxReg")
    try:
        hmon0.access(8, 1, True, 0)       # 旧掩码行归 reserved
        eq("cg8_rc1_monitor_reserved", "no-fault", "CfxReg")
    except Fault as exc:
        eq("cg8_rc1_monitor_reserved", exc.cause, "CfxReg")

    # cg16：只有 cfx_hart / cfx_pmem 实现；mask 复位全 1、pending RO、ack W1C。
    ch16 = Cfx(CFX_HART, 0x0FFF_0000_1000, MODE_SUPV, MASK64)
    eq("cg16_reset",
       [ch16.cg16[rc] for rc in (CG16_TIMER_CTRL, CG16_TIMER_CMP,
                                 CG16_MASK, CG16_PENDING, CG16_ACK)],
       [0, 0, MASK64, 0, 0])
    ch16.access(16, CG16_TIMER_CTRL, True, 0xFF)
    eq("cg16_timer_ctrl_bit0", ch16.access(16, CG16_TIMER_CTRL, False), 1)
    ch16.access(16, CG16_TIMER_CMP, True, 0x1234_5678_9ABC_DEF0)
    eq("cg16_timer_cmp_rw",
       ch16.access(16, CG16_TIMER_CMP, False), 0x1234_5678_9ABC_DEF0)
    ch16.access(16, CG16_MASK, True, 0xFFFF_FFFF_FFFF_FFFE)
    eq("cg16_mask_bit0_only", ch16.access(16, CG16_MASK, False), 0)
    try:
        ch16.access(16, CG16_PENDING, True, 1)
        eq("cg16_pending_ro", "no-fault", "CfxReg")
    except Fault as exc:
        eq("cg16_pending_ro", exc.cause, "CfxReg")
    eq("cg16_ack_reads_zero", ch16.access(16, CG16_ACK, False), 0)
    for rc in (2, 3, 19, 63):
        try:
            ch16.access(16, rc, True, 0)
            eq("cg16_hart_reserved_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg16_hart_reserved_%d" % rc, exc.cause, "CfxReg")
    cpm = Cfx(CFX_PMEM, 0x0FFF_0000_2000, MODE_SUPV, MASK64)
    eq("cg16_pmem_reset_mask", cpm.cg16[CG16_MASK], MASK64)
    for rc in (CG16_TIMER_CTRL, CG16_TIMER_CMP, 2, 63):
        try:
            cpm.access(16, rc, True, 0)
            eq("cg16_pmem_reserved_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg16_pmem_reserved_%d" % rc, exc.cause, "CfxReg")
    for obj, name in ((hmon0, "hmon"), (Cfx(63, 0, MODE_HYPV, MASK64),
                                        "power")):
        try:
            obj.access(16, CG16_MASK, True, 0)
            eq("cg16_absent_%s" % name, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg16_absent_%s" % name, exc.cause, "CfxReg")

    # cg15 只由 cfx_hart（捕获组）与 monitor（rc3 掩码）实现；其它 cfx ⇒ CFXREG。
    for obj, name in ((Cfx(63, 0, MODE_HYPV, MASK64), "power"),
                      (Cfx(CFX_PMEM, 0, MODE_SUPV, MASK64), "pmem")):
        try:
            obj.access(15, 0, True, 0)
            eq("cg15_absent_%s" % name, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg15_absent_%s" % name, exc.cause, "CfxReg")

    c3 = Cfx(3, 0x0FFF_0000_0000, MODE_HYPV, MASK64)
    eq("cg3_reset_switch_vector", (c3.cg3[CG3_SWITCH], c3.cg3[CG3_VECTOR]),
       (MODE_HYPV, 0x0FFF_0000_0000))
    for rc in (4, 5, 6, 7, 8, 9, 10, 11, 13):   # 旧 rc8/rc10 与其余 ⇒ CFXREG
        try:
            c3.access(3, rc, True, 0)
            eq("cg3_reserved_%d" % rc, "no-fault", "CfxReg")
        except Fault as exc:
            eq("cg3_reserved_%d" % rc, exc.cause, "CfxReg")
    c3.access(3, CG3_SWITCH, True, MODE_USER)
    c3.access(3, CG3_VECTOR, True, 0x0FFF_0000_0007)
    eq("cg3_switch_vector_write",
       (c3.cg3[CG3_SWITCH], c3.cg3[CG3_VECTOR]),
       (MODE_HYPV, 0x0FFF_0000_0004))

    # 8b. 同步进入的写入集合：cg5 rc0–rc5 + rc8–rc11（rc8–rc11 = 入口记录副本；
    #     rc3/rc11 = 当前模式 monitor 的 cg15 rc3 快照）。
    ms = _mk_machine()
    ms.cfx_code = 63
    ms.mode = MODE_HYPV
    ms.ip = CAUSE_IP6
    ms.cfx[3].cg15[CG15_ASYNC_INTR_MASK] = 0x0F0F_0F0F_0F0F_0F0F
    ms.take_exception("Malign", CAUSE_IP6, 0x1234)
    hs = ms.cfx[3].cg5
    eq("sync_entry_record",
       [hs[i] for i in range(6)],
       [MODE_HYPV, 63, CAUSE_IP6, 0x0F0F_0F0F_0F0F_0F0F,
        1 << CAUSE_BIT["Malign"], 0x1234])
    eq("sync_exit_intent",
       [hs[i] for i in range(8, 12)],
       [MODE_HYPV, 63, CAUSE_IP6, 0x0F0F_0F0F_0F0F_0F0F])

    # 8c. escape 五类判据 + rc11 整字 + escape_num（§5.1/§5.3）。
    me = _mk_machine()
    me.cfx_code = 3
    me.mode = MODE_HYPV
    me.ip = 0xFFFF_FF01_0100
    he = me.cfx[3]
    he.cg5[CG5_CAUSE_ID] = 0            # 不设帧有效位：cause_id == 0 也可返回
    he.cg5[CG5_ESC_RUN_MODE] = MODE_HYPV
    he.cg5[CG5_ESC_CFX_CODE] = 63
    he.cg5[CG5_ESC_IP] = CAUSE_IP6
    he.cg5[CG5_ESC_INTR_MASK] = 0x1111_2222_3333_4444
    he.cg15[CG15_ASYNC_INTR_MASK] = 0x5
    _op_escape(me, me.dec.decode(0x7E0C0000))       # escape cfx_hmon（imms18 = 0）
    eq("escape_return_ip", me.ip, CAUSE_IP6)
    eq("escape_return_state", (me.mode, me.cfx_code), (MODE_HYPV, 63))
    eq("escape_rc11_whole_word", he.cg15[CG15_ASYNC_INTR_MASK],
       0x1111_2222_3333_4444)
    eq("escape_num_inc", he.cg4[CG4_ESCAPE_NUM], 1)

    mc = _mk_machine()
    mc.cfx_code = 3
    mc.ip = 0xFFFF_FF01_0100
    hc = mc.cfx[3]
    for word, name in ((0x7E0C0001, "escape_imms18_1_illi"),
                       (0x7E0C0002, "escape_imms18_2_illi"),
                       (0x7E0C0003, "escape_imms18_3_illi"),
                       (0x7E0C0004, "escape_sbz_imms18_4_illi"),
                       (0x7E180000, "escape_reserved_cfx_illi")):
        try:
            _op_escape(mc, mc.dec.decode(word))
            eq(name, "no-fault", "Illegal")
        except Fault as exc:
            eq(name, exc.cause, "Illegal")
    eq("escape_illi_keeps_state",
       (mc.ip, mc.mode, mc.cfx_code, hc.cg4[CG4_ESCAPE_NUM]),
       (0xFFFF_FF01_0100, MODE_HYPV, 3, 0))

    # 目标 cfx 必须是当前 cfx（否则当前 cfx 的 CFXESC，且不改任何状态）。
    mcf = _mk_machine()
    mcf.cfx_code = 3
    mcf.ip = 0xFFFF_FF01_0100
    try:
        _op_escape(mcf, mcf.dec.decode(0x7E3C0000))     # escape cfx_hart，当前 = hmon
        eq("escape_target_cfx_mismatch", "no-fault", "CfxEsc")
    except Fault as exc:
        eq("escape_target_cfx_mismatch", exc.cause, "CfxEsc")
    eq("escape_mismatch_keeps_state",
       (mcf.ip, mcf.mode, mcf.cfx_code), (0xFFFF_FF01_0100, MODE_HYPV, 3))

    def _escape_fault(name, setup, mode=MODE_HYPV):
        mm = _mk_machine()
        mm.cfx_code = 3
        mm.ip = 0xFFFF_FF01_0100
        mm.mode = mode
        hh = mm.cfx[3]
        hh.cg5[CG5_ESC_RUN_MODE] = MODE_HYPV
        hh.cg5[CG5_ESC_CFX_CODE] = 63
        hh.cg5[CG5_ESC_IP] = CAUSE_IP6
        hh.cg5[CG5_ESC_INTR_MASK] = 0x5
        hh.cg15[CG15_ASYNC_INTR_MASK] = 0xA5
        setup(mm, hh)
        try:
            _op_escape(mm, mm.dec.decode(0x7E0C0000))
            eq(name, "no-fault", "CfxEsc")
        except Fault as exc:
            eq(name, exc.cause, "CfxEsc")
        eq(name + "_keeps_state",
           (mm.ip, mm.mode, mm.cfx_code, hh.cg15[CG15_ASYNC_INTR_MASK],
            hh.cg4[CG4_ESCAPE_NUM]),
           (0xFFFF_FF01_0100, mode, 3, 0xA5, 0))

    _escape_fault("escape_no_privilege_elevation",
                  lambda mm, hh: (setattr(mm, "mode", MODE_USER),
                                  hh.cg5.__setitem__(CG5_ESC_RUN_MODE, MODE_HYPV)),
                  mode=MODE_USER)
    _escape_fault("escape_target_cfx_unimplemented",
                  lambda mm, hh: hh.cg5.__setitem__(CG5_ESC_CFX_CODE, 6))
    _escape_fault("escape_target_mode_no_monitor",
                  lambda mm, hh: hh.cg5.__setitem__(CG5_ESC_RUN_MODE, MODE_JAIL))

    # 8d. 异步帧返回：当前 cfx = cfx_hart，共用同一出口（rc8–rc11 → supv/smon）。
    mh = _mk_machine()
    hart2 = Cfx(CFX_HART, 0x0FFF_0000_2000, MODE_SUPV, MASK64)
    smon = Cfx(2, 0x0FFF_0000_3000, MODE_SUPV, MASK64)
    mh.cfx[CFX_HART] = hart2
    mh.cfx[2] = smon
    mh.mode = MODE_SUPV
    mh.cfx_code = CFX_HART
    mh.ip = 0x0FFF_0000_4000
    hart2.cg5[CG5_ESC_RUN_MODE] = MODE_SUPV
    hart2.cg5[CG5_ESC_CFX_CODE] = 3
    hart2.cg5[CG5_ESC_IP] = CAUSE_IP6
    hart2.cg5[CG5_ESC_INTR_MASK] = 0xABCD_EF01_2345_6789
    smon.cg15[CG15_ASYNC_INTR_MASK] = 0x5
    _op_escape(mh, mh.dec.decode(0x7E3C0000))       # escape cfx_hart
    eq("async_escape_return",
       (mh.ip, mh.mode, mh.cfx_code,
        smon.cg15[CG15_ASYNC_INTR_MASK], hart2.cg4[CG4_ESCAPE_NUM]),
       (CAUSE_IP6, MODE_SUPV, 3, 0xABCD_EF01_2345_6789, 1))

    # 9. 异步进入（spec/DADAO-12 §5.4；ADR-0064 D4–D6/D9）：源接口在源 cfx 的
    #    cg16（rc16 mask / rc17 pending / rc18 ack），捕获缓冲在 cfx_hart cg15；
    #    运行模式掩码在当前模式 monitor 的 cg15 rc3（复位全 1）；进入不清 pending。
    def _async_pair(mode=MODE_HYPV, switch=MODE_SUPV, time_value=0):
        mm = _mk_machine()
        hh = Cfx(CFX_HART, 0x0FFF_0000_1000, MODE_SUPV, MASK64)
        pp = Cfx(CFX_PMEM, 0x0FFF_0000_2000, MODE_SUPV, MASK64)
        hh.cg15[CG15_VECTOR] = 0x0FFF_0000_1000
        hh.cg15[CG15_SWITCH] = switch
        mm.cfx[CFX_HART] = hh
        mm.cfx[CFX_PMEM] = pp
        if MODE_MONITOR[mode] not in mm.cfx:
            mm.cfx[MODE_MONITOR[mode]] = Cfx(
                MODE_MONITOR[mode], 0x0FFF_0000_3000, MODE_SUPV, MASK64)
        mm.mode = mode
        mm.cfx_code = 63
        mm.ip = 0xFFFF_FF01_0200
        mm.time_value = time_value
        return mm, hh, pp, mm.cfx[MODE_MONITOR[mode]]

    ma, hart, pmem, mon = _async_pair()
    eq("async_src_identity", (ASYNC_SRC_TIMER, ASYNC_SRC_PMEM),
       (0x8000, 0x1_0000_0000))
    eq("async_mask_reset_all1", ma.async_mask(), MASK64)
    # 源 mask 复位全 1 ⇒ 只置 pending、不进入；cg15 rc5 汇总置位。
    ma.async_post(ASYNC_SRC_TIMER)
    eq("async_source_mask_blocks", ma.async_entry(), False)
    eq("async_source_mask_pending",
       (hart.cg16[CG16_PENDING], hart.cg15[CG15_SRC_PENDING]),
       (CG16_SUBEVENT0, ASYNC_SRC_TIMER))
    # 打开 hmon 行与源 mask；先置 ENABLE=1（timer 源放行），再判定模式上限。
    mon.access(15, CG15_ASYNC_INTR_MASK, True,
               MASK64 & ~ASYNC_SRC_TIMER)
    hart.access(16, CG16_MASK, True, 0)
    ma.cfx_write(CFX_HART, 16, CG16_TIMER_CTRL, 1)
    eq("async_mode_ceiling_blocks", ma.async_entry(), False)
    eq("async_mode_ceiling_keeps_pending",
       (hart.cg16[CG16_PENDING], hart.cg15[CG15_SRC_PENDING]),
       (CG16_SUBEVENT0, ASYNC_SRC_TIMER))
    # rc14 配成 hypv(3) ⇒ 进入；源 pending 不清、rc5 不变。
    hart.cg15[CG15_SWITCH] = MODE_HYPV
    eq("async_open_entry", ma.async_entry(), True)
    eq("async_single_frame", hart.cg15[CG15_SRC_FRAME], ASYNC_SRC_TIMER)
    eq("async_pending_not_consumed",
       (hart.cg16[CG16_PENDING], hart.cg15[CG15_SRC_PENDING]),
       (CG16_SUBEVENT0, ASYNC_SRC_TIMER))
    eq("async_entry_record",
       [hart.cg15[i] for i in range(4)],
       [MODE_HYPV, 63, 0xFFFF_FF01_0200, MASK64 & ~ASYNC_SRC_TIMER])
    eq("async_cg5_entry_not_written", [hart.cg5[i] for i in range(4)],
       [0, 0, 0, 0])
    eq("async_exit_intent",
       [hart.cg5[i] for i in range(8, 12)],
       [MODE_HYPV, 63, 0xFFFF_FF01_0200, MASK64 & ~ASYNC_SRC_TIMER])
    eq("async_enter_target",
       (ma.mode, ma.cfx_code, ma.ip),
       (MODE_HYPV, CFX_HART, 0x0FFF_0000_1000))
    eq("async_num_per_entry", hart.cg4[CG4_ASYNC_NUM], 1)
    # ack 才清 pending：W1C bit0；保留位/已清位写 1 为 no-op；ack 读 0。
    hart.access(16, CG16_ACK, True, 0xFFFF_FFFF_FFFF_FFFE)
    eq("async_ack_reserved_ignored",
       hart.cg16[CG16_PENDING], CG16_SUBEVENT0)
    hart.access(16, CG16_ACK, True, 1)
    ma.refresh_async_summary()
    eq("async_ack_clears_pending",
       (hart.cg16[CG16_PENDING], hart.cg15[CG15_SRC_PENDING]), (0, 0))
    hart.access(16, CG16_ACK, True, 1)
    eq("async_ack_idempotent", hart.cg16[CG16_PENDING], 0)
    eq("async_ack_reads_zero", hart.access(16, CG16_ACK, False), 0)

    # 9b. 两个 mask 层各自生效：monitor 放行但源 mask=1 ⇒ 不进入；
    #     源 mask 放行但 monitor 屏蔽该源 ⇒ 不进入。
    mb, hb, pb, monb = _async_pair(mode=MODE_SUPV, switch=MODE_SUPV)
    monb.access(15, CG15_ASYNC_INTR_MASK, True, 0)     # hmon 全放行
    hb.access(16, CG16_MASK, True, CG16_SUBEVENT0)        # 源 mask=1
    mb.cfx_write(CFX_HART, 16, CG16_TIMER_CTRL, 1)
    mb.async_post(ASYNC_SRC_TIMER)
    eq("async_source_mask_gate", mb.async_entry(), False)
    eq("async_source_mask_gate_pending",
       hb.cg15[CG15_SRC_PENDING], ASYNC_SRC_TIMER)
    hb.access(16, CG16_MASK, True, 0)
    monb.access(15, CG15_ASYNC_INTR_MASK, True, ASYNC_SRC_TIMER)
    eq("async_monitor_mask_gate", mb.async_entry(), False)
    monb.access(15, CG15_ASYNC_INTR_MASK, True, 0)
    eq("async_mask_open_entry", mb.async_entry(), True)
    eq("async_mask_open_frame", hb.cg15[CG15_SRC_FRAME], ASYNC_SRC_TIMER)
    eq("async_enter_target_default", (mb.mode, mb.cfx_code),
       (MODE_SUPV, CFX_HART))

    # 9c. 一帧多源：同一界两个源同时放行 ⇒ 一次进入、frame = 位并集、计数 +1；
    #     下一界只放行一个源时仍整体覆盖 frame，未 ack 的源 pending 保留。
    mc, hc, pc, monc = _async_pair(mode=MODE_SUPV, switch=MODE_SUPV)
    monc.access(15, CG15_ASYNC_INTR_MASK, True, 0)
    hc.access(16, CG16_MASK, True, 0)
    pc.access(16, CG16_MASK, True, 0)
    mc.cfx_write(CFX_HART, 16, CG16_TIMER_CTRL, 1)
    mc.async_post(ASYNC_SRC_TIMER | ASYNC_SRC_PMEM)
    eq("async_multi_entry_once", mc.async_entry(), True)
    eq("async_multi_frame_union",
       hc.cg15[CG15_SRC_FRAME], ASYNC_SRC_TIMER | ASYNC_SRC_PMEM)
    eq("async_multi_pending_kept",
       (hc.cg16[CG16_PENDING], pc.cg16[CG16_PENDING],
        hc.cg15[CG15_SRC_PENDING]),
       (CG16_SUBEVENT0, CG16_SUBEVENT0,
        ASYNC_SRC_TIMER | ASYNC_SRC_PMEM))
    eq("async_multi_num_once", hc.cg4[CG4_ASYNC_NUM], 1)
    hc.access(16, CG16_MASK, True, CG16_SUBEVENT0)   # 只屏蔽 TIMER 源
    mc.cfx_code = CFX_HART
    mc.ip = 0x0FFF_0000_1000
    eq("async_overwrite_entry", mc.async_entry(), True)
    eq("async_overwrite_frame", hc.cg15[CG15_SRC_FRAME], ASYNC_SRC_PMEM)
    eq("async_overwrite_num", hc.cg4[CG4_ASYNC_NUM], 2)

    # 9d. TIMER 源还要求 ENABLE=1：pending 已置位但 ENABLE=0 ⇒ 不进入。
    md, hd, pd, mond = _async_pair(mode=MODE_SUPV, switch=MODE_SUPV)
    mond.access(15, CG15_ASYNC_INTR_MASK, True, 0)
    hd.access(16, CG16_MASK, True, 0)
    md.async_post(ASYNC_SRC_TIMER)
    eq("async_timer_disable_blocks", md.async_entry(), False)
    md.cfx_write(CFX_HART, 16, CG16_TIMER_CTRL, 1)
    eq("async_timer_enable_entry", md.async_entry(), True)

    # 9e. TIMER（cfx_hart cg16 rc0/rc1）：ENABLE 门控、到期边沿只置一次、
    #     使能即检、写 cmp 不清 pending、ack 才清。
    mt, ht, _, mont = _async_pair(mode=MODE_SUPV)
    mt.time_value = 100
    eq("timer_reset_pending", ht.cg16[CG16_PENDING], 0)
    mt.cfx_write(CFX_HART, 16, CG16_TIMER_CMP, 50)
    eq("timer_disabled_no_pending", mt.timer_check(), False)
    eq("timer_disabled_pending_zero", ht.cg16[CG16_PENDING], 0)
    mt.cfx_write(CFX_HART, 16, CG16_TIMER_CTRL, 1)   # 0→1 且 100>=50 ⇒ 立即置位
    eq("timer_enable_immediate", ht.cg16[CG16_PENDING], CG16_SUBEVENT0)
    eq("timer_enable_summary", ht.cg15[CG15_SRC_PENDING], ASYNC_SRC_TIMER)
    mt.cfx_write(CFX_HART, 16, CG16_TIMER_CMP, 200)  # 只重新 arm，不清 pending
    eq("timer_cmp_write_keeps_pending",
       ht.cg16[CG16_PENDING], CG16_SUBEVENT0)
    mt.cfx_write(CFX_HART, 16, CG16_ACK, 1)
    eq("timer_ack_clears",
       (ht.cg16[CG16_PENDING], ht.cg15[CG15_SRC_PENDING]), (0, 0))
    mt.time_value = 200
    eq("timer_expiry_edge", mt.timer_check(), True)
    eq("timer_expiry_pending", ht.cg16[CG16_PENDING], CG16_SUBEVENT0)
    eq("timer_edge_once", mt.timer_check(), False)   # 每个 deadline 只置一次

    # 9f. PMEM_DMA（cfx_pmem cg16）：bit0 = 传输结束（DONE|ERROR 合并），ack 前
    #     多次完成合并为一位；ack 只清 pending（dma_status 另行 W1C，不在本模型）。
    mf, hf, pf, monf = _async_pair(mode=MODE_SUPV)
    mf.async_post(ASYNC_SRC_PMEM)
    mf.async_post(ASYNC_SRC_PMEM)
    eq("dma_merge_two_completions", pf.cg16[CG16_PENDING], CG16_SUBEVENT0)
    eq("dma_summary_bit32", hf.cg15[CG15_SRC_PENDING], ASYNC_SRC_PMEM)
    pf.access(16, CG16_ACK, True, 1)
    mf.refresh_async_summary()
    eq("dma_ack_clears_pending",
       (pf.cg16[CG16_PENDING], hf.cg15[CG15_SRC_PENDING]), (0, 0))

    # 9g. 运行模式上限：当前 supv(2)、rc14=1(jail) ⇒ 不进入；rc14=2 ⇒ 进入。
    mg, hg, pg, mong = _async_pair(mode=MODE_SUPV, switch=MODE_JAIL)
    mong.access(15, CG15_ASYNC_INTR_MASK, True, 0)
    hg.access(16, CG16_MASK, True, 0)
    mg.cfx_write(CFX_HART, 16, CG16_TIMER_CTRL, 1)
    mg.async_post(ASYNC_SRC_TIMER)
    eq("async_ceiling_supv_no_entry", mg.async_entry(), False)
    eq("async_ceiling_supv_pending",
       hg.cg15[CG15_SRC_PENDING], ASYNC_SRC_TIMER)
    hg.cg15[CG15_SWITCH] = MODE_SUPV
    eq("async_ceiling_supv_entry", mg.async_entry(), True)


    failed = [c for c in checks if not c[1]]
    for name, ok, got, want in checks:
        print("%s %s" % ("PASS" if ok else "FAIL", name))
    print("self-test: %d/%d checks passed" % (len(checks) - len(failed),
                                              len(checks)))
    return 0 if not failed else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_init(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--elf", default=None)
    ap.add_argument("--profile", default="tiny")
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--init", default=None, help="初始架构状态 JSON（QEMU 观测面）")
    ap.add_argument("--max-steps", type=int, default=2_000_000)
    ap.add_argument("--image-out", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--state-out", default=None)
    ap.add_argument("--pc-log", default=None,
                    help="调试用：逐条记录 PC（不是 trace 格式，不属验收面）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.elf:
        ap.error("--elf required unless --self-test")

    bootrom = Path(args.bootrom) if args.bootrom else test_artifacts_bin()
    machine = new_machine(args.profile, bootrom=bootrom)
    load_elf(machine, args.elf)
    if args.init:
        machine.load_state(_load_init(args.init))
    pc_log = [] if args.pc_log else None
    exit_code = machine.run(args.max_steps, pc_log=pc_log)
    if args.pc_log:
        Path(args.pc_log).write_text(
            "\n".join("%x" % pc for pc in pc_log) + "\n", encoding="utf-8")
    snap = machine.snapshot()
    snap["exit_code"] = exit_code
    snap["steps"] = machine.steps
    snap["output_hex"] = bytes(machine.output).hex()
    if args.image_out:
        Path(args.image_out).write_bytes(bytes(machine.output))
    if args.state_out:
        Path(args.state_out).write_text(json.dumps(snap), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"exit_code": exit_code, "steps": machine.steps,
                        "output_hex": snap["output_hex"]}), encoding="utf-8")
    print("idl_exec: exit_code=%r steps=%d output=%d bytes"
          % (exit_code, machine.steps, len(machine.output)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
