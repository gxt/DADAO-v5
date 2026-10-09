# M3 CodeGen 取舍点 C1–C16：归属判定 + 逐条分析

> **性质**：**决策支持分析**（非任务、非 ADR、非规范）。供用户对 C1–C16 **逐条判决**使用；架构师**不选边**。
> **来源**：C1–C16 清单初次出现在 `.tao/tasks/spec/SPEC-096k-M3启动与分解.md §M68k↔0628 冲突清单`（只含 M68k/0628 两参考）；本文档**补充第三参考 TCH-llvm**、并按用户 2026-10-04 指示纳入「**rb = 基址**」重估。
> **落点说明**：本文件放 `.tao/knowledge/`（命名 `project_*.md`，见 `.tao/README.md`）。理由：① 它是**决策支持材料**，不是可执行交付物——放 `tasks/` 会引入状态机（`k`/`t`/`m`）语义，而本分析不产生实现、也不单独验收；② 它尚未构成 ADR（C1–C16 的取舍**未经用户逐条确认**，不得写为 `Accepted`）；③ `knowledge/` 已承载 `project_*.md` 类决策/背景材料，且被 `SPEC-096k` 与待立的 ADR 引用最方便。**不修改** `spec/`、`contracts/`、任何任务书；**不提交 git**。临时目录 `/tmp/opencode/M3-choices/`（本次分析未产生临时文件）。
> **日期**：2026-10-04　**执行**：architect

---

## 0. 背景与证据基线

### 0.1 三点背景（用户 2026-10-04 指示）

1. **第三参考 TCH-llvm**：`.cache/refs/DADAO/TCH-llvm/llvm-1600-newfiles/llvm/lib/Target/Dadao/`（完整 DADAO LLVM 16 目标，**含 CodeGen**）+ `llvm-1600-patches/`。**只读、不复制**。经核实其事实见 §0.3。
2. **`rb` = 基址寄存器（base register），不是一般地址寄存器**：`spec/SimRISC-00`「基址寄存器又可称为地址寄存器，但**在 SimRISC 中只能用于基址，即绝对地址**」（`spec/SimRISC-00-指令系统设计.md:59`）；RB 64 位、低 48 位有效地址（`:64`、`:80`）。**所有取舍据此重估**——rb 承载「基址/绝对地址」，非一般地址算术/偏移。
3. **三参考**：M68k（`.work/source/llvm-project/llvm/lib/Target/M68k/`）、DADAO-0628（`.cache/refs/DADAO-0628/`）、TCH-llvm（上述）。

### 0.2 归属判定的四条判据（本文使用）

| 归属 | 含义 | 判据 |
| --- | --- | --- |
| **ABI** | 由 `contract-abi.md` / `contracts/abi.yaml` 规定 | 跨组件**可观察**的接口事实（caller/callee 契约、寄存器角色、参数/返回、帧布局、对齐）——不受实现选择影响，按 spec 投影为合约内容 |
| **ADR** | 由 `.tao/adr/` 记录 | 命中 `spec/Process-03-ADR编写规范.md:5-16`：高代价 / 跨模块 / 多方案需记取舍 / 结论固化 / 方向定位；**不承载规范正文** |
| **两者** | ABI 定**内容**、ADR 记**取舍/理由** | 事实是 ABI，但"为什么这样选、否决了什么"是 ADR |
| **随 spec** | spec 已明确，无需新规 | spec 直接可投影/实现，无多方案取舍空间 |

### 0.3 TCH-llvm 关键事实（本文实测，`file:line`）

| 项 | 事实 | 证据 |
| --- | --- | --- |
| 寄存器类 | `GPRD=[i64]`；`GPRB=[i64, bp64]`；`GPRA=[i64]`（`isAllocatable=false`）；**无 RF 类** | `DadaoRegisterInfo.td:56-65`、`:67-79`、`:81-86` |
| 指针 value type | **自定义 MVT `bp64`**：`addRegisterClass(bp64, GPRB)` + `getPointerTy()→bp64` | `DadaoISelLowering.cpp:82-83`、`DadaoISelLowering.h:103-108` |
| 参数（C CC） | `CC_Dadao32`：`[i64,bp64] → CCAssignToReg<[RD16..RD31]>`（**指针也进 RD**） | `DadaoCallingConv.td:28-35` |
| 指针参数 assigner | `CC_Dadao_AssignToReg` 按 `isPointerTy()` 选 RB16-31（**仅 `CC_Dadao32_Fast` 使用**；C CC 未接）+ `FIXME: Handling on pointer arguments is not complete` | `DadaoCallingConv.h:37-71`、`:36`；`.td:18-25` |
| 返回 | `RetCC_Dadao32`：`[i64,bp64]→RDRV(RD31)`；指针返回物理落 RD31，`LowerCallResult` 再用 `RD2RB_ORRI` 转 GPRB | `DadaoCallingConv.td:38-40`、`DadaoISelLowering.cpp:863-867` |
| callee-saved | `CSR = CalleeSavedRegs<(add (sequence "RD%u",32,63))>`（**只 RD32-63，漏 RB32-63**） | `DadaoCallingConv.td:42`、`DadaoRegisterInfo.cpp:36-39` |
| reserved | `getReservedRegs` 只保留 `RD0/RD8/RB0/RB8/RBSP/RBFP/RAVV/RASP`（**未全部 reserve RA/RF**，靠 `GPRA.isAllocatable=0`） | `DadaoRegisterInfo.cpp:41-52` |
| SP/FP | `RBSP=rb1`、`RBFP=rb2`；`setStackPointerRegisterToSaveRestore(RBSP)` | `DadaoRegisterInfo.td:46-47`、`DadaoISelLowering.cpp:89` |
| hasFP | **恒 true**；prologue 存 FP + 建 FP + 调 SP；epilogue `SP=FP` 后恢复 FP | `DadaoFrameLowering.h:47`、`DadaoFrameLowering.cpp:89-137`、`:176-193` |
| getFrameRegister | `RBFP` | `DadaoRegisterInfo.cpp:181-184` |
| DataLayout | `"e-m:e-p:64:64-i64:64-a:0:64-n64-S128"`（**小端 `e`**、S128、无 i128） | `DadaoTargetMachine.cpp:39-48` |
| 跨 bank 搬运 | 同类 `RD2RD_ORRI`/`RB2RB_ORRI`；跨类 `RB2RD_ORRI`/`RD2RB_ORRI` | `DadaoInstrInfo.cpp:40-63` |
| call/ret | `CALL_IIII`/`CALL_RRII` `isCall=1, Uses=[RASP]`（**无显式 Defs**）；`_RET_FIXME` `isReturn=1, Uses=[RASP]` | `DadaoInstrInfo.td:638-642`、`:646-652`、`:665-675` |
| call RegMask | `LowerCCCCallTo` 附 `getRegisterMask(getCallPreservedMask)`；`getCallPreservedMask→CSR_RegMask`（RD32-63） | `DadaoISelLowering.cpp:817-820`、`DadaoRegisterInfo.cpp:189-192` |
| ISel 框架 | **仅 SelectionDAG**（无 GISel 目录）：`addInstSelector→createDadaoISelDag` | `DadaoTargetMachine.cpp:107-111` |
| 常数材料化 | `DadaoWydePosition.h`（wyde 位置） | 文件名 |

> **TCH-llvm 的两个须核实冲突**：① DataLayout 为**小端 `e`**，与 v5 spec 大端（`spec/DADAO-21 §数据表示`、v5 `TargetDataLayout.cpp:648`）**直接冲突**——TCH 可能是另一变体/早期版本，v5 以 spec 大端为准；② C CC 指针参数落 RD（`DadaoCallingConv.td:32`）是**已知未完成项**（`:36` FIXME），**不可作为 v5 范式**。

### 0.4 v5 现状基线（实测，`file:line`）

