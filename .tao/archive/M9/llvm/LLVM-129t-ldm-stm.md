# LLVM-129t: 让 LLVM 用上 `ldm`/`stm`（多寄存器 load/store）

**模块**：llvm
**项目里程碑**：M9（用户 2026-10-23 裁定「M9 做」）
**依赖**：`LLVM-127t`（窄位类型已稳定）、`INFRA-102t`（门控已去常量）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状

### 用户裁定
2026-10-23：「4、M9做」（在「`ldm`/`stm` 立不立项」一问中选 M9 内完成）。

### 现场事实（2026-10-24 核，执行前须复核）
- ISA 已有 `ldm.*`/`stm.*`（`rrri`，`immu6` = 寄存器个数；`immu6 = 0` 触发 ILLI，`legality_rules.yaml::mreg_zero`）。
- `contract-abi §1.3` 明确：`rb32`–`rb63` 是**连续 callee-saved 池**，「可整段用 `stm`/`ldm` 批量保存/恢复」；`rd32`–`rd63` 同为 callee-saved。
- LLVM **完全未使用**它们（`gen_isa_coverage`：`ldm.*`/`stm.*` 全部 `L2_isel=no`）；当前序言/尾声与拷贝都是逐条 `ld.o`/`st.o`。
- LLVM 的 `MaxStoresPerMemcpy/Memset/Memmove = 16`、`MaxLoadsPerMemcmp = 16`（`DADAOISelLowering.cpp`）。

## 目标

让 LLVM 在**不改变语义**的前提下发射 `ldm`/`stm`，至少覆盖：

1. **函数序言/尾声**：多个连续 callee-saved 寄存器的保存/恢复合并为 1 条 `stm`/`ldm`；
2. **连续栈槽的 spill/reload 突发**（若可行）；
3. 一般相邻访存（可选，命中率低）。

**实现机制不预设**：post-RA 机器层合并（参考 `llvm/lib/Target/ARM/ARMLoadStoreOptimizer.cpp`）、pre-RA 聚拢、或其它方案，由工程师论证并在完成区写明**选择理由与代价**。

## 边界（必须写进完成区）

- **不承诺 `memset`**：`stm` 写的是「寄存器组 → 连续地址」，每个寄存器值不同；`memset` 是同一值重复，用 `stm` 需先把值复制到 n 个连续寄存器，收益为零或负。
- `memcpy`：内联展开路径（≤16 次存取）可能受益，但依赖 RA 后寄存器连续；不承诺一定能合并。
- **`MaxStoresPer*` 阈值在本册完成前不改**；合并机制落地后再**用 embench 实测**决定是否调整（无实测不动）。

## 验收

1. **可测量的合并**：构造一个使用 ≥8 个 callee-saved 寄存器的函数，`-O2` 汇编中序言/尾声出现 `stm`/`ldm`（贴前后对比：逐条 `st.o` 条数 → `stm` 条数）。
2. **语义不变**：`libc-test` 静态档、`embench` 38/38、`lit` 全绿；`check_qemu_trans --strict` 266/266。
3. **不误合并**：中间有 `call`、别名写、跨 bank、`immu6 = 0`、寄存器不连续等场景**不得合并**（各 1 条反例，用汇编观察）。
4. **可达 FAIL ≥2**：① 关掉合并 pass ⇒ 序言/尾声断言红；② 故意允许跨 `call` 合并 ⇒ 正确性用例红。
5. 门控：`check-instrinfo`、`check-isa-coverage`、`check-scope`、`check_qemu_trans 266/266`、`check_lit_gen`、`check-lit`、L1、L2；`check-patch-tree`（新增 pass 文件须进补丁树与 `series`）。
6. 覆盖披露：新增/删除/修改用例数。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（新增 pass 文件 + `DADAOTargetMachine.cpp` 挂载 + `DADAOInstrInfo.td` 若无 pattern 需补）、`tests/llvm/lit/**`。
- **输出**：合并 pass（或等价机制）+ lit 正/反例 + 前后对比数据。
- **约束**：不改 ISA / `spec/` / `contracts/`；不改 `scope`；不 commit/push；临时目录 `/tmp/opencode/LLVM-129t/`。

## 风险与纪律

- **正确性优先**：多寄存器指令的寄存器顺序、基址/偏移语义、异常边界（未对齐）必须逐条核对 `SimRISC-01`/`SimRISC-12`；任何不确定就不合并。
- 改 `.td` ⇒ `install-host` + `build-builtins` + `build-musl-shared`。
- 回归超预期（>2 个代表用例 2 h 内定位不了）⇒ 保留 WIP、停在该阶段、报 architect。

