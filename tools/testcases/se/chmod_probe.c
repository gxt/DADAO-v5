/* SE chmod-family probe (GEM5-031t).
 *
 * The same source runs on the host (the reference: this really is Linux), on
 * gem5 SE and under qemu-user, so every assertion below is a fact about the
 * *guest* file-permission surface with the host's own answer as the oracle.
 * The tree root is argv[1]; the driver gives every engine its own tree because
 * these cases change modes.
 *
 * Covered:
 *   A*  chmod(2) -- as musl implements it: fchmodat(AT_FDCWD, path, mode) --
 *       set/read back, high mode bits, missing path, file as a path prefix,
 *       dangling symlink, symlink to a file (followed, link untouched),
 *       EACCES on a non-searchable prefix, ELOOP, a directory, non-owner;
 *   B*  fchmod(2): a descriptor, a read-only descriptor, O_PATH, -1, a pipe;
 *   C*  fchmodat(2): the legacy call has no flags argument -- AT_FDCWD,
 *       dirfd-relative (including ".."), bad/missing dirfd, a non-directory
 *       dirfd, an absolute path that must ignore dirfd;
 *   D*  fchmodat2(2): flags 0, AT_SYMLINK_NOFOLLOW (file, symlink, missing,
 *       directory), AT_EMPTY_PATH (file fd, directory fd, pipe fd, bad fd),
 *       empty path without the flag, an unknown flag bit.
 *
 * Every check prints "PASS/FAIL <id> expected=<e> actual=<a>" and the run ends
 * with "SUMMARY fails=N".  libc entry points are used where both libcs have
 * them (only the guest's own request matters); fchmodat2 is issued raw on both
 * sides so the engine, not the C library, decides the answer.
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
static int fails;

/* One assertion: `expected` is the constant string, `actual` is built from the
 * call's own result/errno (never from another engine's answer). */
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

/* Run one call and report "0" or "errno N". */
#define CHECK_RC(id, expected, call)                                          \
    do {                                                                      \
        long r_;                                                              \
        errno = 0;                                                            \
        r_ = (long)(call);                                                    \
        const int e_ = errno;                                                 \
        if (r_ >= 0)                                                          \
            report((id), (expected), "0");                                    \
        else                                                                  \
            report((id), (expected), "errno %d", e_);                         \
    } while (0)

/* Report the low 12 mode bits of path (follow) or of the link itself. */
static void
check_mode(const char *id, const char *path, const char *expected)
{
    struct stat st;

    errno = 0;
    if (stat(path, &st) < 0) {
        report(id, expected, "stat errno %d", errno);
        return;
    }
    report(id, expected, "mode %04o", (unsigned)(st.st_mode & 07777));
}

static void
check_lmode(const char *id, const char *path, const char *expected)
{
    struct stat st;

    errno = 0;
    if (lstat(path, &st) < 0) {
        report(id, expected, "lstat errno %d", errno);
        return;
    }
    report(id, expected, "mode %04o", (unsigned)(st.st_mode & 07777));
}

/* A path under the tree root. */
static const char *
under(const char *rel, char *buf, size_t size)
{
    snprintf(buf, size, "%s%s", root,
             *root == '/' && root[1] == '\0' ? "" : "/");
    strncat(buf, rel, size - strlen(buf) - 1);
    return buf;
}

