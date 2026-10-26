#!/usr/bin/env python3
"""check_tests_index.py — `tests/*.yaml` 根级索引门控（TESTCASES-071t，L1）。

规范来源：`docs/Process-09-测试组织规范.md` §3（四 scope 目录）与 §5（根级 case 清单）。
本门控只做**静态**校验，不跑被测语义（L1）。

检查（全部 fail-closed；计数一律现场派生，不写死）：
  1. 四个 scope 索引文件 `tests/{inst,arch,unit,tset}.yaml` 必须存在，且
     `tests/<scope>/` 目录必须存在；`tests/` 根下**任何** `*.yaml` 的 stem
     必须是合法 scope（禁止 `tests/index/`、`tests/manifest/` 之类旁路）。
  2. 顶层必须是 list（空文件视作空列表，`[]` 亦合法）。
  3. 每条目字段**恰好** `id/file/platforms/level/requires`（无缺字段/未知字段）。
  4. `id` 形如 `<scope>-<name>[-<name>...]-<nnn>`（三段以上），且前缀 scope
     必须等于所在索引的 scope。
  5. `file` 是 `tests/` 下的相对路径、位于 `<scope>/` 下、且实际存在（且为文件）。
  6. `platforms` 非空、无重复、取值属于该 scope 的允许集：
     inst = system（user/hw 预留）；arch = system（hw 预留）；
     unit = host/toolchain；tset = user（hw 预留）。
  7. `level ∈ {smoke, full}`；`requires` = 无重复的非空字符串列表。
  8. `id` 在四份索引内**全局唯一**。

用法：
  python3 tools/testcases/check_tests_index.py               # 门控（默认）
  python3 tools/testcases/check_tests_index.py --self-test   # 干净基线 + 各类注入
  python3 tools/testcases/check_tests_index.py --root DIR    # 检查另一棵树
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

import yaml

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

ROOT = Path(__file__).resolve().parents[2]
TESTS_REL = "tests"
SCOPES = ("inst", "arch", "unit", "tset")
# Process-09 §7：inst 首期只 system，user 预留；hw = 将来硬件在环（全 scope 预留）。
SCOPE_PLATFORMS = {
    "inst": ("system", "user", "hw"),
    "arch": ("system", "hw"),
    "unit": ("host", "toolchain"),
    "tset": ("user", "hw"),
}
FIELDS = ("id", "file", "platforms", "level", "requires")
LEVELS = ("smoke", "full")
ID_RE = re.compile(r"^(?P<scope>[a-z]+)-(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<num>\d{3})$")


def _load_index(path: Path) -> tuple[object, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"无法读取: {exc}"
    try:
        return yaml.load(text, Loader=_YAML_LOADER), None
    except yaml.YAMLError as exc:
        return None, f"YAML 解析失败: {exc}"


def _check_entry(
    entry: object,
    scope: str,
    idx: int,
    tests_root: Path,
    errors: list[str],
) -> str | None:
    """校验单条目；返回 id（供全局唯一性检查；无效时为 None）。"""
    where = f"tests/{scope}.yaml 第 {idx} 条"
    if not isinstance(entry, dict):
        errors.append(f"{where}: 条目必须是映射，实为 {type(entry).__name__}")
        return None

    keys = set(entry)
    missing = [f for f in FIELDS if f not in keys]
    unknown = sorted(keys - set(FIELDS))
    if missing:
        errors.append(f"{where}: 缺字段 {missing}")
    if unknown:
        errors.append(f"{where}: 未知字段 {unknown}（允许: {list(FIELDS)}）")

    cid = entry.get("id")
    if not isinstance(cid, str) or not cid:
        errors.append(f"{where}: `id` 必须是非空字符串")
        cid = None
    else:
        m = ID_RE.match(cid)
        if not m:
            errors.append(f"{where}: `id`=`{cid}` 不合 `<scope>-<name>[-<name>...]-<nnn>`")
        elif m.group("scope") != scope:
            errors.append(
                f"{where}: `id` 前缀 `{m.group('scope')}` ≠ 所在索引 scope `{scope}`")

    rel = entry.get("file")
    if not isinstance(rel, str) or not rel:
        errors.append(f"{where}: `file` 必须是非空字符串")
    else:
        pure = PurePosixPath(rel)
        if pure.is_absolute():
            errors.append(f"{where}: `file`=`{rel}` 必须是 `tests/` 下相对路径（禁绝对路径）")
        elif ".." in pure.parts:
            errors.append(f"{where}: `file`=`{rel}` 含 `..`（禁止越出 `tests/`）")
        elif not pure.parts or pure.parts[0] != scope:
            errors.append(f"{where}: `file`=`{rel}` 不在 scope 目录 `{scope}/` 下")
        else:
            target = tests_root / pure
            try:
                target.resolve().relative_to(tests_root.resolve())
            except (ValueError, OSError):
                errors.append(f"{where}: `file`=`{rel}` 解析后越出 `tests/`")
            else:
                if not target.exists():
                    errors.append(f"{where}: `file` 不存在: tests/{rel}")
                elif not target.is_file():
                    errors.append(f"{where}: `file` 不是文件: tests/{rel}")

    platforms = entry.get("platforms")
    got_platforms: list[str] = []
    if not isinstance(platforms, list) or not platforms:
        errors.append(f"{where}: `platforms` 必须是非空列表")
    else:
        got_platforms = [p for p in platforms if isinstance(p, str)]
        if len(got_platforms) != len(platforms):
            errors.append(f"{where}: `platforms` 只能含字符串: {platforms}")
        if len(set(got_platforms)) != len(got_platforms):
            errors.append(f"{where}: `platforms` 有重复: {got_platforms}")
        bad = [p for p in got_platforms if p not in SCOPE_PLATFORMS[scope]]
        if bad:
            errors.append(
                f"{where}: `platforms` 非法 {bad}（scope `{scope}` 允许 "
                f"{list(SCOPE_PLATFORMS[scope])}）")

    level = entry.get("level")
    if level not in LEVELS:
        errors.append(f"{where}: `level`=`{level!r}` 须为 {list(LEVELS)}")

    requires = entry.get("requires")
    if not isinstance(requires, list):
        errors.append(f"{where}: `requires` 必须是列表（可为空）")
    else:
        bad_req = [r for r in requires if not isinstance(r, str) or not r]
        if bad_req:
            errors.append(f"{where}: `requires` 含非字符串/空串: {bad_req!r}")
        reqs = [r for r in requires if isinstance(r, str)]
        if len(set(reqs)) != len(reqs):
            errors.append(f"{where}: `requires` 有重复: {reqs}")

    return cid


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-tests-index — tests/ 根级索引（L1）")
    print("=" * 72)
    errors: list[str] = []
    tests_root = root / TESTS_REL

    if not tests_root.is_dir():
        print(f"  ERROR: `tests/` 不存在: {tests_root} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1

    # ── 1. tests/ 根下 *.yaml 必须都是 scope 索引；四个索引/目录必须存在 ──
    root_yamls = sorted(p for p in tests_root.glob("*.yaml") if p.is_file())
    for path in root_yamls:
        if path.stem not in SCOPES:
            errors.append(
                f"tests/{path.name}: 根级 `*.yaml` 的 scope `{path.stem}` 不合法"
                f"（允许 {list(SCOPES)}；禁止 `tests/index/`、`tests/manifest/` 等旁路）")

    counts: dict[str, int] = {}
    seen_ids: dict[str, str] = {}
    for scope in SCOPES:
        index_path = tests_root / f"{scope}.yaml"
        scope_dir = tests_root / scope
        if not scope_dir.is_dir():
            errors.append(f"tests/{scope}/: scope 目录不存在")
        if not index_path.is_file():
            errors.append(f"tests/{scope}.yaml: 索引文件不存在")
            continue

        data, err = _load_index(index_path)
        if err:
            errors.append(f"tests/{scope}.yaml: {err}")
            continue
        if data is None:
            data = []  # 空文件 = 空列表
        if not isinstance(data, list):
            errors.append(
                f"tests/{scope}.yaml: 顶层必须是列表（空列表亦合法），实为 "
                f"{type(data).__name__}")
            continue

        counts[scope] = len(data)
        for idx, entry in enumerate(data, 1):
            cid = _check_entry(entry, scope, idx, tests_root, errors)
            if cid is None:
                continue
            if cid in seen_ids:
                errors.append(
                    f"tests/{scope}.yaml 第 {idx} 条: `id`=`{cid}` 重复"
                    f"（已在 {seen_ids[cid]} 出现）")
            else:
                seen_ids[cid] = f"tests/{scope}.yaml 第 {idx} 条"

    total = sum(counts.values())
    print(f"  scope 索引文件（现场统计）: {len(root_yamls)} 个根级 *.yaml；"
          f"合法 scope 索引 {len(counts)}/{len(SCOPES)}")
    print("  条目计数（现场派生）: " + " / ".join(
        f"{s}={counts.get(s, 0)}" for s in SCOPES) + f" / total={total}")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"结果: PASS（{total} 条；ID 唯一 / file 存在 / 字段·平台·level 合法 / "
          f"scope 合法）")
    return 0


# ---------------------------------------------------------------------------
# self-test：临时树 + 干净基线 + 各类注入（每条断言均有可达 FAIL）
# ---------------------------------------------------------------------------

def _write_tree(
    root: Path,
    indexes: dict[str, str],
    extra_files: dict[str, str] | None = None,
) -> None:
    for scope in SCOPES:
        (root / TESTS_REL / scope).mkdir(parents=True, exist_ok=True)
    for scope, text in indexes.items():
        (root / TESTS_REL / f"{scope}.yaml").write_text(text, encoding="utf-8")
    for rel, text in (extra_files or {}).items():
        path = root / TESTS_REL / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _empty_indexes() -> dict[str, str]:
    return {scope: "[]\n" for scope in SCOPES}


VALID_ENTRY = """\
- id: inst-base-001
  file: inst/base/add.yaml
  platforms: [system]
  level: smoke
  requires: []
