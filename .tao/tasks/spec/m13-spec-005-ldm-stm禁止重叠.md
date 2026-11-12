# m13-spec-005: `ldm`/`stm` 禁止基址/索引寄存器落入传送范围

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-004`（同册，串行）
**可并行分片**：否（单册单写者）
**状态**：待开始

## 用户裁定（2026-11-13，原话）

> 「不允许重叠，改spec」

## 背景

`ldm`/`stm` 的编码是 `{rdHA:rdHA+immu6-1}, [rbHB, rdHC]`：一段**被传送的寄存器范围** + 一个**基址寄存器** + 一个**索引寄存器**。

现状（`SimRISC-01`）：允许基址/索引寄存器落在传送范围内，靠「地址按**原始** `rdHC` 计算」「按序先读后写」保证确定性，但**行为依赖处理顺序**，使用者需自行避免。

用户裁定：**不允许重叠**。

## 目标

1. **`spec/SimRISC-01`** 的限制列表加一条，**只覆盖 RD 与 RB 两种形式**：
   - **RD 形式**：索引寄存器 `rdHC`（RD bank）不得落在传送范围 `[rdHA, rdHA+immu6)` 内 ⇒ 违反 **ILLI**
   - **RB 形式**：基址寄存器 `rbHB`（RB bank）不得落在传送范围 `[rbHA, rbHA+immu6)` 内 ⇒ 违反 **ILLI**
   - **RA / RF 形式：不适用**——传送范围在 RA/RF bank，基址在 RB、索引在 RD，结构上不可能重叠（用户 2026-11-13 明确指出「基址寄存器与 rf/ra 没有关系」）；spec 应写明「不适用」，**不要**编造约束
   - 删除旧句「可以重叠…按序先读后写…行为依赖顺序」；「地址按原始 `rdHC` 计算」这句在非重叠场景已无必要，评估是否保留
2. **`contracts/legality_rules.yaml`**：新增规则（如 `mreg_range_base_overlap`），并给 `contracts/opcodes.yaml` 对应记录的 `legality` 加上该规则 id。
3. 与块复制的 `mreg_range_overlap` 保持语义一致（同一族规则的命名/写法）。

## 非范围

- 不改实现（三个平台各有独立任务：`m12-chipyard-027` / `m13-qemu-006` / `m13-gem5-008`）
- 不改测试（`m13-testcases-013` 自己改 overlap 用例）
- 不动 `spec-004` 已定的「多元素内存指令允许部分生效」

## 验收标准

1. `SimRISC-01` **RD/RB 两种形式**写明禁令与 ILLI；**RA/RF 写明「不适用」及理由**
2. `legality_rules.yaml` 新规则 + `opcodes.yaml` 的 legality 引用（`check-legality-drift`/`check-rule-refs` rc=0）
3. `git grep` 无残留「可以重叠」「行为依赖顺序」类表述（保留历史段除外）
4. 5 个 spec 门控 + `check-legality-drift`/`check-rule-refs`/`check-knowledge-refs` rc=0
5. 版本/锁按互锁规则同步（`0.5.7-rc` 未发布则并入）
6. 一键证据脚本（含可达 FAIL：删禁令 ⇒ 红）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 软链（`ISS-389`）；spec 单写者；与 `spec-004` 串行。
- 本册定稿后三个实现任务才可派单。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

（待填）
