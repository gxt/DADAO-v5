@@ ext.uo_orri_rd.S — ext.uo rdHB, rdHC, immu6（orri, opc 0x40／ha 0x28）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：ext.uo_orri_rd　形式：orri　opc：0x40／ha 0x28　mask：0xFFFC0000　value：0x40A00000　目的银行：RD
@@ 语义：rdHB[hd:0] ← rdHC[hd:0]；rdHB[63:hd+1] ← 0（零扩展）；hd = immu6（0..63）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；
@@   `immu6=0` 合法（`legality_rules.yaml::immu6_zero` 明确不适用于移位/扩展的 orri 形式）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 6 / boundary 3 / overlap 1（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ rd5 = ext.uo(rd6, 2) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40A05182（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | immu6）
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x0F0F0F0F0F0F0F0F
	.dd.t32	0x40A05182
	__CHECK_RD   1, rd5, 0x0000000000000007

	@@ 最高寄存器作目的（rd63）+ 最大起始位 63 的编码字（字段边界；整字复制）
	@@ 规范编码字 0x40A3F07F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | immu6）
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x8000000000000000
	.dd.t32	0x40A3F07F
	__CHECK_RD   2, rd63, 0x8000000000000000

	@@ 起始位 2（YAML semantic 例）：bit2 为 1、只留 bit[2:0] ⇒ 0x7
	TEST_AR_ORRI         3, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, 2, 0x0000000000000007

	@@ 起始位 0 且 bit0 = 0 ⇒ 0
	TEST_AR_ORRI         4, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FE, 0, 0x0000000000000000

	@@ 起始位 0 且 bit0 = 1 ⇒ 1
	TEST_AR_ORRI         5, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x0000000000000001

	@@ 起始位 7：保留低字节 0xEF、高位清零
	TEST_AR_ORRI         6, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, 7, 0x00000000000000EF

	@@ 起始位 63 = N ⇒ 整字复制（YAML boundary 例）
	TEST_AR_ORRI         7, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, 63, 0x0123456789ABCDEF

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRI         8, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 31, 0x0000000000000000

	@@ 起始位 32：保留低 33 位（bit32 = 1）
	TEST_AR_ORRI         9, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, 32, 0x0000000189ABCDEF

	@@ 起始位 62：全 1 只丢 bit63 ⇒ 0x7FFF..F
	TEST_AR_ORRI        10, ext.uo, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 62, 0x7FFFFFFFFFFFFFFF

	@@ 起始位 8 且 bit8 = 0 ⇒ 0
	TEST_AR_ORRI        11, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF00000000, 8, 0x0000000000000000

	@@ 目的=源C（原地）
	TEST_AR_ORRI        12, ext.uo, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, 4, 0x000000000000000F

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, ext.uo, ILLI, rd0, rd6, 2

	__TEST_SECTIONS
