# LLVM-037t: compare / branch

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-035t`、`LLVM-036t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-035t`（算术/常数）、`LLVM-036t`（访存）；v5 指令定义。
- **输出**：条件比较 + 条件/无条件分支的 ISel 与基本块布局；导出的补丁。
- **约束**：
  - **指令事实（实测，`DADAOInstrInfo.td` + `contract-isa.md`）**：
    - 比较：`cmp.ui rdha, rdhb, imm12`（无符号立即数）、`cmp.si`（有符号立即数）；`cmp.uo`/`cmp.so rdhb, rdhc, rdhd`（64 位寄存器，orrr）。比较结果写 rd，零/符号扩展写满 64 位。
    - 双寄存器条件分支 rrii：`br.eq`/`br.ne rdha, rdhb, imms12`。
    - 单寄存器条件分支 riii（测 rd 对 0）：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np rdha, imms18`；另有 `br.z`/`br.nz` 的 `rb` 变体（`br_z_rb`/`br_nz_rb`）。
    - 无条件：`jump`（iiii 24 位 / rrii 12 位）；函数返回 `ret`（riii）。
    - 分支立即数为 **PC 相对、字偏移（`<<2`，无 +4 流水偏移）**（`contract-isa.md §5`；`MCTargetDesc/DADAOFixupKinds.h` 已定义 `PCRel_12/18/24`）。
  - **必须**：`icmp`（至少 `eq/ne/slt/sle/sgt/sge` 6 个有符号谓词；`ult/ule/ugt/uge` 若本任务不覆盖，在完成区明确列出并说明由无符号比较需求时再补）降低到 `cmp*` + `br.*`；无条件 `br` → `jump`；基本块落地/fall-through/跳转目标正确（可参照 0628 `DL-058a`：`BR_CC` 设 `Custom` + `LowerBR_CC` + `BRCOND` 或 `SETCC`+`BRCOND`；`DL-058b` 补无符号）。
  - **无标志位 / compare-branch 约束（C17，只写任务书、不立 ADR/issue）**：DADAO **无标志位**（CZSO 取消）→ `cmp.*` 结果（−1/0/1）落 **rd**、`br.*` 测 rd/rb；**rd 用虚拟寄存器**（(A)，不设固定 RDCC、不做融合）；`==`/`!=`（`br.eq/ne`）省 cmp；`p==NULL` 用 **`br.z/nz {rb}`**（1 条）；`p==q` 用 `cmp.uo-rb` + `br.z`（2 条，**暂不新增指令**）。**`cmp.*` 的 SDNode 不得标 `SDNPCommutative`**（0628 教训）。
  - **指针比较（C14/`ADR-0018（C14）` D2）**：指针比较用 `cmp.uo-rb`（结果→RD，供 `br.*`/`cs.*`）。
  - **范围**：整数条件控制流（if/else、循环）。**不含** `select`/`setcc` 的独立值语义（→M4，若顺手支持需在完成区声明）、间接跳转、`jump` 表。
  - 不回归 `LLVM-034t`~`LLVM-036t`（GPRD/GPRB/算术/访存 MIR）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-058a`/`DL-058b`（只读溯源）。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 真实 MIR：
   - 条件：`define i64 @abs(i64 %x){ %c=icmp slt i64 %x,0  br i1 %c, label %neg, label %pos ... }` → 含 `cmp*` + `br.*` + 基本块标签；
   - 循环：`sum(1..N)` 类 IR → 含回边 `jump`。
3. 覆盖谓词矩阵：给出 `eq/ne/slt/sle/sgt/sge`（+ 无符号如有）各自的 MIR 片段；未覆盖项须显式列出。
4. `llc -verify-machineinstrs -stop-after=finalize-isel` 退出 0。
5. 补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
6. 一键证据脚本 `.work/evidence/LLVM-037t/run.sh`（规格同 `LLVM-033t`；反例注入：改一个谓词映射/分支目标 → 预期 FAIL）。

## 完成区

**测试结果**：通过 **13/13**（一键证据脚本 `.work/evidence/LLVM-037t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（把 `CmpThenBranch` 的 `Unsigned ? CMPU : CMP` 改成恒 `CMPU` → 重建 → `p_slt` 的 signed cmp 消失（变 `cmp_uo`）→ 预期 FAIL → 还原 + 重建 → 回绿；源码 sha256 一致、`git status` 干净）。`make check` `EXIT=0`（lit 33/33）；`make check-patch-tree` 77 patches OK；`make check-source-state` OK（`HEAD=43e5256a30 count=1 clean=True`）；`make check-instrinfo` 0 errors。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 = `43e5256a30193bd80d5e924dc5b8173e1565cd42`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`；共 5 文件修改）：
- `llvm/lib/Target/DADAO/DADAOInstrInfo.td`：新增 `brtarget12/18/24 : Operand<OtherVT>`（CodeGen 用 MBB 目标；MC 复用 `DADAOImmAsmOperand` + `DecodeSImm*`，无 `OPERAND_PCREL`）；把条件/无条件分支的立即数操作数由 `imms*` 改为 `brtarget*`（`br.eq/ne`(12)、`br.n/nn/z/nz/p/np`(18)、`br.z/nz`-rb(18)、`jump`(24)）并加 `isBranch`/`isTerminator`（`jump` 另加 `isBarrier`）。
- `llvm/lib/Target/DADAO/DADAOCodeGen.td`：新增 `DADAOISD::{CMP,CMPU,BRN,BRNP,BRP,BRNN,BRZ,BRNZ,BREQ,BRNE}` SDNode（`CMP/CMPU` 用 `SDTIntBinOp`、**不标 `SDNPCommutative`**）、`immu12imm` ImmLeaf 与 pattern（signed→`cmp.so`/`cmp.si`，unsigned→`cmp.uo`/`cmp.ui`，`==`/`!=` 双寄存器→`br.eq/ne`，无条件 `br`→`jump`）。
- `llvm/lib/Target/DADAO/DADAOISelLowering.h`：新增节点枚举 + `LowerOperation`/`LowerBR_CC`/`LowerBRCOND`/`isPointerBankValue` 声明。
- `llvm/lib/Target/DADAO/DADAOISelLowering.cpp`：构造把 `ISD::BR_CC`(i64)/`ISD::BRCOND`(Other) 设 `Custom`；实现 `LowerBRCOND`（把 `SETCC`+`BRCOND` 折回 `BR_CC`；非 setcc 走 `zext`+`setne 0`）与 `LowerBR_CC`（eq/ne→`BRZ/BRNZ`/`BREQ/BRNE`/指针 `CMPU`，有序→`CMP`/`CMPU` + `BRN/BRNP/BRP/BRNN`；cover signed 6 + unsigned 4；超 12 位立即数常量显式报错）。
- `llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp`：`Select` 新增银行感知选择——`DADAOISD::CMPU` 两 GPRB→`cmp_uo_dbb`，`DADAOISD::BRZ/BRNZ` GPRB→`br_z_rb`/`br_nz_rb`（TableGen 对 i64 操作数不区分寄存器类、会插 GPRB→GPRD copy）。

DADAO-v5 仓库：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfo.td,DADAOCodeGen.td,DADAOISelLowering.cpp,DADAOISelLowering.h,DADAOISelDAGToDAG.cpp}.patch`（由 `tools/infra/make_patch.py llvm-project` 从真实源导出，未手改）+ `components/llvm-project/changelog.md`；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-037t/run.sh`；日志 `.work/log/llvm/LLVM-037t-*.log`；临时 `/tmp/opencode/LLVM-037t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`；完整 log `.work/log/llvm/LLVM-037t-acceptance.log`）：

1. **构建（验收 1）**：`ninja -j8 -C .work/build/llvm llc` → `BUILD_EXIT=0`（`[14/14] Linking CXX executable bin/llc`）。

2. **真实 MIR（验收 2）**。`llc -march=dadao -stop-after=finalize-isel`，`EXIT=0`：
```
abs (icmp slt %x,0 + br):
  bb.0.entry:  %1:gprd = cmp_si_rd %0, -1 ; br_p_rd killed %1, %bb.2 ; jump_iiii %bb.1
  bb.1.neg: ... ; bb.2.pos: ...
  （含 cmp* + br.* + 基本块标签 bb.1/bb.2；InstCombine 把 slt x,0 规范化成 sle x,-1）

