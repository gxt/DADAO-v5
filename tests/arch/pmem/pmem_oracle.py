#!/usr/bin/env python3
"""`pmem_oracle.py` — `tests/arch/pmem/pmem_dma.S` 的独立判据
（`m16-testcases-014`：cfx32 DMA 完成中断 + 同界多源；`m18-testcases-004` 改到 R3）。

期望值**现场**从真源派生，不从实现观测值反推：

  * `cfx_pmem` 的 cfxha（32）、SRAM 基址/大小、`cg15` 行号与位定义、
    `ERR_CODE` one-hot：`spec/DADAO-12 §4.9`、`spec/Kaiwu §1.1/§3`；
  * DMA 与 D-cache 的一致性（软件 `clean`/`invalidate` 的顺序与粒度）：
    `spec/DADAO-12 §4.9`「DMA 与 D-cache 的一致性（软件负责）」+ `§4.6`；
  * 源身份 = 源 cfxha（`TIMER` = 15、`PMEM_DMA` = 32）、monitor `cg15 rc3`
    掩码、源 `cg16` mask/pending/ack、`cg15` 捕获缓冲 / 每次进入整体覆盖 /
    同一界多源一次进入：`spec/DADAO-12 §4.7`、`§4.9`、`§5.4`、`ADR-0064`、
    `contract-see §3`；
  * `escape cfxHA` 的 `imms18` SBZ、`cg5 rc8`–`rc11` 出口意图与三类拒绝：`§5.1`/`§5.3`；
  * `CFXREG`/`CFXESC`/`ILLI` 位号：`contract-see §6.1`；
  * `cfx2rd`/`cfx2rc`/`escape` 编码：`contracts/opcodes.yaml`；
  * `cause_ip`：ELF 符号（投递发生在“下一条指令的边界”，该指令未执行）。

`pmem.S`（RTL 寄存器面探针，`m16-chipyard-022`）的 `facts()` 已是本节
真源的唯一解析实现；本文件复用它的解析与编码，只定义本 case 的槽序/期望
（`expected()`）与逐槽比对（`check()`）。

签名流 = 每个观测点 8 字节大端；槽序见 `expected()`（与探针 `REC` 一一对应）。
长度不符、任一槽不等 ⇒ 非零退出。

用法：
  pmem_oracle.py --stream FILE --elf FILE --mode {0,2,3} --nm llvm-nm --root ROOT
  pmem_oracle.py --expected --mode M --elf FILE --nm llvm-nm --root ROOT
  pmem_oracle.py --self-test --mode M --elf FILE --nm llvm-nm --root ROOT
"""

import argparse
import pathlib
import re
import struct
import sys

import check_pmem as base

SPEC = base.SPEC

# 探针输入（不是判据值）：探针写入的模式、PA 测试窗、DMA 长度与 cache 命令。
P1 = 0x0123456789ABCDEF
P2 = 0x1111222233334444
P3 = 0xAAAABBBBCCCCDDDD
P4 = 0x5555666677778888
PARTIAL_EXP = 0xAABBCC5A11223344
PA_T = 0x200000
CACHE_SPAN = 0x10000
DMA8 = 8
DMA3 = 3

CASES = {"arch-pmem-001": ("hmon",), "arch-pmem-002": ("smon", "umon")}
MODE_CODE = {"hmon": 3, "smon": 2, "umon": 0}

# 真源解析/编码/符号表复用 `check_pmem`（同一份 spec 解析实现）。
elf_symbols = base.elf_symbols
encode = base.encode
parse_opcode = base.parse_opcode


class OracleError(base.OracleError):
    """本 case 的期望派生错误（并入 check_pmem 的异常族）。"""


def facts(root):
    """`check_pmem.facts()` + 本 case 依赖的一致性/多源条款存在性检查。"""
    f = base.facts(root)
    spec = f["spec"]

    # §4.9（A）：DMA 与 D-cache 不保证硬件一致，软件在 START 前 clean、
    # DONE && BUSY=0 后 invalidate；粒度 = 整个参与区间（cache 行）。
    if not re.search(r"DMA \*\*不\*\*与 D-cache 做硬件一致性", spec):
        raise OracleError("spec §4.9: no-hardware-coherence clause not found")
    if not re.search(r"`START` \*\*之前\*\*.*?clean", spec):
        raise OracleError("spec §4.9: 'clean before START' not found")
    if not re.search(r"`DONE` 置位且 `BUSY=0` \*\*之后\*\*.*?invalidate", spec):
        raise OracleError("spec §4.9: 'invalidate after DONE' not found")
    if "`PA 区间` 范围覆盖整个参与区间" not in spec:
        raise OracleError("spec §4.9: PA-interval granularity not found")

    # §5.4（三）：同一界多源一次进入、位图并集、每次进入整体覆盖。
    if not re.search(r"\*\*一次性\*\*.*同一次捕获", spec):
        raise OracleError("spec §5.4: same-boundary single capture not found")
    if "位图并集" not in spec:
        raise OracleError("spec §5.4: bitmap union wording not found")
    if not re.search(r"每次异步进入都整体覆盖|每次进入整体覆盖", spec):
        raise OracleError("spec §5.4: 'every entry overwrites cg15' not found")

    return f


