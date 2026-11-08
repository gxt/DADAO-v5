# INFRA-141t: 里程碑台账改三分表（待开始 / 进行中 / 已验证，去状态列）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-139t`（双表门控，已合入）
**状态**：已验证

## 用户授权（原话）

> 「milestones：把待开始的列表放在任务流水前面，或者分为三类，第一类待开始，第二类进行中，第三类已验证；前两类，写一个预估时间；第三类，写完成时间；状态这一栏可以删除」

即：改**三分表**、待开始置前、**前两类写预估时间**、第三类写完成时间、**删除状态列**。

## 目标版式

```markdown
## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |

## 进行中（已提交待验收 / 待返工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
```

- **分类 = 任务书 `**状态**`**：`待开始`→表1；`待验收`/`待返工`→表2；`已验证`→表3。
- **无状态列**：类别即状态；表内不再写状态。
- **前两表**：`预估时间` 为人工估时，格式 `N h` / `N–M h` / `N 天` / `N–M 天`（也允许 `min`）；**不写完成时间、不写 `（登记）`**。
- **第三表**：`完成时间` 为 `YYYY-MM-DD HH:MM`（沿用现值），**不带 `（登记）`**。
- 三表顺序：待开始 → 进行中 → 已验证；各表行序：
  - 待开始 / 进行中：人工计划顺序（门控不判）；
  - 已验证：按完成时间倒序（同时间按编号升序）。

## 迁移时填写的预估时间（architect 给定，按现状）

| 任务 | 预估 |
|---|---|
| `GEM5-028t` | 1–2 h |
| `QEMU-085t` | 2–3 h |
| `INFRA-140t` | 1 h |
| `INFRA-141t` | 2 h |
| `INTEG-060t` | 3–5 h |
| `TESTCASES-103t` | 3–4 h |
| `TESTCASES-104t` | 5–8 h |
| `INTEG-059t` | 10–16 h |

其余任务按其现状归表；`已验证` 行**只搬不改**（编号、完成时间、一句改动逐字保留）。

## 门控改造（`check_milestones_fresh.py`）

- **A1 分类一致**：表 ↔ 任务书状态映射如上；不一致 ⇒ FAIL。
- **A2 覆盖**：三表并集覆盖全部任务书 + `INTEG-*m` 所列号 + 正文号（归档号豁免，悬空号 FAIL）。
- **A3 长度**：三表「一句改动」均 ≤120 字符。
- **A4 次序**：仅第三表按完成时间倒序；前两表不判。
- **A5 格式**：
  - 三表各 3 列（`编号 | 时间 | 一句改动`）；
  - 表1/表2 时间列匹配预估格式（`\d+(\.\d+)?(–\d+(\.\d+)?)?\s*(h|天|min)`）；
  - 表3 时间列匹配 `YYYY-MM-DD HH:MM`，不得含 `（登记）`；
  - **任何表都不得出现状态列/状态值**（出现 `待开始`/`待验收`/`待返工`/`已验证` 作为状态列即 FAIL）；
  - 编号不得跨表重复。
- **fail-closed**：三个标题/表头缺失、三表皆空 ⇒ FAIL。
- `--self-test` 注入按新规则重写（至少：行放错表、预估格式非法、完成时间带（登记）、跨表重复、第三表乱序）。

## 文档同步

- `AGENTS.md`（两处「对应表行」措辞）、`Makefile` 门控注释、`.opencode/commands/complete.md`（列名与表名）、`docs/Process-04`（归档取行）、`docs/Process-07`（门控描述行）。
- 上一任务 `INFRA-139t` 的描述在 `Process-04/07` 中如与三分表冲突，按本任务更新（不回改历史任务书）。

## 范围 / 非范围

**在范围内**：`tools/infra/check_milestones_fresh.py`、`.tao/knowledge/milestones.md`、上述 5 处文档、本任务书、`milestones.md` 自身行。

**不在范围**：任务书状态机（仍用四态）、`/complete` 流程逻辑、历史归档内容。

## 验收标准

1. `make check-milestones-fresh` rc=0；三表结构与映射正确；`已验证` 行逐字未改（编号/完成时间/一句改动）。
2. 五类注入逐条真实 rc：① `待开始` 行放进「进行中」⇒ FAIL；② 预估格式非法（如 `soon`）⇒ FAIL；③ 完成时间带 `（登记）` ⇒ FAIL；④ 同号跨表 ⇒ FAIL；⑤ 第三表乱序 ⇒ FAIL；均 `cp`+md5 还原回绿。
3. `--self-test` rc=0。
4. `make check`（L1）rc=0（并发任务的 `check-patch-tree` 红需核实归属）。
5. 文档四处与新格式一致（人工核对清单）。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- 这是**门控语义变更**（去状态列、三表分类、预估时间格式），已获用户授权；不得顺手放宽其它断言。
- 预估时间是人工估值，**门控只校验格式与存在性**，不校验准确性。

