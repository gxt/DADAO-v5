#!/usr/bin/env python3
"""run_semihosting_smoke.py — semihosting console/exit closure (`make linux-semihosting-smoke`).

K0 has no kernel yet, so the *guest exit code -> host `$?`* link is proven with
the existing bare-metal semihosting probes, which use the same machine model
and the same `SYS_EXIT` service the kernel-side init will use later:

  * `semihost_smoke.elf`  SYS_EXIT {ADP_Stopped_ApplicationExit, 0}   -> `$? = 0`
  * `semihost_fail.elf`   SYS_EXIT {ADP_Stopped_ApplicationExit, 64}  -> `$? = 64`

Two independent properties per run (spec/Kaiwu §5.3/§5.5):

  1. exit code: the QEMU *process* status, read directly from
     `subprocess.returncode` — never through a shell pipe (`| tee`/`| tail`
     would swallow it);
  2. console bytes: the guest console stream must equal the oracle derived
     from the probe *sources* (`tests/ee-tiny/semihost_msg_tiny.inc` for the
     SYS_WRITE0 payload, `semihost_smoke_tiny.S`'s `EXCL` for the SYS_WRITEC
     character).  QEMU's own output is never used to build the expectation.

A QEMU startup failure (missing firmware, bad machine) is reported separately
from a guest exit code: such a run carries QEMU's own error text on stderr and
is never accepted as "guest exited with N".

Usage:
  python3 tests/ee-tiny/run_semihosting_tiny.py

Requires: `make install-host build-bootrom`.  Missing prerequisites exit 2 with
the exact make invocation to run.

Exit status: 0 = every check passed; 1 = a check failed; 2 = setup error.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]   # `tests/ee-tiny/`（m15-testcases-011）
sys.path.insert(0, str(_REPO_ROOT))

from tools.infra import paths as infra_paths  # noqa: E402
from tools.infra import writer_guard  # noqa: E402

BOOTROM_REL = Path("bootrom")

#: Guest exit codes fixed by the probe sources (`--defsym EXIT_CODE=…` in the
#: Makefile's build-bootrom rule; values are the probe's own contract, not read
#: back from a run).
EXPECT_SMOKE_RC = 0
EXPECT_FAIL_RC = 64

#: The semihosting console is QEMU's stderr (ARM semihosting `target=native`
#: writes the guest console to stderr); stdout must stay empty so the check
#: cannot pass on a partially captured stream.
QEMU_TIMEOUT_S = 120
QEMU_ERROR_PREFIX = b"qemu-system-dadao:"

_MSG_INC = _REPO_ROOT / "tests" / "ee-tiny" / "semihost_msg_tiny.inc"
_SMOKE_S = _REPO_ROOT / "tests" / "ee-tiny" / "semihost_smoke_tiny.S"


class SetupError(RuntimeError):
    """Missing prerequisite (exit 2)."""


class CheckError(RuntimeError):
    """A required property did not hold (exit 1)."""


# ── source-text oracle (independent of QEMU and of the assembler) ────────────

_ESCAPES = {
    "n": b"\n", "t": b"\t", "r": b"\r", "0": b"\0",
    "\\": b"\\", '"': b'"', "'": b"'",
}


def _decode_asm_string(text: str) -> bytes:
    """Decode one `.ascii "…"` payload (C escapes only; UTF-8 stays verbatim)."""
    out = bytearray()
    i = 0
    while i < len(text):
        char = text[i]
        if char != "\\":
            out += char.encode("utf-8")
            i += 1
            continue
        if i + 1 >= len(text):
            raise CheckError("dangling backslash in an .ascii literal")
        esc = text[i + 1]
        if esc in _ESCAPES:
            out += _ESCAPES[esc]
            i += 2
            continue
        raise CheckError(f"unsupported escape '\\{esc}' in an .ascii literal")
    return bytes(out)


def _ascii_payloads(line: str) -> list[bytes]:
    return [_decode_asm_string(m) for m in re.findall(r'\.ascii\s+"((?:[^"\\]|\\.)*)"', line)]


def derive_oracle() -> bytes:
    """The expected console stream, rebuilt from the probe sources."""
    if not _MSG_INC.is_file():
        raise SetupError(f"{_MSG_INC} not found (source-text oracle)")
    payload = b"".join(
        part
        for line in _MSG_INC.read_text(encoding="utf-8").splitlines()
        for part in _ascii_payloads(line)
    )
    if not payload:
        raise CheckError(f"no .ascii payload found in {_MSG_INC.name}")

    # The SYS_WRITEC character is the `.ascii` right after the `EXCL:` label.
    excl: bytes | None = None
    lines = _SMOKE_S.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("EXCL:"):
            for follow in lines[index + 1:index + 4]:
                parts = _ascii_payloads(follow)
                if parts:
                    excl = b"".join(parts)
                    break
            break
    if excl is None:
        raise CheckError(f"could not derive the SYS_WRITEC character from {_SMOKE_S.name}")
    return payload + excl


# ── run ─────────────────────────────────────────────────────────────────────

def _qemu() -> Path:
    path = infra_paths.host_toolchain_bin() / "qemu-system-dadao"
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host' first")
    return path


def _prereq(rel: str) -> Path:
    path = infra_paths.test_artifacts_dir() / BOOTROM_REL / rel
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host build-bootrom' first")
    return path


def run_case(elf: Path, bootrom: Path, oracle: bytes, expected_rc: int, label: str,
             timeout: int) -> int:
    failures = 0
    try:
        proc = subprocess.run(
            [str(_qemu()), "-M", "kaiwu-tiny", "-bios", str(bootrom),
             "-kernel", str(elf),
             "-semihosting-config", "enable=on,target=native",
             "-display", "none", "-nographic", "-monitor", "none"],
            capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[FAIL] {label}: QEMU did not terminate within {timeout}s")
        return 1

    if QEMU_ERROR_PREFIX in proc.stderr:
        print(f"[FAIL] {label}: QEMU itself failed (not a guest exit code); "
              f"rc={proc.returncode} stderr={proc.stderr[:200]!r}")
        return 1

    # 1. guest exit code -> host $? (read straight from the process status)
    ok = proc.returncode == expected_rc
    failures += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: exit code | "
          f"expected={expected_rc} actual={proc.returncode}")

    # 2. console bytes == source oracle, byte for byte
    ok = proc.stderr == oracle
    failures += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: console bytes | "
          f"expected={len(oracle)} actual={len(proc.stderr)} "
          f"sha256_expected={_sha(oracle)[:16]} sha256_actual={_sha(proc.stderr)[:16]}")
    ok = proc.stdout == b""
    failures += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: stdout empty | "
          f"expected=0 actual={len(proc.stdout)}")
    return failures


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── main ───────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="semihosting console/exit-code smoke")
    parser.add_argument("--timeout", type=int, default=QEMU_TIMEOUT_S,
                       help=f"per-run timeout in seconds (default {QEMU_TIMEOUT_S})")
    writer_guard.add_arguments(parser)
    args = parser.parse_args()

    try:
        bootrom = _prereq("tiny/bootrom_tiny.bin")
        smoke = _prereq("semihost_smoke.elf")
        fail = _prereq("semihost_fail.elf")
        oracle = derive_oracle()

        # ISS-373: refuse on an active writer, then hash the QEMU binary (and
        # the bootrom) at start and at finish.
        guard = writer_guard.start_guard(
            args, [str(_qemu()), str(bootrom)], label="run_semihosting_smoke")

        print(f"[INFO] oracle: {len(oracle)} bytes from "
              f"{_MSG_INC.name} + semihost_smoke_tiny.S:EXCL")
        failures = 0
        failures += run_case(smoke, bootrom, oracle, EXPECT_SMOKE_RC,
                             "semihost_smoke.elf", args.timeout)
        failures += run_case(fail, bootrom, oracle, EXPECT_FAIL_RC,
                             "semihost_fail.elf", args.timeout)
    except SetupError as exc:
        print(f"run_semihosting_smoke: SETUP ERROR: {exc}", file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"run_semihosting_smoke: FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"run_semihosting_smoke: {'PASS' if failures == 0 else 'FAIL'} "
          f"(failed checks: {failures})")
    guard_ok = writer_guard.finish_guard(guard)
    return 0 if (failures == 0 and guard_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
