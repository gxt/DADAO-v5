# TESTCASES-059t: `min/max` 集成验证（NaN/±0 矩阵 + clamp/排序 + 编译形态）

**模块**：testcases
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-160t`、`LLVM-124t`、`QEMU-071t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么要专门验

- `min/max` 的坑**全在边界**：单 NaN 返回谁、双 NaN 是否 canonical、sNaN 是否置 NV、`−0` vs `+0`。普通数值用例**全部通过**也不能说明语义对。
- 期望值必须**独立**：由 Python 直接用 IEEE 规则实现（不调用 QEMU/LLVM 结果），并**先自证**（用 `math` 的 `fmin/fmax` 交叉验证有限值用例）。

### 现场事实（2026-10-21 核，执行前须复核）

- 硬件语义：`minimumNumber`/`maximumNumber`（754-2019 §9.6）。
- 后端：`llvm.minnum`/`llvm.minimumnum`/C `fmin` ⇒ **1 条**指令；`llvm.minimum`（C23 `fminimum`）⇒ 展开（`fomin` + NaN 选择）。
- 集成范式：`run_atomics_probe.py` + `oracle_atomics.py`（probe + oracle + 两档）。
- fast 预算须现场测（`check-testcases-suites`），定层按 `Process-07 §3`。

## 目标

1. **语义矩阵**（指令级）：有序 / 相等 / ±0 四组合 / 单 NaN（q&s，两序）/ 双 NaN / Inf / 次正规 —— 结果与**标志**双断言；
2. **展开路径**：C23 `fminimum`（NaN 传播）在目标上结果正确且**无 libcall**；
3. **集成**：clamp/clip 循环、4×4 矩阵逐元素 min/max 与 oracle 一致；
4. 编译形态：`fmin` 热循环 **1 条 `fomin`**（可选，若 `llc` 可用）；
5. 用例能失败（≥2 条真实注入）、耗时可控。

## 接口规范

- **输入**：`tests/` 新增 C 用例 + `tools/testcases/` probe/oracle；`Makefile`（如需新目标或纳入 `check-testcases-suites`）。
- **输出**：`tools/testcases/run_minmax_probe.py`、`tools/testcases/oracle_minmax.py`（IEEE 规则手写 + 自证）、C 用例（`minmax_matrix.c`、`minmax_clamp.c`、`minmax_c23.c`）、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不引入外部库；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 语义矩阵（每条都断言"值 + NV"）

- `min/max` × {有序正向、有序反向、相等同号、`+0/−0` 两两组合、`qNaN` 左/右、`sNaN` 左/右、双 `qNaN`、`sNaN+qNaN`、`±Inf`、次正规}；
- 期望：单 NaN ⇒ 数字；sNaN ⇒ 数字 + **NV 置位**；双 NaN ⇒ **canonical qNaN**（`0x7FC00000`/`0x7FF8000000000000`）；qNaN ⇒ **NV 不置**；任何情形 **NX 不置**。

### B. `fminimum`（C23）展开路径

- 用 `fminimum(a,b)`（clang 支持 C23 时）或 `__builtin_fminimum`；断言：任一 NaN ⇒ 结果为 NaN（canonical）；无 NaN 时 `−0<+0` 成立；
- 断言**无 libcall**（`llvm-nm` 或反汇编检查无 `fmin` 符号引用）。

### C. 集成

- `clamp(x, lo, hi)` 循环 1k 次（含 NaN 与 ±0 边界）；
- 4×4 矩阵逐元素 `min`/`max`（含 NaN 行）；
- 与 oracle 逐位比较（不是"近似"）。

### D. 定层

- 单跑测耗时；≤ fast 预算 ⇒ 纳入 `check-testcases-suites`（L2）；否则按需目标 + 完成区写明实测值。

## 验收标准

1. 语义矩阵全绿（**值与 NV 双列**），两档 `-O0`/`-O2`。
2. `fminimum` 路径：结果正确 + **零 libcall**；`−0<+0` 断言成立。
3. clamp/矩阵集成全绿；计数现场派生；失败/跳过分列。
4. **可达 FAIL ≥ 2**：① 把硬件语义改成"返回第二操作数"（临时）⇒ 单 NaN 用例红；② 去掉 sNaN 的 NV ⇒ 标志用例红。
5. `make check-modules`（L2）rc=0（若纳入）或 L1 + 单目标 rc=0。
6. 证据脚本一键复跑、真实 rc 落盘（禁 `cmd | tee` 吞码）。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（atom probe 结构、两档口径、`rf0` 读取方式、fast 预算）。
2. 写 oracle（IEEE 规则 + 自证）→ 指令级矩阵 → 绿。
3. `fminimum` 展开路径 + 零 libcall 断言。
4. clamp/矩阵集成；两档跑；耗时测定层。
5. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 临时把 `fomin` 实现改为"返回第二操作数" ⇒ 单 NaN 两序用例红；还原 ⇒ 绿。
- 临时让 sNaN 不置 NV ⇒ 标志断言红；还原 ⇒ 绿。

## 已知边界（**披露**）

- 不做 `minimum` 的硬件版用例（无该指令；只验 LLVM 展开）。
- 不做 `*mag`；不做整数 min/max；不做性能基准。
- 不引入外部数学库。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
