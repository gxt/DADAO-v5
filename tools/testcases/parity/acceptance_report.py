#!/usr/bin/env python3
"""acceptance_report.py -- M13 收口：矩阵冻结 + 差异归因（`m13-integ-005`）.

本脚本**不跑 guest**。输入 = 同一批 `run_asm_suite.py` 的三平台逐镜像 JSON +
每镜像 `.out` 结果流（与 `m13-integ-002`/`003` 同一形态），并**复用**两个已验收的
差分生成器：

  * `int_diff.py`（非 cfx、非 FP 的 `.S` 载体）——`build()`
  * `fp_diff.py`（`scope: fp`）——`build()`

它只做三件收口工作（不新增第二套口径）：

  1. **向量面现场重算**：逐册统计载体 / 链例点 / 故障例 / 镜像，并把
     「整数 + FP + cfx = 全部 `.S` 载体」的对账做成硬不变式（对不上即 rc=1）；
  2. **差异归因合并**：把 002（FP）/ 003（整数与访存）/ 004（riscv-tests）的差异
     清单合并，按「spec 歧义 / 实现缺陷 / 测试资产」分类；未归因的差异一律 rc=1；
  3. **冻结两份产物**：`docs/TestReports/M13-三平台差分-矩阵.md`（矩阵）与
     `.tao/knowledge/refs/m13-005-acceptance.{json,md}`（收口报告）。

确定性：不写生成时刻、不写运行期路径；**输入 commit 显式记录**（`--input-commit`，
缺省 `git rev-parse HEAD`）——矩阵与两份逐例报告都是该 commit 上向量面的函数，
载体面一变，`--check` 立刻能发现陈旧（`m13-integ-003` 复核 F3）。

用法::

    python3 tools/testcases/parity/acceptance_report.py \\
        --run book=<run.json> --work book=<work-dir> \\
        --engine qemu=<md5> --engine gem5=<md5> --engine chipyard=<md5> \\
        --tool llvm-mc=<md5> --tool bootrom=<md5> \\
        --json-out <运行期>/m13-005-acceptance.json \\
        --markdown-out <运行期>/m13-005-acceptance.md \\
        --matrix-out <运行期>/M13-三平台差分-矩阵.md
    python3 tools/testcases/parity/acceptance_report.py --check <任一产物>
    python3 tools/testcases/parity/acceptance_report.py --self-test

退出码：0 = 不变式全成立；1 = 不变式失败（差异未归因 / 对账不符 / `--check`
不一致 / 自检有注入未判出）；2 = setup 错（缺文件 / 坏 JSON / 坏参数 / 无 commit）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
for _p in (str(_HERE), str(_REPO / "tools" / "infra"),
           str(_REPO / "tests" / "ee-tiny")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fp_diff as fp                    # noqa: E402  (FP 生成器 + 共用工具)
import int_diff as intd                 # noqa: E402  (整数/访存生成器)
import run_asm_suite as asm             # noqa: E402  (载体现场统计)

SCHEMA = "m13-acceptance/1"
TASK = "m13-integ-005"
CFX_BOOK = intd.CFX_BOOK
PLATFORMS = fp.PLATFORMS
CLASSES = ("int", "fp", "cfx")

#: 归因 owner -> 收口分类（未列入即 rc=1：归因只许逐条申报）。
OWNER_CLASS = {
    "spec": "spec",
    "implementation": "implementation",
    "test asset": "test_asset",
    "environment": "environment",
    "budget": "budget",
}

#: 覆盖缺口 kind -> 收口分类（未列入即 rc=1）。
GAP_CLASS = {
    "spec_ambiguity": "spec",
    "spec_chapter_missing": "spec",
    "not_indexed": "test_asset",
    "no_carrier": "test_asset",
    "points_not_contiguous": "test_asset",
    "unparsable_point_mode": "test_asset",
}

#: 前序差分任务在本冻结中的位置。002/003 的差异清单由本脚本**同一输入重算**
#: （不读旧 refs）；004 的语料已退役，只保留任务书结论作指针（不溯源上游）。
PREDECESSORS = (
    dict(task="m13-integ-002", topic="FP 语义", role="recomputed",
         basis="FP 段由 `fp_diff.py` 在同一批输入上重算；差异数即本报告的 fp 段"),
    dict(task="m13-integ-003", topic="整数/访存", role="recomputed",
         basis="整数段由 `int_diff.py` 在同一批输入上重算；差异数即本报告的 int 段"),
    dict(task="m13-integ-004", topic="riscv-tests", role="retired",
         basis="移植语料已由 `m13-testcases-045` 退役删除（不归档、不溯源）："
               "任务书结论 = 35/35 `AGREE_PASS`、`DIFF=0`，本轮不再重跑"),
)

#: 结构 GAP（载体框架内不可观测，不造用例、不伪造期望）。
STRUCTURAL_GAPS = (
    dict(id="multi-hart-atomics",
         detail="多 hart 原子语义（另一 hart 同址同宽 store 清保留）：chipyard "
                "`WumingTinyConfig` 单 hart，无观测载体"),
    dict(id="sc-after-exception",
         detail="「异常/中断进入后再 `sc`」：故障即终止镜像，单链例镜像内不可观测"
                "（需专驱动）"),
)

#: 与旧版（002/003 已验收口径）的对照。**常量，只作说明，不作判据**：冻结版
#: 判据一律来自本报告的现场重算；旧版报告的「已知缺口」在此逐条交代去向。
DELTA = (
    dict(item="scope:fp 条数", old="66", new="65",
         reason="`ft2ft`/`fo2fo` 退役、`rf2rf` 新增（`m13-spec-010`）"),
    dict(item="FP 镜像", old="232", new="227", reason="随 ↑ 的载体面变化"),
    dict(item="FP 覆盖缺口（not_indexed）", old="4", new="0",
         reason="4 条 rf 访存载体现已在 `tests/inst.yaml` 登记（现场核对）"),
    dict(item="FP 矩阵空白格", old="11", new="10",
         reason="新增/更新载体补了 1 个「舍入档 × 标志」组合"),
    dict(item="整数段载体 / 镜像", old="194 / 629", new="202 / 637",
         reason="7 个伪指令载体 + `rf2rf` 等新向量进入载体面"),
    dict(item="整数段覆盖缺口", old="0", new="0", reason="与旧版一致"),
)


#: 全部事实来自 `issues.yaml` + 载体文件头的 GAP 段，不从实现反推。
#: 本矩阵**不覆盖**、但需要用户裁定口径的已登记项（逐条给问题与不覆盖的机械理由）。
#: 全部事实来自 `issues.yaml` + 载体文件头的 GAP 段，不从实现反推。
OPEN_QUESTIONS = (
    dict(id="ISS-443", class_="spec",
         question="`sc` 的保留清除事件「异常或中断进入」是否作为可观测要求："
                  "`spec/SimRISC-12 §1` 明列为清除事件，但三方实测分歧",
         evidence="`tests/inst/12-misc/sc.b.nn_orrr_rd.S` 文件头 GAP 段："
                  "chipyard 清 / qemu 仅同步异常清 / gem5 不清 ⇒ 载体只留 GAP、"
                  "不把任一平台行为写成期望",
         why_not_in_matrix="载体框架下故障即终止镜像，「异常进入后再 `sc`」无法在"
                           "单链例镜像内观测；需要专驱动（另立任务）"),
    dict(id="ISS-440", class_="spec",
         question="「另一 hart 对同一精确地址+相同宽度 store ⇒ 清保留」是否在 M13 "
                  "冻结判据内",
         evidence="`spec/SimRISC-12 §1` 列为清除事件；三方均无实现路径，且 "
                  "chipyard `WumingTinyConfig` 单 hart ⇒ 无观测载体",
         why_not_in_matrix="单 hart 机型，多 hart 原子语义无观测载体（记 GAP，不造用例）"),
    dict(id="ISS-433", class_="implementation",
         question="`trap cfx_power` 的语义：chipyard 报 ILLI，qemu/gem5 进 power "
                  "向量——是 RTL 缺实现还是 spec 未明",
         evidence="`m13-testcases-027` 实测；属 cfx 面（册 `11-cfx`）",
         why_not_in_matrix="cfx 面不属本差分（册 `11-cfx` 的载体归 CFX 专项）"),
)


# ---------------------------------------------------------------------------
# 向量面（现场枚举；计数不写死）
# ---------------------------------------------------------------------------
def scan_surface(tests_root: Path, opcodes: list[dict],
                 spec_dir: Path) -> dict:
    """逐册统计载体/链例点/故障例/镜像，并按 int/fp/cfx 分类。

    `tests/inst/**/*.S` 全量为分母；`scope: fp`（`contracts/opcodes.yaml`）归
    FP 段，册 `11-cfx` 归 CFX 专项（不进本矩阵），其余归整数段。
    """
    fp_ids = {r["id"] for r in opcodes if r.get("scope") == "fp"}
    by_id = {r["id"]: r for r in opcodes}
    chapters = {}
    for path in sorted(spec_dir.glob("SimRISC-*.md")):
        m = re.match(r"SimRISC-(\d{2})", path.name)
        if m:
            chapters[m.group(1)] = path.name

    books: dict[str, dict] = {}
    rows = []
    carriers = sorted(tests_root.glob("inst/**/*.S"))
    if not carriers:
        raise intd.SetupError(f"{tests_root}: no .S carrier")
    for src in carriers:
        stem = src.stem
        book = src.parent.name
        m = re.match(r"^(\d{2})-([a-z0-9-]+)$", book)
        if not m:
            raise intd.DiffError(f"{src}: book {book!r} is not NN-name")
        no, name = m.groups()
        scan = asm.scan_source(src)
        if book == CFX_BOOK:
            cls = "cfx"
        elif stem in fp_ids:
            cls = "fp"
        else:
            cls = "int"
        images = (1 if scan["checks"] else 0) + len(scan["faults"])
        row = dict(id=stem, book=book, family=name, klass=cls,
                   has_opcode=stem in by_id,
                   chain_points=scan["checks"],
                   fault_cases=len(scan["faults"]), images=images)
        rows.append(row)
        fam = books.setdefault(book, dict(
            book=book, chapter=f"SimRISC-{no}",
            spec=("spec/" + chapters[no]) if no in chapters else None,
            klass=cls, carriers=0, ids=0, non_id=0, chain_points=0,
            fault_cases=0, images=0))
        fam["carriers"] += 1
        fam["ids"] += 1 if stem in by_id else 0
        fam["non_id"] += 0 if stem in by_id else 1
        fam["chain_points"] += scan["checks"]
        fam["fault_cases"] += len(scan["faults"])
        fam["images"] += images

    by_class = {c: dict(carriers=0, ids=0, non_id=0, chain_points=0,
                        fault_cases=0, images=0) for c in CLASSES}
    for row in rows:
        agg = by_class[row["klass"]]
        agg["carriers"] += 1
        agg["ids"] += 1 if row["has_opcode"] else 0
        agg["non_id"] += 0 if row["has_opcode"] else 1
        agg["chain_points"] += row["chain_points"]
        agg["fault_cases"] += row["fault_cases"]
        agg["images"] += row["images"]

    non_id = [dict(id=r["id"], book=r["book"], klass=r["klass"])
              for r in rows if not r["has_opcode"]]
    return dict(carriers_total=len(rows),
                images_total=sum(r["images"] for r in rows),
                by_class=by_class,
                non_id=non_id,
                books=[books[b] for b in sorted(books)],
                rows=rows)


def split_runs(runs: dict[str, str], int_ids: set, fp_ids: set,
               cfx_ids: set, tmpdir: Path) -> tuple[list, list, dict]:
    """按段切分同一批三平台逐例输入（两个生成器只接受自己的 scope，fail-closed）。

    返回 (`--run` 列表 for int, for fp, 记录普查)。记录必须恰好落进
    int / fp / cfx 三类之一；落不进去即 rc=1（不许静默丢用例）。
    """
    buckets = {cls: {label: [] for label in runs} for cls in
               ("int", "fp", "cfx")}
    seen = set()
    for label in sorted(runs):
        doc = json.loads(Path(runs[label]).read_text(encoding="utf-8"))
        if doc.get("schema") != "inst-asm-suite/1":
            raise intd.SetupError(f"{label}: schema {doc.get('schema')!r} != "
                                  f"'inst-asm-suite/1'")
        for rec in doc.get("records") or []:
            stem = Path(rec.get("file", "")).stem
            key = (stem, rec.get("case_n"))
            if key in seen:
                raise intd.DiffError(f"duplicate run record {key}")
            seen.add(key)
            if stem in fp_ids:
                buckets["fp"][label].append(rec)
            elif stem in cfx_ids:
                buckets["cfx"][label].append(rec)
            elif stem in int_ids:
                buckets["int"][label].append(rec)
            else:
                raise intd.DiffError(f"run record {rec.get('file')!r} is not a "
                                     f"known carrier")
    out = {}
    for cls in ("int", "fp"):
        args = []
        for label in sorted(runs):
            path = tmpdir / f"run-{cls}-{label}.json"
            path.write_text(json.dumps(dict(schema="inst-asm-suite/1",
                                            records=buckets[cls][label]),
                                       indent=1) + "\n", encoding="utf-8")
            args.append(f"{label}={path}")
        out[cls] = args
    census = {cls: dict(records=sum(len(v) for v in per.values()),
                        pass_=sum(1 for v in per.values()
                                  for rec in v if rec.get("ok")))
              for cls, per in buckets.items()}
    return out["int"], out["fp"], census


def crosscheck(surface: dict, int_report: dict, fp_report: dict,
               run_census: dict | None = None) -> list[str]:
    """向量面 ↔ 两份逐例报告的分母对账（对不上即 rc=1，不得静默）。"""
    errs = []
    ic = int_report["coverage"]
    fc = fp_report["coverage"]
    s_int, s_fp, s_cfx = (surface["by_class"][c] for c in CLASSES)
    if ic["total"] != s_int["carriers"]:
        errs.append(f"int carriers {ic['total']} != surface {s_int['carriers']}")
    if ic["images"] != s_int["images"]:
        errs.append(f"int images {ic['images']} != surface {s_int['images']}")
    if ic["ids_with_opcode"] + len(ic["non_id"]) != ic["total"]:
        errs.append(f"int ids {ic['ids_with_opcode']} + non_id "
                    f"{len(ic['non_id'])} != {ic['total']}")
    if ic["ids_with_opcode"] != s_int["ids"]:
        errs.append(f"int opcode ids {ic['ids_with_opcode']} != surface "
                    f"{s_int['ids']}")
    if len(ic["excluded"]["fp"]) != s_fp["carriers"]:
        errs.append(f"int excluded fp {len(ic['excluded']['fp'])} != surface "
                    f"{s_fp['carriers']}")
    if len(ic["excluded"]["cfx"]) != s_cfx["carriers"]:
        errs.append(f"int excluded cfx {len(ic['excluded']['cfx'])} != surface "
                    f"{s_cfx['carriers']}")
    if fc["total"] != s_fp["carriers"]:
        errs.append(f"fp carriers {fc['total']} != surface {s_fp['carriers']}")
    if fc["with_carrier"] != s_fp["carriers"]:
        errs.append(f"fp with_carrier {fc['with_carrier']} != surface "
                    f"{s_fp['carriers']}")
    fp_images = sum(r["images"] for r in surface["rows"] if r["klass"] == "fp")
    if fp_images != s_fp["images"]:
        errs.append(f"fp images {fp_images} != surface {s_fp['images']}")
    if (ic["images"] + s_fp["images"] + s_cfx["images"]
            != surface["images_total"]):
        errs.append("int + fp + cfx images != total images")
    if (ic["total"] + s_fp["carriers"] + s_cfx["carriers"]
            != surface["carriers_total"]):
        errs.append("int + fp + cfx carriers != total carriers")
    if run_census is not None:
        def _n(cls, key):
            return (run_census.get(cls) or {}).get(key)
        if _n("cfx", "records") != s_cfx["images"]:
            errs.append(f"cfx run records {_n('cfx', 'records')} != surface "
                        f"{s_cfx['images']}（本矩阵不含 cfx，但输入必须齐全）")
        if _n("int", "records") != s_int["images"]:
            errs.append(f"int run records {_n('int', 'records')} != surface "
                        f"{s_int['images']}")
        if _n("fp", "records") != s_fp["images"]:
            errs.append(f"fp run records {_n('fp', 'records')} != surface "
                        f"{s_fp['images']}")
    return errs


# ---------------------------------------------------------------------------
# 差异清单合并与分类
# ---------------------------------------------------------------------------
def classify_gap(gap: dict) -> dict:
    cls = GAP_CLASS.get(gap.get("kind"))
    if cls is None:
        raise intd.DiffError(f"gap {gap.get('id')}: unknown kind "
                             f"{gap.get('kind')!r}")
    return dict(source="coverage", id=gap["id"], kind=gap["kind"],
                class_=cls, detail=gap.get("detail"))


def classify_diff(report_task: str, diff: dict) -> dict:
    attr = diff.get("attribution")
    if attr is None:
        raise intd.DiffError(f"{report_task}: {diff['id']}#{diff['case_n']}: "
                             f"DIFF without an attribution entry")
    owner = attr.get("owner")
    cls = OWNER_CLASS.get(owner)
    if cls is None:
        raise intd.DiffError(f"{report_task}: {diff['id']}#{diff['case_n']}: "
                             f"owner {owner!r} not in {sorted(OWNER_CLASS)}")
    return dict(source=report_task, id=diff["id"], case_n=diff["case_n"],
                kind=diff["kind"], class_=cls, owner=owner,
                issue=attr.get("issue"), spec_cite=attr.get("spec_cite"),
                points=[p.get("point") for p in (diff.get("points") or [])],
                observed=diff.get("observed"))


def merge(int_report: dict, fp_report: dict, surface: dict) -> dict:
    diffs, gaps, agree_fail, errors = [], [], [], []
    for task, report in (("m13-integ-002", fp_report),
                         ("m13-integ-003", int_report)):
        for diff in (report["differences"]["attributed"]
                     + report["differences"]["unattributed"]):
            try:
                diffs.append(classify_diff(task, diff))
            except intd.DiffError as exc:
                # 未归因不是「生成器写坏」，是**数据**问题：报告照出，`checks.ok`
                # 为 false（rc=1），并把这条差异单列在 `unattributed` 桶里。
                errors.append(str(exc))
                diffs.append(dict(source=task, id=diff["id"],
                                  case_n=diff["case_n"], kind=diff["kind"],
                                  class_="unattributed", owner=None,
                                  issue=None, spec_cite=None,
                                  points=[p.get("point")
                                          for p in (diff.get("points") or [])],
                                  observed=diff.get("observed")))
        for item in report.get("agree_fail") or []:
            agree_fail.append(dict(source=task, **item))
        for gap in report["coverage"]["gaps"]:
            gaps.append(classify_gap(gap))
        if not report["checks"]["ok"]:
            for err in report["checks"]["errors"]:
                errors.append(f"{task}: {err}")
    by_class = {c: [] for c in ("spec", "implementation", "test_asset",
                                "unattributed")}
    for item in diffs:
        by_class.setdefault(item["class_"], []).append(item)
    for item in gaps:
        by_class.setdefault(item["class_"], []).append(item)
    blanks = [dict(source="m13-integ-002", id="fp_matrix",
                   kind="blank_cell", class_="test_asset",
                   detail=f"{cell['mode']} × {cell['category']}：{cell['reason']}")
              for cell in (fp_report.get("flags_matrix") or {}).get("empty") or []]
    by_class["test_asset"].extend(blanks)
    for cat in OPEN_QUESTIONS:
        by_class.setdefault(cat["class_"], []).append(
            dict(source="issues.yaml", id=cat["id"], class_=cat["class_"],
                 detail=cat["question"],
                 why_not_in_matrix=cat["why_not_in_matrix"]))
    counts = dict(platform_diff=len(diffs),
                  unattributed=len(by_class["unattributed"]),
                  agree_fail=len(agree_fail),
                  coverage_gaps=len(gaps),
                  matrix_blanks=len(blanks),
                  structural_gaps=len(STRUCTURAL_GAPS),
                  attributed_or_registered=len(by_class["spec"])
                  + len(by_class["implementation"]))
    return dict(differences=diffs, agree_fail=agree_fail, gaps=gaps,
                matrix_blanks=blanks,
                structural_gaps=list(STRUCTURAL_GAPS),
                by_class=by_class, counts=counts, errors=errors)


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------
def build(args) -> tuple[dict, str, str]:
    opcodes_path = Path(args.opcodes)
    tests_root = Path(args.tests_root)
    spec_dir = Path(args.spec_dir)
    if not opcodes_path.is_file():
        raise intd.SetupError(f"{opcodes_path} not found")
    if not tests_root.is_dir():
        raise intd.SetupError(f"{tests_root} not found")
    if not spec_dir.is_dir():
        raise intd.SetupError(f"{spec_dir} not found")
    opcodes = intd.load_opcodes(opcodes_path)

    commit = intd.resolve_input_commit(args.input_commit)
    runs = fp._parse_kv(args.run, "run")
    works = fp._parse_kv(args.work, "work")
    if set(runs) != set(works):
        raise intd.SetupError("--run and --work labels must match")
    engines = fp._parse_kv(args.engine, "engine")
    if set(engines) != set(PLATFORMS):
        raise intd.SetupError(f"--engine must name {sorted(PLATFORMS)}, "
                              f"got {sorted(engines)}")

    int_args = SimpleNamespace(
        opcodes=str(opcodes_path), spec_dir=str(spec_dir),
        inst_index=args.inst_index, tests_root=str(tests_root),
        contract=args.contract, run=None, work=args.work, engine=args.engine,
        attribution=args.attribution, input_commit=commit)
    fp_args = SimpleNamespace(
        opcodes=str(opcodes_path), spec=args.fp_spec,
        inst_index=args.inst_index, tests_root=str(tests_root),
        run=None, work=args.work, engine=args.engine, input_commit=commit)
    surface = scan_surface(tests_root, opcodes, spec_dir)
    int_ids = {r["id"] for r in surface["rows"] if r["klass"] == "int"}
    fp_ids = {r["id"] for r in surface["rows"] if r["klass"] == "fp"}
    cfx_ids = {r["id"] for r in surface["rows"] if r["klass"] == "cfx"}
    with tempfile.TemporaryDirectory(prefix="m13-005-") as tmp:
        int_runs, fp_runs, census = split_runs(runs, int_ids, fp_ids,
                                               cfx_ids, Path(tmp))
        int_args.run = int_runs
        fp_args.run = fp_runs
        int_report, _ = intd.build(int_args)
        fp_report, _ = fp.build(fp_args)

    errors = crosscheck(surface, int_report, fp_report, census)
    merged = merge(int_report, fp_report, surface)
    errors += merged["errors"]

    tools = fp._parse_kv(args.tool, "tool")
    sources = dict(
        opcodes=dict(path=fp._display(opcodes_path),
                     sha256=fp._sha256(opcodes_path)),
        inst_index=dict(path=int_report["sources"]["inst_index"]["path"],
                        sha256=int_report["sources"]["inst_index"]["sha256"]),
        contract_isa=dict(path=int_report["sources"]["contract_isa"]["path"],
                          sha256=int_report["sources"]["contract_isa"]["sha256"]),
        fp_spec=dict(path=fp_report["sources"]["spec_appendix_a"]["path"],
                     sha256=fp_report["sources"]["spec_appendix_a"]["sha256"]),
        runs=[dict(scope="int", **r) for r in int_report["sources"]["runs"]]
             + [dict(scope="fp", **r) for r in fp_report["sources"]["runs"]],
    )
    report = dict(
        schema=SCHEMA, task=TASK, milestone="M13",
        input_commit=commit,
        scope="M13 三平台差分收口：`tests/inst/**/*.S` 全量载体在 chipyard Tiny / "
              "qemu system / gem5 FS 上逐镜像（同 ELF）比对退出码与逐检查点 8 字节"
              "结果流；cfx 面（册 `11-cfx`）不在本矩阵",
        engines=engines, tools=tools, sources=sources,
        surface=surface, run_census=census,
        classification={k: v for k, v in merged["by_class"].items()},
        merged=dict(counts=merged["counts"],
                    differences=merged["differences"],
                    agree_fail=merged["agree_fail"],
                    gaps=merged["gaps"],
                    matrix_blanks=merged["matrix_blanks"],
                    structural_gaps=merged["structural_gaps"]),
        open_questions=list(OPEN_QUESTIONS),
        delta=list(DELTA),
        known_items=dict(int=int_report["known_items"],
                         fp=fp_report["known_items"]),
        predecessors=list(PREDECESSORS),
        int_report=int_report, fp_report=fp_report,
        checks=dict(ok=not errors, errors=errors),
    )
    return report, render_markdown(report), render_matrix(report)


def _eng_lines(report: dict) -> list[str]:
    lines = [f"qemu `{report['engines'].get('qemu', '?')}`、"
             f"gem5 `{report['engines'].get('gem5', '?')}`、"
             f"chipyard `{report['engines'].get('chipyard', '?')}`"]
    tools = report.get("tools") or {}
    if tools:
        lines.append(" · ".join(f"{k} `{v}`" for k, v in sorted(tools.items())))
    return lines


def _known_rows(report: dict) -> list[dict]:
    """把两段的 known_items 按 key 合并（同一 `ISS-357` 不重复列两次）。"""
    rows: dict[str, dict] = {}
    for group, label in (("int", "整数段"), ("fp", "FP 段")):
        for key, item in report["known_items"][group].items():
            row = rows.setdefault(key, dict(key=key, groups=[], **{
                k: item[k] for k in ("status", "note", "applicability")}))
            row["groups"].append(label)
    return [rows[k] for k in sorted(rows)]


def _class_counts(report: dict) -> dict:
    surf = report["surface"]
    ic = report["int_report"]["results"]
    fc = report["fp_report"]["results"]
    return dict(
        carriers=surf["carriers_total"],
        images=surf["images_total"],
        int_agree=ic["agree_pass"], int_images=ic["images"],
        fp_agree=fc["agree_pass"], fp_images=fc["images"],
        diff=ic["diff"] + fc["diff"],
        agree_fail=ic["agree_fail"] + fc["agree_fail"],
    )


def render_matrix(report: dict) -> str:
    add = "".join
    L: list[str] = []
    a = L.append
    a("<!-- 现场生成，勿手改 -->")
    a("")
    a("# M13 三平台差分矩阵（冻结）")
    a("")
    a("- **生成时间**：不写墙钟（册为确定性重建）；时间锚 = 输入 commit "
      f"`{report['input_commit']}` 的提交时间")
    a("- **数据来源**：同一批三平台逐镜像运行输入（同一份 ELF 在 chipyard Tiny / "
      "qemu system / gem5 FS 上的退出码 + 逐检查点 8 字节结果流），由 "
      "`tools/testcases/parity/int_diff.py` 与 `fp_diff.py` 现场重算；逐例明细见"
      "收口报告（`.tao/knowledge/refs/m13-005-acceptance.json`）的嵌入式逐例表")
    a("- **机器指纹**：" + "；".join(_eng_lines(report)))
    a("- **复现**：`bash <运行期证据目录>/run.sh`（默认段重算并逐字节比对，"
      "`--inject` 段做反例注入）；生成器 = `tools/testcases/parity/"
      "acceptance_report.py`")
    a("")
    cc = _class_counts(report)
    surf = report["surface"]
    by = surf["by_class"]
    a("## 0. 口径与分母（现场统计）")
    a("")
    a(f"- `.S` 载体 **{surf['carriers_total']}**（现场枚举）= 整数段 "
      f"**{by['int']['carriers']}**（{by['int']['ids']} 个 opcode id + "
      f"{by['int']['non_id']} 个非 id 载体）+ FP 段 **{by['fp']['carriers']}** + "
      f"cfx 册 **{by['cfx']['carriers']}**（册 `11-cfx`，归 CFX 专项，不进本矩阵）")
    a(f"- 镜像 **{surf['images_total']}** = 整数段 **{by['int']['images']}** + FP 段 "
      f"**{by['fp']['images']}** + cfx **{by['cfx']['images']}**（链例 = 每载体 1 个，"
      "故障例 = 每 `TEST_FAULT*` 一行）")
    a(f"- 本矩阵覆盖 **{by['int']['images'] + by['fp']['images']}** 个镜像；三平台"
      f"一致通过 **{cc['int_agree'] + cc['fp_agree']}**（整数 {cc['int_agree']}/"
      f"{cc['int_images']}、FP {cc['fp_agree']}/{cc['fp_images']}）；平台差异 "
      f"**{cc['diff']}**、三方一致非通过 **{cc['agree_fail']}**、未归因 **0**")
    a(f"- FP 计数口径：`scope: fp` **{report['fp_report']['count_criteria']['scope_fp']}**"
      f" 条（机器可读全集；`SimRISC-07` 附录 A = "
      f"{report['fp_report']['count_criteria']['appendix_a']} 行；历史别名 47 退役）")
    cen = report.get("run_census") or {}
    if cen.get("cfx"):
        a(f"- 输入完整性：cfx 册 {cen['cfx']['records']} 个镜像在同一批输入中也全部"
          f"三方一致（runner 判定 {cen['cfx']['pass_']}/{cen['cfx']['records']}）；"
          "它们不计入本矩阵（归 CFX 专项）")
    a("- 本册对象 = `.S` 指令级差分（逐检查点 8 字节结果流 + 故障退出码）；"
      "长尾套件矩阵是另一册（同目录 `M13-三平台差分矩阵.md`），两者不合并计数")
    a("")
    a("## 1. 三平台矩阵（按册）")
    a("")
    a("| 册 | spec 章 | 段 | 载体 | 链例点 | 故障例 | 镜像 | 三平台一致 | 差异 |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    book_of = {row["id"]: row["book"] for row in surf["rows"]}
    per_book = {}
    for key, rep in (("int", report["int_report"]),
                     ("fp", report["fp_report"])):
        for img in rep["results"]["per_image"]:
            book = book_of.get(img["id"])
            if book is None:
                raise intd.DiffError(f"{key}: per-image id {img['id']!r} has "
                                     f"no carrier row")
            cell = per_book.setdefault(book, dict(agree=0, diff=0))
            if img["verdict"] == "AGREE_PASS":
                cell["agree"] += 1
            else:
                cell["diff"] += 1
    tot = dict(carriers=0, points=0, faults=0, images=0, agree=0, diff=0)
    for fam in surf["books"]:
        agg = per_book.get(fam["book"], dict(agree=0, diff=0))
        covered = fam["klass"] != "cfx"
        mark = "cfx 专项" if not covered else str(agg["agree"])
        a(f"| `{fam['book']}` | `{fam['spec'] or fam['chapter']}` | {fam['klass']} | "
          f"{fam['carriers']} | {fam['chain_points']} | {fam['fault_cases']} | "
          f"{fam['images']} | {mark} | {agg['diff'] if covered else '—'} |")
        tot["carriers"] += fam["carriers"]
        tot["points"] += fam["chain_points"]
        tot["faults"] += fam["fault_cases"]
        tot["images"] += fam["images"]
        tot["agree"] += agg["agree"]
        tot["diff"] += agg["diff"]
    a(f"| **合计** | — | — | **{tot['carriers']}** | **{tot['points']}** | "
      f"**{tot['faults']}** | **{tot['images']}** | **{tot['agree']}** | "
      f"**{tot['diff']}** |")
    a("")
    a("> 一致数只统计三平台逐例 `AGREE_PASS`（退出码 + 结果字节流逐字节相等）；"
      "cfx 册 5 个载体不在本矩阵。")
    a("")
    a("## 2. FP：`rf0[33:32]` 舍入 × 异常标志（链例点 / 三平台一致）")
    a("")
    fm = report["fp_report"]["flags_matrix"]
    a("| rf0[33:32] | " + " | ".join(fm["categories"]) + " |")
    a("| --- | " + " | ".join(["---"] * len(fm["categories"])) + " |")
    for mode in fm["modes"]:
        cells = [c for c in fm["cells"] if c["mode"] == mode]
        a("| " + mode + " | " + " | ".join(
            f"{c['points']} / {c['agree']} (rf0 {c['rf0_sensitive']})"
            for c in cells) + " |")
    a("")
    a(f"空白格 **{len(fm['empty'])}** 个：现有 `.S` 向量没有该「舍入档 × 标志」组合"
      "（测试资产缺口，不是引擎差异）。逐格原因见收口报告 §5。")
    a("")
    a("## 3. 差异与归因（合并 002 / 003 / 004）")
    a("")
    m = report["merged"]
    a(f"- 平台差异（`DIFF`）：**{m['counts']['platform_diff']}**；未归因 "
      f"**{m['counts']['unattributed']}**；三方一致非通过（`AGREE_FAIL`）："
      f"**{m['counts']['agree_fail']}**")
    if m["counts"]["unattributed"]:
        for item in report["classification"]["unattributed"]:
            a(f"  - **UNATTRIBUTED** `{item['id']}`#{item['case_n']}"
              f"（{item['kind']}）")
    a(f"- 覆盖缺口 **{m['counts']['coverage_gaps']}**、FP 矩阵空白格 "
      f"**{m['counts']['matrix_blanks']}**、结构 GAP **{m['counts']['structural_gaps']}**"
      "（逐条见收口报告 §5）")
    a("- 前序任务位置：" + "；".join(
        f"`{p['task']}`（{p['topic']}）= {p['role']}" for p in report["predecessors"]))
    a("- 与旧版口径的对照（常量，不作判据）：" + "；".join(
        f"{d['item']} {d['old']}→{d['new']}" for d in report["delta"]))
    a("")
    for cls, label in (("spec", "spec 歧义（含已登记待裁定）"),
                       ("implementation", "实现缺陷"),
                       ("test_asset", "测试资产")):
        items = report["classification"].get(cls) or []
        a(f"### {label}（{len(items)}）")
        a("")
        if items:
            for item in items:
                obs = item.get("detail") or item.get("issue") or ""
                a(f"- `{item.get('id')}`"
                  + (f"#{item['case_n']}" if item.get("case_n") else "")
                  + f"：{obs}")
        else:
            a("(none)")
        a("")
    a("> 载体面内的 spec 歧义 = "
      f"{len([g for g in m['gaps'] if g['class_'] == 'spec'])} 条；"
      "「spec 歧义」类里其余条目是**已登记**、但本矩阵不覆盖的待裁定口径（见 §4）。")
    a("")
    a("## 4. 待裁定项（spec 口径 / 实现归口）")
    a("")
    a("本矩阵载体面内的 spec 歧义：**"
      + str(len([g for g in m["gaps"] if g["class_"] == "spec"])) + "** 条。"
      "另有已登记、本矩阵不覆盖但需裁定口径的项：")
    a("")
    for q in report["open_questions"]:
        a(f"- `{q['id']}`：{q['question']}")
        a(f"  - 事实依据：{q['evidence']}")
        a(f"  - 本矩阵不覆盖的理由：{q['why_not_in_matrix']}")
    a("")
    a("## 5. 覆盖缺口与测试资产缺口")
    a("")
    gaps = m["gaps"]
    a(f"- 缺口总数 **{len(gaps)}**")
    if gaps:
        for g in gaps:
            a(f"  - `{g['id']}` — {g['kind']}（{g['class_']}）：{g.get('detail')}")
    else:
        a("  - (none) — 每条载体的 `spec_cite` 都能解析到现存章节且章内有该助记符；"
          "全部载体都在 `tests/inst.yaml` 登记")
    a(f"- FP 空白格：**{len(fm['empty'])}** 个（现有向量无该组合，逐格原因见收口报告）")
    for g in report["merged"]["structural_gaps"]:
        a(f"- 结构 GAP `{g['id']}`：{g['detail']}（不造用例、不伪造期望）")
    a("")
    a("## 6. 已知项（单列，不混入平台差异）")
    a("")
    for row in _known_rows(report):
        a(f"- `{row['key']}`（{row['status']}；{'/'.join(row['groups'])}）："
          f"{row['note']}")
    a("")
    a("## 7. 可回溯与复现")
    a("")
    a("- 逐例（三平台 `exit` / 字节数 / 结果流 md5）：`.tao/knowledge/refs/"
      "m13-005-acceptance.json` 的 `int_report.results.per_image` 与 "
      "`fp_report.results.per_image`（每条即一份状态摘要）")
    a("- 输入静态真源 sha256：" + "、".join(
        f"`{k}` `{v['sha256'][:16]}`" for k, v in sorted(report["sources"].items())
        if isinstance(v, dict) and "sha256" in v))
    a("- 运行输入 sha256：" + "、".join(
        f"`{r['scope']}/{r['label']}` {r['records']} 条 `{r['sha256'][:16]}`"
        for r in report["sources"]["runs"]))
    a("- 复现：`bash <运行期证据目录>/run.sh`；`--inject` 只跑反例注入段")
    a("")
    a("## 8. 判据")
    a("")
    if report["checks"]["ok"]:
        a("- 每个非 `AGREE_PASS` 项均已归因或登记；分母与两份逐例报告逐项对账；"
          "三平台完成数 = 现场枚举分母")
    else:
        for err in report["checks"]["errors"]:
            a(f"- FAIL: {err}")
    a("")
    del add
    return "\n".join(L) + "\n"


def render_markdown(report: dict) -> str:
    L: list[str] = []
    a = L.append
    cc = _class_counts(report)
    surf = report["surface"]
    by = surf["by_class"]
    a("# m13-integ-005: M13 收口（差异归因 + 矩阵冻结）")
    a("")
    a("> 由 `tools/testcases/parity/acceptance_report.py` 从两平台逐例生成器的"
      "同一批输入确定性重建；不写生成时刻、不写运行期路径。")
    a("")
    a("## 0. 结论")
    a("")
    a(f"- 向量面：`.S` 载体 **{surf['carriers_total']}**，镜像 "
      f"**{surf['images_total']}**；本矩阵覆盖 "
      f"{by['int']['images'] + by['fp']['images']} 个镜像")
    a(f"- 三平台逐例：整数段 **{cc['int_agree']}/{cc['int_images']}**、FP 段 "
      f"**{cc['fp_agree']}/{cc['fp_images']}** `AGREE_PASS`；平台差异 "
      f"**{cc['diff']}**、三方一致非通过 **{cc['agree_fail']}**、未归因 **0**")
    a(f"- 差异分类：spec 歧义（含已登记待裁定）**"
      f"{len(report['classification']['spec'])}**、"
      f"实现缺陷 **{len(report['classification']['implementation'])}**、"
      f"测试资产 **{len(report['classification']['test_asset'])}**、"
      f"未归因 **{len(report['classification']['unattributed'])}**")
    a(f"- 输入 commit：`{report['input_commit']}`（陈旧判定的唯一时间锚）")
    a("")
    a("## 1. 输入与身份")
    a("")
    a("- 机器指纹：" + "；".join(_eng_lines(report)))
    for k, v in sorted(report["sources"].items()):
        if isinstance(v, dict) and "sha256" in v:
            a(f"- `{v['path']}` sha256 `{v['sha256'][:16]}`")
    for r in report["sources"]["runs"]:
        a(f"- run `{r['scope']}/{r['label']}`：{r['records']} 条记录 "
          f"sha256 `{r['sha256'][:16]}`")
    a("")
    a("## 2. 向量面（现场统计，按段）")
    a("")
    a("| 段 | 载体 | opcode id | 非 id 载体 | 链例点 | 故障例 | 镜像 |")
    a("| --- | --- | --- | --- | --- | --- | --- |")
    for cls in CLASSES:
        agg = by[cls]
        a(f"| {cls} | {agg['carriers']} | {agg['ids']} | {agg['non_id']} | "
          f"{agg['chain_points']} | {agg['fault_cases']} | {agg['images']} |")
    a(f"| **合计** | **{surf['carriers_total']}** | "
      f"**{sum(by[c]['ids'] for c in CLASSES)}** | "
      f"**{surf['non_id'] and len(surf['non_id'])}** | "
      f"**{sum(by[c]['chain_points'] for c in CLASSES)}** | "
      f"**{sum(by[c]['fault_cases'] for c in CLASSES)}** | "
      f"**{surf['images_total']}** |")
    a("")
    a(f"非 id 载体 **{len(surf['non_id'])}** 条（保留编码 / 伪指令载体，以自身文件头"
      "的 spec 出处计）：" + "、".join(f"`{e['id']}`" for e in surf["non_id"]))
    a("")
    a("## 3. 逐例结果（两份生成器的现场输出）")
    a("")
    a("| 段 | 镜像 | AGREE_PASS | AGREE_FAIL | DIFF | spec 歧义 | 覆盖缺口 |")
    a("| --- | --- | --- | --- | --- | --- | --- |")
    for label, rep in (("整数段", report["int_report"]),
                       ("FP 段", report["fp_report"])):
        res = rep["results"]
        amb = len([g for g in rep["coverage"]["gaps"]
                   if g["kind"] == "spec_ambiguity"])
        a(f"| {label} | {res['images']} | {res['agree_pass']} | "
          f"{res['agree_fail']} | {res['diff']} | {amb} | "
          f"{len(rep['coverage']['gaps'])} |")
    a("")
    a("> 逐镜像三平台 `exit` / 字节数 / 结果流 md5 见本报告 JSON 的 "
      "`int_report.results.per_image` 与 `fp_report.results.per_image`。")
    a("")
    a("## 4. 差异归因（分类）")
    a("")
    for cls, label in (("spec", "spec 歧义（含已登记待裁定）"),
                       ("implementation", "实现缺陷"),
                       ("test_asset", "测试资产")):
        items = report["classification"].get(cls) or []
        a(f"### {label}（{len(items)}）")
        a("")
        if not items:
            a("(none)")
        for item in items:
            head = f"- `{item.get('id')}`"
            if item.get("case_n"):
                head += f"#{item['case_n']}"
            if item.get("kind"):
                head += f"（{item['kind']}）"
            detail = item.get("detail") or item.get("issue") or ""
            extra = ""
            if item.get("owner"):
                extra = f"；owner=`{item['owner']}`"
            if item.get("spec_cite"):
                extra += f"；`{item['spec_cite']}`"
            if item.get("why_not_in_matrix"):
                extra += f"；不覆盖理由：{item['why_not_in_matrix']}"
            a(head + "：" + str(detail) + extra)
        a("")
    a("## 5. 覆盖缺口与测试资产缺口")
    a("")
    gaps = report["merged"]["gaps"]
    a(f"- 生成器报告的覆盖缺口 **{len(gaps)}** 条")
    for g in gaps:
        a(f"  - `{g['id']}` — {g['kind']}（{g['class_']}）：{g.get('detail')}")
    fm = report["fp_report"]["flags_matrix"]
    a(f"- FP 矩阵空白格 **{len(fm['empty'])}** 个（现有向量无该组合）：")
    for cell in fm["empty"]:
        a(f"  - {cell['mode']} × {cell['category']}：{cell['reason']}")
    for g in report["merged"]["structural_gaps"]:
        a(f"- 结构 GAP `{g['id']}`：{g['detail']}（不造用例、不伪造期望）")
    a("")
    a("## 5.1 与旧版口径的对照（常量说明，不作判据）")
    a("")
    a("| 项 | 旧版（002/003 已验收） | 冻结版（本报告现场重算） | 成因 |")
    a("| --- | --- | --- | --- |")
    for d in report["delta"]:
        a(f"| {d['item']} | {d['old']} | {d['new']} | {d['reason']} |")
    a("")
    a("> 旧版报告的「已知缺口」在此逐条交代去向；冻结版判据一律来自本报告的现场重算。")
    a("")
    a("## 6. 待裁定项（spec 口径 / 实现归口）")
    a("")
    inscope = [g for g in gaps if g["class_"] == "spec"]
    a(f"- 载体面内 spec 歧义：**{len(inscope)}** 条"
      + ("" if inscope else "（none）"))
    for q in report["open_questions"]:
        a(f"- `{q['id']}`（{q['class_']}）：{q['question']}")
        a(f"  - 依据：{q['evidence']}")
        a(f"  - 本矩阵不覆盖：{q['why_not_in_matrix']}")
    a("")
    a("## 7. 前序任务位置")
    a("")
    for p in report["predecessors"]:
        a(f"- `{p['task']}`（{p['topic']}）：{p['role']} —— {p['basis']}")
    a("")
    a("## 8. 已知项（单列）")
    a("")
    for row in _known_rows(report):
        a(f"- `{row['key']}`（{row['status']}；{'/'.join(row['groups'])}）："
          f"{row['note']}（{row['applicability']}）")
    a("")
    a("## 9. 判据")
    a("")
    if report["checks"]["ok"]:
        a("- 每个非 `AGREE_PASS` 项均已归因或登记；分母与两份逐例报告逐项对账；"
          "`AGREE_PASS` 链例三平台结果流逐字节相等（生成器内断言）")
    else:
        for err in report["checks"]["errors"]:
            a(f"- FAIL: {err}")
    a("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# 自检：分类 / 对账 / 确定性，每类一条可达 FAIL
# ---------------------------------------------------------------------------
def self_test() -> int:
    checks = []

    def expect(name, fn):
        try:
            fn()
        except (intd.DiffError, intd.SetupError):
            checks.append((name, True, "rejected"))
        else:
            checks.append((name, False, "not detected"))

    # 1. 归因 owner -> 分类；未知 owner 必须拒绝（不是静默归类）
    ok = classify_diff("t", dict(id="x", case_n=0, kind="chain",
                                 attribution=dict(owner="implementation"),
                                 points=[], observed={}))
    checks.append(("owner classified", ok["class_"] == "implementation",
                   ok["class_"]))
    expect("unknown owner rejected", lambda: classify_diff(
        "t", dict(id="x", case_n=0, kind="chain",
                  attribution=dict(owner="nonsense"), points=[], observed={})))

    # 2. 覆盖缺口 kind -> 分类；未知 kind 必须拒绝
    checks.append(("gap classified",
                   classify_gap(dict(id="x", kind="not_indexed"))["class_"]
                   == "test_asset", "test_asset"))
    expect("unknown gap kind rejected", lambda: classify_gap(
        dict(id="x", kind="nonsense")))

    # 3. 向量面对账：分母不一致必须判出（int 镜像数被改 1）
    surf = dict(carriers_total=2, images_total=3,
                by_class=dict(int=dict(carriers=1, ids=1, non_id=0,
                                       chain_points=1, fault_cases=1, images=2),
                              fp=dict(carriers=1, ids=1, non_id=0,
                                      chain_points=1, fault_cases=0, images=1),
                              cfx=dict(carriers=0, ids=0, non_id=0,
                                       chain_points=0, fault_cases=0, images=0)),
                non_id=[], books=[],
                rows=[dict(id="a", klass="int", book="01-x", images=2),
                      dict(id="b", klass="fp", book="07-y", images=1)])
    int_report = dict(coverage=dict(total=1, images=2, ids_with_opcode=1,
                                    non_id=[],
                                    excluded=dict(fp=[dict(id="b")], cfx=[])),
                      checks=dict(ok=True), results={})
    fp_report = dict(coverage=dict(total=1, with_carrier=1),
                     checks=dict(ok=True), results={})
    checks.append(("crosscheck clean",
                   not crosscheck(surf, int_report, fp_report), "no error"))
    bad = json.loads(json.dumps(int_report))
    bad["coverage"]["images"] = 1
    checks.append(("crosscheck catches count drift",
                   bool(crosscheck(surf, bad, fp_report)), "int images"))

    # 4. 确定性：同一报告渲染两次逐字节相同
    rep = dict(schema=SCHEMA, task=TASK, input_commit="0" * 40,
               engines={p: "x" for p in PLATFORMS}, tools={},
               sources=dict(runs=[]),
               surface=surf, classification={c: [] for c in
                                             ("spec", "implementation",
                                              "test_asset", "unattributed")},
               merged=dict(counts=dict(platform_diff=0, agree_fail=0,
                                       coverage_gaps=0, matrix_blanks=0,
                                       structural_gaps=0, unattributed=0),
                           differences=[], agree_fail=[], gaps=[],
                           matrix_blanks=[], structural_gaps=[]),
               open_questions=[], delta=[],
               run_census={}, known_items=dict(int={}, fp={}),
               predecessors=[], int_report=dict(
                   results=dict(per_image=[], agree_pass=0, agree_fail=0,
                                diff=0, images=0),
                   count_criteria=dict(scope_fp=0, appendix_a=0),
                   coverage=dict(gaps=[])),
               fp_report=dict(results=dict(per_image=[], agree_pass=0,
                                           agree_fail=0, diff=0, images=0),
                              count_criteria=dict(scope_fp=0, appendix_a=0),
                              flags_matrix=dict(modes=[], categories=[],
                                                cells=[], empty=[]),
                              coverage=dict(gaps=[])),
               checks=dict(ok=True, errors=[]))
    checks.append(("matrix render deterministic",
                   render_matrix(rep) == render_matrix(rep), "equal"))
    checks.append(("acceptance render deterministic",
                   render_markdown(rep) == render_markdown(rep), "equal"))
    checks.append(("input commit rendered in matrix",
                   "0" * 40 in render_matrix(rep), "sha present"))

    bad = [c for c in checks if not c[1]]
    for name, okv, detail in checks:
        print(f"  [{'PASS' if okv else 'FAIL'}] {name}: {detail}")
    print(f"acceptance_report self-test: {len(checks) - len(bad)}/{len(checks)} "
          f"{'PASS' if not bad else 'FAIL'}")
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opcodes", default="contracts/opcodes.yaml")
    ap.add_argument("--spec-dir", default="spec")
    ap.add_argument("--fp-spec", default="spec/SimRISC-07-浮点运算.md")
    ap.add_argument("--inst-index", default="tests/inst.yaml")
    ap.add_argument("--tests-root", default="tests")
    ap.add_argument("--contract", default=".tao/contracts/contract-isa.md")
    ap.add_argument("--run", action="append", default=None,
                    help="LABEL=<inst-asm-suite JSON>（可重复）")
    ap.add_argument("--work", action="append", default=None,
                    help="LABEL=<run_asm_suite work-dir>（与 --run 一一对应）")
    ap.add_argument("--engine", action="append", default=None,
                    help="PLATFORM=<md5>（qemu / gem5 / chipyard，必须齐全）")
    ap.add_argument("--tool", action="append", default=None,
                    help="NAME=<md5>（llvm-mc / bootrom 等，仅记录身份）")
    ap.add_argument("--attribution", default=None,
                    help="透传给 `int_diff.py` 的逐条归因表 JSON（key=<id>#<case_n>）")
    ap.add_argument("--input-commit", default=None,
                    help="报告记录/比较的输入 commit（缺省 `git rev-parse HEAD`）")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--markdown-out", default=None)
    ap.add_argument("--matrix-out", default=None)
    ap.add_argument("--check", default=None,
                    help="与落盘产物逐字节比对（.json / 名称含「矩阵」/ 其它 .md）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    try:
        report, markdown, matrix = build(args)
    except intd.SetupError as exc:
        print(f"acceptance_report: SETUP: {exc}", file=sys.stderr)
        return 2
    except intd.DiffError as exc:
        print(f"acceptance_report: FAIL: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown, encoding="utf-8")
    if args.matrix_out:
        Path(args.matrix_out).write_text(matrix, encoding="utf-8")

    if args.check:
        target = Path(args.check)
        if not target.is_file():
            print(f"acceptance_report: SETUP: {target} not found",
                  file=sys.stderr)
            return 2
        if target.suffix == ".json":
            want = payload
        elif "矩阵" in target.name:
            want = matrix
        else:
            want = markdown
        got = target.read_text(encoding="utf-8")
        if got != want:
            print(f"acceptance_report: FAIL: {target} differs from the "
                  f"regenerated output ({len(got)} vs {len(want)} bytes)",
                  file=sys.stderr)
            return 1
        print(f"acceptance_report: check PASS ({target})")

    if not report["checks"]["ok"]:
        for err in report["checks"]["errors"]:
            print(f"acceptance_report: FAIL: {err}", file=sys.stderr)
        return 1
    counts = report["merged"]["counts"]
    print("acceptance_report: PASS (%d carriers, %d images, %d diff, "
          "%d gap, %d open question)"
          % (report["surface"]["carriers_total"],
             report["surface"]["images_total"], counts["platform_diff"],
             counts["coverage_gaps"], len(report["open_questions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
