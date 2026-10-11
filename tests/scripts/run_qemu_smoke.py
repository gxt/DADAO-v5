#!/usr/bin/env python3
"""QEMU 语义冒烟门控（L2，INFRA-058t）。

用途：`check-qemu-smoke` 是 `check-qemu-semantics`（全量 149 用例）的**代表子集**，
落在 L2（`check-modules`）；全量留在 L3（`check-full`）。

代表集**机械派生**（禁手工挑）：把 `check-qemu-semantics` 的两个向量文件用例按
`(class, mnemonic)` 分组——`class` = 用例的语义类别（encoding/semantic/boundary/
legality），`mnemonic` = 指令语义类别——每组取文件序**第一条**为代表。

结构断言（fail-closed，`lessons §2.20`「自证命中」/`§2.21`「断言结构」）：
  - 代表集非空，且**每个源 `class` 与每个源 `mnemonic` 均有代表**（覆盖 ≥ 源集合）；
  - 运行结果 `total == 代表数`、`failed == errors == deferred == 0`。

Usage:
    python3 tests/scripts/run_qemu_smoke.py [--qemu BIN] [--trampoline BIN]
        [--vector-dir DIR] [--work-dir DIR] [--jobs N]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import OrderedDict

import yaml

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
sys.path.insert(0, _SCRIPT_DIR)

# 复用现有 harness（构建 + 运行 + 批量聚合），不另造轮子。
import run_qemu_test as harness  # noqa: E402

# check-qemu-semantics 的两个向量文件（与 Makefile 中 QEMU_SEM 保持同步）。
GATE_VECTORS = ("reg-shift-extend.yaml", "reg-compare.yaml")


def select_representatives(cases: list[dict]) -> "OrderedDict[tuple, dict]":
    """按 (class, mnemonic) 分组，每组取第一条为代表（机械派生，无手工清单）。"""
    groups: "OrderedDict[tuple, dict]" = OrderedDict()
    for case in cases:
        key = (case.get("class"), case.get("mnemonic"))
        groups.setdefault(key, case)  # first occurrence wins
    return groups


def main() -> int:
    ap = argparse.ArgumentParser(description="QEMU semantic smoke gate (L2)")
    ap.add_argument("--qemu", default=harness.DEFAULT_QEMU)
    ap.add_argument("--trampoline", default=os.path.join(_SCRIPT_DIR, "trampoline.bin"))
    ap.add_argument("--vector-dir", default=os.path.join(_REPO_ROOT, "tests", "vectors", "isa"))
    ap.add_argument("--work-dir", default=None,
                    help="subset write dir (default: <test-artifacts>/harness/smoke)")
    ap.add_argument("--jobs", type=int, default=1)
    args = ap.parse_args()

    if not os.path.isfile(args.qemu):
        print(f"run_qemu_smoke: ERROR: qemu binary not found: {args.qemu}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.trampoline):
        print(f"run_qemu_smoke: ERROR: trampoline not found: {args.trampoline}", file=sys.stderr)
        return 1

    work_dir = args.work_dir or str(harness._resolve_artifact_dir("smoke"))
    os.makedirs(work_dir, exist_ok=True)

    # ── 机械派生代表集 ────────────────────────────────────────────────
    selected: list[tuple[str, dict]] = []          # (source file, case)
    src_classes: set = set()
    src_mnemonics: set = set()
    per_class: dict = {}
    subset_by_file: "OrderedDict[str, list]" = OrderedDict()

    for vf in GATE_VECTORS:
        path = os.path.join(args.vector_dir, vf)
        if not os.path.isfile(path):
            print(f"run_qemu_smoke: ERROR: gate vector not found: {path}", file=sys.stderr)
            return 1
        with open(path, "r") as fh:
            cases = yaml.safe_load(fh)
        if not isinstance(cases, list) or not cases:
            print(f"run_qemu_smoke: ERROR: empty/invalid vector file {path}", file=sys.stderr)
            return 1
        for c in cases:
            src_classes.add(c.get("class"))
            src_mnemonics.add(c.get("mnemonic"))
        groups = select_representatives(cases)
        subset_by_file[vf] = [c for c in groups.values()]
        for c in groups.values():
            selected.append((vf, c))
            per_class[c.get("class")] = per_class.get(c.get("class"), 0) + 1

    # ── 结构断言（§2.20 自证命中 / §2.21 断言结构）────────────────────
    sel_classes = {c.get("class") for _, c in selected}
    sel_mnemonics = {c.get("mnemonic") for _, c in selected}

    print("run_qemu_smoke: 代表集机械派生 —— 按 (class, mnemonic) 各取 1 条")
    print(f"  源: {' + '.join(GATE_VECTORS)}")
    print(f"  源 class: {sorted(src_classes)}  ({len(src_classes)})")
    print(f"  源 mnemonic: {len(src_mnemonics)} 个")
    print(f"  代表集: {len(selected)} 条  (按 class: {dict(sorted(per_class.items()))})")
    print("  (计数现场统计，不写死)")

    errs = []
    if not selected:
        errs.append("代表集为空")
    if sel_classes != src_classes:
        errs.append(f"class 覆盖不全: 缺 {sorted(src_classes - sel_classes)}")
    if sel_mnemonics != src_mnemonics:
        errs.append(f"mnemonic 覆盖不全: 缺 {sorted(src_mnemonics - sel_mnemonics)}")

    # ── 写子集 YAML 并复用 harness 批量运行 ──────────────────────────
    if not errs:
        for vf, reps in subset_by_file.items():
            out = os.path.join(work_dir, vf)
            with open(out, "w") as fh:
                yaml.safe_dump(reps, fh, sort_keys=True)

        total, passed, failed, deferred, errors, fail_details = harness.run_batch(
            args.qemu, args.trampoline, work_dir, jobs=args.jobs,
        )
        print(f"  QEMU: total={total} passed={passed} failed={failed} "
              f"deferred={deferred} errors={errors}")
        if total != len(selected):
            errs.append(f"运行条数 {total} != 代表数 {len(selected)}")
        if failed or errors or deferred:
            errs.extend(fail_details)
            errs.append(f"非全绿: failed={failed} errors={errors} deferred={deferred}")

    print("-" * 72)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
        print("结果: FAIL")
        return 1
    print("结果: PASS (代表集全绿 + 结构断言通过)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