def _illi_info(root, ha, imm):
    """ILLI 的 `cause_info` = 触发指令编码（`§5.1` 步骤 0）。"""
    return base.encode(base.parse_opcode(root, "escape_ciii_cfx"),
                       cfxcode=ha, imm=imm)


def expected(root, mode, syms):
    f = facts(root)
    pmem_bit = 1 << f["mask_bit"]              # 源 cfxha 32
    timer_bit = 1 << f["timer_bit"]            # 源 cfxha 15
    illi = 1 << f["cause"]["ILLI"]
    err = f["err"]
    st_done = 1 << f["status"][1]
    st_err = 1 << f["status"][2]
    err_size = 1 << err["SIZE"]
    err_fault = 1 << err["PA_FAULT"]
    M = f["modes"]
    C = f["cfx"]
    hart = C["hart"]

    def sym(name):
        if name not in syms:
            raise OracleError("ELF symbol %s not found" % name)
        return syms[name]

    def same(slot):
        return ("slot", slot)

    if mode != M["hypv"]:
        prev_mode = M["user"] if mode == M["user"] else M["supv"]
        prev_cfx = C["umon"] if mode == M["user"] else C["smon"]
        return [
            ("%s mask row reads back all ones" % ("umon" if mode == M["user"]
                                                  else "smon"),
             0xFFFFFFFFFFFFFFFF),
            ("masked: pending = PMEM source bit", pmem_bit),
            ("masked: src_frame kept (capture buffer)", 0),
            ("masked: excp_async_num = 0", 0),
            ("capture prev_run_mode", prev_mode),
            ("capture prev_cfx_code", prev_cfx),
            ("capture cause_ip = delivery boundary", sym("umode_wait_begin")),
            ("capture src_frame = PMEM source bit", pmem_bit),
            ("capture src_pending after entry (not cleared, ack pending)", pmem_bit),
            ("capture excp_async_num = 1 entry", 1),
        ]

    esc3 = _illi_info(root, hart, 3)
    esc4 = _illi_info(root, hart, 4)
    exp = [
        ("DMA CFX->PA 8 B completes: DONE", st_done),
        ("DMA PA->CFX 8 B returns the pattern", P1),
        ("DMA 3 B partial beat keeps the neighbour byte", PARTIAL_EXP),
        ("SIZE: size = 0 -> ERROR|SIZE", st_err | err_size),
        ("ERROR W1C clears ERR_CODE", 0),
        ("PA_FAULT: DMA writing the BootROM", st_err | err_fault),
        ("ERROR W1C after PA_FAULT", 0),
        ("DMA reading the BootROM is legal: DONE", st_done),
        # ---- A: 软件 clean / invalidate（不依赖硬件一致） ----
        ("coherence CFX->PA: invalidated target reads the DMA value", P3),
        ("coherence PA->CFX: cleaned source is visible to the DMA", P4),
        # ---- escape 非法编码 ⇒ ILLI ----
        ("ILLI: escape imms18=3 (cause)", illi),
        ("ILLI: escape imms18=3 (info)", esc3),
        ("ILLI: escape imms18=3 witness", 0xC0DE0005),
        ("ILLI: escape imms18=4 (cause)", illi),
        ("ILLI: escape imms18=4 (info)", esc4),
        ("ILLI: escape imms18=4 witness", 0xC0DE0006),
        # ---- 捕获：屏蔽期只置 pending ----
        ("masked: pending = PMEM source bit", pmem_bit),
        ("masked: src_frame kept (capture buffer)", 0),
        ("masked: excp_async_num = 0", 0),
    ]
    base_slot = len(exp)
    exp += [
        ("capture prev_run_mode = hypv", M["hypv"]),
        ("capture prev_cfx_code = cfx_hmon", C["hmon"]),
        ("capture cause_ip = delivery boundary", sym("capture_fallback")),
        ("capture src_frame = PMEM source bit", pmem_bit),
        ("capture src_pending after entry (not cleared, ack pending)", pmem_bit),
        ("capture excp_async_num = 1 entry", 1),
        ("capture detail: dma_status = DONE", st_done),
        # ---- 正常异步返回：rc11 整字写 smon cg15 rc3（返回到 after_escape） ----
        ("escape rc11 whole word: smon mask = P1", P1),
        # ---- 源 ack ----
        ("ack: pending after W1C = 0", 0),
        ("ack: src_frame still the capture snapshot", pmem_bit),
        # ---- 同界多源：TIMER(15) + DMA(32) 一次进入 ----
        ("multi: pending = TIMER | PMEM", timer_bit | pmem_bit),
        ("multi: src_frame kept (not delivered yet)", pmem_bit),
        ("multi: excp_async_num = 1", 1),
    ]
    exp += [
        ("multi capture prev_run_mode = supv", M["supv"]),
        ("multi capture prev_cfx_code = cfx_hart", hart),
        ("multi capture cause_ip = delivery boundary", sym("multi_fallback")),
        ("multi capture src_frame = union bitmap", timer_bit | pmem_bit),
        ("multi capture src_pending = union (ack pending)", timer_bit | pmem_bit),
        ("multi capture excp_async_num = 2 entries", 2),
        ("multi ack: pending = 0", 0),
        # ---- 屏蔽 → pending → W1C ack → 放行无遗留投递 ----
        ("masked (supv): pending = PMEM bit", pmem_bit),
        ("ack: pending after W1C = 0", 0),
        ("unmask with no event does not deliver", 0xDEAD0006),
        # ---- 覆盖：不搬走再到期 ⇒ 第二次进入整体覆盖 ----
        ("overwrite: prev_run_mode = supv", M["supv"]),
        ("overwrite: prev_cfx_code = cfx_hart", hart),
        ("overwrite: cause_ip = new delivery boundary",
         sym("overwrite_fallback")),
        ("overwrite: src_frame = PMEM bit", pmem_bit),
        ("overwrite: src_pending after entry (not cleared)", pmem_bit),
        ("overwrite: excp_async_num = 3 entries", 3),
    ]
    return exp


