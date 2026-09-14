# INTEG-001k: integ 模块启动

**模块**：integ
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 问题根源

各组件（LLVM MC / QEMU）单独测试通过，不等于**组合**起来正确：接口字段不一致、格式约定漂移、改动未回归，都会出现「各自过、合起来挂」。此前这些集成活动散落在 `verif` 模块中，未与「单组件自测」分离。

## 目的

建立**集成验证**模块：把「MC 汇编 → objcopy → flat → QEMU 执行 → 结果比对」的整条链固化为可重复的 E2E 套件（动态），并机械核对跨模块接口契约（静态），防止跨模块接口漂移与回归。

## 对照关系

- **借鉴**：DADAO-0628 的 MC↔QEMU 集成（`DL-033a`）。
- **差异**：v5 基于 SimRISC 0.5.3，E2E 链与接口契约（ADR-0003/0004）按 v5 重建。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `INTEG-002t` | E2E 套件与回归（最小链路 → 套件 → 可重复重跑） | `tests/e2e/*.s`、`tests/lit/E2E/*` | `LLVM-013m`、`QEMU-020m`、`SPEC-010t` |
| `INTEG-003t` | 跨模块接口对齐核对 | 接口核对清单/脚本 | `LLVM-013m`、`QEMU-020m`、`SPEC-011m`、`TESTCASES-010m` |
| `INTEG-004m` | M1 集成里程碑 | 里程碑标记 | `INTEG-002t`、`INTEG-003t` |

- **依赖关系**：`002t` 依赖 LLVM/QEMU 里程碑与 spec 冻结；`003t` 依赖两侧里程碑与合约；`004m` 收敛。
- **分解理由**：按「动态（E2E 执行）」与「静态（接口核对）」两条线拆分，各自可独立验收。

## 说明

- **E2E**：从 `.s` 到 QEMU 退出码的完整链路（`llvm-mc` → `llvm-objcopy --only-section=.text -O binary` → flat → QEMU）。
- **接口对齐**：核对 LLVM MC ELF emitter ↔ QEMU loader（ELF 头字段、`e_flags`、`.o→flat` 流水线）、ADR-0003 ↔ ADR-0004（flat 格式/入口/加载）、`testcases` 向量 schema ↔ QEMU harness、`contracts/opcodes.yaml` ↔ 两侧实现。
- **验证依据独立**：E2E 与接口核对不得从被测实现反推期望值（对齐 `AGENTS.md` Independent oracle）。
- 参考：`.work/DADAO-0628/code-agent/tasks/DL-033a-mc-qemu-e2e-smoke.md`。
