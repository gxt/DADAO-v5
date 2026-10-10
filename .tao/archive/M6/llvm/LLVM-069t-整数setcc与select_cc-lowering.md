# LLVM-069t: 整数 `setcc` / `select_cc` lowering（补后端能力缺口）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`LLVM-062t`（整数完整调用约定，已验证）、`LLVM-066t`（FP `select_cc`/`FCMP` 结构可作对照，已验证）、`LLVM-063t`（clang target / E2E 通道，已验证）；**与 Wave 2 其它任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景（自包含；主会话 2026-10-10 已独立复核）

`TESTCASES-039t`（Embench 接入）engineer **诚实停工**（判据**未降级** = 恒定退出码 0）：交付的 DADAO 工具链**无法编译任何真实 C 代码**——凡把比较结果**当值**使用（`a==b`、`!x`、`a<b`、三目 `?:`、逻辑 `&&`/`||`）的函数，`clang`/`llc` 在**指令选择**阶段崩溃（SIGABRT）：

```
fatal error: error in backend: Cannot select: t16: i64 = setcc t20, t21, seteq:ch   (clang rc=1)
LLVM ERROR: Cannot select: t13: i64 = setcc t2, t4, seteq:ch                        (llc rc=134)
```

**纯分支**形态 `if(a<b) return 1; return 0;`（`br(icmp)`，-O0）正常（rc=0）；-O2 因 if-conversion 又转 `select_cc` 崩溃。`llc` 手工 `.ll`（`icmp eq`+`zext i1→i64`）亦复现 ⇒ **与 clang 无关，是后端 ISel 能力缺口**。

**根因**：DADAO 后端 `DADAOTargetLowering` 仅把 `ISD::BR_CC`/`ISD::BRCOND` 设 `Custom`（`DADAOISelLowering.cpp`），**无 `ISD::SETCC` / 整数 `ISD::SELECT_CC` 的 action 或 ISel 模式**（`grep -rniE setcc` 仅命中注释）。M4/M6 向量一律用 `br(icmp)` 回避此形态，故历次任务未暴露。

**影响**：19 个 Embench 基准中 **14 个** `verify_benchmark` 直接 `return (比较)`，其余经 `support/main.c:37 return (!correct)` 也必经 `setcc` ⇒ **无一基准可编译**，`TESTCASES-039t` 首验收不可达。