## 完成区

**机制选择**：**post-RA 合并**（`DADAOLoadStoreOptimizer.cpp`，`addPreEmitPass`：PEI 之后、BranchRelaxation 之前，仅 `-O1+`）。理由：寄存器连续性由 RA 决定，pre-RA 只能"聚拢"不能保证（ARM `ARMLoadStoreOptimizer` 同理：pre-RA 排序、post-RA 真合并）；post-PEI 时 FI 已消除、物理寄存器已定，可直接发射。**代价**：只在基本块内严格相邻；非 0 首偏移需 `rb2rb`+`add.si` 两条 setup（故要求 count≥4）、且需要一个"本函数完全未用"的 caller-saved RB 作 scratch（post-RA 无 scavenger），否则不合并。**序言/尾声**的 callee-saved 批量本已存在（LLVM-039t / ADR-0018 C7 D4 form 4，`m6-csr-batch.mir` 在测）；本册补的是**一般相邻访存** + 单一总开关 + 覆盖证据（现场复核推翻了任务书"完全没用"的前提，`stm.o` 早已 `L2_isel=yes`）。
**边界**：不承诺 `memset`（同值重复无收益）；`memcpy` 只在内联展开且 RA 后连续时才可能中（本例实测 f128 双 64-bit 存取、4 连 `st.o` 命中，复制循环的 load/store 交替不命中，不承诺）；**未改 `MaxStoresPer*`**（待 embench 实测后再定）。
**测试结果**：lit **148/148**（+3 新、改 1：`f128-codegen.ll` 的两次 `ld.o` 现为 `ldm.o`）；L1 `make check` **PASS**；L2 `make check-modules` **PASS**（`module checks (L2): PASS`）；embench **38/38**；libc-test 静态 **337 = pass 330 / fail 1 / known-fail 1 / blocked 5**（fail = `math/yn` 3 ulp，**与本册无关**：`jn/j0/j1` 目标码开关本特性逐条一致、只差序言/尾声批量，且 `fofma` 已多点合入，见遗留①）；`check_qemu_trans --strict` **266/266**。
**修改文件**：组件新增 `DADAOLoadStoreOptimizer.cpp`；改 `CMakeLists.txt`/`DADAO.h`/`DADAOTargetMachine.cpp`/`DADAOFrameLowering.cpp`（`-dadao-disable-ldm-stm` 总开关）；`components/llvm-project/{series,changelog.md}` + 5 份补丁；lit 新增 `m9-ldm-stm.mir`、`m9-ldm-stm-prologue.ll`、`m9-ldst-opt.ll`，改 `f128-codegen.ll`；`tools/llvm/llvm-isa-backend-matrix.{tsv,md}` 重生成；`.tao/knowledge/milestones.md` 任务流水状态行；`tests/llvm/ir-lli/manifest.yaml`（+4 条 `exclude`，见下）。
**验收结果**：① 序言/尾声（9 个 callee-saved）：`stm.o {rd32:rd39}, [rb1, rd40]` + `ldm.o {rd32:rd39}, [rb1, rd40]`（+1 holder `st.o`/`ld.o`）→ 关开关后 **9 条 `st.o` + 9 条 `ld.o`**（9→1/9→1）。一般合并：`copy4` **4 `st.o` → 1 `stm.o {rd16:rd19}, [rb16, rd0]`**；`ld.o rd4/rd5` → `ldm.o {rd4:rd5}`（2→1）。② 见上（lit/L1/L2/embench 全绿；libc-test 1 例见遗留①）。③ 反例 4 类均不合并（MIR lit）：跨 `call`（`stm …,5` 不出现、call 两侧各自成 run）、别名写（中间 store 阻断）、跨 bank（`rd20`→`rb21` 不合并）、不连续（寄存器 `rd20`→`rd22`、偏移 0→16），另加"被加载范围含 base 寄存器"1 条。④ 可达 FAIL：`-dadao-disable-ldm-stm` ⇒ 序言断言红（rc=1→还原 rc=0）；`-dadao-ldst-opt-allow-call` ⇒ 跨 call 合成 `stm …,5`、负例红（rc=1→还原 rc=0）。⑤ 门控全绿：`check-instrinfo`/`check-isa-coverage`（yes **189→191**、buildmi 53→59）/`check-scope`/`check_qemu_trans 266/266`/`check_lit_gen`/`check-lit`/L1/L2/`check-patch-tree`（**195** patches）；`install-host`+`build-builtins`+`build-musl-shared` PASS。⑥ 覆盖：lit +3 / 改 1 / 删 0；矩阵 `ldm.o_rrri_{rd,rb}` no→yes，`stm.o` 三形态补 buildmi 证据。
**证据**：`.work/evidence/LLVM-129t/run.sh` **30/30** rc=0（含两组"绿→注入红→还原绿"、4 类反例、6 项静态门控；计数现场统计）。
**diff_ir_lli 登记（reviewer Needs Revision 修复）**：`make test-m6` rc=0；`structural: on-disk=91 include=19 exclude=72 unclassified=0`、`hits 19/19 matched`。新增 `exclude` 4 条（`no-value-entry`，均无 `@main` 值通道）：本册 `m9-ldm-stm-prologue.ll`、`m9-ldst-opt.ll` + LLVM-127t 遗留 `abi-narrow-extend.ll`、`narrow-int.ll`；未改分类口径、未删文件、未动 pass/代码。
**新发现/坑**：① 硬件寄存器号 = `HWEncoding`（`rd0`=0…），**不是** TableGen enum（`rd20`=150）——范围判据必须用 `TRI.getEncodingValue`，否则 `start+immu6≤64` 全错（首版被 MIR 暴露）。② `MachineFunctionPass` 覆写 `getAnalysisUsage` 必须回调基类，否则 `-run-pass` 断言 `MachineModuleInfoWrapperPass` 未 require。③ `stm.o` 的 range 若含其 base 寄存器，顺序语义与新指令不等（load 先写 base）——须显式拒绝。④ 证据提取器只认 `BuildMI(...)` 文本里的 `DADAO::<def>`，opcode 三元式须写在 BuildMI 实参内。⑤ 任务书"现场事实"与现场不符（序言已批量、`stm.o` 已 yes）——派单前复核有效。
**遗留问题**：① `libc-test` 静态 `math/yn` fail（3 ulp）**非本册**：`jn/j0/j1` 目标码在本开关 on/off 下指令逐条相同（仅序言/尾声批量差异），失败用例自身 TU 零 `ldm/stm`，关开关仍 fail；疑与 LLVM-123t 的 FMA 收缩（`j0` 50 / `j1` 49 条 `fofma`）或 126t FP 变更相关，建议 architect 立项核对（127t 基线 331 pass 早于 123t/126t 落地）。② 非 0 首偏移路径依赖"全函数未用的 caller-saved RB"，高压力函数可能无可用 scratch ⇒ 该路径少命中（正确性不受影响，只是不合并）。③ 未做 pre-RA 聚拢（可提高命中率，本册未立项）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：新增 `DADAOLoadStoreOptimizer.cpp`（约 300 行）、`DADAO.h`/`CMakeLists.txt`/`DADAOTargetMachine.cpp`/`DADAOFrameLowering.cpp` 4 处改动、3 个 lit 新增 + 1 个既有 lit 修改、矩阵重生成、证据脚本。

