# tests/arch/ptw — cfx4（TLB/PTW）用例与 RTL 承载

本目录是 cfx4 的 arch scope：15 条 `arch-ptw-*`（`m16-testcases-010` 的
QEMU/gem5 期望在 `expected.yaml`），以及 cfx4 的 RTL 承载（`m16-chipyard-018`）。

## 文件

| 文件 | 作用 |
|------|------|
| `ptw_carrier_tlb.py` / `check_tlb.py` | QEMU/gem5 的载体与驱动入口（`kind: driver`，`--only <case>`） |
| `expected.yaml` | 15 条 case 的期望清单（大类/子原因/`cause_info` 语义/已接线签名槽/来源 §） |
| `ptw_sig.S` + `ptw_sig.lds` + `gen_ptw_sig_tables.py` | **RTL 承载**：同一组 case id/期望；`--defsym PTW_CASE=1..13` 选场景 |
| `check_ptw_rtl.py` + `rtl-coverage.yaml` | RTL 驱动与 15 条 case 的覆盖清单（`signature`/`guest`/`partial`/`gap`） |
| `ptw_regs.S` / `check_ptw_regs.py` | cfx4 寄存器面 + 地址路由（`m16-chipyard-006`；由原 `tools/chipyard/ptw/` 迁入） |
| `ptw_walk.S` + `gen_ptw_walk_tables.py` / `check_ptw_walk.py` | 两级步查 + A/D + 故障（`m16-chipyard-007`；由原 `tools/chipyard/ptw/` 迁入） |
| `ptw_tlb.S` + `gen_ptw_tlb_tables.py` / `check_ptw_tlb.py` | I/D TLB（`m16-chipyard-008`；由原 `tools/chipyard/tlb/` 迁入） |

命名按 `tests/arch/README.md`：`ptw_` 前缀、`check_*`/`gen_*`、`.S`/`.lds`；
**不建** `data/` 子目录。

## 签名流

机制只有一份：汇编侧 `tests/shared/asm/signature.inc`（`SIG_BEGIN`/`SIGUPD`/
`SIG_DUMP`；旧 `__REC` 就是 `SIGUPD`），host 侧 `tests/shared/signature.py`
（`parse`/`compare`）。`check_ptw_regs/walk/tlb.py` 不再自带 `unpack` 解析器；
`check_ptw_rtl.py` 用同一 `parse`/`compare`。

`arch-ptw-002/006/007` 的 RTL 槽与 QEMU/gem5 **逐字节相同**：`ptw_sig.S`
用与 `ptw_carrier_tlb.py` 同一组数据地址/PTE 值（DA/DB/DC、`hsju=0x8`、
`frags=0xFF`）。其它 case 的签名流为 0 槽（QEMU/gem5 侧也是 0 槽），判据是
guest 内断言（非零退出 = 该镜像内第 N 条断言失败）。

## 三方与差异

`run_arch.py --cfx 4 --platforms qemu,gem5,chipyard` 逐槽比较。RTL 的登记差异
在 `tests/arch/expected-divergences.yaml` 的 `slots`（`scope: [chipyard]`、
`close_when` 必填）：**DIV-14** 是 `arch-ptw-007` 的 `flush_adwbfail` 两槽
（RTL 的 PA RAM 全可写、运行期构造不出 A/D 回写失败；QEMU/gem5 的只读 BootROM
页表可以）。例外被修好时 RTL 承载判红，提示删除登记。

## 覆盖与缺口（不假装全覆盖）

