#!/usr/bin/env python3
"""three_platform_matrix.py -- qemu / gem5 / chipyard 三平台差分矩阵入口（M13 骨架）.

为什么先做「骨架 + 生成器」：M13 的 chipyard 列依赖 M12 核（`m12-chipyard-007`），
核未就绪时该列只允许 `N/A`（**明确不可用**，不是伪值），由 `m13-integ-002`/`003`
填列。本脚本只做三件事：

  1. **归一化**：把已入库的逐例基线 JSON 读成统一行（case / 三个平台列 / 归因）；
  2. **复算 + fail-closed**：计数、判定、归因全部从行重算；任何非 PASS 行没有
     owner、任何未知状态/gap、任何声明值与行不符，都是非零退出（不静默放过）；
  3. **渲染**：输出 `docs/TestReports/<M>-<主题>.md` 形态的册（首行现场生成
     marker + 册头四项），只写机器指纹、不写运行期绝对路径。

复用（不复制，`ADR-0048 D1/D2/D5` 同源）：

  * 状态词表与配对判定 `qemu ↔ gem5` = `run_parity.py`（`STATUSES`、
    `_verdict`）；`QEMU PASS ⇒ 对方 PASS` 的硬门语义随之继承；
  * 归因 owner 词表与「预算耗尽 ≠ 判定」口径 = `se_tset_matrix.py`
    （`OWNERS`、`TIMEOUT_CAPABILITY`）。

输入 JSON 两种形态（按有无 `qemu_klass` 自动识别）：

  * **legacy 长尾基线**（已入库 `m13-001` / `m13-002`）：顶层 `rows[]`，每行带
    `qemu_klass` / `gem5_klass` / `gem5_gap` / `*_exit`；脚本按同一映射转成三平台
    列，并用 `selection` 声明的 `total` / `by_suite` 对账（不符即 FAIL）；
  * **canonical 三平台行**（`m13-integ-002`/`003` 用）::

        {"schema": "three-platform-cases/1", "link_mode": "<档>",
         "generated_utc": "...", "fingerprint": {...},
         "cases": [{"case": "...", "suite": "...",
                    "qemu":     {"status": "PASS", "exit": 0},
                    "gem5":     {"status": "BLOCKED", "exit": null,
                                 "gap": "time budget"},
                    "chipyard": {"status": "N/A"}}]}

    同名 `(link_mode, suite, case)` 在多个输入里出现时按**平台列**合并；同一平台
    给出两个不同 `status`/`exit` ⇒ FAIL（不猜哪个是真）。

Usage::

    # 从已入库基线重建（fresh clone 即可跑；默认输入 = m13 长尾两份）
    python3 tools/testcases/parity/three_platform_matrix.py \\
        --markdown-out <运行期目录>/m13-三平台差分矩阵.md

    # 校验入库册与重建结果逐字节一致（册不得手改）
    python3 tools/testcases/parity/three_platform_matrix.py \\
        --check docs/TestReports/M13-三平台差分矩阵.md

    # 追加来源 / 单独挂 chipyard 证据
    python3 tools/testcases/parity/three_platform_matrix.py \\
        --source <canonical.json> --chipyard <chipyard.json>

Exit codes: 0 = 全部不变式成立；1 = 不变式失败（未归因 / 未知状态 / 声明值不符 /
`--check` 与现册不一致）；2 = setup 错（缺文件、坏 JSON、未知 schema）。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import run_parity as parity  # noqa: E402
import se_tset_matrix as se  # noqa: E402

PLATFORMS = ("qemu", "gem5", "chipyard")
SNAPSHOT_MARKER = "<!-- 现场生成，勿手改 -->"
CANONICAL_SCHEMA = "three-platform-cases/1"
#: 默认输入：已入库的两份 M13 长尾基线（fresh clone 上可读 ⇒ 矩阵可重建）。
DEFAULT_SOURCES = (
    os.path.join(".tao", "knowledge", "refs", "m13-001-static-3600s-full.json"),
    os.path.join(".tao", "knowledge", "refs", "m13-002-dynamic-3600s-full.json"),
)
#: chipyard 列不可用的**依据**（核未就绪）；`N/A` 必须能指到这句。
CHIPYARD_BASIS = ("`m12-chipyard-007` 未开始（M12 核未就绪）⇒ chipyard 列记 `N/A`"
                  "（明确不可用，不是伪值），由 `m13-integ-002`/`003` 填列")

#: 驱动 klass -> 平台 status（legacy 长尾基线）。
_KLASS = {"pass": "PASS", "fail": "FAIL", "blocked": "BLOCKED",
          "timeout": "TIMEOUT", "error": "ERROR", "skip": "SKIP_PROFILE",
          "skipped": "SKIP_PROFILE", "deferred": "DEFERRED", "n/a": "N/A"}

#: `gem5` 侧 `BLOCKED` 的归因表，键 = `(档, gap 标签)`。
#:  - static 长尾 72/72 在 3600 s 仍超时、且最小例（qemu 0.0 s）同样吃满 ⇒
#:    `ISS-361` 判为 gem5 SE **挂死**而非「慢」⇒ owner = implementation；
#:  - dynamic 未做单例诊断，按驱动口径只记「预算耗尽」（owner = budget，
#:    `TIMEOUT_CAPABILITY`：不是判定）。
#: 诊断结论变更时**只改本表**，矩阵与归因同步。
BLOCKED_OWNERS = {
    ("static", se.TIMEOUT_CAPABILITY): dict(
        issue="ISS-361", owner="implementation",
        detail="3600 s 预算仍无 guest exit，最小例（qemu 0.0 s）同样吃满 ⇒ "
               "疑 gem5 SE 挂死（`m13-testcases-001` 全量 72/72）"),
    ("dynamic", se.TIMEOUT_CAPABILITY): dict(
        issue=None, owner="budget",
        detail="预算耗尽（3600 s），不是判定；可比比值只覆盖 n=12"),
}

#: `GEM5_ONLY_FAIL`（qemu PASS、gem5 非 PASS）的显式登记表，键 =
#: `(档, suite, case)`；未登记即 FAIL（硬门红，不得静默进矩阵）。
GEM5_ONLY_FAIL = {
    ("dynamic", "llvm-ts", "MultiSource/Benchmarks/FreeBench/neural"): dict(
        issue="ISS-362", owner="implementation",
        detail="输出同长（358 B）但内容不同，qemu 侧与 reference 一致 ⇒ "
               "gem5 侧差异（疑浮点舍入/格式化），交 `m13-integ-002` 定位"),
}

#: 两引擎**同一非 PASS 判定**才允许进矩阵（空表 = 目前没有承认的 known-fail）。
BOTH_NON_PASS = {}

#: chipyard 列沿用 `run_parity` 的判定词表，只把「对方失败」改成本平台名字。
_CHIPYARD_VERDICT = {"AGREE_PASS": "AGREE_PASS", "AGREE_FAIL": "AGREE_FAIL",
                     "GEM5_ONLY_FAIL": "CHIPYARD_ONLY_FAIL",
                     "QEMU_ONLY_FAIL": "QEMU_ONLY_FAIL", "DIFF": "DIFF",
                     "BLOCKED_SIDE": "BLOCKED_SIDE", "N/A": "N/A"}

_COUNT_STATUSES = ("PASS", "FAIL", "BLOCKED", "TIMEOUT", "ERROR", "N/A")
_VERDICT_KEYS = ("AGREE_PASS", "AGREE_FAIL", "GEM5_ONLY_FAIL", "QEMU_ONLY_FAIL",
                 "DIFF", "BLOCKED_SIDE", "N/A")
_FP_KEYS = ("host", "cpu_model", "nproc", "jobs", "gem5_timeout_seconds",
            "qemu_timeout_seconds", "gem5_binary", "gem5_md5", "gem5_version",
            "qemu_binary", "qemu_md5", "qemu_version", "musl_head",
            "musl_dirty", "driver_md5")


class SetupError(Exception):
    """Missing file / bad JSON / unknown schema (exit 2)."""


# ---------------------------------------------------------------------------
# input loading
# ---------------------------------------------------------------------------

def _read_json(path):
    if not os.path.isfile(path):
        raise SetupError(f"input not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as exc:
        raise SetupError(f"{path}: not valid JSON: {exc}") from exc


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _abspath(path):
    return path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)


def _source_head(path, doc, track):
    return {"path": path,
            "sha256": _sha256(path) if os.path.isfile(path) else "",
            "track": track,
            "task": doc.get("task") or os.path.splitext(os.path.basename(path))[0],
            "generated_utc": doc.get("generated_utc"),
            "fingerprint": doc.get("fingerprint") or {}}


def _legacy_cases(path, doc):
    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SetupError(f"{path}: legacy baseline without a non-empty 'rows'")
    cases, declared = [], {}
    for idx, row in enumerate(rows, 1):
        for key in ("case", "suite", "qemu_klass", "gem5_klass"):
            if key not in row:
                raise SetupError(f"{path}: rows[{idx}] has no {key!r}")
        qk, gk = row["qemu_klass"], row["gem5_klass"]
        cases.append({
            "case": row["case"], "suite": row["suite"],
            "category": row.get("category"),
            "qemu": {"status": _KLASS.get(qk, qk), "exit": row.get("qemu_exit")},
            "gem5": {"status": _KLASS.get(gk, gk), "exit": row.get("gem5_exit"),
                     "gap": row.get("gem5_gap")},
        })
    selection = doc.get("selection") or {}
    declared["total"] = selection.get("total")
    declared["by_suite"] = selection.get("by_suite")
    declared["ok"] = doc.get("ok")
    declared["missing"] = doc.get("missing")
    return cases, declared


def _canonical_cases(path, doc):
    if doc.get("schema") != CANONICAL_SCHEMA:
        raise SetupError(f"{path}: schema {doc.get('schema')!r} != "
                         f"{CANONICAL_SCHEMA!r}")
    cases = doc.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SetupError(f"{path}: 'cases' must be a non-empty list")
    out = []
    for idx, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise SetupError(f"{path}: cases[{idx}] is not an object")
        for key in ("case", "suite"):
            if not case.get(key):
                raise SetupError(f"{path}: cases[{idx}] has no {key!r}")
        item = {"case": case["case"], "suite": case["suite"],
                "category": case.get("category")}
        if not any(case.get(p) is not None for p in PLATFORMS):
            raise SetupError(f"{path}: cases[{idx}] has no platform column")
        for plat in PLATFORMS:
            rec = case.get(plat)
            if rec is None:
                continue
            if not isinstance(rec, dict):
                raise SetupError(f"{path}: cases[{idx}].{plat} is not an object")
            item[plat] = dict(rec)
        out.append(item)
    return out, {}


def _from_doc(path, doc):
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if isinstance(rows, list) and rows and isinstance(rows[0], dict) \
            and "qemu_klass" in rows[0]:
        cases, declared = _legacy_cases(path, doc)
        track = doc.get("link_mode") or "static"
        kind = "legacy"
    else:
        cases, declared = _canonical_cases(path, doc)
        track = doc.get("link_mode")
        if not isinstance(track, str) or not track.strip():
            raise SetupError(f"{path}: canonical input needs a non-empty "
                             f"'link_mode' (the 档)")
        kind = "canonical"
    src = _source_head(path, doc, track)
    src.update(kind=kind, cases=cases, declared=declared)
    return src


def load_source(path):
    full = _abspath(path)
    return _from_doc(full, _read_json(full))


# ---------------------------------------------------------------------------
# merge / judge
# ---------------------------------------------------------------------------

def _key(row):
    return "%s/%s/%s" % (row["link_mode"], row["suite"], row["case"])


def _merge(sources, chipyard_docs):
    rows, errors = {}, []

    def absorb(src, case, plat):
        key = (src["track"], case["suite"], case["case"])
        row = rows.get(key)
        if row is None:
            row = rows[key] = {"link_mode": src["track"], "suite": case["suite"],
                               "case": case["case"],
                               "category": case.get("category"),
                               "qemu": None, "gem5": None, "chipyard": None}
        rec = dict(case[plat])
        rec["source"] = src["path"]
        old = row[plat]
        if old is not None:
            if (old.get("status"), old.get("exit")) != (rec.get("status"),
                                                         rec.get("exit")):
                errors.append(
                    "%s/%s/%s: conflicting %s record (%s/%s from %s vs %s/%s "
                    "from %s)" % (key[0], key[1], key[2], plat,
                                  old.get("status"), old.get("exit"),
                                  old["source"], rec.get("status"),
                                  rec.get("exit"), rec["source"]))
            return
        row[plat] = rec

    for src in sources:
        seen = set()
        for case in src["cases"]:
            key = (src["track"], case["suite"], case["case"])
            if key in seen:
                errors.append("%s: duplicate case in one input" % _key(
                    {"link_mode": key[0], "suite": key[1], "case": key[2]}))
            seen.add(key)
            for plat in PLATFORMS:
                if case.get(plat) is not None:
                    absorb(src, case, plat)
    for src in chipyard_docs:
        seen = set()
        for case in src["cases"]:
            key = (src["track"], case["suite"], case["case"])
            if key in seen:
                errors.append("%s: duplicate chipyard case in one input"
                              % _key({"link_mode": key[0], "suite": key[1],
                                      "case": key[2]}))
            seen.add(key)
            absorb(src, case, "chipyard")

    out = [rows[k] for k in sorted(rows)]
    for row in out:
        if row["qemu"] is None or row["gem5"] is None:
            errors.append("%s: missing %s column (qemu and gem5 are required)"
                          % (_key(row),
                             "qemu" if row["qemu"] is None else "gem5"))
        if row["chipyard"] is None:
            row["chipyard"] = {"status": "N/A", "exit": None,
                               "basis": CHIPYARD_BASIS, "source": ""}
    return out, errors


def _check_declared(src, errors):
    """Reconcile a legacy baseline's declared selection with its own rows."""
    declared = src.get("declared") or {}
    if src["kind"] != "legacy":
        return
    if declared.get("ok") is not True:
        errors.append("%s: baseline is not green (ok=%r)"
                      % (src["path"], declared.get("ok")))
    if declared.get("missing"):
        errors.append("%s: baseline lists %d missing case(s)"
                      % (src["path"], len(declared["missing"])))
    total = declared.get("total")
    if total is not None and total != len(src["cases"]):
        errors.append("%s: selection.total %s != %d row(s)"
                      % (src["path"], total, len(src["cases"])))
    by_suite = declared.get("by_suite")
    if isinstance(by_suite, dict):
        got = {}
        for case in src["cases"]:
            got[case["suite"]] = got.get(case["suite"], 0) + 1
        if got != by_suite:
            errors.append("%s: selection.by_suite declared %r but recomputed %r"
                          % (src["path"], by_suite, got))