| 项 | v5 现状 | 证据 |
| --- | --- | --- |
| 寄存器类 | `GPRD/GPRD_Allocatable/GPRB/GPRB_Allocatable/GPRF/GPRA`，**全部 `[i64]`**；GPRF/GPRA `isAllocatable=0` | `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAORegisterInfo.td:107,120,130,143,155,170` |
| 指针 value type | **无独立指针 MVT**（GPRB 也是 `[i64]`）；`DADAO.td` 有 `RemapAllTargetPseudoPointerOperands<GPRB>` | `DADAORegisterInfo.td:130`、`DADAO.td:28` |
| DataLayout | `"E-m:e-p:64:64-i64:64-i128:128-n32:64-S128"` | `.work/source/llvm-project/llvm/lib/TargetParser/TargetDataLayout.cpp:648` |
| 指令 | `rd2rd/rb2rb/rd2rb/rb2rd`（orri，`:1160/1184/1192/1200`）；`add.so-rb`=`rb=rb+rd`（`:686`）、`sub.so-rb`（`:694`）、`add.si-rb`（`:475`）、`cmp.uo-rb`（`:702`）；`set.zw/or.w/andn.w`（rd+rb，`:563-610`） | `DADAOInstrInfo.td` |
| call/ret/jump | `call_iiii/call_rrii/ret_riii/jump_iiii/jump_rrii` **全部 `Pattern=[]`、无 `isCall`/`isReturn`/`Defs`/`Uses`** | `DADAOInstrInfo.td:264,271,538,547,554` |
| mayLoad/mayStore | **0 处**（grep 实测） | `DADAOInstrInfo.td`、`DADAOInstrFormats.td` |
| copyPhysReg | **未实现**（无该函数） | `DADAOInstrInfo.cpp`（grep） |
| FrameLowering | 空存根（只 `TargetFrameLowering(StackGrowsDown, Align(8), 0)`，**无 hasFPImpl/emitPrologue/emitEpilogue**） | `DADAOFrameLowering.h:30-34` |
| eliminateFrameIndex | `llvm_unreachable` | `DADAORegisterInfo.cpp:62-66` |
| getCalleeSavedRegs | 返回空 `{0}`（占位） | `DADAORegisterInfo.cpp:35-40` |
| getReservedRegs | 保留 `rd0/rb0/rb1/rb2` + **全部 rf0-63 + 全部 ra0-63** | `DADAORegisterInfo.cpp:41-54` |
| getFrameRegister | `rb2`（FP） | `DADAORegisterInfo.cpp:56-58` |
| getCallPreservedMask | **未实现** | `DADAORegisterInfo.{h,cpp}`（grep） |
| TargetMachine | 仅 `initAsmInfo()`，**无 PassConfig/Subtarget**；用 `TT.computeDataLayout()` | `DADAOTargetMachine.cpp:26-32` |
| 合约 | `contract-abi.md §4` 完整 CC 仍 `Deferred to M2`（`:9,155-169`）；`contracts/abi.yaml deferred_to_m2`（`:115-130`）；`contract-abi §6 [OPEN]` 5 项（含窄返回扩展 `#2:192`、帧指针省略 `#5:195`、red zone `#4:194`） | `.tao/knowledge/contract-abi.md`、`contracts/abi.yaml` |
| spec | `DADAO-21 §参数寄存器`（`spec/DADAO-21-...md:145-160`）、`§返回值`（`:330-340`）、`§The Stack Frame`（`:121-137`）；`SimRISC-00 §基址寄存器`（`spec/SimRISC-00-...md:57-80`）；`contract-isa §7`（`.tao/knowledge/contract-isa.md:671-705`） | — |

---

## 1. 归属总表（C1–C16）

| # | 主题 | **归属** | 建议立 ADR？（判据） |
| --- | --- | --- | --- |
| C1 | ISel 寄存器模型（硬双类 vs 联合类） | **两者**（ABI 定 bank 归属；ADR 记硬/联合取舍） | **建议 ADR**（多方案+高代价+跨任务；Process-03 §1/§3/§5） |
| C2 | 指针 value type（`bp64`/`iPTR`/i64） | **两者**（ABI 定"指针走 RB"；ADR 记独立类型 vs 通吃） | **建议 ADR**（多方案+高代价+跨任务） |
| C3 | 跨 bank 搬运指令（同/跨 bank 映射） | **随 spec**（指令语义=spec）；映射取舍可 ADR（可选） | 否（可选） |
| C4 | 参数寄存器/计数/栈溢出区 | **ABI**（`SPEC-097t` 投影）；溢出区口径若成取舍另需裁决 | 溢出区口径若需取舍→ADR（可选） |
| C5 | 返回值 + 窄返回扩展 | **两者**（返回寄存器 ABI；窄扩展为 spec 空白→ADR+ABI） | **建议 ADR**（spec 缺、需固化决策） |
| C6 | callee-saved 集合 | **ABI**（spec 已定） | 否 |
| C7 | 帧布局 / `hasFP`（SP-only vs FP） | **两者**（布局内容 ABI；SP-only/FP 取舍 ADR） | **建议 ADR**（多方案+高代价+跨任务） |
| C8 | SP/FP 寄存器 | **随 spec**（已定，投影 ABI 即可） | 否 |
| C9 | DataLayout / 栈对齐（S128/S64、n 规则） | **两者**（串归 ABI；`S128/n32:64/i128` 取舍 ADR） | **建议 ADR**（外部契约+多方案+高代价） |
| C10 | 调用/返回机制（RegRAS） | **随 spec**（已定，投影 ABI 即可） | 否 |
| C11 | 指令选择框架（SelectionDAG vs GlobalISel） | **ADR**（纯机制取舍） | **建议 ADR**（用户已点名；Process-03 §1/§3/§5） |
| C12 | 常数材料化 | **随 spec**（指令语义）＋实现策略（可 ADR 可选） | 否（可选） |
| C13 | 窄类型/子寄存器（无 subreg + 提升/扩展） | **随 spec + 实现**（大端窄访存策略建议 ADR） | 大端窄访存→建议 ADR（可选） |
| C14 | RB 算术语义（结合「rb=基址」） | **随 spec**（`contract-isa §7` 已定）；指针算术落 RB vs 转 RD 取舍可 ADR | 否（可选） |
| C15 | RA/RF bank + `rb2` 分配 | **两者**（保留策略 ABI/范围；`rb2` 取舍随 C7 ADR） | 随 C7（`rb2`） |
| C16 | `call` 的 `Defs`/`RegMask` | **两者**（caller-saved 集合 ABI；`Defs`/RegMask 约束 ADR） | **建议 ADR**（结论固化；0628 两次事故） |

> **建议 ADR 集合（供用户裁定，架构师不擅自决定）**：C1、C2、C5、C7、C9、C11、C16。其中 `SPEC-096k` 已点名 C1/C7/C11。是否立、立几条、如何合并（如 C1+C2 可合一、C7+C15 的 `rb2` 可合一、C6+C16 的 caller/callee-saved 可合一），**由用户裁定**。

---

## 2. 逐条分析

> 约定：`rb=基址影响` = 结合「RB 只能作基址/绝对地址、低 48 位有效地址」重估。

### C1 ISel 寄存器模型（硬双类 vs 联合类）

**(a) 归属**：**两者**。ABI 定「数据→RD、指针/地址→RB」这一**可观察**的 bank 归属（`spec/DADAO-21 §传参 §参数寄存器:145-160`；`SimRISC-00 §基址寄存器:59`）；「ISel 用硬双类还是联合类+软偏好」是**纯实现取舍**（跨全部 ISel 任务、高代价）→ ADR 记录。**建议立 ADR**。

**(b) 分析**

- **M68k**：联合类 + 软偏好。`XR32 = add DR32, AR32`（`M68kRegisterInfo.td:123`）；`addRegisterClass(MVT::i32, XR32)`（`M68kISelLowering.cpp:64`）——int/ptr 共用类，寄存器分配器任选 bank；指针优先走 A 靠 CC 自定义软偏好 `CC_M68k_Any_AssignToReg`（`M68kCallingConv.h:52-63`，`AddrRegList={A0,A1,D0,D1}`）。
- **DADAO-0628**：硬双类。`addRegisterClass(MVT::i64, GPRD)`（patch `0061`:49 / `0007`:150），GPRB 通过 `LowerFormalArguments` 检测指针类型显式建 GPRB vreg（`DL-050a:26-28,77`）+ CC `CCIfPtr`（`DL-069a` 完成区）+ `copyPhysReg` 跨 bank 桥（`DL-051a:89`）。指针 bank 由 CC/ISel 强制，**不是**联合类软偏好。
- **TCH-llvm**：硬双类 + 独立 MVT。`addRegisterClass(i64, GPRD)` + `addRegisterClass(bp64, GPRB)`（`DadaoISelLowering.cpp:82-83`）。
- **v5 现状**：`GPRD`/`GPRB` 均 `[i64]`（`DADAORegisterInfo.td:107,130`），**无 ISel**（CodeGen 骨架待建，`DADAOTargetMachine.cpp` 无 PassConfig）。GPRB 与 0628 一样是 `[i64]`（不是 TCH 的 `[i64,bp64]`）。
- **差异/冲突**：三参考实质都是「bank 硬绑定」（M68k 的联合类也靠 CC 软偏好把指针推 A）；v5 已备 `GPRD_Allocatable`/`GPRB_Allocatable`（rd8-63/rb8-63），**天然支持硬双类**。TCH 的 C CC 未落实「指针进 RB」（§0.3），**不可照抄**。
- **「rb=基址」影响**：RB 只能作基址/绝对地址 → 指针**必须**落 GPRB（硬双类）才与 ISA 语义自洽；联合类软偏好允许指针临时落 RD，会与「地址只在 RB」相悖（M68k 的 AR 可作一般运算，v5 的 RB 不行——见 C14）。

