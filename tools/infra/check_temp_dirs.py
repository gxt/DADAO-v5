#!/usr/bin/env python3
"""L1 gate: stale task temp directories and `/tmp` occupancy (INFRA-145t).

用户 2026-11-08 授权（逐字）：
  「/tmp目录满的问题，是临时目录没有清理，这种事情不要一再发生！同样，台账漏了的
    问题，也需要避免；不要靠记忆，而是靠规则！！！」

Rules (mechanical, no memory):

  R2.1  扫描 `$TMPDIR/opencode` 与 `/tmp/opencode` 的**直接子目录**（不用 `find` 递归）：
        排除 `git worktree list --porcelain` 列出的活动 worktree 路径（这些由任务收尾
        清理）；其余目录 **mtime 超过 `--max-age-hours`（默认 2 h）⇒ FAIL**，按 `du`
        体积降序列出**前 `--top`（默认 5）大**并打印陈旧总数/总体积。
  R2.2  根所在文件系统使用率 **> `--usage-max`（默认 70%）⇒ FAIL**（`df` 实测，
        容量现场读取、不写死）。
  R2.3  **只报告、不删除**：本脚本从不 `rmtree`/`unlink` 任何东西（现场留给收尾）。
  R2.4  无任何扫描根（如别的机器没有 `/tmp/opencode`）⇒ **PASS**（明确打印
        「无残留」，不 vacuous 失败）。

Exit: 0 = PASS, 1 = FAIL.  `--self-test` runs each branch's injection:
stale dir ⇒ FAIL / active worktree ⇒ exempt / missing root ⇒ PASS /
usage threshold ⇒ FAIL (parameter injection of the real `df` value).

Usage:
    python3 tools/infra/check_temp_dirs.py [--root DIR ...] [--repo DIR]
                                          [--max-age-hours H] [--usage-max PCT]
                                          [--top N] [--self-test]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOURS = 2.0
DEFAULT_USAGE_MAX = 70.0
DEFAULT_TOP = 5


def default_roots() -> list[Path]:
    roots = [Path("/tmp/opencode")]
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        roots.append(Path(tmpdir) / "opencode")
    out: list[Path] = []
    for r in roots:  # 去重且保序（TMPDIR=/tmp 时两处相同）
        if all(r.resolve() != o.resolve() for o in out):
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# active worktrees
# ---------------------------------------------------------------------------

def worktree_paths(repo: Path) -> tuple[list[Path], str]:
    """`git worktree list --porcelain` ⇒ 活动 worktree 路径（解析符号链接）。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], f"git 不可用（{exc.__class__.__name__}）⇒ 无排除集"
    if proc.returncode != 0:
        return [], "非 git 仓库（git worktree list 失败）⇒ 无排除集"
    paths = []
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(Path(line[len("worktree "):]).resolve())
    return paths, f"活动 worktree {len(paths)} 个"


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

@dataclass
class Stale:
    path: Path
    age_h: float
    size_b: int