def _attribute(row, errors):
    """Return (owner, issue, detail) for a non-AGREE_PASS row; fail-closed."""
    verdict, key = row["verdict"], _key(row)
    gem5 = row["gem5"]
    if verdict == "AGREE_PASS":
        return "", None, ""
    if gem5.get("status") == "BLOCKED":
        gap = gem5.get("gap") or ""
        entry = BLOCKED_OWNERS.get((row["link_mode"], gap))
        if entry is None:
            errors.append("%s: gem5 BLOCKED with gap %r has no owner in "
                          "BLOCKED_OWNERS" % (key, gap))
            return "", None, ""
        return entry["owner"], entry.get("issue"), entry["detail"]
    if verdict == "GEM5_ONLY_FAIL":
        entry = GEM5_ONLY_FAIL.get((row["link_mode"], row["suite"], row["case"]))
        if entry is None:
            errors.append("%s: GEM5_ONLY_FAIL (qemu PASS, gem5 %s/%s) has no "
                          "attribution entry" % (key, gem5.get("status"),
                                                 gem5.get("exit")))
            return "", None, ""
        return entry["owner"], entry.get("issue"), entry["detail"]
    if verdict == "QEMU_ONLY_FAIL":
        errors.append("%s: QEMU_ONLY_FAIL (gem5 PASS, qemu %s) is not accepted "
                      "as a gem5 win; locate it before it enters the matrix "
                      "(ADR-0048 D5)" % (key, row["qemu"].get("status")))
        return "", None, ""
    if verdict == "AGREE_FAIL":
        entry = BOTH_NON_PASS.get((row["link_mode"], row["suite"], row["case"]))
        if entry is None:
            errors.append("%s: both engines non-PASS without an admitted basis"
                          % key)
            return "", None, ""
        return entry["owner"], entry.get("issue"), entry["detail"]
    if verdict == "DIFF":
        errors.append("%s: DIFF (qemu %s/%s vs gem5 %s/%s) needs a per-case "
                      "attribution" % (key, row["qemu"].get("status"),
                                       row["qemu"].get("exit"),
                                       gem5.get("status"), gem5.get("exit")))
        return "", None, ""
    if verdict in ("N/A", "BLOCKED_SIDE"):
        basis = (row["qemu"].get("basis") or gem5.get("basis") or "")
        if not basis:
            errors.append("%s: %s without a basis" % (key, verdict))
        return "", None, basis
    errors.append("%s: unclassified verdict %r" % (key, verdict))
    return "", None, ""


