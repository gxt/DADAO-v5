# LLVM-046t: InstrInfo 生成器/校验器刷新（陈旧、非真源）

**模块**：llvm
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（**无需**组件重建：纯 Python 工具刷新）

## 目标与 resolved_by

处理 1 条无依赖的 LLVM 工具债 issue（纯 Python，改动不参与 LLVM 编译）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-103 | `tools/llvm/generate_instrinfo.py` / `validate_instrinfo.py` 陈旧、非真源（命名漂移 + 基线过期，`EXIT≠0`，均不在 `make check`） |

`resolved_by`：本任务 `LLVM-046t`。

## 接口规范

- **输入**（已核实）：
  - `tools/llvm/validate_instrinfo.py` 头注释：`1. 178 M1 instruction defs exist (no more, no fewer)`；Check 2 命名漂移（`.td` 用 `.` vs `opcodes.yaml` 用 `_`）。
  - 真源变化：`contracts/opcodes.yaml` 现 **228** 条（`scope: m1` = 152；`fp` 60；`excluded` 15；`m3` 1）；`DADAOInstrInfo.td` + `DADAOInstrInfoFP.td` 现状。
  - 两脚本**均不在** `make check`（`Makefile:224`）。
- **输出**：二选一并执行——
  - **(a) 刷新**：修正命名映射、基线数字；脚本运行 `EXIT=0`；并评估是否接入 `make check`（若接入，须满足可失败门控）；或
  - **(b) 退役**：若判定已被 `generate_opcodes.py` / `validate_encoding.py` / lit 取代，**删除或明确标注为历史脚本**（加 deprecation 头、从 `tools/` 移出或加 guard），并给出理由与替代真源。
- **约束**：
  - **不得**用脚本反推真源；脚本以 `contracts/opcodes.yaml` + `.td` 为真源。
  - 若选择刷新，改动须能对**注入的 .td/opcodes 不一致**失败（见验收 3）。
  - 生成器产物（若脚本产出文件被提交）须随产物保留在非易失位置。

## 验收标准

1. **基线一致**：选择 (a) 时，`python3 tools/llvm/validate_instrinfo.py` **EXIT=0**，且其声明的 M1 def 数与 `grep -c '^- id:' contracts/opcodes.yaml` 的 `scope: m1` 子集一致（给出两命令输出，不再出现 178 类的过期硬编码，或明确由 opcodes.yaml 派生）。
2. **命名对齐**：Check 2 的 `.td`（`.`）与 `opcodes.yaml`（`_`）映射显式定义并有测试；对合法输入 EXIT=0。
3. **反例门控**：在临时副本把某条 `.td`/`opcodes.yaml` 的 mnemonic/op 改错 → 校验器 **EXIT≠0**；还原 → EXIT=0。给出真实输出。
4. **选择 (b)** 时：给出「被谁取代」的逐项对照（`validate_encoding.py` / `generate_opcodes.py` / lit 覆盖点），并确认删除/标注后 `make check` 不回归。
5. `make check` EXIT=0（含新增门控则须全绿）。

## 硬约束

- 临时目录 `/tmp/opencode/LLVM-046t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/llvm/LLVM-046t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/LLVM-046t/`，可复用检查器落 `tools/llvm/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
