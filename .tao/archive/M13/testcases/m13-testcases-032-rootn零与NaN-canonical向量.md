# m13-testcases-032: `rootn(±0,2)=+0`、结果 NaN canonical、quiet compare sNaN 的 `NV` —— 向量与三平台实测

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-007`（口径定稿）+ `m13-qemu-009` + `m12-chipyard-030` + `m13-gem5-011`（期望落定后实测三平台）
**可并行分片**：否（共享 `tests/inst/fp/`）
**状态**：已验证

**预估**：3–4 h

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

1. **R1**：`rootn(±0,2)` = IEEE `+0`（§9.2.1；NOTE：`rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 canonical qNaN（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。
3. **D1**（2026-11-12）：「改为置 NV（跟 IEEE）」——quiet compare（`ftqcmp`/`foqcmp`）遇 sNaN 置 `NV`，只含 qNaN 不置。

审计来源：`docs/TestReports/M13-FP-IEEE对齐审计.md` §D1 / §D2 / §D3（含 P4/P6/P8 行为模式表）。

## 背景

- 既有向量**没有** `rootn(±0,2)` 例（`tests/inst/fp/divrem.yaml` 的 `foroot`/`ftroot` 组无 ±0 源）。
- 既有向量**部分 pin 住 QEMU 的 NaN 传播**：如 `divrem.yaml` 的 `forem qNaN rem 2.0 ⇒ rd5 = 0x7FF8_0000_0000_0123`（payload 传播）——与 R2 冲突，须改 canonical。
- 既有 quiet+sNaN 四例（`arith.yaml`）的「左/右」两方向**机器状态相同**（`ISS-407`：`set.w` 为 wyde 部分写、写序可交换，NaN 实际都在同一操作数）⇒ 需补**真实右操作数**独立用例。

## 范围（只改 `tests/`）

1. **R1 向量**（`tests/inst/fp/divrem.yaml`）：`foroot`/`ftroot` 各补 `−0` 输入例 ≥1、`+0` 对照 ≥1：
   - 期望 `+0`（ft 侧低 32 位 `0x0000_0000`、符号 0；高 32 位按该例装载值，逐例在 `notes` 写清装载与读回路径）
   - `rf0[4:0] = 0`（`rd6` 只含复位 qNaN 位，即 `0x7FF8_00007FC00000`）
2. **R2 向量**（`arith.yaml` / `scaleb.yaml` / `convert.yaml` / `divrem.yaml`）——「结果 qNaN ⇒ canonical」至少覆盖：
   - 算术：`ftadd`/`foadd`（或 sub/mul/div）带 payload **且负号** qNaN 输入 ⇒ `0x7FC0_0000` / `0x7FF8_0000_0000_0000`（符号清 0）
   - scaleB：`ftsclb(qNaN 带 payload, n)` ⇒ canonical
   - 转换：`fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`；`ft2fo(qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`
   - 取余：既有 `forem` qNaN 传播例改 canonical
   - **排除项对照（不得改）**：`ft2ft`/`fo2fo` 复制带 payload NaN ⇒ 位型原样；`foscmp(qNaN)` ⇒ `0x7F80_0001` + `NV=1`
3. **D1 向量**（`arith.yaml`）：quiet compare 遇 sNaN 的**左/右两个真实方向**各有独立用例（`ft`/`fo` 各 ≥2，共 ≥4），期望 `NV=1`、结果 canonical qNaN；`qNaN` 对照 `NV=0`。构造要求：两操作数须落在**不同寄存器**、经**非重叠**写序装入（避免 `ISS-407` 的「两例机器状态相同」），并在 `notes` 写明两侧实际值。
4. **全量清扫**：扫描 `tests/inst/fp/*.yaml` 中结果为**非 canonical qNaN**（`rd5`/`rf` 期望 payload≠0 或符号 1）的项 ⇒ 逐条改 canonical；完成区给出 `grep` 命令与命中数（现场值，不写死）。
5. **索引同步**：`tests/case-ledger.tsv` 重生成（`--write`）；`tests/inst/inventory.md` 若门控/覆盖表要求则同步；每文件检查点 ≤127、点号连续。
6. **三平台实测**（期望为准，逐点记录三方位型）：
   - QEMU：`make check-inst`（Vast 全量 + Tiny 子集）
   - gem5：`tools/gem5/check_b7.py --vectors`（指令路径探针 / `b7_ref` 差分）
   - chipyard：`tools/chipyard/fp_unit/unit_run.py` + `tools/chipyard/fp_sweep.py`
   - 某平台未重建/未合入 ⇒ 标 **BLOCKED（原因 + 替代证据）**，禁写「推定一致」

