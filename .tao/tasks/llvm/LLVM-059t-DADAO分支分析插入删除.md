# LLVM-059t: DADAO target 分支分析/插入/删除（`analyzeBranch` / `insertBranch` / `removeBranch`）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-050t`~`LLVM-058t`（M4 llvm 前序：ELF/reloc、伪指令、`.dd`、选项、越界诊断、全局数据/`ABS48`、LLD target/`dadao.lds`、页大小默认；本任务在其上补 CFG 分支能力）。**本任务先于 `INTEG-016t`**（`INTEG-016t` 的 `make test-elf` 含 loop + eq guard 的多 TU/多段用例，需本任务解除崩溃）。
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源（`ISS-158`）

- `DADAOInstrInfo`（`.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.{h,cpp}`）当前只 override 了 `copyPhysReg` / `expandPostRAPseudo` / `storeRegToStackSlot` / `loadRegFromStackSlot`（`DADAOInstrInfo.h:42-72`，`DADAOInstrInfo.cpp:53-290`）。
- 分支相关 override **全部缺失**，落到基类默认（`llvm/include/llvm/CodeGen/TargetInstrInfo.h`）：
  - `analyzeBranch` 默认 `return true`（语义 = **不能理解**，`:739-744`）；
  - `removeBranch` 默认 `llvm_unreachable("Target didn't implement TargetInstrInfo::removeBranch!")`（`:792-795`）；
  - `insertBranch` 默认 `llvm_unreachable("Target didn't implement TargetInstrInfo::insertBranch!")`（`:810-816`）；
  - `getBranchDestBlock` 默认 `llvm_unreachable`（`:696-698`）。
- **触发路径（已实测）**：循环体含**跨 TU 调用** + **后置等值守卫**（`cond → done → {br.eq/ne} → ret`）时，Control Flow Optimizer（`branch-folder`）在 `TargetInstrInfo::ReplaceTailWithBranchTo`（`llvm/lib/CodeGen/TargetInstrInfo.cpp:166-190`，其中 `:188` 调 `insertBranch`）→ 未实现 → `SIGABRT(134)`。
- **影响**：`INTEG-016t`（M4 门槛 `make test-elf`）等需 CFG 改写（loop + eq guard 组合）的用例受阻。`TESTCASES-030t` 的 `m4_section_main.ll` 已去掉后置守卫以规避（其任务书「新发现/坑 1」与 reviewer 第六节已登记）。

## 已核实的 target 事实（**禁止臆断；以下均有文件/行号或实测 MIR 依据**）

### 1. CodeGen 实际发射的分支形态（读 `.td` + `ISelLowering` + `ISelDAGToDAG` + 实测 MIR）

**无条件分支（1 种）**
- `jump_iiii`（`jump brtarget24`）：`DADAOInstrInfo.td:634-642`（`isBranch=1, isTerminator=1, isBarrier=1`）；由 `(br bb:$d) -> (jump_iiii bb:$d)` 选择（`DADAOCodeGen.td:341`）。
- 分类依据 `MCInstrDesc.h:308-328`：`isUnconditionalBranch() = isBranch() && isBarrier() && !isIndirectBranch()`。

**条件分支（10 种；`isBranch=1, isTerminator=1, isBarrier=0`）**
| 指令 | 定义 | 选择 | 备注 |
|---|---|---|---|
| `br_z_rd` | `.td:563-570` | `DADAOCodeGen.td:329` | GPRD 与 0 比较（`==`/指针 NULL 路径） |
| `br_nz_rd` | `.td:572-579` | `DADAOCodeGen.td:330` | |
| `br_n_rd` | `.td:545-552` | `DADAOCodeGen.td:331` | 有符号/无符号 `<` |
| `br_nn_rd` | `.td:554-561` | `DADAOCodeGen.td:332` | `>=` |
| `br_p_rd` | `.td:581-588` | `DADAOCodeGen.td:333` | `>` |
| `br_np_rd` | `.td:590-597` | `DADAOCodeGen.td:334` | `<=` |
| `br_z_rb` | `.td:599-606` | `DADAOISelDAGToDAG.cpp:327-342`（bank 感知） | GPRB 与 0 |
| `br_nz_rb` | `.td:608-615` | 同上 | |
| `br_eq_rd` | `.td:302-309` | `DADAOCodeGen.td:337` | 双 GPRD 等值（无 cmp） |
| `br_ne_rd` | `.td:311-318` | `DADAOCodeGen.td:338` | 双 GPRD 不等 |

- 降级来源：`DADAOISelLowering.cpp:446-522`（`LowerBR_CC`：SETEQ/NE/LT/LE/GT/GE/ULT/ULE/UGT/UGE → 上述指令；`LowerBRCOND` 把 `br (icmp)` 折回 `BR_CC`，`:422-444`）。
- 分类依据 `MCInstrDesc.h:318-319`：`isConditionalBranch() = isBranch() && !isBarrier() && !isIndirectBranch()`。

**实测 MIR 证据（`llc -march=dadao -O2 -stop-before=branch-folder -o - <prog>.ll`，Control Flow Optimizer 之前）**：
```
# m4_section_main.ll（signed loop）
bb.1.cond:  successors: %bb.2, %bb.3
    br_p_rd killed $rd8, %bb.3
    jump_iiii %bb.2
# m4_call_main.ll（eq guard）
bb.0.entry: successors: %bb.1, %bb.2
    br_ne_rd $rd31, killed $rd8, %bb.2
    jump_iiii %bb.1
# repro2.ll（loop + 跨 TU call + eq guard）
bb.3.done:
    br_nz_rd killed $rd9, %bb.5
    jump_iiii %bb.4
```
结论：CodeGen 形态 = **`br_*`（条件，fall-through）+ `jump_iiii`（无条件）**；**分支目标（MBB）恒为最后一个显式操作数**。

**明确不在范围（禁止臆断为需实现）**
- `jump_rrii`（`.td:320-325`，间接 `jump rd, rb, imm`）：**无 `isBranch`/`isTerminator`**，M3/M4 CodeGen **不发射**，仅汇编器路径；不属本任务。
- `ret`（`ret_riii`，`.td:617-630`）：`isReturn=1`，**非 branch**；`analyzeBranch` 遇 `ret` 终止块应返回「不能分析（true）」，与上游一致。

