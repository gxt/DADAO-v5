# FP 未决语义问题

本报告只收集问题，不选择语义。精确的 `(FP,id,条件)` 投影位于
`contracts/fp_semantics.yaml`；本报告不把机器投影当成人类正文。章节定位均来自
`spec/SimRISC-00`、`01`、`02`、`03`、`07`。

## FP-001
**现象**：同一浮点值写入不同宽度位置后，读回或继续运算可能看到不同的高位。
**受影响指令集合**：浮点格式转换、整数转浮点、浮点算术，以及 `ld/ldm`、`st/stm` 和 `set.w` 的浮点寄存器路径。
**spec 已规定什么**：`SimRISC-07 §格式转换指令`规定转换类别；`SimRISC-01 §浮点数据存取`规定浮点数据存取类别。
**spec 未规定什么**：f32 写入 64 位浮点寄存器时高 32 位是清零、保留旧值还是另有固定值；各写入与后续 FCSR 更新的可观察顺序。
**一个具体可观察例子**：先让目标寄存器高 32 位为非零，再执行产生 f32 的转换；随后以 f64 形式读回，至少有“高位为零”和“高位仍非零”两种结果。
**待裁决问题**：每种写入的目标宽度、写掩码及高位值分别是什么，`st.t` 是否只读 ft 的低 32 位、`st.o` 是否只读 fo 的 64 位？

## FP-002（已裁定）
**裁定**：格式转换的 qNaN 保持 sign 并传播 payload；同格式保持 payload，ft→fo 将 22 位 payload 写入 fo payload 的低 22 位且高 29 位补 0，fo→ft 取低 22 位。该布局使 qNaN 的 `f32→f64→f32` 往返保持相同 sign、quiet 位和 payload。sNaN 使用同一映射后 quiet 化为 qNaN，并产生 NV；qNaN 转换本身不新增异常状态。
**规范落点**：`SimRISC-07 §格式转换指令` 已补入该规则；裁定遵守该节的 payload 传播要求与 IEEE 754 对 signaling NaN 的 invalid/quiet NaN 处理。
**保留边界**：ft 结果写入 RF 的高 32 位仍由 FP-001 裁定；算术/root 的 sNaN、多源 NaN 选择仍由 FP-003 裁定。

## FP-003（已裁定）
**裁定**：S2D1 指令按 `rfHC→rfHD` 选择第一个 NaN，保持其 sign/payload；所选 sNaN quiet 化。任一源为 sNaN 均置 NV，即使结果来自更早的 qNaN；该 NaN 路径不额外置 DZ/OF/UF/NX。rootn 对 qNaN 保持 sign/payload，对 sNaN quiet 化并置 NV。
**规范落点**：`SimRISC-07 §S2D1`、`§S1D1` 已补入该规则；裁定遵守 SimRISC 的 NaN payload 传播要求及 IEEE 754 对 signaling NaN 的 invalid/quiet NaN 处理。
**保留边界**：`rootn(-0,2)` 仍由 FP-010 裁定；f32 RF 高 32 位仍由 FP-001 裁定。

## FP-004（已裁定）
**裁定**：采用 IEEE 754 的 exception flags / accrued status flags 模型。对产生 IEEE 异常的操作，本次异常位集合与指令开始时的 `rf0[4:0]` 按位 OR；同次多个异常均保留、无优先级覆盖；结果与 flags 原子提交。DADAO 无浮点 trap，flags 仅作累积状态记录；显式写 `rf0` 仍按写掩码覆盖相应位。
**规范落点**：`SimRISC-00 §浮点状态寄存器` 已补入该规则；裁定参考 IEEE 754 对 exception flags 与 accrued status flags 的规定。
**受影响指令集合**：产生 IEEE 异常的转换、算术、root、compare 等浮点操作；不将 `set.w rf0`、`rd2rf`/`ld.o` 等显式 FCSR 写入误作异常累积。
**保留边界**：哪些输入产生各异常位、舍入/underflow 细则、NaN 结果规则仍由其他 FP 问题裁定。

## FP-005
**现象**：舍入会改变结果位和异常 flags，但各浮点操作的舍入与异常边界没有闭合。
**受影响指令集合**：浮点格式转换、`add/sub/mul/div/rem/scalb`、`rootn`。
**spec 已规定什么**：`SimRISC-00 §浮点状态寄存器`列出舍入模式；`SimRISC-07 §格式转换指令`、`§S2D1`、`§S1D1`定义操作。
**spec 未规定什么**：RNE/RTZ/RDN/RUP 对中间结果、exact halfway、OF/UF/NX 的逐操作适用范围和更新顺序。
**一个具体可观察例子**：一个不能精确表示的 f64→f32 转换在 RNE 与 RTZ 下结果不同；spec 未明确 NX 是否必置及何时写入。
**待裁决问题**：每类操作的舍入输入、结果位和 OF/UF/NX 触发条件是什么？

