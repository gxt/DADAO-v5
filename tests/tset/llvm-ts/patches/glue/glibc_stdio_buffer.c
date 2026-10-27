/* TESTCASES-081t test glue: reproduce glibc's stdout buffer size.
 *
 * ClamAV's upstream reference (clamscan.reference_output.big-endian) is one
 * interleaved stdout+stderr document produced by upstream's RunSafely, which
 * points both streams at the same file.  cli_dbgmsg() uses puts() (stdout),
 * while the database-age warnings go to stderr.  glibc allocates stdio's
 * buffer from the output file's st_blksize (4096 here) and therefore flushes
 * the first stdout block at exit -- after the stderr warnings; musl uses its
 * fixed 1024-byte BUFSIZ and flushes the first stdout block before them,
 * which moves exactly one line ("Initializing the engine ...") to the top.
 * The bytes and the line multiset are identical either way.
 *
 * A constructor requests glibc's 4096-byte buffer.  musl's setvbuf() only
 * honours the size when the caller supplies the buffer, hence the static
 * array.  This changes buffering only; it does not touch the program, the
 * oracle or the comparison (still byte-exact).
 */
#include <stdio.h>

static char buffer[4096];

__attribute__((constructor))
static void dadao_glibc_stdio_buffer(void)
{
    setvbuf(stdout, buffer, _IOFBF, sizeof buffer);
}