**非范围**：不改实现（`components/**`）、不改 `tools/**` 模型（`fp_ref.py`/`b7_ref.py` 归实现册）、不改 spec/合约。

## 前置（`m13-testcases-021` 已定位根因，2026-11-14）

- 既有唯一红 `divrem.yaml[23]` 的根因已查明：该用例是「`forem` 收到 qNaN、余数 2.0」时**期望 NaN payload 传播**，而 `spec/SimRISC-07 §1.4` 规定 NaN 结果**一律 canonical**；三平台实现均按 canonical ⇒ **是 YAML 旧口径错，不是实现缺陷**。本任务应按 spec 改该 YAML 期望（或按 `030` 口径迁到 `.S`）。
- 另发现一处 **spec 内部不一致**：`spec/SimRISC-07 §2.1` 余数表注「符号随 rfHC」对**非零结果**不成立（三平台实测一致）。属 spec 措辞问题，需用户裁定后另行修订；本任务**不改 spec**。

## 验收标准（可执行、可失败）

1. 新增/修改用例数、每文件检查点号区间、`grep` 命中数：**全部现场统计**并贴出处。
2. `make check-inst` rc=0（Vast/Tiny 计数取现场）；整数 273 例 emit md5 与基线一致（FP 改动不应触及，现场核对）。
3. **三平台逐点一致**：每条新/改语义点给出「QEMU / gem5 / chipyard」三方位型 + 与 spec 期望比对结论；不一致项如实记红并登记 issue（**不得放宽期望**）。
4. **可达 FAIL 注入**：把一条 canonical 期望改回带 payload（如 `0x7FC0_0001`）⇒ 对应用例红；`cp`+md5+`touch` 还原 ⇒ 回绿；再任选一条 root `−0` 期望改回 `0x8000…` ⇒ 红的必须是同一条。
5. 期望派生声明：每条新期望的 `notes` 写明 spec 引用（`SimRISC-07 §1.4` / `§2.2` / `§4` + IEEE 条文）与反算方式（`tools/chipyard/fp_ref.py` 精确 oracle 或手写有理数推导），**不得**从 QEMU/gem5/RTL 输出抄期望。
6. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 说明

- `ft` 的 `set.w` 为 wyde 部分写、写序可交换（`ISS-407` 根因）⇒ 构造「sNaN 在右」须换寄存器或用整字宽装载，并在 `notes` 给出实测寄存器值佐证。
- 若 `m13-gem5-011` 的转换 canonical 项（其「待裁定 Q1」）另立册，则 `fo2ft`/`ft2fo` 的 gem5 侧比对标 BLOCKED，其余两点照常收口。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。
9. 沿用 `012` 系列既有 hmon 自装 workaround（若仍需要，按现场状态说明）。

## 待裁定（交主会话，2026-11-14）

**Q1：`make check-inst` 的 Tiny 子集被并行在途批次阻塞，是否以「Vast 段 0 failed + 本任务 4 册不进 Tiny 子集」的替代证据收口？**