def judge(rows):
    """Recompute every verdict/attribution from the rows; never trust a field."""
    errors = []
    for row in rows:
        bad = False
        for plat in PLATFORMS:
            rec = row.get(plat) or {}
            status = rec.get("status")
            if status not in parity.STATUSES:
                errors.append("%s: %s.status %r outside %s"
                              % (_key(row), plat, status, parity.STATUSES))
                bad = True
        if bad:
            row["verdict"], row["owner"], row["issue"], row["basis"] = (
                "ERROR", "", None, "")
            continue
        # Pair verdict for qemu <-> gem5.  The long-tail/canonical rows carry no
        # per-scope architecture-visible payload, so the empty scope compares
        # status + exit only (`run_parity._norm_visible` -> {}).
        row["verdict"] = parity._verdict("", row["qemu"], row["gem5"])
        row["owner"], row["issue"], row["basis"] = _attribute(row, errors)
        chip = row["chipyard"]
        if chip.get("status") == "N/A":
            basis = chip.get("basis") or ""
            if not basis:
                errors.append("%s: chipyard N/A without a basis (N/A must point "
                              "at why the platform is unusable)" % _key(row))
            row["chipyard_verdict"] = "N/A"
            row["chipyard_basis"] = basis
            continue
        row["chipyard_verdict"] = _CHIPYARD_VERDICT[
            parity._verdict("", row["qemu"], chip)]
        if row["chipyard_verdict"] != "AGREE_PASS":
            owner = chip.get("owner")
            if owner not in se.OWNERS:
                errors.append("%s: chipyard %s/%s has no owner outside %s"
                              % (_key(row), chip.get("status"),
                                 chip.get("exit"), se.OWNERS))
            elif not chip.get("basis"):
                errors.append("%s: chipyard %s needs a non-empty basis"
                              % (_key(row), row["chipyard_verdict"]))
            row["chipyard_owner"] = owner if owner in se.OWNERS else ""
            row["chipyard_basis"] = chip.get("basis") or ""
        else:
            row["chipyard_owner"] = ""
            row["chipyard_basis"] = ""
    return errors


