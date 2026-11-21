@@ cfx2rc_crrr_cfx.S — cfx2rc cfxHA, cgHB, rcHC, rdHD（crrr, opc 0x7B）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §4`）；册目录 `tests/inst/11-cfx/`
@@ id：cfx2rc_crrr_cfx　形式：crrr　opc：0x7B　mask：0xFF000000　value：0x7B000000
@@ 语义：cfx_<cfxHA>_cgHB_rcHC ← rdHD（rd 寄存器组 → cfx 寄存器；`spec/SimRISC-11 §4`）
@@   写不存在/只读的 cg·rc ⇒ CFXREG；reserved cfxha ⇒ ILLI；rd0 作源 ⇒ 写入 0
@@   （rd0 恒读出 0，见 `spec/SimRISC-00 §2`）；Tiny 上 `switch_run_mode` 写入被忽略、
@@   `excp_vector` 写入忽略低 2 位（`spec/Kaiwu §2`、`spec/DADAO-13 §1`）。
@@ 编码：crrr = opc[31:24] | cfxha[23:18] | cghb[17:12] | rchc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 9 / boundary 6 / overlap 2（链例 17 + 故障例 7）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：写入的读回用 `cfx2rd`（该 id 由同册独立文件单独覆盖，不借被测的写通路自证）；
@@   期望值按 `spec/DADAO-12 §3.5/§3.8`、`spec/DADAO-13 §1` 与 `spec/Kaiwu §1.1/§2` 内联
@@ GAP（不计入链例，见任务书完成区）：cg0–cg2、cg4 计数器/标识、cg5 rc5、cg6 暂存、
@@   cg8 rc1 在 chipyard RTL 上未实现（⇒ CFXREG）⇒ 三平台不一致，待 chipyard 任务补齐

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	set.rb rb20, HMON_BASE
	set.rb rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]              @@ 任何意外异常 ⇒ 故障落点（fail-fast）

	@@ ---- encoding（规范编码字直接执行，钉 mask/value 与字段位域）----
	@@ 0x7B0C50C5 = cfx3 / cg5 rc3（excp_cause_ip，RW）/ rd5
	set.rd	rd5, 0x0123456789ABCDEF
	.dd.t32	0x7B0C50C5
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD   1, rd6, 0x0123456789ABCDEF

	@@ 0x7B0C50FF = cfx3 / cg5 rc3 / rd63（rd 字段最大号）
	set.rd	rd63, 0xDEADBEEFCAFEF00D
	.dd.t32	0x7B0C50FF
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD   2, rd6, 0xDEADBEEFCAFEF00D

	@@ ---- semantic：可写寄存器的 64 位全宽写入 ----
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_hmon, cg5, rc3, rd5
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD   3, rd6, 0xFFFFFFFFFFFFFFFF

	set.rd	rd5, 0x0000000000000000
	cfx2rc	cfx_hmon, cg5, rc3, rd5
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD   4, rd6, 0x0000000000000000

	@@ excp_prev_run_mode（cg5 rc0，RW）：写入 2（supv）后读回 2，随后恢复 3（hypv）
	set.rd	rd5, 0x0000000000000002
	cfx2rc	cfx_hmon, cg5, rc0, rd5
	cfx2rd	cfx_hmon, cg5, rc0, rd6
	__CHECK_RD   5, rd6, 0x0000000000000002
	set.rd	rd5, 0x0000000000000003
	cfx2rc	cfx_hmon, cg5, rc0, rd5
	cfx2rd	cfx_hmon, cg5, rc0, rd6
	__CHECK_RD   6, rd6, 0x0000000000000003

	@@ switch_run_mode（cg3 rc8）：Tiny 忽略写入，读回保存值 3（`spec/Kaiwu §2`）
	set.rd	rd5, 0x0000000000000000
	cfx2rc	cfx_hmon, cg3, rc8, rd5
	cfx2rd	cfx_hmon, cg3, rc8, rd6
	__CHECK_RD   7, rd6, 3

	@@ excp_vector（cg3 rc10）：写入忽略低 2 位（`spec/DADAO-13 §1`），读回对齐值；随后复位
	set.rd	rd5, (HMON_BASE + 7)
	cfx2rc	cfx_hmon, cg3, rc10, rd5
	cfx2rd	cfx_hmon, cg3, rc10, rd6
	__CHECK_RD   8, rd6, (HMON_BASE + 4)
	set.rd	rd5, HMON_BASE
	cfx2rc	cfx_hmon, cg3, rc10, rd5
	cfx2rd	cfx_hmon, cg3, rc10, rd6
	__CHECK_RD   9, rd6, HMON_BASE

	@@ power 的 excp_vector（BootROM 起始）：写入同值（幂等）
	set.rd	rd5, BOOTROM_BASE
	cfx2rc	cfx_power, cg3, rc10, rd5
	cfx2rd	cfx_power, cg3, rc10, rd6
	__CHECK_RD  10, rd6, BOOTROM_BASE

	@@ cfx_intr_mask（cg3 rc4，RW）：整 64 位写入/读回
	set.rd	rd5, 0x0123456789ABCDEF
	cfx2rc	cfx_hmon, cg3, rc4, rd5
	cfx2rd	cfx_hmon, cg3, rc4, rd6
	__CHECK_RD  11, rd6, 0x0123456789ABCDEF

	@@ ---- boundary：intr mask 全 0 与复位值（全 1）----
	set.rd	rd5, 0x0000000000000000
	cfx2rc	cfx_hmon, cg3, rc4, rd5
	cfx2rd	cfx_hmon, cg3, rc4, rd6
	__CHECK_RD  12, rd6, 0x0000000000000000
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_hmon, cg3, rc4, rd5
	cfx2rd	cfx_hmon, cg3, rc4, rd6
	__CHECK_RD  13, rd6, 0xFFFFFFFFFFFFFFFF

	@@ ---- boundary：rd0 作源 ⇒ 写入 0（rd0 恒读出 0）----
	cfx2rc	cfx_hmon, cg5, rc3, rd0
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD  14, rd6, 0x0000000000000000
	@@ 帧恢复：cause_ip 写回本文件 .text 内的确定性地址
	set.rd	rd5, (ENTRY + 4)
	cfx2rc	cfx_hmon, cg5, rc3, rd5
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD  15, rd6, (ENTRY + 4)

	@@ ---- overlap：同一 cfx 寄存器连续写（后写覆盖前写；再写回旧值）----
	set.rd	rd5, 0x1111111111111111
	cfx2rc	cfx_hmon, cg5, rc3, rd5
	set.rd	rd5, 0x2222222222222222
	cfx2rc	cfx_hmon, cg5, rc3, rd5
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD  16, rd6, 0x2222222222222222
	set.rd	rd5, 0x1111111111111111
	cfx2rc	cfx_hmon, cg5, rc3, rd5
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__CHECK_RD  17, rd6, 0x1111111111111111

	__TEST_END

	@@ ---- 故障例（同镜像故障链）----
	@@ reserved cfxha ⇒ ILLI（编号 6/61 分属两个保留段）
	TEST_FAULT_ENC  18, ILLI,   0x7B183105, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  19, ILLI,   0x7BF43105, rb12, TEST_DATA, rd11, 0

	@@ 已分配但 Tiny 未实现的 cfx（cfx5 / cfx32）⇒ CFXREG
	TEST_FAULT_ENC  20, CFXREG, 0x7B143105, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  21, CFXREG, 0x7B803105, rb12, TEST_DATA, rd11, 0

	@@ 只读/硬件写寄存器（cg5 rc2 cause_id、cg7 rc0 空间描述）⇒ CFXREG
	TEST_FAULT_ENC  22, CFXREG, 0x7B0C5085, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  23, CFXREG, 0x7B0C7005, rb12, TEST_DATA, rd11, 0

	@@ 已实现 cfx 的保留 rc（cg3 rc9）⇒ CFXREG
	TEST_FAULT_ENC  24, CFXREG, 0x7B0C3245, rb12, TEST_DATA, rd11, 0

	__TEST_SECTIONS
