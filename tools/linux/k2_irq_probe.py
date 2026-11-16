#!/usr/bin/env python3
"""k2_irq_probe.py — M14 K2 interrupt-enable knob gate (`m14-linux-008`).

DADAO has no interrupt-enable state bit: the software IE knob is the per-cfx
`supv_cfx_intr_mask` (`cg2 rc4`), and the kernel maps `local_irq_*` onto it
(contract-see §6.4, ADR-0045 D3).  Whether that mapping is *real* can only be
seen from the physical register, so the probe image (`kernel/k2_irq_test.c`,
CONFIG_DADAO_K2_IRQ_TEST) reads both knob rows back with `cfx2rd` after every
step and prints the raw words; this gate is the judge.

Boot path under test:

    power -> hmon -> smon -> kernel entry -> setup_arch -> time_init ->
    async vector -> two mask axes -> arm -> TIMER tick -> [P1, P3, P5, P2] ->
    [P4: in-frame + after-escape] -> masked exit

What is derived live (nothing is restated):

  * the source bit -> `scalar cfx_hart 15` of `contracts/cfx-aliases.txt`, i.e.
    `1 << 15` — *not* the cause id (`TIMER = 1 << 10`, from contract-see §3);
    the two numbering schemes must not be mixed (contract-see §6.4);
  * the period -> the image's `CONFIG_HZ` and the contract's `cfx_time_freq`
    (`freq // HZ`), so a hardcoded count in the kernel goes red;
  * the exit codes / segments -> `spec/Kaiwu §7.1` (parsed by the K2
    exception gate, reused);
  * the self-check code space -> every `*FAIL*` constant the kernel sources
    define (same scan the K2 time gate uses, extended with this task's file).

Checks: C0 static inputs / C1 image + stage order / P1 save-restore round trip /
P2 masked window + merged re-delivery / P3 nested saves / P4 no nesting inside a
live frame and delivery right after `escape` / P5 `arch_irqs_disabled()` versus
the live register / C9 totals (masked exit).

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
import hashlib
import io
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.linux import k2_time_probe as k2time         # noqa: E402  (derivations)
from tools.linux import k2_trap_probe as k2trap        # noqa: E402  (§7.1 parser)
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

#: Every milestone symbol is pinned so the shared build tree cannot leak one
#: image's configuration into another.
IMAGE = [
    "CONFIG_DADAO_K1_EARLY_STOP=n",
    "CONFIG_DADAO_K2_EARLY_STOP=n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST=n",
    "CONFIG_DADAO_K2_TIME_STOP=y",
    "CONFIG_DADAO_K2_TIME_CASE=0",
    "CONFIG_DADAO_K2_IRQ_TEST=y",
]

#: Deliveries the case sequence forces: the first tick, the event merged out of
#: the P2 masked window, and the P4 event delivered after `escape`.  The floor is
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
    """``cg2 rc4`` from contract-see §6.4's single-knob bullet."""
    text = (REPO / ".tao" / "contracts" / "contract-see.md").read_text(
        encoding="utf-8")
    m = re.search(r"`cfx_smon_supv_cfx_intr_mask`（`cg(\d+) rc(\d+)`）", text)
    if not m:
        raise SystemExit("k2_irq_probe: contract-see §6.4 has no knob register")
    return int(m.group(1)), int(m.group(2))


def knob_rows_written() -> tuple[bool, bool]:
    """Does the write path cover *both* knob rows (ISS-454)?

    The values cannot show this (both rows start from the same word and the
    single-row bug only shows up as behaviour), so the row set is asserted on
    the source the same way the register identity is.
    """
    text = (SOURCE / IRQFLAGS).read_text(encoding="utf-8")
    m = re.search(r"static inline void dadao_irq_mask_row_write"
                  r"\(unsigned long value\)\s*\{(.*?)\n\}", text, re.S)
    body = m.group(1) if m else ""
    # Match the *write*, not the bare name: a comment naming the missing row
    # must not satisfy the check.
    return (bool(re.search(r"DADAO_CFX_WRITE\(cfx_smon\s*,", body)),
            bool(re.search(r"DADAO_CFX_WRITE\(cfx_hart\s*,", body)))


def derivation() -> dict:
    """Everything the checks compare against, read once."""
    hart = k2time.cfxha("cfx_hart")
    freq = k2time.contract_freq()
    cfg = (Path(linux_paths.linux_build_dir()) / ".config").read_text(
        encoding="utf-8")
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


def firmware(tag: str) -> str:
    k0.load_contract()
    if not k0.ABI:
        raise SystemExit("k2_irq_probe: the boot contract projection is empty")
    out = SCRATCH / f"bootrom_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(out), hmon_defs=[],
                             name=f"bootrom_k0_{tag}.bin")


