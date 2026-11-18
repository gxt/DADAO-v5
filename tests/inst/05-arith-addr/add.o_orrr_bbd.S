@@ add.o_orrr_bbd.S — add.o rbHB, rbHC, rdHD（orrr/bbd, opc 0x40, ha 0x30）
@@ 大类：05-arith-addr（64 位地址运算，`spec/SimRISC-05 §1`）；册目录 `tests/inst/05-arith-addr/`
@@ id：add.o_orrr_bbd　形式：orrr（bbd）　opc：0x40　ha：0x30　mask：0xFFFC0000　value：0x40C00000
@@ 目的银行：RB（rbHB）；源 = rbHC（RB）+ rdHD（RD）
@@ 语义：rbHB ← rbHC + rdHD（二进制补码 64 位加法，全 64 位参与、结果完整保留 64 位）
@@   加法本身**不做地址截断**；仅当以结果访存时硬件取 rbHB[47:0] 为有效地址，
@@   rbHB[63:48] 是地址计算的高 16 位（= 地址溢出指示）⇒ 运算结果不截断，用例直接比 64 位
@@ 合法性：目的 rbHB 为 rb0 ⇒ ILLI（`dst_rb0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[17:16] | rbhb[17:12] | rbhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rb`/`set.rd` 拼初值；本册复用 04 的数据块）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 4 / boundary 5 / overlap 2（链例 13 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rb`（rb）/`set.rd`（rd）拼常量（被测指令不参与造初值）、期望内联；
@@   目的在 RB ⇒ 实测经同组 `st.o` 落到 SCRATCH（rb29 指）再 `__CHECK_MEM`

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/05-arith-addr/05-arith-addr.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字 0x40C05187（opc/ha | rb5 | rb6 | rd7）直接执行：钉住 mask/value
	set.rb	rb6, 0x0000000000000064
	set.rd	rd7, 0x000000000000001E
	.dd.t32	0x40C05187
	st.o	rb5, [rb29, 0]
	__CHECK_MEM         1, SCRATCH, 0, 0x0000000000000082

	@@ 字段边界：目的/源都是最大寄存器（0x40C3FFFF = rb63 | rb63 | rd63）
	set.rb	rb63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd63, 0x0000000000000001
	.dd.t32	0x40C3FFFF
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x0000000000000000

	@@ ---- semantic ----
	@@ 正 + 正（两操作数都是大数）
	TEST_AR_BBD         3, add.o, rb5, rb6, 0x0123456789ABCDEF, rd7, 0x0011223344556677, 0x0134679ACE013466

	@@ -1 + 1 = 0（全 64 位参与，进位出 2^64）
	TEST_AR_BBD         4, add.o, rb5, rb6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ (-1) + (-1) = -2
	TEST_AR_BBD         5, add.o, rb5, rb6, 0xFFFFFFFFFFFFFFFF, rd7, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFE

	@@ rd0 作源（读出 0）：结果 = 另一源原值
	TEST_AR_BBD         6, add.o, rb5, rb6, 0xDEADBEEFCAFEF00D, rd0, 0x0000000000000000, 0xDEADBEEFCAFEF00D

	@@ ---- boundary ----
	@@ 低 48 位全 1 + 1：低 48 位归零、bits[63:48] = 1（地址溢出指示）——结果**不**截断到 48 位
	TEST_AR_BBD         7, add.o, rb6, rb6, 0x0000FFFFFFFFFFFF, rd7, 0x0000000000000001, 0x0001000000000000

	@@ 高 16 位与低 48 位同时非零：0xFFFF.. + 0x0000FFFF.. = 全 1
	TEST_AR_BBD         8, add.o, rb6, rb6, 0xFFFF000000000000, rd7, 0x0000FFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ INT64_MIN + INT64_MIN：进位出 2^64 ⇒ 0
	TEST_AR_BBD         9, add.o, rb6, rb6, 0x8000000000000000, rd7, 0x8000000000000000, 0x0000000000000000

	@@ INT64_MAX + INT64_MAX = 2^64-2（高半全 1）
	TEST_AR_BBD        10, add.o, rb6, rb6, 0x7FFFFFFFFFFFFFFF, rd7, 0x7FFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFE

	@@ 进位只发生在低 48 位内：高 16 位保持不变
	TEST_AR_BBD        11, add.o, rb6, rb6, 0x0000FFFFFFFF0000, rd7, 0x0000000000001000, 0x0000FFFFFFFF1000

	@@ ---- overlap ----
	@@ 目的 = 源C（原地）
	TEST_AR_BBD        12, add.o, rb5, rb5, 0x0000000000000100, rd7, 0x0000000000000010, 0x0000000000000110

	@@ 目的 = 源C 且跨 2^64 进位
	TEST_AR_BBD        13, add.o, rb5, rb5, 0xFFFFFFFFFFFFFFF0, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFF1

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rb0：目的 rb0 ⇒ ILLI（rb0 读出为当前 IP、只读）
	TEST_FAULT_BBD      14, add.o, ILLI, rb0, rb6, rd7

	__TEST_SECTIONS
