#!/usr/bin/env python3
"""int_diff.py -- 整数 / 访存 / 控制流 / 位操作 / 原子 三平台逐例差分（`m13-integ-003`）.

本脚本**不跑 guest**：输入是 `run_asm_suite.py` 的三平台逐镜像 JSON（同一份 ELF
在 chipyard / qemu / gem5 上产生的 status/exit/结果字节流）+ 每镜像的 `.out` 结果
字节流（按 8 字节检查点切分），再加上静态真源：

  * `contracts/opcodes.yaml`（每条 id 的 `spec_cite` = 语义依据出处，现场解析）；
  * `spec/SimRISC-NN-*.md`（按册号对应章节；逐 id 核助记符是否在该章出现）；
  * `.tao/contracts/contract-isa.md`（人读契约正文，按族给出口径指针）；
  * `tests/inst.yaml`（载体是否入索引）。

输出 `.tao/knowledge/refs/m13-003-int-diff.{json,md}`，内容是上述输入的
**确定性函数**：不写生成时刻、不写运行期路径。报告另记 **输入 commit**
（`--input-commit`，缺省取 `git rev-parse HEAD`）：没有这个锚，后人只能靠
`--check` 发现报告陈旧（`m13-integ-003` 复核 F3）。`--check` 因此要求在同一
commit 上复算（或显式传同一 sha）。

范围（现场枚举，不写死计数）：`tests/inst/**/*.S` 中**非 cfx**（册 `11-cfx`）且
**非 FP**（`contracts/opcodes.yaml` 的 `scope: fp`，含散落在 01/02/03 册的 14 条）
的全部载体。`00-isa-design/undi_reserved.S` 是**非 id 载体**（保留编码 ⇒ UNDI），
按它自己的文件头取 spec 出处，不冒充 opcode id。

复用（不复制另一套口径）：

  * 逐镜像记录装载 / 三平台判定 / 结果字节流读取 = `fp_diff.py`
    （`load_run` / `merge_runs` / `classify` / `_read_out` / `chain_byte_errors`；
    `m13-integ-002` 已验收）；
  * 载体用例行 / 故障例解析 = `tests/ee-tiny/run_asm_suite.py::scan_source`；
  * owner 词表 = `tests/ee-user/se_tset_matrix.OWNERS`（经 `fp_diff` 转出）；**平台状态词表不另立**：
    状态由 `rc` 现场派生（`0` ⇒ `PASS`，非 `0` ⇒ `FAIL`），三平台判定复用
    `fp_diff.classify`（本脚本不 import `run_parity`，其 `STATUSES` 是 SE 侧词表）。

判定（fail-closed）：

  * 每个镜像记录必须三平台齐全；缺平台 / 未知 id / 重复记录 / `ok` 与平台记录
    矛盾 / 点号与载体不符 ⇒ 非零退出；
  * 每个非 `AGREE_PASS` 镜像必须命中显式归因表（`spec` / `implementation` /
    `test asset` / `environment` / `budget`），未归因即 rc=1；
  * `spec_cite` 解析不到章节或章内找不到助记符 ⇒ 记为 **spec 歧义**并逐条列出
    （不是平台差异，但必须显式留痕，不得静默放过）；
  * `AGREE_PASS` 链例镜像必须三平台 `.out` **逐字节相等**（不只看 runner 的
    `bytes` 计数），且长度 = `8 × 检查点数`；不符即 rc=1
    （`m13-integ-003` 复核 F2：`fp_diff.chain_byte_errors`）。

用法::

    python3 tools/testcases/parity/int_diff.py \\
        --run int-book=<run.json> --work int-book=<work-dir> \\
        --engine qemu=<md5> --engine gem5=<md5> --engine chipyard=<md5> \\
        --json-out <运行期>/m13-003-int-diff.json \\
        --markdown-out <运行期>/m13-003-int-diff.md

    --check <md|json>   与落盘报告逐字节比对（不符 rc=1；缺文件 rc=2）
    --input-commit <sha> 报告记录/比较的输入 commit（缺省 `git rev-parse HEAD`）
    --self-test         合成输入 + 每类反例一条，逐条要求被判出；全判出才 rc=0

退出码：0 不变式全成立；1 不变式失败（差异未归因 / 缺平台 / 计数不符 /
`--check` 不一致 / 自检有注入未判出）；2 setup 错（缺文件、坏 JSON、坏参数）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
for _p in (str(_HERE), str(_REPO / "tools" / "infra"),
           str(_REPO / "tests" / "ee-tiny")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fp_diff as fp                    # noqa: E402  (逐例装载/判定/字节流)
import run_asm_suite as asm             # noqa: E402  (载体现场统计)

SCHEMA = "int-three-platform-diff/1"
TASK = "m13-integ-003"
PLATFORMS = fp.PLATFORMS
OWNERS = fp.OWNERS
CFX_BOOK = "11-cfx"
SetupError = fp.SetupError
DiffError = fp.DiffError

#: 族 = `.S` 载体所在册；册号直接对应 `spec/SimRISC-NN-*` 章节号。
BOOK_RE = re.compile(r"^(\d{2})-([a-z0-9-]+)$")

#: 归因登记表（每条差异必须命中；未登记 ⇒ 报告 FAIL）。
#: key = (id, case_n)；`owner` ∈ OWNERS；`spec_cite` 必须指到 `spec/` 的具体条目。
ATTRIBUTIONS: dict[tuple[str, int], dict] = {}

#: `--attribution` 读入的逐条归因（同样逐条校验；不提供即空表 ⇒ 任何差异都 FAIL）。
EXTERNAL_ATTRIBUTIONS: dict[tuple[str, int], dict] = {}

#: 已知项：单列，不混入平台差异计数（每条都要有可核查的适用性说明）。
KNOWN_ITEMS = {
    "ISS-357": dict(
        status="closed (M13: m13-testcases-006)",
        applicability="not applicable: this differential uses a single "
                     "semihosting output channel and compares bytes only",
        note="SE dual-fd output capture loses fd1/fd2 order"),
    "ISS-373": dict(
        status="open",
        applicability="run identity: the engine fingerprint below is the "
                     "binary actually executed (the build tree), not the "
                     "installed root",
        note="shared install root may diverge from the build tree (m13-qemu-014: "
             "installed-root qemu is still the pre-fix build); a differential "
             "must pin the executed binary instead of assuming they agree"),
    "m13-testcases-037": dict(
        status="landed",
        applicability="vector surface: the sc reservation-granularity vectors "
                     "are part of the input commit (m13-testcases-037 verified); "
                     "reservation paths that the carrier framework cannot "
                     "observe stay GAP and are tracked in issues.yaml "
                     "(ISS-440 / ISS-443)",
        note="sc/sys reservation granularity (exact address + width) formal "
             "vectors; the unobservable reservation paths are not written as "
             "expectations anywhere"),
}


# ---------------------------------------------------------------------------
# 静态真源
# ---------------------------------------------------------------------------
def load_opcodes(path: Path) -> list[dict]:
    doc = fp._load_yaml(path)
    if not isinstance(doc, list):
        raise SetupError(f"{path}: opcodes.yaml is not a list")
    ids = [r.get("id") for r in doc if isinstance(r, dict)]
    if len(ids) != len(set(ids)):
        raise SetupError(f"{path}: duplicate opcode ids")
    return doc


def spec_chapters(spec_dir: Path) -> dict[str, Path]:
    """`SimRISC-NN` -> 章节文件（现场 glob，不写死文件名）。"""
    out = {}
    for path in sorted(spec_dir.glob("SimRISC-*.md")):
        m = re.match(r"SimRISC-(\d{2})", path.name)
        if m:
            out[m.group(1)] = path
    if not out:
        raise SetupError(f"{spec_dir}: no SimRISC-NN chapter")
    return out


def spec_mnemonics(text: str) -> set[str]:
    """章节里以表格首列形式出现的助记符（`| `mnem` | …`）。"""
    return set(re.findall(r"^\|\s*`([^`|]+)`\s*\|", text, re.M))


def resolve_cite(cite: str, chapters: dict[str, Path],
                 cache: dict[str, dict]) -> dict:
    """把 `SimRISC-NN: mnem` 解析成「章节存在且章内有该助记符」。"""
    m = re.match(r"^(SimRISC-\d{2}):\s*(\S+)$", (cite or "").strip())
    if not m:
        return dict(chapter=None, mnemonic=None, form="bad_cite")
    chapter, mnem = m.group(1), m.group(2)
    path = chapters.get(chapter[8:])
    if path is None:
        return dict(chapter=chapter, mnemonic=mnem, form="chapter_missing")
    if chapter not in cache:
        text = path.read_text(encoding="utf-8")
        cache[chapter] = dict(rows=spec_mnemonics(text), text=text)
    info = cache[chapter]
    if mnem in info["rows"]:
        form = "table"
    elif re.search(r"`%s`" % re.escape(mnem), info["text"]):
        form = "prose"
    else:
        form = "not_in_chapter"
    return dict(chapter=chapter, mnemonic=mnem, form=form)


def non_id_cite(src: Path) -> dict:
    """非 id 载体：从文件头取 spec 出处（`spec/SimRISC-NN … §x`），不臆造。"""
    head = "\n".join(src.read_text(encoding="utf-8").splitlines()[:40])
    m = re.search(r"spec/(SimRISC-(\d{2}))[^\n]*?§([0-9.]+)", head)
    if not m:
        return dict(cite=None, chapter=None, section=None)
    return dict(cite=f"{m.group(1)}: §{m.group(3)}", chapter=m.group(1),
                section=m.group(3))


# ---------------------------------------------------------------------------
# 覆盖（现场枚举 + 逐 id 语义出处）
# ---------------------------------------------------------------------------
def build_coverage(opcodes, index, tests_root: Path,
                   spec_dir: Path) -> dict:
    chapters = spec_chapters(spec_dir)
    cache: dict[str, dict] = {}
    fp_ids = {r["id"] for r in opcodes if r.get("scope") == "fp"}
    by_id = {r["id"]: r for r in opcodes}

    carriers = {}
    for path in sorted(tests_root.glob("inst/**/*.S")):
        carriers.setdefault(path.stem, []).append(path)
    if not carriers:
        raise SetupError(f"{tests_root}: no .S carrier under inst/")

    rows = []
    gaps = []
    excluded = dict(fp=[], cfx=[])
    by_book: dict[str, dict] = {}
    for stem, paths in sorted(carriers.items()):
        if len(paths) > 1:
            raise DiffError(f"{stem}: multiple .S carriers: {paths}")
        src = paths[0]
        rel_book = src.parent.name
        m = BOOK_RE.match(rel_book)
        if not m:
            raise DiffError(f"{src}: book {rel_book!r} is not NN-name")
        book_no, book_name = m.groups()
        if rel_book == CFX_BOOK:
            excluded["cfx"].append(dict(id=stem, book=rel_book,
                                        reason="cfx 归 CFX 专项，不属本任务"))
            continue
        if stem in fp_ids:
            excluded["fp"].append(
                dict(id=stem, book=rel_book,
                     reason="contracts/opcodes.yaml scope: fp（归 "
                            "m13-integ-002）"))
            continue
        entry = by_id.get(stem)
        scan = asm.scan_source(src)
        fam = by_book.setdefault(rel_book, dict(
            book=rel_book, chapter=f"SimRISC-{book_no}",
            spec="spec/" + chapters[book_no].name
            if book_no in chapters else None,
            ids=0, carriers=0, chain_points=0, fault_cases=0, images=0,
            cite_ok=0, cite_gap=0))
        fam["carriers"] += 1
        fam["ids"] += 1 if entry else 0
        fam["chain_points"] += scan["checks"]
        fam["fault_cases"] += len(scan["faults"])
        images = (1 if scan["checks"] else 0) + len(scan["faults"])
        fam["images"] += images
        row = dict(id=stem, mnemonic=entry["mnemonic"] if entry else None,
                   scope=entry.get("scope") if entry else None,
                   book=rel_book, family=book_name,
                   carrier="tests/" + src.relative_to(tests_root).as_posix(),
                   chain_points=scan["checks"],
                   fault_cases=len(scan["faults"]), images=images,
                   pts_ok=scan["pts_ok"])
        if entry is None:
            cite = non_id_cite(src)
            row["semantic_basis"] = dict(kind="non_id", **cite)
            if cite["chapter"] is None:
                gaps.append(dict(id=stem, kind="spec_ambiguity",
                                 detail="非 id 载体的文件头里没有 spec 出处"))
                fam["cite_gap"] += 1
            else:
                fam["cite_ok"] += 1
        else:
            cite = resolve_cite(entry.get("spec_cite", ""), chapters, cache)
            row["semantic_basis"] = dict(kind="opcode", **cite,
                                         spec_cite=entry.get("spec_cite"))
            if cite["form"] in ("table", "prose"):
                fam["cite_ok"] += 1
            else:
                fam["cite_gap"] += 1
                gaps.append(dict(
                    id=stem, kind="spec_ambiguity",
                    detail=f"spec_cite {entry.get('spec_cite')!r} -> "
                           f"{cite['form']}"))
        if not scan["pts_ok"]:
            gaps.append(dict(id=stem, kind="points_not_contiguous",
                             detail="检查点号不是 1..N 连续"))
        rel = src.relative_to(tests_root).as_posix()
        hits = index.get(rel, [])
        row["indexed"] = bool(hits)
        row["index_ids"] = sorted(h["id"] for h in hits)
        if not hits:
            gaps.append(dict(id=stem, kind="not_indexed",
                             detail=f"{rel} missing from tests/inst.yaml"))
        rows.append(row)

    cfx_ids = {e["id"] for e in excluded["cfx"]}
    non_fp = {r["id"] for r in opcodes if r.get("scope") != "fp"} - cfx_ids
    missing = sorted(non_fp - {r["id"] for r in rows})
    for oid in missing:
        gaps.append(dict(id=oid, kind="no_carrier",
                         detail=by_id[oid].get("spec_cite", "")))
    carriers_total = len(carriers)
    for fam in by_book.values():
        if fam["spec"] is None:
            gaps.append(dict(id=fam["book"], kind="spec_chapter_missing",
                             detail=f"{fam['chapter']} 无章节文件"))
    return dict(
        carriers_total=carriers_total,
        total=len(rows),
        with_index=sum(1 for r in rows if r["indexed"]),
        images=sum(r["images"] for r in rows),
        chain_images=sum(1 for r in rows if r["chain_points"]),
        fault_images=sum(r["fault_cases"] for r in rows),
        ids_with_opcode=sum(1 for r in rows if r["id"] in by_id),
        non_id=[dict(id=r["id"], carrier=r["carrier"])
                for r in rows if r["id"] not in by_id],
        excluded=excluded,
        gaps=gaps,
        families=[dict(by_book[b], **dict(
            images=r["images"], ids=r["ids"], carriers=r["carriers"],
            chain_points=r["chain_points"], fault_cases=r["fault_cases"],
            cite_ok=r["cite_ok"], cite_gap=r["cite_gap"]))
            for b, r in sorted(by_book.items())],
        rows=rows)


# ---------------------------------------------------------------------------
# 分析
# ---------------------------------------------------------------------------
def attribute(rec) -> dict | None:
    key = (Path(rec["file"]).stem, rec["case_n"])
    entry = ATTRIBUTIONS.get(key) or EXTERNAL_ATTRIBUTIONS.get(key)
    if entry is None or entry.get("owner") not in OWNERS:
        return None
    return dict(entry)


def load_attributions(path: Path, chapters: dict[str, Path]) -> dict:
    """外部归因表（JSON）: {"<id>#<case_n>": {...}}；逐条校验，不静默放过。

    归因表是**显式输入**（与 `fp_diff` 的代码内表同语义），每条必须给
    `owner`（∈ OWNERS）、`spec_cite`（必须解析到现存章节）与可选 `issue`。
    未列出的差异仍然 rc=1 —— 表只允许逐条申报，不允许「全放行」。
    """
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SetupError(f"{path}: {exc}")
    if not isinstance(doc, dict) or not doc:
        raise SetupError(f"{path}: attribution table must be a non-empty object")
    cache: dict[str, dict] = {}
    out = {}
    for key, entry in doc.items():
        m = re.fullmatch(r"(.+)#(\d+)", key)
        if not m:
            raise SetupError(f"{path}: key {key!r} must be <id>#<case_n>")
        if not isinstance(entry, dict):
            raise SetupError(f"{path}: {key}: entry must be an object")
        owner = entry.get("owner")
        if owner not in OWNERS:
            raise SetupError(f"{path}: {key}: owner {owner!r} not in {OWNERS}")
        cite = entry.get("spec_cite", "")
        resolved = resolve_cite(cite, chapters, cache)
        if resolved["form"] not in ("table", "prose"):
            raise SetupError(f"{path}: {key}: spec_cite {cite!r} -> "
                             f"{resolved['form']}")
        out[(m.group(1), int(m.group(2)))] = dict(
            owner=owner, spec_cite=cite, issue=entry.get("issue"),
            note=entry.get("note"))
    return out


def point_analysis(rec, work_root: Path) -> list[dict]:
    """链例镜像：按检查点切 8 字节，找出三平台不一致的点。"""
    blobs = {p: fp._read_out(work_root, Path(rec["file"]).stem, p, rec["case_n"])
             for p in PLATFORMS}
    out = []
    npoints = rec["expected"]
    for k in range(1, npoints + 1):
        chunk = {}
        for plat in PLATFORMS:
            rc = rec["platforms"][plat]["rc"]
            reached = rc == 0 or rc > k
            data = blobs[plat][8 * (k - 1):8 * k]
            chunk[plat] = dict(reached=reached,
                               record=data.hex() if len(data) == 8 else None)
        present = [chunk[p]["record"] for p in PLATFORMS]
        agree = (all(chunk[p]["reached"] for p in PLATFORMS)
                 and all(v is not None for v in present)
                 and len(set(present)) == 1)
        out.append(dict(point=k, agree=agree, platforms=chunk))
    return out


def analyse(coverage, records):
    errors = []
    by_id = {r["id"]: r for r in coverage["rows"]}
    images, diffs, agree_fail = [], [], []
    for rec in sorted(records, key=lambda r: (Path(r["file"]).stem, r["case_n"])):
        oid = Path(rec["file"]).stem
        if oid not in by_id:
            errors.append(f"run record for id {oid} not in coverage")
            continue
        verdict = fp.classify(rec)
        images.append(dict(
            id=oid, case_n=rec["case_n"], kind=rec["kind"],
            expected=rec.get("expected"), verdict=verdict,
            platforms={p: dict(
                status="PASS" if rec["platforms"][p]["rc"] == 0 else "FAIL",
                exit=rec["platforms"][p]["rc"],
                bytes=rec["platforms"][p].get("bytes"),
                md5=fp._md5(fp._read_out(rec["_work"], oid, p, rec["case_n"])))
                for p in PLATFORMS},
            notes=rec.get("notes") or []))
        if verdict == "AGREE_FAIL":
            agree_fail.append(dict(id=oid, case_n=rec["case_n"],
                                   kind=rec["kind"],
                                   expected=rec.get("expected"),
                                   exits={p: rec["platforms"][p]["rc"]
                                          for p in PLATFORMS}))
        if verdict == "DIFF":
            points = []
            if rec["kind"] == "chain":
                points = [p for p in point_analysis(rec, rec["_work"])
                          if not p["agree"]]
            attr = attribute(rec)
            diffs.append(dict(
                id=oid, case_n=rec["case_n"], kind=rec["kind"],
                expected=rec.get("expected"),
                observed={p: dict(rc=rec["platforms"][p]["rc"],
                                  bytes=rec["platforms"][p].get("bytes"))
                          for p in PLATFORMS},
                points=points, attribution=attr))
    for d in diffs:
        if d["attribution"] is None:
            errors.append(f"{d['id']}#{d['case_n']}: DIFF without an "
                          f"attribution entry")
    for gap in coverage["gaps"]:
        if gap["kind"] in ("no_carrier", "points_not_contiguous",
                           "spec_chapter_missing"):
            errors.append(f"coverage gap {gap['id']}: {gap['kind']} -- "
                          f"{gap['detail']}")
    # 每个载体声明的镜像数必须与实际跑到的记录数一致（缺镜像不得静默）
    per_id = {}
    for rec in records:
        oid = Path(rec["file"]).stem
        per_id[oid] = per_id.get(oid, 0) + 1
    for row in coverage["rows"]:
        got = per_id.get(row["id"], 0)
        if got != row["images"]:
            errors.append(f"{row['id']}: {got} run record(s) but "
                          f"{row['images']} image(s) declared by the carrier")
    return images, diffs, agree_fail, errors


def platform_completion(coverage, records):
    """逐平台完成数：分母 = 现场枚举的镜像数；分子 = 带该平台记录且 rc 为整数。

    未跑项按 **id** 归集（同一 id 的任一镜像缺平台即记该 id），便于逐条给原因。
    """
    expected = coverage["images"]
    done = {p: 0 for p in PLATFORMS}
    covered = {}
    for rec in records:
        oid = Path(rec["file"]).stem
        covered.setdefault(oid, set())
        for p in PLATFORMS:
            if isinstance((rec.get("platforms") or {}).get(p, {}).get("rc"), int):
                done[p] += 1
                covered[oid].add(p)
    not_run = [dict(id=oid, missing=sorted(set(PLATFORMS) - got))
               for oid, got in sorted(covered.items()) if len(got) != len(PLATFORMS)]
    return dict(expected_images=expected, completed=done,
                missing={p: expected - done[p] for p in PLATFORMS},
                not_run_ids=not_run)


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------
#: 输入 commit 解析 = `fp_diff.resolve_input_commit`（同一守卫，不复制一份）。
resolve_input_commit = fp.resolve_input_commit


def build_report(coverage, images, diffs, agree_fail, completion, engines,
                 sources, errors, input_commit=None):
    results = dict(
        images=len(images),
        agree_pass=sum(1 for i in images if i["verdict"] == "AGREE_PASS"),
        agree_fail=len(agree_fail),
        diff=len(diffs),
        by_id={row["id"]: dict(
            images=sum(1 for i in images if i["id"] == row["id"]),
            chain=sum(1 for i in images
                      if i["id"] == row["id"] and i["kind"] == "chain"),
            fault=sum(1 for i in images
                      if i["id"] == row["id"] and i["kind"] == "fault"),
            agree_pass=sum(1 for i in images
                           if i["id"] == row["id"]
                           and i["verdict"] == "AGREE_PASS"))
            for row in coverage["rows"]},
        per_image=images)
    return dict(
        schema=SCHEMA, task=TASK,
        input_commit=input_commit,
        scope="non-cfx, non-fp tests/inst .S carriers (integer / memory / "
              "control flow / bit ops / atomics / misc); same ELF per image on "
              "chipyard Tiny, qemu system and gem5 FS; per-checkpoint 8-byte "
              "result records and fault exit codes",
        engines=engines, sources=sources, coverage=coverage,
        attribution_source=("external" if EXTERNAL_ATTRIBUTIONS else "none"),
        results=results,
        completion=completion,
        differences=dict(attributed=[d for d in diffs
                                     if d["attribution"] is not None],
                         unattributed=[d for d in diffs
                                       if d["attribution"] is None]),
        agree_fail=agree_fail,
        known_items=KNOWN_ITEMS,
        checks=dict(ok=not errors, errors=errors))


def render_markdown(report) -> str:
    add = []
    cov = report["coverage"]
    res = report["results"]
    comp = report["completion"]
    add.append("# m13-integ-003: 整数与访存三平台逐例差分（qemu / gem5 / chipyard）")
    add.append("")
    add.append("> 由 `tools/testcases/parity/int_diff.py` 从已入库输入确定性重建；"
               "不写生成时刻、不写运行期路径。")
    add.append("")
    add.append("## 0. 口径与分母（现场统计）")
    add.append("")
    ex = cov["excluded"]
    add.append(f"- `tests/inst` 的 `.S` 载体**总数 {cov['carriers_total']}**"
               "（现场枚举，不写死）")
    add.append(f"- 排除 FP：**{len(ex['fp'])}** 条 `scope: fp` 载体"
               "（`contracts/opcodes.yaml`；其中 "
               f"{sum(1 for e in ex['fp'] if e['book'].startswith('07'))} 条在 "
               "`07-floating-point`，其余散落在 01/02/03 册）——归 `m13-integ-002`")
    add.append(f"- 排除 cfx：**{len(ex['cfx'])}** 条（册 `11-cfx`）——归 CFX 专项")
    non_id = cov["non_id"]
    add.append(f"- 非 id 载体：**{len(non_id)}** 条"
               + ("：" + "，".join(f"`{e['id']}`" for e in non_id)
                  + "（保留编码 ⇒ UNDI；以自身文件头的 spec 出处计）"
                  if non_id else ""))
    add.append(f"- 本报告分母：**{cov['total']}** 个载体（其中 "
               f"{cov['ids_with_opcode']} 个有 opcode id）/ **{cov['images']}** "
               f"个镜像（链例 {cov['chain_images']}，故障例 {cov['fault_images']}）")
    add.append(f"- 三平台完成数：分母 {comp['expected_images']}；"
               + " / ".join(f"{p} {comp['completed'][p]}" for p in PLATFORMS)
               + "；缺失 "
               + ", ".join(f"{p}={comp['missing'][p]}" for p in PLATFORMS))
    add.append("")
    add.append("## 1. 语义依据出处（每族：spec 章节 + contract）")
    add.append("")
    add.append("族 = `.S` 载体所在册；册号直接对应 `spec/SimRISC-NN-*` 章节号；"
               "逐 id 的 `spec_cite`（`contracts/opcodes.yaml`）解析到该章节，"
               "并在章内核对助记符。人读契约正文统一指 "
               "`.tao/contracts/contract-isa.md`（FP 段归 `contract-fp.md`，不在范围）。")
    add.append("")
    add.append("| 族（册） | spec 章节 | id 数 | 载体 | 链例点 | 故障例 | 镜像 "
               "| spec_cite 可解析 | 缺口 |")
    add.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for fam in cov["families"]:
        add.append(f"| `{fam['book']}` | `{fam['spec'] or fam['chapter']}` | "
                   f"{fam['ids']} | {fam['carriers']} | {fam['chain_points']} | "
                   f"{fam['fault_cases']} | {fam['images']} | {fam['cite_ok']} | "
                   f"{fam['cite_gap']} |")
    amb = [g for g in cov["gaps"] if g["kind"] == "spec_ambiguity"]
    add.append("")
    add.append(f"### 语义出处缺口（{len(amb)}）")
    add.append("")
    if amb:
        for gap in amb:
            add.append(f"- `{gap['id']}` — {gap['detail']}")
        add.append("")
        add.append("> 缺出处按「spec 歧义」单列（待裁定），不臆造期望值。")
    else:
        add.append("(none) — 每条载体的 `spec_cite` 都能解析到现存章节且章内"
                   "有该助记符；非 id 载体取自身文件头出处。")
    add.append("")
    add.append("## 2. 三平台逐例结果")
    add.append("")
    add.append(f"- 镜像 **{res['images']}**；三方一致通过 "
               f"**{res['agree_pass']}**；三方一致非通过 **{res['agree_fail']}**；"
               f"平台差异 **{res['diff']}**。")
    add.append("")
    add.append("| id | 链例/故障 | 观测 | 归因 |")
    add.append("| --- | --- | --- | --- |")
    for d in report["differences"]["attributed"]:
        obs = ", ".join(f"{p}=rc{d['observed'][p]['rc']}" for p in PLATFORMS)
        a = d["attribution"]
        add.append(f"| `{d['id']}#{d['case_n']}` | {d['kind']} | {obs} | "
                   f"{a['owner']} / {a.get('issue') or '—'} / "
                   f"`{a.get('spec_cite', '')}` |")
    for d in report["differences"]["unattributed"]:
        obs = ", ".join(f"{p}=rc{d['observed'][p]['rc']}" for p in PLATFORMS)
        add.append(f"| `{d['id']}#{d['case_n']}` | {d['kind']} | {obs} | "
                   "**UNATTRIBUTED** |")
    if not report["differences"]["attributed"] and \
            not report["differences"]["unattributed"]:
        add.append("| — | — | 无平台差异 | — |")
    add.append("")
    if report["agree_fail"]:
        add.append("### 三方一致但非通过（语义/测试资产问题，不算平台差异）")
        add.append("")
        for item in report["agree_fail"]:
            add.append(f"- `{item['id']}#{item['case_n']}` ({item['kind']}, "
                       f"expected {item['expected']}): "
                       + ", ".join(f"{p}=rc{rc}"
                                   for p, rc in item["exits"].items()))
        add.append("")
    diff_points = [d for d in (report["differences"]["attributed"]
                               + report["differences"]["unattributed"])
                   if d["points"]]
    if diff_points:
        add.append("### 差异检查点")
        add.append("")
        for d in diff_points:
            first = d["points"][0]["point"]
            add.append(f"- `{d['id']}#{d['case_n']}`：{len(d['points'])} 个不一致"
                       f"检查点，首个 = {first}（逐点三平台 8 字节记录见 JSON）")
        add.append("")
    add.append("### 逐 id 聚合（链例/故障镜像数、三方一致通过数）")
    add.append("")
    add.append("| id | 族 | 语义出处 | 镜像 | 链例 | 故障 | 一致通过 |")
    add.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in cov["rows"]:
        agg = res["by_id"][row["id"]]
        basis = row["semantic_basis"]
        cite = basis.get("spec_cite") or basis.get("cite") or "—"
        add.append(f"| `{row['id']}` | {row['family']} | `{cite}` | "
                   f"{agg['images']} | {agg['chain']} | {agg['fault']} | "
                   f"{agg['agree_pass']} |")
    add.append("")
    add.append("> 逐镜像的三平台 `exit` / 结果字节流 md5 在配套 JSON 的 "
               "`results.per_image`（每条记录即一份状态文件摘要）。")
    add.append("")
    add.append("## 3. 覆盖缺口与未跑项")
    add.append("")
    other = [g for g in cov["gaps"] if g["kind"] != "spec_ambiguity"]
    add.append(f"- 覆盖缺口（非语义类）：**{len(other)}**")
    for gap in other:
        add.append(f"  - `{gap['id']}` — {gap['kind']}：{gap['detail']}")
    add.append(f"- 未在三平台跑的 id：**{len(comp['not_run_ids'])}**")
    if comp["not_run_ids"]:
        for item in comp["not_run_ids"]:
            add.append(f"  - `{item['id']}`：缺 {', '.join(item['missing'])}")
    else:
        add.append("  - (none) — 本任务范围内全部载体都是单 hart 可执行例"
                   "（chipyard `WumingTinyConfig` 单 hart）；多 hart 原子语义"
                   "无观测载体，记 GAP 不造用例（`m13-chipyard-002` GAP 同口径）")
    add.append("")
    add.append("## 4. 已知项（单列，不混入平台差异）")
    add.append("")
    for key, item in report["known_items"].items():
        add.append(f"- `{key}`（{item['status']}）：{item['note']}"
                   f"（{item['applicability']}）")
    add.append("")
    add.append("## 5. 输入与可重算")
    add.append("")
    add.append(f"- 输入 commit（生成时 HEAD）：`{report.get('input_commit')}`"
               " —— 载体面与报告身份的时间锚；载体面变化后本报告陈旧")
    for key in ("opcodes", "inst_index", "contract_isa"):
        src = report["sources"][key]
        add.append(f"- `{src['path']}` sha256 `{src['sha256'][:16]}`")
    for item in report["sources"]["specs"]:
        add.append(f"- `{item['path']}` sha256 `{item['sha256'][:16]}`")
    for item in report["sources"]["runs"]:
        add.append(f"- run `{item['label']}`：{item['records']} 条记录 "
                   f"sha256 `{item['sha256'][:16]}`")
    eng = report["engines"]
    if eng:
        add.append("")
        add.append("引擎指纹（md5，报告身份）：")
        for plat in PLATFORMS:
            if plat in eng:
                add.append(f"- {plat}: `{eng[plat]}`")
    add.append("")
    add.append("## 6. 判据")
    add.append("")
    if report["checks"]["ok"]:
        add.append("- 每个非 `AGREE_PASS` 差异均已归因；语义出处/覆盖/索引缺口"
                   "逐条列出；平台完成数与现场枚举分母一致")
    else:
        for err in report["checks"]["errors"]:
            add.append(f"- FAIL: {err}")
    add.append("")
    return "\n".join(add) + "\n"


# ---------------------------------------------------------------------------
# 自检：每类不变式一条注入，必须都被判出
# ---------------------------------------------------------------------------
def self_test() -> int:
    checks = []

    def expect(name, fn):
        try:
            fn()
        except (DiffError, SetupError) as exc:
            checks.append((name, True, type(exc).__name__))
        else:
            checks.append((name, False, "not detected"))

    def run_record(payload, known, checks_by_id):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as fh:
            json.dump(dict(schema="inst-asm-suite/1", records=[payload]), fh)
            name = fh.name
        try:
            fp.load_run("synthetic", Path(name), known, checks_by_id)
        finally:
            Path(name).unlink()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "inst" / "01-load-store").mkdir(parents=True)
        (root / "spec").mkdir()
        (root / "spec" / "SimRISC-01-取数存数.md").write_text(
            "| `ld.ub` | x |\n", encoding="utf-8")
        good = root / "inst" / "01-load-store" / "ld.ub_rrii_rd.S"
        good.write_text("\tTEST_LD\t1, ld.ub, rf5, rf6, 0x0\n"
                        "\tTEST_LD\t2, ld.ub, rf5, rf6, 0x0\n", encoding="utf-8")
        bad = root / "inst" / "01-load-store" / "ld.uw_rrii_rd.S"
        bad.write_text("\tTEST_LD\t1, ld.uw, rf5, rf6, 0x0\n"
                       "\tTEST_LD\t3, ld.uw, rf5, rf6, 0x0\n", encoding="utf-8")
        cfx = root / "inst" / "11-cfx"
        cfx.mkdir()
        (cfx / "trap_ciii_cfx.S").write_text("\tTEST_CS\t1, trap\n",
                                             encoding="utf-8")
        ops = [dict(id="ld.ub_rrii_rd", mnemonic="ld.ub", scope="m1",
                    spec_cite="SimRISC-01: ld.ub"),
               dict(id="ld.uw_rrii_rd", mnemonic="ld.uw", scope="m1",
                    spec_cite="SimRISC-01: ld.uw"),
               dict(id="trap_ciii_cfx", mnemonic="trap", scope="m1",
                    spec_cite="SimRISC-11: trap")]
        out = build_coverage(
            ops, {"inst/01-load-store/ld.ub_rrii_rd.S": [dict(id="t1")]},
            root, root / "spec")
        if not [g for g in out["gaps"] if g["kind"] == "points_not_contiguous"]:
            checks.append(("non-contiguous points rejected", False, "no gap"))
        else:
            checks.append(("non-contiguous points rejected", True,
                           "points_not_contiguous"))
        if not [g for g in out["gaps"] if g["kind"] == "not_indexed"]:
            checks.append(("index gap detected", False, "no gap"))
        else:
            checks.append(("index gap detected", True, "not_indexed"))
        if any(r["id"] == "trap_ciii_cfx" for r in out["rows"]):
            checks.append(("cfx not in scope", False, "trap_ciii_cfx in rows"))
        else:
            checks.append(("cfx not in scope", True, "excluded"))
        if len(out["excluded"]["cfx"]) != 1:
            checks.append(("cfx counted as excluded", False,
                           out["excluded"]))
        else:
            checks.append(("cfx counted as excluded", True, "1"))
        amb = [g for g in out["gaps"] if g["kind"] == "spec_ambiguity"]
        if len(amb) != 1 or "not_in_chapter" not in amb[0]["detail"]:
            checks.append(("unresolvable spec_cite flagged", False, amb))
        else:
            checks.append(("unresolvable spec_cite flagged", True,
                           "ld.uw not_in_chapter"))

    expect("unknown id in run record", lambda: run_record(
        dict(file="not_an_id.S", case_n=0, kind="chain", expected=1, ok=True,
             platforms={p: dict(rc=0) for p in PLATFORMS}),
        {"ld.ub_rrii_rd"}, {"ld.ub_rrii_rd": 1}))
    expect("missing platform", lambda: run_record(
        dict(file="ld.ub_rrii_rd.S", case_n=0, kind="chain", expected=1,
             ok=True, platforms={"qemu": dict(rc=0)}),
        {"ld.ub_rrii_rd"}, {"ld.ub_rrii_rd": 1}))
    expect("ok flag contradicts records", lambda: run_record(
        dict(file="ld.ub_rrii_rd.S", case_n=0, kind="chain", expected=1,
             ok=True, platforms={"qemu": dict(rc=0, bytes=8),
                                 "gem5": dict(rc=3, bytes=8),
                                 "chipyard": dict(rc=0, bytes=8)}),
        {"ld.ub_rrii_rd"}, {"ld.ub_rrii_rd": 1}))

    fake = dict(file="ld.ub_rrii_rd.S", case_n=0, kind="chain", expected=1,
                ok=False, platforms={"qemu": dict(rc=0), "gem5": dict(rc=3),
                                     "chipyard": dict(rc=0)})
    checks.append(("platform split detected",
                   fp.classify(fake) == "DIFF", fp.classify(fake)))
    checks.append(("unattributed DIFF rejected", attribute(fake) is None,
                   "no entry"))

    bad = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"int_diff self-test: {len(checks) - len(bad)}/{len(checks)} "
          f"{'PASS' if not bad else 'FAIL'}")
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build(args) -> tuple[dict, str]:
    opcodes_path = Path(args.opcodes)
    if not opcodes_path.is_file():
        raise SetupError(f"{opcodes_path} not found")
    spec_dir = Path(args.spec_dir)
    if not spec_dir.is_dir():
        raise SetupError(f"{spec_dir} not found")
    index_path = Path(args.inst_index)
    tests_root = Path(args.tests_root)
    if not tests_root.is_dir():
        raise SetupError(f"{tests_root} not found")
    opcodes = load_opcodes(opcodes_path)
    index = fp.load_index(index_path)
    chapters = spec_chapters(spec_dir)
    coverage = build_coverage(opcodes, index, tests_root, spec_dir)
    EXTERNAL_ATTRIBUTIONS.clear()
    if args.attribution:
        EXTERNAL_ATTRIBUTIONS.update(load_attributions(
            Path(args.attribution), chapters))

    runs = fp._parse_kv(args.run, "run")
    works = fp._parse_kv(args.work, "work")
    if set(runs) != set(works):
        raise SetupError("--run and --work labels must match")
    known_ids = {r["id"] for r in coverage["rows"]}
    checks_by_id = {r["id"]: r["chain_points"] for r in coverage["rows"]}
    items = [(label, Path(runs[label]), known_ids, checks_by_id)
             for label in sorted(runs)]
    records = fp.merge_runs(items)
    for rec in records:
        rec["_work"] = Path(works[rec["_label"]])

    run_ids = {Path(r["file"]).stem for r in records}
    errors = []
    for row in coverage["rows"]:
        if row["id"] not in run_ids:
            errors.append(f"{row['id']}: no three-platform run record")
    images, diffs, agree_fail, survey_errors = analyse(coverage, records)
    errors = survey_errors + errors + fp.chain_byte_errors(records)
    completion = platform_completion(coverage, records)

    used = {fam["chapter"] for fam in coverage["families"]}
    specs = [dict(path=fp._display(chapters[k]), sha256=fp._sha256(chapters[k]))
             for k in sorted(chapters) if "SimRISC-" + k in used]
    sources = dict(
        opcodes=dict(path=fp._display(opcodes_path),
                     sha256=fp._sha256(opcodes_path)),
        inst_index=dict(path=fp._display(index_path),
                        sha256=fp._sha256(index_path)),
        contract_isa=dict(path=fp._display(Path(args.contract)),
                          sha256=fp._sha256(Path(args.contract))),
        specs=specs,
        runs=[dict(label=label,
                   records=sum(1 for r in records if r["_label"] == label),
                   sha256=fp._sha256(Path(runs[label])))
              for label in sorted(runs)])
    engines = fp._parse_kv(args.engine, "engine")
    report = build_report(coverage, images, diffs, agree_fail, completion,
                          engines, sources, errors,
                          input_commit=resolve_input_commit(args.input_commit))
    return report, render_markdown(report)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opcodes", default="contracts/opcodes.yaml")
    ap.add_argument("--spec-dir", default="spec")
    ap.add_argument("--inst-index", default="tests/inst.yaml")
    ap.add_argument("--tests-root", default="tests")
    ap.add_argument("--contract", default=".tao/contracts/contract-isa.md")
    ap.add_argument("--run", action="append", default=None,
                    help="LABEL=<inst-asm-suite JSON>（可重复）")
    ap.add_argument("--work", action="append", default=None,
                    help="LABEL=<run_asm_suite work-dir>（与 --run 标签一一对应）")
    ap.add_argument("--engine", action="append", default=None,
                    help="PLATFORM=<md5>（可重复；报告身份）")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--markdown-out", default=None)
    ap.add_argument("--attribution", default=None,
                    help="逐条归因表 JSON（key=<id>#<case_n>；逐条校验 owner/"
                         "spec_cite）。不提供 ⇒ 任何平台差异都 rc=1")
    ap.add_argument("--check", default=None,
                    help="与落盘报告逐字节比对（.md 或 .json）")
    ap.add_argument("--input-commit", default=None,
                    help="报告记录/比较的输入 commit（缺省 `git rev-parse HEAD`）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    try:
        report, markdown = build(args)
    except SetupError as exc:
        print(f"int_diff: SETUP: {exc}", file=sys.stderr)
        return 2
    except DiffError as exc:
        print(f"int_diff: FAIL: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown, encoding="utf-8")

    if args.check:
        target = Path(args.check)
        if not target.is_file():
            print(f"int_diff: SETUP: {target} not found", file=sys.stderr)
            return 2
        want = payload if target.suffix == ".json" else markdown
        got = target.read_text(encoding="utf-8")
        if got != want:
            print(f"int_diff: FAIL: {target} differs from the regenerated "
                  f"report ({len(got)} vs {len(want)} bytes)", file=sys.stderr)
            return 1
        print(f"int_diff: check PASS ({target})")

    if not report["checks"]["ok"]:
        for err in report["checks"]["errors"]:
            print(f"int_diff: FAIL: {err}", file=sys.stderr)
        return 1
    print(f"int_diff: PASS ({report['coverage']['total']} carriers, "
          f"{report['results']['images']} images, "
          f"{report['results']['diff']} platform diff, "
          f"{len([g for g in report['coverage']['gaps'] if g['kind'] == 'spec_ambiguity'])} spec ambiguity)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
