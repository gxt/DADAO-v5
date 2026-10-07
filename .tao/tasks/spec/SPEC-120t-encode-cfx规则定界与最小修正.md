# SPEC-120t: `encode_cfx` 规则定界与最小修正（汇编/编码层不应含实现期语义）

**模块**：spec
**项目里程碑**：M5（**architect 判断，列为待用户复核项**：可移 M6/后续，见 §说明）
**依赖**：`SPEC-115t`（**串行**——同涉这 4 条 cfx 与 `LEGALITY` 生成管线）；若调研结论触及 `spec/`，另须 `SPEC-119t` 机制的授权 + 锁同步（见约束）
**状态**：待开始

> **本任务由来（用户裁定 3 原话，2026-10-07，经主会话转达——子会话问答对父会话不可见，见 `lessons §7.3`）**：
> > 「**encode_cfx不应该存在，这个是实现层面的事情，不是汇编或者编码时需要处理的问题，单独建立一个任务解决该问题**」
>
> 本任务即「单独建立」的该任务。**先调研定界，再给最小修正方案**（见 §接口规范）。

## 执行环境
**执行环境**：本地

## 接口规范

- **问题（待调研确认的初步事实，实测）**：
  - `contracts/legality_rules.yaml:198`：规则 `encode_cfx`（`fault: ILLI`、`kind: static`、`status: deferred`、`spec_cite: "SimRISC-11 §寄存器传输指令"`），描述「cfxha 为 reserved 核芯功能扩展（7–14、19–61）时触发 ILLI 异常」。
  - `tools/spec/gen_legality_list.py:50`：`CHAPTER_OF['encode_cfx'] = "编码合法性"`；`:79`：`RULE_SUMMARY['encode_cfx'] = "reserved cfxha → ILLI（deferred）"`。
  - **实测：`encode_cfx` 全仓仅被上述两文件引用**（`grep -rn encode_cfx` 排除 `.tao/`/`.work/`/`.cache/` 后仅此 2 处）；**无任何 `opcodes.yaml` 记录的 `rule_refs` 引用它**（`contracts/opcodes.yaml` 中 `rule_refs` 无 `encode_cfx`）⇒ 它**不进入 `LEGALITY` 段渲染**（`gen_legality_list.py::build_rule_to_chapters` 按 `rule_refs` 建档，`deferred` 且 0 引用不进任何章）。
  - **判断**：该规则把「**执行期** reserved cfx 访问 ⇒ ILLI」（`SimRISC-11 L121`）错误地登记为**静态编码合法性**（`kind: static`）规则。汇编/编码期，reserved `cfxha`（7–14、19–61）仍在 6 位字段内**可编码**，不构成编码非法；ILLI 属**实现/运行期**语义。故用户裁定其「不应存在于汇编/编码层」。
- **输入（自包含）**：
  - `contracts/legality_rules.yaml`（`encode_cfx`，L198 起）；`tools/spec/gen_legality_list.py`（L50/L79）。
  - 门控：`tools/spec/check_rule_refs.py`（orphan/exempt 自检）、`tools/spec/check_legality_drift.py`（`spec/` 各册 `LEGALITY` 生成区精确比对）、`make check-spec-refs`（**若**规范正文引用该规则）。
  - `.tao/knowledge/contract-isa.md`（§7.5「特权 cfx 指令属 M1 范围外」——该规则的描述指针）；`spec/SimRISC-11-其它.md`（`§寄存器传输指令`/`§特权指令`；`LEGALITY` 段为**生成区**）。
  - `spec/Process-02-合约编写规范.md`（规则 `kind`/`status` 口径）、`spec/Process-05`（TDD）、`spec/Process-06`（**`spec/` 改动须用户事先授权**）。
  - 同类对照（只读）：编码期可判定约束的既有规则（如 `encode_sbz`、`dst_rd0`、`mreg_*`）——均为**编码/结构期**可判定；`encode_cfx` 格格不入。
