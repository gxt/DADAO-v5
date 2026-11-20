#!/usr/bin/env python3
"""k4_fork_probe.py — M14 K4 process-model probe (`m14-linux-016`).

K4 is where the kernel gets a *process*: an address space of its own, a task
created by `copy_process()`, and — for the first time — a page allocator behind
the page-fault channel (`alloc_page()` instead of the K3 pool, `find_vma()` on
`current->mm` instead of a static window array).

The kernel side is `arch/dadao/kernel/k4_selftest.c` (probe image,
`CONFIG_DADAO_K4_SELFTEST`), which runs at the K4 boundary — before `rest_init()`
and before any context switch, because running a second task is the work of
`m14-linux-017`) — and this gate builds that image, boots it on Kaiwu-Vast and
judges what the kernel reports.  Every expectation is derived from its owner:

  * page size / shift and the counts per level -> ``spec/DADAO-12 §2.2.2``, and
    the image's own ``.config`` for the page size it actually runs with;
  * the user VA range and the kernel window    -> ``spec/Kaiwu §6.3`` /
    ``contract-linux-boot`` (user space ends where the kernel window starts);
  * the callee-saved set a task must carry     -> ``contract-abi §4.5`` (rd32-63,
    rb32-63, rf32-63) checked against ``asm/processor.h``'s ``thread_struct``;
  * which code owns the clone of an address space -> the kernel sources
    (``asm/mmu_context.h``'s ``arch_dup_mmap`` hook, ``mm/mmu.c``);
  * the marker values the probe pins in the parent's saved context -> the probe
    source itself (never restated here);
  * the exit-code segments                     -> ``spec/Kaiwu §7.1``.

Groups (the letters ``--selfcheck``/``--inject`` flip):

  S  static recon: the image is the probe image the gate asked for, the page
     source is `alloc_page()` (no K3 pool left), the lookup goes through
     `find_vma(current->mm)`, and the fork hooks are wired where the generic
     code calls them.
  F1 `kernel_clone()` created a child: it exists, it has an address space of
     its own with a *different* ASID, and its saved context is the parent's
     with `rd8 = 0` (the fork return value).
  F2 the address space was cloned *copy-on-write* (m14-linux-018): a page the
     parent populated is at the *same* physical address on both sides, both
     PTEs are write-protected and the page carries two references, while the
     shared zero page is shared exactly the same way.  The write that splits
     the two is judged by `k4_cow_probe.py` (W1-W5), not here.
  F4 the K3 placeholders are gone in behaviour too: pages come from
     `alloc_page()` (distinct, zeroed), the shared zero page is the canonical
     `ZERO_PAGE(0)` the generic code recognises, and the lookup answers through
     `find_vma(current->mm)` once the task has an mm.

Not covered here (and why): `execve` building the `VM_GROWSDOWN` stack VMA
(F3) needs an initramfs, i.e. `kernel_init()` and therefore the context switch
of `m14-linux-017`; the user-mode entry (F5) needs the boot SEE to open
`cfx_umon` for the kernel's cfx, which it does not do today.  Both are recorded
in the task book rather than faked.

``--inject`` corrupts one source, rebuilds, asserts the named group goes red,
restores with ``cp`` + md5 and proves the image is green again (one path per
capability).

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
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                     # noqa: E402  (pins)
from tools.linux import k1_boot_probe as k1boot          # noqa: E402  (symbols)
from tools.linux import make_defconfig as defconfig     # noqa: E402  (config slice)
from tools.linux import paths as linux_paths            # noqa: E402
from tools.qemu import k0_boot_probe as k0              # noqa: E402  (firmware, ABI)

SCRATCH = (Path(os.environ.get("K4F_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-016") / "check-linux-k4")

SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
CONTRACT_ABI = _REPO / ".tao" / "contracts" / "contract-abi.md"
SOURCE = linux_paths.linux_source_dir()

#: Every boundary pinned (`make check-config-pins`, ISS-470): the K4 image has no
#: stop inside setup_arch() and no other milestone's self-test compiled in.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    # int symbols with an unmet `depends on` are "left unset" (no `n` value in
    # Kconfig; the symbol is dropped from .config) — tools/linux/config_pins.py.
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K4_SELFTEST": "y",
    # m14-linux-017: the context-switch probe is the mutually exclusive sibling
    # of this one (Kconfig: `depends on !DADAO_K4_SELFTEST`); pin it off so the
    # shared build tree cannot hand this image the other probe's symbol.
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    # m14-linux-020: the kernel-thread probe is an image of its own; pin it
    # off so the shared build tree cannot hand this image that symbol.
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    # m14-linux-017/019: the stack-growth probe is an int too; pin it
    # so no image inherits another gate's case (F30 class, twice seen).
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    # m14-linux-018: the copy-on-write probe is an int with no `depends on`, so
    # it carries a concrete value rather than "unset".
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    # m14-linux-023: the user-syscall probe image; pin it off so no other
    # image inherits it from the shared build tree.
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

ALWAYS_OFF = ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP",
              "CONFIG_DADAO_K2_TIME_STOP")

#: Wall-clock guards; `timeout` => rc 124, which is a FAIL (AGENTS.md「长任务」).
TIMEOUT_BUILD = int(os.environ.get("K4F_BUILD_TIMEOUT", "1800"))
TIMEOUT_QEMU = int(os.environ.get("K4F_QEMU_TIMEOUT", "180"))

JOBS = os.environ.get("JOBS", "32")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.total = 0
        self.failed: list[str] = []

    def check(self, group: str, name: str, expected, actual) -> None:
        self.total += 1
        ok = expected == actual
        print(f"[{'PASS' if ok else 'FAIL'}] {group}: {name}: want={expected!r} got={actual!r}")
        if not ok:
            self.failed.append(f"{group}: {name}")

    def info(self, text: str) -> None:
        print(f"[INFO] {text}")


# ---------------------------------------------------------------------------
# derivations
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def num(text: str | None, default: int = -1) -> int:
    if not text:
        return default
    try:
        return int(text, 0)
    except ValueError:
        return default


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    value = config_value(config, symbol)
    return value is not None and value not in ("n", "0", "")


def spec_page_geometry() -> tuple[int, int]:
    """(page offset bits, 64 KiB page shift) from spec/DADAO-12 §2.2.2."""
    text = SPEC_DADAO12.read_text(encoding="utf-8")
    sec = text[text.index("#### 2.2.2"):]
    sec = sec[:sec.index("#### 2.2.3")]
    # `VA[15:00]` -> 页内偏移（普通页的页内偏移为 16 位，即 64KiB）
    off = re.search(r"`VA\[(\d+):0+\]`\s*->\s*页内偏移", sec)
    if not off:
        raise SystemExit("k4_fork_probe: spec §2.2.2 has no page-offset width")
    # `VA[15:00]` is written as the *top bit index* of the offset field, so the
    # field width (and therefore PAGE_SHIFT) is one more.
    bits = int(off.group(1)) + 1
    return bits, bits


def spec_user_va_bits() -> int:
    """The VA width from spec/DADAO-12 §2.2.1 (VA[41:0] on this machine)."""
    text = SPEC_DADAO12.read_text(encoding="utf-8")
    m = re.search(r"VA\[(\d+):0\]", text)
    if not m:
        raise SystemExit("k4_fork_probe: spec has no VA width")
    return int(m.group(1)) + 1


def spec_run_mode(name: str) -> int:
    """The run-mode number of spec/DADAO-12 §1 (`00 user / 01 jail / 10 supv`)."""
    body = SPEC_DADAO12.read_text(encoding="utf-8")
    # "| 0b00   | 用户模式（U-mode） | user | ..." — the row's encoding column
    m = re.search(rf"\|\s*0b(\d{{2}})\s*\|[^\n]*\|\s*{name}\s*\|", body)
    if not m:
        raise SystemExit(f"k4_fork_probe: spec §1 has no run mode {name!r}")
    return int(m.group(1), 2)


def contract_callee_saved() -> tuple[str, ...]:
    """The callee-saved *banks* of contract-abi §4.5.

    §4.5 states the set as `rd32–rd63 ∪ rb32–rb63 ∪ rf32–rf63`; the return
    address stack (`ra0`–`ra63`) is not part of it (it is saved and restored
    per exception frame instead, spec/SimRISC-00 §2.4).
    """
    text = CONTRACT_ABI.read_text(encoding="utf-8")
    sec = text[text.index("§4.5"):]
    sec = sec[:sec.index("§4.6")] if "§4.6" in sec else sec[:4000]
    banks = set()
    for bank, lo, hi in re.findall(r"\b(rd|rb|rf)(\d+)\s*[–-]\s*\1(\d+)", sec):
        if int(lo) == 32 and int(hi) == 63:
            banks.add(bank)
    if not banks:
        raise SystemExit("k4_fork_probe: contract-abi §4.5 has no callee-saved ranges")
    return tuple(sorted(banks))


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"k4_fork_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def thread_struct_fields() -> dict[str, int]:
    """``thread_struct``'s array sizes, as the header really declares them."""
    header = kernel_text("arch/dadao/include/asm/processor.h")
    sec = header[header.index("struct thread_struct {"):]
    sec = sec[:sec.index("};")]
    out = {}
    for name, size in re.findall(r"unsigned long (rd|rb|rf)\[(\d+)\]", sec):
        out[name] = int(size)
    return out


