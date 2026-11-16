@@ escape_ciii_cfx.S — escape cfxHA, [excp_cause_ip, imms20]（ciii, opc 0x7E）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §3`）；册目录 `tests/inst/11-cfx/`
@@ id：escape_ciii_cfx　形式：ciii　opc：0x7E　mask：0xFF000000　value：0x7E000000
@@ 语义：退出当前 cfx 的异常帧——返回地址 = `excp_cause_ip + (imms18 << 2)`，imms20 只允许
@@   0 或 4（编码层 imms18 ∈ {0,1}）；`imms18[17:1]` 为 SBZ，非零 ⇒ ILLI；cfxha 为 reserved
@@   ⇒ ILLI；cfxha ≠ 当前 cfx（Tiny 恒 cfx3 hmon）或当前 cfx 无有效帧（cause_id = 0）
@@   ⇒ CFXESC（`1<<3`，切换任何状态之前）；成功时 `escape_num += 1`
@@   （`spec/SimRISC-11 §3`、`spec/DADAO-12 §5.3`、`spec/Kaiwu §4.2`）。
@@ 编码：ciii = opc[31:24] | cfxha[23:18] | imms18[17:0]；`[excp_cause_ip, 4]` ⇒ imms18 = 1
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 4（链例 12 + 故障例 8）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：落点 IP 用 `aip.si` 取自身地址（只读观测）；异常路由（CFXESC/IALIGN/CFXMEM）经固件
@@   hmon 的「保存-跳转」把 cause_id/cause_ip/cause_info 落到 hmon SRAM
@@   （`spec/Kaiwu §6.2`），用例读 0xE0/0xE8/0xF0 并逐字节核（`spec/DADAO-13 §2`：
@@   cause_info = 指令编码）。落点/目标块用 `.org` 钉在 ENTRY+0x880 起（期望写绝对常量）
@@ GAP（不计入链例，见任务书完成区）：① `escape_num` 计数（chipyard RTL 无 cg4）；
@@   ② 模式恢复与 trap 保存的 global_cfx_intr_mask 不可观测（Tiny 恒 hypv、固件在同一帧内
@@   完成 escape）；③ 帧错误（cause_id = 0）不可构造（boot 的 CFXTRAP 已置帧、cg5 rc2 为 HW-RO）

	.include "tests/inst/macros/inst_test.inc"

@@ ---- 本文件局部宏（不改共享宏层；宏体不含检查行）----
@@ 写 excp_cause_ip（cg5 rc3，RW）= escape 的返回基址
.macro __ESC_SETIP addr
	set.rd	rd5, \addr
	cfx2rc	cfx_hmon, cg5, rc3, rd5
.endm

@@ 落点 IP 捕获（`aip.si` 取自身地址，经 rb2rd 搬到 rd；rb25 为本文件临时）
.macro __LAND_IP_RD rd
	aip.si	rb25, 0
	rb2rd	{\rd:\rd}, {rb25:rb25}
.endm

	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE
	LOAD_ADDR rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]              @@ 任何意外异常 ⇒ 故障落点（fail-fast）

	@@ ---- encoding：规范编码字 0x7E0C0001（cfx3，imms18 = 1 ⇒ +4）----
	__ESC_SETIP (ENTRY + 0x880)
	.dd.t32	0x7E0C0001
	__EXIT	1
__next1:
	jump	[rb0, __case2]
__fail1:
	__EXIT	1

	@@ ---- encoding：0x7E0C0000（imms18 = 0 ⇒ +0）----
__case2:
	__ESC_SETIP (ENTRY + 0x980)
	.dd.t32	0x7E0C0000
	__EXIT	2
__next2:
	jump	[rb0, __case3]
__fail2:
	__EXIT	2

	@@ ---- semantic：汇编形式 `[excp_cause_ip, 4]` ----
__case3:
	__ESC_SETIP (ENTRY + 0xA80)
	escape	cfx_hmon, [excp_cause_ip, 4]
	__EXIT	3
__next3:
	jump	[rb0, __case4]
__fail3:
	__EXIT	3

	@@ ---- semantic：汇编形式 `[excp_cause_ip, 0]` ----
__case4:
	__ESC_SETIP (ENTRY + 0xB80)
	escape	cfx_hmon, [excp_cause_ip, 0]
	__EXIT	4
__next4:
	jump	[rb0, __case5]
__fail4:
	__EXIT	4

	@@ ---- semantic：从「非 trap 的同步异常帧」（ILLI，cause_id = 1<<8）escape ----
__case5:
	LOAD_ADDR rb21, (ENTRY + 0xC80)
	st.o	rb21, [rb20, 0xF8]
	trap	cfx6, 0                          @@ reserved cfxha ⇒ ILLI（进 hmon 向量）
	__EXIT	5
__next5:
	jump	[rb0, __case6]
__fail5:
	__EXIT	5

	@@ ---- semantic：连续两次 escape（帧未被消费；第一次 +4、第二次 +0）----
__case6:
	__ESC_SETIP (ENTRY + 0xE80)
	escape	cfx_hmon, [excp_cause_ip, 4]
	__EXIT	6
__next6:
	jump	[rb0, __case7]
__fail6:
	__EXIT	6

	@@ ---- semantic：escape 不改写异常帧（cause_id / cause_ip 保持）----
__case7:
	cfx2rd	cfx_hmon, cg5, rc2, rd7             @@ 记录 escape 前的帧 cause_id（应保持）
	__ESC_SETIP (ENTRY + 0x1300)
	escape	cfx_hmon, [excp_cause_ip, 0]
	__EXIT	7
__next7:
	jump	[rb0, __case8]
__fail7:
	__EXIT	7

	@@ ---- boundary：返回地址 = 任意编译期固定地址（.text 高端）----
__case8:
	__ESC_SETIP (ENTRY + 0x1450)
	.dd.t32	0x7E0C0001
	__EXIT	8
__next8:
	jump	[rb0, __case9]
__fail8:
	__EXIT	8

	@@ ---- boundary：目标未 4 字节对齐 ⇒ IALIGN（IP 停在非法地址）----
__case9:
	__ESC_SETIP ((ENTRY + 0x401))
	LOAD_ADDR rb21, (ENTRY + 0x15A0)
	st.o	rb21, [rb20, 0xF8]
	escape	cfx_hmon, [excp_cause_ip, 0]
	__EXIT	9
__next9:
	jump	[rb0, __case10]
__fail9:
	__EXIT	9

	@@ ---- boundary：目标地址 0（Tiny 的 addr[47:42]=0 未映射）⇒ CFXMEM ----
__case10:
	__ESC_SETIP (0)
	LOAD_ADDR rb21, (ENTRY + 0x16F0)
	st.o	rb21, [rb20, 0xF8]
	escape	cfx_hmon, [excp_cause_ip, 0]
	__EXIT	10
__next10:
	jump	[rb0, __case11]
__fail10:
	__EXIT	10

	@@ ---- legality：cfxha ≠ 当前 cfx ⇒ CFXESC（cause_id = 1<<3、info = 指令编码）----
__case11:
	LOAD_ADDR rb21, (ENTRY + 0x1840)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0                          @@ rb25 = 本指令地址；+8 = 下面 escape 的地址
	add.si	rb25, 8
	escape	cfx_power, [excp_cause_ip, 0]
	__EXIT	11
__next11:
	jump	[rb0, __case12]
__fail11:
	__EXIT	11

	@@ ---- legality：目标 cfx0（umon，非 reserved 但非当前 cfx）同样 CFXESC ----
__case12:
	LOAD_ADDR rb21, (ENTRY + 0x1990)
	st.o	rb21, [rb20, 0xF8]
	aip.si	rb25, 0
	add.si	rb25, 8
	escape	cfx_umon, [excp_cause_ip, 4]
	__EXIT	12
__next12:
	jump	[rb0, __end]
__fail12:
	__EXIT	12

__end:
	jump	[rb0, __finish]

	@@ ---- 落点/目标块（`.org` 钉住绝对地址；期望值写 `ENTRY + <偏移>`）----
	.org	0x880
	@@ case 1：+0 落点 = 错（应 +4）
	jump	[rb0, __fail1]
	__LAND_IP_RD rd5
	__CHECK_RD   1, rd5, (ENTRY + 0x884)
	jump	[rb0, __next1]

	.org	0x980
	@@ case 2：+0 落点 = 对；+4 = 错
	jump	[rb0, __t2_ok]
	jump	[rb0, __fail2]
__t2_ok:
	__LAND_IP_RD rd5
	__CHECK_RD   2, rd5, (ENTRY + 0x988)
	jump	[rb0, __next2]

	.org	0xA80
	@@ case 3
	jump	[rb0, __fail3]
	__LAND_IP_RD rd5
	__CHECK_RD   3, rd5, (ENTRY + 0xA84)
	jump	[rb0, __next3]

	.org	0xB80
	@@ case 4
	jump	[rb0, __t4_ok]
	jump	[rb0, __fail4]
__t4_ok:
	__LAND_IP_RD rd5
	__CHECK_RD   4, rd5, (ENTRY + 0xB88)
	jump	[rb0, __next4]

	.org	0xC80
	@@ case 5：ILLI 帧落点 → 改用固定目标 0xD80（+4）
	__VERIFY_MEM 5, HMON_BASE, 0xE0, 0x100      @@ 确实是 ILLI 帧
	__ESC_SETIP (ENTRY + 0xD80)
	escape	cfx_hmon, [excp_cause_ip, 4]
	__EXIT	5
__t5_ok:
	jump	[rb0, __next5]

	.org	0xD80
	@@ case 5 的 escape 目标（+4）
	jump	[rb0, __fail5]
	__LAND_IP_RD rd5
	__CHECK_RD   5, rd5, (ENTRY + 0xD84)
	jump	[rb0, __t5_ok]

	.org	0xE80
	@@ case 6：第一次 escape 落点（+4）→ 第二次 escape 到 0xF80（+0）
	jump	[rb0, __fail6]
	__ESC_SETIP (ENTRY + 0xF80)
	escape	cfx_hmon, [excp_cause_ip, 0]
	__EXIT	6
__t6a:
	jump	[rb0, __next6]

	.org	0xF80
	@@ case 6 的第二次落点（+0）
	jump	[rb0, __t6b_ok]
	jump	[rb0, __fail6]
__t6b_ok:
	__LAND_IP_RD rd5
	__CHECK_RD   6, rd5, (ENTRY + 0xF88)
	jump	[rb0, __t6a]

	.org	0x1300
	@@ case 7：+0 落点，随后核帧未被改写
	jump	[rb0, __t7_ok]
	jump	[rb0, __fail7]
__t7_ok:
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__VERIFY_RD 7, rd6, (ENTRY + 0x1300)       @@ cause_ip 未被 escape 改写
	cfx2rd	cfx_hmon, cg5, rc2, rd6
	__VERIFY_EQ_RD 7, rd6, rd7                 @@ cause_id 未被 escape 改写（帧仍有效）
	__CHECK_RD   7, rd6, 0x100                 @@ 记录实测帧来源 = case 5 的 ILLI 帧
	jump	[rb0, __next7]

	.org	0x1450
	@@ case 8
	jump	[rb0, __fail8]
	__LAND_IP_RD rd5
	__CHECK_RD   8, rd5, (ENTRY + 0x1454)
	jump	[rb0, __next8]

	.org	0x15A0
	@@ case 9：IALIGN 落点
	__VERIFY_MEM 9, HMON_BASE, 0xE8, (ENTRY + 0x401)
	__CHECK_MEM  9, HMON_BASE, 0xE0, 0x2000     @@ IALIGN（1<<13）
	jump	[rb0, __next9]

	.org	0x16F0
	@@ case 10：CFXMEM 落点（目标地址 0）
	__VERIFY_MEM 10, HMON_BASE, 0xE8, 0
	LOAD_ADDR rb21, (HMON_BASE + 0xE0)
	ld.o	rd23, [rb21, 0]
	set.rd	rd22, 0xFFFF                     @@ 只比大类 cause_id[15:0]
	and.o	rd23, rd23, rd22                 @@ 依据 ADR-0056 D2 / contract-see
						@@ §6.1.1：子原因在 wyde2/wyde3，
						@@ 本断言对象是大类 CFXMEM（1<<1）
	__CHECK_RD   10, rd23, 0x2
	jump	[rb0, __next10]

	.org	0x1840
	@@ case 11：CFXESC 落点（cause_ip = escape 指令地址，取自 rb25）
	__VERIFY_MEM 11, HMON_BASE, 0xF0, 0x7EFC0000
	rb2rd	{rd22:rd22}, {rb25:rb25}            @@ 运行期派生的 escape 地址
	LOAD_ADDR rb21, ((HMON_BASE + 0xE8) / 8) * 8
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __t11_ok]
	__EXIT	11
__t11_ok:
	__CHECK_MEM  11, HMON_BASE, 0xE0, 0x8       @@ CFXESC（1<<3）
	jump	[rb0, __next11]

	.org	0x1990
	@@ case 12：CFXESC 落点（cfx0，imms18 = 1）
	__VERIFY_MEM 12, HMON_BASE, 0xF0, 0x7E000001
	rb2rd	{rd22:rd22}, {rb25:rb25}
	LOAD_ADDR rb21, ((HMON_BASE + 0xE8) / 8) * 8
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __t12_ok]
	__EXIT	12
__t12_ok:
	__CHECK_MEM  12, HMON_BASE, 0xE0, 0x8
	jump	[rb0, __next12]

__finish:
	__TEST_END

	@@ ---- 故障例：SBZ 非零（imms18[17:1] ≠ 0）⇒ ILLI ----
	TEST_FAULT_ENC  13, ILLI, 0x7E0C0002, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  14, ILLI, 0x7E0C0003, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  15, ILLI, 0x7EFDFFFF, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  16, ILLI, 0x7EFFFFFE, rb12, TEST_DATA, rd11, 0

	@@ ---- 故障例：reserved cfxha（6 / 61）⇒ ILLI（先于目标/帧判定）----
	TEST_FAULT_ENC  17, ILLI, 0x7E180000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  18, ILLI, 0x7EF40000, rb12, TEST_DATA, rd11, 0

	@@ 故障例：SBZ 检查先于 CFXESC —— cfx63 非保留但非当前 cfx（3），SBZ 非零仍报 ILLI
	@@   （并入原 YAML 的同 id 用例；若先判 cfx 匹配则会是 CFXESC `1<<3`）
	TEST_FAULT_ENC  19, ILLI, 0x7EFC0002, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  20, ILLI, 0x7EFC0003, rb12, TEST_DATA, rd11, 0

	__TEST_SECTIONS
