# m12-chipyard-024: quiet compare 遇 sNaN 置 `NV`（RTL + 模型 + 向量 + spec）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-qemu-004`（QEMU 先行对齐）+ `m12-chipyard-014`（已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 用户裁定（2026-11-12，原话）

> 「改为置 NV（跟 IEEE）」

落盘：`.tao/knowledge/discussing.md`「已裁定：quiet compare 遇 sNaN 也置 `NV`」。

## 背景

现行实现（`013` 定、`m13-qemu-003` 同步）：signaling compare 任何无序 ⇒ `NV`；quiet compare **恒不置**。

IEEE 754-2019 §5.11：quiet 谓词遇 **sNaN** 仍置 invalid（hardfloat 同）。用户裁定跟 IEEE。

**两条裁定并存**：
- signaling（`ftscmp`/`foscmp`）：任何无序（含 qNaN）都置
- quiet（`ftqcmp`/`foqcmp`）：**仅 sNaN** 置；qNaN 不置

## 目标

1. **RTL**：`WumingFP.scala` 比较的 `NV` 条件改为
   `NV = Mux(io.signaling, unordered, rawA.isNaN_s || rawB.isNaN_s)`（quiet 仅在 sNaN 输入时置）。
2. **模型** `tools/chipyard/fp_ref.py` 同步（与 spec 一致，不是与 RTL 一致）。
3. **向量**：`cmp_nan` 组补「quiet + sNaN ⇒ NV=1」「quiet + qNaN ⇒ NV=0」四组，并保留 003 的 signaling 例；`divrem`/`arith` 相关期望同步。
4. **spec 补写**：`spec/SimRISC-07 §4` 比较一节，按 `ISS-396` 的三点修正后入册：
   - 条号用 `§5.6.1` / `§5.11`（不用 `§5.7.1`）
   - 明确 signaling 与 quiet 两条规则（signaling 任何无序、quiet 仅 sNaN）
   - 写明「本核 signaling 对 qNaN 也置 invalid 是 IEEE 一致行为；quiet 对 sNaN 置 invalid 为 IEEE 754-2019 §5.11 行为」
   - 版本按 `Process-03` 记 `Machine-v5`/`SimRISC-07` 附录条目

## 验收标准

1. 四组例 × ft/fo 逐条给输出：`ftqcmp(sNaN,1.0)⇒NV=1`、`ftqcmp(qNaN,1.0)⇒NV=0`、`ftscmp(qNaN,1.0)⇒NV=1`、`ftscmp(1.0,2.0)⇒NV=0`。
2. 三方一致：chipyard == QEMU（`m13-qemu-004` 后）== 模型，逐字节；`cmp_nan` 不再有 model-only 子组（sNaN payload 差异除外，需单列说明）。
3. **可达 FAIL 注入**：把 quiet 的 NV 条件去掉 ⇒ 新例红 ⇒ `cp`+md5 还原回绿。
4. 273 例 md5 不变；`check-inst`/L2/`check-patch-tree` rc=0。
5. spec 门控：`check-spec-*` 全绿，版本与附录按 `Process-03`。
6. 一键证据脚本；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账。

## 说明

- `.work` 必须软链（`ISS-389`）；`JOBS=8`。
- 与 `015` 串行（同组件单写者）。
- spec 正文改动需 architect 校后入账（本任务起草 + 跑门控，不自行定稿）。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数从脚本现场输出直接抄。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## spec 补写草案（architect 校后入账；本任务未改 `spec/`）

条号按任务书指定（`ISS-396` 的三点修正）：用 `§5.6.1` / `§5.11`，**不用** `§5.7.1`。本任务不独立复核标准原文编号。

### 草案 1：`spec/SimRISC-07-浮点运算.md` §4「浮点比较指令」

在现有「rdHB 中的比较结果有四种情况」列表**之后**、讲 qNaN/sNaN 按整型解读那一段**之前**插入：

