/* Copyright (C) 2026 DADAO-v5
 *
 * Hosted board-support shim for Embench-IoT under ``qemu-dadao`` (user mode).
 *
 * The Embench framework only requires three hooks (``support/support.h``):
 *
 *   initialise_board()  board bring-up        (before the timing window)
 *   start_trigger()     timing window starts
 *   stop_trigger()      timing window ends
 *
 * The existing DADAO board support (``examples/dadao/boardsupport.c``, part of
 * the embench-iot component patch set) emits its markers through the
 * *semihosting* ``SYS_WRITE0`` service.  That service does not exist in user
 * mode (``qemu-dadao`` exposes only the ``umon`` syscall table, see
 * TESTCASES-046t "已核事实"), so a hosted variant is needed.  This file is the
 * hosted variant: the same three hooks, each writing a short marker through
 * musl's ``write(2)``.
 *
 * The marker is inert with respect to the benchmark result: the verdict stays
 * Embench's own ``main`` return value (``return !correct``, i.e. guest exit 0
 * iff ``verify_benchmark`` accepted the result).  The markers only make the
 * hook invocations observable in the captured stdout.
 *
 * This file is *not* part of the component tree: ``components/embench-iot/``
 * and ``.work/source/embench-iot/`` stay untouched (TESTCASES-046t hard
 * constraints).
 */

#include <unistd.h>

#include <support.h>

static void
marker (const char *s, unsigned long n)
{
  /* write(2) is the one hosted service the run needs; a partial write cannot
   * occur for these short constant buffers on a pipe/file, but handle it so a
   * short write can never look like a missing marker. */
  while (n > 0)
    {
      long w = write (1, s, n);
      if (w <= 0)
	return;
      s += w;
      n -= (unsigned long) w;
    }
}

void
initialise_board (void)
{
  marker ("[board:init]\n", 13);
}

void
start_trigger (void)
{
  marker ("[board:start]\n", 14);
}

void
stop_trigger (void)
{
  marker ("[board:stop]\n", 13);
}
