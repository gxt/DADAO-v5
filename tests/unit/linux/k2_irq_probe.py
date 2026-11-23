#!/usr/bin/env python3
"""k2_irq_probe.py — M14 K2 interrupt-enable knob gate (`m14-linux-008`).

DADAO has no interrupt-enable state bit: the software IE knob is the running
mode monitor's asynchronous source mask (`cfx_smon_async_intr_mask`,
`cfx_smon cg8 rc1`, spec/DADAO-12 §4.3/§5.4 / ADR-0061 D5), and the kernel maps
`local_irq_*` onto it (contract-see §6.4).  Whether that mapping is *real* can only be
seen from the physical register, so the probe image (`kernel/k2_irq_test.c`,
CONFIG_DADAO_K2_IRQ_TEST) reads the knob row back with `cfx2rd` after every step
— and the delivered cfx's row as well, as the witness that nothing writes it —
and prints the raw words; this gate is the judge.

Boot path under test:

    power -> hmon -> smon -> kernel entry -> setup_arch -> time_init ->
    async vector -> monitor source mask -> arm -> TIMER tick -> [P1, P3, P5, P2] ->
    [P4: in-capture copy + return through smon] -> masked exit

What is derived live (nothing is restated):

  * the source bit -> `scalar cfx_hart 15` of `contracts/cfx-aliases.txt`,
    i.e. `1 << 15`; an asynchronous source has no `excp_cause_id` (ADR-0061
    D2), so the mask/pending index is also the source identity;
  * the period -> the image's `CONFIG_HZ` and the contract's `cfx_time_freq`
    (`freq // HZ`), so a hardcoded count in the kernel goes red;
  * the exit codes / segments -> `spec/Kaiwu §7.1` (parsed by the K2
    exception gate, reused);
  * the self-check code space -> every `*FAIL*` constant the kernel sources
    define (same scan the K2 time gate uses, extended with this task's file).

Checks: C0 static inputs / C1 image + stage order / P1 save-restore round trip
(plus the absolute anchor ISS-457 added: the saved word == the contract's reset
value — all-ones — minus the source bit, so a high-half truncation cannot stay
self-consistent) /
P2 masked window + merged re-delivery / P3 nested saves / P4 capture overwrite
inside the async handler (every entry overwrites cg9; nesting is the software's
job) and the software copy/return through smon / P5 `arch_irqs_disabled()` versus
the live register and the enable-granularity anchor (ISS-457: enable == disable
with only the source bits cleared) / U1 hard-IRQ context inside the handler
(`in_hardirq()` == 1; m14-linux-044) / U2 `sched_clock()` vs `cfx_time` (same
source, monotone) / U3 a bad user pointer through copy_from_user/copy_to_user is
fixed up to -EFAULT instead of ending the boot / C9 totals (masked exit).

`--selfcheck` mutates the captured run and shows every group flips.
`--inject` corrupts the kernel source, rebuilds, asserts the expected FAIL and
restores with ``cp`` + md5 (never ``git checkout``), then proves the image is
green again.

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (contract / build tree / QEMU missing).
"""
from __future__ import annotations

import argparse
import contextlib
import errno
import hashlib
import io
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.linux import config_pins                     # noqa: E402  (pins)
from tests.unit.linux import k2_time_probe as k2time         # noqa: E402  (derivations)
from tests.unit.linux import k2_trap_probe as k2trap        # noqa: E402  (§7.1 parser)
from tools.linux import make_defconfig as defconfig    # noqa: E402  (config slice)
from tools.linux import paths as linux_paths           # noqa: E402
from tools.qemu import k0_boot_probe as k0             # noqa: E402  (firmware)

PROFILE = "vast"

TIMEOUT_QEMU = int(os.environ.get("K2I_QEMU_TIMEOUT", "180"))
TIMEOUT_BUILD = int(os.environ.get("K2I_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K2I_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-008") / "k2_irq_probe")

SOURCE = linux_paths.linux_source_dir()
IRQFLAGS = "arch/dadao/include/asm/irqflags.h"
IRQ_TEST = "arch/dadao/kernel/k2_irq_test.c"
TIME_C = "arch/dadao/kernel/time.c"
TRAPS_C = "arch/dadao/kernel/traps.c"

#: Every milestone symbol is pinned (complete set, `make check-config-pins`,
#: ISS-470) so the shared build tree cannot leak one image's configuration into
#: another; an int pinned ``"n"`` is "left unset" because its `depends on` is
#: not met.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "y",
    "CONFIG_DADAO_K2_TIME_CASE": "0",
    "CONFIG_DADAO_K2_IRQ_TEST": "y",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
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
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

#: Deliveries the case sequence forces: the first tick, the event merged out of
#: the P2 masked window, and the P4 capture copied out of cg9.  The floor is
#: the capability claim; the exact count is not pinned.
TICK_FLOOR = 3


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
# expectations derived from the contract / the kernel source (never restated)
# ---------------------------------------------------------------------------

