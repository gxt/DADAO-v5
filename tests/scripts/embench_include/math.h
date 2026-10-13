/* Minimal freestanding <math.h> for the DADAO Embench port (TESTCASES-039t).
 *
 * Only `sqrt` (double) is referenced by the benchmark set (wikisort).  The
 * implementation is in tests/scripts/embench_runtime.c (no libm).
 */
#ifndef _DADAO_MATH_H
#define _DADAO_MATH_H

double sqrt (double x);

#endif /* _DADAO_MATH_H */