### 2. 所需方法集（最小必要集）

**必须实现（override）**
- `bool analyzeBranch(MachineBasicBlock &, MachineBasicBlock *&TBB, MachineBasicBlock *&FBB, SmallVectorImpl<MachineOperand> &Cond, bool AllowModify) const` —— 识别 `br_*` + `jump_iiii`，按基类约定填充：
  - 无分支/非分支终止子（`ret`）→ 返回 `true`（不能分析）；
  - 单无条件 → `TBB = dest`，`Cond` 空，返回 `false`；
  - 单条件（fall-through）→ `TBB = dest`，`Cond` 非空，返回 `false`；
  - 条件 + 无条件 → `TBB = cond dest`、`FBB = jump dest`、`Cond` 非空，返回 `false`；
  - `AllowModify` 时允许删除首无条件分支之后的死终止子。
- `unsigned removeBranch(MachineBasicBlock &, int *BytesRemoved) const` —— 从尾部删除 ≤2 条分支（先无条件后条件），返回删除条数；`BytesRemoved` 用 `getInstSizeInBytes`（DADAO 定长 4 B，`DADAOInstrFormats.td:48`）。
- `unsigned insertBranch(MachineBasicBlock &, MachineBasicBlock *TBB, MachineBasicBlock *FBB, ArrayRef<MachineOperand> Cond, const DebugLoc &, int *BytesAdded) const` —— `Cond` 空 ⇒ 发 1 条 `jump_iiii TBB`；`Cond` 非空 ⇒ 按 **`Cond[0]=Imm(opcode)`、`Cond[1..]=非目标显式操作数`** 重建条件分支（目标 `addMBB(TBB)`），若 `FBB` 非空再追加 1 条 `jump_iiii FBB`（顺序：条件在前、无条件在后）。

**判别/取目标辅助（为正确性必需）**
- `getBranchDestBlock(const MachineInstr &) const override` —— 返回最后一个**显式**操作数的 MBB（用 `getNumExplicitOperands()`）。
- 条件分支 opcode matcher（`switch` 覆盖上表 10 条；无条件用 `MI.getDesc().isUnconditionalBranch()`）；非支持形态一律「不能分析」，**不得**静默误判。

**`Cond` 约定（本任务自定义，analyzeBranch ↔ insertBranch 必须互为逆）**：`Cond[0] = MachineOperand::CreateImm(opcode)`，`Cond[1..] = ` 该分支除目标外的显式操作数（寄存器，保留 kill 等标志）；目标恒为最后显式操作数。

**明确不需要（写入边界，避免过度设计）**
- `reverseBranchCondition`：基类默认 `return true`（`:1680-1683`），BranchFolder 会退化为插入显式 `jump`，**功能正确**；本任务不要求。
- `isBranchOffsetInRange` / `insertIndirectBranch`：DADAO 没有 branch relaxation pass（`DADAOTargetMachine.cpp` 的 `DADAOPassConfig` 未 `addPass(BranchRelaxation)`），且间接分支不在 M4 范围；本任务不要求。
- `analyzeBranchPredicate`：基类默认 `return true`，不要求。

### 3. 参照（**只读对照，非执行依赖**）

- `RISCVInstrInfo::analyzeBranch/removeBranch/insertBranch` + `parseCondBranch` + `getBranchDestBlock`（`.work/source/llvm-project/llvm/lib/Target/RISCV/RISCVInstrInfo.cpp:1135-1144,1367-1509,1758-1764`）——**范式最接近**（`Cond[0]=opcode` 方案）。
- `PPCInstrInfo::{analyzeBranch,removeBranch,insertBranch}`（`PowerPC/PPCInstrInfo.cpp:1254,1429,1461`）——另一参照。
- `MachineVerifier` 会用 `analyzeBranch` 校验 CFG（`llvm/lib/CodeGen/MachineVerifier.cpp:795-849`），实现须与 `TBB/FBB/Cond` 语义自洽。

## 接口规范

- **输入**（v5 自身，执行依赖）：
  - `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.{h,cpp}`、`DADAOInstrInfo.td`、`DADAOCodeGen.td`、`DADAOISelLowering.cpp`、`DADAOISelDAGToDAG.cpp`、`DADAOTargetMachine.cpp`。
  - `llvm/include/llvm/CodeGen/TargetInstrInfo.h`（基类默认与语义，`:690-824`、`:1680-1683`）；`llvm/include/llvm/MC/MCInstrDesc.h:308-328`；`llvm/lib/CodeGen/TargetInstrInfo.cpp:166-190`；`llvm/lib/CodeGen/MachineVerifier.cpp:795-849`。
  - `spec/Process-01-组件补丁组织与构建编排.md`（§6.3/§6.4 导出、§8 九断言）；`spec/Process-05-里程碑TDD规范.md`（§2 L2、§5 反例门控、§6 落点 = `tests/llvm/lit/CodeGen/DADAO/`、MIR 用例）。
  - `.tao/adr/adr-0018`（C1/C2 双 bank；C17 无标志位 compare-branch 的取舍正文见 `.tao/knowledge/project_M3-codegen-choices.md`，**未立 ADR**）、`adr-0019`（REL20/REL14 对应 `br_*` 字段，**本任务不改 reloc**）。
  - 现有 CodeGen lit 套件占位 `tests/llvm/lit/CodeGen/DADAO/{README.md,lit.cfg.py}`（当前**未接入** `make check-lit`，`suffixes=[".ll"]`、无工具替换——`ISS-152`）；向量落点依 `spec/Process-05 §6`。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  1. `DADAOInstrInfo.h`：新增 `analyzeBranch` / `removeBranch` / `insertBranch` / `getBranchDestBlock` 的声明 + 私有 matcher 声明。
  2. `DADAOInstrInfo.cpp`：上述实现（含 `#include` 需要的头，如 `MachineInstrBundle`/`MachineBasicBlock` 等，按编译需要）。
  3. **lit/MIR 向量（新增，暂不接门控）**：`tests/llvm/lit/CodeGen/DADAO/` 下 ≥1 个 `.mir`（或 `.ll` FileCheck）用例，覆盖**分支插入**（`insertBranch`：cond+jump 两路 / 无条件）与**分支删除**（`removeBranch`）；用例须能**失败**（`NOT`/`missing`-式负例，见验收 3）。
     - **门控策略（主会话裁定，用户已确认）**：本任务**不接** `check-lit`——**不改 `Makefile`**、**不改** `tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`；用例文件头加 lit `UNSUPPORTED:` 标记（与 `TESTCASES-029t` 的「暂不接门控」做法一致）。
     - 「`tests/llvm/lit/CodeGen/DADAO` suite 接入 `check-lit` + 去 `UNSUPPORTED:`」整体留给 **`INTEG-016t`** 一并收口（顺带解 `ISS-152`）。
     - 本任务对向量的验证手段 = **一键证据脚本直接调 `llc`/`FileCheck` 跑这些文件**（见验收 3、6），**不**依赖 `check-lit` 发现它们。
  4. 重建 `llc`（`make build-mc` 或 `ninja -j8 -C .work/build/llvm llc`；**开始前申报重建，预计 5–20 min**）。
  5. 重导出补丁 + `series`（`Process-01`：`git -C .work/source/llvm-project commit --amend` 收敛 base+1 → `tools/infra/make_patch.py llvm-project` → `make check-patch-tree`）；`components/llvm-project/changelog.md` 加一条 `LLVM-059t`。
  6. 一键证据脚本 `.work/evidence/LLVM-059t/`（含 `run.sh` + `inputs/*.ll`）；复现用例/链路真实输出留 `.work/log/llvm/`。
