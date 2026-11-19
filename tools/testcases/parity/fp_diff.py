#!/usr/bin/env python3
"""fp_diff.py -- 浮点三平台逐例差分报告（`m13-integ-002`）.

本脚本**不跑 guest**：输入是 `run_asm_suite.py` 的三平台逐镜像 JSON（每镜像
`status/exit/结果字节流` 已由同一 ELF 产生）+ 每镜像的 `.out` 结果字节流（逐检查点
切 8 字节），再加上三个静态真源：

  * `contracts/opcodes.yaml`（机器可读 FP 指令集：`scope: fp`，现场计数）；
  * `spec/SimRISC-07-浮点运算.md` 附录 A（人读排版口径）；
  * `tests/inst.yaml`（用例索引：载体是否入库登记）。

输出 `tests/data/m13-002-fp-diff.{json,md}`（入库基线的落点），内容是上述输入的**确定性
函数**：不写生成时刻、不写运行期路径，`--check` 在 fresh clone 上可逐字节复现。

复用（不复制另一套口径）：

  * 载体用例行/故障例解析 = `tests/ee-tiny/run_inst_tiny.py::scan_source`
    （检查点数、故障点数、点号连续性）；
  * owner 词表 = `tests/ee-user/tset_matrix_user.py::OWNERS`。
    **平台状态词表不另立**：状态由 `rc` 现场派生（`0` ⇒ `PASS`，非 `0` ⇒ `FAIL`），
    三平台判定 = 本脚本 `classify`（不 import `run_parity`，其 `STATUSES` 是 SE 侧词表）。

判定（fail-closed）：

  * 三个平台必须都在每个镜像记录里；缺平台 / 未知 id / 重复记录 / 点号与载体
    不符 ⇒ 非零退出；
  * 每个非 `AGREE_PASS` 镜像/检查点必须命中显式归因表（`spec` / `implementation`
    / `test asset` / `environment` / `budget`），未归因即 rc=1；
  * `ISS-357`（SE 双 fd 输出顺序）与 picolibc `math_test` 是**已登记已知项**，
    单列在 `known_items`，不参与 FP 语义差异计数。

用法::

    python3 tools/testcases/parity/fp_diff.py \\
        --run fp-book=<run.json> --work fp-book=<work-dir> \\
        --run fp-extras=<run2.json> --work fp-extras=<work-dir2> \\
        --engine qemu=<md5> --engine gem5=<md5> --engine chipyard=<md5> \\
        --json-out <运行期>/m13-002-fp-diff.json \\
        --markdown-out <运行期>/m13-002-fp-diff.md

    --check <md|json>   与落盘报告逐字节比对（不符 rc=1；缺文件 rc=2）
    --input-commit <sha> 报告记录/比较的输入 commit（缺省 `git rev-parse HEAD`）
    --self-test         合成输入 + 全类反例，逐条要求被判出；全判出才 rc=0

报告记 **输入 commit**（`--input-commit`，缺省 `git rev-parse HEAD`）：没有这个锚，
后人只能靠 `--check` 发现报告陈旧（`m13-integ-003` 复核 F3）。`--check` 因此要求
在同一 commit 上复算（或显式传同一 sha）。

退出码：0 不变式全成立；1 不变式失败（差异未归因 / 缺平台 / 计数不符 /
`--check` 不一致 / 自检有注入未判出）；2 setup 错（缺文件、坏 JSON、坏参数）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
for _p in (str(_HERE), str(_REPO / "tools" / "infra"),
           str(_REPO / "tests" / "ee-tiny"),
           str(_REPO / "tests" / "ee-user")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tset_matrix_user as se        # noqa: E402  (owner 词表)
import run_inst_tiny as asm          # noqa: E402  (载体现场统计)

SCHEMA = "fp-three-platform-diff/1"
TASK = "m13-integ-002"
PLATFORMS = ("qemu", "gem5", "chipyard")
OWNERS = se.OWNERS
MODES = ("0 RNE", "1 RTZ", "2 RDN", "3 RUP")
FLAG_BITS = (("NV", 0x01), ("DZ", 0x02), ("OF", 0x04), ("UF", 0x08),
             ("NX", 0x10))
CATEGORIES = ("NONE", "NV", "DZ", "OF", "UF", "NX")

#: 结果依赖 `rf0[33:32]` 的助记符（算术 / FMA / scaleB / 开方 / 取整；比较、
#: 最小最大、符号、分类、复制不涉舍入）。转换类的静态 `immu6` 档不读 `rf0`，
#: 只有动态档 `0x20` 读；矩阵的 `rf0_sensitive` = 本集合 ∪ `immu6 == 0x20`
#: 的转换/取整点，避免把「环境档」冒充「舍入受控」。
RF0_SENSITIVE = frozenset({
    "ftadd", "ftsub", "ftmul", "ftdiv", "ftsclb", "foadd", "fosub",
    "fomul", "fodiv", "fosclb", "ftfma", "fofma", "ftroot", "foroot",
    "ftrnd", "fornd",
})

#: 链例宏 -> (助记符下标, rf0 舍入档下标, 期望标志下标)；下标含点号自身（0）。
#: 与 `tests/inst/macros/inst_test.inc` 的宏参数顺序逐条对齐；未知/漂移即 fail-closed。
CHAIN_MACROS = {
    "TEST_FP3": dict(mnem=2, rm=8, flags=10),
    "TEST_FP4": dict(mnem=2, rm=10, flags=12),
    "TEST_FPROOT": dict(mnem=2, rm=7, flags=9),
    "TEST_FPENC": dict(mnem=None, rm=None, flags=9),
    "TEST_FPENC4": dict(mnem=None, rm=None, flags=11),
    "TEST_FPENC_ROOT": dict(mnem=None, rm=None, flags=7),
    "TEST_FPCVT_F2I": dict(mnem=1, rm=6, flags=8, cvt=5),
    "TEST_FPCVT_I2F": dict(mnem=2, rm=7, flags=9, cvt=6),
    "TEST_FPCVT_F2F": dict(mnem=2, rm=7, flags=9, cvt=6),
    "TEST_FPCVT_ENC_RD": dict(mnem=None, rm=None, flags=6),
    "TEST_FPCVT_ENC_RF": dict(mnem=None, rm=None, flags=7),
    "TEST_FPCVT_ENC_F2F": dict(mnem=None, rm=None, flags=7),
    "TEST_FPCMP": dict(mnem=1, rm=None, flags=8),
    "TEST_FPCMP_ENC": dict(mnem=None, rm=None, flags=8),
    "TEST_FPSGN": dict(mnem=1, rm=None, flags=8),
    "TEST_FPSGN_ENC": dict(mnem=None, rm=None, flags=8),
    "TEST_FPSCLB": dict(mnem=1, rm=7, flags=9),
    "TEST_FPSCLB_ENC": dict(mnem=None, rm=7, flags=9),
    "TEST_FPRND": dict(mnem=1, rm=6, flags=8, cvt=5),
    "TEST_FPRND_ENC": dict(mnem=None, rm=5, flags=7),
}
NO_FLAG_MACRO_PREFIXES = ("TEST_FPCLS", "TEST_FPCOPY")


class SetupError(Exception):
    """缺文件 / 坏 JSON / 坏参数（rc=2）。"""


class DiffError(Exception):
    """不变式失败（rc=1）。"""


# ---------------------------------------------------------------------------
# 静态真源
# ---------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_yaml(path: Path):
    try:
        import yaml
    except ImportError as exc:                 # pragma: no cover
        raise SetupError(f"PyYAML required: {exc}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except OSError as exc:
        raise SetupError(f"{path}: {exc}")


def load_scope(path: Path) -> list[dict]:
    """`contracts/opcodes.yaml` 的 `scope: fp` 条目（机器可读计数口径）。"""
    doc = _load_yaml(path)
    if not isinstance(doc, list):
        raise SetupError(f"{path}: opcodes.yaml is not a list")
    rows = [r for r in doc if isinstance(r, dict) and r.get("scope") == "fp"]
    if not rows:
        raise SetupError(f"{path}: no scope:fp entry")
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise SetupError(f"{path}: duplicate scope:fp ids")
    return sorted(rows, key=lambda r: r["id"])


def load_appendix_a(path: Path) -> list[str]:
    """`spec/SimRISC-07` 附录 A 的指令 id 列表（人读排版口径）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError(f"{path}: {exc}")
    block = re.search(r"<!-- ASSEMBLY_LIST_START -->(.*?)"
                      r"<!-- ASSEMBLY_LIST_END -->", text, re.S)
    if not block:
        raise SetupError(f"{path}: no ASSEMBLY_LIST block")
    ids = re.findall(r"^\| `[^`]+` \|[^|]*\|[^|]*\|[^|]*\| `([^`]+)` \|",
                     block.group(1), re.M)
    if not ids:
        raise SetupError(f"{path}: appendix A has no instruction row")
    if len(ids) != len(set(ids)):
        raise SetupError(f"{path}: duplicate ids in appendix A")
    return sorted(ids)


