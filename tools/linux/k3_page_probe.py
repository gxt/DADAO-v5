#!/usr/bin/env python3
"""k3_page_probe.py — M14 K3 page-fault / demand-paging gate (`m14-linux-012`).

K3 turns the supv synchronous-exception channel into a *page-fault* channel: the
machine reports a page-table failure as a class in `excp_cause_id[15:0]` plus
one sub-reason bit in the wyde ADR-0056 assigns to it, and the kernel decides
what that means (fill, replace, or terminate).  The kernel side is
`arch/dadao/mm/fault.c` (the channel) and `arch/dadao/mm/k3_pf_selftest.c` (the
probe, `CONFIG_DADAO_K3_PF_SELFTEST` = one case per image); this gate builds
those images, boots them on the Vast machine and judges what the kernel reports.

Nothing is restated here — every expectation is derived from its owner:

  * the sub-reason bits and their wyde        -> ``contract-see §6.1.1`` (the
    per-bit table) and §6.1 (the shape rule), checked against the kernel's own
    ``arch/dadao/include/asm/cause-sub.h``;
  * the 11 big classes                        -> ``spec/DADAO-12 §4.1``
  * the exit-code segmentation                -> ``spec/Kaiwu §7.1``
  * the page geometry (offset width, entries) -> ``spec/DADAO-12 §2.2.2``
  * the page size the image really has        -> the image's ``.config``
  * the self-check codes (guest segment)      -> ``spec/Kaiwu §7.1``
  * the kernel's own markers                  -> the kernel source

Checks (group ids are what ``--selfcheck``/``--inject`` flip):

  G1  the image is the probe image the gate asked for, and the kernel's
      sub-reason header agrees with ``contract-see §6.1.1`` bit by bit
  G2  the probe's own setup: the shared zero page, the test window base past
      RAM, the superpage scratch
  G3  P1: a first read of a window enters the channel once, is classified as a
      missing class of CFXMEM (raw `cause_id` included) and returns 0
  G4  P8: the fill mapped the shared zero page, read-only, non-executable
  G5  P10: a second window maps the same page, and the page itself is untouched
  G6  P9: a store to that mapping is CFXPERM + NWPERM and replaces it with a
      private zeroed page (one page, one entry, W = 1)
  G7  P2: a second access to the private page does not enter the channel
  G8  P3a-P3e / P4a-P4a4: every missing class the contract defines, data and
      fetch, reaches the branch it must and leaves the access readable /
      executable
  G9  the sub-reason shape check: CFXMEM/CFXPERM need exactly one bit in their
      own wyde, every other class needs nothing above [15:0]
  G10 the window edges: only [start, end) is covered
  T2  a read of an R = 0 page terminates with CFXPERM + NRPERM and §7.1's
      monitor code
  T3  a wild jump terminates with CFXMEM + IGPTRAP, `cause_ip` = `cause_info`
  T4  a data access one page outside a window terminates by name
  T5  a synthetic ADWBFAIL dispatch allocates nothing, retries nothing, prints
      the PTE address and terminates with §7.1's monitor code

``--selfcheck`` mutates the captured runs and shows every group flips.
``--inject`` corrupts the kernel source, rebuilds, asserts the named groups go
red, restores with ``cp`` + md5 and proves the image is green again.

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (spec / contract / kernel source / build tree missing).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                     # noqa: E402  (pins)
from tools.linux import k1_boot_probe as k1boot          # noqa: E402  (symbols)
from tools.linux import k2_trap_probe as k2trap         # noqa: E402  (causes)
from tools.linux import k3_pt_probe as k3pt             # noqa: E402  (geometry)
from tools.linux import make_defconfig as defconfig     # noqa: E402  (config)
from tools.linux import paths as linux_paths            # noqa: E402
from tools.qemu import k0_boot_probe as k0              # noqa: E402  (firmware)

TIMEOUT_QEMU = int(os.environ.get("K3PF_QEMU_TIMEOUT", "180"))
TIMEOUT_BUILD = int(os.environ.get("K3PF_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K3PF_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-012") / "k3_page_probe")

CONTRACT_SEE = _REPO / ".tao" / "contracts" / "contract-see.md"
SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
SOURCE = linux_paths.linux_source_dir()
CAUSE_SUB_H = SOURCE / "arch/dadao/include/asm/cause-sub.h"
SELFTEST_C = SOURCE / "arch/dadao/mm/k3_pf_selftest.c"

#: The probe image pins every milestone boundary (complete set,
#: `make check-config-pins`, ISS-470) so the shared build tree must never leak
#: another image's configuration into this one; the case is the per-image
#: override.  An int pinned ``"n"`` is "left unset" because its `depends on` is
#: not met.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
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
}

#: The K3 page-fault case each image runs (Kconfig `range 0 9`).
IMAGE_PINS = {
    "0": {"CONFIG_DADAO_K3_PF_SELFTEST": "0"},
    "1": {"CONFIG_DADAO_K3_PF_SELFTEST": "1"},
    "2": {"CONFIG_DADAO_K3_PF_SELFTEST": "2"},
    "3": {"CONFIG_DADAO_K3_PF_SELFTEST": "3"},
    "4": {"CONFIG_DADAO_K3_PF_SELFTEST": "4"},
    "5": {"CONFIG_DADAO_K3_PF_SELFTEST": "5"},
    "6": {"CONFIG_DADAO_K3_PF_SELFTEST": "6"},
    "7": {"CONFIG_DADAO_K3_PF_SELFTEST": "7"},
    "8": {"CONFIG_DADAO_K3_PF_SELFTEST": "8"},
    "9": {"CONFIG_DADAO_K3_PF_SELFTEST": "9"},
}


def image(case: int) -> list[str]:
    overrides = IMAGE_PINS.get(
        str(case), {"CONFIG_DADAO_K3_PF_SELFTEST": str(case)})
    return config_pins.config_lines(CONFIG_PINS, overrides)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus live ``[STAT]``."""

    def __init__(self, quiet: bool = False) -> None:
        self.total = 0
        self.fails: list[str] = []
        self.groups: dict[str, list[int]] = {}
        self.quiet = quiet

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        tally = self.groups.setdefault(cid, [0, 0])
        tally[0] += 1
        if not ok:
            tally[1] += 1
            self.fails.append(f"{cid} {name}: 期望={expected} 实际={actual}")
        if not self.quiet:
            print(f"  [{'PASS' if ok else 'FAIL'}] {cid} {name} | "
                  f"期望={expected} 实际={actual}", flush=True)
        return ok

    def stat(self, text: str) -> None:
        if not self.quiet:
            print(f"  [STAT] {text}", flush=True)

    def summary(self) -> str:
        order = [f"G{i}" for i in range(1, 12)] + \
            ["T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]
        parts = []
        for group in order:
            if group in self.groups:
                total, failed = self.groups[group]
                parts.append(f"{group} {total - failed}/{total}")
        return "  ".join(parts)


def kv(line: str) -> dict[str, str]:
    return dict(re.findall(r"(\w+)=(\S+)", line))


def num(text: str | None, default: int = -1) -> int:
    try:
        return int(text, 0) if text is not None else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# expectations parsed from the contract / spec (never restated)
# ---------------------------------------------------------------------------

def _section(text: str, start: str, end: str, what: str) -> str:
    cut = text.split(start, 1)
    if len(cut) != 2:
        raise SystemExit(f"k3_page_probe: '{start}' not found in {what}")
    return cut[1].split(end, 1)[0]


def contract_subcauses() -> dict[str, dict]:
    """``{name: {bit, wyde, cause}}`` from ``contract-see §6.1.1``.

    The table is the authority for every sub-reason bit (ADR-0056 D3); the
    kernel header is checked against it, never the other way round.
    """
    text = CONTRACT_SEE.read_text(encoding="utf-8")
    body = _section(text, "### §6.1.1", "\n### ", "contract-see §6.1.1")
    rows: dict[str, dict] = {}
    for line in body.splitlines():
        m = re.match(r"^\|\s*`\[(\d+)\]`\s*\|\s*wyde(\d)\s*\|\s*`(\w+)`\s*\|"
                     r"\s*`(\w+)`\s*\|", line)
        if not m:
            continue
        rows[m.group(3)] = {"bit": int(m.group(1)), "wyde": int(m.group(2)),
                            "cause": m.group(4)}
    if len(rows) != 18:
        raise SystemExit(f"k3_page_probe: §6.1.1 parsed {len(rows)} sub-causes, "
                         f"expected 18: {sorted(rows)}")
    return rows


def contract_wyde_shifts(subs: dict[str, dict]) -> tuple[int, int]:
    """``(perm_shift, mem_shift)`` — the wyde's low bit, from the table itself."""
    perm = min(row["bit"] for row in subs.values() if row["cause"] == "CFXPERM")
    mem = min(row["bit"] for row in subs.values() if row["cause"] == "CFXMEM")
    return perm, mem


def contract_reserved() -> set[tuple[int, int]]:
    """Every ``[hi:lo] 保留`` range of ``contract-see §6.1`` (the reserved bits)."""
    text = CONTRACT_SEE.read_text(encoding="utf-8")
    body = _section(text, "### §6.1 ", "\n### §6.1.1", "contract-see §6.1")
    return {(int(hi), int(lo)) for hi, lo in
            re.findall(r"`\[(\d+):(\d+)\]`\s*\**\s*保留", body)}


def header_subcauses() -> dict[str, int]:
    """``{NAME: bit}`` from the kernel's own ``asm/cause-sub.h``."""
    if not CAUSE_SUB_H.is_file():
        raise SystemExit(f"k3_page_probe: {CAUSE_SUB_H} missing; run "
                         f"`make fetch apply-series`")
    out = {}
    for name, value in re.findall(
            r"^#define\s+DADAO_SUB_(\w+)\s+(0x[0-9a-fA-F]+|\d+)\b",
            CAUSE_SUB_H.read_text(encoding="utf-8"), re.MULTILINE):
        out[name] = int(value, 0)
    return out


def header_shifts() -> dict[str, int]:
    text = CAUSE_SUB_H.read_text(encoding="utf-8")
    out = {}
    for name in ("PERM_SHIFT", "MEM_SHIFT"):
        m = re.search(rf"^#define\s+DADAO_SUB_{name}\s+(\d+)", text, re.MULTILINE)
        if not m:
            raise SystemExit(f"k3_page_probe: cause-sub.h has no SUB_{name}")
        out[name] = int(m.group(1))
    return out


def header_reserved() -> dict[str, int]:
    """``{MEM_RESERVED, PERM_RESERVED, RESERVED16}`` as bit masks."""
    text = CAUSE_SUB_H.read_text(encoding="utf-8")
    out = {}
    for name in ("MEM_RESERVED", "PERM_RESERVED", "RESERVED16"):
        m = re.search(rf"^#define\s+DADAO_SUB_{name}\s+"
                      rf"\(0x([0-9a-fA-F]+)UL\s*<<\s*(\d+)\)", text, re.MULTILINE)
        if not m:
            raise SystemExit(f"k3_page_probe: cause-sub.h has no SUB_{name} mask")
        out[name] = int(m.group(1), 16) << int(m.group(2))
    return out


def kernel_consts() -> dict[str, int]:
    """Every constant the probe source defines (markers, self-check codes)."""
    if not SELFTEST_C.is_file():
        raise SystemExit(f"k3_page_probe: {SELFTEST_C} missing; run "
                         f"`make fetch apply-series`")
    text = SELFTEST_C.read_text(encoding="utf-8")
    return {name: int(value, 16) for name, value in
            re.findall(r"^#define\s+(K3_PF_\w+)\s+(0x[0-9a-fA-F]+)",
                       text, re.MULTILINE)}


def causes() -> dict[str, int]:
    table = k2trap.spec_cause_table()
    if len(table) != 11:
        raise SystemExit(f"k3_page_probe: §2 cause table has {len(table)} rows")
    return {name: cid for cid, name in table}


def exit_segments() -> dict:
    return k2trap.spec_exit_segments()


def monitor_code(mode: str, cause: str) -> int:
    specs = exit_segments()
    low, _high = specs["ranges"]["monitor"]
    return low | (specs["modes"][mode] << 4) | specs["indices"][cause]


# ---------------------------------------------------------------------------
# run parsing
# ---------------------------------------------------------------------------

def channel_lines(text: str) -> list[dict]:
    """Every ``K3 pf: …`` channel entry, in order."""
    rows = []
    for line in text.splitlines():
        if line.startswith("K3 pf: "):
            row = kv(line)
            if row:
                rows.append(row)
    return rows


def channel_before(text: str, tag: str) -> dict | None:
    """The channel entry that belongs to case @tag (the last one before it)."""
    seen = None
    for line in text.splitlines():
        if line.startswith("K3 pf: "):
            row = kv(line)
            if row:
                seen = row
        elif line.startswith(f"K3 pfc {tag} "):
            return seen
    return None


def case_line(text: str, tag: str) -> dict | None:
    for line in text.splitlines():
        if line.startswith(f"K3 pfc {tag} "):
            row = kv(line)
            if row:
                return row
    return None


def only_line(text: str, prefix: str) -> dict | None:
    rows = [kv(line) for line in text.splitlines() if line.startswith(prefix)]
    return rows[0] if len(rows) == 1 else None


def die_line(text: str) -> dict | None:
    m = re.search(r"^dadao: .*? cause=(\w+)\((0x[0-9a-f]+)\) ip=(\S+) "
                  r"info=(\S+) ptbr=(\S+) sp=(\S+)$", text, re.MULTILINE)
    if not m:
        return None
    return {"cause": m.group(1), "id": m.group(2), "ip": m.group(3),
            "info": m.group(4)}


# ---------------------------------------------------------------------------
# build / run
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def config_text() -> str:
    return (build_dir() / ".config").read_text(encoding="utf-8")


def build_image(case: int) -> int:
    rc = defconfig.apply_config_lines(image(case))
    if rc != 0:
        print(f"k3_page_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the K3 page-fault image (case={case}, JOBS={JOBS})",
          flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-3000:], file=sys.stderr)
        print((proc.stderr or "")[-3000:], file=sys.stderr)
    return proc.returncode


