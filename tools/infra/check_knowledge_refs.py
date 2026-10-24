#!/usr/bin/env python3
"""check-knowledge-refs: (A) 被引用的 `.work/**` 材料不得悬空 (INFRA-058t / INTEG-037t)；
(B) `.tao/knowledge/**` 内的**小节级互指**须指向真实存在的文档小节 (INFRA-080t)。

背景（用户 2026-10-11 裁定「认 + 并入 INFRA-058t」，`lessons §3.16`）：
  - `.work/` 被 `.gitignore` 整体忽略、只在本机存在 ⇒ 仅放 `.work/` 的**被引用材料**
    会**悬空**、不可复现。
  - 归类判据（四分类）：`spec/` = 规范正文；`.tao/knowledge/` = 结论/设计/口径（含长文）；
    `.work/log/` = 一次性过程（可删）；**凡被引用的材料，一律不得只放 `.work/`**。

(A) 检查（**悬空即红**）：
  扫描 `AGENTS.md` / `spec/**/*.md` / `.tao/knowledge/**/*.md` / `.tao/tasks/**/*.md`
  / `.tao/contracts/**/*.md` 中对 `.work/**` 的引用；对**可判定的具体路径**做存在性检查，不存在即 FAIL。

引用形态口径（详见 AGENTS.md「文档分层与单一真源」与 lessons §3.16）：
  - `<>` / `*` / `$` 形（占位或通配，如 `.work/log/<模块>/`、`.work/log/**`、
    `.work/log/testcases/TESTCASES-036t-*.log`）⇒ **不可判定，跳过**；
  - 以 `-` 结尾（前缀截断，如 `.work/log/testcases/TESTCASES-039t-`）⇒ **跳过**；
  - 位于「删除语境」行（含 `已删`/`删旧`/`删除`/`deleted`/`removed`）的引用 ⇒ 记录
    「历史/删除引用」，**不要求存在**；
  - `.work/build/**`、`.work/source/**`（构建/源码树，`clean-work` 即清）⇒ **显式豁免**；
  - 其余具体路径 ⇒ **要求存在**（文件或目录），不存在即红。

(B) 检查（**悬空即红**；用户 2026-10-14 裁定「A」= 两条都补、并入 L1；任务 `INFRA-080t`）：
  扫描面 = `.tao/knowledge/**/*.md` **+** `.tao/contracts/**/*.md`（后者 `SPEC-171t` 并入：
  契约正文 13 条小节级悬空修完后纳入同一判据防回归；两个面各自空转即 FAIL）；对下列**小节级互指** token
  做目标存在性检查，目标必须是**同仓真实存在**的文档小节：
  - `ADR-<4 位数字>` ⇒ 目标文件 `.tao/adr/adr-<NNNN>-*.md`；
    带**小节设计符**者还须在目标文件内找到该小节：
      - 决策设计符 `§Dn` / `Dn` / `§Cn` / `Cn`（`§` 可选）⇒ 目标文件内有该**决策标签**
        （`**Dn — <标题>**` / `### Dn <标题>` / `#### Dn.m <标题>` / `- **Dn（…）**` 等）；
        带子号者（`Dn.m`）另接受「父决策存在 **且** 目标文件提及该子设计符」（子项未必有独立标题，
        如 `adr-0012` 的 `D3.1` 仅在其 `## 状态说明`/`## 修订` 提及）；
      - 命名小节 `§<Name>`（如 `§Consequences`）⇒ 目标文件内有同名标题（兼容中文括注
        `## Consequences（影响）`）；
      - **区间**（`D1–D8`）按**端点集合**判定（两端均须存在）；`§` 后**尾随内容**取**第一个**
        小节设计符为准；
  - `contract-<名>[.md] §<n>(.<m>)` ⇒ 目标文件 `.tao/contracts/contract-<名>.md` 的该 `§` 小节存在；
    无 `§` 者只校验**文件存在**。

(B) 的**显式跳过**（逐类计数 + 明细打印，**不得静默放过**）：
  - 代码块（``` 围栏）内的示意 token ⇒ 跳过；
  - 占位/示意设计符（`DN`、`N` 等非真实编号/名称）⇒ 跳过；
  - 其它无法判定的设计符形 ⇒ 跳过并列明细（供人工复核）。

fail-closed: (A) 或 (B) 有悬空 → exit 1；任一扫描面**空转**（无任何可判定 token）→ exit 1；
否则 exit 0。

Usage:
    python3 tools/infra/check_knowledge_refs.py [--root DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 引用 token：`.work/` 后接路径字符；遇空白 / 反引号 / CJK 等即止。
_REF_RE = re.compile(r"\.work/[A-Za-z0-9_./<>*$-]+")

# 占位/通配/不可判定标记。
_PLACEHOLDER_CHARS = ("<", ">", "*", "$")

# 删除语境标记（历史引用：记录「某路径已删」，不要求其存在）。
_DELETION_MARKERS = ("已删", "删旧", "删除", "删掉", "deleted", "removed")

# 构建/源码树豁免（`clean-work` 即清；risk B）。
_EXEMPT_PREFIXES = (".work/build", ".work/source")


def _is_exempt(path: str) -> bool:
    for p in _EXEMPT_PREFIXES:
        if path == p or path.startswith(p + "/"):
            return True
    return False


def _classify(raw: str) -> str:
    """Return one of: 'skip_placeholder', 'skip_prefix', 'exempt', 'check'."""
    tok = raw
    if any(c in tok for c in _PLACEHOLDER_CHARS):
        return "skip_placeholder"
    # strip a trailing sentence period (paths never end with '.')
    tok = tok.rstrip(".")
    if tok.endswith("-"):
        return "skip_prefix"
    if _is_exempt(tok):
        return "exempt"
    # path used for existence check is the cleaned token
    return "check"


# ---------------------------------------------------------------------------
# (B) 小节级互指（INFRA-080t）
# ---------------------------------------------------------------------------

# 扫描面：`.tao/knowledge/**/*.md`（INFRA-080t）+ `.tao/contracts/**/*.md`（SPEC-171t：
# 契约正文的 13 条小节级悬空已修，纳入同一判据以防回归；两处均为必扫面，各自空转即 FAIL）。
_SECTION_SCAN_DIRS = (".tao/knowledge", ".tao/contracts")

# 目标：ADR 文件目录 / 契约文件目录。
_ADR_DIR = ".tao/adr"
_CONTRACT_DIR = ".tao/contracts"

# `ADR-<4 位数字>` token。
_ADR_TOKEN_RE = re.compile(r"ADR-(\d{4})\b")

# `contract-<名>[.md][ §<n>(.<m>)(–<k>)]` token。
_CONTRACT_TOKEN_RE = re.compile(
    r"contract-([a-z0-9-]+)(?:\.md)?"
    r"(?:[ \t]*§[ \t]*(\d+(?:\.\d+)*)"
    r"(?:[ \t]*[–~][ \t]*§?[ \t]*(\d+(?:\.\d+)*))?"
    r")?"
)

# 决策设计符：`§Dn` / `Dn` / `§Cn` / `Cn`（`§` 可选；`Dn`、`Dn.m`，含 `–`/`~` 区间）。
_ADR_DECISION_DESIG_RE = re.compile(
    r"^[ \t]*§?[ \t]*([DC]\d+(?:\.\d+)*)"
    r"(?:[ \t]*[–~][ \t]*[DC]?(\d+(?:\.\d+)*))?"
)

# 命名小节设计符：`§Consequences`（须带 `§` 且首字后有小写，避免把普通英文词/占位符误当小节）。
_ADR_SECTION_DESIG_RE = re.compile(r"^[ \t]*§[ \t]*([A-Z][a-z][A-Za-z]*)\b")

# 占位/示意设计符：`DN` / `§N` / 单字母等（非真实编号或名称）⇒ 跳过。
_ADR_PLACEHOLDER_DESIG_RE = re.compile(r"^[ \t]*§?[ \t]*([A-Z]{1,3})(?![a-z0-9])")

# 目标文件内的标签提取：粗体标签 `**Dn …**`、`- **Dn（…）**`。
_ADR_BOLD_LABEL_RE = re.compile(r"\*\*[ \t]*([DC]\d+(?:\.\d+)*)")
# 目标文件内的标签提取：标题标签 `### Dn …`（含 `D2/D3/D4` 多号形）。
_ADR_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_ADR_HEADING_DESIG_RE = re.compile(r"(?:^|[、/])\s*([DC]\d+(?:\.\d+)*)")
# 契约小节标题：`## §<n> …` / `### §<n>.<m> …`
_CONTRACT_SECTION_HEADING_RE = re.compile(r"^#{1,6}\s+§(\d+(?:\.\d+)*)\b")

_SECTION_SKIP_DETAIL_LIMIT = 20


def _iter_lines_with_fences(text: str) -> list[tuple[int, str]]:
    """Return (lineno, line) for lines outside ``` fenced code blocks."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((lineno, line))
    return out


def _adr_labels(text: str) -> tuple[set[str], set[str]]:
    """Return (decision_ids, section_names) labeled in an ADR/contract file."""
    decisions: set[str] = set()
    sections: set[str] = set()
    for line in text.splitlines():
        for m in _ADR_BOLD_LABEL_RE.finditer(line):
            decisions.add(m.group(1))
        hm = _ADR_HEADING_RE.match(line)
        if hm:
            title = hm.group(1).strip()
            for m in _ADR_HEADING_DESIG_RE.finditer(title):
                decisions.add(m.group(1))
            # 命名小节名 = 标题首词（切在空白 / 全角/半角括号 / 冒号），兼容 `Consequences（影响）`。
            name = re.split(r"[（(：:\s]", title, 1)[0]
            if name:
                sections.add(name)
    return decisions, sections


def _find_adr_file(root: Path, num: str) -> Path | None:
    cands = sorted((root / _ADR_DIR).glob(f"adr-{num}-*.md"))
    return cands[0] if cands else None


def _contract_section_ids(root: Path, name: str) -> set[str] | None:
    """Section ids (`n`, `n.m`, …) of `.tao/contracts/contract-<name>.md`; None if file missing."""
    p = root / _CONTRACT_DIR / f"contract-{name}.md"
    if not p.is_file():
        return None
    ids: set[str] = set()
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _CONTRACT_SECTION_HEADING_RE.match(line)
        if m:
            ids.add(m.group(1))
    return ids


def _decision_desig_missing(desig: str, decisions: set[str], target_text: str) -> bool:
    """True if decision designator `desig` is not acknowledged by the **target** ADR file."""
    if desig in decisions:
        return False
    if "." in desig:
        parent = desig.split(".", 1)[0]
        # 子设计符（`Dn.m`）：父决策须存在，且**目标文件**须提及该子设计符
        # （子项未必有独立标题，如 `adr-0012` 的 `D3.1` 仅在其 `## 状态说明`/`## 修订` 提及）。
        mentioned = re.search(
            r"(?<![A-Za-z0-9])" + re.escape(desig) + r"(?![0-9])", target_text
        )
        return not (parent in decisions and mentioned)
    return True


