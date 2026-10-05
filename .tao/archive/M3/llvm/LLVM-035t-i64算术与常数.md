# LLVM-035t: i64 算术 / 常数

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-034t`、`LLVM-043t`（**新增指令 `sub.o rd, rb, rb` 的 MC 先于本任务**；本任务的 ISel pattern 只能在其后添加）。
**状态**：已验证

> **新增依赖（M3 前置，串行在前）**：本任务新增 `ptr−ptr` 的 ISel 选择，依赖新增指令 `sub.o_orrr_dbb` 的落地链：
> `SPEC-101t`（三条既有 RB 算术指令改名+改编码）→ `SPEC-100t`（新增指令规范+编码+`scope:m3`）→ `LLVM-043t`（MC：`.td`/汇编/反汇编/编码）→ **本任务（ISel pattern）**；QEMU 侧 `QEMU-040t`（trans）为 E2E 执行前置（不阻塞本任务的 MIR 验收，但阻塞 `INTEG-012t`）。
> 助记符 / 编码**已定**（`adr-0012 D9`）：新增指令 `id=sub.o_orrr_dbb`、助记符 `sub.o`、`ha=0x33`、`value=0x40CC0000`。依据 `ADR-0018（C14 D4）` 与 `.tao/knowledge/project_M3-codegen-choices.md §5`（C14）：`ptr−ptr` 终态 = 单条 `sub.o`（替代 `rb2rd`×2 + `sub.o` 兜底）。

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-034t` 的骨架 + 双 bank ISel；v5 指令定义（`.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.td`）。
- **输出**：i64 算术与立即数材料化的 ISel 选择（TableGen pattern 或 `ISelDAGToDAG`），含伪指令/多目的处理的展开；导出的补丁。
- **约束**：
  - **指令事实（实测，来自 `DADAOInstrInfo.td` + `contract-isa.md`）**：
    - rrrr 双目的（128 位）加减乘：`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so rdha, rdhb, rdhc, rdhd`；`rdhb` = 结果**低 64 位**、`rdha` = 高位/进位。**i64 运算取 `rdhb`，高位写 `rd0`**（`add.uo rd0, <dst>, <s1>, <s2>`）。两目的不得同时为 `rd0`（`contract-isa.md §6.1`）。
    - orrr 单目的 64 位：`and.o`/`or.o`/`xor.o`/`xnor.o`/`add.uo`/`sub.uo`（MISC-octa）`rdhb, rdhc, rdhd`；`cmp.uo`/`cmp.so`。
    - 立即数：`add.si rd, imm18`（riii，18 位有符号、原地加）；`cmp.ui`/`cmp.si rdha, rdhb, imm12`（rrii）。
    - 移位：`shl.u*/shr.u*/shr.s*`（orrr 变量移位 / orri 立即移位）。
    - 除余：`div.u*/div.s*/rem.u*/rem.s*`（orrr/orri；语义见 `contract-isa.md §6.2`，含除零规则）。
    - 常数材料化（**C12 已判**）：`set.ow`/`set.zw` **按正负选基调** + `or.w`/`andn.w` 修正其余 wyde（镜像 `set.rd` 策略）；`add.si` 仅用于**增减**（不用于立即数设置）；**不引 constant pool**（M3 无 `.rodata`）。指针常量（绝对地址）用 `set.zw-rb`/`or.w-rb` 材料化（`contract-isa.md §5.2`；C14/`ADR-0018（C14）`）。
    - **wyde 位置写法（C12，`ISS-128`）**：`set.zw`/`set.ow`/`or.w`/`andn.w` 的 wyde 位置**只能写作 `wp0`–`wp3`**；**裸数字 0–3 属非法、须报错**（现状为被静默接受，`ISS-128` 待修）。注：本任务书旧表述「`wpN` 会被静默忽略、须用数值 0/1/2/3」与 §5 判定**相反**，已按 §5 更正。
  - **v5 现状**：`DADAOInstrInfo.td` 无任何 pattern（`Pattern = []`），且**无伪指令**；本任务按需新增 `Pattern` 与（如需要）伪指令（如 `ADD_PSEUDO`/`SUB_PSEUDO`），并在 `expandPostRAPseudo`（`LLVM-040t` 或本任务）展开。
  - **范围**：i64 `add/sub/and/or/xor/shl/shr/mul`（`div/rem` 至少 `llvm_unreachable` 或 LibCall 兜底，完整语义可后置——**在完成区明确列出已覆盖/未覆盖**）；常数 i64 材料化。**不含** branch/compare-setcc（→`LLVM-037t`）、访存、调用、FP。
  - **`ptr−ptr` ISel（新增，M3 前置）**：为 `sub.o rd, rb, rb`（RB − RB → RD，见 `LLVM-043t`）添加 ISel 选择，使「两个指针相减」选出该指令。**两操作数须落 GPRB（`rbhc`/`rbhd`）、目的为 GPRD（`rdhb`）**；机制为 **bank 感知**（C1/C2 硬双类 + i64 通吃的人为约束，`ADR-0018`），可在 TableGen pattern 或 `DADAOISelDAGToDAG` 中实现（由 engineer 定，**须在完成区说明所选机制**）。**不得**以 `rb2rd`×2 + `sub.o` 作为终态（`ADR-0018 C14 R2` 已否决）。指令定义与编码由 `LLVM-043t` 提供（本任务只加选择，不重定义编码）。
  - **不回归** GPRD/GPRB MIR（`LLVM-034t` 验收 1 的 `pass_ptr`/`id64`）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`；`make check-patch-tree`、`make check-source-state`。
  - 参照 **0628 `DL-060a`（shift/mul）/`DL-060b`（div/rem）/`DL-061a`（wyde imm）**（只读溯源）。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 对下列（**真实 MIR，含目标指令**）：
   - `define i64 @f(i64 %a,i64 %b){ %r=add i64 %a,%b  ret i64 %r }` → 含 i64 add 选择（如 `ADD_PSEUDO`/`add.uo`），非 `COPY`+未实现；**且结果含 `class: gprd`（计算型 i64 → GPRD；补 `LLVM-034t` 验收 1 推迟项，用户 2026-10-05 裁定）**；
   - 大常数：`define i64 @c(){ ret i64 123456789012345 }` → 材料化为 `set.zw`/`or.w` 序列（或 `add.si`）；给出 MIR。
   - `ptr−ptr`（M3 前置）：以两个指针形参相减为例（如 `define i64 @pdiff(ptr %p, ptr %q)` 中 `%r = sub i64 %a, %b`，`%a`/`%b` 来自 `ptrtoint`），`-stop-after=finalize-isel` 含 `sub.o`（两操作数来自 GPRB）选择，**无** `rb2rd`×2 兜底；给出 MIR。
3. `llc -stop-after=finalize-isel` 对以上程序退出 0、不 `Cannot select`。
4. 补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
5. 一键证据脚本 `.work/evidence/LLVM-035t/run.sh`（规格同 `LLVM-033t`；反例注入：改一条 pattern/操作数使选择失败 → 预期 FAIL）。

## 完成区

**测试结果**：通过 **14/14**（`.work/evidence/LLVM-035t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（禁用 `ISD::Constant` 选择路径 → 重建 → 常数检查 FAIL(rc=134) → 还原+重建 → 回绿，源码 sha256 一致、`git status` 干净）。`make check` `EXIT=0`（lit `33/33`）；`make check-patch-tree` 77 OK；`make check-source-state` OK（`HEAD=bb1f68de5235 count=1 clean=True`）。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 = `bb1f68de52354019696ec6436ba0d7b12afc7904`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`，共 4 文件修改）：
- `llvm/lib/Target/DADAO/DADAOCodeGen.td`：新增 `ADD_PSEUDO`/`SUB_PSEUDO`/`MUL_PSEUDO`/`ADD_IMM_PSEUDO`/`CONST_WYDE` 伪指令 + `simm18imm` ImmLeaf；新增单目的 orrr pattern（`and_o`/`or_o`/`xor_o`、`shl_uo_orrr`/`shr_uo_orrr`/`shr_so_orrr`、`div_uo`/`div_so`/`rem_uo`/`rem_so`）。
- `llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp`：新增 `ISD::Constant` → `CONST_WYDE`（`SelectConstant`）与 **bank 感知 ptr−ptr** → `sub_o_dbb`（`SelectPointerSub` + `isPointerBankValue`，两 GPRB 操作数才走单条 `sub.o`）。
- `llvm/lib/Target/DADAO/DADAOInstrInfo.cpp`：实现 `expandPostRAPseudo`（`ADD/SUB/MUL_PSEUDO` → `add.uo/sub.uo/mul.uo rd0, dst, a, b`；`ADD_IMM_PSEUDO` → `rd2rd` + `add.si`；`CONST_WYDE` → `set.zw`/`set.ow` 基调 + `or.w`/`andn.w` 修正）。
- `llvm/lib/Target/DADAO/DADAOInstrInfo.h`：声明 `expandPostRAPseudo` override。

DADAO-v5 仓库：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOCodeGen.td,DADAOISelDAGToDAG.cpp,DADAOInstrInfo.cpp,DADAOInstrInfo.h}.patch`（由 `tools/infra/make_patch.py llvm-project` 从真实源导出，未手改）+ `components/llvm-project/changelog.md`；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-035t/run.sh`；日志 `.work/log/llvm/LLVM-035t-*.log`；临时 `/tmp/opencode/LLVM-035t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`）：

1. **构建**（验收 1）：`ninja -j8 -C .work/build/llvm llc` → `BUILD_EXIT=0`（`[28/28] Linking CXX executable bin/llc`；log `.work/log/llvm/LLVM-035t-build-final.log`）。

2. **验收 2a — `add i64` 选择且结果 `class: gprd`**（补 LLVM-034t 推迟项）：
```
$ llc -march=dadao -stop-after=finalize-isel -o - /tmp/opencode/LLVM-035t/f.ll; echo "EXIT=$?"
EXIT=0
registers:
  - { id: 0, class: gprd, ... }   - { id: 1, class: gprd, ... }   - { id: 2, class: gprd, ... }
