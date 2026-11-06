#!/usr/bin/env python3
"""QEMU-062t user-mode smoke test: static AND dynamic musl programs under qemu-dadao.

What this tool does
-------------------
1. links a small set of guest programs against the P1/P2 musl products
   (``lib/crt1.o`` + ``lib/libc.a`` for the static line, ``lib/libc.so`` with an
   explicit ``-dynamic-linker /lib/ld-musl-dadao.so.1`` for the dynamic line);
2. runs them under ``qemu-dadao`` (the linux-user target added by QEMU-062t);
3. checks stdout, exit status, syscall-contract observations and the dynamic
   loader's auxv against values derived **independently** of the emulator.

Independent oracle (contract-syscall.md §5 / contract-dynlink.md §8)
--------------------------------------------------------------------
* ELF facts (``e_entry``, ``e_phnum``, ``e_phentsize``, the raw ``PT_INTERP``
  payload, the relocation-type inventory) are parsed from the files here;
* ``-errno`` values come from the host kernel uapi headers
  (``asm-generic/errno*.h``), not from qemu or from the musl port;
* program output is fixed by the sources embedded in this file;
* the guest page size (64 KiB) is fixed here from spec/DADAO-12 §2.2.2
  (``VA[15:00]`` in-page offset) and contract-elf.md §5.3 (``p_align`` 0x10000),
  not read back from qemu;
* the guest rlimit expectations (RLIMIT_AS caps every mapping, RLIMIT_DATA caps
  writable private mappings with the kernel's cur=0 workaround, read-only and
  shared writable mappings are not data) come from the reference kernel's
  ``may_expand_vm()`` (mm/mmap.c), not from qemu;
* the RLIMIT_STACK group asserts the documented qemu-user policy (the main
  stack is pre-mapped by the loader, so the limit is applied at
  ``mmap(MAP_GROWSDOWN)`` time; a native kernel would defer it to stack
  growth), and the untouched-value default is derived here from qemu's
  documented ``-s`` default (8 MiB) plus main.c's rule of raising it to the
  host's RLIMIT_STACK when that is finite and larger -- not read back from
  qemu at run time;
* nothing is read back from qemu's own logs or implementation.

The syscall numbers used by the raw-trap probes come from the *guest* header
``<sys/syscall.h>`` (musl's port), i.e. from the same asm-generic table the
contract locks -- not from qemu.

Exit status: 0 only when every check passes; any failure exits non-zero.
"""

from __future__ import annotations

import argparse
import os
import re
import resource
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MUSL = ROOT / ".work" / "source" / "musl"
QEMU_BUILD = ROOT / ".work" / "build" / "qemu"
DEFAULT_WORK = Path("/tmp/opencode/QEMU-062t/smoke")

TARGET = "dadao-unknown-elf"
DYNAMIC_LINKER = "/lib/ld-musl-dadao.so.1"

# DADAO normal page = 64 KiB: the in-page offset is VA[15:00] (16 bits),
# spec/DADAO-12 §2.2.2 "普通页的地址转换", and contract-elf.md §5.3 makes
# 0x10000 the default p_align.  Fixed here independently of the emulator: the
# assertion must fail if qemu reports anything else (4 KiB was a QEMU bug).
PAGE_SIZE = 1 << 16

PT_LOAD, PT_DYNAMIC, PT_INTERP, PT_PHDR = 1, 2, 3, 6
ET_EXEC, ET_DYN = 2, 3
EM_DADAO = 0x0DA0
SHT_RELA = 4
R_DADAO_ABS48, R_DADAO_JUMP_SLOT, R_DADAO_RELATIVE = 6, 7, 8

# ── guest test programs ─────────────────────────────────────────────────────
# Kept in one place so the expected outputs below are traceable to the source.

HELLO_C = r"""
#include <unistd.h>
static volatile char msg[] = "hi\n";
int main(void) { write(1, (const void *)msg, 3); return 0; }
"""

EXIT_C = r"""
int main(void) { return 42; }
"""

# Guest-visible page size, asked three independent ways, plus the alignment of
# a fresh anonymous mapping.  All three must report PAGE_SIZE (64 KiB), and the
# mmap address must be PAGE_SIZE-aligned: qemu writes AT_PAGESZ from
# TARGET_PAGE_SIZE and musl answers getpagesize()/sysconf(_SC_PAGESIZE) from
# that auxv value, so a 4 KiB build is caught on every path.  One line, fixed
# order.
PAGESZ_C = r"""
#include <unistd.h>
#include <stdio.h>
#include <sys/auxv.h>
#include <sys/mman.h>
int main(void)
{
    /* musl resolves getpagesize()/sysconf(_SC_PAGESIZE) from AT_PAGESZ at
     * start-up; the ABI has no getpagesize syscall (asm-generic numbering). */
    long gps = getpagesize();
    long sc = sysconf(_SC_PAGESIZE);
    long aux = (long)getauxval(AT_PAGESZ);
    void *p = mmap(0, 1, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return 3;
    printf("%ld %ld %ld %lx\n", gps, sc, aux, (unsigned long)p);
    return 0;
}
"""

