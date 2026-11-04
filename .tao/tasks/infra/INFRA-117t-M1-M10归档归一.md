# INFRA-117t: M1–M10 归档归一

**模块**：infra
**项目里程碑**：M10 后（维护）
**依赖**：`INFRA-116t`（Process-04 规则 + `check_archive.py` 就绪）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；临时产物只放 `运行期临时目录`，证据落 `运行期证据（已清理，未归档）`）

## 预检（只读，已现场核实）

- `milestones.md` 现有 **74** 行流水：M9 仅 `INTEG-037m`（2026-10-25 00:00）1 行；M10 期 **70** 行；M10 后维护 **3** 行（`INFRA-115t` / `QEMU-077t` / `INFRA-113t`）。
- M9 的 68 行流水在 `M9 归档` 提交 `e70fb74d` 中已删除，**只能从 `git show e70fb74d^:.tao/knowledge/milestones.md` 恢复**（该父提交中 2026-10-19~10-24 的 68 行；其中 `SPEC-172t` 为 `待验收` + `（登记）`，任务书现为 `已验证`，提交 `bcd5f773` 时间 **2026-10-24 23:57**）。
- M9 任务书 = 68 模块册 + 根级 `INTEG-037m`；M10 任务书 = 70 模块册 + 根级 `INTEG-052m`（`m` 册按 `里程碑` 状态**不入流水**，见其 §说明）。
- `M7/notes/` 5 文件共 **746** 行；`M7/notes/INTEG-027t-report.md` 状态 `待验收`，其余 4 份无任务书字段。
- **事实更正（相对派单原文）**：M6 `INTEG-023k` **并非缺状态**——第 2 行内联 `**模块**：integ　**项目里程碑**：M6　**状态**：已验证`，值已精确；117 只做**格式归位**（拆成独立行），不重复插入、不改值。
- M2 两册确为带括注状态：`TESTCASES-019t` = `已验证（第 3 轮返工后）`；`SPEC-064t` = `已验证（**2026-10-01 主会话补填完成区**——…）`。
- `check_archive.py` 由 116 交付；116 的 `--pending-ok` 仅豁免 M2 两册、`M7/notes`、M9/M10 README 缺节；117 完成后必须全绿严格。

## 接口规范

### A. M9 README（`.tao/archive/M9/README.md`）

1. 新增 `## 2 任务流水（冻结）`：**69 行** =
   - 68 行：从 `git show e70fb74d^:.tao/knowledge/milestones.md` 取 2026-10-19~10-24、任务号全部落在 M9 归档册的行；
   - 1 行：现有 `INTEG-037m | 已验证 | 2026-10-25 00:00`。
   - 列固定 `| 编号 | 状态 | 完成时间 | 一句改动 |`；`SPEC-172t` 状态改 `已验证`、时间用 `2026-10-24 23:57`；其余行去掉 `（登记）`；**每行状态必须等于归档任务书 `**状态**`**。
2. 现有 `## 2 终局证据` → `## 3 终局证据`。
3. 新增 `## 4 MEMORY 摘录`：M9 归档时已移出，写 `0 行` + 指针（`.tao/knowledge/MEMORY.md` 归档指针 / `m9-retrospective.md`）。
4. 新增 `## 5 指针`：合并现 `## 3 相关索引`（issues、核验册、回顾）+ `milestones.md` 归档指针。
5. 流水 68 行与 `M9/{infra,llvm,qemu,spec,testcases}/*.md` **一一对应**（根级 `INTEG-037m` 可入流水，已入）。

### B. M10 README（`.tao/archive/M10/README.md`）

1. 新增 `## 2 任务流水（冻结）`：**70 行**，取自 `milestones.md` 现行 M10 期行（排除 `INFRA-115t` / `QEMU-077t` / `INFRA-113t` 与 `INTEG-037m`）；状态/时间/一句改动原样，去掉 `（登记）`（M10 行应无）；`INTEG-052m` 不入流水（`m` 册 `里程碑` 状态，沿用其自身口径）。
2. 现有 `## 2 终局证据` → `## 3 终局证据`。
3. 新增 `## 4 MEMORY 摘录`：`0 行` + 指针（M10 归档时已移出）。
4. 新增 `## 5 指针`：合并现 `## 3 相关索引 / 指针` + 更新「里程碑定义/达成」措辞（流水已冻结在本 README §2，活台账不再保留 M10 行）。
5. 70 行与 `M10/{infra,integ,llvm,qemu,spec,testcases}/*.md` 一一对应。

### C. `.tao/knowledge/milestones.md`

