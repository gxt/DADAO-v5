# DADAO SimRISC 0.5.4 — 浮点（FP）语义合约（scope: fp）

> **版本：0.5.4** [SimRISC-00 §浮点寄存器][SimRISC-07 §版本]

本合约归一化 `scope: fp` **60 条**指令的语义（IEEE754 浮点运算、FCSR 环境、合法性），供后续 golden oracle / LLVM / QEMU / testcases 消费。

- **编码唯一真源**为 `contracts/opcodes.yaml`（本合约不复制编码）。
- **机器可读投影**为 `contracts/fp_semantics.yaml`（60 条 `id→family→spec_cite→semantics_ref→legality_refs`）。
- **合法性规则**见 `contracts/legality_rules.yaml`。
- 本合约**不含任何期望值**；oracle 方案见 `docs/fp-oracle-design.md`。
- 所有语义断言均标注 spec/ 依据（Spec-first，不从 LLVM/QEMU 反推）。

> **族锚点约定**：每族以 `<a id="<族名>">` 声明锚点，供 `contracts/fp_semantics.yaml` 的 `semantics_ref` 机械解析。

---

## §1 全局环境（FCSR 与寄存器模型）<a id="fp-env"></a>

- rf 寄存器字长 64 位；存放单精（ft，32 位）时只使用低 32 位，高 32 位不做特殊规定。[SimRISC-00 §浮点寄存器]
- `rf0` 为 FCSR，同时是 ft/fo 格式的 qNaN：**可作浮点运算的源**、**不可作浮点运算的目的**（作目的 → ILLI）。[SimRISC-00 §浮点寄存器]
- FCSR 位布局：`[63:51]` 只读 qNaN(fo)、`[50:34]` SBZ、`[33:32]` 舍入模式、`[31:22]` 只读 qNaN(ft)、`[21:5]` SBZ、`[4:0]` 异常状态。[SimRISC-00 §浮点状态寄存器]
- 写 `rf0` 只更新 `[33:32]` 与 `[4:0]`；其余位（只读 qNaN 位、SBZ）写无效、保持原值。[SimRISC-00 §浮点状态寄存器]
- 舍入模式 `rf0[33:32]`：`00` RNE（就近取偶）、`01` RTZ（向零）、`10` RDN（向下）、`11` RUP（向上）。[SimRISC-00 §浮点状态寄存器]
- 异常标志 `rf0[4:0]` 按 IEEE754 累积（accrued）：bit0 NV、bit1 DZ、bit2 OF、bit3 UF、bit4 NX。[SimRISC-00 §浮点状态寄存器]
- 浮点格式符合 IEEE754；浮点指令**不触发异常**，始终按 IEEE754 返回结果（NaN/Inf 等）。[SimRISC-00 §浮点状态寄存器]
- `immu6` 双重语义：作**连续个数**（1–63）用于格式转换 / 分类 / RF 多寄存器；作 **n** 用于 `root`（仅 2）。[SimRISC-07 §格式转换指令][SimRISC-07 §S1D1]
- 浮点寄存器只能用于浮点类指令（RF 组）。[SimRISC-00 §浮点寄存器]

---

## §2 `convert_ff`（同/异浮点格式转换）<a id="convert_ff"></a>

- 指令：`ft2ft`/`ft2fo`/`fo2ft`/`fo2fo`（orri：`rfHB` 目的、`rfHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §格式转换指令]
- 源/目的范围可重叠，按序号递增逐对进行，**先读后写**。[SimRISC-07 §格式转换指令]
- 舍入模式由 `rf0[33:32]` 控制。[SimRISC-07 §格式转换指令]
- 浮点→浮点溢出返回 ±Inf 并置 OF；下溢按舍入模式处理并置 UF；NaN 传播 payload；sNaN 作为算术输入置 NV 并返回 qNaN。[SimRISC-07 §格式转换指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §格式转换指令]
- 目的 `rfHB` 为 `rf0` → ILLI。[SimRISC-00 §浮点寄存器]

## §3 `convert_f2i`（浮点→整型）<a id="convert_f2i"></a>

- 指令：`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`（orri：`rdHB` 目的、`rfHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §格式转换指令]
- 浮点→整数转换中 NaN/Inf/超出范围返回整型饱和值（最大/最小）并置 NV。[SimRISC-07 §格式转换指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §格式转换指令]
- 目的为 rd 组（非 rf），不受 rf0 目的约束。[SimRISC-00 §浮点寄存器]
- 精度损失（inexact）是否置 NX：spec 未明，本合约如实记录、不臆造（见 §16 开放点）。[SimRISC-07 §格式转换指令]

