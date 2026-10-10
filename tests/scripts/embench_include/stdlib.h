/* Minimal freestanding <stdlib.h> for the DADAO Embench port (TESTCASES-039t).
 *
 * Embench-iot uses no libc allocator (BEEBS ships its own bump allocator in
 * support/beebsc.c) and no rand/atoi.  The only symbol actually referenced is
 * `abort` (nettle-sha256, an unreachable default branch); it is provided by
 * tests/scripts/embench_runtime.c.
 */
#ifndef _DADAO_STDLIB_H
#define _DADAO_STDLIB_H

#include <stddef.h>

void abort (void);

#endif /* _DADAO_STDLIB_H */
