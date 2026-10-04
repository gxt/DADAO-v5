# ADR-0018: M3 CodeGen 取舍点（C1–C17 已判）

**状态**：Accepted
**日期**：2026-10-04
**决策者**：用户（逐条确认，见 `project_M3-codegen-choices.md §5`）
**关联**：`SPEC-096k`（M3 启动与分解）；`.tao/knowledge/project_M3-codegen-choices.md §5`（权威判定）；任务 `INFRA-035t`/`SPEC-097t`/`LLVM-033t`–`041t`/`TESTCASES-026t`/`INTEG-012t` 及各模块 `m`

> **合并说明**：本 ADR 由原 10 条草案（C1/C2/C4/C5/C7/C9/C11/C13/C14/C16）合并为**单文件**；32 条 decision 经用户逐一审核**无变化、直接通过**，逐字保留，状态 `Accepted`。C17（无标志位 compare-branch）按用户裁定**只落任务书约束、不立 ADR**；C6（CSR）归 ABI（`SPEC-097t`）。本 ADR **不承载规范正文**（正文归 `spec/` 与 `contract-*`），只记决策/理由/被否方案/指向。

## Context（背景）

- **M3 = Basic CodeGen（纯整数）**：`llc` 把标量整数/指针函数（LLVM IR）编译为 DADAO 汇编，经 MC → **单 TU** obj/raw binary → `qemu-system-dadao` 执行正确；门槛 `make test-codegen` 全绿。bank 只用 `GPRD`+`GPRB`；`RA`/`RF` 仅「保留不分配」；无需链接器（单 TU 自包含 + 最小重定位）。
- M3 CodeGen 涉及一组跨组件、高代价、需一致且有取舍的取舍点 **C1–C17**；逐条分析（含三参考 M68k / DADAO-0628 / TCH-llvm 的 `file:line` 证据）见 `.tao/knowledge/project_M3-codegen-choices.md`。
- 其中 **§5「判定结果」表（C1–C17）及其「附注与澄清」是权威判定**，已逐条经用户确认。本 ADR 固化需立 ADR 的部分。
- 各取舍点的 ABI 内容（跨组件可观察事实）另行投影到 `contract-abi.md`/`contracts/abi.yaml`（`SPEC-097t`），不在本 ADR 内定义。

## Decision（决策）

### C1 ISel 寄存器模型（硬双类）

- **D1**：采用**硬双类** —— `GPRD=i64`（数据）、`GPRB=指针/基址`。
- **D2**：指针**经 CC/ISel 强制落 GPRB**（不依赖寄存器分配器软偏好）。

### C2 指针 value type（i64 通吃）

- **D1**：指针**不引入独立 value type**，**i64（iPTR）通吃**。
- **D2**：用 `ArgFlags.isPointer()`/`CCIfPtr` 做**人为 bank 约束**，**不改 LLVM 核心**。

### C4 栈溢出区口径（ABI）

- **D1**：栈溢出区取**全局声明序**（**单栈区**、按参数声明序；同 0628/主流）。
- **D2**：窄参数（`<8B`）由 **caller 扩展**到 8B（按符号性）。

### C5 返回值与窄返回扩展

- **D1**：指针返回**直接 `rb31`**。
- **D2**：窄返回由 **callee 扩展（canonical）**，caller **不截断**。
- **D3**：多返回值 / `i128` **归 M4**（`i128` 约定 M4 再议）。

### C7 帧布局与 hasFP 策略（附 C8 `getFrameRegister`、C15 `rb2`/保留方式）

- **D1**：`hasFPImpl` 采用**标准条件式** —— `hasFPImpl = DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment`。
- **D2**：默认 **SP-only（rb1）**；上述条件成立或有选项时 → **FP = rb2**。
- **D3**：`getFrameRegister = hasFP ? rb2 : rb1`（C8 的条件式落地；替代现行恒返回 `rb2`）。
- **D4**：大帧：**方案2 为主**（`rb2rb` + `add.si`，≤±128K，单/多寄存器都支持）；方案1（rd 存偏移 + `ldm/stm`）仅 **>128K**。
- **D5**：**M3 现在实现**（帧布局、prologue/epilogue、大帧方案2）。
- **D6**：`rb2` **始终 reserved**（可能是 FP）；RA/RF **保留不分配**（M3 边界）；`rd1-7`/`rb3-7` 保留；保留方式统一为 **`isAllocatable=0` + 显式 `Reserved.set` 双保险**。

