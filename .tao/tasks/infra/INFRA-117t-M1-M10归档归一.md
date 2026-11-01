# INFRA-117t: M1–M10 归档归一

**模块**：infra
**项目里程碑**：M10 后（维护）
**依赖**：`INFRA-116t`（Process-04 规则 + `check_archive.py` 就绪）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根 `/mnt/tao/DADAO-v5`；临时产物只放 `/tmp/opencode/INFRA-117t/`，证据落 `.work/evidence/INFRA-117t/`）

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
8. `git diff --name-only` 仅含：`M1–M10/README.md`（M9/M10 为主，M1–M8 仅别名句/指针）、M2 两册、M6 `INTEG-023k`、`M7/m7-retrospective.md`、`M7/README.md`、删除 `M7/notes/**`、`docs/Process-07`、`docs/Machine-00`、`milestones.md`、`Makefile`、`tools/infra/check_archive.py`、`tools/infra/check_milestones_fresh.py`（仅必要）、本任务书。**不改** M10 归档 `tasks/m`；不补/不删任何 `m`。
9. 证据 `.work/evidence/INFRA-117t/run.sh` 一键重跑（逐条命令 + rc），reviewer 独立重跑 + 一次反例注入（`cp`+md5 还原）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
