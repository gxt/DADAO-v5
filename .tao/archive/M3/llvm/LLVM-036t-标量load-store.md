# LLVM-036t: 标量 load/store

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-034t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-034t`（GPRB 地址 bank + 跨 bank 搬运）；v5 指令定义。
- **输出**：标量 load/store 的 ISel pattern（GPRB base + 12 位偏移），覆盖各访存宽度；导出的补丁。
- **约束**：
  - **指令事实（实测，`DADAOInstrInfo.td`）**：
    - 装载 rrii：`ld.o rd, [rb, imm12]`（64 位）、`ld.ut`/`ld.st`（tetra 零/符号扩展）、`ld.uw`/`ld.sw`（wyde）、`ld.ub`/`ld.sb`（byte）——`(outs GPRD:$ra) (ins GPRB:$rb, imms12:$imm12)`。
    - 存储 rrii：`st.o/st.t/st.w/st.b rd, [rb, imm12]`——`(ins GPRD:$ra, GPRB:$rb, imms12:$imm12)`。
    - 地址 = `rb[47:0] + sign_extend(imm12)`（`contract-isa.md §4`；RB 全 64 位、访存取低 48 位，C14/`ADR-0018（C14）` D3）；负偏移/大偏移需 base 先算（GPRB 算术，`add.o`（orrr，rb 目的；旧名 `add.so-rb`，见 `adr-0012 D9`）/`add.si`，C14/`ADR-0018（C14）` D1）。
    - **大端窄访存（C13，`ADR-0018（C13）` D2）**：byte/wyde/tetra 装载按大端语义；`ld.ub/uw/ut` 零扩展、`ld.sb/sw/st` 符号扩展，结果写满 64 位（`SPEC-069t` 值语义）。**须显式保证/测试** `ReduceLoadWidth` 类 combine 的**字节偏移**（大端下窄 load 的字节偏移与掩码，0628 `DL-068a` silent miscompile 教训）。
  - **必须**：给对应 format class（`DADAORrii` 的 load/store 子类）加 `mayLoad`/`mayStore`（`DADAOInstrInfo.td` 现**无** `mayLoad`/`mayStore`——实测 grep 计数 0）；新增 `Pattern`：`(load (addr))`→`ld.*`、`(store val, addr)`→`st.*`；地址匹配支持 `base + simm12` 偏移。
  - **范围**：标量 i8/i16/i32/i64 及 `ptr` 的 load/store。**不含** FrameIndex 栈槽（→`LLVM-038t`）、全局符号地址（→M4）。本任务用「参数指针 + 常量偏移」验证。
  - 不回归 GPRD/GPRB/算术 MIR（`LLVM-034t`/`LLVM-035t`）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-051a`（zero-offset load/store pattern + `copyPhysReg`）/`DL-052a`（带偏移）；`DL-068a`（大端窄装载掩码）——只读溯源。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 真实 MIR：
   - `define i64 @ld(ptr %p){ %v=load i64, ptr %p  ret i64 %v }` → 含 `ld.o` MI + GPRB 地址；
   - `define void @st(ptr %p, i64 %v){ store i64 %v, ptr %p  ret void }` → 含 `st.o` MI + GPRB 地址；
   - 带偏移（`getelementptr i64, ptr %p, i64 2`）→ `ld.o ..., 16`（非零 imm12）；
   - 窄宽度（`load i8`/`i32`）→ 对应 `ld.ub`/`ld.ut`/`ld.st` 等 + 正确扩展；**大端窄访存须给出字节偏移/掩码的显式核对**（C13/`ADR-0018（C13）` D2，0628 `DL-068a` 教训）。
3. `llc -verify-machineinstrs -stop-after=finalize-isel` 退出 0。
4. 补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
5. 一键证据脚本 `.work/evidence/LLVM-036t/run.sh`（规格同 `LLVM-033t`；反例注入：改 imm12 或 pattern → 预期 FAIL）。

## 完成区