> 异常标志与 NaN 类别的关系如下（IEEE 754-2019 §5.6.1 / §5.11）：
>
> - **Signaling Compare**（`ftscmp`/`foscmp`）：只要比较**无序**（任一操作数为 sNaN **或** qNaN）即置 **NV**——signaling 谓词把「无序」本身视为无效操作，不区分 NaN 类别（§5.6.1）。
> - **Quiet Compare**（`ftqcmp`/`foqcmp`）：仅当操作数中含 **sNaN** 时置 **NV**（§5.11：quiet 谓词遇 signaling NaN 仍发出 invalid）；操作数只含 qNaN 时是安静的无序结果，**不置任何标志**。
> - 有序比较不置任何标志。四条比较指令只可能置 `NV`，不置 `DZ`/`OF`/`UF`/`NX`；标志按累积（sticky）语义写入 `rf0[4:0]`。
> - 两条规则并存且不矛盾：signaling 形式对 qNaN 置 invalid 是 IEEE 一致行为（§5.6.1 以「无序」为条件），quiet 形式对 sNaN 置 invalid 是 §5.11 的要求。

### 草案 2：`spec/SimRISC-00-指令系统设计.md` 附录「版本与变更记录」

在 `### 0.5.7-rc（未发布）` 段内追加一条（变更记录集中于 `SimRISC-00`，`SimRISC-07` 不单列）：

> - **浮点比较的 NaN 与 `NV`**：`ftscmp`/`foscmp` 对任何无序（sNaN 或 qNaN 操作数）置 `NV`（IEEE 754-2019 §5.6.1）；`ftqcmp`/`foqcmp` 仅在操作数含 sNaN 时置 `NV`（§5.11），仅含 qNaN 时返回 qNaN 且不置标志。比较指令只可能置 `NV`。

### 草案 3：版本与门控（入账时执行）

- `SimRISC-07` 头部版本**不变**（仍 `0.5.7-rc`，与 `SimRISC-00`…`12` 同组互锁）；按 `spec/README.md`「加记录本身不引发 `-rc`」，本草案只往既有 `-rc` 段追加条目，不开新段、不改版本号。
- 改 `spec/` 须**用户事先授权原话**；若该册在 sha256 只读锁内，须在**同一次变更**内更新锁（`check-spec-readonly`）。
- 入账后须跑：`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-drift`、`check-spec-readonly`、`check-spec-codeblocks`、`check-spec-cite-targets`。
- 建议同批把 `.tao/contracts/contract-fp.md` §8 `compare` 补一条 NV 规则（现仅写结果值，未写标志；本任务未改合约，避免跨任务越界）。

## 完成区

**测试结果**（返工后重跑，一键证据脚本带 `RUN_CHECK_INST=1`）：`== summary: PASS=83 FAIL=0 ==`、`FINAL_EXIT=0`；`--self-test-inject`：`SELFTEST rc=0`（`SELFTEST_EXIT=0`）。

**四组实测**（核上 `rd5`/`rf0`；三层逐字节：核 == QEMU == YAML）：
- `ftqcmp(sNaN,1.0)` ⇒ `0x000000007fc00000` / `0x7ff800007fc00001`（nv=1，QEMU nv=1）
- `ftqcmp(qNaN,1.0)` ⇒ `0x000000007fc00000` / `0x7ff800007fc00000`（nv=0，QEMU 同）
- `ftscmp(qNaN,1.0)` ⇒ `0x000000007f800001` / `0x7ff800007fc00001`（nv=1，QEMU 同）
- `ftscmp(1.0,2.0)` ⇒ `0xffffffffffffffff` / `0x7ff800007fc00000`（nv=0，QEMU 同）
- fo 同四组：`0x7ff8000000000000/…001`、`…/…000`、`0x7ff0000000000001/…001`、`0xffffffffffffffff/…000`