**(c) 待判选项**

1. **硬双类**：`GPRD=i64`、`GPRB=指针/地址`，指针经 CC/ISel 强制 GPRB（0628/TCH 路线）。
2. **联合类 + 软偏好**：`XR = GPRD ∪ GPRB`，CC 软偏好指针走 RB（M68k 路线）。
3. **其他**（如硬双类 + 独立指针 MVT，见 C2）。
> 连带：若选 3，C2 一并定；若选 1/2，需定「指针 value type」（C2）。

---

### C2 指针 value type（`bp64` / `iPTR` / i64 通吃）

**(a) 归属**：**两者**。ABI 定「指针是 8 字节、走 RB bank」（`spec/DADAO-21 §数据表示`、`§标量参数:161-167`「指针类参数传递时使用基址寄存器」）；「是否引入独立 value type」是**实现机制**（高代价、影响全部 ISel/CC）→ ADR。**建议立 ADR**。

**(b) 分析**

- **M68k**：无独立指针类型。`MVT PtrVT = MVT::i32`（`M68kISelLowering.cpp:52`），指针=int 同 MVT；靠 CC 软偏好区分。
- **DADAO-0628**：**未真正引入独立 MVT**。实测仅 `addRegisterClass(MVT::i64, GPRD)`（patch `0061`:49、`0007`:150）；指针在 SelectionDAG 里是 i64/iPTR，**靠 bank 感知的 Lowering/CC**把指针参数与返回值建为 GPRB vreg（`DL-069a` 完成区：`GPRBRegClass.contains(VA.getLocReg())`、`CCIfPtr`），再用 `copyPhysReg` 桥。`DL-050a:26-27` 文字称「注册 GPRB 承载 iPTR/p0」，但**实际代码路径**是显式 vreg + CC（弱约束）。
- **TCH-llvm**：**引入独立自定义 MVT `bp64`**：`addRegisterClass(bp64, GPRB)` + `getPointerTy()→MVT::bp64`（`DadaoISelLowering.cpp:82-83`、`DadaoISelLowering.h:103-108`），GPRB = `[i64, bp64]`（`DadaoRegisterInfo.td:67`）。强约束：指针类型直接决定 register class。
- **v5 现状**：**无独立指针 MVT**（GPRB 也是 `[i64]`）；`DADAO.td:28` 有 `RemapAllTargetPseudoPointerOperands<GPRB>`。DataLayout `p:64:64`。
- **差异/冲突**：TCH 的 `bp64` 是**最强**的「指针→GPRB」约束（LLVM 16 可用自定义 value type）；0628 是**最弱**（i64 通吃 + CC/ISel 强制）；M68k 干脆不分。v5 若走 0628 路线（i64 通吃 + bank 感知 CC/ISel），需依赖 `ArgFlags.isPointer()` 等从 IR 类型判定（0628 已证可行）；若走 TCH 路线（独立 MVT），约束更强但需核实 **LLVM 23.1.1 是否支持**自定义/别名 MVT（TCH 是 LLVM 16；v5 基线 LLVM 23.1.1，见 ADR-0006）。
- **「rb=基址」影响**：独立指针类型能把「地址值」与「数据值」在类型层分开，天然防止指针落 RD（更贴合「rb 只能基址」）；i64 通吃则完全依赖 CC/ISel 的人为约束，出错风险高（0628 靠大量踩坑修补）。

**(c) 待判选项**

1. **独立指针 MVT**（TCH 式，如自定义 `bp64` 或复用 `iPTR`）→ 强制指针落 GPRB。**须先核实 LLVM 23 可行性**。
2. **iPTR/i64 通吃 + bank 感知 CC/ISel**（0628 式，弱约束）。
3. **纯 i64 硬双类**（v5 现有 `[i64]` 不变，靠 Lowering 显式建 GPRB vreg）。
> 与 C1 强耦合：选 C1-1 + C2-1 是 TCH 风格；C1-1 + C2-2/3 是 0628 风格。

---

### C3 跨 bank 搬运指令

**(a) 归属**：**随 spec**。指令的**编码/语义**由 `contract-isa`（`.tao/knowledge/contract-isa.md`）与 `contracts/opcodes.yaml` 定，v5 指令（`rd2rd/rb2rb/rd2rb/rb2rd`）已存在。「同类用专用移动还是 `addi+0`」是纯实现映射，**不必 ADR**（如需固化可 ADR 可选）。

**(b) 分析**

- **M68k**：`copyPhysReg` 用 `MOV32rr`/`MOV16rr`/`MOV8dd`（`M68kInstrInfo.cpp:686-702`）——因 `XR32` 联合类，同类与跨类**同为 MOV**。
- **DADAO-0628**：同类 `addi r, r, 0`（`ADDI_RRII`/`ADDI_RBRRII` imm0）；跨类 `RD2RB_ORRI`/`RB2RD_ORRI`（`DL-051a:89`；完成区表 `:290-293` 列 `DADAOInstrInfo.cpp:23-50`）。
- **TCH-llvm**：同类 `RD2RD_ORRI`/`RB2RB_ORRI`；跨类 `RB2RD_ORRI`/`RD2RB_ORRI`（`DadaoInstrInfo.cpp:40-63`）。且 `LowerCallResult` 指针返回用 `RD2RB_ORRI`（`DadaoISelLowering.cpp:865`）。
- **v5 现状**：已有专用指令 `rd2rd`/`rb2rb`/`rd2rb`/`rb2rd`（`DADAOInstrInfo.td:1160/1184/1192/1200`，均 `orri`，`Pattern=[]`）；**`copyPhysReg` 未实现**。
- **差异**：0628 同类用 `addi+0`，TCH 与 v5 有专用 `rd2rd`/`rb2rb`。跨类三参考一致用专用 `rd2rd/rb2rb` 的跨 bank 变体。
- **「rb=基址」影响**：`rd2rb`/`rb2rd` 承载「数据↔地址」转换（如把常量地址装入 RB、把 RB 地址值取出算），是 bank 语义的关键通道；同类 `rd2rd`/`rb2rb` 用于分配器插入的 COPY。

**(c) 待判选项**

1. 同类用**专用** `rd2rd`/`rb2rb`（TCH 式，v5 已有指令）。
2. 同类用 `add.si +0`（0628 式）。
3. 跨类固定用 `rd2rb`/`rb2rd`（三参考一致，无异议）。
> 另需定：`copyPhysReg` 必须 `using TargetInstrInfo::copyPhysReg;` 防重载隐藏（0628 `DL-051a:88` 已提，v5 `LLVM-034t` 任务书已含）。

---

### C4 参数寄存器/计数/栈溢出区

**(a) 归属**：**ABI**（`SPEC-097t` 投影到 `contract-abi.md §4` + `contracts/abi.yaml`）。这是跨组件可观察的 caller/callee 契约（哪条指令用什么寄存器传什么参数），必须由合约规定，不能由实现决定。**栈溢出区的组织口径**（统一区 vs per-bank）若 spec 文字有歧义，则是「补契约内容」的取舍，需用户裁定（可并入 ADR）。

**(b) 分析**

- **M68k**：`D0/D1` int、`A0/A1` ptr（软偏好 A，`M68kCallingConv.h:52-63`），最多 4 寄存器，其余 caller-pop 栈（`M68kCallingConv.td:60-100`；`OkToPassInRegs` 逻辑）。
- **DADAO-0628**：`rd16-31` int、`rb16-31` ptr，**各 bank 独立计数从 16**，**统一溢出区按全局声明序**，每槽 8B（`contracts/abi/spec.md §2.1:77-88`、`§2.3:107-132`，含 cross-bank 例子）。
- **TCH-llvm**：`CC_Dadao32` 把 `[i64,bp64]` **全** 塞 `RD16-31`（`DadaoCallingConv.td:28-35`），其余 `CCAssignToStack<8,8>`；指针走 RD 是**已知未完成**（`DadaoCallingConv.h:36` FIXME；`AddrRegList` 定义了但 C CC 未接）。**不可作 v5 范式**。
- **v5 现状**：spec `DADAO-21 §参数寄存器`（`spec/...:145-160`）明确 rd16-31/rb16-31/rf16-31 **独立计数从 16**，含 `read(fd,buf,count)` 例子；`§栈溢出规则`（`:221-236`）「该 bank 的后续参数使用栈传递…按声明顺序从左到右…三 bank 共享同一栈增长方向」。`contract-abi.md §4` 仍 `Deferred to M2`（`:161`）；`contracts/abi.yaml deferred_to_m2.parameter_registers`（`:116-120`）。
- **差异/冲突**：0628 把 spec「声明顺序」实现为**全局统一区**（跨 bank 按全局声明序，`§2.3` 例子 `r→sp+0, s→sp+8, t→sp+16`）；v5 spec 字面是「该 bank 的后续参数…按声明顺序」（可解读为 per-bank 各自连续）。**这是 C4 唯一的实质歧义**，须裁定。
- **「rb=基址」影响**：指针参数必落 `rb16-31`；`rb` 溢出槽同样按序。

