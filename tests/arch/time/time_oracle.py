#!/usr/bin/env python3
"""`tests/arch/time/time_oracle.py` — `cfx_time`（cfxha 34）arch 用例的**唯一**
期望值来源（`m16-chipyard-023`）。

两条 case 共用本文件，三个平台（QEMU / gem5 / RTL）共用同一份槽序与期望：

  * `arch-time-001`（三模式 hmon/smon/umon，7 槽）：只读时间面 —— `time_freq`
    的读数与 RO 稳定性、`time_value` 的**单调 / 严格递增 / 增量有界**、
    `time_value` 的高位（epoch 合理性）、与 `cfx_hart cg8 rc2 cycle` 的**同基准**
    关系（`DADAO-12 §4.10` / `contract-see §3`）。**cfx34 没有中断**，本 case
    不配置/不等待任何中断（探针注释写明）。
  * `arch-time-002`（只 hmon，6 槽）：寄存器面拒绝面 —— `cg10 rc2`/`rc63`
    保留 rc 读、`rc0`/`rc1` 的 RO 写 ⇒ `CFXREG`；写被拒后 `time_freq` 不变。
    （`cg10` 上**没有** `timer_cmp`/`timer_ctrl`：`§4.10` 只定义 rc0/rc1，
    `cfx_hart §4.7` 才是 per-hart 比较/中断。）

## 判据来源（现场派生，不从实现反推）

  * `cfx_time` 的 cfxha（34）：`spec/DADAO-12 §1` 的 cfxha 表；
  * `cg = 10`、`rc0 = freq`、`rc1 = value` 与两行的 **RO** 属性：
    `spec/DADAO-12 §4.10` 的专有寄存器表；
  * `time_freq = 1_000_000_000`（1 GHz ⇒ 1 count = 1 ns）与「复位后从 0 起算」、
    「`cycle` 与之同基准、单 hart 下读数相等」：`.tao/contracts/contract-see.md §3`；
  * 「per-system、不产生中断」：`spec/DADAO-12 §4.10` 正文；
  * `CFXREG = 1 << 2`：`spec/DADAO-12 §3.6` / `contract-see §6.1`；
  * 运行模式编码（user/jail/supv/hypv = 0/1/2/3）：`spec/Kaiwu §7.1`。

动态量（本文件的 :func:`check_time_value`）：`time_value` 的读数本身随机器
时间变化，不能写进 `expected.yaml` 的静态槽；因此**槽里只放静态谓词**（0/1
或契约常量），而「单调 / 严格递增 / 增量有界 / 同基准」的**原始读数和更紧的
上限**由各平台驱动从自己的观测面复核（RTL 从 `+verbose` 的 `cfx2 ... data=`
逐条复核，见 `check_time_rtl.py`）。
"""

from __future__ import annotations

import pathlib
import re

SPEC = "spec/DADAO-12-SEE-主管系统运行环境.md"
KAIWU = "spec/Kaiwu-测试机运行环境.md"
CONTRACT = ".tao/contracts/contract-see.md"

CASES = ("arch-time-001", "arch-time-002")
MODES = ("hmon", "smon", "umon")
CASE_MODES = {
    "arch-time-001": ("hmon", "smon", "umon"),
    "arch-time-002": ("hmon",),
}

# 「增量有界」的判据界（探针里也用它）：两次读数的高 32 位差 ∈ {0,1}
# ⇒ delta < 2^33（≈8.6 s）。真实间隔是数百~数万 count（探针隔约 900 条指令），
# 该界只用来抓「计数器跳到完全不同的量级」；探针内部的相对界见
# `check_time_rtl.py` 的原始读数复核（< 2^32）。
DELTA_HI_WINDOW = 2


class OracleError(Exception):
    pass


def _read(root, rel):
    path = pathlib.Path(root) / rel
    if not path.is_file():
        raise OracleError("missing %s" % rel)
    return path.read_text(encoding="utf-8")


