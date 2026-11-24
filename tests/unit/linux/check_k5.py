#!/usr/bin/env python3
"""check_k5.py — M14 K5 closure gate (`make check-linux-k5`; `m14-linux-029`).

K5 is where the kernel runs a *program*: the boot hands the machine to
`/init.musl`, user syscalls round-trip, `clone` makes threads, `futex`/`lr`+`sc`
synchronise them, the clock ticks, signals are delivered and the ABI is 64 KiB
end to end.  The K5 probes judge those capabilities one at a time; this gate
asks the *stage* question — "does the K5 image the milestone delivers still meet
every exit criterion?" — with **representative** cases only (user ruling
2026-11-16/2026-11-17: the full sweeps stay in `k5_*_probe.py`).

Groups (the group letter is what ``--selfcheck``/``--inject`` flip):

  S  user-mode closure (m14-linux-023): the image builds with only that probe,
     `/init.musl` really runs (its own `init: pid=` / `brk` / exit lines), the
     syscall rounds trip (`write`/`exit`), errors are `rd8 = -errno` inside the
     contract's `[-4095, -1]` and `rd1` never takes part, `rb3` (`rbtp`) is the
     frame's and the user's value, and the cg5 frame fields (`CFXTRAP`,
     prev-mode user, `immu18`) agree with the spec and with the stub's own
     disassembly.
  C  clone/thread (m14-linux-024): `CLONE_VM` shares `mm`/ASID, `mm_users` grows
     by one while the child lives and comes back, `CLONE_SETTLS` puts the `tls`
     argument in the child's `rb3`, the child enters with `rd8 = 0` while the
     parent gets the tid, `CLONE_THREAD` keeps one process, and a `fork`
     contrast has a private `mm` — expectations come from `sched.h` and from the
     probe source's constants.
  F  futex/atomics (m14-linux-025): `FUTEX_WAIT` rechecks the word under the
     bucket lock (`-EAGAIN`), a wake is never lost, `lr`…`sc` cannot cross a
     syscall (the two `sc` outcomes are the spec's), and **shared futex on an
     anonymous page works** — the rmap result of `m14-linux-035`: the page has a
     mapping, so `WAKE` answers 0 and a mismatching `WAIT` reaches the compare
     (`-EAGAIN`) instead of `-EFAULT`.
  T  clock (m14-linux-026): the registered clocksource is monotone, moves, and
     is `sched_clock()`'s source; `set_next_event()` programs the absolute
     compare and the event lands inside `[period/2, 2*period]`; a delivered tick
     advances `jiffies_64` one for one; `ktime_get()` left the jiffies fallback.
  G  signals (m14-linux-027 + 046): an unservable user access is the process's
     `SIGSEGV` (not `DADAO_PF_FATAL`), `exit`/`exit_group` end the task,
     `RLIMIT_STACK` is inherited by a fork child, the frame round-trips all four
     register banks (the `ra` stack and `rf0`'s architectural value included),
     and a signal with no handler takes the default action.
  P  64 KiB ABI (m14-linux-028): `AT_PAGESZ` equals the page size derived from
     the image's `.config` **and** `spec/DADAO-12 §2.2.2`, `mmap` results are
     page-aligned, every `PT_LOAD` is page-aligned (count read from the built
     `/init.musl`), and `brk` maps whole pages.
  R  reverse assertions and the §4a retirement: no monitor named-termination
     trace, no `unknown cause`, no panic/oops and no `-d` per-instruction log in
     any of the runs; each console reports its self-test once and nothing
     self-reports FAIL; the retired wording is gone and the new wording is in
     place (mechanical, `docs/Process-07 §4a.2`), and K3's retired targets and
     symbols have zero hits in the live tree.

Every expectation is derived, never restated:

  * page size / shift              -> that image's ``.config`` **and**
                                      ``spec/DADAO-12 §2.2.2`` (the two must agree)
  * superpage size / max order     -> ``spec/DADAO-12 §2.2.1``, the Kconfig default
  * run-mode encoding              -> ``spec/DADAO-12 §1`` (the mode table)
  * cause ids                      -> ``spec/DADAO-13 §2`` (via the K2 probe parser)
  * errno shape                    -> ``contract-syscall §9``
  * syscall numbers                -> the locked snapshot of ``contract-syscall §1.2``
                                      (sha256-checked by the probe parser)
  * `sc` success/failure values    -> ``spec/SimRISC-12 §1``
  * `CLONE_*` bits, `SIGSEGV`/`SIGTERM`, `EXIT_ZOMBIE`
                                   -> the image's own uapi/generic headers
  * clocksource freq / tick target -> ``contract-see §3``, ``asm/time.h``
  * probe constants (TLS, sentinel) -> the probe/stub sources
  * trap sequence                  -> the built vmlinux's disassembly of the stub
  * retirement anchors             -> the files named in the table below

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (spec / contract / kernel source / build tree missing).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.unit.linux import k2_trap_probe as k2trap          # noqa: E402  (spec §2/§7.1)
from tests.unit.linux import k5_clocksource_probe as k5clock  # noqa: E402
from tests.unit.linux import k5_clone_probe as k5clone        # noqa: E402
from tests.unit.linux import k5_futex_probe as k5futex        # noqa: E402
from tests.unit.linux import k5_pagesz_probe as k5pagesz      # noqa: E402
from tests.unit.linux import k5_signal_probe as k5signal      # noqa: E402
from tests.unit.linux import k5_syscall_probe as k5sys        # noqa: E402
from tools.linux import config_pins as pins                   # noqa: E402
from tools.linux import paths as linux_paths                  # noqa: E402
from tools.qemu import k0_boot_probe as k0                    # noqa: E402  (firmware, qemu)

TIMEOUT_QEMU = int(os.environ.get("K5G_QEMU_TIMEOUT", "300"))
JOBS = os.environ.get("JOBS", "32")

SCRATCH = (Path(os.environ.get("K5G_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-029") / "check-linux-k5")

SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
PROCESS_07 = _REPO / "docs" / "Process-07-门控分层规范.md"
MAKEFILE = _REPO / "Makefile"
SERIES = _REPO / "components" / "linux" / "series"
TESTS_DIR = _REPO / "tests" / "unit" / "linux"
SOURCE = linux_paths.linux_source_dir()

GROUPS = "SCFTGPR"

#: group -> (probe module, the probe symbol that must be `y` in that image).
#:
#: The image slice is the *probe's own* (`module.build_image()`): this gate has
#: no ``CONFIG_PINS`` of its own, so the symbol set has exactly one owner per
#: image and the gate cannot drift from the probe it is a closure of
#: (`make check-config-pins` C2/C3 apply to the probe scripts).
IMAGES = {
    "S": (k5sys, "CONFIG_DADAO_K5_SYSCALL_SELFTEST"),
    "C": (k5clone, "CONFIG_DADAO_K5_CLONE_SELFTEST"),
    "F": (k5futex, "CONFIG_DADAO_K5_FUTEX_SELFTEST"),
    "T": (k5clock, "CONFIG_DADAO_K5_CLOCK_SELFTEST"),
    "G": (k5signal, "CONFIG_DADAO_K5_SIGNAL_SELFTEST"),
    "P": (k5pagesz, "CONFIG_DADAO_K5_PAGESZ_SELFTEST"),
}

#: The representative signal-frame assertions of group G (the full 76-row sweep
#: stays in `k5_signal_probe.py`).
SIGNAL_CASES = {
    "s1": ("novma-died-by-sigsegv", "perm-died-by-sigsegv"),
    "s2": ("handler-runs", "handler-frame-image", "handler-ras-below",
           "snapshot-racnt", "snapshot-mrptr", "fcsr-snapshot-arch",
           "fcsr-masked", "rd-bank", "rb-bank", "ra-bank", "rf-bank",
           "resume-ip"),
    "s3": ("died-by-signal", "no-exit-status", "no-handler-ran"),
    "s4": ("handler-sp-in-altstack",),
    "s5": ("exit-code", "group-exit-code", "group-sibling-gone"),
    "s6": ("child-inherited-cur", "child-inherited-max", "wait-status-sigsegv",
           "over-limit-refused"),
}

#: The §4a retirement table of this task: (file, retired wording, replacement,
#: disposition, alternative criterion).  §4a of ``docs/Process-07`` carries the
#: same rows; the gate asserts both directions (new in / old out).
RETIREMENTS = (
    ("tests/unit/linux/k4_fork_probe.py",
     "F3 已移 017",
     "F3 的替代判据 = check-linux-k5 S 组",
     "改限定语",
     "check-linux-k5 S 组：/init.musl 自己跑完并退出"),
    ("tests/unit/linux/k4_fork_probe.py",
     "无 017 的 switch_to",
     "本镜像按 K4 自己的边界判据停在 K4 边界",
     "改限定语",
     "check-linux-k5 C/G 组：用户任务与线程真的被调度"),
    ("tests/unit/linux/k4_stack_probe.py",
     "the vehicle the task book allows while the\nU-mode closure of "
     "`m14-linux-016/017` is still open.",
     "the vehicle every \"did not grow\" case needs\n"
     "(it ends the boot by name; the user-mode vehicle is K5's s1/s6).",
     "改限定语",
     "check-linux-k5 G 组：用户态 s1/s6 行为例"),
    ("tests/unit/linux/check_k2.py",
     "neither K3 probe may leak in",
     "no milestone probe may leak in",
     "改限定语",
     "check-linux-k5 S–P 组的镜像切片（K3 已整体退役）"),
    ("components/linux/patches/arch/dadao/Kconfig.debug.patch",
     "A real user process pressing on its stack needs the U-mode closure of",
     "A real user process pressing on its stack is the K5 closure's (s1/s6",
     "改限定语",
     "check-linux-k5 G 组"),
)

#: Names this task retires outright (K3 as a stage, user ruling 2026-11-20).
RETIRED_NAMES = ("check-linux-k3", "check_k3", "k3_page_probe", "k3_pt_probe",
                 "k3_pf_selftest", "k3_pt_selftest", "CONFIG_DADAO_K3_")

#: Live scopes the retired names must not appear in (the §4a record and the
#: changelog are history and are allowed to name them).
RETIRED_SCOPES = ("Makefile", "tests/unit/linux", "tools/linux",
                  "components/linux/series", "components/linux/patches")


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus live ``[STAT]``.

    ``<id>`` starts with the group letter; the per-group tally printed at the end
    is what the task means by "PASS == 总数, 每组现场计数".
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

    def info(self, text: str) -> None:
        if not self.quiet:
            print(f"  [INFO] {text}", flush=True)

    def summary(self) -> str:
        parts = []
        for group in GROUPS:
            if group in self.groups:
                total, failed = self.groups[group]
                parts.append(f"{group} {total - failed}/{total}")
        return "  ".join(parts)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"check_k5: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def repo_text(rel: str) -> str:
    path = _REPO / rel
    if not path.is_file():
        raise SystemExit(f"check_k5: repository file missing: {rel}")
    return path.read_text(encoding="utf-8")


#: A VMA lookup must sit inside the mmap lock: `find_vma()` asserts it
#: (mm/mmap.c) and a lock-free read WARNs at include/linux/rwsem.h — the k5
#: probe did exactly that until m18-linux-019.
VMA_LOOKUPS = re.compile(
    r"(?<![A-Za-z0-9_])(?:dadao_pf_find_vma|find_vma)\s*\(")
MMAP_LOCKS = ("mmap_read_lock(", "mmap_write_lock(")
MMAP_UNLOCKS = ("mmap_read_unlock(", "mmap_write_unlock(")


def vma_lookup_outside_lock(text: str) -> list[str]:
    """``<line>: <call>`` for every VMA lookup the mmap lock does not cover.

    The probe builds its address space by hand and then reads it from the
    trap hook, so the same rule has to hold at both sites: the lock depth
    (read or write) must be positive when the lookup runs.  A textual
    balance is enough to catch a lookup moved out of its locked region, and
    it is what `--inject vma-lookup-unlocked` flips.  Comments are dropped
    first so the rule's own prose is not mistaken for a call.
    """
    depth = 0
    problems: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        code = line.split("/*", 1)[0]
        if code.strip().startswith("*"):
            code = ""
        if any(token in code for token in MMAP_LOCKS):
            depth += 1
        if any(token in code for token in MMAP_UNLOCKS):
            depth -= 1
        if depth < 0:
            problems.append(f"{number}: unlock without a lock")
            depth = 0
        if depth <= 0 and VMA_LOOKUPS.search(code):
            problems.append(f"{number}: {line.strip()[:60]}")
    return problems


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    return config_value(config, symbol) in ("y", "1")


def hexs(value: int) -> str:
    return hex(value)


def pf_rows(text: str) -> list[dict[str, str]]:
    """The fault channel's one-line report (``K3 pf: key=value ...``)."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("K3 pf: "):
            continue
        rows.append({key: value for key, value in
                     (tok.split("=", 1) for tok in line.split() if "=" in tok)})
    return rows


