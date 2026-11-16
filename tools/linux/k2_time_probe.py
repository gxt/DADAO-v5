#!/usr/bin/env python3
"""k2_time_probe.py — M14 K2 clock/timer gate (`m14-linux-007`).

K2's second half is time: `cfx_time` (cfxha 34) offers a free-running 64-bit
count, the single-hart timer lives in `cfx_hart` (cfxha 15) and raises the
maskable asynchronous source `TIMER` (`1 << 10`, `cause_info = 0`) into
`cfx_hart`'s **supv** vector.  This gate boots the real kernel on the Vast
machine and checks that the kernel turns that into jiffies:

    power -> hmon -> smon -> kernel entry -> ... -> setup_arch ->
    time_init -> async vector -> two mask axes -> N TIMER ticks -> SYS_EXIT(0)

Everything expected here is derived live (nothing is restated):

  * the frequency -> `cg10 rc0 = cfx_time_freq = <value>` in
    `.tao/contracts/contract-see.md` §3 (and 1 count = 1 ns, so the count is a
    period in ns);
  * the mask bit index -> `contracts/cfx-aliases.txt` (`scalar cfx_hart 15`),
    while the *cause* id (`TIMER = 1 << 10`) comes from the same contract — the
    two numbering schemes must not be mixed (contract-see §6.4);
  * `HZ` -> the build tree's `.config` (`CONFIG_HZ`), and the period ->
    `freq // HZ`; the kernel's printed hz must equal the configured one, so a
    hardcoded constant in the kernel goes red;
  * the tick target N -> the kernel's own declaration (`DADAO_K2_TIME_TICKS`,
    printed by `time_init`), with a floor of 3 (K2 requires *consecutive* ticks);
  * the interval margin -> half a period, and it must survive with 4x headroom
    over the worst observed deviation (both printed as `[STAT]`);
  * the expected exit codes -> `spec/Kaiwu §7.1` (parsed by the K2
    exception gate, reused here) for the permission-negative run.

Images (each pins every symbol it depends on — the build tree is shared):

  time    CONFIG_DADAO_K2_TIME_CASE=0  both axes open -> N ticks -> exit 0
  imask   case 1                       + IMASK parks one event, release delivers
  source  case 2                       source axis closed -> no tick
  global  case 3                       global axis closed -> no tick

The permission-negative run (P6) is not an image but a **firmware variant**:
the same kernel boots against a BootROM whose hmon leaves `cfx_hart`/`cfx_time`
closed (`--defsym K2_TIME_PERM=0`), so the first `cfx_time` read in `time_init`
must be CFXPERM — proving the permission comes from the firmware and is not
default.

Checks: C0 static inputs / C1 image + stage order / C2 time base / C3 tick
series / C4 interval + margin / C5 stopped timer / C6 IMASK / C7 the two axes /
C8 permission negative / C9 live counts.

`--selfcheck` mutates the captured runs and shows every group flips.
`--inject` corrupts the kernel source, rebuilds, asserts the expected FAIL and
restores with ``cp`` + md5 (never ``git checkout``), then proves the image is
green again.

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (contract / image / build tree missing).
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

from tools.linux import k1_boot_probe as k1boot      # noqa: E402  (symbols)
from tools.linux import k2_trap_probe as k2trap      # noqa: E402  (§7.1 parser)
from tools.linux import make_defconfig as defconfig  # noqa: E402  (config slice)
from tools.linux import paths as linux_paths         # noqa: E402
from tools.qemu import k0_boot_probe as k0           # noqa: E402  (firmware, contract)

PROFILE = "vast"

TIMEOUT_QEMU = int(os.environ.get("K2T_QEMU_TIMEOUT", "180"))
TIMEOUT_BUILD = int(os.environ.get("K2T_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K2T_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-007") / "k2_time_probe")

CONTRACT_SEE = _REPO / ".tao" / "contracts" / "contract-see.md"
CFX_ALIASES = _REPO / "contracts" / "cfx-aliases.txt"
SOURCE = linux_paths.linux_source_dir()

#: Kernel paths the single-row variant (C10) mutates at run time.
TIME_C = "arch/dadao/kernel/time.c"
IRQ_C = "arch/dadao/kernel/irq.c"
IRQFLAGS_H = "arch/dadao/include/asm/irqflags.h"

#: The floor on consecutive ticks a K2 image must show.  This is the task's
#: capability requirement ("连续 N 次 TIMER tick"), not the expected count: the
#: expected count is the kernel's own declaration, read from the output.
TICK_FLOOR = 3

#: Images the gate builds.  Every milestone symbol is pinned so the shared build
#: tree cannot leak one image's configuration into another.
IMAGES: dict[str, list[str]] = {
    name: [
        "CONFIG_DADAO_K1_EARLY_STOP=n",
        "CONFIG_DADAO_K2_EARLY_STOP=n",
        "CONFIG_DADAO_K2_TRAP_SELFTEST=n",
        "CONFIG_DADAO_K2_TIME_STOP=y",
        "CONFIG_DADAO_K2_IRQ_TEST=n",   # m14-linux-008 image must not leak in
        f"CONFIG_DADAO_K2_TIME_CASE={case}",
    ]
    for name, case in (("time", 0), ("imask", 1), ("source", 2), ("global", 3))
}


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
# expectations derived from the contract / the build tree (never restated)
# ---------------------------------------------------------------------------

def contract_freq() -> int:
    """`cfx_time_freq` of contract-see §3 (`cg10 rc0 = ... = <value>`)."""
    text = CONTRACT_SEE.read_text(encoding="utf-8")
    m = re.search(r"cg10 rc0 = cfx_time_freq = ([0-9_]+)", text)
    if not m:
        raise SystemExit("k2_time_probe: contract-see §3 cfx_time_freq not found")
    return int(m.group(1).replace("_", ""))


def contract_timer_cause() -> int:
    """The `TIMER` cause id of contract-see §3 (`1 << 10`)."""
    text = CONTRACT_SEE.read_text(encoding="utf-8")
    m = re.search(r"到期触发可屏蔽 `TIMER`（`1 << (\d+)`）", text)
    if not m:
        raise SystemExit("k2_time_probe: contract-see §3 TIMER id not found")
    return 1 << int(m.group(1))


def cfxha(name: str) -> int:
    """`scalar <name> <ha> canonical` from the cfx alias projection."""
    for line in CFX_ALIASES.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^scalar\s+(\w+)\s+(\d+)\s+canonical$", line.strip())
        if m and m.group(1) == name:
            return int(m.group(2))
    raise SystemExit(f"k2_time_probe: {CFX_ALIASES.name} has no scalar {name}")


def config_hz(cfg: str) -> int:
    """`CONFIG_HZ` of the image under test (the .config captured with it)."""
    m = re.search(r"^CONFIG_HZ=(\d+)$", cfg, re.MULTILINE)
    if not m:
        raise SystemExit("k2_time_probe: CONFIG_HZ not in the image's .config")
    return int(m.group(1))


def snapshot() -> dict:
    """What belongs to *this* image: its .config and its symbol table.

    The build tree is shared and every image overwrites it, so these have to be
    read right after the image was built, never at the end of the run.
    """
    return {"config": (Path(linux_paths.linux_build_dir()) / ".config").read_text(
                encoding="utf-8"),
            "syms": k1boot.symbols(kernel_path())}


def declared_ticks() -> int:
    """`DADAO_K2_TIME_TICKS` as the kernel source declares it."""
    path = SOURCE / "arch/dadao/include/asm/time.h"
    m = re.search(r"^#define\s+DADAO_K2_TIME_TICKS\s+(\d+)\s*$",
                  path.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        raise SystemExit(f"k2_time_probe: {path} has no DADAO_K2_TIME_TICKS")
    return int(m.group(1))


def kernel_selfcheck_codes() -> dict[str, int]:
    """Every boot-verdict constant the kernel sources define.

    The guest segment (0x01-0x7f) is the kernel's own verdicts; scanning *all*
    of them — including the files this task adds — is what keeps a new check
    point from silently landing in the monitor segment (where §7.1 would read it
    as an abnormal exception) or colliding with an existing one.
    """
    pat = re.compile(r"^#define\s+((?:FAIL|K2_FAIL|DADAO_TRAP_BAD_POLICY)\w*)\s+"
                     r"(0x[0-9a-fA-F]+|\d+)\s*(?:/\*|$)", re.MULTILINE)
    files = ("arch/dadao/kernel/head.S", "arch/dadao/kernel/setup.c",
             "arch/dadao/mm/k1_pt.c", "arch/dadao/kernel/traps.c",
             "arch/dadao/include/asm/trap.h", "arch/dadao/kernel/time.c",
             "arch/dadao/kernel/irq.c", "arch/dadao/kernel/k2_irq_test.c")
    codes: dict[str, int] = {}
    for rel in files:
        path = SOURCE / rel
        if not path.is_file():
            raise SystemExit(f"k2_time_probe: {path} missing; "
                             f"run `make fetch apply-series`")
        for name, value in pat.findall(path.read_text(encoding="utf-8")):
            codes[f"{rel}:{name}"] = int(value, 0)
    return codes


def monitor_code(specs: dict, mode: str, cause: str) -> int:
    """``0xC0 | (mode << 4) | bit index`` — straight from §7.1."""
    low, _high = specs["ranges"]["monitor"]
    return low | (specs["modes"][mode] << 4) | specs["indices"][cause]


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def config(image: str) -> int:
    rc = defconfig.apply_config_lines(IMAGES[image])
    if rc != 0:
        print(f"k2_time_probe: FAIL: config slice for {image} rc={rc}",
              file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build {image} image (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def kernel_path() -> Path:
    return Path(linux_paths.linux_build_dir()) / "vmlinux"


_ROMS: dict[str, str] = {}


def firmware(tag: str, hmon_defs: list[str] | None = None) -> str:
    """BootROM for @tag; `K2_TIME_PERM=0` builds the permission-negative one."""
    if tag in _ROMS:
        return _ROMS[tag]
    k0.load_contract()
    if not k0.ABI:
        raise SystemExit("k2_time_probe: the boot contract projection is empty")
    out = SCRATCH / f"bootrom_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    rom = k0.build_firmware(str(out), hmon_defs=list(hmon_defs or ()),
                            name=f"bootrom_k0_{tag}.bin")
    _ROMS[tag] = rom
    return rom


def boot(tag: str, rom: str,
         timeout: int | None = None) -> tuple[int, str, list[str]]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k2_time_probe: {kernel} missing")
    log = SCRATCH / "log" / f"{tag}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [k0.DEFAULT_QEMU,
           "-machine", f"kaiwu-vast,bootrom-image={rom}",
           "-nographic",
           "-semihosting-config", "enable=on,target=native",
           "-kernel", str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=timeout or TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        # A run that never returns is a valid observation: keep what it printed
        # (that is the evidence *where* it stopped) and report 124.
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = err or out
    log.write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# parsing the kernel's own report
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
TICK = re.compile(r"^K2 tick (\d+): time=(\d+) jiffies=(\d+)$", re.MULTILINE)
SUMMARY = re.compile(r"^K2 time: ticks=(\d+) jiffies_delta=(\d+)$", re.MULTILINE)
AFTER_STOP = re.compile(r"^K2 time: after stop ticks=(\d+) window=(\d+)$",
                        re.MULTILINE)
DONE = re.compile(r"^K2 time: done ticks=(\d+) mask=(\S+)$",
                  re.MULTILINE)
IMASK = re.compile(r"^K2 imask: ctrl=(\S+) ticks=(\d+)$", re.MULTILINE)
IMASK_RELEASED = re.compile(r"^K2 imask: released ctrl=(\S+) ticks=(\d+)$",
                            re.MULTILINE)
AXIS = re.compile(r"^K2 axistest: axis=(\w+) ticks=(\d+) window=(\d+)$",
                  re.MULTILINE)

STAGE_ANCHORS = (
    ("bootinfo", r"^K1 bootinfo magic="),
    ("stack", r"^K1 stack sp="),
    ("ptw-vector", r"^K1 ptw vec  supv_excp_vector="),
    ("table", r"^K1 ptw map  ram_pa="),
    ("install", r"^K1 ptw post ptbr="),
    ("switch", r"^K1 ptw new  va="),
    ("table-done", r"^K1 ptw done: running on the kernel-built table$"),
    ("setup_arch", r"^K2 setup_arch: memblock_add "),
    ("time_init", r"^K2 time_init: freq="),
    ("irq-vector", r"^K2 irq: vec cfx_hart_supv_excp_vector="),
    ("irq-mask", r"^K2 irq: mask cfx_smon_supv_cfx_intr_mask="),
    ("arm", r"^K2 time: arm period="),
    ("ticks", r"^K2 tick 1: time="),
    ("summary", r"^K2 time: ticks="),
    ("after-stop", r"^K2 time: after stop ticks="),
    ("exit", r"^K2 time: done ticks="),
)

#: The asynchronous vector install must precede the first mask write, and the
#: mask writes must precede the arm — `spec/DADAO-12 §5.2 step 7` (a delivery
#: into an uninstalled vector is unrecoverable).  The stage table above already
#: encodes the whole order; these are the pairs the task calls out explicitly.
ORDER_PAIRS = (("time_init", "irq-vector"), ("irq-vector", "irq-mask"),
               ("irq-mask", "arm"))


def one(text: str, regex: re.Pattern) -> list[re.Match]:
    return list(regex.finditer(text))


def ints(groups) -> list[int]:
    return [int(g, 0) for g in groups]


# ---------------------------------------------------------------------------
# C1..C5: the production time image
# ---------------------------------------------------------------------------

def check_config(rep: Report, cfg: str, image: str, case: int) -> None:
    want = {
        "CONFIG_DADAO_K2_TIME_STOP": "y",
        "CONFIG_DADAO_K2_TIME_CASE": str(case),
    }
    for symbol, value in want.items():
        line = f"{symbol}={value}"
        rep.check("C1", f"{image} 镜像配置：{line}", line,
                  next((ln for ln in cfg.splitlines()
                        if ln.startswith(symbol + "=")), "<unset>"))
    for symbol in ("CONFIG_DADAO_K1_EARLY_STOP",
                   "CONFIG_DADAO_K2_EARLY_STOP"):
        rep.check("C1", f"{image} 镜像配置：{symbol} 未设", [],
                  [ln for ln in cfg.splitlines()
                   if ln.startswith(symbol + "=")])


def check_time_base(rep: Report, text: str, cfg_hz: int, freq: int) -> dict:
    m = TIME_INIT.search(text)
    if not m:
        rep.check("C2", "time_init 行存在", "存在", "缺失")
        return {}
    printed_freq, printed_hz, period, n, first = ints(m.groups())
    derived = printed_freq // printed_hz
    rep.check("C2", "printed freq == 契约 cfx_time_freq", freq, printed_freq)
    rep.check("C2", "printed hz == .config CONFIG_HZ（不写死）", cfg_hz,
              printed_hz)
    rep.check("C2", "printed period == freq / hz（现场派生）", derived, period)
    rep.check("C2", "n_ticks == 内核源码声明（DADAO_K2_TIME_TICKS）",
              declared_ticks(), n)
    rep.check("C2", "n_ticks >= K2 下限（连续 tick 能力）", True,
              n >= TICK_FLOOR)
    rep.check("C2", "首读值 > 0（time 自复位起算，已走过一段启动时间）", True,
              first > 0)
    rep.check("C2", "首读值 < 1 秒（freq 个 count，现场派生）", True,
              first < printed_freq)
    rep.stat(f"freq={printed_freq} hz={printed_hz} period={period} "
             f"n_ticks={n} first={first}")
    # The interval check below uses the *derived* period: the kernel's printed
    # period is a claim of its own (C2 checks it), never the yardstick for its
    # own programming.
    return {"freq": printed_freq, "hz": printed_hz, "period": derived, "n": n}


def check_vector_and_masks(rep: Report, text: str, syms: dict,
                           hart: int, cause_id: int) -> None:
    m = IRQ_VEC.search(text)
    if not m:
        rep.check("C1", "异步向量安装行存在", "存在", "缺失")
    else:
        readback, want, mode = m.group(1), m.group(2), int(m.group(3))
        rep.check("C1", "cfx_hart 向量读回 == 写入（含 4 字节对齐）", want,
                  readback)
        rep.check("C1", "写入值 == dadao_async_excp 符号",
                  hex(syms["dadao_async_excp"]), want)
        rep.check("C1", "cfx_hart supv switch_run_mode == supv(2)", 2, mode)

    m = IRQ_MASK.search(text)
    if not m:
        rep.check("C1", "两轴 mask 行存在", "存在", "缺失")
        return
    smon, hart_row, global_row = ints(m.group(1, 2, 3))
    printed_ha, printed_bit = int(m.group(4)), int(m.group(5), 0)
    bit = 1 << hart
    rep.check("C7", "cfxha 现场读自 cg4 rc0 == 别名表的 cfx_hart", hart,
              printed_ha)
    rep.check("C7", "mask 位 = 目标 cfxha（不是 TIMER 的 cause id）", bit,
              printed_bit)
    rep.check("C7", "mask 位 != TIMER cause id（两套编号不混用）", True,
              printed_bit != cause_id)
    rep.check("C7", "源轴 cfx_smon 行已放开该位", 0, smon & bit)
    rep.check("C7", "源轴 cfx_hart 行已放开该位（投放后 inner_cfx 换到 15）",
              0, hart_row & bit)
    rep.check("C7", "全局轴 cfx_smon 行已放开该位", 0, global_row & bit)
    rep.stat(f"masks: smon_supv={smon:#x} hart_supv={hart_row:#x} "
             f"global={global_row:#x} bit={bit:#x}")


def check_series(rep: Report, text: str, base: dict) -> None:
    """C3/C4/C5: the tick series, the intervals and the stopped timer."""
    period = base.get("period")
    n = base.get("n")
    ticks = [(int(i), int(t), int(j)) for i, t, j in TICK.findall(text)]
    if not n:
        return
    rep.check("C3", "tick 行数 == 内核声明的 n_ticks", n, len(ticks))
    rep.check("C3", "tick 序号 == 1..n", list(range(1, len(ticks) + 1)),
              [i for i, _t, _j in ticks])
    times = [t for _i, t, _j in ticks]
    rep.check("C3", "time 严格单调递增", True,
              all(a < b for a, b in zip(times, times[1:])))
    jif = [j for _i, _t, j in ticks]
    rep.check("C3", "相邻 jiffies 前进 1", [1] * max(0, len(jif) - 1),
              [b - a for a, b in zip(jif, jif[1:])])

    m = SUMMARY.search(text)
    if not m:
        rep.check("C3", "汇总行存在", "存在", "缺失")
        return
    total, jdelta = ints(m.groups())
    rep.check("C3", "汇总 tick 数 == n_ticks", n, total)
    rep.check("C3", "汇总 jiffies 前进 == n_ticks", n, jdelta)

    if period and len(times) >= 2:
        deltas = [b - a for a, b in zip(times, times[1:])]
        devs = [abs(d - period) for d in deltas]
        margin = period // 2          # half a period, derived from the period
        rep.stat(f"tick deltas={deltas} deviations={devs} "
                 f"min={min(devs)} max={max(devs)} "
                 f"mean={sum(devs) // len(devs)} margin={margin}")
        rep.check("C4", "每个 tick 间隔与 period 的偏差 <= period/2", True,
                  all(dev <= margin for dev in devs))
        rep.check("C4", "余量 ≥ 实测最大偏差的 4 倍（不是写死的容差）", True,
                  4 * max(devs) <= margin)

    m = AFTER_STOP.search(text)
    if not m:
        rep.check("C5", "停止后控制行存在", "存在", "缺失")
        return
    after, window = ints(m.groups())
    rep.check("C5", "stop 之后不再有 tick", 0, after)
    rep.check("C5", "停止后等待窗 >= 2 个 period", True,
              bool(period) and window >= 2 * period)


def check_order(rep: Report, text: str) -> None:
    lines = text.splitlines()
    order: list[tuple[str, int]] = []
    for stage, pattern in STAGE_ANCHORS:
        hits = [i for i, line in enumerate(lines) if re.match(pattern, line)]
        rep.check("C1", f"阶段 {stage} 出现 1 次", 1, len(hits))
        if hits:
            order.append((stage, hits[0]))
    rep.check("C1", "阶段顺序 == 常量表顺序",
              [stage for stage, _ in STAGE_ANCHORS],
              [stage for stage, _ in order])
    rep.check("C1", "阶段行号严格递增", True,
              all(a[1] < b[1] for a, b in zip(order, order[1:])))
    where = dict(order)
    for first, second in ORDER_PAIRS:
        rep.check("C1", f"顺序约束：{first} 先于 {second}", True,
                  first in where and second in where
                  and where[first] < where[second])

    non_empty = [line for line in lines if line.strip()]
    rep.check("C1", "退出标记是最后一行", True,
              bool(non_empty) and non_empty[-1].startswith("K2 time: done"))
    rep.check("C1", "输出无 panic/oops/BUG 痕迹", [],
              [line for line in non_empty
               if re.search(r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|Call Trace)",
                            line)])
    rep.check("C1", "输出无具名异常终止（生产镜像不取异常）", [],
              [line for line in non_empty if line.startswith("dadao: ")])


def check_image(name: str, rc: int, text: str, cmd: list[str], rep: Report,
                snap: dict) -> dict:
    """All checks for one image; returns the derived time context."""
    cfg = snap["config"]
    syms = snap["syms"]
    case = {"time": 0, "imask": 1, "source": 2, "global": 3}[name]
    check_config(rep, cfg, name, case)

    rep.check("C1", f"{name} 镜像 guest rc（SYS_EXIT 子码）", 0, rc)
    rep.check("C1", f"{name} 镜像命令行无 -d（不用逐指令日志）", True,
              "-d" not in cmd and "-D" not in cmd)

    hart = cfxha("cfx_hart")
    cfxha("cfx_time")
    cause_id = contract_timer_cause()

    if name == "source" or name == "global":
        check_axis(rep, name, text, case)
        return {}

    check_order(rep, text)
    base = check_time_base(rep, text, config_hz(cfg), contract_freq())
    check_vector_and_masks(rep, text, syms, hart, cause_id)
    if name == "imask":
        check_imask(rep, text)
    check_series(rep, text, base)
    m = DONE.search(text)
    rep.check("C1", f"{name} 镜像退出 tick 数 == n_ticks", base.get("n"),
              int(m.group(1)) if m else "<missing>")
    # m14-linux-008: the exit sequence (stop + SYS_EXIT) runs with the software
    # IE knob closed, so the last line reports the mask and it must still block
    # the kernel's source bit.
    bit = 1 << hart
    rep.check("C1", f"{name} 镜像退出序列在屏蔽下完成（源位仍置位）", True,
              bool(m and (int(m.group(2), 0) & bit)))
    return base


def check_imask(rep: Report, text: str) -> None:
    """C6: IMASK parks the event, releasing IMASK delivers that one event."""
    m = IMASK.search(text)
    if not m:
        rep.check("C6", "IMASK 行存在", "存在", "缺失")
        return
    ctrl, ticks = int(m.group(1), 0), int(m.group(2))
    rep.check("C6", "IMASK=1 时 ctrl 读回 = ENABLE|IMASK|ISTATUS", 0b111, ctrl)
    rep.check("C6", "IMASK=1 时未投递（tick 计数不变）", 0, ticks)
    m = IMASK_RELEASED.search(text)
    if not m:
        rep.check("C6", "IMASK 释放行存在", "存在", "缺失")
        return
    ctrl2, ticks2 = int(m.group(1), 0), int(m.group(2))
    rep.check("C6", "释放后 ctrl 读回只剩 ENABLE（ISTATUS 已清）", 0b1, ctrl2)
    rep.check("C6", "释放投递被挂起的那一次事件（恰好 1）", 1, ticks2)


def check_axis(rep: Report, name: str, text: str, case: int) -> None:
    """C7: closing exactly one axis blocks delivery on its own."""
    m = AXIS.search(text)
    if not m:
        rep.check("C7", f"{name} 轴测试行存在", "存在", "缺失")
        return
    axis, ticks, window = m.group(1), int(m.group(2)), int(m.group(3))
    base = TIME_INIT.search(text)
    period = (int(base.group(1)) // int(base.group(2))) if base else 0
    rep.check("C7", f"{name} 镜像报告的轴 == case 选择", name, axis)
    rep.check("C7", f"{name} 镜像：该轴关闭 ⇒ 无 tick", 0, ticks)
    rep.check("C7", f"{name} 镜像：等待窗 >= 2 个 period（现场派生）", True,
              bool(period) and window >= 2 * period)

    mask = IRQ_MASK.search(text)
    if not mask:
        rep.check("C7", f"{name} 镜像 mask 行存在", "存在", "缺失")
        return
    smon, hart_row, global_row = ints(mask.group(1, 2, 3))
    bit = 1 << cfxha("cfx_hart")
    if name == "source":
        rep.check("C7", "source 镜像：源轴两行仍屏蔽", bit,
                  (smon | hart_row) & bit)
        rep.check("C7", "source 镜像：全局轴已放开（只关了一轴）", 0,
                  global_row & bit)
    else:
        rep.check("C7", "global 镜像：全局轴仍屏蔽", bit, global_row & bit)
        rep.check("C7", "global 镜像：源轴已放开（只关了一轴）", 0,
                  (smon | hart_row) & bit)


def check_single_row(rep: Report, rc: int, text: str, hart: int) -> None:
    """C10 (ISS-455 / m14-qemu-003): the source axis is the *running mode
    monitor's* row, not the current cfx's.

    The image is built from a kernel reduced at run time to writing only
    `cfx_smon`'s supv `cfx_intr_mask` row (`cg2 rc4`); `cfx_hart`'s row keeps
    its reset all-1 value.  spec/DADAO-12 §5.2 step 3 filters asynchronous
    sources on the mode monitor's `<mode>_cfx_intr_mask`, so the whole tick
    series must still complete.  A filter that reads the *current cfx's* row
    delivers exactly one tick after the first frame (current cfx = cfx_hart)
    and parks every later event in pending — m14-linux-007's measurement.
    """
    bit = 1 << hart
    m = IRQ_MASK.search(text)
    if not m:
        rep.check("C10", "single-row mask 行存在", "存在", "缺失")
        return
    smon, hart_row, _global = ints(m.group(1, 2, 3))
    rep.check("C10", "single-row：源轴只剩 cfx_smon 行放开该位", 0, smon & bit)
    rep.check("C10", "single-row：cfx_hart 行仍是复位值（该位屏蔽）", True,
              bool(hart_row & bit))
    declared = declared_ticks()
    rep.check("C10", "single-row：tick 行数 == 内核声明（首投后仍持续投递）",
              declared, len(TICK.findall(text)))
    m = DONE.search(text)
    rep.check("C10", "single-row：退出 tick 数 == 内核声明", declared,
              int(m.group(1)) if m else "<missing>")
    rep.check("C10", "single-row：guest rc（SYS_EXIT 子码）", 0, rc)


def check_permission(rep: Report, rc: int, text: str, specs: dict,
                     snap: dict) -> None:
    """C8: without the firmware's opening the first cfx_time read is CFXPERM."""
    want = monitor_code(specs, "supv", "CFXPERM")
    rep.check("C8", "firmware 未放行时 guest rc == §7.1 supv+CFXPERM", want, rc)
    rep.check("C8", "输出具名 CFXPERM 行", True,
              bool(re.search(r"^dadao: unrecoverable supv exception "
                             r"cause=CFXPERM\(0x80\)", text, re.MULTILINE)))
    # The software IE knob is real since m14-linux-008, so the kernel's *first*
    # cfx access is now the local_irq_* plumbing inside start_kernel, not the
    # cfx_time read in time_init.  Both live behind the same firmware opening,
    # which is what this case proves; pin the span and the fact that the denial
    # is a source-mask rejection (`info` = instruction word, not an address).
    syms = snap["syms"]
    m = re.search(r"cause=CFXPERM\(0x80\) ip=(\S+) info=(\S+)", text)
    ip = int(m.group(1), 0) if m else None
    info = int(m.group(2), 0) if m else None
    rep.check("C8", "首次触碰是 start_kernel 内的掩码拒绝（info = 指令字）", True,
              ip is not None and syms["start_kernel"] <= ip < syms["time_init"]
              and info <= 0xffffffff)
    rep.check("C8", "输出无 tick 行（没走到定时器）", [],
              [line for line in text.splitlines()
               if line.startswith("K2 tick ")])


