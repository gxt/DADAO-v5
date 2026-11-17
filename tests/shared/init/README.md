# tests/shared/init — M14 K0 MVP `init`

The first user program the K1 kernel runs from the built-in initramfs
(`.tao/tasks/infra/m14-infra-002-initramfs与semihosting闭环.md`).  It is a
**static musl** program: `crt1.o` enters `main` through the Linux-shaped stack
vector the kernel hands over, and the program only uses the four syscalls the
K0 MVP is scoped to (`.tao/contracts/contract-syscall.md` §1.1/§3/§4):

| call | purpose | number source |
|---|---|---|
| `getpid` | pid must be `> 0` | locked kernel `scripts/syscall.tbl` (cross-checked against musl `bits/syscall.h`) |
| `write` | banner on fd 1 (partial writes retried), diagnostics on fd 2 | same |
| `brk` | read break, grow by one 64 KiB page, read back | same |
| `exit_group` | exit 0 (via musl `_Exit`) | same |

The C source never hardcodes a number: it uses the musl `<sys/syscall.h>`
macros, and `tools/linux/make_initramfs.py` derives the manifest's
`syscall_numbers` from the locked kernel table and fails if the two carriers
disagree.

## Exit codes

| code | meaning |
|---|---|
| 0 | success (banner + one-page heap growth verified) |
| 2 | `write(2)` to fd 1 failed |
| 3 | `getpid(2)` returned `<= 0` |
| 4 | `brk(2)` failed (read / grow / re-check) |

## Build

```
make linux-initramfs     # -> init ELF + newc initramfs.cpio + manifest.json
```

Outputs are runtime artifacts (the initramfs staging directory the manifest
points at), not repository files.  The ELF is `ET_EXEC`/`EM_DADAO`, has no
`PT_INTERP`, no dynamic section and no build-id; the archive is deterministic
(fixed mtime/uid/gid, ordered entries, 4-byte alignment).

## Host unit test (error paths)

The target ELF cannot be exercised before the kernel exists, so the decision
logic is unit-tested on the build host with injectable shims
(`-DHOST_TEST` replaces `write`/`getpid`/`brk`; `host_test.c` selects the
scenario):

```
cc -DHOST_TEST -O1 -Wall -Wextra tests/shared/init/init.c \
   tests/shared/init/host_test.c -o /tmp/opencode/<task>/host_test
/tmp/opencode/<task>/host_test ok             # rc 0
/tmp/opencode/<task>/host_test ok_short       # rc 0 — 5-byte partial writes
/tmp/opencode/<task>/host_test write_fail     # rc 2
/tmp/opencode/<task>/host_test pid_zero       # rc 3
/tmp/opencode/<task>/host_test brk_read_fail  # rc 4
/tmp/opencode/<task>/host_test brk_grow_fail  # rc 4
/tmp/opencode/<task>/host_test brk_recheck_fail # rc 4
```

Each scenario runs in its own process, so the process exit status *is* the code
`init.c` chose — no in-process assertions to drift.

## Note on the linked binary

`crt1.o` + `libc.a` are linked as a real Linux startup: musl's
`__libc_start_main` pulls its own startup code, which issues
`set_tid_address` at run time (and contains unreachable secure-exec paths).
The acceptance criterion "syscall set ⊆ {write, getpid, brk, exit_group}"
therefore applies to the syscalls **init's own code** issues (scope confirmed by
the user on 2026-11-13: “不做特殊限制，别滥用就行”); the musl startup
baseline is separate and is recorded/compared explicitly in the evidence
script (a runtime `-strace` under the existing `qemu-dadao` shows exactly
`set_tid_address` from startup plus init's four).