**测试结果**：通过 **31/31**（一键证据脚本 `.work/evidence/LLVM-036t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（把 `simm12imm` 的 `isInt<12>` 收紧为 `isInt<0>` → 重建 → 4 条偏移检查 FAIL → 还原 + 重建 → 回绿；源码 sha256 一致、`git status` 干净）。`make check` `EXIT=0`（lit 33/33）；`make check-patch-tree` 77 patches OK；`make check-source-state` OK（`HEAD=01819ba79957 count=1 clean=True`）；`make check-instrinfo` 0 errors。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 = `01819ba7995755dd1af0ddd3aa2fd03ff9b8eb78`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`；共 3 文件修改）：
- `llvm/lib/Target/DADAO/DADAOInstrInfo.td`：给 15 条 rrii load/store def 加 `mayLoad`（9 条 `ld.*`）/`mayStore`（6 条 `st.*`）——此前全 target 0 处。
- `llvm/lib/Target/DADAO/DADAOCodeGen.td`：新增 `simm12imm` ImmLeaf + 28 条 load/store pattern（`ld.o`/`st.o` 的零偏移与 base+simm12；i8/i16/i32 的 `extload`/`zextload`/`sextload` 与 `truncstore`）。
- `llvm/lib/Target/DADAO/DADAOISelLowering.cpp`：构造函数把 i8/i16/i32 的 `EXTLOAD/SEXTLOAD/ZEXTLOAD`（→i64）与 `truncstore`（i64→i8/i16/i32）标 `Legal`，使窄访存节点到达 ISel。

DADAO-v5 仓库：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOCodeGen.td,DADAOISelLowering.cpp,DADAOInstrInfo.td}.patch`（由 `tools/infra/make_patch.py llvm-project` 从真实源导出，未手改）+ `components/llvm-project/changelog.md`；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-036t/run.sh`；日志 `.work/log/llvm/LLVM-036t-*.log`；临时 `/tmp/opencode/LLVM-036t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`；完整 log `.work/log/llvm/LLVM-036t-acceptance.log`）：

1. **构建（验收 1）**：`ninja -j8 -C .work/build/llvm llc` → `BUILD_EXIT=0`（`[16/16] Linking CXX executable bin/llc`；log `.work/log/llvm/LLVM-036t-build2.log`）。

2. **真实 MIR（验收 2）**：`llc -march=dadao -stop-after=finalize-isel`，均 `EXIT=0`：
```
ld64   (load i64)          %0:gprb = COPY $rb16
                           %1:gprd = ld_o_rd %0, 0
st64   (store i64)         %1:gprd = COPY $rd16 ; %0:gprb = COPY $rb16
                           st_o_rd %1, %0, 0
ldoff  (gep i64,ptr,2)     %1:gprd = ld_o_rd %0, 16          ← 非零 imm12
stoff  (同上 store)        st_o_rd %1, %0, 16
ldneg  (gep i64,ptr,-1)    %1:gprd = ld_o_rd %0, -8          ← 负偏移
ldu8/lds8   (zext/sext i8) ld_ub_rd %0, 0 / ld_sb_rd %0, 0
ldu16/lds16 (i16)          ld_uw_rd %0, 0 / ld_sw_rd %0, 0
ldu32/lds32 (i32)          ld_ut_rd %0, 0 / ld_st_rd %0, 0
stu8/stu16/stu32           st_b_rd / st_w_rd / st_t_rd (offset 0)
ldu8off (gep i8,ptr,1)     ld_ub_rd %0, 1
ldp (load ptr)             %1:gprd = ld_o_rd %0, 0 ; $rb31 = COPY %1
stp (store ptr)            %2:gprd = COPY %1 ; st_o_rd %2, %0, 0
```

3. **大端窄访存字节偏移显式核对（C13 D2；从 i16/i32 load 出发，DAGCombiner `ReduceLoadWidth`）**：
```
be_hi8  : load i16 + lshr 8          -> ld_ub_rd %0, 0    # BE 高字节在低地址 offset 0
be_lo8  : load i16 + and 255         -> ld_ub_rd %0, 1    # BE 低字节在 offset 1
be_s8hi : load i16 + ashr 8 + sext   -> ld_sb_rd %0, 0    # 高字节 offset 0，符号扩展
be_s8lo : load i16 -> trunc i8 -> sext -> ld_sb_rd %0, 1  # 低字节 offset 1，符号扩展
be_hi16 : load i32 + lshr 16         -> ld_uw_rd %0, 0    # 高半字 offset 0
be_lo16 : load i32 + and 0xffff      -> ld_uw_rd %0, 2    # 低半字 offset 2
```
关键：窄 load 的 combine 产生**非零**字节偏移（BE 低半部分在 +1/+2），由 `(add GPRB:$base, simm12:$off)` pattern 正确匹配；若只提供 offset 0 的窄 load pattern（0628 `DL-068a` 场景），这些偏移无法匹配/被错折。已逐条用真实 MIR 核对。

