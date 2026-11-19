# m16-chipyard-012: RTL `scmp` 无序结果改 canonical quiet NaN（对齐 spec）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（spec 已定，`SimRISC-07 §4` canonical；等 `m16-chipyard-006` 释放 chipyard 写者）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改
**状态**：已验证

## 背景（`m15-testcases-020` 实测发现，四方对齐漏了 RTL）

spec 已把 signaling compare 的无序结果从 **sNaN** 改为 **canonical quiet NaN**（`a6f11e23`，用户 2026-11-19 裁定，版本号不变）。IDL / QEMU / gem5 三方已对齐（`m15-idl-*`、`m15-qemu-001`、`m15-gem5-001`），但 **chipyard RTL 未改**：

`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch` 的 `WumingCompareRecFN`：

```scala
val quietNan = expOnes | (BigInt(1) << (sigWidth - 2))
val sigNan   = expOnes | 1
val nanBits  = Mux(io.signaling, sigNan.U(fmtW.W), quietNan.U(fmtW.W))   // ← 旧口径
```

实测后果：`tests/inst/07-floating-point/{ftscmp,foscmp}_orrr_rf.S` 在 chipyard lane 上 **rc=10**（点 10 红）；QEMU/gem5 两 lane 已 0。

## 要做

1. `WumingCompareRecFN` 的无序结果**一律** canonical quiet NaN（删 `sigNan` 或使其不再被选中）；
2. **`flags` 规则不变**：signalcing compare 无序恒置 `NV`；quiet compare 仅 `sNaN` 置——即 `io.flags` 那一行保持不动；
3. `WumingMinMax` 已用 canonical（`canon` 常量），**不要**误改成同一份常量以外的行为；若能把两处 canonical 常量合并复用则合并，不能则各自保留并注明；
4. 检查同文件/同目录是否还有其它 `sigNan` 结果路径（`grep -rn "sigNan"`），**结果**用 sigNan 的一并订正，**标志**用途的保留。

## 验收（逐条贴真实 rc）

