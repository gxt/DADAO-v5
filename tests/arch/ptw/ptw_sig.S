@@ ptw_sig.S — cfx4 的 RTL 签名承载（`m16-chipyard-018`）
@@
@@ 目的：把 `m16-testcases-010` 的 15 条 `arch-ptw-*` 中的 cfx4 语义搬到
@@ `WumingVastConfig` 上跑，并与 QEMU/gem5 的**同一组**数据地址/PTE 值对齐
@@ ⇒ 已接线签名流（`arch-ptw-002/006/007`）可以逐字节比较。
@@
@@ 几何与期望值全部来自 `gen_ptw_sig_tables.py`（页表/PTE/magic/cause 编码/
@@ 签名槽），本文件不含手算的索引或位号；QEMU 侧的同一组值由
@@ `ptw_carrier_tlb.py` 给出，`gen_ptw_sig_tables.py --selfcheck` 与
@@ `expected.yaml` 双向核对。
@@
@@ 运行模式：chipyard 的固定 BootROM（`spec/Kaiwu §6.2`）把测试体交付为
@@ `cfx_hmon` + `hypv`，所以 PTE 的 HSJU 取 H=1（`0x8`），与 QEMU 载体的
@@ `pte_leaf(hsju=0x8)` 相同。H/S/U 三模式见 `tests/arch/ptw/README.md`：
@@ smon/umon 的进入链不在 RTL 的 step5 测试路径里（`tests/ee-vast/README.md`），
@@ 由 `modes.yaml` 显式排除并登记原因。
@@
@@ 布局（与 `ptw_carrier_tlb.py` 的 QEMU 场景同一组 PA/VA）：
@@   PT_L1  0x7FF0_0000  L1（L1[0] → L2；L1[0x1003] 映射 PA 1.5–2 GiB）
@@   PT_L2  0x7FF2_0000  L2（L2[i] 由 case 决定，见生成器）
@@   PT_L1B 0x7FF4_0000  第二张 L1（case 008：换 PTBR 不隐含失效）
@@   DA/DB/DC/DD = 0x6000_0000/0x6100_0000/0x6200_0000/0x6300_0000
@@   数据由探针在运行期经 VA = PA + 2 TiB 写入（超页 L1[0x1003]）。
@@
@@ 用例选择：`llvm-mc --defsym PTW_CASE=<n>`（1..13）。
@@ 只有 002/006/007/013 写签名流（与 QEMU/gem5 逐槽比较）；其余 case 由
@@ guest 内断言判（`SYS_EXIT(点号)` ⇒ 红），签名流为 0 槽（与 QEMU 的空流一致）。
@@
@@ 故障观察：chipyard 的固定 BootROM 是 Tiny 固件（`tests/ee-tiny/
@@ cfx_hmon_tiny.S`）⇒ cause_id/cause_ip/cause_info 写在 hmon SRAM 的
@@ +0xE0/+0xE8/+0xF0，返回地址从 +0xF8 取。`ARM_FAULT` 先清槽再写返回点，
@@ 落点读回 cause —— 不靠残留值。

	.ifndef	PTW_CASE
	.equ	PTW_CASE, 2
	.endif

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/shared/asm/perm_hypv.inc"
	.include "ptw_sig_tables.inc"

@@ ---------------------------------------------------------------------------
@@ 文件专用宏
@@ ---------------------------------------------------------------------------
.macro	LDV rd, va
	set.rb	rb4, \va
	ld.o	\rd, [rb4, 0]
.endm

.macro	STV rd, va
	set.rb	rb4, \va
	st.o	\rd, [rb4, 0]
.endm

@@ 改 L2[idx]（表页经 VA = PA + 2 TiB 访问）
.macro	EDIT_L2 idx, pte
	set.rb	rb6, VA_BASE + PT_L2
	set.rd	rd7, \pte
	st.o	rd7, [rb6, 8 * (\idx)]
.endm

@@ 读 L2[idx]（回读 PTE）
.macro	READ_L2 rd, idx
	set.rb	rb6, VA_BASE + PT_L2
	ld.o	\rd, [rb6, 8 * (\idx)]
.endm

.macro	INVAL_ALL
	set.rd	rd6, CTL_INVALID_ALL
	cfx2rc	cfx_ptw, cg12, rc0, rd6
.endm