sum_while（while 形式，回边为无条件 jump）:
  bb.1.cond: %7:gprd = cmp_so %0, %4 ; br_p_rd killed %7, %bb.3 ; jump_iiii %bb.2
  bb.2.body: %2:gprd = ADD_PSEUDO %1, %0 ; %3:gprd = ADD_IMM_PSEUDO %0, 1 ; jump_iiii %bb.1   ← 回边
```

3. **谓词矩阵（验收 3）**（`p_<pred>` 双寄存器 IR；`p_slt` 等因 fall-through 反转分支，同谓词允许 direct/inverted 两极性）：
```
eq  : br_ne_rd %0, %1, %bb.2                       （省 cmp；br.eq/ne 双寄存器）
ne  : br_eq_rd %0, %1, %bb.2
slt : cmp_so %0,%1 + br_nn_rd    sle : cmp_so + br_p_rd
sgt : cmp_so + br_np_rd          sge : cmp_so + br_n_rd
ult : cmp_uo + br_nn_rd          ule : cmp_uo + br_p_rd
ugt : cmp_uo + br_np_rd          uge : cmp_uo + br_n_rd
```
   未覆盖：`eq/ne/slt/sle/sgt/sge` 6 个有符号谓词**全覆盖**；**额外覆盖** `ult/ule/ugt/uge` 4 个无符号谓词（`cmp.uo`）。`setcc`/`select` 独立值语义**不覆盖**（→M4）。

   **指针比较（C14 D2 / C17）**：
```
pptr_null    (p == null) : br_nz_rb %0, %bb.2                 ← 单条 br.nz {rb}
pptr_neqnull (p != null) : br_z_rb %0, %bb.2                  ← 单条 br.z {rb}
pptr_eq      (p == q)    : cmp_uo_dbb %0, %1 + br_nz_rd %2    ← cmp.uo rd, rb, rb + br
```

4. **验收 4**：`llc -march=dadao -verify-machineinstrs -stop-after=finalize-isel` 对 14 个 IR（abs/sum/p_*×10/pptr_*×2）`VERIFY_ALL_EXIT=0`。

5. **验收 5（补丁 + 门控）**：
```
python3 tools/infra/make_patch.py llvm-project → 3 written/42 unchanged（最终态 0 written, 45 unchanged）EXIT=0
make check-patch-tree    → 2 component(s), 77 patches OK            EXIT=0
make check-source-state  → llvm-project: OK HEAD=43e5256a30 count=1 clean=True  EXIT=0
make check-instrinfo     → === Result: 0 errors ===                 EXIT=0
make check-lit           → Total 33, Passed 33 (100.00%)            EXIT=0
make check               → repository checks: PASS                  EXIT=0
```

6. **验收 6（一键证据脚本）**：
```
$ .work/evidence/LLVM-037t/run.sh; echo "EXIT=$?"
[PASS] llc-exists ... [PASS] llc-version
[PASS] mir-abs-compare-branch | rc=0 cmp=1 br=1 lbl=1
[PASS] mir-sum-backedge-jump | rc=0, jump_iiii %bb.1
[PASS] predicate-matrix | all 10 predicates
[PASS] pointer-compare | p==NULL: br.z/nz_rb; p==q: cmp_uo_dbb+br
[PASS] verify-machineinstrs | all-clean
[PASS] regress-034-036 | arith ADD/SUB + ld.o + gprb present
[PASS] source-invariants | cmp not SDNPCommutative; jump barrier; brtarget operands
[PASS] patch-export ... [PASS] check-patch-tree ... [PASS] check-source-state ... [PASS] check-lit
RESULT: PASS (checks complete, 0 failures)
EXIT=0