# ---------------------------------------------------------------------------
# C10: the single-row variant (ISS-455 / m14-qemu-003)
# ---------------------------------------------------------------------------

#: Every kernel write to the *target cfx's* supv `cfx_intr_mask` row, removed at
#: run time so that `cfx_hart`'s row keeps its reset all-1 value and only the
#: running mode monitor's row (`cfx_smon cg2 rc4`) is ever opened.  This is a
#: source mutation with ``cp`` + md5 restore (never a patch-set edit): the kernel
#: writing both rows is m14-linux-008's state, narrowed by m14-linux-010.
SINGLE_ROW_PATCHES = (
    (IRQ_C,
     "\tmask = hart_supv_intr_mask() & ~bit;\n"
     "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_SUPV,\n"
     "\t\t\tCFX_SMON_RC_SUPV_CFX_INTR_MASK, mask);\n",
     "\t/* single-row variant: cfx_hart's row keeps its reset value */\n"),
    (IRQFLAGS_H,
     "\tDADAO_CFX_WRITE(cfx_hart, DADAO_IRQ_CG_SUPV,\n"
     "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK, value);\n",
     "\t/* single-row variant: cfx_hart's row left alone */\n"),
    (IRQFLAGS_H,
     "\tDADAO_CFX_WRITE(cfx_hart, DADAO_IRQ_CG_SUPV,\n"
     "\t\t\tDADAO_IRQ_RC_SUPV_CFX_INTR_MASK,\n"
     "\t\t\tdadao_irq_mask_row_hart() & ~DADAO_IRQ_SOURCE_BITS);\n",
     "\t/* single-row variant: cfx_hart's row left alone */\n"),
)


