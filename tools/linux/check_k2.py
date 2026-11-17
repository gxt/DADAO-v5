#!/usr/bin/env python3
"""check_k2.py — M14 K2 closure gate (`make check-linux-k2`; `m14-linux-009`).

K2 delivered three things on Kaiwu-Vast: the supv synchronous-exception channel,
a clock/timer (cfx_time + the cfx_hart TIMER), and the software interrupt-enable
knob.  K0 asks "can the boot chain hand over at all", K1 "does the kernel run and
stop before any clock"; K2's exit criteria (2026-11-16 user ruling: six narrowed
to four) are:

  1. E  synchronous exception channel: a *pre-declared* CFXMEM is classified
        (name + ip + info) and resumed; an *undeclared* one of the same class
        stops with a named cause and does not re-enter.
  2. T  clock: ``cfx_time`` frequency == the contract value, ``time`` monotone,
        the tick interval == freq/HZ with ``HZ`` parsed live out of the image's
        ``.config``, and the margin has an upper bound.
  3. M  masking: the tick count is frozen inside a masked window and the release
        delivers exactly +1 (merged, neither lost nor doubled).
  4. R  no regression: ``check-linux-k0`` and ``check-linux-k1`` still pass.

Two assertions from the original criteria stay in the gate without being part of
the four (they were folded, not dropped): **S** end-to-end stage order and **X**
the A′ exit-code segmentation.  **B** asserts that the image under test is the
K2 image the gate asked for (``defconfig`` as-is) and that its plain boot is
clean.

Expectations are derived live — this file restates none of them:

  * cause table / bit indices / exit-code segments -> ``spec/DADAO-13 §2`` and
    ``spec/Kaiwu §7.1`` (through the K2 exception gate's parsers);
  * ``cfx_time_freq`` -> ``.tao/contracts/contract-see.md §3``;
  * ``HZ`` -> the ``.config`` captured with the image under test;
  * ``period`` -> freq / HZ; ``margin`` -> period / 2 (``spec/DADAO-12 §5``:
    delivery is checked at instruction boundaries);
  * the declared tick count -> ``arch/dadao/include/asm/time.h``;
  * ``probe_va`` -> boot info ``ram_base``/``ram_size`` + the contract superpage
    size (the first superpage past RAM, ``mm/k1_pt.c §2.2.1``);
  * the kernel text window -> the image's own program headers (``llvm-nm``);
  * the firmware stage order -> the image ``build_firmware`` just produced and
    the machine profile;
  * the self-check code space -> every ``*FAIL*`` constant the kernel sources
    define (the same scan the K2 time gate uses).

Images (each one configured explicitly; the build tree is shared, so no image may
inherit whichever gate configured it last):

  k2    ``defconfig`` as-is: K2 time boundary on, no self-tests  -> SYS_EXIT(0)
  trap  ``CONFIG_DADAO_K2_TRAP_SELFTEST=y``: P1 (registered CFXMEM, resumed) and
        P3 (unregistered CFXMEM, named termination)              -> rc = supv+CFXMEM
  irq   ``CONFIG_DADAO_K2_IRQ_TEST=y``: the masked window (P2) and the escaped
        frame (P4), plus the whole boot chain                     -> SYS_EXIT(0)

The gate runs the K0/K1 closure gates as subprocesses for R (their own counts are
parsed out of their output, never restated here).

``--selfcheck`` mutates the captured runs / the captured ``.config`` and shows
that *every* group flips.  ``--inject`` corrupts the kernel source, rebuilds,
asserts the named groups go red, restores with ``cp`` + md5 and proves the image
is green again — one path per capability.

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

from tools.linux import check_k1 as k1gate          # noqa: E402  (BootROM image)
from tools.linux import k1_boot_probe as k1boot     # noqa: E402  (symbols/ELF)
from tools.linux import k2_irq_probe as k2irq       # noqa: E402  (P2/P4 lines)
from tools.linux import k2_time_probe as k2time     # noqa: E402  (derivations)
from tools.linux import k2_trap_probe as k2trap     # noqa: E402  (§7.1 parsers)
from tools.linux import make_defconfig as defconfig  # noqa: E402  (config slice)
from tools.linux import paths as linux_paths        # noqa: E402
from tools.qemu import k0_boot_probe as k0          # noqa: E402  (contract, ROM)

PROFILE = k1gate.PROFILE

TIMEOUT_QEMU = int(os.environ.get("K2G_QEMU_TIMEOUT", "180"))
TIMEOUT_BUILD = int(os.environ.get("K2G_BUILD_TIMEOUT", "3600"))
TIMEOUT_REGRESS = int(os.environ.get("K2G_REGRESS_TIMEOUT", "2400"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K2G_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-009") / "check-linux-k2")

#: ``None`` = configure with ``make defconfig`` (the K2 image as delivered).
#: Every other image pins every milestone symbol, so the shared build tree cannot
#: leak one image's configuration into another.
IMAGES = {
    "k2": None,
    "trap": [
        "CONFIG_DADAO_K1_EARLY_STOP=n",
        "CONFIG_DADAO_K2_EARLY_STOP=y",
        "CONFIG_DADAO_K2_TIME_STOP=n",
        "CONFIG_DADAO_K2_TRAP_SELFTEST=y",
        "CONFIG_DADAO_K2_SELFTEST_UNKNOWN=n",
        "CONFIG_DADAO_K2_SELFTEST_REENTRY=n",
        "CONFIG_DADAO_K2_SELFTEST_CFXTRAP=n",
        "CONFIG_DADAO_K2_SELFTEST_CFXESC=n",
        # m14-linux-012: the K3 page-fault probe is an int (0 = off).
        "CONFIG_DADAO_K3_PF_SELFTEST=0",
    ],
    "irq": [
        "CONFIG_DADAO_K1_EARLY_STOP=n",
        "CONFIG_DADAO_K2_EARLY_STOP=n",
        "CONFIG_DADAO_K2_TIME_STOP=y",
        "CONFIG_DADAO_K2_TIME_CASE=0",
        "CONFIG_DADAO_K2_IRQ_TEST=y",
        "CONFIG_DADAO_K2_TRAP_SELFTEST=n",
        "CONFIG_DADAO_K3_PF_SELFTEST=0",
    ],
}

#: The boundary symbols each image must carry in its own ``.config``.
IMAGE_CONFIG = {
    "k2": {"CONFIG_DADAO_K2_TIME_STOP": "y"},
    "trap": {"CONFIG_DADAO_K2_EARLY_STOP": "y", "CONFIG_DADAO_K2_TRAP_SELFTEST": "y"},
    "irq": {"CONFIG_DADAO_K2_TIME_STOP": "y", "CONFIG_DADAO_K2_IRQ_TEST": "y"},
}

#: Symbols that must be absent from an image's ``.config`` (the neighbouring
#: milestone boundaries), asserted as "no ``CONFIG_X=`` line at all".
IMAGE_UNSET = {
    "k2": ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP"),
    "trap": ("CONFIG_DADAO_K1_EARLY_STOP",),
    "irq": ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP",
            "CONFIG_DADAO_K2_TRAP_SELFTEST"),
}

KERNEL_BUILD = "vmlinux"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def num(text, default: int = -1) -> int:
    """A contract value (int) or a printed ``0x...``/decimal token; -1 if absent."""
    if isinstance(text, int):
        return text
    try:
        return int(str(text), 0)
    except (TypeError, ValueError):
        return default


def ints(groups) -> list[int]:
    return [int(value, 0) for value in groups]


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus live ``[STAT]``.

    ``<id>`` starts with the group letter (``B``/``E``/``T``/``M``/``S``/``X``/
    ``R``); the live per-group tally is what the gate prints at the end.
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
        for group in "BETMSXR":
            if group in self.groups:
                total, failed = self.groups[group]
                parts.append(f"{group} {total - failed}/{total}")
        return "  ".join(parts)


# ---------------------------------------------------------------------------
# derived expectation context
# ---------------------------------------------------------------------------

def contract() -> dict:
    """Boot ABI + boot info projection (the kernel window and the RAM window)."""
    k0.load_contract()
    if not k0.ABI or not k0.BOOT_INFO:
        raise SystemExit("check_k2: the boot contract projection is empty")
    return {"abi": k0.ABI, "boot_info": k0.BOOT_INFO}


def derivations(snap: dict) -> dict:
    """Everything the checks compare against, derived from @snap's own image."""
    ctx = contract()
    abi = ctx["abi"]
    bi = ctx["boot_info"]
    specs = k2trap.spec_exit_segments()
    hz = k2time.config_hz(snap["config"])
    freq = k2time.contract_freq()
    period = freq // hz
    if not period:
        raise SystemExit("check_k2: freq / CONFIG_HZ is zero")
    superpage = abi["superpage_size"]
    ram_size = num(bi["ram_size"]["value"])
    ram_base_va = num(bi["ram_base"]["value"])
    mapped = -(-ram_size // superpage)
    return {
        "specs": specs,
        "table": k2trap.spec_cause_table(),
        "codes": k2time.kernel_selfcheck_codes(),
        "freq": freq,
        "hz": hz,
        "period": period,
        "ticks": k2time.declared_ticks(),
        "entry_va": abi["entry_va"],
        "kernel_size": snap["kernel_size"],
        #: The first VA past the superpages the kernel maps (mm/k1_pt.c §2.2.1).
        "probe_va": ram_base_va + mapped * superpage,
        "cfxha_smon": k2time.cfxha("cfx_smon"),
    }


def cause_of(table, name: str) -> tuple[int, str]:
    for cause_id, cause_name in table:
        if cause_name == name:
            return cause_id, cause_name
    raise SystemExit(f"check_k2: spec/DADAO-13 §2 has no cause {name!r}")


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / KERNEL_BUILD


def config_image(image: str) -> int:
    """Configure @image's symbols (``make defconfig`` for the K2 image)."""
    if IMAGES[image] is None:
        cmd = [sys.executable, str(_REPO / "tools" / "linux" /
                                   "make_defconfig.py"), f"--jobs={JOBS}"]
        print(f"[INFO] configure {image} image (`make defconfig`)", flush=True)
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
        if proc.returncode != 0:
            print((proc.stdout or "")[-2000:], file=sys.stderr)
            print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode
    rc = defconfig.apply_config_lines(IMAGES[image])
    if rc != 0:
        print(f"check-linux-k2: FAIL: config slice for the {image} image rc={rc}",
              file=sys.stderr)
    return rc


def build_image(image: str) -> tuple[int, dict | None]:
    """Configure and build @image; returns (rc, snapshot of *this* image)."""
    rc = config_image(image)
    if rc != 0:
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build {image} image (JOBS={JOBS})", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    kernel = kernel_path()
    # The build tree is shared and every image overwrites it, so the .config, the
    # symbol table and the image size belong to *this* image: snapshot them here.
    ctx = contract()
    snap = {
        "config": (build_dir() / ".config").read_text(encoding="utf-8"),
        "syms": k1boot.symbols(kernel),
        "kernel": kernel,
        "kernel_size": k1boot.kernel_size_from_elf(kernel,
                                                   ctx["abi"]["entry_va"]),
    }
    return 0, snap


def firmware() -> str:
    """Assemble power + hmon + smon into one Vast BootROM (scratch)."""
    if not contract()["abi"]:
        raise SystemExit("check_k2: the boot contract projection is empty")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k0_k2.bin")


def boot(tag: str, rom: str, qemu: str) -> tuple[int, str, list[str]]:
    """Boot the current image under Vast; returns (guest rc, console, argv)."""
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"check_k2: {kernel} missing; run `make linux-vmlinux`")
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
        # report 124, exactly like the other Linux gates.
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = err or out
    log.write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# B: the image under test is the K2 image the gate asked for
