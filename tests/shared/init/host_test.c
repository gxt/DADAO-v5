/*
 * host_test.c — host-side unit test driver for init.c (`-DHOST_TEST`).
 *
 * The target init ELF cannot run before the K1 kernel exists, so the *error
 * logic* of init.c is exercised here: the three kernel calls (write, getpid,
 * brk) are replaced by the shims below, whose behaviour is selected by the
 * scenario name on the command line.  Every scenario runs in its own process,
 * so the process exit status is exactly the code init.c chose:
 *
 *   ok                rc 0   benign shims (real host write/getpid/brk)
 *   ok_short          rc 0   write(2) returns 5 bytes per call — the retry
 *                            loop in init_write_all() must still emit the
 *                            whole banner
 *   write_fail        rc 2   first write to fd 1 fails (EIO); fd 2 still works
 *   pid_zero          rc 3   getpid() returns 0
 *   brk_read_fail     rc 4   brk(0) (the initial read) fails
 *   brk_grow_fail     rc 4   brk(cur + 65536) fails
 *   brk_recheck_fail  rc 4   grow "succeeds", brk(0) re-read disagrees
 *
 * Build (from the repository root):
 *   cc -DHOST_TEST -O1 -Wall -Wextra tests/shared/init/init.c \
 *      tests/shared/init/host_test.c -o <tmp>/host_test
 * Exit status: the init exit code for the chosen scenario (0/2/3/4);
 * 125 = bad usage, 126 = unknown scenario.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>

#define HOST_TEST_WRITE_CHUNK 5UL

static const char *scenario = "ok";
static int write_calls;
static int brk_zero_calls;

long host_test_write(int fd, const void *buf, unsigned long len)
{
	ssize_t n;

	if (strcmp(scenario, "write_fail") == 0 && fd == 1 && write_calls++ == 0) {
		errno = EIO;
		return -1;
	}
	if (strcmp(scenario, "ok_short") == 0 && len > HOST_TEST_WRITE_CHUNK)
		len = HOST_TEST_WRITE_CHUNK;
	n = write(fd, buf, (size_t)len);
	if (n < 0)
		return -1;
	return (long)n;
}

long host_test_getpid(void)
{
	if (strcmp(scenario, "pid_zero") == 0)
		return 0;
	return (long)getpid();
}

long host_test_brk(unsigned long addr)
{
	if (strcmp(scenario, "brk_read_fail") == 0)
		return -ENOMEM;
	if (strcmp(scenario, "brk_grow_fail") == 0 && addr != 0UL)
		return -ENOMEM;
	if (strcmp(scenario, "brk_recheck_fail") == 0 && addr == 0UL) {
		/* First brk(0) is real, the re-read reports a different address. */
		if (brk_zero_calls++ > 0)
			return 1;
	}
	return (long)syscall(SYS_brk, (void *)addr);
}

int host_test_errno(void)
{
	return errno;
}

int init_main(void);

static void usage(const char *argv0)
{
	fprintf(stderr,
		"usage: %s <scenario>\n"
		"  ok | ok_short | write_fail | pid_zero |\n"
		"  brk_read_fail | brk_grow_fail | brk_recheck_fail\n",
		argv0);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		usage(argv[0]);
		return 125;
	}
	scenario = argv[1];
	if (strcmp(scenario, "ok") != 0 && strcmp(scenario, "ok_short") != 0 &&
	    strcmp(scenario, "write_fail") != 0 && strcmp(scenario, "pid_zero") != 0 &&
	    strcmp(scenario, "brk_read_fail") != 0 &&
	    strcmp(scenario, "brk_grow_fail") != 0 &&
	    strcmp(scenario, "brk_recheck_fail") != 0) {
		fprintf(stderr, "host_test: unknown scenario '%s'\n", scenario);
		return 126;
	}
	return init_main();
}
