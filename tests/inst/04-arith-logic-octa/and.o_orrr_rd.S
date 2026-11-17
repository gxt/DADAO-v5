@@ and.o_orrr_rd.S — and.o rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x08）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：and.o_orrr_rd　形式：orrr　opc：0x40／ha 0x08　mask：0xFFFC0000　value：0x40200000　目的银行：RD
@@ 语义：rdHB ← rdHC & rdHD，全 64 位参与运算（一位一位「全 1 为 1，有 0 为 0」）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 & rd7 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40205187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0xAAAAAAAAAAAAAAAA
	set.rd	rd7, 0xFFFFFFFF00000000
	.dd.t32	0x40205187
	__CHECK_RD   1, rd5, 0xAAAAAAAA00000000

	@@ 最高寄存器作目的（rd63）的编码字（字段边界）
	@@ 规范编码字 0x4023F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	.dd.t32	0x4023F042
	__CHECK_RD   2, rd63, 0x0F0F0F0F0F0F0F0F

	@@ 互补位模式相与 ⇒ 0
	TEST_AR_ORRR         3, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xAAAAAAAAAAAAAAAA, rd7, 0x5555555555555555, 0x0000000000000000

	@@ 全 1 与任何值 ⇒ 该值保持不变
	TEST_AR_ORRR         4, and.o, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0F0F0F0F0F0F0F0F, 0x0F0F0F0F0F0F0F0F

	@@ 高低半掩码互斥 ⇒ 0（YAML boundary 例）
	TEST_AR_ORRR         5, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFF0000FFFF0000, rd7, 0x0000FFFF0000FFFF, 0x0000000000000000

	@@ rd0 作源 C（读出 0）：0 & 全 1 = 0
	TEST_AR_ORRR         6, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000

	@@ 两源同名：x & x = x
	TEST_AR_ORRR         7, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd6, 0x0123456789ABCDEF, 0x0123456789ABCDEF

	@@ 符号位单独保留：INT64_MIN & 全 1 = INT64_MIN
	TEST_AR_ORRR         8, and.o, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, 0x8000000000000000

	@@ 零与全 1 ⇒ 0（目的初值非零也要被覆盖）
	TEST_AR_ORRR         9, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000

	@@ 逐 nibble 交错掩码（字节序无关；任一半错位即红）
	TEST_AR_ORRR        10, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFF00000000FFFF, rd7, 0x0000FFFFFFFF0000, 0x0000000000000000

	@@ 两个「看似互补」的满宽度随机值 ⇒ 0
	TEST_AR_ORRR        11, and.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0xFEDCBA9876543210, 0x0000000000000000

	@@ 目的=源C（原地）
	TEST_AR_ORRR        12, and.o, rd9, 0xAAAAAAAAAAAAAAAA, rd9, 0xAAAAAAAAAAAAAAAA, rd10, 0xFFFFFFFF00000000, 0xAAAAAAAA00000000

	@@ 目的=源D（原地）
	TEST_AR_ORRR        13, and.o, rd9, 0xFFFFFFFF00000000, rd10, 0xAAAAAAAAAAAAAAAA, rd9, 0xFFFFFFFF00000000, 0xAAAAAAAA00000000

	@@ 两源同名且目的不同名
	TEST_AR_ORRR        14, and.o, rd9, 0x0000000000000000, rd11, 0xF0F0F0F0F0F0F0F0, rd11, 0xF0F0F0F0F0F0F0F0, 0xF0F0F0F0F0F0F0F0

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, and.o, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
