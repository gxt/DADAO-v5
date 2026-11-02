# FP 独立 oracle：实现与边界

> **状态**：设计文档（`SPEC-087t` 交付物 10）。
> **范围**：**只出方案，不写实现、不产任何期望值**。
> **铁律**：FP 测试期望值**不得**由 LLVM / QEMU 生成或校准，**必须独立派生自 `spec/`**（同 `tests/inst/README.md` 的独立 oracle 原则）。

此文档描述当前 oracle 的计算方法与适用边界；指令逐条操作过程见 `components/golden/INSTRUCTION_REFERENCE.md`。期望值只依据仓库 SimRISC 规范及浮点合约，不使用 LLVM/QEMU 生成或校准。

---

## 1. 目标与铁律

- 目标：为 `scope: fp` 全部 66 条指令建立**独立于实现**的参考语义模型，用于反哺 LLVM/QEMU 差分验证。
- 铁律：
  - 语义**只**取自 `spec/SimRISC-07` 正文与 `.tao/contracts/contract-fp.md`（经 `contracts/fp_semantics.yaml` 的 `family → semantics_ref` 分派）。
  - **不得**以 LLVM/QEMU 的任何输出作为语义来源、校准锚点或「对拍通过」依据。
  - spec 未明处（见 §3 末）标 `UNSPECIFIED`，**不臆造**。

## 2. 实现结构

```text
components/golden/fp_ref.py

  arithmetic(op, bits_a, bits_b, format, rounding_mode) -> (result_bits, flags)
  minmax(op, bits_a, bits_b, format) -> (result_bits, flags)
  round_to_integral(bits, format, selector, rounding_mode) -> (result_bits, flags)
  fma(bits_a, bits_b, bits_c, format, rounding_mode) -> (result_bits, flags)
      # formats: F32 / F64; exact finite results use fractions.Fraction
      # flags: NV=1, DZ=2, OF=4, UF=8, NX=16
```

约束：

- 输入 / 输出均为**原始 64 位整数**，**不依赖宿主 `float` 的四则运算**作为语义来源。
- `FCSRState` 只含 `round_mode`（`rf0[33:32]`）与 `flags`（`rf0[4:0]`）；写回遵循 FCSR 写掩码。
- 解释器按 opcode 身份和 `contracts/fp_semantics.yaml` 对应族分派；块形式先快照源，再按递增寄存器号写回。
- 返回值区分「结果位」与「异常标志」两类，标志按累积语义合并。

## 3. 从 spec 的派生规则

- 族 → spec 章节映射**严格取自** `contracts/fp_semantics.yaml`（`family → semantics_ref` → `contract-fp.md` 锚点），oracle 只实现 contract-fp.md 明文语义。
- 分派要点（各族语义见对应 `contract-fp.md` 锚点）：
  - 转换族（`convert_ff` / `convert_f2i` / `convert_i2f`）：格式/宽度、饱和、舍入、NaN 传播。
  - `arith`：S2D1 先读全部源再写结果；`ftrem`/`forem` 用 IEEE754 remainder（平局取偶）、`ftsclb`/`fosclb` 用 scaleB。
  - `root`：`immu6` 为 `n`，仅 n=2；`rootn(-0, 2)` 标 `UNSPECIFIED`。
  - `sign` / `compare` / `classify` / `cs_rf` / `rf_mem` / `rf_move` / `set_w_rf`：按键位语义与 FCSR 写掩码实现。
  - `roundint`：`immu6` 为 one-hot 六档；仅 `0x20` 读 `rf0` 方向，仅结果≠输入时置 NX；零结果保留输入符号。
  - `minmax`：严格 `minimumNumber`/`maximumNumber`；单 NaN 返回数、双 NaN 返回规范 qNaN、sNaN 置 NV；`−0 < +0`。
  - `fma`：精确积与加数求和后单次舍入；`0×Inf` 与异号 Inf 相加置 NV；OF/UF/NX 按单次舍入累积。
- **未裁定清单**（spec 未明，oracle 必须显式标注，不得补默认值）：
  - `convert_f2i` 的 inexact 是否置 NX；
  - `rootn(-0, 2)` 的结果；
  - `ftrem`/`forem`、`ftsclb`/`fosclb` 在除零/Inf/NaN 时的逐位细则（按 IEEE754 处理，但 spec 未逐位展开）。