# ---------------------------------------------------------------------------

def check_build(rep: Report, image: str, rc_build: int, snap: dict,
                cmd: list[str], text: str, terminating: bool = False) -> None:
    cfg = snap["config"].splitlines()
    for symbol, value in IMAGE_CONFIG[image].items():
        line = f"{symbol}={value}"
        rep.check("B1", f"{image} 镜像配置：{line}", line,
                  next((ln for ln in cfg if ln.startswith(symbol + "=")),
                       "<unset>"))
    for symbol in IMAGE_UNSET[image]:
        rep.check("B1", f"{image} 镜像配置：{symbol} 未设", [],
                  [ln for ln in cfg if ln.startswith(symbol + "=")])
    rep.check("B2", f"{image} 增量构建 rc", 0, rc_build)
    rep.check("B3", "命令行无 -d/-D（不用逐指令日志）", True,
              "-d" not in cmd and "-D" not in cmd)
    rep.check("B4", "输出无 panic/oops/BUG/Call Trace", [],
              [ln for ln in text.splitlines()
               if re.search(r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|Call Trace)",
                            ln)])
    if not terminating:
        # The trap image is *supposed* to end in the named termination E judges;
        # the plain images must not take any exception at all.
        rep.check("B5", "输出无具名异常终止（dadao: 行）", [],
                  [ln for ln in text.splitlines() if ln.startswith("dadao: ")])
        rep.check("B6", "输出无自检失败行（K2 fail: 行）", [],
                  [ln for ln in text.splitlines() if ln.startswith("K2 fail: ")])
    rep.stat(f"{image}: kernel={snap['kernel'].name} "
             f"{snap['kernel'].stat().st_size} B kernel_size="
             f"{hex(snap['kernel_size'])}")