4. **边界/负偏移（自测扩范围）**：`gep i8,ptr,2047` → `ld_ub_rd %0, 2047`；`gep i8,ptr,-2048` → `ld_ub_rd %0, -2048`（均 `EXIT=0`）。超出 simm12（如 `2048`/`-2049`/`131072`）不由本 pattern 折叠，DAG 保留独立 i64 `add`，由 `ADD_IMM_PSEUDO`/`ADD_PSEUDO` 材料化后经 `rb2rd`/`rd2rb` 搬入 GPRB（`ld_ub_rd ..., 0`），语义正确（非 C14 D1 的单条 `add.o`；见遗留）。

5. **验收 3**：`-verify-machineinstrs -stop-after=finalize-isel` 对 23 个 load/store IR `VERIFY_ALL_EXIT=0`。

6. **验收 4（补丁 + 门控）**：
```
python3 tools/infra/make_patch.py llvm-project → 1 written, 44 unchanged         EXIT=0
make check-patch-tree    → 2 component(s), 77 patches OK                         EXIT=0
make check-source-state  → llvm-project: OK HEAD=01819ba79957 count=1 clean=True EXIT=0
make check-instrinfo     → === Result: 0 errors ===                              EXIT=0
make check-lit           → Total 33, Passed 33 (100.00%)                         EXIT=0
make check               → repository checks: PASS                               EXIT=0
```

7. **验收 5（一键证据脚本）**：
```
$ .work/evidence/LLVM-036t/run.sh; echo "EXIT=$?"
[PASS] llc-exists ... [PASS] llc-version
[PASS] mir-ld64-gprb | ld_o_rd base=%0:gprb | rc=0
[PASS] mir-st64-gprb | st_o_rd base=%0:gprb | rc=0
[PASS] mir-ldoff-16 ... [PASS] mir-stoff-16 ... [PASS] mir-ldneg-8 ...
[PASS] mir-off2047 ... [PASS] mir-offneg2048 ...
[PASS] mir-ld-u8 ... mir-ld-s8 ... mir-ld-u16 ... mir-ld-s16 ... mir-ld-u32 ... mir-ld-s32 ...
[PASS] mir-st-b ... mir-st-w ... mir-st-t ...
[PASS] be-hi-byte-offset0 ... be-lo-byte-offset1 ... be-lo-sext-offset1 ...
[PASS] be-hi-sext-offset0 ... be-hi16-offset0 ... be-lo16-offset2 ...
[PASS] verify-machineinstrs ... [PASS] mayload-maystore (mayLoad=9 mayStore=6) ...
[PASS] patch-hunks ... [PASS] check-patch-tree ... [PASS] check-source-state ... [PASS] check-lit
RESULT: PASS (31 checks, 0 failures)
EXIT=0

$ .work/evidence/LLVM-036t/run.sh --inject; echo "EXIT=$?"
inject: tightening the imm12 leaf (isInt<12> -> isInt<0>) in DADAOCodeGen.td
inject: dirty: llvm/lib/Target/DADAO/DADAOCodeGen.td
inject: rebuild EXIT=0
[FAIL] inject-ldoff-16 ... [FAIL] inject-ldneg-8 ... [FAIL] inject-ldu8off-1 ... [FAIL] inject-be-lo8-1 ...
inject: offset checks failed as expected (4 check(s))
inject: restoring source and rebuilding ... inject: rebuild EXIT=0
inject: restore sha256 unchanged (47c0511c7cd5...)
inject: re-running offset checks (expect PASS) ... [PASS]x4
inject: PASS (injection FAILed offset checks; restore sha256 unchanged; checks green again)
EXIT=0
```

**新发现/坑**：