def probe_markers() -> dict[str, int]:
    """The markers the probe pins in the parent's saved context (its source)."""
    src = kernel_text("arch/dadao/kernel/k4_selftest.c")
    out = {}
    for name, value in re.findall(r"#define (K4_PARENT_[A-Z0-9]+)\s+(0x[0-9a-fA-F]+|\d+)",
                                  src):
        out[name] = num(value, -1)
    return out


def probe_consts() -> dict[str, int]:
    """The probe's own scratch geometry and magic (its source)."""
    src = kernel_text("arch/dadao/kernel/k4_selftest.c")
    out = {}
    m = re.search(r"#define K4_VA_BASE\s+\((\d+)UL << (\d+)\)", src)
    if m:
        out["K4_VA_BASE"] = int(m.group(1)) << int(m.group(2))
    for name in ("K4_MAGIC", "K4_VA_PAGES"):
        m = re.search(rf"#define {name}\s+([0-9a-fA-Fx]+)UL?", src)
        if m:
            out[name] = num(m.group(1), -1)
    return out


def exit_segments() -> dict:
    """spec/Kaiwu §7.1's guest FAIL segment, parsed (no literal here)."""
    text = (SOURCE.parents[1] / "spec" / "Kaiwu-测试机运行环境.md")
    if not text.is_file():
        text = _REPO / "spec" / "Kaiwu-测试机运行环境.md"
    body = text.read_text(encoding="utf-8")
    m = re.search(r"guest[^\n]*0x01\s*[-–]\s*0x([0-7][0-9a-fA-F])", body)
    if not m:
        m = re.search(r"0x01\s*[-–]\s*0x([0-7][0-9a-fA-F])", body)
    if not m:
        raise SystemExit("k4_fork_probe: spec/Kaiwu §7.1 has no guest segment")
    return {"guest_max": int(m.group(1), 16)}


