#!/usr/bin/env python3
"""merge_fragments.py — 把分片任务的片段并入 `tests/inst.yaml` 与 `MIGRATION.md`。

背景（`tests/inst/MIGRATION.md §5.3`）：多个 `tests/inst` 任务并行时，各自只写
`tests/inst/.fragments/<任务号>.{inst.yaml,migration.md}`；本脚本由主会话在合并后
统一并入根清单与迁移台账，然后删除片段目录。

片段格式（约定，只认这三类，其它内容原样忽略）：

- `*.inst.yaml`：YAML 列表，每项字段与 `tests/inst.yaml` 相同（id/file/platforms/level/requires）。
- `*.migration.md`：含
  - `## §1 表行` —— 代码块里一行 `| <册目录>/ | <描述> | <个数> |`，按第一格替换 §1 对应行；
  - `## §6 新增小节` —— 其后文本整体追加到 `MIGRATION.md` 的 §6 末尾。

用法::

    python3 tools/testcases/inst/merge_fragments.py            # 合并并删除片段
    python3 tools/testcases/inst/merge_fragments.py --check    # 只校验，不写盘
    python3 tools/testcases/inst/merge_fragments.py --keep     # 合并但不删片段

退出码: 0 = 合并成功（或 `--check` 通过）；1 = 片段非法 / 与根清单冲突。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INST = ROOT / "tests" / "inst"
MANIFEST = ROOT / "tests" / "inst.yaml"
MIGRATION = INST / "MIGRATION.md"
FRAG = INST / ".fragments"

HEADER_END = "# 门控：make check-tests-index"


def load_manifest(path: Path) -> tuple[str, list[dict]]:
    text = path.read_text(encoding="utf-8")
    i = text.find(HEADER_END)
    if i < 0:
        raise SystemExit(f"{path}: 找不到清单头锚点 {HEADER_END!r}")
    # 头注释保留到「门控：」那行的段落末尾（其后是空行 + 列表）
    j = text.find("\n\n", i)
    header = text[: j + 2] if j > 0 else text[:i]
    body = text[j + 2 :] if j > 0 else text[i:]
    import yaml

    rows = yaml.safe_load(body) or []
    if not isinstance(rows, list):
        raise SystemExit(f"{path}: 根清单不是列表")
    return header, rows


def dump_manifest(header: str, rows: list[dict]) -> str:
    import yaml

    body = yaml.safe_dump(rows, allow_unicode=True, sort_keys=False,
                          default_flow_style=False, width=200)
    return header + body


def frag_entries(path: Path) -> list[dict]:
    import yaml

    try:
        rows = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"{path}: YAML 解析失败：{exc}")
    if not isinstance(rows, list):
        raise SystemExit(f"{path}: 片段不是列表")
    for r in rows:
        if set(r) != {"id", "file", "platforms", "level", "requires"}:
            raise SystemExit(f"{path}: 条目字段不符：{r.get('id')} -> {sorted(r)}")
        if not (ROOT / "tests" / r["file"]).exists():  # file 相对 tests/
            raise SystemExit(f"{path}: file 不存在：{r['file']}")
    return rows


def section(text: str, title: str) -> str:
    """取 `## <title>` 段落的正文（到下一个 `## ` 或文件尾）。"""
    m = re.search(rf"^## {re.escape(title)}\s*$", text, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^## ", text[start:], re.M)
    return text[start : start + nxt.start()] if nxt else text[start:]


def merge_migration(text: str, frag_text: str, frag_name: str) -> str:
    # §1 表行替换
    s1 = section(frag_text, "§1 表行")
    for line in re.findall(r"^\|.*\|\s*$", s1, re.M):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3:
            raise SystemExit(f"{frag_name}: §1 行应为 3 格：{line}")
        name = cells[0]
        pat = re.compile(rf"^\| {re.escape(name)} \|.*\|$", re.M)
        if not pat.search(text):
            raise SystemExit(f"{frag_name}: §1 找不到待替换行 {name!r}")
        text = pat.sub(line, text, count=1)
    # §6 追加
    s6 = section(frag_text, "§6 新增小节").strip("\n")
    if s6:
        anchor = "## 6. 已完成\n"
        i = text.find(anchor)
        if i < 0:
            raise SystemExit("MIGRATION.md: 找不到 `## 6. 已完成`")
        text = text[:i] + anchor + s6 + "\n\n" + text[i + len(anchor):]
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    if not FRAG.is_dir():
        print("merge_fragments: 无片段目录，无事可做")
        return 0
    frags = sorted(FRAG.glob("*.inst.yaml"))
    if not frags:
        print("merge_fragments: 无片段，无事可做")
        return 0

    header, rows = load_manifest(MANIFEST)
    by_id = {r["id"]: r for r in rows}
    added = 0
    for f in frags:
        for r in frag_entries(f):
            if r["id"] in by_id:
                if by_id[r["id"]] == r:
                    continue
                raise SystemExit(f"{f.name}: id 冲突（与根清单不同内容）：{r['id']}")
            by_id[r["id"]] = r
            added += 1
    merged = sorted(by_id.values(), key=lambda r: r["id"])

    mig = MIGRATION.read_text(encoding="utf-8")
    for f in frags:
        mf = f.with_suffix(".migration.md")
        if mf.exists():
            mig = merge_migration(mig, mf.read_text(encoding="utf-8"), mf.name)

    print(f"merge_fragments: 片段 {len(frags)} 个，新增条目 {added}，清单共 {len(merged)}")
    if args.check:
        return 0
    MANIFEST.write_text(dump_manifest(header, merged), encoding="utf-8")
    MIGRATION.write_text(mig, encoding="utf-8")
    if not args.keep:
        shutil.rmtree(FRAG)
        print("merge_fragments: 片段目录已删除")
    return 0


if __name__ == "__main__":
    sys.exit(main())