# Multi-byte structures must cross the host<->guest boundary in TARGET byte
# order (big-endian, contract-elf.md §1):
#   * writev: the iovec array (base/len, 8 B each) is read FROM guest memory;
#   * fstat : the stat structure (st_size among others) is written TO guest
#             memory.
# A little-endian mix-up would garble one of the two directions.
BE_C = r"""
#include <unistd.h>
#include <stdio.h>
#include <sys/uio.h>
#include <sys/stat.h>
static volatile char a[] = "BE";
static volatile char b[] = "!\n";
int main(void)
{
    struct iovec iov[2];
    struct stat st;
    char out[32];
    int n;
    iov[0].iov_base = (void *)a; iov[0].iov_len = 2;
    iov[1].iov_base = (void *)b; iov[1].iov_len = 2;
    if (writev(1, iov, 2) != 4) return 1;
    if (fstat(0, &st) != 0) return 2;
    n = snprintf(out, sizeof out, "%llx\n", (unsigned long long)st.st_size);
    write(1, out, n);
    return 0;
}
"""

# Raw umon trap, bypassing musl's __syscall_ret(), so the value in rd8 is
# observed directly.  ABI: nr rd15, data args rd16+, address args rb16+,
# result/errno in rd8 (contract-syscall.md §2/§3/§4).
RAW_C = r"""
#include <unistd.h>
#include <stdio.h>
#include <sys/syscall.h>
static inline long raw_write(int fd, const void *buf, unsigned long n)
{
    register long nr __asm__("rd15") = SYS_write;
    register long r16 __asm__("rd16") = fd;
    register long r17 __asm__("rd17") = (long)n;
    register long rb16 __asm__("rb16") = (long)buf;
    register long ret __asm__("rd8");
    __asm__ __volatile__("trap cfx0, 0\n\t" : "=r"(ret)
                         : "r"(nr), "r"(r16), "r"(r17), "r"(rb16) : "memory");
    return ret;
}
int main(void)
{
    char out[32];
    int n;
    long r = raw_write(-1, (const void *)"x", 1);
    n = snprintf(out, sizeof out, "%llx\n", (unsigned long long)r);
    write(1, out, n);
    return 0;
}
"""

# A number outside the adopted table: the contract says an unimplemented
# number must come back as an explicit -ENOSYS, never as a silent success.
ENOSYS_C = r"""
#include <unistd.h>
#include <stdio.h>
static inline long raw_trap(long nr)
{
    register long nr_reg __asm__("rd15") = nr;
    register long ret __asm__("rd8");
    __asm__ __volatile__("trap cfx0, 0\n\t" : "=r"(ret) : "r"(nr_reg) : "memory");
    return ret;
}
int main(void)
{
    char out[32];
    int n;
    long r = raw_trap(5000);      /* no syscall in the table has this number */
    n = snprintf(out, sizeof out, "%llx\n", (unsigned long long)r);
    write(1, out, n);
    return 0;
}
"""

# ioctl is the mask-0x04 case of the argument routing (fd and request in the
# data bank, the pointer in the address bank).  With stdout redirected to a
# regular file TCGETS must fail with ENOTTY; if the host side looked for the
# pointer in the data bank it would pass a stale register instead.
IOCTL_C = r"""
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <termios.h>
#include <sys/ioctl.h>
int main(void)
{
    struct termios t;
    char out[48];
    int n;
    int r;
    errno = 0;
    r = ioctl(1, TCGETS, &t);
    n = snprintf(out, sizeof out, "r=%d errno=%d\n", r, errno);
    write(1, out, n);
    return 0;
}
"""