1. **两册回流**：`ftscmp_orrr_rf.S`/`foscmp_orrr_rf.S` 在 chipyard lane **rc=0**（改前 rc=10），给逐检查点输出；
2. **四方一致**：同一批 `.S` 在 IDL/QEMU/gem5/chipyard 四方结果**逐字节一致**（给对照）；
3. **不回归**：`ftqcmp`/`foqcmp`、`ftmin/ftmax/fomin/fomax` 等既有 FP 册 rc=0；`m16-chipyard-001` 的周期基线镜像**抽测不回退**；
4. **可达 FAIL**：把 `nanBits` 改回 `Mux(signaling, sigNan, quietNan)` ⇒ 两册 rc=10（`cp`+md5 还原 + 重建）；
5. `check-patch-tree` chipyard 段 0 问题；`check-gem5-decode`/`check-index-blobs` rc=0；合并态（`Process-07 §5a`）。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 整跑（A–F,R,G + `--inject`）`66 checks, 0 failed`、rc=0；合并态（`git merge master` → `4476a72a`）上跑，逐项输出见运行期日志目录。
**修改文件**：`components/chipyard/patches/generators/dadao-wuming/.../WumingFP.scala.patch`、`.../WumingFPUnitHarness.scala.patch`（`make_patch` 重导，23 补丁不变）、`components/chipyard/changelog.md`、`components/chipyard/README.md`、`tools/chipyard/fp_ref.py`、`tools/chipyard/fp_unit/unit_run.py`、`docs/fp-oracle-design.md`、本任务书。
**验收结果**（逐条真实 rc）：
1. 两册回流：`ftscmp_orrr_rf`/`foscmp_orrr_rf` chipyard lane **rc=0**（2/2，18 检查点/册）；同一镜像在改前 sim 上 **rc=10**（两册均停点 10，周期段 pre/post 对照现场跑出）。
2. 四方一致：IDL 侧期望字节流由 `spec §4` 与 `idl/lib/fp.idl` 的 `DP_CANONICAL_NAN`（`0x7FF8_0000_0000_0000`）/ ft 字面量 `0x7FC0_0000` 现场派生（144 B/册），chipyard/qemu/gem5 三方 `.out` 与之**逐字节相同**（`cmp` 全等，逐检查点表见日志；点 10–17 = canonical + `NV`）。
3. 不回归：`ftqcmp`/`foqcmp`/`ftmin`/`ftmax`/`fomin`/`fomax` 三平台 **6/6 rc=0** 且逐字节相同；周期抽测（`ftadd`/`ftqcmp`/`fomin`）`exit_cycle` 65053/64798/65493 与每助记符样本 777/735/836 同 `m16-chipyard-001` 记录基线、且改前/改后 sim 全等；FP 单元台 `TOTAL failed=0`、四种比较 lane 值/标志/oracle 差 0、`spec points` 20/0（含 `scmp` 两条 canonical 期望）。
4. 可达 FAIL：`nanBits` 改回 `Mux(io.signaling, sigNan.U, canonical.U)` ⇒ 重建（elab/sim rc=0）⇒ 两册 chipyard lane **rc=1**（两镜像均停点 10）⇒ `cp`+md5 还原（md5 相等）⇒ 重建 ⇒ **rc=0** 且与 IDL 流逐字节相同；另有静态注入（点 10 期望改 sNaN 位型）⇒ 期望流判据 rc=1。
5. 门控：`check-patch-tree` **chipyard 段 0 问题**（23 补丁；同刻其余问题全在别的组件段——另一任务在共享源树上并发改动/重建，随时刻在 gem5 与 linux 之间移动，chipyard 段恒 0）、`check-index-blobs`/`check-gem5-decode`/`check-component-changelog`/`check-idl-sync` rc=0、`check-source-state` chipyard `OK clean=True`；合并态同跑一遍。
**新发现/坑**：① 共享 gem5 源树被别的任务重建时，`run_inst_tiny` 的读守卫按设计拒绝（rc=75）或判「二进制在跑批期间被替换」⇒ 该窗口的 gem5 观测不可归因（本次一次整跑在 E 段如此，复原后整跑回绿）；证据脚本对 rc=75 做有界重试并记录 attempts。② `sbt` 与仿真器构建共用组件 target/项目锁 ⇒ 单元台 emit 必须与整核 elab 串行。③ `m16-chipyard-001` 的周期探针硬编码旧 lds 路径 ⇒ 复用时须改指统一布局（`tests/ee-tiny/inst_tiny.lds`）。④ sim md5 首建 `8f4ede4b…`／还原后重建 `360db9c3…`（只记录，身份判据按源码/行为；同一源码两次干净重建字节不同，`ISS-453`）。⑤ `a6f11e23` 只改 spec 正文与 IDL，`fp_ref`/单元台的旧 sNaN 期望未随之改（本任务补）。
**遗留问题**：故事讲义 `docs/DDLN/A-指令系统/DD-A009` 两处仍写「q 版返回 qNaN、s 版返回 sNaN」，与 `spec/SimRISC-07 §4` / `contract-fp` 冲突；讲义非实现判据，未在本任务改，建议随文档批次订正。单元台随机 lane 仍不是 make 门控，只在 `run.sh --unit` 段跑。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`WumingFP.scala`（`WumingRecFN.canonicalQuietNan`、`WumingCompareRecFN.nanBits`/`io.flags`、`WumingMinMax.canonNan`）、`WumingFPUnitHarness.hfCmpValue`、`fp_ref.cmp_exact`、`unit_run.py`（spec points 与比较 lane）、证据脚本各判据。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 改源树后补丁未重导 ⇒ 补丁/源树漂移 | ✅已修 | 组件源树 `commit --amend` + `make_patch chipyard` | 23 补丁、二次 `0 written`、`check-patch-tree` chipyard 0 问题 |
| F2 同目录单元台仍按旧口径造参考值（`Mux(signaling, sNaN, qNaN)`） | ✅已修 | `hfCmpValue` 取 `canonicalQuietNan`（只借 hardfloat 的 lt/eq/gt 与标志） | 生成 SV `io_out = unordered ? 64'h7FC00000`；单元台比较 lane 三差 0 |
| F3 `io.flags` 可能被连带改动 | ✅不修（本就未动） | — | 与固定基线 commit 的 diff 中该表达式 0 增删；补丁内恰 1 处 |
| F4 `WumingMinMax` 行为可能被连带改 | ✅不修（合并常量，值等价） | `canonNan = WumingRecFN.canonicalQuietNan(ew, sw)` | 公式复算 = `0x7FC0_0000` / `0x7FF8_0000_0000_0000`；min/max 册 6/6 绿 |
| F5 旧 NaN 口径文档/工具残留（README、`fp_ref`、`unit_run`、oracle 设计文档） | ✅已修 | 见「修改文件」 | 单元台 `TOTAL failed=0`、`spec points` 20/0、比较 lane 三差 0 |
| F6 C 段「无序点数」判据恒真（与自身比较） | ✅已修 | 改由**操作数**判定 NaN 行（现场 8 行/册） | 注入 1 使该判据 8→7 红 |
| F7 注入 1 原来改的是操作数而非期望列 ⇒ 判据不红 | ✅已修 | 改写点 10 的期望列为 sNaN | builder rc=1；「sNaN 结果」0→1 红 |
| F8 周期段把两册比较册放进「改前=改后」⇒ 必红 | ✅已修 | 只对不受影响三册断言全等；比较册单列「改前 rc=10 / 改后 0」 | 周期段 20/20 PASS（含基线 6 项） |
| F9 复制的改前 sim 起不来（rc=127） | ✅已修 | 导出 `LD_LIBRARY_PATH`（含 `sims/verilator`） | 改前 rc=10、基线样本与 `exit_cycle` 可见且相等 |
| F10 并发 gem5 重建使读守卫 rc=75 / 判「二进制被替换」 | ✅已修（工程侧） | rc=75 有界重试并记录 attempts；替换检测只能重跑 | 一次整跑 E 段红→复原后整跑 `66/0` |

