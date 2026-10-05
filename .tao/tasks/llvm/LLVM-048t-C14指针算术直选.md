# LLVM-048t: C14 指针算术直选（base+offset → GPRB 单条 `add.o`）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-036t`（访存/地址）、`LLVM-038t`（栈帧）、`LLVM-035t`（ISelDAGToDAG 结构）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`ISS-137`（`LLVM-036t` 披露：C14 D1 指针算术未直接落 GPRB）；`tests/codegen/ptr_add_offset.ll`（`TESTCASES-026t`，实测走 `rb2rd`/`rd2rb`）；`ADR-0018（C14）` D1；v5 指令定义。
- **输出**：指针（GPRB）算术 `base + offset` 直接选 **`add.o`（orrr，`rb` 目的 = `add.o_orrr_bbd`，RB+RB→RB）**，而非「搬到 GPRD 做算术再搬回 GPRB」；导出的补丁。
- **约束**：
  - **语义事实**：`add.o_orrr_bbd`（op 0x30；`adr-0012 D9` 改名/改槽）为 RB 目的、RB+RB→RB 的 64 位加。指针 bank = GPRB（C1/C2）。
  - **目标**：`getelementptr` / 地址计算中的 **指针 + 偏移**（偏移亦为 GPRB 值）在 `SelectionDAG` 选择阶段落到 `add.o_orrr_bbd`；**不得**再用 `rb2rd`×N + GPRD `add` + `rd2rb` 兜底。
  - **bank 归属判定**：沿用 `LLVM-035t`/`037t` 的 `isPointerBankValue`（GPRB vreg / `CopyFromReg`）思路，判「两操作数是否均指针 bank」；是 → 选 `add.o_orrr_bbd`；否 → 维持 GPRD 算术。
  - **范围**：**仅** `ptr(基址) + 偏移`（GPRB+GPRB→GPRB）。**不含**：`ptr−ptr`（已由 `sub.o_orrr_dbb` 覆盖，`SPEC-100t`）、小偏移已由访存 `[rb, imm12]`（`LLVM-036t`）直接承担的路径、指针×常数（→M4 若需要）。不改 `contracts/**`。
  - 不回归 `LLVM-033t`~`LLVM-041t` 的 MIR；不回归 `make check-lit`；不改 `tests/codegen/**` 的期望值语义（若 `ptr_add_offset.ll` 的 MIR 覆盖点更新，须保持 independent oracle 与覆盖声明一致，作为本任务的**验证受益方**记录）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 指针算术 bank 处理（只读溯源，非执行依赖）。

## 验收标准

1. `ninja -C .work/build/llvm llc` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 对 `tests/codegen/ptr_add_offset.ll`（或等价最小 IR）：
   - 含 `add.o`（orrr，**`rb` 目的**、两操作数 **GPRB**）；
   - **无** `rb2rd`/`rd2rb` 兜底搬运（`grep -c` 核对）；
   - 反例：把偏移改成非指针（GPRD）值 → **不选** `add.o`（退回 GPRD 算术），证明 bank 判定可达 FAIL。
3. `llc -verify-machineinstrs`（`-O0`~`-O2`）EXIT=0。
4. **语义正确**：给至少一组「base + 非零偏移」样本，独立核对最终结果（host/Python 手算，不取自 `llc`/QEMU）；本任务只保证选择正确，端到端结果由 `INTEG-012t` 承接。
5. 不回归 `LLVM-033t`~`LLVM-041t`；补丁导出 + `make check-patch-tree` 通过；`make check-lit` 不回归。
6. 一键证据 `.work/evidence/LLVM-048t/run.sh`（规格同 `LLVM-033t`；反例注入：去掉 `add.o` 的 bank 选择条件/改 bank 判定 → MIR 检查 FAIL，再还原）。

## 完成区

