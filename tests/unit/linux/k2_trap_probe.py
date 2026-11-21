#!/usr/bin/env python3
"""k2_trap_probe.py — M14 K2 supv-exception channel gate (`m14-linux-006`).

K2 makes the supv synchronous-exception entry a channel instead of the K1
one-shot probe: the entry captures the whole register file, the C half
dispatches by cause, resumable faults come back through the registered probe
API, everything else stops with a named cause and the exit code
spec/Kaiwu §7.1 assigns to it.

What this gate asserts, and where each expectation comes from (nothing is
restated here):

  * the cause table (11 names + ids) -> parsed live out of
    ``spec/DADAO-12 §4.1 cfx_umon`` (the monitor 原因表 is shared by
    ``cfx_umon``/``jmon``/``smon``/``hmon``; contract-see §6.1 is the same
    table);
  * the exit-code segmentation -> parsed live out of
    ``spec/Kaiwu §7.1``: the segment ranges, the run-mode encoding
    (``supv = 10b``) and the 11 monitor bit indices;
  * the escape offsets -> ``escape cfx_smon, [excp_cause_ip, {0,4}]`` in
    ``.tao/contracts/contract-see.md`` §4;
  * the boot/PTW evidence the K1 chain already produced -> the kernel's own
    log lines (the K1 gate owns their field-by-field checks);
  * ``current`` is valid (printk runs) -> the plain image boots past
    ``setup_arch()`` instead of dying in the printk prologue.

Images (each one is configured explicitly — the build tree is shared, so no
image may inherit whichever gate configured it last):

  plain    K2 image: K1 stop off, K2 boundary on, self-test off   -> SYS_EXIT(0)
  probe    + CONFIG_DADAO_K2_TRAP_SELFTEST=y                      -> P1/P2/P5/P3
  unknown  + CONFIG_DADAO_K2_SELFTEST_UNKNOWN=y                   -> P4

Checks:

  C1  configuration of the plain image (.config) and the self-check code
      segmentation of the sources (guest segment 0x01-0x7f only)
  C2  plain image: stage order (boot info -> stack -> vector -> table -> switch
      -> setup_arch -> cause table -> K2 boundary) and SYS_EXIT(0); the K2
      boundary is the last line; no clock/timer/IRQ bring-up before it
  C3  cause table == spec/DADAO-12 §4.1 (ids, names, order) and the dispatcher
      reports the same count
  C4  the entry the kernel installed is its own vector, and the escape offsets
      it may use are the contract's two
  C5  probe image P1: a registered CFXMEM is classified and *skipped*, so the
      code after the faulting load runs
  C6  probe image P2: one retry resumes the faulting instruction itself — the
      same IP faults twice (offset 0 proven, not assumed)
  C7  probe image P5: two consecutive faults leave every GPR identical between
      the frames (126 registers compared, 0 mismatches) — frame integrity
  C8  probe image P3: an unregistered CFXMEM terminates with the *monitor*
      code of supv+CFXMEM from §7.1, named, exactly once (no re-entry)
  C9  unknown image P4: a cause outside the table is named ``unknown`` and
      stops in the guest segment (it cannot be encoded as a monitor cause)

``--selfcheck`` mutates the captured output (or an image) and shows that every
check group flips.  ``--inject`` corrupts the source, rebuilds, asserts the
expected FAIL and restores with ``cp`` + md5 (never ``git checkout``).

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (spec/contract/image missing).
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

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                    # noqa: E402  (pins)
from tests.unit.linux import k1_boot_probe as k1boot        # noqa: E402  (symbols/ELF)
from tools.linux import make_defconfig as defconfig   # noqa: E402  (config slice)
from tools.linux import make_vmlinux as vmlinux       # noqa: E402  (build driver)
from tools.linux import paths as linux_paths          # noqa: E402
from tools.qemu import k0_boot_probe as k0            # noqa: E402  (firmware, run)

PROFILE = "vast"

TIMEOUT_QEMU = int(os.environ.get("K2_QEMU_TIMEOUT", "120"))
TIMEOUT_BUILD = int(os.environ.get("K2_BUILD_TIMEOUT", "3600"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K2_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-006") / "k2_trap_probe")

#: Images the gate builds.  `CONFIG_PINS` is the complete set for the plain K2
#: image (enforced by `make check-config-pins`, ISS-470) and `IMAGE_PINS` holds
#: the per-image overrides, so the shared build tree cannot leak one image's
#: configuration into another (this is the whole point of the explicit slice).
#:
#:   plain     K2 image (no self-test)                       -> SYS_EXIT(0)
#:   probe     self-test, last case = unregistered CFXMEM    -> P1..P8 + P3
#:   unknown   + cause rewritten to a reserved bit           -> P4
#:   reentry   self-test, last case = fault in the handler   -> re-entrancy guard
#:   cftrap    self-test, last case = unregistered CFXTRAP   -> "other cfx" code
#:   cfxesc    self-test, last case = escape to another cfx  -> same code
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "y",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    # int with an unmet `depends on`: "left unset" (no `n` value in Kconfig;
    # the symbol is dropped from .config) — tools/linux/config_pins.py.
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    # m14-linux-011/012 images must not leak in either (the shared build
    # tree is configured by whichever gate ran last).
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

IMAGE_PINS = {
    "probe": {"CONFIG_DADAO_K2_TRAP_SELFTEST": "y"},
    "unknown": {"CONFIG_DADAO_K2_TRAP_SELFTEST": "y",
                "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "y"},
    "reentry": {"CONFIG_DADAO_K2_TRAP_SELFTEST": "y",
                "CONFIG_DADAO_K2_SELFTEST_REENTRY": "y"},
    "cftrap": {"CONFIG_DADAO_K2_TRAP_SELFTEST": "y",
               "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "y"},
    "cfxesc": {"CONFIG_DADAO_K2_TRAP_SELFTEST": "y",
               "CONFIG_DADAO_K2_SELFTEST_CFXESC": "y"},
}

IMAGES: dict[str, list[str]] = {
    name: config_pins.config_lines(CONFIG_PINS, IMAGE_PINS.get(name))
    for name in ("plain", "probe", "unknown", "reentry", "cftrap", "cfxesc")
}

#: The images whose boot ends in the terminal case (rc is the case's verdict).
TERMINAL_IMAGES = ("probe", "reentry", "cftrap", "cfxesc")

SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
SPEC_MACHINE = _REPO / "spec" / "Kaiwu-测试机运行环境.md"
CONTRACT_SEE = _REPO / ".tao" / "contracts" / "contract-see.md"
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
        self.quiet = quiet

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        if not self.quiet:
            print(f"  [{'PASS' if ok else 'FAIL'}] {cid} {name} | "
                  f"期望={expected} 实际={actual}", flush=True)
        if not ok:
            self.fails.append(f"{cid} {name}: 期望={expected} 实际={actual}")
        return ok

    def stat(self, text: str) -> None:
        if not self.quiet:
            print(f"  [STAT] {text}", flush=True)


# ---------------------------------------------------------------------------
# expectations parsed from spec / contract (never restated)
# ---------------------------------------------------------------------------

def spec_cause_table() -> list[tuple[int, str]]:
    """The 11 ``excp_cause_id`` rows of ``spec/DADAO-12 §4.1 cfx_umon``."""
    text = SPEC_DADAO12.read_text(encoding="utf-8")
    section = text.split("### 4.1 cfx_umon", 1)
    if len(section) != 2:
        raise SystemExit("k2_trap_probe: spec/DADAO-12 §4.1 cfx_umon not found")
    body = section[1].split("\n### ", 1)[0]
    rows = re.findall(r"^\|\s*`1\s*<<\s*(\d+)`\s*\|\s*`?(\w+)`?\s*\|",
                      body, re.MULTILINE)
    table = [(1 << int(bit), name) for bit, name in rows]
    if len(table) != 11:
        raise SystemExit(f"k2_trap_probe: spec/DADAO-12 §4.1 parsed "
                         f"{len(table)} causes, expected 11: {table}")
    return table


def spec_exit_segments() -> dict:
    """The segment ranges, run-mode encoding and bit indices of §7.1."""
    text = SPEC_MACHINE.read_text(encoding="utf-8")
    section = text.split("### 7.1", 1)
    if len(section) != 2:
        raise SystemExit("k2_trap_probe: spec/Kaiwu §7.1 not found")
    body = section[1].split("\n### ", 1)[0]

    # Ranges are spelled `0x00` / `0x01`–`0x7F` / ... with the segment name in
    # the next column; parse them in table order and key them by segment
    # (`guest` appears twice: PASS, then FAIL).
    ranges: dict[str, tuple[int, int]] = {}
    for line in body.splitlines():
        m = re.match(r"^\|\s*`(?P<low>0x[0-9A-Fa-f]+)`"
                     r"(?:\s*[–-]\s*`(?P<high>0x[0-9A-Fa-f]+)`)?\s*\|\s*"
                     r"(?P<seg>[^|]+)\|", line)
        if not m:
            continue
        low = int(m.group("low"), 16)
        high = int(m.group("high"), 16) if m.group("high") else low
        seg = m.group("seg").strip()
        if seg == "guest":
            seg = "pass" if (low, high) == (0, 0) else "guest"
        elif "其它" in seg:
            seg = "other"
        ranges[seg] = (low, high)
    for required in ("pass", "guest", "other", "monitor"):
        if required not in ranges:
            raise SystemExit(f"k2_trap_probe: §7.1 has no '{required}' segment")

    modes = {}
    m = re.search(r"`bit5:4` 为运行模式——(.*?)。", body, re.DOTALL)
    if not m:
        raise SystemExit("k2_trap_probe: §7.1 run-mode encoding not found")
    for name, bits in re.findall(r"`(\w+)`\s*=\s*`(\d+)`", m.group(1)):
        modes[name] = int(bits, 2)
    if "supv" not in modes:
        raise SystemExit("k2_trap_probe: §7.1 has no supv mode encoding")

    indices = {}
    for line in body.splitlines():
        m = re.match(r"^\|\s*(?P<bit>\d+)\s*\|\s*`0x[0-9A-F]+`[–-]`0x[0-9A-F]+`"
                     r"\s*\|\s*`bit3:0=(?P<idx>\d+)`\s*\|\s*`(?P<name>\w+)`", line)
        if m:
            indices[m.group("name")] = int(m.group("idx"))
    if len(indices) != 11:
        raise SystemExit(f"k2_trap_probe: §7.1 parsed {len(indices)} bit "
                         f"indices, expected 11")
    return {"ranges": ranges, "modes": modes, "indices": indices}


def cfxha(name: str) -> int:
    """The cfxha the alias table assigns to `cfx_<name>` (contracts/)."""
    path = _REPO / "contracts" / "cfx-aliases.txt"
    wanted = {name, f"cfx_{name}"}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "scalar" and parts[1] in wanted:
            return int(parts[2], 0)
    raise SystemExit(f"k2_trap_probe: '{name}' is not a scalar in {path.name}")


def contract_escape_offsets() -> list[int]:
    """The legal ``escape`` offsets (``contract-see`` §4)."""
    text = CONTRACT_SEE.read_text(encoding="utf-8")
    m = re.search(r"`imms20` 合法值只有\s*(\d+)\s*或\s*(\d+)", text)
    if not m:
        raise SystemExit("k2_trap_probe: contract-see §4 escape offsets not found")
    return [int(m.group(1)), int(m.group(2))]


def kernel_marks() -> list[tuple[int, int, int]]:
    """The P5 register marks of kernel/k2_selftest.c: (bank, index, value)."""
    path = SOURCE / "arch/dadao/kernel/k2_selftest.c"
    if not path.is_file():
        raise SystemExit(f"k2_trap_probe: {path} missing; "
                         f"run `make fetch apply-series`")
    body = path.read_text(encoding="utf-8").split("k2_marks[] = {", 1)
    if len(body) != 2:
        raise SystemExit("k2_trap_probe: k2_selftest.c has no k2_marks[] table")
    rows = re.findall(r"\{\s*(\d+),\s*(\d+),\s*(0x[0-9a-fA-F]+)\s*\}",
                      body[1].split("};", 1)[0])
    if not rows:
        raise SystemExit("k2_trap_probe: k2_marks[] is empty")
    return [(int(bank), int(index), int(value, 0)) for bank, index, value in rows]


def kernel_selfcheck_codes() -> dict[str, int]:
    """Every self-check constant the kernel sources define.

    The guest segment (0x01-0x7f) is the kernel's own verdicts, so the scan
    covers *all* of them — including the ones traps.c owns (`K2_FAIL_*`) — and
    the caller asserts each value lies in that segment.
    """
    pat = re.compile(r"^#define\s+((?:FAIL|DADAO_TRAP_BAD_POLICY|K2_FAIL)\w*)\s+"
                     r"(0x[0-9a-fA-F]+|\d+)\s*(?:/\*|$)", re.MULTILINE)
    codes: dict[str, int] = {}
    for rel in ("arch/dadao/kernel/head.S", "arch/dadao/kernel/setup.c",
                "arch/dadao/mm/k1_pt.c", "arch/dadao/kernel/traps.c",
                "arch/dadao/include/asm/trap.h"):
        path = SOURCE / rel
        if not path.is_file():
            raise SystemExit(f"k2_trap_probe: {path} missing; "
                             f"run `make fetch apply-series`")
        for name, value in pat.findall(path.read_text(encoding="utf-8")):
            codes[f"{rel}:{name}"] = int(value, 0)
    return codes


# ---------------------------------------------------------------------------
# build / run
# ---------------------------------------------------------------------------

def config(image: str) -> int:
    """Configure @image's symbols and build it incrementally."""
    rc = defconfig.apply_config_lines(IMAGES[image])
    if rc != 0:
        print(f"k2_trap_probe: FAIL: config slice for the {image} image "
              f"rc={rc}", file=sys.stderr)
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


