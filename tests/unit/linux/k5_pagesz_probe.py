#!/usr/bin/env python3
"""k5_pagesz_probe.py — M14 user-visible 64 KiB page ABI probe (`m14-linux-028`).

The kernel half is `arch/dadao/kernel/k5_pagesz_selftest.c` (plus the trap hook
in `kernel/process.c` and the probe-only reservation in `kernel/setup.c`),
built as an image with `CONFIG_DADAO_K5_PAGESZ_SELFTEST`; this gate builds that
image, boots it on Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from:

  A1  the auxv `create_elf_tables()` writes for an `execve`d program carries
      `AT_PAGESZ == PAGE_SIZE` (the probe reads it back off that stack, not from
      the kernel's copy) and `AT_ENTRY`/`AT_PHDR`/`AT_PHENT`/`AT_PHNUM` agree
      with the ELF file.  The expected page size is derived twice: from the
      image's `.config` (`CONFIG_PAGE_SIZE_64KB`) and from `spec/DADAO-12
      §2.2.2`'s page-offset field (`VA[15:00]`, 16 bits) - the two must agree.
  A2  a non-`MAP_FIXED` `mmap` made from user mode returns a page-aligned
      address, its length is rounded up to whole pages, `munmap` releases it,
      `mprotect` replaces the protection, and the *minimum* mappable address is
      a page boundary (generic Kconfig's 4096 is not, on this machine).
  A3  every `PT_LOAD` of the exec'd program is mapped page-aligned at its
      `p_vaddr` with the file's bytes in place and `p_align >= PAGE_SIZE`.
      The number of segments the kernel reports must equal the number in the
      image's `/init.musl` (read from the built initramfs).
  A4  `brk(0)` reads the page-aligned break, an aligned and an unaligned growth
      both map whole pages, and an access one page past the break reaches the
      fault channel and ends the task in SIGSEGV (`m14-linux-027`'s path).
  A5  `/proc/buddyinfo` has one column per buddy order - so the largest order
      is `ARCH_FORCE_MAX_ORDER` - and an allocation of exactly that order
      succeeds.  `PAGE_SIZE << MAX_PAGE_ORDER` must equal the spec's superpage
      size (`spec/DADAO-12 §2.2.1`, 512 MiB): that is the user's ruling of
      2026-11-20 made measurable.

The image reserves one `MAX_PAGE_ORDER`-sized chunk of RAM at boot
(`kernel/setup.c`, probe-only) because a boot-time top-order request only
succeeds when a whole 2^order-aligned chunk is still free, and Vast's 2 GiB do
not leave one (the boot's own migratetype fallbacks take one page at the start
of every 512 MiB-aligned region).  The probe releases the chunk, reads
`/proc/buddyinfo` and allocates it back.

Exit status: 0 = every case passed; 1 = at least one FAIL; 2 = an input could
not be derived (kernel source / spec / build tree / toolchain missing).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                          # noqa: E402  (pins)
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("K5P_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-028") / "check-linux-k5p")
SOURCE = linux_paths.linux_source_dir()
SPEC_PAGING = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
KCONFIG = _REPO / "components" / "linux" / "patches" / "arch" / "dadao" / \
    "Kconfig.patch"

#: Every milestone boundary pinned off, and only this probe compiled in
#: (`make check-config-pins`, ISS-470; an int pinned ``"n"`` is "left unset"
#: because its `depends on` is not met).
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
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "y",
}

TIMEOUT_BUILD = int(os.environ.get("K5P_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K5P_QEMU_TIMEOUT", "240"))
JOBS = os.environ.get("JOBS", "32")

#: The check names each case must report, once each (the `a3_load_*` ones are
#: reported once per `PT_LOAD`, so they are checked separately).
CASES = {
    "A1": ("a1_exec_ok", "a1_entry_ip", "a1_sp_aligned", "a1_pagesz",
           "a1_pagesz_once", "a1_entry", "a1_phent", "a1_phnum",
           "a1_phdr_addr", "a1_phdr_content"),
    "A2": ("a2_mmap_min_addr_aligned", "a2_mmap_a_aligned",
           "a2_mmap_b_aligned", "a2_mmap_distinct", "a2_munmap_rc",
           "a2_munmap_released", "a2_mmap_b_mapped", "a2_mmap_b_len",
           "a2_mprotect_ro", "a2_mprotect_rc"),
    "A3": ("a3_elf_read", "a3_elf_magic", "a3_elf_type", "a3_elf_phdrs"),
    "A4": ("a4_brk_initial", "a4_brk_initial_aligned", "a4_brk_grow",
           "a4_brk_reread", "a4_brk_reread_aligned", "a4_brk_unaligned",
           "a4_brk_recheck", "a4_mm_brk", "a4_heap_vma", "a4_report_seen",
           "a4_child_zombie", "a4_child_sigsegv", "a4_child_no_status",
           "a4_fault_novma"),
    "A5": ("a5_reserved_chunk", "a5_chunk_aligned", "a5_proc_mount",
           "a5_top_order_free", "a5_alloc_largest", "a5_alloc_aligned",
           "a5_alloc_bytes", "a5_buddyinfo_read", "a5_buddyinfo_orders"),
}

#: Per-`PT_LOAD` checks (one set per segment).
LOAD_CHECKS = ("a3_load_align", "a3_load_vma", "a3_load_vma_page_aligned",
               "a3_load_vma_len", "a3_load_bytes")

#: The syscalls the stub issues, by the name the locked table uses.
STUB_SYSCALLS = ("mmap", "munmap", "mprotect", "brk")


class Report:
    def __init__(self) -> None:
        self.total = 0
        self.failed: list[str] = []

    def check(self, group: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        print(f"[{'PASS' if ok else 'FAIL'}] {group}: {name}: "
              f"want={expected!r} got={actual!r}")
        if not ok:
            self.failed.append(f"{group}: {name}")
        return ok

    def info(self, text: str) -> None:
        print(f"[INFO] {text}")


# ---------------------------------------------------------------------------
# derivations (never a literal: the owner of each fact is parsed)
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"k5_pagesz_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def spec_paging() -> dict:
    """`spec/DADAO-12 §2.2.2` page offset + `§2.2.1` superpage size."""
    if not SPEC_PAGING.is_file():
        raise SystemExit(f"k5_pagesz_probe: spec missing: {SPEC_PAGING.name}")
    text = SPEC_PAGING.read_text(encoding="utf-8")
    sec = text[text.index("#### 2.2.2"):]
    sec = sec[:sec.index("#### ", 8)]
    m = re.search(r"`VA\[15:00\]`.*?页内偏移为\s*(\d+)\s*位", sec)
    m2 = re.search(r"`VA\[(\d+):00\]`\s*->\s*页内偏移", sec)
    if not m and not m2:
        raise SystemExit("k5_pagesz_probe: spec §2.2.2 has no page-offset width")
    shift = int(m.group(1)) if m else int(m2.group(1))
    page_size = 1 << shift
    m = re.search(r"超页\s*(\d+)\s*MiB", text)
    if not m:
        raise SystemExit("k5_pagesz_probe: spec §2.2.1 has no superpage size")
    return {"shift": shift, "size": page_size,
            "superpage": int(m.group(1)) * 1024 * 1024}


def arch_max_order() -> int:
    """`ARCH_FORCE_MAX_ORDER`'s default, from the port's Kconfig fragment."""
    text = KCONFIG.read_text(encoding="utf-8")
    m = re.search(r"^\+config ARCH_FORCE_MAX_ORDER\n\+\tint[^\n]*\n"
                  r"\+\tdefault (\d+)", text, re.M)
    if not m:
        raise SystemExit("k5_pagesz_probe: Kconfig has no ARCH_FORCE_MAX_ORDER "
                         "default")
    return int(m.group(1))


def syscall_table_snapshot() -> dict:
    """`contract-syscall §1.2`: the locked table snapshot, sha256 verified."""
    contract = _REPO / ".tao" / "contracts" / "contract-syscall.md"
    text = contract.read_text(encoding="utf-8")
    m = re.search(r"`linux-user/riscv/syscall\.tbl`\s*\|\s*`([0-9a-f]{64})`", text)
    if not m:
        raise SystemExit("k5_pagesz_probe: contract-syscall §1.2 has no "
                         "snapshot hash")
    want = m.group(1)
    lock = (_REPO / "manifests" / "components.lock.toml").read_text(encoding="utf-8")
    root = re.search(r'^work_root\s*=\s*"([^"]+)"', lock, re.M)
    if not root:
        raise SystemExit("k5_pagesz_probe: components.lock.toml has no work_root")
    tbl = (_REPO / root.group(1) / "source" / "qemu" / "linux-user" / "riscv" /
           "syscall.tbl")
    if not tbl.is_file():
        raise SystemExit(f"k5_pagesz_probe: snapshot missing: {tbl}")
    got = hashlib.sha256(tbl.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit("k5_pagesz_probe: the vendored syscall.tbl no longer "
                         f"matches contract-syscall §1.2 ({got[:12]} != {want[:12]})")
    table: dict[str, list[int]] = {}
    for line in tbl.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        nr, abi, name = int(parts[0]), parts[1], parts[2]
        if abi in ("common", "64"):
            table.setdefault(name, []).append(nr)
    return {name: sorted(v)[0] for name, v in table.items() if v}


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    value = config_value(config, symbol)
    return value is not None and value not in ("n", "0", "")


# ---------------------------------------------------------------------------
# the built image
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def tool(name: str) -> str:
    return str(linux_paths.toolchain_bin() / name)


def symbols(elf: Path) -> dict[str, int]:
    out = subprocess.run([tool("llvm-nm"), str(elf)], capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise SystemExit(f"k5_pagesz_probe: llvm-nm failed: {out.stderr.strip()}")
    table = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            table[parts[2]] = int(parts[0], 16)
    return table


def pt_load_count() -> int | None:
    """PT_LOAD segments of the image's `/init.musl` (the A3 count)."""
    init = Path(linux_paths.linux_initramfs_dir()) / "init.musl"
    if not init.is_file():
        return None
    data = init.read_bytes()[:4096]
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 2:   # ELF64, MSB
        return None
    e_phoff, = struct.unpack(">Q", data[32:40])
    e_phentsize, e_phnum = struct.unpack(">HH", data[54:58])
    if e_phoff + e_phentsize * e_phnum > len(data):
        return None
    return sum(1 for i in range(e_phnum)
               if struct.unpack(">I", data[e_phoff + i * e_phentsize:
                                           e_phoff + i * e_phentsize + 4])[0] == 1)