`rtl-coverage.yaml` 是机器可读清单，`check_ptw_rtl.py --selfcheck` 与
`tests/arch.yaml` 的 15 条双向核对。当前：`signature` 4 条（002/006/007/**013**）、
`guest` 9 条、`gap` 2 条（014/015，原因与 `close_when` 在清单里）。`gap` 返回 77
（`GAP`），不当作通过；`run_arch` 只对清单登记过的 gap 放行。

**013 从 gap 提升为 signature**（`m16-testcases-019`）：`m16-chipyard-022` 补齐
RTL 的 `cfx_pmem` SRAM 窗口后，`ptw_sig.S` 加 `PTW_CASE=13`（页表整表清零仍能
写/读 cfx_pmem SRAM；保留 cfx 的普通 ld ⇒ `CFXMEM`，`cause_info` = 访问地址），
签名流 3 槽 `[写后回读, cause_id, cause_info]`，与 QEMU/gem5 同一组值。

**RTL 扁平 cause 回归（`m16-testcases-022`）**：`m17-chipyard-001` 把 RTL 的
`excp_cause_id` 对齐 ADR-0062 扁平位图（PTW 权限/缺失只置高位位图、低位 cause=0；
`CFXMEM`/`CFXPERM` 置位时 `[63:32]` 全 0）后，RTL 承载的 15 条 case 全部转绿：
`009/011/013` 由 known-red 变 `PASS`（rc=0），`002/006/007` 不回归（`007` 的
DIV-14 两槽仍按登记值 0/0 判），`014/015` 仍是 `gap`（rc=77）。
`arch-ptw-013` 的签名槽 0（cfx_pmem 写后回读）原先在 `SIGUPD` 前被
`INVAL_ALL` 覆写的 `rd6`（`CTL_INVALID_ALL`）覆盖，记成命令字而非回读值；本任务
把 `SIGUPD` 移到回读断言之后（槽序不变），与 `expected.yaml` 的 M1 逐字节一致。

## H/S/U（J 不测；`m16-testcases-019`）

15 条 case 在 **hmon/smon/umon** 各跑一次（`modes.yaml` 的 `modes:
[hmon, smon, umon]`）。镜像由「载体的固件段（power→hmon→PTW on）+ **共享**
`common/env-<mode>/env.S` + 本 case 的 body」组成：进入/退出、异常向量、签名
输出与 cfx 权限准备全部来自共享环境，不在本目录重写；body 仍留在载体自己的
4 MiB ROM 里（007/014 要**只读页表**、015 要**只读内存窗口**，step5 固件的 ROM
内容固定，造不出这些向量 —— 实测）。

- 测试页 PTE 的 `HSJU = H|S|U`（`0xD`，J 不测）：`DADAO-12 §2.2.5` 只查当前
  模式那一位 ⇒ 同一页在三种模式下都允许，**签名流与运行模式无关**，三方逐槽
  不必按模式分叉。
- **PTE 的 S/U 轴**（`arch-ptw-011` 的 `checks_by_mode`）：supv 下 `S=0`（H|U）
  ⇒ `NSPERM[34]`、`S=1` 即使 `U=1` 也允许（无「S 排除 U」）；user 下 `U=0`
  （H|S）⇒ `NUPERM[32]`、`U=1` 即使 `S=1` 也允许；两组都带 `R/W/X` 组合
  （`W=0`⇒`NWPERM` 等）与优先级（HSJU 先于 `R/W/X`：缺 S 且 `W=0` ⇒ `NSPERM`）。
  hypv 的 H 轴（`NHPERM`）保留。
- `cfx_access: [umon, smon, ptw, pmem, power]`：body 访问 `cfx_ptw`
  （PTBR/`ptw_enable`/TLB 命令）、`cfx_pmem`（013 的 SRAM 窗口）、`cfx_power`
  （ROM 取指与 015 的 ROM store）；smon/umon 下**同步故障处理程序**在**当前模式
  监视器**（cfx_smon/cfx_umon）名下、**触发模式**里运行（读自身 `cg5`、`escape`
  回原指令之后），所以还要声明 `smon`/`umon`（写它们的异常向量、读它们的帧）。
- 环境的两个按需开关（缺省不变）：`ENV_PERM_ALLOW`（打开时同时清监视器 cfx 的
  源位）、`ENV_TLB_INVALIDATE`（改过 L1[3] 的 U 位后丢掉旧转换），见
  `common/env-README.md`。
- `R/W/X` 与 HSJU 正交；`J` 位按用户 2026-11-22 裁定不测。
