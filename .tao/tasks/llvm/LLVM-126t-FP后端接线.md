# LLVM-126t: FP 后端接线补齐（`ISS-188` 剩余项：比较/符号/取余/分类/位转/缩放/舍入模式/饱和转换）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-156t`（`fcls` 位序已对齐 754/LLVM ⇒ `is.fpclass` 零重排）、`LLVM-124t`（min/max）、`LLVM-125t`（取整）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么单独立一本

- `ISS-188`（FP 完备性缺口）把 **硬件已有** 的能力与 **真 ISA 缺口**混在一起列。
- 本轮已把真缺口补齐：`fma`（`SPEC-157t`…）、`min/max`（`SPEC-159t`…）、取整（`SPEC-161t`…）、`fcls` 位序（`SPEC-156t`）。
- **剩下全部是"硬件有指令、后端没接"**：本册一次性收口，不动 ISA、不改 `spec/`。

### 现场事实（2026-10-21 核，执行前须复核）

- `DADAOISelLowering.cpp` 的 `Expand` 列表中仍包含：`FABS`、`FREM`、`FCOPYSIGN`、`FMINNUM/FMAXNUM/FMINIMUM/FMAXIMUM`（后四者由 `LLVM-124t` 处理）、`FCANONICALIZE`、`FLDEXP`、`FFREXP`、`FGETSIGN`、`FP_TO_SINT_SAT`/`FP_TO_UINT_SAT`、以及数学函数族（走 libm，属预期）。
- 硬件已具备（**均无需新指令**）：
  - `fosgnj`/`fosgnn`（copySign / negate-sign）⇒ `fabs`（`sgnj(x, rf0)`）、`fneg`（`sgnn(x, rf0)`）、`copysign`（`sgnj`）
  - `forem`/`ftrem` = **IEEE remainder**（商取最近、平局取偶）⇒ **与 LLVM `frem`（= libm `fmod`，余数符号随被除数）语义不同**，**本册不接**（见 §E）
  - `foqcmp`/`foscmp` ⇒ 全部 `fcmp` 条件（结果在 rd 里是 FP 格式的 1/0/−1/NaN，需按符号与零判定）
  - `focls`/`ftcls` ⇒ `is.fpclass`（10 位 one-hot；`SPEC-156t` 后位序与 LLVM `FPClassTest` 一致 ⇒ 掩码可直接 `and`）
  - `rd2rf`/`rf2rd` ⇒ `bitcast double↔i64`
  - `fosclb` ⇒ `ldexp`（指数是 FP 寄存器里的整数值，需 `io2fo` 一次）
  - `rf0[33:32]` 读写 ⇒ `llvm.get.rounding`/`set.rounding`
  - `fo2io`/`ft2it` 等 ⇒ `fptosi.sat`/`fptoui.sat`（规范：越界 ⇒ 饱和 + NV）
  - `FCANONICALIZE` ⇒ 恒等（无扩展精度）
- **`bitcast` 现状**：`bitcast double→i64` 缺模式（`ISS-188` 原文列出）；`rd2rf`/`rf2rd` 已实现。

## 目标

