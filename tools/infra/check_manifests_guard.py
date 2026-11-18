#!/usr/bin/env python3
"""check-manifests-guard: 目录清单门控（`.manifests.toml`，m15-infra-005）。

**目的**：目录/文件没有「只能放什么」的机械约束 ⇒ 新增逃逸、删除无声。本门控把
「目录里允许什么」落为**清单数据**并**双向**断言（多一个、少一个都红）。

**必需清单注册表（`manifests/dir-guard-roots.toml`，Schema v1）**

    schema = 1
    roots  = ["spec", ".tao", ".tao/knowledge"]   # 必须有 `.manifests.toml` 的目录

门控**按注册表逐个校验**（不是「扫到什么管什么」）——删某份清单不再等于关闭对该目录的
约束：注册表登记的目录缺清单 ⇒ FAIL。注册表自身缺失/不可解析 ⇒ FAIL（否则删注册表即关闭）。
**游离清单**（磁盘上有 `.manifests.toml` 但所在目录未登记）⇒ **FAIL**：只提示的话，
新增清单会被静默忽略（门控不生效）＝ 另一个 fail-open，故按红处理，登记一行即可。

**清单 Schema（v1）**

    schema    = 1                 必填
    owner     = "<name>"          可选，**声明性**：值只打印；键悬空判红
    subdirs   = ["a", "b"]        允许的**直接**子目录；空 = 禁止建子目录
    recursive = false             可选；true ⇒ 对每个 `subdirs` 子目录**递归**套用本清单的
                                  `files`/`subdirs` 规则（第一批无使用者；`--self-test` 覆盖）

    [files."<name>"]
    sha256 = "<64 hex>"           可选；有则逐字节校验
    owner  = "<name>"             可选；只打印

    [subdir_owners]               可选，**声明性**映射：`子目录名 = "模块"`；门控只打印，
                                  不判红；但**键必须属于 `subdirs`**（悬空 ⇒ FAIL，见 A8）。
                                  未填合法（向后兼容：`spec/`、`.tao/`、`.tao/knowledge/`）。

**断言（任一不满足 ⇒ 非零退出）**

  A0 **注册表 fail-closed**：注册表缺失 / 不可解析 / `roots` 空 ⇒ FAIL；登记目录不存在、
     或该目录缺 `.manifests.toml` ⇒ FAIL（点名目录）；游离清单 ⇒ FAIL；
  A1 清单可解析、`schema == 1`、未知键 ⇒ FAIL（拼写错误不得静默通过）；
  A2 **双向文件集合**：目录的**直接子文件**（**清单自身不计**）== `files` 的键；
  A3 **双向子目录集合**：直接子目录 == `subdirs`；
  A4 `files` 的键必须是**直接子文件名**（不含 `/`），且**不得**为 `.manifests.toml`；
  A5 带 `sha256` 的条目逐字节校验（不符 ⇒ 打印期望/实际）；
  A6 `recursive = true` ⇒ 对每个子目录递归套用 A2/A4/A5（**单向 ⊆**：只禁多出，
     不要求每个声明名在每层都出现）；子目录里若另有 `.manifests.toml`，它由**自己那条**
     清单管（不在此处计入集合，也不得被父清单列入）；
  A7 **fail-closed**：某清单 `files`/`subdirs` 皆空 ⇒ FAIL；
  A8 `[subdir_owners]`（可选）：值须为非空字符串；**键必须属于 `subdirs`**——
     悬空 owner（拼错/子目录已删）⇒ FAIL，防止声明性与实际脱钩后静默失效。

**实际集合**：目录内容一律取**磁盘**（遍历时剪掉 `.git`、`.work`、`.cache` 三个目录）——
新增册即使未提交也红（`spec/` 新增逃逸正是要堵的缺口）。

Usage:
    python3 tools/infra/check_manifests_guard.py [--root DIR]
    python3 tools/infra/check_manifests_guard.py --self-test

Exit code: 0 = 全部通过；1 = 有违例（或自检有未达预期项）。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ".manifests.toml"
REGISTRY = Path("manifests") / "dir-guard-roots.toml"
ALLOWED_TOP = frozenset({"schema", "owner", "subdirs", "recursive", "files", "subdir_owners"})
ALLOWED_REGISTRY = frozenset({"schema", "roots"})
ALLOWED_ENTRY = frozenset({"sha256", "owner"})
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PRUNE = {".git", ".work", ".cache"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def discover(root: Path) -> list[Path]:
    """Return every manifest path under `root` (sorted).

    一律**遍历磁盘**（剪掉 `.git`、`.work`、`.cache` 三个目录）：未提交的清单也纳入校验，
    避免「新增目录 + 清单未提交」被静默放过（fail-closed）。
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)
        if MANIFEST in filenames:
            found.append(Path(dirpath) / MANIFEST)
    return sorted(found)


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_registry(root: Path, errors: list[str]) -> list[str] | None:
    """Read the required-manifest registry. Missing/unparsable ⇒ FAIL (fail-closed)."""
    path = root / REGISTRY
    if not path.is_file():
        errors.append(
            f"{REGISTRY.as_posix()}: 注册表缺失（必需清单目录的唯一真源；删它等于关闭本门控）")
        return None
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"{REGISTRY.as_posix()}: 无法解析 TOML：{exc}")
        return None

    unknown = sorted(set(doc) - ALLOWED_REGISTRY)
    if unknown:
        errors.append(
            f"{REGISTRY.as_posix()}: 未知顶层键 {unknown}（允许 {sorted(ALLOWED_REGISTRY)}）")
    if doc.get("schema") != 1:
        errors.append(f"{REGISTRY.as_posix()}: schema 须为 1（实际 {doc.get('schema')!r}）")

    roots = doc.get("roots")
    if not isinstance(roots, list) or not roots:
        errors.append(f"{REGISTRY.as_posix()}: roots 须为非空目录列表（实际 {roots!r}）")
        return []
    bad = [r for r in roots if not isinstance(r, str) or not r
           or r.startswith("/") or any(part in ("", ".", "..") for part in Path(r).parts)]
    if bad:
        errors.append(f"{REGISTRY.as_posix()}: roots 须为仓库内相对目录（非法项 {bad}）")
        return [r for r in roots if isinstance(r, str) and r not in bad]
    dup = sorted({r for r in roots if roots.count(r) > 1})
    if dup:
        errors.append(f"{REGISTRY.as_posix()}: roots 有重复项 {dup}")
    return [str(Path(r)) for r in roots]