ROM: str | None = None


def firmware() -> str:
    global ROM
    if ROM is None:
        k0.load_contract()
        if not k0.ABI:
            raise SystemExit("k3_page_probe: the boot contract projection is empty")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        k0.WORK = str(SCRATCH / "bootrom")
        ROM = k0.build_firmware(k0.WORK)
    return ROM


def boot(tag: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k3_page_probe: {kernel} missing; run "
                         f"`make linux-vmlinux`")
    rc, _blocks, err, _log = k0.run_qemu(k0.DEFAULT_QEMU, firmware(),
                                         str(kernel), f"k3pf_{tag}",
                                         dfilter="0x0+0x4", timeout=TIMEOUT_QEMU)
    text = err or ""
    # Keep the console of every run: a 124 is an observation, and a red image is
    # evidence, so neither may only exist in this process' memory.
    console = SCRATCH / "log" / f"{tag}.console"
    console.parent.mkdir(parents=True, exist_ok=True)
    console.write_text(text, encoding="utf-8")
    if rc is None:
        return 124, text
    return rc, text


# ---------------------------------------------------------------------------
# checks — image 1 (the recoverable cases)
# ---------------------------------------------------------------------------

def check_image(case: int, rc: int, text: str, snap: dict, rep: Report) -> None:
    subs = contract_subcauses()
    perm_shift, mem_shift = contract_wyde_shifts(subs)
    cls = causes()
    codes = kernel_consts()
    magic = codes.get("K3_PF_MAGIC", 0)
    cfg = snap["config"].splitlines()
    page_shift = next((int(line.split("=", 1)[1], 0) for line in cfg
                       if line.startswith("CONFIG_PAGE_SHIFT=")), -1)
    page_offset = next((int(line.split("=", 1)[1], 0) for line in cfg
                        if line.startswith("CONFIG_PAGE_OFFSET=")), -1)
    ppn_low, ppn_high = k3pt.spec_l1_fields()["PPN"]
    ppn_mask = ((1 << (ppn_high - ppn_low + 1)) - 1) << ppn_low

    def pfn(pte: int) -> int:
        return ((pte & ppn_mask) >> ppn_low) if page_shift > 0 else -1
    o_bits, per_level = k3pt.spec_normal_page()
    fail_low, fail_high = exit_segments()["ranges"]["guest"]

    def sub_id(name: str) -> int:
        row = subs[name]
        return cls[row["cause"]] | (1 << row["bit"])

    # ---- G1: this is the image the gate asked for, and the kernel header is
    # the contract's projection, bit by bit.
    rep.check("G1", f"镜像配置：CONFIG_DADAO_K3_PF_SELFTEST={case}",
              f"CONFIG_DADAO_K3_PF_SELFTEST={case}",
              next((line for line in cfg
                    if line.startswith("CONFIG_DADAO_K3_PF_SELFTEST=")),
                   "<unset>"))
    rep.check("G1", "镜像配置：三条早停边界与 PT 自检都关", [],
              [line for line in cfg
               if re.match(r"CONFIG_DADAO_K(1_EARLY_STOP|2_TIME_STOP|"
                           r"2_EARLY_STOP|3_PT_SELFTEST)=(y|1)", line)])
    rep.check("G1", "`.config` PAGE_SHIFT == §2.2.2 页内偏移位宽", o_bits,
              page_shift)
    rep.check("G1", "镜像里有通道与自检符号", [True, True],
              ["dadao_do_page_fault" in snap["syms"],
               "dadao_k3_pf_selftest" in snap["syms"]])

    header = header_subcauses()
    rep.check("G1", "cause-sub.h 的子原因名集合 == contract-see §6.1.1",
              sorted(subs), sorted(name for name in header
                                   if name in subs))
    rep.check("G1", "cause-sub.h 的逐位值与 §6.1.1 一致", {},
              {name: f"header={header[name]} contract={subs[name]['bit']}"
               for name in subs if header.get(name) != subs[name]["bit"]})
    shifts = header_shifts()
    rep.check("G1", "wyde 低位（CFXPERM）", perm_shift, shifts["PERM_SHIFT"])
    rep.check("G1", "wyde 低位（CFXMEM）", mem_shift, shifts["MEM_SHIFT"])
    reserved = header_reserved()
    ranges = contract_reserved()
    rep.check("G1", "§6.1 的保留区 == [63:58]/[47:40]/[31:16]",
              {(63, 58), (47, 40), (31, 16)}, ranges)
    want_reserved = {(hi, lo): ((1 << (hi - lo + 1)) - 1) << lo
                     for hi, lo in ranges}
    got = {"MEM_RESERVED": reserved["MEM_RESERVED"],
           "PERM_RESERVED": reserved["PERM_RESERVED"],
           "RESERVED16": reserved["RESERVED16"]}
    rep.check("G1", "保留位掩码 == §6.1 的 [63:58]/[47:40]/[31:16]",
              [want_reserved[(63, 58)], want_reserved[(47, 40)],
               want_reserved[(31, 16)]],
              [got["MEM_RESERVED"], got["PERM_RESERVED"], got["RESERVED16"]])
    rep.check("G1", f"自检码全在 guest FAIL 段（{hex(fail_low)}-{hex(fail_high)}）",
              {}, {name: hex(v) for name, v in codes.items()
                   if name.startswith("K3_PF_FAIL_") and
                   not fail_low <= v <= fail_high})
    rep.stat(f"契约子原因 {len(subs)} 条；自检码 "
             f"{len({k for k in codes if k.startswith('K3_PF_FAIL_')})} 条")

    # ---- G2: the probe's own setup
    init = only_line(text, "K3 pf init ")
    if init is None:
        rep.check("G2", "K3 pf init 行存在", "一行", "缺失/多行")
        raise SystemExit("k3_page_probe: the probe did not report its setup")
    m = re.match(r"(0x[0-9a-f]+)\+(0x[0-9a-f]+)", init.get("ram", ""))
    ram_base, ram_size = (int(m.group(1), 16), int(m.group(2), 16)) if m \
        else (-1, 0)
    zero_pa = num(init.get("zero_pa"))
    page_size = 1 << page_shift if page_shift > 0 else -1
    rep.check("G2", "零页在 RAM 内", True,
              ram_base <= zero_pa < ram_base + ram_size)
    rep.check("G2", "零页 64 KiB 对齐（§2.2.2 页大小）", 0, zero_pa & (page_size - 1))
    base = num(init.get("base"))
    superpage = num(init.get("super"))
    rep.check("G2", "PAGE_OFFSET 在 `.config` 里（内核窗口基址）", True,
              page_offset > 0)
    rep.check("G2", "测试窗口基址 = 内核窗口基址 + RAM 之后第一个 512 MiB 超页",
              page_offset + ((ram_size + (1 << 29) - 1) >> 29 << 29), base)
    rep.check("G2", "超页基址 = RAM 起点的超页对齐值", ram_base & ~((1 << 29) - 1),
              superpage)
    rep.check("G2", "data_pa 在 RAM 内", True,
              ram_base <= num(init.get("data_pa")) < ram_base + ram_size)
    rep.check("G2", "页池至少含零页与代码页", True, num(init.get("pool")) >= 2)
    rep.check("G2", "code_off 在页内且留足余量（stub 不跨页）", True,
              0 <= num(init.get("code_off")) <= page_size - 128)

    # ---- G3: P1 — one channel entry, a missing class, retried, reads 0
    p1 = case_line(text, "P1")
    entry = channel_before(text, "P1")
    if p1 is None or entry is None:
        rep.check("G3", "P1 行与通道行存在", "两者都有", "缺失")
    else:
        rep.check("G3", "P1 读回 0", 0, num(p1.get("word")))
        rep.check("G3", "P1 恰进通道一次", 1, num(p1.get("entries")))
        rep.check("G3", "P1 通道大类", "CFXMEM", entry.get("cause"))
        rep.check("G3", "P1 原始 cause_id == CFXMEM|DGPTRAP（契约派生）",
                  hex(sub_id("DGPTRAP")), entry.get("id"))
        rep.check("G3", "P1 子原因名 == 契约的 DGPTRAP", "DGPTRAP",
                  entry.get("sub"))
        rep.check("G3", "P1 走了缺失填充分支", "fill-zero", entry.get("result"))
        rep.check("G3", "P1 命中的窗口就是被访问的窗口",
                  num(p1.get("win")), num(entry.get("vma", "0-0").split("-")[0]))

    # ---- G4: P8 — the fill is the shared zero page, read-only
    p8 = case_line(text, "P8")
    if p8 is None:
        rep.check("G4", "P8 行存在", "存在", "缺失")
    else:
        rep.check("G4", "P8 的 PTE PA == 零页 PA（PFN）",
                  pfn(zero_pa), num(p8.get("pte_pa")))
        rep.check("G4", "P8 W = 0（共享只读）", 0, num(p8.get("w")))
        rep.check("G4", "P8 R = 1", 1, num(p8.get("r")))
        rep.check("G4", "P8 X = 0（不可执行）", 0, num(p8.get("x")))

    # ---- G5: P10 — a second window, the same page, untouched
    p10 = case_line(text, "P10")
    if p10 is None:
        rep.check("G5", "P10 行存在", "存在", "缺失")
    else:
        rep.check("G5", "P10 第二窗口读到 0", 0, num(p10.get("word_b")))
        rep.check("G5", "P10 两处 PTE 的 PA 相同且都是零页",
                  [pfn(zero_pa), pfn(zero_pa)],
                  [pfn(num(p10.get("pte_a"))), pfn(num(p10.get("pte_b")))])
        rep.check("G5", "P10 零页未被写（整页扫描）", 0, num(p10.get("zero_dirty")))

    # ---- G6: P9 — the write replaces the mapping
    p9 = case_line(text, "P9")
    entry9 = channel_before(text, "P9")
    if p9 is None or entry9 is None:
        rep.check("G6", "P9 行与通道行存在", "两者都有", "缺失")
    else:
        rep.check("G6", "P9 写后读回一致", codes.get("K3_PF_MAGIC"),
                  num(p9.get("word")))
        rep.check("G6", "P9 新 PA != 零页 PA（不是复制零页）", True,
                  num(p9.get("pte_pa")) != pfn(zero_pa))
        rep.check("G6", "P9 W = 1", 1, num(p9.get("w")))
        rep.check("G6", "P9 恰分配一页（池计数 +1）", 1,
                  num(p9.get("allocs")) - num(p9.get("allocs_before")))
        rep.check("G6", "P9 恰进通道一次（计数 +1）", 1,
                  num(p9.get("entries")) - num(p9.get("entries_before")))
        rep.check("G6", "P9 通道大类 == CFXPERM", "CFXPERM", entry9.get("cause"))
        rep.check("G6", "P9 原始 cause_id == CFXPERM|NWPERM（契约派生）",
                  hex(sub_id("NWPERM")), entry9.get("id"))
        rep.check("G6", "P9 子原因名 == 契约的 NWPERM", "NWPERM",
                  entry9.get("sub"))
        rep.check("G6", "P9 走了零页换新页分支", "replace-zero",
                  entry9.get("result"))

    # ---- G7: P2 — the private page no longer faults
    p2 = case_line(text, "P2")
    if p2 is None:
        rep.check("G7", "P2 行存在", "存在", "缺失")
    else:
        rep.check("G7", "P2 不再进通道（计数 +0）", num(p2.get("entries_before")),
                  num(p2.get("entries")))
        rep.check("G7", "P2 写后读回一致", True,
                  num(p2.get("word2")) == codes.get("K3_PF_MAGIC", 0) + 1)

    # ---- G6 (continued): P9b — a store to a never-read window
    p9b = case_line(text, "P9b")
    if p9b is None:
        rep.check("G6", "P9b 行存在（写缺页，从未读过）", "存在", "缺失")
    else:
        rep.check("G6", "P9b 冷写后读回一致", magic + 2, num(p9b.get("word")))
        rep.check("G6", "P9b 新 PA != 零页 PA", True,
                  num(p9b.get("pte_pa")) != pfn(zero_pa))
        rep.check("G6", "P9b W = 1", 1, num(p9b.get("w")))
        rep.check("G6", "P9b 恰分配一页", 1, num(p9b.get("allocs_delta")))
        rep.check("G6", "P9b 两次进通道（先填充、后换页）", 2,
                  num(p9b.get("entries_delta")))
        rep.check("G6", "P9b 零页未被写", 0, num(p9b.get("zero_dirty")))

    # ---- G8: every missing class, data and fetch
    fill_cases = {
        "P3a": ("DGPTRAP", "fill-zero", 0),
        "P3b": ("DGPTRAP", "fill-zero", 0),
        "P3c": ("DGPFTRAP", "frag-set", magic),
        "P3d": ("DSPFTRAP", "frag-set", magic),
        "P3e": ("DSPTRAP", "fill-super", magic),
        "P4a": ("IGPTRAP", "fill-code", magic),
        "P4a2": ("IGPTRAP", "fill-code", magic),
        "P4a3": ("ISPFTRAP", "frag-set", magic),
        "P4a4": ("ISPTRAP", "fill-super", magic),
    }
    for tag, (name, result, value) in fill_cases.items():
        row = case_line(text, tag)
        entry = channel_before(text, tag)
        if row is None or entry is None:
            rep.check("G8", f"{tag} 行与通道行存在", "两者都有", "缺失")
            continue
        rep.check("G8", f"{tag} 原始 cause_id == {subs[name]['cause']}|{name}"
                        f"（契约派生）", hex(sub_id(name)), entry.get("id"))
        rep.check("G8", f"{tag} 子原因名", name, entry.get("sub"))
        rep.check("G8", f"{tag} 分支", result, entry.get("result"))
        extra = row.get("word") if not tag.startswith("P4a") else row.get("magic")
        rep.check("G8", f"{tag} 访问/执行结果 == 预置值", value, num(extra))
        if tag.startswith("P4a"):
            rep.check("G8", f"{tag} cause_ip == 目标地址",
                      num(row.get("target")), num(entry.get("ip")))
            rep.check("G8", f"{tag} 命中了窗口（VMA）", True,
                      num(entry.get("vma", "0-0").split("-")[0]) != 0)

    # ---- G9: the sub-reason shape check
    verdicts = {}
    for line in text.splitlines():
        m = re.match(r"^K3 pf layout (\w+)=(-?\d+) id=(\S+)$", line)
        if m:
            verdicts[m.group(1)] = (int(m.group(2)), int(m.group(3), 0))
    rep.check("G9", "layout 逐条数", 10, len(verdicts))

    legal = {"CFXMEM": 0, "CFXPERM": 0}
    for row in subs.values():
        own = mem_shift if row["cause"] == "CFXMEM" else perm_shift
        legal[row["cause"]] |= 1 << (row["bit"] - own)
    big_by_name = {name: cls[name] for name in ("CFXMEM", "CFXPERM")}

    def want_verdict(name: str) -> str:
        """ok / rejected, derived from §6.1's rule (never from the kernel)."""
        if name not in verdicts:
            return "missing"
        cid = verdicts[name][1]
        big = cid & 0xffff
        sub = cid & ~0xffff
        if sub & (((1 << 16) - 1) << 16):
            return "rejected"                      # [31:16] is reserved
        own = {big_by_name["CFXMEM"]: mem_shift,
               big_by_name["CFXPERM"]: perm_shift}.get(big)
        if own is None:
            return "ok" if sub == 0 else "rejected"
        other = perm_shift if own == mem_shift else mem_shift
        if (sub >> other) & 0xffff:
            return "rejected"                      # the other class's wyde
        bits = (sub >> own) & 0xffff
        want = legal["CFXMEM"] if own == mem_shift else legal["CFXPERM"]
        return "ok" if bits and not bits & (bits - 1) and not bits & ~want \
            else "rejected"

    for name in verdicts:
        rep.check("G9", f"layout {name}（§6.1 规则派生）", want_verdict(name),
                  "ok" if verdicts[name][0] == 0 else "rejected")

    # ---- G11: the exit-code segmentation ignores the sub-reason wyde
    ex = only_line(text, "K3 pf exit ")
    other_low, other_high = exit_segments()["ranges"]["other"]
    if ex is None:
        rep.check("G11", "K3 pf exit 行存在", "一行", "缺失/多行")
    else:
        rep.check("G11", "带子原因的 CFXTRAP 仍按大类命名", "CFXTRAP",
                  ex.get("dirty_name"))
        rep.check("G11", "裸 CFXTRAP 的名字", "CFXTRAP", ex.get("bare_name"))
        rep.check("G11", "退出码与裸 CFXTRAP 相同（分段不看子原因）",
                  ex.get("bare_code"), ex.get("dirty_code"))
        rep.check("G11", f"CFXTRAP 落在「其它 cfx」段 "
                         f"({other_low}-{other_high})", True,
                  other_low <= num(ex.get("bare_code")) <= other_high)
        rep.check("G11", "内核自评", 1, num(ex.get("ok")))

    # ---- G10: the window edges
    vma = only_line(text, "K3 pf vma ")
    if vma is None:
        rep.check("G10", "K3 pf vma 行存在", "一行", "缺失/多行")
    else:
        rep.check("G10", "start-1 不在窗口内", 0, num(vma.get("before1")))
        rep.check("G10", "start-一页不在窗口内", 0, num(vma.get("before_page")))
        rep.check("G10", "start 在窗口内", 1, num(vma.get("inside")))
        rep.check("G10", "end-1 在窗口内", 1, num(vma.get("last")))
        rep.check("G10", "end 不在窗口内（半开区间）", 0, num(vma.get("at_end")))

    # ---- the run itself
    done = only_line(text, "K3 pf done:")
    rep.check("G2", "guest rc（SYS_EXIT 子码）", 0, rc)
    rep.check("G2", "存在完成行", True, done is not None)
    if done is not None:
        rep.check("G2", "完成行的 case", case, num(done.get("case")))
    rep.check("G2", "无具名异常终止（dadao: 行）", [],
              [line for line in text.splitlines()
               if line.startswith("dadao: ")])


