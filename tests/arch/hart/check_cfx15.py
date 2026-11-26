#!/usr/bin/env python3
"""check_cfx15.py — `tests/arch/hart/cfx15.S` 的独立判据
（`m16-chipyard-021` 起，`m18-testcases-004` 改到 R3）。

R3（`spec/DADAO-12 §3.6/§5.1/§5.3/§5.4`）：`cg9` rc0–rc5 是入口记录/捕获缓冲
（每次进入整体覆盖，无 `frame_valid`）；`cg5 rc8`–`rc11` 是出口意图，异步返回与
同步共用 `escape cfxHA`；`imms18` 必须为 0（非 0 ⇒ `ILLI`），升权/目标未实现/
`cfxha` 不符 ⇒ 当前 cfx 的 `CFXESC`。

期望值**现场**从真源派生，不从 RTL 观测值反推：

  * `cfx_hart` 的 cfxha（15）与运行模式编码：`spec/DADAO-12` §1；
  * `cg8` 行号 / `timer_ctrl` 位 / 源身份 = 源 cfxha（`TIMER` = 15）：
    `spec/DADAO-12` §4.7 与 §5.4（一）；
  * `cg9` 七槽的行号 / 访问属性 / 位宽、位图“软件只读（写忽略）”与
    “每次进入整体覆盖 / 无 `frame_valid`”：`spec/DADAO-12` §4.7 与 §5.4（二）(三)；
  * 来源掩码在 `cfx0`–`cfx3 cg8 rc1`、复位全 1、`0=允许/1=屏蔽`：
    `spec/DADAO-12` §4.1–§4.4 与 §5.4（一）；
  * `escape` 的 `imms18` SBZ、`rc8`–`rc11` 出口意图与三类拒绝（升权/目标未实现/`cfxha` 不符）：
    `spec/DADAO-12` §5.1/§5.4（七）；
  * `CFXREG` / `ILLI` / `CFXESC` 位号：`contract-see` §6.1；
  * `cfx2rd`/`cfx2rc`/`escape` 编码：`contracts/opcodes.yaml`；
  * `cause_ip` 的期望：ELF 符号（投递发生在“下一条指令的边界”，该指令未执行）。

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
ADR = ".tao/adr/adr-0061-async-source-index-and-mask-ownership.md"

# Probe inputs (not oracle values): the pattern the register face writes, the
# source mask with bit 15 open, and the two escape encodings the probe feeds in.
MASK_PATTERN = 0xFFFFFFFFFFFF7FFF
PATTERN64 = 0x123456789ABCDEF0


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
            r"^\|\s*(\d+)\s*\|\s*(umon|jmon|smon|hmon|power)\s*\|", spec, re.M):
        cfx[name] = int(ha)
    for need in ("umon", "smon", "hmon", "power"):
        if need not in cfx:
            raise OracleError("spec §1: cfx %s not found" % need)

    # Synchronous cause bits (spec §4.7/§5.2 tables).
    cause = {}
    for bit, name in re.findall(
            r"^\|\s*`1 << (\d+)`\s*\|\s*(CFXTRAP|CFXREG|ILLI|CFXESC)\s*\|",
            spec, re.M):
        cause[name] = int(bit)
    for need in ("CFXTRAP", "CFXREG", "CFXESC", "ILLI"):
        if need not in cause:
            raise OracleError("spec: cause bit for %s not found" % need)

    # §5.4(一): the async source identity is the source cfxha; TIMER is the
    # hart's own cfx.  There is no macro cause bit for async sources any more.
    m = re.search(r"`TIMER`\s*=\s*(\d+)", spec)
    if not m:
        raise OracleError("spec §5.4: TIMER source cfxha not found")
    timer_ha = int(m.group(1))
    if timer_ha != hart_ha:
        raise OracleError("spec: TIMER cfxha %d != cfx_hart %d"
                          % (timer_ha, hart_ha))
    if re.search(r"`1 << (\d+)`\s*=\s*`TIMER`", spec):
        raise OracleError("spec: a macro TIMER cause bit still exists")
    if not re.search(r"异步源不占本段|异步源标识不占", spec):
        raise OracleError("spec: async cause-id exclusion sentence not found")

    # Mask bit index = the same source cfxha (contract-see §3).
    m = re.search(r"`cfx_hart`\s*⇒\s*bit\s*(\d+)", contract)
    if not m:
        raise OracleError("contract-see §3: cfx_hart mask bit not found")
    mask_bit = int(m.group(1))
    if mask_bit != timer_ha:
        raise OracleError("contract-see mask bit %d != TIMER cfxha %d"
                          % (mask_bit, timer_ha))

    # cg9 table (spec §4.7, ADR-0061 R3): rc0-rc5 entry record (HW/RO),
    # rc14/rc15 configuration (RW); rc6-rc13 reserved.
    rows = {}
    for rc, _name, regname, _init, access, note in re.findall(
            r"^\|\s*9\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*"
            r"(cfx_hart_async_[a-z_]+)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|",
            spec, re.M):
        rows[regname] = (int(rc), access.strip(), note.strip())
    expect_rows = {
        "cfx_hart_async_prev_run_mode": (0, "HW/RO"),
        "cfx_hart_async_prev_cfx_code": (1, "HW/RO"),
        "cfx_hart_async_cause_ip": (2, "HW/RO"),
        "cfx_hart_async_prev_intr_mask": (3, "HW/RO"),
        "cfx_hart_async_src_frame": (4, "HW/RO"),
        "cfx_hart_async_src_pending": (5, "HW/RO"),
        "cfx_hart_async_switch_run_mode": (14, "RW"),
        "cfx_hart_async_excp_vector": (15, "RW"),
    }
    for name, (rc, access) in expect_rows.items():
        if name not in rows or rows[name][0] != rc:
            raise OracleError("spec §4.7: %s must be rc%d" % (name, rc))
        if rows[name][1] != access:
            raise OracleError("spec §4.7: %s must be %s, is %s"
                              % (name, access, rows[name][1]))
    if len(rows) != len(expect_rows):
        raise OracleError("spec §4.7: cg9 must have %d defined slots, parsed %d"
                          % (len(expect_rows), len(rows)))
    if not re.search(r"^\|\s*9\s*\|\s*6–13\s*\|\s*reserved", spec, re.M):
        raise OracleError("spec §4.7: cg9 rc6-rc13 reserved row not found")
    # rc0-rc5 are written by hardware only; a software write is ignored without
    # an exception (m18-spec-007 / ADR-0061 R3 D3).
    for name, (_rc, _access, cell) in (
            (n, v) for n, v in rows.items() if v[0] <= 5):
        if "软件只读" not in cell and "软件写忽略" not in cell:
            raise OracleError(
                "spec §4.7: %s must say '软件只读'/'软件写忽略'" % name)
    if not re.search(r"不产生异常", spec):
        raise OracleError("spec §4.7: 'write ignored, no exception' not stated")
    switch_cell = rows["cfx_hart_async_switch_run_mode"][2]
    if "复位值 2（supv）" not in switch_cell:
        raise OracleError("spec §4.7: rc14 must say '复位值 2（supv）'")
    if "异步进入取本寄存器当前值" not in switch_cell:
        raise OracleError("spec §4.7: rc14 must feed the async entry mode")

    # cg5 entry record rc0-rc3 is HW/RO and a write is CFXREG; rc8-rc11 is the
    # escape intent (HW/RW).
    cg5 = {}
    for rc, suffix, access in re.findall(
            r"^\|\s*5\s*\|\s*(\d+)\s*\|[^|]*\|[^|]*excp_([a-z_]+)\s*\|"
            r"[^|]*\|\s*([^|]*)\|",
            spec, re.M):
        cg5[suffix] = (int(rc), access.strip())
    for rc, suffix in ((0, "prev_run_mode"), (1, "prev_cfx_code"),
                       (2, "cause_ip"), (3, "prev_intr_mask")):
        if cg5.get(suffix) != (rc, "HW/RO"):
            raise OracleError("spec §3.6: excp_%s must be rc%d HW/RO"
                              % (suffix, rc))
    for rc, suffix in ((8, "escape_run_mode"), (9, "escape_cfx_code"),
                       (10, "escape_ip"), (11, "escape_intr_mask")):
        if cg5.get(suffix) != (rc, "HW/RW"):
            raise OracleError("spec §3.6: excp_%s must be rc%d HW/RW"
                              % (suffix, rc))
    if not re.search(r"`rc11` 复位值.*全 1|全 1（fail-safe", spec):
        raise OracleError("spec §3.6: rc11 reset all-ones not stated")
    if not re.search(r"不得高于", spec):
        raise OracleError("spec §5.1: no privilege-escalation rule")
    if not re.search(r"整字", spec):
        raise OracleError("spec §5.3: rc11 whole-word restore not stated")
    if not re.search(r"异步进入只写 `cfx_hart cg9 rc0`–`rc4`", spec):
        raise OracleError("spec §3.6: async write set not stated")

    # The async source mask row lives on cfx0-cfx3 (`cg8 rc1`, reset all ones).
    mask_rows = re.findall(
        r"^\|\s*8\s*\|\s*1\s*\|\s*async intr mask\s*\|\s*"
        r"cfx_(umon|jmon|smon|hmon)_async_intr_mask\s*\|\s*([^|]*)\|\s*"
        r"([^|]*)\|\s*([^|]*)\|", spec, re.M)
    if sorted(name for name, _, _, _ in mask_rows) != \
            ["hmon", "jmon", "smon", "umon"]:
        raise OracleError("spec §4.1-§4.4: the four async mask rows not found")
    for name, reset, access, note in mask_rows:
        if reset.strip() != "全1" or access.strip() != "RW":
            raise OracleError("spec §4.%s: async mask must be 全1/RW"
                              % name)
        if "当前运行模式" not in note:
            raise OracleError("spec §4.%s: mask must follow the running mode"
                              % name)
    # `cg0`-`cg3 rc4` is not defined any more (`ADR-0061` D5).
    if not re.search(r"`rc4`\s*不定义（保留，访问触发 `CFXREG`）", spec):
        raise OracleError("spec §3: rc4 must be reserved (CFXREG)")

    # ADR-0061 R3 is the decision this probe implements.
    if not re.search(r"R3", adr):
        raise OracleError("ADR-0061 R3 not found")
    if not re.search(r"escape cfxHA", spec):
        raise OracleError("spec: escape cfxHA form not found")
    if not re.search(r"`imms18` 必须为 \*\*0\*\*", spec):
        raise OracleError("spec §5.1: imms18 SBZ rule not found")
    if not re.search(r"每次异步进入都整体覆盖|每次进入整体覆盖", spec):
        raise OracleError("spec §4.7/§5.4: 'every entry overwrites cg9' missing")
    if not re.search(r"没有“帧活动期”|没有\"帧活动期\"", spec):
        raise OracleError("spec §5.4: 'no frame phase' missing")
    if not re.search(r"frame_valid", spec):
        raise OracleError("spec: frame_valid absence sentence missing")

    return dict(hart=hart_ha, modes=modes, cfx=cfx, cause=cause,
                timer=timer_ha, mask_bit=mask_bit, rows=rows)


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
    src_bit = 1 << f["timer"]          # source cfxha == bitmap bit
    cfxreg = 1 << f["cause"]["CFXREG"]
    cfxesc = 1 << f["cause"]["CFXESC"]
    illi = 1 << f["cause"]["ILLI"]
    M = f["modes"]
    C = f["cfx"]
    HMON_RESET = 0x7FFFFFFFFFFFFFF7    # spec §3.1-§3.4: hmon's own mask
    ALL1 = 0xFFFFFFFFFFFFFFFF

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

    vec = sym("async_entry") & ~0x3
    rearm_fb = sym("rearm_fallback") & ~0x3
    pend_fb = sym("pending_fallback") & ~0x3

    def async_loop(prev_mode, prev_cfx, wait_label, phase2_mode, phase2_cfx):
        """Slots from the first async entry through the jump precise point."""
        return [
            ("async prev_run_mode", prev_mode),
            ("async prev_cfx_code", prev_cfx),
            ("async prev ip = delivery boundary", wait_label),
            ("async prev intr mask = current-mode mask", MASK_PATTERN),
            ("async src_frame = TIMER source bit", src_bit),
            ("async src_pending after delivery = 0", 0),
            ("async switch read = cg9 rc14 (2)", 2),
            ("async vector read = cg9 rc15", vec),
            ("cfx_hart excp_async_num = 1 frame", 1),
            ("escape rc11 whole word: target monitor mask = ESC_RC11_PATTERN", 0x0123456789ABCDEF),
            ("escape_num = 1 after the async escape", 1),
            ("masked (all ones): pending = source bit", src_bit),
            ("masked: src_frame kept", src_bit),
            ("overwrite: prev_run_mode", phase2_mode),
            ("overwrite: prev_cfx_code", phase2_cfx),
            ("overwrite: prev ip = rearm boundary", rearm_fb),
            ("overwrite: prev intr mask", MASK_PATTERN),
            ("overwrite: src_frame = source bit", src_bit),
            ("overwrite: src_pending after delivery = 0", 0),
            ("overwrite: excp_async_num = 2 entries", 2),
            ("masked (supv): pending = source bit", src_bit),
            ("masked (supv): src_frame kept", src_bit),
            ("ack (timer_cmp rewrite): pending = 0", 0),
            ("re-armed while masked: pending = source bit", src_bit),
            ("third entry: prev_run_mode = supv", M["supv"]),
            ("third entry: prev ip = unmask boundary", pend_fb),
            ("third entry: prev intr mask", MASK_PATTERN),
            ("third entry: src_frame = source bit", src_bit),
            ("third entry: excp_async_num = 3 entries", 3),
            ("final ack: pending = 0", 0),
            ("jump target: prev ip = jump target", sym("jump_target")),
            ("jump target: prev_run_mode = supv", M["supv"]),
            ("jump target: prev_cfx_code = cfx_hart", ha),
            ("jump target: prev intr mask", MASK_PATTERN),
            ("jump target: src_frame = source bit", src_bit),
            ("jump target: converged", 1),
        ]

    def esc_criteria(info1, info3):
        return [
            ("CFXESC escalation: cause", cfxesc),
            ("CFXESC escalation: info = escape cfx_hart", info1),
            ("CFXESC escalation: prev ip", sym("esc_bad1")),
            ("CFXESC escalation: entry prev mode = supv", M["supv"]),
            ("CFXESC escalation: entry prev cfx = cfx_hart", ha),
            ("CFXESC escalation: monitor mask unchanged", MASK_PATTERN),
            ("CFXESC unimplemented target: cause", cfxesc),
            ("CFXESC unimplemented target: info = escape cfx_hart", info1),
            ("CFXESC unimplemented target: prev ip", sym("esc_bad2")),
            ("CFXESC unimplemented target: entry prev mode = supv", M["supv"]),
            ("CFXESC unimplemented target: entry prev cfx = cfx_hart", ha),
            ("CFXESC unimplemented target: monitor mask unchanged", MASK_PATTERN),
            ("CFXESC wrong cfxha: cause", cfxesc),
            ("CFXESC wrong cfxha: info = escape cfx_smon", info3),
            ("CFXESC wrong cfxha: prev ip", sym("esc_bad3")),
            ("CFXESC wrong cfxha: entry prev mode = supv", M["supv"]),
            ("CFXESC wrong cfxha: entry prev cfx = cfx_hart", ha),
            ("CFXESC wrong cfxha: monitor mask unchanged", MASK_PATTERN),
        ]

    if mode == M["hypv"]:
        head = [
            ("sync trap: prev_run_mode = hypv", M["hypv"]),
            ("sync trap: prev_cfx_code = cfx_hmon", C["hmon"]),
            ("sync trap: prev ip = trap address", sym("h_trap")),
            ("sync trap: prev intr mask = hmon cg8 rc1 reset", ALL1),
            ("sync trap: cause id = CFXTRAP", 1 << f["cause"]["CFXTRAP"]),
            ("sync trap: cause info = trap encoding", 0x7F0C0000),
            ("sync trap: escape run mode = hypv", M["hypv"]),
            ("sync trap: escape cfx code = cfx_hmon", C["hmon"]),
            ("sync trap: escape ip = trap address", sym("h_trap")),
            ("sync trap: escape intr mask = hmon cg8 rc1 reset", ALL1),
            ("hart_id", 0),
            ("cycle #1", (">", 0)),
            ("cycle #2 > #1", (">slot", 11)),
            ("insn #1", (">", 0)),
            ("insn #2 > #1", (">slot", 13)),
            ("timer_cmp RW", PATTERN64),
            ("timer_ctrl <- 0", 0),
            ("timer_ctrl <- 1", 1),
            ("timer_ctrl <- 2", 2),
            ("timer_ctrl <- 3", 3),
            ("timer_ctrl <- 4 (bit2 RO, bits1:0 = 0)", 0),
            ("cg9 rc0 prev_run_mode reset", 0),
            ("cg9 rc1 prev_cfx_code reset", 0),
            ("cg9 rc2 prev ip reset", 0),
            ("cg9 rc3 prev intr mask reset", 0),
            ("cg9 rc4 src_frame reset", 0),
            ("cg9 rc5 src_pending reset", 0),
            ("cg9 rc0 write ignored (HW/RO)", 0),
            ("cg9 rc4 write ignored (HW/RO)", 0),
            ("cg9 rc15 vector <- all ones (48b, low2=0)", 0xFFFFFFFFFFFF & ~0x3),
            ("cg9 rc14 reset = 2 (supv)", 2),
            ("cg9 rc14 <- 0 reads 0", 0),
            ("cg9 rc14 <- 1 reads 1", 1),
            ("cg9 rc14 <- 3 reads 3", 3),
            ("cg9 rc14 restore 2 reads 2", 2),
            ("CFXREG: read cg9 rc6 (cause)", cfxreg),
            ("CFXREG: read cg9 rc6 (info)", rd(ha, 9, 6, 5)),
            ("CFXREG: read cg9 rc6 witness", 0xC0DE0013),
            ("CFXREG: read cg9 rc7 (cause)", cfxreg),
            ("CFXREG: read cg9 rc7 (info)", rd(ha, 9, 7, 5)),
            ("CFXREG: read cg9 rc7 witness", 0xC0DE0014),
            ("CFXREG: read cg9 rc8 (cause)", cfxreg),
            ("CFXREG: read cg9 rc8 (info)", rd(ha, 9, 8, 5)),
            ("CFXREG: read cg9 rc8 witness", 0xC0DE0015),
            ("CFXREG: read cg9 rc13 (cause)", cfxreg),
            ("CFXREG: read cg9 rc13 (info)", rd(ha, 9, 13, 5)),
            ("CFXREG: read cg9 rc13 witness", 0xC0DE0016),
            ("CFXREG: write cg8 rc0 RO (cause)", cfxreg),
            ("CFXREG: write cg8 rc0 RO (info)", rc_(ha, 8, 0, 6)),
            ("CFXREG: write cg8 rc0 witness", 0xC0DE0017),
            ("CFXREG: write cg5 rc0 entry record (cause)", cfxreg),
            ("CFXREG: write cg5 rc0 entry record (info)", rc_(ha, 5, 0, 6)),
            ("CFXREG: write cg5 rc0 witness", 0xC0DE0018),
            ("CFXREG: read cg8 rc1 reserved (cause)", cfxreg),
            ("CFXREG: read cg8 rc1 reserved (info)", rd(ha, 8, 1, 5)),
            ("CFXREG: read cg8 rc1 reserved witness", 0xC0DE0019),
            ("ILLI: escape imms18=3 (cause)", illi),
            ("ILLI: escape imms18=3 (info)",
             (0x7E << 24) | ((ha & 0x3F) << 18) | 3),
            ("ILLI: escape imms18=3 witness", 0xC0DE001A),
            ("ILLI: escape imms18=4 (cause)", illi),
            ("ILLI: escape imms18=4 (info)",
             (0x7E << 24) | ((ha & 0x3F) << 18) | 4),
            ("ILLI: escape imms18=4 witness", 0xC0DE001B),
            ("hmon cg8 rc1 async mask reset", ALL1),
            ("masked timer pending = source bit", src_bit),
            ("masked timer src_frame = capture buffer (0)", 0),
        ]
        rc14_mode = [
            ("async rc14=0: entry reads rc14 = 0", 0),
            ("async rc14=0: prev_run_mode = supv", M["supv"]),
            ("async rc14=2 from user: prev_run_mode = user", M["user"]),
            ("async rc14=2 from user: entry reads rc14 = 2", 2),
            ("async rc14=2: prev_run_mode = supv", M["supv"]),
        ]
        info1 = (0x7E << 24) | ((ha & 0x3F) << 18)          # escape cfx_hart
        info3 = (0x7E << 24) | ((C["smon"] & 0x3F) << 18)   # escape cfx_smon
        return (head + async_loop(M["hypv"], C["hmon"], sym("wait_begin"),
                                  M["supv"], ha)
                + rc14_mode + esc_criteria(info1, info3))

    prev_mode = M["user"] if mode == M["user"] else M["supv"]
    prev_cfx = C["umon"] if mode == M["user"] else C["smon"]
    head = [
        ("masked timer pending = source bit", src_bit),
        ("masked timer src_frame = capture buffer (0)", 0),
    ]
    return head + async_loop(prev_mode, prev_cfx, sym("umode_wait_begin"),
                             prev_mode, prev_cfx)


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
            elif kind == "slot":
                ref = recs[exp[1]] if exp[1] < len(recs) else None
                if ref is None or act != ref:
                    fails.append("slot %02d %-46s expected == slot %d actual 0x%x"
                                 % (i, name, exp[1],
                                    act if act is not None else 0))
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
            elif v[0] == "slot":
                ctl.append(ctl[v[1]])
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
            elif v[0] == "slot":
                mut[i] = ctl[v[1]] ^ 1             # no longer equal
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
                ("wait_begin", "umode_wait_begin", "rearm_fallback",
                 "pending_fallback", "async_entry", "jump_target",
                 "h_trap", "esc_bad1", "esc_bad2", "esc_bad3"))}
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
