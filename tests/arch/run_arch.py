#!/usr/bin/env python3
"""`tests/arch/run_arch.py` — Vast arch scope 的唯一驱动（m16-testcases-006）。

范围与判据见 `tests/arch/PLAN.md` / `tests/arch/README.md`：
  * **只测 Kaiwu-Vast**（`system`；cfx 0/2/3/4/5/15/32/34/63）；
  * QEMU/gem5/chipyard 是同一 scope 的三种承载；未实现的后端 **fail-closed**
    （记 SKIP 并非零退出，禁止静默降级为「其余平台通过」）；
  * 用例/脚本/数据都在 `tests/arch/` 内；签名机制真源在 `tests/shared/`。

接口：
    python3 tests/arch/run_arch.py --cfx 4 --platforms qemu --cache-model on
    python3 tests/arch/run_arch.py --level smoke --platforms qemu --cache-model off
    python3 tests/arch/run_arch.py --mode hmon|smon|umon
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
# `common/` 承载跨 cfx 的驱动（`check_mode_env.py`）；其 cfx 归属由用例 id 的
# 第二段（`arch-<cfx>-...`）现场派生，不把 `common` 当作可声明的 cfx 名。
COMMON_DIR = "common"
VALID_CFX = tuple(sorted(DIR_CFX.values()))
PLATFORMS = arch_platform.BACKENDS
CACHE_MODELS = ("on", "off")
KINDS = ("asm", "driver")
LEVELS = ("smoke", "full", "all")
# 运行模式（m16-testcases-015）：hmon/smon/umon = hypv/supv/user 的当前模式监视器。
MODES = ("hmon", "smon", "umon")
DEFAULT_MODE = "hmon"


class ConfigError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# 索引 / 与索引门控同口径的静态校验
# ---------------------------------------------------------------------------
def load_index(path=None, modes_path=None):
    path = Path(path) if path else ARCH.parent / "arch.yaml"
    modes_path = Path(modes_path) if modes_path else ARCH / "modes.yaml"
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
        cfx_dir = parts[1] if len(parts) > 1 else ""
        if len(parts) < 2 or parts[0] != "arch" or (
                cfx_dir != COMMON_DIR and cfx_dir not in DIR_CFX):
            problems.append("%s: `file` 必须是 arch/<cfx>/…，实为 %r"
                            % (where, rel))
            continue
        if cfx_dir == COMMON_DIR:
            # 跨 cfx 驱动（如 `arch-umon-011` 的 check_mode_env.py）：归属取 id
            # 第二段，仍按该 cfx 过滤/归类；`common` 本身不是 cfx 名。
            owner = cid.split("-")[1] if len(cid.split("-")) > 1 else ""
            if owner not in DIR_CFX:
                problems.append("%s: `file` 在 common/ 下，但 id `%s` 的第二段"
                                " %r 不是 cfx 名" % (where, cid, owner))
                continue
            cfx_dir = owner
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
            "cfx": DIR_CFX[cfx_dir], "cfx_dir": cfx_dir,
            "level": entry.get("level"),
        })
    if problems:
        raise ConfigError("\n".join(problems))
    modes = load_modes(modes_path, [case["id"] for case in cases])
    for case in cases:
        case.update(modes[case["id"]])
    return cases


def load_modes(path, case_ids):
    """读取 `tests/arch/modes.yaml` 并做双向校验（缺项/多项/非法模式/缺原因）。

    返回 `{case_id: {modes, mode_reasons, cfx_access}}`；任何不一致都记
    ConfigError，不做「缺省按 hmon」之外的静默补全（`modes` 缺省语义只对旧用例
    成立，这里要求每条 arch 用例都显式登记）。

    `cfx_access`（m16-testcases-017）：该用例在目标模式下需要访问的 cfx 列表
    （取 `DIR_CFX` 的名字，如 `cache`/`ptw`）。环境据此在降模式前打开目标 cfx 的
    `<mode>` 行来源掩码（`DADAO-12 §3`）；声明本身不放宽默认掩码。非法/重复/
    空列表，或在只有 hmon 的用例上声明（永远用不到）⇒ ConfigError，不静默忽略。
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("无法读取模式清单 %s: %s" % (path, exc))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), dict):
        raise ConfigError("%s: 顶层必须是 {cases: {<id>: {...}}}" % path)
    cases = data["cases"]
    ids = set(case_ids)
    problems = []
    missing = sorted(ids - set(cases))
    orphan = sorted(set(cases) - ids)
    if missing:
        problems.append("%s: 缺 arch 用例条目: %s" % (path, ", ".join(missing)))
    if orphan:
        problems.append("%s: 条目不在 tests/arch.yaml: %s"
                        % (path, ", ".join(orphan)))
    out = {}
    for cid in case_ids:
        entry = cases.get(cid)
        if entry is None:
            continue
        where = "%s: %s" % (path, cid)
        if not isinstance(entry, dict):
            problems.append("%s: 条目必须是映射" % where)
            continue
        unknown = sorted(set(entry) - {"modes", "reasons", "cfx_access"})
        if unknown:
            problems.append("%s: 未知字段 %s（允许: ['modes', 'reasons', "
                            "'cfx_access']）" % (where, unknown))
        raw = entry.get("modes")
        if not isinstance(raw, list) or not raw:
            problems.append("%s: `modes` 必须是非空列表" % where)
            continue
        modes = []
        for mode in raw:
            if mode not in MODES:
                problems.append("%s: 非法模式 %r（允许 %s）"
                                % (where, mode, list(MODES)))
            elif mode in modes:
                problems.append("%s: `modes` 重复 %r" % (where, mode))
            else:
                modes.append(mode)
        reasons = entry.get("reasons") or {}
        if not isinstance(reasons, dict):
            problems.append("%s: `reasons` 必须是映射" % where)
            reasons = {}
        for mode in MODES:
            reason = reasons.get(mode)
            if mode in modes:
                if reason is not None:
                    problems.append("%s: `reasons.%s` 给了原因，但该模式已允许"
                                    % (where, mode))
            elif not isinstance(reason, str) or not reason.strip():
                problems.append("%s: 模式 %r 不允许却缺 `reasons.%s` 原因"
                                % (where, mode, mode))
        for mode in reasons:
            if mode not in MODES:
                problems.append("%s: `reasons` 含非法模式 %r" % (where, mode))
        access = entry.get("cfx_access")
        cfx_access = []
        if access is not None:
            if not isinstance(access, list) or not access:
                problems.append("%s: `cfx_access` 必须是非空列表" % where)
                access = []
            for name in access:
                if not isinstance(name, str) or name not in DIR_CFX:
                    problems.append(
                        "%s: `cfx_access` 含非法 cfx 名 %r（允许 %s）"
                        % (where, name, sorted(DIR_CFX)))
                elif DIR_CFX[name] in cfx_access:
                    problems.append("%s: `cfx_access` 重复 %r" % (where, name))
                else:
                    cfx_access.append(DIR_CFX[name])
            if cfx_access and not ({"smon", "umon"} & set(modes)):
                problems.append(
                    "%s: 声明了 `cfx_access` 但允许集只有 hmon —— hmon 模式"
                    "不需要（也无法）做权限准备，声明永远用不到" % where)
        out[cid] = {"modes": modes, "mode_reasons": reasons,
                    "cfx_access": cfx_access}
    if problems:
        raise ConfigError("\n".join(problems))
    return out