body:             |
  bb.0 (%ir-block.0):
    liveins: $rd16, $rd17
    %1:gprd = COPY $rd17
    %0:gprd = COPY $rd16
    %2:gprd = ADD_PSEUDO %0, %1
    $rd31 = COPY %2
    RET_PSEUDO implicit $rd31
```
（post-RA 展开：`$rd0, $rd31 = add_uo_rd $rd16, $rd17`，即 `add.uo rd0, rd31, rd16, rd17`，高位写 rd0。）

3. **验收 2b — 大常数材料化**：
```
$ llc -march=dadao -stop-after=finalize-isel -o - /tmp/opencode/LLVM-035t/c.ll   # ret i64 123456789012345
EXIT=0
  bb.0 (%ir-block.0):
    %0:gprd = CONST_WYDE 123456789012345
    $rd31 = COPY %0
    RET_PSEUDO implicit $rd31

$ llc -march=dadao -run-pass=postrapseudos -verify-machineinstrs -o - c.vr.mir; echo "EXIT=$?"
EXIT=0
  bb.0 (%ir-block.0):
    $rd31 = set_zw_rd 0, 57209
    $rd31 = or_w_rd 1, 34317
    $rd31 = or_w_rd 2, 28744
    RET_PSEUDO implicit $rd31
