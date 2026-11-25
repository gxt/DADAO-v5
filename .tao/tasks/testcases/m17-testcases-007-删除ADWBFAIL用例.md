# m17-testcases-007: 删除 ADWBFAIL 用例（页表必须在内存）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-chipyard-001`（同改 `tests/arch/ptw`，须在其合入后）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-25 裁定）

1. **页表必须放在内存里**，取 PTE 一律用内存的物理地址；把页表放 BootROM（`ptw_sig` case 007 后半的 `ROM_PTE_PA = 0xFFFF_FFFF_FFF8`）是**违反软件契约**的未定义场景，不得作为测试载体。
2. **`ADWBFAIL` 本身不需要测试**：该子原因保留在规范中即可，不为它构造用例，也不把它登记成 DIV。

因此 `m17-chipyard-001` 里「PTE 地址越窗（RTL `CFXMEM` vs QEMU `exit(1)`）」**不登记 permanent DIV**，而是**删掉该测试路径**。

## 要做

1. 删除 `tests/arch/ptw/ptw_sig.S` case 007 后半的 A/D 回写失败段（PTE 在 BootROM 的构造），以及 `gen_ptw_sig_tables.py` 的 `ROM_PTE_PA` 期望/槽位；
2. 删除/收缩 `tests/arch/ptw/ptw_carrier_tlb.py` 中「PTBR 指向 BootROM 页表」的场景与相关断言；
3. 同步 `tests/arch/ptw/expected.yaml`、`rtl-coverage.yaml`：移除该 case/槽；若 `ADWBFAIL` 在覆盖表里是 case，改为「不测（用户裁定）」而不是 GAP/DIV；
4. 全仓 `grep` 确认 **页表 PTE 地址只落在 pmem**（`0..0x8000_0000`），无 BootROM/越窗 PTE；
5. 不改 `spec/`/契约（`ADWBFAIL` 定义保留）；**不登记** `expected-divergences.yaml`；
6. 重跑受影响的 ptw 探针（三平台）与 `check_ptw_*` 自检，更新任务书。

## 不做

- 不改 RTL/QEMU/gem5 对越窗 PTE 的行为；
- 不为 ADWBFAIL 找替代载体。

## 约束

- 独立 `git worktree`；不提交 git；只动 `tests/arch/ptw/**`、必要时 `tests/arch/expected-divergences.yaml`（仅删旧临时项时）、本任务书；完成区 ≤30 行。

## 验证

1. `grep` 证明 PTE 地址只落在 pmem；
2. `arch-ptw` 受影响 case 三平台 PASS（或按覆盖表 GAP 登记，但**不得**用未定义路径）；
3. **可达 FAIL**：把某个 PTE 期望改错 ⇒ 对应槽红；`cp`+md5 还原回绿；
4. `check_ptw_regs/walk/tlb` 自检 rc=0；`check-tests-index`/`case-ledger` 不变或按现场更新；
5. 不产生任何 `DIV` 条目。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