**证据指针**：`.work/log/testcases/TESTCASES-039t-{blocker.log,blocker_probe_result.txt,matrix_result.txt,progress.md}`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）；现 `DADAOISelLowering.cpp` 已定义 `DADAOISD::CMP`/`CMPU`/`FCMP` 与 `LowerBR_CC`/`LowerBRCOND`，`DADAOCodeGen.td` 已有 `DADAOCmp`/`DADAOCmpU`（`SDTIntBinOp`）与 FP `selectcc` 模式。
  - `.tao/knowledge/contract-isa.md §6.2`（`cmp.si`/`cmp.ui` 立即数比较、`cmp.uo` 寄存器比较；**结果按 -1/0/1 写满 64 位**，见 §6.2.1/§6.2.2）、`§6.5`（`cs.n`/`cs.z`/`cs.p`/`cs.eq`/`cs.ne` 条件赋值，rrrr）、`§8`（条件跳转 `br.*`）。
  - `.tao/knowledge/contract-fp.md §8` + `DADAOCodeGen.td` 的 FP `selectcc`→`cs.*` 模式（结构对照）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`）：
  1. **整数 `setcc`-as-value lowering**（IR `icmp` 经 `zext i1→i64`）：产出 **0/1 的 i64 值**。做法（engineer 择一，须给理由）：(a) `setOperationAction(ISD::SETCC, MVT::i64, Custom)` + `LowerSETCC`——用 `DADAOISD::CMP`/`CMPU`（结果 -1/0/1）+ `cs.*` 归一化为 0/1；(b) TableGen `Pat` 直接匹配 `setcc`。**谓词须全覆盖**：`eq/ne/slt/sle/ult/ule/sgt/sge/ugt/uge`（有符号 `CMP` / 无符号 `CMPU` 两条路径）。
  2. **整数 `select_cc` / `select` lowering**：整数 `SELECT_CC`（及经合法化后的 `select`）lowering 为 `cs.*` 条件赋值（结构参照 FP `selectcc`，注意操作数/真值臂交换）。
  3. 如需新增 `DADAOISD` 节点/模式或改 `DADAOISelDAGToDAG`/`DADAOCodeGen.td`/`DADAOISelLowering.{h,cpp}`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  4. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `contract-isa §6.2/§6.5`（`cmp` = -1/0/1；`cs.*` 条件赋值），**不从实现反推**（Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；**不改 ISA/ABI/ELF 契约**（纯后端能力补全，无新决策 ⇒ 无需 ADR）。
  - 与 Wave 2 同改 `components/llvm-project/patches` ⇒ **串行**（不得与其它 Wave 2 任务并行）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-069t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-069t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-069t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`setcc` 全谓词可编译**：对 `eq/ne/slt/sle/ult/ule/sgt/sge/ugt/uge`（有/无符号）各构造返回比较值的函数，`clang`（或 `llc`）**rc=0** 生成目标文件（给真实命令 + 输出）。原崩溃最小复现 `int f(int a,int b){return a==b;}` 必须 rc=0。
2. **`setcc` 语义正确（E2E）**：至少覆盖「相等 / 有符号小于 / 无符号小于 / 不等 / `!x` / 逻辑与」各一例，经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）；含 `return (a<b)`、`return !x`、`return (a<b)&&(c<d)` 形态。
3. **整数 `select_cc`/`select` 语义正确（E2E）**：三目 `?:`（有/无符号条件）经端到端执行**退出码正确**（给真实命令 + 退出码）；-O2 形态（if-conversion 产生的 `select_cc`）不再崩溃。
4. **真实 C 可编译**：Embench `support/main.c:37` 的 `return (!correct)` 惯用法与 `verify_benchmark` 的 `return (比较)` 惯用法**可编译**（给真实命令 + rc）；不要求在 `TESTCASES-039t` 范围内跑通全量基准。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**，计数由门控现场统计）。
6. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-069t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把某谓词的 `CMP`/`CMPU` 选错或归一化常数改错 ⇒ 断言/期望 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**做法选择**：(a) `Custom` lowering（非 TableGen `Pat`）。理由：`setcc-as-value` 需产出 0/1（臂为常量 0/1），且整数 `select_cc` 的比较操作数常为**常量**——TableGen 需按「reg/imm × 有/无符号 × 10 谓词」组合爆炸，而 `Custom` 可复用既有 `CMP/CMPU`（已有 reg/imm 模式）+ 新增 `cs.*` 节点统一归一化/选臂。

**测试结果**：证据脚本 58/58（`fail=0 detected=1`，`RUN_EXIT=0`）；`make build-mc`/`make check`/`make check-patch-tree`（3 组件 106 补丁 OK）/`make check-lit` 全 **EXIT=0**。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.h,DADAOISelLowering.cpp,DADAOCodeGen.td}.patch`（source `.work/source/llvm-project`，3 文件补丁重导出，`series` 仍 71）；`components/llvm-project/changelog.md`（追加 LLVM-069t 行）；新增 `tests/llvm/lit/CodeGen/DADAO/setcc-select.ll`、`tests/e2e/setcc_e2e.c`、`tests/e2e/selectcc_e2e.c`（**越界披露**：任务书输出范围为 `tests/llvm/**`，E2E C 程序按既有约定落 `tests/e2e/`，沿用 `LLVM-066t` 的 `tests/e2e/fp_codegen.c` 先例）。
**验收结果**（真实输出与退出码；完整日志 `.work/log/llvm/LLVM-069t-*.log`，脚本 `.work/evidence/LLVM-069t/run.sh`）：
1. **逐谓词 rc=0**（clang 与 llc 各 10 条）：`eq/ne/slt/sle/sgt/sge/ult/ule/ugt/uge` 全 `rc=0`；崩最小复现 `int f(int a,int b){return a==b;}` clang `rc=0`；结构核验 `setcc_<p>_cmp`∈{`cmp.so`,`cmp.uo`}、`setcc_<p>_cs`∈{`cs.n`,`cs.p`,`cs.z`} 全 PASS（映射按 `contract-isa §6.2/§6.5`）。
2. **setcc E2E**（编译→`ld.lld`→QEMU→退出码）：`setcc_e2e.c` -O0/-O2 退出码 **59**（相等/有符号</无符号</不等/`!x`/`&&`）；`return (a<b)`、`return (!correct)` 惯用法 clang `rc=0`。
3. **select_cc E2E**：三目 `?:`（有/无符号）`selectcc_e2e.c` -O0/-O2 退出码 **15**；`-O2`（if-conversion）**不再崩溃**（`rc=0`）。
4. **门控**：`make check` EXIT=0；lit `check-lit` 77 发现 / 76 通过 / 1 unsupported —— 基线（`TESTCASES-038t-make-check.log`）76/75/1 ⇒ **+1 通过、无下降**（新增 `setcc-select.ll` PASS）。
5. **`spec//contracts/` 交集空**（脚本 `spec_intersection_empty` `expected=[] actual=[]`）；**无残留**（`git status --porcelain -uall` 仅本任务 3 补丁 + changelog + 3 新测试）。
6. **注入自检**：把 `CMPU↔CMP` 选错 ⇒ `pl_ult` 由 `cmp.uo`→`cmp.so`（`PASS(inject-detected)`）⇒ `cp`+md5 还原（`bd2d04e5…` 相等）⇒ `ninja … llc` 重建 ⇒ 回绿 `cmp.uo`。
**新发现/坑**（建议沉淀）：`ISD::SETCC` 的 action 按**操作数**类型、`ISD::SELECT_CC` 按**结果**类型取 ⇒ `SELECT_CC MVT::i64 Custom` 会连带捕获「FP 比较选整数臂」（i64 结果）的 selectcc，故 `LowerCmpSelect` 统一处理（FCMP+cs.*）并删除失效的 `FPSelCC_{f64,f32}_rd`（FP 结果仍走原 pattern）。`cs_*_rd` 臂操作数须用 `i64` **类型**叶子（非 `GPRD` 寄存器类叶子）才接受**常量臂**（经 `CONST_WYDE` 物化）。常量比较沿用既有 `LowerBR_CC` 的 12 位立即数界（不满足即 `report_fatal_error`，不静默）。
**遗留问题**：① 常量比较/选择超出 12 位立即数（如 `a < 5000`）仍显式失败（与既有 `br(icmp)` 分支路径**同界**，属既有能力边界，非本任务范围）；② 未在 `TESTCASES-039t` 范围跑通全量 Embench（任务书 §验收4 明确不要求）——本任务已解除其编译阻塞（根因 `ISS-173`）。
**ISS-173 原话**：「凡把比较结果**当值**使用的 C（`a==b`、`!x`、`a<b`、三目 `?:`、逻辑 `&&`/`||`）经 `clang`/`llc` 在**指令选择**阶段 SIGABRT…最小复现 `int f(int a,int b){return a==b;}`…19 个 Embench 基准中 14 个 `verify_benchmark` 直接 `return (比较)`，其余经 `main.c:37` 也必经 `setcc` ⇒ 无一基准可编译」。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可交付（`待验收`）。改动范围 = `components/llvm-project/patches/**`（3 文件补丁）+ `tests/**`（3 新文件）+ changelog；未动 `spec/`/`contracts/`，未改任何已有函数签名，未引入外部依赖。

