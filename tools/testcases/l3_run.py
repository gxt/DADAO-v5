#!/usr/bin/env python3
"""l3_run.py -- ``make check-full`` 的包装：逐成员执行 + 写机器可读报告
（TESTCASES-083t）。

报告落 ``<test-artifacts>/l3/<YYYYMMDDTHHMMSSZ>/``，三件套与夜跑同格式
（``tools/testcases/report_io.py``，``docs/Process-09 §4``/``§8``）：

    manifest.tsv   scope<TAB>suite<TAB>rc<TAB>log（逐成员一行）
    meta.json      command / started_utc / finished_utc / commit / toolchain / members
    run.log        汇总 + ``[exit marker] rc=N``

成员（= L3 的**直接**清单，``docs/Process-07 §1``；一个检查只在一层）：

* ``inst``：``check-inst``（全量）+ 4 个 FP 探针（``fp`` 身份无向量）
* ``arch``：``check-arch``（全 cfx）
* ``unit``：``check-unit-full``（= ``check-unit`` + ``check-lit-full``）
* ``tset``：``test-m6`` 的**集成**步骤（全量 lit + ir-lli + Embench E2E）；082t 后
  L3 不直接列任何 tset smoke/full，此行取 test-m6 的独有内容（Embench E2E）作
  tset 集成覆盖 —— 它不构成 tset smoke 重复（``Process-07 §4``）。

纪律
----
* **顺序执行**（一次只跑一个长任务），逐成员日志落
  ``.work/log/testcases/check-l3-<stamp>-<scope>-<suite>.log``；任一成员 rc != 0 ⇒ 整体
  rc=1，但**其余成员照跑**（一次拿到全景）。
* **同 stamp 不覆盖**：目录已存在且非空 ⇒ rc=2（``--allow-overwrite`` 显式放行）。
* 结尾打印 ``[exit marker] rc=N``；报告由 ``check-l3-report``（里程碑层）消费。

``--self-test`` 用假成员（``echo`` / ``false``）验证：全绿 ⇒ rc=0 且报告门控 PASS；
红成员 ⇒ rc=1 + manifest 记 rc + 门控 FAIL；同 stamp 重跑 ⇒ 拒绝；日志落临时目录。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import report_io

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")

# 成员 = L3 的直接清单（真源；``docs/Process-07 §1``）。
DEFAULT_MEMBERS: list[tuple[str, str, str]] = [
    ("inst", "base", "make check-inst"),
    ("inst", "fp-rnd", "make check-rnd-probe"),
    ("inst", "fp-minmax", "make check-minmax-probe"),
    ("inst", "fp-fma", "make check-fma-probe"),
    ("inst", "fp-clmul", "make check-clmul-probe"),
    ("arch", "cfx", "make check-arch"),
    ("unit", "full", "make check-unit-full"),
    # test-m6 = 集成步骤：全量 lit + ir-lli + Embench E2E；082t 后 L3 无独立 tset
    # smoke/full，此行以 Embench E2E 作 tset 集成覆盖（不算 smoke 重复）。
    ("tset", "m6-integration", "make test-m6"),
]


def parse_member(raw: str) -> tuple[str, str, str]:
    try:
        key, cmd = raw.split("=", 1)
        scope, suite = key.split(":", 1)
    except ValueError:
        raise SystemExit(f"ERROR: --member 需形如 scope:suite=cmd，得到 {raw!r}")
    if not scope or not suite or not cmd.strip():
        raise SystemExit(f"ERROR: --member 字段为空：{raw!r}")
    return scope, suite, cmd


def git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True)
    except OSError:
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def _tool_entry(path: Path) -> dict:
    """Content identity (GNU build-id, sha256 fallback) of an installed tool."""
    entry: dict = {"path": str(path)}
    if not path.is_file():
        entry["id"] = None
        return entry
    sys.path.insert(0, str(REPO_ROOT / "tools" / "infra"))
    import toolchain_id  # noqa: PLC0415

    kind, value = toolchain_id.content_id(path)
    entry["id"] = f"{kind}:{value}"
    return entry


def toolchain_summary() -> dict:
    """摘要（不 hash 整个 clang）：构建号/内容 id + 路径，缺件记 ``id=None``。"""
    sys.path.insert(0, str(REPO_ROOT / "tools" / "infra"))
    import paths  # noqa: PLC0415

    bin_dir = paths.host_toolchain_bin()
    return {
        "clang": _tool_entry(bin_dir / "clang"),
        "lld": _tool_entry(bin_dir / "ld.lld"),
        "qemu": _tool_entry(bin_dir / "qemu-system-dadao"),
        "libc": _tool_entry(paths.target_sysroot_dir() / "lib" / "libc.so"),
    }


def _manifest_log_path(log: Path) -> str:
    try:
        return str(log.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(log)


def run_l3(root: Path, stamp: str, members: list[tuple[str, str, str]],
           log_dir: Path, allow_overwrite: bool) -> int:
    report = root / "l3" / stamp
    if report.exists() and any(report.iterdir()) and not allow_overwrite:
        sys.stderr.write(
            f"check-full: FAIL — 报告目录已存在（同 stamp 不覆盖）：{report}\n"
            "  稍后重跑（stamp 精确到秒）或显式 --allow-overwrite。\n")
        return 2
    report.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    started = report_io.utc_now()
    rows: list[tuple[str, str, int, str]] = []
    for scope, suite, cmd in members:
        log = log_dir / f"check-l3-{stamp}-{scope}-{suite}.log"
        print(f"check-full: [{scope}:{suite}] $ {cmd}  (log {log})", flush=True)
        with log.open("w") as fh:
            rc = subprocess.call(["bash", "-lc", cmd], cwd=REPO_ROOT,
                                 stdout=fh, stderr=subprocess.STDOUT)
        print(f"check-full: [{scope}:{suite}] rc={rc}", flush=True)
        rows.append((scope, suite, rc, _manifest_log_path(log)))
    finished = report_io.utc_now()

    report_io.write_manifest(report, rows)
    report_io.write_meta(report, {
        "command": "make check-full",
        "started_utc": started,
        "finished_utc": finished,
        "commit": git_commit(),
        "toolchain": toolchain_summary(),
        "members": [{"scope": s, "suite": u, "cmd": c} for s, u, c in members],
    })

    failed = [f"{s}:{u}" for s, u, rc, _ in rows if rc != 0]
    overall = 1 if failed else 0
    (report / "run.log").write_text("\n".join([
        f"check-full {stamp}  ({started} .. {finished})",
        *[f"  {s}:{u}\trc={rc}\t{log}" for s, u, rc, log in rows],
        f"[exit marker] rc={overall}",
    ]) + "\n")

    total = len(rows)
    if failed:
        print(f"check-full: FAIL — {len(failed)}/{total} member(s) red: {', '.join(failed)}")
        print(f"check-full: report {report}")
        print(f"[exit marker] rc={overall}")
        return overall
    print(f"check-full: PASS ({total}/{total} member(s) green)")
    print(f"check-full: report {report}")
    print(f"[exit marker] rc={overall}")
    return overall


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def cmd_selftest(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_l3_report as report_gate  # noqa: E402

    base = Path(tempfile.mkdtemp(prefix="l3-run-selftest-",
                                 dir=args.tmp_root or "/tmp/opencode"))
    log_dir = base / "logs"
    tests_root = base / "tests"
    checks: list[tuple[str, bool, str]] = []

    # 成员日志须非空（报告门控要求），故用 `echo` 而非裸 `true`。
    green = [(s, u, "echo ok") for s, u, _ in DEFAULT_MEMBERS]
    red = [(s, u, "echo red; false" if u == "fp-fma" else "echo ok")
           for s, u, _ in DEFAULT_MEMBERS]

    rc = run_l3(tests_root, "20261027T000000Z", green, log_dir, allow_overwrite=False)
    checks.append(("green L3 => rc=0", rc == 0, f"rc={rc}"))
    rep = report_gate.check(tests_root, "20261027T000000Z", repo_root=base)
    checks.append(("green L3 => report gate PASS", not rep.errors,
                   "errors=" + ("; ".join(rep.errors)[:120] if rep.errors else "-")))

    man = (tests_root / "l3" / "20261027T000000Z" / "manifest.tsv").read_text()
    body = [ln for ln in man.splitlines()[1:] if ln.strip()]
    checks.append(("manifest has one row per member",
                   len(body) == len(DEFAULT_MEMBERS),
                   f"{len(body)} vs {len(DEFAULT_MEMBERS)}"))
    checks.append(("manifest covers four scopes",
                   len({ln.split("\t")[0] for ln in body}) >= 4,
                   str(sorted({ln.split("\t")[0] for ln in body}))))
    run_log = (tests_root / "l3" / "20261027T000000Z" / "run.log").read_text()
    checks.append(("green run.log exit marker rc=0",
                   "[exit marker] rc=0" in run_log, run_log.splitlines()[-1]))

    rc = run_l3(tests_root, "20261027T000001Z", red, log_dir, allow_overwrite=False)
    checks.append(("red member => rc=1", rc == 1, f"rc={rc}"))
    rep = report_gate.check(tests_root, "20261027T000001Z", repo_root=base)
    checks.append(("red L3 => report gate FAIL", bool(rep.errors),
                   "errors=" + ("; ".join(rep.errors)[:120] if rep.errors else "-")))
    red_rows = [ln for ln in (tests_root / "l3" / "20261027T000001Z" /
                              "manifest.tsv").read_text().splitlines()
                if "\tfp-fma\t" in ln]
    checks.append(("manifest records rc=1 for red member",
                   bool(red_rows) and red_rows[0].split("\t")[2] == "1",
                   str(red_rows)))

    rc = run_l3(tests_root, "20261027T000000Z", green, log_dir, allow_overwrite=False)
    checks.append(("same-stamp rerun refused => rc=2", rc == 2, f"rc={rc}"))

    fails = sum(0 if ok else 1 for _, ok, _ in checks)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
    print(f"l3_run --self-test: {'PASS' if fails == 0 else 'FAIL'} "
          f"({len(checks) - fails}/{len(checks)})")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"  kept: {base}")
    return 0 if fails == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L3 编排 + 报告落盘")
    ap.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"))
    ap.add_argument("--stamp", default=None, help="报告目录戳（默认 UTC 当前秒）")
    ap.add_argument("--member", action="append", default=None,
                    help="scope:suite=cmd（可重复；默认 = L3 直接清单）")
    ap.add_argument("--log-dir", default=str(REPO_ROOT / ".work" / "log" / "testcases"))
    ap.add_argument("--allow-overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--tmp-root", default=None)
    args = ap.parse_args(argv)

    if args.self_test:
        return cmd_selftest(args)

    stamp = args.stamp or report_io.utc_stamp()
    if not STAMP_RE.match(stamp):
        sys.stderr.write(f"ERROR: --stamp 必须是 YYYYMMDDTHHMMSSZ，得到 {stamp!r}\n")
        return 2
    members = [parse_member(m) for m in (args.member or
                                         [f"{s}:{u}={c}" for s, u, c in DEFAULT_MEMBERS])]
    if args.dry_run:
        print(f"check-full: DRY-RUN stamp={stamp} root={args.root} "
              f"members={len(members)}")
        for scope, suite, cmd in members:
            print(f"  {scope}:{suite}  $ {cmd}")
        return 0
    return run_l3(Path(args.root), stamp, members, Path(args.log_dir),
                  args.allow_overwrite)


if __name__ == "__main__":
    sys.exit(main())
