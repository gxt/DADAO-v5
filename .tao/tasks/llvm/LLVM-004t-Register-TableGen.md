# LLVM-004t: Register TableGen

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-003t`、`SPEC-004t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-003t` 的 target 骨架、`.tao/knowledge/contract-isa.md` §1（寄存器模型）、`.tao/knowledge/contract-abi.md`（SPEC-004t，可分配集合/保留寄存器/SP/FP 角色）
- 输出：`components/llvm-project/patches/0003-dadao-register-info.patch`、更新后的 `components/llvm-project/patches/series`
- 约束：4 bank × 64 = 256 个 RegisterDef；只定义寄存器，不写指令；RF/RA 全部 non-allocatable（M1 范围外）；可分配集合精确取自 `contract-abi.md`，不自行扩展/缩减；合约引用用章节号

## 背景（完整）

### 目标

在骨架上用 LLVM TableGen 定义 DADAO 全部寄存器 bank（RD/RB/RF/RA），设置可分配集合与保留寄存器约束，使 `make build-mc` 仍 PASS，并为 `LLVM-005t`（指令格式 TableGen）提供完整寄存器类型。

### 设计理由

- 寄存器模型是 MC/CodeGen 的共同基础；M1 只定义、不接入寄存器分配（CodeGen 属 M2）。
- 以 Lanai 最简 register `.td` 风格为参考；多 bank 参考 RISCV。

### 关键概念 / 数据

**寄存器组**（`contract-isa.md` §1.1）：RD `rd0–rd63`、RB `rb0–rb63`、RF `rf0–rf63`、RA `ra0–ra63`，每组 64 个、每寄存器 64 位。

**RD bank（64）**：`rd0` 硬连接零、immutable；其余保留/可分配集合按 `contract-abi.md`。注册 `GPRD`（全部 64，MC 用途）与 `GPRD_Allocatable`（可分配子集，CodeGen 用；M1 只定义不连接 isel）。

**RB bank（64）**：`rb0` 为 PC（只读，`[63:48]=0`）；`rb1` SP、`rb2` FP、`rb3` GP、`rb4` TP 等角色按 `contract-abi.md`；注册 `GPRB` 与 `GPRB_Allocatable`。

**RF bank（64）**：`rf0` 为 FCSR（`contract-isa.md` §1.3.3）；M1 范围不含浮点，全部 non-allocatable，注册 `GPRF`。

**RA bank（64）**：`ra0` 为 MemRAS 引用计数/指针，`ra1–ra63` 为 RegRAS（`contract-isa.md` §1.3.4）；全部 non-allocatable，注册 `GPRA`。

**别名**：`RBSP = rb1`、`RBFP = rb2`（按 `contract-abi.md` 的 SP/FP 约定）。

**实现文件**：`DADAORegisterInfo.td`、`DADAORegisterInfo.{h,cpp}`（继承 TableGen 生成的 `DADAOGenRegisterInfo`，实现 `getCalleeSavedRegs`/`getReservedRegs`/`eliminateFrameIndex` 存根、`getFrameRegister`）、顶层 `DADAO.td`、`CMakeLists.txt`（`tablegen(... -gen-register-info)` + 源文件）、`DADAOMCTargetDesc.cpp`/`DADAOTargetMachine.cpp` 注册 `createDADAORegisterInfo`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-008a-llvm-reginfo.md`（完整转述：目标、RD/RB/RF/RA bank 表、文件清单、约束、验收、Architecture Review）。
- DADAO-0628：`components/llvm/patches/0003-dadao-register-info.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`contracts/isa/spec.md §1`、`contracts/abi/spec.md §1`（0.4.1，仅作结构参考）。

## 交付物

- `components/llvm-project/patches/0003-dadao-register-info.patch`：包含 `DADAORegisterInfo.td`、`DADAORegisterInfo.{h,cpp}`、`DADAO.td`、`CMakeLists.txt`、注册代码。
  - **实际交付范围（验收后补全，2026-09-18）**：还包含 `DADAOFrameLowering.{h,cpp}`（最小存根，为编译 `DADAORegisterInfo.cpp` 所必需）、对 `LLVM-003t` 文件的修复（`DADAOTargetMachine.{h,cpp}` 基类 `LLVMTargetMachine`→`CodeGenTargetMachineImpl`；`DADAOMCTargetDesc.{h,cpp}` 的 `GET_REGINFO_ENUM` 调整）。
- `components/llvm-project/patches/series`：追加 `0003-dadao-register-info.patch`。
- **`Makefile`**：`build-mc` 的 ninja 目标列表新增 `LLVMDADAOCodeGen`（修复门禁盲区，见「已知坑」）。
- 生成的 `DADAOGenRegisterInfo*.inc`（构建产物，不入 git）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **可分配集合来源**：v5 以 `.tao/knowledge/contract-abi.md`（SPEC-004t）为准，不照抄 0628 的 rd8–rd63 / rb8–rb63 表；若 v5 ABI 集合不同，以合约为准。
- **保留寄存器**：`rd0` 只读零、`rb0` 为 PC、`rf0` 为 FCSR、`ra0` 为 RAS 计数，均来自 0.5.3 `contract-isa.md §1.3`，与 0.4.1 表述可能有别。
- **RF/RA 处理**：M1 不含浮点，RF 全部 non-allocatable；RA 由 call/ret 隐式管理，全部 non-allocatable。是否定义 RF/RA 全部 64 个 def 按 256 def 约束执行。
- **补丁命名**：沿用 `0003-dadao-register-info.patch`（series 顺序 0001→0002→0003），但内容按 0.5.3 重新生成。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **`build-mc` 原不构建 CodeGen（本任务暴露的根因，2026-09-18 补记）**：`Makefile` 的 ninja 目标列表原为 `llvm-mc llvm-objdump FileCheck`，**不含 `LLVMDADAOCodeGen`** → `LLVM-003t` 起 DADAO 的 CodeGen C++（`DADAOTargetMachine.cpp`、`DADAORegisterInfo.cpp`）**从未被编译**，导致两个缺陷长期被掩盖：① `LLVMTargetMachine` 基类在 LLVM 23 已改名 `CodeGenTargetMachineImpl`（003t 遗留）；② `GET_REGINFO_*` 重复展开（004t 新代码）。本任务已把 `LLVMDADAOCodeGen` 加入 `build-mc` 门禁。**教训：验收门禁必须覆盖本任务新增的全部编译单元**（编译覆盖 ≠ 仅构建 MC 工具）。
- `make build-mc` 必须仍然 PASS：patch apply → cmake → ninja 无错。
- 4 bank × 64 = 256 个 RegisterDef（bank 口径；另有 `RBSP`/`RBFP` 两个别名 def，故 `NUM_TARGET_REGS = 259`），不多不少。
- 只定义寄存器，不引入 `DADAOInstrInfo.td`（属 `LLVM-005t`）。
- RF/RA 全部 `isAllocatable = 0`，注释说明 M1 范围 defer 原因。
- patch 03 紧接 patch 02 apply，确保 `.work/source/llvm-project` 上 01+02 已应用。
- 引用合约用章节号（§1 等），不引用行号。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-008a-llvm-reginfo.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§1）、`.tao/knowledge/contract-abi.md`（SPEC-004t 产出后）

## 验收标准

1. `components/llvm-project/patches/0003-dadao-register-info.patch` 存在并追加到 `series`
2. `make build-mc` PASS（无新增错误/警告）
3. 构建产物含 `DADAOGenRegisterInfo*.inc`（含 enums/header/MCDesc）
4. 256 个 RegisterDef；`GPRD`/`GPRD_Allocatable`/`GPRB`/`GPRB_Allocatable`/`GPRF`/`GPRA` 类均生成
5. `rd0` immutable、`rb0` 保留、RF/RA non-allocatable；可分配集合与 `contract-abi.md` 一致
6. 未引入任何指令 `.td`

## 完成区

**测试结果**：通过 10/10（验证步骤全部满足）

**修改文件**：
- `components/llvm-project/patches/0003-dadao-register-info.patch`（新增，含 B2/B1/N2 修复）
- `components/llvm-project/patches/series`（追加 0003）
- `Makefile`（`build-mc` 增加 `LLVMDADAOCodeGen` 目标 — B3）

**验收结果**：

1. **Patch 存在并追加到 series** ✅
2. **`make build-mc` PASS（含 CodeGen）** ✅
   - 干净重放 → 3 patches applied cleanly
   - `make build-mc`: `[1487/1487] Linking CXX static library lib/libLLVMDADAOCodeGen.a` + `build-mc: PASS`
   - `libLLVMDADAOCodeGen.a` 已生成（4.5 MB）
3. **构建产物含 `DADAOGenRegisterInfo*.inc`** ✅（5 个文件）
4. **256 个 RegisterDef + 6 个 RegisterClass** ✅
   - 计数口径：rd0(1) + rd1-63(63) + rb0-63(64) + rf0-63(64) + ra0-63(64) = 256
5. **rd0 immutable、rb0 保留、RF/RA non-allocatable** ✅（现已经 `LLVMDADAOCodeGen` 编译覆盖）
6. **未引入任何指令 `.td`** ✅
7. **F2 未回退** ✅（返工修复后）
   - `echo "" | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null`：
     `error: unable to create subtarget info`，exit=1，无 core dump
8. **lit 测试** ✅（1/1 PASS）
9. **git status** ✅（主仓库无 `Output/` 污染）
10. **manifest-check** ✅

**新发现/坑**：
- `MCRegisterInfo` 必须堆分配（`new`），不能用 `static`（`DenseMap`/`vector` 析构时序问题）
- LLVM 23.1.1 已删除 `LLVMTargetMachine`，改名 `CodeGenTargetMachineImpl`
- `GET_REGINFO_ENUM` 应放在 `MCTargetDesc.h`（Lanai 模式），`.cpp` 只需 `GET_REGINFO_TARGET_DESC`
- `DwarfRegAlias` 产生的是别名 enum（值 1/2），不等于实际寄存器 enum（rb1=68/rb2=69）
- `DADAOFrameLowering` 存根是 M1 骨架所需（`TargetDesc.inc` 引用完整类型）
- `build-mc` 必须包含 `LLVMDADAOCodeGen` 才能覆盖 CodeGen C++ 编译

**遗留问题**（登记，不改代码，留 LLVM-005t/M2）：
- **N1**：256 bank 计数 vs 258 RegisterDef（含 RBFP/RBSP 别名）——计数口径差异属设计正常
- **N3**：`RBSP`/`RBFP` 别名 MC 名大写，且不属于任何 RegisterClass
- **N4**：`InitDADAOMCRegisterInfo`/`DADAOGenRegisterInfo` 构造把 SP 当 RA 传入的语义疑问（LLVM 惯例如此，RA 寄存器用于 DWARF unwind）

## 审阅记录

### 第 1 轮返工（F2 core dump 回退）

**问题**：替换 `LLVM-003t` 的空 MCRegInfo stub 后，`llvm-mc --triple=dadao-unknown-elf` 从「干净报错 exit=1」退化为 `free(): invalid pointer` + core dump（exit=134）。

**根因**：`createDadaoMCRegInfo` 使用 `static MCRegisterInfo X`（静态存储期）。`MCRegisterInfo` 含 `DenseMap<MCRegister, int>` 成员（`L2SEHRegs`/`L2CVRegs`）和 `std::vector<std::vector<MCPhysReg>> RegAliasesCache`。程序退出时静态对象析构，`DenseMap`/`vector` 的 `free` 与其他 LLVM 静态对象的析构时序冲突，触发 `free(): invalid pointer`。

**证据链**：
1. 复现：`echo "" | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null` → exit=134, `free(): invalid pointer`, core dump
2. 对照：Lanai 的 `createLanaiMCRegisterInfo` 使用 `new MCRegisterInfo()`（堆分配，程序生命周期单例，不触发析构）
3. 修复：`static MCRegisterInfo X` → `MCRegisterInfo *X = new MCRegisterInfo()`（恢复堆分配）
4. 复验：同命令 → `error: unable to create subtarget info` + exit=1，无 core dump

**处置**：✅已修（`DADAOMCTargetDesc.cpp` 第 89–93 行）

**复验证据**：
```
$ echo "" | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
.work/build/llvm/bin/llvm-mc: error: unable to create subtarget info
EXIT_CODE=1
```

### 第 2 轮返工（B1/B2/B3 CodeGen 可构建 + 门禁）

**问题**：reviewer 独立核实发现三项问题：
- **B3**：`build-mc` 从不构建 `LLVMDADAOCodeGen`，`DADAORegisterInfo.cpp`/`DADAOTargetMachine.cpp` 从未被编译
- **B2**：LLVM 23.1.1 已删除 `LLVMTargetMachine`，`DADAOTargetMachine` 基类不存在
- **B1**：`DADAORegisterInfo.cpp` 重复展开 `GET_REGINFO_HEADER`/`GET_REGINFO_MC_DESC` 导致重定义
- **N2**：`getReservedRegs` 设置的是别名 enum（RBSP=2/RBFP=1），非实际寄存器（rb1=68/rb2=69）

**根因**：
- B3：`Makefile:84` 的 `ninja` 目标列表只有 `llvm-mc llvm-objdump FileCheck`，不含 CodeGen
- B2：`DADAOTargetMachine.h:20` 继承 `LLVMTargetMachine`（已不存在），应为 `CodeGenTargetMachineImpl`
- B1：`.cpp` 重复 include `GET_REGINFO_HEADER`（已由 `.h` include）和 `GET_REGINFO_MC_DESC`（已由 `DADAOMCTargetDesc.cpp` include）；`TargetDesc.inc` 引用 `DADAOFrameLowering` 完整类型但无存根
- N2：`DwarfRegAlias` 产生的别名值（1/2）与实际寄存器值（68/69）不同

**处置**：
- **B3**：`Makefile` 增加 `LLVMDADAOCodeGen` 到 `build-mc` 的 ninja 目标
- **B2**：`DADAOTargetMachine.h` 改继承 `CodeGenTargetMachineImpl`，`.cpp` 构造函数改调 `CodeGenTargetMachineImpl(...)` + `initAsmInfo()`
- **B1**：`DADAORegisterInfo.cpp` 改为 Lanai 模式（仅 `GET_REGINFO_TARGET_DESC`）；`DADAOMCTargetDesc.h` 添加 `GET_REGINFO_ENUM`；`DADAOMCTargetDesc.cpp` 去除重复的 ENUM/HEADER 块；新建 `DADAOFrameLowering.{h,cpp}` 存根
- **N2**：`getReservedRegs` 改为 `DADAO::rb1`/`DADAO::rb2`

**复验证据**：
```
$ ninja -C .work/build/llvm LLVMDADAOCodeGen 2>&1 | tail -3
ninja: no work to do.
EXIT=0

