# DADAO SimRISC 0.5.5 — 浮点（FP）语义合约（scope: fp）

> **版本：0.5.5** [SimRISC-00 §浮点寄存器][SimRISC-07 §版本]

本合约归一化 `scope: fp` **66 条**指令的语义（IEEE754 浮点运算、FCSR 环境、合法性），供后续 golden oracle / LLVM / QEMU / testcases 消费。§18 的取整（`ftrnd`/`fornd`）在实现落地后已由 `excluded` 转入 `fp`（`SPEC-162t`），§19 的最小/最大值（`ftmin`/`ftmax`/`fomin`/`fomax`）同样在实现落地后转入 `fp`（`SPEC-160t`），§20 的融合乘加（`ftfma`/`fofma`）亦在实现落地后转入 `fp`（`SPEC-158t`），均计入 66 条。[SimRISC-07 §取整（roundToIntegral）][SimRISC-07 §最小最大值][SimRISC-07 §融合乘加（fusedMultiplyAdd）]

- **编码唯一真源**为 `contracts/opcodes.yaml`（本合约不复制编码）。
- **机器可读投影**为 `contracts/fp_semantics.yaml`（66 条 `id→family→spec_cite→semantics_ref→legality_refs`）。
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
- 异常标志 `rf0[4:0]` 按 IEEE754 累积（accrued、**sticky**：置位后保持到软件清零）：bit0 NV、bit1 DZ、bit2 OF、bit3 UF、bit4 NX；`UF` 仅在结果 **tiny 且 inexact** 时置位（**tininess 检测点 = 舍入后**），`UF ⇒ NX`，反之不成立。[SimRISC-00 §浮点状态寄存器][SimRISC-07 §格式转换指令]
- 浮点格式符合 IEEE754；浮点指令**不触发异常**，始终按 IEEE754 返回结果（NaN/Inf 等）。[SimRISC-00 §浮点状态寄存器]
- `immu6` 双重语义：作**连续个数**（1–63）用于格式转换 / 分类 / RF 多寄存器；作 **n** 用于 `root`（仅 2）。[SimRISC-07 §格式转换指令][SimRISC-07 §S1D1]
- 浮点寄存器只能用于浮点类指令（RF 组）。[SimRISC-00 §浮点寄存器]

---

## §2 `convert_ff`（同/异浮点格式转换）<a id="convert_ff"></a>

- 指令：`ft2ft`/`ft2fo`/`fo2ft`/`fo2fo`（orri：`rfHB` 目的、`rfHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §格式转换指令]
- 源范围与目的范围不可有任何交集（含完全重合），否则 → ILLI（见 `mreg_range_overlap`）；无交集时按序号递增逐对进行，**先读后写**。[SimRISC-07 §格式转换指令]
- 舍入模式由 `rf0[33:32]` 控制。[SimRISC-07 §格式转换指令]
- 浮点→浮点溢出返回 ±Inf 并置 OF；下溢（结果 tiny 且 inexact）按舍入模式处理并置 UF（并置 NX）；NaN 传播 payload；sNaN 作为算术输入置 NV 并返回 qNaN。[SimRISC-07 §格式转换指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §格式转换指令]
- 目的 `rfHB` 为 `rf0` → ILLI。[SimRISC-00 §浮点寄存器]

## §3 `convert_f2i`（浮点→整型）<a id="convert_f2i"></a>

- 指令：`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`（orri：`rdHB` 目的、`rfHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §格式转换指令]
- 浮点→整数转换中 NaN/Inf/超出范围返回整型饱和值（最大/最小）并置 NV。[SimRISC-07 §格式转换指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §格式转换指令]
- 目的为 rd 组（非 rf），不受 rf0 目的约束；但受 `dst_rd0` 约束（目的 `rdHB` 为 `rd0` → ILLI）。[SimRISC-00 §浮点寄存器][SimRISC-00 §数据寄存器]
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
- 目的为 rd 组（非 rf），不受 rf0 目的约束；但受 `dst_rd0` 约束（目的 `rdHB` 为 `rd0` → ILLI）。[SimRISC-00 §浮点寄存器][SimRISC-00 §数据寄存器]