$ .work/evidence/LLVM-037t/run.sh --inject; echo "EXIT=$?"
inject: breaking the signed/unsigned compare mapping (CMP -> CMPU) ...
inject: dirty: llvm/lib/Target/DADAO/DADAOISelLowering.cpp
inject: [EXPECTED-FAIL] p_slt signed cmp gone: cmp_uo
inject: restoring source and rebuilding ... restore sha256 unchanged (7943ea18573f...)
inject: [PASS] p_slt signed cmp back
inject: PASS (injection FAILed the signed-cmp mapping; restore sha256 unchanged; green again)
EXIT=0
```

**新发现/坑**：

1. **TableGen 对 i64 操作数不区分寄存器类**：`(DADAOBrz GPRB:$v, bb) -> br_z_rb` 这类 pattern 在生成的 matcher 里**没有寄存器类检查**（scope 里 GPRD/GPRB 两个分支都是无条件 `MorphNodeTo`，先到先得），结果选 `br_z_rd` 并插入 GPRB→GPRD 的 COPY；`cmp_uo_dbb` 亦然。故银行敏感选择必须放在 `DADAOISelDAGToDAG::Select`（同 LLVM-035t 的 `sub.o`），TableGen 只留 GPRD 形式。
2. **手工构造 chained 分支机器节点必须把输入 chain 作为最后一个操作数**：`CurDAG->SelectNodeTo(Node, Opc, MVT::Other, val, bb, chain)`（照生成 matcher 的 `OPC_MorphNodeTo0Chain`）。若漏掉 chain，`InstrEmitter::countOperands` 会把 `OtherVT`（== `MVT::Other`）的 BasicBlock 当成 chain 丢掉，导致 `#operands for dag node doesn't match .td file!` 断言（本任务实测踩到）。
3. **fall-through 反转会翻转分支极性**：`SelectionDAGBuilder::visitSwitchCase` 在 true 块是 fall-through 时交换目标并取反条件，故 MIR 里 `eq`→`br_ne_rd`、`slt`→`cmp_so`+`br_nn_rd`（direct 为 `br_n`）。谓词→opcode 的核验须接受 {direct, inverted} 两极性；反例注入也需注意——改单个 `case ISD::SETLT` 可能**不影响** `p_slt`（其 CC 被规范化/反转成 `SETGE`），可靠注入点是 `CmpThenBranch` 的有/无符号选择。
4. **分支常量比较超 12 位立即数的处理**：`cmp.si`(imms12)/`cmp.ui`(immu12) 覆盖范围内正常选；超范围（如 `icmp slt x, 5000`）**显式 `report_fatal_error`**（不静默编错）——M3 未做常量材料化到比较寄存器。
5. **`DADAOInstrInfo.td` 是「生成」文件但长期被手改**（035t patterns / 036t mayLoad/036t、本任务 brtarget 操作数）：`tools/llvm/generate_instrinfo.py` 会按 `imms*` 重新生成分支操作数，**重跑生成器会丢失 brtarget**。属 LLVM-046t「instrinfo 生成器/校验器刷新」范围，未在本任务改（`check-instrinfo` 只校验编码身份，绿灯）。
6. **`isPointerBankValue` 仅识别 `CopyFromReg` 的 GPRB vreg**（同 LLVM-035t）：复杂指针表达式（GEP 结果等）做 `p==q`/`p==NULL` 时可能退回普通整数形式（`br.eq/ne` 或 `cmp`+`br`），语义仍正确但非 `cmp.uo-rb`/`br.z {rb}` 单条形式。

