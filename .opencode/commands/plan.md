---
description: Plan a large task - invoke architect to break down into task files - 架构师规划
agent: build
---

# /plan $ARGUMENTS — 架构师规划

调起架构师（architect）子代理，将需求拆解为任务文件。

## 执行步骤

### 1. 定位交互目录

按 `.tao/README.md`「交互目录 `$TAO_ROOT` 定位」确定 `$TAO_ROOT`。

### 2. 调起架构师子代理

用 `task` 工具调起 `architect` 子代理：

- **subagent_type**：`architect`（模型 = deepseek/deepseek-flash；定义见 `.opencode/agents/architect.md`）
- **任务描述**：需求 = `$ARGUMENTS`。让架构师澄清需求、拆解任务，在 `$TAO_ROOT/tasks/<module>/` 下创建 `<PREFIX>-nnn<suffix>-描述.md` 任务文件（模块清单由项目 `.tao/README.md` 定义）；跨组件合约变更时在 `$TAO_ROOT/knowledge/` 创建 `adr-*.md`
- 架构师返回规划结果（任务文件清单、阶段划分、ADR、待确认事项）

### 2.5 计划级交叉审查（双模型相互验证）

调起 `reviewer` 子代理（模型 = mimo/mimo-v2.5-pro）对架构师规划产出做**独立计划级审查**：

- 审查任务文件质量：依赖连通性、验收标准可验证性、风险遗漏、与 ADR 一致性
- reviewer 返回缺陷清单与判定（Needs Revision / Accepted）
- 审查通过（Accepted）后，主会话将 `k` 启动任务状态置为 `已验证`（`k` 不单独验收，见 `.opencode/agents/architect.md` 任务状态机）

### 3. 汇总统一报告并等待确认

主会话**汇总架构师规划与 reviewer 审查意见**，生成统一报告：

- 规划产出（任务文件清单、阶段依赖、ADR）
- reviewer 缺陷清单与判定
- 分歧点与最终处理（需要修订则调 architect 修订或直接修订）

汇报统一报告，提示用户：审查任务文件，确认后可用 `/dispatch` 逐一下发执行。