# QEMU-084t (ISS-343): the guest-visible RLIMIT_AS / RLIMIT_DATA / RLIMIT_STACK
# must be the values the guest set, and once a limit is in force the guest's
# own mapping calls must fail with ENOMEM exactly where the kernel's
# may_expand_vm() would say no.  The expected values below come from the
# reference kernel rule (mm/mmap.c: RLIMIT_AS caps total_vm for any mapping;
# RLIMIT_DATA caps writable private mappings, with the "Workaround for
# Valgrind" that keeps cur=0/max-untouched working; read-only and shared
# writable mappings are not data), not from qemu.
#
# The page size is written as 65536 here on purpose: the probe must not learn
# it from the emulator (spec/DADAO-12 §2.2.2).
#
# Not probed: brk().  The DADAO musl port's public brk() returns -ENOMEM
# unconditionally and its syscall(SYS_brk, ...) wrapper mis-passes the
# argument (TESTCASES-099t diagnosis), so neither can judge rlimit
# accounting; do_brk() grows the heap through target_mmap(), i.e. the same
# path the RW mmap below exercises.
RLIMIT_C = r"""
#include <unistd.h>
#include <errno.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/syscall.h>

#define PROBE_PAGE 65536UL

static char obuf[2048];
static int olen;

static void put_str(const char *s)
{
    while (*s) obuf[olen++] = *s++;
}

static void put_dec(unsigned long v)
{
    char t[24];
    int i = 0;
    if (!v) t[i++] = '0';
    while (v) { t[i++] = (char)('0' + v % 10); v /= 10; }
    while (i) obuf[olen++] = t[--i];
}

static void put_hex(unsigned long v)
{
    char t[20];
    int i = 0;
    if (!v) t[i++] = '0';
    while (v) {
        unsigned d = (unsigned)(v & 15);
        t[i++] = (char)(d < 10 ? '0' + d : 'a' + d - 10);
        v >>= 4;
    }
    while (i) obuf[olen++] = t[--i];
}

static void put_kv(const char *k, const char *v)
{
    put_str(k); obuf[olen++] = '='; put_str(v); obuf[olen++] = '\n';
}

static void put_kv_dec(const char *k, long v)
{
    put_str(k); obuf[olen++] = '=';
    if (v < 0) { obuf[olen++] = '-'; put_dec((unsigned long)-v); }
    else put_dec((unsigned long)v);
    obuf[olen++] = '\n';
}

static void put_kv_hex(const char *k, unsigned long v)
{
    put_str(k); obuf[olen++] = '='; put_hex(v); obuf[olen++] = '\n';
}

static void *map_rw_flags(unsigned long len, int flags)
{
    errno = 0;
    return mmap(0, len, PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS | flags, -1, 0);
}

static void *map_rw(void)
{
    return map_rw_flags(PROBE_PAGE, 0);
}

int main(void)
{
    struct rlimit lim, got;
    void *p;

    /* RLIMIT_STACK read before anything is set: the guest's main stack is a
     * fixed region mapped by the loader, so the reported value must be that
     * region (the driver derives it from qemu's documented -s default plus
     * main.c's raise-to-the-host-limit rule), never RLIM_INFINITY. */
    put_kv_dec("stack_default_getrlimit_rc", getrlimit(RLIMIT_STACK, &got));
    put_kv_hex("stack_default_cur", (unsigned long)got.rlim_cur);
    put_kv_hex("stack_default_max", (unsigned long)got.rlim_max);

    /* control: nothing was asked for, so a RW anonymous page must map */
    p = map_rw();
    put_kv("unset_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    /* RLIMIT_AS, soft only (max stays unlimited), so it can be restored:
     * 0 caps every mapping, since the image/stack are already mapped. */
    lim.rlim_cur = 0;
    lim.rlim_max = RLIM_INFINITY;
    put_kv_dec("as_setrlimit_rc", setrlimit(RLIMIT_AS, &lim));
    put_kv_dec("as_getrlimit_rc", getrlimit(RLIMIT_AS, &got));
    put_kv_hex("as_getrlimit_cur", (unsigned long)got.rlim_cur);
    p = map_rw();
    put_kv_dec("as_mmap_rc", p == MAP_FAILED ? -1 : 0);
    put_kv_dec("as_mmap_errno", p == MAP_FAILED ? errno : 0);
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    /* RLIMIT_AS back to unlimited: the limit must not be one-way */
    lim.rlim_cur = RLIM_INFINITY;
    lim.rlim_max = RLIM_INFINITY;
    put_kv_dec("as_restore_rc", setrlimit(RLIMIT_AS, &lim));
    put_kv_dec("as_restore_getrlimit_rc", getrlimit(RLIMIT_AS, &got));
    put_kv_hex("as_restore_cur", (unsigned long)got.rlim_cur);
    p = map_rw();
    put_kv("as_restore_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    /* RLIMIT_DATA soft only: the kernel's Valgrind workaround keeps this
     * usable (data total still fits in rlim_max), so the mapping must work. */
    lim.rlim_cur = 0;
    lim.rlim_max = RLIM_INFINITY;
    put_kv_dec("data_soft_setrlimit_rc", setrlimit(RLIMIT_DATA, &lim));
    put_kv_dec("data_soft_getrlimit_rc", getrlimit(RLIMIT_DATA, &got));
    put_kv_hex("data_soft_getrlimit_cur", (unsigned long)got.rlim_cur);
    p = map_rw();
    put_kv("data_soft_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);
    lim.rlim_cur = RLIM_INFINITY;
    put_kv_dec("data_restore_rc", setrlimit(RLIMIT_DATA, &lim));
    p = map_rw();
    put_kv("data_restore_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    /* RLIMIT_STACK, soft only (reversible): the value must be reported back,
     * stack-shaped (MAP_GROWSDOWN) mappings must be capped at the soft limit,
     * and ordinary mappings must be untouched.  The MAP_GROWSDOWN caps are the
     * qemu-user policy documented in the driver: the main stack is pre-mapped
     * and cannot grow on demand here, so the limit is applied at mmap time
     * (a native kernel defers the same limit to stack growth, i.e. it would
     * accept the 256 KiB request -- that part is NOT asserted against native). */
    lim.rlim_cur = 128 * 1024;
    lim.rlim_max = RLIM_INFINITY;
    put_kv_dec("stack_setrlimit_rc", setrlimit(RLIMIT_STACK, &lim));
    put_kv_dec("stack_getrlimit_rc", getrlimit(RLIMIT_STACK, &got));
    put_kv_hex("stack_getrlimit_cur", (unsigned long)got.rlim_cur);
    put_kv_hex("stack_getrlimit_max", (unsigned long)got.rlim_max);
    p = map_rw_flags(256 * 1024, MAP_GROWSDOWN);
    put_kv_dec("stack_growsdown_256k_rc", p == MAP_FAILED ? -1 : 0);
    put_kv_dec("stack_growsdown_256k_errno", p == MAP_FAILED ? errno : 0);
    if (p != MAP_FAILED) munmap(p, 256 * 1024);
    p = map_rw_flags(128 * 1024, MAP_GROWSDOWN);
    put_kv("stack_growsdown_128k_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, 128 * 1024);
    p = map_rw_flags(256 * 1024, 0);
    put_kv("stack_plain_256k_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, 256 * 1024);
    lim.rlim_cur = RLIM_INFINITY;
    lim.rlim_max = RLIM_INFINITY;
    put_kv_dec("stack_restore_rc", setrlimit(RLIMIT_STACK, &lim));
    put_kv_dec("stack_restore_getrlimit_rc", getrlimit(RLIMIT_STACK, &got));
    put_kv_hex("stack_restore_cur", (unsigned long)got.rlim_cur);
    p = map_rw_flags(256 * 1024, MAP_GROWSDOWN);
    put_kv("stack_restore_growsdown_256k", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, 256 * 1024);

    /* Raw syscall numbers 163/164 (SYS_getrlimit/SYS_setrlimit): musl's
     * libc wrappers use prlimit64, so these two branches need their own
     * probe.  Reversible: soft 0 with max untouched, then restore. */
    lim.rlim_cur = 0;
    lim.rlim_max = RLIM_INFINITY;
    put_kv_dec("raw_setrlimit_rc", syscall(SYS_setrlimit, RLIMIT_DATA, &lim));
    put_kv_dec("raw_getrlimit_rc", syscall(SYS_getrlimit, RLIMIT_DATA, &got));
    put_kv_hex("raw_getrlimit_cur", (unsigned long)got.rlim_cur);
    lim.rlim_cur = RLIM_INFINITY;
    put_kv_dec("raw_restore_rc", syscall(SYS_setrlimit, RLIMIT_DATA, &lim));
    put_kv_dec("raw_restore_getrlimit_rc",
               syscall(SYS_getrlimit, RLIMIT_DATA, &got));
    put_kv_hex("raw_restore_cur", (unsigned long)got.rlim_cur);

    /* RLIMIT_DATA = {0, 0}: now writable private mappings are data and must
     * fail, while read-only and shared writable ones are not data.  This is
     * the irreversible one (max cannot be raised back unprivileged), so it
     * runs last. */
    lim.rlim_cur = 0;
    lim.rlim_max = 0;
    put_kv_dec("data_zero_setrlimit_rc", setrlimit(RLIMIT_DATA, &lim));
    put_kv_dec("data_zero_getrlimit_rc", getrlimit(RLIMIT_DATA, &got));
    put_kv_hex("data_zero_getrlimit_cur", (unsigned long)got.rlim_cur);
    put_kv_hex("data_zero_getrlimit_max", (unsigned long)got.rlim_max);
    p = map_rw();
    put_kv_dec("data_zero_mmap_rc", p == MAP_FAILED ? -1 : 0);
    put_kv_dec("data_zero_mmap_errno", p == MAP_FAILED ? errno : 0);
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    errno = 0;
    p = mmap(0, PROBE_PAGE, PROT_READ, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    put_kv("data_zero_ro_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    errno = 0;
    p = mmap(0, PROBE_PAGE, PROT_READ | PROT_WRITE,
             MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    put_kv("data_zero_shared_mmap", p == MAP_FAILED ? "fail" : "ok");
    if (p != MAP_FAILED) munmap(p, PROBE_PAGE);

    write(1, obuf, olen);
    return 0;
}
"""

