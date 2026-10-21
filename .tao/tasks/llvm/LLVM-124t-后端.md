# LLVM-124t: `ftmin`/`fomin`/`ftmax`/`fomax` 后端（`.td` + `FMINNUM_IEEE`/`FMINIMUMNUM` Legal）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-159t`（记录已立）、`QEMU-071t`（语义已实现）；`INFRA-099t`（门控串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 真源

- `spec/SimRISC-07 §4.x` + `contract-fp.md §minmax`：4 条 `orrr`，`op=0x44`，`ha` 分别为 `0x26/0x27/0x2E/0x2F`；语义 = 754-2019 `minimumNumber`/`maximumNumber`。
- 硬件保证：单 NaN（含 sNaN）⇒ 数字（sNaN 置 NV）；双 NaN ⇒ canonical qNaN；`−0 < +0`；无舍入。

### 现场事实（2026-10-21 核，执行前须复核）

- LLVM 有 **4 个** 相关 ISD 节点：`FMINNUM`（遗留）、`FMINNUM_IEEE`（定义良好的 number 语义）、`FMINIMUM`（NaN 传播 = 754-2019 `minimum`）、`FMINIMUMNUM`（2019 `minimumNumber`）。
- 现有后端把这些**全部**标为 `Expand`（`DADAOISelLowering.cpp` 的 `setOperationAction` 列表含 `FMINNUM/FMAXNUM/FMINIMUM/FMAXIMUM`）⇒ 现在 C `fmin/fmax` 是 4–6 条比较序列。
- LLVM 的降级链（源码已核）：`expandFMINNUM_FMAXNUM`（`FMINNUM`→`FMINNUM_IEEE` + `FCANONICALIZE`）、`expandFMINIMUMNUM_FMAXIMUMNUM`（→`FMINNUM_IEEE` + canonicalize）、`expandFMINIMUM_FMAXIMUM`（`FMINNUM_IEEE` + `SETUO` 选 NaN；若底层不保证 ordered zero 再加 `SETOEQ` ±0 修正）。
- **结论**：目标只需让 **`FMINNUM_IEEE`/`FMAXNUM_IEEE` 与 `FMINIMUMNUM`/`FMAXIMUMNUM` Legal**（映射到本组指令），`FMINIMUM/FMAXIMUM` 继续 `Expand` 即可覆盖 C23。

## 目标

1. `.td` 定义 4 条（`orrr`，`(outs RF:$hb), (ins RF:$hc, RF:$hd)`）；
2. `@llvm.minnum`、`@llvm.minimumnum`、C `fmin/fmax` ⇒ **1 条** `fomin`/`fomax`（无比较序列）；
3. `@llvm.minimum`（C23 `fminimum`）⇒ 展开为 `fomin` + NaN 选择（**无 libcall**、不落 `fmin` 库函数）；
4. 不回归既有 `fcmp`/`cs.*-rf` 路径。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOInstrInfoFP.td`、`DADAOCodeGen.td`、`DADAOISelLowering.cpp`）、`tests/llvm/lit/**`。
- **输出**：4 条 `.td` def + 2 组 pattern（`fminnum_ieee`/`fmaxnum_ieee`、`fminimumnum`/`fmaximumnum`）；lit（正/反例）；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（翻转归 `SPEC-160t`）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 节点映射（**关键，别只映射 `FMINNUM`**）

- `FMINNUM_IEEE`/`FMAXNUM_IEEE` → `fomin`/`fomax`（`ft` 同理，按 `VT` 选）；
- `FMINIMUMNUM`/`FMAXIMUMNUM` → 同一条（语义与硬件完全一致）；
- `FMINNUM`/`FMAXNUM`（遗留）**保持 Expand**，由 LLVM 转成 `FMINNUM_IEEE`（其 `FCANONICALIZE` 在无 x87 扩展精度的目标上应为恒等；须现场确认 `FCANONICALIZE` 的 lower 结果不引入额外指令）；
- `FMINIMUM`/`FMAXIMUM` **保持 Expand**。

### B. 语义断言（用 lit）

- `@llvm.minnum.f64(x,y)` ⇒ **恰好 1 条 `fomin`**；
- `@llvm.minimumnum.f64` ⇒ 同上；
- `@llvm.minimum.f64` ⇒ `fomin` + `SETUO` 选择（**数字符**：无 `call fmin`、无 `call fminf`）；
- C `fmin(a,b)`（`-O2`）⇒ 1 条；
- `-0`/`+0` 语义：`llc` 不得额外插入 ±0 修正（硬件保证 ordered zero ⇒ `MinMaxMustRespectOrderedZero` 成立）；
- 反例：`fomin rf0, rf1, rf2` ⇒ 汇编失败/ILLI（`dst_rf0`）。

### C. 已知陷阱

- `FMINNUM` 若被误标 Legal 而不做 canonicalize，会让 **sNaN 不置 NV**、与 `minimumnum` 混淆 ⇒ 必须走 Expand 路径；
- `nsz` 标志：LLVM 会传 `hasNoSignedZeros`；我们的硬件仍按 `−0<+0` 执行，结果**仍是合法**的（`nsz` 允许非确定）✓ 但不得因此删掉硬件语义。

## 验收标准

1. 三条 lit 正例各断言**指令计数**（`minnum`/`minimumnum` = 1；`minimum` ≤ 4 且无 libcall），粘真实输出。
2. `llvm-mc` 编码 == `44 26/27/2E/2F`（现场派生）+ round-trip。
3. 反例 `dst_rf0` 汇编拒绝。
4. `check-instrinfo` 0 errors（`excluded` 有 `.td` 合规）；`check-lit`/`check-lit-full` 绿。
5. 改 `.td` 后 `make install-host` + `make build-builtins` + `make build-musl-shared`（新鲜度门控）。
6. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
7. **可达 FAIL ≥ 2**：① 把 `FMINNUM_IEEE` 改回 Expand ⇒ 指令计数断言红；② 去掉 `FMINIMUM` 的 NaN 选择（临时）⇒ `minimum` 语义用例红。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（FP `.td` 形态、`FCANONICALIZE` 的 lower、ISD 节点名）。
2. `.td` 4 条 + 两组 pattern + 编码 round-trip。
3. lit：`minnum`/`minimumnum` 各 1 条；`minimum` 展开；`fmin` C 层 1 条。
4. `install-host` + builtins/musl + L1/L2。
5. 反例注入 + 完成区。

## 可达 FAIL（**≥2**）

- `FMINNUM_IEEE` 保持 Expand ⇒ lit「1 条 fomin」红；还原 ⇒ 绿。
- 删 `FMINIMUM` 展开里的 NaN select（临时）⇒ `@llvm.minimum` 用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做 `minimum` 的硬件版（无此指令）；不做 `*mag`；不改 `fcmp` 路径。
- 不改 `scope`（`SPEC-160t`）；不做集成（`TESTCASES-059t`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
