@@ xnor.o_orrr_rd.S — xnor.o rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x0B）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：xnor.o_orrr_rd　形式：orrr　opc：0x40／ha 0x0B　mask：0xFFFC0000　value：0x402C0000　目的银行：RD
@@ 语义：rdHB ← ~(rdHC ^ rdHD)，全 64 位（相同为 1、相异为 0）；源 rd0 读出 0 ⇒ 对另一源取反
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 xnor rd7 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x402C5187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0xAAAAAAAAAAAAAAAA
	__LI	rd7, 0xFFFFFFFF00000000
	.dd.t32	0x402C5187
	__CHECK_RD   1, rd5, 0xAAAAAAAA55555555

	@@ 最高寄存器作目的（rd63）的编码字（字段边界）
	@@ 规范编码字 0x402FF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0123456789ABCDEF
	__LI	rd2, 0xFEDCBA9876543210
	.dd.t32	0x402FF042
	__CHECK_RD   2, rd63, 0x0000000000000000

	@@ 互补位模式同或 ⇒ 0
	TEST_AR_ORRR         3, xnor.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xAAAAAAAAAAAAAAAA, rd7, 0x5555555555555555, 0x0000000000000000

	@@ rd0 作源 C ⇒ 对源 D 按位取反（规范 §2.1 明确的无 not 指令用法）
	TEST_AR_ORRR         4, xnor.o, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0xAAAAAAAAAAAAAAAA, 0x5555555555555555

	@@ 两个源都是 rd0（读出 0）⇒ 全 1
	TEST_AR_ORRR         5, xnor.o, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd0, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ 与全 1 同或 ⇒ 原值不变（xor 全 1 才是取反）
	TEST_AR_ORRR         6, xnor.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, rd7, 0xFFFFFFFFFFFFFFFF, 0x0123456789ABCDEF

	@@ 两源同名：x xnor x ⇒ 全 1
	TEST_AR_ORRR         7, xnor.o, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd6, 0x0F0F0F0F0F0F0F0F, 0xFFFFFFFFFFFFFFFF

	@@ 符号位相同 ⇒ bit63 为 1、其余按位；两源同为 INT64_MIN ⇒ 全 1
	TEST_AR_ORRR         8, xnor.o, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x8000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ 零 xnor 全 1 ⇒ 0（目的初值非零也要被覆盖）
	TEST_AR_ORRR         9, xnor.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000

	@@ 两源同高低半掩码（相同）⇒ 全 1
	TEST_AR_ORRR        10, xnor.o, rd5, 0x0000000000000000, rd6, 0xFFFF0000FFFF0000, rd7, 0xFFFF0000FFFF0000, 0xFFFFFFFFFFFFFFFF

	@@ 逐 nibble 交错掩码互补 ⇒ 0
	TEST_AR_ORRR        11, xnor.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFF00000000FFFF, rd7, 0x0000FFFFFFFF0000, 0x0000000000000000

	@@ 目的=源C（原地）
	TEST_AR_ORRR        12, xnor.o, rd9, 0xAAAAAAAAAAAAAAAA, rd9, 0xAAAAAAAAAAAAAAAA, rd10, 0xFFFFFFFF00000000, 0xAAAAAAAA55555555

	@@ 目的=源D（原地）
	TEST_AR_ORRR        13, xnor.o, rd9, 0xFFFFFFFF00000000, rd10, 0xAAAAAAAAAAAAAAAA, rd9, 0xFFFFFFFF00000000, 0xAAAAAAAA55555555

	@@ 两源同名且目的不同名
	TEST_AR_ORRR        14, xnor.o, rd9, 0x0000000000000000, rd11, 0xF0F0F0F0F0F0F0F0, rd11, 0xF0F0F0F0F0F0F0F0, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, xnor.o, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
