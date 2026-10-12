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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 M7 归档任务书；按 `Process-04 §3/§4/§5/§6/§7/§8` 执行（§3 台账梳理前置 → §4 判据 → `git mv` 入 `.tao/archive/M7/` → 回顾/快照/指针/自归档）；**原样引用**用户 2026-10-12 裁定「记为达成（推荐）」+ 现场四数入 `m7-retrospective.md`；含并行纪律与「归档 = 真进 `.tao/archive/`」。
- **编号依据**：归档 = M7 生命周期终环（`Process-04 §1` 归档阶段），属 `integ` 模块里程碑级活动；`integ` 现场最大（`INTEG-034m` 顺延）⇒ 本 `m` = `INTEG-035m`（模块内跨后缀递增）。
