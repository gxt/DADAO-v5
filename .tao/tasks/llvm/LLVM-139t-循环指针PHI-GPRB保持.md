# LLVM-139t: 循环指针 PHI 的 GPRB 保持（machine pass）

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-138t
**状态**：待验收

## 背景
DADAO 的 i64/指针共用位宽，SelectionDAG 可能把循环 pointer PHI 分到 GPRD，导致每轮地址消费前插 `rd2rb`。PR 新增 `DADAOPointerPHIBank`（post-ISel、pre-RA），仅处理「入口已在 GPRB、单入口/单回边、无 call/inline asm 的直接 pointer PHI + 两段 GEP」，重建 GPRB PHI 和 RB 加法。该 pass 是机器级改写，风险最高，必须独立评审。

## 目标
1. 重放/实现 pass，保持窄范围：多回边、call/inline asm、select 派生、ptrtoint/inttoptr、普通 i64 PHI 一律回退，不改变全局 i64 寄存器类/ABI。
2. **补正确性保护**：
   - `BaseCopy`/被替换的 `CopyDst` 必须与 PHI 在同一支配域（或证明使用点受 MBB 支配）；不能只看存在性；
   - `add_o_bbd` 的 GPRB/GPRD 操作数约束、`TailConst` 插入、PHI 删除顺序；
   - 不破坏 debug loc、kill flags、live range（pre-RA）。
3. 测试：正例 + 至少覆盖跨块 COPY、循环内 call、多回边、switch、select、inline asm、ptr-int、i64 PHI；RUN 行加 `-verify-machineinstrs`（`-stop-after` 与最终 asm 两路）。
4. 运行期验证：QEMU 执行正例循环，检查结果；llvm-ts 定向（至少一个 pointer-loop 基准）不回归。
5. 更新 docs/矩阵；报告注明「减少 rd2rb」是汇编级指标，不冒充整体性能。

## 验收
- 新增 lit 全绿；完整 `check-lit` 不回归（现场统计）；`-verify-machineinstrs` 无报错。
- QEMU 正例结果与独立 oracle 一致；llvm-ts 定向 rc=0。
- `make check`/`check-patch-tree` rc=0；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-139t/`。

## 约束
- 只改该 machine pass、pass 接线、测试/文档/补丁；不碰 code model/tailjmp/i64 移位/窄 extension。
- 不改 ABI/全局寄存器类/spec/contracts/QEMU。
- **不提交、不 push**；重建申报；全量/夜跑未授权时不跑。

## 完成区

**状态**：待验收

### 修改文件
- `components/.../DADAOPointerPHIBank.cpp.patch`（新，381 行）+ `{CMakeLists.txt,DADAO.h,DADAOTargetMachine.cpp}.patch` + `series`（`make_patch.py` 增量导出）
- `.work/source/llvm-project`（base+1 单 commit、干净）；`tests/unit/llvm/lit/CodeGen/DADAO/m10-loop-pointer-bank.{ll,mir}`（4 正例 + 8 负例 + 两操作数序 MIR）
- `tests/unit/llvm/codegen/m10-loop-pointer-bank.ll` + `expected.yaml`；`tools/testcases/validate_codegen_vectors.py`（vocab/oracle 分支）
- `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（重生成：buildmi 59→63、yes 202 不变）；`.tao/knowledge/milestones.md`

### 测试结果
证据 22/22；`check-lit` **158 passed/0 failed**（基线 156 + 2，现场统计）；`run_codegen_e2e` 18/18；QEMU 正例 exit=0；llvm-ts 定向 `Shootout/lists` 前后同 pass、stdout sha256 一致；`make check`/`check-patch-tree`（205 patch）/`check-isa-coverage` rc=0

