#!/usr/bin/env python3
"""k4_kthread_probe.py — M14 K4 kernel-thread probe (`m14-linux-020`).

Kernel threads are the second kind of task the K4 process model has to make
real: a task created by `kernel_thread()` that runs a kernel function, owns no
user address space (`mm == NULL`), shares the parent's `fs`/`files` tables by
default, and is stopped through `kthread_stop()` — as opposed to `fork()`, whose
child gets an address space of its own (016) and is entered in user mode.

The kernel side is `arch/dadao/kernel/k4_kthread_selftest.c`
(`CONFIG_DADAO_K4_KTHREAD_SELFTEST`), which runs inside `kernel_init()` after
`kernel_init_freeable()` — the first point where both kernel threads the probe
needs exist: `kthreadd`, created by `rest_init()` from the boot task (pid 2),
and the threads it creates on request.  Every expectation is derived from its
owner:

  * `CLONE_FS`/`CLONE_FILES` bit values      -> `include/uapi/linux/sched.h`
    (the kernel's own locked copy), compared with what the image prints;
  * `kthreadd`'s pid                          -> `init/main.c`'s `rest_init()`
    call order (the pid is the ordinal of the `kernel_thread(kthreadd, ...)`
    call, with `user_mode_thread(kernel_init, ...)` first);
  * the flags both in-kernel callers pass     -> `init/main.c` (`kthreadd`) and
    `kernel/kthread.c` (`kthread`), read from the source, matched by the
    selftest's own `CLONE_FS | CLONE_FILES`;
  * the entry IP a kernel thread starts at    -> the image's symbol table
    (`dadao_ret_from_fork`);
  * `TASK_DEAD`                               -> `include/linux/sched.h`;
  * the body's two return codes               -> `k4_kthread_selftest.c`;
  * the guest FAIL segment                    -> `spec/Kaiwu §7.1`;
  * the page size                             -> the image's own `.config`
    (checked against `spec/DADAO-12 §2.2.2`);
  * `mm`/`mm_users` existence and meaning     -> `include/linux/mm_types.h` /
    `include/linux/sched.h` (a kernel thread's `mm` is NULL; `mm_users` is the
    count a `CLONE_VM` clone adds a reference to, so `kernel_thread()` from a
    task that has an mm must leave the count unchanged after the arch hook
    drops the reference `copy_mm()` took).

Groups (the letters ``--selfcheck``/``--inject`` flip):

  S  static recon: the image is the probe image the gate asked for (every other
     `CONFIG_DADAO_*` pinned off), the probe's hook sits where it must, and the
     symbols the run relies on are in the image.
  K1 `kthreadd` is the daemon the kernel created itself: pid 2, `PF_KTHREAD`,
     no user `mm`, real `fs`/`files` tables, and — once it has serviced a
     request — the name "kthreadd".
  K2 `kthread_create()` + `wake_up_process()` and `kthread_run()` each produce a
     thread that runs its body (inside the body: pid, `mm == NULL`,
     `PF_KTHREAD`), that sees `kthread_should_stop()` after `kthread_stop()`
     (its return code comes back), and that then leaves the run queue
     (`TASK_DEAD`, `on_rq == 0`) with its counter frozen.
  K3 `kernel_thread(fn, arg, CLONE_FS | CLONE_FILES)` shares the parent's
     `fs`/`files`, owns no user `mm` even when the parent has one (the reference
     `copy_mm()` took is dropped, so `mm_users` is unchanged), leaves
     `rb3`/`thread.tp` at 0 and starts at `dadao_ret_from_fork`; a fork from the
     same task gets a private `mm` with a different ASID.
  K4 the *negative* half — what this milestone must not implement: no user
     `clone()` in this probe (`copy_thread()` takes no `tls` argument and the
     kernel-thread probe never spells `CLONE_SETTLS`/`CLONE_THREAD`), no
     `ret_from_kernel_thread` and no futex surface, and a kernel thread's frame
     carries no `rd8` return value.  The user `clone()`/TLS work arrived with
     m14-linux-024 (K5) and lives in `copy_thread()`'s `CLONE_SETTLS` branch and
     in the K5 clone probe — structural, judged from the sources either way.

``--inject`` corrupts one rule, rebuilds, asserts the named group goes red,
restores with ``cp`` + md5 and proves the image is green again: ① `rest_init()`
never creates `kthreadd`; ② the kernel_thread hook keeps the parent's mm;
③ `kthread_should_stop()` never sees the stop bit.

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

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                     # noqa: E402  (pins)
from tests.unit.linux import k1_boot_probe as k1boot          # noqa: E402  (symbols)
from tools.linux import make_defconfig as defconfig      # noqa: E402  (config slice)
from tools.linux import paths as linux_paths             # noqa: E402
from tools.qemu import k0_boot_probe as k0               # noqa: E402  (firmware, ABI)

SCRATCH = (Path(os.environ.get("K4KT_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-020") / "check-linux-k4-kthread")

SPEC_DADAO12 = _REPO / "spec" / "DADAO-12-SEE-主管系统运行环境.md"
SOURCE = linux_paths.linux_source_dir()

SELFTEST_C = "arch/dadao/kernel/k4_kthread_selftest.c"
PROCESS_C = "arch/dadao/kernel/process.c"
SETUP_C = "arch/dadao/kernel/setup.c"
INIT_MAIN_C = "init/main.c"
KTHREAD_C = "kernel/kthread.c"

#: Every boundary pinned (`make check-config-pins`, ISS-470): this image runs
#: one probe, after `kernel_init_freeable()`.  The other K4 probes stop at the
#: boundary or need their own image, so all of them are pinned off.
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
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "y",
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

#: The K6 production boot's continuation symbol lives in arch/dadao/Kconfig (not
#: Kconfig.debug), so the Kconfig.debug pin gate does not cover it; keep the K6
#: shell out of this probe image (see k4_fork_probe.py).
K6_SHELL_OFF = "CONFIG_DADAO_K6_SHELL=n"

IMAGE = config_pins.config_lines(CONFIG_PINS) + [K6_SHELL_OFF]

ALWAYS_OFF = ("CONFIG_DADAO_K1_EARLY_STOP", "CONFIG_DADAO_K2_EARLY_STOP",
              "CONFIG_DADAO_K2_TIME_STOP", "CONFIG_DADAO_K6_SHELL")

#: Wall-clock guards; `timeout` => rc 124, which is a FAIL (AGENTS.md「长任务」).
TIMEOUT_BUILD = int(os.environ.get("K4KT_BUILD_TIMEOUT", "1800"))
TIMEOUT_QEMU = int(os.environ.get("K4KT_QEMU_TIMEOUT", "180"))

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
    off = re.search(r"`VA\[(\d+):0+\]`\s*->\s*页内偏移", sec)
    if not off:
        raise SystemExit("k4_kthread_probe: spec §2.2.2 has no page-offset width")
    bits = int(off.group(1)) + 1
    return bits, bits


def exit_segments() -> dict:
    """spec/Kaiwu §7.1's guest FAIL segment, parsed (no literal here)."""
    text = (SOURCE.parents[1] / "spec" / "Kaiwu-测试机运行环境.md")
    if not text.is_file():
        text = _REPO / "spec" / "Kaiwu-测试机运行环境.md"
    body = text.read_text(encoding="utf-8")
    # The table row `| `0x01`–`0x7F` | guest | ...` is the authoritative shape;
    # the prose repeats it with the same backticks, so one pattern covers both.
    m = re.search(r"`0x01`\s*[-–]\s*`0x([0-7][0-9a-fA-F])`", body)
    if not m:
        raise SystemExit("k4_kthread_probe: spec/Kaiwu §7.1 has no guest segment")
    return {"guest_max": int(m.group(1), 16)}


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"k4_kthread_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def strip_comments(text: str) -> str:
    """@text with C comments removed (so a comment cannot satisfy a code check)."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", text)


def block(text: str, anchor: str) -> str:
    """The `{ ... }` block that follows @anchor (brace matched)."""
    start = text.index(anchor)
    open_brace = text.index("{", start)
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace:index + 1]
    raise SystemExit(f"k4_kthread_probe: unbalanced block after {anchor!r}")


def clone_bit(name: str) -> int:
    """`CLONE_<name>`'s value from the kernel's own uapi header."""
    text = kernel_text("include/uapi/linux/sched.h")
    m = re.search(rf"#define\s+{name}\s+(0x[0-9a-fA-F]+|\d+)", text)
    if not m:
        raise SystemExit(f"k4_kthread_probe: include/uapi/linux/sched.h has no {name}")
    return num(m.group(1), -1)


def kthreadd_pid() -> int:
    """`kthreadd`'s pid, from `rest_init()`'s own call order.

    The pid is the ordinal of the task-creating call: `rest_init()` spawns
    `kernel_init` first ("so that it obtains pid 1" — the comment in the same
    function), then `kthreadd`; no other task exists before them.
    """
    text = kernel_text(INIT_MAIN_C)
    body = block(text, "static noinline void __ref __noreturn rest_init(void)")
    calls = list(re.finditer(r"pid = (user_mode_thread|kernel_thread)\((\w+)",
                             body))
    names = [(m.group(1), m.group(2)) for m in calls]
    if not names:
        raise SystemExit("k4_kthread_probe: rest_init() creates no task")
    for index, (_fn, name) in enumerate(names, start=1):
        if name == "kthreadd":
            return index
    raise SystemExit("k4_kthread_probe: rest_init() never creates kthreadd")


def task_dead() -> int:
    text = kernel_text("include/linux/sched.h")
    m = re.search(r"#define\s+TASK_DEAD\s+(0x[0-9a-fA-F]+|\d+)", text)
    if not m:
        raise SystemExit("k4_kthread_probe: include/linux/sched.h has no TASK_DEAD")
    return num(m.group(1), -1)


def selftest_ret(name: str) -> int:
    text = kernel_text(SELFTEST_C)
    m = re.search(rf"#define\s+{name}\s+(0x[0-9a-fA-F]+|\d+)", text)
    if not m:
        raise SystemExit(f"k4_kthread_probe: {SELFTEST_C} has no {name}")
    return num(m.group(1), -1)


def selftest_fail_codes() -> dict[str, int]:
    text = kernel_text(SELFTEST_C)
    codes = {}
    for name, value in re.findall(r"#define\s+(K4KT_FAIL_K[0-9])\s+"
                                  r"(0x[0-9a-fA-F]+|\d+)", text):
        codes[name] = num(value, -1)
    if not codes:
        raise SystemExit(f"k4_kthread_probe: {SELFTEST_C} has no FAIL codes")
    return codes


def selftest_check_names() -> list[str]:
    """The `K4 check ...` names the kernel's own assertions print."""
    text = kernel_text(SELFTEST_C)
    names = re.findall(r'k4kt_expect\("([^"]+)"', text)
    if not names:
        raise SystemExit(f"k4_kthread_probe: {SELFTEST_C} prints no checks")
    if len(names) != len(set(names)):
        raise SystemExit("k4_kthread_probe: duplicate check name in the selftest")
    return sorted(names)


