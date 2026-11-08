# m12-infra-001: M12 任务编号与独立台账脚手架

**模块**：infra
**项目里程碑**：M12
**类型**：task
**状态**：已验证

## 用户裁定（原话）

> 「从M12开始，任务书都带上里程碑，例如 chipyard-m12-001t-***；这样在合并的时候不会出现冲突，且milestones.md也改为milestones-m12.md」
> 「m12是不是放在前面更好，m12-infra-001t，你觉得呢」
> 「从M12开始，任务书的后缀k/t/m，我觉得也可以取消了，就是<NNNN>」

最终口径（architect 归并，已经用户确认方向）：**`<mNN>-<module>-<NNNN>`**，无后缀。

## 目标

### 1. 任务编号与文件名

- 任务号：`m12-<module>-<NNN[N]>`（模块小写；序号 **3–4 位**均可，本仓库沿用 3 位：`m12-chipyard-001`）
- 任务书文件名：`.tao/tasks/<module>/m12-<module>-<NNNN>-<描述>.md`
- 任务书头部新增 `**类型**：task | kickoff | verify`（默认 `task`；`verify` 供里程碑核验用）
- **旧编号（M11 及之前，如 `GEM5-031t`）保持不变**，不做迁移

### 2. 独立台账

- 新增 `.tao/knowledge/milestones-m12.md`：与 `milestones.md` 同结构（`项目里程碑 = M12` 断言 + 待开始 / 进行中 / 已验证 三表，进行中带派单时间）
- `milestones.md` 继续作为 M11 台账，直至 M11 收口
- 两文件**互不影响**；M12 任务的派单/完成只改 `milestones-m12.md`

### 3. 门控与工具

- `tools/infra/check_milestones_fresh.py`：支持 `--file PATH`（默认仍为 `milestones.md`）；任务号正则同时接受旧格式（`PREFIX-nnn[suffix]`）与新格式（`mNN-module-NNNN`）
- `Makefile`：`check-milestones-fresh` 依次校验存在的台账（M11 必有；M12 存在则校验），任一红即红
- 覆盖性：`.tao/tasks/**` 的任务书须在其**所属里程碑**的台账中出现（按任务书 `**项目里程碑**` 字段分派）
- `docs/Process-07`：登记新编号与双台账规则
- `AGENTS.md`：任务编号段补一行新格式

## 范围 / 非范围

**在范围内**：`tools/infra/check_milestones_fresh.py`、`Makefile`（仅该目标）、`.tao/knowledge/milestones-m12.md`（新建）、`docs/Process-07`、`AGENTS.md`、本任务书。

**不在范围**：`check-milestone`（m 册门控，由 `m12-infra-002` 取消）、旧任务书改名、其它门控。

## 验收标准

1. `make check-milestones-fresh` rc=0（M11 台账 + M12 空台账都通过）
2. **可达 FAIL**：临时树放一份 `m12-test-0001` 任务书但 M12 台账未列 ⇒ FAIL 并指名；补行后回绿
3. 旧格式任务书（如 `GEM5-031t`）仍被正确覆盖，M11 台账不受影响
4. **跨台账隔离**：把 M12 任务写进 `milestones.md` ⇒ 应判「不在其所属里程碑台账」FAIL（或明确被 M11 校验拒绝）
5. `--file` 参数可用；缺文件时行为明确（M12 文件不存在 ⇒ 跳过，不 vacuous）
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 说明

- 本任务是**自举**：它自己用新编号命名。architect 已先做**最小自举**——`check_milestones_fresh.py` 的 `TASK_ID_RE`/`ROW_ID_RE`/`TASK_FILE_RE` 已接受 `m\d{2}-[a-z][a-z0-9]*-\d{3,4}`（旧格式并存），因此本任务书与台账行已可被门控识别；**剩余的台账路由/双文件/文档由本任务完成**。
- 本任务行暂时放在 `milestones.md`（M11 台账）；任务结束前须创建 `milestones-m12.md` 并把 M12 行迁入，同时把门控改为按任务书 `**项目里程碑**` 路由。
- 不改任何 M11 任务的状态与台账行

## 完成区