# ---------------------------------------------------------------------------
# checks — the terminating images
# ---------------------------------------------------------------------------

def check_terminal(case: int, rc: int, text: str, rep: Report) -> None:
    subs = contract_subcauses()
    cls = causes()
    group = {2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6"}[case]

    def sub_id(name: str) -> int:
        row = subs[name]
        return cls[row["cause"]] | (1 << row["bit"])

    wanted = {
        2: ("NRPERM", "die-perm", "CFXPERM"),
        3: ("IGPTRAP", "die-no-vma", "CFXMEM"),
        4: ("DGPTRAP", "die-no-vma", "CFXMEM"),
        5: ("ADWBFAIL", "die-adwb", "CFXMEM"),
        6: ("NSPERM", "die-perm", "CFXPERM"),
    }[case]
    name, result, big = wanted

    entry = channel_lines(text)[0] if channel_lines(text) else None
    die = die_line(text)
    if entry is None or die is None:
        rep.check(group, "通道行与终止行都存在", "两者都有", "缺失")
        return

    rep.check(group, f"通道大类 == {big}", big, entry.get("cause"))
    rep.check(group, f"原始 cause_id == {big}|{name}（契约派生）",
              hex(sub_id(name)), entry.get("id"))
    rep.check(group, f"子原因名 == {name}", name, entry.get("sub"))
    rep.check(group, f"分支 == {result}", result, entry.get("result"))
    rep.check(group, f"退出码 == §7.1 monitor(supv, {big})",
              hex(monitor_code("supv", big)), hex(rc))
    rep.check(group, "终止行的原因名", big, die["cause"])
    rep.check(group, "终止行的原因编号 == 大类（子原因不进退出码）",
              hex(cls[big]), die["id"])
    rep.check(group, "通道行数 == 1（不重试）", 1, len(channel_lines(text)))

    if case in (3, 4):
        rep.check(group, "cause_info == ci 的地址（= 通道行的 va）",
                  entry.get("va"), die["info"])
        rep.check(group, "没有窗口命中", [0, 0],
                  [num(entry.get("vma", "0-0").split("-")[0]),
                   num(entry.get("vma", "0-0").split("-")[1])])
        if case == 3:   # a fetch fault: cause_ip *is* the target address
            rep.check(group, "cause_ip == cause_info（取指）", die["info"],
                      die["ip"])
    if case in (2, 6):
        rep.check(group, "cause_info == 读失败的地址", entry.get("va"),
                  die["info"])
    if case == 5:
        head = case_line(text, "P6")
        if head is None:
            rep.check(group, "P6 前置行存在", "一行", "缺失/多行")
        else:
            rep.check(group, "ADWBFAIL 不分配页（池计数不变）", head.get("pool"),
                      entry.get("pool"))
            rep.check(group, "cause_info == 打印的 PTE 物理地址",
                      head.get("pte_pa"), entry.get("va"))
            rep.check(group, "终止行的 info == 该 PTE 地址", head.get("pte_pa"),
                      die["info"])


# ---------------------------------------------------------------------------
# checks - the malformed-id dispatch images (cases 7-9)
# ---------------------------------------------------------------------------

#: The three malformed shapes cases 7-9 dispatch.  The *shape* is the test
#: design; every bit number it uses comes from ``contract-see §6.1.1`` (the
#: sub-reason bit) or §6.1 (the reserved ``[31:16]`` range), never from a
#: literal here.
MALFORMED = {7: "P7", 8: "P8", 9: "P9"}


def malformed_id(case: int, subs: dict, cls: dict,
                 ranges: set[tuple[int, int]]) -> int:
    """The raw 64-bit id case @case dispatches, derived from the contract."""
    if case == 7:                       # reserved [31:16] + one real bit
        low16 = min(lo for (hi, lo) in ranges if (hi, lo) == (31, 16))
        return cls["CFXMEM"] | (1 << low16) | (1 << subs["DGPTRAP"]["bit"])
    if case == 8:                       # two bits in the class's own wyde
        return (cls["CFXMEM"] | (1 << subs["IGPTRAP"]["bit"]) |
                (1 << subs["DGPTRAP"]["bit"]))
    return cls["CFXMEM"] | (1 << subs["NRPERM"]["bit"])   # the other wyde


def check_malformed(case: int, rc: int, text: str, rep: Report) -> None:
    """A malformed id must be refused by the dispatcher, not decoded.

    The window behind ``cause_info`` is registered by the probe, so a dispatcher
    that let the id through to the page-fault channel would fill it and print a
    ``fill-*`` line; the assertions below are exactly "that did not happen, and
    the id reached the named termination untouched".
    """
    subs = contract_subcauses()
    cls = causes()
    group = {7: "T7", 8: "T8", 9: "T9"}[case]
    want = malformed_id(case, subs, cls, contract_reserved())
    head = case_line(text, MALFORMED[case])
    die = die_line(text)
    chans = channel_lines(text)
    fatal = [line for line in text.splitlines()
             if re.match(r"^dadao: .*? cause=\w+\(0x[0-9a-f]+\) .*$", line)]
    fills = [line for line in text.splitlines() if "result=fill-" in line]

    if head is None:
        rep.check(group, "合成分派的前置行存在", "存在", "缺失")
        return
    rep.check(group, "送进分派器的 id == 契约派生的畸形 id", hex(want),
              head.get("id"))
    rep.check(group, "畸形 id 未被当成大类（原始值 != 掩码后的大类）", True,
              num(head.get("id")) != cls["CFXMEM"])
    rep.check(group, "具名终止：终止行恰 1 条", 1, len(fatal))
    rep.check(group, "没有任何通道行（未进页故障解码器）", 0, len(chans))
    rep.check(group, "没有任何 fill-* 分支", 0, len(fills))
    if die is None:
        rep.check(group, "终止行存在", "存在", "缺失")
        return
    rep.check(group, "终止行的原因名 == 大类", "CFXMEM", die["cause"])
    rep.check(group, "终止行带原始 64 位 id（未经掩码）", hex(want), die["id"])
    rep.check(group, "退出码 == §7.1 monitor(supv, CFXMEM)",
              hex(monitor_code("supv", "CFXMEM")), hex(rc))
    rep.check(group, "cause_info == 窗口内地址", head.get("va"), die["info"])


def judge(case: int, rc: int, text: str, snap: dict, rep: Report) -> None:
    """Route one captured run to the checker its image belongs to."""
    if case == 1:
        check_image(1, rc, text, snap, rep)
    elif case in MALFORMED:
        check_malformed(case, rc, text, rep)
    else:
        check_terminal(case, rc, text, rep)


# ---------------------------------------------------------------------------
# --selfcheck: every group must be able to go red
# ---------------------------------------------------------------------------

#: (group, text key, line prefix, field, replacement) — one mutation per group.
SELFCHECK = {
    "G2": ("case1", "K3 pf init ", "base", lambda v: hex(int(v, 0) + 1)),
    "G3": ("case1", "K3 pfc P1 ", "entries", lambda v: "2"),
    "G4": ("case1", "K3 pfc P8 ", "w", lambda v: "1"),
    "G5": ("case1", "K3 pfc P10 ", "zero_dirty", lambda v: "0x1"),
    "G6": ("case1", "K3 pfc P9 ", "w", lambda v: "0"),
    "G7": ("case1", "K3 pfc P2 ", "entries", lambda v: str(int(v, 0) + 1)),
    "G8": ("case1", "K3 pfc P3c ", "word", lambda v: "0x0"),
    "G9": ("case1", "K3 pf layout other_dirty=", "other_dirty", lambda v: "0"),
    "G10": ("case1", "K3 pf vma ", "at_end", lambda v: "1"),
    "G11": ("case1", "K3 pf exit ", "dirty_code", lambda v: "0xe1"),
    "T2": ("case2", "K3 pf: ", "sub", lambda v: "NSPERM"),
    "T3": ("case3", "K3 pf: ", "result", lambda v: "die-perm"),
    "T4": ("case4", "K3 pf: ", "result", lambda v: "fill-zero"),
    "T5": ("case5", "K3 pf: ", "result", lambda v: "die-no-vma"),
    "T6": ("case6", "K3 pf: ", "sub", lambda v: "NRPERM"),
    # malformed-id dispatch: the die line must carry the raw id (T7), the id
    # handed to the dispatcher must be the derived one (T8), the address must
    # be the window one (T9).
    "T7": ("case7", "dadao: unrecoverable", "cause",
           lambda v: "CFXMEM(0x2)"),
    "T8": ("case7", "K3 pfc P8 ", "id", lambda v: "0x2"),
    "T9": ("case7", "K3 pfc P9 ", "va", lambda v: "0x0"),
}


def mutate(text: str, group: str) -> str:
    _key, prefix, field, fn = SELFCHECK[group]
    out = []
    done = False
    for line in text.splitlines():
        if not done and line.startswith(prefix):
            if group == "G9":
                line = re.sub(r"(other_dirty=)(-?\d+)", r"\g<1>" + fn("0"), line,
                              count=1)
                done = True
            else:
                line = re.sub(rf"(\b{re.escape(field)}=)(\S+)",
                              lambda m: m.group(1) + fn(m.group(2)), line,
                              count=1)
                done = True
        out.append(line)
    if not done:
        raise SystemExit(f"k3_page_probe: --selfcheck: no '{prefix}' line")
    return "\n".join(out) + "\n"


def run_selfcheck(runs: dict[int, tuple[int, str]], snaps: dict[int, dict],
                  problems: list[str]) -> int:
    for group, (_key, _prefix, _field, _fn) in SELFCHECK.items():
        case = int(group[1]) if group.startswith("T") else 1
        rc, text = runs[case]
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                judge(case, rc, mutate(text, group), snaps.get(case, {}), rep)
            except SystemExit as exc:
                problems.append(f"selfcheck:{group}: {exc}")
                continue
        red = [msg for msg in rep.fails if msg.startswith(group)]
        other = [msg for msg in rep.fails if not msg.startswith(group)]
        ok = bool(red) and not other
        print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck:{group} 注入变异后本组变红"
              f"（其它组不动） | 期望=本组 FAIL 实际="
              f"{red[0] if red else '未变红'}", flush=True)
        if not ok:
            problems.append(f"selfcheck:{group}: 未按预期变红（本组 {len(red)} 条，"
                            f"其它 {len(other)} 条）")
    if problems:
        print("k3_page_probe: --selfcheck FAIL: " + "; ".join(problems),
              file=sys.stderr)
        return 1
    print(f"k3_page_probe: --selfcheck PASS ({len(SELFCHECK)}/{len(SELFCHECK)})")
    return 0


