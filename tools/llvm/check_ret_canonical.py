#!/usr/bin/env python3
"""check_ret_canonical.py — contract-level probe for narrow-return canonicalisation.

contract-abi.md §4.4 C5: a value narrower than 8 bytes is extended by the
**callee** (§4.2 sign/zero rules) to a canonical 64-bit value before `ret`;
the caller may assume the full return register is canonical.  clang's C caller
inserts its own extension, which would hide a missing callee-side conversion,
so this probe uses a **hand-written assembly consumer** (not clang) that calls
the function and stores the *full* 64-bit `rd8` for a C assertion.

Cases (independent oracle = C semantics + §4.2/§4.4 canonical values):
  addu     unsigned(0xFFFFFFFF, 1) -> 0x0000000000000000   (zero-extend)
  add_s    int(-1, -1)             -> 0xfffffffffffffffe   (sign-extend)
  neg      int(-2147483648)        -> 0xffffffff80000000   (sign-extend)
  uc_inc   unsigned char(0xFF)+1   -> 0x0000000000000000   (zero-extend i8)
  sc_inc   signed char(0x7F)+1     -> 0xffffffffffffff80   (sign-extend i8)
  us_inc   unsigned short(0xFFFF)+1-> 0x0000000000000000   (zero-extend i16)
  ss_inc   short(0x7FFF)+1         -> 0xffffffffffff8000   (sign-extend i16)
  bnot     _Bool(0)                -> 0x0000000000000001   (zero-extend i1)

`--expect-broken` is for retaining the pre-fix现场: it succeeds when the run
fails and at least one of addu/neg is reported FAIL (the i8/i16/i1 controls
must stay OK).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

IMPL = r"""
unsigned addu(unsigned a, unsigned b) { return a + b; }
int add_s(int a, int b) { return a + b; }
int neg(int a) { return -a; }
unsigned char uc_inc(unsigned char a) { return (unsigned char)(a + 1); }
signed char sc_inc(signed char a) { return (signed char)(a + 1); }
unsigned short us_inc(unsigned short a) { return (unsigned short)(a + 1); }
short ss_inc(short a) { return (short)(a + 1); }
_Bool bnot(_Bool a) { return !a; }
"""

# Hand-written consumers: set the arguments per contract-abi §4.1/§4.2, call
# the callee, and store the FULL 64-bit rd8 to *out (rb16).
CONSUMER = r"""
	.text

	.globl call_addu
	.type call_addu,@function
call_addu:                       ; out(rb16); addu(0xFFFFFFFF,1)
	set.zw rd16, wp0, 0xffff
	or.w rd16, wp1, 0xffff
	set.zw rd17, wp0, 0x1
	call [rb0, addu]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_add_s
	.type call_add_s,@function
call_add_s:                      ; out(rb16); add_s(-1,-1)
	set.ow rd16, wp0, 0xffff
	rd2rd {rd17}, {rd16}
	call [rb0, add_s]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_neg
	.type call_neg,@function
call_neg:                        ; out(rb16); neg(0x80000000)
	set.zw rd16, wp3, 0xffff
	or.w rd16, wp2, 0xffff
	or.w rd16, wp1, 0x8000
	call [rb0, neg]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_uc_inc
	.type call_uc_inc,@function
call_uc_inc:                     ; out(rb16); uc_inc(0xFF)
	set.zw rd16, wp0, 0xff
	call [rb0, uc_inc]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_sc_inc
	.type call_sc_inc,@function
call_sc_inc:                     ; out(rb16); sc_inc(0x7F)
	set.zw rd16, wp0, 0x7f
	call [rb0, sc_inc]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_us_inc
	.type call_us_inc,@function
call_us_inc:                     ; out(rb16); us_inc(0xFFFF)
	set.zw rd16, wp0, 0xffff
	call [rb0, us_inc]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_ss_inc
	.type call_ss_inc,@function
call_ss_inc:                     ; out(rb16); ss_inc(0x7FFF)
	set.zw rd16, wp0, 0x7fff
	call [rb0, ss_inc]
	st.o rd8, [rb16, 0]
	ret rd0, 0

	.globl call_bnot
	.type call_bnot,@function
call_bnot:                       ; out(rb16); bnot(0)
	set.zw rd16, wp0, 0x0
	call [rb0, bnot]
	st.o rd8, [rb16, 0]
	ret rd0, 0
"""

MAIN = r"""
#include <stdio.h>
extern void call_addu(unsigned long *);
extern void call_add_s(unsigned long *);
extern void call_neg(unsigned long *);
extern void call_uc_inc(unsigned long *);
extern void call_sc_inc(unsigned long *);
extern void call_us_inc(unsigned long *);
extern void call_ss_inc(unsigned long *);
extern void call_bnot(unsigned long *);