# ---------------------------------------------------------------------------
# T: the clock (freq / monotone time / interval == freq/HZ / bounded margin)
# ---------------------------------------------------------------------------

def check_clock(rep: Report, rc: int, text: str, snap: dict, d: dict) -> None:
    freq, hz, period = d["freq"], d["hz"], d["period"]
    m = k2time.TIME_INIT.search(text)
    if not m:
        rep.check("T1", "time_init 行存在", "存在", "缺失")
        return
    printed_freq, printed_hz, printed_period, declared, first = ints(m.groups())
    rep.check("T1", "printed freq == 契约 cfx_time_freq（contract-see §3）",
              freq, printed_freq)
    rep.check("T2", "printed hz == 该镜像 .config 的 CONFIG_HZ（现场解析）",
              hz, printed_hz)
    rep.check("T3", "printed period == freq / hz（现场派生）", period,
              printed_period)
    rep.check("T4", "n_ticks == 内核声明 DADAO_K2_TIME_TICKS（asm/time.h）",
              d["ticks"], declared)

    ticks = [(int(i), int(t), int(j)) for i, t, j in k2time.TICK.findall(text)]
    rep.check("T5", "tick 行数 == 声明的 n_ticks", declared, len(ticks))
    rep.check("T6", "tick 序号 == 1..n", list(range(1, len(ticks) + 1)),
              [index for index, _t, _j in ticks])
    times = [value for _i, value, _j in ticks]
    rep.check("T7", "time 严格单调递增", True,
              all(left < right for left, right in zip(times, times[1:])))
    jiffies = [value for _i, _t, value in ticks]
    rep.check("T8", "相邻 tick 的 jiffies 前进 1", [1] * max(0, len(jiffies) - 1),
              [right - left for left, right in zip(jiffies, jiffies[1:])])
    rep.check("T9", "首个时间读数 > 0 且 < 1 秒（freq 个 count，现场派生）", True,
              bool(period) and 0 < first < printed_freq)

    margin = period // 2
    if len(times) >= 2 and period:
        deltas = [right - left for left, right in zip(times, times[1:])]
        devs = [abs(delta - period) for delta in deltas]
        rep.check("T10", f"每个 tick 间隔与 period 的偏差 <= margin（{margin}）",
                  True, all(dev <= margin for dev in devs))
        rep.check("T11", "margin 有上界：4×实测最大偏差 <= margin", True,
                  4 * max(devs) <= margin)
        rep.stat(f"tick deltas={deltas} deviations={devs} max={max(devs)} "
                 f"margin={margin}")

    m = k2time.SUMMARY.search(text)
    if not m:
        rep.check("T12", "tick 汇总行存在", "存在", "缺失")
    else:
        total, jdelta = ints(m.groups())
        rep.check("T12", "汇总 tick 数 == 声明的 n_ticks", declared, total)
        rep.check("T13", "汇总 jiffies 前进 == n_ticks", declared, jdelta)

    m = k2time.AFTER_STOP.search(text)
    if not m:
        rep.check("T14", "停止后控制行存在", "存在", "缺失")
    else:
        after, window = ints(m.groups())
        rep.check("T14", "定时器停止后不再有 tick", 0, after)
        rep.check("T15", "停止后等待窗 >= 2 个 period（现场派生）", True,
                  window >= 2 * period)

    m = k2time.DONE.search(text)
    rep.check("T16", "退出行的 tick 数 == 声明的 n_ticks", declared,
              int(m.group(1)) if m else "<missing>")
    rep.check("T17", "guest rc（SYS_EXIT 子码）", 0, rc)


# ---------------------------------------------------------------------------
# E: the synchronous exception channel (declared vs undeclared CFXMEM)
# ---------------------------------------------------------------------------

def check_exception(rep: Report, rc: int, text: str, d: dict) -> None:
    specs = d["specs"]
    cause_id, cause_name = cause_of(d["table"], "CFXMEM")
    low, high = d["entry_va"], d["entry_va"] + d["kernel_size"]

    m = re.search(r"^K2 selftest: probe_va=(\S+) ", text, re.MULTILINE)
    probe_va = m.group(1) if m else None
    rep.check("E1", "自检报告 probe_va == 契约派生的首个 RAM 外超页",
              hex(d["probe_va"]), probe_va)

    rows = k2trap.hits(text, "probe")
    first = rows[0] if rows else None
    rep.check("E2", "预先声明的 CFXMEM 命中 1 次", 1,
              first["hit"] if first else "<missing>")
    rep.check("E3", "命中行的原因名 == spec/DADAO-13 §2 的表名", cause_name,
              first["cause"] if first else "<missing>")
    rep.check("E4", "命中行的 info == probe_va", probe_va,
              first["info"] if first else "<missing>")
    ip = num(first["ip"]) if first else 0
    rep.check("E5", "命中行的 ip 在内核镜像内（[entry, entry+size)）", True,
              bool(first) and low <= ip < high)

    line = k2trap.probe_lines(text).get("P1", "")
    tokens = {tok.split("=")[0]: tok.split("=")[1]
              for tok in line.split() if "=" in tok}
    rep.check("E6", "P1 故障被分类后按 +4 续跑（resumed=yes）", "yes",
              tokens.get("resumed", "<missing>"))
    rep.check("E7", "P1 续跑后的代码确实执行（标记非 0）", True,
              num(tokens.get("marker"), 0) != 0)

    die = k2trap.die_line(text)
    want = k2time.monitor_code(specs, "supv", "CFXMEM")
    rep.check("E8", "未声明的 CFXMEM：退出码 == §7.1 supv+CFXMEM", hex(want),
              hex(rc))
    rep.check("E9", "未声明：终止行的原因名", cause_name,
              die["cause"] if die else "<missing>")
    rep.check("E10", "未声明：终止行的原因编号 == 1<<位号", hex(cause_id),
              die["id"] if die else "<missing>")
    rep.check("E11", "未声明：终止行的 info == probe_va", probe_va,
              die["info"] if die else "<missing>")
    die_ip = num(die["ip"]) if die else 0
    rep.check("E12", "未声明：终止行的 ip 在内核镜像内", True,
              bool(die) and low <= die_ip < high)

    fatal = k2trap.fatal_lines(text)
    rep.check("E13", "不递归：终止行总数 == 1", 1, len(fatal))
    rep.check("E14", "不递归：无 recursive supv exception 行", [],
              [ln for ln in fatal if "recursive" in ln])
    rep.check("E15", "未续跑：无 P3 FAIL 行", [],
              re.findall(r"^K2 probe P3: FAIL.*$", text, re.MULTILINE))