def caller_flags() -> dict[str, int]:
    """The resource flags each in-kernel `kernel_thread()` caller passes.

    `rest_init()` creates `kthreadd` with `CLONE_FS | CLONE_FILES`, and
    `create_kthread()` creates the daemon's children with the same two plus the
    exit signal — "默认共享父资源表" is these two call sites, read from the
    source rather than restated in the probe.
    """
    init = block(kernel_text(INIT_MAIN_C),
                 "static noinline void __ref __noreturn rest_init(void)")
    m = re.search(r"kernel_thread\(kthreadd,\s*NULL,\s*NULL,\s*([^)]+)\)", init)
    if not m:
        raise SystemExit("k4_kthread_probe: rest_init()'s kthreadd call not found")
    kd = m.group(1).strip()

    kthread = kernel_text(KTHREAD_C)
    m = re.search(r"kernel_thread\(kthread,\s*create,\s*create->full_name,\s*"
                  r"([^)]+)\)", kthread)
    if not m:
        raise SystemExit("k4_kthread_probe: create_kthread()'s call not found")
    kt = m.group(1).strip()
    for expr, label in ((kd, "kthreadd"), (kt, "kthread")):
        if "CLONE_FS" not in expr or "CLONE_FILES" not in expr:
            raise SystemExit(
                f"k4_kthread_probe: {label} no longer passes CLONE_FS|CLONE_FILES "
                f"({expr})")
    return {"kthreadd": shared_flags(kd), "kthread": shared_flags(kt)}