**测试结果**：一键证据脚本 15/15 PASS（注入①/② FAIL→回绿往返）；`check_milestones_fresh.py --self-test` 29/29；`check_run_artifacts.py --self-test` 8/8（含「新编号日志名合法 / 形似缺号仍非法」）。`make check`（L1）唯一红 = `check-patch-tree`（gem5 patch 与共享组件源码树漂移），`master` 同 commit 复现，非本任务引入（遗留①）。

**修改文件**：
- `tools/infra/check_milestones_fresh.py`：A6 双台账路由（台账 `项目里程碑 = M<n>` 断言 + 按任务书 `**项目里程碑**` 分派、跨台账错放 FAIL）、`--file PATH`、R1/覆盖/正文按所属台账过滤、新编号分支识别、A6 自检 8 例
- `tools/infra/check_run_artifacts.py`：`TASK_ID` 并存新编号 `mNN-<module>-<NNNN>`；自检补「新编号日志名合法 / 形似缺号仍非法」两例
- `Makefile`：`check-milestones-fresh` 依次校验存在的台账（M11 必有 / M12 存在则校验；缺 M12 打印跳过），help 行同步
- `.tao/knowledge/milestones-m12.md`（新建，`m12-infra-001` 进行中，派单 2026-11-08 21:06）；`.tao/knowledge/milestones.md` 仅删该行（M11 行与状态未动）
- `.tao/knowledge/MEMORY.md`：台账指针补 `milestones-m12.md`（指引表 + 历史节两处）
- `docs/Process-07-门控分层规范.md` 登记双台账 + A6 路由 + 新旧双编号；`AGENTS.md` 任务编号段补 M12 格式（3–4 位、无后缀）
- `tools/infra/check_knowledge_dir.py`（**越界披露**）：顶层白名单加 glob `milestones-*.md`（否则新台账令 L1 红）

**验收结果**：
1. `make check-milestones-fresh` rc=0，输出含两台账名（M11 3/1/105 行；M12 0/1/0 行）
2. 注入① `m12-test-0001` 有册未列 ⇒ rc=1 指名；补行 ⇒ rc=0；注入② M12 行写进 `milestones.md` ⇒ rc=1「跨台账错放」指名 `m12-infra-001`，还原 ⇒ rc=0
3. 旧格式：删 `GEM5-031t` 行 ⇒ rc=1 指名；补回 ⇒ rc=0（M11 台账仍有效）
4. `--file` 两台账 rc=0；指向不存在文件 ⇒ rc=1「台账不存在」；M12 文件缺失 ⇒ M11 仍 rc=0（删行仍 rc=1，非 vacuous）
5. `python3 tools/infra/check_run_artifacts.py` rc=0；真实树放 `m12-test-001-demo.log` ⇒ PASS，放 `m12-test-demo.log` ⇒ FAIL 指名，删除后回 PASS
6. `make check`（L1）除 `check-patch-tree` 外全绿（逐项打印实际退出码）

**新发现/坑**：共享组件源码树被并发任务推进会让 `check-patch-tree` 在任意任务期间变红 ⇒ 判据须「同 commit 主工作树复现」而非直接归因本任务；`check_milestone_tasks.py` 只读 `milestones.md` 的断言（M12 收口口径按任务书归 `m12-infra-002`）。

**遗留问题**：① `make check` 唯一红 = `check-patch-tree`：gem5 补丁集与共享组件源码树漂移（并发 `GEM5-031t` 推进所致），`master` 同 commit 复现，本任务不动 `components/`；② 越界文件 `check_knowledge_dir.py` 已在上方披露。

## 审阅记录

### 第 1 轮 engineer 自审