## §9 `classify`（浮点分类）<a id="classify"></a>

- 指令：`ftcls`/`focls`（orri：`rdHB` 目的、`rfHC` 源、`immu6` 连续个数 1–63）。[SimRISC-07 §浮点分类指令]
- 对每个源寄存器浮点数据设置对应目的寄存器相应位，其余位清零：`[63:10]` 全部清零，结果仅用 `[9:0]`。[SimRISC-07 §浮点分类指令]
- 10 类位：0 signalingNaN、1 quietNaN、2 negativeInfinity、3 negativeNormal、4 negativeSubnormal、5 negativeZero、6 positiveZero、7 positiveSubnormal、8 positiveNormal、9 positiveInfinity。[SimRISC-07 §浮点分类指令]
- 来源 `rf`、目的 `rd` 分属不同寄存器组、结构性不可能重叠；分类按序号递增逐对进行，**先读后写**。[SimRISC-07 §浮点分类指令]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-07 §浮点分类指令]
- 目的为 rd 组（非 rf），不受 rf0 目的约束；但受 `dst_rd0` 约束（目的 `rdHB` 为 `rd0` → ILLI）。[SimRISC-00 §浮点寄存器][SimRISC-00 §数据寄存器]

## §10 `cs_rf`（浮点条件赋值）<a id="cs_rf"></a>

- 指令：`cs.n`/`cs.z`/`cs.p` 的 rf 变体（rrrr）。[SimRISC-02 §浮点条件赋值]
- 第一类 `cs.n`/`cs.z`/`cs.p`：`rdHA` 为负/零/正 ⇒ `rfHB = rfHC`，否则 `rfHB = rfHD`。[SimRISC-02 §浮点条件赋值]
- 目的（`rfHB`）为 `rf0` → ILLI；源（`rfHC`/`rfHD`）为 `rf0` 合法（读出完整 64 位）。[SimRISC-02 §浮点条件赋值]

## §11 `rf_mem`（RF 存取）<a id="rf_mem"></a>