1. 删除 **70** 条 M10 期流水行 + `INTEG-037m` 行（共 71 行）；**保留** `INFRA-115t`、`QEMU-077t`、`INFRA-113t`、`INFRA-116t`、`INFRA-117t`。
2. 新增 `> **M9 归档指针（2026-11-01）**：… 流水 69 行已冻结到 .tao/archive/M9/README.md §2`。
3. 改写现有 M10 归档指针：「本页保留 M10 任务流水行」→「流水 70 行已冻结到 `.tao/archive/M10/README.md §2`，本页仅留 M10 后维护行」。
4. 保留 `**项目里程碑 = M10**` 断言（本任务不改当前里程碑号）。

### D. 状态规范化与格式归位（历史内容不改）

1. `M2/testcases/TESTCASES-019t-*.md`、`M2/spec/SPEC-064t-*.md`：`**状态**` 行改为**精确** `**状态**：已验证`；原括注**原样**移到紧跟其后的 `> **状态注记**：…`（保留全部文字），不删改正文。
2. `M6/integ/INTEG-023k-*.md`：把第 2 行拆为三行独立字段（模块 / 项目里程碑 / 状态），值不变；**不新增重复状态行**。
3. `M7/notes/INTEG-027t-report.md` 的 `待验收` 随 `notes/` 删除而消失；不另建任务书。

### E. M7 `notes/` 并入回顾

1. 将 5 份文件**全文**并入 `.tao/archive/M7/m7-retrospective.md` 附录，按 5 个主题分节（建议 `## 附录 A–E`：gate-tiering-design / embench-analysis / LLVM-070t-rootcause / SPEC-129t-count-table / INTEG-027t-report），保留原文与行数（746 行，允许只加标题与来源行）。
2. `git rm -r .tao/archive/M7/notes/`；更新 `.tao/archive/M7/README.md` §4 指针为「附录 A–E 见 `m7-retrospective.md`」。
3. 更新**活文档**中的 `M7/notes` 引用（已现场定位）：
   - `docs/Process-07-门控分层规范.md`（文件头 §缘起、§1 层边界注）→ 指向 `m7-retrospective.md` 附录；
   - `docs/Machine-00-执行环境分层-Draft.md`（2 处）→ 同上；
   - `.tao/archive/M7/README.md`。
   - **不改**已归档任务书内的历史路径（如 `M7/infra/INFRA-070t`、`M7/integ/INTEG-035m`、`M8/infra/INFRA-071t`）——历史快照，保留溯源。
4. `make check-knowledge-refs` 必须 rc=0（悬空引用清零）。

### F. 模板最小统一（不重写内容）

- M1–M6：在 `## 2. changelog` / `## 2. 台账快照` 标题下加**一句**「本节 = 任务流水（冻结）历史别名」；不重命名、不搬行、不改内容。
- M7/M8：已用「任务流水与实质改动」，保持；只在标题后补「（冻结）」同义说明（可选，不得改表）。
- M9/M10：按 A/B 补齐五节，成为后续归档模板实例。

### G. 门控收口

1. `Makefile` 去掉 `check-archive` 的 `--pending-ok`（目标改为严格默认）。
2. `tools/infra/check_archive.py` 删除 `PENDING_117` 常量与 `--pending-ok` 分支；`--self-test` 去掉过渡用例、保留 ≥6 类注入。
3. `check_milestones_fresh.py` A2：若删行后出现「`m` 册列号必须入流水」的假红，按新口径最小调整——**`m` 册列出的号在归档任务文件名命中即可**（已归档豁免），不强制活流水有行；不得放宽其它断言。
4. `check_milestone_tasks.py`：**不在 L1**，本任务不调整；M11 未定义期间 `make check-milestone` 因「无活 `m` 册」**预期红**（M10 README 已记录），117 只在完成区披露。

## 验收标准

1. `python3 tools/infra/check_archive.py` **rc=0**（严格）；`grep -R "pending-ok\|PENDING_117" Makefile tools/infra/check_archive.py` = **0 命中**。
2. `make check` **rc=0**（L1 含 `check-archive` 严格）。
3. `python3 tools/infra/check_milestones_fresh.py` **rc=0**；流水表**只剩** 5 行（`INFRA-115t`/`QEMU-077t`/`INFRA-113t`/`INFRA-116t`/`INFRA-117t`），无 M9/M10 历史行；M9/M10 归档指针各 1 行。
4. `python3 tools/infra/check_tasks.py` **rc=0**（0 漏收尾）。
5. M9：流水 **69** 行，68 模块册 + `INTEG-037m` 一一对应；`SPEC-172t` = `已验证` / `2026-10-24 23:57`，全表无 `（登记）`。M10：流水 **70** 行与 70 模块册一一对应，无 `（登记）`。
6. 状态规范化：`grep -n "^\*\*状态\*\*" M2 两册` = 精确 `已验证`，括注在 `> **状态注记**`；`INTEG-023k` 三字段分行且值不变。
7. `test ! -e .tao/archive/M7/notes`；5 份原文行数合计 **746** 行出现在 retrospective 附录（逐文件计数对账）；`grep -R "M7/notes" docs .tao/archive/M7/README.md` = 0（归档任务书历史引用不计）。
8. `git diff --name-only` 仅含：`M1–M10/README.md`（M9/M10 为主，M1–M8 仅别名句/指针）、M2 两册、M6 `INTEG-023k`、`M7/m7-retrospective.md`、`M7/README.md`、删除 `M7/notes/**`、`docs/Process-04`（§8 过渡段改最终态）、`docs/Process-07`、`docs/Machine-00`、`milestones.md`、`Makefile`、`tools/infra/check_archive.py`、`tools/infra/check_milestones_fresh.py`（仅必要）、本任务书。**不改** M10 归档 `tasks/m`；不补/不删任何 `m`。
9. 证据 `运行期证据脚本（已清理，未归档）` 一键重跑（逐条命令 + rc），reviewer 独立重跑 + 一次反例注入（`cp`+md5 还原）。

