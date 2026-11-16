@@ ext.uo_orrr_rd.S — ext.uo rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x20）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：ext.uo_orrr_rd　形式：orrr　opc：0x40／ha 0x20　mask：0xFFFC0000　value：0x40800000　目的银行：RD
@@ 语义：rdHB[hd:0] ← rdHC[hd:0]；rdHB[63:hd+1] ← 0（零扩展）；hd = rdHD[5:0]
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；
@@   hd 取 rdHD 低 6 位，**越界位忽略、不抛 ILLI**（用户裁定 2026-11-13；`spec/SimRISC-04 §2.2`
@@   已定稿 `hd = rdHD[5:0]`；QEMU/gem5 已按此修（`m13-qemu-010`/`m13-gem5-012`））
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 11 / overlap 3（链例 22 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联
@@ 起始位边界：0（只留 bit0）/ 31 / 63（等于 N ⇒ 整字复制）；**越界位忽略、不抛 ILLI**
@@   （用户裁定 2026-11-13：`hd = rdHD[5:0]`；rdHD=64 ⇒ hd=0、67 ⇒ 3、2^64−1 ⇒ 63）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = ext.uo(rd6, 2) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40805187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0F0F0F0F0F0F0F0F
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x40805187
	__CHECK_RD   1, rd5, 0x0000000000000007

	@@ 最高寄存器作目的（rd63）+ 起始位 63 的编码字（字段边界；整字复制）
	@@ 规范编码字 0x4083F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0123456789ABCDEF
	set.rd	rd2, 0x000000000000003F
	.dd.t32	0x4083F042
	__CHECK_RD   2, rd63, 0x0123456789ABCDEF

	@@ 起始位 2（YAML semantic 例）：bit2 为 1、只留 bit[2:0] ⇒ 0x7
	TEST_AR_ORRR         3, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x0000000000000007

	@@ 起始位 0 且 bit0 = 0 ⇒ 0（零扩展只看被保留的那一位）
	TEST_AR_ORRR         4, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FE, rd7, 0x0000000000000000, 0x0000000000000000

	@@ 起始位 0 且 bit0 = 1 ⇒ 1
	TEST_AR_ORRR         5, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x0000000000000001

	@@ 起始位 7：保留低字节 0xEF、高位清零
	TEST_AR_ORRR         6, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000007, 0x00000000000000EF

	@@ 起始位 63 = N ⇒ 整字复制（YAML boundary 例）
	TEST_AR_ORRR         7, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0x000000000000003F, 0x0123456789ABCDEF

	@@ rd0 作源 C（读出 0）：保留 0 位、扩展 0 ⇒ 0
	TEST_AR_ORRR         8, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x000000000000001F, 0x0000000000000000

	@@ 起始位 32：保留低 33 位（bit32 是 c 的 bit0 of 0x01234567 ⇒ 1）
	TEST_AR_ORRR         9, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000020, 0x0000000189ABCDEF

	@@ 起始位 62：全 1 只丢 bit63 ⇒ 0x7FFF..F
	TEST_AR_ORRR        10, ext.uo, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x000000000000003E, 0x7FFFFFFFFFFFFFFF

	@@ 起始位 8 且 bit8 = 0 ⇒ 0（保留位段全 0）
	TEST_AR_ORRR        11, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF00000000, rd7, 0x0000000000000008, 0x0000000000000000

	@@ 起始位 63 且符号位为 1：零扩展 ⇒ 整字不变（不补 1）
	TEST_AR_ORRR        12, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0x000000000000003F, 0x8000000000000000

	@@ 起始位 31：保留低 32 位、高位清零（全 1 源 ⇒ 0xFFFFFFFF）
	TEST_AR_ORRR        13, ext.uo, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x000000000000001F, 0x00000000FFFFFFFF

	@@ 目的=源C（原地）
	TEST_AR_ORRR        14, ext.uo, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, rd10, 0x0000000000000004, 0x000000000000000F

	@@ 目的=源D（原地）：目的旧值 8 就是起始位
	TEST_AR_ORRR        15, ext.uo, rd9, 0x0000000000000008, rd10, 0x000000000000FFFF, rd9, 0x0000000000000008, 0x00000000000001FF

	@@ 两源同名：0x7 在起始位 7 ⇒ 低 8 位原样
	TEST_AR_ORRR        16, ext.uo, rd9, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000007, rd11, 0x0000000000000007, 0x0000000000000007

	@@ ---- 起始位越界（`rdHD > 63`）：`hd = rdHD[5:0]`、越界位忽略、**不抛 ILLI** ----
	@@ 依据 `spec/SimRISC-04 §2.2`：「`orrr` 形式的 `hd` 取 `rdHD` 的低 6 位（`hd = rdHD[5:0]`），
	@@   `rdHD` 的更高位被忽略、不触发异常」（`m13-spec-008` 定稿）。
	@@ 用户裁定（2026-11-13，`ISS-422`）：「`ext.*` 的 orrr 形式，`rdHD` 取低 6 位作起始位 `hd`
	@@   后继续执行，不抛 ILLI」⇒ 以下 6 例期望按手算给（抄任一平台输出当期望 = 禁止）。

	@@ 点 17 = 跨用例不变量基线（rdHD=0）：hd=0 ⇒ 只留 bit0
	@@   手算：src=0x0123456789ABCDEF，bit0 = (0xEF & 1) = 1 ⇒ [0:0]=1、[63:1]=0 ⇒ 0x1
	TEST_AR_ORRR        17, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000000, 0x0000000000000001

	@@ rdHD=64（0x40）：64 & 0x3F = 0 ⇒ 与点 17 同值（bit6 越界、忽略）
	@@   手算：hd=0；src 同上 bit0=1 ⇒ 0x1（与点 17 逐字节相同 = 不变量 A）
	TEST_AR_ORRR        18, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000040, 0x0000000000000001

	@@ rdHD=64 且 bit0 = 0：hd=0 ⇒ 结果 0；与点 4（rdHD=0、同源值 0x…FE）配对 = 不变量 B
	@@   手算：src=0x00000000000000FE，bit0 = 0 ⇒ [0:0]=0、[63:1]=0 ⇒ 0x0
	TEST_AR_ORRR        19, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FE, rd7, 0x0000000000000040, 0x0000000000000000

	@@ rdHD=67（0x43）：67 & 0x3F = 3 ⇒ 只留 [3:0]
	@@   手算：src=0x0123456789ABCDE9，低 4 位 = 0x9 ⇒ [3:0]=0x9、[63:4]=0 ⇒ 0x9
	TEST_AR_ORRR        20, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDE9, rd7, 0x0000000000000043, 0x0000000000000009

	@@ rdHD=63：hd=63 = N ⇒ 整字复制（合法边界，非越界）
	@@   手算：保留 [63:0] 全字、无扩展位 ⇒ 0x0123456789ABCDE9
	TEST_AR_ORRR        21, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDE9, rd7, 0x000000000000003F, 0x0123456789ABCDE9

	@@ rdHD=0xFFFF_FFFF_FFFF_FFFF：全 1 & 0x3F = 63 ⇒ 整字复制（高 58 位全部忽略）
	@@   手算：hd=63；src=0xFEDCBA9876543210 ⇒ 原样 0xFEDCBA9876543210
	TEST_AR_ORRR        22, ext.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFEDCBA9876543210, rd7, 0xFFFFFFFFFFFFFFFF, 0xFEDCBA9876543210

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     23, ext.uo, ILLI, rd0, rd6, rd7

	@@ 起始位越界（`rdHD > 63`）**不构成故障**：上述链例 17–22 已按 `hd = rdHD[5:0]` 收录，
	@@   故本文件无「越界 ⇒ ILLI」故障例（用户裁定 2026-11-13；语义由 `m13-spec-008` 定稿）。

	__TEST_SECTIONS
