# INFRA-139t: 里程碑台账拆出「待开始」表（不再把未开工任务混进流水）

**模块**：infra
**项目里程碑**：M11
**依赖**：无
**状态**：已验证

## 用户授权（原话）

> 「milestone中，是不是把待开始的任务单独列出来，要不然实在找不到，其完成时间可以不写，只会增加困惑性」

即：**`待开始` 任务单独成表、不写时间**；流水表只留已开工/已完成的。

## 背景与事实

- 现状 `milestones.md` 只有一张「任务流水」，`待开始` 行与 `已验证` 行混在一起，靠 `（登记）` 标注区分；未开工任务还被迫填一个「登记时间」。
- 实证痛点：巡检时要在一张 100 行表里找 6 条未开工任务；「登记时间」既不是完成时间也不参与任何判据，只增加误读。
- 门控 `tools/infra/check_milestones_fresh.py` 现按单表实现 5 条断言（A1 状态一致 / A2 覆盖 / A3 长度 / A4 次序 / A5 格式），`--self-test` 内置五类注入。

## 目标

### 1. `milestones.md` 版式

```markdown
## 任务流水（已开工）

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| …（仅 待验收 / 待返工 / 已验证）…

## 待开始（未开工）

| 编号 | 一句改动 |
| --- | --- |
| …（仅 待开始，无时间列，不要求排序）…
```

- 两个二级标题**都必须存在**（无待开始任务时，表可为空，但标题保留）。
- 待开始表**不写状态列、不写时间**。

### 2. 门控改造（`check_milestones_fresh.py`）

- **A1 状态一致**：流水行（表状态 == 任务书状态）；待开始行的任务书状态**必须**是 `待开始`。
- **A2 覆盖**：两张表的并集覆盖全部任务书 + `INTEG-*m` 所列号 + 正文号（归档号豁免，悬空号 FAIL）。
- **A3 长度**：两张表的「一句改动」均 ≤120 字符。
- **A4 次序**：**只对流水表**按完成时间倒序（同一时间按编号升序）；待开始表不判次序。
- **A5 格式**：
  - 流水表：恰好 4 格；状态 ∈ {`待验收`,`待返工`,`已验证`}（**出现 `待开始` ⇒ FAIL**）；`已验证` 不得带 `（登记）`，其余带；
  - 待开始表：恰好 2 格、无时间列、无状态列；同一编号不得重复；
  - 两表「一句改动」均不得含 `.work/<具体路径>`。
- **fail-closed**：任一标题/表缺失、表无表头、两表皆空 ⇒ FAIL。
- `--self-test` 五类注入按新规则重写（至少含：待开始在流水表 ⇒ FAIL、待开始行缺 ⇒ 覆盖 FAIL、待开始行带时间 ⇒ FAIL、状态不符 ⇒ FAIL、次序错 ⇒ FAIL）。

### 3. 文档同步

- `docs/Process-04-里程碑归档规范.md`：归档时的取行口径（流水表按日期取；待开始表**不归档**，随里程碑迁移或重立）。
- `docs/Process-07-门控分层规范.md` 的 `check-milestones-fresh` 描述行按新规则改写。

## 范围 / 非范围

**在范围内**：`tools/infra/check_milestones_fresh.py`、`.tao/knowledge/milestones.md`（版式与现有 6 条 `待开始` 行迁移）、`docs/Process-04`、`docs/Process-07`、本任务书。

**不在范围**：其它门控、任务书状态机、`/complete` 流程、`milestones.md` 的历史行内容。

## 验收标准