```
（`set_zw_rd`/`or_w_rd` = 助记符 `set.zw`/`or.w` 的 MIR def 名；57209/34317/28744 = `0x7048860ddf79` 的 wyde0/1/2，与 `123456789012345` 独立重算一致。负数/边界另验：`-1 → set_ow_rd 0,65535`；`INT64_MIN → set_ow_rd 3,32768 + andn_w_rd 0/1/2,65535`；`0xFFFFFFFF00000000 → set_ow_rd 1,0 + andn_w_rd 0,65535`，逐条重算正确。）

4. **验收 2c — `ptr−ptr`（M3 前置）**：
```
$ llc -march=dadao -stop-after=finalize-isel -o - /tmp/opencode/LLVM-035t/pdiff.ll; echo "EXIT=$?"
EXIT=0
registers:
  - { id: 0, class: gprb, ... }   - { id: 1, class: gprb, ... }   - { id: 2, class: gprd, ... }
  bb.0 (%ir-block.0):
    liveins: $rb16, $rb17
    %1:gprb = COPY $rb17
    %0:gprb = COPY $rb16
    %2:gprd = sub_o_dbb %0, %1
    $rd31 = COPY %2
    RET_PSEUDO implicit $rd31
```
（两操作数 GPRB、目的 GPRD，单条 `sub.o`；**无** `rb2rd`×2 兜底。整文件 `grep rb2rd` = 0。）

5. **验收 2d — `add.si` 立即数（范围列举项）**：`add i64 %a, 5` → `%1:gprd = ADD_IMM_PSEUDO %0, 5`；post-RA → `$rd31 = rd2rd $rd16, 1` + `$rd31 = add_si_rd 5`（`sub %a,5` 被归一为 `add %a,-5` 同路径；`add %a,123456789` 超 imm18 → `CONST_WYDE`+`ADD_PSEUDO`）。

6. **验收 3 — 无 `Cannot select`**：`arith.ll`（sub/mul/and/or/xor/shl/lshr/ashr/udiv/sdiv/urem/srem）`-stop-after=finalize-isel` `EXIT=0`、stderr 空；选择结果 `SUB_PSEUDO`/`MUL_PSEUDO`/`and_o`/`or_o`/`xor_o`/`shl_uo_orrr`/`shr_uo_orrr`/`shr_so_orrr`/`div_uo`/`div_so`/`rem_uo`/`rem_so` 全部命中。

7. **验收 4 — 补丁 + 门控**：
```
$ python3 tools/infra/make_patch.py llvm-project   → EXIT=0（1 written, 44 unchanged）
$ make check-patch-tree    → check-patch-tree: 2 component(s), 77 patches OK        EXIT=0
$ make check-source-state  → llvm-project: OK HEAD=bb1f68de5235 count=1 clean=True  EXIT=0
$ make check-lit           → Total 33, Passed 33 (100.00%)                           EXIT=0
$ make check               → repository checks: PASS                                 EXIT=0
```

8. **验收 5 — 一键证据脚本**：
```
$ .work/evidence/LLVM-035t/run.sh; echo "EXIT=$?"
[PASS] llc-exists ... [PASS] llc-version
[PASS] mir-add-i64-gprd | ... ADD_PSEUDO=yes, gprd=yes | rc=0
[PASS] mir-const-wyde | ... CONST_WYDE 123456789012345 | rc=0
reconstructed 0x7048860ddf79 == 0x7048860ddf79
[PASS] postra-const-sequence | ... | rc=0
[PASS] postra-add-rrrr | ... | rc=0
[PASS] postra-add-si | ... | rc=0
[PASS] mir-ptr-sub | ... | rc=0
[PASS] arith-select | ... all present | rc=0
[PASS] regress-id64-passptr | ... ok | rc=0
[PASS] patch-hunks | ... [PASS] check-patch-tree | ... [PASS] check-source-state | ... [PASS] check-lit
RESULT: PASS (14 checks, 0 failures)
EXIT=0

