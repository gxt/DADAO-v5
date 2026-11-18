#!/usr/bin/env python3
"""inst_sweep.py — DADAO 整数指令的**编码器 / ELF 布局 / 结果转储**库（不是门控）。

历史：本文件曾是 m12-chipyard-005 的 273 例 YAML sweep 驱动（`list`/`emit` 子命令）。
YAML 载体已随 `m13-testcases-043` 全退役 ⇒ 驱动与向量扫描部分删除，只保留**无 YAML
依赖**的复用件，供 `tools/chipyard/fetch_probe/gen_probe.py`（取指探针生成器）使用：

  * 编码器（`enc_*`）与立即数装载（`load_rd` / `load_rb`）；
  * 结果转储（`dump_reg` / `dump_mem`：把值写进结果缓冲、按 `st.o` 落盘）；
  * ELF/raw 布局（`LDS` / `assemble` / `toolchain_bin` / `IMAGE_LIMIT`）。

**这些函数生成的期望值不作判据**：判定一律走 `tests/inst/**/*.S` 的内联期望 +
`run_inst_tiny.py`（chipyard/qemu/gem5 三平台逐字节）与 L2 `check-inst-asm`。
"""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "infra"))
import paths as _paths  # noqa: E402

ENTRY = 0xFFFF_FF01_0100
KERNEL_BASE = 0xFFFF_FF01_0000
RAW_PREFIX = ENTRY - KERNEL_BASE
BUF = ENTRY + 0x8000          # result buffer (32 KiB past the code)
EXITBLOCK = ENTRY + 0x9000    # SYS_EXIT argument block
PRE_BLOCK = ENTRY + 0x400     # "PRE\n\0" (inside the fault image)
POST_BLOCK = ENTRY + 0x408    # "POST\n\0" (inside the fault image)
IMAGE_LIMIT = BUF - ENTRY     # code must stay below BUF

SEMIHOST_TAG = 0x3FF00
SYS_WRITEC = 0x03
SYS_WRITE0 = 0x04
SYS_EXIT = 0x18
ADP_STOPPED_APPLICATION_EXIT = 0x20026

# Scratch registers used by the generated harness only.  The covered cases use
# rd1..rd5 and rb1..rb3 (checked at emit time), so these are free.
WR_PTR = 30      # rb30: moving result-write pointer
RD_PTR = 31      # rb31: result-read pointer (not used; rb16 is reused)
ZERO_RB = 27     # rb27: permanent zero for rb -> rd copies
TMP_RD = 9       # rd9: rb -> rd copy destination
SEMI_RD = 16     # rd16 / rb16: semihosting op / pointer
TMP_RB = 29      # rb29: memory-input address


# ---------------------------------------------------------------------------
# Encoding helpers (contracts/opcodes.yaml; SimRISC field layouts)
# ---------------------------------------------------------------------------
def enc_set_zw_rd(rd, wp, imm):
    return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_or_w_rd(rd, wp, imm):
    return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_set_zw_rb(rb, wp, imm):
    return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_or_w_rb(rb, wp, imm):
    return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_st_o_rd(rd, rb, off):
    return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)


def enc_mem(opc, reg, rb, off):
    """Memory-family form: opc | reg(bank high 6) | rb | imms12."""
    return (opc << 24) | (reg << 18) | (rb << 12) | (off & 0xFFF)


# contracts/opcodes.yaml opcodes for the load/store families used by the
# register/memory dump helpers below.
ST_OPC = {"b": 0x18, "w": 0x19, "t": 0x1A,
          "o_rd": 0x21, "o_rb": 0x23, "o_ra": 0x25}
LD_U_OPC = {1: 0x10, 2: 0x11, 4: 0x12, 8: 0x20}   # unsigned load by byte width


def enc_trap(cfxha, imm18):
    return (0x7F << 24) | (cfxha << 18) | (imm18 & 0x3FFFF)


