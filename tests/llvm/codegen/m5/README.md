# CodeGen/execution test vectors (M5) — SEE / semihosting

Hand-written `.s` execution vectors for the M5 (SEE + semihosting) milestone,
driven end-to-end by `tools/integ/run_m5_e2e.py`.  Unlike the M3/M4 directories
(LLVM IR `*.ll` linked to an executable) these vectors exercise the *system*
instructions (`trap`, `escape`, `cfx2rd`, `cfx2rc`) and semihosting, which have
no high-level IR form.

## Pipeline

```
llvm-mc --triple=dadao-unknown-elf -filetype=obj <vector>.s -> <vector>.o
llvm-objcopy -O binary --only-section=.text <vector>.o        -> <vector>.bin
qemu-system-dadao -M dadao-m1 -bios .dadao/tests/bootrom/bootrom.bin \
    -kernel <vector>.bin \
    -semihosting-config enable=on,target=native,chardev=semi \
    -chardev file,id=semi,path=<console> -d cpu -D <cpu log>
                                                -> host exit code (+ console/file)
```

The flat bin is loaded at the legacy RAM base `0xffff_0000_0000` (`-kernel`,
ADR-0004 D2.3 path B); the SEE bootrom (`-bios`, QEMU-047t) starts at the reset
PC `0xffff_ffff_0000`, installs the cfx user exception vector / clears the trap
masks, and hands off to the application in *user* mode (Machine-01 §2).  No
multi-TU ELF is used (ELF loading moved to M6, `ISS-168`).

## Independent oracle

`tools/testcases/validate_m5_vectors.py` re-derives every expectation from
`.tao/knowledge/contract-semihosting.md §3` (service table), the vector's own
machine-readable `; @m5` header (service number, console data bytes, fault rule,
tokens) and `.tao/knowledge/contract-see.md §3` (cfx permission rules).  It
never invokes `llvm-mc`, `llvm-objcopy` or QEMU.  A green validator is necessary
but not sufficient — the end-to-end run is owned by `run_m5_e2e.py`.

## Validate / run

```
python3 tools/testcases/validate_m5_vectors.py
python3 tools/integ/run_m5_e2e.py            # needs 'make build-bootrom' + 'make install-host'
python3 tools/integ/run_m5_e2e.py --inject   # counter-example self-test
```

The full vector ↔ capability ↔ expected-value table and the exact qemu command
line are in `tests/llvm/lit/MC/DADAO/README-m5.md`.
