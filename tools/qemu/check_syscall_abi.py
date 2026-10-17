#!/usr/bin/env python3
"""QEMU-062t: cross-check the syscall ABI facts that must not drift.

Three independent facts are compared, each derived from a different artefact:

1. **number table vs the locked snapshot** -- ``linux-user/dadao/syscall.tbl``
   must be byte-identical to the qemu tree's ``linux-user/riscv/syscall.tbl``,
   whose sha256 the contract pins (contract-syscall.md §1.2).  The expected
   digest is *read from the contract*, not from the tree.
2. **argument routing, guest vs host** -- the guest stub decides where each
   argument goes (data bank rd16+ / address bank rb16+) from the syscall number
   (musl ``arch/dadao/syscall_arch.h:__dadao_argmask`` and, for cancellable
   calls, ``src/thread/dadao/syscall_cp.s``).  The host must reconstruct the
   positional list with the SAME mask (``linux-user/dadao/cpu_loop.c:
   dadao_argmask``).  All three tables are parsed here and must agree number
   for number.
3. **AUDIT_ARCH_DADAO** -- preprocessed out of
   ``linux-user/dadao/target_syscall.h`` and compared with the contract's
   ruling (EM_DADAO | AUDIT_ARCH_64BIT, no AUDIT_ARCH_LE bit).

Exit status: 0 only when every check passes.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QEMU = ROOT / ".work" / "source" / "qemu"
MUSL = ROOT / ".work" / "source" / "musl"
CONTRACT = ROOT / ".tao" / "contracts" / "contract-syscall.md"

HOST_TABLE = QEMU / "linux-user" / "dadao" / "cpu_loop.c"
GUEST_TABLE = MUSL / "arch" / "dadao" / "syscall_arch.h"
GUEST_CP = MUSL / "src" / "thread" / "dadao" / "syscall_cp.s"
TARGET_SYSCALL_H = QEMU / "linux-user" / "dadao" / "target_syscall.h"
SYSCALL_TBL = QEMU / "linux-user" / "dadao" / "syscall.tbl"
ABIS = {"common", "64", "riscv", "rlimit", "memfd_secret"}

results: list[tuple[str, str, str, bool]] = []


def check(name: str, expected, actual, ok: bool | None = None) -> None:
    if ok is None:
        ok = expected == actual
    results.append((name, str(expected), str(actual), bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} actual={actual}")


def contract_sha256(path: str) -> str:
    text = CONTRACT.read_text()
    for line in text.splitlines():
        if path in line and "sha256" not in line:
            # table row: | `path` | `digest` |
            cells = [c.strip().strip("`") for c in line.split("|")]
            for cell in cells:
                if re.fullmatch(r"[0-9a-f]{64}", cell):
                    return cell
    raise SystemExit(f"cannot find the pinned sha256 of {path} in the contract")


def tbl_numbers() -> dict[str, int]:
    nums: dict[str, int] = {}
    for line in SYSCALL_TBL.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3 or parts[1] not in ABIS:
            continue
        nr = int(parts[0], 0)
        nums[parts[2]] = nr
    return nums


def guest_numbers() -> dict[str, int]:
    nums: dict[str, int] = {}
    p = MUSL / "arch" / "dadao" / "bits" / "syscall.h.in"
    for m in re.finditer(r"^#define\s+__NR_(\w+)\s+(\d+)", p.read_text(), re.M):
        nums[m.group(1)] = int(m.group(2))
    return nums


def parse_c_table(path: Path, prefix: str) -> dict[str, int]:
    """Map nr-name -> pointer mask out of the switch statement."""
    text = path.read_text()
    start = text.index("dadao_argmask")
    body = text[start:]
    table: dict[str, int] = {}
    for block in re.finditer(
            r"((?:\s*case\s+" + prefix + r"\w+\s*:[^\n]*\n)+)"
            r"\s*return\s+(0x[0-9A-Fa-f]+|\d+);", body):
        mask = int(block.group(2), 0)
        for name in re.findall(prefix + r"(\w+)\s*:", block.group(1)):
            table[name] = mask
    return table


def parse_guest_table(path: Path) -> dict[str, int]:
    text = path.read_text()
    start = text.index("__dadao_argmask")
    body = text[start:]
    table: dict[str, int] = {}
    for block in re.finditer(
            r"((?:\s*case\s+SYS_\w+\s*:[^\n]*\n)+)"
            r"\s*return\s+(0x[0-9A-Fa-f]+|\d+);", body):
        mask = int(block.group(2), 0)
        for name in re.findall(r"SYS_(\w+)\s*:", block.group(1)):
            table[name] = mask
    return table


def parse_cp_asm(path: Path) -> dict[int, int]:
    """(number, mask) pairs out of the cancellable-syscall stub's dispatch."""
    text = path.read_text()
    labels = {"1": 0x01, "2": 0x02, "4": 0x04, "0": 0x00}
    out: dict[int, int] = {}
    for m in re.finditer(
            r"set\.zw\s+rd9,\s+wp0,\s+(0x[0-9A-Fa-f]+|\d+)\s*\n"
            r"\s*br\.eq\s+\{rd16, rd9\}\?,\s*\[rb0,\s*\.Lmask(\d)\]", text):
        out[int(m.group(1), 0)] = labels[m.group(2)]
    return out


