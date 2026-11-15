# m13-chipyard-003: chipyard 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（译码/执行 + sim 重建 + 三平台差分复核）

**模块**：chipyard
**项目里程碑**：M13
**依赖**：`m13-spec-010`（已合 `cb8ca30d`）；`m13-llvm-001`/`m13-qemu-016`/`m13-testcases-047`/`m13-gem5-015` 均已合入，**三平台其余两方已有 `rf2rf`**
**可并行分片**：否（chipyard 组件单写者）
**预估**：2–3 h（含 sim 重建 20–40 min）
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：已验证

## 语义真源

`spec/SimRISC-02`（`rf2rf` 段）+ `contracts/opcodes.yaml::rf2rf_orri_rf`：`opc=OPC-octa(0x40)`、`opx=111-100(ha=0x3C)`、`orri`/`rf`；整 64 位逐位复制、不置标志；`immu6=0`/两端越界/任意重叠 ⇒ ILLI；**目的含 `rf0` ⇒ ILLI**、源 `rf0` 合法。

## 任务

1. `WumingDecoder.scala`：删两条旧译码、加 `rf2rf`（`opx=111-100`）；
2. `WumingFP.scala`（或块复制所在文件）：实现整 64 位逐元素搬移 + 六类非法（**在任何寄存器写之前判定**）；
3. 删 `ft2ft`/`fo2fo` 的执行路径；
4. 重建 sim（`make verilog`/`build-chipyard` 按现有 Makefile 目标，申报耗时），记录**新 sim md5**（旧基线 `079ae015…` 作废，需在完成区登记新值）；
5. **三平台复核**：用 `run_asm_suite.py` 对 `tests/inst/02-reg-copy/rf2rf_orri_rf.S`（17 点/7 镜像）跑 **qemu + gem5 + chipyard**，三点逐字节一致；若 chipyard 侧因机型不支持某故障例 ⇒ 记 GAP 并给 spec 依据，不伪造。

## 验收（真实 rc）

