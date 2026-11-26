#!/usr/bin/env python3
"""idl_exec_trace.py — 用 `idl/tools/idl_exec.py` 生成逐指令 trace（`m17-idl-004`）。

格式与字段口径见 `idl/docs/trace-format.md`；每条 JSONL 记录 = 一条**退休指令**
（取指异常没有自己的指令记录，其异常归并到前一条指令——与 QEMU `-d cpu` 的
记录边界一致）。

入口状态用 QEMU 的观测面（`--init <json>`，由 `idl/tools/idl_qemu_trace.py` 产出），
与 `idl/tools/idl_check_trace.py` 的口径相同。

用法：

    python3 idl/tools/idl_exec_trace.py --elf <elf> --bootrom <img> \
        --init <entry.json> --out <trace.jsonl> [--max-records N]
    python3 idl/tools/idl_exec_trace.py --self-test

退出码：0 = 正常；1 = 执行器/输入错误；2 = 参数问题。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True       # idl/ 由 check-manifests-guard 做目录断言
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import idl_exec  # noqa: E402
import idl_trace_common as tc  # noqa: E402

CFX_WATCH = (3, 63)
_EXIT_SERVICES = (idl_exec.SYS_EXIT, idl_exec.SYS_EXIT_EXTENDED)
_IMPL_DEFINED_SERVICES = (idl_exec.SYS_WRITEC, idl_exec.SYS_CLOCK,
                          idl_exec.SYS_EXIT, idl_exec.SYS_EXIT_EXTENDED)


def _cg4(machine):
    return {cfx: list(machine.cfx[cfx].cg4[2:5]) for cfx in CFX_WATCH
            if cfx in machine.cfx}


def _exc_of_step(machine, cg4_before):
    """本步异常：取发生计数增量的 cfx 的 cg5（cause_id/cause_ip/cause_info）。

    IDL `Cfx.cg5` 布局：`PREV_MODE/PREV_CFX/PREV_IP/PREV_INTR_MASK/CAUSE_ID/
    CAUSE_INFO`（`idl_exec.CG5_*`）；QEMU dump 的 `CID/CIP/CINFO` 与
    `CAUSE_ID`/`PREV_IP`/`CAUSE_INFO` 对应。
    """
    for cfx in CFX_WATCH:
        now = machine.cfx[cfx].cg4[2:5]
        if now != cg4_before[cfx]:
            frame = machine.cfx[cfx].cg5
            return tc.exc_object(
                cfx, frame[idl_exec.CG5_CAUSE_ID],
                frame[idl_exec.CG5_PREV_IP], frame[idl_exec.CG5_CAUSE_INFO])
    return None


def _snapshot(machine):
    """架构（逻辑）视图快照：四组全 64 槽，RA 按环形映射换算（sim §2.4.3）。"""
    return tc.snapshot(machine)


def build_trace(elf, bootrom, init_state=None, max_steps=2_000_000,
                max_records=None, profile="tiny"):
    """跑一个镜像，返回逐指令 trace 与统计。

    返回 `{"records": [...], "states": [...], "exit_code", "output",
    "steps", "fetch_faults", "rd8_skips", "halted"}`。
    """
    machine = idl_exec.new_machine(profile, bootrom=Path(bootrom))
    idl_exec.load_elf(machine, str(elf))
    if init_state is not None:
        machine.load_state(init_state)
    rd8_taint = False
    records, states = [], []
    fetch_faults = 0
    rd8_skips = 0
    while not machine.halted and machine.steps < max_steps:
        before = _snapshot(machine)
        cg4_before = _cg4(machine)
        machine.step()
        obs = machine.last_step
        after = _snapshot(machine)
        service = machine.semihost_service
        if service in _IMPL_DEFINED_SERVICES:
            rd8_taint = True
        elif before["rd"][8] != after["rd"][8]:
            rd8_taint = False
        if rd8_taint:
            rd8_skips += 1
        exc = _exc_of_step(machine, cg4_before)
        if obs["word"] is None:
            # 取指异常：QEMU 不为该地址出记录 ⇒ 没有独立指令；异常归前一条，
            # 前后状态也归前一条记录（handler 入口态）。
            fetch_faults += 1
            if not records:
                raise idl_exec.ExecError(
                    "fetch fault at %#x before any instruction" % obs["pc"])
            if exc is not None:
                records[-1]["exc"] = exc
            states[-1] = {"mode": machine.mode, "cfx": machine.cfx_code}
            continue
        dst, val = tc.reg_delta(before, after, rd8_ok=not rd8_taint)
        insn = machine.dec.decode(obs["word"])
        rec = tc.make_record(
            len(records) + 1, obs["pc"], obs["word"], obs["id"],
            insn.mnemonic if insn is not None else None, dst, val, exc)
        records.append(rec)
        states.append({"mode": machine.mode, "cfx": machine.cfx_code})
        if max_records is not None and len(records) >= max_records:
            break
    if not machine.halted and machine.steps >= max_steps:
        raise idl_exec.ExecError("step limit %d reached at ip %#x"
                                 % (max_steps, machine.ip))
    # 收尾 semihosting 是「执行前」观测的终点：QEMU 没有它的后状态记录
    # ⇒ trace 不含该条（退出码/semihosting 字节流单独比）。
    if machine.halted and records and machine.semihost_service in _EXIT_SERVICES:
        records.pop()
        states.pop()
    return {"records": records, "states": states,
            "exit_code": machine.exit_code,
            "output": bytes(machine.output), "steps": machine.steps,
            "fetch_faults": fetch_faults,
            "rd8_skips": rd8_skips, "halted": machine.halted}


def load_init(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_trace(records, out, max_bytes=tc.DEFAULT_MAX_BYTES):
    writer = tc.TraceWriter(out, max_bytes=max_bytes)
    for rec in records:
        writer.write(rec)
    return writer


def self_test():
    """trace 口径自检：全 64 槽按值比（含窗口外残留）、rd0/rb0、rd8 跳过、异常对象。"""
    checks = []

    def eq(name, got, want):
        checks.append((name, got == want, got, want))

    banks = {b: [0] * 64 for b in tc.BANKS}
    banks["ra"][0] = 0x0003_0000_0000_0000          # RACNT=3（窗口 ra61..63）
    after = {b: list(v) for b, v in banks.items()}
    after["rd"][5] = 7
    after["rb"][0] = 0x1234                          # rb0: 永不列出
    after["rd"][0] = 0
    after["ra"][63] = 9                              # 窗口内 ⇒ 列出
    after["ra"][1] = 9                               # 窗口外残留 ⇒ 也列出（全 64 槽）
    dst, val = tc.reg_delta(banks, after)
    eq("delta_rd", dst[:1], ["rd5"])
    eq("delta_no_rb0", "rb0" in dst, False)
    eq("delta_ra_window", "ra63" in dst, True)
    eq("delta_ra_window_outside", "ra1" in dst, True)
    eq("delta_values", val[0], "0x0000000000000007")
    # 窗口外槽值不变 ⇒ 不列出（只比「值变化」，不是无条件全列）
    after["ra"][1] = banks["ra"][1]
    dst2, _ = tc.reg_delta(banks, after)
    eq("delta_ra_window_outside_unchanged", "ra1" in dst2, False)
    # rd8：semihosting 之后整条记录跳过
    banks3 = {b: [0] * 64 for b in tc.BANKS}
    after3 = {b: list(v) for b, v in banks3.items()}
    after3["rd"][8] = 0xDEADBEEF
    dst3, _ = tc.reg_delta(banks3, after3, rd8_ok=False)
    eq("rd8_skipped", "rd8" in dst3, False)
    # 异常对象字段
    exc = tc.exc_object(3, 0x200000000000002, 0x1000, 0x1000)
    eq("exc_cause", exc["cause"], "0x0200000000000002")
    eq("exc_cfx", exc["cfx"], 3)
    failed = [c for c in checks if not c[1]]
    for name, ok, got, want in checks:
        print("%s %s" % ("PASS" if ok else "FAIL", name))
    print("self-test: %d/%d checks passed" % (len(checks) - len(failed),
                                              len(checks)))
    return 0 if not failed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--elf", default=None)
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--init", default=None, help="入口架构状态 JSON（QEMU 观测面）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-bytes", type=int, default=tc.DEFAULT_MAX_BYTES)
    ap.add_argument("--max-records", type=int, default=None)
    ap.add_argument("--summary-out", default=None)
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.elf or not args.out:
        ap.error("--elf and --out required unless --self-test")
    init = load_init(args.init) if args.init else None
    trace = build_trace(args.elf, args.bootrom, init,
                        max_records=args.max_records)
    writer = write_trace(trace["records"], args.out, max_bytes=args.max_bytes)
    parts = writer.close()
    summary = {"elf": str(args.elf), "instructions": len(trace["records"]),
               "steps": trace["steps"],
               "fetch_faults": trace["fetch_faults"],
               "rd8_skips": trace["rd8_skips"],
               "exit_code": trace["exit_code"],
               "output_bytes": len(trace["output"]),
               "parts": parts, "bytes": writer.bytes}
    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(summary) + "\n",
                                          encoding="utf-8")
    print("idl_exec_trace: %s instructions=%d steps=%d fetch_faults=%d "
          "bytes=%d parts=%d" % (Path(args.elf).name, len(trace["records"]),
                                 trace["steps"], trace["fetch_faults"],
                                 writer.bytes, len(parts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
