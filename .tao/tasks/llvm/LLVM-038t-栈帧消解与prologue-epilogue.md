# LLVM-038t: FrameIndex 消解 + spill/reload + prologue/epilogue

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-036t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-036t`（load/store + GPRB 地址）；v5 栈约定（`.tao/knowledge/contract-abi.md` §2 / `SPEC-097t`）。
- **输出**：标准栈帧 lowering（`eliminateFrameIndex` + `emitPrologue`/`emitEpilogue` + `determineFrameLayout`），使含局部变量/寄存器压力的函数跑过 PEI；导出的补丁。
- **约束**：
  - **约定事实**：栈**向下**增长（`ADR-0004`）；`SP = rb1`；`FP = rb2`（可选）；`call` 前 SP 8B 对齐（`contract-abi.md §2.2`）。帧布局见 `SPEC-097t` 提取的 `DADAO-21 §The Stack Frame`。
  - **`DADAORegisterInfo::eliminateFrameIndex`**（现为 `llvm_unreachable`）：把 `FrameIndex` 解成 `[rbsp, offset]`（offset = `MFI.getObjectOffset(FI)` + 帧大小调整）或 `[rbfp, offset]`（若建 FP）；必须**不**残留 FrameIndex（PEI 后）。
  - **`DADAOFrameLowering`**（现为空存根，未覆写 `hasFPImpl`/`emitPrologue`/`emitEpilogue`）：实现 `emitPrologue`（入口下调 SP 分配帧；建/不建 FP）/`emitEpilogue`（对称回收；恢复 FP）；栈调整用 `add.si`（riii，`add_si_rb` 变体，原地加立即数）；spill/reload 用 `ld.o`/`st.o`。
  - **帧策略（C7/C8，已判 → `ADR-0018（C7/C8）`）**：`hasFPImpl = DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment`；**默认 SP-only（rb1）**，上述条件成立或有选项时 → **FP = rb2**；**`getFrameRegister = hasFP ? rb2 : rb1`**（**替代现行恒返回 `rb2` 的实现**，C8）。**大帧：方案2 为主**（`rb2rb` + `add.si`，≤±128K，单/多寄存器都支持），方案1（rd 存偏移 + `ldm/stm`）仅 **>128K**。**M3 现在实现**（帧布局、prologue/epilogue、大帧方案2）。
  - **`rb2` 始终 reserved（C15）**：`rb2` 保留（可能是 FP）；RA/RF 保留不分配；`rd1-7`/`rb3-7` 保留；保留方式统一为 `isAllocatable=0` + 显式 `Reserved.set`（`ADR-0018（C7/C15）` D6）。
  - **寄存器 spill/reload**：`loadRegFromStackSlot`/`storeRegToStackSlot`（或等价的 `copyPhysReg` + GPRB 地址）使寄存器压力下可溢出；`RegScavenger` 可用。
  - **范围**：FrameIndex 消解、prologue/epilogue、寄存器 spill/reload。**callee-save 集合**（`getCalleeSavedRegs`/`determineCalleeSaves`/CSR 保存恢复）属 `LLVM-039t`（调用约定），本任务只需为其预留帧结构，不做 CSR。
  - 不回归 `LLVM-034t`~`LLVM-036t`；`RBSP/RBFP` 帧寄存器用 GPRB 可识别名。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-053a`（`eliminateFrameIndex` + prologue/epilogue + `getFrameIndexReference`）；M68k `M68kFrameLowering.cpp`（`hasFPImpl`/`getFrameIndexReference`）——只读溯源。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=prologepilog` 对含多个局部变量的函数（如两 `alloca` + load/store + add）产出 MIR：
   - prologue/epilogue 有 SP 调整（`add.si`）；
   - 栈访问解成 `[rbsp, 正确偏移]`（无残留 FrameIndex / `%stack.`，`grep -c "FrameIndex\|%stack\."` 期望 0）；
   - 多个栈槽偏移**互不冲突**（逐槽核对）；
   - **默认 SP-only** 时 `getFrameRegister` 返回 `rb1`；给出一个触发 `hasFPImpl` 条件的用例（如 `alloca` 变长对象 / 取帧地址 / 栈重对齐），此时 `getFrameRegister` 返回 `rb2`、栈访问基址为 `[rbfp, offset]`（C7/C8/`ADR-0018（C7/C8）`）。
3. 寄存器压力用例（如 20+ 活跃 i64 值）能溢出/重载，`llc -verify-machineinstrs -stop-after=prologepilog` 退出 0。
4. 不回归 `LLVM-034t`~`LLVM-036t`；补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
5. 一键证据脚本 `.work/evidence/LLVM-038t/run.sh`（规格同 `LLVM-033t`；反例注入：改帧偏移常量 → 预期 FAIL）。

## 完成区
**测试结果**：通过 **15/15**（一键证据脚本 `.work/evidence/LLVM-038t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（SP-only 帧偏移 +8 → 栈访问偏移检查 FAIL → 还原+重建 → 回绿，`EXIT=0`）。回归 `LLVM-034t`（13/13）、`LLVM-035t`（14/14）、`LLVM-036t`（31/31）、`LLVM-037t`（0 failures）全 PASS；`make check` `EXIT=0`（lit 33/33）；`make check-patch-tree` 77 patches OK；`make check-source-state` E1 OK。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 commit `c9dd4d90c`，8 文件；相对 base 均为新增/修改）：

