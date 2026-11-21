#!/usr/bin/env python3
"""k5_futex_probe.py — M14 K5 futex / user-atomic probe (`m14-linux-025`).

The kernel side is `arch/dadao/kernel/k5_futex_selftest.c` (+ the user program
in `kernel/trap.S`, the arch futex atomics in `include/asm/futex.h`), built as a
probe image with `CONFIG_DADAO_K5_FUTEX_SELFTEST`; this gate builds that image,
boots it on Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from
(contract-syscall §11, spec/SimRISC-12 §1, `futex(2)`, `include/uapi/linux/futex.h`):

  F1  `FUTEX_WAIT`'s "check the user word, then sleep" is atomic and a wake is
      never lost: one waiter sleeps, `WAKE(1)` returns 1 and the waiter returns
      0.  The hand-over is serialized by the kernel side, so "the waiter was
      asleep" is an observed fact (`f1_waiter_awake` reads its scheduler state)
      rather than a race the probe hopes to win.
  F1A the same pair with the word changed *before* the call: the wait must
      return `-EAGAIN` (the recheck under the hash-bucket lock).  `EAGAIN` and
      the `-errno` shape are read from `asm-generic/errno-base.h`, not written
      here.
  F2  `WAKE(n)` wakes exactly n of three waiters: `WAKE(2)` returns 2 and takes
      exactly two out of the sleeping state (counted on the spot), the third is
      still asleep and reports only after `WAKE(1)`.
  F3  two threads raise the same compare-and-exchange: exactly one stores; the
      loser's `sc` fails (`sc`'s success/failure values come from
      `spec/SimRISC-12 §1`) and its retry re-reads and stores nothing.
  F4  `lr`…`sc` cannot cross a syscall: the immediate pair succeeds, the pair
      with a `trap` in between fails *and stores nothing* — an exception entry
      clears the hart's reservation (§1「保留机制」, §11).
  F5  `FUTEX_REQUEUE` moves a waiter without waking it (`futex_requeue()`
      answers woken+requeued; one waiter moved) and a later `WAKE` on the
      destination reaches it.
  F6  `WAIT_BITSET`/`WAKE_BITSET` match on the bitset: a non-matching wake
      returns 0 and leaves the waiter asleep, the matching one takes it.

Two more derivations the gate makes on its own:

  * **the arguments the program really sent.**  The child lines carry the
    syscall it issued (`op`, `val`, `uaddr`, `bitset`).  The expected
    `(script, uaddr)` sequence is parsed out of the stub's clone blocks
    (`set.rd rd12, K5F_DATA_VA + K5F_W_*` then the script in `rd18`), and every
    `op` is compared with `include/uapi/linux/futex.h`'s `FUTEX_*` plus
    `FUTEX_PRIVATE_FLAG`.  A wrong argmask slot or a stale word would show up
    here even though the kernel's own checks passed.
  * **the syscalls the program made.**  The number of `nr=…` trap lines must
    equal the count of `K5F_SYS_FUTEX` / `K5F_SYS_CLONE` / `K5F_SYS_EXIT`
    loads in the stub; the numbers themselves come from the locked
    `syscall.tbl` snapshot (contract-syscall §1.2).

Exit status: 0 = every case passed; 1 = at least one FAIL; 2 = an input could
not be derived (kernel source / build tree / toolchain / spec missing).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                          # noqa: E402
from tools.linux import make_defconfig as defconfig           # noqa: E402
from tools.linux import paths as linux_paths                  # noqa: E402
from tests.unit.linux.k5_syscall_probe import (                    # noqa: E402
    Report, config_enabled, config_value, kernel_text, kv, md5, one,
    symbols, syscall_table_snapshot, table_slot, tool,
)
from tools.qemu import k0_boot_probe as k0                    # noqa: E402

SCRATCH = (Path(os.environ.get("K5F_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-025") / "check-linux-k5-futex")
SOURCE = linux_paths.linux_source_dir()
SPEC_ATOMIC = _REPO / "spec" / "SimRISC-12-其它指令.md"
SPEC_ATOMIC_GLOB = "SimRISC-12*.md"
FUTEX_H = "include/uapi/linux/futex.h"
ERRNO_BASE_H = "include/uapi/asm-generic/errno-base.h"
SCHED_H = "include/uapi/linux/sched.h"
TRAP_S = "arch/dadao/kernel/trap.S"
PROBE_C = "arch/dadao/kernel/k5_futex_selftest.c"
FUTEX_ARCH_H = "arch/dadao/include/asm/futex.h"
WAITWAKE_C = "kernel/futex/waitwake.c"
FORK_C = "kernel/fork.c"
REQUEUE_C = "kernel/futex/requeue.c"
QEMU_INT_H = "target/dadao/helper.c"

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
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "y",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

TIMEOUT_BUILD = int(os.environ.get("K5F_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K5F_QEMU_TIMEOUT", "240"))
TIMEOUT_QEMU_BUILD = int(os.environ.get("K5F_QEMU_BUILD_TIMEOUT", "2400"))
JOBS = os.environ.get("JOBS", "32")

#: The check names each case must report (`K5 check <name> ...`).
CASES = {
    "F1": ("f1_wake_count", "f1_waiter_awake", "f1_waiter_script",
           "f1_waiter_word", "f1_waiter_reported", "f1_waiter_ret"),
    "F1A": ("f1a_waiter_returned", "f1a_waiter_script", "f1a_word",
            "f1a_ret_is_eagain", "f1a_read_before_change"),
    "F2": ("f2_armed", "f2_waiter_script", "f2_wake_count", "f2_awake",
           "f2_reported", "f2_reported_ret", "f2_left_asleep",
           "f2b_left_waiter", "f2b_wake_count", "f2b_left_awake",
           "f2b_reported", "f2b_reported_ret"),
    "F3": ("f3_parent_sc_after_yield", "f3_parent_retry_value",
           "f3_parent_retry_stored", "f3_word", "f3_peer_success",
           "f3_peer_value_seen", "f3_peer_word", "f3_peer_script"),
    "F4": ("f4_sc_immediate", "f4_sc_value", "f4_sc_after_syscall",
           "f4_word_after_crossing"),
    "F5": ("f5_requeue_moved", "f5_waiter_still_asleep", "f5_waiter_script",
           "f5_wake_on_destination", "f5_waiter_awake", "f5_waiter_reported",
           "f5_waiter_ret"),
    "F6": ("f6_other_bitset_wake", "f6_waiter_still_asleep",
           "f6_waiter_bitset", "f6_bitset_wake", "f6_waiter_awake",
           "f6_waiter_reported", "f6_waiter_ret"),
    "F8": ("f8_wakeop_count", "f8_op_word", "f8_waiter_script",
           "f8_waiter_awake", "f8_waiter_reported", "f8_waiter_ret"),
    "F7": ("f7_clear_tid_ptr", "f7_mm_users_gt1", "f7_tid_cleared",
           "f7_child_script", "f7_child_reported", "shared_futex_wake",
           "shared_futex_wait_eagain", "shared_futex_page_mapped"),
}

#: Names that must appear more than once (F2's three waiters).
REPEATED = {"f2_waiter_script": 3, "f2_reported_ret": 2, "f2b_reported_ret": 3}


# ---------------------------------------------------------------------------
# derivations (never a literal: the owner of each fact is parsed)
# ---------------------------------------------------------------------------

def uapi_futex() -> dict[str, int]:
    """`include/uapi/linux/futex.h`: the FUTEX_* op numbers and the flag."""
    text = kernel_text(FUTEX_H)
    values = {}
    for name, value in re.findall(r"^#define\s+(FUTEX_\w+)\s+(\d+)\s*$", text,
                                  re.M):
        values[name] = int(value)
    need = ("FUTEX_WAIT", "FUTEX_WAKE", "FUTEX_REQUEUE", "FUTEX_WAKE_OP",
            "FUTEX_WAIT_BITSET", "FUTEX_WAKE_BITSET", "FUTEX_PRIVATE_FLAG")
    missing = [n for n in need if n not in values]
    if missing:
        raise SystemExit(f"k5_futex_probe: {FUTEX_H} lacks {missing}")

    def compound(name: str) -> int:
        m = re.search(r"^#define\s+" + name + r"\s+\((\w+) \| (\w+)\)", text,
                      re.M)
        if not m:
            raise SystemExit(f"k5_futex_probe: {FUTEX_H} lacks {name}")
        return values[m.group(1)] | values[m.group(2)]

    values["FUTEX_WAIT_BITSET_PRIVATE"] = compound("FUTEX_WAIT_BITSET_PRIVATE")
    values["FUTEX_WAKE_BITSET_PRIVATE"] = compound("FUTEX_WAKE_BITSET_PRIVATE")
    return values


def eagain() -> int:
    """`include/uapi/asm-generic/errno-base.h`: `EAGAIN`."""
    m = re.search(r"^#define\s+EAGAIN\s+(\d+)", kernel_text(ERRNO_BASE_H), re.M)
    if not m:
        raise SystemExit(f"k5_futex_probe: {ERRNO_BASE_H} has no EAGAIN")
    return int(m.group(1))


def sc_codes() -> tuple[int, int]:
    """`spec/SimRISC-12 §1`: `sc`'s destination on success and on failure.

    The two sentences are the instruction's own definition; the gate compares
    the console against these numbers instead of assuming the usual 0/1 order.
    """
    path = SPEC_ATOMIC if SPEC_ATOMIC.is_file() else next(
        (p for p in _REPO.glob(f"spec/{SPEC_ATOMIC_GLOB}")), None)
    if path is None:
        raise SystemExit("k5_futex_probe: spec/SimRISC-12 (原子指令) missing")
    text = path.read_text(encoding="utf-8")
    ok = re.search(r"设置成\s*(\d+)\s*，\s*表示写入成功", text)
    bad = re.search(r"设置成\s*(\d+)\s*，\s*表示写入失败", text)
    if not ok or not bad:
        raise SystemExit("k5_futex_probe: spec/SimRISC-12 §1 has no sc "
                         "success/failure sentence")
    return int(ok.group(1)), int(bad.group(1))


def clone_bits() -> dict[str, int]:
    """`include/uapi/linux/sched.h`: the CLONE_* bit values."""
    bits = {name: int(value, 16) for name, value in
            re.findall(r"^#define\s+(CLONE_\w+)\s+(0x[0-9a-fA-F]+)",
                       kernel_text(SCHED_H), re.M)}
    need = ("CLONE_VM", "CLONE_FS", "CLONE_FILES", "CLONE_SIGHAND",
            "CLONE_THREAD", "CLONE_SETTLS")
    missing = [n for n in need if n not in bits]
    if missing:
        raise SystemExit(f"k5_futex_probe: {SCHED_H} lacks {missing}")
    return bits


_DEFINE_RE = r"^#define\s+{name}\s+(\S+)"
_DEFINE_ALL = re.compile(r"^#define\s+(K5F_\w+)\s+(.+)$", re.M)


def _work_root() -> Path:
    """`work_root` from `manifests/components.lock.toml` (repo-relative)."""
    import tomllib
    with (_REPO / "manifests" / "components.lock.toml").open("rb") as stream:
        root = tomllib.load(stream).get("work_root")
    return _REPO / str(root)


def const_map(text: str, page_size: int = 0x10000) -> dict[str, int]:
    """Every `#define K5F_* <integer expression>` of a file, evaluated.

    Function-like macros are skipped; identifiers resolve against the map, so
    `K5F_DATA_VA = K5F_VA_BASE + 65 * K5F_PAGE` is derived from the file's own
    numbers instead of being parsed as one literal.  `PAGE_SIZE`/`K5F_PAGE`
    come from the image's 64 KiB page (asserted separately).
    """
    raw: dict[str, str] = {}
    for name, value in _DEFINE_ALL.findall(text):
        value = value.split("/*")[0].strip()
        if value.startswith("(") and re.match(r"^\(\w+\)", value):
            continue        # function-like macro
        raw[name] = value
    ns: dict[str, int] = {"PAGE_SIZE": page_size, "K5F_PAGE": page_size,
                          "UL": 1}
    for _ in range(len(raw) + 1):
        progressed = False
        for name, expr in raw.items():
            if name in ns:
                continue
            cleaned = re.sub(r"([0-9a-fA-Fx]+)[ULul]+", r"\1", expr)
            try:
                ns[name] = int(eval(cleaned, {"__builtins__": {}}, ns))  # noqa: S307 - literals only
                progressed = True
            except Exception:      # noqa: BLE001 - unresolved on this pass
                continue
        if not progressed:
            break
    return {k: v for k, v in ns.items() if k in raw}


def stub_constants() -> dict[str, int]:
    return const_map(kernel_text(TRAP_S))


def probe_constants() -> dict[str, int]:
    return const_map(kernel_text(PROBE_C))


def stub_constant(name: str) -> int:
    """A `#define <name> <integer expression>` of the user program."""
    values = stub_constants()
    if name not in values:
        raise SystemExit(f"k5_futex_probe: {TRAP_S} has no evaluable {name}")
    return values[name]


def probe_constant(name: str) -> int:
    """A `#define <name> <integer expression>` of the kernel half."""
    values = probe_constants()
    if name not in values:
        raise SystemExit(f"k5_futex_probe: {PROBE_C} has no evaluable {name}")
    return values[name]


def stub_block() -> str:
    text = kernel_text(TRAP_S)
    start = text.index("dadao_k5f_user_stub:")
    end = text.index("dadao_k5f_user_stub_end:")
    return text[start:end]


def stub_threads() -> list[tuple[str, str]]:
    """The (script, word-expression) of every `clone` the program issues.

    A clone block loads the child's futex word address into `rd12` and its
    script into `rd18`; the kernel hands the script to the child through
    `CLONE_SETTLS` (`rb3`).  Walking the stub in order is what makes the
    expected `(script, uaddr)` sequence a *derivation* instead of a copy of
    what the console reported.
    """
    out: list[tuple[str, str]] = []
    word: str | None = None
    for line in stub_block().splitlines():
        line = line.split("/*")[0].strip()
        m = re.match(r"set\.rd\s+rd12,\s*(.+)$", line)
        if m:
            word = m.group(1).strip()
            continue
        m = re.match(r"set\.rd\s+rd18,\s*K5F_SCRIPT_(\w+)$", line)
        if m and word is not None:
            out.append((m.group(1), word))
    return out


def f2_waiters(threads: list[tuple[str, str]]) -> int:
    """How many threads the program parks on F2's word: measured, not pinned."""
    return sum(1 for script, word in threads
               if script == "WAIT_F1" and word.endswith("K5F_W_F2"))