**逐行审查**：
- 谓词映射逐条对照 `contract-isa §6.2/§6.5`（`<`→`cs.n`、`>`→`cs.p`、`==`/`!=`→`cs.z`；`<=`/`>=` 复用 `>`/`<` 并交换臂；有/无符号→`CMP`/`CMPU`）；10 谓词 llc 结构核验全 PASS。
- 边界：常量臂物化（`sel_const`→`set.zw 0xb/0x16`+`cs.n`）；非 setcc 条件（`trunc i64 to i1`→`and.o …,1`+`cs.z`）；常量超 12 位立即数→显式 `report_fatal_error`（不静默）；LHS 常量→交换+`getSetCCSwappedOperands`。
- 回归防护：`br(icmp)` 仍降 `cmp.so`+`br.nn`（未退化）；FP-条件选整数臂 `foqcmp`+`cs.n`；FP 结果 select 仍走 `FPSelCC_*_rf`；`make check` 全绿、lit 无下降。
- 防造假：证据脚本 `rc=$?` 直取退出码（无 `tee`）；注入自检真实重建 llc 并检出；还原以 md5 对账 + `check-source-state`（HEAD=base+1 干净）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 大常量（>12 位立即数）比较显式失败 | ❌不修 | —（与既有 `LowerBR_CC` 同界，既有能力边界） | `.work/log/llvm/LLVM-069t-evidence.log` |
| F2 删 `FPSelCC_{f64,f32}_rd` 是否回归 FP 选整数臂 | ✅已修/验证 | FP i64 结果 selectcc 改由 `LowerCmpSelect` | `llc fpsel.ll`→`foqcmp`+`cs.n` rc=0；lit 76 通过 |
| F3 `setBooleanContents(ZeroOrOne)` 影响 | ✅验证 | 新增 1 行 | E2E 退出码正确；lit 无下降 |

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**

**逐条约束核验**：

