#!/usr/bin/env python3
"""check_pmem.py — `tests/arch/pmem/pmem.S` 的独立判据（`m16-chipyard-022`）。

期望值**现场**从真源派生，不从 RTL 观测值反推：

  * `cfx_pmem` 的 cfxha（32）：`contracts/cfx-aliases.txt` / `contract-see` §3；
  * cg/rc 行号与访问属性：`spec/DADAO-12 §4.9` 的专有寄存器表；
  * `dma_ctrl`/`dma_status` 位定义与 `ERR_CODE` one-hot 位号：`§4.9` 正文与
    ERR_CODE 表；
  * `dma_size` 合法范围 `1..2^29`：`§4.9` 正文；
  * cfx_pmem SRAM 基址/大小：`spec/Kaiwu` §1.1 的地址表；
  * `PMEM_DMA` 的源身份 = 源 cfxha（bit 32）与掩码位：`§5.4`、`contract-see` §3、
    `ADR-0061` D2；
  * `CFXREG`/`CFXESC` 位号：`§4.9` 异常原因表；
  * `cfx2rd`/`cfx2rc`/`escape` 编码：`contracts/opcodes.yaml`；
  * `cause_ip` 的期望：ELF 符号（投递发生在“下一条指令的边界”，该指令未执行）。

`pmem_exist` 的读回值不是 spec 指定的常量：本测试机约定 **64 个 PM 区域全部
存在**（`§4.9` “最多支持 64 个不连续 PM 区域”），见 `tests/arch/pmem/README.md`。

签名流 = 每个观测点 8 字节大端；槽序 = 本文件 `expected()`（与探针 `REC`
顺序一一对应）。长度不符、任一槽不等 ⇒ 非零退出。

用法：
  check_pmem.py --stream FILE --elf FILE --mode {0,2,3} --nm llvm-nm --root ROOT
  check_pmem.py --expected --mode M --elf FILE --nm llvm-nm --root ROOT
  check_pmem.py --self-test --mode M --elf FILE --nm llvm-nm --root ROOT
"""

import argparse
import pathlib
import re
import struct
import subprocess
import sys

import yaml

SPEC = "spec/DADAO-12-SEE-主管系统运行环境.md"
KAIWU = "spec/Kaiwu-测试机运行环境.md"
CONTRACT = ".tao/contracts/contract-see.md"
ALIASES = ".tao/contracts/contract-cfx-aliases.md"
ADR = ".tao/adr/adr-0061-async-source-index-and-mask-ownership.md"

# Probe inputs (not oracle values): patterns the probe writes and the SRAM
# offset it uses for the 1 KiB BUSY test.
PATTERN64 = 0x0123456789ABCDEF
PATTERN2 = 0xFEDCBA9876543210
PARTIALP = 0xAABBCC5A00000000
BUSY_SRC_OFF = 0x2000
PMEM_REGIONS = 64


class OracleError(Exception):
    pass


def read(root, rel):
    p = pathlib.Path(root) / rel
    if not p.is_file():
        raise OracleError("missing %s" % rel)
    return p.read_text(encoding="utf-8")