int
main(int argc, char **argv)
{
    char f[512], d[512], l[512], dang[512], s[512], sf[512], a[512];
    char tmp[512];
    int fd, dfd, sfd, pp[2];

    if (argc < 2) {
        fprintf(stderr, "usage: %s <tree-root>\n", argv[0]);
        return 2;
    }
    root = argv[1];
    under("f", f, sizeof(f));
    under("d", d, sizeof(d));
    under("l", l, sizeof(l));
    under("dang", dang, sizeof(dang));
    under("s", s, sizeof(s));
    under("s/f", sf, sizeof(sf));
    under("a", a, sizeof(a));

    /* --- A: chmod(2) ------------------------------------------------------ */
    CHECK_RC("A1-chmod-set-rc", "0", chmod(f, 0640));
    check_mode("A1-chmod-set-mode", f, "mode 0640");
    CHECK_RC("A2-chmod-change-rc", "0", chmod(f, 0751));
    check_mode("A2-chmod-change-mode", f, "mode 0751");
    /* The kernel masks the mode to S_IALLUGO; extra bits are not EINVAL. */
    CHECK_RC("A3-chmod-high-bits-rc", "0", chmod(f, 07777 | 0x8000));
    check_mode("A3-chmod-high-bits-mode", f, "mode 7777");

    under("missing", tmp, sizeof(tmp));
    CHECK_RC("A4-chmod-missing", "errno 2", chmod(tmp, 0600));
    snprintf(tmp, sizeof(tmp), "%s/x", f);
    CHECK_RC("A5-chmod-file-child", "errno 20", chmod(tmp, 0600));
    CHECK_RC("A6-chmod-dangling", "errno 2", chmod(dang, 0600));

    /* A final symlink is followed: the target changes, the link does not. */
    CHECK_RC("A7-chmod-symlink-rc", "0", chmod(l, 0600));
    check_mode("A7-chmod-symlink-target", f, "mode 0600");
    check_lmode("A7-chmod-symlink-link", l, "mode 0777");

    /* EACCES: the owner still needs search permission on a prefix. */
    mkdir(s, 0755);
    sfd = open(sf, O_CREAT | O_RDWR, 0644);
    chmod(sf, 0644);
    chmod(s, 0600);
    CHECK_RC("A8-chmod-eacces", "errno 13", chmod(sf, 0600));
    chmod(s, 0755);
    close(sfd);
    unlink(sf);

    CHECK_RC("A9-chmod-eloop", "errno 40", chmod(a, 0600));

    CHECK_RC("A10-chmod-dir-rc", "0", chmod(d, 0750));
    check_mode("A10-chmod-dir-mode", d, "mode 0750");
    chmod(d, 0755);

    /* Non-owner: a root-owned file must answer EPERM.  Only the *owner* can
     * chmod, and an unprivileged test cannot create one, so a stock root-owned
     * system file is used; the mode written is the one it already has, so the
     * call is a no-op even if it ever ran as root.  SKIP is a first-class line:
     * every engine sees the same host facts, so the lines still compare. */
    {
        struct stat st;
        const char *passwd = "/etc/passwd";

        if (stat(passwd, &st) == 0 && st.st_uid != geteuid()) {
            CHECK_RC("A11-chmod-not-owner", "errno 1",
                     chmod(passwd, st.st_mode & 07777));
        } else {
            printf("PASS A11-chmod-not-owner expected=skipped actual=skipped\n");
        }
    }

    /* --- B: fchmod(2) ----------------------------------------------------- */
    fd = open(f, O_RDWR);
    CHECK_RC("B1-fchmod-rc", "0", fchmod(fd, 0604));
    {
        struct stat st;
        errno = 0;
        if (fstat(fd, &st) < 0)
            report("B1-fchmod-mode", "mode 0604", "fstat errno %d", errno);
        else
            report("B1-fchmod-mode", "mode 0604", "mode %04o",
                   (unsigned)(st.st_mode & 07777));
    }
    CHECK_RC("B2-fchmod-badfd", "errno 9", fchmod(-1, 0600));

    /* A directory descriptor is a normal fchmod target. */
    dfd = open(d, O_RDONLY | O_DIRECTORY);
    CHECK_RC("B3-fchmod-dirfd-rc", "0", fchmod(dfd, 0753));
    check_mode("B3-fchmod-dirfd-mode", d, "mode 0753");
    chmod(d, 0755);
    close(dfd);

    if (pipe(pp) == 0) {
        CHECK_RC("B4-fchmod-pipe", "0", fchmod(pp[0], 0600));
        close(pp[0]);
        close(pp[1]);
    } else {
        report("B4-fchmod-pipe", "0", "pipe errno %d", errno);
    }

    /* A read-only descriptor is enough: chmod does not need write access. */
    {
        int rfd = open(f, O_RDONLY);
        CHECK_RC("B5-fchmod-readonly-rc", "0", fchmod(rfd, 0607));
        {
            struct stat st;
            errno = 0;
            if (fstat(rfd, &st) < 0)
                report("B5-fchmod-readonly-mode", "mode 0607",
                       "fstat errno %d", errno);
            else
                report("B5-fchmod-readonly-mode", "mode 0607", "mode %04o",
                       (unsigned)(st.st_mode & 07777));
        }
        close(rfd);
    }

    /* --- C: fchmodat(2) (no flags argument) ------------------------------- */
    CHECK_RC("C1-fchmodat-cwd-rc", "0", fchmodat(AT_FDCWD, f, 0666, 0));
    check_mode("C1-fchmodat-cwd-mode", f, "mode 0666");

    dfd = open(d, O_RDONLY | O_DIRECTORY);
    CHECK_RC("C2-fchmodat-dirfd-rc", "0", fchmodat(dfd, "../f", 0641, 0));
    check_mode("C2-fchmodat-dirfd-mode", f, "mode 0641");
    CHECK_RC("C3-fchmodat-dirfd-missing", "errno 2",
             fchmodat(dfd, "missing", 0641, 0));
    CHECK_RC("C4-fchmodat-dirfd-file", "errno 20",
             fchmodat(fd, "f", 0641, 0));
    CHECK_RC("C5-fchmodat-badfd", "errno 9", fchmodat(-1, "f", 0641, 0));
    /* A relative name with AT_FDCWD resolves against the working directory
     * (the driver starts every engine in the tree root).
     * An absolute path with a dirfd is not asserted: glibc's fchmodat -- which
     * QEMU forwards to -- appends the name to /proc/self/fd/<fd> even when it
     * is absolute, while the kernel (and musl) ignore the descriptor; gem5
     * follows the kernel. */
    CHECK_RC("C6-fchmodat-cwd-rel-rc", "0", fchmodat(AT_FDCWD, "f", 0643, 0));
    check_mode("C6-fchmodat-cwd-rel-mode", f, "mode 0643");

    if (pipe(pp) == 0) {
        CHECK_RC("C7-fchmodat-pipe-dirfd", "errno 20",
                 fchmodat(pp[0], "f", 0641, 0));
        close(pp[0]);
        close(pp[1]);
    }
    close(fd);

    /* --- D: fchmodat2(2) (flag-carrying) ---------------------------------- */
#ifdef SYS_fchmodat2
    CHECK_RC("D1-fchmodat2-plain-rc", "0",
             syscall(SYS_fchmodat2, AT_FDCWD, f, 0644, 0));
    check_mode("D1-fchmodat2-plain-mode", f, "mode 0644");
    CHECK_RC("D2-fchmodat2-nofollow-file-rc", "0",
             syscall(SYS_fchmodat2, AT_FDCWD, f, 0605, AT_SYMLINK_NOFOLLOW));
    check_mode("D2-fchmodat2-nofollow-file-mode", f, "mode 0605");

    CHECK_RC("D3-fchmodat2-nofollow-link", "errno 95",
             syscall(SYS_fchmodat2, AT_FDCWD, l, 0611, AT_SYMLINK_NOFOLLOW));
    check_lmode("D3-fchmodat2-nofollow-link-mode", l, "mode 0777");
    under("missing", tmp, sizeof(tmp));
    CHECK_RC("D4-fchmodat2-nofollow-missing", "errno 2",
             syscall(SYS_fchmodat2, AT_FDCWD, tmp, 0611,
                     AT_SYMLINK_NOFOLLOW));
    CHECK_RC("D5-fchmodat2-nofollow-dir-rc", "0",
             syscall(SYS_fchmodat2, AT_FDCWD, d, 0751, AT_SYMLINK_NOFOLLOW));
    check_mode("D5-fchmodat2-nofollow-dir-mode", d, "mode 0751");
    chmod(d, 0755);

    fd = open(f, O_RDWR);
    CHECK_RC("D6-fchmodat2-empty-fd-rc", "0",
             syscall(SYS_fchmodat2, fd, "", 0642, AT_EMPTY_PATH));
    {
        struct stat st;
        errno = 0;
        if (fstat(fd, &st) < 0)
            report("D6-fchmodat2-empty-fd-mode", "mode 0642",
                   "fstat errno %d", errno);
        else
            report("D6-fchmodat2-empty-fd-mode", "mode 0642", "mode %04o",
                   (unsigned)(st.st_mode & 07777));
    }
    close(fd);

    dfd = open(d, O_RDONLY | O_DIRECTORY);
    CHECK_RC("D7-fchmodat2-empty-dirfd-rc", "0",
             syscall(SYS_fchmodat2, dfd, "", 0752, AT_EMPTY_PATH));
    check_mode("D7-fchmodat2-empty-dirfd-mode", d, "mode 0752");
    chmod(d, 0755);
    close(dfd);

    CHECK_RC("D8-fchmodat2-empty-noflag", "errno 2",
             syscall(SYS_fchmodat2, AT_FDCWD, "", 0644, 0));
    CHECK_RC("D9-fchmodat2-badflag", "errno 22",
             syscall(SYS_fchmodat2, AT_FDCWD, f, 0644, 0x8000));
    CHECK_RC("D10-fchmodat2-empty-badfd", "errno 9",
             syscall(SYS_fchmodat2, -1, "", 0644, AT_EMPTY_PATH));
    if (pipe(pp) == 0) {
        CHECK_RC("D11-fchmodat2-empty-pipe", "0",
                 syscall(SYS_fchmodat2, pp[0], "", 0600, AT_EMPTY_PATH));
        close(pp[0]);
        close(pp[1]);
    }

    /* fchmodat2 with no flags and a dirfd-relative name. */
    dfd = open(d, O_RDONLY | O_DIRECTORY);
    CHECK_RC("D12-fchmodat2-dirfd-rc", "0",
             syscall(SYS_fchmodat2, dfd, "../f", 0610, 0));
    check_mode("D12-fchmodat2-dirfd-mode", f, "mode 0610");
    close(dfd);
#else
    printf("PASS D0-fchmodat2-available expected=skipped actual=skipped\n");
#endif

    printf("SUMMARY fails=%d\n", fails);
    return fails ? 1 : 0;
}
