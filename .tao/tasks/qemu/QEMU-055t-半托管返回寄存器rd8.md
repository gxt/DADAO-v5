# QEMU-055t: 半托管/SEE 返回寄存器 `rd31 → rd8`（实现 + 探针重派生重验）

**模块**：qemu
**项目里程碑**：M6
**依赖**：`SPEC-126t`（Spec-first：契约/规范先行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「统一为 rd8」**（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**（用户既定）。

## 变更边界（两个独立变更，**分别验收**）

- **本任务 = 「系统调用/半托管返回」域的实现侧**（半托管 `rd31 → rd8`）。**不涉**「函数返回」域（`rd8/K=8`，`SPEC-124t` 的 ABI，实现归 `LLVM-062t`）。
- 两者**独立**、**分别验收**；不得以函数返回改动为由跳过本域的半托管返回校验。

## 接口规范

- **输入**：
  - `SPEC-126t`（服务返回寄存器 `rd8` 的规范/契约结论；`.tao/knowledge/contract-semihosting.md §2/§4`、`contract-see §5`）。
  - `components/qemu/patches/target/dadao/common-semi-target.c.patch`（现 `#define DADAO_SEMI_RET_REG 31`，及头注释 `rd31 = scalar return`）。
  - `spec/Machine-01-测试机运行环境.md §5.2/§5.4`（semihosting 返回）。
  - `tools/qemu/min_rom_probe_046t.py`（25 服务 semihosting 探针，期望值多以 `rd31` 承服务返回）；其余 `tools/qemu/min_rom_probe_*.py`。
- **输出**：
  1. `common-semi-target.c.patch`：`DADAO_SEMI_RET_REG` **31 → 8**（`common_semi_set_ret()` 写 `rd8`），并同步头注释中的返回寄存器措辞（引 `Machine-01 §5.2`/`contract-semihosting`）。
  2. `tools/qemu/min_rom_probe_046t.py`：**服务返回**期望值按 `rd8` 重派生并重验；「返回落 `rd31`」用例改为「返回落 `rd8`（且 `rd31` 不被改）」。
  3. 其余探针：**逐条分类**（`rd31` 作**中间暂存**者**不改**，仅服务返回者改），分类表入完成区。
  4. 重跑相关探针 + 门控，给真实输出与退出码。
- **约束**：
  - **只改半托管服务返回**：`DADAO_SEMI_RET_REG` 及读服务返回处；**不改** `DADAO_SEMI_NUM_REG`（`rd16` 服务号）/`DADAO_SEMI_ARG_REG`（`rb16`）等**入参**映射；**不改**以 `rd31` 作通用暂存的用法（`rd31` 仍为通用 temp）。
  - **不改 `spec/`**（`git diff --name-only | grep -E '^spec/'` 无输出）；规范侧归 `SPEC-126t`。
  - **重建成本申报**：改 `components/qemu/patches/**` ⇒ 开工前写明「重建 QEMU（增量），预计 N 分钟」；一次构建、勿零散重跑。
  - `series`/`changelog.md` 随任务追加（`Process-01`）。
  - **门控保持全绿**，不回归。

## 硬约束

- **临时目录** `/tmp/opencode/QEMU-055t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/QEMU-055t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据；**还原须含重建**（源码还原 ≠ 二进制还原）。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/qemu/QEMU-055t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **实现改毕**：`common-semi-target.c.patch` 中 `DADAO_SEMI_RET_REG == 8`，`common_semi_set_ret` 写 `rd8`（给 grep 真实输出）；`rd16`/`rb16` 入参映射**逐条未变**。
2. **探针重派生**：`min_rom_probe_046t.py` 服务返回期望值按 `rd8` 重派生并**重跑通过**（给真实输出与退出码）；「返回落 `rd8`、`rd31` 未被改」用例存在。
3. **逐条分类**：其余探针的 `rd31` 命中**逐条**分类（改 / 不改 + 理由）；暂存用法**不改**。
4. **不回归**：`make check`/`check-qemu-semantics`/`check-patch-tree` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/QEMU-055t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `DADAO_SEMI_RET_REG` 改回 `31` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 + **重建** ⇒ 回绿）。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
