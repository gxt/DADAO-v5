#!/usr/bin/env python3
"""`spec_cite` 目标存在性门控（SPEC-165t）。

为什么
------
`opcodes.yaml` / 测试向量里的 ``spec_cite: SimRISC-XX §<节>`` 是「期望值的来源」；
若规范重编号或删节后引用不跟着改，引用会**静默指向不存在的节**（引用完整性
只在 `check-spec-refs` 覆盖 `.tao/contracts/*.md` 的方括号形式）。本门控把
「书 + 节」在 `spec/` 中真实存在作为硬条件。

判据
----
* 扫描 ``contracts/*.yaml`` 与 ``tests/**/*.yaml`` 的 ``spec_cite:`` 值；
* 值内以 ``;`` 分段；**仅**校验带 spec 前缀的分段
  （``SimRISC-nn`` / ``DADAO-nn`` / ``Toolchain-nn`` / ``Machine-nn``），
  其余分段（``ADR-…`` / ``contract-…`` / 自由文本）不是本门控的判据；
* 节号形态：
  - 数字（``4.2`` / ``7``）：须命中某标题的前导章节号；
  - 文本（``存取RD寄存器``）：须命中某标题（剥离前导章节号后）的等值或前缀
    （后接 ``：``/`(`/空格/``—``）；复合引用（``A、B`` / ``A §B`` / ``A / B``）
    命中**任一**分段即可；
  - ``附录 A`` / ``附录 B`` / ``附录：版本与变更记录``：须命中该册同名附录标题。

用法
----
* ``python3 tools/spec/check_spec_cite_targets.py``
* ``python3 tools/spec/check_spec_cite_targets.py --self-test``  # 注入 1 条错节号 ⇒ FAIL

计数现场统计，不写死。退出码 0 = 全部命中；1 = 有悬空引用 / 自检失败。
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
REF_RE = re.compile(
    r"^(SimRISC-\d\d|DADAO-\d\d|Toolchain-\d\d|Machine-\d\d)\s*§\s*(.+)$")
HEAD_RE = re.compile(r"^#{1,4}\s+(.+?)\s*$")
LEAD_NUM_RE = re.compile(r"^\d+(?:\.\d+)*[\.、]?\s+")
NUMERIC_RE = re.compile(r"^\d+(?:\.\d+)*$")
SPLIT_RE = re.compile(r"[、/]| §")
APPENDIX_RE = re.compile(r"^附录\s*[A-Z]?[:：]?")

# 复合引用的分隔（`A、B` / `A §B` / `A / B`）与判定所需的最小分段


def spec_paths(spec_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in sorted(spec_dir.glob("*.md")):
        m = re.match(r"((?:SimRISC|DADAO|Toolchain|Machine)-\d+)", p.name)
        if m:
            out[m.group(1)] = p
    return out


def heads(path: Path) -> list[str]:
    return [m.group(1) for m in map(HEAD_RE.match, path.read_text(encoding="utf-8").splitlines()) if m]


def _strip_num(text: str) -> str:
    m = LEAD_NUM_RE.match(text)
    return text[m.end():] if m else text


def section_matches(head_list: list[str], section: str) -> bool:
    """节号/节名是否命中某标题（数字严格前导；文本允许后缀子标题）。"""
    section = section.strip().strip("`").lstrip("§").strip()
    if not section:
        return False
    if APPENDIX_RE.match(section):
        key = section.replace("：", ":").replace(" ", "")
        return any(h.replace("：", ":").replace(" ", "").startswith(key) for h in head_list)
    if NUMERIC_RE.match(section):
        for h in head_list:
            text = h.replace("`", "")
            if text == section:
                return True
            if text.startswith(section) and text[len(section):][:1] in (" ", "."):
                return True
        return False
    for h in head_list:
        target = _strip_num(h.replace("`", ""))
        if not target.startswith(section):
            continue
        rest = target[len(section):]
        if not rest or rest[0] in (" ", "：", ":", "（", "(", "—", "，", ","):
            return True
    return False


def cite_parts(value: str) -> list[str]:
    return [p.strip() for p in value.split(";") if p.strip()]


def ref_matches(head_list: list[str], section: str) -> bool:
    return any(section_matches(head_list, part) for part in SPLIT_RE.split(section) if part.strip())


def scan_yaml(path: Path, spec_heads: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = CITE_RE.search(line)
        if not m:
            continue
        value = m.group(1).strip().strip("'\"")
        for part in cite_parts(value):
            r = REF_RE.match(part)
            if not r:
                continue  # ADR / contract / 自由文本分段不属本门控判据
            prefix, section = r.group(1), r.group(2).strip()
            hs = spec_heads.get(prefix)
            if hs is None:
                errors.append(f"{path}:{ln}: 未知 spec 前缀 {prefix}")
            elif not ref_matches(hs, section):
                errors.append(f"{path}:{ln}: `{prefix} §{section}` 在 spec/ 中不存在")
    return errors


def yaml_targets(contracts: Path, tests: Path) -> list[Path]:
    files = sorted(p for p in contracts.glob("*.yaml"))
    if tests.is_dir():
        files += sorted(p for p in tests.rglob("*.yaml"))
    return files


def run(spec_dir: Path, contracts: Path, tests: Path, verbose: bool = True) -> int:
    paths = spec_paths(spec_dir)
    spec_heads = {k: heads(v) for k, v in paths.items()}
    targets = yaml_targets(contracts, tests)
    errors: list[str] = []
    cites = 0
    for p in targets:
        cites += len(CITE_RE.findall(p.read_text(encoding="utf-8")))
        errors.extend(scan_yaml(p, spec_heads))
    if verbose:
        print(f"check-spec-cite-targets: spec_books={len(paths)}  yaml_files={len(targets)}  "
              f"spec_cite_lines={cites}  unresolved={len(errors)}")
        for e in errors[:40]:
            print("  " + e)
        if len(errors) > 40:
            print(f"  … {len(errors) - 40} more")
    if errors:
        print(f"check-spec-cite-targets: FAIL ({len(errors)} dangling cite(s))")
        return 1
    print("check-spec-cite-targets: PASS（全部 spec_cite 指向真实存在的书+节）")
    return 0


def self_test() -> int:
    """基线 PASS；把一条真实 spec_cite 的节号改成不存在的号 ⇒ 须 FAIL。"""
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "SPEC-165t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="cite-", dir=tmp_root))
    num_re = re.compile(r"(SimRISC-\d\d §)(\d+(?:\.\d+)*)")
    target = None
    for cand in yaml_targets(ROOT / "contracts", ROOT / "tests"):
        text = cand.read_text(encoding="utf-8")
        m = None
        for line in text.splitlines():
            if "spec_cite" not in line:
                continue
            m = num_re.search(line)
            if m:
                break
        if m:
            target = (cand, text, m)
            break
    assert target, "self-test 需要至少一条数字节号的 spec_cite"
    src, text, m = target
    case_dir = tmpdir / "contracts"
    case_dir.mkdir()
    ok = True
    try:
        (case_dir / src.name).write_text(text, encoding="utf-8")
        rc = run(SPEC, case_dir, tmpdir / "_no_tests", verbose=False)
        good = rc == 0
        print(f"[{'PASS' if good else 'FAIL'}] self-test baseline: 期望=0 实际={rc}"
              f"（{src.name}）")
        ok = ok and good

        broken_line = line[:m.start(2)] + "9.99" + line[m.end(2):]
        broken = text.replace(line, broken_line, 1)
        assert broken != text, "空注入"
        (case_dir / src.name).write_text(broken, encoding="utf-8")
        rc = run(SPEC, case_dir, tmpdir / "_no_tests", verbose=False)
        good = rc != 0
        print(f"[{'PASS' if good else 'FAIL'}] self-test broken-cite: "
              f"期望=非0 实际={rc}（{m.group(1)}9.99 不存在）")
        ok = ok and good
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
