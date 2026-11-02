#!/usr/bin/env python3
"""manage_tests.py -- `make clean-tests` / `make test-repro` 的实现（TESTCASES-076t，P6）。

两个子命令：

``clean``
    删除某个 scope 的**生成物**目录（`.dadao/tests/` 下，按 `SCOPE_MAP`）。
    ``--dry-run`` 只列出将要删除的目录/文件数，不动盘。

``repro``
    证明某 scope 的**构建产物逐字节可重生成**（`docs/Process-09 §4`）：
    清 → 跑 producer → 快照 → 清 → 再跑 → 快照 → 逐文件比 md5。
    运行记录（`run.json` / `meta.json` / `*.log` / `.lit_test_times.txt` …）**不参与**
    比较（含时间戳/宿主信息，本就不可逐字节复现）。判据 = **构建产物后缀白名单**
    （`BUILD_SUFFIXES`）；白名单之外的文件计入 ``skipped`` 并打印（不静默漏比）。

可达 FAIL / 反 vacuous
---------------------
* ``clean``：scope 必须是 `SCOPE_MAP` 的键（或 `all`）；**未知 scope ⇒ rc=2**。
* ``clean``/``repro``：`.dadao/tests/` 顶层出现**未归属**目录 ⇒ rc=1（防新产物目录
  悄悄长出而清理/复现只覆盖旧名）。
* ``repro``：**产物数 == 0 ⇒ FAIL**（producer 没产出等于没比）；两次文件集不一致
  ⇒ FAIL；任一文件 md5 不一致 ⇒ FAIL。
* ``repro --inject CMD``：在两次生产之间执行 CMD，用于证明比较**可达 FAIL**。
* ``repro`` 的 `night` scope 显式拒绝（夜跑报告含时间戳，不可逐字节复现）。

退出码：0 PASS / 1 FAIL（比较失败、未归属目录、零产物）/ 2 用法或环境错误。
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# 单一真源：scope → 生成物目录（`docs/Process-09 §4` 的映射表）
# ---------------------------------------------------------------------------
# 现状：`.dadao/tests/` 沿用历史目录名（`e2e` 归属未定 ⇒ 尚未统一成 `{inst,arch,
# unit,tset}/`）。本表是「哪些目录属于哪个 scope」的**唯一**出处；新增生成物目录
# 必须登记，否则 clean/repro 因「未归属」报红。
SCOPE_MAP: dict[str, list[str]] = {
    # 自身同名目录（`inst/`/`arch/`/`unit/`/`tset/`）现在就登记：将来统一改名到
    # Process-09 §4 的目标形状时，清理/复现无需再改表。
    "inst": ["harness", "smoke", "inst"],
    "arch": ["arch", "m5-e2e", "probes"],
    "unit": [
        "codegen-e2e", "codegen-m6", "elf-e2e", "elf-m6",
        "ir-lli-diff", "lit-output", "unit",
    ],
    "tset": [
        "libc-test-user", "llvm-ts-user", "llvm-ts-user-050t", "embench-user",
        "m6-embench", "libc-argv-static", "libc-argv-dynamic", "tset",
    ],
    "night": ["night"],
    # L3 报告（TESTCASES-083t）：与 night 同为只读汇总报告，不可逐字节复现。
    "l3": ["l3"],
}

# 顶层目录里**不是**测试生成物的：构建产物（由对应 build 目标管理，不进 scope 清理）。
UNSCOPED = {"bootrom"}

# 构建产物后缀（`repro` 的比较面）= **白名单**：运行记录天然不在其中。
BUILD_SUFFIXES = {
    ".o", ".bin", ".s", ".elf", ".ll", ".mir", ".yaml", ".a", ".so", ".d",
}

# 显式列出的运行记录名（白名单已排除；列出便于报告与 `--dry-run` 说明）。
RUN_RECORD_NAMES = {"run.json", "meta.json", "run.log", ".lit_test_times.txt"}

# scope → producer（`repro` 用；argv 列表，cwd = 仓库根）
PRODUCERS: dict[str, list[list[str]]] = {
    "inst": [["make", "check-inst-smoke"]],
    "arch": [["make", "check-arch-smoke"]],
    "unit": [["make", "test-codegen"], ["make", "test-elf"]],
    "tset": [["make", "check-tset-embench-smoke"]],
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def log_path(name: str) -> Path:
    p = REPO_ROOT / ".work" / "log" / "testcases"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"check-{name}.log"


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scope_dirs(root: Path, scope: str) -> list[Path]:
    if scope == "all":
        names = [n for names in SCOPE_MAP.values() for n in names]
        names += sorted(UNSCOPED)
    else:
        names = SCOPE_MAP[scope]
    return [root / n for n in names]


def unassigned(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    known = {n for names in SCOPE_MAP.values() for n in names} | UNSCOPED
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name not in known)


def count_files(paths: list[Path]) -> int:
    return sum(1 for d in paths if d.exists() for p in d.rglob("*") if p.is_file())


def parse_scope(raw: str) -> str:
    scope = (raw or "").strip()
    if scope not in SCOPE_MAP and scope != "all":
        sys.stderr.write(
            "ERROR: --scope 必须是 %s|all，得到 %r\n"
            % ("|".join(sorted(SCOPE_MAP)), raw or ""))
        sys.exit(2)
    return scope


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------

def cmd_clean(args: argparse.Namespace) -> int:
    scope = parse_scope(args.scope)
    root = Path(args.root)

    if scope != "all":
        stray = unassigned(root)
        if stray:
            sys.stderr.write(
                "clean-tests: FAIL — %s 顶层有未归属目录：%s\n"
                "  先登记到 tools/testcases/manage_tests.py 的 SCOPE_MAP（或 UNSCOPED）。\n"
                % (root, ", ".join(stray)))
            return 1

    dirs = scope_dirs(root, scope)
    existing = [d for d in dirs if d.exists()]
    files = count_files(existing)

    print(f"clean-tests: scope={scope} root={repo_rel(root)}")
    print(f"  assigned={len(dirs)} existing={len(existing)} files={files}")
    for d in existing:
        print(f"  {'WOULD DELETE' if args.dry_run else 'delete'} {repo_rel(d)}")
    for d in dirs:
        if not d.exists():
            print(f"  absent       {repo_rel(d)}")

    if args.dry_run:
        print(f"clean-tests: DRY-RUN (would delete {len(existing)} dir(s), {files} file(s))")
        return 0

    for d in existing:
        shutil.rmtree(d)
    print(f"clean-tests: PASS (removed {len(existing)} dir(s), {files} file(s))")
    return 0


# ---------------------------------------------------------------------------
# repro
# ---------------------------------------------------------------------------

def snapshot(root: Path, dirs: list[Path]) -> tuple[dict[str, str], int]:
    products: dict[str, str] = {}
    skipped = 0
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file():
                continue
            if p.name in RUN_RECORD_NAMES or p.suffix not in BUILD_SUFFIXES:
                skipped += 1
                continue
            products[str(p.relative_to(root))] = md5_file(p)
    return products, skipped


def run_command(cmd: list[str], logname: str) -> int:
    log = log_path(logname)
    print(f"  $ {' '.join(cmd)}   (log {repo_rel(log)})")
    with log.open("w") as fh:
        return subprocess.call(cmd, cwd=REPO_ROOT, stdout=fh, stderr=subprocess.STDOUT)


def producer_commands(args: argparse.Namespace) -> list[list[str]]:
    if args.producer:
        return [["bash", "-lc", args.producer]]
    return PRODUCERS[args.scope]


def cmd_repro(args: argparse.Namespace) -> int:
    scope = parse_scope(args.scope)
    if scope == "all":
        sys.stderr.write("ERROR: test-repro 需要具体 scope（night 报告不可逐字节复现）\n")
        return 2
    if scope == "night":
        sys.stderr.write(
            "ERROR: test-repro 不支持 SCOPE=night —— 夜跑报告含时间戳/宿主信息，"
            "按 docs/Process-08 §1.1 本就不要求逐字节复现。\n")
        return 2
    if scope == "l3":
        sys.stderr.write(
            "ERROR: test-repro 不支持 SCOPE=l3 —— L3 报告含时间戳/宿主信息，"
            "按 docs/Process-08 §1.1 本就不要求逐字节复现。\n")
        return 2

    root = Path(args.root)
    dirs = scope_dirs(root, scope)
    stray = unassigned(root)
    if stray:
        sys.stderr.write(
            "test-repro: FAIL — %s 顶层有未归属目录：%s（登记 SCOPE_MAP 后重试）\n"
            % (root, ", ".join(stray)))
        return 1

    producers = producer_commands(args)
    print(f"test-repro: scope={scope} root={repo_rel(root)} producers={len(producers)}")
    print("  compare suffixes: " + " ".join(sorted(BUILD_SUFFIXES)))
    print("  excluded: " + " ".join(sorted(RUN_RECORD_NAMES)) + " + 白名单外后缀")

    if args.dry_run:
        products, skipped = snapshot(root, dirs)
        for d in dirs:
            print(f"  {'exists' if d.exists() else 'absent':6s} {repo_rel(d)}")
        for cmd in producers:
            print(f"  $ {' '.join(cmd)}")
        print(f"  current products={len(products)} skipped={skipped}")
        print(f"test-repro: DRY-RUN (2 productions + md5 compare; 先清 {len(dirs)} 个目录)")
        return 0

    # 清单目录名**不以时间戳开头**：`docs/Process-08 §1.1` 的 `^\d{8}T\d{6}Z-` 运行目录
    # 语义（三件套 `run.json`/`meta.json`/`run.log`、`check-run-artifacts` A2）只约束
    # 驱动的**运行记录**；这里是 md5 快照清单，不是运行记录。
    work = REPO_ROOT / ".work" / "tests" / "repro" / f"{scope}-{utc_stamp()}"
    n = 1
    while work.exists():          # 禁止两次跑写同一目录
        n += 1
        work = REPO_ROOT / ".work" / "tests" / "repro" / f"{scope}-{utc_stamp()}-{n}"
    work.mkdir(parents=True)
    print(f"  manifests: {repo_rel(work)}")

    snapshots: list[dict[str, str]] = []
    for round_name in ("a", "b"):
        if cmd_clean(argparse.Namespace(scope=scope, root=str(root), dry_run=False)) != 0:
            return 2
        for i, cmd in enumerate(producers):
            name = f"test-repro-{scope}-{round_name}-{i}"
            rc = run_command(cmd, name)
            if rc != 0:
                sys.stderr.write(
                    f"test-repro: FAIL — producer #{i} rc={rc} "
                    f"（log .work/log/testcases/check-{name}.log）\n")
                return 2
        products, skipped = snapshot(root, dirs)
        print(f"  round {round_name}: products={len(products)} skipped={skipped}")
        if not products:
            sys.stderr.write(
                "test-repro: FAIL — 本轮构建产物数为 0（producer 没产出 ⇒ 比较为空）\n")
            return 1
        (work / f"{round_name}.tsv").write_text(
            "".join(f"{md5}\t{path}\n" for path, md5 in sorted(products.items())))
        snapshots.append(products)

        if round_name == "a" and args.inject:
            print(f"  --inject: {args.inject}")
            irc = subprocess.call(["bash", "-lc", args.inject], cwd=REPO_ROOT)
            if irc != 0:
                sys.stderr.write(f"test-repro: FAIL — 注入命令自身 rc={irc}\n")
                return 2

    a, b = snapshots
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = sorted(p for p in set(a) & set(b) if a[p] != b[p])
    if only_a or only_b or diff:
        sys.stderr.write(
            "test-repro: FAIL — 构建产物不可逐字节复现："
            f"only-a={len(only_a)} only-b={len(only_b)} md5-diff={len(diff)}\n")
        for p in (only_a + only_b + diff)[:10]:
            sys.stderr.write(f"  {p}\n")
        return 1

    print(f"test-repro: PASS (scope={scope}, {len(a)} build product(s) byte-identical across 2 runs)")
    return 0


# ---------------------------------------------------------------------------
# self-test：假 producer（不跑真门控），逐条给出可达 FAIL
# ---------------------------------------------------------------------------

_SELFTEST_PRODUCER = """\
import pathlib, sys, time
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
seed = pathlib.Path(sys.argv[2]).read_bytes()
(out / "a.o").write_bytes(b"DADAO-REPRO\\x00" + seed)
(out / "b.elf").write_bytes(b"ELF\\x7f")
(out / "run.json").write_text('{"stamp": %f}' % time.time())
(out / "run.log").write_text("noise")
"""


def cmd_selftest(args: argparse.Namespace) -> int:
    base = Path(tempfile.mkdtemp(prefix="manage-tests-selftest-",
                                 dir=args.tmp_root or "/tmp/opencode"))
    producer = base / "producer.py"
    producer.write_text(_SELFTEST_PRODUCER)
    seed = base / "seed.txt"
    seed.write_bytes(b"seed-0")
    # 注入面 = producer 的**输入**（seed）：两轮之间改输入 ⇒ 第二轮产物不同 ⇒ FAIL。
    corrupt = base / "corrupt.py"
    corrupt.write_text(
        "import pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "p.write_bytes(p.read_bytes() + b'-tampered')\n")
    root = base / "artifacts"
    smoke = root / "harness" / "smoke"
    smoke.mkdir(parents=True)
    (smoke / "stale.o").write_bytes(b"old")

    saved = PRODUCERS["inst"]
    PRODUCERS["inst"] = [["python3", str(producer), str(smoke), str(seed)]]
    checks: list[tuple[str, bool, str]] = []

    def repro(inject: str | None) -> int:
        return cmd_repro(argparse.Namespace(
            scope="inst", root=str(root), dry_run=False, producer=None, inject=inject))

    try:
        rc = repro(None)
        checks.append(("baseline repro => PASS", rc == 0, f"rc={rc}"))
        rc = repro(f"python3 {corrupt} {seed}")
        checks.append(("injected corruption => FAIL (rc=1)", rc == 1, f"rc={rc}"))
        seed.write_bytes(b"seed-0")
        rc = repro(None)
        checks.append(("re-run after restore => PASS", rc == 0, f"rc={rc}"))

        # 零产物 ⇒ FAIL（producer 写不出白名单后缀）
        empty = base / "empty"
        empty.mkdir()
        PRODUCERS["inst"] = [["bash", "-c", f"mkdir -p {smoke}; echo run > {smoke}/run.log"]]
        rc = repro(None)
        checks.append(("zero build products => FAIL (rc=1)", rc == 1, f"rc={rc}"))

        # 未归属目录 ⇒ clean FAIL
        (root / "stray_dir").mkdir()
        rc = cmd_clean(argparse.Namespace(scope="inst", root=str(root), dry_run=False))
        checks.append(("unassigned dir => clean FAIL (rc=1)", rc == 1, f"rc={rc}"))
        (root / "stray_dir").rmdir()

        # 未知 scope ⇒ rc=2（真实子进程调用，避免"假断言"）
        rc = subprocess.call(
            [sys.executable, __file__, "clean", "--scope", "bogus", "--root", str(root)],
            stderr=subprocess.DEVNULL)
        checks.append(("unknown scope => rc=2", rc == 2, f"rc={rc}"))

        # night 显式拒绝
        rc = cmd_repro(argparse.Namespace(
            scope="night", root=str(root), dry_run=False, producer=None, inject=None))
        checks.append(("repro night => explicit refuse (rc=2)", rc == 2, f"rc={rc}"))

        # l3 显式拒绝（TESTCASES-083t）
        rc = cmd_repro(argparse.Namespace(
            scope="l3", root=str(root), dry_run=False, producer=None, inject=None))
        checks.append(("repro l3 => explicit refuse (rc=2)", rc == 2, f"rc={rc}"))
    finally:
        PRODUCERS["inst"] = saved

    fails = sum(0 if ok else 1 for _, ok, _ in checks)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
    print(f"manage_tests --self-test: {'PASS' if fails == 0 else 'FAIL'} "
          f"({len(checks) - fails}/{len(checks)})")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"  kept: {base}")
    return 0 if fails == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="clean-tests / test-repro 实现")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--keep", action="store_true", help="self-test: 保留临时树")
    ap.add_argument("--tmp-root", default=None, help="self-test: 临时根（默认 /tmp/opencode）")
    sub = ap.add_subparsers(dest="cmd")

    p_clean = sub.add_parser("clean", help="删除某 scope 的生成物目录")
    p_clean.add_argument("--scope", default="")
    p_clean.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"))
    p_clean.add_argument("--dry-run", action="store_true")

    p_repro = sub.add_parser("repro", help="构建产物逐字节可重生成")
    p_repro.add_argument("--scope", default="")
    p_repro.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"))
    p_repro.add_argument("--dry-run", action="store_true")
    p_repro.add_argument("--producer", default=None,
                         help="覆盖 producer 命令（调试/小范围；默认见 PRODUCERS）")
    p_repro.add_argument("--inject", default=None,
                         help="在两次生产之间执行一次注入命令（反例自检）")

    args = ap.parse_args(argv)
    if args.self_test:
        return cmd_selftest(args)
    if args.cmd == "clean":
        return cmd_clean(args)
    if args.cmd == "repro":
        return cmd_repro(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
