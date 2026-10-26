/* Minimal freestanding <assert.h> for the DADAO Embench port (TESTCASES-039t).
 *
 * Embench does not use the standard assert() (it uses the `assert_beebs` macro
 * from support/beebsc.h); this header only has to exist because some sources
 * `#include <assert.h>`.  The macro forwards to abort() to stay standards
 * shaped.
 */
#ifndef _DADAO_ASSERT_H
#define _DADAO_ASSERT_H

void abort (void);

#ifdef NDEBUG
#define assert(expr) ((void)0)
#else
#define assert(expr) ((expr) ? (void)0 : abort ())
#endif

#endif /* _DADAO_ASSERT_H */