### 验收命令与结果
- `bash .work/evidence/LLVM-139t/run.sh` → `evidence: 22 passed, 0 failed` rc=0；I1（lit 期望错）/I2（期望和错）注入→FAIL、`cp`+md5 还原→PASS
- 构建：`build-mc`/`install-host`/`build-musl-shared` rc=0；安装根 llc == 构建树 llc（md5 `efaa6c56…`）
- 正例汇编：`add.o rb4, rb16, rd6` + `add.o rb16, rb4, rd5`，循环体零 `rd2rb`/`rd2rd`（基线为 `rd2rb`+`add.uo`+`add.si`）；**「减少 rd2rb」只作汇编级指标，非整体性能**
- 组件增量：`git diff components` 仅 5 文件、无 `^-` 内容删除；`GPRBTC|tailjmp|ExternalSymbol|selectCodeModel|CM.value_or` 0 命中

### 新发现/坑
- PR 版把 `add_o_bbd` 基址恒当操作数 1；`ADD_PSEUDO` 指针在第 2 位时产出 `add_o_bbd %off:gprd, %phi:gprb`，`-verify-machineinstrs` 报 Illegal virtual register（旧二进制已复现，MIR 测试锁定）
- 机器 PHI 允许入值与 def 异类 ⇒ 只查「COPY 存在」不成立；按 SSA + MDT 逐 use（PHI 用其入边源块）证明支配
- C 源指针循环无外部指针入参时入口值先 `rb2rd` 成 GPRD ⇒ 不触发；运行期向量用 `noinline` 助手（指针参数 rb16/GPRB）方命中
- `validate_codegen_vectors.py` 在 master 已红三条（137/138 未补 vocab/oracle），本册只保证自有记录 PASS

### 遗留
- 未跑 `check-full`/夜跑（未授权）；未提交/未 push（提交权归 architect）
- PR 的 `docs/llvm-136-139-后端优化工作报告.md` 未落（仓库内无该文件；本册报告 = 完成区）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`DADAOPointerPHIBank.cpp` 全文逐行；4 处接线（CMakeLists/DADAO.h/TargetMachine/series）；`.ll`/`.mir`/运行期向量/oracle/证据脚本；矩阵与 `components` 增量。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `add_o_bbd` 基址恒按操作数 1 处理；`ADD_PSEUDO` 指针在第 2 位时生成 `add_o_bbd %off:%gprd, %phi:%gprb`（类与描述符矛盾） | ✅已修 | 接受后先清 op1/op2 的 kill，再把基址归一到 op1 | 新增 `m10-loop-pointer-bank.mir` 两操作数序；旧二进制运行报 `Illegal virtual register`（rc=134），新二进制 rc=0 |
| COPY 目的为物理寄存器时 `MRI.getRegClass` 触发断言 | ✅已修 | `Dst.isVirtual()` 先判 | `-verify-machineinstrs` 全 opt 级 rc=0；负例 `m10_loop_call` 含 `$rb16 = COPY` |
| `add %p, %p` 时另一操作数仍是旧 PHI，删除后悬空 | ✅已修 | `Offset != OldPhi` 显式判 | 该形不会进入接受分支（检查在变更前） |
| 支配只查「存在性」不够 | ✅已修 | 要求 IsSSA + `MDT.dominates`（MBB→BaseCopy）+ 逐 use 判支配（PHI 用入边源块） | 跨块 COPY 正例、嵌套循环正例均改写且 verify 通过 |
| 删除 PHI 会留下 debug 引用 | ✅已修 | `replaceRegWith`（含 debug 操作数）+ `substituteDebugValuesForInst` | `clang -g` 编译 `walk` 与 `-force-instr-ref-livedebugvalues` 均 rc=0 |
| 改写操作数保留旧 kill 标志 | ✅已修 | `clearKillFlags(NewPhi)`、op1/op2 `setIsKill(false)` | `-O0..-O3` + verify 全绿 |
| 常量每轮物化可能吃掉收益 | ✅已修 | `CONST_WYDE` 提到前置块 | 嵌套循环里落在内层前置块（`bb.1.outer`） |
| 负常量未覆盖 | ✅已修 | 两链正例含 `-2` 元素基址 | MIR `CONST_WYDE -16`、verify 通过 |
| `check_full`/夜跑 | ⏸延后 | 未授权 | 已在遗留声明 |

**判决**：finding 全部处置（8 项已修、1 项延后且已披露）⇒ 可标 `待验收`。
