# FP 未决语义候选方案

以下方案均是待裁定提案，尚未成为已接受语义。选择后才可据此更新 contract、独立
oracle、LLVM、QEMU 和 vectors；机器投影仍保留逐 id/条件关联。

## FP-001
**候选 A**：按目标格式写入，f32 清零高 32 位，store 只读其目标宽度；优点是边界简单，代价是改变 rf0/旧值观察，需更新 contract、oracle、组件和宽度向量。
**候选 B**：窄写保留高位，store 仍只读目标宽度；优点是保留旧实现兼容性，代价是寄存器状态依赖历史，四层实现和回读向量都要明确。
**候选 C**：窄写产生固定扩展模式并让 store 严格按格式取值；优点是可重复，代价是新增编码规则、contract 字段及全套回归向量。
**后续影响**：选择 A/B/C 都要同步 contract 与独立 oracle；LLVM/QEMU 按同一写掩码实现，vectors 增加高位回读和 t/o store 用例。

## FP-002
**候选 A**：保留 sign，quiet sNaN，按目标格式截取/补位 payload；优点是信息保留，代价是实现和 oracle 需格式化 payload 规则。
**候选 B**：所有 NaN 转成目标格式固定 canonical qNaN；优点是跨格式一致，代价是丢失 sign/payload，需更新 contract、组件和 NaN 向量。
**候选 C**：保留 payload 但固定 sign；优点是诊断信息适中，代价是与 A 不同且需单独验证 quiet/NV。
**后续影响**：contract/oracle 要记录 payload、sign、quiet 和 NV；LLVM/QEMU 的转换路径及 NaN vectors 必须采用同一候选。

## FP-003
**候选 A**：按操作数顺序选第一 NaN，quiet sNaN，保留 sign/payload，并为 sNaN 置 NV；优点是可追踪，代价是每个二元操作需统一双源逻辑。
**候选 B**：sNaN 优先，结果 canonical qNaN，NV 只由 sNaN 触发；优点是异常规则醒目，代价是丢失 payload，contract/oracle/组件需同步。
**候选 C**：单源操作保留 NaN 信息，双源操作 canonical 化；优点是实现分层，代价是规则不对称、向量数量增加。
**后续影响**：contract/oracle 要按单源和双源分支；LLVM/QEMU 需一致实现，vectors 覆盖源交换与 sNaN/qNaN 混合。

## FP-004
**候选 A**：一次操作先计算完整结果，再以 OR 合并所有新 flags，最后原子提交结果和 FCSR；优点是容易复现，代价是需明确异常集合。
**候选 B**：按规定优先级逐项提交 flags，结果提交后再更新 FCSR；优点是可表达优先级，代价是时序更复杂，LLVM/QEMU 需同步。
**候选 C**：异常只保留最高优先级；优点是状态简单，代价是丢失并发异常信息，contract 与 oracle 需重写。
**后续影响**：contract/oracle 固定 flags 合并和时序；LLVM/QEMU 更新 FCSR 提交点，vectors 加旧 flags 与多异常组合。

## FP-005
**候选 A**：所有可舍入操作使用 FCSR rounding_mode，按 IEEE 类似的 exact/inexact 判定并 OR OF/UF/NX；优点是统一，代价是需为边界建立独立 oracle。
**候选 B**：仅格式转换和算术使用 rounding_mode，特殊值走固定结果；优点是实现范围清楚，代价是操作族间规则不同。
**候选 C**：结果采用固定 RNE，rounding_mode 只记录不影响结果；优点是组件简单，代价是放弃状态字段语义，需改 contract 和 vectors。
**后续影响**：contract/oracle 明确模式是否生效；LLVM/QEMU 的舍入实现与 vectors 的 halfway、OF/UF/NX 期望必须同步。

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

## FP-008
**候选 A**：特殊 rem 返回格式 canonical qNaN，非法零/无穷组合置 NV，有限结果保留被除数零符号；优点是边界闭合，代价是新增 NaN/符号表。
**候选 B**：按数学 remainder 规则扩展特殊值，Inf/0 等全部返回 qNaN 并置 NV；优点是统一，代价是仍需明确每种零符号。
**候选 C**：对特殊输入保持一个操作数或返回零；优点是硬件路径短，代价是非直观，contract/oracle 必须明确逐组合结果。
**后续影响**：contract/oracle 加入 rem 特殊值表；LLVM/QEMU 统一零符号和 NV，vectors 覆盖零、Inf、NaN 及除零组合。

