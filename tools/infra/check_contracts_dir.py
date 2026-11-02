#!/usr/bin/env python3
"""check-contracts-dir: 契约目录**顶层白名单门控**（守两处；INFRA-071t）。

背景：`INFRA-070t`（Phase A）把 `.tao/knowledge/` 顶层收拢为白名单门控
（`check_knowledge_dir.py`）；`INFRA-071t`（Phase B）把 11 份 `contract-*.md`
（人读叙述正文）迁入 **`.tao/contracts/`**，仓库根 `contracts/` 保持
**纯机器可读数据**。本门控把「两处顶层只允许既定模式」落为**机械门控**：
白名单外文件即 **FAIL**（治根），不靠人眼。

白名单（仅约束**顶层**；子目录内容不扫）：

  - `.tao/contracts/`：``contract-*.md``（人读契约正文） / ``README.md`` / **子目录**；
  - `contracts/`：``*.yaml``（机器可读合约数据） / ``README.md`` /
    ``cfx-aliases.txt``（LLVM-135t 运行时 cfx 别名表：由 spec 投影生成、
    llvm-mc/llvm-objdump 运行时读取的纯数据） / **子目录**
    ——``contract-*.md`` **不在**白名单（Phase B 已迁出 ⇒ 残留在 `contracts/` 顶层即 FAIL）。

设计要点（沿用 `check_knowledge_dir.py` 体例，`lessons §2.13`）：

  - **计数现场统计、不写死**；
  - **fail-closed**：任一目录缺失、或顶层**无任何条目**（空 ⇒ 扫描面 vacuous）⇒ 非零退出；
  - **自证命中**：每个目录须至少见到一个白名单文件，否则判「空转」FAIL。

Usage:
    python3 tools/infra/check_contracts_dir.py [--root DIR]

``--root DIR`` 检查另一棵树（默认仓库根）；白名单相对 ``<root>/.tao/contracts``
与 ``<root>/contracts``。
Exit code: 有白名单外文件 / 目录缺失 / vacuous / 空转 ⇒ 非零。
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (相对路径, 允许的 glob 模式, 允许的显式文件名) —— 两处契约目录
_ALLOWED_GLOBS_TAO_CONTRACTS = ("contract-*.md",)
_ALLOWED_GLOBS_CONTRACTS = ("*.yaml",)
_ALLOWED_FILES_TAO_CONTRACTS = ("README.md",)
# `cfx-aliases.txt`: the runtime cfx alias table (LLVM-135t) — machine-readable
# data projected from spec/, read by llvm-mc/llvm-objdump at run time.
_ALLOWED_FILES_CONTRACTS = ("README.md", "cfx-aliases.txt")

_TARGETS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (".tao/contracts", _ALLOWED_GLOBS_TAO_CONTRACTS, _ALLOWED_FILES_TAO_CONTRACTS),
    ("contracts", _ALLOWED_GLOBS_CONTRACTS, _ALLOWED_FILES_CONTRACTS),
)


def _is_allowed_file(name: str, globs: tuple[str, ...], files: tuple[str, ...]) -> bool:
    if name in files:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in globs)


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-contracts-dir — 契约目录顶层白名单门控（.tao/contracts/ + contracts/）")
    print("=" * 72)

    errors: list[str] = []
    for reldir, globs, files in _TARGETS:
        d = root / reldir
        if not d.is_dir():
            errors.append(f"目录不存在: {reldir}")
            print(f"  [{reldir}] ERROR: 目录不存在 ⇒ fail-closed")
            continue

        entries = sorted(d.iterdir())
        top_files = [e for e in entries if e.is_file()]
        top_dirs = [e for e in entries if e.is_dir()]

        allowed_seen = 0
        violations: list[str] = []
        for e in top_files:
            if _is_allowed_file(e.name, globs, files):
                allowed_seen += 1
            else:
                violations.append(e.name)

        print(f"  [{reldir}] 顶层条目总数（现场统计）: {len(entries)}"
              f"（文件 {len(top_files)} / 子目录 {len(top_dirs)}）")
        print(f"  [{reldir}] 允许 glob: {list(globs)}；允许文件: {list(files)}")
        print(f"  [{reldir}] 白名单文件命中（自证）: {allowed_seen}")

        if not entries:
            errors.append(f"{reldir}: 顶层为空 ⇒ 扫描面 vacuous")
            print(f"  [{reldir}] ERROR: 顶层为空 ⇒ 扫描面 vacuous（fail-closed）")
        elif allowed_seen == 0:
            errors.append(f"{reldir}: 未见任何白名单文件 ⇒ 门控空转")
            print(f"  [{reldir}] ERROR: 未见任何白名单文件 ⇒ 门控空转（fail-closed）")

        for name in violations:
            errors.append(f"{reldir}/{name}: 白名单外文件")
            print(f"  [{reldir}] 白名单外文件: {Path(reldir) / name}")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print("结果: PASS (两处顶层均无白名单外文件)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                        help="检查另一棵树（默认仓库根）")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-contracts-dir: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