### C9 DataLayout / 栈对齐

- **D1**：DataLayout 串 = **`E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`**。
- **D2**：保留 **`S128`**、**`i128:128`**；**省略 `a:`**；采用 **`n8:16:32:64`**；端序 **`E`（大端，有意）**。

### C11 指令选择框架

- **D1**：M3 采用 **SelectionDAG 为主**。
- **D2**：**预留后续加 GISel 的空间**（M3 **不做** GISel）。

### C13 窄类型 / 子寄存器

- **D1**：**无 subreg**（同 RISC-V 的单 64 位设计，**非因「x86 特有」**）。
- **D2**：**大端窄访存须显式保证/测试** `ReduceLoadWidth` 类 combine 的字节偏移。
- **D3**：窄算术回绕 = **用对应符号后缀的窄指令**（`add.st/ut` 等：N 位结果 + 扩展写满 64），**无额外规则**。
- **D4**：补 `mayLoad`/`mayStore` 标注。

### C14 RB 算术语义

- **D1**：指针算术**直接落 GPRB**（`add.so-rb`/`add.si-rb`/`sub.so-rb`，利用 base(rb)+offset(rd)）。
- **D2**：`cmp.uo-rb` 做指针比较（结果→RD，供 `br.*`/`cs.*`）。
- **D3**：**RB 算术 = 全 64 位**，仅**访存**取低 48 位、高 16 位示溢出（→`ISS-129`）。
- **D4**：`ptr−ptr` **暂转 RD**，待新增 `sub rd,rb,rb`（→`ISS-130`）。
- **D5**：RB **仅用于基址/绝对地址**。

### C16 `call` 的 `Defs`/`RegMask`（附 C6 为 ABI 输入）

- **D1**：`call` 声明 **`Defs = [rd31, rb31]`**。
- **D2**：实现 **`getCallPreservedMask`（含 rb32–63）** 并在 `LowerCall` **附 RegMask**。
- **D3**：`storeRegToStackSlot`/`loadRegFromStackSlot` **按 bank 路由**（GPRB → RB-bank 存取）。
- **D4**：`ret` **不加 `Defs`**。

## Rationale（理由，按组）

### C1

- 「rb=基址」要求指针必须落 GPRB 才与 ISA 语义自洽；联合类软偏好允许指针临时落 RD，与「地址只在 RB」相悖。
- 硬双类与 0628/TCH 实践一致，且 v5 已有可分配类就绪。

### C2

- 0628 的 i64 通吃 + bank 感知 CC/ISel 已在 codegen 实践中走通，且不触碰 LLVM 核心，改动代价低。
- TCH 的自定义 `bp64` 是 LLVM 16 特性，v5 在 LLVM 23.1.1 上能否等价引入未知；引入独立 MVT 代价高。

### C4

- 全局声明序消除 spec 同句内两读的歧义，实现与验证均确定。
- 与 0628 已验证口径一致，减少后续跨组件分歧。

### C5

- spec 字面指针返回走基址寄存器 → `rb31`；TCH 的 `rd31`+`rd2rb` 与其 C CC 未落实 RB 同源，语义等价但多一条指令、与 spec 字面不符。
- 窄返回值扩展为 spec 空白，需固化；0628 的「callee 扩展 / caller 不截断」是已验证决策，与 M3 目标一致。

### C7

- 条件式兼顾两者：默认 SP-only 与 0628 已验证实现一致；条件成立（变长对象/取帧地址/栈重对齐/禁用消除）时建 FP，覆盖 SP-only 无法处理的场景。
- 「rb=基址」下 FP 作为帧基址正是 RB 的本职用途；但 `rb2` 非通用，故 D6 始终保留。
- 大帧以两寄存器形式（`add.so` 的 base+offset）为主，覆盖单/多寄存器访问；`ldm/stm` 仅在 >128K 且需要长偏移时使用。

### C9

- `S128`/`i128:128`/省略 `a:` 随主流；`i128:128` 是 clang `__int128` 布局所需（0628 教训），M3 即便不做 i128 codegen 也保留。
- `n8:16:32:64` 同 x86-64；端序 `E` 依 v5 spec 大端（`spec/DADAO-21 §数据表示`）。
- **`a:0:64` 是 no-op**（= 默认 `a:8:64`，聚合 ABI 1 字节）；显式写 `a:` 无增益并可能改变 struct 尺寸，故**省略**。

### C11

