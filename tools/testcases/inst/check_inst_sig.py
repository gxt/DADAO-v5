#!/usr/bin/env python3
"""check_inst_sig.py — `tests/inst` 签名区**槽级**门控（L2，m17-testcases-001）。

判据（两条独立路径，期望不从实现反推）
--------------------------------------
  1. **期望值路径**：`tools/testcases/lib/inst_expected.py` 从 `.S` + 宏层派生
     「槽 → 期望常量」（`__CHECK_*` 内联常量 / `WDATA` 数据区），逐字节比对入库数据
     `tests/data/inst-signature/expected.tsv`（漂移 ⇒ 红，提示重生成）；
  2. **实测流路径**：同一批 `.S` 编译成镜像，QEMU `kaiwu-tiny` 跑出签名流，
     `tests/shared/signature.py` 解析成槽后**逐槽**与 1 的期望比对。

诊断：每处失败写「槽 N 期望 0x… 实际 0x…（来源 `<.S>:<行>`）”；漏写（`0xdeadbeef`）
写「槽 N 未写」。签名流缺失/长度不符/构建失败 ⇒ 该镜像 **BLOCKED**（不是 PASS）。

计数一律现场派生：镜像集 = `tests/inst/` 下含 `.S` 的册目录；槽数 = `__NCHECK` 累加；
并与 `tests/case-ledger.tsv`（另一条扫描器路径）现场对账（镜像数 + 每镜像槽数）。

用法：
  python3 tools/testcases/inst/check_inst_sig.py            # 门控（L2）
  python3 tools/testcases/inst/check_inst_sig.py --write    # 重生成 tests/data/inst-signature/
  python3 tools/testcases/inst/check_inst_sig.py --data-only  # 只核对数据产物（不跑 QEMU）
  python3 tools/testcases/inst/check_inst_sig.py --id <stem>  # 只跑指定镜像
退出码：0 = 全绿；1 = 有 FAIL/BLOCKED 或数据漂移；2 = setup（缺工具/固件/0 载体）。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _p in (_ROOT / "tools" / "testcases" / "lib",
           _ROOT / "tests" / "shared",
           _ROOT / "tests" / "ee-tiny",
           _ROOT / "tools" / "infra"):
    sys.path.insert(0, str(_p))

import inst_expected  # noqa: E402
import paths  # noqa: E402
import run_inst_tiny  # noqa: E402
import signature  # noqa: E402
import writer_guard  # noqa: E402

LEDGER = "tests/case-ledger.tsv"


def _first_diff(name, live, disk):
    a, b = live.splitlines(), disk.splitlines()
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return "%s:%d 行不一致：\n  生成=%r\n  入库=%r" % (name, i, x, y)
    if len(a) != len(b):
        return "%s 行数不一致：生成 %d 行 / 入库 %d 行" % (name, len(a), len(b))
    return "%s 不一致（末尾换行）" % name


def check_data(root: Path, images) -> list:
    """入库数据 == 现场生成（期望值 + 输入 sha256）。返回问题列表。"""
    problems = []
    exp_live = inst_expected.render_expected(images)
    exp_disk = inst_expected.expected_path(root)
    if not exp_disk.is_file():
        problems.append("%s 不存在 —— 先跑 check_inst_sig.py --write" % exp_disk)
    else:
        disk = exp_disk.read_text(encoding="utf-8")
        if disk != exp_live:
            problems.append(_first_diff(inst_expected.EXPECTED_NAME, exp_live, disk))
    in_live = inst_expected.render_inputs(root)
    in_disk = inst_expected.inputs_path(root)
    if not in_disk.is_file():
        problems.append("%s 不存在 —— 先跑 check_inst_sig.py --write" % in_disk)
    else:
        disk = in_disk.read_text(encoding="utf-8")
        if disk != in_live:
            problems.append(_first_diff(inst_expected.INPUTS_NAME, in_live, disk))
    return problems


def check_ledger(root: Path, images) -> list:
    """镜像数 / 每镜像槽数与 `tests/case-ledger.tsv` 现场派生一致（独立扫描路径）。"""
    ledger = root / LEDGER
    if not ledger.is_file():
        return ["缺少 %s（无法现场对账）" % LEDGER]
    rows = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if parts[0] != "asm":
            continue
        rows[parts[1]] = rows.get(parts[1], 0) + 1
    problems = []
    live = {img.path: img for img in images}
    for path in sorted(set(live) - set(rows)):
        problems.append("镜像不在 case-ledger：%s" % path)
    for path in sorted(set(rows) - set(live)):
        problems.append("case-ledger 有、载体集没有：%s" % path)
    for path in sorted(set(live) & set(rows)):
        faults = len(run_inst_tiny.scan_source(root / path)["faults"])
        slots = rows[path] - faults
        if slots != len(live[path].slots):
            problems.append("%s 槽数 %d ≠ case-ledger 派生 %d（asm 行 %d − 故障例 %d）"
                            % (path, len(live[path].slots), slots, rows[path], faults))
    return problems


def _slot_problem(index: int, slot, got):
    if slot.kind == "unwritten":
        return ("槽 %d 未写（__NCHECK 记了该检查点，但源码没有 SIGUPD 写入口；"
                "来源 %s）" % (index, slot.source))
    if slot.kind == "relation":
        return None
    if signature.compare([got], [slot.value]):
        if got is None:
            return "槽 %d 未写（期望 0x%016x；来源 %s）" % (
                index, slot.value, slot.source)
        return "槽 %d 期望 0x%016x 实际 0x%016x（来源 %s）" % (
            index, slot.value, got, slot.source)
    return None


def _build_diag(toolbin: Path, src: Path, lds: Path, work: Path, stem: str) -> Path:
    """诊断构建：`-defsym SIG_CONTINUE=1` ⇒ 判红点不退出（正常构建不含此定义）。

    只用于**正常镜像已判红**后的第二次构建；正常门控构建走
    `run_inst_tiny.build`（未定义 `SIG_CONTINUE` 时 `.text` 与旧版逐字节相同）。
    """
    obj = work / (stem + ".diag.o")
    elf = work / (stem + ".diag.elf")
    subprocess.run([str(toolbin / "llvm-mc"), "--triple=dadao-unknown-elf",
                    "-filetype=obj", "--defsym", "SIG_CONTINUE=1", str(src),
                    "-o", str(obj)], check=True, capture_output=True)
    subprocess.run([str(toolbin / "ld.lld"), "-T", str(lds), str(obj),
                    "-o", str(elf)], check=True, capture_output=True)
    return elf


def _slot_report(img, blob):
    """解析签名流并返回 (problems, exact) —— 逐槽比对（`signature.compare`）。

    `signature.unwritten` 只对**预填哨兵**的 scope（`tests/arch`）有意义；`tests/inst`
    按 `signature.py` 的 inst 口径 `sentinel=False`，漏跑由静态 `kind=unwritten` 判。
    """
    got = signature.parse(blob, len(img.slots), sentinel=False)
    problems, exact = [], 0
    for slot, value in zip(img.slots, got):
        if slot.kind in ("value", "table") and value == slot.value:
            exact += 1
        problem = _slot_problem(slot.index, slot, value)
        if problem:
            problems.append(problem)
    return problems, exact


def run_image(task, cfg) -> dict:
    img, lds = task
    src = cfg["root"] / img.path
    stem = Path(img.path).stem
    work = cfg["work"] / stem
    work.mkdir(parents=True, exist_ok=True)
    rec = {"image": img.path, "status": "PASS", "slots": len(img.slots),
           "exact": 0, "relation": 0, "problems": []}
    # `tests/inst` **不**用 `SIG_BEGIN` 预填（预填会改指令流，M16 周期基线不允许），
    # 且合法期望本身可为 `0x00000000deadbeef`（见 08 册 rol.t 两例）⇒ 解析必须
    # `sentinel=False`（`signature.py` 的 inst 口径）；「漏跑」由**静态派生**判
    # （`__NCHECK` 加一但无 `SIGUPD` ⇒ kind=unwritten），不靠哨兵猜。
    try:
        elf = run_inst_tiny.build(cfg["toolbin"], src, lds, 0, work, stem)
    except Exception as exc:                       # noqa: BLE001 — 构建失败 = BLOCKED
        rec["status"] = "BLOCKED"
        rec["problems"].append("构建失败：%s" % exc)
        return rec
    out = work / "sig.out"
    log = work / "run.log"
    rc, blob, _ = signature.capture(
        "qemu", image=elf, bootrom=cfg["bootrom"], out=out, log=log,
        timeout=cfg["timeout"], qemu=cfg["qemu"])
    rec["rc"] = rc
    if rc != 0:
        # 正常镜像判红（guest 断言失败 / 异常终止）⇒ 用诊断构建重跑一次，拿完整流做
        # 「槽 N 期望/实际」定位；诊断流也拿不到 ⇒ 仍判 FAIL（不是 PASS）。
        rec["status"] = "FAIL"
        rec["problems"].append("正常镜像 QEMU 退出码 %s（签名流 %d B）"
                               % (rc, len(blob)))
        try:
            diag = _build_diag(cfg["toolbin"], src, lds, work, stem)
            rc2, blob2, _ = signature.capture(
                "qemu", image=diag, bootrom=cfg["bootrom"],
                out=work / "sig.diag.out", log=work / "run.diag.log",
                timeout=cfg["timeout"], qemu=cfg["qemu"])
        except Exception as exc:                   # noqa: BLE001
            rec["problems"].append("诊断构建失败：%s" % exc)
            return rec
        rec["diag_rc"] = rc2
        if rc2 != 0:
            rec["problems"].append("诊断构建（SIG_CONTINUE）退出码 %s，无法取流" % rc2)
            return rec
        try:
            problems, exact = _slot_report(img, blob2)
        except signature.SignatureError as exc:
            rec["problems"].append("诊断签名流不可用：%s" % exc)
            return rec
        rec["exact"] = exact
        rec["relation"] = sum(1 for s in img.slots if s.kind == "relation")
        rec["problems"] += ["诊断构建：%s" % p for p in problems]
        return rec
    try:
        problems, exact = _slot_report(img, blob)
    except signature.SignatureError as exc:
        rec["status"] = "BLOCKED"
        rec["problems"].append("签名流不可用：%s" % exc)
        return rec
    rec["exact"] = exact
    rec["relation"] = sum(1 for s in img.slots if s.kind == "relation")
    rec["problems"] += problems
    if rec["problems"]:
        rec["status"] = "FAIL"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="重生成 tests/data/inst-signature/（不跑 QEMU）")
    ap.add_argument("--data-only", action="store_true",
                    help="只核对入库数据与现场派生一致（不跑 QEMU）")
    ap.add_argument("--id", action="append", default=None,
                    help="只跑这些镜像（.S stem；可重复）")
    ap.add_argument("--books-root", default=inst_expected.DEFAULT_BOOKS)
    ap.add_argument("--lds", default=inst_expected.DEFAULT_LDS)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--jobs", type=int,
                    default=max(1, (os.cpu_count() or 1) - 2))
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--json-out", default=None)
    writer_guard.add_arguments(ap)
    args = ap.parse_args()

    root = _ROOT
    os.chdir(root)          # `.include "tests/…"` 相对仓库根（与 run_inst_tiny 同口径）
    try:
        images = inst_expected.derive(root, args.books_root)
    except inst_expected.ExpectError as exc:
        print("check-inst-sig: ERROR: 期望值派生失败：%s" % exc, file=sys.stderr)
        return 2
    run_images = images
    if args.id:
        want = set(args.id)
        run_images = [i for i in images if Path(i.path).stem in want]
        if not run_images:
            print("check-inst-sig: ERROR: --id 未命中任何镜像", file=sys.stderr)
            return 2

    if args.write:
        result = inst_expected.write_data(root)
        total = sum(len(i.slots) for i in result["images"])
        kinds = {}
        for i in result["images"]:
            for s in i.slots:
                kinds[s.kind] = kinds.get(s.kind, 0) + 1
        print("check-inst-sig: 已写 %s/{expected.tsv,inputs.sha256}：%d 镜像 / %d 槽 %s"
              % (inst_expected.DATA_DIR, len(result["images"]), total,
                 " ".join("%s=%d" % kv for kv in sorted(kinds.items()))))
        return 0

    problems = check_data(root, images) + check_ledger(root, images)
    if problems:
        for p in problems:
            print("check-inst-sig: DATA-FAIL: %s" % p)
        print("check-inst-sig: FAIL（入库数据与现场派生不一致）")
        return 1
    total = sum(len(i.slots) for i in run_images)
    static = sum(1 for i in run_images for s in i.slots
                 if s.kind in ("value", "table"))
    print("check-inst-sig: %d 镜像 / %d 槽（静态期望 %d / 运行期关系 %d）；"
          "数据与 case-ledger 对账一致"
          % (len(run_images), total, static, total - static))
    if args.data_only:
        print("check-inst-sig: PASS（--data-only）")
        return 0

    toolbin = paths.host_toolchain_dir() / "bin"
    qemu = Path(args.qemu) if args.qemu else toolbin / "qemu-system-dadao"
    bootrom = (Path(args.bootrom) if args.bootrom
               else paths.test_artifacts_dir() / "bootrom" / "tiny" / "bootrom_tiny.bin")
    lds = root / args.lds
    work = (Path(args.work_dir) if args.work_dir
            else paths.test_artifacts_dir() / "harness" / "inst-sig")
    for what, path in (("qemu", qemu), ("llvm-mc", toolbin / "llvm-mc"),
                       ("ld.lld", toolbin / "ld.lld"), ("bootrom", bootrom),
                       ("lds", lds)):
        if not Path(path).exists():
            print("check-inst-sig: ERROR: %s 不存在: %s" % (what, path),
                  file=sys.stderr)
            return 2
    work.mkdir(parents=True, exist_ok=True)
    cfg = {"root": root, "toolbin": toolbin, "qemu": qemu, "bootrom": bootrom,
           "work": work, "timeout": args.timeout}
    guard = writer_guard.start_guard(
        args, [str(qemu), str(toolbin / "llvm-mc"), str(toolbin / "ld.lld"),
               str(bootrom)], label="check_inst_sig")
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_image, (img, lds), cfg) for img in run_images]
        for fut in futures:
            rec = fut.result()
            records.append(rec)
            if rec["status"] == "PASS":
                print("  [PASS] %-52s %3d 槽（静态 %d / 关系 %d）"
                      % (rec["image"], rec["slots"], rec["exact"], rec["relation"]))
            else:
                print("  [%s] %-52s %3d 槽"
                      % (rec["status"], rec["image"], rec["slots"]))
                for p in rec["problems"]:
                    print("         %s" % p)
    guard_ok = writer_guard.finish_guard(guard)
    npass = sum(1 for r in records if r["status"] == "PASS")
    exact = sum(r["exact"] for r in records)
    relation = sum(r["relation"] for r in records)
    print("-" * 78)
    print("check-inst-sig: %d/%d 镜像通过；静态槽 %d 逐槽一致；运行期关系槽 %d（不比对取值）"
          % (npass, len(records), exact, relation))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"schema": "inst-signature/1", "records": records}, indent=1) + "\n")
    if npass != len(records) or not guard_ok:
        print("check-inst-sig: FAIL")
        return 1
    print("check-inst-sig: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
