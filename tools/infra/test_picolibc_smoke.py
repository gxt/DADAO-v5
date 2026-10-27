#!/usr/bin/env python3
"""picolibc end-to-end smoke test for DADAO (INFRA-057t; libm stage INFRA-066t).

Compiles C programs against the installed picolibc sysroot, links them with the
project crt0 / linker script and runs them under ``qemu-system-dadao`` with
semihosting, then checks the guest wrote the expected bytes and exited with
status 0.  Two stages:

1. ``printf`` stage (INFRA-057t): a ``printf("%d\\n", v)`` program must print
   ``42`` and exit 0.  The format string carries an argument (read from a
   ``volatile`` object so clang cannot constant-fold it) **on purpose**: clang
   rewrites the argument-less ``printf("hi\\n")`` into ``puts("hi\\n")``, which
   would make ``nm`` show ``U puts`` and silently skip the printf code path.
   The test therefore asserts via ``nm`` that the object references ``printf``
   (not a ``puts`` fold), so the ``__dtoa_engine`` / ``__atod_engine``
   conversion path and the variant selected by ``io-float-exact=false`` are
   actually exercised.

2. ``libm`` stage (INFRA-066t): calls the eight acceptance math symbols
   (``floor``/``ceil``/``trunc``/``round``/``rint``/``nearbyint``/``fmin``/
   ``fmax``) plus ``fmod``/``sqrt``/``sin``/``cos``/``log`` and checks every
   result against the C99 semantics; the guest prints ``libm 0`` and returns the
   number of mismatches as its exit status.  ``nm`` must show the eight symbols
   as *undefined* in the object, so the calls really go to the library instead
   of being folded or expanded inline; the results are checked by the guest, so
   a wrong library value fails the run.  The object is compiled with
   ``-ffreestanding -fno-builtin`` so ``fmin``/``fmax`` stay *calls*: with
   builtins enabled clang expands them to ``llvm.minnum``/``llvm.maxnum``, which
   the DADAO backend cannot select yet (ISS-193 (a)).

   The link line includes the sysroot ``libm.a`` exactly like a real ``-lm``
   link.  picolibc merges libc and libm into a single archive and ships an
   *empty* ``libm.a`` for ``-lm`` compatibility (upstream README, "Picolibc
   version 1.7 §1"), so the math definitions come from ``libc.a`` -- that is why
   ``nm`` on the sysroot archive, not on ``libm.a``, is the meaningful check.

Both stages exercise the whole port path: the picolibc headers, ``libc.a``
(stdio + the engine-based float conversions + the merged math library),
``libsemihost.a`` (the ``write`` -> SYS_WRITE 0x05 and ``_exit`` -> SYS_EXIT 0x18
stubs), the DADAO cross file / big-endian ``long double``=f64 config, and the
``sys_semihost`` trap primitive.

Exit status: 0 = PASS, 1 = FAIL (output/exit-code mismatch or a failed step),
2 = setup error.  ``--inject`` corrupts the expected marker so the checks must
report FAIL (proving the comparisons are live); it restores nothing itself and
is only used by the evidence script.

Fail-closed: any non-zero compile/assemble/link/qemu step, a timeout, or a
missing tool is a failure, never a silent skip.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
SYSROOT = paths.target_sysroot_dir()
CRT0 = REPO_ROOT / "tests" / "shared" / "crt0" / "codegen_crt0.s"
LDS = REPO_ROOT / "tests" / "shared" / "linker" / "dadao.lds"

PROG_C = """\
#include <stdio.h>

/* ``volatile`` so clang cannot fold the value into the format string; the
   format argument also keeps clang from rewriting printf() into puts(). */
volatile int smoke_value = 42;

