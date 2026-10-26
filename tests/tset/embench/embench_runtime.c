/* embench_runtime.c — minimal freestanding runtime gap for the DADAO Embench
 * port (TESTCASES-039t).
 *
 * Embench-iot is built freestanding, with no libc.  The `mem*` primitives are
 * already provided out-of-line by tests/scripts/dadao_mem_runtime.ll (reused,
 * unchanged); this TU supplies the remaining symbols the benchmark set
 * references:
 *
 *   string : strlen, strchr, strcmp
 *   ctype  : tolower, isspace, isdigit, isxdigit
 *   math   : sqrt (double)
 *   stdlib : abort
 *
 * All ASCII/plain implementations — no libc, no locale tables, no libm.  The
 * DADAO scalar model is big-endian LP64 (contract-abi.md); the code is
 * endianness-neutral.
 *
 * Build: clang -target dadao-unknown-elf -O2 -ffreestanding -fno-builtin -c
 */

#include <stddef.h>

/* ------------------------------------------------------------------ string */

size_t
strlen (const char *s)
{
  const char *p = s;
  while (*p)
    p++;
  return (size_t) (p - s);
}

char *
strchr (const char *s, int c)
{
  char ch = (char) c;
  for (;;)
    {
      if (*s == ch)
	return (char *) s;
      if (*s == '\0')
	return NULL;
      s++;
    }
}

int
strcmp (const char *a, const char *b)
{
  while (*a && *a == *b)
    {
      a++;
      b++;
    }
  return (int) (unsigned char) *a - (int) (unsigned char) *b;
}

/* ------------------------------------------------------------------- ctype */

int
tolower (int c)
{
  if (c >= 'A' && c <= 'Z')
    return c + ('a' - 'A');
  return c;
}

int
isspace (int c)
{
  return (c == ' ' || c == '\t' || c == '\n' || c == '\v' || c == '\f'
	  || c == '\r');
}

int
isdigit (int c)
{
  return (c >= '0' && c <= '9');
}

int
isxdigit (int c)
{
  return (isdigit (c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'));
}

/* -------------------------------------------------------------------- math */

/* memcpy is used only as a compiler-recognised 8-byte load/store (type pun);
 * its out-of-line definition lives in tests/scripts/dadao_mem_runtime.ll.  The
 * DADAO backend cannot select a register-register `bitcast f64<->i64`, so the
 * bit pattern is moved through memory instead. */
void *memcpy (void *dst, const void *src, size_t n);

/* sqrt(x) for x >= 0, IEEE-754 double, no libm.
 *
 * Seed the exponent by halving the stored bit pattern (a standard bit trick
 * that lands within a few bits of the true root), then refine with
 * Newton-Raphson (r <- (r + x/r)/2), which doubles the number of correct bits
 * per step.  Six iterations give full double precision.  The bit trick works
 * on any endianness because it operates on the integer *value* of the bit
 * pattern (moved via memcpy), not on memory byte order.
 */
double
sqrt (double x)
{
  unsigned long u;
  double r;

  if (!(x > 0.0))
    return x == 0.0 ? x : 0.0;	/* +0/-0 -> 0; negative/NaN -> 0 */

  memcpy (&u, &x, sizeof (u));
  u = (u >> 1) + 0x1ff8000000000000UL;
  memcpy (&r, &u, sizeof (r));

  r = 0.5 * (r + x / r);
  r = 0.5 * (r + x / r);
  r = 0.5 * (r + x / r);
  r = 0.5 * (r + x / r);
  r = 0.5 * (r + x / r);
  r = 0.5 * (r + x / r);
  return r;
}

/* ------------------------------------------------------------------ stdlib */

/* `abort` is referenced only by nettle-sha256's unreachable `default` branch.
 * Halt in a loop (fail-closed) so a real breach shows up as a harness timeout
 * rather than silent success.
 */
void
abort (void)
{
  for (;;)
    ;
}