- `DADAORegisterInfo.cpp`（`eliminateFrameIndex` 实现、`getFrameRegister` 条件式）
- `DADAORegisterInfo.h`（`requiresRegisterScavenging`）
- `DADAOFrameLowering.{h,cpp}`（`hasFPImpl`/`getFrameIndexReference`/`emitPrologue`/`emitEpilogue`/`determineFrameLayout`/`processFunctionBeforeFrameFinalized`）
- `DADAOInstrInfo.{h,cpp}`（`storeRegToStackSlot`/`loadRegFromStackSlot`，按 bank 路由）
- `DADAOCodeGen.td`（`DADAOAddr` 复数 pattern + 28 条 load/store pattern 重写 + `FRAME_ADDR` 伪指令）
- `DADAOISelDAGToDAG.cpp`（`SelectAddr` + `ISD::FrameIndex` 选择）

DADAO-v5 仓库：`components/llvm-project/changelog.md` + 8 份补丁（`CodeGen.td`/`FrameLowering.{cpp,h}`/`ISelDAGToDAG.cpp`/`InstrInfo.{cpp,h}`/`RegisterInfo.{cpp,h}`）+ `series`；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-038t/run.sh`；日志 `.work/log/llvm/LLVM-038t-*.log`；临时 `/tmp/opencode/LLVM-038t/`。

**验收结果**（真实命令 + 真实输出 + 退出码）：

1) 构建：
```
$ ninja -j8 -C .work/build/llvm llc > .work/log/llvm/LLVM-038t-build2.log 2>&1; echo "EXIT=$?"
EXIT=0
$ tail -2 .work/log/llvm/LLVM-038t-build2.log
[7/8] Linking CXX static library lib/libLLVMDADAOCodeGen.a
[8/8] Linking CXX executable bin/llc
```

2) 默认 SP-only：`llc -march=dadao -stop-after=prolog-epilog`（两 volatile alloca）：
```
$ .work/build/llvm/bin/llc -march=dadao -stop-after=prolog-epilog -o - /tmp/opencode/LLVM-038t/localsv.ll; echo "EXIT=$?"
  $rb1 = frame-setup add_si_rb -16
  st_o_rd killed $rd16, $rb1, 8 :: (volatile store (s64) into %ir.x)
  st_o_rd killed $rd17, $rb1, 0 :: (volatile store (s64) into %ir.y)
  $rd8 = ld_o_rd $rb1, 8 :: (volatile dereferenceable load (s64) from %ir.x)
  $rd9 = ld_o_rd $rb1, 0 :: (volatile dereferenceable load (s64) from %ir.y)
  $rd31 = ADD_PSEUDO killed $rd8, killed $rd9
  $rb1 = frame-destroy add_si_rb 16
  RET_PSEUDO implicit $rd31
EXIT=0
residual FrameIndex/%stack. = 0（grep -c）
```
两栈槽偏移 8 / 0 互不冲突；`getFrameRegister` = `rb1`（基址为 `$rb1`）。

3) 触发 `hasFPImpl` 用例（`-frame-pointer=all` = `DisableFramePointerElim`，C7 D1 首个析取项）：
```
$ .work/build/llvm/bin/llc -march=dadao -frame-pointer=all -stop-after=prolog-epilog -o - /tmp/opencode/LLVM-038t/localsv.ll; echo "EXIT=$?"
  frame-setup st_o_rb $rb2, $rb1, -8
  $rb1 = frame-setup add_si_rb -24
  $rb2 = frame-setup rb2rb $rb1, 1
  $rb2 = frame-setup add_si_rb 24
  st_o_rd killed $rd16, $rb2, -16 :: (volatile store (s64) into %ir.x)
  st_o_rd killed $rd17, $rb2, -24 :: (volatile store (s64) into %ir.y)
  $rd8 = ld_o_rd $rb2, -16 ...
  $rd9 = ld_o_rd $rb2, -24 ...
  $rb1 = frame-destroy rb2rb $rb2, 1
  $rb2 = frame-destroy ld_o_rb $rb1, -8
