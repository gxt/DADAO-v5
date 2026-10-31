#!/usr/bin/env python3
"""check-knowledge-dir: ``.tao/knowledge/`` 顶层白名单门控（INFRA-070t）。

背景（用户 2026-10-12 裁定）：``.tao/knowledge/`` 顶层文件过多 ⇒
「**难以发现混入新文档**」。本门控把「顶层只允许既定模式」落为**机械门控**：
**白名单外文件即 FAIL**（治根），不靠人眼。

白名单（仅约束**顶层**；子目录内容不扫）：
  - **子目录**（任意名，如 ``archive``/``refs``）——递归内容不受本门控约束；
  - **台账 / 索引集合**（显式名单 ``_ALLOWED_FILES``）。

> **Phase B 已落地（INFRA-071t，2026-10-14）**：11 份 ``contract-*.md`` 已迁入 ``.tao/contracts/``
> ⇒ 原 ``contract-*.md`` 顶层通配**作废**（``_ALLOWED_GLOBS`` 清空；``.tao/knowledge/`` 顶层
> 再出现 ``contract-*.md`` 即白名单外 ⇒ FAIL）。新落点白名单见 ``check_contracts_dir.py``。

设计要点：
  - **计数现场统计、不写死**；
  - **fail-closed**：``.tao/knowledge/`` 缺失、或顶层**无任何条目**（空 ⇒ 扫描面 vacuous）⇒ 非零退出；
  - **自证命中**：须至少见到一个白名单文件，否则判「空转」FAIL。

Usage:
    python3 tools/infra/check_knowledge_dir.py [--root DIR]

``--root DIR`` 检查另一棵树（默认仓库根）；白名单相对 ``<root>/.tao/knowledge``。
Exit code: 有白名单外文件 / 目录缺失 / vacuous ⇒ 非零。
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_REL = Path(".tao") / "knowledge"

# ── 顶层允许的**文件**（显式名单；子目录不受限）────────────────────────────────
_ALLOWED_FILES = frozenset({
    "MEMORY.md",                     # 入口指针 + 上游↔v5 偏离台账
    "issues.yaml",                   # issue 台账
    "lessons.md",                    # 教训/判据
    "milestones.md",                 # 任务流水 / 进度
    "discussing.md",                 # 讨论项 backlog（非任务流水）
    "mirrors.md",                    # 镜像/下载口径
    "project_M3-codegen-choices.md", # M3 codegen 口径台账
})

# 顶层允许的 glob 模式（空）：`contract-*.md` 已由 INFRA-071t 迁入 `.tao/contracts/`
# ⇒ 原通配作废（迁出后 `.tao/knowledge/` 顶层再出现该模式即白名单外 ⇒ FAIL）。
_ALLOWED_GLOBS: tuple[str, ...] = ()


def _is_allowed_file(name: str) -> bool:
    if name in _ALLOWED_FILES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in _ALLOWED_GLOBS)


def audit(root: Path) -> int:
    kdir = root / KNOWLEDGE_REL
    if not kdir.is_dir():
        print(f"check-knowledge-dir: ERROR: 目录不存在: {kdir}", file=sys.stderr)
        print("结果: FAIL (knowledge dir missing)")
        return 1

    entries = sorted(kdir.iterdir())
    files = [e for e in entries if e.is_file()]
    dirs = [e for e in entries if e.is_dir()]

    print("=" * 72)
    print("check-knowledge-dir — `.tao/knowledge/` 顶层白名单门控")
    print("=" * 72)
    print(f"  顶层条目总数（现场统计）: {len(entries)}  （文件 {len(files)} / 子目录 {len(dirs)}）")
    print(f"  允许文件名单: {sorted(_ALLOWED_FILES)}")
    print(f"  允许 glob:    {list(_ALLOWED_GLOBS)}")

    violations: list[str] = []
    allowed_seen = 0
    for e in files:
        if _is_allowed_file(e.name):
            allowed_seen += 1
        else:
            violations.append(e.name)

    print(f"  白名单文件命中（自证）: {allowed_seen}")

    if not entries:
        print("ERROR: `.tao/knowledge/` 顶层为空 ⇒ 扫描面 vacuous（fail-closed）", file=sys.stderr)
        print("结果: FAIL (vacuous: empty top level)")
        return 1
    if allowed_seen == 0:
        print("ERROR: 未见任何白名单文件 ⇒ 门控空转（fail-closed）", file=sys.stderr)
        print("结果: FAIL (vacuous: no allowed file seen)")
        return 1

    if violations:
        print()
        for name in violations:
            print(f"  白名单外文件: {KNOWLEDGE_REL / name}")
        print("-" * 72)
        print(f"结果: FAIL ({len(violations)} 个白名单外文件)")
        return 1

    print("-" * 72)
    print("结果: PASS (顶层无白名单外文件)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                        help="检查另一棵树（默认仓库根）")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-knowledge-dir: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