static int bad;
static void check(const char *name, unsigned long got, unsigned long want) {
    int ok = got == want;
    printf("%-10s got=0x%016lx want=0x%016lx %s\n", name, got, want,
           ok ? "OK" : "FAIL");
    if (!ok) bad = 1;
}
int main(void) {
    unsigned long v;
    call_addu(&v);   check("addu", v, 0x0000000000000000UL);
    call_add_s(&v);  check("add_s", v, 0xfffffffffffffffeUL);
    call_neg(&v);    check("neg", v, 0xffffffff80000000UL);
    call_uc_inc(&v); check("uc_inc", v, 0x0000000000000000UL);
    call_sc_inc(&v); check("sc_inc", v, 0xffffffffffffff80UL);
    call_us_inc(&v); check("us_inc", v, 0x0000000000000000UL);
    call_ss_inc(&v); check("ss_inc", v, 0xffffffffffff8000UL);
    call_bnot(&v);   check("bnot", v, 0x0000000000000001UL);
    return bad;
}
"""

EXPECTED = {
    "addu": "0x0000000000000000",
    "add_s": "0xfffffffffffffffe",
    "neg": "0xffffffff80000000",
    "uc_inc": "0x0000000000000000",
    "sc_inc": "0xffffffffffffff80",
    "us_inc": "0x0000000000000000",
    "ss_inc": "0xffffffffffff8000",
    "bnot": "0x0000000000000001",
}

MUSL_INC = [
    "arch/dadao",
    "arch/generic",
    "obj/src/internal",
    "src/include",
    "src/internal",
    "obj/include",
    "include",
]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clang", default=str(ROOT / ".work/build/llvm/bin/clang"))
    ap.add_argument("--ldlld", default=str(ROOT / ".work/build/llvm/bin/ld.lld"))
    ap.add_argument("--qemu", default=str(ROOT / ".dadao/cross-toolchain/bin/qemu-dadao"))
    ap.add_argument("--musl", default=str(ROOT / ".work/source/musl"))
    ap.add_argument("--builtins", default=None,
                    help="compiler-rt builtins archive (default: clang -print-libgcc-file-name)")
    ap.add_argument("--work-dir", default="/tmp/opencode/LLVM-107t/tool")
    ap.add_argument("--expect-broken", action="store_true",
                    help="pre-fix mode: succeed only if the probe fails (i8/i16/i1 controls stay OK)")
    args = ap.parse_args()

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    (work / "ret_impl.c").write_text(IMPL)
    (work / "ret_consumer.s").write_text(CONSUMER)
    (work / "ret_main.c").write_text(MAIN)

    inc: list[str] = []
    for d in MUSL_INC:
        inc += ["-I", str(Path(args.musl) / d)]
    target = ["-target", "dadao-unknown-elf"]

    builtins = args.builtins
    if not builtins:
        q = run([args.clang, *target, "-print-libgcc-file-name"])
        if q.returncode != 0:
            print(f"FAIL clang -print-libgcc-file-name: {q.stderr.strip()}", file=sys.stderr)
            return 2
        builtins = q.stdout.strip()

    steps = [
        ("impl", [args.clang, *target, "-nostdinc", *inc, "-O2", "-c",
                  str(work / "ret_impl.c"), "-o", str(work / "impl.o")]),
        ("consumer", [args.clang, *target, "-c", str(work / "ret_consumer.s"),
                      "-o", str(work / "consumer.o")]),
        ("main", [args.clang, *target, "-nostdinc", *inc, "-O2", "-c",
                  str(work / "ret_main.c"), "-o", str(work / "main.o")]),
        ("link", [args.ldlld, "-o", str(work / "probe.elf"),
                  str(Path(args.musl) / "lib/crt1.o"), str(work / "main.o"),
                  str(work / "impl.o"), str(work / "consumer.o"),
                  "--start-group", str(Path(args.musl) / "lib/libc.a"), builtins,
                  "--end-group"]),
    ]
    for name, cmd in steps:
        p = run(cmd)
        if p.returncode != 0:
            print(f"[FAIL] {name}: rc={p.returncode}\n{p.stderr}", file=sys.stderr)
            return 2

    p = run([args.qemu, str(work / "probe.elf")], timeout=60)
    out = p.stdout + p.stderr
    print(out, end="")
    got = dict(re.findall(r"^(\w+)\s+got=(0x[0-9a-f]+)", out, re.MULTILINE))
    fails = [n for n, w in EXPECTED.items() if got.get(n) != w]

    if args.expect_broken:
        # The i8/i16/i1 controls must remain canonical even before the fix.
        broken = [n for n in ("addu", "neg") if got.get(n) != EXPECTED[n]]
        controls_ok = all(got.get(n) == EXPECTED[n] for n in ("uc_inc", "sc_inc", "us_inc", "ss_inc", "bnot"))
        ok = p.returncode != 0 and broken and controls_ok
        print(f"[{'OK' if ok else 'FAIL'}] expect-broken rc={p.returncode} broken={broken} controls_ok={controls_ok}")
        return 0 if ok else 1

    if p.returncode != 0 or fails:
        print(f"[FAIL] canonical probe: rc={p.returncode} mismatches={fails}")
        return 1
    print("[OK] all narrow returns are canonical (i1/i8/i16/i32, signed and unsigned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