> **任务书前提订正（已获用户裁定，2026-10-05）**：任务书称 `add.o_orrr_bbd` 为「RB+RB→RB、两操作数 GPRB」，但权威合约一致定义为 **RB+RD→RB**（`contract-isa.md §7.1`：`add.o rbhb, rbhc, rdhd` = base(rb)+offset(rd)→rb；`ADR-0012 D9.3`：`bbd`=(rb dst, rb, rd)；`contracts/opcodes.yaml` `add.o_orrr_bbd` 字段 dst `rbhb`(rb)/src `rbhc`(rb)/src `rdhd`(**rd**）；`DADAOInstrInfo.td:785` `add_o_bbd`=(outs GPRB),(ins GPRB,GPRD)）。**提问用户后裁定**：按合约实现——`base(rb)+offset(rd)`，**仅判 base 是否为指针 bank**（offset 保持 GPRD）；反例改为「**base 非指针 bank → 不选 `add.o`**」。任务书 §验收 2 的「两操作数 GPRB」「偏移改成非指针→不选」按此订正（若按字面则验收 2 不可达，且与 `ptr_add_offset.ll` 偏移为 GPRD 加载值矛盾）。

**测试结果**：通过 **13/13**（一键证据 `.work/evidence/LLVM-048t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（把 `Select` 的 `if (Base0 != Base1) {` 注入为 `if (false)` → 重建 → `mir-ptr-add-o`/`mir-ptrarg`/`mir-chain` 三条 **FAIL** → 还原 + 重建 → 回绿；`git diff --name-only` 非空、sha256 一致、`git status` 干净）。`make check` `EXIT=0`（lit 33/33、`repository checks: PASS`）；`make check-patch-tree` 80 patches OK；`make check-source-state` OK（`HEAD=da9f99c6a749 count=1 clean=True`）。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 = `da9f99c6a749deb962183d0b967b7d547e89079e`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`；共 **1** 文件修改）：
- `llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp`（sha256 `b324dd9334d2b8d76d9e87555abdaab9dbb217a9c5fe22098cbdc19f46d3113b`）：新增 `SelectPointerAdd`；`Select` 增 `case ISD::ADD`（恰好一个操作数指针 bank → `add_o_bbd`，结果留 GPRB）；`isPointerBankValue` 扩展为 ①`CopyFromReg`(GPRB vreg) ②`ISD::FrameIndex` ③`FRAME_ADDR`/`add_o_bbd` 机器节点 ④「恰好一个操作数指针 bank 的未选 `ISD::ADD`」（镜像选择规则，支持链式 GEP）；文件头注释同步。

DADAO-v5 仓库：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp.patch`（由 `tools/infra/make_patch.py llvm-project` 从真实源导出，未手改；sha256 `f0e0e51c80870f9b0303a2b76dc20bfa55b9a548874b13315ee6dea41f972cd5`）+ `components/llvm-project/changelog.md`（`Process-01 §12.162` 强制，追加 1 行）；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-048t/run.sh`；`.work/evidence/LLVM-039t/run.sh`（1 条断言改属性式，见遗留 #1）；日志 `.work/log/llvm/LLVM-048t-*.log`；临时 `/tmp/opencode/LLVM-048t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`；完整 log 见 `.work/log/llvm/LLVM-048t-*.log`）：

1. **构建（验收 1）**：`ninja -j8 -C .work/build/llvm llc` → `EXIT=0`：
```
[1/3] Building CXX object lib/Target/DADAO/CMakeFiles/LLVMDADAOCodeGen.dir/DADAOISelDAGToDAG.cpp.o
[2/3] Linking CXX static library lib/libLLVMDADAOCodeGen.a
[3/3] Linking CXX executable bin/llc
```

2. **验收 2 — 真实 MIR（`tests/codegen/ptr_add_offset.ll`，`llc -march=dadao -stop-after=finalize-isel`，`EXIT=0`）**：
```
    %1:gprb = FRAME_ADDR %stack.0.buf
    %2:gprd = ld_o_rd %stack.1.soff, 0 :: (volatile dereferenceable load ...)
    %3:gprb = add_o_bbd killed %1, killed %2        ← rb 目的；base GPRB；offset GPRD
    st_b_rd killed %4, %3, 0
    %5:gprd = ld_ub_rd %3, 0
```
- **含 `add.o`（orrr，`rb` 目的，base GPRB + offset GPRD）**；**无** `rb2rd`/`rd2rb`（`grep -cE 'rb2rd|rd2rb'` = **0**）。
- **发射汇编（post-RA）**：`add.o rb8, rb8, rd8`（`llc -filetype=asm`；整文件 `grep -cE '\b(rb2rd|rd2rb)\b'` = **0**）。
- **反例（base 非指针 bank）**：`define i64 @pure_add(i64 %a,i64 %b){ %r=add i64 %a,%b  ret i64 %r }` → `add_o_bbd` 计数 = **0**，含 `ADD_PSEUDO`（退回 GPRD 算术）。
- 补充（自测扩范围，均 `EXIT=0`）：指针形参 base `%2:gprb = add_o_bbd %0, %1`；链式 GEP 两条 `add_o_bbd`（`%3:gprb = add_o_bbd %0,%1` + `%4:gprb = add_o_bbd %3,%2`）；大常数偏移 `%2:gprb = add_o_bbd %0, CONST_WYDE 5000`；`ptrtoint(p)+x` 与交换序亦选 `add_o_bbd`。

3. **验收 3 — `-verify-machineinstrs`（`-O0`~`-O2`）**：证据脚本对 `ptr_add_offset`/`ptrarg`/`chain`/`pure_add` 4 个 IR × 3 优化级 = 12 次全 `EXIT=0`；另手工对 `bigoff`/`intadd`/`mixed`（及 `ptrarg`/`chain` 补充）等运行 `-verify-machineinstrs`（O0–O2）亦全 `EXIT=0`。`make check` 内含的 verifier 路径亦全绿。

4. **验收 4 — 语义正确（独立 host/Python 手算，不取自 `llc`/QEMU）**：`add.o`（`contract-isa.md §7.1`）为**全 64 位补码加**；GEP 语义 = base+offset(mod 2^64)。样本：
```
0x0000000000010000 + 0x0000000000001234 = 0x0000000000011234
0x0000000000002000 + 0xfffffffffffffff0 = 0x0000000000001ff0   (−16，64 位回绕)
```
并由 MIR 证实该程序选中 `add_o_bbd`（base GPRB、offset GPRD）。端到端结果由 `INTEG-012t` 承接（任务范围）。

5. **验收 5 — 补丁 + 门控 + 不回归**：
```
make check-patch-tree    → check-patch-tree: 2 component(s), 80 patches OK        EXIT=0
make check-source-state  → llvm-project: OK HEAD=da9f99c6a749 count=1 clean=True  EXIT=0
make check               → Total 33, Passed 33 (100.00%); repository checks: PASS EXIT=0
```
回归（非 inject，逐个重跑）：`LLVM-033t`(11/11)、`034t`(13/13)、`035t`(14/14)、`036t`(31/31)、`037t`、`038t`(15/15)、`039t`(14/14)、`040t`(16/16)、`041t`(19/19)、`044t`(21/21)、`046t`、`047t` 全 `EXIT=0`；`TESTCASES-026t` `EXIT=0`。`043t`/`045t` 各 1–2 条**硬编码 MC 计数**失败（见遗留 #2：与本次 codegen-only 改动无关）。本次改动面 = `git diff --name-only f15f1998b HEAD` = **仅 `DADAOISelDAGToDAG.cpp`**。

6. **验收 6 — 一键证据脚本（`.work/evidence/LLVM-048t/run.sh`）**：
```
$ bash .work/evidence/LLVM-048t/run.sh; echo "EXIT=$?"
[PASS] llc-exists ... [PASS] llc-version
[PASS] mir-ptr-add-o | ... add_o_bbd(gprb,gprb,gprd): [('3','gprb','1','2')] | rc=0
[PASS] mir-ptrarg | ... add_o_bbd(gprb,gprb,gprd): [('2','gprb','0','1')] | rc=0
[PASS] mir-chain | ... 2x add_o_bbd (chained GEPs) | rc=0
[PASS] no-bank-copy | ... 0 copies | rc=0
[PASS] counterexample-base-not-ptr | ... add_o_bbd=0 | rc=0
[PASS] verify-machineinstrs | ... all-clean (12 runs) | rc=0
[PASS] semantics-full64-add | ... ok | rc=0
[PASS] patch-hunks | ... [PASS] check-patch-tree | ... [PASS] check-source-state | ... [PASS] check-lit
RESULT: PASS (13 checks, 0 failures)
EXIT=0

$ bash .work/evidence/LLVM-048t/run.sh --inject; echo "EXIT=$?"
inject: disabling the ptr+offset bank selection condition (Base0 != Base1)
inject: dirty: llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp
inject: rebuild EXIT=0
inject: add.o MIR checks failed as expected (3 check(s))
inject: restoring source and rebuilding ... inject: rebuild EXIT=0
inject: restore sha256 unchanged (b324dd9334d2...)
inject: re-running add.o MIR checks (expect PASS) ...
inject: PASS (injection FAILed add.o MIR checks; restore sha256 unchanged; checks green again)
EXIT=0
```

**新发现/坑**：

1. **SelectionDAG ISel 的访问顺序是「使用者先于操作数」（topological 逆序）**：`SelectionDAGISel` 从根往 entry 方向遍历（`SelectionDAG.cpp::AssignTopologicalOrder` 把 root 放末尾，driver 从末尾回走）。因此选中某节点时其操作数**仍是原始 ISD 节点**（`allnodes` 断言「操作数尚未选中」）。这直接决定了两处实现细节：① `ptr_add_offset.ll` 的 base 在 ADD 选中时仍是 **`ISD::FrameIndex`**（尚未物化为 `FRAME_ADDR`），故 `isPointerBankValue` 必须识别 `ISD::FrameIndex`；② 链式 GEP 的外层 ADD 看到的内层 ADD 仍是 **`ISD::ADD`**，故须递归识别「将选为 `add_o_bbd` 的未选 ADD」。指针形参情形不受影响（`CopyFromReg` 不是机器节点，常驻）。
2. **`-stop-after=finalize-isel` 的跨 bank 搬运显示为通用 `COPY`，不是 `rb2rd`/`rd2rb`**：`copyPhysReg` 在 RA 后才把 COPY 物化为 bank 搬运指令。故仅 grep `rb2rd/rd2rb`（finalize-isel）恒为 0、无鉴别力；证据脚本另加 **post-RA 汇编** 的 `rb2rd/rd2rb` 计数（=0）+ MIR 操作数寄存器类核对（dst/base gprb、offset gprd）。
3. **去掉 `rb2rd`/`rd2rb` 后，指针返回 `rb31` 的 `CopyToReg` 被 RA 合并**：`039t` 证据脚本断言 `$rb31 = COPY`，现为 `$rb31 = add_o_bbd ...`（结果直接落 rb31，更优）。该断言改属性式（见遗留 #1）。属**语义改进**（少一条搬运），非功能回归。
4. **`ptrtoint(p) + x` 亦选 `add.o`**：base 为指针 bank 即选 `add.o`（结果 GPRB），若结果作 i64 数据用则再加一条 GPRB→GPRD `COPY`（较改前多一条）。语义正确，且与用户裁定「仅判 base」一致；`intadd`/`commuted` 实测 `EXIT=0`。
5. **`llc -stop-after=finalize-isel` 的 ADD 若 base 为 FRAME_ADDR/`add_o_bbd`，其机器节点操作数在 `ReplaceNode` 后才更新**：`getMachineNode` 接受未选操作数 SDValue，后续 `ReplaceNode` 就地把 `FRAME_ADDR`/`add_o_bbd` 回填，`-verify-machineinstrs` 全绿。
6. **`isPointerBankValue` 递归识别未选 ADD = 镜像选择规则，二者必须一致**：任何一方改动须同步（否则「判为指针 bank 但不选 add.o」会留下类型/银行不一致）。已在注释中写明。

**遗留问题**：

1. **`LLVM-039t` 证据脚本 1 条断言改为属性式（✅已处理，披露）**：`check_csr_rb` 的 `ret = bool(re.search(r"\$rb31 = COPY", body))` → `r"\$rb31 = (COPY|add_o_bbd)"`。原因：本次改动使指针结果直接落 `$rb31`（无 COPY），断言检查的**属性（返回值在 rb31）不变**。属 `.work/evidence/`（gitignored），不影响仓库交付物；`039t` 复跑 14/14。
2. **`LLVM-043t`/`045t` 各有硬编码 MC 计数失败（非本任务引入，非阻塞）**：`043t` 期望 `114 patterns OK`/`27 MC`、`045t` 期望 `28 MC`，当前分别为 `110`/`29`/`29`。这是 **MC 侧**文件（`tests/lit/MC/Dadao`、`check_lit_bytes.py`）计数，由 `044t`/`046t`/`047t` 等后续任务新增用例后陈旧；本次改动面仅 `DADAOISelDAGToDAG.cpp`（`git diff --name-only f15f1998b HEAD` 仅此一文件），**不可能影响 `llvm-mc`/lit MC**，且任务书 §验收 5 的回归范围为 `LLVM-033t`~`041t`（全绿）。建议随文档/计数小任务统一刷新。
3. **`isPointerBankValue` 递归最坏 O(n²)**（每个 ADD/SUB/CMPU/BRZ 节点遍历其子树）：典型函数可忽略；如需极致可缓存。未处理，非阻塞。
4. **链式 GEP 以上均已单条 `add.o`；但「偏移亦为指针 bank」（`ptr+ptr`，C14 D5 未建模）仍退回 `ADD_PSEUDO`**：按裁定 `add.o` 仅一个 RB 操作数，无对应指令；`ptr+ptr` 非合法地址运算。属本任务范围外（任务书 §范围排除）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围（逐行）**：组件源码 1 文件 `DADAOISelDAGToDAG.cpp`（`isPointerBankValue` 扩展、`SelectPointerAdd`、`Select` 的 `ISD::ADD` 分支、文件头注释）；导出补丁；`components/llvm-project/changelog.md`；`.work/evidence/LLVM-048t/run.sh`。

**审查要点（逐行）**：
- **逻辑正确性**：`Select` 的 `ISD::ADD` 分支先判 `getValueType(0)==MVT::i64`，再 `Base0 != Base1`（恰好一个指针 bank）→ `SelectPointerAdd(Node, Base, Offset)`；**两操作数均指针 bank 或均非指针 → `break` 退回 `ADD_PSEUDO`**（`add.o` 仅一个 RB 操作数，`ptr+ptr` 无对应指令，C14 D5）。`SelectPointerAdd` 建 `add_o_bbd`（MVT::i64 结果，operand 顺序 = base,offset），与 `contract-isa §7.1`/`ADR-0012 D9.3` 一致。`isPointerBankValue` 四个来源：`CopyFromReg`(GPRB vreg，含 `R.isVirtual()` 守卫)、`ISD::FrameIndex`、`FRAME_ADDR`/`add_o_bbd` 机器节点、未选 `ISD::ADD`（返回 `B0 != B1`，**与 Select 分支规则逐字对应**）。递归无环（DAG 无环）。`ISD::SUB`/`CMPU`/`BRZ` 调用点行为随之增强（一致性）。
- **设计/惯用法**：bank 感知选择仍集中在 `DADAOISelDAGToDAG`（i64 通吃下唯一可靠机制，同 LLVM-035t/037t）；`add.o` 已有 MC def（`add_o_bbd`，`Pattern=[]`），本任务只加选择、不重定义编码；未改架构/ABI/函数签名（仅新增成员函数 + override 不变）；未引外部依赖；未引 constant pool。
- **防造假**：完成区所有输出为真实 `llc`/`ninja`/`make` 运行后 `cmd > log 2>&1; rc=$?` 捕获；证据脚本 `--inject` 真实改源码（sha256 变化 + `git diff --name-only` 非空）、真实重建、真实 3 条 FAIL、真实还原（cp + sha256 一致 + `git status` 干净）+ 重建回绿；脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码。
- **边界**：alloca/FRAME_ADDR base、指针形参 base、链式 GEP、大常数偏移、`ptrtoint+add`、交换序、base 非指针（反例）、`-O0/-O1/-O2`、`-verify-machineinstrs`（24 次）均实测；`make check`/`check-patch-tree`/`check-source-state`/`check-lit` 全绿。
- **越界**：仅改任务列出的组件源码 1 文件 + 导出补丁 + `changelog.md`（`Process-01 §162` 强制，已披露）+ 本任务书；未改 `contracts/**`、`tests/codegen/**`、`spec/**`；`.work/source/llvm-project` 收敛 base+1 且干净。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 初版 `isPointerBankValue` 仅识别 `CopyFromReg`/机器节点 → `ptr_add_offset.ll` 的 base 在选中时仍是未物化 `ISD::FrameIndex`，`add.o` 未被选（实测 `add_o_bbd=0`，仍 `ADD_PSEUDO`+COPY） | ✅已修 | 加 `ISD::FrameIndex → true` | `ptr_add_offset` MIR `%3:gprb = add_o_bbd %1,%2`；`mir-ptr-add-o` PASS |
| 2 | 链式 GEP 外层未选（内层 ADD 仍是原始 `ISD::ADD`，`add_o_bbd=1` 而非 2） | ✅已修 | `isPointerBankValue` 加「未选 i64 ADD → `B0 != B1`」递归 | `chain` MIR 2×`add_o_bbd`；`mir-chain` PASS |
| 3 | 验收 2 的「`grep -c rb2rd/rd2rb`」在 `finalize-isel` 恒 0、无鉴别力（跨 bank 显示为通用 COPY） | ✅已修 | 证据脚本另加「post-RA 汇编 `rb2rd/rd2rb` 计数」+ MIR 操作数寄存器类核对 | `no-bank-copy`（汇编 0 copies）+ `mir-*` PASS |
| 4 | 任务书前提与合约冲突（`add.o` 实为 RB+RD，非 RB+RB）；按字面验收 2 不可达 | ✅已修（用户裁定） | 按合约实现（仅判 base 指针 bank）；反例改「base 非指针」；任务书前提订正记于完成区 | 用户裁定（2026-10-05）；`counterexample-base-not-ptr` PASS |
| 5 | 去 `rb2rd/rd2rb` 后 `039t` 断言 `$rb31 = COPY` 因 RA 合并而 FAIL（`$rb31 = add_o_bbd`） | ✅已修（披露） | `.work/evidence/LLVM-039t/run.sh` 断言改属性式 `\$rb31 = (COPY|add_o_bbd)` | `LLVM-039t` 复跑 14/14（`ret-rb31=True`） |

**自审判决**：finding #1–#5 全部 ✅已修 + 复验，无未修项。证据脚本 13/13 PASS 且 `--inject` 具备可达 FAIL（3 条 add.o MIR 检查）与可复原性（sha256 + `git status` + 重建）；完成区结论与真实输出逐条对齐；`make check`/`check-patch-tree`/`check-source-state`/`check-lit` 全绿；回归 `033t`~`041t` 全绿（`043t`/`045t` 的 MC 计数陈旧为既有、与改动面无关，已披露）。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查日期**：2026-10-05

---

##### 一、证据脚本审查（`.work/evidence/LLVM-048t/run.sh`）

逐条核对 13 条断言：

| # | 检查名 | 类型 | FAIL 路径可达 | 注入有效 | 备注 |
|---|--------|------|:---:|:---:|------|
| 1 | llc-exists | 文件存在 | ✅ | — | `[ -x ]` 反例：llc 缺失 |
| 2 | llc-version | 版本 | ✅ | — | grep dadao 反例：target 未注册 |
| 3 | mir-ptr-add-o | MIR 结构 | ✅ | ✅ | Python 正则 + 寄存器类校验；inject 后 add_o_bbd=0 |
| 4 | mir-ptrarg | MIR 结构 | ✅ | ✅ | 同上 |
| 5 | mir-chain | MIR 计数+结构 | ✅ | ✅ | n=2 + mir_addo 校验 |
| 6 | no-bank-copy | 汇编 grep | ✅ | — | 3 个 IR 的 post-RA 汇编无 rb2rd/rd2rb |
| 7 | counterexample-base-not-ptr | 反例 | ✅ | ✅ | add_o_bbd=0 + grep ADD_PSEUDO |
| 8 | verify-machineinstrs | verifier | ✅ | — | 4 IR × 3 opt = 12 runs |
| 9 | semantics-full64-add | 语义 | ✅ | — | Python 独立手算 + MIR 含 add_o_bbd |
| 10 | patch-hunks | 文件校验 | ✅ | — | patch 存在 + 含 add_o_bbd + 含 @@ |
| 11 | check-patch-tree | make | ✅ | — | |
| 12 | check-source-state | make | ✅ | — | |
| 13 | check-lit | make | ✅ | — | |

**脚本结构评估**：
- 结尾用 `echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码 ✅
- `--inject` 模式：`sed` 注入 `Base0 != Base1` → `if (false)` → 重建 → 3 条 MIR FAIL → `cp` 备份还原 → sha256 一致 → `git status` 干净 → 重建回绿 ✅
- 所有断言有可达 FAIL 路径 ✅
- 不含恒真断言 ✅
- **判决：脚本合格**

---

##### 二、重跑记录（独立执行）

```
$ bash .work/evidence/LLVM-048t/run.sh > log 2>&1; echo "EXIT=$?"
[PASS] llc-exists | expected: executable ... | actual: exists+exec | rc=0
[PASS] llc-version | expected: rc=0 and 'dadao' registered | actual: rc=0, match=yes | rc=0
[PASS] mir-ptr-add-o | expected: rc=0, add_o_bbd gprb<-gprb+gprd | actual: rc=0, add_o_bbd(gprb,gprb,gprd): [('3', 'gprb', '1', '2')] | rc=0
[PASS] mir-ptrarg | ... | actual: rc=0, add_o_bbd(gprb,gprb,gprd): [('2', 'gprb', '0', '1')] | rc=0
[PASS] mir-chain | ... | actual: rc=0, add_o_bbd=2 | rc=0
[PASS] no-bank-copy | ... | actual: 0 copies | rc=0
[PASS] counterexample-base-not-ptr | ... | actual: rc=0, add_o_bbd=0 | rc=0
[PASS] verify-machineinstrs | ... | actual: all-clean (12 runs) | rc=0
[PASS] semantics-full64-add | ... | actual: ok | rc=0
[PASS] patch-hunks | ... | actual: ok | rc=0
[PASS] check-patch-tree | ... | actual: rc=0 | rc=0
[PASS] check-source-state | ... | actual: rc=0 | rc=0
[PASS] check-lit | ... | actual: rc=0 | rc=0
RESULT: PASS (13 checks, 0 failures)
EXIT=0
```

**真实退出码**：EXIT=0（脚本自身 `exit "$rc"` 捕获，非 `tee` 管道）

---

##### 三、独立注入测试（与 engineer 不同的注入点）

**注入策略**：将 `Base0 != Base1` 改为 `Base0 == Base1`（条件反转）——engineer 用 `if (false)`（禁用条件），reviewer 用 `if (Base0 == Base1)`（反转条件），测试不同的语义失效模式。

**注入前**：
```
sha256: b324dd9334d2b8d76d9e87555abdaab9dbb217a9c5fe22098cbdc19f46d3113b
git diff --name-only: (empty)
```

**注入后**：
```
sha256: 7e3b484b58f0d442462d280df128a94ee21bc93d9101ecfc1e4dd2a976bcc9d2  (changed ✓)
git diff --name-only: llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp  (non-empty ✓)
```

**注入后重建**：ninja EXIT=0

**注入后 MIR 检查（预期 FAIL）**：
- `ptrarg.ll`（指针+偏移）: `add_o_bbd=0`, 有 `ADD_PSEUDO` → **FAIL** ✓（应选 add_o 但未选）
- `ptr_add_offset.ll`（alloca base + 偏移）: `add_o_bbd=0`, 有 `ADD_PSEUDO` → **FAIL** ✓
- `pure_add.ll`（纯数据 i64 add）: `add_o_bbd=1` → **FAIL** ✓（不应选 add_o 但误选了）

三个 MIR 检查全部按预期 FAIL，注入有效。

**还原**：
```
cp -f /tmp/opencode/LLVM-048t-review/DADAOISelDAGToDAG.cpp.orig → source
sha256: b324dd9334d2b8d76d9e87555abdaab9dbb217a9c5fe22098cbdc19f46d3113b  (matches original ✓)
git diff --name-only: (empty, clean ✓)
```

**还原后重建**：ninja EXIT=0

**还原后 MIR 检查（预期 PASS）**：
- `ptrarg.ll`: `add_o_bbd(gprb,gprb,gprd): [('2', 'gprb', '0', '1')]` → **PASS** ✓
- `pure_add.ll`: `add_o_bbd=0`, 有 `ADD_PSEUDO` → **PASS** ✓（数据 add 不选 add_o）

回绿确认。

---

##### 四、Post-RA 汇编独立核验（非 finalize-isel MIR）

| IR 文件 | 汇编关键行 | rb2rd/rd2rb | 判定 |
|---------|-----------|:-----------:|:----:|
| `ptr_add_offset.ll` | `add.o rb8, rb8, rd8` | 0 | ✅ rb dst, rb base, rd offset |
| `pure_add.ll` | `add.uo {rd0, rd31}, rd16, rd17` | 0 | ✅ 纯数据，无 add.o |
| `chain.ll` | `add.o rb8, rb16, rd16` + `add.o rb8, rb8, rd17` | 0 | ✅ 链式两条 add.o |

---

##### 五、合约一致性独立复核

| 来源 | add_o_bbd 定义 | reviewer 核验 |
|------|---------------|:---:|
| `contracts/opcodes.yaml` L2999 | dst=rbhb(rb), src=rbhc(rb), src=rdhd(rd) | ✅ |
| `DADAOInstrInfo.td` L785 | `(outs GPRB:$rb)(ins GPRB:$rc, GPRD:$rd)` | ✅ |
| 实现 `SelectPointerAdd` | `getMachineNode(add_o_bbd, DL, MVT::i64, Base, Offset)` | ✅ base=GPRB, offset=GPRD |
| 实现 `Select` ISD::ADD | `Base0 != Base1` → 恰好一个指针 bank → base=指针, offset=数据 | ✅ |
| MIR 验证 `%3:gprb = add_o_bbd %1(gprb), %2(gprd)` | 寄存器类与合约一致 | ✅ |

---

##### 六、验收标准逐条核验

| # | 验收标准 | reviewer 证据 | 判定 |
|---|---------|:---:|:---:|
| 1 | `ninja llc` EXIT=0 | reviewer 独立重建 EXIT=0 | ✅ |
| 2 | MIR 含 add_o_bbd（rb dst, base rb, offset rd） | `%3:gprb = add_o_bbd %1, %2`；寄存器类 gprb/gprb/gprd | ✅ |
| 2 | 无 rb2rd/rd2rb | post-RA 汇编 grep = 0 | ✅ |
| 2 | 反例：base 非指针 → 不选 add_o | `pure_add.ll`: add_o_bbd=0, ADD_PSEUDO | ✅ |
| 3 | -verify-machineinstrs O0-O2 EXIT=0 | 4 IR × 3 opt = 12 runs all-clean | ✅ |
| 4 | 语义正确（独立手算） | 0x10000+0x1234=0x11234, 0x2000+(-16)=0x1FF0 ✓ | ✅ |
| 5 | 不回归 033t-041t | engineer 逐个重跑全 EXIT=0（reviewer 独立确认 039t 14/14 EXIT=0） | ✅ |
| 5 | make check-patch-tree | 2 component(s), 80 patches OK | ✅ |
| 5 | make check-lit | 33/33 (100.00%) | ✅ |
| 5 | make check | EXIT=0, repository checks: PASS | ✅ |
| 6 | 一键证据脚本 | 13/13 PASS, --inject 自检通过 | ✅ |

补充边界测试（engineer 完成区提及，reviewer 未独立重跑每一条，采信 engineer 完成区 + run.sh 覆盖）：
- 指针形参 base ✅（mir-ptrarg）
- 链式 GEP ✅（mir-chain）
- 大常数偏移 ✅（mir-ptr-add-o 中的 soff 偏移）
- `ptrtoint+add` / 交换序 ✅（engineer 自测 EXIT=0）

---

##### 七、039t 回归/越界判定

**事实**：
- engineer 修改了 `.work/evidence/LLVM-039t/run.sh`（mtime 晚于 039t 完成）
- 改动：`check_csr_rb` 的 `pred_ret_ptr` 中 `$rb31 = COPY` → `$rb31 = (COPY|add_o_bbd)`
- 原因：`rbkeep.ll` 的 GEP `base(rb)+offset(rd)` 现被选为 `add_o_bbd`，结果直接落 `$rb31`（RA 合并 CopyToReg），不再有显式 COPY

**reviewer 独立验证**：
- `rbkeep.mir` 中 `$rb31 = add_o_bbd killed $rb32, killed $rd31`（确认 add_o_bbd 路径）
- `retptr.mir`（纯指针返回）中 `$rb31 = COPY %0`（确认 COPY 路径仍有效）
- 039t 全部 14 个检查 PASS（reviewer 独立重跑 EXIT=0）

**判定**：
1. **是否引入 039t 回归**：❌ **不构成功能回归**。`$rb31` 仍承载指针返回值（属性不变），只是定义方式从 COPY 变为 add_o_bbd（更优：少一条搬运）。语义等价。
2. **改上一任务证据脚本是否可接受**：⚠️ **有条件可接受**。`.work/evidence/` 为 gitignored 临时文件，非仓库交付物；改动保持了断言的**语义意图**（返回值在 rb31）而非硬编码指令形式。但严格来说，039t 的 reviewer 已验收通过的脚本不应被后续任务静默修改——建议：
   - **当前处置可接受**（属性式断言更健壮，不掩盖语义回归）
   - **建议 039t 任务书追加备注**说明该脚本被 048t 的语义改进所更新
3. **是否需要还原**：**不需要还原**。039t 复跑 14/14 PASS，语义正确。

---

##### 八、043t/045t 计数判定

**事实**：
- 043t 失败 2 项：`check-lit-bytes`（期望 114 patterns OK，实际 110）、`lit-mc`（期望 27/27，实际 29/29 PASS）
- 045t 失败 1 项：`lit-mc`（期望 28/28，实际 29/29 PASS）
- 048t 的 git diff 仅改 `DADAOISelDAGToDAG.cpp`（1 文件，76 ins / 8 del），无 MC 测试文件变更

**reviewer 独立验证**：
- `git diff --stat f15f1998b HEAD` = 仅 `DADAOISelDAGToDAG.cpp`（codegen 层）
- MC 测试数量变化（110/29）来自后续任务 044t/046t/047t 等新增 MC 用例，043t/045t 的硬编码计数未同步更新

**判定**：**与 048t 无关，属预存陈旧计数**。建议随文档/计数刷新小任务统一修复。不阻塞本任务验收。

---

##### 九、约束核验

| 约束 | 判定 | 证据 |
|------|:---:|------|
| 临时目录 `/tmp/opencode/LLVM-048t/` | ✅ | run.sh 和 reviewer 均使用该目录 |
| 不提交 git | ✅ | reviewer 全程未执行 `git commit` |
| 不代写/不改证据脚本 | ✅ | reviewer 仅运行 + 审查，未修改 run.sh |
| 注入后还原含重建 | ✅ | cp 备份精确还原 + ninja 重建 + sha256/`git status` 核验 |
| 复杂命令留 `.work/log/` | ✅ | 注入构建日志在 `/tmp/opencode/LLVM-048t-review/` |
| 不 `tee` 吞退出码 | ✅ | 脚本 `echo "EXIT=$rc"; exit "$rc"` |

---

##### 十、判决

**✅ Accepted**

全部 6 条验收标准通过（reviewer 独立重跑验证），合约一致性（opcodes.yaml + TableGen + 实现三者一致），独立注入反例有效且可复原，039t 回归判定为语义改进（非功能回归），043t/045t 计数为预存陈旧问题（与本任务无关），约束全部遵守。
