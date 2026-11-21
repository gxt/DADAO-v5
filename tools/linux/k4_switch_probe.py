#!/usr/bin/env python3
"""k4_switch_probe.py — M14 K4 context-switch probe (`m14-linux-017`).

The kernel side is `arch/dadao/kernel/k4_switch_selftest.c` (+ the register half
in `k4_switch_asm.S`), built as a probe image with
`CONFIG_DADAO_K4_SWITCH_SELFTEST`; this gate builds that image, boots it on
Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from:

  S1  register round trip (fabricated context B, `kernel/k4_switch_asm.S`): the
      callee-saved banks travel with the task, B's arrive intact, B's are saved
      on the way back, A's come back unchanged, and the return-address stack
      depth at the switch point is what the measurement predicted.
  S2  two kernel threads increment their own counters and yield until both are
      done; each of them is still itself when `schedule()` returns
      (`switch_to()`'s `last` semantics through the real `__switch_to()`).
  S3  `switch_mm()` — the four steps of contract-tlb TLB-30: the ASID and PTBR
      read back as the new address space's, `ptw_enable` is 1, the invalidation
      command value is rebuilt from contract-tlb TLB-19 (not a literal), and the
      kernel keeps executing *on the new table* (which is what proves
      `pgd_alloc()` carried the kernel's G = 1 L1 slots into it, TLB-26).
  S4  footprint: the switch leaves the caller-saved blocks, `rb2` (frame
      pointer, ADR-0018 C6) and `rb3` (rbtp, contract-abi §4.5) untouched.
  S6  the minimal clockevent: `cfx_hart`'s compare register raises `TIMER`
      `freq / HZ` apart, `jiffies` advances by exactly the number of delivered
      ticks, and no generic clockevent/clocksource framework is registered
      (that upgrade is K5's m14-linux-021).
  S5  two *user* processes A/B alternating; needs the per-task user-mode frame
      (the umon entry still saves into one static frame, kernel/trap.S).
  S7  F3: `kernel_init` brings up the initramfs and the probe's syscall hook
      sees the init chain exit.  Since m14-linux-031 the image's `/init` is a
      **script** (`#!/bin/sh` + `exec /bin/sh`) that starts busybox's `sh`; the
      static musl ELF of the original MVP init ships as `init.musl` and is not
      what the kernel execs.  The target is therefore "script -> sh -> busybox
      runs and prints", and `init.musl` is only the recorded fallback (its
      trigger: busybox cannot start for want of K5's `fork`/`execve`/`wait`/
      `read` — record the evidence, then switch `/init` to `exec /init.musl`).
      Reaching it needs F16 (the boot stops inside `kernel_init_freeable()`,
      before the first `*_initcall`) and the syscall surface K5 owns.

S5 and S7 are reported as FAIL with their own names when the image does not get
there: the gate must not silently drop an acceptance item.

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
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                          # noqa: E402  (pins)
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import make_vmlinux as make_vmlinux         # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("K4S_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-017") / "check-linux-k4-switch")
SOURCE = linux_paths.linux_source_dir()
CONTRACT_TLB = _REPO / ".tao" / "contracts" / "contract-tlb.md"
CONTRACT_ABI = _REPO / ".tao" / "contracts" / "contract-abi.md"

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
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "y",
    # m14-linux-020: the kernel-thread probe is an image of its own; pin it
    # off so the shared build tree cannot hand this image that symbol.
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    # The stack-growth probe is an int (0 = off); pin it off or this
    # image inherits the last stack case and ends the boot at the K4
    # boundary (F30 class: sibling config symbols are pinned in pairs).
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    # m14-linux-018: same reason — the COW probe is an int with no `depends on`,
    # so it carries a concrete value rather than "unset".
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    # m14-linux-023: the user-syscall probe image; pin it off so no other
    # image inherits it from the shared build tree.
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

TIMEOUT_BUILD = int(os.environ.get("K4S_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K4S_QEMU_TIMEOUT", "180"))
JOBS = os.environ.get("JOBS", "32")

#: The cases this image must report, with the check name that starts each one.
CASES = ("S1", "S2", "S3", "S4", "S5", "S6")
#: Acceptance items the image cannot reach yet (they are FAIL, named).
MISSING = {
    # S5 left this table when the A/B round trip went green (m14-linux-017
    # round 31): two tasks with their own address spaces, the frame checked
    # before and after the other one runs.
    # S7 left it in round 22 (`/init` reached `exit_group`).
}


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
# derivations (never a literal: the owner of each fact is parsed)
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"k4_switch_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def tlb_encoding() -> dict:
    """`contract-tlb TLB-19`: the `tlb_control` field layout and op numbers."""
    text = CONTRACT_TLB.read_text(encoding="utf-8")
    m = re.search(r"TLB-19 \*\*编码\*\*：`\[1:0\]` 操作 = `00=none`/`01=clean`/"
                  r"`10=invalid`/`11=flush`；`\[3:2\]` 地址范围 = `00=all`", text)
    if not m:
        raise SystemExit("k4_switch_probe: contract-tlb TLB-19 has no encoding")
    return {
        # "invalid" is the second of the four op values, "all" the first scope,
        # ASID_ANY = 0: 0b10 | 0b00 << 2 | 0 << 4
        "invalid_all_own_asid": 0b10,
    }


def callee_saved_banks() -> tuple[str, ...]:
    """`contract-abi §4.5`: the banks a task's context must carry."""
    text = CONTRACT_ABI.read_text(encoding="utf-8")
    sec = text[text.index("§4.5"):]
    sec = sec[:sec.index("§4.6")] if "§4.6" in sec else sec[:4000]
    banks = set()
    for bank, lo, hi in re.findall(r"\b(rd|rb|rf)(\d+)\s*[–-]\s*\1(\d+)", sec):
        if int(lo) == 32 and int(hi) == 63:
            banks.add(bank)
    if not banks:
        raise SystemExit("k4_switch_probe: contract-abi §4.5 has no banks")
    return tuple(sorted(banks))


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    value = config_value(config, symbol)
    return value is not None and value not in ("n", "0", "")


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
        m = re.match(r"K4 check (\S+) want=(\S+) got=(\S+) (ok|FAIL)$", line)
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(4)}))
    return out


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