def elf_section(elf: Path, name: str) -> tuple[int, int, int]:
    """(address, file offset, size) of a section, from `llvm-readelf -S`."""
    out = subprocess.run([tool("llvm-readelf"), "-S", str(elf)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"k5_pagesz_probe: llvm-readelf failed: "
                         f"{out.stderr.strip()}")
    for line in out.stdout.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-fA-F]+)\s+"
                     r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", line)
        if m and m.group(1) == name:
            return int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)
    raise SystemExit(f"k5_pagesz_probe: section {name} not found in {elf.name}")


def stub_oracle(elf: Path) -> list[int]:
    """Every `trap cfx_umon` immediate of `dadao_k5p_user_stub`, in order.

    Derived from the built image, not from the kernel's own table: the symbol's
    bytes are taken out of `.rodata` and run through the toolchain's decoder, so
    a moved or re-numbered trap shows up as a mismatch instead of agreeing with
    the kernel's expectation.
    """
    syms = symbols(elf)
    for name in ("dadao_k5p_user_stub", "dadao_k5p_user_stub_end"):
        if name not in syms:
            raise SystemExit(f"k5_pagesz_probe: {name} not in {elf.name}")
    start, end = syms["dadao_k5p_user_stub"], syms["dadao_k5p_user_stub_end"]
    addr, off, size = elf_section(elf, ".rodata")
    if not (addr <= start and end <= addr + size):
        raise SystemExit("k5_pagesz_probe: the stub is not inside .rodata")
    blob = elf.read_bytes()[off + (start - addr):off + (end - addr)]
    words = [blob[i:i + 4] for i in range(0, len(blob) - 3, 4)]
    listing = "".join(" ".join(f"0x{b:02x}" for b in w) + "\n" for w in words)
    out = subprocess.run([tool("llvm-mc"), "-triple=dadao", "--disassemble"],
                         input=listing, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"k5_pagesz_probe: llvm-mc --disassemble failed: "
                         f"{out.stderr.strip()}")
    lines = out.stdout.splitlines()
    if len(lines) != len(words):
        raise SystemExit("k5_pagesz_probe: the decoder returned a different "
                         f"instruction count ({len(lines)} != {len(words)})")
    traps = []
    for line in lines:
        m = re.match(r"\s*trap\s+cfx_umon,\s*(\d+)", line)
        if m:
            traps.append(int(m.group(1)))
    if not traps:
        raise SystemExit("k5_pagesz_probe: no trap instruction in the stub")
    return traps


