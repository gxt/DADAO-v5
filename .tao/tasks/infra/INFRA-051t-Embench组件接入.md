# INFRA-051t: Embench 组件接入（组件化 + `enabled`）

**模块**：infra
**项目里程碑**：M6
**依赖**：`SPEC-122t`（Embench 上游选择 ADR，拟 `adr-0022`，须 `Accepted`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 已 `Accepted` 的 Embench 上游选择 ADR（`SPEC-122t` 产出，拟 `.tao/adr/adr-0022-*.md`：记录上游仓库 + 精确 commit）。
  - `manifests/components.lock.toml`（现有组件锁体例；`ADR-0005` 多源锁）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（树形补丁集 + 一文件一补丁）。
  - 现 `make fetch` 机制（落 `.work/source/<name>/`）。
- **输出**：
  1. `manifests/components.lock.toml`：Embench 条目 **翻 `enabled = true`**（`name`/`repository`/精确 commit 与 ADR 一致；标识符 = 原始仓库名，`MEMORY.md` 决策）。
  2. `components/embench-iot/{patches/**,series,changelog.md}`：**骨架**（`patches/` 树形补丁集 + `series` 清单 + `changelog.md`；本任务只建骨架，board shim/运行时的**实现**归 `TESTCASES-039t`）。
  3. **工作树**：`make fetch` 生成 `.work/source/embench-iot`（gitignored）。
- **约束**：
  - **ADR 未 `Accepted` 前不进实现**（`Process-03`）。
  - 与 `INFRA-050t` **同改 `Makefile`/`manifests` ⇒ 串行**。
  - 补丁集组织/生成/应用/校验以 `Process-01` 为准（`make check` 的 `check-patch-tree` 机械校验）。
  - 只建**骨架**；不提前引入 board shim/运行时实现（那属 `TESTCASES-039t`）。

## 硬约束

- **临时目录** `/tmp/opencode/INFRA-051t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**（涉 `components/**` 者）：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿（新组件须入校验）。
- **一键证据脚本** `.work/evidence/INFRA-051t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：`make fetch` 若需克隆/下载 Embench（网络）须先申报；**禁**自行选定镜像/开始下载，按 `AGENTS.md`「大文件下载与镜像」由用户定。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/infra/INFRA-051t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **锁条目启用**：`manifests/components.lock.toml` 的 Embench 条目 `enabled = true`，且 `name`/`repository`/commit 与 ADR **逐字一致**（给 `grep` 真实输出）。
2. **骨架存在**：`components/embench-iot/{patches/**,series,changelog.md}` 存在（给 `ls`/`find` 输出）。
3. **工作树生成**：`make fetch` EXIT=0，`.work/source/embench-iot` 存在且 HEAD == 锁定 commit（给真实输出）。
4. **门控**：`make check` EXIT=0（含 `check-patch-tree` 断言⑥，新组件纳入校验）。
5. **一键证据脚本**：`.work/evidence/INFRA-051t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `enabled` 改回 `false` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`manifests/components.lock.toml` + `components/embench-iot/**` + 本任务书）；`.work/` 生成物不暴露；无 `*_tmp*`/`*.orig`/`*.rej`。

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
