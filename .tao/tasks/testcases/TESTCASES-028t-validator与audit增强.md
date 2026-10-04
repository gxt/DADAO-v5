# TESTCASES-028t: validator/audit 增强（br 双路径守卫、overlap 语义门控、009t-audit id 修正）

**模块**：testcases
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 3 条无依赖的 testcases 门控 issue（纯 Python，无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-025 | `br.*` 双路径（taken + not-taken）覆盖无结构性守卫 |
| ISS-097 | `class: overlap` 同组用例缺语义门控（覆盖≠语义再现） |
| ISS-099 | `tools/testcases/009t-audit.py` 对 `ctrl-ret` 全部 skip（旧 id `ret-riii` 应为 `ret_riii_ra`） |

`resolved_by`：本任务 `TESTCASES-028t`。

## 接口规范

- **输入**（已核实）：
  - `tools/testcases/validate_vectors.py`：`ctrl-br` 仅在注释中提及 taken/not-taken（L387-388），无结构性守卫；`cls in ("boundary","overlap")` 分支（L425-431）未对 overlap 组重算区间交集。
  - `tools/testcases/009t-audit.py:880`：`insn == "ret-riii"`，而 `contracts/opcodes.yaml` 中 `ret` 的 id 为 `ret_riii_ra` ⇒ ctrl-ret 全部 skip。
  - 向量真源：`tests/vectors/isa/*.yaml`、`tests/vectors/inventory.md`、`contracts/opcodes.yaml`。
- **输出**：`validate_vectors.py` 增强 + `009t-audit.py` id 修正。
- **约束**：
  - ISS-025：守卫须为**结构性**（如：同一 `br.*` 指令须同时存在 taken 与非 taken 两类用例；删任一条 ⇒ 报错），不得依赖注释或文本。
  - ISS-097：按 word 的 `hb/hc/immu6`（`{start:end}` 区间）**重算交集**；有交集且 `expected_fault != ILLI` ⇒ 报错（纯结构、可机械执行）。区间语义以 `contract-isa.md` / `contracts/legality_rules.yaml::mreg_range_overlap` 为准。
  - ISS-099：只改 id 匹配（或为 `ctrl-ret` 加专用重算），**不得**降低 audit 覆盖。
  - 期望值来源必须独立（Spec-first），不得从 LLVM/QEMU 反推。

## 验收标准

1. **ISS-025**：从 `tests/vectors/isa/` 副本删除某 `br.*` 的 taken（或 not-taken）用例 → `validate_vectors.py` **EXIT≠0** 且报该指令双路径缺失；还原 → EXIT=0。
2. **ISS-097**：在副本构造一条 `class: overlap` 且区间相交但 `expected_fault: null` 的用例 → 报错（EXIT≠0）；改回 `expected_fault: ILLI`（或不交叠）→ EXIT=0。给出真实输出。
3. **ISS-099**：修后 `009t-audit.py` 对 `ctrl-ret` 的 `ret_riii_ra` 用例**不再全 skip**（报告实际核算条数 > 0）；修正运行 `git grep "ret-riii"` → 0 命中。
4. **反例门控**：以上每条断言均须给出「注入→FAIL→还原→PASS」的真实输出；不得有恒真/`check(name, True)` 式断言。
5. `validate_vectors` 全量 EXIT=0（含 0 gaps）；`make check` EXIT=0。改动若触及 `tests/vectors/`（新增用例），须同时满足数据类任务的**独立全量重算**要求（不抽样）。

## 硬约束

- 临时目录 `/tmp/opencode/TESTCASES-028t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/testcases/TESTCASES-028t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/TESTCASES-028t/`，可复用检查器落 `tools/testcases/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
