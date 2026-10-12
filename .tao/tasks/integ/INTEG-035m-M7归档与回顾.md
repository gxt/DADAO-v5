# INTEG-035m: M7 归档与回顾

**模块**：integ
**项目里程碑**：M7
**依赖**：`INTEG-034m`（M7 整体收敛，`里程碑`）⇒ 前置条件 = **项目里程碑 M7 = 达成**
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目的
M7 达成后按 `Process-04`（里程碑归档规范）**归档 M7**——把 M7 任务书 `git mv` 入 `.tao/archive/M7/`、建里程碑回顾与台账快照、收敛活台账指针，防止 `.tao/tasks/` 膨胀、防止历史被误读为现行事实（`Process-04 §2`）。

**核心交付**：
1. `.tao/archive/M7/README.md`（归档说明 + 任务清单 + 流水快照 + MEMORY 摘录 + 指针，模板见 `Process-04 §6`）；
2. `.tao/archive/M7/m7-retrospective.md`（里程碑回顾：**写入用户 2026-10-12 裁定「记为达成（推荐）」+ 现场四数**）；
3. `.tao/archive/M7/issues-closed.md`（M7 阶段 `closed` 台账快照，`Process-04 §4.4/§7`）；
4. `git mv` 各 M7 任务书入 `.tao/archive/M7/<模块>/`（**`R` rename**，`Process-04 §5`）。

## 接口规范
- **输入**：`.tao/tasks/**` 中 `**项目里程碑**：M7` 且状态终态的任务书；`milestones.md`「任务流水」M7 行；`MEMORY.md` M7 相关行；`issues.yaml` M7 阶段 `closed` 项；既有 `.tao/archive/M7/notes/`（`gate-tiering-design.md`，`INFRA-070t` 已归档，**保留**）。
- **输出**：见上「核心交付」+ 台账收敛（`milestones.md`/`MEMORY.md`/`issues.yaml` 指针更新）。
- **约束**：
  - 归档**不删除、不改变历史**——任务书用 `git mv`（`R`），台账历史**搬入** archive、原文件只留**指针**（`Process-04 §2`）。
  - **归档前必做 §3 台账梳理**（未完成不得进入 §4 归档判据）：① 关闭已消解 `open`；② 校正 `scope`；③ 移出「教训/过程记录」类入 `lessons.md`；④ 判定 `moot`/过期；⑤ 头部同步；⑥ 逐条判定表 + `check_issues` EXIT 0。
  - **§4 归档判据**（机械可判）：① 任务书字段 `**项目里程碑**：M7` 且终态（过渡期与 M8 任务**不归档**）；② `milestones.md` 流水 ≤ M7 达成日的行；③ `MEMORY.md` 纯 M7 行（混合行只归档纯部分）；④ `issues.yaml` 中 `resolved_by` 提交日 ≤ 达成日的 `closed` 项。
  - **归档任务自归档**：本 `INTEG-035m` 自身最后一步 `git mv` 入 `.tao/archive/M7/integ/`（`Process-04 §4.1` 末条）。
  - **写用户裁定**（**原样引用**、不得臆造）：用户 2026-10-12 裁定「**记为达成（推荐）**」；picolibc 自带 test 现场 **total 235 / pass 213 / fail 0 / excluded 22 / blocked 0**（来源：`QEMU-058t` 完成区 + `components/qemu/changelog.md`；**现场统计、不写死**）——写入 `m7-retrospective.md`。
  - **并行纪律**（`Process-04 §8`）：**不得**与并行任务同树并发归档；等其完成/提交后再动；**只 `git add` 归档相关文件**。
  - 生成的 `README.md`/`milestones.md`/`MEMORY.md`：**无表内空行、无连续空行**，表格 `|---|` 后**必跟**数据行，blockquote 不插在 `|---|` 与数据行之间，文件尾无残留空行（`Process-04 §8`）。
  - **归档 = 真进 `.tao/archive/`**（**禁**子目录假装归档）；**计数不写死**（现场统计，或写「不下降 / 逐项相等」）。
  - **提交须经用户确认**（`AGENTS.md`）。

## 验收标准
1. **§3 台账梳理**：逐条判定表（id → 动作 + 依据）+ `check_issues.py` **EXIT 0**。
2. **§4 归档执行**：`git status` 显示各任务书为 `R`（rename）；`.tao/archive/M7/README.md`/`m7-retrospective.md`/`issues-closed.md` 存在且结构合 `Process-04 §6`。
3. **回顾含用户裁定**：`m7-retrospective.md` 原样含用户 2026-10-12 裁定「**记为达成（推荐）**」+ 现场四数（`pass 213 / fail 0 / excluded 22 / blocked 0`，total 现场统计）。
4. **台账收敛**：`milestones.md` 流水行移入 `README.md §2` + 新增「M7 归档指针」；`MEMORY.md` 新增 M7 归档指针行；`issues.yaml` 提取 M7 `closed` 项入 archive + 头指针。
5. **门控**：`make check`（L1）**EXIT 0**；`make check-no-residue` rc=0；`git status --untracked-files=all` 干净（无临时残留）。
6. **状态机**：核验通过 ⇒ 主会话将本 `m` `**状态**` 置 `里程碑`（末步自归档）。
7. **角色**：本任务为**归档/收敛类**（非实现）——由 **reviewer 独立执行核验**，**architect** 记录 / 回填完成区 / 提交。

