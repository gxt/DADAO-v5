# LLVM-068t: ABI 寄存器布局重排（后端实现）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`SPEC-128t`（册/契约先行；`SPEC-128t` 产出 `contract-abi`/`contracts/abi.yaml` 新口径）、`LLVM-062t`（整数完整调用约定；**须同步其 RegMask/caller-saved**）、`INFRA-050t`（一次构建 `DADAO;X86`）；**排 `LLVM-063t` 之前**；与 `LLVM-064t` **串行**（同改 `DADAOFrameLowering`，且 `LLVM-064t` 大帧四形态含 `ldm/stm` 批量保存）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（原话留痕，2026-10-09；`lessons §7.3`）

> 1. 「**我想把fp改为rb63**，在明确需要的时候，rb63是fp，否则，rb63可以由llvm分配；且**rb63自身就是callee saved**」。
> 2. 「想把 **rb4-rb7 作为 caller saved regs**，交给 llvm 使用，**现有的 rbgp/rbtp 改为 rb2/rb3**」。
> 3. 「**ldm/stm 会用到 32 个寄存器的情况**，应该比较罕见，而且这种情况下，**如果 rb63 正好被用作 fp，也完全可以先保存再恢复**」。
> 4. 「**同样的，rd4-rd7/rf1-rf7 也改为 caller-saved，由 llvm 分配使用**」→ 追问后定：「**可以建一个新任务，只放开 rd4-rd7，rd2 和 rd3 可以加说明：调试/测试保留**」。
> 5. 追问里程碑后定：「**放 M6，排 clang target 之前**」。**RF 实现侧放开归 `LLVM-066t`**（`rf1–rf7` 放开为 caller-saved；`rf0`=FCSR 保留）。

## 接口规范