$ ls .work/build/llvm/lib/libLLVMDADAOCodeGen.a
-rw-rw-r-- 1 ubuntu ubuntu 4542074 Sep 18 00:11 .work/build/llvm/lib/libLLVMDADAOCodeGen.a

$ grep "Reserved.set" .work/source/llvm-project/llvm/lib/Target/DADAO/DADAORegisterInfo.cpp | grep rb
  Reserved.set(DADAO::rb1);
  Reserved.set(DADAO::rb2);

$ make build-mc 2>&1 | tail -3
[1487/1487] Linking CXX static library lib/libLLVMDADAOCodeGen.a
build-mc: PASS
EXIT=0

$ echo "" | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
.work/build/llvm/bin/llvm-mc: error: unable to create subtarget info
EXIT=1
```

### 第 1 轮 reviewer 验收（Needs Revision）

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Needs Revision**

**独立重跑**：6 条验收标准在 `make build-mc` 门禁下逐条通过；但 `ninja -C .work/build/llvm LLVMDADAOCodeGen` **exit=1**（该库从未被门禁构建），且完成区把未编译的 `getReservedRegs` 当已验证事实陈述。

**阻塞项**：
- **B1**：`DADAORegisterInfo.{h,cpp}` 的 `.inc` 展开方式错（`GET_REGINFO_HEADER`/`MC_DESC` 重复展开、缺 `TARGET_DESC`），且需最小 `DADAOFrameLowering` 存根。
- **B2（003t 遗留）**：LLVM 23.1.1 已删除 `LLVMTargetMachine`（改名 `CodeGenTargetMachineImpl`），`DADAOTargetMachine.h:20` 仍继承旧名 → CodeGen 自 003t 起不可构建。
- **B3（根因/门禁盲区）**：`Makefile` 的 `build-mc` 只 `ninja llvm-mc llvm-objdump FileCheck`，**不含 `LLVMDADAOCodeGen`** → 004t 新增 C++ 从未被编译，验收标准 2 的 PASS 证明不了它成立。

**非阻塞**：N1 计数口径（256 bank vs 258 RegisterDef）；N2 `getReservedRegs` 设的是别名 enum（`RBSP`/`RBFP`）而非 `rb1`/`rb2`；N3 别名 MC 名大写且不属任何 RegisterClass；N4 `InitDADAOMCRegisterInfo`/ctor 把 SP 当 RA 传入语义可疑。

### 第 3 轮返工（reviewer B1/B2/B3 + N2）

**返工者**：engineer
**时间**：2026-09-18

| 项 | 根因 | 处置 | 复验 |
|---|---|---|---|
| B3 | 门禁不含 `LLVMDADAOCodeGen` | `Makefile` 的 ninja 目标列表新增 `LLVMDADAOCodeGen` | `make build-mc` exit=0、`[715/715]` 链接 `libLLVMDADAOCodeGen.a`、三个 `.o` 均生成 |
| B2 | LLVM 23 删除 `LLVMTargetMachine` | `0003` 中改 `CodeGenTargetMachineImpl`（`#include` + 基类 + 构造 + `initAsmInfo()`） | 该 TU 编译通过 |
| B1 | `.inc` 展开重复/缺失 + 缺 FrameLowering | `.h`=`GET_REGINFO_HEADER`；`.cpp`=`GET_REGINFO_ENUM`+`GET_REGINFO_TARGET_DESC`；`DADAOMCTargetDesc.h` 加 `ENUM`、`.cpp` 去重复 `MC_DESC`；新增 `DADAOFrameLowering.{h,cpp}` 存根 | `ninja LLVMDADAOCodeGen` exit=0；`nm` 确认基类构造与成员已定义 |
| N2 | 设了别名 enum | `Reserved.set(DADAO::rb1)`/`rb2`（enum 68/69） | 源码 + enum 值核对 |
| N1/N3/N4 | — | **不改代码**，登记「遗留问题」 | 实测 `.td`/`.h` 尺寸未变，未偷改 |

