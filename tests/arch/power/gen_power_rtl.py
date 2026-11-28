#!/usr/bin/env python3
"""`tests/arch/power/gen_power_rtl.py` — 由 cfx_power 探针表生成 RTL（chipyard
`WumingVastConfig`）的 `.S` 探针（`m16-testcases-016`）。

**单一真源**：探针表、寄存器编码、期望值都在 `power_vast.py`（QEMU/gem5 同一
份，含 `tools/chipyard/excp/prevcfx.S` 的检查点思路）；本生成器只把同一张表落成
RTL 可装配的汇编文本，**不新增第二条判据**。

RTL 与 QEMU/gem5 的差异只有「故障观察通道」与「运行模式」：

  * 故障：QEMU/gem5 用载体自装的 `cfx_hmon.hypv` 处理程序；RTL 用测试链固件的
    hmon（cause 在 hmon 数据页 `+0x00`、回落点 `+0x18`；常量 = `machine-tiny.inc`
    的 `HMON_DATA_BASE`/`HMON_FRAME_*`，与 `tests/arch/umon/cfx02_regs.S` /
    `tools/chipyard/excp/prevcfx.S` 同一约定）；
  * 运行模式：RTL 的 BootROM 把测试体交付为 `cfx_power`（cfx63）/hypv，没有
    U/S 进入链 ⇒ `arch-power-001` 只跑一次（相当于 hmon 那个镜像）。

用法：
  gen_power_rtl.py --only arch-power-001 --out PATH
  gen_power_rtl.py --only arch-power-001            # 打到 stdout
  gen_power_rtl.py --only write0                    # 写侧：写 0 接受（m16-chipyard-031）
  gen_power_rtl.py --only poweroff|hard-reset|soft-reset  # 写侧：写位 ⇒ 结束仿真
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]
_REPO = _HERE.parents[3]

for _sub in (("tools", "testcases", "arch"), ("tools", "testcases", "lib"),
             ("tests", "shared")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

CARRIER = _HERE.with_name("power_vast.py")

# `cfx_power cg8 rc1`（`DADAO-12 §4.12`，WO）的 bit0/1/2 写侧探针
# （`m16-chipyard-031`）：(名字, 写入值, RTL `io.power.action` 编码)。
# 动作编码是本实现**文档化的内部约定**（`GewuFile` 的 `power` 端口注释：
# 0 = POWEROFF、1 = HARD_RESET、2 = SOFT_RESET，bit0 优先，与 QEMU/gem5 同序），
# 只用于核对 `+verbose` 的 `WumingCore: power ... action=` 行，不是 spec 派生值。
# bit1/2 在本测试机无法真正重启 ⇒ 按 gem5 同口径「结束仿真 + harness 重启」。
POWER_ACTIONS = (
    ("poweroff", 0x1, 0),
    ("hard-reset", 0x2, 1),
    ("soft-reset", 0x4, 2),
)


def load_carrier():
    spec = importlib.util.spec_from_file_location("_arch_power_vast_gen",
                                                  CARRIER)
    if spec is None or spec.loader is None:
        raise SystemExit("gen_power_rtl: 无法加载 %s" % CARRIER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def render(case_id: str) -> str:
    carrier = load_carrier()
    table = carrier.slot_table(case_id)
    values = carrier.expected_values(case_id)
    lines = [
        "@@ 自动生成（tests/arch/power/gen_power_rtl.py；m16-testcases-016）"
        "——禁止手改。",
        "@@ 源：tests/arch/power/power_vast.py 的探针表（与 QEMU/gem5 同一份）。",
        "@@ case %s：%d 个槽，期望 %s" % (
            case_id, len(values),
            ", ".join("%s=%#x" % (label, value)
                      for label, value in zip(carrier.slot_labels(case_id),
                                              values))),
        "",
        "\t.include \"tests/inst/macros/inst_test.inc\"",
        "",
        "\t__TEST_BEGIN",
        "\tset.rb rb20, HMON_DATA_BASE\t@@ 测试链固件 hmon 的异常帧槽",
        "\tset.rb rb21, abort",
        "\tst.o rb21, [rb20, HMON_FRAME_RETURN]\t@@ 任何未预期异常 ⇒ abort（fail-closed）",
        "",
    ]
    for idx, (_, label, spec) in enumerate(table):
        lines.append("\t@@ 槽 %d：%s（期望 %#x）"
                     % (idx, label, values[idx]))
        lines.extend(carrier.slot_asm(spec, idx))
        lines.append("")
    lines += [
        "\t__TEST_END",
        "abort:",
        "\t__EXIT\t126",
        "\t__TEST_SECTIONS",
        "",
    ]
    return "\n".join(lines)


def render_diagnose() -> str:
    """未纳入判据的差分探针（写 0 / 读 cg4 / 读 cg6）：每探针两槽（cause, 值）。

    只作 `--diagnose` 的逐方报告（QEMU/gem5 与 RTL 的现状对照），不进
    `expected.yaml`（规范与实现不一致时，不拿实现现状当期望）。
    """
    carrier = load_carrier()
    codes = carrier.cfx_codes()
    name = {codes["power"]: "cfx_power", codes["hmon"]: "cfx_hmon"}
    lines = [
        "@@ 自动生成（tests/arch/power/gen_power_rtl.py --diagnose；"
        "m16-testcases-016）——禁止手改。",
        "@@ 诊断用，不参与签名判据：每探针两槽（cause, 读回值）。",
        "",
        "\t.include \"tests/inst/macros/inst_test.inc\"",
        "",
        "\t__TEST_BEGIN",
        "\tset.rb rb20, HMON_DATA_BASE",
        "\tset.rb rb21, abort",
        "\tst.o rb21, [rb20, HMON_FRAME_RETURN]",
        "",
    ]
    for idx, (kind_label, kind, cg, rc) in enumerate(carrier.DIAG_PROBES):
        target = "%s, cg%d, rc%d" % (name[codes["power"]], cg, rc)
        lab = "d%d" % idx
        lines += [
            "\t@@ %s" % kind_label,
            "\tst.o rd0, [rb20, HMON_FRAME_CAUSE_ID]\t@@ 清固件 cause 槽（不靠残留）",
            "\tset.rb rb21, %s" % lab,
            "\tst.o rb21, [rb20, HMON_FRAME_RETURN]\t@@ 返回点 = 本探针之后",
            "\tset.rd rd5, 0",
        ]
        if kind == "wr":
            lines += ["\tset.rd\trd6, 0",
                      "\tcfx2rc\t%s, rd6" % target]
        else:
            lines += ["\tcfx2rd\t%s, rd5" % target]
        lines += ["%s:" % lab,
                  "\tld.o rd6, [rb20, HMON_FRAME_CAUSE_ID]",
                  "\t__REC rd6",
                  "\t__REC rd5",
                  ""]
    lines += ["\t__TEST_END", "abort:", "\t__EXIT\t126",
              "\t__TEST_SECTIONS", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 写侧探针（`m16-chipyard-031`）：`cfx_power cg8 rc1`（WO，`DADAO-12 §4.12`）
#
# 与 QEMU/gem5 的同一场景（`power_vast.py` 的 `wr_ok` 槽 = 写 0 被接受；
# `poweroff.S` 式的「写位 ⇒ 结束仿真」）：bit0/1/2 在测试机上的约定是
# **结束仿真**，复位 = 结束 + harness 重启（gem5 `DADAO_POWER_*` 同口径）。
# 失败路径：写被拒/未结束仿真 ⇒ `abort`（`__EXIT 126`），不是静默通过。
# ---------------------------------------------------------------------------
def _probe_head(reason: str) -> list:
    return [
        "@@ 自动生成（tests/arch/power/gen_power_rtl.py；m16-chipyard-031）"
        "——禁止手改。",
        "@@ %s" % reason,
        "",
        "\t.include \"tests/inst/macros/inst_test.inc\"",
        "",
        "\t__TEST_BEGIN",
        "\tset.rb rb20, HMON_DATA_BASE",
        "\tset.rb rb21, abort",
        "\tst.o rb21, [rb20, HMON_FRAME_RETURN]\t@@ 任何意外异常 ⇒ abort（fail-closed）",
        "\tst.o rd0, [rb20, HMON_FRAME_CAUSE_ID]\t@@ 清固件 cause 槽（不靠残留）",
    ]


def render_write0() -> str:
    """写 0 被接受 + 读同一寄存器 ⇒ `CFXREG`（两槽）。

    槽 0 = 写 0 之后固件 hmon 的 cause 槽（0 = 被接受，没有 `CFXREG`）；
    槽 1 = `cfx2rd` 触发 `CFXREG` 后 cause 槽的值。与 `power_vast.py` 的
    `power_ctrl_write0_ok` 槽（QEMU/gem5）同场景。
    """
    carrier = load_carrier()
    codes = carrier.cfx_codes()
    target = "cfx_power, cg%d, rc%d" % (8, 1)
    if codes["power"] != 63:
        raise SystemExit("gen_power_rtl: cfx_power 不是 63（%r）"
                         % codes["power"])
    lines = _probe_head("写 0 被接受（WO）+ 读同一寄存器 ⇒ CFXREG。")
    lines += [
        "\tset.rd\trd6, 0",
        "\tcfx2rc\t%s, rd6\t@@ 写 0：WO 写必须被接受" % target,
        "\tld.o rd5, [rb20, HMON_FRAME_CAUSE_ID]",
        "\t__REC\trd5\t@@ 槽 0 = 0（接受）",
        "\tst.o rd0, [rb20, HMON_FRAME_CAUSE_ID]\t@@ 清 cause 槽",
        "\tset.rb rb21, read_done",
        "\tst.o rb21, [rb20, HMON_FRAME_RETURN]\t@@ 读故障的返回点",
        "\tcfx2rd\t%s, rd6\t@@ WO 读 ⇒ CFXREG" % target,
        "read_done:",
        "\tld.o rd5, [rb20, HMON_FRAME_CAUSE_ID]",
        "\t__REC\trd5\t@@ 槽 1 = CFXREG",
        "\t__TEST_END",
        "abort:",
        "\t__EXIT\t126",
        "\t__TEST_SECTIONS",
        "",
    ]
    return "\n".join(lines)


def render_power_action(name: str) -> str:
    """写 `bit0/1/2` ⇒ 仿真结束（零槽；写被接受由 `+verbose` 现场断言）。

    仿真结束由 harness 的 success 线（`io.halted`）驱动 `$finish`，所以本探针
    **不写** `__TEST_END` 之后的收尾：写被接受且动作生效 ⇒ 进程在 `+verbose`
    的 `WumingCore: power action=<n>` 之后结束（rc=0，无 SYS_EXIT）。写未被接受
    （`CFXREG`）或动作未生效时，执行流落到 `abort`（`__EXIT 126`）。
    """
    entry = next((e for e in POWER_ACTIONS if e[0] == name), None)
    if entry is None:
        raise SystemExit("gen_power_rtl: 未知动作 %r（允许 %s）"
                         % (name, [e[0] for e in POWER_ACTIONS]))
    _, value, _ = entry
    lines = _probe_head("写 bit%s ⇒ %s：结束仿真（复位 = 结束 + harness 重启）。"
                        % (("0" if value & 1 else
                            "1" if value & 2 else "2"), name))
    lines += [
        # 不写签名槽：仿真在 power 事件处结束，`__TEST_SECTIONS` 的 dump 不会执行；
        # 「body 已执行 + 写被接受」由 `+verbose` 的 cfx2 行现场断言。
        "\tset.rd\trd6, %#x" % value,
        "\tcfx2rc\tcfx_power, cg8, rc1, rd6\t@@ %s" % name,
        "\tjump\t[rb0, abort]\t@@ 未结束仿真 ⇒ fail-closed（126）",
        "abort:",
        "\t__EXIT\t126",
        "\t__TEST_END",
        "\t__TEST_SECTIONS",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None,
                    help="arch-power-001/002 或 write0 / poweroff / hard-reset "
                         "/ soft-reset")
    ap.add_argument("--diagnose", action="store_true",
                    help="渲染未纳入判据的差分探针（写 0/cg4/cg6）")
    ap.add_argument("--out", default=None, help="输出 .S（缺省 stdout）")
    args = ap.parse_args(argv)
    carrier = load_carrier()
    if args.diagnose:
        text = render_diagnose()
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    if not args.only:
        print("gen_power_rtl: --only 或 --diagnose 必填", file=sys.stderr)
        return 2
    if args.only == "write0":
        text = render_write0()
    elif args.only in [e[0] for e in POWER_ACTIONS]:
        text = render_power_action(args.only)
    elif args.only in carrier.CASES:
        text = render(args.only)
    else:
        print("gen_power_rtl: 未知 case %r（允许 %s + write0/%s）"
              % (args.only, list(carrier.CASES),
                 "/".join(e[0] for e in POWER_ACTIONS)), file=sys.stderr)
        return 2
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
