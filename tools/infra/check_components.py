#!/usr/bin/env python3
"""check-components: L1 组件可用性冒烟（INFRA-058t）。

L1（`make check`）= 仓库完整性 + 组件可用性；本门控只证「工具可执行且确实认识
`dadao` 目标」，**不跑被测语义**（那是 L2/L3 的事）。

三项（fail-closed，任一失败 ⇒ exit 1）：
  1. `llc`      —— 可执行，且 `--version` 的 Registered Targets 含 `dadao`；
  2. `clang`    —— 可执行，且 `--print-targets` 含 `dadao`；
  3. `qemu-system-dadao` —— 可执行，且 `-machine help` 含 `dadao-m1`。

工具路径取自 install root（ADR-0016 D9），经 `tools/infra/paths.py` 解析（D7），
不硬编码。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "infra"))
import paths as _paths  # noqa: E402

_TIMEOUT = 60


def _run_and_check(name: str, argv: list[str], needle: str) -> tuple[bool, str]:
    exe = argv[0]
    if not Path(exe).is_file():
        return False, f"{name}: 工具不存在: {exe}"
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, f"{name}: 超时 (>{_TIMEOUT}s): {' '.join(argv)}"
    except OSError as e:
        return False, f"{name}: 无法执行: {e}"
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return False, f"{name}: rc={proc.returncode} (期望 0)"
    if needle not in out:
        return False, f"{name}: 输出不含 {needle!r}"
    return True, f"{name}: OK (含 {needle!r})"


def main() -> int:
    tool_bin = _paths.host_toolchain_bin()
    checks = [
        ("llc", [str(tool_bin / "llc"), "--version"], "dadao"),
        ("clang", [str(tool_bin / "clang"), "--print-targets"], "dadao"),
        ("qemu-system-dadao", [str(tool_bin / "qemu-system-dadao"), "-machine", "help"], "dadao-m1"),
    ]

    print("check-components — L1 组件可用性冒烟")
    ok = 0
    for name, argv, needle in checks:
        passed, msg = _run_and_check(name, argv, needle)
        print(f"  [{'PASS' if passed else 'FAIL'}] {msg}")
        ok += 1 if passed else 0

    print(f"  {ok}/{len(checks)} 项通过 (计数现场统计)")
    print("-" * 72)
    if ok != len(checks):
        print(f"check-components: FAIL ({len(checks) - ok} 项失败)")
        return 1
    print("check-components: PASS (llc/clang/qemu 均可用且含 dadao)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
