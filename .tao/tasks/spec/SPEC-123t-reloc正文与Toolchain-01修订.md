# SPEC-123t: reloc 正文 + `Toolchain-01 §6.1` 修订（已授权）+ 锁

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-122t`（reloc 体系 ADR 须 `Accepted`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 已 `Accepted` 的 reloc 体系 ADR（`SPEC-122t` 产出，拟 `.tao/adr/adr-0021-*.md`）。
  - `.tao/knowledge/contract-elf.md §2–§4`（reloc 投影，`ISS-154`/`ISS-151`/`ISS-161`）。
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（现有 reloc 集 D1–D8；`ABS48` 数据 8B 字段）。
  - `spec/Toolchain-01-汇编语言.md §6.1`（现口径「4×`set.w`」，与 `ISS-156` 实现口径不一致）。
  - `manifests/spec-readonly.lock.toml`（只读册 `sha256` 锁）、`spec/Process-06-spec目录保护规范.md`、`spec/Process-02-合约编写规范.md`。
  - **用户授权（原话，见 `INTEG-023k §B`）**：`ISS-156` 口径 = `rd2rf rfx, rd0` + **仅非零 `wp` 的 `set.w`**（`set.fo rf,0` ⇒ 1 条）；**并同步该册 `sha256` 锁**。
- **输出**：
  1. `.tao/knowledge/contract-elf.md §2–§4`：**reloc 正文**——`REL12` + 新专用类型（`ISS-151`/`ISS-161`）+ **`ABS48` 数据 8 字节字段表示**（`ISS-154`：48 位地址、大端存储、高 16 位填 0）。
  2. `spec/Toolchain-01-汇编语言.md §6.1`：**修订** `ISS-156` 口径（`rd2rf rfx, rd0` + 仅非零 `wp` 的 `set.w`；`set.fo rf,0` ⇒ 1 条）——**限 `§6.1`（用户授权范围内）**。
  3. `manifests/spec-readonly.lock.toml`：`Toolchain-01` 段 `sha256` **同步**（同一变更内）。
- **约束**：
  - **只改授权范围**（`Toolchain-01 §6.1`）；其余只读册**不得**触碰；任何扩面须**先停下、报告、待用户授权**。
  - 只读册改动**必须**在**同一变更**内同步 `sha256` 锁（`Process-06`）。
  - 与 `SPEC-122t`/`SPEC-124t` **同改 `spec/`/锁 ⇒ 串行**。
  - 正文以 `Process-02` 合约编写规范为准；不引入 ADR 決策之外的口径。
  - 计数口径**派生自单一真源**（`contracts/opcodes.yaml` 等），**不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-123t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-123t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-123t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **reloc 正文落笔**：`contract-elf.md §2–§4` 含 `REL12` + 新专用类型 + `ABS48` 数据 8B 字段表示；与已 `Accepted` 的 reloc ADR **一致**（给 `grep`/摘录）。
2. **`Toolchain-01 §6.1` 修订**：口径 = `rd2rf rfx, rd0` + 仅非零 `wp` 的 `set.w`（`set.fo rf,0` ⇒ 1 条）；给 `sed`/`grep` 真实输出。
3. **锁同步**：`manifests/spec-readonly.lock.toml` 的 `Toolchain-01` `sha256` == 实测 `sha256sum`（给真实输出）。
4. **授权范围核验**：`git diff --name-only` 中 `spec/` 仅 `Toolchain-01`（无其它只读册）；`grep` 证据。
5. **门控**：`make check` EXIT=0（`check-spec-readonly`/`check-spec-refs`/`check-contracts` 等）。
6. **一键证据脚本**：`.work/evidence/SPEC-123t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如改 `§6.1` 后再跑 `check-spec-readonly` ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/Toolchain-01` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-elf.md` + 本任务书）。

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