## §4 `convert_i2f`（整型→浮点）<a id="convert_i2f"></a>

- 指令：`it2ft`/`io2ft`/`ut2ft`/`uo2ft`/`it2fo`/`io2fo`/`ut2fo`/`uo2fo`（orri：`rfHB` 目的、`rdHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §格式转换指令]
- 整数→浮点转换可能 inexact（精度损失），舍入模式由 `rf0[33:32]` 控制，异常标志按 IEEE754。[SimRISC-07 §格式转换指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §格式转换指令]
- 目的 `rfHB` 为 `rf0` → ILLI。[SimRISC-00 §浮点寄存器]

## §5 `arith`（S2D1 双源单目的运算）<a id="arith"></a>

- 指令：`ftadd`/`ftsub`/`ftmul`/`ftdiv`/`ftrem`/`ftsclb` 与 `foadd`/`fosub`/`fomul`/`fodiv`/`forem`/`fosclb`（orrr：`rfHB` 目的、`rfHC`/`rfHD` 源）。[SimRISC-07 §S2D1]
- 硬件先读全部源操作数再写结果；源被目的覆盖前其值已捕获，行为确定。[SimRISC-07 §S2D1]
- `ftrem`/`forem` 为 IEEE754 remainder（`rfHC − n × rfHD`，n 为最接近 `rfHC/rfHD` 的整数，平局取偶数）；除数为零、Inf 或 NaN 行为遵循 IEEE754。[SimRISC-07 §S2D1]
- `ftsclb`/`fosclb` 为 IEEE754 scaleB：计算 `rfHC × 2^rfHD`（rfHD 取整数值），舍入模式由 rf0 控制；NaN/Inf/溢出/下溢行为遵循 IEEE754。[SimRISC-07 §S2D1]
- 异常标志 NV/DZ/OF/UF/NX 按 IEEE754 设置。[SimRISC-07 §S2D1]
- 目的 `rfHB` 为 `rf0` → ILLI。[SimRISC-00 §浮点寄存器]

## §6 `root`（S1D1 开方）<a id="root"></a>

- 指令：`ftroot`/`foroot`（orri：`rfHB` 目的、`rfHC` 源、`immu6` = n）。[SimRISC-07 §S1D1]
- 实现 `rootn(x, n)`，n 存放在 `immu6`；**仅支持 n=2**，其他 n 值 → ILLI。[SimRISC-07 §S1D1]
- `rootn(-0, 2)` 的运算结果**不做具体要求**。[SimRISC-07 §S1D1]
- 硬件先读源操作数再写结果，行为确定。[SimRISC-07 §S1D1]
- 目的 `rfHB` 为 `rf0` → ILLI。[SimRISC-00 §浮点寄存器]

## §7 `sign`（符号位注入）<a id="sign"></a>

- 指令：`ftsgnj`/`ftsgnn`/`fosgnj`/`fosgnn`（orrr：`rfHB` 目的、`rfHC`/`rfHD` 源）。[SimRISC-07 §浮点符号位操作指令]
- `sgnj` 实现 `copySign(rfHC, rfHD)`：取 rfHC 除符号位外的全部位，与 rfHD 的符号位组合写入 rfHB。[SimRISC-07 §浮点符号位操作指令]
- `sgnn` 取 rfHC 除符号位外的全部位，与 rfHD 符号位**取反**后组合写入 rfHB。[SimRISC-07 §浮点符号位操作指令]
- 特例：`rfHD = rf0` ⇒ `sgnj` = `abs(rfHC)`、`sgnn` = `−abs(rfHC)`；`rfHC == rfHD` ⇒ `sgnj` = `copy(rfHC)`、`sgnn` = `negate(rfHC)`。[SimRISC-07 §浮点符号位操作指令]
- 硬件先读全部源操作数再写结果，行为确定。[SimRISC-07 §浮点符号位操作指令]
- 目的 `rfHB` 为 `rf0` → ILLI。[SimRISC-00 §浮点寄存器]

## §8 `compare`（浮点比较）<a id="compare"></a>

- 指令：`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp`（orrr：`rdHB` 目的、`rfHC`/`rfHD` 源）。[SimRISC-07 §浮点比较指令]
- 结果写入 rdHB：`rfHC > rfHD` → 1、`=` → 0、`<` → −1。[SimRISC-07 §浮点比较指令]
- unordered（含 NaN）：Quiet Compare 返回 qNaN、Signaling Compare 返回 sNaN，**符号位为 0**。[SimRISC-07 §浮点比较指令]
- qNaN/sNaN 按整型解读为**正数**；配合 `cs.*-rf`（SimRISC-02 §浮点条件赋值）的使用约定，可区分 Equal/NotEqual/Less/NotLess/LessEqual/GreaterUnordered 等关系。[SimRISC-07 §浮点比较指令]
- 目的为 rd 组（非 rf），不受 rf0 目的约束。[SimRISC-00 §浮点寄存器]

## §9 `classify`（浮点分类）<a id="classify"></a>

- 指令：`ftcls`/`focls`（orri：`rdHB` 目的、`rfHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §浮点分类指令]
- 对每个源寄存器浮点数据设置对应目的寄存器相应位，其余位清零：`[63:10]` 全部清零，结果仅用 `[9:0]`。[SimRISC-07 §浮点分类指令]
- 10 类位：0 negativeInfinity、1 negativeNormal、2 negativeSubnormal、3 negativeZero、4 positiveZero、5 positiveSubnormal、6 positiveNormal、7 positiveInfinity、8 signalingNaN、9 quietNaN。[SimRISC-07 §浮点分类指令]
- 源/目的范围可重叠，按序号递增逐对进行，**先读后写**。[SimRISC-07 §浮点分类指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §浮点分类指令]

