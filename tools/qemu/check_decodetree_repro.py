#!/usr/bin/env python3
"""check_decodetree_repro.py — QEMU decodetree 输出 bit-reproducible 门控（ISS-058）。

背景
----
QEMU 上游 `scripts/decodetree.py` 输出的**字段赋值顺序**依赖 Python 集合迭代，
即依赖 `PYTHONHASHSEED`（实测：seed 0/1/2/12345 产出 md5 各不相同）。同一
源、不同构建 ⇒ 生成 C 不同 ⇒ 二进制不可复现。

处置（用户要求「固定 PYTHONHASHSEED」）
--------------------------------------
* **构建侧**：`Makefile` 的 `build-qemu` / `build-qemu-reconfig` 两条 recipe 在
  调用 `$(MAKE) -C $(QEMU_BUILD)` 时必须带 `PYTHONHASHSEED=0` 前缀（ninja 继承
  环境 ⇒ decodetree 子进程拿到固定 seed）。
* **门控**：本脚本断言这两条 recipe **都**固定了 seed；若
  `.work/source/qemu` 存在，再实际跑 `decodetree.py` 两种 seed 对比：
  - 输出随 seed 变 ⇒ 必须已固定（固定后才 PASS；未固定 ⇒ FAIL）；
  - 输出不随 seed 变 ⇒ 也 PASS（无敏感性问题）。
  两 seed 均固定为 0 的**同一** seed 时输出必须逐字节一致（确定性自证）。

用法：
  python3 tools/qemu/check_decodetree_repro.py
  python3 tools/qemu/check_decodetree_repro.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
# 产出 decodetree C 的构建目标（recipe 内的 make/ninja 必须继承固定 seed）。
BUILD_TARGETS = ("_locked-build-qemu", "_locked-build-qemu-reconfig")
SEED_ENV = "PYTHONHASHSEED=0"
QEMU_SRC = ROOT / ".work" / "source" / "qemu"
DECODETREE = QEMU_SRC / "scripts" / "decodetree.py"
DECODE_INPUT = QEMU_SRC / "target" / "dadao" / "insn.decode"


def recipe_of(text: str, target: str) -> str:
    """取 Makefile 某 target 的 recipe（续行合并；到下一个非缩进行止）。"""
    lines = text.splitlines()
    out: list[str] = []
    active = False
    for line in lines:
        if not active:
            if re.match(rf"^{re.escape(target)}\s*:", line):
                active = True
            continue
        if line.startswith("\t"):
            out.append(line.strip())
            continue
        if line.strip() == "":
            continue
        break
    return "\n".join(out)


def form_check(makefile_text: str) -> tuple[list[str], list[str]]:
    """逐构建目标断言 `$(MAKE) -C $(QEMU_BUILD)` 前有 PYTHONHASHSEED=0。"""
    ok: list[str] = []
    bad: list[str] = []
    for target in BUILD_TARGETS:
        recipe = recipe_of(makefile_text, target)
        if not recipe:
            bad.append(f"{target}: recipe 未找到（无法断言 seed 固定）")
            continue
        invocations = [ln for ln in recipe.splitlines()
                       if "$(MAKE)" in ln and "-C $(QEMU_BUILD)" in ln]
        if not invocations:
            bad.append(f"{target}: 未找到 `$(MAKE) -C $(QEMU_BUILD)` 调用")
            continue
        unpinned = [ln for ln in invocations if SEED_ENV not in ln]
        if unpinned:
            bad.append(f"{target}: 调用未固定 {SEED_ENV}: {unpinned[0]}")
        else:
            ok.append(f"{target}: {len(invocations)} 处调用均固定 {SEED_ENV}")
    return ok, bad


def run_decodetree(seed: str, out_path: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    proc = subprocess.run(
        [sys.executable, str(DECODETREE), "-o", str(out_path), str(DECODE_INPUT)],
        env=env, capture_output=True, text=True)
    return proc.returncode, (proc.stderr or "").strip()[:200]


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def repro_check(tmpdir: Path) -> tuple[list[str], list[str]]:
    ok: list[str] = []
    bad: list[str] = []
    if not DECODETREE.is_file() or not DECODE_INPUT.is_file():
        return [f"SKIP（.work/source/qemu 缺失：{DECODETREE}）"], bad
    a = tmpdir / "seed0.c"
    b = tmpdir / "seed1.c"
    c = tmpdir / "seed0-again.c"
    for path, seed in ((a, "0"), (b, "1"), (c, "0")):
        rc, err = run_decodetree(seed, path)
        if rc != 0:
            bad.append(f"decodetree seed={seed} rc={rc}: {err}")
            return ok, bad
    if _md5(a) != _md5(c):
        bad.append("decodetree 同一 seed=0 两次输出不同（非确定性）")
    else:
        ok.append(f"decodetree seed=0 两次输出一致（md5 {_md5(a)[:12]}）")
    if _md5(a) != _md5(b):
        ok.append("decodetree 输出对 PYTHONHASHSEED 敏感 ⇒ 构建必须固定 seed"
                  f"（seed0={_md5(a)[:12]} seed1={_md5(b)[:12]}）")
    else:
        ok.append("decodetree 输出对 PYTHONHASHSEED 不敏感（无需固定亦可复现）")
    return ok, bad


def run(makefile_path: Path = MAKEFILE) -> int:
    if not makefile_path.is_file():
        print(f"check-decodetree-repro: FAIL — Makefile 缺失: {makefile_path}",
              file=sys.stderr)
        return 1
    form_ok, bad = form_check(makefile_path.read_text(encoding="utf-8"))
    for msg in form_ok:
        print(f"[PASS] {msg}")
    for msg in bad:
        print(f"[FAIL] {msg}", file=sys.stderr)

    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "INFRA-102t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="decodetree-repro-", dir=tmp_root))
    try:
        repro_ok, repro_bad = repro_check(tmpdir)
        for msg in repro_ok:
            print(f"[PASS] {msg}")
        for msg in repro_bad:
            print(f"[FAIL] {msg}", file=sys.stderr)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if bad or repro_bad:
        print(f"check-decodetree-repro: FAIL（{len(bad) + len(repro_bad)} 项）",
              file=sys.stderr)
        return 1
    print("check-decodetree-repro: PASS")
    return 0


def self_test() -> int:
    base = MAKEFILE.read_text(encoding="utf-8")
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "INFRA-102t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="decodetree-form-", dir=tmp_root))
    try:
        plans = []
        plans.append(("baseline", base, 0))
        for target in BUILD_TARGETS:
            recipe = recipe_of(base, target)
            assert SEED_ENV in recipe, target
            pinned = [ln for ln in recipe.splitlines()
                      if "$(MAKE)" in ln and SEED_ENV in ln][0]
            unpinned = pinned.replace(SEED_ENV + " ", "")
            plans.append((f"unpin-{target}", base.replace(pinned, unpinned), 1))
        ok = True
        for i, (name, text, expect_rc) in enumerate(plans, 1):
            path = tmpdir / f"Makefile-{i}"
            path.write_text(text, encoding="utf-8")
            form_ok, bad = form_check(text)
            rc = 0 if not bad else 1
            good = rc == expect_rc and (expect_rc == 0 or text != base)
            print(f"[{'PASS' if good else 'FAIL'}] self-test case{i} {name}: "
                  f"期望 rc={expect_rc} 实际 rc={rc}")
            ok = ok and good
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--makefile", default=str(MAKEFILE))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        rc = self_test()
        print(f"self-test: {'PASS' if rc == 0 else 'FAIL'}")
        return rc
    return run(Path(args.makefile))


if __name__ == "__main__":
    raise SystemExit(main())