- **约束**：
  - **中性/边界（用户要求）**：只补 DADAO target 的**分支分析/插入/删除**能力；**不改** reloc/ABI/`defaultMaxPageSize`/`dadao.lds`/段布局；**不改**其它 target；未支持的形态（间接分支、`ret` 等）**返回「不能分析」**，**不得静默错降级**。
  - **不改** `tests/llvm/codegen/m4/**`（TESTCASES 模块）、`contracts/**`、`spec/**`；**不**在本任务恢复 `m4_section_main.ll` 的守卫（属 TESTCASES 范围，见「遗留问题」）。
  - **暂不接门控（主会话裁定，用户已确认）**：**不改 `Makefile`**、**不改** `tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`；新增用例标 `UNSUPPORTED:`；suite 接入 `check-lit` + 去标记留给 `INTEG-016t`（解 `ISS-152`）。
  - **补丁纪律（`spec/Process-01`）**：**不手改** `components/llvm-project/patches/**`；只改 `.work/source/llvm-project`；`series` 路径不变（仍 57 项，`DADAOInstrInfo.{cpp,h}.patch` 已存在）；导出前 E1（worktree 干净 + HEAD = base+1）、导出后 `make check-patch-tree`（9 断言）须过。
  - 构建受 `JOBS`（默认 8）限制；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-059t/`；**不提交 git**；复杂命令完整输出留存 `.work/log/llvm/`。

### 参考复现基线（TDD，**先立**）

**复现 IR（main TU；与 `TESTCASES-030t` 的 `m4_section_main.ll` 同构，仅恢复后置等值守卫）**：
```llvm
@rw_acc  = external global i64, align 8
@bss_cnt = external global i64, align 8

declare i64 @get_ro(i64)

define i64 @main() noinline {
entry:
  br label %cond

cond:
  %i = load i64, i64* @bss_cnt, align 8
  %c = icmp slt i64 %i, 4
  br i1 %c, label %body, label %done

body:
  %v = call i64 @get_ro(i64 %i)
  %a = load i64, i64* @rw_acc, align 8
  %s = add i64 %a, %v
  store i64 %s, i64* @rw_acc, align 8
  %i1 = add i64 %i, 1
  store i64 %i1, i64* @bss_cnt, align 8
  br label %cond

done:
  %sum = load i64, i64* @rw_acc, align 8
  %is26 = icmp eq i64 %sum, 26
  br i1 %is26, label %ok, label %fail

ok:
  %r = add i64 %sum, 4
  ret i64 %r

fail:
  ret i64 1
}
```
**lib TU（复用 `tests/llvm/codegen/m4/m4_section_data.ll` 内容，拷到 `/tmp` 作为输入）**：
```llvm
@ro_tbl  = constant [4 x i64] [i64 3, i64 5, i64 7, i64 9], align 8
@rw_acc  = global i64 2, align 8
@bss_cnt = global i64 0, align 8