def select_level(cases, level):
    """按 `tests/arch.yaml` 的 `level` 现场派生代表集（不写死条数）。

    `level == "all"` 表示不过滤；所选集合为空时**显式失败**（fail-closed），
    不得把空代表集当成 vacuous 绿灯。
    """
    if level == "all":
        return cases
    selected = [case for case in cases if case["level"] == level]
    if not selected:
        raise ConfigError(
            "tests/arch.yaml 中 level=%r 的代表集为空（现场派生；"
            "不得静默当作通过）" % level)
    return selected


# ---------------------------------------------------------------------------
# --self-test（不启动模拟器）
# ---------------------------------------------------------------------------
PERM_INCLUDE = ".include \"cfx_perm.inc\""


def _perm_sources():
    """三个 env 必须都 include 单一宏块（`common/env/cfx_perm.inc`），不得再内联。

    宏块曾因 `llvm-mc` 不搜索源文件目录而在 smon/umon 各复制一份；现在驱动给
    llvm-mc 传了 env 目录的 `-I`（`m16-testcases-017`）⇒ 只留一份，这里机械
    检查没有回退成多份（判据：include 行在、宏定义行不在）。
    """
    problems = []
    for mode in ("hmon", "smon", "umon"):
        text = (ARCH / "common" / ("env-%s" % mode) / "env.S").read_text(
            encoding="utf-8")
        if PERM_INCLUDE not in text:
            problems.append("env-%s/env.S 缺 `%s`" % (mode, PERM_INCLUDE))
        if ".macro\tENV_PERM_OPEN_RC" in text:
            problems.append("env-%s/env.S 内联了权限准备宏（应只用 cfx_perm.inc）"
                            % mode)
    inc = ARCH / "common" / "env" / "cfx_perm.inc"
    if not inc.is_file():
        problems.append("缺 common/env/cfx_perm.inc")
    return problems


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
    per_mode = {mode: sum(1 for c in cases if mode in c["modes"])
                for mode in MODES}
    print("  PASS  modes 元数据: 每用例允许集 + 被排除模式的原因齐全（%s）"
          % ", ".join("%s=%d" % (m, n) for m, n in per_mode.items()))
    declared = [(c["id"], c["cfx_access"]) for c in cases if c["cfx_access"]]
    print("  PASS  cfx_access 声明: %d 条用例（%s）"
          % (len(declared),
             ", ".join("%s=%s" % (cid, [n for n, v in sorted(DIR_CFX.items())
                                        if v in acc])
                       for cid, acc in declared) or "无"))

    perm_problems = _perm_sources()
    if perm_problems:
        problems.extend(perm_problems)
        print("  FAIL  权限准备宏块: %s" % "; ".join(perm_problems))
    else:
        print("  PASS  权限准备宏块: hmon/smon/umon 共用 common/env/cfx_perm.inc")

    by_dir = {}
    for case in cases:
        by_dir.setdefault(case["cfx_dir"], []).append(case)
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
            print("  FAIL  后端接线/fail-closed: %s" % problem)
    else:
        print("  PASS  后端接线: gem5 driver 承载已接（qemu_gem5_shim）；"
              "chipyard 显式 fail-closed")

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
    gem5 = (Path(args.gem5) if args.gem5
            else Path(os.environ.get("PARITY_GEM5")
                      or ROOT / ".work/source/gem5/build/DADAO/gem5.opt"))
    gem5_config = (Path(args.gem5_config) if args.gem5_config
                   else Path(os.environ.get("PARITY_GEM5_CONFIG")
                             or ROOT / ".work/source/gem5/configs/dadao/fs.py"))
    gem5_shim = ROOT / "tools" / "testcases" / "parity" / "qemu_gem5_shim.py"
    return (qemu, llvm_mc, llvm_objcopy, bootrom, work,
            gem5, gem5_config, gem5_shim)