**复验**：干净重放 3 patch；`make build-mc` exit=0（现含 CodeGen）；5 个 `.inc`；256 bank；6 类；合约比对 PASS；无指令 `.td`；F2 `exit=1` 无 core dump；lit PASS；无仓库污染。

### 第 2 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Accepted**（6/6）

**第 1 轮 B1/B2/B3/N2 复核**：均**真正修复**（非绕过）——B3：门禁已含 `LLVMDADAOCodeGen`，实测编译出 `DADAOTargetMachine.cpp.o`/`DADAOFrameLowering.cpp.o`/`DADAORegisterInfo.cpp.o` 并链接 `libLLVMDADAOCodeGen.a`（4,542,074 B）；B2：基类改 `CodeGenTargetMachineImpl`，该 TU 实际编译通过；B1：展开模式对齐 Lanai、`nm -C` 证明符号已定义；N2：`Reserved.set(rb1/rb2)`（enum 68/69）。

**独立重跑**：`make manifest-check` exit=0；回基线 + `make prepare`（3 patch）；`make build-mc` exit=0（`[715/715]` + `build-mc: PASS`，DADAO 源零告警）；`ninja LLVMDADAOCodeGen` exit=0；5 个 `.inc`；256 bank / 64×4；6 类；合约脚本 `RESULT: PASS`；无指令 `.td`；F2 exit=1 单行无 core dump；`llvm-mc --version` 含 dadao；lit 1/1；无污染；与 0628 `0003` 对照**未照抄**。

