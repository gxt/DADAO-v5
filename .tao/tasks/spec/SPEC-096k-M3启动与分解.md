# SPEC-096k: M3（Basic CodeGen，纯整数）启动与分解

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 问题根源

M2（规范与接口冻结）已达成（2026-10-04，见 `milestones.md`）。当前 v5 的 DADAO LLVM target **只有 MC 层**（AsmParser / MCTargetDesc / Disassembler），CodeGen 侧只有空壳：

- `DADAOInstrInfo.td`：全部指令 `Pattern = []`（无 ISel pattern）；无 `mayLoad`/`mayStore`；无 `isCall`/`Defs`；无伪指令。
- `DADAOFrameLowering`：空存根（未覆写 `hasFPImpl`/`emitPrologue`/`emitEpilogue`）。
- `DADAORegisterInfo::eliminateFrameIndex`：`llvm_unreachable`。
- **缺**：`DADAOSubtarget`、`DADAOISelLowering`、`DADAOISelDAGToDAG`、`DADAOAsmPrinter`、`DADAOCallingConv.td`。
- `DADAOTargetMachine` 无 `createPassConfig`/`Subtarget`；`LLVMDADAOCodeGen` 虽在 `build-mc` 目标内（`Makefile:LLVM_MC_FULL_TARGETS`），但**不产出 `llc`**（`.work/build/llvm/bin/llc` 不存在），且 codegen 管线未接线。

结果：`llc` 无法把 IR 编成汇编，**没有「IR → 机器码 → 执行」的闭环**。

标量调用约定事实（参数寄存器 `rd16–rd31`/`rb16–rb31`、返回值 `rd31`/`rb31`、callee-save `rd32–rd63`/`rb32–rb63`、帧布局、prologue/epilogue）在 v5 合约 `.tao/knowledge/contract-abi.md` §4 中仍是 **`Deferred to M2`**（M2 未落地，未提取正文）——M3 的 CodeGen 依赖它们，须先补合约（`SPEC-097t`）。

## 目的

`llc` 把**标量整数/指针**函数（LLVM IR）编译为 DADAO 汇编，经 `llvm-mc` → **单 TU** `obj`/raw binary → `qemu-system-dadao` 执行结果正确。**门槛 = `make test-codegen` 绿**（≥1 算术/访存/分支/调用函数端到端）。

## 已锁定边界（用户裁定 2026-10-04）

- **M3 = 纯整数 CodeGen**：bank 只 **`GPRD`（i64 数据）+ `GPRB`（ptr 地址）**。
- **`RA` 不处理**：RegRAS 由 `call`/`ret` 自动（深度 ≤63）；codegen 侧仅 **「保留不分配」**。
- **`RF` 不处理**：整层归 **M4**，仅 **「保留不分配」**。
- **无需链接器**：单 TU 自包含（`ADR-0003 §D5`）、汇编器就地解析段内标签、**最小重定位**（分支/call/jump 的 PCRel `<<2`）+ raw binary / 最小 linker script；完整重定位（`contract-elf.md §2–§4`，`ISS-008`）→ **M4+**。
- **不做（→ M4）**：变参、聚合传参/返回、多返回值、sret、**间接调用**、**全局变量寻址**（`.data`/`.rodata`）、i128、FP/RF codegen、完整调用约定、clang targetinfo/driver。

## 对照关系

