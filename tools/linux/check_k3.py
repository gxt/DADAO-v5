#!/usr/bin/env python3
"""check_k3.py — M14 K3 closure gate (`make check-linux-k3`; `m14-linux-015`).

K3 turned the kernel into one that owns its address space: the page-table
primitives (`pmd_populate*`, the TLB invalidation commands, the ASID register),
the page-fault channel (CFXMEM/CFXPERM + the sub-reason wyde of
`contract-see §6.1.1`) and the shared zero page.  The K3 probes judge those one
capability at a time; this gate asks the *stage* question — "does the K3 image
the milestone delivers still meet every exit criterion, end to end?" — and it is
the one place a criterion can be retired from an earlier stage (§4a of
``docs/Process-07``).

Groups (the group letter is what ``--selfcheck``/``--inject`` flip):

  B  build & configuration: the image is the K3 image the gate asked for
     (``.config`` parsed live), its page size equals the *contract* page size
     (never a literal "64 KiB"), the earlier milestones' early stops are off,
     the K3 self-test symbols belong to this image only, build rc = 0, and the
     command line carries no per-instruction logging.
  M  page-table primitives (m14-linux-011): the L1 entry `pmd_populate*()`
     builds is P = 1, SP = 0, SPF = 0, G = 0 with PPN == the L2 table's **PA**
     (not its VA); every command value the kernel prints is rebuilt here from
     ``spec/DADAO-12 §4.5``'s bit fields and must match exactly; the ASID
     register reads back `[63:16] == 0`.
  F  fault channel (m14-linux-012): a missing page is handled, retried and the
     second access does not re-enter the channel; no window ⇒ named
     termination; ADWBFAIL ⇒ no allocation and no retry; the sub-reason table
     is compared against ``contract-see §6.1.1`` bit by bit (including "every
     other class carries nothing above [15:0]"); the class is resolved by
     ``cause & 0xffff`` (a sub-reason-carrying id is still named).
  C  zero page (`P8`–`P10`): a read fault maps the shared zero page read-only,
     a write fault replaces it with a private page, and the zero page itself is
     never written.  (Non-zero-page COW moved to K4 with `m14-linux-013`; the
     stack-growth group left with `m14-linux-014` — neither is in this gate.)
     §4a (m14-linux-016): the *boundary* of the F/C groups moved.  The channel's
     page source is `alloc_page()` since K4, so the cases run at the K4 boundary
     (after `mm_core_init()`, before `rest_init()`) instead of at the end of
     `setup_arch()`; the cases themselves are unchanged and the assertions below
     are still the same ones.  The zero page is the canonical `ZERO_PAGE(0)`
     from K4 on, which is why the group still compares *its* PA rather than an
     allocated one.
  T  TLB, kernel side (the m14-linux-011 probe): fill/hit (a changed PTE stays
     invisible until an explicit invalidation), `invalid`+VA/`range` (and an
     empty range leaving the entry alone), `clean` (A/D back, entry kept),
     `flush` (A/D back, entry dropped), `ASID_ANY = 0` leaving `G = 1` alone
     and `= 1` reaching it, and writing PTBR/ASID/`ptw_enable` not invalidating.
     The **hardware** side of the TLB is judged by L3 ``make check-arch``
     (``docs/Process-07 §4``: one check, one layer); this gate only reconciles
     it statically: ``ARCH_CFX_PROBES`` carries the TLB probe, the carrier and
     ``tests/arch/ptw/expected.yaml`` agree with each other and with the
     contract tables, and no expectation is a bare number.
  X  exit codes and quiescence: the positive images exit with §7.1's PASS value;
     every K3 self-check constant is inside the guest segment; a named
     termination lands in the monitor segment at ``0xC0 | supv << 4 | bit``
     (supv ⇒ ``0xE0 | bit``) — segments, mode encoding and bit indices are
     parsed out of ``spec/Kaiwu §7.1``, no code is spelled here; the output has
     no ``panic``/``unknown cause`` and no second initialisation.
  R  reverse assertions: the channel-entry deltas equal the case design (no
     silent extra entry), the retry budget was never reached, the page
     allocation deltas match the case, and the §4a retirement is still in force
     (the new wording is there, the retired wording is gone, and the doc records
     which new group took the criterion over).

Nothing below restates an expectation; every one is derived from its owner:

  * page geometry, L1 field positions        -> ``spec/DADAO-12 §2.2.2/§2.2.3``
  * `tlb_control` op/scope/ASID_ANY encoding -> ``spec/DADAO-12 §4.5`` (the
    register row *and* the "失效接口" bullets), cross-checked against
    ``contract-tlb`` TLB-19/TLB-29 — both parsed live, neither restated
  * op semantics (which op deletes, which writes A/D back) -> ``§4.5`` bullets
  * ASID width and `[63:16]`                 -> ``§4.5`` and ``contract-tlb``
    TLB-04 (the two must agree)
  * sub-reason bits / wyde placement         -> ``contract-see §6.1/§6.1.1``
    against the kernel's own ``asm/cause-sub.h``
  * cause table                              -> ``spec/DADAO-13 §2``
  * exit-code segments/modes/indices         -> ``spec/Kaiwu §7.1``
  * page size / page shift the image has     -> that image's ``.config``
  * self-check constants                     -> the K3 self-test sources
  * data markers, retry budget               -> the kernel sources
  * TLB probe case list                      -> ``tests/arch/ptw/expected.yaml``
    + ``tools/testcases/arch/min_rom_probe_tlb.py`` (its ``--selfcheck``)

Images (each pins every milestone boundary: the build tree is shared, so no
image may inherit whichever gate configured it last):

  pt   ``CONFIG_DADAO_K3_PT_SELFTEST=y``  page table / TLB primitives  -> SYS_EXIT(0)
  pf1  ``CONFIG_DADAO_K3_PF_SELFTEST=1``  the recoverable channel, the
       zero page and every missing class                            -> SYS_EXIT(0)
  pf4  ``CONFIG_DADAO_K3_PF_SELFTEST=4``  a data access outside every window
       (named termination)                                          -> monitor code
  pf5  ``CONFIG_DADAO_K3_PF_SELFTEST=5``  the ADWBFAIL dispatch     -> monitor code

Representative cases only (one or two per class); the full case sweep stays in
``k3_page_probe.py`` (user ruling 2026-11-16, task book 「待裁定」 3).

``--selfcheck`` mutates the captured runs / the captured ``.config`` and shows
that *every* group flips.  ``--inject`` corrupts a source, rebuilds, asserts the
named groups go red, restores with ``cp`` + md5 and proves the image is green
again — one path per capability, plus the static "retired wording comes back".

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
from tools.linux import k2_trap_probe as k2trap         # noqa: E402  (§7.1, §2)
from tools.linux import k3_page_probe as k3pf           # noqa: E402  (channel parsers)
from tools.linux import k3_pt_probe as k3pt             # noqa: E402  (§2.2.x parsers)
from tools.linux import make_defconfig as defconfig     # noqa: E402  (config slice)
from tools.linux import paths as linux_paths            # noqa: E402
from tools.qemu import k0_boot_probe as k0              # noqa: E402  (firmware, ABI)

TIMEOUT_QEMU = int(os.environ.get("K3G_QEMU_TIMEOUT", "180"))
TIMEOUT_BUILD = int(os.environ.get("K3G_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K3G_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-015") / "check-linux-k3")

SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
CONTRACT_TLB = _REPO / ".tao" / "contracts" / "contract-tlb.md"
CONTRACT_SEE = _REPO / ".tao" / "contracts" / "contract-see.md"
PROCESS_07 = _REPO / "docs" / "Process-07-门控分层规范.md"
MAKEFILE = _REPO / "Makefile"
EXPECTED_YAML = _REPO / "tests" / "arch" / "ptw" / "expected.yaml"
TLB_PROBE = _REPO / "tools" / "testcases" / "arch" / "min_rom_probe_tlb.py"
SOURCE = linux_paths.linux_source_dir()

GROUPS = "BMFCTXR"

#: The images this gate builds: every milestone symbol is pinned in every image
#: (`make check-config-pins`, ISS-470), the per-image K3 probe value comes from
#: `IMAGE_PINS`.  `CONFIG_PINS` is the K3 image with both K3 probes off.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    # int symbols whose `depends on` is not met are "left unset": Kconfig has no
    # `n` value for them and drops them from .config (see tools/linux/config_pins.py).
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    # m14-linux-017/019: the stack-growth probe is an int too; pin it
    # so no image inherits another gate's case (F30 class, twice seen).
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    # m14-linux-018: the copy-on-write probe is an int with no `depends on`,
    # so it has no "unset" spelling: pin the concrete 0.
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    # m14-linux-016: the K3 page-fault cases moved to the K4 boundary (their
    # page source is the buddy allocator now), so the K3 images must reach it —
    # and must not also carry the K4 self-test.
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
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
}

#: Per-image overrides: the K3 probe this image runs (the other one stays off).
IMAGE_PINS = {
    "pt": {"CONFIG_DADAO_K3_PT_SELFTEST": "y"},
    "pf1": {"CONFIG_DADAO_K3_PF_SELFTEST": "1"},
    "pf4": {"CONFIG_DADAO_K3_PF_SELFTEST": "4"},
    "pf5": {"CONFIG_DADAO_K3_PF_SELFTEST": "5"},
}

IMAGES = {name: config_pins.config_lines(CONFIG_PINS, IMAGE_PINS[name])
          for name in ("pt", "pf1", "pf4", "pf5")}

#: Symbols this image must carry as ``SYMBOL=value`` (exact line).
IMAGE_ON = {
    "pt": {"CONFIG_DADAO_K3_PT_SELFTEST": "y"},
    "pf1": {"CONFIG_DADAO_K3_PF_SELFTEST": "1"},
    "pf4": {"CONFIG_DADAO_K3_PF_SELFTEST": "4"},
    "pf5": {"CONFIG_DADAO_K3_PF_SELFTEST": "5"},
}

#: Symbols that must be *off* in this image (no ``SYMBOL=y`` / ``=1`` line).
IMAGE_OFF = {
    "pt": ("CONFIG_DADAO_K3_PF_SELFTEST",),
    "pf1": ("CONFIG_DADAO_K3_PT_SELFTEST",),
    "pf4": ("CONFIG_DADAO_K3_PT_SELFTEST",),
    "pf5": ("CONFIG_DADAO_K3_PT_SELFTEST",),
}

#: Every image: the page-size symbol plus the earlier milestones' early stops.
ALWAYS_ON = {"CONFIG_PAGE_SIZE_64KB": "y"}
ALWAYS_OFF = ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP",
              "CONFIG_DADAO_K2_TIME_STOP", "CONFIG_DADAO_K4_SELFTEST")

#: (must be present, must be absent) — the K3 self-test symbols of *this* image.
IMAGE_SYMBOLS = {
    "pt": (("dadao_k3_pt_selftest",), ("dadao_k3_pf_selftest",)),
    "pf1": (("dadao_k3_pf_selftest", "dadao_do_page_fault"),
            ("dadao_k3_pt_selftest",)),
    "pf4": (("dadao_k3_pf_selftest", "dadao_do_page_fault"),
            ("dadao_k3_pt_selftest",)),
    "pf5": (("dadao_k3_pf_selftest", "dadao_do_page_fault"),
            ("dadao_k3_pt_selftest",)),
}

#: Images that are supposed to end in a named termination (monitor segment).
TERMINATING = {"pf4", "pf5"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus live ``[STAT]``.

    ``<id>`` starts with the group letter (``B``/``M``/``F``/``C``/``T``/``X``/
    ``R``); the per-group tally printed at the end is what the task means by
    "PASS 数 == 总项数, 每组现场计数".
    """

    def __init__(self, quiet: bool = False) -> None:
        self.total = 0
        self.fails: list[str] = []
        self.groups: dict[str, list[int]] = {}
        self.quiet = quiet

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        tally = self.groups.setdefault(cid[0], [0, 0])
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
        parts = []
        for group in GROUPS:
            if group in self.groups:
                total, failed = self.groups[group]
                parts.append(f"{group} {total - failed}/{total}")
        return "  ".join(parts)