.macro	TLB_START va
	set.rd	rd6, \va
	cfx2rc	cfx_ptw, cg12, rc2, rd6
.endm

.macro	TLB_SIZE sz
	set.rd	rd6, \sz
	cfx2rc	cfx_ptw, cg12, rc3, rd6
.endm

.macro	TLB_CTL val
	set.rd	rd6, \val
	cfx2rc	cfx_ptw, cg12, rc0, rd6
.endm

@@ 清 cause 槽 + 写返回点；故障（或正常执行）后都落到 resume 标签
.macro	ARM_FAULT resume
	st.o	rd0, [rb20, 0xE0]
	st.o	rd0, [rb20, 0xF0]
	set.rb	rb21, \resume
	st.o	rb21, [rb20, 0xF8]
.endm

.macro	READ_CAUSE rd
	ld.o	\rd, [rb20, 0xE0]
.endm

.macro	READ_INFO rd
	ld.o	\rd, [rb20, 0xF0]
.endm

__TEST_BEGIN
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	set.rb	rb20, HMON_BASE		@@ 固定固件 hmon 的 cause 槽/返回槽

	@@ 页表在镜像里预置（PT_L1/PT_L1B/PT_L2），这里只装 PTBR/开 PTW/清 TLB。
	set.rd	rd6, PT_L1
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	INVAL_ALL

	@@ 数据页（经 VA = PA + 2 TiB 写入；与 QEMU 载体的 magic 相同）
	set.rd	rd5, M1
	STV	rd5, VA_DA
	set.rd	rd5, M2
	STV	rd5, VA_DB
	set.rd	rd5, M3
	STV	rd5, VA_DC
	set.rd	rd5, M4
	STV	rd5, VA_DD

.if PTW_CASE == 1
	@@ ---- 001：首次访问缺页步进+填充，第二次命中 ----
	LDV	rd5, 0
	__VERIFY_RD	1, rd5, M1
	LDV	rd6, 0
	__VERIFY_RD	2, rd6, M1
	__EXIT	0

.elseif PTW_CASE == 2
	@@ ---- 002：命中不重读 PTE（改 PPN 后仍读旧 PA）----
	SIG_BEGIN	TEST_BUF, 3
	LDV	rd5, 0
	__VERIFY_RD	4, rd5, M1
	SIGUPD	rd5
	EDIT_L2	0, PTE_DB_A0D0
	LDV	rd6, 0
	__VERIFY_RD	5, rd6, M1
	SIGUPD	rd6
	READ_L2	rd7, 0
	__VERIFY_RD	6, rd7, PTE_DB_A0D0
	SIGUPD	rd7
	SIG_DUMP	TEST_BUF, 3
	__EXIT	0

.elseif PTW_CASE == 3
	@@ ---- 003：invalid + scope=VA 只删包含 start 的条目 ----
	LDV	rd5, 0
	__VERIFY_RD	8, rd5, M1
	LDV	rd6, VA1
	__VERIFY_RD	9, rd6, M2
	EDIT_L2	0, PTE_DC_A0D0
	EDIT_L2	1, PTE_DD		@@ 若重走页表会读到 M4
	TLB_START	0x40			@@ 落在 X 页内（非页首）
	TLB_CTL	CTL_INVALID_VA
	LDV	rd5, 0
	__VERIFY_RD	10, rd5, M3
	LDV	rd6, VA1
	__VERIFY_RD	11, rd6, M2
	__EXIT	0

.elseif PTW_CASE == 4
	@@ ---- 004：invalid + range 只失效相交者；range&&size=0 / scope=11 ⇒ CFXREG ----
	LDV	rd5, 0
	__VERIFY_RD	12, rd5, M1
	LDV	rd6, VA1
	__VERIFY_RD	13, rd6, M2
	EDIT_L2	0, PTE_DC_A0D0
	EDIT_L2	1, PTE_DD		@@ 若重走页表会读到 M4
	TLB_START	0x8000			@@ 区间 [0x8000,0x10000) 只与 X 相交
	TLB_SIZE	0x8000
	TLB_CTL	CTL_INVALID_RANGE
	LDV	rd5, 0
	__VERIFY_RD	14, rd5, M3
	LDV	rd6, VA1
	__VERIFY_RD	15, rd6, M2
	@@ range && size = 0 ⇒ CFXREG（TLB-24）
	ARM_FAULT	c4a_ok
	TLB_START	0
	TLB_SIZE	0
