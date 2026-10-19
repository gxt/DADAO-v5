# LLVM-110t: FP 回归 `rb2`（无条件保留）+ `rb63` 回归普通 callee-saved（含 setjmp 端口依赖）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`SPEC-150t`（规范/契约面，**同批**；本册实现须与 `contract-abi §1.3/§4.5/§4.7` 一致）、`ADR-0018`（`C7 D2/D3/D6` 已由 architect 于 2026-10-19 就地修订）、`LLVM-039t`/`LLVM-064t`（现 prologue/epilogue 与 CSR 批量保存实现）、`ISS-280`（本册对应 issue）
**状态**：待开始

## 用户授权（原话逐字，渠道 = 经主会话问答，2026-10-19）

> 「**frame pointer重新改回rb2，且删除fp/gp等别名；可以立**」
> 「**rb2：不做帧指针的时候，建议不做分配，你说呢？**」→（主会话答复「同意无条件保留」）「**好**」

## 问题根源

1. 现行后端按 2026-10-09 的口径：`rb2` 作 GP 保留、`rb63` **条件式**保留（`hasFP` 时作 FP，否则可分配），prologue 用 `rb63` 作帧指针并为其建 **LLVM fixed stack object 专用槽**（`CreateFixedSpillStackObject(8, -8)`）。用户 2026-10-19 裁定回退：`rb2` = FP、**无条件**保留；`rb63` = 普通 callee-saved。
2. 若不改：`-fno-omit-frame-pointer` 下 FP 仍是 `rb63`，与规范/契约矛盾；`rb63` 被错误排除在连续可分配池外；`rb2` 仍被当 GP 保留，与「无条件 FP 保留」名实不符。
3. **跨组件依赖（实测）**：musl/picolibc 的 `setjmp`/`longjmp` 端口按「CSR = rd32–rd63 ∪ rb32–rb63 ∪ rf32–rf63」保存/恢复，注释写「incl. rb63 = FP」。FP 迁回 `rb2` 后，`rb2` 是 callee-saved 的帧指针但**不在 CSR**（保留寄存器），必须在 `jmp_buf` 中**单独**保存/恢复；否则被调函数没有正常返回路径时（longjmp），`rb2` 停在中间帧的值，返回到 `setjmp` 调用者后帧基址错误。**本册必须同批修**，不得留中间态。

## 判据（必须写死）

- **`rb2` 无条件保留**：`getReservedRegs` 中 `Reserved.set(DADAO::rb2)` **无条件**执行；删除 `if (TFI->hasFP(MF)) Reserved.set(DADAO::rb63);` 整块。
- **FP 号**：`getFrameRegister = TFI->hasFP(MF) ? DADAO::rb2 : DADAO::rb1`。
- **`rb63`**：不再有任何条件保留/特殊槽；作为 `rb32`–`rb63` 连续 callee-saved 池的普通成员参与分配与 `stm.o`/`ldm.o` 批量保存。
- **prologue/epilogue**：所有 `rb63` 作 FP 的读写改为 `rb2`；**删除 FP 专用 fixed stack object**（`FPSaveSlotSize`/`FPSaveSlotOffset`/`CreateFixedSpillStackObject`），保存旧 FP 的 8 B 改为在 `determineFrameLayout` 中计入 `StackSize`（hasFP 时），仍以常量 `-8` 显式 `st.o rb2, [rsp, -8]` / `ld.o rb2, [rsp, -8]`；帧大小/其它对象偏移与改前**逐字节一致**。
- **CSR 不变**：`CSR = rd32–rd63 ∪ rb32–rb63 ∪ rf32–rf63`（`rb2` 不在 CSR；作 FP 时由 prologue 保存）。
- **setjmp/longjmp**：`jmp_buf` 增加 1 个 octa 保存 `rb2`（161 → 162），`setjmp` 保存、`longjmp` 恢复；`sigjmp_buf` 的 `__fl` 偏移等派生量同步。
- **补丁树不变**：只改既有 patch 文件内容，`components/*/patches/series` 条目数不变；`check-patch-tree` 仍 **180**。
- **不猜测**：hasFP 判定仍用现有 `TFI->hasFP(MF)`，不要复制条件；`getReservedRegs` 与 `getFrameRegister` 不得出现两套判定。

## 改动清单

### A. LLVM 后端（补丁源，改后须 `make install-host`）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAORegisterInfo.cpp.patch`
  - `getReservedRegs`：`rb2` 无条件 `Reserved.set`；删除 `rb63` 条件块及其注释；更新 CSR/FP 注释（`rb63` 普通成员、`rb2` 无条件 FP 保留）。
  - `getFrameRegister`：`hasFP ? rb2 : rb1`；注释改 `ADR-0018 C7 D3/D6（rev. 2026-10-19）`。
  - `getCalleeSavedRegs`/`getCallPreservedMask` 的 CSR 列表保持 `rb32`–`rb63`（`rb63` 仍在，只是不再有条件语义）。
