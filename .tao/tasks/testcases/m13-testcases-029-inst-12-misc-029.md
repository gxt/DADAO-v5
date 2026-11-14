# m13-testcases-029: `12-misc` —— `swym`/`ctpop`/`ctlz`/`cttz`

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **4 个 id**（`12-misc` 其余（swym/ctpop/ctlz/cttz））

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
ctlz_orri_rd ctpop_orri_rd cttz_orri_rd swym_oiii_imm
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/12-misc/` 下本任务 id 的 `.S` 齐全（== 4）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` rc=0；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
5. YAML 迁移：把相关 YAML 里属于本任务 id 的 case 并入；**该 YAML 文件全部 id 迁完**才 `git rm` 并更新 `MIGRATION.md`
6. **可达 FAIL 注入**：改错一个 boundary 期望 ⇒ 对应点号非零退出（三平台同值）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修前必须保留）。
- **不要**改 `contracts/`/`spec/`/`Makefile` 门控集合。
- `.work` 软链（`ISS-389`）；改动必须落在任务 worktree 内（`AGENTS.md` 硬约束 14）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

审查范围：4 个 `.S`（头注/用例段/期望/故障段/点号逐文件逐行核，另由独立复算全量重放）、
证据脚本四件（`oracle_check.py`/`run.sh`/`verify_bytes.py`/`check_fragments.py`）、两个片段文件；
`git status -uall` 仅本任务 6 个新增 + 本任务书。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 手算 `ctpop(0x0123456789ABCDEF)` = 33（`0x89` 记成 4 个 1，实为 3） | ✅已修 | ctpop 点 5 期望 `0x21→0x20` | 独立复算（位循环）报 `0x20`；修后 67/67 链点 0 不符，三平台一致 |
| F2 独立复算初版在第二条 `aip.si` 处误报「未配对」（假红，非用例错） | ✅已修 | oracle 改为「配对即清标记」 | 复算 PASS；`swym` 13 点全绿 |
| F3 证据脚本故障例计数用空格匹配 tab ⇒ 计数恒 0、镜像总数断言假红 | ✅已修 | 改 `TEST_FAULT_ALU_ORRI[[:space:]]\+[0-9]` | 现场 3；`7 == 4 + 3` 通过 |
| F4 掩码类用例**可判性**不足：初版越界位取值恰不改变结果（忽略 `hd` 的实现同值 ⇒ 恒真） | ✅已修 | ctlz 点 10 改 bit15、cttz 点 4 改 bit40、点 9 改 bit12 | 三平台仍绿；按全 64 位算会得 16/40/12 ⇒ 三处断言对「忽略 hd」实现必红（推导） |
| F5 头注的用例分类计数与实测不符 | ✅已修 | 按现场重算：`ct*` 2/6/8/1/1、`swym` 2/5/5/0/1 | 每文件点数 18/18/18/13 与分类合计逐项相等 |
| F6 `check-milestones-fresh` 红（5 条派单行） | ✅已处置（非本任务引入） | 不改台账；用 master 版台账 overlay 现场验证 rc=0；脚本改为断言违规集恰为该 5 个任务号 | overlay 后 PASS；未 overlay 时违规集 == master 派单提交所修的 5 行 |
| F7 共享构建区被并发会话重建（gem5 二进制一度仅 41 MB 且不可执行、qemu md5 变动） | ✅已处置 | 不向节点同步半成品；用节点既有产物 + 记录其 md5 + 跑批前后自证不变 | 三件产物 md5 已记录；跑批前后 md5 相同 |
| F8 `make check-inst` 一次被 SIGTERM 打断（rc=143） | ✅已处置（有据重试 1 次，记录次数） | gates 阶段 rc=143 ⇒ 重试 1/1；仍 143 则如实报红 | 重跑 rc=2、红集恰 `divrem.yaml[23]`（与 028 现场一致） |

未修 finding：无。任务状态置 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-14）