def single_row_run(rep: Report, hart: int) -> dict:
    """Build + boot the single-row image; returns the run for ``--selfcheck``.

    The source is patched in place and restored with ``cp`` + md5 in a
    ``finally`` block; the caller rebuilds the pristine ``time`` image before it
    interprets anything else (the noperm run does that explicitly).
    """
    originals: dict[str, bytes] = {}
    before_md5: dict[str, str] = {}
    texts: dict[str, str] = {}
    for rel, old, new in SINGLE_ROW_PATCHES:
        path = SOURCE / rel
        if rel not in originals:
            originals[rel] = path.read_bytes()
            before_md5[rel] = md5(path)
            texts[rel] = originals[rel].decode("utf-8")
        if texts[rel].count(old) != 1:
            raise SystemExit(f"k2_time_probe: single-row 注入点不唯一 "
                             f"({rel}: {texts[rel].count(old)} 处)")
        texts[rel] = texts[rel].replace(old, new, 1)
    try:
        for rel in originals:
            (SOURCE / rel).write_text(texts[rel], encoding="utf-8")
            print(f"  [PASS] single-row 注入 {rel} | md5 "
                  f"{before_md5[rel][:8]} -> {md5(SOURCE / rel)[:8]}",
                  flush=True)
        if md5(SOURCE / IRQ_C) == before_md5[IRQ_C]:
            raise SystemExit("k2_time_probe: single-row 注入是空操作（md5 未变）")
        if config("time") != 0:
            raise SystemExit("k2_time_probe: single-row 重建失败")
        rc, text, cmd = boot("single_row", firmware("time"))
    finally:
        for rel, blob in originals.items():
            (SOURCE / rel).write_bytes(blob)
            restored = md5(SOURCE / rel)
            print(f"  [{'PASS' if restored == before_md5[rel] else 'FAIL'}] "
                  f"single-row 还原 {rel} (cp) | md5 "
                  f"期望={before_md5[rel][:8]} 实际={restored[:8]}", flush=True)
            if restored != before_md5[rel]:
                raise SystemExit(f"k2_time_probe: single-row 还原后 md5 不一致 "
                                 f"({rel})")
    check_single_row(rep, rc, text, hart)
    return {"rc": rc, "text": text, "cmd": cmd}


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------

