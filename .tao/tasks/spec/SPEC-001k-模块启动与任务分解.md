# SPEC-001k: spec 模块启动（目标澄清与任务分解）

**模块**：spec
**阶段**：1

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：SimRISC 0.5.3 规范文档（`spec/`）
- 输出：spec 模块任务分解（`SPEC-002t` ~ `SPEC-004t`）
- 约束：Spec-first，期望值来自 `spec/`，不从实现反推

## 验收标准

1. 明确 spec 模块目标与交付物
2. 分解出可独立验收的任务并标注依赖
3. 任务编号符合 `<PREFIX>-nnn<suffix>` 约定

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `SPEC-002t` | ISA 规范合约提取 | `.tao/knowledge/contract-isa.md` | — |
| `SPEC-003t` | 机器可读编码表 | `verif/opcodes.yaml` | `SPEC-002t` |
| `SPEC-004t` | 合法性规则与验证器 | `verif/legality_rules.yaml`、`verif/validate_encoding.py` | `SPEC-003t` |

## 完成区

**状态**：已验证
**Commit**：无（回填）
**测试结果**：规划任务，无可执行验收命令
**修改文件**：`.tao/tasks/spec/SPEC-001k-模块启动与任务分解.md`
**验收结果**：模块目标与任务分解确定，依赖链 `SPEC-002t → SPEC-003t → SPEC-004t`
**新发现/坑**：无
**遗留问题**：无

---

## 审阅记录

#### 第 1 轮 reviewer 验收

**说明**：本任务为按模块制约定回填的启动记录；规划内容见 `docs/phases/Phase1-ISA规范合约与编码表.md`（`## 子代理分解`）。三个交付任务均已验收，见各自任务文件的审阅记录。

**判决**：Accepted
