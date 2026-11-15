# m13-testcases-035: 07 浮点补边界（余数零符号 + 无符号 f2i 负向）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-021`（余数族已建）、`m13-testcases-022`（f2i 族已建）
**可并行分片**：否（`tests/inst` 串行）
**预估**：1–2 h
**状态**：已验证

## 背景（两处规范裁定后的用例缺口）

1. **余数零符号**（`spec/SimRISC-07 §2.1`，2026-11-14 裁定「完全按 IEEE 754-2019 §5.3.1」）：
   - 非零余数符号由 `rfHC − n×rfHD` 决定（可与 `rfHC` 相反）——`021` 已有覆盖；
   - **余数为零时取 `rfHC` 的符号**——**当前无用例**（`+4 rem 2 = +0`、`−4 rem 2 = −0`、`+0 rem 2 = +0`、`−0 rem 2 = −0`）。
2. **无符号 f2i 的负向饱和**（`spec/SimRISC-07 §1.4`，2026-11-14 裁定「与 hardfloat/RISC-V 一致」）：
   - `NaN`/`+Inf`/正溢出 ⇒ 最大无符号值、`−Inf`/负溢出 ⇒ **`0`**；
   - `022` 已覆盖 NaN（含负号 NaN）与正向，**负向（`−Inf`、负溢出 ⇒ 0）无用例**。

## 范围

- `tests/inst/07-floating-point/ftrem_orrr_rf.S`、`forem_orrr_rf.S`：补零余数符号 4 例（`ft`/`fo` 各 2）。
- `tests/inst/07-floating-point/` 的 4 条无符号 f2i（`ft2ut`/`ft2uo`/`fo2ut`/`fo2uo`）：各补「`−Inf` ⇒ 0」「负溢出 ⇒ 0」两例（至少 `ft2uo`/`fo2uo` 各 2 例，其余各 1 例）。
- 其余文件不动；不改 `contracts/`、`spec/`、`Makefile`。

## 验收