**遗留问题**：

- **`setcc`/`select` 的独立值语义未实现**（任务范围明示 →M4）：本任务只覆盖「icmp 直接喂 br」的条件控制流。已验证 `br i1 %c`（非 icmp）走 `zext`+`and 1`+`br_z` 语义正确。
- **常量比较超 12 位立即数显式失败**（见坑 4）：需 M4 常量材料化到 RD 后 `cmp.so/cmp.uo` 才能覆盖。
- **`jump_rrii`/`call_*` 未转 brtarget 操作数**：ISel 未选择它们（无条件 `br` 用 `jump_iiii`）；`call`/`ret` 真发射与 `.s` 归 LLVM-039t/040t。
- **生成器/校验器刷新（LLVM-046t）**：`generate_instrinfo.py` 尚不会产出 brtarget 操作数（见坑 5）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：组件源码 5 文件（`DADAOInstrInfo.td` 的 brtarget/分支操作数改造、`DADAOCodeGen.td` 的 SDNode+pattern、`DADAOISelLowering.{h,cpp}`、`DADAOISelDAGToDAG.cpp`）；5 份导出补丁；`components/llvm-project/changelog.md`；`.work/evidence/LLVM-037t/run.sh`。

**审查要点（逐行）**：
- **逻辑正确性**：`LowerBR_CC` 谓词映射与 `contract-isa.md §6.2/§7.3/§8` 一致（cmp 结果 −1/0/1；`res<0→BRN`、`≤0→BRNP`、`>0→BRP`、`≥0→BRNN`；eq/ne→`BRZ/BRNZ`）；`Cmp`/`BrOn`/`CmpThenBranch` 的常量 12 位范围检查按有/无符号分别取 `simm12`/`uimm12`；eq/ne 先 swap 常量到 RHS 再用 `br.z/nz`（等价对称）；指针路径 `isPointerBankValue` 双 GPRB→`cmp_uo_dbb`、单指针+0→`br.z/nz {rb}`；无条件 `br`→`jump_iiii`。`DADAOISD::CMP/CMPU` 不标 `SDNPCommutative`。
- **设计/惯用法**：无标志位 cmp→rd→br 两指令（C17，无固定 RDCC/不融合）；银行敏感选择放 ISelDAGToDAG（TableGen 不可靠，同 035t）；分支操作数用 `Operand<OtherVT>`（Lanai/0628 范式）、MC 复用既有 `PCRel_12/18/24` fixup（未引新概念）；未改已有函数签名（仅新增 override/私有 helper）、未引外部依赖。
- **防造假**：完成区所有输出为真实 `llc`/`make` 运行后 `cmd > log 2>&1; rc=$?` 捕获；证据脚本 `--inject` 真实改源码（sha256 变化 + `git diff` 非空）、真实重建、真实预期 FAIL、真实还原（sha256 + `git status` 双证）+ 重建回绿；脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee`。
- **边界**：6 有符号 + 4 无符号谓词；eq/ne 双寄存器 vs 非零常量（`cmp_ui_rd`）；有序 vs 0 常量（`cmp_si_rd`）；指针 `==/!= NULL`、`p==q`；无条件回边 `jump`；`-verify-machineinstrs` 14 例全绿；超 12 位常量显式失败。
- **越界**：仅改任务相关 5 个组件源文件 + 5 份导出补丁 + `changelog.md`（`Process-01 §162` 强制，已披露）+ 本任务书；`.work/source/llvm-project` 收敛 base+1 且干净。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 手工 `SelectNodeTo` 建 chained 分支节点漏传输入 chain → `InstrEmitter` 断言 `#operands for dag node doesn't match .td file!`（`pptr_null` rc=134） | ✅已修 | `DADAOISelDAGToDAG.cpp` 的 BRZ/BRNZ custom 分支把 `Node->getOperand(0)`（chain）作为最后操作数传入 | `pptr_null` MIR 得 `br_nz_rb %0, %bb.2`；14 例 `-verify-machineinstrs` 全绿 |
| 2 | `LowerBRCOND` 非 setcc 回退用 `getAnyExtOrTrunc(i1→i64)`，高位垃圾会使 `!= 0` 误真 | ✅已修 | 改为 `DAG.getZExtOrTrunc(Cond, DL, MVT::i64)` | `brarg`（`br i1 %c`）MIR `and_o` + `br_z_rd`，`-verify-machineinstrs` rc=0 |
| 3 | 证据脚本矩阵正则 `cmp_(so|si)_rd` 漏匹配 `cmp_so`/`cmp_uo`（def 名无 `_rd`），误报 8 谓词缺 | ✅已修 | 改为 `cmp_(so|si_rd)` / `cmp_(uo|ui_rd)`；abs 检查同理放宽 | `run.sh` `[PASS] predicate-matrix`（13/13） |
| 4 | `--inject` 首版改 `case ISD::SETLT`，但 `p_slt` 的 CC 被规范化/反转成 `SETGE`，注入无效果 | ✅已修 | 注入点改为 `CmpThenBranch` 的有/无符号选择（恒 `CMPU`），检测 `p_slt` 的 `cmp_so` 消失 | `--inject`：`[EXPECTED-FAIL] p_slt signed cmp gone: cmp_uo` → 还原回绿，EXIT=0 |
| 5 | `DADAOISelLowering.{h,cpp}`/`DADAOCodeGen.td` 文件头注释未提 LLVM-037t | ✅已修 | 补 compare/branch（C17/C14）说明 | 重建 `BUILD_EXIT=0`；`run.sh` 13/13 |

