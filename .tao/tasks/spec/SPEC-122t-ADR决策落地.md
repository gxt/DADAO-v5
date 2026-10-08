# SPEC-122t: M6 ADR 决策落地（逐条用户确认）

**模块**：spec
**项目里程碑**：M6
**依赖**：无（决策先行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/Process-03-ADR编写规范.md`（ADR 格式：背景 → 决策 → 影响 → 已拒绝方案；判据）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（现 `§C7 D4`：大帧「方案2 为主 / 方案1 仅 >128K」）。
  - `INTEG-023k §A（#8/#9/#10）` 与 `§B（ISS-138）`、`§E`（M6 用户裁定原话）。
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（现 reloc 集 D1–D8；新类型为其**扩展**）。
- **输出**（**均为决策层**，落 `.tao/adr/`；正文归 `SPEC-123t`）：
  1. **`adr-0018` 就地修订 `§C7 D4`**（大帧寻址 = **四形态**：①`[sp,disp12]` ②`rb2rb`+`add.si` ③`add.o tmprb,sp,tmp`+`[tmprb,disp]` ④`ldm/stm [sp,tmp]`〔`immu6`=1 单次、>1 批量〕；**由编译器按代价（指令数 × 访存条数/复用次数）选择**）。修订方式（就地修订）按 `Process-03` 判定。
  2. **新建「`ld/st` 符号偏移 reloc 体系」ADR**（拟 `.tao/adr/adr-0021-*.md`）：`REL12`（load/store 相对寻址）+ **新专用类型**（`ISS-151`，**不复用 `REL20`**；须覆盖**超出 `REL12`** 的情形）。
  3. **新建 Embench 上游选择 ADR**（拟 `.tao/adr/adr-0022-*.md`）：记录 Embench 上游仓库 + **精确 commit**（供 `INFRA-051t` 翻 `enabled`）。
  4. **组合加载语义 ADR「不立」记录**：**不再需要独立 ADR**——已被「改走 `load_elf()`」取代（自建 loader/组合路径**取消**）；只在 ADR 或本任务书落「**不立 + 理由**」（不新建 ADR）。
- **约束**：
  - **每个 decision 必须由用户逐条判定**（保留/修改/否决），确认后方可写入并置 `Accepted`；**不得**因任务书/参考文档已写有该决策而默认通过（`AGENTS.md`「ADR decision 逐条确认」）。
  - **只落 ADR 决策/口径**；**不改实现/链接脚本/规范正文**（正文归 `SPEC-123t`）。
  - **`spec/` 交集为空**（`.tao/adr/` 非 `spec/`）。
  - 与 Wave 1 其它 spec 任务**同改决策层 ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-122t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-122t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-122t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`adr-0018 §C7 D4` 已修订**且落**四形态 + 代价驱动**口径；给出用户**逐条确认**的证据（问答摘要原样落任务书，`lessons §7.3`）。
2. **新 reloc ADR 存在**：含 `REL12` + 新专用类型（不复用 `REL20`；覆盖超出 `REL12` 情形）；用户逐条确认；状态 `Accepted`。
3. **Embench ADR 存在**：上游仓库 + 精确 commit；用户确认；状态 `Accepted`。
4. **组合加载 ADR「不立」记录存在**：含「不立 + 理由」（已被 `load_elf()` 取代）。
5. **逐条确认证据**：每个 decision（D1…/修订项）均有用户判定记录，**无预标 `Accepted`**。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/SPEC-122t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如移除某 ADR 的 decision/状态 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`.tao/adr/**` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

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