- 与 x86-64/RISC-V 主流后端模式一致；0628/TCH 的已验证路线均为 SelectionDAG，风险最低。
- SelectionDAG 的 TableGen pattern + 自定义 `ISelDAGToDAG` 足以覆盖 M3 纯整数标量。

### C13

- v5 spec 已定单 64 位寄存器、无 subreg；窄类型以提升/扩展处理。
- 大端下窄访存的字节偏移与掩码易被 combine 按小端假设处理，必须显式覆盖并测试，避免 silent miscompile。

### C14

- `add.so-rb` 的语义恰为「base(rb)+offset(rd)」，天然贴合「rb=基址+偏移」；指针偏移量本就来自数据运算（RD）。
- RB 全 64 位参与运算，作访存基址时硬件取低 48 位、高 16 位可判地址溢出（`ISS-129` 澄清）。

### C16

- `call` 会写返回值寄存器 `rd31`/`rb31`，须在 `Defs` 显式声明，否则 liveness/verifier 出错（`DL-070a`）。
- RegMask 必须正确表达「哪些寄存器跨调用存活」（preserved），含 **RB32–63**；否则 GPRB callee-saved（地址类 callee-saved）被误 clobber（`ML-004c`，与 C6 同源）。
- `ret` 的返回值定义在 `CopyToReg`+glue 链，无需 `Defs`（0628 三方独立验证）。

## 被否方案与理由（汇总）

### C1

- **R1（否决）**：联合类 + 软偏好（M68k 路线，`XR = GPRD ∪ GPRB` + `CC_M68k_Any_AssignToReg` 式指针优先）。理由：M68k 的 AR 可作一般运算，v5 的 RB 不行（见 C14）；软偏好允许指针临时落 RD，与 ISA 语义相悖。
- **R2（否决）**：硬双类 + 独立指针 MVT（TCH 风格）。理由：指针 value type 已在 C2 按用户判定改为 i64 通吃 + 人为约束，不引入独立 MVT。

### C2

- **R1（否决）**：独立指针 MVT（TCH 式自定义 `bp64` 或复用 `iPTR` 强绑定）。理由：LLVM 23 可行性未核实，需改 LLVM 核心、代价高；且与 C1 的硬双类不冲突（硬双类用 CC/ISel 即可）。
- **R2（否决）**：纯 i64 硬双类、无 bank 感知 CC（v5 现有 `[i64]` 不变、仅 Lowering 显式建 GPRB vreg）。理由：约束最弱，出错风险高（0628 靠大量踩坑修补）；D2 的 `isPointer`/`CCIfPtr` 是对它的补强。

### C4

- **R1（否决）**：**per-bank 各自连续**（spec「该 bank 的后续参数…按声明顺序」的字面读法）。理由：与同句「各组溢出参数连续紧凑存放」冲突，且 0628 未采用；歧义更大。

### C5

- **R1（否决）**：指针返回经 `rd31` + `rd2rb` 转换（TCH 式）。理由：与 spec 字面（指针→基址寄存器）不符，且多一条指令。
- **R2（否决）**：caller 截断窄返回。理由：与 0628 已验证决策相反，跨组件语义不稳。
- **R3（否决）**：`i8`/`i16` 返回落子寄存器（M68k `BD0`/`WD0`）。理由：v5 **无 subreg**（见 C13），不适用，统一 64 位寄存器。
- **R4（否决，顺延）**：M3 纳入 `i128` 返回（`rd31:rd30`）。理由：超出 M3 边界，归 M4。

### C7

- **R1（否决）**：`hasFP` 恒 true（TCH 式，每函数都建 FP）。理由：牺牲 leaf 函数、与 0628 实践相悖，代价无谓。
- **R2（否决）**：无条件 SP-only（0628 式，永不建 FP）。理由：无法覆盖 `hasVarSizedObjects`/`isFrameAddressTaken`/`hasStackRealignment` 等场景。
- **R3（否决）**：大帧以方案1（`ldm/stm` + rd 存偏移）为主。理由：>128K 才需要；≤±128K 用方案2 更直接。

### C9

- **R1（否决）**：`S64`（0628 因「ABI §4.2 8 字节」改）。理由：v5 取主流 `S128`；spec 的 8B 是 `call` 时 SP 对齐要求，不强制 DataLayout 栈对齐为 8。
- **R2（否决）**：`n64`（0628 式）。理由：`n8:16:32:64` 与 x86-64 一致、语义更明确。
- **R3（否决）**：显式 `a:`（如 TCH `a:0:64`，或 spec 若指内存布局需 `a:64`）。理由：已裁定省略 `a:`（随主流/C 规则，避免改变 struct 尺寸）。
- **R4（否决）**：小端 `e`（TCH 式）。理由：与 v5 spec 大端**直接冲突**，不采纳。

