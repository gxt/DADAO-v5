#!/usr/bin/env python3
"""k5_clocksource_probe.py — M14 K5 clock subsystem gate (`m14-linux-026`).

`time_init()` now hands the two frozen registers (contract-see §3) to the
generic Linux time subsystem: `dadao_clocksource` over `cfx_time` (1 GHz,
1 count = 1 ns, 64-bit, free running) and `dadao_clock_event_device` over
`cfx_hart`'s absolute compare register.  This gate boots the real kernel with
the probe image (`CONFIG_DADAO_K5_CLOCK_SELFTEST`) and judges what the
*registered objects* report:

    T1  the clocksource is monotone, moves, and is the same counter as
        `sched_clock()` (constant offset within the derived tolerance);
    T2  `set_next_event()` writes the absolute `timer_cmp`; programming an
        8-period deadline and then a 1-period one cancels the first, and the
        delivery lands inside `[period/2, 2*period]`;
    T3  a delivered tick advances `jiffies_64` (`do_timer(1)` inside
        `tick_handle_periodic()`) one for one, and `sched_tick()` ran (the
        CFS `sum_exec_runtime` moved);
    T4  the clocksource is stable over a window and `ktime_get()` advances at
        sub-period resolution, i.e. timekeeping left the 10 ms jiffies
        fallback and follows `cfx_time`.

Everything expected are derived live, never restated:

  * `freq` -> `.tao/contracts/contract-see.md` §3 (`cg10 rc0 = ... = <value>`);
  * `HZ` -> the image's `.config` (`CONFIG_HZ`), `period` -> `freq // HZ`;
  * the jiffies fallback's rating -> `kernel/time/jiffies.c` (the clocksource
    the kernel uses before `time_init()` registers ours);
  * `CLOCK_EVT_FEAT_ONESHOT` -> `include/linux/clockchips.h`;
  * the consecutive-tick target -> `arch/dadao/include/asm/time.h`
    (`DADAO_K5_CLOCK_TICKS`);
  * the interval margin -> half a period, reported as `[STAT]` with the live
    values.

`--selfcheck` mutates the captured run and shows every group flips.
`--inject` corrupts the kernel source (frozen clocksource / wrong register in
`set_next_event` / `event_handler` not called), rebuilds, asserts the named
group goes red, restores with ``cp`` + md5 (never ``git checkout``), rebuilds
and proves the image is green again.

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

from tools.linux import config_pins                  # noqa: E402  (pins)
from tools.linux import k1_boot_probe as k1boot      # noqa: E402  (symbols)
from tools.linux import make_defconfig as defconfig  # noqa: E402  (config slice)
from tools.linux import paths as linux_paths         # noqa: E402
from tools.qemu import k0_boot_probe as k0           # noqa: E402  (firmware, qemu)

PROFILE = "vast"

TIMEOUT_QEMU = int(os.environ.get("K5C_QEMU_TIMEOUT", "240"))
TIMEOUT_BUILD = int(os.environ.get("K5C_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K5C_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-026") / "k5_clocksource_probe")

CONTRACT_SEE = _REPO / ".tao" / "contracts" / "contract-see.md"
SOURCE = linux_paths.linux_source_dir()

#: Kernel source the injections mutate (single file each).
TIME_C = "arch/dadao/kernel/time.c"

#: Every milestone symbol pinned, only this probe compiled in
#: (`make check-config-pins`; an int pinned "n" is "left unset").
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
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "y",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)


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
        raise SystemExit("k5_clocksource_probe: contract-see §3 freq not found")
    return int(m.group(1).replace("_", ""))


def config_hz(cfg: str) -> int:
    m = re.search(r"^CONFIG_HZ=(\d+)$", cfg, re.MULTILINE)
    if not m:
        raise SystemExit("k5_clocksource_probe: CONFIG_HZ not in .config")
    return int(m.group(1))


def jiffies_rating() -> int:
    """The fallback clocksource's rating (`kernel/time/jiffies.c`)."""
    path = SOURCE / "kernel" / "time" / "jiffies.c"
    m = re.search(r"rating\s*=\s*(\d+)", path.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"k5_clocksource_probe: no rating in {path}")
    return int(m.group(1))


