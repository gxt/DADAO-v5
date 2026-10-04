# INFRA-037t: infra/integ 工具与文档小修（asm-prose stdout、build-mc help、LLVM 补丁计数）

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 3 条无依赖的工具/文档小修 issue（纯 Python/文本，无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-094 | `tools/spec/check_asm_prose.py` 域外场景 stdout 仍打 PASS（rc=1 但 stdout 语义不一致） |
| ISS-132 | `Makefile` 的 `build-mc` help 文本仍写 "LLVM MC tools"，未提 `llc` |
| ISS-133 | `components/llvm-project/README.md` 补丁数 36 陈旧（LLVM-033t 后实为 45） |

`resolved_by`：本任务 `INFRA-037t`。

## 接口规范

- **输入**（已核实）：
  - `tools/spec/check_asm_prose.py:734-771`：`--files` 有域外文件时 `had_out_of_scope=True`，但 `report()`（L682）在 0 violations 时先打印 `check-asm-prose: PASS (0 violations)`，随后才 `sys.exit(1)` ⇒ stdout 与退出码语义不一致。
  - `Makefile:65/67`：`make build-mc` / `build-mc-reconfig` 的 help 文案。
  - `components/llvm-project/README.md:9`：`规模（2026-09-23 M1 重整后）：**36 份** = 新增 32 + 修改 4。`
- **输出**：修正后的 `check_asm_prose.py`、`Makefile`、`components/llvm-project/README.md`。
- **约束**：
  - ISS-094：`had_out_of_scope` 时 stdout 须打 `FAIL (out-of-scope --files)`，不得再打 `PASS`；正常 0 violations 仍打 PASS。
  - ISS-132：help 文案须与 `LLVM_MC_FULL_TARGETS`（已含 `llc`，见 `INFRA-035t`）一致，最小改动。
  - ISS-133：README 补丁数**由命令推导、不得手写猜测**：总数 = `find components/llvm-project/patches -name '*.patch' | wc -l`；`新增/修改` = 按各 patch 是否含 `new file mode` 统计（或在 README 中改为「总数」单一表述，避免易腐化）。**保留** `2026-09-23 M1 重整后` 语义的历史数字时可另起一行注明最新值，不得抹掉历史。

## 验收标准

1. **ISS-094**：构造域外 `--files` 输入 → **EXIT≠0 且 stdout 不含 `PASS`**、含 `out-of-scope`/`FAIL`；正常扫描 0 violations → EXIT=0 且 stdout 含 PASS。给出真实输出。
2. **ISS-132**：`grep -n "LLVM MC tools" Makefile` → 0 命中；`make help`（或对应 echo）输出含 `llc`。
3. **ISS-133**：README 补丁数 == `find components/llvm-project/patches -name '*.patch' | wc -l`（当前 45），且 `新增`/`修改` 之和等于总数（给出统计命令与输出）。
4. **反例门控**：把 README 数字改回 36（临时副本）⇒ 验收 3 的比对 FAIL；还原。把 `check_asm_prose` 的域外分支改回打 PASS ⇒ 验收 1 FAIL；还原。
5. 改动落在门控覆盖范围（`Makefile`、`tools/**`）时 `make check` EXIT=0；`components/llvm-project/README.md` 属文档，不作为门控阻断项。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-037t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/infra/INFRA-037t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-037t/`，可复用检查器落 `tools/infra/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