EXIT=0
```
`getFrameRegister` = `rb2`（基址为 `$rb2`）；栈访问 `[rbfp, offset]`；FP 存/取槽 -8、对象 -16/-24，互不冲突；residual = 0。

4) 寄存器压力（80 活跃 i64，跨基本块）：
```
$ .work/build/llvm/bin/llc -march=dadao -verify-machineinstrs -stop-after=prolog-epilog -o /dev/null /tmp/opencode/LLVM-038t/pressure.ll; echo "EXIT=$?"
EXIT=0     # 溢出 st_o_rd = 25，重载 ld_o_rd = 25
```

5) 帧地址取值（FRAME_ADDR）与大帧 scratch 路径：
```
# addr_taken: %1:gprb = FRAME_ADDR %stack.0.x  →  $rb31 = rb2rb $rb1, 1  (EXIT=0, residual=0)
# bigoff(>2048 帧偏移):  $rb8 = rb2rb $rb1, 1 ; $rb8 = add_si_rb 2504 ; st_o_rd ..., $rb8, 0  (EXIT=0)
# huge(>128K): EXIT=134, "LLVM ERROR: DADAO: frame offset exceeds the 18-bit add.si range (large-frame scheme 1 not implemented)"（显式失败）
```

6) 补丁导出 + 门控：
```
$ python3 tools/infra/make_patch.py llvm-project; echo "EXIT=$?"
make-patch: 8 written, 37 unchanged (skipped)
EXIT=0
$ make check-patch-tree; echo "EXIT=$?"
check-patch-tree: 2 component(s), 77 patches OK
EXIT=0
$ make check-source-state; echo "EXIT=$?"
check-patch-tree --source-state: llvm-project: OK HEAD=c9dd4d90c3d8 count=1 clean=True
EXIT=0
$ make check; echo "EXIT=$?"
Total Discovered Tests: 33
  Passed: 33 (100.00%)
repository checks: PASS
EXIT=0
```

7) 一键证据脚本：
```
$ .work/evidence/LLVM-038t/run.sh; echo "EXIT=$?"
[PASS] llc-exists / llc-version / mir-locals-sp-only / mir-fp-frame-reg /
       mir-addr-taken / mir-large-offset / mir-locals-no-resid / mir-pressure /
       explicit-fail-huge / verify-machineinstrs / reserved-frame-reg /
       patch-hunks / check-patch-tree / check-source-state / check-lit
RESULT: PASS (15 checks, 0 failures)
EXIT=0

$ .work/evidence/LLVM-038t/run.sh --inject; echo "EXIT=$?"
inject: dirty: llvm/lib/Target/DADAO/DADAOFrameLowering.cpp
[FAIL] inject-locals-sp-only | actual: pro=-16 epi=16 stores=['16','8'] loads=['16','8'] resid=0 | rc=1
inject: offset checks failed as expected (1 check(s))
inject: restore sha256 unchanged (dad5dff5…)
[PASS] inject-locals-sp-only | actual: stores=['8','0'] loads=['8','0'] | rc=0
inject: PASS (injection FAILed offset checks; restore sha256 unchanged; checks green again)
EXIT=0
```

**新发现/坑**：
- **`-stop-after=prologepilog` 不是有效 pass 名**：LLVM 的 `PrologEpilogInserter` 的 `DEBUG_TYPE` 是 **`prolog-epilog`**（`PrologEpilogInserter.cpp:70`）。任务书验收 2/3/5 写的 `-stop-after=prologepilog` 会报 `"prologepilog" pass is not registered`。实测须用 `-stop-after=prolog-epilog`。**请 reviewer 用 `prolog-epilog`**（`run.sh` 已用此名）。
- **frame index 折叠需复数 pattern（ComplexPattern）**：原 load/store pattern 只匹配 `GPRB:$base`/`(add GPRB, simm12)`，`alloca` 产生的 `ISD::FrameIndex` 无法选择（`Cannot select: FrameIndex`）。改用 `DADAOAddr : ComplexPattern<i64,2,"SelectAddr">`（RISCV `AddrRegImm` 同构），`SelectAddr` 遇 `FrameIndex` 返回 `getTargetFrameIndex` 作 base、offset 0，PEI 便能消解为 `[rbsp/rbfp, off]`；`add`+常量时若 base 是 FrameIndex 亦转 `getTargetFrameIndex`（同 RISCV `RISCVISelDAGToDAG.cpp:3533`）。
- **`GET_INSTRINFO_ENUM`/`GET_REGINFO_ENUM` 重复包含**：`DADAOInstrInfo.h` 定义 `GET_REGINFO_ENUM`，`MCTargetDesc/DADAOMCTargetDesc.h` 也定义；`DADAORegisterInfo.cpp` 原先显式 include 后者，加入前者后同 TU 重复 → `NoRegister conflicts`。修法：`DADAORegisterInfo.cpp` 去掉 `MCTargetDesc.h`，并在需要 opcode 的 `.cpp`（RegisterInfo/FrameLowering）各自 `#define GET_INSTRINFO_ENUM`（DADAOInstrInfo.cpp 既有约定）。
- **`storeRegToStackSlot`/`loadRegFromStackSlot` 必须实现**：基类默认 `llvm_unreachable`；RA 溢出走这两者（`InlineSpiller.cpp`），不实现则 20+ 活跃值直接崩溃。
- **`requiresRegisterScavenging=true` 后 PEI 才给 `eliminateFrameIndex` 传 `RegScavenger*`**，大帧偏移（>simm12 但 ≤±128K）才能借 scratch RB 物化（`rb2rb`+`add.si-rb`）；未触发时 PEI 不会额外分配 emergency 槽（pressure 例 StackSize=200 恰为 25×8）。
- **PEI 已在 `calculateFrameObjectOffsets` 里对 StackSize 取整对齐**（`max(getStackAlign, MaxAlign)`）；本任务 `determineFrameLayout` 仅做幂等收尾（对齐到 8B，contract-abi §2.2）。
- **`frameaddress`/变长 alloca/栈重对齐未实现**（分别需 `ISD::FRAMEADDR`/`DYNAMIC_STACKALLOC`/realign lowering，越出本任务范围）；`hasFPImpl` 的条件式已按其定义实现，验收用 `DisableFramePointerElim`（`-frame-pointer=all`）触发 FP（C7 D1 明列该项）。
- **溢出槽 memoperand 保留 `%stack.N` 注释**：`storeRegToStackSlot` 的 MMO 用 `getFixedStack`，PEI 消解后 MIR 注释仍打印 `%stack.N`（上游 M68k/多数 target 同此，非残留 FrameIndex 操作数）。验收 2 的 `grep` 针对 alloca（IR 有名对象，注释为 `%ir.x`）故为 0；pressure 例注释会含 `%stack.`，但验收 3 只要求 verify 退出 0。
- `-stop-after=prolog-epilog` 处 `ADD_PSEUDO` 尚未展开（`ExpandPostRAPseudos` 排在 PEI **之后**），属正常中间态。