def _section(path: Path, start: str, end: str, what: str) -> str:
    text = path.read_text(encoding="utf-8")
    cut = text.split(start, 1)
    if len(cut) != 2:
        raise SystemExit(f"check_k3: '{start}' not found in {what}")
    return cut[1].split(end, 1)[0]


def kv(line: str) -> dict[str, str]:
    return dict(re.findall(r"(\w+)=(\S+)", line))


def num(text, default: int = -1) -> int:
    try:
        return int(str(text), 0)
    except (TypeError, ValueError):
        return default


def lines_matching(text: str, pattern: str) -> list[str]:
    return [line for line in text.splitlines() if re.search(pattern, line)]


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    """``True`` for ``SYMBOL=y`` / ``SYMBOL=1`` — "is this feature on here?"."""
    return config_value(config, symbol) in ("y", "1")


# ---------------------------------------------------------------------------
# expectations parsed from spec / contract (never restated)
# ---------------------------------------------------------------------------

def spec_l1_fields() -> dict[str, tuple[int, int]]:
    """``{field: (low, high)}`` of the L1 entry (``spec/DADAO-12 §2.2.3``)."""
    return k3pt.spec_l1_fields()


def spec_page_geometry() -> tuple[int, int]:
    """``(page_offset_bits, entries_per_level)`` (``spec/DADAO-12 §2.2.2``)."""
    return k3pt.spec_normal_page()


def spec_tlb_control() -> dict:
    """The three dimensions of `cfx_ptw_tlb_control` (`spec/DADAO-12 §4.5`).

    Read out of the register row: the field positions come from the `[hi:lo]`
    spans, the values from the `NN=name` list — no shift and no opcode is
    spelled in this file.
    """
    body = _section(SPEC_DADAO12, "### 4.5", "\n### ", "spec/DADAO-12 §4.5")
    row = next((line for line in body.splitlines()
                if "cfx_ptw_tlb_control" in line and line.startswith("|")), None)
    if row is None:
        raise SystemExit("check_k3: §4.5 has no cfx_ptw_tlb_control row")

    m = re.search(r"`\[(\d+):(\d+)\]`\s*操作\s*=\s*(.+?)；", row)
    if not m:
        raise SystemExit("check_k3: §4.5 op field not parsed")
    op_high, op_low, op_text = int(m.group(1)), int(m.group(2)), m.group(3)

    m = re.search(r"`\[(\d+):(\d+)\]`\s*地址范围\s*=\s*(.+?)；", row)
    if not m:
        raise SystemExit("check_k3: §4.5 scope field not parsed")
    scope_high, scope_low, scope_text = int(m.group(1)), int(m.group(2)), m.group(3)

    m = re.search(r"`bit(\d+)\s*=\s*ASID_ANY`", row)
    if not m:
        raise SystemExit("check_k3: §4.5 has no ASID_ANY bit")
    asid_any_bit = int(m.group(1))

    # The spec spells the scope `VA`; the kernel and the probes use the lower
    # case name, so the parsed keys are normalised here (not in the checks).
    ops = {name: int(bits, 2) for bits, name in re.findall(r"(\d\d)=(\w+)", op_text)}
    scopes = {name.lower(): int(bits, 2) for bits, name in
              re.findall(r"(\d\d)=(\w+)", scope_text)}
    if set(ops) != {"none", "clean", "invalid", "flush"}:
        raise SystemExit(f"check_k3: §4.5 ops parsed as {sorted(ops)}")
    if not {"all", "va", "range"} <= set(scopes):
        raise SystemExit(f"check_k3: §4.5 scopes parsed as {sorted(scopes)}")
    if sorted(ops.values()) != [0, 1, 2, 3]:
        raise SystemExit(f"check_k3: §4.5 op values are not 00..11: {ops}")
    return {"op": ops, "scope": scopes, "op_low": op_low, "op_bits": op_high - op_low + 1,
            "scope_low": scope_low, "scope_bits": scope_high - scope_low + 1,
            "asid_any_bit": asid_any_bit, "doc": "spec/DADAO-12 §4.5"}


def contract_tlb_control() -> dict:
    """The same three dimensions out of ``contract-tlb`` TLB-19."""
    text = CONTRACT_TLB.read_text(encoding="utf-8")
    m = re.search(r"TLB-19 \*\*编码\*\*：(.+)", text)
    if not m:
        raise SystemExit("check_k3: contract-tlb TLB-19 not found")
    line = m.group(1)
    op = re.search(r"`\[(\d+):(\d+)\]`\s*操作\s*=\s*(.+?)；", line)
    scope = re.search(r"`\[(\d+):(\d+)\]`\s*地址范围\s*=\s*(.+?)；", line)
    any_bit = re.search(r"`bit(\d+)\s*=\s*ASID_ANY`", line)
    if not op or not scope or not any_bit:
        raise SystemExit("check_k3: contract-tlb TLB-19 dimensions not parsed")
    return {
        "op": {name: int(bits, 2)
               for bits, name in re.findall(r"(\d\d)=(\w+)", op.group(3))},
        "scope": {name.lower(): int(bits, 2)
                  for bits, name in re.findall(r"(\d\d)=(\w+)", scope.group(3))},
        "op_low": int(op.group(2)), "scope_low": int(scope.group(2)),
        "asid_any_bit": int(any_bit.group(1)), "doc": "contract-tlb TLB-19",
    }


def spec_op_semantics() -> dict:
    """``{op: {"deletes": bool, "writes_ad": bool}}`` from §4.5's bullets.

    The spec spells it as ``01 = clean``：回写 A/D，保留条目。``10 = invalid``：
    只删除条目，不回写。…``11 = flush``：回写 A/D 后删除条目.  A "不回写" is the
    opposite of a write-back, so the negative form is excluded explicitly.
    """
    body = _section(SPEC_DADAO12, "### 4.5", "\n### ", "spec/DADAO-12 §4.5")
    out: dict[str, dict] = {}
    for digit, name in (("00", "none"), ("01", "clean"), ("10", "invalid"),
                        ("11", "flush")):
        m = re.search(rf"`{digit} = {name}`：(.+?)。", body)
        if not m:
            raise SystemExit(f"check_k3: §4.5 has no semantics for {name}")
        text = m.group(1)
        out[name] = {"deletes": "删除条目" in text,
                     "writes_ad": bool(re.search(r"(?<!不)回写", text))}
    if not out["invalid"]["deletes"] or out["clean"]["deletes"]:
        raise SystemExit(f"check_k3: §4.5 op semantics parsed as {out}")
    return out


def spec_asid() -> dict:
    """``(width, high_bit)`` of `cfx_ptw_tlb_asid` from §4.5's register row."""
    body = _section(SPEC_DADAO12, "### 4.5", "\n### ", "spec/DADAO-12 §4.5")
    row = next((line for line in body.splitlines()
                if "cfx_ptw_tlb_asid" in line and line.startswith("|")), None)
    if row is None:
        raise SystemExit("check_k3: §4.5 has no cfx_ptw_tlb_asid row")
    low = re.search(r"`\[(\d+):0\]`", row)
    high = re.search(r"`\[63:(\d+)\]`\s*读 0", row)
    if not low or not high:
        raise SystemExit("check_k3: §4.5 ASID width not parsed")
    return {"width": int(low.group(1)) + 1, "high_from": int(high.group(1)),
            "doc": "spec/DADAO-12 §4.5"}


def contract_asid() -> dict:
    """The same width out of ``contract-tlb`` TLB-04."""
    text = CONTRACT_TLB.read_text(encoding="utf-8")
    m = re.search(r"`cfx_ptw_tlb_asid` 为 `cg12 rc1`（`\[(\d+):0\]`[^。]*?"
                  r"`\[63:(\d+)\]` 读 0", text)
    if not m:
        raise SystemExit("check_k3: contract-tlb TLB-04 ASID width not found")
    return {"width": int(m.group(1)) + 1, "high_from": int(m.group(2)),
            "doc": "contract-tlb TLB-04"}


def spec_no_implicit_invalidate() -> dict:
    """Which registers §4.5 says must not invalidate the TLB implicitly."""
    body = _section(SPEC_DADAO12, "### 4.5", "\n### ", "spec/DADAO-12 §4.5")
    sentence = next((line for line in body.splitlines()
                     if "不隐含 TLB 失效" in line), None)
    if sentence is None:
        raise SystemExit("check_k3: §4.5 has no '不隐含 TLB 失效' sentence")
    return {"PTBR": "PTBR" in sentence, "ASID": "ASID" in sentence,
            "ptw_enable": "ptw_enable" in sentence,
            "doc": "spec/DADAO-12 §4.5"}


def contract_subcauses() -> dict[str, dict]:
    """``{name: {bit, wyde, cause}}`` from ``contract-see §6.1.1``."""
    return k3pf.contract_subcauses()


def kernel_subcauses() -> dict[str, int]:
    """``{NAME: bit}`` from the kernel's own ``asm/cause-sub.h``."""
    return k3pf.header_subcauses()


def kernel_shifts() -> tuple[int, int]:
    """``(perm_shift, mem_shift)`` the kernel uses, from ``cause-sub.h``."""
    shifts = k3pf.header_shifts()
    return shifts["PERM_SHIFT"], shifts["MEM_SHIFT"]


def kernel_reserved() -> dict[str, int]:
    """The kernel's reserved-bit masks (`[63:58]/[47:40]/[31:16]`)."""
    return k3pf.header_reserved()


def contract_reserved() -> set[tuple[int, int]]:
    """The reserved ranges of ``contract-see §6.1``."""
    return k3pf.contract_reserved()


def cause_table() -> dict[str, int]:
    """``{name: one-hot id}`` from ``spec/DADAO-13 §2``."""
    return k3pf.causes()


