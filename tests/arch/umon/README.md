# `tests/arch/umon/` — cfx_umon（SEE / semihosting）执行向量（M5 起）

Hand-written `.s` execution vectors for the SEE/semihosting + cfx-level permission
face, driven end-to-end by `tools/testcases/arch/run_m5_e2e.py`.  Unlike the M3/M4
directories (LLVM IR `*.ll` linked to an executable) these vectors exercise the
*system* instructions (`trap`, `escape`, `cfx2rd`, `cfx2rc`) and semihosting,
which have no high-level IR form.

> `TESTCASES-073t`（2026-10-27）从 `tests/unit/llvm/codegen/m5/` 迁入（P3 arch 迁移）；
> 旧路径 `tests/unit/llvm/codegen/m5/` 保留为**符号链接**（删除见 `TESTCASES-076t`）。
> cfx 归属：Node only。power → hmon（页表/PTW）→ 测试本体在 **hypv** 运行（用户 2026-11-02 裁定）。Tiny 不跑 arch。

## Pipeline

```
llvm-mc --triple=dadao-unknown-elf -filetype=obj <vector>.s -> <vector>.o
llvm-objcopy -O binary --only-section=.text <vector>.o        -> <vector>.bin
qemu-system-dadao -M dadao-m1 -bios .dadao/tests/bootrom/step5/bootrom_step5.bin \
    -kernel <vector>.bin \
    -semihosting-config enable=on,target=native,chardev=semi \
    -chardev file,id=semi,path=<console> -d cpu -D <cpu log>
                                                -> host exit code (+ console/file)
```

The flat bin is loaded at the Node profile ENTRY (`-kernel`); the Node BootROM
(`tests/shared/bootrom/step5/`) starts at reset `0xffff_ffff_0000`, power hands
to hmon, hmon installs the page table/PTW and hands the test body to **hypv**.
No multi-TU ELF is used (ELF loading moved to M6, `ISS-168`).

## Independent oracle

`tools/testcases/validate_m5_vectors.py` re-derives every expectation from
`.tao/contracts/contract-semihosting.md §3` (service table), the vector's own
machine-readable `; @m5` header (service number, console data bytes, fault rule,
tokens) and `.tao/contracts/contract-see.md §3` (cfx permission rules).  It
never invokes `llvm-mc`, `llvm-objcopy` or QEMU.  A green validator is necessary
but not sufficient — the end-to-end run is owned by `run_m5_e2e.py`.

## Validate / run

```
python3 tools/testcases/validate_m5_vectors.py
python3 tools/testcases/arch/run_m5_e2e.py            # needs 'make build-bootrom' + 'make install-host'
python3 tools/testcases/arch/run_m5_e2e.py --inject   # counter-example self-test
```

门控：`make check-arch-smoke`（L2）/ `make check-arch`（L3）；旧名
`make test-semihost` 为别名（判据未改）。

The full vector ↔ capability ↔ expected-value table and the exact qemu command
line are in `tests/unit/llvm/lit/MC/DADAO/README-m5.md`.
