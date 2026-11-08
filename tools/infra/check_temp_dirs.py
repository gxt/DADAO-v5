#!/usr/bin/env python3
"""L1 gate: stale task temp directories, stale large files, `/tmp` occupancy
(INFRA-145t / INFRA-146t).

用户 2026-11-08 授权（逐字）：
  「/tmp目录满的问题，是临时目录没有清理，这种事情不要一再发生！同样，台账漏了的
    问题，也需要避免；不要靠记忆，而是靠规则！！！」

Rules (mechanical, no memory):

  R2.1  扫描 `$TMPDIR/opencode` 与 `/tmp/opencode` 的**直接子目录**（不用 `find` 递归）：
        排除 `git worktree list --porcelain` 列出的活动 worktree 路径（这些由任务收尾
        清理）。**在用任务豁免**（R2 收紧口径，INFRA-146t）：目录名以任务号开头
        （`^[A-Z][A-Z0-9]*-\\d{3,4}[a-z]?`，允许 `-<后缀>` 如 `<任务号>-work`）且
        `.tao/tasks/**` 里对应任务书 `**状态**` ∈ {`待开始`,`待验收`,`待返工`}
        ⇒ 视为在用、不判红。其余目录（任务书 `已验证`、任务号不存在、非任务号名）
        **mtime 超过 `--max-age-hours`（默认 2 h）⇒ FAIL**，按 `du` 体积降序列出
        **前 `--top`（默认 5）大**并打印陈旧总数/总体积。
  R2.2  根所在文件系统使用率 **> `--usage-max`（默认 70%）⇒ FAIL**（`df` 实测，
        容量现场读取、不写死）。
  R2.3  **陈旧大文件**（F2，INFRA-146t）：扫描根**直接子文件**中 size >
        `--large-file-mib`（默认 100 MiB）且 mtime > `--max-age-hours` 者，
        先列清单（前 `--top` 大）再计入 FAIL。
  R2.4  **只报告、不删除**：本脚本从不 `rmtree`/`unlink` 任何东西（现场留给收尾）。
  R2.5  无任何扫描根（如别的机器没有 `/tmp/opencode`）⇒ **PASS**（明确打印
        「无残留」，不 vacuous 失败）。

Exit: 0 = PASS, 1 = FAIL.  `--self-test` runs each branch's injection:
stale dir ⇒ FAIL / active worktree ⇒ exempt / in-use task ⇒ exempt /
verified task ⇒ FAIL / unknown task id ⇒ FAIL / non-task name ⇒ FAIL /
stale large file ⇒ FAIL / missing root ⇒ PASS / usage threshold ⇒ FAIL
(parameter injection of the real `df` value).

Usage:
    python3 tools/infra/check_temp_dirs.py [--root DIR ...] [--repo DIR]
                                          [--max-age-hours H] [--usage-max PCT]
                                          [--large-file-mib MiB] [--top N]
                                          [--self-test]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOURS = 2.0
DEFAULT_USAGE_MAX = 70.0
DEFAULT_LARGE_MIB = 100.0
DEFAULT_TOP = 5

# Task-book statuses that mean "this task is in flight" ⇒ its scratch dir is in use.
IN_USE_STATUS = frozenset({"待开始", "待验收", "待返工"})
# Task-number prefix; `-<suffix>` (e.g. `<id>-work`) still belongs to that task.
_TASK_ID = re.compile(r"^([A-Z][A-Z0-9]*-\d{3,4}[a-z]?)(?:-.*)?$")
_STATUS_LINE = re.compile(r"^\*\*状态\*\*\s*[:：]\s*(.*?)\s*$")


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
# task-book status (R2.1 in-use exemption)
# ---------------------------------------------------------------------------

def _read_status(path: Path) -> str | None:
    """任务书的 `**状态**：<值>`（去掉反引号/空白）；无则 None。"""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for _ in range(40):
                line = fh.readline()
                if not line:
                    break
                m = _STATUS_LINE.match(line.rstrip("\n"))
                if m:
                    return m.group(1).strip().strip("`").strip() or None
    except OSError:
        return None
    return None


def task_book_status(repo: Path, dir_name: str) -> str | None:
    """目录名 ⇒ 对应任务书状态；非任务号名或任务书不存在 ⇒ None。"""
    m = _TASK_ID.match(dir_name)
    if not m:
        return None
    tid = m.group(1)
    tasks = repo / ".tao" / "tasks"
    for pattern in (f"*/{tid}-*.md", f"*/{tid}.md"):
        for path in sorted(tasks.glob(pattern)):
            status = _read_status(path)
            if status is not None:
                return status
    return None


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


def scan_root(root: Path, active: set[Path], max_age_h: float,
              repo: Path) -> tuple[list[Stale], list[tuple[Path, str]]]:
    """扫描根的**直接子目录**；返回（陈旧项, 在用豁免项），陈旧项体积降序。"""
    now = time.time()
    stale: list[Stale] = []
    exempt: list[tuple[Path, str]] = []
    for entry in os.scandir(root):
        p = Path(entry.path)
        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
            continue
        real = p.resolve()
        if any(real == a or a.is_relative_to(real) or real.is_relative_to(a) for a in active):
            continue
        age_h = (now - entry.stat(follow_symlinks=False).st_mtime) / 3600.0
        if age_h <= max_age_h:
            continue
        status = task_book_status(repo, p.name)
        if status in IN_USE_STATUS:
            exempt.append((p, status))
            continue
        stale.append(Stale(p, age_h, dir_size(p)))
    stale.sort(key=lambda s: (-s.size_b, str(s.path)))
    exempt.sort(key=lambda e: str(e[0]))
    return stale, exempt


def scan_large_files(root: Path, max_age_h: float, min_bytes: int) -> list[Stale]:
    """扫描根**直接子文件**中的陈旧大文件（R2.3）；体积降序。"""
    now = time.time()
    out: list[Stale] = []
    for entry in os.scandir(root):
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if not entry.is_file(follow_symlinks=False):
            continue
        age_h = (now - st.st_mtime) / 3600.0
        if age_h > max_age_h and st.st_size > min_bytes:
            out.append(Stale(Path(entry.path), age_h, st.st_size))
    out.sort(key=lambda s: (-s.size_b, str(s.path)))
    return out


def scan_staging_files(root: Path) -> list[Path]:
    """节点交互中转文件（bundle 等）**无论时龄**都不得留在临时根（AGENTS「节点交互不走 /tmp」）。"""
    out: list[Path] = []
    try:
        entries = list(os.scandir(root))
    except OSError:
        return out
    for entry in entries:
        if not entry.is_file(follow_symlinks=False):
            continue
        name = entry.name
        if name.endswith(".bundle") or ".bundle." in name:
            out.append(Path(entry.path))
    out.sort()
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
    repo: Path = REPO_ROOT,
    large_mib: float = DEFAULT_LARGE_MIB,
    active_note: str = "",
) -> int:
    print("=" * 72)
    print("check-temp-dirs — 陈旧任务临时目录 / 陈旧大文件 + /tmp 占用（L1）")
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

    large_bytes = int(large_mib * 1024 * 1024)
    errors: list[str] = []
    for root in present:
        print("-" * 72)
        print(f"  扫描根: {root}")
        try:
            stale, exempt = scan_root(root, active, max_age_h, repo)
            total_n = sum(1 for e in os.scandir(root)
                          if e.is_dir(follow_symlinks=False))
        except OSError as exc:
            errors.append(f"{root}: 无法扫描（{exc}）⇒ 按 FAIL 处理（fail-closed）")
            print(f"    ERROR: 无法扫描: {exc}")
            continue
        print(f"    直接子目录（现场统计）: {total_n}；活动 worktree 排除 {len(active)} 条")
        if exempt:
            print(f"    在用任务目录（{ '/'.join(sorted(IN_USE_STATUS)) }）豁免: "
                  f"{len(exempt)} 个")
            for p, status in exempt[:top]:
                print(f"      E {p.name}: 状态 {status} ⇒ 视为在用")
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
        try:
            big = scan_large_files(root, max_age_h, large_bytes)
        except OSError as exc:
            errors.append(f"{root}: 无法扫描大文件（{exc}）⇒ 按 FAIL 处理（fail-closed）")
            print(f"    ERROR: 无法扫描大文件: {exc}")
            big = []
        if big:
            print(f"    陈旧大文件（> {large_mib:g} MiB 且 mtime > {max_age_h:g} h）:"
                  f" {len(big)} 个；清单：")
            for i, s in enumerate(big[:top], start=1):
                print(f"      F{i} {s.path.name}: {s.age_h:.1f} h / {_human(s.size_b)}")
                errors.append(
                    f"{s.path}: 陈旧大文件 {_human(s.size_b)} > {large_mib:g} MiB"
                    f"，mtime {s.age_h:.1f} h > {max_age_h:g} h")
        else:
            print(f"    陈旧大文件（> {large_mib:g} MiB 且 mtime > {max_age_h:g} h）: 0 个")
        staging = scan_staging_files(root)
        if staging:
            print(f"    节点交互中转文件（不得放临时根）: {len(staging)} 个")
            for p in staging[:top]:
                print(f"      S {p.name}")
                errors.append(
                    f"{p}: 节点交互中转文件不得放 `/tmp`（tmpfs 耗光会断任务链；"
                    "bundle 等应放 .work/ 或节点持久路径）")
        else:
            print("    节点交互中转文件（不得放临时根）: 0 个")
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
    print("  结果: PASS（无陈旧非活动目录/大文件；占用未超阈值；只报告不删除）")
    return 0


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _write_task(repo: Path, tid: str, status: str) -> None:
    tasks = repo / ".tao" / "tasks" / "selftest"
    tasks.mkdir(parents=True, exist_ok=True)
    (tasks / f"{tid}-selftest.md").write_text(
        f"# {tid}\n\n**状态**：{status}\n", encoding="utf-8")


def self_test() -> int:
    print("=" * 72)
    print("check-temp-dirs --self-test（基线 PASS + 各分支注入可达 FAIL）")
    print("=" * 72)
    ok = True

    def run(roots, active, repo, max_age_h=2.0, usage_max=70.0, top=5,
            large_mib=DEFAULT_LARGE_MIB, note="自检") -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = audit(roots, active, max_age_h, usage_max, top, repo,
                       large_mib, note)
        return rc, buf.getvalue()

    def case(name, rc, out, want_rc, marker) -> None:
        nonlocal ok
        good = rc == want_rc and marker in out
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: rc={rc} 期望 {want_rc} marker={marker!r}")

    with tempfile.TemporaryDirectory(prefix="temp-dirs-") as td:
        base = Path(td)
        repo = base / "repo"                       # 假任务书树（真状态字段）
        _write_task(repo, "INFRA-910t", "待验收")
        _write_task(repo, "INFRA-911t", "已验证")
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

        rc, out = run([base / "nope"], set(), repo)
        case("基线① 无扫描根 ⇒ PASS（不 vacuous 失败）", rc, out, 0, "无 /tmp/opencode")

        rc, out = run([now_root], set(), repo, usage_max=100.0)
        case("基线② 无陈旧目录 ⇒ PASS", rc, out, 0, "陈旧（mtime > 2 h）: 0 个")

        rc, out = run([old_root], set(), repo, usage_max=100.0)
        case("注入① 陈旧非活动目录 ⇒ FAIL 指名", rc, out, 1, "INFRA-900t")

        rc, out = run([active_root], {active.resolve()}, repo, usage_max=100.0)
        case("注入② 陈旧但属活动 worktree ⇒ 排除后 PASS", rc, out, 0, "0 个")
        rc, out = run([active_root], set(), repo, usage_max=100.0)
        case("注入③ 同一目录不在排除集 ⇒ FAIL（证明排除真的生效）", rc, out, 1, "QEMU-901t")

        pct, _u, _t = usage_percent(base)
        rc, out = run([now_root], set(), repo, usage_max=-1.0)
        case(f"注入④ 占用阈值注入（实测 {pct:.1f}%，阈值 -1%）⇒ FAIL",
             rc, out, 1, "所在文件系统占用")
        rc, out = run([now_root], set(), repo, usage_max=100.0)
        case("基线③ 占用阈值 100% ⇒ PASS", rc, out, 0, "结果: PASS")

        for i in range(7):
            d = base / "many" / f"TASK-90{i}t"
            d.mkdir(parents=True)
            (d / "payload.bin").write_bytes(b"x" * (i + 1))  # 体积递增，验证按体积降序
            os.utime(d, (old, old))
        rc, out = run([base / "many"], set(), repo, usage_max=100.0, top=5)
        lines = [ln for ln in out.splitlines() if ln.strip().startswith("L")
                 and " h / " in ln]
        ordered = [ln.split()[1].rstrip(":") for ln in lines]
        good = (rc == 1 and len(lines) == 5 and "陈旧（mtime > 2 h）: 7 个" in out
                and ordered == ["TASK-906t", "TASK-905t", "TASK-904t",
                                "TASK-903t", "TASK-902t"])
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  注入⑤ 只列前 5 大且按体积降序"
              f"（陈旧 7 个，列出 {len(lines)} 行: {ordered}）")

        # R2 收紧口径（INFRA-146t）：任务书状态决定任务号目录是否在用。
        def stale_dir(name: str) -> Path:
            root = base / f"r-{name}"
            d = root / name
            d.mkdir(parents=True)
            os.utime(d, (old, old))
            return root

        rc, out = run([stale_dir("INFRA-910t")], set(), repo, usage_max=100.0)
        case("注入⑥ 待验收任务目录 >2h ⇒ 豁免 PASS（新口径）",
             rc, out, 0, "状态 待验收 ⇒ 视为在用")
        rc, out = run([stale_dir("INFRA-911t")], set(), repo, usage_max=100.0)
        case("注入⑦ 已验证任务目录 >2h ⇒ FAIL", rc, out, 1, "INFRA-911t")
        rc, out = run([stale_dir("INFRA-912t")], set(), repo, usage_max=100.0)
        case("注入⑧ 任务号不存在 ⇒ FAIL", rc, out, 1, "INFRA-912t")
        rc, out = run([stale_dir("scratch-dir")], set(), repo, usage_max=100.0)
        case("注入⑨ 非任务号目录 >2h ⇒ FAIL", rc, out, 1, "scratch-dir")
        work_root = base / "r-work"
        (work_root / "INFRA-910t-work").mkdir(parents=True)
        os.utime(work_root / "INFRA-910t-work", (old, old))
        rc, out = run([work_root], set(), repo, usage_max=100.0)
        case("注入⑩ <在跑任务号>-work 目录 >2h ⇒ 豁免 PASS", rc, out, 0, "视为在用")

        # F2 陈旧大文件（1 MiB 稀疏文件；阈值注入 1 MiB）
        large_root = base / "large"
        large_root.mkdir(parents=True)
        bigf = large_root / "dump.bin"
        with bigf.open("wb") as fh:
            fh.seek(2 * 1024 * 1024 - 1)
            fh.write(b"\0")                     # 稀疏，快且省盘
        os.utime(bigf, (old, old))
        rc, out = run([large_root], set(), repo, usage_max=100.0, large_mib=1.0)
        case("注入⑪ 陈旧大文件 > 阈值 ⇒ FAIL 并列清单", rc, out, 1,
             "陈旧大文件（> 1 MiB")
        os.utime(bigf, None)                    # 新鲜 ⇒ 不报
        rc, out = run([large_root], set(), repo, usage_max=100.0, large_mib=1.0)
        case("基线④ 大文件但 mtime 新鲜 ⇒ PASS", rc, out, 0,
             "陈旧大文件（> 1 MiB 且 mtime > 2 h）: 0 个")
        os.utime(bigf, (old, old))
        rc, out = run([large_root], set(), repo, usage_max=100.0, large_mib=4.0)
        case("基线⑤ 陈旧但低于体积阈值 ⇒ PASS", rc, out, 0, "陈旧大文件（> 4 MiB")
        bigf.unlink()
        rc, out = run([large_root], set(), repo, usage_max=100.0, large_mib=1.0)
        case("注入⑫ 删除大文件 ⇒ 回绿 PASS", rc, out, 0,
             "陈旧大文件（> 1 MiB 且 mtime > 2 h）: 0 个")

        # 只报告不删除
        still = (old_root / "INFRA-900t").is_dir()
        ok &= still
        print(f"  {'PASS' if still else 'FAIL'}  注入⑬ 只报告不删除（目录仍在={still}）")

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, action="append", default=None,
                    help="扫描根（可重复；默认 /tmp/opencode 与 $TMPDIR/opencode）")
    ap.add_argument("--repo", type=Path, default=REPO_ROOT,
                    help="取 git worktree 列表与任务书状态的本仓库（默认本仓库根）")
    ap.add_argument("--max-age-hours", type=float, default=DEFAULT_HOURS,
                    help=f"陈旧阈值小时数（默认 {DEFAULT_HOURS:g}）")
    ap.add_argument("--usage-max", type=float, default=DEFAULT_USAGE_MAX,
                    help=f"文件系统占用阈值百分比（默认 {DEFAULT_USAGE_MAX:g}）")
    ap.add_argument("--large-file-mib", type=float, default=DEFAULT_LARGE_MIB,
                    help=f"陈旧大文件体积阈值 MiB（默认 {DEFAULT_LARGE_MIB:g}）")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP, help="列出前 N 大（默认 5）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    roots = [p.resolve() for p in args.root] if args.root else default_roots()
    active, note = worktree_paths(args.repo)
    return audit(roots, set(active), args.max_age_hours, args.usage_max,
                 args.top, args.repo.resolve(), args.large_file_mib, note)


if __name__ == "__main__":
    raise SystemExit(main())
