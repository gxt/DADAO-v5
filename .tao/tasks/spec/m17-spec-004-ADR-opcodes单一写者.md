# m17-spec-004: ADR——`opcodes.yaml` 单一写者与生成一致性

**模块**：spec
**项目里程碑**：M17
**依赖**：`m17-spec-003`（门控已落）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景

`m17-spec-003` 收口了 `generate_opcodes.py` 与 `contracts/opcodes.yaml` 的漂移，并新增 L1 `check-opcodes-repro`（重渲染 == 入库 yaml 逐字节）。reviewer 按 `Process-03` 判据（跨模块一致、多方案取舍、结论固化）建议立轻量 ADR，记录「yaml 为机器数据真源、生成器为唯一写者」的长期约束。

## 要做

1. 新增 `.tao/adr/adr-0063-*.md`（编号 0063；状态 `Candidate`）：
   - D1 `contracts/opcodes.yaml` 是机器可读**真源**；
   - D2 `tools/spec/generate_opcodes.py` 是**唯一写者**（禁手改 yaml）；
   - D3 L1 `check-opcodes-repro` 是机械判据（渲染 == 入库）；
   - D4 修改流程：改生成器 → 重跑 → 评审 diff；`--check` 失败即红；
   - D5 影响面：`validate-encoding`/`check-instrinfo`/`check-qemu-forms`/`check-isa-coverage` 等消费方；
2. 在 `ADR` 中注明与 `ADR-0019`（重定位）/`ADR-0032`（编码重分配）等既有 ADR 的关系（不重复其决策）。

## 不做

- 不改 yaml/生成器/spec 正文；不升版本号；
- 不批量改消费方门控。

## 约束

- 独立 `git worktree`；不提交 git；只新增 ADR + 本任务书；完成区 ≤30 行。

## 验证

1. ADR 存在、`Candidate`、D1–D5 完整；
2. 文中引用的门控/文件现场 `grep` 存在；
3. 不产生 yaml/生成器改动（`git status` 仅 ADR + 任务书）。

## 待裁定（用户）

- D1–D5 逐条确认后转 `Accepted`；
- 是否并入既有 ADR（如 `ADR-0032`）而不新开——本任务默认新开 0063。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