# Dynamic line: argv/envp/auxv must come from the loader-built stack (the
# ldso hands the program its original sp), AT_BASE must point at the mapped
# interpreter, and calls/globals reached through RELATIVE/JUMP_SLOT
# relocations must work (snprintf through the PLT, `environ` through a GOT
# slot).
DYN_C = r"""
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <sys/auxv.h>
#include <stdlib.h>
static void puthex(unsigned long v)
{
    char b[32];
    int n = snprintf(b, sizeof b, "%lx\n", v);
    write(1, b, n);
}
int main(void)
{
    unsigned long base = getauxval(AT_BASE);
    unsigned long entry = getauxval(AT_ENTRY);
    unsigned long phdr = getauxval(AT_PHDR);
    unsigned long phnum = getauxval(AT_PHNUM);
    unsigned long phent = getauxval(AT_PHENT);
    const unsigned char *p = (const unsigned char *)base;
    char b[64];
    int n;

    puthex(base);
    puthex(entry);
    puthex(phdr);
    puthex(phnum);
    puthex(phent);
    n = snprintf(b, sizeof b, "%02x%02x%02x%02x %02x%02x\n",
                 p[0], p[1], p[2], p[3], p[18], p[19]);
    write(1, b, n);
    /* envp comes from the same loader-built vector; getenv() reaches the
     * environment through libc's __environ, whose address is materialised by
     * a data relocation in libc.so (the executable is non-PIC, so it has no
     * GOT of its own).  printf() additionally goes through the PLT and
     * dereferences libc's `stdout` data symbol, i.e. through the loader's
     * RELATIVE/ABS48 work. */
    {
        const char *mark = getenv("QEMU062T_MARK");
        if (!mark) return 8;
        printf("mark=%s\n", mark);
        fflush(NULL);
    }
    return 7;
}
"""


def run(cmd, *, cwd=None, stdin=None, env=None, timeout=60):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env,
                          stdin=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout)


def toolchain_env() -> dict:
    env = dict(os.environ)
    bindir = ROOT / ".dadao" / "cross-toolchain" / "bin"
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    return env


def musl_include_flags() -> list[str]:
    flags: list[str] = []
    for d in ("arch/dadao", "arch/generic", "obj/src/internal", "src/include",
              "src/internal", "obj/include", "include"):
        flags.append(f"-I{MUSL / d}")
    return flags


def tool(name: str) -> Path:
    return ROOT / ".dadao" / "cross-toolchain" / "bin" / name


def builtins_archive() -> Path:
    """compiler-rt builtins for the target (clang -print-libgcc-file-name)."""
    env = toolchain_env()
    r = run([tool("clang"), f"--target={TARGET}", "-rtlib=compiler-rt",
             "-print-libgcc-file-name"], env=env)
    path = Path(r.stdout.decode().strip())
    if r.returncode != 0 or not path.is_file():
        raise SystemExit(f"cannot resolve the target builtins archive "
                         f"(clang rc={r.returncode}, path={path})\n"
                         f"{r.stderr.decode()}")
    return path


# ── ELF reader (independent of qemu) ────────────────────────────────────────