### C11

- **R1（否决）**：GlobalISel。理由：仅 M68k 参考有，M3 无必要、风险高。
- **R2（否决）**：SelectionDAG 与 GISel 并存（M68k 式）。理由：M3 边界不需要，徒增成本。

### C13

- **R1（否决）**：M68k 式子寄存器（B/W/L，`DR8`/`DR16`/`DR32`）。理由：v5 spec 无 subreg，引入代价高且与 ISA 不符。
- **R2（否决）**：大端窄访存不做专门测试/保证。理由：0628 silent miscompile 教训，禁止。

### C14

- **R1（否决）**：0628 式转 GPRD（`rb2rd`→RD 算术→`rd2rb`）。理由：多两条跨 bank 搬运、与「rb 承载基址」不符；用户裁定改为直接落 GPRB。
- **R2（否决）**：以 `rb2rd`×2 + `sub.o` 三条实现 `ptr−ptr` 为终态。理由：`ISS-130` 计划新增单条 `sub rd,rb,rb`；M3 在落地前**暂用**多条兜底（D4）。

### C16

- **R1（否决）**：仅靠 RegMask、`call` 不显式 `Defs`（TCH 式）。理由：`DL-070a` 证明会在 `-O1+` verifier 失败；TCH 的 CSR 不全还会误 clobber RB callee-saved。
- **R2（否决）**：`ret` 加 `Defs=[rd31,rb31]`。理由：返回值定义在更早的链上，0628 判定不需。

## Consequences（影响，汇总）

### C1 / C2

- `DADAOISelLowering` 需 `addRegisterClass(i64, GPRD)` 并按类型/bank 为指针参数/返回建立 GPRB 虚拟寄存器（`LLVM-034t`）；指针 bank 由 CC/ISel 保证，以 IR 类型（`ArgFlags.isPointer()`）与 `CCIfPtr` 判定，而非独立 MVT。
- `copyPhysReg` 须实现同 bank（`rd2rd`/`rb2rb`）与跨 bank（`rd2rb`/`rb2rd`）搬运。
- 若约束遗漏，指针可能落 RD——须由测试显式覆盖（`LLVM-039t` 参数就位验收）。

### C4

- `SPEC-097t` 把该口径投影进 `contract-abi.md §4` + `contracts/abi.yaml`（ABI 内容）；建议补一句 spec 澄清句（消除 §栈溢出规则 字面拉扯；本 ADR 不改 `spec/`）。
- `LLVM-039t` 的 LowerCall/LowerFormalArguments 按全局声明序布置/读取溢出槽。

### C5

- `SPEC-097t` 在 `contract-abi.md §4` 给出窄返回扩展 M3 口径（callee 扩展 / caller 不截断）并更新 §6 `[OPEN] #2`。
- `LLVM-039t` 在 `ret` 前按该规则扩展窄返回值；`LowerCallResult` 直接取 `rb31`（指针）。

### C7

- `LLVM-038t` 实现条件式 `hasFPImpl`、`getFrameRegister`、`emitPrologue`/`emitEpilogue`、`eliminateFrameIndex`、大帧方案2。
- `SPEC-097t` 在 `contract-abi.md §4` 给出帧指针策略 M3 口径并更新 §6 `[OPEN] #5`；`rb2` 始终 reserved 的 ABI 事实以 `contract-abi.md`/`abi.yaml` 为准。
- `LLVM-033t` 的 RA/RF 保留配置按 D6 双保险落实。

### C9

- `LLVM-033t` 把 `llvm/lib/TargetParser/TargetDataLayout.cpp` 的 `case Triple::dadao` 改为 D1 串（在现值基础上将 `n32:64` → `n8:16:32:64`）。
- `SPEC-097t` 在合约中登记 DataLayout 串与「`call` 时 SP 8B 对齐」的关系（栈对齐 spec 只要求 8B）。
- **M4 引入 clang 时须核对 clang 侧 AST 布局一致**。

### C11

- `LLVM-033t` 用 `SelectionDAGISelLegacy` + `createDADAOISelDag` 接线（`DADAOPassConfig::addInstSelector`）。
- 后续若加 GISel，可在不推翻 SelectionDAG 的前提下扩展（D2 的预留空间）。