## FP-006
**现象**：浮点转整数既有目标 signedness/宽度差异，也可能丢失小数；结果和 NX 不唯一。
**受影响指令集合**：`ft2it/ft2io/ft2ut/ft2uo` 与 `fo2it/fo2io/fo2ut/fo2uo`。
**spec 已规定什么**：`SimRISC-07 §格式转换指令`标出 signed/unsigned 及 tetra/octa 目标。
**spec 未规定什么**：小数如何舍入、越界/NaN/Inf 的整数结果、f32 与 f64 的 NX 条件及结果写宽度。
**一个具体可观察例子**：输入 `-2.5` 转 signed i32；向零和向负无穷取整分别给 `-2` 与 `-3`，且 flags 可能不同。
**待裁决问题**：每个目标宽度和 signedness 的舍入、越界结果、NX/NV 与寄存器写掩码是什么？

## FP-007
**现象**：整数转 f32/f64 时，不能精确表示的大整数需要舍入，但 NX 与结果位未唯一规定。
**受影响指令集合**：`it2ft/it2fo/io2ft/io2fo/ut2ft/ut2fo/uo2ft/uo2fo`。
**spec 已规定什么**：`SimRISC-07 §格式转换指令`规定 signed/unsigned 源和目标格式。
**spec 未规定什么**：舍入模式是否生效、NX 何时置位、f32 结果的高位写入以及超出目标精度时的确切位模式。
**一个具体可观察例子**：把 `2^24+1` 转 f32；结果可为偶数邻居或另一邻居，回读和 NX 都可观察到差异。
**待裁决问题**：按源 signedness、源宽度和目标格式，唯一规定结果位、高位写入和 NX 的规则是什么？

## FP-008（已裁定）
**裁定**：NaN 输入按 FP-003。被除数为 ±Inf 或除数为 ±0 时，返回正 canonical qNaN+NV（ft=`0x7FC00000`，fo=`0x7FF8000000000000`）。有限被除数除以 ±Inf 时原样返回；其中 subnormal 被除数置 UF，其他有限被除数无新增 flags。有限被除数与非零有限除数的 IEEE remainder 精确，零结果的符号取自被除数，不置 DZ/OF/UF/NX。
**规范落点**：`SimRISC-07 §S2D1` 已补入该规则；包含 IEEE 754 原文 `remainder(subnormal, ∞) signals underflow.`。
**保留边界**：f32 结果写入 RF 的高 32 位仍由 FP-001 裁定。

## FP-009（已裁定）
**裁定**：NaN 输入按 FP-003；否则 rfHD 按 rf0 舍入模式转换为整数 N。有限非整数在值改变时置 NX；±Inf 或越界值饱和为最大/最小整数并置 NV，均遵循格式转换指令的浮点→整数规则。N=0 原样返回 rfHC；N≠0 时 `±0→±0`、`±∞→±∞`；有限非零值计算 `x×2^N` 并按 rf0 舍入。转换与缩放 flags 按 FP-004 累积。
**规范落点**：`SimRISC-07 §S2D1` 已补入该规则；`scaleB(±0,N)`、`scaleB(±∞,N)` 的 N≠0 规则采用 IEEE 754，整数 N 的取得沿用 SimRISC 格式转换规则。
**保留边界**：缩放结果的 OF/UF/NX 触发条件仍由 FP-005 裁定；f32 结果写入 RF 的高 32 位仍由 FP-001 裁定。本裁定不关闭独立格式转换指令的 FP-006。

## FP-010（已裁定）
**裁定**：仅支持 n=2；`rootn(±0,2)=+0`、`rootn(+∞,2)=+∞`，均不新增异常状态。`rootn(-∞,2)` 与有限负数返回目标格式的正 canonical qNaN，并置 NV：ft 为 `0x7FC00000`，fo 为 `0x7FF8000000000000`。有限正数按当前舍入模式计算；qNaN/sNaN 按 FP-003。
**规范落点**：`SimRISC-07 §S1D1` 已补入该规则；`±0`、`±∞` 的处理参考 IEEE 754 rootn 规则，并结合 SimRISC 的 n=2 限制。
**保留边界**：有限正数的舍入、NX/UF 等触发条件仍由 FP-005 裁定；ft 结果写入 RF 的高 32 位仍由 FP-001 裁定。

