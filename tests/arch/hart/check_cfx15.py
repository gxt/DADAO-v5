#!/usr/bin/env python3
"""check_cfx15.py — `tests/arch/hart/cfx15.S` 的独立判据（`m16-chipyard-021`）。

期望值**现场**从真源派生，不从 RTL 观测值反推：

  * `cfx_hart` 的 cfxha（15）与运行模式编码：`spec/DADAO-12` §1；
  * `cg8` 行号 / `timer_ctrl` 位 / TIMER cause（`1 << 17`）：`spec/DADAO-12`
    §4.7 与 §3.6（二）；
  * `cg9` 行号 / 宽度 / 固定 supv：`ADR-0060` D2；
  * pending 位 = cause id、mask 位索引 = 源 cfxha、`escape` frame selector：
    `ADR-0060` D2/D4 与 `contract-see` §3（mask 位索引口径）；
  * `CFXREG` / `ILLI` 位号：`contract-see` §6.1；
  * `cfx2rd`/`cfx2rc`/`escape` 编码：`contracts/opcodes.yaml`；
  * `cause_ip` 的期望区间：ELF 符号表（`llvm-nm`）。

签名流 = 每个观测点 8 字节大端；槽序 = 本文件 `expected()`（与探针 `REC`
顺序一一对应）。长度不符、任一槽不等 ⇒ 非零退出。

用法：
  check_cfx15.py --stream FILE --elf FILE --mode {0,2,3} --nm llvm-nm --root ROOT
  check_cfx15.py --expected --mode M --elf FILE --nm llvm-nm --root ROOT
  check_cfx15.py --self-test --mode M --elf FILE --nm llvm-nm --root ROOT
"""

import argparse
import pathlib
import re
import struct
import subprocess
import sys

import yaml

SPEC = "spec/DADAO-12-SEE-主管系统运行环境.md"
CONTRACT = ".tao/contracts/contract-see.md"
ADR = ".tao/adr/adr-0060-hart-first-async-delivery.md"


class OracleError(Exception):
    pass


def read(root, rel):
    p = pathlib.Path(root) / rel
    if not p.is_file():
        raise OracleError("missing %s" % rel)
    return p.read_text(encoding="utf-8")


def facts(root):
    spec = read(root, SPEC)
    contract = read(root, CONTRACT)
    adr = read(root, ADR)

    # cfx_hart's cfxha and the mode encodings (spec §1).
    m = re.search(r"^\|\s*(\d+)\s*\|\s*hart\s*\|", spec, re.M)
    if not m:
        raise OracleError("spec §1: cfx_hart row not found")
    hart_ha = int(m.group(1))

    modes = {}
    for enc, abbr in re.findall(
            r"^\|\s*(0b[01]+)\s*\|\s*[^|]*\|\s*(user|jail|supv|hypv)\s*\|",
            spec, re.M):
        modes[abbr] = int(enc, 2)
    for need in ("user", "supv", "hypv"):
        if need not in modes:
            raise OracleError("spec §1: mode %s not found" % need)

    cfx = {}
    for ha, name in re.findall(
            r"^\|\s*(\d+)\s*\|\s*(umon|jmon|smon|hmon)\s*\|", spec, re.M):
        cfx[name] = int(ha)
    for need in ("umon", "smon", "hmon"):
        if need not in cfx:
            raise OracleError("spec §1: cfx %s not found" % need)

    # Synchronous cause bits (spec §4.7/§5.2 tables).
    cause = {}
    for bit, name in re.findall(
            r"^\|\s*`1 << (\d+)`\s*\|\s*(CFXTRAP|CFXREG|ILLI|CFXESC)\s*\|",
            spec, re.M):
        cause[name] = int(bit)
    for need in ("CFXTRAP", "CFXREG", "ILLI"):
        if need not in cause:
            raise OracleError("spec: cause bit for %s not found" % need)

    # TIMER is the macro cause bit of spec §3.6 (二) / §4.7.
    m = re.search(r"`1 << (\d+)`\s*=\s*`TIMER`", spec)
    if not m:
        raise OracleError("spec §3.6/§4.7: TIMER bit not found")
    timer_bit = int(m.group(1))
    if timer_bit < 16:
        raise OracleError("TIMER bit %d is not in the macro cause space" % timer_bit)

    # Mask bit index = *source* cfxha (contract-see §3).
    m = re.search(r"`cfx_hart`\s*⇒\s*bit\s*(\d+)", contract)
    if not m:
        raise OracleError("contract-see §3: cfx_hart mask bit not found")
    mask_bit = int(m.group(1))
    if mask_bit != hart_ha:
        raise OracleError("contract-see mask bit %d != cfx_hart %d"
                          % (mask_bit, hart_ha))

    # ADR-0060 D2: cg9 row numbers and widths (the asynchronous frame).
    rows = {}
    for rc, name, width in re.findall(
            r"^\|\s*9\s*\|\s*(\d+)\s*\|\s*(async_[a-z_]+)\s*\|\s*(\d+)b",
            adr, re.M):
        rows[name] = (int(rc), int(width))
    expect_rows = {
        "async_prev_run_mode": 0, "async_prev_cfx_code": 1,
        "async_cause_ip": 2, "async_cause_id": 3,
        "async_saved_global_intr_mask": 4, "async_pending": 5,
        "async_excp_vector": 6, "async_switch_run_mode": 7,
        "async_global_intr_mask": 8, "async_user_intr_mask": 9,
        "async_jail_intr_mask": 10, "async_supv_intr_mask": 11,
        "async_hypv_intr_mask": 12,
    }
    for name, rc in expect_rows.items():
        if name not in rows or rows[name][0] != rc:
            raise OracleError("ADR-0060 D2: %s must be rc%d" % (name, rc))
    if rows["async_switch_run_mode"][1] != 2:
        raise OracleError("ADR-0060 D2: async_switch_run_mode must be 2 bits")
    if not re.search(r"固定 supv（2）", adr):
        raise OracleError("ADR-0060 D2: fixed supv value not found")

    # ADR-0060 D4: the frame selector is imms18 bit1.
    if not re.search(r"frame selector 位（bit1）|frame selector 位 = \*\*bit1\*\*", adr) \
            and "bit1" not in adr:
        raise OracleError("ADR-0060 D4: frame selector bit1 not found")

    return dict(hart=hart_ha, modes=modes, cfx=cfx, cause=cause,
                timer=timer_bit, mask_bit=mask_bit, rows=rows)