# ---------------------------------------------------------------------------
# --inject: corrupt the kernel, rebuild, expect red, restore, expect green
# ---------------------------------------------------------------------------

FAULT_C = "arch/dadao/mm/fault.c"
CAUSE_SUB = "arch/dadao/include/asm/cause-sub.h"
TRAPS_C = "arch/dadao/kernel/traps.c"

INJECTIONS = {
    # ① the missing-class predicate stops covering DGPFTRAP/DSPFTRAP: the GPF
    #    branches fall through to "unknown sub-reason" and the probe dies.
    "missing-gpf": (
        CAUSE_SUB,
        "\treturn pos >= DADAO_SUB_IGPTRAP && pos <= DADAO_SUB_DSPFTRAP;\n",
        "\treturn pos >= DADAO_SUB_IGPTRAP && pos < DADAO_SUB_DGPFTRAP;\n",
        1, ("G8",)),
    # ② the fill reports "done" without installing anything: the retry budget
    #    (not an infinite loop) has to end the boot.
    "retry-no-fill": (
        FAULT_C,
        "\tif (!dadao_zero_pa)\n\t\treturn NULL;\n"
        "\tset_pte(ptep, __pte(dadao_pf_zero_pte()));\n"
        "\tdadao_pf_publish(vma, addr, ptep);\n\treturn \"fill-zero\";\n",
        "\tif (!dadao_zero_pa)\n\t\treturn NULL;\n\treturn \"fill-zero\";\n",
        1, ("G3",)),
    # ③ ADWBFAIL treated like an ordinary fault: it is looked up as a VA (it is
    #    a PTE physical address) and reported as "no window".
    "adwbfail-as-fault": (
        FAULT_C,
        "\t} else if (pos == DADAO_SUB_ADWBFAIL) {\n",
        "\t} else if (0 && pos == DADAO_SUB_ADWBFAIL) {\n",
        5, ("T5",)),
    # ④ the PTE store is published without the invalidation: the write to the
    #    zero page keeps hitting the read-only translation.
    "no-invalidate": (
        FAULT_C,
        "\tupdate_mmu_cache(vma, addr, ptep);\n"
        "\tlocal_flush_tlb_page(vma, addr);\n",
        "\tupdate_mmu_cache(vma, addr, ptep);\n",
        1, ("G6", "G7")),
    # ⑤ no window is allowed through: the handler retries a fault it cannot fix,
    #    so the retry budget has to end it instead of the named verdict.
    "no-vma-pass": (
        FAULT_C,
        "\t} else if (!(vma = dadao_pf_find_vma(info))) {\n"
        "\t\tresult = \"die-no-vma\";\n",
        "\t} else if (!(vma = dadao_pf_find_vma(info))) {\n"
        "\t\tresult = \"fill-zero\";\n",
        4, ("T4",)),
    # ⑦ the exit-code segmentation stops masking the class: a dirty CFXTRAP
    #    falls into the monitor segment (its sub-reason bit sits *above* the
    #    class bit, so __ffs already lands on CFXMEM's index for CFXMEM).
    "exit-mask-off": (
        TRAPS_C,
        "\tcause = DADAO_CAUSE_CLASS(cause);\n"
        "\tif (cause == DADAO_CAUSE_CFXTRAP || cause == DADAO_CAUSE_CFXESC)\n",
        "\tif (cause == DADAO_CAUSE_CFXTRAP || cause == DADAO_CAUSE_CFXESC)\n",
        1, ("G11",)),
    # ⑧ the dispatcher stops refusing a malformed sub-reason: the id falls
    #    through to the page-fault channel, which *fills* the window the probe
    #    registered (F1 of the round-1 review: without this the rule "a
    #    malformed sub-reason is never read as a page fault" had no reachable
    #    FAIL path).
    "malformed-dispatch": (
        TRAPS_C,
        "\tif (dadao_subcause_layout(raw_cause) != DADAO_SUB_LAYOUT_OK)\n"
        "\t\tdadao_die(regs, raw_cause, info);\n",
        "\t/* injected: the malformed sub-reason is not refused */\n",
        7, ("T7",)),
    # ⑨ the same edit, judged on the multi-bit shape: there the bypass dies
    #    through the page-fault channel as well, so the discriminator is the
    #    channel line ("not decoded at all"), not the fill.
    "malformed-multi": (
        TRAPS_C,
        "\tif (dadao_subcause_layout(raw_cause) != DADAO_SUB_LAYOUT_OK)\n"
        "\t\tdadao_die(regs, raw_cause, info);\n",
        "\t/* injected: the malformed sub-reason is not refused */\n",
        8, ("T8",)),
    # ⑥ a non-page-table cause keeps its high bits: §6.1 requires [63:16] = 0
    #    for every class that carries no sub-reason.
    "layout-other-dirty": (
        CAUSE_SUB,
        "\t\t/* Every other class carries no sub-reason at all. */\n"
        "\t\treturn sub ? DADAO_SUB_LAYOUT_FOREIGN : DADAO_SUB_LAYOUT_OK;\n",
        "\t\t/* injected: the other classes are not checked */\n"
        "\t\treturn DADAO_SUB_LAYOUT_OK;\n",
        1, ("G9",)),
}