1. **窄访存必须把 load-ext / trunc-store action 标 `Legal`**：仅加 pattern 不够——不设 `setLoadExtAction(EXTLOAD/SEXTLOAD/ZEXTLOAD, i64, {i8,i16,i32}, Legal)` 与 `setTruncStoreAction(i64, {i8,i16,i32}, Legal)`，legalizer 会把 extload/truncstore 拆成 `anyext load + trunc`/`zext` 等，pattern 无从匹配（同 0628 `0016` 做法）。
2. **大端字节偏移由 pattern 的非零 offset 匹配保证**：C13 D2 的 0628 `DL-068a`「silent miscompile」根因是窄 load pattern 只匹配 offset 0；本任务对 `(add GPRB:$base, simm12:$off)` 显式匹配，实测 `ReduceLoadWidth` 在大端下对低半部分给出 +1/+2 偏移并正确选中 `ld_ub/uw`（`ld_ub_rd %0, 1`、`ld_uw_rd %0, 2`），不再被折叠到 0。
3. **超 imm12 偏移无需专门处理也不会 `Cannot select`**：DAG 不把放不下的常量折入地址，而是保留独立 i64 `add`；`(load GPRB:$base)` 的寄存器类叶子会触发把该 add 结果 `COPY` 进 GPRB，add 本身由既有 `ADD_IMM_PSEUDO`/`ADD_PSEUDO` 选中（经 `rb2rd`/`rd2rb` 跨 bank）。语义正确，但非 C14 D1 的单条 `add.o`（见遗留）。
4. **GPRB 地址由 pattern 的寄存器类叶子强制**：`(load GPRB:$base)`/`(store ..., GPRB:$base)` 使地址落 GPRB；指针实参本就是 GPRB vreg（`LLVM-034t`），`ldp`/`stp` 中跨 bank 值（指针 load 结果 / store 值）由 `COPY`（`copyPhysReg`）处理，未回归。
5. **`-verify-machineinstrs` 在 `finalize-isel` 处可跑**（虚拟寄存器阶段），对 23 例全绿。

**遗留问题**：

- **C14 D1 的「指针算术直接落 GPRB」未实现（非阻塞）**：本任务范围是 load/store 地址匹配，不含 GPRB 指针加减 ISel（`add.o_orrr_dbb`）。大偏移经「GPRD 算术 + `rb2rd`/`rd2rb` 搬运」实现，语义正确但非单条；`add.o` 指针算术选择属后续指针运算任务（`LLVM-035t` 亦仅做 `ptr−ptr`）。已披露，`LLVM-036t` 验收未要求。
- **不含 FrameIndex 栈槽**（→`LLVM-038t`）与**全局符号地址**（→M4）：本任务用「参数指针 + 常量偏移」验证，符合任务范围。
- **未新增 lit 测试**：验收 4 只要求 `make check-lit` 不回归（33/33 通过）；大端窄访存等显式核对由一键证据脚本承担（任务未要求新增 lit）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：组件源码 3 文件（`DADAOInstrInfo.td` 的 15 处 `mayLoad`/`mayStore`、`DADAOCodeGen.td` 的 28 条 pattern、`DADAOISelLowering.cpp` 构造函数）；3 份导出补丁；`components/llvm-project/changelog.md`；`.work/evidence/LLVM-036t/run.sh`。

