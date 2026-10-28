# LLVM 后端 PR 审计（3d77f7bb）：差异清单与 137–139 重放点

> **定位**：`LLVM-136t` 的审计快照（判据层）。用途：① 说明为何**不得整体 merge / cherry-pick** 该 PR；② 给出 `LLVM-137t–139t` 在**当前 master 基线**上可安全重放的位置。
> **只读复现**：
> ```
> git clone --bare https://github.com/xkw9/DADAO-v5.git /tmp/opencode/LLVM-136t/pr.git
> git -C /tmp/opencode/LLVM-136t/pr.git -c core.quotepath=false diff 3fa3631 3d77f7b
> ```

## 1. 元数据与基线判定

- PR：`https://github.com/gxt/DADAO-v5/compare/master...xkw9:DADAO-v5:pr/llvm-130-133`
- head `3d77f7bb`（2026-10-27 14:15:39 +0000，"DADAO: add verified LLVM codegen optimizations"），parent `3fa3631`；**15 文件，+1399 −454**
- fork 的 `master` = `8961d4aa`（旧快照）；PR 分支整树与本仓 master 差 **1726 文件**（历史重写痕迹，与三项优化无关）
- **关键判定**：delta 的*基线侧*对 9 个既有路径与本仓 master **逐 blob 相同**（其余 6 个是新增文件；`git hash-object <f>` == `git show 3fa3631:<f>`，9/9 SAME，**本册改动前**实测；`lit.cfg.py` 随后被本册按相反口径改过，见 §2）
  ⇒ **三项回退是该 commit 自己引入的**，不是「旧基线顺带带出」；审计只需看 delta，不必 diff 整树。
- lit 口径：本仓 `make check-lit` 现场 **154 passed**（2026-10-28，136t 完成区）；PR 报告称 151/151（其集合含 3 个新增 `.ll`，口径未复核）。

## 2. 差异清单（15 文件）

类别：**R** = 回退 master 已有功能（**禁落**）；**137/138/139** = 新功能（另册重放）；**D** = 文档（改名+改号后随 139）；**I** = 基建（PR 口径被否决）。

| 文件（相对 `components/llvm-project/` 或仓库根） | Δ | 类别 | 处置 |
|---|---|---|---|
| `patches/llvm/lib/Target/DADAO/CMakeLists.txt.patch` | +3 −2 | 139 | 新增 `DADAOPointerPHIBank.cpp` 源文件 |
| `patches/llvm/lib/Target/DADAO/DADAO.h.patch` | +4 −2 | 139 | `create*` / `initialize*` 各一行 |
| `patches/llvm/lib/Target/DADAO/DADAOCodeGen.td.patch` | +48 −6 | **R** + 138 | 只取 39 条 `Pat`（+45），**不取** tailjmp 回落 |
| `patches/llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp.patch` | +49 −28 | **R** + 137 + 138 | 取 shift hunk（137）与 extend 分支（138），**不取** ExternalSymbol 删除 |
| `patches/llvm/lib/Target/DADAO/DADAOPointerPHIBank.cpp.patch` | +199 | 139 | 新补丁文件（199 行全文） |
| `patches/llvm/lib/Target/DADAO/DADAOTargetMachine.cpp.patch` | +11 −34 | **R** + 139 | 取 `initialize` + `addPreRegAlloc`（+8），**不取** `selectCodeModel` 删除与 `CM.value_or` 改写 |
| `series` | +1 | 139 | `DADAOPointerPHIBank.cpp.patch`（字典序位置正确） |
| `docs/README.md` | +1 | D | 报告索引行，随改名后的报告 |
| `docs/llvm-130-133-后端优化工作报告.md` | +48 | D | **必须改名 `llvm-136-139-…`** 并改号（§5） |
| `tests/unit/llvm/lit/CodeGen/DADAO/lit.cfg.py` | +5 −5 | **I** | **否决**：改成 `LLVM_TOOLS_DIR` 优先；136t 以相反口径落地（安装根/site config 优先 + opt-in + identity） |
| `tests/unit/llvm/lit/CodeGen/DADAO/m10-i64-shift.ll` | +149 | 137 | 注释 `LLVM-131t` → `LLVM-137t` |
| `tests/unit/llvm/lit/CodeGen/DADAO/m10-narrow-extend.ll` | +388 | 138 | 注释 `LLVM-132t` → `LLVM-138t` |
| `tests/unit/llvm/lit/CodeGen/DADAO/m10-loop-pointer-bank.ll` | +127 | 139 | 补 `LLVM-139t` 注记 |
| `tools/llvm/llvm-isa-backend-matrix.md` | +185 −196 | I | 派生量（补丁行号位移）⇒ 重放后**现场重生成** |
| `tools/llvm/llvm-isa-backend-matrix.tsv` | +181 −181 | I | 同上 |

## 3. 三项回退（master 内容，必须保留）

判据均为**可执行 grep**（在 `components/llvm-project/patches/...` 上；PR 侧同一 grep 为 0）。

1. **代码模型校验** `selectCodeModel()`（LLVM-131t，ADR-0036 D1/D2）
   - 位置：`DADAOTargetMachine.cpp`（master patch `selectCodeModel` 命中 2 次：定义 + 构造调用）
   - PR：整块删除（−31 行），构造改 `CM.value_or(CodeModel::Small)`（−1/+1）
   - 后果：`-mcmodel=medium/kernel/tiny` 不再 `report_fatal_error`，静默当 small 用（前端/驱动绕过检查时不可见）