**自审判决**：finding #1–#5 全部 ✅已修 + 复验，无未修项。证据脚本 13/13 PASS 且 `--inject` 具备可达 FAIL（signed cmp 消失）与可复原性（sha256 + `git status` + 重建回绿）；完成区结论与真实输出逐条对齐；`make check`/`check-patch-tree`/`check-source-state`/`check-instrinfo`/`check-lit` 全绿。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**重跑证据脚本**（`.work/evidence/LLVM-037t/run.sh`，完整 log `.work/log/llvm/LLVM-037t-review-run.log` + `/tmp/opencode/LLVM-037t-review/run.log`）：

```
[PASS] llc-exists | expected: executable .../bin/llc | actual: exists+exec | rc=0
[PASS] llc-version | expected: rc=0 and dadao registered | actual: rc=0, match=yes | rc=0
[PASS] mir-abs-compare-branch | expected: rc=0, cmp*=yes, br*=yes, labels=yes | actual: rc=0 cmp=1 br=1 lbl=1 | rc=0
[PASS] mir-sum-backedge-jump | expected: rc=0, unconditional back-edge jump_iiii %bb.1 | actual: rc=0, match=yes | rc=0
[PASS] predicate-matrix | expected: all 10 predicates select cmp*/br* | actual: all present | rc=0
[PASS] pointer-compare | expected: p==NULL: br.z/nz_rb; p==q: cmp_uo_dbb+br | actual: ok | rc=0
[PASS] verify-machineinstrs | expected: rc=0 for 14 IRs | actual: all-clean | rc=0
[PASS] regress-034-036 | expected: arith ADD/SUB + ld.o + gprb present | actual: ok | rc=0
[PASS] source-invariants | expected: cmp not SDNPCommutative; jump barrier; brtarget operands | actual: ok | rc=0
[PASS] patch-export | expected: 5 changed patches valid | actual: hunks=5 | rc=0
[PASS] check-patch-tree | expected: make rc=0 | actual: rc=0 | rc=0
[PASS] check-source-state | expected: make rc=0 | actual: rc=0 | rc=0
[PASS] check-lit | expected: make rc=0 | actual: rc=0 | rc=0
RESULT: PASS (checks complete, 0 failures)
EXIT=0
```