**逐行结论**：① 只认 `ld_o_rd/rb`、`st_o_rd/rb` 4 个 8 字节形态（`getNumExplicitOperands()==3` + 类型校验），其余 memory 指令一律当屏障；合并要求同 MBB、严格相邻（仅允许 debug 指令）、同方向、同 bank、同 base、寄存器逐个 +1、偏移逐个 +8，因此不存在重排/别名穿越。② `immu6` 判据用 `TRI.getEncodingValue`（硬件 bank 内编号）而非 TableGen enum，`start+immu6≤64`、`ldm` 起始≠0、保留寄存器拒绝；`isReserved(FirstReg+Count-1)` 依赖同 bank enum 连续（已由范围判据保证不跨 bank）。③ volatile/atomic、FrameSetup/Destroy 一律跳过；memoperands 用 `cloneMergedMemRefs` 合并（非手工拼）。④ 偏移为 0 → `rd0` 作偏移寄存器（零成本）；非 0 → `rb2rb`+`add.si` 到"全函数未用"的 caller-saved RB（`rb3`–`rb31`，避开 PC/SP/FP/TP），并要求 count≥4 才划算；scratch 语义安全依据 = 未被本函数任何 operand 引用 ⇒ 值不可观察。⑤ 新增"被加载范围含 base 寄存器"拒绝：顺序码第二条地址用的是第一条刚写入的值，`ldm` 用旧值 ⇒ 不等价（`stm` 只读范围，不拒绝）。⑥ 删除原访问、保留 `AfterRun` 迭代器（intrusive list 不失效）；`-O0` 不挂 pass，FrameLowering 批量在 `-O0` 仍生效（与改动前一致）。

