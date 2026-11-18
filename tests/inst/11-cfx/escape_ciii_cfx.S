@@ escape_ciii_cfx.S — escape cfxHA, [excp_cause_ip, imms20]（ciii, opc 0x7E）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §3`）；册目录 `tests/inst/11-cfx/`
@@ id：escape_ciii_cfx　形式：ciii　opc：0x7E　mask：0xFF000000　value：0x7E000000
@@ 语义（`spec/DADAO-12 §5.3`，m14-spec-009 起）：`escape` 在**当前 cfx**（`inner_cfx_code`）
@@   的异常帧上退出——步骤 0 检查目标/帧：`imms18[17:1]` 非 0 ⇒ ILLI；`cfxha` reserved ⇒ ILLI；
@@   `cfxha != inner_cfx_code` 或该 cfx 帧无效（`excp_cause_id == 0`）⇒ **CFXESC**（切换任何
@@   状态之前）；步骤 1 恢复 trap 保存的 global 中断掩码；步骤 2 恢复 `inner_run_mode` 与
@@   **`inner_cfx_code` ← `excp_prev_cfx_code`**；步骤 3 `escape_num += 1`、返回地址 =
@@   `excp_cause_ip + (imms18 << 2)`（imms20 只允许 0 或 4 ⇒ 编码层 imms18 ∈ {0,1}）。
@@ ★ 本文件的关键前提（m14-spec-009 新语义）：**boot 移交后应用运行在 cfx_power(63) 上下文**——
@@   `spec/Kaiwu §1` 的复位 cfx 是 cfx_power(63)；固件 hmon 在 `§6.2` 第 7 步 `escape cfx_hmon`
@@   会把 `inner_cfx_code` 从 hmon(3) 恢复成进入前的 63（旧语义「escape 不改 `inner_cfx_code`」
@@   已作废）。故应用**不能**直接 `escape cfx_hmon`（`cfxha(3) != inner_cfx_code(63)` ⇒ CFXESC）；
@@   成功路径只能在 **monitor 上下文**里执行 ⇒ 本文件自建 monitor 入口：应用写
@@   `cfx_hmon cg3 rc10`（hypv 异常向量，RW、低 2 位被忽略）指向本文件的 handler，再
@@   `trap cfx_hmon` 进入 hmon（此时 `inner_cfx_code = 3`），由 handler 执行被测 `escape`
@@   回到应用；结束前把自建入口撤掉，把 `cfx_hmon` / `cfx_power` 的向量还原成各自的初值
@@   （`spec/DADAO-13 §1`：= 该 cfx 的 SRAM 起始；hmon = hmon SRAM、power = BootROM）。
@@ 编码：ciii = opc[31:24] | cfxha[23:18] | imms18[17:0]；`[excp_cause_ip, 4]` ⇒ imms18 = 1
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / legality 2（链例 12 + 故障例 8）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：落点 IP 用 `aip.si` 取自身地址（只读观测）；三类异常的 cause 观测面都是 hmon SRAM 的
@@   0xE0/0xE8/0xF0 槽（cause_id / cause_ip / cause_info，`spec/DADAO-13 §2`：cause_info = 指令编码）——
@@   目标侧异常（IALIGN/CFXMEM）由**平台固件** hmon 的「保存-跳转」写这些槽（`spec/Kaiwu §6.2`）；
@@   CFXESC 交给**当前 cfx = cfx_power**（`§5.3` 步骤 0），故由本文件挂在 `cfx_power` 向量上的
@@   自建入口写同样三个槽（链例 10/11）。落点/目标块/handler 用 `.org` 钉在 ENTRY+0x880 起。
@@ GAP（不计入链例，见任务书完成区）：① `escape_num` 计数（chipyard RTL 无 cg4）；
@@   ② 模式恢复与 trap 保存的 global_cfx_intr_mask 不可观测（Tiny 恒 hypv）；③ `inner_cfx_code`
@@   本身不可直接读 ⇒ 用「同帧第二次 escape 必判 CFXESC」间接断言恢复（链例 12）；
@@   ④ 本文件的 handler 是**测试替身**，不是平台固件（平台固件的行为由各故障例的固件路由覆盖）

	.include "tests/inst/macros/inst_test.inc"

@@ ---- 本文件局部宏（不改共享宏层；宏体不含检查行）----
@@ 安装自建 monitor 入口：`cfx_hmon cg3 rc10` = hypv 异常向量（RW；写入忽略低 2 位）
.macro __MON_INSTALL handler
	set.rd	rd12, \handler
	cfx2rc	cfx_hmon, cg3, rc10, rd12
.endm

@@ 进 hmon 跑被测 `escape`：装入口 → 返回基址进 rd13 → `trap cfx_hmon`
@@   （应用在 cfx_power(63)：`cfx_hmon` 的 hypv `cfxtrap` 掩码允许 63 ⇒ 可显式 trap）
.macro __MON_ENTER handler, target
	__MON_INSTALL \handler
	set.rd	rd13, \target
	trap	cfx_hmon, 0x30001
.endm

@@ handler 公共前置：记进入时的 cause_id（落点断言用）、把返回基址设成用例给的 rd13
.macro __MON_PRE cfx
	cfx2rd	\cfx, cg5, rc2, rd63
	st.o	rd63, [rb22, 0xE0]
	cfx2rc	\cfx, cg5, rc3, rd13
.endm

@@ cfx63 侧入口前置：CFXESC 交付给**当前 cfx**（应用在 cfx_power 63）⇒ 帧属于 cfx_power；
@@   进入时记下 cause_id / cause_ip / cause_info 三个槽（落点断言的独立观测面），
@@   再把返回基址改成用例给的 rd13（escape 不改写帧的其余字段）
.macro __MON_PRE_POWER
	cfx2rd	cfx_power, cg5, rc2, rd63
	st.o	rd63, [rb22, 0xE0]
	cfx2rd	cfx_power, cg5, rc3, rd63
	st.o	rd63, [rb22, 0xE8]
	cfx2rd	cfx_power, cg5, rc4, rd63
	st.o	rd63, [rb22, 0xF0]
	cfx2rc	cfx_power, cg5, rc3, rd13
.endm

@@ 落点 IP 捕获（`aip.si` 取自身地址，经 rb2rd 搬到 rd；rb25 为本文件临时）
.macro __LAND_IP_RD rd
	aip.si	rb25, 0
	rb2rd	{\rd:\rd}, {rb25:rb25}
.endm

	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE
	LOAD_ADDR rb22, HMON_BASE              @@ handler 的槽基址（跨 trap 保留）
	set.rd	rd11, HMON_BASE                    @@ 固件异常向量值（`spec/DADAO-13 §1` 初值）
	LOAD_ADDR rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]              @@ 任何意外异常 ⇒ 故障落点（fail-fast）

	@@ ---- encoding：规范编码字 0x7E0C0001（cfx3，imms18 = 1 ⇒ +4）----
__c1:
	__MON_ENTER (ENTRY + 0x1B80), (ENTRY + 0x880)
	__EXIT	1

	@@ ---- encoding：0x7E0C0000（imms18 = 0 ⇒ +0）----
__c2:
	__MON_ENTER (ENTRY + 0x1BC0), (ENTRY + 0x980)
	__EXIT	2

	@@ ---- semantic：汇编形式 `[excp_cause_ip, 4]` ----
__c3:
	__MON_ENTER (ENTRY + 0x1B00), (ENTRY + 0xA80)
	__EXIT	3

	@@ ---- semantic：汇编形式 `[excp_cause_ip, 0]` ----
__c4:
	__MON_ENTER (ENTRY + 0x1B40), (ENTRY + 0xB80)
	__EXIT	4

	@@ ---- semantic：从「非 trap 的同步异常帧」（ILLI，cause_id = 1<<8）escape ----
__c5:
	__MON_INSTALL (ENTRY + 0x1B00)         @@ [+4] 入口（本用例不同 trap，靠 ILLI 陷入）
	set.rd	rd13, (ENTRY + 0xD80)
	trap	cfx6, 0                        @@ reserved cfxha ⇒ ILLI（进当前模式 monitor = hmon）
	__EXIT	5

	@@ ---- semantic：escape 不改写异常帧（cause_id / cause_ip 保持）----
__c6:
	__MON_ENTER (ENTRY + 0x1B40), (ENTRY + 0x1300)
	__EXIT	6

	@@ ---- boundary：返回地址 = 任意编译期固定地址（.text 高端）----
__c7:
	__MON_ENTER (ENTRY + 0x1B00), (ENTRY + 0x1450)
	__EXIT	7

	@@ ---- boundary：目标未 4 字节对齐 ⇒ IALIGN（IP 停在非法地址）----
	@@   handler 先把向量还原成平台固件再 escape，于是目标侧异常按固件「保存-跳转」落到 0x15A0
__c8:
	LOAD_ADDR rb21, (ENTRY + 0x15A0)
	st.o	rb21, [rb20, 0xF8]
	__MON_ENTER (ENTRY + 0x1C00), ((ENTRY + 0x401))
	__EXIT	8

	@@ ---- boundary：目标地址 0（Tiny 的 addr[47:42]=0 未映射）⇒ CFXMEM ----
__c9:
	LOAD_ADDR rb21, (ENTRY + 0x16F0)
	st.o	rb21, [rb20, 0xF8]
	__MON_ENTER (ENTRY + 0x1C00), 0
	__EXIT	9

	@@ ---- legality：cfxha = 当前 cfx（应用在 cfx_power 63）但该帧无效（cause_id = 0）⇒ CFXESC ----
	@@   CFXESC 交给**当前 cfx**（= cfx_power 63，`§5.3` 步骤 0 伪代码）⇒ 把自建入口挂到
	@@   cfx_power 的 hypv 向量上，由它记下三槽并 escape 回落点（否则会跳进 power 的复位向量）
__c10:
	set.rd	rd12, (ENTRY + 0x1C80)
	cfx2rc	cfx_power, cg3, rc10, rd12
	set.rd	rd13, (ENTRY + 0x1840)
	aip.si	rb25, 0                        @@ rb25 = 本指令地址；+8 = 下面 escape 的地址
	add.si	rb25, 8
	escape	cfx_power, [excp_cause_ip, 0]
	__EXIT	10

	@@ ---- legality：cfxha ≠ 当前 cfx（cfx0 umon）同样 CFXESC（同样交当前 cfx = power）----
__c11:
	set.rd	rd13, (ENTRY + 0x1990)
	aip.si	rb25, 0
	add.si	rb25, 8
	escape	cfx_umon, [excp_cause_ip, 4]
	__EXIT	11

	@@ ---- semantic：escape 恢复 `inner_cfx_code` ← `excp_prev_cfx_code`（`§5.3` 步骤 2）----
	@@   第一次 escape 后应用回到 cfx_power(63) ⇒ 再 `escape cfx_hmon` 必判 CFXESC
	@@   （cfxha 3 ≠ inner 63）；旧语义（inner 仍为 3）下会直接成功落回本 pad ⇒ 计数超限判红
__c12:
	__MON_ENTER (ENTRY + 0x1B40), (ENTRY + 0x1E00)
	__EXIT	12

__end:
	jump	[rb0, __finish]

	@@ ---- 落点/目标块（`.org` 钉住绝对地址；期望值写 `ENTRY + <偏移>`）----
	.org	0x880
	@@ case 1：+4 落点对（0x880 = 按 +0 落 ⇒ 错）
	jump	[rb0, __fail1]
	__LAND_IP_RD rd5
	__CHECK_RD   1, rd5, (ENTRY + 0x884)
	jump	[rb0, __c2]
__fail1:
	__EXIT	1

	.org	0x980
	@@ case 2：+0 落点对；+4 = 错
	jump	[rb0, __t2_ok]
	jump	[rb0, __fail2]
__t2_ok:
	__LAND_IP_RD rd5
	__CHECK_RD   2, rd5, (ENTRY + 0x988)
	jump	[rb0, __c3]
__fail2:
	__EXIT	2

	.org	0xA80
	@@ case 3
	jump	[rb0, __fail3]
	__LAND_IP_RD rd5
	__CHECK_RD   3, rd5, (ENTRY + 0xA84)
	jump	[rb0, __c4]
__fail3:
	__EXIT	3

	.org	0xB80
	@@ case 4
	jump	[rb0, __t4_ok]
	jump	[rb0, __fail4]
__t4_ok:
	__LAND_IP_RD rd5
	__CHECK_RD   4, rd5, (ENTRY + 0xB88)
	jump	[rb0, __c5]
__fail4:
	__EXIT	4

	.org	0xD80
	@@ case 5：ILLI 帧的 escape 落点（+4）；`aip.si` 必须紧贴落点（捕获的就是落点地址）
	jump	[rb0, __fail5]
	__LAND_IP_RD rd5
	__VERIFY_MEM 5, HMON_BASE, 0xE0, 0x100  @@ 帧来源确实是 ILLI（handler 记录的 cause_id）
	__CHECK_RD   5, rd5, (ENTRY + 0xD84)
	jump	[rb0, __c6]
__fail5:
	__EXIT	5

	.org	0x1300
	@@ case 6：+0 落点；随后核帧字段未被 escape 改写/消费
	jump	[rb0, __t6_ok]
	jump	[rb0, __fail6]
__t6_ok:
	cfx2rd	cfx_hmon, cg5, rc3, rd6
	__VERIFY_RD 6, rd6, (ENTRY + 0x1300)       @@ cause_ip 仍 = handler 写入的返回基址
	LOAD_ADDR rb21, HMON_BASE
	ld.o	rd7, [rb21, 0xE0]                  @@ 进入 hmon 时记录的 cause_id
	cfx2rd	cfx_hmon, cg5, rc2, rd6
	__VERIFY_EQ_RD 6, rd6, rd7                 @@ escape 前后一致 ⇒ 帧未被消费
	__CHECK_RD   6, rd6, 0x1                   @@ 且就是 CFXTRAP（记录实测值）
	jump	[rb0, __c7]
__fail6:
	__EXIT	6

	.org	0x1450
	@@ case 7
	jump	[rb0, __fail7]
	__LAND_IP_RD rd5
	__CHECK_RD   7, rd5, (ENTRY + 0x1454)
	jump	[rb0, __c8]
__fail7:
	__EXIT	7

	.org	0x15A0
	@@ case 8：IALIGN 落点（目标侧异常经还原后的平台固件）
	__VERIFY_MEM 8, HMON_BASE, 0xE8, (ENTRY + 0x401)
	__CHECK_MEM  8, HMON_BASE, 0xE0, 0x2000     @@ IALIGN（1<<13）
	jump	[rb0, __c9]

	.org	0x16F0
	@@ case 9：CFXMEM 落点（目标地址 0）
	__VERIFY_MEM 9, HMON_BASE, 0xE8, 0
	LOAD_ADDR rb21, (HMON_BASE + 0xE0)
	ld.o	rd23, [rb21, 0]
	set.rd	rd22, 0xFFFF                     @@ 只比大类 cause_id[15:0]
	and.o	rd23, rd23, rd22                 @@ 依据 ADR-0056 D2 / contract-see
						@@ §6.1.1：子原因在 wyde2/wyde3，
						@@ 本断言对象是大类 CFXMEM（1<<1）
	__CHECK_RD   9, rd23, 0x2
	jump	[rb0, __c10]

	.org	0x1840
	@@ case 10：CFXESC 落点（cause_ip = escape 指令地址，取自 rb25）
	__VERIFY_MEM 10, HMON_BASE, 0xF0, 0x7EFC0000
	rb2rd	{rd22:rd22}, {rb25:rb25}            @@ 运行期派生的 escape 地址
	LOAD_ADDR rb21, ((HMON_BASE + 0xE8) / 8) * 8
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __t10_ok]
	__EXIT	10
__t10_ok:
	__CHECK_MEM  10, HMON_BASE, 0xE0, 0x8       @@ CFXESC（1<<3）
	jump	[rb0, __c11]

	.org	0x1990
	@@ case 11：CFXESC 落点（cfx0，imms18 = 1）
	__VERIFY_MEM 11, HMON_BASE, 0xF0, 0x7E000001
	rb2rd	{rd22:rd22}, {rb25:rb25}
	LOAD_ADDR rb21, ((HMON_BASE + 0xE8) / 8) * 8
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __t11_ok]
	__EXIT	11
__t11_ok:
	__CHECK_MEM  11, HMON_BASE, 0xE0, 0x8
	jump	[rb0, __c12]

	@@ ---- 自建 monitor 入口（vector 指向这里；进入时 `inner_cfx_code = 3`）----
	.org	0x1B00
__mon_a4:                                      @@ 汇编形式：`[excp_cause_ip, 4]`
	__MON_PRE cfx_hmon
	escape	cfx_hmon, [excp_cause_ip, 4]

	.org	0x1B40
__mon_a0:                                      @@ 汇编形式：`[excp_cause_ip, 0]`
	__MON_PRE cfx_hmon
	escape	cfx_hmon, [excp_cause_ip, 0]

	.org	0x1B80
__mon_e4:                                      @@ 原始编码 0x7E0C0001（cfx3，imms18 = 1 ⇒ +4）
	__MON_PRE cfx_hmon
	.dd.t32	0x7E0C0001

	.org	0x1BC0
__mon_e0:                                      @@ 原始编码 0x7E0C0000（imms18 = 0 ⇒ +0）
	__MON_PRE cfx_hmon
	.dd.t32	0x7E0C0000

	.org	0x1C00
__mon_t0:                                      @@ 目标侧异常用例：先还原平台固件向量再 escape
	__MON_PRE cfx_hmon
	cfx2rc	cfx_hmon, cg3, rc10, rd11      @@ 还原 = hmon SRAM 起始（`spec/DADAO-13 §1` 初值）
	escape	cfx_hmon, [excp_cause_ip, 0]

	.org	0x1C40
__mon_probe:                                   @@ cfx63 侧入口：只记 cause_id 再 escape 回 rd13（链例 12 用）
	@@ 应用里第二次 `escape cfx_hmon` 的 CFXESC 交付给**当前 cfx = cfx_power(63)**（`§5.3` 步骤 0）
	cfx2rd	cfx_power, cg5, rc2, rd63
	st.o	rd63, [rb22, 0xC0]
	cfx2rc	cfx_power, cg5, rc3, rd13
	escape	cfx_power, [excp_cause_ip, 0]

	.org	0x1C80
__mon_p0:                                      @@ cfx63 侧入口：CFXESC 落点（目标 cfx 帧无效 / cfxha 不符）
	__MON_PRE_POWER
	escape	cfx_power, [excp_cause_ip, 0]

	.org	0x1E00
	@@ case 12：`escape` 恢复 `inner_cfx_code` ← `excp_prev_cfx_code`
	@@   第一次到达 = handler 的 escape 落点（应用已回到 cfx_power 63），
	@@     此时再 `escape cfx_hmon` 必须被判 CFXESC（cfxha 3 ≠ inner 63）⇒ probe 入口写 cause_id；
	@@   第二次到达 = CFXESC 经 probe 入口 escape 回来的落点 ⇒ 断言 cause_id = 1<<3。
	@@   到达次数上限 2：旧语义下第二次 escape 会直接成功、cause_id 标记恒 0 ⇒ 第 3 次到达判红
	@@   （不挂死，可判定失败）。
	LOAD_ADDR rb21, HMON_BASE
	ld.o	rd8, [rb21, 0xC8]                  @@ 到达计数
	add.si	rd8, 1
	st.o	rd8, [rb21, 0xC8]
	ld.o	rd7, [rb21, 0xC0]                  @@ probe 入口记录的 cause_id（0 = 未被调用）
	set.rd	rd9, 2
	cmp.uo	rd9, rd8, rd9
	br.p	{rd9}?, [rb0, __fail12]             @@ 到达 > 2 次 ⇒ 判红（旧语义必到此）
	br.z	{rd7}?, [rb0, __t12_first]
	__CHECK_RD  12, rd7, 0x8                    @@ 第二次到达：cause_id = CFXESC（1<<3）
	jump	[rb0, __end]
__t12_first:
	set.rd	rd12, (ENTRY + 0x1C40)              @@ 安装「记录 CFXESC」入口（挂 cfx_power 向量）
	cfx2rc	cfx_power, cg3, rc10, rd12
	set.rd	rd13, (ENTRY + 0x1E00)              @@ 旧语义下 escape 成功会落回本 pad
	escape	cfx_hmon, [excp_cause_ip, 0]        @@ 应用在 cfx63 ⇒ 新语义下必判 CFXESC
	__EXIT	12
__fail12:
	__EXIT	12

__finish:
	cfx2rc	cfx_hmon, cg3, rc10, rd11              @@ 还原平台固件向量（故障链经固件路由）
	set.rd	rd12, BOOTROM_BASE                     @@ 还原 cfx_power 向量 = 其 ROM 起始（`DADAO-13 §1`）
	cfx2rc	cfx_power, cg3, rc10, rd12
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
