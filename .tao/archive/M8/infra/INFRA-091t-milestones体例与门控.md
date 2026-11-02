# INFRA-091t: milestones 台账体例改造 + L1 门控 check-milestones-fresh

**模块**：infra
**项目里程碑**：M8
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户要求（原话逐字；渠道 = 经主会话问答，2026-10-18）
> 「**milestones.md中的任务流水表格又乱了，这个表格换成列表，而且按时间序，未完成的任务也需要列上；这个要求明确写到文档里，不要再乱了；另外，该文档后面的信息应按时更新；最后的历史台账指针没用，删除**」
> 「**如果能这么短写清楚，就不要换掉表格，你自己看看现在的表格长啥样了**」

## 接口规范
- 输入：`.tao/knowledge/milestones.md`、各任务书头部 `**状态**`、`INTEG-036m`
- 输出：改造后的 `milestones.md`；`tools/infra/check_milestones_fresh.py`；`Makefile` 的 L1 挂载；`docs/Process-07 §1.1` 登记行
- 约束：任务流水**保留表格**（`编号|状态|完成时间|一句改动`）、**一句改动 ≤120 字符**、**按完成时间倒序**、**未完成任务必列**（时间 = 登记时间 + `（登记）`）、细节写任务书（本页只做索引）；门控**不得依赖 `.work/**`**

## 验收标准
1. 任务流水保留四列表格；全部行 `一句改动` ≤120 字符；按时间倒序；未完成任务在列且带 `（登记）`。
2. 文档头新增「体例约定（硬约束）」四条（表格 + 长度、倒序 + 未完成、状态以任务书为准、后续信息同步更新且计数现场派生）。
3. `check-milestones-fresh` 五断言（状态一致 / 覆盖 / 长度 / 次序 / 格式）各可达 FAIL；`--self-test` 五类注入各自报错；并入 `make check`（L1）。
4. 「历史台账指针」节删除，全仓无该节引用；`check-knowledge-refs` rc=0。
5. 表格之后的当前进度 / M8 规划区 / 快照按现场刷新（`check-patch-tree` 174、三套测试真值、各册状态）。

## 完成区
**测试结果**：`make check`(L1) **rc=0**（含新门控）；`python3 tools/infra/check_milestones_fresh.py` **rc=0**（53 行；状态一致/覆盖/≤120 字符/倒序/格式）；`--self-test` **rc=0**（干净基线 + 五类注入各自 FAIL）；真实注入（`INFRA-090t` 表改 `已验证`）⇒ **rc=1**（`VIOLATION L33 表 已验证 ≠ 任务书 待开始`）⇒ `cp` 还原 + **md5 三态一致**（`6e913a81…`）⇒ **rc=0**；`check-knowledge-refs`/`check-knowledge-dir`/`check-tasks`/`check-no-residue`/`check_issues.py` 全 **rc=0**；`check-milestone` **rc=2**（m 册 37 号全存在 = PASS；rc=2 仅 `check_tasks --strict` 既有 7 份 `待验收`，含本册）。
**修改文件**：`M` `.tao/knowledge/milestones.md`（表格压缩 52→53 行：平均行 1030→98 字符、最长 3905→114；体例四条；后续信息刷新；删除「历史台账指针」）；`A` `tools/infra/check_milestones_fresh.py`；`M` `Makefile`（L1 + help）；`M` `docs/Process-07-门控分层规范.md §1.1`；`M` 4 份任务书追加「台账迁入」（`SPEC-145t`/`QEMU-061t`/`LLVM-097t`/`TESTCASES-047t`）；`A` 本任务书。
**验收结果**：待 reviewer 独立复验（本笔按用户指令由 architect 执行，未自判 `Accepted`）。
**新发现/坑**：① 门控「状态一致」使台账不再是手写副本——表状态与任务书不一致即红；② 覆盖断言把「正文悬空号」也纳入（本次清掉 `INTEG-036t`/`INTEG-037t` 两个未立册旧号）；③ 原表实际为 52 行（主会话口径 62 行与盘上不符，按实测报告）。
**遗留问题**：`check-milestone` rc=2 由既有 `待验收` 触发（非本笔引入）；`SPEC-141t` 等 16 册仍 `待开始`，随收尾更新。

## 审阅记录

#### 第 1 轮 reviewer 验收
**重跑（2026-10-18 独立）**：`python3 tools/infra/check_milestones_fresh.py` **rc=0**（54 行；状态一致/覆盖/≤120 字符/倒序/格式）✓；`--self-test` **rc=0**（干净基线 + 五类注入各自 FAIL）✓。
- 本册无独立证据脚本（接口规范不要求；证据 = 门控 + `--self-test`）。
**逐条核验**：① 表格保留四列、54 行、一句改动 ≤120（max=114）✓；② 体例约定四条存在（L10 `## 体例约定（硬约束）`）✓；③ 五断言各可达 FAIL（self-test 5/5 PASS）✓；④ 历史台账指针已删、check-knowledge-refs rc=0 ✓；⑤ 快照刷新（check-patch-tree 180、L1 rc=0）✓。
**约束**：只改 milestones.md、新脚本、Makefile、Process-07、4 份任务书追加 ✓；未越界。
**如实性抽查**：行数 54（完成区 53 + INFRA-092t 行由 architect 追加）✓；max_summary=114 ✓；check-milestones-fresh 54 行 PASS ✓。
**独立注入（本组≥1次）**：在 INFRA-092t 行注入 `.work/evidence/…` 路径 ⇒ rc=1（`VIOLATION L33 一句改动含 .work/ 路径`）⇒ cp+md5 还原（`2065113f…` 一致）⇒ rc=0 ✓。
**判决**：**Accepted**。