def shared_flags(expr: str) -> int:
    """The `CLONE_FS | CLONE_FILES[ | SIGCHLD]` set named by @expr."""
    flags = 0
    if "CLONE_FS" in expr:
        flags |= clone_bit("CLONE_FS")
    if "CLONE_FILES" in expr:
        flags |= clone_bit("CLONE_FILES")
    return flags


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
        print(f"k4_kthread_probe: FAIL: config slice for {label} rc={rc}",
              file=sys.stderr)
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
    }


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k4kt.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k4_kthread_probe: {kernel} missing; run `make linux-vmlinux`")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k4_kthread_probe: qemu-system-dadao missing (make install-host)")
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
    rep.check("S0", "K4 内核线程探针镜像可构建", 0, rc_build)
    if snap is None:
        for name in ("配置行", "边界符号", "页大小"):
            rep.check("S1", f"{name}（镜像缺失）", "可检查", "镜像未构建")
        return

    config = snap["config"]
    for symbol, value in {"CONFIG_DADAO_K4_KTHREAD_SELFTEST": "y",
                          "CONFIG_PAGE_SIZE_64KB": "y"}.items():
        line = f"{symbol}={value}"
        rep.check("S1", f"镜像配置：{line}", line,
                  next((ln for ln in config.splitlines()
                        if ln.startswith(symbol + "=")), "<unset>"))
    rep.check("S1", "其余 DADAO_* 自检全关（本镜像只有一个探针）", [],
              [s for s in CONFIG_PINS
               if s != "CONFIG_DADAO_K4_KTHREAD_SELFTEST"
               and config_enabled(config, s)])
    off = [f"{s}={config_value(config, s)}" for s in ALWAYS_OFF
           if config_enabled(config, s)]
    rep.check("S1", "早期里程碑边界全关（镜像走过 rest_init）", [], off)

    shift = num(config_value(config, "CONFIG_PAGE_SHIFT"))
    rep.check("S2", "页大小（1 << CONFIG_PAGE_SHIFT）== spec §2.2.2 页内偏移位宽",
              d["page_size"], 1 << shift)
    rep.check("S2", "CONFIG_PAGE_SHIFT == spec §2.2.2", d["page_shift"], shift)

    # The hook: the probe runs in kernel_init after the initcalls, and it is
    # compiled only into this image.
    init = kernel_text(INIT_MAIN_C)
    hook = re.search(r"kernel_init_freeable\(\);.*?dadao_k4_kthread_selftest\(\);",
                     init, re.DOTALL)
    rep.check("S3", "探针在 kernel_init() 里于 kernel_init_freeable() 之后运行", True,
              hook is not None)
    rep.check("S3", "探针调用点受 CONFIG_DADAO_K4_KTHREAD_SELFTEST 保护", True,
              "#ifdef CONFIG_DADAO_K4_KTHREAD_SELFTEST\n\t/*\n\t * K4 kernel-thread probe"
              in init)
    rep.check("S3", "边界不再收尾（镜像继续到 rest_init/kernel_init）", True,
              "#ifdef CONFIG_DADAO_K4_KTHREAD_SELFTEST" in kernel_text(SETUP_C))
    rep.check("S3", "kernel/Makefile 编译 k4_kthread_selftest.o", True,
              "obj-$(CONFIG_DADAO_K4_KTHREAD_SELFTEST) += k4_kthread_selftest.o"
              in kernel_text("arch/dadao/kernel/Makefile"))

    # The kernel_thread hook: the reference copy_mm() took for CLONE_VM is
    # dropped for a kernel thread, and the thread pointer is left at 0.
    process = kernel_text(PROCESS_C)
    fn_block = block(process, "if (unlikely(args->fn))")
    rep.check("S4", "copy_thread 的 kernel_thread 分支丢弃父 mm 的引用", True,
              "if (args->kthread && p->mm)" in fn_block and "mmput(mm);" in fn_block)
    rep.check("S4", "kernel_thread 子帧 rb3 = 0（无用户线程指针）", True,
              "childregs->rb[3] = 0;" in fn_block)
    rep.check("S4", "kernel_thread 分支不写 rd8（无用户返回值）", False,
              "rd[8]" in fn_block)
    rep.check("S4", "fork 分支仍写 rd8 = 0（对照）", True,
              "childregs->rd[8] = 0;" in process)
    rep.check("S4", "copy_thread 签名无 tls 参数", True,
              "int copy_thread(struct task_struct *p, "
              "const struct kernel_clone_args *args)" in process)

    # K4's negative half: this milestone owns kernel threads only.  The user
    # `clone()`/TLS surface arrived with m14-linux-024 (K5) — it lives in the
    # arch's `copy_thread()` hook and in the K5 clone probe, and must stay out
    # of *this* milestone's probe; the kernel-thread shape above (S4) is what
    # this gate is about either way.
    arch = "\n".join(strip_comments(kernel_text(rel)) for rel in (
        PROCESS_C, "arch/dadao/kernel/syscall_table.c",
        "arch/dadao/kernel/syscalls.c", SETUP_C, SELFTEST_C))
    kthread_probe = strip_comments(kernel_text(SELFTEST_C))
    for token in ("CLONE_SETTLS", "CLONE_THREAD"):
        rep.check("S5", f"K4 探针不处理 {token}（用户 clone 归 K5）", 0,
                  kthread_probe.count(token))
    for token in ("ret_from_kernel_thread", "futex"):
        rep.check("S5", f"arch/dadao 不实现 {token}（futex 归 K5/m14-linux-025）",
                  0, arch.count(token))
    rep.check("S5", "用户 clone 的 SETTLS 分支在 arch 的进程钩子里（K5）", True,
              "args->flags & CLONE_SETTLS" in process)
    rep.check("S5", "K5 clone 探针登记在 kernel/Makefile（探针镜像）", True,
              "obj-$(CONFIG_DADAO_K5_CLONE_SELFTEST) += k5_clone_selftest.o"
              in kernel_text("arch/dadao/kernel/Makefile"))
    rep.check("S5", "arch 的 syscalls.c 没有 clone 实现（表走 asm-generic）", False,
              "clone" in kernel_text("arch/dadao/kernel/syscalls.c").lower())

    # The probe source the run is judged against.
    rep.check("S6", "self-test 覆盖 K1/K2/K3 三个 case", ["k4kt_case_k1",
              "k4kt_case_k2", "k4kt_case_k3"],
              [name for name in ("k4kt_case_k1", "k4kt_case_k2", "k4kt_case_k3")
               if f"static void {name}(void)" in kernel_text(SELFTEST_C)])
    codes = selftest_fail_codes()
    rep.check("S6", "FAIL 码都在 spec/Kaiwu §7.1 的 guest 段内", [],
              [f"{name}={value:#x}" for name, value in codes.items()
               if not 1 <= value <= d["guest_max"]])

    # S7 (m18-linux-009, ISS-494): the stop verdict waits for the *event*
    # (do_exit() reaching TASK_DEAD), bounded, with a real hand-over point.
    check_k2_dead_wait(rep)

    rep.check("S6", "mm_users 是 mm_struct 的引用计数（源内存在）", True,
              "atomic_t mm_users;" in kernel_text("include/linux/mm_types.h"))
    sched_h = kernel_text("include/linux/sched.h")
    rep.check("S6", "task_struct 有 mm/active_mm 两个字段", ["mm", "active_mm"],
              [name for name in ("mm", "active_mm")
               if re.search(rf"struct mm_struct\s+\*\s*{name}\s*;", sched_h)])

    syms = snap["syms"]
    for name in ("dadao_k4_kthread_selftest", "kthreadd", "kthreadd_task",
                 "kthread_create_on_node", "kthread_stop", "kthread_should_stop",
                 "kernel_thread", "dadao_ret_from_fork"):
        rep.check("S7", f"镜像含符号 {name}", True, name in syms)