def boot(tag: str, rom: str,
         timeout: int | None = None) -> tuple[int, str, list[str]]:
    kernel = kernel_path()
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
    rep.check("C0", "源位 = 1 << 目标 cfxha（不是 TIMER 的 cause id）", bit,
              declared_source_bits())
    rep.check("C0", "源位 != TIMER cause id（两套编号不混用）", True,
              bit != d["timer"])
    # Register identity is a *static* property: with the knob on another row the
    # printed values stay self-consistent (both rows carry the same default and
    # init_IRQ opens both), so only the source can pin it.
    rep.check("C0", "旋钮寄存器 == 契约 §6.4 的 cg/rc", contract_knob_register(),
              knob_register())
    rep.check("C0", "旋钮写入覆盖两行（cfx_smon + 投递过的 cfx_hart）",
              (True, True), knob_rows_written())
    rep.stat(f"bit={bit:#x} cfx_hart={d['hart']} timer_cause={d['timer']:#x} "
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
    rep.check("C1", "源轴 cfx_smon 行已放开该位（旋钮行）", 0, smon & bit)
    rep.check("C1", "源轴 cfx_hart 行已放开该位（首投后当前 cfx 行）", 0,
              hart & bit)
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
    rep.check("P1", "两行稳态值相同（单字保存的前提）", before_smon, before_hart)
    rep.check("P1", "save 后 cfx_smon 行置位源位", before_smon | bit,
              masked_smon)
    rep.check("P1", "save 后 cfx_hart 行置位源位", before_hart | bit,
              masked_hart)
    rep.check("P1", "save 返回的是保存前的整字", before_smon, flags)
    rep.check("P1", "restore 后 cfx_smon 逐位等于保存值", flags, rest_smon)
    rep.check("P1", "restore 后 cfx_hart 逐位等于保存值", flags, rest_hart)
    rep.check("P1", "restore 后两行都回到保存前", before_smon, rest_smon)


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
    rep.check("P3", "内层 restore 后 cfx_hart 仍屏蔽", inner, inner_hart)
    rep.check("P3", "外层 restore 后 cfx_smon 回到最初", before_smon, outer_smon)
    rep.check("P3", "外层 restore 后 cfx_hart 回到最初", before_hart, outer_hart)
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
        rep.check("P5", f"{state}: 现场 cfx_smon 与 cfx_hart 的源位一致", True,
                  bool(smon & bit) == bool(hart & bit))
        rep.check("P5", f"{state}: arch_irqs_disabled() == 现场寄存器", live,
                  disabled)
        rep.check("P5", f"{state}: arch_irqs_disabled_flags(flags) == 位与结果",
                  1 if (flags & bit) else 0, flags_disabled)
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
# P4: a live frame blocks nesting; `escape` delivers the parked event
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
    rep.check("P4", "帧内不再进第二次 tick（global 仍挡）", 0, waited)
    rep.check("P4", "帧内报告的 period == freq/HZ", period, printed_period)
    rep.check("P4", "escape 后补投恰 +1", tick + 1, after)
    rep.check("P4", "补投紧跟在帧结束之后（不是周期重挂那一次）", True,
              gap < period // 2)
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
# the gate
# ---------------------------------------------------------------------------

def run_checks(rc: int, text: str, cmd: list[str], spec: dict, *,
               static: bool = True) -> Report:
    rep = Report()
    d = derivation()
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
    check_totals(rep, text, d)
    return rep


def run_gate(rep: Report) -> dict:
    if config() != 0:
        raise SystemExit("k2_irq_probe: image build failed")
    rom = firmware("irq")
    rc, text, cmd = boot("irq", rom)
    return {"rc": rc, "text": text, "cmd": cmd}


# ---------------------------------------------------------------------------
# --selfcheck: every group flips on a mutated capture
# ---------------------------------------------------------------------------

def run_selfcheck(result: dict, spec: dict) -> int:
    problems: list[str] = []
    rc, text, cmd = result["rc"], result["text"], result["cmd"]

    mutations = [
        ("P1", lambda t: re.sub(r"(restored_hart=)\S+", r"\g<1>0x0", t),
         "restore 后 cfx_hart 行没有回到保存值"),
        ("P3", lambda t: re.sub(r"(inner_hart=)\S+", r"\g<1>0xffffffffffff7fff",
                                t), "内层 restore 就把屏蔽放开了"),
        ("P5", lambda t: re.sub(r"(state=disable flags=\S+ disabled=)1",
                                r"\g<1>0", t), "屏蔽态下 irqs_disabled() 说没屏蔽"),
        ("P2", lambda t: re.sub(r"(P2: masked ticks=)0", r"\g<1>3", t),
         "屏蔽窗内照样 tick"),
        ("P4", lambda t: re.sub(r"(waited_ticks=)0", r"\g<1>1", t),
         "同一帧内进了第二次 tick"),
        ("C9", lambda t: re.sub(r"(done ticks=\d+ mask=)\S+", r"\g<1>0x0", t),
         "退出时掩码已被放开"),
        ("C1", lambda t: re.sub(r"^K2 irq: done ticks=\d+ mask=\S+\n", "", t,
                                flags=re.MULTILINE), "删掉退出标记行"),
    ]
    for cid, mutate, why in mutations:
        rep = run_checks(rc, mutate(text), cmd, spec, static=False)
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

    rep = run_checks(rc, text, cmd, spec)
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
    # ② the knob is wired to the mode-level row (`cfx_smon cg8 rc1`) instead of
    #    the per-cfx supv row: delivery still gets masked outside a frame, so the
    #    behavioural cases survive — what breaks is the register identity the
    #    gate pins (P1/P3/P5 read the *cfx* rows back).  See the task's
    #    completion area: the frame-time collision needs the frame path, which is
    #    injection `global-row-unmask` below.
    "knob-on-global": (
        IRQFLAGS,
        [(("#define DADAO_IRQ_CG_SUPV\t\t2\t/* supv row, spec/DADAO-12 §3.3 */\n"
           "#define DADAO_IRQ_RC_SUPV_CFX_INTR_MASK\t4\n"),
          ("#define DADAO_IRQ_CG_SUPV\t\t8\t/* injected: global row */\n"
           "#define DADAO_IRQ_RC_SUPV_CFX_INTR_MASK\t1\n")),
         (("static inline unsigned long dadao_irq_mask_row_hart(void)\n"
           "{\n\treturn DADAO_CFX_READ(cfx_hart, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\t      DADAO_IRQ_RC_SUPV_CFX_INTR_MASK);\n}\n"),
          ("static inline unsigned long dadao_irq_mask_row_hart(void)\n"
           "{\n\treturn DADAO_CFX_READ(cfx_smon, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\t      DADAO_IRQ_RC_SUPV_CFX_INTR_MASK);\t"
           "/* injected */\n}\n")),
         (("\tDADAO_CFX_WRITE(cfx_hart, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK, value);\n}"),
          ("\t/* injected: single mode-level row */\n}")),
         (("\tDADAO_CFX_WRITE(cfx_hart, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK,\n"
           "\t\t\tdadao_irq_mask_row_hart() & ~DADAO_IRQ_SOURCE_BITS);\n"),
          ("\t/* injected: single mode-level row */\n"))],
        0, r"^K2 irq: done ticks=", None, ("C0",),
    ),
    # ②b restore also clears the source bit in the mode-level global row: the
    #     frame's own protection is that row, so the P4 event is delivered
    #     *inside* the live frame — the hazard contract-see §6.3/§6.4 names.
    "global-row-unmask": (
        IRQFLAGS,
        [(("static inline void arch_local_irq_restore(unsigned long flags)\n"
           "{\n\tdadao_irq_mask_row_write(flags);\n}\n"),
          ("static inline void arch_local_irq_restore(unsigned long flags)\n"
           "{\n\tdadao_irq_mask_row_write(flags);\n"
           "\tDADAO_CFX_WRITE(cfx_smon, 8, 1,\n"
           "\t\t\tdadao_irq_mask_row_smon() & ~DADAO_IRQ_SOURCE_BITS);\t"
           "/* injected */\n}\n"))],
        None, r"^K2 irq P2: released ", r"^K2 irq P4: ", ("P4",),
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
    # ⑤ only cfx_smon's row is written, never the delivered cfx's row
    #    (ISS-454): after the first delivery the kernel runs in cfx_hart, so the
    #    "masked" window keeps ticking — the direct judge for the two-row rule.
    "only-smon-row": (
        IRQFLAGS,
        [(("\tDADAO_CFX_WRITE(cfx_smon, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK, value);\n"
           "\tDADAO_CFX_WRITE(cfx_hart, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK, value);\n"),
          ("\tDADAO_CFX_WRITE(cfx_smon, DADAO_IRQ_CG_SUPV,\n"
           "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK, value);\n"
           "\t/* injected: cfx_hart's row left alone (ISS-454) */\n"))],
        0, r"^K2 irq: done ticks=", None, ("C0", "P1", "P2"),
    ),
}


def run_inject(name: str, problems: list[str], spec: dict) -> None:
    rel, patches, want_rc, want_re, forbid, want_cids = INJECTIONS[name]
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
            rc, text_out, _cmd = boot(f"inject_{name}", firmware("irq"))
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
            rep = run_checks(rc, text_out, _cmd, spec)
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
    rc, text_out, _cmd = boot(f"inject_{name}_green", firmware("irq"))
    rep = run_checks(rc, text_out, _cmd, spec, static=False)
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

    rep = run_checks(result["rc"], result["text"], result["cmd"], specs)
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