2. **`ISD::ExternalSymbol` 的 large 物化**（LLVM-131t）
   - 位置：`DADAOISelDAGToDAG.cpp`（`case ISD::ExternalSymbol:` 命中 1 次）
   - PR：整段删除（−21 行，含 `TM.getCodeModel() != CodeModel::Large` 门控与 `GLOBAL_ADDR` 物化）
   - 后果：large 模型下 libcall 目标退化（间接调用序列缺 48 位绝对地址物化）
3. **`tailjmp_rrii` 的 `GPRBTC`**（LLVM-131t）
   - 位置：`DADAOCodeGen.td`（`GPRBTC:$ra` 命中 1 次 + 注释 1 行）
   - PR：`InOperandList` 改回 `GPRB:$ra` 并删注释（−4/+1）
   - 后果：epilogue 在终止跳转前发射，callee-saved 基址被 restore 破坏（`GPRBTC` = 调用易失 `rb4–rb31`，见 `DADAORegisterInfo.td`）

## 4. 137–139 可安全重放的 patch 点

> 重放一律走 `.work/source/llvm-project` 源码 + `make_patch.py` 导出（`Process-01 §6.1.1`：**禁手改 patch**）。以下按 hunk 归属，互不夹带。

### 4.1 LLVM-137t（i64 常量移位立即数）

- 文件：`DADAOISelDAGToDAG.cpp`，常量移位分支（master 锚点：`const auto *Amt = dyn_cast<ConstantSDNode>(Node->getOperand(1));` 后的 `if (!Amt || (VT != MVT::i8 && VT != MVT::i16 && VT != MVT::i32))`）
- 新增：条件加 `&& VT != MVT::i64`；`IsT/IsW` 前插 `IsO = VT == MVT::i64`；三处 `Opc` 三元前置 `IsO ? DADAO::shl_o_orri / shr_uo_orri / shr_so_orri`
- 依赖：三个 `orri` 指令 def **master 已有**（`DADAOInstrInfo.td.patch`），无需新增指令
- 须核（重放时验证，不预设）：① `Sh >= W` 已挡 `>= 64`；② `Sh == 0` 是否真会进入该分支（LLVM 一般折叠为 copy）——任务 137 要求保留 copy 语义；③ 不得改动 poison 语义（仍只在常量且 `Sh < W` 时选立即数形态）
- **必不取**：同文件 `case ISD::ExternalSymbol` 的删除、`SIGN_EXTEND/ZERO_EXTEND` 新增分支（后者属 138）

### 4.2 LLVM-138t（窄整数 canonical extension 折叠）

- 两处，**同批落地**：
  - `DADAOCodeGen.td`：39 条 `def : Pat<(i64 (sext|zext (iN (add|sub|mul|udiv|urem|sdiv|srem …))))…>`（锚点：narrow `srem_sb` Pat 之后）
  - `DADAOISelDAGToDAG.cpp`：`switch (Node->getOpcode())` 首部新增 `case ISD::SIGN_EXTEND: case ISD::ZERO_EXTEND:`（窄 `sub 0, x` 在包围 extend 下仍走 `sub_s{b,w,t}` + `ext_{s,u}o_orri` 两条）
- 须核：shift 组把 amount 写成 `(i64 GPRD:$b)`，而 IR 中窄 shift 的 amount 与 value 同宽 ⇒ 须证 legalize 后成立，否则改类型或删该组（任务 138 已列为核实点）
- **必不取**：`DADAOCodeGen.td` 的 tailjmp hunk

### 4.3 LLVM-139t（循环指针 PHI 的 GPRB 保持）

- 五处 + series，缺一不可：
  1. 新补丁文件 `DADAOPointerPHIBank.cpp`（199 行全文；pass 名 `dadao-pointer-phi-bank`，测试用 `-stop-after=`）
  2. `CMakeLists.txt`：源列表 `DADAOISelLowering.cpp` 之后插 `DADAOPointerPHIBank.cpp`
  3. `DADAO.h`：`createDADAOISelDag(...)` 之后插 `createDADAOPointerPHIBankPass()`；`initializeDADAODAGToDAGISelLegacyPass(...)` 之后插 `initializeDADAOPointerPHIBankPass(...)`
  4. `DADAOTargetMachine.cpp`：`initializeDADAODAGToDAGISelLegacyPass(*PR);` 之后插 `initializeDADAOPointerPHIBankPass(*PR);`；`DADAOPassConfig` 内 `addInstSelector()` 之后、`void addIRPasses()` 之前插 `addPreRegAlloc()`
  5. `series` 一行
- **必不取**：同文件 TargetMachine hunk 的 `selectCodeModel` 整块删除与 `CM.value_or(CodeModel::Small)` 改写

## 5. 重放同批的任务号订正（PR 的错号）

- 报告 `docs/llvm-130-133-后端优化工作报告.md` → `docs/llvm-136-139-后端优化工作报告.md`；正文标题、（`docs/README.md` 索引行）、`LLVM_TOOLS_DIR` 段落需按 136t 结论重写
- `DADAOPointerPHIBank.cpp` 头注释 `prototype for LLVM-133t` → `LLVM-139t`
- `m10-i64-shift.ll` 注释 `LLVM-131t` → `LLVM-137t`；`m10-narrow-extend.ll` 注释 `LLVM-132t` → `LLVM-138t`；`m10-loop-pointer-bank.ll` 补 `LLVM-139t`
- `130–133` 号段已分别被 64 位缺省/DWARF64、代码模型、fixup 大端、cmp.u 语义占用，**不得复用**
