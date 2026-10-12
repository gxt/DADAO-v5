# TESTCASES-043m: M7 testcases 模块里程碑核验

**模块**：testcases
**项目里程碑**：M7
**依赖**：`TESTCASES-042t`（`已验证`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目的
核验 **testcases 模块 M7 目标**是否达成。**本模块 M7 口径（逐条；来源 = `milestones.md`「当前进度」M7 段落 + `INTEG-033k §裁定汇总 #2`，逐条引用）**：

1. **picolibc 自带 test 接入**（`TESTCASES-042t`）——编/链/跑 harness 落 `tools/testcases/**`（入库）、分层门控（快档代表集入 L2、全量档 opt-in）、诚实四分类报告（blocked 逐条有根因）。
2. **test 验收 = 100%**（用户 2026-10-11 原话「**要求 100%**」；`INTEG-033k §裁定汇总 #2`）。
3. **现场达成口径（用户裁定）**：picolibc 自带 test 现场 **total 235 / pass 213 / fail 0 / excluded 22 / blocked 0**（来源：`QEMU-058t` 完成区 + `components/qemu/changelog.md`，`make check-picolibc-tests-full` 现场统计；**`total` 与四数均现场统计、不写死**）；**用户 2026-10-12 裁定「记为达成（推荐）」**（原话引用，取得渠道 = 经主会话问答）。

## 核验内容（可执行步骤）
1. **L2 + 按需全量**：跑 `make check-modules`（L2，含 `check-picolibc-tests` 快档）；按需跑全量 `make check-picolibc-tests-full`——均留真实退出码。
2. **逐条核 M7 口径**（以**真实命令输出 + 退出码**为证，**禁**抽样推断 / 转述）：
   - 口径 1：`tools/testcases/**` harness 存在且入库；`check-picolibc-tests` 在 `check-modules`（L2）目标行；
   - 口径 2/3：`make check-picolibc-tests-full` rc=0，**现场重跑**复核四分类 = `pass 213 / fail 0 / excluded 22 / blocked 0`（total 现场统计）；复跑须逐用例与快照一致（**禁**仅采信快照）。
3. **跨模块影响**：本模块向量/门控受 `llvm`（后端缺口 ⇒ blocked）、`qemu`（softfloat ⇒ blocked）、`infra`（picolibc 运行时 ⇒ blocked）牵动——逐个核对是否未处置；点名 `ISS-198`（2-NaN payload 无测试覆盖，`qemu`+`testcases`）、`ISS-191`、`ISS-190`、`ISS-102`/`ISS-125`/`ISS-098`/`ISS-120`。**若存在未处置项 ⇒ 本 `m` 不得置里程碑**（`AGENTS.md`「模块里程碑与跨模块交互」）。
4. **M7 范围内 issue 处置**：对 `scope` 含 `testcases` 的 M7 期 issue 逐条给动作（关闭 / 转遗留 / 指明编号）——至少含 `ISS-191`（`__heap_*`）、`ISS-198`（转遗留）、`ISS-190`/`ISS-098`/`ISS-102`/`ISS-120`/`ISS-125`；**`open` 者不得擅自 close**（须依据或用户裁定，`Process-04 §3`）。
5. **门控**：`make check`（L1）rc=0 + `make check-no-residue` rc=0 + issue 台账校验（`check_issues`）rc=0。

## 验收标准
1. **逐条核验表**：每条 M7 口径 → 证据（命令 + 真实输出 + 退出码）→ 结论（达成 / 未达成 + 理由）。
2. **关联任务态核**：`TESTCASES-042t` 是否 `已验证`；`tools/testcases/**` 产出是否存在（现场核）。
3. **用户裁定落纸**：核验表须**原样引用**用户 2026-10-12 裁定「**记为达成（推荐）**」+ 现场四数（`pass 213 / fail 0 / excluded 22 / blocked 0`，total 现场统计）——**不得臆造/扩写**裁定。
4. **跨模块判定**：明列未处置项（若有）⇒ 明确写「**不得置里程碑**」；无未处置项则写「无」。
5. **状态机**：核验通过 ⇒ 主会话将 `**状态**` 置 `里程碑`；未通过 ⇒ 保持 `待开始` 并登记阻断。
6. **角色**：本任务**无实现**（核验类）——由 **reviewer 独立执行核验**，**architect** 记录 / 回填完成区 / 提交；**不得**要求 engineer 写无意义实现。

## 硬约束
- 临时目录 `/tmp/opencode/<任务ID>/`；**禁**仓库内临时文件。
- **不提交 git**（提交权归 architect，核验后在本任务分支内提交）。
- 全量档 `make check-picolibc-tests-full` 为**长任务**：`setsid nohup` 脱离 + 落盘 `XXX_EXIT=$rc`、`JOBS=8`、`timeout` 的 `124` 判 FAIL、**禁**会话内等待器。
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
- 立本 `m` 核验任务书（M7 testcases 模块里程碑）；M7 口径逐条引用 `milestones.md` M7 段落 + `INTEG-033k §裁定汇总 #2`；**原样引用**用户 2026-10-12 裁定「记为达成（推荐）」+ 现场四数（`pass 213 / fail 0 / excluded 22 / blocked 0`，total 现场统计）；含跨模块影响（点 `ISS-198`）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`testcases` 现场最大 `TESTCASES-042t` ⇒ 本 `m` = `TESTCASES-043m`（模块内跨后缀递增）。