**验收结果**：D 段 14 例 compare 全 `core == QEMU == YAML`（`qemu_same=14`、`qemu_nv_only=0`、`qemu_bad=0`）；quiet+sNaN 两个引擎都 `NV=1`、quiet+qNaN 都 `NV=0`；`arith.yaml` 其余 21 例核上全绿。E 段 273 例 md5 `2d4d94651346ef673c5a855e024c1489`（期望与核输出同）不变。F 段单元台 compare 四组各 144 例 `hf-flag-diff=0`/`oracle-diff=0`（已删 quiet/sNaN 容差）。G 段 `check-index-blobs`/`check-source-state`/`check-case-ledger`/`validate-vectors`/`check-fp-contract`/6 个 `check-spec-*` rc=0，**L2 rc=0**；`check-patch-tree` 本树 rc=2 但 offenders 只有 `qemu`（`chipyard=0`），L1（`-k`）红项 5 个全属他任务/基线（guard 命中 0）。H 段 `check-inst` **rc=0**（1066 total / 1061 passed / **0 failed** / 5 deferred；tiny 44/44）。B 段手算锚点 13 条 `anchors_bad=0`。
**注入**：quiet 的 NV 条件改回 `false.B` ⇒ 重建 ⇒ D 段红满 4 例（恰为 quiet+sNaN；`core==YAML 14→10`）⇒ `cp`+md5+`touch` 还原（`58d587767c47022c0a8bea0a9dfd320a`）⇒ 重建 ⇒ D 段回绿；`SELFTEST rc=0`。
**R4 基线归属（临时树实测）**：`git archive master` + 对本任务 8 个文件做 `git merge-file` 三方合并（仅 `components/chipyard/changelog.md` 冲突，两条并留）⇒ `check-patch-tree: 9 patch set(s), 333 patches OK`（rc=0）、单元台 `TOTAL failed=0`（含 `f2f fo2ft` 0）⇒ 本树的两处红（qemu 补丁 + `f2f fo2ft`）纯属基线早于 `m13-qemu-004`/`m12-chipyard-026`，合入即消；**合并后请 architect 在 master 复跑留证**。
**修改文件**（`git status -uall` 9 项，逐项一致）：本任务书；`components/chipyard/changelog.md`；`components/chipyard/patches/.../WumingFP.scala.patch`、`.../WumingFPUnitHarness.scala.patch`；`tests/case-ledger.tsv`；`tests/inst/fp/arith.yaml`；`tools/chipyard/{fp_ref.py,fp_sweep.py,fp_unit/unit_run.py}`。
**新发现/坑**：① 本树基线早于 `m12-chipyard-026`，`f2f fo2ft` 的 oracle 差异（154）只在合并前存在、合并后为 0（临时树实测）；② 任务 worktree 的安装根按 `paths.py` 就地解析 ⇒ L2 的 `build-bootrom` 需把 `.dadao` 软链到安装根（run.sh 已内置）；③ L1 须用 `-k` 才能一次列出全部红项（否则首个红即停、归因不完整）；④ `components/chipyard/changelog.md` 与 master 同锚点各插一条 ⇒ 合并冲突，两条并留；⑤ 本机 `grep -E` 对 `(` 按字面处理（BRE 行为），标签查表用 awk。
**遗留问题**：`spec/` 未改（草案见下，architect 校后入账），`.tao/contracts/contract-fp.md §8` 建议同批补 NV 规则；`m13-qemu-004` 已合入 ⇒ 三方一致与 `check-inst` 均已达成，无功能遗留；`ISS-396` ②③ 由 architect 收尾关闭。

## 审阅记录

### 第 1 轮 engineer 自审

**方式**：逐行读 9 个文件的 `git diff` + 改后 RTL 段；对照 `spec/SimRISC-07 §4` 与 IEEE 754-2019 §5.6.1/§5.11 及 hardfloat `CompareRecFN` 的 `invalid` 表达式逐项核；证据脚本全量跑 + 注入自检各一轮。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 重导出补丁带入 025 未导出的 RTL（master 补丁落后于源树） | ❌不修（越界） | 无（已在完成区披露；不导出反而会让 025 的 RTL 丢失） | patch diff 仅 2 文件；`check-patch-tree`/`--source-state`/`check-source-state` rc=0 |
| F2 单元台 `f2f fo2ft oracle-diff=154`（025 model 遗失） | ⏸延后 | F 段改为「total == f2f 组」精确归因 | `expected=154 actual=154`，其余组全 0 |
| F3 标签查表用 `grep -E`，本机按 BRE 处理 ⇒ 17 条 row 断言全红 | ✅已修 | 改 `awk '$1==k'` | D 段 17 条 row 断言全 PASS |
| F4 任务 worktree 内 L2 找不到 `.dadao`（安装根就地解析） | ✅已修 | run.sh 内置「非安装根则软链共享根」 | L2 rc=0 |
| F5 L1 `check-knowledge-refs` 红（他任务书的具体 `.work/` 路径） | ⏸记录 | 不改他人任务书；脚本按「唯一红 + 本任务书 0 命中」归因 | 输出两条 pre-existing；`mine=0` |
| F6 `check-inst` 红 4 条（QEMU 未实现 quiet+sNaN） | ⏸阻塞（待 `m13-qemu-004`） | 新增段 H：现场派生期望失败集并逐条比对 | `19 20 23 24` == 期望集 |
| F7 初版把「有序例」计入 `quiet_qnan`，指标语义错 | ✅已修 | 分类为 sNaN/qNaN/有序三类分别统计 | `snan=4 qnan=4 ordered=2 nv=4` |
| F8 初版断言 `cmp>=15` 与实际 14 不符（凭空估数） | ✅已修 | 改为现场值 14 | PASS |