def required_manifests(root: Path, roots: list[str], errors: list[str]) -> list[Path]:
    """Map registry roots → manifest paths; missing dir/manifest ⇒ FAIL."""
    out: list[Path] = []
    for rel in roots:
        directory = root / rel
        if not directory.is_dir():
            errors.append(f"{rel}: 注册表登记的目录不存在（{REGISTRY.as_posix()} 要求它带 {MANIFEST}）")
            continue
        manifest = directory / MANIFEST
        if not manifest.is_file():
            errors.append(f"{rel}: 缺少清单 {MANIFEST}（该目录已登记在 {REGISTRY.as_posix()}，删清单不放行）")
            continue
        out.append(manifest)

    registered_dirs = {(root / rel).resolve() for rel in roots}
    for path in discover(root):
        if path.parent.resolve() not in registered_dirs:
            errors.append(
                f"{_rel(root, path)}: 游离清单（所在目录未登记在 {REGISTRY.as_posix()}）"
                f"⇒ 该清单一律不生效；如需启用请在注册表加一行")
    return out


def load_manifest(path: Path, errors: list[str]) -> dict | None:
    """Parse + structural validation. Returns the doc when structurally usable."""
    where = str(path)
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"{where}: 无法解析 TOML：{exc}")
        return None

    unknown = sorted(set(doc) - ALLOWED_TOP)
    if unknown:
        errors.append(f"{where}: 未知顶层键 {unknown}（允许 {sorted(ALLOWED_TOP)}）")
    if doc.get("schema") != 1:
        errors.append(f"{where}: schema 须为 1（实际 {doc.get('schema')!r}）")

    subdirs = doc.get("subdirs", [])
    if not isinstance(subdirs, list) or any(not isinstance(s, str) or not s for s in subdirs):
        errors.append(f"{where}: subdirs 须为非空字符串列表（实际 {subdirs!r}）")
        subdirs = []
    else:
        dup = sorted({s for s in subdirs if subdirs.count(s) > 1})
        if dup:
            errors.append(f"{where}: subdirs 有重复项 {dup}")
        bad = sorted(s for s in subdirs if "/" in s or "\\" in s or s in (".", ".."))
        if bad:
            errors.append(f"{where}: subdirs 只允许直接子目录名（非法项 {bad}）")

    recursive = doc.get("recursive", False)
    if not isinstance(recursive, bool):
        errors.append(f"{where}: recursive 须为布尔（实际 {recursive!r}）")

    files = doc.get("files", {})
    if not isinstance(files, dict):
        errors.append(f"{where}: files 须为表（实际 {type(files).__name__}）")
        files = {}

    subdir_owners = doc.get("subdir_owners", {})
    if not isinstance(subdir_owners, dict):
        errors.append(f"{where}: subdir_owners 须为表（实际 {type(subdir_owners).__name__}）")
        subdir_owners = {}
    for name, owner in sorted(subdir_owners.items()):
        if not isinstance(owner, str) or not owner:
            errors.append(f"{where}: subdir_owners[{name!r}] 须为非空字符串（实际 {owner!r}）")
            continue
        if name not in subdirs:
            errors.append(
                f"{where}: subdir_owners[{name!r}] 悬空 owner（不在 subdirs 中；"
                f"子目录名须与 subdirs 一致，实际 subdirs={subdirs}）")

    for name, entry in sorted(files.items()):
        if not isinstance(name, str) or not name:
            errors.append(f"{where}: files 键须为非空字符串（实际 {name!r}）")
            continue
        if name == MANIFEST:
            errors.append(f"{where}: files 不得列入清单自身 `{MANIFEST}`（自身不计入集合）")
        if "/" in name or "\\" in name or name in (".", ".."):
            errors.append(f"{where}: files 键 {name!r} 须为直接子文件名（不含路径分隔符）")
        if not isinstance(entry, dict):
            errors.append(f"{where}: files[{name!r}] 须为表（实际 {type(entry).__name__}）")
            continue
        extra = sorted(set(entry) - ALLOWED_ENTRY)
        if extra:
            errors.append(f"{where}: files[{name!r}] 未知键 {extra}（允许 {sorted(ALLOWED_ENTRY)}）")
        sha = entry.get("sha256")
        if sha is not None and (not isinstance(sha, str) or not SHA_RE.match(sha)):
            errors.append(f"{where}: files[{name!r}].sha256 须为 64 位小写十六进制")

    if not files and not subdirs:
        errors.append(f"{where}: 清单为空（files 与 subdirs 皆空）⇒ vacuous")

    return {"schema": doc.get("schema"), "owner": doc.get("owner"),
            "subdirs": subdirs, "recursive": recursive, "files": files,
            "subdir_owners": subdir_owners}