def build(sources, chipyard_docs):
    rows, errors = _merge(sources, chipyard_docs)
    for src in sources:
        _check_declared(src, errors)
    errors += judge(rows)
    return rows, errors


# ---------------------------------------------------------------------------
# counts
# ---------------------------------------------------------------------------

def _counts(rows):
    per = {}
    verdicts = {}
    owners = {}
    for row in rows:
        for plat in PLATFORMS:
            c = per.setdefault((row["link_mode"], plat), {})
            status = (row.get(plat) or {}).get("status")
            c[status] = c.get(status, 0) + 1
        key = (row["link_mode"], row["verdict"])
        verdicts[key] = verdicts.get(key, 0) + 1
        if row["verdict"] != "AGREE_PASS":
            okey = (row["link_mode"], "qemu↔gem5", row["owner"] or "—",
                    row["issue"] or "—", row["basis"])
            owners[okey] = owners.get(okey, 0) + 1
        if row.get("chipyard_verdict") not in (None, "N/A", "AGREE_PASS"):
            ckey = (row["link_mode"], "chipyard↔qemu",
                    row.get("chipyard_owner") or "—", "—",
                    row.get("chipyard_basis") or "")
            owners[ckey] = owners.get(ckey, 0) + 1
    return per, verdicts, owners


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def _cell(rec):
    status = rec.get("status")
    exit_code = rec.get("exit")
    text = "%s/%s" % (status, "—" if exit_code is None else exit_code)
    if rec.get("gap"):
        text += "（%s）" % rec["gap"]
    return text


