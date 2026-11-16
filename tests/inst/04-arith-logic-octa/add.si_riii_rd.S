@@ add.si_riii_rd.S — add.si rdHA, imms18（riii, opc 0x59）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：add.si_riii_rd　形式：riii　opc：0x59　mask：0xFF000000　value：0x59000000　目的银行：RD
@@ 语义：rdHA ← rdHA + 符号扩展(imms18)（全 64 位，溢出回绕；进位丢弃）
@@ 合法性：目的 rdHA/rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：riii = opc | rdha[23:18] | imms18[17:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ rd5 + (-8) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x5917FFF8（opc<<24 | rd5<<18 | imms18）
	__LI	rd5, 0x0000000000000100
	.dd.t32	0x5917FFF8
	__CHECK_RD   1, rd5, 0x00000000000000F8

	@@ 最高寄存器 rd63 + 最大正立即数（字段边界）
	@@ 规范编码字 0x59FDFFFF（opc<<24 | rd63<<18 | imms18）
	__LI	rd63, 0x0000000000000000
	.dd.t32	0x59FDFFFF
	__CHECK_RD   2, rd63, 0x000000000001FFFF

	@@ +1
	TEST_AR_SI           3, add.si, rd5, 0x0123456789ABCDEF, 1, 0x0123456789ABCDF0

	@@ -1
	TEST_AR_SI           4, add.si, rd5, 0x0123456789ABCDEF, -1, 0x0123456789ABCDEE

	@@ 立即数 0（空操作）
	TEST_AR_SI           5, add.si, rd5, 0x0123456789ABCDEF, 0, 0x0123456789ABCDEF

	@@ 最大正立即数 0x1FFFF
	TEST_AR_SI           6, add.si, rd5, 0x0000000000000000, 131071, 0x000000000001FFFF

	@@ 最小负立即数 -0x20000
	TEST_AR_SI           7, add.si, rd5, 0x0000000000000000, -131072, 0xFFFFFFFFFFFE0000

	@@ 正溢出回绕：max + 1 = min
	TEST_AR_SI           8, add.si, rd6, 0x7FFFFFFFFFFFFFFF, 1, 0x8000000000000000

	@@ 负溢出回绕：min + (-1) = max
	TEST_AR_SI           9, add.si, rd6, 0x8000000000000000, -1, 0x7FFFFFFFFFFFFFFF

	@@ 全 1 + 1 = 0（进位丢弃）
	TEST_AR_SI          10, add.si, rd6, 0xFFFFFFFFFFFFFFFF, 1, 0x0000000000000000

	@@ max + 0x1FFFF 跨符号（跨 4 个 16 位片）
	TEST_AR_SI          11, add.si, rd7, 0x7FFFFFFFFFFFFFFF, 131071, 0x800000000001FFFE

	@@ min + (-0x20000)
	TEST_AR_SI          12, add.si, rd7, 0x8000000000000000, -131072, 0x7FFFFFFFFFFE0000

	@@ 进位跨 wyde：0xFFFF + 2 = 0x10001
	TEST_AR_SI          13, add.si, rd7, 0x000000000000FFFF, 2, 0x0000000000010001

	@@ 目的=源：旧值参与运算（同一寄存器读写）
	TEST_AR_SI          14, add.si, rd8, 0xA5A5A5A55A5A5A5A, 4660, 0xA5A5A5A55A5A6C8E

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_SI   15, add.si, ILLI, rd0, 1

	__TEST_SECTIONS