def exit_segments() -> dict:
    """Segments / mode encoding / bit indices of ``spec/Kaiwu §7.1``."""
    return k2trap.spec_exit_segments()


def monitor_code(specs: dict, mode: str, cause: str) -> int:
    low, _high = specs["ranges"]["monitor"]
    return low | (specs["modes"][mode] << 4) | specs["indices"][cause]


def kernel_marks() -> dict[str, int]:
    """The K3 data-page markers, from the self-test source."""
    return k3pt.kernel_marks()


def k3_selfcheck_codes() -> dict[str, int]:
    """Every ``*FAIL*`` constant the K3 self-test sources define.

    The files are discovered (``arch/dadao/mm/k3_*_selftest.c``) so a new probe
    file cannot land a self-check code outside the scanned set; an empty scan is
    a FAIL, never a vacuous pass.
    """
    directory = SOURCE / "arch/dadao/mm"
    files = sorted(directory.glob("k3_*_selftest.c"))
    if not files:
        raise SystemExit(f"check_k3: no K3 self-test source under {directory}")
    pattern = re.compile(r"^#define\s+(K3\w*FAIL\w*)\s+(0x[0-9a-fA-F]+|\d+)",
                         re.MULTILINE)
    codes: dict[str, int] = {}
    for path in files:
        for name, value in pattern.findall(path.read_text(encoding="utf-8")):
            codes[f"{path.name}:{name}"] = int(value, 0)
    return codes


def retry_budget() -> int:
    """The handler's retry budget, from the kernel source."""
    text = (SOURCE / "arch/dadao/mm/fault.c").read_text(encoding="utf-8")
    m = re.search(r"^#define\s+DADAO_PF_RETRY_BUDGET\s+(\d+)", text, re.MULTILINE)
    if not m:
        raise SystemExit("check_k3: fault.c has no DADAO_PF_RETRY_BUDGET")
    return int(m.group(1))


def layout_case_names() -> list[str]:
    """The sub-reason shape cases the pf self-test declares (``ids[]``)."""
    text = (SOURCE / "arch/dadao/mm/k3_pf_selftest.c").read_text(encoding="utf-8")
    cut = text.split("static void __init k3_pf_layout(void)", 1)
    if len(cut) != 2:
        raise SystemExit("check_k3: k3_pf_selftest.c has no k3_pf_layout()")
    body = cut[1].split("};", 1)[0]
    names = re.findall(r'\{\s*"(\w+)",', body)
    if not names:
        raise SystemExit("check_k3: k3_pf_layout() declares no case")
    return names


def abi() -> dict:
    k0.load_contract()
    if not k0.ABI or not k0.BOOT_INFO:
        raise SystemExit("check_k3: the boot contract projection is empty")
    return k0.ABI


def derivations(snap: dict) -> dict:
    """Everything the checks compare against (each value has an owner)."""
    specs = exit_segments()
    encoding = spec_tlb_control()
    contract_enc = contract_tlb_control()
    off_bits, per_level = spec_page_geometry()
    shift = num(config_value(snap["config"], "CONFIG_PAGE_SHIFT"))
    if shift < 0:
        raise SystemExit("check_k3: the image's .config has no CONFIG_PAGE_SHIFT")
    return {
        "abi": abi(),
        "specs": specs,
        "encoding": encoding,
        "contract_encoding": contract_enc,
        "op_semantics": spec_op_semantics(),
        "asid": spec_asid(),
        "contract_asid": contract_asid(),
        "no_implicit": spec_no_implicit_invalidate(),
        "subs": contract_subcauses(),
        "header": kernel_subcauses(),
        "shifts": kernel_shifts(),
        "reserved": kernel_reserved(),
        "contract_reserved": contract_reserved(),
        "causes": cause_table(),
        "marks": kernel_marks(),
        "pf": k3pf.kernel_consts(),
        "codes": k3_selfcheck_codes(),
        "retry_budget": retry_budget(),
        "l1": spec_l1_fields(),
        "page_offset_bits": off_bits,
        "entries_per_level": per_level,
        "page_shift": shift,
        "page_size": 1 << shift,
    }


def sub_id(d: dict, name: str) -> int:
    """``class | 1 << bit`` of a sub-reason — the raw id the machine raises."""
    row = d["subs"][name]
    return d["causes"][row["cause"]] | (1 << row["bit"])


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def build_image(image: str) -> tuple[int, dict | None]:
    """Configure and build @image; returns (rc, snapshot of *this* image)."""
    rc = defconfig.apply_config_lines(IMAGES[image])
    if rc != 0:
        print(f"check_k3: FAIL: config slice for {image} rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {image} image (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    kernel = kernel_path()
    # The build tree is shared: the .config and the symbol table belong to
    # *this* image, so snapshot them before the next image overwrites them.
    snap = {
        "config": (build_dir() / ".config").read_text(encoding="utf-8"),
        "syms": k1boot.symbols(kernel),
        "kernel": kernel,
        "kernel_size": k1boot.kernel_size_from_elf(kernel, abi()["entry_va"]),
    }
    return 0, snap


def firmware() -> str:
    abi()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k0_k3.bin")


def boot(tag: str, rom: str, qemu: str) -> tuple[int, str, list[str]]:
    """Boot the current image on Vast; returns (guest rc, console, argv)."""
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"check_k3: {kernel} missing; run `make linux-vmlinux`")
    log = SCRATCH / "log" / f"{tag}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [qemu,
           "-machine", f"kaiwu-vast,bootrom-image={rom}",
           "-nographic",
           "-semihosting-config", "enable=on,target=native",
           "-kernel", str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        # A run that never returns is an observation: keep what it printed and
        # report 124, the same convention as the other Linux gates.
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = err or out
    log.write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# B: the image under test is the K3 image the gate asked for
# ---------------------------------------------------------------------------

def check_build(rep: Report, image: str, rc_build: int, snap: dict | None,
                cmd: list[str] | None, text: str) -> None:
    rep.check("B0", f"{image} 镜像可构建", 0, rc_build)
    if snap is None:
        # A build that never produced an image cannot satisfy any other B
        # check; report them as red instead of silently skipping.
        for name in ("配置行", "页大小 == 契约值", "自检符号按镜像"):
            rep.check("B1", f"{image} {name}（镜像缺失）", "可检查", "镜像未构建")
        return

    config = snap["config"]
    for symbol, value in {**ALWAYS_ON, **IMAGE_ON[image]}.items():
        line = f"{symbol}={value}"
        rep.check("B1", f"{image} 镜像配置：{line}", line,
                  next((ln for ln in config.splitlines()
                        if ln.startswith(symbol + "=")), "<unset>"))
    off = list(ALWAYS_OFF) + list(IMAGE_OFF[image])
    rep.check("B1", f"{image} 镜像配置：{len(off)} 个边界符号未开", [],
              [f"{symbol}={config_value(config, symbol)}" for symbol in off
               if config_enabled(config, symbol)])

    # The page size is the contract's, not a literal: `.config` is the only
    # place the image states it, and §2.2.2 fixes the geometry.
    context = derivations(snap)
    rep.check("B2", f"{image} 页大小（1 << CONFIG_PAGE_SHIFT）== 契约 page_size",
              context["abi"]["page_size"], context["page_size"])
    rep.check("B2", f"{image} CONFIG_PAGE_SHIFT == spec §2.2.2 页内偏移位宽",
              context["page_offset_bits"], context["page_shift"])

    rep.check("B3", f"{image} 命令行无 -d/-D（不用逐指令日志）", True,
              bool(cmd) and "-d" not in cmd and "-D" not in cmd)
    # ... and the console really carries no per-instruction dump: with `-d in_asm`
    # QEMU prints `IN:` blocks, with `-d exec` it prints `Trace N:` lines.
    rep.check("B3", f"{image} 输出无逐指令转储标记（IN:/Trace）", [],
              lines_matching(text, r"^IN: |^Trace \d+:"))

    present, absent = IMAGE_SYMBOLS[image]
    rep.check("B4", f"{image} 自检符号齐全", sorted(present),
              sorted(name for name in present if name in snap["syms"]))
    rep.check("B4", f"{image} 不含邻镜像的自检符号", [],
              sorted(name for name in absent if name in snap["syms"]))

    rep.check("B5", f"{image} 输出无 panic/oops/BUG/Call Trace", [],
              lines_matching(text, r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|"
                                   r"Call Trace)"))
    if image not in TERMINATING:
        rep.check("B5", f"{image} 输出无具名终止（dadao: 行）", [],
                  lines_matching(text, r"^dadao: "))
        rep.check("B5", f"{image} 输出无自检失败行", [],
                  lines_matching(text, r"^K3 p[ft] FAIL: "))
    rep.stat(f"{image}: kernel={snap['kernel'].name} "
             f"{snap['kernel'].stat().st_size} B kernel_size="
             f"{hex(snap['kernel_size'])} page_size={context['page_size']:#x}")


# ---------------------------------------------------------------------------
# M: page-table primitives (L1 entry, TLB commands, ASID register)
# ---------------------------------------------------------------------------