def check_tree(manifest_dir: Path, doc: dict, rel_dir: str,
               errors: list[str], stats: dict, nested: bool = False,
               verbose: bool = True) -> None:
    """Assert one directory (top level, or a subdirectory when ``recursive``).

    顶层 = **双向**（多一个、少一个都红）；递归到的子目录 = **单向 ⊆**（只禁多出，
    不要求每个声明名都在每层出现——`subdirs`/`files` 是"允许集"，各层不必同形）。
    """
    files = doc["files"]
    subdirs = doc["subdirs"]

    entries = sorted(manifest_dir.iterdir(), key=lambda p: p.name)
    actual_files = {p.name for p in entries if p.is_file() and p.name != MANIFEST}
    actual_dirs = {p.name for p in entries if p.is_dir()}

    stats["dirs_checked"] += 1
    for name in sorted(actual_files - set(files)):
        errors.append(f"{rel_dir}: 多出文件 {name}（未在 files 中登记）")
    for name in sorted(actual_dirs - set(subdirs)):
        errors.append(f"{rel_dir}: 多出子目录 {name}（未在 subdirs 中登记）")
    if not nested:
        for name in sorted(set(files) - actual_files):
            errors.append(f"{rel_dir}: 缺失文件 {name}（files 已登记但磁盘不存在）")
        for name in sorted(set(subdirs) - actual_dirs):
            errors.append(f"{rel_dir}: 缺失子目录 {name}（subdirs 已登记但磁盘不存在）")

    for name in sorted(files):
        entry = files[name]
        path = manifest_dir / name
        owner = entry.get("owner")
        if owner and verbose:
            print(f"    owner {rel_dir}/{name} = {owner}")
        if not path.is_file():
            continue
        stats["files_checked"] += 1
        sha = entry.get("sha256")
        if sha is None:
            continue
        actual = sha256_file(path)
        stats["hashes_checked"] += 1
        if actual != sha:
            errors.append(
                f"{rel_dir}/{name}: sha256 不符（期望 {sha} 实际 {actual}）")

    if doc["recursive"]:
        for name in subdirs:
            sub = manifest_dir / name
            if sub.is_dir():
                check_tree(sub, doc, f"{rel_dir}/{name}", errors, stats,
                           nested=True, verbose=verbose)


