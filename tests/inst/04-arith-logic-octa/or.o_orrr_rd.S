@@ or.o_orrr_rd.S — or.o rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x09）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：or.o_orrr_rd　形式：orrr　opc：0x40／ha 0x09　mask：0xFFFC0000　value：0x40240000　目的银行：RD
@@ 语义：rdHB ← rdHC | rdHD，全 64 位参与运算（一位一位「全 0 为 0，有 1 为 1」）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 | rd7 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40245187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0xAAAAAAAAAAAAAAAA
	__LI	rd7, 0xFFFFFFFF00000000
	.dd.t32	0x40245187
	__CHECK_RD   1, rd5, 0xFFFFFFFFAAAAAAAA

	@@ 最高寄存器作目的（rd63）的编码字（字段边界）
	@@ 规范编码字 0x4027F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	__LI	rd63, 0x0000000000000000
	__LI	rd1, 0x0123456789ABCDEF
	__LI	rd2, 0xFEDCBA9876543210
	.dd.t32	0x4027F042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ 互补位模式相或 ⇒ 全 1
	TEST_AR_ORRR         3, or.o, rd5, 0x0000000000000000, rd6, 0xAAAAAAAAAAAAAAAA, rd7, 0x5555555555555555, 0xFFFFFFFFFFFFFFFF

	@@ 全 1 与任何值相或 ⇒ 全 1（目的初值非零也要被覆盖）
	TEST_AR_ORRR         4, or.o, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0F0F0F0F0F0F0F0F, 0xFFFFFFFFFFFFFFFF

	@@ 高低半掩码互斥 ⇒ 全 1（YAML boundary 例）
	TEST_AR_ORRR         5, or.o, rd5, 0x0000000000000000, rd6, 0xFFFF0000FFFF0000, rd7, 0x0000FFFF0000FFFF, 0xFFFFFFFFFFFFFFFF

	@@ rd0 作源 C（读出 0）：0 | x = x
	TEST_AR_ORRR         6, or.o, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x8000000000000000, 0x8000000000000000

	@@ 两源同名：x | x = x
	TEST_AR_ORRR         7, or.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd6, 0x0123456789ABCDEF, 0x0123456789ABCDEF

	@@ 符号位单独保留：INT64_MIN | 0 = INT64_MIN
	TEST_AR_ORRR         8, or.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0x0000000000000000, 0x8000000000000000

	@@ 零 | 零 ⇒ 0（目的初值全 1 也要被覆盖）
	TEST_AR_ORRR         9, or.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000000, 0x0000000000000000

	@@ 高低半各置一位：0x8000000000000000 | 0x0000000080000000
	TEST_AR_ORRR        10, or.o, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x0000000080000000, 0x8000000080000000

	@@ 逐 nibble 交错掩码（并集覆盖全部 64 位）
	TEST_AR_ORRR        11, or.o, rd5, 0x0000000000000000, rd6, 0xFFFF00000000FFFF, rd7, 0x0000FFFFFFFF0000, 0xFFFFFFFFFFFFFFFF

	@@ 目的=源C（原地）
	TEST_AR_ORRR        12, or.o, rd9, 0xAAAAAAAAAAAAAAAA, rd9, 0xAAAAAAAAAAAAAAAA, rd10, 0xFFFFFFFF00000000, 0xFFFFFFFFAAAAAAAA

	@@ 目的=源D（原地）
	TEST_AR_ORRR        13, or.o, rd9, 0xFFFFFFFF00000000, rd10, 0xAAAAAAAAAAAAAAAA, rd9, 0xFFFFFFFF00000000, 0xFFFFFFFFAAAAAAAA

	@@ 两源同名且目的不同名
	TEST_AR_ORRR        14, or.o, rd9, 0x0000000000000000, rd11, 0xF0F0F0F0F0F0F0F0, rd11, 0xF0F0F0F0F0F0F0F0, 0xF0F0F0F0F0F0F0F0

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, or.o, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