# ---------------------------------------------------------------------------
# M: the masked window and the +1 release
# ---------------------------------------------------------------------------

def check_mask(rep: Report, text: str, d: dict) -> None:
    period = d["period"]
    window = None
    m = k2irq.P2_MASKED.search(text)
    if not m:
        rep.check("M1", "屏蔽窗口行存在", "存在", "缺失")
    else:
        ticks, ctrl, window = int(m.group(1)), int(m.group(2), 0), int(m.group(3))
        rep.check("M1", "屏蔽窗内 tick 计数不前进（冻结）", 0, ticks)
        rep.check("M2", "屏蔽窗内 ISTATUS 置位（事件发生、只记 pending）", 1,
                  (ctrl >> 2) & 1)
        rep.check("M3", "屏蔽窗 >= 3 个 period（现场派生）", True,
                  window >= 3 * period)

    m = k2irq.P2_RELEASED.search(text)
    if not m:
        rep.check("M4", "解除屏蔽行存在", "存在", "缺失")
    else:
        released, rel_window, elapsed = ints(m.groups())
        rep.check("M4", "解除后计数恰增 1（合并补投，不丢不多）", 1, released)
        rep.check("M5", "释放测量窗 == period/2（现场派生）", period // 2,
                  rel_window)
        rep.check("M6", "投递在半个 period 内完成（不是周期重挂的那一次）", True,
                  elapsed < rel_window)
        rep.stat(f"P2 masked window={window} released={released} "
                 f"elapsed={elapsed} period={period}")

    frame = k2irq.P4_FRAME.search(text)
    after = k2irq.P4_AFTER.search(text)
    if not frame or not after:
        rep.check("M7", "帧内/帧后两行存在", "存在", "缺失")
        return
    tick, waited, ctrl, _window, _elapsed = ints(frame.groups())
    delivered, gap, printed_period = ints(after.groups())
    rep.check("M7", "帧内不再投递第二次 tick（硬件全局轴仍挡）", 0, waited)
    rep.check("M8", "帧内事件已到期（ISTATUS 置位）", 1, (ctrl >> 2) & 1)
    rep.check("M9", "escape 释放帧后补投恰 +1", tick + 1, delivered)
    rep.check("M10", "补投紧跟帧结束（gap < period/2，不是周期重挂）", True,
              gap < period // 2)
    rep.check("M11", "帧内报告的 period == freq/HZ（现场派生）", period,
              printed_period)
    rep.stat(f"P4 frame tick={tick} after={delivered} gap={gap} "
             f"period={printed_period}")


# ---------------------------------------------------------------------------
# S: the end-to-end stage order (reused assertion 原①)
# ---------------------------------------------------------------------------

#: One anchor per stage.  power/hmon/smon run before the kernel prints anything,
#: so they are evidenced by the firmware image (S1) and by the kernel's handover
#: lines (boot info block = hmon, pre-switch PTBR = smon); every stage after that
#: has its own line.
STAGE_ANCHORS = (
    ("hmon", r"^K1 bootinfo magic="),
    ("kernel-entry", r"^K1 stack sp="),
    ("sync-vector", r"^K1 ptw vec  supv_excp_vector="),
    ("smon", r"^K1 ptw pre  ptbr="),
    ("table", r"^K1 ptw map  ram_pa="),
    ("install", r"^K1 ptw post ptbr="),
    ("switch", r"^K1 ptw new  va="),
    ("table-done", r"^K1 ptw done: running on the kernel-built table$"),
    ("start_kernel", r"^K2 setup_arch: memblock_add "),
    ("time_init", r"^K2 time_init: freq="),
    ("async-vector", r"^K2 irq: vec cfx_hart_supv_excp_vector="),
    ("mask-axes", r"^K2 irq: mask cfx_smon_supv_cfx_intr_mask="),
    ("armed", r"^K2 irq: armed ticks period="),
    ("first-tick", r"^K2 irq P1: "),
    ("masked-window", r"^K2 irq P2: masked "),
    ("exit", r"^K2 irq: done ticks="),
)


def check_order(rep: Report, text: str, rom: str) -> None:
    """The chain power -> ... -> SYS_EXIT(0), each stage once and in order.

    The firmware half (power/hmon/smon) is read out of the BootROM image the gate
    just built: the individual stage fields are K1's business; the fact that
    matters here is that the chain starts at power (reset vector inside the power
    window, hmon before smon).
    """
    table = k1gate.bootrom_table(Path(rom))
    stages = [k1gate.STAGE_TYPES.get(entry["type"]) for entry in table["entries"]]
    profile = k1gate.machine_profile.load(PROFILE)
    reset_offset = profile.reset_pc - profile["bootrom_base"]
    power_window = table["image"][reset_offset:reset_offset
                                  + k1gate.POWER_WINDOW]
    rep.check("S1", "固件阶段顺序 power→hmon→smon（复位向量在 power 窗口内、"
                    "索引表 hmon 先于 smon）", True,
              stages == ["hmon", "smon"]
              and profile.reset_pc == profile["bootrom_base"]
              + profile["bootrom_size"] - k1gate.POWER_WINDOW
              and any(power_window))

    lines = text.splitlines()
    order: list[tuple[str, int]] = []
    for stage, pattern in STAGE_ANCHORS:
        hits = [index for index, line in enumerate(lines)
                if re.match(pattern, line)]
        rep.check("S2", f"阶段 {stage} 出现 1 次", 1, len(hits))
        if hits:
            order.append((stage, hits[0]))
    rep.check("S3", "阶段顺序 == 常量表顺序",
              [stage for stage, _ in STAGE_ANCHORS],
              [stage for stage, _ in order])
    rep.check("S4", "阶段行号严格递增", True,
              all(left[1] < right[1] for left, right in zip(order, order[1:])))
    non_empty = [line for line in lines if line.strip()]
    rep.check("S5", "退出标记（SYS_EXIT）是输出的最后一行", True,
              bool(non_empty) and non_empty[-1].startswith("K2 irq: done"))
    rep.stat(f"阶段锚点 {len(order)}/{len(STAGE_ANCHORS)}")


# ---------------------------------------------------------------------------
# X: the A′ exit-code segmentation (reused assertion 原⑤)
# ---------------------------------------------------------------------------

def check_exit_static(rep: Report, pass_rc: int, d: dict) -> None:
    """PASS value, the segment table and the kernel's own verdict constants."""
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
    rep.check("X2", "PASS 镜像 guest rc == §7.1 的 PASS 值", pass_low, pass_rc)

    codes = d["codes"]
    outside = {name: value for name, value in codes.items()
               if not (guest_low <= value <= guest_high)}
    rep.check("X3", f"自检码全在 guest 段（{hex(guest_low)}-{hex(guest_high)}）",
              {}, outside)
    in_monitor = {name: value for name, value in codes.items()
                  if monitor_low <= value <= monitor_high
                  or other_low <= value <= other_high}
    rep.check("X4", "自检码无一落 monitor / 其它 cfx 段", {}, in_monitor)
    values = list(codes.values())
    rep.check("X5", "自检码互不重复（跨 head/setup/k1_pt/trap/time/irq）", True,
              len(values) == len(set(values)))
    rep.stat("自检码 " + " ".join(f"{name.split(':')[-1]}={hex(value)}"
                                  for name, value in sorted(codes.items())))
    rep.stat(f"segments pass={hex(pass_low)} guest={hex(guest_low)}-"
             f"{hex(guest_high)} other={hex(other_low)}-{hex(other_high)} "
             f"monitor={hex(monitor_low)}-{hex(monitor_high)}")


def check_exit_trap(rep: Report, rc: int, text: str, d: dict) -> None:
    """The abnormal termination's code, and the four branches the kernel predicts."""
    specs = d["specs"]
    ranges = specs["ranges"]
    guest_low, guest_high = ranges["guest"]
    monitor_low, monitor_high = ranges["monitor"]
    other_low, _other_high = ranges["other"]

    want = k2time.monitor_code(specs, "supv", "CFXMEM")
    rep.check("X6", "异常终止 rc == 0xC0|supv<<4|CFXMEM 位号（supv ⇒ 0xE0|bit）",
              hex(want), hex(rc))
    rep.check("X7", "异常终止 rc 落 monitor 段且不落 guest 段", True,
              monitor_low <= rc <= monitor_high
              and not (guest_low <= rc <= guest_high))

    m = re.search(r"^K2 probe P7: exit-code (.*)$", text, re.MULTILINE)
    predicted = {}
    if m:
        predicted = {tok.split("=")[0]: tok.split("=")[1]
                     for tok in m.group(1).split() if "=" in tok}
    other = hex(other_low | d["cfxha_smon"])          # 0x80 | cfxHA(cfx_smon)
    want_pred = {
        "trap": other,
        "esc": other,
        "cfxmem": hex(k2time.monitor_code(specs, "supv", "CFXMEM")),
        "illi": hex(k2time.monitor_code(specs, "supv", "ILLI")),
    }
    rep.check("X8", "内核自报的四段退出码 == spec 派生（trap/esc/CFXMEM/ILLI）",
              want_pred, predicted)
    rep.check("X9", "自报的 CFXMEM/ILLI 不落 guest 段（与自检点可区分）", True,
              bool(predicted) and all(num(predicted.get(key), 0) > guest_high
                                      for key in ("cfxmem", "illi")))


# ---------------------------------------------------------------------------
# R: no regression (K0 / K1 closure gates)
# ---------------------------------------------------------------------------

def run_closure_gate(script: str, tag: str) -> tuple[int, str]:
    """Run another Linux closure gate as a subprocess and return (rc, output)."""
    env = dict(os.environ, JOBS=str(JOBS),
               K0_TMP=str(SCRATCH / f"regress-k0-{tag}"),
               K1_TMP=str(SCRATCH / f"regress-k1-{tag}"))
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / script)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_REGRESS, env=env)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + (exc.stderr or "")