def run_inject(name: str, problems: list[str]) -> None:
    rel, old, new, case, want_groups = INJECTIONS[name]
    path = SOURCE / rel
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
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> {md5(path)[:8]}",
          flush=True)
    try:
        rc_build = build_image(case)
        if rc_build != 0:
            problems.append(f"inject:{name}: 重建 rc={rc_build}")
        else:
            rc, boot_text = boot(f"inject_{name}")
            rep = Report(quiet=True)
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    judge(case, rc, boot_text,
                          {"config": config_text(),
                           "syms": k1boot.symbols(kernel_path())}, rep)
                except SystemExit as exc:
                    for group in want_groups:
                        rep.fails.append(f"{group} 行缺失: {exc}")
            rows = [line for line in boot_text.splitlines()
                    if line.startswith("K3 pf") or line.startswith("dadao: ")]
            print(f"---- guest channel/die lines ({name}, rc={rc}) ----",
                  flush=True)
            print("\n".join(rows[-10:]), flush=True)
            print(f"---- guest tail ({name}) ----", flush=True)
            print(boot_text.strip()[-400:], flush=True)
            print("-------------------------------------", flush=True)
            for group in want_groups:
                red = [msg for msg in rep.fails if msg.startswith(group)]
                print(f"  [{'PASS' if red else 'FAIL'}] inject:{name} 断言 "
                      f"{group} 变红 | 期望={group} 出现 FAIL 实际="
                      f"{red[0] if red else '未变红'}", flush=True)
                if not red:
                    problems.append(f"inject:{name}: {group} 未变红")
    except Exception as exc:            # restore even if the run blew up
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

    rc_build = build_image(case)
    if rc_build != 0:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    rc, boot_text = boot(f"inject_{name}_green")
    rep = Report(quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            judge(case, rc, boot_text,
                  {"config": config_text(),
                   "syms": k1boot.symbols(kernel_path())}, rep)
        except SystemExit as exc:
            rep.fails.append(f"G0 {exc}")
    green = not rep.fails
    print(f"  [{'PASS' if green else 'FAIL'}] inject:{name} 还原后回绿 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
    if not green:
        problems.append(f"inject:{name}: 还原后仍红：{rep.fails[0]}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="K3 page-fault channel gate")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured runs; every group must flip")
    ap.add_argument("--inject", nargs="*", metavar="NAME",
                    help="corrupt the kernel, rebuild, expect red, restore")
    ap.add_argument("--list", action="store_true", help="list injections")
    args = ap.parse_args()

    if args.list:
        print("\n".join(INJECTIONS))
        return 0

    if args.inject is not None:
        names = args.inject or list(INJECTIONS)
        unknown = [n for n in names if n not in INJECTIONS]
        if unknown:
            print(f"k3_page_probe: unknown injection(s): {unknown}",
                  file=sys.stderr)
            return 2
        problems: list[str] = []
        for name in names:
            print(f"[INFO] injection {name}", flush=True)
            run_inject(name, problems)
        total = len(names)
        if problems:
            print("k3_page_probe: --inject FAIL: " + "; ".join(problems),
                  file=sys.stderr)
            return 1
        print(f"k3_page_probe: --inject PASS ({total}/{total})")
        return 0

    runs: dict[int, tuple[int, str]] = {}
    snaps: dict[int, dict] = {}
    for case in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        rc_build = build_image(case)
        if rc_build != 0:
            print(f"k3_page_probe: FAIL: case {case} build rc={rc_build}",
                  file=sys.stderr)
            return 1
        rc, text = boot(f"case{case}")
        runs[case] = (rc, text)
        snaps[case] = {"config": config_text(),
                       "syms": k1boot.symbols(kernel_path())}

    if args.selfcheck:
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                for case in runs:
                    judge(case, *runs[case], snaps[case], rep)
            except SystemExit as exc:
                print(f"k3_page_probe: FAIL: {exc}", file=sys.stderr)
                return 1
        if rep.fails:
            print("k3_page_probe: FAIL: the captured runs are not green: "
                  f"{rep.fails[0]}", file=sys.stderr)
            return 1
        print("[INFO] 捕获的五次运行全绿；逐组变异：", flush=True)
        problems: list[str] = []
        return run_selfcheck(runs, snaps, problems)

    rep = Report()
    try:
        for case in runs:
            judge(case, *runs[case], snaps[case], rep)
    except SystemExit as exc:
        print(f"k3_page_probe: FAIL: {exc}", file=sys.stderr)
        return 1
    print("================================================================")
    if rep.fails:
        for msg in rep.fails:
            print(f"  [FAIL] {msg}", file=sys.stderr)
        print(f"k3_page_probe: FAIL ({len(rep.fails)}/{rep.total})",
              file=sys.stderr)
        return 1
    print(f"k3_page_probe: PASS ({rep.total}/{rep.total})  {rep.summary()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