- **输出**：
  1. **调研定界（先做，必须先于任何改动落纸）**：逐项核——① `encode_cfx` 的**全部引用点**（实测 2 处 + `rule_refs` 0）；② 它是否影响**任何** `spec/*` 的 `LEGALITY` 渲染（实测：否，因 0 引用）；③ 其在 `check_rule_refs.py` 的 **orphan 豁免清单**中的关系（`deferred` 非 `active`，应不在 `EXPECTED_ORPHAN_EXEMPTIONS`）；④ 它与 `SimRISC-11 L121`（执行期 reserved ⇒ ILLI）语义的重叠；⑤ `status: deferred` 是否仍有任何挂靠。**结论写入完成区**。
  2. **最小修正方案（据调研选择，写清取舍）**：
     - **候选 A（倾向）**：**删除** `encode_cfx` 规则（`contracts/legality_rules.yaml`）+ 从 `gen_legality_list.py` 移除 `CHAPTER_OF['encode_cfx']`/`RULE_SUMMARY['encode_cfx']` + **重跑 `gen_legality_list.py`**；因 0 引用 ⇒ `spec/*` 渲染**无变化** ⇒ `check-legality-drift` 保持绿（**不触 `spec/`** ⇒ **无需**用户授权/锁更新）。
     - **候选 B（备用）**：若调研发现该语义确需在规范层保留，则**不删**，改为明确标注「**运行期/实现层**语义、**非**汇编/编码期 legality」（口径落 `spec/` 或投影），并同步生成器。**B 若触 `spec/` ⇒ 先取用户授权（原话落盘）+ 同变更更新 `manifests/spec-readonly.lock.toml`**（`SPEC-119t`/`Process-06`）。
     - **不得**保留「half」：既称 `static` 编码合法性又不进任何渲染/引用。
  3. **投影/门控对齐**：`check_rule_refs.py`/`check_legality_drift.py`/`check-spec-refs`/`make check` 全绿；`contract-isa.md §7.5` 若含对 `encode_cfx` 的指针则同步措辞。
  4. **一键证据脚本**：`.work/evidence/SPEC-120t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（如「恢复 `encode_cfx` 规则 / 恢复 `RULE_SUMMARY` 条目 ⇒ 断言 FAIL ⇒ 还原 ⇒ 回绿」），结尾**禁 `tee`**。
- **约束（硬）**：
  - **先调研、后决策、再落地**；调研结论与所选候选（A/B）须写入完成区并给依据。
  - **最小改动**：只处置 `encode_cfx` 及其生成器条目；**不动**其它规则、不动 4 条 cfx 的 `rule_refs`（`SPEC-115t` 已定 `[]`）。
  - **不触 `spec/`**（除非候选 B 且经用户授权）：`spec/` 改动须用户**事先**允许 + 授权原话落盘 + 同变更更新 `spec-readonly` 锁（`Process-06`/`SPEC-119t`）。
  - 与 `SPEC-115t`/其它改 `spec/`·`contracts/` 的任务**串行**。
  - `make check` EXIT=0；失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-120t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **调研定界落纸**：完成区含 `encode_cfx` 的引用点清单（全仓 `grep` 真实输出）、`rule_refs` 0 引用证据、orphan 豁免清单关系、`SimRISC-11 L121` 对照、`status: deferred` 挂靠核查。
2. **最小修正落地**：候选 A 或 B 已落地（给真实 `git diff`）；所选候选与理由写入完成区。
3. **门控**：`python3 tools/spec/check_rule_refs.py` / `check_legality_drift.py` / `make check` EXIT=0（给真实输出/退出码，**禁 `tee`**）。
4. **渲染无回归**（候选 A 期望）：`check-legality-drift` EXIT=0 且 `git status --untracked-files=all` **不含** `spec/SimRISC-*.md`（若不含则证「0 引用 ⇒ 无渲染变化」）。
5. **一键证据脚本**：`.work/evidence/SPEC-120t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（恢复规则/生成器条目 ⇒ FAIL ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
6. **无残留**：`git status --untracked-files=all` 仅 `contracts/legality_rules.yaml`（+ 候选 B 时的 `spec/` 册与锁）+ `tools/spec/gen_legality_list.py` + `.tao/knowledge/contract-*.md`（如需）+ 本任务书。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### architect 立项（2026-10-07，用户裁定 3）
**用户原话（落盘）**：
> 「**encode_cfx不应该存在，这个是实现层面的事情，不是汇编或者编码时需要处理的问题，单独建立一个任务解决该问题**」

**立项要点**：编号按 spec 模块现状顺延（`SPEC-119t` → **`SPEC-120t`**）；`**项目里程碑** = M5`（**architect 判断，待用户复核**，理由见 §说明）；依赖 `SPEC-115t`（串行，同涉案 4 条 cfx 与 `LEGALITY` 生成管线）；**先调研定界、再最小修正**；默认候选 A（删除，不触 `spec/`），候选 B（保留并降级为运行期口径）为备用。

## 说明

**`**项目里程碑** = M5` 的判断理由（architect，列为待用户复核项）**：

- `encode_cfx` 与 `SPEC-115t` 处置的是**同一族**（4 条 cfx）与**同一条 `LEGALITY` 生成管线**（`opcodes.yaml` 的 `rule_refs` ↔ `legality_rules.yaml` ↔ `gen_legality_list.py` 渲染）；`SPEC-115t` 把 4 条 re-scope 为「已实现」并以 `rule_refs: []` 收口后，若仍留一条 `deferred` 的 `encode_cfx`（且措辞为「reserved cfxha → ILLI」），M5 spec 层口径**内部不一致**（已实现 cfx vs 规则称 cfx 触发 ILLI）。
- 归 M5 且**串在 `SPEC-115t` 之后**，可复用其对 4 条 cfx/`LEGALITY` 的上下文，避免 M6 重新捡起同一 region。
- **备选（待用户复核）**：若判其**不在 M5 功能门槛路径**上（确非 `make test-semihost` 所需），可**移 M6/后续**——则本任务书 `**项目里程碑**` 改 `M6`，并从 `INTEG-019k` 任务表/`SPEC-118m` 关联任务中撤出。
