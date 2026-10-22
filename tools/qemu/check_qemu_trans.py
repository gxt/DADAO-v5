#!/usr/bin/env python3
"""check_qemu_trans.py — lint: 每条 insn 是否有对应的 trans_* 函数定义（双向）。

用法：
  python3 tools/qemu/check_qemu_trans.py [--yaml <opcodes.yaml>] [--src <patches_dir>] [--strict]

默认：
  - 读 contracts/opcodes.yaml
  - 递归搜索 components/qemu/patches/ 下的 **.patch**（树形补丁集：`<上游相对路径>.patch`）
  - 默认 exit 0；--strict 且存在缺失/残留时 exit 1
  - 扫不到任何补丁文件时**无条件**非零退出（无法校验 ≠ 通过）

两个方向（ISS-321）：
  * MISSING：opcodes.yaml 每条记录 → 期望 `trans_<unique>` 必须存在；
  * ORPHAN ：`trans_<unique>` 定义必须对应一条 opcodes 记录（删指令后残留的
    trans_* ⇒ 红，不再只靠 `check_interface` 的「数目不符」间接发现）。
"""

import argparse
import contextlib
import glob
import io
import os
import re
import shutil
import sys
import tempfile

# 复用 validate_decodetree 的命名函数（DRY）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from validate_decodetree import build_unique_func_names  # noqa: E402

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def collect_trans_defs(src_dir):
    """从 patch 文件中收集所有 trans_* 函数定义名（精确匹配）。

    补丁集为树形（`patches/<上游相对路径>.patch`），故须**递归**搜索。
    只计 '+'（新增行）和 ' '（上下文行），忽略 '-'（已删除行），
    防止前序 patch 的 '+' 行在后序 patch 删除后仍被误判为存在。
    返回 (定义名集合, 补丁文件数)。
    """
    trans_defs = set()
    patch_files = sorted(glob.glob(os.path.join(src_dir, "**", "*.patch"),
                                   recursive=True))
    pattern = re.compile(r'static\s+bool\s+(trans_\w+)\s*\(')
    for pf in patch_files:
        with open(pf, encoding="utf-8") as f:
            for line in f:
                # 只处理 '+'（新增）和 ' '（上下文）行；
                # 跳过 '-'（删除）行及 diff 头（'---'/'+++'/'@@'/'\ '）
                if line.startswith('-'):
                    continue
                m = pattern.search(line)
                if m:
                    trans_defs.add(m.group(1))
    return trans_defs, len(patch_files)


