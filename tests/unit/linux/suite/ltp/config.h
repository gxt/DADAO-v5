/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * config.h for the DADAO LTP build (m18-linux-006).
 *
 * LTP's Autotools `configure` writes this file after probing the target.  For a
 * cross target it cannot be run here: upstream does not ship a generated
 * `configure` (only `configure.ac`), this machine has no autoconf, and the
 * probes are mostly `AC_RUN_IFELSE` (run a program) which a cross build cannot
 * answer.
 *
 * So the answer is written down instead, once, for the target -- and every
 * macro below is *proven* by a compile probe in
 * `tools/linux/suite/build_ltp.py::PROBES` before the build uses it.  A macro
 * whose capability the target's headers no longer provide fails the build
 * (`make ... --check-config`), it never silently selects an LTP fallback shim.
 *
 * Every entry says why it is 1 for this target (musl 1.2.6 + the locked kernel
 * uapi headers).  Adding a macro requires adding its probe.
 */
#ifndef DADAO_LTP_CONFIG_H__
#define DADAO_LTP_CONFIG_H__

/* clang implements the __atomic builtins (LTP's preferred atomic layer). */
#define HAVE_ATOMIC_MEMORY_MODEL 1

/* musl declares `struct file_handle` in <fcntl.h> (name_to_handle_at family). */
#define HAVE_STRUCT_FILE_HANDLE 1

/* musl provides the timerfd wrappers and <sys/timerfd.h>. */
#define HAVE_SYS_TIMERFD_H 1
#define HAVE_TIMERFD_CREATE 1
#define HAVE_TIMERFD_SETTIME 1
#define HAVE_TIMERFD_GETTIME 1

/* musl provides fallocate(), setns() and the preadv/pwritev family. */
#define HAVE_FALLOCATE 1
#define HAVE_SETNS 1
#define HAVE_PREADV 1
#define HAVE_PWRITEV 1
#define HAVE_PREADV2 1
#define HAVE_PWRITEV2 1

/* The locked kernel's uapi <linux/loop.h> carries `struct loop_config`. */
#define HAVE_STRUCT_LOOP_CONFIG 1

#endif /* DADAO_LTP_CONFIG_H__ */
