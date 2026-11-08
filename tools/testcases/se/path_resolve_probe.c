/* SE path-resolution probe (INTEG-060t).
 *
 * The same source is compiled for the host (the reference: this really is
 * Linux) and for DADAO (musl + gem5 SE / qemu-user), so every assertion below
 * is a fact about the *guest* path rules with the host's own answer as the
 * oracle.  Paths are built from argv[1], the tree root as the run sees it
 * ("/" on an engine that maps the guest root, the host directory otherwise),
 * so the runs execute the identical sequence.
 *
 * Covered:
 *   A*  absolute path + non-AT_FDCWD dirfd: the dirfd must be ignored;
 *   R*  relative path + dirfd, ".." in the middle and at the front, and a cwd
 *       reached through chdir(2) (a redirected run must make it absolute);
 *   S*  trailing "/" on a directory and on a file, and ".." at the root;
 *   E*  empty path with and without AT_EMPTY_PATH, plus a NULL path;
 *   D*  invalid dirfd values.
 *
 * Every check prints "PASS/FAIL <id> expected=<e> actual=<a>" and the run ends
 * with "SUMMARY fails=N".  Raw syscall() is used so both libcs issue the same
 * request and the expected values stay the kernel's.  With a second argument
 * "guest-root" the run is the redirecting one, and the two root-clamp cases
 * that a non-chrooted host cannot express are emitted as "local:" assertions.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef AT_EMPTY_PATH
#define AT_EMPTY_PATH 0x1000
#endif
#ifndef AT_FDCWD
#define AT_FDCWD -100
#endif

static const char *root;
static int guest_root;
static int fails;

static void
report(const char *id, const char *expected, const char *fmt, ...)
{
    char actual[256];
    va_list ap;

    va_start(ap, fmt);
    vsnprintf(actual, sizeof(actual), fmt, ap);
    va_end(ap);
    if (strcmp(expected, actual) == 0) {
        printf("PASS %s expected=%s actual=%s\n", id, expected, actual);
    } else {
        printf("FAIL %s expected=%s actual=%s\n", id, expected, actual);
        ++fails;
    }
}

/* A path under the tree root; "/" as the root is the guest case. */
static const char *
under(const char *rel, char *buf, size_t size)
{
    snprintf(buf, size, "%s%s", root,
             *root == '/' && root[1] == '\0' ? "" : "/");
    strncat(buf, rel, size - strlen(buf) - 1);
    return buf;
}

/* Read up to 8 bytes of a freshly opened file, or "errno N". */
static void
content(const char *id, const char *expected, int dirfd, const char *path)
{
    char buf[9] = {0};
    int fd = syscall(SYS_openat, dirfd, path, O_RDONLY, 0);

    if (fd < 0) {
        report(id, expected, "errno %d", errno);
        return;
    }
    long n = syscall(SYS_read, fd, buf, 8);
    syscall(SYS_close, fd);
    report(id, expected, "%ld:%s", n, n > 0 ? buf : "");
}

static void
expect_errno(const char *id, int expected, long rc, int err)
{
    char want[32];

    snprintf(want, sizeof(want), "errno %d", expected);
    if (rc >= 0) {
        syscall(SYS_close, rc);
        report(id, want, "ok");
    } else {
        report(id, want, "errno %d", err);
    }
}