## 硬约束
- 临时目录 `/tmp/opencode/<任务ID>/`；**禁**仓库内临时文件。
- **不提交 git**（提交权归 architect，核验后在本任务分支内提交）；**不 push**。
- 命令须捕退出码：`cmd; echo rc=$?`（**禁** `cmd | tail`/`| tee` 吞码）。
- 任务书文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
- 反例注入还原：**禁** `git checkout`/`git restore`/`git stash`；一律 `cp` 备份 + md5 对账或临时树；`git status`/`git diff` 干净**不作**「已还原」证据。
- 计数不写死：一律现场统计，或写「不下降 / 逐项相等」。

## 完成区
**测试结果**：L1 `make check` rc=0（`repository checks (L1): PASS`；`check-patch-tree: 4 component(s), 127 patches OK`）；L2 `make check-modules` rc=0（`check-lit` 107/107、`check-qemu-smoke` 86/86、`check-interface` 83/83、`check-picolibc-tests` 快档 20/18pass/0fail/2excluded/0blocked）；L3 `make check-full` **FULL_EXIT=0**（`setsid nohup`+`JOBS=8`；`check-qemu-semantics` 149/149 + `test-m6`：`check-lit-full` 12/12 + `diff_ir_lli` PASS + Embench 38/38）；`check-no-residue` rc=0；`check-knowledge-refs` rc=0（42 文件 / 16 具体路径 / **0 悬空**）；`check_issues.py` rc=0（**25 open / 0 closed**）；`check-knowledge-dir` PASS。
**修改文件**：`.tao/archive/M7/{README.md,m7-retrospective.md,issues-closed.md}`（新建）+ `git mv` **37** 份 M7 终态任务书 → `.tao/archive/M7/<模块>/`（`R` rename）+ `.tao/knowledge/{issues.yaml,milestones.md,MEMORY.md}` + `.tao/README.md` + 本任务书（完成区 + 审阅记录）。**范围外**：`spec/`/`contracts/`/`components/`/`Makefile`/`tools/`/`tests/` 交集为空。
**验收结果**：归档（37 份，真进 `.tao/archive/M7/`）✓；`README.md`/`m7-retrospective.md`/`issues-closed.md` 结构合 `Process-04 §6` ✓；`m7-retrospective.md` 原样含用户 2026-10-12 裁定「记为达成（推荐）」+ 现场四数（`total 235 / pass 213 / fail 0 / excluded 22 / blocked 0`）✓；台账收敛（`milestones.md` 流水行移入 README §2 + M7 归档指针；`MEMORY.md` 入口指针新增；`issues.yaml` 提取 12 条 `closed` + 头指针）✓；§3 梳理逐条判定表 ✓；门控全绿 ✓。
**新发现/坑**：① `INTEG-028t`（字段 `M6`、提交晚于 M6 归档）为 **M6 归档遗漏**，非 M7 判据 ⇒ 未归档、待回溯补入（见 `README §4`）；② **项目 M7 未标记「达成」**（`SPEC-136m`/`ISS-201`）⇒ 本归档无「≤ 达成日」机械界，以归档日为上界（**已披露偏离** `Process-04 §4.4`）；③ `m7-retrospective.md §5` 引用的行内 `\|` 需转义（已处理）。
**遗留问题**：① `ISS-201` 待用户逐条确认（决定 `SPEC-136m` 与**项目 M7 达成**）；② `INTEG-035m` **自归档**（`Process-04 §4.1` 末条）**待置 `里程碑` 后执行**（本次状态非终态，据主会话指示保留于 `.tao/tasks/`）；③ `INTEG-028t` 归属待裁定；④ 其余待裁定/操作项见 `m7-retrospective.md §7`（≥8 条）。

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 M7 归档任务书；按 `Process-04 §3/§4/§5/§6/§7/§8` 执行（§3 台账梳理前置 → §4 判据 → `git mv` 入 `.tao/archive/M7/` → 回顾/快照/指针/自归档）；**原样引用**用户 2026-10-12 裁定「记为达成（推荐）」+ 现场四数入 `m7-retrospective.md`；含并行纪律与「归档 = 真进 `.tao/archive/`」。
- **编号依据**：归档 = M7 生命周期终环（`Process-04 §1` 归档阶段），属 `integ` 模块里程碑级活动；`integ` 现场最大（`INTEG-034m` 顺延）⇒ 本 `m` = `INTEG-035m`（模块内跨后缀递增）。