- **M68k**（`.work/source/llvm-project/llvm/lib/Target/M68k/`，**LLVM 内只读参考**）：`M68kRegisterInfo.td`（`DR32`/`AR32`/`XR32` 双类+联合类）、`M68kISelLowering.cpp`（`addRegisterClass` 按类型选类、`getPointerTy`）、`M68kCallingConv.{td,h}`（`CC_M68k_Any_AssignToReg` 指针优先地址寄存器）、`M68kInstrInfo.cpp::copyPhysReg`（跨类 MOV）、`M68kFrameLowering.cpp`（`hasFPImpl`、A6=FP）。
- **DADAO-0628**（`.cache/refs/DADAO-0628/`，**只读、不复制**）：
  - `code-agent/designs/0002-detailed-roadmap.md`（Phase 5 + CodeGen Feasibility Spike）；
  - `code-agent/tasks/DL-036a`（spike）→ `DL-037a`/`DL-037b`（构建/管线）→ `DL-040a`（ABI 一致性）→ `DL-050a`（GPRB）→ `DL-051a`（load/store）→ `DL-052a`（偏移/FrameIndex）→ `DL-053a`（栈帧）→ `DL-054a`（AsmPrinter）→ `DL-055a`（LowerCall）→ `DL-056a`/`DL-056b`（E2E/call 重定位）→ `DL-058a`（控制流）→ `DL-060a`/`DL-060b`/`DL-061a`（shift/mul/div/wyde imm）→ `DL-069a`（RB 指针 CC）/`DL-070a`（call Defs 缺 RB31）/`ML-004c`（call RegMask）；
  - `contracts/abi/spec.md`（完整 CC，§2 传参/§3 返回值/§4 帧布局/§5 prologue-epilogue）；`code-agent/knowledge/07-abi-call-convention.md`（bank ABI）。
- 两者实现/口径冲突见下 **§M68k ↔ 0628 冲突清单（待用户判决）**——**不自行选边**。

## 任务分解

