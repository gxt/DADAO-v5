# m18-spec-002: hart-first/cg9 规格与契约同步（含 escape frame selector）

**模块**：spec
**项目里程碑**：M18
**依赖**：`ADR-0060`（Accepted）、`ADR-0059`（Superseded 标记由本任务落）
**可并行分片**：否（spec/契约同笔；实现任务在其后）
**预估**：4–6 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 SEE 多节 + 契约 + escape 编码，取 3–4× 中位）
**档位**：大改（ISA/契约语义）
**状态**：待开始
**执行环境**：本地

## 背景

`ADR-0060: 异步中断投递改为 hart-first（统一进 cfx_hart + 新增 cg9 异步现场）` 已 Accepted。现 `spec/DADAO-12`/`contract-see` 仍是 monitor-first（0.8.0-rc 内容），需按 ADR-0060 改为 hart-first：

- 所有异步源统一投递 `cfx_hart`（cfxha 15），入口 supv，单向量；
- `cg9` 为异步现场 + mask + pending（表见 ADR-0060 D2）；
- `async_pending` 位 = 源 cause id（`1<<17`/`1<<18`），mask 位 = 来源 cfxha（15/32）；
- `escape` 复用，`imms18` bit1 = frame selector（0=cg5，1=cg9；cg9 仅偏移 0；`imms18=3` ⇒ ILLI）；
- 版本**保持 0.8.0-rc**（用户 2026-11-23 裁定：内容改、不升号）。

## 目标

1. **spec/DADAO-12**：
   - `§5.2` 异步投递整段改 hart-first：目标 `cfx_hart`、supv 单向量、mask/pending 在 `cfx_hart cg9`、无嵌套、pending 不迁移、软件可快照/写 0 释放/重建；
   - 新增 `§3.x`（`cfx_hart` 专有）`cg9` 寄存器表（16 项，按 ADR-0060 D2；`rc13–15` reserved）；
   - `§4.7`（cfx_hart）加 cg9 与异步入口/返回；`§4.9`（cfx_pmem）异步投递目标改 `cfx_hart`；
   - `§5.3` 的 `escape` 增加 **frame selector bit1** 与合法 `imms18` 值 `{0,1,2}`、`3` ⇒ ILLI；`imms18[17:2]` SBZ；
   - monitor 的 `<mode>_cfx_intr_mask`（cg0–3 rc4）与 `global_cfx_intr_mask`（cg8 rc1）的**异步用途作废**：明确改为 reserved/非异步（不删字段，去掉异步语义）；
   - 变更记录按 0.8.0-rc 追加一条（不写任务号/ADR 号）。
2. **contract-see**：`§3` 统一异步仲裁、`§6.3` 异步内核入口、`§6.4` IE 单旋钮三段改 hart-first；`cg9` 寄存器/`escape` selector 同步；`§6.2` 的 escape 合法偏移/帧判定更新。
3. **contract-cfx-aliases / 其它契约**：补 `cg9` 的寄存器名/编号；如 `escape` 编码在 `contract-isa`/其它册有投影，一并同步（只改指针/编码语义，不复制正文）。
4. **ADR-0059**：头部加 `Superseded by ADR-0060`（保留 cause 17/18 与 mask 位索引两条有效口径的说明）。
5. **锁**：`spec/.manifests.toml` 只重算 `DADAO-12`（如 SBI 无改动则不重算 DADAO-22）的 sha256；版本号不动。

## 验收（逐条贴真实 rc）

1. `make check-spec-refs check-spec-drift check-spec-purity check-spec-changelog check-spec-numbering check-contracts-dir check-contracts-pending check-contracts` 全 rc=0（按实际目标名；至少覆盖这些）。
2. `grep` 活文档中不再有「异步先入当前运行模式 monitor」「pending 记 monitor」「async 进 cfx_umon/smon」等旧口径；`cfx_hart cg9` 表 16 项齐全；`escape` selector 的 `{0,1,2}`/`3⇒ILLI` 明文。
3. `spec/.manifests.toml` 的 DADAO-12 哈希与文件一致；版本仍 `0.8.0-rc`。
4. `ADR-0059` 头部 Superseded，指向 ADR-0060；ADR-0060 状态 Accepted。
5. 不回归：`make check` 与基线逐行相同；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git（提交由 architect/主会话）；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`spec/DADAO-12-SEE-…`、`spec/.manifests.toml`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-cfx-aliases.md`、`.tao/contracts/contract-isa.md`（若 escape 编码投影在此）、`.tao/adr/adr-0059-*.md`、本任务书。
3. **不改** `DADAO-22`（无 SBI 语义变化，版本互锁不动）、不改实现/QEMU/RTL/gem5/内核、不改版本号。
4. 不复制 spec 正文；引用用 `§章节`；术语「bank = 寄存器组」。
5. 若发现 ADR-0060 与 spec 现有其它条款冲突（如同步/异步分流、cg5 语义），停下写「待裁定」，不得自行改 ADR。

## 待裁定

无（ADR-0060 已 Accepted；若发现新冲突再写）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