1. 新增检查点现场统计、点号连续 ≤127。
2. 三平台逐字节（chipyard == QEMU == gem5，同镜像），含新点；零余数的**符号位**必须逐字节核（`±0` 不能只看数值相等）。
3. 独立复算（自写，用 host `math.remainder` 的 IEEE 语义 + 显式符号位判定）。
4. `check-tests-index` / `check-case-ledger` / `validate_vectors`（gaps 0）/ 273 md5 / `check-generator-sync` / `check-inst`（红集恰 `{divrem.yaml[23]}`）。
5. ≥1 路注入（把 `−4 rem 2` 的期望从 `−0` 改成 `+0`）⇒ 三平台同点号红；`cp`+md5 还原回绿。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree（分支 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/m13-testcases-035/`。
2. 不提交 git；`run_asm_suite` 用独占 work-dir（`ISS-431`）；节点跑批记录二进制 md5（`ISS-429`）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 日志 `.work/log/testcases/<任务ID>-<用途>.log`。

## 待裁定

1. **任务书前提与实盘不符（已按规格补齐缺口，请确认口径）**：
   - 余数侧：`021` 落地时已含 `+0 rem 2 = +0`、`-0 rem 2 = -0`、`5 rem 5 = +0`（正号零余数）。
     真正缺的只有**被除数非零且除尽**的符号组合 ⇒ 本次只补 `4 rem 2 = +0`、`-4 rem 2 = -0`。
   - f2i 侧：`022` 落地时**已含** `−Inf ⇒ 0 + NV`（四个无符号载体各 1 例）与负有限值饱和
     （`-1.0`/`-1.75`/`-2.5` 各若干）⇒ 「`022` 未覆盖负向」的说法不成立。本次改补两处
     **确实未覆盖**的子类：负向**溢出量级**（`-1e30`/`-1e300`）与 **`-0.0` 精确零**（无 NV 无 NX）。
   - 判据：`git show f1215710 -- tests/inst/07-floating-point/ft2ut_orri_rf.S` 可见 `−Inf` 用例；
     余数三例见 `ftrem`/`forem` 的 13/14/15 点（`021` 提交）。
   - **无需新语义裁定**（期望值全部来自 `SimRISC-07 §2.1`/§1.4），仅请确认「按未覆盖子类补」的口径。
2. **`-0.0 → 0` 的标志口径**（请确认无异议）：按 §1.4 属「有限值且取整在范围内、结果精确」
   ⇒ **无 NV、无 NX**（三平台实测一致）。若后续希望改判「负号一律 NV」，须先改 spec。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

逐行审 6 个 `.S` 的新增段（含故障例点号顺延）、两个片段文件、证据脚本四件
（`run.sh` / `oracle_check.py` / `points.py` / `verify_bytes.py`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书前提与实盘不符（`021` 已覆盖 `+0/-0 rem 2`、`5 rem 5`；`022` 已覆盖 `−Inf ⇒ 0+NV` 与负有限值饱和）⇒ 照字面复制会造重复点，真缺口 `±4 rem 2` 反而不补 | ✅已修 | 余数补 `±4 rem 2`；f2i 补「负向溢出量级」（`-1e30`/`-1e300`）与「`-0.0` 精确零」 | 点号/期望经 oracle 18 条断言复算；三平台 24/24 |
| F2 `verify_bytes.py` 初版按**小端**解析结果缓冲（`__REC` 实为**大端**落盘）⇒ `-4 rem 2`/`-0.0` 全假红、零余数符号位全报 0 | ✅已修 | 改 `struct.pack(">Q")` / `from_bytes(..., "big")` | 32 个「平台×点」全 PASS；符号位 `-4 rem 2` = 1、`+4 rem 2` = 0 |
| F3 `points.py` 初版把 encoding 宏（`TEST_FPENC`/`TEST_FPCVT_ENC_RD`）排除在链例序列外 ⇒ 点号连续性全假红 | ✅已修 | 改为「凡 `TEST_*` 行取其首参点号，`TEST_FAULT*` 归故障例」 | 6 文件点号均 1..N 连续（19/19/25/26/25/26） |
| F4 产物 md5 判据读主控机共享工作区，另有会话正反复重建 `gem5.opt`（读到 0 字节/半截/两次读同值但仍在链中）⇒ 假红 | ✅已修 | 判据加「非空 + 两次读同值 + 大小阈值 + **可执行位**」；不稳定时打 WARN 并改判「节点侧跑批前后 md5 不变」 | 跑批用节点侧完整副本 `bffd9415…`（736 MB、可执行），跑批前后 md5 不变；`qemu`/`chipyard` 与本机一致 |
| F5 新点落在 overlap 段之后但注释标 boundary（段序不理想） | ❌不修 | — | 重编号会改动已通过用例的失败点号（`031` 先例：只追加段、不重编号）；注释已标 `boundary：零余数…` 独立成段 |
| F6 期望值位型若由同一脚本「生成并校验」会自证 | ✅已修 | 生成用 `struct` 手写常量；校验用 `Fraction`+`math.remainder` 独立路径回读 `.S` | oracle 18/18（含 `-0.0`、`-1e30`、`-1e300`、`±4 rem 2`） |

未修 finding：无（F5 为「不改」的显式判断）。任务状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14，独立重跑）

**重跑记录（以下退出码均为 reviewer 亲自执行）**
- `run.sh points` rc=0：10 条新增点、点号 1..N 连续 ≤127；`git diff 3d6ca5f3..67f28860` 现场数新增链点 = 10（一致）。
- `run.sh oracle` rc=0（18/18）；**reviewer 自写复算**（`Fraction` + host `math.remainder`，六载体全部检查点）**152/152 PASS、rc=0**（覆盖零余数位型、`±0` 符号、`-1e30/-1e300`、六档取整、NV/NX 饱和、点号连续）。
- `run.sh run3` rc=1（**有据重试 1 次，同点红**）：`24/24 镜像通过（链例 6 / 故障例 18）`、`bytes: PASS`、六载体链例字节流三平台逐字节一致；唯一 FAIL = 本地 `gem5.opt` md5 `a6c53a0d…` ≠ 节点 `bffd9415…` ⇒ 根因：共享 `.work/…/gem5.opt` 于 11:53 被并发会话 `m16-gem5-008` 重建（`stat` mtime + `ps` 在证，本地稳定同尺寸可执行），节点侧跑批前后 md5 不变（PASS）⇒ **环境干扰，非交付物缺陷**。
- `run.sh inject` rc=0：`-4 rem 2` 期望 `-0→+0` ⇒ 三平台 `rc={'chipyard':19,'qemu':19,'gem5':19}` 红，`cp`+md5 还原回绿（本地==节点 `60da1ab7…`）。
- **reviewer 独立注入（自设计，非 `-4 rem 2`）**：`ft2uo` pt25 负向溢出期望 `0 → 0xFFFFFFFFFFFFFFFF` ⇒ `SUITE_RC=1`、三平台 `rc=25` 同点红；`cp` 还原后本地/节点 md5 均回 `79d7191a…`、`RESTORE_SUITE_RC=0` 回绿。
- `run.sh gates` rc=0（9/9）：`check-tests-index` 0（385）、`check-case-ledger` 0（2184）、`validate-vectors` 0（gaps 0）、`check-generator-sync` 0、sweep emit md5 `2d4d9465…`（covered 273 == list）、`check-inst` rc=2 红集恰 `divrem.yaml[23]`（1141/1135/1/5）。

**约束核验**：① 独立 worktree、分支=任务号，未改主工作树；② 我未提交 git，注入还原只用 `cp`+md5（未用 checkout/restore/stash）；③ 跑批独占 work-dir，节点产物 md5 已记（qemu `5d04d3e8…` / chipyard `45748f3f…` / gem5 `bffd9415…`）；④ `git diff --name-only` = 6 个 `.S` + 任务书 + 2 片段，`fornd/ftrnd/ftsclb/ftsgn*` 未触碰；⑤ 完成区 12 行（≤30）、`**状态**：待验收`；⑥ 前/后快照：HEAD `67f28860`、6 `.S`+2 片段 md5 全同、`git status` 干净（唯一变更为本审阅记录）。

**findings（不阻断）**：F1 `run.sh` 的 `sync_to_node` 失败不传播非零（潜在假绿；本轮 rsync 实成功——节点跑出 26 链点可证）⇒ 建议 `sync_to_node || fail=1`；F2 本地/节点 gem5 md5 比对在并发重建下必红 ⇒ 本地「稳定但已换新构建」也应走 WARN、以节点侧前后不变为准；F3 台账 `m13-testcases-035` 仍在 `milestones-m13.md`「待开始」表（状态已 `待验收`）⇒ architect 收尾移「进行中」并填派单时间；F4 `fo2ut` pt13 注释「越界→NV」与期望 `0x10`(NX) 不符（022 遗留；按「取整后判范围」口径 NX 正确，三平台一致）；F5 `verify_bytes.py` docstring 仍写「小端」（代码已按大端）；F6「待裁定」1/2 尚无用户原话，未决不阻塞（期望值与 `SimRISC-07 §2.1/§1.4`、`contract-fp` 一致，已独立复算）。

**判决：Accepted** —— 验收项 1–6 在 reviewer 重跑下全绿；`run3` 的 md5 比对红已根因定位（并发重建）并记录 2 次运行，实质判据 24/24 与三方字节流两次通过。

## 完成区

**测试结果**：三平台 `run_asm_suite` 6 id / 24 镜像 **24/24**（链例 6 + 故障例 18，三平台 rc 全同）；独立复算 **18/18**；注入 1 路 6 条断言全过；门控 **8/8**（`check-inst` 红集恰 `divrem.yaml[23]`，rc=2 属既有 pin）。证据脚本 `run.sh all` rc=0。
**修改文件**：`tests/inst/07-floating-point/{ftrem,forem}_orrr_rf.S`（各 +2 链点；故障例 18→20）；`{ft2uo,fo2uo}_orri_rf.S`（各 +2 链点；故障例 25–28→27–30）；`{ft2ut,fo2ut}_orri_rf.S`（各 +1 链点；故障例 25–28→26–29）；`tests/inst/.fragments/m13-testcases-035.{inst.yaml,migration.md}`（新增片段）。证据脚本在运行期证据目录（`run.sh` + `oracle_check.py` + `points.py` + `verify_bytes.py`）。
**验收结果**：
- 新增点 **10**（现场派生）：`ftrem`/`forem` 各 18（`4 rem 2 = +0`）、19（`-4 rem 2 = -0`）；`ft2uo`/`fo2uo` 各 25（负向溢出 ⇒ 0+NV）、26（`-0.0` ⇒ 0 无标志）；`ft2ut`/`fo2ut` 各 25（`-0.0` ⇒ 0 无标志）。点号 1..N 连续；链例 19/19/25/26/25/26 + 故障例 1/1/4/4/4/4（≤127）。
- 三平台逐字节：全部 `.out` 三平台 md5 相同；零余数符号位实测 `ftrem` pt19 = `0000000080000000`（bit31=1）、`forem` pt19 = `8000000000000000`（bit63=1）、pt18 两者全 0；新 f2i 点三平台均 `0000000000000000`。
- 注入：`-4 rem 2` 期望 `-0 → +0` ⇒ `rc {'chipyard': 19, 'qemu': 19, 'gem5': 19}`（套件 rc=1）；`cp` 还原后 md5 `60da1ab7…` 本地==节点，重跑 2/2 绿。
- 门控：`check-tests-index` rc=0（385 条）、`check-case-ledger` rc=0（2184）、`validate-vectors` rc=0（gaps 0）、`check-generator-sync` rc=0、`inst_sweep emit` md5 `2d4d94651346ef673c5a855e024c1489`（covered 273，emit==list）、`check-inst` rc=2 红集恰 `divrem.yaml[23]`（Vast 1141 total / 1135 passed / 1 failed / 5 deferred；Tiny 段因 Vast 非零未跑，同既有 pin 口径）。
- 运行期产物 md5（ISS-429）：qemu `5d04d3e8…`、chipyard `45748f3f…`（与本机一致）；gem5 `bffd9415…`（跑批时本机正被他会话重建 ⇒ 用节点侧完整副本，跑批前后 md5 不变，脚本打 WARN 记录现场）。
**新发现/坑**：①任务书前提需先核实盘（`021`/`022` 已覆盖部分缺口）——建议派单时对「缺口」类任务加一步「现场计数核对」；②结果缓冲是**大端**逐字节落盘，写字节级断言时勿按小端解析（假红）；③主控机共享工作区可能被他会话并发重建（`gem5.opt` 读到 0 字节/半截，甚至两次读同值但仍在链中）⇒ 产物 md5 判据要「非空 + 稳定 + 可执行位 + 节点侧前后不变」；④`ft`/`fo` 的 32 位位型在 `.S` 里写成 16 位十六进制，按字符串匹配会漏（应按 token 数值比较）。
**遗留问题**：无代码遗留。口径确认项见「待裁定」1/2（不阻塞验收）。