- **输入**：
  - `SPEC-128t` 产出的 `.tao/knowledge/contract-abi.md §1.2/§1.3/§1.6`（新角色表）与 `contracts/abi.yaml`；`spec/DADAO-21 §寄存器规范` 与 `ADR-0018 C7 D6`（就地修订后）。
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAORegisterInfo.{h,cpp,td}`（现 `GPRD_Allocatable`=rd8–rd63、`GPRB_Allocatable`=rb8–rb63；`getReservedRegs` 保留 `rd1–rd7`/`rb3–rb7`/`rb2`；`getFrameRegister` 返回 `hasFP ? rb2 : rb1`）。
  - `DADAOFrameLowering.{h,cpp}`（FP 处理、callee-saved 保存/恢复）。
  - `DADAOCallingConv.td`/`DADAOISelLowering.cpp`（`call` 的 `Defs`/RegMask、caller-saved 集合；**`LLVM-062t` 可能已落含旧 caller-saved 集合/RegMask 的补丁**）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + `tests/llvm/**`）：
  1. **寄存器类**（`DADAORegisterInfo.td`）：`GPRD_Allocatable` 增 **`rd4–rd7`**、`GPRB_Allocatable` 增 **`rb4–rb7`**（各 +4）。
  2. **`getReservedRegs`**（`DADAORegisterInfo.cpp`）：保留 `rd0`/`rb0`/`rb1`、**`rb2`(GP)**、**`rb3`(TP)**、`rd1`、**`rd2–rd3`**（调试/测试保留）；**`rb63` 条件保留**（`hasFP(MF)` 为真 ⇒ `Reserved.set(rb63)`；否则不保留，可作通用 callee-saved 分配）。**删除**旧的 `rd1–rd7`/`rb3–rb7` 整段保留与恒 `rb2` 保留。
  3. **`getFrameRegister = hasFP ? RB63 : RB1`**（原 `rb2`）。
  4. **`DADAOFrameLowering`**：FP 改用 **`rb63`**（prologue 保存旧 `rb63`、epilogue 恢复；`rbfp` 语义随册）；**批量保存 callee-saved 时须排除 FP（`rb63`）**——`rb63` 为 RB 组最高编号，`ldm/stm` 的 `immu6` 连续区间**不能从 `rb63` 往上展开**，故按用户对策「**排除 FP**」或「**先保存再恢复**」处理该不变式。
  5. **`call` 的 `Defs`/RegMask / caller-saved 同步**：`getCallPreservedMask` 含 `rb32–rb63`（`rb63` 作 callee-saved 时）；caller-saved 集合含 **`rd4–rd7`/`rb4–rb7`**；**与 `LLVM-062t` 已落补丁逐条一致**（同任务内做同步检查）。
  6. **lit / CodeGen 期望更新**（`tests/llvm/**`）：受影响指令选择/寄存器分配期望值重派生（**不从实现反填**，依册/契约口径重算）。
  7. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **不改 `spec/`/`contracts/`**（`git diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；册/契约口径来自 `SPEC-128t`。
  - **RF 不在本任务**（`rf1–rf7` 放开归 `LLVM-066t`；`rf0`=FCSR 保留）；本任务不碰 `GPRF`。
  - 期望值来自 `SPEC-128t` 产出的 `contract-abi`/`contracts/abi.yaml`，**不从实现反推**（`Spec-first`）。
  - 与 Wave 2 **同改 `components/llvm-project/patches` ⇒ 串行**；与 `LLVM-064t` **串行**（同改 `FrameLowering`）。
  - **`rb63` 恒 callee-saved**（用户原话）；`hasFP` 真 ⇒ 保留为 FP；否则可分配。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-068t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-068t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`XXX_EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-068t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **caller-saved 扩大**：寄存器分配器可将 **`rd4–rd7`/`rb4–rb7`** 分配给值（给真实 IR→asm 证据，显示这几个寄存器被使用）；类定义 + `getReservedRegs` 一致。
2. **保留集**：`rd1`/`rd2–rd3` 与 `rb2`(GP)/`rb3`(TP) 保留（`getReservedRegs` 真实输出）；`rd0`/`rb0`/`rb1` 保留不变。
3. **`rb63` 条件保留**：**有 FP** 的函数中 `rb63` = FP（prologue 保存/epilogue 恢复，给反汇编）；**无 FP** 的函数中 `rb63` 可作通用 callee-saved 被分配（给真实证据）。
4. **`getFrameRegister`**：返回 `hasFP ? rb63 : rb1`（给代码/真实证据）。
5. **FP 批量保存不变式**：callee-saved 批量保存**排除 FP（`rb63`）**或「先保存再恢复」；给真实产物/反汇编 + 与 `contract-abi` 登记的不变式逐条对照。
6. **`LLVM-062t` RegMask/caller-saved 同步**：`call` 的 preserved mask 含 `rb32–rb63`、caller-saved 含 `rd4–rd7`/`rb4–rb7`；与 `LLVM-062t` 已落补丁**逐条一致**（给对照输出）。
7. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
8. **`spec/`/`contracts/` 交集为空**：`git diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
9. **一键证据脚本**：`.work/evidence/LLVM-068t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `rb63` 条件保留改回恒保留 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
10. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**预计耗时**：改补丁 ⇒ LLVM 增量重建，实测约 6 分钟（build-mc 41 目标 <4 min，install-host 2 min）；两个门控为测试运行（`make check` ~1 min、`test-codegen` ~1.5 min、`test-elf` ~1 min）。

**测试结果**：全部门控 PASS（真实 rc）：`make check` **EXIT=0**（含 `check-lit` 68/68）；`make check-patch-tree` **EXIT=0**（`2 component(s), 93 patches OK`）；`make check-lit` 含于 check（68/68）；`make test-codegen` **EXIT=0**（`Results: 19/19 passed`）；`make test-elf` **EXIT=0**（`Results: 5/5 passed`）。日志留 `.work/log/llvm/LLVM-068t-*.log`。

**修改文件**（组件补丁集，`make_patch.py llvm-project` 导出，`series` 仍 59）：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAORegisterInfo.{td,cpp}.patch`、`DADAOFrameLowering.{cpp,h}.patch`、`DADAOCallingConv.td.patch`（5 补丁）+ `components/llvm-project/changelog.md`（+1 行）。源树 `.work/source/llvm-project` 同上 5 文件（HEAD=base+1，clean）。**未动 spec//contracts/**（`git diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）。

**验收结果**（证据脚本 `.work/evidence/LLVM-068t/run.sh` 真实输出，`RUN_EXIT=0`；llc = `.work/build/llvm/bin/llc`）：
- ①caller-saved 扩大：`alloc_rd.ll` 全流水线用 **rd4/rd5/rd6 + rb4**（A1/A2 PASS）；`GPRD/GPRB_Allocatable` 各 +4。
- ②保留集：`many_ptr.ll`（高压力、无 FP）中 **rd1/rd2/rd3/rb2/rb3 从不分配**（A6 PASS）；rd0/rb0/rb1 保留不变。
- ③`rb63` 条件保留：有 FP（`-frame-pointer=all`）⇒ 反汇编含 `st.o rb63, [rb1, -8]` / `rb2rb {rb63}, {rb1}` / FP 访问 `[rb63, -16]`（A3 PASS）；无 FP（`many_ptr.ll`）⇒ `rb63` 作通用 callee-saved 被分配并 spill/reload（`add.o rb63, rb4, rd8`、`st.o rb63, [rb1, 72] ; Folded Spill`，A4 PASS）。
- ④`getFrameRegister`：有 FP→rb63（A3）、无 FP→rb1（`sp_fn` 访问 `[rb1, 0]`，A5 PASS）。
- ⑤批量保存不变式：现为 per-register spill（无 `ldm/stm` 批），FP(`rb63`) 由固定槽 `-8` 单独存/取；`DADAORegisterInfo.cpp`/`DADAOFrameLowering.cpp` 均写入「批量 CSR 保存须排除 FP(rb63)」不变式注释。
- ⑥RegMask 同步：解码构建产物 `CSR_RegMask`（A7 PASS）——`rb32..rb63`（含 `rb63`）preserved、`rd4..rd7`/`rb4..rb7` clobbered；`getCallPreservedMask`=CSR_RegMask，`call` `Defs`=rd8–15/rb8–15（`LLVM-062t` 口径）**逐处核对无改动**（已与新布局一致）。
- ⑦注入自检：`getFrameRegister` 改回 `rb2` ⇒ 重建 ⇒ A3 FAIL（`[rb63,` 消失）；`cp`+**md5 相等**还原 ⇒ 重建 ⇒ 回绿（`RUN_EXIT=0`）。
- ⑧`machineinstrs` 验证：`fp_fn`/`sp_fn`/`many_ptr` 均 `-verify-machineinstrs` rc=0。

**新发现/坑**：① `getReservedRegs` 的 `rb63` 条件保留**必须**与 `getFrameRegister` 用**同一** `hasFP(MF)`（已写注释不变式）——`hasFPImpl` 输入（var-sized/取帧址/重对齐/`-fno-omit-frame-pointer`）在 SelectionDAG `finalizeLowering` 冻结保留集前已定，故 RA 与 PEI 间稳定。②`RBFP` 是独立 `DwarfRegAlias` 寄存器（非 `rb63`）；其编码/别名已由 `rb2` 改指 `rb63`。③`GPRD/GPRB`（全 64）经寄存器集包含自动成为 `_Allocatable` 的父类，故 `getMinimalPhysRegClass` 返回 `_Allocatable` 时 `hasSubClassEq` 仍真⇒spill 路由正确（已由 rd4/rb4 spill 实证）。④**还原注入禁 `cp -p`**：保留 mtime 会使 ninja 判定 .o 新于源而**不重建**，导致注入残留（首轮踩到）；须 plain `cp`（脚本已注明）。

**遗留问题**：无。RF 放开归 `LLVM-066t`；大帧四形态 + `ldm/stm` 批量保存（须适用上述 FP 排除不变式）归 `LLVM-064t`。用户裁定原话留痕见任务书「用户裁定」区（与 `.tao/adr/adr-0018 §C7 D6` rev. 一致）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（engineer 深度 1，无嵌套子代理）。判决：**全部 finding 已修**，状态 → 待验收。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `getReservedRegs` 条件保留 `rb63` 与 `getFrameRegister` 的 `hasFP` 必须同源（否则 RA 与 PEI 对 rb63 是否 FP 分歧，静默坏帧） | ✅已修 | 两处**均** `MF.getSubtarget().getFrameLowering()->hasFP(MF)`，并在两处写不变式注释 | 同 MF 下 A3/A4 双向证据；`fp_fn`/`many_ptr` `-verify-machineinstrs` rc=0 |
| F2 `RBFP` 别名仍指 `rb2`（FP 已迁 `rb63`，语义失真） | ✅已修 | `def RBFP : DADAOReg<63,"rbfp">, DwarfRegAlias<rb63>;` | 编译通过；`many_ptr` 打印 `rb63`；`check-lit` 68/68 |
| F3 批量 CSR 保存须排除 FP（`rb63` 为 RB 最高编号，`immu6` 不能向上展开）——现无 `ldm/stm` 批，须留不变式 | ✅已修 | `getCalleeSavedRegs` + `DADAOFrameLowering.cpp` 头注释写明「批保存须排除 FP/先存后取」 | 现路径为 per-register spill（`many_ptr` 中 `st.o rb63,... ; Folded Spill` 逐条存），A4 PASS |
| F4 首轮注入自检「还原后未回绿」：`cp -p` 保留 mtime，ninja 判定 .o 新于源⇒**不重建**，注入残留 | ✅已修 | `run.sh` 还原改 **plain `cp`**（注释说明理由） | 重跑 `run.sh`：注入 FAIL → md5 还原 → 重建 → 回绿，`RUN_EXIT=0` |
| F5 `rd4–rd7`/`rb4–rb7` 加入 `_Allocatable` 后 spill 路由（`getMinimalPhysRegClass`→`_Allocatable`，`hasSubClassEq`）是否成立 | ✅已修（非改动，实证） | 无代码改动 | `many_ptr` 真出现 `st.o rd4,…`/`st.o rb4,… ; Folded Spill`（GPRD/GPRB 自动成为父类） |
| F6 是否有 lit/CodeGen 用例断言旧布局（`rb2` 作 FP / `rb5–7` 保留 / prologue 里 `rb2`） | ❌不修（无此用例） | 无 | `grep -rnE 'rb2|rb5|rb6|rb7|rbfp|frame-pointer' tests/` → 仅 `rb2rb` 通用模式与变量名；`check-lit` 68/68、`test-codegen` 19/19 不改期望全绿 |

自审补充核对：`spec/`/`contracts/` 交集为空（A8）；补丁一文件一补丁 + `series` 同步（`check-patch-tree` 93 patches OK）；计数未写死（注释去数字）；临时产物在 `/tmp/opencode/LLVM-068t/` 与 `.work/`，仓库无残留。

#### 第 1 轮 reviewer 验收

**重跑证据脚本**：`bash .work/evidence/LLVM-068t/run.sh > /tmp/opencode/LLVM-068t-review/run.log 2>&1; rc=$?` → **RUN_EXIT=0**，全部 16 检查 PASS（A1–A8 + 注入自检 8 项）。

**门控**（逐个 `make`，真实 rc）：`make check` EXIT=0（check-lit 68/68、check-patch-tree 93 patches OK、INTEG-003t 85/85 PASS）；`make check-patch-tree` EXIT=0（2 component, 93 patches）；`make test-codegen` EXIT=0（19/19）；`make test-elf` EXIT=0（5/5）。

**独立注入**（与 engineer 不同：将 `getReservedRegs` 的 `if (TFI->hasFP(MF)) rb63` 改为**恒保留 rb63**）：注入后 `git diff` 非空 → 重建 → **A4 FAIL**（`rb63 present` 失败，无 FP 时 rb63 不再被分配）→ `cp`+md5 还原（md5=d5151824056112c3ff1094252f257c32 相等）→ 重建 → 回绿（RUN_EXIT=0）。

**① rd4–rd7/rb4–rb7 真被分配**：`alloc_rd.s` 中出现 `rd4`/`rd5`/`rd6`/`rb4`（已分配位置）。✅
**② rb63 条件语义双向**：`fp_fn.s`（`-frame-pointer=all`）含 `st.o rb63,[rb1,-8]` + `rb2rb {rb63},{rb1}` + `[rb63,`（FP）；`many_ptr.s`（无 FP）含 `st.o rb63,[rb1,72] ; Folded Spill`（通用 callee-saved）且**无** `rb63,[rb1,-8]`（非 FP）。✅
**③ getFrameRegister**：源码 `TFI->hasFP(MF) ? DADAO::rb63 : DADAO::rb1`，与 `getReservedRegs` 同用 `MF.getSubtarget().getFrameLowering()->hasFP(MF)`，同源一致（INVARIANT 注释明确要求）。✅
**④ 不变式 4**：**仅注释**（`DADAORegisterInfo.cpp:48-51`、`DADAOFrameLowering.cpp:30-35`），当前无 `ldm/stm` 批保存路径（per-register spill）；注释标注为 `LLVM-064t` 待强制。**风险：未代码强制**，供 `LLVM-064t` 遵循。
**⑤ Defs/PreservedMask**：`CSR` = `(add rd32..rd63, rb32..rb63)` → `CSR_RegMask`（rb32..rb63 preserved, rd4..7/rb4..7 clobbered）；`getCallPreservedMask` 返回 `CSR_RegMask`；RetCC Defs = rd8–15/rb8–15。✅
**⑥ 补丁纪律**：5 补丁一文件一补丁（DADAORegisterInfo.{td,cpp}.patch + DADAOFrameLowering.{cpp,h}.patch + DADAOCallingConv.td.patch）+ changelog.md +1 行；`check-patch-tree` 93 patches OK；`spec/`/`contracts/` 交集空；`git status` 无 `_tmp/_orig/_rej/_preinject`。✅

**判决：Accepted** — 验收标准 1–10 全部满足，约束无违反。
