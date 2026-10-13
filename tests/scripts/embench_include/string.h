/* Minimal freestanding <string.h> for the DADAO Embench port (TESTCASES-039t).
 *
 * No libc: this header only declares the small subset of <string.h> used by
 * Embench-iot.  The implementations live in tests/scripts/dadao_mem_runtime.ll
 * (mem*) and tests/scripts/embench_runtime.c (str*).
 */
#ifndef _DADAO_STRING_H
#define _DADAO_STRING_H

#include <stddef.h>

void *memcpy (void *dst, const void *src, size_t n);
void *memmove (void *dst, const void *src, size_t n);
void *memset (void *dst, int c, size_t n);
int memcmp (const void *a, const void *b, size_t n);

size_t strlen (const char *s);
char *strchr (const char *s, int c);
int strcmp (const char *a, const char *b);

#endif /* _DADAO_STRING_H */