| 编号 | 任务 | 模块 | 交付物 | 依赖 |
|------|------|------|--------|------|
| `INFRA-035t` | `llc` 纳入 LLVM 构建目标 | infra | `Makefile`（`build-mc` 追加 `llc` 或新增 `build-llc`）+ 构建证据 | 无 |
| `SPEC-097t` | 标量调用约定合约落地 | spec | `.tao/knowledge/contract-abi.md` §4 正文 + `contracts/abi.yaml` 扩展 | 无 |
| `SPEC-100t` | **新增指令 `sub.o_orrr_dbb`（RB−RB→RD）规范与编码**（M3 前置） | spec | `spec/SimRISC-00/05` + `contracts/opcodes.yaml`（`scope:m3`）+ `check_scope.py` + `adr-0012 D9` | `SPEC-101t`（同改 opcodes/向量，串行在前） |
| `SPEC-101t` | **RB 算术三条指令改名+改编码槽**（`add.so_orrr_rb`→`add.o_orrr_bbd`(0x30)、`sub.so_orrr_rb`→`sub.o_orrr_bbd`(0x31)、`cmp.uo_orrr_rb`→`cmp.uo_orrr_dbb`(0x32)）跨组件原子 | spec（+llvm/qemu） | `spec/` + `opcodes.yaml` + 向量/inventory + 生成器 + MC + QEMU + 探针 | 无（**本任务先于 `SPEC-100t`**） |
| `LLVM-033t` | CodeGen 骨架（`llc` build + DataLayout + 注册 ISel/FrameLowering/AsmPrinter）+ RA/RF 保留配置 | llvm | `DADAOSubtarget`/`DADAOISelLowering`/`DADAOISelDAGToDAG`/`DADAOPassConfig` + 补丁集 + MIR 证据 | `INFRA-035t` |
| `LLVM-034t` | 值类型 + 寄存器类（GPRD/GPRB）+ 跨 bank 搬运 | llvm | ISelLowering 双类注册 + `copyPhysReg` + MIR 证据 | `LLVM-033t` |
| `LLVM-043t` | **`sub.o_orrr_dbb` 的 MC**（汇编/反汇编/编码/decode）（M3 前置） | llvm | `DADAOInstrInfo.td` 定义 + AsmParser/InstPrinter + lit 往返 + 编码 oracle | `SPEC-100t` |
| `LLVM-035t` | i64 算术 / 常数（+ **`ptr−ptr` ISel**） | llvm | `.td` pattern + 常量材料化 + `sub.o` ISel + MIR 证据 | `LLVM-034t`、`LLVM-043t` |
| `LLVM-036t` | 标量 load/store | llvm | 各宽度 ld/st pattern（GPRB base + 偏移）+ MIR 证据 | `LLVM-034t` |
| `LLVM-037t` | compare / branch | llvm | cmp/br.* ISel + 基本块布局 + MIR 证据 | `LLVM-035t`、`LLVM-036t` |
| `LLVM-038t` | FrameIndex 消解 + spill/reload + prologue/epilogue | llvm | `eliminateFrameIndex` + `emitPrologue`/`emitEpilogue` + PEI MIR 证据 | `LLVM-036t` |
| `LLVM-039t` | 调用约定（FormalArgs/Return/callee-save）+ call/ret | llvm | `DADAOCallingConv.td` + LowerCall/LowerReturn + MIR/`.s` 证据 | `SPEC-097t`、`LLVM-038t` |
| `LLVM-040t` | AsmPrinter（MI→MCInst→`.s`） | llvm | `DADAOAsmPrinter` + pseudo 展开 + `.s`→`llvm-mc` obj 证据 | `LLVM-039t` |
| `LLVM-041t` | 最小重定位与产物路径 | llvm | call/branch/jump 段内符号 PCRel 修复 + obj→raw binary 路径证据 | `LLVM-040t` |
| `QEMU-040t` | **`sub.o_orrr_dbb` 的 QEMU 语义翻译（trans）**（M3 前置） | qemu | `insn.decode` pattern + `trans_sub_o_orrr_dbb` + 探针 | `SPEC-100t` |
| `TESTCASES-026t` | CodeGen 独立测试向量（+ **`ptr−ptr` 指针差**） | testcases | `tests/codegen/*.ll` + 期望值（独立 oracle）+ validator | 无 |
| `INTEG-012t` | CodeGen E2E 套件 + `make test-codegen` | integ | `tests/lit/Codegen/*.test` + `tools/integ/run_codegen_e2e.py` + `Makefile` 目标 | `LLVM-041t`、`TESTCASES-026t`、`INFRA-035t`、`QEMU-040t` |
| `SPEC-099m` | M3 spec 里程碑 | spec | `m` 文件 | `SPEC-097t`、`SPEC-100t`、`SPEC-101t` |
| `INFRA-036m` | M3 infra 里程碑 | infra | `m` 文件 | `INFRA-035t` |
| `TESTCASES-027m` | M3 testcases 里程碑 | testcases | `m` 文件 | `TESTCASES-026t` |
| `LLVM-042m` | M3 llvm 里程碑 | llvm | `m` 文件 | `LLVM-033t`~`LLVM-041t`、`LLVM-043t` |
| `INTEG-013m` | M3 integ 里程碑 | integ | `m` 文件 | `INTEG-012t`（前置 `QEMU-040t`） |

### 依赖关系与串行纪律

