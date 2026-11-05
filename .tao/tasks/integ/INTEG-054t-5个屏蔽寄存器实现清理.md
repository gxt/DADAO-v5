# INTEG-054t: 5 个屏蔽寄存器实现清理

**模块**：integ
**项目里程碑**：M11
**依赖**：`SPEC-188t`/`SPEC-189t`/`SPEC-190t`（已验证；定义与路由已定稿）、`SPEC-191t`（旧码清理，文档）
**状态**：待开始

## 执行环境
本地；跨 QEMU/gem5/tests 的实现清理，按 QEMU → gem5 → tests 串行。

## 背景

`SPEC-188t` 已删除 5 个无效屏蔽寄存器的语义，编号保留 reserved：

- `inner_cfx_mask`
- `switch_cfx_mask`（cg0–3 rc9）
- `excp_cause_mask`（cg0–3 rc11）
- `excp_prev_cfx_mask`（cg5 rc1）
- `excp_cause_nonmaskable`（cg5 rc63）

保留：

- `cfx_intr_mask`（cg0–3 rc4）
- `global_cfx_intr_mask`（cg8 rc1）
- `excp_pending`（cg5 rc5）

实现仍按旧寄存器工作，需清理。

## 目标

1. **QEMU**：删除 5 个寄存器的读写/状态路径；reserved 访问 ⇒ `CFXREG`；`escape` 不再恢复 `excp_prev_cfx_mask`，保留 `global_cfx_intr_mask` 的 trap 保存/escape 恢复；保留 `cfx_intr_mask`/`excp_pending`。
2. **gem5**：同 QEMU，逐处对齐。
3. **tests**：
   - `tests/shared/bootrom/step5/hmon.S` 删除 `cfx_umon, cg3, rc9` 写；
   - 更新依赖这些寄存器的探针/向量/期望；
   - 保留 `CFXREG` 期望与 Node/Tiny 语义。
4. 三阶段串行：QEMU → gem5 → tests；共享测试只在 tests 阶段改。

## 验收标准

1. 5 个寄存器在 QEMU/gem5 活代码与 tests 活资产中 0 命中（历史/注释除外）。
2. reserved 访问 ⇒ `CFXREG`；合法路径不变；`escape` 只恢复 `global_cfx_intr_mask`。
3. `hmon.S` 不再写 rc9；Node/Tiny boot 正常。
4. `make build-qemu`/`build-gem5`、`check-source-state`/`check-patch-tree`、`check-arch`/`check-inst`、L1 rc=0。
5. `matrix-M11` 重跑：`node/arch` 249 AGREE、0 fail；无回归。
6. 反例：写回一处 rc9/inner mask ⇒ 断言 FAIL；还原回绿。
7. 完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`components/qemu/**`、`components/gem5/**`、`tests/**`（相关 bootrom/arch/inst 期望）、`tools/testcases`（仅相关读取）、本任务书、`milestones.md`。

**不在范围内**：`spec/**`、ADR、`contracts/**`、`.tao/contracts/**`（别名已由 188t 清理）、退出码语义。

## 说明

- 这是 `SPEC-188t` 的实现落地；不改 spec。
- 若某测试必须保留旧寄存器才能表达，先留问，不自行改语义。
- 退出码实现由 `INTEG-055t` 独立处理，本任务不改退出码映射。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