c4a_fault:
	TLB_CTL	CTL_INVALID_RANGE_NOANY
c4a_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	16, rd5, CAUSE_CFXREG
	@@ scope = 11（保留）⇒ CFXREG
	ARM_FAULT	c4b_ok
c4b_fault:
	TLB_CTL	CTL_INVALID_RESERVED
c4b_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	17, rd5, CAUSE_CFXREG
	@@ scope = all 忽略 start/size：先把两页重新填上，再用垃圾 start/size
	EDIT_L2	0, PTE_DA_A0D0
	EDIT_L2	1, PTE_DB_A0D0
	INVAL_ALL
	LDV	rd5, 0
	__VERIFY_RD	18, rd5, M1
	LDV	rd6, VA1
	__VERIFY_RD	19, rd6, M2
	EDIT_L2	0, PTE_DC_A0D0
	EDIT_L2	1, PTE_DD
	TLB_START	0x3ffffffff000
	TLB_SIZE	0x1000
	TLB_CTL	CTL_INVALID_ALL
	LDV	rd5, 0
	__VERIFY_RD	20, rd5, M3
	LDV	rd6, VA1
	__VERIFY_RD	21, rd6, M4
	__EXIT	0

.elseif PTW_CASE == 5
	@@ ---- 005：ASID_ANY / G ----
	LDV	rd5, 0
	__VERIFY_RD	18, rd5, M1
	LDV	rd6, VA1
	__VERIFY_RD	19, rd6, M2
	EDIT_L2	0, PTE_DC_A0D0
	EDIT_L2	1, PTE_DB_G_NEW
	@@ (a) ASID_ANY = 0：G=0 的条目删、G=1 的保留
	TLB_CTL	CTL_INVALID_ALL_NOANY
	LDV	rd5, 0
	__VERIFY_RD	20, rd5, M3
	LDV	rd6, VA1
	__VERIFY_RD	21, rd6, M2
	@@ (b) ASID_ANY = 1：两者都删
	TLB_CTL	CTL_INVALID_ALL
	LDV	rd5, 0
	__VERIFY_RD	22, rd5, M3
	LDV	rd6, VA1
	__VERIFY_RD	23, rd6, M4
	@@ (c) G 跨 ASID：ASID 0 填 G 条目，ASID 1 仍命中
	EDIT_L2	0, PTE_DA_A0D0
	EDIT_L2	1, PTE_DB_G
	TLB_CTL	CTL_INVALID_ALL
	LDV	rd6, VA1
	__VERIFY_RD	24, rd6, M2
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc1, rd6		@@ tlb_asid = 1
	EDIT_L2	0, PTE_DC_A0D0
	LDV	rd6, VA1
	__VERIFY_RD	25, rd6, M2
	LDV	rd5, 0
	__VERIFY_RD	26, rd5, M3
	__EXIT	0

.elseif PTW_CASE == 6
	@@ ---- 006：clean 原子 OR 回写 A/D 且保留条目；invalid 不回写且删除 ----
	SIG_BEGIN	TEST_BUF, 3
	LDV	rd5, 0
	__VERIFY_RD	28, rd5, M1
	READ_L2	rd6, 0
	__VERIFY_RD	29, rd6, PTE_DA_A0D0
	SIGUPD	rd6
	@@ store 让 D 挂起（访问本身不回写；clean 才 OR 回写 A/D）
	set.rd	rd5, M4
	STV	rd5, 0
	TLB_START	0
	TLB_CTL	CTL_CLEAN_VA
	READ_L2	rd6, 0
	__VERIFY_RD	30, rd6, PTE_DA_A1D1
	SIGUPD	rd6
	@@ clean 保留条目：改 L2 后仍读旧 PA 的数据（DA 已是 M4）
	EDIT_L2	0, PTE_DC_A0D0
	LDV	rd6, 0
	__VERIFY_RD	31, rd6, M4
	@@ invalid 不回写 A/D：对 Y 做 store（D 挂起）后 invalid
	set.rd	rd5, M4
	STV	rd5, VA1
	TLB_START	VA1
	TLB_CTL	CTL_INVALID_VA
	READ_L2	rd6, 1
	__VERIFY_RD	32, rd6, PTE_DB_A0D0
	SIGUPD	rd6
	EDIT_L2	1, PTE_DC_A0D0
	LDV	rd6, VA1
	__VERIFY_RD	33, rd6, M3
	SIG_DUMP	TEST_BUF, 3
	__EXIT	0