**判决**：全部 finding 已处置（8 修、2 判不修且给证据），证据脚本整跑 `66 checks, 0 failed`。

### 第 1 轮 reviewer 验收（2026-11-20）

**重跑记录**（任务 worktree 内相对路径；证据 = 运行期证据目录内 `run.sh`，运行期日志目录内 `m16-chipyard-012-reviewer-*`）：
1. `bash <运行期证据目录内 run.sh>`（A–D）⇒ **`48 PASS / 0 FAIL`**；`ONLY=E,F,R,G bash <同上>` ⇒ **`== summary: 24 checks, 0 failed ==`、`RUN2_EXIT=0`**；合计 **66 checks, 0 failed**，与完成区一致。
2. 关键实测（我自己的输出）：两册 `2/2 镜像通过`、`four-way byte equality rc=0`，`pt10–17` chipyard/qemu/gem5 与 spec 现场派生 IDL 流逐字节相等（ft `7fc00000`、fo `7ff8000000000000`，各 18 点/144 B）；不回归 `6/6 rc=0`；周期 `exit_cycle 65053/64798/65493`、样本 `777/735/836` 与 `m16-chipyard-001` 基线逐项相等，**改前 sim 两册 `rc=10`、改后 `rc=0`**；FP 单元台 `TOTAL failed=0`、`spec points 20/0`、四比较 lane 三项差 0。
3. **独立反例注入（我做，非 engineer 自检）**：把 `canonicalQuietNan` 结果清 quiet 位（payload LSB=1）⇒ `elab_rc=0 sim_rc=0` ⇒ 两册 **`lane_suite_rc=1`、`rc {'chipyard': 10}`、输出 0 B** ⇒ `cp`+md5 还原（`md5_before=b390ac8f…` == `md5_after`）⇒ 重建 `elab_rc=0 sim_rc=0` ⇒ 两册 **`lane_suite_rc=0`、各 144 B**；组件源树 `git status -uall` 0 行。可达 FAIL 路径成立。
4. 门控（我单独跑、取真实 rc）：`check-index-blobs`/`check-gem5-decode`/`check-component-changelog`/`check-idl-sync` **均 rc=0**；`check-patch-tree` **rc=2**，43 项问题全在 **linux 段**（`m14-linux-025` 在途），**chipyard 段 23 补丁、0 问题**；`check-source-state` **rc=2**（同因 linux dirty），**`chipyard: OK HEAD=74ba545… clean=True`**。
5. `make check-milestones-fresh` **rc=2**，唯一红项 `R1: m14-linux-025 有 worktree 但台账在「待开始」`——该行在 master 已由 `505b03c9`（派单 01:31）移入「进行中」，本分支基点 `4476a72a` 早于该提交 ⇒ **基点问题，engineer 不背**。

**约束核验**：`io.flags` 表达式对固定基线 `24b1ce92` 的 diff **0 行增删**、补丁内**恰 1 处**（脚本断言 + 我独立 `git diff | grep -c` = 0）；组件生成源 `sigNan` **0 处**；`canonicalQuietNan` 公式逐位复算 ft=`0x7FC00000`、fo=`0x7FF8000000000000`，与 `spec/SimRISC-07 §4`/`§1.3` 及 `idl/lib/fp.idl` 的 `DP_CANONICAL_NAN` 一致；改动 **8 文件**与完成区「修改文件」逐一对得上，工作树 `git status -uall` 干净、无越界、无 `sigNan` 结果路径残留。

**Findings（非阻断）**：① `docs/DDLN/A-指令系统/DD-A009` L111/L114 仍写「q 版返回 qNaN、s 版返回 sNaN」，与 spec §4 冲突——讲义非实现判据、无门控读取、且不属本任务 8 文件范围 ⇒ **留文档批次订正**（交 architect 登记）；② `check-patch-tree`/`check-source-state` 的整体 rc 由 linux 段在途造成，非本任务缺陷。

**判决：Accepted** —— 验收命令在本人重跑下 66/0 全绿、独立注入红→还原回绿、chipyard 段门控 0 问题、`io.flags` 与规范值逐位核过。