def audit(root: Path, quiet: bool = False, collect: list[str] | None = None) -> int:
    errors: list[str] = []
    stats = {"manifests": 0, "files_checked": 0, "hashes_checked": 0, "dirs_checked": 0}

    if not quiet:
        print("=" * 78)
        print("check-manifests-guard — `.manifests.toml` 目录清单门控（双向集合 + sha256）")
        print("=" * 78)

    roots = load_registry(root, errors)
    manifests = required_manifests(root, roots, errors) if roots is not None else []
    stats["manifests"] = len(manifests)

    for path in manifests:
        rel = _rel(root, path)
        doc = load_manifest(path, errors)
        if doc is None:
            continue
        owner = doc.get("owner") or "-"
        if not quiet:
            print(f"清单 {rel}  owner={owner}  recursive={doc['recursive']}")
        check_tree(path.parent, doc, str(Path(rel).parent), errors, stats,
                   verbose=not quiet)
        if not quiet:
            rel_dir = str(Path(rel).parent)
            for name in sorted(doc["subdir_owners"]):
                print(f"    owner {rel_dir}/{name} = {doc['subdir_owners'][name]}")
        # 计数现场统计、不写死
        if not quiet:
            print(f"  files 登记 {len(doc['files'])} / subdirs 登记 {len(doc['subdirs'])}")

    if not quiet:
        print("-" * 78)
        print(f"清单 {stats['manifests']}；受检目录 {stats['dirs_checked']}；"
              f"文件 {stats['files_checked']}；sha256 {stats['hashes_checked']}")
    if errors:
        if collect is not None:
            collect.extend(errors)
        if quiet:
            return 1
        print(f"结果: FAIL（{len(errors)} 项）")
        for err in errors:
            print(f"  ERROR: {err}")
        return 1
    if not quiet:
        print("结果: PASS（双向文件/子目录集合一致、sha256 全符）")
    return 0


# ── 自检：六类注入各自可达 FAIL ────────────────────────────────────────────────
BASE_A = """schema = 1
owner = "selftest"
subdirs = ["sub"]
recursive = false

[subdir_owners]
sub = "mod"

[files."x.txt"]
sha256 = "{sha_x}"

[files."y.txt"]
owner = "selftest"
"""

BASE_B = """schema = 1
subdirs = ["s"]
recursive = true

[files."f.txt"]
sha256 = "{sha_f}"
"""