def load_index(path: Path) -> dict:
    doc = _load_yaml(path)
    if not isinstance(doc, list):
        raise SetupError(f"{path}: tests index is not a list")
    out = {}
    for entry in doc:
        if not isinstance(entry, dict) or "file" not in entry:
            raise SetupError(f"{path}: malformed entry {entry!r}")
        out.setdefault(entry["file"], []).append(entry)
    return out


# ---------------------------------------------------------------------------
# 载体：现场解析链例（点号 / 舍入档 / 期望标志）
# ---------------------------------------------------------------------------
def _int_literal(tok: str, where: str) -> int:
    tok = tok.strip()
    if not re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", tok):
        raise DiffError(f"{where}: not an integer literal: {tok!r}")
    return int(tok, 0)


def parse_points(src: Path) -> list[dict]:
    """按文件顺序解析链例行；点号必须 1..N 连续且与 `scan_source` 计数一致。"""
    points = []
    for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^\t([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$", line)
        if not m:
            continue
        macro = m.group(1)
        no_flag = macro.startswith(NO_FLAG_MACRO_PREFIXES)
        if macro not in CHAIN_MACROS and not no_flag:
            continue
        args = [a.strip() for a in m.group(2).split("@@")[0].split(",")]
        where = f"{src.name}:{lineno}"
        if len(args) < 2:
            raise DiffError(f"{where}: {macro} has too few arguments")
        pt = _int_literal(args[0], where)
        if no_flag:
            points.append(dict(pt=pt, rm=0, flags=0, mnemonic=macro,
                               immu6=None, where=where))
            continue
        spec = CHAIN_MACROS[macro]
        if spec["flags"] >= len(args):
            raise DiffError(f"{where}: {macro} has no flags argument")
        flags = _int_literal(args[spec["flags"]], where)
        rm = _int_literal(args[spec["rm"]], where) \
            if spec["rm"] is not None else 0
        mnem = args[spec["mnem"]] if spec["mnem"] is not None else None
        if mnem is not None and not re.fullmatch(r"[a-z0-9.]+", mnem):
            raise DiffError(f"{where}: bad mnemonic {mnem!r}")
        if rm not in (0, 1, 2, 3):
            raise DiffError(f"{where}: rf0 rounding {rm} outside 0..3")
        if flags & ~0x1F:
            raise DiffError(f"{where}: flags {flags:#x} outside rf0[4:0]")
        cvt = (_int_literal(args[spec["cvt"]], where)
               if spec.get("cvt") is not None else None)
        points.append(dict(pt=pt, rm=rm, flags=flags, mnemonic=mnem,
                           immu6=cvt, where=where))
    pts = [p["pt"] for p in points]
    if pts != list(range(1, len(points) + 1)):
        raise DiffError(f"{src.name}: chain point numbers are not 1..N "
                        f"({pts[:8]}...)")
    return points


def build_coverage(scope, appendix_ids, index, tests_root: Path) -> dict:
    by_stem = {}
    for path in sorted(tests_root.glob("inst/**/*.S")):
        by_stem.setdefault(path.stem, []).append(path)
    scope_ids = {r["id"] for r in scope}
    appendix = set(appendix_ids)
    unknown = appendix - scope_ids
    if unknown:
        raise DiffError(f"appendix A id(s) not in scope:fp: {sorted(unknown)}")
    rows = []
    gaps = []
    for entry in scope:
        oid = entry["id"]
        carriers = by_stem.get(oid, [])
        row = dict(id=oid, mnemonic=entry["mnemonic"],
                   format=entry.get("format"),
                   kind="fp_arithmetic" if oid in appendix else "fp_extended",
                   carrier=None, chain_points=None, fault_cases=None,
                   pts_ok=None, indexed=False, index_ids=[])
        if len(carriers) > 1:
            raise DiffError(f"{oid}: multiple .S carriers: {carriers}")
        if not carriers:
            gaps.append(dict(id=oid, kind="no_carrier",
                             detail=f"{entry['mnemonic']} has no tests/inst/**/"
                                    f"{oid}.S carrier"))
            rows.append(row)
            continue
        carrier = carriers[0]
        rel = carrier.relative_to(tests_root).as_posix()
        scan = asm.scan_source(carrier)
        row.update(carrier="tests/" + rel, chain_points=scan["checks"],
                   fault_cases=len(scan["faults"]), pts_ok=scan["pts_ok"])
        if not scan["pts_ok"]:
            gaps.append(dict(id=oid, kind="points_not_contiguous",
                             detail=rel))
        if oid in appendix:
            points = parse_points(carrier)
            if len(points) != scan["checks"]:
                raise DiffError(f"{oid}: parsed {len(points)} chain point(s) "
                                f"but scan_source counted {scan['checks']}")
            row["point_modes"] = points
        hits = index.get(rel, [])
        row["indexed"] = bool(hits)
        row["index_ids"] = sorted(h["id"] for h in hits)
        if not hits:
            gaps.append(dict(id=oid, kind="not_indexed",
                             detail=f"{rel} missing from tests/inst.yaml"))
        rows.append(row)
    return dict(total=len(scope), with_carrier=sum(1 for r in rows if r["carrier"]),
                with_index=sum(1 for r in rows if r["indexed"]),
                arithmetic=len(appendix),
                gaps=gaps, rows=rows)


# ---------------------------------------------------------------------------
# 运行输入：三平台逐镜像记录
# ---------------------------------------------------------------------------
def load_run(label: str, path: Path, known_ids, checks_by_id) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SetupError(f"{label}: {path}: {exc}")
    if doc.get("schema") != "inst-asm-suite/1":
        raise SetupError(f"{label}: schema {doc.get('schema')!r} != "
                         f"'inst-asm-suite/1'")
    records = doc.get("records")
    if not isinstance(records, list) or not records:
        raise SetupError(f"{label}: no records")
    for rec in records:
        stem = Path(rec.get("file", "")).stem
        where = f"{label}:{rec.get('file')}#{rec.get('case_n')}"
        if stem not in known_ids:
            raise DiffError(f"{label}: record for unknown id {rec.get('file')!r}")
        platforms = rec.get("platforms") or {}
        if set(platforms) != set(PLATFORMS):
            raise DiffError(f"{where}: platforms {sorted(platforms)} != "
                            f"{PLATFORMS}")
        for plat in PLATFORMS:
            if not isinstance(platforms[plat].get("rc"), int):
                raise DiffError(f"{where}: {plat} rc missing")
        # `ok` is the runner's own verdict; re-derive it here so a tampered /
        # stale boolean cannot turn a real platform split into a pass.
        rcs = [platforms[p]["rc"] for p in PLATFORMS]
        if rec["kind"] == "chain":
            nbytes = [platforms[p].get("bytes") for p in PLATFORMS]
            want = 8 * checks_by_id[stem]
            derived = (set(rcs) == {0} and len(set(nbytes)) == 1
                       and nbytes[0] == want)
        elif rec["kind"] == "fault":
            code = asm.FAULT_CODE.get(rec.get("expected"))
            derived = code is not None and set(rcs) == {code}
        else:
            raise DiffError(f"{where}: unknown kind {rec['kind']!r}")
        if bool(rec.get("ok")) != derived:
            raise DiffError(f"{where}: ok={rec.get('ok')} contradicts the "
                            f"platform records (rc={rcs})")
        rec["_label"] = label
    return records


def merge_runs(items) -> list[dict]:
    merged = {}
    for label, path, known_ids, checks_by_id in items:
        for rec in load_run(label, path, known_ids, checks_by_id):
            key = (Path(rec["file"]).stem, rec["case_n"])
            if key in merged:
                raise DiffError(f"duplicate run record {key}")
            merged[key] = rec
    return [merged[k] for k in sorted(merged)]


def classify(rec) -> str:
    plats = rec["platforms"]
    rcs = {p: plats[p]["rc"] for p in PLATFORMS}
    if rec["ok"]:
        return "AGREE_PASS"
    if rec["kind"] == "fault":
        expected = asm.FAULT_CODE.get(rec.get("expected"))
        if expected is not None and all(rc == expected for rc in rcs.values()):
            return "AGREE_FAIL"           # 三方一致但不是期望故障码
        return "DIFF"
    if all(rc == 0 for rc in rcs.values()):
        return "DIFF"                     # 退出码同 0 但结果字节流不同
    if len(set(rcs.values())) == 1:
        return "AGREE_FAIL"               # 三方同点失败（语义/资产问题，非平台差异）
    return "DIFF"


def _read_out(work_root: Path, stem: str, plat: str, case_n: int) -> bytes:
    stem_full = stem if case_n == 0 else f"{stem}_fault{case_n:03d}"
    path = work_root / stem / f"{stem_full}.{plat}.out"
    return path.read_bytes() if path.is_file() else b""


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def chain_byte_errors(records) -> list[str]:
    """`AGREE_PASS` 链例镜像：三平台 `.out` 必须**逐字节相等**（F2）。

    `load_run` 只能核 runner 声明的 `rc`/`bytes`（计数），内容相等过去只由 runner
    的 `ok` 布尔承担 —— 一份陈旧/被篡改的 `ok=True` 即使三方字节流不同也能蒙混。
    这里直接读三份结果流比较（`rec["_work"]` 必须已由 `build` 设好），并核对
    长度 = `8 × 检查点数`（点数取自载体现场统计，不读 runner）。
    """
    errs = []
    for rec in records:
        if rec.get("kind") != "chain" or not rec.get("ok"):
            continue
        stem = Path(rec["file"]).stem
        blobs = {p: _read_out(rec["_work"], stem, p, rec["case_n"])
                 for p in PLATFORMS}
        if len(set(blobs.values())) != 1:
            errs.append(f"{stem}#{rec['case_n']}: AGREE_PASS but the three "
                        f"platform byte streams differ")
            continue
        want = 8 * int(rec.get("expected") or 0)
        if len(blobs[PLATFORMS[0]]) != want:
            errs.append(f"{stem}#{rec['case_n']}: AGREE_PASS but the result "
                        f"stream is {len(blobs[PLATFORMS[0]])} B, expected "
                        f"8 x {rec.get('expected')} = {want} B")
    return errs


def resolve_input_commit(explicit: str | None) -> str:
    """报告必须记生成时的输入 commit（`m13-integ-003` 复核 F3：否则无法判陈旧）。"""
    if explicit:
        return explicit.strip()
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_REPO),
                              capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SetupError("--input-commit not given and `git rev-parse HEAD` "
                         f"failed: {exc}")
    sha = done.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        raise SetupError(f"git rev-parse HEAD returned {sha!r}")
    return sha


def point_analysis(rec, points, work_root: Path) -> list[dict]:
    blobs = {p: _read_out(work_root, Path(rec["file"]).stem, p, rec["case_n"])
             for p in PLATFORMS}
    out = []
    for point in points:
        k = point["pt"]
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
        out.append(dict(point=k, rm=point["rm"], flags=point["flags"],
                        mnemonic=point["mnemonic"], agree=agree,
                        platforms=chunk))
    return out


# ---------------------------------------------------------------------------
# 归因登记表（每条差异必须命中；未登记 ⇒ 报告 FAIL）
# ---------------------------------------------------------------------------
#: key = (id, case_n)。`spec_cite` 必须指到 `spec/` 的具体条目；`owner` ∈ OWNERS。
ATTRIBUTIONS: dict[tuple[str, int], dict] = {}


def _attr_key(rec):
    return (Path(rec["file"]).stem, rec["case_n"])


def attribute(rec, point=None) -> dict | None:
    entry = ATTRIBUTIONS.get(_attr_key(rec))
    if entry is None:
        return None
    if entry.get("owner") not in OWNERS:
        return None
    out = dict(entry)
    out["point"] = None if point is None else point["point"]
    return out


# ---------------------------------------------------------------------------
# 分析
# ---------------------------------------------------------------------------
def analyse(scope_rows, coverage, records):
    errors = []
    by_id = {r["id"]: r for r in scope_rows}
    for rec in records:
        oid = Path(rec["file"]).stem
        if oid not in by_id:
            errors.append(f"run record for id {oid} not in coverage")
    images = []
    diffs = []
    agree_fail = []
    for rec in sorted(records, key=lambda r: (Path(r["file"]).stem,
                                              r["case_n"])):
        oid = Path(rec["file"]).stem
        verdict = classify(rec)
        images.append(dict(id=oid, case_n=rec["case_n"], kind=rec["kind"],
                           expected=rec.get("expected"),
                           verdict=verdict,
                           platforms={p: dict(
                               status="PASS"
                               if rec["platforms"][p]["rc"] == 0 else "FAIL",
                               exit=rec["platforms"][p]["rc"],
                               bytes=rec["platforms"][p].get("bytes"),
                               md5=_md5(_read_out(rec["_work"], oid, p,
                                                  rec["case_n"])))
                               for p in PLATFORMS},
                           notes=rec.get("notes") or []))
        if verdict == "AGREE_FAIL":
            agree_fail.append(dict(id=oid, case_n=rec["case_n"],
                                   kind=rec["kind"],
                                   expected=rec.get("expected"),
                                   exits={p: rec["platforms"][p]["rc"]
                                          for p in PLATFORMS}))
        if verdict == "DIFF":
            point_notes = []
            row = by_id.get(oid) or {}
            points = row.get("point_modes") or []
            if rec["kind"] == "chain" and points:
                point_notes = point_analysis(rec, points, rec["_work"])
            bad_points = [p for p in point_notes if not p["agree"]]
            attr = attribute(rec, bad_points[0] if bad_points else None)
            diffs.append(dict(
                id=oid, case_n=rec["case_n"], kind=rec["kind"],
                expected=rec.get("expected"),
                observed={p: dict(rc=rec["platforms"][p]["rc"],
                                  bytes=rec["platforms"][p].get("bytes"))
                          for p in PLATFORMS},
                points=[dict(point=p["point"], rm=p["rm"], flags=p["flags"],
                             mnemonic=p["mnemonic"],
                             platforms=p["platforms"])
                        for p in bad_points],
                attribution=attr))
    unattributed = [d for d in diffs if d["attribution"] is None]
    for d in unattributed:
        errors.append(f"{d['id']}#{d['case_n']}: DIFF without an attribution "
                      f"entry")
    for gap in coverage["gaps"]:
        if gap["kind"] in ("no_carrier", "points_not_contiguous"):
            errors.append(f"coverage gap {gap['id']}: {gap['kind']} -- "
                          f"{gap['detail']}")
    return images, diffs, agree_fail, errors


def flags_matrix(scope_rows, confirmed_points, excluded_images):
    """4 档 rf0 舍入 × {NONE,NV,DZ,OF,UF,NX} 的链例点 + 三平台一致计数。

    `confirmed_points` = 来自 `AGREE_PASS` 链例镜像的 `(id, point)` 集合
    （该镜像三方退出码 0 且结果字节流逐字节相同 ⇒ 每个点都三方一致）。
    非 `AGREE_PASS` 镜像的点不计入一致数，由 `excluded_images` 单列。
    """
    agg = {(rm, cat): dict(points=0, agree=0, rf0_sensitive=0)
           for rm in range(4) for cat in CATEGORIES}
    flag_modes = {cat: 0 for cat in CATEGORIES if cat != "NONE"}
    for row in scope_rows:
        points = row.get("point_modes") or []
        for point in points:
            rm = point["rm"]
            cats = ["NONE"] if point["flags"] == 0 else \
                [name for name, bit in FLAG_BITS if point["flags"] & bit]
            agree = (row["id"], point["pt"]) in confirmed_points
            for cat in cats:
                cell = agg[(rm, cat)]
                cell["points"] += 1
                if agree:
                    cell["agree"] += 1
                if (point["mnemonic"] in RF0_SENSITIVE
                        or point.get("immu6") == 0x20):
                    cell["rf0_sensitive"] += 1
                if cat != "NONE":
                    flag_modes[cat] += 1
    cells = [dict(mode=MODES[rm], category=cat, **agg[(rm, cat)])
             for rm in range(4) for cat in CATEGORIES]
    empty = []
    for rm in range(4):
        for cat in CATEGORIES:
            cell = agg[(rm, cat)]
            if cell["points"]:
                continue
            if cat == "NONE":
                reason = ("该舍入档没有 flags=0 的链例点")
            elif flag_modes[cat] == 0:
                reason = ("测试资产缺口：没有任何链例期望该标志位"
                          "（不是引擎差异）")
            else:
                present = [MODES[m] for m in range(4)
                           if agg[(m, cat)]["points"]]
                reason = ("该标志位只在 " + " / ".join(present) +
                          " 档有点（本档无）")
            empty.append(dict(mode=MODES[rm], category=cat, reason=reason))
    return dict(modes=list(MODES), categories=list(CATEGORIES), cells=cells,
                empty=empty, excluded_images=excluded_images)


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------
def build_report(coverage, images, diffs, agree_fail, matrix,
                 engines, sources, errors, notes, input_commit=None):
    report = dict(
        schema=SCHEMA,
        task=TASK,
        input_commit=input_commit,
        scope="scope:fp instruction semantics, qemu system vs gem5 FS vs "
              "chipyard; same ELF per image, per-point 8-byte result records "
              "and rf0[4:0] flag assertions",
        count_criteria=notes["count_criteria"],
        engines=engines,
        sources=sources,
        coverage=coverage,
        results=dict(images=len(images),
                     agree_pass=sum(1 for i in images
                                    if i["verdict"] == "AGREE_PASS"),
                     agree_fail=len(agree_fail),
                     diff=len(diffs),
                     by_id=notes["by_id"],
                     per_image=images),
        differences=dict(attributed=[d for d in diffs
                                     if d["attribution"] is not None],
                         unattributed=[d for d in diffs
                                       if d["attribution"] is None]),
        agree_fail=agree_fail,
        flags_matrix=matrix,
        known_items=notes["known_items"],
        checks=dict(ok=not errors, errors=errors),
    )
    return report


def render_markdown(report) -> str:
    lines = []
    add = lines.append
    add("# m13-integ-002: 浮点指令三平台逐例差分（qemu / gem5 / chipyard）")
    add("")
    add("> 由 `tools/testcases/parity/fp_diff.py` 从已入库输入确定性重建；"
        "不写生成时刻、不写运行期路径。")
    add("")
    cc = report["count_criteria"]
    add("## 0. 计数口径（现场统计）")
    add("")
    add(f"- `contracts/opcodes.yaml` 的 `scope: fp`：**{cc['scope_fp']}** 条"
        "（机器可读口径，本报告的覆盖全集）")
    add(f"- `spec/SimRISC-07` 附录 A：**{cc['appendix_a']}** 行"
        "（人读排版口径；与 scope:fp 的差集 = 8 条 rf 访存 + 3 条 `cs.*` + "
        "`set.w rf` + `rd2rf`/`rf2rd`/`rf2rf`）")
    add(f"- 历史别名「47 条」：**{cc['historical_alias']}** —— 在任何机器可读"
        "源里都复现不出（`issues.yaml` 已登记；47 退役，不再作判据）")
    add("")
    add("## 1. 覆盖（每条 id：载体 / 链例点 / 故障例 / 索引）")
    add("")
    add(f"- scope:fp **{report['coverage']['total']}** 条；有 `.S` 载体 "
        f"**{report['coverage']['with_carrier']}**；在 `tests/inst.yaml` 登记 "
        f"**{report['coverage']['with_index']}**。")
    add("")
    add("| id | 助记符 | 类别 | 载体 | 链例点 | 故障例 | 索引 |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for row in report["coverage"]["rows"]:
        add(f"| `{row['id']}` | `{row['mnemonic']}` | {row['kind']} | "
            f"`{row['carrier'] or '—'}` | {row['chain_points'] if row['chain_points'] is not None else '—'} | "
            f"{row['fault_cases'] if row['fault_cases'] is not None else '—'} | "
            f"{'yes' if row['indexed'] else '**NO**'} |")
    add("")
    gaps = report["coverage"]["gaps"]
    add(f"### 覆盖缺口（{len(gaps)}）")
    add("")
    if gaps:
        for gap in gaps:
            add(f"- `{gap['id']}` — {gap['kind']}：{gap['detail']}")
        add("")
        add("> 缺口按现场统计如实列出，不以 `N/A` 冒充覆盖；"
            "载体存在但未登记索引的条目仍由 L2 `check-inst-asm` 执行。")
    else:
        add("(none)")
    add("")
    add("## 2. 三平台逐例结果")
    add("")
    r = report["results"]
    add(f"- 镜像 **{r['images']}**；三方一致通过 **{r['agree_pass']}**；"
        f"三方一致非通过 **{r['agree_fail']}**；平台差异 **{r['diff']}**。")
    add("")
    add("| id | 链例/故障 | 观测 | 归因 |")
    add("| --- | --- | --- | --- |")
    for d in report["differences"]["attributed"]:
        obs = ", ".join(f"{p}=rc{d['observed'][p]['rc']}"
                        for p in PLATFORMS)
        a = d["attribution"]
        add(f"| `{d['id']}#{d['case_n']}` | {d['kind']} | {obs} | "
            f"{a['owner']} / {a.get('issue') or '—'} / `{a.get('spec_cite', '')}` |")
    for d in report["differences"]["unattributed"]:
        obs = ", ".join(f"{p}=rc{d['observed'][p]['rc']}" for p in PLATFORMS)
        add(f"| `{d['id']}#{d['case_n']}` | {d['kind']} | {obs} | "
            f"**UNATTRIBUTED** |")
    if not report["differences"]["attributed"] and \
            not report["differences"]["unattributed"]:
        add("| — | — | 无平台差异 | — |")
    add("")
    if report["agree_fail"]:
        add("### 三方一致但非通过（测试资产/语义问题，不算平台差异）")
        add("")
        for item in report["agree_fail"]:
            add(f"- `{item['id']}#{item['case_n']}` ({item['kind']}, "
                f"expected {item['expected']}): "
                + ", ".join(f"{p}=rc{rc}"
                            for p, rc in item["exits"].items()))
        add("")
    add("## 3. 舍入方向 × 异常标志矩阵（链例点，4 × 6）")
    add("")
    add("单元 = 该 `rf0[33:32]` 档下期望该标志（或 flags=0）的链例点数 / "
        "三平台逐点一致数；`rf0-sensitive` = 其中舍入真正受 `rf0` 控制的点数。")
    add("")
    add("空白格 = **现有 `.S` 向量没有该组合**（测试资产缺口），不是引擎差异；"
        "本任务不改向量，逐格原因见下。矩阵只统计 `AGREE_PASS` 链例镜像的点，"
        "失败镜像已在 §2 单列。")
    add("")
    add("| rf0[33:32] | " + " | ".join(CATEGORIES) + " |")
    add("| --- | " + " | ".join(["---"] * len(CATEGORIES)) + " |")
    for mode in report["flags_matrix"]["modes"]:
        cells = [c for c in report["flags_matrix"]["cells"]
                 if c["mode"] == mode]
        add("| " + mode + " | " + " | ".join(
            f"{c['points']} / {c['agree']} (rf0 {c['rf0_sensitive']})"
            for c in cells) + " |")
    add("")
    empty = report["flags_matrix"]["empty"]
    add(f"### 空白格说明（{len(empty)}）")
    add("")
    if empty:
        for cell in empty:
            add(f"- {cell['mode']} × {cell['category']}：{cell['reason']}")
    else:
        add("(none)")
    add("")
    add("## 4. 已知项（单列，不混入 FP 语义差异）")
    add("")
    ki = report["known_items"]
    add(f"- `ISS-357`：{ki['ISS-357']['note']}（本差分包 {ki['ISS-357']['applicability']}）")
    add(f"- picolibc `math_test`：{ki['picolibc_math']['note']}"
        f"（{ki['picolibc_math']['applicability']}）")
    add("")
    add("## 5. 输入与可重算")
    add("")
    add(f"- 输入 commit（生成时 HEAD）：`{report.get('input_commit')}`"
        " —— 载体面与报告身份的时间锚；载体面变化后本报告陈旧")
    for key in ("opcodes", "spec_appendix_a", "inst_index"):
        src = report["sources"][key]
        add(f"- `{src['path']}` sha256 `{src['sha256'][:16]}`")
    for item in report["sources"]["runs"]:
        add(f"- run `{item['label']}`：{item['records']} 条记录 "
            f"sha256 `{item['sha256'][:16]}`")
    eng = report["engines"]
    if eng:
        add("")
        add("引擎指纹（md5，报告身份）：")
        for plat in PLATFORMS:
            if plat in eng:
                add(f"- {plat}: `{eng[plat]}`")
    add("")
    add("## 6. 判据")
    add("")
    if report["checks"]["ok"]:
        add("- 每个非 `AGREE_PASS` 差异均已归因；覆盖/索引缺口逐条列出")
    else:
        for err in report["checks"]["errors"]:
            add(f"- FAIL: {err}")
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 自检：每类不变式一条注入，必须都被判出
# ---------------------------------------------------------------------------
def self_test() -> int:
    import tempfile
    checks = []

    def expect(name, fn):
        try:
            fn()
        except (DiffError, SetupError) as exc:
            checks.append((name, True, type(exc).__name__))
        else:
            checks.append((name, False, "not detected"))

    def run_record(payload):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as fh:
            json.dump(dict(schema="inst-asm-suite/1", records=[payload]), fh)
            name = fh.name
        try:
            load_run("synthetic", Path(name), {"ftadd_orrr_rf"},
                     {"ftadd_orrr_rf": 18})
        finally:
            os.unlink(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "inst").mkdir()
        src = root / "inst" / "x.S"
        src.write_text("\tTEST_FP3\t1, ft, ftadd, rf5, rf6, 0x0, rf7, 0x0, 0, "
                       "0x0, 0x00\n\tTEST_FP3\t3, ft, ftadd, rf5, rf6, 0x0, "
                       "rf7, 0x0, 0, 0x0, 0x00\n", encoding="utf-8")
        expect("non-contiguous point numbers", lambda: parse_points(src))
        src2 = root / "inst" / "y.S"
        src2.write_text("\tTEST_FP3\t1, ft, ftadd, rf5, rf6, 0x0, rf7, 0x0, 9, "
                        "0x0, 0x00\n", encoding="utf-8")
        expect("rounding outside 0..3", lambda: parse_points(src2))
        # 覆盖缺口：载体不在索引里
        src3 = root / "inst" / "z.S"
        src3.write_text("\tTEST_FP3\t1, ft, ftadd, rf5, rf6, 0x0, rf7, 0x0, 0, "
                        "0x0, 0x00\n", encoding="utf-8")
        scope = [dict(id="z", mnemonic="ftadd", format="orrr")]
        out = build_coverage(scope, ["z"], {}, root)
        if not out["gaps"]:
            checks.append(("coverage gap detected", False, "no gap"))
        else:
            checks.append(("coverage gap detected", True, "indexed=False"))
        # 空白矩阵格必须有原因
        matrix = flags_matrix(scope + [dict(
            id="x", point_modes=[])],
            set(), [])
        if not matrix["empty"]:
            checks.append(("blank matrix cell explained", False, "no empty"))
        elif any(not c["reason"] for c in matrix["empty"]):
            checks.append(("blank matrix cell explained", False, "empty reason"))
        else:
            checks.append(("blank matrix cell explained", True,
                           f"{len(matrix['empty'])} cell(s)"))

    expect("unknown id in run record", lambda: run_record(dict(
        file="not_an_id.S", case_n=0, kind="chain", expected=1, ok=True,
        platforms={p: dict(rc=0) for p in PLATFORMS})))
    expect("missing platform", lambda: run_record(dict(
        file="ftadd_orrr_rf.S", case_n=0, kind="chain", expected=1, ok=True,
        platforms={"qemu": dict(rc=0)})))

    fake = dict(file="ftadd_orrr_rf.S", case_n=0, kind="chain", expected=1,
                ok=False, platforms={"qemu": dict(rc=0), "gem5": dict(rc=3),
                                     "chipyard": dict(rc=0)})
    if classify(fake) != "DIFF":
        checks.append(("platform split detected", False, classify(fake)))
    else:
        checks.append(("platform split detected", True, "DIFF"))
    if attribute(fake) is not None:
        checks.append(("unattributed DIFF rejected", False, "attributed"))
    else:
        checks.append(("unattributed DIFF rejected", True, "no entry"))

    # F2：链例 `AGREE_PASS` 不能只信 runner 的 `bytes` 计数 —— 三平台结果流必须
    # 逐字节相等且长度 = 8×点数；下面三支分别验证「相等放行 / 内容不符判出 /
    # 长度不符判出」，保证断言有可达 FAIL 路径（不是恒真）。
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "ftadd_orrr_rf").mkdir()
        blob = b"\x00" * 8
        for plat in PLATFORMS:
            (work / "ftadd_orrr_rf" / f"ftadd_orrr_rf.{plat}.out").write_bytes(blob)
        rec = dict(file="ftadd_orrr_rf.S", case_n=0, kind="chain", expected=1,
                   ok=True, _work=work,
                   platforms={p: dict(rc=0, bytes=8) for p in PLATFORMS})
        checks.append(("chain bytes equal accepted",
                       not chain_byte_errors([rec]), "no error"))
        (work / "ftadd_orrr_rf" / "ftadd_orrr_rf.gem5.out").write_bytes(
            b"\x00" * 7 + b"\x01")
        errs = chain_byte_errors([rec])
        checks.append(("chain byte mismatch rejected", bool(errs), errs[:1]))
        short = b"\x00" * 7
        for plat in PLATFORMS:
            (work / "ftadd_orrr_rf" / f"ftadd_orrr_rf.{plat}.out").write_bytes(short)
        errs = chain_byte_errors([rec])
        checks.append(("chain byte length rejected", bool(errs), errs[:1]))

    bad = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"fp_diff self-test: {len(checks) - len(bad)}/{len(checks)} "
          f"{'PASS' if not bad else 'FAIL'}")
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def _parse_kv(items, what):
    out = {}
    for item in items or []:
        if "=" not in item:
            raise SetupError(f"{what}: expected NAME=PATH, got {item!r}")
        key, val = item.split("=", 1)
        if key in out:
            raise SetupError(f"{what}: duplicate key {key!r}")
        out[key] = val
    return out