## 完成区

**测试结果**：通过 19/19（门控基线、`--self-test` 基线+11 类注入、五类现场注入各自 FAIL/还原/回绿、`make check-milestones-fresh`、L1 归因）；L1 `make -k _locked-check` 唯一红 = `check-patch-tree`（并发 GEM5-028t 的共享组件源，非本任务文件）。
**修改文件**：`tools/infra/check_milestones_fresh.py`、`.tao/knowledge/milestones.md`、`AGENTS.md`、`Makefile`、`.opencode/commands/complete.md`、`docs/Process-04-里程碑归档规范.md`、`docs/Process-07-门控分层规范.md`、本任务书。
**验收结果**：三表现场统计 = 待开始 7 / 进行中 1 / 已验证 95；与旧台账逐字比对：已验证 95 行（编号/完成时间/一句改动）全等、待开始 7 行一句改动全等；预估时间按指定清单；门控 rc=0；`--self-test` rc=0；五类注入 rc=1 各自命中预期断言，`cp`+md5 还原后 rc=0。
**新发现/坑**：① 各 worktree 的 `.dadao`/`.work` 均软链主工作区 ⇒ gate 锁与组件源全局共享，`make check` 会被并发 build 长时间阻塞；等价 recipe 体 `_locked-check` 可直跑。② 运行期日志文件名只允许 `<TASK>-<purpose>.(log|json|txt)`，`*_EXIT`/`.NOTE` 会被 `check-run-artifacts` 判红（本次踩中，已改名）。③ 共享组件源 `se_workload.cc`/`mmap.c` 的 patch 集与 HEAD 不一致导致 `check-patch-tree` 红。
**遗留问题**：`make check` 无法在本任务内取得 rc=0：`check-patch-tree` 红归属并发 GEM5-028t（共享组件源 patch 集未完成），其余 L1 子门控全绿（`make -k` 现场统计，无第二红）。

## 审阅记录

### 第 1 轮 engineer 自审

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | 未校验三表小节次序（目标版式要求 待开始→进行中→已验证） | ✅已修 | 加 A5 次序断言 + self-test ⑦ | 注入⑦ rc=1 命中「三表须按」 |
| 2 | `_swap_done_first` 用 `is not` 比字符串对象，脆弱 | ✅已修 | 改 `pop(index)` | 注入⑦ 稳定复现 |
| 3 | self-test 未覆盖 A2 覆盖 / fail-closed / A3 超长 / `.work` 路径 | ✅已修 | 加注入⑧⑨⑩⑪ | 四项 rc=1 各自命中 |
| 4 | 生成中间文件落在仓库根（`milestones.new.md`） | ✅已修 | 删除并复核 | `git status -uall` 仅范围内 8 文件 |
| 5 | `complete.md` 首版改写丢了台账位置指针 | ✅已修 | 补回 `$TAO_ROOT/knowledge/milestones.md` | 人工核对 diff |
| 6 | 注入④同时触发 A1 与跨表重复 | ❌不修 | 双报错不掩盖主断言（状态类别互斥，无法只触发其一） | `gate-inj4.log` 两条 VIOLATION |

判据：A1–A5 各有可达 FAIL（①/⑧/⑩/⑤/②③④⑥⑦⑨⑪）；三表分类 == 任务书状态；已验证行逐字未改。判决：待验收。

### 第 1 轮 reviewer 验收

**判决：Accepted**（以下全部为 reviewer 独立重跑，未采信完成区转述；未 commit / 未 push）