# ---------------------------------------------------------------------------
# console parsing
# ---------------------------------------------------------------------------

def kv(line: str) -> dict[str, str]:
    out = {}
    for token in line.split():
        if "=" in token:
            key, value = token.split("=", 1)
            out[key] = value
    return out


def line_with(text: str, prefix: str) -> dict[str, str] | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return kv(line)
    return None


def all_lines(text: str, prefix: str) -> list[dict[str, str]]:
    return [kv(line) for line in text.splitlines() if line.startswith(prefix)]


def check_lines(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"K4 check (\S+) want=(\S+) got=(\S+) (ok|FAIL)$", line)
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(4)}))
    return out


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def build_image(label: str) -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k4_fork_probe: FAIL: config slice for {label} rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    kernel = kernel_path()
    return 0, {
        "config": (build_dir() / ".config").read_text(encoding="utf-8"),
        "syms": k1boot.symbols(kernel),
        "kernel": kernel,
        "kernel_size": k1boot.kernel_size_from_elf(kernel, 0x20000100000),
    }


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k4.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k4_fork_probe: {kernel} missing; run `make linux-vmlinux`")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k4_fork_probe: qemu-system-dadao missing (make install-host)")
    log_dir = SCRATCH / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={rom}", "-nographic",
           "-semihosting-config", "enable=on,target=native", "-kernel", str(kernel)]
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
# S: static recon
# ---------------------------------------------------------------------------

def check_static(rep: Report, rc_build: int, snap: dict | None, d: dict) -> None:
    rep.check("S0", "K4 探针镜像可构建", 0, rc_build)
    if snap is None:
        for name in ("配置行", "边界符号", "页大小"):
            rep.check("S1", f"{name}（镜像缺失）", "可检查", "镜像未构建")
        return

    config = snap["config"]
    for symbol, value in {"CONFIG_DADAO_K4_SELFTEST": "y",
                          "CONFIG_PAGE_SIZE_64KB": "y"}.items():
        line = f"{symbol}={value}"
        rep.check("S1", f"镜像配置：{line}", line,
                  next((ln for ln in config.splitlines()
                        if ln.startswith(symbol + "=")), "<unset>"))
    rep.check("S1", "K3 页故障自检符号未开（本镜像只有 K4 的自检）", [],
              [s for s in ("CONFIG_DADAO_K3_PF_SELFTEST",
                           "CONFIG_DADAO_K3_PT_SELFTEST")
               if config_enabled(config, s)])
    off = [f"{s}={config_value(config, s)}" for s in ALWAYS_OFF
           if config_enabled(config, s)]
    rep.check("S1", "早期里程碑边界全关（镜像走完 setup_arch）", [], off)

    shift = num(config_value(config, "CONFIG_PAGE_SHIFT"))
    rep.check("S2", "页大小（1 << CONFIG_PAGE_SHIFT）== spec §2.2.2 页内偏移位宽",
              d["page_size"], 1 << shift)
    rep.check("S2", "CONFIG_PAGE_SHIFT == spec §2.2.2", d["page_shift"], shift)

    # The page source: alloc_page, and no K3 pool left anywhere.
    faults = kernel_text("arch/dadao/mm/fault.c")
    rep.check("S3", "页来源 = alloc_page(GFP_KERNEL | __GFP_ZERO)",
              True, "alloc_page(GFP_KERNEL | __GFP_ZERO)" in faults)
    rep.check("S3", "K3 静态池已消失（无 dadao_pf_pool_）", 0,
              faults.count("dadao_pf_pool_"))
    rep.check("S3", "零页 = 规范零页 ZERO_PAGE(0)（dup/COW 认得）", True,
              "ZERO_PAGE(0)" in faults)
    rep.check("S3", "查表走 find_vma(current->mm)", True,
              "find_vma(mm, addr)" in faults and "current->mm" in faults)

    # The fork hooks: copy_thread, start_thread and the arch half of dup_mm.
    process = kernel_text("arch/dadao/kernel/process.c")
    rep.check("S4", "copy_thread() 由 kernel/process.c 提供", True,
              "int copy_thread(struct task_struct *p" in process)
    rep.check("S4", "copy_thread() 设子 rd8 = 0（fork 返回值）", True,
              "childregs->rd[8] = 0" in process)
    mmu_ctx = kernel_text("arch/dadao/include/asm/mmu_context.h")
    # m14-linux-035: the port-side COW is gone.  The fork's sharing is generic
    # `copy_page_range()` (write-protect both PTEs, same page, second reference),
    # the write half is generic `do_wp_page()` reached through
    # `handle_mm_fault()`, and `dup_mmap()` itself drops the parent's stale
    # translations with `flush_tlb_mm(oldmm)`.
    rep.check("S4", "arch_dup_mmap 不再做 COW（返回 0，无 port-side 钩子）", True,
              "static inline int arch_dup_mmap(struct mm_struct *oldmm,"
              in mmu_ctx and "return 0;" in mmu_ctx
              and "return dadao_dup_mmap_cow(" not in mmu_ctx)
    rep.check("S4", "写半交给 generic handle_mm_fault（mm/cow.c 已删）", True,
              "handle_mm_fault(" in faults
              and not (SOURCE / "arch" / "dadao" / "mm" / "cow.c").exists()
              and "dadao_do_wp_page" not in faults)

    # The callee-saved set the task must carry (contract-abi §4.5).
    fields = thread_struct_fields()
    rep.check("S5", f"thread_struct 含 contract-abi §4.5 的 callee-saved 库 {sorted(d['callee'])}",
              {bank: 32 for bank in d["callee"]},
              {bank: fields.get(bank) for bank in sorted(d["callee"])})
    rep.check("S5", "thread_struct 的 sp/ra/tp 三个固定角色在处理器头里",
              ["ra", "sp", "tp"],
              [n for n in ("ra", "sp", "tp")
               if re.search(rf"unsigned long {n};", kernel_text(
                   "arch/dadao/include/asm/processor.h"))])

    # The probe image carries the symbols the run must show.
    syms = snap["syms"]
    for name in ("dadao_k4_selftest", "dadao_k4_boundary", "copy_thread",
                 "handle_mm_fault", "dadao_pf_alloc_page",
                 "dadao_user_excp_handler"):
        rep.check("S6", f"镜像含符号 {name}", True, name in syms)


