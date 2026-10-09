# SPEC-126t: 系统调用/半托管返回寄存器统一 `rd8`

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-124t`（函数返回 `rd8` 契约已收口；本任务与其它改 `spec/`/锁任务**串行**）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「统一为 rd8」**（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**（用户既定）。

## 变更边界（两个独立变更，**分别验收**）

1. **「函数返回」改动**（已完成）：`SPEC-124t`——函数返回寄存器 `rd31/rb31/rf31 → rd8/rb8/rf8`、声明序递增、每 bank `K=8`。**不在本任务范围**。
2. **「系统调用返回」改动**（本任务）：系统调用（`DADAO-22`/`DADAO-23`/`DADAO-21 §系统调用规范`）与半托管（`Machine-01 §5`）的**服务返回**寄存器 `rd31 → rd8`。两者**独立**、**分别验收**；不得把 1 的结论当作 2 的依据、亦不得因 1 已改而跳过 2 的逐条核。

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-see.md §5`（SBI 调用约定：标量返回 `rd31`）、`.tao/knowledge/contract-semihosting.md §2/§4`（semihosting 返回 `rd31`）。
  - `spec/DADAO-21-ABI-应用程序二进制接口.md §系统调用规范`（`返回值放在 RD31`）。
  - `spec/DADAO-22-SBI-主管系统二进制接口.md`（`rd31 = result/version/base/…` 返回表 + 代码示例，**十余处**）。
  - `spec/DADAO-23-HBI-超管系统二进制接口.md`（`HBI_GET_VERSION → rd31 = version`）。
  - `spec/Machine-01-测试机运行环境.md §5.2/§5.4`（semihosting 返回 `rd31`）。
  - `manifests/spec-readonly.lock.toml`（`DADAO-21/22/23`、`Machine-01` 的 `sha256`）。
  - 参考：`contract-abi.md §4.4/§4.6`（返回区 `rd8–rd15`，`SPEC-124t` 落点）。
- **输出**：
  1. 上述 **4 册 `spec/`** 正文中，**「调用/服务返回」用途**的返回寄存器 `rd31` 统一为 **`rd8`**；**逐条分类**（见约束）。
  2. `.tao/knowledge/contract-see.md §5`、`.tao/knowledge/contract-semihosting.md §2/§4` 同步返回寄存器 `rd8`。
  3. `manifests/spec-readonly.lock.toml` 中**被改册**的 `sha256` **同变更内**更新（改毕 `sha256sum` 实测）。
- **约束**：
  - **只改「调用/服务返回」用途**：改 = `DADAO-22` 各返回表中 `rd31 = result/version/base/ppn/ch/…`、`DADAO-23` `rd31 = version`、`DADAO-21 §系统调用规范`「返回值放在 RD31」、`Machine-01 §5.2/§5.4` semihosting 返回、`contract-see §5`/`contract-semihosting §2/§4` 返回寄存器。**不改**：`rd15 = nr`（系统调用号**入参**）、`rd16 = cfx/idx/len`、`rb16` 等**入参**、参数寄存器区（`rd16–rd31`/`rb16–rb31`）、寄存器角色表、指令语义（`cfx2rd … rd31` 中 `rd31` 若为**目标暂存/返回槽**须按用途判定，见下）。
  - **`rd15 = nr` 与返回区 `rd8–rd15` 重叠 —— 判断：需要澄清**：`rd15` 在**系统调用域**是调用号**入参**（`rd15 = nr`，**不改**），在**函数 ABI 域**是返回区第 8 槽（`rd8–rd15`）；二者分属**不同调用域**、不得混用。本任务**只改返回寄存器为 `rd8`、不改 `rd15 = nr` 约定本身**。若须在册内加**最小**区分说明（不得改变既有入参约定），须在完成区**逐条披露**其文本与理由；**勿擅自改动册**。
  - **逐条分类 + 修一类**：全仓 grep `rd31`（必要时 `rb31`）命中**逐条**判定「`调用/服务返回` → 改 `rd8`」或「非返回 → 不改（给理由）」；分类表入完成区，**计数由脚本现场统计、不写死**（`ISS-148` 教训）。
  - **不含实现**：`components/**`/`tools/**`/`tests/**` 归 `QEMU-055t`/`TESTCASES-041t`，本任务**`git diff` 与实现侧交集为空**。
  - **门控全绿**：`make check`（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）EXIT=0。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-126t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-126t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-126t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **逐条分类表**：完成区给「改 / 不改」逐条分类（`文件:行 + 用途 + 理由`），计数脚本现场统计（不写死）。
2. **返回寄存器统一**：4 册中被改条目的服务返回寄存器 == `rd8`（给 `grep`/摘录真实输出）；`rd15 = nr` 等**入参**约定**逐条未变**。
3. **contracts 侧同步**：`contract-see §5` / `contract-semihosting §2/§4` 返回寄存器 == `rd8`。
4. **锁同步**：被改册 `sha256` 改毕实测更新；`make check-spec-readonly` EXIT=0；**未被改册** `sha256` **逐条未变**（`git diff` 中既有 `sha256` 行 `-`/`+` 计数 = 0）。
5. **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）。
6. **一键证据脚本**：`.work/evidence/SPEC-126t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把某返回 `rd8` 还原为 `rd31` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`DADAO-21/22/23`、`Machine-01`、`manifests/spec-readonly.lock.toml`、`contract-see.md`、`contract-semihosting.md` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

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