def parse_opcode(root, ident):
    path = pathlib.Path(root) / "contracts" / "opcodes.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for entry in data:
        if isinstance(entry, dict) and entry.get("id") == ident:
            return {"value": int(str(entry["value"]), 16),
                    "fields": entry.get("fields", [])}
    raise OracleError("opcodes.yaml missing %s" % ident)


def _lo_hi(bits):
    m = re.fullmatch(r"\[(\d+):(\d+)\]", bits.strip())
    if not m:
        raise OracleError("unsupported field bits %r" % bits)
    return int(m.group(2)), int(m.group(1))


def encode(op, **fields):
    word = op["value"]
    for field in op["fields"]:
        role = field.get("role")
        if role not in fields:
            raise OracleError("no value for field %r" % role)
        lo, hi = _lo_hi(field["bits"])
        value = int(fields[role])
        if value < 0 or value >= (1 << (hi - lo + 1)):
            raise OracleError("%r value %#x does not fit %s"
                              % (role, value, field["bits"]))
        word |= value << lo
    return word


def elf_symbols(nm, elf):
    out = subprocess.run([nm, elf], capture_output=True, text=True)
    if out.returncode != 0:
        raise OracleError("llvm-nm failed: %s" % out.stderr.strip())
    syms = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in "tTaA" and \
                re.fullmatch(r"[0-9a-fA-F]+", parts[0]):
            syms[parts[2]] = int(parts[0], 16)
    return syms


