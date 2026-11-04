#!/usr/bin/env python3
"""Shared Node L3 probe prelude (TESTCASES-093t §2) — one implementation for
the 13 `ARCH_CFX_PROBES` and `min_rom_probe_046t`.

Loading model (task book §0/§2, spec/Machine-v5 §1 + DADAO-12 §4.5/§4.9):

  * one 4 MiB `bootrom-image` (`-machine dadao-m1,profile=node,...`), **no
    `-kernel`**; the CPU resets in power (cfx63/hypv) at RESET_PC, which is
    image offset `RESET_PC - BOOTROM_BASE` (Node: 0x3f_0000, the last 64 KiB);
  * power segment (reset_pc + 0): installs `cfx_hmon.hypv.excp_vector =
    RESET_PC + H_OFF` and `trap cfx_hmon, 0`;
  * hmon segment (reset_pc + H_OFF, 0x200): clears the cfx_power
    cfxmem/cfxexe mask for cg0-cg3 (former `bootstrap_stage`), writes four
    identity superpage PTEs (0xF000_0000_0000_FFEF | (i << 29), bit-identical
    to tests/shared/bootrom/step5/hmon.S) into cfx_pmem SRAM, copies them to
    `PT_PA` with the cfx_pmem DMA, invalidates the TLB, sets PTBR and
    `ptw_enable = 1`, then jumps to the body;
  * body (reset_pc + BODY_OFF, 0x1000): the probe, in hmon (cfx3/hypv).
    Everything the body writes to RAM (exit block, page tables it installs
    itself) therefore needs the prelude's identity map.

Why the body cannot run in power: ADR-0045 D4 keeps cfx_pmem/cfx_ptw/cfx0
default-masked; the same sequence succeeds in hmon (rc=0) and is rejected in
power (rc=0x81 CFXMEM) — task book E3/E4.

Exit sequence: the profile `exit_block` (Node 0x7ffd_0000), not the legacy
0x00ff_f000 window (task book §2).

A DMA ERROR / missing DONE at start-up is a harness failure: the hmon segment
reports it explicitly and does not continue (task book §2.3).  Note that with
PTW still off a RAM store cannot complete; the report is therefore built by
the semihosting attempt as well and either way the probe stays red.
"""

import os
import struct
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))

for _sub in (("tools", "testcases", "lib"), ("tools", "infra")):
    _p = os.path.join(_REPO, *_sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import machine_profile as _machine_profile  # noqa: E402
import paths as _paths  # noqa: E402

PROFILE = _machine_profile.load(os.environ.get("DADAO_TEST_PROFILE") or "node")
if not PROFILE.get("ptw") or not PROFILE.get("hmon"):
    raise SystemExit(
        "node_probe_prelude: profile %r has no PTW/hmon; the Node L3 prelude "
        "only supports a profile with monitor + page-table walker "
        "(tests/shared/machine-profiles.yaml)" % PROFILE.name)

# --- machine geometry (single source: tests/shared/machine-profiles.yaml) ---
RAM_BASE = PROFILE.ram_base
RAM_END = PROFILE.ram_end
SP = PROFILE.sp
BOOTROM_BASE = PROFILE.bootrom_base
BOOTROM_SIZE = PROFILE["bootrom_size"]
RESET_PC = PROFILE.reset_pc
EXIT_BLOCK = PROFILE.exit_block
RAM_W2 = (RAM_BASE >> 32) & 0xFFFF
RAM_W1 = (RAM_BASE >> 16) & 0xFFFF
RAM_W0 = RAM_BASE & 0xFFFF
EXIT_W2 = (EXIT_BLOCK >> 32) & 0xFFFF
EXIT_W1 = (EXIT_BLOCK >> 16) & 0xFFFF
EXIT_W0 = EXIT_BLOCK & 0xFFFF

# --- prelude layout / page-table target (task book §2, D3) ------------------
H_OFF = 0x200            # hmon segment, reset_pc-relative
BODY_OFF = 0x1000        # probe body, reset_pc-relative
ROM_BASE = RESET_PC + BODY_OFF
RESET_IMAGE_OFF = RESET_PC - BOOTROM_BASE
PT_PA = 0x7FF0_0000      # 64 KiB aligned, in RAM, below fault_record/exit
PMEM_BASE = 0x83FF_0000_0000   # spec/Machine-v5 §1 (cfxha 32)
PMEM_STAGE = PMEM_BASE + 0x1000

DEFAULT_QEMU = str(_paths.host_toolchain_bin() / "qemu-system-dadao")
QEMU = DEFAULT_QEMU
TMP_ROOT = "/tmp/opencode/TESTCASES-093t"
TIMEOUT = 10

# Semihosting SYS_EXIT (ADR-0020 D8): trap immu18[17:8] == 0x3FF.
SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def default_qemu():
    """Install-root QEMU (task book §1): every probe uses this default."""
    return DEFAULT_QEMU


# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml; same layout as the probe drivers)
# ---------------------------------------------------------------------------

def set_zw_rd(rd, wp, imm):
    return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)


