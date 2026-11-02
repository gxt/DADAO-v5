/* Minimal freestanding <stdio.h> for the DADAO Embench port (TESTCASES-039t).
 *
 * No stdio is available (freestanding).  Every printf/puts call in Embench-iot
 * is inside a debug macro (DEBUG/ROUNDS/DO_TRACING/SLRE_DEBUG) that the default
 * build never enables, so these declarations are never referenced.  The header
 * exists only so sources that `#include <stdio.h>` compile.
 */
#ifndef _DADAO_STDIO_H
#define _DADAO_STDIO_H

#include <stddef.h>

int printf (const char *fmt, ...);
int puts (const char *s);
int putchar (int c);

#endif /* _DADAO_STDIO_H */
