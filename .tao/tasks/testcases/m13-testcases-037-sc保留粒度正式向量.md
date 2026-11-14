# m13-testcases-037: `sc` 保留粒度（精确地址+宽度）正式向量

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-qemu-014`（QEMU 去整字值比较）+ `m13-chipyard-002`（RTL 去整字值比较）；gem5 已合规
**可并行分片**：否（`12-misc/` 单册）
**预估**：2–3 h
**状态**：已验证
> **派单授权（用户 2026-11-14）**：`m13-chipyard-002` 合入后由主会话**直接连派本件**，不再逐件确认。


## 用户裁定（2026-11-14，原话）

> 「ISS-435：严格按spec来」

- 口径：保留标记键 = **精确地址 + 访问宽度**；清除事件只限 spec 所列（另一 hart 同址同宽 store、另一条 `lr`、异常/中断进入）；`sc` 自身成败都清。
- 因此：**同 hart 写同字另一字节 ⇒ `sc` 必须成功**；**不同宽度访问 ⇒ 不影响**。

## 背景

- `m13-testcases-028` 为登记三平台分歧写过一次性探针 `probe_gran.S`（3 个观测点，实际差异 `chipyard=2 / qemu=1 / gem5=0`），当时因为口径未定只记 GAP、**未入正式向量**。
- 现在用户已裁定走严格口径，`m13-qemu-014`/`m13-chipyard-002` 修实现 ⇒ 本任务把探针升级为**正式 `.S` 向量**，并覆盖到 5–6 个点。

## 范围

在 `tests/inst/12-misc/` 新增 **1 个** `.S`（建议名 `sc_gran_<format>`，与 028 既有 24 个原子 id 的命名风格一致；id 需在 `contracts/opcodes.yaml` 中实际存在——若「保留粒度」不是独立 id，则挂到既有 `sc.<w>.<序>` id 的**链例尾部追加**，请先核 `opcodes.yaml` 再定形态，并在完成区写明判据）。

覆盖点（每点写清 spec 依据 + 手算过程）：

1. **同字异址**：`lr.b [A]` → 写 `[A+1]` → `sc.b [A]` ⇒ **成功（0）**。
2. **同字同址不同宽度**：`lr.b [A]` → 写 `[A]` 的 4 字节（`.t`）→ `sc.b [A]` ⇒ **成功（0）**（不同宽度不清）。
3. **同地址同宽度写（同 hart）**：`lr.b [A]` → `st.b [A]` → `sc.b [A]` ⇒ **成功（0）**（spec 只列「另一 hart」；同 hart 普通 store 不清）。
4. **另一条 `lr` 后**：`lr [A]` → `lr [B]` → `sc [A]` ⇒ **失败（1）**（保留被新 `lr` 覆盖）。
5. **`sc` 自身消费**：`lr [A]` → `sc [A]`（成功）→ `sc [A]` ⇒ 第二次 **失败（1）**。
6. **异常进入后**（若可在链例构造）：`lr [A]` → 触发同步异常并返回 → `sc [A]` ⇒ **失败（1）**。

要求：

- 每点一行、期望**内联**；点号连续、≤127；**不得**把任一平台输出当期望；
- 若某点因单 hart 无法构造（多 hart 同址 store 清除），写 GAP，**不伪造**；
- 遵循 `tests/inst/MIGRATION.md §5.3`：只写本任务 `.S` + `.fragments/m13-testcases-037.{inst.yaml,migration.md}`；**不改**根清单/`MIGRATION.md`/`README.md`/宏层/驱动器（确需新宏则在 `.S` 内 `.macro` 局部定义）。

## 验收（逐条贴真实 rc）

1. **三平台逐字节**：`run_asm_suite.py`（chipyard/qemu/gem5）同 ELF，全点一致；给出每点三平台实测值。
2. **改前对照**：用**改前**二进制（`m13-qemu-014`/`m13-chipyard-002` 改动前的构建，若已不可得则用其证据目录备份）跑同一 ELF，点 1/2 应红——证明向量真的守护了裁定（贴在完成区）。
3. **门控改用 `.S` 面**（`043` 已退役 `check-inst`/`check-inst-smoke`/273 例 md5 钉）：`check-inst-asm` 264/897 不变（本任务只加检查点，不加 id）、`check-tests-index`（每 id ≤127）、`validate-vectors`、`check-case-ledger` 现场值。
4. ≥2 路可达 FAIL 注入（`cp`+md5 还原）：① 把点 1 期望改成失败 ⇒ 三平台同点红；② 把点 4 期望改成成功 ⇒ 三平台同点红。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules` / 真 `build-*`**（用构建树/安装根里已修好的三件二进制，记录 md5）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/inst/12-misc/**` + 本任务片段 + 任务书。
5. 大文件落 `/tmp/opencode/m13-testcases-037/` 并测完即删。

## 待裁定

1. **点 6（异常或中断进入清标记）未进正式向量——请确认处置口径。**
   - 现场：链例**可构造**（固件 hmon 返回槽指向固定 `.text` 桩），但四条进入路径三平台实测分歧
     （spec 全为「清 ⇒ `sc`=1」）：`MALIGN`/`CFXMEM`/`ILLI` = `chipyard 1 / qemu 1 / gem5 0`；
     `CFXTRAP`（`trap cfx_hmon,0`）= `1 / 0 / 0`。chipyard 四条全符合 spec。
   - 临时处置（建议）：**写 GAP 不进向量** —— 若把期望 1 内联，`gem5`（及 qemu 的 CFXTRAP 路径）
     会让链例红，直接挡 L2 `check-inst-asm`；而放宽成平台行为即「以实现反推」，任务书明确禁止。
   - 选项：(a) 按 GAP + 立 gem5/qemu 修复任务，修好后补 1 点（点号 22、故障例顺延 23）；
     (b) 现在就进向量接受红（不建议：红门控无回归价值）。
2. **安装根 qemu 仍是改前版本**（`b34ed7f9…`，`m13-qemu-014` 后未跑 `install-host`）⇒ 原样
   `make check-inst-asm` 在本向量点 17 红（900/901）；本任务的验收用门控体 + `--qemu` 改后
   构建树二进制（901/901）。请主会话决定何时 `install-host`（本任务禁跑）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15，自主逐行）

范围：`tests/inst/12-misc/sc.b.nn_orrr_rd.S` 新增段（点 17–21 + 头部）逐行核 spec 依据与手算拍值、
点号连续性、数据拍互不重叠；证据脚本六模式逐条核「断言 → 可达 FAIL 路径」；门控与改前对照组。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 点 6（异常进入）未入向量，与任务书「覆盖 6 点」有差 | ⏸延后（待裁定 1） | 头部 GAP 段 + 任务书 GAP 写明四方实测值；不把平台行为写成期望 | 四路径探针：chipyard `1 1 1 1`、qemu `1 1 1 0`、gem5 `0 0 0 0`（spec `1 1 1 1`） |
| F2 首版证据脚本 `pre.*.suite_nonzero` 期望串「非 0」vs 实际「非0」⇒ 假 FAIL | ✅已修 | 期望串统一为「非0」（3 处） | 改后 `run.sh pre` PASS=10 FAIL=0 |
| F3 首版注入备份写在 `$TMP/$VEC.bak`（子目录不存在）⇒ `cp` 失败 | ✅已修 | 备份改 `$TMP/bak.<tag>` + `mkdir -p`；trap 同步改 | `run.sh --inject` PASS=11 FAIL=0 |
| F4 首版 `mode_points` 残留无效 py 行、`$?` 被 `\|\| rc=1` 覆盖 ⇒ 判决不准 | ✅已修 | 改为显式 `prc=$?` + `eq` 判决 | 三平台各 5 行逐点 PASS |
| F5 工作树基线落后（`f4b2de26` vs master `9afbced5`，后者修了 3 处 `.work/**` 引用）⇒ `check-knowledge-refs` 假红 | ✅已修 | `git apply -R` 只撤自己的 ledger 派生增量 → `merge --ff-only master` → 重生 ledger（**未用** checkout/restore/stash/reset） | 9 门控全 rc=0；`git diff --stat` = 2 文件（+91/−5） |
| F6 `tests/case-ledger.tsv` 超出「只改 `12-misc` + 片段 + 任务书」的字面范围 | ⏸披露（不可省） | 由 `check_case_ledger.py --write` 重生成（派生清单；+6 行、1 行点号改） | 增量逐行核：只含本任务新增/改动的 7 行，无他册改动 |
| F7 chipyard sim md5 与 `002` 记录不同（`079ae015…` vs `4e2228ad…`）——被后续任务重建 | ✅已核 | 不重建；用 `002` 的 9 点探针复核行为 | 该 sim `P1..P8` 全 match（粒度三点绿），仅 `P9` 与 spec 不符（＝点 6 GAP） |
| F8 并发写者 `m16-gem5-005` 正在重链 `gem5.opt`（737 MB → 41 MB 中间态）⇒ 三平台重跑被 writer-guard 拒（rc=75） | ✅已处置（重试 1 次记录） | 等构建结束（`BUILD_EXIT=0`）再重跑；期间不 `--allow-concurrent` 读移动中的二进制；脚本加「运行前后二进制 md5 不变」守卫 | 构建后 `run.sh` 默认 27 项 + `--inject` 12 项全 PASS；`bin.stable_during_run` PASS |

未修 finding：无（F1/F6 分别为待裁定与已披露，非缺陷）。

### 第 1 轮 reviewer 验收（2026-11-15，独立重跑）—— **判决：Accepted**

**独立推导（点 17–21，非抄完成区）**：按 `spec/SimRISC-12 §1`「保留机制」+ `contract-isa §14.2`（保留键 = 精确地址 + 访问宽度；清除事件仅「另一 hart 同址同宽 store / 本 hart 另一条 lr / 异常或中断进入 / sc 自身成败」）逐点推 ⇒ 17=0、18=0、19=0、20=1、21=1；手算大端拍 `5AAA456789ABCDEF` / `5AADBEEF89ABCDEF` / `5A23456789ABCDEF` / `1122334455667788` / `5A1E2D3C4B5A6978` 与 `.S` 内联期望逐条相等；五点期望全是内联常量 + 独立手算表，**无一处取平台输出**。

**三平台实测（我跑，同一 ELF）**：链例逐点三平台完全相同 `17:0 18:0 19:0 20:1 21:1`、168 B `cmp` 逐字节相同、`points.*.oracle` 3/3 PASS、故障例 rc 248/248/248；引擎 md5：qemu 构建树 `725c5da7…`、gem5 `a1dd0e4a…`、chipyard `079ae015…`、bootrom `51430087…`，运行前后不变（`bin.stable_during_run` PASS）。

**门控（我跑）**：`make check-inst-asm` rc=0，`265 id / 901 镜像 / 链例264 + 故障例637`，检查点**现场求和 4137**（`scan_source` 独立同值 4137）；master 基线用 `git archive` 现场扫 = 265/901/**4132** ⇒ id ±0、镜像 ±0、检查点 +5 成立；`check-tests-index` / `validate-vectors` / `check-case-ledger` / `check-no-residue` / `check-knowledge-refs` 五项 rc=0。

**注入（我自设计 2 路，`cp`+md5 还原）**：A 点19 期望 0→1 ⇒ 三平台同点 `19/19/19`；B 删点20 第二条 `lr`（语义反例，非改常量）⇒ 三平台 `20/20/20`；还原 md5 回 `dcf47d6f…` == HEAD blob、`git status -uall` 0 行、回绿 `0/0/0`。engineer 的一键脚本 `--inject` 我重跑 rc=0（12/12 PASS）。

**改前对照**：chipyard 我独立复现 —— 同 ELF 在改前 sim（`ac35dffb…`）上 rc=**17**、gran 探针 `1 1 1 1 1`。qemu 改前二进制 `b34ed7f9…` 已被主会话 01:37 前的 `install-host` 刷新（master `f6a04472`：安装根与构建树逐字节一致）、盘上无副本 ⇒ **我不可重跑**；采信三条互相独立的记录：① 运行期证据里 engineer 的原始 `pre_qemu.log`（01:32:43，writer-guard 记 `md5=b34ed7f9…`、rc=17）；② `ISS-373` 01:26 现场（安装根落后、037 改用构建树）；③ `m13-qemu-014` reviewer 独立记录（改前探针 `1 1 1 1 0 1 0 0`、P1 同字异址红）。

**重跑红 4 项（环境归因，非交付物缺陷）**：一键脚本默认模式我跑 rc=**1**（23 PASS / 4 FAIL）：`bin.qemu.pre_post_differ`、`pre.qemu.suite_nonzero`、`pre.qemu.rc_point17`、`pre.qemu.gran_points_red` —— 根因 = `QEMU_PRE` 默认锚**共享安装根**、现与构建树同 md5（`725c5da7…`），改前二进制不可得；其余 23 项（含 `pre.chipyard.*`、四路径 exc、6 门控、`check-inst-asm` 265/901）我重跑全 PASS。**未以重试掩盖**：`b34ed7f9` 无副本且禁重建，物理上不可回绿。

**点 6 GAP（重点复核）**：我实测四路径 `chipyard 1 1 1 1 / qemu 1 1 1 0 / gem5 0 0 0 0`（spec 全 1）⇒ **四条路径无一条三平台一致**，排除法取不到任何点；写 1 ⇒ gem5（+qemu 的 CFXTRAP）恒红直接挡 L2，写 0 或写平台值 = 以实现反推（任务书明禁）⇒ **GAP 判定成立**；「先修 gem5/qemu 再补点 22」的建议合理。

**约束核验**：独立 worktree + 分支、未提交（commit 归 architect）、未跑 `install-host` / `check-modules` / `build-*`、未动主工作树、注入只用 `cp`+md5（全程未用 checkout/restore/stash/reset）、改动面 = 4 文件（`case-ledger.tsv` 7 行为 `--write` 派生、已披露）、完成区 12 行、本记录 ≤40 行、完成区与本记录无绝对运行期路径。

**finding（均非阻断）**：F1 一键脚本 `QEMU_PRE` 锚共享安装根 + INFO 仍标「改前版本」⇒ 现恒红，建议改指证据目录固定副本，或「不可得 ⇒ SKIP + 引原始日志 md5」；F2 `merge_fragments.py` 仍 glob `*.inst.yaml`，与 master 已改的 `.inst.fragment`（§5.3）不一致 ⇒ 片段会被静默漏合并，请 architect 同笔补改；F3 任务书验收 3 的「264/897」是旧基线（现 265/901，±0 结论不变）；F4 「异常/中断进入清标记」缺口未入 `issues.yaml`（ISS-435 只覆盖粒度）⇒ 请主会话登记；F5 任务书硬约束第 5 行含临时目录绝对路径（architect 立册文本，文档级）。

## 完成区

**测试结果**：三平台 2/2 镜像全绿；点 17–21 实测 `0 0 0 1 1`（与 spec 手算一致，三平台逐字节相同 168 B）；门控 6/6 rc=0；证据脚本默认 27 项 + `--inject` 12 项全 PASS。
**修改文件**：`tests/inst/12-misc/sc.b.nn_orrr_rd.S`（点 17–21、故障例 17→22、头部计数/GAP）、`tests/case-ledger.tsv`（`--write` 重生成：+6/−1，含故障例点号 17→22）、`tests/inst/.fragments/m13-testcases-037.migration.md`（无 `.inst.yaml` 片段：本任务无清单增量）、本任务书。
**验收结果**（真实输出）：
- **三件二进制**（不重建）：qemu `725c5da788cf4ca7ceba569221f9f1f6`（**构建树**，含 `m13-qemu-014` 修复；安装根 `b34ed7f9…` 是改前旧版，全程未用）；gem5 `a1dd0e4a0b073c7b68205cb244193fec`（共享构建产物；任务期间由 `m16-gem5-005` 从 `6e436d1b…` 重建——重建前早期证据同结论，重建后全量复跑）；chipyard Tiny sim `079ae01569e5fbf9fa9944bd6aee89cd`（被后续任务重建、非 `002` 的 `4e2228ad…`；用 `002` 的 9 点探针复核含修复：P1–P8 全 match）。bootrom `514300876ea66ec108396334f3ef2b0f`。
- **三平台逐字节**（同一 ELF）：chipyard/qemu/gem5 链例 rc 全 0、字节流逐字节相同（21 点 × 8 B = 168 B）；故障例 rc 248 = `0xF8`。逐点实测 `0,1,0,0,1,1,1,1,0,0,0,0,0,0,1,0,0,0,0,1,1`（点 17/18/19=0、20/21=1）。
- **改前对照**：同一 ELF 在改前 qemu（`b34ed7f9…`）/改前 chipyard（`ac35dffb…`）上首红点 = 17（rc=17）；record-only 复刻探针逐点 `1 1 1 1 1`（spec `0 0 0 1 1`）⇒ 点 17/18/19 改前必红。
- **门控**：`check-inst-asm` **265 id / 901 镜像 / 链例 264 + 故障例 637**（id ±0、镜像 ±0、**检查点 +5**：链检查点 4132 → 4137，来源 = 追加 5 个链例点）；`check-tests-index`/`validate-vectors`/`check-case-ledger`/`check-no-residue`/`check-knowledge-refs` rc=0。
- **注入 2 路**（`cp`+md5 还原）：点 17 期望 0→1 ⇒ 三平台同点红（17/17/17）；点 20 期望 1→0 ⇒ 三平台同点红（20/20/20）；还原 md5 一致、回绿。
**新发现/坑**：① 保留粒度无独立 opcode 身份 ⇒ 新建 `.S` 会撞「一 stem 一 `.S`」+ 载体↔索引双向断言，只能挂既有 `sc.b.nn_orrr_rd` 链例尾。② 点 6「异常进入」链例可构造但三平台分歧（MALIGN/CFXMEM/ILLI = `1/1/0`、CFXTRAP = `1/0/0`，spec 全 1）⇒ 不写期望。③ 安装根 qemu 是改前版 ⇒ 原样 `make check-inst-asm` 在本向量点 17 红（900/901）；同门控体换 `--qemu` 构建树即 901/901。④ `check-case-ledger` 是派生清单 ⇒ 追用例后必须 `--write`。⑤ L1 `check-tests-index` 拒绝 `tests/inst/` 下任何 `*.yaml`，与 `MIGRATION §5.3` 的 `.fragments/<任务>.inst.yaml` 协议冲突（本任务无清单增量，故不出该片段）。⑥ 基线推进：worktree 由 `f4b2de26` ff 到 master `9afbced5`（后者修了 3 处具体运行期路径引用），全部证据在 `9afbced5` 上重跑（未用 checkout/restore/stash/reset）。
**遗留问题**：点 6（异常或中断进入清标记）未入向量——需先修 gem5（四路径全不清）与 qemu 的 CFXTRAP 路径，建议立修复任务后补 1 点（点 22、故障例顺延 23）；多 hart 同址同宽 store 清标记单 hart 不可测（GAP）；安装根 qemu 待主会话 `install-host` 后复跑原样门控。无未修 finding。
