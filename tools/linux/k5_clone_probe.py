#!/usr/bin/env python3
"""k5_clone_probe.py — M14 K5 user clone/thread probe (`m14-linux-024`).

The kernel side is `arch/dadao/kernel/k5_clone_selftest.c` (+ the user program
in `kernel/trap.S`, the dispatcher in `kernel/syscalls.c` / `kernel/process.c`),
built as a probe image with `CONFIG_DADAO_K5_CLONE_SELFTEST`; this gate builds
that image, boots it on Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from
(contract-syscall §10/§11, spec/SimRISC-12 §1, `include/uapi/linux/sched.h`):

  C1 `CLONE_VM` shares the address space: the thread child's `mm` is the
     parent's, `context.asid` is the same, `mm_users` grew by one while it
     lived and came back after it exited.  The contrast is created in the same
     boot: a `fork` child has an `mm` of its own with a different ASID and the
     parent's `mm_users` untouched.
  C2 `CLONE_SETTLS`: the child's `rb3` (`rbtp`) is the `tls` argument and the
     parent's is unchanged.  The `tls` value is checked against the constant the
     user stub loaded (parsed from `kernel/trap.S`), so the kernel is shown to
     have read the *4th* argument (`CONFIG_CLONE_BACKWARDS`) rather than any
     other slot.
  C3 the child's entry: `rd8 = 0`, the parent's `clone` return is the child's
     tid.  The dual return itself is the user wrapper's half (§10) — the program
     branches on `rd8 == 0` exactly as musl's stub does.
  C4 `CLONE_THREAD`: one thread group (`tgid`, `group_leader`, `signal`) and
     shared `fs`/`files`/`sighand`; the thread's `getpid` answers the group's
     pid, and a fork child has none of it.
  C5 `rbtp` survives a completed syscall (the entry saved it, the escape
     restored it).
  A  `lr`…`sc` with nothing in between succeeds (the control, so the next one
     cannot pass vacuously) and the same pair across a `trap` fails — an
     exception entry clears the hart's reservation (spec/SimRISC-12 §1,
     contract-syscall §11).  `sc`'s success/failure values are parsed from the
     spec, not written here.
  X  `execve` clears `rbtp` (§10): after `kernel_execve("/init.musl")` the frame
     has `rb3 = 0` and `ip` = the ELF's `e_entry`, read back from the file in
     the image rather than from the console.

Exit status: 0 = every case passed; 1 = at least one FAIL; 2 = an input could
not be derived (kernel source / build tree / toolchain / contract / spec
missing).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                          # noqa: E402  (pins)
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.linux.k5_syscall_probe import (                   # noqa: E402
    Report, config_enabled, config_value, elf_section, kernel_text, kv, md5,
    one, symbols, syscall_table_snapshot, table_slot, tool)
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("K5C_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-024") / "check-linux-k5-clone")
SOURCE = linux_paths.linux_source_dir()
CONTRACT_SYSCALL = _REPO / ".tao" / "contracts" / "contract-syscall.md"
SPEC_ATOMIC = _REPO / "spec" / "SimRISC-12-其它指令.md"
SPEC_ATOMIC_GLOB = "SimRISC-12*.md"
SCHED_H = "include/uapi/linux/sched.h"
SIGNAL_H = "include/uapi/asm-generic/signal.h"
TRAP_S = "arch/dadao/kernel/trap.S"
PROBE_C = "arch/dadao/kernel/k5_clone_selftest.c"
PROCESS_C = "arch/dadao/kernel/process.c"
FORK_C = "kernel/fork.c"
ARCH_KCONFIG = "arch/dadao/Kconfig"

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
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "y",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

TIMEOUT_BUILD = int(os.environ.get("K5C_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K5C_QEMU_TIMEOUT", "180"))
JOBS = os.environ.get("JOBS", "32")

#: The check names each case must report (`K5 check <name> ...`).
CASES = {
    "C1": ("c1_thread_mm_shared", "c1_thread_asid_same", "c1_thread_mm_users",
           "c1_fork_mm_private", "c1_fork_asid_differs",
           "c1_fork_parent_mm_users", "c1_mm_users_restored"),
    "C2": ("c2_child_rb3", "c2_parent_rb3", "c2_fork_child_rb3",
           "c2_parent_rb3_after_fork"),
    "C3": ("c3_child_rd8_zero", "c3_child_rd8_still_zero",
           "c3_child_frame_copy", "c3_child_frame_copy_set",
           "c3_fork_child_frame_copy", "c3_parent_tid",
           "c3_parent_tid_nonzero", "c3_fork_child_rd8_zero",
           "c3_fork_parent_tid", "clone_thread_gone"),
    "C4": ("c4_tgid_shared", "c4_group_leader", "c4_fs_shared",
           "c4_files_shared", "c4_sighand_shared", "c4_child_getpid",
           "c4_fork_tgid_own", "c4_fork_tgid_differs", "c4_fork_fs_private",
           "c4_fork_files_private"),
    "C5": ("c5_child_frame_rb3", "c5_child_rb3_after_syscall"),
    "A": ("atom_sc_immediate", "atom_sc_after_syscall"),
    "X": ("exec_ok", "exec_entry_ip", "exec_rbtp_zero"),
}

#: The syscalls the user program issues, by the name the locked table uses, and
#: how many times each must appear in the trap trace.
STUB_SYSCALLS = {"clone": 2, "getpid": 2, "exit": 2}


# ---------------------------------------------------------------------------
# derivations (never a literal: the owner of each fact is parsed)
# ---------------------------------------------------------------------------

def clone_bits() -> dict[str, int]:
    """`include/uapi/linux/sched.h`: the CLONE_* bit values, as macros."""
    text = kernel_text(SCHED_H)
    bits = {}
    for name, value in re.findall(r"^#define\s+(CLONE_\w+)\s+(0x[0-9a-fA-F]+)",
                                  text, re.M):
        bits[name] = int(value, 16)
    need = ("CLONE_VM", "CLONE_FS", "CLONE_FILES", "CLONE_SIGHAND",
            "CLONE_THREAD", "CLONE_SETTLS")
    missing = [n for n in need if n not in bits]
    if missing:
        raise SystemExit(f"k5_clone_probe: {SCHED_H} lacks {missing}")
    return bits


def sigchld() -> int:
    """`include/uapi/asm-generic/signal.h`: the SIGCHLD number."""
    m = re.search(r"^#define\s+SIGCHLD\s+(\d+)", kernel_text(SIGNAL_H), re.M)
    if not m:
        raise SystemExit(f"k5_clone_probe: {SIGNAL_H} has no SIGCHLD")
    return int(m.group(1))


def stub_constant(name: str) -> int:
    """A `#define <name> <integer>` of the user stub in `kernel/trap.S`."""
    text = kernel_text(TRAP_S)
    m = re.search(r"^#define\s+" + re.escape(name) + r"\s+(\S+)", text, re.M)
    if not m:
        raise SystemExit(f"k5_clone_probe: {TRAP_S} has no {name}")
    return int(re.sub(r"[ULul]+$", "", m.group(1)), 0)


def probe_constant(name: str) -> int:
    """A `#define <name> <integer>` of the kernel half (`k5_clone_selftest.c`)."""
    text = kernel_text(PROBE_C)
    m = re.search(r"^#define\s+" + re.escape(name) + r"\s+(\S+)", text, re.M)
    if not m:
        raise SystemExit(f"k5_clone_probe: {PROBE_C} has no {name}")
    return int(re.sub(r"[ULul]+$", "", m.group(1)), 0)


def sc_codes() -> tuple[int, int]:
    """`spec/SimRISC-12 §1`: `sc`'s destination on success and on failure.

    The two sentences are the instruction's own definition ("把 rdHB 寄存器设置成
    0，表示写入成功" / "设置成 1， 表示写入失败"); the gate judges the console
    against these numbers instead of assuming the usual 0/1 order.
    """
    path = SPEC_ATOMIC if SPEC_ATOMIC.is_file() else next(
        (p for p in _REPO.glob(f"spec/{SPEC_ATOMIC_GLOB}")), None)
    if path is None:
        raise SystemExit("k5_clone_probe: spec/SimRISC-12 (原子指令) missing")
    text = path.read_text(encoding="utf-8")
    ok = re.search(r"设置成\s*(\d+)\s*，\s*表示写入成功", text)
    bad = re.search(r"设置成\s*(\d+)\s*，\s*表示写入失败", text)
    if not ok or not bad:
        raise SystemExit("k5_clone_probe: spec/SimRISC-12 §1 has no sc "
                         "success/failure sentence")
    return int(ok.group(1)), int(bad.group(1))


def musl_argmask_row(name: str) -> int | None:
    """`components/musl/patches/arch/dadao/syscall_arch.h.patch`: the row.

    The kernel's own argmask table is a copy of this fact (and
    `tools/qemu/check_syscall_abi.py` compares all five carriers); reading it
    here states which argument slots the *user* side puts addresses in.
    """
    patch = (_REPO / "components" / "musl" / "patches" / "arch" / "dadao" /
             "syscall_arch.h.patch")
    if not patch.is_file():
        return None
    text = "\n".join(line[1:] for line in
                     patch.read_text(encoding="utf-8").splitlines()
                     if line.startswith("+") and not line.startswith("+++"))
    section = text[text.index("__dadao_argmask(long nr)"):]
    section = section[:section.index("\n}\n")]
    pending: list[str] = []
    for line in section.splitlines():
        pending += re.findall(r"case SYS_(\w+):", line)
        m = re.search(r"return (0x[0-9a-fA-F]+);", line)
        if m:
            if name in pending:
                return int(m.group(1), 16)
            pending = []
    return None


def kernel_argmask_rows() -> dict[int, int]:
    text = kernel_text("arch/dadao/kernel/syscall_argmask.c")
    return {int(nr): int(mask, 16) for nr, mask in
            re.findall(r"^\s*\[\s*(\d+)\]\s*=\s*(0x[0-9a-fA-F]+)\s*,", text,
                       re.M)}


def elf_entry(archive: Path, name: str) -> int:
    """ELF64 big-endian `e_entry` (offset 24) of an initramfs member, or ~0.

    The archive is read with the *writer's own* parser
    (`tools.linux.make_initramfs.parse_newc`), so the number is the bytes the
    image really carries — not a path lookup into the build tree.
    """
    from tools.linux.make_initramfs import parse_newc
    try:
        entries = parse_newc(archive.read_bytes())
    except (OSError, Exception):        # noqa: BLE001 - any parse error is "no ELF"
        return ~0
    for entry in entries:
        if entry["name"].split("/")[-1] == name:
            body = entry["body"]
            if len(body) < 32:
                return ~0
            return struct.unpack(">Q", body[24:32])[0]
    return ~0


# ---------------------------------------------------------------------------
# console parsing
# ---------------------------------------------------------------------------

_CHECK_RE = re.compile(r"^K5 check (\S+) want=(\S+) got=(\S+) (.*?)(ok|FAIL)$")
_TRAP_RE = re.compile(r"^K5 clone trap (\d+): pid=(\d+) nr=(\S+) immu18=(\S+) "
                      r"ip=(\S+) rd8=(\S+) rb3=(\S+)$")


def check_lines(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for line in text.splitlines():
        m = _CHECK_RE.match(line.strip())
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(5)}))
    return out


def trap_lines(text: str) -> list[dict[str, str]]:
    out = []
    for line in text.splitlines():
        m = _TRAP_RE.match(line.strip())
        if m:
            out.append({"index": m.group(1), "pid": m.group(2),
                        "nr": m.group(3), "immu18": m.group(4),
                        "ip": m.group(5), "rd8": m.group(6),
                        "rb3": m.group(7)})
    return out


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def build_image(label: str = "k5c") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k5_clone_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k5_clone_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k5c.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k5_clone_probe: {kernel} missing")
    qemu = tool("qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k5_clone_probe: qemu-system-dadao missing "
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
    bits = clone_bits()
    table = syscall_table_snapshot()
    sc_ok, sc_bad = sc_codes()
    tls = stub_constant("K5C_TLS")
    sentinel = probe_constant("K5C_RB3_SENTINEL")
    thread_flags = (bits["CLONE_VM"] | bits["CLONE_FS"] | bits["CLONE_FILES"] |
                    bits["CLONE_SIGHAND"] | bits["CLONE_THREAD"] |
                    bits["CLONE_SETTLS"])

    rep.check(f"B{s}", "镜像跑到 K5 clone 自检", True,
              "K5 clone selftest: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5 clone FAIL")])
    rep.check(f"B{s}", "末行是自检完成", True,
              "K5 clone selftest: done" in text)

    rows = check_lines(text)
    bad = [name for name, row in rows if row["verdict"] != "ok"]
    rep.check(f"B{s}", "内核自评的每条 K5 check 都 ok", [], bad)

    seen = [name for name, _ in rows]
    for case, names in CASES.items():
        missing = [n for n in names if n not in seen]
        rep.check(f"{case}{s}", f"{case} 的断言都报了（{len(names)} 条）", [],
                  missing)

    # --- the trap trace: which syscalls the program really issued ------------
    traps = trap_lines(text)
    sys_traps = [row for row in traps if row["immu18"] == "0x0"]
    rep.check(f"C3{s}", "syscall 型 trap 条数 == 程序发出的调用数",
              sum(STUB_SYSCALLS.values()), len(sys_traps))
    by_nr: dict[str, int] = {}
    for row in sys_traps:
        by_nr[row["nr"]] = by_nr.get(row["nr"], 0) + 1
    want_by_nr = {hex(table[name]): count
                  for name, count in STUB_SYSCALLS.items()}
    rep.check(f"C3{s}", "trap 的 syscall 号与次数（clone/getpid/exit）",
              want_by_nr, {k: v for k, v in by_nr.items() if v})
    # The probe's own umon functions (parsed from the stub) are each claimed
    # once: that is what makes the wait/report hand-overs appear at all.
    claimed = {name: stub_constant(name) for name in
               ("K5C_TRAP_WAIT_THREAD", "K5C_TRAP_CHILD_REPORT",
                "K5C_TRAP_WAIT_FORK", "K5C_TRAP_FORKCHILD_REPORT",
                "K5C_TRAP_DONE")}
    seen_immu = [row["immu18"] for row in traps if row["immu18"] != "0x0"]
    rep.check(f"C1{s}", "探针自己的 umon 号各被调用一次",
              {hex(v): 1 for v in claimed.values()},
              {hex(v): seen_immu.count(hex(v)) for v in claimed.values()})
    head = one(text, "K5 clone selftest: stub=")
    code = int((head or {}).get("code", "0"), 16)
    offs = [int(row["ip"], 16) - code for row in traps]
    rep.check(f"C3{s}", "每条 trap 的 ip 落在用户代码页内（0..PAGE_SIZE）",
              [], [o for o in offs if not 0 <= o < 0x10000])
    rep.check(f"C3{s}", "trap 序号连续且从 1 开始", [],
              [row["index"] for i, row in enumerate(traps, 1)
               if row["index"] != str(i)])

    # --- the probe's own value lines ----------------------------------------
    pre = one(text, "K5 clone pre:")
    rep.check(f"C1{s}", "thread clone 前记录了现场", True, pre is not None)
    if pre:
        rep.check(f"C2{s}", "clone flags == CLONE_VM|FS|FILES|SIGHAND|THREAD|"
                  "SETTLS（值来自 sched.h）", hex(thread_flags), pre.get("flags"))
        rep.check(f"C2{s}", "clone 的 tls 参数 == stub 里的 K5C_TLS", hex(tls),
                  pre.get("tls"))
        rep.check(f"C2{s}", "clone 的 newsp 是非零的页对齐地址（子栈）", True,
                  int(pre.get("stack", "0"), 16) != 0 and
                  int(pre.get("stack", "0"), 16) % 0x10000 == 0)
        rep.check(f"C2{s}", "父线程 trap 时 rb3 == 哨兵", hex(sentinel),
                  pre.get("rb3"))
        # §11's copy half needs a non-zero sentinel: an all-zero frame would
        # satisfy "the child's rd12 equals the parent's" without proving any
        # copy happened.
        want_copy = stub_constant("K5C_FRAME_SENTINEL")
        rep.check(f"C3{s}", "clone 前的帧拷贝哨兵 == stub 的常量且非零",
                  hex(want_copy), pre.get("copy"))

    fork_pre = one(text, "K5 clone fork pre:")
    rep.check(f"C1{s}", "fork 前记录了现场", True, fork_pre is not None)
    if fork_pre:
        rep.check(f"C4{s}", "fork flags == SIGCHLD（进程，不是线程）",
                  hex(sigchld()), fork_pre.get("flags"))
        rep.check(f"C1{s}", "fork 的 newsp == 0（沿用父栈）", "0x0",
                  fork_pre.get("stack"))

    child = one(text, "K5 clone child:")
    rep.check(f"C1{s}", "thread 子线程的现场行存在", True, child is not None)
    if child:
        rep.check(f"C1{s}", "子 mm == 父 mm", child.get("parent_mm"),
                  child.get("mm"))
        rep.check(f"C1{s}", "子 asid == 父 asid", child.get("parent_asid"),
                  child.get("asid"))
        pre_users = int(pre.get("mm_users", "-1")) if pre else -2
        rep.check(f"C1{s}", "子存活时 mm_users == 父 + 1", pre_users + 1,
                  int(child.get("mm_users", "-9")))
        rep.check(f"C3{s}", "子入口 rd8 == 0", "0x0", child.get("rd8_at_entry"))
        rep.check(f"C2{s}", "子 rb3 == tls 参数", hex(tls), child.get("rb3"))
        rep.check(f"C3{s}", "子帧的拷贝哨兵 == 父帧（§11 现场副本）",
                  pre.get("copy") if pre else None, child.get("copy"))

    forkc = one(text, "K5 clone fork child:")
    rep.check(f"C1{s}", "fork 子进程的现场行存在", True, forkc is not None)
    if forkc:
        rep.check(f"C1{s}", "fork 子的 mm != 父 mm", True,
                  forkc.get("mm") != forkc.get("parent_mm"))
        rep.check(f"C1{s}", "fork 子的 asid != 父 asid", True,
                  forkc.get("asid") != forkc.get("parent_asid"))
        rep.check(f"C1{s}", "fork 不动父 mm_users", "1",
                  forkc.get("parent_mm_users"))
        rep.check(f"C3{s}", "fork 子入口 rd8 == 0", "0x0",
                  forkc.get("rd8_at_entry"))
        rep.check(f"C2{s}", "fork 子继承父的 rb3（无 SETTLS）", hex(sentinel),
                  forkc.get("rb3"))
        rep.check(f"C4{s}", "fork 子的 tgid == 它自己的 pid", forkc.get("pid"),
                  forkc.get("tgid"))

    done = one(text, "K5 clone done:")
    rep.check(f"C3{s}", "父侧结论行存在", True, done is not None)
    if done:
        rep.check(f"C3{s}", "父 clone 返回值非零（子 tid）", True,
                  int(done.get("thread_ret", "0"), 16) != 0)
        rep.check(f"C3{s}", "两个 clone 返回不同的 tid", True,
                  done.get("thread_ret") != done.get("fork_ret"))
        rep.check(f"C2{s}", "父 rb3 在两个 clone 后仍是哨兵", hex(sentinel),
                  done.get("parent_rb3"))
        pre_users = int(pre.get("mm_users", "-1")) if pre else -2
        rep.check(f"C1{s}", "全部子退出后 mm_users 回到原值", pre_users,
                  int(done.get("mm_users", "-9")))
        rep.check(f"A{s}", "lr;sc 无异常介入 ⇒ sc 成功（spec 的值）", hex(sc_ok),
                  done.get("sc_now"))
        rep.check(f"A{s}", "lr;trap;sc ⇒ sc 失败（spec 的值）", hex(sc_bad),
                  done.get("sc_across"))

    ex = one(text, "K5 clone exec:")
    rep.check(f"X{s}", "execve 行存在", True, ex is not None)
    if ex:
        rep.check(f"X{s}", "kernel_execve 成功", "0", ex.get("rc"))
        rep.check(f"X{s}", "execve 后帧 rb3 == 0", "0x0", ex.get("rb3"))
        want = elf_entry(build_dir() / "initramfs" / "initramfs.cpio",
                         "init.musl")
        rep.check(f"X{s}", "镜像里能读出 /init.musl 的 e_entry", True,
                  want != ~0 and want != 0)
        if want != ~0 and want != 0:
            rep.check(f"X{s}", "帧 ip == 该 e_entry", hex(want), ex.get("ip"))

    rep.check(f"D{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)


def static_recon(rep: Report, snap: dict | None) -> None:
    """The pieces a boot cannot show: the image's configuration and the wiring."""
    rep.check("S0", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]
    table = syscall_table_snapshot()
    for symbol, value in {"CONFIG_DADAO_K5_CLONE_SELFTEST": "y",
                          "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
                          "CONFIG_DADAO_K4_SELFTEST": "n",
                          "CONFIG_CLONE_BACKWARDS": "y",
                          "CONFIG_ARCH_HAS_SYSCALL_WRAPPER": "y",
                          "CONFIG_PAGE_SIZE_64KB": "y"}.items():
        if value == "n":
            rep.check("B", f"镜像配置：{symbol} 关", False,
                      config_enabled(config, symbol))
        else:
            rep.check("B", f"镜像配置：{symbol}={value}", value,
                      config_value(config, symbol))

    # The table really carries `clone` (all slots left at sys_ni_syscall would
    # answer -ENOSYS and look like "clone is not implemented").
    elf = kernel_path()
    syms = symbols(elf)
    rep.check("C3", "sys_call_table[clone] == sys_clone", syms.get("sys_clone"),
              table_slot(elf, "sys_call_table", table["clone"]))

    # The ABI order: tls is the 4th argument, which is what CLONE_BACKWARDS
    # selects (`arch/Kconfig`: "tls passed as the 4th argument of clone(2)").
    arch_kconfig = kernel_text(ARCH_KCONFIG)
    rep.check("C2", "arch 选择 CONFIG_CLONE_BACKWARDS（tls 是第 4 个参数）", True,
              "select CLONE_BACKWARDS" in arch_kconfig)
    musl = musl_argmask_row("clone")
    rows = kernel_argmask_rows()
    rep.check("C2", "clone 的 argmask == musl 的（地址参数在槽 2/4）", musl,
              rows.get(table["clone"]))
    # The remaining clone arguments must stay in the data bank (flags, newsp,
    # tls), which is what "address arguments are exactly slots 2 and 4" means.
    rep.check("C2", "clone 的地址参数恰为 ptid/ctid（mask 0x14）", 0x14,
              rows.get(table["clone"]))

    # copy_thread: the TLS branch and the inherited half.
    process = kernel_text(PROCESS_C)
    start = process.index("fork()/clone(): the child returns")
    end = process.index("t->sp = (unsigned long)childregs;")
    while process.find("t->sp = (unsigned long)childregs;", end + 1) != -1:
        end = process.find("t->sp = (unsigned long)childregs;", end + 1)
    block = process[start:end]
    rep.check("C2", "copy_thread 的 fork 分支按 CLONE_SETTLS 取 args->tls",
              True, "args->flags & CLONE_SETTLS" in block and
              "args->tls" in block)
    rep.check("C2", "无 SETTLS 时子 rb3 继承父帧", True,
              "regs->rb[3]" in block)
    rep.check("C3", "fork 分支子 rd8 = 0", True, "childregs->rd[8] = 0;" in block)
    rep.check("C3", "用户子任务从 trap 的下一条进入（ret_from_fork）", True,
              "regs->ip += DADAO_INSN_BYTES;" in process)

    # The umon return path restores *its own* cg5 field before escaping: a task
    # that slept in the handler must not resume at another task's trap.
    trap = kernel_text(TRAP_S)
    rep.check("C5", "umon 返回前把本任务 cg5.excp_cause_ip 写回（两份）", 2,
              trap.count("cfx2rc\tcfx_umon, cg5, rc3, rd4"))
    rep.check("C5", "入口栈顶取自已停放变量（不再读被抓取清掉的 cg6）", True,
              "dadao_user_stack_top" in trap and
              "cfx2rd\tcfx_umon, cg6, rc1, rd3" not in trap)
    rep.check("C5", "__switch_to 在切换前停放栈顶", True,
              "dadao_user_stack_top =" in process)

    # The stub is what the user side sends: CLONE_* values must be the ones the
    # locked uapi header defines (a typo here would still pass a self-check).
    bits = clone_bits()
    flags = stub_constant("K5C_CLONE_FLAGS")
    want = (bits["CLONE_VM"] | bits["CLONE_FS"] | bits["CLONE_FILES"] |
            bits["CLONE_SIGHAND"] | bits["CLONE_THREAD"] | bits["CLONE_SETTLS"])
    rep.check("C2", "stub 的 CLONE_* 组合 == sched.h 的位或", hex(want),
              hex(flags))

    # execve's half of §10 lives in start_thread() (setup.c).
    setup = kernel_text("arch/dadao/kernel/setup.c")
    sec = setup[setup.index("void start_thread("):]
    sec = sec[:sec.index("\n}")]
    rep.check("X", "start_thread 清 rbtp（execve 侧）", True, "rb[3] = 0" in sec)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> (file, needle, replacement, case that must go red, why)
