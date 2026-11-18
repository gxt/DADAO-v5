#!/usr/bin/env python3
"""check_k1.py — M14 K1 closure gate (`make check-linux-k1`; `m14-linux-005`).

K1 is the boundary the user fixed on 2026-11-14: on the Vast machine the boot
chain hands over to the kernel and the kernel **runs and stops** before any
clock/timer/interrupt exists:

    power -> hmon -> smon -> kernel entry -> start_kernel -> SYS_EXIT(0)

This gate asserts that boundary end-to-end on the real kernel image.
`check-linux-k0` answers a different question ("can the boot chain hand over at
all: image + boot ABI + initramfs + patch set agree"), K1 answers "does the
kernel then run on the table it built and exit cleanly".  init / syscall /
interrupt are K2+ and are asserted to be *absent*.

Expectations are derived live — this file restates none of them:

  * boot info field values, the kernel window, the VA/PA bias, the page and
    superpage sizes, the incoming PTBR and ``ptw_enable`` ->
    ``contracts/linux-boot.yaml`` (through ``tools/qemu/k0_boot_probe``);
  * the reset vector / bootrom / hmon / smon windows -> the machine profile
    (``tests/shared/machine-profiles.yaml`` via ``machine_profile``);
  * ``kernel_size`` / entry word -> the image's own program headers;
  * ``swapper_pg_dir`` (the table PA), ``start_kernel`` and its enclosing
    symbol -> the image's own symbol table (``llvm-nm``);
  * the BootROM index table -> the image ``build_firmware`` just produced.

Checks (``--selfcheck`` flips every check group by mutating the captured run /
a copy of the image or BootROM; ``--inject`` proves four of them go red
end-to-end by rebuilding the kernel with the corruption in place, then
restoring it: ``cp`` + md5):

  K1  incremental build: ``make_vmlinux.py`` rc 0 (``--no-build`` skips)
  K2  ELF: ``e_entry == kernel_base`` (the contract's entry VA)
  K3  BootROM header: index-table magic/version/count; exactly one entry per
      stage, types ordered hmon < smon; the reset vector sits in the power
      window (``reset_pc == bootrom_base + size - 64 KiB``) and that window is
      not blank -- i.e. the power stage is the code at reset
  K4  hmon/smon entries load inside their own SRAM windows (proof the stage the
      machine jumps to is the stage the image describes)
  K5  guest rc == 0 (SYS_EXIT subcode; no ``-d`` per-instruction log is used --
      the command line is asserted, and dump markers are rejected)
  K6  boot info: all 15 fields == the contract / the live-derived size (hmon
      wrote the block, the kernel parsed it)
  K7  kernel entry: the guest's ``entry_va`` == contract entry == ``e_entry``
      == boot info ``kernel_base``
  K8  smon handover: ``ptw_enable`` == the contract's startup value, incoming
      PTBR == contract ``ptbr``, and the prebuilt table covers exactly one
      superpage (the probe VA is unmapped *before* the switch)
  K9  kernel table: L1 index == ``kernel_start >> 29`` (4096) with P/SP/SPF,
      PTBR == the PA of ``swapper_pg_dir``, ``[15:0]`` forced to 0, PTBR
      actually changed, ``ptw_enable`` still 1
  K10 the switch is live: the previously unmapped VA resolves, and the two
      VA->PA readbacks (image word, boot info magic) plus the marker
      round-trip go through the new table
  K11 stage order + one-shot: kernel entry -> boot info -> stack -> ptw
      announce -> table -> install -> post-switch -> start_kernel marker ->
      exit, each exactly once and in that order; the PTE report covers exactly
      the two derived VAs
  K12 stop point: ``start_kernel`` marker once, ``ra`` inside
      ``[start_kernel, next symbol)``, and the exit line is the **last** line
  K13 reverse assertions: no ``panic``/``oops``/``BUG``/``Call Trace``; no
      named machine fault, no kernel-table rejection, no boot-info rejection;
      **in this image** (``CONFIG_DADAO_K1_EARLY_STOP=y``, no mm subsystem) the
      only ``CFXMEM`` is the single declared (and resumed) probe, and nothing
      from a post-K1 subsystem appears (init / syscall / IRQ / timer / tick).
      §4a (`m14-linux-015`): those three assertions are qualified to this
      image; the K3 criterion for a page fault (handled, retried, no second
      entry) is `check-linux-k3` F group (record: `docs/Process-07 §4a`).
  K14 semihosting pointers are PAs (`ISS-450`): a second run on the same Vast
      firmware (PTW already on) executes ``tools/linux/semihost_pa_probe.S``,
      which hands `SYS_WRITE0` (a short string and a 640-byte long string that
      spans the responder's 256-byte block reads), `SYS_WRITEC` (character) and
      `SYS_OPEN` (file name, length field 0) the **PA** of data whose PA, read
      as a VA, is *unmapped*.  All of them must come back byte-exact; a
      responder that walks the page table faults on those pointers, and one
      that stops at the first block (or whose physical window is cut short)
      cannot reproduce the long string.  The probe self-checks the
      "unmapped as a VA" premise against the live page table before it prints
      anything.
  K15 the same rule reaches `SYS_READC`'s internal scratch slot (`ISS-452`): a
      third run executes ``tools/linux/semihost_readc_probe.S``, which installs
      a kernel-window **VA** as `rb1` (like the kernel's own early stack) and
      asks for one character; the gate feeds that character on the semihosting
      console chardev and the guest must get exactly that byte back, twice (the
      `rd8` exit code and the echoed console byte).  A responder that names the
      slot by its VA reads 2 TiB beyond RAM and returns −1.

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (contract / image / profile / symbols missing).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import os
import re
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import k1_boot_probe as k1boot    # noqa: E402  (ELF/symbols)
from tools.linux import make_defconfig as defconfig  # noqa: E402  (config slice)
from tools.linux import k1_pt_probe as k1pt       # noqa: E402  (ptw parsers)
from tools.linux import make_vmlinux as vmlinux   # noqa: E402  (build driver)
from tools.linux import paths as linux_paths      # noqa: E402
# `.ascii` oracle helper: `tests/ee-tiny/` 不是合法模块名（`-`），按文件路径加载
# （m15-testcases-011：脚本迁出 `tools/linux/`）。
_SEMI_SMOKE = _REPO / "tests" / "ee-tiny" / "run_semihosting_smoke.py"
_spec = importlib.util.spec_from_file_location("tiny_run_semihosting_smoke", _SEMI_SMOKE)
run_semihosting_smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_semihosting_smoke)
from tools.qemu import k0_boot_probe as k0         # noqa: E402  (contract, firmware)

sys.path.insert(0, str(_REPO / "tools" / "testcases" / "lib"))
import machine_profile                             # noqa: E402

PROFILE = "vast"
BOOTROM_MAGIC = 0x44424F54            # tests/ee-vast/k0_*, image index table
POWER_WINDOW = 0x10000                # spec/Kaiwu §1: last 64 KiB = reset
#: BootROM index types (`tests/ee-vast/k0_README.md`): 1 = hmon, 2 = smon.
STAGE_TYPES = {1: "hmon", 2: "smon"}
#: Monitor SRAM windows (spec/Kaiwu §1.1): the image index table names the
#: ELF each stage is loaded from; power copies them here before the handover.
SPEC_SRAM = {"hmon": 0x0FFF_0000_0000, "smon": 0x0BFF_0000_0000}

#: The image this gate boots: the K1 stop is on and the K2 symbols are
#: explicitly off, so the result never depends on which gate configured the
#: shared build tree last (m14-linux-006 config slices).
K1_CONFIG = [
    "CONFIG_DADAO_K1_EARLY_STOP=y",
    "CONFIG_DADAO_K2_EARLY_STOP=n",
    "CONFIG_DADAO_K2_TIME_STOP=n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST=n",
    # m14-linux-012: the K3 page-fault probe is an int (0 = off); pin it so an
    # image that reaches setup_arch() never inherits another gate's case.
    "CONFIG_DADAO_K3_PF_SELFTEST=0",
]

TIMEOUT_QEMU = int(os.environ.get("K1_QEMU_TIMEOUT", "120"))
TIMEOUT_BUILD = int(os.environ.get("K1_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K1_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-005") / "check-linux-k1")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def num(text) -> int:
    """A contract value (int) or a printed ``0x...``/decimal token; -1 when absent."""
    if isinstance(text, int):
        return text
    try:
        return int(str(text), 0)
    except (TypeError, ValueError):
        return -1


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus live ``[STAT]`` lines."""

    def __init__(self, quiet: bool = False) -> None:
        self.total = 0
        self.fails: list[str] = []
        self.quiet = quiet

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        if not self.quiet:
            flag = "PASS" if ok else "FAIL"
            print(f"  [{flag}] {cid} {name} | 期望={expected} 实际={actual}",
                  flush=True)
        if not ok:
            self.fails.append(f"{cid} {name}: 期望={expected} 实际={actual}")
        return ok

    def stat(self, text: str) -> None:
        if not self.quiet:
            print(f"  [STAT] {text}", flush=True)


