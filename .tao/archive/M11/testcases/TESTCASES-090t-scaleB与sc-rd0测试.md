# TESTCASES-090t: scaleB C1 与 sc rd0 测试

**模块**：testcases
**项目里程碑**：M11
**依赖**：`SPEC-181t`、`LLVM-142t`、`QEMU-078t`、`GEM5-005t`
**状态**：已验证

## 用户授权

用户 2026-11-01：scaleB C1 与 `sc rdHB=rd0 ⇒ ILLI` 的测试必须随实现独立调整；不新建 `tests/gem5`，复用现有 `tests/inst`/`tests/arch`/`tset` scope。

用户 2026-11-02 裁定：**扩展本任务**，同时接收 LLVM lit 与 `tools/llvm/llvm-isa-backend-matrix.*` 同步；LLVM-142t 只验实现与定向行为，全局 `check-lit`/`check-isa-coverage` 由本任务关绿。

## 目标

1. **scaleB C1**：
   - 新语法 `ftsclb rf,rf,rd`、`fosclb rf,rf,rd` 的正例；
   - 旧 `rf,rf,rf` 负例；
   - `ldexp`/`scalbn` 的 C/IR 运行期与编码检查；
   - QEMU/gem5/LLVM 结果一致性。
2. **sc rd0**：
   - 12 条 `sc` 的 `rdHB=rd0` 负例，期望 ILLI；
   - 正常 rd 目的正例；
   - QEMU system 与 gem5 FS 对照。
