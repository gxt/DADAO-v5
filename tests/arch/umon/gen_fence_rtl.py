#!/usr/bin/env python3
"""`tests/arch/umon/gen_fence_rtl.py` — 由 fence 探针表生成 RTL（chipyard
`WumingVastConfig`）的 `.S` 探针（`m16-testcases-012`）。

**单一真源**：探针表、fence 编码与期望值都在 `umon_fence.py`（QEMU/gem5 同一份），
本生成器只把同一张表落成 RTL 可装配的汇编文本，**不新增第二条判据**。

RTL 与 QEMU/gem5 的差异只有「故障观察通道」：

  * QEMU/gem5：载体自己的 hmon 处理程序把 `excp_cause_id` 写进 RAM 故障槽并
    `escape` 回 `cause_ip + 4`；
  * RTL：测试链固件的 hmon 把 `cause_id` 写 `HMON_BASE + 0xE0`、从
    `HMON_BASE + 0xF8` 取回落点（与 `tests/arch/umon/cfx02_regs.S` 同一约定）。

两种通道都记「一个 probe 一个 8 字节槽」：`0` = 未异常，`ILLI` = 异常；
生成器在故障 probe 前清零 `+0xE0`（不靠残留值），并把放行 probe 的回落点固定
指向 `abort`（意外异常 ⇒ `SYS_EXIT(126)`，不是 PASS）。

用法：
  gen_fence_rtl.py --only arch-umon-012 --out PATH
  gen_fence_rtl.py --only arch-umon-012            # 打到 stdout
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

CARRIER = _HERE.with_name("umon_fence.py")


def load_carrier():
    spec = importlib.util.spec_from_file_location("_arch_umon_fence_gen", CARRIER)
    if spec is None or spec.loader is None:
        raise SystemExit("gen_fence_rtl: 无法加载 %s" % CARRIER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def render(case_id: str) -> str:
    carrier = load_carrier()
    probes = carrier.case_probes(case_id)
    want = carrier.expected_values(probes, carrier.illi_cause())
    lines = [
        "@@ 自动生成（tests/arch/umon/gen_fence_rtl.py；m16-testcases-012）——禁止手改。",
        "@@ 源：tests/arch/umon/umon_fence.py 的探针表（与 QEMU/gem5 同一份）。",
        "@@ case %s：%d 个 probe，期望 %s" % (
            case_id, len(probes),
            ", ".join("%s=%#x" % (p[0], w) for p, w in zip(probes, want))),
        "",
        "\t.include \"tests/inst/macros/inst_test.inc\"",
        "",
        "\t__TEST_BEGIN",
        "\tset.rb rb20, HMON_BASE\t@@ 测试链固件 hmon 的异常帧槽",
        "\tset.rb rb21, abort",
        "\tst.o rb21, [rb20, 0xF8]\t@@ 放行 probe 的意外异常 ⇒ abort（fail-closed）",
        "",
    ]
    for (label, cfx, hb, pred, succ, why), expected in zip(probes, want):
        word = carrier.fence_word(cfx, hb, pred, succ)
        lines.append("\t@@ %s：cfxha=%d hb=%#x pred=%#x succ=%#x（%s）"
                     % (label, cfx, hb, pred, succ, why))
        if expected == 0:
            # 放行 probe：编码用 `.dd.t32`（hb/保留 cfxha 的静态合法性由 llvm-mc
            # 把关，这里要的是**核**的判定，故直接用契约编码值）。
            lines.append("\t.dd.t32\t%#010x\t@@ fence cfx%d, %#x"
                         % (word, cfx, (hb << 12) | (pred << 6) | succ))
            lines.append("\t__REC\trd0\t@@ 见证：执行过 fence 才写这一槽")
        else:
            lines.append("\tst.o rd0, [rb20, 0xE0]\t@@ 清固件 cause 槽（不靠残留）")
            lines.append("\tset.rb rb21, 1f")
            lines.append("\tst.o rb21, [rb20, 0xF8]")
            lines.append("\t.dd.t32\t%#010x\t@@ fence cfx%d, %#x"
                         % (word, cfx, (hb << 12) | (pred << 6) | succ))
            lines.append("1:")
            lines.append("\tld.o rd5, [rb20, 0xE0]")
            lines.append("\t__REC\trd5")
        lines.append("")
    lines += [
        "\t__TEST_END",
        "abort:",
        "\t__EXIT\t126",
        "\t__TEST_SECTIONS",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", required=True, help="arch-umon-012 / arch-umon-013")
    ap.add_argument("--out", default=None, help="输出 .S（缺省 stdout）")
    args = ap.parse_args(argv)
    carrier = load_carrier()
    if args.only not in carrier.CASES:
        print("gen_fence_rtl: 未知 case %r（允许 %s）"
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