# ---------------------------------------------------------------------------
# derived expectation context
# ---------------------------------------------------------------------------

def bootrom_table(path: Path) -> dict:
    """Parse the image index table of a BootROM image (build_step5 format)."""
    img = Path(path).read_bytes()
    magic, version, count, boot_magic, reserved = struct.unpack(">IHHII", img[:16])
    entries = []
    for index in range(count):
        base = 16 + index * 32
        typ, flags, offset, size = struct.unpack(">IIQQ", img[base:base + 24])
        (elf_entry,) = struct.unpack(">Q", img[offset + 24:offset + 32])
        entries.append({"type": typ, "flags": flags, "offset": offset,
                        "size": size, "entry": elf_entry})
    return {"magic": magic, "version": version, "count": count,
            "boot_magic": boot_magic, "reserved": reserved,
            "entries": entries, "image": img}


@dataclass
class Ctx:
    """Everything the checks compare against, derived once from live inputs."""

    kernel: Path
    qemu: str
    bootrom: Path
    bias: int
    page_size: int
    superpage: int
    kernel_start: int
    entry_va: int
    boot_va: int
    ram_base_pa: int
    ram_size: int
    ptbr_in: int
    ptw_enable: int
    boot_info: dict
    profile: object
    syms: dict
    kernel_size: int
    table_pa: int
    base_index: int
    probe_va: int
    superpages: int
    entry_word: int

    def pa(self, va: int) -> int:
        return va - self.bias