ROM: str | None = None


def firmware() -> str:
    global ROM
    if ROM is None:
        k0.load_contract()
        if not k0.ABI:
            raise SystemExit("k2_trap_probe: the boot contract projection is empty")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        k0.WORK = str(SCRATCH / "bootrom")
        ROM = k0.build_firmware(k0.WORK)
    return ROM


def boot(tag: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k2_trap_probe: {kernel} missing")
    rc, _blocks, err, _log = k0.run_qemu(k0.DEFAULT_QEMU, firmware(),
                                         str(kernel), f"k2_{tag}",
                                         dfilter="0x0+0x4", timeout=TIMEOUT_QEMU)
    if rc is None:
        return 124, err or ""
    return rc, err or ""


# ---------------------------------------------------------------------------
# plain image: the K2 boundary
# ---------------------------------------------------------------------------

STAGE_ANCHORS = (
    ("bootinfo", r"^K1 bootinfo magic="),
    ("stack", r"^K1 stack sp="),
    ("vector", r"^K1 ptw vec  supv_excp_vector="),
    ("table", r"^K1 ptw map  ram_pa="),
    ("install", r"^K1 ptw post ptbr="),
    ("switch", r"^K1 ptw new  va="),
    ("table-done", r"^K1 ptw done: running on the kernel-built table$"),
    ("setup_arch", r"^K2 setup_arch: memblock_add "),
    ("cause-table", r"^K2 trap causes: "),
    ("channel", r"^K2 trap: entry="),
    ("boundary", r"^K2 done: semihosting SYS_EXIT\(0\)"),
)

#: Bring-up that must NOT have happened at the K2 boundary (the boundary line
#: itself names them, so it is excluded).
NO_CLOCK = r"(clocksource|\btimer\b|\btick\b|\bIRQ\b|init_IRQ|interrupt)"


def config_text() -> str:
    return (Path(linux_paths.linux_build_dir()) / ".config").read_text(
        encoding="utf-8")


def check_plain(rc: int, text: str, rep: Report, specs: dict, table,
                snap: dict) -> None:
    # The snapshot belongs to *this* image: the build tree is shared, so the
    # .config and the symbol addresses have to be read right after its build.
    cfg = snap["config"].splitlines()
    rep.check("C1", "镜像配置：K1 停止边界未设",
              [], [line for line in cfg
                   if line.startswith("CONFIG_DADAO_K1_EARLY_STOP=")])
    rep.check("C1", "镜像配置：K2 边界开",
              "CONFIG_DADAO_K2_EARLY_STOP=y",
              next((line for line in cfg
                    if line.startswith("CONFIG_DADAO_K2_EARLY_STOP=")), "<unset>"))
    rep.check("C1", "镜像配置：K2 自检未设",
              [], [line for line in cfg
                   if line.startswith("CONFIG_DADAO_K2_TRAP_SELFTEST=")])

    codes = kernel_selfcheck_codes()
    guest = specs["ranges"].get("guest")
    if not guest:
        raise SystemExit("k2_trap_probe: §7.1 has no guest segment rows")
    # The FAIL row is the second guest row (0x01-0x7f, value = check point).
    fail_low, fail_high = specs["ranges"]["guest"]
    out_of_segment = {name: value for name, value in codes.items()
                      if not (fail_low <= value <= fail_high)}
    rep.check("C1", f"自检码全在 guest FAIL 段 "
                    f"({hex(fail_low)}-{hex(fail_high)})", {}, out_of_segment)
    rep.check("C1", "静态扫描覆盖 traps.c 的自检点（K2_FAIL_*）", True,
              any("traps.c" in name for name in codes))
    rep.stat(f"自检码 {len(codes)} 条："
             + " ".join(f"{name.split(':')[-1]}={hex(v)}"
                        for name, v in sorted(codes.items())))

    rep.check("C2", "plain 镜像 guest rc（SYS_EXIT 子码）", 0, rc)
    lines = [line for line in text.splitlines() if line.strip()]
    rep.check("C2", "K2 边界是输出的最后一行", True,
              bool(lines) and lines[-1].startswith("K2 done: semihosting SYS_EXIT(0)"))

    order: list[tuple[str, int]] = []
    for stage, pattern in STAGE_ANCHORS:
        hits = [i for i, line in enumerate(text.splitlines())
                if re.match(pattern, line)]
        rep.check("C2", f"阶段 {stage} 出现 1 次", 1, len(hits))
        if hits:
            order.append((stage, hits[0]))
    rep.check("C2", "阶段顺序 = 常量表顺序",
              [stage for stage, _ in STAGE_ANCHORS], [stage for stage, _ in order])
    rep.check("C2", "阶段行号严格递增", True,
              all(a[1] < b[1] for a, b in zip(order, order[1:])))
    body = [line for line in lines if not line.startswith("K2 done: semihosting")]
    rep.check("C2", "K2 边界前无时钟/定时器/中断 bring-up", [], [
        line for line in body if re.search(NO_CLOCK, line)])
    rep.check("C2", "无机器具名 fault（plain 镜像不应取异常）", [],
              [line for line in body if line.startswith("dadao: ")])

    # C3: the table the dispatcher matched on IS the spec table.
    m = re.search(r"^K2 trap causes: n=(\d+)(.*)$", text, re.MULTILINE)
    if not m:
        rep.check("C3", "cause 表行存在", "存在", "缺失")
        return
    printed = re.findall(r"(\w+)=(0x[0-9a-fA-F]+)", m.group(2))
    rep.check("C3", "cause 表条目数 == spec/DADAO-12 §4.1", len(table),
              int(m.group(1)))
    rep.check("C3", "cause 名字/编号逐项 == spec/DADAO-12 §4.1",
              [(name, hex(cid)) for cid, name in table],
              [(name, cid) for name, cid in printed])

    # C4: the vector the kernel installed is its own entry, and the offsets it
    # may escape with are the contract's two.
    m = re.search(r"^K1 ptw vec  supv_excp_vector=(\S+) handler=(\S+)$", text,
                  re.MULTILINE)
    syms = snap["syms"]
    if not m:
        rep.check("C4", "向量安装行存在", "存在", "缺失")
    else:
        rep.check("C4", "supv_excp_vector == dadao_supv_excp 符号",
                  hex(syms["dadao_supv_excp"]), m.group(1))
        rep.check("C4", "读回值 == 写入值", m.group(1), m.group(2))
    offsets = contract_escape_offsets()
    m = re.search(r"escape=\{([^}]*)\}", text)
    rep.check("C4", "stub 声明的 escape 偏移 == 契约的两个", offsets,
              [int(v) for v in m.group(1).split(",")] if m else "<missing>")
    rep.check("C4", "静态帧是 .bss 里的 pt_regs（帧符号存在）", True,
              "dadao_excp_save" in syms)


# ---------------------------------------------------------------------------
# probe image: P1 / P2 / P5 / P3
# ---------------------------------------------------------------------------

def probe_lines(text: str) -> dict:
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^K2 probe (P\d): (.*)$", line)
        if m:
            out.setdefault(m.group(1), m.group(2))
    return out


def hits(text: str, tag: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = re.match(r"^K2 probe: cause=(\w+) va=(\S+) ip=(\S+) info=(\S+) "
                     r"hit=(\d+)$", line)
        if m:
            rows.append({"cause": m.group(1), "va": m.group(2), "ip": m.group(3),
                         "info": m.group(4), "hit": int(m.group(5))})
    return rows


def fatal_lines(text: str) -> list[str]:
    """Every fatal `dadao: ... cause=...` line, whatever the reason string is.

    The re-entrancy report (`recursive supv exception`) has to be counted here:
    a check that only matches `unrecoverable`/`unclassifiable` cannot see a
    second entry into the handler.
    """
    return re.findall(r"^dadao: .*? cause=\w+\(0x[0-9a-f]+\) .*$", text,
                      re.MULTILINE)


def die_line(text: str) -> dict | None:
    m = re.search(r"^dadao: .*? cause=(\w+)\((0x[0-9a-f]+)\) ip=(\S+) "
                  r"info=(\S+) ptbr=(\S+) sp=(\S+)$", text, re.MULTILINE)
    if not m:
        return None
    return {"cause": m.group(1), "id": m.group(2), "ip": m.group(3),
            "info": m.group(4), "ptbr": m.group(5), "sp": m.group(6)}


def check_probe(rc: int, text: str, rep: Report, specs: dict) -> None:
    pl = probe_lines(text)
    rows = hits(text, "probe")
    probe_va = None
    m = re.search(r"^K2 selftest: probe_va=(\S+) ", text, re.MULTILINE)
    if m:
        probe_va = m.group(1)
    rep.check("C5", "自检报告探针 VA", True, probe_va is not None)

    # P1: classified and skipped.
    p1 = pl.get("P1", "")
    rep.check("C5", "P1 探针被分类（cause 名打印）", True,
              any(r["cause"] == "CFXMEM" and r["info"] == probe_va for r in rows))
    rep.check("C5", "P1 命中 1 次、按 +4 续跑、后续标记存在", "hits=1 resumed=yes",
              " ".join(p1.split()[:2]))
    rep.check("C5", "P1 标记值（续跑后执行到的常量）", "marker=0x5031",
              next((tok for tok in p1.split() if tok.startswith("marker=")), "?"))

    # P2: one retry, then skip — the same instruction faulted twice.
    p2 = pl.get("P2", "")
    rep.check("C6", "P2 同一指令两次进入（escape +0 生效）", "same_ip=yes",
              next((tok for tok in p2.split() if tok.startswith("same_ip=")), "?"))
    rep.check("C6", "P2 命中次数", "hits=2",
              next((tok for tok in p2.split() if tok.startswith("hits=")), "?"))
    ips = re.search(r"ip1=(\S+) ip2=(\S+)", p2)
    rep.check("C6", "P2 两次 fault 的 ip 相同", True,
              bool(ips) and ips.group(1) == ips.group(2))

    # P5: frame integrity.
    p5 = pl.get("P5", "")
    rep.check("C7", "P5 两次 fault 都取到帧", "frames=2",
              next((tok for tok in p5.split() if tok.startswith("frames=")), "?"))
    rep.check("C7", "P5 逐寄存器比对（rd1-rd63 + rb1-rb63）", "gpr_cmp=126",
              next((tok for tok in p5.split() if tok.startswith("gpr_cmp=")), "?"))
    rep.check("C7", "P5 标记寄存器也在帧内比对", f"marked={len(kernel_marks())}",
              next((tok for tok in p5.split() if tok.startswith("marked=")), "?"))
    rep.check("C7", "P5 帧差异（保存/恢复前后必须逐一相等）", "mismatches=0",
              next((tok for tok in p5.split() if tok.startswith("mismatches=")), "?"))

    # P6: CFXTRAP is a table entry that can be dispatched (probe covers it).
    p6 = pl.get("P6", "")
    rep.check("C10", "P6 supv `trap cfx_smon` 被分类为 CFXTRAP", "cause=CFXTRAP",
              " ".join(p6.split()[:1]))
    rep.check("C10", "P6 命中 1 次后按 +4 续跑（服务返回）", "hits=1 resumed=yes",
              " ".join(p6.split()[1:3]))
    rep.check("C10", "P6 续跑后的标记", "marker=0x5036",
              next((tok for tok in p6.split() if tok.startswith("marker=")), "?"))

    # P7: the two exit-code branches, asserted without dying.
    p7 = pl.get("P7", "")
    codes = {tok.split("=")[0]: tok.split("=")[1]
             for tok in p7.split() if "=" in tok}
    rep.check("C11", "P7 预测行存在", True, bool(codes))
    smon = cfxha("smon")
    rep.check("C11", f"CFXTRAP 走「其它 cfx」段 0x80|cfxHA(cfx_smon={smon})",
              hex(0x80 | smon), codes.get("trap", "?"))
    rep.check("C11", "CFXESC 走同一段", hex(0x80 | smon), codes.get("esc", "?"))
    rep.check("C11", "CFXMEM 走 monitor 段 supv+bit1",
              hex(_monitor_code(specs, "supv", "CFXMEM")), codes.get("cfxmem", "?"))
    rep.check("C11", "ILLI 走 monitor 段 supv+bit8",
              hex(_monitor_code(specs, "supv", "ILLI")), codes.get("illi", "?"))

    # P8: the handler's cg5 rc3 write decides where `escape …, 0` lands.
    p8 = pl.get("P8", "")
    rep.check("C12", "P8 handler 改写 cg5 rc3 后落在新 ip", "landed=yes",
              next((tok for tok in p8.split() if tok.startswith("landed=")), "?"))
    rep.check("C12", "P8 新 ip 上留下的标记", "marker=0x600d",
              next((tok for tok in p8.split() if tok.startswith("marker=")), "?"))
    rep.check("C12", "P8 未走「跳过错页」的老路径（landed=no 不出现）", [],
              re.findall(r"^K2 probe P8: landed=no.*$", text, re.MULTILINE))

    # P3: unregistered fault terminates with the monitor code of supv+CFXMEM.
    rc_expect = _monitor_code(specs, "supv", "CFXMEM")
    rep.check("C8", "P3 未注册的 CFXMEM 被具名终止（退出码）", rc_expect, rc)
    die = die_line(text)
    if die is None:
        rep.check("C8", "P3 终止行存在", "存在", "缺失")
        return
    rep.check("C8", "P3 原因名", "CFXMEM", die["cause"])
    rep.check("C8", "P3 原因编号", hex(1 << specs["indices"]["CFXMEM"]),
              die["id"])
    rep.check("C8", "P3 info == 自检的探针 VA", probe_va, die["info"])
    rep.check("C8", "P3 不重复进入（终止行总数 == 1，含 recursive 行）", 1,
              len(fatal_lines(text)))
    rep.check("C8", "P3 未续跑（FAIL resumed 行不存在）", [],
              re.findall(r"^K2 probe P3: FAIL.*$", text, re.MULTILINE))
    seg = specs["ranges"]["monitor"]
    rep.check("C8", "P3 退出码落在 monitor 段", True, seg[0] <= rc <= seg[1])


def _monitor_code(specs: dict, mode: str, cause: str) -> int:
    """``0xC0 | (mode << 4) | bit index`` — straight from §7.1."""
    seg_low, _seg_high = specs["ranges"]["monitor"]
    return seg_low | (specs["modes"][mode] << 4) | specs["indices"][cause]


# ---------------------------------------------------------------------------
# unknown image: P4
# ---------------------------------------------------------------------------

def check_unknown(rc: int, text: str, rep: Report, specs: dict) -> None:
    rep.check("C9", "P4 打印 unknown cause 行（保留原始 cause）", True,
              bool(re.search(r"^dadao: unknown cause=0x[0-9a-f]+ "
                             r"\(not in the 11-item table\)$", text, re.MULTILINE)))
    unknown = re.search(r"^dadao: unknown cause=(0x[0-9a-f]+)", text, re.MULTILINE)
    table = {cid for cid, _name in spec_cause_table()}
    value = int(unknown.group(1), 16) if unknown else 0
    rep.check("C9", "P4 注入的 cause 不在 11 项表内（现场核对）", True,
              value not in table and value != 0)
    # The ruling: an unclassifiable cause is an *abnormal termination*, so it
    # lands in the monitor segment (never in the guest FAIL segment, where it
    # would be indistinguishable from a self-check check point).  The bit index
    # is derived mechanically from the one-hot id.
    seg_low, seg_high = specs["ranges"]["monitor"]
    index = (value & -value).bit_length() - 1 if value else 0
    expect = seg_low | (specs["modes"]["supv"] << 4) | (index & 0xF)
    rep.check("C9", "P4 退出码 ∈ monitor 段（异常终止）", True,
              seg_low <= rc <= seg_high)
    rep.check("C9", "P4 退出码 == 0xC0|supv<<4|(__ffs(cause)&0xF)", hex(expect),
              hex(rc))
    fail_low, fail_high = specs["ranges"]["guest"]
    rep.check("C9", "P4 未落 guest FAIL 段（与自检点可区分）", False,
              fail_low <= rc <= fail_high)


# ---------------------------------------------------------------------------
# terminal images: the caps of the channel (re-entrancy, "other cfx" codes)
# ---------------------------------------------------------------------------

def check_reentry(rc: int, text: str, rep: Report, specs: dict) -> None:
    """A fault *inside* the handler must hit the guard, not the dispatcher."""
    fatal = fatal_lines(text)
    rep.check("C13", "reentry 镜像跑到尾例", True,
              "K2 probe P9: first fault" in text)
    rep.check("C13", "重入被具名拦下（recursive supv exception）", True,
              any("recursive supv exception" in line for line in fatal))
    rep.check("C13", "重入按自检点 0x0e 终止", 0x0e, rc)
    rep.check("C13", "终止行总数 == 1（二次进入未被当普通异常再分派）", 1,
              len(fatal))
    rep.check("C13", "未被续跑（P9 FAIL 行不出现）", [],
              re.findall(r"^K2 probe P9: FAIL.*$", text, re.MULTILINE))


def check_cfx_branch(image: str, say: str, cause: str, rc: int, text: str,
                     rep: Report, specs: dict) -> None:
    """CFXTRAP / CFXESC terminate in the ``0x80 | cfxHA`` segment (§7.1)."""
    fatal = fatal_lines(text)
    expect = specs["ranges"]["other"][0] | cfxha("smon")
    rep.check("C14", f"{image} 镜像跑到尾例", True, say in text)
    rep.check("C14", f"{image} 具名终止（{cause}）", True,
              any(f"cause={cause}(" in line for line in fatal))
    rep.check("C14", f"{image} 退出码 == 0x80|cfxHA(cfx_smon) — 其它 cfx 段",
              hex(expect), hex(rc))
    seg_low, seg_high = specs["ranges"]["other"]
    rep.check("C14", f"{image} 退出码落在其它 cfx 段", True,
              seg_low <= rc <= seg_high)
    rep.check("C14", f"{image} 不落 monitor 段（不是位索引编码）", False,
              specs["ranges"]["monitor"][0] <= rc <= specs["ranges"]["monitor"][1])
    rep.check("C14", f"{image} 终止行总数 == 1", 1, len(fatal))


def check_image(image: str, rc: int, text: str, rep: Report, specs: dict,
                table, snap: dict | None = None) -> None:
    """Run the checks that belong to @image's boot."""
    if image == "plain":
        check_plain(rc, text, rep, specs, table, snap)
    elif image == "probe":
        check_probe(rc, text, rep, specs)
    elif image == "unknown":
        check_unknown(rc, text, rep, specs)
    elif image == "reentry":
        check_reentry(rc, text, rep, specs)
    elif image == "cftrap":
        check_cfx_branch("cftrap", "K2 probe P10: unregistered CFXTRAP",
                         "CFXTRAP", rc, text, rep, specs)
    elif image == "cfxesc":
        check_cfx_branch("cfxesc", "K2 probe P11: escape to cfx_umon",
                         "CFXESC", rc, text, rep, specs)
    else:
        raise SystemExit(f"k2_trap_probe: no checks for image {image!r}")


# ---------------------------------------------------------------------------
# gate driver
# ---------------------------------------------------------------------------

def run_gate(rep: Report, *, build_images: bool = True) -> dict:
    specs = spec_exit_segments()
    table = spec_cause_table()
    result: dict = {"runs": {}, "plain": None}

    for image in IMAGES:
        if build_images:
            rc = config(image)
            rep.check("C0", f"{image} 镜像可构建", 0, rc)
            if rc != 0:
                return result
        # Snapshot what belongs to *this* image before the next build replaces
        # it: the .config and the symbol addresses.
        snap = {"config": config_text(),
                "syms": k1boot.symbols(kernel_path())}
        rc, text = boot(image)
        result["runs"][image] = (rc, text)
        if image == "plain":
            result["plain"] = snap
        if not rep.quiet:
            print(f"---- guest output ({image}, rc={rc}) ----")
            print(text.strip())
            print("----------------------------------------")

    outputs = result["runs"]
    rc, text = outputs["plain"]
    check_plain(rc, text, rep, specs, table, result["plain"])
    rc, text = outputs["probe"]
    check_probe(rc, text, rep, specs)
    rc, text = outputs["unknown"]
    check_unknown(rc, text, rep, specs)
    rc, text = outputs["reentry"]
    check_reentry(rc, text, rep, specs)
    rc, text = outputs["cftrap"]
    check_cfx_branch("cftrap", "K2 probe P10: unregistered CFXTRAP", "CFXTRAP",
                     rc, text, rep, specs)
    rc, text = outputs["cfxesc"]
    check_cfx_branch("cfxesc", "K2 probe P11: escape to cfx_umon", "CFXESC",
                     rc, text, rep, specs)
    return result


# ---------------------------------------------------------------------------
# --selfcheck: every group must be able to fail
# ---------------------------------------------------------------------------

#: Mutations applied to the captured *plain* run; each perturbs one group.
PLAIN_MUTATIONS = {
    "C2": (r"^K2 setup_arch: memblock_add .*\n", ""),
    "C3": (r"^K2 trap causes: n=11 CFXTRAP=0x1 CFXMEM=0x2",
           "K2 trap causes: n=10 CFXTRAP=0x1 CFXMEM=0x4"),
    "C4": (r"(^K1 ptw vec  supv_excp_vector=\S+ handler=)\S+$",
           r"\g<1>0x0"),
}

PROBE_MUTATIONS = {
    "C5": (r"^K2 probe P1: hits=1 resumed=yes", "K2 probe P1: hits=0 resumed=no"),
    "C6": (r"same_ip=yes", "same_ip=no"),
    "C7": (r"mismatches=0", "mismatches=3"),
    "C10": (r"^K2 probe P6: cause=CFXTRAP", "K2 probe P6: cause=UNKNOWN"),
    "C11": (r"trap=0x82 esc=0x82", "trap=0xe0 esc=0xe0"),
    "C12": (r"^K2 probe P8: landed=yes marker=0x600d",
            "K2 probe P8: landed=no marker=0xbad"),
}

REENTRY_MUTATIONS = {
    "C13": (r"^dadao: recursive supv exception cause=",
            "dadao: unrecoverable supv exception cause="),
}

UNKNOWN_MUTATIONS = {
    "C9": (r"^dadao: unknown cause=\S+ .*\n", ""),
}


def run_selfcheck(result: dict) -> int:
    specs = spec_exit_segments()
    table = spec_cause_table()
    outputs = result["runs"]
    snap = result["plain"]
    bad = 0

    def flipped(cid: str, fn) -> None:
        nonlocal bad
        rep = Report(quiet=True)
        with contextlib.redirect_stdout(io.StringIO()):
            fn(rep)
        hit = [msg for msg in rep.fails if msg.startswith(cid)]
        print(f"  [{'PASS' if hit else 'FAIL'}] selfcheck {cid} 注入后判定翻转 | "
              f"期望=该组 FAIL 实际={hit[0] if hit else '未翻转'}", flush=True)
        bad += 0 if hit else 1

    prc, ptext = outputs["probe"]
    urc, utext = outputs["unknown"]
    rrc, rtext = outputs["reentry"]
    crc, ctext = outputs["cftrap"]
    erc, etext = outputs["cfxesc"]
    rc, text = outputs["plain"]

    # Baseline: the captured runs must be green before anything is mutated,
    # otherwise "the group flipped" would prove nothing.
    base = Report(quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        check_plain(rc, text, base, specs, table, snap)
        check_probe(prc, ptext, base, specs)
        check_unknown(urc, utext, base, specs)
        check_reentry(rrc, rtext, base, specs)
        check_cfx_branch("cftrap", "K2 probe P10: unregistered CFXTRAP",
                         "CFXTRAP", crc, ctext, base, specs)
        check_cfx_branch("cfxesc", "K2 probe P11: escape to cfx_umon",
                         "CFXESC", erc, etext, base, specs)
    print(f"  [{'PASS' if not base.fails else 'FAIL'}] selfcheck 基准三镜像全绿 | "
          f"期望=0 失败 实际={len(base.fails)} 失败", flush=True)
    bad += 0 if not base.fails else 1

    # Every group, mutated on the evidence it actually reads.
    for cid, (pattern, repl) in PLAIN_MUTATIONS.items():
        mutated = re.sub(pattern, repl, text, count=1, flags=re.MULTILINE)
        if mutated == text:
            print(f"  [FAIL] selfcheck {cid} 注入点未命中", flush=True)
            bad += 1
            continue
        flipped(cid, lambda rep, m=mutated: check_plain(rc, m, rep, specs, table,
                                                       snap))

    # C1 reads the image configuration and the source constants.
    real = kernel_selfcheck_codes()

    def c1_mutated(rep: Report) -> None:
        saved = globals()["kernel_selfcheck_codes"]
        try:
            globals()["kernel_selfcheck_codes"] = lambda: {
                **real, "arch/dadao/kernel/head.S:FAIL_MAGIC": 0xE1}
            check_plain(rc, text, rep, specs, table, snap)
        finally:
            globals()["kernel_selfcheck_codes"] = saved

    flipped("C1", c1_mutated)

    for cid, (pattern, repl) in PROBE_MUTATIONS.items():
        mutated = re.sub(pattern, repl, ptext, count=1, flags=re.MULTILINE)
        if mutated == ptext:
            print(f"  [FAIL] selfcheck {cid} 注入点未命中", flush=True)
            bad += 1
            continue
        flipped(cid, lambda rep, m=mutated: check_probe(prc, m, rep, specs))
    flipped("C8", lambda rep: check_probe(prc + 1, ptext, rep, specs))

    for cid, (pattern, repl) in UNKNOWN_MUTATIONS.items():
        mutated = re.sub(pattern, repl, utext, count=1, flags=re.MULTILINE)
        if mutated == utext:
            print(f"  [FAIL] selfcheck {cid} 注入点未命中", flush=True)
            bad += 1
            continue
        flipped(cid, lambda rep, m=mutated: check_unknown(urc, m, rep, specs))

    for cid, (pattern, repl) in REENTRY_MUTATIONS.items():
        mutated = re.sub(pattern, repl, rtext, count=1, flags=re.MULTILINE)
        if mutated == rtext:
            print(f"  [FAIL] selfcheck {cid} 注入点未命中", flush=True)
            bad += 1
            continue
        flipped(cid, lambda rep, m=mutated: check_reentry(rrc, m, rep, specs))
    flipped("C13",
            lambda rep: check_reentry(0x00, rtext, rep, specs))
    flipped("C14", lambda rep: check_cfx_branch(
        "cftrap", "K2 probe P10: unregistered CFXTRAP", "CFXTRAP", 0xE0,
        ctext, rep, specs))
    flipped("C14", lambda rep: check_cfx_branch(
        "cfxesc", "K2 probe P11: escape to cfx_umon", "CFXESC", crc,
        etext.replace("cause=CFXESC", "cause=CFXTRAP"), rep, specs))

    groups = 1 + len(PLAIN_MUTATIONS) + 1 + len(PROBE_MUTATIONS) + 1 + \
        len(UNKNOWN_MUTATIONS) + len(REENTRY_MUTATIONS) + 2
    print(f"k2_trap_probe: selfcheck {'PASS' if not bad else 'FAIL'} "
          f"({groups - bad}/{groups} 组可翻转)")
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# --inject: real corruptions, rebuilt and restored (cp + md5)
# ---------------------------------------------------------------------------

TRAP_S = "arch/dadao/kernel/trap.S"
TRAPS_C = "arch/dadao/kernel/traps.c"
SETUP_C = "arch/dadao/kernel/setup.c"
HEAD_S = "arch/dadao/kernel/head.S"

#: name -> (image, relative source, exact text, replacement, expected rc,
#:          expected line regex, forbidden line regex, check ids that must flip)
INJECTIONS = {
    # ① The entry stops saving one bank: rd32-rd63 keep whatever the stub left
    #    in them, so the two frames of P5 differ.
    "save-half-rd": (
        "probe", TRAP_S,
        "\tstm.o\t{rd4:rd63}, [rb3, rd2]\t\t/* frame.rd[4..63] */\n",
        "\tstm.o\t{rd4:rd31}, [rb3, rd2]\t\t/* frame.rd[4..63] */\n",
        0xE1,                     # P3 still terminates, but only after P5 fails
        r"^K2 probe P5: frames=2 .*mismatches=[1-9]",
        r"^K2 probe P5: .*mismatches=0",
        ("C7",),
    ),
    # ② "Any CFXMEM is resumable": the probe match drops the registration
    #    check, so P3's unregistered fault no longer terminates (it "resumes"
    #    instead and the selftest reports the impossible outcome by name).
    "allow-any-cfxmem": (
        "probe", TRAPS_C,
        "\tif (!dadao_probe || dadao_probe->cause != cause)\n"
        "\t\treturn NULL;\n",
        "\tif (!dadao_probe) {\n"
        "\t\tstatic struct dadao_fault_probe any;\n\n"
        "\t\tany.cause = DADAO_CAUSE_CFXMEM;\n"
        "\t\treturn cause == any.cause ? &any : NULL;\n"
        "\t}\n"
        "\tif (dadao_probe->cause != cause)\n"
        "\t\treturn NULL;\n",
        0x7f,                     # the selftest notices and reports 0x7f
        r"^K2 probe P3: FAIL resumed an unregistered fault$",
        r"^dadao: unrecoverable supv exception",
        ("C8",),
    ),
    # ③ escape +4 becomes +0: the skip path re-executes the faulting load, so
    #    P1 never gets past it (the probe's hit budget reports it by name).
    "escape-offset-zero": (
        "probe", TRAP_S,
        ".Lresume_skip:\n\tDADAO_TRAP_RESTORE_AND_ESCAPE 4\n",
        ".Lresume_skip:\n\tDADAO_TRAP_RESTORE_AND_ESCAPE 0\n",
        0x0f,                     # probe hit budget exhausted -> self-check
        r"^dadao: fault probe hit too often cause=CFXMEM",
        r"^K2 probe P1: hits=1 resumed=yes",
        ("C5",),
    ),
    # ⑤ The handler stops writing cg5 rc3: `escape …, 0` then returns to the
    #    faulting instruction, so P8 never lands on the redirected ip (the probe
    #    budget ends the boot instead).
    "drop-rc3-write": (
        "probe", TRAPS_C,
        "\t\t\tDADAO_CFX_WRITE(cfx_smon, SMON_CG_FRAME,\n"
        "\t\t\t\t\tSMON_RC_FRAME_CAUSE_IP, probe->redirect);\n",
        "\t\t\t/* injected: no cg5 rc3 write */\n",
        0x0f,                     # probe budget -> self-check point 0x0f
        r"^dadao: fault probe hit too often cause=CFXMEM",
        r"^K2 probe P8: landed=yes",
        ("C12",),
    ),
    # ⑥ The re-entrancy guard is gone: the second exception is dispatched again,
    #    so the boot ends in the probe budget instead of the recursive report.
    "drop-busy-guard": (
        "reentry", TRAPS_C,
        "\tif (dadao_trap_busy)\n",
        "\tif (0 && dadao_trap_busy)\n",
        0x0f,                     # -> "fault probe hit too often" (0x0f)
        r"^dadao: fault probe hit too often cause=CFXMEM",
        r"recursive supv exception",
        ("C13",),
    ),
    # ④ A self-check code back in the monitor segment: §7.1 reads it as a supv
    #    synchronous exception instead of a boot check point.
    "selfcheck-in-monitor-segment": (
        "plain", HEAD_S,
        "#define FAIL_MAGIC\t0x01",
        "#define FAIL_MAGIC\t0xE1",
        0,                        # the plain image still boots ...
        r"^K2 done: semihosting SYS_EXIT\(0\)",
        r"^dadao: ",              # ... but the static segmentation check fails
        ("C1",),
    ),
}


def run_inject(name: str, problems: list[str]) -> None:
    image, rel, old, new, want_rc, want_re, forbid, want_cids = INJECTIONS[name]
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
        rc_build = config(image)
        if rc_build != 0:
            problems.append(f"inject:{name}: 重建 rc={rc_build}")
        else:
            snap = {"config": config_text(),
                    "syms": k1boot.symbols(kernel_path())}
            specs = spec_exit_segments()
            table = spec_cause_table()
            rc, text = boot(f"inject_{name}")
            print(f"---- guest output ({name}, rc={rc}) ----")
            print(text.strip()[-4000:])
            print("----------------------------------------")
            checks = [("退出码", rc == want_rc, hex(want_rc), hex(rc)),
                      ("具名行", bool(re.search(want_re, text, re.MULTILINE)),
                       want_re, "命中" if re.search(want_re, text, re.MULTILINE)
                       else "<none>")]
            if forbid is not None:
                absent = not re.search(forbid, text, re.MULTILINE)
                checks.append(("禁止行", absent, f"无 {forbid}",
                               "无" if absent else "有"))
            rep = Report(quiet=True)
            with contextlib.redirect_stdout(io.StringIO()):
                check_image(image, rc, text, rep, specs, table, snap)
            for cid in want_cids:
                red = [msg for msg in rep.fails if msg.startswith(cid)]
                checks.append((f"断言 {cid} 变红", bool(red), f"{cid} 出现 FAIL",
                               red[0] if red else "未变红"))
            for label, ok, expected, actual in checks:
                print(f"  [{'PASS' if ok else 'FAIL'}] inject:{name} {label} | "
                      f"期望={expected} 实际={actual}", flush=True)
                if not ok:
                    problems.append(f"inject:{name}: {label}（期望 {expected}，"
                                    f"实际 {actual}）")
    except Exception as exc:            # restore below even if the run blew up
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

    rc_build = config(image)
    if rc_build != 0:
        problems.append(f"inject:{name}: 还原后重建 rc={rc_build}")
        return
    snap = {"config": config_text(), "syms": k1boot.symbols(kernel_path())}
    specs = spec_exit_segments()
    table = spec_cause_table()
    rep = Report(quiet=True)
    rc, text = boot(f"inject_{name}_green")
    with contextlib.redirect_stdout(io.StringIO()):
        check_image(image, rc, text, rep, specs, table, snap)
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
                    help="four source injections: rebuild, assert FAIL, restore")
    ap.add_argument("--no-build", action="store_true",
                    help="assert only; reuse the images in the build tree")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(["gate", "selfcheck"] +
                        [f"inject:{name}" for name in INJECTIONS]))
        return 0

    if not k0.DEFAULT_QEMU or not Path(k0.DEFAULT_QEMU).is_file():
        print(f"k2_trap_probe: FAIL: {k0.DEFAULT_QEMU} missing; "
              f"run `make install-host`", file=sys.stderr)
        return 1
    if not Path(kernel_path()).parent.is_dir():
        print("k2_trap_probe: FAIL: the kernel build tree is missing; "
              "run `make linux-defconfig`", file=sys.stderr)
        return 2

    specs = spec_exit_segments()
    table = spec_cause_table()
    plain_code = _monitor_code(specs, "supv", "CFXMEM")
    print(f"k2: qemu={k0.DEFAULT_QEMU} md5={md5(Path(k0.DEFAULT_QEMU))[:8]}")
    print(f"k2: spec/DADAO-12 §4.1 causes={len(table)} "
          f"spec/Kaiwu §7.1 supv={specs['modes']['supv']:02b}b "
          f"CFXMEM index={specs['indices']['CFXMEM']} "
          f"=> supv+CFXMEM exit code {hex(plain_code)}")
    # The task book's ruling quotes 0xD0|bit for supv, which §7.1 assigns to
    # jail; the gate follows the spec (and the ruling's own formula).  Say so
    # where the verdict is made instead of leaving it to the reader.
    print(f"k2: [STAT] §7.1 运行模式编码: "
          + " ".join(f"{name}={bits:02b}b" for name, bits in
                     sorted(specs["modes"].items()))
          + f" ⇒ supv 段基址 {hex(specs['ranges']['monitor'][0] | (specs['modes']['supv'] << 4))}"
          + "（任务书示例 0xD0|bit 与 §7.1 冲突，见任务书待裁定 4）")

    rep = Report()
    result = run_gate(rep, build_images=not args.no_build)
    if not result["runs"]:
        print("k2_trap_probe: FAIL: no image could be built", file=sys.stderr)
        return 2

    if args.selfcheck:
        return run_selfcheck(result)

    if not rep.fails:
        print(f"k2_trap_probe: PASS ({rep.total}/{rep.total})")
    else:
        print(f"k2_trap_probe: FAIL ({rep.total - len(rep.fails)}/{rep.total}); "
              f"{len(rep.fails)} 项失败")
        for failure in rep.fails:
            print("  - " + failure)

    if args.inject:
        if rep.fails:
            print("k2_trap_probe: 基线不绿，先修基线再做注入")
            return 1
        problems: list[str] = []
        for name in INJECTIONS:
            run_inject(name, problems)
        total = len(INJECTIONS)
        print(f"k2_trap_probe --inject: "
              f"{'PASS' if not problems else 'FAIL'} "
              f"({total}/{total} 路注入按预期变红并还原)" if not problems else
              f"k2_trap_probe --inject: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        if problems:
            return 1

    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
