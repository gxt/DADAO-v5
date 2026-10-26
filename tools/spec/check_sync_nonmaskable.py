#!/usr/bin/env python3
"""同步异常不可屏蔽门控（SPEC-175t；**里程碑层**，不进 L1）。

规则（用户 2026-10-26 裁定「同步异常全部不可屏蔽；仅异步可屏蔽」）：扫描
``spec/DADAO-12/22/23`` 的**异常原因表**（表头含 `是否可屏蔽` 列），凡该列取值为
`可` 的行，其名称必须是**异步源**——`IPI`、`TIMER`、`UART<n>` 或占位行 `...`；
其余任何 cause 行出现 `可` 即 **FAIL**（打印 `file:line`）。

计数**现场统计**（不写死）。若一册表都没找到 ⇒ ERROR（防空跑假绿）。

``--self-test``（可达 FAIL 自检）：临时副本上「注入一条同步 cause=可 → 必须 FAIL →
还原 → 必须 PASS」，任一预期不成立即非零退出。临时树落 `/tmp/opencode/SPEC-175t/`，
不触碰仓库文件。

Exit codes
----------
* 0 -- PASS（或 `--self-test` 全部预期成立）
* 1 -- FAIL（存在同步 cause 被标为可屏蔽）
* 2 -- ERROR（源文件缺失 / 未找到任何异常原因表）
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "spec"
TARGETS = (
    "DADAO-12-SEE-主管系统运行环境.md",
    "DADAO-22-SBI-主管系统二进制接口.md",
    "DADAO-23-HBI-超管系统二进制接口.md",
)
SELFTEST_ROOT = Path("/tmp/opencode/SPEC-175t")

MASK_HEADER = "是否可屏蔽"
NAME_HEADER = "名称"
MASKABLE = "可"
# 异步源白名单（用户裁定：仅异步可屏蔽）
ASYNC_NAME_RE = re.compile(r"^(?:IPI|TIMER|UART\d*|\.\.\.)$")
SPLIT_RE = re.compile(r"(?<!\\)\|")


def _cells(line: str) -> list[str]:
    """Split a markdown table row into stripped cells."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [c.strip().replace("\\|", "|") for c in SPLIT_RE.split(text)]


def scan_text(rel: str, text: str) -> tuple[list[str], dict]:
    """Return (violations, stats) for one volume."""
    errors: list[str] = []
    stats = {"tables": 0, "rows": 0, "maskable_rows": 0}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        # 收集连续表格行
        block: list[tuple[int, str]] = []
        j = i
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            block.append((j + 1, lines[j]))
            j += 1
        header = _cells(block[0][1])
        if len(block) < 2 or MASK_HEADER not in header:
            i = j
            continue
        stats["tables"] += 1
        mask_col = header.index(MASK_HEADER)
        name_col = header.index(NAME_HEADER) if NAME_HEADER in header else 1
        for lineno, raw in block[2:]:  # 跳过表头 + 分隔行
            cells = _cells(raw)
            if len(cells) <= max(mask_col, name_col):
                continue
            stats["rows"] += 1
            if cells[mask_col] != MASKABLE:
                continue
            stats["maskable_rows"] += 1
            name = cells[name_col]
            if not ASYNC_NAME_RE.match(name):
                errors.append(
                    f"{rel}:{lineno}: 同步异常原因 {name or '<空>'} 被标为可屏蔽（仅异步源可屏蔽）"
                )
        i = j
    return errors, stats


def run(spec_dir: Path) -> tuple[int, list[str], dict]:
    errors: list[str] = []
    agg = {"files": 0, "tables": 0, "rows": 0, "maskable_rows": 0}
    for name in TARGETS:
        path = spec_dir / name
        if not path.exists():
            return 2, [f"ERROR — 源文件缺失：{path}"], agg
        agg["files"] += 1
        errs, st = scan_text(name, path.read_text(encoding="utf-8"))
        errors.extend(errs)
        for key in ("tables", "rows", "maskable_rows"):
            agg[key] += st[key]
    if agg["tables"] == 0:
        return 2, ["ERROR — 未找到任何含「是否可屏蔽」列的异常原因表（防空跑假绿）"], agg
    return (1 if errors else 0), errors, agg