**重跑（reviewer 现场执行，均在本 worktree、相对路径）**
- `<运行期证据目录>/run.sh all` ⇒ **`RERUN_ALL_EXIT=1`**（2 条 FAIL，见阻断项）；`run.sh points` ⇒ rc=1（同一 FAIL，最小复现）。
- run3 段（我方重跑）：`run_asm_suite: 7/7 镜像通过（4 id；链例 4，故障例 3）`；3 例故障 `期望 0xF8 / rc {'chipyard':248,'qemu':248,'gem5':248}`；`verify_bytes: 4 文件 / 67「平台×点」/ PASS`；三件节点产物跑批前后 md5 不变。
- 门控（我方重跑）：`check-tests-index` PASS（485 条）、`check-case-ledger` PASS（2184 条）、`validate-vectors` gaps 0、`inst_sweep` 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变、`check-inst` rc=2 红集恰 `divrem.yaml[23]`（未扩大；日志中 0 处 `12-misc` ⇒ 该门控不跑 .S）。
- **独立复算**（reviewer 自写，用 `bit_length/bit_count` 位运算，**未 import** 其 `oracle_check.py`）：**67 链点 / 不符 0**；`ctpop(0x0123456789ABCDEF, hd=63)=0x20`（=32）——F1 已按真实语义修正。
- **独立字节核对**（读回 `.run/base` 的 `.out`）：4 文件三平台逐字节相同，67 条记录与我方复算全等。
- **独立注入 1 路**（非其 ctlz-pt9/swym-pt9）：cttz 点 4 **输入** `0x0000010000000000→0x0000000000010000`（期望仍 0x20）⇒ 套件 rc=1、三平台同点号 `{'chipyard':4,'qemu':4,'gem5':4}`；`cp` 备份+md5 还原（本地/节点均 `980c63ec…`）⇒ 回绿 rc=0（`INJECT_REVIEW: PASS`）。
- 片段：`merge_fragments.py --check` rc=0（新增 4 → 289）；id `inst-12-misc-025..028` 与根清单不重、`file` 均存在、合并后 12-misc = 28。
- 范围对账：`git diff --name-only master...HEAD` = 任务书「修改文件」7 项，逐条一致；`git status -uall` 干净；28 个 `.S` md5 事后 == 事前快照。

**约束核验**：未改 `contracts/`/`spec/`/`Makefile`/根清单/`MIGRATION.md`/`README.md`/宏层/驱动器 ✓；`bitcnt/bitcnt.yaml`（ctlz/cttz/ctpop 各 138 例）与 `base/misc.yaml`（swym 2 + escape 4）**未删未改** ✓；GAP 成立（`SimRISC-12 §2`：N+1 倍时延/上限属性能语义，功能层无观测点）✓；台账红线**确为基线陈旧**（overlay master 版台账后 `make check-milestones-fresh` **rc=0**，我方现场验证并 `cp`+md5 还原）✓；未跑 `install-host` ✓；完成区 15 行、无运行期路径 ✓。

**阻断项（唯一，均在证据脚本，不在交付物）**
1. `[FAIL] 既有 lr/sc 载体未被本任务改动（git status …）期望=4 实际=0` —— 断言用裸 `git status`，architect 提交 `3acc433e` 后恒为 0 ⇒ **假 FAIL**（违反 AGENTS「断言须带 `$BASE..HEAD`，禁裸 `git status/diff`」）；同段第 2 条 `git diff … HEAD` 提交后恒空 ⇒ 恒真空转。改法：以 `git merge-base HEAD master` 为基线判（lr/sc 相对基线无改动 + 本任务 4 个 `.S` 相对基线新增）。
2. `[FAIL] check-milestones-fresh 违规集 == 5 行` 实际 **6 行**（多 `m13-spec-008`，系并发会话在基线后于 master 派单 `700a9928`）—— 写死集合随在跑任务增长。改法：违规集**现场派生**，或直接以「overlay master 台账后 rc=0」为判据（已验 rc=0）。
- 次级（不阻断）：`点号连续` 用 `grep -c ERROR`，`--scan-only` 整体失败时会假绿 ⇒ 建议同时断言其 rc。