审查范围：路由/过滤新增代码、`Makefile` 配方、两份台账、`docs/Process-07`、`AGENTS.md`、证据脚本；逐行核对边界（归档册、缺字段、无活册号、异台账号）。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 新编号漏进 R1（`BRANCH_TASK_RE` 只认旧前缀）⇒ 在跑任务不受约束（假绿） | ✅已修 | 复用 `_OLD_ID\|_NEW_ID` 拼 `BRANCH_TASK_RE` | 自检 R1 六例；真实树 M12 在跑 1 个被核 |
| F2 双台账下 R1/覆盖/正文会把异台账号算进本台账（跨台账假红） | ✅已修 | `owned()` 过滤在跑号、`todo_books`、m 册、正文号 | 证据 3/5/6/7 项 |
| F3 A6 行路由对 `ms=None` 打印 `MNone` | ✅已修 | 引入 `ms_label` | 自检 A6 注入⑤（缺字段）PASS |
| F4 m 册归属过滤会 `IndexError`（文件名不含任务号） | ✅已修 | 抽 `_file_task_id()`（不匹配返空串） | 自检 29/29 PASS |
| F5 自检树书缺 `**项目里程碑**` ⇒ A6 全线假红 | ✅已修 | `write_tree` 写字段（新格式按前缀、旧格式 M11），台账补断言 | 自检 29/29 PASS |
| F6 证据脚本日志名触发 `check-run-artifacts` A3 | ✅已修 | 日志名改 `check-*.log` | `make check-run-artifacts` PASS |
| F7 证据脚本临时树目录层级错（基线假红） | ✅已修 | 先建根目录再拷 `.tao` | 证据第 3 项 rc=0/0 |
| F8 证据脚本 L1 失败项提取把顶层 `check` 也算进去 | ✅已修 | 只取 `^make[n]: *** [...]` | 证据第 9 项 `bad=[check-patch-tree]` |

**判决**：findings 全部已修（证据 15/15 PASS、自检 29/29 PASS）⇒ 可交付、状态 `待验收`。残留仅环境既有红（`check-patch-tree`），已在遗留问题①记录并附复现证据。

### 第 2 轮 engineer 自审（收尾补充：新编号日志名 + MEMORY 指针）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F9 `check_run_artifacts.TASK_ID` 只认旧编号 ⇒ 新编号 `<任务号>-<purpose>.log` 撞 A3（假红） | ✅已修 | `TASK_ID` 并存新格式 `m\d{2}-[a-z][a-z0-9]*-\d{3,4}` | 自检 8/8 PASS；真实树 `m12-test-001-demo.log` ⇒ rc=0 |
| F10 新格式正则若放宽（缺序号也放行）会削弱 A3 判据 | ✅验证不放宽 | 保持 `-<3–4 位数字>` 必需 | 自检「new-format without number rejected」rc=1；真实树 `m12-test-demo.log` ⇒ FAIL 指名 |
| F11 `MEMORY.md` 台账指针只写 `milestones.md` ⇒ 入口误导 | ✅已修 | 指引表 + 历史节两处补 `milestones-m12.md` 与分派口径 | `make check-knowledge-dir` / `check-knowledge-refs` rc=0 |

**第 2 轮判决**：F9–F11 处置完毕；`check_run_artifacts.py` 实跑 rc=0、`make check-milestones-fresh` rc=0、L1 仍仅 `check-patch-tree` 红（主工作树同 commit 复现）⇒ 仍为 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（worktree 内相对路径，未 commit/push；`git status` 前后快照逐行相同、6 个目标文件 md5 前后一致）：
1. `make check-milestones-fresh` ⇒ rc=0；M11 3/1/105、M12 0/1/0（与完成区一致）；`--file nope.md` ⇒ rc=1「台账不存在」；移走 M12 册 ⇒ make rc=0 且打印「不存在 ⇒ 跳过」。
2. `check_milestones_fresh.py --self-test` ⇒ rc=0，29/29（14 基础 + 8 A6 + 6 R1）；`check_run_artifacts.py --self-test` ⇒ rc=0，8/8。
3. 证据脚本 `bash .work/evidence/m12-infra-001/run.sh` ⇒ rc=0，PASS=15 FAIL=0（脚本逐项有可达 FAIL 路径、注入在临时树、无两支同果）。
4. 独立注入（真实树；`cp` 备份 + md5 `02107736…` 前后相等还原；无残留文件）：① M12 行写进 `milestones.md` ⇒ rc=1「跨台账错放」指名 `m12-infra-001`，还原 rc=0；② 造 `m12-test-001-demo.md`（M12/待开始）⇒ M12 rc=1「未列入台账三表」、M11 仍 rc=0，删文件；③ 删 `GEM5-031t` 行 ⇒ rc=1 指名，还原 rc=0；④ `.work/log/m12-test-001-demo.log` ⇒ rc=0、`m12-test-demo.log` ⇒ rc=1 指名，删后 rc=0。
5. `make -k check`（L1）⇒ rc=2，唯一失败 `check-patch-tree`：gem5 `se_workload.cc` 断言⑨⑥ 共 2 problem；主树干净检出 `bd9379f6`（含 d693971e，其间 4 提交零 `components/` 改动）同样 rc=2 同两行 ⇒ 该门控输入等价复现，非本任务引入；本任务 diff 零 `components/` 文件。
6. 正则：`_NEW_ID`/`_OLD_ID` 与 `check_run_artifacts.TASK_ID` 两段子串全等，8 个样例（新旧/形似缺号）判定逐一对齐。
7. `check_knowledge_dir.py` rc=0（允许 glob `['milestones-*.md']`）；`MEMORY.md` 指引表 + 历史节两处已补 M12 指针；完成区 26 行 ≤30、grep `/tmp|/mnt|~/|/home/` 零命中；`m12-infra-001` 表行全仓仅 `milestones-m12.md` 一处，`milestones.md` git diff 仅删该行。