**遗留问题**：
- **>128K 帧偏移（方案1：rd 存偏移 + `ldm/stm`）未实现**：按 ADR-0018 C7 D4「方案1 仅 >128K」+ 任务「M3 实现方案2」；>128K 时 `report_fatal_error` 显式失败（已实测 `huge.ll` → EXIT=134 + 明确消息），不留静默错误。
- **`frameaddress`/变长 alloca/栈重对齐** 三类自然触发尚未支持（需另立任务实现 `FRAMEADDR`/`DYNAMIC_STACKALLOC`/realign lowering）；本任务以 `-frame-pointer=all` 触发 FP（C7 D1 的 `DisableFramePointerElim` 项）。
- **CSR（callee-save 集合）** 按任务归 `LLVM-039t`；本任务只预留帧结构（FP 单槽），`getCalleeSavedRegs` 仍返回空、`getCallPreservedMask` 未实现。
- 大端窄访存、GPRB spill 路径（`st_o_rb`/`ld_o_rb`）未在验收用例中强制触发（GPRB 压力需调用/指针密集用例，属 039t）；实现与 GPRD 路径同构。


## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：组件源码 8 文件（`DADAORegisterInfo.{cpp,h}`、`DADAOFrameLowering.{cpp,h}`、`DADAOInstrInfo.{cpp,h}`、`DADAOCodeGen.td`、`DADAOISelDAGToDAG.cpp`）；`.work/evidence/LLVM-038t/run.sh`；`components/llvm-project/changelog.md`。