def preprocess_audit_arch() -> int:
    """Evaluate AUDIT_ARCH_DADAO with the host C compiler.

    target_syscall.h is deliberately dependency-free, so it can be compiled
    standalone: the value printed at run time is the one the emulator is built
    with, not a number re-typed in this script.
    """
    src = (f'#include <stdio.h>\n#include "{TARGET_SYSCALL_H}"\n'
           'int main(void) { printf("%x\\n", (unsigned)AUDIT_ARCH_DADAO); return 0; }\n')
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "audit.c"
        exe = Path(tmp) / "audit"
        f.write_text(src)
        r = subprocess.run(["cc", "-I", str(QEMU), str(f), "-o", str(exe)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"cc failed: {r.stderr}")
        out = subprocess.run([str(exe)], capture_output=True, text=True)
    return int(out.stdout.strip(), 16)


def main() -> int:
    # 1. number table
    pinned = contract_sha256("linux-user/riscv/syscall.tbl")
    actual = hashlib.sha256(SYSCALL_TBL.read_bytes()).hexdigest()
    check("number table == contract §1.2 snapshot", pinned, actual)

    # 2. routing tables
    nums = tbl_numbers()
    guest_nums = guest_numbers()
    host = parse_c_table(HOST_TABLE, "TARGET_NR_")
    guest = parse_guest_table(GUEST_TABLE)
    check("host routing table non-empty", "True", str(bool(host)))
    check("guest routing table non-empty", "True", str(bool(guest)))

    check("routing: same number set (host vs guest stub)",
          sorted(guest), sorted(host))
    for name in sorted(set(host) & set(guest)):
        check(f"routing mask {name} (host == guest stub)",
              hex(guest[name]), hex(host[name]))
        if name in nums:
            check(f"routing {name}: number in the locked table", nums[name],
                  guest_nums.get(name))

    cp = parse_cp_asm(GUEST_CP)
    check("routing: cancellable stub table non-empty", "True", str(bool(cp)))
    for nr, mask in sorted(cp.items()):
        # reverse-map the number to a name through the locked table
        name = next((n for n, v in nums.items() if v == nr), None)
        check(f"routing mask in syscall_cp.s for nr {nr}"
              f" ({name or 'not in the locked table'})",
              hex(host.get(name, -1)) if name else "n/a", hex(mask))

    # 3. audit arch
    value = preprocess_audit_arch()
    check("AUDIT_ARCH_DADAO == EM_DADAO | AUDIT_ARCH_64BIT",
          hex(0x0DA0 | 0x80000000), hex(value))
    check("AUDIT_ARCH_DADAO has no AUDIT_ARCH_LE bit", 0, value & 0x40000000)

    bad = [r for r in results if not r[3]]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