- **`INFRA-035t` 最先**（否则无 `llc` 可 build）。
- **LLVM 全链严格串行**：`LLVM-033t → 034t → 043t → 035t → 036t → 037t → 038t → 039t → 040t → 041t`（新增指令 MC **`LLVM-043t`** 插在 `034t` 与 `035t` 之间；`035t` 的 `ptr−ptr` ISel 依赖 `043t`）。所有 LLVM 任务同改 `components/llvm-project/patches/llvm/lib/Target/DADAO/**` 与 `.work/source/llvm-project`（共享文件），按 `AGENTS.md`「同改共享文件一律串行」**不得并行**；`LLVM-037t`/`LLVM-038t` 名义上可并行，仍按**串行**执行（同树、同构建）。
- **新增/改名指令的 M3 前置链（全串行）**：`SPEC-101t`（三条既有 RB 算术指令改名+改编码，跨组件原子）→ `SPEC-100t`（新增 `sub.o_orrr_dbb`，`scope:m3`）→ {`LLVM-043t`（新指令 MC）∥ `QEMU-040t`（新指令 trans）}；`LLVM-035t` 的 `ptr−ptr` ISel 在 `LLVM-043t` 之后；`INTEG-012t` 在 `QEMU-040t` 之后。
  - **串行理由**：`SPEC-100t`/`SPEC-101t` 共享 `contracts/opcodes.yaml` 与 `tests/vectors/**`；`SPEC-101t`/`LLVM-043t` 共享 `DADAOInstrInfo.td`；`SPEC-101t`/`QEMU-040t` 共享 `insn.decode`/`trans_*`。
  - **原子落地集**：`SPEC-100t` + `QEMU-040t` 须**同一提交/集成波**落地（`check-interface` 要求 `opcodes.yaml` 条目 ↔ QEMU `trans_*` 一一对应，单独提交 `SPEC-100t` 会红）；`SPEC-101t` **内部原子**（改名/改槽一次改完，否则 `validate_vectors`/`check_qemu_trans` 必红）。**建议落地波**：先 `SPEC-101t`（改名，内部自洽、门控绿）→ 再 `SPEC-100t`+`QEMU-040t`（新指令，原子对）→ 再 `LLVM-043t`。
  - **决策依据**：`adr-0012 D9`（`Accepted`，用户 2026-10-04 逐条确认）。
- **`SPEC-097t` 先于 `LLVM-039t`**（CC 事实是 codegen 期望值来源）。
- **`TESTCASES-026t` 先于 `INTEG-012t`**；`INTEG-012t` 须在 `INFRA-035t` 之后（同改 `Makefile`，串行）。
- **`INTEG-012t` 最后**（依赖 `LLVM-041t` 的可编译产物与 `QEMU-040t` 的 trans）。
- `k ↔ m`：本 `k` 对应项目里程碑 **M3**；各模块 `m`（`LLVM-042m`/`INFRA-036m`/`SPEC-099m`/`TESTCASES-027m`/`INTEG-013m`）在其模块任务收敛时核验，M3 项目里程碑由主会话在依赖的模块 `m` 均达成后置 `达成`。

### 分解理由

- 按 0628 已验证的 CodeGen 序列切分：骨架 → 双 bank → 算术 → 访存 → 控制流 → 栈帧 → 调用 → AsmPrinter → 重定位；每步以「真实 MIR/`.s` + 重 build + 不回归」为独立验收点。
- 契约（`SPEC-097t`）先于依赖它的调用任务，避免工程师从 `spec/DADAO-21` 之外反推期望值。
- 测试（`TESTCASES-026t` 独立 oracle）与 E2E  harness（`INTEG-012t`）分离，满足 project 的 **Independent oracle** 原则（向量不得从 LLVM/QEMU 生成）。

## M68k ↔ 0628 冲突清单（待用户判决）

> 以下每条给出「M68k 做法 / DADAO-0628 做法 / 差异 / 待用户判决」。**架构师不选边**；凡 v5 `spec/` 或已 `Accepted` ADR 已明确者，在「备注」标注（便于判决时区分「已定」与「未定」）。