def check_k2_dead_wait(rep: Report) -> None:
    """S7: `k4kt_wait_dead()` — event + bounded wait + yield (ISS-494)."""
    src = kernel_text(SELFTEST_C)
    rep.check("S7", "K2 完成判据 = TASK_DEAD 事件 + 有界上限", True,
              "static bool k4kt_wait_dead(" in src and
              "READ_ONCE(t->__state) == TASK_DEAD" in src and
              "K4KT_SPINS" in src)
    rep.check("S7", "K2 等待循环有 cond_resched()/yield() 让出点", True,
              re.search(r"cond_resched\(\);\s*\n\s*yield\(\);", src) is not None)
    rep.check("S7", "K2 停止判据调用有界等待（不是立即读）", True,
              "if (!k4kt_wait_dead(t))" in src)
    rep.check("S7", "K2 不再用 16 次裸 schedule() 冒充等待", 0,
              len(re.findall(r"spins < 16[^\n]*\n\s*schedule\(\);", src)))


# ---------------------------------------------------------------------------
# K1 / K2 / K3: the run
# ---------------------------------------------------------------------------

def check_k1(rep: Report, rc: int, text: str, d: dict) -> None:
    rep.check("K1", "镜像以 SYS_EXIT(0) 结束", 0, rc)
    lines = check_lines(text)
    rep.check("K1", "内核自评的每条 K4 check 都 ok", [],
              [n for n, row in lines if row["verdict"] != "ok"])
    rep.check("K1", "内核打印的 check 名集合 == self-test 源码里的断言集合",
              d["check_names"], sorted({n for n, _r in lines}))

    k1 = line_with(text, "K4 kthread k1: ")
    rep.check("K1", "K1 行存在（vacuous ⇒ FAIL）", True, k1 is not None)
    if not k1:
        return
    rep.check("K1", "kthreadd 存在", 1, num(k1.get("present")))
    rep.check("K1", "kthreadd 的 pid == rest_init() 里的第 2 个创建（现场派生）",
              d["kthreadd_pid"], num(k1.get("pid")))
    rep.check("K1", "kthreadd 没有用户 mm", 0, num(k1.get("mm"), -1))
    rep.check("K1", "kthreadd 是内核线程（PF_KTHREAD）", 1, num(k1.get("kthread")))
    rep.check("K1", "kthreadd 有 fs/files 资源表", True,
              num(k1.get("fs"), 0) > 0 and num(k1.get("files"), 0) > 0)
    run = line_with(text, "K4 kthread k2: kthreadd_comm=")
    rep.check("K2", "daemon 行存在（vacuous ⇒ FAIL）", True, run is not None)
    if run:
        rep.check("K2", "kthreadd 自己的 prologue 跑过（它给自己命名）",
                  "kthreadd", run.get("kthreadd_comm"))
        rep.check("K2", "跑过 prologue 的 kthreadd 仍无用户 mm", 0,
                  num(run.get("mm"), -1))


