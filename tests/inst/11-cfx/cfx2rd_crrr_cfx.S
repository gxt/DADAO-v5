@@ cfx2rd_crrr_cfx.S — cfx2rd cfxHA, cgHB, rcHC, rdHD（crrr, opc 0x7A）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §4`）；册目录 `tests/inst/11-cfx/`
@@ id：cfx2rd_crrr_cfx　形式：crrr　opc：0x7A　mask：0xFF000000　value：0x7A000000
@@ 语义：rdHD ← cfx_<cfxHA>_cgHB_rcHC（cfx 寄存器 → rd 寄存器组；`spec/SimRISC-11 §4`）
@@   目标 cfx 为 reserved（6–14、16–31、35–61）⇒ ILLI；目标为已分配但本 profile 未实现的
@@   cfx（Tiny：cfx0/1/2/4/5/32/33/34…）或已实现 cfx 的未定义/只写 cg·rc ⇒ CFXREG
@@   （`spec/Kaiwu §3`；`contracts/legality_rules.yaml` `encode_cfx_reserved`）。
@@ 编码：crrr = opc[31:24] | cfxha[23:18] | cghb[17:12] | rchc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 13 / boundary 5 / overlap 2（链例 22 + 故障例 7）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：被读寄存器取 Tiny 已实现的 cfx3(hmon)/cfx63(power) 的 cg3/cg5/cg7（`spec/Kaiwu §3`）；
@@   期望值按 `spec/DADAO-12 §3.5/§3.8`、`§4.12` 与 `spec/Kaiwu §1.1` 的地址图内联
@@ GAP（不计入链例，见任务书完成区）：cfx 共有寄存器 cg0–cg2、cg4（cfx_id/version/计数器/
@@   scratch_regs_num）、cg5 rc5、cg6（暂存）、cg8 rc1 在 chipyard RTL 上未实现（⇒ CFXREG），
@@   QEMU/gem5 已实现 ⇒ 三平台不一致，待 chipyard 任务补齐后再加例

	.include "tests/inst/macros/inst_test.inc"

@@ ---- 本文件局部宏（不改共享宏层）----
@@ 任何意外异常都落到固件 hmon 的返回槽：先指向 TEST_PAD（故障落点，按监控码退出 = fail-fast）
	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE
	LOAD_ADDR rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]

	@@ ---- encoding（规范编码字直接执行，钉 mask/value 与字段位域）----
	@@ 0x7A0C3285 = cfx3 / cg3 / rc10（hypv excp vector）/ rd5 ⇒ hmon SRAM 起始
	.dd.t32	0x7A0C3285
	__CHECK_RD   1, rd5, HMON_BASE

	@@ 0x7AFC3285 = cfx63（power）/ cg3 / rc10 / rd5 ⇒ BootROM 起始（复位向量）
	.dd.t32	0x7AFC3285
	__CHECK_RD   2, rd5, BOOTROM_BASE

	@@ ---- semantic：hmon 的 cg3 行（hypv 四类同步 mask / switch_run_mode）----
	cfx2rd	cfx_hmon, cg3, rc0, rd5
	__CHECK_RD   3, rd5, 0x7FFFFFFFFFFFFFF7      @@ hypv cfxtrap mask 复位值（DADAO-13 §1）
	cfx2rd	cfx_power, cg3, rc0, rd5
	__CHECK_RD   4, rd5, 0xFFFFFFFFFFFFFFF7      @@ power 的同一 mask 复位值
	cfx2rd	cfx_hmon, cg3, rc8, rd5
	__CHECK_RD   5, rd5, 3                      @@ switch_run_mode：Tiny 恒 hypv，读回保存值 3

	@@ ---- semantic：hmon 的异常帧（cg5）----
	cfx2rd	cfx_hmon, cg5, rc0, rd5
	__CHECK_RD   6, rd5, 3                      @@ excp_prev_run_mode = hypv（启动移交的 trap）
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	__CHECK_RD   7, rd5, 1                      @@ excp_cause_id = CFXTRAP（启动移交留下有效帧）

	@@ ---- semantic：hmon 的 cg7 空间描述（`spec/DADAO-12 §3.8`）----
	cfx2rd	cfx_hmon, cg7, rc0, rd5
	__CHECK_RD   8, rd5, 3                      @@ desc：exists | SRAM
	cfx2rd	cfx_hmon, cg7, rc1, rd5
	__CHECK_RD   9, rd5, (HMON_BASE - (3 * 0x40000000000))   @@ start：核内偏移 0x3FF_0000_0000
	cfx2rd	cfx_hmon, cg7, rc2, rd5
	__CHECK_RD  10, rd5, 0x10000                @@ size：64 KiB
	cfx2rd	cfx_hmon, cg7, rc3, rd5
	__CHECK_RD  11, rd5, 7                      @@ attr：R | W | X

	@@ ---- semantic：power 的 cg7 空间描述（BootROM = ROM、R|X）----
	cfx2rd	cfx_power, cg7, rc0, rd5
	__CHECK_RD  12, rd5, 5                      @@ desc：exists | ROM
	cfx2rd	cfx_power, cg7, rc1, rd5
	__CHECK_RD  13, rd5, (BOOTROM_BASE - (63 * 0x40000000000))
	cfx2rd	cfx_power, cg7, rc2, rd5
	__CHECK_RD  14, rd5, 0x10000
	cfx2rd	cfx_power, cg7, rc3, rd5
	__CHECK_RD  15, rd5, 5                      @@ attr：R | X

	@@ ---- boundary：不存在的空间块读 0（`exists = 0` ⇒ 其余字段 0）----
	cfx2rd	cfx_hmon, cg7, rc4, rd5             @@ 块 1 的描述字
	__CHECK_RD  16, rd5, 0
	cfx2rd	cfx_hmon, cg7, rc63, rd5            @@ 块 15 的 attr
	__CHECK_RD  17, rd5, 0

	@@ ---- boundary：cg3 rc4（异步中断来源掩码）复位为全 1 ----
	cfx2rd	cfx_hmon, cg3, rc4, rd5
	__CHECK_RD  18, rd5, 0xFFFFFFFFFFFFFFFF

	@@ ---- boundary：rd 字段边界 rd63（最大目的号）与 rd0（零寄存器，写被丢弃）----
	set.rd	rd63, 0
	cfx2rd	cfx_hmon, cg3, rc10, rd63
	__CHECK_RD  19, rd63, HMON_BASE
	cfx2rd	cfx_hmon, cg3, rc10, rd0
	__CHECK_RD  20, rd0, 0

	@@ ---- overlap：目的号与 cfxha 同号（rd3 / cfx3）不改变语义，且读是幂等的 ----
	cfx2rd	cfx_hmon, cg7, rc2, rd3
	__CHECK_RD  21, rd3, 0x10000
	cfx2rd	cfx_hmon, cg7, rc2, rd3
	__CHECK_RD  22, rd3, 0x10000

	__TEST_END

	@@ ---- 故障例（同镜像故障链：异常不返回到被测指令之后）----
	@@ reserved cfxha ⇒ ILLI（`encode_cfx_reserved`；编号 6/16/35 分属三个保留段）
	TEST_FAULT_ENC  23, ILLI,   0x7A183285, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  24, ILLI,   0x7A403285, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  25, ILLI,   0x7A8C3285, rb12, TEST_DATA, rd11, 0

	@@ 已分配但 Tiny 未实现的 cfx（cfx5 cache / cfx32 pmem）⇒ CFXREG
	TEST_FAULT_ENC  26, CFXREG, 0x7A143285, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  27, CFXREG, 0x7A803285, rb12, TEST_DATA, rd11, 0

	@@ 已实现 cfx 的未定义 rc（cg5 rc1、cg3 rc9 保留）⇒ CFXREG
	TEST_FAULT_ENC  28, CFXREG, 0x7A0C5045, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  29, CFXREG, 0x7A0C3245, rb12, TEST_DATA, rd11, 0

	__TEST_SECTIONS