def _select_mode(cases, mode):
    """按 `--mode` 过滤；不允许的用例显式打印原因，全被排除 ⇒ 配置错误。

    不静默丢用例：每条不允许的用例都打印 `N/A <id> --mode <mode>: <原因>`；
    `--case` 指定的单条不允许时由调用方（`run`）在 `--case` 分支后仍走本函数，
    这里的「全空 ⇒ ConfigError」就是 fail-closed。
    """
    allowed, blocked = [], []
    for case in cases:
        if mode in case["modes"]:
            allowed.append(case)
        else:
            blocked.append(case)
    for case in blocked:
        print("  N/A   %-10s %-22s --mode %s: %s"
              % (case["kind"], case["id"], mode,
                 case["mode_reasons"].get(mode, "（未登记原因）")))
    if not allowed:
        raise ConfigError(
            "--mode %s 下无用例可跑（%d 条被排除：%s）；不得静默跳过"
            % (mode, len(blocked),
               ", ".join(c["id"] for c in blocked) or "无"))
    return allowed


def run(args) -> int:
    cfx = (_split_csv(args.cfx, [str(v) for v in VALID_CFX], "--cfx")
           if args.cfx else [str(v) for v in VALID_CFX])
    cfx = [int(v) for v in cfx]
    platforms = (_split_csv(args.platforms, PLATFORMS, "--platforms")
                 if args.platforms else list(PLATFORMS))
    cases = select_level(load_index(), args.level)
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            raise ConfigError("--case %r 不在 level=%r 的 tests/arch.yaml 集合"
                              % (args.case, args.level))
        if args.mode not in cases[0]["modes"]:
            raise ConfigError(
                "--case %s 不允许 --mode %s：%s"
                % (args.case, args.mode,
                   cases[0]["mode_reasons"].get(args.mode, "（未登记原因）")))
    else:
        cases = [c for c in cases if c["cfx"] in cfx]
    if not cases:
        raise ConfigError("所选 cfx 无用例（cfx=%s）" % cfx)
    cases = _select_mode(cases, args.mode)

    (qemu, llvm_mc, llvm_objcopy, bootrom, work,
     gem5, gem5_config, gem5_shim) = _default_paths(args)
    ctx = argparse.Namespace(arch_root=str(ARCH), repo_root=str(ROOT),
                             work=str(work), qemu=qemu,
                             llvm_mc=llvm_mc, llvm_objcopy=llvm_objcopy,
                             bootrom=bootrom,
                             gem5=gem5, gem5_config=gem5_config,
                             gem5_shim=gem5_shim,
                             m5_runner=ROOT / "tools" / "testcases" / "arch"
                             / "run_m5_e2e.py",
                             mode=args.mode,
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
    print("run_arch: level=%s cfx=%s platforms=%s cache-model=%s mode=%s "
          "cases=%d"
          % (args.level, cfx, platforms, args.cache_model, args.mode,
             len(cases)))
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

    # 跨平台一致性：同一 case 的逐槽签名字节与 verdict 必须相同（多平台时）。
    # 已接线的签名流逐字节比较；未接线的 case 是两份 0 槽空流（显式登记，
    # 不把空流当成已验证的「签名一致」）。
    def _observed_checks(res):
        """驱动日志里逐检查的 PASS/FAIL 行（同一驱动 → 跨引擎可比）。"""
        try:
            text = Path(res["log"]).read_text(encoding="utf-8",
                                              errors="replace")
        except OSError:
            return []
        return sorted(line.strip() for line in text.splitlines()
                      if line.startswith(("PASS ", "FAIL ")))

    by_case = {}
    for res in results:
        by_case.setdefault(res["case"], {})[res["platform"]] = res
    cross = {}
    for case_id, per in sorted(by_case.items()):
        if len(per) < 2:
            continue
        verdicts = {res["verdict"] for res in per.values()}
        sigs = {}
        checks = {}
        for name, res in per.items():
            path = Path(res["signature"])
            sigs[name] = path.read_bytes() if path.is_file() else b""
            checks[name] = _observed_checks(res)
        entry = {
            "platforms": sorted(per),
            "verdict_equal": len(verdicts) == 1,
            "signature_equal": len(set(sigs.values())) == 1,
            "checks_equal": len({tuple(v) for v in checks.values()}) == 1,
            "signature_slots": {name: len(blob) // 8
                                for name, blob in sigs.items()},
            "check_count": {name: len(v) for name, v in checks.items()},
        }
        entry["ok"] = (entry["verdict_equal"] and entry["signature_equal"]
                       and entry["checks_equal"])
        cross[case_id] = entry
        if entry["ok"]:
            continue
        msg = ("跨平台不一致 %s: verdict=%r signature_slots=%r check_count=%r"
               % (case_id, {name: res["verdict"] for name, res in per.items()},
                  entry["signature_slots"], entry["check_count"]))
        print("  FAIL  %s" % msg)
        failures.append(msg)

    summary = work / "run.json"
    summary.write_text(json.dumps(
        {"level": args.level, "cfx": cfx, "platforms": platforms,
         "cache_model": args.cache_model, "mode": args.mode,
         "cases": [c["id"] for c in cases], "results": results,
         "cross_platform": cross, "failures": failures},
        ensure_ascii=False, indent=2),
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
    cfx = (_split_csv(args.cfx, [str(v) for v in VALID_CFX], "--cfx")
           if args.cfx else [str(v) for v in VALID_CFX])
    platforms = (_split_csv(args.platforms, PLATFORMS, "--platforms")
                 if args.platforms else list(PLATFORMS))
    cases = [c for c in select_level(load_index(), args.level)
             if str(c["cfx"]) in cfx and args.mode in c["modes"]]
    print("%-4s %-12s %-22s %-7s %-5s %-14s %s"
          % ("cfx", "dir", "case", "kind", "level", "modes", "platforms"))
    for case in cases:
        print("%-4d %-12s %-22s %-7s %-5s %-14s %s"
              % (case["cfx"], case["cfx_dir"],
                 case["id"], case["kind"], case["level"],
                 ",".join(case["modes"]), ",".join(platforms)))
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
                    help="smoke 用 off（不测 cache）；cfx5 用例用 on")
    ap.add_argument("--level", default="all", choices=LEVELS,
                    help="只跑该 level 的代表集（smoke/full；all = 不过滤）")
    ap.add_argument("--mode", default=DEFAULT_MODE, choices=MODES,
                    help="运行模式环境（hmon/smon/umon；缺省 hmon）；"
                         "用例的 `modes` 不含该模式时显式 N/A + 原因，全被"
                         "排除则退出 2（fail-closed）")
    ap.add_argument("--case", default=None, help="只跑指定 case id")
    ap.add_argument("--work-dir", default=None, help="运行期证据目录")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--gem5", default=None,
                    help="gem5.opt（缺省 = $PARITY_GEM5 或 .work/source/gem5/"
                         "build/DADAO/gem5.opt）")
    ap.add_argument("--gem5-config", default=None,
                    help="gem5 fs.py（缺省 = $PARITY_GEM5_CONFIG 或 "
                         ".work/source/gem5/configs/dadao/fs.py）")
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