**(c) 待判选项**

1. 溢出区口径：**统一区/全局声明序**（0628）vs **per-bank 各自连续**（spec 字面）。
2. 参数提升：`<8B` 按符号性提升到 8B（spec `§标量参数:163-167`）；由 **caller** 负责扩展（0628 `§2.2:103-104`）。
3. 计数细节：三 bank 独立计数从 16（已定）。
4. 窄参数是否 caller 扩展、callee 免扩展（0628 决策，与 C5 窄返回呼应）。

---

### C5 返回值 + 窄返回扩展

**(a) 归属**：**两者**。返回**寄存器**（rd31/rb31/rf31）由 ABI 定（`spec/DADAO-21 §返回值 §标量类型返回值:335-340`）；**窄返回扩展规则在 spec 中缺失**（v5 `contract-abi.md §6 [OPEN] #2:192`「spec §返回值 未规定 callee 扩展 / caller 不截断」）——这是**补契约内容 + 固化决策**，需 ADR + ABI。**建议立 ADR**。

**(b) 分析**

- **M68k**：`RetCC_M68k_C` —— ptr→`A0`；i8→`BD0/BD1`（**子寄存器**）、i16→`WD0/WD1`、i32→`D0/D1`（`M68kCallingConv.td:26-32`）。窄返回落子寄存器（M68k 有 subreg）。
- **DADAO-0628**：int→`rd31`、ptr→`rb31`；**callee 扩展窄值、caller 不截断**（`contracts/abi/spec.md §3.1:195-201`，明标「M1 architecture decision: callee extends; caller does not truncate」，wiki 缺）。
- **TCH-llvm**：`RetCC_Dadao32` 把 `[i64,bp64]` **都** 归 `RDRV(RD31)`（`DadaoCallingConv.td:38-40`）；**指针返回物理落 RD31**，`LowerCallResult` 再用 `RD2RB_ORRI` 转 GPRB（`DadaoISelLowering.cpp:863-867`）。无显式窄返回扩展（窄值已被 `CCIfType<[i8,i16,i32],CCPromoteToType<i64>>` 提升）。
- **v5 现状**：spec `§返回值:330-340`「绝对地址→rb31、浮点→rf31、其它→rd31」；**未提窄返回扩展**；`contract-abi §6 #2` 标 `[OPEN]`；`contracts/abi.yaml return_registers`（`:121-124`）。M3 的 `LLVM-039t` 明确依赖 `SPEC-097t` 给窄返回口径。
- **差异/冲突**：**0728/TCH 的指针返回口径不同**——v5 spec/0628 = `rb31` 直接；TCH = `rd31` 再 `RD2RB` 转。TCH 是反例（其 C CC 未落实 RB，只在 `RetCC` 写 RDRV，且靠转换补），**v5 应采用 spec 的 rb31**。
- **「rb=基址」影响**：指针返回是绝对地址 → 必须 `rb31`（spec）；TCH 的 RD31+转换在语义上等价但多一条指令且与 spec 字面不符。

**(c) 待判选项**

1. 指针返回：**`rb31` 直接**（v5 spec/0628）vs TCH 的 `rd31`+`rd2rb`。
2. 窄返回扩展：**callee 扩展**（0628 决策，v5 spec 空白）vs caller 截断。
3. i8/i16 返回是否落子寄存器（仅 M68k；v5 **无 subreg → 不适用**，统一 64 位寄存器）。
4. `i128` 返回（`rd31:rd30`，0628 `ML-038a`）是否纳入 M3（v5 M3 边界：**不做 i128**，归 M4）。

---

### C6 callee-saved 集合

**(a) 归属**：**ABI**。spec `DADAO-21 §寄存器规范` 明确 RD/RB/RF `32-63` callee-saved，无需新规，投影到 `contract-abi §1` + `abi.yaml`。

**(b) 分析**

- **M68k**：`CSR_STD = D2-D7, A2-A6`（`M68kCallingConv.td:112`；A5=BP、A6=FP）。
- **DADAO-0628**：`rd32-63` + `rb32-63`（`contracts/abi/spec.md §1.1:27`、`§1.2:46`、`§4.4:314`）；`getCalleeSavedRegs` 早期只 `RD8-15`（`DL-055a:100`），后修正。
- **TCH-llvm**：`CSR = CalleeSavedRegs<(add (sequence "RD%u",32,63))>`——**只 RD32-63，漏 RB32-63**（`DadaoCallingConv.td:42`）；`getCalleeSavedRegs→CSR_SaveList`（`DadaoRegisterInfo.cpp:36-39`）。**这是 TCH 缺陷**，与 v5 spec（rb32-63 也 callee-saved）冲突。
- **v5 现状**：spec RB 表 `rb32-63` callee-saved（`spec/...:25-40`）；`contract-abi §1.3:59`；`abi.yaml registers.rb:68` / `callee_saved.rb=[32,63]:108`。**`getCalleeSavedRegs` 实测返回空 `{0}`**（`DADAORegisterInfo.cpp:35-40`，待 `LLVM-039t`）。
- **差异**：TCH 漏 RB——**不可照抄**；0628 与 v5 spec 一致。
- **「rb=基址」影响**：RB32-63 是**地址类 callee-saved**，函数用它作基址时必须存/取（`ld.o/st.o`）。

**(c) 待判选项**

1. CSR = `rd32-63 ∪ rb32-63`（v5 spec/0628，基本已定）。
2. SP/FP（rb1/rb2）是否入 CSR_SaveList：v5 `abi.yaml` 逐寄存器标 rb1/rb2 `callee_saved:true`，但「派生块」`callee_saved.rb=[32,63]` 不含它们（`abi.yaml:99-108` 注释说明）。**须澄清** CSR_SaveList 是否含 rb1/rb2（0628/TCH 均靠 prologue 显式管理 SP/FP，不入通用 CSR）。
3. `rd1/rb3/rb4`（spec 栏 `-`，`[OPEN]`，`contract-abi §6 #1:191`）：v5 现 M1 保守不分配；M3 是否冻结其 caller/callee 语义。

---

### C7 帧布局 / `hasFP`

**(a) 归属**：**两者**。帧布局**内容**（FP 相对偏移、SP 指向、参数溢出区）归 ABI（`contract-abi §4` / `spec/DADAO-21 §The Stack Frame:121-137`）；「SP-only vs 建 FP」是 spec 明确允许二选一的**实现取舍 + 高代价 + 跨全部帧任务** → ADR。**建议立 ADR**（用户 `SPEC-096k` 已点名；v5 `contract-abi §6 #5:195` 也标 `[OPEN]`）。

**(b) 分析**

- **M68k**：`hasFPImpl = DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment`（`M68kFrameLowering.cpp:45-54`）；FP=`A6`、SP=`A7`；`getFrameRegister = hasFP ? A6 : SP`（`M68kRegisterInfo.cpp:49-50,259-261`）。
- **DADAO-0628**：ABI **允许**可选 FP（rb2），但**实现走 SP-only**：`hasFPImpl=false`、`getFrameRegister=RB1/SP`（`DL-053a` 完成区 L227「hasFPImpl 返回 false」/ L453；`DL-054a:84-85,266-267`「getFrameRegister→RB1」）。
- **TCH-llvm**：`hasFP` **恒 true**（`DadaoFrameLowering.h:47`）；prologue `st RBFP,[RBSP+spOffset]` → `RBFP=RBSP+0` → `RBSP-=StackSize`（`DadaoFrameLowering.cpp:110-132`）；epilogue `RBSP=RBFP+0` → `RBFP=[RBFP+spOffset]`（`:184-192`）。
- **v5 现状**：`DADAOFrameLowering` **空存根**（无 `hasFPImpl`/`emitPrologue`/`emitEpilogue`，`DADAOFrameLowering.h:30-34`）；`getFrameRegister`=rb2（`DADAORegisterInfo.cpp:56-58`）；`eliminateFrameIndex` unreachable。`LLVM-038t` 任务书默认 **SP-only** 但标注 C7 待判。
- **差异**：**0628=SP-only vs M68k/TCH=FP**；v5 任务书暂按 SP-only。
- **「rb=基址」影响**：SP(rb1)、FP(rb2) 都是**基址寄存器**；SP-only 省掉一个 RB（rb2 可保留不用）；建 FP 则 `rb2` 专用于帧基址。因「rb 只能基址」，FP 作为帧基址正是 RB 的本职用途。

**(c) 待判选项**

