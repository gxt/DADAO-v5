@@ ext.so_orrr_rd.S — ext.so rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x21）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：ext.so_orrr_rd　形式：orrr　opc：0x40／ha 0x21　mask：0xFFFC0000　value：0x40840000　目的银行：RD
@@ 语义：rdHB[hd:0] ← rdHC[hd:0]；rdHB[63:hd+1] ← rdHC[hd]（符号扩展）；hd = rdHD[5:0]
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；
@@   hd 取 rdHD 低 6 位，**越界位忽略、不抛 ILLI**（用户裁定 2026-11-13；chipyard 即此口径，
@@   QEMU/gem5 判 ILLI 为缺陷 `ISS-422`；`spec/SimRISC-04 §2.2` 措辞待 spec 任务修正）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 6 / boundary 5 / overlap 3（链例 16 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联
@@ 起始位边界：0 / 31 / 63（等于 N ⇒ 整字复制）；**越界位忽略、不抛 ILLI**
@@   （用户裁定 2026-11-13：`hd = rdHD[5:0]`；chipyard 即此口径，QEMU/gem5 判 ILLI 为 `ISS-422` 缺陷）

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ rd5 = ext.so(rd6, 2) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40845187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0F0F0F0F0F0F0F0F
	__LI	rd7, 0x0000000000000002
	.dd.t32	0x40845187
	__CHECK_RD   1, rd5, 0xFFFFFFFFFFFFFFFF

	@@ 最高寄存器作目的（rd63）+ 起始位 63 的编码字（字段边界；整字复制）
	@@ 规范编码字 0x4087F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0123456789ABCDEF
	__LI	rd2, 0x000000000000003F
	.dd.t32	0x4087F042
	__CHECK_RD   2, rd63, 0x0123456789ABCDEF

	@@ 起始位 2 且 bit2 = 1 ⇒ 高位全 1（YAML semantic 例）
	TEST_AR_ORRR         3, ext.so, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ 起始位 0 且 bit0 = 1 ⇒ 全 1（符号就是 bit0）
	TEST_AR_ORRR         4, ext.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ 起始位 0 且 bit0 = 0 ⇒ 0
	TEST_AR_ORRR         5, ext.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FE, rd7, 0x0000000000000000, 0x0000000000000000

	@@ 起始位 7 且 bit7 = 1 ⇒ 保留低字节 0xEF、高位补 1
	TEST_AR_ORRR         6, ext.so, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFEF

	@@ 起始位 63 = N ⇒ 整字复制，符号扩展无位可补（YAML boundary 例）
	TEST_AR_ORRR         7, ext.so, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, rd7, 0x000000000000003F, 0x0123456789ABCDEF

	@@ rd0 作源 C（读出 0）：符号位 0、保留位 0 ⇒ 0
	TEST_AR_ORRR         8, ext.so, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x000000000000001F, 0x0000000000000000

	@@ 起始位 32 且 bit32 = 1 ⇒ 低 33 位保留、高位补 1
	TEST_AR_ORRR         9, ext.so, rd5, 0x0000000000000000, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000020, 0xFFFFFFFF89ABCDEF

	@@ 起始位 62 且 bit62 = 1 ⇒ 全 1
	TEST_AR_ORRR        10, ext.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x000000000000003E, 0xFFFFFFFFFFFFFFFF

	@@ 起始位 8 且 bit8 = 1 ⇒ 0x00000000FFFFFFFF 的 bit8 = 1 ⇒ 全 1
	TEST_AR_ORRR        11, ext.so, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000008, 0xFFFFFFFFFFFFFFFF

	@@ 起始位 7 且 bit7 = 0 ⇒ 0
	TEST_AR_ORRR        12, ext.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCD00, rd7, 0x0000000000000007, 0x0000000000000000

	@@ 起始位 31：保留低 32 位；bit31 = 0 ⇒ 符号扩展补 0
	TEST_AR_ORRR        13, ext.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000007FFFFFFF, rd7, 0x000000000000001F, 0x000000007FFFFFFF

	@@ 目的=源C（原地）
	TEST_AR_ORRR        14, ext.so, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, rd10, 0x0000000000000004, 0x000000000000000F

	@@ 目的=源D（原地）：目的旧值 8 就是起始位
	TEST_AR_ORRR        15, ext.so, rd9, 0x0000000000000008, rd10, 0x000000000000FFFF, rd9, 0x0000000000000008, 0xFFFFFFFFFFFFFFFF

	@@ 两源同名：0x7 在起始位 7 ⇒ 低 8 位原样、符号位 0
	TEST_AR_ORRR        16, ext.so, rd9, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000007, rd11, 0x0000000000000007, 0x0000000000000007

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     17, ext.so, ILLI, rd0, rd6, rd7

	@@ 起始位越界（`rdHD > 63`）**未收录**：用户裁定（2026-11-13，`ISS-422`）口径为
	@@   `hd = rdHD[5:0]`（越界位忽略、不抛 ILLI）⇒ chipyard 行为正确；
	@@   QEMU/gem5 判 ILLI（`0xF8`）是缺陷、待修，故暂不写成故障例（见 `MIGRATION §6/017`）。

	__TEST_SECTIONS
