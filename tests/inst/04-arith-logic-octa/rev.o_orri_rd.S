@@ rev.o_orri_rd.S — rev.o rdHB, rdHC, immu6（orri, opc 0x40／ha 0x0C）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2.1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：rev.o_orri_rd　形式：orri　opc：0x40／ha 0x0C　mask：0xFFFC0000　value：0x40300000　目的银行：RD
@@ 语义：rdHB ← 把 64 位源切成 64/k 个 k 位单元后**倒序拼接**（单元内部位序不变）；
@@   k=8 ⇒ bswap64、k=1 ⇒ 64 位整体位反序；全部 64 位都参与，不存在「高位保持」
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；原地反转允许；
@@   immu6 = k 须为 one-hot 且 k < 64（合法档 1/2/4/8/16/32）⇒ 0/3/5/…/63 触发 ILLI（`encode_onehot`）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 4 / overlap 1（链例 13 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rev.o(rd6, k=8) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40305188（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | immu6）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0123456789ABCDEF
	.dd.t32	0x40305188
	__CHECK_RD   1, rd5, 0xEFCDAB8967452301

	@@ 最高寄存器作目的（rd63）+ k=32 的编码字（字段边界）
	@@ 规范编码字 0x4033F060（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | immu6）
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0123456789ABCDEF
	.dd.t32	0x4033F060
	__CHECK_RD   2, rd63, 0x89ABCDEF01234567

	@@ k=1：64 位整体位反序（bitreverse64）
	TEST_AR_ORRI         3, rev.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 1, 0xF7B3D591E6A2C480

	@@ k=2：每 2 位单元倒序
	TEST_AR_ORRI         4, rev.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 2, 0xFB73EA62D951C840

	@@ k=4：每 nibble 倒序
	TEST_AR_ORRI         5, rev.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 4, 0xFEDCBA9876543210

	@@ k=8：bswap64（端序敏感）
	TEST_AR_ORRI         6, rev.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 8, 0xEFCDAB8967452301

	@@ k=16：每 16 位单元倒序
	TEST_AR_ORRI         7, rev.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 16, 0xCDEF89AB45670123

	@@ k=32：高低 32 位互换
	TEST_AR_ORRI         8, rev.o, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 32, 0x89ABCDEF01234567

	@@ 源全 0 ⇒ 结果全 0（目的初值被覆盖）
	TEST_AR_ORRI         9, rev.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 1, 0x0000000000000000

	@@ 源全 1 ⇒ 结果全 1（全 1 图案逐单元倒序不变）
	TEST_AR_ORRI        10, rev.o, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 1, 0xFFFFFFFFFFFFFFFF

	@@ 目的=源（原地反转，允许）
	TEST_AR_ORRI        11, rev.o, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, 1, 0xF7B3D591E6A2C480

	@@ rd0 作源（读出 0）⇒ 结果 0
	TEST_AR_ORRI        12, rev.o, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 1, 0x0000000000000000

	@@ 原地 bswap64：0x0102030405060708 → 0x0807060504030201（端序敏感）
	TEST_AR_ORRI        13, rev.o, rd9, 0x0102030405060708, rd9, 0x0102030405060708, 8, 0x0807060504030201

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ encode_onehot：k=0 非 one-hot ⇒ ILLI
	TEST_FAULT_ALU_ORRI 14, rev.o, ILLI, rd5, rd6, 0

	@@ encode_onehot：k=3 非 one-hot ⇒ ILLI
	TEST_FAULT_ALU_ORRI 15, rev.o, ILLI, rd5, rd6, 3

	@@ encode_onehot：k=5 非 one-hot ⇒ ILLI
	TEST_FAULT_ALU_ORRI 16, rev.o, ILLI, rd5, rd6, 5

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 17, rev.o, ILLI, rd0, rd6, 8

	__TEST_SECTIONS