1. `make check-milestones-fresh` rc=0；现有 6 条 `待开始` 全部出现在「待开始」表、流水表内 `待开始` 行数 = 0。
2. 五类注入（逐条给真实 rc）：① 把一条 `待开始` 放回流水表 ⇒ FAIL；② 删一条待开始行 ⇒ 覆盖 FAIL；③ 给待开始行加时间列 ⇒ FAIL；④ 表状态与任务书不符 ⇒ FAIL；⑤ 流水表次序打乱 ⇒ FAIL；均 `cp`+md5 还原后回绿。
3. `--self-test` rc=0（新五类注入）。
4. `make check`（L1）rc=0（`check-patch-tree` 若因并发 gem5 任务红，核实归属）。
5. `docs/Process-04`、`docs/Process-07` 描述与实际一致（人工核对清单）。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- 这是**门控语义变更**（新增「待开始不得进流水表」），已获用户授权；不得顺手放宽其它断言。
- 迁移现有 6 行时**只搬不改**：编号与「一句改动」逐字保留。

## 完成区

**测试结果**：通过 6/6（门控 PASS / self-test PASS / 五类注入逐条 rc=1 / 还原回绿 / 结构断言 / L1 仅 `check-patch-tree` 并发红）
**修改文件**：`tools/infra/check_milestones_fresh.py`、`.tao/knowledge/milestones.md`、`docs/Process-04-里程碑归档规范.md`、`docs/Process-07-门控分层规范.md`、本任务书
**验收结果**：
- `make check-milestones-fresh` rc=0（流水 94 行 / 待开始 7 行；两表并集覆盖 101 行）
- `--self-test` rc=0（干净基线 PASS + 五类注入各自 FAIL）
- 五类注入逐条 rc=1 且 marker 命中：①待开始放回流水表 ②删待开始行→覆盖 FAIL ③待开始加时间列→须 2 格 ④状态不符→MISMATCH ⑤流水次序打乱→逆序；均 `cp`+md5 还原回绿
- `make check`（L1）：除 `check-patch-tree` 外全绿；该红因并发 GEM5-028t/QEMU-085t 改写共用 `.work/source`（两工作树补丁未提交），本分支 `components/` 相对 HEAD 无差异 ⇒ 非本任务引入
- 迁移：原表 101 行 → 流水 94 + 待开始 7；现场实有 8 条 `待开始`（任务书「6 条」为旧口径）全部逐字搬入，编号与一句改动未改
**新发现/坑**：任务书写的 6 条与现场 8 条不符，按现场全量迁移；worktree 的 `.work` 软链共享主树，证据/临时文件须落证据目录，写 `/tmp/opencode/<任务ID>/` 会落进 worktree 根污染仓库
**遗留问题**：无

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 单表断言不足以判双表（标题/表头/两表皆空） | ✅已修 | 重写 `section_rows` 双小节解析 + 五断言 + fail-closed | `--self-test` rc=0；真实树 rc=0 |
| 任务书「6 条待开始」与现场 8 条不符 | ✅已修 | 按现场 8 条全量逐字迁移（INFRA-139t 完成时按状态移回流水） | 两表合计 101 行 = 迁移前 101 行 |
| 证据脚本临时文件落在 worktree 根 | ✅已修 | 临时路径改指证据目录 | `git status --porcelain -uall` 仅 5 个任务文件 |
| 结构断言含恒真项 | ✅已修 | 改「流水编号无重复 / 两表无交集」等可达 FAIL 断言 | 证据脚本结构段全 PASS |

### 第 1 轮 reviewer 验收