## §10 `cs_rf`（浮点条件赋值）<a id="cs_rf"></a>

- 指令：`cs.n`/`cs.z`/`cs.p`/`cs.eq`/`cs.ne` 的 rf 变体（rrrr）。[SimRISC-02 §浮点条件赋值]
- 第一类 `cs.n`/`cs.z`/`cs.p`：`rdHA` 为负/零/正 ⇒ `rfHB = rfHC`，否则 `rfHB = rfHD`。[SimRISC-02 §浮点条件赋值]
- 第二类 `cs.eq`/`cs.ne`：`rdHA == / != rdHB` ⇒ `rfHC = rfHD`。[SimRISC-02 §浮点条件赋值]
- 目的（`rfHB`/`rfHC`）为 `rf0` → ILLI；源（`rfHC`/`rfHD`）为 `rf0` 合法（读出完整 64 位）。[SimRISC-02 §浮点条件赋值]

## §11 `rf_mem`（RF 存取）<a id="rf_mem"></a>

- 指令：`ld.t`/`st.t`/`ld.o`/`st.o`（rrii，4B/8B）与 `ldm.t`/`stm.t`/`ldm.o`/`stm.o`（rrri，`immu6` 连续个数 1–63）。[SimRISC-01 §存取RF寄存器]
- 对齐：`-t` 需 4 字节对齐、`-o` 需 8 字节对齐；未对齐触发 MALIGN。[SimRISC-01 §存取RF寄存器]
- `rf0` 作**目的**合法（`ld.t`/`ldm.t` 的 `[63:32]` 不变；`ld.o`/`ldm.o` 按 FCSR 写掩码）；作**源**读出完整 64 位。[SimRISC-01 §存取RF寄存器]
- 多寄存器形式 `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-01 §存取RF寄存器]

## §12 `rf_move`（RF↔RD 块赋值）<a id="rf_move"></a>

- 指令：`rd2rf`（orri：`rfHB` 目的、`rdHC` 源、`immu6` 1–63）与 `rf2rd`（orri：`rdHB` 目的、`rfHC` 源、`immu6` 1–63）。[SimRISC-02 §寄存器组之间块赋值]
- 块传输不进行数据类型转换，保持 64 位二进制不变；源/目的范围可重叠、按序先读后写。[SimRISC-02 §寄存器组之间块赋值]
- `rd2rf` 目的 `rf0` **合法**（含 `{rf0:rf0+immu6-1}`，immu6≥2 允许）；`rf2rd` 源 `rf0` 合法（读出完整 64 位）。[SimRISC-02 §寄存器组之间块赋值]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-02 §寄存器组之间块赋值]

## §13 `set_w_rf`（RF 立即数）<a id="set_w_rf"></a>

- 指令：`set.w`（rwii：`rfHA` 目的、`wpN`、`immu16`）。[SimRISC-03 §立即数常数赋值：Immediate constant]
- 只设置 `wpN` 指定的 16 位，其余 48 位不变。[SimRISC-03 §立即数常数赋值：Immediate constant]
- `set.w rf0` **合法**：`wp2` 命中舍入模式、`wp0` 命中异常状态、`wp1`/`wp3` 完全写无效（遵 FCSR 写掩码）。[SimRISC-03 §立即数常数赋值：Immediate constant]

## §14 伪指令（非 60 条 id，仅说明）<a id="pseudo"></a>

- `set.ft`/`set.fo` 不是硬件指令，由汇编器展开为 `set.w` 组合：全零 → `rd2rf {rf}, {rd0}`；寄存器传值 → `rd2rf`/`ft2ft`/`fo2fo`。[SimRISC-03 §set.ft / set.fo 伪指令]
- 伪指令属汇编器展开，**不进** `contracts/opcodes.yaml` 的 60 条。[SimRISC-03 §set.ft / set.fo 伪指令]

## §15 合法性规则映射

- `dst_rf0`：浮点运算指令**目的**为 `rf0` → ILLI（35 条：convert_ff 4 + convert_i2f 8 + arith 12 + root 2 + sign 4 + cs_rf 5）；`rf0` 作源合法。[SimRISC-00 §浮点寄存器]
- `encode_fp_root_n`：`ftroot`/`foroot` 仅 n=2，其他 n → ILLI（2 条）。[SimRISC-07 §S1D1]
- `fp_mreg_zero`：FP `immu6` 连续个数形式 `immu6 = 0` → ILLI（28 条）。[SimRISC-07 §格式转换指令][SimRISC-01 §存取RF寄存器][SimRISC-02 §寄存器组之间块赋值]
- `fp_mreg_range_overflow`：FP `immu6` 连续个数形式起始 + `immu6 > 64` → ILLI，不环绕、不截断（28 条）。[SimRISC-07 §浮点分类指令][SimRISC-01 §存取RF寄存器][SimRISC-02 §寄存器组之间块赋值]
- `rf0` 作目的**例外（合法）**：`rd2rf`、`rf2rd`（源）、`ld.t`/`ldm.t`/`ld.o`/`ldm.o`、`st.*`/`stm.*`（源）、`set.w`。[SimRISC-02 §寄存器组之间块赋值][SimRISC-01 §存取RF寄存器][SimRISC-03 §立即数常数赋值：Immediate constant]
- 上述 4 条 FP 规则在 FP 未实现期均为 `deferred`（`opcodes.yaml` 的 FP 记录 `rule_refs` 为空，规则覆盖由 `check-fp-contract` 的 `legality_refs` 双向核对承担）。[SimRISC-07 §版本]

## §16 开放点（spec 未明，如实记录、不臆造）<a id="open-points"></a>

- `convert_f2i`（浮点→整数）精度损失是否置 NX：spec 仅说明「浮点→整数 NaN/Inf/超范围返回饱和值并置 NV」，未提 NX。[SimRISC-07 §格式转换指令]
- `rootn(-0, 2)`：spec 明确**不做具体要求**。[SimRISC-07 §S1D1]
- `ftrem`/`forem`、`ftsclb`/`fosclb` 的边界（除零/Inf/NaN）按 IEEE754，spec 未给逐位细则。[SimRISC-07 §S2D1]

## §17 oracle 独立派生原则

- FP 测试期望值**必须独立派生自 spec/**，**不得**由 LLVM/QEMU 生成或校准。[SimRISC-07 §版本]
- oracle 只实现 spec 明文语义；spec 未明处（§16）标 `UNSPECIFIED`，不臆造。[SimRISC-07 §版本]
- 本合约（本文）与 `contracts/fp_semantics.yaml` 为 oracle 的稳定输入；oracle 方案见 `docs/fp-oracle-design.md`（本任务不含实现、不含期望值）。[SimRISC-07 §版本]
