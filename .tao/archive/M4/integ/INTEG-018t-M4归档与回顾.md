# INTEG-018t: M4 归档与回顾

**模块**：integ
**项目里程碑**：M4
**依赖**：无（M4 已达成）；**与其它任务串行**（改 `.tao/knowledge/*` 共享文件，须避开同树并发任务）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/Process-04-里程碑归档规范.md`（**编号以文件现状为准**；§1「里程碑生命周期」于 2026-10-06 新增、其后各节顺延）：§2 目的与触发、§3 归档前遗留台账梳理（**本任务前已由主会话完成**，见下）、§4 归档判据、§5 落点与结构、§6 `README.md` 模板、§7 原台账处理、§8 验收与纪律、§9 教训。
  - `milestones.md`：M4 = ✅ 达成（达成日 **2026-10-07**，commit `cfcb64d`）。
  - 先例：`.tao/archive/M1/`、`.tao/archive/M2/`（`INTEG-010t`）、`.tao/archive/M3/`（`INTEG-014t`/`INTEG-015t`）。
  - **归档前置（已完成）**：`Process-04 §3` 台账梳理由**主会话**于 2026-10-07 执行（commit `bdbcfd2`：issues 核查 6 结案 + 8 rescale M5 + 3 moot + `ISS-149/150`→`160/161` + `ISS-047`→M5）。**本任务不重复 §3**，直接进入 §4 判据执行。
- **输出**（M4 归档）：
  - `.tao/archive/M4/<模块>/…`：`项目里程碑` 字段 = `M4` 且终态（`已验证`/`里程碑`）的任务书，**用 `git mv` 移动**（保留 rename 历史）。
  - `.tao/archive/M4/README.md`（按 §6 模板；含任务清单 / `changelog` 摘录 / `MEMORY` 摘录 / 指针）。
  - `.tao/archive/M4/m4-retrospective.md`（**M4 回顾**：目的/门槛/关键决策〔`ADR-0019` reloc、`ADR-0013 D11` 伪指令、`ADR-0004` 调整、`ADR-0003 §D5` 修订〕/落地链/坑与教训/遗留 M5）。
  - `.tao/archive/M4/issues-closed.md`（§4.4/§7：`resolved_by` 提交日 ≤ **2026-10-07** 的 `closed` 项快照）。
  - `changelog.md`：移除归档条目（行首 `| YYYY-MM-DD |` 日期 ≤ 2026-10-07；**按行首正则分组**，多行 cell 勿切）+ 在**表头之上**加 M4 归档指针（§7/§8）。
  - `MEMORY.md`：移除纯 M4 行 + 在「当前进度」表**内**加 M4 归档指针（合法表行）。
  - `issues.yaml`：移除已归档 `closed` 项 + 文件头注释加指针。
  - `milestones.md`：里程碑表下方加 M4 归档注。
- **判据（§4，机械可判）**：
  1. 任务书 `**项目里程碑**` **恰好 = M4** 且终态；**不归档**下一里程碑（M5）/过渡期任务。**本次含两类特别项**：
     - **`SPEC-111t`（用户裁定 2026-10-07：`项目里程碑` 由 `M3` 改判为 `M4`）**，随后与 M4 一并归档；`git status` 显示 `RM`（改名 + 改字段）。
     - **本任务书自身 `INTEG-018t`**（**自归档**，§4.1 末条 / §3.1）；最后一步 `git mv` 自身入 `archive/M4/integ/`。
  2. `changelog.md` 行首 `| YYYY-MM-DD |` **日期 ≤ 2026-10-07** 的表行（本仓现状：**28 条**，26 条 `2026-10-06` + 2 条 `2026-10-07`）。
  3. `MEMORY.md` **纯 M4** 行（混合行只归档纯 M4 部分，必要时人工拆分，不机械切行）。
  4. `issues.yaml` `closed` 项：`resolved_by` 对应任务**提交日 ≤ 2026-10-07**（以 `git log --grep <taskID>` **实测**，**不得凭印象**；起始状态：本仓现有 `closed` **12 条** = `ISS-008/011/014/038/044/050/117/142/152/153/155/158`，须逐条核提交日并给出判定表）。
- **预期规模（供核对，执行时以实测为准）**：
  - M4 任务书（`项目里程碑：M4` 且终态）**30 个** = `infra 4 / spec 8 / testcases 4 / llvm 10 / qemu 2 / integ 2`：
    - infra：`INFRA-043t`/`044m`/`045t`/`046t`
    - spec：`SPEC-104k`/`105t`/`106t`/`107t`/`108m`/`109t`/`110t`/`112t`
    - testcases：`TESTCASES-029t`/`030t`/`031m`/`032t`
    - llvm：`LLVM-050t`~`059t`（含 `057m`）
    - qemu：`QEMU-042t`/`043m`
    - integ：`INTEG-016t`/`017m`
  - **+ reclassified** `SPEC-111t`（spec，M3→M4）→ 31
  - **+ 自归档** `INTEG-018t`（integ）→ **32**
  - ⇒ 归档后 `archive/M4/` 各模块任务书：`infra 4 / spec 9 / testcases 4 / llvm 10 / qemu 2 / integ 3 = 32`
- **纪律（§7/§8）**：
  - **只动 `.tao/**`**（归档移动 + `milestones.md` 归档指针 + `MEMORY.md`/`changelog.md`/`issues.yaml` 归档注记 + `SPEC-111t` 的 `项目里程碑` 字段改判）；**不碰** `spec/`、`contracts/`、`components/`、`tools/`、`tests/`。
  - **不改写历史行**（`.tao/README.md`「历史行不改写」）：`changelog.md` 归档后的历史条目、`MEMORY.md` 历史行不重写；`milestones.md` 既有 M1–M3 行不动，仅**新增** M4 归档注。
  - **不误伤并行未提交工作**：只 `git add` 归档相关文件；并行任务书/补丁一律不动；**不得**与其它在同树并发执行 `make check`/构建的任务同时改共享文件。
  - 生成的 `README.md`/`changelog.md`/`MEMORY.md`：**无表内空行、无连续空行**；blockquote **不得**插在 `|---|` 与数据行之间；文件尾**单换行**、无残留空行。
  - 指向 `changelog.md`/`MEMORY.md` 中 M4 条目的历史引用**不回溯更新**（§6 指针说明）。
  - **不提交 git**（提交由 architect 判断执行；归档提交须经用户确认）。
  - **临时目录 `/tmp/opencode/INTEG-018t/`**；日志/证据留 `.work/log/`、`.work/evidence/`（`.work/` 已 gitignore）。
  - **完成区与真实输出逐条对齐**；命令留证**须捕获被检命令自身退出码**（**禁** `cmd | tee log; echo $?`，用 `cmd > log 2>&1; rc=$?`）。
  - **反例注入还原**：**禁** `git checkout`/`git restore`/`git stash`；一律 **`cp` 备份 + `md5sum` 对账**（或临时树作业）；`git status`/`git diff` 干净**不作**「已还原」证据。
  - **用户裁定落盘**：本任务取得的用户裁定须**原样写入任务书**（完成区「用户裁定」）。

## 验收标准

1. **任务书归档齐全**：`.tao/archive/M4/` 含各模块子目录（`infra/ spec/ testcases/ llvm/ qemu/ integ/`），其中任务书数 = **归档前 `.tao/tasks/` 中 `项目里程碑=M4` 且终态者**（预期 **32**：30 + `SPEC-111t` + `INTEG-018t`），**逐条登录**；`git status` 显示 **`R`（rename）**，`SPEC-111t` 显示 **`RM`**（改名 + 改字段）。
2. **三份产物**：`archive/M4/README.md` + `m4-retrospective.md` + `issues-closed.md` 均存在，且**内容与 M1–M3 体例一致**：`README.md` 按 §6 模板（§1 任务清单〔模块和 = 总数〕/§2 `changelog` 摘录〔28 条〕/§3 `MEMORY` 摘录/§4 指针）；`issues-closed.md` 条数与判据一致（逐条可核，附判定表）；`m4-retrospective.md` 覆盖目的/门槛/决策/落地链/坑与教训/遗留 M5。
3. **自归档**：`INTEG-018t` 自身在 `.tao/archive/M4/integ/` 且**不在** `.tao/tasks/integ/`。
4. **台账指针就位**：`milestones.md` 里程碑表下**新增** M4 归档注；`changelog.md` 表头**之上**加 M4 指针（非表内/表底）；`MEMORY.md` 表**内**加 M4 归档指针（合法表行）；`issues.yaml` 文件头加指针。
5. **移动呈 rename**：所有归档任务书 `git status` 为 `R`/`RM`，**无** `A`+`D` 未识别对；`.tao/tasks/` 下无 M4 终态任务残留。
6. **门控**：`make check-no-residue` **EXIT=0**（须）；`make check` 建议运行以确认无回归（`.tao/**` 纯文档/台账改动**豁免**门控，若跑须 EXIT=0）；生成物无表断行/连续空行/尾空行。
7. **一键证据脚本** `.work/evidence/INTEG-018t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**不得用 `tee` 吞退出码**。

## 完成区

**测试结果**：
- `make check` **EXIT=0**（日志 `.work/log/integ/INTEG-018t-make-check.log`）：`repository checks: PASS`；lit **60/60**；`check_issues: 34 open, 0 closed`；`check-patch-tree` 89、`check-qemu-semantics` 149/149（未变）。
- `make check-no-residue` **EXIT=0**（`check-no-residue: PASS`）。
- `tools/infra/check_issues.py` **EXIT=0**（归档前 `34 open, 12 closed` → 归档后 `34 open, 0 closed`）。
- 一键证据脚本 `.work/evidence/INTEG-018t/run.sh` **EXIT=0**（运行结果见「验收结果」；含注入→预期 FAIL→`cp`+md5 还原→回绿）。

**修改文件**（`git status --porcelain -uall` 逐条）：
1. **归档移动（`git mv`，31 个 tracked）**：`.tao/tasks/<module>/<task>.md` → `.tao/archive/M4/<module>/<task>.md`（30 个 `R` + `SPEC-111t` `RM`；均 `R100`）。
2. **`SPEC-111t` 字段改判**：`**项目里程碑**：M3 → M4`（仅此一行，工作树未 staged，故呈 `RM`）。
3. **新增（3）**：`.tao/archive/M4/README.md`、`.tao/archive/M4/m4-retrospective.md`、`.tao/archive/M4/issues-closed.md`。
4. **修改（4）**：`.tao/knowledge/milestones.md`（表断行修正 + M4 归档注）、`.tao/knowledge/changelog.md`（28 条搬入 README + 表头 M4 指针）、`.tao/knowledge/MEMORY.md`（`M4 规划`行 → `M4 归档`指针）、`.tao/knowledge/issues.yaml`（12 closed 提取 + 文件头 M4 指针 + M4 头部状态/scope 描述同步）。
5. **自归档（1）**：`.tao/tasks/integ/INTEG-018t-*.md` → `.tao/archive/M4/integ/`（见「新发现/坑」1）。
6. **本任务书自身**（完成区 + 自审 + 状态）；证据脚本/生成脚本/日志在 `.work/`（gitignored）。

**验收结果（真实输出）**：
```
$ git status --porcelain -uall | awk '{print $1}' | sort | uniq -c
      4 ??
      4 M
     30 R
      1 RM

$ git diff --cached --summary | grep -c rename         → 31       （全 R100）
$ ls .tao/archive/M4/*/  →  infra 4 / spec 9 / testcases 4 / llvm 10 / qemu 2 / integ 3   （合计 32）
$ test -e .tao/tasks/integ/INTEG-018t* ; echo $?       → 1        （不在 tasks）
$ ls .tao/tasks/*/*.md 2>/dev/null | wc -l             → 0        （tasks 已清空）

$ make check            → EXIT=0 ; repository checks: PASS ; lit 60/60
$ make check-no-residue → EXIT=0 ; check-no-residue: PASS
$ python3 tools/infra/check_issues.py → EXIT=0 ; check_issues: 34 open, 0 closed
$ bash .work/evidence/INTEG-018t/run.sh → EXIT=0 ; == INTEG-018t evidence: ALL PASS ==
```
（完整输出见 `.work/log/integ/INTEG-018t-make-check.log`、`/tmp/opencode/INTEG-018t/`。）

**用户裁定**：
- `SPEC-111t` 的 `**项目里程碑**` 由 `M3` 改判为 `M4`（用户裁定 **2026-10-07**；见任务书 §接口规范「判据」第 1 条），随后与 M4 一并归档（`git status` 呈 `RM`）。本任务未新增其它需用户裁定的事项。

**新发现/坑**：
1. **未跟踪任务书无法 `git mv`（自归档）**：`INTEG-018t` 在首次提交前无 HEAD 基线，直接 `git mv` 报「not under version control」。处置：`git add`（staged 为新增）后 `git mv`，`git status` 呈 **`A`（新增）**而非 `R`——**预提交阶段无法体现 rename 历史**。（对照：M3 的 `INTEG-014t` 是先由 `80a5a0a` 提交、再由 `INTEG-015t` 自归档，故当时可 `R`。）
2. **`milestones.md` 表断行（预存缺陷）**：`cfcb64d` 在里程碑**表头与分隔行之间**插入了「M4 达成」blockquote（`Process-04 §9.1` 教训所述断表模式），致表断为普通文本；本次归档一并把该注移出表内、置于表下方，并把「M4 达成注」末句「归档待立归档任务」订正为「归档见下」。
3. **`issues.yaml` 头部状态陈旧**：头部 `M4 = 规划中` 与 scope 枚举描述 `M4 = 后续里程碑（未规划…）` 随归档同步为 `M4 = ✅ 达成` / `M4 = ELF 文件支持 + LLD 链接 + 汇编器遗留收口（已达成）；M5 = …`（`Process-04 §3.5`「头部同步」口径）。
4. **README §2 摘录按「行首正则」分组**：`changelog.md` 条目跨物理行的 cell 以 `^\| \d{4}-\d{2}-\d{2} \|` 分组搬运，断言恰 **28** 条（26×`2026-10-06` + 2×`2026-10-07`），未切行。

**遗留问题**：
- **无未完成项**（32 任务书归档齐全含自归档；三份产物齐；台账指针就位；移动呈 rename；`check-no-residue` EXIT=0）。
- **披露（超「仅加指针」的必要的头部同步，见「新发现/坑」2/3）**：`milestones.md` 表断行修正 + M4 达成注末句；`issues.yaml` 头部 M4 状态行/scope 描述。均限 `.tao/**` 内，未触 M1–M3 历史行。
- **未改（按纪律）**：`issues.yaml` 头部 `project_M4-*.md（待建）` 保留（该文件确未建）；`milestones.md` 的 M1–M3 行与既有 blockquote 未动。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（全局 `subagent_depth=1`，无法嵌套子代理）；对产物 + 台账 + 真实重跑对账，关键结论附真实输出/退出码。

**逐项审查与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 归档任务数是否恰 32（30 M4 终态 + SPEC-111t + INTEG-018t） | ✅已核 | —— | `ls .tao/archive/M4/*/`：infra 4/spec 9/testcases 4/llvm 10/qemu 2/integ 3=32；`.tao/tasks/*/*.md`=0 |
| F2 `SPEC-111t` 字段改判 + `RM` | ✅已核 | 仅 `**项目里程碑**：M3→M4` 一行 | `git status` 该文件 `RM`；`git diff`（unstaged）仅此一行 |
| F3 移动呈 rename（无 A+D 未识别对） | ✅已核 | —— | `git diff --cached --summary`：31×`rename … (100%)` |
| F4 `INTEG-018t` 自归档为 `A` 非 `R` | ✅已核（预提交固有限制） | `git add`+`git mv` | 见「新发现/坑」1；`git status` 该文件 `A` |
| F5 `milestones.md` 表断行修复 | ✅已修 | M4 达成注移出表内、置表下方 | 表头下一行实测为 `\| --- \| …` |
| F6 台账指针就位（4 文件） | ✅已核 | —— | `run.sh` §5 全 PASS |
| F7 README §2 恰 28 条、§3 恰 1 行、无 marker 残留 | ✅已核 | —— | `awk` 计数 28/1；`grep @@` 无输出 |
| F8 issues-closed 恰 12 条 + 判定表逐条 | ✅已核 | —— | `grep -c '^\| \`ISS-'`=12；`git log --grep` 逐条 ≤ 2026-10-07 |
| F9 changelog 数据行清零、M4 指针在表头之上 | ✅已核 | —— | `grep -c '^| 2026-'`=0；指针在 `| 日期 |` 之上 |
| F10 生成物无表断行/连续空行/尾空行 | ✅已核 | —— | 7 个产物尾字节均单 `\n`；表结构逐行核对 |
| F11 反例注入可失败 + `cp`+md5 还原 | ✅已核 | —— | `run.sh` §8：「注入有效性(md5 改变/diff 非空)」+「还原后 md5==注入前」 |
| F12 `check_issues` 34 open/0 closed；`make check`/`check-no-residue` EXIT=0 | ✅已核 | —— | 真实重跑 EXIT=0（见完成区） |
| F13 只动 `.tao/**`、未碰 spec/contracts/components/tools/tests | ✅已核 | —— | `git status -uall` 仅 `.tao/**`（+ `.work/` ignored） |
| F14 证据脚本 `issues-closed` 计数首跑误报（24≠12，`grep` 同时命中判定表） | ✅已修 | `run.sh` 改用 `awk` 限定「主表/判定表」分别计数 | 首跑 **EXIT=1**（可失败）；修后复跑 **EXIT=0 / ALL PASS** |

**判决**：无未修 finding（F5 已修并复验；其余已核实）。状态置 `待验收`，返回主会话。

#### 第 1 轮 reviewer 验收（2026-10-07）

**重跑记录**：

```
$ bash .work/evidence/INTEG-018t/run.sh 2>&1
== INTEG-018t evidence @ 2026-10-06T21:27:55Z ==
-- 1. 归档结构（archive/M4）--
[PASS] 目录 .tao/archive/M4/infra 存在  rc 期望=0 实际=0
[PASS] 目录 .tao/archive/M4/spec 存在  rc 期望=0 实际=0
[PASS] 目录 .tao/archive/M4/testcases 存在  rc 期望=0 实际=0
[PASS] 目录 .tao/archive/M4/llvm 存在  rc 期望=0 实际=0
[PASS] 目录 .tao/archive/M4/qemu 存在  rc 期望=0 实际=0
[PASS] 目录 .tao/archive/M4/integ 存在  rc 期望=0 实际=0
[PASS] infra 任务书数  期望=4 实际=4
[PASS] spec 任务书数  期望=9 实际=9
[PASS] testcases 任务书数  期望=4 实际=4
[PASS] llvm 任务书数  期望=10 实际=10
[PASS] qemu 任务书数  期望=2 实际=2
[PASS] integ 任务书数  期望=3 实际=3
[PASS] 合计任务书数  期望=32 实际=32
-- 2. 字段：项目里程碑=M4 且终态 --
[PASS] 非 M4 字段文件数（应为 0）  期望=0 实际=0
[PASS] 非终态/待验收状态文件数（应为 0）  期望=0 实际=0
-- 3. 自归档（INTEG-018t）+ .tao/tasks 无残留 --
[PASS] INTEG-018t 在 archive/M4/integ  rc 期望=0 实际=0
[PASS] .tao/tasks 下残留任务书数（应为 0）  期望=0 实际=0
[PASS] M4 任务残留于 .tao/tasks（应为 0）  期望=0 实际=0
-- 4. 三份产物 --
[PASS] archive/M4/README.md 存在  rc 期望=0 实际=0
[PASS] archive/M4/m4-retrospective.md 存在  rc 期望=0 实际=0
[PASS] archive/M4/issues-closed.md 存在  rc 期望=0 实际=0
[PASS] README §2 changelog 条数  期望=28 实际=28
[PASS] README §3 MEMORY 行数  期望=1 实际=1
[PASS] README §1 模块和  期望=32 实际=32
[PASS] issues-closed 主表条数  期望=12 实际=12
[PASS] issues-closed 判定表条数  期望=12 实际=12
[PASS] README 指向 retrospective  rc 期望=0 实际=0
[PASS] retrospective 含 M5 交接  rc 期望=0 实际=0
-- 5. 台账指针 --
[PASS] MEMORY 表内 M4 归档指针  rc 期望=0 实际=0
[PASS] MEMORY 残留 M4 规划 行（应为 0）  期望=0 实际=0
[PASS] changelog 表头之上 M4 指针  rc 期望=0 实际=0
[PASS] changelog 残留数据行（应为 0）  期望=0 实际=0
[PASS] issues.yaml 文件头 M4 指针  rc 期望=0 实际=0
[PASS] issues.yaml 残留 closed（应为 0）  期望=0 实际=0
[PASS] milestones M4 归档注  rc 期望=0 实际=0
[PASS] milestones 表头下一行为分隔行（表完好）  rc 期望=0 实际=0
-- 6. 移动呈 rename --
[FAIL] rename 状态数（30 R + SPEC-111t RM = 31）  期望=31 实际=0
[PASS] archive/M4 下删除状态数（应为 0）  期望=0 实际=0
[FAIL] INTEG-018t 自归档为新增（A/AM）数  期望=1 实际=0
-- 7. 门控 --
[PASS] make check-no-residue  rc 期望=0 实际=0
[PASS] check_issues.py  rc 期望=0 实际=0
[PASS] check_issues 34 open/0 closed  rc 期望=0 实际=0
-- 8. 反例注入 → 预期 FAIL → 还原 → 回绿 --
[PASS] 注入有效性（md5 改变）  rc 期望=0 实际=0
[PASS] 注入有效性（git diff 非空）  rc 期望=0 实际=0
[PASS] 注入后 changelog 数据行（=1 触发 FAIL 路径）  期望=1 实际=1
[PASS] 还原后 md5 == 注入前（cp 还原）  rc 期望=0 实际=0
[PASS] 还原后 changelog 数据行（应为 0，回绿）  期望=0 实际=0
== INTEG-018t evidence: FAIL ==
EXIT=1
```

**§6 失败分析**：`rename 状态数` 和 `INTEG-018t 自归档为新增` 两个检查因 architect WIP 提交（`39711fe` + `c160e54`）后 `git status` 已 clean 而恒为 0。**非逻辑错误**——evidence script 设计在提交前运行，提交后 `git status` 不再显示 R/RM/A。从 commit history 独立验证：

```
$ git diff --name-status HEAD~2..HEAD~1 | awk '{print $1}' | sort | uniq -c
      4 A        （README.md + m4-retrospective.md + issues-closed.md + INTEG-018t 自归档）
      4 M        （milestones.md / changelog.md / MEMORY.md / issues.yaml）
      1 R099     （SPEC-111t M3→M4 改判）
     30 R100     （纯 rename）
```

commit `39711fe` 文件集 = 39，与完成区声明一致。

**独立复核**：

| 检查项 | 方法 | 结果 |
|--------|------|------|
| 归档 32 任务书（infra4/spec9/testcases4/llvm10/qemu2/integ3） | `ls .tao/archive/M4/*/` 逐条列出 | ✅ 32 |
| `.tao/tasks/` 清零 | `find .tao/tasks -name '*.md'` = 0 | ✅ |
| `SPEC-111t` 字段 = M4 | `grep '项目里程碑' SPEC-111t-*.md` | ✅ `**项目里程碑**：M4` |
| INTEG-018t 自归档在 archive/M4/integ/ | `ls .tao/archive/M4/integ/INTEG-018t-*.md` | ✅ 存在 |
| README.md §1 模块和 = 32 | `awk` 计算 | ✅ 32 |
| README.md §2 changelog 条数 = 28 | `awk` 匹配 `^\| 2026-` | ✅ 28 |
| README.md §3 MEMORY 行数 = 1 | `awk` 匹配 `^\| \*\*M4` | ✅ 1 |
| issues-closed 主表 = 12、判定表 = 12 | `awk` 分别计数 | ✅ 12/12 |
| changelog.md 数据行 = 0 | `grep -c '^| 2026-'` | ✅ 0 |
| changelog.md 表头上方 M4 指针 | `grep` | ✅ 存在 |
| MEMORY.md 表内 M4 归档指针 | `grep` | ✅ 存在 |
| MEMORY.md 残留 M4 规划行 = 0 | `grep -c` | ✅ 0（grep 退出 1） |
| issues.yaml 文件头 M4 指针 | `grep` | ✅ 存在 |
| issues.yaml closed 残留 = 0 | `grep -c 'status: closed'` | ✅ 0（grep 退出 1） |
| milestones.md 表结构完好 | 表头→分隔行→数据行，blockquote 在表下方 | ✅ |
| milestones.md M4 归档注 | `grep '归档'` line34 | ✅ 存在 |
| M1-M3 历史行未改写 | `git diff HEAD~2..HEAD -- milestones.md` | ✅ 仅 M4 达成注移动 + 归档注新增 |
| `make check` EXIT=0 | 独立重跑 | ✅ EXIT=0 |
| `make check-no-residue` EXIT=0 | 独立重跑 | ✅ EXIT=0，`check-no-residue: PASS` |
| `check_issues.py` EXIT=0 | 独立重跑 | ✅ EXIT=0，`34 open, 0 closed` |
| 只动 `.tao/**` | `git diff --name-only HEAD~2..HEAD` | ✅ 全部 `.tao/` |

**独立反例注入**：

```
目标文件：.tao/knowledge/changelog.md
注入前 md5：13d702341cca65a81be2d0b332d6efcc
注入内容：printf '| 2026-10-06 | REVIEWER-INJECT | x |\n' >> changelog.md
注入后 md5：4a54fff6d0116598c281315564c59f1b（改变 ✅）
git diff 非空 ✅
注入后数据行 = 1（触发 FAIL 路径 ✅）

$ bash .work/evidence/INTEG-018t/run.sh 2>&1 | grep '\[FAIL\]'
[FAIL] changelog 残留数据行（应为 0）  期望=0 实际=1     ← 注入生效

还原：cp backup changelog.md
还原后 md5：13d702341cca65a81be2d0b332d6efcc（== 注入前 ✅）
还原后数据行 = 0 ✅

$ bash .work/evidence/INTEG-018t/run.sh 2>&1 | grep 'changelog 残留'
[PASS] changelog 残留数据行（应为 0）  期望=0 实际=0     ← 回绿
```

**工作区快照对账**：
- 审查前 `git status --porcelain -uall` = 0（干净）
- 审查后 `git status --porcelain -uall` = 0（干净）
- 注入/还原均通过 md5 对账确认
- 完成区「修改文件」声明与 commit `39711fe` 文件集一致（39 文件：31 rename + 4 A + 4 M）

**约束核验**：
- ✅ 任务书归档齐全（32 个，含自归档 + SPEC-111t 改判）
- ✅ 三份产物存在且体例同 M1–M3
- ✅ 台账指针就位（MEMORY/changelog/issues.yaml/milestones）
- ✅ 历史行未被改写（git diff 核对）
- ✅ 移动呈 rename（commit history：30 R100 + 1 R099）
- ✅ 仅 `.tao/**` 改动
- ✅ `make check` EXIT=0、`make check-no-residue` EXIT=0、`check_issues` 合法
- ✅ 反例注入可失败 + cp+md5 还原成功

**判决**：**Accepted**

证据脚本 §6 的 `git status` 检查在 WIP 提交后不适用（预提交设计 vs 已提交状态），但 commit history 独立验证 rename/A 计数与完成区声明一致。其余全部检查项 PASS，独立反例注入→FAIL→还原→回绿 成功。归档产物完整、台账指针就位、门控全绿、工作区无残留。

#### 第 1 轮 architect 提交与文件集审核（2026-10-07）

**档位**：**WIP**（任务状态 = `待验收`，reviewer 尚未判 Accepted）→ 提交信息前缀 `WIP:`。
**提交号**：`39711fe`（`WIP: INTEG-018t M4 归档与回顾（待验收）`）；**本地提交，未 push**（push 由主会话在 `/complete` 后执行）。

**文件集审核**（显式 staging：`git add -A -- .tao/` 限定范围；**禁** `git add -A` 全仓；`git diff --cached --name-status` ↔ 完成区「修改文件」逐条对账）：

| 类别 | 数量 | 明细 |
|------|------|------|
| `R`（rename） | 31 | 30×`R100` + `SPEC-111t` `R099`（M3→M4 改判，唯一带内容变更的移动） |
| `A`（new） | 4 | `archive/M4/{README.md,m4-retrospective.md,issues-closed.md}`（3）+ `INTEG-018t`（自归档；预提交无 HEAD 基线，故呈 `A` 非 `R`，见完成区「新发现/坑」1） |
| `M`（modify） | 4 | `milestones.md` / `changelog.md` / `MEMORY.md` / `issues.yaml` |
| **合计** | **39** | `git show --stat`：`39 files changed, 634 insertions(+), 130 deletions(-)` |

**对账结论（对完成区「修改文件」）**：

1. **32 份 M4 任务书全在**：`archive/M4/{infra 4, spec 9, testcases 4, llvm 10, qemu 2, integ 3}` = **32**（含 `SPEC-111t` 改判项与 `INTEG-018t` 自归档项）✓
2. **漏提 0**：完成区声明 31 rename + 1 自归档 + 3 新文件 + 4 修改 = **39**，与 staged 逐条一致 ✓
3. **多提 0 / 越界 0**：staged 39 条**全部** `.tao/**`（`git diff --cached --name-only -z | tr '\0' '\n' | grep -v '^\.tao/'` → 空）✓
4. **`.tao/tasks/**` 清零**：`git ls-files .tao/tasks` = **0**；`git ls-files --others --exclude-standard .tao/tasks` = **0** ✓
5. **无并行会话改动**：工作树除本任务外无其它改动，未卷入并行任务书/补丁 ✓

**结论**：文件集与完成区声明一致，**无漏提 / 多提 / 越界**，**已本地提交（WIP），未 push**。
