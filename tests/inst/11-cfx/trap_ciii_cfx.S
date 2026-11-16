@@ trap_ciii_cfx.S — trap cfxHA, immu18（ciii, opc 0x7F）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §2`）；册目录 `tests/inst/11-cfx/`
@@ id：trap_ciii_cfx　形式：ciii　opc：0x7F　mask：0xFF000000　value：0x7F000000
@@ 语义：把控制权转移到 cfxHA 的异常向量——按 `spec/DADAO-12 §5.2` 的 CFXTRAP 进入流程
@@   （`trap_num += 1`，保存 `excp_prev_run_mode`/`excp_cause_ip`/`excp_cause_id`（= 1<<0）/
@@   `excp_cause_info`（= 指令编码），跳到该 cfx 的 `<mode>_excp_vector`）。
@@   reserved cfxha（6–14、16–31、35–61）⇒ ILLI；已分配但本 profile 未实现的 cfx
@@   （Tiny：cfx0/1/2/4/5/32…）⇒ ILLI（`spec/Kaiwu §3`）；`immu18[17:8] == 0x3FF`
@@   （0x3FF00–0x3FFFF）为 semihosting 短路、**不进向量**（`spec/Kaiwu §5.1/§5.4`）。
@@ 编码：ciii = opc[31:24] | cfxha[23:18] | immu18[17:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 2（链例 9 + 故障例 6）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：一般 trap 经固件 hmon 的「保存-跳转」落到 `.org` 钉住的落点块
@@   （`spec/Kaiwu §6.2`），用例读 0xE0/0xE8/0xF0 三个槽逐字节核
@@   （`spec/DADAO-13 §2`：cause_info = 指令编码）；trap 指令地址用 `aip.si` 运行期派生
@@ GAP（不计入链例，见任务书完成区）：① `trap_num` 计数（chipyard RTL 无 cg4，
@@   `cfx2rd cfx_hmon, cg4, rc2` 在 chipyard 报 CFXREG、QEMU/gem5 读成功）；
@@   ② `trap cfx_power`（cfx63，`immu18 < 0x3FF00`）——spec 判「进 power 的异常向量」，
@@   实测 QEMU/gem5 进入（把 power 的 `hypv_excp_vector` 改到落点即可观测），但
@@   chipyard 报 ILLI（与 spec 不符）；且不改向量时该向量 = BootROM 复位入口 ⇒ 表现为重启。
@@   三方不一致 ⇒ 不构造该维度的用例；③ semihosting 服务号取 `rd16`（`immu18[17:8] == 0x3FF` 只是
@@   标记、`immu18[7:0]` 被忽略）；本文件在 immediate 里保留 `0x10` 只为沿用既有编码字节，**不**表示低 8 位承载服务号

	.include "tests/inst/macros/inst_test.inc"

@@ ---- 本文件局部宏（不改共享宏层；宏体不含检查行）----
@@ 落点块公共体：cause_info（0xF0 = 指令编码）与 cause_ip（0xE8 = trap 地址，取自 rb25）
.macro __TRAP_CHKINFO pt, info
	__VERIFY_MEM \pt, HMON_BASE, 0xF0, \info
	rb2rd	{rd22:rd22}, {rb25:rb25}
	LOAD_ADDR rb21, ((HMON_BASE + 0xE8) / 8) * 8
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __tci_\@]
	__EXIT	\pt
__tci_\@:
.endm

	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE
	LOAD_ADDR rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]              @@ 任何意外异常 ⇒ 故障落点（fail-fast）

	@@ ---- boundary：immu18 = 0x3FF10（semihosting 窗口，SYS_CLOCK）⇒ 短路返回、不进向量 ----
__case1:
	LOAD_ADDR rb21, (ENTRY + 0x11B0)        @@ 误入向量 ⇒ 落这里（判红）
	st.o	rb21, [rb20, 0xF8]
	set.zw	rd16, wp0, 0x10               @@ 服务号 = SYS_CLOCK（`rd16`；immu18 低 8 位被忽略）
	trap	cfx_hmon, 0x3FF10
	__LI	rd5, 0x5A5A5A5A5A5A5A5A
	__CHECK_RD   1, rd5, 0x5A5A5A5A5A5A5A5A   @@ 到达这里 = semihosting 未进向量
__next1:
	jump	[rb0, __case2]
__fail1:
	__EXIT	1

	@@ ---- encoding：规范编码字 0x7F0C0000（cfx3 = hmon，immu18 = 0）----
__case2:
	LOAD_ADDR rb21, (ENTRY + 0x880)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0                          @@ rb25 = 本指令地址；+8 = 下面 trap 的地址
	add.si	rb25, 8
	.dd.t32	0x7F0C0000
	__EXIT	2
__next2:
	jump	[rb0, __case3]
__fail2:
	__EXIT	2

	@@ ---- encoding：0x7F0C0100（immu18 = 0x100）----
__case3:
	LOAD_ADDR rb21, (ENTRY + 0x9D0)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	.dd.t32	0x7F0C0100
	__EXIT	3
__next3:
	jump	[rb0, __case4]
__fail3:
	__EXIT	3

	@@ ---- semantic：immu18 = 1 / 2（功能编号原样进 cause_info）----
__case4:
	LOAD_ADDR rb21, (ENTRY + 0xB20)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	trap	cfx_hmon, 1
	__EXIT	4
__next4:
	jump	[rb0, __case5]
__fail4:
	__EXIT	4

__case5:
	LOAD_ADDR rb21, (ENTRY + 0xC70)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	trap	cfx_hmon, 2
	__EXIT	5
__next5:
	jump	[rb0, __case6]
__fail5:
	__EXIT	5

	@@ ---- semantic：cfx3 与符号名 cfx_hmon 等价（同一编码 0x7F0C0100）----
__case6:
	LOAD_ADDR rb21, (ENTRY + 0xDC0)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	trap	cfx3, 0x100
	__EXIT	6
__next6:
	jump	[rb0, __case7]
__fail6:
	__EXIT	6

	@@ ---- semantic：immu18 = 0xFFFF（仍在一般 trap 窗口内，< 0x3FF00）----
__case7:
	LOAD_ADDR rb21, (ENTRY + 0xF10)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	trap	cfx_hmon, 0xFFFF
	__EXIT	7
__next7:
	jump	[rb0, __case8]
__fail7:
	__EXIT	7

	@@ ---- boundary：immu18 = 0x3FEFF（一般 trap 窗口上界）----
__case8:
	LOAD_ADDR rb21, (ENTRY + 0x1060)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	trap	cfx_hmon, 0x3FEFF
	__EXIT	8
__next8:
	jump	[rb0, __case9]
__fail8:
	__EXIT	8

	@@ ---- semantic：cfx_hmon 的 immu18 = 0（启动移交同形编码）----
__case9:
	LOAD_ADDR rb21, (ENTRY + 0x1300)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	trap	cfx_hmon, 0
	__EXIT	9
__next9:
	jump	[rb0, __finish]
__fail9:
	__EXIT	9

	@@ ---- 落点块（`.org` 钉住绝对地址；期望值写 `ENTRY + <偏移>`）----
	.org	0x880
	@@ case 2
	__TRAP_CHKINFO 2, 0x7F0C0000
	__CHECK_MEM  2, HMON_BASE, 0xE0, 0x1       @@ cause_id = CFXTRAP（1<<0）
	jump	[rb0, __next2]

	.org	0x9D0
	@@ case 3
	__TRAP_CHKINFO 3, 0x7F0C0100
	__CHECK_MEM  3, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next3]

	.org	0xB20
	@@ case 4
	__TRAP_CHKINFO 4, 0x7F0C0001
	__CHECK_MEM  4, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next4]

	.org	0xC70
	@@ case 5
	__TRAP_CHKINFO 5, 0x7F0C0002
	__CHECK_MEM  5, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next5]

	.org	0xDC0
	@@ case 6
	__TRAP_CHKINFO 6, 0x7F0C0100
	__CHECK_MEM  6, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next6]

	.org	0xF10
	@@ case 7
	__TRAP_CHKINFO 7, 0x7F0CFFFF
	__CHECK_MEM  7, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next7]

	.org	0x1060
	@@ case 8
	__TRAP_CHKINFO 8, 0x7F0FFEFF
	__CHECK_MEM  8, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next8]

	.org	0x11B0
	@@ case 1 的「误入向量」落点
	__EXIT	1

	.org	0x1300
	@@ case 9
	__TRAP_CHKINFO 9, 0x7F0C0000
	__CHECK_MEM  9, HMON_BASE, 0xE0, 0x1
	jump	[rb0, __next9]

__finish:
	__TEST_END

	@@ ---- 故障例：reserved cfxha（6 / 16 / 35）⇒ ILLI ----
	TEST_FAULT_ENC  10, ILLI, 0x7F180000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  11, ILLI, 0x7F400000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  12, ILLI, 0x7F8C0000, rb12, TEST_DATA, rd11, 0

	@@ ---- 故障例：已分配但 Tiny 未实现的 cfx（umon cfx0 / cache cfx5 / pmem cfx32）⇒ ILLI ----
	TEST_FAULT_ENC  13, ILLI, 0x7F000000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  14, ILLI, 0x7F140000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  15, ILLI, 0x7F800000, rb12, TEST_DATA, rd11, 0

	__TEST_SECTIONS
