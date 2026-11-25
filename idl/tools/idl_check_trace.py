#!/usr/bin/env python3
"""idl_check_trace.py — 逐指令 trace 与 QEMU 的按 PC 对齐比对（`m17-idl-004`）。

对每个用例（`idl/data/idl_exec_cases.toml` 的 `tests/inst` 载体）：

  1. `idl/tools/idl_qemu_trace.py` 跑 QEMU（`one-insn-per-tb` + `-d cpu`），取入口态、
     折叠连续重复记录、按「记录间差分」派生 QEMU 侧 trace；
  2. `idl/tools/idl_exec_trace.py` 用同一入口态跑执行器，生成执行器侧 trace（取指异常
     归并到前一条指令）；
  3. **逐条记录**比较 `pc/insn/id/mn/dst/val/exc`，并比较每条指令后的运行模式与
     cfx code、最终退出码与 semihosting 字节流。

四类文档化等价（逐条计数见输出；口径见 `idl/docs/trace-format.md`）：

  E1 QEMU TB 日志的**连续重复记录**（同 PC 且状态逐字段相同）折叠；
  E2 取指异常 QEMU **不出记录**，其异常归并到前一条指令（区间边界一致）；
  E3 semihosting「无返回」服务（`SYS_WRITEC`/`SYS_EXIT*`）与 `SYS_CLOCK` 的 `rd8`
     不是架构语义（QEMU 写 `0xdeadbeef` / 宿主时钟）⇒ 该步起 `rd8` 退出比对；
  E4 `ra1..ra63` 在 `RACNT` 有效区外**内容未定义**（`spec/SimRISC-00 §2.4`）⇒
     只比有效区；内容来源未定义的条目（有效区外提升，或 `call`/`ret` 整栈搬移
     自未定义来源）不参与比对。两侧各记一份跳过集，比较时取**并集**后成对剔除
     `dst`/`val`（两侧物理布局不同 ⇒ 单侧跳过不代表另一侧可判为差异）。

用法：

    python3 idl/tools/idl_check_trace.py --images <run_inst_tiny --work-dir> \
        --bootrom <bootrom_tiny.bin> [--only <id>] [--trace-dir <dir>] \
        [--json-out <f>]
    python3 idl/tools/idl_check_trace.py ... --sample-out idl/docs/trace-sample.jsonl
    python3 idl/tools/idl_check_trace.py ... --sample-check idl/docs/trace-sample.jsonl
    python3 idl/tools/idl_check_trace.py --self-test   # 清单键自检

`--cases` 清单的 `[[case]]` 以 `image`（`tests/inst/**/*.S`，相对仓库根；用例名取
`Path(image).stem`）为主键，并接受旧格式的 `id` 作诊断别名（两者都缺 ⇒ 报错）。

退出码：0 = 全部一致；1 = 有差异；2 = 环境/输入问题。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True       # idl/ 由 check-manifests-guard 做目录断言

import idl_exec_trace  # noqa: E402
import idl_qemu_trace  # noqa: E402
import idl_trace_common as tc  # noqa: E402

FIELDS = ("seq", "pc", "insn", "id", "mn", "dst", "val", "exc")
SAMPLE_CASE = "add.st_orrr_rd"
SAMPLE_RECORDS = 8


def _fail(msg):
    """清单/输入问题：stderr 打印并 rc=2（与 `--only` 未知 id 等输入错误同口径）。"""
    print("idl_check_trace: %s" % msg, file=sys.stderr)
    raise SystemExit(2)


def resolve_image(image):
    """`image` 相对路径按仓库根解析（与 `idl_four_way.py` 同口径）。"""
    path = Path(image)
    return path if path.is_absolute() else REPO_ROOT / path


def load_cases(path):
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        _fail("Python 3.11+ (tomllib) required")
    try:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
    except (OSError, ValueError) as exc:      # 读不到 / 清单格式错
        _fail("%s: 读不到或解析不了清单：%s" % (path, exc))
    cases = doc.get("case")
    if not isinstance(cases, list) or not cases:
        _fail("%s: no [[case]] entries" % path)
    out = []
    for case in cases:
        if not isinstance(case, dict):
            _fail("%s: [[case]] 不是表：%r" % (path, case))
        image = case.get("image")
        legacy = case.get("id")
        if image is None and legacy is None:
            _fail("%s: [[case]] 缺 'image'（或旧别名 'id'）：%r" % (path, case))
        if image is not None and not isinstance(image, str):
            _fail("%s: [[case]] image 不是字符串：%r" % (path, case))
        if image is None:
            if not isinstance(legacy, str):
                _fail("%s: [[case]] id 不是字符串：%r" % (path, case))
            cid = legacy         # 旧格式：`id` 即用例名，无镜像可核
        else:
            path_image = resolve_image(image)
            if not path_image.is_file():
                _fail("%s: [[case]] image 不存在：%r（解析为 %s）"
                      % (path, image, path_image))
            cid = Path(image).stem
        if not case.get("category"):
            _fail("%s: [[case]] 缺 'category'：%r" % (path, case))
        out.append(dict(case, id=cid))
    return out


def _without_skip(rec, skip):
    """成对剔除 `dst`/`val` 中命中 `skip` 的条目（E4：来源未定义）。"""
    dst = rec.get("dst") or []
    val = rec.get("val") or []
    if not skip:
        return dst, val
    kept = [(name, value) for name, value in zip(dst, val)
            if name not in skip]
    return [name for name, _ in kept], [value for _, value in kept]


def compare_records(qrecs, erecs):
    if len(qrecs) != len(erecs):
        return "记录数 %d != QEMU %d" % (len(erecs), len(qrecs))
    for i, (q, e) in enumerate(zip(qrecs, erecs)):
        # 两侧各自记录「被 E4 跳过」的 RA 条目；取并集后成对剔除。
        # 单侧跳过 ⇒ 该条目在另一侧本不应参与比较（物理布局不同）。
        skip = set(q.get("skip") or ()) | set(e.get("skip") or ())
        qdst, qval = _without_skip(q, skip)
        edst, eval_ = _without_skip(e, skip)
        for key in FIELDS:
            if key == "dst":
                got, want = qdst, edst
            elif key == "val":
                got, want = qval, eval_
            else:
                got, want = q.get(key), e.get(key)
            if got != want:
                return ("第 %d 条（pc %s）%s: exec %r != QEMU %r"
                        % (i + 1, q.get("pc"), key, want, got))
    return None


def compare_states(qstates, estates):
    if len(qstates) != len(estates):
        return "状态数 %d != QEMU %d" % (len(estates), len(qstates))
    for i, (q, e) in enumerate(zip(qstates, estates)):
        for key in ("mode", "cfx"):
            if q.get(key) != e.get(key):
                return "第 %d 条指令后 %s: exec %r != QEMU %r" % (
                    i + 1, key, e.get(key), q.get(key))
    return None


def run_case(case, cfg):
    cid = case["id"]
    elf = Path(cfg["images"]) / cid / (cid + ".elf")
    if not elf.is_file():
        return {"id": cid, "ok": False, "detail": "missing image %s" % elf}
    obs = idl_qemu_trace.observe(elf, cfg["bootrom"], qemu=cfg["qemu"])
    image = idl_qemu_trace.ImageMap(elf, cfg["bootrom"], cfg["hmon_base"])
    qtrace = idl_qemu_trace.derive_trace(obs["records"], image, cfg["decoder"])
    try:
        etrace = idl_exec_trace.build_trace(elf, cfg["bootrom"], obs["entry"])
    except Exception as exc:  # ExecError/IO：保留现场，判 FAIL
        return {"id": cid, "category": case["category"], "ok": False,
                "detail": "exec: %s: %s" % (type(exc).__name__, exc)}
    detail = compare_records(qtrace["records"], etrace["records"]) \
        or compare_states(qtrace["states"], etrace["states"])
    if detail is None and etrace["exit_code"] != obs["qemu_rc"]:
        detail = "退出码 %r != QEMU %r" % (etrace["exit_code"], obs["qemu_rc"])
    if detail is None and etrace["output"] != obs["guest_out"]:
        detail = ("SYS_WRITEC 字节流 %d B != QEMU %d B"
                  % (len(etrace["output"]), len(obs["guest_out"])))
    if detail is None and not etrace["halted"]:
        detail = "执行器未在收尾 semihosting 停机"
    if cfg["trace_dir"] and detail is None:
        outdir = Path(cfg["trace_dir"]) / cid
        outdir.mkdir(parents=True, exist_ok=True)
        idl_exec_trace.write_trace(etrace["records"],
                               outdir / "exec.jsonl").close()
        writer = tc.TraceWriter(outdir / "qemu.jsonl")
        for rec in qtrace["records"]:
            writer.write(rec)
        writer.close()
    return {
        "id": cid, "category": case["category"], "ok": detail is None,
        "detail": detail or "records/states/exit/out 全等",
        "records": len(etrace["records"]),
        "duplicates": obs["duplicates"],
        "fetch_faults": etrace["fetch_faults"],
        "ra_skips": max(qtrace["ra_skips"], etrace["ra_skips"]),
        "rd8_skips": etrace["rd8_skips"],
        "unresolved": qtrace["unresolved"],
        "qemu_rc": obs["qemu_rc"], "exit_code": etrace["exit_code"],
        "bytes": len(etrace["output"]),
    }


def make_cfg(args):
    qemu = args.qemu or str(idl_qemu_trace.DEFAULT_QEMU)
    for what, path in (("qemu", qemu), ("bootrom", args.bootrom),
                       ("idl_exec.py", REPO_ROOT / "idl" / "tools" / "idl_exec.py")):
        if not Path(path).is_file():
            print("idl_check_trace: %s not found: %s" % (what, path),
                  file=sys.stderr)
            return None
    prof = idl_qemu_trace._machine_profile()
    return {"images": str(args.images), "bootrom": str(args.bootrom),
            "qemu": qemu, "hmon_base": prof.HMON_BASE,
            "decoder": idl_qemu_trace.Decoder(),
            "trace_dir": args.trace_dir}


def build_sample(cases, cfg, cid, count, around_exc=False):
    case = next((c for c in cases if c["id"] == cid), None)
    if case is None:
        raise SystemExit("idl_check_trace: sample case %r not in --cases"
                         % cid)
    elf = Path(cfg["images"]) / cid / (cid + ".elf")
    obs = idl_qemu_trace.observe(elf, cfg["bootrom"], qemu=cfg["qemu"])
    image = idl_qemu_trace.ImageMap(elf, cfg["bootrom"], cfg["hmon_base"])
    qtrace = idl_qemu_trace.derive_trace(obs["records"], image, cfg["decoder"])
    etrace = idl_exec_trace.build_trace(elf, cfg["bootrom"], obs["entry"])
    start = 0
    if around_exc:
        start = next((i for i, rec in enumerate(etrace["records"])
                      if rec["exc"] is not None), None)
        if start is None:
            raise SystemExit("idl_check_trace: %s has no exception record"
                             % cid)
        start = max(0, start - 2)
    window_q = qtrace["records"][start:start + count]
    window_e = etrace["records"][start:start + count]
    err = compare_records(window_q, window_e)
    if err:
        raise SystemExit("idl_check_trace: sample window mismatch: %s" % err)
    return window_e


def self_test():
    """`--cases` 清单键自检：`image` 可通过、缺键/缺文件明确报错。"""
    checks = []

    def eq(name, got, want):
        checks.append((name, got == want, got, want))

    def probe(path):
        """返回 (cases, rc, stderr 文本)；rc=None 表示成功。"""
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                return load_cases(path), None, buf.getvalue()
            except SystemExit as exc:
                return [], exc.code, buf.getvalue()

    with tempfile.TemporaryDirectory(prefix="trace-cases-") as td:
        tmp = Path(td)
        image = tmp / "add.st_orrr_rd.S"
        image.write_text("", encoding="utf-8")
        # 1) `image` 清单可通过：相对仓库根解析、用例名取 `Path(image).stem`
        rel = Path(os.path.relpath(image, REPO_ROOT)).as_posix()
        good = tmp / "good.toml"
        good.write_text('[[case]]\nimage = %s\ncategory = "alu"\n'
                        % json.dumps(rel), encoding="utf-8")
        cases, rc, text = probe(good)
        eq("image_manifest_rc", rc, None)
        eq("image_case_count", len(cases), 1)
        eq("image_case_id", cases[0]["id"] if cases else None, "add.st_orrr_rd")
        # 2) `image`/`id` 都缺 ⇒ rc=2 且指名缺键（不得是 KeyError 栈）
        bad = tmp / "missing.toml"
        bad.write_text('[[case]]\ncategory = "alu"\n', encoding="utf-8")
        cases, rc, text = probe(bad)
        eq("missing_key_rc", rc, 2)
        eq("missing_key_names_image", "image" in text, True)
        eq("missing_key_no_keyerror", "KeyError" not in text, True)
        # 3) `image` 指向不存在的文件 ⇒ rc=2 且指名（不得是 KeyError/回退）
        ghost = tmp / "ghost.toml"
        ghost.write_text('[[case]]\nimage = "tests/inst/00-ghost/none.S"\n'
                         'category = "alu"\n', encoding="utf-8")
        cases, rc, text = probe(ghost)
        eq("missing_file_rc", rc, 2)
        eq("missing_file_names_path", "不存在" in text, True)
        eq("missing_file_no_keyerror", "KeyError" not in text, True)

    failed = [c for c in checks if not c[1]]
    for name, ok, got, want in checks:
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s (got=%r want=%r)" % (name, got, want))
    print("self-test: %d/%d checks passed" % (len(checks) - len(failed),
                                              len(checks)))
    return 0 if not failed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="清单键自检（image 清单可通过 / 缺键、缺文件明确报错）")
    ap.add_argument("--cases", default=str(REPO_ROOT / "idl" / "data"
                                           / "idl_exec_cases.toml"))
    ap.add_argument("--images", default=None,
                    help="run_inst_tiny.py 的 --work-dir（内含 <id>/<id>.elf）")
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--only", action="append", default=None,
                    help="只跑这些 id（可重复；用于注入自检缩小范围）")
    ap.add_argument("--trace-dir", default=None,
                    help="把每个用例的两侧 trace 落盘（运行期证据目录）")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--sample-out", default=None)
    ap.add_argument("--sample-check", default=None)
    ap.add_argument("--sample-case", default=SAMPLE_CASE)
    ap.add_argument("--sample-records", type=int, default=SAMPLE_RECORDS)
    ap.add_argument("--sample-around-exc", action="store_true",
                    help="样例取第一个异常记录前后窗口（否则取开头窗口）")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.images or not args.bootrom:
        ap.error("--images and --bootrom required unless --self-test")

    cases = load_cases(args.cases)
    cfg = make_cfg(args)
    if cfg is None:
        return 2
    if args.only:
        wanted = set(args.only)
        cases = [c for c in cases if c["id"] in wanted]
        missing = wanted - {c["id"] for c in cases}
        if missing:
            print("idl_check_trace: unknown --only id: %s"
                  % ", ".join(sorted(missing)), file=sys.stderr)
            return 2
    if args.sample_out or args.sample_check:
        recs = build_sample(cases, cfg, args.sample_case, args.sample_records,
                            around_exc=args.sample_around_exc)
        if args.sample_check:
            original = Path(args.sample_check).read_text(encoding="utf-8")
            tmp = (Path(tempfile.mkdtemp(prefix="trace-sample-"))
                   / "sample.jsonl")
            writer = tc.TraceWriter(tmp)
            for rec in recs:
                writer.write(rec)
            writer.close()
            want = tmp.read_text(encoding="utf-8")
            ok = original == want
            print("[%s] sample %s（%d 条记录）"
                  % ("PASS" if ok else "FAIL", args.sample_check, len(recs)))
            return 0 if ok else 1
        writer = tc.TraceWriter(args.sample_out)
        for rec in recs:
            writer.write(rec)
        writer.close()
        print("idl_check_trace: sample -> %s（%d 条记录）"
              % (args.sample_out, len(recs)))
        return 0

    records = []
    for case in cases:
        rec = run_case(case, cfg)
        records.append(rec)
        print("[%s] %-22s %-8s records=%s dup=%s ffetch=%s ra_skip=%s "
              "rd8_skip=%s %s"
              % ("PASS" if rec["ok"] else "FAIL", rec["id"],
                 rec.get("category", ""), rec.get("records", "-"),
                 rec.get("duplicates", "-"), rec.get("fetch_faults", "-"),
                 rec.get("ra_skips", "-"), rec.get("rd8_skips", "-"),
                 rec["detail"]))
    npass = sum(1 for r in records if r["ok"])
    if not args.only and len(records) < 20:
        print("idl_check_trace: 用例数 %d < 20（验收下限）" % len(records),
              file=sys.stderr)
        return 2
    print("-" * 78)
    total = sum(r.get("records", 0) for r in records)
    print("idl_check_trace: %d/%d 用例逐指令 trace 与 QEMU 按 PC 对齐后全等"
          "（共 %d 条指令记录）" % (npass, len(records), total))
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"schema": "trace-parity/1", "records": records},
                       indent=1) + "\n", encoding="utf-8")
    return 0 if npass == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