- **现场**：`make check-inst` **Vast 段通过**（`1157 total / 1152 passed / 0 failed / 5 deferred`，红集**空**——本任务目标达成）；**Tiny 段 44/44 红**，全部是 `base/mem-rd.yaml` 等 `profiles: [tiny]` 的既有 load/store 例，错误为
  `qemu-system-dadao: dadao: -bios image 'tools/testcases/lib/trampoline.bin' is 56 bytes; the Machine-v5-Tiny -bios path accepts only the fixed 65536-byte BootROM firmware`。
- **根因（非本任务）**：共享**安装根**的 `qemu-system-dadao`（md5 `b34ed7f9…`，与构建树同 md5）已含**在途** `m13-qemu-011`（`-bios` 收紧为 64 KiB 固定固件）的行为，而 `Makefile` 的 Tiny 段仍传 56 B trampoline、44 例 oracle 迁移归 `m13-testcases-034`；两任务任务书明示「同批合入」。**同一失败在主工作树/master 上同样复现**（与本分支无关）。
- **替代证据**：① 本任务 4 册 `profiles:` 条目数 = 0（现场 `grep -c profiles:`）⇒ 一例都不进 Tiny 子集；② Vast 段（含全部 fp 向量）0 failed；③ `run.sh` 对已知 Tiny 迁移错误打印 `[BLOCKED]` 并给具名复现（直接跑 `mem-rd.yaml[25]`），**其它任何红仍判 FAIL**。
- **建议**：按 BLOCKED 收口（不写「推定一致」），Tiny 回绿随 `m13-qemu-011` + `m13-testcases-034` 同批验收；本任务不改 `Makefile`/QEMU。
- 自决的临时处置：已完成（上述替代证据 + `[BLOCKED]` 分支）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14，自主逐行审查）

审查范围：4 册 YAML 全部新增/改动条目、`oracle.py`（spec 条款表 + sequence 解释器）、
`sweep.py`、`gem5_probe.py`、`run.sh` 全脚本、`case-ledger.tsv` 差异、`.fragments/` 两文件。

- **Spec-first 核验**：每条新期望的 `notes` 均写 spec 条款（§1.4/§2.1/§2.2/§4 + IEEE
  §6.2.3/§6.3/§7.2/§9.2.1/§5.11）与推导方式（canonical 常量 / 手写零符号）；无一条
  抄自 QEMU/gem5/RTL 输出。
- **编码核验**：新增用例的 `encoding.word` 与 `sequence` 全部经 `llvm-mc --show-encoding`
  双向往返核对（`ld.o`/`st.o`/`st.t`/`rf2rd`/`set.w`/被测指令；含 `rf7`/`rf9`/`rd13`/`rd14`
  字段位置），并与 `oracle.py` 的独立解码一致。
- **防「同源自比」**：`oracle.py` 不 import `fp_ref`/`b7_ref`/实现，只借
  `gen_decode_table` 的字段**位置**；三平台字节流是同镜像实测（QEMU/chipyard/gem5），
  期望来自 spec 条款表。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `oracle.py` 初版 `run_case` 漏掉被测指令前的 `machine.step(w)` ⇒ root/转换例被误算 | ✅已修 | 补 `machine.step(w)`；重跑 | 27 例全 ok（29 值逐例打印） |