## FP-009
**候选 A**：有限 scale 先按 rounding_mode 缩放，特殊组合按固定 qNaN/Inf/zero 表处理并设置 OF/UF/NX；优点是可测，代价是表较大。
**候选 B**：scale 只接受有限整数语义，非有限 scale 返回 canonical qNaN+NV；优点是边界清晰，代价是拒绝更多输入。
**候选 C**：沿用通用乘幂模型，特殊值遵循统一 NaN/Inf 传播；优点是与算术共用 oracle，代价是零符号和下溢仍需补充规则。
**后续影响**：contract/oracle 固定 scale 解释和 flags；LLVM/QEMU 复用或新增 scalb 路径，vectors 覆盖非有限 scale 与 OF/UF/NX。

## FP-010
**候选 A**：偶次根对负零返回正零，负有限数返回 canonical qNaN+NV；优点是数学直观，代价是需固定 rootn 特殊值表。
**候选 B**：保留零符号，负数仍按 sign 规则产生 qNaN+NV；优点是符号信息保留，代价是与 A 的 `-0` 不同。
**候选 C**：奇偶次数分别采用实数根规则，非实结果保持输入 sign 的 NaN；优点是统一符号路径，代价是 NaN 位形需另定。
**后续影响**：contract/oracle 固定次数、零符号和 NaN；LLVM/QEMU 的 rootn 实现及 vectors 必须逐格式覆盖特殊输入。

## FP-011
**候选 A**：无序比较返回固定无序编码；sNaN 置 NV，qNaN 不置 NV；优点是区分两种 NaN，代价是比较器和 oracle 需分类。
**候选 B**：任意 NaN 都返回同一无序编码并置 NV；优点是简单，代价是 qNaN 也产生副作用。
**候选 C**：NaN 比较返回 false 编码且不置 NV；优点是条件使用方便，代价是丢失异常可见性，需改 FCSR 期望。
**后续影响**：contract/oracle 固定无序编码和 NV；LLVM/QEMU compare lowering 与 vectors 的 qNaN/sNaN 期望同步。

## FP-012
**候选 A**：rf0 的 FCSR 字段使用专用读写掩码，浮点别名只触及允许位；优点是状态安全，代价是实现需分流访问。
**候选 B**：rf0 作为普通 64 位寄存器读写，再由 FCSR 解释字段；优点是路径统一，代价是 SBZ/只读字段可能被污染。
**候选 C**：禁止会同时触碰 rf0/FCSR 的别名组合；优点是无歧义，代价是新增 legality、LLVM/QEMU 拒绝路径和向量。
**后续影响**：contract 增加字段/legality，oracle 拒绝非法组合；LLVM/QEMU 增加同一诊断，vectors 验证合法与拒绝路径。

## FP-013
**候选 A**：块操作按地址递增，逐元素提交，fault 后保留已完成元素；优点是可恢复，代价是 partial-state oracle 和 fault 向量。
**候选 B**：块操作先检查全范围，成功后原子提交；优点是状态简单，代价是需要范围检查，组件实现更复杂。
**候选 C**：按寄存器顺序处理重叠区域，未完成部分回滚；优点是确定，代价是需要临时缓冲和明确回滚语义。
**后续影响**：contract/oracle 固定顺序、部分提交或回滚；LLVM/QEMU 的块路径和 vectors 必须覆盖 overlap 与 fault。

## FP-014
**候选 A**：t 操作严格 32 位、o 操作严格 64 位；窄 load 清高位，窄 store 只读低 32 位；优点是边界直观，代价是更新所有宽度向量。
**候选 B**：窄 load 保留高位但窄 store 仍只写低 32 位；优点是减少寄存器破坏，代价是状态历史可见。
**候选 C**：所有浮点存取统一 64 位容器并由格式字段解释；优点是实现统一，代价是内存宽度和 contract 复杂，需改后续组件。
**后续影响**：contract/oracle 固定容器与内存宽度；LLVM/QEMU 的 load/store 及 vectors 必须同步高位和字节掩码规则。

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

## FP-017
**候选 A**：二元操作按左到右取第一 NaN，root 取唯一 NaN；保留 sign/payload、置 quiet，qNaN 不新增 flags；优点是可追踪，代价是需按 ft/fo 截取/补位。
**候选 B**：任一 qNaN 结果 canonical 化；双 qNaN 不依赖源顺序，优点是跨操作一致，代价是丢失 payload，contract/oracle/组件和 vectors 都要固定 canonical 位形。
**候选 C**：sNaN 优先、qNaN 次之，结果保留被选源 payload；优点是异常优先级明确，代价是 qNaN+sNaN 与双 qNaN 要分别编码，后续规则最多。
**后续影响**：contract/oracle 固定双源优先级、格式位形和 flags；LLVM/QEMU 算术/root 路径与 vectors 覆盖交换、双 qNaN 和混合 NaN。
