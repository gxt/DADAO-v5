# SPEC-103t: spec 门控脚本小修（--verify 退出码、gate2 死分支、正文代码块门控、root n=2 门控）

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 4 条无依赖的 spec 门控 issue（纯 Python，无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-122 | `tools/spec/gen_legality_list.py --verify` 检出 MISMATCH 时须非零退出 |
| ISS-123 | `tools/spec/check_rule_refs.py` 的 `gate2_fail` 分支不可达 |
| ISS-077 | spec 正文代码块正确性接入永久门控（现仅任务级 reviewer 脚本） |
| ISS-079 | `ftroot`/`foroot` n=2 约束与规则改名缺机械门控 |

`resolved_by`：本任务 `SPEC-103t`。

## 接口规范

- **输入**（脚本现状，已核实）：
  - `gen_legality_list.py:329-336`：`--verify` 分支打印 `OK/MISMATCH` 后**恒 `return 0`**（MISMATCH 也返回 0）。
  - `check_rule_refs.py:63-94`：`gate2_fail` 置位后由 `if gate1_fail or gate2_fail:` 统一失败；但存在「豁免自检先行退出」路径使 `gate2_fail` 不可达。
  - `check_asm_prose.py`：仅检**旧格式**违规（ADR-0013），**不**逐行比对生成表 ⇒ 新格式正文块无永久门控。
  - `gen_legality_list.py:51/80`：`encode_fp_root_n = "ftroot/foroot n≠2 → ILLI"` 为 `RULE_SUMMARY` 文案；`SPEC-067t` F4 的 n=2 约束与规则改名无独立机械门控。
- **输出**：修订后的 4 个 checker（含新增/抽取的公共检查），并接入 `make check`（若尚未接入）。
- **约束**：
  - ISS-122：仅改 `--verify` 退出行为；**不得**改变 `--apply`/默认渲染输出。
  - ISS-123：要么**删除**不可达分支（精简），要么**使其可达**；不得留下无断言价值的死代码。
  - ISS-077：新增门控须以 `contracts/opcodes.yaml`（经 `tools/llvm/gen_asm_list.py` / 生成表）为唯一真源；伪指令行需**例外表**（用户/规范确认的伪指令 `return` 等），不得硬编码全表。**若评估后认为成本高于收益，须给出评估结论并登记 deferred（不静默跳过）。**
  - ISS-079：门控须覆盖「`ftroot`/`foroot` 的 `immu6 != 2 ⇒ ILLI`」与「规则改名（新 id 生效、旧 id 0 命中）」，来源 `contracts/legality_rules.yaml` + `opcodes.yaml`。
  - 一切检查器须**可失败**（见验收 5）。
  - 若新增脚本，落 `tools/spec/` 并随产物入库；同时更新 `spec/README.md` 或对应 Makefile 目标（按最小改动）。

## 验收标准

1. **ISS-122**：构造 LEGALITY 区与期望不符的临时 fixture，`gen_legality_list.py --verify` → **EXIT≠0** 且 stdout/stderr 含 `MISMATCH`；一致时 EXIT=0。还原。
2. **ISS-123**：`check_rule_refs.py` 对孤儿 `rule_refs`（引用不存在的规则）报 FAIL（EXIT≠0）；对合法输入 EXIT=0。若选择删除死分支，须在完成区给出「删除前不可达」的证据（逐行说明）。
3. **ISS-077**：新门控对「正文 ```simrisc 块某行汇编格式/助记符错误」报 FAIL（EXIT≠0）；对当前仓库正文 EXIT=0。给出**至少 1 条可失败断言**的真实注入输出。
4. **ISS-079**：注入「`ftroot` 的 `immu6` 由 2 改为 3 且未标 ILLI」或「规则旧 id 复活」→ 门控 FAIL；还原 → 全绿。
5. **反例门控（逐脚本）**：每个新增/修改的 checker 都须有可达 FAIL 路径；不得出现「两支写同一结果」「断言恒真」。给出注入→FAIL→还原→PASS 的真实输出。
6. `make check` EXIT=0（新增 checker 接入后）；`make check-rule-refs`、`make check-legality-drift` 仍全绿。

## 硬约束

- 临时目录 `/tmp/opencode/SPEC-103t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/spec/SPEC-103t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/SPEC-103t/`，可复用检查器落 `tools/spec/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