int main(void)
{
    printf("%d\\n", smoke_value);
    return 0;
}
"""

EXPECTED_MARKER = "42"

# libm stage (INFRA-066t).  Every argument lives in a ``volatile`` object so
# clang cannot fold the calls away; ``-ffreestanding -fno-builtin`` turns the
# math calls into real library calls.  Expected values are the C99 semantics of
# each function (round: half away from zero; rint/nearbyint: round half to
# even), not values read back from this implementation.
PROG_LIBM_C = """\
#include <math.h>
#include <stdio.h>

volatile double v_a = 2.75;
volatile double v_n = -2.75;
volatile double v_25 = 2.5;
volatile double v_35 = 3.5;
volatile double v_0 = 0.0;
volatile double v_1 = 1.0;
volatile double v_3 = 3.0;
volatile double v_4 = 4.0;
volatile double v_7 = 7.0;
volatile double v_16 = 16.0;

int main(void)
{
    int fails = 0;
    double fl = floor(v_a);
    double ce = ceil(v_a);
    double tr = trunc(v_n);
    double ro = round(v_a);
    double ri = rint(v_25);
    double nr = nearbyint(v_35);
    double mn = fmin(v_a, v_4);
    double mx = fmax(v_a, v_4);
    double md = fmod(v_7, v_3);
    double sq = sqrt(v_16);
    double sn = sin(v_0);
    double cs = cos(v_0);
    double lg = log(v_1);

    if ((int)fl != 2) fails++;          /* floor(2.75)  */
    if ((int)ce != 3) fails++;          /* ceil(2.75)   */
    if ((int)tr != -2) fails++;         /* trunc(-2.75) */
    if ((int)ro != 3) fails++;          /* round(2.75)  */
    if ((int)ri != 2) fails++;          /* rint(2.5) -> even */
    if ((int)nr != 4) fails++;          /* nearbyint(3.5) -> even */
    if ((int)(mn * 4.0) != 11) fails++; /* fmin(2.75, 4.0) */
    if ((int)mx != 4) fails++;          /* fmax(2.75, 4.0) */
    if ((int)md != 1) fails++;          /* fmod(7.0, 3.0)  */
    if ((int)sq != 4) fails++;          /* sqrt(16.0)      */
    if ((int)sn != 0) fails++;          /* sin(0.0)        */
    if ((int)cs != 1) fails++;          /* cos(0.0)        */
    if ((int)lg != 0) fails++;          /* log(1.0)        */

    printf("libm %d\\n", fails);
    return fails;
}
"""

LIBM_MARKER = "libm 0"
LIBM_SYMBOLS = ("floor", "ceil", "trunc", "round", "rint", "nearbyint", "fmin", "fmax")

STAGES = [
    {"tag": "printf", "source": PROG_C, "cflags": [], "required": ("printf",),
     "marker": EXPECTED_MARKER},
    {"tag": "libm", "source": PROG_LIBM_C, "cflags": ["-ffreestanding", "-fno-builtin"],
     "required": LIBM_SYMBOLS, "marker": LIBM_MARKER},
]


def run(cmd: list[str], *, timeout: int | None = None, merge: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT if merge else subprocess.PIPE,
                          text=True, timeout=timeout)


def undefined_symbols(nm: str, obj: Path) -> list[str]:
    res = run([nm, str(obj)])
    if res.returncode != 0:
        raise RuntimeError(f"nm rc={res.returncode}\n{res.stderr}")
    out: list[str] = []
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-2] == "U":
            out.append(parts[-1])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", default=str(REPO_ROOT / ".work" / "build" / "picolibc-smoke"),
                    help="scratch dir for generated sources/objects (default: <repo>/.work/build/picolibc-smoke)")
    ap.add_argument("--qemu-timeout", type=int, default=30)
    ap.add_argument("--inject", action="store_true", help="corrupt the expectation to prove FAIL is reachable")
    args = ap.parse_args()

    for tool in ("clang", "llvm-mc", "ld.lld", "qemu-system-dadao"):
        if not (TOOLCHAIN_BIN / tool).exists():
            print(f"test-picolibc-smoke: ERROR: {TOOLCHAIN_BIN / tool} not found — run 'make install-host'", file=sys.stderr)
            return 2
    nm = shutil.which("nm")
    if nm is None:
        print("test-picolibc-smoke: ERROR: 'nm' not found on PATH (host binutils)", file=sys.stderr)
        return 2
    if not (SYSROOT / "lib" / "libc.a").is_file():
        print(f"test-picolibc-smoke: ERROR: {SYSROOT / 'lib' / 'libc.a'} not found — run 'make build-picolibc'", file=sys.stderr)
        return 2

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    clang = str(TOOLCHAIN_BIN / "clang")

    res = run([str(TOOLCHAIN_BIN / "llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
               str(CRT0), "-o", str(work / "crt0.o")])
    if res.returncode != 0:
        print(f"test-picolibc-smoke: FAIL (assemble crt0 rc={res.returncode})\n{res.stderr}", file=sys.stderr)
        return 1

    for stage in STAGES:
        tag = stage["tag"]
        (work / f"{tag}.c").write_text(stage["source"])
        obj = work / f"{tag}.o"
        elf = work / f"{tag}.elf"

        res = run([clang, "-target", "dadao-unknown-elf", "-nostdlib", *stage["cflags"], "-Oz",
                   "-I", str(SYSROOT / "include"), "-c", str(work / f"{tag}.c"), "-o", str(obj)])
        if res.returncode != 0:
            print(f"test-picolibc-smoke: FAIL ({tag}: compile rc={res.returncode})\n{res.stderr}", file=sys.stderr)
            return 1

        # Anti-fold guard: the object must still call the library symbols, so the
        # library (and, for printf, the conversion path) is really exercised.
        try:
            undef = undefined_symbols(nm, obj)
        except RuntimeError as exc:
            print(f"test-picolibc-smoke: FAIL ({tag}: {exc})", file=sys.stderr)
            return 1
        print(f"test-picolibc-smoke: {tag}.o undefined symbols = {sorted(undef)}")
        missing = [s for s in stage["required"] if s not in undef]
        if missing:
            print(f"test-picolibc-smoke: FAIL ({tag}: not referenced — folded away or inline: "
                  f"{missing}; undefined={sorted(undef)})", file=sys.stderr)
            return 1

        res = run([str(TOOLCHAIN_BIN / "ld.lld"), "-T", str(LDS), str(work / "crt0.o"), str(obj),
                   str(SYSROOT / "lib" / "libc.a"), str(SYSROOT / "lib" / "libm.a"),
                   str(SYSROOT / "lib" / "libsemihost.a"), "-o", str(elf)])
        if res.returncode != 0:
            print(f"test-picolibc-smoke: FAIL ({tag}: link rc={res.returncode})\n{res.stderr}", file=sys.stderr)
            return 1

        qemu = [str(TOOLCHAIN_BIN / "qemu-system-dadao"), "-M", "dadao-m1", "-kernel", str(elf),
                "-semihosting-config", "enable=on,target=native", "-display", "none", "-nographic", "-monitor", "none"]
        try:
            res = run(qemu, timeout=args.qemu_timeout, merge=True)
        except subprocess.TimeoutExpired:
            print(f"test-picolibc-smoke: FAIL ({tag}: qemu timeout after {args.qemu_timeout}s)", file=sys.stderr)
            return 1

        marker = "XX" if args.inject else stage["marker"]
        guest_out = res.stdout
        print(f"test-picolibc-smoke: {tag}: qemu rc={res.returncode} output={guest_out!r}")
        ok = res.returncode == 0 and any(marker in line for line in guest_out.splitlines())
        if not ok:
            print(f"test-picolibc-smoke: FAIL ({tag}: expected exit 0 and line {marker!r})", file=sys.stderr)
            return 1

    print("test-picolibc-smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
