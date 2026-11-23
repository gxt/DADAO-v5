# tests/arch/ptw — cfx4（TLB/PTW）用例与 RTL 承载

本目录是 cfx4 的 arch scope：15 条 `arch-ptw-*`（`m16-testcases-010` 的
QEMU/gem5 期望在 `expected.yaml`），以及 cfx4 的 RTL 承载（`m16-chipyard-018`）。

## 文件

| 文件 | 作用 |
|------|------|
| `ptw_carrier_tlb.py` / `check_tlb.py` | QEMU/gem5 的载体与驱动入口（`kind: driver`，`--only <case>`） |
| `expected.yaml` | 15 条 case 的期望清单（大类/子原因/`cause_info` 语义/已接线签名槽/来源 §） |
| `ptw_sig.S` + `ptw_sig.lds` + `gen_ptw_sig_tables.py` | **RTL 承载**：同一组 case id/期望；`--defsym PTW_CASE=1..12` 选场景 |
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
`tests/arch.yaml` 的 15 条双向核对。当前：`signature` 3 条、`guest` 9 条、
`gap` 3 条（013/014/015，原因与 `close_when` 在清单里）。`gap` 返回 77
（`GAP`），不当作通过；`run_arch` 只对清单登记过的 gap 放行。

## H/S/U（J 不测）

RTL 的固定 BootROM（`spec/Kaiwu §6.2`）把测试体交付为 `cfx_hmon` + `hypv`，
PTE 的 `H=1` 是运行前提；`H=0` ⇒ `NHPERM` 由 `PTW_CASE=11` 覆盖。

- `H/S/U` **三模式**：`modes.yaml` 对 15 条 ptw case 登记 `[hmon]`，`smon`/
  `umon` 的排除原因逐条写明（QEMU/gem5 载体固定 `cfx_hmon`/hypv；RTL 的 step5
  测试路径没有 smon/umon 进入链，`tests/ee-vast/README.md`）。`--mode smon`
  会显式 `rc=2` + 原因，不静默按 hmon 跑。
- PTE 的 `S`/`U` 位在 **hypv** 下不改变判定（与 QEMU/gem5 的 `pte_leaf(hsju=…)`
  同口径）；S/U **运行模式**下的权限矩阵是缺口，随模式迁移任务补齐（不写进判据）。
- `R/W/X`：`W=0` ⇒ `NWPERM`、`R=0` ⇒ `NRPERM`、`X=0` ⇒ `NXPERM`（`PTW_CASE=11`），
  全开（`R=W=X=1`）由其余 case 覆盖；`J` 位按用户 2026-11-22 裁定不测。
