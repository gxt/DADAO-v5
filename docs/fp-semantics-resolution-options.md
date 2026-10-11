# FP 未决语义候选方案

以下方案均是待裁定提案，尚未成为已接受语义。选择后才可据此更新 contract、独立
oracle、LLVM、QEMU 和 vectors；机器投影仍保留逐 id/条件关联。

## FP-001
**候选 A**：按目标格式写入，f32 清零高 32 位，store 只读其目标宽度；优点是边界简单，代价是改变 rf0/旧值观察，需更新 contract、oracle、组件和宽度向量。
**候选 B**：窄写保留高位，store 仍只读目标宽度；优点是保留旧实现兼容性，代价是寄存器状态依赖历史，四层实现和回读向量都要明确。
**候选 C**：窄写产生固定扩展模式并让 store 严格按格式取值；优点是可重复，代价是新增编码规则、contract 字段及全套回归向量。
**后续影响**：选择 A/B/C 都要同步 contract 与独立 oracle；LLVM/QEMU 按同一写掩码实现，vectors 增加高位回读和 t/o store 用例。

## FP-002（已裁定：细化原候选 A）
**采用规则**：qNaN 保持 sign；同格式保持 payload，ft→fo 将 payload 放入 fo payload 的低 22 位并将高 29 位清零，fo→ft 取低 22 位。选择低位布局是为保证 qNaN `f32→f64→f32` 往返保持相同 sign、quiet 位和 payload。sNaN 使用同一映射、quiet 化为 qNaN 并置 NV；qNaN 转换不新增 flags。
**依据**：SimRISC-07 的 NaN payload 传播要求；IEEE 754 的 signaling NaN invalid/quiet NaN 处理。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 NaN 转换向量必须采用该映射；ft 结果的 RF 高 32 位仍依赖 FP-001。

## FP-003（已裁定：原候选 A）
**采用规则**：S2D1 按 `rfHC→rfHD` 取第一 NaN，保持 sign/payload，所选 sNaN quiet 化；任一源为 sNaN 均置 NV，即使结果来自更早 qNaN。rootn 保持 qNaN 的 sign/payload，或 quiet 化 sNaN 并置 NV。NaN 路径不额外置 DZ/OF/UF/NX。
**依据**：SimRISC-07 的 NaN payload 传播要求；IEEE 754 对 signaling NaN 的 invalid/quiet NaN 处理。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖源交换、qNaN+sNaN、sNaN+qNaN、双 sNaN 与 rootn sNaN；`rootn(-0,2)` 仍属 FP-010。

## FP-004（已裁定：原候选 A）
**采用规则**：一次操作先依据其各自语义计算完整结果与本次 IEEE exception flags 集合，再将该集合与旧 `rf0[4:0]` 按位 OR，并与结果原子提交；同次多个异常位均保留，无优先级覆盖。
**依据**：IEEE 754 的 exception flags / accrued status flags 模型；DADAO 浮点无 trap。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须采用该累积/提交规则；各异常的触发条件与 NaN/舍入细则仍按其对应未决问题处理。

## FP-005（已裁定：细化原候选 A）
**采用规则**：以精确结果为输入、按指令开始时 FCSR rounding_mode 单次正确舍入；RNE halfway 取偶。结果不精确置 NX；溢出且舍入置 OF+NX；tininess 在舍入后检测，通常的 tiny 且不精确结果置 UF+NX。NaN/无穷/invalid/divide-by-zero 等指令特例优先。
**依据**：IEEE 754 的定向舍入、overflow、underflow、inexact 与 tininess-after-rounding 模型；FP-004 的 accrued flags 规则。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖四种舍入模式、halfway、OF、舍入后 tiny/zero 及 NX；FP-008 remainder 特例、FP-009 指数转换、FP-006/007 保持各自规则。

