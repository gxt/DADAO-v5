# QEMU-071t: `ftmin`/`fomin`/`ftmax`/`fomax` 执行语义（softfloat `minimum_number`）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-159t`（记录已立，`scope: excluded`）、`INFRA-099t`（门控串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §4.x`（`SPEC-159t`）：`min/max` = IEEE 754-2019 §9.6 **`minimumNumber`/`maximumNumber`**。
- 边界：单 NaN（含 sNaN）⇒ 返回数字（sNaN 另置 NV）；双 NaN ⇒ **canonical qNaN**（正号、payload 0）；`−0 < +0`；`x==y` 同号 ⇒ 任一；不涉舍入。

### 现场事实（2026-10-21 核，执行前须复核）

- **QEMU softfloat 已提供** `float32_minimum_number` / `float64_minimum_number`（`include/fpu/softfloat.h` 的 `MINMAX_1(type, minimum_number, float_minmax_isnum)`）⇒ 语义与 754-2019 一致，**直接调用**，不自写比较。
- 现有 helper 范式（`gen_convert_f2i` 等）已处理：从 `rf0[33:32]` 取舍入模式（本族**不需要**，无舍入）、把 softfloat 返回的 `flags` 合回 `rf0[4:0]` ⇒ **复用该范式**（只合 flags）。
- `insn.decode`：`01000100` + opx；新增 4 条（`0x26/0x27/0x2E/0x2F`）。
- `check_qemu_trans --strict` 现为 266-4（`SPEC-159t` 新记录缺 trans）⇒ 本册收口后 **266/266**。

## 目标

1. 4 条按 754-2019 `minimumNumber` 执行（含 sNaN 置 NV、canonical NaN、`−0<+0`）；
2. `decode` + `trans_*` 齐备 ⇒ `check_qemu_trans --strict` 全绿；
3. 探针覆盖语义矩阵（见 §C），并验证**不置** NX（无舍入）。

## 接口规范

- **输入**：`components/qemu/patches/target/dadao/insn.decode.patch`、`insn_trans/trans_fp.c.inc.patch`、`helper.c.patch`、`tools/qemu/*`。
- **输出**：4 条 `insn.decode`；`trans_ftmin_orrr_rf`/`trans_ftmax_orrr_rf`/`trans_fomin_orrr_rf`/`trans_fomax_orrr_rf`（或统一 `gen_fp_minmax(a, isdbl, ismax)`）；探针；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（不翻 scope）；不改其它 FP 族；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 调用与标志

- 单精度走 `float32_minimum_number` / `float64_minimum_number`（`float_maximum_number` 对应 max）；传入 `&env->fp_status`（或既有 helper 的 status 入口）；
- 返回后：`rfHB` 写结果；`flags` 按既有方式**或入** `rf0[4:0]`（不得覆盖既有位）；
- 目的 `rf0` ⇒ ILLI（`fp_check_dst_rf0`）；源可为 `rf0`。

### B. 与"分两步实现"的区别（必须能测出）

- 禁止用 `min = (a<b) ? a : b` 的朴素比较实现——它在 **单 NaN** 时返回第二操作数（错）、**双 NaN** 时返回某个 NaN（可能非 canonical）、且 **sNaN 不置 NV**。

### C. 探针矩阵（每格都要断言）

- 有序：`1 vs 2`、`−2 vs 1`（min/max 各一）；
- **`±0` 四组合**：`(+0,−0)`、`(−0,+0)`、`(+0,+0)`、`(−0,−0)`（min(−0,+0)=−0、max=+0）；
- 单 NaN：`qNaN vs 1`、`1 vs qNaN`（两序）、`sNaN vs 1`、`1 vs sNaN` ⇒ 返回数字；sNaN 两序都置 **NV**；
- 双 NaN：`qNaN vs qNaN`、`sNaN vs qNaN` ⇒ **canonical qNaN**（`0x7FC00000`/`0x7FF8000000000000`）+ sNaN 情形置 NV；
- 相等：`1 vs 1`（返回任一即可，但须与实现一致）；
- Inf：`+Inf vs 1`、`−Inf vs +Inf`；
- **标志面**：qNaN 输入 ⇒ NV **不置**；任一有限值比较 ⇒ **NX 不置**（无舍入）。

## 验收标准

1. `check_qemu_trans --strict` ⇒ **266/266**（现场输出）。
2. 探针全绿（计数现场派生），每格含**期望结果 + 期望标志**两列断言。
3. ILLI：目的 `rf0` ⇒ 真跑观察到非法指令异常。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**：① 改用朴素 `(a<b)?a:b`（临时改 trans）⇒ 单 NaN/双 NaN/sNaN 用例红；② sNaN 不置 NV ⇒ 标志用例红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；关闭 `SPEC-159t` 登记的 issue。

## 做（阶段）

1. 现场复核（softfloat 函数签名、helper 范式、`insn.decode` FP 行、探针骨架）。
2. decode 4 条 + `gen_fp_minmax` + helper 调用 → `make build-qemu`。
3. 探针矩阵（先有序/±0，再 NaN/标志）。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 朴素比较实现 ⇒ 单 NaN 返回错、sNaN 不置 NV ⇒ 红；还原 ⇒ 绿。
- 双 NaN 返回输入 NaN 而非 canonical ⇒ 红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做 `minimum`/`maximum`（NaN 传播）——CPU 无此指令，由 LLVM 展开。
- 不做 `*mag`（绝对值 min/max）；不做整数 min/max。
- 不改 `scope`（`SPEC-160t`）；不接后端（`LLVM-124t`）；不做集成（`TESTCASES-059t`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
