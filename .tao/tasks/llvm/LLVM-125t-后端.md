# LLVM-125t: `ftrnd`/`fornd` 后端（7 个取整 intrinsic → 6 档 one-hot）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-161t`（记录已立）、`QEMU-072t`（语义已实现）；`INFRA-099t`（门控串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 真源

- `SimRISC-07 §4.x`：`ftrnd/fornd rfHB, rfHC, immu6`；`immu6` one-hot：
  `0x01` 取偶、`0x02` 远离 0、`0x04` 向 0、`0x08` 向 +∞、`0x10` 向 −∞、`0x20` 动态（读 `rf0`，置 NX）。
- 偏差（`SPEC-161t` 已登记）：`nearbyint` 落 `0x20`，NX 可能被置位（值正确）。

### 现场事实（2026-10-21 核，执行前须复核）

- 我们后端当前把 `FCEIL/FFLOOR/FTRUNC/FROUND/FROUNDEVEN/FRINT/FNEARBYINT` **全部标为 `Expand`**（`DADAOISelLowering.cpp`）⇒ 现在是 5–10 条软件序列。
- 7 个 ISD 节点 ↔ immu6 的映射：
  - `FROUNDEVEN` → `0x01`；`FROUND` → `0x02`；`FTRUNC` → `0x04`；
  - `FCEIL` → `0x08`；`FFLOOR` → `0x10`；
  - `FRINT` → `0x20`；`FNEARBYINT` → `0x20`（**偏差**，见 §B）。
- `orri` FP 指令的 `.td` 先例：`foroot_orri_rf`（`(outs RF:$hb), (ins RF:$hc, immu6)`）⇒ 直接照抄形态。

## 目标

1. `.td` 两条（`ftrnd_orri_rf`/`fornd_orri_rf`），`op=0x44`、`ha=0x03/0x0B`；
2. 7 个 intrinsic **各 1 条**指令（无比较序列、无 libcall）；
3. `FNEARBYINT` 落 `0x20` 并在代码注释/完成区写明偏差；
4. 不回归既有 `fo2io` 转换与 `fcmp` 路径。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`、`tests/llvm/lit/**`。
- **输出**：2 条 `.td`；7 条选择路径（pattern 或伪指令）；lit（正/反例）；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（翻转归 `SPEC-162t`）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 选择方式

- 首选：`Pat` 直接匹配 `fceil`/`ffloor`/`ftrunc`/`fround`/`froundeven`/`frint`/`fnearbyint` → `(FORND $src, <onehot>)`；
- 若某节点带 `flags`（`no-nans` 等）导致不匹配，可用自定义 lowering 兜底（不得落 libcall）。

### B. `FNEARBYINT` 的偏差（**必须注释 + 完成区写明**）

- 落 `0x20`（DYN）⇒ 会置 NX；
- 依据：SimRISC 浮点无异常/陷阱，NX 仅为 `rf0[4:0]` 状态位；LLVM 非严格模式两者均 `IntrNoMem + IntrSpeculatable`（标志不可观察）；值语义完全一致；
- lit 只断言**指令与值**，**不得**断言 NX（避免把偏差固化成契约）。

### C. 边界（由硬件保证，后端不额外处理）

- `±0` 符号、`|x| ≥ 2^p` 原样、NaN/Inf 原样、sNaN 置 NV —— 均在 `QEMU-072t` 验证；后端只负责选择。

## 验收标准

1. lit：7 个 intrinsic **各 1 条** `fornd`（`FileCheck` 断言指令计数 + imm 值），粘真实输出。
2. C 层：`floor/ceil/trunc/round/nearbyint`（`-O2`）各 1 条；C23 `roundeven` 若可用则 1 条。
3. `llvm-mc` 编码 == `44 03/0B` 前缀（现场派生）+ round-trip。
4. 反例：`fornd rf0, rf1, 0x01` ⇒ 汇编失败/ILLI（`dst_rf0`）；`immu6=0x03`（非 one-hot）⇒ 汇编拒绝/ILLI。
5. `check-instrinfo` 0 errors；`check-lit`/`check-lit-full` 绿。
6. 改 `.td` 后 `make install-host` + `make build-builtins` + `make build-musl-shared`。
7. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
8. **可达 FAIL ≥ 2**：① 把 `FFLOOR` 映射成 `0x10` 以外的值（临时）⇒ lit 红；② 把 `FROUND` 与 `FROUNDEVEN` 映射对调 ⇒ `.5` 用例红。
9. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`foroot` 的 `.td` 形态、ISD 节点名、flags 影响）。
2. `.td` 2 条 + 7 条 pattern + 编码 round-trip lit。
3. 7 个 intrinsic 的 lit + C 层 `-O2` 抽查。
4. `install-host` + builtins/musl + L1/L2。
5. 反例注入 + 完成区。

## 可达 FAIL（**≥2**）

- `FFLOOR` 误映 `0x10` 以外 ⇒ lit 红；还原 ⇒ 绿。
- `FROUND`/`FROUNDEVEN` 对调 ⇒ `1.5/2.5` 用例红；还原 ⇒ 绿。

## 已知边界（**披露**）

- 不做 `nearbyint` 的 NX 精确性（偏差已登记）；不做 constrained FP（`llvm.experimental.constrained.*` 仍不支持）。
- 不做 `*mag`；不改转换族；不改 `scope`（`SPEC-162t`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