| # | 主题 | M68k 做法 | DADAO-0628 做法 | 差异 / 待判决 | 备注 |
|---|------|-----------|-----------------|---------------|------|
| C1 | **ISel 寄存器模型** | `addRegisterClass(i32, XR32)`：`XR32 = DR32 ∪ AR32` 联合类，int/ptr 共用，寄存器分配器任选 bank | `addRegisterClass(i64, GPRD)` + 指针类型绑定 `GPRB`（硬双类），指针强制落 GPRB | **硬双类 vs 联合类+软偏好**；决定 v5 ISelLowering 结构与 CC 自定义量 | 未定 |
| C2 | **指针的 value type** | 指针 = `i32`（与 int 同 MVT），无独立 GPRB | 指针独立（`iPTR`/`p0`）；`CCIfPtr` + 按 bank 反查 | v5 指针用独立 GPRB 类，还是 i64 通吃？ | 未定 |
| C3 | **跨 bank 搬运指令** | 普通 `MOV`（`MOV32rr` 对 XR32 对称；跨类亦 MOV） | 跨 bank 用专用 `rd2rb`/`rb2rd`；同 bank 用 `addi r,r,0`（DL-051a） | v5 已有 `rd2rd`/`rb2rb`/`rd2rb`/`rb2rd`（orri）；同 bank 用 `addi+0` 还是 `rd2rd`/`rb2rb`？ | 未定 |
| C4 | **参数寄存器/计数** | `D0/D1`（int）、`A0/A1`（ptr），指针 A 优先，最多 4 个，其余 caller-pop 栈 | `rd16–rd31`/`rb16–rb31`，各 bank 独立计数从 16，溢出到**统一栈区**（按全局声明序） | 实现口径差异 | v5 `spec/DADAO-21 §传参` 与 0628 一致（已定） |
| C5 | **返回值寄存器** | `RetCC_M68k_C`：int→`D0/D1`；ptr→`A0`；i8→`BD0/BD1`、i16→`WD0/WD1` | int→`rd31`；ptr→`rb31`；callee 扩展窄值；i128→`rd31:rd30`（ML-038a） | 窄返回值扩展规则 | v5 spec 同 0628；v5 合约窄扩展仍 `[OPEN]` |
| C6 | **callee-saved 集合** | `CSR_STD = D2–D7, A2–A6`（A5=BP, A6=FP） | `rd32–rd63`, `rb32–rb63` | — | v5 spec 同 0628（已定） |
| C7 | **帧布局 / `hasFP` 策略** | `A6`=FP；`hasFPImpl` = `DisableFramePointerElim ∨ var-sized ∨ frame-address-taken ∨ stack-realign`；prologue 建 FP | ABI 允许可选 FP（`rb2`），但**实现走 SP-only**（`getFrameRegister`=`RB1`/SP，DL-054a） | v5 M3 默认 **SP-only** 还是 **建 FP（rb2）**？影响 `hasFPImpl`/prologue/epilogue/FrameIndex 基址 | **未定（关键）** |
| C8 | **SP/FP 物理寄存器** | SP=`A7`，FP=`A6` | SP=`rb1`，FP=`rb2` | 仅范式差异 | v5 spec 同 0628（已定） |
| C9 | **DataLayout 与栈对齐** | `E-m:e-p:32:16:32-...`（32 位指针） | `E-m:e-i64:64-n64-S64`（DL-050a 后；spike 曾 `S128`，DL-040a 暴露 `S128` vs ABI 8B 冲突后改 `S64`） | v5 现值 `E-m:e-p:64:64-i64:64-i128:128-n32:64-`**`S128`**：栈对齐 `S128`(16B) vs `S64`(8B)？`n32:64` vs `n64`？ | **未定（关键）** |
| C10 | **调用/返回机制** | `JSR`/`BSR` 写内存栈，`RTS` 弹出 | `call` 压 RegRAS（`ra63`）、`ret` 弹；无内存返回地址槽；RA 不软件保存 | 口径差异 | v5 spec 同 0628（已定） |
| C11 | **指令选择框架** | SelectionDAG + **GlobalISel**（`GISel/` 目录） | SelectionDAG（TableGen pattern + 自定义 `ISelDAGToDAG`），LLVM 22 API 适配 | v5 M3 用 SelectionDAG 还是 GlobalISel？ | **未定（建议 ADR）** |
| C12 | **常量/立即数材料化** | `MOV` 立即数 / `LEA` / constant pool | `set.zw`（16 位 wyde，多次）+ `or.w` 构造 64 位；小立即数 `add.si`（18 位） | 范式选择 | v5 无 constant pool 通路（倾向 0628） |
| C13 | **窄类型/子寄存器模型** | `DR8`/`DR16`/`DR32` 子寄存器（B/W/L） | 单一 64 位寄存器，无 subreg；窄类型提升/扩展；窄 load 需掩码（big-endian，DL-068a） | v5 无 subreg，取 0628 路径 | 倾向 0628 |
| C14 | **GPRB 指针算术语义** | 地址寄存器可算术（`ADDQ` 等） | GPRB 算术用 `add.so`/`sub.so`（rb 变体） | v5 spec：0.5.4 RB 算术全 64 位 | v5 spec 已定 |
| C15 | **RA/RF 保留 & `rb2`** | 无 RA/RF bank | RA/RF 全 reserved | SP-only 策略下 `rb2`（FP）是否仍 reserved？ | v5 现 reserved；结合 C7 |
| C16 | **call 指令 `Defs`/RegMask** | 标准 target call-clobber 机制 | `Defs=[RD31,RB31]` + `getCallPreservedMask`（ML-004c/DL-070a 返工） | v5 call 必须声明 `Defs=[rd31,rb31]` 并附 call-preserved RegMask，否则寄存器分配静默错误 | 0628 教训，需纳入 |