**重跑记录**（workdir 内相对路径；退出码均取命令自身）
- `python3 tools/infra/check_milestones_fresh.py` ⇒ **rc=0**：待开始 7 / 进行中 1 / 已验证 95、活册 102 / 含归档 725、A1+A2+A4 全过。
- `... --self-test` ⇒ **rc=0**：干净基线 + 十一类注入逐条 `rc=1 marker=True`。
- **五类现场注入**（`cp` 备份 + md5 → 改 → 跑 → `cp` 还原 → md5 相等 → 回绿；全程未用 git 还原）：① 待开始行进进行中 **rc=1** `A1 … QEMU-085t MISMATCH`；② 预估 `soon` **rc=1** `预估时间 … 不合格式`；③ 完成时间带 `（登记）` **rc=1** `不得带`；④ 同号跨表 **rc=1** 且 运行期注入日志恰 2 条 VIOLATION（跨表重复 + MISMATCH）；⑤ 第三表末两行对调 **rc=1** `A4 … 逆序`。每次还原 md5 == `17605c987c1f8068168c6bc1550e2420`、还原后 rc=0。
- 重跑运行期证据脚本（未归档）⇒ **rc=0，结果 PASS（19 PASS / 0 FAIL）**，收尾台账 md5 与开工前逐字节相同。
- L1：先按验收优先试 `timeout 45 make -k check` ⇒ **被共享 gate 锁阻塞**（`gate-lock: WAIT … held by pid=2160521 target=check-modules … waits up to 3600s`，42.5s 才 ACQUIRED；同期 5 个并发 gate 用户）⇒ 改跑同 recipe 体 `make -k _locked-check` ⇒ **rc=2，`grep '\*\*\*'` 唯一红 = `check-patch-tree`**（4 问题），其余 L1 全绿（含 `check-milestones-fresh: PASS`、`check-run-artifacts: PASS`、`check-knowledge-refs: PASS 悬空 0`）。
- **归属核实**：`python3 tools/infra/check_patch_tree.py` 在**主工作树**（master、`git status` 干净、零本任务改动）复现**同样 4 条** ⇒ 与本任务无关；共享 `.work/source/qemu` 本地 commit `2c6ab04` committer 时间 **2026-11-08 11:52**、`/tmp/opencode/QEMU-085t` 工作树 `M components/qemu/patches/linux-user/mmap.c.patch` ⇒ 红归并发 **QEMU-085t（mmap.c）/ GEM5-028t（se_workload.cc）**；本任务 8 改动文件命中 `components/` **0**。

**约束核验**
- ① 无行丢失：`git show HEAD:` 旧流水 95 行 ↔ 新「已验证」95 行，按（编号|完成时间|一句改动）三元组逐行 diff **0 差异、顺序全同**；旧「待开始」8 行 = 新待开始 7 + 进行中 1，一句改动全等；行数 7/1/95 与声明一致。
- ② 分类：现场读 103 册 `**状态**`（已验证 95 / 待开始 7 / 待验收 1）↔ 103 行**一一对应、唯一归属、零不符**（`待验收` 落「进行中」✓）。
- ③ 预估格式：前两表 8 行全合 `N h`/`N–M h`，与任务书指定清单**逐字相等**；前两表无完成时间、全文 `（登记）` 计数 = **0**。
- ④ 文档：AGENTS 两处、Makefile help+注释（`make help` 实跑命中）、`complete.md` E 节、`Process-04` §2/§7、`Process-07` §1.1 均已同步；grep「任务流水（已开工）」在活文档**零命中**（仅 INFRA-139t 历史任务书与归档 README §2，后者仍带状态列、口径正确）。
- ⑤ 完成区正文 5 行（含标题共 7）≤30；无绝对/临时/家目录路径；`check-knowledge-refs` 扫 `.tao/tasks/**` 悬空 0。
- ⑥ 改动范围 = 完成区声明 8 文件；验收前后 `git status -uall` 快照逐行一致、`md5sum -c` **8/8 OK**。

**findings（文档级，不阻断）**：F1 `complete.md` 小节标题仍为旧表名「**E. 任务流水（`milestones.md`）**」（正文已改三分表）；F2 仓库根残留 `audit1.log`/`audit2.log`（被 `*.log` 忽略、`git status` 不显，建议收尾删除）；F3 `MEMORY.md:10` 仍以「任务流水」作 milestones 内容标签（非本任务 5 处范围）。

**独立回答**：① **无行丢失、已验证 95 行零改动**；② **分类与预估格式全对**；③ 文档旧口径残留**仅 F1/F3 两处措辞级**（活文档无结构性旧口径）。

#### 收尾（architect，2026-11-08 12:46）

- 判决 Accepted：reviewer 独立五类注入逐条 rc=1 + `cp`+md5 还原回绿；`--self-test` 11 类注入；旧流水 95 行 ↔ 新「已验证」95 行按（编号|完成时间|一句改动）**0 差异**；103 册 ↔ 103 行一一映射。
- L1 因共享锁被并发 `check-modules` 占用，改用 `_locked-check` 等价体；唯一红 `check-patch-tree` 在**干净 master 复现同 4 条**，归并发 `QEMU-085t`/`GEM5-028t`。
- F1 已修：`complete.md` 小节标题「任务流水」→「任务台账」。
- F2 已清：worktree 根的 `audit1.log`/`audit2.log` 删除（运行期残留，未入库）。
- F3 已修：`MEMORY.md` 的 milestones 标签改为「任务台账（待开始·进行中·已验证）」。
- 三分表结构落定：`待开始（预估时间）` / `进行中（预估时间）` / `已验证（完成时间）`，无状态列。
