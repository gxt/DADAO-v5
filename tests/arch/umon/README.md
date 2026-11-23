# `tests/arch/umon/` — cfx_umon（SEE / semihosting）执行向量（M5 起）

Hand-written `.S` execution vectors for the SEE/semihosting + cfx-level permission
face, driven end-to-end by `tools/testcases/arch/run_m5_e2e.py`.  Unlike the M3/M4
directories (LLVM IR `*.ll` linked to an executable) these vectors exercise the
*system* instructions (`trap`, `escape`, `cfx2rd`, `cfx2rc`) and semihosting,
which have no high-level IR form.

> `TESTCASES-073t`（2026-10-27）从 `tests/unit/llvm/codegen/m5/` 迁入（P3 arch 迁移）；
> 旧路径 `tests/unit/llvm/codegen/m5/` 保留为**符号链接**（删除见 `TESTCASES-076t`）。
> cfx 归属：Vast only。power → hmon（页表/PTW）→ 测试本体在 **hypv** 运行（用户 2026-11-02 裁定）。Tiny 不跑 arch。

## Pipeline

```
llvm-mc --triple=dadao-unknown-elf -filetype=obj <vector>.S -> <vector>.o
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

## `mode_entry` — U/S/H 模式进入路由 RTL 探针（`m16-chipyard-020`）

`mode_entry.S` / `mode_entry.lds` / `check_mode_entry.py` 是 **Kaiwu-Vast RTL
（chipyard `WumingVastConfig`）** 的运行模式进入主控制流探针（`DADAO-12 §5.2/§5.3`）：

- 同步异常 / 异步中断的入口目标 = **异常前运行模式的 monitor**（U→cfx0、S→cfx2、
  H→cfx3）；第 6 步 `inner_run_mode` 取目标 cfx 的 `<mode>_switch_run_mode`；
  帧的 `excp_prev_run_mode / excp_prev_cfx_code / excp_cause_id / excp_cause_ip /
  excp_cause_info` 逐项断言，`escape` 恢复并回到编译期固定偏移；
- `trap cfxHA` 的“目标 cfx”组合（U 下 `trap cfx_smon`、H 下 `trap cfx_umon`）；
- U/S 下 `cfx2rd` 的两轴判权：目标 cfx 的 `<mode>_cfxreg` 源掩码 + `cg3 rc12`
  `cg_reg_deleg`，拒绝 ⇒ `CFXPERM` + `[39] NCFXPERM`；
- 异步 monitor-first 投递：pending 记录在当前模式 monitor 的 `cg5 rc5`
  （TIMER `1<<10`、PMEM_DMA `1<<8`），两级源掩码按源 cfxha（15/32）过滤，
  屏蔽期间保留 pending、放开后投递。

**一份 case、三个镜像**：`--defsym TMODE={0,2,3}` 在链接期选择 umon/smon/hmon，
同一份 `.S` 与同一份期望表（`check_mode_entry.py` 现场从 `spec/` +
`.tao/contracts/contract-see.md` 派生 cause 位号/模式编码/cfx 编号/switch 复位值/
`[39]` 子原因）。签名槽 14（H）/21（U）/14（S），槽序是 case 定义。

**运行模式口径（RTL）**：chipyard 的固定 BootROM（`spec/Kaiwu §6.2`）以
`cfx_power` 在 hypv 直接跳到 `ENTRY`，本探针在 `_start` 即 cfx_power/hypv，写目标
cfx 的 hypv 行后 `trap` 进入目标 cfx（H 模式 `trap cfx_hmon`）。

**两轴判权的强制范围**：与任务书口径一致，只强制 **U/S 行**；hypv 行不强制
（固定 BootROM 链以 cfx_power 运行测试体、规范复位掩码只允许 cfx_hmon，强制会让
既有 cfx 探针整体不可达；QEMU 的 BootROM 有 hmon 阶段、测试体以 cfx_hmon 交付，
故可全模式强制）。U/S 访问**无 `<mode>` 行**的 cfx（3/4/5/63…）一律 fail-closed
⇒ `CFXPERM`。两条口径都登记在 `tests/arch/expected-divergences.yaml`。

**未登记 `tests/arch.yaml`**：与 `cfx02_regs`（019）同口径——`run_arch.py` 的
chipyard 后端仍 fail-closed，且探针依赖 chipyard 的 `+loadmem` 与固定 BootROM；
运行方式见任务书的运行期证据脚本。
