# spec 目录保护规范

> **状态**：生效（2026-10-07）｜**上位依据**：无——属**工程过程规范**（可逆、单项目、无外部契约，不命中 ADR 判据，见 `spec/Process-03`）。
> **缘起**：`SPEC-114t` 的工程师**未获授权擅自修改上游只读册** `spec/DADAO-12`、`spec/DADAO-22`（各插入 2 行）事故。用户 2026-10-07 裁定「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」；本规范把该纪律落为**机械门控**（哈希锁）+ **三处固定检查**（下发 / 验收 / 提交）。
> **关键词**：本规范用「**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）」表达规范性等级。§1–§5 均标 **MUST**。

---

## 1. 上游只读册只作只读引用（MUST）

任务书「输出」**不得**把上游只读册（清单见 §6）列为**可改对象**：对上游册只作**只读引用**——引其 `§` 章节号，**不改一字**。需要的新正文一律落 **v5 自定册**（`spec/Machine-*`、`spec/Process-*` 等）。

## 2. 任何 `spec/` 改动须用户事先明确允许（MUST）

`spec/` 目录下**任何新增 / 修改 / 删除**——含 v5 自定册（`spec/Machine-*`、`spec/Process-*`）与 `spec/README.md`——**必须**先取得用户**事先**明确允许，并在任务书 / 审阅记录中**留存授权原话**（子会话问答对父会话不可见，见 `.tao/knowledge/lessons.md §7.3`）。**未获授权而拟改 `spec/` ⇒ BLOCKED**，不得动笔。

> 注：本规则**不止**约束上游只读册——`spec/` 下**任何**册（含 v5 自定册与索引 `spec/README.md`）都须用户事先授权。

## 3. 下发前预检：第 5 项（MUST）

`/dispatch` 前，主会话**必须**把**拟改文件清单 × `spec/` 清单**逐一对照：凡**命中 `spec/`** 而任务书**无用户授权原话**者 ⇒ **BLOCKED**。据此，`AGENTS.md`「下发前预检」由 **4 项扩为 5 项**（新增本项）。

## 4. reviewer / architect 固定检查（MUST）

- **reviewer** 验收与 **architect** 提交前，**必须**固定执行 `git diff --name-only`（提交前为 `git diff --cached --name-only`）并与 `spec/` 清单交叉；
- **有交集而缺用户授权证据** ⇒ **reviewer 判 `Needs Revision` / architect 拒绝提交**。

## 5. 上游只读册哈希锁机制（MUST）

上游只读册以 **`manifests/spec-readonly.lock.toml`** 逐册 `sha256` 锁定，由 **`make check-spec-readonly`** 校验（已纳入 `make check`）。确需修改某只读册（**须先经用户授权**，见 §2）时，**同一变更**内**必须**更新该册 `sha256` 锁 + 在完成区记录授权原话；**未更新锁即改册 ⇒ 门控 FAIL**。

- 锁文件体例：`format = 1` + `policy = "readonly-requires-authorization"` + 每册一条 `[[spec]]`（`path` / `group` / `sha256`）。
- 校验器：`tools/infra/check_spec_readonly.py`——逐册重算 `sha256` 与锁比对；**不符 / 缺失 ⇒ 非零退出**并逐条打印「册 + 期望 / 实际」。

## 6. 上游只读册清单（判据，20 册）

> `sha256` 真源见 `manifests/spec-readonly.lock.toml`（本节只列册与分组，避免双份哈希漂移）。

| group | 册 |
|-------|----|
| `dadao-1x` | `spec/DADAO-11-AEE-应用程序运行环境.md`、`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/DADAO-13-HEE-超管系统运行环境.md` |
| `dadao-2x` | `spec/DADAO-21-ABI-应用程序二进制接口.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`、`spec/DADAO-23-HBI-超管系统二进制接口.md` |
| `simrisc-00..12` | `spec/SimRISC-00-指令系统设计.md` … `spec/SimRISC-12-待定.md`（共 13 册） |
| `toolchain-01` | `spec/Toolchain-01-汇编语言.md` |

> **不在锁内**：`spec/Machine-01`、`spec/Process-0x`、`spec/README.md` 为 **v5 自定册**，其正当修订由 §2 的授权流程把关（哈希锁只覆盖**上游只读册**，其「不该被擅改」可由机械门控判定）。

## 7. 与其它规范的关系

- `spec/Process-03`（ADR）：本规范属**工程过程规范**，不命中 ADR 判据（可逆、单项目、无外部契约），**不立 ADR**、**不承载 ADR 决策**；
- `spec/Process-01`（组件补丁）：组件补丁的机械校验与此无关；
- `AGENTS.md`：本规范落地其「下发前预检」「提交分档与角色」中的 `spec/` 保护要求。