def enc_add_uo(rdha, rdhb, rdhc, rdhd):
    return (0x50 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_sub_uo(rdha, rdhb, rdhc, rdhd):
    return (0x52 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_sub_so(rdha, rdhb, rdhc, rdhd):
    return (0x53 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_mul_uo(rdha, rdhb, rdhc, rdhd):
    return (0x54 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_add_si_rb(rbha, imms18):
    return (0x5B << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def enc_aip_si_rb(rbha, imms18):
    return (0x5A << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def enc_sub_o_dbb(rdhb, rbhc, rbhd):
    return 0x40CC0000 | (rdhb << 12) | (rbhc << 6) | rbhd


def enc_add_o_bbd(rbhb, rbhc, rdhd):
    return 0x40C00000 | (rbhb << 12) | (rbhc << 6) | rdhd


def enc_shl_t_orri(rdhb, rdhc, immu6):
    return 0x41600000 | (rdhb << 12) | (rdhc << 6) | (immu6 & 0x3F)


def load_rd(dst, value):
    """set.zw wp0 + three or.w merges -- always 4 words (fixed index math)."""
    return [
        enc_set_zw_rd(dst, 0, value & 0xFFFF),
        enc_or_w_rd(dst, 1, (value >> 16) & 0xFFFF),
        enc_or_w_rd(dst, 2, (value >> 32) & 0xFFFF),
        enc_or_w_rd(dst, 3, (value >> 48) & 0xFFFF),
    ]


def load_rb(dst, value):
    return [
        enc_set_zw_rb(dst, 0, value & 0xFFFF),
        enc_or_w_rb(dst, 1, (value >> 16) & 0xFFFF),
        enc_or_w_rb(dst, 2, (value >> 32) & 0xFFFF),
        enc_or_w_rb(dst, 3, (value >> 48) & 0xFFFF),
    ]


def asm_sys_exit(code):
    """SYS_EXIT(code) 收尾（参数块 = EXITBLOCK）。"""
    words = []
    words += load_rb(SEMI_RD, EXITBLOCK)
    words += load_rd(15, ADP_STOPPED_APPLICATION_EXIT)
    words.append(enc_st_o_rd(15, SEMI_RD, 0))
    words += load_rd(15, code)
    words.append(enc_st_o_rd(15, SEMI_RD, 8))
    words.append(enc_set_zw_rd(SEMI_RD, 0, SYS_EXIT))
    words.append(enc_trap(0, SEMIHOST_TAG | SYS_EXIT))
    return words


def word_bytes(words):
    return b"".join(struct.pack(">I", w) for w in words)


def dump_reg(bank, num):
    """Append the register value to the result buffer (WR_PTR advances)."""
    if bank == "rd":
        words = [enc_mem(ST_OPC["o_rd"], num, WR_PTR, 0)]
    elif bank == "rb":
        # sub.o dbb copies an rb register into rd without a store/load round
        # trip (m12-005 path, independent of the memory unit).
        words = [enc_sub_o_dbb(TMP_RD, num, ZERO_RB),
                 enc_mem(ST_OPC["o_rd"], TMP_RD, WR_PTR, 0)]
    else:  # ra
        words = [enc_mem(ST_OPC["o_ra"], num, WR_PTR, 0)]
    return words + [enc_add_si_rb(WR_PTR, 8)]


def dump_mem(addr, nbytes):
    """Read `nbytes` at `addr` with the matching unsigned load and buffer it."""
    words = load_rb(TMP_RB, addr)
    words.append(enc_mem(LD_U_OPC[nbytes], TMP_RD, TMP_RB, 0))
    words.append(enc_mem(ST_OPC["o_rd"], TMP_RD, WR_PTR, 0))
    return words + [enc_add_si_rb(WR_PTR, 8)]

# ---------------------------------------------------------------------------
# Assemble / link
# ---------------------------------------------------------------------------
LDS = """ENTRY(_start)
PHDRS {{ image PT_LOAD FLAGS(7); }}
SECTIONS
{{
  . = 0x{entry:x};
  .text : {{ *(.text .text.*) }} : image
  /DISCARD/ : {{ *(.note.GNU-stack) *(.comment) }}
}}
"""


def toolchain_bin(explicit):
    if explicit:
        return Path(explicit)
    return _paths.host_toolchain_bin()


def assemble(words, outdir, stem, tb, extra_symbols=()):
    """Write the source, assemble/link it, and return (elf, raw) paths."""
    src = outdir / f"{stem}.S"
    lds = outdir / f"{stem}.lds"
    obj = outdir / f"{stem}.o"
    elf = outdir / f"{stem}.elf"
    raw0 = outdir / f"{stem}.flat"
    raw = outdir / f"{stem}.raw"
    lds.write_text(LDS.format(entry=ENTRY))
    lines = [".text", ".globl _start", "_start:"]
    lines += [".dd.t32 0x%08x" % w for w in words]
    src.write_text("\n".join(lines) + "\n")
    subprocess.run([str(tb / "llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
                    str(src), "-o", str(obj)], check=True)
    subprocess.run([str(tb / "ld.lld"), "-T", str(lds), str(obj), "-o", str(elf)], check=True)
    subprocess.run([str(tb / "llvm-objcopy"), "-O", "binary", str(elf), str(raw0)], check=True)
    data = raw0.read_bytes()
    if len(data) > IMAGE_LIMIT:
        raise SystemExit(f"inst_sweep: {stem} code {len(data)} B exceeds {IMAGE_LIMIT} B")
    raw.write_bytes(b"\x00" * RAW_PREFIX + data)
    return elf, raw