1. **SP-only**（0628 实测路线）vs **建 FP**（M68k/TCH 路线）vs `hasFPImpl` 条件式（仅按需）。
2. 若建 FP：prologue/epilogue 序列（0628 `§5.2-5.3` 给了两套可汇编序列，`contracts/abi/spec.md:338-390`）。
3. 大帧偏移：是否实现 `RegScavenger` + `add.so-rb`/大立即数材料化（0628 `DL-053a`/patch `0051`；TCH `DadaoRegisterInfo.cpp:113-160`）——M3 是否有 >2047 帧用例。
4. `getFrameRegister` 返回 rb1（SP-only）还是 rb2。

---

### C8 SP/FP 寄存器

**(a) 归属**：**随 spec**（已定）。`spec/DADAO-21 §寄存器规范 §RB寄存器:25-40` 定 `rb1=rbsp(SP)`、`rb2=rbfp(FP)`；投影到 `contract-abi §2.1` + `abi.yaml stack` 即可，无取舍。

**(b) 分析**

- **M68k**：`SP=A7`、`FP=A6`（`M68kRegisterInfo.cpp:49-50`）。
- **DADAO-0628**：`SP=rb1`、`FP=rb2`（`contracts/abi/spec.md §4.1:277-281`）。
- **TCH-llvm**：`RBSP=RB1`、`RBFP=RB2`（`DadaoRegisterInfo.td:46-47`）。
- **v5 现状**：spec `rb1/rb2`（`spec/...:25-40`）；`contract-abi §2.1:130-133`；`abi.yaml stack:28-36`；实测 `DADAORegisterInfo.cpp:50` `DADAOGenRegisterInfo(DADAO::RBSP)`、`:56-58` `getFrameRegister→rb2`。
- **差异**：仅范式差异（M68k 是 A6/A7），**v5 已定 rb1/rb2**。
- **「rb=基址」影响**：SP/FP 是基址寄存器的**帧管理专用**成员（非通用可分配）。

**(c) 待判选项**：无（已由 spec 定）。

---

### C9 DataLayout / 栈对齐（`S128` vs `S64`、`n` 规则）

**(a) 归属**：**两者**。DataLayout 串是跨组件（clang/llvm 后端/MC）**可观察**的一致契约 → ABI 记录；`S128 vs S64`、`n32:64 vs n64`、是否 `i128:128` 是**外部契约 + 多方案 + 高代价** → ADR。**建议立 ADR**（`SPEC-096k` 已点名）。

**(b) 分析**

- **M68k**：`E-m:e-p:32:16:32-i8:8:8-i16:16:16-i32:16:32-n8:16:32-a:0:16-S16`（32 位指针、ABI 16 位对齐、S16）（`TargetDataLayout.cpp:129-148`，`case m68k:586`）。
- **DADAO-0628**：初始 `E-m:e-i64:64-n64-S128`（`DL-036a:64`）→ 因 ABI §4.2「8 字节」改 **`S128→S64`**（`DL-041a:16,33-46`；契约串 `E-m:e-i64:64-n64-S64`）→ 再加 **`i128:128`**（`DL-064a:214`，clang `__int128` 对齐崩溃，对标 RISCV64）。终值 `E-m:e-i64:64-i128:128-n64-S64`。
- **TCH-llvm**：`"e-m:e-p:64:64-i64:64-a:0:64-n64-S128"`（`DadaoTargetMachine.cpp:39-48`）——**小端 `e`**（与 v5 大端冲突）、S128、**无 i128**、无 n32:64。
- **v5 现状**：`"E-m:e-p:64:64-i64:64-i128:128-n32:64-S128"`（`TargetDataLayout.cpp:648`）——大端 `E`、`p:64:64`、`i64:64`、`i128:128`、`n32:64`、**`S128`**。
- **差异/冲突**：
  - **`S128`(16B) vs spec ABI §4.2 8B**：0628 已认定 S128 比契约严并改为 S64；**v5 现值 S128 与 spec 8B 不一致**（同 0628 `DL-040a:119,164-170` 暴露的 MISMATCH）。
  - **`n32:64` vs `n64`**：v5 用 `n32:64`（native 整数 32 快 64 合法），0628 用 `n64`；含义不同，须裁定。
  - **`i128:128`**：v5/0628 有（clang `__int128` 需要），TCH 无。v5 M3 不做 i128 codegen，但 DataLayout 对齐仍建议保留（0628 教训）。
  - **端序**：v5 spec 大端（`spec/DADAO-21 §数据表示`）；TCH 小端为**反例**，v5 保持 `E`。
- **「rb=基址」影响**：`p:64:64`（8 字节指针、8 字节对齐）与 RB 8 字节寄存器一致；栈对齐影响 `call` 前 SP 的 RB 值对齐。

**(c) 待判选项**

1. **栈对齐 `S128`(16B) vs `S64`(8B)**（spec 只要 8B）。
2. **`n32:64` vs `n64`**。
3. 是否保留/新增 **`i128:128`**（0628 因 clang 需要）。
4. 是否补 `-a:`（聚合对齐，TCH 用 `a:0:64`）。
5. 端序：v5 已定大端（`E`）——TCH 小端不采纳。

---

### C10 调用/返回机制

**(a) 归属**：**随 spec**（已定）。`call`/`ret` 用 RegRAS 由 `spec/SimRISC-06 §函数调用/§函数返回` 定；投影到 `contract-abi §2.3` + `abi.yaml call_ret` 即可。

**(b) 分析**

- **M68k**：`JSR`/`BSR`/`RTS` **写内存栈**返回地址（`M68kInstrControl.td:260-342`）；`M68kISelLowering.cpp:388-428` 为返回地址建固定帧对象。
- **DADAO-0628**：`call` 压 `ra63`(RegRAS)、`ret` 弹；**无内存返回地址槽**（`contracts/abi/spec.md §1.4:63-69`、`§4.3:299`「no memory return-address slot」、`§5.2-5.3`；`DL-055a:27`）。
- **TCH-llvm**：`CALL_IIII`/`CALL_RRII` `Uses=[RASP]`；`_RET_FIXME` `Uses=[RASP]`；无内存返回槽（`DadaoInstrInfo.td:641,651,674`）。
- **v5 现状**：spec `SimRISC-06` §函数调用/§函数返回；`contract-abi §2.3:140-145`；`abi.yaml call_ret:39-46`。实测 `call_iiii`/`ret_riii` 无 `Uses`/`isCall`/`isReturn`（`DADAOInstrInfo.td:538,554`）。
- **差异**：M68k 内存栈 vs DADAO RegRAS——**v5 已定 RegRAS**（0628/TCH 一致）。
- **「rb=基址」影响**：`rb0`(PC) 参与 `call`/`jump` 的 64 位地址计算（`spec/SimRISC-00:75-76`）。

**(c) 待判选项**：无（机制已定）。**但**：`call`/`ret` 指令需补 `isCall`/`isReturn`/`Uses=[rasp]`/`Defs`——属实现（见 C16）。

---

### C11 指令选择框架（SelectionDAG vs GlobalISel）

**(a) 归属**：**ADR**（纯实现机制取舍，高代价、跨全部 ISel 任务、结论固化）。**建议立 ADR**（用户 `SPEC-096k` 已点名）。

**(b) 分析**

- **M68k**：SelectionDAG **+ GlobalISel**（`M68k/GISel/` 8 文件：`M68kCallLowering.cpp`、`M68kInstructionSelector.cpp`、`M68kRegisterBankInfo.cpp`、`M68kLegalizerInfo.cpp` 等）。`M68kTargetMachine.cpp:71` 用 `TT.computeDataLayout()`；PassConfig 挂 `createM68kISelDag`。
- **DADAO-0628**：**仅 SelectionDAG**：`DADAOPassConfig::addInstSelector → createDADAOISelDag`（`DL-037b:32-38`；`DL-036a:239`）。
- **TCH-llvm**：**仅 SelectionDAG**：`DadaoPassConfig::addInstSelector → createDadaoISelDag`（`DadaoTargetMachine.cpp:107-111`），**无 GISel 目录**。
- **v5 现状**：无 ISel；`LLVM-033t` 任务书已定 SelectionDAG（约束：`SelectionDAGISelLegacy` + `createDADAOISelDag`）。LLVM 23.1.1。
- **差异**：全部含 SelectionDAG；仅 M68k 另有 GlobalISel。0628/TCH 均为 SelectionDAG。
- **「rb=基址」影响**：与框架选择无关（两框架都可用 bank 感知 lowering）。

**(c) 待判选项**

1. **SelectionDAG**（0628/TCH，v5 任务书现状）。
2. GlobalISel（仅 M68k 有）。
3. 两者并存（M68k）。
> 建议 ADR 固化（含：若选 SelectionDAG，是否保留未来加 GISel 的空间）。

