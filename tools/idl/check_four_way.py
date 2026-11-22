#!/usr/bin/env python3
"""check_four_way.py — 四方差分驱动（IDL / QEMU / gem5 / chipyard，`m17-idl-005`）。

判据（`m17-idl-005` 验收 1；用户 2026-11-22 定口径）：

  1. 同一份 ELF 交给三方既有平台（`tests/ee-tiny/run_inst_tiny.py` 的构建/启动
     路径，不另建第二套）与 IDL 执行器（`idl/idl_exec.py`）；
  2. 取每方的**签名槽流 + 退出码**：三方流由 `tests/shared/signature.py` 的
     `capture` 落到 `<work>/<id>/<id>.<platform>.out`，IDL 流由 `idl_exec.py`
     `--image-out` 落盘；
  3. 四方逐槽**全等**（`signature.parse(..., sentinel=False)`，inst 口径）、
     退出码全等；
  4. 每方槽值再与独立 oracle `tests/data/inst-signature/expected.tsv`（由 `.S`
     内联常量派生）比对（`kind=value/table` 逐槽；`relation` 无数值；
     `unwritten` ⇒ 红）——四方一致但全错时仍红，**不从实测反填期望**。

用例清单机制（`idl/idl_exec_cases.toml`）：

  * `[[case]]`（主清单）= `image` + `category`；
  * `[[pending]]` = 尚未纳入的镜像 + `reason`（每条必填）；
  * 门控断言 **主清单集合 == 现场派生集合（`tests/inst/*/*.S` 去掉
    `07-floating-point`）− pending 集合**；集合按现场 glob 派生，不写死计数。

平台集：

  * IDL 是固定一方；`--platforms` 只选另外三方，默认 `qemu`（L2 可跑，不依赖
    gem5/Verilator 构建）；节点/收口跑全四方用 `--platforms qemu,gem5,chipyard`。
  * 任一选中平台缺可执行文件/固件 ⇒ **ERROR（rc=2）**，不静默跳过。

用法：

    python3 tools/idl/check_four_way.py                       # IDL + QEMU（L2）
    python3 tools/idl/check_four_way.py --platforms qemu,gem5,chipyard
    python3 tools/idl/check_four_way.py --only ld.o_rrii_rd    # 单例诊断
    python3 tools/idl/check_four_way.py --json-out <f>

退出码：0 = 全部一致；1 = 有 FAIL；2 = setup/清单/输入错误。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

_HERE = Path(__file__).resolve()
_R = _HERE.parents[2]
sys.path.insert(0, str(_R / "tools" / "infra"))
sys.path.insert(0, str(_R / "tests" / "shared"))

import paths  # noqa: E402
import signature  # noqa: E402
import writer_guard  # noqa: E402

RUN_INST = _R / "tests" / "ee-tiny" / "run_inst_tiny.py"
IDL_EXEC = _R / "idl" / "idl_exec.py"
EXPECTED = _R / "tests" / "data" / "inst-signature" / "expected.tsv"
MANIFEST = _R / "idl" / "idl_exec_cases.toml"
BOOKS = _R / "tests" / "inst"
FP_BOOK = "07-floating-point"
PLATFORMS = ("qemu", "gem5", "chipyard")
VALUE_KINDS = ("value", "table")


class ManifestError(Exception):
    """清单与现场派生不一致（集合断言失败）。"""


# ---------------------------------------------------------------------------
# 清单：主集合 == 现场派生 − pending
# ---------------------------------------------------------------------------
def derived_images(books=BOOKS) -> dict:
    """`tests/inst/*/*.S` 去掉 FP 册；返回 `{stem: 相对路径}`（现场派生）。"""
    out = {}
    for path in sorted(Path(books).glob("*/*.S")):
        if path.parent.name == FP_BOOK:
            continue
        rel = path.relative_to(_R).as_posix()
        if path.stem in out:
            raise ManifestError("镜像 stem 重复（清单按 stem 索引）：%s / %s"
                                % (out[path.stem], rel))
        out[path.stem] = rel
    return out


def load_manifest(path=MANIFEST):
    """读 `[[case]]` / `[[pending]]`；返回 `(cases, pending)` 列表。"""
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)
    cases = doc.get("case")
    pending = doc.get("pending", [])
    if not isinstance(cases, list) or not cases:
        raise ManifestError("%s: 无 [[case]] 主清单" % path)
    for c in cases:
        for key in ("image", "category"):
            if not c.get(key):
                raise ManifestError("%s: [[case]] 缺 %r：%r" % (path, key, c))
    for p in pending:
        for key in ("image", "reason"):
            if not p.get(key):
                raise ManifestError("%s: [[pending]] 缺 %r：%r" % (path, key, p))
    return cases, pending


def check_manifest(cases, pending, derived):
    """集合断言（fail-closed）。

    主清单 == 现场派生 − pending；pending ⊆ 派生且与主清单不交。
    """
    problems = []
    main = [c["image"] for c in cases]
    pend = [p["image"] for p in pending]
    main_set, pend_set, live = set(main), set(pend), set(derived.values())
    if len(main_set) != len(main):
        problems.append("主清单有重复 image（%d 条 / %d 唯一）"
                        % (len(main), len(main_set)))
    if len(pend_set) != len(pend):
        problems.append("pending 有重复 image（%d 条 / %d 唯一）"
                        % (len(pend), len(pend_set)))
    dup = main_set & pend_set
    if dup:
        problems.append("同一镜像同时在主清单与 pending：%s"
                        % ", ".join(sorted(dup)))
    for label, s in (("pending", pend_set), ("主清单", main_set)):
        extra = s - live
        if extra:
            problems.append("%s 有现场不存在的镜像：%s"
                            % (label, ", ".join(sorted(extra))))
    expect_main = live - pend_set
    missing = expect_main - main_set
    surplus = main_set - expect_main
    if missing:
        problems.append("主清单缺 %d 个应纳入镜像：%s"
                        % (len(missing), ", ".join(sorted(missing)[:8])))
    if surplus:
        problems.append("主清单多 %d 个不在「派生−pending」内的镜像：%s"
                        % (len(surplus), ", ".join(sorted(surplus)[:8])))
    if problems:
        raise ManifestError("；".join(problems))
    return {"main": len(main_set), "pending": len(pend_set),
            "derived": len(live)}


# ---------------------------------------------------------------------------
# 独立 oracle：expected.tsv
# ---------------------------------------------------------------------------
def load_expected(path=EXPECTED) -> dict:
    """`image -> [{slot, kind, value, source}]`，槽号 1..N 连续（fail-closed）。"""
    out = {}
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8")
                                  .splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) != 6:
            raise ManifestError("%s:%d 列数 %d ≠ 6" % (path, lineno, len(cols)))
        image, slot, kind, expected, _expr, source = cols
        if kind not in ("value", "table", "relation", "unwritten"):
            raise ManifestError("%s:%d 未知 kind %r" % (path, lineno, kind))
        value = int(expected, 0) if kind in VALUE_KINDS else None
        out.setdefault(image, []).append({
            "slot": int(slot), "kind": kind,
            "value": value, "source": source})
    for image, slots in out.items():
        if [s["slot"] for s in slots] != list(range(1, len(slots) + 1)):
            raise ManifestError("%s: 槽号不是 1..N 连续" % image)
    return out


def expected_problems(slots, party, got):
    """一方槽值 vs expected.tsv（`value`/`table` 逐槽；`unwritten` ⇒ 红）。"""
    problems = []
    for want, value in zip(slots, got):
        if want["kind"] == "unwritten":
            problems.append("%s 槽 %d 未写入口（%s）"
                            % (party, want["slot"], want["source"]))
        elif want["kind"] in VALUE_KINDS and value != want["value"]:
            problems.append("%s 槽 %d 期望 0x%016x 实际 0x%016x（%s）"
                            % (party, want["slot"], want["value"],
                               value if value is not None else 0,
                               want["source"]))
    return problems


# ---------------------------------------------------------------------------
# 取流
# ---------------------------------------------------------------------------
def run_platforms(ids, platforms, cfg, out_json):
    """调 `run_inst_tiny.py`（既有构建/启动路径）跑三方；返回 `(rc, records)`。"""
    cmd = [sys.executable, str(RUN_INST), "--books-root", str(BOOKS),
           "--platforms", ",".join(platforms),
           "--work-dir", str(cfg["work"]), "--log-dir", str(cfg["work"] / "log"),
           "--jobs", str(cfg["jobs"]), "--json-out", str(out_json),
           "--qemu", str(cfg["qemu"]), "--bootrom", str(cfg["bootrom"]),
           "--timeout-qemu", str(cfg["timeout_qemu"]),
           "--timeout-gem5", str(cfg["timeout_gem5"]),
           "--timeout-chipyard", str(cfg["timeout_chipyard"])]
    if "gem5" in platforms:
        cmd += ["--gem5", str(cfg["gem5"]),
                "--gem5-config", str(cfg["gem5_config"])]
    if "chipyard" in platforms:
        cmd += ["--chipyard", str(cfg["chipyard"])]
    for cid in ids:
        cmd += ["--id", cid]
    log = cfg["work"] / "run_inst_tiny.log"
    out_json.unlink(missing_ok=True)      # 防上次运行的 JSON 被当本次结果
    with open(log, "wb") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL).returncode
    records = {}
    if out_json.is_file():
        for rec in json.loads(out_json.read_text(encoding="utf-8"))["records"]:
            records[Path(rec["file"]).stem] = rec
    return rc, records


def run_idl(case, cfg):
    """IDL 一方：`idl_exec.py --elf … --state-out … --image-out …`。"""
    cid = Path(case["image"]).stem
    work = cfg["work"] / cid
    state_out = work / (cid + ".idl.state.json")
    image_out = work / (cid + ".idl.out")
    elf = work / (cid + ".elf")
    if not elf.is_file():
        return {"id": cid, "ok": False,
                "detail": "缺镜像 %s（run_inst_tiny 未产出）" % elf}
    log = work / (cid + ".idl.log")
    state_out.unlink(missing_ok=True)     # 防上次运行的末态/流被当本次结果
    image_out.unlink(missing_ok=True)
    with open(log, "wb") as fh:
        proc = subprocess.run(
            [sys.executable, str(IDL_EXEC), "--elf", str(elf),
             "--bootrom", str(cfg["bootrom"]), "--state-out", str(state_out),
             "--image-out", str(image_out), "--max-steps", str(cfg["max_steps"])],
            stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    if proc.returncode != 0 or not state_out.is_file():
        return {"id": cid, "ok": False,
                "detail": "idl_exec rc=%d（日志 %s）" % (proc.returncode, log)}
    state = json.loads(state_out.read_text(encoding="utf-8"))
    blob = image_out.read_bytes() if image_out.is_file() else b""
    return {"id": cid, "ok": True, "exit_code": state["exit_code"],
            "blob": blob, "steps": state.get("steps"), "log": str(log)}


# ---------------------------------------------------------------------------
# 比对
# ---------------------------------------------------------------------------
def compare_case(case, rec, idl, expected, platforms):
    """四方槽流 + 退出码 + expected.tsv；返回记录。"""
    rel = case["image"]
    cid = Path(rel).stem
    nslots = len(expected.get(rel, []))
    out = {"id": cid, "image": rel, "category": case["category"],
           "slots": nslots, "ok": False, "problems": []}
    if not idl.get("ok"):
        out["problems"].append("IDL: %s" % idl.get("detail"))
        return out
    if rec is None:
        out["problems"].append("run_inst_tiny 无该镜像记录（构建失败？）")
        return out
    if not nslots:
        # 0 检查点的镜像（如 `undi_reserved.S`）在 expected.tsv 无行；用
        # run_inst_tiny 的现场统计对账，防「数据漂移导致整镜像漏槽」被静默放过。
        checks = rec.get("expected")
        if checks != 0:
            out["problems"].append(
                "expected.tsv 无该镜像槽，但现场派生检查点数 = %r（数据漂移？）"
                % (checks,))
            return out

    parties = ["idl"] + list(platforms)
    rcs = {"idl": idl["exit_code"]}
    blobs = {"idl": idl["blob"]}
    for plat in platforms:
        entry = rec.get("platforms", {}).get(plat)
        if entry is None:
            out["problems"].append("%s: 平台未产出记录" % plat)
            return out
        rcs[plat] = entry["rc"]
        blob_path = rec["__work"] / (cid + "." + plat + ".out")
        blobs[plat] = blob_path.read_bytes() if blob_path.is_file() else b""
    out["rcs"] = rcs
    out["bytes"] = {p: len(b) for p, b in blobs.items()}

    if len(set(rcs.values())) != 1:
        out["problems"].append("退出码不一致：%s" % _fmt(rcs))
    try:
        slots = {p: signature.parse(b, nslots, sentinel=False)
                 for p, b in blobs.items()}
    except signature.SignatureError as exc:
        out["problems"].append("签名流不可解析：%s（字节 %s）"
                               % (exc, _fmt(out["bytes"])))
        return out

    first = slots["idl"]
    for plat in platforms:
        if slots[plat] != first:
            i = next(i for i, (a, b) in enumerate(zip(first, slots[plat]))
                     if a != b)
            out["problems"].append("槽流不一致：槽 %d idl=0x%016x %s=0x%016x"
                                   % (i + 1, first[i], plat, slots[plat][i]))
    for party, got in slots.items():
        for problem in expected_problems(expected.get(rel, []), party, got):
            out["problems"].append(problem)
            if len(out["problems"]) >= 8:
                break
        if len(out["problems"]) >= 8:
            break
    out["ok"] = not out["problems"]
    return out


def _fmt(d):
    return "{" + ",".join("%s:%s" % (k, v) for k, v in d.items()) + "}"


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(MANIFEST),
                    help="用例清单（默认 idl/idl_exec_cases.toml）")
    ap.add_argument("--platforms", default="qemu",
                    help="IDL 之外的三方（逗号分隔，默认 qemu；"
                         "全四方用 qemu,gem5,chipyard）")
    ap.add_argument("--only", action="append", default=None,
                    help="只跑这些镜像 id（可重复；诊断/注入用）")
    ap.add_argument("--qemu", default=str(paths.host_toolchain_dir() / "bin"
                                          / "qemu-system-dadao"))
    ap.add_argument("--bootrom",
                    default=str(paths.test_artifacts_dir() / "bootrom" / "tiny"
                               / "bootrom_tiny.bin"))
    ap.add_argument("--gem5", default=str(_R / ".work" / "source" / "gem5"
                                          / "build" / "DADAO" / "gem5.opt"))
    ap.add_argument("--gem5-config", default=str(_R / ".work" / "source" / "gem5"
                                                 / "configs" / "dadao" / "fs.py"))
    ap.add_argument("--chipyard", default=str(
        _R / ".work" / "source" / "chipyard" / "sims" / "verilator"
        / "simulator-chipyard.harness-WumingTinyConfig"))
    ap.add_argument("--work-dir", default=None,
                    help="构建/取流产物根（默认 test_artifacts/harness/inst-asm/"
                         "idl-four-way）")
    ap.add_argument("--jobs", type=int,
                    default=max(1, (os.cpu_count() or 1) - 2))
    ap.add_argument("--max-steps", type=int, default=2_000_000)
    ap.add_argument("--timeout-qemu", type=int, default=120)
    ap.add_argument("--timeout-gem5", type=int, default=300)
    ap.add_argument("--timeout-chipyard", type=int, default=900)
    ap.add_argument("--json-out", default=None)
    writer_guard.add_arguments(ap)
    args = ap.parse_args(argv)

    platforms = [p for p in args.platforms.split(",") if p]
    bad = [p for p in platforms if p not in PLATFORMS]
    if bad or not platforms:
        print("check_four_way: ERROR: --platforms 非法：%r（可选 %s）"
              % (bad or args.platforms, ",".join(PLATFORMS)), file=sys.stderr)
        return 2

    try:
        cases, pending = load_manifest(args.cases)
        derived = derived_images()
        counts = check_manifest(cases, pending, derived)
        expected = load_expected()
    except (ManifestError, tomllib.TOMLDecodeError) as exc:
        print("check_four_way: ERROR: 清单/派生不一致：%s" % exc,
              file=sys.stderr)
        return 2

    def usable(path, executable=False):
        p = Path(path)
        return p.is_file() and os.access(p, os.X_OK if executable else os.R_OK)

    missing = [name for name, path, exe in (
        ("run_inst_tiny.py", RUN_INST, False),
        ("idl_exec.py", IDL_EXEC, False),
        ("expected.tsv", EXPECTED, False),
        ("qemu", args.qemu, True),
        ("bootrom", args.bootrom, False),
        ("llvm-mc", paths.host_toolchain_dir() / "bin" / "llvm-mc", True),
        ("ld.lld", paths.host_toolchain_dir() / "bin" / "ld.lld", True))
        if not usable(path, exe)]
    if "gem5" in platforms and not usable(args.gem5, True):
        missing.append("gem5:%s" % args.gem5)
    if "chipyard" in platforms and not usable(args.chipyard, True):
        missing.append("chipyard:%s" % args.chipyard)
    if missing:
        print("check_four_way: ERROR: 缺 %s（不静默跳过）"
              % ", ".join(missing), file=sys.stderr)
        return 2

    sel = cases
    if args.only:
        wanted = set(args.only)
        sel = [c for c in cases if Path(c["image"]).stem in wanted]
        lost = wanted - {Path(c["image"]).stem for c in sel}
        if lost:
            print("check_four_way: ERROR: --only 不在主清单：%s"
                  % ", ".join(sorted(lost)), file=sys.stderr)
            return 2
    ids = [Path(c["image"]).stem for c in sel]

    work = Path(args.work_dir) if args.work_dir else \
        paths.test_artifacts_dir() / "harness" / "inst-asm" / "idl-four-way"
    work.mkdir(parents=True, exist_ok=True)
    cfg = {"work": work, "jobs": args.jobs, "qemu": Path(args.qemu),
           "bootrom": Path(args.bootrom), "gem5": Path(args.gem5),
           "gem5_config": Path(args.gem5_config),
           "chipyard": Path(args.chipyard), "max_steps": args.max_steps,
           "timeout_qemu": args.timeout_qemu,
           "timeout_gem5": args.timeout_gem5,
           "timeout_chipyard": args.timeout_chipyard}

    used = [str(Path(args.qemu)), str(Path(args.bootrom)),
            str(paths.host_toolchain_dir() / "bin" / "llvm-mc"),
            str(paths.host_toolchain_dir() / "bin" / "ld.lld")]
    if "gem5" in platforms:
        used.append(str(Path(args.gem5)))
    if "chipyard" in platforms:
        used.append(str(Path(args.chipyard)))
    guard = writer_guard.start_guard(args, used, label="check_four_way")

    out_json = work / "run_inst_tiny.json"
    rc, records = run_platforms(ids, platforms, cfg, out_json)
    if rc == 2 or not records:
        print("check_four_way: ERROR: run_inst_tiny rc=%d / records=%d"
              "（日志 %s；缺可执行/固件或平台启动失败）"
              % (rc, len(records), work / "run_inst_tiny.log"), file=sys.stderr)
        return 2

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        idl_by_id = dict(zip(ids, pool.map(lambda c: run_idl(c, cfg), sel)))
    for case in sel:
        cid = Path(case["image"]).stem
        rec = records.get(cid)
        if rec is not None:
            rec["__work"] = work / cid
        results.append(compare_case(case, rec, idl_by_id[cid], expected,
                                    platforms))

    for r in results:
        tag = "PASS" if r["ok"] else "FAIL"
        detail = "槽 %d / rc %s" % (r.get("slots"), _fmt(r.get("rcs", {})))
        print("  [%s] %-24s %-9s %s"
              % (tag, r["id"], r.get("category", ""), detail))
        for problem in r.get("problems", []):
            print("         %s" % problem)
    npass = sum(1 for r in results if r["ok"])
    print("-" * 72)
    print("check_four_way: %d/%d 例四方一致（parties=idl,%s；主清单 %d / "
          "pending %d / 现场派生 %d）"
          % (npass, len(results), ",".join(platforms), counts["main"],
             counts["pending"], counts["derived"]))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"schema": "four-way/1", "parties": ["idl"] + platforms,
             "manifest": counts, "records": results}, indent=1) + "\n",
            encoding="utf-8")
    guard_ok = writer_guard.finish_guard(guard)
    return 0 if (npass == len(results) and guard_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