**finding 与处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 范围判据用 enum 值（`rd20`=150）⇒ `start+immu6>64` 恒真、全部拒绝 | ✅已修 | 改用 `TRI.getEncodingValue(Head.Reg)` | MIR `merge_st4` 4→1 `stm_o_rd`；`m9-ldst-opt.ll` `stm.o {rd16:rd19}` |
| `getAnalysisUsage` 未回调基类 ⇒ `-run-pass` 断言 `MachineModuleInfoWrapperPass` 未 require（abort） | ✅已修 | 末尾 `MachineFunctionPass::getAnalysisUsage(AU)` | `llc -run-pass=dadao-ldst-opt -verify-machineinstrs` rc=0 |
| load 范围包含 base 寄存器时顺序语义不等价（未拒绝） | ✅已修 | `Head.IsLoad && Bank==1 && Base∈[First,First+Count)` ⇒ 拒绝 | 新增 MIR `no_merge_base_load`（`ldm_o_rb` 计数 0） |
| 矩阵证据提取只认 `BuildMI(...)` 内的 `DADAO::<def>`；opcode 三元式写在 BuildMI 外 ⇒ `ldm.o` 仍 `L2_isel=no` | ✅已修 | 四个 batch opcode 直接写进两个 `BuildMI` 实参 | 矩阵 `ldm.o_rrri_{rd,rb}` yes；buildmi 53→59 |
| 新 pass 合并了 `f128_load` 的两次 `ld.o`，既有 lit 期望过期 | ✅已修（披露） | `f128-codegen.ll` 改为断言 `ldm.o {rd4:rd5}, [rb16, rd0]` | `make check-lit` 148/148 |
| 首版 MIR 输入非 verifier-clean（load 未写成 `$rd = ld_o_rd`、regmask 需 `CustomRegMask(...)` 且语义是"保留集"） | ✅已修 | 按 MIR 语法重写，`-verify-machineinstrs` 全绿 | 证据脚本 `mir-lit-assertions` rc=0 |
| `libc-test` `math/yn` 3 ulp fail | ⏸延后（非本册） | 未改 | `jn/j0/j1` on/off 目标码逐条一致（仅序言/尾声批量差异）、失败 TU 零 `ldm/stm`、关开关仍 fail ⇒ 归 123t/126t FP 面，见完成区遗留① |
| 非 0 偏移路径依赖"全函数未用 scratch"，高压力函数可能不命中 | ❌不修（记录） | 未改设计 | 正确性不受影响；已写入遗留② |

**判决**：finding 全部已修或已证不适用/非本册；状态置 `待验收`。

### 第 1 轮 reviewer 验收

**范围**：独立重跑，不采信完成区。临时树 `/tmp/opencode/LLVM-129t-review/`；仓库零改动（4 个目标文件 md5 与验收前逐一对账一致，`git status --porcelain -uall` 干净）。

**合并真发生**（reviewer 自写用例，非工程师用例）：10 个值跨 call ⇒ `-O2` ON = `stm.o {rd32:rd41},[rb1,rd42]` + `ldm.o {rd32:rd41},[rb1,rd42]` + 各 1 条 holder `st.o`/`ld.o`；OFF = **11 `st.o` + 11 `ld.o`**。4 连 `st.o rd16..rd19,[rb16,0..24]` → `stm.o {rd16:rd19},[rb16,rd0]`（4→1）。

**语义 3 例**（QEMU + host `clang` 编同一 IR 作独立 oracle，不经 DADAO codegen）：① 10 值跨 call 保存/恢复（与 caller-saved 短命值混用）：host / QEMU ON / QEMU OFF 三方 exit **=155**；② 非 0 首偏移 count=4：`rb2rb {rb4},{rb16}`+`add.si rb4,8`+`stm.o {rd16:rd19},[rb4,rd0]`，三方 exit **=0**（哨兵校验无越界写）；③ load 范围含基址：顺序语义 exit=**0**，负控制（手写 `ldm.o {rb20:rb21},[rb20,rd0]` 形态）exit=**239** ⇒ 误合并必被抓，反例是活的。

**反例 5 类不合并**（reviewer 自写 MIR，每类配"去掉障碍即合并"孪生）：跨 call（call 后 4 连不合并；孪生去 call ⇒ `rb2rb`+`add_si`+`stm …,4`）、别名写（孪生去 store ⇒ `ldm …,4`）、跨 bank（孪生 rb21→rd21 ⇒ `stm …,2`）、不连续（孪生 rd22→rd21 ⇒ `stm …,2`）、load 含 base（孪生 base→rb22 ⇒ `ldm_o_rb …,2`）——5 孪生全合并 ⇒ 5 反例全为真反例。

