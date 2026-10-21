# TESTCASES-058t: `fma` 集成验证（单次舍入对拍 / 点积与 GEMM / Horner 代价）

**模块**：testcases
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-158t`、`LLVM-123t`、`QEMU-070t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么要单独验"单次舍入"

- `fma` 与 `mul+add` **不等价**：前者只舍入一次。若实现或选择退化为两条，**普通用例多数仍对**，只有特定输入暴露 ⇒ 必须有**针对性反例**，否则等于没测。
- 期望值须**独立**：用 Python `fractions.Fraction`（精确有理数）+ 一次 IEEE 舍入算出，**不得**从 QEMU/LLVM 结果反推（`AGENTS.md`「Independent oracle」）。

### 现场事实（2026-10-21 核，执行前须复核）

- 集成范式：`tools/testcases/run_atomics_probe.py` + `oracle_atomics.py`（probe + 独立 oracle + 两档）；本册照此结构。
- 目标上 `double`/`float` 已完整（`fo`/`ft`）；`unsigned __int128` 可用。
- 点积型语义 ⇒ **循环累加形态零拷贝**、3-address `fma(a,b,c)` 允许 1 条 `rf2rf`（`LLVM-123t` 已在 lit 断言，本册做端到端复核）。
- `check-testcases-suites`（L2 fast）耗时预算须现场测后定层（`Process-07 §3`）。

## 目标

1. **指令级**：单次舍入反例 + 特殊值 + 四种舍入模式，与独立 oracle 逐例相等；
2. **算法级**：点积 / 小型 GEMM（double）结果与 oracle 在**给定误差界**内一致；Horner 多项式与 oracle 相等；
3. 代码形态断言：循环累加编译结果 **1 条 `fofma`**（可选，若 `llc` 可用则做）；
4. 用例能失败（≥2 条真实注入），耗时可控（定层有实测依据）。

## 接口规范

- **输入**：`tests/` 新增 C 用例 + `tools/testcases/` probe/oracle；`Makefile`（如需新目标或纳入 `check-testcases-suites`）。
- **输出**：`tools/testcases/run_fma_probe.py`（编译 → QEMU → 比对，两档 `-O0`/`-O2`）、`tools/testcases/oracle_fma.py`（`fractions` 精确 + 一次舍入；含自检）、C 用例（`fma_edges.c`、`fma_dot.c`、`fma_horner.c`）、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不引入外部库（OpenSSL/zlib）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 单次舍入反例（核心）

- 构造：取 `a = 1 + 2^-23`（单）/`1 + 2^-52`（双），`b = a`，`c = -1`：
  - 精确 `a×b + c = 2^-22 + 2^-46`（单）⇒ 一次舍入与两次舍入结果**不同**；
- 至少 **4 组**这类反例（单/双各 2 组），每组的两个候选结果（fma / mul+add）必须**互相不同**——用例先自检这一点，否则该例无效。

### B. 特殊值与模式

- `±0`、`±Inf`、qNaN、sNaN、次正规；
- 四种舍入模式（`rf0[33:32]`：RN/RZ/RP/RM）各 ≥1 例，选会被模式影响的值；
- `sNaN` 输入 ⇒ NV 置位且结果为 qNaN（用 `rf0` 读标志验证，若 C 层无接口则用内联汇编读取）。

### C. 算法级

- **点积**：长度 16/64/256 的随机向量（种子固定），与 oracle 的**逐步 fma**（同样单次舍入）逐位相等；
- **小型 GEMM**：4×4 × 4×4（double），与 oracle 相等；
- **Horner**：5/9 次多项式，与 oracle 相等；
- 误差界：算法级若用不同求和顺序，须给**明确误差界**（相对 ≤ k·u），不得写"近似相等"这类不可判断言。

### D. 定层

- 先单跑测总耗时；≤ fast 预算 ⇒ 纳入 `check-testcases-suites`（L2）；否则单列按需目标并在完成区写明实测值（`Process-07 §3`）。

## 验收标准

1. 指令级（含 4 组单次舍入反例）+ 特殊值 + 四模式全绿，**两档优化级**。
2. 点积 / GEMM / Horner 全绿（误差界明写）。
3. 计数现场派生；失败/跳过分列，禁静默跳过。
4. **可达 FAIL ≥ 2**：① 把实现退化为 `fomul`+`foadd`（临时）⇒ 单次舍入反例红；② 翻转 oracle 的一个期望位 ⇒ 红。
5. `make check-modules`（L2）rc=0（若纳入）或 L1 + 单目标 rc=0（若不纳入）。
6. 证据脚本一键复跑、真实 rc 落盘（禁 `cmd | tee` 吞码）。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（atom probe 结构、两档口径、`rf0` 读取方式、fast 预算）。
2. 写 oracle（`fractions` + 一次舍入）+ 自检（fma 与 mul+add 必须不同）。
3. 指令级 → 特殊值/模式 → 点积/GEMM/Horner。
4. 两档跑 + 耗时测 + 定层 + 反例注入。
5. L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时把 C 侧 `fma()` 换成 `a*b+c` ⇒ 反例红；还原 ⇒ 绿。
- 改 oracle 一组期望（`cp` 备份 + md5）⇒ 红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做性能基准（只做正确性 + 代码形态断言）；
- 不做 `fmsub`/`fnmadd` 用例（指令未立）；不做 libm 精度对比（`fma` 只保证单次舍入）。
- 不引入外部数学库。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