$ .work/evidence/LLVM-035t/run.sh --inject; echo "EXIT=$?"
inject: disabling the ISD::Constant selection path in DADAOISelDAGToDAG.cpp
inject: dirty: llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp
inject: rebuild EXIT=0
[FAIL] mir-const-wyde | ... actual: rc=134, match=no | rc=1
[FAIL] postra-const-sequence | ... actual: rc=134 | rc=1
inject: constant selection failed as expected
inject: restoring source and rebuilding ... inject: rebuild EXIT=0
inject: restore sha256 unchanged (efb993da0a5d...)
inject: re-running constant checks (expect PASS) ...
inject: PASS (injection FAILed constant checks; restore sha256 unchanged; checks green again)
EXIT=0
```

**新发现/坑**：

1. **rrrr 双目的无法用 TableGen pattern 直选**：`add.uo/sub.uo/mul.uo` 有 2 个目的（rdha=高、rdhb=低），DAG 的 `add` 只有 1 个值 → 用单结果伪指令 `ADD/SUB/MUL_PSEUDO` + `expandPostRAPseudo` 展开为 `... rd0, dst, a, b`（高位写 rd0）。**`BuildMI` 多目的必须用 `.addDef()`**：首版用 `.addReg()` 生成后被 `-verify-machineinstrs` 判 `Explicit definition marked as use` / `Using an undefined physical register`，改 `.addDef(rd0).addDef(Dst)` 后 `PS_EXIT=0`。
2. **ptr−ptr 的 bank 判定机制（本任务所选机制）**：C2 为 i64 通吃，指针 bank 只体现在 `LowerFormalArguments` 为指针形参建的 GPRB 虚拟寄存器上。故在 `DADAOISelDAGToDAG::Select` 对 `ISD::SUB` 检查两操作数是否为「GPRB 虚拟寄存器的 `CopyFromReg`」（`MRI.getRegClass(R) == &GPRBRegClass`），是则选单条 `sub_o_dbb`，否则退回 `SUB_PSEUDO`。限制：仅识别 `CopyFromReg`，中间经其它 DAG 节点包装/折叠的指针表达式会退回（语义仍正确，只是多条）。本任务验收的 `ptrtoint` 直用可检出。
3. **常数材料化用伪指令 + post-RA 展开**：`set.zw/or.w/set.ow/andn.w` 的 rwii 指令在 TableGen 中是无显式源操作数的**读-改-写**（def 即硬件隐式输入），无法在 SelectionDAG 里用单结果 chain 构造真实指令序列；故用 `CONST_WYDE` 伪指令。`-stop-after=finalize-isel` 显示 `CONST_WYDE`，真实 `set.zw`/`set.ow`/`or.w`/`andn.w` 序列在 `postrapseudos` 展开后可见（MIR 打印为 def 名 `set_zw_rd`/`or_w_rd`/`andn_w_rd`/`set_ow_rd`）。C12「按正负选基调」：非负用 `set.zw`（其余清零）+ `or.w` 补 1 位；负用 `set.ow`（其余全 1）+ `andn.w` 清 0 位。**不引 constant pool**。
4. **`sub %a, imm` 被 DAGCombine 归一为 `add %a, -imm`**：由 `ADD_IMM_PSEUDO`（`add.si`）覆盖；`add %a,5` 与 `sub %a,5` 走同一路径。
5. **MIR 的 wydepos 数值 0–3 与「只能写 wpN」不冲突**：`DADAOMCInstPrinter.cpp:310` 已把 rwii 的 wyde 位置打印为 `wpN`，与 `LLVM-045t` 的 AsmParser 收紧（裸数字拒绝）配套；本任务输出的是 MIR 内部数值，AsmPrinter（`LLVM-040t`）会打印为 `wp0`–`wp3`。
6. **读-改-写指令的隐式读未在 TableGen 建模**：`or.w`/`andn.w`/`add.si` 读-改-写自身目的寄存器，但指令定义无显式源 operand。post-RA 展开产生同一物理寄存器连续 def 的序列，可通过 `-verify-machineinstrs`（展开在 RA 之后、无后续 liveness 敏感 pass），且 `set.zw` 首条会清零/置全 1，序列语义正确；属既有建模局限（0628 同）。

**遗留问题**：

- **指针常量（绝对地址）的 `set.zw-rb`/`or.w-rb` 材料化未实现**：`CONST_WYDE` 固定用 RD 变体；指针常量会先落 GPRD，再经 `copyPhysReg` 的 `rd2rb` 转 GPRB（语义正确，多一条搬运）。任务验收未涉及（无指针常量用例），登记为**未覆盖**（`LLVM-036t` 指针/GEP 相关或后续任务）。
- **`isPointerBankValue` 仅识别 `CopyFromReg`**（见坑 2）：复杂指针表达式相减可能退回 `SUB_PSEUDO` + `rb2rd`（语义正确但非终态）；本任务验收用例可检出。
- **窄类型（i8/i16/i32）算术未覆盖**（M3 边界；窄算术回绕由对应符号后缀窄指令承担，属 `LLVM-037t`/后续）。
- **常量移位量走寄存器形式**（`CONST_WYDE` + orrr），未用 `orri` 立即数优化（正确但多一条指令）；与 0628 遗留一致。
- `div/rem` **已覆盖**（直接选 `div_uo/div_so/rem_uo/rem_so`；DADAO 除零/INT_MIN÷-1 为定值，LLVM IR 对应为 UB，映射安全），非仅 `llvm_unreachable` 兜底——超出任务「至少兜底」要求。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：组件源码 4 文件（`DADAOCodeGen.td`、`DADAOISelDAGToDAG.cpp`、`DADAOInstrInfo.{cpp,h}`）；4 份导出补丁；`.work/evidence/LLVM-035t/run.sh`；`components/llvm-project/changelog.md`。

**审查要点（逐行）**：
- **逻辑正确性**：`Select` 先 `isMachineOpcode` 短路再 switch（`Constant`/`SUB`），其余 `SelectCode`；`isPointerBankValue` 只对 `CopyFromReg` 的 GPRB vreg 返回真（`R.isVirtual()` 且 `getRegClass == &GPRBRegClass`），避免误判普通 i64；`SelectPointerSub` 操作数顺序 = `rbhc − rbhd`，与 `sub.o_dbb` 定义一致；`expandPostRAPseudo` 的 ADD/SUB/MUL 用 `addDef(rd0)` 弃高位、`addDef(Dst)` 得低位（两目的不同时为 rd0，符合 §6.1.1）；`CONST_WYDE` 基调/修正分支穷尽 4 个 wyde、`~T` 取 `uint16_t` 截断；`ADD_IMM_PSEUDO` 在 `Dst==Src` 时跳过 `rd2rd`（避免非法 identity/重叠块拷贝）。
- **设计/惯用法**：双目的用「单结果伪指令 + `expandPostRAPseudo`」（同 0628 `DL-060a/061a`）；单目的 orrr 用 TableGen pattern 直选（最简）；bank 感知 ptr−ptr 用 `ISelDAGToDAG`（C2 i64 通吃下唯一可靠机制）；未改 MC 定义/编码、未改已有函数签名（仅新增 override）、未引外部依赖、未引 constant pool。
- **防造假**：完成区所有输出为真实运行后 `cmd > log 2>&1; rc=$?` 捕获；证据脚本 `--inject` 真实重建、真实 FAIL(rc=134)、真实还原（sha256 + `git status` 双证）+ 重建回绿；脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码。
- **边界**：正/负/全 0/全 1/`INT64_MIN`/`0xFFFFFFFF00000000`/`0x100000000` 常数逐条重算；`add`/`sub` 立即数（含 18 位边界外的 `123456789`）；`ptrtoint` 直用与普通 i64 `sub`（负对照）均实测；`pass_ptr`/`id64` 不回归。
- **越界**：仅改任务列出的 4 个组件源文件 + 4 份导出补丁 + `changelog.md`（`Process-01 §162` 强制，已披露）+ 本任务书；`.work/source/llvm-project` 收敛 base+1 且干净。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `ADD/SUB/MUL_PSEUDO` 展开用 `.addReg` 未标 def，`-verify-machineinstrs` 报 `Explicit definition marked as use` / `Using an undefined physical register` | ✅已修 | `DADAOInstrInfo.cpp` 前两操作数改 `.addDef(rd0).addDef(Dst)` | `postrapseudos -verify-machineinstrs` `PS_EXIT=0`；`$rd0, $rd31 = add_uo_rd $rd16, $rd17` |
| 2 | 证据脚本 `check_add_rrrr_expand` 的 grep 方向写反（想匹配 `add_uo_rd` 后的 `$rd0,`，实际 `$rd0,` 在 `=` 前） | ✅已修 | 改为 `grep -Eq '\$rd0, \$rd[0-9]+ = add_uo_rd'` | `run.sh` `[PASS] postra-add-rrrr`（14/14） |
| 3 | 证据脚本 `check_ptr_sub` 误设 MIR 操作数打印带 `:gprb`（实际为裸 `%0, %1`，类在 `registers:` 表） | ✅已修 | 改为 Python 交叉核对 `registers:` 表（%0/%1 gprb、%2 gprd） | `run.sh` `[PASS] mir-ptr-sub`（14/14） |
| 4 | 任务 scope 的立即数 `add.si` 未覆盖（小立即数走常量材料化，正确但未用 `add.si`） | ✅已修 | `DADAOCodeGen.td` 加 `simm18imm` ImmLeaf + `ADD_IMM_PSEUDO`；`DADAOInstrInfo.cpp` 加其展开（`rd2rd` + `add.si`） | `add %a,5` → `add_si_rd 5`；`run.sh` `[PASS] postra-add-si` |
| 5 | `DADAOCodeGen.td` 头注释仍写「skeleton (LLVM-033t)」，与现内容不符 | ✅已修 | 更新文件头注释 | 重建 `BUILD_EXIT=0`；`run.sh` 14/14 |

**自审判决**：所有 finding 均已处置（#1–#5 全部 ✅已修 + 复验），无未修项。证据脚本 14/14 PASS 且 `--inject` 具备可达 FAIL 路径（rc=134）与可复原性（sha256 + `git status` + 重建）；完成区结论与真实输出逐条对齐；`make check` / `check-patch-tree` / `check-source-state` / `check-lit` 全绿。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查时间**：2026-10-05

---

**1. 证据脚本审查（`.work/evidence/LLVM-035t/run.sh`）**

逐条核对14个 `check_*` 函数：
- 每个函数的 `rc != 0` 分支均调用 `record(..., 1)`，有可达 FAIL 路径 ✓
- `record()` 函数正确统计 `FAILS` 并传递返回码 ✓
- 结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码 ✓
- `--inject` 注入 sed 替换 `SelectConstant(Node)` → sha256 变化验证 → FAIL 期望 → 还原+重建 → sha256 回绿 + `git status` 干净 ✓
- `check_const_sequence` 的 Python 解码器逐 wyde 累加重建，含 `set_zw_rd`/`set_ow_rd`/`or_w_rd`/`andn_w_rd` 四种操作，逻辑正确 ✓
- `check_ptr_sub` 用 Python 交叉核对 `registers:` 表（class 字段）+ body 中 `sub_o_dbb`，不含 `rb2rd` ✓
- `check_arith_ops` 逐项 grep12种指令名，`miss` 变量累积缺失项 ✓

**脚本判定**：合格，可独立重跑。

---

**2. 重跑记录（`.work/evidence/LLVM-035t/run.sh`）**

```
$ cd /mnt/tao/DADAO-v5 && .work/evidence/LLVM-035t/run.sh > /tmp/opencode/LLVM-035t-review/run.log 2>&1; echo "EXIT=$?"