## FP-006
**候选 A**：按 rounding_mode 舍入到零/无穷等，越界与 NaN/Inf 写目标格式的固定 sentinel，并分别置 NV/NX；优点是结果总可观察，代价是需逐 signedness 定义 sentinel。
**候选 B**：整数转换截断小数，越界饱和到目标边界，NX 表示丢小数；优点是软件友好，代价是与异常型转换不同。
**候选 C**：越界和 NaN 只置 NV，目标寄存器保持未定义但由 contract 标记；优点是硬件自由度大，代价是 oracle 不能比较结果位，后续向量受限。
**后续影响**：contract/oracle 需表达 sentinel 或不可比较结果；LLVM/QEMU 对 signedness、宽度和 flags 对齐，vectors 只能验证可定义部分。

## FP-007
**候选 A**：按 FCSR 舍入模式转目标格式，无法精确表示即置 NX，并按 FP-001 的目标写掩码；优点是与 f2i 对称，代价是需完整位级 oracle。
**候选 B**：整数转浮点固定 RNE，NX 仅在丢失有效位时置位；优点是常见实现简单，代价是 rounding_mode 影响范围缩小。
**候选 C**：固定向零并保留可表示邻居；优点是确定，代价是数值偏差，LLVM/QEMU 和向量均需采用该规则。
**后续影响**：contract/oracle 固定舍入和 NX；LLVM/QEMU 的整数转浮点 lowering 与各 signedness/宽度 vectors 必须一致。

## FP-008（已裁定：细化原候选 A）
**采用规则**：非 NaN invalid（±Inf 被除数或 ±0 除数）返回目标格式正 canonical qNaN+NV；有限被除数/±Inf 原样返回，且 subnormal 被除数置 UF；有限非零除数的 remainder 精确，零结果保留被除数符号，不置 DZ/OF/UF/NX。NaN 输入按 FP-003。
**依据**：IEEE 754 remainder 定义与原文 `remainder(subnormal, ∞) signals underflow.`；FP-003 NaN 传播及 FP-004 累计 flags 规则。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖 ±0 除数、±Inf 被除数、有限值/±Inf（含 subnormal）和零结果符号。

## FP-009（已裁定：细化原候选 A）
**采用规则**：先按 FP-003 处理 NaN；再将 scale 源按 rf0 舍入为整数 N。有限非整数的值改变置 NX；±Inf/越界饱和为最大/最小整数并置 NV。N=0 返回原 rfHC；N≠0 时保留零和无穷的符号，有限非零值按 `x×2^N` 缩放并按 rf0 舍入。
**依据**：SimRISC-07 格式转换的浮点→整数饱和规则；IEEE 754 scaleB 对 N=0、N≠0 时 ±0/±∞ 的规则；FP-003 和 FP-004。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖非整数 N、±Inf/越界 N、N=0 及 `±0/±∞` 被缩放数；缩放 OF/UF/NX 边界仍依赖 FP-005。

## FP-010（已裁定：细化原候选 A）
**采用规则**：仅允许 n=2；`±0→+0`、`+∞→+∞`，均无新增 flags；`-∞` 与有限负数→目标格式正 canonical qNaN+NV（ft=`0x7FC00000`，fo=`0x7FF8000000000000`）。有限正数按当前舍入模式，NaN 输入按 FP-003。
**依据**：IEEE 754 rootn 对 `±0`、`±∞` 和偶次根 invalid 的规则；SimRISC-07 的 n=2 限制与 rf0 qNaN 定义。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖 `±0`、`±∞`、有限负数及两种格式；舍入/NX/UF 仍依赖 FP-005。

## FP-011（已裁定：细化原候选 A）
**采用规则**：任一 NaN 为 unordered；qcmp 返回正 canonical qNaN，只有 sNaN 输入置 NV；scmp 返回正 canonical sNaN，任一 NaN 输入置 NV。ft 的 32 位 NaN 零扩展写 rd，fo 的 64 位 NaN 直接写 rd；不传播输入 payload/sign，不置 DZ/OF/UF/NX。
**依据**：IEEE 754 quiet/signaling comparison 的 invalid 规则；SimRISC-00 的 canonical NaN 格式常量；FP-004 累计 flags 规则。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖 qcmp/scmp、qNaN/sNaN、源交换以及 ft/fo 的 rd 编码。