def facts(root=".") -> dict:
    """从 spec/contract 现场解析 `cfx_time` 的整份寄存器面与语义常量。"""
    spec = _read(root, SPEC)
    contract = _read(root, CONTRACT)
    kaiwu = _read(root, KAIWU)

    # cfxha（`§1` 的 cfx 表）。
    m = re.search(r"^\|\s*(\d+)\s*\|\s*time\s*\|", spec, re.M)
    if not m:
        raise OracleError("spec §1: `time` row not found")
    time_ha = int(m.group(1))
    m = re.search(r"^\|\s*(\d+)\s*\|\s*hart\s*\|", spec, re.M)
    if not m:
        raise OracleError("spec §1: `hart` row not found")
    hart_ha = int(m.group(1))

    # `§4.10` 的专有寄存器表：cg / rc / 访问属性。
    section = spec.split("### 4.10", 1)
    if len(section) != 2:
        raise OracleError("spec §4.10 (cfx_time) not found")
    body = section[1].split("### 4.11", 1)[0]
    rows = {}
    for name in ("freq", "value"):
        m = re.search(
            r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*time %s\s*\|\s*cfx_time_%s\s*\|"
            r"[^|]*\|\s*([A-Z]+)\s*\|" % (name, name), body, re.M)
        if not m:
            raise OracleError("spec §4.10: `time %s` row not found" % name)
        rows[name] = {"cg": int(m.group(1)), "rc": int(m.group(2)),
                      "access": m.group(3)}
    if rows["freq"]["cg"] != rows["value"]["cg"]:
        raise OracleError("spec §4.10: freq/value are in different cg")
    for name, row in rows.items():
        if row["access"] != "RO":
            raise OracleError("spec §4.10: `time %s` must be RO, got %r"
                              % (name, row["access"]))
    # 只定义 rc0/rc1；`§4.10` 没有 `timer_cmp`/`timer_ctrl`（那是 `§4.7`），
    # 也没有任何 `1<<N` 的中断 cause。
    if "timer_cmp" in body or "timer_ctrl" in body:
        raise OracleError("spec §4.10: cfx_time must not define a timer")
    if not re.search(r"不产生中断", body):
        raise OracleError("spec §4.10: 'no interrupt' sentence missing")

    # `contract-see §3`：频率/单位/epoch/与 `cycle` 的关系。
    m = re.search(r"cg10 rc0 = cfx_time_freq = ([0-9][0-9_]*)", contract)
    if not m:
        raise OracleError("contract-see §3: cfx_time_freq value not found")
    freq_hz = int(m.group(1).replace("_", ""))
    if freq_hz != 1000000000:
        raise OracleError("contract-see §3: expected the 1 GHz test-machine "
                          "convention, got %d" % freq_hz)
    if "1 count = 1 ns" not in contract:
        raise OracleError("contract-see §3: '1 count = 1 ns' missing")
    if not re.search(r"复位后从 0 起算", contract):
        raise OracleError("contract-see §3: epoch (reset from 0) missing")
    if not re.search(r"与 `cfx_time_value` 同基准", contract):
        raise OracleError("contract-see §3: cycle/time same-base sentence "
                          "missing")
    # cfx_hart 的同基准计数器：`cg8 rc0 = hart_id` 那一段里的 ``rc2 = cycle``。
    m = re.search(r"`cg8 rc0 = hart_id = 0`.*?`rc2 = cycle`", contract, re.S)
    if not m:
        raise OracleError("contract-see §3: cfx_hart `rc2 = cycle` row missing")

    # `CFXREG = 1 << 2`（`§3.6` / `§6.1`）。
    m = re.search(r"`1 << (\d+)`\s*\|\s*`CFXREG`", contract)
    if not m:
        raise OracleError("contract-see §6.1: CFXREG bit not found")
    cfxreg = 1 << int(m.group(1))

    # 运行模式编码（`spec/Kaiwu §7.1`）。
    m = re.search(r"`bit5:4` 为运行模式——`user`=`(\d+)`、`jail`=`(\d+)`、"
                  r"`supv`=`(\d+)`、`hypv`=`(\d+)`", kaiwu)
    if not m:
        raise OracleError("spec/Kaiwu §7.1: mode encoding sentence not found")
    modes = dict(zip(("user", "jail", "supv", "hypv"),
                     (int(g, 2) for g in m.groups())))

    return {"time": time_ha, "hart": hart_ha, "cg": rows["freq"]["cg"],
            "freq_rc": rows["freq"]["rc"], "value_rc": rows["value"]["rc"],
            "freq_hz": freq_hz, "cfxreg": cfxreg, "modes": modes}


