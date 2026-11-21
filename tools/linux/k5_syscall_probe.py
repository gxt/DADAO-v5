#!/usr/bin/env python3
"""k5_syscall_probe.py — M14 K5 user-syscall closure probe (`m14-linux-023`).

The kernel side is `arch/dadao/kernel/k5_syscall_selftest.c` (+ the user program
in `kernel/trap.S`, the dispatcher in `kernel/syscalls.c`), built as a probe
image with `CONFIG_DADAO_K5_SYSCALL_SELFTEST`; this gate builds that image, boots
it on Kaiwu-Vast and judges what the kernel reports.

What each case proves, and where its expectation comes from:

  U1  `write(fd, buf, n)` from user mode: the `trap cfx_umon, 0` reaches the
      umon entry, the number (`rd15`) indexes `sys_call_table`, the entry runs
      with the ABI's parameter registers, and the frame's `rd8` comes back with
      the byte count — the bytes themselves land in the ramfs file the probe
      opened, which the boot task reads back.  Numbers from the contract's
      locked snapshot (contract-syscall §1.2, sha256-verified below).
  U2  `exit(0)` ends the task through `do_exit`; the boot task observes
      `exit_code == 0` and the host process exits 0.
  U3  the error shape of contract-syscall §9: `rd8 = -errno` inside
      `[-4095, -1]` — `-ENOSYS` for an in-range slot with no implementation and
      for a number past the table, `-EINVAL` for a bad argument — and `rd1`
      (`rderrno`) never takes part.
  U4  TLS: `rb3` = `rbtp` (§10) is what the entry saved and the escape restored,
      at every trap and in the value the program reads back after a syscall.
  U5  the cg5 frame fields (§8): `excp_cause_id = CFXTRAP`,
      `excp_prev_run_mode = user`, `excp_cause_ip` at the trap instruction and
      `immu18 = excp_cause_info & 0x3FFFF`; the two SBI functions of
      spec/DADAO-22 §2 answer as documented.  **The trap list this gate checks
      against is derived from the built vmlinux's disassembly** of
      `dadao_k5_user_stub` (offset + immediate of every `trap`), not from the
      kernel's own table, so a wrong parse or a moved instruction shows up.
  U6  the internal restart codes (`ERESTARTSYS` and friends) cannot reach user
      mode (§9: 内核内部码不外泄).
  U7  the execve half of the TLS rule (§10, user ruling 2026-11-17): after
      `kernel_execve("/init.musl")` the frame the entry will load has
      `rb3 = 0`, and its `ip` equals the ELF header's `e_entry` read back from
      the file.

Exit status: 0 = every case passed; 1 = at least one FAIL; 2 = an input could
not be derived (kernel source / build tree / toolchain / contract missing).
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
from tools.linux import make_vmlinux as make_vmlinux         # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("K5_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-023") / "check-linux-k5")
SOURCE = linux_paths.linux_source_dir()
CONTRACT_SYSCALL = _REPO / ".tao" / "contracts" / "contract-syscall.md"
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
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "y",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
}

IMAGE = config_pins.config_lines(CONFIG_PINS)

TIMEOUT_BUILD = int(os.environ.get("K5_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K5_QEMU_TIMEOUT", "180"))
JOBS = os.environ.get("JOBS", "32")

#: The check names this image must report, once each (`K5 check <name> ...`).
CASES = {
    "U1": ("u1_write_ret", "u1_file_bytes", "u1_file_content"),
    "U2": ("u2_exited", "u2_exit_code", "u2_exit_reason"),
    "U3": ("u3_ni_enosys", "u3_range_enosys", "u3_mmap_einval",
           "u3_undef_enosys", "u3_rd1_untouched", "u3_rd1_sentinel"),
    "U4": ("u4_frame_rb3", "u4_user_rb3"),
    "U5": ("u5_traps", "u5_trap_ip", "u5_trap_immu18", "u5_cause_cfxtrap",
           "u5_prev_mode_user", "u5_nr_write", "u5_nr_ni", "u5_nr_range",
           "u5_nr_mmap", "u5_version"),
    "U6": ("u6_erestartsys_eintr", "u6_restartblock_eintr"),
    "U7": ("u7_exec_ok", "u7_entry_ip", "u7_exec_rbtp_zero"),
    "U8": ("u8_brk_read", "u8_brk_grow", "u8_brk_recheck", "u8_brk_mm",
           "u8_brk_vma"),
}

#: The syscalls the user program makes, by the name the locked table uses.
STUB_SYSCALLS = ("write", "exit", "mmap")


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
        raise SystemExit(f"k5_syscall_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def syscall_table_snapshot() -> dict:
    """`contract-syscall §1.2`: the locked table snapshot, sha256 verified.

    Returns ``{name: nr}`` from the qemu component's vendored ``syscall.tbl``
    (the contract's own "本仓已锁定快照（可核 / 可复算）"), after checking that
    the file still hashes to the value the contract records.
    """
    text = CONTRACT_SYSCALL.read_text(encoding="utf-8")
    m = re.search(r"`linux-user/riscv/syscall\.tbl`\s*\|\s*`([0-9a-f]{64})`", text)
    if not m:
        raise SystemExit("k5_syscall_probe: contract-syscall §1.2 has no "
                         "snapshot hash for linux-user/riscv/syscall.tbl")
    want = m.group(1)
    work_root = _REPO / "manifests"
    lock = (work_root / "components.lock.toml").read_text(encoding="utf-8")
    # the checkout lives under the manifest's work_root
    root = re.search(r'^work_root\s*=\s*"([^"]+)"', lock, re.M)
    if not root:
        raise SystemExit("k5_syscall_probe: components.lock.toml has no work_root")
    tbl = (_REPO / root.group(1) / "source" / "qemu" / "linux-user" / "riscv" /
           "syscall.tbl")
    if not tbl.is_file():
        raise SystemExit(f"k5_syscall_probe: snapshot missing: {tbl}")
    got = hashlib.sha256(tbl.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit("k5_syscall_probe: the vendored syscall.tbl no longer "
                         f"matches contract-syscall §1.2 ({got[:12]} != {want[:12]})")
    table: dict[str, list[int]] = {}
    for line in tbl.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        nr, abi, name = int(parts[0]), parts[1], parts[2]
        table.setdefault(name, [])
        if abi in ("common", "64"):
            table[name].append(nr)
    return {name: sorted(v)[0] for name, v in table.items() if v}


def musl_argmask() -> dict[str, int]:
    """`musl arch/dadao/syscall_arch.h:__dadao_argmask()`: name -> mask.

    The kernel's own table is a copy of this fact (and
    `tools/qemu/check_syscall_abi.py` compares all carriers); the probe reads it
    here to state the two rows the review named as live expectations.
    """
    patch = _REPO / "components" / "musl" / "patches" / "arch" / "dadao" / \
        "syscall_arch.h.patch"
    live = _REPO / ".work" / "source" / "musl" / "arch" / "dadao" / \
        "syscall_arch.h"
    if live.is_file():
        text = live.read_text(encoding="utf-8")
    elif patch.is_file():
        text = "\n".join(line[1:] for line in
                         patch.read_text(encoding="utf-8").splitlines()
                         if line.startswith("+") and not line.startswith("+++"))
    else:
        raise SystemExit("k5_syscall_probe: musl syscall_arch.h not found")
    start = text.index("__dadao_argmask(long nr)")
    body = text[start:text.index("\n}\n", start) + 3]
    table: dict[str, int] = {}
    pending: list[str] = []
    for line in body.splitlines():
        pending += re.findall(r"case SYS_(\w+):", line)
        m = re.search(r"return (0x[0-9a-fA-F]+);", line)
        if m:
            for name in pending:
                table[name] = int(m.group(1), 16)
            pending = []
    if not table:
        raise SystemExit("k5_syscall_probe: musl argmask table is empty")
    return table


def errno_bounds() -> tuple[int, int]:
    """`contract-syscall §9`: errors are `rd8 = -errno` inside `[-4095, -1]`."""
    text = CONTRACT_SYSCALL.read_text(encoding="utf-8")
    m = re.search(r"取值范围 \*\*`\[(-?\d+), (-?\d+)\]`\*\*", text)
    if not m:
        raise SystemExit("k5_syscall_probe: contract-syscall §9 has no errno range")
    return int(m.group(1)), int(m.group(2))


def parameter_registers() -> dict:
    """`contract-abi §4.1`: which bank each argument class starts at."""
    text = CONTRACT_ABI.read_text(encoding="utf-8")
    sec = text[text.index("### §4.1"):]
    sec = sec[:sec.index("### §4.2")]
    banks = {}
    for label, bank in (("数据参数寄存器", "rd"), ("地址参数寄存器", "rb")):
        m = re.search(r"`" + bank + r"(\d+) - " + bank + r"\d+`：\s*" + label, sec)
        if m:
            banks[label] = int(m.group(1))
    if len(banks) != 2:
        raise SystemExit("k5_syscall_probe: contract-abi §4.1 parameter banks "
                         f"not found (got {banks})")
    return {"data": banks["数据参数寄存器"], "address": banks["地址参数寄存器"]}


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    value = config_value(config, symbol)
    return value is not None and value not in ("n", "0", "")


# ---------------------------------------------------------------------------
# the built image: symbols and the stub's disassembly (the U5 oracle)
# ---------------------------------------------------------------------------

def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def kernel_path() -> Path:
    return build_dir() / "vmlinux"


def tool(name: str) -> str:
    return str(linux_paths.toolchain_bin() / name)


def symbols(elf: Path) -> dict[str, int]:
    out = subprocess.run([tool("llvm-nm"), str(elf)], capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise SystemExit(f"k5_syscall_probe: llvm-nm failed: {out.stderr.strip()}")
    table = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            table[parts[2]] = int(parts[0], 16)
    return table


def elf_section(elf: Path, name: str) -> tuple[int, int, int]:
    """(address, file offset, size) of a section, from `llvm-readelf -S`."""
    out = subprocess.run([tool("llvm-readelf"), "-S", str(elf)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"k5_syscall_probe: llvm-readelf failed: {out.stderr.strip()}")
    for line in out.stdout.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-fA-F]+)\s+"
                     r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", line)
        if m and m.group(1) == name:
            return int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)
    raise SystemExit(f"k5_syscall_probe: section {name} not found in {elf.name}")


def table_slot(elf: Path, table_sym: str, nr: int) -> int:
    """The `sys_call_table[nr]` value, read out of the ELF image."""
    syms = symbols(elf)
    if table_sym not in syms:
        raise SystemExit(f"k5_syscall_probe: {table_sym} not in {elf.name}")
    addr, off, size = elf_section(elf, ".rodata")
    table_addr = syms[table_sym]
    if not (addr <= table_addr < addr + size):
        raise SystemExit("k5_syscall_probe: sys_call_table is not in .rodata")
    data = elf.read_bytes()
    at = off + (table_addr - addr) + nr * 8
    if at + 8 > len(data):
        raise SystemExit("k5_syscall_probe: sys_call_table slot past EOF")
    return struct.unpack(">Q", data[at:at + 8])[0]


def stub_oracle(elf: Path) -> list[tuple[int, int]]:
    """Every `trap` of `dadao_k5_user_stub`: (byte offset, immediate).

    Derived from the built image, not from the kernel's own expectation table:
    the gate takes the symbol's bytes out of the ELF and runs them through the
    toolchain's *decoder* (`llvm-mc --disassemble`), then keeps the `trap`
    instructions with the offset they sit at.  The stub lives in `.rodata`
    (a probe program is data until the probe maps it), so `llvm-objdump -d`
    has nothing to disassemble there — the bytes are the image's own.
    """
    syms = symbols(elf)
    for name in ("dadao_k5_user_stub", "dadao_k5_user_stub_end"):
        if name not in syms:
            raise SystemExit(f"k5_syscall_probe: {name} not in {elf.name}")
    start, end = syms["dadao_k5_user_stub"], syms["dadao_k5_user_stub_end"]
    addr, off, size = elf_section(elf, ".rodata")
    if not (addr <= start and end <= addr + size):
        raise SystemExit("k5_syscall_probe: the stub is not inside .rodata")
    blob = elf.read_bytes()[off + (start - addr):off + (end - addr)]
    words = [blob[i:i + 4] for i in range(0, len(blob) - 3, 4)]
    listing = "".join(" ".join(f"0x{b:02x}" for b in w) + "\n" for w in words)
    out = subprocess.run([tool("llvm-mc"), "-triple=dadao", "--disassemble"],
                         input=listing, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"k5_syscall_probe: llvm-mc --disassemble failed: "
                         f"{out.stderr.strip()}")
    lines = out.stdout.splitlines()
    if len(lines) != len(words):
        raise SystemExit("k5_syscall_probe: the decoder returned a different "
                         f"instruction count ({len(lines)} != {len(words)})")
    traps = []
    for idx, line in enumerate(lines):
        m = re.match(r"\s*trap\s+cfx_umon,\s*(\d+)", line)
        if m:
            traps.append((idx * 4, int(m.group(1))))
    if not traps:
        raise SystemExit("k5_syscall_probe: no trap instruction in the stub")
    return traps


# ---------------------------------------------------------------------------
# console parsing
# ---------------------------------------------------------------------------

_CHECK_RE = re.compile(r"^K5 check (\S+) want=(\S+) got=(\S+) (.*?)(ok|FAIL)$")
_TRAP_RE = re.compile(r"^K5 trap (\d+): ip=(\S+) immu18=(\S+) nr=(\S+) "
                      r"cause=(\S+) mode=(\d+) rb3=(\S+) rd1=(\S+)$")


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
            out.append({"index": m.group(1), "ip": m.group(2),
                        "immu18": m.group(3), "nr": m.group(4),
                        "cause": m.group(5), "mode": m.group(6),
                        "rb3": m.group(7), "rd1": m.group(8)})
    return out


def one(text: str, prefix: str) -> dict[str, str] | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return kv(line)
    return None


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_image(label: str = "k5") -> tuple[int, dict | None]:
    rc = defconfig.apply_config_lines(IMAGE)
    if rc != 0:
        print(f"k5_syscall_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc, None
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the {label} image (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k5_syscall_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124, None
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
        return proc.returncode, None
    return 0, {"config": (build_dir() / ".config").read_text(encoding="utf-8")}


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k5.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = kernel_path()
    if not kernel.is_file():
        raise SystemExit(f"k5_syscall_probe: {kernel} missing")
    qemu = tool("qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k5_syscall_probe: qemu-system-dadao missing "
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

def judge(rep: Report, text: str, rc: int, oracle: list[tuple[int, int]],
          suffix: str = "") -> None:
    """The console of one probe run -> one verdict per case."""
    s = suffix
    table = syscall_table_snapshot()
    lo, hi = errno_bounds()

    rep.check(f"B{s}", "镜像跑到 K5 自检", True, "K5 selftest: begin" in text)
    rep.check(f"B{s}", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K5 selftest FAIL")])

    rows = check_lines(text)
    bad = [name for name, row in rows if row["verdict"] != "ok"]
    rep.check(f"B{s}", "内核自评的每条 K5 check 都 ok", [], bad)

    # Every acceptance item must have said something: a case that never ran is
    # FAIL under its own name, not silently absent.
    seen = [name for name, _ in rows]
    for case, names in CASES.items():
        missing = [n for n in names if n not in seen]
        rep.check(f"{case}{s}", f"{case} 的断言都报了（{len(names)} 条）", [],
                  missing)

    # U5: the trap stream against the disassembly-derived oracle.
    traps = trap_lines(text)
    rep.check(f"U5{s}", "trap 条数 == stub 里的 trap 条数", len(oracle),
              len(traps))
    if traps and len(traps) == len(oracle):
        first_ip = int(traps[0]["ip"], 16)
        bad_ip, bad_immu, bad_nr = [], [], []
        for idx, (row, (off, immu)) in enumerate(zip(traps, oracle)):
            if int(row["ip"], 16) - first_ip != off - oracle[0][0]:
                bad_ip.append(idx)
            if int(row["immu18"], 16) != immu:
                bad_immu.append(idx)
            if row["index"] != str(idx) or row["cause"] != "0x1" or \
                    row["mode"] != "0":
                bad_nr.append(idx)
        rep.check(f"U5{s}", "每条 trap_cause_ip 落在 stub 的 trap 指令上", [],
                  bad_ip)
        rep.check(f"U5{s}", "每条 immu18 == 该 trap 的立即数", [], bad_immu)
        rep.check(f"U5{s}", "每条 cause=CFXTRAP 且 prev_mode=user、序号连续",
                  [], bad_nr)
        # the numbers the program used come from the locked snapshot
        want_nr = {"0": table["write"], "1": table.get("lookup_dcookie"),
                   "3": table["mmap"]}
        got_nr = {row["index"]: int(row["nr"], 16) for row in traps}
        rep.check(f"U5{s}", "rd15 现场值 == 锁定快照的号（write/ni/mmap）",
                  {k: v for k, v in want_nr.items() if v is not None},
                  {k: got_nr.get(k) for k in want_nr if want_nr[k] is not None})

    # U1/U3/U4/U6/U7 are judged in the kernel; the errno *range* is the
    # contract's, so the gate re-reads it from the log rather than trusting the
    # kernel's own in_range flag.
    for name, row in rows:
        if not name.startswith("u3_") or name == "u3_rd1_untouched" or \
                name == "u3_rd1_sentinel":
            continue
        got = int(row["got"], 0)
        rep.check(f"U3{s}", f"{name} 在契约的 errno 区间内", True,
                  lo <= got <= hi and got < 0)

    # The real init: the boot hands the machine to /init.musl and its own
    # output is the end-to-end evidence (the console is shimmed only because
    # this image ships no /dev/console).  Its `brk` goes through the address
    # bank, so "init: brk +65536 ok" is the user ruling C′'s live check.
    for want in ("init: pid=", "init: brk +65536 ok", "K5 init: exit=0"):
        rep.check(f"U8{s}", f"init 自己的输出包含 {want!r}", True,
                  want in text)

    exit_row = one(text, "K5 exit:")
    rep.check(f"U2{s}", "退出观察行存在", True, exit_row is not None)
    if exit_row:
        rep.check(f"U2{s}", "子任务的 exit_code == 0", "0",
                  str(int(exit_row.get("code", "-1"))))

    exec_row = one(text, "K5 exec:")
    rep.check(f"U7{s}", "execve 行存在", True, exec_row is not None)
    if exec_row:
        rep.check(f"U7{s}", "execve 后帧的 rb3 == 0", "0x0",
                  exec_row.get("rb3"))
        rep.check(f"U7{s}", "execve 后帧的 ip == ELF e_entry", True,
                  int(exec_row.get("entry", "1"), 16) ==
                  int(exec_row.get("ip", "0"), 16) and
                  int(exec_row.get("entry", "0"), 16) != 0)

    rep.check(f"D{s}", "启动以 SYS_EXIT(0) 收尾", 0, rc)


CUR: dict = {"config": None, "elf": None}


def static_recon(rep: Report, snap: dict | None) -> None:
    """The pieces a boot cannot show: the image's own configuration and the
    wiring the run depends on."""
    rep.check("S0", "探针镜像可构建", True, snap is not None)
    if snap is None:
        return
    config = snap["config"]
    CUR["config"] = config
    for symbol, value in {"CONFIG_DADAO_K5_SYSCALL_SELFTEST": "y",
                          "CONFIG_DADAO_K4_SELFTEST": "n",
                          "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
                          "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
                          "CONFIG_ARCH_HAS_SYSCALL_WRAPPER": "y",
                          "CONFIG_PAGE_SIZE_64KB": "y"}.items():
        want = config_enabled(config, symbol) if value == "n" else value
        got = (config_value(config, symbol) if value != "n"
               else config_enabled(config, symbol))
        rep.check("B", f"镜像配置：{symbol}={value}", want, got)

    # The table really carries the three entries the stub calls (the failure
    # mode this catches: every slot left at sys_ni_syscall, which answers
    # -ENOSYS for the write and looks like a syscall that "worked").
    elf = kernel_path()
    CUR["elf"] = elf
    syms = symbols(elf)
    table = syscall_table_snapshot()
    for name in STUB_SYSCALLS:
        want = syms.get(f"sys_{name}")
        rep.check("U1" if name == "write" else "U5",
                  f"sys_call_table[{table[name]}] == sys_{name}", want,
                  table_slot(elf, "sys_call_table", table[name]))

    # The ABI hooks of contract-syscall §3: number in rd15, result in rd8.
    hooks = kernel_text("arch/dadao/include/asm/syscall.h")
    banks = parameter_registers()
    rep.check("U5", "syscall_get_nr 取 rd15", True, "regs->rd[15]" in hooks)
    rep.check("U5", "syscall_set_return_value 写 rd8", True,
              "regs->rd[8]" in hooks)
    rep.check("U4", f"参数寄存器按契约分库（数据 rd{banks['data']}、地址 "
              f"rb{banks['address']}）", True,
              "regs->rd[16" in hooks and f"rd{banks['data']}" == "rd16" and
              banks["address"] == 16)

    # The generic chain is kept (`__SC_LONG`) and the entry rebuilds the
    # positional list from the frame by the syscall's argmask.
    wrap = kernel_text("arch/dadao/include/asm/syscall_wrapper.h")
    rep.check("U5", "syscall_wrapper 用通用链 __SC_LONG", True,
              "__SC_LONG" in wrap and "__SC_CAST" in wrap)
    rep.check("U5", "sys_<name> 入口按 argmask 取参", True,
              "dadao_syscall_arg(regs, i)" in wrap and
              "SC_DADAO_ARGS" in wrap)
    argmask = kernel_text("arch/dadao/kernel/syscall_argmask.c")
    rows = dict((int(nr), int(m, 16)) for nr, m in
                re.findall(r"^\s*\[\s*(\d+)\]\s*=\s*(0x[0-9a-fA-F]+)\s*,",
                           argmask, re.M))
    rep.check("U5", "内核 argmask 表非空", True, len(rows) > 0)
    rep.check("U5", "argmask 按位算 rb/rd 槽位", True,
              "addr_before" in argmask and "data_before" in argmask and
              "hweight32" in argmask)
    # brk / mmap are the two the review named: both send their address
    # argument in the RB bank, which the kernel's own prototypes do not say.
    musl = musl_argmask()
    table = syscall_table_snapshot()
    for name in ("brk", "mmap", "ioctl", "ptrace", "semctl"):
        if name in musl and name in table:
            rep.check("U8", f"内核 {name} 的 argmask == musl（{musl[name]:#04x}）",
                      musl[name], rows.get(table[name]))
    # The entry's call is a plain indirect call: the entry takes the frame as
    # an address argument (rb16), so nothing of the register file is reloaded.
    trap = kernel_text("arch/dadao/kernel/trap.S")
    rep.check("U5", "dadao_call_syscall 只传帧（不再装回参数库）", True,
              "call\t[rb5, rd0, 0]" in trap and
              "ldm.o\t{rb16:rb31}" not in trap and
              "ldm.o\t{rd16:rd31}" not in trap)
    rep.check("U4", "调用期间 rb3(rbtp) 保持内核值 0", True,
              "set.rb\trb3, 0" in trap)
    entry = kernel_text("arch/dadao/include/asm/entry.h")
    rep.check("U4", "入口保存 rb3（rbtp）", True,
              "PT_RB_BASE + 3 * 8" in entry)
    rep.check("U4", "返回恢复 rb3（rbtp）", True,
              "ld.o\trb3, [rb3, PT_RB_BASE + 3 * 8]" in entry)

    # The dispatcher: SBI function numbers and the errno shape.
    disp = kernel_text("arch/dadao/kernel/syscalls.c")
    rep.check("U5", "immu18 掩码是契约的 0x3FFFF（syscall.h）", True,
              "DADAO_IMMU18_MASK\t0x3ffffUL" in hooks)
    rep.check("U5", "trap 分派按该掩码解析一次（process.c）", True,
              "info & DADAO_IMMU18_MASK" in kernel_text(
                  "arch/dadao/kernel/process.c"))
    rep.check("U5", "SBI_UMON_GET_VERSION 返回契约版本号", True,
              "DADAO_SBI_VERSION" in disp)
    rep.check("U3", "越界号返回 -ENOSYS", True, "-ENOSYS" in disp)
    rep.check("U6", "内部重启码在返回前转 -EINTR", True,
              "-ERESTARTSYS" in disp and "-EINTR" in disp)
    rep.check("U3", "rd1 不参与 syscall 路径", False,
              re.search(r"rd\[1\]\s*=", disp) is not None)

    # The execve half of §10 lives in start_thread() (setup.c).
    setup = kernel_text("arch/dadao/kernel/setup.c")
    sec = setup[setup.index("void start_thread("):]
    sec = sec[:sec.index("\n}")]
    rep.check("U7", "start_thread 清 rbtp（execve 侧）", True,
              "rb[3] = 0" in sec)


# ---------------------------------------------------------------------------
# injections
# ---------------------------------------------------------------------------

#: name -> (file, needle, replacement, case that must go red, why)
INJECTIONS = {
    "no-rb3-restore": (
        "arch/dadao/include/asm/entry.h",
        "\tld.o\trb3, [rb3, PT_RB_BASE + 3 * 8]\n",
        "",
        "U4", "返回不从帧恢复 rb3(rbtp) ⇒ 用户看到的 rbtp 变成帧地址，U4 红"),
    "result-to-rd1": (
        "arch/dadao/kernel/syscalls.c",
        "\tregs->rd[8] = (unsigned long)ret;\n",
        "\tregs->rd[1] = (unsigned long)ret;\n",
        "U3", "结果写 rd1 而非 rd8 ⇒ rd8 不动、rd1 哨兵被改，U3 红"),
    "immu18-wrong-mask": (
        # The one parse site: the dispatcher's, which the probe's observer
        # also reads (kernel/process.c, right before the K5 hook).
        "arch/dadao/kernel/process.c",
        "\timmu18 = info & DADAO_IMMU18_MASK;\n",
        "\timmu18 = info & 0x3ff;\n",
        "U5", "immu18 取错位段 ⇒ 0x2AAA 变 0x2AA，U5 红"),
    "errno-minus-one": (
        "arch/dadao/kernel/syscalls.c",
        "\t\tregs->rd[8] = (unsigned long)-ENOSYS;\n\t\treturn 0;\n\t}\n"
        "\tnr = array_index_nospec",
        "\t\tregs->rd[8] = (unsigned long)-1;\n\t\treturn 0;\n\t}\n"
        "\tnr = array_index_nospec",
        "U3", "越界号返回 -1 而非 -errno ⇒ U3 红"),
    "argmask-brk": (
        "arch/dadao/kernel/syscall_argmask.c",
        "\t[214] = 0x01,\t/* brk */\n",
        "\t[214] = 0x00,\t/* brk */\n",
        "U8", "把 brk 的路由改成「数据」⇒ 内核读 rd16(=0)，U8 红"),
    "argmask-mmap": (
        "arch/dadao/kernel/syscall_argmask.c",
        "\t[222] = 0x01,\t/* mmap */\n",
        "\t[222] = 0x00,\t/* mmap */\n",
        "U3", "把 mmap 的路由改成「数据」⇒ 参数错位、-EINVAL 不再出现，U3 红"),
    "exec-keeps-rbtp": (
        "arch/dadao/kernel/setup.c",
        "\tregs->rb[3] = 0;\n",
        "\tregs->rb[3] = 0x1234UL;\n",
        "U7", "execve 不清 rbtp ⇒ U7 红"),
}


def run_injection(rep: Report, name: str, rom: str,
                  oracle: list[tuple[int, int]]) -> None:
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
        # the oracle is re-derived: the stub is unchanged by these injections,
        # but the image's symbol addresses are not, and the trap offsets are
        # what the console's lines are compared against.
        rc, out = boot(f"inject-{name}", rom)
        # The injection must not have moved the user program: if the traps
        # still sit at the disassembled offsets, the red check that follows is
        # attributable to the injected semantics, not to a broken image.  Only
        # the *offsets* are compared — an injected `immu18` parse is expected to
        # change the immediates the console shows, and that is the defect.
        traps = trap_lines(out)
        same = (len(traps) == len(oracle) and bool(traps) and
                all(int(row["ip"], 16) - int(traps[0]["ip"], 16) ==
                    off - oracle[0][0]
                    for row, (off, _) in zip(traps, oracle)))
        rep.check(f"INJECT {name}", "桩未变（trap 位置仍与反汇编一致）", True,
                  same)
        rows = check_lines(out)
        red = [n for n, row in rows if row["verdict"] != "ok"]
        case_ok = [n for n, row in rows
                   if row["verdict"] == "ok" and n.startswith(case.lower()[:2])]
        died = any(tok in out for tok in ("dadao: die mode=",
                                          "K5 selftest FAIL",
                                          "Kernel panic"))
        rep.info(f"inject {name}: rc={rc} red={red[:5]} died={died}")
        rep.check(f"INJECT {name}", f"{why} ⇒ {case} 红", True,
                  bool([n for n in red if n.startswith(case.lower()[:2])]) or
                  died or not case_ok)
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
    oracle = [(0x00, 0), (0x10, 0)]
    text = (
        "K5 selftest: begin pid=1 mm=0\n"
        "K5 trap 0: ip=0x10000400000 immu18=0x0 nr=0x40 cause=0x1 mode=0 "
        "rb3=0x0 rd1=0x0\n"
        "K5 trap 1: ip=0x10000400020 immu18=0x7 nr=0x12 cause=0x2 mode=1 "
        "rb3=0x5 rd1=0x5\n"
        "K5 check u1_write_ret want=0xc got=0x0 FAIL\n"
        "K5 check u3_ni_enosys want=-38 got=-1 in_range=0 FAIL\n"
        "K5 exit: child=16 state=32 status=0x100 code=1 rounds=4\n"
        "K5 exec: rc=0 entry=0x211c8 ip=0x211d0 rb3=0x1234 mm=1\n"
        "K5 selftest FAIL: u1_write_ret=0x0 code=0x61\n"
    )
    CUR["config"] = ""
    judge(rep, text, 1, oracle)
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
    parser = argparse.ArgumentParser(description="M14 K5 user-syscall probe")
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
        print("k5_syscall_probe: no image; judging stops here", file=sys.stderr)
        return 1
    oracle = stub_oracle(kernel_path())
    rep.info(f"stub oracle (from the built image): {[(hex(o), hex(i)) for o, i in oracle]}")
    rom = firmware()
    rc, out = boot("k5", rom)
    judge(rep, out, rc, oracle)

    if not args.no_inject:
        names = args.inject or sorted(INJECTIONS)
        for name in names:
            if name not in INJECTIONS:
                raise SystemExit(f"k5_syscall_probe: unknown injection {name!r}")
            run_injection(rep, name, rom, oracle)

    print()
    if rep.failed:
        print(f"k5_syscall_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"k5_syscall_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