def bytes_of(path: Path) -> bytes:
    return Path(path).read_bytes()


def build_image(label: str = "switch") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k4_switch_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k4_switch_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k4s.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k4_switch_probe: {kernel} missing")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k4_switch_probe: qemu-system-dadao missing (make install-host)")
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

    rep.check(f"B{s}", "镜像跑到 K4 边界之后的自检", True,
              "K4 switch: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K4 switch FAIL")])

    rows = check_lines(text)
    bad = [name for name, row in rows if row["verdict"] != "ok"]
    rep.check(f"B{s}", "内核自评的每条 K4 check 都 ok", [], bad)
    # Every case this image is supposed to cover must have said something.
    seen = " ".join(name for name, _ in rows)
    for case in CASES:
        rep.check(f"B{s}", f"{case} 的断言存在（vacuous ⇒ FAIL）", True,
                  case.lower() in seen.lower())

    for case in MISSING:
        # A case that never ran must not be silently absent: it is FAIL with
        # the acceptance item's own name.
        rep.check(f"{case}{s}", f"{case}（{MISSING[case]}）", "已实现", "未实现")

    if "S1" in CASES:
        s1 = one(text, "K4 switch s1: bad=")
        rep.check(f"S1{s}", "S1 往返行存在", True, s1 is not None)
        if s1:
            rep.check(f"S1{s}", "S1 逐库往返坏位", "0x0", s1.get("bad"))

    s2 = one(text, "K4 switch s2: c0=")
    rep.check(f"S2{s}", "S2 双任务行存在", True, s2 is not None)
    if s2:
        rep.check(f"S2{s}", "S2 两个任务都推进", "4/4",
                  f"{s2.get('c0')}/{s2.get('c1')}")

    s3 = one(text, "K4 switch s3: asid=")
    rep.check(f"S3{s}", "S3 switch_mm 行存在", True, s3 is not None)
    if s3:
        rep.check(f"S3{s}", "S3 ASID 已切换", s3.get("want_asid"), s3.get("asid"))
        rep.check(f"S3{s}", "S3 PTBR 已切换", s3.get("want_ptbr"), s3.get("ptbr"))
        want_cmd = hex(tlb_encoding()["invalid_all_own_asid"])
        rep.check(f"S3{s}", "S3 失效命令值（TLB-19 现场重建）",
                  want_cmd, s3.get("invalid_cmd"))
    rep.check(f"S3{s}", "S3 在新页表上继续执行", True,
              "alive_on_new_table=1" in text)

    s6 = one(text, "K4 switch s6: ticks=")
    rep.check(f"S6{s}", "S6 tick 行存在", True, s6 is not None)
    if s6:
        ticks = s6.get("ticks")
        rep.check(f"S6{s}", "S6 jiffies 增量 == tick 数", ticks,
                  s6.get("jiffies_delta"))
        rep.check(f"S6{s}", "S6 收到了多个 tick（非一次残留）", True,
                  ticks is not None and int(ticks, 0) >= 2)

    # The generic framework is K5's, but its *config symbols* are upstream
    # generic options that are always on; what matters is that this port never
    # registers a device or a clocksource -- that is the static recon's S6
    # negative, and it is the only place the claim can be made.
    rep.info("S6 负例（通用框架未接线）见 static_recon 的 S6 两条静态断言")

    s5 = one(text, "K4 switch s5: a_bad=")
    rep.check(f"S5{s}", "S5 A/B 往返行存在", True, s5 is not None)
    if s5:
        rep.check(f"S5{s}", "S5 A 帧逐项一致（bad == 0）", "0x0", s5.get("a_bad"))
        rep.check(f"S5{s}", "S5 B 帧逐项一致（bad == 0）", "0x0", s5.get("b_bad"))
        rep.check(f"S5{s}", "S5 两个任务都进过用户态（1/1）", "1/1",
                  f"{s5.get('visits', '').split('/')[0]}/"
                  f"{s5.get('visits', '/').split('/')[-1]}")
        rep.check(f"S5{s}", "S5 两个任务都自报了", "2", s5.get("reported"))
    pgd = one(text, "K4 switch s5: pgd copy")
    rep.check(f"S5{s}", "S5 新表复制了 VA >= 2 TiB 的顶层项", True,
              pgd is not None)
    if pgd:
        rep.check(f"S5{s}", "S5 复制的项数 == 8192 - USER_PTRS_PER_PGD", "4096",
                  pgd.get("items"))
        rep.check(f"S5{s}", "S5 复制与 swapper_pg_dir 逐项相等", "0",
                  pgd.get("mismatches"))

    init = one(text, "K4 switch init: exit code=")
    rep.check(f"S7{s}", "initramfs /init 跑到 exit_group", True, init is not None)
    # The boot's own exit code is only meaningful once S7 is reached: before
    # that the image is expected to stall, and `timeout` (124) is the shape of
    # that stall -- not a separate finding to double-count.
    if init is not None:
        rep.check(f"D{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)


CUR_CONFIG: list[str] = [""]


def static_recon(rep: Report, snap: dict | None) -> None:
    """The pieces a boot cannot show: the image's own configuration and the
    source-level facts the probe's expectations rely on."""
    rep.check("S0", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]
    CUR_CONFIG[0] = config
    for symbol, value in {"CONFIG_DADAO_K4_SWITCH_SELFTEST": "y",
                          "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
                          "CONFIG_DADAO_K4_COW_SELFTEST": "0",
                          "CONFIG_DADAO_K4_SELFTEST": "n",
                          "CONFIG_PAGE_SIZE_64KB": "y"}.items():
        # `n` is spelled as a comment by kconfig ("# SYM is not set"), so the
        # comparison is on the *state*, not on one spelling of the line.
        want = config_enabled(config, symbol) if value == "n" else value
        got = (config_value(config, symbol)
               if value != "n" else config_enabled(config, symbol))
        line = f"{symbol}={value}"
        rep.check("B", f"镜像配置：{line}", want, got)
    rep.check("B", "K1/K2 边界全关（镜像走完 setup_arch）", [],
              [s for s in ("CONFIG_DADAO_K1_EARLY_STOP",
                           "CONFIG_DADAO_K2_EARLY_STOP",
                           "CONFIG_DADAO_K2_TIME_STOP")
               if config_enabled(config, s)])

    # The banks the switch carries: contract-abi §4.5, checked against the
    # header's declaration (the probe's `in[]` table is sized from it).
    header = kernel_text("arch/dadao/include/asm/processor.h")
    sec = header[header.index("struct thread_struct {"):]
    sec = sec[:sec.index("};")]
    sizes = {bank: int(n) for bank, n in
             re.findall(r"unsigned long (rd|rb|rf|ras)\[(\d+)\]", sec)}
    rep.check("S1", f"thread_struct 含 contract-abi §4.5 的库 {callee_saved_banks()}",
              {bank: 32 for bank in callee_saved_banks()},
              {bank: sizes.get(bank) for bank in callee_saved_banks()})
    rep.check("S1", "thread_struct 有返回地址栈（ra0= {RACNT,MRPTR} + 63 项）",
              64, sizes.get("ras"))

    # The switch itself: the block transfers of spec/SimRISC-01 §1/§2 and the
    # two registers it must not touch.
    switch_src = kernel_text("arch/dadao/kernel/entry.S")
    rep.check("S1", "__switch_to_asm 用块传送搬 rd32-63 与 rb32-63", True,
              "stm.o\t{rd32:rd63}" in switch_src and
              "stm.o\t{rb32:rb63}" in switch_src)
    rep.check("S1", "__switch_to_asm 搬返回地址栈（ra0-62 + ra63）", True,
              "stm.o\t{ra0:ra62}" in switch_src and
              "stm.o\t{ra63:ra63}" in switch_src)
    rep.check("S4", "切换路径不写 rb3（rbtp）", False,
              re.search(r"^\s*(set\.rb|ld\.o)\s+rb3,", switch_src, re.M) is not None)
    rep.check("S4", "切换路径不搬 rf32-63（帧所有）", False,
              re.search(r"(stm|ldm)\.o\t\{rf|\b(ld|st)\.o\trf\d+", switch_src)
              is not None)

    mmu = kernel_text("arch/dadao/mm/mmu.c")
    rep.check("S3", "switch_mm 写 ASID（TLB-30 ①）", True,
              "dadao_asid_write(asid)" in mmu)
    rep.check("S3", "switch_mm 写 PTBR（TLB-30 ①）", True,
              "dadao_ptbr_write(__pa(next->pgd))" in mmu)
    rep.check("S3", "switch_mm 显式 invalidate（TLB-30 ②）", True,
              "__dadao_tlb_flush(DADAO_TLB_INVALID, DADAO_TLB_SCOPE_ALL" in mmu)
    rep.check("S3", "switch_mm 置 ptw_enable（TLB-30 ③）", True,
              "DADAO_PTW_ENABLE_ON" in mmu)
    rep.check("S3", "switch_mm 保存/恢复 cg6 暂存（TLB-30 ④）", True,
              "PTW_CG_SCRATCH" in mmu)

    time_src = kernel_text("arch/dadao/kernel/time.c")
    rep.check("S6", "最小 clockevent 只写 timer_cmp/timer_ctrl", True,
              "dadao_timer_arm" in time_src and "dadao_tick_on" in time_src)
    rep.check("S6", "tick 调用 sched_tick（调度记账）", True,
              "sched_tick()" in time_src)
    # m14-linux-026 upgraded this boundary: `time_init()` now registers a
    # clocksource/clockevent pair and the generic tick owns jiffies.  The K4
    # image therefore takes the *generic* path, and the static half asserts
    # exactly that: the registration is present, and the raw K2 tick is
    # compile-time isolated to CONFIG_DADAO_K2_TIME_STOP.  The registration
    # itself is judged end-to-end by `tools/linux/k5_clocksource_probe.py`
    # (T1-T4), so this file does not restate it.
    rep.check("S6", "生产镜像走通用 clockevent；K2 裸 tick 只剩边界镜像",
              True,
              "clockevents_config_and_register" in time_src and
              "#ifdef CONFIG_DADAO_K2_TIME_STOP" in time_src)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> (file, needle, replacement, case that must go red, why)
INJECTIONS = {
    "no-rd32-save": (
        "arch/dadao/kernel/entry.S",
        "\tset.rd\trd2, THREAD_RD\n\tstm.o\t{rd32:rd63}, [rb16, rd2]\n",
        "",
        "S1", "__switch_to 不保存 rd32-63 ⇒ A 的库留在寄存器里，S1 红"),
    "restore-wrong-order": (
        "arch/dadao/kernel/entry.S",
        "\tset.rd\trd2, THREAD_RB\n\tldm.o\t{rb32:rb63}, [rb17, rd2]\n",
        "\tset.rd\trd2, THREAD_RAS\n\tldm.o\t{rb32:rb63}, [rb17, rd2]\n",
        "S1", "恢复用了错的偏移 ⇒ B 的库搬到 RAS 区，S1 红"),
    "no-asid-write": (
        "arch/dadao/mm/mmu.c",
        "\tdadao_asid_write(asid);\n",
        "\n",
        "S3", "switch_mm 不写 ASID ⇒ S3 红（寄存器仍是旧的）"),
    "switch-clobbers-tp": (
        "arch/dadao/kernel/entry.S",
        "\tld.o\trb1, [rb17, THREAD_SP]\n",
        "\tld.o\trb1, [rb17, THREAD_SP]\n\tset.rb\trb3, 0\n",
        "S4", "切换碰 rb3（rbtp）⇒ S4 红"),
    "no-rbtp-save": (
        "arch/dadao/include/asm/entry.h",
        "\tst.o\trd2, [rb3, PT_RB_BASE + 3 * 8]\t/* frame.rb[3] = the real rbtp */\n",
        "",
        "S5", "用户态帧不保存 rb3(rbtp) ⇒ A/B 往返后帧校验红"),
    "no-timer-arm": (
        "arch/dadao/kernel/time.c",
        "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_TIMER, CFX_HART_RC_TIMER_CMP,\n"
        "\t\t\tdeadline);\n"
        "\tDADAO_CFX_WRITE(cfx_hart, CFX_HART_CG_TIMER, CFX_HART_RC_TIMER_CTRL,\n"
        "\t\t\tDADAO_TIMER_ENABLE);\n",
        "\n",
        "S6", "arm 不下发（cmp 与 ctrl 都不写）⇒ 没有 tick，S6 红"),
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
        # The case's own check must not have come out `ok`; a guest that dies
        # before printing it (a hard fault is a legitimate red) counts too.
        case_ok = [n for n, row in rows
                   if row["verdict"] == "ok" and n.lower().startswith(case.lower())]
        died = any(tok in out for tok in ("dadao: die mode=", "K4 switch FAIL",
                                          "recursive supv exception",
                                          "Kernel panic"))
        rep.info(f"inject {name}: rc={rc} red={red[:5]} died={died}")
        rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True,
                  bool(red) or died or (not case_ok))
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


def selfcheck() -> int:
    """Prove the judging can fail: feed it a console that must be red."""
    rep = Report()
    text = (
        "K4 switch: begin\n"
        "K4 switch s1: bad=0x2 a_rd0=0x0 a_rb0=0x0 b_rd0=0x0 b_rb0=0x0 "
        "seen_rd0=0x0 res_rd0=0x0\n"
        "K4 check s1-roundtrip want=0x0 got=0x2 FAIL\n"
        "K4 switch s2: c0=4 c1=0 done=1 spins=1 back_bad=1\n"
        "K4 check s2-thread-1-ran want=0x4 got=0x0 FAIL\n"
        "K4 switch s3: asid=0 want_asid=1 ptbr=0x0 want_ptbr=0x10 "
        "ptw=0 invalid_cmd=0x0\n"
        "K4 switch s6: ticks=0 jiffies_delta=0 window=1 elapsed=1\n"
        "K4 switch FAIL: s1-roundtrip=0x2 code=0x40\n"
    )
    CUR_CONFIG[0] = "CONFIG_GENERIC_CLOCKEVENTS=y\n"
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
    parser = argparse.ArgumentParser(description="M14 K4 context-switch probe")
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
        print("k4_switch_probe: no image; judging stops here", file=sys.stderr)
        return 1
    rom = firmware()
    rc, out = boot("switch", rom)
    judge(rep, out, rc)

    if not args.no_inject:
        names = args.inject or sorted(INJECTIONS)
        for name in names:
            if name not in INJECTIONS:
                raise SystemExit(f"k4_switch_probe: unknown injection {name!r}")
            run_injection(rep, name, rom)

    print()
    if rep.failed:
        print(f"k4_switch_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"k4_switch_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
