# LLVM-127t: 窄位类型合法化与 canonical 扩展（`i8`/`i16`/`i32` 全做）

**模块**：llvm
**项目里程碑**：M9（后端指令利用）
**依赖**：`LLVM-128t`（同改 `.td`，须串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定
- 2026-10-22：「**窄位指令当然要用，不然定义它做什么**」+「**全做**」（`i8`/`i16`/`i32` 三档）⇒ 推翻 2026-10-10「先只登记，暂不改」（原 `ISS-187`）。
- 同根因面：`ISS-310`（`int` 实参未按 `contract-abi §4.2` 符号扩展，现生成 `set.zw`+`or.w` 零扩展）。

### 真源（`contracts/opcodes.yaml`，实测 24 条窄位算术，全 `orrr`、`scope: m1`）
- 32 位 `op=0x41`：`add/sub/mul/div/rem.ut`（无符号）/ `.st`（有符号）
- 16 位 `op=0x42`：`.uw` / `.sw`
- 8 位 `op=0x43`：`.ub` / `.sb`
- 另有窄位比较 6 条（`cmp.sb/.sw/.st/.ub/.uw/.ut`）与窄位移 9 条（`shl.b/.t/.w`、`shr.{s,u}{b,w,t}`）

### 现场事实（2026-10-22 实测，`clang -O2`）
- `int32 a+b` → `add.uo` + `ext.so`；`int32 a*b` → `mul.uo`；`uint32 a/b` → `div.uo`；`int16/int8 a+b` → `add.uo`。
- `uint32 → uint64` 零扩展 → `set.zw` + `or.w`（未用 `ext.uo`）。
- 根因：`DADAOISelLowering.cpp` 只把 `MVT::i64` 设 legal ⇒ `i8/i16/i32` 全 promote。

## 目标

1. `i8/i16/i32` 设 legal（`addRegisterClass`），对**有窄位指令的**操作把 action 改 `Legal`：`ADD/SUB/MUL/SDIV/UDIV/SREM/UREM`、`SHL/SRL/SRA`、`SETCC`（窄比较）。
2. `.td` 补三档 pattern（有/无符号各一条），覆盖 24 条算术 + 6 条比较 + 9 条位移中所需的组合。
3. **canonical 扩展**：窄位结果落回 64 位寄存器时按类型正确扩展（`contract-abi §4.2`）；并入 `ISS-310`（`int` 实参按符号扩展，零扩展场景改用 `ext.uo`）。
4. 不改 `spec/`、`contracts/`、`scope`。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.cpp.patch,DADAOISelLowering.h.patch,DADAOInstrInfo.td.patch,DADAOCodeGen.td.patch}`、`tests/llvm/lit/**`。
- **输出**：legal 类型 + pattern + lowering 扩展逻辑；lit（每宽度正例 + `ISS-310` 复现用例 + 反例）；证据脚本。
- **约束**：不 commit/push；临时目录 `/tmp/opencode/LLVM-127t/`。

## 设计要点

### A. 只对**有指令支撑**的组合设 Legal
`AND/OR/XOR` 无 8/16/32 位变体（ISA 只有 `.o`/`.w` 部分）⇒ 保持 Promote，**不要**盲目全设 Legal（否则选不出指令、退化更差）。逐个 opcode 现场核 `contracts/opcodes.yaml`。

### B. 扩展语义（**关键**）
窄位结果在 64 位寄存器里的高半部必须是"按源类型扩展后的 canonical 值"，否则后续 64 位运算会读脏。做法二选一（完成区写明）：① 选 `*_s*`/`*_u*` 编码本身即完成扩展（`add.st` 符号扩展 / `add.ut` 零扩展）；② 显式补 `ext.so`/`ext.uo`。**优先 ①**（一条顶两条）。

### C. 与调用约定/ABI 的交互
`ISS-310` 的修法依赖本册的 canonical 规则：参数入栈/入寄存器前按 `contract-abi §4.2` 扩展；返回值同理。二者必须一致，**同一提交内**保证。

## 验收

1. `llc -O2`：`int32 a+b` → `add.st`（或 `add.ut`，按符号性）**1 条**；`int16` → `add.sw`/`add.uw`；`int8` → `add.sb`/`add.ub`；`mul32` → `mul.ut`/`mul.st`（**单目的**，不再 128 位双目的 `mul.uo`）。
2. `ISS-310` 复现：`int f(int x){ ext(x,-1,5); return x; }` ⇒ 参数按 `§4.2` 符号扩展（不再 `set.zw`+`or.w` 零扩展）。
3. 窄位比较/位移各 1 条正例。
4. 门控：`check-instrinfo`、`check-scope`（excluded 31 / fp 60 不变）、`check_qemu_trans --strict` 264/264、`check-isa-coverage`、`check_lit_gen`、`check-lit`、L1、L2。
5. **可达 FAIL ≥2**：① 把 `i32` 改回 Promote ⇒ 窄位断言红；② 去掉符号扩展 ⇒ `ISS-310` 用例红。
6. 重建：`install-host` + `build-builtins` + `build-musl-shared`。
7. **回归**：libc-test 静态档 + embench 冒烟（i32 代码生成面全变，须有代表性证据；若 >2 个代表用例 2 h 内无法定位 ⇒ **保留 WIP 先报 architect**，不得放宽断言）。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
