/* Minimal freestanding <ctype.h> for the DADAO Embench port (TESTCASES-039t).
 *
 * Declares the subset of <ctype.h> used by Embench-iot; implementations are in
 * tests/scripts/embench_runtime.c (no libc, no locale table).
 */
#ifndef _DADAO_CTYPE_H
#define _DADAO_CTYPE_H

int tolower (int c);
int isspace (int c);
int isdigit (int c);
int isxdigit (int c);

#endif /* _DADAO_CTYPE_H */