## M4 交接

以下顺延 **M4**（不在 M3 范围）：FP/RF codegen（bank `GPRF`/`rfa`/`rft`、FP 指令 ISel）；**完整调用约定**（变参、聚合 HPA/HFA、多返回值、sret、`ISS-005`）；**完整重定位**（`contract-elf.md §2–§4`、relocation 编号/溢出/松弛、LLD、`ISS-008`）；clang targetinfo/driver（`DADAOABIInfo`、driver）；间接调用；全局变量寻址（`.data`/`.rodata`/constant pool）；i128；`select`/`setcc` 完备化。M3 的 `GPRD`/`GPRB`/`GPRD_Allocatable`/`GPRB_Allocatable` 类定义与 `GPRF`/`GPRA`（non-allocatable）保持不变，M4 直接在其上扩展。

## 说明

- 本 `k` 只做规划，不实现；门槛核验在 `INTEG-013m`（及 M3 项目里程碑）前完成。
- **ADR 提醒**：C1（硬双类 vs 联合类）、C7（FP 策略）、C9（栈对齐）、C11（SD vs GISel）涉及**外部契约/多方案取舍**，按 `spec/Process-03-ADR编写规范.md` 与 `AGENTS.md`「ADR decision 逐条确认」，**须由用户判定是否立 ADR**；架构师不擅自决定。建议至少对 C11（指令选择框架）与 C1/C7（bank 落地口径）立 ADR。
- 任务书自包含：执行所需事实写入各任务书或引用 v5 自身知识（`.tao/knowledge/contract-*.md`、`contracts/*`）；M68k/0628 仅作**只读对照**，不作执行依赖（内容溯源，非执行必需）。
- 假设：M3 期间不改 `spec/` 规范正文（仅 `SPEC-097t` 投影合约）——**例外**：`SPEC-101t`（三条既有 RB 算术指令改名+改编码）与 `SPEC-100t`（新增指令 `sub.o_orrr_dbb`，`scope:m3`）需改 `spec/SimRISC-00/05` 正文；重定位不扩 `contract-elf.md §2–§4`。
- **`adr-0012 D9`**（新增指令 `sub.o_orrr_dbb`(0x33,`scope:m3`) + 三条既有 RB 算术指令改名/改编码 `add.o_orrr_bbd`(0x30)/`sub.o_orrr_bbd`(0x31)/`cmp.uo_orrr_dbb`(0x32) + id 后缀 bank 签名约定）：`Accepted`，用户 2026-10-04 逐条确认追加；落地 `SPEC-101t`→`SPEC-100t`→`{LLVM-043t,QEMU-040t}`→`LLVM-035t`。**⏳ 待确认**：D9.1 的 `ha=0x33` 对应 `value` 应为 `0x40CC0000`（原裁定写 `0x40C00000`，实为 `ha=0x30`、与 `add.o_orrr_bbd` 冲突）。
