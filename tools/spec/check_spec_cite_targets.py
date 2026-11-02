#!/usr/bin/env python3
"""`spec_cite` 目标存在性门控（SPEC-165t，SPEC-166t 改「手册: 目标」形）。

为什么
------
`opcodes.yaml` / 测试向量里的 ``spec_cite: <手册>: <目标>`` 是「期望值的来源」；
若规范重编号/删节/改名后引用不跟着改，引用会**静默指向不存在的节**。
本门控把「书 + 目标」在 `spec/` 中真实存在作为硬条件。

引用形（SPEC-166t，**不带 `§`、不带节号**）
------------------------------------------
* 指令类：``SimRISC-07: ftmin`` —— 目标须出现在该册 **附录 A（汇编指令速查）** 的助记符列；
* 非指令类：``SimRISC-00: 编码布局`` / ``DADAO-21: 参数寄存器`` —— 目标须命中该册某标题
  （剥离前导章节号后的等值或前缀，后接 `：`/`(`/空格/`—`）；
* 复合引用（``A、B`` / ``A / B``）：命中**任一**分段即可；
* 一段之内可含多条引用（以 `;` 分隔）；非 spec 前缀的分段
  （``ADR-…`` / ``contract-…`` / ``legality_rules.yaml :: …`` / 自由文本）不是本门控的判据；
* 旧形 ``SimRISC-07 §取整``（带 `§`）⇒ **报错**（引用语法已迁移）。

用法
----
* ``python3 tools/spec/check_spec_cite_targets.py``
* ``python3 tools/spec/check_spec_cite_targets.py --self-test``  # 3 类注入（错助记符/错标题/旧 § 形）

计数现场统计，不写死。退出码 0 = 全部命中；1 = 有悬空引用 / 旧形 / 自检失败。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "spec"

CITE_RE = re.compile(r"spec_cite\s*:\s*(.+?)\s*$", re.M)
BOOK = r"(?:SimRISC|DADAO|Toolchain|Machine)-\d\d"
REF_RE = re.compile(rf"^({BOOK}):\s*(.+)$")
OLD_RE = re.compile(rf"^{BOOK}\s*§")
HEAD_RE = re.compile(r"^#{1,4}\s+(.+?)\s*$")
APPENDIX_A = "## 附录 A：汇编指令速查"
LEAD_NUM_RE = re.compile(r"^\d+(?:\.\d+)*[\.、]?\s+")
SPLIT_RE = re.compile(r"[、/]")
APPENDIX_RE = re.compile(r"^附录\s*[A-Z]?[:：]?")


def spec_paths(spec_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in sorted(spec_dir.glob("*.md")):
        m = re.match(rf"({BOOK})", p.name)
        if m:
            out[m.group(1)] = p
    return out


def heads(path: Path) -> list[str]:
    return [m.group(1) for m in map(HEAD_RE.match, path.read_text(encoding="utf-8").splitlines()) if m]


def mnemonics(path: Path) -> set[str]:
    """该册「附录 A：汇编指令速查」表首列的助记符集合（无该附录 ⇒ 空集）。"""
    out: set[str] = set()
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == APPENDIX_A:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if not inside or not line.lstrip().startswith("|"):
            continue
        first = line.strip().strip("|").split("|")[0].strip()
        if first.startswith("`") and first.endswith("`") and len(first) > 2:
            out.add(first.strip("`"))
    return out


def _strip_num(text: str) -> str:
    m = LEAD_NUM_RE.match(text)
    return text[m.end():] if m else text


def title_matches(head_list: list[str], section: str) -> bool:
    """标题是否存在（等值或前缀；前缀后须为分隔符）。"""
    section = section.strip().strip("`").strip()
    if not section:
        return False
    if APPENDIX_RE.match(section):
        key = section.replace("：", ":").replace(" ", "")
        return any(h.replace("：", ":").replace(" ", "").startswith(key) for h in head_list)
    for h in head_list:
        target = _strip_num(h.replace("`", ""))
        if target == section:
            return True
        if not target.startswith(section):
            continue
        rest = target[len(section):]
        if not rest or rest[0] in (" ", "：", ":", "（", "(", "—", "，", ","):
            return True
    return False


def target_ok(book: str, target: str, head_map: dict[str, list[str]],
              mnemonic_map: dict[str, set[str]]) -> bool:
    parts = [p.strip() for p in SPLIT_RE.split(target) if p.strip()]
    for part in parts or [target]:
        if part in mnemonic_map.get(book, set()):
            return True
        if title_matches(head_map.get(book, []), part):
            return True
    return False


def cite_parts(value: str) -> list[str]:
    return [p.strip() for p in value.split(";") if p.strip()]


def scan_yaml(path: Path, head_map: dict[str, list[str]],
              mnemonic_map: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = CITE_RE.search(line)
        if not m:
            continue
        value = m.group(1).strip().strip("'\"")
        for part in cite_parts(value):
            if OLD_RE.match(part):
                errors.append(f"{path}:{ln}: 旧形引用（带 `§`）：`{part[:60]}`"
                              f"（应写 `手册: 小节标题` 或 `手册: 助记符`）")
                continue
            r = REF_RE.match(part)
            if not r:
                continue  # ADR / contract / 自由文本分段不属本门控判据
            book, target = r.group(1), r.group(2).strip()
            if book not in head_map:
                errors.append(f"{path}:{ln}: 未知 spec 前缀 {book}")
            elif not target_ok(book, target, head_map, mnemonic_map):
                errors.append(f"{path}:{ln}: `{book}: {target}` 既非该册助记符"
                              f"（附录 A）也非该册标题")
    return errors


def yaml_targets(contracts: Path, tests: Path) -> list[Path]:
    files = sorted(p for p in contracts.glob("*.yaml"))
    if tests.is_dir():
        files += sorted(p for p in tests.rglob("*.yaml"))
    return files


def run(spec_dir: Path, contracts: Path, tests: Path, verbose: bool = True) -> int:
    paths = spec_paths(spec_dir)
    head_map = {k: heads(v) for k, v in paths.items()}
    mnemonic_map = {k: mnemonics(v) for k, v in paths.items()}
    targets = yaml_targets(contracts, tests)
    errors: list[str] = []
    cites = 0
    for p in targets:
        cites += len(CITE_RE.findall(p.read_text(encoding="utf-8")))
        errors.extend(scan_yaml(p, head_map, mnemonic_map))
    if verbose:
        print(f"check-spec-cite-targets: spec_books={len(paths)}  yaml_files={len(targets)}  "
              f"spec_cite_lines={cites}  mnemonics={sum(len(v) for v in mnemonic_map.values())}  "
              f"unresolved={len(errors)}")
        for e in errors[:40]:
            print("  " + e)
        if len(errors) > 40:
            print(f"  … {len(errors) - 40} more")
    if errors:
        print(f"check-spec-cite-targets: FAIL ({len(errors)} dangling cite(s))")
        return 1
    print("check-spec-cite-targets: PASS（全部 spec_cite 指向真实存在的「手册 + 助记符/标题」）")
    return 0


def self_test() -> int:
    """基线 PASS；3 类注入（错助记符 / 错标题 / 旧 `§` 形）⇒ 均须 FAIL。"""
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "SPEC-166t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="cite-", dir=tmp_root))
    head_map = {k: heads(v) for k, v in spec_paths(SPEC).items()}
    mnemonic_map = {k: mnemonics(v) for k, v in spec_paths(SPEC).items()}
    # 取一条真实可解析的助记符与一条真实标题作基线
    book_mn = sorted(k for k, v in mnemonic_map.items() if v)[0]
    some_mnemonic = sorted(mnemonic_map[book_mn])[0]
    book_t = "SimRISC-00"
    some_title = _strip_num(heads(SPEC / "SimRISC-00-指令系统设计.md")[0])
    cases = [
        ("baseline", f"spec_cite: {book_mn}: {some_mnemonic}", True),
        ("baseline-title", f"spec_cite: {book_t}: {some_title}", True),
        ("bad-mnemonic", f"spec_cite: {book_mn}: nosuchinsn", False),
        ("bad-title", f"spec_cite: {book_t}: 不存在的节", False),
        ("old-sigil", f'spec_cite: "{book_t} §{some_title}"', False),
    ]
    ok = True
    try:
        case_dir = tmpdir / "contracts"
        case_dir.mkdir()
        target = case_dir / "probe.yaml"
        for name, line, expect_zero in cases:
            target.write_text("- id: probe\n  " + line + "\n", encoding="utf-8")
            rc = run(SPEC, case_dir, tmpdir / "_no_tests", verbose=False)
            good = (rc == 0) if expect_zero else (rc != 0)
            print(f"[{'PASS' if good else 'FAIL'}] self-test {name}: "
                  f"期望={'0' if expect_zero else '非0'} 实际={rc}（{line[:60]}）")
            ok = ok and good
        # 空注入反例：确保探针不是恒真（把 baseline 换成空文件 ⇒ 无 spec_cite ⇒ PASS，
        # 说明「PASS」来自解析成功而非短路）
        target.write_text("# no spec_cite here\n", encoding="utf-8")
        rc = run(SPEC, case_dir, tmpdir / "_no_tests", verbose=False)
        print(f"[{'PASS' if rc == 0 else 'FAIL'}] self-test empty-file: 期望=0 实际={rc}"
              f"（无引用 ⇒ 无判据）")
        ok = ok and rc == 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="spec_cite 目标存在性门控")
    ap.add_argument("--spec-dir", type=Path, default=SPEC)
    ap.add_argument("--contracts", type=Path, default=ROOT / "contracts")
    ap.add_argument("--tests", type=Path, default=ROOT / "tests")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    return run(args.spec_dir, args.contracts, args.tests)


if __name__ == "__main__":
    raise SystemExit(main())
