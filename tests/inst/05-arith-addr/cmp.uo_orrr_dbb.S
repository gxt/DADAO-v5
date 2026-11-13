@@ cmp.uo_orrr_dbb.S — cmp.uo rdHB, rbHC, rbHD（orrr/dbb, opc 0x40, ha 0x32）
@@ 大类：05-arith-addr（64 位地址运算，`spec/SimRISC-05 §3`）；册目录 `tests/inst/05-arith-addr/`
@@ id：cmp.uo_orrr_dbb　形式：orrr（dbb）　opc：0x40　ha：0x32　mask：0xFFFC0000　value：0x40C80000
@@ 目的银行：RD（rdHB）；两源都在 RB（rbHC、rbHD）
@@ 语义：rdHB ← 无符号比较(rbHC, rbHD) 的 -1 / 0 / 1（小于 / 等于 / 大于）
@@   **整 64 位**参与比较（bits[63:48] 参与），不是只比低 48 位；结果写满 64 位
@@ 合法性：目的 rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[17:16] | rdhb[17:12] | rbhc[11:6] | rbhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI_RB` 拼初值；本册复用 04 的数据块）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 3 / boundary 6 / overlap 2（链例 13 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI_RB` 拼常量（被测指令不参与造初值）、期望内联；目的在 rd ⇒ `__CHECK_RD`

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字 0x40C85187（opc/ha | rd5 | rb6 | rb7）直接执行：钉住 mask/value
	__LI_RB	rb6, 0x0000000000000005
	__LI_RB	rb7, 0x0000000000000007
	.dd.t32	0x40C85187
	__CHECK_RD          1, rd5, 0xFFFFFFFFFFFFFFFF

	@@ 字段边界：目的/两源都是最大寄存器（0x40CBFFFF = rd63 | rb63 | rb63）
	__LI_RB	rb63, 0x0000000000000000
	.dd.t32	0x40CBFFFF
	__CHECK_RD          2, rd63, 0x0000000000000000

	@@ ---- semantic ----
	@@ 0xA < 0x14 ⇒ -1
	TEST_AR_DBB         3, cmp.uo, rd5, rb6, 0x000000000000000A, rb7, 0x0000000000000014, 0xFFFFFFFFFFFFFFFF

	@@ 相等 ⇒ 0
	TEST_AR_DBB         4, cmp.uo, rd5, rb6, 0x0123456789ABCDEF, rb7, 0x0123456789ABCDEF, 0x0000000000000000

	@@ 大于 ⇒ 1
	TEST_AR_DBB         5, cmp.uo, rd5, rb6, 0x0000000000000021, rb7, 0x0000000000000020, 0x0000000000000001

	@@ ---- boundary ----
	@@ bits[63:48] 参与的大数边界：0x0000FFFF.. < 0x0001_0000_0000_0000
	@@（只比低 48 位会判「相等 0」⇒ 本用例区分 64 位 / 48 位比较口径）
	TEST_AR_DBB         6, cmp.uo, rd5, rb6, 0x0000FFFFFFFFFFFF, rb7, 0x0001000000000000, 0xFFFFFFFFFFFFFFFF

	@@ 反向：0x0001_0000_0000_0000 > 0x0000FFFF.. ⇒ 1
	TEST_AR_DBB         7, cmp.uo, rd5, rb6, 0x0001000000000000, rb7, 0x0000FFFFFFFFFFFF, 0x0000000000000001

	@@ **无符号**：bit63 置位的值是更大的数（INT64_MIN > INT64_MAX 的无符号解读）
	TEST_AR_DBB         8, cmp.uo, rd5, rb6, 0x8000000000000000, rb7, 0x7FFFFFFFFFFFFFFF, 0x0000000000000001

	@@ 同上反向 ⇒ -1
	TEST_AR_DBB         9, cmp.uo, rd5, rb6, 0x7FFFFFFFFFFFFFFF, rb7, 0x8000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ 全 1 > 0 ⇒ 1
	TEST_AR_DBB        10, cmp.uo, rd5, rb6, 0xFFFFFFFFFFFFFFFF, rb7, 0x0000000000000000, 0x0000000000000001

	@@ 0 < 全 1 ⇒ -1（结果 -1 写满 64 位）
	TEST_AR_DBB        11, cmp.uo, rd5, rb6, 0x0000000000000000, rb7, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ ---- overlap ----
	@@ 两源为同一寄存器（源 C = 源 D）⇒ 必相等 ⇒ 0
	TEST_AR_DBB        12, cmp.uo, rd5, rb63, 0x8000000000000000, rb63, 0x8000000000000000, 0x0000000000000000

	@@ 两源为同值不同寄存器 ⇒ 0
	TEST_AR_DBB        13, cmp.uo, rd5, rb6, 0x0000FFFFFFFFFFFF, rb7, 0x0000FFFFFFFFFFFF, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI（单目的指令丢弃唯一结果无语义）
	TEST_FAULT_DBB      14, cmp.uo, ILLI, rd0, rb6, rb7

	__TEST_SECTIONS
