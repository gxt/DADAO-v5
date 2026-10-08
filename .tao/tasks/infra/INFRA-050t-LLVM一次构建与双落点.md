# INFRA-050t: LLVM 一次构建与双落点

**模块**：infra
**项目里程碑**：M6
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `Makefile`（现 `build-mc`/`install-host` 等目标；构建变量与 install 布局以**实测**为准）。
  - `.tao/adr/adr-0016-dadao-install-layout.md`（install 落点 `D1–D11`；安装根 `.dadao/`）。
  - `manifests/components.lock.toml`（`llvm-project` 精确 commit，`ADR-0006`）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（构建编排约束）。
- **输出**：
  1. `Makefile`：一次构建 `LLVM_TARGETS_TO_BUILD="DADAO;X86"`，产出 **`clang`/`llc`/`ld.lld`/`lli`**（`lli` 为 host 工具，走 X86 back-end）；**一次构建、双落点**：
     - 交叉工具链 → `.dadao/cross-toolchain/bin/`（`clang`/`llc`/`ld.lld`；
     - host `lli` → `.dadao/host-tools/bin/`（可作为**可选**落点；若采纳须在完成区给实测路径）。
  2. `install-dirs`/install 规则同步（`ADR-0016` 布局）。
- **约束**：
  - **一次构建**（不重复全量 configure/build）；`JOBS` 受限（默认 8），**禁** `-j$(nproc)`。
  - **不改组件补丁语义**（本任务只编排构建/落点，不动 `components/llvm-project/patches/**` 的指令/编码内容）。
  - 交叉工具链与 host 工具**同源同 commit**（`manifests/components.lock.toml`）。
  - `DADAO;X86` 双 target 是「`lli` 值级 oracle」（`TESTCASES-038t`）的前置。

## 硬约束

- **临时目录** `/tmp/opencode/INFRA-050t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**（涉 `components/**` 者）：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/INFRA-050t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：本任务即一次构建立项，开工前写明「构建 LLVM（`DADAO;X86`），预计 N 分钟」；**一次构建、勿零散重跑**。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/infra/INFRA-050t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **一次构建产出四工具**：构建目标 EXIT=0；`clang`/`llc`/`ld.lld`/`lli` **均存在且可执行**（给 `ls -l` 与逐工具 `--version`/`-help` 的真实输出）。
2. **双落点**：`.dadao/cross-toolchain/bin/{clang,llc,ld.lld}` 存在；host `lli` 落点（`.dadao/host-tools/bin/lli` 或实测等价）存在（给实测路径 + `ls -l`）。
3. **同源**：四工具来自同一 commit（对照 `manifests/components.lock.toml`；给证据）。
4. **不回归**：`make check` EXIT=0；`make check-patch-tree` EXIT=0。
5. **一键证据脚本**：`.work/evidence/INFRA-050t/run.sh` 逐项通过、`RUN_EXIT=0`；**含注入自检**（如把落点变量指向旧路径/移除某工具 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`Makefile`/install 规则 + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

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