| F2 FMA 的目的字段是 `rfha`（非 `rfhb`），源字段整体前移 ⇒ 目的/源错位 | ✅已修 | 改为按 `entry.fields` 的 `role=dst/src` 取字段 | `arith[12]` fofma 复算 == YAML |
| F3 转换类目的格式 ≠ 源格式（`fo2ft`→ft、`ft2fo`→fo）⇒ canonical 常量与写宽用错 | ✅已修 | 新增 `dst_fmt`，结果/写宽用它 | `convert[15]/[16]` ok；三平台一致 |
| F4 `st.t` 半字写落在 chipyard 未初始化 RAM 上 ⇒ 另半字读到垃圾 `0xC257BF55`（同镜像 QEMU 为 0） | ✅已修 | 新 `fo2ft` 例改 `st.o` 整 8 字节回读（notes 写明避开该坑） | `convert.yaml[15]` chipyard/QEMU/gem5 三绿 |
| F5 `select()` 把 `rd` 组源（scaleb 指数）当浮点位型 ⇒ `0xFFFF…` 被误判 qNaN | ✅已修 | NaN 判定只对 `bank == rf` 的源 | targets 27（不再误选非 NaN 的 sclb 例） |
| F6 `sweep.py` 初版漏 `ftrnd`/`fornd`（§2.3 也规定 canonical 化） | ✅已修 | 加入扫描族；重跑 | `scanned=124 noncanonical=0` |
| F7 run.sh 的 check-inst 判据对「已知 Tiny 迁移阻塞」无辨识能力 | ✅已修 | 加 `[BLOCKED]` 分支：Vast 0 failed + 本任务 4 册 `profiles:`=0 + 直接复现具名错误，三者同时成立才放行；其它红仍 FAIL | 见「待裁定 Q1」与完成区 |
| F8 gem5 探针与 YAML 的 f32 读回布局差 32 位（`st.t`） | ✅已修 | 按每例 `align_shift`（0/32）对齐 blob；比较仍用未移位值 | 三方 432 B `cmp` 相等 |
| F9 注入窗口与在跑的 `check-inst` 可能重叠（读取注入中的 YAML） | ✅已修 | 先终止自己排队的 check-inst，注入/还原完成后再单独跑 | 注入还原 md5 `7bf9c9d2…` 相等；随后 Vast 0 failed |

判决：finding 全部已修；除「Tiny 段被并行批次阻塞」外无未决项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14，worktree @ `db001ec3`，`git status -uall` 0 行）

判决：**Needs Revision** —— 唯一阻断是证据脚本 §2b 在交付提交后不可复现（`run.sh` rc=1）；其余验收项 reviewer 亲跑全部通过。

**重跑记录（reviewer 亲跑，不采信完成区）**

- `bash .work/evidence/<任务ID>/run.sh --inject` → `== summary: PASS=42 FAIL=1 (checks=43) ==`、**rc=1**；唯一 FAIL：
  `[FAIL] 改前 divrem.yaml[23] 判红（rc≠0） | expected=nonzero actual=0`。根因：run.sh L82 `git show HEAD:tests/inst/fp/divrem.yaml`
  —— 交付提交后 HEAD 已是**改后**文件，`[23]` 不再是旧 payload pin（旧值 `0x7FF8000000000123`）而是新的 sNaN 例 ⇒ QEMU rc=0。
  完成区「PASS=43 FAIL=0、rc=0」在交付提交后不可复现。
- 该步**事实**本身成立（reviewer 用 `git show b46313e0:` 的改前文件单跑）：`Result: FAIL`、rc=1；改后 `[26]/[27]` PASS。
  修法：改取「最后改动该文件的提交之父」（`git rev-list -1 HEAD -- tests/inst/fp/divrem.yaml` 后取 `^`），或按 `m13-qemu-012`
  惯例钉一份改前副本（该任务已注明 `git show HEAD:` 交付后自我指涉的同名教训）；修后重跑 `run.sh --inject` 至 rc=0。
- 其余现场：oracle `targets=27 mismatches=0`、`sweep scanned=124 noncanonical=0`、QEMU 全册 `114/114`、chipyard `27/27`、
  gem5 `27/27`、三方拼接 `432 B` `cmp` 全等、门控 `check-tests-index 485` / `check-case-ledger 2200` /
  `validate_vectors 156/156（723 例）` / `check-spec-cite-targets` 全 rc=0、273 例 md5 `2d4d94651346ef673c5a855e024c1489`、
  其两路注入红 → `cp`+md5 `7bf9c9d2…` 还原 → 回绿、4 册 md5 与开工一致。