.elseif PTW_CASE == 7
	@@ ---- 007：flush 回写 A/D 并删除；回写失败（RTL 不可构造）----
	SIG_BEGIN	TEST_BUF, 4
	LDV	rd5, 0
	__VERIFY_RD	36, rd5, M1
	set.rd	rd5, M3
	STV	rd5, 0
	TLB_START	0
	TLB_CTL	CTL_FLUSH_VA
	READ_L2	rd6, 0
	__VERIFY_RD	37, rd6, PTE_DA_A1D1
	SIGUPD	rd6
	EDIT_L2	0, PTE_DB_A0D0
	LDV	rd6, 0
	__VERIFY_RD	38, rd6, M2
	SIGUPD	rd6
	@@ 回写失败面：RTL 的 PA RAM 全可写 ⇒ 两次 flush 都成功；
	@@ 槽 2/3 记 (cause_info, cause_id) = (0, 0)（未发生异常），
	@@ 由 `expected-divergences.yaml` 的 DIV-14 登记（QEMU/gem5 为
	@@ ROM 页表的 CFXMEM[56] + 2 次失败）。
	ARM_FAULT	c7_ok
	TLB_CTL	CTL_INVALID_ALL
	TLB_CTL	CTL_INVALID_ALL
c7_ok:
	READ_INFO	rd7
	SIGUPD	rd7
	READ_CAUSE	rd7
	SIGUPD	rd7
	SIG_DUMP	TEST_BUF, 4
	__EXIT	0

.elseif PTW_CASE == 8
	@@ ---- 008：写 PTBR（同值/异值）、ASID、ptw_enable=1 均不隐含失效 ----
	LDV	rd5, 0
	__VERIFY_RD	40, rd5, M1
	@@ 同值 PTBR
	set.rd	rd6, PT_L1
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	LDV	rd5, 0
	__VERIFY_RD	41, rd5, M1
	@@ 异值 PTBR：若失效会重走 L1B ⇒ 读到 DB 的 M2
	set.rd	rd6, PT_L1B
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	LDV	rd5, 0
	__VERIFY_RD	42, rd5, M1
	@@ ASID / ptw_enable 写
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg12, rc1, rd6
	LDV	rd5, 0
	__VERIFY_RD	43, rd5, M1
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	LDV	rd5, 0
	__VERIFY_RD	44, rd5, M1
	@@ 显式 invalid 才让 PTBR 生效
	INVAL_ALL
	LDV	rd6, 0
	__VERIFY_RD	45, rd6, M2
	__EXIT	0

.elseif PTW_CASE == 9
	@@ ---- 009：ptw_enable=0 ⇒ 只置 CFXMEM（无高位位图）+ info=访存地址；TLB 旁路 ----
	LDV	rd5, 0
	__VERIFY_RD	46, rd5, M1
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg8, rc8, rd6		@@ PTW off
	ARM_FAULT	c9_ok
c9_fault:
	LDV	rd5, 0
c9_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	47, rd5, CAUSE_NONPTW
	READ_INFO	rd6
	__VERIFY_RD	48, rd6, 0
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	INVAL_ALL
	__EXIT	0

.elseif PTW_CASE == 10
	@@ ---- 010：页表未映射 ⇒ 只置 DGPTRAP / IGPTRAP（CFXMEM=0） ----
	ARM_FAULT	c10a_ok
c10a_fault:
	LDV	rd5, VA1
c10a_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	50, rd5, CAUSE_DGPTRAP
	READ_INFO	rd6
	__VERIFY_RD	51, rd6, VA1
	@@ 取指
	ARM_FAULT	c10b_ok
	set.rb	rb4, VA1
	set.rd	rd6, 0
c10b_fault:
	jump	[rb4, rd6, 0]
c10b_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	52, rd5, CAUSE_IGPTRAP
	READ_INFO	rd6
	__VERIFY_RD	53, rd6, VA1
	__EXIT	0

.elseif PTW_CASE == 11
	@@ ---- 011：W=0/R=0/X=0/HSJU 缺 H ⇒ CFXPERM 子原因 ----
	EDIT_L2	0, PTE_W0
	INVAL_ALL
	ARM_FAULT	c11a_ok