**判决**：本任务实现相关的 finding（F3/F4/F7/F8）全部已修并复验；F1/F2/F5/F6 为越界、他任务遗失或外部阻塞项，已在完成区「未达成验收项 / 新发现 / 遗留问题」逐条落地，无静默项。

### 第 1 轮 reviewer 验收（2026-11-12）

**判决：Needs Revision** —— **实现语义、三方逐字节一致、`check-inst` 均已实测达标**（见①②）；红项在**证据脚本自身**与**工作树基线**，须返工后复跑。环境：任务 worktree、`JOBS=8`、本机亲和 `0-63`（不涉 207/208）；长输出留运行期日志（`rerun-full.log`、`inject-selftest.log`、`myinject*.log`、`my-check-inst.log`）。

**重跑记录（本人命令 + 真实输出/退出码）**
- 全量脚本 `JOBS=8 RUN_CHECK_INST=1 bash <一键证据脚本 run.sh>` ⇒ `summary: PASS=77 FAIL=4`、`FINAL_EXIT=1`；4 红：`QEMU differs on exactly the quiet+sNaN cases (m13-qemu-004 pending) | expected=4 actual=0`、`QEMU divergence set | expected=quiet+sNaN only (4) actual=0`、`patch-tree rc | expected=0 actual=2`、`L1 (make check) rc | actual=rc=2 bad=check-patch-tree mine=0`。
- `check-inst`（两路）：脚本 H 段 `timeout 3000 make check-inst` ⇒ `[PASS] check-inst (L3) rc | expected=0 actual=0`；我另在本工作树直接跑 `timeout 3000 make check-inst` ⇒ `MY_CHECK_INST_EXIT=0`，`Results: 1066 total, 1061 passed, 0 failed, 5 deferred, 0 errors`，`FAIL arith` 行数 = 0；5 deferred 全为 `reg-cond-assign.yaml[15..19]`（既有登记，与本任务无关）。
- 脚本自带注入 `bash <一键证据脚本 run.sh> --self-test-inject` ⇒ `SELFTEST_EXIT=1`：注入轮红 **4 例 quiet+sNaN**（`core==YAML 14→10`、`row ftqcmp_(sNaN_a/b)/foqcmp_(sNaN_a/b): NV expected=1 actual=0`）✓、`restore md5 matched | 58d587767c47022c0a8bea0a9dfd320a` ✓；**还原轮** `summary: PASS=22 FAIL=2`（2 红恰是上面两条过期 QEMU 断言）⇒ `[FAIL] restore did not return section D to PASS` ⇒ **「注入→FAIL→还原→回绿」断链**。
- 我自选反例（quiet 对**任何** NaN 都置 NV）：`cp -p` 备份 + md5 注入、`ONLY=C` ⇒ `BUILD1_EXIT=0`、`ONLY=D` ⇒ `D_INJECT_EXIT=1`，红项恰为 `row ftqcmp_(qNaN_a/b)/foqcmp_(qNaN_a/b): NV expected=0 actual=1`（quiet+sNaN 行仍绿）✓；还原 ⇒ `RESTORE_MD5=MATCH | 58d587767c47022c0a8bea0a9dfd320a`。**第 1 次复跑无效（我的疏漏：漏 `touch`，`cp -p` 保留旧 mtime ⇒ make 不重建、仍跑注入版）**，补 `touch` 后 `BUILD3_EXIT=0`、`ONLY=D` ⇒ `summary: PASS=22 FAIL=2`（红仍仅那 2 条过期断言）；终态 `check-source-state` 各组件 `OK … clean=True` rc=0、无 `*.inj-bak`/`*.reviewbak` 残留。
- 三方逐字节（自算、不采信完成区）：14 例 `core.out == qemu.out == *_expect.bin` ⇒ `three_way_mismatch=0`；`fp_ref.cmp_exact` vs YAML ⇒ `mismatch=0`；**独立 oracle**（不 import `fp_ref`，按两条裁定手推 14 例：signaling 任一 NaN⇒NV、quiet 仅 sNaN⇒NV、结果 quiet→canonical qNaN / signaling→canonical sNaN 符号清零、有序→1/0/-1）vs YAML ⇒ `cmp_cases=14 mismatch=0`。ISS-407 探针：`ftqcmp_(sNaN_a/b)` dump `a0a36613` vs `(qNaN_a/b)` `be46a3b7`、`fo` `bf79c9fa` vs `2e3b6c58` ⇒ 两侧状态真不同（sNaN 在右的两例独立成行）。
- 基线归属：主工作树 `make check-patch-tree` ⇒ `9 patch set(s), 333 patches OK` rc=0；本工作树 rc=2，2 红**全在 qemu**（`trans_fp.c.inc` 断言⑨/⑥）——本树基线 `db8a7e1c` 早于 `m13-qemu-004(0e0bd1c8)`、`components/qemu/**` 不在 9 项 `git status` 内、该补丁 `git diff HEAD master` 差 61 行 ⇒ 归属**基线落后**，非本任务交付物。同轮 `check-index-blobs`/`check-case-ledger` rc=0；`273 md5=2d4d94651346ef673c5a855e024c1489` 不变；`L2 rc=0`；6 个 `check-spec-*` rc=0。