# ---------------------------------------------------------------------------
# F1 / F2 / F4: the run
# ---------------------------------------------------------------------------

def check_f1(rep: Report, rc: int, text: str, d: dict) -> None:
    marks = d["marks"]
    rep.check("F1", "镜像以 SYS_EXIT(0) 结束", 0, rc)
    lines = check_lines(text)
    verdicts = [row["verdict"] for _name, row in lines]
    rep.check("F1", "内核自评的每条 K4 check 都 ok", [],
              [n for n, row in lines if row["verdict"] != "ok"])

    f1 = line_with(text, "K4 f1 child=")
    rep.check("F1", "F1 行存在（vacuous ⇒ FAIL）", True, f1 is not None)
    if not f1:
        return
    rep.check("F1", "子任务存在", True, num(f1.get("child")) > 0)
    rep.check("F1", "子任务有地址空间", True, num(f1.get("mm")) > 0)
    rep.check("F1", "子 mm 与父 mm 不同", 1, num(f1.get("asid_diff")))
    # The ASID must differ, and both must be inside the 16-bit space the
    # contract gives (contract-tlb TLB-04: [15:0], all values usable).
    rep.check("F1", "父子 ASID 不同", True,
              num(f1.get("asid_parent")) != num(f1.get("asid_child")))
    rep.check("F1", "ASID 在 16 位空间内", True,
              all(0 < num(f1.get(k), -1) <= 0xFFFF
                  for k in ("asid_parent", "asid_child")))

    regs = line_with(text, "K4 f1 regs ")
    rep.check("F1", "F1 上下文行存在", True, regs is not None)
    if not regs:
        return
    rep.check("F1", "子 ip == 父 ip（副本）", marks["K4_PARENT_IP"], num(regs.get("child_ip")))
    rep.check("F1", "子 sp == 父 sp（副本）", marks["K4_PARENT_SP"], num(regs.get("child_sp")))
    rep.check("F1", "子 rd8 = 0（fork 返回值）", 0, num(regs.get("child_rd8")))
    rep.check("F1", "子 rb3 继承父（TLS 到 execve 前不变）", marks["K4_PARENT_TP"],
              num(regs.get("child_rb3")))
    rep.check("F1", "父 ip 就是探针钉的标记（证明比的是真副本）", marks["K4_PARENT_IP"],
              num(regs.get("parent_ip")))
    rep.check("F1", "内核自评的 F1 行数 == 探针源码里的 child-* 断言数",
              d["f1_checks"],
              sum(1 for n, _r in lines if n.startswith("child-")))


def check_f2(rep: Report, text: str, d: dict) -> None:
    f2 = line_with(text, "K4 f2 private ")
    rep.check("F2", "F2 共享页行存在（vacuous ⇒ FAIL）", True, f2 is not None)
    if not f2:
        return
    parent_pa = num(f2.get("parent_pa"))
    child_pa = num(f2.get("child_pa"))
    rep.check("F2", "父页已映射（PA 非 0）", True, parent_pa > 0)
    rep.check("F2", "子页已映射（PA 非 0）", True, child_pa > 0)
    # m14-linux-018: a fork shares the page (COW); the split happens on the
    # first write and is mm/k4_cow_selftest.c's W1-W5, not this probe's.
    rep.check("F2", "两侧 PA 相同（写时复制共享，非私有复制）", 1,
              num(f2.get("pa_same")))
    rep.check("F2", "父侧 PTE 已写保护（W = 0）", 0, num(f2.get("w_parent")))
    rep.check("F2", "子侧 PTE 已写保护（W = 0）", 0, num(f2.get("w_child")))
    rep.check("F2", "页引用计数 == 2（两个映射各一份）", 2, num(f2.get("count")))
    rep.check("F2", "两侧页对齐", [],
              [hex(pa) for pa in (parent_pa, child_pa) if pa % d["page_size"]])
    rep.check("F2", "内容相同（共享同一页）", d["consts"]["K4_MAGIC"],
              num(f2.get("content_child")))
    rep.check("F2", "父侧内容仍是探针写的魔数", d["consts"]["K4_MAGIC"],
              num(f2.get("content_parent")))

    zero = line_with(text, "K4 f2 zero ")
    rep.check("F2", "F2 零页行存在", True, zero is not None)
    if not zero:
        return
    rep.check("F2", "共享零页两侧 PA 相同（不复制）", True,
              num(zero.get("parent_pa")) == num(zero.get("child_pa")))
    rep.check("F2", "共享零页 PA == ZERO_PAGE(0) 的 PA", d["zero_pa"],
              num(zero.get("child_pa")))
    rep.check("F2", "零页内容为 0（从未被写）", 0, num(zero.get("zero_bytes")))


