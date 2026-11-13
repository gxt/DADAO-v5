@@ sub.o_orrr_dbb.S — sub.o rdHB, rbHC, rbHD（orrr/dbb, opc 0x40, ha 0x33）
@@ 大类：05-arith-addr（64 位地址运算，`spec/SimRISC-05 §1`）；册目录 `tests/inst/05-arith-addr/`
@@ id：sub.o_orrr_dbb　形式：orrr（dbb）　opc：0x40　ha：0x33　mask：0xFFFC0000　value：0x40CC0000
@@ 目的银行：RD（rdHB）；两源都在 RB（rbHC、rbHD）；scope m3（`contracts/opcodes.yaml`）
@@ 语义：rdHB ← rbHC − rbHD（二进制补码 64 位减法，全 64 位参与、结果完整保留 64 位）
@@   单条、无 `.s`/`.u` 变体（64 位单目的结果的位型与符号性无关）；不做地址截断
@@ 合法性：目的 rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[17:16] | rdhb[17:12] | rbhc[11:6] | rbhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI_RB` 拼初值；本册复用 04 的数据块）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 2（链例 13 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI_RB` 拼常量（被测指令不参与造初值）、期望内联；目的在 rd ⇒ `__CHECK_RD`

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字 0x40CC5187（opc/ha | rd5 | rb6 | rb7）直接执行：钉住 mask/value
	__LI_RB	rb6, 0x0000000000000064
	__LI_RB	rb7, 0x000000000000001E
	.dd.t32	0x40CC5187
	__CHECK_RD          1, rd5, 0x0000000000000046

	@@ 字段边界：目的/两源都是最大寄存器（0x40CFFFFF = rd63 | rb63 | rb63）
	__LI_RB	rb63, 0x0F1E2D3C4B5A6978
	.dd.t32	0x40CFFFFF
	__CHECK_RD          2, rd63, 0x0000000000000000

	@@ ---- semantic ----
	@@ 大数 − 大数
	TEST_AR_DBB         3, sub.o, rd5, rb6, 0x0123456789ABCDEF, rb7, 0x0011223344556677, 0x0112233445566778

	@@ 借位：5 − 7 = -2
	TEST_AR_DBB         4, sub.o, rd5, rb6, 0x0000000000000005, rb7, 0x0000000000000007, 0xFFFFFFFFFFFFFFFE

	@@ 0 − 1 = 全 1
	TEST_AR_DBB         5, sub.o, rd5, rb6, 0x0000000000000000, rb7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ INT64_MIN − INT64_MAX = 1
	TEST_AR_DBB         6, sub.o, rd5, rb6, 0x8000000000000000, rb7, 0x7FFFFFFFFFFFFFFF, 0x0000000000000001

	@@ 全 1 − INT64_MIN = INT64_MAX
	TEST_AR_DBB         7, sub.o, rd5, rb6, 0xFFFFFFFFFFFFFFFF, rb7, 0x8000000000000000, 0x7FFFFFFFFFFFFFFF

	@@ ---- boundary ----
	@@ 跨 48 位借位：2^48 − 1 ⇒ 低 48 位全 1、bits[63:48] 归 0
	TEST_AR_DBB         8, sub.o, rd5, rb6, 0x0001000000000000, rb7, 0x0000000000000001, 0x0000FFFFFFFFFFFF

	@@ 结果为负 ⇒ bits[63:48] 全 1：0 − 2^48
	TEST_AR_DBB         9, sub.o, rd5, rb6, 0x0000000000000000, rb7, 0x0001000000000000, 0xFFFF000000000000

	@@ 借位沿全 64 位传播：0x00000000FFFFFFFF − 0x0000000100000000 = -1（全 1）
	TEST_AR_DBB        10, sub.o, rd5, rb6, 0x00000000FFFFFFFF, rb7, 0x0000000100000000, 0xFFFFFFFFFFFFFFFF

	@@ 两源为同值、不同寄存器 ⇒ 0（借位精确相消）
	TEST_AR_DBB        11, sub.o, rd5, rb6, 0x0F1E2D3C4B5A6978, rb7, 0x0F1E2D3C4B5A6978, 0x0000000000000000

	@@ ---- overlap ----
	@@ 两源为同一寄存器 ⇒ 0
	TEST_AR_DBB        12, sub.o, rd5, rb63, 0x8000000000000000, rb63, 0x8000000000000000, 0x0000000000000000

	@@ 目的寄存器此前有值 ⇒ 被完整覆盖（目的只写）
	TEST_AR_DBB        13, sub.o, rd5, rb6, 0x0000000000000100, rb7, 0x0000000000000001, 0x00000000000000FF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI（单目的指令丢弃唯一结果无语义）
	TEST_FAULT_DBB      14, sub.o, ILLI, rd0, rb6, rb7

	__TEST_SECTIONS
