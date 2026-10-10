# LLVM-078t: 数据指示符口径（工具链生成侧/受理侧 + 用例跟改）【`ISS-181` 拆分-②】

**模块**：llvm
**项目里程碑**：M6
**依赖**：**`SPEC-130t`（正文口径 + 锁，`已验证`）**、`INFRA-050t`（一次构建 `DADAO;X86`）、`LLVM-062t`/`LLVM-063t`/`LLVM-065t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：待开始

> **覆盖缺口**：**`ISS-181`** 的**工具链实现 + 用例跟改**部分。**说明（拆分）**：`ISS-181` 拆为 **`SPEC-130t`（规范正文 + 锁）** + **`LLVM-078t`（本文件）**；**本任务依赖 `SPEC-130t`**（正文口径先落，再对齐实现，Spec-first）。

## 用户裁定（2026-10-10，经主会话转述的原话/结论，原样落纸）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。其中 **`ISS-181`（数据指示符口径）** 的裁定为：
> - **① 只留 `.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**（`.byte` / `.short` / `.long` / `.quad` / `.word` / `.octa` **全部禁**）。
> - **② 两侧一致**：`llc` **只生成** `.dd.*`，`llvm-mc` **拒绝** GAS 名（**若「受理侧拒」确需动 LLVM 通用 MC 代码，须先评估可行性并给结论**：可行则做；**确不可行 ⇒ 退回「只禁生成侧」并登记**）。
> - **③ 删 `.align`，只留 `.p2align`**（实测 `.align N` 是**字节数**语义、与 GAS 的 `2^N` 冲突）。
> - **④ 不立 ADR**：改 v5 侧 `spec/Toolchain-01 §7` + `.tao/knowledge/contract-asm.md` 正文 + 同步 `manifests/spec-readonly.lock.toml` 的 `sha256`；**不动上游 `DADAO-11`**（归 `SPEC-130t`）。
> - **⑤ `.dd.128` 暂不加**（用户保留；如加为小改）。
> - **⑥ 跟改面**：`tests/**`（lit CHECK 行、e2e `.s`、`tests/scripts/*.s`）与 `components/llvm-project/patches/**` 内受影响的 DADAO 侧 directive 串（`DADAOMCAsmInfo`）。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现状（实现侧，实测）**：
  - `llc` **生成侧**发 **GAS 名**：`i8→.byte`、`i16→.short`、`i32→.long`、`i64/指针→.quad`、`i128→两条 .quad`；数据段对齐发 **`.p2align N, 0x0`**。根因：`DADAOMCAsmInfo` **未覆盖** data directive 串 ⇒ 继承 `MCAsmInfo` 默认（`.byte/.short/.long/.quad`）。
  - **受理侧** `llvm-mc`：`.dd.b08/.dd.w16/.dd.t32/.dd.o64` 与 `.byte/.short/.long/.quad` **两套名字当前都能汇编**（各 rc=0）；`.word` 已被拒（`unknown directive`）；`.octa` 已被显式拒（提示 GAS 16 字节语义）。
- **目的**：按 `SPEC-130t` 收口的正文口径，把**实现侧**对齐——`llc` 只生成 `.dd.*`；受理侧尽量拒 GAS 名；删 `.align` 只留 `.p2align`；同步用例。
- **性质 = 工具链口径对齐（llvm 模块）**。

**证据指针**：`.work/log/integ/pending-registrations.md §R1`；`spec/Toolchain-01 §7`（`SPEC-130t` 改后）；issue `ISS-181`；`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）；重点 `MCTargetDesc/DADAOMCAsmInfo.{h,cpp}`（data directive 串 + alignment 串）、可能的 AsmParser/AsmPrinter。
  - `spec/Toolchain-01 §7`（`SPEC-130t` 改后 = 权威口径）；`.tao/knowledge/contract-asm.md`；`spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + `tests/**`）：
  1. **生成侧**：`llc` 对 `i8/i16/i32/i64`（及指针）**只生成** `.dd.b08/.dd.w16/.dd.t32/.dd.o64`（改 `DADAOMCAsmInfo` 的 `Data8/16/32/64bitsDirective` 等）；对 `i128` 保持**两条 `.dd.o64`**（`.dd.128` **不加**，用户裁定 ⑤）。
  2. **`.align`**：生成侧**不再发 `.align`**（保持/收紧为 `.p2align`）；受理侧对 `.align` 的处置按 ③ 与下述可行性评估。
  3. **受理侧（先评估可行性）**：使 `llvm-mc` **拒绝** GAS 名（`.byte/.short/.long/.quad`）——**先评估**：能否**target-scoped** 实现（不改 LLVM 通用 MC 代码）？
     - **可行** ⇒ 落地拒绝（rc≠0，给诊断信息）；
     - **确不可行（须动 `llvm/lib/MC/MCParser/AsmParser.cpp` 等通用 MC 代码）** ⇒ **退回「只禁生成侧」并登记**（在完成区 + `issues.yaml` 记「受理侧拒 GAS 名不可行/成本过高，暂只禁生成侧」），**不得擅自改通用 MC 层**（若确需 ⇒ **停下报告**）。
  4. **用例跟改**：`tests/**` 受影响处按新口径重派生/更新——lit CHECK 行、`tests/e2e/**` 的 `.s`、`tests/scripts/*.s`（**期望值按册/契约重新派生，不从实现反填**）；`components/llvm-project/patches/**` 内受影响的 DADAO 侧 directive 串同步。
  5. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 口径来自 `SPEC-130t` 的正文（**不从实现反推**，Spec-first）；**不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出；spec 侧归 `SPEC-130t`）。
  - **不引 libc/compiler-rt**（M6 约束）。
  - **不改 LLVM 通用 MC 代码**（`llvm/lib/MC/**`）；确需 ⇒ 停下报告（见上 3）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-078t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-078t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-078t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **生成侧只发 `.dd.*`**：`llc` 对一个含 `i8/i16/i32/i64/指针/全局` 的最小模块**只发** `.dd.b08/.dd.w16/.dd.t32/.dd.o64`，**不再发** `.byte/.short/.long/.quad`（给真实命令 + `llc -filetype=asm` 输出证据 + rc）；`i128` 仍两条 `.dd.o64`。
2. **受理侧（按评估结论）**：`.dd.*` 受理 rc=0；GAS 名（`.byte/.short/.long/.quad`）——**可行则拒绝（rc≠0 + 诊断）**；**不可行则如实登记**（完成区 + `issues.yaml`），并给「可行性评估结论 + 依据（为何须动通用 MC 代码）」。
3. **`.align` 删**：生成侧不再发 `.align`（给 grep 证据）；受理侧 `.align` 行为按 ③ 与评估结论如实记录（本任务**不裁决** `.align` 的受理与否超出裁定范围）。
4. **用例跟改**：`tests/**` 受影响处（lit CHECK 行 / e2e `.s` / `tests/scripts/*.s`）已按新口径更新；`make check-lit` 及相关门控 **EXIT=0**（通过数与改前**逐项相等 / 不下降**）。
5. **E2E**：一段含全局数据（`.dd.*`）的程序经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码；确保数据段字节正确）。
6. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
7. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出（spec 侧归 `SPEC-130t`）。
8. **一键证据脚本**：`.work/evidence/LLVM-078t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（**把 directive 串改回 GAS 名 ⇒ 生成侧断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿**），给真实输出与退出码。
9. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**受理侧可行性评估结论**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
