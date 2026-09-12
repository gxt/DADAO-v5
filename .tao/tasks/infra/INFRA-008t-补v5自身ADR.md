# INFRA-008t: 补 v5 自身 ADR（0001 greenfield / 0002 构建编排）

**模块**：infra
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`.tao/knowledge/adr-authoring.md`（ADR 格式与模板）、DADAO-0628 `docs/adr/0001-greenfield-rebuild.md` 与 `docs/adr/0002-build-orchestration.md`（内容溯源）、各 infra 任务书的「设计理由 / 关键概念」
- 输出：`.tao/knowledge/adr-0001-greenfield-rebuild.md`、`.tao/knowledge/adr-0002-build-orchestration.md`
- 约束：按 `adr-authoring.md` 格式（Status/Context/Decision/Rationale/Consequences，中文，Status 先 `Candidate`）；采纳 0628 决策为 **v5 自己的决策**并写成 v5 版本（0.5.3、`.work/`、`.cache/`、`manifests/` 等 v5 约定）；**不照抄 0628 正文**（内容溯源）；不写行号

## 背景（完整）

### 目标

v5 多处文档（`INFRA-002t`/`003t`/`004t`/`006t`、`docs/repository-layout.md`）引用 **ADR-0002（构建编排）**，但 v5 自身并无 `adr-0002-*.md`（`.tao/knowledge/` 只有 `adr-authoring.md` 模板）；且编号上 ADR-0001/0002 无人创建（spec 产出 0003/0004、llvm/qemu 产出 0005/0006）。本任务补 v5 自身的 ADR-0001/0002，并把这些引用改指向 v5 版本。

### 设计理由

- **任务自包含**（项目 `AGENTS.md`「参考来源与任务自包含」）：v5 文档不得把 0628 的 ADR 当权威；模板/格式以 v5 自身知识为准。
- ADR-0002 的决策（Make 用户接口 + Python 标准库处理 manifest、一次性数据在 `.work/`、按完整 commit 获取 + 单一有序补丁序列）已在 v5 infra 任务中落地（`INFRA-003t`~`006t`），需固化为 v5 的 ADR。
- ADR-0001（greenfield 重建）是项目定位决策，v5 沿用。

### 关键概念 / 数据

- ADR 格式：见 `.tao/knowledge/adr-authoring.md`。
- 0628 `docs/adr/0002-build-orchestration.md` 决策：Make 稳定接口 + Python 标准库；一次性数据在 `.work/`；每组件按完整 commit + 单一有序补丁序列；否决环境相关 URL 重写、按可变分支选版本、未审查 fixups、把上游仓库拷进 meta-repo、把脏生成树当权威实现。
- 0628 `docs/adr/0001-greenfield-rebuild.md`：greenfield 重建定位（内容溯源）。
- v5 约定：`.work/`（一次性工作区）、`.cache/`（持久 bare mirror）、`manifests/`（锁）、`components/`（有序补丁序列）。

### 上游引用

- DADAO-0628 `docs/adr/0001-greenfield-rebuild.md`、`docs/adr/0002-build-orchestration.md`（内容溯源，非执行必需）。
- 本项目：`.tao/knowledge/adr-authoring.md`、`docs/repository-layout.md`、`.tao/tasks/infra/INFRA-00{2,3,4,6}t-*.md`。

## 交付物

- `.tao/knowledge/adr-0001-greenfield-rebuild.md`：v5 greenfield 重建定位（Status 先 Candidate）。
- `.tao/knowledge/adr-0002-build-orchestration.md`：v5 构建编排决策（Make + Python 标准库、`.work/` 一次性数据、`.cache/` 持久 mirror、按完整 commit + 单一有序补丁序列、否决项）。
- **引用更新**：把 `INFRA-002t`/`003t`/`004t`/`006t` 与 `docs/repository-layout.md` 中对「ADR-0002」的引用指向 v5 `.tao/knowledge/adr-0002-build-orchestration.md`（原文只写 "ADR-0002" 处补明 v5 路径）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异。
- v5 新增 `.cache/`（持久 bare mirror）约定，ADR-0002 须体现（0628 无）。
- ADR 落点：v5 在 `.tao/knowledge/`（0628 在 `docs/adr/`）。

## 已知坑 / 结论

- 不要把 0628 的 ADR 正文照抄进来；只采纳决策并写成 v5 版本。
- Status 先 `Candidate`，评审后 `Accepted`（见 `adr-authoring.md` 流程）。
- 引用更新是最小改动：不改任务书实质内容，只让 ADR 引用可定位。

## 参考

- DADAO-0628：`.work/DADAO-0628/docs/adr/0001-greenfield-rebuild.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- 本项目：`.tao/knowledge/adr-authoring.md`、`docs/repository-layout.md`

## 验收标准

1. `.tao/knowledge/adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md` 存在，按 `adr-authoring.md` 格式（含 Status/Context/Decision/Rationale/Consequences），Status 先 `Candidate`
2. `adr-0002` 含 v5 决策：Make + Python 标准库、`.work/` 一次性数据、`.cache/` 持久 mirror、按完整 commit + 单一有序补丁序列、否决项
3. `INFRA-002t`/`003t`/`004t`/`006t`、`docs/repository-layout.md` 的 ADR-0002 引用指向 v5 `.tao/knowledge/adr-0002-build-orchestration.md`
4. 未照抄 0628 ADR 正文（内容溯源）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