**未决/建议**：① 节点三件产物与主控机**当前**构建树 md5 **均不一致**（qemu `5d04d3e8…` vs `b34ed7f9…`、chipyard `45748f3f…` vs `ac6a1480…`、gem5 `bc1b1b5f…` vs `49e600e3…`）——我**不据此推翻结论**（判据是同一 ELF 三方逐字节 + 独立 oracle + 跑批前后 md5 不变），但 `sync_node_artifacts.sh` 未跑属既有要求，建议合并后在共享构建区稳定时补跑一次并留 md5。

**判决：Needs Revision** —— 仅需修 `run.sh` 上述两处状态依赖断言并重跑 `run.sh all` 回绿；交付物（4 个 `.S`、片段、语义/编码、三平台、注入、其余门控）本轮全部核过，无需重做。

### 第 3 轮 reviewer 验收（2026-11-14，复验两条阻断项）

**四条 rc（我方实跑，非采信其自述）**：`run.sh points` → **0**（`BASE=b46313e0`、命中 `ctlz/ctpop/cttz/swym` 4 个 `.S`、lr/sc 0）；`run.sh gates` → **0**（overlay `changed` → 还原 md5 `6d773be6…` → `check-milestones-fresh` rc=0）；`run.sh --inject` → **0**（两路三平台同点红→`cp`+md5 还原→回绿）；`run.sh all` → **0**（7/7 镜像、67「平台×点」、三件节点产物跑批前后 md5 不变）。

**阻断项 1 复验（区间断言）**：改法成立——`BASE=$(git merge-base HEAD master)`、`RANGE=${DIFF_RANGE:-$BASE..HEAD}`，断言「RANGE 内 `12-misc` 文件集 == 4」+「lr/sc 命中 0」并打印 `BASE/RANGE/命中清单`；裸 `git status`/`git diff HEAD` 断言已删净（grep 仅剩注释）。**我方独立可失败证明（只用既有提交，零新对象、不动 ref）**：`DIFF_RANGE=e132b5f3..cac76845`（028 加入 24 个 lr/sc 的区间）⇒ **rc=1**，`文件集 期望4 实际24` + `lr/sc 期望0 实际24`；`DIFF_RANGE=HEAD..HEAD` 空区间 ⇒ **rc=1**（fail-closed）；去掉 `DIFF_RANGE` ⇒ **rc=0**；事后 `for-each-ref`=15（与事前同）、仅 `refs/heads/m13-testcases-029`、`git status` 干净、HEAD 仍 `89386801`。其自证悬挂提交已核：`87ec1c74`（父 `3acc433e`，仅 `lr.b.nn_orrr_rd.S` +1 行），`git branch/tag --contains` 皆空 ⇒ 无 ref 指向；不可达对象 1 个，`git gc` 可回收（观察项）。

**阻断项 2 复验（overlay 判据）**：顺序 = 备份 → overlay → `make` → **无条件 `cp` 还原** → md5 对账 → 判 rc，中间无 `exit`、无 `set -e` ⇒ 门控红也会还原。**我方红路径实测**（`PATH` 垫 `make` 令该门控返回 97）：`[FAIL] check-milestones-fresh rc 期望=0 实际=97` + `[PASS] 台账已还原 md5=6d773be6…` + 整体 **rc=1** + `git status` 干净 ⇒ 红不被掩盖、还原不依赖门控结果。**未掩盖别的红**：无 overlay 现场 rc=2、7 条违规**全部**落在 `milestones-m13.md`（A1×1 + R1×6，均为「行仍在待开始」），`m12/m14/m15/m16/milestones.md` 全 PASS；overlay 后 m13 表 `待开始 12→6 / 进行中 1→7`（6 行移动 == 6 条 R1，A1 由同一行移动解决），且 A1 仍校验本任务书 `待验收 ↔ 进行中`；取不到 master 版 ⇒ `ck` 失败传播非零（读码确认）。