**证据脚本审查**：13 条断言，每条有可达 FAIL 路径（`ok=0` → `miss` → `FAILS++`）。注入 `--inject` 改 `CmpThenBranch` 的 signed/unsigned 选择（`CMP→CMPU`），SHA 变化 + `git diff` 非空 + 重建 + `p_slt` signed cmp 消失 + 还原 SHA 一致 + `git status` 干净 + 重建回绿。结尾 `exit "$rc"` 无 `tee`。**脚本合格**。

**独立注入**（与 engineer 的 `CMP→CMPU` 不同）：

- **注入点**：`isPointerBankValue()` 函数体首行插入 `return false;`（禁用指针银行检测），使 `p==q` 走整数寄存器路径而非 `cmp_uo_dbb+br`
- **注入确认**：SHA 从 `7943ea18...` → `0dc2b646...`（变化 ✓），`git diff --name-only` 非空 ✓，`grep` 定位注入行 ✓
- **重建**：`ninja -j8 -C .work/build/llvm llc` → `REBUILD_EXIT=0`
- **注入后 MIR 验证**：`pptr_eq` 出 `br_ne_rd`（整数路径），无 `cmp_uo_dbb` → 证据脚本 `[FAIL] pointer-compare | rc=0/0 mismatch | rc=1`
- **注入后脚本运行**：`EXIT=1`，主目标 `[FAIL] pointer-compare` + 3 个级联 FAIL（脏源码→patch/source-state 不通过）
- **还原**：`cp -f` 恢复备份 → SHA = `7943ea18573f390d156cd5eb1f23a6830ba5433b082555881d696371ea0318ff`（一致 ✓）→ `git diff --name-only` 空 ✓
- **重建回绿**：`ninja -j8` → `REBUILD_EXIT=0` → 证据脚本 `EXIT=0`，13/13 PASS