## FP-011（已裁定）
**裁定**：任一 NaN 比较均为 unordered，输入 payload/sign 不传播。ftqcmp/foqcmp 返回目标格式正 canonical qNaN，且仅 sNaN 输入置 NV；ftscmp/foscmp 返回目标格式正 canonical sNaN，任一 NaN 输入均置 NV。ft 结果零扩展写 rd，fo 结果直接写 rd；NaN 比较不置 DZ/OF/UF/NX。
**规范落点**：`SimRISC-00 §浮点状态寄存器`定义 canonical qNaN/sNaN（sNaN 不存于 rf0）；`SimRISC-07 §浮点比较指令`定义 unordered 编码与 NV 规则；NV 按 FP-004 累积。
**保留边界**：rd 写宽度/rd0 legality 与 rf0 别名仍由 FP-012 等问题裁定。

## FP-012（已关闭：既有规则覆盖）
**关闭依据**：SimRISC-00 已定义 rf0 的完整 64 位读出、`[33:32]`/`[4:0]` 的唯一可写掩码及显式写不累积 flags；SimRISC-01/02/03 已分别定义 load/store、`rd2rf`/`rf2rd`、`set.w` 的 rf0 源/目的行为。浮点运算/转换及 `cs.*-rf` 目的为 rf0 触发 ILLI。
**规范落点**：`SimRISC-00 §浮点状态寄存器`、`SimRISC-01 §浮点数据存取`、`SimRISC-02 §寄存器复制`、`SimRISC-03 §16位立即数操作`；不新增独立语义裁定。

## FP-013
**现象**：块操作或重叠源目的区域发生 fault 时，部分读写是否已经生效不明确。
**受影响指令集合**：浮点 `ld/ldm`、`st/stm`，以及 `rd2rf/rf2rd` 块/别名路径。
**spec 已规定什么**：`SimRISC-01 §浮点数据存取`和`SimRISC-02 §寄存器组之间块赋值`定义块操作类别和方向。
**spec 未规定什么**：元素顺序、重叠处理、fault 前已完成元素、地址递增以及读写原子性。
**一个具体可观察例子**：块 store 的第二个元素地址 fault；第一元素是否已写入决定内存可观察状态。
**待裁决问题**：块元素顺序、重叠策略、fault 提交点和部分结果规则是什么？

## FP-014
**现象**：f32 load/store 与 `set.w` 的宽度边界容易被错误地当成 64 位操作。
**受影响指令集合**：`ld.t/ldm.t/st.t/stm.t`、`ld.o/ldm.o/st.o/stm.o`、`set.w`。
**spec 已规定什么**：`SimRISC-01 §浮点数据存取`规定 tetra/octa 存取类别；`SimRISC-03 §Immediate constant`规定 set.w。
**spec 未规定什么**：f32 load 写寄存器高位、f32 store 读取范围、store 是否修改寄存器，以及各类地址/块边界的掩码。
**一个具体可观察例子**：fo 的高 32 位非零时执行 `st.t`；若 store 读取整个 fo，内存会多出不应有的高位字节。
**待裁决问题**：每条 t/o 操作的源读取宽度、目标写掩码和块行为是什么？

## FP-015
**现象**：conditional move 未选中的源是否读取，会影响 NaN、fault 和 FCSR 可观察行为。
**受影响指令集合**：`cs.n/cs.z/cs.p/cs.eq/cs.ne`。
**spec 已规定什么**：`SimRISC-07 §浮点条件赋值`规定条件选择与目标浮点寄存器。
**spec 未规定什么**：未选源是否求值、是否检查其 NaN/fault、源读取顺序及任何 flags 副作用。
**一个具体可观察例子**：条件选择普通值，而未选源是 sNaN；“不读”与“先读并置 NV”产生不同 FCSR。
**待裁决问题**：未选源是否完全不读取？若读取，结果、fault、flags 和顺序是什么？

## FP-016
**现象**：classify 对不同格式、sNaN 和寄存器高位的分类输入范围不清楚。
**受影响指令集合**：`ftcls_orri_rf`、`focls_orri_rf`。
**spec 已规定什么**：`SimRISC-07 §浮点分类指令`规定 classify 操作类别及结果写入。
**spec 未规定什么**：分类只看目标格式有效位还是整个寄存器，sNaN 是否改变 quiet/NV，以及 f32 高位如何处理。
**一个具体可观察例子**：低 32 位是 f32 正零而高 32 位编码 NaN；按低位或整寄存器分类会得到不同类别。
**待裁决问题**：输入有效宽度、NaN 分类、flags 和结果编码的唯一规则是什么？

## FP-017（已关闭：由 FP-003 覆盖）
**关闭依据**：FP-003 已规定 S2D1 按 `rfHC→rfHD` 选择第一个 NaN，保持其 sign/payload；因此 qNaN 与普通值、双 qNaN、qNaN+sNaN 的结果来源和 flags 均已唯一确定。rootn 的唯一 qNaN 输入保持 sign/payload 返回。
**规范落点**：`SimRISC-07 §S2D1`、`§S1D1`；不新增独立语义裁定。
**保留边界**：f32 结果写入 RF 的高 32 位仍由 FP-001 裁定。