def parse_elf(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise SystemExit(f"{path}: not an ELF file")
    ei_class, ei_data = data[4], data[5]
    if ei_class != 2 or ei_data != 2:
        raise SystemExit(f"{path}: expected ELFCLASS64/ELFDATA2MSB, "
                         f"got class={ei_class} data={ei_data}")
    be = ">"
    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
     e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
     e_shstrndx) = struct.unpack_from(be + "HHIQQQIHHHHHH", data, 16)

    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
            struct.unpack_from(be + "IIQQQQQQ", data, off)
        phdrs.append(dict(type=p_type, flags=p_flags, offset=p_offset,
                          vaddr=p_vaddr, filesz=p_filesz, memsz=p_memsz))

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, \
            sh_info, sh_addralign, sh_entsize = struct.unpack_from(
                be + "IIQQQQIIQQ", data, off)
        sections.append(dict(name_off=sh_name, type=sh_type, offset=sh_offset,
                             size=sh_size, entsize=sh_entsize))

    relocs: list[tuple[int, int]] = []      # (type, offset)
    for sh in sections:
        if sh["type"] != SHT_RELA or not sh["entsize"]:
            continue
        for off in range(sh["offset"], sh["offset"] + sh["size"], sh["entsize"]):
            r_offset, r_info, r_addend = struct.unpack_from(be + "QQq", data, off)
            relocs.append((r_info & 0xFFFFFFFF, r_offset))

    interp = b""
    for p in phdrs:
        if p["type"] == PT_INTERP:
            interp = data[p["offset"]:p["offset"] + p["filesz"]]

    return dict(data=data, e_type=e_type, e_machine=e_machine, e_entry=e_entry,
                e_flags=e_flags, e_phentsize=e_phentsize, e_phnum=e_phnum,
                phdrs=phdrs, relocs=relocs, interp=interp)


def uapi_errno(name: str) -> int:
    """Read an errno value from the host kernel uapi (independent oracle)."""
    for f in ("asm-generic/errno-base.h", "asm-generic/errno.h"):
        p = Path("/usr/include") / f
        if not p.is_file():
            continue
        m = re.search(rf"^#define\s+{name}\s+(\d+)", p.read_text(), re.M)
        if m:
            return int(m.group(1))
    raise SystemExit(f"cannot derive {name} from the host uapi headers")


# ── harness ─────────────────────────────────────────────────────────────────

class Checks:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str, bool]] = []

    def add(self, name: str, expected, actual, ok: bool | None = None) -> None:
        if ok is None:
            ok = expected == actual
        self.items.append((name, str(expected), str(actual), bool(ok)))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} actual={actual}")

    def report(self) -> int:
        bad = [c for c in self.items if not c[3]]
        print(f"\n{len(self.items) - len(bad)}/{len(self.items)} checks passed")
        return 1 if bad else 0


def compile_program(name: str, source: str, work: Path, env: dict) -> Path:
    src = work / f"{name}.c"
    obj = work / f"{name}.o"
    src.write_text(source)
    r = run([tool("clang"), f"--target={TARGET}", "-O1", "-nostdinc",
             *musl_include_flags(), "-c", src, "-o", obj], env=env)
    if r.returncode != 0:
        raise SystemExit(f"compile {name} failed rc={r.returncode}\n"
                         f"{r.stdout.decode()}{r.stderr.decode()}")
    return obj


def link_static(name: str, obj: Path, work: Path) -> Path:
    out = work / f"{name}.elf"
    crt = MUSL / "lib" / "crt1.o"
    libc = MUSL / "lib" / "libc.a"
    # The static musl archive's printf pulls in the long-double (binary128)
    # helpers, so the compiler-rt builtins archive must be linked too.  Same
    # recipe (and ordering) as tools/testcases/run_clmul_probe.py: crt first,
    # then libc/builtins in one --start-group so their references resolve in
    # either order.
    r = run([tool("ld.lld"), crt, obj, "--start-group", libc,
             builtins_archive(), "--end-group", "-o", out])
    if r.returncode != 0:
        raise SystemExit(f"static link {name} failed rc={r.returncode}\n"
                         f"{r.stdout.decode()}{r.stderr.decode()}")
    return out


def link_dynamic(name: str, obj: Path, work: Path) -> Path:
    out = work / f"{name}_dyn.elf"
    crt = MUSL / "lib" / "crt1.o"
    so = MUSL / "lib" / "libc.so"
    r = run([tool("ld.lld"), crt, obj, so,
             "-dynamic-linker", DYNAMIC_LINKER, "-o", out])
    if r.returncode != 0:
        raise SystemExit(f"dynamic link {name} failed rc={r.returncode}\n"
                         f"{r.stdout.decode()}{r.stderr.decode()}")
    return out


def setup_guest_root(work: Path) -> Path:
    root = work / "root"
    (root / "lib").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MUSL / "lib" / "libc.so", root / "lib" / "ld-musl-dadao.so.1")
    return root


def qemu_run(qemu: Path, argv: list, *, ld_root: Path | None = None,
             stdin_path: Path | None = None,
             extra_env: dict | None = None) -> subprocess.CompletedProcess:
    cmd = [qemu]
    if ld_root is not None:
        cmd += ["-L", ld_root]
    cmd += argv
    stdin = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    try:
        return run(cmd, stdin=stdin, env=env)
    finally:
        if stdin_path:
            stdin.close()