1. `rf2rf` 在 chipyard Tiny 上：`immu6=3` 三元素逐位复制、源不变；六类非法各 `ILLI`；源 `rf0` 合法；
2. 旧指令编码 ⇒ 非法（与 qemu `0xF9`、gem5 `FaultUNDI` 同口径说明）；
3. 三平台差分：`rf2rf` 7 镜像逐字节一致（贴三平台 rc 与字节数）；**新 sim md5** 登记；
4. 门控：`check-patch-tree`（chipyard 段 0 问题）、`--source-state` chipyard OK、`check-component-changelog`、`check-no-residue`、`check-inst-asm`（应仍 PASS：qemu 侧）；
5. **≥2 路注入**（`cp`+md5 还原）：① 放行目的 `rf0` ⇒ 负例红；② 重叠放宽为"仅完全重合" ⇒ 部分重叠负例红；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/chipyard/**`、本任务书；不改 `spec/`、`contracts/`、`tests/inst/**`、其它组件；
- 构建按需（`JOBS=32`，**申报耗时**）；**禁 `install-host`/`check-modules`**；**禁 `git reset --hard`**；不 sync/reset 节点；
- 注意：`server208` 与 `ics170` 上可能仍有 M12 遗留 sim 进程，**禁 kill**（若非本任务进程）；
- 不提交 git；注入还原 `cp`+md5。

## 待裁定

无。`rf2rf` 的语义与六类非法全部取自 `spec/SimRISC-02 §1` 与 `contracts/opcodes.yaml::rf2rf_orri_rf`（`m13-spec-010` 已定稿），实现期未产生需用户裁定的新决策。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

逐行审查 `WumingDecoder.scala`（`blockCopy` 新参数、`0x40/0x3C` 译码、两条旧译码与 `fpCopy` 删除、`octaRows`/`rfRows` 位图、`cvtF2F`/`w0Ft` 注释）与运行期证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `cp -p` 还原保留旧 mtime ⇒ `common.mk` 的生成器 jar 规则（`$(GENERATOR_CLASSPATH) &: $(CHIPYARD_SCALA_SOURCES)`）判「已最新」，于是用**注入后的 jar** 重新 elaborate（实测到假绿：7 镜像全绿而退役编码探针 rc=1） | ✅已修 | 证据脚本 `restore_src` 增 `touch`；新增 `rebuild_was_real` 断言（elab 日志须含 `sbt-launch.jar`、不得含 `Nothing to be done for 'verilog'`） | `[restore] elaboration re-assembled the generator jar=PASS` / `not a no-op=PASS`；sim md5 回 `4e072a71…` |
| F2 注入备份在第一次还原时被删，后续注入无备份可还原（源码被 inj2+inj3 叠加污染） | ✅已修 | 备份保留到段末、末轮后统一删；已污染的源码用「逆替换 + md5 对账」恢复 | 还原 md5 `545a5479…` == 交付源码 md5；组件源 `git status` 0 项 |
| F3 基线「源码树干净」检查排在 `cp` 备份之后 ⇒ 备份文件自身算 untracked 而误红 | ✅已修 | 先查干净、再 `cp` | `injection baseline: source tree clean=PASS (0)` |
| F4 注入负例的 rc 期望写成 0；`TEST_FAULT_ENC` 无异常时直落 `__EXIT(pt)` ⇒ 实际是点号 | ✅已修 | 断言改 12 / 16，并保留「rc ≠ 0xF8」的可达 FAIL 断言 | `pt12 falls through to __EXIT(pt12)=12`、`pt16…=16` |
| F5 静态断言用 `is(0x0A.U)` 判「旧译码已删」会命中 octa 子表的 `xor.o`（同为 ha=0x0A） | ✅已修 | 改按 `fpCopy(false)`/`fpCopy(true)` 上下文断言 | `patch: the ft2ft/fo2fo decode cell (with its copy helper) is gone` |
| F6 新增参数是否波及 `rd2rf`（`rf0` 可作目的） | ❌不修（无需改） | `forbidRf0Dst` 默认 `false`，`0x3D/0x3E` 调用点未动，`if` 在 elaboration 即消去 | `02-reg-copy` 全册三平台 65/65（含 `rd2rf`/`rf2rd` 全镜像） |
| F7 `w0Ft` 在 `sCopy` 期间是否被下一条指令改写 | ❌不修（已核） | `inst` 由当前 IP 组合派生、`sCopy` 期间 IP 不变；且 `rf2rf` 恒 `w0Ft=false` | 高位非零的位型（`0x8000_0000_0000_0000` 等）逐位复制绿 |
| F8 「目的范围含 `rf0` ⇔ `hb == 0`」是否普遍 | ❌不修（已核） | 窗口自 `hb` 升序、`immu6 ≥ 1` ⇒ 等价，与 QEMU `fp_check_dst_rf0` 同判 | 注入①（放行该判定）使 pt12 由 `0xF8` 变 12、其余 5 例不动 |

自审判决：F1–F8 全部闭环（6 条已修/已核、0 条延后）⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-15）
**重跑（我方执行、真实退出码）**：`run.sh` A–E ⇒ `PASS=51 FAIL=0` rc=0（7 镜像三平台 rc `0`/`248×6`、链例 88 B、输出 md5 `ce2011e6…`；n=3 探针 48 B 三方全等；退役编码三平台 `[249,249]`；sim md5 `4e072a71…`；`check-patch-tree` 0（10 集 401、chipyard 21）、`--source-state` chipyard OK `35c62c8` base+1 clean、changelog/no-residue/`check-inst-asm` 全 0（896/896、264 id））；另抽 `rd2rf`/`rf2rd` 三平台 4/4、5/5 全绿；与完成区数字逐条一致。
**位图独立对照（contracts↔RTL 逐格）**：`0x40–0x43/0x47` 全等；`0x44` 行0/行1 `0x4B==0x4B` ⇒ 恰好只清 `000-010`/`001-010` 两格（`ft2ft`/`fo2fo` 已不在 contracts）；`octaRows[7] 0x6F→0x7F` = 补上 rf2rf 格（`0x40/0x3F` 仍空置，contracts 同），其余 id 不受影响。
**六类非法先于写、目的未改**：`is(sExec)` 同链内 `execFault` 先于 `d.isCopy`、`execW0` 带 `!execFault`；`+verbose` 实跑 fault016：`exec ip=0xffffff0118e8 inst=0x40f15504 cycle=35302` 与 `excp cause=0x100 … cycle=35302` 同拍，全镜像 `copy ip=` 仅 setup `rd2rf` 一条 ⇒ 故障指令未进 `sCopy`、写口未使能（陷阱后寄存器不可读——hmon 直接 `SYS_EXIT`，故以同拍异常+无 sCopy+`w0En` 门控三重证明）。
**整 64 位**：`w0Data=Mux(w0Copy, rf.io.r0Data, …)`、`w0Ft := d.w0Ft` 且 `blockCopy` 不置 ⇒ `writeRf(ft=false)` 全 64 位；链例点5（immu6=3，`0x8000000000000000`/`0x000FFFFFFFFFFFFF` 高半非零）与 n=3 探针三平台逐字节相等。
**注入（自设计 2 路，`cp`+md5+`touch` 还原、真实重编）**：① 调用点 `forbidRf0Dst=true→false` ⇒ pt12 `248→12`（另 5 例仍 248、链例绿）；② `rfRows 0x4B,0x4B→0x4F,0x4F` ⇒ 退役编码 `249→1/2`（宏 `__pad_fail` cause 不符退点号；机制 `when(!subHandled){subDefined⇒ill}` = ILLI≠UNDI）。还原重建：sim 回 `4e072a71…`、7 镜像与 `[249,249]` 全绿、源码 `545a5479…`、源树 0 改动无残留（mtime 坑按 `touch` 处理，重建均非 no-op）。
**越界**：`git show 63c38e23 --name-only` = 本任务书 + `components/chipyard/{README.md, changelog.md, 两 .patch}`；`spec/`、`contracts/`、`tests/inst/**` 0 改动；主工作树 `master` 干净、`git status -uall` 0 项。
**非阻断 finding（文档级，交 architect 收尾改）**：F1 README 称 `octaRows[7]=0x7F`「本行 8 格全定义」——0x7F 仅 7 格；F2 changelog 记「注入 2 路」而完成区为 3 路；F3 我复跑 `make check` 红在 `check-milestones-fresh`（`m13-spec-011`/`m13-testcases-048` 有 worktree 未入表）——系审查期间另一会话在 master 建 worktree+补台账行、本任务基线 `ed7428af` 未含（主工作树 `c7fe9a5e` 该门控 PASS）⇒ 环境并发非本任务产出；F4 RTL `rfRows[2],[3]=0x7F` vs contracts `0xFF`（`ftsgnj`/`fosgnj` 格），两格有 switch 分支故行为无差（既有差异）。
**判决：Accepted** —— 中改档位（diff 逐行 + 2 路自设计注入红→还原回绿 + 5 项验收门控我方重跑全绿 + 越界 0）；完成区 17 行、无运行期路径。未复跑 `run.sh --inject`（其 3 路），以上方自设计 2 路覆盖 ≥2 路要求。

## 完成区

**测试结果**：通过 51/51（证据脚本 `run.sh` A–E，`EXIT=0`）+ 39/39（`run.sh --inject`，3 路注入含「还原→回绿」，`EXIT=0`）+ 02 册回归 65/65 镜像三平台全绿；失败原因：无。

**修改文件**（与 `git status -uall` 逐项一致）：① `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingDecoder.scala.patch`；② 同目录 `WumingFP.scala.patch`（仅注释一句）；③ `components/chipyard/README.md`（新节「寄存器复制 `rf2rf` 取代 `ft2ft`/`fo2fo`」）；④ `components/chipyard/changelog.md`（M13 一条）；⑤ 本任务书。证据脚本与两份运行期探针 `.S` 落运行期证据目录（不入 git）。组件源 HEAD=`35c62c8`（base+1、clean，`make_patch.py chipyard`：2 written / 19 unchanged）。

**验收结果**：
- **sim 重建**：`make verilog CONFIG=WumingTinyConfig` 67 s + `make CONFIG=WumingTinyConfig`（Verilator，`JOBS=32`）44 s，单轮 ≈2 min（增量：重新装配 jar + 重 elaborate + 重编改动的模块）；**新 sim md5 `4e072a711afdca8a36788f9a9958e896`**（旧基线 `079ae015…` 作废）。还原后同源码重建两次均得同一 md5 ⇒ 构建对源码确定性。
- **chipyard 侧 `rf2rf`**：n=3 探针（目的三元素逐位 + 三源元素复制后不变）三平台 48 B 全等；向量链例 11 点 / 88 B 三方 rc=0；**六类非法 chipyard 全 `0xF8`**（pt12 目的 rf0 / 13 immu6=0 / 14 目的越界 / 15 完全重合 / 16 部分交错 / 17 源越界）；**源 `rf0` 合法**（链例 pt11 `TEST_MOV_RF0` 绿）。
- **旧指令编码**：`0x44080000`（`ft2ft`，0x44/0x02）与 `0x44280000`（`fo2fo`，0x44/0x0A）三平台 rc=`0xF9`（UNDI，槽位自 `m13-spec-010` 起空置；与 QEMU `insn.decode`「空白单元格 ⇒ UNDI」、gem5 `FaultUNDI` 同口径）。
- **三平台差分**：`rf2rf_orri_rf.S` **7/7 镜像**；链例三平台各 **88 B**、三份输出 md5 同为 `ce2011e6…`；6 个故障例三点 rc 均 **248**；另 `02-reg-copy` 全册 17 id × 65 镜像三平台全绿。
- **门控**：`check-patch-tree` rc=0（10 集 401 补丁；chipyard 21 段 0 问题）、`check-source-state`（chipyard OK base+1 clean）、`check-component-changelog` rc=0、`check-no-residue` rc=0、`check-inst-asm` rc=0（896/896、264 id）、`check-index-blobs` rc=0、`check-run-artifacts` rc=0、`make check`（L1）41 项 PASS／唯一红点 `check-temp-dirs`（另一任务的遗留临时目录，非本任务、按规不代删）。
- **注入（`cp`+md5 还原，每轮真实重编并核「jar 重装配 + 非 no-op」）**：① 放行目的 `rf0` ⇒ pt12 由 `0xF8` 变 12（直落 `__EXIT(pt)`），另 5 例仍 `0xF8`、链例仍绿；② 重叠放宽为「仅完全重合」⇒ pt16 变 16，完全重合 pt15 仍 `0xF8`；③ `0x02` 单元重新译码 ⇒ 退役编码探针 `0xF9→1`、另一字仍 `0xF9`。还原后源码 md5 `545a5479…`、sim 回 `4e072a71…`、7 镜像与 `0xF9` 探针全绿。

**新发现/坑**：① 生成器 jar 规则按 **mtime** 判新旧：`cp -p` 还原会保留旧 mtime ⇒ `make verilog` 打 `Nothing to be done` 并用**注入后的 jar** 重新 elaborate（实测假绿）；还原后必须 `touch` 源文件并断言 elab 日志含 sbt 装配。② 空置槽位语义：只删 `switch` 分支不改子表位图会把旧编码变成 ILLI（应为 UNDI），位图必须同步（`rfRows` 前两行 `0x4F→0x4B`、`octaRows[7]` `0x6F→0x7F`）。③ `TEST_FAULT_ENC` 无故障时直落 `__EXIT(pt)`，注入负例 rc = 点号而非 0。④ 组件内 `is(0x0A.U)` 不唯一（octa 子表 `xor.o` 亦为 ha=0x0A），静态断言须带上下文。⑤ 改 1 个 Scala 文件的增量重建 ≈2 min，不必按 20–40 min 预算。⑥ 证据脚本给 `run_asm_suite` 的 `--log-dir` 不能落 `.work/log/**`：镜像级日志名不合 `check-run-artifacts` 的 `<TASK-ID>-<purpose>.(log|json|txt)` 约定（`A3 illegal name` 红），须留在证据 work 目录。

**遗留问题**：① `tools/chipyard/fp_sweep.py` / `inst_sweep.py` 未重跑（不引用已退役助记符、与本次改动无交集，也不在本任务门控内）；② 组件 README 的 `m12-chipyard-012` / `m13-chipyard-001` 段仍以 `ft2ft`/`fo2fo` 举例（历史任务记录，按「不改写既有记录」保留）；③ 下单时作业树停在 `9959516f`（未含任务书提交 `ed7428af`），已用 `git merge --ff-only ed7428af` 对齐，未另建提交；④ L1 的 `check-temp-dirs` 红点属他任务遗留临时目录，未删（按「不代删、不凑绿」）。