def check_primitives(rep: Report, text: str, d: dict) -> None:
    fields = d["l1"]
    enc = d["encoding"]
    page_shift = d["page_shift"]
    per_level = d["entries_per_level"]
    ppn_low, ppn_high = fields["PPN"]
    ppn_mask = ((1 << (ppn_high - ppn_low + 1)) - 1) << ppn_low
    spf_mask = ((1 << (fields["SPF"][1] - fields["SPF"][0] + 1)) - 1) << \
        fields["SPF"][0]

    pages = k3pt.one(text, "K3 pt pages ")
    alloc = k3pt.one(text, "K3 pt alloc ")
    l2_pa = int(pages["l2_pa"], 0)
    va = int(pages["va"], 0)
    entry = int(alloc["pte"], 0)
    pgdir_shift = page_shift + per_level

    rep.check("M1", "L1 索引 == pgd_index(va)（spec §2.2.1 的 VA 拆分）",
              (va >> pgdir_shift) & ((1 << per_level) - 1),
              int(alloc["l1"], 0))
    rep.check("M2", "L1 表项 P = 1", 1, (entry >> fields["P"][0]) & 1)
    rep.check("M2", "L1 表项 SP = 0（指向下一级表）", 0,
              (entry >> fields["SP"][0]) & 1)
    rep.check("M2", "L1 表项 SPF == 0（非叶子不使用 §2.2.3）", 0,
              (entry & spf_mask) >> fields["SPF"][0])
    rep.check("M2", "L1 表项 G == 0（非叶子不使用 §2.2.3）", 0,
              (entry >> fields["G"][0]) & 1)
    rep.check("M3", "L1 表项 PPN == L2 表的 PA",
              (l2_pa & ppn_mask) >> ppn_low, (entry & ppn_mask) >> ppn_low)
    table_va = l2_pa + d["abi"]["va_pa_offset"]
    rep.check("M3", "L1 表项 PPN != 表的 VA（VA = PA + 契约 va_pa_offset）", True,
              ((entry & ppn_mask) >> ppn_low) !=
              ((table_va & ppn_mask) >> ppn_low))
    walk = k3pt.one(text, "K3 pt alloc-walk ")
    rep.check("M3", "步进 L1 表项落到 L2 表页",
              l2_pa + ((va >> page_shift) & ((1 << per_level) - 1)) * 8,
              int(walk["ptep_pa"], 0))

    def command(op: str, scope: str, asid_any: bool) -> int:
        """The value §4.5 says (op, scope, ASID_ANY) writes."""
        return (((enc["op"][op] & ((1 << enc["op_bits"]) - 1)) << enc["op_low"]) |
                ((enc["scope"][scope] & ((1 << enc["scope_bits"]) - 1))
                 << enc["scope_low"]) |
                ((1 << enc["asid_any_bit"]) if asid_any else 0))

    inval = k3pt.one(text, "K3 pt inval_va ")
    rep.check("M4", "inval_va 命令值 == §4.5 重建的 invalid|VA|ASID_ANY=1",
              hex(command("invalid", "va", True)), hex(int(inval["cmd"], 0)))

    clean = k3pt.one(text, "K3 pt ad_clean ")
    rep.check("M4", "ad_clean 命令值 == §4.5 重建的 clean|VA|ASID_ANY=1",
              hex(command("clean", "va", True)), hex(int(clean["cmd"], 0)))

    flush = k3pt.one(text, "K3 pt flush ")
    rep.check("M4", "flush 命令值 == §4.5 重建的 flush|all|ASID_ANY=1",
              hex(command("flush", "all", True)), hex(int(flush["cmd"], 0)))

    # The whole (op, scope) matrix: the expected op/scope come from the line's
    # own name, so a renamed or missing combination cannot pass unnoticed.
    matrix = k3pt.lines_of(text, "K3 pt m_")
    rep.check("M4", "矩阵覆盖 §4.5 的全部 op×scope 组合（现场派生）",
              sorted(f"m_{op}_{scope}" for op in enc["op"]
                     for scope in ("all", "va", "range")),
              sorted(matrix))
    for name, row in sorted(matrix.items()):
        _m, op, scope = name.split("_")
        if op not in enc["op"] or scope not in enc["scope"]:
            rep.check("M4", f"{name} 的 op/scope 名在 §4.5 里存在", True, False)
            continue
        rep.check("M4", f"{name} 命令值 == §4.5 重建",
                  hex(command(op, scope, True)), hex(int(row["cmd"], 0)))

    asid = k3pt.one(text, "K3 pt asid ")
    width = d["asid"]["width"]
    rep.check("M4", "asid 命令值 == §4.5 重建的 invalid|all|ASID_ANY=0",
              hex(command("invalid", "all", False)), hex(int(asid["cmd0"], 0)))
    asid_g = k3pt.one(text, "K3 pt asid_g ")
    rep.check("M4", "asid_g 命令值 == §4.5 重建的 invalid|all|ASID_ANY=0",
              hex(command("invalid", "all", False)), hex(int(asid_g["cmd0"], 0)))
    rep.check("M4", "asid_g 命令值 == §4.5 重建的 invalid|all|ASID_ANY=1",
              hex(command("invalid", "all", True)), hex(int(asid_g["cmd1"], 0)))

    # The two authorities must agree: §4.5 is the machine's own register row,
    # contract-tlb is the normative encoding.  A drift between them is a red.
    contract_enc = d["contract_encoding"]
    rep.check("M6", "§4.5 的 op 编码 == contract-tlb TLB-19", enc["op"],
              contract_enc["op"])
    rep.check("M6", "§4.5 的 scope 编码 == contract-tlb TLB-19", enc["scope"],
              contract_enc["scope"])
    rep.check("M6", "§4.5 的位位置（op/scope/ASID_ANY）== TLB-19",
              [enc["op_low"], enc["scope_low"], enc["asid_any_bit"]],
              [contract_enc["op_low"], contract_enc["scope_low"],
               contract_enc["asid_any_bit"]])

    raw = int(asid["raw"], 0)
    rep.check("M5", f"ASID 寄存器宽 {width} 位：写入宽值被截到全 1",
              (1 << width) - 1, raw)
    rep.check("M5", "§4.5 的 ASID 位宽/高位读 0 == contract-tlb TLB-04",
              [d["asid"]["width"], d["asid"]["high_from"]],
              [d["contract_asid"]["width"], d["contract_asid"]["high_from"]])
    rep.check("M5", "ASID 读回 [63:%d] == 0（§4.5 / TLB-04）" % width, 0,
              raw >> width)
    rep.check("M5", "ASID 读回 == 写入值（截断后）", (1 << width) - 1,
              int(asid["read"], 0))
    first, second = (int(v, 0) for v in asid["alloc"].split(","))
    rep.check("M5", "ASID 分配器从不发 0（内核保留）", 0,
              int(first == 0) + int(second == 0))
    rep.check("M5", "两个地址空间的 ASID 不同", 1, int(first != second))
    rep.check("M5", "init_new_context 写入了非 0 ASID", 1,
              int(int(asid["mm_asid"], 0) != 0))
    rep.stat(f"§4.5 编码：op {enc['op']} @[{enc['op_low']}+{enc['op_bits']}] "
             f"scope {enc['scope']} @[{enc['scope_low']}+{enc['scope_bits']}] "
             f"ASID_ANY @bit{enc['asid_any_bit']}；ASID {width} 位")


# ---------------------------------------------------------------------------
# T: TLB, kernel side (the m14-linux-011 probe) + the static reconciliation
# ---------------------------------------------------------------------------

def check_tlb(rep: Report, text: str, d: dict) -> None:
    marks = d["marks"]
    sem = d["op_semantics"]
    pages = k3pt.one(text, "K3 pt pages ")
    ppn_low, ppn_high = d["l1"]["PPN"]
    ppn_mask = ((1 << (ppn_high - ppn_low + 1)) - 1) << ppn_low
    y_ppn = (int(pages["y_pa"], 0) & ppn_mask) >> ppn_low

    m_map = k3pt.one(text, "K3 pt map ")
    rep.check("T1", "新映射（fill）读到 X 页标记", marks["K3_MARK_X"],
              int(m_map["word"], 0))
    stale = k3pt.one(text, "K3 pt stale ")
    rep.check("T1", "改 PTE 不失效 ⇒ 仍读旧页（命中不重读 PTE）",
              marks["K3_MARK_X"], int(stale["word"], 0))
    rep.check("T1", "PTE 确实已指向 Y 页（不是缓存假象）", y_ppn,
              int(stale["pte_ppn"], 0))
    inval = k3pt.one(text, "K3 pt inval_va ")
    rep.check("T2", "invalid + VA ⇒ 读到新页", marks["K3_MARK_Y"],
              int(inval["word"], 0))

    ranges = k3pt.one(text, "K3 pt ranges ")
    rep.check("T2", "invalid + range（内核 VA）⇒ 读到新页", 1,
              int(ranges["krq_new"], 0))
    rep.check("T2", "invalid + range（VMA 拼写）⇒ 读到新页", 1,
              int(ranges["vma_new"], 0))
    rep.check("T2", "空 range 不下发命令、条目保留（只影响相交条目）", 1,
              int(ranges["empty_old"], 0))
    rep.check("T2", "invalid + all（flush_tlb_mm）⇒ 读到新页", 1,
              int(ranges["mm_new"], 0))

    clean = k3pt.one(text, "K3 pt ad_clean ")
    rep.check("T3", "clean 前 PTE.A 仍为 0（填充不回写）", 0,
              int(clean["a_before"], 0))
    rep.check("T3", "clean 回写 A", 1, int(clean["a_after"], 0))
    rep.check("T3", "clean 不写回 D（未修改）", 0, int(clean["d_after"], 0))
    rep.check("T3", "clean 保留条目 ⇒ 仍读旧页", 1, int(clean["kept_old"], 0))

    flush = k3pt.one(text, "K3 pt flush ")
    rep.check("T3", "flush 回写 A", 1, int(flush["a"], 0))
    rep.check("T3", "flush 回写 D", 1, int(flush["d"], 0))
    rep.check("T3", "flush 删条目 ⇒ 再访问走步进", 1, int(flush["refill_new"], 0))

    # The matrix outcome follows §4.5's own sentence about each operation.
    matrix = k3pt.lines_of(text, "K3 pt m_")
    for name, row in sorted(matrix.items()):
        _m, op, _scope = name.split("_")
        want = "new" if sem[op]["deletes"] else "old"
        got = "new" if int(row["word"], 0) == marks["K3_MARK_Y"] else "old"
        rep.check("T4", f"{name} 结果（§4.5：{'删除' if sem[op]['deletes'] else '保留'}条目）",
                  want, got)
        rep.check("T4", f"{name} PTE.A",
                  1 if sem[op]["writes_ad"] else 0, int(row["a"], 0))
        rep.check("T4", f"{name} 内核自评", 1, int(row["ok"], 0))

    asid_g = k3pt.one(text, "K3 pt asid_g ")
    rep.check("T5", "ASID_ANY=0 不动 G=1 条目", 1,
              int(asid_g["any0_global_old"], 0))
    rep.check("T5", "ASID_ANY=0 删掉 G=0 条目", 1,
              int(asid_g["any0_local_new"], 0))
    rep.check("T5", "ASID_ANY=1 含 G=1 条目（删掉它）", 1,
              int(asid_g["any1_global_new"], 0))

    ptbr = k3pt.one(text, "K3 pt ptbr_no_inval ")
    rep.check("T6", "写 PTBR 不隐含失效（条目仍命中）", 1, int(ptbr["old"], 0))
    names = d["no_implicit"]
    rep.check("T6", "§4.5 点名 PTBR/ASID/ptw_enable 三者均不隐含失效",
              [True, True, True],
              [names["PTBR"], names["ASID"], names["ptw_enable"]])
    rep.check("T6", "写 ASID 后 G=1 条目仍在（ASID 写不隐含失效）", 1,
              int(asid_g["any0_global_old"], 0))