def stub_count(pattern: str) -> int:
    return len(re.findall(pattern, stub_block(), re.M))


def child_lines(text: str) -> list[dict[str, str]]:
    out = []
    for line in text.splitlines():
        if line.startswith("K5 futex child:"):
            out.append(kv(line))
    return out


def reg_lines(text: str) -> list[dict[str, str]]:
    return [kv(line) for line in text.splitlines()
            if line.startswith("K5 futex reg:")]


def check_lines(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"^K5 check (\S+) want=(\S+) got=(\S+) (.*?)(ok|FAIL)$",
                     line.strip())
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(5)}))
    return out


def trap_lines(text: str) -> list[dict[str, str]]:
    return [kv(line) for line in text.splitlines()
            if line.startswith("K5 futex trap ")]


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def qemu_binary() -> str:
    """The emulator to boot; `K5F_QEMU` lets an injection run its own build."""
    override = os.environ.get("K5F_QEMU")
    if override:
        return override
    return tool("qemu-system-dadao")


def build_image(label: str = "k5f") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k5_futex_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k5_futex_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def build_qemu() -> int:
    print("[INFO] rebuild qemu-system-dadao (one file touched)", flush=True)
    try:
        proc = subprocess.run(["make", "build-qemu", f"JOBS={JOBS}"],
                              cwd=str(_REPO), capture_output=True, text=True,
                              timeout=TIMEOUT_QEMU_BUILD)
    except subprocess.TimeoutExpired:
        return 124
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k5f.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k5_futex_probe: {kernel} missing")
    qemu = qemu_binary()
    if not os.access(qemu, os.X_OK):
        raise SystemExit(f"k5_futex_probe: {qemu} missing/unusable")
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