- **独立复算**：reviewer 自写 `recheck.py`（字段取 `contracts/opcodes.yaml`，不 import `oracle.py`/`sweep.py`/`fp_ref`/`b7_ref`）
  对 18 例（16 新 + 2 改）**MISMATCH=0**；反例（`scaleb[14]` canonical→`0x7FF8000000000123`，注入在临时树）⇒ `MISMATCH=1` rc=1。
  被测指令 + `ld.o`/`st.o`/`rf2rd` 共 15 条经 `llvm-mc --show-encoding` 往返核对，与 YAML `encoding.word` 全等。
- **check-inst 两段归因**：Vast `1157 total / 1152 passed / 0 failed / 5 deferred`（红集空）；Tiny `44 total / 44 failed`，
  失败仅 `aip-si`/`ctrl-br`/`ctrl-call`/`ctrl-jump`/`mem-ra`/`mem-rb`/`mem-rd`，本任务 4 册 `profiles:` 现场 `grep -c` 合计 0
  ⇒ 无一例进 Tiny；`-bios … is 56 bytes` 具名错误在 `mem-rd[25]`、`ctrl-br[3]`、`aip-si[1]` 复现，**主工作树 master 同样复现**
  （前后 `git status` 0 行）⇒ BLOCKED 非本任务引入，按 Q1 同批复验，不计入本判决。
- **三平台（server208，reviewer 自跑）**：`sync_node_artifacts.sh gxt@server208` → `PASS / verify: OK`；节点 checkout `db001ec3`、
  4 册 md5 与主控机逐件相同。首轮 chipyard `rc=127`（节点缺 `libdramsim.so`/`libriscv.so`），补 rsync 后 md5 `3f7960fd…`/`398cfd3e…`
  与主控机一致；复跑 `SKIP_CHECK_INST=1 run.sh` → `PASS=26 FAIL=1`（唯一 FAIL 同 §2b），三平台 `27/27`、`432 B` 逐字节相等。
- **独立注入（自设计，与 engineer 两路不同）**：`convert.yaml[15]` `rd5`→`0x000000007FC00001` ⇒ QEMU `Result: FAIL` rc=1、
  我方复算 `MISMATCH=1`；`cp`+md5 `9ffc61cd…` 还原 ⇒ QEMU rc=0、`git status -uall` 0 行。

**约束核验**：diff 仅 8 文件（4 册 + `case-ledger.tsv` + 2 片段 + 任务书），根清单/`MIGRATION.md`/`README.md`/宏层/驱动器/
`tools/`/`components/`/`spec/` 未动；完成区 13 行 ≤30、无运行期绝对路径；未提交 git、未改主工作树、未跑 `install-host`；片段为 `[]`（无新载体）。

**文档级 finding（不阻断）**：3 条 notes 与 migration 片段把「单精只写低 32」标为 `SimRISC-07 §1.4`，实为 **§1.3**
（§1.4=异常与标志，spec L340 自注「见 §1.3」）⇒ 记 finding，随 D1 文档收尾订正。

**判决：Needs Revision** —— 指名失败：`.work/evidence/<任务ID>/run.sh` §2b 依赖 `HEAD`、交付提交后 rc=1，验收标准 6（`run.sh rc=0`）
不满足；验收标准 1–5 在我的重跑下全部成立。修 §2b 后重跑即可复验；Tiny BLOCKED 按 Q1 同批复验。

### 第 2 轮 reviewer 验收（2026-11-14，worktree @ `e1e08ae5`，`git status -uall` 0 行）

判决：**Accepted** —— 上轮唯一阻断（§2b 自我指涉）已修；重跑 rc=0，可达 FAIL、改前正证语义、notes-only 改动均经我独立验证。

**重跑（reviewer 亲跑）**

- `bash .work/evidence/<任务ID>/run.sh --inject` → `== summary: PASS=46 FAIL=0 (checks=46) ==`、**rc=0**；`run.sh` → `== summary: PASS=31 FAIL=0 (checks=31) ==`、**rc=0**。
- 两轮 `== sim 重试次数（并行重建竞态）：0 ==`；Vast `1157 total / 1152 passed / 0 failed / 5 deferred`（红集空）、Tiny `44 total / 44 failed` → `[BLOCKED]`（同批，不计入判决）；三方拼接 `432 B` 全等、273 md5 `2d4d94651346ef673c5a855e024c1489`、注入两路还原 md5 `19ba8214…` 回绿、4 册 md5 与开工一致。

