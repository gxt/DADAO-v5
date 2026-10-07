# SPEC-116t: 大小写敏感修订（`Toolchain-01 §2.1` + `contract-asm §2.1`）

**模块**：spec
**项目里程碑**：M5
**依赖**：无（与 `SPEC-113t`~`115t`/`117t` 同改 `spec/` ⇒ **串行**）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **背景**：`spec/Toolchain-01-汇编语言.md §2.1` 与 `.tao/knowledge/contract-asm.md §2.1` 现规定「助记符与寄存器名**大小写不敏感**（`ADD.SI` ≡ `add.si`）」，但 **LLVM MC 实现为大小写敏感**（`ADD.UO {RD8…}` 报错；`ISS-157`；`TESTCASES-029t` F3/`新发现`）。**用户裁定（`INTEG-019k D16`）：改为大小写敏感，撤销「不敏感」条款** ⇒ `ISS-157` 以「**条款撤销**」结案（**不是**"实现缺口"）。
- **输入（自包含）**：
  - `spec/Toolchain-01-汇编语言.md §2.1`（现行「大小写不敏感」句）。
  - `.tao/knowledge/contract-asm.md §2.1`（同款投影句，含 `[Toolchain-01 §2.1]` 引用）。
  - `.tao/knowledge/contract-asm-list.md`（生成投影，助记符列——大小写范式须一致）。
  - `.tao/knowledge/issues.yaml` 的 `ISS-157`（`scope: [llvm, spec]`）。
  - 门控：`tools/spec/check_asm_prose.py`、`check_asm_list_consistency.py`、`check_asm_list_drift.py`；`make check-spec-refs`。
- **输出**：
  1. **`spec/Toolchain-01 §2.1`**：把「助记符与寄存器名大小写不敏感（`ADD.SI` ≡ `add.si`）」**撤销/改写为大小写敏感**（明确措辞：助记符、寄存器名、伪指令、指导符等**区分大小写**；规范书写范式为**小写**；仅规范文档在**叙述**中大写属示例，不构成等价形式）。**撤销**须显式（非新增），保留变更痕迹（rev 说明/变更记录节）。
  2. **`contract-asm.md §2.1`**：同步撤销 `[Toolchain-01 §2.1]` 投影句为大小写敏感；版本号/来源标注同步（如 `§附：与上游 spec/ 的关系` 处记 rev）。
  3. **投影/门控对齐**：`contract-asm-list.md` 助记符大小写范式与规范一致；`check-asm-prose`/`check-asm-list*`/`check-spec-refs` 绿。
  4. **`ISS-157` 结案**：`.tao/knowledge/issues.yaml` `ISS-157` → `status: closed`、`resolved_by: SPEC-116t`、`notes` 记「**以「条款撤销」结案**（撤销「大小写不敏感」条款，非实现缺口）」。
- **约束（硬）**：
  - **只改大小写条款及其投影/结案**；不动其它语法条款语义。
  - **撤销**措辞明确（撤销 ≠ 新增）；**不引入**大小写不敏感的实现工作（`LLVM` 侧不因此改；`ISS-157` 以条款撤销结案，**不是**留作实现缺口）。
  - `spec/`/`.tao/knowledge/` 为共享文件，与 `SPEC-113t`~`115t`/`117t` **串行**。
  - `make check`（含 `check-asm-prose`/`check-spec-refs`）EXIT=0。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-116t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **条款撤销**：`grep -n "大小写" spec/Toolchain-01-汇编语言.md .tao/knowledge/contract-asm.md` 显示二处均为**大小写敏感**口径，「不敏感」句已撤（给真实输出）。
2. **投影/门控**：`make check` EXIT=0（`check-asm-prose`/`check-asm-list-*`/`check-spec-refs` 均绿）；给真实输出。
3. **结案**：`issues.yaml` `ISS-157` `status: closed`、`resolved_by: SPEC-116t`、`notes` 含「条款撤销」（给真实片段）。
4. **一键证据脚本**：`.work/evidence/SPEC-116t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（把条款改回「不敏感」⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
5. **无残留**：`git status --untracked-files=all` 仅 `spec/Toolchain-01-汇编语言.md` + `.tao/knowledge/contract-asm.md`（+ 必要的 `contract-asm-list.md`）+ `.tao/knowledge/issues.yaml` + 本任务书。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 核「撤销」措辞与结案 + 判决）