def run_gate(rep: Report, build_images: bool = True) -> dict:
    runs: dict[str, tuple[int, str, list[str]]] = {}
    snaps: dict[str, dict] = {}

    codes = kernel_selfcheck_codes()
    specs = k2trap.spec_exit_segments()
    fail_low, fail_high = specs["ranges"]["guest"]
    rep.check("C0", f"自检码全在 guest FAIL 段（{hex(fail_low)}-{hex(fail_high)}）",
              {}, {name: value for name, value in codes.items()
                   if not (fail_low <= value <= fail_high)})
    values = list(codes.values())
    rep.check("C0", "自检码互不重复（跨 head/setup/k1_pt/trap/time/irq）", True,
              len(values) == len(set(values)))
    rep.check("C0", "扫描面覆盖本任务进代码（time.c/irq.c）", True,
              any("kernel/time.c" in name for name in codes)
              and any("kernel/irq.c" in name for name in codes))
    rep.stat("自检码 " + " ".join(f"{name.split(':')[-1]}={hex(v)}"
                                 for name, v in sorted(codes.items())))

    rep.check("C0", "contract-see 的 cfx_time_freq 可解析", True,
              contract_freq() > 0)
    rep.check("C0", "TIMER cause id 与 cfx_hart 的 mask 位是两套编号", True,
              contract_timer_cause() != (1 << cfxha("cfx_hart")))
    rep.stat(f"freq={contract_freq()} timer_cause={contract_timer_cause():#x} "
             f"cfx_hart={cfxha('cfx_hart')} cfx_time={cfxha('cfx_time')} "
             f"declared_ticks={declared_ticks()} "
             f"config_hz={config_hz((Path(linux_paths.linux_build_dir()) / '.config').read_text(encoding='utf-8'))}")

    for name in IMAGES:
        if build_images:
            rc_build = config(name)
            if rc_build != 0:
                raise SystemExit(f"k2_time_probe: build {name} rc={rc_build}")
        snaps[name] = snapshot()
        runs[name] = boot(name, firmware("time"))

    base = check_image("time", *runs["time"], rep, snaps["time"])
    check_image("imask", *runs["imask"], rep, snaps["imask"])
    check_image("source", *runs["source"], rep, snaps["source"])
    check_image("global", *runs["global"], rep, snaps["global"])

    # C10 (ISS-455): reduce the kernel to the single mode-monitor row and show
    # the tick series still completes.  Runs last but one so the noperm rebuild
    # below returns the shared build tree to the pristine image.
    single_row = None
    if build_images:
        single_row = single_row_run(rep, cfxha("cfx_hart"))

    # The permission-negative run uses the *time* image against a firmware whose
    # hmon leaves cfx_hart / cfx_time closed.
    rom = firmware("noperm", ["--defsym", "K2_TIME_PERM=0"])
    if build_images:
        rc_build = config("time")       # pin the image this run interprets
        if rc_build != 0:
            raise SystemExit(f"k2_time_probe: rebuild time rc={rc_build}")
    snaps["noperm"] = snapshot()
    runs["noperm"] = boot("noperm", rom)
    check_permission(rep, *runs["noperm"][:2], specs, snaps["noperm"])

    rep.stat(f"runs={len(runs)} qemu={Path(k0.DEFAULT_QEMU).name} "
             f"md5={md5(Path(k0.DEFAULT_QEMU))[:8]}")
    return {"runs": runs, "snaps": snaps, "specs": specs, "codes": codes,
            "base": base, "single_row": single_row}


