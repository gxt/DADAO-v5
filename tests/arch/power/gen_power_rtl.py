#!/usr/bin/env python3
"""`tests/arch/power/gen_power_rtl.py` — 由 cfx_power 探针表生成 RTL（chipyard
`WumingVastConfig`）的 `.S` 探针（`m16-testcases-016`）。

**单一真源**：探针表、寄存器编码、期望值都在 `power_vast.py`（QEMU/gem5 同一
份，含 `tools/chipyard/excp/prevcfx.S` 的检查点思路）；本生成器只把同一张表落成
RTL 可装配的汇编文本，**不新增第二条判据**。

RTL 与 QEMU/gem5 的差异只有「故障观察通道」与「运行模式」：

  * 故障：QEMU/gem5 用载体自装的 `cfx_hmon.hypv` 处理程序；RTL 用测试链固件的
    hmon（cause 在 `HMON_BASE + 0xE0`、回落点 `HMON_BASE + 0xF8`，与
    `tests/arch/umon/cfx02_regs.S` / `tools/chipyard/excp/prevcfx.S` 同一约定）；
  * 运行模式：RTL 的 BootROM 把测试体交付为 `cfx_power`（cfx63）/hypv，没有
    U/S 进入链 ⇒ `arch-power-001` 只跑一次（相当于 hmon 那个镜像）。

用法：
  gen_power_rtl.py --only arch-power-001 --out PATH
  gen_power_rtl.py --only arch-power-001            # 打到 stdout
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
        "\tset.rb rb20, HMON_BASE\t@@ 测试链固件 hmon 的异常帧槽",
        "\tset.rb rb21, abort",
        "\tst.o rb21, [rb20, 0xF8]\t@@ 任何未预期异常 ⇒ abort（fail-closed）",
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
        "\tset.rb rb20, HMON_BASE",
        "\tset.rb rb21, abort",
        "\tst.o rb21, [rb20, 0xF8]",
        "",
    ]
    for idx, (kind_label, kind, cg, rc) in enumerate(carrier.DIAG_PROBES):
        target = "%s, cg%d, rc%d" % (name[codes["power"]], cg, rc)
        lab = "d%d" % idx
        lines += [
            "\t@@ %s" % kind_label,
            "\tst.o rd0, [rb20, 0xE0]\t@@ 清固件 cause 槽（不靠残留）",
            "\tset.rb rb21, %s" % lab,
            "\tst.o rb21, [rb20, 0xF8]\t@@ 返回点 = 本探针之后",
            "\tset.rd rd5, 0",
        ]
        if kind == "wr":
            lines += ["\tset.rd rd6, 0",
                      "\tcfx2rc\t%s, rd6" % target]
        else:
            lines += ["\tcfx2rd\t%s, rd5" % target]
        lines += ["%s:" % lab,
                  "\tld.o rd6, [rb20, 0xE0]",
                  "\t__REC rd6",
                  "\t__REC rd5",
                  ""]
    lines += ["\t__TEST_END", "abort:", "\t__EXIT\t126",
              "\t__TEST_SECTIONS", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None, help="arch-power-001/002")
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
    if args.only not in carrier.CASES:
        print("gen_power_rtl: 未知 case %r（允许 %s）"
              % (args.only, list(carrier.CASES)), file=sys.stderr)
        return 2
    text = render(args.only)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