define i64 @get_ro(i64 %i) noinline {
entry:
  %p = getelementptr [4 x i64], [4 x i64]* @ro_tbl, i64 0, i64 %i
  %v = load i64, i64* %p, align 8
  ret i64 %v
}
```
**当前基线（已实测，改前必须复现）**：
```bash
LLC=.work/build/llvm/bin/llc
$LLC -march=dadao -O2 -filetype=obj /tmp/opencode/LLVM-059t/main.ll -o /tmp/opencode/LLVM-059t/main.o > log 2>&1; echo "EXIT=$?"
# → EXIT=134（SIGABRT / core dumped）
# stderr 首行：Target didn't implement TargetInstrInfo::insertBranch!
#             UNREACHABLE executed at .../llvm/include/llvm/CodeGen/TargetInstrInfo.h:815!
#             Running pass 'Control Flow Optimizer' on function '@main'
```
（等价触发：`TESTCASES-030t` 的 `min_insertbranch_crash2.ll`；实测 `-O2` 与 `-mtriple=dadao-unknown-elf` 亦可复现。）

**改后期望（TDD 目标）**：同命令 `EXIT=0`、stderr 无 `insertBranch`/`UNREACHABLE`；随后执行级链路（见验收 2）跑到 guest 退出码 **30**。

**期望值独立推导（不从 `llc`/QEMU 反推）**：`acc = rw_acc(初值 2) + ro_tbl[0..3](3+5+7+9) = 26`；`icmp eq 26,26` 真 ⇒ `%ok: 26+4 = 30`（∈ 退出码区间 `0x00–0x7F`，`ADR-0004 D3`）。**守卫取假变体**：把 `icmp eq i64 %sum, 26` 改为 `... , 99` ⇒ 走 `fail` ⇒ 退出码 **1**。

### 硬约束清单（下发/执行必带）

1. **只动任务书范围**：`DADAOInstrInfo.{h,cpp}` + 新增 `tests/llvm/lit/CodeGen/DADAO/**`（**标 `UNSUPPORTED:`**）+ 补丁/`changelog`/证据；**不改 `Makefile`、不改 `lit.cfg.py`**；越界须披露。
2. **不提交 git**（主仓库与组件源树均不提交；组件源树仅按 `Process-01` `commit --amend` 收敛 base+1）。
3. **完成区与真实输出逐条对齐**：命令一律 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，**禁** `cmd | tee log; echo $?`（管道后 `$?` 是 `tee` 的，恒 0；需同时看终端与落盘时用 `cmd > log 2>&1; rc=$?; cat log; echo "EXIT=$rc"` 或 `${PIPESTATUS[0]}`）。
4. **失败即停、禁自动重试**（含换参数/换等价命令/改码后重跑）；保留失败现场并报用户。
5. **临时目录** `/tmp/opencode/LLVM-059t/`（证据输入可放 `.work/evidence/LLVM-059t/inputs/`）；不得污染仓库。
6. **补丁导出纪律**（`Process-01`）：见上约束；`make_patch.py` 输出写 `/tmp`，非空 blob，`make check-patch-tree` 过。
7. **一键证据脚本** `.work/evidence/LLVM-059t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入→预期 FAIL→还原（含重建）→回绿**（见验收 6）；结尾**不得用 `tee` 吞退出码**。
8. **重建成本申报**：每次重建前在回复写「重建 `llc`，预计 N 分钟」；多例注入合并到一轮重建，不零散重跑。

## 验收标准

> 每条须**真实输出 + 退出码**；详细日志落 `.work/log/llvm/`；证据脚本 `.work/evidence/LLVM-059t/`。

1. **复现基线 → 修复（TDD）**：改前先复现 `llc` **EXIT=134** + `Target didn't implement TargetInstrInfo::insertBranch!`；改后同命令（main + lib 两个 TU）**EXIT=0**、stderr 无 `insertBranch`/`UNREACHABLE`（贴真实输出与退出码）。
2. **执行级验证（`llc → ld.lld → qemu`）**：逐 TU `llc -march=dadao -filetype=obj` EXIT=0；`llvm-mc --triple=dadao -filetype=obj tests/scripts/codegen_crt0.s` EXIT=0；`ld.lld -T tests/scripts/dadao.lds crt0.o <data.o> <main.o>` EXIT=0；`timeout 30 qemu-system-dadao -M dadao-m1 -kernel prog.elf -display none -nographic` ⇒ **guest 退出码 = 30**（守卫取真）。**守卫取假变体**（`icmp eq …, 99`）⇒ **guest 退出码 = 1**（证双向）。附「无守卫」对照 ⇒ 30。日志落 `.work/log/llvm/`。
3. **lit/MIR 向量（新增，暂不接门控）**：`tests/llvm/lit/CodeGen/DADAO/` 下新增用例，覆盖 (a) **分支插入**（`insertBranch`：无条件 / cond+jump 两路）与 (b) **分支删除**（`removeBranch`）；用例经 `llc`（必要时 `-run-pass`/`-start-before`）驱动 + `FileCheck`。**验收只要求**：① 用例文件存在；② 文件头含 `UNSUPPORTED:` 标记；③ **`Makefile` 与 `lit.cfg.py` 未被改**（`git status`/`git diff` 证）；**不**要求 `check-lit` 发现它们。向量**可失败性**由**一键证据脚本**直接调 `llc`/`FileCheck` 证明（至少 1 条 `missing`/`NOT` 式负例：注入错误 opcode 或错误期望 ⇒ 非零），证据脚本须留真实输出。
4. **不回归**：`make test-codegen`（15/15）EXIT=0；`make check-lit` EXIT=0（新套件**未接入**，既有 MC/E2E 用例不受影响）；`make check` EXIT=0；`make check-patch-tree` EXIT=0（`series` 仍 57 项、9 断言全过）。
5. **`-verify-machineinstrs`**：复现用例与 lit/MIR 用例均加 `-verify-machineinstrs` 跑 **EXIT=0**（MachineVerifier 经 `analyzeBranch` 校验 CFG 与 `TBB/FBB/Cond` 一致，`MachineVerifier.cpp:795-849`）。
6. **一键证据脚本**：`.work/evidence/LLVM-059t/run.sh` 正常模式**全绿 / EXIT=0**；`--inject` 模式**内置注入→FAIL→还原（含重建）→回绿**，至少覆盖：
   - (a) **源码级注入（一次重建批量做）**：把 `insertBranch`（或 `analyzeBranch`）退回 `llvm_unreachable` ⇒ 重建 `llc` ⇒ 复现用例 `llc` FAIL（134）；还原源码 + **重建** ⇒ 回绿。
   - (b) **脚本级/期望值注入（不改编译输入，优先）**：把 lit/MIR 用例的期望分支序列改错（或期望退出码改错）⇒ 检查 FAIL；还原 ⇒ 回绿。
   - 注入有效性：注入后 `git -C .work/source/llvm-project diff --name-only`（或测试文件）**非空**；还原后工作区干净、`git diff` 空。
7. **补丁与台账**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.{cpp,h}.patch` 已更新为含新实现的版本（**非空 hunk**）；`series` 含二者不变（57 项）；`components/llvm-project/changelog.md` 含 `LLVM-059t` 条目（写明：补 `analyzeBranch`/`insertBranch`/`removeBranch`/`getBranchDestBlock`，解除 `ISS-158` 的 `llc` 崩溃）。
8. **中性/边界**：只改 DADAO target（+ 本任务新增的 lit 向量文件，标 `UNSUPPORTED:`）；**不改 `Makefile`/`lit.cfg.py`**；`git -C .work/source/llvm-project diff` 不触及其它 target、不触及 reloc/ABI/`defaultMaxPageSize`/`dadao.lds`；未支持形态返回「不能分析」，无静默错降级。
9. **状态**：完成后 `**状态**` 置 `待验收`；提交前经 `/complete` 收尾。

## 完成区

**测试结果**：
- 复现基线（改前）：`llc -march=dadao -O2 -filetype=obj main.ll` **EXIT=134**（SIGABRT），stderr 首行 `Target didn't implement TargetInstrInfo::insertBranch!` / `UNREACHABLE ... TargetInstrInfo.h:815` / `Running pass 'Control Flow Optimizer' on function '@main'`（`.work/log/llvm/LLVM-059t-before-llc.log`）。
- 改后同命令：main/lib 两 TU **EXIT=0**，stderr 空（无 `insertBranch`/`UNREACHABLE`）（`.work/log/llvm/LLVM-059t-after-llc.log`、`-after-lib-llc.log`）；`-verify-machineinstrs` **EXIT=0**（`-after-llc-vmi.log`）。
- 执行级（`llc → llvm-mc(crt0) → ld.lld → qemu`）：守卫取真 guest **30**；守卫取假（`icmp eq …, 99`）guest **1**；无守卫对照 guest **30**（`.work/log/llvm/LLVM-059t-qemu-{true,fail,noguard}.log`）。
- 向量：`branch-fold-insert.ll`（llc `-O2 -stop-after=branch-folder` + FileCheck）**EXIT=0**；`branch-fold-two-way.mir`（`-run-pass=branch-folder` + FileCheck）**EXIT=0**。
- 一键证据 `.work/evidence/LLVM-059t/run.sh`：正常模式 **EXIT=0（全绿）**（`.work/log/llvm/LLVM-059t-evidence-run.log`）；`--inject` 模式 **EXIT=0（全绿）**（`.work/log/llvm/LLVM-059t-evidence-inject-run.log`），含：源码注入 `insertBranch`→重建→复现用例 **EXIT=134**、还原源码+**重建**→回绿；B1/B2 期望值注入→FileCheck **FAIL**、还原→回绿。
- 不回归（真实输出 + 退出码）：
  - `make test-codegen` **EXIT=0**（15/15，`.work/log/llvm/LLVM-059t-test-codegen.log`）
  - `make check-lit` **EXIT=0**（57 discovered：50 passed / 7 unsupported，新套件未接入，`.work/log/llvm/LLVM-059t-check-lit.log`）
  - `make check` **EXIT=0**（`repository checks: PASS`，`.work/log/llvm/LLVM-059t-check.log`）
  - `make check-patch-tree` **EXIT=0**（`2 component(s), 89 patches OK`，`.work/log/llvm/LLVM-059t-check-patch-tree.log`）
  - `make check-no-residue` **EXIT=0**（`.work/log/llvm/LLVM-059t-check-no-residue.log`）
- 补丁重导出：`make_patch.py llvm-project` → `2 written, 55 unchanged`；`DADAOInstrInfo.cpp.patch` 296→**499** 行、`DADAOInstrInfo.h.patch` 83→**124** 行（非空 hunk）；`series` 仍 **57**。

**修改文件**：
- `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.h`（+45：4 个 override 声明 + 私有 matcher + `getInstSizeInBytes`）
- `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.cpp`（+207：4 个实现 + matcher + `getInstSizeInBytes`）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.{cpp,h}.patch`（重导出）
- `components/llvm-project/changelog.md`（+1 条 `LLVM-059t`）
- `tests/llvm/lit/CodeGen/DADAO/branch-fold-insert.ll`（新增，`UNSUPPORTED: true`）
- `tests/llvm/lit/CodeGen/DADAO/branch-fold-two-way.mir`（新增，`UNSUPPORTED: true`）
- `.work/evidence/LLVM-059t/{run.sh, inputs/{main,lib,main_fail,main_noguard}.ll}`（证据，gitignore）

**验收结果**（逐条对 §验收）：
1. ✅ 复现 134→0（上面真实输出/退出码）。
2. ✅ 执行级 30 / 1（守卫假）/ 30（无守卫对照）。
3. ✅ 向量存在 + 头含 `UNSUPPORTED:`；`Makefile`/`lit.cfg.py` 未改（`git status` 仅新增 2 向量文件）；可失败性由证据脚本 B1/B2 期望值注入证明（`corrupt → FAIL(1) → 还原 → green(0)`）；另源码注入证明复现用例可失败（134）。
4. ✅ `test-codegen` 15/15、`check-lit`、`check`、`check-patch-tree`、`check-no-residue` 全 EXIT=0。
5. ✅ `-verify-machineinstrs`：复现用例 + 两个向量均 EXIT=0。
6. ✅ 一键证据 `run.sh`（正常 + `--inject`）均全绿 EXIT=0，注入含源码级（重建）+ 期望值级（不重建）。
7. ✅ 补丁非空 hunk；`series` 57；`changelog.md` 含 `LLVM-059t` 条目。
8. ✅ 只改 DADAO target（`git -C .work/source/llvm-project diff --name-only` 仅 `DADAOInstrInfo.{cpp,h}`）；未触 reloc/ABI/`defaultMaxPageSize`/`dadao.lds`/其它 target；未支持形态（`ret`/间接分支/未知条件分支）返回「不能分析」（`analyzeBranch` `return true`）。
9. ✅ 状态置 `待验收`。

**新发现/坑**：
1. **`getInstSizeInBytes` 基类返回 `~0U`（未实现）**：任务书要求 `removeBranch`/`insertBranch` 用它报告 `BytesRemoved`/`BytesAdded`，但 DADAO 此前**未 override**（`grep` 实测），直接调用会把 `~0U` 当作删除/新增字节数 → 静默错误。本次在 `DADAOInstrInfo.{h,cpp}`（同文件、任务书范围）补 `getInstSizeInBytes`（返回 `getDesc().getSize()`，DADAO 定长 4 B）。**建议沉淀**：其它 target（含未来新增分支能力）凡用 `BytesAdded/Removed` 须先确认 `getInstSizeInBytes` 已实现，否则先补。
2. **BranchFolder 会尽可能消除条件分支后的 `jump_iiii`**：`llc -O2 -stop-after=branch-folder` 的常规输出里，条件块几乎总被折成「无条件 fall-through」——**看不到 cond+jump 两路**。要覆盖 `insertBranch(FBB≠nullptr)` 两路形态，需用 `-run-pass=branch-folder` 驱动、且**调整块布局**使得条件分支的 taken 目标即 fall-through（`reverseBranchCondition` 未实现 → 不能反转），pass 遂保留显式 `jump`。`branch-fold-two-way.mir` 即此构造。**建议沉淀**：DADAO 无 `reverseBranchCondition` 时，两路块的保留依赖布局，测试须显式构造。
3. **MIR 测试文件的 RUN/CHECK 注释前缀必须是 `#`，不能是 `;`**：MIR 解析器把 `--- |` 之前的 `;` 行当 YAML token 解析 → `error: YAML:3:8: Unrecognized character while tokenizing`。LLVM IR（`.ll`）用 `;`，MIR（`.mir`）用 `#`。
4. **`-stop-before=branch-folder -simplify-mir` 生成的 MIR 含绝对 `source_filename`/`ModuleID` 路径**：入仓前须替换为测试自身名，避免机器相关路径。
5. `analyzeBranch` 对 `ret` 终止块：`ret_riii` 是 terminator 但非 branch（`isBranch=0`），数到 `NumTerminators==1` 后既不匹配条件也不匹配无条件分支 → `return true`（不能分析），与上游一致、无静默错降级。

**遗留问题**：
- `reverseBranchCondition` **未实现**（任务书明确不需要）：基类默认 `return true`，BranchFolder 会退化为插入显式 `jump_iiii`，**功能正确**（执行级 30/1/30 已验证）。若后续需代码质量优化可另立任务。
- `tests/llvm/lit/CodeGen/DADAO` suite **仍未接入** `make check-lit`（`lit.cfg.py` 无 `%llc`/`%FileCheck` 替换、`Makefile` 未加该目录）——按任务书留 **`INTEG-016t`** 一并收口（含解 `ISS-152`、去 `UNSUPPORTED:`）。
- `tests/llvm/codegen/m4/m4_section_main.ll` 的后置守卫**按任务书不恢复**（属 TESTCASES 范围）；本任务已用同构 IR（`/tmp` + 证据 `inputs/main.ll`）验证崩溃解除。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`DADAOInstrInfo.{h,cpp}` 新增代码逐行审查 + 证据脚本 + 向量；判决 **PASS（可标待验收）**。

**逐行审查意见**：
- `analyzeBranch`：`TBB/FBB=nullptr; Cond.clear()` 起始复位符合基类契约；`isUnpredicatedTerminator` 计数 + `FirstUncondOrIndirectBr`/`AllowModify` 删除逻辑与上游 RISCV 同构；`ret`/间接/`>2 terminator`/未支持条件分支均 `return true`（不能分析），无静默降级（对应验收 8）。
- `parseCondBranch`（file-static）：取「最后一个显式操作数」为目标、其余显式操作数为 `Cond[1..]`，与 `insertBranch` 互逆；`assert(isConditionalBranch())` 兜底。
- `removeBranch`：先删末条无条件、再删其上条件（≤2），`BytesRemoved` 经 `getInstSizeInBytes` 累加；末条非分支返回 0，不误删。
- `insertBranch`：`Cond` 空→单条 `jump_iiii`；非空→按 `Cond[0]=Imm(opcode)` 重建条件分支 + `addMBB(TBB)`，`FBB` 非空再追加 `jump_iiii`（条件在前、无条件在后）；`assert(unsupported cond)` 兜底。
- `getBranchDestBlock`：`getNumExplicitOperands()-1` 取最后显式操作数 MBB，`assert(isBranch())`。
- `getInstSizeInBytes`：返回 `getDesc().getSize()`（4 B）。
- `isSupportedCondBranchOpcode`：显式覆盖 10 条条件分支（6 条 riii-rd：`br.n/nn/z/nz/p/np_rd`；2 条 riii-rb：`br.z/nz_rb`；2 条 rrii：`br.eq/ne_rd`），default false。

**findings 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书要求 removeBranch/insertBranch 用 `getInstSizeInBytes`，但 DADAO 未 override（基类 `~0U`），直接调用即静默错值 | ✅已修 | `DADAOInstrInfo.{h,cpp}` 新增 `getInstSizeInBytes` override（`getDesc().getSize()`=4） | 证据脚本 `check-patch-tree`/`test-codegen`/`check` 全绿；`BytesRemoved/Added` 由实际删除/新增指令数计得（编译无告警） |
| F2 `insertBranch` 中 `Cond[0].getImm()`（int64_t）→ `get(unsigned)` 隐式窄化 | ❌不修 | — | 值为 opcode 枚举（<256），与上游 RISCV 同范式；编译器无警告 |
| F3 两路 `insertBranch`（FBB≠nullptr）在常规 `-O2 -stop-after=branch-folder` 输出中不可见，若不显式构造则该分支形态无测试覆盖 | ✅已修 | 新增 `branch-fold-two-way.mir`（调整块布局，`-run-pass=branch-folder` 保留 cond+jump） | `run.sh` “vector branch-fold-two-way.mir” PASS(0)；B2 注入 corrupt→FAIL(1)→还原→green(0) |
| F4 MIR 文件用 `;` 前缀注释导致解析失败 | ✅已修 | 向量 RUN/CHECK 改 `#` 前缀 | `llc -run-pass=branch-folder` 向量 EXIT=0 |
| F5 生成 MIR 含绝对 `/tmp` 路径 | ✅已修 | `source_filename`/`ModuleID` 改为测试自身名 | `grep -nE '/tmp\|/mnt'` 向量 → none |
| F6 `analyzeBranch` 未支持形态（`ret`）行为是否与验收 8 一致 | ✅核对 | — | 代码路径：`ret` 非 branch → 落 `return true`；MIR 中 `ret` 块不参与受限块分析，`-verify-machineinstrs` EXIT=0 |
| F7 `getBranchDestBlock` 对非分支调用风险 | ✅核对 | — | 调用点仅 `BranchRelaxation`（DADAO pass config 未挂）+ 本类内部；均先经 `isBranch` 判定/断言 |

**判决**：所有 finding 已 ✅已修/❌不修（附证据）；无未修 finding；任务状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-06

---

##### 一、证据脚本审核

审核 `.work/evidence/LLVM-059t/run.sh`（196 行）：

| 检查项 | 结果 |
|--------|------|
| 无 `tee` 使用 | ✅ 全部用 `> log 2>&1` + `$?` 捕获退出码 |
| `run()` 函数跟踪失败 | ✅ `FAILED=1` on mismatch，脚本末尾 `exit 1` |
| 注入 A（源码级+重建） | ✅ cp backup→inject→rebuild→test(134)→restore→rebuild→test(0) |
| 注入 B1/B2（期望值级，不重建） | ✅ corrupt CHECK→FAIL(1)→restore→green(0) |
| 还原验证 | ✅ `git -C $SRC diff --quiet` 确认干净 |
| 无恒真断言 | ✅ 每条 `run()` 有明确 expected exit code |
| FAIL 路径可达 | ✅ 注入后 FileCheck/llc 确实 FAIL |
| 结尾无 `tee` 吞退出码 | ✅ `exit 0` / `exit 1` 直接退出 |

**脚本合格，可作为验收依据。**

---

##### 二、重跑记录（真实输出/退出码）

**正常模式**：
```
==== tool availability ====
[PASS] tool llc                                                 exists
[PASS] tool llvm-mc                                             exists
[PASS] tool ld.lld                                              exists
[PASS] tool FileCheck                                           exists
[PASS] tool qemu-system-dadao                                   exists

==== 1. llc repro (LLVM-059t / ISS-158) ====
[PASS] llc main.ll (repro, -O2 -filetype=obj)                   exit=0 (want 0)
[PASS] repro stderr has no insertBranch/UNREACHABLE             exit=1 (want 1)
[PASS] llc lib.ll (-O2 -filetype=obj)                           exit=0 (want 0)
[PASS] llc main.ll (-verify-machineinstrs)                      exit=0 (want 0)

==== 2. execution level (llc -> ld.lld -> qemu) ====
[PASS] llvm-mc crt0.s -> crt0.o                                 exit=0 (want 0)
[PASS] llc main.ll (-filetype=obj)                              exit=0 (want 0)
[PASS] ld.lld link main.elf                                     exit=0 (want 0)
[PASS] llc main_fail.ll (-filetype=obj)                         exit=0 (want 0)
[PASS] ld.lld link main_fail.elf                                exit=0 (want 0)
[PASS] llc main_noguard.ll (-filetype=obj)                      exit=0 (want 0)
[PASS] ld.lld link main_noguard.elf                             exit=0 (want 0)
[PASS] qemu guest exit == 30 (guard true)                       exit=30 (want 30)
[PASS] qemu guest exit == 1 (guard false, bidirectional)        exit=1 (want 1)
[PASS] qemu guest exit == 30 (no guard, control)                exit=30 (want 30)

==== 3. lit vectors (llc + FileCheck) ====
[PASS] vector branch-fold-insert.ll                             exit=0 (want 0)
[PASS] vector branch-fold-two-way.mir                           exit=0 (want 0)

==== 4. patch gate ====
[PASS] make check-patch-tree                                    exit=0 (want 0)

LLVM-059t evidence (normal): ALL CHECKS PASSED
EXIT=0
```

**注入模式**：
```
[...正常检查同上，全部 PASS...]

==== INJECT A. source-level (rebuild): stub insertBranch -> expect 134 ====
[PASS] inject: source really changed (git diff non-empty)       exit=0 (want 0)
[PASS] rebuild llc (injected)                                   exit=0 (want 0)
[PASS] inject: repro llc FAILS (134)                            exit=134 (want 134)
[PASS] restore: git diff empty                                  exit=0 (want 0)
[PASS] rebuild llc (restored)                                   exit=0 (want 0)
[PASS] restore: repro llc green (0)                             exit=0 (want 0)

==== INJECT B. expected-value (no rebuild): corrupt CHECK -> expect FAIL ====
[PASS] B1: injected test file differs                           exit=0 (want 0)
[PASS] B1: corrupted expectation FAILS the check                exit=1 (want 1)
[PASS] B1: restored (original) goes green                       exit=0 (want 0)
[PASS] B2: injected test file differs                           exit=0 (want 0)
[PASS] B2: corrupted expectation FAILS the check                exit=1 (want 1)
[PASS] B2: restored (original) goes green                       exit=0 (want 0)

LLVM-059t evidence (inject): ALL CHECKS PASSED
EXIT=0
```

---

##### 三、独立注入（与 engineer 不同）

**注入方式**：将 `branch-fold-two-way.mir` 第 29 行 `# CHECK-NOT:     jump_iiii` 改为 `# CHECK:         jump_iiii`（改「不存在」断言为「存在」断言，测试 done 块中被 branch-folder 删除的冗余 jump）。

**注入后 FileCheck 输出**（EXIT=1，FAIL）：
```
tests/llvm/lit/CodeGen/DADAO/branch-fold-two-way.mir:29:10: error: CHECK: expected string not found in input
# CHECK: jump_iiii
         ^
<stdin>:124:10: note: scanning from here
 br_nz_rd killed $rd9, %bb.5
```
FileCheck 正确报告：`br_nz_rd` 之后无 `jump_iiii`（branch-folder 正确删除了冗余无条件分支），注入断言失败。

**还原**：`cp` 恢复原始文件，`git diff --name-only` 为空（exit=0）。
**还原后重建**：不需要重建（仅修改测试文件，不改编译输入）。
**还原后验证**：FileCheck EXIT=0（回绿）。

**注入有效性**：注入后 `git diff --name-only` 非空（`tests/llvm/lit/CodeGen/DADAO/branch-fold-two-way.mir`）；还原后干净。

---

##### 四、回归测试（独立重跑）

| 测试 | 退出码 | 结果 |
|------|--------|------|
| `make test-codegen` | EXIT=0 | 15/15 passed |
| `make check-lit` | EXIT=0 | 57 discovered: 50 passed, 7 unsupported |
| `make check` | EXIT=0 | repository checks: PASS |
| `make check-patch-tree` | EXIT=0 | 2 component(s), 89 patches OK |
| `make check-no-residue` | EXIT=0 | PASS |

---

##### 五、实现正确性逐条核验

**5.1 `analyzeBranch` ↔ `insertBranch` 互逆**

- `parseCondBranch` 构造：`Cond[0]=Imm(opcode)`、`Cond[1..]=非目标显式操作数`（循环 `i=0..NumExplicit-2`）、目标=`getOperand(NumExplicit-1).getMBB()`。
- `insertBranch` 重建：`get(Cond[0].getImm())` 作 opcode、循环 `Cond[1..]` 添加操作数、`addMBB(TBB)` 添加目标。
- 结论：✅ 互逆。

**5.2 `Cond` 约定**

- `Cond[0] = MachineOperand::CreateImm(opcode)` ✅
- `Cond[1..] = 非目标显式操作数`（保留 kill 等标志，直接 `add(Cond[i])`） ✅
- 目标恒为最后显式操作数（`getOperand(NumExplicit-1)`） ✅

**5.3 10 条条件分支逐条覆盖**

`isSupportedCondBranchOpcode` switch 覆盖：
`br_eq_rd` ✅ `br_ne_rd` ✅ `br_n_rd` ✅ `br_nn_rd` ✅ `br_z_rd` ✅ `br_nz_rd` ✅ `br_p_rd` ✅ `br_np_rd` ✅ `br_z_rb` ✅ `br_nz_rb` ✅

**5.4 无条件 `jump_iiii`**

由 `isUnconditionalBranch()` 判别（非 opcode 硬编码），覆盖所有无条件分支。 ✅

**5.5 `removeBranch` 正确删分支**

- 先检查末条：是无条件或支持的条件分支才继续
- 删末条（无条件或单独条件）
- 再检查新末条：是支持的条件分支则一并删除
- `BytesRemoved` 累加正确
- ✅

**5.6 未支持形态 / `ret` / 间接分支返回「不能分析」**

- 间接分支：`I->getDesc().isIndirectBranch()` → `return true` ✅
- pre-ISel：`I->isPreISelOpcode()` → `return true` ✅
- `>2` terminators：`return true` ✅
- 不支持的条件分支 opcode：`!isSupportedCondBranchOpcode()` → `return true` ✅
- `ret` 终止块：非 branch terminator，不匹配任何模式 → `return true` ✅
- 无静默错降级 ✅

**5.7 `getBranchDestBlock`**

返回 `MI.getOperand(MI.getNumExplicitOperands() - 1).getMBB()`，有 `assert(isBranch())` 兜底。 ✅

**5.8 `getInstSizeInBytes`（任务书外新增 override）**

- **必要性**：基类返回 `~0U`（4294967295），直接用于 `BytesRemoved`/`BytesAdded` 会静默产生错误值。**必须 override**。✅
- **正确性**：返回 `MI.getDesc().getSize()`，DADAO 定长 4 字节（`DADAOInstrFormats.td`）。✅
- **是否越界**：在同一文件 `DADAOInstrInfo.{h,cpp}` 中，属于任务书「DADAO target 分支分析/插入/删除」范围内的必要辅助。✅
- **是否需披露升级**：已在完成区「新发现/坑 1」中明确记载并建议沉淀。✅

---

##### 六、约束核验

| 约束 | 结果 |
|------|------|
| 只动 `DADAOInstrInfo.{h,cpp}` + 新增 lit 向量（标 `UNSUPPORTED:`）+ 补丁/changelog/证据 | ✅ `git -C .work/source/llvm-project diff` 干净（已 amend commit）；主仓库 untracked 仅 2 向量文件 |
| 不改 `Makefile` / `lit.cfg.py` | ✅ `git diff Makefile tests/llvm/lit/CodeGen/DADAO/lit.cfg.py` 无输出 |
| 不改其它 target / reloc/ABI/defaultMaxPageSize/dadao.lds | ✅ 仅 DADAOInstrInfo.{h,cpp} |
| 未支持形态返回「不能分析」，无静默错降级 | ✅ 见 5.6 |
| 补丁非空 hunk | ✅ cpp.patch 499 行，h.patch 124 行 |
| series 仍 57 项 | ✅ |
| changelog 含 LLVM-059t | ✅ |
| lit 向量含 `UNSUPPORTED:` | ✅ |
| 不提交 git | ✅ 组件源树 amend commit；主仓库未提交 |

---

##### 七、Engineer 7 条 finding 判定

| finding | 判定 | 说明 |
|---------|------|------|
| F1: `getInstSizeInBytes` 未 override（基类 `~0U`） | ✅ 已修，必要且正确 | 见 5.8 |
| F2: `Cond[0].getImm()` 隐式窄化 | ❌不修，合理 | opcode 枚举 <256，与 RISCV 同范式，无告警 |
| F3: 两路 `insertBranch` 常规不可见 | ✅ 已修 | `branch-fold-two-way.mir` 显式构造 |
| F4: MIR `;` 前缀解析失败 | ✅ 已修 | 改用 `#` 前缀 |
| F5: 生成 MIR 含绝对 `/tmp` 路径 | ✅ 已修 | 改为测试自身名 |
| F6: `analyzeBranch` 对 `ret` 行为 | ✅ 核对 | `ret` 非 branch → `return true`，与上游一致 |
| F7: `getBranchDestBlock` 对非分支调用风险 | ✅ 核对 | 仅 BranchRelaxation（DADAO 未挂）+ 本类 assert 内部调用 |

**遗留问题判定**：
- `reverseBranchCondition` 未实现：任务书明确不需要，基类默认 `return true`，BranchFolder 退化为插入显式 `jump_iiii`，功能正确（执行级 30/1/30 已验证）。**非阻塞**。
- lit suite 未接入 `check-lit`：按任务书留给 `INTEG-016t`。**非阻塞**。
- `m4_section_main.ll` 守卫不恢复：按任务书属 TESTCASES 范围。**非阻塞**。

---

##### 八、判决

**Accepted**

所有验收命令在 reviewer 独立重跑下全部通过（正常模式 EXIT=0、注入模式 EXIT=0）。独立注入（改 CHECK-NOT→CHECK）正确 FAIL→还原→回绿。实现正确性逐条核验通过（analyzeBranch↔insertBranch 互逆、10 条条件分支全覆盖、未支持形态 return true、getInstSizeInBytes 必要且正确）。约束全部守住。Engineer 7 条 finding 与遗留均属实、非阻塞。