---

### C12 常数材料化

**(a) 归属**：**随 spec**。`set.zw`/`set.ow`/`or.w`/`andn.w`/`add.si` 的语义由 `contract-isa §5/§7` 定。是否 constant pool、何时用 `add.si` vs wyde 序列是实现策略（可 ADR 可选）。

**(b) 分析**

- **M68k**：`MOV` 立即数 / `LEA` / constant pool（`M68kISelLowering.cpp:144` `ConstantPool Custom`）。
- **DADAO-0628**：`set.zw`（16 位 wyde）+ `or.w` 构造 64 位；小立即数 `addi`（**imms12**，范围窄）（`DL-061a:41-52`；大/负/高位逐一 wyde，`:73`；`DL-060a`；patch `0012-dadao-wyde-const`）。
- **TCH-llvm**：`DadaoWydePosition.h` / `DADAOInstrInfo.td` wyde 指令；常数材料化在 `DadaoISelDAGToDAG.cpp`（未逐行核）。
- **v5 现状**：`set.zw`/`set.ow`/`or.w`/`andn.w`（rd+rb 变体，`DADAOInstrInfo.td:563-610`）；小立即数 **`add.si`（imms18 = 18 位，范围 [-2^17, 2^17-1]，大于 0628 的 imms12）**（`DADAOInstrInfo.td:466/475`；`contract-isa §7.2:679-683`）。**关键约束**：`llvm-mc` `AsmParser` **静默忽略 `wpN` 具名常量**，须用**数值 wyde 位置 0-3**（`LLVM-035t` 任务书约束，源自 `tests/e2e/smoke_add.s` 注释）。
- **差异**：v5 小立即数 18 位（比 0628 的 12 位宽）；v5 无 constant pool 通路（M3 无 `.rodata`，倾向 0628）。
- **「rb=基址」影响**：指针常量（绝对地址）用 `set.zw-rb`/`or.w-rb` 材料化（`contract-isa §5.2:441,447`）。

**(c) 待判选项**

1. 小立即数阈值：用 `add.si` 的 18 位范围，超出走 wyde 序列。
2. 是否引入 constant pool（v5 M3 无 `.rodata` → 倾向**不引入**，0628 路线）。
3. `wpN` 具名 vs 数值位置（AsmParser 限制 → **数值 0-3**）。
4. 负常数/高位（`INT64_MIN`、`0xFFFFFFFF00000000`）的 wyde 序列（0628 `DL-061a:73`）。

---

### C13 窄类型/子寄存器

**(a) 归属**：**随 spec + 实现**。v5 spec **无 subreg**（单一 64 位寄存器），窄 load/store/扩展语义归 `contract-isa §3/§10-12`；「大端窄访存的字节偏移/掩码策略」是**实现取舍 + 高代价**（0628 反复踩坑）→ **建议 ADR（可选）**。

**(b) 分析**

- **M68k**：`DR8`/`DR16`/`DR32` 子寄存器（B/W/L），`MxSubRegIndex8Lo/16Lo`（`M68kRegisterInfo.td:103-107,28-29`）；i8/i16/i32 分别注册（`M68kISelLowering.cpp:62-64`）。
- **DADAO-0628**：单一 64 位寄存器、**无 subreg**；窄类型提升/扩展；窄 load 按宽选 `ld?s/ld?u`、`exts`/`sign_extend_inreg`（`DL-062a:41-46`）；**大端窄 load 掩码偏移 bug**：`x & 0xFF` 被 `ReduceLoadWidth` 类 combine 按小端读偏移 0（应读偏移 3），是 silent miscompile（`DL-068a:16-26`）。
- **TCH-llvm**：单一 64 位寄存器、**无 subreg**（RegisterClass 均 64-bit，无 subreg index）；窄 load 有 `LDBU/LDBS/LDWU/LDWS/LDTU/LDTS`（`DadaoInstrInfo.td`）。
- **v5 现状**：**无 subreg**（`DADAORegisterInfo.td` GPRD/GPRB 单一 64 位）；指令有 `ld.ub/ld.sb/ld.uw/ld.sw/ld.ut/ld.st/st.b/st.w/st.t`（`DADAOInstrInfo.td:131-206`）；`mayLoad/mayStore` **0 处**；大端（spec）。
- **差异**：M68k 有 subreg；0628/TCH/v5 均无。**大端**下窄访存须按端序算字节偏移（0628 血泪教训）。
- **「rb=基址」影响**：窄访存地址仍为 `rb base + imm12`（`contract-isa §3.1:272`）。

**(c) 待判选项**

1. 无 subreg + 提升/扩展（0628/TCH；v5 已定无 subreg）。
2. **大端窄 load 的字节偏移/掩码策略**（须显式覆盖；0628 `DL-068a` 教训）。
3. 窄类型算术回绕（i32 溢出行为）。
4. `mayLoad`/`mayStore` 标注（`LLVM-036t` 已列）。

---

### C14 RB 算术语义（结合「rb=基址」）

> **2026-10-04 更正**：RB 加减是**全 64 位运算**（结果为完整 64 位）；**仅当用该地址访存时**硬件取 `rb[47:0]`，`rb[63:48]` 用于**判断地址溢出**。下方正文“地址计算仅在低 48 位有效”属 spec 措辞误导（见 ISS-129）。

**(a) 归属**：**随 spec**。RB 算术**指令语义**已在 `contract-isa §7`（`.tao/knowledge/contract-isa.md:671-705`）明确；「指针算术在 GPRB 直接做 vs 转 GPRD 做」是实现取舍（可 ADR 可选）。

**(b) 分析**

- **M68k**：AR 可参与算术（`ADDQ`/`ADDA` 等，`M68kInstrArithmetic.td`）；且 `XR32` 联合类使 AR 与 DR 同 MOV（`M68kInstrInfo.cpp:686-702`）——AR 既作基址又可算术语义。
- **DADAO-0628**：**RB-bank 算术指令存在且已用**——`ADDRB_ORRR`（`add`）/`SUBRB_ORRR`（`sub`）/`ADDI_RBRRII`（`addi`）定义于 patch `0004:239-240,326`，并加 `(DADAOAddrB GPRB, GPRD)→ADDRB_ORRR` pattern（patch `0060:479`）；**但用于栈帧调整 / 大帧偏移材料化**（patch `0051:69,102,374`），**一般 GEP 指针算术先 `rb2rd` 转 GPRD 算完再 `rd2rb` 转回**（`DL-059a:114-116` 反汇编：`rb2rd rd17, rb8, 1 # GPRB→GPRD，供指针运算`）。即 **0628 未把一般指针算术放在 GPRB 做**。
- **TCH-llvm**：GPRB = `[i64,bp64]`，但未见到针对 GPRB 的 `add` pattern（C CC 指针本就走 RD，`DadaoInstrInfo.td` 未核到 GPRB 算术 pattern）——**待核实**。
- **v5 现状**：`add.so-rb` = `(outs GPRB)(ins GPRB:$rc, GPRD:$rd)` → **`rb = rb + rd`**（`DADAOInstrInfo.td:686`）；`sub.so-rb` = `rb = rb - rd`（`:694`）；`add.si-rb` = `rb += sext(imms18)`（`:475`）；`cmp.uo-rb` = `(outs GPRD)(ins GPRB,GPRB)` → 比较两个 RB、结果写 RD（`:702`）。spec `contract-isa §7:671-705`：RB 加减「地址计算仅在低 48 位有效，溢出丢弃」「用户可通过高 16 位判断地址溢出」；`cmp.uo-rb` 整 64 位无符号比较。
- **差异/冲突**：用户背景称「0628 GPRB 算术用 add.so/sub.so（rb 变体）」——**实测需修正**：0628 的 RB 算术用于**帧/地址调整**，一般指针算术**转 RD**（`DL-059a` 证据）。这是重要的口径澄清。
- **「rb=基址」影响（关键）**：`add.so-rb` 第二操作数是 **GPRD**（数据寄存器），即 `base(rb) + offset(rd)`——**RB+RB 无直接指令**。因此：
  - `ptr + i64 offset` → **恰好一条 `add.so-rb`**（base=指针、offset=RD 偏移），天然贴合「rb=基址+偏移」；
  - `ptr - ptr`（指针差）无直接指令（须转 RD 或用 `cmp.uo-rb` + 其它）；
  - `ptr + ptr` 无意义（地址加地址）；
  - RB 的**高 16 位参与运算**（全 64 位），故地址算术溢出可用高 16 位检测。

**(c) 待判选项**

