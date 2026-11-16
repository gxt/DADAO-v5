#!/usr/bin/env python3
"""k3_pt_probe.py — M14 K3 page-table / TLB primitive gate (`m14-linux-011`).

K3 starts building page tables in software: the L1 entry that points at an L2
table, the TLB invalidation primitives and the ASID they are selected with.  The
kernel side of the milestone is `arch/dadao/mm/k3_pt_selftest.c` (compiled only
into a probe image, `CONFIG_DADAO_K3_PT_SELFTEST`); this gate builds that image,
boots it on the Vast machine and judges what the kernel reports.

Nothing is restated here — every expectation is derived from its owner:

  * the L1 field positions (P, SP, PPN, G, SPF)   -> ``spec/DADAO-12 §2.2.3``
  * the page-offset width and the per-level entry count -> §2.2.2
  * the invalidation encoding (op/scope/ASID_ANY)  -> ``contract-tlb`` TLB-19
  * the ASID register width                       -> ``contract-tlb`` TLB-04
  * the cause id of CFXMEM                        -> ``spec/DADAO-13 §2``
  * the self-check codes (guest segment)          -> ``spec/Kaiwu §7.1``
  * the page size / geometry the image really has -> the image's ``.config``
  * the data-page markers                         -> the kernel source itself

Checks (group ids are what ``--selfcheck``/``--inject`` flip):

  G1  the image under test is the K3 probe image, and the `.config` page size
      agrees with §2.2.2
  G2  the kernel's own geometry line (PAGE_SHIFT / PAGE_SIZE / entry counts /
      PGDIR_SHIFT / entry size)
  G3  `alloc`: the L1 entry `pmd_populate_kernel()` builds is P=1, SP=0, S=1,
      G=0, SPF=0, R/W/X/A/D=0 and PPN == the L2 table's PA; walking it lands on
      the table page
  G4  `map`/`stale`/`inval_va`/`ad_clean`/`flush`: a new mapping works, a
      changed PTE stays invisible until an explicit invalidation, `clean` keeps
      the entry and writes A back, `flush` writes A/D back and drops it
  G5  the whole (op, scope) matrix: 4 operations × 3 scopes, each with the
      contract's command value and its old/new/A outcome
  G6  the ASID register (16-bit, `[63:16]` reads 0) and the allocator
  G7  `ASID_ANY = 0` leaves G = 1 entries alone, `ASID_ANY = 1` reaches them
  G8  writing PTBR does not invalidate
  G9  `cause & 0xffff` masking: a cause id with sub-reason wyde(s) is still
      named and segmented like its class
  G10 a P = 0 entry produced by these primitives faults through the real supv
      entry and is recovered by the registered-probe channel

``--selfcheck`` mutates the captured run and shows every group flips.
``--inject`` corrupts the kernel source, rebuilds, asserts the named groups go
red, restores with ``cp`` + md5 and proves the image is green again.

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (spec / contract / image / build tree missing).
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

from tools.linux import k1_boot_probe as k1boot          # noqa: E402  (symbols)
from tools.linux import k2_trap_probe as k2trap         # noqa: E402  (cause table)
from tools.linux import make_defconfig as defconfig     # noqa: E402  (config slice)
from tools.linux import paths as linux_paths            # noqa: E402
from tools.qemu import k0_boot_probe as k0              # noqa: E402  (firmware, run)

TIMEOUT_QEMU = int(os.environ.get("K3_QEMU_TIMEOUT", "120"))
TIMEOUT_BUILD = int(os.environ.get("K3_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K3_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-011") / "k3_pt_probe")

#: The probe image pins every milestone boundary it depends on, so the shared
#: build tree cannot leak another image's configuration into this one.
IMAGE = [
    "CONFIG_DADAO_K1_EARLY_STOP=n",
    "CONFIG_DADAO_K2_EARLY_STOP=n",
    "CONFIG_DADAO_K2_TIME_STOP=n",
    "CONFIG_DADAO_K3_PT_SELFTEST=y",
]

SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
SPEC_DADAO13 = _REPO / "spec" / "DADAO-13-HEE-超管系统运行环境.md"
SPEC_MACHINE = _REPO / "spec" / "Kaiwu-测试机运行环境.md"
CONTRACT_TLB = _REPO / ".tao" / "contracts" / "contract-tlb.md"
SOURCE = linux_paths.linux_source_dir()


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
        order = [f"G{i}" for i in range(1, 11)]
        parts = []
        for group in order:
            if group in self.groups:
                total, failed = self.groups[group]
                parts.append(f"{group} {total - failed}/{total}")
        return "  ".join(parts)


# ---------------------------------------------------------------------------
# expectations parsed from spec / contract (never restated)
# ---------------------------------------------------------------------------

def _section(path: Path, start: str, end: str) -> str:
    text = path.read_text(encoding="utf-8")
    cut = text.split(start, 1)
    if len(cut) != 2:
        raise SystemExit(f"k3_pt_probe: '{start}' not found in {path.name}")
    return cut[1].split(end, 1)[0]


def spec_l1_fields() -> dict[str, tuple[int, int]]:
    """``{field: (low_bit, high_bit)}`` of the L1 entry table (``§2.2.3``)."""
    body = _section(SPEC_DADAO12, "#### 2.2.3 一级页表条目格式", "\n#### ")
    fields: dict[str, tuple[int, int]] = {}
    for line in body.splitlines():
        m = re.match(r"^\|\s*(?:bits?\[(\d+)(?::(\d+))?\]|bit(\d+))\s*\|"
                     r"\s*([^|]+)\|\s*([^|]+)\|", line)
        if not m:
            continue
        if m.group(3) is not None:          # `bitN` row
            high = low = int(m.group(3))
        else:
            high = int(m.group(1))
            low = int(m.group(2)) if m.group(2) else high
        fields[m.group(5).strip()] = (low, high)
    for required in ("PPN", "SPF", "G", "SP", "P"):
        if required not in fields:
            raise SystemExit(f"k3_pt_probe: §2.2.3 has no field {required!r}: "
                             f"{sorted(fields)}")
    return fields


def spec_normal_page() -> tuple[int, int]:
    """``(offset_bits, entries_per_level)`` from the normal-page walk (§2.2.2)."""
    body = _section(SPEC_DADAO12, "#### 2.2.2 普通页的地址转换", "\n#### ")
    m = re.search(r"`VA\[(\d+):0?0\]`\s*->\s*页内偏移", body)
    if not m:
        raise SystemExit("k3_pt_probe: §2.2.2 page-offset field not found")
    offset_bits = int(m.group(1)) + 1
    counts = [int(v) for v in re.findall(r"2\^(\d+)\s*个页表项", body)]
    if len(set(counts)) != 1:
        raise SystemExit(f"k3_pt_probe: §2.2.2 entry counts are not uniform: "
                         f"{counts}")
    return offset_bits, counts[0]


def contract_encoding() -> dict:
    """The three dimensions of ``cfx_ptw_tlb_control`` (contract-tlb TLB-19)."""
    text = CONTRACT_TLB.read_text(encoding="utf-8")
    m = re.search(r"TLB-19 \*\*编码\*\*：(.+)", text)
    if not m:
        raise SystemExit("k3_pt_probe: contract-tlb TLB-19 not found")
    line = m.group(1)

    ops = {}
    scope = {}
    ok, sk = re.search(r"`\[1:0\]` 操作 = (.+?)；", line), \
        re.search(r"`\[3:2\]` 地址范围 = (.+?)；", line)
    if not ok or not sk:
        raise SystemExit("k3_pt_probe: contract-tlb TLB-19 dimensions not parsed")
    for value, name in re.findall(r"(\d\d)=(\w+)", ok.group(1)):
        ops[name] = int(value, 2)
    for value, name in re.findall(r"(\d\d)=(\w+)", sk.group(1)):
        scope[name.lower()] = int(value, 2)
    m = re.search(r"`bit(\d+) = ASID_ANY`", line)
    if not m:
        raise SystemExit("k3_pt_probe: contract-tlb TLB-19 has no ASID_ANY bit")
    if set(ops) != {"none", "clean", "invalid", "flush"}:
        raise SystemExit(f"k3_pt_probe: TLB-19 ops parsed as {ops}")
    if set(scope) < {"all", "va", "range"}:
        raise SystemExit(f"k3_pt_probe: TLB-19 scopes parsed as {scope}")
    return {"op": ops, "scope": scope, "asid_any_bit": int(m.group(1)),
            "op_shift": 0, "scope_shift": 2}


def contract_asid_bits() -> int:
    text = CONTRACT_TLB.read_text(encoding="utf-8")
    m = re.search(r"`cfx_ptw_tlb_asid` 为 `cg12 rc1`（`\[(\d+):0\]`", text)
    if not m:
        raise SystemExit("k3_pt_probe: contract-tlb TLB-04 ASID width not found")
    return int(m.group(1)) + 1


def contract_subcause_masks() -> tuple[int, int]:
    """``(perm_wyde_mask, mem_wyde_mask)`` from contract-tlb TLB-34."""
    text = CONTRACT_TLB.read_text(encoding="utf-8")
    m = re.search(r"CFXPERM` 占 \*\*wyde2 `\[(\d+):32\]`", text)
    n = re.search(r"CFXMEM` 占 \*\*wyde3 `\[(\d+):48\]`", text)
    if not m or not n:
        raise SystemExit("k3_pt_probe: contract-tlb TLB-34 wyde归属 not found")
    perm_high, mem_high = int(m.group(1)), int(n.group(1))
    return 0xffff << (perm_high - 15), 0xffff << (mem_high - 15)


def kernel_marks() -> dict[str, int]:
    """The data-page markers of the self-test source."""
    path = SOURCE / "arch/dadao/mm/k3_pt_selftest.c"
    if not path.is_file():
        raise SystemExit(f"k3_pt_probe: {path} missing; run `make fetch "
                         f"apply-series`")
    out = {}
    for name, value in re.findall(r"^#define\s+(K3_MARK_\w+)\s+(0x[0-9a-fA-F]+)",
                                  path.read_text(encoding="utf-8"), re.MULTILINE):
        out[name] = int(value, 16)
    if set(out) != {"K3_MARK_X", "K3_MARK_Y"}:
        raise SystemExit(f"k3_pt_probe: markers parsed as {out}")
    return out


def kernel_selfcheck_codes() -> dict[str, int]:
    """Every self-check constant the K3 self-test defines (guest segment)."""
    path = SOURCE / "arch/dadao/mm/k3_pt_selftest.c"
    if not path.is_file():
        raise SystemExit(f"k3_pt_probe: {path} missing")
    return {name: int(value, 0) for name, value in
            re.findall(r"^#define\s+(K3_FAIL_\w+)\s+(0x[0-9a-fA-F]+)",
                       path.read_text(encoding="utf-8"), re.MULTILINE)}


def spec_exit_segments() -> dict:
    """The exit-code segments of ``spec/Kaiwu §7.1`` (parsed by the K2 gate)."""
    return k2trap.spec_exit_segments()


# ---------------------------------------------------------------------------
# build / run
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def config_text() -> str:
    return (build_dir() / ".config").read_text(encoding="utf-8")


def config_image() -> int:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k3_pt_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the K3 probe image (JOBS={JOBS})", flush=True)
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
            raise SystemExit("k3_pt_probe: the boot contract projection is empty")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        k0.WORK = str(SCRATCH / "bootrom")
        ROM = k0.build_firmware(k0.WORK)
    return ROM


def boot(tag: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k3_pt_probe: {kernel} missing; run "
                         f"`make linux-vmlinux`")
    rc, _blocks, err, _log = k0.run_qemu(k0.DEFAULT_QEMU, firmware(),
                                         str(kernel), f"k3_{tag}",
                                         dfilter="0x0+0x4", timeout=TIMEOUT_QEMU)
    if rc is None:
        return 124, err or ""
    return rc, err or ""


# ---------------------------------------------------------------------------
# output parsing
# ---------------------------------------------------------------------------

def kv(line: str) -> dict[str, str]:
    return dict(re.findall(r"(\w+)=(\S+)", line))


def lines_of(text: str, prefix: str) -> dict[str, dict[str, str]]:
    out = {}
    for line in text.splitlines():
        if line.startswith(prefix):
            row = kv(line)
            if row:
                out.setdefault(line.split()[2], row)
    return out


def one(text: str, prefix: str) -> dict[str, str]:
    rows = lines_of(text, prefix)
    if len(rows) != 1:
        raise SystemExit(f"k3_pt_probe: expected one '{prefix}' line, "
                         f"got {len(rows)}")
    return next(iter(rows.values()))


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check_image(rc: int, text: str, snap: dict, rep: Report) -> None:
    fields = spec_l1_fields()
    off_bits, per_level = spec_normal_page()
    enc = contract_encoding()
    asid_bits = contract_asid_bits()
    marks = kernel_marks()
    table = k2trap.spec_cause_table()
    cfxmem = next(cid for cid, name in table if name == "CFXMEM")
    specs = spec_exit_segments()
    cfg = snap["config"].splitlines()

    page_shift = next((int(line.split("=", 1)[1], 0) for line in cfg
                       if line.startswith("CONFIG_PAGE_SHIFT=")), -1)
    page_size = 1 << page_shift if page_shift > 0 else -1

    # ---- G1: this is the probe image, and its page size is §2.2.2's
    rep.check("G1", "镜像配置：K3 自检开", "CONFIG_DADAO_K3_PT_SELFTEST=y",
              next((line for line in cfg
                    if line.startswith("CONFIG_DADAO_K3_PT_SELFTEST=")), "<unset>"))
    rep.check("G1", "镜像配置：三条早停边界都关", [],
              [line for line in cfg
               if re.match(r"CONFIG_DADAO_K(1_EARLY_STOP|2_TIME_STOP|"
                           r"2_EARLY_STOP)=y", line)])
    rep.check("G1", "`.config` PAGE_SHIFT == §2.2.2 页内偏移位宽",
              off_bits, page_shift)
    rep.check("G1", "`.config` PTRS_PER_PTE 由 PAGE_SIZE/8 派生",
              page_size // 8, 1 << per_level)
    rep.check("G1", "镜像里有 K3 自检符号", True,
              "dadao_k3_pt_selftest" in snap.get("syms", {}))

    codes = kernel_selfcheck_codes()
    fail_low, fail_high = specs["ranges"]["guest"]
    rep.check("G1", f"自检码全在 guest FAIL 段 "
                    f"({hex(fail_low)}-{hex(fail_high)})", {},
              {name: hex(v) for name, v in codes.items()
               if not (fail_low <= v <= fail_high)})
    rep.stat(f"自检码 {len(codes)} 条：" +
             " ".join(f"{k.split('_')[-1]}={hex(v)}"
                      for k, v in sorted(codes.items())))

    # ---- G2: geometry
    geom = one(text, "K3 pt geom ")
    rep.check("G2", "PAGE_SHIFT", page_shift, int(geom["PAGE_SHIFT"], 0))
    rep.check("G2", "PAGE_SIZE", page_size, int(geom["PAGE_SIZE"], 0))
    rep.check("G2", "PTRS_PER_PTE", 1 << per_level,
              int(geom["PTRS_PER_PTE"], 0))
    rep.check("G2", "PTRS_PER_PGD", 1 << per_level,
              int(geom["PTRS_PER_PGD"], 0))
    rep.check("G2", "PGDIR_SHIFT == PAGE_SHIFT + log2(entries)",
              page_shift + per_level, int(geom["PGDIR_SHIFT"], 0))
    rep.check("G2", "PGDIR_SIZE == 1 << PGDIR_SHIFT",
              1 << (page_shift + per_level), int(geom["PGDIR_SIZE"], 0))
    rep.check("G2", "PTE_BYTES", 8, int(geom["PTE_BYTES"], 0))

    pages = one(text, "K3 pt pages ")
    l2_pa = int(pages["l2_pa"], 0)
    x_pa = int(pages["x_pa"], 0)
    y_pa = int(pages["y_pa"], 0)
    va = int(pages["va"], 0)
    pgdir_shift = page_shift + per_level
    ppn_low, ppn_high = fields["PPN"]
    ppn_mask = ((1 << (ppn_high - ppn_low + 1)) - 1) << ppn_low
    p_bit = 1 << fields["P"][0]
    sp_bit = 1 << fields["SP"][0]
    g_bit = 1 << fields["G"][0]
    spf_mask = ((1 << (fields["SPF"][1] - fields["SPF"][0] + 1)) - 1) << \
        fields["SPF"][0]
    s_bit = 1 << (fields["HSJU"][0] + 2)     # HSJU = H63 S62 J61 U60
    rwxad_mask = 0
    for name in ("R", "W", "X", "A", "D"):
        rwxad_mask |= 1 << fields[name][0]

    # ---- G3: the L1 entry the primitives build
    alloc = one(text, "K3 pt alloc ")
    entry = int(alloc["pte"], 0)
    rep.check("G3", "L1 index == pgd_index(va)",
              (va >> pgdir_shift) & ((1 << per_level) - 1), int(alloc["l1"], 0))
    rep.check("G3", "P", 1, (entry >> fields["P"][0]) & 1)
    rep.check("G3", "SP（非叶子）", 0, (entry >> fields["SP"][0]) & 1)
    rep.check("G3", "S（当前模式位）", s_bit, entry & s_bit)
    rep.check("G3", "G（非叶子须写 0）", 0, (entry >> fields["G"][0]) & 1)
    rep.check("G3", "SPF（非叶子须写 0）", 0, (entry & spf_mask) >> fields["SPF"][0])
    rep.check("G3", "R/W/X/A/D（非叶子不使用，须写 0）", 0,
              entry & rwxad_mask)
    rep.check("G3", f"PPN == L2 表 PA[${ppn_high}:{ppn_low}]",
              (l2_pa & ppn_mask) >> ppn_low, (entry & ppn_mask) >> ppn_low)
    rep.check("G3", "整条 L1 表项 == (l2_pa & PPN) | P | S",
              (l2_pa & ppn_mask) | p_bit | s_bit, entry)
    walk = one(text, "K3 pt alloc-walk ")
    rep.check("G3", "走过 L1 表项落到 L2 表页",
              l2_pa + ((va >> page_shift) & ((1 << per_level) - 1)) * 8,
              int(walk["ptep_pa"], 0))

    # ---- G4: mapping, staleness, clean, flush
    m_map = one(text, "K3 pt map ")
    rep.check("G4", "新映射读到 X 页标记", marks["K3_MARK_X"],
              int(m_map["word"], 0))
    rep.check("G4", "L2 PTE 的 PPN == X 页 PA", (x_pa & ppn_mask) >> ppn_low,
              (int(m_map["pte"], 0) & ppn_mask) >> ppn_low)

    stale = one(text, "K3 pt stale ")
    rep.check("G4", "改 PTE 不失效 ⇒ 仍读旧页", marks["K3_MARK_X"],
              int(stale["word"], 0))
    rep.check("G4", "PTE 已指向 Y 页（不是缓存假象）",
              (y_pa & ppn_mask) >> ppn_low, int(stale["pte_ppn"], 0))

    inval = one(text, "K3 pt inval_va ")
    rep.check("G4", "invalid|VA ⇒ 读到新页", marks["K3_MARK_Y"],
              int(inval["word"], 0))
    rep.check("G4", "命令值 == invalid|VA|ASID_ANY",
              enc["op"]["invalid"] | enc["scope"]["va"] << enc["scope_shift"]
              | 1 << enc["asid_any_bit"], int(inval["cmd"], 0))

    clean = one(text, "K3 pt ad_clean ")
    rep.check("G4", "clean 前 PTE.A 仍为 0（填充不回写）", 0,
              int(clean["a_before"], 0))
    rep.check("G4", "clean 后 PTE.A == 1（回写）", 1, int(clean["a_after"], 0))
    rep.check("G4", "clean 后 PTE.D 仍为 0（未写）", 0, int(clean["d_after"], 0))
    rep.check("G4", "clean 保留条目 ⇒ 仍读旧页", 1, int(clean["kept_old"], 0))

    flush = one(text, "K3 pt flush ")
    rep.check("G4", "flush 回写 A", 1, int(flush["a"], 0))
    rep.check("G4", "flush 回写 D", 1, int(flush["d"], 0))
    rep.check("G4", "flush 删条目 ⇒ 再访问走步进", 1, int(flush["refill_new"], 0))

    # ---- G5: the (op, scope) matrix
    matrix = lines_of(text, "K3 pt m_")
    for op in ("none", "clean", "invalid", "flush"):
        for scope in ("all", "va", "range"):
            name = f"m_{op}_{scope}"
            row = matrix.get(name)
            cid = f"G5"
            if row is None:
                rep.check(cid, f"{name} 行存在", "存在", "缺失")
                continue
            deletes = op in ("invalid", "flush")
            rep.check(cid, f"{name} 结果", "new" if deletes else "old",
                      "new" if int(row["word"], 0) == marks["K3_MARK_Y"]
                      else "old")
            rep.check(cid, f"{name} PTE.A", 1 if op in ("clean", "flush") else 0,
                      int(row["a"], 0))
            rep.check(cid, f"{name} 命令值",
                      enc["op"][op] | enc["scope"][scope] << enc["scope_shift"]
                      | 1 << enc["asid_any_bit"], int(row["cmd"], 0))
            rep.check(cid, f"{name} 内核自评", 1, int(row["ok"], 0))

    # ---- G4 (continued): the flush_tlb_* helpers, one per scope
    ranges = one(text, "K3 pt ranges ")
    rep.check("G4", "kernel_range 失效后读到新页", 1, int(ranges["krq_new"], 0))
    rep.check("G4", "flush_tlb_range（内核 VA）后读到新页", 1,
              int(ranges["vma_new"], 0))
    rep.check("G4", "空 range 不下发命令（size=0 会是 CFXREG），条目保留", 1,
              int(ranges["empty_old"], 0))
    rep.check("G4", "flush_tlb_mm(init_mm) 走 ASID_ANY 全失效", 1,
              int(ranges["mm_new"], 0))

    # ---- G6: ASID register and allocator
    asid = one(text, "K3 pt asid ")
    rep.check("G6", "ASID [63:16] 读 0（写宽值被截到 16 位）",
              (1 << asid_bits) - 1, int(asid["raw"], 0))
    rep.check("G6", "ASID 读回 == 写入值", (1 << asid_bits) - 1,
              int(asid["read"], 0))
    first, second = (int(v, 0) for v in asid["alloc"].split(","))
    rep.check("G6", "分配器从不发 0（内核保留）", 0,
              int(first == 0) + int(second == 0))
    rep.check("G6", "两个 mm 的 ASID 不同", 1, int(first != second))
    rep.check("G6", "init_new_context 写入了非 0 ASID", 1,
              int(int(asid["mm_asid"], 0) != 0))
    rep.check("G6", "invalid|all|ASID_ANY=0 的命令值",
              enc["op"]["invalid"] | enc["scope"]["all"] << enc["scope_shift"],
              int(asid["cmd0"], 0))

    # ---- G7: ASID_ANY vs G
    asg = one(text, "K3 pt asid_g ")
    rep.check("G7", "ASID_ANY=0 不动 G=1 条目", 1,
              int(asg["any0_global_old"], 0))
    rep.check("G7", "ASID_ANY=0 删掉 G=0 条目", 1,
              int(asg["any0_local_new"], 0))
    rep.check("G7", "ASID_ANY=1 删掉 G=1 条目", 1,
              int(asg["any1_global_new"], 0))
    rep.check("G7", "ASID_ANY=0 的命令值（bit4=0）",
              enc["op"]["invalid"] | enc["scope"]["all"] << enc["scope_shift"]
              | 0, int(asg["cmd0"], 0))
    rep.check("G7", "ASID_ANY=1 的命令值（bit4=1）",
              enc["op"]["invalid"] | enc["scope"]["all"] << enc["scope_shift"]
              | 1 << enc["asid_any_bit"], int(asg["cmd1"], 0))

    # ---- G8: writing PTBR does not invalidate
    ptbr = one(text, "K3 pt ptbr_no_inval ")
    rep.check("G8", "写 PTBR 同值 ⇒ 条目仍命中（读旧页）", 1,
              int(ptbr["old"], 0))

    # ---- G9: cause masking
    cause = one(text, "K3 pt cause ")
    name = next(n for cid, n in table if cid == cfxmem)
    rep.check("G9", "裸 cause 的名字", name, cause["bare"])
    rep.check("G9", "带子原因位的 cause 仍被认出", name, cause["masked"])
    rep.check("G9", "退出码分段不看子原因位", int(cause["exit_bare"], 0),
              int(cause["exit_masked"], 0))
    perm_mask, mem_mask = contract_subcause_masks()
    sub = int(cause["sub"], 0)
    rep.check("G9", "子原因只落在 wyde2/wyde3（contract-tlb TLB-34）",
              [True, True, True],
              [bool(sub & perm_mask), bool(sub & mem_mask),
               not (sub & ~(perm_mask | mem_mask))])
    rep.check("G9", "大类 == cause_id[15:0]", cfxmem,
              int(cause["class"], 0) & 0xffff)

    # ---- G10: the P = 0 path faults through the real entry
    for tag in ("neg_l2", "neg_l1"):
        neg = one(text, f"K3 pt {tag} ")
        rep.check("G10", f"{tag}：命中注册探针一次", 1, int(neg["hits"], 0))
        rep.check("G10", f"{tag}：cause == {name}", name, neg["cause"])
        rep.check("G10", f"{tag}：通道恢复执行", 1, int(neg["resumed"], 0))

    # ---- the run itself
    rep.check("G10", "guest rc（SYS_EXIT 子码）", 0, rc)
    rep.check("G10", "最后一行是自检完成行", True,
              bool([line for line in text.splitlines() if line.strip()]) and
              text.splitlines()[-1].strip().startswith("K3 pt done:"))
    done = [line for line in text.splitlines() if line.startswith("K3 pt done:")]
    if done:
        row = kv(done[-1])
        rep.check("G10", "matrix 覆盖全部 12 组（3 scope × 4 op）", 12,
                  int(row.get("matrix", 0)))
        rep.check("G10", "自检 case 数", 8, int(row.get("cases", 0)))
        rep.check("G10", "失败计数", 0, int(row.get("fail", -1)))


# ---------------------------------------------------------------------------
# --selfcheck: every group must be able to go red
# ---------------------------------------------------------------------------

#: (group, line prefix, field, replacement) — one mutation per group.
SELFCHECK = {
    "G2": ("K3 pt geom ", "PAGE_SHIFT", lambda v: str(int(v, 0) - 1)),
    "G3": ("K3 pt alloc ", "pte", lambda v: hex(int(v, 0) ^ 0x1)),
    "G4": ("K3 pt inval_va ", "word", lambda v: "0x0"),
    "G5": ("K3 pt m_invalid_va ", "cmd", lambda v: hex(int(v, 0) ^ 0x02)),
    "G6": ("K3 pt asid ", "raw", lambda v: "0x0"),
    "G7": ("K3 pt asid_g ", "any1_global_new", lambda v: "0"),
    "G8": ("K3 pt ptbr_no_inval ", "old", lambda v: "0"),
    "G9": ("K3 pt cause ", "masked", lambda v: "unknown"),
    "G10": ("K3 pt neg_l2 ", "hits", lambda v: "0"),
}


def mutate(text: str, group: str) -> str:
    prefix, field, fn = SELFCHECK[group]
    out = []
    done = False
    for line in text.splitlines():
        if not done and line.startswith(prefix):
            line = re.sub(rf"(\b{re.escape(field)}=)(\S+)",
                          lambda m: m.group(1) + fn(m.group(2)), line, count=1)
            done = True
        out.append(line)
    if not done:
        raise SystemExit(f"k3_pt_probe: --selfcheck: no '{prefix}' line")
    return "\n".join(out) + "\n"


def run_selfcheck(text: str, snap: dict) -> int:
    problems: list[str] = []
    for group in SELFCHECK:
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                check_image(0, mutate(text, group), snap, rep)
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
        print("k3_pt_probe: --selfcheck FAIL: " + "; ".join(problems),
              file=sys.stderr)
        return 1
    print(f"k3_pt_probe: --selfcheck PASS ({len(SELFCHECK)}/{len(SELFCHECK)})")
    return 0


# ---------------------------------------------------------------------------
# --inject: corrupt the kernel, rebuild, expect red, restore, expect green
# ---------------------------------------------------------------------------

PTW_H = "arch/dadao/include/asm/ptw.h"
TLBFLUSH_H = "arch/dadao/include/asm/tlbflush.h"
PGALLOC_H = "arch/dadao/include/asm/pgalloc.h"
PGTABLE_H = "arch/dadao/include/asm/pgtable.h"
TRAPS_C = "arch/dadao/kernel/traps.c"

INJECTIONS = {
    # ② (the mandatory one) the pre-fix value: the L1 entry carries the table's
    #    kernel VA instead of its PA — `page_to_virt()` is exactly that value.
    "l1-write-va": (
        PGALLOC_H,
        "\treturn __pa(table) | _PAGE_PRESENT | _PAGE_S;\n",
        "\treturn (unsigned long)table | _PAGE_PRESENT | _PAGE_S;\n",
        ("G3",),
    ),
    # ① non-leaf SPF written as "all fragments": §2.2.3/TLB-27 require 0.
    "l1-spf-nonzero": (
        PGALLOC_H,
        "\treturn __pa(table) | _PAGE_PRESENT | _PAGE_S;\n",
        "\treturn __pa(table) | _PAGE_PRESENT | _PAGE_S | _PAGE_FRAG_ALL;\n",
        ("G3",),
    ),
    # ④ invalid encoded as clean: the entry survives the "invalidation".
    "invalid-as-clean": (
        PTW_H,
        "\tDADAO_TLB_INVALID\t= 2,\n\tDADAO_TLB_FLUSH\t\t= 3,\n",
        "\tDADAO_TLB_INVALID\t= 1,\n\tDADAO_TLB_FLUSH\t\t= 3,\n",
        ("G4",),
    ),
    # scope bits moved to [4:3]: every command value is wrong and a VA command
    # becomes a range command with size 0 (CFXREG).
    "scope-shift": (
        PTW_H,
        "#define DADAO_TLB_CTRL_SCOPE_SHIFT\t2\n",
        "#define DADAO_TLB_CTRL_SCOPE_SHIFT\t3\n",
        ("G4",),
    ),
    # ③ the page flush forgets that the kernel's mappings are G = 1: with
    #    ASID_ANY = 0 the G = 1 entry survives its own invalidation.
    "page-any-off": (
        TLBFLUSH_H,
        "\t\t__dadao_tlb_flush(DADAO_TLB_INVALID, DADAO_TLB_SCOPE_VA, addr, 0,\n"
        "\t\t\t\t  0, true);\n",
        "\t\t__dadao_tlb_flush(DADAO_TLB_INVALID, DADAO_TLB_SCOPE_VA, addr, 0,\n"
        "\t\t\t\t  0, false);\n",
        ("G4",),
    ),
    # ASID_ANY shifted: the kernel issues an ASID-scoped command for a G = 1
    # mapping, so the entry is never dropped.
    "asid-any-shift": (
        PTW_H,
        "#define DADAO_TLB_CTRL_ASID_ANY_SHIFT\t4\n",
        "#define DADAO_TLB_CTRL_ASID_ANY_SHIFT\t5\n",
        ("G4",),
    ),
    # ③ cause masking removed from the name lookup: a sub-reason-carrying id
    #    falls out of the table as "unknown".
    "cause-mask-off": (
        TRAPS_C,
        "\tcause = DADAO_CAUSE_CLASS(cause);\n\tfor (i = 0;",
        "\t/* injected: no class mask */\n\tfor (i = 0;",
        ("G9",),
    ),
    # ⑥ the page-size assertion itself: a 15-bit page build must not compile.
    "page-shift-15": (
        PGTABLE_H,
        "#if PAGE_SHIFT != 16\n",
        "#if PAGE_SHIFT != 15\n",
        ("G1", "G2"),
    ),
}


def run_inject(name: str, problems: list[str]) -> None:
    rel, old, new, want_groups = INJECTIONS[name]
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
        rc_build = config_image()
        if rc_build != 0:
            # A build failure is the intended red for the compile-time
            # assertion; otherwise it is a problem of the injection itself.
            ok = name == "page-shift-15"
            print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} 构建 rc={rc_build}"
                  f" | 期望={'非 0（编译期断言）' if ok else '0'}", flush=True)
            if not ok:
                problems.append(f"inject:{name}: 重建 rc={rc_build}")
        else:
            rep = Report(quiet=True)
            rc, boot_text = boot(f"inject_{name}")
            snap = {"config": config_text(),
                    "syms": k1boot.symbols(kernel_path())}
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    check_image(rc, boot_text, snap, rep)
                except SystemExit as exc:
                    # A line the kernel no longer reaches (it stopped earlier)
                    # is a red for the groups that line belongs to.
                    for group in want_groups:
                        rep.fails.append(f"{group} 行缺失: {exc}")
            print(f"---- guest tail ({name}, rc={rc}) ----", flush=True)
            print(boot_text.strip()[-1200:], flush=True)
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

    rc_build = config_image()
    if rc_build != 0:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    rep = Report(quiet=True)
    rc, boot_text = boot(f"inject_{name}_green")
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            check_image(rc, boot_text,
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
    ap = argparse.ArgumentParser(description="K3 page-table/TLB primitive gate")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured run; every group must flip")
    ap.add_argument("--inject", nargs="*", metavar="NAME",
                    help="corrupt the kernel, rebuild, expect red, restore")
    ap.add_argument("--list", action="store_true", help="list injections")
    ap.add_argument("--no-build", action="store_true",
                    help="reuse the current image (no configure/build)")
    args = ap.parse_args()

    if args.list:
        print("\n".join(INJECTIONS))
        return 0

    if args.inject is not None:
        names = args.inject or list(INJECTIONS)
        unknown = [n for n in names if n not in INJECTIONS]
        if unknown:
            print(f"k3_pt_probe: unknown injection(s): {unknown}", file=sys.stderr)
            return 2
        problems: list[str] = []
        for name in names:
            print(f"[INFO] injection {name}", flush=True)
            run_inject(name, problems)
        total = len(names)
        if problems:
            print("k3_pt_probe: --inject FAIL: " + "; ".join(problems),
                  file=sys.stderr)
            return 1
        print(f"k3_pt_probe: --inject PASS ({total}/{total})")
        return 0

    if not args.no_build:
        rc = config_image()
        if rc != 0:
            print(f"k3_pt_probe: FAIL: build rc={rc}", file=sys.stderr)
            return 1
    snap = {"config": config_text()}
    snap["syms"] = k1boot.symbols(kernel_path())
    rc, text = boot("gate")

    if args.selfcheck:
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                check_image(rc, text, snap, rep)
            except SystemExit as exc:
                print(f"k3_pt_probe: FAIL: {exc}", file=sys.stderr)
                return 1
        if rep.fails:
            print("k3_pt_probe: FAIL: the captured run is not green: "
                  f"{rep.fails[0]}", file=sys.stderr)
            return 1
        print("[INFO] 捕获的镜像运行全绿；逐组变异：", flush=True)
        return run_selfcheck(text, snap)

    rep = Report()
    try:
        check_image(rc, text, snap, rep)
    except SystemExit as exc:
        print(f"k3_pt_probe: FAIL: {exc}", file=sys.stderr)
        return 1
    print("================================================================")
    if rep.fails:
        print(f"k3_pt_probe: FAIL ({len(rep.fails)}/{rep.total})", file=sys.stderr)
        return 1
    print(f"k3_pt_probe: PASS ({rep.total}/{rep.total})  {rep.summary()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