EXIT=0
[PASS] llc-exists | expected: executable .../llc | actual: exists+exec | rc=0
[PASS] llc-version | expected: rc=0 and 'dadao' registered | actual: rc=0, match=yes | rc=0
[PASS] mir-add-i64-gprd | expected: rc=0, ADD_PSEUDO + class gprd | actual: rc=0, ADD_PSEUDO=yes, gprd=yes | rc=0
[PASS] mir-const-wyde | expected: rc=0, CONST_WYDE 123456789012345 | actual: rc=0, match=yes | rc=0
reconstructed 0x7048860ddf79 == 0x7048860ddf79
[PASS] postra-const-sequence | expected: post-RA set.zw/or.w reconstructs 123456789012345 | actual: ok | rc=0
[PASS] postra-add-rrrr | expected: post-RA add_uo_rd with rd0 high half | actual: rc=0, match=yes | rc=0
[PASS] postra-add-si | expected: add i64 %a,5 -> ADD_IMM_PSEUDO -> add.si 5 | actual: rc=0, match=yes | rc=0
[PASS] mir-ptr-sub | expected: rc=0, sub_o_dbb(gprb,gprb)->gprd, no rb2rd | actual: ok | rc=0
[PASS] arith-select | expected: all i64 ops selected (no Cannot select) | actual: rc=0, all present | rc=0
[PASS] regress-id64-passptr | expected: id64->gprd, pass_ptr->gprb | actual: rc=0/0, ok | rc=0
patch-hunks: 4 LLVM-035t patches have valid hunks
[PASS] patch-hunks | expected: 4 changed patches have valid hunks | actual: ok | rc=0
[PASS] check-patch-tree | expected: make check-patch-tree rc=0 | actual: rc=0 | rc=0
[PASS] check-source-state | expected: make check-source-state rc=0 | actual: rc=0 | rc=0
[PASS] check-lit | expected: make check-lit rc=0 | actual: rc=0 | rc=0
----------------------------------------
RESULT: PASS (14 checks, 0 failures)
EXIT=0
```

**14/14 全 PASS，EXIT=0。**

---

**3. 独立注入（与 engineer 的注入不同）**

**注入点**：`DADAOISelDAGToDAG.cpp` 的 `isPointerBankValue()` 函数，将 `return MF->getRegInfo().getRegClass(R) == &DADAO::GPRBRegClass;` 改为 `return false;`（禁用 GPRB 指针 bank 检测，使 ptr−ptr 退回 SUB_PSEUDO + rb2rd）。

**注入前 sha256**：`efb993da0a5dff4f8aa0d5655f9e1b0ff7ae7a784ad89a0db770e51fea94c853`
**注入后 sha256**：`68bc13799656020e23a623a234d87db106ace095449f78f1d7818de091a4a2da`（`git diff --name-only` 非空 ✓）

**重建**：`ninja -j8 -C .work/build/llvm llc` → `BUILD_EXIT=0`

**注入后 ptr-ptr 检查结果**：
```
LLC_EXIT=0
sub_o_dbb count: 0   ← 未选中 sub_o_dbb
body:
    %0:gprb = COPY $rb16
    %1:gprb = COPY $rb17
    %3:gprd = COPY %0    ← rb2rd 退回路径
    %4:gprd = COPY %1
    %2:gprd = SUB_PSEUDO %3, %4