def build_ctx(kernel: Path, qemu: str, bootrom: Path) -> Ctx:
    k0.load_contract()
    if not k0.ABI or not k0.BOOT_INFO:
        raise SystemExit("check_k1: the boot contract projection is empty")
    profile = machine_profile.load(PROFILE)
    syms = k1boot.symbols(kernel)
    for required in ("start_kernel", "swapper_pg_dir", "_start"):
        if required not in syms:
            raise SystemExit(f"check_k1: {required} is not in {kernel.name}; "
                             f"run `make linux-vmlinux`")
    entry_va = k0.ABI["entry_va"]
    return Ctx(
        kernel=kernel, qemu=qemu, bootrom=bootrom,
        bias=k0.ABI["va_pa_offset"],
        page_size=k0.ABI["page_size"],
        superpage=k0.ABI["superpage_size"],
        kernel_start=k0.ABI["kernel_start"],
        entry_va=entry_va,
        boot_va=k0.ABI["boot_info_va"],
        ram_base_pa=num(k0.BOOT_INFO["ram_base"]["value"]) - k0.ABI["va_pa_offset"],
        ram_size=num(k0.BOOT_INFO["ram_size"]["value"]),
        ptbr_in=num(k0.BOOT_INFO["ptbr"]["value"]),
        ptw_enable=k1pt.startup_model()["ptw_enable"],
        boot_info=k0.BOOT_INFO,
        profile=profile,
        syms=syms,
        kernel_size=k1boot.kernel_size_from_elf(kernel, entry_va),
        table_pa=syms["swapper_pg_dir"] - k0.ABI["va_pa_offset"],
        base_index=k0.ABI["kernel_start"] >> 29,        # VA[41:29], §2.2.1
        probe_va=k0.ABI["kernel_start"] + k0.ABI["superpage_size"],
        superpages=-(-num(k0.BOOT_INFO["ram_size"]["value"])
                     // k0.ABI["superpage_size"]),
        entry_word=k1pt.file_word_at(kernel, entry_va),
    )


# ---------------------------------------------------------------------------
# QEMU run: no `-d` (K1's ordering evidence is the guest's own report)
# ---------------------------------------------------------------------------

def run_kernel(ctx: Ctx, tag: str) -> tuple[int, str, list[str]]:
    log = SCRATCH / f"{tag}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ctx.qemu,
           "-machine", f"kaiwu-vast,bootrom-image={ctx.bootrom}",
           "-nographic",
           "-semihosting-config", "enable=on,target=native",
           "-kernel", str(ctx.kernel)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
        text = proc.stderr or proc.stdout
    except subprocess.TimeoutExpired:
        rc, text = 124, ""
    log.write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# K14: semihosting pointer arguments are PAs (ISS-450)
# ---------------------------------------------------------------------------

#: The probe and the fixed offsets of its data blocks inside the image.  Every
#: datum sits at ``ENTRY_VA + <offset>``: its VA is mapped, its PA — read as a
#: VA — is not (all of them are below one 512 MiB superpage).
SEMI_PROBE_S = _REPO / "tools" / "linux" / "semihost_pa_probe.S"
SEMI_PROBE_LDS = _REPO / "tools" / "linux" / "semihost_pa_probe.lds"
SEMI_DATA_OFF = {
    "sp_payload": 0x800,        # SYS_WRITE0 string + NUL
    "sp_chars": 0x810,          # SYS_WRITEC characters ("XYZ")
    "sp_mark_ok": 0x820,        # SYS_OPEN succeeded
    "sp_mark_bad": 0x828,       # SYS_OPEN faulted
    "sp_exit_block": 0x900,     # SYS_EXIT {reason, code}
    "sp_open_block": 0x940,     # SYS_OPEN {name pointer, mode, length}
    "sp_path": 0x980,           # the SYS_OPEN file name
    "sp_long": 0x1030,          # SYS_WRITE0 long string (m14-qemu-007)
}
SEMI_EXIT_BLOCK_OFF = SEMI_DATA_OFF["sp_exit_block"]
#: The Arm semihosting console name the responder special-cases (the probe's
#: own `sp_path` literal is asserted against this).
SEMI_CONSOLE_NAME = b":tt"


def semi_console_oracle() -> tuple[bytes, bytes, bytes, bytes, bytes, bytes]:
    """Console expectation from the probe source, in file order.

    ``(SYS_WRITE0 string, SYS_WRITE0 long string, SYS_WRITEC characters,
    SYS_OPEN ok marker, SYS_OPEN bad marker, SYS_OPEN file name)``.

    Same oracle discipline as `run_semihosting_smoke`: the expectation is the
    `.ascii` text of the probe, decoded here, never QEMU's own output.  The
    long string is the concatenation of every `.ascii` payload **after** the
    SYS_OPEN name, so it can be written as several readable lines.
    """
    payloads = [part for line in SEMI_PROBE_S.read_text(encoding="utf-8").splitlines()
                for part in run_semihosting_smoke._ascii_payloads(line)]
    if len(payloads) < 6:
        raise SystemExit(
            f"check_k1: {SEMI_PROBE_S.name}: expected >= 6 .ascii payloads "
            f"(string, characters, open-ok, open-bad, file name, long string), "
            f"found {len(payloads)}")
    payload, chars, mark_ok, mark_bad, path = payloads[:5]
    long_payload = b"".join(payloads[5:])
    if len(long_payload) <= 2 * 256:
        raise SystemExit(
            f"check_k1: {SEMI_PROBE_S.name}: long string is "
            f"{len(long_payload)} B, must exceed two 256-byte block reads")
    if path != SEMI_CONSOLE_NAME:
        raise SystemExit(f"check_k1: {SEMI_PROBE_S.name}: SYS_OPEN name is "
                         f"{path!r}, expected {SEMI_CONSOLE_NAME!r}")
    # The markers must be distinguishable from the printed text, otherwise a
    # dropped SYS_OPEN result could hide inside the payload.
    for mark in (mark_ok, mark_bad):
        for text in (payload, chars, long_payload):
            if mark in text or len(mark) != 1:
                raise SystemExit(f"check_k1: {SEMI_PROBE_S.name}: marker "
                                 f"{mark!r} is not a single byte outside the "
                                 f"payload")
    if mark_ok == mark_bad:
        raise SystemExit(f"check_k1: {SEMI_PROBE_S.name}: open markers equal")
    return payload, long_payload, chars, mark_ok, mark_bad, path


def build_semihost_probe(ctx: Ctx) -> tuple[Path, tuple[bytes, ...]]:
    """Assemble+link the PA probe; returns (elf, console oracle parts)."""
    oracle = semi_console_oracle()
    payload, _long, _chars, _ok, _bad, _path = oracle

    def va_of(symbol: str) -> int:
        return ctx.entry_va + SEMI_DATA_OFF[symbol]

    def pa_of(symbol: str) -> int:
        return ctx.pa(va_of(symbol))

    values = {
        "ENTRY_VA": ctx.entry_va,
        "PAYLOAD_VA": va_of("sp_payload"),
        "PAYLOAD_PA": pa_of("sp_payload"),
        "LONG_PA": pa_of("sp_long"),
        "CHARSET_PA": pa_of("sp_chars"),
        "MARK_OK_PA": pa_of("sp_mark_ok"),
        "MARK_BAD_PA": pa_of("sp_mark_bad"),
        "PATH_PA": pa_of("sp_path"),
        "OPEN_BLOCK_VA": va_of("sp_open_block"),
        "OPEN_BLOCK_PA": pa_of("sp_open_block"),
        "EXIT_BLOCK_VA": va_of("sp_exit_block"),
        "EXIT_BLOCK_PA": pa_of("sp_exit_block"),
        "PT_VA": k0.LAYOUT["page_table"][0],
        "PA_PTE_INDEX": pa_of("sp_payload") >> 29,
        "ENTRY_PTE_INDEX": ctx.entry_va >> 29,
    }
    defs: list[str] = []
    for key, value in values.items():
        value &= 0xFFFFFFFFFFFFFFFF
        if value >= 1 << 63:              # llvm-mc --defsym takes a signed i64
            value -= 1 << 64
        defs += ["--defsym", f"{key}={value}"]

    out = SCRATCH / "semihost_pa"
    out.mkdir(parents=True, exist_ok=True)
    obj, elf = out / "semihost_pa_probe.o", out / "semihost_pa_probe.elf"
    k0.run([k0.tool("llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
            *defs, str(SEMI_PROBE_S), "-o", str(obj)])
    k0.run([k0.tool("ld.lld"), "-z", "max-page-size=0x10000", "-T",
            str(SEMI_PROBE_LDS), str(obj), "-o", str(elf)])

    # K1 ELF-VA-TO-PA: the loader uses p_paddr, so rewrite it to p_vaddr - BIAS.
    buf = k0.elf_read(elf)
    for (off, vaddr, _paddr, _filesz, _memsz, _align) in k0.elf_loads(buf):
        if vaddr < ctx.bias:
            raise SystemExit("check_k1: PA probe segment below the kernel window")
        k0.put64(buf, off + 24, vaddr - ctx.bias)
    elf.write_bytes(buf)

    # The probe's immediates come from --defsym, so the linked symbols must land
    # where the probe assumes them (a drift here would silently test nothing).
    symbols = k1boot.symbols(elf)
    for name, expected in [("_start", ctx.entry_va)] + [
            (symbol, va_of(symbol)) for symbol in SEMI_DATA_OFF]:
        if symbols.get(name) != expected:
            raise SystemExit(f"check_k1: PA probe symbol {name}="
                             f"{symbols.get(name)!r}, expected {hex(expected)}")

    # The name the guest hands SYS_OPEN must be the bytes actually in the image.
    raw_path = elf.read_bytes()
    offset = _elf_file_offset(elf, symbols["sp_path"])
    if raw_path[offset:offset + len(SEMI_CONSOLE_NAME) + 1] != \
            SEMI_CONSOLE_NAME + b"\0":
        raise SystemExit("check_k1: PA probe sp_path bytes != "
                         f"{SEMI_CONSOLE_NAME!r}")
    return elf, oracle


def _elf_file_offset(elf: Path, addr: int) -> int:
    """File offset holding virtual address @addr (ELF64 big-endian, PT_LOAD)."""
    buf = k0.elf_read(elf)
    for (off, vaddr, _paddr, filesz, _memsz, _align) in k0.elf_loads(buf):
        p_offset = k0.be64(buf, off + 8)
        if vaddr <= addr < vaddr + filesz:
            return p_offset + (addr - vaddr)
    raise SystemExit(f"check_k1: {hex(addr)} is in no PT_LOAD file range")


def run_semihost_probe(ctx: Ctx, elf: Path) -> tuple[int, bytes]:
    """Run the PA probe on Vast (PTW already on) and return (rc, console)."""
    log = SCRATCH / "semihost_pa.log"
    cmd = [ctx.qemu,
           "-machine", f"kaiwu-vast,bootrom-image={ctx.bootrom}",
           "-nographic",
           "-semihosting-config", "enable=on,target=native",
           "-kernel", str(elf)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              timeout=TIMEOUT_QEMU)
        rc, console = proc.returncode & 0xFF, proc.stderr
    except subprocess.TimeoutExpired:
        rc, console = 124, b""
    log.write_bytes(console)
    return rc, console


def check_semihost_pa(rep: Report, rc: int, console: bytes) -> None:
    """Console services + SYS_OPEN must read their pointers by PA (PTW on)."""
    payload, long_payload, chars, mark_ok, mark_bad, _path = semi_console_oracle()
    rep.check("K14", "QEMU 未自行报错（探针不是启动失败）", False,
              b"qemu-system-dadao:" in console)
    rep.check("K14", "SYS_WRITE0：字符串经 PA 取出（该 PA 作为 VA 未映射）",
              True, payload in console)
    # 长串：跨 256 字节分块读、起点不在分块边界 ⇒ 长度探测必须走完整个
    # physical map 的窗口（不是只读一块），且长度/内容都正确（m14-qemu-007）。
    rep.check("K14", "SYS_WRITE0：长串（>2×256 B，跨分块）经 PA 完整取出",
              True, long_payload in console)
    rep.check("K14", "SYS_WRITEC：字符经 PA 取出（该 PA 作为 VA 未映射）", True,
              chars in console)
    # SYS_OPEN 的无长度文件名经 `common_semi_strlen` 钩子 + `lock_user`（identity = PA）
    # 取出；名指针是 PA 而其 VA 未映射，若改回 `lock_user_string` 就会走页表而 EFAULT。
    rep.check("K14", "SYS_OPEN：无长度文件名的指针经 PA 取出"
                     "（该 PA 作为 VA 未映射）", True,
              mark_ok in console and mark_bad not in console)
    rep.check("K14", "控制台字节 == 探针源文件推导的 oracle",
              payload + long_payload + chars + mark_ok, console)
    rep.check("K14", "SYS_EXIT：参数块经 PA 读取（guest rc）", 0, rc)


# ---------------------------------------------------------------------------
# K15: SYS_READC's internal scratch slot is named as a PA (ISS-452)
# ---------------------------------------------------------------------------

READC_PROBE_S = _REPO / "tools" / "linux" / "semihost_readc_probe.S"
#: The probe sets rb1 to this VA (inside the mapped kernel-window superpage,
#: one 64 KiB image above the entry: the probe image is <= 64 KiB).
READC_SCRATCH_OFF = 0x20000
#: The character the gate feeds on the semihosting console chardev.
READC_CHAR = b"K"
READC_DATA_OFF = {
    "sp_exit_block": 0xA00,
    "sp_char": 0xB00,
}


def build_readc_probe(ctx: Ctx) -> Path:
    """Assemble+link the SYS_READC scratch-slot probe (K15)."""
    # Premise B (the slot's numeric value is not a plausible PA) is only a
    # premise while RAM is smaller than 2 GiB; the probe tests bit 32.
    if ctx.ram_size > (1 << 32):
        raise SystemExit(f"check_k1: RAM {ctx.ram_size:#x} > 2^32; the READC "
                         f"probe's premise check no longer discriminates")

    scratch_va = ctx.entry_va + READC_SCRATCH_OFF
    values = {
        "ENTRY_VA": ctx.entry_va,
        "SCRATCH_VA": scratch_va,
        "SCRATCH_PTE_INDEX": scratch_va >> 29,
        "PT_VA": k0.LAYOUT["page_table"][0],
        "EXPECT_CHAR": READC_CHAR[0],
        "CHAR_PA": ctx.pa(ctx.entry_va + READC_DATA_OFF["sp_char"]),
        "EXIT_BLOCK_VA": ctx.entry_va + READC_DATA_OFF["sp_exit_block"],
        "EXIT_BLOCK_PA": ctx.pa(ctx.entry_va + READC_DATA_OFF["sp_exit_block"]),
    }
    defs: list[str] = []
    for key, value in values.items():
        value &= 0xFFFFFFFFFFFFFFFF
        if value >= 1 << 63:              # llvm-mc --defsym takes a signed i64
            value -= 1 << 64
        defs += ["--defsym", f"{key}={value}"]

    out = SCRATCH / "semihost_readc"
    out.mkdir(parents=True, exist_ok=True)
    obj, elf = out / "semihost_readc_probe.o", out / "semihost_readc_probe.elf"
    k0.run([k0.tool("llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
            *defs, str(READC_PROBE_S), "-o", str(obj)])
    k0.run([k0.tool("ld.lld"), "-z", "max-page-size=0x10000", "-T",
            str(SEMI_PROBE_LDS), str(obj), "-o", str(elf)])

    # K1 ELF-VA-TO-PA: the loader uses p_paddr, so rewrite it to p_vaddr - BIAS.
    buf = k0.elf_read(elf)
    for (off, vaddr, _paddr, _filesz, _memsz, _align) in k0.elf_loads(buf):
        if vaddr < ctx.bias:
            raise SystemExit("check_k1: READC probe segment below the kernel "
                             "window")
        k0.put64(buf, off + 24, vaddr - ctx.bias)
    elf.write_bytes(buf)

    symbols = k1boot.symbols(elf)
    expected = [("_start", ctx.entry_va)] + [
        (name, ctx.entry_va + offset) for name, offset in READC_DATA_OFF.items()]
    for name, want in expected:
        if symbols.get(name) != want:
            raise SystemExit(f"check_k1: READC probe symbol {name}="
                             f"{symbols.get(name)!r}, expected {hex(want)}")

    # The echoed character must be the byte the gate feeds, or the console
    # assertion would compare against something the probe never printed.
    raw = elf.read_bytes()
    offset = _elf_file_offset(elf, symbols["sp_char"])
    if raw[offset:offset + 1] != READC_CHAR:
        raise SystemExit(f"check_k1: READC probe sp_char={raw[offset:offset + 1]!r}"
                         f", expected {READC_CHAR!r}")
    return elf


def run_readc_probe(ctx: Ctx, elf: Path) -> tuple[int, bytes, bytes]:
    """Run the READC probe with a fed semihosting console; (rc, out, err).

    SYS_READC reads the semihosting console, so this run needs a chardev: the
    probe would otherwise block forever with no input source.  ``stdio`` is
    used for the semihosting console (``-serial none`` keeps it off the serial
    port) and the fed character goes in on stdin.
    """
    log = SCRATCH / "semihost_readc.log"
    cmd = [ctx.qemu,
           "-machine", f"kaiwu-vast,bootrom-image={ctx.bootrom}",
           "-display", "none", "-serial", "none",
           "-chardev", "stdio,id=semi",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-kernel", str(elf)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              input=READC_CHAR, timeout=TIMEOUT_QEMU)
        rc, out, err = proc.returncode & 0xFF, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = exc.stdout if isinstance(exc.stdout, bytes) else b""
        err = exc.stderr if isinstance(exc.stderr, bytes) else b""
    log.write_bytes(out + b"\n--- stderr ---\n" + err)
    return rc, out, err


def check_semihost_readc(rep: Report, rc: int, console: bytes,
                         err: bytes) -> None:
    """SYS_READC's scratch slot must be the PA of the stack slot (PTW on)."""
    rep.check("K15", "QEMU 未自行报错（探针不是启动失败）", False,
              b"qemu-system-dadao:" in err)
    # rc encodes more than "did it fail": the probe's own premise checks use
    # 0xE3/0xE5, so a broken setup can never be read as a broken responder.
    rep.check("K15", "SYS_READC：取字缓冲按 PA 命名（读回喂入的字节；"
                     "0xE3/0xE5=前提不成立，0xE4=取字不符）", 0, rc)
    rep.check("K15", "SYS_READC 读回的字符经 SYS_WRITEC 回显 == 喂入字符",
              READC_CHAR, console)


# ---------------------------------------------------------------------------
# stage anchors: one line each, in the order the boot chain produces them
# ---------------------------------------------------------------------------

STAGE_ANCHORS = (
    ("kernel-entry", r"^K1 bootinfo magic="),
    ("bootinfo", r"^K1 stack sp="),
    ("ptw-announce", r"^K1 ptw vec  supv_excp_vector="),
    ("table-build", r"^K1 ptw map  ram_pa="),
    ("install", r"^K1 ptw post ptbr="),
    ("post-switch", r"^K1 ptw new  va="),
    ("start_kernel", r"^start_kernel$"),
    ("exit", r"^K1 done: semihosting SYS_EXIT"),
)

#: Lines that must appear exactly once (kind -> pattern).
ONE_SHOT = {
    "bootinfo1": r"^K1 bootinfo magic=",
    "bootinfo2": r"^K1 bootinfo kernel_base=",
    "bootinfo3": r"^K1 bootinfo initramfs=",
    "stack": r"^K1 stack sp=",
    "vec": r"^K1 ptw vec  supv_excp_vector=",
    "ids": r"^K1 ptw ids  cfx_smon=",
    "pre": r"^K1 ptw pre  ptbr=",
    "map": r"^K1 ptw map  ram_pa=",
    "post": r"^K1 ptw post ptbr=",
    "new": r"^K1 ptw new  va=",
    "text": r"^K1 ptw va2pa text va=",
    "boot": r"^K1 ptw va2pa boot va=",
    "mark": r"^K1 ptw va2pa mark va=",
    "done": r"^K1 ptw done: running on the kernel-built table$",
    "marker": r"^start_kernel$",
    "start_kernel_line": r"^K1 start_kernel ra=",
    "exit": r"^K1 done: semihosting SYS_EXIT",
}

FATAL_PATTERNS = {
    "panic/oops/BUG": r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|Call Trace)",
    "机器具名 fault": r"^dadao: ",
    "内核致命 fault": r"^K1 ptw fault: ",
    "内核页表拒绝": r"^K1 ptw table rejected: ",
    "boot info 拒绝": r"^K1 bootinfo invalid: ",
}

#: Post-K1 subsystem traces: K1 stops before any of these exist.
POST_K1_PATTERN = (r"(Run /|init process|\bsyscall\b|\bIRQ\b|\btimer\b|\btick\b|"
                   r"clocksource|console \[|Mount-|Freeing unused|SMP:|PID hash)")


def line_indexes(text: str, pattern: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines())
            if re.match(pattern, line)]


def check_all(ctx: Ctx, rc: int, text: str, cmd: list[str], rep: Report) -> None:
    parsed = k1pt.parse(text)
    boot = k1boot.parse_positive(text)
    lines = [line for line in text.splitlines() if line.strip()]

    def get(key: str) -> str:
        if key not in boot:
            rep.check("K6", f"输出缺失字段 {key}", "存在", "缺失")
            return "<missing>"
        return boot[key]

    # ── K2: the image under test ─────────────────────────────────────────
    raw = ctx.kernel.read_bytes()
    rep.check("K2", "ELF magic/class/data（大端 ELF64）", "7f454c46/2/2",
              f"{raw[:4].hex()}/{raw[4]}/{raw[5]}")
    (elf_entry,) = struct.unpack(">Q", raw[24:32])
    rep.check("K2", "e_entry == contract kernel_base", hex(ctx.entry_va),
              hex(elf_entry))
    rep.stat(f"kernel={ctx.kernel.name} {ctx.kernel.stat().st_size} B "
             f"kernel_size={ctx.kernel_size:#x} superpages={ctx.superpages} "
             f"l1_index={ctx.base_index}")

    # ── K3/K4: the firmware stage order is a property of the image ───────
    table = bootrom_table(ctx.bootrom)
    rep.check("K3", "BootROM index-table magic", hex(BOOTROM_MAGIC),
              hex(table["magic"]))
    rep.check("K3", "index-table 条目数（每阶段一条）", len(STAGE_TYPES),
              table["count"])
    rep.check("K3", "条目类型（顺序 hmon<smon，各出现一次）",
              sorted(STAGE_TYPES), [e["type"] for e in table["entries"]])
    rep.check("K3", "复位向量落在 power 窗口起点（bootrom_base + size - 64 KiB）",
              hex(ctx.profile["bootrom_base"] + ctx.profile["bootrom_size"]
                  - POWER_WINDOW),
              hex(ctx.profile.reset_pc))
    reset_offset = ctx.profile.reset_pc - ctx.profile["bootrom_base"]
    power_window = table["image"][reset_offset:reset_offset + POWER_WINDOW]
    rep.check("K3", "power 窗口非空（复位处真的有代码）", True,
              any(power_window))
    for entry in table["entries"]:
        stage = STAGE_TYPES[entry["type"]]
        window = SPEC_SRAM[stage]
        rep.check("K4", f"{stage} 入口落在 {stage} SRAM 内（spec/Kaiwu §1.1）",
                  True, window <= entry["entry"] < window + 0x10000)
        rep.check("K4", f"{stage} ELF 在镜像内（offset+size 不越界）", True,
                  entry["offset"] + entry["size"] <= len(table["image"]))

    # ── K5: the guest stopped by itself ─────────────────────────────────
    rep.check("K5", "guest rc（SYS_EXIT 的退出码）", 0, rc)
    rep.check("K5", "QEMU 命令行无 -d/-D（不用逐指令日志）", True,
              "-d" not in cmd and "-D" not in cmd)
    rep.check("K5", "输出无 -d 转储标记（IN:/PC: 0x）", [], [
        line for line in lines if re.match(r"^(IN:|PC: 0x)", line)])

    # ── K6: the boot info block (hmon -> kernel) ─────────────────────────
    bi = ctx.boot_info
    want = [
        ("magic", hex(num(bi["magic"]["value"]))),
        ("version", hex(num(bi["version"]["value"]))),
        ("size", hex(num(bi["size"]["value"]))),
        ("hart_id", str(num(bi["hart_id"]["value"]))),
    ]
    for (field, expected), key in zip(want,
                                      ("bootinfo1.1", "bootinfo1.2",
                                       "bootinfo1.3", "bootinfo1.4")):
        rep.check("K6", f"bootinfo {field}", expected, get(key))
    second = [
        ("kernel_base", hex(ctx.entry_va), "bootinfo2.1"),
        ("kernel_size（ELF 程序头现场推导）", hex(ctx.kernel_size), "bootinfo2.2"),
        ("ram_base", hex(num(bi["ram_base"]["value"])), "bootinfo2.3"),
        ("ram_size", hex(num(bi["ram_size"]["value"])), "bootinfo2.4"),
    ]
    for field, expected, key in second:
        rep.check("K6", f"bootinfo {field}", expected, get(key))
    third = [
        ("initramfs_base", hex(num(bi["initramfs_base"]["value"])), "bootinfo3.1"),
        # K1 installs no initramfs (contract: initramfs_size is `runtime`).
        ("initramfs_size（K1 不装 initramfs）", "0x0", "bootinfo3.2"),
        ("cmdline_base", hex(num(bi["cmdline_base"]["value"])), "bootinfo3.3"),
        ("cmdline_size", hex(num(bi["cmdline_size"]["value"])), "bootinfo3.4"),
        ("ptbr（传入值）", hex(ctx.ptbr_in), "bootinfo3.5"),
        ("page_size_log2", hex(num(bi["page_size_log2"]["value"])), "bootinfo3.6"),
        ("flags", hex(num(bi["flags"]["value"])), "bootinfo3.7"),
    ]
    for field, expected, key in third:
        rep.check("K6", f"bootinfo {field}", expected, get(key))
    rep.check("K6", "page_size_log2 == log2(契约页大小)", ctx.page_size.bit_length() - 1,
              num(get("bootinfo3.6")))

    # ── K7: entry state ─────────────────────────────────────────────────
    rep.check("K7", "guest entry_va（rb16 移交值）", hex(ctx.entry_va),
              get("stack.4"))
    rep.check("K7", "bootinfo kernel_base == e_entry == entry_va", True,
              num(get("bootinfo2.1")) == elf_entry == ctx.entry_va)

    # ── K8: what smon handed over (before the kernel's own switch) ──────
    pre = parsed["pre"][0] if parsed["pre"] else ("<missing>",) * 2
    rep.check("K8", "切换前 ptw_enable（smon 已开启 PTW）", hex(ctx.ptw_enable),
              pre[1])
    rep.check("K8", "切换前 PTBR（smon 的首张表）", hex(ctx.ptbr_in), pre[0])
    old = parsed["old"][0] if parsed["old"] else ("<missing>",) * 3
    rep.check("K8", "预建表只覆盖 1 个超页（探针 VA 切换前未映射）", "0", old[1])
    rep.check("K8", "探针 VA == 内核窗口 + 1 超页（现场派生）",
              hex(ctx.probe_va), old[0])

    # ── K9: the kernel-built table is the installed one ─────────────────
    ptes = parsed["pte"]
    pte2s = parsed["pte2"]
    rep.check("K9", "PTE 报数（内核窗口 + 探针两个 VA）", 2, len(ptes))
    pte_vas = {row[0] for row in ptes}
    rep.check("K9", "PTE 覆盖的 VA 集合", sorted({hex(ctx.entry_va),
                                                  hex(ctx.probe_va)}),
              sorted(pte_vas))
    kernel_pte = next((row for row in ptes
                       if num(row[0]) == ctx.entry_va), None)
    if kernel_pte is None:
        rep.check("K9", "内核窗口表项存在", "存在", "缺失")
    else:
        rep.check("K9", "内核窗口 L1 索引 == VA[41:29]", str(ctx.base_index),
                  kernel_pte[1])
        rep.check("K9", "va41_29 == L1 索引", hex(ctx.base_index), kernel_pte[2])
        rep.check("K9", "P（present）", "1", kernel_pte[4])
        rep.check("K9", "SP（superpage）", "1", kernel_pte[5])
        rep.check("K9", "SPF（8 个 64 MiB 片段全在）", hex(0xff), kernel_pte[6])
    kernel_pte2 = next((row for row in pte2s
                        if num(row[0]) == ctx.entry_va), None)
    if kernel_pte2 is None:
        rep.check("K9", "内核窗口表项字段", "存在", "缺失")
    else:
        rep.check("K9", "VA -> PA（表项推出的 PA）", hex(ctx.pa(ctx.entry_va)),
                  kernel_pte2[12])
        rep.check("K9", "R/W/X", "1/1/1",
                  f"{kernel_pte2[5]}/{kernel_pte2[6]}/{kernel_pte2[7]}")
        rep.check("K9", "S（HSJU，supv 可访问）", "1", kernel_pte2[2])
    mapping = parsed["map"][0] if parsed["map"] else ("<missing>",) * 5
    rep.check("K9", "表覆盖的 RAM 基址 (PA)", hex(ctx.ram_base_pa), mapping[0])
    rep.check("K9", "表覆盖的 RAM 大小", hex(ctx.ram_size), mapping[1])
    rep.check("K9", "超页数 == ceil(ram_size / 超页)", str(ctx.superpages),
              mapping[2])
    rep.check("K9", "L1 索引区间 == [VA[41:29], +超页数)",
              [str(ctx.base_index), str(ctx.base_index + ctx.superpages - 1)],
              [mapping[3], mapping[4]])
    post = parsed["post"][0] if parsed["post"] else ("<missing>",) * 4
    rep.check("K9", "切换后 PTBR == swapper_pg_dir 的 PA",
              hex(ctx.table_pa), post[0])
    rep.check("K9", "PTBR[15:0] 被硬件强制为 0", hex(0), post[2])
    rep.check("K9", "PTBR 确实改变（写入生效）", True,
              num(post[0]) != num(pre[0]) and bool(num(post[1]) & 0xffff))
    rep.check("K9", "切换后 PTBR 与预建表不同", True,
              num(post[0]) != ctx.ptbr_in)

    # ── K10: the new table is live (output continues through it) ────────
    new = parsed["new"][0] if parsed["new"] else ("<missing>",) * 3
    rep.check("K10", "切换后同一 VA 已映射", "1", new[1])
    text_line = parsed["text"][0] if parsed["text"] else ("<missing>",) * 3
    rep.check("K10", "入口 VA -> PA", hex(ctx.pa(ctx.entry_va)), text_line[1])
    rep.check("K10", "入口 VA 处的字 == 镜像文件同一偏移的字节",
              hex(ctx.entry_word), text_line[2])
    boot_line = parsed["boot"][0] if parsed["boot"] else ("<missing>",) * 5
    rep.check("K10", "boot info VA -> PA", hex(ctx.pa(ctx.boot_va)), boot_line[1])
    rep.check("K10", "boot info magic 经新表读回", "1", boot_line[3])
    mark_line = parsed["mark"][0] if parsed["mark"] else ("<missing>",) * 5
    rep.check("K10", "写入经新表读回（marker roundtrip）", "1", mark_line[3])
    rep.check("K10", "切换后仍有输出（done 行）", 1, len(parsed["done"]))

    # ── K11: stage order + one-shot ─────────────────────────────────────
    firsts: list[tuple[str, int]] = []
    for stage, pattern in STAGE_ANCHORS:
        hits = line_indexes(text, pattern)
        rep.check("K11", f"阶段 {stage} 出现 1 次", 1, len(hits))
        if hits:
            firsts.append((stage, hits[0]))
    rep.check("K11", "阶段锚点齐全且顺序为 入口→报告→PTW→建表→安装→切换后→start_kernel→退出",
              [stage for stage, _ in STAGE_ANCHORS],
              [stage for stage, _ in firsts])
    rep.check("K11", "锚点行号严格递增", True,
              all(left[1] < right[1] for left, right in zip(firsts, firsts[1:])))
    for kind, pattern in ONE_SHOT.items():
        rep.check("K11", f"行 {kind} 出现 1 次", 1, len(line_indexes(text, pattern)))
    rep.stat(f"阶段锚点 {len(firsts)}/{len(STAGE_ANCHORS)}，"
             f"一次性行 {len(ONE_SHOT)} 类，输出 {len(lines)} 行")

    # ── K12: the stop point ─────────────────────────────────────────────
    rep.check("K12", "start_kernel 标记行后仍打印 RA 证据", True,
              "marker.1" in boot)
    rep.check("K12", "marker base == start_kernel 符号", hex(ctx.syms["start_kernel"]),
              get("marker.2"))
    ra = num(get("marker.1"))
    upper = k1boot.next_symbol(ctx.syms, "start_kernel")
    rep.check("K12", "RA 落在 start_kernel 内（ra < 下一个符号）", True,
              ctx.syms["start_kernel"] <= ra < upper)
    rep.check("K12", "inside 标记", "yes", get("marker.5"))
    rep.check("K12", "退出行是输出的最后一行", True,
              bool(lines) and lines[-1].startswith("K1 done: semihosting SYS_EXIT"))
    rep.check("K12", "退出行声明 SYS_EXIT(0) 先于任何时钟/中断", True,
              any(line == ("K1 done: semihosting SYS_EXIT(0) before any "
                           "clock/interrupt init") for line in lines))

    # ── K13: reverse assertions ─────────────────────────────────────────
    body = [line for line in lines if not line.startswith("K1 done: semihosting")]
    for label, pattern in FATAL_PATTERNS.items():
        rep.check("K13", f"无 {label}", [],
                  [line for line in body if re.search(pattern, line, re.M)])
    cfxmem = [line for line in body if "CFXMEM" in line]
    rep.check("K13", "本镜像内（CONFIG_DADAO_K1_EARLY_STOP=y、无 mm 子系统）CFXMEM 只出现 1 次：唯一一次预先声明的探针；替代判据 = check-linux-k3 F 组", 1, len(cfxmem))
    rep.check("K13", "本镜像内（无 mm 子系统）该 CFXMEM 是被处理过的探针（resumed）；替代判据 = check-linux-k3 F 组", True,
              bool(cfxmem) and bool(re.match(
                  r"^K1 ptw fault probed cause=CFXMEM va=\S+ ip=\S+ \(resumed\)$",
                  cfxmem[0])))
    rep.check("K13", "本镜像内（CONFIG_DADAO_K1_EARLY_STOP=y、无 mm 子系统 ⇒ 无页故障通道痕迹）无 K1 之后的子系统迹象（init/syscall/IRQ/timer/tick）；替代判据 = check-linux-k3 F 组", [],
              [line for line in body if re.search(POST_K1_PATTERN, line)])


# ---------------------------------------------------------------------------
# build / run drivers
# ---------------------------------------------------------------------------

def build() -> int:
    """
    Configure this gate's image, then build it incrementally.

    The kernel build tree is shared, so the gate must not inherit whatever
    configuration the previous command left behind: it states the symbols its
    image needs (K1 stops at the first line of start_kernel(); the K2 boundary
    and the K2 self-test are off) through the explicit config-slice entry point
    of tools/linux/make_defconfig.py.
    """
    rc = defconfig.apply_config_lines(K1_CONFIG)
    if rc != 0:
        print(f"check-linux-k1: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}"]
    print(f"[INFO] incremental build (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def firmware() -> Path:
    """Assemble power + hmon + smon into the shared Vast BootROM (scratch)."""
    k0.load_contract()
    if not k0.ABI:
        raise SystemExit("check_k1: the boot contract projection is empty")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return Path(k0.build_firmware(str(SCRATCH / "bootrom")))


def gate(kernel: Path, qemu: str, bootrom: Path, rep: Report) -> tuple[int, str]:
    ctx = build_ctx(kernel, qemu, bootrom)
    rc, text, cmd = run_kernel(ctx, "positive")
    if not rep.quiet:
        print("---- guest output ----")
        print(text.strip())
        print("----------------------")
    check_all(ctx, rc, text, cmd, rep)

    # ── K14: semihosting reads its pointer arguments by PA (ISS-450) ────
    # A second, independent run: the PA probe needs the same Vast firmware (so
    # PTW is on) but its own payload, and its evidence is the raw console.
    elf, _oracle = build_semihost_probe(ctx)
    probe_rc, probe_console = run_semihost_probe(ctx, elf)
    if not rep.quiet:
        print(f"---- PA probe output (rc={probe_rc}) ----")
        print(probe_console.decode("utf-8", "backslashreplace").strip())
        print("----------------------")
    check_semihost_pa(rep, probe_rc, probe_console)

    # ── K15: SYS_READC's internal scratch slot is a PA (ISS-452) ────────
    # Same Vast firmware (PTW on), third run: the probe installs a kernel-window
    # VA as SP (like the kernel's early stack) and asks for one character.
    readc_elf = build_readc_probe(ctx)
    readc_rc, readc_out, readc_err = run_readc_probe(ctx, readc_elf)
    if not rep.quiet:
        print(f"---- READC probe output (rc={readc_rc:#x}) ----")
        print(readc_out.decode("utf-8", "backslashreplace").strip())
        print(readc_err.decode("utf-8", "backslashreplace").strip())
        print("----------------------")
    check_semihost_readc(rep, readc_rc, readc_out, readc_err)
    return rc, text


# ---------------------------------------------------------------------------
# --selfcheck: every check group must be able to fail
# ---------------------------------------------------------------------------

#: cid -> (regex, replacement) applied to the captured positive output.  Each
#: mutation perturbs exactly the evidence that group reads.
TEXT_MUTATIONS = {
    "K6": (r"^(K1 bootinfo magic=)0x\S+", r"\g<1>0xdeadbeef"),
    "K7": (r"(entry_va=)0x[0-9a-f]+$", r"\g<1>0x20000000000"),
    "K8": (r"^(K1 ptw pre  ptbr=\S+ ptw_enable=)0x1", r"\g<1>0x0"),
    "K9": (r"^(K1 ptw post ptbr=)0x[0-9a-f]+", r"\g<1>0x0"),
    "K10": (r"^(K1 ptw new  va=\S+ mapped=)1", r"\g<1>0"),
    "K11": (r"^K1 ptw map  ram_pa=.*\n", ""),
    "K12": (r"inside=yes$", "inside=no"),
    "K13": (None, "Kernel panic - not syncing: injected\n"),
}


def run_selfcheck(qemu: str, bootrom: Path) -> int:
    """Mutate the captured run (or an image copy) and show each group flips."""
    kernel = Path(linux_paths.linux_build_dir()) / "vmlinux"
    ctx = build_ctx(kernel, qemu, bootrom)
    rc, text, cmd = run_kernel(ctx, "selfcheck")
    base = Report(quiet=True)
    check_all(ctx, rc, text, cmd, base)
    print(f"  [{'PASS' if not base.fails else 'FAIL'}] selfcheck 基准输出全绿 | "
          f"期望=0 失败 实际={len(base.fails)} 失败", flush=True)
    bad = 0 if not base.fails else 1

    def flipped(cid: str, mutated_ctx, mutated_rc, mutated_text) -> bool:
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            check_all(mutated_ctx, mutated_rc, mutated_text, cmd, rep)
        hit = [msg for msg in rep.fails if msg.startswith(cid)]
        print(f"  [{'PASS' if hit else 'FAIL'}] selfcheck {cid} 注入后判定翻转 | "
              f"期望=该组 FAIL 实际={hit[0] if hit else '未翻转'}", flush=True)
        return bool(hit)

    # K5 reads the exit code itself.
    if not flipped("K5", ctx, 1, text):
        bad += 1
    for cid, (pattern, repl) in TEXT_MUTATIONS.items():
        mutated = text + repl if pattern is None else \
            re.sub(pattern, repl, text, count=1, flags=re.M)
        if mutated == text:
            print(f"  [FAIL] selfcheck {cid} 注入点未命中 | 期望=文本改变 实际=未变")
            bad += 1
            continue
        if not flipped(cid, ctx, rc, mutated):
            bad += 1

    # K14 reads the *second* run's console bytes (the PA probe), so it is
    # flipped on a captured console: dropping either service, truncating the
    # long string, or failing SYS_OPEN must redden it.
    # 4 flips read the run itself / an image copy (K5, K2, K3, K4), 4 are K14's.
    groups = len(TEXT_MUTATIONS) + 4 + 4
    payload, long_payload, chars, mark_ok, mark_bad, _path = semi_console_oracle()
    for label, console in (
            ("WRITE0 缺串", long_payload + chars + mark_ok),
            ("WRITE0 长串截断", payload + long_payload[:len(long_payload) // 2]
                                + chars + mark_ok),
            ("WRITEC 缺字", payload + long_payload + mark_ok),
            ("SYS_OPEN 失败标记", payload + long_payload + chars + mark_bad)):
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            check_semihost_pa(rep, 0, console)
        hit = [msg for msg in rep.fails if msg.startswith("K14")]
        print(f"  [{'PASS' if hit else 'FAIL'}] selfcheck K14 {label} | "
              f"期望=K14 FAIL 实际={hit[0] if hit else '未翻转'}", flush=True)
        if not hit:
            bad += 1

    # K15 reads the third run's exit code and the character it echoed back;
    # both channels are flipped, plus the probe's "premise broken" code.
    groups += 3
    for label, readc_rc, readc_out in (
            ("取字不符（0xE4）", 0xE4, READC_CHAR),
            ("前提不成立（0xE3）", 0xE3, READC_CHAR),
            ("回显字符不符", 0, b"X")):
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            check_semihost_readc(rep, readc_rc, readc_out, b"")
        hit = [msg for msg in rep.fails if msg.startswith("K15")]
        print(f"  [{'PASS' if hit else 'FAIL'}] selfcheck K15 {label} | "
              f"期望=K15 FAIL 实际={hit[0] if hit else '未翻转'}", flush=True)
        if not hit:
            bad += 1

    # K2/K3/K4 read the image / BootROM, so they are flipped on faithful copies.
    copy = SCRATCH / "selfcheck-vmlinux"
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(kernel, copy)
    raw = bytearray(copy.read_bytes())
    (entry,) = struct.unpack(">Q", raw[24:32])
    raw[24:32] = (entry + 0x10000).to_bytes(8, "big")
    copy.write_bytes(bytes(raw))
    if not flipped("K2", build_ctx(copy, qemu, bootrom), rc, text):
        bad += 1

    rom = SCRATCH / "selfcheck-bootrom.bin"
    rom.write_bytes(bootrom.read_bytes())
    rom_raw = bytearray(rom.read_bytes())
    rom_raw[0:4] = b"\xde\xad\xbe\xef"
    rom.write_bytes(bytes(rom_raw))
    if not flipped("K3", build_ctx(kernel, qemu, rom), rc, text):
        bad += 1

    rom2 = SCRATCH / "selfcheck-bootrom2.bin"
    rom2.write_bytes(bootrom.read_bytes())
    raw2 = bytearray(rom2.read_bytes())
    # entry 0 (hmon): move e_entry of the hmon ELF out of its SRAM window
    (offset,) = struct.unpack(">Q", raw2[16 + 8:16 + 16])
    raw2[offset + 24:offset + 32] = (0xDEAD_0000).to_bytes(8, "big")
    rom2.write_bytes(bytes(raw2))
    if not flipped("K4", build_ctx(kernel, qemu, rom2), rc, text):
        bad += 1

    print(f"check-k1 selfcheck: {'PASS' if not bad else 'FAIL'} "
          f"({groups - bad}/{groups} 组可翻转)")
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# --inject: four real corruptions, rebuilt and restored (cp + md5)
# ---------------------------------------------------------------------------

PT_C = "arch/dadao/mm/k1_pt.c"
SETUP_C = "arch/dadao/kernel/setup.c"
HEAD_S = "arch/dadao/kernel/head.S"

INJECTIONS = {
    # (file, exact text, replacement, expected rc, expected line, forbidden
    #  line, check ids that must go red)
    "bootinfo-magic": (
        HEAD_S,
        "\tset.zw rd5, wp1, 0x4442\n\tor.w rd5, wp0, 0x494e\n",
        "\tset.zw rd5, wp1, 0x4442\n\tor.w rd5, wp0, 0x494f\n",
        0x01,
        r"^K1 bootinfo invalid: magic code=0x1$",
        r"^(K1 bootinfo magic=|start_kernel$)",
        ("K5", "K11", "K13"),
    ),
    "ptbr-unmapped": (
        PT_C,
        "\tdadao_ptbr_write(base | 0xffffUL);",
        "\tdadao_ptbr_write((base | 0xffffUL) ^ (1UL << 33));",
        1,
        r"dadao: page-table access outside physical memory "
        r"\(VA=[0-9a-f]+, PTBR=[0-9a-f]+\)",
        r"^(K1 ptw post |K1 ptw done|start_kernel$)",
        ("K9", "K11"),
    ),
    # The exit call is part of the K1 boundary's last line, so the injection
    # names that line too (the K2 boundary carries the same call).
    "exit-code": (
        SETUP_C,
        "\tdadao_early_printf(\"K1 done: semihosting SYS_EXIT(0) before any "
        "clock/interrupt init\\n\");\n"
        "\tdadao_early_exit(0);",
        "\tdadao_early_printf(\"K1 done: semihosting SYS_EXIT(0) before any "
        "clock/interrupt init\\n\");\n"
        "\tdadao_early_exit(1);",
        1,
        r"^K1 done: semihosting SYS_EXIT\(0\)",
        None,                     # rc is the only signature of this injection
        ("K5",),
    ),
    "no-start-marker": (
        SETUP_C,
        "\tdadao_early_printf(\"start_kernel\\n\");\n",
        "",
        0,
        r"^K1 start_kernel ra=",
        r"^start_kernel$",
        ("K11",),
    ),
}


def run_inject(name: str, qemu: str, bootrom: Path, problems: list[str]) -> None:
    """One source injection: patch -> rebuild -> red -> restore -> rebuild -> green."""
    rel, old, new, want_rc, want_re, forbid, want_cids = INJECTIONS[name]
    path = linux_paths.linux_source_dir() / rel
    before = md5(path)
    backup = SCRATCH / f"inject-{name}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(path.read_bytes())
    text = path.read_text()
    if text.count(old) != 1:
        problems.append(f"inject:{name}: 注入点不唯一（{text.count(old)} 处）")
        backup.unlink()
        return
    path.write_text(text.replace(old, new, 1))
    if md5(path) == before:
        problems.append(f"inject:{name}: 注入是空操作（md5 未变）")
        path.write_bytes(backup.read_bytes())
        backup.unlink()
        return
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> "
          f"{md5(path)[:8]}", flush=True)

    # Any failure still restores the source *and* rebuilds, so a later step can
    # never run against a kernel built from the injected tree.
    try:
        rc_build = build()
        if rc_build != 0:
            problems.append(f"inject:{name}: 重建 rc={rc_build}")
        else:
            kernel = Path(linux_paths.linux_build_dir()) / "vmlinux"
            rep = Report(quiet=True)
            rc, text = gate(kernel, qemu, bootrom, rep)
            print(f"---- guest output ({name}) ----")
            print(text.strip())
            print("--------------------------------")
            hit = re.search(want_re, text, re.MULTILINE)
            checks = [
                ("退出码", rc == want_rc, hex(want_rc), hex(rc)),
                ("具名行", bool(hit), want_re, hit.group(0) if hit else "<none>"),
            ]
            if forbid is not None:
                absent = not re.search(forbid, text, re.MULTILINE)
                checks.append(("禁止行", absent, f"无 {forbid}",
                               "无" if absent else "有"))
            for cid in want_cids:
                red = [msg for msg in rep.fails if msg.startswith(cid)]
                checks.append((f"断言 {cid} 变红", bool(red),
                               f"{cid} 出现 FAIL",
                               red[0] if red else "未变红"))
            for label, ok, expected, actual in checks:
                print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} {label} | "
                      f"期望={expected} 实际={actual}", flush=True)
                if not ok:
                    problems.append(f"inject:{name}: {label}（期望 {expected}，"
                                    f"实际 {actual}）")
    except Exception as exc:                    # keep the run going, restore below
        problems.append(f"inject:{name}: {type(exc).__name__}: {exc}")
    finally:
        path.write_bytes(backup.read_bytes())
        restored = md5(path)
        ok = restored == before
        print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} 还原 (cp) | "
              f"md5 期望={before[:8]} 实际={restored[:8]}", flush=True)
        if not ok:
            problems.append(f"inject:{name}: 还原后 md5 不一致")
        backup.unlink()

    rc_build = build()
    if rc_build != 0:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    rep = Report(quiet=True)
    gate(Path(linux_paths.linux_build_dir()) / "vmlinux", qemu, bootrom, rep)
    green = not rep.fails
    print(f"  [{'PASS' if green else 'FAIL'}] inject:{name} 还原后回绿 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
    if not green:
        problems.append(f"inject:{name}: 还原后仍失败 "
                        f"({rep.fails[0]})")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel", default=None, help="vmlinux under test")
    ap.add_argument("--qemu", default=os.environ.get("K1_QEMU"),
                    help="qemu-system-dadao binary (default: install root)")
    ap.add_argument("--no-build", action="store_true",
                    help="assert only; never run the incremental build")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured run / an image copy: every check "
                         "group must flip")
    ap.add_argument("--inject", action="store_true",
                    help="four source injections: rebuild, assert FAIL, restore")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(["positive", "selfcheck"] +
                        [f"inject:{name}" for name in INJECTIONS]))
        return 0

    qemu = args.qemu or k0.DEFAULT_QEMU
    if not Path(qemu).is_file():
        print(f"check-linux-k1: FAIL: {qemu} missing; run `make install-host`",
              file=sys.stderr)
        return 1
    if not args.no_build:
        rc = build()
        if rc != 0:
            print(f"check-linux-k1: FAIL: build rc={rc}", file=sys.stderr)
            return 1
    kernel = Path(args.kernel) if args.kernel else \
        Path(linux_paths.linux_build_dir()) / "vmlinux"
    if not kernel.is_file():
        print(f"check-linux-k1: FAIL: {kernel.name} missing; "
              f"run `make linux-vmlinux`", file=sys.stderr)
        return 2

    bootrom = firmware()
    print(f"k1: kernel={kernel.name} ({kernel.stat().st_size} B) "
          f"qemu={qemu} md5={md5(Path(qemu))[:8]} bootrom={bootrom.name}")

    if args.selfcheck:
        return run_selfcheck(qemu, bootrom)

    rep = Report()
    try:
        gate(kernel, qemu, bootrom, rep)
    except SystemExit as exc:                 # inputs could not be derived
        print(f"check-linux-k1: {exc}", file=sys.stderr)
        return 2
    if not rep.fails:
        print(f"check-linux-k1: PASS ({rep.total}/{rep.total})")
    else:
        print(f"check-linux-k1: FAIL ({rep.total - len(rep.fails)}/{rep.total}); "
              f"{len(rep.fails)} 项失败")
        for failure in rep.fails:
            print("  - " + failure)
    if args.inject:
        if rep.fails:
            print("check-linux-k1: 基线不绿，先修基线再做注入")
            return 1
        problems: list[str] = []
        for name in INJECTIONS:
            run_inject(name, qemu, bootrom, problems)
        total = sum(1 for _ in INJECTIONS)
        print(f"check-linux-k1 --inject: "
              f"{'PASS' if not problems else 'FAIL'} "
              f"({total}/{total} 路注入按预期变红并还原)"
              if not problems else
              f"check-linux-k1 --inject: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        if problems:
            return 1
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
