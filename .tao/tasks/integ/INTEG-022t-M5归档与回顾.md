# INTEG-022t: M5 归档与回顾

**模块**：integ
**项目里程碑**：M5
**依赖**：M5 全部 `t` 任务（20 个）+ `INTEG-019k`（均 `已验证`）+ 6 个模块 `m`（`INFRA-049m`/`SPEC-118m`/`LLVM-061m`/`QEMU-048m`/`TESTCASES-035m`/`INTEG-021m`，均 `里程碑`）；**与其它任务串行**（改 `.tao/knowledge/*` 共享文件，须避开同树并发任务）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/Process-04-里程碑归档规范.md`（**编号以文件现状为准**）：**§3 归档前遗留台账梳理（6 步，MUST）**、**§4 归档判据（四类，机械可判）**、§5 落点与结构、§6 `README.md` 模板、§7 原台账处理、§8 验收与纪律、§9 教训。
  - `milestones.md`：M5 = **✅ 达成**（达成日 **2026-10-08**；门槛 `make test-semihost` EXIT=0；6 模块 `m` 全 `里程碑`；核验记录见 `.tao/tasks/integ/INTEG-021m-M5-integ里程碑.md`「核验记录（主会话）」）。
  - **先例体例**：`.tao/archive/M4/`（`README.md` + `m4-retrospective.md` + `issues-closed.md`）与归档任务 `.tao/archive/M4/integ/INTEG-018t-M4归档与回顾.md`（M4 归档实录：§3 由主会话先行、§4 判据、自归档坑）。
  - **归档前置**：本任务按用户指令**自行执行 `Process-04 §3` 台账梳理**（步骤 1–6），随后进入 `§4` 判据执行（与 M4 先例不同——M4 的 §3 由主会话先行；本任务合并执行）。
- **输出（M5 归档）**：
  1. `.tao/archive/M5/<模块>/…`：`**项目里程碑**` 字段 = `M5` 且终态（`已验证`/`里程碑`）的**全部**任务书，**用 `git mv` 移动**（保留 rename 历史）。
  2. `.tao/archive/M5/README.md`（按 `§6` 模板，体例照 `M4/README.md`：§1 任务清单〔模块和 = 总数〕/§2 `changelog` 摘录/§3 `MEMORY` 摘录/§4 指针）。
  3. `.tao/archive/M5/m5-retrospective.md`（M5 回顾：**达成情况 / 关键决策 / 新增机制 / 遗留登记 / 对 M6 的交接**）。
  4. `.tao/archive/M5/issues-closed.md`（`§4.4`：`resolved_by` 提交日 ≤ **2026-10-08** 的 `closed` 项快照 + 判定表）。
  5. `changelog.md`：移除归档条目（**按行首正则** `^\| \d{4}-\d{2}-\d{2} \|` 分组，多行 cell 勿切）+ 在**表头之上**加 M5 归档指针（`§7`）。
  6. `MEMORY.md`：移除纯 M5 行 + 在「当前进度」表**内**加 M5 归档指针（合法表行）。
  7. `issues.yaml`：移除已归档 `closed` 项 + 文件头注释加指针 + §3 梳理结果落盘。
  8. `milestones.md`：M5 里程碑表下方加归档注。
- **判据与预期规模（供核对；**执行时以实测为准**）**：

  **（一）`Process-04 §3` 台账梳理（**先做**，6 步）**——逐条、可追溯：

  1. **关闭已消解项**：本轮（或前序任务）已消解的 `open` issue → `closed` + `resolved_by`（指向消解任务/日期）。
  2. **校正 `scope`**：按**当前**里程碑定义校正；**残留 `M5` 且已达成/失效者按实际处理**（见下「M5-scope 待处理项」）。`scope` 枚举里 `M5` 语义须同步为「已达成」。
  3. **移出「教训/过程记录」类**：凡属记录/教训而非「待办 issue」的条目 → **移入 `.tao/knowledge/lessons.md`**（`issues.yaml` 中删除或留极简指针；**id 不复用**，如实说明）。
  4. **判定 `moot`/过期项**：已被后续任务覆盖、或里程碑已达成而失效的 → `closed`（附理由）或保留（附依据）；**不得凭印象**。
     - **里程碑边界项**（「本里程碑**部分交付**、剩余归下一里程碑」；用户裁定 2026-10-05）：须**拆分处置**——**交付部分单独 `closed`**（新增独立 `closed` 条目，`resolved_by` 指向交付任务；**原 id 保留给未交付的 `open` 条目**，不复用），**未交付部分留 `open`** 且 `scope` 校正到 **`M6`**；**不得**整条一并 `closed`，也不得一律保留。
  5. **头部同步**：更新文件头的里程碑状态（M5 → ✅ 达成）、字段约束（`scope` 枚举说明：`M5 = 已达成`；`M6 = 下一里程碑`）、`gate` 判据（如 `M5-gate` 历史化，若无则明确注记）。
  6. **交付**：**逐条判定表**（id → 动作 + 依据）+ `tools/infra/check_issues.py` **EXIT 0**（在完成区贴真实输出）。

  **M5-scope 待处理项（实测基线，2026-10-08，供 §3 判定起点；执行时重新实测）**：`issues.yaml` 共 42 条（39 open / 3 closed）；`scope` 含 `M5` 的 **13** 条 = **open 12** + **closed 1**：
  - **open 12**：`ISS-003`（`[M5]`）、`ISS-005`（`[M5]`）、`ISS-006`（`[M5]`）、`ISS-019`（`[golden,M5]`）、`ISS-026`（`[testcases,M5]`）、`ISS-047`（`[llvm,M5]`）、`ISS-074`（`[testcases,M5]`）、`ISS-081`（`[spec,golden,testcases,llvm,qemu,integ,M5]`）、`ISS-110`（`[llvm,M5]`）、`ISS-163`（`[spec,M5]`）、`ISS-164`（`[qemu,M5]`）、`ISS-167`（`[spec,qemu,M5]`）。
  - **closed 1**：`ISS-166`（`[spec,qemu,M5]`，`resolved_by: SPEC-121t`）。
  - **已知边界项（须按步骤 4 拆分/校正）**：`ISS-003`（特权 cfx 部分由 M5 收口，FP RF→`ISS-081`、LR-SC 未交付）、`ISS-110`（`trap`/`escape`/`cfx2rd`/`cfx2rc` 已由 `LLVM-060t` 实现、re-scope 由 `SPEC-115t` 收口 ⇒ **交付部分**；剩余 `cfxld`/`cfxst`〔`SimRISC-12`〕与 `SPEC-075t` 别名缺口未交付）。
  - **`scope` 未定归属者**（`ISS-019`/`ISS-026`/`ISS-081` 的 golden model、`ISS-074`、`ISS-047`、`ISS-163`/`ISS-164`/`ISS-167` 的归属里程碑）——按「**不确定处提问**」纪律：**不得擅自定为 `M6` 或 `closed`**；能机械判者按 §3 处置，**归属存疑者须停下报告主会话提请用户裁定**（并在判定表中标明「待裁定」）。
  - **不得**把 `spec/` 相关项（`ISS-163`/`ISS-167`）在**未获用户授权**前以「改 spec 收口」方式关闭——只登记/校正 `scope`。

  **（二）`§4` 归档判据（四类，机械可判）**：

  1. **任务书**：`**项目里程碑**` 字段**恰好 = `M5`** 且状态终态（`已验证`/`里程碑`）。**先实测计数**。**预期 26 个** = `infra 3 / spec 9 / llvm 2 / qemu 6 / testcases 3 / integ 3`：
     - `infra`=`INFRA-047t`/`INFRA-048t`/`INFRA-049m`；`spec`=`SPEC-113t/114t/115t/116t/117t/118m/119t/120t/121t`；`llvm`=`LLVM-060t/061m`；`qemu`=`QEMU-044t/045t/046t/047t/048m/049t`；`testcases`=`TESTCASES-033t/034t/035m`；`integ`=`INTEG-019k/020t/021m`（含 `INTEG-019k`）。
     - **+ 自归档** 本任务 `INTEG-022t` 自身 ⇒ 归档后 `archive/M5/` 各模块 **27**（`integ 4`）。
  2. **`changelog.md` 条目**：行首 `| YYYY-MM-DD |` **日期 ≤ 达成日 2026-10-08** 的表行（**实测基线：20 条** = 8×`2026-10-07` + 12×`2026-10-08`）。**说明**：其中含 `INTEG-018t`（M4 归档任务）1 行（`2026-10-07`）——按「日期 ≤ 达成日」**机械判据应计入**（M4 先例：其自身行在归档后追加故未计入；本任务自身行同此，在归档后追加）。
  3. **`MEMORY.md` 行**：内容**纯 M5** 的行（**实测基线：1 行** = `**M5 进行中**（2026-10-07）`）；混合了后续里程碑内容的行**不整行归档**（必要时人工拆分）。
  4. **`issues.yaml` 的 `closed` 项**：`resolved_by` 对应任务**提交日 ≤ 2026-10-08**（以 `git log --grep <taskID>` **实测**，**不得凭印象**）。**实测基线：3 条** = `ISS-147`（`TESTCASES-034t`）/`ISS-157`（`SPEC-116t`）/`ISS-166`（`SPEC-121t`）。**灰区不计**（`§4.4`）。

- **约束（硬）**：
  - **只动归档/台账相关文件**：`.tao/archive/M5/**`（新增/移动）、`.tao/knowledge/{changelog.md,MEMORY.md,issues.yaml,milestones.md,lessons.md}`、`.tao/tasks/integ/INTEG-022t-*.md`（自身）。**不得**触 `spec/`（交集必须为空）、`contracts/`、`components/`、`tools/`、`tests/`、`Makefile`。
  - **禁改 `spec/`**（用户裁定 + `spec/Process-06`）；本任务**不需要**改任何 `spec/` 册，若发现需要改 ⇒ **停下报告**（须用户事先授权）。
  - **不改写历史行**（`.tao/README.md`「历史行不改写」）：`changelog.md` 归档后的历史条目、`MEMORY.md` 历史行不重写；`milestones.md` 既有 M1–M5 行不动，仅**新增** M5 归档注。
  - **`git mv` 保 rename 历史**（`git status` 呈 `R` 而非 `A`+`D`）。**自归档**（本任务自身最后 `git mv`）——本任务书在建案时已由 architect 提交（tracked）⇒ 应呈 `R`；若因时点原因呈 `A`，须在完成区披露（参照 `INTEG-018t` 坑 1）。
  - **不误伤并行未提交工作**：只 `git add` 归档相关文件；**不得**与其它在同树并发执行 `make check`/构建的任务同时改共享文件（`§8`）。
  - 生成的 `README.md`/`changelog.md`/`MEMORY.md`/`issues.yaml`：**无表内空行、无连续空行**；blockquote **不得**插在 `|---|` 与数据行之间；文件尾**单换行**、无残留空行（`§8`/`§9`）。
  - 指向 `changelog.md`/`MEMORY.md` 中 M5 条目的历史引用**不回溯更新**（`§6` 指针说明）。
  - **不提交 git**（提交由 architect 判断执行；归档提交须经用户确认）。
  - **临时目录 `/tmp/opencode/INTEG-022t/`**；日志/证据留 `.work/log/integ/`、`.work/evidence/`（`.work/` 已 gitignore）。
  - **失败即停、禁自动重试**；**完成区与真实输出逐条对齐**；命令留证**须捕获被检命令自身退出码**（**禁** `cmd | tee log; echo $?`，用 `cmd > log 2>&1; rc=$?`）。
  - **反例注入还原**：**禁** `git checkout`/`git restore`/`git stash`；**禁** `git show <commit>:<path> > <path>`（从提交读回，`lessons §7.20`/`§8.14`）；一律 **`cp` 备份 + `md5sum` 对账**（或临时树作业）。**`git status`/`git diff` 干净不作「已还原」证据**。
  - **用户裁定落盘**：本任务取得的用户裁定须**原样写入任务书**（完成区「用户裁定」）。

## 验收标准

1. **`§3` 台账梳理完成**：完成区含 **逐条判定表**（`id → 动作 + 依据`，覆盖上「M5-scope 待处理项」全部 12 open + 1 closed 及被移出/关闭项）；`tools/infra/check_issues.py` **EXIT 0**（真实输出 + 退出码）；`scope` 中**无残留未处置的 `M5`**（若有正当保留，须逐条说明理由）；教训/过程记录类条目已入 `lessons.md`（**id 不复用**，说明落点）。
2. **任务书归档齐全**：`.tao/archive/M5/` 含各模块子目录（`infra/ spec/ llvm/ qemu/ testcases/ integ/`），任务书数 = 归档前 `.tao/tasks/` 中 `项目里程碑=M5` 且终态者**实测计数**，**预期 27**（26 + 自归档 `INTEG-022t`）；**逐条登录**；`.tao/tasks/` 下**无 M5 终态任务残留**。
3. **三份产物齐、体例一致**：`archive/M5/README.md`（按 `§6` 模板；§1 任务清单模块和 = 总数 27；§2 `changelog` 摘录条数 = 实测 `≤ 2026-10-08` 条数；§3 `MEMORY` 摘录 = 实测纯 M5 行数；§4 指针）+ `m5-retrospective.md`（**覆盖：达成情况 / 关键决策〔`ADR-0020` 新建、`ADR-0004 R1–R3` 修订、`ADR-0016` install、`ADR-0011 D3`→`SYS_EXIT` 取代 exit-port〕/ 新增机制 / 遗留登记 / 对 M6 的交接**）+ `issues-closed.md`（条数 = 实测 `closed` ≤ 达成日；含逐条判定表）。
4. **台账指针就位**：`milestones.md` M5 表下方**新增**归档注；`changelog.md` 表头**之上**加 M5 指针（非表内/表底）；`MEMORY.md` 表**内**加 M5 归档指针（合法表行）+ 纯 M5 行已移出；`issues.yaml` 文件头加指针 + 已归档 `closed` 项已提取。
5. **移动呈 rename**：所有归档任务书 `git status` 呈 `R`（自归档若呈 `A` 须披露）；`git mv` 后 `git diff --cached --summary` 见 `rename … (100%)`。
6. **门控**：`tools/infra/check_issues.py` **EXIT=0**（须）；`make check` **EXIT=0**（`.tao/**` 纯文档/台账改动**豁免**门控，但按本任务口径**仍须跑**并 EXIT=0）；`make check-no-residue` **EXIT=0**（须）。生成物无表断行/连续空行/尾空行。
7. **一键证据脚本** `.work/evidence/INTEG-022t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**不得用 `tee` 吞退出码**。
8. **无残留**：`git status --porcelain -uall` 仅归档相关改动（归档移动 + 新产物 + 台账 5 文件 + 本任务书）；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.preinject`；**`spec/` 交集为空**。

## 完成区

**测试结果**：

**修改文件**：

**验收结果**：

**用户裁定**：

**新发现/坑**：

**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

（自主逐行审查；finding 处置表见下）

#### 第 1 轮 reviewer 验收

（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 核归档齐全/台账/门控 + 判决）