def check_tlb_static(rep: Report, d: dict) -> None:
    """Hardware-side TLB: reconciled statically (L3 runs the probes)."""
    makefile = MAKEFILE.read_text(encoding="utf-8")
    m = re.search(r"^ARCH_CFX_PROBES\s*=\s*(.+)$", makefile, re.MULTILINE)
    probes = m.group(1).split() if m else []
    rep.check("T7", "Makefile 的 ARCH_CFX_PROBES 含 TLB 探针条目", True,
              "tlb" in probes)
    rep.check("T7", "TLB 探针载体存在", True,
              TLB_PROBE.is_file() and EXPECTED_YAML.is_file())
    if not TLB_PROBE.is_file():
        return

    import yaml  # noqa: PLC0415 — the arch driver reads the same file
    doc = yaml.safe_load(EXPECTED_YAML.read_text(encoding="utf-8"))
    cases = doc.get("cases") or []
    rep.check("T7", "expected.yaml 非空（vacuous ⇒ FAIL）", True, bool(cases))
    names = sorted(entry.get("only") for entry in cases)
    rep.check("T7", "expected.yaml 的 case 名唯一", len(names), len(set(names)))

    subs = d["subs"]
    classes = set(d["causes"]) | {"none"}
    bad_sub = {entry["id"]: [item.get("subcause") for item in entry.get("checks", [])
                             if item.get("subcause") is not None
                             and item.get("subcause") not in subs]
               for entry in cases}
    rep.check("T7", "期望的子原因符号全部来自 contract-see §6.1.1", {},
              {cid: names_ for cid, names_ in bad_sub.items() if names_})
    bad_cause = {entry["id"]: [item.get("cause") for item in entry.get("checks", [])
                               if item.get("cause") not in classes]
                 for entry in cases}
    rep.check("T7", "期望的大类全部来自 spec/DADAO-13 §2", {},
              {cid: names_ for cid, names_ in bad_cause.items() if names_})
    # "No magic numbers": every expectation is a symbol plus a source pointer.
    numeric = [(entry["id"], item.get("label")) for entry in cases
               for item in entry.get("checks", [])
               if re.fullmatch(r"0x[0-9a-fA-F]+|\d+", str(item.get("cause")))]
    rep.check("T7", "期望里没有裸编码（cause 一律是符号名）", [], numeric)
    unsourced = [(entry["id"], item.get("label")) for entry in cases
                 for item in entry.get("checks", []) if not item.get("source")]
    rep.check("T7", "每条期望都有来源指针（source 非空）", [], unsourced)

    # The driver cross-checks the same file against the contract tables.
    proc = subprocess.run([sys.executable, str(TLB_PROBE), "--selfcheck"],
                          cwd=str(_REPO), capture_output=True, text=True,
                          timeout=600)
    rep.check("T7", "min_rom_probe_tlb.py --selfcheck（合约 ↔ 载体 ↔ expected）",
              0, proc.returncode)
    rep.stat((proc.stdout or proc.stderr).strip().splitlines()[-1]
             if (proc.stdout or proc.stderr).strip() else "<无输出>")


# ---------------------------------------------------------------------------
# F: the fault channel
# ---------------------------------------------------------------------------

def check_fault(rep: Report, runs: dict, snaps: dict, d: dict) -> None:
    subs = d["subs"]
    header = d["header"]
    perm_shift, mem_shift = d["shifts"]

    # The kernel's sub-reason table is the contract's projection, bit by bit.
    rep.check("F1", "cause-sub.h 的逐位值 == contract-see §6.1.1", {},
              {name: f"header={header.get(name)} contract={row['bit']}"
               for name, row in subs.items() if header.get(name) != row["bit"]})
    rep.check("F1", "子原因名集合 == contract-see §6.1.1", sorted(subs),
              sorted(name for name in header if name in subs))
    rep.check("F1", "wyde 低位：CFXPERM == wyde2 的最低位",
              min(row["bit"] for row in subs.values()
                  if row["cause"] == "CFXPERM"), perm_shift)
    rep.check("F1", "wyde 低位：CFXMEM == wyde3 的最低位",
              min(row["bit"] for row in subs.values()
                  if row["cause"] == "CFXMEM"), mem_shift)
    ranges = d["contract_reserved"]
    rep.check("F1", "§6.1 的保留区 == [63:58]/[47:40]/[31:16]",
              {(63, 58), (47, 40), (31, 16)}, ranges)
    want_masks = {(hi, lo): ((1 << (hi - lo + 1)) - 1) << lo for hi, lo in ranges}
    got = d["reserved"]
    rep.check("F1", "内核保留位掩码 == §6.1 的保留区",
              [want_masks[(63, 58)], want_masks[(47, 40)], want_masks[(31, 16)]],
              [got["MEM_RESERVED"], got["PERM_RESERVED"], got["RESERVED16"]])
    # "Every other class carries no sub-reason at all" (§6.1) — the kernel must
    # refuse a non-page-table id that carries one.
    layout = {name: (int(value), int(cid, 0))
              for name, value, cid in re.findall(
                  r"^K3 pf layout (\w+)=(-?\d+) id=(\S+)$",
                  runs["pf1"][1], re.MULTILINE)}
    other = layout.get("other_dirty")
    rep.check("F1", "其它 cause 带 [63:16] 位 ⇒ 被判为畸形（§6.1）", True,
              bool(other) and other[0] != 0)
    rep.check("F1", "裸的其它 cause ⇒ 合法（其它 cause 的 [63:16] 必须为 0）",
              (0, d["causes"]["CFXTRAP"]), layout.get("other_clean"))

    # The shape cases the kernel dispatches are the ones the source declares:
    # a dropped or silently added case cannot pass as "not seen".
    rep.check("F1", "layout 的 case 集合 == 内核源码声明的集合",
              sorted(layout_case_names()), sorted(layout))

    # P1/P2: a missing page is filled, retried, and not re-entered.
    text = runs["pf1"][1]
    p1 = k3pf.case_line(text, "P1")
    entry = k3pf.channel_before(text, "P1")
    if p1 is None or entry is None:
        rep.check("F2", "P1 行与通道行存在", "两者都有", "缺失")
    else:
        rep.check("F2", "P1 读缺页后读回 0", 0, num(p1.get("word")))
        rep.check("F2", "P1 恰进通道一次", 1, num(p1.get("entries")))
        rep.check("F2", "P1 通道大类（cause & 0xffff）", "CFXMEM",
                  entry.get("cause"))
        rep.check("F2", "P1 原始 cause_id == CFXMEM|DGPTRAP（契约派生）",
                  hex(sub_id(d, "DGPTRAP")), entry.get("id"))
        rep.check("F2", "P1 子原因名 == 契约的 DGPTRAP", "DGPTRAP",
                  entry.get("sub"))
        rep.check("F2", "P1 走了缺失填充分支", "fill-zero", entry.get("result"))
        rep.check("F2", "P1 命中的窗口就是被访问的窗口", num(p1.get("win")),
                  num(entry.get("vma", "0-0").split("-")[0]))
    p2 = k3pf.case_line(text, "P2")
    if p2 is None:
        rep.check("F2", "P2 行存在", "存在", "缺失")
    else:
        rep.check("F2", "P2 第二次访问不再进通道（计数增量 == 0）",
                  num(p2.get("entries_before")), num(p2.get("entries")))
        rep.check("F2", "P2 写后读回一致", True,
                  num(p2.get("word2")) == d["pf"]["K3_PF_MAGIC"] + 1)

    # pf4: an access outside every window terminates by name.
    p4 = k3pf.case_line(runs["pf4"][1], "P7")
    chan4 = (k3pf.channel_lines(runs["pf4"][1]) or [None])[0]
    die4 = k3pf.die_line(runs["pf4"][1])
    if p4 is None or chan4 is None or die4 is None:
        rep.check("F3", "pf4 的前置行/通道行/终止行都存在", "三者都有", "缺失")
    else:
        rep.check("F3", "无窗口：通道大类", "CFXMEM", chan4.get("cause"))
        rep.check("F3", "无窗口：子原因 == DGPTRAP", "DGPTRAP", chan4.get("sub"))
        rep.check("F3", "无窗口：分支 == die-no-vma", "die-no-vma",
                  chan4.get("result"))
        rep.check("F3", "无窗口：cause_info == 被访问的地址", chan4.get("va"),
                  die4["info"])
        rep.check("F3", "无窗口：终止行的原因名 == 大类", "CFXMEM",
                  die4["cause"])
        rep.check("F3", "无窗口：终止行的编号 == 大类（子原因不进退出码）",
                  hex(d["causes"]["CFXMEM"]), die4["id"])
        rep.check("F3", "无窗口：通道行数 == 1（不重试）", 1,
                  len(k3pf.channel_lines(runs["pf4"][1])))

    # pf5: ADWBFAIL is a verdict, not a fault to retry.
    p6 = k3pf.case_line(runs["pf5"][1], "P6")
    chan5 = (k3pf.channel_lines(runs["pf5"][1]) or [None])[0]
    die5 = k3pf.die_line(runs["pf5"][1])
    if p6 is None or chan5 is None or die5 is None:
        rep.check("F4", "pf5 的前置行/通道行/终止行都存在", "三者都有", "缺失")
    else:
        rep.check("F4", "ADWBFAIL：分支 == die-adwb", "die-adwb",
                  chan5.get("result"))
        rep.check("F4", "ADWBFAIL：子原因 == ADWBFAIL", "ADWBFAIL",
                  chan5.get("sub"))
        rep.check("F4", "ADWBFAIL：不分配页（池计数不变）", p6.get("pool"),
                  chan5.get("pool"))
        rep.check("F4", "ADWBFAIL：cause_info == 打印的 PTE 物理地址",
                  p6.get("pte_pa"), chan5.get("va"))
        rep.check("F4", "ADWBFAIL：终止行的 info == 该 PTE 地址", p6.get("pte_pa"),
                  die5["info"])
        rep.check("F4", "ADWBFAIL：通道行数 == 1（不重试）", 1,
                  len(k3pf.channel_lines(runs["pf5"][1])))

    # The class is `cause & 0xffff`: a sub-reason-carrying id is still named.
    channels = (k3pf.channel_lines(runs["pf1"][1]) +
                k3pf.channel_lines(runs["pf4"][1]) +
                k3pf.channel_lines(runs["pf5"][1]))
    rep.check("F5", "通道行数非零（vacuous ⇒ FAIL）", True, bool(channels))
    unmasked = {row.get("n"): row.get("cause") for row in channels
                if d["causes"].get(row.get("cause")) != (num(row.get("id")) & 0xffff)}
    rep.check("F5", "每条通道行的大类 == id & 0xffff", {}, unmasked)
    rep.check("F5", "没有 unknown 大类（带子原因位也必须命名）", [],
              sorted({row.get("cause") for row in channels
                      if row.get("cause") in (None, "unknown")}))
    exits = k3pf.only_line(runs["pf1"][1], "K3 pf exit ")
    if exits is None:
        rep.check("F5", "K3 pf exit 行存在", "一行", "缺失/多行")
    else:
        rep.check("F5", "带子原因的 CFXTRAP 仍按大类命名", "CFXTRAP",
                  exits.get("dirty_name"))
        rep.check("F5", "退出码与裸 CFXTRAP 相同（分段不看子原因）",
                  exits.get("bare_code"), exits.get("dirty_code"))
    cause_line = k3pt.one(runs["pt"][1], "K3 pt cause ")
    rep.check("F5", "带子原因位的 CFXMEM 名字 == 裸 CFXMEM",
              cause_line["bare"], cause_line["masked"])
    rep.check("F5", "大类 == cause & 0xffff", d["causes"]["CFXMEM"],
              num(cause_line["class"]) & 0xffff)


# ---------------------------------------------------------------------------
# C: the shared zero page (P8-P10)
# ---------------------------------------------------------------------------

