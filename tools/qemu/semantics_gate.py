#!/usr/bin/env python3
"""L3 语义门控 `check-inst`（旧名 `check-qemu-semantics` = 别名）的载体派生 + 执行。

载体范围（`ISS-235` 处置「甲」= 扩至全量；`TESTCASES-072t` 起载体根 = `tests/inst/`）：
  - `tests/inst/base/*.yaml` **现场清单全量**（册名/册数一律现场派生，
    `Makefile` 与本脚本**均不写死册名/册数**）；
  - 非 `base/` 的既有载体目录：`tests/inst/rol/*.yaml`（`QEMU-064t`：`rol.*`
    scope = m9，故不在 `base/`）与 `tests/inst/atomics/*.yaml`
    （`QEMU-067t`：`fence`/`lr`/`sc` 已实现原子语义，非 M1 身份）与
    `tests/inst/clmul/*.yaml`（`QEMU-068t`：`clmul.o` 语义已实现，scope
    翻转归 `SPEC-155t`，故暂不在 `base/`）。
  - **不在**本门控：`tests/inst/rev/`、`tests/inst/bitcnt/`（M8 scope，
    2 册；见 `tests/inst/inventory.md`「非 M1 向量」）。

结构性断言（fail-closed，禁静默跳过）：
  - 每个载体目录（`base`/`rol`/`atomics`/`clmul`）非空 —— 0 册 ⇒ FAIL；
  - `git` 索引登记的载体册须全部在盘 —— 缺册 ⇒ FAIL（真源 = git 索引，
    故不写死册名/册数；无 git 工作树时打印 SKIP 提示后跳过该项）；
  - 载体 `basename` 唯一 —— 重名会被 gate 目录的 symlink 互相覆盖 ⇒ FAIL；
  - 每册为普通文件且含 ≥1 条用例；
  - gate 目录里的同名路径须为「指向该册」的 symlink（被普通文件/错指 symlink
    占用 ⇒ FAIL，不静默覆盖）；
  - 运行 `total` == 现场派生用例总数（gate 目录漏/多载体 ⇒ FAIL）。

形态门控（ISS-225，`--form-check` 可单独跑、无需 qemu 二进制）：
  - `components/qemu/patches/target/dadao/helper.c.patch` 必须存在且可读
    （「文件被引用」断言；缺文件 ⇒ FAIL，不得静默跳过）；
  - 该补丁与 `components/qemu/patches/**`、`tools/**` 中**不得**出现
    `dadao-m1` 的 umon syscall 接管实现符号（用户 2026-10-15 已裁定
    「不在 dadao-m1 上实现另一套 syscall 模拟」⇒ 需要形态哨兵）。
    符号名在代码中以拼接构造，避免本文件自身命中被扫。

日志自证（`ISS-236`）：默认档打印载体清单 + 载体数 + 用例总数 + 逐册用例数
（相对改造前载体集的增量）+ `total/passed/failed` + 与 `ISS-235` 旧值 161 的差值；
全部现场统计（`lessons §2`）。

Usage:
    python3 tools/qemu/semantics_gate.py --gate-dir DIR [--vectors DIR]
        [--qemu BIN] [--trampoline BIN] [--jobs N]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import yaml

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
# harness / 冒烟驱动在 `tools/testcases/{lib,inst}`（TESTCASES-072t）。
sys.path.insert(0, os.path.join(_REPO_ROOT, "tools", "testcases", "lib"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "tools", "testcases", "inst"))

# 复用现有 harness（构建 + 运行 + 批量聚合），不另造轮子。
import run_qemu_test as harness  # noqa: E402

# 载体目录（相对 --vectors）。`base` = 全量现场派生；其余为非 base 载体。
CARRIER_DIRS = ("base", "rol", "atomics", "clmul")

# ── 历史常量（仅用于「增量展示」，**不作**通过判据）──────────────────────
# `ISS-235` 登记时的 L3 现场 total（当时的 3 册载体集）。本轮打印与它的差值；
# 判据不看绝对值，改由「运行 total == 现场派生总数」+「全绿」保证。
ISS235_BASELINE_TOTAL = 161
# 改造前（INFRA-097t 之前）已在载体集内的册（仅用于逐册「新增 +N」标注）。
PREVIOUS_CARRIERS = (
    "reg-shift-extend.yaml",
    "reg-compare.yaml",
    "aip-si.yaml",
    "rol.yaml",
    "atomics-lrsc.yaml",
    "atomics-fence.yaml",
)

# ── deferred 登记：**精确到用例**（禁按类/正则批量豁免）─────────────────
# 向量侧对暂缓用例标 `status: deferred`（含 deferred_reason 指针 + 原期望存
# notes）；门控在此**再登记一遍**，实际 deferred 集合 != 本表 ⇒ FAIL
# （多一条 = 偷偷豁免；少一条 = 白挂 deferred）。
# `ISS-098` 的 6 条（ctrl-call[5] + ctrl-ret[0,1,2,3,8]）已由 TESTCASES-063t
# 修复 harness 后全部还原 `active`，故本表不再登记它们。
KNOWN_DEFERRED = {
    # 既有 deferred（非本任务新增）：cs.* overlap 快照 C-27，inventory 已声明
    ("reg-cond-assign.yaml", 15): "C-27: overlap 快照 deferred（inventory 既有声明）",
    ("reg-cond-assign.yaml", 16): "C-27: overlap 快照 deferred（inventory 既有声明）",
    ("reg-cond-assign.yaml", 17): "C-27: overlap 快照 deferred（inventory 既有声明）",
    ("reg-cond-assign.yaml", 18): "C-27: overlap 快照 deferred（inventory 既有声明）",
    ("reg-cond-assign.yaml", 19): "C-27: overlap 快照 deferred（inventory 既有声明）",
}


# ── ISS-225：dadao-m1 服务撤回后的形态哨兵 ──────────────────────────────────
# 用户 2026-10-15 裁定「我不需要在 dadao-m1 上实现另外一套 syscall 的模拟」。
# 符号名以拼接构造：本文件自身不会命中被扫文本（同时保证 grep 静态搜索为 0）。
_UMON_FORBIDDEN = (
    "umon" + "_serve_syscall",
    "is_umon" + "_user_syscall",
    "DADAO_NR" + "_write",
    "umon" + "_sys_",
    "umon" + "_host_",
    "umon" + "_set_",
)
_UMON_SCAN_DIRS = ("components/qemu/patches", "tools")
_UMON_TEXT_SUFFIXES = {".patch", ".py", ".sh", ".c", ".h", ".inc"}
# 必须存在的「被引用」文件（形态断言的落点）。
_UMON_REQUIRED_FILE = "components/qemu/patches/target/dadao/helper.c.patch"


def check_no_umon_takeover(repo_root: str) -> tuple[str, list[str]]:
    """断言 dadao-m1 的 umon syscall 接管实现不复存在（形态，不跑语义）。

    返回 (结论串, 错误列表)。缺 `helper.c.patch` ⇒ FAIL（文件被引用断言）。
    """
    errs: list[str] = []
    required = os.path.join(repo_root, _UMON_REQUIRED_FILE)
    scanned = 0
    hits: list[str] = []
    if not os.path.isfile(required):
        errs.append(f"形态：缺少被断言文件 {_UMON_REQUIRED_FILE}")
    for rel in _UMON_SCAN_DIRS:
        root = os.path.join(repo_root, rel)
        if not os.path.isdir(root):
            errs.append(f"形态：扫描目录缺失 {rel}（无法校验 ⇒ FAIL）")
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            if any(part in ("__pycache__", ".git") for part in dirpath.split(os.sep)):
                continue
            for name in filenames:
                if os.path.splitext(name)[1] not in _UMON_TEXT_SUFFIXES:
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except OSError as exc:
                    errs.append(f"形态：文件不可读 {path}: {exc}")
                    continue
                scanned += 1
                for token in _UMON_FORBIDDEN:
                    if token in text:
                        hits.append(f"{os.path.relpath(path, repo_root)}:{token}")
    for hit in hits:
        errs.append(f"形态：出现 umon 接管实现符号 {hit}")
    verdict = (f"OK（扫描 {scanned} 文件，0 命中；断言文件 "
               f"{_UMON_REQUIRED_FILE} 已读）" if not errs else
               f"FAIL（{len(errs)} 项）")
    return verdict, errs


def _fail(errs: list, msg: str) -> None:
    errs.append(msg)


def derive_carriers(vectors: str, errs: list) -> list:
    """现场派生载体清单（相对 --vectors 的路径，按目錄名 + 文件名排序）。"""
    carriers = []
    for d in CARRIER_DIRS:
        full = os.path.join(vectors, d)
        if not os.path.isdir(full):
            _fail(errs, f"载体目录缺失: {full}")
            continue
        names = []
        for f in sorted(os.listdir(full)):
            if not f.endswith(".yaml"):
                continue
            if not os.path.isfile(os.path.join(full, f)):
                _fail(errs, f"载体不是普通文件（断链/目录?）: {os.path.join(full, f)}")
                continue
            names.append(f)
        if not names:
            _fail(errs, f"载体目录 0 册（vacuous）: {full}")
            continue
        carriers.extend(os.path.join(d, n) for n in names)
    return carriers


def check_tracked(carriers: list, vectors: str, errs: list) -> str:
    """git 索引登记的载体册须全部在盘（缺册判据；真源 = git 索引）。"""
    try:
        repo = subprocess.run(
            ["git", "-C", _REPO_ROOT, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
    except OSError as exc:  # pragma: no cover - git 不在 PATH
        return f"SKIP（git 不可用: {exc}）"
    if repo.returncode != 0:
        return "SKIP（非 git 工作树）"
    rel_vectors = os.path.relpath(os.path.abspath(vectors), repo.stdout.strip())
    if rel_vectors.startswith(".."):
        return "SKIP（--vectors 不在本仓库内）"
    paths = [os.path.join(rel_vectors, d) for d in CARRIER_DIRS]
    out = subprocess.run(
        ["git", "-C", repo.stdout.strip(), "ls-files", "--", *paths],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        return f"SKIP（git ls-files rc={out.returncode}）"
    tracked = sorted(p for p in out.stdout.splitlines() if p.endswith(".yaml"))
    if not tracked:
        _fail(errs, "git 索引里没有任何载体册（vacuous）")
        return "FAIL（索引 0 册）"
    on_disk = {os.path.relpath(os.path.join(vectors, c), repo.stdout.strip())
               for c in carriers}
    missing = [p for p in tracked if p not in on_disk]
    for p in missing:
        _fail(errs, f"缺册: git 索引登记但工作树缺失: {p}")
    return (f"OK（索引 {len(tracked)} 册全部在盘）" if not missing
            else f"FAIL（缺 {len(missing)} 册）")


def load_cases(path: str, errs: list):
    try:
        with open(path, "r") as fh:
            cases = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        _fail(errs, f"载体不可读/非法 YAML: {path}: {exc}")
        return []
    if not isinstance(cases, list) or not cases:
        _fail(errs, f"载体为空或非 list: {path}")
        return []
    return cases


def prepare_gate_dir(gate_dir: str, vectors: str, carriers: list, errs: list) -> None:
    """建 gate 目录 + 逐册 symlink（错指/占用 ⇒ FAIL；不静默覆盖）。

    既有同名路径**不**先删：普通文件占用、或 symlink 指错 ⇒ 显式 FAIL
    （否则 ``ln -sf`` 会把错指静默覆盖，该断言就不可达）。
    """
    os.makedirs(gate_dir, exist_ok=True)
    for rel in carriers:
        src = os.path.abspath(os.path.join(vectors, rel))
        dst = os.path.join(gate_dir, os.path.basename(rel))
        if os.path.lexists(dst):
            if not os.path.islink(dst):
                _fail(errs, f"gate 路径被非 symlink 占用（stale）: {dst}")
                continue
            got = os.path.realpath(dst)
            if got != os.path.realpath(src):
                _fail(errs, f"symlink 指向错误: {dst} -> {got}"
                            f"（期望 {os.path.realpath(src)}）")
            continue
        try:
            os.symlink(src, dst)
        except OSError as exc:
            _fail(errs, f"symlink 失败: {dst} -> {src}: {exc}")
            continue
        if not os.path.islink(dst) or os.path.realpath(dst) != os.path.realpath(src):
            _fail(errs, f"symlink 校验失败: {dst} -> {os.path.realpath(dst)}")


def check_inventory_coverage(vectors: str, carriers: list, errs: list) -> str:
    """`tests/inst/inventory.md` 的「门控覆盖」表须与现场载体集**双向一致**。

    表是覆盖**登记**（人读真源），载体集是现场派生真源；二者任一方向多/少 ⇒ FAIL
    （新增向量册忘了登记、或登记了却没进载体，两种都会被打红）。
    """
    path = os.path.join(vectors, "inventory.md")
    try:
        with open(path, "r") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        _fail(errs, f"门控覆盖登记缺失: {path}: {exc}")
        return "FAIL（文件不可读）"

    n_errs0 = len(errs)
    l2_declared: set = set()      # basename
    l3_declared: dict = {}        # basename -> 表内写法的路径
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line.startswith("## 门控覆盖（L2/L3）")
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("册", "") \
                or set(cells[0]) <= set("-: "):
            continue  # 表头/分隔行
        name, l2, l3 = cells
        base = os.path.basename(name)
        if l2 == "✓":
            l2_declared.add(base)
        elif l2 != "—":
            _fail(errs, f"门控覆盖表 L2 列取值非法: {name} => {l2!r}")
        if l3 == "✓":
            l3_declared[base] = name
        elif l3 != "—":
            _fail(errs, f"门控覆盖表 L3 列取值非法: {name} => {l3!r}")

    if not l2_declared and not l3_declared:
        _fail(errs, "门控覆盖表为空（vacuous）")
        return "FAIL（0 行）"

    live_basenames = {os.path.basename(c) for c in carriers}
    live_paths = {c for c in carriers}
    missing_l3 = sorted(live_basenames - set(l3_declared))
    extra_l3 = sorted(set(l3_declared) - live_basenames)
    for b in missing_l3:
        _fail(errs, f"门控覆盖表未登记 L3 载体: {b}"
                    "（新增册须同步 inventory 登记 + 门控载体）")
    for b in extra_l3:
        _fail(errs, f"门控覆盖表登记了非现场 L3 载体: {l3_declared[b]}")
    for base, name in sorted(l3_declared.items()):
        if "/" in name and name not in live_paths:
            _fail(errs, f"门控覆盖表 L3 路径与现场不符: {name}")

    # L2：登记 == run_qemu_smoke 的代表集载体（basename）
    import run_qemu_smoke  # noqa: E402  (只取 GATE_VECTORS，不触发运行)
    l2_live = set(run_qemu_smoke.GATE_VECTORS)
    if l2_declared != l2_live:
        _fail(errs, "门控覆盖表 L2 列 != run_qemu_smoke.GATE_VECTORS: "
                    f"表多 {sorted(l2_declared - l2_live)} / "
                    f"表少 {sorted(l2_live - l2_declared)}")
    ok = len(errs) == n_errs0
    return (f"OK（L2 {len(l2_declared)} 册 / L3 {len(live_paths)} 册）"
            if ok else "FAIL")


def live_deferred(gate_dir: str) -> set:
    """gate 目录里 status=deferred 的精确用例集 {(basename, idx)}。"""
    out = set()
    for name in sorted(os.listdir(gate_dir)):
        if not name.endswith(".yaml"):
            continue
        try:
            with open(os.path.join(gate_dir, name), "r") as fh:
                cases = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(cases, list):
            continue
        for i, c in enumerate(cases):
            if isinstance(c, dict) and c.get("status") == "deferred":
                out.add((name, i))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="L3 semantic gate carrier derivation")
    ap.add_argument("--vectors", default=os.path.join(_REPO_ROOT, "tests", "inst"))
    ap.add_argument("--gate-dir", default=None,
                    help="gate 目录（--form-check 时可省）")
    ap.add_argument("--qemu", default=harness.DEFAULT_QEMU)
    ap.add_argument("--trampoline",
                    default=os.path.join(_REPO_ROOT, "tools", "testcases", "lib",
                                         "trampoline.bin"))
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--check-only", action="store_true",
                    help="只跑结构断言/派生（不执行用例；供证据脚本注入用）")
    ap.add_argument("--form-check", action="store_true",
                    help="只跑形态断言（ISS-225；无需 qemu 二进制，供 L1 门控用）")
    args = ap.parse_args()

    errs: list = []
    form_verdict, form_errs = check_no_umon_takeover(_REPO_ROOT)
    if args.form_check:
        print("check-qemu-forms: QEMU 形态断言（ISS-225）")
        print(f"  umon 接管形态: {form_verdict}")
        for e in form_errs:
            print(f"  FAIL: {e}")
        print("check-qemu-forms: " + ("PASS" if not form_errs else "FAIL (rc=1)"))
        return 0 if not form_errs else 1
    errs.extend(form_errs)
    if args.gate_dir is None:
        print("semantics_gate: ERROR: --gate-dir 必填（除 --form-check 外）",
              file=sys.stderr)
        return 1

    if not os.path.isfile(args.qemu):
        print(f"semantics_gate: ERROR: qemu binary not found: {args.qemu} "
              f"— run 'make install-host' first", file=sys.stderr)
        return 1
    if not os.path.isfile(args.trampoline):
        print(f"semantics_gate: ERROR: trampoline not found: {args.trampoline}",
              file=sys.stderr)
        return 1

    # ── 1. 现场派生 + 结构断言 ────────────────────────────────────────
    carriers = derive_carriers(args.vectors, errs)
    tracked_verdict = check_tracked(carriers, args.vectors, errs) if carriers else "SKIP"

    coverage_verdict = (check_inventory_coverage(args.vectors, carriers, errs)
                        if carriers else "SKIP")

    counts = {}
    seen = {}
    for rel in carriers:
        base = os.path.basename(rel)
        if base in seen:
            _fail(errs, f"重复 basename: {base}（{seen[base]} 与 {rel}）")
        seen[base] = rel
        counts[rel] = len(load_cases(os.path.join(args.vectors, rel), errs))

    if not errs:
        prepare_gate_dir(args.gate_dir, args.vectors, carriers, errs)

    total_cases = sum(counts.values())
    previous_basenames = set(PREVIOUS_CARRIERS)
    new_carriers = [c for c in carriers
                    if os.path.basename(c) not in previous_basenames]
    new_case_count = sum(counts[c] for c in new_carriers)

    print("check-inst: L3 语义载体（现场派生；册名/册数不写死）")
    print(f"  umon 接管形态（ISS-225）: {form_verdict}")
    print(f"  载体目录: {', '.join(os.path.join(args.vectors, d) for d in CARRIER_DIRS)}")
    print(f"  缺册断言（git 索引）: {tracked_verdict}")
    print(f"  覆盖登记（inventory.md ↔ 现场）: {coverage_verdict}")
    for rel in carriers:
        base = os.path.basename(rel)
        mark = "既有" if base in previous_basenames else "新增"
        print(f"    {mark} {rel}: {counts[rel]} 例")
    print(f"  载体册数: {len(carriers)}（现场统计）")
    print(f"  用例总数: {total_cases}（现场统计）")
    print(f"  改造前载体: {len(PREVIOUS_CARRIERS)} 册；本轮新增载体: "
          f"{len(new_carriers)} 册 / {new_case_count} 例")
    legacy3 = ("reg-shift-extend.yaml", "reg-compare.yaml", "aip-si.yaml")
    legacy3_live = sum(counts[c] for c in carriers
                       if os.path.basename(c) in legacy3)
    print(f"  旧三册现场计数: {legacy3_live}（ISS-235 历史登记值 "
          f"{ISS235_BASELINE_TOTAL}，差 {legacy3_live - ISS235_BASELINE_TOTAL:+d}）")

    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
        print("check-inst: FAIL（结构断言）")
        shutil.rmtree(args.gate_dir, ignore_errors=True)
        return 1

    if args.check_only:
        shutil.rmtree(args.gate_dir, ignore_errors=True)
        print("check-inst: 结构断言 PASS（--check-only，未执行用例）")
        return 0

    # ── 2. 执行（复用 harness 批量运行）────────────────────────────────
    deferred_live = live_deferred(args.gate_dir)
    deferred_extra = sorted(deferred_live - set(KNOWN_DEFERRED))
    deferred_missing = sorted(set(KNOWN_DEFERRED) - deferred_live)
    for key in deferred_extra:
        _fail(errs, f"未登记的 deferred 用例（禁批量豁免）: {key[0]}[{key[1]}]")
    for key in deferred_missing:
        _fail(errs, f"已登记 deferred 但向量里未挂: {key[0]}[{key[1]}]")
    print(f"  deferred 登记: {len(deferred_live)}/{len(KNOWN_DEFERRED)} 条"
          f"（精确名单：既有 C-27 5；禁按类/正则豁免；"
          f"{'一致' if not (deferred_extra or deferred_missing) else '不一致'}）")
    print("  gate 目录: %s（symlink 校验通过）" % args.gate_dir)
    print(f"  QEMU: {args.qemu}  jobs={args.jobs}")
    try:
        total, passed, failed, deferred, errors, fail_details = harness.run_batch(
            args.qemu, args.trampoline, args.gate_dir, jobs=args.jobs,
        )
    except Exception as exc:  # harness 异常也要清 gate 目录并显式失败
        shutil.rmtree(args.gate_dir, ignore_errors=True)
        print(f"  FAIL: harness 异常: {type(exc).__name__}: {exc}")
        print("check-inst: FAIL (rc=1)")
        return 1
    print(f"  Results: {total} total, {passed} passed, {failed} failed, "
          f"{deferred} deferred, {errors} errors")
    print(f"  基线差值: total {total} - ISS-235 旧值 {ISS235_BASELINE_TOTAL} = "
          f"{total - ISS235_BASELINE_TOTAL:+d}（旧值为历史登记值，非判据）")

    if total != total_cases:
        errs.append(f"运行 total {total} != 现场派生用例总数 {total_cases}")
    if failed or errors:
        errs.extend(fail_details)
        errs.append(f"非全绿: failed={failed} errors={errors}")
    if deferred:
        # deferred 只允许 KNOWN_DEFERRED 精确名单（上面已比对）；此处仅留 trace
        print(f"  deferred（已登记，不执行）: "
              f"{', '.join(f'{f}[{i}]' for f, i in sorted(deferred_live))}")
    if total - deferred <= 0:
        errs.append("0 cases executed（全 deferred）")

    shutil.rmtree(args.gate_dir, ignore_errors=True)

    print("-" * 72)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
        print("check-inst: FAIL (rc=1)")
        return 1
    print(f"check-inst: PASS（{passed}/{total}，载体 {len(carriers)} 册）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