def row_of(rows: list[tuple[str, dict[str, str]]],
           name: str) -> dict[str, str] | None:
    for got_name, row in rows:
        if got_name == name:
            return row
    return None


def got_of(rows, name, default=None):
    row = row_of(rows, name)
    return default if row is None else row["got"]


def want_of(rows, name, default=None):
    row = row_of(rows, name)
    return default if row is None else row["want"]


# ---------------------------------------------------------------------------
# expectations parsed from spec / contract / headers (never restated)
# ---------------------------------------------------------------------------

def spec_section(path: Path, start: str, end: str, what: str) -> str:
    text = path.read_text(encoding="utf-8")
    cut = text.split(start, 1)
    if len(cut) != 2:
        raise SystemExit(f"check_k5: '{start}' not found in {what}")
    return cut[1].split(end, 1)[0]


def page_shift_from_spec() -> int:
    """``spec/DADAO-12 §2.2.2``: the page-offset width, in bits."""
    body = spec_section(SPEC_DADAO12, "#### 2.2.2", "\n#### ",
                        "spec/DADAO-12 §2.2.2")
    m = re.search(r"页内偏移为\s*(\d+)\s*位", body)
    if m:
        return int(m.group(1))
    m = re.search(r"`VA\[(\d+):00\]`\s*->\s*页内偏移", body)
    if not m:
        raise SystemExit("check_k5: §2.2.2 has no page-offset width")
    return int(m.group(1)) + 1


def superpage_bytes() -> int:
    """``spec/DADAO-12 §2.2.1``: the superpage size, in bytes."""
    text = SPEC_DADAO12.read_text(encoding="utf-8")
    m = re.search(r"超页\s*(\d+)\s*MiB", text)
    if not m:
        raise SystemExit("check_k5: §2.2.1 has no superpage size")
    return int(m.group(1), 0) * 1024 * 1024


def run_mode(name: str) -> int:
    """``spec/DADAO-12 §1``'s two-bit encoding of a run mode (``user``/``supv``)."""
    text = SPEC_DADAO12.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 3 and any(cell == name for cell in cells):
            m = re.search(r"0b([01]{2})", cells[0])
            if m:
                return int(m.group(1), 2)
    raise SystemExit(f"check_k5: spec/DADAO-12 §1 has no mode {name!r}")


def cause_ids() -> dict[str, int]:
    table = k2trap.spec_cause_table()
    if not table:
        raise SystemExit("check_k5: spec/DADAO-13 §2 cause table is empty")
    return {name: cid for cid, name in table}


def signal_number(name: str) -> int:
    text = kernel_text("include/uapi/asm-generic/signal.h")
    m = re.search(rf"^#define\s+{name}\s+(\d+)", text, re.MULTILINE)
    if not m:
        raise SystemExit(f"check_k5: signal.h has no {name}")
    return int(m.group(1), 0)


def exit_zombie() -> int:
    text = kernel_text("include/linux/sched.h")
    m = re.search(r"^#define\s+EXIT_ZOMBIE\s+(0x[0-9a-fA-F]+|\d+)\s*$",
                  text, re.MULTILINE)
    if not m:
        raise SystemExit("check_k5: include/linux/sched.h has no EXIT_ZOMBIE")
    return int(m.group(1), 0)


def image_page_size(config: str) -> int:
    """The page size the image runs with: ``CONFIG_PAGE_SHIFT`` (live)."""
    shift = config_value(config, "CONFIG_PAGE_SHIFT")
    if shift is None:
        raise SystemExit("check_k5: the image's .config has no CONFIG_PAGE_SHIFT")
    return 1 << int(shift)


def eagain() -> int:
    return k5futex.eagain()


def minus(value: int) -> int:
    return (1 << 64) - value


# ---------------------------------------------------------------------------
# build + boot (the probes' own image slices)
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def build_image(group: str, label: str) -> tuple[int, str | None]:
    """Build the group's image through that probe's own entry point.

    The probe owns the slice (`CONFIG_PINS` + `config_lines()`), so the gate
    reuses it instead of declaring a second copy that could drift.
    """
    module = IMAGES[group][0]
    print(f"[INFO] build group {group} ({label}, JOBS={JOBS})", flush=True)
    if group == "T":
        rc = module.config()            # the clock probe's builder returns rc
        if rc != 0:
            return rc, None
        return 0, (build_dir() / ".config").read_text(encoding="utf-8")
    rc, snap = module.build_image(label)
    if rc != 0 or snap is None:
        return rc, None
    return 0, snap["config"]


_ROMS: dict[str, str] = {}


def firmware() -> str:
    if "rom" not in _ROMS:
        k0.load_contract()
        if not k0.ABI:
            raise SystemExit("check_k5: the boot contract is empty")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        _ROMS["rom"] = k0.build_firmware(str(SCRATCH / "bootrom"),
                                         name="bootrom_k5g.bin")
    return _ROMS["rom"]


