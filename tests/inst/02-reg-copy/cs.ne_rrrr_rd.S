@@ cs.ne_rrrr_rd.S — cs.ne {rdHA, rdHB}?, rdHC, rdHD（rrrr, opc 0x67）
@@ 大类：02-reg-copy（条件赋值，`spec/SimRISC-02 §2`）
@@ id：cs.ne_rrrr_rd　形式：rrrr　opc：0x67　mask：0xFF000000　value：0x67000000
@@ 语义：rdHA != rdHB ⇒ rdHC = rdHD；否则 rdHC 不变（**目的在第三个操作数** rdHC）
@@ 合法性：目的 rdHC 为 rd0 ⇒ ILLI（`dst_rd0`）；比较操作数可为 rd0 合法（读出 0）
@@ 数据块：本文件只用立即数准备寄存器；`tests/inst/macros/inst_test.inc` 的 RDATA 供 rf 变体用
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 3 / boundary 8 / overlap 2（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 注：**比较操作数与目的同名**的快照语义按 C-27 仍 deferred（`inventory.md`）⇒ 目的不与
@@   比较操作数同名；**比较操作数彼此同名且与赋值源同名**由 overlap 点覆盖（spec §2
@@   「先比较、再赋值」⇒ 读后写序确定，不涉及 C-27 快照问题）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高几个寄存器作比较/目的/赋值源（字段边界）
	TEST_CS2           1, cs.ne, rd63, 0x0123456789ABCDEF, rd62, 0xFEDCBA9876543210, rd61, 0x1111111111111111, rd60, 0x2222222222222222, 0x2222222222222222
	@@ 规范编码字（rdHA=rd5, rdHB=rd6, rdHC=rd7, rdHD=rd8）直接执行：钉住 mask/value
	set.rd	rd5, 0x2A
	set.rd	rd6, 0x63
	set.rd	rd7, 0x1111111111111111
	set.rd	rd8, 0x2222222222222222
	.dd.t32	0x671461C8
	__CHECK_RD          2, rd7, 0x2222222222222222

	@@ ---- semantic ----
	@@ 不相等 ⇒ 目的 = rdHD
	set.rd	rd1, 0x2A
	set.rd	rd2, 0x63
	set.rd	rd3, 0x1111111111111111
	set.rd	rd5, 0xBBBBBBBBBBBBBBBB
	cs.ne	{rd1, rd2}?, rd3, rd5
	__VERIFY_RD         3, rd5, 0xBBBBBBBBBBBBBBBB
	__CHECK_RD          3, rd3, 0xBBBBBBBBBBBBBBBB
	@@ 相等 ⇒ 目的保持初值（rdHD 不写）
	TEST_CS2           4, cs.ne, rd1, 0x2A, rd2, 0x2A, rd3, 0x1111111111111111, rd5, 0xBBBBBBBBBBBBBBBB, 0x1111111111111111
	@@ 比较操作数 rd0（硬连零）与非零寄存器不相等 ⇒ 成立
	TEST_CS2           5, cs.ne, rd0, 0, rd6, 1, rd3, 0x1111111111111111, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB

	@@ ---- boundary ----
	@@ 只差最低位 ⇒ 不相等
	TEST_CS2           6, cs.ne, rd1, 0x8000000000000000, rd2, 0x8000000000000001, rd3, 0x1111111111111111, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB
	@@ 两侧全一 ⇒ 相等 ⇒ 目的保持
	TEST_CS2           7, cs.ne, rd1, -1, rd2, -1, rd3, 0x1111111111111111, rd5, 0xBBBBBBBBBBBBBBBB, 0x1111111111111111
	@@ 两侧为零 ⇒ 相等 ⇒ 目的保持
	TEST_CS2           8, cs.ne, rd1, 0, rd2, 0, rd3, 0x1111111111111111, rd5, 0xBBBBBBBBBBBBBBBB, 0x1111111111111111
	@@ 赋值源为零 ⇒ 目的被清零（不是「不写」）
	TEST_CS2           9, cs.ne, rd1, 0x2A, rd2, 0x63, rd3, 0x1111111111111111, rd5, 0x0000000000000000, 0x0000000000000000
	@@ 赋值源为全一
	TEST_CS2          10, cs.ne, rd1, 0x2A, rd2, 0x63, rd3, 0x1111111111111111, rd5, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@ 相等且目的初值为零 ⇒ 保持零
	TEST_CS2          11, cs.ne, rd1, 0x2A, rd2, 0x2A, rd3, 0x0000000000000000, rd5, 0xBBBBBBBBBBBBBBBB, 0x0000000000000000
	@@ 仅符号位不同（0x7FFF… vs 0xFFFF…）⇒ 不相等
	TEST_CS2          12, cs.ne, rd1, 0x7FFFFFFFFFFFFFFF, rd2, 0xFFFFFFFFFFFFFFFF, rd3, 0x1111111111111111, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB
	@@ 两侧都为 1 ⇒ 相等 ⇒ 目的保持
	TEST_CS2          13, cs.ne, rd1, 1, rd2, 1, rd3, 0x1111111111111111, rd5, 0x5555555555555555, 0x1111111111111111

	@@ ---- overlap ----
	@@ 比较/赋值源/目的互不同名（C-27 之外的路径）：赋值源未被改写
	set.rd	rd1, 0x2A
	set.rd	rd2, 0x63
	set.rd	rd3, 0x1111222233334444
	set.rd	rd5, 0x000000000000BBBB
	cs.ne	{rd1, rd2}?, rd3, rd5
	__VERIFY_RD        14, rd5, 0x000000000000BBBB
	__CHECK_RD         14, rd3, 0x000000000000BBBB
	@@ 条件 rdHB = 赋值源 rdHD 别名且不等（spec §2 先比较再赋值）：不等 ⇒ 目的 = 同一源，源不被改写
	set.rd	rd1, 0x2A
	set.rd	rd3, 0x2B
	set.rd	rd2, 0x1111222233334444
	cs.ne	{rd1, rd3}?, rd2, rd3
	__VERIFY_RD        15, rd3, 0x2B
	__CHECK_RD         15, rd2, 0x2B

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 目的 rdHC = rd0 ⇒ ILLI（dst_rd0；汇编器对 cs.* 放行该编码）
	TEST_FAULT_CS2        16, cs.ne, rd0, ILLI, rd1, rd2, rd4

	__TEST_SECTIONS