**不许回归**：`git diff --name-only $BASE..HEAD -- tests/` = 6（4 `.S` + 2 片段）；`check-tests-index` 485、`check-case-ledger` 2184、`validate-vectors` gaps 0、273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变、`check-inst` 红集恰 `divrem.yaml[23]`（1 处）；28 个 `.S` md5 == 第 2 轮快照（交付物零改动）。**审阅记录/完成区**：第 2 轮记录 23 行逐行比对**未被改写**；完成区 22 行 ≤30（返工说明为尾部追加，未改写既有行）；`89386801` 相对 `3acc433e` 仅任务书 +30 行。

**次级（不阻断）**：① overlay 段**无 `trap`**——脚本若在 overlay 窗口（该门控运行数秒）被 SIGTERM/SIGINT 杀掉，会把 master 版台账留在 worktree（`git status` 的 tracked 修改可发现），建议 `trap … EXIT`；② `DIFF_RANGE` 是门控可覆盖口（已验空区间 fail-closed、非本任务区间必红，正常路径无法借此凑绿）；③ 本脚本为**生命周期内**证据工具，合并到 master 后 `BASE=HEAD`、overlay 同内容会假红（不在验收窗口，合并后不必再跑）；④ 节点三件产物仍与主控机构建树 md5 不一致，建议合并后补跑 `sync_node_artifacts.sh` 留 md5。

**判决：Accepted** —— 上轮两条阻断项均已按建议修复，并经我方独立重跑（四模式 rc=0）+ 独立反例注入（可达 FAIL、还原回绿）证实；交付物与门控无回归。

## 完成区

**测试结果**：三平台 `run_asm_suite` 4 id / **7 镜像 7/7**（链例 4 + 故障例 3，chipyard==QEMU==gem5 rc 全同）；结果缓冲 **67 链点 × 3 平台逐字节一致**且 == 独立复算（67/67、0 不符）；注入 2 路各三平台同点红（`ctlz` pt9 期望 0x20→0x21 / `swym` pt9 IP 差 0x14→0x10）、`cp`+md5 还原回绿；门控 `check-tests-index`/`check-case-ledger`/`validate-vectors`（gaps 0）rc=0、273 例 md5 不变、`check-inst` 红集恰既有 pin `divrem.yaml[23]`（rc=2）；证据脚本 `run.sh {points,run3,inject,gates}` 与 `run.sh all` 均 rc=0。
**修改文件**：新增 `tests/inst/12-misc/{ctlz,ctpop,cttz}_orri_rd.S` + `swym_oiii_imm.S`（4 个）；新增 `tests/inst/.fragments/m13-testcases-029.{inst.yaml,migration.md}`（4 条 + §1/§6 片段）；改本任务书（审阅记录 + 完成区 + 状态）。`git status -uall` 仅上述 6 个新增 + 任务书。
**验收结果**：
- `.S` 数 4 == `contracts/opcodes.yaml` 的 `ctlz`/`cttz`/`ctpop`/`swym` id 数 4；每 id 18 链点 + 1 故障例，`swym` 13 链点且无故障例（`legality: []`）；点号 1..N 连续、≤127（现场：链点 67、故障 3）。
- 三方逐字节：7/7 镜像；67 个「平台×点」记录三平台完全相同且 == 独立复算；故障例 ILLI `0xF8` 三方同值（3 例）。
- 独立复算（模型 B：位循环实现 + 字节字典内存 + 直接解析 `.S` 仿真 `__LI`/`LOAD_ADDR`/`st.o`/`ld.o`/`aip.si`/`swym`/`.dd.t32`/`sub.o`/`rb2rd`；原始编码字按 `opcodes.yaml` 的 mask/value/ha 复核）：67/67 PASS。
- 注入：`ctlz` pt9、`swym` pt9 ⇒ 三平台均 rc=9（套件 rc=1）；还原后 md5 本地==节点、套件回绿。
- 片段：YAML 可解析、4 条、字段五项、id 与根清单不重、`file` 存在；`merge_fragments.py --check` rc=0（新增 4 → 289 条）。
- 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变（covered=273）；`check-tests-index` 485 条、`check-case-ledger` 2184 条均 PASS。
- 产物：节点侧 qemu `5d04d3e8…`、chipyard `45748f3f…`、gem5 `bc1b1b5f…`，跑批前后不变；**未同步**（共享构建区正被并发会话重建，见「新发现」①）。
**新发现/坑**：① 共享构建区的 qemu/gem5 二进制可在跑批窗口内被并发会话重建（gem5 一度仅 41 MB 且不可执行）⇒ 不得向节点推半成品；判据取「三平台对同一份 ELF 的结果」，产物 md5 只记节点侧 + 跑批前后不变。② `.S` 行内宏实参与宏名之间是 **tab** ⇒ 证据脚本的 `grep` 计数须用 `[[:space:]]`（空格模式恒 0，会造出假红）。③「有效位上界 `hd`」类用例的**可判性**：越界位须改变「忽略 `hd`」实现的结果，否则断言恒真（`cttz(hd=7, v=1<<8)` 与全 64 位同为 8）。④ 本 worktree 基线早于 master 的派单提交（台账 5 行未移动）⇒ `check-milestones-fresh` 红属基线差异，已在合并后的 master 台账上 overlay 验证 rc=0。⑤ `check-inst` 长跑可能被并发会话 SIGTERM（rc=143）打断 ⇒ 有据重试并记录次数。
**遗留问题**：① `bitcnt/bitcnt.yaml`（`ctlz`/`cttz`/`ctpop` 各 138 例）与 `base/misc.yaml`（`swym` 2 例，另 4 例 `escape` 属 `11-cfx`）未删 —— 属 §5.1 前置（载体登记改 `.S` + 数据覆盖门控 + 台账重生成）与根清单 `file:` 条目，与 `m13-testcases-030` 同批；② GAP：`swym N` 的时延倍数/上限属性能语义（功能层无观测点），不写用例、不伪造。无未修 finding。