def check_k2(rep: Report, text: str, d: dict) -> None:
    for ident, creator in ((1, "kthread_create"), (2, "kthread_run")):
        create = line_with(text, f"K4 kthread k2: id={ident} create=")
        rep.check("K2", f"id={ident}: 创建行存在（{creator}）", True,
                  create is not None)
        if not create:
            continue
        rep.check("K2", f"id={ident}: 走的是 {creator}", creator,
                  create.get("create"))
        rep.check("K2", f"id={ident}: 子任务 pid > kthreadd", True,
                  num(create.get("pid")) > d["kthreadd_pid"])
        rep.check("K2", f"id={ident}: 内核线程没有用户 mm", 0, num(create.get("mm"), -1))
        rep.check("K2", f"id={ident}: PF_KTHREAD", 1, num(create.get("kthread")))

        body = line_with(text, f"K4 kthread body: id={ident} ")
        rep.check("K2", f"id={ident}: 函数体真的在跑（从线程里自报 pid）", True,
                  body is not None)
        if body:
            rep.check("K2", f"id={ident}: 函数体自报 pid == 任务 pid", num(create.get("pid")),
                      num(body.get("pid")))
            rep.check("K2", f"id={ident}: 函数体所在任务 mm == NULL", 0,
                      num(body.get("mm"), -1))
            rep.check("K2", f"id={ident}: 函数体所在任务是内核线程", 1,
                      num(body.get("kthread")))

        started = line_with(text, f"K4 kthread k2: id={ident} started=")
        rep.check("K2", f"id={ident}: 启动观测行存在", True, started is not None)
        if started:
            rep.check("K2", f"id={ident}: 函数体已经开始", 1, num(started.get("started")))
            rep.check("K2", f"id={ident}: 计数器推进（prologue + 首轮）", 2,
                      num(started.get("ticks")))

        stop = line_with(text, f"K4 kthread k2: id={ident} stop_ret=")
        rep.check("K2", f"id={ident}: 停止行存在", True, stop is not None)
        if stop:
            rep.check("K2", f"id={ident}: kthread_stop 拿回函数体的返回值", 
                      d["ret_stopped"], num(stop.get("stop_ret")))
            rep.check("K2", f"id={ident}: 函数体看到 kthread_should_stop()", 1,
                      num(stop.get("saw_stop")))

        dead = line_with(text, f"K4 kthread k2: id={ident} state=")
        rep.check("K2", f"id={ident}: 退出观测行存在", True, dead is not None)
        if dead:
            rep.check("K2", f"id={ident}: 任务已 TASK_DEAD", d["task_dead"],
                      num(dead.get("state")))
            rep.check("K2", f"id={ident}: 任务已离开运行队列", 0, num(dead.get("on_rq"), -1))
            rep.check("K2", f"id={ident}: 停止后计数器冻结", 1, num(dead.get("frozen")))
            rep.check("K2", f"id={ident}: 停止后 fn 不再推进",
                      num(stop.get("ticks")) if stop else -1,
                      num(dead.get("ticks_now")))