def or_w_rd(rd, wp, imm):
    return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)


def set_zw_rb(rb, wp, imm):
    return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)


def or_w_rb(rb, wp, imm):
    return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)


def st_o(rd, rb, off):
    return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)


def ld_o(rd, rb, off):
    """ld.o: the imm12 field is sign-extended, so offsets stay in [0, 0x7ff]."""
    return (0x20 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)


def add_si(rd, imms18):
    return (0x59 << 24) | (rd << 18) | (imms18 & 0x3FFFF)


def escape(ha, imms18):
    return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)


def cfx2rd(ha, cg, rc, rd):
    return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd


def cfx2rc(ha, cg, rc, rd):
    return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd


def trap(ha, immu18):
    return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)


def jump_rel(imms24):
    """jump [rb0, imms24]: Addr = rb0 + (imms24 << 2), rb0 = this IP."""
    return (0x70 << 24) | (imms24 & 0xFFFFFF)


def br_nz(rdha, imms18):
    """br.nz {rdHA}?, [rb0, imms18] (rd bank variant, opcode 0x6b)."""
    return (0x6B << 24) | (rdha << 18) | (imms18 & 0x3FFFF)


def br_z(rdha, imms18):
    """br.z {rdHA}?, [rb0, imms18] (rd bank variant, opcode 0x6a)."""
    return (0x6A << 24) | (rdha << 18) | (imms18 & 0x3FFFF)


def br_nn(rdha, imms18):
    """br.nn {rdHA}?, [rb0, imms18] (rd bank variant, opcode 0x69)."""
    return (0x69 << 24) | (rdha << 18) | (imms18 & 0x3FFFF)


def br_eq(rdha, rdhb, imms12):
    """br.eq {rdha}?, {rdhb}?, [rb0, imms12] (opcode 0x6e)."""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return (0x6E << 24) | (rdha << 18) | (rdhb << 12) | (hc << 6) | hd


def br_ne(rdha, rdhb, imms12):
    """br.ne {rdha}?, {rdhb}?, [rb0, imms12] (opcode 0x6f)."""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return (0x6F << 24) | (rdha << 18) | (rdhb << 12) | (hc << 6) | hd


class Seq:
    """Word list with self-relative label fixups (labels are word indexes).

    Probe bodies only need a handful of instructions, so this stays a word
    builder rather than a full assembler.
    """

    def __init__(self):
        self.w = []
        self.lab = {}
        self.fix = []

    def e(self, *ws):
        self.w.extend(ws)

    def mark(self, name):
        if name in self.lab:
            raise ValueError("duplicate label %r" % name)
        self.lab[name] = len(self.w)

    def b(self, kind, rd, label, rdb=0):
        self.fix.append((len(self.w), kind, rd, rdb, label))
        self.w.append(0)

    def resolve(self):
        for idx, kind, rd, rdb, label in self.fix:
            off = self.lab[label] - idx
            if kind == "eq":
                self.w[idx] = br_eq(rd, rdb, off)
            elif kind == "ne":
                self.w[idx] = br_ne(rd, rdb, off)
            elif kind == "nz":
                self.w[idx] = br_nz(rd, off)
            elif kind == "z":
                self.w[idx] = br_z(rd, off)
            elif kind == "nn":
                self.w[idx] = br_nn(rd, off)
            else:
                raise ValueError(kind)
        return self.w