**独立复核验收 2–5**：

| 验收项 | 结果 | 证据 |
|--------|------|------|
| 2. abs→cmp*+br.*+块标签 | ✅ | MIR: `cmp_si_rd` + `br_p_rd` + `bb.1.neg`/`bb.2.pos` |
| 2. sum 循环→回边 jump | ✅ | MIR: `jump_iiii %bb.1` |
| 3. 谓词矩阵 eq/ne/slt/sle/sgt/sge + ult/ule/ugt/uge | ✅全覆盖 | 10 个谓词各生成正确 cmp/br；fall-through 反转语义正确（eq→br_ne_rd，slt→cmp_so+br_nn_rd） |
| 3. p==NULL→br.z/nz {rb} | ✅ | `br_nz_rb %0, %bb.2`（单条，无 cmp） |
| 3. p==q→cmp_uo_dbb+br | ✅ | `cmp_uo_dbb %0, %1` + `br_nz_rd` |
| 3. 指针比较走 cmp.uo-rb（C14 D2） | ✅ | `isPointerBankValue` 检测 GPRB→`cmp_uo_dbb` |
| 4. -verify-machineinstrs EXIT=0 | ✅ | 14 例全绿（abs/sum/p_*×10/pptr_*×2） |
| 5. check-patch-tree 77 | ✅ | 77 patches OK |
| 5. check-lit 33/33 | ✅ | Total 33, Passed 33 (100.00%) |
| 5. make check EXIT=0 | ✅ | repository checks: PASS |

**C17 约束核验**：

| 约束 | 状态 | 证据 |
|------|------|------|
| `cmp.*` SDNode 无 `SDNPCommutative` | ✅ | `DADAOCodeGen.td`: `def DADAOCmp : SDNode<"DADAOISD::CMP", SDTIntBinOp>;` — 无 `[SDNPCommutative]` |
| `==`/`!=` 用 `br.eq/ne` | ✅ | 谓词矩阵 eq→br_ne_rd、ne→br_eq_rd（fall-through 反转） |
| rd 用虚拟寄存器（无固定 RDCC） | ✅ | MIR 全用 `%N:gprd` 虚拟寄存器 |
| `p==NULL` 用 `br.z/nz {rb}` | ✅ | `br_nz_rb`（单条，无 cmp） |
| `p==q` 用 `cmp.uo-rb`（C14 D2） | ✅ | `cmp_uo_dbb`（bank 感知 ISelDAGToDAG 选择） |

**Fall-through/极性核验**：`SelectionDAGBuilder::visitSwitchCase` 在 true 块为 fall-through 时交换目标并取反条件。MIR 实测：`eq`→`br_ne_rd`（BRZ 反转）、`slt`→`cmp_so`+`br_nn_rd`（BRN 反转为 BRNN）。矩阵检查接受 {direct, inverted} 两极性——**语义正确，非 bug**。

**披露判定**（非阻塞）：

| 项 | 判定 | 理由 |
|----|------|------|
| `setcc`/`select`→M4 | ✅ 非阻塞 | 任务范围明示「不含 select/setcc 独立值语义」；已验证 `br i1 %c` 走 zext+setne 语义正确 |
| 常量比较超 12 位 `report_fatal_error` | ✅ 非阻塞 | 显式报错（不静默编错），需 M4 常量材料化 |
| `jump_rrii`/`call_*` brtarget 化→LLVM-040t | ✅ 非阻塞 | ISel 未选择它们，call/ret 归 039t/040t |
| `generate_instrinfo.py` 不产 brtarget→LLVM-046t | ✅ 非阻塞 | `check-instrinfo` 0 errors（只校验编码身份） |

**判决：Accepted**

验收命令块在独立重跑下全部通过（13/13 EXIT=0）。独立注入（`isPointerBankValue` 禁用→`pptr_eq` 无 `cmp_uo_dbb`→`[FAIL] pointer-compare`）验证了指针比较路径的可失败性与可还原性（SHA+git status+重建回绿）。C17/谓词矩阵/披露全部核验通过。无阻断发现。

