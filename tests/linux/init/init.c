/*
 * init.c — DADAO Linux M14 K0 MVP init (static musl user program).
 *
 * Purpose: the first user program the K1 kernel must be able to run from the
 * built-in initramfs.  It exercises exactly the four syscalls the K0 MVP is
 * scoped to (`.tao/contracts/contract-syscall.md` §1.1/§3/§4; syscall numbers
 * come from the locked kernel `scripts/syscall.tbl`, never from a literal
 * here — the C code uses the musl headers' `SYS_*` macros):
 *
 *   getpid      (172)  pid must be > 0
 *   write       ( 64)  banner to fd 1 (partial writes are retried), errors
 *                      and diagnostics to fd 2 (best effort)
 *   brk         (214)  read the break, grow it by one DADAO page (64 KiB),
 *                      read it back to confirm
 *   exit_group  ( 94)  normal exit 0
 *
 * Exit codes (deliberately distinguishable so the kernel-side smoke can tell
 * which step failed):
 *
 *   0  success
 *   2  write(2) failed on fd 1
 *   3  getpid(2) returned <= 0
 *   4  brk(2) failed (read, grow or re-check)
 *
 * Two builds come out of this one source:
 *
 *   * target build (default): linked with musl `crt1.o` + `libc.a` by
 *     `tools/linux/make_initramfs.py`; runs under the Linux kernel.
 *   * host build (`-DHOST_TEST`, driven by `tests/linux/init/host_test.c`):
 *     the three kernel calls are replaced by injectable shims so the error
 *     logic is unit-testable on the host build machine (the target ELF cannot
 *     run before the kernel exists).  This branch never reaches the ELF.
 */

#ifdef HOST_TEST

/* Host-unit-test shims (tests/linux/init/host_test.c).  They return the same
 * raw shape as the kernel calls: byte count / -1, pid / <= 0, break address /
 * negative errno. */
long host_test_write(int fd, const void *buf, unsigned long len);
long host_test_getpid(void);
long host_test_brk(unsigned long addr);
int host_test_errno(void);

#define INIT_WRITE(fd, buf, len) host_test_write((fd), (buf), (len))
#define INIT_GETPID() host_test_getpid()
#define INIT_BRK(addr) host_test_brk(addr)
#define INIT_ERRNO() host_test_errno()
#define INIT_EINTR 4 /* arbitrary non-zero: the host shim never sets it */

#else /* target build: the real musl / kernel surface */

#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>

#define INIT_WRITE(fd, buf, len) ((long)write((fd), (buf), (len)))
#define INIT_GETPID() ((long)getpid())
#define INIT_BRK(addr) ((long)syscall(SYS_brk, (void *)(addr)))
#define INIT_ERRNO() (errno)
#define INIT_EINTR EINTR

#endif

#define INIT_PAGE_SIZE 65536UL /* DADAO ordinary page: 64 KiB */
#define INIT_BRK_GROW INIT_PAGE_SIZE

#define INIT_EXIT_OK 0
#define INIT_EXIT_WRITE 2
#define INIT_EXIT_PID 3
#define INIT_EXIT_BRK 4

static unsigned long init_strlen(const char *s)
{
	unsigned long n = 0;
	while (s[n] != '\0')
		n++;
	return n;
}

/* Append `s` to buf at off; the banner buffer is sized for the widest pid. */
static unsigned long init_put_str(char *buf, unsigned long off, const char *s)
{
	while (*s != '\0')
		buf[off++] = *s++;
	return off;
}

static unsigned long init_put_dec(char *buf, unsigned long off, unsigned long v)
{
	char digits[20];
	unsigned long n = 0;

	do {
		digits[n++] = (char)('0' + (int)(v % 10UL));
		v /= 10UL;
	} while (v != 0UL);
	while (n != 0UL)
		buf[off++] = digits[--n];
	return off;
}

/* Write the whole buffer to `fd`, retrying partial writes and EINTR. */
static int init_write_all(int fd, const char *buf, unsigned long len)
{
	while (len != 0UL) {
		long n = INIT_WRITE(fd, buf, len);

		if (n < 0) {
			if (INIT_ERRNO() == INIT_EINTR)
				continue;
			return -1;
		}
		if (n == 0)
			return -1;
		buf += n;
		len -= (unsigned long)n;
	}
	return 0;
}

/* Best-effort diagnostic on fd 2, then return the step's exit code. */
static int init_fail(int code, const char *msg)
{
	(void)init_write_all(2, msg, init_strlen(msg));
	return code;
}

/* Banner: "init: pid=<n>\n" — built by hand (no stdio in the MVP). */
static unsigned long init_format_banner(char *buf, unsigned long pid)
{
	unsigned long off = 0;

	off = init_put_str(buf, off, "init: pid=");
	off = init_put_dec(buf, off, pid);
	off = init_put_str(buf, off, "\n");
	return off;
}

/*
 * Body of init.  Returns the process exit code before calling anything that
 * does not return; the target `main` wraps it with _Exit() (= exit_group).
 */
int init_main(void)
{
	static const char brk_ok[] = "init: brk +65536 ok\n";
	char banner[64];
	unsigned long len;
	long pid, cur, want, got, chk;

	pid = INIT_GETPID();
	if (pid <= 0)
		return init_fail(INIT_EXIT_PID, "init: getpid failed\n");

	len = init_format_banner(banner, (unsigned long)pid);
	if (init_write_all(1, banner, len) != 0)
		return init_fail(INIT_EXIT_WRITE, "init: write fd1 failed\n");

	cur = INIT_BRK(0UL);
	if (cur < 0)
		return init_fail(INIT_EXIT_BRK, "init: brk read failed\n");

	want = cur + (long)INIT_BRK_GROW;
	got = INIT_BRK((unsigned long)want);
	if (got < want)
		return init_fail(INIT_EXIT_BRK, "init: brk grow failed\n");

	chk = INIT_BRK(0UL);
	if (chk != got)
		return init_fail(INIT_EXIT_BRK, "init: brk recheck failed\n");

	if (init_write_all(1, brk_ok, sizeof(brk_ok) - 1) != 0)
		return init_fail(INIT_EXIT_WRITE, "init: write fd1 failed\n");

	return INIT_EXIT_OK;
}

#ifndef HOST_TEST
int main(void)
{
	_Exit(init_main());
}
#endif