def check_regression(rep: Report, k0_result=None, k1_result=None) -> None:
    """R: the two earlier closure gates still pass (their own counts, parsed)."""
    if k0_result is None:
        print("[INFO] R: 运行 check-linux-k0", flush=True)
        k0_result = run_closure_gate("check_k0.py", "k0")
    if k1_result is None:
        print("[INFO] R: 运行 check-linux-k1", flush=True)
        k1_result = run_closure_gate("check_k1.py", "k1")

    rc, out = k0_result
    m = re.search(r"^(\d+)/(\d+) 项通过", out, re.MULTILINE)
    rep.check("R1", "check-linux-k0 rc", 0, rc)
    rep.check("R2", "check-linux-k0 计数（现场解析：通过 == 总数）", True,
              bool(m) and int(m.group(1)) == int(m.group(2))
              and int(m.group(2)) > 0)
    rep.stat(f"check-linux-k0: rc={rc} {m.group(0) if m else '<无计数行>'}")

    rc, out = k1_result
    m = re.search(r"^check-linux-k1: PASS \((\d+)/(\d+)\)", out, re.MULTILINE)
    rep.check("R3", "check-linux-k1 rc", 0, rc)
    rep.check("R4", "check-linux-k1 计数（现场解析：通过 == 总数）", True,
              bool(m) and int(m.group(1)) == int(m.group(2))
              and int(m.group(2)) > 0)
    rep.stat(f"check-linux-k1: rc={rc} {m.group(0) if m else '<无计数行>'}")


