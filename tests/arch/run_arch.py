#!/usr/bin/env python3
"""`tests/arch/run_arch.py` — Vast arch scope 的唯一驱动（m16-testcases-006）。

范围与判据见 `tests/arch/PLAN.md` / `tests/arch/README.md`：
  * **只测 Kaiwu-Vast**（`system`；cfx 0/2/3/4/5/15/32/34/63）；
  * QEMU/gem5/chipyard 是同一 scope 的三种承载；未实现的后端 **fail-closed**
    （记 SKIP 并非零退出，禁止静默降级为「其余平台通过」）；
  * 用例/脚本/数据都在 `tests/arch/` 内；签名机制真源在 `tests/shared/`。

接口：
    python3 tests/arch/run_arch.py --cfx 4 --platforms qemu --cache-model on
    python3 tests/arch/run_arch.py --self-test
    python3 tests/arch/run_arch.py --list

退出码：0 全通过；1 任一用例/平台失败或 SKIP；2 用法/配置错误。
不启动模拟器的 `--self-test` 只校验：arch.yaml 的 `machine/kind`、
各 `expected.yaml` 的签名流结构、驱动声明的 `--selfcheck`、未实现后端的
fail-closed 探针。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[2]      # 仓库根
ARCH = ROOT / "tests" / "arch"
sys.path.insert(0, str(ARCH))

from common import platform as arch_platform   # noqa: E402
from common import signature as arch_sig       # noqa: E402

DIR_CFX = {
    "umon": 0, "smon": 2, "hmon": 3, "ptw": 4, "cache": 5,
    "hart": 15, "pmem": 32, "time": 34, "power": 63,
}
VALID_CFX = tuple(sorted(DIR_CFX.values()))
PLATFORMS = arch_platform.BACKENDS
CACHE_MODELS = ("on", "off")
KINDS = ("asm", "driver")


class ConfigError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# 索引 / 与索引门控同口径的静态校验
# ---------------------------------------------------------------------------
def load_index(path=None):
    path = Path(path) if path else ARCH.parent / "arch.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("无法读取 %s: %s" % (path, exc))
    if not isinstance(data, list):
        raise ConfigError("%s: 顶层必须是列表" % path)
    cases = []
    problems = []
    for index, entry in enumerate(data, 1):
        where = "%s 第 %d 条" % (path, index)
        if not isinstance(entry, dict):
            problems.append("%s: 条目必须是映射" % where)
            continue
        cid = entry.get("id")
        rel = entry.get("file")
        if not isinstance(cid, str) or not cid.startswith("arch-"):
            problems.append("%s: `id` 必须是 arch-*，实为 %r" % (where, cid))
            continue
        if not isinstance(rel, str) or not rel:
            problems.append("%s: `file` 必须是非空字符串" % where)
            continue
        parts = PurePosixPath(rel).parts
        if len(parts) < 2 or parts[0] != "arch" or parts[1] not in DIR_CFX:
            problems.append("%s: `file` 必须是 arch/<cfx>/…，实为 %r"
                            % (where, rel))
            continue
        if not (ROOT / "tests" / rel).is_file():
            problems.append("%s: `file` 不存在: tests/%s" % (where, rel))
        kind = entry.get("kind", "asm")
        if "kind" not in entry:
            problems.append("%s: arch 条目必须写 `kind: asm|driver`" % where)
        elif kind not in KINDS:
            problems.append("%s: `kind`=%r 须为 %s" % (where, kind, list(KINDS)))
        machine = entry.get("machine")
        if machine != "vast":
            problems.append("%s: arch 条目 `machine`=%r 只能 'vast'"
                            % (where, machine))
        cases.append({
            "id": cid, "file": rel, "kind": kind, "machine": machine,
            "cfx": DIR_CFX[parts[1]],
            "level": entry.get("level"),
        })
    if problems:
        raise ConfigError("\n".join(problems))
    return cases


# ---------------------------------------------------------------------------
# --self-test（不启动模拟器）
# ---------------------------------------------------------------------------
def self_test() -> int:
    print("=" * 72)
    print("run_arch --self-test（不启动模拟器）")
    print("=" * 72)
    problems = []
    try:
        cases = load_index()
    except ConfigError as exc:
        print("  FAIL  索引: %s" % exc)
        return 1
    print("  PASS  索引: %d 条 arch case，machine 全 vast，kind ∈ %s"
          % (len(cases), list(KINDS)))

    by_dir = {}
    for case in cases:
        by_dir.setdefault(PurePosixPath(case["file"]).parts[1], []).append(case)
    for cfx_dir, dir_cases in sorted(by_dir.items()):
        expected = ARCH / cfx_dir / "expected.yaml"
        issues = arch_sig.validate_expected(expected)
        if issues:
            problems.extend(issues)
            print("  FAIL  expected.yaml: %s（%d 项）"
                  % (expected.relative_to(ROOT), len(issues)))
        else:
            data = yaml.safe_load(expected.read_text(encoding="utf-8"))
            n_sig = sum(len(check.get("signature") or [])
                        for case in data.get("cases") or []
                        for check in case.get("checks") or [])
            print("  PASS  expected.yaml: %s（%d case，签名槽 %d）"
                  % (expected.relative_to(ROOT), len(dir_cases), n_sig))

    drivers = sorted({c["file"] for c in cases if c["kind"] == "driver"})
    for rel in drivers:
        driver = ROOT / "tests" / rel
        try:
            proc = subprocess.run(
                [sys.executable, str(driver), "--selfcheck"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=120, stdin=subprocess.DEVNULL)
            rc, out = proc.returncode, proc.stdout
        except subprocess.TimeoutExpired:
            rc, out = -2, b""
        tail = out.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        if rc == 0:
            print("  PASS  驱动 --selfcheck: %s（%s）" % (rel, tail[0]))
        else:
            problems.append("%s: --selfcheck rc=%d（%s）" % (rel, rc, tail[0]))
            print("  FAIL  驱动 --selfcheck: %s rc=%d" % (rel, rc))

    backend_problems = arch_platform.self_test_fail_closed()
    if backend_problems:
        problems.extend(backend_problems)
        for problem in backend_problems:
            print("  FAIL  后端 fail-closed: %s" % problem)
    else:
        print("  PASS  后端 fail-closed: gem5 / chipyard 均显式拒绝")

    print("-" * 72)
    if problems:
        print("self-test: FAIL（%d 项）" % len(problems))
        return 1
    print("self-test: PASS")
    return 0


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------
def _split_csv(values, allowed, label):
    out = []
    for raw in values:
        for item in str(raw).split(","):
            item = item.strip()
            if not item:
                continue
            if item not in allowed:
                raise ConfigError("%s 非法: %r（允许 %s）"
                                  % (label, item, list(allowed)))
            if item not in out:
                out.append(item)
    return out


def _default_paths(args):
    sys.path.insert(0, str(ROOT / "tools" / "infra"))
    try:
        import paths  # noqa: WPS433
    except Exception as exc:  # pragma: no cover - 环境异常
        raise ConfigError("无法加载 tools/infra/paths.py: %s" % exc)
    toolchain = paths.host_toolchain_bin()
    qemu = Path(args.qemu) if args.qemu else toolchain / "qemu-system-dadao"
    llvm_mc = Path(args.llvm_mc) if args.llvm_mc else toolchain / "llvm-mc"
    llvm_objcopy = (Path(args.llvm_objcopy) if args.llvm_objcopy
                    else toolchain / "llvm-objcopy")
    bootrom = (Path(args.bootrom) if args.bootrom
               else paths.test_artifacts_dir() / "bootrom" / "step5"
               / "bootrom_step5.bin")
    work = (Path(args.work_dir) if args.work_dir
            else paths.test_artifacts_dir() / "arch" / "run_arch")
    return qemu, llvm_mc, llvm_objcopy, bootrom, work


def run(args) -> int:
    if args.cache_model != "on":
        raise ConfigError("--cache-model 只支持 on；arch 不测直通模式（off）")
    cfx = (_split_csv(args.cfx, [str(v) for v in VALID_CFX], "--cfx")
           if args.cfx else [str(v) for v in VALID_CFX])
    cfx = [int(v) for v in cfx]
    platforms = (_split_csv(args.platforms, PLATFORMS, "--platforms")
                 if args.platforms else list(PLATFORMS))
    cases = load_index()
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            raise ConfigError("--case %r 不在 tests/arch.yaml" % args.case)
    else:
        cases = [c for c in cases if c["cfx"] in cfx]
    if not cases:
        raise ConfigError("所选 cfx 无用例（cfx=%s）" % cfx)

    qemu, llvm_mc, llvm_objcopy, bootrom, work = _default_paths(args)
    ctx = argparse.Namespace(arch_root=str(ARCH), repo_root=str(ROOT),
                             work=str(work), qemu=qemu,
                             llvm_mc=llvm_mc, llvm_objcopy=llvm_objcopy,
                             bootrom=bootrom,
                             m5_runner=ROOT / "tools" / "testcases" / "arch"
                             / "run_m5_e2e.py",
                             timeout=args.timeout)
    work.mkdir(parents=True, exist_ok=True)

    if "qemu" in platforms and not (
            Path(qemu).is_file() and os.access(qemu, os.X_OK)):
        raise ConfigError("qemu 不存在或不可执行: %s（--qemu 或 make install-host）"
                          % qemu)
    if "qemu" in platforms and any(c["kind"] == "asm" for c in cases):
        for value, label in ((llvm_mc, "llvm-mc"),
                             (llvm_objcopy, "llvm-objcopy"),
                             (bootrom, "Vast step5 BootROM")):
            if not Path(value).is_file():
                raise ConfigError("%s 不存在: %s（asm 载体需要）" % (label, value))

    print("=" * 72)
    print("run_arch: cfx=%s platforms=%s cache-model=on cases=%d"
          % (cfx, platforms, len(cases)))
    print("work=%s" % work)
    print("=" * 72)

    results = []
    failures = []
    for platform in platforms:
        try:
            platform_results = arch_platform.run(platform, cases, ctx)
        except arch_platform.PlatformError as exc:
            print("  SKIP  %-8s %s" % (platform, exc))
            failures.append("%s: SKIP（%s）" % (platform, exc))
            continue
        if len(platform_results) != len(cases):
            msg = ("%s: 后端返回 %d 条结果，期望 %d 条（不得静默漏跑）"
                   % (platform, len(platform_results), len(cases)))
            print("  FAIL  %s" % msg)
            failures.append(msg)
        for res in platform_results:
            results.append(res)
            status = res["verdict"]
            print("  %-4s  %-10s %-22s rc=%s %s"
                  % (status, res["platform"], res["case"], res["rc"],
                     res.get("reason", "")))
            if status != "PASS":
                failures.append("%s/%s: %s"
                                % (res["platform"], res["case"],
                                   res.get("reason", "")))

    summary = work / "run.json"
    summary.write_text(json.dumps(
        {"cfx": cfx, "platforms": platforms, "cache_model": "on",
         "cases": [c["id"] for c in cases], "results": results,
         "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("-" * 72)
    if failures:
        for failure in failures:
            print("  FAIL  %s" % failure)
        print("run_arch: FAIL（%d 项；见 %s）" % (len(failures), summary))
        return 1
    print("run_arch: PASS（%d case × %d 平台；见 %s）"
          % (len(cases), len(platforms), summary))
    return 0


def list_plan(args) -> int:
    if args.cache_model != "on":
        raise ConfigError("--cache-model 只支持 on；arch 不测直通模式（off）")
    cfx = (_split_csv(args.cfx, [str(v) for v in VALID_CFX], "--cfx")
           if args.cfx else [str(v) for v in VALID_CFX])
    platforms = (_split_csv(args.platforms, PLATFORMS, "--platforms")
                 if args.platforms else list(PLATFORMS))
    cases = [c for c in load_index() if str(c["cfx"]) in cfx]
    print("%-4s %-12s %-22s %-7s %s"
          % ("cfx", "dir", "case", "kind", "platforms"))
    for case in cases:
        print("%-4d %-12s %-22s %-7s %s"
              % (case["cfx"], PurePosixPath(case["file"]).parts[1],
                 case["id"], case["kind"], ",".join(platforms)))
    print("%d case × %d 平台" % (len(cases), len(platforms)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cfx", action="append",
                    help="cfx 列表（逗号分隔）；缺省 = 0/2/3/4/5/15/32/34/63")
    ap.add_argument("--platforms", action="append",
                    help="qemu/gem5/chipyard 逗号列表；缺省 = 三者全跑")
    ap.add_argument("--cache-model", default="on", choices=CACHE_MODELS,
                    help="arch 固定 on；off 退出 2")
    ap.add_argument("--case", default=None, help="只跑指定 case id")
    ap.add_argument("--work-dir", default=None, help="运行期证据目录")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--llvm-mc", default=None)
    ap.add_argument("--llvm-objcopy", default=None)
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--self-test", action="store_true",
                    help="不启动模拟器：索引/期望/驱动自检/后端 fail-closed")
    ap.add_argument("--list", action="store_true", help="打印计划表，不执行")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    try:
        if args.list:
            return list_plan(args)
        return run(args)
    except ConfigError as exc:
        print("run_arch: ERROR: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