**约束核验**：独立 worktree ✓；未 commit ✓（`git log master..HEAD`=0、`stash`=0、注入前后 9 文件 md5 逐项一致 `POST_SNAPSHOT_IDENTICAL_TO_PRE`）；「修改文件」9 项与 `git status` 逐项对账 ✓；未越界，补丁重导带入 025 RTL 已披露且与 master 补丁**逐字节相同**（`3ebefa91…` / `7130b5fc…`）⇒ 无重复导出、无回退 ✓；完成区 17 行 ≤30 ✓；`spec/` 未改 ✓；**一键证据脚本当前跑不通 ✗**；**完成区关键结论已过时 ✗**。自省：我在本审阅记录初稿里误写 2 处具体运行期证据路径，`check-knowledge-refs` 一度由 2 红顶成 4 红；已删除并复测 rc=2，红项仍是 `m12-chipyard-025` 与 `m13-spec-003` 两份**他任务书**（`mine=0`，与完成区归因一致）。

**返工要求（指名）**：① `run.sh` D 段两条「要求 QEMU 与核不一致」的断言是**方向性错误**（要求失败态），改为正向：`qemu_bad=0 && qemu_nv_only=0` 且 14 例 core/QEMU/YAML 逐字节；② H 段删掉「失败集 == `19 20 23 24` 即算 PASS」的容忍分支（qemu-004 已合入，该分支现会掩盖 QEMU 回归），期望 `rc=0`、失败集只作诊断；③ 全量重跑至 `FAIL=0`、`FINAL_EXIT=0`（含 `RUN_CHECK_INST=1`），`--self-test-inject` 须完整回绿；④ 任务分支基线同步 master 后复跑 `check-patch-tree`/`check` 为 0（或由 architect 合并后在 master 复跑留证）；⑤ 更新完成区过时段（`check-inst rc=2`「未达成」、`m13-qemu-004 未合入`、`PASS=80 FAIL=0`、L1 红项归因）。
**非阻断 findings**：F-a `components/chipyard/changelog.md` 与 master 同锚点各插一条 ⇒ `git merge-file` rc=1 冲突（`fp_ref`/`fp_sweep`/`unit_run` 三方均 rc=0），合并时两条并留即可；F-b 完成区/审阅记录 3 处相对运行期树措辞（共享源树、安装根、运行期目录各一，均无绝对路径），建议改「共享源树/安装根/运行期目录」；F-c `ISS-396` 仍 `open`，其②③已被 2026-11-12 裁定消解，收尾时更新/关闭（architect）。

