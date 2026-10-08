# LLVM-063t: DADAO clang target + driver/sysroot（钉子①）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`SPEC-124t`（调用约定契约收口）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/adr/adr-0003-object-abi.md`（`e_machine`/`e_flags`/ELF 形态；`contract-elf.md`）。
  - `.tao/knowledge/contract-abi.md §4/§6`（调用约定；clang ABI 形状来源）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（DataLayout C9 等）。
  - `INFRA-050t` 产出的一次构建（`clang`/`llc`/`ld.lld`）。
  - 只读对照（**内容溯源，非执行依赖**）：RISC-V64 形状 + PPC64BE 端序/DataLayout + AArch64 调用约定。
- **输出**：
  1. `components/clang-project`/`components/llvm-project/patches/clang/**`：DADAO clang target——`clang/lib/Basic/Targets/**`（`TargetInfo`：DataLayout/端序/`__dadao__` 宏/类型宽度）、`clang/lib/Driver/**`（driver 名/`--target`/默认 `-march`）、**sysroot** 约定（`ADR-0016` 布局）。
  2. **只用于 freestanding**（无 libc/OS/syscall；`-ffreestanding` 语义为主）。
  3. 与 `clang` 一并入一次构建（`INFRA-050t` 目标产出）。
- **约束**：
  - 模板 = **RISC-V64 形状 + PPC64BE 端序/DataLayout + AArch64 CC**；**不**复制 RISC-V 的 ABI 细节（v5 有自己的 ABI）。
  - **`spec/` 交集为空**。
  - 与 Wave 2 其它任务**同改 `components/llvm-project/patches` ⇒ 串行**。
  - 不改 `LLVM` 数据流以外内容；期望值/校验来自 `contracts/`/`.tao/knowledge/`。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-063t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-063t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/**/patches/**` ⇒ 开工前写明「重建 clang（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-063t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **clang target 生效**：`clang --target=dadao-unknown-elf -c`（freestanding）对最小 C 源产出 DADAO 目标文件（给真实命令 + 输出 + `readelf` 证据：`e_machine`/端序）。
2. **DataLayout/端序**：生成对象/IR 与 `contract-abi.md §4.9` 的 DataLayout（大端 `E`）一致（给真实输出）。
3. **driver/sysroot**：`--target`/`-ffreestanding`/`-isystem`（sysroot）按 `ADR-0016` 布局解析（给真实输出）。
4. **无 libc 依赖**：`clang` 可编最小程序且**不**隐式引入 libc/syscall（给证据）。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-063t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