def check_case_k3(rep: Report, text: str, d: dict) -> None:
    k3 = line_with(text, "K4 kthread k3: parent_pid=")
    rep.check("K3", "K3 父任务行存在（vacuous ⇒ FAIL）", True, k3 is not None)
    if not k3:
        return
    rep.check("K3", "父任务此刻没有 mm（kernel_init 尚未 execve）", 0,
              num(k3.get("parent_mm"), -1))
    rep.check("K3", "探针用的 CLONE_FS 位 == include/uapi/linux/sched.h",
              d["clone_fs"], num(k3.get("clone_fs")))
    rep.check("K3", "探针用的 CLONE_FILES 位 == include/uapi/linux/sched.h",
              d["clone_files"], num(k3.get("clone_files")))
    probe_flags = num(k3.get("clone_fs")) | num(k3.get("clone_files"))
    rep.check("K3", "两位正是 rest_init() 给 kthreadd 用的集合",
              d["kthreadd_flags"], probe_flags)
    rep.check("K3", "create_kthread() 给 daemon 子线程的集合含同样两位",
              d["kthreadd_flags"],
              d["kthread_flags"] & d["kthreadd_flags"])

    kt = line_with(text, "K4 kthread k3: kt_pid=")
    rep.check("K3", "K3 kernel_thread 行存在", True, kt is not None)
    if kt:
        rep.check("K3", "kernel_thread 子任务与父共享 fs（指针相同）", 1,
                  num(kt.get("fs_same")))
        rep.check("K3", "kernel_thread 子任务与父共享 files（指针相同）", 1,
                  num(kt.get("files_same")))
        rep.check("K3", "fs/files 指针非 0（共享的是真表）", True,
                  num(kt.get("fs"), 0) > 0 and num(kt.get("files"), 0) > 0)
        rep.check("K3", "kernel_thread 子任务没有用户 mm", 0, num(kt.get("kt_mm"), -1))
        rep.check("K3", "kernel_thread 子任务 thread.tp == 0（无 TLS）", 0,
                  num(kt.get("tp"), -1))
        rep.check("K3", "子任务保存帧的 rb3 == 0", 0, num(kt.get("frame_rb3"), -1))
        rep.check("K3", "子任务保存帧的 rd8 == 0（内核线程没有返回值）", 0,
                  num(kt.get("frame_rd8"), -1))
        rep.check("K3", "子任务入口 == 镜像里的 dadao_ret_from_fork",
                  d["ret_from_fork"], num(kt.get("frame_ip")))

    mm = line_with(text, "K4 kthread k3: mm_pid=")
    rep.check("K3", "K3 有 mm 的父任务行存在", True, mm is not None)
    if mm:
        rep.check("K3", "父任务有 mm 时 kernel_thread 子仍无 mm", 0,
                  num(mm.get("kt_mm"), -1))
        rep.check("K3", "CLONE_VM 取的引用被 arch 钩子还掉（mm_users 不变）",
                  num(mm.get("mm_users_pre")), num(mm.get("mm_users_post")))
        rep.check("K3", "父 mm 就是临时装上的那一个", True,
                  num(mm.get("mm_parent_mm"), 0) > 0)

    fork = line_with(text, "K4 kthread k3: fork_pid=")
    rep.check("K3", "K3 fork 对照行存在", True, fork is not None)
    if fork:
        rep.check("K3", "fork 子任务有地址空间", True, num(fork.get("fork_mm"), 0) > 0)
        rep.check("K3", "fork 子的 mm 与父不同（私有副本）", 1,
                  num(fork.get("fork_mm_diff")))
        rep.check("K3", "fork 子 asid 与父不同", True,
                  num(fork.get("asid_parent")) != num(fork.get("asid_child")))
        rep.check("K3", "两侧 asid 都在 16 位空间内", True,
                  all(0 < num(fork.get(k), -1) <= 0xFFFF
                      for k in ("asid_parent", "asid_child")))


