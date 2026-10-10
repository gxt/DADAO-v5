# LLVM-074t: 真尾调用实现（优化，可选；**非 M6 硬性**）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

> **范围变更（2026-10-10，`LLVM-070t` 收尾）**：原缺口 **G4（`ISS-178`）** 与 **G6（`ISS-180`）同根**——根因均为「后端不处理尾调用」（`LowerCall` 忽略 `CLI.IsTailCall`）；`LLVM-070t` 已修复（尾调用一律降级为非尾调用：发普通 `call`+`ret`；`musttail` ⇒ `report_fatal_error`）并**关闭 G4/G6**。
> ⇒ 本任务**不再是缺陷修复**，降级为**优化项（可选）**：**实现**真尾调用（tail-jump：复用调用者返回地址 + 拆帧），不再以「`-O2` 崩溃」为动机。**非 M6 硬性**——**可在 M6 内做，亦可推 M7**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **动机（优化）**：`LLVM-070t` 后，DADAO 后端对尾调用**一律降级为非尾调用**（发普通 `call`+`ret`）——正确但**放弃尾调用优化**（每次尾调用多一轮帧压/弹与返回）。
- **本任务目标**：**实现**真尾调用（tail-jump）——在 `-O2`（等）下把合法尾调用编译为「**复用调用者返回地址 + 拆本帧**」的跳转，减栈占用/返回开销。
- **性质 = 能力增强（优化，非缺陷）**；**不影响现状正确性**（降级路径已正确）⇒ **非 M6 硬性、可选**。
- **受益基准（参考）**：crc32 / md5sum / tarfind / ud / xgboost 等（原 G4 命中项，`-O2`）。

**证据指针（原缺口）**：`.work/log/testcases/TESTCASES-039t-stage1-gaps.md §G4`；issue `ISS-178`（**已 closed**，`resolved_by: LLVM-070t`）。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`），含 `DADAOISelLowering.cpp` 的 `LowerCall` 与调用约定（`LLVM-062t` 交付：返回 `rd8`/`rb8`/`rf8` + 变参 + 间接调用）。
  - `.tao/knowledge/contract-abi.md`（完整调用约定；尾调用须保持 ABI 语义）、`contract-isa.md`（`call`/`ret` 族）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **真尾调用 lowering（实现）**：在 `LowerCall`/`isTailCall` 路径**实现** DADAO 真尾调用（tail-jump：复用调用者返回地址 + 拆本帧），使合法尾调用在 `-O2` 下编译为**跳转**（不再是「降级为非尾调用」）；语义须正确（返回被调者返回值，保持返回寄存器约定 `rd8`）；ISA/ABI 不支持的形态（如 `musttail` 约束不满足）**优雅降级或显式失败**，不得断言崩溃。
  2. 如需改 `DADAOISelLowering.{h,cpp}`/`DADAOCallingConv.td`/`DADAOInstrInfo.td`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `contract-abi`（**不从实现反推**，Spec-first）；尾调用须保持返回寄存器约定（`rd8`）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯后端能力补全 ⇒ 无新决策、无需 ADR。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-074t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-074t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-074t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **真尾调用已实现（优化）**：最小复现 `extern long g(void); long f(void){ return g(); }`（`-O2`）经 `clang` rc=0，且生成代码为**尾跳转**（复用返回地址、无额外 `call`/`ret` 帧往返）——**不能只是「已降级为非尾调用」**（须给反汇编证据）。
2. **尾调用语义正确（E2E）**：尾调用链（至少两级、含非 void 返回）经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）；返回寄存器约定（`rd8`）保持。
3. **真实基准**：crc32 / md5sum / tarfind / ud / xgboost **至少一个**经 `-O2` 编译 **rc=0**（给真实命令 + rc）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）；`-O0` 集不下降。
5. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-074t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（改尾调用判定/返回路径 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**任务定位**：**优化项（非 M6 硬性，用户裁定）**——实现真尾调用 tail-jump。实现复用既有 `jump` 编码 + PEI epilogue 机制、仅限寄存器实参，**未牵动 ABI/寄存器/栈布局多处** ⇒ **未触发停工判据**。
**测试结果**：一键证据脚本 `.work/evidence/LLVM-074t/run.sh` → `checks: pass=29 fail=0`、`RUN_EXIT=0`（含注入自检）；门控 `make build-mc`/`check`（lit 83/83）/`check-lit`（83/83）/`check-patch-tree`（3 comp / 109 patches OK）均 EXIT=0。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.h,DADAOISelLowering.cpp,DADAOCodeGen.td,DADAOISelDAGToDAG.cpp,MCTargetDesc/DADAOMCCodeEmitter.cpp}.patch` + `components/llvm-project/changelog.md` + `tests/llvm/lit/CodeGen/DADAO/tail-call-lowering.ll`（改断言）+ `tests/llvm/lit/CodeGen/DADAO/tail-call-musttail-reject.ll`（新增）。
**验收结果**（真实输出 + 退出码；日志 `.work/log/llvm/LLVM-074t-*.log`）：
1. 最小复现 `long f(void){return g();}` `-O2`：`llc` rc=0，反汇编 `jump [rb0, g]`（**无 `call`/`ret`**）——真尾跳转；编码 `70`（jump）≠ `74`（call）。
2. E2E 尾调用链（`main→t1→t2→t3→leaf`，含非 void）：clang→ld.lld→QEMU **exit=40**（期望 30+2+1+7=40）；反汇编 4 条 `70` 尾跳转；返回值经 `rd8` 隐式转发（epilogue 不碰 `rd8`）。
3. 基准 `-O2` 编译 rc=0：crc32/md5sum/tarfind/ud/xgboost（原 G4 命中项）。
4. `spec|contracts` 交集空；`git status --porcelain -uall` 仅上述文件、无 `_tmp/_orig/_rej`。
5. 注入自检：`Eligible` 判定置 `false` ⇒ `git diff` 非空、重建 llc ⇒ 断言 FAIL（jump 消失、现 call）⇒ `cp`+md5（`907ccd56…`）还原 ⇒ 重建 ⇒ 回绿（29/29）。
**新发现/坑**（建议沉淀）：①DADAO **可实现**真尾调用：无尾调用指令但有普通 `jump`（不压 RegRAS ⇒ 复用调用者返回地址）；帧拆除交 PEI（尾跳指令 `isReturn`）。②尾跳指令**必须不标 `isBranch`**——否则 `BranchRelaxation::getBranchDestBlock` 会对符号操作数 `getMBB()` 断言（直接 `jump_iiii` 因 `isBranch` 不可复用；间接 `jump_rrii` 因 `isIndirectBranch` 侥幸跳过）。③`byval`/`Indirect`/`sret` 实参是指向**本帧**的指针，尾跳拆帧后悬垂（latent 误编译）⇒ 与 RISCV/AArch64 同守卫拒绝。④`clang-23` 独立链接 DADAO 静态库，`ninja llc` **不更新它** ⇒ clang/llc 行为不一致（曾误判为后端 bug）。
**遗留问题**：无。（可选后续：栈实参/变参的尾调用需复用调用者出参区，属进一步增强。）

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可交付（`待验收`）。范围 = `components/llvm-project/patches/**`（5 补丁）+ `tests/llvm/**`（1 改 1 新）+ `changelog.md`；未动 `spec/`/`contracts/`，未改已有函数签名，未引入外部依赖。