def check_guest_page_size(c: Checks, label: str, qemu: Path, elf: Path,
                          ld_root: Path | None = None) -> None:
    """Assert the guest-visible page size (three independent queries)."""
    r = qemu_run(qemu, [elf], ld_root=ld_root)
    c.add(f"{label}: exit", 0, r.returncode)
    fields = r.stdout.split()
    if len(fields) != 4:
        c.add(f"{label}: output field count", 4, len(fields), ok=False)
        return
    gps, sc, aux = (int(x) for x in fields[:3])
    addr = int(fields[3], 16)
    c.add(f"{label}: getpagesize()", PAGE_SIZE, gps)
    c.add(f"{label}: sysconf(_SC_PAGESIZE)", PAGE_SIZE, sc)
    c.add(f"{label}: getauxval(AT_PAGESZ)", PAGE_SIZE, aux)
    c.add(f"{label}: mmap(NULL,1) address % PAGE_SIZE", 0, addr % PAGE_SIZE)


def check_guest_rlimit(c: Checks, label: str, qemu: Path, elf: Path) -> None:
    """Guest RLIMIT_AS/DATA/STACK: reported values and mmap enforcement.

    Expected values are the reference kernel rule (see RLIMIT_C) plus the
    host uapi ENOMEM; nothing is taken from the guest's own output meaning
    "the emulator said so" -- the program only reports what man 2 mmap /
    man 2 getrlimit say must happen.
    """
    r = qemu_run(qemu, [elf])
    c.add(f"{label}: exit", 0, r.returncode)
    kv: dict[str, str] = {}
    for line in r.stdout.decode(errors="replace").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            kv[key] = value

    enomem = uapi_errno("ENOMEM")
    infinity = "ffffffffffffffff"      # guest RLIM_INFINITY is ~0UL (musl)

    c.add(f"{label}: unset RW mmap succeeds", "ok", kv.get("unset_mmap"))

    # RLIMIT_STACK default: qemu-user maps the main stack up front, so an
    # untouched limit must report that region, not RLIM_INFINITY.  The size is
    # derived here from qemu's documented -s default (8 MiB) and main.c's rule
    # (raise to the host's RLIMIT_STACK only when finite and larger).
    mapped_stack = 8 << 20
    host_stack = resource.getrlimit(resource.RLIMIT_STACK)[0]
    if host_stack != resource.RLIM_INFINITY and host_stack > mapped_stack:
        mapped_stack = host_stack
    c.add(f"{label}: unset RLIMIT_STACK getrlimit rc", "0",
          kv.get("stack_default_getrlimit_rc"))
    c.add(f"{label}: unset RLIMIT_STACK reports the mapped main stack "
          f"({mapped_stack} B)", f"{mapped_stack:x}", kv.get("stack_default_cur"))
    c.add(f"{label}: unset RLIMIT_STACK default rlim_max", f"{mapped_stack:x}",
          kv.get("stack_default_max"))

    c.add(f"{label}: setrlimit(RLIMIT_AS, {{0,inf}}) rc", "0",
          kv.get("as_setrlimit_rc"))
    c.add(f"{label}: getrlimit(RLIMIT_AS).rlim_cur == 0", "0",
          kv.get("as_getrlimit_cur"))
    c.add(f"{label}: RLIMIT_AS=0 RW mmap rc", "-1", kv.get("as_mmap_rc"))
    c.add(f"{label}: RLIMIT_AS=0 RW mmap errno == ENOMEM", str(enomem),
          kv.get("as_mmap_errno"))
    c.add(f"{label}: RLIMIT_AS restored rc", "0", kv.get("as_restore_rc"))
    c.add(f"{label}: getrlimit(RLIMIT_AS).rlim_cur == RLIM_INFINITY",
          infinity, kv.get("as_restore_cur"))
    c.add(f"{label}: RLIMIT_AS restored RW mmap succeeds", "ok",
          kv.get("as_restore_mmap"))

    c.add(f"{label}: setrlimit(RLIMIT_DATA, {{0,inf}}) rc", "0",
          kv.get("data_soft_setrlimit_rc"))
    c.add(f"{label}: getrlimit(RLIMIT_DATA).rlim_cur == 0", "0",
          kv.get("data_soft_getrlimit_cur"))
    # may_expand_vm(): "Workaround for Valgrind" -- cur=0 with max untouched
    # keeps working, so this mapping must not be rejected.
    c.add(f"{label}: RLIMIT_DATA={{0,inf}} RW mmap succeeds (kernel cur=0 "
          f"workaround)", "ok", kv.get("data_soft_mmap"))
    c.add(f"{label}: RLIMIT_DATA restored rc", "0", kv.get("data_restore_rc"))
    c.add(f"{label}: RLIMIT_DATA restored RW mmap succeeds", "ok",
          kv.get("data_restore_mmap"))

    # {0,0}: writable private mappings are data and must fail; read-only and
    # shared writable mappings are not data and must still work.
    c.add(f"{label}: setrlimit(RLIMIT_DATA, {{0,0}}) rc", "0",
          kv.get("data_zero_setrlimit_rc"))
    c.add(f"{label}: getrlimit(RLIMIT_DATA) cur/max == 0",
          "0/0", f"{kv.get('data_zero_getrlimit_cur')}/"
                 f"{kv.get('data_zero_getrlimit_max')}")
    c.add(f"{label}: RLIMIT_DATA={{0,0}} RW mmap rc", "-1",
          kv.get("data_zero_mmap_rc"))
    c.add(f"{label}: RLIMIT_DATA={{0,0}} RW mmap errno == ENOMEM", str(enomem),
          kv.get("data_zero_mmap_errno"))
    c.add(f"{label}: RLIMIT_DATA={{0,0}} read-only mmap still succeeds", "ok",
          kv.get("data_zero_ro_mmap"))
    c.add(f"{label}: RLIMIT_DATA={{0,0}} shared RW mmap still succeeds", "ok",
          kv.get("data_zero_shared_mmap"))

    # RLIMIT_STACK: set/value round trip, stack-shaped mappings capped, plain
    # mappings untouched (qemu-user policy, see the probe source).
    c.add(f"{label}: setrlimit(RLIMIT_STACK, 128 KiB) rc", "0",
          kv.get("stack_setrlimit_rc"))
    c.add(f"{label}: getrlimit(RLIMIT_STACK).rlim_cur == 128 KiB", "20000",
          kv.get("stack_getrlimit_cur"))
    c.add(f"{label}: getrlimit(RLIMIT_STACK).rlim_max == RLIM_INFINITY",
          infinity, kv.get("stack_getrlimit_max"))
    c.add(f"{label}: RLIMIT_STACK=128 KiB MAP_GROWSDOWN 256 KiB rc", "-1",
          kv.get("stack_growsdown_256k_rc"))
    c.add(f"{label}: RLIMIT_STACK=128 KiB MAP_GROWSDOWN 256 KiB errno == ENOMEM",
          str(enomem), kv.get("stack_growsdown_256k_errno"))
    c.add(f"{label}: RLIMIT_STACK=128 KiB MAP_GROWSDOWN 128 KiB succeeds", "ok",
          kv.get("stack_growsdown_128k_mmap"))
    c.add(f"{label}: RLIMIT_STACK=128 KiB plain 256 KiB mmap unaffected", "ok",
          kv.get("stack_plain_256k_mmap"))
    c.add(f"{label}: RLIMIT_STACK restored rc", "0", kv.get("stack_restore_rc"))
    c.add(f"{label}: getrlimit(RLIMIT_STACK) back to RLIM_INFINITY", infinity,
          kv.get("stack_restore_cur"))
    c.add(f"{label}: RLIMIT_STACK restored MAP_GROWSDOWN 256 KiB succeeds", "ok",
          kv.get("stack_restore_growsdown_256k"))

    # Raw SYS_setrlimit / SYS_getrlimit (musl's libc uses prlimit64).
    c.add(f"{label}: raw SYS_setrlimit(RLIMIT_DATA, {{0,inf}}) rc", "0",
          kv.get("raw_setrlimit_rc"))
    c.add(f"{label}: raw SYS_getrlimit(RLIMIT_DATA) rc", "0",
          kv.get("raw_getrlimit_rc"))
    c.add(f"{label}: raw SYS_getrlimit(RLIMIT_DATA).rlim_cur == 0", "0",
          kv.get("raw_getrlimit_cur"))
    c.add(f"{label}: raw SYS_setrlimit restore rc", "0",
          kv.get("raw_restore_rc"))
    c.add(f"{label}: raw SYS_getrlimit after restore rc", "0",
          kv.get("raw_restore_getrlimit_rc"))
    c.add(f"{label}: raw SYS_getrlimit after restore", infinity,
          kv.get("raw_restore_cur"))


