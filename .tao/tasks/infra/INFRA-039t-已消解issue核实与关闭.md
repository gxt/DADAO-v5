# INFRA-039t: 已消解（代码已修）issue 核实与关闭

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（**无需**组件重建：核实 + 台账 `issues.yaml` 状态收口）

## 目标与 resolved_by

主会话初筛将下列 issue 视为待修，但**架构核实发现仓库中已由后续任务修复**。本任务**独立复核**（重跑/重算`不以 git log 叙述为准`），确认已消解则置 `closed`，否则**保持 open 并报告**。预期关闭：

| ISS | 声称的修复来源（须独立复核） |
| --- | --- |
| ISS-013 | `fetch.py::select_source()` 现返回 `(url, label)`（SPEC-085t 后） |
| ISS-023 | `validate_vectors.py` 已加 F10④b（rbha 为 dst 时 =0 报错；TESTCASES-019t） |
| ISS-041 | 4 个 LLVM 补丁无 `No newline at end of file`（源文件含末尾换行） |
| ISS-046 | `DecodeGPRFRegisterClass` 因 FP 指令入 MC（LLVM-029t）而不再 unused |
| ISS-049 | 3 个 QEMU 补丁无 `No newline at end of file` |
| ISS-067 | `check_qemu_trans.py::collect_trans_defs()` 已 `skip '-'` 行 |
| ISS-069 | `tools/qemu/check_harness_ops.py` 已存在（harness op ↔ opcodes.yaml 交叉校验） |
| ISS-100 | `tests/vectors/isa/ctrl-ret.yaml` 已含 `dst_rd0_nonzero` ILLI 用例（TESTCASES-022t） |
| ISS-109 | `DADAOMCAsmInfo.cpp` 已 `AllowAdditionalComments = false`（LLVM-025t），`Toolchain-01` L205 已文档化 |
| ISS-112 | `check_interface_alignment.py` 三处 patch 读取统一走 `iter_patch_files`（无残留 isdir 守卫） |
| ISS-114 | `tools/infra/test_spec_drift_fixtures.py` 已提供 4 类真实缺陷 fixture 负测试 |
| ISS-115 | `gen_asm_list.py --plain` 无 `--output` 时输出 stdout（实测） |
| ISS-116 | `validate_encoding.py` 的 `ALLOWED_NON_FIELD` 已含 `no_overlap`（实测 EXIT=0） |
| ISS-124 | 立即数范围通用说明已落位 `contract-asm.md` + `Toolchain-01 §2.4` + `contract-asm-list.md`「立即数范围速查」（SPEC-085t）；须判断是否满足 SPEC-070t 的规范侧收口 |

`resolved_by`：逐条填写**实际修复任务**（如 `TESTCASES-019t`/`LLVM-025t`/`INTEG-008t`/`SPEC-085t`）；无法归因时填本任务 `INFRA-039t`。

## 接口规范

- **输入**：`.tao/knowledge/issues.yaml`（上述 14 条 open 项）；各条目关联的源文件/脚本/向量。
- **输出**：
  - 每条 issue 的**独立复核证据**（命令 + 输出 + 退出码）；
  - 确认已消解者：`issues.yaml` 中改 `status: open → closed`、填 `resolved_by`、可保留/精简 `notes`；
  - 未能复现「已消解」者：**保持 open** 并在完成区列明反证。
- **约束**：
  - **独立复核**：不得仅凭 git log/任务书叙述；须**重跑命令或重算**（如 `git hash-object`/grep/脚本运行）。
  - 只改 `issues.yaml` 的 `status`/`resolved_by`/`notes` 字段，**不删条目、不改 title/scope**。
  - **例外**：若发现某条确有未修的子问题（如 ISS-046 若实测仍 unused），**不得关闭**，转「遗留问题」并建议另立/并入任务。
  - 关闭后 `tools/infra/check_issues.py` 须无 INVALID STATUS。
  - 不触碰 `.tao/archive/**`。

## 验收标准

1. 对 14 条逐条给出**可复现命令 + 真实输出 + 退出码**（一条一段），并明确 `已消解 / 未消解`。
2. 反例思路：对至少 3 条做「注入→检出」证明其承重（如把 `select_source` 返回值改回单值、或删 `no_overlap` 白名单 → 对应检查/断言 FAIL；还原）。
3. `python3 tools/infra/check_issues.py` **EXIT=0**，且 open 数 = 初筛数 − 实际关闭数；闭合条目 `status: closed` 且 `resolved_by` 非空。
4. `git diff .tao/knowledge/issues.yaml` 仅含上述字段变更（逐行核对）。
5. 完成区给出「最终 open/closed 计数」与「未消解项清单」。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-039t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件（`issues.yaml`），越界须披露。
- 复杂命令输出留存 `.work/log/infra/INFRA-039t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-039t/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