## FP-012（已关闭：既有规则覆盖）
**采用规则**：不新增独立规则；采用 SimRISC-00 的 rf0 写掩码和显式写语义，以及 SimRISC-01/02/03 对 load/store、寄存器复制和 `set.w` 的路径规则。
**关闭理由**：原候选 A 已由现有规范实现：rf0 读出完整 64 位，显式写仅更新 FCSR 可写字段，浮点结果路径与 rf0 目的的 legality 已单独明确。
**后续影响**：contract、oracle、组件和 vectors 按既有章节覆盖 rf0 的完整读取、掩码写入、低 32 位 load 及 ILLI 路径；不新增 FP-012 专属实现要求。

## FP-013
**候选 A**：块操作按地址递增，逐元素提交，fault 后保留已完成元素；优点是可恢复，代价是 partial-state oracle 和 fault 向量。
**候选 B**：块操作先检查全范围，成功后原子提交；优点是状态简单，代价是需要范围检查，组件实现更复杂。
**候选 C**：按寄存器顺序处理重叠区域，未完成部分回滚；优点是确定，代价是需要临时缓冲和明确回滚语义。
**后续影响**：contract/oracle 固定顺序、部分提交或回滚；LLVM/QEMU 的块路径和 vectors 必须覆盖 overlap 与 fault。

## FP-014（已裁定：候选 B）
**采用规则**：t 操作严格读写 32 位，load 保持 RF 高 32 位，store 仅读 RF 低 32 位；o 操作严格读写完整 64 位。所有 store 不修改 RF，块指令逐元素采用相同宽度；`set.w` 保持其选定 16 位替换语义。
**依据**：SimRISC-03 的 `set.w` 保持其余 48 位规则；rf0 的 t-load 高 32 位保持规则；tetra/octa 的 32/64 位格式定义。
**后续影响**：contract、独立 oracle、LLVM、QEMU 和 vectors 均须覆盖 t-load 高位保持、t-store 忽略高位、o 操作全宽及 rf0 路径；动态 fault 仍归 FP-013。

## FP-015
**候选 A**：只读取被选源，未选源不产生 NaN、fault 或 flags；优点是条件选择可短路，代价是实现需保证惰性。
**候选 B**：先读取两个源，再选择结果；优点是数据通路统一，代价是未选 sNaN/fault 可见，需增加 flags/异常规则。
**候选 C**：读取两个源但只对被选源产生 flags；优点是兼顾固定读取路径，代价是 oracle 与 QEMU 时序需明确。
**后续影响**：contract/oracle 记录读取与 flags 的分离；LLVM/QEMU 保持同一副作用，vectors 增加未选 sNaN/fault 用例。

## FP-016
**候选 A**：只按 ft/fo 有效位分类，sNaN 单独分类且不 quiet、不置 NV；优点是 classify 无副作用，代价是高位必须清零/忽略。
**候选 B**：sNaN 分类同时置 NV，其他分类无副作用；优点是异常可见，代价是 classify 不再纯读。
**候选 C**：按完整寄存器位模式分类；优点是保留所有位信息，代价是 f32 高位影响结果，需与 load/write 规则联动。
**后续影响**：contract/oracle 固定有效位和分类编码；LLVM/QEMU classify 与 vectors 必须同 FP-001/014 的高位规则联动。

## FP-017（已关闭：由 FP-003 覆盖）
**采用规则**：不新增独立规则；采用 FP-003 的 S2D1 第一 NaN 源顺序、sign/payload 保持和任一 sNaN 置 NV 规则，以及 rootn 的唯一 NaN 传播规则。
**关闭理由**：原候选 A 已被 FP-003 作为算术/root 的统一 NaN 规则采纳，qNaN 的单独问题无剩余语义。
**后续影响**：contract、oracle、组件和 vectors 按 FP-003 覆盖源交换、双 qNaN 与 qNaN/sNaN 混合；不新增 FP-017 专属实现要求。