c11a_fault:
	set.rd	rd5, M2
	STV	rd5, 0
c11a_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	54, rd5, CAUSE_NWPERM
	EDIT_L2	0, PTE_R0
	INVAL_ALL
	ARM_FAULT	c11b_ok
c11b_fault:
	LDV	rd5, 0
c11b_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	55, rd5, CAUSE_NRPERM
	EDIT_L2	0, PTE_X0
	INVAL_ALL
	ARM_FAULT	c11c_ok
	set.rb	rb4, 0
	set.rd	rd6, 0
c11c_fault:
	jump	[rb4, rd6, 0]
c11c_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	56, rd5, CAUSE_NXPERM
	EDIT_L2	0, PTE_H0
	INVAL_ALL
	ARM_FAULT	c11d_ok
c11d_fault:
	LDV	rd5, 0
c11d_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	57, rd5, CAUSE_NHPERM
	__EXIT	0

.elseif PTW_CASE == 12
	@@ ---- 012：改 PTE 不失效仍读旧页；invalid+VA 后才生效 ----
	LDV	rd5, 0
	__VERIFY_RD	58, rd5, M1
	EDIT_L2	0, PTE_DB_A0D0
	LDV	rd5, 0
	__VERIFY_RD	59, rd5, M1
	TLB_START	0
	TLB_CTL	CTL_INVALID_VA
	LDV	rd6, 0
	__VERIFY_RD	60, rd6, M2
	__EXIT	0

.elseif PTW_CASE == 13
	@@ ---- 013：cfx 空间旁路（cfx_pmem SRAM 窗口）+ 保留 cfx ⇒ CFXMEM ----
	@@ 判据（`DADAO-12 §2.1/§2.2.1`、`TLB-40`）：`addr[47:42] != 0` 的 cfx 内部
	@@ 空间不经 PTW/TLB ⇒ 页表全零也能访问 `cfx_pmem` 的 SRAM 窗口；保留 cfx
	@@ 的普通 ld 只置 `CFXMEM`（低位 cause），`cause_info` = 访问地址。
	@@ 与 QEMU 载体 `arch-ptw-013` 的签名流同序：窗口写后回读、cause_id、cause_info。
	SIG_BEGIN	TEST_BUF, 3

	@@ 页表整表清零（PT_L1B）后 PTBR 指过去：PTW 开着也没有任何映射
	set.rb	rb6, VA_BASE + PT_L1B
	set.rd	rd7, 0
	st.o	rd7, [rb6, 0]
	st.o	rd7, [rb6, 8]
	st.o	rd7, [rb6, 16]
	st.o	rd7, [rb6, 24]
	INVAL_ALL
	set.rd	rd6, PT_L1B
	cfx2rc	cfx_ptw, cg9, rc0, rd6

	@@ cfx_pmem SRAM 窗口：写 M1、读回（不经页表）
	set.rd	rd5, M1
	STV	rd5, PMEM_SRAM
	LDV	rd6, PMEM_SRAM
	__VERIFY_RD	2, rd6, M1
	@@ 先记录回读值（槽 0 = M1）；`INVAL_ALL` 会覆写 rd6（`CTL_INVALID_ALL`）
	SIGUPD	rd6

	@@ 还原恒等表：签名区/后续访存都靠它
	set.rd	rd6, PT_L1
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	INVAL_ALL

	@@ 保留 cfx 的普通 ld ⇒ CFXMEM（低位 cause 1<<1），cause_info = 访问地址
	ARM_FAULT	c13_ok
c13_fault:
	LDV	rd5, RESERVED_CFX
c13_ok:
	READ_CAUSE	rd5
	__VERIFY_RD	3, rd5, CAUSE_NONPTW
	SIGUPD	rd5
	READ_INFO	rd6
	__VERIFY_RD	4, rd6, RESERVED_CFX
	SIGUPD	rd6
	SIG_DUMP	TEST_BUF, 3
	__EXIT	0

.else
	.error	"PTW_CASE must be 1..13"
.endif

	@@ 放行块（cfx_hmon/hypv 下把 cfx_ptw 的 hypv 源掩码打开）
	.balign 4
perm_mon:
	PERM_OPEN	cfx_ptw
	PERM_MON_CLOSE