def check_zero(rep: Report, text: str, d: dict) -> None:
    pages = k3pf.only_line(text, "K3 pf init ")
    if pages is None:
        rep.check("C0", "K3 pf init 行存在", "一行", "缺失/多行")
        return
    zero_pa = num(pages.get("zero_pa"))
    ppn_low, ppn_high = d["l1"]["PPN"]
    ppn_mask = ((1 << (ppn_high - ppn_low + 1)) - 1) << ppn_low

    def pfn(value) -> int:
        return (num(value) & ppn_mask) >> ppn_low

    magic = d["pf"]["K3_PF_MAGIC"]
    p8 = k3pf.case_line(text, "P8")
    if p8 is None:
        rep.check("C1", "P8 行存在", "存在", "缺失")
    else:
        rep.check("C1", "P8 读缺页映射共享零页（PTE 的 PN == 零页 PN）",
                  pfn(zero_pa), num(p8.get("pte_pa")))
        rep.check("C1", "P8 W = 0（共享只读）", 0, num(p8.get("w")))
        rep.check("C1", "P8 R = 1", 1, num(p8.get("r")))
        rep.check("C1", "P8 X = 0（不可执行）", 0, num(p8.get("x")))

    p9 = k3pf.case_line(text, "P9")
    entry9 = k3pf.channel_before(text, "P9")
    if p9 is None or entry9 is None:
        rep.check("C2", "P9 行与通道行存在", "两者都有", "缺失")
    else:
        rep.check("C2", "P9 写后读回一致", magic, num(p9.get("word")))
        rep.check("C2", "P9 写缺页换新页（新 PA != 零页 PA）", True,
                  num(p9.get("pte_pa")) != pfn(zero_pa))
        rep.check("C2", "P9 W = 1", 1, num(p9.get("w")))
        rep.check("C2", "P9 恰分配一页", 1,
                  num(p9.get("allocs")) - num(p9.get("allocs_before")))
        rep.check("C2", "P9 通道大类 == CFXPERM", "CFXPERM", entry9.get("cause"))
        rep.check("C2", "P9 原始 cause_id == CFXPERM|NWPERM（契约派生）",
                  hex(sub_id(d, "NWPERM")), entry9.get("id"))
        rep.check("C2", "P9 子原因名 == 契约的 NWPERM", "NWPERM",
                  entry9.get("sub"))
        rep.check("C2", "P9 走了零页换新页分支", "replace-zero",
                  entry9.get("result"))

    p10 = k3pf.case_line(text, "P10")
    if p10 is None:
        rep.check("C3", "P10 行存在", "存在", "缺失")
    else:
        rep.check("C3", "P10 第二个窗口也读 0", 0, num(p10.get("word_b")))
        rep.check("C3", "P10 两处 PTE 都指向零页",
                  [pfn(zero_pa), pfn(zero_pa)],
                  [pfn(p10.get("pte_a")), pfn(p10.get("pte_b"))])
        rep.check("C3", "P10 零页未被污染（整页扫描）", 0,
                  num(p10.get("zero_dirty")))
    p9b = k3pf.case_line(text, "P9b")
    if p9b is None:
        rep.check("C3", "P9b 行存在（冷写缺页）", "存在", "缺失")
    else:
        rep.check("C3", "P9b 零页未被写（冷写也换页，不就地写）", 0,
                  num(p9b.get("zero_dirty")))
        rep.check("C3", "P9b 新 PA != 零页 PA", True,
                  num(p9b.get("pte_pa")) != pfn(zero_pa))


# ---------------------------------------------------------------------------
# X: exit codes and quiescence
# ---------------------------------------------------------------------------