- `.../DADAOFrameLowering.cpp.patch`
  - `emitPrologue`/`emitEpilogue`：`rb63` → `rb2`；`rb2rb` 帧基址建立/恢复同步。
  - 删除 `FPSaveSlotSize`/`FPSaveSlotOffset` 与 `processFunctionBeforeFrameFinalized` 的 `CreateFixedSpillStackObject` 调用；`determineFrameLayout` 在 `hasFP` 时把 8 B 计入帧大小（与改前 `StackSize` 相同）。
  - 更新文件头与 `emitCalleeSavedRegs` 中「`rb63` 最高编号 / FP 专用槽」注释；`rb32`–`rb63` 整段批量保存合法。
- `.../DADAOFrameLowering.h.patch`：`FP = rb63` 注释 → `rb2`；删除「rb63 条件式」表述。
- `.../DADAORegisterInfo.td.patch`：`RBFP` 别名（`rbfp`）删除；`rb2` 角色注释改 frame pointer（无条件保留）；`rb63` 注释改普通 callee-saved；可分配/保留列表注释同步（`rb2` 不可分配、`rb63` 可分配）。
- `.../MCTargetDesc/DADAOMCTargetDesc.h.patch`：注释中的 `DADAO::RBFP` 删除（`RBFP` 定义已删）。
- `components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.cpp.patch`：`getGCCRegAliases()` 删除 `{{"rbgp"}, "rb2"}` 与 `{{"rbfp"}, "rb63"}` 两项（**删别名**；`rbsp`/`rbtp` 等其它别名保留），注释同步。
- `.../DADAOCallingConv.td.patch`：CSR 注释删「`rb63` 条件式 / FP 专用槽 / 最高编号」段；`rb32`–`rb63` 连续。
- `.../DADAOISelLowering.cpp.patch`：变参快照注释 `rbfp + 8` → `rb2 + 8`（仅注释，语义不变）。
- `.../DADAOInstrInfo.h.patch`、`.../DADAOISelDAGToDAG.cpp.patch`、`.../DADAOCodeGen.td.patch`：仅当 grep 命中「`rb63` = FP / rbfp / 条件式」时同步注释；**编码表/寄存器号表不动**。
- `tests/llvm/lit/CodeGen/DADAO/`：新增 FP 探针（见下），必要时更新 `m6-csr-batch.mir` 注释（其 `CHECK-NOT` 对 `rb63` 的断言仍可保留，但需说明 `rb63` 现在是普通成员、该函数未用到）。

### B. setjmp/longjmp 依赖修复（同批，不改 patch 数量）
- `components/musl/patches/arch/dadao/bits/setjmp.h.patch`：`__jmp_buf[161]` → `[162]`；布局注释新增 `rb2` 槽（建议放在 `rb1` 后或 CSR 块后，全文件一致），`CSR` 注释去掉「incl. rb63 = FP」。
- `components/musl/patches/src/setjmp/dadao/setjmp.S.patch`：保存 `rb2`（`st.o rb2, [rb16, <off>]`），更新头部布局与偏移注释；不改变 `stm.o {rb32:rb63}`。
- `components/musl/patches/src/setjmp/dadao/longjmp.S.patch`：恢复 `rb2`（`ld.o rb2, [rb16, <off>]`），恢复顺序在 `rb1` 之前/之后须与 `setjmp` 布局一致。
- `components/picolibc/patches/libc/include/machine/setjmp.h.patch`：`_JBLEN 161` → `162`，注释同步。
- `components/picolibc/patches/libc/machine/dadao/setjmp.S.patch`：同上保存/恢复 `rb2`，更新偏移与注释。
- `sigsetjmp`（`src/signal/dadao/sigsetjmp.s`）：检查其 `__fl`/`__ss` 偏移是否依赖 161/1288；若有，按 162/1296 同步（grep `1288`、`161`）。

## 探针（必做；每项独立 oracle；证据落 `.work/evidence/LLVM-110t/*`）

1. **`-fno-omit-frame-pointer` 生效**：简单 C（有局部数组/调用）用 `-O1 -fno-omit-frame-pointer -S`；独立 oracle = 汇编中出现 ① `st.o rb2, [rb1, -8]`（或等价保存旧 FP）② `ld.o rb2, ...` ③ `rb2rb rb2, rb1`（FP=entry SP）。改前该形态为 `rb63` ⇒ 改后必须为 `rb2`。
2. **VLA + `alloca` 正确**：C 程序含 VLA 与 `alloca`，编译后 `qemu-dadao` 跑；独立 oracle = 程序自身输出/退出码（如数组元素和/哨兵），不依赖编译器自证。
3. **`rb63` 真被分配到**：构造同函数内 >32 个跨调用存活整数/指针值（或 MIR 直接写 `$rb63` live），检查汇编/MIR 出现 `rb63` 的保存/恢复（`stm.o {..:rb63}` 或 `st.o rb63`）且程序语义正确；改前 `rb63` 条件可分配，改后必须无条件可分配。
4. **大栈帧连续批量保存含 `rb63`**：局部数组 >4 KiB 迫使大帧寻址；断言 `stm.o {rbX:rb63}` / `ldm.o {rbX:rb63}` 连续区间出现（且 `start + immu6 <= 64`），运行结果正确。
5. **旧基线对照**：改前先在 `/tmp/opencode/LLVM-110t/baseline/` 保存同一组 C 语料的 `-O2 -fomit-frame-pointer -S` 汇编与目标码（旧工具链快照）；改后同参数重编，逐文件 `diff` ⇒ **除含 FP 的函数外零差异**（差异白名单 = 保存/恢复 `rb2` 的行）。
6. **setjmp/longjmp 保 `rb2`（依赖核查产物）**：`-fno-omit-frame-pointer` 的 `f()` 调 `setjmp`，中间调 `g()`（hasFP）后 `longjmp`；独立 oracle = `f()` 返回后计算的局部变量/输出与 C 语义一致（如 `volatile` 计数器），且汇编断言 `jmp_buf` 保存/恢复 `rb2`、`_JBLEN`/`__jmp_buf` = 162。**改前应 FAIL**（`rb2` 未被保存），改后 PASS。