# ---------------------------------------------------------------------------
# 槽序（探针 `SIGUPD` 顺序 == 这里的顺序）
# ---------------------------------------------------------------------------
SLOTS = {
    # 三模式：只读时间面（无异常 ⇒ 三模式同一份槽序）。
    "arch-time-001": (
        "time_freq",
        "time_freq_reread",
        "time_monotonic",
        "time_strictly_increasing",
        "time_delta_bounded",
        "time_high_bit_clear",
        "cycle_same_base",
    ),
    # 只 hmon：保留 rc / RO 写的拒绝面 + 写被拒后 freq 不变。
    "arch-time-002": (
        "time_freq",
        "cfxreg_rc2_cause",
        "cfxreg_rc63_cause",
        "cfxreg_write_rc0_cause",
        "cfxreg_write_rc1_cause",
        "time_freq_after_rejected_write",
    ),
}


def slot_labels(case_id: str) -> tuple:
    if case_id not in SLOTS:
        raise OracleError("unknown case %r" % (case_id,))
    return SLOTS[case_id]


def expected(case_id: str, root=".") -> list:
    """静态期望（槽里只有契约常量与谓词的真值 1/0）。"""
    f = facts(root)
    if case_id == "arch-time-001":
        # 谓词由探针从实测读数算出（单调 / 严格增 / 增量有界 / 高位 0 /
        # 同基准）；正确的机器上它们全为 1。
        return [f["freq_hz"], f["freq_hz"], 1, 1, 1, 1, 1]
    if case_id == "arch-time-002":
        return [f["freq_hz"], f["cfxreg"], f["cfxreg"], f["cfxreg"],
                f["cfxreg"], f["freq_hz"]]
    raise OracleError("unknown case %r" % (case_id,))


def mode_code(f: dict, mode: str) -> int:
    name = {"hmon": "hypv", "smon": "supv", "umon": "user"}[mode]
    return f["modes"][name]


def check_time_value(t0: int, t1: int, cycle: int, t2: int) -> list:
    """原始读数的独立复核（RTL 从 trace 取；其余平台由驱动取同源值）。

    返回问题列表（空 = 通过）。判据全部来自契约：
      * 单调：`t1 >= t0`；
      * 严格递增：`t1 > t0`（隔了约 900 条指令，任何真实计数器都会前进）；
      * 增量有界：`0 < t1 - t0 < 2^32`（同一量级，不是跳到垃圾值）；
      * epoch 合理：`t0 < 2^63`（高位置 0，排除符号/垃圾值）；
      * 同基准：`cycle >= t2` 且 `cycle - t2 < 2^32`（`contract-see §3`：
        `cycle` 与 `time_value` 同基准、1 count = 1 ns）。
    """
    problems = []
    if not (t1 >= t0):
        problems.append("time_value 不单调: t0=%#x t1=%#x" % (t0, t1))
    if not (t1 > t0):
        problems.append("time_value 未严格递增（隔约 900 条指令仍不动）: "
                        "t0=%#x t1=%#x" % (t0, t1))
    delta = (t1 - t0) & ((1 << 64) - 1)
    if not (0 < delta < (1 << 32)):
        problems.append("time_value 增量不合理: delta=%#x（期望 0 < d < 2^32）"
                        % delta)
    if not (t0 < (1 << 63)):
        problems.append("time_value 高位为 1（epoch 不合理）: t0=%#x" % t0)
    if not (cycle >= t2):
        problems.append("cfx_hart cycle 早于 cfx_time: cycle=%#x t2=%#x"
                        % (cycle, t2))
    elif (cycle - t2) >= (1 << 32):
        problems.append("cycle 与 time_value 不同基准: cycle-t2=%#x"
                        % (cycle - t2))
    return problems