def _fp(fingerprint, key):
    value = fingerprint.get(key)
    if value is None or value == "":
        return "—"
    if isinstance(value, dict):
        return ", ".join("%s=`%s`" % (k, _fp({"v": v}, "v"))
                         for k, v in sorted(value.items()))
    if isinstance(value, bool):
        return "true" if value else "false"
    if key in ("gem5_binary", "qemu_binary"):
        return os.path.basename(str(value))
    return str(value)


def render(rows, sources):
    per, verdicts, owners = _counts(rows)
    tracks = []
    for src in sources:
        if src["track"] not in tracks:
            tracks.append(src["track"])
    for track in sorted({row["link_mode"] for row in rows}):
        if track not in tracks:
            tracks.append(track)
    lines = [SNAPSHOT_MARKER, "",
             "# M13 三平台差分矩阵（qemu / gem5 / chipyard）", ""]
    data_time = "、".join(
        "`%s %s`" % (s["track"], s["generated_utc"] or "—") for s in sources)
    lines.append("- **生成时间**：基线数据时间 %s（本册由已入库 JSON 确定性重建，"
                 "重建时刻不入册）" % data_time)
    lines.append("- **数据来源**：已入库 M13 长尾基线 %d 份（%s）：%s；"
                 "chipyard 列未就绪（见 §5）"
                 % (len(sources), " / ".join("`%s`" % s["track"]
                                            for s in sources),
                    "、".join("`%s`" % _display(s["path"])
                             for s in sources)))
    lines.append("- **覆盖范围**：%d 行（%s 档）；`inst`/FP 差分由 "
                 "`m13-integ-002`/`003` 以 `--source` 追加，chipyard 列未就绪（§5）"
                 % (len(rows), " / ".join("`%s`" % s["track"]
                                          for s in sources)))
    lines.append("- **机器指纹**：见 §6「机器指纹（逐源，不合并）」——CPU 型号 / "
                 "引擎 md5+版本 / 源码 tree hash / driver md5")
    lines.append("- **复现命令**：`python3 tools/testcases/parity/"
                 "three_platform_matrix.py --markdown-out <运行期目录>/"
                 "m13-三平台差分矩阵.md`；入库册用 `--check` 校验逐字节一致（§7）")
    lines.append("")
    lines.append("> 生成器 `tools/testcases/parity/three_platform_matrix.py`：行、"
                 "计数、判定、归因全部由输入 JSON 复算，不信任任何已声明判定；"
                 "非 PASS 行无 owner 即非零退出。")
    lines.append("> 三平台列 = `qemu`（qemu-user）/ `gem5`（gem5 SE）/ "
                 "`chipyard`（未就绪 ⇒ `N/A`）。配对硬门 `QEMU PASS ⇒ gem5 PASS`"
                 "（`ADR-0048 D1/D2/D5`）。")
    lines.append("")
    lines.append("## 1. 列结构（schema）")
    lines.append("")
    lines.append("| 列 | 含义 | 来源 |")
    lines.append("| --- | --- | --- |")
    lines.append("| `档`（`link_mode`） | 基线的跑法/选例档（`static` / `dynamic`；"
                 "后续任务可自定义） | 输入 JSON |")
    lines.append("| `suite` / `case` | 冻结的用例身份（`libc-test` / `llvm-ts` / "
                 "`embench` / `inst`…） | 输入 JSON |")
    lines.append("| `qemu` | qemu 侧 `status/exit` | 输入 JSON |")
    lines.append("| `gem5` | gem5 侧 `status/exit`（`BLOCKED` 带 `gap` 标签） | "
                 "输入 JSON |")
    lines.append("| `chipyard` | chipyard 侧 `status/exit`；核未就绪时 `N/A`"
                 "（依据见 §5） | 输入 JSON / `N/A` 默认 |")
    lines.append("| `判定` | `qemu ↔ gem5` 配对判定，从行复算（"
                 "`AGREE_PASS` / `GEM5_ONLY_FAIL` / `DIFF` / …） | "
                 "`run_parity._verdict` |")
    lines.append("| `owner` / `issue` | 非 PASS 行的归因层与台账号 | 本脚本登记表"
                 " + 输入 JSON |")
    lines.append("")
    lines.append("`status` = 驱动判定（对 reference 比对），`exit` = 宿主退出码；"
                 "两者不必同向（`llvm-ts` 的 reference 把 `exit N` 也纳入 md5，"
                 "非 0 退出同样可以 `PASS`）。"
                 "`BLOCKED` 是能力/预算缺口，永不改写成 `PASS`。")
    lines.append("")
    lines.append("## 2. 汇总（现场统计）")
    lines.append("")
    lines.append("| 档 | 平台 | total | " + " | ".join(_COUNT_STATUSES)
                 + " | 其他 |")
    lines.append("| --- | --- | " + " | ".join(["---"] * 8) + " |")
    for track in tracks:
        for plat in PLATFORMS:
            c = per.get((track, plat), {})
            total = sum(c.values())
            shown = sum(c.get(s, 0) for s in _COUNT_STATUSES)
            lines.append("| %s | %s | %d | %s | %d |" % (
                track, plat, total,
                " | ".join(str(c.get(s, 0)) for s in _COUNT_STATUSES),
                total - shown))
    lines.append("")
    lines.append("| 档 | " + " | ".join(_VERDICT_KEYS) + " | 合计 |")
    lines.append("| --- | " + " | ".join(["---"] * (len(_VERDICT_KEYS) + 1))
                 + " |")
    for track in tracks:
        vals = [verdicts.get((track, v), 0) for v in _VERDICT_KEYS]
        lines.append("| %s | %s | %d |" % (track, " | ".join(str(v) for v in vals),
                                          sum(vals)))
    lines.append("")
    lines.append("## 3. 逐例矩阵（全量行，不抽样）")
    lines.append("")
    lines.append("| 档 | suite | case | qemu | gem5 | chipyard | 判定 | "
                 "chipyard 判定 | owner | issue |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        lines.append("| %s | %s | `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
            row["link_mode"], row["suite"], row["case"],
            _cell(row["qemu"]), _cell(row["gem5"]), _cell(row["chipyard"]),
            row["verdict"], row.get("chipyard_verdict", "—"),
            row["owner"] or "—", row["issue"] or "—"))
    lines.append("")
    lines.append("## 4. 归因汇总（非 PASS 行必须有 owner）")
    lines.append("")
    lines.append("| 档 | 配对 | owner | issue | 行数 | 依据 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for (track, pair, owner, issue, basis), count in sorted(owners.items()):
        lines.append("| %s | %s | %s | %s | %d | %s |" % (
            track, pair, owner, issue, count,
            (basis or "—").replace("|", "/")))
    lines.append("")
    lines.append("## 5. chipyard 列（`N/A` 依据）")
    lines.append("")
    chip_rows = [r for r in rows if r["chipyard"].get("status") == "N/A"]
    lines.append("- `N/A` 行数：%d / %d（现场统计）" % (len(chip_rows), len(rows)))
    lines.append("- 依据：%s" % CHIPYARD_BASIS)
    lines.append("- 填列方式：`m13-integ-002`/`003` 产出 canonical JSON 后，用 "
                 "`--source`（内嵌 chipyard 列）或 `--chipyard <json>` 挂上；"
                 "非 `N/A` 行必须带 `owner`（`%s`）与 `basis`，否则生成器非零退出。"
                 % " / ".join(se.OWNERS))
    lines.append("")
    lines.append("## 6. 机器指纹（逐源，不合并）")
    lines.append("")
    for src in sources:
        fp = src["fingerprint"]
        lines.append("- `%s`（`%s`，数据时间 `%s`，sha256 `%s`）：host `%s`；"
                     "CPU `%s`（nproc %s / jobs %s）；gem5 `%s` md5 `%s` 版本 "
                     "`%s`；qemu `%s` md5 `%s` 版本 `%s`；源码 tree hash（musl）"
                     "`%s`（dirty %s）；预算 gem5/qemu %s s / %s s；driver md5 %s"
                     % (src["track"], src["task"], src["generated_utc"] or "—",
                        src["sha256"][:16] + "…", _fp(fp, "host"),
                        _fp(fp, "cpu_model"), _fp(fp, "nproc"),
                        _fp(fp, "jobs"), _fp(fp, "gem5_binary"),
                        _fp(fp, "gem5_md5"), _fp(fp, "gem5_version"),
                        _fp(fp, "qemu_binary"), _fp(fp, "qemu_md5"),
                        _fp(fp, "qemu_version"), _fp(fp, "musl_head"),
                        _fp(fp, "musl_dirty"),
                        _fp(fp, "gem5_timeout_seconds"),
                        _fp(fp, "qemu_timeout_seconds"),
                        _fp(fp, "driver_md5")))
    lines.append("")
    lines.append("## 7. 复现与重建")
    lines.append("")
    lines.append("```sh")
    lines.append("# 从已入库基线重建（fresh clone 即可；默认输入 = 上述 %d 份）"
                 % len(sources))
    lines.append("python3 tools/testcases/parity/three_platform_matrix.py \\")
    lines.append("  --markdown-out <运行期目录>/m13-三平台差分矩阵.md")
    lines.append("")
    lines.append("# 入库册由重建结果写入（或 `cp`），并用 --check 验证逐字节一致")
    lines.append("python3 tools/testcases/parity/three_platform_matrix.py \\")
    lines.append("  --check docs/TestReports/M13-三平台差分矩阵.md")
    lines.append("```")
    lines.append("")
    lines.append("`--source <json>` 追加来源（可多次）；`--chipyard <json>` 单独挂 "
                 "chipyard 证据。同名 `(档, suite, case)` 按平台列合并；同一平台"
                 "给出两个不同 `status`/`exit` 即 FAIL。")
    lines.append("")
    lines.append("## 8. 检查（生成器不变式）")
    lines.append("")
    lines.append("- 行数 = 输入行并集（%d 行，现场统计）；每行 `qemu`/`gem5` 列不可缺。"
                 % len(rows))
    lines.append("- 判定从行复算；`AGREE_PASS` 不需归因，其余行必须命中归因表。")
    lines.append("- `BLOCKED` 的 `gap` 必须登记（`BLOCKED_OWNERS`）；未登记即 FAIL。")
    lines.append("- legacy 基线须 `ok=true`、`missing=[]`，且 `selection.total` / "
                 "`by_suite` 与行一致。")
    lines.append("- `chipyard` 非 `N/A` 行必须带 `owner` + `basis`；`N/A` 必须带依据。")
    lines.append("")
    return "\n".join(lines) + "\n"


def _display(path):
    """Identity path for the committed book: repo-relative or basename.

    `docs/TestReports/README.md §4` forbids runtime absolute paths, and engine
    identity stays anchored by md5/commit, so a path outside the repo is
    rendered as its basename (`run_parity._display_path` does the same).
    """
    return parity._display_path(path)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _synth_source():
    doc = {
        "schema": CANONICAL_SCHEMA, "link_mode": "static", "task": "synth",
        "generated_utc": "2026-01-01T00:00:00Z",
        "fingerprint": {"host": "synth", "cpu_model": "synth-cpu",
                        "gem5_md5": "0" * 32},
        "cases": [
            {"case": "functional/argv", "suite": "libc-test",
             "category": "functional",
             "qemu": {"status": "PASS", "exit": 0},
             "gem5": {"status": "PASS", "exit": 0}},
            {"case": "functional/ipc_msg", "suite": "libc-test",
             "qemu": {"status": "PASS", "exit": 0},
             "gem5": {"status": "BLOCKED", "exit": None,
                      "gap": se.TIMEOUT_CAPABILITY}},
        ],
    }
    return doc


def _synth_legacy(delta=0):
    rows = [{"case": "functional/argv", "suite": "libc-test",
             "qemu_klass": "pass", "qemu_exit": 0,
             "gem5_klass": "pass", "gem5_exit": 0, "gem5_gap": None}]
    total = len(rows) + delta
    return {"task": "synth", "generated_utc": "2026-01-01T00:00:00Z",
            "link_mode": "static", "rows": rows, "ok": True, "missing": [],
            "selection": {"total": total,
                          "by_suite": {"libc-test": len(rows)}}}


def _injections():
    """[(name, mutate(sources, chipyard), needle)] -- every one must be caught."""

    def gem5_only(sources, chip):
        sources[0]["cases"][0]["gem5"] = {"status": "FAIL", "exit": 1}

    def qemu_only(sources, chip):
        sources[0]["cases"][0]["qemu"] = {"status": "FAIL", "exit": 1}

    def unknown_gap(sources, chip):
        sources[0]["cases"][1]["gem5"]["gap"] = "syscall gap"

    def bad_status(sources, chip):
        sources[0]["cases"][0]["qemu"]["status"] = "OK"

    def conflict(sources, chip):
        extra = copy.deepcopy(sources[0])
        extra["cases"] = [{"case": "functional/argv", "suite": "libc-test",
                           "gem5": {"status": "FAIL", "exit": 1}}]
        sources.append(extra)

    def duplicate(sources, chip):
        sources[0]["cases"].append(copy.deepcopy(sources[0]["cases"][0]))

    def legacy_drift(sources, chip):
        sources[0] = _from_doc("<synth-legacy>", _synth_legacy(delta=1))

    def chipyard_fail_no_owner(sources, chip):
        sources[0]["cases"][0]["chipyard"] = {"status": "FAIL", "exit": 1}

    def chipyard_na_no_basis(sources, chip):
        sources[0]["cases"][0]["chipyard"] = {"status": "N/A"}

    def chipyard_unknown_case(sources, chip):
        chip.append(_from_doc(
            "<synth-chipyard>",
            {"schema": CANONICAL_SCHEMA, "link_mode": "static",
             "task": "synth-chipyard",
             "cases": [{"case": "functional/absent", "suite": "libc-test",
                        "chipyard": {"status": "PASS", "exit": 0}}]}))

    def agree_fail(sources, chip):
        sources[0]["cases"][0]["qemu"] = {"status": "FAIL", "exit": 1}
        sources[0]["cases"][0]["gem5"] = {"status": "FAIL", "exit": 1}

    def diff(sources, chip):
        sources[0]["cases"][0]["qemu"] = {"status": "TIMEOUT", "exit": 124}
        sources[0]["cases"][0]["gem5"] = {"status": "TIMEOUT", "exit": 125}

    return [
        ("gem5_only_fail without attribution", gem5_only,
         "GEM5_ONLY_FAIL"),
        ("qemu_only_fail not accepted", qemu_only, "QEMU_ONLY_FAIL"),
        ("blocked with unmapped gap", unknown_gap, "BLOCKED_OWNERS"),
        ("status outside the vocabulary", bad_status, "outside"),
        ("conflicting platform record", conflict, "conflicting"),
        ("duplicate case in one input", duplicate, "duplicate case"),
        ("legacy selection drift", legacy_drift, "selection.total"),
        ("chipyard fail without owner", chipyard_fail_no_owner, "chipyard"),
        ("chipyard N/A without basis", chipyard_na_no_basis,
         "chipyard N/A without a basis"),
        ("chipyard case outside the matrix", chipyard_unknown_case,
         "missing qemu column"),
        ("both engines non-PASS without basis", agree_fail, "admitted basis"),
        ("DIFF without attribution", diff, "DIFF"),
    ]


def self_test():
    ok = True
    sources = [_from_doc("<synth>", _synth_source())]
    rows, errs = build(copy.deepcopy(sources), [])
    if errs:
        ok = False
        print("SELFTEST baseline: FAIL -> %s" % errs[:2])
    else:
        print("SELFTEST baseline: PASS (%d row(s), no problem)"
              % len(rows))
    for name, mutate, needle in _injections():
        doc_sources = copy.deepcopy(sources)
        chip = []
        mutate(doc_sources, chip)
        _rows, problems = build(doc_sources, chip)
        hit = any(needle in p for p in problems)
        print("[SELFTEST] %s: %s" % (name, "PASS (detected)" if hit
                                     else "FAIL (not detected; got %r)"
                                     % (problems[:2],)))
        if not hit:
            ok = False
    print("--self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _guard_repo_write(path, allow):
    if not path:
        return
    full = os.path.abspath(path)
    repo = os.path.abspath(_REPO_ROOT)
    if full.startswith(repo + os.sep) and not allow:
        raise SetupError("refusing to write inside the repo without "
                         "--allow-repo-write: %s" % path)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="qemu / gem5 / chipyard 三平台差分矩阵（M13 骨架）")
    ap.add_argument("--source", action="append", default=None,
                    help="canonical 三平台输入 JSON（可多次；默认 = 已入库的 "
                         "m13 长尾两份基线）")
    ap.add_argument("--chipyard", action="append", default=[],
                    help="chipyard 证据 JSON（canonical，只带 chipyard 列）")
    ap.add_argument("--markdown-out", default=None,
                    help="册输出（运行期目录）；入库册只由证据脚本 cp")
    ap.add_argument("--check", default=None,
                    help="校验现册与重建结果逐字节一致（不一致 rc=1）")
    ap.add_argument("--allow-repo-write", action="store_true",
                    help="允许 --markdown-out 写进仓库（默认拒绝）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    try:
        if args.self_test:
            return self_test()
        _guard_repo_write(args.markdown_out, args.allow_repo_write)
        paths = args.source or list(DEFAULT_SOURCES)
        sources = [load_source(p) for p in paths]
        chip_docs = [load_source(p) for p in args.chipyard]
        rows, errors = build(sources, chip_docs)
        if errors:
            for err in errors:
                print("FAIL: " + err)
            print("three_platform_matrix: FAIL (%d issue(s))" % len(errors))
            return 1
        text = render(rows, sources)
        if args.check:
            if not os.path.isfile(args.check):
                raise SetupError("--check target not found: %s" % args.check)
            with open(args.check, "r", encoding="utf-8") as fh:
                have = fh.read()
            if have != text:
                print("check: FAIL -- %s differs from the rebuilt book "
                      "(%d vs %d bytes)" % (args.check, len(have), len(text)))
                return 1
            print("check: PASS (%s is byte-identical to the rebuilt book)"
                  % args.check)
            return 0
        if args.markdown_out:
            os.makedirs(os.path.dirname(os.path.abspath(args.markdown_out)),
                        exist_ok=True)
            with open(args.markdown_out, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("markdown: %s" % args.markdown_out)
        else:
            sys.stdout.write(text)
        print("three_platform_matrix: PASS (%d row(s), %d source(s))"
              % (len(rows), len(sources)))
        return 0
    except SetupError as exc:
        print("three_platform_matrix: SETUP ERROR: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
