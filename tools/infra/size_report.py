#!/usr/bin/env python3
"""组件源文件规模报告（报告型，非门控）。

规则见 ``spec/Process-01-组件补丁组织与构建编排.md``「组件源文件规模约定」节。

判据口径
--------
* **口径 A（我们新增的文件）**：整文件行数（``wc -l`` 等价，即换行符计数）。
  建议 ≤ ``--warn``（默认 1000）；> ``--warn`` 须提醒用户；> ``--split``（默认 2000）
  建议拆分。
* **口径 B（我们修改的上游文件）**：只看**我们的增量行**（``git diff --numstat``
  的 ``+`` 数），**不**以上游文件总行数计。

本工具**仅报告、不阻断**：正常报告路径**退出码恒为 0**（发现大文件不构成失败）。
仅当参数错误或无法读取 manifest 等**硬错误**时返回非零。

Usage::

    python3 tools/infra/size_report.py [--repo-root DIR] [--warn 1000] [--split 2000]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

# tools/infra/size_report.py → 仓库根
ROOT = Path(__file__).resolve().parents[2]

# 「逼近」带的宽度：默认 --warn=1000 ⇒ 逼近带 900–1000（含 1000）。
APPROACH_BAND = 100


def _git(src: Path, *args: str) -> subprocess.CompletedProcess | None:
    """在 src 工作树执行 git；OSError ⇒ None（git 缺失/非仓库）。"""
    try:
        return subprocess.run(
            ["git", "-C", str(src), *args],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None


def count_newlines(path: Path) -> int | None:
    """``wc -l`` 等价：统计文件中的换行符个数。文件不可读 ⇒ None。"""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return data.count(b"\n")


def numstat_added(src: Path, base: str, head: str, path: str) -> int | None:
    """口径 B：某路径相对 base 的增量 ``+`` 行数；非数字（如二进制 ``-``）⇒ None。"""
    proc = _git(src, "diff", "--numstat", base, head, "--", path)
    if proc is None or proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        try:
            return int(fields[0])
        except ValueError:
            return None
    return None


def scan_component(repo_root: Path, work_root: str, comp: dict) -> dict | None:
    """扫描单个组件，返回结果 dict；不可扫描 ⇒ None（附带原因由调用方打印）。"""
    name = comp.get("name", "<unnamed>")
    commit = comp.get("commit") or ""
    src = repo_root / work_root / "source" / name

    if not src.is_dir():
        print(f"  跳过：源树不存在 — {src}")
        return None
    git_dir = _git(src, "rev-parse", "--git-dir")
    if git_dir is None:
        print(f"  跳过：git 不可用 — {src}")
        return None
    if git_dir.returncode != 0:
        print(f"  跳过：非 git 仓库 — {src}")
        return None
    if not commit:
        print(f"  跳过：manifest 未锁定 commit — {name}")
        return None

    head_proc = _git(src, "rev-parse", "HEAD")
    if head_proc is None or head_proc.returncode != 0:
        print(f"  跳过：无法读取 HEAD — {src}")
        return None
    head = head_proc.stdout.strip()

    ns_proc = _git(src, "diff", "--name-status", commit, head)
    if ns_proc is None or ns_proc.returncode != 0:
        print(f"  跳过：git diff 失败 — {name} base={commit[:12]}")
        return None

    added: list[str] = []
    modified: list[str] = []
    other = 0
    for line in ns_proc.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        status = fields[0]
        letter = status[0]
        if letter in ("A", "M") and len(fields) >= 2:
            (added if letter == "A" else modified).append(fields[1])
        else:
            # rename/delete/copy 等（Process-01 §12 边界情况「待定」），暂不统计。
            other += 1

    return {
        "name": name,
        "commit": commit,
        "head": head,
        "src": src,
        "added": added,
        "modified": modified,
        "other": other,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="组件源文件规模报告（报告型，非门控）"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="仓库根目录（默认：脚本向上 2 级）",
    )
    parser.add_argument(
        "--warn", type=int, default=1000,
        help="新增文件行数提醒阈值（默认 1000）",
    )
    parser.add_argument(
        "--split", type=int, default=2000,
        help="新增文件行数建议拆分阈值（默认 2000）",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve() if args.repo_root else ROOT
    warn = args.warn
    split = args.split
    if warn < 1 or split < 1:
        parser.error("--warn / --split 必须为正整数")
    approach_low = max(1, warn - APPROACH_BAND)

    manifest_path = repo_root / "manifests" / "components.lock.toml"
    if not manifest_path.is_file():
        print(f"size-report: ERROR — manifest 不存在: {manifest_path}", file=sys.stderr)
        return 2
    try:
        with manifest_path.open("rb") as stream:
            manifest = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"size-report: ERROR — 无法解析 manifest: {exc}", file=sys.stderr)
        return 2

    work_root = manifest.get("work_root", ".work")
    components = [c for c in manifest.get("component", []) if c.get("enabled")]

    print("── 组件源文件规模报告（报告型，非门控）──")
    print(f"仓库根: {repo_root}")
    print(f"阈值: 提醒 > {warn} 行；建议拆分 > {split} 行；逼近带 {approach_low}–{warn} 行")
    print("口径 A（新增文件）= 整文件行数；口径 B（修改上游文件）= 仅我们的增量行")
    print()

    big: list[tuple[str, str, int]] = []
    approach: list[tuple[str, str, int]] = []
    split_list: list[tuple[str, str, int]] = []
    inc_big: list[tuple[str, str, int]] = []
    inc_max: tuple[str, str, int] | None = None

    for comp in components:
        result = scan_component(repo_root, work_root, comp)
        if result is None:
            continue

        name = result["name"]
        print(f"[组件] {name}  (base={result['commit'][:12]})")

        for path in result["added"]:
            count = count_newlines(result["src"] / path)
            if count is None:
                print(f"    读取失败（跳过）: {path}")
                continue
            if count > split:
                split_list.append((name, path, count))
            if count > warn:
                big.append((name, path, count))
            elif approach_low <= count <= warn:
                approach.append((name, path, count))

        for path in result["modified"]:
            inc = numstat_added(result["src"], result["commit"], result["head"], path)
            if inc is None:
                continue
            if inc > warn:
                inc_big.append((name, path, inc))
            if inc_max is None or inc > inc_max[2]:
                inc_max = (name, path, inc)

        big_c = sorted((x for x in big if x[0] == name), key=lambda x: -x[2])
        approach_c = sorted((x for x in approach if x[0] == name), key=lambda x: -x[2])
        split_c = sorted((x for x in split_list if x[0] == name), key=lambda x: -x[2])
        inc_big_c = sorted((x for x in inc_big if x[0] == name), key=lambda x: -x[2])

        print(f"  新增文件 > {warn} 行（口径 A：整文件行数）:")
        if big_c:
            for cname, path, count in big_c:
                mark = "  ⚠ 建议拆分" if count > split else ""
                print(f"    [>{warn}] {cname}  {path}  {count} 行{mark}")
        else:
            print("    （无）")
        print(f"  新增文件 {approach_low}–{warn} 行（逼近提醒）:")
        if approach_c:
            for cname, path, count in approach_c:
                print(f"    [逼近] {cname}  {path}  {count} 行")
        else:
            print("    （无）")
        print(f"  新增文件 > {split} 行（建议拆分）:")
        if split_c:
            for cname, path, count in split_c:
                print(f"    [>{split}] {cname}  {path}  {count} 行  ⚠ 建议拆分")
        else:
            print("    （无）")
        print(f"  修改上游文件的我们的增量 > {warn} 行（口径 B）:")
        if inc_big_c:
            for cname, path, inc in inc_big_c:
                print(f"    [>{warn}] {cname}  {path}  +{inc} 行")
        else:
            print("    （无）")
        if result["other"]:
            print(f"  注：另有 {result['other']} 项非 A/M 状态变更（rename/delete 等）未统计。")
        print()

    # 口径 B 最大增量对照（全局一行）
    print("── 摘要 ──")
    print(f">{warn} 行新增文件: {len(big)} 个")
    print(f">{split} 行新增文件: {len(split_list)} 个")
    print(f"修改上游文件增量 >{warn} 行: {len(inc_big)} 个")
    if inc_max is not None:
        print(f"口径 B 最大增量: {inc_max[2]} 行 ({inc_max[0]} {inc_max[1]})")
    else:
        print("口径 B 最大增量: 无")
    print()
    print(
        f"提示：新增文件 >{warn} 行须提醒用户；>{split} 行建议拆分"
        f"（非强制，不阻断 make check）。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
