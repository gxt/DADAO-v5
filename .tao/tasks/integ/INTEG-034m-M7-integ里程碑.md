# INTEG-034m: M7 integ 模块里程碑核验（整体收敛点）

**模块**：integ
**项目里程碑**：M7
**依赖**：各模块 `m`（`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m`）；`INTEG-033k`（M7 开启）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目的
核验 **M7 整体收敛**（`Process-04 §1`：**INTEG 结束** = 集成门槛）。**M7 口径（来源 = `milestones.md` M7 段落 + `INTEG-033k`，逐条引用）**：

1. **M7 主题达成** = picolibc 移植（自带 test 现场 `total 235 / pass 213 / fail 0 / excluded 22 / blocked 0`，用户 2026-10-12 裁定「记为达成（推荐）」）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle。
2. **各模块 `m` 均 `里程碑`**（`INFRA-072m`/`SPEC-136m`/`LLVM-090m`/`QEMU-059m`/`TESTCASES-043m`）⇒ 满足后由主会话置**项目里程碑 M7 = 达成**（`Process-04 §1`）。
3. **L3 门控**（`docs/Process-07 §1/§2` 触发点「里程碑 / `/complete` 跑 L3」）= `make check-full`（`check-qemu-semantics` 全量 + `test-m6` = `check-lit-full` + `lli` 值级对拍 + Embench）全绿。

## 核验内容（可执行步骤）
1. **L3 全量**（长任务规则）：`make check-full`（= `check-qemu-semantics` + `test-m6`）——`setsid nohup` 脱离 + 落盘完成标记 `XXX_EXIT=$rc`、`JOBS=8`、`timeout` 的 `124` 判 FAIL、**申报预计耗时**（几百~几千秒）、**禁**会话内等待器；另跑 L1 `make check` rc=0。
2. **汇总各模块 `m` 结论**：逐个 `grep` 5 本 `m` 的 `**状态**` = `里程碑`；核各 `m` 的核验表结论与「跨模块影响」判定。
3. **跨模块交互核**（`AGENTS.md`「模块里程碑与跨模块交互」）：汇总各 `m` 的未处置项（若有）——点名 `ISS-198`（2-NaN 无 oracle）、`ISS-199`（权限 fail-fast 待复验）、`ISS-200`（changelog 缺条目）、`ISS-201`（弱符号防御分支待裁定）、`ISS-202`（contract 迁移待授权）、`ISS-193`（剩余面）。**存在未处置跨模块影响 ⇒ 本 `m` 不得置里程碑、且**不得**置项目里程碑 M7 为达成**。
4. **M7 范围内 issue 处置**：核对 M7 期 issue 的最终动作（关闭 / 转遗留 / 指明编号）已由各模块 `m` 逐条给出；`open` 者逐条有依据。
5. **门控**：`make check-no-residue` rc=0 + `git status --untracked-files=all` 干净（无临时残留）。

## 验收标准
1. **L3 证据**：`make check-full` 真实退出码 = 0（落盘 `XXX_EXIT` 标记；`124` 判 FAIL）+ `make check`（L1）rc=0。
2. **5 模块 `m` 均 `里程碑`**：逐个现场 `grep` 取证。
3. **跨模块判定**：明列未处置项（若有）⇒ 明确写「**不置里程碑**」；无未处置项 ⇒ 置 `里程碑` 并由主会话置 **项目里程碑 M7 = 达成**。
4. **状态机**：核验通过 ⇒ 主会话将本 `m` `**状态**` 置 `里程碑`；随后**项目里程碑 M7** 置 `达成`。
5. **角色**：本任务**无实现**（核验类）——由 **reviewer 独立执行核验**，**architect** 记录 / 回填完成区 / 提交；**不得**要求 engineer 写无意义实现。

## 硬约束
- 临时目录 `/tmp/opencode/<任务ID>/`；**禁**仓库内临时文件。
- **不提交 git**（提交权归 architect，核验后在本任务分支内提交）；**不 push**。
- 长任务（L3）：`setsid nohup <cmd> >log 2>&1 &` 脱离 + 落盘 `XXX_EXIT=$rc`、`JOBS=8`、`timeout` 的 `124` 判 FAIL、**申报耗时**、**禁**会话内等待器。
- 命令须捕退出码：`cmd; echo rc=$?`（**禁** `cmd | tail`/`| tee` 吞码）。
- 任务书文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
- 反例注入还原：**禁** `git checkout`/`git restore`/`git stash`；一律 `cp` 备份 + md5 对账或临时树。
- 计数不写死：一律现场统计，或写「不下降 / 逐项相等」。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 `m` 核验任务书（M7 integ 整体收敛点）；跑 L3 `make check-full`（长任务规则）+ 汇总 5 模块 `m` 结论 + 跨模块交互核；含「有未处置 ⇒ 不置里程碑 / 不置项目里程碑达成」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`integ` 现场最大 `INTEG-033k` ⇒ 本 `m` = `INTEG-034m`（模块内跨后缀递增）；与 `INTEG-033k`（M7 开启）一一对应（`Process-04 §1` INTEG 开闭）。