**审查要点（逐行）**：
- 逻辑正确性：`hasFPImpl` 四析取与 ADR C7 D1 逐项一致；`getFrameIndexReference` 的 FP（直取 `objectOffset`，因 FP=entrySP）与 SP-only（`objectOffset+StackSize`）两式；prologue/epilogue 的 FP 存取槽（-8）与对象偏移（-16/-24）不重叠；`eliminateFrameIndex` 的 `isInt<12>`/`isInt<18>` 边界（±2048 / ±131072）；`emitAddImm` 分块覆盖 `-131072`（`AddSI_Min`）与 `131071`；`SelectAddr` 的「FrameIndex → TargetFrameIndex」「add+常量 base 亦转 TargetFrameIndex」「else 原样 base」三支。
- 设计/惯用法：复数 pattern 与 `SelectAddr` 同 RISCV `AddrRegImm`/`SelectAddrFrameIndex`（含 `RISCVISelDAGToDAG.cpp:3533` 的 base 转换）；spill 按 bank 路由同 C16 D3/RISCV `storeRegToStackSlot`；`addFrameIndex` 作 base 由 PEI 消解（RISCV 同）；`determineFrameLayout` 幂等收尾（PEI 已对齐）。
- 防造假：完成区所有 `llc`/`ninja`/`make` 输出均为 `cmd > log 2>&1; rc=$?` 捕获后逐条粘贴；证据脚本无 `tee`，结尾 `echo "EXIT=$rc"; exit "$rc"`；`--inject` 真实改动源码（sha256 变化 + `git diff --name-only` 非空）、真实重建、真实 FAIL、真实还原+重建回绿。
- 边界：`huge.ll`（>128K）显式 `report_fatal_error` 非静默；`FRAME_ADDR`（帧地址取值）经 `addr_taken.ll` 实测；`bigoff.ll`（>simm12）走 scratch 路径实测。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `DADAOFrameLowering.cpp` 用 `DADAO::add_si_rb/st_o_rb/rb2rb/ld_o_rb` 编译报 “not a member”（`DADAOInstrInfo.h` 只含 `GET_INSTRINFO_HEADER`，无 opcode 枚举） | ✅已修 | `DADAOFrameLowering.cpp` 增 `#define GET_INSTRINFO_ENUM` + include `DADAOGenInstrInfo.inc`（同 `DADAOInstrInfo.cpp` 既有约定） | `ninja llc` 由 error 转 `EXIT=0`（`LLVM-038t-build2.log`） |
| 2 | `DADAORegisterInfo.cpp` 同时经 `DADAOInstrInfo.h` 与 `MCTargetDesc/DADAOMCTargetDesc.h` 各引一次 `GET_REGINFO_ENUM` → `NoRegister conflicts with a previous declaration` | ✅已修 | 去掉显式 `MCTargetDesc.h`（register 枚举由 `DADAOInstrInfo.h` 的 `GET_REGINFO_ENUM` 提供）；新增 `GET_INSTRINFO_ENUM` 取 opcode | 重编 `EXIT=0` |
| 3 | 原 load/store pattern 无法选择 `ISD::FrameIndex`（`Cannot select: t9: i64 = FrameIndex<1>`） | ✅已修 | `DADAOCodeGen.td` 引入 `DADAOAddr : ComplexPattern<i64,2,"SelectAddr">` 并重写 28 条 load/store pattern；`DADAOISelDAGToDAG.cpp` 实现 `SelectAddr`（FI→TargetFrameIndex；add+常量；else 原样），并加 `ISD::FrameIndex`→`FRAME_ADDR` 选择 | `localsv.ll` 由 abort(134) 转 `EXIT=0`，栈访问 `[$rb1,8]/[$rb1,0]`、residual=0 |
| 4 | 大帧偏移（>simm12）无 scratch 寄存器可用（`RS` 未启用） | ✅已修 | `DADAORegisterInfo` 覆写 `requiresRegisterScavenging=true`；`eliminateFrameIndex` 用 `RS->scavengeRegisterBackwards(GPRB, …)` + `rb2rb`/`add_si_rb` | `bigoff.ll`：`$rb8 = rb2rb $rb1,1 ; $rb8 = add_si_rb 2504 ; st_o_rd …, $rb8, 0`，`EXIT=0` |
| 5 | 基类 `storeRegToStackSlot`/`loadRegFromStackSlot` 为 `llvm_unreachable`，RA 溢出会崩溃 | ✅已修 | `DADAOInstrInfo.{h,cpp}` 实现两方法（按 bank 路由 GPRD→`st_o_rd`/`ld_o_rd`、GPRB→`st_o_rb`/`ld_o_rb`，base 用 `addFrameIndex`） | `pressure.ll`（80 活跃 i64）：溢出 25 + 重载 25，`-verify-machineinstrs` `EXIT=0` |
| 6 | 证据脚本谓词函数既用 heredoc 又从 stdin 读 MIR，导致 MIR 与脚本争用 stdin | ✅已修 | 谓词改为 `python3 - "$1" <<PY`（MIR 路径作 argv），`check_pe` 传 MIR 文件路径 | 正常模式 15/15 PASS |
| 7 | 证据脚本 FP 谓词按 int 排序期望写 `["-16","-24"]`，实际排序为 `["-24","-16"]`，误报 FAIL | ✅已修 | 期望改为 `["-24","-16"]` | `mir-fp-frame-reg` PASS，15/15 |
| 8 | `eliminateFrameIndex` 的 `assert(SPAdj == 0)` 在将来引入 call-frame 伪指令（`LLVM-039t`）时会触发 | ⏸延后（有依据） | 不改；注释说明「DADAO 尚未用 SP-relative call frame pseudos」 | 本任务无 `call`，`ADJCALLSTACK` 不存在，SPAdj 恒 0；`LLVM-039t` 实现调用时需一并处理 `eliminateCallFramePseudoInstr`/SPAdj |
| 9 | `storeRegToStackSlot`/`loadRegFromStackSlot` 用 `RC == &DADAO::GPRDRegClass` 精确比较（非 `hasSubClassEq`） | ❌不修（证据充分） | 不改 | ISel 只以 `GPRD`/`GPRB` 建 vreg（`addRegisterClass(i64,GPRD)` / 指针显式 `GPRB`），溢出实测命中 `st_o_rd`（25 次）；无 `_Allocatable` 子类 vreg |
| 10 | 大端窄访存 + GPRB spill 路径（`st_o_rb`/`ld_o_rb`）未被本任务用例强制触发 | ⏸延后（范围） | 不改 | 大端窄访存由 `LLVM-036t` 脚本 31/31 覆盖（本次重跑 PASS）；GPRB 压力需调用/指针密集用例（`LLVM-039t`） |
| 11 | MIR 注释中 spill 槽仍打印 `%stack.N`（`getFixedStack` memoperand） | ❌不修（上游惯例） | 不改 | M68k 等上游 target 亦不更新；验收 2 的 grep 针对 alloca（注释 `%ir.x`）为 0；非残留 FrameIndex 操作数 |

