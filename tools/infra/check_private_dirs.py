#!/usr/bin/env python3
"""L1 gate: stale task-private directories under `.work/private/<任务号>/`
(m20-infra-005).

用户 2026-11-28 裁定：私有目录清理门控**只报警、不自动删**（module 级、L1）。

Rules:

  R1.1  扫描仓库 `.work/private/` 的**直接子目录**（`--root` 可重复，指向临时树
        自测）。目录名须为**现行**任务号 `mNN-<module>-<NNN[N]>`（允许
        `-<后缀>`，如 `<任务号>-work`）。
  R1.2  **在用任务豁免**：`.tao/tasks/**/<任务号>[-*].md` 的 `**状态**` ∈
        {`待开始`,`待验收`,`待返工`} ⇒ 视为在用，不判红（不限时龄）。
  R1.3  其余目录 **mtime > `--max-age-hours`（默认 2 h）⇒ FAIL**：非任务号名、
        任务号无任务书、任务已 `已验证`（或任何非在用状态）均按此判红，按
        `du` 体积降序列出**前 `--top`（默认 5）大**并打印陈旧总数/总体积。
  R1.4  **只报告、不删除**：本脚本从不 `rmtree`/`unlink` 任何东西（清理由
        任务收尾/主会话执行）。
  R1.5  无任何扫描根（如别的机器没有 `.work/private`）⇒ **PASS**（明确打印
        「无私有目录残留」，不 vacuous 失败）。

Exit: 0 = PASS, 1 = FAIL.  `--self-test` runs each branch's injection:
stale dir ⇒ FAIL / in-use task ⇒ exempt / verified task ⇒ FAIL / unknown task
id ⇒ FAIL / non-task name ⇒ FAIL / missing root ⇒ PASS / max-age threshold
injection ⇒ FAIL / top-N only ⇒ verified / report-only never deletes.

Usage:
    python3 tools/infra/check_private_dirs.py [--root DIR ...] [--repo DIR]
                                             [--max-age-hours H] [--top N]
                                             [--self-test]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOURS = 2.0
DEFAULT_TOP = 5

# Task-book statuses that mean "this task is in flight" ⇒ its private dir is in use.
IN_USE_STATUS = frozenset({"待开始", "待验收", "待返工"})
# 现行任务号约定 `mNN-<module>-<NNN[N]>`；`-<后缀>` 仍归属该任务。
# （`check_temp_dirs.py` 的 `^[A-Z][A-Z0-9]*-\d{3,4}[a-z]?$` 是旧约定，不复用。）
_TASK_ID = re.compile(r"^(m\d+-\w+-\d{3,4})(?:-.+)?$")
_STATUS_LINE = re.compile(r"^\*\*状态\*\*\s*[:：]\s*(.*?)\s*$")


def default_root(repo: Path) -> Path:
    return repo / ".work" / "private"


# ---------------------------------------------------------------------------
# task-book status (R1.2 in-use exemption)
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


def task_book_status(repo: Path, dir_name: str) -> tuple[str | None, str | None]:
    """目录名 ⇒（任务号, 任务书状态）；非任务号名 ⇒ (None, None)；无任务书 ⇒ (id, None)。"""
    m = _TASK_ID.match(dir_name)
    if not m:
        return None, None
    tid = m.group(1)
    tasks = repo / ".tao" / "tasks"
    for pattern in (f"{tid}-*.md", f"{tid}.md"):
        for path in sorted(tasks.rglob(pattern)):
            status = _read_status(path)
            if status is not None:
                return tid, status
    return tid, None


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

@dataclass
class Stale:
    path: Path
    age_h: float
    size_b: int
    reason: str


def dir_size(path: Path) -> int:
    try:
        proc = subprocess.run(
            ["du", "-sb", str(path)], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout.strip():
            return int(proc.stdout.split("\t")[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0


def scan_root(root: Path, max_age_h: float,
              repo: Path) -> tuple[list[Stale], list[tuple[Path, str]]]:
    """扫描根的直接子目录；返回（陈旧项, 在用豁免项），陈旧项体积降序。"""
    now = time.time()
    stale: list[Stale] = []
    exempt: list[tuple[Path, str]] = []
    for entry in os.scandir(root):
        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
            continue
        p = Path(entry.path)
        age_h = (now - entry.stat(follow_symlinks=False).st_mtime) / 3600.0
        if age_h <= max_age_h:
            continue
        tid, status = task_book_status(repo, p.name)
        if status in IN_USE_STATUS:
            exempt.append((p, status))
            continue
        if tid is None:
            reason = "目录名非现行任务号"
        elif status is None:
            reason = f"任务 {tid} 无任务书/无状态字段"
        else:
            reason = f"任务 {tid} 状态 {status}（非在用）"
        stale.append(Stale(p, age_h, dir_size(p), reason))
    stale.sort(key=lambda s: (-s.size_b, str(s.path)))
    exempt.sort(key=lambda e: str(e[0]))
    return stale, exempt


def _human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0  # type: ignore[assignment]
    return f"{n} B"


def audit(roots: list[Path], max_age_h: float, top: int,
          repo: Path = REPO_ROOT) -> int:
    print("=" * 72)
    print("check-private-dirs — 任务私有目录陈旧门控（L1；只报告不删除）")
    print("=" * 72)

    missing = [r for r in roots if not r.is_dir()]
    present = [r for r in roots if r.is_dir()]
    for r in missing:
        print(f"  无扫描根 {r}（不存在）⇒ 视为无私有目录残留")
    if not present:
        print("  结果: PASS（无 .work/private，无残留；非 vacuous 失败）")
        return 0

    errors: list[str] = []
    for root in present:
        print("-" * 72)
        print(f"  扫描根: {root}")
        try:
            stale, exempt = scan_root(root, max_age_h, repo)
            total_n = sum(1 for e in os.scandir(root)
                          if e.is_dir(follow_symlinks=False))
        except OSError as exc:
            errors.append(f"{root}: 无法扫描（{exc}）⇒ 按 FAIL 处理（fail-closed）")
            print(f"    ERROR: 无法扫描: {exc}")
            continue
        print(f"    直接子目录（现场统计）: {total_n}")
        if exempt:
            print(f"    在用任务目录（{'/'.join(sorted(IN_USE_STATUS))}）豁免: "
                  f"{len(exempt)} 个")
            for p, status in exempt[:top]:
                print(f"      E {p.name}: 状态 {status} ⇒ 视为在用")
        if stale:
            total_b = sum(s.size_b for s in stale)
            print(f"    陈旧（mtime > {max_age_h:g} h）: {len(stale)} 个 / {_human(total_b)}"
                  f"；前 {min(top, len(stale))} 大：")
            for i, s in enumerate(stale[:top], start=1):
                print(f"      L{i} {s.path.name}: {s.age_h:.1f} h / {_human(s.size_b)}"
                      f" — {s.reason}")
                errors.append(
                    f"{s.path}: 陈旧私有目录 mtime {s.age_h:.1f} h > {max_age_h:g} h"
                    f"（{_human(s.size_b)}；{s.reason}）")
        else:
            print(f"    陈旧（mtime > {max_age_h:g} h）: 0 个")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"  结果: FAIL ({len(errors)} 项)；本门控**只报告不删除**，"
              "清理由任务收尾执行")
        return 1
    print("  结果: PASS（无陈旧非在用私有目录；只报告不删除）")
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
    print("check-private-dirs --self-test（基线 PASS + 各分支注入可达 FAIL）")
    print("=" * 72)
    ok = True

    def run(roots, repo, max_age_h=2.0, top=5) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = audit(roots, max_age_h, top, repo)
        return rc, buf.getvalue()

    def case(name, rc, out, want_rc, marker) -> None:
        nonlocal ok
        good = rc == want_rc and marker in out
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: rc={rc} 期望 {want_rc} "
              f"marker={marker!r}")

    with tempfile.TemporaryDirectory(prefix="private-dirs-") as td:
        base = Path(td)
        repo = base / "repo"                       # 假任务书树（真状态字段）
        _write_task(repo, "m20-infra-910", "待验收")
        _write_task(repo, "m20-infra-911", "待返工")
        _write_task(repo, "m20-infra-912", "待开始")
        _write_task(repo, "m20-infra-913", "已验证")

        old = time.time() - 3 * 3600

        def stale_dir(root_name: str, name: str, size: int = 16) -> Path:
            root = base / root_name
            d = root / name
            d.mkdir(parents=True)
            (d / "payload.bin").write_bytes(b"x" * size)
            os.utime(d, (old, old))
            return root

        rc, out = run([base / "nope"], repo)
        case("基线① 无扫描根 ⇒ PASS（不 vacuous 失败）", rc, out, 0, "无扫描根")

        fresh_root = base / "fresh"
        fresh = fresh_root / "m20-infra-913"
        fresh.mkdir(parents=True)
        rc, out = run([fresh_root], repo)
        case("基线② 已验证但 mtime 新鲜 ⇒ PASS（未陈旧）", rc, out, 0,
             "陈旧（mtime > 2 h）: 0 个")

        empty_root = base / "empty"
        empty_root.mkdir()
        rc, out = run([empty_root], repo)
        case("基线③ 空扫描根 ⇒ PASS", rc, out, 0, "现场统计）: 0")

        rc, out = run([stale_dir("r-nontask", "scratch-dir")], repo)
        case("注入① 非任务号陈旧目录 ⇒ FAIL 指名", rc, out, 1, "scratch-dir")

        rc, out = run([stale_dir("r-unknown", "m20-infra-914")], repo)
        case("注入② 任务号无任务书 ⇒ FAIL", rc, out, 1, "m20-infra-914")

        rc, out = run([stale_dir("r-verified", "m20-infra-913")], repo)
        case("注入③ 已验证任务陈旧目录 ⇒ FAIL 指名", rc, out, 1, "m20-infra-913")

        rc, out = run([stale_dir("r-inuse", "m20-infra-910")], repo)
        case("注入④ 待验收任务陈旧目录 ⇒ 豁免 PASS", rc, out, 0,
             "状态 待验收 ⇒ 视为在用")

        rc, out = run([stale_dir("r-return", "m20-infra-911")], repo)
        case("注入⑤ 待返工任务陈旧目录 ⇒ 豁免 PASS", rc, out, 0,
             "状态 待返工 ⇒ 视为在用")

        rc, out = run([stale_dir("r-start", "m20-infra-912-work")], repo)
        case("注入⑥ 待开始任务 + `-work` 后缀 ⇒ 豁免 PASS", rc, out, 0,
             "状态 待开始 ⇒ 视为在用")

        # 阈值注入：同一新鲜目录，max-age 降到 -1 h ⇒ 必须判红。
        rc, out = run([fresh_root], repo, max_age_h=-1.0)
        case("注入⑦ max-age 阈值注入（-1 h）⇒ 已验证新鲜目录 FAIL", rc, out, 1,
             "m20-infra-913")
        rc, out = run([fresh_root], repo, max_age_h=2.0)
        case("基线④ 阈值恢复 2 h ⇒ 回绿 PASS", rc, out, 0, "结果: PASS")

        # 只列前 5 大且按体积降序（7 个陈旧目录，体积递增）。
        many = base / "many"
        for i in range(7):
            d = many / f"m20-infra-92{i}"
            d.mkdir(parents=True)
            (d / "payload.bin").write_bytes(b"x" * (1000 * (i + 1)))
            os.utime(d, (old, old))
        rc, out = run([many], repo, top=5)
        lines = [ln for ln in out.splitlines() if ln.strip().startswith("L")
                 and " h / " in ln]
        ordered = [ln.split()[1].rstrip(":") for ln in lines]
        good = (rc == 1 and len(lines) == 5 and "陈旧（mtime > 2 h）: 7 个" in out
                and ordered == ["m20-infra-926", "m20-infra-925", "m20-infra-924",
                                "m20-infra-923", "m20-infra-922"])
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  注入⑧ 只列前 5 大且按体积降序"
              f"（陈旧 7 个，列出 {len(lines)} 行: {ordered}）")

        # 只报告不删除
        still = (base / "r-nontask" / "scratch-dir").is_dir()
        ok &= still
        print(f"  {'PASS' if still else 'FAIL'}  注入⑨ 只报告不删除（目录仍在={still}）")

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, action="append", default=None,
                    help="扫描根（可重复；默认 <repo>/.work/private）")
    ap.add_argument("--repo", type=Path, default=REPO_ROOT,
                    help="取任务书状态的本仓库（默认本仓库根）")
    ap.add_argument("--max-age-hours", type=float, default=DEFAULT_HOURS,
                    help=f"陈旧阈值小时数（默认 {DEFAULT_HOURS:g}）")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP, help="列出前 N 大（默认 5）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    repo = args.repo.resolve()
    roots = ([p.resolve() for p in args.root] if args.root
             else [default_root(repo)])
    return audit(roots, args.max_age_hours, args.top, repo)


if __name__ == "__main__":
    raise SystemExit(main())
