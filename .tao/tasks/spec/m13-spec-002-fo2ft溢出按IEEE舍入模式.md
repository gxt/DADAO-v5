# m13-spec-002: `fo2ft` 溢出按 IEEE 舍入模式（spec 修订）

**模块**：spec
**项目里程碑**：M13
**依赖**：无（本族第一个，其余四项等它定稿）
**可并行分片**：否（单册单写者）
**状态**：待开始

## 背景（共同，5 个子任务共用）

用户 2026-11-12 定规则（`MEMORY.md`「DADAO 反套用清单」末条）：**浮点差分一律以 IEEE-754 2019 为准**，SimRISC 与各模拟器据此更新修订；「与既有实现一致」不构成保留依据。

**条款**：`fo2ft` 溢出。

- 现行 spec（`spec/SimRISC-07 §1.4`）+ `contract-fp §2`：溢出**恒**返回 ±Inf（置 `OF|NX`）
- IEEE 754-2019 §7.4：结果由**舍入方向**决定 —— `RNE` / `RUP`（向 +∞）⇒ ±Inf；`RTZ` / `RDN`（向 −∞）⇒ **±最大有限值**；两种情况都置 `OF|NX`
- hardfloat `RoundAnyRawFNToRecFN` 即按舍入模式给出，可作对照

已登记 `ISS-397`。

## 本任务目标（只改 spec 与合约）

1. `spec/SimRISC-07` 的 `fo2ft` 溢出描述改为按舍入模式分派（写清 `RNE`/`RUP` ⇒ ±Inf、`RTZ`/`RDN` ⇒ ±最大有限，均置 `OF|NX`）。
2. `spec/SimRISC-07` 补一句**规范性引用**：浮点行为以 **IEEE-754 2019** 为准；与本文冲突时以 IEEE 为准（存在有意偏离的，必须显式标注）。
3. `.tao/contracts/contract-fp.md` §2 同步（合约是 spec 的投影，不得反向定义语义）。
4. 版本按 `docs/Process-03`：`SimRISC-07` 版本号 + 附录条目；`manifests/spec-readonly.lock.toml` 同笔更新（只改该册一行 sha）。
5. `ADR`：若认定「原「恒 ±Inf」是有意设计」需要留痕，登记到 `.tao/knowledge/discussing.md` 与 ADR 候选；**不擅自改已 Accepted 的 ADR**（`ADR-0004` 之外若涉及 ADR-0050，逐条确认后才动）。

## 非范围

- 不改任何实现（chipyard / QEMU / gem5）
- 不改向量（`m13-testcases-011`）
- 不动其它 FP 语义（quiet+sNaN 已由 `qemu-004`/`chipyard-024` 处理）

## 验收标准

1. `spec/SimRISC-07` 的 `fo2ft` 条目逐条列出四档舍入的结果形态，且与 IEEE 754-2019 §7.4 一致
2. `contract-fp §2` 与 spec 一致（`git grep` 证无残留「恒 ±Inf」表述）
3. 5 个 spec 门控 rc=0（`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-spec-numbering` / `check-spec-refs`）+ `check-knowledge-refs`
4. 版本与锁同笔更新，`sha256` 实测 MATCH
5. 一键证据脚本（含可达 FAIL 注入：把「按舍入模式」改回「恒 ±Inf」⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 必须软链（`ISS-389`）；spec 单写者。
- 本册定稿后，实现侧三册（`m12-chipyard-025` / `m13-qemu-005` / `m13-gem5-007`）才可派单。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