#### 收尾（architect）

（待填）

## 返工项（reviewer 第 1 轮 Needs Revision，全在取证脚本 + 完成区）

**R1（阻断）**：`run.sh` D 段两条断言**方向反了**——要求「QEMU 与核不一致恰 4 例」，`m13-qemu-004` 合入后成功态反而变红（`expected=4 actual=0`）。改为**正向**：`qemu_bad=0 && qemu_nv_only=0`，且 14 例三方逐字节一致。

**R2（阻断）**：H 段保留「失败集 == `19 20 23 24` 即 PASS」的**容忍分支**，会掩盖 QEMU 回归 ⇒ 删掉，期望 `rc=0`，失败集只作诊断输出。

**R3（阻断）**：`--self-test-inject` 断链——注入轮 4 例红 ✓、`restore md5 matched` ✓，但还原轮 `PASS=22 FAIL=2`（红的就是 R1 那两条过期断言）。修完 R1/R2 后必须**完整回绿**（`SELFTEST_EXIT=0`）。

**R4（非阻断）**：`check-patch-tree` rc=2 的 2 红全在 **qemu**（本树基线 `db8a7e1c` 早于 `m13-qemu-004(0e0bd1c8)`，qemu 补丁差 61 行）；主工作树跑同门控 **rc=0**。⇒ 合并后由 architect 在 master 复跑留证；或在任务树里 rebase/同步基线后复跑。

**R5（完成区，过时项）**：①「`check-inst` rc=2 未达成」→ 已 **rc=0**（1066 total / 1061 passed / 0 failed / 5 deferred）；②「`m13-qemu-004` 未合入」→ 已合入；③「`PASS=80 FAIL=0`」→ 按修完后的真实值；④ L1 红项归因按现场。

**F-a（合并提示）**：`components/chipyard/changelog.md` 与 master 同锚点各插一条 ⇒ 合并时会冲突；**两条并留**。

**F-c**：`ISS-396` 的②③已被 2026-11-12 裁定消解，收尾由 architect 关闭，本任务不必动。

### 第 2 轮 engineer 返工自审（R1–R5）

**改动范围自证**：本次只改运行期一键证据脚本与本任务书。8 个交付文件的 `git diff --stat` 与返工前**逐项相同**（`8 files changed, 348 insertions(+), 67 deletions(-)`），两个补丁 md5 仍是 reviewer 记录的 `3ebefa91402a41caceaa598d21ff0735` / `7130b5fc31812af79a9fcb8ff939afcf` ⇒ RTL/模型/向量零改动。

| 返工项 | 处置 | 改了什么 | 复验证据 |
|--------|------|---------|---------|
| R1 D 段断言方向反 | ✅已修 | 4 条正向断言：`core==YAML`、`core==QEMU`、`qemu_nv_only=0`、`qemu_bad=0`；另加「quiet+sNaN 两个引擎都 NV=1」「quiet+qNaN 都 NV=0」 | `qemu_same=14 … qemu_nv_only=0 qemu_bad=0`；四组 `nv=1/qemu_nv=1`、`nv=0/qemu_nv=0` |
| R2 H 段容忍分支 | ✅已修 | 删「失败集 == `19 20 23 24` 即 PASS」，改 `eq rc 0`；失败集/向量索引只作诊断打印 | `[PASS] check-inst (L3) rc | expected=0 actual=0`；`failures: none` |
| R3 注入自检断链 | ✅已修（随 R1/R2） | 另加「注入轮红行数 == quiet+sNaN 行数」与 `SELFTEST rc=` 打印；还原保持 `cp`+md5+`touch` | 注入轮 `core==YAML 14→10` 且红行 4；`SELFTEST rc=0`、`SELFTEST_EXIT=0` |
| R4 基线落后致 patch-tree 红 | ✅按「可选」第二路 | 不 rebase（无提交权）；改用临时树 `git archive master` + `git merge-file` 三方合并实测，脚本内则把该红按「offenders 全是非 chipyard 组件」严格归因 | 临时树 `9 patch set(s), 333 patches OK`（rc=0）+ 单元台 `TOTAL failed=0`；脚本 `offenders=qemu chipyard=0` |
| R5 完成区过时项 | ✅已修 | `check-inst` 改 rc=0（1066/1061/0/5 + tiny 44/44）、`qemu-004` 已合入、`PASS/FAIL` 用 `83/0`、L1 红项按 `-k` 现场归因 | 见完成区 |
| F-a changelog 冲突 | ✅记录 | 合并提示保留；临时树实测 8 个文件中仅它 rc=1 冲突 | `merge … changelog.md rc=1`，其余 7 个 rc=0 |
| F-b 运行期树措辞 | ✅已修 | 完成区改「共享源树 / 安装根 / 运行期目录」，任务书内具体运行期路径 0 处 | 全文 grep 0 命中 |
| N1（自查）`make check` 首个红即停、归因不完整 | ✅已修 | 改 `make -k check`，一次列全 | 5 个红项全列并逐条打印来源 |
| N2（自查）guard 用 `$TASK.*\.work/` 会误命中构建路径行（`mine=3` 假阳性） | ✅已修 | 换成 5 条精确模式（chipyard 补丁行 / 本任务书 offender 行 / 台账 VIOLATION / `A3` 非法名 / 陈旧目录行） | `guards=0` 且打印的 offender 全是他任务与基线 |