## 依赖核查（architect 2026-10-19 实测，engineer 须复核）

- `crt1` / `arch/dadao/crt_arch.h`：**无** `rb63`/`rbfp` 硬引用 ⇒ 不改。
- `components/musl/patches/src/setjmp/dadao/{setjmp.S,longjmp.S}`、`arch/dadao/bits/setjmp.h`：**有** `rb32:rb63` 批量保存 + 注释「incl. rb63 = FP」⇒ 按上「B」改（需加 `rb2` 槽）。
- `components/picolibc/patches/libc/machine/dadao/setjmp.S` + `libc/include/machine/setjmp.h`：同上 ⇒ 按「B」改。
- `tests/**/*.s` 与工具：`rb63` 仅作编号边界/编码用例（`aip-si`、`mreg-range-legality` 等），**不是 FP 语义** ⇒ 不改。
- 结论：**硬用 `rb63` 当 FP 的只有两套 setjmp 端口**，已纳入本册 B 段。

## 接口规范

- **输入**：`SPEC-150t` 的契约文本（`contract-abi §1.3/§4.5/§4.7`）、`ADR-0018` 修订、本册判据与探针。
- **输出**：A/B 两组 patch 改动；`tests/llvm/lit/CodeGen/DADAO/` 新增探针；证据脚本与日志；完成区。
- **约束**：
  - 临时目录 `/tmp/opencode/LLVM-110t/`；禁 `git checkout/restore/stash`（用 `cp` + md5 或临时树）；
  - **改补丁后必须 `make install-host`**（`ISS-210`；禁只重建）；
  - 重建申报：`install-host` + `build-musl`/`build-musl-shared` 预计耗时须先申报；`JOBS=8`、禁全核；长构建 `setsid nohup` + 落 `XXX_EXIT=$rc`；
  - 不 `push`；不跑与本册无关的全量。

## 验收标准

1. **源码形态**：`grep` 断言 `DADAORegisterInfo.cpp` 中 `Reserved.set(DADAO::rb2)` 无条件、`rb63` 条件块 0 处；`getFrameRegister` = `hasFP ? rb2 : rb1`；`DADAOFrameLowering.cpp` 中 `rb63` 作 FP 的读写 0 处、`CreateFixedSpillStackObject` 0 处；`grep -RIn "rbgp\|rbfp" components/llvm-project/patches/llvm/lib/Target/DADAO components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.cpp.patch` = **0 行**（别名彻底删除）。
2. **探针 ①–⑥ 全 PASS**，每项独立 oracle 与改前/改后对照（⑥ 改前 FAIL 证据保留）。
3. **补丁树**：`make check-patch-tree` rc=0、总数仍 **180**；`check-instrinfo` / `check-isa-coverage` / `check-component-changelog` rc=0。
4. **重建后**：`make install-host` rc=0；两档冒烟（`check-qemu-smoke` + `check-qemu-semantics` 或等价两档 E2E）rc=0。
5. **抽样回归**：`TESTCASES-047t` 抽 `functional/setjmp`、`functional/fcntl`、`math/*` 代表性例；`TESTCASES-048t` 抽 `lencod`/`dbms`/`lemon` 相关例；两档无新 `fail`（与改前基线逐例 diff）。
6. **L2/L3**：`make check`(L1) + `make check-modules`(L2) + `make check-full`(L3) rc=0；L3 若因并发禁令不可跑，须在完成区显式说明并用最近一次基线 + 本册定向证据替代。
7. **可达 FAIL**：至少两处注入——① `getFrameRegister` 改回 `rb63` ⇒ 探针①/④ FAIL；② 删 `Reserved.set(rb2)` ⇒ 探针③/①（`rb2` 被分配）FAIL；`cp` + `md5sum` 还原后回绿。
8. **`SPEC-150t` 对齐**：本册完成后，`getReservedRegs`/`getFrameRegister`/`getCalleeSavedRegs` 与 `contract-abi` 逐条一致（完成区列对照表）。
9. 完成区贴真实命令输出 + 退出码（≤30 行）；长日志留 `.work/log/llvm/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
