#!/usr/bin/env python3
"""`tests/arch/power/power_vast.py` — `cfx_power`（cfx63）寄存器面 + power→hmon
移交的基础验证载体（`m16-testcases-016`）。

两条 case（`arch-power-001` 寄存器面/移交，三模式；`arch-power-002` 属性拒绝面，
只 hmon），由 `tests/arch/power/check_power.py` 按 `run_arch.py` 的 driver 契约
调起；RTL 承载由 `gen_power_rtl.py` / `check_power_rtl.py` 从**同一张探针表**生成。

## 判据来源（Independent oracle，现场派生，不写死）

  * cfx 编号（`cfx_power = 63`、`cfx_hmon = 3`）：`.tao/contracts/contract-cfx-aliases.md`
    §1 标量别名表；
  * `cg7` 块 0（BootROM）的 `desc`/`attr` 位号（`exists`/`ROM`/`R`/`X`）：
    `spec/DADAO-12-SEE-主管系统运行环境.md §3.8`；`desc = exists|ROM`、
    `attr = R|X`、`start = BootROM 起始地址 − (63 << 42)`、`size` = BootROM
    字节数：`spec/Kaiwu-测试机运行环境.md §3`（Vast 显式值 `0x3ff_ffc0_0000`
    / `0x40_0000`）；起始地址/字节数另与 `contracts/machine.yaml` 的 vast
    profile 双向核对；
  * 复位 `inner_cfx_code = 63`：`spec/Kaiwu §1`（复位向量 = `cfx_power` 的
    hypv 入口）＋ `DADAO-12 §5.2` 第 5/6 步（`trap` 进入时把**改写前**的
    `inner_cfx_code` 存进目标 cfx 的 `cg5 rc1`）⇒ 它的可观测形式就是
    power→hmon 帧里的 `excp_prev_cfx_code`；
  * 运行模式编码（user/jail/supv/hypv = 0/1/2/3）：`spec/Kaiwu §7.1`；
  * `CFXTRAP = 1 << 0`、`CFXREG = 1 << 2`：`.tao/contracts/contract-see.md
    §6.1`（monitor 视角同步原因表）；
  * `cg7` 全部只读、写任意 rc ⇒ `CFXREG`；`cfx_power_ctrl`（`cg8 rc1`，WO）
    读 ⇒ 读写属性不匹配 ⇒ `CFXREG`：`DADAO-12 §3.8`/`§4.12`、`SimRISC-11
    特权指令`（WO 只写）、`spec/Kaiwu §3`（Vast 实现该寄存器）。

期望值的唯一真源是上述派生函数；`tests/arch/power/expected.yaml` 的
`cases[].checks[].signature` 只是登记，由 `--selfcheck` 与本模块**双向**核对。

## 载体（4 MiB BootROM，QEMU 与 gem5 同一份字节）

复用 `tools/testcases/arch/node_probe_prelude.py` 的启动链：power 段
（`RESET_PC+0`，cfx63/hypv）装 `cfx_hmon.hypv.excp_vector` 后
`trap cfx_hmon, 0`；hmon 段（`RESET_PC+0x200`）按 step5 同序建页表/开 PTW 后
跳到 body（`RESET_PC+0x1000`）。body 进入时仍在 **hmon/hypv**，`cfx_hmon cg5`
里留着 power 的移交帧；body 先把移交值抄进签名槽，再按
`tests/arch/common/env-README.md` 的同一协议切到 `smon`/`umon` 跑寄存器面
（`cfx_hmon` 的 `<mode>` 行 `switch_run_mode` + `excp_vector` + `trap
cfx_hmon`），收尾回 hypv。

## 观测（签名流，槽 = 一个观测点）

`arch-power-001`（36 槽）：移交 4 槽（`prev_cfx` = 63、`prev_mode` = hypv、
`cause_id` = `CFXTRAP`、`cause_ip` 落在 BootROM 窗口的归一化标志）；`cg7`
块 0 四字段 + 块 1–15 的 `desc` + 块 15 的 `start/size/attr`（22 槽）；`cg4`/`cg6`
配置面 7 槽；`cfx_power_ctrl`（`cg8 rc1`，WO）**写 0 被接受** 1 槽（`m16-chipyard-031`，
原因槽仍 0）；收尾在 hypv 做 `cg5 rc1` 的 RW 回读（写哨兵、还原 cfxha，2 槽）。

`arch-power-002`（3 槽，只 hmon）：`cg7` 写 ⇒ `CFXREG`、`cfx_power_ctrl` 读 ⇒
`CFXREG`、`cg8 rc2` 读 ⇒ `CFXREG`（未定义 rc）。故障经 body 自装的
`cfx_hmon.hypv` 处理程序记 `excp_cause_id` 后 `escape` 回 `cause_ip + 4`。

`cfx_power_ctrl` 的 `bit0/1/2`（POWEROFF/HARD_RESET/SOFT_RESET）会结束仿真，
没有「执行后仍可观测」的签名槽；RTL 写侧探针
（`check_power_rtl.py --write-side`）逐位断言「写该位 ⇒ 仿真结束」。

## 未覆盖项（显式登记，见 `tests/arch/README.md`）

  * `cfx_power_ctrl` 的**写侧**：写 0 被接受已进 `arch-power-001` 的三方签名槽
    （QEMU `m16-qemu-006`、gem5 `m16-gem5-025`、RTL `m16-chipyard-031`）；bit0/1/2
    的副作用（结束仿真，复位约定为「结束 + harness 重启」）只由 RTL 写侧探针
    断言，不进签名流；
  * `cfx_power` 的 `cg4 rc1`（`version`）是 HW 值，spec 不规定、测试机约定
    也不在合约里 ⇒ 不写进逐槽判据（`cg4` 的 `cfx_id` 与四个计数器、`cg6`
    的 rc0/rc1 RW 已纳入，见 `_config_slots`）；
  * 电源语义本身（`bit0/1/2` = 关机/硬复位/软复位）不做板级断电/重启验证：
    测试机约定只到「结束仿真」（任务书「不做」第 1 条）。

用法：
  power_vast.py --only arch-power-001 --mode hmon --qemu PATH \\
      [--work-dir DIR] [--signature-out PATH] [--selfcheck] [--list] [--diagnose]
退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]               # tests/arch
_REPO = _HERE.parents[3]               # 仓库根

for _sub in (("tools", "testcases", "arch"), ("tools", "testcases", "lib"),
             ("tools", "infra"), ("tests", "shared")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_ARCH) not in sys.path:
    sys.path.insert(0, str(_ARCH))

import node_probe_prelude as P          # noqa: E402
import signature as _signature          # noqa: E402
import machine_profile                   # noqa: E402
from common import runlimit             # noqa: E402

CASES = ("arch-power-001", "arch-power-002")
MODES = ("hmon", "smon", "umon")
CASE_MODES = {
    "arch-power-001": ("hmon", "smon", "umon"),
    "arch-power-002": ("hmon",),
}

# 签名区 / 故障槽 / 模式切换保存区：都在 L1[3]（0x6000_0000..0x7fff_ffff，
# 预置页表已带 U+J）内；避开预置的 PT_PA(0x7ff0_0000)、FAULT_RECORD
# (0x7ffc_0000)、EXIT_BLOCK(0x7ffd_0000)。
SIG_BUF = 0x7000_0000
FAULT_SLOT = 0x7ffb_0000
SAVE_SLOT = 0x7ffb_0100
# 故障处理程序在 body 之后的固定偏移（ROM_BASE 相对；运行时按 body 长度校验）。
HAND_OFF = 0x1800

ROM_BASE = P.ROM_BASE
# 故障路径短超时（ISS-522）：与其它 arch 载体共用 `common/runlimit.py`
# （默认 10 s，`DADAO_ARCH_TIMEOUT` 放宽；`-d cpu` dump 运行中即按上限截断）。
TIMEOUT = runlimit.DEFAULT_TIMEOUT
SIG = _signature.Emitter(P)

# `cg5 rc1` 的 RW 回读哨兵（`DADAO-12 §3.6`：该字段 RW）。
RW_SENTINEL = 0x25


class SetupError(RuntimeError):
    """缺件/配置错误（退出码 2）。"""


# ---------------------------------------------------------------------------
# 合约 / 规范现场解析
# ---------------------------------------------------------------------------
def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError("cannot read %s: %s" % (path, exc))


def cfx_codes() -> dict:
    """`.tao/contracts/contract-cfx-aliases.md` §1：`cfx_<name>` -> cfxha。"""
    text = _read(_REPO / ".tao" / "contracts" / "contract-cfx-aliases.md")
    out = {}
    for name, code in re.findall(r"^\|\s*`cfx_([a-z]+)`\s*\|\s*`(\d+)`\s*\|",
                                 text, re.M):
        out[name] = int(code)
    need = {"power", "hmon"}
    if not need <= set(out):
        raise SetupError("contract-cfx-aliases §1 缺标量别名: %r"
                         % sorted(need - set(out)))
    return out


def mode_codes() -> dict:
    """`spec/Kaiwu` §7.1 monitor 段编码：user/jail/supv/hypv -> 0/1/2/3。"""
    text = _read(_REPO / "spec" / "Kaiwu-测试机运行环境.md")
    m = re.search(r"`bit5:4` 为运行模式——`user`=`(\d+)`、`jail`=`(\d+)`、"
                  r"`supv`=`(\d+)`、`hypv`=`(\d+)`", text)
    if not m:
        raise SetupError("spec/Kaiwu §7.1 模式编码句未找到")
    codes = dict(zip(("user", "jail", "supv", "hypv"),
                     (int(g, 2) for g in m.groups())))
    if codes != {"user": 0, "jail": 1, "supv": 2, "hypv": 3}:
        raise SetupError("模式编码与 2 bit 编码不符: %r" % codes)
    return {"hmon": codes["hypv"], "smon": codes["supv"],
            "umon": codes["user"]}


def cause_bits() -> dict:
    """`.tao/contracts/contract-see.md §6.1` 同步原因表：名字 -> cause id。"""
    text = _read(_REPO / ".tao" / "contracts" / "contract-see.md")
    out = {}
    for bit, name in re.findall(r"^\|\s*`1 << (\d+)`\s*\|\s*`([A-Z_]+)`\s*\|",
                                text, re.M):
        out.setdefault(name, 1 << int(bit))
    need = {"CFXTRAP", "CFXREG"}
    if not need <= set(out):
        raise SetupError("contract-see §6.1 缺原因: %r"
                         % sorted(need - set(out)))
    return out


def space_bits() -> dict:
    """`spec/DADAO-12 §3.8` 的 `desc`/`attr` 位号（现场解析，不写死）。"""
    text = _read(_REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md")
    start = text.find("### 3.8 cg7")
    # The section ends at the next top-level chapter ("## 4. …").  Do not key on
    # a following sub-section number: `m18-spec-004` deleted §3.9 (cg9 moved to
    # §4.7), which broke a "### 3.9" end marker while §3.8 itself is unchanged.
    end = -1
    if start >= 0:
        m = re.search(r"^## 4\.", text[start:], re.M)
        if m:
            end = start + m.start()
    if start < 0 or end < 0:
        raise SetupError("spec/DADAO-12 §3.8 未找到（小节起点或下一章起点缺失）")
    sec = text[start:end]
    bits = {}
    for m in re.finditer(r"bit(\d) = ([A-Za-z]+)", sec):
        bits.setdefault(m.group(2), int(m.group(1)))
    need = {"exists", "SRAM", "ROM", "MMIO", "DRAM", "OTHER", "R", "W", "X"}
    if not need <= set(bits):
        raise SetupError("§3.8 位表缺项: %r" % sorted(need - set(bits)))
    if "cg7 **全部只读**" not in sec:
        raise SetupError("§3.8 缺「cg7 全部只读」句")
    return bits


def power_space() -> dict:
    """`cfx_power` 的 cg7 块 0（BootROM）：现场派生 + 与 Kaiwu §3 双向核对。

    `start = BootROM 起始地址 − (cfxha << 42)`、`size` = BootROM 字节数、
    `desc = exists|ROM`、`attr = R|X`（`DADAO-12 §3.8` + `spec/Kaiwu §3`）；
    起始地址/字节数取 `contracts/machine.yaml` 的 vast profile，再与 Kaiwu §3
    的显式值核对，任一侧缺失/不符即显式失败。
    """
    prof = machine_profile.load("vast")
    codes = cfx_codes()
    bits = space_bits()
    power = codes["power"]
    base = prof.bootrom_base
    size = prof["bootrom_size"]
    start = base - (power << 42)
    if not 0 <= start < (1 << 42):
        raise SetupError("cfx_power 的 cg7 start 越界: %#x" % start)
    if start + size > (1 << 42):
        raise SetupError("cfx_power 的 cg7 start+size > 2^42: %#x"
                         % (start + size))
    desc = (1 << bits["exists"]) | (1 << bits["ROM"])
    attr = (1 << bits["R"]) | (1 << bits["X"])

    text = _read(_REPO / "spec" / "Kaiwu-测试机运行环境.md")
    m = re.search(r"\*\*`cg7` 空间块 0 = BootROM\*\*.*?"
                  r"`Kaiwu-Vast` ⇒ `start = (0x[0-9a-f_]+)`、"
                  r"`size = (0x[0-9a-f_]+)`", text, re.S)
    if not m:
        raise SetupError("spec/Kaiwu §3 的 cfx_power cg7（Vast）句未找到")
    spec_start = int(m.group(1).replace("_", ""), 16)
    spec_size = int(m.group(2).replace("_", ""), 16)
    if (spec_start, spec_size) != (start, size):
        raise SetupError(
            "cfx_power cg7 与 machine.yaml 不符: Kaiwu=(%#x,%#x) "
            "machine.yaml=(%#x,%#x)" % (spec_start, spec_size, start, size))
    return {"cfx": power, "desc": desc, "start": start, "size": size,
            "attr": attr}


def opcode_value(entry_id: str) -> int:
    """`contracts/opcodes.yaml` 的 `value`（opc + 子操作位）。"""
    import yaml

    path = _REPO / "contracts" / "opcodes.yaml"
    try:
        data = yaml.safe_load(_read(path))
    except yaml.YAMLError as exc:
        raise SetupError("opcodes.yaml 解析失败: %s" % exc)
    entry = next((e for e in data if isinstance(e, dict)
                  and e.get("id") == entry_id), None)
    if entry is None:
        raise SetupError("opcodes.yaml 缺 %s" % entry_id)
    try:
        return int(str(entry.get("value")), 16)
    except (TypeError, ValueError):
        raise SetupError("%s 的 value 不可解析: %r"
                         % (entry_id, entry.get("value")))


# ---------------------------------------------------------------------------
# 探针表（覆盖点见模块 docstring）
# ---------------------------------------------------------------------------
# `cg6` scratch 的 RW 哨兵（`DADAO-12 §3.7`：软件可用的 RW 寄存器）。
SCRATCH0 = 0x5A5A_5A5A_5A5A_5A5A
SCRATCH1 = 0xA5A5_A5A5_A5A5_A5A5


def _config_slots(power: int):
    """`cg4`/`cg6`（`DADAO-12 §3.5`/§3.7）的 7 个槽（`ISS-524`/DIV-13）。

    `cfx_id` 取自 `contract-cfx-aliases §1`；四个计数器为 0：本探针没有任何
    `trap`/异常/`escape` 以 `cfx_power` 为目标（移交的 `trap` 目标是
    `cfx_hmon`），`DADAO-12 §3.5` 定义它们按**进入该 cfx** 计数。`cg6` 只
    测试 rc0/rc1 的 RW 往返：`§3.7` 保证至少 2 个 scratch，数量本身是 HW
    值（`cg4 rc6`），不在本槽面里写死实现值。
    """
    out = [
        ("power_cfx_id", ("reg", power, 4, 0, cfx_codes()["power"])),
        ("power_trap_num", ("reg", power, 4, 2, 0)),
        ("power_sync_num", ("reg", power, 4, 3, 0)),
        ("power_async_num", ("reg", power, 4, 4, 0)),
        ("power_escape_num", ("reg", power, 4, 5, 0)),
        ("power_scratch0_rw", ("rw", power, 6, 0, SCRATCH0)),
        ("power_scratch1_rw", ("rw", power, 6, 1, SCRATCH1)),
    ]
    return [("mid", label, spec) for label, spec in out]


def _space_slots(power: int):
    """`arch-power-001` 的 22 个寄存器面槽（同一张表也给 RTL 生成器用）。"""
    pw = power_space()
    out = [
        ("space0_desc", ("reg", power, 7, 0, pw["desc"])),
        ("space0_start", ("reg", power, 7, 1, pw["start"])),
        ("space0_size", ("reg", power, 7, 2, pw["size"])),
        ("space0_attr", ("reg", power, 7, 3, pw["attr"])),
    ]
    for idx in range(1, 16):
        out.append(("space%d_desc" % idx, ("reg", power, 7, 4 * idx, 0)))
    out.append(("space15_start", ("reg", power, 7, 61, 0)))
    out.append(("space15_size", ("reg", power, 7, 62, 0)))
    out.append(("space15_attr", ("reg", power, 7, 63, 0)))
    return [("mid", label, spec) for label, spec in out]


def slot_table(case_id):
    """返回 `[(label, spec)]`；顺序即签名槽顺序（`expected.yaml` 同序）。

    spec 元组首项是槽类型，末项是期望值：
      * `("reg", cfx, cg, rc, 期望)`           读寄存器
      * `("ip_in_rom", cfx, cg, rc, 期望)`     读 cause_ip 并归一化成 1/0
      * `("rw", cfx, cg, rc, 期望)`            写值后读回
      * `("fault_rd", cfx, cg, rc, 期望)`      读 ⇒ 期望异常，槽记 cause id
      * `("fault_wr", cfx, cg, rc, 期望)`      写 ⇒ 期望异常，槽记 cause id
      * `("wr_ok", cfx, cg, rc, 写值, 期望)`   写 ⇒ 期望**被接受**，槽记 cause id
    """
    codes = cfx_codes()
    causes = cause_bits()
    power = codes["power"]
    hmon = codes["hmon"]
    if case_id == "arch-power-001":
        out = [
            # 移交帧（power -> hmon）：进入 body 时仍在 hmon/hypv，
            # `cfx_hmon cg5` 保留 power 段那次 `trap` 的现场。必须在降模式
            # **之前**读（降模式自身的 `trap cfx_hmon` 会重写该帧）。
            ("pre", "hmon_prev_cfx", ("reg", hmon, 5, 1, power)),
            ("pre", "hmon_prev_mode", ("reg", hmon, 5, 0,
                                      mode_codes()["hmon"])),
            ("pre", "hmon_cause_id", ("reg", hmon, 5, 2,
                                     causes["CFXTRAP"])),
            ("pre", "hmon_cause_ip_in_rom", ("ip_in_rom", hmon, 5, 3, 1)),
        ]
        out.extend(_config_slots(power))
        out.extend(_space_slots(power))
        out.extend([
            # `cfx_power_ctrl`（`cg8 rc1`，WO）写侧：写 0 必须**被接受**
            # （原因槽保持 0，不产生 CFXREG）——`DADAO-12 §4.12` + `SimRISC-11`
            # 「WO 只写」。读侧拒绝面在 `arch-power-002`；bit0/1/2 的副作用
            # 会结束仿真，放进 RTL 写侧探针（`check_power_rtl.py --write-side`），
            # 不进签名流。
            ("mid", "power_ctrl_write0_ok", ("wr_ok", power, 8, 1, 0, 0)),
        ])
        out.extend([
            # `cg5 rc1` 是 RW：写哨兵读回、再还原 power 的 cfxha。
            ("post", "hmon_prev_cfx_rw", ("rw", hmon, 5, 1, RW_SENTINEL)),
            ("post", "hmon_prev_cfx_restore", ("rw", hmon, 5, 1, power)),
        ])
        return out
    if case_id == "arch-power-002":
        return [
            ("mid", "cg7_write_cause",
             ("fault_wr", power, 7, 0, causes["CFXREG"])),
            ("mid", "power_ctrl_read_cause",
             ("fault_rd", power, 8, 1, causes["CFXREG"])),
            ("mid", "cg8_rc2_read_cause",
             ("fault_rd", power, 8, 2, causes["CFXREG"])),
        ]
    raise SetupError("未知 case %r（允许 %s）" % (case_id, list(CASES)))


def expected_values(case_id):
    """按同一派生规则给出每槽期望值（与 `expected.yaml` 双向核对）。"""
    return [spec[-1] for _, _, spec in slot_table(case_id)]


def slot_labels(case_id):
    return [label for _, label, _ in slot_table(case_id)]


# ---------------------------------------------------------------------------
# 编码（`contracts/opcodes.yaml`；`value` 携带 ALU 子操作位）
# ---------------------------------------------------------------------------
def _alu(hb, hc, hd, entry_id):
    return opcode_value(entry_id) | (hb << 12) | (hc << 6) | hd


def cmp_uo(hb, hc, hd):
    """`cmp.uo rdHB, rdHC, rdHD`（-1/0/1 写入 rdHB）。"""
    return _alu(hb, hc, hd, "cmp.uo_orrr_rd")


def br_cond(entry_id, rd, imms18):
    """`br.<cond> {rd}?, [rb0, imms18]`（`rdha[23:18]`、`imms18[17:0]`）。"""
    return opcode_value(entry_id) | (rd << 18) | (imms18 & 0x3FFFF)


class _BrFix:
    """`node_probe_prelude.Seq.resolve()` 只支持 eq/ne/nz/z/nn；本载体需要
    `br.n`/`br.np`（`ip_in_rom` 的区间判定），故在 `resolve()` 之后自行回填。"""

    def __init__(self):
        self.sites = []                 # [(word_index, entry_id, rd, label)]

    def emit(self, seq, entry_id, rd, label):
        self.sites.append((len(seq.w), entry_id, rd, label))
        seq.e(0)

    def patch(self, seq):
        for idx, entry_id, rd, label in self.sites:
            seq.w[idx] = br_cond(entry_id, rd, seq.lab[label] - idx)


def _load4(rd, val):
    """固定 4 字的 64 位立即数装入（地址两遍 patch 需要固定长度）。"""
    out = [P.set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        out.append(P.or_w_rd(rd, wp, (val >> (16 * wp)) & 0xFFFF))
    return out


class _AddrSites:
    """记录 `_load4` 装入的位置，`resolve()` 后按标签地址回填。"""

    def __init__(self):
        self.sites = []                 # [(label, word_index, rd)]

    def emit(self, seq, rd, label):
        idx = len(seq.w)
        seq.e(*_load4(rd, 0))
        self.sites.append((label, idx, rd))

    def patch(self, seq, labels):
        for label, idx, rd in self.sites:
            seq.w[idx:idx + 4] = _load4(rd, labels[label])


# ---------------------------------------------------------------------------
# 槽的发射（word-builder）；RTL 生成器用 `slot_asm` 出等价助记符
# ---------------------------------------------------------------------------
def _emit_slot(seq, spec, brfix=None):
    kind = spec[0]
    if kind == "reg":
        _, cfx, cg, rc, _ = spec
        seq.e(P.cfx2rd(cfx, cg, rc, 5))
        SIG.upd(seq, 5)
        return
    if kind == "ip_in_rom":
        _, cfx, cg, rc, _ = spec
        # `trap` 由 BootROM 里的 power 段发出 ⇒ cause_ip 必在该窗口；地址本身
        # 逐平台不同（QEMU/gem5 是自建 ROM 的偏移，RTL 是固件的偏移），故归一化
        # 成 1/0 再进签名流。
        seq.e(P.cfx2rd(cfx, cg, rc, 5))
        seq.e(*P.load_rd(6, P.BOOTROM_BASE))
        seq.e(cmp_uo(7, 5, 6))
        if brfix is None:
            raise SetupError("ip_in_rom 槽需要 _BrFix（br.np/br.n 不在 Seq 里）")
        brfix.emit(seq, "br.np_riii_rd", 7, "ip_not_above_base")
        seq.e(*P.load_rd(6, P.BOOTROM_BASE + P.BOOTROM_SIZE))
        seq.e(cmp_uo(7, 5, 6))
        brfix.emit(seq, "br.n_riii_rd", 7, "ip_in_rom")
        seq.mark("ip_not_above_base")
        seq.e(*P.load_rd(5, 0))
        seq.b("z", 0, "ip_flag_done")
        seq.mark("ip_in_rom")
        seq.e(*P.load_rd(5, 1))
        seq.mark("ip_flag_done")
        SIG.upd(seq, 5)
        return
    if kind == "rw":
        _, cfx, cg, rc, value = spec
        seq.e(*P.load_rd(6, value))
        seq.e(P.cfx2rc(cfx, cg, rc, 6))
        seq.e(P.cfx2rd(cfx, cg, rc, 5))
        SIG.upd(seq, 5)
        return
    if kind in ("fault_rd", "fault_wr", "wr_ok"):
        _, cfx, cg, rc = spec[:4]
        seq.e(*P.load_rb(7, FAULT_SLOT))
        seq.e(P.st_o(0, 7, 0))              # 清故障槽（不靠残留）
        if kind == "fault_rd":
            seq.e(P.cfx2rd(cfx, cg, rc, 6))
        else:
            # `wr_ok` 写的是 spec 给的值（写 0 ⇒ 规范要求被接受）；`fault_wr`
            # 只关心「被拒」，写 0 即可。
            value = spec[4] if kind == "wr_ok" else 0
            seq.e(*P.load_rd(6, value))
            seq.e(P.cfx2rc(cfx, cg, rc, 6))
        seq.e(P.ld_o(5, 7, 0))
        SIG.upd(seq, 5)
        return
    raise SetupError("未知槽类型 %r" % (kind,))


def slot_asm(spec, idx):
    """RTL 生成器用：返回该槽的等价汇编行（含 `__REC`）。"""
    kind = spec[0]
    codes = cfx_codes()
    name = {codes["power"]: "cfx_power", codes["hmon"]: "cfx_hmon"}

    def reg(cfx, cg, rc):
        return "%s, cg%d, rc%d" % (name[cfx], cg, rc)

    if kind == "reg":
        _, cfx, cg, rc, _ = spec
        return ["\tcfx2rd\t%s, rd5" % reg(cfx, cg, rc), "\t__REC\trd5"]
    if kind == "ip_in_rom":
        _, cfx, cg, rc, _ = spec
        lab = "ip%d" % idx
        return [
            "\tcfx2rd\t%s, rd5" % reg(cfx, cg, rc),
            "\tset.rd\trd6, BOOTROM_BASE",
            "\tcmp.uo\trd7, rd5, rd6",
            "\tbr.np\t{rd7}?, [rb0, %s_no]" % lab,
            "\tset.rd\trd6, BOOTROM_BASE + BOOTROM_SIZE",
            "\tcmp.uo\trd7, rd5, rd6",
            "\tbr.n\t{rd7}?, [rb0, %s_yes]" % lab,
            "%s_no:" % lab,
            "\tset.rd\trd5, 0",
            "\tjump\t[rb0, %s_done]" % lab,
            "%s_yes:" % lab,
            "\tset.rd\trd5, 1",
            "%s_done:" % lab,
            "\t__REC\trd5",
        ]
    if kind == "rw":
        _, cfx, cg, rc, value = spec
        return [
            "\tset.rd\trd6, %#x" % value,
            "\tcfx2rc\t%s, rd6" % reg(cfx, cg, rc),
            "\tcfx2rd\t%s, rd5" % reg(cfx, cg, rc),
            "\t__REC\trd5",
        ]
    if kind in ("fault_rd", "fault_wr", "wr_ok"):
        _, cfx, cg, rc = spec[:4]
        lab = "f%d" % idx
        lines = [
            "\tst.o\trd0, [rb20, 0xE0]\t@@ 清固件 cause 槽（不靠残留）",
            "\tset.rb\trb21, %s" % lab,
            "\tst.o\trb21, [rb20, 0xF8]\t@@ 返回点",
        ]
        if kind == "fault_rd":
            lines.append("\tcfx2rd\t%s, rd6" % reg(cfx, cg, rc))
        else:
            value = spec[4] if kind == "wr_ok" else 0
            lines.append("\tset.rd\trd6, %s" % (("%#x" % value) if value
                                                else "0"))
            lines.append("\tcfx2rc\t%s, rd6" % reg(cfx, cg, rc))
        lines += ["%s:" % lab,
                  "\tld.o\trd5, [rb20, 0xE0]",
                  "\t__REC\trd5"]
        return lines
    raise SetupError("未知槽类型 %r" % (kind,))


# ---------------------------------------------------------------------------
# 镜像构造
# ---------------------------------------------------------------------------
def _fault_handler(hmon: int):
    """hmon 同步异常：记 cause_id 到故障槽，回到 `cause_ip + 4`。

    用 rd9（不是 rd5）：诊断探针的「读回值」槽也放在 rd5，处理程序不得改写它。
    """
    seq = P.Seq()
    seq.e(P.cfx2rd(hmon, 5, 2, 9))
    seq.e(*P.load_rb(7, FAULT_SLOT))
    seq.e(P.st_o(9, 7, 0))              # [FAULT_SLOT] = cause
    seq.e(P.escape(hmon, 1))
    return seq.resolve()


def build_program(case_id, mode):
    """返回 (body words, handler words, labels)；labels 用于诊断。"""
    if mode not in CASE_MODES[case_id]:
        raise SetupError("%s 不允许 --mode %s" % (case_id, mode))
    codes = cfx_codes()
    hmon, power = codes["hmon"], codes["power"]
    table = slot_table(case_id)
    seq = P.Seq()
    addr = _AddrSites()
    brfix = _BrFix()
    mods = mode_codes()

    SIG.begin(seq, SIG_BUF, len(table))

    need_handler = any(spec[0].startswith("fault") for _, _, spec in table)
    # 故障处理程序放在 body 之后的固定偏移；地址先占位，body 定长后回填。
    if need_handler:
        addr.emit(seq, 22, "HANDLER")
        seq.e(P.cfx2rc(hmon, 3, 10, 22))    # cfx_hmon.hypv.excp_vector

    # 模式切换的权限准备：smon 访问 cfx_power 的任一 cg 要其 `cg3 rc12`
    # （deleg）对应位 = 0（`DADAO-12 §3.4`；缺省全 1 ⇒ supv 全拒）。降模式前
    # 在 hypv 整组开放（`0x8`：除恒 1 的 bit3 外无置位），回到 hypv 后还原并
    # 回读校验；不符 ⇒ fail-closed（`0xE3`）。
    save_deleg = mode == "smon"
    if save_deleg:
        seq.e(*P.load_rb(8, SAVE_SLOT))
        seq.e(P.cfx2rd(power, 3, 12, 5))
        seq.e(P.st_o(5, 8, 16))             # [SAVE_SLOT+16] = 原 deleg
        seq.e(*P.load_rd(6, 0x8))
        seq.e(P.cfx2rc(power, 3, 12, 6))
        seq.e(P.cfx2rd(power, 3, 12, 5))
        seq.e(*P.load_rd(6, 0x8))
        seq.e(cmp_uo(7, 5, 6))              # 回读必须等于 0x8
        seq.b("nz", 7, "perm_fail")

    for phase, _, spec in table:
        if phase == "pre":
            _emit_slot(seq, spec, brfix)

    if mode != "hmon":
        seq.e(*P.load_rb(8, SAVE_SLOT))
        # 保存 cfx_hmon 的 hypv 行（向量 + switch_run_mode），收尾还原
        seq.e(P.cfx2rd(hmon, 3, 10, 5))
        seq.e(P.st_o(5, 8, 0))
        seq.e(P.cfx2rd(hmon, 3, 8, 5))
        seq.e(P.st_o(5, 8, 8))
        row = 2 if mode == "smon" else 0     # supv / user 行
        # 该模式行的收尾向量：`trap cfx_hmon` 回到 hypv 的 HYPV_RET
        addr.emit(seq, 6, "HYPV_RET")
        seq.e(P.cfx2rc(hmon, row, 10, 6))
        seq.e(*_load4(6, mods["hmon"]), P.cfx2rc(hmon, row, 8, 6))
        # hypv 行：进入目标模式
        addr.emit(seq, 6, "MODE_ENTRY")
        seq.e(P.cfx2rc(hmon, 3, 10, 6))
        seq.e(*_load4(6, mods[mode]), P.cfx2rc(hmon, 3, 8, 6))
        seq.e(P.trap(hmon, 0), P.swym())
        seq.mark("MODE_ENTRY")

    for phase, _, spec in table:
        if phase == "mid":
            _emit_slot(seq, spec, brfix)

    if mode != "hmon":
        seq.e(P.trap(hmon, 0), P.swym())    # 回到 hypv（经该模式行）
        seq.mark("HYPV_RET")
        seq.e(*P.load_rb(8, SAVE_SLOT))
        seq.e(P.ld_o(5, 8, 0), P.cfx2rc(hmon, 3, 10, 5))
        seq.e(P.ld_o(5, 8, 8), P.cfx2rc(hmon, 3, 8, 5))

    if save_deleg:
        seq.e(*P.load_rb(8, SAVE_SLOT))
        seq.e(P.ld_o(5, 8, 16))
        seq.e(P.cfx2rc(power, 3, 12, 5))
        seq.e(P.cfx2rd(power, 3, 12, 5))
        seq.e(P.ld_o(6, 8, 16))
        seq.e(cmp_uo(7, 5, 6))              # 还原后回读校验
        seq.b("nz", 7, "perm_fail")

    # `cg5 rc1` 的 RW 回读放在**所有故障面之后**：哨兵值 0x25 不是有效 cfxha，
    # 若它生效期间进入异常，`escape` 会把 `inner_cfx_code` 还原成 0x25。
    for phase, _, spec in table:
        if phase == "post":
            _emit_slot(seq, spec, brfix)

    SIG.dump(seq, SIG_BUF, len(table))
    seq.e(*P.exit_seq(0))
    seq.e(P.jump_rel(0))                    # SYS_EXIT 未生效 ⇒ 自锁（非 PASS）
    seq.mark("perm_fail")
    seq.e(*P.exit_seq(0xE3))                # 权限准备/还原回读不符
    seq.e(P.jump_rel(0))
    seq.resolve()
    brfix.patch(seq)

    body_len = 4 * len(seq.w)
    if body_len > HAND_OFF - 4 * len(_fault_handler(hmon) if need_handler else []):
        raise SetupError("body %d B 与故障处理程序（偏移 0x%x）重叠"
                         % (body_len, HAND_OFF))
    labels = {name: ROM_BASE + 4 * idx for name, idx in seq.lab.items()}
    labels["HANDLER"] = ROM_BASE + HAND_OFF
    addr.patch(seq, labels)
    handler = _fault_handler(hmon) if need_handler else []
    return seq.w, handler, labels


def build_rom(case_id, mode):
    """返回 (4 MiB 镜像, 标签表, body 字节数)。"""
    body, handler, labels = build_program(case_id, mode)
    handlers = {HAND_OFF: handler} if handler else None
    return P.build_rom(body, handlers=handlers), labels, 4 * len(body)


# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------
def _parse_cpu_log(text):
    blocks, pc = [], None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^PC: ([0-9a-fA-F]+)$", line)
        if m:
            pc = int(m.group(1), 16)
            continue
        m = re.match(r"^MODE: (\d+)$", line)
        if m and pc is not None:
            blocks.append((pc, int(m.group(1))))
            pc = None
    return blocks


def _rom_command(engine, rom_path, console, cpu_log, body_len):
    return [str(engine), "-machine",
            "%s,bootrom-image=%s" % (machine_profile.machine_name(P.PROFILE),
                                     rom_path),
            "-nographic",
            "-semihosting-config", "enable=on,target=native,chardev=semi",
            "-chardev", "file,id=semi,path=%s" % console,
            "-d", "cpu", "-D", str(cpu_log),
            "-dfilter", "0x%x+0x%x" % (ROM_BASE, body_len)]


def run_case(case_id, mode, engine, work, timeout=TIMEOUT):
    rom, _labels, body_len = build_rom(case_id, mode)
    work.mkdir(parents=True, exist_ok=True)
    console = work / "console.bin"
    cpu_log = work / "cpu.log"
    for stale in (console, cpu_log):
        if stale.exists():
            stale.unlink()
    rom_path = work / "rom.bin"
    rom_path.write_bytes(rom)
    cmd = _rom_command(engine, rom_path, console, cpu_log, body_len)
    res = runlimit.run(cmd, timeout=timeout, dump=cpu_log)
    rc = res.rc
    blob = console.read_bytes() if console.is_file() else b""

    problems = []
    if res.timed_out:
        problems.append("模拟器超时（%ds）" % res.timeout)
    elif res.dump_capped:
        problems.append("`-d cpu` dump %d B 超过上限 %d B（已终止）"
                        % (res.dump_bytes, runlimit.max_dump_bytes()))
    elif rc != 0:
        problems.append("模拟器退出码 %d（0x%x）" % (rc, rc) if rc > 0
                        else "模拟器退出码 %d" % rc)

    # MODE 观测在截断之前先读出来（失败/超限后 `finish_dump` 只留头部）。
    blocks = []
    if cpu_log.is_file():
        blocks = _parse_cpu_log(cpu_log.read_text(encoding="utf-8",
                                                  errors="replace"))
    runlimit.finish_dump(cpu_log, res)

    want = expected_values(case_id)
    got = None
    try:
        got = _signature.parse(blob, len(want))
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        problems.extend("签名流: " + p for p in _signature.compare(got, want))

    # 运行模式由模拟器现场观测（`-d cpu` 的 MODE:），不由 body 自述。
    body_lo, body_hi = ROM_BASE, ROM_BASE + body_len
    seen = sorted({m for pc, m in blocks if body_lo <= pc < body_hi})
    if mode_codes()[mode] not in seen:
        problems.append(
            "运行模式未观测到：期望 body 窗口 [%#x,%#x) 内 MODE=%d，实际 %r"
            % (body_lo, body_hi, mode_codes()[mode], seen))

    result = {
        "case": case_id,
        "mode": mode,
        "exit_code": rc,
        "timeout_s": res.timeout,
        "dump_bytes": res.dump_bytes,
        "dump_capped": res.dump_capped,
        "observed_body_modes": seen,
        "signature_slots": got,
        "expected_signature": want,
        "problems": problems,
        "command": cmd,
        "verdict": "PASS" if not problems else "FAIL",
    }
    (work / "run.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, blob


# ---------------------------------------------------------------------------
# --diagnose：未纳入判据的差分面（逐平台报告，不参与签名比对）
# ---------------------------------------------------------------------------
DIAG_PROBES = (
    ("power_ctrl_write0", "wr", 8, 1),
    ("power_id_cg4", "rd", 4, 0),
    ("power_scratch_cg6", "rd", 6, 0),
)


def build_diagnose_program():
    """返回 (body, handler, labels)：每个诊断探针两个槽（cause, 读回值）。

    cause = 0 ⇒ 该访问被接受，第二个槽是寄存器的读回值；cause = `CFXREG` ⇒
    访问被拒，第二个槽固定 0（读之前的初值）。
    """
    codes = cfx_codes()
    hmon, power = codes["hmon"], codes["power"]
    seq = P.Seq()
    addr = _AddrSites()
    SIG.begin(seq, SIG_BUF, 2 * len(DIAG_PROBES))
    addr.emit(seq, 22, "HANDLER")
    seq.e(P.cfx2rc(hmon, 3, 10, 22))
    for _, kind, cg, rc in DIAG_PROBES:
        seq.e(*P.load_rb(7, FAULT_SLOT))
        seq.e(P.st_o(0, 7, 0))              # 清 cause 槽
        seq.e(*P.load_rd(5, 0))             # 读回值先置 0（异常时保持）
        if kind == "wr":
            seq.e(*P.load_rd(6, 0))
            seq.e(P.cfx2rc(power, cg, rc, 6))
        else:
            seq.e(P.cfx2rd(power, cg, rc, 5))
        seq.e(P.ld_o(6, 7, 0))              # cause
        SIG.upd(seq, 6)
        SIG.upd(seq, 5)
    SIG.dump(seq, SIG_BUF, 2 * len(DIAG_PROBES))
    seq.e(*P.exit_seq(0))
    seq.e(P.jump_rel(0))
    seq.resolve()
    labels = {name: ROM_BASE + 4 * idx for name, idx in seq.lab.items()}
    labels["HANDLER"] = ROM_BASE + HAND_OFF
    addr.patch(seq, labels)
    return seq.w, _fault_handler(hmon), labels


def diagnose(engine, work, timeout=TIMEOUT) -> dict:
    """跑诊断探针，返回 {"probes": {label: {"cause": .., "value": ..}}}。"""
    body, handler, _ = build_diagnose_program()
    rom = P.build_rom(body, handlers={HAND_OFF: handler})
    work.mkdir(parents=True, exist_ok=True)
    console = work / "console.bin"
    cpu_log = work / "cpu.log"
    for stale in (console, cpu_log):
        if stale.exists():
            stale.unlink()
    rom_path = work / "rom.bin"
    rom_path.write_bytes(rom)
    cmd = _rom_command(engine, rom_path, console, cpu_log, 4 * len(body))
    rc, blob, _ = _signature.run(cmd, out=str(console), timeout=timeout)
    out = {"exit_code": rc, "probes": {}}
    try:
        slots = _signature.parse(blob, 2 * len(DIAG_PROBES))
    except _signature.SignatureError as exc:
        out["error"] = str(exc)
        return out
    for idx, (label, _, _, _) in enumerate(DIAG_PROBES):
        out["probes"][label] = {"cause": slots[2 * idx],
                                "value": slots[2 * idx + 1]}
    return out


# ---------------------------------------------------------------------------
# --selfcheck（不启动模拟器）
# ---------------------------------------------------------------------------
def selfcheck() -> int:
    import yaml

    problems = []
    print("=" * 72)
    print("power_vast --selfcheck（不启动模拟器）")
    print("=" * 72)
    try:
        codes = cfx_codes()
        modes = mode_codes()
        causes = cause_bits()
        bits = space_bits()
        pw = power_space()
        cmp_val = opcode_value("cmp.uo_orrr_rd")
    except SetupError as exc:
        print("  FAIL  合约/规范派生: %s" % exc)
        return 1
    print("  PASS  cfxha: power=%d hmon=%d；模式编码 %r"
          % (codes["power"], codes["hmon"], modes))
    print("  PASS  cause: CFXTRAP=%#x CFXREG=%#x"
          % (causes["CFXTRAP"], causes["CFXREG"]))
    print("  PASS  cg7 位号: %r" % bits)
    print("  PASS  cfx_power cg7 块 0: desc=%#x start=%#x size=%#x attr=%#x"
          % (pw["desc"], pw["start"], pw["size"], pw["attr"]))
    if cmp_val >> 24 != 0x40:
        problems.append("cmp.uo 的 value 与 opc 0x40 不符: %#x" % cmp_val)
    else:
        print("  PASS  编码: cmp.uo value=%#010x（opc 0x40）" % cmp_val)

    path = _ARCH / "power" / "expected.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print("  FAIL  读 expected.yaml: %s" % exc)
        return 1
    entries = {c.get("id"): c for c in (doc.get("cases") or [])
               if isinstance(c, dict)}
    for case_id in CASES:
        want = expected_values(case_id)
        entry = entries.get(case_id)
        if entry is None:
            problems.append("expected.yaml 缺 %s" % case_id)
            continue
        got = [int(v) for chk in entry.get("checks") or []
               for v in chk.get("signature") or []]
        if got != want:
            problems.append("%s 的 expected.yaml 签名与现场派生不一致"
                            "（%d 槽 vs %d 槽）" % (case_id, len(got), len(want)))
        else:
            print("  PASS  %s: expected.yaml 与现场派生一致（%d 槽）"
                  % (case_id, len(want)))
        labels = slot_labels(case_id)
        if len(set(labels)) != len(labels):
            problems.append("%s 的槽标签重复" % case_id)
        for mode in CASE_MODES[case_id]:
            try:
                body, handler, _ = build_program(case_id, mode)
            except SetupError as exc:
                problems.append("%s/%s 镜像构造: %s" % (case_id, mode, exc))
                continue
            print("  PASS  %s/%s 镜像构造: body %d 字 / handler %d 字"
                  % (case_id, mode, len(body), len(handler)))

    # 覆盖点现场统计（不写死条数）：cg7 的 16 个块都必须被采样
    slots = slot_table("arch-power-001")
    sampled = {spec[3] // 4 for _, _, spec in slots
               if spec[0] == "reg" and spec[2] == 7}
    if sampled != set(range(16)):
        problems.append("cg7 空间块采样缺: %r"
                        % sorted(set(range(16)) - sampled))
    else:
        print("  PASS  cg7 空间块覆盖: 0–15（%d 个 reg 槽）"
              % sum(1 for _, _, s in slots if s[0] == "reg" and s[2] == 7))
    print("  PASS  arch-power-001 槽类型: %r"
          % sorted({spec[0] for _, _, spec in slots}))
    # 写侧覆盖点：`cfx_power_ctrl`（cg8 rc1）的「写 0 被接受」必须有一个槽，
    # 且目标就是 power 的 cg8 rc1（现场统计，不写死槽数）。
    pw = cfx_codes()["power"]
    n_wr_ok = sum(1 for _, _, s in slots
                  if s[0] == "wr_ok" and s[1] == pw and s[2] == 8 and s[3] == 1)
    if n_wr_ok < 1:
        problems.append("arch-power-001 缺 `cfx_power_ctrl` 写接受槽（cg8 rc1）")
    else:
        print("  PASS  arch-power-001 写接受槽: %d（cfx_power cg8 rc1 写 0）"
              % n_wr_ok)

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("power_vast: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("power_vast: selfcheck PASS")
    return 0


def list_cases() -> int:
    for case_id in CASES:
        want = expected_values(case_id)
        print("%s %-14s %2d 槽: %s" % (
            case_id, "/".join(CASE_MODES[case_id]), len(want),
            ", ".join("%s=%#x" % (label, value)
                      for label, value in zip(slot_labels(case_id), want))))
    return 0


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None)
    ap.add_argument("--mode", default="hmon", choices=MODES)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=None,
                    help="模拟器时限（秒）；缺省 = $DADAO_ARCH_TIMEOUT 或 %d"
                         % TIMEOUT)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--diagnose", action="store_true",
                    help="跑未纳入判据的差分探针（写 0/cg4/cg6），逐方报告")
    # `run_arch` 的多模式 driver 契约会附带这三个参数；本载体不需要。
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--cache-model", default=None)
    ap.add_argument("--cfx-access", default=None)
    args = ap.parse_args(argv)

    if args.list:
        return list_cases()
    if args.selfcheck:
        return selfcheck()
    if not args.qemu:
        print("power_vast: --qemu 必填", file=sys.stderr)
        return 2
    if args.cfx_access:
        print("power_vast: 本用例的权限准备在载体内部完成（smon 的 deleg），"
              "不接受 --cfx-access: %r" % args.cfx_access, file=sys.stderr)
        return 2
    if args.timeout is None:
        args.timeout = runlimit.timeout()
    work_root = (Path(args.work_dir).resolve() if args.work_dir
                 else Path(P.TMP_ROOT) / "power")
    try:
        if args.diagnose:
            out = diagnose(Path(args.qemu), work_root / "diagnose",
                           timeout=args.timeout)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("error") is None and out["exit_code"] == 0 else 1
        if args.only not in CASES:
            print("power_vast: 未知 case %r（允许 %s）"
                  % (args.only, list(CASES)), file=sys.stderr)
            return 2
        if args.mode not in CASE_MODES[args.only]:
            print("power_vast: %s 不允许 --mode %s（允许 %s）"
                  % (args.only, args.mode, list(CASE_MODES[args.only])),
                  file=sys.stderr)
            return 2
        work = work_root / args.only / args.mode
        result, blob = run_case(args.only, args.mode, args.qemu, work,
                                timeout=args.timeout)
    except (SetupError, runlimit.RunLimitError) as exc:
        print("power_vast: SETUP: %s" % exc, file=sys.stderr)
        return 2

    out = (Path(args.signature_out) if args.signature_out
           else work / "signature.bin")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)

    # 顶层 PASS/FAIL 行：`run_arch` 的跨引擎 `checks_equal` 按行首比对（不 strip），
    # 故这里不缩进。
    print("%-4s %-14s %-4s rc=%s modes=%r slots=%s"
          % (result["verdict"], result["case"], args.mode,
             result["exit_code"], result["observed_body_modes"],
             result["signature_slots"]))
    if result["verdict"] != "PASS":
        for p in result["problems"]:
            print("  [FAIL] %s" % p)
        print("power_vast: FAIL（%s / %s）" % (args.only, args.mode))
        return 1
    print("power_vast: PASS（%s / %s）" % (args.only, args.mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