def run(yaml_path, src_dir, strict=False) -> int:
    with open(yaml_path, encoding="utf-8") as f:
        records = _yaml.safe_load(f)

    # 派生 trans_* 函数名
    func_names = build_unique_func_names(records)
    expected = {f"trans_{name}" for name in func_names}

    # 收集源中的 trans 定义
    trans_defs, n_patches = collect_trans_defs(src_dir)
    if n_patches == 0:
        print(f"ERROR: 在 {src_dir} 下未找到任何 .patch 文件；"
              "无法校验（补丁集为树形，请检查 --src 是否为 patches/ 根）",
              file=sys.stderr)
        return 2

    # 方向 1：记录 → trans（缺失）
    missing = []
    for rec, func_name in zip(records, func_names):
        exp = f"trans_{func_name}"
        if exp not in trans_defs:
            missing.append({
                "insn": rec["id"],
                "func": exp,
                "is_m1": rec.get("scope") == "m1",
            })

    # 方向 2：trans → 记录（残留；ISS-321）
    orphans = sorted(trans_defs - expected)

    total = len(records)
    m1_total = sum(1 for r in records if r.get("scope") == "m1")
    missing_total = len(missing)
    found_total = total - missing_total
    missing_m1 = sum(1 for m in missing if m["is_m1"])
    found_m1 = m1_total - missing_m1

    for m in missing:
        tag = " [M1]" if m["is_m1"] else ""
        print(f"MISSING: {m['insn']} -> {m['func']}{tag}")
    for name in orphans:
        print(f"ORPHAN: {name}（无对应 opcodes 记录：删指令后残留?）")

    print(f"check_qemu_trans: {found_total}/{total} insns have trans impl"
          f" (M1 {found_m1}/{m1_total}); orphan trans {len(orphans)}")

    if strict and (missing_total > 0 or orphans):
        print(f"check_qemu_trans: FAIL --strict（missing={missing_total}, "
              f"orphan={len(orphans)}）", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# --self-test：临时树注入（不改真实 patches/），两个方向各一条可达 FAIL。
# ---------------------------------------------------------------------------
def self_test() -> int:
    repo = REPO_ROOT
    tmp_root = os.path.join(tempfile.gettempdir(), "opencode", "INFRA-102t")
    os.makedirs(tmp_root, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="check-qemu-trans-", dir=tmp_root)
    try:
        src = os.path.join(tmpdir, "patches", "target", "dadao")
        os.makedirs(src)
        real_src = os.path.join(repo, "components", "qemu", "patches")
        # 只复制包含 trans_* 的补丁（双向统计只看这些），保持真实内容。
        def_re = re.compile(r"static\s+bool\s+(trans_\w+)\s*\(")
        patch_names = []
        for pf in glob.glob(os.path.join(real_src, "**", "*.patch"), recursive=True):
            text = open(pf, encoding="utf-8").read()
            if not def_re.search(text):
                continue
            dst = os.path.join(src, os.path.basename(pf))
            shutil.copyfile(pf, dst)
            patch_names.append(dst)
        if not patch_names:
            print("[FAIL] self-test: 真实补丁集里找不到 trans_* 定义")
            return 1
        target = patch_names[0]
        base_text = open(target, encoding="utf-8").read()

        def write_patch(text: str) -> None:
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text)

        def last_trans_name() -> str:
            names = re.findall(r'static\s+bool\s+(trans_\w+)\s*\(', base_text)
            return names[-1]

        def make_injection(text: str) -> str:
            """在补丁首个 @@ 后插入一行 '+' 定义（合法 diff 形状足够本 lint 解析）。"""
            idx = text.index("@@")
            eol = text.index("\n", idx) + 1
            return text[:eol] + "+static bool trans_zzz_injected(DisasContext *ctx, arg_main *a)\n" + text[eol:]

        cases = [
            ("baseline", base_text, 0, None, True),
            ("orphan-trans", make_injection(base_text), 1,
             "ORPHAN: trans_zzz_injected", True),
            ("missing-trans",
             re.sub(r'^\+static\s+bool\s+' + re.escape(last_trans_name()) + r'\s*\(',
                    "+static bool xxx_not_trans(", base_text, count=1, flags=re.M),
             1, "MISSING:", True),
            ("orphan-trans-not-strict", make_injection(base_text), 0, None, False),
        ]
        ok = True
        for i, (name, text, expect_rc, marker, strict) in enumerate(cases, 1):
            write_patch(text)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = run(os.path.join(repo, "contracts", "opcodes.yaml"),
                         os.path.join(tmpdir, "patches"), strict=strict)
            out = buf.getvalue()
            good = rc == expect_rc
            if marker and marker not in out:
                good = False
            if text == base_text and i > 1:
                good = False  # 空注入
            print(f"[{'PASS' if good else 'FAIL'}] self-test case{i} {name}: "
                  f"期望 rc={expect_rc} 实际 rc={rc}"
                  + (f"；marker={marker!r} {'命中' if marker and marker in out else ''}"
                     if marker else ""))
            if not good:
                print(out)
            ok = ok and good
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="检查每条 insn 是否有对应的 trans_* 函数定义")
    parser.add_argument("--yaml", default=os.path.join(REPO_ROOT, "contracts",
                                                        "opcodes.yaml"),
                        help="opcodes.yaml 路径（默认 contracts/opcodes.yaml）")
    parser.add_argument("--src", "--patches",
                        default=os.path.join(REPO_ROOT, "components", "qemu",
                                             "patches"),
                        help="patch 文件目录（默认 components/qemu/patches/）")
    parser.add_argument("--strict", action="store_true",
                        help="存在缺失或 orphan 残留时 exit 1（默认 exit 0）")
    parser.add_argument("--self-test", action="store_true",
                        help="临时树注入自检（两方向各一条可达 FAIL）")
    args = parser.parse_args()

    if args.self_test:
        rc = self_test()
        print(f"self-test: {'PASS' if rc == 0 else 'FAIL'}")
        return rc
    return run(args.yaml, args.src, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