def check_f5(rep: Report, rc: int, text: str, d: dict) -> None:
    """F5: the user-mode entry — cfx_umon user row in, cfx_smon for faults.

    Every expectation has an owner: the run-mode numbers come from
    ``spec/DADAO-12 §1``, the entry/exit registers from ``§3.1``/``§5.2`` and
    ``contract-syscall §8`` (user row for the syscall, the kernel's own rows for
    the hand-over), the frame shape from ``m14-linux-022``.
    """
    rep.check("F5", "用户态段以 SYS_EXIT(0) 收尾（无自检失败码）", 0, rc)
    install = line_with(text, "K4 umon vec ")
    rep.check("F5", "入口行寄存器已由内核自写（vacuous ⇒ FAIL）", True,
              install is not None)
    if install:
        rep.check("F5", "cfx_umon_user_switch_run_mode == supv(2)",
                  d["mode_supv"], num(install.get("user_mode")))
        rep.check("F5", "cfx_umon_user_excp_vector 非 0（内核自写）", True,
                  num(install.get("user_vector")) > 0)
        rep.check("F5", "cfx_umon_supv_switch_run_mode == user(0)",
                  d["mode_user"], num(install.get("supv_mode")))

    enter = line_with(text, "K4 f5 enter: ")
    rep.check("F5", "进入用户态行存在", True, enter is not None)
    if enter:
        rep.check("F5", "用户页在进入前未映射（缺页是用户态真异常）", 0,
                  num(enter.get("data_pte")))
        rep.check("F5", "用户程序按汇编仓拷入（字节数 > 0）", True,
                  num(enter.get("stub_bytes")) > 0)

    frames = [line_with(text, "K4 f5 sys%d:" % i) for i in (0, 1)]
    rep.check("F5", "两次用户 syscall 的帧行都存在", True,
              all(f is not None for f in frames))
    if not all(frames):
        return
    base = num(enter.get("ip")) if enter else -1
    for i, f in enumerate(frames):
        rep.check("F5", f"sys{i}: excp_prev_run_mode == user(0)（§5.2）",
                  d["mode_user"], num(f.get("prev_mode")))
        rep.check("F5", f"sys{i}: excp_cause_id == 1<<0（CFXTRAP）",
                  1 << d["cause_cfxtrap"], num(f.get("cause")))
        rep.check("F5", f"sys{i}: excp_cause_ip == trap 指令地址",
                  base + 8 * i, num(f.get("ip")))
        rep.check("F5", f"sys{i}: immu18 = excp_cause_info & 0x3FFFF == {i}",
                  i, num(f.get("immu18")))
        rep.check("F5", f"sys{i}: 用户行 switch == supv(2)", d["mode_supv"],
                  num(f.get("umon_switch")))
        rep.check("F5", f"sys{i}: 返回经 escape +4 落回 trap 下一条（第 2 次 ip = {i*8}）",
                  True, num(f.get("ip")) == base + 8 * i)

    banks = [line for line in text.splitlines() if line.startswith("K4 f5 banks:")]
    rep.check("F5", "四组帧里都能看到用户置的 callee-saved 哨兵", True,
              len(banks) == 2)

    trip = line_with(text, "K4 f5 roundtrip: ")
    rep.check("F5", "往返行存在", True, trip is not None)
    if trip:
        rep.check("F5", "RAS 逐位不变（022：进出异常不改 ra0-63）", 0,
                  num(trip.get("ras_bad")))
        rep.check("F5", "两次帧的三库哨兵一致（出口真恢复了）", 0,
                  num(trip.get("sentinel_bad")))
        rep.check("F5", "被重试的取数真执行了（读到共享零页 0）", 0,
                  num(trip.get("rd20")))
        rep.check("F5", "U-mode 缺页恰好 1 次且经通道处理", 1,
                  num(trip.get("pf_entries_delta")))

    # The hand-over: the supv channel (cfx_smon) took the fault, on its own
    # frame, and the page-fault channel filled the user page.
    deleg = line_with(text, "K4 umon->smon: ")
    rep.check("F5", "U-mode 同步异常经 cfx_smon 的 supv 通道（vacuous ⇒ FAIL）",
              True, deleg is not None)
    if deleg:
        rep.check("F5", "两个帧不共用（不串 umon 帧）", True,
                  num(deleg.get("frame_umon")) != num(deleg.get("frame_smon")))
        rep.check("F5", "移交的 cause 是页表类（CFXMEM）", 1,
                  1 if num(deleg.get("cause")) & (1 << d["cause_cfxmem"]) else 0)
        rep.check("F5", "移交的 ip 是用户的取数指令", base + 4, num(deleg.get("ip")))
        rep.check("F5", "移交的 info 是用户访问的地址",
                  num(enter.get("data_va")) if enter else -1, num(deleg.get("info")))

    fill = line_with(text, "K3 pf: ")
    rep.check("F5", "页故障通道在用户态 ip 上填了页", True, fill is not None)
    if fill:
        rep.check("F5", "填充分支 = fill-zero（匿名读映射共享零页）", "fill-zero",
                  fill.get("result"))
        rep.check("F5", "通道记录的 ip 是用户指令", base + 4, num(fill.get("ip")))
        rep.check("F5", "通道命中的 VMA 覆盖用户数据地址", True,
                  num(fill.get("vma")) <= num(fill.get("va")))

    done = line_with(text, "K4 f5 done: ")
    rep.check("F5", "F5 收尾行存在且 syscall 数 == 2", 2,
              num(done.get("syscalls")) if done else -1)


