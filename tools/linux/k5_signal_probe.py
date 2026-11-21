#!/usr/bin/env python3
"""k5_signal_probe.py — M14 signal-frame gate (`m14-linux-046`).

The kernel side is `arch/dadao/kernel/k5_signal_selftest.c` (plus the user
program in `kernel/trap.S`), built as a probe image with
`CONFIG_DADAO_K5_SIGNAL_SELFTEST`; this gate builds that image, boots it on
Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from:

  S2  the frame round trip.  A handler installed with `rt_sigaction`
      (SA_RESTORER, no SA_ONSTACK) receives SIGUSR1; it checks the frame image it
      was handed (`uc->uc_mcontext.regs` at the offsets `uapi/asm/ucontext.h`
      fixes) against what the program put in the registers, makes one balanced
      `call`, and scribbles over every callee-saved bank (`rd32`-`rd63`,
      `rb32`-`rb63`, `rf32`-`rf63`, `rb2`, `rd1`, the FCSR).  After the
      restorer's `rt_sigreturn` the kernel compares the restored frame with the
      one it snapshotted at the raise: all four banks bit-identical — the `ra`
      stack with `RACNT`/`MRPTR` (spec/SimRISC-00 §2.4), the FCSR at its
      architectural value (§2.3: its write port masks the read-only qNaN bits),
      every callee-saved register — and `ip` exactly four bytes on, because the
      interrupted context resumes after the trap.

  S3  the default action: the same program raises SIGTERM with no handler, so
      `do_group_exit()` must end the task (`exit_code & 0x7f == SIGTERM`, no
      exit status).

  S4  the alternate stack: `sigaltstack(2)` + SA_ONSTACK, and the frame must be
      built inside the alternate stack while the handler still sees the
      interrupted context (the `sigsp()` branch of `get_sigframe`).

The expectations that are facts about the *source* (the 2048-byte layout, the
`SA_RESTORER` convention, the RA push rules, the data-page contract between the
C probe and the assembly) are asserted statically in `static_recon()`; a boot
cannot show them.

Exit status: 0 = every case and every injection held; 1 = at least one FAIL;
2 = an input could not be derived (kernel source / build tree / toolchain).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                          # noqa: E402
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import make_vmlinux as make_vmlinux         # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("M46_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-046") / "check-linux-k46")
SOURCE = linux_paths.linux_source_dir()

#: Every milestone boundary pinned off, and only this probe compiled in
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
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "y",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

TIMEOUT_BUILD = int(os.environ.get("M46_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("M46_QEMU_TIMEOUT", "240"))
JOBS = os.environ.get("JOBS", "32")

#: The assertions the image must report, per phase.  A case with no line at all
#: is a FAIL, not a silent pass (`judge()` checks presence explicitly).
CASES = {
    "s2": (
        "handler-runs", "handler-sig", "handler-info-off", "handler-uc-off",
        "handler-frame-image", "handler-ras-below", "setup-ret",
        "snapshot-racnt", "snapshot-mrptr", "snapshot-status", "fcsr-masked",
        "fcsr-snapshot-arch", "handler-sp-below-user-sp", "handler-sp-aligned",
        "rd-bank", "rb-bank", "ra-bank", "rf-bank", "resume-ip", "raise-seen",
        "verify-seen", "exited-cleanly",
    ),
    "s3": ("died-by-signal", "no-exit-status", "no-handler-ran"),
    "s4": (
        "handler-runs", "handler-frame-image", "handler-ras-below", "setup-ret",
        "ss-ret",
        "handler-sp-in-altstack", "handler-sp-aligned", "snapshot-racnt",
        "snapshot-mrptr", "fcsr-snapshot-arch", "rd-bank", "rb-bank", "ra-bank",
        "rf-bank", "resume-ip", "altframe-seen", "exited-cleanly",
    ),
}

#: The three phases the program runs, in order, and the exit status each must
#: leave behind (`exit_code` low 7 bits / high bits, `wait_task_zombie`'s shape).
PHASES = (
    # script, state, status, code
    ("0", 32, 0x0, 0),
    ("1", 32, 0xF, 0),
    ("2", 32, 0x0, 0),
)


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

def check_lines(text: str) -> list[tuple[str, str]]:
    """(name, verdict) for every `M46 check` line the kernel printed."""
    out = []
    for line in text.splitlines():
        m = re.match(r"M46 check (\S+) want=(\S+) got=(\S+) (ok|FAIL)$", line)
        if m:
            out.append((m.group(1), m.group(4)))
    return out


def phase_lines(text: str) -> list[tuple[str, int, int, int]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"M46 phase: script=(\d+) state=(\d+) status=(0x[0-9a-f]+) "
                     r"code=(\d+)$", line)
        if m:
            out.append((m.group(1), int(m.group(2)), int(m.group(3), 16),
                        int(m.group(4))))
    return out


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    value = config_value(config, symbol)
    return value is not None and value not in ("n", "0", "")


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def build_image(label: str = "m46") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k5_signal_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k5_signal_probe: build timed out (124 is a FAIL)",
              file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-4000:], file=sys.stderr)
        print((proc.stderr or "")[-4000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_m46.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k5_signal_probe: {kernel} missing")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k5_signal_probe: qemu-system-dadao missing "
                         "(make install-host)")
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

    rep.check(f"B{s}", "镜像跑到探针自检", True, "M46 selftest: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("M46 selftest FAIL")])

    rows = check_lines(text)
    bad = [name for name, verdict in rows if verdict != "ok"]
    rep.check(f"B{s}", "内核自评的每条 M46 check 都 ok", [], bad)

    seen = {name for name, _ in rows}
    for case, names in CASES.items():
        for name in names:
            # A case with no assertion at all must be FAIL, not silently absent.
            rep.check(f"B{s}", f"{case}-{name} 的断言存在（vacuous ⇒ FAIL）",
                      True, f"{case}-{name}" in seen)

    got = phase_lines(text)
    rep.check(f"B{s}", "三个阶段各跑了一次（script 0/1/2）", [p[0] for p in PHASES],
              [p[0] for p in got])
    for want, actual in zip(PHASES, got):
        script, state, status, code = want
        rep.check(f"S{script}{s}", f"script {script} 的任务退出状态", (state,
                  status, code), actual[1:])
    rep.check(f"B{s}", "探针自检跑完（不是半路死掉）", True,
              "M46 selftest: probe cases done" in text)
    rep.check(f"B{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)


# ---------------------------------------------------------------------------
# static recon
# ---------------------------------------------------------------------------

def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"k5_signal_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def defines(text: str, prefix: str) -> dict[str, int]:
    out = {}
    for m in re.finditer(rf"^#define\s+({prefix}\w*)\s+(0x[0-9a-fA-F]+|\d+)\b",
                         text, re.MULTILINE):
        out[m.group(1)] = int(m.group(2), 0)
    return out


def static_recon(rep: Report, snap: dict | None) -> None:
    rep.check("B", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]

    rep.check("B", "镜像配置：CONFIG_DADAO_K5_SIGNAL_SELFTEST=y", True,
              config_enabled(config, "CONFIG_DADAO_K5_SIGNAL_SELFTEST"))
    rep.check("B", "别的探针符号全关", [],
              [sym for sym in CONFIG_PINS
               if sym != "CONFIG_DADAO_K5_SIGNAL_SELFTEST"
               and CONFIG_PINS[sym] == "y" and config_enabled(config, sym)])

    # The frame: four 64-slot banks, 2048 B, rd[0] = status, rb[0] = ip -- and
    # the anonymous unions that keep every asm offset derived from a member.
    ptrace_h = kernel_text("arch/dadao/include/asm/ptrace.h")
    rep.check("B", "pt_regs 是 2048 B（4 × 64 槽）", True,
              "4 * 64 * sizeof(unsigned long)" in ptrace_h
              and "union {" in ptrace_h)
    rep.check("B", "rd[0] 槽 = status、rb[0] 槽 = ip", True,
              "unsigned long status;" in ptrace_h
              and "unsigned long ip;" in ptrace_h
              and "offsetof(struct pt_regs, status) == 0" in ptrace_h
              and "offsetof(struct pt_regs, ip) == 512" in ptrace_h
              and "offsetof(struct pt_regs, ra) == 1024" in ptrace_h
              and "offsetof(struct pt_regs, rf) == 1536" in ptrace_h)
    uapi_ptrace = kernel_text("arch/dadao/include/uapi/asm/ptrace.h")
    rep.check("B", "uapi user_regs_struct 与内核帧同形状", True,
              "unsigned long rd[64];" in uapi_ptrace
              and "unsigned long rb[64];" in uapi_ptrace
              and "unsigned long ra[64];" in uapi_ptrace
              and "unsigned long rf[64];" in uapi_ptrace
              and "unsigned long status;" in uapi_ptrace
              and "unsigned long ip;" in uapi_ptrace)

    # The signal frame: the whole register file in one copy, and the ucontext
    # member offsets user code reads (168 = flags+link+stack+1024-bit mask).
    sig_c = kernel_text("arch/dadao/kernel/signal.c")
    rep.check("B", "signal.c 用一次 copy 写/读整个 2048 B 寄存器文件", True,
              "copy_to_user(sc, regs, sizeof(*regs))" in sig_c
              and "copy_from_user(regs, sc, sizeof(*regs))" in sig_c)
    rep.check("B", "uc_mcontext 偏移 = 168（uapi/asm/ucontext.h）", True,
              "offsetof(struct ucontext, uc_mcontext) == 168" in sig_c)
    rep.check("B", "sigcontext = 寄存器文件 + 4 个保留字", True,
              "sizeof(struct sigcontext) ==" in sig_c)
    rep.check("B", "uapi/asm/ucontext.h 把 uc_mcontext 放最后", True,
              kernel_text("arch/dadao/include/uapi/asm/ucontext.h")
              .rfind("uc_mcontext") > 0
              and kernel_text("arch/dadao/include/uapi/asm/ucontext.h")
              .find("uc_sigmask") < kernel_text(
                  "arch/dadao/include/uapi/asm/ucontext.h").find("uc_mcontext"))

    # The restorer: no vDSO, so the pushed return address is the caller's
    # SA_RESTORER trampoline, and the flag is mandatory.
    rep.check("B", "SA_RESTORER 由本端口 uapi 定义（无 vDSO）", True,
              "#define SA_RESTORER" in
              kernel_text("arch/dadao/include/uapi/asm/signal.h"))
    rep.check("B", "缺 SA_RESTORER ⇒ setup_rt_frame -EFAULT", True,
              "if (!(ksig->ka.sa.sa_flags & SA_RESTORER))" in sig_c
              and "return -EFAULT;" in sig_c)
    rep.check("B", "handler 的返回地址走 RA 栈（dadao_ra_push）", True,
              "dadao_ra_push(regs" in sig_c)
    for rule, needle in (
        ("C2 递归折叠", "DADAO_RAS_RECUR_MAX"),
        ("C3a 普通压栈", "racnt < DADAO_RAS_ENTRIES"),
        ("C3b MemRAS 溢出写回", "put_user(ra[1]"),
        ("RASOF 具名拒绝", "if (!mrptr)"),
    ):
        rep.check("B", f"RA 压栈按 spec/SimRISC-00 §2.4.1：{rule}", True,
                  needle in sig_c)

    # The restore path answers the resume policy, and the dispatcher hands the
    # frame-restoring syscall's answer straight to the stub.
    rep.check("B", "rt_sigreturn 返回 RESUME_RETRY（恢复的 ip 就是返回地址）",
              True, "return DADAO_TRAP_RESUME_RETRY;" in sig_c)
    proc = kernel_text("arch/dadao/kernel/process.c")
    rep.check("B", "rt_sigreturn 在分发里单独成路（不写回 rd8）", True,
              "__NR_rt_sigreturn" in proc
              and "return (unsigned long)dadao_call_syscall(regs" in proc)
    common = kernel_text("arch/dadao/kernel/entry_common.c")
    rep.check("B", "arch_do_signal_or_restart 走 dadao_handle_signal", True,
              "dadao_handle_signal(&ksig, regs)" in common)
    rep.check("B", "SKIP 的 +4 由帧的 ip 承担（信号帧存恢复地址）", True,
              "regs->ip += DADAO_INSN_BYTES;" in common)

    # The probe's data-page contract: the C probe and the assembly must agree
    # offset for offset, or the program reads the wrong object.
    c_defs = defines(kernel_text("arch/dadao/kernel/k5_signal_selftest.c"),
                     "M46_K_")
    asm_defs = defines(kernel_text("arch/dadao/kernel/trap.S"), "M46_K_")
    shared = sorted(set(c_defs) & set(asm_defs))
    rep.check("B", "探针数据页偏移在 C 与汇编两侧一致", [],
              [name for name in shared if c_defs[name] != asm_defs[name]])
    rep.check("B", "两侧确实共享同一组偏移（不是空集）", True,
              len(shared) >= 10)
    rep.check("B", "探针的数据页映射为 MAP_SHARED（私有映射会被 COW）", True,
              "MAP_SHARED" in kernel_text(
                  "arch/dadao/kernel/k5_signal_selftest.c"))

    # The rework rule this task inherits (m14-linux-045 R1): the port owns
    # `arch/dadao/**`, not the generic signal/entry code.  Exact entries, so the
    # port's own `arch/dadao/kernel/signal.c.patch` is not mistaken for one.
    series = [line.strip() for line in
              (_REPO / "components" / "linux" / "series")
              .read_text(encoding="utf-8").splitlines() if line.strip()]
    generic = [entry for entry in series
               if entry in ("kernel/signal.c.patch",
                            "kernel/entry/common.c.patch")]
    rep.check("B", "补丁集不含通用 kernel/signal.c、kernel/entry/common.c hunk",
              [], generic)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> (file, needle, replacement, case that must go red, why)
INJECTIONS = {
    "no-ra-save": (
        "arch/dadao/kernel/signal.c",
        "\treturn copy_to_user(sc, regs, sizeof(*regs)) ? -EFAULT : 0;\n",
        "\tif (copy_to_user(sc, regs, sizeof(*regs)))\n"
        "\t\treturn -EFAULT;\n"
        "\treturn clear_user((void __user *)&sc->ra, sizeof(regs->ra)) ?"
        " -EFAULT : 0;\n",
        "s2", "帧不保存 ra 栈（RACNT/MRPTR 与 63 条条目都丢）"),
    "no-rf0-restore": (
        "arch/dadao/kernel/signal.c",
        "\tregs->status = DADAO_STATUS_USER;\n\treturn 0;\n",
        "\tregs->status = DADAO_STATUS_USER;\n\tregs->rf[0] = 0;\n\treturn 0;\n",
        "s2", "rt_sigreturn 不恢复 rf0（FCSR 清零）"),
    "no-sigpending": (
        "arch/dadao/kernel/entry_common.c",
        "\tif (!get_signal(&ksig))\n\t\treturn;\n",
        "\tclear_thread_flag(TIF_SIGPENDING);\n\treturn;\n",
        "s3", "信号位被消费而没投递（等价于发送端没置 TIF_SIGPENDING）"),
    "ra-push-no-shift": (
        "arch/dadao/kernel/signal.c",
        "\t\tfor (i = DADAO_RAS_ENTRIES + 1 - racnt;\n"
        "\t\t     i <= DADAO_RAS_ENTRIES; i++)\n"
        "\t\t\tra[i - 1] = ra[i];\n",
        "\t\t/* injected: write the top without moving the window */\n",
        "s2", "RA 压栈不搬动窗口（把程序自己的 call 条目盖掉）"),
    "no-ip-set": (
        "arch/dadao/kernel/signal.c",
        "\tregs->ip = (unsigned long)ksig->ka.sa.sa_handler;\n",
        "\t/* injected: the frame never reaches the handler */\n",
        "s2", "setup_rt_frame 不把 ip 指向 handler"),
}


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
        # A run killed between the write and the `finally` leaves the injected
        # text in the tree; every later verdict would then be about the wrong
        # source.  Name that instead of reporting a red/green.
        if repl in text:
            raise SystemExit(
                f"k5_signal_probe: {rel} still carries the '{name}' injection "
                f"(a previous run was killed before its restore); fix the "
                f"source before re-running")
        return
    path.write_text(text.replace(needle, repl, 1), encoding="utf-8")
    try:
        rc, snap = build_image(f"injected:{name}")
        if rc != 0 or snap is None:
            rep.check(f"INJECT {name}", f"注入后镜像可构建（{why}）", 0, rc)
            return
        # The injected image must still *be* this probe's image: a build that
        # lost the symbol (a concurrent writer's config slice, a dependency that
        # olddefconfig dropped) would boot an image that never reports a case,
        # and "no case line" must not be mistaken for a red.
        enabled = config_enabled(snap["config"],
                                 "CONFIG_DADAO_K5_SIGNAL_SELFTEST")
        rep.check(f"INJECT {name}", "注入镜像仍带本探针符号", True, enabled)
        if not enabled:
            return
        rc, out = boot(f"inject-{name}", rom)
        rows = check_lines(out)
        red = [n for n, verdict in rows if verdict != "ok"]
        case_ok = [n for n, verdict in rows
                   if verdict == "ok" and n.startswith(case)]
        began = "M46 selftest: begin" in out
        died = any(tok in out for tok in ("M46 selftest FAIL",
                                          "dadao: die mode=", "Kernel panic",
                                          "recursive supv exception"))
        hung = rc == 124
        rep.info(f"inject {name}: rc={rc} red={red[:5]} began={began} "
                 f"died={died} hung={hung}")
        observed = bool(red) or died or hung or (began and not case_ok)
        rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True, observed)
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        rc, snap = build_image("restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if snap is not None:
            rc2, out2 = boot(f"restored-{name}", rom)
            rep.check(f"INJECT {name}", "还原后回绿（无红项）", [],
                      [n for n, verdict in check_lines(out2)
                       if verdict != "ok"])


def selfcheck() -> int:
    """Prove the judging can fail: feed it a console that must be red."""
    rep = Report()
    text = (
        "M46 selftest: begin pid=1 mm=0\n"
        "M46 check s2-handler-runs want=0x1 got=0x0 FAIL\n"
        "M46 check s2-ra-bank want=0x0 got=0x3 FAIL\n"
        "M46 phase: script=0 state=32 status=0x0 code=0\n"
        "M46 phase: script=1 state=32 status=0x0 code=0\n"
        "M46 selftest: FAIL mask=0x74\n"
    )
    judge(rep, text, 1)
    red = rep.failed
    print(f"[SELFCHECK] red checks: {len(red)}")
    for name in red[:8]:
        print(f"[SELFCHECK]   {name}")
    if not red:
        print("[SELFCHECK] FAIL: a broken console produced no red check")
        return 1
    print("[SELFCHECK] PASS: the judging goes red on a broken console")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="M14 signal-frame probe")
    parser.add_argument("--selfcheck", action="store_true",
                        help="prove the judging can fail (no build, no boot)")
    parser.add_argument("--inject", action="append", default=[], metavar="NAME",
                        help=f"one of: {', '.join(sorted(INJECTIONS))}")
    parser.add_argument("--no-inject", action="store_true",
                        help="only the cases (no injection rounds)")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

    rep = Report()
    rc, snap = build_image()
    static_recon(rep, snap)
    if snap is None:
        print("k5_signal_probe: no image; judging stops here", file=sys.stderr)
        return 1
    rom = firmware()
    rc, out = boot("m46", rom)
    judge(rep, out, rc)

    if not args.no_inject:
        names = args.inject or sorted(INJECTIONS)
        for name in names:
            if name not in INJECTIONS:
                raise SystemExit(f"k5_signal_probe: unknown injection {name!r}")
            run_injection(rep, name, rom)

    print()
    if rep.failed:
        print(f"k5_signal_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"k5_signal_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