def audit_section_refs(root: Path) -> dict:
    """(B) section-level cross-reference existence check; prints its own report block."""
    files: list[Path] = []
    face_checked: dict[str, int] = {}
    for scan_dir in _SECTION_SCAN_DIRS:
        base = root / scan_dir
        face_files = sorted(base.rglob("*.md")) if base.is_dir() else []
        files.extend(face_files)
        face_checked[scan_dir] = 0

    n_adr = n_adr_bare = n_adr_ph = n_adr_unknown = n_adr_checked = 0
    n_contract = n_contract_bare = n_contract_checked = 0
    dangling: list[tuple[str, int, str, str]] = []
    skipped: list[tuple[str, int, str, str]] = []

    adr_cache: dict[str, tuple[set[str], set[str], str] | None] = {}
    con_cache: dict[str, set[str] | None] = {}

    for f in files:
        rel = str(f.relative_to(root))
        face = next((d for d in _SECTION_SCAN_DIRS if rel.startswith(d + "/")), None)
        checked_before = n_adr_checked + n_contract_checked
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in _iter_lines_with_fences(raw):
            for m in _ADR_TOKEN_RE.finditer(line):
                n_adr += 1
                num = m.group(1)
                raw_token = m.group(0)
                tail = line[m.end():m.end() + 24]

                designs: list[str] = []
                kind = ""
                dm = _ADR_DECISION_DESIG_RE.match(tail)
                if dm:
                    kind = "decision"
                    designs.append(dm.group(1))
                    if dm.group(2):
                        designs.append(dm.group(1)[0] + dm.group(2))
                else:
                    pm = _ADR_PLACEHOLDER_DESIG_RE.match(tail)
                    if pm:
                        n_adr_ph += 1
                        skipped.append((rel, lineno, f"{raw_token} {pm.group(1)}",
                                        "占位/示意设计符 (跳过)"))
                        continue
                    sm = _ADR_SECTION_DESIG_RE.match(tail)
                    if sm:
                        kind = "namesec"
                        designs.append(sm.group(1))
                    else:
                        wm = re.match(r"^[ \t]*§?[ \t]*([A-Za-z][A-Za-z0-9.]*)", tail)
                        if wm:
                            n_adr_unknown += 1
                            skipped.append((rel, lineno, f"{raw_token} {wm.group(1)}",
                                            "无法判定的设计符形 (跳过)"))
                            continue
                        n_adr_bare += 1
                        designs = []

                if num not in adr_cache:
                    p = _find_adr_file(root, num)
                    if p is None:
                        adr_cache[num] = None
                    else:
                        ptext = p.read_text(encoding="utf-8", errors="replace")
                        dec, sec = _adr_labels(ptext)
                        adr_cache[num] = (dec, sec, ptext)
                tgt = adr_cache[num]
                if tgt is None:
                    dangling.append((rel, lineno, f"ADR-{num}", "目标文件不存在"))
                    continue
                decisions, sections, target_text = tgt
                if not designs:
                    continue
                n_adr_checked += 1
                for d in designs:
                    if kind == "namesec":
                        ok = any(s.lower() == d.lower() for s in sections)
                    else:
                        ok = not _decision_desig_missing(d, decisions, target_text)
                    if not ok:
                        dangling.append((rel, lineno, f"ADR-{num} {d}", "目标小节不存在"))

            for m in _CONTRACT_TOKEN_RE.finditer(line):
                n_contract += 1
                name = m.group(1)
                sec, sec_end = m.group(2), m.group(3)
                if name not in con_cache:
                    con_cache[name] = _contract_section_ids(root, name)
                ids = con_cache[name]
                if ids is None:
                    dangling.append((rel, lineno, f"contract-{name}.md", "目标文件不存在"))
                    continue
                if sec is None:
                    n_contract_bare += 1
                    continue
                n_contract_checked += 1
                for sid in ([sec] + ([sec_end] if sec_end else [])):
                    if sid not in ids:
                        dangling.append(
                            (rel, lineno, f"contract-{name}.md §{sid}", "目标小节不存在")
                        )
        if face is not None:
            face_checked[face] += (n_adr_checked + n_contract_checked) - checked_before

    print()
    print(f"  [INFRA-080t] 小节级互指存在性（扫描面: {' + '.join(_SECTION_SCAN_DIRS)}/**/*.md，"
          f"文件 {len(files)}）")
    for scan_dir in _SECTION_SCAN_DIRS:
        print(f"      {scan_dir}/**/*.md: 校验 {face_checked[scan_dir]} 条")
    print(f"    `ADR-…` 引用总数: {n_adr}")
    print(f"      无小节设计符 (只校验文件存在): {n_adr_bare}")
    print(f"      占位/示意 (跳过): {n_adr_ph}")
    print(f"      无法判定 (跳过): {n_adr_unknown}")
    print(f"      带小节设计符 (校验): {n_adr_checked}")
    print(f"    `contract-…` 引用总数: {n_contract}")
    print(f"      无 `§` (只校验文件存在): {n_contract_bare}")
    print(f"      带 `§` 小节 (校验): {n_contract_checked}")
    if skipped:
        print(f"    跳过明细 (共 {len(skipped)}，最多列 {_SECTION_SKIP_DETAIL_LIMIT} 条):")
        for rel, lineno, tok, why in skipped[:_SECTION_SKIP_DETAIL_LIMIT]:
            print(f"      {rel}:{lineno}  {tok}  [{why}]")
    print(f"    悬空: {len(dangling)}")
    for rel, lineno, tok, why in dangling:
        print(f"      {rel}:{lineno}  {tok}  ({why})")

    return {
        "adr": n_adr,
        "adr_checked": n_adr_checked,
        "adr_bare": n_adr_bare,
        "adr_placeholder": n_adr_ph,
        "adr_unknown": n_adr_unknown,
        "contract": n_contract,
        "contract_checked": n_contract_checked,
        "contract_bare": n_contract_bare,
        "checked": n_adr_checked + n_contract_checked,
        "face_checked": face_checked,
        "dangling": dangling,
        "skipped": skipped,
    }