## 完成区
**测试结果**：`运行期证据脚本（已清理，未归档）` **24/24 PASS、rc=0**；`make check` rc=0；`check_archive.py` 严格 rc=0；`--self-test` 13/13（12 类注入）；`check_milestones_fresh` rc=0（5 行）；`check_tasks`（报告型，验收 4）rc=0、`--strict` rc=0（收尾后）；`check-knowledge-refs` rc=0；`make check-milestone` rc=2（**预期红**：当前 M10 无活 `m` 册）。
**修改文件**：M1–M10 `README.md`（M9/M10 五节+流水 69/70；M1–M8 仅冻结别名句）；M7 `m7-retrospective.md`（附录 A–E）；`git rm -r .tao/archive/M7/notes/`（5 文件）；M2 `TESTCASES-019t`/`SPEC-064t`；M6 `INTEG-023k`；`.tao/knowledge/milestones.md`；`Makefile`；`tools/infra/check_archive.py`；`docs/Process-04`/`Process-07`/`Machine-00`；本任务书；`运行期证据脚本（已清理，未归档）`。
**验收结果**：M9 **69** 行（68 模块册+`INTEG-037m`；`SPEC-172t`=已验证/2026-10-24 23:57；全表无登记注），行状态与册 **100% 相等**；M10 **70** 行 == 70 个 `t` 模块册（无 `INTEG-052m`/`INFRA-113t`），状态全等；M7 附录 A–E **5/5** md5+行数（48/355/86/40/217=**746**）；M2 两册状态精确+`状态注记`、M6 三字段独立行；`grep pending-ok\|PENDING_117`=**0**、`grep M7/notes docs`=**0**；`git diff --name-only HEAD` 白名单 **26** 文件；反例注入 M10 状态 → `check_archive` **rc=1** → `cp`+md5 还原 → **rc=0**。
**新发现/坑**：M9 `SPEC-172t` 完成时间由登记 15:20 改为 23:57 后须按时间前移（已移到 `INTEG-037m` 之后）；现行台账 M10 期含维护项 `INFRA-113t`，按 5 行维护清单剔除后恰 70；`m7-retrospective` 原文自带 `---` 与 `## 附录` 标题，朴素截断会误判，证据脚本改用精确标题边界；非 ASCII 路径须 `git -c core.quotepath=false`。
**遗留问题**：无功能遗留。`make check-milestone` 预期红（M11 未定义、无活 `m` 册），`check_milestone_tasks.py` 按任务书不改；`check_milestones_fresh.py` 无需调整（A2 已豁免归档号）；`check_tasks --strict` 在待验收阶段为 1、收尾置 `已验证` 后为 0；`INFRA-113t` 仍为 `待开始`（非本任务范围）。

## 审阅记录

### 第 1 轮 engineer 自审

结论：改动逐行复核（门控脚本 / 两个 README 流水 / 台账 / 文档引用）；findings 全部修复，状态置 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| M9 `SPEC-172t` 改 23:57 后仍留在 15:20 位置，流水非倒序 | ✅已修 | 移到 `INTEG-037m` 之后 | 脚本核对 M9/M10 全部相邻时间 `order_bad=0` |
| 证据脚本以首个 `---`/`## 附录` 截断，embench 正文自带两者 ⇒ 误判 327/355 | ✅已修 | 改用五个精确附录标题为边界 | 附录 A–E 5/5 md5+行数（746）PASS |
| 白名单检查被 git 八进制转义路径误报 | ✅已修 | `git -c core.quotepath=false diff --name-only HEAD` | 26 文件均在白名单，rc=0 |
| `check_archive.py` 自检注释/Process-04 §8 仍写「过渡边界」 | ✅已修 | 改为「12 类注入，各自可达」 | `grep pending-ok\|PENDING_117`=0；self-test 13/13 |
| M9/M10 README 说明句含字面 `（登记）`，简单 grep 会歧义 | ✅已修 | 改为「全表不含登记注记」 | 两 README `grep （登记）`=0；数据行脚本复核 |
| `check_tasks --strict` 在「`待验收`+完成区已填」时 rc=1（工具设计即「漏 /complete」判据），与主会话口头验收 rc=0 冲突 | ✅已披露（不改工具） | 证据脚本用非 strict 验收（任务书验收 4）+ strict 预期红记录；完成区显式说明 | 证据 24/24 PASS；strict rc=1 命中「① 漏收尾」 |