def declared_source_bits() -> int:
    """``DADAO_IRQ_SOURCE_BITS`` as asm/irqflags.h spells it."""
    path = SOURCE / IRQFLAGS
    m = re.search(r"^#define\s+DADAO_IRQ_SOURCE_BITS\s+\(1UL << (\d+)\)",
                  path.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        raise SystemExit(f"k2_irq_probe: {path} has no DADAO_IRQ_SOURCE_BITS")
    return 1 << int(m.group(1))


def knob_register() -> tuple[int, int]:
    """The knob's ``(cg, rc)`` as `asm/irqflags.h` defines them."""
    text = (SOURCE / IRQFLAGS).read_text(encoding="utf-8")
    cg = re.search(r"^#define\s+DADAO_IRQ_CG_SUPV\s+(\d+)", text,
                   re.MULTILINE)
    rc = re.search(r"^#define\s+DADAO_IRQ_RC_SUPV_CFX_INTR_MASK\s+(\d+)",
                   text, re.MULTILINE)
    if not cg or not rc:
        raise SystemExit(f"k2_irq_probe: {IRQFLAGS} has no supv-row defines")
    return int(cg.group(1)), int(rc.group(1))


def contract_knob_register() -> tuple[int, int]:
    """``cg8 rc1`` from contract-see §6.4's single-knob bullet.

    ADR-0061 D5 moved the async source mask from the monitor's cg0-cg3 rc4
    row to `cfx_smon`'s `cg8 rc1` (`cfx_smon_async_intr_mask`).
    """
    text = (REPO / ".tao" / "contracts" / "contract-see.md").read_text(
        encoding="utf-8")
    m = re.search(r"`cfx_smon_async_intr_mask`（`cg(\d+) rc(\d+)`）", text)
    if not m:
        raise SystemExit("k2_irq_probe: contract-see §6.4 has no knob register")
    return int(m.group(1)), int(m.group(2))


def knob_rows_written() -> tuple[bool, bool]:
    """Which rows the knob's *write* path touches (ISS-455: exactly one).

    The run mode picks the row — `supv` ⇒ the mode monitor's `cfx_smon`
    `cg2 rc4` — so the write path must never touch the delivered cfx's row.
    The values cannot show this from behaviour (and the second write is
    indistinguishable in the readback), so the row set is asserted on the
    source the same way the register identity is.  The reader lives in
    ``k2_time_probe`` because C10 needs the very same judgement.
    """
    return k2time.knob_rows_written()


def image_config() -> str:
    """The ``.config`` of the image just built.

    The build tree is shared with every other Linux gate (and every worktree
    reaches the same one through ``.work``), so this has to be read right after
    the build, never at the end of the run: a concurrent gate re-slicing
    ``.config`` in between is otherwise indistinguishable from "the image was
    built without the symbols this gate pinned".
    """
    return (Path(linux_paths.linux_build_dir()) / ".config").read_text(
        encoding="utf-8")


def derivation(cfg: str | None = None) -> dict:
    """Everything the checks compare against, read once."""
    hart = k2time.cfxha("cfx_hart")
    freq = k2time.contract_freq()
    if cfg is None:
        cfg = image_config()
    hz = k2time.config_hz(cfg)
    period = freq // hz
    if not period:
        raise SystemExit("k2_irq_probe: freq / CONFIG_HZ is zero")
    return {"bit": 1 << hart, "hart": hart, "freq": freq, "hz": hz,
            "period": period, "timer": k2time.contract_timer_cause(),
            "config": cfg}


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def config() -> int:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k2_irq_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc
    cmd = [sys.executable, str(REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build irq image (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def kernel_path() -> Path:
    return Path(linux_paths.linux_build_dir()) / "vmlinux"


def freeze_image(tag: str) -> dict:
    """Copy the image and its ``.config`` out of the shared build tree.

    The build tree is one directory for every worktree (``.work`` is shared) and
    every Linux gate rebuilds it, so a concurrent run can replace the ELF
    between this gate's build and its boot.  Freezing both artefacts right after
    the build makes the run judge the image it built: the boot uses the copy and
    the config assertions use the captured text.
    """
    out = SCRATCH / "images" / tag
    out.mkdir(parents=True, exist_ok=True)
    kernel = out / "vmlinux"
    kernel.write_bytes(kernel_path().read_bytes())
    return {"kernel": kernel, "config": image_config()}


def firmware(tag: str) -> str:
    k0.load_contract()
    if not k0.ABI:
        raise SystemExit("k2_irq_probe: the boot contract projection is empty")
    out = SCRATCH / f"bootrom_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(out), hmon_defs=[],
                             name=f"bootrom_k0_{tag}.bin")


def boot(tag: str, rom: str, kernel: Path | None = None,
         timeout: int | None = None) -> tuple[int, str, list[str]]:
    kernel = kernel or kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k2_irq_probe: {kernel} missing")
    log = SCRATCH / "log" / f"{tag}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [k0.DEFAULT_QEMU,
           "-machine", f"kaiwu-vast,bootrom-image={rom}",
           "-nographic",
           "-semihosting-config", "enable=on,target=native",
           "-kernel", str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=timeout or TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = err or out
    log.write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# the kernel's own report
# ---------------------------------------------------------------------------

TIME_INIT = re.compile(
    r"^K2 time_init: freq=(\d+) hz=(\d+) period=(\d+) n_ticks=(\d+) "
    r"first=(\d+)$", re.MULTILINE)
IRQ_VEC = re.compile(
    r"^K2 irq: vec cfx_hart_supv_excp_vector=(\S+) want=(\S+) mode=(\d+)$",
    re.MULTILINE)
IRQ_MASK = re.compile(
    r"^K2 irq: mask cfx_smon_supv_cfx_intr_mask=(\S+) "
    r"cfx_hart_supv_cfx_intr_mask=(\S+) cfx_smon_global_cfx_intr_mask=(\S+) "
    r"cfxha=(\d+) bit=(\S+)$", re.MULTILINE)
ARMED = re.compile(r"^K2 irq: armed ticks period=(\d+)$", re.MULTILINE)
P1 = re.compile(
    r"^K2 irq P1: before_smon=(\S+) before_hart=(\S+) flags=(\S+) "
    r"masked_smon=(\S+) masked_hart=(\S+) restored_smon=(\S+) "
    r"restored_hart=(\S+)$", re.MULTILINE)
P3 = re.compile(
    r"^K2 irq P3: before_smon=(\S+) before_hart=(\S+) outer=(\S+) inner=(\S+) "
    r"inner_smon=(\S+) inner_hart=(\S+) outer_smon=(\S+) outer_hart=(\S+)$",
    re.MULTILINE)
P5 = re.compile(
    r"^K2 irq P5: state=(\w+) flags=(\S+) disabled=(\d+) flags_disabled=(\d+) "
    r"smon=(\S+) hart=(\S+)$", re.MULTILINE)
P2_MASKED = re.compile(r"^K2 irq P2: masked ticks=(\d+) ctrl=(\S+) "
                       r"window=(\d+)$", re.MULTILINE)
P2_RELEASED = re.compile(r"^K2 irq P2: released ticks=(\d+) window=(\d+) "
                         r"elapsed=(\d+)$", re.MULTILINE)
P4_FRAME = re.compile(r"^K2 irq P4: frame tick=(\d+) waited_ticks=(\d+) "
                      r"ctrl=(\S+) window=(\d+) elapsed=(\d+)$", re.MULTILINE)
P4_AFTER = re.compile(r"^K2 irq P4: afterframe tick=(\d+) gap=(\d+) "
                      r"period=(\d+)$", re.MULTILINE)
DONE = re.compile(r"^K2 irq: done ticks=(\d+) mask=(\S+)$", re.MULTILINE)

#: m14-linux-044: the three "only a select / only a call site" gaps.
U1 = re.compile(r"^K2 irq U1: inframe=(\d+) in_hardirq=(\d+) "
                r"in_interrupt=(\d+) irq_regs=(\d+)$", re.MULTILINE)
U2 = re.compile(r"^K2 sched: t0=(\d+) s0=(\d+) t1=(\d+) s1=(\d+) t2=(\d+) "
                r"s2=(\d+) dcfx1=(\d+) dsc1=(\d+) dcfx2=(\d+) dsc2=(\d+)$",
                re.MULTILINE)
U3 = re.compile(r"^K2 uaccess: bad=(\S+) size=(\d+) from=(\d+) to=(\d+) "
                r"errno=(-?\d+)$", re.MULTILINE)

#: One anchor per stage, in the order the boot must produce them.  The vector is
#: installed before any mask is opened (spec/DADAO-12 §5.2 step 7), the arm
#: follows the masks (init_IRQ), and the cases start after the first tick.
STAGES = (
    ("bootinfo", r"^K1 bootinfo magic="),
    ("setup_arch", r"^K2 setup_arch: memblock_add "),
    ("time_init", r"^K2 time_init: freq="),
    ("irq-vector", r"^K2 irq: vec cfx_hart_supv_excp_vector="),
    ("irq-mask", r"^K2 irq: mask cfx_smon_supv_cfx_intr_mask="),
    ("armed", r"^K2 irq: armed ticks period="),
    ("P1", r"^K2 irq P1: "),
    ("P3", r"^K2 irq P3: "),
    ("P5-disable", r"^K2 irq P5: state=disable "),
    ("P5-enable", r"^K2 irq P5: state=enable "),
    ("P5-save", r"^K2 irq P5: state=save "),
    ("P5-restore", r"^K2 irq P5: state=restore "),
    ("P2-masked", r"^K2 irq P2: masked "),
    ("P2-released", r"^K2 irq P2: released "),
    ("P4-frame", r"^K2 irq P4: frame "),
    ("P4-afterframe", r"^K2 irq P4: afterframe "),
    ("done", r"^K2 irq: done ticks="),
)

ORDER_PAIRS = (("time_init", "irq-vector"), ("irq-vector", "irq-mask"),
               ("irq-mask", "armed"), ("armed", "P1"), ("P2-released", "P4-frame"))


def ints(groups) -> list[int]:
    return [int(g, 0) for g in groups]


# ---------------------------------------------------------------------------
# C0/C1: inputs, image and order
# ---------------------------------------------------------------------------

def check_static(rep: Report, spec: dict) -> None:
    d = derivation()
    bit = d["bit"]
    rep.check("C0", "cfx_hart 的 cfxha 来自别名表", 15, d["hart"])
    rep.check("C0", "源位 = 1 << 源 cfxha（异步无独立 cause id）", bit,
              declared_source_bits())
    rep.check("C0", "源位 == TIMER 源位（只有一套编号）", True,
              bit == d["timer"])
    # Register identity is a *static* property: with the knob on another row the
    # printed values stay self-consistent (the row carries its own default and
    # init_IRQ opens it), so only the source can pin it.
    rep.check("C0", "旋钮寄存器 == 契约 §6.4 的 cg/rc", contract_knob_register(),
              knob_register())
    rep.check("C0", "旋钮只写运行模式 monitor 行（cfx_smon；不写 cfx_hart，"
              "ISS-455）", (True, False), knob_rows_written())
    rep.stat(f"bit={bit:#x} cfx_hart={d['hart']} timer_src={d['timer']:#x} "
             f"freq={d['freq']} hz={d['hz']} period={d['period']}")

    codes = k2time.kernel_selfcheck_codes()
    low, high = spec["ranges"]["guest"]
    rep.check("C0", f"自检码全在 guest FAIL 段（{hex(low)}-{hex(high)}）", {},
              {name: value for name, value in codes.items()
               if not (low <= value <= high)})
    values = list(codes.values())
    rep.check("C0", "自检码互不重复（跨 head/setup/k1_pt/trap/time/irq/irq_test）",
              True, len(values) == len(set(values)))
    rep.check("C0", "扫描面覆盖本任务新文件（kernel/k2_irq_test.c）", True,
              any("kernel/k2_irq_test.c" in name for name in codes))
    rep.stat("自检码 " + " ".join(f"{name.split('/')[-1].split(':')[0]}"
                                  f".{name.split(':')[-1]}={hex(v)}"
                                  for name, v in sorted(codes.items())
                                  if "irq_test" in name))


def check_image_meta(rep: Report, rc: int, text: str, cmd: list[str],
                     d: dict) -> None:
    cfg = d["config"]
    for symbol, value in (("CONFIG_DADAO_K2_IRQ_TEST", "y"),
                          ("CONFIG_DADAO_K2_TIME_STOP", "y"),
                          ("CONFIG_DADAO_K2_TIME_CASE", "0")):
        line = f"{symbol}={value}"
        rep.check("C1", f"镜像配置：{line}", line,
                  next((ln for ln in cfg.splitlines()
                        if ln.startswith(symbol + "=")), "<unset>"))
    for symbol in ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP",
                   "CONFIG_DADAO_K2_TRAP_SELFTEST"):
        rep.check("C1", f"镜像配置：{symbol} 未设", [],
                  [ln for ln in cfg.splitlines()
                   if ln.startswith(symbol + "=")])
    rep.check("C1", "guest rc（SYS_EXIT 子码）", 0, rc)
    rep.check("C1", "命令行无 -d（不用逐指令日志）", True,
              "-d" not in cmd and "-D" not in cmd)
    rep.check("C1", "输出无 panic/oops/BUG 痕迹", [],
              [ln for ln in text.splitlines()
               if re.search(r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|Call Trace)",
                            ln)])
    rep.check("C1", "输出无具名异常终止（生产通道不取异常）", [],
              [ln for ln in text.splitlines() if ln.startswith("dadao: ")])
    rep.check("C1", "输出无具名自检失败", [],
              [ln for ln in text.splitlines() if ln.startswith("K2 fail: ")])


def check_order(rep: Report, text: str) -> None:
    lines = text.splitlines()
    order: list[tuple[str, int]] = []
    for stage, pattern in STAGES:
        hits = [i for i, line in enumerate(lines) if re.match(pattern, line)]
        rep.check("C1", f"阶段 {stage} 出现 1 次", 1, len(hits))
        if hits:
            order.append((stage, hits[0]))
    rep.check("C1", "阶段顺序 == 常量表顺序", [s for s, _ in STAGES],
              [s for s, _ in order])
    where = dict(order)
    for first, second in ORDER_PAIRS:
        rep.check("C1", f"顺序约束：{first} 先于 {second}", True,
                  first in where and second in where
                  and where[first] < where[second])
    non_empty = [line for line in lines if line.strip()]
    rep.check("C1", "退出标记是最后一行", True,
              bool(non_empty) and non_empty[-1].startswith("K2 irq: done"))


def check_mask_axes(rep: Report, text: str, d: dict) -> None:
    """The two axes init_IRQ opened are still the ones the knob rides on."""
    m = IRQ_MASK.search(text)
    if not m:
        rep.check("C1", "两轴 mask 行存在", "存在", "缺失")
        return
    smon, hart, glob = ints(m.group(1, 2, 3))
    bit = d["bit"]
    rep.check("C1", "源轴 cfx_smon 行已放开该位（运行模式 monitor 行，§5.2 step 3）",
              0, smon & bit)
    rep.check("C1", "cfx_hart 行未被内核写过（仍是复位值，该位屏蔽，ISS-455）",
              bit, hart & bit)
    rep.check("C1", "全局轴已放开该位（帧内由硬件接管，不是旋钮）", 0, glob & bit)
    rep.check("C1", "mask 位 = 目标 cfxha", bit, int(m.group(5), 0))


# ---------------------------------------------------------------------------
# P1/P3/P5: value semantics of the knob
# ---------------------------------------------------------------------------

def check_p1(rep: Report, text: str, d: dict) -> None:
    m = P1.search(text)
    if not m:
        rep.check("P1", "P1 行存在", "存在", "缺失")
        return
    before_smon, before_hart, flags, masked_smon, masked_hart, rest_smon, \
        rest_hart = ints(m.groups())
    bit = d["bit"]
    # Absolute anchor (ISS-457): contract-see §3 pins `cfx_intr_mask`'s reset
    # value to all-ones and the kernel's single knob only ever clears the source
    # bits it owns, so the saved word must be exactly "all-ones minus that bit".
    # A truncated save stays self-consistent everywhere else — including the row
    # `init_IRQ` prints, because start_kernel's own `local_irq_*` calls run
    # through the same save and have already written the truncated word back
    # (measured) — so the reset value is the only anchor left.
    all_ones = (1 << 64) - 1
    rep.check("P1", "save 的整字 == 复位全 1 只清源位（64 位，高位参与）",
              all_ones & ~bit, before_smon)
    rep.check("P1", "before: cfx_hart 行的源位仍屏蔽（内核从未写过它）", bit,
              before_hart & bit)
    rep.check("P1", "save 后 cfx_smon 行置位源位", before_smon | bit,
              masked_smon)
    rep.check("P1", "save 返回的是保存前的整字", before_smon, flags)
    rep.check("P1", "save 没有写 cfx_hart 行（值不变）", before_hart, masked_hart)
    rep.check("P1", "restore 后 cfx_smon 逐位等于保存值", flags, rest_smon)
    rep.check("P1", "restore 后整字 == 复位全 1 只清源位（逐位复原的绝对锚点）",
              all_ones & ~bit, rest_smon)
    rep.check("P1", "restore 后 cfx_smon 回到保存前", before_smon, rest_smon)
    rep.check("P1", "restore 后 cfx_hart 行仍不变（旋钮只写 monitor 行）",
              before_hart, rest_hart)


def check_p3(rep: Report, text: str, d: dict) -> None:
    m = P3.search(text)
    if not m:
        rep.check("P3", "P3 行存在", "存在", "缺失")
        return
    before_smon, before_hart, outer, inner, inner_smon, inner_hart, \
        outer_smon, outer_hart = ints(m.groups())
    bit = d["bit"]
    rep.check("P3", "外层 save 返回保存前的整字", before_smon, outer)
    rep.check("P3", "内层 save 返回外层值 | 源位", outer | bit, inner)
    rep.check("P3", "内层 restore 后 cfx_smon 仍屏蔽（外层未恢复）", inner,
              inner_smon)
    rep.check("P3", "内层 restore 后 cfx_hart 行仍不变", before_hart, inner_hart)
    rep.check("P3", "外层 restore 后 cfx_smon 回到最初", before_smon, outer_smon)
    rep.check("P3", "外层 restore 后 cfx_hart 行仍不变", before_hart, outer_hart)
    rep.check("P3", "源位在最终状态是放开的（嵌套没有泄漏成屏蔽）", 0,
              outer_smon & bit)


P5_STATES = ("disable", "enable", "save", "restore")


def check_p5(rep: Report, text: str, d: dict) -> None:
    bit = d["bit"]
    rows = {}
    for state, flags, disabled, flags_disabled, smon, hart in P5.findall(text):
        rows[state] = (int(flags, 0), int(disabled), int(flags_disabled),
                       int(smon, 0), int(hart, 0))
    rep.check("P5", "四个状态各一行", sorted(P5_STATES), sorted(rows))
    if sorted(rows) != sorted(P5_STATES):
        return
    for state in P5_STATES:
        flags, disabled, flags_disabled, smon, hart = rows[state]
        live = 1 if (smon & bit) else 0
        rep.check("P5", f"{state}: arch_irqs_disabled() == 现场 cfx_smon 位", live,
                  disabled)
        rep.check("P5", f"{state}: arch_irqs_disabled_flags(flags) == 位与结果",
                  1 if (flags & bit) else 0, flags_disabled)
        rep.check("P5", f"{state}: cfx_hart 行的源位仍屏蔽（旋钮不写它）", bit,
                  hart & bit)
    # The witness that the delivered cfx's row is never written: it holds one
    # value across all four states.
    rep.check("P5", "cfx_hart 行四态恒定（旋钮只写 monitor 行）", 1,
              len({rows[state][4] for state in P5_STATES}))
    # The three saved/live pairs have to differ, otherwise the "3 mask states"
    # claim would be vacuous.
    rep.check("P5", "disable 与 enable 的现场值不同", True,
              rows["disable"][3] != rows["enable"][3])
    rep.check("P5", "save 返回的字与现场寄存器不同（保存值 != 现场值）", True,
              rows["save"][0] != rows["save"][3])
    rep.check("P5", "save 返回的字 == 现场寄存器清掉源位", rows["save"][3] & ~bit,
              rows["save"][0])
    rep.check("P5", "restore 后 flags == 现场 cfx_smon 行", rows["restore"][3],
              rows["restore"][0])
    # Granularity anchor (ISS-457): `enable` may only clear the source bits; a
    # blanket write of 0 would also discard a policy the kernel does not own, and
    # every other P5 assertion stays green under it.
    rep.check("P5", "enable == disable 清掉源位（其余位保持）",
              rows["disable"][3] & ~bit, rows["enable"][3])


# ---------------------------------------------------------------------------
# P2: the masked window and its single merged delivery
# ---------------------------------------------------------------------------

def check_p2(rep: Report, text: str, d: dict) -> None:
    period = d["period"]
    m = P2_MASKED.search(text)
    if not m:
        rep.check("P2", "屏蔽窗口行存在", "存在", "缺失")
        return
    ticks, ctrl, window = int(m.group(1)), int(m.group(2), 0), int(m.group(3))
    rep.check("P2", "屏蔽窗内 tick 计数不前进", 0, ticks)
    rep.check("P2", "屏蔽窗内 ISTATUS 已置位（事件确实发生、只记 pending）", 1,
              (ctrl >> 2) & 1)
    rep.check("P2", "屏蔽窗 >= 3 个 period（现场派生）", True,
              window >= 3 * period)

    m = P2_RELEASED.search(text)
    if not m:
        rep.check("P2", "释放行存在", "存在", "缺失")
        return
    released, rel_window, elapsed = ints(m.groups())
    rep.check("P2", "释放后计数恰增 1（合并补投，不丢不多）", 1, released)
    rep.check("P2", "释放测量窗 == period/2（现场派生）", period // 2,
              rel_window)
    rep.check("P2", "投递在半个 period 内完成（不是周期重挂的那一次）", True,
              elapsed < rel_window)
    rep.stat(f"P2 masked={ticks} ctrl={ctrl:#x} window={window} "
             f"released={released} elapsed={elapsed}")


# ---------------------------------------------------------------------------
# P4: every entry overwrites cg9; the software copies the capture out and
# returns through smon (ADR-0061 R2: no "live frame", no `escape` async return)
# ---------------------------------------------------------------------------

def check_p4(rep: Report, text: str, d: dict) -> None:
    period = d["period"]
    f = P4_FRAME.search(text)
    a = P4_AFTER.search(text)
    if not f or not a:
        rep.check("P4", "帧内/帧后两行存在", "存在", "缺失")
        return
    tick, waited, ctrl, window, elapsed = ints(f.groups())
    after, gap, printed_period = ints(a.groups())
    rep.check("P4", "帧内窗口 == period/2（现场派生）", period // 2, window)
    rep.check("P4", "帧内已等满窗口（测量真实）", True, elapsed >= window)
    rep.check("P4", "帧内事件到期（ISTATUS 置位）", 1, (ctrl >> 2) & 1)
    # R2: a nested capture inside the handler overwrites cg9 instead of being
    # parked behind a "live frame" bit; the kernel copies the capture out and
    # returns through smon.  No hardware anti-reentry assertion is derivable
    # (the "waited" count is reported, not judged).
    rep.check("P4", "帧内报告的 period == freq/HZ", period, printed_period)
    # Return/copy path: the ticks that follow may not lose the one the capture
    # carries, so the post-return count never moves backwards.
    rep.check("P4", "返回后 tick 计数不倒退（软件搬运不丢帧）", True,
              after >= tick)
    rep.stat(f"P4 frame tick={tick} waited={waited} ctrl={ctrl:#x} "
             f"after={after} gap={gap} period={printed_period}")


# ---------------------------------------------------------------------------
# C9: totals and the masked exit
# ---------------------------------------------------------------------------

def check_totals(rep: Report, text: str, d: dict) -> None:
    m = ARMED.search(text)
    if not m:
        rep.check("C9", "arm 行存在", "存在", "缺失")
        return
    rep.check("C9", "arm 的 period == freq/HZ（现场派生）", d["period"],
              int(m.group(1)))
    m = TIME_INIT.search(text)
    if m:
        printed_freq, printed_hz, printed_period = ints(m.group(1, 2, 3))
        rep.check("C9", "内核报告的 freq/hz/period == 现场派生", (d["freq"],
                  d["hz"], d["period"]), (printed_freq, printed_hz,
                  printed_period))
    else:
        rep.check("C9", "time_init 行存在", "存在", "缺失")

    m = DONE.search(text)
    if not m:
        rep.check("C9", "退出行存在", "存在", "缺失")
        return
    ticks, mask = int(m.group(1)), int(m.group(2), 0)
    rep.check("C9", "本次启动的 tick 数 >= 用例结构强制的次数", True,
              ticks >= TICK_FLOOR)
    rep.check("C9", "退出序列在屏蔽下完成（源位仍置位）", True,
              bool(mask & d["bit"]))
    rep.stat(f"done ticks={ticks} mask={mask:#x} floor={TICK_FLOOR}")


# ---------------------------------------------------------------------------
# U1/U2/U3: hard-IRQ context, sched_clock and exception-table uaccess
# (m14-linux-044)
# ---------------------------------------------------------------------------

def check_u(rep: Report, text: str) -> None:
    m = U1.search(text)
    if not m:
        rep.check("U1", "U1（帧内）行存在", "存在", "缺失")
    else:
        inframe, hardirq, interrupt, irq_regs = ints(m.groups())
        rep.check("U1", "U1 是从中断 handler 的帧内测的", 1, inframe)
        # The gap 042 found: no entry point ever added HARDIRQ_OFFSET, so
        # in_hardirq() was 0 for ever.  CONFIG_GENERIC_IRQ_ENTRY alone is not
        # the switch -- the call site (irq_enter_rcu) is.
        rep.check("U1", "in_hardirq() 在中断 handler 内为 1（不再恒 0）", 1,
                  hardirq)
        rep.check("U1", "in_interrupt() 的硬中断分量已计入", True,
                  interrupt >= 1)
        rep.stat(f"U1 in_hardirq={hardirq} in_interrupt={interrupt} "
                 f"irq_regs={irq_regs}")

    m = U2.search(text)
    if not m:
        rep.check("U2", "sched_clock 采样行存在", "存在", "缺失")
    else:
        t0, s0, t1, s1, t2, s2, dcfx1, dsc1, dcfx2, dsc2 = ints(m.groups())
        # cfx_time counts nanoseconds (contract-see §3), so the generic scaling
        # the registered source gets is 1 count = 1 ns.  The two reads of one
        # sample are not atomic, so the increments agree up to the skew between
        # them; over a 50 ms window a jiffies-based clock (HZ=100) would be off
        # by a whole 10 ms period, i.e. ~20 %.  1 % is a source-identity bound
        # that still leaves the sampling skew order-of-magnitude room.
        skew1 = abs(dsc1 - dcfx1)
        skew2 = abs(dsc2 - dcfx2)
        rep.check("U2", "sched_clock 与 cfx_time 同源（增量差 < 1 %，段 1）", True,
                  skew1 * 100 <= dcfx1)
        rep.check("U2", "sched_clock 与 cfx_time 同源（增量差 < 1 %，段 2）", True,
                  skew2 * 100 <= dcfx2)
        rep.check("U2", "两段测量都有推进（不是零增量自证）", True,
                  dcfx1 > 0 and dcfx2 > 0)
        rep.check("U2", "sched_clock 单调递增", True,
                  s1 > s0 and s2 > s1)
        rep.check("U2", "cfx_time 单调递增", True, t1 > t0 and t2 > t1)
        rep.stat(f"U2 t0={t0} s0={s0} t1={t1} s1={s1} t2={t2} s2={s2} "
                 f"dcfx={dcfx1}/{dcfx2} dsc={dsc1}/{dsc2} "
                 f"skew={skew1}/{skew2}")

    m = U3.search(text)
    if not m:
        rep.check("U3", "uaccess 行存在", "存在", "缺失")
    else:
        bad, size, frm, to, err = ints(m.groups())
        rep.check("U3", "坏地址在用户窗口内（不是被 access_ok 挡掉的）", True,
                  0 < bad < (1 << 41))
        rep.check("U3", "copy_from_user 返回未拷贝字节数 == 长度（-EFAULT）", size,
                  frm)
        rep.check("U3", "copy_to_user 返回未写字节数 == 长度（-EFAULT）", size, to)
        rep.check("U3", "调用点看到的 errno == -EFAULT", -errno.EFAULT, err)
        rep.check("U3", "本次启动没有因此停机（done 行仍在）", True,
                  bool(DONE.search(text)))
        rep.stat(f"U3 bad={bad:#x} size={size} from={frm} to={to} errno={err}")


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------

def run_checks(rc: int, text: str, cmd: list[str], spec: dict, *,
               static: bool = True, cfg: str | None = None) -> Report:
    rep = Report()
    d = derivation(cfg)
    if static:
        check_static(rep, spec)
    check_image_meta(rep, rc, text, cmd, d)
    check_order(rep, text)
    check_mask_axes(rep, text, d)
    check_p1(rep, text, d)
    check_p3(rep, text, d)
    check_p5(rep, text, d)
    check_p2(rep, text, d)
    check_p4(rep, text, d)
    check_u(rep, text)
    check_totals(rep, text, d)
    return rep


def run_gate(rep: Report) -> dict:
    if config() != 0:
        raise SystemExit("k2_irq_probe: image build failed")
    image = freeze_image("irq")     # this image, before anyone rebuilds
    rom = firmware("irq")
    rc, text, cmd = boot("irq", rom, kernel=image["kernel"])
    return {"rc": rc, "text": text, "cmd": cmd, "config": image["config"]}


# ---------------------------------------------------------------------------
# --selfcheck: every group flips on a mutated capture
# ---------------------------------------------------------------------------

def run_selfcheck(result: dict, spec: dict) -> int:
    problems: list[str] = []
    rc, text, cmd = result["rc"], result["text"], result["cmd"]

    mutations = [
        ("P1", lambda t: re.sub(r"(restored_hart=)\S+", r"\g<1>0x0", t),
         "restore 写了 cfx_hart 行（该行应恒定不变）"),
        ("P3", lambda t: re.sub(r"(inner_hart=)\S+", r"\g<1>0xffffffffffff7fff",
                                t), "内层 restore 改了 cfx_hart 行（该行应恒定）"),
        ("P1", lambda t: re.sub(
            r"(P1: before_smon=)0x\S+( before_hart=\S+ flags=\S+ "
            r"masked_smon=\S+ masked_hart=\S+ restored_smon=\S+ "
            r"restored_hart=)\S+", r"\g<1>0xffff7fff\g<2>0xffff7fff", t),
         "save 只带回低 32 位（与契约复位全 1 失配）"),
        ("P5", lambda t: re.sub(r"(state=disable flags=\S+ disabled=)1",
                                r"\g<1>0", t), "屏蔽态下 irqs_disabled() 说没屏蔽"),
        ("P5", lambda t: re.sub(
            r"(state=enable flags=\S+ disabled=\d+ flags_disabled=\d+ smon=)\S+"
            r"( hart=)\S+", r"\g<1>0x0\g<2>0x0", t),
         "enable 把整行写 0（其余位没保持）"),
        ("P2", lambda t: re.sub(r"(P2: masked ticks=)0", r"\g<1>3", t),
         "屏蔽窗内照样 tick"),
        ("P4", lambda t: re.sub(r"(P4: frame tick=)\d+", r"\g<1>9999", t),
         "返回后 tick 倒退（搬运丢帧）"),
        ("C9", lambda t: re.sub(r"(done ticks=\d+ mask=)\S+", r"\g<1>0x0", t),
         "退出时掩码已被放开"),
        ("C1", lambda t: re.sub(r"^K2 irq: done ticks=\d+ mask=\S+\n", "", t,
                                flags=re.MULTILINE), "删掉退出标记行"),
        # m14-linux-044: the three gaps this probe now covers.
        ("U1", lambda t: re.sub(r"(in_hardirq=)1", r"\g<1>0", t),
         "没有进硬中断记账（in_hardirq 恒 0）"),
        ("U2", lambda t: re.sub(r"(dcfx1=\d+ dsc1=)\d+", r"\g<1>0", t),
         "sched_clock 不与 cfx_time 同源"),
        ("U3", lambda t: re.sub(r"(size=8 from=)8", r"\g<1>0", t),
         "坏用户指针没有被修复成 EFAULT"),
    ]
    for cid, mutate, why in mutations:
        rep = run_checks(rc, mutate(text), cmd, spec, static=False,
                         cfg=result["config"])
        red = [msg for msg in rep.fails if msg.startswith(cid)]
        print(f"  [{'PASS' if red else 'FAIL'}] selfcheck {cid} | "
              f"注入「{why}」⇒ 期望={cid} 变红 实际={red[0] if red else '未变红'}",
              flush=True)
        if not red:
            problems.append(f"selfcheck {cid}: 未变红（{why}）")

    # C0 must flip too: the header constant is where the bit is defined.
    bit_ok = True
    try:
        declared_source_bits()
    except SystemExit:
        bit_ok = False
    print(f"  [{'PASS' if bit_ok else 'FAIL'}] selfcheck C0 | 期望=头文件可解析 "
          f"实际={'可解析' if bit_ok else '缺失'}", flush=True)
    if not bit_ok:
        problems.append("selfcheck C0: 头文件常量不可解析")

    rep = run_checks(rc, text, cmd, spec, cfg=result["config"])
    print(f"  [{'PASS' if not rep.fails else 'FAIL'}] selfcheck 对照 未改动 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
    if rep.fails:
        problems.append(f"selfcheck 对照: {rep.fails[0]}")

    total = len(mutations) + 2
    if problems:
        print(f"k2_irq_probe --selfcheck: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"k2_irq_probe --selfcheck: PASS ({total}/{total} 组可翻转 + 对照)")
    return 0


# ---------------------------------------------------------------------------
# --inject: source injections, cp + md5 restore, green again
# ---------------------------------------------------------------------------

#: name -> (file, [(old, new), ...], expected rc, output regex, forbidden regex,
#:          check groups that must go red)
INJECTIONS: dict[str, tuple] = {
    # ① restore writes zero instead of the saved word: the nested save loses its
    #    meaning (an inner restore re-enables).
    "restore-zero": (
        IRQFLAGS,
        [(("static inline void arch_local_irq_restore(unsigned long flags)\n"
           "{\n\tdadao_irq_mask_row_write(flags);\n}\n"),
          ("static inline void arch_local_irq_restore(unsigned long flags)\n"
           "{\n\t(void)flags;\n\tdadao_irq_mask_row_write(0UL);\t"
           "/* injected */\n}\n"))],
        0, r"^K2 irq: done ticks=", None, ("P3",),
    ),
    # ①b `restore` writes only the low 32 bits of the saved word: the round trip
    #    stops being bit-identical to the save, which is precisely what P1's
    #    "restore 后 cfx_smon 逐位等于保存值" pins.  (Task m14-linux-010 §2①: a
    #    truncating *restore* must reach the restore assertion, not only the
    #    save anchor that `flags-32` hits.)
    "restore-32": (
        IRQFLAGS,
        [(("static inline void arch_local_irq_restore(unsigned long flags)\n"
           "{\n\tdadao_irq_mask_row_write(flags);\n}\n"),
          ("static inline void arch_local_irq_restore(unsigned long flags)\n"
           "{\n\tdadao_irq_mask_row_write(flags & 0xffffffffUL);\t"
           "/* injected: low half only */\n}\n"))],
        0, r"^K2 irq: done ticks=", None, ("P1",),
    ),
    # ② the knob is wired to the mode-level row (`cfx_smon cg8 rc1`) instead of
    #    the mode monitor's supv row: the register identity the gate pins (C0)
    #    goes red, and the run itself dies on the first `cg8` access — the
    #    firmware's `supv_cfxreg` delegation covers `cg2`, not `cg8`, so the
    #    kernel gets a named `CFXREG` instead of reaching its boot marker.
    "knob-on-global": (
        IRQFLAGS,
        [(("#define DADAO_IRQ_CG_SUPV\t\t2\t/* supv row, spec/DADAO-12 §3.3 */\n"
           "#define DADAO_IRQ_RC_SUPV_CFX_INTR_MASK\t4\n"),
          ("#define DADAO_IRQ_CG_SUPV\t\t8\t/* injected: global row */\n"
           "#define DADAO_IRQ_RC_SUPV_CFX_INTR_MASK\t1\n"))],
        ("monitor", "supv", "CFXREG"),
        r"^dadao: unrecoverable supv exception cause=CFXREG", r"^K2 irq: done",
        ("C0",),
    ),
    # ③ arch_irqs_disabled_flags() judged as `flags == 0` instead of a bit test.
    "flags-is-zero": (
        IRQFLAGS,
        [(("static inline int arch_irqs_disabled_flags(unsigned long flags)\n"
           "{\n\t/* \"does this knob value block a source the kernel cares about\" — a bit\n"
           "\t * test, not `flags == 0` (the mask is all-1 at reset, so zero means\n"
           "\t * something else). */\n"
           "\treturn (flags & DADAO_IRQ_SOURCE_BITS) != 0;\n}\n"),
          ("static inline int arch_irqs_disabled_flags(unsigned long flags)\n"
           "{\n\treturn flags == 0;\t/* injected */\n}\n"))],
        0, r"^K2 irq: done ticks=", None, ("P5",),
    ),
    # ④ the P2 window is not wrapped in a critical section: the tick count keeps
    #    moving inside it (single hart, so the *handler's* own wrapper cannot
    #    drift — the window's wrapper is what P2 asserts on).
    "no-window-mask": (
        IRQ_TEST,
        [(("\tt0 = READ_ONCE(jiffies_64);\n\tlocal_irq_save(flags);\n"
           "\tk2_irq_wait_counts(window);\n"),
          ("\tt0 = READ_ONCE(jiffies_64);\n\tflags = 0;\t"
           "/* injected: no critical section */\n"
           "\tk2_irq_wait_counts(window);\n")),
         (("\treleased_at = dadao_read_time();\n\tlocal_irq_restore(flags);\n"),
          ("\treleased_at = dadao_read_time();\n\t(void)flags;\t"
           "/* injected */\n"))],
        0, r"^K2 irq: done ticks=", None, ("P2",),
    ),
    # ⑥ `save` hands back only the low 32 bits (ISS-457): the handler restores
    #    that word, so from the first tick on the monitor row genuinely holds
    #    0xffff7fff and every P1 read agrees with every other P1 read — including
    #    the row `init_IRQ` prints (start_kernel's earlier saves already wrote it
    #    back).  Only the contract's reset value (all-ones) minus the source bit
    #    can see the dropped high half.
    "flags-32": (
        IRQFLAGS,
        [(("\tunsigned long flags = dadao_irq_mask_row_smon();\n"
           "\n"
           "\tdadao_irq_mask_row_write(flags | DADAO_IRQ_SOURCE_BITS);\n"
           "\treturn flags;\n"),
          ("\tunsigned long flags = dadao_irq_mask_row_smon();\n"
           "\n"
           "\tdadao_irq_mask_row_write(flags | DADAO_IRQ_SOURCE_BITS);\n"
           "\treturn flags & 0xffffffffUL;\t"
           "/* injected: high half dropped */\n"))],
        0, r"^K2 irq: done ticks=", None, ("P1",),
    ),
    # ⑦ `enable` writes 0 instead of clearing only the source bits (ISS-457):
    #    the enable row loses the other sources' policy, and only the
    #    granularity anchor can see it.
    "enable-write-zero": (
        IRQFLAGS,
        [(("\tDADAO_CFX_WRITE(cfx_smon, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK,\n"
           "\t\t\tdadao_irq_mask_row_smon() & ~DADAO_IRQ_SOURCE_BITS);\n"),
          ("\tDADAO_CFX_WRITE(cfx_smon, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK, 0UL);\t/* injected */\n"))],
        0, r"^K2 irq: done ticks=", None, ("P5",),
    ),
    # ⑤ cfx_hart's row left alone: since m14-linux-010 that is the *shipped*
    #    state, so the "does the kernel still write a second row" direction is
    #    injected the other way round — k2_time_probe's C10 `two-row` mutation
    #    adds the write back and requires a red.  A mutation without a reachable
    #    FAIL path does not belong in this table.
    # ⑧ m14-linux-044: the hard-IRQ bookkeeping is the *call site*, not the
    #    Kconfig symbol.  Drop irq_enter_rcu()/irq_exit_rcu() and the handler
    #    stops being hard-IRQ context: U1's in_hardirq() goes back to 0 while
    #    the rest of the probe (and the boot) still passes — the mutation has a
    #    reachable FAIL and touches nothing else.
    "no-irq-enter": (
        TIME_C,
        [(("\tflags = arch_local_save_flags();\n\tirq_enter_rcu();\n"),
          ("\tflags = arch_local_save_flags();\t"
           "/* injected: no irq_enter_rcu */\n")),
         (("\tdadao_timer_interrupt();\n\tirq_exit_rcu();\n"),
          ("\tdadao_timer_interrupt();\t"
           "/* injected: no irq_exit_rcu */\n"))],
        0, r"^K2 irq U1: inframe=1 in_hardirq=0 ", None, ("U1",),
    ),
    # ⑨ m14-linux-044: without the exception-table fixup the bad user pointer is
    #    still a fault the page-fault channel cannot serve, so the boot ends in
    #    dadao_die() before the uaccess case can report -EFAULT — the "改前停机"
    #    the task asks to demonstrate.
    "no-fixup": (
        TRAPS_C,
        [(("\t\tif (fixup_exception(regs)) {\n"),
          ("\t\tif (0) {\t/* injected: no fixup_exception */\n"))],
        None, r"^dadao: unrecoverable supv exception", r"^K2 uaccess: ",
        ("U3",),
    ),
}


def run_inject(name: str, problems: list[str], spec: dict) -> None:
    rel, patches, want_rc, want_re, forbid, want_cids = INJECTIONS[name]
    if isinstance(want_rc, tuple):
        # ("monitor", mode, cause): the run must die with that §7.1 code.
        _kind, mode, cause = want_rc
        want_rc = k2time.monitor_code(spec, mode, cause)
    path = SOURCE / rel
    before = md5(path)
    backup = SCRATCH / f"inject-{name}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(path.read_bytes())
    text = path.read_text(encoding="utf-8")
    ok = True
    for old, new in patches:
        if text.count(old) != 1:
            problems.append(f"inject:{name}: 注入点不唯一（{text.count(old)} 处）")
            ok = False
            break
        text = text.replace(old, new, 1)
    if not ok:
        backup.unlink()
        return
    path.write_text(text, encoding="utf-8")
    if md5(path) == before:
        problems.append(f"inject:{name}: 注入是空操作（md5 未变）")
        path.write_bytes(backup.read_bytes())
        backup.unlink()
        return
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> {md5(path)[:8]}",
          flush=True)
    try:
        if config() != 0:
            problems.append(f"inject:{name}: 重建失败")
        else:
            image = freeze_image(f"inject_{name}")
            rc, text_out, _cmd = boot(f"inject_{name}", firmware("irq"),
                                      kernel=image["kernel"])
            cfg = image["config"]
            print(f"---- guest output ({name}, rc={rc}) ----")
            print(text_out.strip()[-2500:])
            print("----------------------------------------")
            checks = []
            if want_rc is not None:
                checks.append(("退出码", rc == want_rc, hex(want_rc), hex(rc)))
            hit = bool(re.search(want_re, text_out, re.MULTILINE))
            checks.append(("具名行", hit, want_re, "命中" if hit else "<none>"))
            if forbid is not None:
                absent = not re.search(forbid, text_out, re.MULTILINE)
                checks.append(("禁止行", absent, f"无 {forbid}",
                               "无" if absent else "有"))
            rep = run_checks(rc, text_out, _cmd, spec, cfg=cfg)
            for cid in want_cids:
                red = [msg for msg in rep.fails if msg.startswith(cid)]
                checks.append((f"断言 {cid} 变红", bool(red), f"{cid} 出现 FAIL",
                               red[0] if red else "未变红"))
            for label, good, expected, actual in checks:
                print(f"  [{'PASS' if good else 'FAIL'}] inject:{name} {label} | "
                      f"期望={expected} 实际={actual}", flush=True)
                if not good:
                    problems.append(f"inject:{name}: {label}（期望 {expected}，"
                                    f"实际 {actual}）")
    except Exception as exc:            # restore below even if the run blew up
        problems.append(f"inject:{name}: {type(exc).__name__}: {exc}")
    finally:
        path.write_bytes(backup.read_bytes())
        restored = md5(path)
        good = restored == before
        print(f"  [{'PASS' if good else 'FAIL'}] inject:{name} 还原 (cp) | "
              f"md5 期望={before[:8]} 实际={restored[:8]}", flush=True)
        if not good:
            problems.append(f"inject:{name}: 还原后 md5 不一致")
        backup.unlink()

    if config() != 0:
        problems.append(f"inject:{name}: 还原后重建失败")
        return
    image = freeze_image(f"inject_{name}_green")
    cfg = image["config"]
    rc, text_out, _cmd = boot(f"inject_{name}_green", firmware("irq"),
                              kernel=image["kernel"])
    rep = run_checks(rc, text_out, _cmd, spec, static=False, cfg=cfg)
    green = not rep.fails
    print(f"  [{'PASS' if green else 'FAIL'}] inject:{name} 还原后回绿 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
    if not green:
        problems.append(f"inject:{name}: 还原后仍失败（{rep.fails[0]}）")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured run: every check group must flip")
    ap.add_argument("--inject", action="store_true",
                    help="source injections: rebuild, assert FAIL, restore")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", action="append", default=[],
                    help="run only the named injection (with --inject)")
    args = ap.parse_args()

    if args.list:
        for name in INJECTIONS:
            print(f"inject:{name}")
        return 0

    if not k0.DEFAULT_QEMU or not Path(k0.DEFAULT_QEMU).is_file():
        print(f"k2_irq_probe: FAIL: {k0.DEFAULT_QEMU} missing; "
              f"run `make install-host`", file=sys.stderr)
        return 1
    if not Path(linux_paths.linux_build_dir()).is_dir():
        print("k2_irq_probe: FAIL: the kernel build tree is missing; "
              "run `make linux-defconfig`", file=sys.stderr)
        return 2
    SCRATCH.mkdir(parents=True, exist_ok=True)

    specs = k2trap.spec_exit_segments()

    if args.inject:
        problems: list[str] = []
        names = args.only or list(INJECTIONS)
        for name in names:
            run_inject(name, problems, specs)
        total = len(names)
        if problems:
            print(f"k2_irq_probe --inject: FAIL ({len(problems)} 问题)")
            for problem in problems:
                print("  - " + problem)
            return 1
        print(f"k2_irq_probe --inject: PASS ({total}/{total} 路注入按预期变红并还原)")
        return 0

    print(f"k2i: qemu={k0.DEFAULT_QEMU} md5={md5(Path(k0.DEFAULT_QEMU))[:8]}")
    rep = Report()
    result = run_gate(rep)

    if args.selfcheck:
        return run_selfcheck(result, specs)

    rep = run_checks(result["rc"], result["text"], result["cmd"], specs,
                     cfg=result["config"])
    if not rep.fails:
        print(f"k2_irq_probe: PASS ({rep.total}/{rep.total})")
    else:
        print(f"k2_irq_probe: FAIL ({len(rep.fails)}/{rep.total})")
        for failure in rep.fails:
            print("  - " + failure)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