def judge(rep: Report, text: str, rc: int, suffix: str = "") -> None:
    s = suffix
    futex = uapi_futex()
    sc_ok, sc_bad = sc_codes()
    bits = clone_bits()
    threads = stub_threads()
    f2_n = f2_waiters(threads)
    table = syscall_table_snapshot()

    rep.check(f"B{s}", "镜像跑到 K5 futex 自检", True,
              "K5 futex selftest: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5 futex FAIL")])
    rep.check(f"B{s}", "末行是自检完成", True,
              "K5 futex selftest: done" in text)

    rows = check_lines(text)
    rep.check(f"B{s}", "内核自评的每条 K5 check 都 ok", [],
              [name for name, row in rows if row["verdict"] != "ok"])

    seen: dict[str, int] = {}
    for name, _ in rows:
        seen[name] = seen.get(name, 0) + 1
    for case, names in CASES.items():
        missing = [n for n in names if n not in seen]
        rep.check(f"{case}{s}", f"{case} 的断言都报了（{len(names)} 条）", [],
                  missing)
    for name, count in REPEATED.items():
        rep.check(f"F2{s}", f"{name} 报了 {count} 次", count, seen.get(name, 0))

    # --- what the console says the expectations were ------------------------
    want = {name: int(row["want"], 16) for name, row in rows}
    got = {name: int(row["got"], 16) for name, row in rows}

    def expect_group(case: str, name: str, value: int) -> None:
        if name in want:
            rep.check(f"{case}{s}", f"{name} 的 want 是现场派生值", value,
                      want[name])

    expect_group("F4", "f4_sc_immediate", sc_ok)
    expect_group("F3", "f3_peer_success", sc_ok)
    expect_group("F4", "f4_sc_after_syscall", sc_bad)
    expect_group("F3", "f3_parent_sc_after_yield", sc_bad)
    expect_group("F1A", "f1a_ret_is_eagain", (1 << 64) - eagain())
    expect_group("F1", "f1_wake_count", 1)
    # m14-linux-035 / N27: a shared futex on an anonymous page resolves its key
    # (WAKE returns 0, a mismatching WAIT reaches the compare and returns
    # -EAGAIN) instead of failing with -EFAULT on a page with no `mapping`.
    expect_group("F7", "shared_futex_wake", 0)
    expect_group("F7", "shared_futex_wait_eagain", (1 << 64) - eagain())
    expect_group("F7", "shared_futex_page_mapped", 1)
    expect_group("F2", "f2_wake_count", stub_constant("K5F_F2_WAKE"))
    expect_group("F2", "f2_armed", f2_n)
    expect_group("F2", "f2_awake", stub_constant("K5F_F2_WAKE"))
    expect_group("F2", "f2_reported", stub_constant("K5F_F2_WAKE"))
    expect_group("F2", "f2b_reported", f2_n)
    expect_group("F5", "f5_requeue_moved", 1)
    expect_group("F6", "f6_waiter_bitset", stub_constant("K5F_F6_BITS"))
    expect_group("F6", "f6_other_bitset_wake", 0)
    expect_group("F8", "f8_wakeop_count", 1)
    # The woken waits answer 0 and the requeue case moved exactly the one
    # waiter it created; those are the only two outcomes the cases accept.
    for name in ("f1_waiter_ret", "f3_peer_success", "f5_waiter_ret",
                 "f6_waiter_ret", "f8_waiter_ret"):
        if name in got:
            rep.check(f"B{s}", f"{name}: 0", 0, got[name])

    # --- the arguments the program really sent ------------------------------
    # Three shapes of "first trap": the cmpxchg peer traps only on its report,
    # the F1A waiter traps on the probe's PRE_WAIT (the word changes between its
    # read and its FUTEX_WAIT), and every other waiter's first trap *is* its
    # FUTEX_WAIT.  The split is what makes the (script, uaddr) comparison
    # possible — the PRE_WAIT trap carries no futex arguments.
    consts = stub_constants()
    pre_wait_hex = hex(consts["K5F_TRAP_PRE_WAIT"])
    rows = child_lines(text)
    children = [row for row in rows if row.get("immu18") == "0x0"]
    pre_wait = [row for row in rows if row.get("immu18") == pre_wait_hex]
    expected = []
    for script, word in threads:
        if script in ("CMPXCHG", "ATOMIC", "EXITNOW"):
            continue
        offset = word.replace("K5F_DATA_VA + ", "").strip()
        if offset not in consts:
            raise SystemExit(f"k5_futex_probe: the stub's word {offset!r} "
                             "has no evaluable #define")
        expected.append((consts["K5F_SCRIPT_" + script],
                         consts["K5F_DATA_VA"] + consts[offset]))
    rep.check(f"F1{s}", "子线程的 futex 调用次数 == 程序里创建的等待线程数",
              len(expected), len(children))
    actual = [(int(row.get("script", "-1")), int(row.get("uaddr", "0"), 16))
              for row in children]
    rep.check(f"F1{s}", "每个等待者的 (script, uaddr) 都是程序指定那一个",
              expected, actual)
    rep.check(f"F1A{s}", "恰有一个线程先在 PRE_WAIT 处把字改掉再 wait", 1,
              len(pre_wait))
    if pre_wait:
        rep.check(f"F1A{s}", "PRE_WAIT 的那个线程就是 ATOMIC 脚本",
                  consts["K5F_SCRIPT_ATOMIC"],
                  int(pre_wait[0].get("script", "-1")))

    op_of_script = {
        "WAIT_F1": futex["FUTEX_WAIT"] | futex["FUTEX_PRIVATE_FLAG"],
        "ATOMIC": futex["FUTEX_WAIT"] | futex["FUTEX_PRIVATE_FLAG"],
        "REQUEUE": futex["FUTEX_WAIT"] | futex["FUTEX_PRIVATE_FLAG"],
        "BITSET": futex["FUTEX_WAIT_BITSET_PRIVATE"],
    }
    for row in children:
        script = int(row.get("script", "-1"))
        for name, value in op_of_script.items():
            if script == consts["K5F_SCRIPT_" + name]:
                rep.check(f"F1{s}", f"{name} 的 futex op == uapi 值",
                          hex(value), row.get("op"))

    # --- the syscalls the program made --------------------------------------
    traps = trap_lines(text)
    nr_lines = [row for row in traps if row.get("immu18") == "0x0"]
    by_nr: dict[str, int] = {}
    for row in nr_lines:
        by_nr[row.get("nr", "")] = by_nr.get(row.get("nr", ""), 0) + 1
    # The stub's child scripts share their futex blocks, so the dynamic count
    # is "one futex call per clone of a waiting script" plus the parent's own
    # static calls (everything before the child dispatch).
    parent_block = stub_block().split(".Lk5f_child:")[0]
    waiting = [s for s in threads if s[0] in
               ("WAIT_F1", "ATOMIC", "REQUEUE", "BITSET")]
    want_futex = len(waiting) + len(re.findall(
        r"\bset\.rd\s+rd15,\s*K5F_SYS_FUTEX\b", parent_block))
    want_clone = stub_count(r"\bset\.rd\s+rd15,\s*K5F_SYS_CLONE\b")
    want_exit = len(threads)      # every child ends through the shared block
    rep.check(f"B{s}", "futex 系统调用次数", want_futex,
              by_nr.get(hex(table["futex"]), 0))
    rep.check(f"B{s}", "clone 系统调用次数", want_clone,
              by_nr.get(hex(table["clone"]), 0))
    rep.check(f"B{s}", "exit 系统调用次数", want_exit,
              by_nr.get(hex(table["exit"]), 0))
    rep.check(f"B{s}", "trap 号与 stub 的号常量一致（futex）",
              table["futex"], stub_constant("K5F_SYS_FUTEX"))
    rep.check(f"B{s}", "trap 号与 stub 的号常量一致（clone）",
              table["clone"], stub_constant("K5F_SYS_CLONE"))
    rep.check(f"B{s}", "trap 号与 stub 的号常量一致（exit）",
              table["exit"], stub_constant("K5F_SYS_EXIT"))
    rep.check(f"B{s}", "trap 号与 stub 的号常量一致（getpid）",
              table["getpid"], stub_constant("K5F_SYS_GETPID"))

    # --- the probe's own numbers, as the console printed them ---------------
    const = one(text, "K5 futex const:")
    rep.check(f"F2{s}", "F2 常量行存在", True, const is not None)
    if const:
        rep.check(f"F2{s}", "F2 waiters 常量 == 程序里的等待线程数", f2_n,
                  int(const.get("f2_waiters", "-1")))
        rep.check(f"F2{s}", "F2 wake 常量 == stub", stub_constant("K5F_F2_WAKE"),
                  int(const.get("f2_wake", "-1")))
        rep.check(f"F6{s}", "F6 bits 常量 == stub", stub_constant("K5F_F6_BITS"),
                  int(const.get("bits", "-1"), 0))
        rep.check(f"F6{s}", "F6 other 常量 == stub",
                  stub_constant("K5F_F6_OTHER"),
                  int(const.get("other", "-1"), 0))
    judged = one(text, "K5 futex selftest: cases judged,")
    rep.check(f"B{s}", "judged 行存在", True, judged is not None)
    if judged:
        rep.check(f"B{s}", "注册的线程数 == 程序里的 clone 数", len(threads),
                  int(judged.get("slots", "-1")))

    # The scripts are handed over through CLONE_SETTLS: each registration must
    # name the script the stub assigned to that clone, in order.
    regs = reg_lines(text)
    rep.check(f"B{s}", "每个线程都登记了", len(threads), len(regs))
    if len(regs) == len(threads):
        rep.check(f"B{s}", "登记的 script 顺序 == stub 的 clone 顺序",
                  [stub_constant("K5F_SCRIPT_" + s) for s, _ in threads],
                  [int(r.get("script", "-1")) for r in regs])

    rep.check(f"D{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)


def static_recon(rep: Report, snap: dict | None) -> None:
    """The pieces a boot cannot show: image configuration and wiring."""
    rep.check("S0", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]
    for symbol, value in {"CONFIG_DADAO_K5_FUTEX_SELFTEST": "y",
                          "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
                          "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
                          "CONFIG_FUTEX": "y",
                          "CONFIG_SMP": "n",
                          "CONFIG_PAGE_SIZE_64KB": "y"}.items():
        if value == "n":
            rep.check("B", f"镜像配置：{symbol} 关", False,
                      config_enabled(config, symbol))
        else:
            rep.check("B", f"镜像配置：{symbol}={value}", value,
                      config_value(config, symbol))

    # The table really carries `futex` (an untouched slot answers -ENOSYS and
    # would read as "futex is not implemented").
    table = syscall_table_snapshot()
    elf = kernel_path()
    syms = symbols(elf)
    rep.check("F1", "sys_call_table[futex] == sys_futex", syms.get("sys_futex"),
              table_slot(elf, "sys_call_table", table["futex"]))

    # The arch futex header: `lr`/`sc`, a bounded retry, and the two hooks the
    # generic futex code requires.
    arch = kernel_text(FUTEX_ARCH_H)
    rep.check("F1", "arch futex 用 lr.t/sc.t（不是 get_user/put_user 当原子）",
              True, "lr.t.nn" in arch and "sc.t.nn" in arch)
    rep.check("F1", "arch futex 提供 cmpxchg 与 op_inuser 两个钩子", True,
              "futex_atomic_cmpxchg_inatomic" in arch and
              "arch_futex_atomic_op_inuser" in arch)
    m = re.search(r"#define\s+DADAO_FUTEX_SC_RETRIES\s+(\d+)", arch)
    rep.check("F1", "arch futex 的 sc 重试有界", True,
              bool(m) and int(m.group(1)) > 0)

    # The stub and the kernel carry the same constant block; the gate compares
    # them copy against copy, so a rename on one side is a FAIL.
    for name in ("K5F_DATA_VA", "K5F_VA_BASE", "K5F_W_F1", "K5F_W_F1B",
                 "K5F_W_F2", "K5F_W_F3", "K5F_W_F4", "K5F_W_F5A",
                 "K5F_W_F5B", "K5F_W_F6", "K5F_F2_WAKE",
                 "K5F_F6_BITS", "K5F_F6_OTHER", "K5F_F4_MARK", "K5F_F4_STORE",
                 "K5F_F3_PVAL", "K5F_F3_TVAL", "K5F_SCRIPT_WAIT_F1",
                 "K5F_SCRIPT_ATOMIC", "K5F_SCRIPT_REQUEUE", "K5F_SCRIPT_BITSET",
                 "K5F_SCRIPT_CMPXCHG", "K5F_TRAP_REG", "K5F_TRAP_ARM",
                 "K5F_TRAP_F4", "K5F_TRAP_F3_YIELD", "K5F_TRAP_F3",
                 "K5F_TRAP_F1", "K5F_TRAP_F1A", "K5F_TRAP_F2",
                 "K5F_TRAP_F2B", "K5F_TRAP_F5A", "K5F_TRAP_F5B",
                 "K5F_TRAP_F6A", "K5F_TRAP_F6B", "K5F_TRAP_DONE",
                 "K5F_TRAP_PRE_WAIT", "K5F_TRAP_REPORT"):
        rep.check("S1", f"{name}: stub == kernel", probe_constant(name),
                  stub_constant(name))

    # The op numbers the stub sends must be the uapi ones.
    futex = uapi_futex()
    rep.check("F1", "stub 的 WAIT op == FUTEX_WAIT|PRIVATE", 
              futex["FUTEX_WAIT"] | futex["FUTEX_PRIVATE_FLAG"],
              stub_constant("K5F_OP_WAIT_PRIVATE"))
    rep.check("F1", "stub 的 WAKE op == FUTEX_WAKE|PRIVATE",
              futex["FUTEX_WAKE"] | futex["FUTEX_PRIVATE_FLAG"],
              stub_constant("K5F_OP_WAKE_PRIVATE"))
    rep.check("F5", "stub 的 REQUEUE op == FUTEX_REQUEUE|PRIVATE",
              futex["FUTEX_REQUEUE"] | futex["FUTEX_PRIVATE_FLAG"],
              stub_constant("K5F_OP_REQUEUE_PRIVATE"))
    rep.check("F6", "stub 的 WAKE_BITSET op == FUTEX_WAKE_BITSET_PRIVATE",
              futex["FUTEX_WAKE_BITSET_PRIVATE"],
              stub_constant("K5F_OP_WAKE_BITSET_PRIV"))
    rep.check("F6", "stub 的 WAIT_BITSET op == FUTEX_WAIT_BITSET_PRIVATE",
              futex["FUTEX_WAIT_BITSET_PRIVATE"],
              stub_constant("K5F_OP_WAIT_BITSET_PRIV"))

    # FUTEX_WAKE_OP's encoded word: op=ADD, cmp=EQ, oparg=1, cmparg=0x10 (the
    # values the stub's F8 case writes); FUTEX_OP_* come from the same uapi
    # header, so a renumbering there is a FAIL here.
    op_num = {name: int(value, 0) for name, value in
              re.findall(r"^#define\s+(FUTEX_OP_\w+)\s+(\w+)",
                         kernel_text(FUTEX_H), re.M)}
    want_arg = ((op_num["FUTEX_OP_ADD"] << 28) |
                (op_num["FUTEX_OP_CMP_EQ"] << 24) | (1 << 12) | 0x10)
    rep.check("F8", "stub 的 WAKE_OP op == FUTEX_WAKE_OP|PRIVATE",
              futex["FUTEX_WAKE_OP"] | futex["FUTEX_PRIVATE_FLAG"],
              stub_constant("K5F_OP_WAKE_OP_PRIV"))
    rep.check("F8", "stub 的 WAKE_OP 编码字 == uapi 的 FUTEX_OP_* 组合",
              hex(want_arg), hex(stub_constant("K5F_WAKEOP_ARG")))
    # The kernel half must name the same words and the same trap.
    for name in ("K5F_W_WAKEOP_A", "K5F_W_WAKEOP_B", "K5F_TRAP_F8"):
        rep.check("S1", f"{name}: stub == kernel", probe_constant(name),
                  stub_constant(name))

    # CLONE_CHILD_CLEARTID: the value the stub sends must be `sched.h`'s (a
    # 0x02000000 typo is CLONE_NEWCGROUP and silently disables the case).
    bits_early = clone_bits()
    rep.check("F7", "stub 的 CLONE_CHILD_CLEARTID == sched.h",
              hex(bits_early["CLONE_CHILD_CLEARTID"]),
              hex(stub_constant("K5F_CLONE_CHILD_CLEARTID")))
    for name in ("K5F_W_F7", "K5F_SCRIPT_EXITNOW", "K5F_TRAP_F7"):
        rep.check("S1", f"{name}: stub == kernel", probe_constant(name),
                  stub_constant(name))

    # ... and the clone flags must be the CLONE_* the locked header defines.
    bits = clone_bits()
    want = (bits["CLONE_VM"] | bits["CLONE_FS"] | bits["CLONE_FILES"] |
            bits["CLONE_SIGHAND"] | bits["CLONE_THREAD"] | bits["CLONE_SETTLS"])
    rep.check("B", "stub 的 CLONE_* 组合 == sched.h 的位或", hex(want),
              hex(stub_constant("K5F_CLONE_FLAGS")))

    # The syscall numbers the stub sends must be the locked table's.
    table = syscall_table_snapshot()
    for stub_name, entry in (("K5F_SYS_FUTEX", "futex"),
                             ("K5F_SYS_CLONE", "clone"),
                             ("K5F_SYS_GETPID", "getpid"),
                             ("K5F_SYS_EXIT", "exit")):
        rep.check("B", f"{stub_name} == syscall.tbl[{entry}]", table[entry],
                  stub_constant(stub_name))

    # The recheck the F1A case turns on lives in futex_wait_setup(): the user
    # word is compared under the bucket lock before the enqueue.
    waitwake = kernel_text(WAITWAKE_C)
    start = waitwake.index("int futex_wait_setup(")
    setup = waitwake[start:waitwake.index("\n}\n", start)]
    rep.check("F1A", "futex_wait_setup 在 enqueue 前复核用户字", True,
              "futex_get_value_locked(&uval, uaddr)" in setup and
              "if (uval != val)" in setup and
              setup.index("if (uval != val)") < setup.index("futex_queue("))
    rep.check("F1A", "复核失败返回 -EWOULDBLOCK（== -EAGAIN）", True,
              "-EWOULDBLOCK" in setup)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> dict(file, needle, replacement, case, why, layer)
INJECTIONS = {
    "no-recheck": {
        "file": WAITWAKE_C,
        "needle": "\t\tif (uval != val) {\n\t\t\tfutex_q_unlock(hb);",
        "replacement": "\t\tif (0 && uval != val) {\n\t\t\tfutex_q_unlock(hb);",
        "case": "F1A",
        "why": "FUTEX_WAIT 不再复核用户字（检查与睡眠之间可被插队）",
        "layer": "kernel",
    },
    "lost-wake": {
        "file": WAITWAKE_C,
        "needle": "\tif (WARN(q->pi_state || q->rt_waiter, \"refusing to wake PI futex\\n\"))\n"
                  "\t\treturn false;\n\n\t__futex_unqueue(q);",
        "replacement": "\tif (WARN(q->pi_state || q->rt_waiter, \"refusing to wake PI futex\\n\"))\n"
                       "\t\treturn false;\n\n\tif (1)\n\t\treturn false;\n"
                       "\t__futex_unqueue(q);",
        "case": "F1",
        "why": "FUTEX_WAKE 记了数却不唤醒（唤醒丢失）",
        "layer": "kernel",
    },
    "no-bitset": {
        "file": WAITWAKE_C,
        "needle": "\t\t\t/* Check if one of the bits is set in both bitsets */\n"
                  "\t\t\tif (!(this->bitset & bitset))\n\t\t\t\tcontinue;",
        "replacement": "\t\t\t/* Check if one of the bits is set in both bitsets */\n"
                       "\t\t\tif (0)\n\t\t\t\tcontinue;",
        "case": "F6",
        "why": "WAKE_BITSET 忽略 bitset（错位 bitset 也唤醒）",
        "layer": "kernel",
    },
    "no-requeue": {
        "file": REQUEUE_C,
        "needle": "\t\tif (task_count - nr_wake >= nr_requeue)\n",
        "replacement": "\t\tif (1 || task_count - nr_wake >= nr_requeue)\n",
        "case": "F5",
        "why": "REQUEUE 一个也不搬（直接停）",
        "layer": "kernel",
    },
    "no-op-add": {
        "file": FUTEX_ARCH_H,
        "needle": "\t\tcase FUTEX_OP_ADD:\n\t\t\tnewval = old + oparg;",
        "replacement": "\t\tcase FUTEX_OP_ADD:\n\t\t\tnewval = oparg;",
        "case": "F8",
        "why": "arch 的 lr/sc 读改写把 ADD 算成「只写 oparg」（丢旧值）",
        "layer": "kernel",
    },
    "clear-tid-off": {
        "file": FORK_C,
        "needle": "\tp->clear_child_tid = (clone_flags & CLONE_CHILD_CLEARTID) ?"
                  " args->child_tid : NULL;",
        "replacement": "\tp->clear_child_tid = NULL;	/* injected: CLEARTID ignored */",
        "case": "F7",
        "why": "内核不再记录 clear_child_tid（CLEARTID 形同未开）⇒ 退出不清 tid",
        "layer": "kernel",
    },
    "sc-crossing": {
        "file": QEMU_INT_H,
        "needle": "    env->lock_valid = 0;\n",
        "replacement": "    /* injected: the entry no longer clears the reservation */\n",
        "case": "F4",
        "why": "异常/中断进入不清 lr/sc 保留标记（跨 syscall 的 sc 仍成功）",
        "layer": "qemu",
    },
}


def run_injection(rep: Report, name: str, rom: str) -> None:
    spec = INJECTIONS[name]
    rel, needle, repl = spec["file"], spec["needle"], spec["replacement"]
    case, why, layer = spec["case"], spec["why"], spec["layer"]
    root = SOURCE if layer == "kernel" else Path(
        os.environ.get("K5F_QEMU_SRC") or (_work_root() / "source" / "qemu"))
    path = root / rel
    if not path.is_file():
        rep.check(f"INJECT {name}", "注入点文件存在", True, False)
        return
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
        if layer == "qemu":
            qrc = build_qemu()
            rep.check(f"INJECT {name}", "注入后 qemu 可构建", 0, qrc)
            if qrc != 0:
                return
            os.environ["K5F_QEMU"] = str(build_dir().parent / "qemu" /
                                         "qemu-system-dadao")
        kernel_rc, snap = build_image(f"injected:{name}")
        if kernel_rc != 0 or snap is None:
            rep.check(f"INJECT {name}", f"注入后镜像可构建（{why}）", 0,
                      kernel_rc)
            return
        rc, out = boot(f"inject-{name}", rom)
        rows = check_lines(out)
        red = [n for n, row in rows if row["verdict"] != "ok"]
        died = ("K5 futex FAIL" in out or "Kernel panic" in out or
                "dadao: die mode=" in out)
        rep.info(f"inject {name}: rc={rc} red={red[:5]} died={died}")
        # A hang (the 180 s boot timeout) is a red too: the injected defect can
        # leave a waiter blocked for ever, in which case nothing is ever
        # printed to go red (m14-linux-045's exit loop makes that reachable for
        # `no-recheck`, where the waiter sleeps through the changed word).
        rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True,
                  bool([n for n in red if n.lower().startswith(case.lower())]) or
                  died or rc == 124)
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        if layer == "qemu":
            rc = build_qemu()
            rep.check(f"INJECT {name}", "还原后 qemu 可构建", 0, rc)
        rc, snap = build_image("restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if snap is not None:
            rc2, out2 = boot(f"restored-{name}", rom)
            rows2 = check_lines(out2)
            rep.check(f"INJECT {name}", "还原后回绿（无红项）", [],
                      [n for n, row in rows2 if row["verdict"] != "ok"])
            rep.check(f"INJECT {name}", "还原后宿主 rc=0", 0, rc2)
        os.environ.pop("K5F_QEMU", None)


def selfcheck() -> int:
    """Prove the judging can fail — and that the same check can pass.

    Two consoles: a broken one and the same one with four specific facts
    repaired.  Each of the four checks must be red on the first and green on
    the second, so none of them is a constant.
    """
    broken = (
        "K5 futex selftest: begin pid=1\n"
        "K5 futex const: f2_waiters=2 f2_wake=9 bits=0x4 other=0x1\n"
        "K5 check f1_wake_count want=0x9 got=0x1 FAIL\n"
    )
    repaired = (
        "K5 futex selftest: begin pid=1\n"
        f"K5 futex const: f2_waiters={f2_waiters(stub_threads())} "
        f"f2_wake={stub_constant('K5F_F2_WAKE')} "
        f"bits={stub_constant('K5F_F6_BITS'):#x} "
        f"other={stub_constant('K5F_F6_OTHER'):#x}\n"
        "K5 check f1_wake_count want=0x1 got=0x1 ok\n"
        "K5 futex selftest: done (futex/atomics closed)\n"
    )
    watch = ("B: 末行是自检完成",
             "B: 内核自评的每条 K5 check 都 ok",
             "F2: F2 waiters 常量 == 程序里的等待线程数",
             "F6: F6 bits 常量 == stub")
    rep1 = Report()
    judge(rep1, broken, 0)
    rep2 = Report()
    judge(rep2, repaired, 0)
    print(f"[SELFCHECK] broken console: {len(rep1.failed)} red checks")
    for name in rep1.failed[:8]:
        print(f"[SELFCHECK]   {name}")
    ok = True
    for name in watch:
        red1 = name in rep1.failed
        red2 = name in rep2.failed
        want_red2 = False
        good = red1 and (red2 == want_red2)
        print(f"[SELFCHECK] {'PASS' if good else 'FAIL'} {name}: "
              f"broken_red={red1} repaired_red={red2}")
        ok = ok and good
    if not ok:
        print("[SELFCHECK] FAIL: the judging is constant on a broken console")
        return 1
    print("[SELFCHECK] PASS: every watched check has a reachable FAIL path")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="M14 K5 futex probe")
    parser.add_argument("--selfcheck", action="store_true",
                        help="prove the judging can fail (no build, no boot)")
    parser.add_argument("--inject", action="append", default=[], metavar="NAME",
                        help=f"one of: {', '.join(sorted(INJECTIONS))}")
    parser.add_argument("--no-inject", action="store_true",
                        help="only the cases (no injection rounds)")
    parser.add_argument("--no-build", action="store_true",
                        help="judge the last console log instead of rebuilding")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

    rep = Report()
    if args.no_build:
        text = (SCRATCH / "log" / "k5f.log").read_text(encoding="utf-8")
        judge(rep, text, 0)
    else:
        rc, snap = build_image()
        static_recon(rep, snap)
        if snap is None:
            print("k5_futex_probe: no image; judging stops here",
                  file=sys.stderr)
            return 1
        rom = firmware()
        rc, out = boot("k5f", rom)
        judge(rep, out, rc)

        if not args.no_inject:
            names = args.inject or sorted(INJECTIONS)
            for name in names:
                if name not in INJECTIONS:
                    raise SystemExit(f"k5_futex_probe: unknown injection "
                                     f"{name!r}")
                run_injection(rep, name, rom)

    print()
    if rep.failed:
        print(f"k5_futex_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"k5_futex_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
