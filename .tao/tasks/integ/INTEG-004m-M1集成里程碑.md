# INTEG-004m: M1 集成里程碑

**模块**：integ
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的 M1 集成闭环达成——「MC 汇编 → objcopy → flat → QEMU 执行 → 结果比对」的端到端链路打通并可重复回归，跨模块接口契约机械核对一致，形成 MC↔QEMU 集成闭环。
**关联任务**：`INTEG-002t`、`INTEG-003t`

## 核验

- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `tests/e2e/*.s`、`tests/lit/E2E/*`（`INTEG-002t`）
  - 跨模块接口对齐核对清单/脚本（`INTEG-003t`）
- 集成验收：`llvm-lit tests/lit/E2E/` 全 PASS；接口对齐核对零不一致
- 项目里程碑联动：`knowledge/milestones.md` 中 M1 行的 `integ` 列 = `INTEG-004m`

（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
