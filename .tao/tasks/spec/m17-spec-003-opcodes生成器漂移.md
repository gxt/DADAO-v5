# m17-spec-003: `generate_opcodes.py` 与 `opcodes.yaml` 漂移收口（ISS-416）

**模块**：spec
**项目里程碑**：M17
**依赖**：无
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`ISS-416`（P2，`m13-spec-005` 发现）：自 `SPEC-194t` 起只改 `contracts/opcodes.yaml`、未重跑 `tools/spec/generate_opcodes.py` ⇒ 现在重跑会改 **93 行 FP 记录**。两份都可被门控/工具消费（`validate-encoding`、`check-isa-coverage`、`check-qemu-forms`、`check-decodetree-repro` 等），漂移会造成「改 yaml 不改生成器」的静默不一致。

## 要做

1. 在临时副本里重跑生成器，与入库 `contracts/opcodes.yaml` 做**逐行 diff**，把 93 行按「纯格式/顺序 / 字段值」分类；
2. 确定唯一真源与生成方向（写进任务书）：若生成器为准 ⇒ 重生成 yaml；若 yaml 为准 ⇒ 修生成器并补对照断言（推荐后者：yaml 是长期真源）；
3. 加一条**机械门控**（或并入现有）：生成器输出 == 入库 yaml（或字段级等价），禁再漂移；
4. 不改任何指令的编码语义（opc/mask/字段位域）；版本号不升。

## 不做

- 不改 fp 语义、QEMU/gem5/RTL/IDL；
- 不动 spec 正文。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml`、必要门控/文档、本任务书；完成区 ≤30 行。

## 验证

1. `make validate-encoding check-isa-coverage check-qemu-forms check-instrutinfo`（或现场对应目标）rc=0；
2. 重跑生成器 ⇒ 与入库 yaml **零 diff**（或字段级等价断言通过）；
3. **可达 FAIL**：手改 yaml 一行 ⇒ 新门控红；`cp`+md5 还原回绿；
4. diff 审计：93 行逐条归因（格式 vs 语义），语义行数必须为 0。

## 待裁定

- 若 diff 中存在**真实字段差异**（非格式/顺序），先列清单交用户，不自行选边。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