**判决**：R1–R5 与 F-a/F-b 全部落地并复验，无未修项；一键证据脚本 `PASS=83 FAIL=0`（`FINAL_EXIT=0`）、`SELFTEST_EXIT=0`。

### 第 2 轮 reviewer 验收（2026-11-12）

**判决：Accepted** —— 第 1 轮 5 条返工要求逐条实测达成，验收标准 1–6 在**我自己的重跑**下全部通过；零改动核实、无新增提交、未改台账。长输出留运行期日志（`r2-full`、`r2-selftest`、`r2-patchtree-swapped/back`）。

**重跑记录（本人命令 + 真实输出/退出码）**
1. 全量 `JOBS=8 RUN_CHECK_INST=1 bash <一键证据脚本>` ⇒ `summary: PASS=83 FAIL=0`、`R2_FINAL_EXIT=0`、全文 **0 条 `[FAIL]`**；A 段现场计数 `cmp=14 quiet_snan=4 quiet_nv=4 quiet_qnan=4`、B 段 `anchors_bad=0 rows=13`、`sweep cmp_nan cases=20 quiet_nv=6 == quiet_snan_by_name=6`。
2. **R1**：D 段 4 条正向断言全 PASS —— `core == YAML 14/14`、`core == QEMU 14/14`、`no compare case: QEMU left NV clear 0/0`、`mismatch beyond the NV bit 0/0`；语义断言 `quiet+sNaN raise NV on the core 4/4`、`… on QEMU too 4/4`、`quiet+qNaN leave NV clear on both engines 0/0`、`[OK] three-way byte-exact`。通读全脚本 54 条断言：**无**「要求 QEMU 不一致」、**无**「失败集相等即 PASS」残留。
3. **R2**：H 段仅 `eq "check-inst (L3) rc" "0" "$RC"`，失败集/索引只作诊断打印；实测 `1066 total, 1061 passed, 0 failed, 5 deferred`（5 条全为 `reg-cond-assign.yaml[15..19]` 既有登记）、tiny `44/44`、`check-inst failures: none`。
4. **R3**：亲跑 `--self-test-inject` ⇒ `R2_SELFTEST_EXIT=0`、`SELFTEST rc=0`；注入轮 `injected: exactly the 4 quiet+sNaN rows went red`（红行数==quiet+sNaN 行数，新检查可达 FAIL）、`restore md5 matched | 58d587767c47022c0a8bea0a9dfd320a`、`restore -> section D PASS`（restore 轮 `PASS=26 FAIL=0`）⇒ **注入→FAIL→还原→回绿闭合**。
5. **R4（我用替换法独立闭合，不采信临时树说法）**：本树 qemu 补丁 `md5=c4f6151f…` ≠ master `4efa5f5a…`；`cp` 备份换 master 版 ⇒ `check-patch-tree: 9 patch set(s), 333 patches OK` **rc=0**（含本任务 chipyard 补丁）；`cp` 还原 ⇒ md5 MATCH、`BACK_RC=2`（qemu ⑨/⑥ 两红复现）、`git status` 0 行。旁证：本任务两份 chipyard 补丁 `worktree == master == HEAD`（`3ebefa91…`/`7130b5fc…`）。⇒ **chipyard 0 问题；qemu 两红唯一变量 = 本树基线早于 `m13-qemu-004`，属基线非交付缺陷**（本树现场亦为 `offenders=qemu chipyard=0`）。
6. **零改动**：8 个交付文件 md5 与第 1 轮快照**逐项 SAME**（changelog/两补丁/case-ledger/arith.yaml/fp_ref/fp_sweep/unit_run）⇒ RTL/模型/向量确未动。
7. **完成区逐条对账（全对）**：`PASS=83 FAIL=0`、`SELFTEST rc=0`、`qemu_same=14 qemu_nv_only=0 qemu_bad=0`、273 md5 `2d4d94651346ef673c5a855e024c1489`、`L2 rc=0`、F 段四组各 144 例全 0、`anchors_bad=0`(13)、注入 md5、`check-patch-tree offenders 只有 qemu(chipyard=0)`、`check-inst rc=0 1066/1061/0` + tiny 44/44。
8. **L1 归因我逐条读现场（非采信 `guards=0`）**：5 红 = `check-knowledge-refs`（2 条具体路径在 `m12-chipyard-025`、`m13-spec-003` 两份他任务书，本任务 0 条，复测 rc=2）、`check-patch-tree`（见 5）、`check-milestones-fresh`（`VIOLATION: R1: m12-chipyard-026: 有 worktree 但未列入表` —— **点名 026**）、`check-run-artifacts`（57 项全为 night/gem5/025/m13-spec-002 他任务日志名，`A3 .*024` 命中 0）、`check-temp-dirs`（5 VIOLATION 全为 gem5-003/testcases-006/chipyard-012/gem5-004 他任务目录，本任务为活动 worktree 已排除）⇒ 归因成立，非 grep 过窄假绿。
9. **纪律**：无新增提交（`git log master..HEAD` = architect 所提交的第 1 轮记录 + 返工两笔）、未 push、未改台账；`db8a7e1c..HEAD` 改动 **9 文件**与完成区「修改文件」逐项一致；完成区 17 行 ≤30、全文**无具体运行期文件路径**；本轮我只写本审阅记录（注入/替换实验均 `cp`+md5 还原并复测回原态）。

