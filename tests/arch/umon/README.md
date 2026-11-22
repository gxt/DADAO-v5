# `tests/arch/umon/` — cfx_umon（SEE / semihosting）执行向量（M5 起）

Hand-written `.s` execution vectors for the SEE/semihosting + cfx-level permission
face, driven end-to-end by `tools/testcases/arch/run_m5_e2e.py`.  Unlike the M3/M4
directories (LLVM IR `*.ll` linked to an executable) these vectors exercise the
*system* instructions (`trap`, `escape`, `cfx2rd`, `cfx2rc`) and semihosting,
which have no high-level IR form.

> `TESTCASES-073t`（2026-10-27）从 `tests/unit/llvm/codegen/m5/` 迁入（P3 arch 迁移）；
> 旧路径 `tests/unit/llvm/codegen/m5/` 保留为**符号链接**（删除见 `TESTCASES-076t`）。
> cfx 归属：Vast only。power → hmon（页表/PTW）→ 测试本体在 **hypv** 运行（用户 2026-11-02 裁定）。Tiny 不跑 arch。

## Pipeline

```
llvm-mc --triple=dadao-unknown-elf -filetype=obj <vector>.s -> <vector>.o
llvm-objcopy -O binary --only-section=.text <vector>.o        -> <vector>.bin
qemu-system-dadao -machine kaiwu-vast,bootrom-image=.dadao/tests/bootrom/step5/bootrom_step5.bin \
    -kernel <vector>.bin \
    -semihosting-config enable=on,target=native,chardev=semi \
    -chardev file,id=semi,path=<console> -d cpu -D <cpu log>
                                                -> host exit code (+ console/file)
```

The flat bin is loaded at the Vast profile ENTRY (`-kernel`); the Vast BootROM
(`tests/ee-vast/`) starts at reset `0xffff_ffff_0000`, power hands
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

## `cfx02_regs` — cfx0/cfx2 寄存器面 RTL 探针（`m16-chipyard-019`）

`cfx02_regs.S` / `cfx02_regs.lds` / `check_cfx02_regs.py` 是 **Kaiwu-Vast RTL
（chipyard `WumingVastConfig`）** 的寄存器面探针：cfx0（umon）与 cfx2（smon）的
模式行、`cg_reg_deleg`、`cg4` 配置/计数、`cg5 rc5`、`cg6` 暂存、`cg8 rc1`、`cg7`
空间块，以及保留 rc / 写 RO ⇒ `CFXREG`。判据现场从 `spec/DADAO-12` 与
`.tao/contracts/contract-see.md` 派生，模板与 `cache/cfx5_regs.*` 相同。

**运行模式（显式排除 smon/umon）**：本探针当前只跑 **hmon（hypv）**。原因：
chipyard 的 BootROM 链以 `cfx_power`（cfx63）运行测试体，`m16-chipyard-020` 的
U/S 模式进入路由（以及打开 `cfx0`/`cfx2` 的 `<mode>_cfx*` 掩码的环境准备）尚未
合入；`smon`（supv）/`umon`（user）在本 RTL 上不可进入，故不声明这两个模式。
020 合入后须用 `tests/arch/common/env-{smon,umon}` 的三模式载体补跑。

**两轴权限**：探针覆盖掩码的**存储面**（cg0–cg3 的四个独立同步 mask 与
`cg3 rc12`）；`cfxreg` 轴的**强制判定**（`CFXPERM`）未在本任务启用——同一原因：
测试体以 `cfx_power` 运行，规范复位掩码只允许 `cfx_hmon`（bit3），启用判定会让
cfx0/cfx2（以及既有 cfx4/cfx5）整体不可达。判定随 020 的进入链落地。

本探针**未登记** `tests/arch.yaml`：`run_arch.py` 的 chipyard 后端仍 fail-closed，
且探针依赖 chipyard 的 `+loadmem`/hmon 返回槽固件；若登记会让 qemu/gem5 后端
产生不可执行的 case。运行方式见任务书的运行期证据脚本。