SELF_LISTED = """schema = 1
subdirs = ["sub"]
recursive = false

[files."x.txt"]
sha256 = "{sha_x}"

[files."y.txt"]

[files.".manifests.toml"]
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


REGISTRY_TEXT = 'schema = 1\nroots = ["a", "b"]\n'


def _build_tree(root: Path, *, self_listed: bool = False) -> None:
    _write(root / REGISTRY, REGISTRY_TEXT)
    _write(root / "a" / "x.txt", "alpha\n")
    _write(root / "a" / "y.txt", "beta\n")
    _write(root / "a" / "sub" / "deep.txt", "deep\n")      # 非递归：子目录内容不限
    sha_x = hashlib.sha256(b"alpha\n").hexdigest()
    _write(root / "a" / MANIFEST, (SELF_LISTED if self_listed else BASE_A).format(sha_x=sha_x))
    # recursive=true：s 层套用同一 files/subdirs 规则（单向 ⊆）
    _write(root / "b" / "f.txt", "rec\n")
    _write(root / "b" / "s" / "f.txt", "rec\n")
    _write(root / "b" / MANIFEST, BASE_B.format(sha_f=hashlib.sha256(b"rec\n").hexdigest()))


def self_test() -> int:
    # (名称, 变更, 期望 rc, 期望错误子串) —— 不只判 rc，还判「红在预期原因上」
    cases = [
        ("基线（含 recursive 正例）", lambda r: None, 0, ""),
        ("新增文件", lambda r: _write(r / "a" / "new.txt", "new\n"), 1, "多出文件 new.txt"),
        ("删除文件", lambda r: (r / "a" / "y.txt").unlink(), 1, "缺失文件 y.txt"),
        ("改 sha256", lambda r: _write(r / "a" / "x.txt", "tampered\n"), 1, "sha256 不符"),
        ("多建子目录", lambda r: (r / "a" / "other").mkdir(), 1, "多出子目录 other"),
        ("清单自身被列入", lambda r: _build_tree(r, self_listed=True), 1, "不得列入清单自身"),
        ("清单不可解析（TOML 语法错）",
         lambda r: _write(r / "a" / MANIFEST, "schema = [\n"), 1, "无法解析 TOML"),
        ("recursive 分支（子目录内新增文件）",
         lambda r: _write(r / "b" / "s" / "extra.txt", "x\n"), 1, "b/s: 多出文件 extra.txt"),
        ("recursive 分支（子目录内多建目录）",
         lambda r: (r / "b" / "s" / "u").mkdir(), 1, "b/s: 多出子目录 u"),
        # ── 注册表（fail-closed）──
        ("删除某份清单（注册表仍要求它）",
         lambda r: (r / "a" / MANIFEST).unlink(), 1, "a: 缺少清单 .manifests.toml"),
        ("删除注册表",
         lambda r: (r / REGISTRY).unlink(), 1, "注册表缺失"),
        ("注册表登记不存在的目录",
         lambda r: _write(r / REGISTRY, 'schema = 1\nroots = ["a", "b", "ghost"]\n'),
         1, "ghost: 注册表登记的目录不存在"),
        ("游离清单（目录未登记）",
         lambda r: _write(r / "c" / MANIFEST, 'schema = 1\nsubdirs = []\n'),
         1, "c/.manifests.toml: 游离清单"),
        # ── subdir_owners（A8，可选映射）──
        ("subdir_owners 悬空 key（不在 subdirs）",
         lambda r: _write(r / "a" / MANIFEST, BASE_A.format(
             sha_x=hashlib.sha256(b"alpha\n").hexdigest()).replace(
                 'sub = "mod"', 'sub = "mod"\nghost = "mod"')),
         1, "悬空 owner"),
        ("subdir_owners 值非字符串",
         lambda r: _write(r / "a" / MANIFEST, BASE_A.format(
             sha_x=hashlib.sha256(b"alpha\n").hexdigest()).replace(
                 'sub = "mod"', "sub = 1")),
         1, "subdir_owners['sub'] 须为非空字符串"),
    ]
    print("=" * 78)
    print(f"check-manifests-guard --self-test（目录/文件注入 + 注册表 + subdir_owners，共 {len(cases)} 例）")
    print("=" * 78)
    bad = 0
    for name, mutate, want_rc, needle in cases:
        tmp = Path(tempfile.mkdtemp(prefix="manifests-guard-"))
        errs: list[str] = []
        try:
            _build_tree(tmp)
            mutate(tmp)
            rc = audit(tmp, quiet=True, collect=errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if want_rc == 0:
            ok = rc == 0
            detail = f"rc={rc}"
        else:
            matched = needle and any(needle in e for e in errs)
            ok = rc != 0 and bool(matched)
            detail = f"rc={rc} 原因命中={bool(matched)}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: 期望 rc={'0' if want_rc == 0 else '≠0'} 实际 {detail}")
        if not ok:
            bad += 1
            for err in errs[:5]:
                print(f"        {err}")
    print(f"--self-test: {len(cases) - bad}/{len(cases)} 符合预期")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="`.manifests.toml` 目录清单门控")
    ap.add_argument("--root", default=str(ROOT), help="仓库根（默认脚本所在仓库）")
    ap.add_argument("--self-test", action="store_true", help="用临时树跑六类注入自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"check-manifests-guard: ERROR: 目录不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    sys.exit(main())