1. 上表 8 类（比较/符号/分类/位转/缩放/舍入模式/饱和/恒等）全部**有线可落**：每类 **1–3 条**指令，**零 libcall**；`frem` 经核对**不接**（见 §E）；
2. `fcmp` 全部 12 种条件（quiet/signaling）行为正确；
3. `is_fpclass`/`fpclassify` 直接由 `fcls` + 掩码实现（零重排）；
4. `get/set.rounding` 读写 `rf0[33:32]`；
5. `ISS-188` 可关闭（或收窄为"仅剩 f16/bf16 等已裁定不做项"）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOISelLowering.cpp`、`DADAOInstrInfoFP.td`、`DADAOCodeGen.td`）、`tests/llvm/lit/**`。
- **输出**：各节点的 Legal/Custom 设置与 pattern/伪指令；lit 覆盖每类；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`、不动 ISA 编码；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. `fcmp` 取值（最容易出错）

- `foqcmp a,b` 输出 **FP 格式**：`>0 ⇒ 1`、`==0 ⇒ 0`、`<0 ⇒ −1`、`unordered ⇒ qNaN`；
- 实现 `SETOEQ/OGT/OGE/OLT/OLE/ONE/ORD/UNO` 与 `SETUEQ/UGT/...` 全部条件，**用符号/零/NaN 判定**（NaN 的位模式为正数 ⇒ 需 `focls` 或比较自身判别）；
- 必须覆盖：`x != x`（UNO）、`x == x`（ORD）、`±0` 相等、`sNaN` 置 NV（signaling 比较）、`qNaN` 不置 NV（quiet 比较）。

### B. `fabs`/`fneg`/`copysign`

- `fabs(x)` = `fosgnj(x, rf0)`（`rfHD = rf0` 即 abs，`SimRISC-07 §5` 明写）；
- `fneg(x)` = `fosgnn(x, rf0)`；`copysign(x,y)` = `fosgnj(x,y)`；
- 断言：**1 条**指令，且不产生 FP 异常。

### C. `is_fpclass` / `fpclassify`

- `focls rd, {rf}`（标量 `immu6=1`）返回 10 位 one-hot；
- `is_fpclass(x, M)` = `focls` + `and mask` + `!=0`（单类掩码可省 `and`：直接与 one-hot 常量比较）；
- `fpclassify`（C 5 类）= `fcls` + 常量映射（编译期可折叠成 1 次 `and`/比较）；
- **位序依赖 `SPEC-156t`**：若其未落地，本册 BLOCKED。

### D. `bitcast` / `ldexp` / `rounding` / `sat`

- `bitcast double↔i64`：`rf2rd`/`rd2rf`（1 条，无 FP 异常）；
- `ldexp(x, n)`：`io2fo(n)` + `fosclb`（2 条）；`frexp` 不接（保持 libm）；
- `get.rounding`/`set.rounding`/`flt.rounds`：读/写 `rf0[33:32]`（写需只改该字段，用 `set.w` + 掩码）；
- `fptosi.sat`/`fptoui.sat`：`fo2io`/`ft2it` 等（硬件已饱和 + NV）。

### E. `frem` 不接（已核对，**不是缺口**）

- **LLVM `frem` = libm `fmod`**（LangRef：「same output as libm `fmod` … remainder has the same sign as the dividend」；`TargetLowering` 的 `FREM` 展开走 `RTLIB::REM_*` = `fmod`）；
- **我们的 `forem`/`ftrem` = IEEE remainder**（`SimRISC-07 §4.1`：`rfHC − n × rfHD`，n 取最近整数、平局取偶）；
- **数值反例**：`fmod(5,3)=2` vs `remainder(5,3)=−1`；`fmod(−5,3)=−2` vs `remainder(−5,3)=1`；
- LLVM **无** `llvm.remainder` intrinsic（`grep int_remainder` = 0）⇒ `frem` **保持 `Expand`**（落 musl `fmod`），**禁止**接 `forem`；
- `forem` 目前仅经内联汇编可达；若要服务 C 的 `remainder()/remainderf()`，应在 **musl 侧**改造（`INFRA` 另册，低频）；
- `ISS-188` 中"`frem` 缺 ISel 模式"一条按此改为**"不接（语义不一致）"**，不是补 pattern。

## 验收标准

1. lit：9 类各至少 1 例，断言**指令计数**与**无 libcall**（`FileCheck` + `llvm-nm`/反汇编）。
2. `fcmp` 12 种条件全覆盖（含 `UNO`/`ORD` 与 `±0`）。
3. `is_fpclass`/`fpclassify`：`fcls` 后掩码**零重排**（掩码常量与 `FPClassTest` 一致）。
4. C 层抽查：`fabs/fabsf`、`copysign`、`fmin`、`rint/nearbyint`（已由 `LLVM-125t`）、`isnan/isinf/isfinite/fpclassify`、`ldexp`、`bit cast`（`union`/`memcpy` 不适用时用 `__builtin_bit_cast`）。
5. **`frem` 已核对为"不接"**：`FREM` 保持 `Expand`（libcall `fmod`）；完成区须粘 `git grep` 证据证明未新增 `FREM`→`forem` 映射；不得静默错接。
6. `check-instrinfo` 0 errors；`check-lit`/`check-lit-full` 绿。
7. 改 `.td` 后 `make install-host` + `build-builtins` + `build-musl-shared`。
8. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
9. **可达 FAIL ≥ 2**：① 把 `fabs` 错接成 `fosgnn`（取反）⇒ 值用例红；② `is_fpclass` 掩码不重排（用旧位序）⇒ 分类用例红。
10. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；`ISS-188` 关闭或收窄（写明剩余项与理由）。

## 做（阶段）

1. 现场复核（各节点当前 action、`rd2rf`/`rf2rd` 的 `.td`、`forem` 与 `frem` 语义差异）。
2. `fabs/fneg/copysign` → `fcmp` → `fpclass` → `bitcast` → `ldexp` → `rounding` → `sat`（每步加 lit）。
3. `frem` 语义核对并定接法。
4. `install-host` + builtins/musl + L1/L2 + 反例注入。
5. 完成区 + `ISS-188` 收口。

## 可达 FAIL（**≥2**）

- `fabs` 误接 `fosgnn` ⇒ 值红；还原 ⇒ 绿。
- `is_fpclass` 用旧位序掩码 ⇒ 分类红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不接 `frexp`、数学函数族（libm）；不做 f16/bf16（已裁定）。
- 不做 constrained FP（`llvm.experimental.constrained.*`）。
- `frem` 保持 libm（`fmod`）；`forem` 不接（语义不同，已核）。若要让 `remainder()` 用上硬件，另立 `INFRA` 册改 musl。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