**`math/yn` 归因（决定性）**：基线复现 exit=1（ulperr -3.219）。全量重建 musl 关 `-dadao-disable-ldm-stm`（ldm/stm 311→36 个 .o；余 36 是 varargs/setjmp 未受门控的既有路径）⇒ 仍 exit=1 且错误逐字节相同；`jn.c`（`yn` 所在 TU）加 **`-ffp-contract=off`** 重编 ⇒ **exit=0 回绿**。⇒ 非本册引入，ISS-332 假设（FMA 收缩）成立。

**门控**（reviewer 本人重跑，全 rc=0）：`check-instrinfo` 0 errors、`check-isa-coverage` yes **191**、`check-scope` PASS、`check_qemu_trans --strict` **266/266**、`check_lit_gen` 64 checks、`check-lit` **148/148**、L1 `repository checks (L1): PASS`、L2 `module checks (L2): PASS`（总 rc=0）、`check-patch-tree` **195** patches。

**注入 2 次**（reviewer 自写用例，`cp`+md5 还原，两次 md5 对账 OK）：① `-dadao-disable-ldm-stm` ⇒ 序言断言 绿0→**红1**→绿0；② `-dadao-ldst-opt-allow-call` ⇒ 跨 call 合成 `stm_o_rd $rd4,$rb16,$rd0,6`（把 call 返回值 store 提到 call 之前），负例 绿0→**红1**→绿0。

**ISS-332 建议**（仅建议，不改 issue 状态、不改仓库）：修法 = 给 musl 交叉构建加 `-ffp-contract=off`（落点 `tools/infra/build_musl.py` 的 `CFLAGS`；上游 musl `configure` 本就尝试该 flag）。本审已用临时树实证回绿，建议按此立项修复。

**失败项（阻断）**：`make test-m6` 第 2/3 步 `diff_ir_lli` **FAIL rc=2**（`structural: unclassified=4`）。本册新增的 `m9-ldm-stm-prologue.ll`、`m9-ldst-opt.ll` 未登记 `tests/llvm/ir-lli/manifest.yaml`（二者无 `@main`、无值通道，应入 `exclude` 并写 class+reason）；缺口另含 127t 遗留未登记的 `abi-narrow-extend.ll`/`narrow-int.ll`（既有红、非本册引入，但同属该账本，建议一并补）。完成区未披露此项。修法仅账本登记，不涉代码/语义。

**判决**：**Needs Revision** —— 本册核心交付（合并正确性、5 类反例、归因、覆盖 +3/改1/删0 且 f128 断言为收紧、任务书 9 项验收门控、两次注入）全部达标；但新增 lit `.ll` 未登记 ir-lli 账本致 `test-m6` 红且未披露，补齐 2（或 4）条 `exclude` 记录即可复验放行。

### 第 2 轮 reviewer 验收

**返工面**：`97774bfb` 仅改 `tests/llvm/ir-lli/manifest.yaml`（`git diff HEAD~1 -- tests/` = 1 个 M、0 删除）。4 个文件均登记为 **`exclude`**、复用既有 class `no-value-entry`（未造新口径、未挪动任何既有 include 条目，include 仍 19；exclude 68→72）：`m9-ldm-stm-prologue.ll`/`m9-ldst-opt.ll`（本册）+ `abi-narrow-extend.ll`/`narrow-int.ll`（127t 遗留，一并补）；4 个均无 `@main` 值通道，归类属实。

**重跑**：本人重跑 `make test-m6` **rc=0**（`test-m6: PASS (lit full + lli value-level diff + Embench E2E)`）；`diff_ir_lli: PASS`（`hits: 19/19 compared, matched: 19/19`）；Embench **38/38 passed, 0 failed**。本人独立复算结构闭包：on-disk 91 = include 19 + exclude 72，**unclassified=0**、overlap=0、missing=0。

**凑绿核查**：无文件删除、无分类口径放宽（class 复用既有 `no-value-entry`）、include 集合零改动 ⇒ 上轮阻断已按建议修法真实消除，非规避。

**判决**：**Accepted** —— 上轮唯一阻断（ir-lli 账本未登记致 `test-m6` 红）已修复并经我重跑证实；第 1 轮已核的合并正确性、语义 3 例、5 类反例、`math/yn` 归因、9 项验收门控、2 次注入均未被返工触碰（返工仅 1 个账本文件）。遗留 `math/yn`（ISS-332，修法=musl 加 `-ffp-contract=off`）非本册、已登记，建议 architect 按此立项。
