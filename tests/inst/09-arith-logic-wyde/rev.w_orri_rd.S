@@ rev.w_orri_rd.S — rev.w rdHB, rdHC, immu6（orri, opc 0x42／ha 0x0C）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：rev.w_orri_rd　形式：orri　opc：0x42／ha 0x0C　mask：0xFFFC0000　value：0x42300000　目的银行：RD
@@ 语义：rdHB ← 逐 16 位块反转：64 位源切成 4 个 S=16 的块，每块按 k 位单元倒序（单元内位序不变），四块一律处理（`spec/SimRISC-09 §2.1`、总述 `spec/SimRISC-04 §2.2.1`）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；k 须 one-hot 且 k<16（{1,2,4,8}），否则 ILLI（`encode_onehot`）；源可为 rd0；rdHB==rdHC 合法
@@ 边界/覆盖：覆盖 k=1/2/4/8 四档、k=8 即逐块 bswap16、源高位块参与、rd0 作源、原地反转
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 9 / semantic 7 / boundary 8 / overlap 3（链例 21 + 故障例 8）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word 与 opcodes.yaml mask/value 一致；rdhb=rd1（非 rd0）、rdhc=rd2、immu6=8（合法 one-hot 档）
	set.rd	rd2, 0x0000000000000000
	.dd.t32	0x42301088
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）rev.w: S=16, k=1, rd2=0x0123456789ABCDEF → rd1=0xC480E6A2D591F7B3（oracle 大整数独立派生）
	set.rd	rd2, 0x0123456789ABCDEF
	.dd.t32	0x42301081
	__CHECK_RD   2, rd1, 0xC480E6A2D591F7B3

	@@ [3] （原 YAML 并入）rev.w: S=16, k=2, rd2=0x0123456789ABCDEF → rd1=0xC840D951EA62FB73（oracle 大整数独立派生）
	set.rd	rd2, 0x0123456789ABCDEF
	.dd.t32	0x42301082
	__CHECK_RD   3, rd1, 0xC840D951EA62FB73

	@@ [4] （原 YAML 并入）rev.w: S=16, k=4, rd2=0x0123456789ABCDEF → rd1=0x32107654BA98FEDC（oracle 大整数独立派生）
	set.rd	rd2, 0x0123456789ABCDEF
	.dd.t32	0x42301084
	__CHECK_RD   4, rd1, 0x32107654BA98FEDC

	@@ [5] （原 YAML 并入）rev.w: S=16, k=8, rd2=0x0123456789ABCDEF → rd1=0x23016745AB89EFCD（oracle 大整数独立派生）
	set.rd	rd2, 0x0123456789ABCDEF
	.dd.t32	0x42301088
	__CHECK_RD   5, rd1, 0x23016745AB89EFCD

	@@ [6] （原 YAML 并入）端序敏感（大端 k=8）：rd2 的大端字节序 01 02 03 04 05 06 07 08 → 每个 16 位块内反转字节序 → rd1=0x0201040306050807
	set.rd	rd2, 0x0102030405060708
	.dd.t32	0x42301088
	__CHECK_RD   6, rd1, 0x0201040306050807

	@@ [7] （原 YAML 并入）boundary rev.w k=8: 源高 48 位为 0 ⇒ 结果高 48 位亦为 0（bswap 前提）
	set.rd	rd2, 0x0000000001020304
	.dd.t32	0x42301088
	__CHECK_RD   7, rd1, 0x0000000002010403

	@@ [8] （原 YAML 并入）boundary rev.w k=1: rdHC=0 ⇒ rdHB=0
	set.rd	rd2, 0x0000000000000000
	.dd.t32	0x42301081
	__CHECK_RD   8, rd1, 0x0000000000000000

	@@ [9] （原 YAML 并入）boundary rev.w k=1: rdHC 全 1 ⇒ rdHB 全 1（全 1 图案逐块逆序不变）
	set.rd	rd2, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42301081
	__CHECK_RD   9, rd1, 0xFFFFFFFFFFFFFFFF

	@@ [10] （原 YAML 并入）boundary rev.w k=1: rdHB == rdHC == rd3（原地反转，允许）
	set.rd	rd3, 0x0123456789ABCDEF
	.dd.t32	0x423030C1
	__CHECK_RD   10, rd3, 0xC480E6A2D591F7B3

	@@ [11] （原 YAML 并入）boundary rev.w k=1: rdHC=rd0（源读出 0，合法）⇒ rdHB=0
	.dd.t32	0x42301001
	__CHECK_RD   11, rd1, 0x0000000000000000

	@@ [12] 最大寄存器字段：rd63 = rev.w(rd1, k=4)，0xABCDEF01 逐块 4 位单元倒序 ⇒ 0x0000DCBA10FE
	set.rd	rd1, 0x00000000ABCDEF01
	.dd.t32	0x4233F044
	__CHECK_RD   12, rd63, 0x00000000DCBA10FE

	@@ [13] k=2：0x8001 每块切成 8 个 2 位单元倒序 ⇒ 0x4002
	TEST_AR_ORRI     13, rev.w, rd5, 0x0000000000000000, rd6, 0x0000000000008001, 2, 0x0000000000004002

	@@ [14] k=4：0x1234 ⇒ 0x4321（单元倒序、单元内位序不变）
	TEST_AR_ORRI     14, rev.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, 4, 0x0000000000004321

	@@ [15] k=1：0x8000 块内位反序 ⇒ 0x0001（不是 64 位整体位反序）
	TEST_AR_ORRI     15, rev.w, rd5, 0x0000000000000000, rd6, 0x0000000000008000, 1, 0x0000000000000001

	@@ [16] k=8 只处理低块而源高块非零：0xFFFF0000 ⇒ 0xFFFF0000（逐块各自反转）
	TEST_AR_ORRI     16, rev.w, rd5, 0x0000000000000000, rd6, 0x00000000FFFF0000, 8, 0x00000000FFFF0000

	@@ [17] k=8：0x0102030405060708 ⇒ 0x0201040306050807（四块逐块 bswap16）
	TEST_AR_ORRI     17, rev.w, rd5, 0x0000000000000000, rd6, 0x0102030405060708, 8, 0x0201040306050807

	@@ [18] rd0 作源 C ⇒ 0
	TEST_AR_ORRI     18, rev.w, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 8, 0x0000000000000000

	@@ [19] 目的=源C（原地）：rd9 = rev.w(rd9=−1, k=1) ⇒ −1（全 1 图案不变）
	TEST_AR_ORRI     19, rev.w, rd9, 0xFFFFFFFFFFFFFFFF, rd9, 0xFFFFFFFFFFFFFFFF, 1, 0xFFFFFFFFFFFFFFFF

	@@ [20] 目的=源C（原地）：rd9 = rev.w(rd9=0x1234, k=4) ⇒ 0x4321
	TEST_AR_ORRI     20, rev.w, rd9, 0x0000000000001234, rd9, 0x0000000000001234, 4, 0x0000000000004321

	@@ [21] 目的=源C（原地）：rd9 = rev.w(rd9=0x0001, k=8) ⇒ 0x0100
	TEST_AR_ORRI     21, rev.w, rd9, 0x0000000000000001, rd9, 0x0000000000000001, 8, 0x0000000000000100

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [22] （原 YAML 并入）legality rev.w: k=0 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_ALU_ORRI 22, rev.w, ILLI, rd1, rd2, 0

	@@ [23] （原 YAML 并入）legality rev.w: k=3 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_ALU_ORRI 23, rev.w, ILLI, rd1, rd2, 3

	@@ [24] （原 YAML 并入）legality rev.w: k=5 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_ALU_ORRI 24, rev.w, ILLI, rd1, rd2, 5

	@@ [25] （原 YAML 并入）legality rev.w: k=16 == S（恒等档） ⇒ ILLI（encode_onehot）
	TEST_FAULT_ALU_ORRI 25, rev.w, ILLI, rd1, rd2, 16

	@@ [26] （原 YAML 并入）legality rev.w: rdhb=rd0（目的）⇒ ILLI（dst_rd0）
	TEST_FAULT_ALU_ORRI 26, rev.w, ILLI, rd0, rd2, 8

	@@ [27] k=0 非 one-hot ⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 27, rev.w, ILLI, rd5, rd6, 0

	@@ [28] k=16 == S（恒等档）⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 28, rev.w, ILLI, rd5, rd6, 16

	@@ [29] k=32 > S ⇒ ILLI（`encode_onehot`）
	TEST_FAULT_ALU_ORRI 29, rev.w, ILLI, rd5, rd6, 32

	__TEST_SECTIONS