def check_f3_scope(rep: Report, text: str, rc: int) -> None:
    """F3's scope: `execve`'s `VM_GROWSDOWN` stack and a real `init` moved to
    m14-linux-017 (user 2026-11-17 ruling), because they need `kernel_init()`,
    i.e. the context switch.  What this image must *not* do is pretend: it stops
    at the K4 boundary, by name, before any task is scheduled."""
    boundary = [line for line in text.splitlines()
                if line.startswith("K4 boundary:")]
    rep.check("F3", "镜像在 K4 边界运行（边界行存在，vacuous ⇒ FAIL）", 1,
              len(boundary))
    rep.check("F3", "镜像没有走到内核 init / initramfs（F3 已移 017）", [],
              [line for line in text.splitlines()
               if (("Run /init" in line) or
                   ("initramfs" in line and not line.startswith("K1 bootinfo")))])
    rep.check("F3", "边界之外没有第二个任务被调度（无 017 的 switch_to）", 0, rc)


def check_f4(rep: Report, text: str, d: dict) -> None:
    alloc = line_with(text, "K4 f4 alloc ")
    rep.check("F4", "F4 页来源行存在（vacuous ⇒ FAIL）", True, alloc is not None)
    if alloc:
        rep.check("F4", "两次分配非 0", True,
                  num(alloc.get("pa1")) > 0 and num(alloc.get("pa2")) > 0)
        rep.check("F4", "两次分配 PA 不同", 1, num(alloc.get("distinct")))
        rep.check("F4", "新页全 0（__GFP_ZERO 生效）", 1, num(alloc.get("zeroed")))
        rep.check("F4", "分配页都不在镜像内", [],
                  [hex(num(alloc.get(k))) for k in ("pa1", "pa2")
                   if d["image_start"] <= num(alloc.get(k)) < d["image_end"]])

    zero = line_with(text, "K4 f4 zero_page ")
    rep.check("F4", "F4 零页行存在", True, zero is not None)
    if zero:
        rep.check("F4", "零页 PA == 规范 ZERO_PAGE(0)", d["zero_pa"],
                  num(zero.get("pa")))
        rep.check("F4", "is_zero_pfn(ZERO_PAGE(0)) 为真", 1,
                  num(zero.get("is_zero_pfn")))

    vma = line_with(text, "K4 f4 find_vma ")
    if vma and "vma" in vma and "-" in vma["vma"]:
        vma["start"], _end = vma["vma"].split("-", 1)
    rep.check("F4", "F4 查表行存在", True, vma is not None)
    if vma:
        base = d["consts"]["K4_VA_BASE"]
        rep.check("F4", "current->mm 的 VMA 命中探针窗口起点", 1, num(vma.get("hit")))
        rep.check("F4", "命中窗口起点 == 探针窗口基址", base, num(vma.get("start")))


# ---------------------------------------------------------------------------
# self-check: mutate the capture, every group must flip
# ---------------------------------------------------------------------------

def mutate(text: str, group: str) -> str:
    if group == "F1":
        # Flip the kernel's own verdict *and* the value the derived checks
        # read: `check_f1` judges both ("每条 K4 check 都 ok" and the child
        # context line), so a mutation that only touches a redundant copy of
        # the value cannot leave the group green.
        return (text
                .replace("child-ip-copied want=0xbeef got=0xbeef ok",
                         "child-ip-copied want=0xbeef got=0x0 FAIL")
                .replace("child_ip=0xbeef", "child_ip=0x0"))
    if group == "F2":
        # Both a value the derived checks read (pa_same / w_child) and the
        # kernel's own verdict line flip: a mutation of one copy cannot leave
        # the group green.
        return (text
                .replace(" pa_same=1 ", " pa_same=0 ")
                .replace(" w_child=0 ", " w_child=1 ")
                .replace("cow-pa-shared want=0x1 got=0x1 ok",
                         "cow-pa-shared want=0x1 got=0x0 FAIL")
                .replace("cow-child-readonly want=0x0 got=0x0 ok",
                         "cow-child-readonly want=0x0 got=0x1 FAIL"))
    if group == "F5":
        return text.replace("K4 f5 sys0: nr=0 prev_mode=0 cause=0x1",
                            "K4 f5 sys0: nr=0 prev_mode=2 cause=0x1")
    if group == "F4":
        return text.replace("K4 f4 alloc pa1=", "K4 f4 alloc pa1=0x0 pa2=0x0 distinct=0 zeroed=1 pa1_=")
    raise SystemExit(f"k4_fork_probe: no mutation for group {group}")