3. **LLVM 测试资产同步**：
   - 更新 `tests/unit/llvm/lit/MC/DADAO/fp-encoding.s`、`tests/unit/llvm/lit/CodeGen/DADAO/fp-ldexp.ll`，以及受影响的 `gen-orrr.s`；
   - 重生成 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}`；
   - `make check-lit` 与 `make check-isa-coverage` 回绿。
4. 只改 `tests/**`、`tools/llvm/llvm-isa-backend-matrix.*` 和测试驱动；不改实现/spec/contracts；不新建平行测试树。
5. 测试任务独立分支；实现补丁不得夹带测试资产。

## 验收

1. `make check-inst-smoke`/targeted 向量真实 rc=0；负例必须 FAIL/ILLI。
2. `make check-lit` 与 `make check-isa-coverage` 真实 rc=0；旧 `rf` 断言/矩阵必须已更新。
3. `make check-tests-index`、`make check-case-ledger` rc=0。
4. QEMU system 与 gem5 FS 对应 case 结果一致；差异必须定位，不比较时序。
5. 证据 `运行期证据（已清理，未归档）`；完成区 ≤30 行，状态待验收。

## 完成区

**测试结果**：gem5 FS 段补齐：`运行期证据脚本（已清理，未归档）` rc=0（checks=46 failures=0）——独立 oracle 280/280（tiny+node 各自 `@ENTRY` token 解析）、targeted QEMU `fp/scaleb.yaml` 12/12 与 `atomics/sc-rd0.yaml` 14/14、**gem5 FS ↔ QEMU system targeted parity 52 行全 `AGREE_PASS`**（tiny 26 + node 26，case ID/退出码/expected_fault 一致；`GEM5_ONLY_FAIL`/`QEMU_ONLY_FAIL`/`DIFF`=0）、`check-inst-smoke` 90/90、`check-lit` 163/163、`check-isa-coverage` PASS、9 项静态门控全绿、L1 除两个本任务外阻断项外全绿；4 组注入（错期望值 / rdHB≠0 / 删 ledger 行 / parity JSON gem5-only fail）均可达 FAIL→`cp`+md5 还原→回绿（tracked 注入另断言 `git diff` 非空）。QEMU 段前轮证据 `运行期证据（已清理，未归档）` 保留。
**修改文件**：本轮仅新增证据脚本（`运行期临时目录` 不入库）：`运行期证据（已清理，未归档）`；`tests/`、`tools/` 测试资产沿用前轮且本轮**未再改**（`tests/inst/fp/scaleb.yaml`、`tests/inst/atomics/sc-rd0.yaml`、inventory/tests.yaml/case-ledger 等见前轮记录）；本任务书。
**验收结果**：引擎身份现场记录：qemu md5 `6b9eb0a7…`、gem5 md5 `e84ebbaa…`、`configs/dadao/fs.py` md5 `952b78c4…`、gem5 源 `12a4716`。tiny/node 的 scaleB 正例 exit=0；sc 12 条负例 exit=136（ILLI）、2 条正例 exit=0；**同 case ID 上 QEMU 与 gem5 的 status/exit/fault 逐一相同**，不比较时序/日志。
**新发现/坑**：① `build_test_binary._PROFILE` 在 import 期冻结，同进程先 tiny 后 node 会复用 Tiny 二进制（实测 QEMU FAIL/1、gem5 FAIL/125）⇒ 每 `(profile,engine)` 必须子进程隔离（同 `run_parity`→`semantics_gate`）；② 共享 `gem5 组件源树` 被 GEM5-018t 改写（HEAD `12a4716` 含 semihosting 修复），本分支 `components/gem5` 补丁集未含 ⇒ `check-patch-tree` 红（外部阻断）；③ `make check-modules` 会触发 install-host→build-mc 的 LLVM 全量重建（>30 min、磁盘 91%），且与 GEM5-018t 共享安装根 ⇒ 只跑 L2 的 inst 成员 `check-inst-smoke`；④ TESTCASES-091t 后向量用 `@ENTRY+…` token，oracle 须走 `machine_profile.resolve_case`；⑤ 证据脚本须前后核 gem5 二进制 md5，防并发重建造成混跑。
**遗留问题**：① L1 的 `check-patch-tree`（GEM5-018t 共享源漂移）与 `check-knowledge-refs`（本 worktree 其它任务 `运行期临时目录` 悬空引用）仍红，均本任务外、未改；② 未跑 L3 全量 `check-inst`（本轮 = targeted + 结构断言 + L2 smoke）；③ `docs/TestReports/M11-三平台一致矩阵.md` 快照属 GEM5-017t 且早于 091t、未含本任务 2 册；是否重生成快照交主会话（避免改他人任务产物）；④ 前轮 LLVM 遗留项不变。

## 审阅记录

### 第 1 轮 engineer 自审

逐文件审查：
- `fp-encoding.s`：`word=0x44544188` 未变（`rdhd` bits[5:0]=8 与旧 `rf8` 同编码）；OBJ/ASM 同步 `rd8`；两条 `OLD-RF` RUN 用 `%not` + 诊断 `invalid operand`，旧写法若被接受则 `%not` 非零 ⇒ 可达 FAIL（注入 1 实证）。
- `fp-ldexp.ll`：RUN 加 `--implicit-check-not=io2fo/it2ft`（全文件兜底）；三条 sclb 断言 `rf, rf, rd`；i64 加 `CHECK-NOT: ext.so`；注入 2 把断言改回 `rf` ⇒ check-lit rc=2，证可达 FAIL。
- `gen-orrr.s`：仅生成器产出变化（2 例 × 2 行），编码/OBJ 未动；`check-lit-full` 11/11，注入 3 改回旧拼写 ⇒ rc=2。
- `llvm-isa-backend-matrix.{tsv,md}`：重生成后 264 行；独立脚本 strip 行号逐字段比对，非行号差异恰 2 格（`ftsclb/fosclb` 的 `L1_asm`），L1/L2 统计不变；注入 4 改一格 ⇒ check-isa-coverage rc=2。
- `run.sh`：门控取真实 rc；lit 计数/矩阵行数现场解析不写死；无 `tee`；注入一律 cp 备份 + md5 对账（未用 git 还原）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

#### 第 1 轮 architect 提交（WIP）
- 档位：`待验收`（reviewer 未验收）⇒ WIP。
- 提交：`a83a9a7c` `WIP: TESTCASES-090t LLVM 资产同步（QEMU/gem5 阶段待实现）`（7 files, +358/-340）。
- 文件集对账：显式 staging 7 项，与完成区「修改文件」逐项一致（`fp-encoding.s`、`fp-ldexp.ll`、`gen-orrr.s`、`llvm-isa-backend-matrix.{tsv,md}`、本任务书、`milestones.md`）；漏提 0 / 多提 0 / 越界 0；无 `components/`、`spec/`、`contracts/`、QEMU/gem5、`Makefile` 改动；`git status --porcelain -uall` 除本行外干净。

### 第 2 轮 engineer 自审（QEMU 段）

**范围**：逐行审 `tests/inst/fp/scaleb.yaml`、`tests/inst/atomics/sc-rd0.yaml`、`tests/inst/inventory.md`、`tests/inst.yaml`、`tools/qemu/semantics_gate.py`（`CARRIER_DIRS`）、`tests/case-ledger.tsv`（生成物）与证据脚本；实机重跑 `run.sh`。

- 期望值来源：只据 `spec/SimRISC-07 §2.1`（`rfHC × 2^rdHD`，`rdHD∈rd`、`rd0` 为指数 0）、`spec/SimRISC-12`（`sc rdHB` 为结果目的、`=rd0 ⇒ ILLI`；`lr rdHB` 固定 rd0）与 `contracts/opcodes.yaml`（mask/value/fields/rule_refs）；数值用 `math.ldexp`+`ctypes.c_float` 独立重算（`oracle_vectors.py` 140 项），未读 QEMU 实现、未反推。
- 可达 FAIL：三组注入均实跑（错期望值 → scaleb rc=1；rdHB≠0 → sc 用例 rc=1；删 ledger 行 → `check-case-ledger` rc=2），全部 `cp`+`md5sum -c` 还原后回绿；两向量文件为本分支新增（untracked），故注入断言用 md5 变化，另对 tracked `case-ledger.tsv` 断言 `git diff` 非空。
- 脚本纪律：无 `tee`；每检查捕获真实 rc；计数现场统计（12/14/90/241/1995/22 册/1012 例），无写死期望；`trap` 清理注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-1 `lr` 的 rdHB 手写成 5（应固定 rd0），正例实机先 ILLI | ✅已修 | `sc-rd0.yaml` 两条 sequence 的 lr 字 `0x47005004`→`0x47000144` | targeted 14/14；`run.sh` rc=0 |
| F-2 oracle 未校验 lr 字段，F-1 只靠实机才发现 | ✅已修 | oracle 增 `lr.rdhb==0`、`lr.rbhd==sc.rbhd` 检查 | oracle checks=140 failed=0 |
| F-3 rf 诱饵可能恰好同值使断言假绿 | ✅已修 | oracle 增「诱饵指数结果 ≠ 期望」断言 | 12 例全过；错期望值注入 FAIL |
| F-4 非 M1 载体未登记会使 L3/inventory 红 | ✅已修 | `CARRIER_DIRS` 增 `fp` + inventory 2 行 + `tests/inst.yaml` 2 条 + ledger 重生成 | `semantics_gate --check-only` rc=0；`check-tests-index` 241；`check-case-ledger` 1995 |

**判决**：QEMU 段 finding 全部 ✅已修，可标 `待验收`；gem5 FS 段仍 BLOCKED（未声称完成）。

### 第 3 轮 engineer 自审（gem5 FS 段补齐）

**范围**：逐行审本轮新增 `运行期证据（已清理，未归档）`；口径只引用 GEM5-017t 的 `run_parity.{_rec,_row,judge,counts_for}`、真实 `run_qemu_test` harness 与 `qemu_gem5_shim.py`，未另造期望值；实机重跑 `run.sh` 两轮（首轮发现 2 个失败，修复后 rc=0，checks=46）。

- 判据：`inst` 的可见结果 = `expected_fault` + guest exit（继承 GEM5-017t §0 定义）；硬门 `QEMU PASS ⇒ gem5 PASS` 且同 exit/可见；不比较时序/PC/日志。
- 可达 FAIL：parity JSON 注入（tiny scaleb#1 gem5 PASS→FAIL）→ judge 报 `GEM5_ONLY_FAIL` rc=1 → `cp`+md5 还原 → rc=0；其余 3 组注入同前轮并新增 `git diff` 非空断言（向量已随 091t 入库）。
- 结构：`(profile,engine)` 子进程隔离；矩阵行数=现场 YAML 用例数×2（52），case ID 格式 `inst/<rel>#<ord>:<id>` 与 GEM5-017t 冻结规则一致；引擎 md5 前后对账。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-1 同进程先 tiny 后 node 复用 Tiny 二进制（`_PROFILE` import 期冻结） | ✅已修 | 每个 `(profile,engine)` 起子进程，写 records JSON 汇总 | 首轮 52 行全 DIFF（node QEMU/1 gem5/125）→ 修复后 52/52 AGREE_PASS |
| F-2 091t 后向量用 `@ENTRY+0x…` token，oracle `int(...,16)` 崩 | ✅已修 | oracle 经 `machine_profile.resolve_case` 按 tiny/node 解析并各跑一遍 | oracle checks=280 failed=0（两 profile） |
| F-3 L1 失败目标解析把顶层 `check` 也算失败项 | ✅已修 | 过滤 `check`/`check-modules` 顶层目标 | L1 失败集恰为两项外部阻断 |
| F-4 GEM5-018t 并发重建 gem5 可能使证据混跑 | ✅已修 | `run.sh` 前后核 qemu/gem5 md5，不等即 FAIL | 两轮均「engines unchanged」 |

**判决**：gem5 FS 段 finding 全部 ✅已修；`run.sh` 真实 rc=0。L1 两项红为外部条件（GEM5-018t 共享源、worktree 悬空 `运行期临时目录` 引用），已在完成区登记，未改 `components/`；状态维持 `待验收`。

### 第 1 轮 reviewer 验收

**判决：Accepted**（3 条 finding 均不阻断，交 architect 收尾处置）

**重跑记录（全部在 worktree 内、相对路径，退出码取 `cmd; echo $?`）**
- `运行期证据脚本（已清理，未归档）` → **rc=0，checks=46 failures=0**；与 engineer `logs/run.log` diff 仅我方追加 `RUN_RC=0` 一行，46 条 `[PASS]` 逐行一致 ⇒ 输出真实性成立。引擎身份前后不变：qemu `6b9eb0a7…`、gem5 `e84ebbaa…`、`fs.py` `952b78c4…`、gem5 src `12a4716`（与完成区一致）。
- 独立核数：`oracle_vectors.py` rc=0 **checks=280 failed=0**；`check-lit` rc=0 **Total 163 / Passed 163**；`check-isa-coverage` rc=0 PASS（真源 264）；`check-inst-smoke` rc=0 **total=90 passed=90**（90 条现场统计）；静态门控 **9 项** rc=0（validate-vectors / check-tests-index / check-case-ledger / check-spec-cite-targets / check-dirs / check-no-residue / check-interface / check-qemu-forms / semantics_gate --check-only）。
- parity 矩阵（本轮现场生成 `generated_at=2026-11-04T06:41:29Z`）：**52 行 = tiny 26 + node 26，全 AGREE_PASS**；counts 里 `gem5_only_fail/qemu_only_fail/diff/blocked/n_a` 全 0；scaleb 24 行 (qemu,gem5) exit=(0,0)；sc-rd0 24 行 = 12 负例 exit=**136**+fault=ILLI、2 正例 exit=**0**，同 case 双引擎逐一相同。
- L1 `make -k check` rc=2，失败目标**恰为** `check-knowledge-refs` + `check-patch-tree`（无第三项，l1.log 1625 行无其它 FAIL）。独立单跑：`check-patch-tree` rc=2（4 problems 全是 gem5 `semihosting.cc/hh` 断言⑥⑨）、`check-knowledge-refs` rc=2（悬空 **162**）。`check-modules` 未跑（脚本明示 NOT run），**无 L2/L3 伪 PASS**；Makefile 中 `check` 不依赖 `check-modules`，脚本过滤它不构成凑绿。

**独立注入（2 项，均与 run.sh 的 4 组不同；`cp` 备份 + md5 对账还原，未用 git 还原）**
1. `tests/unit/llvm/lit/MC/DADAO/fp-encoding.s:125` `rd8`→`rf8` ⇒ `make check-lit` **rc=2**（`error: invalid operand for instruction`，Passed 162/Failed 1）；`cp` 还原 `md5sum -c OK` ⇒ rc=0、163/163。
2. `tools/llvm/llvm-isa-backend-matrix.tsv` ftsclb 行 `rd10`→`rf10` ⇒ `check-isa-coverage` **rc=2**（`FAIL（1 项）`）；还原后 rc=0 PASS。
还原后 `git status --porcelain -uall` 仅任务书 1 文件，4 个快照文件 md5 与开工快照逐项相等。

**约束核验**：范围仅本任务书（未提交）+ `运行期证据（已清理，未归档）`（`.gitignore` 命中、不入库）；`git diff HEAD`/`git diff master -- tests/ tools/ spec/ contracts/ components/` 均空 ⇒ 未改实现/spec/contracts/tests/tools；`components/gem5` 0 diff，patch-tree 红确属共享源被 GEM5-018t 改写（其 worktree 未提交改动恰为 `semihosting.cc.patch`/`semihosting.hh.patch`，与 4 个报错文件一一对应）；完成区 5 行、本轮审阅记录 ≤40 行。

**finding（不阻断，交收尾）**
- F1 文档级：遗留问题①「均本任务外」不准——162 悬空中有 1 条出自本任务书 line42 `运行期证据（已清理，未归档）`；该证据实际在主工作树 `运行期证据（已清理，未归档）`（run.sh/logs 齐全），属 `运行期临时目录` 不跨 worktree 的系统性悬空、非证据丢失，建议改措辞。
- F2 条件复跑：本次 gem5 FS 段跑在共享源 `12a4716`（= 本分支补丁 + GEM5-018t semihosting 修复）之上，本分支无法复现（patch-tree 红）；本次引擎 md5 全程稳定、52/52 双引擎一致故不阻断，但**GEM5-018t 落地、patch-tree 转绿后应复跑一次 gem5 FS 段**。
- F3 交主会话：`docs/TestReports/M11-三平台一致矩阵.md` 仍是 GEM5-017t 快照（引擎 md5 来自 GEM5-017t worktree，0 处提及 scaleb/sc-rd0），是否重生成由主会话裁定（建议等 GEM5-018t 后一并做）。

### 收尾复跑（GEM5-018t 落地后，architect）

**F2 条件已满足**：本分支已合入 `master`（含 `GEM5-018t`），`check-patch-tree` 转绿；重跑 `运行期证据脚本（已清理，未归档）` ⇒ `RUN_RC=0`、`checks=46 failures=0`。

- 现场 L1：`make -k check` rc=2，失败目标仅 `check-knowledge-refs`；`check-patch-tree` 已绿。
- gem5：`source HEAD=12a4716`，gem5 md5 `d2bf3bad3d91579343ed262ecf89a29f`；52 行 = tiny 26 + node 26，全 `AGREE_PASS`，`GEM5_ONLY/QEMU_ONLY/DIFF=0`。
- 证据脚本的 L1 断言已改为同时接受「018 前双阻断」与「018 后仅 krefs」；本次走后者。
- `docs/TestReports/M11-三平台一致矩阵.md` 仍按 F3 交主会话，不写入本任务 PASS。
