#!/usr/bin/env python3
"""`tests/arch/ptw/check_tlb.py` — arch ptw 的 scope 内驱动入口（kind: driver）。

判据与载体都在本目录：`ptw_carrier_tlb.py`（`m14-testcases-005` 的 15 条
`arch-ptw-*`、contract-tlb §11；`m16-testcases-010` 由
`tools/testcases/arch/min_rom_probe_tlb.py` 迁入）。本文件只把
「用例 id → `--only`」、引擎路径、运行期工作目录与签名流产物路径接到
`tests/arch/run_arch.py` 的驱动契约：

    check_tlb.py --only arch-ptw-002 --qemu PATH \
        [--work-dir DIR] [--signature-out PATH] [--selfcheck] [--list]

`--qemu` 可以是 `qemu-system-dadao`，也可以是 `qemu_gem5_shim.py`
（gem5 承载，`-machine kaiwu-vast` 由载体发出）。本文件不复制判据，
也不另写签名流解析器（真源 `tests/shared/signature.py`）。
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

PROBE = Path(__file__).resolve().with_name("ptw_carrier_tlb.py")


def _load_probe():
    if not PROBE.is_file():
        raise SystemExit("check_tlb: 缺件 %s（PTW/TLB 载体）" % PROBE)
    spec = importlib.util.spec_from_file_location("_arch_ptw_carrier_tlb",
                                                  PROBE)
    if spec is None or spec.loader is None:
        raise SystemExit("check_tlb: 无法加载 %s" % PROBE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # 载体自己会把 `tools/testcases/arch`（node_probe_prelude）加入 sys.path；
    # 这里补脚本目录，保证以任意 cwd 调起时相对导入路径一致。
    probe_dir = str(PROBE.parent)
    if probe_dir not in sys.path:
        sys.path.insert(0, probe_dir)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None,
                    help="case id（如 arch-ptw-002）或 id/label")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--work-dir", default=None,
                    help="运行期工作目录（缺省 = 探针默认）")
    ap.add_argument("--signature-out", default=None,
                    help="签名流文件（缺省 = 工作目录/signature.out）")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    probe = _load_probe()
    if args.work_dir:
        probe.WORKDIR = str(Path(args.work_dir))
        if not args.signature_out:
            probe.SIG_OUT = str(Path(args.work_dir) / "signature.out")
    if args.signature_out:
        signature_out = Path(args.signature_out)
        signature_out.parent.mkdir(parents=True, exist_ok=True)
        probe.SIG_OUT = str(signature_out)
    Path(probe.WORKDIR).mkdir(parents=True, exist_ok=True)

    argv = ["check_tlb.py"]
    if args.only:
        argv += ["--only", args.only]
    if args.qemu:
        argv += ["--qemu", args.qemu]
    if args.selfcheck:
        argv += ["--selfcheck"]
    if args.list:
        argv += ["--list"]
    old = sys.argv
    sys.argv = argv
    try:
        return probe.main()
    finally:
        sys.argv = old


if __name__ == "__main__":
    sys.exit(main())