**§2b 可达 FAIL（我注入，非换了个恒真写法）**

- 屏蔽回退支（`BASELINE_COMMIT=b46313e0`→`0000000`，先 `cp`+md5 `613027fb692ba6452073aa6b8b41fd02` 备份）→ 重跑 **rc=1**、`PASS=29 FAIL=2`：
  `[FAIL] 2b：改前副本 [23] 期望 == 旧 payload pin | expected=0x7FF8000000000123 actual=0x7FF8000000000000`、
  `[FAIL] 2b：定位到含旧 pin 的改前版本 | expected=y actual=n`（其余 29 项仍绿）；`cp`+md5 还原（`613027fb…` 相等）→ 重跑 rc=0 回绿。
- 观察（不阻断）：两候选都未命中时改前副本已被前一轮 `rm -f` 清空 ⇒ 第 3 条 ck 会以 `Result: ERROR` 假性通过；因前两条 ck 已判红、整体 rc=1，不构成凑绿，建议补 `[ -s 文件 ]` 守卫。

**改前正证语义**：日志 `改前副本取自 b46313e0`，落盘副本 32 例、`[23] = forem_orrr_rf rd5=0x7FF8000000000123`；我独立跑该文件 case23 → `Result: FAIL`、**rc=1**（非只看断言 PASS）。

**`sim_run()` 不掩盖真红**：截取原脚本前 68 行 + 驱动，`SIM` 指向不存在文件 → 打印 `重试 1/2`、`重试 2/2`、`SIM_RETRY=2`、`sim_run rc=127` ⇒ 判据 `JUDGE=RED`（不静默变绿）。

**notes-only 改动**：`git diff db001ec3..e1e08ae5 -- tests/` 共 8 行（4 对），全部为 notes/fragment 文本；命中 `expected_state|encoding|word|sequence|rd5|rd6` 的改动行 **0**；`tests/case-ledger.tsv` 不在 diff、md5 `f67b5632…` 未变；`§1.4 单精` 残留 **0**、订正 4 处（arith×1、divrem×2、片段×1），canonical 的 `§1.4` 保留；我的独立复算 18 例仍 `MISMATCH=0`。

**门控/约束**：`check-tests-index 485`、`check-case-ledger 2200`、`validate_vectors 156/156（723 例）`、`check-spec-cite-targets` 全 rc=0、273 例 md5 不变；第 1 轮审阅记录 31 行未被改动（特征行齐全）；完成区 14 行 ≤30；未提交 git、未改主工作树、未跑 `install-host`/`check-modules`。

**判决：Accepted** —— 上轮指名失败已修复且其可失败性经我注入证明；Tiny 段 BLOCKED 仍按 Q1 同批复验，不计入本判决。

## 完成区