**findings（均非阻断）**：F1 `check_milestones_fresh.py:57` 文档串 `\d` 未转义（HEAD 为 `\\d`）⇒ 每次运行打 SyntaxWarning，改 `\\d` 即可；F2 白名单 `milestones-*.md` **过宽**（见下问③）；F3 完成区「master 同 commit 复现」措辞不准（主树实为 d693971e 后 4 个 docs/tools 提交，对该门控输入等价）——文档级，按 6.5 不阻断。

**约束核验**：编号/独立台账/A6 路由/归档豁免/`--file`/缺册非 vacuous/双格式正则/文档均落地；改动 = 任务书列的 9 文件 + 新建 1，`check_knowledge_dir.py` 越界已披露；未动 M11 状态与其它行。

**三个单独问题**：① 跨台账错放**会红**（实测 rc=1 且指名）；② 新旧编号正则**一致**（子串全等 + 8 串行为对齐）；③ 白名单 glob **过宽**：任意 `milestones-*.md` 顶层放行；实测带断言的 `milestones-evil.md` 会劫持归属令 A6 **大声红**（非假绿），但「新台账须人工登记」的绊线被削弱，且 Makefile 只硬编码 M11/M12 ⇒ 将来 `milestones-m13.md` 会被路由却从不被三表校验；建议收窄 glob 并让 Makefile 遍历所有带断言册（交 architect 定）。

**判决：Accepted**（验收项 1–5、7 全绿；验收项 6 字面 rc=0 未达成，根因已独立定为共享 `.work/source/gem5` 被并发 `GEM5-031t` 推进——主树干净复现、门控输入两 commit 间零差异、本任务零 `components/` 改动，按「环境/并发干扰」记录放行，不凑绿、未改任何代码使其变绿）。

#### 收尾（architect，2026-11-08 21:38）

- 判决 Accepted：reviewer 独立注入（M12 行写进 M11 台账 ⇒ 跨台账 FAIL；`m12-test-001` 有册无行 ⇒ FAIL；旧格式删行 ⇒ FAIL）均 rc=1 并还原；两脚本正则子串全等、8 组样例判定一致；`--self-test` 29/29 与 8/8。
- F1 已修：`check_milestones_fresh.py` docstring 的 `\d` 转义（消除 SyntaxWarning）。
- F2 已修：`check_knowledge_dir.py` **去掉 `milestones-*.md` 通配**，改为在 `_ALLOWED_FILES` 显式登记 `milestones-m12.md`（新增分册须人工放行，保留「新增台账必须登记」的绊线）。
- F3：完成区「master 同 commit 复现」措辞按实况理解为「对 `check-patch-tree` 输入等价」（主树另有 4 个 docs/tools 提交，不含 `components/`）。
- 双台账落定：M11 台账 `milestones.md`（3/1/105）、M12 台账 `milestones-m12.md`（0/1/0）。