### 第 1 轮 reviewer 验收（2026-11-01）

判决：**Accepted**（3 条非阻断建议，见末尾，交 architect 收尾处置）。日志：`运行期临时日志`。完成区数字（24/24、69/70、746、26）与我实测**逐项一致**，无采信项。

**重跑记录（reviewer 独立执行，rc 均为现场实测）**
- `运行期证据脚本（已清理，未归档）` → **24/24 PASS，exit=0**：`check-archive 严格 rc=0`、`--self-test rc=0`、`make check rc=0`、`check-milestones-fresh rc=0`、`check-tasks rc=0`、`--strict rc=1`（含「① 漏收尾」，预期红）、`check-knowledge-refs rc=0`、`make check-milestone rc=2`（含「无 m 册」，**预期红如实核**）。
- 逐项独立重跑：`check_archive.py` rc=0；`--self-test` 13/13（12 类注入）；`make check` rc=0（`repository checks (L1): PASS`）。
- **反例注入①（独立，选 M9 非脚本所用的 M10 行）**：`SPEC-172t 已验证→待验收`，md5 `563e71d3→8c19086f` ⇒ rc=**1**，命中 `[M9/flow/SPEC-172t] 流水状态 != 任务书状态`；`cp` 还原 md5 `563e71d3` 相等 ⇒ rc=**0**。
- **反例注入②（结构性）**：重建 `.tao/archive/M7/notes/r.md` ⇒ rc=1，命中 `[M7/dir/notes]`；`rm -rf` 后 rc=0。前/后 `git status` 快照逐行一致，目标文件 md5 全部复原。

**约束逐条核验（直核，不依赖证据脚本）**
- 验收 1/2/3/4：见上 rc；`milestones.md` 仅 **5** 行（115/077/113/116/117），M9/M10 归档指针各 1，`**项目里程碑 = M10**` 在。
- 验收 5：M9 **69** 行 = 68 模块册 + 根级 `INTEG-037m`（册 `已验证` 相符），无重复、**时间倒序**、全文 `（登记）`=0；`SPEC-172t` = `已验证 / 2026-10-24 23:57`。M10 **70** 行与 70 个 `t` 册 ID 集合**全等**、逐行状态 == 册 `**状态**`、无登记注、无 INFRA-113t/INTEG-052m 行。
- 验收 6：M2 两册 `**状态**：已验证` 精确 + `> **状态注记**` 逐字保留（diff 核对）；M6 `INTEG-023k` 三行独立、值不变（diff 仅拆行）。
- 验收 7：`notes/` 不存在；附录 A–E 与 `git show HEAD:` 原文**逐行一致**（48/355/86/40/217=**746**）；`grep -R "M7/notes" docs .tao/archive/M7/README.md`=0；Process-07 §缘起/§1、Machine-00 2 处、M7 README 指针均指向 retrospective 附录。
- 验收 8：`git diff --name-only HEAD` = **26** 文件与白名单逐一相符；M9/M10 文件清单与 HEAD 完全一致（72/74，**无增删 m**）；M1–M8 README 各仅 +1 别名句；`Makefile` check-archive 严格、`grep pending-ok|PENDING_117`=0；Process-04 §8 为最终态无过渡 flag。
- 验收 9：证据脚本逐条断言均有**可达 FAIL 路径**（rc 门控 / md5 不等 / 计数不等 / 注入命中键），无恒真或双写同果；注入非空、还原 md5 相等。

**非阻断建议（不改判 Accepted）**
1. `m7-retrospective.md` 附录重号歧义：新并入 `## 附录 A`(L208)/`附录 B`(L263) 与 embench 原文自带 `## 附录 A：证据脚本与临时产物`(L597)/`## 附录 B：关键文件索引`(L606) 同号；建议在 L202 引言加一句消歧注（不改原文、门控按精确标题串匹配不受影响）。
2. `run.sh:161` 登记注检查只扫时间列；本次我全文 grep 已证两 README 无 `（登记）`，建议改全行扫描更严。
3. `run.sh` 白名单只验「改动 ⊆ 白名单」，建议补「集合相等」断言（本次已由 reviewer 独立核对）。