# ---------------------------------------------------------------------------
# --selfcheck: every group flips on a mutated capture
# ---------------------------------------------------------------------------

def run_selfcheck(result: dict) -> int:
    """Re-run the checks on mutated captures; each mutation must flip its group."""
    specs = result["specs"]
    runs = result["runs"]
    snaps = result["snaps"]
    problems: list[str] = []

    bit = 1 << cfxha("cfx_hart")

    def fails_of(name: str, mutate, cid: str) -> tuple[bool, str]:
        rc, text, cmd = runs[name]
        text = mutate(text)
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            if name == "noperm":
                check_permission(rep, rc, text, specs, snaps[name])
            else:
                check_image(name, rc, text, cmd, rep, snaps[name])
        red = [msg for msg in rep.fails if msg.startswith(cid)]
        return bool(red), (red[0] if red else "未变红")

    wrong_hz = config_hz(snaps["time"]["config"]) + 1

    mutations = [
        ("time", "C2", lambda t: re.sub(r"(K2 time_init: freq=\d+ hz=)\d+",
                                        rf"\g<1>{wrong_hz}", t),
         f"hz 写成配置之外的常数（{wrong_hz}）"),
        ("time", "C3", lambda t: re.sub(r"^K2 tick 3: time=\d+ jiffies=\d+\n",
                                        "", t, flags=re.MULTILINE),
         "少一个 tick 行"),
        ("time", "C4", lambda t: re.sub(r"^(K2 tick 2: time=)(\d+)",
                                        lambda m: m.group(1) + str(
                                            int(m.group(2)) + 3_000_000),
                                        t, flags=re.MULTILINE),
         "第二个 tick 的时间戳偏移 3 ms"),
        ("time", "C5", lambda t: re.sub(r"(after stop ticks=)\d+", r"\g<1>1", t),
         "stop 后仍有 tick"),
        ("imask", "C6", lambda t: re.sub(r"(K2 imask: ctrl=\S+ ticks=)\d+",
                                         r"\g<1>1", t), "IMASK 期间投递了 tick"),
        ("source", "C7", lambda t: re.sub(r"(K2 axistest: axis=source ticks=)\d+",
                                          r"\g<1>2", t), "关源轴仍有 tick"),
        ("global", "C7", lambda t: re.sub(
            r"(cfx_smon_global_cfx_intr_mask=)(\S+)",
            lambda m: m.group(1) + hex(int(m.group(2), 0) & ~(1 << cfxha("cfx_hart"))), t),
         "全局轴被放开（读回不再屏蔽）"),
        ("time", "C1", lambda t: re.sub(r"^K2 time: done ticks=\d+.*\n",
                                        "", t, flags=re.MULTILINE),
         "删掉退出标记行"),
        ("noperm", "C8", lambda t: t.replace("cause=CFXPERM(0x80)", "cause=CFXMEM(0x2)"),
         "负例具名行改成 CFXMEM"),
    ]
    for name, cid, mutate, why in mutations:
        red, detail = fails_of(name, mutate, cid)
        print(f"  [{'PASS' if red else 'FAIL'}] selfcheck {name}/{cid} | "
              f"注入「{why}」⇒ 期望={cid} 变红 实际={detail}", flush=True)
        if not red:
            problems.append(f"selfcheck {name}/{cid}: 未变红（{why}）")

    # The control: the untouched captures must be green.
    for name, (rc, text, cmd) in runs.items():
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            if name == "noperm":
                check_permission(rep, rc, text, specs, snaps[name])
            else:
                check_image(name, rc, text, cmd, rep, snaps[name])
        print(f"  [{'PASS' if not rep.fails else 'FAIL'}] selfcheck 对照 "
              f"{name} 未改动 | 期望=0 失败 实际={len(rep.fails)} 失败",
              flush=True)
        if rep.fails:
            problems.append(f"selfcheck 对照 {name}: {rep.fails[0]}")

    # C10's capture (ISS-455): truncated to the first delivery it must go red;
    # untouched it must stay green.
    single_row = result.get("single_row")
    if single_row:
        hart = cfxha("cfx_hart")
        one_tick = re.sub(r"^K2 tick (?:[2-9]|\d\d+):.*\n", "",
                          single_row["text"], flags=re.MULTILINE)
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            check_single_row(rep, single_row["rc"], one_tick, hart)
        red = [msg for msg in rep.fails if msg.startswith("C10")]
        print(f"  [{'PASS' if red else 'FAIL'}] selfcheck single_row/C10 | "
              f"注入「tick 停在首投那一次」⇒ 期望=C10 变红 实际="
              f"{red[0] if red else '未变红'}", flush=True)
        if not red:
            problems.append("selfcheck single_row/C10: 未变红")

        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            check_single_row(rep, single_row["rc"], single_row["text"], hart)
        print(f"  [{'PASS' if not rep.fails else 'FAIL'}] selfcheck 对照 "
              f"single_row 未改动 | 期望=0 失败 实际={len(rep.fails)} 失败",
              flush=True)
        if rep.fails:
            problems.append(f"selfcheck 对照 single_row: {rep.fails[0]}")

    total = len(mutations) + len(runs) + (2 if single_row else 0)
    if problems:
        print(f"k2_time_probe --selfcheck: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"k2_time_probe --selfcheck: PASS ({total}/{total} 组可翻转 + 对照)")
    return 0


# ---------------------------------------------------------------------------
# --inject: source injections, cp + md5 restore, green again
# ---------------------------------------------------------------------------

#: name -> (image, [(old, new), ...], expected rc, output regex, forbidden regex,
#:          check groups that must go red)
INJECTIONS: dict[str, tuple] = {
    # ① HZ written as a constant instead of the configured value: the reported
    #    hz no longer equals .config's CONFIG_HZ (the period is still right, so
    #    this isolates the "derived, not hardcoded" claim).
    "hz-hardcoded": (
        "time", [(("freq, (unsigned int)HZ, dadao_period,"),
                  ("freq, (unsigned int)HZ * 2, dadao_period,\t/* injected */"))],
        0, r"^K2 time: done ticks=", None, ("C2",), None,
    ),
    # ② The asynchronous vector written into cfx_smon's same-name register
    #    (and read back from there): cfx_hart keeps its reset vector 0, so the
    #    first delivered tick executes at address 0 instead of the kernel.
    "vector-to-smon": (
        "time",
        [(("\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_SUPV,\n"
           "\t\t\tCFX_HART_RC_SUPV_EXCP_VECTOR, vec);\n"),
          ("\tDADAO_CFX_WRITE(cfx_smon, CFX_HART_CG_SUPV,\n"
           "\t\t\tCFX_HART_RC_SUPV_EXCP_VECTOR, vec);\t/* injected */\n")),
         (("\tvread = DADAO_CFX_READ(cfx_hart, CFX_HART_CG_SUPV,\n"
           "\t\t\t       CFX_HART_RC_SUPV_EXCP_VECTOR);\n"),
          ("\tvread = DADAO_CFX_READ(cfx_smon, CFX_HART_CG_SUPV,\n"
           "\t\t\t       CFX_HART_RC_SUPV_EXCP_VECTOR);\t/* injected */\n"))],
        # cfx_hart keeps its reset vector, and writing cfx_smon's spv row also
        # overwrites the *synchronous* vector, so the first delivery loops in
        # CFXESC: the machine never returns and no tick is ever accounted.
        124, r"^K2 time: arm period=", r"^K2 (tick 1:|time: done)", ("C1", "C3"),
        30,
    ),
    # ⑥ The same vector in the same cfx but the wrong mode row (user instead of
    #    supv): cfx_hart's supv vector keeps its reset value 0, so the first
    #    delivered tick fetches at VA 0 — an unmapped address, i.e. a clean
    #    named CFXMEM termination instead of a tick.
    "vector-user-row": (
        "time",
        [(("\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_SUPV,\n"
           "\t\t\tCFX_HART_RC_SUPV_EXCP_VECTOR, vec);\n"),
          ("\tDADAO_CFX_WRITE(cfx_hart, 0 /* user row */,\n"
           "\t\t\tCFX_HART_RC_SUPV_EXCP_VECTOR, vec);\t/* injected */\n")),
         (("\tvread = DADAO_CFX_READ(cfx_hart, CFX_HART_CG_SUPV,\n"
           "\t\t\t       CFX_HART_RC_SUPV_EXCP_VECTOR);\n"),
          ("\tvread = DADAO_CFX_READ(cfx_hart, 0 /* user row */,\n"
           "\t\t\t       CFX_HART_RC_SUPV_EXCP_VECTOR);\t/* injected */\n"))],
        ("monitor", "supv", "CFXMEM"),
        r"^dadao: unrecoverable supv exception cause=CFXMEM", r"^K2 time: done",
        ("C1", "C3"), None,
    ),
    # ③ Neither mask axis opened: no tick can be delivered at all.
    "no-mask-open": (
        "time", [(("#if K2_AXIS_GLOBAL_OPEN\n"), ("#if 0\t/* injected */\n")),
                 (("#if K2_AXIS_SOURCE_OPEN\n"), ("#if 0\t/* injected */\n"))],
        None, r"^K2 fail: timer delivered no tick code=0x13$", r"^K2 time: done",
        ("C1", "C3"), None,
    ),
    # ④ The handler re-arms with twice the period: the tick count is still N
    #    but the intervals are no longer the configured period.
    "period-doubled": (
        "time", [(("\t\t\tnow + dadao_period);\n"),
                  ("\t\t\tnow + 2 * dadao_period);\t/* injected */\n"))],
        0, r"^K2 time: done ticks=", None, ("C4",), None,
    ),
    # ⑤ was "only cfx_smon's supv row opened (irq.c)": after m14-linux-008 the
    #    software IE knob writes *both* rows on every save/restore (ISS-454), so
    #    the handler itself re-opens cfx_hart's row on the first tick and the
    #    missing init_IRQ write no longer has an observable.  That property is
    #    judged by k2_irq_probe's `only-smon-row` injection instead; a mutation
    #    without a reachable FAIL path does not belong in this table.
}


def run_inject(name: str, problems: list[str], specs: dict) -> None:
    image, patches, want_rc, want_re, forbid, want_cids, timeout = \
        INJECTIONS[name]
    if isinstance(want_rc, tuple):
        _kind, mode, cause = want_rc
        want_rc = monitor_code(specs, mode, cause)
    # Each injection targets one file; its patches apply in order.
    rel = TIME_C if name in ("hz-hardcoded", "period-doubled") else IRQ_C
    path = SOURCE / rel
    before = md5(path)
    backup = SCRATCH / f"inject-{name}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(path.read_bytes())
    text = path.read_text()
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
    path.write_text(text)
    if md5(path) == before:
        problems.append(f"inject:{name}: 注入是空操作（md5 未变）")
        path.write_bytes(backup.read_bytes())
        backup.unlink()
        return
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> {md5(path)[:8]}",
          flush=True)
    try:
        rc_build = config(image)
        if rc_build != 0:
            problems.append(f"inject:{name}: 重建 rc={rc_build}")
        else:
            snap = snapshot()
            rc, text_out, _cmd = boot(f"inject_{name}", firmware("time"),
                                      timeout=timeout)
            print(f"---- guest output ({name}, rc={rc}) ----")
            print(text_out.strip()[-3000:])
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
            rep = Report(quiet=True)
            with contextlib.redirect_stdout(io.StringIO()):
                check_image(image, rc, text_out, _cmd, rep, snap)
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

    rc_build = config(image)
    if rc_build != 0:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    snap = snapshot()
    rc, text_out, _cmd = boot(f"inject_{name}_green", firmware("time"))
    rep = Report(quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        check_image(image, rc, text_out, _cmd, rep, snap)
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
                    help="mutate the captured runs: every check group must flip")
    ap.add_argument("--inject", action="store_true",
                    help="source injections: rebuild, assert FAIL, restore")
    ap.add_argument("--no-build", action="store_true",
                    help="assert only; reuse the images in the build tree")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", action="append", default=[],
                    help="run only the named injection (with --inject)")
    args = ap.parse_args()

    if args.list:
        for name in INJECTIONS:
            print(f"inject:{name}")
        for name in IMAGES:
            print(f"image:{name}")
        return 0

    if not k0.DEFAULT_QEMU or not Path(k0.DEFAULT_QEMU).is_file():
        print(f"k2_time_probe: FAIL: {k0.DEFAULT_QEMU} missing; "
              f"run `make install-host`", file=sys.stderr)
        return 1
    if not Path(linux_paths.linux_build_dir()).is_dir():
        print("k2_time_probe: FAIL: the kernel build tree is missing; "
              "run `make linux-defconfig`", file=sys.stderr)
        return 2
    SCRATCH.mkdir(parents=True, exist_ok=True)

    if args.inject:
        problems: list[str] = []
        names = args.only or list(INJECTIONS)
        for name in names:
            run_inject(name, problems, k2trap.spec_exit_segments())
        total = len(names)
        if problems:
            print(f"k2_time_probe --inject: FAIL ({len(problems)} 问题)")
            for problem in problems:
                print("  - " + problem)
            return 1
        print(f"k2_time_probe --inject: PASS ({total}/{total} 路注入按预期变红并还原)")
        return 0

    specs = k2trap.spec_exit_segments()
    print(f"k2t: qemu={k0.DEFAULT_QEMU} md5={md5(Path(k0.DEFAULT_QEMU))[:8]}")
    print(f"k2t: [STAT] §7.1 supv+CFXPERM monitor code = "
          f"{hex(monitor_code(specs, 'supv', 'CFXPERM'))}")

    rep = Report()
    result = run_gate(rep, build_images=not args.no_build)
    if not result["runs"]:
        print("k2_time_probe: FAIL: no image could be built", file=sys.stderr)
        return 2

    if args.selfcheck:
        return run_selfcheck(result)

    if not rep.fails:
        print(f"k2_time_probe: PASS ({rep.total}/{rep.total})")
    else:
        print(f"k2_time_probe: FAIL ({len(rep.fails)}/{rep.total})")
        for failure in rep.fails:
            print("  - " + failure)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