# ---------------------------------------------------------------------------
# per-image check bundles
# ---------------------------------------------------------------------------

def check_k2_image(rep: Report, rc: int, text: str, cmd: list[str], snap: dict,
                   rc_build: int, d: dict) -> None:
    check_build(rep, "k2", rc_build, snap, cmd, text)
    check_clock(rep, rc, text, snap, d)
    check_exit_static(rep, rc, d)


def check_trap_image(rep: Report, rc: int, text: str, cmd: list[str], snap: dict,
                     rc_build: int, d: dict) -> None:
    check_build(rep, "trap", rc_build, snap, cmd, text, terminating=True)
    check_exception(rep, rc, text, d)
    check_exit_trap(rep, rc, text, d)


def check_irq_image(rep: Report, rc: int, text: str, cmd: list[str], snap: dict,
                    rc_build: int, d: dict, rom: str) -> None:
    check_build(rep, "irq", rc_build, snap, cmd, text)
    check_mask(rep, text, d)
    check_order(rep, text, rom)
    rep.check("M12", "irq 镜像 guest rc（SYS_EXIT 子码）", 0, rc)


BUNDLES = {"k2": check_k2_image, "trap": check_trap_image, "irq": check_irq_image}


def judge(rep: Report, result: dict) -> None:
    """Run every image's bundle on the captured runs (the judging half)."""
    for image in IMAGES:
        rc, text, cmd = result["runs"][image]
        bundle = BUNDLES[image]
        if image == "irq":
            bundle(rep, rc, text, cmd, result["snaps"][image],
                   result["builds"][image], result["derivs"][image],
                   result["rom"])
        else:
            bundle(rep, rc, text, cmd, result["snaps"][image],
                   result["builds"][image], result["derivs"][image])


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------

def gate(rep: Report, qemu: str, regress: bool = True) -> dict:
    """Build and boot the three images, judge them, then run the R sub-gates."""
    rom = firmware()
    print(f"k2 gate: bootrom={Path(rom).name} qemu={Path(qemu).name} "
          f"md5={md5(Path(qemu))[:8]}", flush=True)
    result = {"runs": {}, "snaps": {}, "builds": {}, "derivs": {}, "rom": rom}
    for image in IMAGES:
        rc_build, snap = build_image(image)
        result["builds"][image] = rc_build
        rep.check("B0", f"{image} 镜像可构建", 0, rc_build)
        if snap is None:
            raise SystemExit(f"check_k2: build {image} rc={rc_build}")
        result["snaps"][image] = snap
        result["derivs"][image] = derivations(snap)
        result["runs"][image] = boot(image, rom, qemu)
        rc, text, _cmd = result["runs"][image]
        print(f"---- guest output ({image}, rc={hex(rc)}) ----", flush=True)
        print(text.strip(), flush=True)
        print("-----------------------------------------------", flush=True)

    judge(rep, result)
    if regress:
        check_regression(rep)
    return result


# ---------------------------------------------------------------------------
# --selfcheck: every group must be able to fail
# ---------------------------------------------------------------------------

