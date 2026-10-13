# FP 独立 oracle 设计方案（原生浮点）

> **状态**：设计文档（`SPEC-087t` 交付物 10）。
> **范围**：**只出方案，不写实现、不产任何期望值**。
> **铁律**：FP 测试期望值**不得**由 LLVM / QEMU 生成或校准，**必须独立派生自 `spec/`**（同 `tests/vectors/README.md` 的独立 oracle 原则）。

本方案定义「将来如何独立派生出可信 FP 期望值」，是后续 `GOLDEN-*` / `TESTCASES-*` 任务的输入；**本文不含代码、不含任何用例的输入→结果对照**。

---

## 1. 目标与铁律

- 目标：为 `scope: fp` 全部 60 条指令建立**独立于实现**的参考语义模型，用于反哺 LLVM/QEMU 差分验证。
- 铁律：
  - 语义**只**取自 `spec/SimRISC-07` 正文与 `.tao/knowledge/contract-fp.md`（经 `contracts/fp_semantics.yaml` 的 `family → semantics_ref` 分派）。
  - **不得**以 LLVM/QEMU 的任何输出作为语义来源、校准锚点或「对拍通过」依据。
  - spec 未明处（见 §3 末）标 `UNSPECIFIED`，**不臆造**。

## 2. 接口形态（设计层骨架）

```text
tools/golden/fp_ref.py

  eval(insn: str, ops: list[int], state: FCSRState, fmt: str) -> Result
      # insn : contracts/opcodes.yaml 的 id（如 "ftadd_orrr_rf"）
      # ops  : 输入寄存器原始 64 位整数（按 fp_semantics.yaml 的族约定顺序）
      # state: FCSRState(round_mode, flags)（rf0 舍入模式 + 标志初值）
      # fmt  : 目标格式（"ft"=f32 / "fo"=f64 / "int"=整型宽度）
      # Result: 目的寄存器原始 64 位（列表，支持 immu6 块形式）+ 新 FCSRState
```

约束：

- 输入 / 输出均为**原始 64 位整数**，**不依赖宿主 `float` 的四则运算**作为语义来源。
- `FCSRState` 只含 `round_mode`（`rf0[33:32]`）与 `flags`（`rf0[4:0]`）；写回遵循 FCSR 写掩码。
- 分派依据 `contracts/fp_semantics.yaml` 的 `id → family → semantics_ref`：同一接口覆盖 60 条；块形式（`immu6` 连续个数）在接口内逐对调用并按「先读后写」聚合。
- 返回值区分「结果位」与「异常标志」两类，标志按累积语义合并。

## 3. 从 spec 的派生规则

- 族 → spec 章节映射**严格取自** `contracts/fp_semantics.yaml`（`family → semantics_ref` → `contract-fp.md` 锚点），oracle 只实现 contract-fp.md 明文语义。
- 分派要点（各族语义见对应 `contract-fp.md` 锚点）：
  - 转换族（`convert_ff` / `convert_f2i` / `convert_i2f`）：格式/宽度、饱和、舍入、NaN 传播。
  - `arith`：S2D1 先读全部源再写结果；`ftrem`/`forem` 用 IEEE754 remainder（平局取偶）、`ftsclb`/`fosclb` 用 scaleB。
  - `root`：`immu6` 为 `n`，仅 n=2；`rootn(-0, 2)` 标 `UNSPECIFIED`。
  - `sign` / `compare` / `classify` / `cs_rf` / `rf_mem` / `rf_move` / `set_w_rf`：按键位语义与 FCSR 写掩码实现。
- **UNSPECIFIED 清单**（spec 未明，oracle 必须显式标注，不得补默认值）：
  - `convert_f2i` 的 inexact 是否置 NX；
  - `rootn(-0, 2)` 的结果；
  - `ftrem`/`forem`、`ftsclb`/`fosclb` 在除零/Inf/NaN 时的逐位细则（按 IEEE754 处理，但 spec 未逐位展开）。

## 4. 舍入模式（`rf0[33:32]`，最大风险点）