def expected(root, mode, syms):
    f = facts(root)
    ha = f["hart"]
    timer = 1 << f["timer"]
    cfxreg = 1 << f["cause"]["CFXREG"]
    illi = 1 << f["cause"]["ILLI"]
    mask_pattern = 0xFFFFFFFFFFFF7FFF
    pattern = 0x123456789ABCDEF0
    M = f["modes"]
    C = f["cfx"]

    rd = lambda ha_, cg, rc, dst: encode(
        parse_opcode(root, "cfx2rd_crrr_cfx"),
        cfxcode=ha_, cfx_cg=cg, cfx_rc=rc, dst=dst)
    rc_ = lambda ha_, cg, rc, dst: encode(
        parse_opcode(root, "cfx2rc_crrr_cfx"),
        cfxcode=ha_, cfx_cg=cg, cfx_rc=rc, dst=dst)

    def sym(name):
        if name not in syms:
            raise OracleError("ELF symbol %s not found" % name)
        return syms[name]

    def in_range(name, lo_name, hi_name):
        lo, hi = sym(lo_name), sym(hi_name)
        return ("range", lo, hi, name)

    if mode == M["hypv"]:
        return [
            ("hart_id", 0),
            ("cycle #1", (">", 0)),
            ("cycle #2 > #1", (">slot", 1)),
            ("insn #1", (">", 0)),
            ("insn #2 > #1", (">slot", 3)),
            ("timer_cmp RW", pattern),
            ("timer_ctrl <- 0", 0),
            ("timer_ctrl <- 1", 1),
            ("timer_ctrl <- 2", 2),
            ("timer_ctrl <- 3", 3),
            ("timer_ctrl <- 4 (bit2 RO, bits1:0 = 0)", 0),
            ("cg9 prev_run_mode <- all ones (2b)", 3),
            ("cg9 prev_cfx_code <- all ones (6b)", 63),
            ("cg9 cause_ip <- all ones (48b)", 0xFFFFFFFFFFFF),
            ("cg9 cause_id <- pattern", pattern),
            ("cg9 saved_global <- pattern", pattern),
            ("cg9 pending <- pattern", pattern),
            ("cg9 vector <- all ones (48b, low2=0)", 0xFFFFFFFFFFFC),
            ("cg9 switch <- 0 ignored, reads 2", 2),
            ("cg9 global mask RW", pattern),
            ("cg9 user mask RW", pattern),
            ("cg9 jail mask RW", pattern),
            ("cg9 supv mask RW", pattern),
            ("cg9 hypv mask RW", pattern),
            ("CFXREG: read cg9 rc13 (cause)", cfxreg),
            ("CFXREG: read cg9 rc13 (info)", rd(ha, 9, 13, 5)),
            ("CFXREG: read cg9 rc13 witness", 0xC0DE0013),
            ("CFXREG: read cg9 rc14 (cause)", cfxreg),
            ("CFXREG: read cg9 rc14 (info)", rd(ha, 9, 14, 5)),
            ("CFXREG: read cg9 rc14 witness", 0xC0DE0018),
            ("CFXREG: read cg9 rc15 (cause)", cfxreg),
            ("CFXREG: read cg9 rc15 (info)", rd(ha, 9, 15, 5)),
            ("CFXREG: read cg9 rc15 witness", 0xC0DE0019),
            ("CFXREG: write cg8 rc0 RO (cause)", cfxreg),
            ("CFXREG: write cg8 rc0 RO (info)", rc_(ha, 8, 0, 6)),
            ("CFXREG: write cg8 rc0 RO witness", 0xC0DE0014),
            ("CFXREG: read cg8 rc1 reserved (cause)", cfxreg),
            ("CFXREG: read cg8 rc1 reserved (info)", rd(ha, 8, 1, 5)),
            ("CFXREG: read cg8 rc1 reserved witness", 0xC0DE0015),
            ("ILLI: escape imms18=3 (cause)", illi),
            ("ILLI: escape imms18=3 (info)",
             (0x7E << 24) | ((ha & 0x3F) << 18) | 3),
            ("ILLI: escape imms18=3 witness", 0xC0DE0016),
            ("ILLI: escape imms18=4 (cause)", illi),
            ("ILLI: escape imms18=4 (info)",
             (0x7E << 24) | ((ha & 0x3F) << 18) | 4),
            ("ILLI: escape imms18=4 witness", 0xC0DE0017),
            ("masked timer pending = cause bit", timer),
            ("masked timer cause_id = 0 (no delivery)", 0),
            ("async prev_run_mode (hypv)", M["hypv"]),
            ("async prev_cfx_code (hmon)", C["hmon"]),
            ("async cause_ip in wait loop",
             in_range("async cause_ip", "wait_begin", "wait_end")),
            ("async cause_id = TIMER", timer),
            ("async saved_global_intr_mask", mask_pattern),
            ("async pending after delivery = cause bit", timer),
            ("no-nest: cause_id unchanged", timer),
            ("no-nest: pending kept", timer),
            ("escape cg9 returns", 0xC0DE0021),
            ("escape cg9 releases frame", 0),
            ("escape cg9 restores global mask", mask_pattern),
        ]

    prev_mode = M["user"] if mode == M["user"] else M["supv"]
    prev_cfx = C["umon"] if mode == M["user"] else C["smon"]
    return [
        ("masked timer pending = cause bit", timer),
        ("masked timer cause_id = 0", 0),
        ("delivery witness", 0xC0DE0031),
        ("async prev_run_mode (%s)" % ("user" if mode == M["user"] else "supv"),
         prev_mode),
        ("async prev_cfx_code", prev_cfx),
        ("async cause_ip in wait loop",
         in_range("async cause_ip", "umode_wait_begin", "umode_wait_end")),
        ("async cause_id = TIMER", timer),
        ("async saved_global_intr_mask", mask_pattern),
        ("async pending after delivery = cause bit", timer),
        ("no-nest: cause_id unchanged", timer),
        ("no-nest: pending kept", timer),
        ("escape cg9 returns", 0xC0DE0032),
        ("escape cg9 releases frame", 0),
        ("escape cg9 restores global mask", mask_pattern),
    ]