def unpack(data):
    return base.unpack(data)


def check(recs, expected_slots):
    """与 `check_cfx15.check` 同型：谓词只有 `slot`（快照未变）。"""
    fails = []
    for i, (name, exp) in enumerate(expected_slots):
        act = recs[i] if i < len(recs) else None
        if isinstance(exp, tuple):
            kind = exp[0]
            if act is None:
                fails.append("slot %02d %-52s missing" % (i, name))
                continue
            if kind == "slot":
                ref = recs[exp[1]] if exp[1] < len(recs) else None
                if ref is None or act != ref:
                    fails.append("slot %02d %-52s expected == slot %d actual 0x%x"
                                 % (i, name, exp[1], act))
                    continue
            else:
                fails.append("slot %02d unknown predicate %r" % (i, kind))
                continue
        else:
            if act != exp:
                fails.append("slot %02d %-52s expected 0x%016x actual %s"
                             % (i, name, exp & 0xFFFFFFFFFFFFFFFF,
                                "missing" if act is None else "0x%016x" % act))
    if len(recs) > len(expected_slots):
        fails.append("stream has %d extra slot(s): first extra 0x%016x"
                     % (len(recs) - len(expected_slots),
                        recs[len(expected_slots)]))
    if len(recs) < len(expected_slots):
        fails.append("stream truncated: got %d slots, expected %d"
                     % (len(recs), len(expected_slots)))
    return fails


def self_test(root, mode, syms):
    exp = expected(root, mode, syms)
    ctl = []
    for _, v in exp:
        if isinstance(v, tuple):
            if v[0] == "slot":
                ctl.append(ctl[v[1]])
            else:
                raise OracleError("unknown predicate %r" % (v,))
        else:
            ctl.append(v)
    fails = list(check(ctl, exp))
    print("  [%s] control stream accepted" % ("PASS" if not fails else "FAIL"))
    for i, (name, v) in enumerate(exp):
        mut = list(ctl)
        if isinstance(v, tuple):
            if v[0] == "slot":
                mut[i] = ctl[v[1]] ^ 1
            else:
                raise OracleError("unknown predicate %r" % (v,))
        else:
            mut[i] ^= 0x5A
        if not check(mut, exp):
            fails.append("mutation of slot %d (%s) was not detected"
                         % (i, name))
    print("  [%s] every slot mutation is rejected"
          % ("PASS" if not fails else "FAIL"))
    if not check(ctl[:-1], exp):
        fails.append("truncated stream was accepted")
    if not check(ctl + [0], exp):
        fails.append("stream with an extra slot was accepted")
    print("  [%s] truncation / extra slot rejected"
          % ("PASS" if not fails else "FAIL"))
    for fmsg in fails:
        print("  [FAIL] %s" % fmsg)
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--mode", type=lambda x: int(x, 0), required=True)
    ap.add_argument("--elf")
    ap.add_argument("--nm")
    ap.add_argument("--stream")
    ap.add_argument("--expected", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    try:
        if args.elf and args.nm:
            syms = base.elf_symbols(args.nm, args.elf)
        else:
            syms = {n: 0x1000 + 8 * i for i, n in enumerate(
                ("capture_fallback", "multi_fallback", "overwrite_fallback",
                 "umode_wait_begin", "async_entry", "esc9_entry"))}
        exp = expected(args.root, args.mode, syms)
        if args.expected:
            for i, (name, v) in enumerate(exp):
                print("%02d %-52s %r" % (i, name, v))
            return 0
        if args.self_test:
            return self_test(args.root, args.mode, syms)
        if not args.stream:
            raise OracleError("--stream is required unless --expected/"
                              "--self-test")
        recs = unpack(pathlib.Path(args.stream).read_bytes())
        fails = check(recs, exp)
        if fails:
            for f in fails:
                print("FAIL %s" % f)
            print("pmem_oracle[%d]: %d slot(s) failed" % (args.mode, len(fails)))
            return 1
        print("pmem_oracle[%d]: %d slot(s) match" % (args.mode, len(exp)))
        return 0
    except OracleError as exc:
        print("pmem_oracle: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