- 宿主 Python `float` 为 IEEE754 双精、仅 RNE；`struct` 打包同样是 RNE。**RTZ / RDN / RUP 无法由宿主 `float` 直接得到**。
- **推荐路径**：纯 Python，以**精确有理数**（`fractions.Fraction` 或自写整数尾数/指数）表示精确结果，再按目标格式（f32/f64）与指定舍入模式**显式舍入并编码**。四种模式统一由一套显式舍入逻辑处理；**不使用宿主 `float` 的运算结果作为语义来源**。
- 备选（记录取舍，本任务不选定实现）：
  1. `decimal`：支持多种舍入，但指数/子正规/标志仍需额外处理。
  2. 引入 softfloat 库：依赖外部库、版本锁定成本高（违反「不引入外部依赖」取向）。
  3. 宿主 `struct` + 手写 guard/sticky：仅 RNE 可靠，其余模式仍须手写。
- 可行性：f32 可行且优先；f64 全模式 + 子正规 + tininess 检测 + UF/NX 判定是难点，需分阶段（见 §7）。

## 5. 标志位（NV/DZ/OF/UF/NX）与 NaN/Inf 传播

- 标志须**累积**到 `rf0[4:0]`（accrued），非仅当条；sNaN → NV + qNaN；浮点→整型饱和 → NV；溢出 → ±Inf + OF；下溢按舍入模式 + UF；inexact → NX。
- NaN/Inf 逐族实现：`convert_ff` 传播 payload、`compare` 的 unordered 编码（qcmp → qNaN / scmp → sNaN，符号位 0）、`sign` 的符号注入与 `rfHD = rf0` 的 `abs()` 特例。
- 非算术类（`sign` / `classify`）不置标志位的约定，按 `contract-fp.md` 各族锚点执行。

## 6. 独立验证方式（自证，不靠 LLVM/QEMU）

- **代数恒等式 / 性质**（不依赖对照实现）：`x + 0 = x`、`x × 1 = x`、各舍入模式下的单调性、`convert_ff` 在可表示范围内的往返、`sgnj` 与符号位的组合恒等式、`classify` 恰一位置位。
- **双路对照（独立实现互证）**：同一语义用两条独立路径计算（精确有理数路径 vs 手写位级路径），在随机输入下断言两者一致——**不引入 LLVM/QEMU**。
- **RNE 交叉锚点**：RNE 结果可与宿主 `struct`（f32）/`float`（f64）对拍，**仅作 RNE 的第三方参照**；其它模式与标志仍靠自证。
- **spec 明文特例**：把 spec 明文给出的特例（如 `rfHD = rf0` 的 `abs()`、`rfHC == rfHD` 的 `copy`/`negate`）作为断言。
- 所有自证**不得**使用 LLVM/QEMU 输出作为语义来源或通过判据。

## 7. 可行性风险与落地任务

- 风险：f64 + 四舍入模式 + 子正规 + UF/NX 的精确判定；`ftrem` 与 `ftsclb` 的边界；NaN payload 逐位传播；`immu6` 块形式的逐对/先读后写顺序；整数宽度（32/64、有/无符号）与饱和边界。
- 建议分期（先窄后宽）：**先 f32、先 RNE、先 arith**，再扩模式与 f64，最后补转换/比较/分类/符号/root 与块形式。
- 建议的后续任务（**本任务只登记，不创建**）：
  - `GOLDEN-001t`：oracle 骨架（`tools/golden/fp_ref.py` 接口 + `FCSRState` + 分派 + 自证 harness；无期望值）。
  - `GOLDEN-002t`：f32 arith + RNE + 标志（自证）。
  - `GOLDEN-003t`：四舍入模式 + f64。
  - `GOLDEN-004t`：转换/比较/分类/符号/root + 块形式。
  - `TESTCASES-0xxt`：FP 覆盖矩阵 + 向量（由 `GOLDEN-*` 独立产出期望值，反哺 LLVM/QEMU 差分）。

## 8. 边界

- 本文档**不含实现**（`tools/golden/**` 不创建代码）、**不含任何期望值或测试向量**。
- oracle 的期望值产出属后续 `GOLDEN-*` 任务；FP 向量/lit、LLVM/QEMU 实现分别属 `TESTCASES-*` / `LLVM-*` / `QEMU-*` / `INTEG-*`。
- 语义真源 = `spec/SimRISC-07` 正文 + `.tao/knowledge/contract-fp.md`；机器可读输入 = `contracts/fp_semantics.yaml`。
