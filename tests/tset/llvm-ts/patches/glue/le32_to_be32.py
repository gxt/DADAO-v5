#!/usr/bin/env python3
"""Rewrite a little-endian u32 word stream as the same words in big endian.

Test glue for `MultiSource/Benchmarks/VersaBench/8b10b` (TESTCASES-080t).

The corpus file ``input.txt`` is a **little-endian** u32 word stream (calc.c's
own header describes the words it was generated from), while DADAO is a
big-endian target (ADR-0003 D1).  ``testbench.c:59`` does

    fread(theInputArray, numberOfWords, sizeof(unsigned int), inputFile);

i.e. it reads host-order ``unsigned int`` words, so on a big-endian target the
same bytes decode as byte-swapped words.  ``calc.c:170-173`` then indexes
``lookupTable5B[index5]``/``lookupTable3B[index3]`` with
``index5 = ((w>>3)&0x1f)|(k<<5)``, ``index3 = (w&7)|(k<<3)``, ``k = w>>8``; for
byte-swapped words ``k`` reaches 0x380000 and the access leaves the tables
(guest SIGSEGV, ISS-266).

This script performs the *explicit, auditable* conversion the other way: it
rewrites the per-case **run copy** of the file so that a big-endian ``fread``
yields the words the corpus author wrote.  The corpus itself is never touched
(patchless), the target's byte order is never changed, and the conversion is a
pure byte swap: word ``i`` after the rewrite is the same value as word ``i``
before it.

Usage: le32_to_be32.py <file>

Prints one JSON line on success:
  {"file": ..., "words": N, "sha256_before": ..., "sha256_after": ...}
Exit status: 0 = converted and verified, 1 = refused (message on stderr).
"""

import hashlib
import json
import sys


def fail(msg):
    sys.stderr.write(f"le32_to_be32: {msg}\n")
    return 1


def main(argv):
    if len(argv) != 2:
        return fail("usage: le32_to_be32.py <file>")
    path = argv[1]
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        return fail(f"cannot read {path}: {exc}")
    if len(raw) == 0:
        return fail(f"{path} is empty")
    if len(raw) % 4:
        return fail(f"{path} size {len(raw)} B is not a whole number of u32 "
                    f"words")
    words = [int.from_bytes(raw[i:i + 4], "little")
             for i in range(0, len(raw), 4)]
    converted = b"".join(w.to_bytes(4, "big") for w in words)
    if len(converted) != len(raw):
        return fail("internal: converted size changed")
    try:
        with open(path, "wb") as fh:
            fh.write(converted)
    except OSError as exc:
        return fail(f"cannot write {path}: {exc}")
    # Read back and verify: a big-endian read of the rewritten file must give
    # exactly the words a little-endian read of the original gave.
    with open(path, "rb") as fh:
        back = fh.read()
    if back != converted:
        return fail(f"{path}: read-back differs from what was written")
    back_words = [int.from_bytes(back[i:i + 4], "big")
                  for i in range(0, len(back), 4)]
    if back_words != words:
        first = next(i for i, (a, b) in enumerate(zip(words, back_words))
                     if a != b)
        return fail(f"{path}: word {first} changed "
                    f"({words[first]:#x} -> {back_words[first]:#x})")
    print(json.dumps(dict(
        file=path, words=len(words),
        sha256_before=hashlib.sha256(raw).hexdigest(),
        sha256_after=hashlib.sha256(back).hexdigest())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
