# m13-spec-003: `forem` 的 NaN 优先级按 IEEE §7.2 f) 写明

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-002`（同册，串行）
**可并行分片**：否（单册单写者）
**状态**：待开始

## 背景

`m12-chipyard-014` 的 reviewer 发现 `spec/SimRISC-07 §2.1` 对 `qNaN rem ±0` 有两句互相冲突的表述：

- 「`rfHD` 为 ±0 ⇒ NV」
- 「qNaN 作输入不传播标志」

用户 2026-11-12 追问「IEEE 754 标准里有规定吗」，核查结论：**有明文**。

IEEE 754-2019 **§7.2 f)**（无效操作的条件）原文：

> remainder: remainder(x, y), when y is zero or x is infinite **and neither is a NaN**

即：**只要任一操作数是 NaN，remainder 就不属无效操作**，不置 invalid；quiet NaN 原样传播（§6.2：quiet NaN 输入不触发任何异常），signaling NaN 仍按 §7.2 a) 置 invalid。

⇒ 现行实现（NaN 优先、`qNaN rem ±0` 不置 NV）**符合 IEEE**；错的是 spec 那句缺了「且两者都不是 NaN」的限定。

## 目标

1. `spec/SimRISC-07 §2.1`：给「`rfHD` 为 ±0 ⇒ NV」补限定语——**「且两个操作数都不是 NaN」**，并明写优先级：NaN 输入优先于「除数为 ±0」这条无效条件。
2. 同节或脚注补一句 sNaN 例外：sNaN 操作数仍置 `NV`（IEEE §7.2 a）。
3. `.tao/contracts/contract-fp.md` 同步（投影，不反向定义语义）。
4. 版本与 `manifests/spec-readonly.lock.toml` 同笔更新（只改 `SimRISC-07` 一行 sha）。

## 非范围

- 不改任何实现（chipyard/QEMU/gem5 现状即 IEEE 一致）
- 不改向量（现有向量已按 NaN 优先）
- 不动 `fo2ft` 溢出（`m13-spec-002`）

## 验收标准

1. `§2.1` 的 remainder 段逐条给出四种组合的期望（qNaN×零、sNaN×零、finite×零、Inf×finite），且与 IEEE §7.2 f) 一致
2. `git grep` 证明无残留「`rfHD` 为 ±0 ⇒ NV」无条件表述
3. 5 个 spec 门控 + `check-knowledge-refs` rc=0
4. 版本与锁同笔更新，`sha256` 实测 MATCH
5. 一键证据脚本（含可达 FAIL：把限定语删掉 ⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 必须软链（`ISS-389`）。
- 本任务只改文字，不改行为；若发现实现与 IEEE 仍有出入，**停下登记**，不要顺手改实现。

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