**非阻断遗留（交 architect，不阻本判决）**：① `changelog.md` 与 master 同锚点合并冲突，两条并留（完成区已记，8 文件中仅它 rc=1）；② 合并后在 master 复跑 `check-patch-tree`/L1 留证；③ `ISS-396` ②③ 由 architect 关闭；④ L1 三项他任务红（026 worktree 未入表、63 项他任务运行期残留）属他任务收尾，建议主会话一并派单清理。

#### 收尾（architect，第 2 轮）

（待填）

#### 收尾（architect，2026-11-12 19:04）

- 第 2 轮 reviewer **Accepted**：R1/R2 已改正向（54 条断言静态通读无残留「要求不一致」/「失败集即 PASS」）；全量 `PASS=83 FAIL=0`；注入链闭合（`[PASS] injected: exactly the 4 quiet+sNaN rows went red` ⇒ `restore -> section D PASS`，`SELFTEST_EXIT=0`）。
- **R4 用替换法独立闭合**：换 master 版 qemu 补丁 ⇒ `9 patch set(s), 333 patches OK` rc=0；换回 ⇒ 2 红复现 ⇒ **chipyard 0 问题、qemu 两红纯属基线早于 `qemu-004`**。
- 零改动核实：8 个交付文件 md5 逐项 SAME；`check-inst` rc=0（1066/1061/0 failed/5 deferred）；273 md5 不变；L2 rc=0。
- **合并处置**：`changelog.md` 与 master 同锚点冲突 ⇒ **两条并留**。
- 遗留：`ISS-396` ②③ 由 architect 关闭；L1 三项他任务红（含 `m12-chipyard-026` worktree 未入表）由主会话派单清理。