**审查要点（逐行）**：
- **逻辑正确性**：`simm12imm` 与 `imms12` 匹配（`isInt<12>`，与 ISA 符号扩展 12 位一致，C14 D3）；每个 `extload`/`zextload`/`sextload`/`truncstore` 映射到尾缀匹配的指令（`extload→ld.ub/uw/ut`、`zext→ld.ub/uw/ut`、`sext→ld.sb/sw/st`、`truncstore→st.b/w/t` 低 8/16/32 位）；`(load GPRB:$base)`/`(store ..., GPRB:$base)` 强制地址落 GPRB（C14 D5）；`setLoadExtAction` 覆盖 3 种 ext、`setTruncStoreAction` 覆盖 i8/16/32。
- **设计/惯用法**：窄偏移用 `(add base, simm12)` pattern（与 C14 D3、`imms12` 一致），复用既有 `ld_*_rd`/`st_*_rd` def，未新增指令/伪指令；大端偏移依赖 pattern 非零匹配（避免 0628 DL-068a）；load-ext/trunc action 与 0628 `0016` 一致；未改已有函数签名、未引外部依赖。
- **防造假**：完成区所有输出为真实 `llc` 运行后捕获；证据脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee`；`--inject` 真实改源码（sha256 变化）、真实重建、真实 FAIL(4 条)、还原（sha256 + `git status` 双证）+ 重建回绿。
- **边界**：i8/16/32 有符号/无符号 6 种 load + 3 种 store；offset 0/1/16/-8/2047/-2048 及超界 2048/-2049/131072；指针 load/store（`ldp`/`stp`）；`-verify-machineinstrs` 23 例全绿。
- **越界**：仅改任务列出的 3 个组件源文件 + 3 份导出补丁 + `changelog.md`（`Process-01 §162` 强制，已披露）+ 本任务书；`.work/source/llvm-project` 收敛 base+1 且干净。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `DADAOCodeGen.td` 头部/段注释把超 imm12 偏移描述为「limitation」，实测其经 generic i64 add 正确工作，措辞不准 | ✅已修 | 改写注释为「不折入 pattern，由 `ADD_IMM_PSEUDO`/`ADD_PSEUDO` 材料化后搬入 GPRB」 | 重建 `BUILD_EXIT=0`；证据 31/31 |
| 2 | 证据脚本 `check_addr_gprb` 用「行内首个 `%N`」当 load operand，实际首个 `%N` 是 def，误判 ld64 为 gprd | ✅已修 | 改为按 opcode 解析操作数（load 取第一个 vreg） | `run.sh` `[PASS] mir-ld64-gprb`（31/31） |
| 3 | 证据脚本 store 的 `check_addr_gprb` 取 `sm.group(2)`（value）而非 base `group(3)` | ✅已修 | 改为 `group(3)` | `[PASS] mir-st64-gprb`（31/31） |
| 4 | 证据脚本 `mem_check` 只允许 opcode 后一个 vreg，store（两 vreg 后才是偏移）不匹配 | ✅已修 | 正则改为 `${opc} %N(, %M)?, off` | `[PASS] mir-stoff-16`/`mir-st-b/w/t`（31/31） |

**自审判决**：finding #1–#4 全部 ✅已修 + 复验，无未修项。证据脚本 31/31 PASS 且 `--inject` 具备可达 FAIL（4 条偏移检查）与可复原性（sha256 + `git status` + 重建）；完成区结论与真实输出逐条对齐；`make check`/`check-patch-tree`/`check-source-state`/`check-instrinfo`/`check-lit` 全绿。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查环境**：reviewer 独立重跑，未采信 engineer 完成区的任何输出。

### 1. 证据脚本审阅

`.work/evidence/LLVM-036t/run.sh`（393 行）逐条审核：

- `record()` 函数：`FAILS` 计数器 + `return "$rc"`，失败路径可达 ✓
- `mem_check()`：`llc` 非零或 grep 不匹配 opcode+offset → FAIL ✓
- `check_addr_gprb()`：Python 解析 MIR 寄存器类，load 取第一个 vreg、store 取第三个 vreg 作为 base，cls≠gprb → exit(1) ✓
- `check_verify()`：23 个 IR 逐一跑 `-verify-machineinstrs`，任一失败 → `fail=1` ✓
- `check_mayflags()`：grep 补丁中 mayLoad/mayStore 计数，!=9/6 → FAIL ✓
- `--inject` 模式：`sed` 改 `isInt<12>→isInt<0>` → sha256 变化验证 → 重建 → 4 条 offset check FAIL → 还原+重建 → sha256 一致+`git status` 干净+回绿 ✓
- 结尾：`echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码 ✓
- `--inject` 的 4 条 offset check 在 `isInt<0>` 下必然 FAIL（非零偏移无法折叠），FAIL 路径可达 ✓

**脚本判定**：合格。

### 2. 重跑记录（独立执行）

