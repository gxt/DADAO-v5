#!/usr/bin/env python3
"""SimRISC 版本清单与按版本归档（SPEC-154t）。

**派生（两源独立，脚本内无版本表常量）**
- 源 A `wiki`：`.cache/refs/DADAO.wiki`（只读参考树；**锚点固定**，不随该树 HEAD 漂移）；
- 源 B `repo`：本仓 `git` 历史，只取 `spec/` 与 `wiki/` 两个目录下的 `SimRISC*.md`
  （`wiki/` 为 2026-09-10 `bb98fff0` 重命名前的路径；不含 `.tao/archive/**` 副本）。
- 版本号 = 该提交树里 `SimRISC-00*` 册头 `> **版本：X.Y.Z[-rc]**` 的值。
- 版本 `V` 的**首次提交** = 最早携带 `V` 的提交；**快照** = 最晚携带 `V` 的提交
  = 「下一版本首次出现的提交的父提交」（末版 = 锚点 HEAD）。
- 同版本号在两源都出现时，取**首次标记更早**的一方为准（同刻优先 wiki），并在
  `--report` 中逐条列出跨源差异（不合并、不覆盖）。

**版本组合 sha256**（脚本与门控同一实现）：目录内 `SimRISC-*.md` 按**文件名排序**，
拼 `<sha256>  <basename>\\n` 后取 `sha256`。

用法
----
  python3 tools/spec/gen_spec_archive.py --list          # 清单 TSV（无表头；确定性）
  python3 tools/spec/gen_spec_archive.py --report        # 派生过程 / 跨源冲突 / 不可重建披露
  python3 tools/spec/gen_spec_archive.py --apply         # 只新增缺失的非 -rc 目录（已存在目录不动）
  python3 tools/spec/gen_spec_archive.py --verify        # 清单 ↔ 目录 ↔ sha256 三向校验
  python3 tools/spec/gen_spec_archive.py --self-test     # 内置反例自检（`-rc` 跳过逻辑：`--verify` + `--apply`）

`--list` 的列（TSV）：`版本 \t 首次提交 \t 快照提交 \t 首次标记日期 \t 来源仓库 \t 文件数 \t 组合sha256`。

`0.3` 及更早**无版本标记**（wiki 早期为单文件 `SimRISC.md`），不伪造快照，只在 `--report`
与 `spec/README.md` 中披露。

`--verify` 以归档目录内 `PROVENANCE.md` 的 `快照提交` 为锚（`-rc` 目录为时点快照，随
工作树演进属正常）；无 `PROVENANCE.md` 的既有目录（0.4.1 / 0.5.3）回落到派生快照。
有 `PROVENANCE.md` 时**逐文件精确比对**：其「逐文件 sha256」表须与快照内容全等，其
「版本组合 sha256」须等于按该表重算的值（不接受子串/前缀匹配）。

`-rc` 为**预发布**，**不纳入归档校验**（与 `tools/spec/check_spec_archive.py` 的
「`-rc` 不纳入归档门控」口径一致；用户 2026-10-25 裁定 `SimRISC-0.5.5-rc` 可删除）：
`--verify` 与 `--apply` 均对 `-rc` 条目打印 `SKIP` 并跳过（`--apply` 不得重建 `-rc` 目录），
`--list`/`--report` 仍如实列出（历史清单不减）。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / ".cache" / "refs" / "DADAO.wiki"
ARCHIVE = REPO / ".tao" / "archive"

# wiki 参考树的**固定锚点**（SPEC-154t 实测 HEAD）。`.cache/refs/DADAO.wiki` 未纳入
# `manifests/references.lock.toml`；固定提交号保证清单可复现，不依赖「当前 HEAD」。
WIKI_ANCHOR = "9f378f4426e131903d60a208766086ae74a53c89"

VERSION_RE = re.compile(r"^>\s*\*\*版本[：:]\s*(\d+(?:\.\d+){1,2}(?:-rc)?)", re.M)
SIMRISC_RE = re.compile(r"^SimRISC.*\.md$")
DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2013\u2014\uff0d"), "-")

# 各源的 `SimRISC-00` 候选路径（wiki 历史早期用 U+2010 连字符；本仓 2026-09-10 前后
# 分别在 `wiki/` 与 `spec/`）。只用于读册头版本号，不构成版本表。
VOL0_PATHS = {
    "wiki": ("SimRISC-00-指令系统设计.md", "SimRISC\u201000\u2010指令系统设计.md"),
    "repo": ("spec/SimRISC-00-指令系统设计.md", "wiki/SimRISC-00-指令系统设计.md"),
}
ROOTS = {"wiki": (".",), "repo": ("spec", "wiki")}


def git(repo: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} @ {repo} failed: {res.stderr.strip()}")
    return res.stdout


def git_bytes(repo: Path, *args: str) -> tuple[int, bytes]:
    res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    return res.returncode, res.stdout


def cat_file_batch(repo: Path, specs: list[str]) -> list[bytes | None]:
    """一次 `git cat-file --batch` 取多个 `<rev>:<path>` 内容；不存在 ⇒ None。"""
    if not specs:
        return []
    res = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch"],
        input=("\n".join(specs) + "\n").encode(),
        capture_output=True,
    )
    out = res.stdout
    results: list[bytes | None] = []
    pos = 0
    for _ in specs:
        nl = out.find(b"\n", pos)
        if nl < 0:
            results.append(None)
            continue
        header = out[pos:nl].decode("utf-8", "replace")
        pos = nl + 1
        if header.endswith("missing") or " " not in header:
            results.append(None)
            continue
        size = int(header.rsplit(" ", 1)[1])
        results.append(out[pos : pos + size])
        pos += size + 1  # 内容后随换行
    return results


def normalize(name: str) -> str:
    """把 wiki 历史文件名里的 Unicode 连字符归一为 ASCII `-`（写归档时用）。"""
    return name.translate(DASHES)


def simrisc_files(repo: Path, commit: str, roots: tuple[str, ...]) -> list[str]:
    """该提交树中指定根目录下、**直接位于**该目录的 `SimRISC*.md`（相对 repo 的路径）。"""
    args = ["ls-tree", "-r", "--name-only", "-z", commit]
    if roots != (".",):
        args += ["--", *roots]
    out = git(repo, *args)
    wanted = {"." if r == "" else r for r in roots}
    files = []
    for raw in out.split("\0"):
        if not raw:
            continue
        path = Path(raw)
        if str(path.parent) in wanted and SIMRISC_RE.match(path.name):
            files.append(raw)
    return sorted(files)


def commit_date(repo: Path, commit: str) -> str:
    return git(repo, "show", "-s", "--format=%ad", "--date=short", commit).strip()


def commit_subject(repo: Path, commit: str) -> str:
    return git(repo, "show", "-s", "--format=%s", commit).strip()


def file_version(text: str | None) -> str | None:
    if not text:
        return None
    m = VERSION_RE.search(text)
    return m.group(1) if m else None


def scan(repo: Path, anchor: str, source: str) -> dict:
    """扫描一源，返回 {version: {first, snapshot, files, date}} 与过程信息。"""
    anchor = git(repo, "rev-parse", anchor).strip()
    commits = git(repo, "rev-list", anchor).split()  # newest -> oldest
    paths = VOL0_PATHS[source]
    # 每提交 × 候选路径一次批量读取（单进程），取第一个命中的册头版本号
    specs = [f"{c}:{p}" for c in commits for p in paths]
    blobs = cat_file_batch(repo, specs)
    chunk = len(paths)
    commit_version: dict[str, str | None] = {}
    for i, commit in enumerate(commits):
        ver = None
        for j in range(chunk):
            ver = file_version(
                blobs[i * chunk + j].decode("utf-8", "replace") if blobs[i * chunk + j] else None
            )
            if ver:
                break
        commit_version[commit] = ver

    # 每版本：最早（rev-list 末尾方向）/ 最晚（开头方向）携带该版本号的提交
    seen: dict[str, list[str]] = {}
    for commit in commits:  # newest -> oldest
        ver = commit_version[commit]
        if ver:
            seen.setdefault(ver, []).append(commit)
    firsts = {ver: cl[-1] for ver, cl in seen.items()}  # 最旧

    versions = sorted(seen, key=version_key)
    entries = {}
    for idx, ver in enumerate(versions):
        first = firsts[ver]
        if idx + 1 < len(versions):
            nxt = firsts[versions[idx + 1]]
            # 快照 = 下一版本首次出现提交的父提交
            snapshot = git(repo, "rev-parse", f"{nxt}^").strip()
        else:
            snapshot = anchor
        files = simrisc_files(repo, snapshot, ROOTS[source])
        entries[ver] = {
            "version": ver,
            "source": source,
            "first": first,
            "snapshot": snapshot,
            "date": commit_date(repo, first),
            "files": files,
            "versioned_commits": len(seen[ver]),
        }
    return {"entries": entries, "commits_with_version": sum(1 for v in commit_version.values() if v)}


def version_key(ver: str) -> tuple:
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?(-rc)?$", ver)
    # `-rc` 是**预发布**，须排在正式版之前（否则正式版的快照会被算成 rc 首现提交的父提交）
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), 0 if m.group(4) else 1)


def file_sha(repo: Path, commit: str, path: str) -> str:
    rc, blob = git_bytes(repo, "show", f"{commit}:{path}")
    if rc != 0:
        raise RuntimeError(f"无法读取 {commit}:{path}")
    return hashlib.sha256(blob).hexdigest()


def composite(pairs: list[tuple[str, str]]) -> str:
    """pairs = [(basename, sha256)]；按 basename 排序拼 `<sha>  <name>\\n` 再取 sha256。"""
    lines = "".join(f"{sha}  {name}\n" for name, sha in sorted(pairs))
    return hashlib.sha256(lines.encode()).hexdigest()


def enrich(repo: Path, entry: dict) -> dict:
    pairs = [
        (normalize(Path(p).name), file_sha(repo, entry["snapshot"], p)) for p in entry["files"]
    ]
    entry["file_entries"] = pairs
    entry["count"] = len(pairs)
    entry["composite"] = composite(pairs)
    return entry


def derive(wiki_anchor: str = WIKI_ANCHOR) -> dict:
    """两源独立派生 + 合并。返回 {versions: [...], report: {...}}。"""
    wiki_scan = scan(WIKI, wiki_anchor, "wiki")
    repo_scan = scan(REPO, "HEAD", "repo")

    merged: dict[str, dict] = {}
    cross = []
    for entry in wiki_scan["entries"].values():
        merged[entry["version"]] = entry
    for entry in repo_scan["entries"].values():
        if entry["version"] in merged:
            other = merged[entry["version"]]
            cross.append((entry["version"], other, entry))
            # 取首次标记更早的一方（同刻优先 wiki）
            if entry["date"] < other["date"]:
                merged[entry["version"]] = entry
        else:
            merged[entry["version"]] = entry

    versions = []
    for ver in sorted(merged, key=version_key):
        entry = merged[ver]
        repo = WIKI if entry["source"] == "wiki" else REPO
        versions.append(enrich(repo, entry))

    cross_report = []
    for ver, chosen, other in cross:
        o = dict(other)
        enrich(WIKI if o["source"] == "wiki" else REPO, o)
        cross_report.append(
            {
                "version": ver,
                "chosen": chosen["source"],
                "chosen_sha": chosen["composite"],
                "other": o["source"],
                "other_sha": o["composite"],
                "other_snapshot": o["snapshot"],
                "other_count": o["count"],
                "same": chosen["composite"] == o["composite"],
            }
        )

    return {
        "versions": versions,
        "wiki_anchor": wiki_anchor,
        "repo_anchor": git(REPO, "rev-parse", "HEAD").strip(),
        "cross_source": cross_report,
        "versioned_commits": {
            "wiki": wiki_scan["commits_with_version"],
            "repo": repo_scan["commits_with_version"],
        },
    }


def tsv(data: dict) -> str:
    rows = []
    for e in data["versions"]:
        rows.append(
            "\t".join(
                [
                    e["version"],
                    e["first"],
                    e["snapshot"],
                    e["date"],
                    e["source"],
                    str(e["count"]),
                    e["composite"],
                ]
            )
        )
    return "\n".join(rows) + "\n"


def write_provenance(e: dict, data: dict, dest: Path) -> None:
    repo = WIKI if e["source"] == "wiki" else REPO
    src_repo = ".cache/refs/DADAO.wiki" if e["source"] == "wiki" else "本仓"
    renamed = sum(1 for p in e["files"] if Path(p).name != normalize(Path(p).name))
    lines = [
        f"# SimRISC {e['version']} 归档来源",
        "",
        f"- 版本：`{e['version']}`",
        f"- 来源仓库：{src_repo}",
        f"- 快照提交：`{e['snapshot']}`（{commit_subject(repo, e['snapshot'])}）",
        f"- 首次标记提交：`{e['first']}`（{e['date']}）",
    ]
    if e["source"] == "wiki":
        lines.append(f"- wiki 锚点：`{data['wiki_anchor']}`")
    lines += [
        f"- 文件数：{e['count']}",
        f"- 版本组合 sha256：`{e['composite']}`",
    ]
    if renamed:
        lines.append(f"- 文件名规范化：U+2010（`‐`）→ ASCII `-`，共 {renamed} 个")
    lines += [
        "",
        "## 逐文件 sha256",
        "",
        "```",
        *[f"{sha}  {name}" for name, sha in e["file_entries"]],
        "```",
        "",
        "## 提取命令",
        "",
        "```sh",
    ]
    for p in e["files"]:
        target = normalize(Path(p).name)
        if e["source"] == "wiki":
            lines.append(
                f"git -C .cache/refs/DADAO.wiki show {e['snapshot']}:{p}"
                f" > .tao/archive/SimRISC-{e['version']}/{target}"
            )
        else:
            lines.append(
                f"git show {e['snapshot']}:{p} > .tao/archive/SimRISC-{e['version']}/{target}"
            )
    lines += [
        "```",
        "",
        "> 归档为**只读历史快照**：不参与 `spec/` 门控扫描；引用方须指向本目录，不得改写内容。",
        "",
    ]
    dest.write_text("\n".join(lines))


def apply(data: dict, archive: Path | None = None) -> int:
    dest_root = archive or ARCHIVE
    for e in data["versions"]:
        if is_rc(e["version"]):
            # 预发布 `-rc` 不建目录（与 `--verify` / check_spec_archive.py 同口径）
            print(f"SKIP SimRISC-{e['version']}（预发布 -rc：不建归档目录）")
            continue
        dest = dest_root / f"SimRISC-{e['version']}"
        if dest.exists():
            ok, msgs = verify_one(e, dest)
            print(f"SKIP SimRISC-{e['version']}（已存在；与快照{'一致' if ok else '不一致'}）")
            for m in msgs:
                print(f"     {m}")
            continue
        dest.mkdir(parents=True)
        repo = WIKI if e["source"] == "wiki" else REPO
        for p in e["files"]:
            target = dest / normalize(Path(p).name)
            rc, blob = git_bytes(repo, "show", f"{e['snapshot']}:{p}")
            if rc != 0:
                print(f"FAIL {dest.name}: {p} 提取失败", file=sys.stderr)
                return 1
            target.write_bytes(blob)
        write_provenance(e, data, dest / "PROVENANCE.md")
        print(
            f"ADD  SimRISC-{e['version']}"
            f"（{e['count']} 文件，来源 {e['source']}@{e['snapshot'][:7]}）"
        )
    return 0


def provenance_snapshot(dest: Path) -> str | None:
    prov = dest / "PROVENANCE.md"
    if not prov.is_file():
        return None
    m = re.search(r"快照提交：`([0-9a-f]{7,40})`", prov.read_text())
    return m.group(1) if m else None


PROV_COMPOSITE_RE = re.compile(r"版本组合 sha256：`([0-9a-f]{64})`")
PROV_TABLE_RE = re.compile(r"## 逐文件 sha256\s*\n+```\n(.*?)\n```", re.S)
PROV_FILE_RE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def provenance_pairs(dest: Path) -> tuple[str | None, list[tuple[str, str]] | None, list[str]]:
    """解析 `PROVENANCE.md`：返回（声明的组合 sha256, 逐文件表 [(name, sha)], 问题清单）。

    无 `PROVENANCE.md` ⇒ (None, None, [])。格式不符即记问题（绝不降级为「跳过」）。
    """
    prov = dest / "PROVENANCE.md"
    if not prov.is_file():
        return None, None, []
    text = prov.read_text()
    problems: list[str] = []
    m = PROV_COMPOSITE_RE.search(text)
    declared = m.group(1) if m else None
    if declared is None:
        problems.append("PROVENANCE 缺「版本组合 sha256」行或格式不符")
    block = PROV_TABLE_RE.search(text)
    pairs: list[tuple[str, str]] | None = None
    if block is None:
        problems.append("PROVENANCE 缺「逐文件 sha256」表")
        return declared, pairs, problems
    pairs = []
    for ln in block.group(1).splitlines():
        fm = PROV_FILE_RE.match(ln)
        if not fm:
            problems.append(f"PROVENANCE 逐文件表行格式不符：{ln!r}")
            continue
        pairs.append((fm.group(2), fm.group(1)))
    names = [n for n, _ in pairs]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        problems.append(f"PROVENANCE 逐文件表重复条目：{dup}")
    return declared, pairs, problems


def verify_one(e: dict, dest: Path) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    if not dest.is_dir():
        label = dest.relative_to(REPO) if dest.is_relative_to(REPO) else dest
        return False, [f"目录缺失：{label}"]
    present = sorted(p.name for p in dest.glob("SimRISC-*.md"))
    pin = provenance_snapshot(dest) or e["snapshot"]
    repo = WIKI if e["source"] == "wiki" else REPO
    try:
        files = simrisc_files(repo, pin, ROOTS[e["source"]])
    except RuntimeError:
        return False, [f"快照提交不可解析：{pin}"]
    expected = sorted(normalize(Path(p).name) for p in files)
    ok = True
    if present != expected:
        ok = False
        missing = sorted(set(expected) - set(present))
        extra = sorted(set(present) - set(expected))
        msgs.append(f"文件集不符（缺 {len(missing)} / 多 {len(extra)}）：缺={missing} 多={extra}")
    expected_pairs = [(normalize(Path(p).name), file_sha(repo, pin, p)) for p in files]
    actual_pairs = []
    for name, expected_sha in expected_pairs:
        actual = dest / name
        if not actual.is_file():
            continue
        sha = hashlib.sha256(actual.read_bytes()).hexdigest()
        actual_pairs.append((name, sha))
        if sha != expected_sha:
            ok = False
            msgs.append(f"sha256 不符：{name}")
    if len(actual_pairs) == len(expected_pairs):
        want, got = composite(expected_pairs), composite(actual_pairs)
        if want != got:
            ok = False
            msgs.append(f"组合 sha256 不符：期望 {want[:16]}… 实际 {got[:16]}…")
    # PROVENANCE 自洽：逐文件表 == 快照内容；声明的组合 sha256 == 按该表重算（精确相等）
    declared, table_pairs, problems = provenance_pairs(dest)
    for problem in problems:
        ok = False
        msgs.append(problem)
    if table_pairs is not None:
        if sorted(table_pairs) != sorted(expected_pairs):
            ok = False
            missing = sorted(set(expected_pairs) - set(table_pairs))
            extra = sorted(set(table_pairs) - set(expected_pairs))
            msgs.append(
                f"PROVENANCE 逐文件表与快照不符（缺 {len(missing)} / 多 {len(extra)}）："
                f"缺={missing} 多={extra}"
            )
        if declared is not None:
            recomputed = composite(table_pairs)
            if declared != recomputed:
                ok = False
                msgs.append(
                    f"PROVENANCE 组合 sha256 与逐文件表重算不符："
                    f"声明 {declared[:16]}… 重算 {recomputed[:16]}…"
                )
    return ok, msgs


def is_rc(version: str) -> bool:
    """`-rc` 为**预发布**：不纳入归档校验（与 `check_spec_archive.py` 归档门控同口径）。"""
    return version.endswith("-rc")


def verify(data: dict) -> int:
    rc = 0
    for e in data["versions"]:
        if is_rc(e["version"]):
            # 预发布 `-rc` 不纳入归档校验（check_spec_archive.py 同口径；用户 2026-10-25 裁定）
            print(f"SKIP SimRISC-{e['version']}（预发布 -rc：不纳入归档校验）")
            continue
        dest = ARCHIVE / f"SimRISC-{e['version']}"
        ok, msgs = verify_one(e, dest)
        print(f"{'OK  ' if ok else 'FAIL'} SimRISC-{e['version']}（{e['count']} 文件@清单快照）")
        for m in msgs:
            print(f"     {m}")
        if not ok:
            rc = 1
    return rc


def self_test() -> int:
    """内置反例：`-rc` 须 SKIP（`--verify` rc=0、`--apply` 不建目录）、非 `-rc` 须 FAIL/建目录。"""
    import contextlib
    import io
    import shutil
    import tempfile

    rc = 0

    def fake(version: str) -> dict:
        return {"version": version, "count": 0}

    cases = [
        ("仅 -rc 条目（目录缺失）", [fake("0.0.0-rc")], 0, "SKIP SimRISC-0.0.0-rc"),
        ("仅非 -rc 条目（目录缺失）", [fake("0.0.0")], 1, "FAIL SimRISC-0.0.0"),
        ("-rc 与非 -rc 混合", [fake("0.0.0-rc"), fake("0.0.0")], 1, "FAIL SimRISC-0.0.0"),
    ]
    for name, versions, want_rc, want_line in cases:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = verify({"versions": versions})
        out = buf.getvalue()
        hit = want_line in out
        ok = got == want_rc and hit
        print(
            f"[self-test] {name}：rc={got}（期望 {want_rc}），含 {want_line!r}={hit} "
            f"→ {'PASS' if ok else 'FAIL'}"
        )
        if not ok:
            rc = 1

    # `--apply` 的 `-rc` 跳过：须「打印 SKIP」且「不建目录」；非 -rc 须「打印 ADD」且「建目录」。
    head = git(REPO, "rev-parse", "HEAD").strip()
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "SPEC-174t"
    tmp_root.mkdir(parents=True, exist_ok=True)

    def apply_entry(version: str) -> dict:
        return {
            "version": version, "source": "repo", "snapshot": head, "first": head,
            "date": commit_date(REPO, head), "files": [], "file_entries": [],
            "count": 0, "composite": composite([]),
        }

    apply_cases = [
        ("仅 -rc 条目", ["0.0.0-rc"], [], ["0.0.0-rc"]),
        ("仅非 -rc 条目", ["0.0.0"], ["0.0.0"], []),
        ("-rc 与非 -rc 混合", ["0.0.0-rc", "0.0.0"], ["0.0.0"], ["0.0.0-rc"]),
    ]
    for name, versions, want_dirs, want_absent in apply_cases:
        tmpdir = Path(tempfile.mkdtemp(prefix="apply-", dir=tmp_root))
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                got = apply({"versions": [apply_entry(v) for v in versions]}, archive=tmpdir)
            out = buf.getvalue()
            made = sorted(p.name for p in tmpdir.iterdir() if p.is_dir())
            want_names = sorted(f"SimRISC-{v}" for v in want_dirs)
            absent_ok = all(not (tmpdir / f"SimRISC-{v}").exists() for v in want_absent)
            skip_ok = all(f"SKIP SimRISC-{v}" in out for v in want_absent)
            ok = got == 0 and made == want_names and absent_ok and skip_ok
            print(
                f"[self-test] apply {name}：rc={got}（期望 0），建目录={made}"
                f"（期望 {want_names}），-rc 未建={absent_ok}，SKIP 行={skip_ok}"
                f" → {'PASS' if ok else 'FAIL'}"
            )
            if not ok:
                rc = 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"gen_spec_archive --self-test: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


def report(data: dict) -> int:
    print(f"wiki 锚点：{data['wiki_anchor']}（记录值；不随该树 HEAD 漂移）")
    print(f"本仓 HEAD：{data['repo_anchor']}")
    print(
        "带版本标记的提交数："
        f"wiki={data['versioned_commits']['wiki']} repo={data['versioned_commits']['repo']}"
    )
    print(f"派生版本数：{len(data['versions'])}")
    print()
    print(tsv(data).rstrip())
    print()
    print("跨源同号版本：")
    if not data["cross_source"]:
        print("  （无）")
    for c in data["cross_source"]:
        print(
            f"  {c['version']}：采用 {c['chosen']}（{c['chosen_sha'][:16]}…）"
            f" vs {c['other']}@{c['other_snapshot'][:7]}（{c['other_sha'][:16]}…，{c['other_count']} 文件）"
            f" → {'内容相同' if c['same'] else '内容不同（冲突，只报告不合并）'}"
        )
    print()
    print("不可按版本重建：0.3 及更早无版本标记（wiki 早期为单文件 SimRISC.md），不伪造快照。")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="SimRISC 版本清单与按版本归档（SPEC-154t）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="打印清单 TSV（无表头，确定性）")
    group.add_argument("--report", action="store_true", help="派生过程 / 跨源冲突 / 披露")
    group.add_argument("--apply", action="store_true", help="只新增缺失归档目录")
    group.add_argument("--verify", action="store_true", help="清单 ↔ 目录 ↔ sha256 校验")
    group.add_argument("--self-test", action="store_true", help="内置反例自检（-rc 跳过逻辑）")
    parser.add_argument("--wiki-anchor", default=WIKI_ANCHOR, help="wiki 参考树锚点提交")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    data = derive(args.wiki_anchor)
    if args.list:
        sys.stdout.write(tsv(data))
        return 0
    if args.report:
        return report(data)
    if args.apply:
        return apply(data)
    return verify(data)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