## 4. 舍入模式（`rf0[33:32]`，最大风险点）

- 对有限 binary32/binary64 输入，先解码成有符号精确有理数。舍入器以整数商和余数显式实现 RNE、RTZ、RDN、RUP，再编码正规数、子正规数、零或无穷，并派生 NX/UF/OF。
- 结果路径不调用宿主 `float` 或 `struct` 计算；格式转换、整数转换及 sqrt 使用同一套精确整数/有理数方法。
- 当前测试覆盖指定的易错边界，不等于对全部输入空间完成穷举或独立形式化证明；语义范围与未裁定输入见 §3 和 §8。

## 5. 标志位（NV/DZ/OF/UF/NX）与 NaN/Inf 传播

- 标志须**累积**到 `rf0[4:0]`（accrued），非仅当条；sNaN → NV + qNaN；浮点→整型饱和 → NV；溢出 → ±Inf + OF；下溢按舍入模式 + UF；inexact → NX。
- NaN/Inf 逐族实现：`convert_ff` 传播 payload、`compare` 的 unordered 编码（qcmp → qNaN / scmp → sNaN，符号位 0）、`sign` 的符号注入与 `rfHD = rf0` 的 `abs()` 特例。
- 非算术类（`sign` / `classify`）不置标志位的约定，按 `contract-fp.md` 各族锚点执行。

## 6. 独立验证方式（自证，不靠 LLVM/QEMU）

- **代数恒等式 / 性质**（不依赖对照实现）：`x + 0 = x`、`x × 1 = x`、各舍入模式下的单调性、`convert_ff` 在可表示范围内的往返、`sgnj` 与符号位的组合恒等式、`classify` 恰一位置位。
- **双路对照（独立实现互证）**：同一语义用两条独立路径计算（精确有理数路径 vs 手写位级路径），在随机输入下断言两者一致——**不引入 LLVM/QEMU**。
- 当前验证使用手工推导的精确值、舍入边界、特殊值和状态标志断言；没有将宿主 `float`、LLVM 或 QEMU 用作 oracle 或校准来源。
- **spec 明文特例**：把 spec 明文给出的特例（如 `rfHD = rf0` 的 `abs()`、`rfHC == rfHD` 的 `copy`/`negate`）作为断言。
- 所有自证**不得**使用 LLVM/QEMU 输出作为语义来源或通过判据。

## 7. 已知风险

- 风险：`fma` 的精确积与单次舍入、`minmax` 的单/双 NaN 与 `±0` 定序、`roundint` 的 one-hot selector 与 NX 条件；f64 + 四舍入模式 + 子正规 + UF/NX 的精确判定；`ftrem` 与 `ftsclb` 的边界；NaN payload 逐位传播；`immu6` 块形式的逐对/先读后写顺序；整数宽度（32/64、有/无符号）与饱和边界。
- 局部测试覆盖格式转换、运算、四舍入、累积标志、比较、分类、RF 存取和范围合法性；并不穷尽全部编码组合和所有 binary32/binary64 输入。

## 8. 边界与当前不足

- 本文档说明已有实现；没有修改或生成 `tests/vectors/` 浮点期望值。
- 本模型可为后续独立向量提供参考，但每条期望值仍须按规范推导并经独立审查。
- 语义真源 = `spec/SimRISC-07` 正文 + `.tao/contracts/contract-fp.md`；机器可读输入 = `contracts/fp_semantics.yaml`。
- **f2i 当前是保守实现**：`convert_to_int` 在 inexact 时抛 `FPGap`（NX 未裁定），会连带拒绝已可确定的整数值；舍入方向与 NaN/Inf/负无符号饱和值仍需与规范/合约对齐（golden 用 `rf0`；QEMU softfloat 对 f2i 用 toward-zero）。
- **FP 没有共享向量**：oracle 差分脚本尚未成为仓库门控；当前 FP 证据是单测、逐身份冒烟和一次性差分，不能替代 `tests/vectors` 回放。