def facts(root):
    spec = read(root, SPEC)
    kaiwu = read(root, KAIWU)
    contract = read(root, CONTRACT)
    aliases = read(root, ALIASES)
    adr = read(root, ADR)

    # cfx_pmem's cfxha (`contract-cfx-aliases`).
    m = re.search(r"^\|\s*`cfx_pmem`\s*\|\s*`?(\d+)`?\s*\|", aliases, re.M)
    if not m:
        raise OracleError("contract-cfx-aliases: cfx_pmem row not found")
    pmem_ha = int(m.group(1))
    if pmem_ha != 32:
        raise OracleError("cfx_pmem cfxha must be 32, spec says %d" % pmem_ha)

    # cfx_pmem's SRAM base/size (`spec/Kaiwu` §1.1 address table).
    m = re.search(r"^\|\s*\*\*cfx_pmem SRAM\*\*\s*\|\s*`0x([0-9a-fA-F_]+)`\s*\|\s*"
                  r"(\d+)\s*KiB", kaiwu, re.M)
    if not m:
        raise OracleError("spec/Kaiwu §1.1: cfx_pmem SRAM row not found")
    sram_base = int(m.group(1).replace("_", ""), 16)
    sram_size = int(m.group(2)) * 1024

    # cfx_pmem's专有寄存器表 (`DADAO-12 §4.9`).
    rows = {}
    for cg, rc, _name, regname, _init, access, _note in re.findall(
            r"^\|\s*(\d+)\s*\|\s*([0-9-]+)\s*\|\s*([^|]+?)\s*\|\s*"
            r"(cfx_pmem_[a-z_\[\]\.0-9]+)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|",
            spec, re.M):
        rows[regname] = (int(cg), rc.strip(), access.strip())
    expect = {
        "cfx_pmem_exist": (8, "0", "RO"),
        "cfx_pmem_start[0..63]": (12, "0-63", "RW"),
        "cfx_pmem_size[0..63]": (13, "0-63", "RW"),
        "cfx_pmem_attr[0..63]": (14, "0-63", "RW"),
        "cfx_pmem_dma_src": (15, "0", "RW"),
        "cfx_pmem_dma_dst": (15, "1", "RW"),
        "cfx_pmem_dma_size": (15, "2", "RW"),
        "cfx_pmem_dma_ctrl": (15, "3", "RW"),
        "cfx_pmem_dma_status": (15, "4", "RW"),
    }
    for name, (cg, rc, access) in expect.items():
        if name not in rows:
            raise OracleError("spec §4.9: %s row not found" % name)
        if rows[name] != (cg, rc, access):
            raise OracleError("spec §4.9: %s must be cg%d rc%s %s, is %r"
                              % (name, cg, rc, access, rows[name]))

    # dma_ctrl / dma_status bit layout (§4.9 table row).
    def bit_of(text, name):
        m = re.search(r"bit(\d+)\s*=\s*%s" % name, text)
        if not m:
            raise OracleError("spec §4.9: %s bit not found" % name)
        return int(m.group(1))
    ctrl = rows["cfx_pmem_dma_ctrl"]
    status = rows["cfx_pmem_dma_status"]
    if "START" not in spec or "IRQ_EN" not in spec:
        raise OracleError("spec §4.9: dma_ctrl field names not found")
    ctrl_start = bit_of(spec, "START")
    ctrl_dir = bit_of(spec, "DIR")
    ctrl_irq = bit_of(spec, "IRQ_EN")
    st_busy = bit_of(spec, "BUSY")
    st_done = bit_of(spec, "DONE")
    st_error = bit_of(spec, "ERROR")
    if (ctrl_start, ctrl_dir, ctrl_irq) != (0, 1, 2):
        raise OracleError("spec §4.9: unexpected dma_ctrl bit layout")
    if (st_busy, st_done, st_error) != (0, 1, 2):
        raise OracleError("spec §4.9: unexpected dma_status bit layout")
    if not re.search(r"bit3-15\s*=\s*ERR_CODE", spec):
        raise OracleError("spec §4.9: ERR_CODE field position not found")

    # ERR_CODE one-hot bits (§4.9 ERR_CODE table).
    err = {}
    for bit, name in re.findall(
            r"^\|\s*bit(\d+)\s*\|\s*(SIZE|CFX_RANGE|PA_RANGE|PA_FAULT)\s*\|",
            spec, re.M):
        err[name] = int(bit)
    for need in ("SIZE", "CFX_RANGE", "PA_RANGE", "PA_FAULT"):
        if need not in err:
            raise OracleError("spec §4.9: ERR_CODE %s bit not found" % need)
    if sorted(err.values()) != [3, 4, 5, 6]:
        raise OracleError("spec §4.9: unexpected ERR_CODE bit layout %r" % err)

    # `dma_size` legal range 1..2^29 (`§4.9`).
    m = re.search(r"合法范围 `1\.\.2\^(\d+)`", spec)
    if not m or int(m.group(1)) != 29:
        raise OracleError("spec §4.9: dma_size range 1..2^29 not found")

    # Synchronous cause bits (§4.9 exception table).
    cause = {}
    for bit, name in re.findall(
            r"^\|\s*`1 << (\d+)`\s*\|\s*(CFXTRAP|CFXMEM|CFXREG|CFXESC|ILLI)\s*\|",
            spec, re.M):
        cause[name] = int(bit)
    for need in ("CFXREG", "CFXESC", "ILLI"):
        if need not in cause:
            raise OracleError("spec: cause bit for %s not found" % need)

    # Source identity = source cfxha (§5.4), mask bit in contract-see §3.
    if not re.search(r"`PMEM_DMA`\s*=\s*(\d+)", spec):
        raise OracleError("spec §5.4: PMEM_DMA cfxha not found")
    if int(re.search(r"`PMEM_DMA`\s*=\s*(\d+)", spec).group(1)) != pmem_ha:
        raise OracleError("spec §5.4: PMEM_DMA cfxha differs from cfx_pmem")
    m = re.search(r"`cfx_pmem`\s*⇒\s*bit\s*(\d+)", contract)
    if not m:
        raise OracleError("contract-see §3: cfx_pmem mask bit not found")
    mask_bit = int(m.group(1))
    if mask_bit != pmem_ha:
        raise OracleError("contract-see mask bit %d != cfx_pmem %d"
                          % (mask_bit, pmem_ha))
    m = re.search(r"`cfx_hart`\s*⇒\s*bit\s*(\d+)", contract)
    if not m:
        raise OracleError("contract-see §3: cfx_hart mask bit not found")
    timer_bit = int(m.group(1))

    # Modes and monitors (§1).  The probe's three images use H/S/U.
    modes = {}
    for enc, abbr in re.findall(
            r"^\|\s*(0b[01]+)\s*\|\s*[^|]*\|\s*(user|jail|supv|hypv)\s*\|",
            spec, re.M):
        modes[abbr] = int(enc, 2)
    cfx = {}
    for ha, name in re.findall(
            r"^\|\s*(\d+)\s*\|\s*(umon|jmon|smon|hmon|hart|pmem)\s*\|",
            spec, re.M):
        cfx[name] = int(ha)
    for need in ("user", "supv", "hypv"):
        if need not in modes:
            raise OracleError("spec §1: mode %s not found" % need)
    for need in ("umon", "smon", "hmon", "hart", "pmem"):
        if need not in cfx:
            raise OracleError("spec §1: cfx %s not found" % need)

    # R2: cg9 is a capture buffer, `escape imms18 = 2` is not an async return.
    if not re.search(r"不用于异步返回|不作为异步返回", spec):
        raise OracleError("spec §5.1/§5.4: 'cg9 is not an async return' missing")
    if not re.search(r"每次异步进入都整体覆盖|每次进入整体覆盖", spec):
        raise OracleError("spec: 'every entry overwrites cg9' missing")
    if not re.search(r"7 槽", adr):
        raise OracleError("ADR-0061: seven-slot cg9 decision not found")

    return dict(spec=spec, pmem_ha=pmem_ha, sram_base=sram_base,
                sram_size=sram_size, rows=rows, ctrl=(ctrl_start, ctrl_dir,
                ctrl_irq), status=(st_busy, st_done, st_error), err=err,
                cause=cause, mask_bit=mask_bit, timer_bit=timer_bit,
                modes=modes, cfx=cfx)


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
    ha = f["pmem_ha"]
    src_bit = 1 << f["mask_bit"]
    timer_bit = 1 << f["timer_bit"]
    cfxreg = 1 << f["cause"]["CFXREG"]
    cfxesc = 1 << f["cause"]["CFXESC"]
    illi = 1 << f["cause"]["ILLI"]
    err = f["err"]
    st_busy = 1 << f["status"][0]
    st_done = 1 << f["status"][1]
    st_err = 1 << f["status"][2]
    err_size = 1 << err["SIZE"]
    err_cfx = 1 << err["CFX_RANGE"]
    err_pa = 1 << err["PA_RANGE"]
    err_fault = 1 << err["PA_FAULT"]
    M = f["modes"]
    C = f["cfx"]

    rd = lambda cg, rc, dst: encode(
        parse_opcode(root, "cfx2rd_crrr_cfx"),
        cfxcode=ha, cfx_cg=cg, cfx_rc=rc, dst=dst)
    rc_ = lambda cg, rc, dst: encode(
        parse_opcode(root, "cfx2rc_crrr_cfx"),
        cfxcode=ha, cfx_cg=cg, cfx_rc=rc, dst=dst)

    def sym(name):
        if name not in syms:
            raise OracleError("ELF symbol %s not found" % name)
        return syms[name]

    if mode != M["hypv"]:
        prev_mode = M["user"] if mode == M["user"] else M["supv"]
        prev_cfx = C["umon"] if mode == M["user"] else C["smon"]
        return [
            ("masked: pending = PMEM source bit", src_bit),
            ("masked: src_frame kept (capture buffer)", 0),
            ("capture prev_run_mode", prev_mode),
            ("capture prev_cfx_code", prev_cfx),
            ("capture cause_ip = delivery boundary", sym("umode_wait_begin")),
            ("capture src_frame = PMEM source bit", src_bit),
            ("capture src_pending after delivery = 0", 0),
            ("capture excp_async_num = 1 entry", 1),
        ]

    exp = [
        # ---- register face -------------------------------------------------
        ("pmem_exist = 64 PM regions (test-machine convention)",
         (1 << PMEM_REGIONS) - 1),
        ("CFXREG: write pmem_exist (cause)", cfxreg),
        ("CFXREG: write pmem_exist (info)", rc_(8, 0, 6)),
        ("CFXREG: write pmem_exist witness", 0xC0DE0001),
        ("pmem_start[0] RW", PATTERN64),
        ("pmem_start[63] RW", PATTERN2),
        ("pmem_size[0] RW", PATTERN64),
        ("pmem_attr[63] RW", PATTERN2),
        ("dma_src RW", PATTERN64),
        ("dma_dst RW", PATTERN2),
        ("dma_size is a 30-bit field", 0x3FFFFFFF),
        ("dma_ctrl: START self-clears, DIR|IRQ_EN read back", 0x6),
        ("CFXREG: read cg15 rc5 (cause)", cfxreg),
        ("CFXREG: read cg15 rc5 (info)", rd(15, 5, 5)),
        ("CFXREG: read cg15 rc5 witness", 0xC0DE0002),
        ("CFXREG: read cg15 rc63 (cause)", cfxreg),
        ("CFXREG: read cg15 rc63 (info)", rd(15, 63, 5)),
        ("CFXREG: read cg15 rc63 witness", 0xC0DE0003),
        ("CFXREG: read cg8 rc1 reserved (cause)", cfxreg),
        ("CFXREG: read cg8 rc1 reserved (info)", rd(8, 1, 5)),
        ("CFXREG: read cg8 rc1 reserved witness", 0xC0DE0004),
        # ---- DMA -----------------------------------------------------------
        ("DMA CFX->PA 8 B completes: DONE", st_done),
        ("DMA PA->CFX 8 B returns the pattern", PATTERN64),
        ("DMA 32 B word 0", 0x1111111111111111),
        ("DMA 32 B word 1", 0x2222222222222222),
        ("DMA 32 B word 2", 0x3333333333333333),
        ("DMA 32 B word 3", 0x4444444444444444),
        ("DMA 3 B: partial beat keeps the neighbour byte", PARTIALP),
        ("DMA 6 B unaligned: destination low word (beat crossing)",
         0xDEADBEEFCAFE0077),
        ("DMA 6 B unaligned: destination high word (beat crossing)",
         0x8899AABBCC111111),
        ("DMA CFX end boundary 0xFFF8 + 8: DONE", st_done),
        ("SIZE: size = 0", st_err | err_size),
        ("ERROR W1C clears ERR_CODE", 0),
        ("SIZE: size > 2^29", st_err | err_size),
        ("SIZE: size = 2^29 passes SIZE, CFX_RANGE applies", st_err | err_cfx),
        ("CFX_RANGE: offset 0xFFFC + 8", st_err | err_cfx),
        ("CFX_RANGE: offset below 0x3ff_0000_0000", st_err | err_cfx),
        ("PA_RANGE: PA + size > 2^56", st_err | err_pa),
        ("PA_FAULT: DMA writing the BootROM", st_err | err_fault),
        ("PA read from the BootROM is legal: DONE", st_done),
        ("DONE W1C", 0),
        # ---- BUSY window ---------------------------------------------------
        ("BUSY during a 1 KiB transfer", st_busy),
        ("BUSY: dma_src write is ignored",
         (f["sram_base"] + BUSY_SRC_OFF) & ((1 << 64) - 1)),
        ("status after the transfer: DONE", st_done),
        ("W1C after BUSY", 0),
        ("ILLI: escape imms18=3 (cause)", illi),
        ("ILLI: escape imms18=3 (info)", 0x7E3C0003),
        ("ILLI: escape imms18=3 witness", 0xC0DE0005),
        ("ILLI: escape imms18=4 (cause)", illi),
        ("ILLI: escape imms18=4 (info)", 0x7E3C0004),
        ("ILLI: escape imms18=4 witness", 0xC0DE0006),
        # ---- capture: masked -> pending ------------------------------------
        ("masked: pending = PMEM source bit", src_bit),
        ("masked: src_frame kept (capture buffer)", 0),
        ("masked: excp_async_num = 0", 0),
    ]
    base = len(exp)
    exp += [
        ("capture prev_run_mode = hypv", M["hypv"]),
        ("capture prev_cfx_code = cfx_hmon", C["hmon"]),
        ("capture cause_ip = delivery boundary", sym("capture_fallback")),
        ("capture src_frame = PMEM source bit", src_bit),
        ("capture src_pending after delivery = 0", 0),
        ("capture excp_async_num = 1 entry", 1),
        # `escape imms18 = 2` ⇒ CFXESC, cg9 unchanged
        ("CFXESC: cg5 cause = CFXESC", cfxesc),
        ("CFXESC: cg5 cause_info = escape encoding",
         encode(parse_opcode(root, "escape_ciii_cfx"), cfxcode=C["hart"],
                imm=2)),
        ("CFXESC: cg5 prev_run_mode = supv", M["supv"]),
        ("CFXESC: cg5 prev_cfx_code = cfx_hart", C["hart"]),
        ("CFXESC: cg9 prev_mode unchanged", ("slot", base + 0)),
        ("CFXESC: cg9 prev_cfx unchanged", ("slot", base + 1)),
        ("CFXESC: cg9 cause_ip unchanged", ("slot", base + 2)),
        ("CFXESC: cg9 src_frame unchanged", ("slot", base + 3)),
        # ---- same-boundary multi-source ------------------------------------
        ("multi: pending = TIMER | PMEM", timer_bit | src_bit),
        ("multi: src_frame kept (not delivered yet)", src_bit),
        ("multi: excp_async_num = 1", 1),
        ("multi capture prev_run_mode = supv", M["supv"]),
        # The first entry already switched to cfx_hart/supv, so the second
        # one records cfx_hart as the interrupted cfx (not cfx_smon).
        ("multi capture prev_cfx_code = cfx_hart", C["hart"]),
        ("multi capture cause_ip = delivery boundary", sym("multi_fallback")),
        ("multi capture src_frame = union bitmap", timer_bit | src_bit),
        ("multi capture src_pending = 0", 0),
        ("multi capture excp_async_num = 2 entries", 2),
        # ---- source ack ----------------------------------------------------
        ("ack: pending before W1C = PMEM bit", src_bit),
        ("ack: pending after W1C = 0", 0),
        ("ack: unmask with no event does not deliver", 0xDEAD0006),
        # ---- overwrite -----------------------------------------------------
        ("overwrite: prev_run_mode = supv", M["supv"]),
        ("overwrite: cause_ip = new delivery boundary",
         sym("overwrite_fallback")),
        ("overwrite: src_frame = PMEM bit", src_bit),
        ("overwrite: src_pending = 0", 0),
        ("overwrite: excp_async_num = 3 entries", 3),
    ]
    return exp


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
            if kind == "slot":
                ref = recs[exp[1]] if exp[1] < len(recs) else None
                if ref is None or act != ref:
                    fails.append("slot %02d %-46s expected == slot %d actual 0x%x"
                                 % (i, name, exp[1], act))
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
    ctl = []
    for _, v in exp:
        if isinstance(v, tuple):
            if v[0] == "slot":
                ctl.append(ctl[v[1]])
            else:
                raise OracleError("unknown predicate %r" % (v,))
        else:
            ctl.append(v)
    fails = []
    f = check(ctl, exp)
    print("  [%s] control stream accepted" % ("PASS" if not fails else "FAIL"))
    fails += f
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
            fails.append("mutation of slot %d (%s) was not detected" % (i, name))
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
            syms = elf_symbols(args.nm, args.elf)
        else:
            syms = {n: 0x1000 + 8 * i for i, n in enumerate(
                ("capture_fallback", "multi_fallback", "overwrite_fallback",
                 "umode_wait_begin", "async_entry", "esc9_entry"))}
        exp = expected(args.root, args.mode, syms)
        if args.expected:
            for i, (name, v) in enumerate(exp):
                print("%02d %-46s %r" % (i, name, v))
            return 0
        if args.self_test:
            return self_test(args.root, args.mode, syms)
        if not args.stream:
            raise OracleError("--stream is required unless --expected/--self-test")
        recs = unpack(pathlib.Path(args.stream).read_bytes())
        fails = check(recs, exp)
        if fails:
            for f in fails:
                print("FAIL %s" % f)
            print("check_pmem[%d]: %d slot(s) failed" % (args.mode, len(fails)))
            return 1
        print("check_pmem[%d]: %d slot(s) match" % (args.mode, len(exp)))
        return 0
    except OracleError as exc:
        print("check_pmem: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
