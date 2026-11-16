@@ rev.b_orri_rd.S — rev.b rdHB, rdHC, immu6（orri, opc 0x43／ha 0x0C）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2.1`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：rev.b_orri_rd　形式：orri　opc：0x43／ha 0x0C　mask：0xFFFC0000　value：0x43300000　目的银行：RD
@@ 语义：把 64 位源切成 **8 个 8 位块**，每块再按 k 位切成 8/k 个单元、**块内单元倒序**拼接
@@   （单元内部位序不变）；八个块一律同样处理 —— k=4 只是字节内 nibble 互换，
@@   不是 64 位整体 nibble 反序；k=1 是块内位反序，不是 64 位整体位反序
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；
@@   k = immu6 须 one-hot 且 k < 8（合法档 1/2/4）⇒ 0/3/5..7 与非 one-hot 值、
@@   以及 k ≥ 8（含 k=8 恒等档）触发 ILLI（`encode_onehot`）
@@ 编码：orri = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43305181 = value | rd5<<12 | rd6<<6 | k=1：每字节位反序
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x0123456789ABCDEF
	.dd.t32	0x43305181
	__CHECK_RD   1, rd5, 0x80C4A2E691D5B3F7

	@@ 0x4333F044 = value | rd63<<12 | rd1<<6 | k=4（字段边界：最大目的号）：每字节 nibble 互换
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0123456789ABCDEF
	.dd.t32	0x4333F044
	__CHECK_RD   2, rd63, 0x1032547698BADCFE

	@@ ---- semantic ----
	@@ k=1：0x01 ⇒ 0x80（块内位反序，高位块不变 0）
	TEST_AR_ORRI         3, rev.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, 1, 0x0000000000000080

	@@ k=1：0x80 ⇒ 0x01
	TEST_AR_ORRI         4, rev.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, 1, 0x0000000000000001

	@@ k=2：0x0F ⇒ 0xF0（4 个 2 位单元倒序）
	TEST_AR_ORRI         5, rev.b, rd5, 0x0000000000000000, rd6, 0x000000000000000F, 2, 0x00000000000000F0

	@@ k=4：0x80 ⇒ 0x08（各字节内 nibble 互换，跨字节不动）
	TEST_AR_ORRI         6, rev.b, rd5, 0x0000000000000000, rd6, 0x0000000000000080, 4, 0x0000000000000008

	@@ k=4：0xAA 是 nibble 回文 ⇒ 原值
	TEST_AR_ORRI         7, rev.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000AA, 4, 0x00000000000000AA

	@@ ---- boundary ----
	@@ 八个块全部处理（k=2，块内 2 位单元倒序）：0x0123456789ABCDEF ⇒ 0x40C851D962EA73FB
	TEST_AR_ORRI         8, rev.b, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 2, 0x40C851D962EA73FB

	@@ k=1：源全 1 ⇒ 全 1
	TEST_AR_ORRI         9, rev.b, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 1, 0xFFFFFFFFFFFFFFFF

	@@ k=2：0xD2(1101_0010) ⇒ 0x87（字节内 4 个 2 位单元 11|01|00|10 倒序 ⇒ 10|00|01|11）
	TEST_AR_ORRI        10, rev.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000D2, 2, 0x0000000000000087

	@@ 源 0 ⇒ 结果 0（目的初值全 1 被覆盖）
	TEST_AR_ORRI        11, rev.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 1, 0x0000000000000000

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x01 ⇒ 0x80
	TEST_AR_ORRI        12, rev.b, rd9, 0x0000000000000001, rd9, 0x0000000000000001, 1, 0x0000000000000080

	@@ 原地 k=4：0x0123456789ABCDEF ⇒ 0x1032547698BADCFE
	TEST_AR_ORRI        13, rev.b, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, 4, 0x1032547698BADCFE

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRI        14, rev.b, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 4, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 15, rev.b, ILLI, rd0, rd6, 1

	@@ legality（encode_onehot）：k=3 非 one-hot ⇒ ILLI
	TEST_FAULT_ALU_ORRI 16, rev.b, ILLI, rd5, rd6, 3

	@@ legality（encode_onehot）：k=8（恒等档，k 须 < 8）⇒ ILLI
	TEST_FAULT_ALU_ORRI 17, rev.b, ILLI, rd5, rd6, 8

	__TEST_SECTIONS
