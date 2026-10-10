# SPEC-130t: 数据指示符口径（正文 + 锁）【`ISS-181` 拆分-①】

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-129t`（`Toolchain-01` 旧口径消除 + 锁同步，`已验证`）；无硬前置
**状态**：待开始

> **覆盖缺口**：**`ISS-181`** 的**规范正文 + 锁**部分。**说明（拆分）**：`ISS-181` 同时含「规范正文口径」与「工具链实现 + 用例跟改」，体量大且跨模块（spec 只读册 + llvm 后端 + tests）⇒ 按 Spec-first 拆为 **`SPEC-130t`（正文 + 锁，本文件）** + **`LLVM-078t`（工具链生成侧/受理侧 + 用例跟改）**，后者依赖本任务。

## 用户裁定（2026-10-10，经主会话转述的原话/结论，原样落纸）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。其中 **`ISS-181`（数据指示符口径）** 的裁定为：
> - **① 只留 `.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**（`.byte` / `.short` / `.long` / `.quad` / `.word` / `.octa` **全部禁**）。
> - **② 两侧一致**：`llc` **只生成** `.dd.*`，`llvm-mc` **拒绝** GAS 名（**受理侧可行性**归 `LLVM-078t` 评估）。
> - **③ 删 `.align`，只留 `.p2align`**（实测 `.align N` 是**字节数**语义、与 GAS 的 `2^N` 冲突）。
> - **④ 不立 ADR**：改 **v5 侧 `spec/Toolchain-01 §7`** + **`.tao/knowledge/contract-asm.md` 正文** + **同步 `manifests/spec-readonly.lock.toml` 的 `sha256`**；**不动上游 `DADAO-11`**（确需 ⇒ **停下报告**）。
> - **⑤ `.dd.128` 暂不加**（用户保留；如加为小改）。
> - **⑥ 跟改面**：`tests/**`（lit CHECK 行、e2e `.s`、`tests/scripts/*.s`）与 `components/llvm-project/patches/**` 内受影响的 DADAO 侧 directive 串（`DADAOMCAsmInfo`）——**归 `LLVM-078t`**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现状**：`Toolchain-01 §7`（指导符）**只列** 4 条 `.dd.*`（Knuth/MMIX 长度定义），并注明「MUST NOT 使用 GAS 的 `.word`/`.octa`」，但**未显式禁** `.byte/.short/.long/.quad`，也**未涉 `.align`**。而实现侧 `DADAOMCAsmInfo` **未覆盖** data directive 串 ⇒ 继承 `MCAsmInfo` 默认 ⇒ `llc` 生成侧发 `.byte/.short/.long/.quad`（与 §7 的规范名不一致）；受理侧 `llvm-mc` 两套名字当前**都能汇编**（各 rc=0）。`.align N` 实测为**字节数**语义（与 GAS 的 `2^N` 冲突）。
- **目的**：把「DADAO 数据指示符口径」在**规范正文**上收口到**单一真源**（只 `.dd.*`；删 `.align` 只留 `.p2align`），供 `LLVM-078t` 实现侧对齐。
- **性质 = 规范口径收口（`spec` 模块）**；**不含实现**（实现归 `LLVM-078t`）。

**证据指针**：`.tao/knowledge/contract-asm.md`（当前 §指导符 行）、`spec/Toolchain-01-汇编语言.md §7`、`spec/DADAO-11-AEE-应用程序运行环境.md §汇编兼容性`（**只读引用，不改**）；issue `ISS-181`。

## 接口规范

- **输入**：
  - `spec/Toolchain-01-汇编语言.md §7`（**只读册，需用户授权**——授权见上「用户裁定」段，**须原样留档**）。
  - `.tao/knowledge/contract-asm.md`（v5 投影层正文）。
  - `manifests/spec-readonly.lock.toml`（`Toolchain-01` 的 `sha256` 锁）。
  - `spec/Process-06-spec目录保护规范.md`（只读册修改流程 + 锁同步要求）。
- **输出**：
  1. **`spec/Toolchain-01 §7`** 正文改对：① 只保留 4 条 `.dd.*` 为**唯一** DADAO 数据指示符；② 显式声明 **`.byte/.short/.long/.quad/.word/.octa` 全部禁**（`.word`/`.octa` 与 GAS 语义差异的既有注保留/加强）；③ **删 `.align`，只留 `.p2align`**（写清 `.p2align N` = 2^N 对齐）；④ `.dd.128` **不加**（可留一句「暂不引入」）。**不写死计数**。
  2. **`.tao/knowledge/contract-asm.md` 正文**：与 §7 **同口径**同步（只 `.dd.*` + 禁 GAS 名 + 删 `.align` 留 `.p2align`）。
  3. **`manifests/spec-readonly.lock.toml`**：`spec/Toolchain-01-汇编语言.md` 的 `sha256` **同步更新**（同一变更内），并在锁文件内注释本次变更理由。
- **约束**：
  - **不动上游 `DADAO-11`**（`spec/DADAO-11-*.md` 一字不改；确需 ⇒ **停下报告**）。
  - **不立 ADR**（用户裁定 ④）；本任务只改正文口径 + 锁。
  - **不改实现**（`components/**` 交集为空）；**不改 `tests/**`**（跟改归 `LLVM-078t`）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-130t/`；禁仓库内临时文件。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **用户授权留档**：`spec/Toolchain-01` 的修改授权（用户 2026-10-10 裁定，见上）须在完成区**原样留档**（子会话问答对父会话不可见，`lessons §7.3`）；未留授权 ⇒ reviewer 判 `Needs Revision`。
- **一键证据脚本** `.work/evidence/SPEC-130t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**（如改错锁 `sha256` ⇒ `make check-spec-readonly` FAIL；或把 §7 口径改回 GAS 名 ⇒ 一致性检查 FAIL）；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**。
- 复杂命令输出留 `.work/log/spec/SPEC-130t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **规范正文口径收口**：`spec/Toolchain-01 §7` 明确「唯一数据指示符 = `.dd.b08/.dd.w16/.dd.t32/.dd.o64`；`.byte/.short/.long/.quad/.word/.octa` 全部禁；`.align` 删、只留 `.p2align`（2^N）」；`.tao/knowledge/contract-asm.md` 同口径（给 `grep`/摘录证据）。
2. **锁同步**：`manifests/spec-readonly.lock.toml` 中 `spec/Toolchain-01-汇编语言.md` 的 `sha256` = **改后实测值**；`make check-spec-readonly`（或对应门控）EXIT=0（给真实命令 + rc）。
3. **不动上游**：`git -c core.quotepath=false diff --name-only | grep -E '^spec/DADAO-11'` → 无输出；`spec/` 改动**仅** `Toolchain-01` 一册；`components/**`/`tests/**` 交集为空。
4. **无 ADR**：本任务不新增/不修订 ADR（给 `git status` 证据）。
5. **一键证据脚本**：`.work/evidence/SPEC-130t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（`sha256` 写错 ⇒ 门控 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**用户授权留档**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