**自主逐行审查**：
- `LowerCall` 尾调用路径与普通路径**逐字段同构**（实参扩展 / callee 取法 / RegMask / 实参寄存器），差异仅「不发 CALLSEQ、发 `DADAOISD::TAIL`、保留 `CLI.IsTailCall`」；`ArgLocs`↔`OutVals` 下标一致（同普通路径）。
- 边界：eligibility 覆盖 varargs / 栈实参 / byval / Indirect / sret；不满足者 `tail` 走 `IsTailCall=false`（正确 `call`+`ret`）、`musttail` `report_fatal_error`（**非 assert**）。间接尾调经 `tailjmp_rrii`（`rbha+rd0+0`）。
- 指令层：`tailjmp_iiii`/`tailjmp_rrii` 与 `jump-iiii`/`jump-rrii` 同编码（0x70/0x71）但不 `isBranch`（防 BranchRelaxation 断言）；`isReturn` 驱动 PEI 发 epilogue；`isCodeGenOnly` 不进汇编匹配器。
- 防造假：证据脚本 `rc` 直取（无 `tee`）；注入经 `diff --name-only` 非空 + 重建 + md5 对账；全程无 `git checkout/restore/stash`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 byval/sret/Indirect 尾跳后悬垂（latent 误编译） | ✅已修 | eligibility 加 `Arg.Flags.isByVal()/isSRet()` 与 `CCValAssign::Indirect` 守卫 | `tail-call-lowering.ll::fwd_big` 降级为 `call`+`ret`；手工 `byval.ll`：`call`+`ret` 无 jump；E2E exit=40 不变 |
| F2 `isBranch` 触发 BranchRelaxation 断言 | ✅已修 | 新增 CodeGen-only `tailjmp_*`（同编码、无 `isBranch`）替代 `jump_iiii` | `llc -O2` rc=0（此前 rc=134 崩溃）；disasm `70`/`71`/`74` 各自正确 |
| F3 注释残留「TAILJMP pseudo」（实为实指令） | ✅已修 | 注释改「tailjmp_iiii/tailjmp_rrii」 | 源码 + changelog 措辞一致 |
| F4 `ninja llc` 不更新 `clang-23`（易误判后端 bug） | ✅不修（已记录） | —（用完整 `make build-mc` 保证 clang/llc 同步） | clang 与 llc 输出一致（均 tail-jump）；记录于完成区「新发现④」 |
| F5 `musttail` 失败信息未含 byval/indirect/sret | ✅已修 | 信息补全 + 新增 `tail-call-musttail-reject.ll` | lit 83/83（含该新测试 PASS） |

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**。全部 7 条验收项通过；独立注入 opcode 变更 `0x70→0x74` ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿。

