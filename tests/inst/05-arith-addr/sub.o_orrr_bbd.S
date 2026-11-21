@@ sub.o_orrr_bbd.S — sub.o rbHB, rbHC, rdHD（orrr/bbd, opc 0x40, ha 0x31）
@@ 大类：05-arith-addr（64 位地址运算，`spec/SimRISC-05 §1`）；册目录 `tests/inst/05-arith-addr/`
@@ id：sub.o_orrr_bbd　形式：orrr（bbd）　opc：0x40　ha：0x31　mask：0xFFFC0000　value：0x40C40000
@@ 目的银行：RB（rbHB）；源 = rbHC（RB）+ rdHD（RD）
@@ 语义：rbHB ← rbHC − rdHD（二进制补码 64 位减法，全 64 位参与、结果完整保留 64 位）
@@   减法本身**不做地址截断**；仅当以结果访存时硬件取 rbHB[47:0] 为有效地址，
@@   rbHB[63:48] 是地址计算的高 16 位（借位/欠落时为全 1）⇒ 运算结果不截断，用例直接比 64 位
@@ 合法性：目的 rbHB 为 rb0 ⇒ ILLI（`dst_rb0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[17:16] | rbhb[17:12] | rbhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rb`/`set.rd` 拼初值；本册复用 04 的数据块）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 4 / boundary 5 / overlap 2（链例 13 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rb`（rb）/`set.rd`（rd）拼常量（被测指令不参与造初值）、期望内联；
@@   目的在 RB ⇒ 实测经同组 `st.o` 落到 SCRATCH（rb29 指）再 `__CHECK_MEM`

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/05-arith-addr/05-arith-addr.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字 0x40C45187（opc/ha | rb5 | rb6 | rd7）直接执行：钉住 mask/value
	set.rb	rb6, 0x0000000000000064
	set.rd	rd7, 0x000000000000001E
	.dd.t32	0x40C45187
	st.o	rb5, [rb29, 0]
	__CHECK_MEM         1, SCRATCH, 0, 0x0000000000000046

	@@ 字段边界：目的/源都是最大寄存器（0x40C7FFFF = rb63 | rb63 | rd63）
	set.rb	rb63, 0x8000000000000000
	set.rd	rd63, 0x8000000000000000
	.dd.t32	0x40C7FFFF
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x0000000000000000

	@@ ---- semantic ----
	@@ 大数 − 大数
	TEST_AR_BBD         3, sub.o, rb5, rb6, 0x0123456789ABCDEF, rd7, 0x0011223344556677, 0x0112233445566778

	@@ 借位：5 − 7 = -2
	TEST_AR_BBD         4, sub.o, rb5, rb6, 0x0000000000000005, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFFE

	@@ 0 − 1 = 全 1
	TEST_AR_BBD         5, sub.o, rb5, rb6, 0x0000000000000000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ rd0 作源（读出 0）：结果 = 被减数原值
	TEST_AR_BBD         6, sub.o, rb5, rb6, 0xDEADBEEFCAFEF00D, rd0, 0x0000000000000000, 0xDEADBEEFCAFEF00D

	@@ ---- boundary ----
	@@ INT64_MIN − INT64_MAX = 1（有符号最值对，全 64 位差）
	TEST_AR_BBD         7, sub.o, rb6, rb6, 0x8000000000000000, rd7, 0x7FFFFFFFFFFFFFFF, 0x0000000000000001

	@@ 2^48 − 1：低 48 位全 1、bits[63:48] 归 0（跨 48 位借位，结果不截断）
	TEST_AR_BBD         8, sub.o, rb6, rb6, 0x0001000000000000, rd7, 0x0000000000000001, 0x0000FFFFFFFFFFFF

	@@ 低 48 位借位后仍留 0x0000FFFF..：0x1_0000_0001 − 2
	TEST_AR_BBD         9, sub.o, rb6, rb6, 0x0001000000000001, rd7, 0x0000000000000002, 0x0000FFFFFFFFFFFF

	@@ 0 − 2^48：结果为负 ⇒ bits[63:48] 全 1
	TEST_AR_BBD        10, sub.o, rb6, rb6, 0x0000000000000000, rd7, 0x0001000000000000, 0xFFFF000000000000

	@@ 全 1（= -1）− INT64_MIN = INT64_MAX（有符号两端相减，结果按模 2^64）
	TEST_AR_BBD        11, sub.o, rb6, rb6, 0xFFFFFFFFFFFFFFFF, rd7, 0x8000000000000000, 0x7FFFFFFFFFFFFFFF

	@@ ---- overlap ----
	@@ 目的 = 源C（原地）
	TEST_AR_BBD        12, sub.o, rb5, rb5, 0x0000000000000100, rd7, 0x0000000000000001, 0x00000000000000FF

	@@ 目的 = 源C 且借位
	TEST_AR_BBD        13, sub.o, rb5, rb5, 0x0000000000000000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rb0：目的 rb0 ⇒ ILLI（rb0 读出为当前 IP、只读）
	TEST_FAULT_BBD      14, sub.o, ILLI, rb0, rb6, rd7

	__TEST_SECTIONS
