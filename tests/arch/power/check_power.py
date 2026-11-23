#!/usr/bin/env python3
"""`tests/arch/power/check_power.py` — `cfx_power`（cfx63）用例的驱动入口
（`m16-testcases-016`，`kind: driver`）。

判据与载体都在 `power_vast.py`（探针表、合约派生、镜像构造、自检）；本文件只
把 `run_arch.py` 的 driver 契约接到载体的命令行：

    check_power.py --only arch-power-001 --mode smon --qemu PATH \\
        [--work-dir DIR] [--signature-out PATH] [--selfcheck] [--list]

`--qemu` 可以是 `qemu-system-dadao`，也可以是 `qemu_gem5_shim.py`（gem5 承载）：
载体产出的 4 MiB BootROM 镜像在两种引擎上是同一份字节。

退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CARRIER = Path(__file__).resolve().with_name("power_vast.py")


def _load_carrier():
    if not CARRIER.is_file():
        raise SystemExit("check_power: 缺件 %s（power 载体）" % CARRIER)
    spec = importlib.util.spec_from_file_location("_arch_power_vast", CARRIER)
    if spec is None or spec.loader is None:
        raise SystemExit("check_power: 无法加载 %s" % CARRIER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    return _load_carrier().main()


if __name__ == "__main__":
    sys.exit(main())