# ---------------------------------------------------------------------------
# console parsing
# ---------------------------------------------------------------------------

_CHECK_RE = re.compile(r"^K5P check (\S+) want=(\S+) got=(\S+) (.*?)(ok|FAIL)$")


def check_lines(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for line in text.splitlines():
        m = _CHECK_RE.match(line.strip())
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(5)}))
    return out


def value_of(rows: list[tuple[str, dict[str, str]]], name: str) -> str | None:
    for got_name, row in rows:
        if got_name == name:
            return row["got"]
    return None


def one(text: str, prefix: str) -> dict[str, str] | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return dict(token.split("=", 1) for token in line.split()
                        if "=" in token)
    return None


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

CUR: dict = {"config": None}


def image_lines() -> list[str]:
    """The probe image's config slice, with the allocator orders derived."""
    order = arch_max_order()
    # `ARCH_FORCE_MAX_ORDER`'s default comes from the port's Kconfig; a build
    # tree that once had another value keeps it in `.config`, so the image
    # states it.  `config_lines()` already caps the *pageblock* order (generic
    # 64 MiB, see `config_pins`), which is the value this port measures with.
    return config_pins.config_lines(CONFIG_PINS) + [
        f"CONFIG_ARCH_FORCE_MAX_ORDER={order}",
    ]