# ---------------------------------------------------------------------------
# self-check: mutate the capture, every group must flip
# ---------------------------------------------------------------------------

def mutate(text: str, group: str) -> str:
    if group == "K1":
        return (text
                .replace("K4 kthread k1: present=1 pid=2",
                         "K4 kthread k1: present=1 pid=3")
                .replace("k1-kthreadd-pid want=0x2 got=0x2 ok",
                         "k1-kthreadd-pid want=0x2 got=0x3 FAIL"))
    if group == "K2":
        return (text
                .replace("id=1 stop_ret=0x4b54 saw_stop=1",
                         "id=1 stop_ret=0x4b4c saw_stop=0")
                .replace("k2-stop-ret want=0x4b54 got=0x4b54 ok",
                         "k2-stop-ret want=0x4b54 got=0x4b4c FAIL"))
    if group == "K3":
        return (text
                .replace(" frame_rb3=0x0 ", " frame_rb3=0x1 ")
                .replace(" frame_rd8=0x0 ", " frame_rd8=0x1 "))
    raise SystemExit(f"k4_kthread_probe: no mutation for group {group}")


def run_selfcheck(rc: int, text: str, d: dict) -> int:
    problems = []
    for group in ("K1", "K2", "K3"):
        rep = Report()
        with contextlib.redirect_stdout(io.StringIO()):
            if group == "K1":
                check_k1(rep, rc, mutate(text, "K1"), d)
            elif group == "K2":
                check_k2(rep, mutate(text, "K2"), d)
            else:
                check_case_k3(rep, mutate(text, "K3"), d)
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
    "no-dead-wait": {
        # m18-linux-009 (ISS-494): drop the bounded event wait and read the
        # task state immediately — the pre-fix race.  The behavioural red is
        # timing-dependent, so the source-level S7 assertion is the
        # deterministic verdict; the restored image is booted green below.
        "file": SELFTEST_C,
        "old": "\t/* Wait (bounded) for the *event*: do_exit() reaching TASK_DEAD. */\n"
               "\tif (!k4kt_wait_dead(t))\n"
               "\t\tk4kt_fail(K4KT_FAIL_K2, \"k2-task-dead-wait\",\n"
               "\t\t\t  (unsigned long)READ_ONCE(t->__state));\n",
        "new": "\t/* injected: read the task state without waiting for the event */\n",
        "group": "S",
        "why": "K2 退回 kthread_stop() 后立即读任务态（不等 TASK_DEAD 事件）",
    },
    "no-kthreadd": {
        "file": INIT_MAIN_C,
        "old": "\tpid = kernel_thread(kthreadd, NULL, NULL, CLONE_FS | CLONE_FILES);\n",
        "new": "\tpid = 0;\t/* injected: rest_init() never creates kthreadd */\n",
        "group": "K1",
        "why": "rest_init() 不建 kthreadd（K1 的 pid/名字必然红）",
    },
    "kt-keeps-mm": {
        "file": PROCESS_C,
        "old": "\t\tif (args->kthread && p->mm) {\n",
        "new": "\t\tif (0 && args->kthread && p->mm) {\n",
        "group": "K3",
        "why": "kernel_thread 钩子保留 copy_mm 共享的父 mm（子 mm 非空）",
    },
    "no-stop-bit": {
        "file": KTHREAD_C,
        "old": "\treturn test_bit(KTHREAD_SHOULD_STOP, &to_kthread(current)->flags);\n",
        "new": "\treturn false;\t/* injected: the stop request never arrives */\n",
        "group": "K2",
        "why": "kthread_should_stop() 恒假（函数体看不到停止请求）",
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
        # The expectations are the *pristine* tree's (`d`): an injection
        # changes the rule under test, not what the rule is derived from —
        # re-deriving from the corrupted source would move the reference the
        # red verdict is measured against.
        if spec["group"] == "S":
            with contextlib.redirect_stdout(io.StringIO()):
                check_k2_dead_wait(rep)
            print(f"[INJECT] {name}: S7 red checks = {len(rep.failed)}")
            for item in rep.failed[:4]:
                print(f"[INJECT]   {item}")
            if not rep.failed:
                print(f"[INJECT] {name}: FAIL: nothing went red")
                return 1
        else:
            rc, run = boot(f"inject-{name}", firmware())
            with contextlib.redirect_stdout(io.StringIO()):
                if spec["group"] == "K1":
                    check_k1(rep, rc, run, d)
                elif spec["group"] == "K2":
                    check_k2(rep, run, d)
                else:
                    check_case_k3(rep, run, d)
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
        check_static(green, rc_build, snap, d)
        check_k1(green, rc, run, d)
        check_k2(green, run, d)
        check_case_k3(green, run, d)
    print(f"[INJECT] {name}: back to green rc={rc} failures={len(green.failed)}")
    return 0 if not green.failed else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def derivations(snap: dict) -> dict:
    config = snap["config"]
    shift = num(config_value(config, "CONFIG_PAGE_SHIFT"))
    if shift < 0:
        raise SystemExit("k4_kthread_probe: the image's .config has no CONFIG_PAGE_SHIFT")
    off_bits, contract_shift = spec_page_geometry()
    syms = snap["syms"]
    if "dadao_ret_from_fork" not in syms:
        raise SystemExit("k4_kthread_probe: the image has no dadao_ret_from_fork")
    flags = caller_flags()
    return {
        "shift": shift,
        "page_size": 1 << shift,
        "page_shift": contract_shift,
        "page_offset_bits": off_bits,
        "kthreadd_pid": kthreadd_pid(),
        "task_dead": task_dead(),
        "ret_stopped": selftest_ret("K4KT_RET_STOPPED"),
        "ret_limit": selftest_ret("K4KT_RET_LIMIT"),
        "fail_codes": selftest_fail_codes(),
        "check_names": selftest_check_names(),
        "clone_fs": clone_bit("CLONE_FS"),
        "clone_files": clone_bit("CLONE_FILES"),
        "kthreadd_flags": flags["kthreadd"],
        "kthread_flags": flags["kthread"],
        "ret_from_fork": syms["dadao_ret_from_fork"],
        "guest_max": exit_segments()["guest_max"],
        "syms": syms,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="K4 kernel-thread probe")
    ap.add_argument("--selfcheck", action="store_true",
                    help="mutate the captured run and show every group flips")
    ap.add_argument("--inject", action="append", choices=sorted(INJECTIONS),
                    help="corrupt a source, rebuild, assert red, restore, re-green")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    rc_build, snap = (0, None) if args.skip_build else build_image("k4kthread")
    if snap is None and not args.skip_build:
        rep = Report()
        check_static(rep, rc_build, None, {})
        return 1
    if snap is None:
        raise SystemExit("k4_kthread_probe: --skip-build needs an image in the build tree")
    d = derivations(snap)

    if args.inject:
        rc = 0
        for name in args.inject:
            rc |= run_inject(name, d)
        return rc

    rc, text = boot("k4kthread", firmware())
    if args.selfcheck:
        return run_selfcheck(rc, text, d)

    rep = Report()
    check_static(rep, rc_build, snap, d)
    check_k1(rep, rc, text, d)
    check_k2(rep, text, d)
    check_case_k3(rep, text, d)

    # A K4 FAIL line (the kernel's own verdict) is never a pass.
    rep.check("K1", "内核没有自报 FAIL 行", [],
              re.findall(r"^K4 kthread FAIL:.*$", text, re.MULTILINE))
    print()
    if rep.failed:
        print(f"k4_kthread_probe: {rep.total - len(rep.failed)}/{rep.total} passed; "
              f"{len(rep.failed)} FAILED")
        for item in rep.failed:
            print(f"  - {item}")
        return 1
    print(f"k4_kthread_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