def build(args) -> tuple[dict, str]:
    opcodes = Path(args.opcodes)
    spec = Path(args.spec)
    index_path = Path(args.inst_index)
    tests_root = Path(args.tests_root)
    if not tests_root.is_dir():
        raise SetupError(f"{tests_root}: not a directory")
    scope = load_scope(opcodes)
    appendix = load_appendix_a(spec)
    index = load_index(index_path)
    coverage = build_coverage(scope, appendix, index, tests_root)

    runs = _parse_kv(args.run, "run")
    works = _parse_kv(args.work, "work")
    if set(runs) != set(works):
        raise SetupError("--run and --work labels must match")
    known_ids = {r["id"] for r in scope}
    checks_by_id = {r["id"]: (r["chain_points"] or 0)
                    for r in coverage["rows"]}
    items = [(label, Path(runs[label]), known_ids, checks_by_id)
             for label in sorted(runs)]
    records = merge_runs(items)
    for rec in records:
        rec["_work"] = Path(works[rec["_label"]])

    by_id = {}
    for row in coverage["rows"]:
        mine = [r for r in records if Path(r["file"]).stem == row["id"]]
        by_id[row["id"]] = dict(images=len(mine),
                                chain=sum(1 for r in mine
                                          if r["kind"] == "chain"),
                                fault=sum(1 for r in mine
                                          if r["kind"] == "fault"),
                                ok=sum(1 for r in mine if r["ok"]))
    ctx = dict(count_criteria=dict(
                   scope_fp=len(scope), appendix_a=len(appendix),
                   historical_alias=47,
                   note="47 is a retired historical alias; see issues.yaml"),
               by_id=by_id,
               known_items=dict(
                   **{"ISS-357": dict(
                       status="closed (M13: m13-testcases-006)",
                       applicability="not applicable: this "
                       "differential uses a single semihosting output channel "
                       "and compares bytes only",
                       note="SE dual-fd output capture loses fd1/fd2 order")},
                   picolibc_math=dict(
                       status="blocked (B7 closed)", applicability="not in "
                       "scope: separate picolibc suite, excluded by task",
                       note="picolibc math_test gap stays in its own matrix")))
    images, diffs, agree_fail, errors = analyse(
        coverage["rows"], coverage, records)
    run_ids = {Path(r["file"]).stem for r in records}
    for row in coverage["rows"]:
        if row["id"] not in run_ids:
            errors.append(f"{row['id']}: no three-platform run record")
    errors += chain_byte_errors(records)
    # 矩阵的「三平台一致」只取三方逐例一致通过的链例镜像；
    # 失败镜像的点不进矩阵，由 §2 的 AGREE_FAIL / DIFF 单列。
    verdict_of = {(i["id"], i["case_n"]): i["verdict"] for i in images}
    confirmed = set()
    excluded_images = []
    for rec in records:
        oid = Path(rec["file"]).stem
        if rec["kind"] != "chain":
            continue
        if verdict_of.get((oid, rec["case_n"])) != "AGREE_PASS":
            excluded_images.append(dict(id=oid, case_n=rec["case_n"],
                                        verdict=verdict_of.get(
                                            (oid, rec["case_n"]))))
            continue
        row = next(r for r in coverage["rows"] if r["id"] == oid)
        for point in (row.get("point_modes") or []):
            confirmed.add((oid, point["pt"]))
    matrix = flags_matrix(coverage["rows"], confirmed, excluded_images)
    sources = dict(
        opcodes=dict(path=_display(opcodes), sha256=_sha256(opcodes)),
        spec_appendix_a=dict(path=_display(spec), sha256=_sha256(spec)),
        inst_index=dict(path=_display(index_path),
                        sha256=_sha256(index_path)),
        runs=[dict(label=label, records=sum(
            1 for r in records if r["_label"] == label),
            sha256=_sha256(Path(runs[label]))) for label in sorted(runs)])
    engines = _parse_kv(args.engine, "engine")
    report = build_report(coverage, images, diffs, agree_fail, matrix,
                          engines, sources, errors, ctx,
                          input_commit=resolve_input_commit(args.input_commit))
    return report, render_markdown(report)


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(_REPO.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opcodes", default="contracts/opcodes.yaml")
    ap.add_argument("--spec", default="spec/SimRISC-07-浮点运算.md")
    ap.add_argument("--inst-index", default="tests/inst.yaml")
    ap.add_argument("--tests-root", default="tests")
    ap.add_argument("--run", action="append", default=None,
                    help="LABEL=<inst-asm-suite JSON>（可重复）")
    ap.add_argument("--work", action="append", default=None,
                    help="LABEL=<run_asm_suite work-dir>（与 --run 标签一一对应）")
    ap.add_argument("--engine", action="append", default=None,
                    help="PLATFORM=<md5>（可重复；报告身份）")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--markdown-out", default=None)
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
        print(f"fp_diff: SETUP: {exc}", file=sys.stderr)
        return 2
    except DiffError as exc:
        print(f"fp_diff: FAIL: {exc}", file=sys.stderr)
        return 2 if "not found" in str(exc) else 1

    payload = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown, encoding="utf-8")

    if args.check:
        target = Path(args.check)
        if not target.is_file():
            print(f"fp_diff: SETUP: {target} not found", file=sys.stderr)
            return 2
        want = payload if target.suffix == ".json" else markdown
        got = target.read_text(encoding="utf-8")
        if got != want:
            print(f"fp_diff: FAIL: {target} differs from the regenerated "
                  f"report ({len(got)} vs {len(want)} bytes)", file=sys.stderr)
            return 1
        print(f"fp_diff: check PASS ({target})")

    if not report["checks"]["ok"]:
        for err in report["checks"]["errors"]:
            print(f"fp_diff: FAIL: {err}", file=sys.stderr)
        return 1
    print(f"fp_diff: PASS ({report['coverage']['total']} id, "
          f"{report['results']['images']} image, "
          f"{report['results']['diff']} platform diff)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