int
main(int argc, char **argv)
{
    char abs_abs[512];
    struct stat st_root, st_dotdot, st_fd, st_dir;
    int dirfd_a, dirfd_b, file_fd, dirfd_root, sub, up;
    long rc, rc2;

    if (argc < 2 || argc > 3 ||
        (argc == 3 && strcmp(argv[2], "guest-root") != 0)) {
        fprintf(stderr, "usage: %s <tree-root> [guest-root]\n", argv[0]);
        return 2;
    }
    root = argv[1];
    guest_root = argc == 3;
    if (syscall(SYS_chdir, root) < 0) {
        fprintf(stderr, "chdir %s: errno %d\n", root, errno);
        return 2;
    }

    /* The tree (built by the driver): a/f, a/sub/g, b/f, abs. */
    dirfd_a = syscall(SYS_openat, AT_FDCWD, "a", O_RDONLY | O_DIRECTORY, 0);
    dirfd_b = syscall(SYS_openat, AT_FDCWD, "b", O_RDONLY | O_DIRECTORY, 0);
    file_fd = syscall(SYS_openat, AT_FDCWD, "a/f", O_RDONLY, 0);
    if (dirfd_a < 0 || dirfd_b < 0 || file_fd < 0) {
        fprintf(stderr, "setup open failed: %d/%d/%d\n", dirfd_a, dirfd_b,
                file_fd);
        return 2;
    }

    /* Absolute paths: the dirfd must be ignored, whatever kind it is. */
    content("A1-abs-file-dirfd", "3:ABS", file_fd,
            under("abs", abs_abs, sizeof(abs_abs)));
    content("A2-abs-dir-dirfd", "3:ABS", dirfd_a,
            under("abs", abs_abs, sizeof(abs_abs)));
    content("A3-abs-dirfd-minus-one", "3:ABS", -1,
            under("abs", abs_abs, sizeof(abs_abs)));

    /* Relative paths + dirfd. */
    content("R1-rel-dirfd", "2:AF", dirfd_a, "f");
    content("R2-dotdot-front", "2:BF", dirfd_a, "../b/f");
    content("R3-dotdot-middle", "2:AF", dirfd_a, "sub/../f");
    content("R4-dotdot-deep", "2:AF", dirfd_a, "sub/../../a/f");
    content("R5-dotdot-dir", "2:BF", dirfd_b, "../b/../b/f");
    /* cwd-relative paths come from chdir(2): the cwd itself must become an
     * absolute guest name, or a redirected run resolves it outside the root. */
    rc = syscall(SYS_chdir, "a");
    if (rc < 0) {
        report("R6-chdir-relative", "2:AF", "errno %d", errno);
    } else {
        content("R6-chdir-relative", "2:AF", AT_FDCWD, "f");
        rc = syscall(SYS_chdir, "..");
        report("R7-chdir-dotdot", "0", "%ld", rc);
    }

    /* Trailing "/" is a directory requirement, and "/" names the root. */
    sub = syscall(SYS_openat, dirfd_a, "sub/", O_RDONLY | O_DIRECTORY, 0);
    if (sub < 0) {
        report("S1-dir-trailing-slash", "dir", "errno %d", errno);
    } else {
        rc = syscall(SYS_fstat, sub, &st_dir);
        syscall(SYS_close, sub);
        report("S1-dir-trailing-slash", "dir",
               rc == 0 && S_ISDIR(st_dir.st_mode) ? "dir" : "not-dir");
    }
    rc = syscall(SYS_openat, dirfd_a, "f/", O_RDONLY, 0);
    expect_errno("S2-file-trailing-slash", ENOTDIR, rc, errno);
    dirfd_root = syscall(SYS_openat, dirfd_a, "/", O_RDONLY | O_DIRECTORY, 0);
    if (dirfd_root < 0) {
        report("S3-root-dir", "dir", "errno %d", errno);
        report("S4-root-dotdot", "same", "errno %d", errno);
    } else {
        rc = syscall(SYS_fstat, dirfd_root, &st_root);
        report("S3-root-dir", "dir",
               rc == 0 && S_ISDIR(st_root.st_mode) ? "dir" : "not-dir");
        /* ".." at the root stays at the root: an escape would show another
         * device/inode pair. */
        up = syscall(SYS_openat, dirfd_root, "..", O_RDONLY | O_DIRECTORY, 0);
        if (up < 0) {
            report("S4-root-dotdot", "same", "errno %d", errno);
        } else {
            rc = syscall(SYS_fstat, up, &st_dotdot);
            syscall(SYS_close, up);
            report("S4-root-dotdot", "same",
                   rc == 0 && st_dotdot.st_dev == st_root.st_dev &&
                   st_dotdot.st_ino == st_root.st_ino ? "same" : "escaped");
        }
    }

    /* Leading ".." from the guest root is clamped there.  A host run has no
     * guest root, so this one is engine-local; the rule itself is the one S4
     * verifies on the host. */
    if (guest_root) {
        content("local:S5-root-relative-dotdot", "2:BF", AT_FDCWD, "../b/f");
    } else {
        printf("SKIP local:S5-root-relative-dotdot (host cwd is not a guest "
               "root)\n");
    }

    /* Empty path: no AT_EMPTY_PATH names nothing, the flag names the fd. */
    rc = syscall(SYS_openat, dirfd_a, "", O_RDONLY, 0);
    expect_errno("E1-empty-openat", ENOENT, rc, errno);
    rc = syscall(SYS_newfstatat, dirfd_a, "", &st_dir, 0);
    expect_errno("E2-empty-fstatat", ENOENT, rc, errno);
    rc = syscall(SYS_newfstatat, file_fd, "", &st_fd, AT_EMPTY_PATH);
    report("E3-empty-at-empty-path", "0", "%ld", rc);
    rc2 = syscall(SYS_fstat, file_fd, &st_dir);
    report("E4-at-empty-path-is-the-fd", "same",
           rc == 0 && rc2 == 0 && st_fd.st_ino == st_dir.st_ino
               ? "same" : "other");
    rc = syscall(SYS_newfstatat, file_fd, NULL, &st_fd, AT_EMPTY_PATH);
    expect_errno("E5-null-at-empty-path", EFAULT, rc, errno);

    /* Invalid dirfds. */
    rc = syscall(SYS_openat, -1, "f", O_RDONLY, 0);
    expect_errno("D1-dirfd-minus-one-rel", EBADF, rc, errno);
    rc = syscall(SYS_openat, file_fd, "x", O_RDONLY, 0);
    expect_errno("D2-dirfd-file-rel", ENOTDIR, rc, errno);
    rc = syscall(SYS_openat, 9999, "f", O_RDONLY, 0);
    expect_errno("D3-dirfd-unused-number", EBADF, rc, errno);

    syscall(SYS_close, dirfd_a);
    syscall(SYS_close, dirfd_b);
    syscall(SYS_close, file_fd);
    printf("SUMMARY fails=%d\n", fails);
    return fails == 0 ? 0 : 1;
}