**测试结果**：`bash .work/evidence/<任务ID>/run.sh --inject` → `PASS=46 FAIL=0`、rc=0；`bash .work/evidence/<任务ID>/run.sh` → `PASS=31 FAIL=0`、rc=0（两轮均含 check-inst 段：Vast PASS、Tiny [BLOCKED]；sim 重建竞态重试 0 次）。失败原因：无。
**修改文件**（与 `git status -uall` 逐项一致）：`tests/inst/fp/divrem.yaml`、`tests/inst/fp/arith.yaml`、`tests/inst/fp/scaleb.yaml`、`tests/inst/fp/convert.yaml`、`tests/case-ledger.tsv`、`tests/inst/.fragments/m13-testcases-032.{inst.yaml,migration.md}`（新增）+ 本任务书；无其它改动/残留。
**验收结果**：
1. **新增 16 例 / 改 2 例**（现场统计：divrem +4、arith +8、scaleb +2、convert +2；改 = divrem[26] 补 rd5 canonical、[27] 旧 payload 传播→canonical）。四册现场例数 36/46/15/17；无 `.S` 改动（不涉点号）。
2. **改前对照**：`BASE_F^`（最后改动 `tests/inst/fp/divrem.yaml` 的提交之父，= 基线 `b46313e0`）版 `divrem.yaml[23]`（`forem qNaN rem 2.0`，期望 `0x7FF8_0000_0000_0123`）在当前 QEMU 上 `Result: FAIL`（rc=1）⇒ 旧红 pin 可复现；改后 **Vast 段 `1157 total / 1152 passed / 0 failed / 5 deferred`（红集空）**。Tiny 段 `[BLOCKED]`（QEMU `-bios` 收紧为 64 KiB、44 例迁移归 `034`，见待裁定 Q1）。
3. **门控**：`check-tests-index` rc=0（485 条）、`check-case-ledger` rc=0（2200 条）、`validate_vectors` rc=0（156/156、723 例）、`check-spec-cite-targets` rc=0、`generate_isa_vectors --check cond-assign.yaml` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变。
4. **独立复算**：自写 `oracle.py`（spec 条款表 + `sequence` 解释器，不 import `fp_ref`/`b7_ref`/实现）27 例 0 差；`sweep.py` 全量 `scanned=124 noncanonical=0`。
5. **三平台**：QEMU 全册 114/114；chipyard 27/27（含 `rd13`/`rd14` 操作数回读）；gem5 B7 探针 27/27（另 `check_b7` rc=0：4098 向量 / `oracle mismatch=0`）；**同镜像拼接字节流 432 B（27×16）三平台 `cmp` 逐字节相等**。
6. **注入 2 路**（canonical→payload、root `−0`→`0x8000…`）：oracle / 清扫 / QEMU / chipyard 全判红且命中同一条；`cp`+md5 还原（`7bf9c9d2…`）回绿。
**新发现/坑**：① 共享安装根 QEMU（md5 `b34ed7f9…`）已含在途 `m13-qemu-011` 的 `-bios` 收紧 ⇒ Tiny 44 例全红（56 B trampoline 被具名拒绝）；本任务 4 册无一例进 Tiny 子集、主工作树同样复现 ⇒ BLOCKED 非本任务缺陷；② chipyard `st.t` 半字写落在未初始化 RAM 会漏出垃圾（同镜像 QEMU 为 0）⇒ f32 读回改用 `st.o` 整字写；③ `spec/SimRISC-07 §2.1` 余数符号措辞已由 `c35d7146` 按 IEEE 修正（任务书「另发现」已消解）。
**遗留问题**：① Tiny 子集回绿随 `m13-qemu-011` + `m13-testcases-034` 同批（本任务不碰 `Makefile`/QEMU）；② `tests/inst/fp/arith.yaml` 头部「quiet 不置」是 `m13-qemu-004` 之前的旧表述（现为「仅 sNaN 置」），本任务按最小修改未改，建议随 D1 文档收尾补一句。

**返工（reviewer 第 1 轮，2026-11-14）**：① `run.sh` §2b 改取「最后改动该文件的提交之父」（`BASE_F=$(git rev-list -1 HEAD -- …)` 的 `^`），返工提交也改该文件时回退基线 commit `b46313e0`，并断言改前副本 `[23]` 期望 == `0x7FF8000000000123`（可达 FAIL，不再自我指涉）；② 3 条 `notes` + migration 片段的「单精只写低 32 位」引用 `§1.4`→`§1.3`（期望值/编码未动）；③ 共享 sim 被并行任务重建时 `execve` 会 rc=127，`sim_run()` 加一次带记录的重试（重试后仍失败照常判红）。
重跑（真实）：`run.sh --inject` → `PASS=46 FAIL=0`、rc=0；`run.sh` → `PASS=31 FAIL=0`、rc=0（两轮 `sim 重试次数=0`）。