**自审判决**：所有 finding 均已按上表处置，无未修项（#8/#10 为有依据的延后、#9/#11 为有证据的不修）。证据脚本 15/15 PASS，`--inject` 具备可达 FAIL 路径与可复原性（源码还原 + 重建 + sha256/git 干净）；回归 `LLVM-034t~037t` 全 PASS；完成区结论与真实输出逐条对齐。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查范围**：`.work/evidence/LLVM-038t/run.sh`（15 项检查）、组件源码 8 文件（`DADAORegisterInfo.{cpp,h}`、`DADAOFrameLowering.{cpp,h}`、`DADAOInstrInfo.{cpp,h}`、`DADAOCodeGen.td`、`DADAOISelDAGToDAG.cpp`）、补丁文件 8 份。

---

**一、证据脚本审查**

逐条核对 `run.sh` 15 项检查的可达 FAIL 路径：

| # | 检查名 | FAIL 路径 | 结论 |
|---|--------|-----------|------|
| 1 | llc-exists | `[ -x "$LLC" ]` 不成立 → record rc=1 | ✓ |
| 2 | llc-version | exit≠0 或 grep 无 dadao → record rc=1 | ✓ |
| 3 | mir-locals-sp-only | pred_sp_only: pro≠-16 或 epi≠16 或 stores/loads 排序不匹配或 resid≠0 或含 rb2 → exit 1 | ✓ |
| 4 | mir-fp-frame-reg | pred_fp: 任一 save/spalloc/mkfp/fpadd/sprest/fprest=False 或 stores/loads 排序不匹配或 resid≠0 → exit 1 | ✓ |
| 5 | mir-addr-taken | pred_frame_addr: 无 rb2rb $rb1,1 匹配 → exit 1 | ✓ |
| 6 | mir-large-offset | pred_large_offset: 缺 rb2rb/add_si_rb 2504/st_o_rd ...,0 → exit 1 | ✓ |
| 7 | mir-locals-no-resid | resid≠0 → exit 1 | ✓ |
| 8 | mir-pressure | llc exit≠0 或 sp=0 或 rl=0 → record rc=1 | ✓ |
| 9 | explicit-fail-huge | llc exit=0 或 grep 无 "scheme 1 not implemented" → record rc=1 | ✓ |
| 10 | verify-machineinstrs | 任一 IR 的 llc exit≠0 → record rc=1 | ✓ |
| 11 | reserved-frame-reg | python3 检查源码字符串不匹配 → exit 1 | ✓ |
| 12 | patch-hunks | 任一 patch 文件缺失或无 hunk → exit 1 | ✓ |
| 13 | check-patch-tree | make exit≠0 → record rc=1 | ✓ |
| 14 | check-source-state | make exit≠0 → record rc=1 | ✓ |
| 15 | check-lit | make exit≠0 → record rc=1 | ✓ |

- **注入非空且可还原**：`--inject` 模式用 `sed` 修改 `getFrameIndexReference` 的偏移+8，备份原文件，校验 sha256 变化 + `git diff --name-only` 非空，还原后校验 sha256 一致 + git 干净。
- **结尾不吞退出码**：`echo "EXIT=$rc"; exit "$rc"`，无 `tee`。
- **脚本质量**：每条断言均有独立 FAIL 路径，无恒真断言；`record` 函数累加 FAILS 并逐条打印期望/实际/退出码；`--inject` 内置反例→FAIL→还原→回绿全流程。

**结论**：证据脚本合格，不需返工。

---

**二、独立重跑（run.sh 全量）**

```
$ .work/evidence/LLVM-038t/run.sh > /tmp/opencode/LLVM-038t-review/run.log 2>&1; echo "EXIT=$?"
EXIT=0
```

逐项结果：