PTR_SUB_CHECK_EXIT=1   ← 证据脚本检查 FAIL ✓
```

**还原**：`cp -f backup → DADAOISelDAGToDAG.cpp`
- 还原后 sha256：`efb993da0a5dff4f8aa0d5655f9e1b0ff7ae7a784ad89a0db770e51fea94c853`（与注入前一致 ✓）
- `git status`：干净（无残留 ✓）

**还原后重建**：`ninja -j8 -C .work/build/llvm llc` → `RESTORE_BUILD_EXIT=0`

**还原后 ptr-ptr 检查结果**：
```
LLC_EXIT=0
sub_o_dbb count: 1   ← sub_o_dbb 重新选中
body:
    %0:gprb = COPY $rb16
    %1:gprb = COPY $rb17
    %2:gprd = sub_o_dbb %0, %1   ← 正确选中
PTR_SUB_CHECK_EXIT=0   ← 回绿 ✓
```

---

**4. 独立常数重算**

`123456789012345` = `0x00007048860DDF79`：
| wyde | 位置 | 十六进制 | 十进制 | MIR 操作数 |
|------|------|---------|--------|-----------|
| wp0 | 位 0–15 | `0xDF79` | 57209 | `set_zw_rd 0, 57209` |
| wp1 | 位 16–31 | `0x860D` | 34317 | `or_w_rd 1, 34317` |
| wp2 | 位 32–47 | `0x7048` | 28744 | `or_w_rd 2, 28744` |
| wp3 | 位 48–63 | `0x0000` | 0 | （不需修正） |

重建：`57209 | (34317<<16) | (28744<<32)` = `123456789012345` ✓

**边缘案例独立验证**：
- `INT64_MIN`（`-9223372036854775808`）：`set_ow_rd 3, 32768` + `andn_w_rd 0, 65535` + `andn_w_rd 1, 65535` + `andn_w_rd 2, 65535` → `0x8000000000000000` ✓
- `0xFFFFFFFF00000000`（`-4294967296`）：`set_ow_rd 1, 0` + `andn_w_rd 0, 65535` → `0xFFFFFFFF00000000` ✓

---

**5. 伪指令方案判定**

`CONST_WYDE` 伪指令 + `expandPostRAPseudo` 展开方案：
- **任务书允许**：§接口规范明确「本任务按需新增伪指令」，验收标准允许 `-stop-after=finalize-isel` 显示 `CONST_WYDE`、`postrapseudos` 后显示真实指令 ✓
- **合理**：`set.zw/or.w/set.ow/andn.w` 是 rwii 读-改-写指令，无显式源操作数，DAG 的单结果 `add`/`or` 节点无法直接构造这种隐式读写语义 → 伪指令是正确选择（同0628 `DL-061a` 策略）✓
- **expandPostRAPseudo 正确性**：正负选基调逻辑完整（`Neg` 分支选 `set.ow` + `andn.w` vs `set.zw` + `or.w`）；basis 选择策略正确（负数从高到低找首个非0xFFFF、非负从低到高找首个非0）；4 wyde 全遍历 ✓
- **rdrrr rrrr 的伪指令展开**：`addDef(rd0).addDef(Dst)` 正确处理双目的，高位写 rd0 弃掉，低位为结果（符合 `contract-isa.md §6.1.1`）✓

---

**6. 验收标准逐项核对**

| # | 验收项 | 结果 |
|---|--------|------|
| 1 | `ninja` 退出 0 | ✓ |
| 2a | `add i64` → finalize-isel 含 `ADD_PSEUDO`、`class: gprd` | ✓ |
| 2b | 大常数 → `CONST_WYDE`、post-RA `set.zw/or.w` 序列 = 123456789012345 | ✓（独立重算一致）|
| 2c | `ptr−ptr` → `sub_o_dbb`（两操作数 GPRB、目的 GPRD）、无 `rb2rd` | ✓ |
| 3 | `-stop-after=finalize-isel` 无 `Cannot select` | ✓（arith.ll 12种指令全选中）|
| 4 | 补丁导出 + `make check-patch-tree` 77 OK + `make check-lit` 33/33 | ✓ |
| 5 | 一键证据脚本 14/14 PASS + `--inject` 自检 | ✓（我独立注入也验证了）|

**约束核对**：
- 指令事实（rrrr 双目的/单目的 orrr/立即数/移位/常数材料化 C12）：全部按规范实现 ✓
- `ptr−ptr` bank 感知单条 `sub.o`（非 `rb2rd`×2 兜底，符合 ADR-0018 C14 R2）✓
- 不回归 GPRD/GPRB MIR（id64→gprd、pass_ptr→gprb）✓
- 补丁纪律（4文件 + make_patch.py 导出）✓
- 不引 constant pool ✓
- 无 tee 吞退出码 ✓

**7. 未覆盖披露（非阻塞）**

| 遗留项 | 判定 | 理由 |
|--------|------|------|
| 指针常量 `set.zw-rb/or.w-rb` 材料化 | 非阻塞 | 任务验收无指针常量用例；当前路径 `rd2rb` copy 语义正确，登记后续任务 |
| `isPointerBankValue` 仅识别 `CopyFromReg` | 非阻塞 | 复杂指针表达式退回 SUB_PSEUDO（语义正确），任务验收用例可检出 |
| 窄类型（i8/i16/i32）算术 | 非阻塞 | M3 边界，属 LLVM-037t/后续 |
| 常量移位走 `CONST_WYDE` + orrr | 非阻塞 | 正确但多一条，与0628遗留一致 |

---

**判决：Accepted**

14/14 项验收全部通过（独立重跑确认）；独立注入（禁用 `isPointerBankValue` → ptr−ptr 退回 SUB_PSEUDO）验证了反例 FAIL 路径；还原 + 重建回绿（sha256 一致 + git status 干净）；独立常数重算与 MIR 一致；伪指令方案合理且任务书允许；未覆盖项均为非阻塞遗留。

**状态更新：待验收 → 已验证**