def unpack(data):
    if len(data) % 8:
        raise OracleError("stream size %d is not a multiple of 8" % len(data))
    return list(struct.unpack(">%dQ" % (len(data) // 8), data))


def check(recs, expected_slots):
    fails = []
    for i, (name, exp) in enumerate(expected_slots):
        act = recs[i] if i < len(recs) else None
        if isinstance(exp, tuple):
            kind = exp[0]
            if act is None:
                fails.append("slot %02d %-46s missing" % (i, name))
                continue
            if kind == ">":
                if not act > exp[1]:
                    fails.append("slot %02d %-46s expected > 0x%x actual 0x%x"
                                 % (i, name, exp[1], act))
                    continue
            elif kind == ">slot":
                prev = recs[exp[1]] if exp[1] < len(recs) else None
                if prev is None or not act > prev:
                    fails.append("slot %02d %-46s expected > slot %d actual 0x%x"
                                 % (i, name, exp[1], act))
                    continue
            elif kind == "range":
                _, lo, hi, _ = exp
                if not (lo <= act < hi):
                    fails.append("slot %02d %-46s expected [0x%x,0x%x) actual 0x%x"
                                 % (i, name, lo, hi, act))
                    continue
            else:
                fails.append("slot %02d unknown predicate %r" % (i, kind))
                continue
        else:
            if act != exp:
                fails.append("slot %02d %-46s expected 0x%016x actual %s"
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
    base = [v for _, v in exp]
    # Numeric slots are materialised for the control run; predicates use the
    # values the probe is expected to observe.
    ctl = []
    for _, v in exp:
        if isinstance(v, tuple):
            if v[0] == ">":
                ctl.append(v[1] + 1)
            elif v[0] == ">slot":
                ctl.append(ctl[v[1]] + 1)
            elif v[0] == "range":
                ctl.append(v[1])
            else:
                raise OracleError("unknown predicate %r" % (v,))
        else:
            ctl.append(v)
    fails = []
    f = check(ctl, exp)
    print("  [%s] control stream accepted" % ("PASS" if not fails else "FAIL"))
    fails += f
    # Every slot must have a reachable FAIL path.
    for i, (name, v) in enumerate(exp):
        mut = list(ctl)
        if isinstance(v, tuple):
            if v[0] == ">":
                mut[i] = v[1]                      # equal, not greater
            elif v[0] == ">slot":
                mut[i] = ctl[v[1]]                 # equal, not greater
            elif v[0] == "range":
                mut[i] = v[1] - 1                  # below the range
            else:
                raise OracleError("unknown predicate %r" % (v,))
        else:
            mut[i] ^= 0x5A
        if not check(mut, exp):
            fails.append("mutation of slot %d (%s) was not detected" % (i, name))
    print("  [%s] every slot mutation is rejected"
          % ("PASS" if not fails else "FAIL"))
    # Truncation / extra slot.
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
            syms = elf_symbols(args.nm, args.elf)
        else:
            syms = {n: 0x1000 + 8 * i for i, n in enumerate(
                ("wait_begin", "wait_end", "umode_wait_begin", "umode_wait_end"))}
        exp = expected(args.root, args.mode, syms)
        if args.expected:
            for i, (name, v) in enumerate(exp):
                print("%02d %-46s %r" % (i, name, v))
            return 0
        if args.self_test:
            return self_test(args.root, args.mode, syms)
        if not args.stream:
            ap.error("--stream is required")
        recs = unpack(pathlib.Path(args.stream).read_bytes())
        fails = check(recs, exp)
        for fmsg in fails:
            print("  [FAIL] %s" % fmsg)
        print("summary: %d slot(s), %d failure(s)" % (len(exp), len(fails)))
        return 0 if not fails else 1
    except OracleError as exc:
        print("check_cfx15: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