def run_selfcheck(rc: int, text: str, d: dict) -> int:
    problems = []
    for group in ("F1", "F2", "F4", "F5"):
        rep = Report()
        with contextlib.redirect_stdout(io.StringIO()):
            if group == "F1":
                check_f1(rep, rc, mutate(text, "F1"), d)
            elif group == "F2":
                check_f2(rep, mutate(text, "F2"), d)
            elif group == "F5":
                check_f5(rep, 0, mutate(text, "F5"), d)
            else:
                check_f4(rep, mutate(text, "F4"), d)
        if not rep.failed:
            problems.append(f"mutating {group} did not turn any check red")
        else:
            print(f"[SELFCHECK] {group}: mutation caught by {len(rep.failed)} check(s)")
    if problems:
        print(f"[SELFCHECK] FAIL: {problems}")
        return 1
    print("[SELFCHECK] PASS: every group has a reachable FAIL path")
    return 0


# ---------------------------------------------------------------------------
# injections: corrupt one source, rebuild, assert red, restore + md5
# ---------------------------------------------------------------------------

INJECTIONS = {
    "no-regs-copy": {
        "file": "arch/dadao/kernel/process.c",
        "old": "\t*childregs = *regs;\n",
        "new": "\tmemset(childregs, 0, sizeof(*childregs));\n",
        "group": "F1",
        "why": "子上下文不再复制父 pt_regs",
    },
    "eager-copy": {
        # m14-linux-018 turned the hook into COW sharing; the injection puts the
        # m14-linux-016 eager private copy back, which is exactly what F2 says
        # must not happen any more (the child's PA would differ).
        #
        # The anchor is the *early-return* branch: F2's VMA is `VM_MIXEDMAP`,
        # so the generic `copy_page_range()` has already installed the child's
        # PTE (`vma_needs_copy()` returns true for it) and the sharing code
        # below never runs for this page — an injection placed there is dead
        # code for F2 (measured by the reviewer: `F2 red checks = 0`).
        "file": "arch/dadao/mm/mmu.c",
        "old": "\tif (pte_present(ptep_get(dst_pte))) {\n"
               "\t\t/*\n"
               "\t\t * The generic path shared this one already (a VM_MIXEDMAP VMA):\n",
        "new": "\tif (pte_present(ptep_get(dst_pte))) {\n"
               "\t\t/* injected: 016's eager private copy is back, so the child\n"
               "\t\t * gets a page of its own instead of sharing the parent's */\n"
               "\t\t{\n"
               "\t\t\tstruct page *cow_dst =\n"
               "\t\t\t\talloc_page(GFP_KERNEL | __GFP_ZERO);\n"
               "\t\n"
               "\t\t\tif (cow_dst) {\n"
               "\t\t\t\tcopy_page(page_address(cow_dst),\n"
               "\t\t\t\t\t  __va(pte_val(entry) & _PAGE_PFN_MASK));\n"
               "\t\t\t\tset_pte(dst_pte,\n"
               "\t\t\t\t\t__pte((page_to_phys(cow_dst) &\n"
               "\t\t\t\t\t\t _PAGE_PFN_MASK) |\n"
               "\t\t\t\t\t      (pte_val(entry) &\n"
               "\t\t\t\t\t\t ~_PAGE_PFN_MASK)));\n"
               "\t\t\t}\n"
               "\t\t}\n"
               "\t\t/*\n"
               "\t\t * The generic path shared this one already (a VM_MIXEDMAP VMA):\n",
        "group": "F2",
        "why": "arch 钩子退回 016 的私有页复制（子 PA 与父不同）",
    },
    "no-user-vector": {
        "file": "arch/dadao/kernel/process.c",
        "old": "\tDADAO_CFX_WRITE(cfx_umon, UMON_CG_USER, UMON_RC_EXCP_VECTOR, vec);\n",
        "new": "\tDADAO_CFX_WRITE(cfx_umon, UMON_CG_USER, UMON_RC_EXCP_VECTOR, vec & 0);\n",
        "group": "F5",
        "why": "cfx_umon 的 user 行向量不写（复位 0）：用户 trap 的第一个落点不是内核代码",
    },
    "no-cause-ip-save": {
        "file": "arch/dadao/kernel/trap.S",
        "old": "\tst.o\trd17, [rb3, PT_IP]\n\tst.o\trd0, [rb3, PT_STATUS]\n\n\t/*\n\t * 4a. A user *syscall*",
        "new": "\tst.o\trd0, [rb3, PT_STATUS]\n\n\t/*\n\t * 4a. A user *syscall*",
        "group": "F5",
        "why": "umon 入口不把 excp_cause_ip 存进帧（返回/判据都用不到的错 IP）",
    },
    "static-window-lookup": {
        "file": "arch/dadao/mm/fault.c",
        "old": "\t\tvma = find_vma(mm, addr);\n",
        "new": "\t\tvma = NULL;\n",
        "group": "F4",
        "why": "查表不再走 find_vma(current->mm)（退回 K3 的静态窗口形状）",
    },
}