**重跑记录**（真实输出，无 `tee`，rc 直捕）：
1. **反汇编**：`f(){return g();}` `-O2` → `jump [rb0, g]`（编码 `70`），无 `call`；`warm`(void) → `jump [rb0, body]`；`ind`(fp) → `jump [rb16, rd0, 0]`（编码 `71`）；`vwarm`(varargs) → `call [rb0, vbody]` + `ret rd0, 0`（降级）。rc=0。
2. **E2E ≥3 级链**：`main(0)→a(2 args)→b(1 arg)→c(3 args,间接 fp)→leaf(4 args)`。手算：leaf(7,8,15,-1)=7+16+45-4=64。QEMU exit=64 ✓。反汇编 4 条 `jump [` + 0 条 `call [`（crt0→main 的 `call` 不计入链）。`rd8` 经 epilogue 不碰、隐式转发。
3. **降级路径**：varargs / byval / sret 各例 `-O2` 均 `call` + `ret`（无 `jump`）。varargs E2E `vsum(3,10,11,12)=33` QEMU exit=33 ✓。`musttail` + byval → `report_fatal_error` → SIGABRT rc=134，信息含 "DADAO: 'musttail' call cannot be lowered: … byval/indirect/sret"（非断言）。
4. **BranchRelaxation 交互**：`tailjmp_iiii` 不标 `isBranch`（`DADAOCodeGen.td` L174-188 确认）→ BranchRelaxation 忽略它；与 `call_iiii`（同样不标 `isBranch`、同 PCRel_24 修复）行为一致；越界目标由 lld `checkInt` 报 relocation overflow 错（`DADAO.cpp.patch` L147-155），非静默误编。**结论：不回归**。
5. **不回归**：`make build-mc` rc=0；`make check` 83/83 + 全仓库检查 PASS（rc=0）；`make check-lit` 83/83（rc=0）；`make check-patch-tree` 3 comp / 109 patches OK（rc=0）。`-O0` 集 3 jump + 1 call（降级），与 `-O2` 一致，不下降。
6. **证据脚本**：`.work/evidence/LLVM-074t/run.sh` 审查通过——逐条 FAIL 路径可达（`ck_eq`/`ck_rc` 比较失败即 FAIL）；注入 `sed 's/!VarArgSaveArea && CCInfo.getStackSize() == 0/false/'` ⇒ `git diff` 非空 + 重建 + jump 消失 + call 出现 ⇒ `cp`+md5(`907ccd56…`)还原 + 重建 ⇒ 回绿。重跑：`pass=29 fail=0 RUN_EXIT=0`。
7. **补丁纪律**：series 71 补丁（一文件一补丁、非空 blob）；`spec|contracts` 交集空；`git status --porcelain -uall` 仅本任务文件 + 1 个 untracked（`tail-call-musttail-reject.ll`）；无 `_tmp/_orig/_rej`。

**独立注入**（与 `Eligible=false` 不同）：改 `tailjmp_iiii` opcode `0x70→0x74`（`DADAOCodeGen.td` L174）→ `touch` + `ninja llc` 重建 → `llvm-objdump` 确认编码变 `74`（call）→ `cp`+md5 还原 → 重建 → 编码回 `70`（jump）。源树 `git diff --name-only` 干净。

**约束核验**：①真尾调用已实现（jump 而非 call+ret）✓；②E2E 语义正确（exit=64 手算一致）✓；③真实基准 -O2 rc=0（crc32/md5sum/tarfind/ud/xgboost）✓；④spec/contracts 交集空 ✓；⑤证据脚本 RUN_EXIT=0 ✓；⑥无残留 ✓；⑦musttail 显式报错（非断言）✓。

**问题**：无阻断项。建议后续：栈实参/变参尾调用需复用调用者出参区，属进一步增强（非 M6 硬性）。