def check_exit(rep: Report, runs: dict, d: dict) -> None:
    specs = d["specs"]
    ranges = specs["ranges"]
    pass_low, pass_high = ranges["pass"]
    guest_low, guest_high = ranges["guest"]
    other_low, other_high = ranges["other"]
    monitor_low, monitor_high = ranges["monitor"]

    rep.check("X1", "四段区间互不重叠且 guest < other < monitor", True,
              pass_low == pass_high == 0
              and guest_low <= guest_high < other_low <= other_high
              < monitor_low <= monitor_high)
    for image in ("pt", "pf1"):
        rep.check("X1", f"{image} 正例 rc == §7.1 的 PASS 值", pass_low,
                  runs[image][0])

    codes = d["codes"]
    rep.check("X2", "K3 自检码非空（vacuous ⇒ FAIL）", True, bool(codes))
    rep.check("X2", f"自检码全在 guest 段（{hex(guest_low)}-{hex(guest_high)}）",
              {}, {name: hex(value) for name, value in codes.items()
                   if not guest_low <= value <= guest_high})
    rep.check("X2", "自检码互不重复", len(codes), len(set(codes.values())))
    rep.stat("自检码 " + " ".join(f"{name.split(':')[-1]}={hex(value)}"
                                  for name, value in sorted(codes.items())))

    want = {image: monitor_code(specs, "supv", "CFXMEM")
            for image in TERMINATING}
    for image in sorted(TERMINATING):
        rep.check("X3", f"{image} 终止码 == §7.1 monitor(supv, CFXMEM)（supv ⇒ "
                        f"0xE0|bit）", hex(want[image]), hex(runs[image][0]))
        rc = runs[image][0]
        rep.check("X3", f"{image} 终止码落 monitor 段且不落 guest/其它段", True,
                  monitor_low <= rc <= monitor_high
                  and not (guest_low <= rc <= guest_high)
                  and not (other_low <= rc <= other_high))

    for image in ("pt", "pf1"):
        text = runs[image][1]
        rep.check("X4", f"{image} 输出无 panic/oops/BUG", [],
                  lines_matching(text, r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:)"))
        rep.check("X4", f"{image} 输出无 unknown cause", [],
                  lines_matching(text, r"(cause=unknown|unknown cause)"))
        body = [line for line in text.splitlines() if line.strip()]
        marker = "K3 pt done:" if image == "pt" else "K3 pf done:"
        rep.check("X4", f"{image} 完成行是输出的最后一行", True,
                  bool(body) and body[-1].startswith(marker))
        rep.check("X4", f"{image} 完成行恰 1 次（无二次初始化）", 1,
                  len(lines_matching(text, "^" + re.escape(marker))))
        rep.check("X4", f"{image} 没有自检失败行", [],
                  lines_matching(text, r"^K3 p[ft] FAIL: "))

    for image in sorted(TERMINATING):
        text = runs[image][1]
        fatal = lines_matching(text, r"^dadao: .* cause=\w+\(0x[0-9a-f]+\) ip=")
        rep.check("X5", f"{image} 具名终止恰 1 条（不递归）", 1, len(fatal))
        body = [line for line in text.splitlines() if line.strip()]
        summary = re.match(r"^dadao: die mode=(\d+) code=(\S+)$", body[-1]) \
            if body else None
        rep.check("X5", f"{image} 输出以 die 汇总行结束（mode == §7.1 supv）",
                  specs["modes"]["supv"],
                  int(summary.group(1)) if summary else "<缺 die 行>")
        rep.check("X5", f"{image} die 汇总行的 code == 退出码", hex(runs[image][0]),
                  summary.group(2) if summary else "<缺 die 行>")
        rep.check("X5", f"{image} 输出无 panic/oops/BUG", [],
                  lines_matching(text, r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:)"))

    rep.stat(f"segments pass={hex(pass_low)} guest={hex(guest_low)}-"
             f"{hex(guest_high)} other={hex(other_low)}-{hex(other_high)} "
             f"monitor={hex(monitor_low)}-{hex(monitor_high)} "
             f"supv={specs['modes']['supv']}")


# ---------------------------------------------------------------------------
# R: reverse assertions (counts, the retry budget, the §4a retirement)
# ---------------------------------------------------------------------------

#: §4a disposition (docs/Process-07 §4a): every assertion this task retired
#: from an earlier gate, the wording that replaced it, and the K3 group that
#: took the criterion over.  ``anchor`` is the row name in the doc record; the
#: gate asserts all three places agree, so a retired wording cannot come back
#: unnoticed and the record cannot drift away from the code.
RETIREMENTS = (
    {
        "file": "tools/linux/check_k1.py",
        "anchor": "K13 CFXMEM 计数",
        "old": "CFXMEM 只出现 1 次（唯一一次预先声明的探针）",
        "new": "本镜像内（CONFIG_DADAO_K1_EARLY_STOP=y、无 mm 子系统）CFXMEM "
               "只出现 1 次：唯一一次预先声明的探针；替代判据 = check-linux-k3 "
               "F 组",
        "alt": "check-linux-k3 F 组",
    },
    {
        "file": "tools/linux/check_k1.py",
        "anchor": "K13 CFXMEM resumed",
        "old": "该 CFXMEM 是被处理过的探针（resumed）",
        "new": "本镜像内（无 mm 子系统）该 CFXMEM 是被处理过的探针（resumed）；"
               "替代判据 = check-linux-k3 F 组",
        "alt": "check-linux-k3 F 组",
    },
    {
        "file": "tools/linux/check_k1.py",
        "anchor": "K13 后置子系统痕迹",
        "old": "无 K1 之后的子系统痕迹（init/syscall/IRQ/timer/tick）",
        "new": "本镜像内（CONFIG_DADAO_K1_EARLY_STOP=y、无 mm 子系统 ⇒ 无页故障"
               "通道痕迹）无 K1 之后的子系统迹象（init/syscall/IRQ/timer/tick）；"
               "替代判据 = check-linux-k3 F 组",
        "alt": "check-linux-k3 F 组",
    },
    {
        "file": "tools/linux/check_k2.py",
        "anchor": "E8 未声明 CFXMEM 退出码",
        "old": "未声明的 CFXMEM：退出码 == §7.1 supv+CFXMEM",
        "new": "本镜像内（无 mm 子系统）未声明的 CFXMEM：退出码 == §7.1 "
               "supv+CFXMEM；K3 起同址由页故障通道接住，替代判据 = "
               "check-linux-k3 F 组",
        "alt": "check-linux-k3 F 组",
    },
)


def check_retirement(rep: Report, sources: dict[str, str] | None = None) -> None:
    """The §4a ledger is in force: new wording there, old wording gone."""
    doc = PROCESS_07.read_text(encoding="utf-8")
    for item in RETIREMENTS:
        text = (sources or {}).get(item["file"])
        if text is None:
            text = (_REPO / item["file"]).read_text(encoding="utf-8")
        rep.check("R4", f"{item['anchor']}：新文案在 {item['file']}",
                  True, f'"{item["new"]}"' in text)
        rep.check("R4", f"{item['anchor']}：已退役的旧文案不在 {item['file']}",
                  False, f'"{item["old"]}"' in text)
        rep.check("R4", f"{item['anchor']}：替代判据指向 {item['alt']}", True,
                  item["alt"] in text)
        rep.check("R4", f"{item['anchor']}：docs/Process-07 §4a 有处置记录", True,
                  item["anchor"] in doc and item["alt"] in doc)


def check_reverse(rep: Report, runs: dict, d: dict) -> None:
    text = runs["pf1"][1]
    magic = d["pf"]["K3_PF_MAGIC"]
    budget = d["retry_budget"]

    # One channel line per entry, and the counter the kernel prints must agree
    # with the number of lines actually produced (a silent extra entry shows up
    # in both, a missing line shows up here).
    channels = k3pf.channel_lines(text)
    rep.check("R1", "通道行非空（vacuous ⇒ FAIL）", True, bool(channels))
    rep.check("R1", "一条入口一行且序号连续 1..n（不多不少）",
              list(range(1, len(channels) + 1)),
              [num(row.get("n")) for row in channels])

    # The entry deltas are the case design: a first read is one entry, a second
    # access to a private page is none, a write on the zero page is one, and a
    # cold store is two (fill, then replace).
    p1 = k3pf.case_line(text, "P1") or {}
    p2 = k3pf.case_line(text, "P2") or {}
    p9 = k3pf.case_line(text, "P9") or {}
    rep.check("R1", "P1 入口数 == 1（首次读缺页）", 1, num(p1.get("entries")))
    rep.check("R1", "P2 入口增量 == 0（私有页不再进通道）", 0,
              num(p2.get("entries")) - num(p2.get("entries_before")))
    rep.check("R1", "P9 入口增量 == 1（零页写缺页）", 1,
              num(p9.get("entries")) - num(p9.get("entries_before")))
    rep.check("R1", "P9b 入口增量 == 2（先填充、后换页）", 2,
              num((k3pf.case_line(text, "P9b") or {}).get("entries_delta")))

    # No retry budget was ever reached, and no entry ever repeated the same
    # (address, cause) more than the budget allows.
    rep.check("R2", "无重试上限痕迹（没有 die-budget 分支）", [],
              sorted({row.get("n") for row in channels
                      if row.get("result") == "die-budget"}))
    rep.check("R2", f"通道行的 try 计数均 <= 内核预算（{budget}）",
              [], sorted({row.get("n") for row in channels
                          if num(row.get("try")) > budget}))
    rep.check("R2", "无重试上限触发行（内核打印）", [],
              lines_matching(text, r"die-budget"))

    # Allocation deltas match the case: a replace takes exactly one page.
    rep.check("R3", "P9 分配增量 == 1（换页不复制）", 1,
              num(p9.get("allocs")) - num(p9.get("allocs_before")))
    rep.check("R3", "P9b 分配增量 == 1", 1,
              num((k3pf.case_line(text, "P9b") or {}).get("allocs_delta")))
    # The pool counter the channel prints: no single entry may hand out more
    # than one page (a fill can allocate one *table* page, a replace one data
    # page), so a burst is a fault-path defect.
    pools = [num(row.get("pool")) for row in channels]
    bursts = [(channels[i].get("n"), pools[i] - pools[i - 1])
              for i in range(1, len(pools)) if pools[i] - pools[i - 1] > 1]
    rep.check("R3", "没有一次入口分配超过一页（表页或数据页，各至多一页）", [],
              bursts)

    # The kernel's own verdict on the case (a case-design violation shows here
    # before any of the derived assertions above can absorb it).
    rep.check("R3", "case 1 的每一条 pfc 行都自评 ok=1", [],
              [f"{row.get('n')} ok={row.get('ok')}" for row in
               (k3pf.case_line(text, tag) for tag in
                ("P1", "P8", "P10", "P9", "P2", "P9b", "P3a", "P3b", "P3c",
                 "P3d", "P3e", "P4a", "P4a2", "P4a3", "P4a4"))
               if row and num(row.get("ok")) != 1])

    check_retirement(rep)


# ---------------------------------------------------------------------------
# the judging half
# ---------------------------------------------------------------------------

def judge(rep: Report, result: dict) -> None:
    runs, snaps, builds, d = (result["runs"], result["snaps"],
                              result["builds"], result["derivs"])
    for image in IMAGES:
        rc, text, cmd = runs[image]
        check_build(rep, image, builds[image], snaps[image], cmd, text)
    check_primitives(rep, runs["pt"][1], d)
    check_tlb(rep, runs["pt"][1], d)
    check_tlb_static(rep, d)
    check_fault(rep, runs, snaps, d)
    check_zero(rep, runs["pf1"][1], d)
    check_exit(rep, runs, d)
    check_reverse(rep, runs, d)


def gate(rep: Report, qemu: str) -> dict:
    """Build and boot the four images, then judge them."""
    rom = firmware()
    print(f"k3 gate: bootrom={Path(rom).name} qemu={Path(qemu).name} "
          f"md5={md5(Path(qemu))[:8]}", flush=True)
    result = {"runs": {}, "snaps": {}, "builds": {}, "derivs": {}, "rom": rom}
    for image in IMAGES:
        rc_build, snap = build_image(image)
        result["builds"][image] = rc_build
        if snap is None:
            rep.check("B0", f"{image} 镜像可构建", 0, rc_build)
            raise SystemExit(f"check_k3: build {image} rc={rc_build}")
        result["snaps"][image] = snap
        if not result["derivs"]:
            result["derivs"] = derivations(snap)
        result["runs"][image] = boot(image, rom, qemu)
        rc, text, _cmd = result["runs"][image]
        print(f"---- guest output ({image}, rc={hex(rc)}) ----", flush=True)
        print(text.strip(), flush=True)
        print("-----------------------------------------------", flush=True)
    return result


# ---------------------------------------------------------------------------
# --selfcheck: every group must be able to fail
# ---------------------------------------------------------------------------

def run_selfcheck(qemu: str) -> int:
    """Mutate the captured runs / .config / the retirement ledger, one per group."""
    result = gate(Report(quiet=True), qemu)
    runs, snaps, d = result["runs"], result["snaps"], result["derivs"]
    _krc, ktext, kcmd = runs["pt"]
    prc, ptext, _pcmd = runs["pf1"]

    base = Report(quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        judge(base, result)
    print(f"  [{'PASS' if not base.fails else 'FAIL'}] selfcheck 基准四镜像全绿 | "
          f"期望=0 失败 实际={len(base.fails)} 失败", flush=True)

    flipped: dict[str, bool] = {}

    def flip(group: str, label: str, fn) -> None:
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                fn(rep)
            except SystemExit as exc:
                rep.fails.append(f"{group} 输入派生失败: {exc}")
        red = [msg for msg in rep.fails if msg.startswith(group)]
        print(f"  [{'PASS' if red else 'FAIL'}] selfcheck {label} | "
              f"期望={group} FAIL 实际={red[0] if red else '未翻转'}", flush=True)
        flipped[group] = flipped.get(group, True) and bool(red)

    # B: the captured .config claims a 4 KiB page and keeps a K1 early stop.
    broken = snaps["pt"]["config"].replace("CONFIG_PAGE_SIZE_64KB=y",
                                           "# CONFIG_PAGE_SIZE_64KB is not set")
    broken = re.sub(r"^CONFIG_PAGE_SHIFT=16$", "CONFIG_PAGE_SHIFT=12", broken,
                    flags=re.MULTILINE) + "CONFIG_DADAO_K1_EARLY_STOP=y\n"
    flip("B", "B 页大小/边界被改", lambda rep: check_build(
        rep, "pt", 0, dict(snaps["pt"], config=broken), kcmd, ktext))

    # M: one command value moves by one bit.
    flip("M", "M 命令值改一位", lambda rep: check_primitives(
        rep, re.sub(r"(K3 pt inval_va .*?cmd=)(0x[0-9a-f]+)",
                    lambda m: m.group(1) + hex(int(m.group(2), 16) ^ 0x2),
                    ktext), d))

    # T: the ASID_ANY/G verdicts swap.
    flip("T", "T ASID_ANY 判据对调", lambda rep: check_tlb(
        rep, ktext.replace("any0_global_old=1", "any0_global_old=0")
        .replace("any1_global_new=1", "any1_global_new=0"), d))

    # F: a sub-reason symbol is renamed in the channel output.
    flip("F", "F 子原因符号改名", lambda rep: check_fault(
        rep, dict(runs, pf1=(prc, ptext.replace("sub=DGPTRAP", "sub=DSPFTRAP"))),
        snaps, d))

    # C: the replacement page is not observed.
    def _w0(match: re.Match) -> str:
        return match.group(1) + "0"

    flip("C", "C 换页判据被改", lambda rep: check_zero(
        rep, re.sub(r"(K3 pfc P9 win=.*?\bw=)\d+", _w0, ptext, count=1), d))

    # X: a self-check constant moves one past the guest segment's edge.
    high = d["specs"]["ranges"]["guest"][1]
    saved = k3_selfcheck_codes
    try:
        globals()["k3_selfcheck_codes"] = lambda: {
            **d["codes"], "arch/dadao/mm/k3_pt_selftest.c:K3_FAIL_EDGE": high + 1}
        flip("X", "X 段边界挪一位", lambda rep: check_exit(
            rep, runs, derivations(snaps["pf1"])))
    finally:
        globals()["k3_selfcheck_codes"] = saved

    # R: one handler entry count changes / the retired wording comes back.
    flip("R", "R 入口计数被改", lambda rep: check_reverse(
        rep, dict(runs, pf1=(prc, re.sub(r"(K3 pfc P1 .*?\bentries=)\d+",
                                         r"\g<1>2", ptext, count=1))), d))
    flip("R", "R 旧文案回潮", lambda rep: check_retirement(
        rep, {"tools/linux/check_k1.py": (
            _REPO / "tools/linux/check_k1.py").read_text(encoding="utf-8")
            + f'\n    rep.check("K13", "{RETIREMENTS[0]["old"]}", 1, 1)\n'}))

    missing = [group for group in GROUPS if not flipped.get(group)]
    print(f"check-k3 selfcheck: {'PASS' if not missing else 'FAIL'} "
          f"({len(GROUPS) - len(missing)}/{len(GROUPS)} 组可翻转；未翻转 {missing})")
    return 0 if not missing and not base.fails else 1


# ---------------------------------------------------------------------------
# --inject: real corruptions, rebuilt and restored (cp + md5)
# ---------------------------------------------------------------------------

PGTABLE_H = "arch/dadao/include/asm/pgtable.h"
PTW_H = "arch/dadao/include/asm/ptw.h"
CAUSE_SUB_H = "arch/dadao/include/asm/cause-sub.h"
FAULT_C = "arch/dadao/mm/fault.c"

#: name -> the corruption, the image it is judged on, the groups that must go
#: red, and whether the red is a *build* failure (a compile-time assertion).
INJECTIONS = {
    # ① the page size the image was built with: the kernel's own assertion moves
    #    to the 4 KiB geometry, so a 4 KiB image must not build at all.
    "page-size-4k": {
        "file": PGTABLE_H, "root": "source",
        "old": "#if PAGE_SHIFT != 16\n",
        "new": "#if PAGE_SHIFT != 12\n",
        "image": "pt", "groups": ("B",), "build_fail": True,
        "about": "页大小改成 4 KiB 几何 ⇒ 构建拒绝 ⇒ B 组红",
    },
    # ② the scope dimension of the command is shifted by one bit: every command
    #    value printed by the kernel disagrees with §4.5.
    "scope-shift": {
        "file": PTW_H, "root": "source",
        "old": "#define DADAO_TLB_CTRL_SCOPE_SHIFT\t2\n",
        "new": "#define DADAO_TLB_CTRL_SCOPE_SHIFT\t3\n",
        "image": "pt", "groups": ("M",), "build_fail": False,
        "about": "tlb_control 的 scope 移位错一位 ⇒ 命令值全错 ⇒ M 组红",
    },
    # ③ the CFXMEM sub-reason wyde is read from the CFXPERM wyde instead: the
    #    channel can no longer name the missing class.
    "subcause-wyde": {
        "file": CAUSE_SUB_H, "root": "source",
        "old": "#define DADAO_SUB_MEM_SHIFT\t48\t/* CFXMEM:  (cause_id >> 48) & 0xffff */\n",
        "new": "#define DADAO_SUB_MEM_SHIFT\t32\t/* CFXMEM:  (cause_id >> 32) & 0xffff */\n",
        "image": "pf1", "groups": ("F",), "build_fail": False,
        "about": "CFXMEM 的子原因按错 wyde 取值 ⇒ 缺失类无法命名 ⇒ F 组红",
    },
    # ④ the write to a zero-page mapping is made writable in place instead of
    #    being replaced: the shared page is written through.
    "zero-page-write": {
        "file": FAULT_C, "root": "source",
        "old": "\tset_pte(ptep, __pte(dadao_pf_pte(pa, true, false)));\n",
        "new": "\tset_pte(ptep, __pte(pte_val(*ptep) | _PAGE_WRITE));\n"
               "\t(void)pa;\n",
        "image": "pf1", "groups": ("C",), "build_fail": False,
        "about": "零页写缺页改成就地写零页 ⇒ C 组（P9/P10）红",
    },
    # ⑤ the fill reports success without installing anything: the retry budget
    #    has to end the boot, which is what F and R forbid.
    "retry-no-fill": {
        "file": FAULT_C, "root": "source",
        "old": "\tif (!dadao_zero_pa)\n\t\treturn NULL;\n"
               "\tset_pte(ptep, __pte(dadao_pf_zero_pte()));\n"
               "\tdadao_pf_publish(vma, addr, ptep);\n\treturn \"fill-zero\";\n",
        "new": "\tif (!dadao_zero_pa)\n\t\treturn NULL;\n"
               "\treturn \"fill-zero\";\n",
        "image": "pf1", "groups": ("F", "R"), "build_fail": False,
        "about": "handler 不分配直接重试 ⇒ 重试上限触发 ⇒ F/R 组红",
    },
    # ⑥ a retired wording comes back into the K1 gate: the §4a ledger is the
    #    only thing that notices, and it must.
    "retired-back": {
        "file": "tools/linux/check_k1.py", "root": "repo",
        "old": "# ── K13: reverse assertions ─────────────────────────────────────────\n",
        "new": "# ── K13: reverse assertions ─────────────────────────────────────────\n"
               "    rep.check(\"K13\", \"CFXMEM 只出现 1 次（唯一一次预先声明的探针）\", 1, 1)\n",
        "image": None, "groups": ("R",), "build_fail": False,
        "about": "旧的退役文案回潮 ⇒ R 组（§4a 机械断言）红",
    },
}


def _bundle(image: str, rc: int, text: str, cmd: list[str], snap: dict,
            rc_build: int, d: dict, runs: dict,
            groups: tuple[str, ...] = GROUPS) -> Report:
    """The checks of one image (what an injection re-runs after a rebuild).

    A line the kernel no longer reaches (it died earlier) is a red for the
    groups under test, not a crash of the gate: the injected image is broken,
    which is exactly what the injection wanted to show.
    """
    rep = Report(quiet=True)

    def run(fn, *args) -> None:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                fn(*args)
        except SystemExit as exc:
            for group in groups:
                rep.fails.append(f"{group} 行缺失: {exc}")

    run(check_build, rep, image, rc_build, snap, cmd, text)
    if image == "pt":
        run(check_primitives, rep, text, d)
        run(check_tlb, rep, text, d)
    else:
        runs = dict(runs, **{image: (rc, text, cmd)})
        run(check_fault, rep, runs, {}, d)
        if image == "pf1":
            run(check_zero, rep, text, d)
        run(check_exit, rep, runs, d)
        run(check_reverse, rep, runs, d)
    return rep


def run_inject(name: str, qemu: str, rom: str, result: dict,
               problems: list[str]) -> None:
    """One injection: patch -> (rebuild) -> red -> restore (cp) -> green."""
    spec = INJECTIONS[name]
    path = ((SOURCE if spec["root"] == "source" else _REPO) / spec["file"])
    image = spec["image"]
    before = md5(path)
    backup = path.read_bytes()
    text = backup.decode("utf-8")
    print(f"── inject:{name}（{spec['file']}；镜像 {image or '无（静态）'}）──",
          flush=True)
    if text.count(spec["old"]) != 1:
        problems.append(f"inject:{name}: 注入点不唯一（{text.count(spec['old'])} 处）")
        return
    path.write_text(text.replace(spec["old"], spec["new"], 1), encoding="utf-8")
    if md5(path) == before:
        problems.append(f"inject:{name}: 注入是空操作（md5 未变）")
        path.write_bytes(backup)
        return
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> "
          f"{md5(path)[:8]}", flush=True)

    try:
        if image is None:
            # Static: only the group that reads the gate sources can move.
            rep = Report(quiet=True)
            check_retirement(rep)
            for group in spec["groups"]:
                red = [msg for msg in rep.fails if msg.startswith(group)]
                print(f"  [{'PASS' if red else 'FAIL'}] inject:{name} 断言 "
                      f"{group} 变红 | 期望={group} 出现 FAIL 实际="
                      f"{red[0] if red else '未变红'}", flush=True)
                if not red:
                    problems.append(f"inject:{name}: {group} 未变红")
        else:
            rc_build, snap = build_image(image)
            if rc_build != 0:
                ok = spec["build_fail"]
                print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} 构建 "
                      f"rc={rc_build} | 期望={'非 0（编译期断言）' if ok else '0'}",
                      flush=True)
                if not ok:
                    problems.append(f"inject:{name}: 重建 rc={rc_build}")
            else:
                rc, out, cmd = boot(f"inject-{name}", rom, qemu)
                print(f"---- guest output ({name}, rc={hex(rc)}) ----", flush=True)
                print(out.strip()[-1500:], flush=True)
                print("-----------------------------------------------", flush=True)
                rep = _bundle(image, rc, out, cmd, snap, rc_build,
                              derivations(snap), result["runs"], spec["groups"])
                for group in spec["groups"]:
                    red = [msg for msg in rep.fails if msg.startswith(group)]
                    print(f"  [{'PASS' if red else 'FAIL'}] inject:{name} 断言 "
                          f"{group} 变红 | 期望={group} 出现 FAIL 实际="
                          f"{red[0] if red else '未变红'}", flush=True)
                    if not red:
                        problems.append(f"inject:{name}: {group} 未变红")
    except (Exception, SystemExit) as exc:    # keep going; restore below
        problems.append(f"inject:{name}: {type(exc).__name__}: {exc}")
    finally:
        path.write_bytes(backup)             # cp + md5, never `git checkout`
        restored = md5(path)
        ok = restored == before
        print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} 还原 (cp) | "
              f"md5 期望={before[:8]} 实际={restored[:8]}", flush=True)
        if not ok:
            problems.append(f"inject:{name}: 还原后 md5 不一致")

    if image is None:
        rep = Report(quiet=True)
        check_retirement(rep)
        green = not rep.fails
        print(f"  [{'PASS' if green else 'FAIL'}] inject:{name} 还原后回绿 | "
              f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
        if not green:
            problems.append(f"inject:{name}: 还原后仍失败（{rep.fails[0]}）")
        return

    rc_build, snap = build_image(image)
    if snap is None:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    rc, out, cmd = boot(f"restored-{name}", rom, qemu)
    rep = _bundle(image, rc, out, cmd, snap, rc_build, derivations(snap),
                  result["runs"])
    green = not rep.fails
    print(f"  [{'PASS' if green else 'FAIL'}] inject:{name} 还原后回绿 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
    if not green:
        problems.append(f"inject:{name}: 还原后仍失败（{rep.fails[0]}）")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--qemu", default=os.environ.get("K3G_QEMU"),
                    help="qemu-system-dadao binary (default: install root)")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured runs: every group must flip")
    ap.add_argument("--inject", action="store_true",
                    help="six corruptions: rebuild, assert FAIL, restore (cp+md5)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        print("\n".join(["positive", "selfcheck"] +
                        [f"inject:{name}" for name in INJECTIONS]))
        return 0

    qemu = args.qemu or k0.DEFAULT_QEMU
    if not Path(qemu).is_file():
        print(f"check-linux-k3: FAIL: {qemu} missing; run `make install-host`",
              file=sys.stderr)
        return 1

    if args.selfcheck:
        try:
            return run_selfcheck(qemu)
        except SystemExit as exc:
            print(f"check-linux-k3: {exc}", file=sys.stderr)
            return 2

    rep = Report()
    try:
        result = gate(rep, qemu)
        judge(rep, result)
        if args.inject:
            if rep.fails:
                print("check-linux-k3: 基线不绿，先修基线再做注入", flush=True)
            else:
                problems: list[str] = []
                for name in INJECTIONS:
                    run_inject(name, qemu, result["rom"], result, problems)
                total = len(INJECTIONS)
                if problems:
                    print(f"check-linux-k3 --inject: FAIL "
                          f"({len(problems)} 问题；{total} 路注入)", flush=True)
                    for problem in problems:
                        print("  - " + problem)
                    return 1
                print(f"check-linux-k3 --inject: PASS "
                      f"({total}/{total} 路注入按预期变红并还原)", flush=True)
    except SystemExit as exc:
        print(f"check-linux-k3: {exc}", file=sys.stderr)
        if rep.fails:
            # A build (or an image) was an assertion of its own: report it as
            # a FAIL of the group that owns it, not as a missing input.
            print(f"\n[GROUP] {rep.summary()}")
            print(f"check-linux-k3: FAIL ({len(rep.fails)} 项失败)")
            for failure in rep.fails:
                print("  - " + failure)
            return 1
        return 2

    print(f"\n[GROUP] {rep.summary()}")
    if not rep.fails:
        print(f"check-linux-k3: PASS ({rep.total}/{rep.total})")
    else:
        print(f"check-linux-k3: FAIL ({rep.total - len(rep.fails)}/{rep.total}); "
              f"{len(rep.fails)} 项失败")
        for failure in rep.fails:
            print("  - " + failure)
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