"""


def _run(root: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit(root)
    return rc, buf.getvalue()


def self_test() -> int:
    print("=" * 72)
    print("check-tests-index --self-test（干净基线 PASS + 注入各自 FAIL）")
    print("=" * 72)
    tmp_base = Path(tempfile.gettempdir()) / "opencode" / "TESTCASES-071t"
    tmp_base.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="tests-index-", dir=tmp_base))
    ok = True
    try:
        case_no = 0

        def case(
            name: str,
            indexes: dict[str, str],
            marker: str | None,
            extra_files: dict[str, str] | None = None,
            expect_rc: int = 1,
        ) -> None:
            nonlocal ok, case_no
            case_no += 1
            work = tmpdir / f"case{case_no}"
            _write_tree(work, indexes, extra_files)
            rc, out = _run(work)
            hit = marker is None or marker in out
            good = rc == expect_rc and hit
            ok = ok and good
            print(f"  [{'PASS' if good else 'FAIL'}] self-test case{case_no} {name}: "
                  f"期望 rc={expect_rc} 实际 rc={rc} marker={hit}")

        # 干净基线①：四个空索引（`[]` 与空文件均合法）
        empty = _empty_indexes()
        empty["inst"] = ""
        case("干净基线·空索引", empty, None, expect_rc=0)
        # 干净基线②：一条合法条目
        good = _empty_indexes()
        good["inst"] = VALID_ENTRY
        case("干净基线·一条合法条目", good, None,
             extra_files={"inst/base/add.yaml": "# demo\n"}, expect_rc=0)

        # 注入①：ID 重复
        dup = dict(good)
        dup["inst"] = VALID_ENTRY + VALID_ENTRY
        case("注入① ID 重复", dup, "重复",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入②：file 不存在
        bad = dict(_empty_indexes())
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.yaml", "inst/base/nope.yaml")
        case("注入② file 不存在", bad, "不存在")

        # 注入③：platforms 非法
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("[system]", "[windows]")
        case("注入③ platforms 非法", bad, "platforms",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入④：level 非法
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("level: smoke", "level: quick")
        case("注入④ level 非法", bad, "level",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑤：ID 前缀与索引 scope 不一致
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("id: inst-base-001", "id: arch-base-001")
        case("注入⑤ ID 前缀错配", bad, "前缀",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑥：缺字段
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("  requires: []\n", "")
        case("注入⑥ 缺字段", bad, "缺字段",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑦：未知字段
        bad = dict(good)
        bad["inst"] = VALID_ENTRY + "  owner: nobody\n"
        case("注入⑦ 未知字段", bad, "未知字段",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑧：file 不在本 scope 目录
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.yaml", "arch/base/add.yaml")
        case("注入⑧ file 越 scope", bad, "不在 scope 目录",
             extra_files={"arch/base/add.yaml": "# demo\n"})

        # 注入⑨：tests/ 根下出现非法 scope 索引
        bad = dict(_empty_indexes())
        case("注入⑨ 非法 scope 索引文件", bad, "不合法",
             extra_files={"tst.yaml": "[]\n"})

        # 注入⑩：YAML 解析失败
        bad = dict(_empty_indexes())
        bad["inst"] = "- id: [unclosed\n"
        case("注入⑩ YAML 解析失败", bad, "YAML 解析失败")

        # 注入⑪：顶层不是列表
        bad = dict(_empty_indexes())
        bad["inst"] = "{}\n"
        case("注入⑪ 顶层非列表", bad, "顶层必须是列表")

        # 注入⑫：file 指向目录（不是文件）
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.yaml", "inst/base")
        case("注入⑫ file 指向目录", bad, "不是文件",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑬：scope 目录缺失
        bad = dict(_empty_indexes())
        case_dir_work = tmpdir / "case-dir"
        case_dir_work.mkdir()
        _write_tree(case_dir_work, bad)
        shutil.rmtree(case_dir_work / TESTS_REL / "tset")
        rc, out = _run(case_dir_work)
        good_dir = rc == 1 and "scope 目录不存在" in out
        ok = ok and good_dir
        print(f"  [{'PASS' if good_dir else 'FAIL'}] self-test case-dir "
              f"注入⑬ scope 目录缺失: rc={rc} marker={'scope 目录不存在' in out}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("-" * 72)
    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help="检查另一棵树（默认仓库根）")
    ap.add_argument("--self-test", action="store_true", help="跑内置注入自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-tests-index: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