1. 指针算术落点：**直接落 GPRB**（用 `add.so-rb`/`add.si-rb`，利用 base+offset 结构）vs **0628 式转 GPRD**（`rb2rd`→RD 算术→`rd2rb`）。
2. `cmp.uo-rb` 是否用于指针比较（结果在 RD，可能需再 `rd2rb` 或直接 RD 比较）。
3. RB 值是否允许参与一般（非地址）运算——按「rb=基址」应**仅用于基址/绝对地址**；`add.so-rb` 的 `rb+rd` 语义支持「基址+偏移」，但不支持「任意地址算术」（如两指针相加）。
4. RB 高 16 位的处理（`add.so-rb` 全 64 位；作访存基址时取低 48 位）。

---

### C15 RA/RF bank + `rb2` 分配

**(a) 归属**：**两者**。bank 保留策略（RA/RF 不分配）由 ABI/范围定（spec + M3 边界）；**`rb2` 是否 reserved**取决于 C7（SP-only 可不用 FP）→ 随 C7 ADR。

**(b) 分析**

- **M68k**：无 RA/RF bank；A5=BP、A6=FP（`M68kRegisterInfo.cpp:49-51`）。
- **DADAO-0628**：RA/RF **全 reserved**（`DL-053a`/`DL-055a`）；M3 无 RF class；`rb2` reserved（SP-only 下不用 FP，仍 reserved）。
- **TCH-llvm**：`GPRA` `isAllocatable=false`（`DadaoRegisterInfo.td:81-86`）；**无 RF 寄存器类**（`DadaoRegisterInfo.td` 只有 RD/RB/RA）；`getReservedRegs` 只保留 `RD0/RD8/RB0/RB8/RBSP/RBFP/RAVV/RASP`（`DadaoRegisterInfo.cpp:41-52`）——**未全部 reserve RA/RF**（靠 `isAllocatable=0`）；`rb2` 被 `RBFP` reserved。
- **v5 现状**：`GPRF`/`GPRA` `isAllocatable=0`（`DADAORegisterInfo.td:155,170`）；`getReservedRegs` 保留 `rd0/rb0/rb1/rb2` + **全部 rf0-63 + 全部 ra0-63**（`DADAORegisterInfo.cpp:41-54`）；M3 边界「RA/RF 保留不分配」；**`rb2` 现 reserved**。
- **差异**：reserve 方式不同（TCH 靠 `isAllocatable`+少量 reserved；v5 显式 reserve 全部 RA/RF）。`rb2` 都 reserved（无论是否用 FP）。
- **「rb=基址」影响**：若 SP-only 释放 `rb2`，则多一个可用**基址寄存器**（但违反 spec 的 `rb2=rbfp` 角色，且 `abi.yaml` 标其 callee-saved）。

**(c) 待判选项**

1. RA/RF 保留方式：显式 `Reserved.set`（v5 现状）vs 只靠 `isAllocatable=0`（TCH）。
2. **`rb2` 在 SP-only 下是否仍 reserved**（v5 现保留；0628 保留；M68k FP 用 A6）。
3. `rd1`/`rd2-7`/`rb3-7` 是否显式 reserve（v5 现靠 `GPRD_Allocatable`/`GPRB_Allocatable` 排除；`GPRD`/`GPRB` 全集用于 MC）。

---

### C16 `call` 的 `Defs`/`RegMask`

**(a) 归属**：**两者**。caller-saved / callee-saved **集合**归 ABI（C6/C5）；`call` 指令**必须声明 `Defs`/`RegMask`** 是**实现层寄存器分配正确性约束**，且 0628 两次事故「结论固化为约束」→ ADR。**建议立 ADR**（或并入 C6 ADR）。

**(b) 分析**

- **M68k**：`LowerCall` 附 `getRegisterMask(RegInfo->getCallPreservedMask(...))`（`M68kISelLowering.cpp:839-842`）；call 指令 `isCall=1`（`M68kInstrControl.td:279`）。
- **DADAO-0628**（**教训**）：
  - `CALL_IIII`/`CALL_RRII`/`CALL_PSEUDO_INDIRECT` `Defs=[RD31, RB31]`（`DL-070a`：`Defs=[RD31]` 缺 `RB31` → `-O1+` MachineVerifier 报 `Using an undefined physical register`，波及 16 个 musl 对象）；`RET_RIII` **不需改**（返回值定义在更早的 `CopyToReg`+glue 链，`DL-070a` 三方独立验证）。
  - `LowerCall` 必须附 `getRegisterMask(TRI->getCallPreservedMask(MF,CallConv))`（`ML-004c`：不附 RegMask → 「调用前算好 GPRB 地址→调用→调用后复用」静默用陈旧值 → llvm-test-suite 8/10 失败）。
  - 连带：`storeRegToStackSlot`/`loadRegFromStackSlot` 必须按 bank 路由 GPRB 到 RB-bank `LDO_RB`/`STO_RB`（`ML-004c` 复核发现）。
- **TCH-llvm**：`isCall=1, Uses=[RASP]`（**无显式 `Defs`**，靠 RegMask 隐含 clobber）；`LowerCCCCallTo` 附 RegMask（`DadaoISelLowering.cpp:817-820`）；`getCallPreservedMask→CSR_RegMask`（`DadaoRegisterInfo.cpp:189-192`），**但 CSR 只 RD32-63**（§0.3）→ GPRB 全部（含 RB32-63）被当 clobbered → 与 C6 缺陷同源，**RB callee-saved 会被误 clobber**。
- **v5 现状**：`call_iiii`/`call_rrii`/`ret_riii` **无 `isCall`/`isReturn`/`Defs`/`Uses`**（`DADAOInstrInfo.td:271,538,554`）；`getCallPreservedMask` **未实现**；`getCalleeSavedRegs` 空。
- **差异**：0628 显式 `Defs=[RD31,RB31]`；TCH 靠 RegMask（且 CSR 不全）。v5 需按 0628 教训实现。
- **「rb=基址」影响**：`call` 可 clobber RB caller-saved（rb8-31）；指针返回值 `rb31` 必须 `Defs`；RB callee-saved（rb32-63）必须进 `getCallPreservedMask` 的 preserved 集合，否则跨调用存活的**基址**被误 clobber。

**(c) 待判选项**

1. `call` 的 `Defs`：`[rd31, rb31]`（0628）vs 仅靠 RegMask（TCH）。
2. `RegMask` 来源：实现 `getCallPreservedMask` 并在 `LowerCall` 附上（0628 `ML-004c`）。
3. CSR/RegMask **必须含 rb32-63**（否则 GPRB callee-saved 被误 clobber）——与 C6 一致。
4. `ret` 是否需 `Defs`（0628 判「不需」，理由：定义在 `CopyToReg`+glue 链）。
5. `storeRegToStackSlot`/`loadRegFromStackSlot` 按 bank 路由（v5 需实现）。

---

## 3. 待用户判决汇总（按归属归并）

| 判决组 | 关联 C | 待判要点（一句话） |
| --- | --- | --- |
| **A. bank/类型建模** | C1, C2 | 硬双类 vs 联合类；指针用独立 MVT vs i64 通吃 |
| **B. 调用约定内容** | C4, C5, C6, C10 | 参数/返回寄存器与窄扩展；溢出区口径；CSR 是否含 rb32-63/SP/FP |
| **C. 帧策略** | C7, C15 | SP-only vs FP；`rb2` 是否保留；大帧偏移/RegScavenger |
| **D. DataLayout** | C9 | S128 vs S64；n32:64 vs n64；i128:128；端序（大端已定） |
| **E. 框架** | C11 | SelectionDAG vs GlobalISel |
| **F. 指令映射** | C3, C12, C13, C14 | 同/跨 bank 搬运；常数材料化阈值/pool；大端窄访存；指针算术落 RB vs 转 RD |
| **G. 分配正确性** | C16 | call `Defs=[rd31,rb31]` + RegMask + bank 路由 |
| **H. 无需新规** | C8, C10（机制） | 已由 spec 定，投影 ABI 即可 |

---

## 4. 未核实 / 须注意项

1. **0628「GPRB 算术用 add.so/sub.so」**（用户背景原话）：**实测需修正**——0628 的 RB 算术（`ADDRB_ORRR`/`ADDI_RBRRII`）用于**栈帧调整/大帧偏移材料化**；一般 GEP 指针算术**转 GPRD**（`DL-059a:114-116`）。本文按实测为准。
2. **TCH-llvm C14**（GPRB 算术 pattern）：未逐行核到 `DadaoInstrInfo.td` 中 GPRB 的 `add` pattern，**待核实**。
3. **TCH-llvm DataLayout 小端 `e`**：与 v5 spec 大端**冲突**——须核实 TCH 是否为另一变体/早期版本；**v5 以 spec 大端为准**，TCH 小端不作为依据。
4. **LLVM 23 自定义 MVT 可行性**（C2 选项 1）：TCH 用 LLVM 16 的自定义 `bp64`；v5 基线 LLVM 23.1.1，**须核实**能否引入等价 value type（否则退回 iPTR/i64 通吃）。
5. **CSR_SaveList 是否含 SP/FP**（C6/C15）：v5 `abi.yaml` 逐寄存器与派生块不一致，须澄清。
6. **本分析只读**：未改 `spec/`、`contracts/`、任务书；未提交 git；未创建 ADR（decision 待用户逐条确认）。