**残余（非阻断）**：NF1 `DADAOTargetMachine.h` 末尾缺换行；NF2 无消费者链接 CodeGen 库（编译覆盖 ≠ 链接覆盖，M2 的 `llc` 将是首个消费者）；NF3 `DADAOFrameLowering` 未覆写纯虚 `hasFPImpl`（抽象类，M1 不可达）；NF4 N1/N3/N4 已登记遗留；NF5 本次改 `Makefile` 超出原交付物声明（B3 必要最小改动）；NF6 完成区 `[1487/1487]` vs reviewer `[715/715]`（缓存差异，结论一致）。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-18
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（门禁变更被 ADR-0002「Make 统一入口/构建编排」覆盖；`LLVMTargetMachine`→`CodeGenTargetMachineImpl` 是 ADR-0006 锁定版本内的 API 适配）。

**独立核对**：6 条验收标准逐条复核通过；`libLLVMDADAOCodeGen.a` 存在；`GET_REGINFO_*` 三处展开各司其职无重复；全仓无 `LLVMTargetMachine` 遗漏；`LLVMDADAOCodeGen` 仅出现在 `Makefile:84`；`build-qemu`/`build-gem5` 未受影响；`LLVM-005t` 前置就绪；`.work/log/llvm/` 新日志约定已被遵守（38 文件）。

**新发现**：
- **F1**：**4 个**文件缺末尾换行（`DADAOFrameLowering.{h,cpp}`、`DADAORegisterInfo.cpp`、`DADAOTargetMachine.h` ← 后者是 003t 原版有、被 `0003` 去掉的**回归**）——不影响编译；登记 `deferred.md`（用户裁定 2026-09-18）。
- **F2**：`DADAOFrameLowering` 未覆写纯虚 `hasFPImpl` → 抽象类；M1 安全、**M2 会阻塞** → 登记 `deferred.md`。
- **F3/F4/F5（任务书精度）**：交付物未声明 `DADAOFrameLowering`/`Makefile`/对 003t 文件的修改；验收标准 ② 未显式要求 CodeGen 可编译；已知坑未记录「`build-mc` 原不构建 CodeGen」根因 → 已由主会话补全（交付物 + 已知坑）。

### 收尾

- `**状态**` 置 `已验证`（2026-09-18）。
- F3/F4/F5 由**主会话**补全任务书；F1/F2 登记 `deferred.md`。
- `MEMORY.md`（llvm `002t`~`004t`）、`changelog.md` 已同步。