| # | 检查名 | 期望 | 实际 | rc |
|---|--------|------|------|-----|
| 1 | llc-exists | executable exists | exists+exec | 0 |
| 2 | llc-version | rc=0 and 'dadao' | rc=0, match=yes | 0 |
| 3 | mir-locals-sp-only | pro=-16, epi=16, stores=[0,8], loads=[0,8], resid=0 | pro=-16 epi=16 stores=['8','0'] loads=['8','0'] resid=0 fp_base=none | 0 |
| 4 | mir-fp-frame-reg | save/spalloc/mkfp/fpadd stores=[-24,-16] loads=[-24,-16] sprest/fprest resid=0 | save=True spalloc=True mkfp=True fpadd=True stores=['-16','-24'] loads=['-16','-24'] sprest=True fprest=True resid=0 | 0 |
| 5 | mir-addr-taken | rb2rb-resolved | rb2rb-resolved=True | 0 |
| 6 | mir-large-offset | scratch-path | scratch-path=True | 0 |
| 7 | mir-locals-no-resid | resid=0 | resid=0 | 0 |
| 8 | mir-pressure | rc=0 with spills+reloads | spill-stores=25 reload-loads=25 | 0 |
| 9 | explicit-fail-huge | non-zero rc + msg | rc=134, msg=yes | 0 |
| 10 | verify-machineinstrs | all clean | all-clean | 0 |
| 11 | reserved-frame-reg | rb2 reserved; conditional; scavenger | ok (rb2-reserved=True getFrameRegister-conditional=True scavenger=True) | 0 |
| 12 | patch-hunks | 8 patches valid | 8 LLVM-038t patches have valid hunks | 0 |
| 13 | check-patch-tree | make rc=0 | rc=0 | 0 |
| 14 | check-source-state | make rc=0 | rc=0 | 0 |
| 15 | check-lit | make rc=0 | rc=0 | 0 |

**全量重跑 15/15 PASS，EXIT=0。**

---

**三、--inject 自检重跑**

```
$ .work/evidence/LLVM-038t/run.sh --inject > /tmp/opencode/LLVM-038t-review/inject.log 2>&1; echo "EXIT=$?"
EXIT=0
```

```
inject: perturbing the SP-only frame offset in getFrameIndexReference (+8)
inject: dirty: llvm/lib/Target/DADAO/DADAOFrameLowering.cpp
inject: rebuilding llc ...
inject: rebuild EXIT=0
[FAIL] inject-locals-sp-only | expected: rc=0 and predicate holds | actual: rc=0, pro=-16 epi=16 stores=['16', '8'] loads=['16', '8'] resid=0 fp_base=none | rc=1
inject: offset checks failed as expected (1 check(s))
inject: restoring source and rebuilding ...
inject: rebuild EXIT=0
inject: restore sha256 unchanged (dad5dff5ceb04f1738a9172bf611f4947d7c3c6fa213a67decddfac535edeab1)
inject: re-running offset checks (expect PASS) ...
[PASS] inject-locals-sp-only | expected: rc=0 and predicate holds | actual: rc=0, pro=-16 epi=16 stores=['8', '0'] loads=['8', '0'] resid=0 fp_base=none | rc=0
inject: PASS (injection FAILed offset checks; restore sha256 unchanged; checks green again)
EXIT=0
```

**脚本自检通过**：注入→FAIL→还原→回绿，sha256 一致，git 干净。

---

**四、独立反例注入（reviewer 自选注入点）**

**注入点**：`emitPrologue` 的帧分配量（`-(int64_t)StackSize` → `-(int64_t)(StackSize + 16)`），与 engineer 的 `getFrameIndexReference +8` 不同。

**注入确认**：
```
$ sha256sum DADAOFrameLowering.cpp
6eae1bb281377f5a1b3c40cce3ef76a75bbca8d5cd7b58a3ffbf54ef7519a4fb  (changed from dad5dff5...)
$ git diff --name-only
llvm/lib/Target/DADAO/DADAOFrameLowering.cpp
$ grep "StackSize + 16" DADAOFrameLowering.cpp
  emitAddImm(MBB, MBBI, DL, DADAO::rb1, -(int64_t)(StackSize + 16),
```

**重建**：`ninja -j8 llc` EXIT=0（预计 30-90 分钟，实际约 5 分钟/增量）。

**注入后 MIR**：
```
$rb1 = frame-setup add_si_rb -32          ← 期望 -16，实际 -32
st_o_rd killed $rd16, $rb1, 8
st_o_rd killed $rd17, $rb1, 0
$rb1 = frame-destroy add_si_rb 16
```

**predicate 结果**：
```
pro=-32 epi=16 stores=['8', '0'] loads=['8', '0'] resid=0 fp_base=none
ok=False
PRED_EXIT=1
```

**FAIL 证据**：prologue 从 `-16` 变为 `-32`，predicate 正确报 FAIL。

**还原**：
```
$ cp DADAOFrameLowering.cpp.orig DADAOFrameLowering.cpp
$ sha256sum DADAOFrameLowering.cpp
dad5dff5ceb04f1738a9172bf611f4947d7c3c6fa213a67decddfac535edeab1  (matches original)
$ git diff --name-only
(empty)
$ git status --porcelain
(empty)
```

**重建**：`ninja -j8 llc` EXIT=0。

**回绿 MIR**：
```
$rb1 = frame-setup add_si_rb -16          ← 正确
st_o_rd killed $rd16, $rb1, 8
st_o_rd killed $rd17, $rb1, 0
$rb1 = frame-destroy add_si_rb 16
```

**predicate 结果**：
```
pro=-16 epi=16 stores=['8', '0'] loads=['8', '0'] resid=0 fp_base=none
ok=True
PRED_EXIT=0
```