| # | 约束 | 结果 | 证据 |
|---|------|------|------|
| 1 | 10 谓词全覆盖（signed CMP / unsigned CMPU） | ✅ | lit `setcc-select.ll` PASS；脚本逐谓词 `cmp.so`/`cmp.uo` + `cs.n`/`cs.z`/`cs.p` 全绿 |
| 2 | 语义正确：signed/unsigned 区分 | ✅ | `test_sign.c` E2E exit=1（-1<1 signed=true, unsigned=false）；`test_full.c` exit=206 全 10 谓词手算/实测一致 |
| 3 | 归一化（cmp -1/0/1 → 0/1） | ✅ | `test_norm.c` exit=5；若漏归一则(5>7)!=0→1 误→exit=7；exit=5 证明 cs.* 正确 |
| 4 | select_cc 语义 | ✅ | `selectcc_e2e.c` -O0/-O2 均 exit=15（signed/unsigned 三目，含 if-conversion） |
| 5 | 边界常量 >12 位 → 显式失败 | ✅ | `v1 < 3000`（signed，immu12=3000>2047）→ clang rc=1 + "does not fit a 12-bit immediate"；llc rc=134（SIGABRT）；不静默错码 |
| 6 | 不回归：门控全绿 | ✅ | `make build-mc` EXIT=0；`make check` 77 discovered / 76 passed / 1 unsupported；`make check-patch-tree` 106 patches OK；`make check-lit` 77 discovered / 76 passed / 1 unsupported |
| 7 | spec/contracts 交集空 | ✅ | `git diff --name-only | grep -E '^(spec|contracts)/'` → 空 |
| 8 | 补丁纪律：3 补丁 + changelog + 3 测试 | ✅ | `git status --porcelain -uall` 仅 3 patch + changelog + 3 test + 任务书；无 `_tmp/_orig/_rej/_preinject` |
| 9 | 证据脚本 RUN_EXIT=0 | ✅ | 重跑 `run.sh`：58/58 PASS，fail=0，detected=1（CMPU↔CMP 注入检出），RUN_EXIT=0 |

**独立注入（CS_N→CS_P，slt 极性反转）**：
- 注入前 md5：`bd2d04e567ea692f4bb54b557b3993a8`
- 注入后 md5：`348ed77c4925a244d2a74ecdd9b0344b`（diff 非空 ✓）
- 注入后重建 llc（3 targets，~1min）→ `test_sign.ll` slt 变 `cs.p` → exit=**0**（应为 1，FAIL ✓）
- 还原 cp+md5=`bd2d04e5...` = 备份 ✓
- 还原后重建 → `test_sign.ll` slt 恢复 `cs.n` → exit=**1**（GREEN ✓）

**手算表（关键用例）**：

| 测试 | 期望 exit | 实际 exit | 验证方式 |
|------|----------|----------|---------|
| `test_full.c` 10 谓词（5 vs 7）| 206 | 206 | QEMU E2E |
| `test_sign.c` signed/unsigned -1 vs 1 | 1 | 1 | QEMU E2E |
| `test_norm.c` 归一化（5 vs 7）| 5 | 5 | QEMU E2E（exit=5 vs 未归一=7）|
| `setcc_e2e.c` -O0 | 59 | 59 | QEMU E2E |
| `selectcc_e2e.c` -O0/-O2 | 15 | 15 | QEMU E2E |
| `v1 < 3000`（signed imm 超界）| clang rc≠0 | rc=1 | 显式报错 |

**手算推理（test_full.c）**：
5 vs 7：eq=0, ne=1, slt=1, sle=1, sgt=0, sge=0, ult=1, ule=1, ugt=0, uge=0
→ bits 0-9 = 0|2|4|8|0|0|64|128|0|0 = **206** ✓

**手算推理（test_sign.c）**：
-1 signed < 1 → true(1)；0xFFFFFFFFFFFFFFFF unsigned < 1 → false(0)
→ bit0=1, bit1=0 → **1** ✓

**手算推理（test_norm.c）**：
(5<7)!=0 → 1，(5>7)!=0 → 0，(5==5)!=0 → 1，(5==7)!=0 → 0
→ 1|0|4|0 = **5**（若未归一化则 (5>7) cmp=-1, -1!=0→1, exit=7 ≠5）✓

**workspace 快照对账**：`git status --porcelain -uall` 与 md5 与注入前快照一致，无残留。

#### architect 提交留痕（A 分支提交）

- **档位**：**正常提交**（reviewer 判 **Accepted**）。
- **提交号**：分支提交 `947c32d`（`LLVM-069t: 整数 setcc/select_cc lowering…`）；本留痕为其后继提交，随 `master` **一次性落地**（`git merge --squash`）。
- **文件集对账**（`git -c core.quotepath=false diff --cached --name-only` vs 完成区「修改文件」+ 任务范围）：产物 **3 补丁 + `changelog.md` + 3 新测试**全部纳入；**漏提 0 / 多提 0**。**越界**：`tests/e2e/{setcc,selectcc}_e2e.c`（任务书输出范围仅 `tests/llvm/**`）—— engineer 已披露、沿用 `LLVM-066t` `tests/e2e/fp_codegen.c` 先例，**合理**。
- **收尾台账**：`milestones.md`（`LLVM-069t`→`已验证` + `TESTCASES-039t` 说明更新）、`issues.yaml`（`ISS-173`→`closed`/`resolved_by: LLVM-069t`，`check_issues.py` rc=0）、`lessons.md §8.40`、任务书 `**状态**`→`已验证`，一并入库。`.work/**`（证据脚本/日志）按 `.gitignore` 不入库。