def run_selfcheck(qemu: str) -> int:
    """Mutate the captured runs / the captured .config and show every group flips."""
    result = gate(Report(quiet=True), qemu, regress=False)
    runs, snaps, builds, derivs = (result["runs"], result["snaps"],
                                   result["builds"], result["derivs"])
    rom = result["rom"]
    krc, ktext, kcmd = runs["k2"]
    trc, ttext, tcmd = runs["trap"]
    irc, itext, icmd = runs["irq"]

    base = Report(quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        judge(base, result)
    print(f"  [{'PASS' if not base.fails else 'FAIL'}] selfcheck 基准三镜像全绿 | "
          f"期望=0 失败 实际={len(base.fails)} 失败", flush=True)

    flipped: dict[str, bool] = {}

    def flip(group: str, label: str, fn) -> None:
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            fn(rep)
        red = [msg for msg in rep.fails if msg.startswith(group)]
        print(f"  [{'PASS' if red else 'FAIL'}] selfcheck {label} | "
              f"期望={group} FAIL 实际={red[0] if red else '未翻转'}",
              flush=True)
        flipped[group] = flipped.get(group, True) and bool(red)

    # B: the captured .config loses the K2 boundary and gains a K1 stop.
    broken_cfg = (snaps["k2"]["config"].replace(
        "CONFIG_DADAO_K2_TIME_STOP=y", "# CONFIG_DADAO_K2_TIME_STOP is not set")
        + "CONFIG_DADAO_K1_EARLY_STOP=y\n")
    flip("B", "B 配置被改", lambda rep: check_build(
        rep, "k2", 1, dict(snaps["k2"], config=broken_cfg), kcmd, ktext))

    # T: a hardcoded HZ, a missing tick, a non-zero exit code.
    flip("T", "T hz 被改", lambda rep: check_clock(
        rep, krc, re.sub(r"(K2 time_init: freq=\d+ hz=)\d+",
                         rf"\g<1>{derivs['k2']['hz'] + 1}", ktext),
        snaps["k2"], derivs["k2"]))
    flip("T", "T tick 行被删", lambda rep: check_clock(
        rep, krc, re.sub(r"^K2 tick 2: .*\n", "", ktext, flags=re.MULTILINE),
        snaps["k2"], derivs["k2"]))
    flip("T", "T rc 非 0", lambda rep: check_clock(
        rep, 1, ktext, snaps["k2"], derivs["k2"]))

    # E: the resume disappears / the termination code moves into the guest segment.
    flip("E", "E 未续跑", lambda rep: check_exception(
        rep, trc, ttext.replace("hits=1 resumed=yes marker=0x5031",
                                "hits=1 resumed=no marker=0x0"), derivs["trap"]))
    flip("E", "E 终止码进 guest 段", lambda rep: check_exception(
        rep, 0x61, ttext, derivs["trap"]))

    # M: the window is not frozen / the release delivers twice.
    flip("M", "M 窗内投递", lambda rep: check_mask(
        rep, itext.replace("K2 irq P2: masked ticks=0",
                           "K2 irq P2: masked ticks=2"), derivs["irq"]))
    flip("M", "M 释放补投两次", lambda rep: check_mask(
        rep, itext.replace("K2 irq P2: released ticks=1",
                           "K2 irq P2: released ticks=2"), derivs["irq"]))

    # S: an anchor disappears / the exit is no longer the last line.
    flip("S", "S 缺 armed 锚点", lambda rep: check_order(
        rep, re.sub(r"^K2 irq: armed .*\n", "", itext, flags=re.MULTILINE),
        rom))
    flip("S", "S 退出行不是最后一行", lambda rep: check_order(
        rep, itext + "dadao: trailing\n", rom))

    # X: PASS becomes a guest code / the predicted monitor code lands in guest.
    flip("X", "X PASS 镜像 rc 非 PASS", lambda rep: check_exit_static(
        rep, 0x13, derivs["k2"]))
    flip("X", "X 自报码落 guest 段", lambda rep: check_exit_trap(
        rep, trc, ttext.replace("cfxmem=0xe1", "cfxmem=0x61"), derivs["trap"]))

    # X3/X4 read the source scan; flip one code into the monitor segment.
    saved = k2time.kernel_selfcheck_codes
    try:
        k2time.kernel_selfcheck_codes = lambda: {
            **derivs["trap"]["codes"], "arch/dadao/kernel/head.S:FAIL_X": 0xE1}
        flip("X", "X 自检码进 monitor 段", lambda rep: check_exit_static(
            rep, krc, derivations(snaps["trap"])))
    finally:
        k2time.kernel_selfcheck_codes = saved

    # R: a synthetic failing sub-gate result.
    flip("R", "R k0 失败", lambda rep: check_regression(
        rep, k0_result=(1, "118/119 项通过\n"),
        k1_result=(0, "check-linux-k1: PASS (10/10)\n")))

    groups = [group for group in "BETMSXR" if flipped.get(group)]
    missing = [group for group in "BETMSXR" if not flipped.get(group)]
    print(f"check-k2 selfcheck: {'PASS' if not missing else 'FAIL'} "
          f"({len(groups)}/7 组可翻转；未翻转 {missing})")
    return 0 if not missing and not base.fails else 1


# ---------------------------------------------------------------------------
# --inject: real corruptions, rebuilt and restored (cp + md5)
# ---------------------------------------------------------------------------

IRQ_C = "arch/dadao/kernel/irq.c"
TIME_C = "arch/dadao/kernel/time.c"
TRAPS_C = "arch/dadao/kernel/traps.c"

def _tick_state(text: str) -> str:
    return "有 K2 tick" if re.search(r"^K2 tick ", text, re.MULTILINE) else "无 K2 tick"


def _exit_state(text: str) -> str:
    return ("有 K2 time: done"
            if re.search(r"^K2 time: done", text, re.MULTILINE)
            else "无 K2 time: done")


def _in_guest(code: int, d: dict) -> str:
    low, high = d["specs"]["ranges"]["guest"]
    return hex(code) if low <= code <= high else f"{hex(code)} 越界"


#: name -> (image, relative source, exact text, replacement, groups that must go
#:          red, verdict(rc, text, derivs) -> [(label, ok, expected, actual)])
INJECTIONS = {
    # ① The asynchronous vector is written one superpage past the image: the
    #    read-back still passes (both sides use the corrupted value), so the very
    #    first delivery leaves the kernel and no tick is ever accounted.
    "async-vector-unmapped": (
        "k2", IRQ_C,
        "\tunsigned long vec = (unsigned long)dadao_async_excp;\n",
        "\tunsigned long vec = (unsigned long)dadao_async_excp + 0x2000000UL;\n",
        ("T", "X"),
        lambda rc, text, d: [
            ("首次 tick 不可恢复（rc != 0）", rc != 0, "!=0", hex(rc)),
            ("未产生 tick 行", _tick_state(text) == "无 K2 tick", "无 K2 tick",
             _tick_state(text)),
            ("未走到退出行", _exit_state(text) == "无 K2 time: done",
             "无 K2 time: done", _exit_state(text)),
        ],
    ),
    # ② The handler re-arms with `cmp = now`: every escape is followed by the next
    #    delivery, so the tick series never completes (no tick line, no exit
    #    line) — the interval/count assertions cannot be satisfied.
    "period-zero": (
        "k2", TIME_C,
        "\t\t\tnow + dadao_period);\n",
        "\t\t\tnow + 0UL);\n",
        ("T", "X"),
        lambda rc, text, d: [
            ("重挂后无 tick 行", _tick_state(text) == "无 K2 tick", "无 K2 tick",
             _tick_state(text)),
            ("未走到退出行", _exit_state(text) == "无 K2 time: done",
             "无 K2 time: done", _exit_state(text)),
            ("boot 未以 SYS_EXIT(0) 结束", rc != 0, "!=0", hex(rc)),
        ],
    ),
    # ③ Only the source axis is opened: the global axis stays closed, so no
    #    delivery happens at all and the masked-window case never runs.
    "one-axis-only": (
        "irq", IRQ_C,
        "\tmask = smon_global_intr_mask() & ~bit;\n"
        "\tDADAO_CFX_WRITE(cfx_smon, CFX_SMON_CG_GLOBAL,\n"
        "\t\t\tCFX_SMON_RC_GLOBAL_CFX_INTR_MASK, mask);\n",
        "\tmask = smon_global_intr_mask();\n",
        ("M", "S"),
        lambda rc, text, d: [
            ("内核自报首个 tick 未到",
             "K2 fail: irq test: first TIMER tick" in text,
             "有「K2 fail: irq test: first TIMER tick」",
             "有" if "first TIMER tick" in text else "无"),
            ("自报失败码落 guest 段（§7.1）",
             d["specs"]["ranges"]["guest"][0] <= rc
             <= d["specs"]["ranges"]["guest"][1],
             f"{hex(d['specs']['ranges']['guest'][0])}-"
             f"{hex(d['specs']['ranges']['guest'][1])}", _in_guest(rc, d)),
            ("无屏蔽窗行", "K2 irq P2: masked" not in text, "无 P2 masked",
             "无 P2 masked" if "K2 irq P2: masked" not in text else "有 P2 masked"),
        ],
    ),
    # ④ The monitor segment's base moves into the guest segment: an unrecoverable
    #    CFXMEM becomes indistinguishable from a self-check point in `$?`.
    "die-code-guest": (
        "trap", TRAPS_C,
        "#define DADAO_EXIT_MONITOR(mode, index) \\\n"
        "\t(0xc0UL | (((mode) & 0x3) << 4) | ((index) & 0xf))\n",
        "#define DADAO_EXIT_MONITOR(mode, index) \\\n"
        "\t(0x40UL | (((mode) & 0x3) << 4) | ((index) & 0xf))\n",
        ("E", "X"),
        lambda rc, text, d: [
            ("终止码落 guest 段（不再是 monitor 段）",
             d["specs"]["ranges"]["guest"][0] <= rc
             <= d["specs"]["ranges"]["guest"][1],
             f"{hex(d['specs']['ranges']['guest'][0])}-"
             f"{hex(d['specs']['ranges']['guest'][1])}", _in_guest(rc, d)),
            ("P7 自报的 CFXMEM 码也进了 guest 段",
             bool(re.search(r"cfxmem=0x[0-7][0-9a-f]?\b", text)),
             "P7 cfxmem ∈ 0x00-0x7f",
             re.search(r"cfxmem=\S+", text).group(0)
             if re.search(r"cfxmem=\S+", text) else "<missing>"),
        ],
    ),
}


def run_inject(name: str, qemu: str, rom: str, problems: list[str]) -> None:
    """One source injection: patch -> rebuild -> red -> restore -> rebuild -> green."""
    image, rel, old, new, groups, verdict = INJECTIONS[name]
    path = linux_paths.linux_source_dir() / rel
    before = md5(path)
    backup = path.read_bytes()
    text = backup.decode("utf-8")
    print(f"── inject:{name}（镜像 {image}，{rel}）──", flush=True)
    if text.count(old) != 1:
        problems.append(f"inject:{name}: 注入点不唯一（{text.count(old)} 处）")
        return
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    if md5(path) == before:
        problems.append(f"inject:{name}: 注入是空操作（md5 未变）")
        path.write_bytes(backup)
        return
    print(f"  [PASS] inject:{name} 已注入 | md5 {before[:8]} -> "
          f"{md5(path)[:8]}", flush=True)

    # Any failure still restores the source *and* rebuilds, so no later step can
    # run against a kernel built from the injected tree.
    try:
        rc_build, snap = build_image(image)
        checks: list[tuple[str, bool, str, str]] = []
        if snap is None:
            problems.append(f"inject:{name}: 注入后重建 rc={rc_build}")
        else:
            rc, out, cmd = boot(f"inject-{name}", rom, qemu)
            print(f"---- guest output ({name}, rc={hex(rc)}) ----", flush=True)
            print(out.strip(), flush=True)
            print("-----------------------------------------------", flush=True)
            rep = Report(quiet=True)
            d = derivations(snap)
            if image == "irq":
                check_irq_image(rep, rc, out, cmd, snap, rc_build, d, rom)
            else:
                BUNDLES[image](rep, rc, out, cmd, snap, rc_build, d)
            for group in groups:
                red = [msg for msg in rep.fails if msg.startswith(group)]
                checks.append((f"断言组 {group} 变红", bool(red),
                               f"{group} 出现 FAIL", red[0] if red else "未变红"))
            checks.extend(verdict(rc, out, d))
        for label, ok, expected, actual in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} {label} | "
                  f"期望={expected} 实际={actual}", flush=True)
            if not ok:
                problems.append(f"inject:{name}: {label}（期望 {expected}，"
                                f"实际 {actual}）")
    except Exception as exc:                 # keep going; restore below
        problems.append(f"inject:{name}: {type(exc).__name__}: {exc}")
    finally:
        path.write_bytes(backup)             # cp + md5, never `git checkout`
        restored = md5(path)
        ok = restored == before
        print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} 还原 (cp) | "
              f"md5 期望={before[:8]} 实际={restored[:8]}", flush=True)
        if not ok:
            problems.append(f"inject:{name}: 还原后 md5 不一致")

    rc_build, snap = build_image(image)
    if snap is None:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    rc, out, cmd = boot(f"restored-{name}", rom, qemu)
    rep = Report(quiet=True)
    d = derivations(snap)
    if image == "irq":
        check_irq_image(rep, rc, out, cmd, snap, rc_build, d, rom)
    else:
        BUNDLES[image](rep, rc, out, cmd, snap, rc_build, d)
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
    ap.add_argument("--qemu", default=os.environ.get("K2G_QEMU"),
                    help="qemu-system-dadao binary (default: install root)")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured runs / .config: every group must flip")
    ap.add_argument("--inject", action="store_true",
                    help="four source injections: rebuild, assert FAIL, restore")
    ap.add_argument("--no-regress", action="store_true",
                    help="skip the R (K0/K1) sub-gates; iteration only, the make "
                         "target never passes this")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(["positive", "selfcheck"] +
                        [f"inject:{name}" for name in INJECTIONS]))
        return 0

    qemu = args.qemu or k0.DEFAULT_QEMU
    if not Path(qemu).is_file():
        print(f"check-linux-k2: FAIL: {qemu} missing; run `make install-host`",
              file=sys.stderr)
        return 1

    if args.selfcheck:
        try:
            return run_selfcheck(qemu)
        except SystemExit as exc:
            print(f"check-linux-k2: {exc}", file=sys.stderr)
            return 2

    rep = Report()
    try:
        result = gate(rep, qemu, regress=not args.no_regress)
        if args.inject:
            if rep.fails:
                print("check-linux-k2: 基线不绿，先修基线再做注入", flush=True)
            else:
                problems: list[str] = []
                for name in INJECTIONS:
                    run_inject(name, qemu, result["rom"], problems)
                total = len(INJECTIONS)
                if problems:
                    print(f"check-linux-k2 --inject: FAIL "
                          f"({len(problems)} 问题；{total} 路注入)", flush=True)
                    for problem in problems:
                        print("  - " + problem)
                    return 1
                print(f"check-linux-k2 --inject: PASS "
                      f"({total}/{total} 路注入按预期变红并还原)", flush=True)
    except SystemExit as exc:
        print(f"check-linux-k2: {exc}", file=sys.stderr)
        return 2

    print(f"\n[GROUP] {rep.summary()}")
    if not rep.fails:
        print(f"check-linux-k2: PASS ({rep.total}/{rep.total})")
    else:
        print(f"check-linux-k2: FAIL ({rep.total - len(rep.fails)}/{rep.total}); "
              f"{len(rep.fails)} 项失败")
        for failure in rep.fails:
            print("  - " + failure)
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
