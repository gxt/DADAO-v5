@@ cs.z_rrrr_rd.S — cs.z {rdHA}?, rdHB, rdHC, rdHD（rrrr, opc 0x62）
@@ 大类：02-reg-copy（条件赋值，`spec/SimRISC-02 §2`）
@@ id：cs.z_rrrr_rd　形式：rrrr　opc：0x62　mask：0xFF000000　value：0x62000000
@@ 语义：rdHA 为零 ⇒ rdHB = rdHC；否则 rdHB = rdHD（rdHC/rdHD 只读，未被选中侧不写）
@@ 合法性：目的 rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）；条件寄存器 rdHA 为 rd0 合法（读出 0 ⇒ 条件成立）
@@ 数据块：本文件只用立即数准备寄存器；`tests/inst/macros/inst_test.inc` 的 RDATA 供 rf 变体用
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / legality 1 / semantic 3 / boundary 7 / overlap 2（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 注：**条件寄存器与目的同名**的快照语义按 C-27 仍 deferred（`inventory.md`）⇒ 目的不与
@@   条件/候选同名；**条件寄存器与源同名**由 overlap 点覆盖（spec §2「先判断、再赋值」
@@   ⇒ 读后写序确定，不涉及 C-27 快照问题）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高几个寄存器作条件/目的/候选（字段边界）
	TEST_CS1           1, cs.z, rd63, 0, rd62, 0x1111111111111111, rd61, 0x2222222222222222, rd60, 0x3333333333333333, 0x2222222222222222
	@@ 规范编码字（rdHA=rd5, rdHB=rd6, rdHC=rd7, rdHD=rd8）直接执行：钉住 mask/value
	__LI	rd5, 0
	__LI	rd6, 0x1111111111111111
	__LI	rd7, 0x2222222222222222
	__LI	rd8, 0x3333333333333333
	.dd.t32	0x621461C8
	__CHECK_RD          2, rd6, 0x2222222222222222

	@@ ---- semantic ----
	@@ 条件为零 ⇒ 取 rdHC
	__LI	rd1, 0
	__LI	rd2, 0x1111111111111111
	__LI	rd3, 0xAAAAAAAAAAAAAAAA
	__LI	rd5, 0xBBBBBBBBBBBBBBBB
	cs.z	{rd1}?, rd2, rd3, rd5
	__VERIFY_RD         3, rd5, 0xBBBBBBBBBBBBBBBB
	__CHECK_RD          3, rd2, 0xAAAAAAAAAAAAAAAA
	@@ 条件为正 ⇒ 取 rdHD
	TEST_CS1           4, cs.z, rd1, 1, rd2, 0x1111111111111111, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB
	@@ 条件为负 ⇒ 取 rdHD
	TEST_CS1           5, cs.z, rd1, -1, rd2, 0x1111111111111111, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB

	@@ ---- legality / boundary ----
	@@ 条件寄存器 rd0（硬连零，读出 0）⇒ 条件成立 ⇒ 取 rdHC
	TEST_CS1           6, cs.z, rd0, 0, rd2, 0x1111111111111111, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xBBBBBBBBBBBBBBBB, 0xAAAAAAAAAAAAAAAA
	@@ 条件为最小负数 / 最大正数 ⇒ 都取 rdHD（只有零成立）
	TEST_CS1           7, cs.z, rd1, 0x8000000000000000, rd2, 0x1111111111111111, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB
	TEST_CS1           8, cs.z, rd1, 0x7FFFFFFFFFFFFFFF, rd2, 0x1111111111111111, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB
	@@ 两侧候选为零 / 全一（照搬位型，不做符号解释）
	TEST_CS1           9, cs.z, rd1, 0, rd2, 0x1111111111111111, rd3, 0x0000000000000000, rd5, 0xBBBBBBBBBBBBBBBB, 0x0000000000000000
	TEST_CS1          10, cs.z, rd1, 1, rd2, 0x1111111111111111, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@ 两侧候选同值 ⇒ 两支结果一致
	TEST_CS1          11, cs.z, rd1, 0, rd2, 0x1111111111111111, rd3, 0x5555555555555555, rd5, 0x5555555555555555, 0x5555555555555555
	@@ 目的初值恰等于「成立侧」而条件不成立 ⇒ 仍被 rdHD 改写（选择而非「相等则保持」）
	TEST_CS1          12, cs.z, rd1, -1, rd2, 0xAAAAAAAAAAAAAAAA, rd3, 0xAAAAAAAAAAAAAAAA, rd5, 0xBBBBBBBBBBBBBBBB, 0xBBBBBBBBBBBBBBBB
	@@ 条件恰为零、成立侧为全一 ⇒ 目的变全一
	TEST_CS1          13, cs.z, rd1, 0, rd2, 0x1111111111111111, rd3, 0xFFFFFFFFFFFFFFFF, rd5, 0xBBBBBBBBBBBBBBBB, 0xFFFFFFFFFFFFFFFF

	@@ ---- overlap ----
	@@ 条件/候选/目的互不同名（C-27 之外的路径）：未选中侧（rdHC）不得被改写
	__LI	rd1, 1
	__LI	rd2, 0x1111222233334444
	__LI	rd3, 0x000000000000AAAA
	__LI	rd5, 0x000000000000BBBB
	cs.z	{rd1}?, rd2, rd3, rd5
	__VERIFY_RD        14, rd3, 0x000000000000AAAA
	__CHECK_RD         14, rd2, 0x000000000000BBBB
	@@ 条件寄存器 = 源 rdHC 别名（spec §2 先判断再赋值）：条件为零 ⇒ 目的 = 同一源，源不被改写
	__LI	rd3, 0x0000000000000000
	__LI	rd2, 0x1111222233334444
	__LI	rd5, 0x000000000000BBBB
	cs.z	{rd3}?, rd2, rd3, rd5
	__VERIFY_RD        15, rd3, 0x0000000000000000
	__VERIFY_RD        15, rd5, 0x000000000000BBBB
	__CHECK_RD         15, rd2, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器对 cs.* 放行该编码）
	TEST_FAULT_CS         16, cs.z, rd0, ILLI, rd1, rd3, rd4

	__TEST_SECTIONS