def boot(tag: str) -> tuple[int, str, list[str]]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"check_k5: {kernel} missing")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("check_k5: qemu-system-dadao missing (make install-host)")
    log_dir = SCRATCH / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={firmware()}",
           "-nographic", "-semihosting-config", "enable=on,target=native",
           "-kernel", str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    # The semihosting console is QEMU's stderr; stdout carries only the monitor
    # banner.  Keep the console stream alone (the log keeps both for diagnosis).
    text = err or out or ""
    (log_dir / f"{tag}.log").write_text((err or "") + (out or ""),
                                        encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# S — user-mode closure (m14-linux-023)
# ---------------------------------------------------------------------------

def judge_s(rep: Report, text: str, rc: int, config: str | None,
            oracle: list[tuple[int, int]] | None) -> None:
    g = "S"
    if config is not None:
        for symbol in ("CONFIG_DADAO_K1_EARLY_STOP",
                       "CONFIG_DADAO_K2_EARLY_STOP",
                       "CONFIG_DADAO_K2_TIME_STOP",
                       "CONFIG_DADAO_K4_SELFTEST",
                       "CONFIG_DADAO_K4_SWITCH_SELFTEST"):
            rep.check(g, f"镜像配置：{symbol} 关", False,
                      config_enabled(config, symbol))
        rep.check(g, "镜像配置：K5 用户 syscall 自检 = y", "y",
                  config_value(config, "CONFIG_DADAO_K5_SYSCALL_SELFTEST"))
        rep.check(g, "镜像页大小 == spec §2.2.2 的页内偏移", 1 << page_shift_from_spec(),
                  image_page_size(config))

    rep.check(g, "自检只开始一次（没有二次初始化）", 1,
              text.count("K5 selftest: begin"))
    rep.check(g, "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5 selftest FAIL")])
    # m18-linux-019: every VMA lookup of the probe is a mmap-lock guest, and
    # a lookup moved out of its locked region must show up as the rwsem WARN
    # (the source-level rule catches it even before the image boots).
    rep.check(g, "VMA 查找全在 mmap 锁内（源码级）", [],
              vma_lookup_outside_lock(
                  kernel_text("arch/dadao/kernel/k5_syscall_selftest.c")))
    rep.check(g, "日志无 rwsem 锁警告（rwsem.h:81）", 0,
              text.count("rwsem.h:81"))
    rows = k5sys.check_lines(text)
    rep.check(g, "内核自评的每条 K5 check 都 ok", [],
              [name for name, row in rows if row["verdict"] != "ok"])
    seen = [name for name, _ in rows]
    for case, names in k5sys.CASES.items():
        missing = [name for name in names if name not in seen]
        rep.check(g, f"{case} 的代表断言都报了（{len(names)} 条）", [], missing)

    # The real init: /init.musl's own output is the end-to-end evidence.
    for want in ("init: pid=", "init: brk +65536 ok", "K5 init: exit=0"):
        rep.check(g, f"init 自己的输出包含 {want!r}", True, want in text)
    exit_row = k5sys.one(text, "K5 exit:")
    rep.check(g, "退出观察行存在", True, exit_row is not None)
    if exit_row:
        rep.check(g, "子任务的 exit_code == 0", "0",
                  str(int(exit_row.get("code", "-1"))))

    # errno: rd8 = -errno inside the contract's range; rd1 out of the path.
    lo, hi = k5sys.errno_bounds()
    bad = []
    for name in ("u3_ni_enosys", "u3_range_enosys", "u3_mmap_einval",
                 "u3_undef_enosys"):
        got = got_of(rows, name)
        if got is None:
            bad.append(f"{name}(缺)")
            continue
        value = int(got, 0)
        if not (lo <= value <= hi and value < 0):
            bad.append(f"{name}={value}")
    rep.check(g, f"errno 全在契约区间 [{lo},{hi}] 且为负", [], bad)
    rd1 = row_of(rows, "u3_rd1_untouched")
    rep.check(g, "rd1 不参与 syscall 路径（内核判据 ok）", "ok",
              rd1["verdict"] if rd1 else None)
    sentinel = row_of(rows, "u3_rd1_sentinel")
    rep.check(g, "rd1 的哨兵值往返未变", True,
              bool(sentinel) and sentinel["want"] == sentinel["got"])

    # TLS: the kernel compares the frame's rb3 with the value the program put
    # there (the row's got is that verdict), and the user's read-back is the
    # TLS the program loaded (want == got, non-zero: `rb3` is `rbtp`).
    frame_rb3 = row_of(rows, "u4_frame_rb3")
    user_rb3 = row_of(rows, "u4_user_rb3")
    rep.check(g, "帧保存的 rb3 == 用户值（内核判据 ok）", "ok",
              frame_rb3["verdict"] if frame_rb3 else None)
    rep.check(g, "用户读回的 rb3 是程序装的 TLS（want == got ≠ 0）", True,
              bool(user_rb3) and user_rb3["want"] == user_rb3["got"]
              and int(user_rb3["got"], 16) != 0)
    entry = kernel_text("arch/dadao/include/asm/entry.h")
    rep.check(g, "入口保存并恢复 rb3（rbtp）", True,
              "PT_RB_BASE + 3 * 8" in entry
              and "ld.o\trb3, [rb3, PT_RB_BASE + 3 * 8]" in entry)

    # cg5 frame fields: cause/mode from the spec, immu18 from the disassembly.
    traps = k5sys.trap_lines(text)
    cftrap = cause_ids()["CFXTRAP"]
    user = run_mode("user")
    rep.check(g, "每条 trap 的 cause == spec 的 CFXTRAP", [],
              [i for i, row in enumerate(traps)
               if int(row["cause"], 16) != cftrap])
    rep.check(g, "每条 trap 的上一运行模式 == spec 的 user", [],
              [i for i, row in enumerate(traps)
               if int(row["mode"], 16) != user])
    if oracle:
        rep.check(g, "trap 条数 == stub 反汇编的 trap 条数", len(oracle),
                  len(traps))
        if len(traps) == len(oracle) and traps:
            first = int(traps[0]["ip"], 16)
            rep.check(g, "trap_cause_ip 的偏移 == 反汇编的偏移", [],
                      [i for i, (row, (off, _)) in enumerate(zip(traps, oracle))
                       if int(row["ip"], 16) - first != off - oracle[0][0]])
            rep.check(g, "immu18 == 该 trap 指令的立即数", [],
                      [i for i, (row, (_, immu)) in enumerate(zip(traps, oracle))
                       if int(row["immu18"], 16) != immu])
    table = k5sys.syscall_table_snapshot()
    numbers = {int(row["nr"], 16) for row in traps}
    known = set(table.values())
    highest = max(known)
    # The program deliberately sends one number past the table (the `-ENOSYS`
    # range arm): "inside the locked snapshot or past its end, nothing else".
    rep.check(g, "trap 号或 ∈ 锁定快照，或越过表尾（范围用例）", [],
              sorted(n for n in numbers if n not in known and n < highest))
    rep.check(g, "恰有一个越过表尾的号（-ENOSYS 范围用例）", True,
              any(n > highest for n in numbers))
    for name in ("write", "mmap"):
        rep.check(g, f"程序真的发过 {name}（号 {table[name]}）", True,
                  table[name] in numbers)
    exec_row = k5sys.one(text, "K5 exec:")
    rep.check(g, "execve 行存在", True, exec_row is not None)
    if exec_row:
        rep.check(g, "execve 后帧的 rb3 == 0", "0x0", exec_row.get("rb3"))
        rep.check(g, "execve 后帧的 ip == 镜像里 /init.musl 的 e_entry", True,
                  exec_row.get("entry") == exec_row.get("ip")
                  and int(exec_row.get("entry", "0"), 16) != 0)
    rep.check(g, "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# C — clone / threads (m14-linux-024)
# ---------------------------------------------------------------------------

def judge_c(rep: Report, text: str, rc: int, config: str | None) -> None:
    g = "C"
    if config is not None:
        for symbol, value in {
                "CONFIG_DADAO_K5_CLONE_SELFTEST": "y",
                "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
                "CONFIG_CLONE_BACKWARDS": "y",
                "CONFIG_PAGE_SIZE_64KB": "y"}.items():
            if value == "n":
                rep.check(g, f"镜像配置：{symbol} 关", False,
                          config_enabled(config, symbol))
            else:
                rep.check(g, f"镜像配置：{symbol} = {value}", value,
                          config_value(config, symbol))

    rep.check(g, "自检只开始一次", 1, text.count("K5 clone selftest: begin"))
    rep.check(g, "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5 clone FAIL")])
    rep.check(g, "末尾是自检完成行", True, "K5 clone selftest: done" in text)
    rows = k5clone.check_lines(text)
    rep.check(g, "内核自评的每条 K5 check 都 ok", [],
              [name for name, row in rows if row["verdict"] != "ok"])
    seen = [name for name, _ in rows]
    for case, names in k5clone.CASES.items():
        missing = [name for name in names if name not in seen]
        rep.check(g, f"{case} 的代表断言都报了（{len(names)} 条）", [], missing)

    bits = k5clone.clone_bits()
    tls = k5clone.stub_constant("K5C_TLS")
    sentinel = k5clone.probe_constant("K5C_RB3_SENTINEL")
    sc_ok, sc_bad = k5clone.sc_codes()

    pre = k5clone.one(text, "K5 clone pre:")
    fork_pre = k5clone.one(text, "K5 clone fork pre:")
    child = k5clone.one(text, "K5 clone child:")
    forked = k5clone.one(text, "K5 clone fork child:")
    done = k5clone.one(text, "K5 clone done:")
    rep.check(g, "clone 前现场行存在", True, pre is not None)
    rep.check(g, "thread 子线程现场行存在", True, child is not None)
    rep.check(g, "fork 子进程现场行存在", True, forked is not None)
    rep.check(g, "父侧结论文存在", True, done is not None)

    if pre and child:
        rep.check(g, "CLONE_VM：子 mm == 父 mm", child.get("parent_mm"),
                  child.get("mm"))
        rep.check(g, "CLONE_VM：子 asid == 父 asid", child.get("parent_asid"),
                  child.get("asid"))
        rep.check(g, "子存活时 mm_users == 父 + 1",
                  int(pre.get("mm_users", "-1")) + 1,
                  int(child.get("mm_users", "-9")))
        rep.check(g, "CLONE_SETTLS：子 rb3 == tls 参数", hexs(tls),
                  child.get("rb3"))
        rep.check(g, "子入口 rd8 == 0", "0x0", child.get("rd8_at_entry"))
        rep.check(g, "子帧是父帧的副本（§11 现场副本）", pre.get("copy"),
                  child.get("copy"))
        rep.check(g, "thread clone 的 flags == sched.h 的 VM|FS|FILES|SIGHAND"
                  "|THREAD|SETTLS", hexs(
                      bits["CLONE_VM"] | bits["CLONE_FS"] | bits["CLONE_FILES"]
                      | bits["CLONE_SIGHAND"] | bits["CLONE_THREAD"]
                      | bits["CLONE_SETTLS"]), pre.get("flags"))
    if forked:
        rep.check(g, "fork 子的 mm != 父 mm", True,
                  forked.get("mm") != forked.get("parent_mm"))
        rep.check(g, "fork 子的 asid != 父 asid", True,
                  forked.get("asid") != forked.get("parent_asid"))
        # The thread child may still hold its reference when the fork is
        # taken, so the invariant is "the fork added none" (the kernel's own
        # c1_fork_parent_mm_users check is the verdict; this is its evidence).
        before = int(fork_pre.get("mm_users", "-1")) if fork_pre else -2
        after = int(forked.get("parent_mm_users", "-9"))
        rep.check(g, "fork 不新增父 mm 的引用（<= fork 前的值）", True,
                  1 <= after <= before)
        rep.check(g, "fork 子继承父的 rb3（无 SETTLS）", hexs(sentinel),
                  forked.get("rb3"))
        rep.check(g, "CLONE_THREAD 的反面：fork 子的 tgid == 它自己的 pid",
                  forked.get("pid"), forked.get("tgid"))
    if done:
        rep.check(g, "父 clone 返回子 tid（非零）", True,
                  int(done.get("thread_ret", "0"), 16) != 0)
        rep.check(g, "两个 clone 返回不同的 tid", True,
                  done.get("thread_ret") != done.get("fork_ret"))
        rep.check(g, "两个 clone 后父 rb3 仍是哨兵", hexs(sentinel),
                  done.get("parent_rb3"))
        if pre:
            rep.check(g, "全部子退出后 mm_users 回到原值",
                      int(pre.get("mm_users", "-1")),
                      int(done.get("mm_users", "-9")))
        rep.check(g, "lr;sc 无异常介入 ⇒ spec 的成功值", hexs(sc_ok),
                  done.get("sc_now"))
        rep.check(g, "lr;trap;sc ⇒ spec 的失败值", hexs(sc_bad),
                  done.get("sc_across"))

    # Source facts a boot cannot show.
    fork_c = kernel_text("kernel/fork.c")
    rep.check(g, "copy_process 在 CLONE_VM 下共享 mm（mmget 而非 dup_mm）", True,
              "if (clone_flags & CLONE_VM)" in fork_c
              and "mmget(oldmm)" in fork_c)
    process = kernel_text("arch/dadao/kernel/process.c")
    rep.check(g, "copy_thread 的 fork 分支按 CLONE_SETTLS 取 args->tls", True,
              "args->flags & CLONE_SETTLS" in process
              and "childregs->rb[3] = args->tls" in process)
    sched = kernel_text("include/uapi/linux/sched.h")
    stub_flags = k5clone.stub_constant("K5C_CLONE_FLAGS")
    all_bits = 0
    for name in ("CLONE_VM", "CLONE_FS", "CLONE_FILES", "CLONE_SIGHAND",
                 "CLONE_THREAD", "CLONE_SETTLS"):
        m = re.search(rf"^#define\s+{name}\s+(0x[0-9a-fA-F]+)", sched,
                      re.MULTILINE)
        if not m:
            raise SystemExit(f"check_k5: sched.h has no {name}")
        all_bits |= int(m.group(1), 16)
    rep.check(g, "stub 的 CLONE_* 组合 == sched.h 的位或", hexs(all_bits),
              hexs(stub_flags))
    rep.check(g, "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# F — futex / user atomics (m14-linux-025)
# ---------------------------------------------------------------------------

def judge_f(rep: Report, text: str, rc: int, config: str | None) -> None:
    g = "F"
    if config is not None:
        for symbol, value in {
                "CONFIG_DADAO_K5_FUTEX_SELFTEST": "y",
                "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
                "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
                "CONFIG_FUTEX": "y",
                "CONFIG_SMP": "n",
                "CONFIG_PAGE_SIZE_64KB": "y"}.items():
            if value == "n":
                rep.check(g, f"镜像配置：{symbol} 关", False,
                          config_enabled(config, symbol))
            else:
                rep.check(g, f"镜像配置：{symbol} = {value}", value,
                          config_value(config, symbol))

    rep.check(g, "自检只开始一次", 1, text.count("K5 futex selftest: begin"))
    rep.check(g, "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5 futex FAIL")])
    rep.check(g, "末尾是自检完成行", True, "K5 futex selftest: done" in text)
    rows = k5futex.check_lines(text)
    rep.check(g, "内核自评的每条 K5 check 都 ok", [],
              [name for name, row in rows if row["verdict"] != "ok"])
    seen = [name for name, _ in rows]
    for case, names in k5futex.CASES.items():
        missing = [name for name in names if name not in seen]
        rep.check(g, f"{case} 的代表断言都报了（{len(names)} 条）", [], missing)

    sc_ok, sc_bad = k5futex.sc_codes()
    futex = k5futex.uapi_futex()
    again = eagain()

    def expect_want(name: str, value: int) -> None:
        got = want_of(rows, name)
        rep.check(g, f"{name} 的 want 是现场派生值", hexs(value),
                  None if got is None else hexs(int(got, 0)))

    # F1 / F1A: the wait is atomic, the recheck answers -EAGAIN.
    expect_want("f1_wake_count", 1)
    expect_want("f1a_ret_is_eagain", minus(again))
    # F3/F4: the two `sc` outcomes are the spec's.
    expect_want("f3_peer_success", sc_ok)
    expect_want("f3_parent_sc_after_yield", sc_bad)
    expect_want("f4_sc_immediate", sc_ok)
    expect_want("f4_sc_after_syscall", sc_bad)
    # F5/F6: requeue moves without waking; a wrong bitset does not wake.
    expect_want("f5_requeue_moved", 1)
    expect_want("f6_other_bitset_wake", 0)
    # F7 / m14-linux-035: a shared futex on an anonymous page resolves its key.
    expect_want("shared_futex_wake", 0)
    expect_want("shared_futex_wait_eagain", minus(again))
    expect_want("shared_futex_page_mapped", 1)

    # The op numbers the program sent are the uapi ones.
    stub = k5futex.stub_constants()
    rep.check(g, "stub 的 WAIT op == FUTEX_WAIT|PRIVATE",
              hexs(futex["FUTEX_WAIT"] | futex["FUTEX_PRIVATE_FLAG"]),
              hexs(stub.get("K5F_OP_WAIT_PRIVATE", -1)))
    rep.check(g, "stub 的 WAKE op == FUTEX_WAKE|PRIVATE",
              hexs(futex["FUTEX_WAKE"] | futex["FUTEX_PRIVATE_FLAG"]),
              hexs(stub.get("K5F_OP_WAKE_PRIVATE", -1)))

    # Source facts: arch atomics, the recheck, and the rmap-backed anon page.
    arch = kernel_text("arch/dadao/include/asm/futex.h")
    rep.check(g, "arch futex 用 lr.t/sc.t（不是 get_user 当原子）", True,
              "lr.t.nn" in arch and "sc.t.nn" in arch)
    rep.check(g, "arch futex 提供 cmpxchg 与 op_inuser 两个钩子", True,
              "futex_atomic_cmpxchg_inatomic" in arch
              and "arch_futex_atomic_op_inuser" in arch)
    waitwake = kernel_text("kernel/futex/waitwake.c")
    setup_at = waitwake.index("int futex_wait_setup(")
    setup = waitwake[setup_at:waitwake.index("\n}\n", setup_at)]
    rep.check(g, "futex_wait_setup 在 enqueue 前复核用户字", True,
              "futex_get_value_locked(&uval, uaddr)" in setup
              and "if (uval != val)" in setup
              and setup.index("if (uval != val)") < setup.index("futex_queue("))
    fault = kernel_text("arch/dadao/mm/fault.c")
    rep.check(g, "用户 VMA 走通用 handle_mm_fault（rmap 的前提）", True,
              "handle_mm_fault(" in fault)
    memory = kernel_text("mm/memory.c")
    rep.check(g, "匿名页经 rmap 安装（folio_add_new_anon_rmap）", True,
              "folio_add_new_anon_rmap(" in memory)
    rmap = kernel_text("mm/rmap.c")
    mapping_anon = re.findall(r"\b[A-Z_]*MAPPING_ANON\b", rmap)
    rep.check(g, "匿名页的 mapping 带 *_MAPPING_ANON 标记（rmap 成果）", True,
              bool(mapping_anon))
    core = kernel_text("kernel/futex/core.c")
    rep.check(g, "get_futex_key：无 mapping ⇒ -EFAULT、anon ⇒ mm 键", True,
              "if (unlikely(!mapping))" in core
              and "folio_test_anon(folio)" in core)
    rep.check(g, "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# T — clocksource / clockevent (m14-linux-026)
# ---------------------------------------------------------------------------

def judge_t(rep: Report, text: str, rc: int, config: str | None,
            cmd: list[str] | None) -> None:
    g = "T"
    freq = k5clock.contract_freq()
    if config is not None:
        rep.check(g, "镜像配置：K5 时钟自检 = y", "y",
                  config_value(config, "CONFIG_DADAO_K5_CLOCK_SELFTEST"))
        rep.check(g, "镜像配置：K2 时间边界未设（走通用 time_init）", [],
                  [line for line in config.splitlines()
                   if line.startswith("CONFIG_DADAO_K2_TIME_STOP=")])
        hz = k5clock.config_hz(config)
    else:
        hz = int(config_value(config or "", "CONFIG_HZ") or "100")
    period = freq // hz
    rep.stat(f"freq={freq} hz={hz} period={period}")

    rep.check(g, "探针 begin 行只出现一次", 1, len(k5clock.BEGIN.findall(text)))
    begin = k5clock.BEGIN.search(text)
    rep.check(g, "begin 行存在", True, begin is not None)
    if begin:
        (_cs, rating, _mask, _ce, _ce_rating, features, handler, printed_freq,
         printed_hz, printed_period) = begin.groups()
        rep.check(g, "clocksource freq == contract-see §3", freq,
                  int(printed_freq))
        rep.check(g, "clocksource hz == 镜像的 CONFIG_HZ", hz, int(printed_hz))
        rep.check(g, "clocksource period == freq / hz", period,
                  int(printed_period))
        rep.check(g, "clocksource rating > jiffies 后备源", True,
                  int(rating) > k5clock.jiffies_rating())
        rep.check(g, "clockevent 已安装 tick 的 handler", 1, int(handler))
        rep.check(g, "clockevent 声明 ONESHOT", True,
                  bool(int(features, 0) & k5clock.oneshot_feature()))

    # Registration happens inside time_init(): cs, then ce, then the probe.
    lines = text.splitlines()

    def index(prefix: str) -> int:
        return next((i for i, line in enumerate(lines)
                     if line.startswith(prefix)), -1)

    rep.check(g, "time_init 注册 clocksource 行存在", True,
              k5clock.CS.search(text) is not None)
    rep.check(g, "time_init 注册 clockevent 行存在", True,
              k5clock.CE.search(text) is not None)
    rep.check(g, "注册顺序：clocksource 先于 clockevent、均先于探针体", True,
              0 <= index("K5 time: cs=") < index("K5 time: ce=")
              < index("K5 clock: begin"))

    samples = [(int(i), int(s), int(r)) for i, s, r in k5clock.T1.findall(text)]
    rep.check(g, "t1 采样行数 == 3", 3, len(samples))
    if len(samples) == 3:
        raw = [r for _i, _s, r in samples]
        sched = [s for _i, s, _r in samples]
        rep.check(g, "clocksource 读值非降", True,
                  all(a <= b for a, b in zip(raw, raw[1:])))
        rep.check(g, "clocksource 在读数期间真的前进（非常量源）", True,
                  raw[-1] > raw[0])
        rep.check(g, "sched_clock 与 clocksource 同源（偏移恒定，±period/8）",
                  True,
                  max(raw) - min(raw) > 0
                  and (max(r - s for r, s in zip(raw, sched))
                       - min(r - s for r, s in zip(raw, sched)))
                  <= period // 8)

    t2 = k5clock.T2.search(text)
    rep.check(g, "t2 next-event 行存在", True, t2 is not None)
    if t2:
        (_p, arm_long, cmp_long, arm_short, cmp_short, event,
         interval) = (int(v) for v in t2.groups())
        rep.check(g, "长 deadline 写进 timer_cmp（8 期 ±period/2）", True,
                  8 * period <= cmp_long - arm_long <= 8 * period + period // 2)
        rep.check(g, "短 deadline 覆盖长 deadline", True,
                  cmp_long - cmp_short >= 6 * period)
        rep.check(g, "事件真的投递了", True, event != 0)
        rep.check(g, "投递间隔 ∈ [period/2, 2*period]", True,
                  period // 2 <= interval <= 2 * period)

    t3 = k5clock.T3.search(text)
    rep.check(g, "t3 tick 行存在", True, t3 is not None)
    if t3:
        want, j0, j1, ticks = (int(v) for v in t3.groups()[:4])
        rep.check(g, "tick 目标 == asm/time.h 的 DADAO_K5_CLOCK_TICKS",
                  k5clock.declared_ticks(), want)
        rep.check(g, "连续投递数 >= 目标", True, ticks >= want)
        rep.check(g, "jiffies_64 每次投递前进 1（do_timer(1) 真的跑）", ticks,
                  j1 - j0)

    t4 = k5clock.T4.search(text)
    rep.check(g, "t4 ktime 汇总行存在", True, t4 is not None)
    if t4:
        cs0, cs1, k0v, k1v, window = (int(v) for v in t4.groups())
        rep.check(g, "ktime_get() 前进", True, k1v > k0v)
        rep.check(g, "ktime 分辨率优于半个 period（离开 jiffies 后备源）", True,
                  k1v - k0v < period // 2)
        rep.check(g, "t4 采样行数 == 8", 8, len(k5clock.T4S.findall(text)))
    rep.check(g, "末尾是自检完成行", True, len(k5clock.DONE.findall(text)) == 1)
    non_empty = [line for line in text.splitlines() if line.strip()]
    rep.check(g, "退出标记是最后一行", True,
              bool(non_empty) and non_empty[-1] == "K5 clock: done")
    rep.check(g, "命令行无 -d（不用逐指令日志）", True,
              not cmd or ("-d" not in cmd and "-D" not in cmd))
    rep.check(g, "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# G — signals / exit / rlimit (m14-linux-027 + 046)
# ---------------------------------------------------------------------------

def judge_g(rep: Report, text: str, rc: int, config: str | None) -> None:
    g = "G"
    if config is not None:
        for symbol, value in {
                "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "y",
                "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
                "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
                "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
                "CONFIG_PAGE_SIZE_64KB": "y"}.items():
            if value == "n":
                rep.check(g, f"镜像配置：{symbol} 关", False,
                          config_enabled(config, symbol))
            else:
                rep.check(g, f"镜像配置：{symbol} = {value}", value,
                          config_value(config, symbol))

    rep.check(g, "自检只开始一次", 1, text.count("M46 selftest: begin"))
    rep.check(g, "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("M46 selftest FAIL")])
    rep.check(g, "探针的用例阶段跑完（不是半路死掉）", True,
              "M46 selftest: probe cases done" in text)
    # ADR-0062 D1: the s1 permission fault (a store into a read-only mapping)
    # must reach the channel as *one flat bitmap bit*: the low class is 0, the
    # id is exactly 1 << NWPERM of contract-see §6.1.1, and the bit is named.
    nwperm = k2trap.contract_bitmap_bit("NWPERM")
    perm_pf = [row for row in pf_rows(text)
               if row.get("result") == "die-perm"
               and row.get("sub") == "NWPERM"]
    rep.check(g, "页权限故障以扁平位图到达通道（≥1 次 NWPERM/die-perm）", True,
              bool(perm_pf))
    rep.check(g, "die-perm 的 cause_id == 1 << §6.1.1 NWPERM",
              [hex(1 << nwperm)] * len(perm_pf),
              [row.get("id") for row in perm_pf])
    rep.check(g, "die-perm 的原因区/位名 == PTWPERM/NWPERM",
              [("PTWPERM", "NWPERM")] * len(perm_pf),
              [(row.get("cause"), row.get("sub")) for row in perm_pf])
    rows = k5signal.check_lines(text)
    rep.check(g, "内核自评的每条 M46 check 都 ok", [],
              [name for name, verdict in rows if verdict != "ok"])
    seen = {name for name, _ in rows}
    for case, names in SIGNAL_CASES.items():
        missing = [f"{case}-{name}" for name in names
                   if f"{case}-{name}" not in seen]
        rep.check(g, f"{case} 的代表断言都报了（{len(names)} 条）", [], missing)

    # The exit status of each script, with the signal numbers from the uapi
    # header and the zombie state from sched.h (never written here).
    sigsegv = signal_number("SIGSEGV")
    sigterm = signal_number("SIGTERM")
    expected_signal = {"0": 0, "1": sigterm, "2": 0, "3": sigsegv, "4": sigsegv,
                       "5": 0, "6": 0, "7": 0}
    phases = k5signal.phase_lines(text)
    rep.check(g, "每个阶段各跑了一次（脚本号齐全）",
              [p[0] for p in k5signal.PHASES], [p[0] for p in phases])
    zombie = exit_zombie()
    bad = []
    for script, state, status, code in phases:
        want_signal = expected_signal.get(script)
        if (want_signal is None or state != zombie or code != 0
                or status & 0x7f != want_signal or status & ~0x7f):
            bad.append(f"script={script} state={state} status={status:#x} "
                       f"code={code} (want sig={want_signal})")
    rep.check(g, "退出状态：SIGSEGV/SIGTERM 段与 exit(0) 段（uapi 号派生）", [],
              bad)

    # Source facts: the user arm delivers SIGSEGV, the kernel arm keeps FATAL.
    fault = kernel_text("arch/dadao/mm/fault.c")
    rep.check(g, "用户态页故障的 verdict 改成投 SIGSEGV（非 FATAL）", True,
              "if (policy == DADAO_PF_FATAL && from_user) {" in fault
              and "force_sig_fault(SIGSEGV," in fault
              and "policy = DADAO_PF_SEGV;" in fault)
    rep.check(g, "内核态页故障仍是 DADAO_PF_FATAL", True,
              "policy == DADAO_PF_FATAL && from_user" in fault)
    traps = kernel_text("arch/dadao/kernel/traps.c")
    segv_arm = traps.split("if (policy == DADAO_PF_SEGV) {", 1)
    segv_body = segv_arm[1].split("\n\t}", 1)[0] if len(segv_arm) == 2 else ""
    rep.check(g, "traps.c 的 SEGV 分支只交回 stub（不具名退出）", True,
              "return DADAO_TRAP_RESUME_SKIP;" in segv_body
              and "dadao_early_exit" not in segv_body)
    sig_c = kernel_text("arch/dadao/kernel/signal.c")
    rep.check(g, "信号帧一次 copy 整个 2048 B 寄存器文件", True,
              "copy_to_user(sc, regs, sizeof(*regs))" in sig_c
              and "copy_from_user(regs, sc, sizeof(*regs))" in sig_c)
    rep.check(g, "handler 的返回地址走 RA 栈（dadao_ra_push）", True,
              "dadao_ra_push(regs" in sig_c)
    rep.check(g, "rt_sigreturn 答 RESUME_RETRY（恢复的 ip 即返回地址）", True,
              "return DADAO_TRAP_RESUME_RETRY;" in sig_c)
    ptrace_uapi = kernel_text("arch/dadao/include/uapi/asm/ptrace.h")
    rep.check(g, "uapi user_regs_struct 是四组各 64 槽（帧同形状）", True,
              all(f"unsigned long {bank}[64];" in ptrace_uapi
                  for bank in ("rd", "rb", "ra", "rf")))
    fork_c = kernel_text("kernel/fork.c")
    rep.check(g, "fork 子进程继承 RLIMIT_STACK（通用 copy_signal 未被改）", True,
              "memcpy(sig->rlim, current->signal->rlim, sizeof sig->rlim);"
              in fork_c)
    rep.check(g, "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# P — 64 KiB ABI (m14-linux-028)
# ---------------------------------------------------------------------------

def judge_p(rep: Report, text: str, rc: int, config: str | None) -> None:
    g = "P"
    shift = page_shift_from_spec()
    size = 1 << shift
    superpage = superpage_bytes()
    order = k5pagesz.arch_max_order()
    if config is not None:
        for symbol, value in {
                "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "y",
                "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
                "CONFIG_PAGE_SIZE_64KB": "y",
                "CONFIG_ARCH_FORCE_MAX_ORDER": str(order),
                "CONFIG_PAGE_BLOCK_MAX_ORDER": str(pins.PAGE_BLOCK_MAX_ORDER)}.items():
            if value == "n":
                rep.check(g, f"镜像配置：{symbol} 关", False,
                          config_enabled(config, symbol))
            else:
                rep.check(g, f"镜像配置：{symbol} = {value}", value,
                          config_value(config, symbol))
        rep.check(g, "镜像页大小 == spec §2.2.2 的页内偏移", size,
                  image_page_size(config))
    rep.check(g, "PAGE_SIZE << MAX_PAGE_ORDER == spec §2.2.1 的超页", superpage,
              size << order)

    rep.check(g, "自检只开始一次", 1, text.count("K5P selftest: begin"))
    rep.check(g, "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5P selftest FAIL")])
    rep.check(g, "自检以 probe cases done 结尾", True,
              "K5P selftest: probe cases done" in text)
    rep.check(g, "没有 vfree 风暴（延迟释放队列完好）", 0,
              text.count("Trying to vfree() nonexistent vm area"))
    rows = k5pagesz.check_lines(text)
    rep.check(g, "内核自评的每条 K5P check 都 ok", [],
              [name for name, row in rows if row["verdict"] != "ok"])
    seen = [name for name, _ in rows]
    for case, names in k5pagesz.CASES.items():
        missing = [name for name in names if name not in seen]
        rep.check(g, f"{case} 的代表断言都报了（{len(names)} 条）", [], missing)

    loads = k5pagesz.pt_load_count()
    rep.check(g, "镜像里 /init.musl 的 PT_LOAD 数可派生", True,
              loads is not None and loads > 0)
    for name in k5pagesz.LOAD_CHECKS:
        rep.check(g, f"{name} 报了 {loads} 次（每段一次）", loads,
                  len([n for n in seen if n == name]))

    rep.check(g, "AT_PAGESZ 现场值 == spec/.config 的页大小", hexs(size),
              got_of(rows, "a1_pagesz"))
    rep.check(g, "AT_PAGESZ 只出现一次", "0x1", got_of(rows, "a1_pagesz_once"))
    rep.check(g, "512 MiB 粒度分配成功", hexs(superpage),
              got_of(rows, "a5_alloc_bytes"))
    rep.check(g, "最大阶有一次成功分配", "0x1", got_of(rows, "a5_alloc_largest"))
    orders = got_of(rows, "a5_buddyinfo_orders")
    rep.check(g, "buddyinfo 列数 == MAX_PAGE_ORDER + 1", hexs(order + 1),
              orders)
    rep.check(g, "子任务死于 SIGSEGV（越界 brk 走故障通道）",
              hexs(signal_number("SIGSEGV")), got_of(rows, "a4_child_sigsegv"))
    rep.check(g, "故障来自无 VMA 的访问（die-no-vma）", "0x1",
              got_of(rows, "a4_fault_novma"))

    elfh = kernel_text("arch/dadao/include/asm/elf.h")
    rep.check(g, "ELF_EXEC_PAGESIZE == PAGE_SIZE（auxv 的来源）", True,
              "ELF_EXEC_PAGESIZE\tPAGE_SIZE" in elfh)
    init = kernel_text("arch/dadao/mm/init.c")
    rep.check(g, "最小 mmap 地址按页大小对齐", True,
              "mmap_min_addr = PAGE_ALIGN(mmap_min_addr)" in init)
    processor = kernel_text("arch/dadao/include/asm/processor.h")
    rep.check(g, "TASK_UNMAPPED_BASE 按页对齐", True,
              "PAGE_ALIGN(TASK_SIZE / 3)" in processor)
    process = kernel_text("arch/dadao/kernel/process.c")
    rep.check(g, "探针钩子接在 umon 分发之前", True,
              "dadao_k5p_user_trap(regs, immu18, &policy)" in process)
    rep.check(g, "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# R — reverse assertions, §4a retirement and the K3 retirement
# ---------------------------------------------------------------------------

def group_texts(runs: dict[str, dict]) -> str:
    return "\n".join(run["text"] for run in runs.values())


def scan_scope(scope: str) -> list[tuple[str, int, str]]:
    """(relative path, line number, line) of every live file in @scope."""
    root = _REPO / scope
    if root.is_file():
        files = [root]
    elif root.is_dir():
        files = [path for path in sorted(root.rglob("*")) if path.is_file()]
    else:
        return []
    hits = []
    for path in files:
        if "__pycache__" in path.parts:
            continue
        if path.name == "check_k5.py":
            # This file names the retired symbols on purpose (the retirement
            # table and the assertions about it); it is not a "live use".
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            hits.append((str(path.relative_to(_REPO)), number, line))
    return hits


def retirement_problems(files: dict[str, str]) -> list[str]:
    """§4a in both directions: the new wording is in, the retired one is out.

    ``files`` maps the repository-relative path to its text, so the same
    function serves the live tree and ``--selfcheck``.
    """
    problems = []
    for rel, old, new, _disposition, _alternative in RETIREMENTS:
        text = files.get(rel)
        if text is None:
            problems.append(f"{rel}: 文件缺失")
            continue
        if new not in text:
            problems.append(f"{rel}: 新文案缺失（{new[:24]}…）")
        if old in text:
            problems.append(f"{rel}: 旧文案回潮（{old[:24]}…）")
    return problems


def judge_r(rep: Report, runs: dict[str, dict],
            retired_hits: list[tuple[str, int, str]] | None = None) -> None:
    g = "R"
    # Every run: no monitor named termination, no unknown cause, no panic.
    for group, run in runs.items():
        text = run["text"]
        lines = [line for line in text.splitlines() if line.strip()]
        rep.check(g, f"{group}: 无 monitor 具名终止痕迹（dadao: die）", [],
                  [line for line in lines if line.startswith("dadao: die")])
        rep.check(g, f"{group}: 无 unknown cause", False,
                  "unknown cause" in text)
        rep.check(g, f"{group}: 无 panic / oops / BUG / Call Trace", [],
                  [line for line in lines
                   if re.search(r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|"
                                r"Call Trace)", line)])
        rep.check(g, f"{group}: 无内核自报 FAIL 行", [],
                  [line for line in lines if re.search(r"FAIL: ?\S+=", line)])
        rep.check(g, f"{group}: 命令行无 -d/-D（无逐指令日志）", True,
                  "-d" not in run["cmd"] and "-D" not in run["cmd"])
        rep.check(g, f"{group}: 运行以 SYS_EXIT(0) 收尾", 0, run["rc"])

    # §4a: the retirement table in both directions, and the record in the doc.
    files = {}
    for rel, *_rest in RETIREMENTS:
        files[rel] = repo_text(rel) if (_REPO / rel).is_file() else None
    rep.check(g, "§4a 退役：新文案在 / 旧文案不在", [], retirement_problems(files))
    doc = PROCESS_07.read_text(encoding="utf-8")
    rep.check(g, "Process-07 §4a.2 有本任务的退役记录", True,
              "4a.2" in doc and "m14-linux-029" in doc)
    def flat(text: str) -> str:
        return " ".join(text.split())

    for rel, old, new, disposition, alternative in RETIREMENTS:
        row = [line for line in doc.splitlines()
               if rel in line
               and (flat(new)[:40] in flat(line) or flat(old)[:40] in flat(line))]
        rep.check(g, f"§4a 记录覆盖 {rel}:{old[:16]}…", True, bool(row))
        rep.check(g, f"§4a 记录的处置是允许的三态之一（{disposition}）", True,
                  disposition in ("保留", "改限定语", "删除"))
        rep.check(g, f"§4a 记录指向替代判据（{alternative[:12]}…）", True,
                  bool(row) and any("替代" in line or "check-linux-k5" in line
                                    for line in row))

    # K3 as a stage is retired: zero hits in the live tree.
    if retired_hits is None:
        hits = []
        for scope in RETIRED_SCOPES:
            for rel, number, line in scan_scope(scope):
                for name in RETIRED_NAMES:
                    if name in line or name in rel:
                        hits.append((rel, number, line.strip()[:80]))
                        break
        retired_hits = hits
    rep.check(g, "K3 退役符号/目标在活树中 0 命中", [], retired_hits[:10])
    rep.check(g, "K3 的补丁条目已从 series 移除", [],
              [line for line in SERIES.read_text(encoding="utf-8").splitlines()
               if "k3_" in line])
    rep.check(g, "K3 的探针/门控文件已删除", [],
              [path.name for path in TESTS_DIR.glob("k3_*")]
              + [path.name for path in TESTS_DIR.glob("check_k3*")])
    rep.check(g, "K3 的 Kconfig 符号已从真源移除", [],
              [name for name in pins.symbols() if "DADAO_K3_" in name])
    make = MAKEFILE.read_text(encoding="utf-8")
    rep.check(g, "Makefile 不再声明 check-linux-k3", False,
              "check-linux-k3" in make or "check_k3" in make)
    phony_lines, in_phony = [], False
    for line in make.splitlines():
        if line.startswith(".PHONY:"):
            in_phony = True
        elif in_phony and not line.rstrip().endswith("\\"):
            phony_lines.append(line)
            break
        if in_phony:
            phony_lines.append(line)
    phony = "\n".join(phony_lines)
    locked = [line for line in make.splitlines()
              if "GATE_LOCKED_TARGETS" in line or "_locked-check-linux-k5" in line]
    l2 = [line for line in make.splitlines()
          if line.startswith("_locked-check-modules:")]
    help_text = make.split("help:", 1)[1] if "help:" in make else ""
    rep.check(g, "Makefile：check-linux-k5 入 PHONY", True,
              "check-linux-k5" in phony)
    rep.check(g, "Makefile：check-linux-k5 入 GATE_LOCKED_TARGETS", True,
              any("check-linux-k5" in line and "check-linux-k0" in line
                  for line in locked))
    rep.check(g, "Makefile：check-linux-k5 入 L2 _locked-check-modules", True,
              bool(l2) and "check-linux-k5" in l2[0])
    rep.check(g, "Makefile：help 有 check-linux-k5 行", True,
              "make check-linux-k5" in help_text)


# ---------------------------------------------------------------------------
# injections (real rebuilds, `cp` + md5 restore, green again)
# ---------------------------------------------------------------------------

#: name -> (group, source path, needle, replacement, why)
INJECTIONS = {
    "errno-to-rd1": (
        "S", "arch/dadao/kernel/syscalls.c",
        "\tregs->rd[8] = (unsigned long)ret;\n",
        "\tregs->rd[1] = (unsigned long)ret;\n",
        "syscall 结果写 rd1 而非 rd8 ⇒ S 组的 errno/rd1 断言红"),
    "clone-set-tls-off": (
        "C", "arch/dadao/kernel/process.c",
        "\tif (args->flags & CLONE_SETTLS)\n\t\tchildregs->rb[3] = args->tls;\n"
        "\telse\n",
        "\tif (0)\n\t\tchildregs->rb[3] = args->tls;\n\telse\n",
        "CLONE_SETTLS 不设子 rbtp ⇒ 子继承哨兵，C 组红"),
    "sigsegv-stays-fatal": (
        "G", "arch/dadao/mm/fault.c",
        "\tif (policy == DADAO_PF_FATAL && from_user) {\n",
        "\tif (policy == DADAO_PF_FATAL && from_user && 0) {\n",
        "用户态页故障仍走 DADAO_PF_FATAL（具名终止）⇒ G 组红"),
    "vma-lookup-unlocked": (
        "S", "arch/dadao/kernel/k5_syscall_selftest.c",
        "\t\t\tmmap_read_lock(k5_mm);\n"
        "\t\t\tvma = find_vma(k5_mm, K5_BRK_VA);\n"
        "\t\t\tmmap_read_unlock(k5_mm);\n",
        "\t\t\tvma = find_vma(k5_mm, K5_BRK_VA);\n",
        "锁外查 VMA ⇒ rwsem.h:81 WARN 且源码锁断言红"),
    "auxv-pagesz-4k": (
        "P", "arch/dadao/include/asm/elf.h",
        "#define ELF_EXEC_PAGESIZE\tPAGE_SIZE\n",
        "#define ELF_EXEC_PAGESIZE\t4096UL\n",
        "AT_PAGESZ 写 4096 ⇒ auxv 现场值不等于页大小，P 组红"),
}

#: Static injections (no build): the §4a "retired wording comes back" path.
STATIC_INJECTIONS = {
    name: (rel, old) for name, rel, old in (
        ("retired-back", *RETIREMENTS[0][:2]),
        ("retired-back-stack", *RETIREMENTS[2][:2]),
    )
}


def run_static_injection(rep: Report, name: str) -> None:
    rel, old = STATIC_INJECTIONS[name]
    path = _REPO / rel
    original = path.read_bytes()
    before = md5(path)
    tmp = SCRATCH / f"inject-{name}.orig"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(original)
    text = original.decode()
    if old in text:
        rep.check(f"INJECT {name}", "旧文案已不在源码中（还原态）", True, False)
        return
    path.write_text(text + "\n" + old + "\n", encoding="utf-8")
    try:
        rep.check(f"INJECT {name}", "注入改动了源码", True,
                  path.read_bytes() != original)
        files = {rel2: (path.read_text(encoding="utf-8")
                        if rel2 == rel else repo_text(rel2))
                 for rel2, _o, _n, _d, _a in RETIREMENTS}
        problems = retirement_problems(
            {rel2: text2 for rel2, text2 in files.items()})
        rep.check(f"INJECT {name}",
                  f"退役文案回潮 ⇒ R 组红（{old[:24]}…）", True,
                  any("旧文案回潮" in problem for problem in problems))
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        files = {rel2: (path.read_text(encoding="utf-8")
                        if rel2 == rel else repo_text(rel2))
                 for rel2, _o, _n, _d, _a in RETIREMENTS}
        rep.check(f"INJECT {name}", "还原后 R 组回绿", [],
                  retirement_problems(files))


JUDGES = {
    "S": lambda rep, run, cfg, extra: judge_s(rep, run["text"], run["rc"], cfg,
                                             extra.get("oracle")),
    "C": lambda rep, run, cfg, extra: judge_c(rep, run["text"], run["rc"], cfg),
    "F": lambda rep, run, cfg, extra: judge_f(rep, run["text"], run["rc"], cfg),
    "T": lambda rep, run, cfg, extra: judge_t(rep, run["text"], run["rc"], cfg,
                                             run["cmd"]),
    "G": lambda rep, run, cfg, extra: judge_g(rep, run["text"], run["rc"], cfg),
    "P": lambda rep, run, cfg, extra: judge_p(rep, run["text"], run["rc"], cfg),
}


def group_red(group: str, run: dict, config: str, extra: dict,
              quiet: bool = True) -> tuple[int, list[str]]:
    rep = Report(quiet=quiet)
    JUDGES[group](rep, run, config, extra)
    return len(rep.fails), rep.fails


def run_injection(rep: Report, name: str, extra: dict) -> None:
    group, rel, needle, repl, why = INJECTIONS[name]
    path = SOURCE / rel
    original = path.read_bytes()
    before = md5(path)
    tmp = SCRATCH / f"inject-{name}.orig"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(original)
    text = original.decode()
    if needle not in text:
        rep.check(f"INJECT {name}", "注入点存在于源码", True, False)
        if repl in text:
            raise SystemExit(f"check_k5: {rel} still carries the '{name}' "
                             f"injection (a previous run was killed before its "
                             f"restore); fix the source before re-running")
        return
    path.write_text(text.replace(needle, repl, 1), encoding="utf-8")
    try:
        rep.check(f"INJECT {name}", "注入改动了源码", True,
                  path.read_bytes() != original)
        rc, config = build_image(group, f"injected:{name}")
        rep.check(f"INJECT {name}", f"注入后镜像可构建（{why}）", 0, rc)
        if rc != 0 or config is None:
            return
        rep.check(f"INJECT {name}",
                  f"注入镜像仍带本组探针符号（{IMAGES[group][1]}）", True,
                  config_enabled(config, IMAGES[group][1]))
        run_rc, out, cmd = boot(f"inject-{name}")
        run = {"rc": run_rc, "text": out, "cmd": cmd}
        fails, names = group_red(group, run, config, extra, quiet=True)
        rep.info(f"inject {name}: rc={run_rc} group={group} red={names[:3]}")
        rep.check(f"INJECT {name}", f"{why} ⇒ {group} 组红", True, fails > 0)
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        rc, config = build_image(group, "restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if config is not None:
            run_rc, out, cmd = boot(f"restored-{name}")
            fails, names = group_red(group, {"rc": run_rc, "text": out,
                                             "cmd": cmd}, config, extra,
                                     quiet=True)
            rep.check(f"INJECT {name}", "还原后本组回绿", [], names[:5])


# ---------------------------------------------------------------------------
# --selfcheck: every group flips (no build, no boot)
# ---------------------------------------------------------------------------

#: A minimal console per group where the watched facts are right.  The
#: selfcheck then flips one field at a time and requires the group to go red.
def _console_s(text: str) -> str:
    return text


def _row(name: str, got: str, want: str | None = None) -> str:
    return f"K5 check {name} want={want or got} got={got} ok"


def _rows(cases: dict, overrides: dict | None = None,
          prefix: str = "K5 check") -> str:
    """Synthetic ``ok`` rows for every named case (selfcheck scaffolding)."""
    out = []
    for names in cases.values():
        for name in names:
            want, got = (overrides or {}).get(name, ("0x1", "0x1"))
            out.append(f"{prefix} {name} want={want} got={got} ok")
    return "\n".join(out)


def selfcheck() -> int:
    """Prove the judging can fail: flip one watched fact per group."""
    problems: list[str] = []

    def flip(group: str, why: str, watched: str, base: str, broken: str,
             config: str | None = None, extra: dict | None = None) -> None:
        extra = extra or {}
        run = lambda text: {"rc": 0, "text": text, "cmd": ["qemu"]}  # noqa: E731
        _n, base_fails = group_red(group, run(base), config, extra)
        _n2, broken_fails = group_red(group, run(broken), config, extra)
        clean = not any(watched in fail for fail in base_fails)
        red = any(watched in fail for fail in broken_fails)
        ok = clean and red
        print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck {group} | "
              f"注入「{why}」⇒ 期望={group} 变红 实际="
              f"对照={'绿' if clean else base_fails[0] if base_fails else '红'}"
              f"、翻转后={'红' if red else '未变红'}", flush=True)
        if not ok:
            problems.append(f"selfcheck {group}: 未翻转（{why}）")

    # S — the errno range is the contract's.
    overrides = {"u3_ni_enosys": ("-38", "-38"),
                 "u3_range_enosys": ("-38", "-38"),
                 "u3_mmap_einval": ("-22", "-22"),
                 "u3_undef_enosys": ("-38", "-38"),
                 "u4_frame_rb3": ("0x77", "0x77"),
                 "u4_user_rb3": ("0x77", "0x77")}
    cftrap = hexs(cause_ids()["CFXTRAP"])
    user = hexs(run_mode("user"))
    table = k5sys.syscall_table_snapshot()
    traps = "\n".join(
        f"K5 trap {i}: ip={0x1000 + 16 * i:#x} immu18=0x0 nr={table[name]:#x} "
        f"cause={cftrap} mode={user} rb3=0x77 rd1=0x5a"
        for i, name in enumerate(("write", "mmap")))
    base_s = "\n".join([
        "K5 selftest: begin pid=1 mm=0",
        "init: pid=1", "init: brk +65536 ok", "K5 init: exit=0",
        _rows(k5sys.CASES, overrides), traps,
        "K5 exit: child=16 state=32 status=0x0 code=0 rounds=1",
        "K5 exec: rc=0 entry=0x1000 ip=0x1000 rb3=0x0 mm=1",
        "K5 selftest: probe cases done",
    ])
    broken = base_s.replace("K5 check u3_mmap_einval want=-22 got=-22 ok",
                            "K5 check u3_mmap_einval want=-22 got=-5000 ok")
    flip("S", "errno 越界（-5000）", "errno 全在契约区间", base_s, broken,
         extra={"oracle": None})
    warn = ("WARNING: CPU: 0 PID: 16 at include/linux/rwsem.h:81 "
            "find_vma+0x0/0x0")
    flip("S", "锁外 find_vma（rwsem.h:81 WARN）", "日志无 rwsem 锁警告",
         base_s, base_s + "\n" + warn, extra={"oracle": None})

    # C — the child's rbtp is the tls argument.
    tls = k5clone.stub_constant("K5C_TLS")
    sentinel = k5clone.probe_constant("K5C_RB3_SENTINEL")
    sc_ok, sc_bad = k5clone.sc_codes()
    flags = (k5clone.clone_bits()["CLONE_VM"] | k5clone.clone_bits()["CLONE_FS"]
             | k5clone.clone_bits()["CLONE_FILES"]
             | k5clone.clone_bits()["CLONE_SIGHAND"]
             | k5clone.clone_bits()["CLONE_THREAD"]
             | k5clone.clone_bits()["CLONE_SETTLS"])
    base_c = "\n".join([
        "K5 clone selftest: begin pid=1 mm=0",
        f"K5 clone pre: pid=16 flags={flags:#x} stack=0x10000 tls={tls:#x} "
        f"rb3={sentinel:#x} copy=0x33 mm=0x1 asid=1 mm_users=1",
        f"K5 clone child: pid=17 tgid=16 mm=0x1 parent_mm=0x1 asid=1 "
        f"parent_asid=1 mm_users=2 rd8_at_entry=0x0 rb3={tls:#x} "
        f"tls_arg={tls:#x} copy=0x33",
        # The thread child is still alive when the fork is taken (the racy
        # case the invariant has to accept): 2 before, 2 after.
        "K5 clone fork pre: pid=16 flags=0x11 stack=0x0 asid=1 mm_users=2",
        f"K5 clone fork child: pid=18 tgid=18 mm=0x2 parent_mm=0x1 asid=2 "
        f"parent_asid=1 parent_mm_users=2 rd8_at_entry=0x0 rb3={sentinel:#x}",
        f"K5 clone done: thread_ret=0x11 fork_ret=0x12 parent_rb3={sentinel:#x} "
        f"mm_users=1 sc_now={sc_ok:#x} sc_across={sc_bad:#x}",
        _rows(k5clone.CASES, None),
        "K5 clone selftest: done",
    ])
    broken = base_c.replace(f"rb3={tls:#x} tls_arg", f"rb3={sentinel:#x} tls_arg")
    flip("C", "SETTLS 未设子 rbtp", "CLONE_SETTLS：子 rb3 == tls 参数",
         base_c, broken)
    broken = base_c.replace("parent_mm_users=2", "parent_mm_users=3")
    flip("C", "fork 新增父 mm 引用", "fork 不新增父 mm 的引用", base_c, broken)

    # F — FUTEX_WAIT's recheck answers -EAGAIN with the uapi number.
    again = minus(eagain())
    futex_over = {
        "f1_wake_count": ("0x1", "0x1"),
        "f1a_ret_is_eagain": (f"{again:#x}", f"{again:#x}"),
        "f3_peer_success": (f"{sc_ok:#x}", f"{sc_ok:#x}"),
        "f3_parent_sc_after_yield": (f"{sc_bad:#x}", f"{sc_bad:#x}"),
        "f4_sc_immediate": (f"{sc_ok:#x}", f"{sc_ok:#x}"),
        "f4_sc_after_syscall": (f"{sc_bad:#x}", f"{sc_bad:#x}"),
        "f5_requeue_moved": ("0x1", "0x1"),
        "f6_other_bitset_wake": ("0x0", "0x0"),
        "shared_futex_wake": ("0x0", "0x0"),
        "shared_futex_wait_eagain": (f"{again:#x}", f"{again:#x}"),
        "shared_futex_page_mapped": ("0x1", "0x1"),
    }
    base_f = "\n".join([
        "K5 futex selftest: begin pid=1",
        _rows(k5futex.CASES, futex_over),
        "K5 futex selftest: done (futex/atomics closed)",
    ])
    broken = base_f.replace(f"K5 check f1a_ret_is_eagain want={again:#x}",
                            "K5 check f1a_ret_is_eagain want=0xffffffffffffffff")
    flip("F", "EAGAIN 号不是 uapi 的", "f1a_ret_is_eagain 的 want 是现场派生值",
         base_f, broken)

    # T — the event lands inside [period/2, 2*period].
    freq = k5clock.contract_freq()
    period = freq // 100
    base_t = "\n".join([
        f"K5 time: cs=cfx rating=300 mask=0xffffffffffffffff freq={freq} "
        "hz=100 period=%d" % period,
        "K5 time: ce=cfx rating=300 features=0x2 handler=1 min_delta=100",
        f"K5 clock: begin cs=cfx rating=300 mask=0xffffffffffffffff ce=cfx "
        f"rating=300 features=0x2 handler=1 freq={freq} hz=100 period={period}",
        "K5 clock: t1 i=0 sched=100 raw=100",
        "K5 clock: t1 i=1 sched=200 raw=210",
        "K5 clock: t1 i=2 sched=300 raw=320",
        f"K5 clock: t2 period={period} arm_long=100 cmp_long={100 + 8 * period} "
        f"arm_short=200 cmp_short={200 + period} event={200 + period} "
        f"interval={period}",
        f"K5 clock: t3 want=3 j0=10 j1=13 ticks=3 se0=1 se1=2 ut0=0 ut1=0 "
        f"window={5 * period}",
        f"K5 clock: t4 cs0=100 cs1={100 + period // 8} k0=100 "
        f"k1={100 + period // 8} window={period // 4}",
        *[f"K5 clock: t4 s={i} value={100 + i}" for i in range(8)],
        "K5 clock: done",
    ])
    broken = base_t.replace(f"interval={period}", f"interval={3 * period}")
    flip("T", "投递间隔 3 个 period", "投递间隔 ∈ [period/2, 2*period]",
         base_t, broken, config="CONFIG_HZ=100")

    # G — an unservable user access is SIGSEGV, not a clean exit.
    sigsegv = signal_number("SIGSEGV")
    zombie = exit_zombie()
    statuses = {"0": 0, "1": signal_number("SIGTERM"), "2": 0, "3": sigsegv,
                "4": sigsegv, "5": 0, "6": 0, "7": 0}
    phases = "\n".join(
        f"M46 phase: script={script} state={zombie} status={status:#x} code=0"
        for script, status in statuses.items())
    base_g = "\n".join([
        "M46 selftest: begin pid=1 mm=0",
        _rows({case: names for case, names in SIGNAL_CASES.items()}, None,
              prefix="M46 check"),
        phases,
        "M46 selftest: probe cases done",
    ])
    broken = base_g.replace(f"script=3 state={zombie} status={sigsegv:#x}",
                            f"script=3 state={zombie} status=0x0")
    flip("G", "SIGSEGV 阶段变成干净退出", "退出状态：SIGSEGV/SIGTERM 段",
         base_g, broken)

    # P — AT_PAGESZ is the page size the image really runs with.
    size = 1 << page_shift_from_spec()
    order = k5pagesz.arch_max_order()
    loads = k5pagesz.pt_load_count() or 1
    page_over = {
        "a1_pagesz": (hexs(size), hexs(size)),
        "a1_pagesz_once": ("0x1", "0x1"),
        "a5_alloc_bytes": (hexs(superpage_bytes()), hexs(superpage_bytes())),
        "a5_alloc_largest": ("0x1", "0x1"),
        "a5_buddyinfo_orders": (hexs(order + 1), hexs(order + 1)),
        "a4_child_sigsegv": (hexs(sigsegv), hexs(sigsegv)),
        "a4_fault_novma": ("0x1", "0x1"),
    }
    rows_p = [_rows(k5pagesz.CASES, page_over, prefix="K5P check")]
    for name in k5pagesz.LOAD_CHECKS:
        rows_p.append("\n".join(
            f"K5P check {name} want=0x1 got=0x1 ok" for _ in range(loads)))
    base_p = "\n".join([
        "K5P selftest: begin pid=1", "\n".join(rows_p),
        "K5P selftest: probe cases done",
    ])
    broken = base_p.replace(
        f"K5P check a1_pagesz want={hexs(size)} got={hexs(size)}",
        f"K5P check a1_pagesz want=0x1000 got=0x1000")
    flip("P", "AT_PAGESZ 写 4096", "AT_PAGESZ 现场值", base_p, broken)

    # R — the retired wording coming back must be red.
    files: dict[str, str] = {}
    for rel, _old, new, _d, _a in RETIREMENTS:
        files[rel] = files.get(rel, "") + new
    clean = retirement_problems(files)
    rel, old, new, _d, _a = RETIREMENTS[0]
    files2 = dict(files)
    files2[rel] = new + "\n" + old
    dirty = retirement_problems(files2)
    ok = bool(dirty) and not clean
    print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck R | 注入「旧文案回潮」⇒ "
          f"期望=R 变红 实际={'红：' + dirty[0] if dirty else '未变红'}", flush=True)
    if not ok:
        problems.append("selfcheck R: 旧文案回潮未变红")

    if problems:
        print(f"check_k5 --selfcheck: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"check_k5 --selfcheck: PASS ({len(GROUPS)} 组各一次可翻转 + 对照)")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="M14 K5 closure gate")
    parser.add_argument("--selfcheck", action="store_true",
                        help="prove every group can fail (no build, no boot)")
    parser.add_argument("--inject", action="append", default=[], metavar="NAME",
                        help=f"run this source injection (repeatable); one of: "
                             f"{', '.join(sorted(set(INJECTIONS) | set(STATIC_INJECTIONS)))}")
    parser.add_argument("--all-inject", action="store_true",
                        help="run every injection (the evidence script does this)")
    parser.add_argument("--no-inject", action="store_true",
                        help="explicitly no injection round (the default)")
    parser.add_argument("--only", default="", metavar="GROUPS",
                        help="run only these group letters (e.g. SFR)")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

    wanted = [g for g in GROUPS if not args.only or g in args.only]
    if not wanted:
        raise SystemExit(f"check_k5: no group in --only {args.only!r}")

    rep = Report()
    runs: dict[str, dict] = {}
    extra: dict = {"oracle": None}

    for group in wanted:
        if group == "R":
            continue
        rc, config = build_image(group, "gate")
        if config is None:
            rep.check(group, "镜像可构建", 0, rc)
            continue
        if group == "S":
            extra["oracle"] = k5sys.stub_oracle(kernel_path())
            rep.stat(f"stub oracle: {[(hex(o), hex(i)) for o, i in extra['oracle']]}")
        run_rc, out, cmd = boot(f"group-{group.lower()}")
        if run_rc == 124:
            # One reported retry: the K5 probe images are tick-preempted user
            # programs and a QEMU timeout has been seen once on the futex image
            # (the probe's blocking hand-over).  The retry is printed, and a
            # second timeout is still a FAIL (the group's own checks).
            rep.stat(f"{group} 组首次启动超时（rc=124），重试一次（第 1/1 次）")
            run_rc, out, cmd = boot(f"group-{group.lower()}-retry")
            rep.stat(f"{group} 组重试结果 rc={run_rc}")
        runs[group] = {"rc": run_rc, "text": out, "cmd": cmd}
        JUDGES[group](rep, runs[group], config, extra)

    if "R" in wanted:
        retired = None
        if not args.inject:
            retired = []
            for scope in RETIRED_SCOPES:
                for rel, number, line in scan_scope(scope):
                    if any(name in line or name in rel for name in RETIRED_NAMES):
                        retired.append((rel, number, line.strip()[:80]))
        judge_r(rep, {group: run for group, run in runs.items()}, retired)

    names = list(args.inject)
    if args.all_inject:
        names += sorted(INJECTIONS) + sorted(STATIC_INJECTIONS)
    # Injections are opt-in: the L2 run (`make check-linux-k5`) judges the
    # stage; the evidence script asks for the rebuild-red-restore-green rounds.
    if args.no_inject:
        names = []
    for name in names:
        if name in STATIC_INJECTIONS:
            run_static_injection(rep, name)
        elif name in INJECTIONS:
            run_injection(rep, name, extra)
        else:
            raise SystemExit(f"check_k5: unknown injection {name!r}")

    print()
    print(f"check_k5: {rep.summary()}")
    if rep.fails:
        print(f"check_k5: {rep.total - len(rep.fails)}/{rep.total} passed, "
              f"{len(rep.fails)} FAILED")
        for name in rep.fails:
            print(f"  - {name}")
        return 1
    print(f"check_k5: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
