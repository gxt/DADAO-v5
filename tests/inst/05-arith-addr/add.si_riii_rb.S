@@ add.si_riii_rb.S — add.si rbHA, imms18（riii/rb, opc 0x5B）
@@ 大类：05-arith-addr（64 位地址运算，`spec/SimRISC-05 §2`）；册目录 `tests/inst/05-arith-addr/`
@@ id：add.si_riii_rb　形式：riii（rb）　opc：0x5B　mask：0xFF000000　value：0x5B000000　目的银行：RB
@@ 语义：rbHA ← rbHA + SX(imms18)（二进制补码 64 位加法，目的兼源；全 64 位参与、结果完整保留）
@@   加法本身**不做地址截断**；仅当以结果访存时取 rbHA[47:0] 为有效地址，
@@   rbHA[63:48] 是地址计算的高 16 位（= 地址溢出指示）⇒ 运算结果不截断，用例直接比 64 位
@@   立即数有符号（imms18 ∈ [-131072, 131071]），故同一指令也隐含减法
@@ 合法性：目的 rbHA 为 rb0 ⇒ ILLI（`dst_rb0`）；imms18 无「零立即数」禁令（`immu6_zero` 不适用）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：riii = opc | rbha[23:18] | imms18[17:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI_RB` 拼初值；本册复用 04 的数据块）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 3 / boundary 5 / overlap 2（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI_RB` 拼常量（被测指令不参与造初值）、期望内联；
@@   目的在 RB ⇒ 实测经同组 `st.o` 落到 SCRATCH（rb29 指）再 `__CHECK_MEM`

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字 0x5B140001（opc | rb5 | imms18=1）直接执行：钉住 mask/value
	__LI_RB	rb5, 0x0000000000000000
	.dd.t32	0x5B140001
	st.o	rb5, [rb29, 0]
	__CHECK_MEM         1, SCRATCH, 0, 0x0000000000000001

	@@ 字段边界：目的 rb63 + imms18 上界 131071（0x5BFDFFFF = rb63 | 0x1FFFF）
	__LI_RB	rb63, 0x0000000000000000
	.dd.t32	0x5BFDFFFF
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x000000000001FFFF

	@@ ---- semantic ----
	@@ 正立即数：0x64 + 12345
	TEST_AR_RB_SI       3, add.si, rb5, 0x0000000000000064, 12345, 0x000000000000309D

	@@ 负立即数：-1 + (-1)
	TEST_AR_RB_SI       4, add.si, rb5, 0xFFFFFFFFFFFFFFFF, -1, 0xFFFFFFFFFFFFFFFE

	@@ imms18 = 0：原值不变
	TEST_AR_RB_SI       5, add.si, rb5, 0xDEADBEEFCAFEF00D, 0, 0xDEADBEEFCAFEF00D

	@@ ---- boundary ----
	@@ 进位出 2^64：全 1 + 1 = 0
	TEST_AR_RB_SI       6, add.si, rb6, 0xFFFFFFFFFFFFFFFF, 1, 0x0000000000000000

	@@ imms18 上界 131071：低 48 位内进位、高 16 位不变
	TEST_AR_RB_SI       7, add.si, rb6, 0x0000FFFF00000000, 131071, 0x0000FFFF0001FFFF

	@@ imms18 下界 -131072：0 + (-131072) ⇒ 符号扩展后为 0xFFFFFFFFFFFE0000
	TEST_AR_RB_SI       8, add.si, rb6, 0x0000000000000000, -131072, 0xFFFFFFFFFFFE0000

	@@ 地址溢出指示：低 48 位全 1 + 1 ⇒ bits[63:48] = 1（结果**不**截断到 48 位）
	TEST_AR_RB_SI       9, add.si, rb6, 0x0000FFFFFFFFFFFF, 1, 0x0001000000000000

	@@ 跨 bit47 借位（负数立即数）：0x0000800000000000 − 1
	TEST_AR_RB_SI      10, add.si, rb6, 0x0000800000000000, -1, 0x00007FFFFFFFFFFF

	@@ ---- overlap ----
	@@ 目的兼源（riii rb 的定义性质）：连加两次 +5 / -5 回到初值
	__LI_RB	rb7, 0x0000000000000100
	add.si	rb7, 5
	add.si	rb7, -5
	st.o	rb7, [rb29, 0]
	__CHECK_MEM        11, SCRATCH, 0, 0x0000000000000100

	@@ 连加两次移动地址：目的兼源、结果继续作源
	__LI_RB	rb8, 0x0000000000000000
	add.si	rb8, 7
	add.si	rb8, -3
	st.o	rb8, [rb29, 0]
	__CHECK_MEM        12, SCRATCH, 0, 0x0000000000000004

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rb0：目的 rb0 ⇒ ILLI（rb0 读出为当前 IP、只读）
	TEST_FAULT_RB_SI    13, add.si, ILLI, rb0, 1

	__TEST_SECTIONS