- 指令：`ld.t`/`st.t`/`ld.o`/`st.o`（rrii，4B/8B）与 `ldm.t`/`stm.t`/`ldm.o`/`stm.o`（rrri，`immu6` 连续个数 1–63）。[SimRISC-01 §存取RF寄存器]
- 对齐：`-t` 需 4 字节对齐、`-o` 需 8 字节对齐；未对齐触发 MALIGN。[SimRISC-01 §存取RF寄存器]
- `rf0` 作**目的**合法（`ld.t`/`ldm.t` 的 `[63:32]` 不变；`ld.o`/`ldm.o` 按 FCSR 写掩码）；作**源**读出完整 64 位。[SimRISC-01 §存取RF寄存器]
- 多寄存器形式 `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-01 §存取RF寄存器]

## §12 `rf_move`（RF↔RD 块赋值）<a id="rf_move"></a>

- 指令：`rd2rf`（orri：`rfHB` 目的、`rdHC` 源、`immu6` 1–63）与 `rf2rd`（orri：`rdHB` 目的、`rfHC` 源、`immu6` 1–63）。[SimRISC-02 §寄存器组之间块赋值]
- 块传输不进行数据类型转换，保持 64 位二进制不变；`rd2rf`/`rf2rd` 的源与目的分属 RD/RF 不同寄存器组、结构性不可能重叠，按序先读后写。[SimRISC-02 §寄存器组之间块赋值]
- `rd2rf` 目的 `rf0` **合法**（含 `{rf0:rf0+immu6-1}`，immu6≥2 允许）；`rf2rd` 源 `rf0` 合法（读出完整 64 位）。[SimRISC-02 §寄存器组之间块赋值]
- `rf2rd` 目的 `rdHB` 为 `rd0` → ILLI（`dst_rd0`，目的不可为 `rd0`）；`rd2rf` 目的为 rf 组（`rf0` 合法）——「源 `rf0` 合法」与「目的 `rd0` 非法」是两条不同约束。[SimRISC-02 §寄存器组之间块赋值][SimRISC-00 §数据寄存器]
- `immu6 = 0` 或任一起始寄存器 + `immu6 > 64` → ILLI。[SimRISC-02 §寄存器组之间块赋值]

## §13 `set_w_rf`（RF 立即数）<a id="set_w_rf"></a>

- 指令：`set.w`（rwii：`rfHA` 目的、`wpN`、`immu16`）。[SimRISC-03 §立即数常数赋值：Immediate constant]
- 只设置 `wpN` 指定的 16 位，其余 48 位不变。[SimRISC-03 §立即数常数赋值：Immediate constant]
- `set.w rf0` **合法**：`wp2` 命中舍入模式、`wp0` 命中异常状态、`wp1`/`wp3` 完全写无效（遵 FCSR 写掩码）。[SimRISC-03 §立即数常数赋值：Immediate constant]

## §14 伪指令（非 66 条 id，仅说明）<a id="pseudo"></a>

- `set.ft`/`set.fo` 不是硬件指令，由汇编器展开为 `set.w` 组合：全零 → `rd2rf {rf}, {rd0}`；寄存器传值 → `rd2rf`/`ft2ft`/`fo2fo`。[SimRISC-03 §set.ft / set.fo 伪指令]
- 伪指令属汇编器展开，**不进** `contracts/opcodes.yaml` 的 66 条。[SimRISC-03 §set.ft / set.fo 伪指令]

## §15 合法性规则映射

- `dst_rf0`（FP 专属）：浮点运算指令**目的**为 `rf0` → ILLI（41 条：convert_ff 4 + convert_i2f 8 + arith 12 + root 2 + sign 4 + cs_rf 3 + roundint 2 + minmax 4 + fma 2）；`rf0` 作源合法。`rf2rd`/`st.*`/`stm.*`（rf 仅作源、无 rf 目的字段）不适用本规则。[SimRISC-00 §浮点寄存器][SimRISC-01 §存取RF寄存器][SimRISC-02 §浮点条件赋值]
- `encode_fp_root_n`（FP 专属）：`ftroot`/`foroot` 仅 n=2，其他 n → ILLI（2 条）。[SimRISC-07 §S1D1]
- `encode_onehot`（与 `rev.*` 共享）：`roundint` 两条的 `immu6` 非 one-hot（含 `0x00`）→ ILLI（2 条）；六档 one-hot 与 754-2019 六种 `roundToIntegral` 按位序一一对应，复用既有规则、不新增规则。[SimRISC-07 §取整（roundToIntegral）]
- `mreg_zero`（与 M1 共享，同时服务 RD/RB/RA 多寄存器）：FP `immu6` 连续个数形式 `immu6 = 0` → ILLI（28 条）。[SimRISC-07 §格式转换指令][SimRISC-01 §存取RF寄存器][SimRISC-02 §寄存器组之间块赋值]
- `mreg_range_overflow`（与 M1 共享）：FP `immu6` 连续个数形式起始 + `immu6 > 64` → ILLI，不环绕、不截断（28 条）；**源与目的起始寄存器均检查**。[SimRISC-07 §格式转换指令][SimRISC-01 §存取RF寄存器][SimRISC-02 §寄存器组之间块赋值]
- `mreg_range_overlap`（与 M1 共享，M1 侧为 rd2rd/rb2rb）：FP `convert_ff` 四条源范围与目的范围有任何交集（含完全重合）→ ILLI（4 条）；跨组指令（convert_f2i/convert_i2f/classify/rd2rf/rf2rd）结构性不可能重叠。[SimRISC-07 §格式转换指令][SimRISC-02 §寄存器组之间块赋值]
- `dst_rd0`（与 M1 共享）：FP 中目的为 rd 组的 15 条——orri 目的字段 `rdhb`（`convert_f2i` 8 + `classify` 2 + `rf2rd` 1）与 orrr 单目的 `rdhb`（`compare` 4）为 `rd0` → ILLI；目的为 rf 组的 FP 指令（`rd2rf` 等）不适用本规则。[SimRISC-00 §数据寄存器][SimRISC-02 §寄存器组之间块赋值]
- `rf0` 作目的**例外（合法）**：`rd2rf`、`rf2rd`（源）、`ld.t`/`ldm.t`/`ld.o`/`ldm.o`、`st.*`/`stm.*`（源）、`set.w`。[SimRISC-02 §寄存器组之间块赋值][SimRISC-01 §存取RF寄存器][SimRISC-03 §立即数常数赋值：Immediate constant]
- `dst_rf0`/`encode_fp_root_n` 为 FP 专属，FP 已实现（`LLVM-029t/030t`、`QEMU-034t`–`037t`）后均为 `active`；`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`/`dst_rd0` 为 `active` 且与 M1 共享。FP 记录的 `rule_refs` 由 `opcodes.yaml` 依 `legality` 回填，须与 `fp_semantics.yaml` 的 `legality_refs` **逐 id 一致**（`check-fp-contract` Check 8 机械门控）。[SimRISC-07 §版本]

## §16 开放点（spec 未明，如实记录、不臆造）<a id="open-points"></a>

- `convert_f2i`（浮点→整数）精度损失是否置 NX：spec 仅说明「浮点→整数 NaN/Inf/超范围返回饱和值并置 NV」，未提 NX。[SimRISC-07 §格式转换指令]
- `rootn(-0, 2)`：spec 明确**不做具体要求**。[SimRISC-07 §S1D1]
- `ftrem`/`forem`、`ftsclb`/`fosclb` 的边界（除零/Inf/NaN）按 IEEE754，spec 未给逐位细则。[SimRISC-07 §S2D1]

## §17 oracle 独立派生原则

- FP 测试期望值**必须独立派生自 spec/**，**不得**由 LLVM/QEMU 生成或校准。[SimRISC-07 §版本]
- oracle 只实现 spec 明文语义；spec 未明处（§16）标 `UNSPECIFIED`，不臆造。[SimRISC-07 §版本]
- 本合约（本文）与 `contracts/fp_semantics.yaml` 为 oracle 的稳定输入；oracle 方案见 `docs/fp-oracle-design.md`（本任务不含实现、不含期望值）。[SimRISC-07 §版本]

## §18 `roundint`（取整：roundToIntegral 六档）<a id="roundint"></a>

> **范围**：本节 2 条为 `scope: fp`（`QEMU-072t`/`LLVM-125t` 落地后由 `SPEC-162t` 解除 `excluded`、撤销 `decode: ILLI`），计入 `scope: fp` 66 条并投影为 `contracts/fp_semantics.yaml` 的 `family: roundint`；语义在此冻结，供 oracle / LLVM / QEMU / testcases 消费。编码唯一真源仍为 `contracts/opcodes.yaml`（本节不复制编码）。[SimRISC-07 §取整（roundToIntegral）]

- 指令：`ftrnd`/`fornd`（orri：`rfHB` 目的、`rfHC` 源、`immu6` = 取整模式）。`ftrnd` 作用于 ft（32 位，p = 24）、`fornd` 作用于 fo（64 位，p = 53）。[SimRISC-07 §取整（roundToIntegral）]
- `immu6` 为 **one-hot 六档**（恰一位为 1），与 IEEE 754-2019 §5.3.1 的 `roundToIntegral` 六种操作**按位序一一对应**。[SimRISC-07 §取整（roundToIntegral）]
- 档位：`0x01` = `roundToIntegralTiesToEven`（就近取偶，静态）、`0x02` = `roundToIntegralTiesToAway`（就近、平局远离 0，静态）、`0x04` = `roundToIntegralTowardZero`、`0x08` = `roundToIntegralTowardPositive`、`0x10` = `roundToIntegralTowardNegative`、`0x20` = `roundToIntegralExact`（方向读 `rf0[33:32]`）。[SimRISC-07 §取整（roundToIntegral）]
- 5 个静态方向**不受** `rf0[33:32]` 影响；只有 `0x20` 读 `rf0[33:32]`（`00` RNE / `01` RTZ / `10` RDN / `11` RUP）。[SimRISC-07 §取整（roundToIntegral）][SimRISC-00 §浮点状态寄存器]
- **只有 `0x20` 置 NX**（且仅当结果 ≠ 输入）；其余 5 档**不得**置 NX。[SimRISC-07 §取整（roundToIntegral）]
- sNaN 作输入 ⇒ 置 NV、返回 qNaN；qNaN 作输入 ⇒ 返回 qNaN（canonical 化）。[SimRISC-07 §取整（roundToIntegral）]
- `|x| ≥ 2^p` ⇒ **原样返回**（x 已为整数）；**禁止**用「转整数再转回」实现。[SimRISC-07 §取整（roundToIntegral）]
- `±0` 符号位保留（`trunc(-0.5) = -0`、`floor(-0.0) = -0`）；Inf 原样返回；取整**不置** OF/UF；结果格式与输入相同。[SimRISC-07 §取整（roundToIntegral）]
- 目的 `rfHB = rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`。`immu6` 非 one-hot（含 `0x00`）⇒ ILLI（`encode_onehot` 口径，复用既有规则、不新增规则）。[SimRISC-07 §取整（roundToIntegral）][SimRISC-00 §浮点寄存器]
- **已知偏差（`nearbyint`）**：本 ISA **不提供** `nearbyint`（取整但不置 inexact）的硬件变体 ⇒ 后端落 `0x20`（DYN）：**值正确**，但结果 ≠ 输入时 **NX 可能被置位**。可接受性：本 ISA 浮点指令不产生异常/陷阱，NX 仅 `rf0[4:0]` 状态位（软件可忽略）；`roundToIntegral` 族与 `nearbyint` 的**值**语义一致。[SimRISC-07 §取整（roundToIntegral）]
- **`rf0[33:32]` 不扩充**：仅 4 档、无 `roundTiesToAway` ⇒ C23 `fesetround(FE_TONEARESTFROMZERO)` **不支持**（可返回失败，符合 C 标准）；「平局远离 0」仅由静态档 `0x02` 提供。[SimRISC-07 §取整（roundToIntegral）][SimRISC-00 §浮点状态寄存器]

## §19 `minmax`（最小/最大值：`minimumNumber` / `maximumNumber`）<a id="minmax"></a>

> **范围**：本节 4 条为 `scope: fp`（`QEMU-071t`/`LLVM-124t` 落地后由 `SPEC-160t` 解除 `excluded`、撤销 `decode: ILLI`），计入 `scope: fp` 66 条并投影为 `contracts/fp_semantics.yaml` 的 `family: minmax`；语义在此冻结，供 oracle / LLVM / QEMU / testcases 消费。编码唯一真源仍为 `contracts/opcodes.yaml`（本节不复制编码）。[SimRISC-07 §最小最大值]

- 指令：`ftmin`/`ftmax`/`fomin`/`fomax`（orrr：`rfHB` 目的、`rfHC`/`rfHD` 源）；`ft*` 作用于 ft（32 位）、`fo*` 作用于 fo（64 位）。硬件先读全部源再写结果，源与目的允许重叠。[SimRISC-07 §最小最大值]
- 语义 = IEEE 754-2019 §9.6 `minimumNumber`/`maximumNumber`（**严格版**，与 RISC-V `FMIN.S`/`FMAX.S` 逐条一致）：`x < y` ⇒ `min` 取 x、`max` 取 y；`y < x` ⇒ 反之。[SimRISC-07 §最小最大值]
- `−0 < +0`：`min(+0, −0) = −0`、`max(+0, −0) = +0`；**不得**把 `±0` 视为"相等而任选"。[SimRISC-07 §最小最大值]
- `x == y` 且同号（含 `+0/+0`、`−0/−0`、相同位型）⇒ 返回任一操作数（位型相同，结果唯一）。[SimRISC-07 §最小最大值]
- 单 NaN（一个为 NaN、另一个为数；qNaN 与 **sNaN** 同论）⇒ 返回**那个数**（不传播 NaN）。[SimRISC-07 §最小最大值]
- 双 NaN（任意 qNaN/sNaN 组合）⇒ 返回 **canonical quiet NaN**（IEEE 754-2019 §6.2：符号位 0、payload 全零 ⇒ ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。[SimRISC-07 §最小最大值]
- 标志：**sNaN** 作输入 ⇒ 置 **NV**（即使结果为数字）；qNaN 作输入不置；**不涉舍入、不置 NX**；不置 OF/UF。Inf 按数值序参与比较（`min(+Inf, x) = x`、`max(−Inf, x) = x`）。[SimRISC-07 §最小最大值]
- 目的 `rfHB = rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`（读出 FCSR 中的 qNaN）。[SimRISC-07 §最小最大值][SimRISC-00 §浮点寄存器]
- **负向约束**：不得实现为「返回第二操作数」（x86 `minss`/`maxss` 遗留语义），也不得按 754-2008 `minNum`/`maxNum` 的宽松处实现；不提供 NaN 传播版 `minimum`/`maximum` 硬件形态（由 LLVM 从本条展开，`LLVM-124t`），不做 `*mag` 变体、不做整数 min/max。[SimRISC-07 §最小最大值]

## §20 `fma`（融合乘加：`fusedMultiplyAdd`）<a id="fma"></a>

> **范围**：本节 2 条（`ftfma`/`fofma`）为 `scope: fp`（`QEMU-070t`/`LLVM-123t` 落地后由 `SPEC-158t` 解除 `excluded`、撤销 `decode: ILLI`），计入 `scope: fp` 66 条并投影为 `contracts/fp_semantics.yaml` 的 `family: fma`。语义在此冻结，供 oracle / LLVM / QEMU / testcases 消费。编码唯一真源仍为 `contracts/opcodes.yaml`（本节不复制编码）。`spec_cite`：`SimRISC-07: ftfma`、`SimRISC-07: fofma`。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]

- 指令：`ftfma`/`fofma`（`rrrr`：`rfHA` 目的、`rfHB`/`rfHC`/`rfHD` 源）；`ftfma` 作用于 ft（32 位，p = 24）、`fofma` 作用于 fo（64 位，p = 53）。语义 = IEEE 754-2019 `fusedMultiplyAdd(rfHB, rfHC, rfHD)`，即 `rfHA ← rfHB × rfHC + rfHD`。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- **单次舍入**：精确积 `rfHB × rfHC`（不先舍入）与 `rfHD` 相加，精确和**只舍入一次**（舍入模式 `rf0[33:32]`）；**不等价于** `ftmul`/`fomul` + `ftadd`/`foadd`（后者在积处多舍入一次）。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- 反例（ft）：`a = 1 + 2⁻²³`、`b = 1 − 2⁻²³`、`c = −1` ⇒ `fma(a,b,c) = −2⁻⁴⁶`（`0xA880_0000`），而 `mul` 后 `add` 得 `+0`。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- 硬件**先读**三个源再写结果；目的 `rfHA` 允许与任一源重叠（行为确定）。乘法可交换（`rfHB`/`rfHC` 互换结果不变），`rfHD` 不可互换。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- NaN：qNaN ⇒ 返回 qNaN（canonical 化）；**sNaN ⇒ 置 NV**、返回 qNaN。`0 × ±Inf` ⇒ **NV** + qNaN（即使 `rfHD` 为 qNaN 也置 NV）。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- Inf：`±Inf × 有限非零数` ⇒ 同号 Inf；`Inf + (−Inf)`（积与加数异号）⇒ **NV** + qNaN；同号 ⇒ 该 Inf。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- 精确和为零 ⇒ 依 IEEE 754-2019 §6.3 零符号规则（RDN ⇒ `−0`，其余 ⇒ `+0`）。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- 标志：溢出 ⇒ `±Inf` + **OF**；下溢 ⇒ 次正规数或 `±0` + **UF**；**NX 最多置一次**；不触发陷阱，只累积 `rf0[4:0]`。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
- 目的 `rfHA = rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`（读出 FCSR 中的 qNaN）；**不采用**双目的形态（无 `dst_dual_same`）。[SimRISC-07 §融合乘加（fusedMultiplyAdd）][SimRISC-00 §浮点寄存器]
- **负向约束**：不提供 `fmsub`/`fnmadd`/`fnmsub` 独立编码；`a × b − c` 等形态用 `ftsgnn`/`fosgnn` 对 `rfHD` 取负后执行本族（符号位取反逐位精确、不涉舍入）。[SimRISC-07 §融合乘加（fusedMultiplyAdd）]
