# QEMU-070t: `ftfma`/`fofma` 执行语义（softfloat 单次舍入 + 块/标量）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-157t`（记录已立，`scope: excluded`）、`INFRA-099t`（门控互斥；门控串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §4.x`（`SPEC-157t` 新增）：`ftfma rfHA, rfHB, rfHC, rfHD` = `rfHA ← rfHB × rfHC + rfHD`（单精度）；`fofma` 同（双精度）。
- **四操作数**：`rfHA ← rfHB × rfHC + rfHD`；目的与源**允许重叠** ⇒ **先读全部源再写**；**单次舍入**。
- 异常：sNaN ⇒ NV + qNaN；OF/UF/NX 按 IEEE，一次运算只置一次；舍入模式由 `rf0[33:32]` 控制。

### 现场事实（2026-10-21 核，执行前须复核）

- QEMU FP 实现分两层：`insn_trans/trans_fp.c.inc.patch`（位级/简单运算，纯 TCG）与 `helper.c.patch`（softfloat）。FMA **必须走 softfloat**（单次舍入无法用 TCG 位运算拼）。
- softfloat 已提供融合乘加入口（名称以现场源码为准，典型为 `float32_muladd` / `float64_muladd`，含 `flags` 与舍入模式参数）；**须现场确认本仓库 qemu 版本的函数名/签名**。
- 现有 helper 调用范式（`gen_convert_f2i` 等）已处理：从 `rf0` 取舍入模式、把 `flags` 合回 `rf0[4:0]` ⇒ **复用该范式**，不自造。
- `insn.decode`：新增 `ftfma`（`0x5E`）/ `fofma`（`0x5F`）两条**整 op 字节** pattern（`rrrr` 四寄存器，**无 opx**）。
- `check_qemu_trans --strict` 现有计数 = 262-1（`SPEC-157t` 新记录缺 trans；issue 已登记）⇒ 本册收口后应为 **262/262**。

## 目标

1. `ftfma`/`fofma` 按 IEEE 单次舍入执行（含 NaN/Inf/溢出/下溢与标志）；
2. `decode` + `trans_*` 齐备 ⇒ `check_qemu_trans --strict` **262/262**；
3. 语义探针覆盖：一般值、单次舍入反例、sNaN/qNaN、±0、溢出/下溢、`rf0` 四种舍入模式。

## 接口规范

- **输入**：`components/qemu/patches/target/dadao/insn.decode.patch`、`insn_trans/trans_fp.c.inc.patch`、`helper.c.patch`、`tools/qemu/*`（探针）。
- **输出**：两条 `insn.decode` pattern；`trans_ftfma_rrrr_rf`/`trans_fofma_rrrr_rf`（或统一 `gen_fp_muladd`，读 3 源写 1 目的）；helper 侧调用 softfloat 的 mulAdd；探针 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（本册不翻 scope）；不改其它 FP 族；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 单次舍入的**可判定证据**（本册最关键）

- 必须给一个**经典反例**：选 `a,b,c` 使 `round(a×b) + c ≠ round(a×b + c)`（例如 `a=b=1+2^-23` 附近、`c = -1`），探针断言结果等于 **精确积再舍入** 的那一个；
- 该反例同时用作"实现是否退化为 mul+add"的判据。

### B. 读序与写回

- 三个源（`rfHB`、`rfHC`、`rfHD`）**先全部读出**再写 `rfHA`；目的与源同寄存器时行为确定（规范要求）。
- 目的 `rf0` ⇒ ILLI（`dst_rf0`），沿用 `fp_check_dst_rf0`。

### C. 标志与舍入模式

- 从 `rf0[33:32]` 取舍入模式传给 softfloat；把返回 `flags` 合并进 `rf0[4:0]`（**只置位、清零语义照既有 helper**）。
- 一次运算只更新一次标志（不得拆成两次 mul/add 各置一次）。

### D. 探针覆盖

- 一般值：正/负/混合符号，≥16 组（含 `a×b` 与 `c` 量级相差大的情形）；
- 特殊值：`±0`、`±Inf`、qNaN、sNaN（sNaN ⇒ NV + qNaN 且**不**传播 payload 错误）；
- 边界：最大有限值 × 2 → OF；最小正规 × 2^-1 → UF（含次正规）；
- 舍入模式：四种（RN/RZ/RP/RM）**各 ≥1 例**，只测会被模式影响的值；
- 单次舍入反例 ≥1 例（见 A）。

## 验收标准

1. `check_qemu_trans --strict` ⇒ **262/262**（现场输出）。
2. 探针全绿（计数现场派生）；单次舍入反例**必须**有独立期望值（由 Python 精确有理数/`fractions` + 一次舍入算出，**不得**用 QEMU 自身结果反推）。
3. ILLI：目的 `rf0` ⇒ 真跑观察到非法指令异常。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**：① 把实现改成 `fomul`+`foadd` ⇒ 单次舍入反例红；② 舍入模式不接 `rf0`（固定 RN）⇒ 四种模式用例红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；关闭 `SPEC-157t` 登记的缺 trans issue。

## 做（阶段）

1. 现场复核（softfloat mulAdd 函数名/签名、helper 范式、`insn.decode` FP 行、探针骨架）。
2. `insn.decode` 两条 + `trans_*` + helper 调用 → `make build-qemu`。
3. 探针（先一般值，再单次舍入反例，再标志/模式）。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 实现退化为 `fomul`+`foadd`（临时改 trans）⇒ 单次舍入反例红；还原 ⇒ 绿。
- 舍入模式恒传 RN ⇒ 四种模式用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不改 `scope`（`SPEC-158t`）；不接 LLVM（`LLVM-123t`）；不做集成基准（`TESTCASES-058t`）。
- 不做 `fmsub`/`fnmadd`（负号靠 `fosgnn`）。
- 不加新的 softfloat 函数（只用既有 mulAdd；若缺失则**停下报告**，不自行改上游）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