def build_image(label: str = "k5p") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(image_lines())
    if rc != 0:
        print(f"k5_pagesz_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k5_pagesz_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k5p.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k5_pagesz_probe: {kernel} missing")
    qemu = tool("qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k5_pagesz_probe: qemu-system-dadao missing "
                         "(make install-host)")
    log_dir = SCRATCH / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={rom}", "-nographic",
           "-semihosting-config", "enable=on,target=native", "-kernel",
           str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = (err or "") + (out or "")
    (log_dir / f"{tag}.log").write_text(text, encoding="utf-8")
    return rc, text


# ---------------------------------------------------------------------------
# judging
# ---------------------------------------------------------------------------

def judge(rep: Report, text: str, rc: int, oracle: list[int] | None = None,
          suffix: str = "") -> None:
    """The console of one probe run -> one verdict per case."""
    s = suffix
    geo = spec_paging()
    order = arch_max_order()
    rows = check_lines(text)

    rep.check(f"B{s}", "镜像跑到 K5P 自检", True, "K5P selftest: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5P selftest FAIL")])
    rep.check(f"B{s}", "内核没有 vfree 风暴（延迟释放队列完好）", 0,
              text.count("Trying to vfree() nonexistent vm area"))
    rep.check(f"B{s}", "内核自评的每条 K5P check 都 ok", [],
              [name for name, row in rows if row["verdict"] != "ok"])

    seen = [name for name, _ in rows]
    for case, names in CASES.items():
        missing = [n for n in names if n not in seen]
        rep.check(f"{case}{s}", f"{case} 的断言都报了（{len(names)} 条）", [],
                  missing)

    # A3's per-segment checks: all present, and as many as the program has.
    loads = pt_load_count()
    rep.check(f"A3{s}", "镜像的 /init.musl 可读（PT_LOAD 数可派生）", True,
              loads is not None and loads > 0)
    for name in LOAD_CHECKS:
        rep.check(f"A3{s}", f"{name} 报了 {loads} 次（每段一次）", loads,
                  len([n for n in seen if n == name]))

    # Echo the two console lines the derived values are compared with, so the
    # evidence log carries the kernel's own numbers next to the verdicts.
    for line in text.splitlines():
        if line.startswith(("K5P auxv:", "K5P alloc:", "K5P buddyinfo:")):
            rep.info(f"console: {line.strip()}")

    # A1/A5: the page size the auxv carries is the machine's (spec + .config),
    # and the largest order really is one superpage.
    rep.check(f"A1{s}", "AT_PAGESZ 现场值 == spec/.config 的页大小",
              hex(geo["size"]), value_of(rows, "a1_pagesz"))
    rep.check(f"A1{s}", "AT_PAGESZ 只出现一次", "0x1",
              value_of(rows, "a1_pagesz_once"))
    top = value_of(rows, "a5_buddyinfo_orders")
    rep.check(f"A5{s}", "PAGE_SIZE << MAX_PAGE_ORDER == spec 的超页大小",
              hex(geo["superpage"]), hex(geo["size"] << order))
    rep.check(f"A5{s}", "512 MiB 粒度分配成功（bytes）", hex(geo["superpage"]),
              value_of(rows, "a5_alloc_bytes"))
    rep.check(f"A5{s}", "最大阶有成功分配（order 13 的一次请求）", "0x1",
              value_of(rows, "a5_alloc_largest"))
    if top:
        rep.check(f"A5{s}", "buddyinfo 列数 == MAX_PAGE_ORDER + 1",
                  hex(order + 1), top)

    # The stub's trap stream against the disassembly-derived oracle (the
    # dispatcher's immediate parse and the program's trap sequence).
    report = one(text, "K5P report:")
    if oracle:
        rep.info(f"stub oracle: {[hex(v) for v in oracle]}")
        rep.check(f"A4{s}", "trap 条数 == stub 里的 trap 条数", len(oracle),
                  int(report["traps"]) if report else None)
        if report:
            got = [int(v, 0) for v in report.get("immu", "").split(",") if v]
            rep.check(f"A4{s}", "每条 trap 的 immu18 == 反汇编的立即数",
                      oracle, got)

    # A4: the child's death is the fault channel's, with SIGSEGV and no status.
    rep.check(f"A4{s}", "子任务死于 SIGSEGV", "0xb",
              value_of(rows, "a4_child_sigsegv"))
    rep.check(f"A4{s}", "故障来自无 VMA 的访问（die-no-vma）", "0x1",
              value_of(rows, "a4_fault_novma"))

    # The stub's syscalls are the locked table's numbers, and their routing is
    # `syscall_argmask.c`'s (address in rb16 for these four).
    hooks = kernel_text("arch/dadao/kernel/syscall_argmask.c")
    table = syscall_table_snapshot()
    for name in STUB_SYSCALLS:
        nr = table[name]
        rep.check(f"A2{s}", f"argmask[{nr}]（{name}）把首参路由到地址库", True,
                  re.search(rf"\[\s*{nr}\]\s*=\s*0x01,", hooks) is not None)
    disp = kernel_text("arch/dadao/kernel/syscalls.c")
    rep.check(f"A2{s}", "mmap 走 byte-offset 形式（sys_mmap 里 shift）", True,
              "off >> PAGE_SHIFT" in disp and "offset_in_page(off)" in disp)
    # The page-table geometry is the spec's: the L1/L2 tables are one page each
    # and the entries are 8 bytes (spec/DADAO-12 §2.2.2 - both derived here).
    pgtable = kernel_text("arch/dadao/include/asm/pgtable.h")
    rep.check(f"A1{s}", "L1/L2 索引位宽 == spec（2^13 项 × 8 B = 一页）",
              True,
              f"#if PAGE_SHIFT != {geo['shift']}" in pgtable)
    elfh = kernel_text("arch/dadao/include/asm/elf.h")
    rep.check(f"A1{s}", "ELF_EXEC_PAGESIZE == PAGE_SIZE（auxv 的来源）", True,
              "ELF_EXEC_PAGESIZE\tPAGE_SIZE" in elfh)
    proc = kernel_text("arch/dadao/kernel/process.c")
    rep.check(f"A2{s}", "trap 钩子接在 umon 分发之前", True,
              "dadao_k5p_user_trap(regs, immu18, &policy)" in proc)
    setup = kernel_text("arch/dadao/kernel/setup.c")
    rep.check(f"A5{s}", "pageblock 阶保持通用值（不随 MAX_ORDER 变大）", True,
              config_pins.PAGE_BLOCK_MAX_ORDER < order)
    rep.check(f"A5{s}", "探针镜像预留了 MAX_PAGE_ORDER 大小的块", True,
              "dadao_pagesz_reserve_max_order()" in setup)
    init = kernel_text("arch/dadao/mm/init.c")
    rep.check(f"A2{s}", "最小 mmap 地址按页大小对齐（paging_init）", True,
              "mmap_min_addr = PAGE_ALIGN(mmap_min_addr)" in init)

    rep.check(f"D{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)
    rep.check(f"D{s}", "自检以 'probe cases done' 结尾", True,
              "K5P selftest: probe cases done" in text)


def static_recon(rep: Report, snap: dict | None) -> None:
    """The pieces a boot cannot show: the image's own configuration."""
    rep.check("S0", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]
    CUR["config"] = config
    geo = spec_paging()
    order = arch_max_order()
    for symbol, value in {
            "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "y",
            "CONFIG_PAGE_SIZE_64KB": "y",
            "CONFIG_ARCH_FORCE_MAX_ORDER": str(order),
            "CONFIG_PAGE_BLOCK_MAX_ORDER": str(config_pins.PAGE_BLOCK_MAX_ORDER),
            "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    }.items():
        if value == "n":
            rep.check("B", f"镜像配置：{symbol}=n", False,
                      config_enabled(config, symbol))
        else:
            rep.check("B", f"镜像配置：{symbol}=={value}", value,
                      config_value(config, symbol))
    # The spec's page offset width and the image's page size must agree.
    rep.check("B", "spec §2.2.2 的页内偏移位宽 == 镜像的页大小",
              hex(geo["size"]),
              hex(1 << 16) if config_enabled(config, "CONFIG_PAGE_SIZE_64KB")
              else "unknown")
    # The allocator's largest order is one superpage (user ruling 2026-11-20).
    rep.check("B", "2^ARCH_FORCE_MAX_ORDER × 页大小 == 超页大小",
              hex(geo["superpage"]), hex(geo["size"] << order))

    # The fault channel is the one the SIGSEGV case goes through.
    fault = kernel_text("arch/dadao/mm/fault.c")
    rep.check("A4", "用户态无 VMA 的故障走 force_sig_fault(SIGSEGV)", True,
              "force_sig_fault(SIGSEGV" in fault and
              "DADAO_PF_SEGV" in fault)
    rep.check("A4", "dadao_pf_last_result() 记录通道判决", True,
              "dadao_pf_last_result" in fault)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> (file, needle, replacement, case that must go red, why)
INJECTIONS = {
    "auxv-pagesz-4k": (
        "arch/dadao/include/asm/elf.h",
        "#define ELF_EXEC_PAGESIZE\tPAGE_SIZE\n",
        "#define ELF_EXEC_PAGESIZE\t4096UL\n",
        "A1", "AT_PAGESZ 写 4096（4 KiB 页经验）⇒ auxv 现场值不等页大小，A1 红"),
    "mmap-unaligned": (
        "arch/dadao/kernel/syscalls.c",
        "\treturn ksys_mmap_pgoff(addr, len, prot, flags, fd, off >> PAGE_SHIFT);\n",
        "\t{\n\t\tunsigned long ret = ksys_mmap_pgoff(addr, len, prot, flags,\n"
        "\t\t\t\t\t\t   fd, off >> PAGE_SHIFT);\n"
        "\t\tif (!IS_ERR_VALUE(ret))\n"
        "\t\t\tret += 0x1000;   /* a 4 KiB (\"small page\") offset */\n"
        "\t\treturn ret;\n\t}\n",
        "A2", "mmap 返回值加 4 KiB（不按 64 KiB 页对齐）⇒ A2 红"),
    "brk-not-page-rounded": (
        "mm/mmap.c",
        "\tnewbrk = PAGE_ALIGN(brk);\n",
        "\tnewbrk = PAGE_ALIGN(brk) - PAGE_SIZE;   /* one page short */\n",
        "A4", "brk 的增长少映射一页（不按页取整）⇒ 堆尾 VMA 与断点不符，A4 红"),
}


def run_injection(rep: Report, name: str, rom: str) -> None:
    rel, needle, repl, case, why = INJECTIONS[name]
    path = SOURCE / rel
    original = path.read_bytes()
    before = md5(path)
    tmp = SCRATCH / f"inject-{name}.orig"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(original)
    text = original.decode()
    if needle not in text:
        rep.check(f"INJECT {name}", "注入点存在于源码", True, False)
        return
    path.write_text(text.replace(needle, repl, 1), encoding="utf-8")
    try:
        rep.check(f"INJECT {name}", "注入改动了源码（git diff 非空）", True,
                  path.read_bytes() != original)
        rc, snap = build_image(f"injected:{name}")
        if rc != 0 or snap is None:
            rep.check(f"INJECT {name}", f"注入后镜像可构建（{why}）", 0, rc)
            return
        rc, out = boot(f"inject-{name}", rom)
        rows = check_lines(out)
        red = [n for n, row in rows if row["verdict"] != "ok"]
        case_red = [n for n in red if n.startswith(case.lower()[:2])]
        died = any(tok in out for tok in ("K5P selftest FAIL", "Kernel panic",
                                          "dadao: die mode="))
        rep.info(f"inject {name}: rc={rc} red={red[:6]} died={died}")
        rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True,
                  bool(case_red) or died)
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        rc, snap = build_image("restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if snap is not None:
            rc2, out2 = boot(f"restored-{name}", rom)
            rows2 = check_lines(out2)
            rep.check(f"INJECT {name}", "还原后回绿（无红项）", [],
                      [n for n, row in rows2 if row["verdict"] != "ok"])
            rep.check(f"INJECT {name}", "还原后宿主 rc=0", 0, rc2)


def selfcheck() -> int:
    """Prove the judging can fail: feed it a console that must be red."""
    rep = Report()
    text = (
        "K5P selftest: begin pid=1 page_size=65536 page_shift=16 "
        "max_order=13\n"
        "K5P check a1_pagesz want=0x10000 got=0x1000 FAIL\n"
        "K5P check a1_pagesz_once want=0x1 got=0x1 ok\n"
        "K5P check a5_alloc_bytes want=0x20000000 got=0x4000000 FAIL\n"
        "K5P selftest FAIL: a1_pagesz=0x1000 code=0x71\n"
    )
    judge(rep, text, 1)
    red = rep.failed
    print(f"[SELFCHECK] red checks: {len(red)}")
    for name in red[:8]:
        print(f"[SELFCHECK]   {name}")
    if not red:
        print("[SELFCHECK] FAIL: a broken console produced no red check")
        return 1
    print("[SELFCHECK] PASS: the judging goes red on a broken console")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="M14 K5 page-size ABI probe")
    parser.add_argument("--selfcheck", action="store_true",
                        help="prove the judging can fail (no build, no boot)")
    parser.add_argument("--inject", action="append", default=[], metavar="NAME",
                        help=f"one of: {', '.join(sorted(INJECTIONS))}")
    parser.add_argument("--no-inject", action="store_true",
                        help="only the cases (no injection rounds)")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

    rep = Report()
    rc, snap = build_image()
    static_recon(rep, snap)
    if snap is None:
        print("k5_pagesz_probe: no image; judging stops here", file=sys.stderr)
        return 1
    rom = firmware()
    rc, out = boot("k5p", rom)
    judge(rep, out, rc, stub_oracle(kernel_path()))

    if not args.no_inject:
        names = args.inject or sorted(INJECTIONS)
        for name in names:
            if name not in INJECTIONS:
                raise SystemExit(f"k5_pagesz_probe: unknown injection {name!r}")
            run_injection(rep, name, rom)

    print()
    if rep.failed:
        print(f"k5_pagesz_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"k5_pagesz_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
