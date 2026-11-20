#!/usr/bin/env python3
"""k1_pt_probe.py — K1 page table + PTBR probe (`m14-linux-004`).

Boots the real kernel image on the Vast machine and checks the K1 boundary of
the page-table milestone: the kernel builds its own L1 table, installs it in
`cfx_ptw_ptbr`, and keeps running on it.

    qemu-system-dadao -machine kaiwu-vast,bootrom-image=<k0 BootROM> \\
                      -nographic -semihosting-config enable=on,target=native \\
                      -kernel <vmlinux>

Expectation sources (never restated here):

  * ``contracts/linux-boot.yaml`` — the kernel window, ``va_pa_offset``, the
    page/superpage sizes, the boot info VA, ``ptw_enable`` and the boot info
    field values (including the *incoming* ``ptbr``);
  * ``contracts/cfx-aliases.txt`` — the ``cfx_smon``/``cfx_ptw`` codes the guest
    must report (the same table the assembler resolves the instruction operands
    from);
  * ``spec/DADAO-12`` §2.2.1/§2.2.3 — L1 index = ``VA[41:29]``, the PTE field
    layout (P/SP/SPF/HSJU/R/W/X), superpage PPN alignment;
  * the image's own symbol table (``llvm-nm``) — ``swapper_pg_dir`` (the table's
    PA the PTBR must hold) and ``dadao_supv_excp`` (the vector the guest must
    have installed);
  * the image's own program headers — the file bytes the entry VA maps to (the
    kernel-window VA -> PA check).

Checks (``--selfcheck`` proves each one has a reachable FAIL by mutating the
captured output; ``--inject`` proves four of them end-to-end by rebuilding the
kernel with the corruption in place):

  P1  guest rc == 0 (SYS_EXIT subcode)
  P2  ``pre``: PTBR == the contract's incoming ``ptbr``, ``ptw_enable`` == 1
  P3  ``ids``: the cfx codes the guest reads back are ``cfx_smon``/``cfx_ptw``
  P4  ``vec``: the guest installed ``dadao_supv_excp`` as the supv vector
  P5  ``old``: the probe VA is unmapped *before* the switch, and the one CFXMEM
      it raises is the handled probe (cause/VA match)
  P6  ``map``: one superpage per ``ceil(ram_size / superpage)``, at the L1 index
      range derived from the kernel-window base
  P7  ``pte``: the kernel-window entry is a present superpage covering the
      accessed 64 MiB fragment
  P8  ``pte2``: HSJU/R/W/X of that entry, PPN == PA >> 16, VA -> PA == VA - bias
  P9  the same two checks for the probe superpage (index + 1)
  P10 ``post``: PTBR == the PA of ``swapper_pg_dir``, ``[15:0]`` forced to 0,
      and different from the incoming PTBR
  P11 ``new``: the same VA that faulted in P5 resolves after the switch
  P12 ``va2pa text``: the word read through the entry VA equals the image file's
      bytes at the offset that address maps to
  P13 ``va2pa boot``: boot info magic == the contract value, and the four bytes
      printed back *by PA* are the magic's ASCII
  P14 ``va2pa mark``: a word written through the new table reads back, and the
      same bytes printed by PA are the marker text
  P15 the completion line, the ``start_kernel`` marker, and no rejection/fault

``--inject`` cases (source patch -> rebuild -> run -> restore, ``cp`` + md5):

  pte-sp     the entry is built without ``SP`` -> the kernel refuses to install
             a table whose kernel-window entry is not a superpage (0x0a)
  ptbr-ppn   the PTBR value gets PPN bit 33 flipped -> the base leaves RAM and
             is refused (0x09)
  no-expect  the deliberate unmapped access is not announced as a probe -> the
             live CFXMEM is reported by name and is fatal (supv+CFXMEM monitor
             code, spec/Kaiwu §7.1)

Usage::

  python3 tools/linux/k1_pt_probe.py                # positive run
  python3 tools/linux/k1_pt_probe.py --selfcheck    # per-check reachable FAIL
  python3 tools/linux/k1_pt_probe.py --inject       # four real injections
  python3 tools/linux/k1_pt_probe.py --list
  python3 tools/linux/k1_pt_probe.py --kernel <vmlinux> --qemu <binary>

Exit status: 0 = every requested check passed; 1 = at least one FAIL; 2 = the
inputs could not be derived (contract/image/symbols missing).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins               # noqa: E402  (pins)
from tools.linux import k1_boot_probe as k1     # noqa: E402
from tools.linux import make_defconfig as defconfig  # noqa: E402  (config slice)
from tools.linux import make_vmlinux as vmlinux  # noqa: E402
from tools.linux import paths as _paths          # noqa: E402
from tools.qemu import k0_boot_probe as k0        # noqa: E402

import yaml                                        # noqa: E402

#: This probe boots the *K1* image: K1's stop is on and every other milestone
#: symbol is off (m14-linux-006 config slices — the default image is the K4 one).
#: Complete set, enforced by `make check-config-pins` (ISS-470); an int pinned
#: ``"n"`` is "left unset" because its `depends on` is not met.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "y",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    # m14-linux-018: the copy-on-write probe is an int with no `depends on`,
    # so it has no "unset" spelling: pin the concrete 0.
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    # m14-linux-020: the kernel-thread probe is an image of its own; pin it
    # off so the shared build tree cannot hand this image that symbol.
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    # m14-linux-023: the user-syscall probe image; pin it off so no other
    # image inherits it from the shared build tree.
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
}

K1_CONFIG = config_pins.config_lines(CONFIG_PINS)

TIMEOUT = int(os.environ.get("K1_PT_TIMEOUT", "120"))

_WORK_ROOT = os.environ.get("DADAO_TMP_ROOT") or "/tmp/opencode/m14-linux-004"
k0.TMP_ROOT = _WORK_ROOT
k0.WORK = os.path.join(_WORK_ROOT, "k1_pt_probe")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def num(text) -> int:
    """Contract value (int) or a printed `0x...`/decimal token; -1 when absent."""
    if isinstance(text, int):
        return text
    try:
        return int(str(text), 0)
    except (TypeError, ValueError):
        return -1


def startup_model() -> dict:
    with open(_REPO / "contracts" / "linux-boot.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["startup_model"]


def cfx_code(name: str) -> int:
    """The cfxha the alias table assigns to `cfx_<name>` (assembler source)."""
    path = _REPO / "contracts" / "cfx-aliases.txt"
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "scalar" and parts[1] == name:
            return int(parts[2], 0)
    raise SystemExit(f"k1_pt_probe: '{name}' is not a scalar in {path.name}")


def symbols(kernel: Path) -> dict[str, int]:
    return k1.symbols(kernel)


def file_word_at(elf: Path, va: int, size: int = 8) -> int:
    """The `size` bytes of the image file that the load covers for address @va."""
    raw = Path(elf).read_bytes()
    (phoff,) = struct.unpack(">Q", raw[32:40])
    (phentsize, phnum) = struct.unpack(">HH", raw[54:58])
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, _fl, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _al = \
            struct.unpack(">IIQQQQQQ", raw[off:off + 56])
        if p_type != 1:
            continue
        if p_vaddr <= va < p_vaddr + p_filesz:
            start = p_offset + (va - p_vaddr)
            return int.from_bytes(raw[start:start + size], "big")
    raise SystemExit(f"k1_pt_probe: VA {va:#x} is not covered by a loaded "
                     f"segment of {elf.name}")


# ---------------------------------------------------------------------------
# parse the guest output
# ---------------------------------------------------------------------------

LINES = {
    "vec": r"^K1 ptw vec  supv_excp_vector=(\S+) handler=(\S+)$",
    "ids": r"^K1 ptw ids  cfx_smon=(\S+) cfx_ptw=(\S+)$",
    "pre": r"^K1 ptw pre  ptbr=(\S+) ptw_enable=(\S+)$",
    "fault": r"^K1 ptw fault probed cause=(\S+) va=(\S+) ip=(\S+) \(resumed\)$",
    "old": r"^K1 ptw old  va=(\S+) mapped=(\d+) word=(\S+)$",
    "map": r"^K1 ptw map  ram_pa=(\S+) ram_size=(\S+) superpages=(\S+) "
           r"l1_index=(\d+)\.\.(\d+)$",
    "pte": r"^K1 ptw pte  va=(\S+) l1_index=(\S+) va41_29=(\S+) pte=(\S+) "
           r"P=(\d+) SP=(\d+) SPF=(\S+) spf_bit=(\d+)$",
    "pte2": r"^K1 ptw pte2 va=(\S+) H=(\d+) S=(\d+) J=(\d+) U=(\d+) R=(\d+) "
            r"W=(\d+) X=(\d+) G=(\d+) A=(\d+) D=(\d+) ppn=(\S+) va2pa=(\S+)$",
    "post": r"^K1 ptw post ptbr=(\S+) wrote=(\S+) low16=(\S+) ptw_enable=(\S+)$",
    "new": r"^K1 ptw new  va=(\S+) mapped=(\d+) word=(\S+)$",
    "text": r"^K1 ptw va2pa text va=(\S+) pa=(\S+) word=(\S+)$",
    "boot": r"^K1 ptw va2pa boot va=(\S+) pa=(\S+) magic=(\S+) magic_ok=(\d+) "
            r"bytes=(.{4})$",
    "mark": r"^K1 ptw va2pa mark va=(\S+) pa=(\S+) word=(\S+) roundtrip=(\d+) "
            r"bytes=(.{7})$",
    "done": r"^K1 ptw done: running on the kernel-built table$",
}


def parse(text: str) -> dict[str, list[tuple[str, ...]]]:
    """Every match per line kind, in output order (the pte groups repeat)."""
    out: dict[str, list[tuple[str, ...]]] = {key: [] for key in LINES}
    for line in text.splitlines():
        for key, pattern in LINES.items():
            m = re.match(pattern, line)
            if m:
                out[key].append(m.groups())
                break
    return out


# ---------------------------------------------------------------------------
# the check list
# ---------------------------------------------------------------------------

class Ctx:
    """Everything the checks compare against, derived once from live inputs."""

    def __init__(self, kernel: Path) -> None:
        k0.load_contract()
        if not k0.ABI:
            raise SystemExit("k1_pt_probe: contract projection is empty")
        self.kernel = kernel
        self.bias = k0.ABI["va_pa_offset"]
        self.superpage = k0.ABI["superpage_size"]
        self.page_size = k0.ABI["page_size"]
        self.page_shift = self.page_size.bit_length() - 1
        self.kernel_start = k0.ABI["kernel_start"]
        self.entry_va = k0.ABI["entry_va"]
        self.boot_va = k0.ABI["boot_info_va"]
        self.boot_size = k0.ABI["boot_info_size"]
        self.ptbr_in = num(k0.BOOT_INFO["ptbr"]["value"])
        self.ptw_enable = startup_model()["ptw_enable"]
        self.ram_base = num(k0.BOOT_INFO["ram_base"]["value"]) - self.bias
        self.ram_size = num(k0.BOOT_INFO["ram_size"]["value"])
        self.magic = num(k0.BOOT_INFO["magic"]["value"])
        self.smon = cfx_code("cfx_smon")
        self.ptw = cfx_code("cfx_ptw")
        self.base_index = self.kernel_start >> 29            # VA[41:29] (§2.2.1)
        self.probe_va = self.kernel_start + self.superpage
        self.probe_index = self.probe_va >> 29
        self.superpages = -(-self.ram_size // self.superpage)
        self.syms = symbols(kernel)
        for required in ("_start", "swapper_pg_dir", "dadao_supv_excp"):
            if required not in self.syms:
                raise SystemExit(f"k1_pt_probe: {required} is not in {kernel.name}")
        self.table_pa = self.syms["swapper_pg_dir"] - self.bias
        self.entry_word = file_word_at(kernel, self.entry_va)

    def pa(self, va: int) -> int:                 # VA -> PA for this machine
        return va - self.bias


def check_all(ctx: Ctx, rc: int, text: str, rep) -> None:
    f = parse(text)

    def one(key: str, index: int = 0) -> tuple[str, ...]:
        if len(f[key]) > index:
            return f[key][index]
        rep.check(f"P?{key}", f"输出缺失行 {key}[{index}]", "存在", "缺失")
        return tuple("<missing>" for _ in range(8))

    rep.check("P1", "guest rc (SYS_EXIT 的退出码)", 0, rc)

    pre = one("pre")
    rep.check("P2", "切换前 PTBR", hex(ctx.ptbr_in), pre[0])
    rep.check("P2", "切换前 ptw_enable", hex(ctx.ptw_enable), pre[1])

    ids = one("ids")
    rep.check("P3", "cfx_smon 编号（alias 表）", str(ctx.smon), ids[0])
    rep.check("P3", "cfx_ptw 编号（alias 表）", str(ctx.ptw), ids[1])

    vec = one("vec")
    rep.check("P4", "supv_excp_vector == dadao_supv_excp 符号",
              hex(ctx.syms["dadao_supv_excp"]), vec[0])
    rep.check("P4", "读回的向量 == 写入值", vec[0], vec[1])

    old = one("old")
    rep.check("P5", "切换前探针 VA（内核窗口 + 1 超页）",
              hex(ctx.probe_va), old[0])
    rep.check("P5", "切换前该 VA 未映射（旧表只有 1 个超页）", "0", old[1])
    rep.check("P5", "处理掉的探针缺页次数（现场计数）", 1, len(f["fault"]))
    fault = f["fault"][0] if f["fault"] else ("<missing>",) * 3
    rep.check("P5", "探针缺页原因", "CFXMEM", fault[0])
    rep.check("P5", "探针缺页地址", hex(ctx.probe_va), fault[1])

    mapping = one("map")
    rep.check("P6", "RAM 基址 (PA)", hex(ctx.ram_base), mapping[0])
    rep.check("P6", "RAM 大小", hex(ctx.ram_size), mapping[1])
    rep.check("P6", "超页数 == ceil(ram_size / 超页)", str(ctx.superpages),
              mapping[2])
    rep.check("P6", "L1 索引起点 == VA[41:29]（内核窗口基址）",
              str(ctx.base_index), mapping[3])
    rep.check("P6", "L1 索引终点", str(ctx.base_index + ctx.superpages - 1),
              mapping[4])

    # P7/P8: the kernel-window entry, P9: the probe superpage entry.
    for cid, va in (("P7", ctx.entry_va), ("P9", ctx.probe_va)):
        want_index = va >> 29
        pte = one("pte", 0 if va == ctx.entry_va else 1)
        rep.check(cid, f"表项 va={hex(va)} 的 l1_index", str(want_index), pte[1])
        rep.check(cid, "va41_29 == l1_index", hex(want_index), pte[2])
        rep.check(cid, "P（present）", "1", pte[4])
        rep.check(cid, "SP（superpage）", "1", pte[5])
        rep.check(cid, "SPF（8 个 64 MiB 片段全在）", hex(0xff), pte[6])
        rep.check(cid, "被访问片段的 SPF 位", "1", pte[7])

    for cid, va in (("P8", ctx.entry_va), ("P9", ctx.probe_va)):
        pte2 = one("pte2", 0 if va == ctx.entry_va else 1)
        rep.check(cid, f"表项 va={hex(va)} 的 S（HSJU）", "1", pte2[2])
        rep.check(cid, "U（HSJU）", "0", pte2[4])
        rep.check(cid, "R / W / X", "1/1/1", f"{pte2[5]}/{pte2[6]}/{pte2[7]}")
        # A superpage entry carries PPN[55:29] only (PPN[28:16] is forced to
        # 0, spec/DADAO-12 §2.2.3), i.e. the superpage-aligned page number.
        rep.check(cid, "PPN（PTE[55:16]，超页对齐）",
                  hex((ctx.pa(va) & ~(ctx.superpage - 1)) >> ctx.page_shift),
                  pte2[11])
        rep.check(cid, "VA -> PA", hex(ctx.pa(va)), pte2[12])

    post = one("post")
    rep.check("P10", "切换后 PTBR == swapper_pg_dir 的 PA", hex(ctx.table_pa),
              post[0])
    rep.check("P10", "PTBR[15:0] 被硬件强制为 0", hex(0), post[2])
    rep.check("P10", "切换后 ptw_enable", hex(ctx.ptw_enable), post[3])
    rep.check("P10", "PTBR 确实改变（写入生效）", True,
              num(post[0]) != num(pre[0]) and num(post[1]) & 0xffff != 0)

    new = one("new")
    rep.check("P11", "切换后探针 VA 地址", old[0], new[0])
    rep.check("P11", "切换后该 VA 已映射", "1", new[1])

    text_line = one("text")
    rep.check("P12", "入口 VA -> PA", hex(ctx.pa(ctx.entry_va)), text_line[1])
    rep.check("P12", "入口 VA 处的字 == 镜像文件同一偏移的字节",
              hex(ctx.entry_word), text_line[2])

    boot = one("boot")
    rep.check("P13", "boot info VA -> PA", hex(ctx.pa(ctx.boot_va)), boot[1])
    rep.check("P13", "boot info magic（经 VA 读）", hex(ctx.magic), boot[2])
    rep.check("P13", "magic 自校验", "1", boot[3])
    rep.check("P13", "按 PA 打印的 magic 字节",
              bytes.fromhex(f"{ctx.magic:08x}").decode("latin-1"), boot[4])

    mark = one("mark")
    rep.check("P14", "marker VA -> PA", hex(num(mark[0]) - ctx.bias), mark[1])
    rep.check("P14", "写回读通", "1", mark[3])
    rep.check("P14", "按 PA 打印的 marker 字节", "K1PT-KW", mark[4])

    rep.check("P15", "完成行", 1, len(f["done"]))
    rep.check("P15", "未出现拒绝行", [], re.findall(r"^K1 ptw table rejected:.*$",
                                                   text, re.MULTILINE))
    rep.check("P15", "未出现致命 fault 行", [],
              re.findall(r"^K1 ptw fault:.*$", text, re.MULTILINE))
    rep.check("P15", "仍到达 start_kernel（K1 未回归）", True,
              bool(re.search(r"^start_kernel$", text, re.MULTILINE)))


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------

QEMU: str | None = None
ROM: str | None = None


def boot(kernel: Path, tag: str) -> tuple[int, str]:
    global ROM
    if ROM is None:
        ROM = k0.build_firmware(os.path.join(k0.WORK, "bootrom"))
    rc, _blocks, err, _log = k0.run_qemu(QEMU or k0.DEFAULT_QEMU, ROM,
                                         str(kernel), tag,
                                         dfilter="0x0+0x4", timeout=TIMEOUT)
    if rc is None:
        return 124, err or ""
    return rc, err or ""


def run_positive(kernel: Path, ctx: Ctx, rep) -> None:
    rc, text = boot(kernel, "positive")
    print("---- guest output ----")
    print(text.strip())
    print("----------------------")
    check_all(ctx, rc, text, rep)


# ---------------------------------------------------------------------------
# --selfcheck: every check must be able to fail
# ---------------------------------------------------------------------------

#: cid -> (regex, replacement) applied to the captured positive output.  Each
#: mutation perturbs exactly the evidence that check reads.
MUTATIONS = {
    "P1": (r"", ""),                       # P1 compares rc, handled below
    "P2": (r"^(K1 ptw pre  ptbr=)0x0", r"\g<1>0x1"),
    "P3": (r"cfx_ptw=4", "cfx_ptw=5"),
    "P4": (r"^K1 ptw vec  supv_excp_vector=(\S+)",
           lambda m: m.group(0)[:-1] + ("0" if m.group(0)[-1] != "0" else "1")),
    "P5": (r"^(K1 ptw old  va=\S+ mapped=)0", r"\g<1>1"),
    "P6": (r"l1_index=(\d+)\.\.", lambda m: "l1_index=%d.." % (int(m.group(1)) - 1)),
    "P7": (r"P=1 SP=1", "P=1 SP=0"),
    "P8": (r"(pte2 va=\S+ .*va2pa=0x)([0-9a-f]+)$",
           lambda m: m.group(1) + "%x" % (int(m.group(2), 16) + 8)),
    "P9": (r"va41_29=0x1001", "va41_29=0x1002"),
    "P10": (r"(low16=)0x0", r"\g<1>0x1"),
    "P11": (r"^(K1 ptw new  va=\S+ mapped=)1", r"\g<1>0"),
    "P12": (r"(K1 ptw va2pa text va=\S+ pa=0x)([0-9a-f]+)",
            lambda m: m.group(1) + "%x" % (int(m.group(2), 16) + 8)),
    "P13": (r"magic_ok=1", "magic_ok=0"),
    "P14": (r"roundtrip=1", "roundtrip=0"),
    "P15": (r"^K1 ptw done:.*\n", ""),
}


def run_selfcheck(kernel: Path, ctx: Ctx) -> int:
    rc, text = boot(kernel, "selfcheck")
    base = k1.Report()
    check_all(ctx, rc, text, base)
    ok = not base.fails
    print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck 基准输出全绿 | "
          f"期望=0 失败 实际={len(base.fails)} 失败")
    bad = 0
    for cid, (pattern, repl) in MUTATIONS.items():
        if cid == "P1":
            mutated_text, mutated_rc = text, 1
        else:
            mutated_text, mutated_rc = re.sub(pattern, repl, text, count=1, flags=re.M), rc
        rep = k1.Report()
        with contextlib.redirect_stdout(io.StringIO()):
            check_all(ctx, mutated_rc, mutated_text, rep)
        hit = [msg for msg in rep.fails if msg.startswith(cid)]
        flag = "PASS" if hit else "FAIL"
        print(f"  [{flag}] selfcheck {cid} 注入后判定翻转 | "
              f"期望=该组 FAIL 实际={hit[0] if hit else '未翻转'}")
        bad += 0 if hit else 1
    print(f"k1_pt_probe: selfcheck {'PASS' if ok and not bad else 'FAIL'} "
          f"({len(MUTATIONS) - bad}/{len(MUTATIONS)} 组可翻转)")
    return 0 if ok and not bad else 1


# ---------------------------------------------------------------------------
# --inject: four real corruptions, rebuilt and restored
# ---------------------------------------------------------------------------

PT_C = "arch/dadao/mm/k1_pt.c"

#: name -> (relative source, exact line, replacement, expected rc, expected
#: regex, line that must NOT appear)
INJECTIONS = {
    "pte-sp": (
        PT_C,
        "\treturn (pa & SUPERPAGE_PA_MASK) | _PAGE_KERNEL | _PAGE_SUPER;",
        "\treturn (pa & SUPERPAGE_PA_MASK) | _PAGE_KERNEL;",
        0x0a,
        r"^K1 ptw table rejected: kernel_window_pte=0x[0-9a-f]+ code=0xa$",
        r"^K1 ptw post ",
    ),
    "ptbr-ppn": (
        PT_C,
        "\tunsigned long base = (unsigned long)__pa(swapper_pg_dir);",
        "\tunsigned long base = (unsigned long)__pa(swapper_pg_dir) ^ (1UL << 33);",
        0x09,
        r"^K1 ptw table rejected: ptbr_outside_ram=0x[0-9a-f]+ code=0x9$",
        r"^K1 ptw post ",
    ),
    # The live counterpart of the negative case: the *check* still looks at the
    # good base, but the value actually written is unmapped.  The very next
    # instruction fetch makes the walker read a PTE outside physical memory, so
    # the machine stops with the model's named machine fault (spec/Kaiwu
    # §7.1; DADAO-12 §5.2 step 7 gives the guest no recovery for an unmapped
    # vector page).  Expected: named exit, and no "post"/"done"/start_kernel
    # line — it never continues silently.
    "ptbr-live": (
        PT_C,
        "\tdadao_ptbr_write(base | 0xffffUL);",
        "\tdadao_ptbr_write((base | 0xffffUL) ^ (1UL << 33));",
        1,
        r"dadao: page-table access outside physical memory "
        r"\(VA=[0-9a-f]+, PTBR=[0-9a-f]+\)",
        r"^(K1 ptw post |K1 ptw done|start_kernel$)",
    ),
    "no-expect": (
        PT_C,
        "\tif (dadao_trap_probe_register(&k1_pt_probe))",
        "\tif (0)",
        0xe1,                 # supv + CFXMEM, spec/Kaiwu §7.1
        r"^dadao: unrecoverable supv exception cause=CFXMEM\(0x2\) "
        r"ip=0x[0-9a-f]+ info={probe_va:#x} ptbr=0x0 sp=0x[0-9a-f]+$",
        r"^K1 ptw done",
    ),
}


def require_k1_image() -> None:
    """Refuse to interpret a non-K1 image (the default build is the K2 one)."""
    config = _paths.linux_build_dir() / ".config"
    if config.is_file():
        text = config.read_text(encoding="utf-8")
        if "CONFIG_DADAO_K1_EARLY_STOP=y" in text:
            return
    sys.exit("k1_pt_probe: the build tree is not configured for the K1 image; "
             "run `make check-linux-k1` (it applies the K1 config slice) or set "
             "CONFIG_DADAO_K1_EARLY_STOP=y")


def rebuild() -> int:
    rc = defconfig.apply_config_lines(K1_CONFIG)
    if rc != 0:
        return rc
    src = _paths.linux_source_dir()
    cmd, _tools = vmlinux.defconfig.kernel_make_base()
    jobs = os.environ.get("JOBS", "32")
    print(f"[INFO] rebuild (JOBS={jobs})", flush=True)
    proc = subprocess.run(cmd + [f"-j{jobs}", "vmlinux"], cwd=str(src),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-2000:] + proc.stderr[-2000:], file=sys.stderr)
    return proc.returncode


def run_inject(name: str, kernel: Path, ctx: Ctx) -> int:
    rel, old, new, want_rc, want_re, forbid = INJECTIONS[name]
    want_re = want_re.format(probe_va=ctx.probe_va)
    path = _paths.linux_source_dir() / rel
    backup = Path(_WORK_ROOT) / f"{name}.bak"
    before = md5(path)
    backup.write_bytes(path.read_bytes())
    text = path.read_text()
    if text.count(old) != 1:
        print(f"  [FAIL] inject:{name} 注入点唯一 | 期望=1 实际={text.count(old)}")
        return 1
    path.write_text(text.replace(old, new))
    injected = md5(path)
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> {injected[:8]}",
          flush=True)

    fails = 0
    try:
        rc = rebuild()
        if rc != 0:
            print(f"  [FAIL] inject:{name} 重建 | 期望=0 实际={rc}")
            return 1
        rc, text = boot(kernel, f"inject_{name}")
        print(f"---- guest output ({name}) ----")
        print(text.strip())
        print("--------------------------------")
        hit = re.search(want_re, text, re.MULTILINE)
        hit_rc = rc == want_rc
        hit_neg = not re.search(forbid, text, re.MULTILINE)
        for label, ok, expected, actual in (
            ("退出码", hit_rc, hex(want_rc), hex(rc)),
            ("具名行", bool(hit), want_re, hit.group(0) if hit else "<none>"),
            ("禁止行", hit_neg, f"无 {forbid}", "有" if not hit_neg else "无"),
        ):
            print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} {label} | "
                  f"期望={expected} 实际={actual}")
            fails += 0 if ok else 1
    finally:
        path.write_bytes(backup.read_bytes())
        restored = md5(path)
        ok = restored == before
        print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} 还原 (cp) | "
              f"md5 期望={before[:8]} 实际={restored[:8]}")
        fails += 0 if ok else 1
        backup.unlink()

    rc = rebuild()
    if rc != 0:
        print(f"  [FAIL] inject:{name} 还原后重建 | 期望=0 实际={rc}")
        return 1
    rep = k1.Report()
    run_positive(kernel, ctx, rep)
    green = not rep.fails
    print(f"  [{'PASS' if green else 'FAIL'}] inject:{name} 还原后回绿 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败")
    return fails + (0 if green else 1)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    global QEMU
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel", default=None, help="vmlinux under test")
    ap.add_argument("--qemu", default=None, help="qemu-system-dadao binary")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured output and show every check flips")
    ap.add_argument("--inject", action="store_true",
                    help="rebuild with each corruption in place, then restore")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(["positive", "selfcheck"] +
                        [f"inject:{name}" for name in INJECTIONS]))
        return 0

    QEMU = args.qemu
    require_k1_image()
    kernel = Path(args.kernel) if args.kernel else \
        Path(_paths.linux_build_dir()) / "vmlinux"
    if not kernel.is_file():
        raise SystemExit("k1_pt_probe: vmlinux missing; run `make linux-vmlinux`")
    print(f"k1pt: kernel={kernel.name} ({kernel.stat().st_size} B) "
          f"qemu={QEMU or k0.DEFAULT_QEMU}")

    ctx = Ctx(kernel)
    if args.selfcheck:
        return run_selfcheck(kernel, ctx)
    if args.inject:
        rep = k1.Report()
        run_positive(kernel, ctx, rep)
        if rep.fails:
            print("k1_pt_probe: baseline is not green; fix that first")
            return 1
        bad = 0
        for name in INJECTIONS:
            bad += run_inject(name, kernel, ctx)
        print(f"k1_pt_probe: inject {'PASS' if not bad else 'FAIL'} "
              f"({len(INJECTIONS) - min(bad, len(INJECTIONS))}/{len(INJECTIONS)} "
              f"路注入按预期失败并还原)")
        return 0 if not bad else 1

    rep = k1.Report()
    run_positive(kernel, ctx, rep)
    print(f"k1_pt_probe: {rep.total - len(rep.fails)}/{rep.total} PASS")
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