def oneshot_feature() -> int:
    """`CLOCK_EVT_FEAT_ONESHOT` from include/linux/clockchips.h."""
    path = SOURCE / "include" / "linux" / "clockchips.h"
    m = re.search(r"#\s*define\s+CLOCK_EVT_FEAT_ONESHOT\s+0x([0-9a-fA-F]+)",
                  path.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("k5_clocksource_probe: CLOCK_EVT_FEAT_ONESHOT missing")
    return int(m.group(1), 16)


def declared_ticks() -> int:
    """`DADAO_K5_CLOCK_TICKS` as the kernel source declares it."""
    path = SOURCE / "arch" / "dadao" / "include" / "asm" / "time.h"
    m = re.search(r"^#define\s+DADAO_K5_CLOCK_TICKS\s+(\d+)\s*$",
                  path.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        raise SystemExit(f"k5_clocksource_probe: no DADAO_K5_CLOCK_TICKS in {path}")
    return int(m.group(1))


def kernel_path() -> Path:
    return Path(linux_paths.linux_build_dir()) / "vmlinux"


def snapshot() -> dict:
    """What belongs to *this* image: its .config and its symbol table."""
    return {"config": (Path(linux_paths.linux_build_dir()) / ".config").read_text(
                encoding="utf-8"),
            "syms": k1boot.symbols(kernel_path())}


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def config() -> int:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k5_clocksource_probe: FAIL: config slice rc={rc}",
              file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build clock image (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-3000:], file=sys.stderr)
        print((proc.stderr or "")[-3000:], file=sys.stderr)
    return proc.returncode


_ROMS: dict[str, str] = {}


def firmware(tag: str = "clock") -> str:
    if tag in _ROMS:
        return _ROMS[tag]
    k0.load_contract()
    if not k0.ABI:
        raise SystemExit("k5_clocksource_probe: the boot contract is empty")
    out = SCRATCH / f"bootrom_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    _ROMS[tag] = k0.build_firmware(str(out), name=f"bootrom_k0_{tag}.bin")
    return _ROMS[tag]


def boot(tag: str, rom: str,
         timeout: int | None = None) -> tuple[int, str, list[str]]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k5_clocksource_probe: {kernel} missing")
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
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = err or out
    log.write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# parsing the kernel's own report
# ---------------------------------------------------------------------------

BEGIN = re.compile(
    r"^K5 clock: begin cs=(\S+) rating=(\d+) mask=(\S+) ce=(\S+) rating=(\d+) "
    r"features=(\S+) handler=(\d+) freq=(\d+) hz=(\d+) period=(\d+)$",
    re.MULTILINE)
CS = re.compile(r"^K5 time: cs=(\S+) rating=(\d+) mask=(\S+) freq=(\d+) "
                r"hz=(\d+) period=(\d+)$", re.MULTILINE)
CE = re.compile(r"^K5 time: ce=(\S+) rating=(\d+) features=(\S+) "
                r"handler=(\d+) min_delta=(\d+)$", re.MULTILINE)
T1 = re.compile(r"^K5 clock: t1 i=(\d+) sched=(\d+) raw=(\d+)$", re.MULTILINE)
T2 = re.compile(r"^K5 clock: t2 period=(\d+) arm_long=(\d+) cmp_long=(\d+) "
                r"arm_short=(\d+) cmp_short=(\d+) event=(\d+) interval=(\d+)$",
                re.MULTILINE)
T3 = re.compile(r"^K5 clock: t3 want=(\d+) j0=(\d+) j1=(\d+) ticks=(\d+) "
                r"se0=(\d+) se1=(\d+) ut0=(\d+) ut1=(\d+) window=(\d+)$",
                re.MULTILINE)
T4S = re.compile(r"^K5 clock: t4 s=(\d+) value=(\d+)$", re.MULTILINE)
T4 = re.compile(r"^K5 clock: t4 cs0=(\d+) cs1=(\d+) k0=(\d+) k1=(\d+) "
                r"window=(\d+)$", re.MULTILINE)
DONE = re.compile(r"^K5 clock: done$", re.MULTILINE)


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check_config(rep: Report, cfg: str) -> None:
    line = "CONFIG_DADAO_K5_CLOCK_SELFTEST=y"
    rep.check("C1", f"镜像配置：{line}", line,
              next((ln for ln in cfg.splitlines() if ln.startswith(
                  "CONFIG_DADAO_K5_CLOCK_SELFTEST=")), "<unset>"))
    # The generic framework must be the one running in this image: the K2
    # boundary image compiles the raw tick path instead.
    rep.check("C1", "镜像配置：K2 时间边界未设（走 start_kernel 的 time_init）",
              [], [ln for ln in cfg.splitlines()
                   if ln.startswith("CONFIG_DADAO_K2_TIME_STOP=")])
    for symbol in ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP"):
        rep.check("C1", f"镜像配置：{symbol} 未设", [],
                  [ln for ln in cfg.splitlines()
                   if ln.startswith(symbol + "=")])


def check_registration(rep: Report, text: str, cfg_hz: int, freq: int) -> dict:
    """C1: the two devices were registered in time_init() with live values."""
    period = freq // cfg_hz
    m = CS.search(text)
    if not m:
        rep.check("C1", "time_init 注册 clocksource 行存在", "存在", "缺失")
        return {"period": period}
    name, rating, mask, printed_freq, printed_hz, printed_period = m.groups()
    rating, printed_freq, printed_hz, printed_period = (
        int(rating), int(printed_freq), int(printed_hz), int(printed_period))
    rep.check("C1", "clocksource freq == 契约 cfx_time_freq", freq, printed_freq)
    rep.check("C1", "clocksource hz == .config CONFIG_HZ（不写死）", cfg_hz,
              printed_hz)
    rep.check("C1", "clocksource period == freq / hz（现场派生）", period,
              printed_period)
    rep.check("C1", "clocksource mask == 64 位全 1", (1 << 64) - 1,
              int(mask, 0))
    rep.check("C1", "clocksource rating > jiffies 后备源 rating", True,
              rating > jiffies_rating())
    rep.check("C1", "clocksource 名字非空", True, bool(name))

    m = CE.search(text)
    if not m:
        rep.check("C1", "time_init 注册 clockevent 行存在", "存在", "缺失")
        return {"period": period}
    ce_name, ce_rating, ce_features, handler, min_delta = m.groups()
    ce_features = int(ce_features, 0)
    rep.check("C1", "clockevent handler 已由 tick 框架安装", 1, int(handler))
    rep.check("C1", "clockevent 声明 ONESHOT 能力（无硬件重装）", True,
              bool(ce_features & oneshot_feature()))
    rep.check("C1", "clockevent min_delta > 0 且 < period", True,
              0 < int(min_delta) < period)
    rep.check("C1", "clockevent 名字非空", True, bool(ce_name))

    # The registration must happen inside time_init(), after the K2 time-base
    # line and before the probe body.
    lines = text.splitlines()
    def index(prefix: str) -> int:
        return next((i for i, ln in enumerate(lines) if ln.startswith(prefix)),
                    -1)
    base = index("K2 time_init:")
    cs_line = index("K5 time: cs=")
    ce_line = index("K5 time: ce=")
    begin = index("K5 clock: begin")
    rep.check("C1", "注册在 time_init：K2 time_init 行先于 cs 行", True,
              0 <= base < cs_line)
    rep.check("C1", "注册顺序：clocksource 先于 clockevent", True,
              0 <= cs_line < ce_line)
    rep.check("C1", "注册先于探针体（begin 行最后）", True,
              0 <= ce_line < begin)
    rep.check("C1", "begin 行读回的 freq/hz/period 与注册行一致", True,
              bool(re.search(
                  rf"^K5 clock: begin cs={re.escape(name)} rating={rating} "
                  rf"mask={re.escape(mask)} ce={re.escape(ce_name)} .* "
                  rf"freq={printed_freq} hz={printed_hz} "
                  rf"period={printed_period}$", text, re.MULTILINE)))
    return {"period": period, "freq": freq, "hz": cfg_hz,
            "cs_rating": rating, "ce_features": ce_features}


def check_t1(rep: Report, text: str, base: dict) -> None:
    period = base.get("period") or 1
    rows = [(int(i), int(s), int(r)) for i, s, r in T1.findall(text)]
    rep.check("T1", "t1 采样行数 == 3", 3, len(rows))
    if len(rows) != 3:
        return
    idx = [i for i, _s, _r in rows]
    sched = [s for _i, s, _r in rows]
    raw = [r for _i, _s, r in rows]
    rep.check("T1", "采样序号 == 0..2", [0, 1, 2], idx)
    rep.check("T1", "clocksource 读值非降", True,
              all(a <= b for a, b in zip(raw, raw[1:])))
    rep.check("T1", "clocksource 在读期间真的前进（非常量源）", True,
              raw[-1] > raw[0])
    rep.check("T1", "sched_clock 读值非降", True,
              all(a <= b for a, b in zip(sched, sched[1:])))
    rep.check("T1", "sched_clock 与 clocksource 同源：偏移恒定", True,
              max(raw) - min(raw) > 0
              and (max((r - s) for r, s in zip(raw, sched))
                   - min((r - s) for r, s in zip(raw, sched)))
              <= period // 8)
    # Same-source also means the two counters step together: a sched_clock on
    # the 10 ms jiffies fallback would differ by a jiffy between samples.
    drift = [abs((raw[i + 1] - raw[i]) - (sched[i + 1] - sched[i]))
             for i in range(2)]
    rep.check("T1", "相邻采样的 sched/raw 步进一致（差值 <= period/8）", True,
              all(d <= period // 8 for d in drift))
    rep.stat(f"t1 raw={raw} sched={sched} offsets="
             f"{[r - s for r, s in zip(raw, sched)]} drift={drift} "
             f"margin={period // 8}")


def check_t2(rep: Report, text: str, base: dict) -> None:
    period = base.get("period") or 1
    m = T2.search(text)
    if not m:
        rep.check("T2", "t2 next-event 行存在", "存在", "缺失")
        return
    (printed_period, arm_long, cmp_long, arm_short, cmp_short, event,
     interval) = (int(g) for g in m.groups())
    rep.check("T2", "printed period == freq / HZ", period, printed_period)
    rep.check("T2", "长 deadline：cmp 读回 == arm + 8*period（±period/2）", True,
              8 * period <= cmp_long - arm_long <= 8 * period + period // 2)
    rep.check("T2", "短 deadline：cmp 读回 == arm + period（±period/2）", True,
              period <= cmp_short - arm_short <= period + period // 2)
    rep.check("T2", "第二次写 cmp 覆盖了第一次（不是两个 deadline 共存）", True,
              cmp_long - cmp_short >= 6 * period)
    rep.check("T2", "事件真的投递了", True, event != 0)
    rep.check("T2", "投递间隔 ∈ [period/2, 2*period]", True,
              period // 2 <= interval <= 2 * period)
    rep.check("T2", "投递没有等到旧的 8 期 deadline", True,
              0 < event - arm_short < 4 * period)
    rep.stat(f"t2 period={period} cmp_long-arm={cmp_long - arm_long} "
             f"cmp_short-arm={cmp_short - arm_short} interval={interval} "
             f"margin=[{period // 2},{2 * period}]")


def check_t3(rep: Report, text: str, base: dict) -> None:
    period = base.get("period") or 1
    m = T3.search(text)
    if not m:
        rep.check("T3", "t3 tick 行存在", "存在", "缺失")
        return
    (want, j0, j1, ticks, se0, se1, ut0, ut1, window) = (int(g)
                                                         for g in m.groups())
    rep.check("T3", "tick 目标 == 内核源码声明（DADAO_K5_CLOCK_TICKS）",
              declared_ticks(), want)
    rep.check("T3", "连续投递数 >= 目标", True, ticks >= want)
    rep.check("T3", "jiffies_64 每投递前进 1（do_timer(1) 真的跑）",
              ticks, j1 - j0)
    rep.check("T3", "sched_tick 跑过（CFS sum_exec_runtime 前进）", True,
              se1 > se0)
    rep.check("T3", "等待窗 >= 目标 + 2 个 period（现场派生）", True,
              window >= (want + 2) * period)
    rep.stat(f"t3 want={want} ticks={ticks} jdelta={j1 - j0} "
             f"se_delta={se1 - se0} ut_delta={ut1 - ut0} window={window}")


def check_t4(rep: Report, text: str, base: dict) -> None:
    period = base.get("period") or 1
    samples = [(int(i), int(v)) for i, v in T4S.findall(text)]
    rep.check("T4", "稳定性采样行数 == 8", 8, len(samples))
    if len(samples) != 8:
        return
    idx = [i for i, _v in samples]
    vals = [v for _i, v in samples]
    rep.check("T4", "采样序号 == 0..7", list(range(8)), idx)
    rep.check("T4", "两次读之间不回退（单调非降）", True,
              all(a <= b for a, b in zip(vals, vals[1:])))
    rep.check("T4", "读值在窗口内前进（不是「返回上次值」）", True,
              vals[-1] > vals[0])

    m = T4.search(text)
    if not m:
        rep.check("T4", "t4 汇总行存在", "存在", "缺失")
        return
    cs0, cs1, k0, k1, window = (int(g) for g in m.groups())
    rep.check("T4", "窗口 == period/4（现场派生）", period // 4, window)
    rep.check("T4", "ktime_get 前进（时间不被冻结）", True, k1 > k0)
    rep.check("T4", "ktime 分辨率优于半个 period（已离开 10 ms jiffies 源）",
              True, k1 - k0 < period // 2)
    rep.check("T4", "ktime 步进与 clocksource 一致（±period/4）", True,
              cs1 > cs0 and abs((k1 - k0) - (cs1 - cs0)) <= period // 4)
    rep.stat(f"t4 cs_delta={cs1 - cs0} ktime_delta={k1 - k0} "
             f"window={window} samples={vals}")


def check_image(rc: int, text: str, cmd: list[str], rep: Report,
                snap: dict) -> dict:
    check_config(rep, snap["config"])
    rep.check("C1", "guest rc（SYS_EXIT 子码）", 0, rc)
    rep.check("C1", "命令行无 -d（不用逐指令日志）", True,
              "-d" not in cmd and "-D" not in cmd)
    rep.check("C1", "探针 begin 行存在", 1, len(BEGIN.findall(text)))
    rep.check("C1", "探针 done 行存在", 1, len(DONE.findall(text)))
    non_empty = [ln for ln in text.splitlines() if ln.strip()]
    rep.check("C1", "退出标记是最后一行", True,
              bool(non_empty) and non_empty[-1] == "K5 clock: done")
    # Two warnings are pre-existing properties of this port, measured on every
    # full-boot image since K4/K5 (not this task): `init/main.c:1110` fires
    # because `init_IRQ()` opens the source mask, `fs/sysfs/group.c:137` during
    # `kernel_init`'s initcalls.  They are filtered by name, so any *new*
    # warning, oops or panic still goes red.
    known = (r"^WARNING: init/main\.c:1110",
             r"^WARNING: fs/sysfs/group\.c:137")
    rep.check("C1", "输出无 panic/oops/BUG 与新增 WARNING 痕迹", [],
              [ln for ln in non_empty
               if re.search(r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|"
                            r"^WARNING:|Call Trace)", ln)
               and not any(re.search(k, ln) for k in known)])
    rep.check("C1", "输出无具名异常终止", [],
              [ln for ln in non_empty if ln.startswith("dadao: ")])

    base = check_registration(rep, text, config_hz(snap["config"]),
                              contract_freq())
    check_t1(rep, text, base)
    check_t3(rep, text, base)
    check_t2(rep, text, base)
    check_t4(rep, text, base)
    return base


def run_gate(rep: Report, build: bool = True) -> dict:
    cfg_hz = 0
    if build:
        rc_build = config()
        if rc_build != 0:
            raise SystemExit(f"k5_clocksource_probe: build rc={rc_build}")
    snap = snapshot()
    cfg_hz = config_hz(snap["config"])
    freq = contract_freq()
    period = freq // cfg_hz
    rep.stat(f"freq={freq} hz={cfg_hz} period={period} "
             f"jiffies_rating={jiffies_rating()} "
             f"oneshot={oneshot_feature():#x} "
             f"ticks={declared_ticks()}")
    rc, text, cmd = boot("clock", firmware())
    check_image(rc, text, cmd, rep, snap)
    rep.stat(f"qemu={Path(k0.DEFAULT_QEMU).name} "
             f"md5={md5(Path(k0.DEFAULT_QEMU))[:8]}")
    return {"rc": rc, "text": text, "cmd": cmd, "snap": snap}


# ---------------------------------------------------------------------------
# --selfcheck: every group flips on a mutated capture
# ---------------------------------------------------------------------------

def judge(rc: int, text: str, cmd: list[str], snap: dict) -> Report:
    rep = Report(quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        check_image(rc, text, cmd, rep, snap)
    return rep


def run_selfcheck(result: dict) -> int:
    snap = result["snap"]
    text = result["text"]
    period = image_period(snap)
    problems: list[str] = []

    def flip(cid: str, mutate, why: str) -> None:
        mutated = mutate(text)
        red = [msg for msg in judge(result["rc"], mutated, result["cmd"],
                                    snap).fails if msg.startswith(cid)]
        print(f"  [{'PASS' if red else 'FAIL'}] selfcheck {cid} | "
              f"注入「{why}」⇒ 期望={cid} 变红 实际={red[0] if red else '未变红'}",
              flush=True)
        if not red:
            problems.append(f"selfcheck {cid}: 未变红（{why}）")

    def raw_constant(t: str) -> str:
        m = T1.search(t)
        value = m.group(3) if m else "0"
        return re.sub(r"(^K5 clock: t1 i=\d+ sched=\d+ raw=)\d+",
                      rf"\g<1>{value}", t, flags=re.MULTILINE)

    mutations = [
        ("C1", lambda t: re.sub(r"^K5 clock: begin .*\n", "", t,
                                flags=re.MULTILINE), "删掉 begin 行"),
        ("T1", raw_constant, "clocksource 读值恒常量"),
        ("T2", lambda t: re.sub(r"(^K5 clock: t2 .* interval=)\d+",
                                rf"\g<1>{3 * period}", t, flags=re.MULTILINE),
         "投递间隔改成 3 个 period"),
        ("T3", lambda t: re.sub(r"(^K5 clock: t3 want=\d+ j0=)(\d+)( j1=)\d+",
                                r"\g<1>\g<2>\g<3>\g<2>", t,
                                flags=re.MULTILINE), "jiffies 不前进"),
        ("T4", lambda t: re.sub(r"(^K5 clock: t4 cs0=\d+ cs1=\d+ k0=\d+ k1=)(\d+)",
                                lambda m: m.group(1) + str(
                                    int(m.group(2)) + period), t,
                                flags=re.MULTILINE),
         "ktime 步进一个整 period（退回 jiffies 源）"),
    ]
    for cid, mutate, why in mutations:
        flip(cid, mutate, why)

    rep = judge(result["rc"], text, result["cmd"], snap)
    print(f"  [{'PASS' if not rep.fails else 'FAIL'}] selfcheck 对照 未改动 | "
          f"期望=0 失败 实际={len(rep.fails)} 失败", flush=True)
    if rep.fails:
        problems.append(f"selfcheck 对照: {rep.fails[0]}")

    total = len(mutations) + 1
    if problems:
        print(f"k5_clocksource_probe --selfcheck: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"k5_clocksource_probe --selfcheck: PASS ({total}/{total} 组可翻转 + 对照)")
    return 0


def image_period(snap: dict) -> int:
    """`freq / HZ` for the image under test (the tick's claim, derived)."""
    return contract_freq() // config_hz(snap["config"])


# ---------------------------------------------------------------------------
# --inject: source injections, cp + md5 restore, green again
# ---------------------------------------------------------------------------

READ_BODY = (
    "static u64 notrace dadao_clocksource_read(struct clocksource *cs)\n"
    "{\n"
    "\treturn dadao_read_time();\n"
    "}\n")

NEXT_EVENT_BODY = (
    "\tunsigned long deadline = dadao_read_time() + delta;\n"
    "\n"
    "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_TIMER, CFX_HART_RC_TIMER_CMP,\n"
    "\t\t\tdeadline);\n")

HANDLER_CALL = (
    "\tif (WARN_ON_ONCE(!dev->event_handler)) {\n"
    "\t\tarch_local_irq_restore(flags);\n"
    "\t\treturn;\n"
    "\t}\n"
    "\tdadao_ticks++;\n"
    "\tdev->event_handler(dev);\n"
    "\tarch_local_irq_restore(flags);\n")

#: name -> ([(old, new), ...], expected exit rc, output regex, red group)
INJECTIONS: dict[str, tuple] = {
    # ① The registered clocksource no longer reads cfx_time: every read
    #    returns the value cached on the first call.  T1 must see a source
    #    that does not move (and T4's ktime window freezes too).
    "read-frozen": (
        [(READ_BODY,
          "static u64 notrace dadao_clocksource_read(struct clocksource *cs)\n"
          "{\n"
          "\tstatic u64 frozen;\t/* injected: constant read */\n"
          "\n"
          "\tif (!frozen)\n"
          "\t\tfrozen = dadao_read_time();\n"
          "\treturn frozen;\n"
          "}\n")],
        ("T1", "T4"), None),
    # ② `set_next_event` writes the deadline into timer_ctrl instead of
    #    timer_cmp: the compare value is never replaced, so no event lands
    #    where the second write asked for it.  T2 must go red.
    "next-event-wrong-reg": (
        [(NEXT_EVENT_BODY,
          "\tunsigned long deadline = dadao_read_time() + delta;\n"
          "\n"
          "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_TIMER, "
          "CFX_HART_RC_TIMER_CTRL,\n"
          "\t\t\tdeadline);\t/* injected: wrong register */\n")],
        ("T2",), r"^K5 clock: done"),
    # ③ The delivery is re-armed by hand instead of reaching the registered
    #    event handler: the hardware keeps ticking, but `do_timer(1)` and
    #    `sched_tick()` never run.  T3 must go red.
    "handler-no-tick": (
        [(HANDLER_CALL,
          "\tif (WARN_ON_ONCE(!dev->event_handler)) {\n"
          "\t\tarch_local_irq_restore(flags);\n"
          "\t\treturn;\n"
          "\t}\n"
          "\tdadao_ticks++;\n"
          "\t/* injected: no generic tick, re-arm by hand */\n"
          "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_TIMER, "
          "CFX_HART_RC_TIMER_CMP,\n"
          "\t\t\tdadao_read_time() + dadao_period);\n"
          "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_TIMER, "
          "CFX_HART_RC_TIMER_CTRL,\n"
          "\t\t\tDADAO_TIMER_ENABLE);\n"
          "\tarch_local_irq_restore(flags);\n")],
        ("T3",), r"^K5 clock: done"),
}


def run_inject(name: str, problems: list[str]) -> None:
    patches, want_cids, want_re = INJECTIONS[name]
    path = SOURCE / TIME_C
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
        rc_build = config()
        if rc_build != 0:
            problems.append(f"inject:{name}: 重建 rc={rc_build}")
        else:
            snap = snapshot()
            rc, out, cmd = boot(f"inject_{name}", firmware())
            print(f"---- guest output ({name}, rc={rc}) ----")
            print(out.strip()[-3000:])
            print("----------------------------------------")
            rep = judge(rc, out, cmd, snap)
            checks = []
            for cid in want_cids:
                red = [msg for msg in rep.fails if msg.startswith(cid)]
                checks.append((f"断言 {cid} 变红", bool(red), f"{cid} 出现 FAIL",
                               red[0] if red else "未变红"))
            if want_re is not None:
                hit = bool(re.search(want_re, out, re.MULTILINE))
                checks.append(("后续探针行仍打印（boot 未死）", hit, want_re,
                               "命中" if hit else "<none>"))
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

    rc_build = config()
    if rc_build != 0:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    snap = snapshot()
    rc, out, cmd = boot(f"inject_{name}_green", firmware())
    rep = judge(rc, out, cmd, snap)
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
    ap.add_argument("--no-build", action="store_true",
                    help="assert only; reuse the image in the build tree")
    ap.add_argument("--only", action="append", default=[],
                    help="run only the named injection (with --inject)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for name in INJECTIONS:
            print(f"inject:{name}")
        print("image:clock")
        return 0

    if not k0.DEFAULT_QEMU or not Path(k0.DEFAULT_QEMU).is_file():
        print(f"k5_clocksource_probe: FAIL: {k0.DEFAULT_QEMU} missing; "
              f"run `make install-host`", file=sys.stderr)
        return 1
    if not Path(linux_paths.linux_build_dir()).is_dir():
        print("k5_clocksource_probe: FAIL: the kernel build tree is missing; "
              "run `make linux-defconfig`", file=sys.stderr)
        return 2
    SCRATCH.mkdir(parents=True, exist_ok=True)

    if args.inject:
        problems: list[str] = []
        names = args.only or list(INJECTIONS)
        for name in names:
            run_inject(name, problems)
        total = len(names)
        if problems:
            print(f"k5_clocksource_probe --inject: FAIL ({len(problems)} 问题)")
            for problem in problems:
                print("  - " + problem)
            return 1
        print(f"k5_clocksource_probe --inject: PASS ({total}/{total} 路注入按预期变红并还原)")
        return 0

    rep = Report()
    result = run_gate(rep, build=not args.no_build)

    if args.selfcheck:
        return run_selfcheck(result)

    if not rep.fails:
        print(f"k5_clocksource_probe: PASS ({rep.total}/{rep.total})")
        return 0
    print(f"k5_clocksource_probe: FAIL ({len(rep.fails)}/{rep.total})")
    for failure in rep.fails:
        print("  - " + failure)
    return 1


if __name__ == "__main__":
    sys.exit(main())