#### 第 1 轮 architect 执行（2026-10-13，归档 + 收敛）

**分支/环境**：`git switch -c INTEG-035m`（基线 = `master` 干净）；workdir = 仓库根、相对路径；临时目录 `/tmp/opencode/arch-INTEG-035m/`；全程未越界、未用 `question`、未 `push`。

**§3 台账梳理（`Process-04 §3` 步骤 1–6）逐条判定**：
| # | 步骤 | 动作 | 依据 |
|---|---|---|---|
| 1 | 关闭已消解 `open` | 无 | M7 期已消解者（`ISS-189`/`191`/`194`/`195`/`196`）均已 `closed`；无「已消解仍 open」 |
| 2 | 校正 `scope` | 无 | 无 `M7` 前缀 scope 项、无 `post-M1` 模糊项 |
| 3 | 移出「教训/过程记录」类 | 无 | M7 教训已沉淀 `lessons.md`；余项均真 issue/待裁定 |
| 4 | `moot`/过期判定 | 无 | 余 25 条 `open` 均现行（缺陷/欠债/技术债/待裁定） |
| 5 | 头部同步 | ✓ | `issues.yaml` 顶部 M7 状态行 + M7 归档前置梳理块；`M7` scope 说明行 |
| 6 | 交付 | ✓ | 逐条判定表（本表）+ `check_issues.py` **rc=0** |

**§4 归档判据（机械可判）**：任务书 `**项目里程碑**：M7` 且终态 = **37**（现场统计，逐文件核字段+状态）；`milestones.md` 流水 ≤ 归档日终态行 = **37**；`MEMORY.md` 纯 M7 行 = **0**；`issues.yaml` `closed` = **12**（M7 期 5 + M6 遗留收敛 7）。

**执行记录**：
1. §3 梳理 → `issues.yaml` 提取 12 条 `closed` 入 `issues-closed.md` + 活台账仅留 25 `open`（YAML 解析校验通过）。
2. `git mv` **37** 份 → `.tao/archive/M7/<模块>/`（`git status` 显示 `R` rename；逐条对账）。
3. 建 `.tao/archive/M7/README.md`（§1 清单 / §2 任务流水 37 条原样搬入 / §3 MEMORY 摘录 / §4 指针）；`m7-retrospective.md`（含 §7 待裁定清单）；`issues-closed.md`。
4. 台账指针：`milestones.md`（M7 流水行移入 README §2 + M7 归档指针 + 未决 3 行保留 + 状态如实）；`MEMORY.md`（入口指针 2 行）；`.tao/README.md`（`archive/<里程碑>/` 约定）。
5. 门控：L1/L2/L3 + `check-no-residue` + `check-knowledge-refs` + `check_issues` **全绿**（见完成区）。

**如实披露（偏离/未决）**：
- **项目 M7 未标记「达成」**（`SPEC-136m` 未通过 `ISS-201`）⇒ 归档为**收尾归档**，前置条件（M7=达成）未满足；相对 `Process-04 §4.2/§4.4` 的「≤ 达成日」以**归档日 2026-10-13** 为上界。
- **`INTEG-035m` 未自归档**：其状态非终态（待 reviewer 核验 + 主会话置 `里程碑`）；据**主会话指示**（"保留未完结者，含 `INTEG-035m` 自身"）保留于 `.tao/tasks/integ/`，**自归档待置 `里程碑` 后执行**（与任务书 §接口规范的"末步自归档"为**已披露的偏离**，理由：主会话指令优先 + 状态未终态）。
- **跨文件历史引用未改写**（`Process-04 §6` + M1–M6 先例）：`issues.yaml` 注/`milestones.md` 中指向原 `.tao/tasks/<module>/<task>.md` 的 M7 任务指针**保留原样**，以 `README.md §4`「跨文件引用说明」统一指向归档路径；`check-knowledge-refs`（仅校验 `.work/**`）**0 悬空**。
- **`INTEG-028t` 未归档**（字段 `M6`、非 M7 判据）；建议 M6 历史遗漏回溯补入或用户裁定。

**判决（architect 执行结论）**：归档与台账收敛**完成**；门控全绿；**待 reviewer 独立核验**。

**提交留痕（architect）**：档位 = **正常提交**（非 WIP；归档/收敛类任务，主会话指定提交信息）；提交号 = `afc2c80`；**文件集对账**：显式 staging **45** 路径 = `R` rename **37** + `A` 新增 **3**（`archive/M7/{README,m7-retrospective,issues-closed}.md`）+ `M` **5**（`.tao/README.md`、`knowledge/{MEMORY,issues,milestones}`、本任务书），与完成区「**修改文件**」声明**逐项一致**，**无漏提/多提/越界**（`spec/`/`contracts/`/`components/`/`Makefile`/`tools/`/`tests/` 交集空）；**未 `push`**。

