@@ rev.t_orri_rd.S — rev.t rdHB, rdHC, immu6（orri, opc 0x41／ha 0x0C）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：rev.t_orri_rd　形式：orri　opc：0x41／ha 0x0C　mask：0xFFFC0000　value：0x41300000　目的银行：RD
@@ 语义：rdHB ← 把源按 **32 位块**（两块一律处理）各切成 32/k 个 k 位单元、块内单元倒序（单元内位序不变）；k=8 ⇒ bswap32、k=1 ⇒ 块内位反序
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；k 须 one-hot 且 k < 32（合法档 1/2/4/8/16）⇒ 0/3/5/…/32/63 触发 ILLI（`encode_onehot`）；源可为 rd0
@@ 边界/覆盖：边界：两块都处理（高 32 位不是保持/清零）、k=1 不是 64 位整体反序、k=16 半字交换、最高合法档 16
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic+boundary+overlap 18（链例 20 + 故障例 6）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rev.t(rd6, k=8)（两块各自 bswap32，**块位置不交换**）的规范编码字
	@@ 规范编码字 0x41305188（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 8）
	__LI	rd6, 0x0123456789ABCDEF
	.dd.t32	0x41305188
	__CHECK_RD   1, rd5, 0x67452301EFCDAB89

	@@ [encoding 2] 最高寄存器作目的（rd63）+ k=16 半字交换
	@@ 规范编码字 0x4133F050（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 16）
	__LI	rd1, 0x1122334455667788
	.dd.t32	0x4133F050
	__CHECK_RD   2, rd63, 0x3344112277885566

	@@ [3] k=8：两个 32 位块各自 bswap32、块位置不变（0x11223344_55667788 ⇒ 0x44332211_88776655）
	TEST_AR_ORRI        3, rev.t, rd5, 0x0000000000000000, rd6, 0x1122334455667788, 8, 0x4433221188776655

	@@ [4] k=8 且源高 32 位为 0 ⇒ 纯 bswap32（0x00000000_01020304 ⇒ 0x00000000_04030201）
	TEST_AR_ORRI        4, rev.t, rd5, 0x0000000000000000, rd6, 0x0000000001020304, 8, 0x0000000004030201

	@@ [5] k=16：每块两半字交换（0xAABBCCDD_EEFF0011 ⇒ 0xCCDDAABB_0011EEFF）
	TEST_AR_ORRI        5, rev.t, rd5, 0x0000000000000000, rd6, 0xAABBCCDDEEFF0011, 16, 0xCCDDAABB0011EEFF

	@@ [6] k=4：每块 8 个 nibble 块内倒序（0x01234567_89ABCDEF ⇒ 0x76543210_FEDCBA98）
	TEST_AR_ORRI        6, rev.t, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 4, 0x76543210FEDCBA98

	@@ [7] k=2：每块 16 个 2 位单元块内倒序（0x01234567_89ABCDEF ⇒ 0xD951C840_FB73EA62）
	TEST_AR_ORRI        7, rev.t, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 2, 0xD951C840FB73EA62

	@@ [8] k=1：每块内位反序（**不是** 64 位整体反序；0x80000000 ⇒ 0x00000000_00000001）
	TEST_AR_ORRI        8, rev.t, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 1, 0x0000000000000001

	@@ [9] k=1：高块同样处理（0x00000001_00000000 ⇒ 0x80000000_00000000）
	TEST_AR_ORRI        9, rev.t, rd5, 0x0000000000000000, rd6, 0x0000000100000000, 1, 0x8000000000000000

	@@ [10] k=8 且源高 32 位全 1：高块参与反转 ⇒ 0xFFFFFFFF_01000000
	TEST_AR_ORRI       10, rev.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, 8, 0xFFFFFFFF01000000

	@@ [11] k=16：高块参与（0x8000000000000000 ⇒ 0x0000800000000000）
	TEST_AR_ORRI       11, rev.t, rd5, 0x0000000000000000, rd6, 0x8000000000000000, 16, 0x0000800000000000

	@@ [12] k=2 全 1 对称源 ⇒ 原值（不变量自检）
	TEST_AR_ORRI       12, rev.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 2, 0xFFFFFFFFFFFFFFFF

	@@ [13] k=8：0x00FF00FF00FF00FF ⇒ 0xFF00FF00FF00FF00（字节交换的交替模式）
	TEST_AR_ORRI       13, rev.t, rd5, 0x0000000000000000, rd6, 0x00FF00FF00FF00FF, 8, 0xFF00FF00FF00FF00

	@@ [14] rd0 作源：rev.t(0, k=8) = 0
	TEST_AR_ORRI       14, rev.t, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 8, 0x0000000000000000

	@@ [15] 源=目（原地）：rd9 = rev.t(rd9, k=8)
	TEST_AR_ORRI       15, rev.t, rd9, 0x0102030405060708, rd9, 0x0102030405060708, 8, 0x0403020108070605

	@@ [16] （YAML semantic 并入）k=1：0x0123456789ABCDEF ⇒ 0xE6A2C480F7B3D591
	TEST_AR_ORRI       16, rev.t, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 1, 0xE6A2C480F7B3D591

	@@ [17] （YAML semantic 并入）k=16：0x0123456789ABCDEF ⇒ 0x45670123CDEF89AB
	TEST_AR_ORRI       17, rev.t, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 16, 0x45670123CDEF89AB

	@@ [18] （YAML semantic 并入）k=8：0x0123456789ABCDEF ⇒ 0x67452301EFCDAB89
	TEST_AR_ORRI       18, rev.t, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, 8, 0x67452301EFCDAB89

	@@ [19] （YAML boundary 并入）k=1 全 1 源 ⇒ 全 1（逐块逆序不变量）
	TEST_AR_ORRI       19, rev.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 1, 0xFFFFFFFFFFFFFFFF

	@@ [20] （YAML boundary 并入）k=1 且源为 rd0（读出 0）⇒ 0
	TEST_AR_ORRI       20, rev.t, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 1, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [21] k=0 非 one-hot ⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 21, rev.t, ILLI, rd5, rd6, 0

	@@ [22] k=3 非 one-hot ⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 22, rev.t, ILLI, rd5, rd6, 3

	@@ [23] （YAML legality 并入）k=5 非 one-hot ⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 23, rev.t, ILLI, rd5, rd6, 5

	@@ [24] k=32 = S ⇒ ILLI（`encode_onehot` 的 k ≥ S）
	TEST_FAULT_ALU_ORRI 24, rev.t, ILLI, rd5, rd6, 32

	@@ [25] k=63 非 one-hot ⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 25, rev.t, ILLI, rd5, rd6, 63

	@@ [26] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 26, rev.t, ILLI, rd0, rd6, 8

	__TEST_SECTIONS