### C13

- `LLVM-036t` 实现窄 load/store pattern 并显式覆盖大端字节偏移；`mayLoad`/`mayStore` 标注（现 0 处）。
- `TESTCASES-026t`/`INTEG-012t` 加入大端窄访存用例（显式核对字节偏移/扩展）。
- 窄算术回绕由对应符号后缀窄指令承担（`LLVM-035t`/`LLVM-037t` 引用）。

### C14

- `LLVM-035t`（指针常量材料化 `set.zw-rb`/`or.w-rb`）、`LLVM-036t`（GPRB base+offset）、`LLVM-037t`（`cmp.uo-rb` 指针比较）按 D1–D2 实现。
- `ISS-129` 需同步 `spec/SimRISC-05`/`SimRISC-00` 同类表述（**不在本 ADR 范围，另走 spec 任务**）。
- `ISS-130` 的 `sub rd,rb,rb` 走 spec 变更 + MC/QEMU/ISel + 独立 ADR；M3 用到 `ptr−ptr` 前落地。

### C16

- `LLVM-039t` 实现 `getCallPreservedMask`（含 rb32–63）、`LowerCall` 附 RegMask、`call` 指令属性（`isCall=1` + `Defs`）、bank 路由存取；`ret` 视为 terminator/barrier 但不加 `Defs`。
- `SPEC-097t` 提供 CSR = `rd32–63 ∪ rb32–63`、SP ∉ CSR 的合约内容（ABI 输入）。
- 验收须复现 `DL-070a` 场景（`-O1`/`-O2` verifier）与 `ML-004c` 场景（调用前后 GPRB 地址）。

## 指向的规范章节（汇总）

- **C1/C2**：`spec/DADAO-21 §寄存器规范`、`§传参 §参数寄存器`、`§数据表示`、`§标量参数`；`spec/SimRISC-00 §基址寄存器`；合约 `.tao/knowledge/contract-abi.md §1`/`§4`、`.tao/knowledge/contract-isa.md §7`。
- **C4**：`spec/DADAO-21 §传参 §栈溢出规则`、`§传参 §标量参数`；合约 `.tao/knowledge/contract-abi.md §4`。
- **C5**：`spec/DADAO-21 §返回值 §标量类型返回值`、`§返回值 §多返回值`（M4）；合约 `.tao/knowledge/contract-abi.md §4`、`§6 [OPEN] #2`。
- **C7**：`spec/DADAO-21 §函数调用规范 §The Stack Frame`、`§寄存器规范 §RB寄存器`；合约 `.tao/knowledge/contract-abi.md §2.1`/`§4`、`§6 [OPEN] #5`。
- **C9**：`spec/DADAO-21 §数据表示`、`§传参 §栈溢出规则`；实现落点 `llvm/lib/TargetParser/TargetDataLayout.cpp`（`case Triple::dadao`）。
- **C11**：无对应 spec 章节（纯实现机制）；实现落点 `DADAOTargetMachine`/`DADAOPassConfig`/`DADAOISelDAGToDAG`。
- **C13**：`.tao/knowledge/contract-isa.md §3`/`§10`–`§12`；`spec/DADAO-21 §数据表示`（大端）；溯源教训 0628 `DL-068a`。
- **C14**：`.tao/knowledge/contract-isa.md §7`；`spec/SimRISC-05 §比较`、`spec/SimRISC-00 §基址寄存器`；台账 `ISS-129`/`ISS-130`。
- **C16**：`.tao/knowledge/contract-abi.md §1.5`/`§1.6`/`§4`；`spec/DADAO-21 §寄存器规范`、`§函数调用规范`；溯源教训 0628 `DL-070a`、`ML-004c`。

## 状态说明

- 2026-10-04：C1/C2/C4/C5/C7/C9/C11/C13/C14/C16 的 32 条 decision 经用户逐一审核**无变化、直接通过**；本 ADR 由原 10 条草案合并为单文件，置 **`Accepted`**。
- C17（无标志位 compare-branch）按用户裁定**只落任务书约束**（`LLVM-037t`），不立 ADR；C6（CSR）归 ABI（`SPEC-097t`）。
- 后续如需变更任一 decision，按 `spec/Process-03-ADR编写规范.md`（新增 ADR / 标注 `Superseded` / 经授权的就地修订），并仍须逐条经用户确认。