def run_inject(name: str, d: dict) -> int:
    spec = INJECTIONS[name]
    path = SOURCE / spec["file"]
    backup = SCRATCH / f"{name}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    before = md5(path)
    shutil.copy2(path, backup)
    rep = Report()
    try:
        text = path.read_text(encoding="utf-8")
        if spec["old"] not in text:
            print(f"[INJECT] {name}: anchor not found in {spec['file']}")
            return 1
        path.write_text(text.replace(spec["old"], spec["new"], 1),
                        encoding="utf-8")
        print(f"[INJECT] {name}: {spec['why']} ({spec['file']})")
        rc_build, snap = build_image(f"inject-{name}")
        if rc_build != 0 or snap is None:
            print(f"[INJECT] {name}: FAIL: the injected image does not build")
            return 1
        rom = firmware()
        rc, run = boot(f"inject-{name}", rom)
        with contextlib.redirect_stdout(io.StringIO()):
            if spec["group"] == "F1":
                check_f1(rep, rc, run, d)
            elif spec["group"] == "F2":
                check_f2(rep, run, d)
            elif spec["group"] == "F5":
                check_f5(rep, rc, run, d)
            else:
                check_f4(rep, run, d)
        print(f"[INJECT] {name}: {spec['group']} red checks = {len(rep.failed)}"
              f" (rc={rc})")
        for item in rep.failed[:4]:
            print(f"[INJECT]   {item}")
        if not rep.failed:
            print(f"[INJECT] {name}: FAIL: nothing went red")
            return 1
    finally:
        shutil.copy2(backup, path)
        # `copy2` restores the *original* mtime, which is older than the
        # object file the injected build produced: `make` would then skip the
        # rebuild and the "green again" run would execute the injected image.
        os.utime(path, None)
        after = md5(path)
        print(f"[INJECT] {name}: restored md5 {before} -> {after} "
              f"{'OK' if before == after else 'MISMATCH'}")
        if before != after:
            return 1
    # Rebuild and prove the restored source is green again.
    rc_build, snap = build_image(f"post-{name}")
    if rc_build != 0 or snap is None:
        print(f"[INJECT] {name}: FAIL: rebuild after restore failed")
        return 1
    rc, run = boot(f"post-{name}", firmware())
    green = Report()
    with contextlib.redirect_stdout(io.StringIO()):
        check_f1(green, rc, run, d)
        check_f2(green, run, d)
        check_f4(green, run, d)
        check_f5(green, rc, run, d)
        check_f3_scope(green, run, rc)
    print(f"[INJECT] {name}: back to green rc={rc} failures={len(green.failed)}")
    return 0 if not green.failed else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def derivations(snap: dict) -> dict:
    config = snap["config"]
    shift = num(config_value(config, "CONFIG_PAGE_SHIFT"))
    if shift < 0:
        raise SystemExit("k4_fork_probe: the image's .config has no CONFIG_PAGE_SHIFT")
    off_bits, contract_shift = spec_page_geometry()
    page_size = 1 << shift
    syms = snap["syms"]
    # The zero page the image really uses, from its own symbol table: the
    # canonical page is a kernel-image page (empty_zero_page), and the image
    # starts at `_start`.
    image_start = syms.get("_start")
    image_end = syms.get("_end")
    if not image_start or not image_end:
        raise SystemExit("k4_fork_probe: the image has no _start/_end symbols")
    return {
        "shift": shift,
        "page_size": page_size,
        "page_shift": contract_shift,
        "page_offset_bits": off_bits,
        "va_bits": spec_user_va_bits(),
        "callee": contract_callee_saved(),
        "marks": probe_markers(),
        "consts": probe_consts(),
        # `empty_zero_page` is a kernel-image symbol, i.e. a VA: the zero
        # page's PA is what the kernel prints and what a PTE carries.
        "zero_pa": syms.get("empty_zero_page", 0)
                    - num(config_value(config, "CONFIG_PAGE_OFFSET")),
        "image_start": image_start,
        "image_end": image_end,
        "syms": syms,
        "mode_user": spec_run_mode("user"),
        "mode_supv": spec_run_mode("supv"),
        "cause_cfxtrap": num(re.search(r"#define DADAO_CAUSE_CFXTRAP\s+\(1UL << (\d+)\)",
                                       kernel_text("arch/dadao/include/asm/trap.h")).group(1), -1),
        "cause_cfxmem": num(re.search(r"#define DADAO_CAUSE_CFXMEM\s+\(1UL << (\d+)\)",
                                      kernel_text("arch/dadao/include/asm/trap.h")).group(1), -1),
        "f1_checks": len(re.findall(r'k4_expect\("child-', kernel_text(
            "arch/dadao/kernel/k4_selftest.c"))),
        "page_offset": num(config_value(config, "CONFIG_PAGE_OFFSET")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="K4 process-model probe")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured run and show every group flips")
    ap.add_argument("--inject", action="append", choices=sorted(INJECTIONS),
                    help="corrupt a source, rebuild, assert red, restore, re-green")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    rc_build, snap = (0, None) if args.skip_build else build_image("k4")
    if snap is None and not args.skip_build:
        rep = Report()
        check_static(rep, rc_build, None, {})
        return 1
    if snap is None:
        raise SystemExit("k4_fork_probe: --skip-build needs an image in the build tree")
    d = derivations(snap)

    if args.inject:
        rc = 0
        for name in args.inject:
            rc |= run_inject(name, d)
        return rc

    rc, text = boot("k4", firmware())
    if args.selfcheck:
        return run_selfcheck(rc, text, d)

    rep = Report()
    check_static(rep, rc_build, snap, d)
    check_f1(rep, rc, text, d)
    check_f2(rep, text, d)
    check_f4(rep, text, d)
    check_f5(rep, rc, text, d)
    check_f3_scope(rep, text, rc)

    # A K4 FAIL line (the kernel's own verdict) is never a pass.
    rep.check("F1", "内核没有自报 FAIL 行", [], re.findall(r"^K4 FAIL:.*$", text,
                                                          re.MULTILINE))
    print()
    if rep.failed:
        print(f"k4_fork_probe: {rep.total - len(rep.failed)}/{rep.total} passed; "
              f"{len(rep.failed)} FAILED")
        for item in rep.failed:
            print(f"  - {item}")
        return 1
    print(f"k4_fork_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