def _scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    agents = root / "AGENTS.md"
    if agents.is_file():
        files.append(agents)
    for sub in ("spec", ".tao/knowledge", ".tao/contracts", ".tao/tasks"):
        d = root / sub
        if d.is_dir():
            files.extend(sorted(d.rglob("*.md")))
    return files


def audit(root: Path) -> int:
    files = _scan_files(root)
    if not files:
        print("ERROR: no scannable files found (AGENTS.md / spec / .tao/knowledge / .tao/contracts / .tao/tasks)",
              file=sys.stderr)
        return 1

    found = 0                 # total `.work/` refs seen
    checked = 0               # concrete paths existence-checked
    dangling: list[tuple[str, int, str]] = []
    n_placeholder = 0
    n_prefix = 0
    n_exempt = 0
    n_deleted = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in _REF_RE.finditer(line):
                found += 1
                raw = m.group(0)
                kind = _classify(raw)
                if kind == "skip_placeholder":
                    n_placeholder += 1
                    continue
                if kind == "skip_prefix":
                    n_prefix += 1
                    continue
                if kind == "exempt":
                    n_exempt += 1
                    continue
                # deletion-context historical reference: record, do not require existence
                if any(mk in line for mk in _DELETION_MARKERS):
                    n_deleted += 1
                    continue
                checked += 1
                tok = raw.rstrip(".")
                if not (root / tok).exists():
                    dangling.append((str(f.relative_to(root)), lineno, tok))

    print("=" * 72)
    print("check-knowledge-refs — 被引用 `.work/**` 材料悬空检查")
    print("=" * 72)
    print(f"  扫描文件数: {len(files)}")
    print(f"  `.work/` 引用总数: {found}")
    print(f"    占位/通配 (跳过): {n_placeholder}")
    print(f"    前缀截断 (跳过): {n_prefix}")
    print(f"    构建/源码 (豁免): {n_exempt}")
    print(f"    删除语境 (历史): {n_deleted}")
    print(f"    具体路径 (校验): {checked}")
    print(f"  悬空: {len(dangling)}")
    if dangling:
        print()
        for rel, lineno, tok in dangling:
            print(f"    {rel}:{lineno}  {tok}")

    # ---- (B) 小节级互指（INFRA-080t）----
    sec = audit_section_refs(root)

    print("-" * 72)

    # 判据顺序：先报**悬空**（两扫描面各自可达 FAIL），再报**空转**（fail-closed）。
    # 注：原实现只有 (A)，`checked == 0` 与 `dangling` 互斥 ⇒ 本顺序不改变 (A) 的既有行为。
    if dangling:
        print(f"结果: FAIL ({len(dangling)} 悬空 `.work/**` 引用)")
        return 1
    if sec["dangling"]:
        print(f"结果: FAIL ({len(sec['dangling'])} 悬空小节级互指)")
        return 1
    # §2.20 自证命中：两个扫描面 (A)/(B) 都必须确有 token 被判定，(B) 的每个目录面亦然，
    # 否则判为「空转」而 FAIL。
    if checked == 0:
        print("ERROR: 无任何可校验的 `.work/**` 引用（扫描面为空 ⇒ 门控空转，fail-closed）",
              file=sys.stderr)
        print("结果: FAIL (vacuous: no checkable .work/** refs)")
        return 1
    vacuous_faces = [d for d, n in sec["face_checked"].items() if n == 0]
    if vacuous_faces:
        print(f"ERROR: 小节级互指扫描面空转（无可校验 token）: {', '.join(vacuous_faces)}"
              f"（fail-closed）", file=sys.stderr)
        print("结果: FAIL (vacuous: no checkable section-level cross-refs)")
        return 1
    print(f"结果: PASS (0 悬空 `.work/**` 引用; 0 悬空小节级互指；"
          f"小节级: ADR {sec['adr_checked']} + contract {sec['contract_checked']} 已校验)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parents[2],
                        help="repository root (default: repo root)")
    args = parser.parse_args()
    return audit(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
