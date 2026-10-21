# QEMU-072t: `ftrnd`/`fornd` 执行语义（softfloat `round_to_int` + 5 静态模式 + DYN）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-161t`（记录已立，`scope: excluded`）、`INFRA-099t`（门控串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §4.x`（`SPEC-161t`）：`immu6` one-hot 六档
  `0x01` 取偶 / `0x02` 远离 0 / `0x04` 向 0 / `0x08` 向 +∞ / `0x10` 向 −∞ / `0x20` 动态（读 `rf0[33:32]`，置 NX）。
- 共同边界：sNaN ⇒ NV + qNaN；qNaN 原样；`|x| ≥ 2^p` 原样；`±0` 符号保留；Inf 原样；5 个静态档**不置** NX。

### 现场事实（2026-10-21 核，执行前须复核）

- softfloat 已有 `float32_round_to_int` / `float64_round_to_int`（按 `float_status.float_rounding_mode` 取整，**已处理** ±0/Inf/NaN/大值）；
- 模式枚举含全部 5 种：`float_round_nearest_even`、`float_round_ties_away`(4)、`float_round_to_zero`、`float_round_down`、`float_round_up` ✓ ⇒ **静态档无需自写取整**；
- 现有 helper 范式：读 `rf0[33:32]` 取舍入、把 flags 或回 `rf0[4:0]` ⇒ 复用；
- `check_qemu_trans --strict` 现缺 2 条 ⇒ 本册收口后应全绿。

## 目标

1. 六档语义与 754-2019 一致（**NX 只有 `0x20` 置**）；
2. `decode` + `trans_*` 齐备 ⇒ `check_qemu_trans --strict` 全绿；
3. 探针覆盖"模式敏感"用例（同一输入在 4 种 `rf0` 模式下的 `0x20` 结果）。

## 接口规范

- **输入**：`insn.decode.patch`、`insn_trans/trans_fp.c.inc.patch`、`helper.c.patch`、`tools/qemu/*`。
- **输出**：2 条 `insn.decode`；`trans_ftrnd_orri_rf`/`trans_fornd_orri_rf`（共用 `gen_fp_round_to_int(a, isdbl)`）；探针；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不改其它 FP 族；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 静态 5 档：临时 `float_status` + 只合 NV

1. 复制真实 `fp_status` 到临时结构，设 `float_rounding_mode` = 目标模式；
2. 调 `float{32,64}_round_to_int`；
3. **只**把返回的 **NV** 合回真实 `rf0[4:0]`，**丢掉 NX**（静态档不置 inexact）；
4. 结果写 `rfHB`。

> 若直接改真实 status 的 mode，再改回，会**污染**并发/后续指令的 mode 与标志 ⇒ **必须**用副本 + 选择性合并。

### B. DYN（`0x20`）：直接用真实 status

- 直接 `float*_round_to_int(x, &env->fp_status)` ⇒ 内部按 `rf0[33:32]` 取整，**NX/NV 都合回**（= `roundToIntegralExact`）。

### C. 合法性

- `immu6` 非 one-hot ⇒ ILLI（`encode_onehot`，与 `rev.o` 同规则）；目的 `rf0` ⇒ ILLI（`dst_rf0`）。

### D. 探针矩阵

- 输入集：`±0.0`、`±0.4`、`±0.5`、`±1.5`、`±2.5`、`±3.5`、`±1.0`、`2^53`（fo）/`2^24`（ft）、`+Inf`、`−Inf`、qNaN、sNaN、次正规；
- 6 档 × 上述输入，逐例断言**结果位模式**（`±0` 符号、`0.5` 的取偶/远离差异、`2.5`/`3.5` 的取偶结果）；
- **模式敏感专测**：把 `rf0[33:32]` 依次设为 `RNE/RTZ/RDN/RUP`，对同一组输入跑 `0x20`，断言结果随模式变化；
- **NX 专测**：静态档（如 `trunc(1.5)`）后 **NX 不置**；`0x20`（`rint(1.5)`）后 **NX 置位**；qNaN 输入 **NV 不置**；sNaN 输入 **NV 置位**。

## 验收标准

1. `check_qemu_trans --strict` 全绿（现场输出）。
2. 探针全绿（计数现场派生），含 **6 档 × 边界值**、**4 种模式敏感**、**NX/NV 标志**三类断言。
3. ILLI：`immu6=0x03`（非 one-hot）、`immu6=0`、目的 `rf0` ⇒ 真跑观察到非法指令异常（3 例）。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**：① 静态档也走真实 status（NX 被置）⇒ NX 用例红；② `0x20` 写死 RNE 不读 `rf0` ⇒ 模式敏感用例红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；关闭 `SPEC-161t` 登记的 issue。

## 做（阶段）

1. 现场复核（softfloat 模式枚举、`round_to_int` 行为、helper 范式、探针骨架）。
2. decode 2 条 + `gen_fp_round_to_int`（静态副本 / DYN 直连）。
3. 探针（先值矩阵，再模式敏感，再标志）。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 静态档直接改真实 status ⇒ NX 被置 ⇒ 红；还原 ⇒ 绿。
- DYN 档写死 RNE ⇒ 模式敏感用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- `nearbyint` 无硬件变体（落 DYN，NX 可能置位 —— 已在 `SPEC-161t` 登记）。
- 不做 `*mag`；不改 `fo2io` 转换族（FP→整数另有指令）。
- 不改 `scope`（`SPEC-162t`）；不接后端（`LLVM-125t`）；不做集成（`TESTCASES-060t`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