**返工（reviewer 第 2 轮，仅证据脚本 `run.sh`；交付物零改动）**：
1. 阻断项 1（裸 `git status`/`git diff HEAD` 在提交后恒空）：删两条，改 `BASE=$(git merge-base HEAD master)` + `RANGE=${DIFF_RANGE:-$BASE..HEAD}`，断言「`RANGE` 内 `tests/inst/12-misc` 文件集 == 本任务 4 个 `.S`（现场派生）」与「既有 lr/sc 命中数 == 0」，并打印 `BASE`/`RANGE`/命中清单。
2. 阻断项 2（写死「违规集 == 5 行」）：改 **overlay 判据** —— `git show master:<台账>` 覆盖（`cp` 备份 + md5 对账 + `cp` 还原再核 md5），断言 `check-milestones-fresh` rc=0；取不到 master 版/覆盖无效/还原不一致均传播非零。
3. 次级：`--scan-only` 增断言**其自身 rc**（并留 ERROR 计数）；模式支持 `--points/--inject/...`，未知模式 rc=2。
4. 真实 rc：`run.sh points`=0、`run.sh --inject`=0、`run.sh gates`=0、`run.sh all`=0（`all` 内 7/7 镜像、67「平台×点」、overlay rc=0、273 md5 不变、`check-inst` 红集仍恰 `divrem.yaml[23]`）。
5. 新断言可失败证明（不动交付物、不提交）：用 `git commit-tree` 造**悬挂提交**（树 = HEAD + 既有 `lr.b.nn_orrr_rd.S` 多一行注释；不动 ref/worktree），`DIFF_RANGE=BASE..<悬挂>` ⇒ `points` rc=1（文件集 5≠4、lr/sc 命中 1）；去掉 `DIFF_RANGE` ⇒ rc=0。