def dir_size(path: Path) -> int:
    try:
        proc = subprocess.run(
            ["du", "-sb", str(path)], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout.strip():
            return int(proc.stdout.split("\t")[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0


def scan_root(root: Path, active: set[Path], max_age_h: float) -> list[Stale]:
    """扫描根的**直接子目录**；返回陈旧项（体积降序）。"""
    now = time.time()
    out: list[Stale] = []
    for entry in os.scandir(root):
        p = Path(entry.path)
        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
            continue
        real = p.resolve()
        if any(real == a or a.is_relative_to(real) or real.is_relative_to(a) for a in active):
            continue
        age_h = (now - entry.stat(follow_symlinks=False).st_mtime) / 3600.0
        if age_h > max_age_h:
            out.append(Stale(p, age_h, dir_size(p)))
    out.sort(key=lambda s: (-s.size_b, str(s.path)))
    return out


def usage_percent(path: Path) -> tuple[float, int, int]:
    total, used, _free = shutil.disk_usage(path)
    return (100.0 * used / total if total else 0.0), used, total


def _human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0  # type: ignore[assignment]
    return f"{n} B"


def audit(
    roots: list[Path],
    active: set[Path],
    max_age_h: float,
    usage_max: float,
    top: int,
    active_note: str = "",
) -> int:
    print("=" * 72)
    print("check-temp-dirs — 陈旧任务临时目录 + /tmp 占用（L1）")
    print("=" * 72)
    if active_note:
        print(f"  {active_note}")

    missing = [r for r in roots if not r.is_dir()]
    present = [r for r in roots if r.is_dir()]
    for r in missing:
        print(f"  无扫描根 {r}（不存在）⇒ 视为无残留")
    if not present:
        print("  结果: PASS（无 /tmp/opencode，无残留；非 vacuous 失败）")
        return 0

    errors: list[str] = []
    for root in present:
        print("-" * 72)
        print(f"  扫描根: {root}")
        try:
            stale = scan_root(root, active, max_age_h)
            total_n = sum(1 for e in os.scandir(root)
                          if e.is_dir(follow_symlinks=False))
        except OSError as exc:
            errors.append(f"{root}: 无法扫描（{exc}）⇒ 按 FAIL 处理（fail-closed）")
            print(f"    ERROR: 无法扫描: {exc}")
            continue
        print(f"    直接子目录（现场统计）: {total_n}；活动 worktree 排除 {len(active)} 条")
        if stale:
            total_b = sum(s.size_b for s in stale)
            print(f"    陈旧（mtime > {max_age_h:g} h）: {len(stale)} 个 / {_human(total_b)}"
                  f"；前 {min(top, len(stale))} 大：")
            for i, s in enumerate(stale[:top], start=1):
                print(f"      L{i} {s.path.name}: {s.age_h:.1f} h / {_human(s.size_b)}")
                errors.append(
                    f"{s.path}: 非活动临时目录 mtime {s.age_h:.1f} h > {max_age_h:g} h"
                    f"（{_human(s.size_b)}）")
        else:
            print(f"    陈旧（mtime > {max_age_h:g} h）: 0 个")
        pct, used, total = usage_percent(root)
        print(f"    文件系统占用: {pct:.1f}% ({_human(used)} / {_human(total)})；"
              f"阈值 > {usage_max:g}%")
        if pct > usage_max:
            errors.append(
                f"{root} 所在文件系统占用 {pct:.1f}% > {usage_max:g}%"
                f"（{_human(used)} / {_human(total)}）")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"  结果: FAIL ({len(errors)} 项)；本门控**只报告不删除**，清理由任务收尾执行")
        return 1
    print("  结果: PASS（无陈旧非活动目录；占用未超阈值；只报告不删除）")
    return 0


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    print("=" * 72)
    print("check-temp-dirs --self-test（基线 PASS + 各分支注入可达 FAIL）")
    print("=" * 72)
    ok = True

    def run(roots, active, max_age_h=2.0, usage_max=70.0, top=5, note="自检") -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = audit(roots, active, max_age_h, usage_max, top, note)
        return rc, buf.getvalue()

    def case(name, rc, out, want_rc, marker) -> None:
        nonlocal ok
        good = rc == want_rc and marker in out
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: rc={rc} 期望 {want_rc} marker={marker!r}")

    with tempfile.TemporaryDirectory(prefix="temp-dirs-") as td:
        base = Path(td)
        now_root = base / "current"          # 只有新目录
        (now_root / "INFRA-900t").mkdir(parents=True)
        old_root = base / "stale"            # 一个 3 h 前的非活动目录
        (old_root / "INFRA-900t").mkdir(parents=True)
        active_root = base / "active"        # 只含活动 worktree 的扫描根
        active = active_root / "QEMU-901t"
        active.mkdir(parents=True)
        old = time.time() - 3 * 3600
        os.utime(old_root / "INFRA-900t", (old, old))
        os.utime(active, (old, old))

        rc, out = run([base / "nope"], set())
        case("基线① 无扫描根 ⇒ PASS（不 vacuous 失败）", rc, out, 0, "无 /tmp/opencode")

        rc, out = run([now_root], set(), usage_max=100.0)
        case("基线② 无陈旧目录 ⇒ PASS", rc, out, 0, "陈旧（mtime > 2 h）: 0 个")

        rc, out = run([old_root], set(), usage_max=100.0)
        case("注入① 陈旧非活动目录 ⇒ FAIL 指名", rc, out, 1, "INFRA-900t")

        rc, out = run([active_root], {active.resolve()}, usage_max=100.0)
        case("注入② 陈旧但属活动 worktree ⇒ 排除后 PASS", rc, out, 0, "0 个")
        rc, out = run([active_root], set(), usage_max=100.0)
        case("注入③ 同一目录不在排除集 ⇒ FAIL（证明排除真的生效）", rc, out, 1, "QEMU-901t")

        pct, _u, _t = usage_percent(base)
        rc, out = run([now_root], set(), usage_max=-1.0)
        case(f"注入④ 占用阈值注入（实测 {pct:.1f}%，阈值 -1%）⇒ FAIL",
             rc, out, 1, "所在文件系统占用")
        rc, out = run([now_root], set(), usage_max=100.0)
        case("基线③ 占用阈值 100% ⇒ PASS", rc, out, 0, "结果: PASS")

        for i in range(7):
            d = base / "many" / f"TASK-90{i}t"
            d.mkdir(parents=True)
            (d / "payload.bin").write_bytes(b"x" * (i + 1))  # 体积递增，验证按体积降序
            os.utime(d, (old, old))
        rc, out = run([base / "many"], set(), usage_max=100.0, top=5)
        lines = [ln for ln in out.splitlines() if ln.strip().startswith("L")
                 and " h / " in ln]
        ordered = [ln.split()[1].rstrip(":") for ln in lines]
        good = (rc == 1 and len(lines) == 5 and "陈旧（mtime > 2 h）: 7 个" in out
                and ordered == ["TASK-906t", "TASK-905t", "TASK-904t",
                                "TASK-903t", "TASK-902t"])
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  注入⑤ 只列前 5 大且按体积降序"
              f"（陈旧 7 个，列出 {len(lines)} 行: {ordered}）")

        # 只报告不删除
        still = (old_root / "INFRA-900t").is_dir()
        ok &= still
        print(f"  {'PASS' if still else 'FAIL'}  注入⑥ 只报告不删除（目录仍在={still}）")

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, action="append", default=None,
                    help="扫描根（可重复；默认 /tmp/opencode 与 $TMPDIR/opencode）")
    ap.add_argument("--repo", type=Path, default=REPO_ROOT,
                    help="取 git worktree 列表的仓库（默认本仓库根）")
    ap.add_argument("--max-age-hours", type=float, default=DEFAULT_HOURS,
                    help=f"陈旧阈值小时数（默认 {DEFAULT_HOURS:g}）")
    ap.add_argument("--usage-max", type=float, default=DEFAULT_USAGE_MAX,
                    help=f"文件系统占用阈值百分比（默认 {DEFAULT_USAGE_MAX:g}）")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP, help="列出前 N 大（默认 5）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    roots = [p.resolve() for p in args.root] if args.root else default_roots()
    active, note = worktree_paths(args.repo)
    return audit(roots, set(active), args.max_age_hours, args.usage_max, args.top, note)


if __name__ == "__main__":
    raise SystemExit(main())