---

## 5. 判定结果（2026-10-04，用户逐条判定）

> 逐条判定进行中（C1–C10 已判，其余待判）。每条均经用户确认；ADR 待全部判完后按「建议 ADR 集合」落地。

| C | 判定 | ADR |
|---|---|---|
| **C1** | **硬双类**：`GPRD=i64`、`GPRB=指针/基址`；指针经 CC/ISel 强制落 GPRB | 建议立 |
| **C2** | **(2) i64 通吃 + `ArgFlags.isPointer()`/`CCIfPtr` 人为约束**（不改 LLVM 核心） | 建议立 |
| **C3** | **(1) 专用 `rd2rd`/`rb2rb`**；跨 bank 用 `rd2rb`/`rb2rd` | 否 |
| **C4** | 溢出区 **(a) 全局声明序**（单栈区、按参数声明序；同 0628/主流）；窄参数由 caller 扩展 | 并入 ABI |
| **C5** | 指针返回 `rb31`；窄返回 **(A) callee 扩展（canonical）**；多返回值/i128 **归 M4**（i128 约定 M4 再议） | 建议立 |
| **C6** | `CSR = rd32–63 ∪ rb32–63`；caller-saved = rd/rb 8–31；`rd1–7`/`rb3–7` reserved；`rd0`/`rb0` 特殊；**SP(rb1) ∉ CSR**（对称回收） | 否 |
| **C7** | **(ii) 标准条件式** `hasFPImpl = DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment`；默认 **SP-only(rb1)**，选项/条件 → **FP=rb2**；`getFrameRegister = hasFP ? rb2 : rb1`；**大帧**：方案2 为主（`rb2rb`+`add.si`，≤±128K，单/多寄存器都支持），方案1（rd 存偏移 + `ldm/stm`）仅 >128K；**M3 现在实现** | **建议立** |
| **C8** | `SP=rb1`、`FP=rb2`（spec 定）；`getFrameRegister` 须改为条件式（现行返回 rb2 恒值） | 否 |
| **C9** | DataLayout = **`E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`**（`S128`/`i128:128`/省略 `a:` 随主流；`n8:16:32:64` 同 x86-64；端序 `E` 有意） | **建议立** |
| **C10** | `call`/`ret` 用 **RegRAS(ra63)**，**无内存返回地址槽**；机制随 spec、无取舍；实现项 `isCall`/`isReturn`/`Uses`/`Defs` 归 C16 | 否 |
| **C11** | **SelectionDAG 为主**，**预留后续加 GISel 的空间**（M3 不做 GISel）；与 x86-64/RISC-V 模式一致 | **建议立** |
| **C12** | 常数材料化：`set.ow`/`set.zw` **按正负选基调** + `or.w`/`andn.w` 修正其余 wyde（镜像 `set.rd` 策略）；**不引 constant pool**；`add.si` 仅用于**增减**（非立即数设置）；**`wpN` 是唯一合法 wyde 位置写法（裸数字 0–3 须报错 → ISS-128）** | 否 |
| **C13** | **无 subreg**（同 RISC-V 的单 64 位设计，非因“x86 特有”）；**大端窄访存须显式保证/测试** `ReduceLoadWidth` 类 combine 的字节偏移（0628 silent miscompile 教训）；窄算术回绕 = **用对应符号后缀的窄指令**（`add.st/ut` 等：N 位结果 + 扩展写满 64），无额外规则；补 `mayLoad`/`mayStore` | **建议立**（大端） |
| **C14** | 指针算术**直接落 GPRB**（`add.so-rb`/`add.si-rb`/`sub.so-rb`，利用 base(rb)+offset(rd)）；`cmp.uo-rb` 做指针比较（结果→RD，供 `br.*`/`cs.*`）；**RB 算术=全 64 位**，仅**访存**取低 48 位、高 16 位示溢出（→ISS-129）；`ptr−ptr` 暂转 RD，待新增 `sub rd,rb,rb`（→ISS-130）；RB 仅用于基址/绝对地址 | 建议立 |
| **C15** | RA/RF 保留不分配（M3 边界）；**`rb2` 始终 reserved**（随 C7，可能是 FP）；`rd1-7`/`rb3-7` 保留；保留方式统一为 **`isAllocatable=0` + 显式 `Reserved.set`** 双保险 | 随 C7 ADR |
| **C16** | `call` **`Defs=[rd31, rb31]`**；实现 **`getCallPreservedMask`（含 rb32–63）** 并在 `LowerCall` **附 RegMask**；`storeRegToStackSlot`/`loadRegFromStackSlot` **按 bank 路由**；`ret` **不加 Defs** | **建议立** |
| **C17** | **无标志位**（CZSO 取消）→ `cmp.*` 结果（−1/0/1）落 **rd**、`br.*` 测 rd/rb；**rd 用虚拟寄存器**（(A)，不设固定 RDCC/不做融合）；`==`/`!=` 用 `br.eq/ne` 省 cmp；`p==NULL` 用 **`br.z/nz {rb}`**（1 条）；`p==q` 用 `cmp.uo-rb`+`br.z`（2 条，**暂不新增指令**）；`cmp.*` 的 SDNode **不得标 `SDNPCommutative`**（0628 教训；**只写任务书约束**，不立 issue/ADR） | 否 |

### 附注与澄清

- **C4 栈溢出区**：`spec/DADAO-21 §栈溢出规则` 同句「按声明顺序从左到右」与「各组溢出参数连续紧凑存放」互相拉扯，**取全局声明序**；建议补 spec 澄清句。
- **C7 FP**：`rb2` 仅在 FP 时启用（DADAO 的 rb2 是特殊寄存器，非 M68k 那种兼作通用 callee-saved）；大帧 >128K 的**单**访问无寄存器偏移形式，仍需方案2 的 `add.so`（两寄存器形式）。
- **C9 `a:`**：`a:0:64` 是 **no-op**（= 默认 `a:8:64`，聚合 ABI 1 字节）；spec `:107`「聚合 ≥8B 对齐」若指内存布局则须 `a:64`，但**已裁定省略 `a:`**（随主流/C 规则，避免改变 struct 尺寸）。**M4 引入 clang 时须核对 clang 侧 AST 布局一致**。
- **`iiii` 立即数宽度（非不一致）**：`iiii` 编码 **24 位**（`imms24`，`SimRISC-00:220`/`opcodes.yaml`）；因 SimRISC 指令 32 位对齐，PCRel 位移**左移 2 位**使用，**有效相对范围 = 26 位**（速查表 `call/jump [rb0, imms26]` 指此）。两者描述不同层面，**不矛盾**。
- **C17「暂不新增指令」的范围**：仅指**不给 `br.eq/ne` 增加 rb 形式**（两指针相等走 `cmp.uo-rb`+`br.z`，2 条）；**ISS-130（新增 `sub rd,rb,rb`）按原计划保留**（M3 用到 `ptr−ptr` 前落地，走 spec 变更 + ADR）。

---

## 修订注记（2026-10-09，SPEC-124t；正文不追溯重写）

> 用户 2026-10-09 裁定：返回值寄存器由 `rd31/rb31/rf31` 改为 **`rd8/rb8/rf8`**；多返回值/聚合按**声明顺序自 8 递增**、**每 bank K=8**；`sret` 经 `rb16`（其后地址参数自 `rb17` 起）；**不立 ADR，但修改 `spec/DADAO-21 §返回值` 后重新生成 contract**。
>
> 下列本文档正文条目**已随本变更过时**（正文保留作历史，勿据此实现）：
> - §C5 / C16 及正文各处出现的 `rd31`/`rb31`/`rf31` 返回寄存器编号 → 现为 **`rd8`/`rb8`/`rf8`**（依据改册后的 `spec/DADAO-21 §返回值`；见 `contract-abi.md §4.4/§4.6/§6.1`、`contracts/abi.yaml return_values`）。
> - C16 `call` 的 `Defs=[rd31, rb31]` → 现为**返回寄存器区间** `rd8–rd15`/`rb8–rb15`（见 `contract-abi.md §4.6`）。
> - C5「指针返回 `rb31` 直接 / 窄返回 callee 扩展」→ **口径不变**，仅寄存器名改 `rb8`。
> - 正文中「返回寄存器 `rd31/rb31/rf31`」属**函数返回值约定**用途；其余 `rd31`/`rb31`/`rf31` 命中（系统调用 / semihosting / 参数寄存器 `rd16–rd31` 等）**不受影响**。
