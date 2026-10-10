# LLVM-075t: `.p2align`（可执行段）使 `llvm-mc` 崩溃【缺陷】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：待开始

> **覆盖缺口**：**`ISS-182`**（缺陷）。

## 用户裁定（2026-10-10，原话/结论）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。本任务 = 其中 **`ISS-182`（缺陷，优先）**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象（缺陷）**：`.text`（可执行段）内 `.p2align N`（N≥1）或 `.align N`（N≥2）⇒ `llvm-mc` **rc=134/141**，断言 `MCAssembler.cpp:588 The stream should advance by fragment size`；**`.rodata` 内同指令正常**（rc=0）。
- **最小复现**：`printf '.text\n.byte 1\n.p2align 3\n.byte 2\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/x.o /dev/stdin`（**须先自行复现**，给真实 rc + 断言原文）。
- **可疑根因**：`DADAOAsmBackend::writeNopData`（源 `MCTargetDesc/DADAOAsmBackend.cpp:299`，**已实现**）——当前实现按 `for (I=0; I<Count; I+=4) OS.write("\x77\x88\x00\x00", 4);` 每次写 **4 字节**；当所需对齐填充 `Count` **非 4 的倍数**时**写超**（向上取整）⇒ 实际推进字节数 ≠ fragment 尺寸 ⇒ 触发该断言。**须先诊断确认根因**（区分「`writeNopData` 尺寸错」与「对齐 fragment 尺寸算错」两说），再修。
- **影响**：真实 C 代码在 `.text` 内做块对齐即触发（`llc` 会发 `.p2align`）——**编译期显式失败**（非静默错码）。
- **性质 = 缺陷（`llvm-mc`/汇编路径崩溃）**。

**证据指针**：`.work/log/integ/pending-registrations.md §R2`；issue `ISS-182`；可疑根因源 `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`），重点 `MCTargetDesc/DADAOAsmBackend.{h,cpp}`（`writeNopData`）。
  - `.tao/knowledge/contract-isa.md`（指令宽度 4 字节、`swym` NOP 语义）；`spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **修复**：可执行段 `.p2align`/`.align` 汇编 **rc=0**，且**填充字节数正确**（对齐后偏移 = 目标对齐；填充内容为**合法** NOP/填充，不越界写）。
  2. 受影响 `tests/llvm/**`/`tests/e2e/**` 期望值按册/契约**重新派生**（**不从实现反填**）；新增向量覆盖 `.text` 内 `.p2align`。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义/宽度口径来自 `spec/`/`contracts`（**不从实现反推**，Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯缺陷修复 ⇒ 无新决策、无需 ADR。
  - 若修复须触及 LLVM **通用 MC 代码**（`llvm/lib/MC/**`）⇒ **停下报告**（优先 target-scoped 修复，避免动上游共享层）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-075t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-075t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-075t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **可执行段 `.p2align` 可汇编**：`.text` 内 `.byte 1` + `.p2align N`（N=1..4）`llvm-mc` **rc=0**（给真实命令 + rc），且**填充字节数正确**（对齐后偏移 = `2^N` 的倍数；如 `.byte 1`+`.p2align 3` ⇒ 段尺寸 8；给 `readelf`/`llvm-objdump`/`od` 实测证据），填充为**合法** NOP/填充字节。
2. **`.rodata` 不回归**：`.rodata` 内 `.p2align` 仍 rc=0 且填充正确（对齐前后逐字节核对）。
3. **`.align` 口径披露**：实测 `.align N`（若仍受理）= 字节语义、与 GAS 的 `2^N` 不同；**本任务不裁决 `.align` 去留**（该项归 `LLVM-078t`），但须**如实记录**其现状，若 `.align` 与 `.p2align` 共用同一修复路径则一并覆盖。
4. **E2E**：一段**含 `.text` 内对齐**的程序经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
6. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-075t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（**复现原缺陷**：如把 `writeNopData` 改回「每次写 4 字节 / 尺寸错误」⇒ 断言 FAIL/rc≠0 ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
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