```
$ bash .work/evidence/LLVM-036t/run.sh > /tmp/opencode/LLVM-036t-review/run-all.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项输出（从日志提取）：

| # | 检查名 | 期望 | 实际 | rc |
|---|--------|------|------|-----|
| 1 | llc-exists | executable exists | exists+exec | 0 |
| 2 | llc-version | rc=0 + dadao registered | rc=0, match=yes | 0 |
| 3 | mir-ld64-gprb | rc=0, base gprb | ok | 0 |
| 4 | mir-st64-gprb | rc=0, base gprb | ok | 0 |
| 5 | mir-ldoff-16 | ld_o_rd offset 16 | match=yes | 0 |
| 6 | mir-stoff-16 | st_o_rd offset 16 | match=yes | 0 |
| 7 | mir-ldneg-8 | ld_o_rd offset -8 | match=yes | 0 |
| 8 | mir-off2047 | ld_ub_rd offset 2047 | match=yes | 0 |
| 9 | mir-offneg2048 | ld_ub_rd offset -2048 | match=yes | 0 |
| 10 | mir-ld-u8 | ld_ub_rd offset 0 | match=yes | 0 |
| 11 | mir-ld-s8 | ld_sb_rd offset 0 | match=yes | 0 |
| 12 | mir-ld-u16 | ld_uw_rd offset 0 | match=yes | 0 |
| 13 | mir-ld-s16 | ld_sw_rd offset 0 | match=yes | 0 |
| 14 | mir-ld-u32 | ld_ut_rd offset 0 | match=yes | 0 |
| 15 | mir-ld-s32 | ld_st_rd offset 0 | match=yes | 0 |
| 16 | mir-ld-u8-off1 | ld_ub_rd offset 1 | match=yes | 0 |
| 17 | mir-st-b | st_b_rd offset 0 | match=yes | 0 |
| 18 | mir-st-w | st_w_rd offset 0 | match=yes | 0 |
| 19 | mir-st-t | st_t_rd offset 0 | match=yes | 0 |
| 20 | be-hi-byte-offset0 | ld_ub_rd offset 0 | match=yes | 0 |
| 21 | be-lo-byte-offset1 | ld_ub_rd offset 1 | match=yes | 0 |
| 22 | be-lo-sext-offset1 | ld_sb_rd offset 1 | match=yes | 0 |
| 23 | be-hi-sext-offset0 | ld_sb_rd offset 0 | match=yes | 0 |
| 24 | be-hi16-offset0 | ld_uw_rd offset 0 | match=yes | 0 |
| 25 | be-lo16-offset2 | ld_uw_rd offset 2 | match=yes | 0 |
| 26 | verify-machineinstrs | rc=0 for 23 IRs | all-clean | 0 |
| 27 | mayload-maystore | 9+6 | mayLoad=9 mayStore=6 | 0 |
| 28 | patch-hunks | 3 patches valid | ok | 0 |
| 29 | check-patch-tree | make rc=0 | rc=0 | 0 |
| 30 | check-source-state | make rc=0 | rc=0 | 0 |
| 31 | check-lit | make rc=0 | rc=0 | 0 |

**RESULT: PASS (31 checks, 0 failures)**

### 3. 独立注入反例

**注入点**：与 engineer 的 `isInt<12>→isInt<0>` 不同。reviewer 选择把 `zextloadi8` 的 pattern 从 `ld_ub_rd`（零扩展）改为 `ld_sb_rd`（符号扩展）——错误的 opcode。

**注入**：
```
# 原文
def : Pat<(i64 (zextloadi8 GPRB:$base)), (ld_ub_rd GPRB:$base, 0)>;
# 改为
def : Pat<(i64 (zextloadi8 GPRB:$base)), (ld_sb_rd GPRB:$base, 0)>; // REVIEWER-INJECT
```

- SHA256 注入前：`47c0511c7cd54425fbfcd2165c1f4cc2ede08ab8aa3932643dac8ce83d646b0e`
- SHA256 注入后：`f2e9d5ec71c3496643aa4abc135b875e23ed57d5eabcbc60eeebdb7453ad4553`（已变化）
- `git diff --name-only`：`llvm/lib/Target/DADAO/DADAOCodeGen.td`（非空）✓

**重建**：`ninja -j8 -C .work/build/llvm llc` → `BUILD_EXIT=0`

**注入后 MIR 检查**：
```
$ llc -march=dadao -stop-after=finalize-isel ldu8.ll | grep ld_
%1:gprd = ld_sb_rd %0, 0 :: (load (s8) from %ir.p)    ← 应为 ld_ub_rd，实际 ld_sb_rd
```
- `mem_check mir-ld-u8 ldu8 ld_ub_rd 0` → **FAIL**（opcode 不匹配）✓
- `lds8`（sextload，未注入）仍为 `ld_sb_rd`，未受影响 ✓

**还原 + 重建**：
```
SHA256 还原后：47c0511c7cd54425fbfcd2165c1f4cc2ede08ab8aa3932643dac8ce83d646b0e（一致）
git status --porcelain：空（干净）
重建：BUILD_EXIT=0
```

**还原后 MIR 检查**：
```
$ llc -march=dadao -stop-after=finalize-isel ldu8.ll | grep ld_
%1:gprd = ld_ub_rd %0, 0 :: (load (s8) from %ir.p)    ← 回绿 ✓
```

### 4. 大端字节偏移独立核对

reviewer 独立生成 6 个 IR 并跑 MIR，不采信 engineer 输出：

| 检查 | IR | 期望 opcode | 期望 offset | 实际 opcode | 实际 offset | 判定 |
|---|---|---|---|---|---|---|
| be_hi8 | i16 load + lshr 8 | ld_ub_rd | 0 | ld_ub_rd | 0 | ✓ |
| be_lo8 | i16 load + and 255 | ld_ub_rd | 1 | ld_ub_rd | 1 | ✓ |
| be_s8hi | i16 load + ashr 8 + sext | ld_sb_rd | 0 | ld_sb_rd | 0 | ✓ |
| be_s8lo | i16 load → trunc i8 → sext | ld_sb_rd | 1 | ld_sb_rd | 1 | ✓ |
| be_hi16 | i32 load + lshr 16 | ld_uw_rd | 0 | ld_uw_rd | 0 | ✓ |
| be_lo16 | i32 load + and 0xffff | ld_uw_rd | 2 | ld_uw_rd | 2 | ✓ |

**大端语义分析**：
- i16 BE：`[base+0]=high, [base+1]=low` → `lshr 8` 取高字节 @ offset 0，`and 255` 取低字节 @ offset 1 ✓
- i32 BE：`[base+0..1]=high, [base+2..3]=low` → `lshr 16` 取高半字 @ offset 0，`and 0xffff` 取低半字 @ offset 2 ✓
- 无小端误偏移，`ReduceLoadWidth` 产生的非零偏移均由 `(add GPRB:$base, simm12:$off)` pattern 正确匹配

### 5. mayLoad/mayStore 核对

```
$ grep -c 'let mayLoad = 1;' components/llvm-project/patches/.../DADAOInstrInfo.td.patch
9
$ grep -c 'let mayStore = 1;' components/llvm-project/patches/.../DADAOInstrInfo.td.patch
6
```
9 mayLoad + 6 mayStore = 15 条 rrii load/store，无遗漏。

### 6. 独立复核验收 1-4

| 验收项 | 命令 | 结果 | EXIT |
|---|---|---|---|
| 1. 构建 | `ninja -j8 llc` | [16/16] | 0 |
| 2. ld64→ld.o+GPRB | `llc -stop-after=finalize-isel` | `ld_o_rd %0, 0` + gprb | 0 |
| 2. st64→st.o+GPRB | 同上 | `st_o_rd %1, %0, 0` + gprb | 0 |
| 2. gep2→offset 16 | 同上 | `ld_o_rd %0, 16` | 0 |
| 2. gep-1→offset -8 | 同上 | `ld_o_rd %0, -8` | 0 |
| 3. verify-machineinstrs | `-verify-machineinstrs` 23 IRs | all clean | 0 |
| 4. check-patch-tree | `make check-patch-tree` | 77 patches OK | 0 |
| 4. check-source-state | `make check-source-state` | OK HEAD=01819ba79957 | 0 |
| 4. check-lit | `make check-lit` | 33/33 (100%) | 0 |
| 4. check-instrinfo | `make check-instrinfo` | 0 errors | 0 |
| 4. make check | `make check` | PASS | 0 |

### 7. 披露判定

**C14 D1「指针算术直接落 GPRB（单条 `add.o`）」未实现**：

- engineer 已在遗留问题中披露：大偏移经 GPRD 算术 + `rb2rd/rd2rb` 搬入 GPRB，语义正确但非单条 `add.o`
- **是否阻塞**：本任务验收标准只要求 base+imm12 的 load/store pattern 匹配，**未要求**大偏移 GPRB 直接算术。验收 2 的偏移检查范围为 0/16/-8/2047/-2048（均在 simm12 内），超界情况不由本 pattern 折叠但语义正确（DAG 保留独立 `add` + `COPY` 进 GPRB）
- **判定**：**非阻塞**。已披露，不需额外登记。

### 判决

**Accepted**

- 31/31 证据脚本全 PASS（reviewer 独立重跑，EXIT=0）
- 独立注入反例（zextloadi8→ld_sb_rd）：注入后 FAIL → 还原+重建 → 回绿，闭环完整
- 大端字节偏移 6 项独立核对全正确，无小端误偏移
- mayLoad=9 + mayStore=6，无遗漏
- 验收 1-4 全部独立复核通过
- C14 D1 遗留已披露，非阻塞