def check_identity(c: Checks, label: str, elf: Path, want_interp: bool) -> dict:
    info = parse_elf(elf)
    c.add(f"{label}: EI_CLASS/EI_DATA (2/2 == ELFCLASS64/ELFDATA2MSB)",
          "2/2", f"{info['data'][4]}/{info['data'][5]}")
    c.add(f"{label}: e_machine", hex(EM_DADAO), hex(info["e_machine"]))
    c.add(f"{label}: e_flags[7:0]", 1, info["e_flags"] & 0xFF)
    c.add(f"{label}: e_flags[31:8]", 0, info["e_flags"] >> 8)
    c.add(f"{label}: PT_INTERP",
          DYNAMIC_LINKER if want_interp else "absent",
          info["interp"].decode(errors="replace").rstrip("\0")
          if info["interp"] else "absent")
    if want_interp:
        c.add(f"{label}: PT_INTERP bytes (NUL included)",
              (DYNAMIC_LINKER + "\0").encode().hex(), info["interp"].hex())
        c.add(f"{label}: PT_DYNAMIC", "present",
              "present" if any(p["type"] == PT_DYNAMIC for p in info["phdrs"])
              else "absent")
    else:
        c.add(f"{label}: PT_DYNAMIC", "absent",
              "present" if any(p["type"] == PT_DYNAMIC for p in info["phdrs"])
              else "absent")
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu", default=str(QEMU_BUILD / "qemu-dadao"))
    ap.add_argument("--work", default=str(DEFAULT_WORK))
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--skip-dynamic", action="store_true")
    args = ap.parse_args()

    qemu = Path(args.qemu)
    work = Path(args.work)
    if work.exists() and not args.keep:
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    c = Checks()
    env = toolchain_env()

    c.add("qemu-dadao binary", "present", "present" if qemu.is_file() else "absent")
    if not qemu.is_file():
        return c.report()
    for p in ("lib/crt1.o", "lib/libc.a", "lib/libc.so"):
        c.add(f"musl product {p}", "present",
              "present" if (MUSL / p).is_file() else "absent")
    if any(not x[3] for x in c.items):
        return c.report()

    # ── static line ────────────────────────────────────────────────────────
    cases = {}
    for name, src in (("hello", HELLO_C), ("exit_code", EXIT_C),
                      ("be", BE_C), ("errno_rd8", RAW_C),
                      ("enosys_rd8", ENOSYS_C), ("ioctl_mask", IOCTL_C),
                      ("pagesz", PAGESZ_C), ("rlimit", RLIMIT_C)):
        cases[name] = link_static(name, compile_program(name, src, work, env), work)

    info = check_identity(c, "static hello", cases["hello"], want_interp=False)
    c.add("static hello: e_type", hex(ET_EXEC), hex(info["e_type"]))

    check_guest_page_size(c, "static pagesz", qemu, cases["pagesz"])

    data = work / "be_input.bin"
    data_size = 0x119D
    data.write_bytes((bytes(range(256)) * (data_size // 256 + 1))[:data_size])

    r = qemu_run(qemu, [cases["hello"]])
    c.add("static hello: stdout", b"hi\n", r.stdout)
    c.add("static hello: exit", 0, r.returncode)

    r = qemu_run(qemu, [cases["exit_code"]])
    c.add("static exit_code: stdout", b"", r.stdout)
    c.add("static exit_code: exit", 42, r.returncode)

    r = qemu_run(qemu, [cases["be"]], stdin_path=data)
    c.add("static be (writev + fstat, BE structs)",
          b"BE!\n" + ("%x\n" % data_size).encode(), r.stdout)
    c.add("static be: exit", 0, r.returncode)

    ebadf = uapi_errno("EBADF")
    r = qemu_run(qemu, [cases["errno_rd8"]])
    want = (-ebadf) & 0xFFFFFFFFFFFFFFFF
    c.add("static errno: raw rd8 for write(-1) == -EBADF", f"{want:x}", r.stdout.strip().decode())
    c.add("static errno: rd8 is negative", "sign bit set", "sign bit set"
          if r.stdout.strip() and int(r.stdout.strip(), 16) >> 63 else "clear")

    enosys = uapi_errno("ENOSYS")
    r = qemu_run(qemu, [cases["enosys_rd8"]])
    want = (-enosys) & 0xFFFFFFFFFFFFFFFF
    c.add("static unimplemented nr: raw rd8 == -ENOSYS", f"{want:x}", r.stdout.strip().decode())

    enotty = uapi_errno("ENOTTY")
    r = qemu_run(qemu, [cases["ioctl_mask"]])
    c.add("static ioctl(arg in rb16): r/errno", f"r=-1 errno={enotty}",
          r.stdout.strip().decode())

    # QEMU-084t (ISS-343): guest RLIMIT_AS/DATA must be reported back and
    # enforced on the guest's own mmap calls.
    check_guest_rlimit(c, "static rlimit", qemu, cases["rlimit"])

    # ── dynamic line ───────────────────────────────────────────────────────
    if not args.skip_dynamic:
        root = setup_guest_root(work)
        dyn = link_dynamic("dyn", compile_program("dyn", DYN_C, work, env), work)
        dinfo = check_identity(c, "dynamic dyn", dyn, want_interp=True)

        r = qemu_run(qemu, [dyn], ld_root=root,
                     extra_env={"QEMU062T_MARK": "062t-mark"})
        c.add("dynamic dyn: exit", 7, r.returncode)
        lines = r.stdout.decode(errors="replace").splitlines()
        c.add("dynamic dyn: output line count", 7, len(lines))
        if len(lines) == 7:
            base = int(lines[0], 16)
            c.add("dynamic dyn: AT_BASE != 0", "True", str(base != 0))
            c.add("dynamic dyn: AT_BASE page aligned", 0, base % PAGE_SIZE)
            c.add("dynamic dyn: AT_ENTRY == file e_entry", hex(dinfo["e_entry"]),
                  hex(int(lines[1], 16)))
            c.add("dynamic dyn: AT_PHDR != 0", "True",
                  str(int(lines[2], 16) != 0))
            c.add("dynamic dyn: AT_PHNUM == file e_phnum", dinfo["e_phnum"],
                  int(lines[3], 16))
            c.add("dynamic dyn: AT_PHENT == file e_phentsize",
                  dinfo["e_phentsize"], int(lines[4], 16))
            c.add("dynamic dyn: AT_BASE points at a DADAO ELF image "
                  "(magic e_machine)", "7f454c46 0da0", lines[5])
            c.add("dynamic dyn: envp + libc data relocs (getenv/printf)",
                  "mark=062t-mark", lines[6])

        # the interpreter must be required: without a guest root it cannot be
        # opened, so the very same program must fail (negative control).
        r = qemu_run(qemu, [dyn], ld_root=work / "empty-root")
        c.add("dynamic dyn: interpreter required (empty -L fails)", "True",
              str(r.returncode != 0))

        hello_dyn = link_dynamic("hello", compile_program("hello", HELLO_C, work, env),
                                 work)
        r = qemu_run(qemu, [hello_dyn], ld_root=root)
        c.add("dynamic hello: stdout", b"hi\n", r.stdout)
        c.add("dynamic hello: exit", 0, r.returncode)

        # Same three page-size queries through the dynamic loader's auxv.
        pagesz_dyn = link_dynamic("pagesz",
                                  compile_program("pagesz", PAGESZ_C, work, env),
                                  work)
        check_guest_page_size(c, "dynamic pagesz", qemu, pagesz_dyn, ld_root=root)

        # relocation inventory (structural, from the files): all three classes
        # the contract names must be present in the loaded objects.
        types = {t for t, _ in parse_elf(dyn)["relocs"]}
        libc_types = {t for t, _ in parse_elf(MUSL / "lib" / "libc.so")["relocs"]}
        c.add("relocs: executable JUMP_SLOT", "present",
              "present" if R_DADAO_JUMP_SLOT in types else "absent")
        c.add("relocs: libc.so ABS48 (6)", "present",
              "present" if R_DADAO_ABS48 in libc_types else "absent")
        c.add("relocs: libc.so JUMP_SLOT (7)", "present",
              "present" if R_DADAO_JUMP_SLOT in libc_types else "absent")
        c.add("relocs: libc.so RELATIVE (8)", "present",
              "present" if R_DADAO_RELATIVE in libc_types else "absent")

    return c.report()


if __name__ == "__main__":
    sys.exit(main())
