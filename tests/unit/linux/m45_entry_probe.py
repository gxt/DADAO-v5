#!/usr/bin/env python3
"""m45_entry_probe.py — M14 entry/exit work-loop probe (`m14-linux-045`).

The kernel side is `arch/dadao/kernel/m45_entry_selftest.c` (plus the user
program in `kernel/trap.S`), built as a probe image with
`CONFIG_DADAO_M45_ENTRY_SELFTEST`; this gate builds that image, boots it on
Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from:

  E1  preemption: a user task runs a long loop (a user-only spin plus one
      `getpid` per outer iteration).  At iteration 4 the trap hook wakes a
      worker kernel thread and sets `TIF_NEED_RESCHED` on the looping task; the
      verdict is that the worker ran **while the loop still had iterations
      left** (`iters > b_ran_at`).  With no consumer for that bit the task
      returns to user mode every iteration and — single hart — the worker never
      runs at all, which is a difference the console shows, not a timing guess.
  E2  `TIF_SIGPENDING` reaches `get_signal()`: `SIGTERM` is sent to the looping
      task at its last iteration; the default action is `do_group_exit()`, so
      the boot task observes `exit_code & 0x7f == SIGTERM` (and no exit status).
      If the bit is never consumed the child finishes the loop and exits 0.
  E3  `in_hardirq()` and `get_irq_regs()` inside every asynchronous delivery:
      no delivery may see a false `in_hardirq()` or a `get_irq_regs()` that is
      not its own frame.
  E4  `user_mode(regs)`: a user-mode `trap cfx_umon` frame is true, a frame the
      tick took from kernel code is false — both counters must be non-zero, so
      the evidence is two entry kinds, not one frame judged twice.

The expectations that are facts about the *source* (the criterion's shape, the
entry stubs writing `status`, the generic call sites) are asserted statically in
`static_recon()`; a boot cannot show them.

Exit status: 0 = every case passed; 1 = at least one FAIL; 2 = an input could
not be derived (kernel source / build tree / toolchain missing).
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

from tools.linux import config_pins                          # noqa: E402  (pins)
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import make_vmlinux as make_vmlinux         # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("M45_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-045") / "check-linux-m45")
SOURCE = linux_paths.linux_source_dir()

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
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "y",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

#: The probe image is deliberately rootfs-free: its verdict is a *kernel* task
#: (`M45 selftest: begin pid=1 mm=0`) that runs from `late_initcall`, so a
#: built-in initramfs would hand the machine to `/init` first and the probe
#: would never run.  The shared build tree keeps whatever image configured it
#: last (`ISS-470` class), so the slice empties it too.  It is not a
#: ``CONFIG_DADAO_*`` symbol, so it cannot live in ``CONFIG_PINS`` (that dict
#: must equal the Kconfig set exactly, `tests/unit/linux/check_config_pins.py`).
NO_INITRAMFS = ['CONFIG_INITRAMFS_SOURCE=""']

TIMEOUT_BUILD = int(os.environ.get("M45_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("M45_QEMU_TIMEOUT", "180"))
JOBS = os.environ.get("JOBS", "32")

#: The cases this image must report (the check-name prefix each one uses).
CASES = ("e1", "e2", "e3", "e4")


class Report:
    def __init__(self) -> None:
        self.total = 0
        self.failed: list[str] = []

    def check(self, group: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        print(f"[{'PASS' if ok else 'FAIL'}] {group}: {name}: "
              f"want={expected!r} got={actual!r}")
        if not ok:
            self.failed.append(f"{group}: {name}")
        return ok

    def info(self, text: str) -> None:
        print(f"[INFO] {text}")


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


def check_lines(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"M45 check (\S+) want=(\S+) got=(\S+) (ok|FAIL)$", line)
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(4)}))
    return out


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    value = config_value(config, symbol)
    return value is not None and value not in ("n", "0", "")


def named(text: str, prefix: str) -> list[dict[str, str]]:
    return [kv(line) for line in text.splitlines() if line.startswith(prefix)]


def one(text: str, prefix: str) -> dict[str, str] | None:
    rows = named(text, prefix)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def build_image(label: str = "m45") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE + NO_INITRAMFS)
    if rc != 0:
        print(f"m45_entry_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    # Kbuild does not reliably re-evaluate the int Kconfig symbols used in
    # `#if`, and an injection round restores the sources after building; drop
    # every arch/dadao/kernel object so each image is compiled from the sources
    # on disk.
    for obj in (build_dir() / "arch/dadao/kernel").glob("*.o"):
        obj.unlink(missing_ok=True)
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("m45_entry_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-4000:], file=sys.stderr)
        print((proc.stderr or "")[-4000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_m45.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"m45_entry_probe: {kernel} missing")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("m45_entry_probe: qemu-system-dadao missing "
                         "(make install-host)")
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
# judging
# ---------------------------------------------------------------------------

def judge(rep: Report, text: str, rc: int, suffix: str = "") -> None:
    """The console of one probe run -> one verdict per case."""
    s = suffix

    rep.check(f"B{s}", "镜像跑到探针自检", True, "M45 selftest: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("M45 selftest FAIL")])

    rows = check_lines(text)
    bad = [name for name, row in rows if row["verdict"] != "ok"]
    rep.check(f"B{s}", "内核自评的每条 M45 check 都 ok", [], bad)
    seen = " ".join(name for name, _ in rows)
    for case in CASES:
        # A case with no assertion at all must be FAIL, not silently absent.
        rep.check(f"B{s}", f"{case} 的断言存在（vacuous ⇒ FAIL）", True,
                  case in seen)

    counts = one(text, "M45 selftest: iters=")
    rep.check(f"E1{s}", "循环计数行存在", True, counts is not None)
    if counts:
        iters = int(counts.get("iters", "0"), 0)
        b_ran = counts.get("b_ran")
        b_at = int(counts.get("b_ran_at", "0"), 0)
        rep.check(f"E1{s}", "worker 线程真的跑过", "1", b_ran)
        rep.check(f"E1{s}", "worker 在循环中途拿到 CPU（iters > b_ran_at）",
                  True, iters > b_at > 0)

    irq = one(text, "M45 selftest: sig_calls=")
    rep.check(f"E3{s}", "信号/中断观测行存在", True, irq is not None)
    if irq:
        rep.check(f"E3{s}", "没有一次投递落在 in_hardirq()=false", "0",
                  irq.get("bad_hardirq"))
        rep.check(f"E3{s}", "get_irq_regs() 每次都等于处理器收到的帧", "0",
                  irq.get("bad_regs"))
        rep.check(f"E3{s}", "异步投递确实发生过", True,
                  int(irq.get("irq_user", "0"), 0) +
                  int(irq.get("irq_kernel", "0"), 0) > 0)
        rep.check(f"E4{s}", "中断取自用户态（user_mode 真）", True,
                  int(irq.get("irq_user", "0"), 0) > 0)
        rep.check(f"E4{s}", "中断取自内核态（user_mode 假）", True,
                  int(irq.get("irq_kernel", "0"), 0) > 0)
        rep.check(f"E4{s}", "umon 帧 user_mode 全真", True,
                  int(irq.get("exit_user", "0"), 0) > 0)
        rep.check(f"E4{s}", "umon 帧 user_mode 没有一次假", 0,
                  int(irq.get("exit_kernel", "0"), 0))
        rep.check(f"E2{s}", "TIF_SIGPENDING 到达分发点（arch_do_signal_or_restart 带位进入）",
                  True, int(irq.get("sig_calls", "0"), 0) > 0)
    exitrow = one(text, "M45 exit: child=")
    rep.check(f"E2{s}", "子任务退出行存在", True, exitrow is not None)
    if exitrow:
        rep.check(f"E2{s}", "信号已发出", "1", counts.get("signal_sent") if counts else None)
        # exit_code's low 7 bits are the signal (wait_task_zombie's shape).
        code = int(exitrow.get("status", "0"), 0)
        rep.check(f"E2{s}", "任务被 SIGTERM 终止（低 7 位 = 15）", 15, code & 0x7f)
        rep.check(f"E2{s}", "没有普通退出状态（高位 = 0）", 0, code >> 8)
    if exitrow is not None:
        rep.check(f"D{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# static recon
# ---------------------------------------------------------------------------

CUR_CONFIG: list[str] = [""]


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"m45_entry_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def static_recon(rep: Report, snap: dict | None) -> None:
    rep.check("B", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]
    CUR_CONFIG[0] = config

    # The image really carries this probe and none of the others.
    rep.check("B", "镜像配置：CONFIG_DADAO_M45_ENTRY_SELFTEST=y", True,
              config_enabled(config, "CONFIG_DADAO_M45_ENTRY_SELFTEST"))
    rep.check("B", "镜像配置：无内建 initramfs（共享构建树不串味）", '""',
              config_value(config, "CONFIG_INITRAMFS_SOURCE"))
    rep.check("B", "别的探针符号全关", [],
              [sym for sym in CONFIG_PINS
               if sym != "CONFIG_DADAO_M45_ENTRY_SELFTEST"
               and CONFIG_PINS[sym] == "y"
               and config_enabled(config, sym)])

    # E4: the criterion is the user ruling's, and the entry stubs write the
    # field it reads -- all three vectors (supv frame, umon frame, async frame).
    ptrace_h = kernel_text("arch/dadao/include/asm/ptrace.h")
    rep.check("E4", "user_mode 判据 = (status & 0x3) != 0", True,
              "(regs->status & 0x3) != 0" in ptrace_h)
    entry_h = kernel_text("arch/dadao/include/asm/entry.h")
    rep.check("E4", "入口宏从 cg5 rc0（excp_prev_run_mode）写 status", True,
              "DADAO_SAVE_STATUS" in entry_h and "cg5, rc0" in entry_h)
    for rel, tag in (("arch/dadao/kernel/trap.S", "supv/umon 桩"),
                     ("arch/dadao/kernel/async_trap.S", "异步桩")):
        text = kernel_text(rel)
        if rel == "arch/dadao/kernel/trap.S":
            wrote = "DADAO_SAVE_STATUS" in text
        else:
            # ADR-0064 D5: the async stub writes status from cg15 rc0
            # (async_prev_run_mode), not from a cg5 frame.
            wrote = ("PT_STATUS" in text and "dadao_async_prev_mode" in text)
        rep.check("E4", f"{tag}都写 status（不再写 0）", True, wrote)
        rep.check("E4", f"{tag}不再把 status 写成 0", False,
                  re.search(r"st\.o\s+rd0, \[r\w+, PT_STATUS\]", text) is not None)

    # E1/E2: the work loop is the generic one, its tail is wired, and the
    # handler calls it.
    common = kernel_text("arch/dadao/kernel/entry_common.c")
    rep.check("E1", "syscall 出口走通用 exit_to_user_mode_loop", True,
              "syscall_exit_to_user_mode_prepare(regs)" in common
              and "exit_to_user_mode()" in common)
    rep.check("E1", "非 syscall 出口走 irqentry_enter/irqentry 用户态出口", True,
              "irqentry_enter(regs)" in common
              and "irqentry_exit_to_user_mode_prepare(regs)" in common)
    rep.check("E1", "出口前后保存/恢复本端口的 IE 字（否则 TIMER 永久被掩）",
              True, common.count("arch_local_irq_restore(flags)") >= 2)
    rep.check("E2", "本文件提供 arch_do_signal_or_restart 强定义", True,
              "void arch_do_signal_or_restart(struct pt_regs *regs)" in common)
    rep.check("E2", "它调用 get_signal()", True, "get_signal(&ksig)" in common)
    proc = kernel_text("arch/dadao/kernel/process.c")
    rep.check("E1", "umon 入口的 C 半调用 dadao_user_excp_handler→工作循环",
              True, "dadao_syscall_exit(regs)" in common
              and "dadao_user_excp_handler" in proc)
    syscalls = kernel_text("arch/dadao/kernel/syscalls.c")
    rep.check("E1", "syscall 入口 = enter_from_user_mode（通用入口状态机）",
              True, "dadao_syscall_enter(regs)" in syscalls
              and "enter_from_user_mode(regs)" in common)
    # E3: the asynchronous handler publishes its frame and runs in hard-IRQ
    # context.
    # The rework rule: this task must not carry a hunk in the generic tree.
    series = (_REPO / "components" / "linux" / "series").read_text(encoding="utf-8")
    rep.check("B", "补丁集不含通配目录 hunk（kernel/entry、mm/）", True,
              "kernel/entry/common.c.patch" not in series
              and not (_REPO / "components" / "linux" / "patches" / "kernel"
                       / "entry").exists()
              and not (_REPO / "components" / "linux" / "patches" / "mm").exists())

    time_c = kernel_text("arch/dadao/kernel/time.c")
    rep.check("E3", "异步处理器 set_irq_regs(regs)", True,
              "set_irq_regs(regs)" in time_c)
    rep.check("E3", "异步处理器恢复 set_irq_regs(old_regs)", True,
              "set_irq_regs(old_regs)" in time_c)
    rep.check("E3", "异步处理器 irq_enter_rcu/irq_exit_rcu", True,
              "irq_enter_rcu()" in time_c and "irq_exit_rcu()" in time_c)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> (file, needle, replacement, case that must go red, why)
INJECTIONS = {
    "no-work-loop": (
        "arch/dadao/kernel/entry_common.c",
        "\tlocal_irq_disable();\n"
        "\tif (syscall)\n"
        "\t\tsyscall_exit_to_user_mode_prepare(regs);\n"
        "\telse\n"
        "\t\tirqentry_exit_to_user_mode_prepare(regs);\n"
        "\texit_to_user_mode();\n",
        "\tlocal_irq_disable();\n",
        "e1", "出口不消费 `_TIF_WORK_MASK`（E1 与 E2 都失去消费者）"),
    "no-ie-restore": (
        "arch/dadao/kernel/entry_common.c",
        "\tirqentry_exit_to_user_mode_prepare(regs);\n"
        "\texit_to_user_mode();\n"
        "\tarch_local_irq_restore(flags);\n",
        "\tirqentry_exit_to_user_mode_prepare(regs);\n"
        "\texit_to_user_mode();\n",
        "e1", "去掉出口的 IE 存/恢复（真实红项以运行结果为准）"),
}


#: Injections whose outcome is *recorded* rather than required: the acceptance
#: asks for the real red item, and "no red" is a legitimate finding to report.
INFORMATIONAL = {"no-ie-restore"}


def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def run_injection(rep: Report, name: str, rom: str) -> None:
    rel, needle, repl, case, why = INJECTIONS[name]
    path = SOURCE / rel
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
        rc, snap = build_image(f"injected:{name}")
        if rc != 0 or snap is None:
            rep.check(f"INJECT {name}", f"注入后镜像可构建（{why}）", 0, rc)
            return
        rc, out = boot(f"inject-{name}", rom)
        rows = check_lines(out)
        red = [n for n, row in rows if row["verdict"] != "ok"]
        case_ok = [n for n, row in rows
                   if row["verdict"] == "ok" and n.lower().startswith(case.lower())]
        # A run that dies or hangs never prints the case at all; that is a red
        # too (the case cannot be "ok" if it never reported).
        died = any(tok in out for tok in ("M45 selftest FAIL", "dadao: die mode=",
                                         "Kernel panic", "recursive supv exception"))
        hung = rc == 124
        rep.info(f"inject {name}: rc={rc} red={red[:5]} died={died} hung={hung}")
        observed = (bool(red) or died or hung or not case_ok)
        if name in INFORMATIONAL:
            # Record what actually happened instead of demanding a red.
            rep.info(f"inject {name}: observed red={bool(red) or died or hung} "
                     f"(informational: {why})")
        else:
            rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True, observed)
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        rc, snap = build_image("restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if snap is not None:
            rc2, out2 = boot(f"restored-{name}", rom)
            rep.check(f"INJECT {name}", "还原后回绿（无红项）", [],
                      [n for n, row in check_lines(out2)
                       if row["verdict"] != "ok"])


def selfcheck() -> int:
    """Prove the judging can fail: feed it a console that must be red."""
    rep = Report()
    text = (
        "M45 selftest: begin pid=1 mm=0\n"
        "M45 selftest: iters=20 b_ran=0 b_ran_at=0 signal_sent=1 probe_hits=1\n"
        "M45 selftest: irq user=0 kernel=0 bad_hardirq=3 bad_regs=3 exit=0/0\n"
        "M45 check e1-worker-ran want=0x1 got=0x0 FAIL\n"
        "M45 check e2-died-by-signal want=0xf got=0x0 FAIL\n"
        "M45 exit: child=3 state=1 status=0x0 code=0 rounds=1\n"
    )
    CUR_CONFIG[0] = "CONFIG_DADAO_M45_ENTRY_SELFTEST=y\n"
    judge(rep, text, 0)
    red = rep.failed
    print(f"[SELFCHECK] red checks: {len(red)}")
    for name in red[:8]:
        print(f"[SELFCHECK]   {name}")
    if not red:
        print("[SELFCHECK] FAIL: a broken console produced no red check")
        return 1
    print("[SELFCHECK] PASS: the judging goes red on a broken console")
    return 0


def boot_series(count: int) -> int:
    """Build one image, then boot *the same image* `count` times.

    A stalled boot is exactly what this task's R2 async entry was fixing: the
    console stops mid-run (`K2 async user` lines stop, no `probe cases done`)
    and QEMU has to be killed at the timeout.  Each boot is judged on its own;
    one stall makes the run FAIL — there is no retry here on purpose.
    """
    rep = Report()
    rc, snap = build_image()
    static_recon(rep, snap)
    if snap is None or rc != 0:
        print("m45_entry_probe: no image; the boot series stops here",
              file=sys.stderr)
        return 1
    rom = firmware()
    stalls = 0
    for i in range(1, count + 1):
        run_rc, out = boot(f"boots-{i}", rom)
        if run_rc == 0 and "M45 selftest: probe cases done" in out:
            print(f"[PASS] boot {i}: rc=0 async="
                  f"{out.count('K2 async user')}", flush=True)
            continue
        stalls += 1
        tail = [line for line in out.splitlines() if line.strip()][-2:]
        print(f"[FAIL] boot {i}: rc={run_rc} async={out.count('K2 async user')} "
              f"last={tail}", flush=True)
    print(f"m45_entry_probe: boots={count} stalls={stalls}")
    return 0 if stalls == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="M14 entry/exit work-loop probe")
    parser.add_argument("--selfcheck", action="store_true",
                        help="prove the judging can fail (no build, no boot)")
    parser.add_argument("--boots", type=int, metavar="N",
                        help="build the image once and boot it N times; every "
                             "boot must end with 'probe cases done' (no retries)")
    parser.add_argument("--inject", action="append", default=[], metavar="NAME",
                        help=f"one of: {', '.join(sorted(INJECTIONS))}")
    parser.add_argument("--no-inject", action="store_true",
                        help="only the cases (no injection rounds)")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

    if args.boots:
        return boot_series(args.boots)

    rep = Report()
    rc, snap = build_image()
    static_recon(rep, snap)
    if snap is None:
        print("m45_entry_probe: no image; judging stops here", file=sys.stderr)
        return 1
    rom = firmware()
    rc, out = boot("m45", rom)
    # One machine-readable line: the evidence script judges the *boot*'s exit
    # status (124 = the timeout killed a stalled boot) separately from this
    # probe's verdict, which is 1 for any red.
    print(f"[INFO] m45 boot rc={rc} async={out.count('K2 async user')}",
          flush=True)
    judge(rep, out, rc)

    if not args.no_inject:
        names = args.inject or sorted(INJECTIONS)
        for name in names:
            if name not in INJECTIONS:
                raise SystemExit(f"m45_entry_probe: unknown injection {name!r}")
            run_injection(rep, name, rom)

    print()
    if rep.failed:
        print(f"m45_entry_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"m45_entry_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