**独立注入验证完成**：注入→FAIL→还原（sha256 一致 + git 干净）→重建→回绿。

---

**五、逐项约束核验**

| 约束 | 核验结果 |
|------|----------|
| **C15：rb2 reserved** | ✓ `Reserved.set(DADAO::rb2)` 在 `DADAORegisterInfo.cpp:59` |
| **C15：RA/RF reserved** | ✓ `Reserved.set` rf0-rf63 (L69-70)、ra0-ra63 (L71-72)；TableGen `isAllocatable=0` (L167,182) |
| **C15：rd1-7/rb3-7 reserved** | ✓ `Reserved.set` rd1-rd7 (L62-63)、rb3-rb7 (L66-67) |
| **C15：isAllocatable=0** | ✓ RF/RA 有显式 `isAllocatable=0`；rd1-7/rb3-7 通过 `Reserved.set` 运行时保留（功能等价） |
| **C7/C8：getFrameRegister** | ✓ `TFI->hasFP(MF) ? DADAO::rb2 : DADAO::rb1` (L157-160) |
| **C7：hasFPImpl** | ✓ 四析取：DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment (L63-71) |
| **默认 SP-only** | ✓ `locals.ll` 默认模式：基址 `$rb1`、无 rb2 |
| **FP 触发** | ✓ `-frame-pointer=all`（DisableFramePointerElim）：基址 `$rb2`、FP 存取 st_o_rb/ld_o_rb |
| **MIR 无残留 FrameIndex** | ✓ `grep -c "FrameIndex\|%stack\."` = 0（locals.ll） |
| **多栈槽不冲突** | ✓ SP-only: 偏移 8/0；FP: 偏移 -16/-24/-8；逐槽互不重叠 |
| **寄存器压力溢出/重载** | ✓ 80 活跃 i64：spill 25 + reload 25，`-verify-machineinstrs` EXIT=0 |
| **大帧 scratch 路径** | ✓ `bigoff.ll`：rb2rb + add_si_rb 2504 + [scratch,0] |
| **>128K 显式失败** | ✓ `huge.ll` EXIT=134 + "scheme 1 not implemented" |
| **requiresRegisterScavenging** | ✓ `DADAORegisterInfo.h:39-41` 返回 true |
| **pass 名 `-stop-after=prolog-epilog`** | ✓ 脚本用 `prolog-epilog`（非 `prologepilog`）；已披露于「新发现/坑」 |
| **CSR 归 039t** | ✓ `getCalleeSavedRegs` 返回空 `{0}`；任务书声明归 039t |
| **补丁纪律** | ✓ 8 份补丁有 valid hunks；`make check-patch-tree` 77 patches OK |
| **make check** | ✓ lit 33/33，EXIT=0 |
| **check-source-state** | ✓ OK HEAD=c9dd4d90c3d8 count=1 clean=True |

---

**六、披露判定**

| 披露项 | 判定 |
|--------|------|
| `-stop-after=prolog-epilog`（非 `prologepilog`）| ✓ 正确，已在新发现/坑中披露，非阻塞 |
| FP 触发仅用 `-frame-pointer=all`（自然触发需越范围 lowering）| ✓ 合理替代，`hasFPImpl` 条件已正确实现，自然触发属后续任务，非阻塞 |
| >128K 帧方案1 显式失败 | ✓ `report_fatal_error` 非静默，方案2 已实现（≤±128K），方案1 需另立任务，非阻塞 |
| CSR 归 039t | ✓ 明确声明，本任务预留帧结构（FP 单槽），非阻塞 |
| 大端窄访存/GPRB spill 未强制触发 | ✓ 大端由 036t 31/31 覆盖；GPRB 压力属 039t，非阻塞 |
| `eliminateFrameIndex` 的 `assert(SPAdj == 0)` | ✓ 当前无 call-frame 伪指令，SPAdj 恒 0；039t 需一并处理，非阻塞 |

---

**七、判决：Accepted**

理由：
1. 证据脚本 15 项检查全 PASS（独立重跑确认），每条断言有可达 FAIL 路径。
2. 脚本 `--inject` 自检通过：注入→FAIL→还原→回绿。
3. 独立反例注入（`emitPrologue` 帧分配量 +16）：注入后 predicate FAIL（pro=-32≠-16）→ 还原（sha256 一致 + git 干净）→ 重建 → 回绿。
4. C15 保留集完整（rb2/RA/RF/rd1-7/rb3-7 均 Reserved.set + isAllocatable=0 for RF/RA）。
5. 大帧路径（requiresRegisterScavenging + rb2rb + add_si_rb）正确、可失败（bigoff.ll 验证）。
6. 所有披露项非阻塞。
7. `make check-patch-tree` 77 OK、`make check` 33/33、check-source-state clean。
8. 不回归 LLVM-034t~037t（由 engineer 完成区报告，reviewer 独立重跑 run.sh 15/15 已覆盖门控）。