def _report(rc: int, errors: list[str], agg: dict, label: str) -> None:
    print(
        f"check-sync-nonmaskable[{label}]: files={agg['files']} tables={agg['tables']} "
        f"rows={agg['rows']} maskable_rows={agg['maskable_rows']}"
    )
    for e in errors:
        print("  " + e)
    if rc == 0:
        print("check-sync-nonmaskable: PASS（仅异步源（IPI/TIMER/UART*/…）可屏蔽）")
    elif rc == 1:
        print(f"check-sync-nonmaskable: FAIL ({len(errors)} violation(s))")
    else:
        print("check-sync-nonmaskable: ERROR")


def self_test() -> int:
    SELFTEST_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="gate-selftest-", dir=SELFTEST_ROOT))
    failures: list[str] = []

    def note(ok: bool, what: str, rc: int) -> None:
        print(f"  [{'OK' if ok else 'BAD'}] {what}（rc={rc}）")
        if not ok:
            failures.append(what)

    try:
        for name in TARGETS:
            shutil.copy2(SPEC / name, tmp / name)
        pristine = tmp / "pristine"
        pristine.mkdir()
        for name in TARGETS:
            shutil.copy2(tmp / name, pristine / name)

        # 1) 基线（仓库当前文本的副本）→ PASS
        rc0, err0, agg0 = run(tmp)
        _report(rc0, err0, agg0, "self-test/base")
        note(rc0 == 0, "基线副本必须 PASS", rc0)

        # 2) 注入：把 DADAO-12 的 SOFT_RESET（同步 cause）改为「可」→ 必须 FAIL
        target = tmp / TARGETS[0]
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        injected = False
        for k, line in enumerate(lines):
            if "SOFT_RESET" in line and line.rstrip().endswith("|"):
                cells = _cells(line)
                assert len(cells) == 5 and cells[3] == "否", f"SOFT_RESET 行形态异常: {line!r}"
                cells[3] = MASKABLE  # 是否可屏蔽列
                lines[k] = "| " + " | ".join(cells) + " |\n"
                injected = True
                break
        if not injected:
            print("  [BAD] 注入点未找到（SOFT_RESET 行）")
            failures.append("注入点未找到")
        target.write_text("".join(lines), encoding="utf-8")
        rc1, err1, agg1 = run(tmp)
        _report(rc1, err1, agg1, "self-test/inject")
        note(rc1 == 1 and any("SOFT_RESET" in e for e in err1),
             "注入同步 cause=可 必须 FAIL 且指出 SOFT_RESET", rc1)

        # 3) 还原（cp 回原副本）→ 必须 PASS
        shutil.copy2(pristine / TARGETS[0], target)
        rc2, err2, agg2 = run(tmp)
        _report(rc2, err2, agg2, "self-test/restore")
        note(rc2 == 0, "还原后必须 PASS", rc2)

        # 4) 注入：把 TIMER（异步源）改为「可」→ 仍必须 PASS（白名单可达）
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        injected = False
        for k, line in enumerate(lines):
            if "| TIMER" in line:
                cells = _cells(line)
                assert len(cells) == 5 and cells[1] == "TIMER", f"TIMER 行形态异常: {line!r}"
                cells[3] = MASKABLE
                lines[k] = "| " + " | ".join(cells) + " |\n"
                injected = True
                break
        if not injected:
            print("  [BAD] 注入点未找到（TIMER 行）")
            failures.append("TIMER 注入点未找到")
        target.write_text("".join(lines), encoding="utf-8")
        rc3, err3, agg3 = run(tmp)
        _report(rc3, err3, agg3, "self-test/async")
        note(rc3 == 0, "异步源 TIMER=可 必须 PASS", rc3)

        # 5) 还原并复核
        shutil.copy2(pristine / TARGETS[0], target)
        rc4, err4, agg4 = run(tmp)
        _report(rc4, err4, agg4, "self-test/final")
        note(rc4 == 0, "最终还原后必须 PASS", rc4)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"check-sync-nonmaskable --self-test: FAIL ({len(failures)} 项预期不成立)")
        return 1
    print("check-sync-nonmaskable --self-test: PASS（注入→FAIL→还原→PASS 全部成立）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="运行注入→FAIL→还原→PASS 自检")
    parser.add_argument("--spec-dir", type=str, default=None, help="改扫指定目录（默认 spec/）")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    spec_dir = Path(args.spec_dir) if args.spec_dir else SPEC
    rc, errors, agg = run(spec_dir)
    _report(rc, errors, agg, "repo")
    return rc


if __name__ == "__main__":
    sys.exit(main())
