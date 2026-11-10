#!/usr/bin/env python3
"""L1 gate: `docs/TestReports/` report hygiene (m13-testcases-004).

Rules = `docs/TestReports/README.md` + `docs/Process-09-测试组织规范.md`
「测试报告归属」.  Four static assertions (no rendering / no formatting):

R1  no runtime absolute path in a report body: `/tmp/<x>`, `/home/<x>` or a
    concrete `.work/<x>` path.  The glob forms used by the rules text
    (`/tmp/**`, `.work/**`) do not match, so `README.md` needs no exemption
    (it is the rulebook and is skipped anyway).
R2  a snapshot report (its body contains the snapshot kind word) must carry
    `<!-- 现场生成，勿手改 -->` as its **first line**; at least one snapshot
    must exist (deleting every marker is a vacuous FAIL, never a silent pass).
R3  every report is named `<M>-<主题>[-<后缀>].md` (`M\\d+`, no whitespace) and
    lives directly in the directory (no nested theme sub-directory, README
    §4); the name must not carry a date (`20YY-MM-DD` or `20YYMMDD`) — the
    date belongs in the header, so one milestone has exactly one current file.
R4  the header (first 40 lines) carries the four required items:
    生成时间 / 数据来源 / 机器指纹 / 复现.

`README.md` is the rules file: R1/R2/R4 skip it (R3 still checks the layout).

Exit: 0 = PASS, 1 = FAIL.  `--self-test` builds a synthetic tree, proves the
clean baseline green, then injects one or more counter-examples per assertion
and requires every one to turn red.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

REPORTS_SUBDIR = ("docs", "TestReports")
README = "README.md"
SNAPSHOT_WORD = "现场生成"
SNAPSHOT_MARKER = "<!-- 现场生成，勿手改 -->"
RUNTIME_PATH = re.compile(r"(?:/tmp|/home)/[A-Za-z0-9_]|\.work/[A-Za-z0-9_]")
NAME_RE = re.compile(r"^M[0-9]+-[^/]+\.md$")
NAME_DATE_RE = re.compile(r"20[0-9]{2}-?[0-9]{2}-?[0-9]{2}")
HEADER_KEYWORDS = ("生成时间", "数据来源", "机器指纹", "复现")
HEADER_LINES = 40


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def reports_dir(root: str | None) -> str:
    base = root if root else REPO_ROOT
    return os.path.join(base, *REPORTS_SUBDIR)


def run_checks(root: str | None = None, out=print) -> list[str]:
    """Return the list of problems; ``out`` receives one line per problem."""
    problems: list[str] = []
    ddir = reports_dir(root)
    if not os.path.isdir(ddir):
        problems.append(f"R3 report directory missing: {ddir}")
    else:
        entries = sorted(os.listdir(ddir))
        for entry in entries:
            if os.path.isdir(os.path.join(ddir, entry)):
                problems.append(f"R3 nested theme sub-directory forbidden: "
                                f"{entry}/")
        reports = [e for e in entries
                   if e.endswith(".md") and os.path.isfile(os.path.join(ddir, e))
                   and e != README]
        if not reports:
            problems.append("R3 zero report(s) under docs/TestReports/ "
                            "(vacuous)")
        snapshots = 0
        for name in reports:
            lines = _read(os.path.join(ddir, name)).splitlines()
            # R1 -- runtime absolute paths anywhere in the body.
            for lineno, line in enumerate(lines, 1):
                hit = RUNTIME_PATH.search(line)
                if hit:
                    problems.append(f"R1 {name}:{lineno} runtime path "
                                    f"{hit.group(0)!r}")
            # R2 -- snapshot marker must be the first line.  A snapshot is a
            # report whose body carries the marker; a first line that mentions
            # the snapshot kind must be the marker verbatim.
            if SNAPSHOT_MARKER in "\n".join(lines):
                snapshots += 1
                first = lines[0].strip() if lines else ""
                if first != SNAPSHOT_MARKER:
                    problems.append(
                        f"R2 {name}: snapshot first line must be "
                        f"{SNAPSHOT_MARKER!r}, got {first!r}")
            elif lines and SNAPSHOT_WORD in lines[0] \
                    and lines[0].strip() != SNAPSHOT_MARKER:
                problems.append(
                    f"R2 {name}: first line mentions {SNAPSHOT_WORD} but is "
                    f"not the marker {SNAPSHOT_MARKER!r}")
            # R3 -- file name shape (no date, no whitespace, no sub-dirs).
            if not NAME_RE.match(name) or re.search(r"\s", name):
                problems.append(f"R3 {name}: name must be "
                                f"<M>-<主题>[-<后缀>].md (M<digits>, no date, "
                                f"no whitespace)")
            elif NAME_DATE_RE.search(name):
                problems.append(f"R3 {name}: file name must not carry a date "
                                f"(put it in the header)")
            # R4 -- header keywords.
            head = "\n".join(lines[:HEADER_LINES])
            missing = [k for k in HEADER_KEYWORDS if k not in head]
            if missing:
                problems.append(f"R4 {name}: header (first {HEADER_LINES} "
                                f"lines) missing {missing}")
        if snapshots == 0:
            problems.append("R2 zero snapshot(s) (no report carries the "
                            "现场生成 marker; vacuous)")
    for p in problems:
        out(f"[FAIL] {p}")
    return problems


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _make_tree(base: str) -> str:
    tree = tempfile.mkdtemp(prefix="test-reports-", dir=base)
    ddir = os.path.join(tree, *REPORTS_SUBDIR)
    # Rules file: contains the forbidden glob forms, must stay exempt.
    _write(os.path.join(ddir, README),
           "# reports\n\n- 禁止 `/tmp/**`、`/home/**`、具体 `.work/**` 路径。\n"
           "- 快照首行 `<!-- 现场生成，勿手改 -->`。\n")
    _write(os.path.join(ddir, "M11-demo.md"),
           f"{SNAPSHOT_MARKER}\n\n# M11 demo snapshot\n\n"
           "- 生成时间：2026-01-01（UTC）\n"
           "- 数据来源：`demo`\n"
           "- 机器指纹：qemu md5 `deadbeef`\n"
           "- 复现命令：`make demo`\n")
    _write(os.path.join(ddir, "M13-demo.md"),
           "<!-- 人读结论 -->\n# M13 demo conclusion\n\n"
           "- **生成时间**：2026-01-02\n"
           "- **数据来源**：`demo`\n"
           "- **机器指纹**：qemu md5 `deadbeef`\n"
           "- **复现**：见 §4\n")
    return tree


def self_test(base: str) -> int:
    os.makedirs(base, exist_ok=True)
    outcomes: list[tuple[str, int, int]] = []

    def run(tree: str) -> int:
        return 1 if run_checks(tree, lambda _line: None) else 0

    def case(name: str, mutate):
        tree = _make_tree(base)
        try:
            mutate(tree)
            rc = run(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        outcomes.append((name, 1, rc))

    # 0. clean baseline => PASS.
    tree = _make_tree(base)
    try:
        rc = run(tree)
    finally:
        shutil.rmtree(tree, ignore_errors=True)
    outcomes.append(("clean baseline", 0, rc))

    # 1. R1: runtime absolute path injected into a report body.
    def inject_r1(tree: str) -> None:
        path = os.path.join(reports_dir(tree), "M13-demo.md")
        _write(path, _read(path) + "- JSON: `/tmp/opencode/demo/matrix.json`\n")
    case("R1 runtime path in body", inject_r1)

    # 2. R2: snapshot marker moved off the first line.
    def inject_r2(tree: str) -> None:
        path = os.path.join(reports_dir(tree), "M11-demo.md")
        _write(path, "# title above marker\n\n" + _read(path))
    case("R2 marker not on first line", inject_r2)

    # 3. R3: file name without the `<M>-` milestone prefix.
    def inject_r3(tree: str) -> None:
        path = os.path.join(reports_dir(tree), "M13-demo.md")
        _write(os.path.join(reports_dir(tree), "matrix-demo.md"), _read(path))
    case("R3 bad file name", inject_r3)

    # 3b. R3: file name carrying a date (date belongs in the header).
    def inject_r3_date(tree: str) -> None:
        path = os.path.join(reports_dir(tree), "M13-demo.md")
        _write(os.path.join(reports_dir(tree), "M11-2026-11-10-凡例.md"),
               _read(path))
    case("R3 date in file name", inject_r3_date)

    # 4. R4: header loses one required item.
    def inject_r4(tree: str) -> None:
        path = os.path.join(reports_dir(tree), "M11-demo.md")
        text = _read(path).replace("- 机器指纹：qemu md5 `deadbeef`\n", "", 1)
        assert "机器指纹" not in text, "R4 injection did not apply"
        _write(path, text)
    case("R4 header item missing", inject_r4)

    ok = True
    for name, want, got in outcomes:
        verdict = "PASS" if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"[SELFTEST] {name}: expected rc={want} actual rc={got} "
              f"=> {verdict}")
    print("check-test-reports --self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="m13-testcases-004: docs/TestReports/ report hygiene (L1)")
    ap.add_argument("--root", default=None,
                    help="alternative tree root for self-test/CI "
                         "(default: repo root)")
    ap.add_argument("--self-test", action="store_true",
                    help="baseline + one injected counter-example per "
                         "assertion")
    args = ap.parse_args(argv)
    if args.self_test:
        base = os.environ.get("DADAO_TMP",
                              "/tmp/opencode/m13-testcases-004-selftest")
        return self_test(base)
    problems = run_checks(args.root)
    if problems:
        print(f"check-test-reports: FAIL ({len(problems)} problem(s))")
        return 1
    ddir = reports_dir(args.root)
    reports = [e for e in os.listdir(ddir)
               if e.endswith(".md") and e != README]
    snapshots = [e for e in reports if SNAPSHOT_MARKER in _read(
        os.path.join(ddir, e))]
    print(f"check-test-reports: PASS ({len(reports)} report(s), "
          f"{len(snapshots)} snapshot(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