**重跑（我自己的命令 + 真实 rc；注入全部自造，不复用 engineer 脚本，`cp`+md5 `e849636b…` 还原、每次还原后回绿）**
- `make check-milestones-fresh` → **rc=0**（`流水 94 / 待开始 7 / 两表 101 行`）；`--self-test` → **rc=0**（基线 rc=0 + 五类注入各自 rc=1 且 marker 命中）
- 独立五类注入（临时树 `--root`）：① 待开始放回流水 **rc=1** 唯一 violation `L16 QEMU-085t: 流水表不得出现 \`待开始\``；② 删待开始行 **rc=1** `覆盖: 活任务册 TESTCASES-103t 未列入台账表`；③ 待开始加时间列 **rc=1** `待开始行须恰好 2 格…实得 3 格`；④ 表状态≠任务书 **rc=1** `INFRA-139t: 表 \`待返工\` ≠ 任务书 \`待验收\``；⑤ 流水次序打乱 **rc=1** `次序: L16 INFRA-139t(11:17) 应排在 L15 INFRA-133t(10:26) 之前`
- fail-closed / 其余断言独立注入（均 rc=1 → 还原 rc=0）：缺「待开始」标题、缺「任务流水（已开工）」标题、两表皆空（`两表皆无数据行 ⇒ vacuous FAIL`）、待开始表头被改、同号两表重复、A3 121 字、A5 待开始重复行
- `make -k check` → **rc=2**，唯一失败 target = `check-patch-tree`（4 problem：qemu `linux-user/mmap.c` ⑨⑥ + gem5 `se_workload.cc` ⑨⑥），`check-milestones-fresh` 在 L1 内 PASS。归属证据：本树 `git status -- components/` 与 `git diff HEAD -- components/` 均空；并发树 `/tmp/opencode/QEMU-085t` 有 `components/qemu/patches/linux-user/mmap.c.patch` 改动、`/tmp/opencode/GEM5-028t` 有 `components/gem5/patches/src/arch/dadao/se_workload.cc.patch` 改动 ⇒ 非本任务引入
- 工作区快照对账：验收前后 `git status --porcelain -uall` 均为**同一 5 个文件**，`milestones.md` md5 前后同为 `e849636b4d1f8ad46e4cb9e1a4bfa9d1`（我未写入工作树）

**无行丢失（逐行比对）**：HEAD 版 101 数据行 vs 工作树 101 行（流水 94 + 待开始 7）；按「编号 + 一句改动」配对 diff **0 差异**，无缺号、无多号、无重复；唯一状态变化 = 本册 `INFRA-139t 待开始→待验收` 且留在流水表。任务书「6 条」实为现场 8 条（HEAD 中 `待开始` 状态行 = 8）⇒ engineer 披露属实。

**约束核验**：改动 = 恰 5 文件（gate / milestones / Process-04 / Process-07 / 本任务书），`components|spec|contracts|tests|Makefile` 零 diff；完成区 **13 行 ≤30**、无绝对运行期路径；7 条待开始行对应任务书 `**状态**` 逐个现场核全为 `待开始`；本册行在流水表且与任务书一致。A1–A5 读码核对：A5 第 213–217 行在时间解析**之前**无条件 `errors.append` ⇒ 待开始进流水表为硬 FAIL，未被覆盖/格式分支吞掉。

**文档**：`docs/Process-04`（§归档取行 + §文件动作表两处，待开始表不归档）与 `docs/Process-07` 描述行已按双表改写，与实际行为一致；未发现 Process-04/07 内残留单表口径。

**遗留（文档级 finding，不阻断，交 architect 收尾）**：① `AGENTS.md` L106/L108「与 `milestones.md` **有流水行**」仍是单表口径；② `Makefile` L1264-1265 注释仍列单表断言，且引用已不存在的 `milestones.md「体例约定（硬约束）」`；③ `.opencode/commands/complete.md` L83 仍写「任务流水」表、列名「日期」。三者均在本任务书范围外、非门控判据。

**判决：Accepted** —— 验收标准 1–6 在我自己的重跑下全部满足（仅上述文档级 finding）。

#### 收尾（architect，2026-11-08 11:35）

- 判决 Accepted：reviewer 独立五类注入逐条 rc=1（待开始误入流水表为**硬 FAIL**、未被覆盖逻辑吞掉），另测 7 类 fail-closed（缺标题/两表皆空/表头改坏/跨表重复/超长等）均 rc=1；两表 101 行与 HEAD 逐行配对 **0 差异**。
- 范围外旧口径 3 处（`AGENTS.md`、`Makefile` 注释、`.opencode/commands/complete.md`）由本任务收尾一并改（仅文字，不改判据）。
- 任务书「现有 6 条待开始」与现场 8 条的偏差已在完成区披露；迁移按现场全量执行。
