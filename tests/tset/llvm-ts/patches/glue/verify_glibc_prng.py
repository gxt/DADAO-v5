#!/usr/bin/env python3
"""Verify `glibc_prng.c` against the host glibc's own `random()`.

Independent oracle for the glue: the host's libc IS the generator upstream's
reference outputs were produced with (host build of the unmodified corpus
reproduces both references).  Two binaries are built from one probe source:

  * ``probe_glibc``  -- linked without the glue, so `random()` is the host
    libc's;
  * ``probe_glue``   -- linked with ``glibc_prng.c`` first, so its definitions
    win and the rest of the probe is identical.

Their outputs must be byte-identical for the unseeded default state and for
every seed in ``SEEDS`` (100 draws each).  Any divergence exits non-zero and
prints the first differing index.

Usage: verify_glibc_prng.py [--keep DIR]   (default temp dir: mkdtemp)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

SEEDS = (0, 1, 2, 7, 12345, 2147483647, 4294967295)
DRAWS = 100

GLUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glibc_prng.c")

PROBE = r"""
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	int i;

	(void)argc;
	/* Unseeded default state, in a fresh process (glibc: == srandom(1)). */
	printf("default:");
	for (i = 0; i < %(draws)d; i++)
		printf(" %%ld", (long)random());
	printf("\n");

	for (i = 1; i < argc; i++) {
		unsigned long seed = strtoul(argv[i], 0, 10);
		int j;

		srandom((unsigned int)seed);
		printf("seed %%lu:", seed);
		for (j = 0; j < %(draws)d; j++)
			printf(" %%ld", (long)random());
		printf("\n");
	}
	return 0;
}
""" % dict(draws=DRAWS)


def build(cc, src, out, extra):
    cmd = [cc, "-O2", "-o", out, src] + list(extra)
    rc = subprocess.call(cmd)
    if rc != 0:
        sys.exit(f"verify_glibc_prng: build failed rc={rc}: {' '.join(cmd)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", default="", help="work dir (default: mkdtemp)")
    args = ap.parse_args()
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        print("verify_glibc_prng: no host cc/gcc", file=sys.stderr)
        return 2
    work = args.keep or tempfile.mkdtemp(prefix="verify-glibc-prng-")
    os.makedirs(work, exist_ok=True)
    src = os.path.join(work, "probe.c")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(PROBE)
    build(cc, src, os.path.join(work, "probe_glibc"), [])
    build(cc, src, os.path.join(work, "probe_glue"), [GLUE])
    argv = [str(s) for s in SEEDS]
    a = subprocess.run([os.path.join(work, "probe_glibc")] + argv,
                       capture_output=True)
    b = subprocess.run([os.path.join(work, "probe_glue")] + argv,
                       capture_output=True)
    ok = True
    if a.returncode != 0 or b.returncode != 0:
        print(f"verify_glibc_prng: probe rc {a.returncode}/{b.returncode}",
              file=sys.stderr)
        return 1
    la = a.stdout.decode().splitlines()
    lb = b.stdout.decode().splitlines()
    if len(la) != len(lb):
        print(f"verify_glibc_prng: line count {len(la)} != {len(lb)}",
              file=sys.stderr)
        return 1
    for line_a, line_b in zip(la, lb):
        if line_a == line_b:
            print(f"  OK   {line_a.split(':')[0]}: {DRAWS} draws identical")
            continue
        ok = False
        va = line_a.split(":")[1].split()
        vb = line_b.split(":")[1].split()
        first = next((i for i, (x, y) in enumerate(zip(va, vb)) if x != y),
                     min(len(va), len(vb)))
        print(f"  FAIL {line_a.split(':')[0]}: first difference at draw "
              f"{first}: glibc={va[first] if first < len(va) else '(none)'} "
              f"glue={vb[first] if first < len(vb) else '(none)'}")
    print(f"verify_glibc_prng: {'PASS' if ok else 'FAIL'} "
          f"({len(la)} sequences, {DRAWS} draws each)")
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