INJECTIONS = {
    "clone-vm-dup": (
        FORK_C,
        "\tif (clone_flags & CLONE_VM) {\n\t\tmmget(oldmm);\n",
        "\tif (0 && (clone_flags & CLONE_VM)) {\n\t\tmmget(oldmm);\n",
        "C1", "CLONE_VM 不再共享 mm（走 dup_mm）⇒ 子 mm/asid 与父不同，C1 红"),
    "clone-set-tls": (
        PROCESS_C,
        "\tif (args->flags & CLONE_SETTLS)\n\t\tchildregs->rb[3] = args->tls;\n"
        "\telse\n",
        "\tif (0)\n\t\tchildregs->rb[3] = args->tls;\n\telse\n",
        "C2", "CLONE_SETTLS 不设子 rb3 ⇒ 子继承哨兵，C2 红"),
    "child-rd8": (
        PROCESS_C,
        "\tchildregs->rd[8] = 0;\n\tchildregs->ip = regs->ip;\n",
        "\tchildregs->rd[8] = 0xdead;\n\tchildregs->ip = regs->ip;\n",
        "C3", "子入口 rd8 不为 0 ⇒ 子走父分支，C3 红"),
    "clone-thread-group": (
        FORK_C,
        "\tif (clone_flags & CLONE_THREAD)\n\t\treturn 0;\n\n\tsig = "
        "kmem_cache_zalloc(signal_cachep, GFP_KERNEL);",
        "\tif (0)\n\t\treturn 0;\n\n\tsig = kmem_cache_zalloc(signal_cachep, "
        "GFP_KERNEL);",
        "C4", "CLONE_THREAD 不共享 signal ⇒ 子 tgid 独立，C4 红"),
    "clone-backwards": (
        ARCH_KCONFIG,
        "\tselect CLONE_BACKWARDS\n",
        "",
        "C2", "不选 CONFIG_CLONE_BACKWARDS ⇒ tls 从第 5 个参数取（0），C2 红"),
}


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
        died = any(tok in out for tok in ("dadao: die mode=",
                                          "K5 clone FAIL",
                                          "Kernel panic"))
        rep.info(f"inject {name}: rc={rc} red={red[:5]} died={died}")
        rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True,
                  bool([n for n in red if n.startswith(case.lower() + "_")]) or
                  died)
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        rc, snap = build_image("restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if snap is not None:
            rc2, out2 = boot(f"restored-{name}", rom)
            rows2 = check_lines(out2)
            rep.check(f"INJECT {name}", "还原后回绿（无红项）", [],
                      [n for n, row in rows2 if row["verdict"] != "ok"])
            rep.check(f"INJECT {name}", "还原后宿主 rc=0", 0, rc2)


def selfcheck() -> int:
    """Prove the judging can fail: feed it a console that must be red."""
    rep = Report()
    text = (
        "K5 clone selftest: begin pid=1 mm=0\n"
        "K5 clone trap 1: pid=16 nr=0xac immu18=0x0 ip=0x10000400000 rd8=0x0 "
        "rb3=0x1\n"
        "K5 clone pre: pid=16 flags=0x100 stack=0x0 tls=0x0 rb3=0x0 "
        "mm=0x1 asid=1 mm_users=1\n"
        "K5 clone child: pid=17 tgid=17 mm=0x2 parent_mm=0x1 asid=2 "
        "parent_asid=1 mm_users=1 rd8_at_entry=0xdead rb3=0x0 tls_arg=0x0\n"
        "K5 check c1_thread_mm_shared want=0x1 got=0x0 FAIL\n"
        "K5 check c2_child_rb3 want=0x1 got=0x0 FAIL\n"
        "K5 clone exec: rc=-2 entry=0x0 ip=0x4 rb3=0x99\n"
        "K5 clone selftest: FAIL mask=0x76\n"
    )
    judge(rep, text, 1)
    red = rep.failed
    print(f"[SELFCHECK] red checks: {len(red)}")
    for name in red[:10]:
        print(f"[SELFCHECK]   {name}")
    if not red:
        print("[SELFCHECK] FAIL: a broken console produced no red check")
        return 1
    print("[SELFCHECK] PASS: the judging goes red on a broken console")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="M14 K5 user clone probe")
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
        print("k5_clone_probe: no image; judging stops here", file=sys.stderr)
        return 1
    rom = firmware()
    rc, out = boot("k5c", rom)
    judge(rep, out, rc)

    if not args.no_inject:
        names = args.inject or sorted(INJECTIONS)
        for name in names:
            if name not in INJECTIONS:
                raise SystemExit(f"k5_clone_probe: unknown injection {name!r}")
            run_injection(rep, name, rom)

    print()
    if rep.failed:
        print(f"k5_clone_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"k5_clone_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