def and_o(rdhb, rdhc, rdhd):
    """and.o rdhb, rdhc, rdhd (contracts/opcodes.yaml: opc 0x40, ha 0x08)."""
    return (0x40 << 24) | (0x08 << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def swym():
    return 0x47880000


def load_rd(rd, val):
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def load_rb(rb, val):
    out = [set_zw_rb(rb, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rb(rb, wp, x))
    return out


def exit_seq(code):
    """Report `code` through semihosting SYS_EXIT (ABI: `exit_block`).

    The leading no-op `jump [rb0, 1]` ends the current translation block so a
    `-d cpu` dump captures the caller's state before this epilogue (the probe
    drivers use the last dump block as their observation channel).
    """
    return ([jump_rel(1)]
            + load_rb(16, EXIT_BLOCK)
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def _pte(i):
    """spec/DADAO-12 §2.2.3 + hmon.S: HSJU=0xF, PPN=i, SPF=0xFF, flags=0xEF."""
    return 0xF000_0000_0000_FFEF | (i << 29)


# ---------------------------------------------------------------------------
# Prelude segments
# ---------------------------------------------------------------------------

def power_segment(extra=None):
    """cfx63/hypv: install the hmon vector, then trap into hmon.

    Power only performs this hand-off (task book §0/D1); every PMEM/PTW body
    step runs in hmon.  `extra` is probe-specific power-mode setup: it runs
    after the vector install and before the trap, so a write of cfx_hmon's
    `hypv_switch_cfx_mask` (cg3 rc9) takes effect when the trap re-enters hmon
    (cfx_enter applies `switch_cfx_mask` only on entry, not on a register
    write -- TESTCASES-094t §2).
    """
    ins = load_rd(22, RESET_PC + H_OFF) + [cfx2rc(3, 3, 10, 22)]
    if extra:
        ins += list(extra)
    ins += [trap(3, 0)]
    return ins


def hmon_segment(hmon_extra=None):
    """hmon (cfx3/hypv): clear power masks, identity PT via PMEM DMA, PTW on.

    `hmon_extra` are probe-specific hmon-mode setup words (vectors/masks); they
    run last, so the registers they set stay live when the body starts.
    """
    ins = []
    # 1. former `bootstrap_stage`, narrowed to the fetch axis: cfx_power
    #    cg0-cg3 cfxexe = 0 so the body and its handlers can fetch this ROM in
    #    every run mode (ADR-0045 D2).  cfxmem is left at its reset value: the
    #    probes observe it (integ048t asserts MASK_DEFAULT) and no probe needs
    #    direct ld/st into cfx_power's internal space.
    ins += load_rd(20, 0)
    for cg in (0, 1, 2, 3):
        ins += [cfx2rc(63, cg, 3, 20)]

    # 2. four identity superpage PTEs -> PMEM SRAM staging.
    ins += load_rb(2, PMEM_STAGE)
    for i in range(4):
        ins += load_rd(4, _pte(i)) + [st_o(4, 2, i * 8)]

    # 3. cfx_pmem DMA: PMEM SRAM -> PT_PA, 32 bytes, DIR=0.
    ins += load_rd(9, PMEM_STAGE) + [cfx2rc(32, 15, 0, 9)]
    ins += load_rd(9, PT_PA) + [cfx2rc(32, 15, 1, 9)]
    ins += load_rd(9, 32) + [cfx2rc(32, 15, 2, 9)]
    ins += load_rd(9, 1) + [cfx2rc(32, 15, 3, 9)]

    # 4. poll dma_status.BUSY (bit0) until the transfer completes.
    poll = len(ins)
    ins += [cfx2rd(32, 15, 4, 9)]
    ins += load_rd(10, 1) + [and_o(9, 9, 10)]
    br = len(ins)
    ins += [br_nz(9, 0)]                 # patched: -> poll

    # 5. ERROR (bit2) or no DONE (bit1) => explicit harness failure (0xE0).
    fail_branches = []
    ins += [cfx2rd(32, 15, 4, 10)]
    ins += load_rd(11, 4) + [and_o(11, 10, 11)]
    fail_branches.append(("nz", len(ins)))
    ins += [br_nz(11, 0)]                # patched: -> fail
    ins += load_rd(11, 2) + [and_o(11, 10, 11)]
    fail_branches.append(("z", len(ins)))
    ins += [br_z(11, 0)]                 # patched: -> fail
    ok = len(ins)
    ins += [jump_rel(0)]                 # patched: skip the failure block

    fail = len(ins)
    fail_seq = exit_seq(0xE0)
    ins += fail_seq
    ins += [jump_rel(0)]                 # self loop if SYS_EXIT did not exit
    after_fail = len(ins)

    # 6. clear the PMEM staging (32 B) and W1C DONE, so a later probe that
    #    asserts on the SRAM/DMA state (integ042t) sees a clean device.
    ins += load_rd(20, 0)
    for off in (0, 8, 16, 24):
        ins += [st_o(20, 2, off)]
    ins += load_rd(9, 2) + [cfx2rc(32, 15, 4, 9)]

    # 7. TLB invalidate (all), PTBR = PT_PA, ptw_enable = 1.
    ins += load_rd(9, 2) + [cfx2rc(4, 12, 0, 9)]
    ins += load_rd(9, PT_PA) + [cfx2rc(4, 9, 0, 9)]
    ins += load_rd(9, 1) + [cfx2rc(4, 8, 8, 9)]

    # 8. leave the scratch registers as at reset (the probes read rd5..rd14 as
    #    observation registers, and e.g. integ040t expects "no fault" => rd10=0).
    ins += load_rd(4, 0) + load_rd(9, 0) + load_rd(10, 0) + load_rd(11, 0)
    ins += load_rd(20, 0) + load_rd(22, 0) + load_rb(2, 0)
    # 9. probe-specific hmon setup (vectors/masks), then the body.
    if hmon_extra:
        ins += list(hmon_extra)
    body_jump = len(ins)
    ins += [jump_rel(0)]

    # patch the self-relative branches (rb0 = the branch's own PC)
    ins[br] = br_nz(9, poll - br)
    for kind, idx in fail_branches:
        imm = fail - idx
        ins[idx] = br_nz(11, imm) if kind == "nz" else br_z(11, imm)
    ins[ok] = jump_rel(after_fail - ok)
    ins[fail + len(fail_seq)] = jump_rel(0)           # self loop
    ins[body_jump] = jump_rel(BODY_OFF // 4 - H_OFF // 4 - body_jump)
    return ins


def build_rom(prog, handlers=None, words_at=None, hmon_extra=None,
              image_at=None, power_extra=None):
    """Return the full 4 MiB bootrom image.

    `prog` is the body at ROM_BASE (RESET_PC + BODY_OFF); `handlers` and
    `words_at` map body-relative byte offsets to word lists (handlers first,
    then extra data; neither may overlap earlier content).  `hmon_extra` runs
    inside the prelude's hmon segment; `power_extra` runs in power before the
    trap into hmon (see `power_segment`).
    """
    body = bytearray(words_to_bytes(prog))
    for table in (handlers or {}, words_at or {}):
        for off in sorted(table):
            if off < len(body):
                raise ValueError("offset 0x%x overlaps the body" % off)
            while len(body) < off:
                body += words_to_bytes([swym()])
            body += words_to_bytes(table[off])
    while len(body) < BODY_OFF:
        body += words_to_bytes([swym()])

    prelude_off = H_OFF // 4
    hmon = hmon_segment(hmon_extra)
    power = power_segment(power_extra)
    if len(power) > prelude_off:
        raise ValueError("power segment does not fit before hmon (0x%x words)"
                         % prelude_off)
    if H_OFF + len(hmon) * 4 > BODY_OFF:
        raise ValueError("hmon segment does not fit before the body")

    image = bytearray(BOOTROM_SIZE)
    win = words_to_bytes(power) + words_to_bytes([swym()] * (prelude_off - len(power))) \
        + words_to_bytes(hmon)
    if RESET_IMAGE_OFF + len(win) > BOOTROM_SIZE:
        raise ValueError("prelude does not fit in the bootrom image")
    image[RESET_IMAGE_OFF:RESET_IMAGE_OFF + len(win)] = win
    body_off = RESET_IMAGE_OFF + BODY_OFF
    if body_off + len(body) > BOOTROM_SIZE:
        raise ValueError("body does not fit in the bootrom image")
    image[body_off:body_off + len(body)] = body
    for off in sorted(image_at or {}):
        win = words_to_bytes(image_at[off])
        if off + len(win) > RESET_IMAGE_OFF:
            raise ValueError("image_at 0x%x overlaps the reset window" % off)
        image[off:off + len(win)] = win
    return bytes(image)


# ---------------------------------------------------------------------------
# QEMU runner
# ---------------------------------------------------------------------------

def run(rom, workdir=None, qemu=None, timeout=TIMEOUT, icount_shift=None):
    """Run one probe image; returns (exit_code_or_None, cpu_log).

    Loading: 4 MiB `bootrom-image`, no `-kernel` (task book §2/E3); each case
    is its own QEMU process.
    """
    if workdir is None:
        stem = os.path.splitext(os.path.basename(sys.argv[0] or "probe"))[0]
        workdir = os.path.join(TMP_ROOT, stem)
    if qemu is None:
        qemu = QEMU
    os.makedirs(workdir, exist_ok=True)
    rp = os.path.join(workdir, "rom.bin")
    lp = os.path.join(workdir, "cpu.log")
    with open(rp, "wb") as f:
        f.write(rom)
    cmd = [qemu, "-machine",
           "dadao-m1,profile=%s,bootrom-image=%s" % (PROFILE.name, rp),
           "-nographic", "-semihosting-config", "enable=on,target=native"]
    if icount_shift is None:
        cmd += ["-d", "cpu", "-D", lp]
    else:
        # `-icount` cases self-check through the exit code (no dump channel);
        # the per-instruction dump would make the 1 ms prelude DMA window cost
        # gigabytes of I/O and time the case out.
        cmd += ["-icount", "shift=%d" % icount_shift]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
        rc = r.returncode & 0xFF
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    log = ""
    if icount_shift is None and os.path.isfile(lp):
        with open(lp) as f:
            log = f.read()
    return rc, log
