@@ ld.o_rrii_ra.S — ld.o raHA, [rbHB, imms12]（rrii, opc 0x24）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ld.o_rrii_ra　形式：rrii　opc：0x24　mask：0xFF000000
@@ 语义：目的 ← zero_extend(mem[EA])；EA = rb[47:0] + imms12（大端；64 位零扩展）
@@ 对齐：EA 需 8 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：该银行 0 号寄存器可作目的（无 dst_0 限制）；`ra0` 是 **DADAO MemRAS 窗口**：
@@   `[63:54]` = SBZ（**写无效**）、`[53:48]` = `RACNT`、`[47:0]` = `MRPTR`（`spec/SimRISC-00 §2.4`）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 6 / overlap 2 / ra0 7（链例 22 + 故障例 2；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ ra0 段（用户 2026-11-13 裁定：读写都测；写时 `[63:54]` 的 SBZ 10 位忽略）：
@@   写：`ld.o ra0, [rb5, imm]` 写入含 SBZ 置位的值 ⇒ `ra2rd` 读回，`[63:54]` 必为 0、
@@     `[53:48]`/`[47:0]` 生效（源值就地用 `st.o` 预置，不新增数据区字节）；
@@   读：`call` 压栈 / `call` 溢出到 MemRAS / `ret` 走 D4b 构造已知 `RACNT`·`MRPTR`，
@@     再 `ra2rd` 拷到 RD 校验两字段（期望 = 架构常量，落点地址写 `ENTRY + <偏移>`）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

@@ ---- 文件专用宏（m15-testcases-002 下沉；只被本文件使用）----
@@ ra 目的
.macro TEST_LD_RA pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	ra2rd	{rd21:rd21}, {\dst:\dst}
	set.rd	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_LD_RA         1, ld.o,   ra63,  rb63,  TEST_DATA,          0x000,    0x0123456789ABCDEF
	TEST_LD_RA         2, ld.o,   ra1,   rb1,   TEST_DATA + 0x008,  0x000,    0x0011223344556677

	@@ ---- semantic ----
	TEST_LD_RA         3, ld.o,   ra2,   rb4,   TEST_DATA,          0x000,    0x0123456789ABCDEF
	TEST_LD_RA         4, ld.o,   ra2,   rb4,   TEST_DATA,          0x008,    0x0011223344556677
	TEST_LD_RA         5, ld.o,   ra2,   rb4,   TEST_DATA,          0x010,    0x8899AABBCCDDEEFF
	TEST_LD_RA         6, ld.o,   ra2,   rb4,   TEST_DATA,          0x020,    0x8000000000000000
	TEST_LD_RA         7, ld.o,   ra2,   rb4,   TEST_DATA,          0x018,    0xFFEEDDCCBBAA9988

	@@ ---- boundary ----
	TEST_LD_RA         8, ld.o,   ra5,   rb6,   TEST_DATA,          0x030,    0x0000000000000080
	TEST_LD_RA         9, ld.o,   ra5,   rb6,   TEST_DATA,          0x028,    0x7FFFFFFFFFFFFFFF
	TEST_LD_RA        10, ld.o,   ra5,   rb6,   TEST_DATA,          0x0E0,    0x0000000000000000
	TEST_LD_RA        11, ld.o,   ra5,   rb6,   TEST_DATA,          0x098,    0x5555555555555555
	TEST_LD_RA        12, ld.o,   ra7,   rb7,   TEST_DATA + 0x800,  -0x800,   0x0123456789ABCDEF
	TEST_LD_RA        13, ld.o,   ra8,   rb8,   TEST_DATA + 0x800,  -0x7F8,   0x0011223344556677

	@@ ---- overlap ----
	TEST_LD_RA        14, ld.o,   ra1,   rb1,   TEST_DATA,          0x000,    0x0123456789ABCDEF
	@@ overlap：同一目的连装两次，后到者生效
	LOAD_ADDR rb9, TEST_DATA
	ld.o    ra2, [rb9, 0x000]
	ld.o    ra2, [rb9, 0x008]
	ra2rd	{rd21:rd21}, {ra2:ra2}
	__CHECK_RD 15, rd21, 0x0011223344556677

	@@ ---- ra0 读：`call`/`ret` 构造已知 RACNT·MRPTR ⇒ `ra2rd` 拷到 RD 校验 ----
	@@ 顺序：读段在前、写段在后 —— 写段的 `[63:54]` 判据是三平台**分歧点**（见写段注释），
	@@   放最后可让读段在三平台都跑到。
	@@ R1：`call` 冷栈压栈（C1）⇒ RACNT 0→1、MRPTR 保持 0（在**被调函数内**读，尚未 ret）
	call	[rb0, __r1_f]
	jump	[rb0, __r1_ck]
__r1_f:
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 16, rd25, 0x0001000000000000
	ret	rd0, 0
__r1_ck:

	@@ R2：两层嵌套 call（C3a）⇒ RACNT = 2、MRPTR 仍 0
	call	[rb0, __r2_f1]
	jump	[rb0, __r2_ck]
__r2_f1:
	call	[rb0, __r2_f2]
	jump	[rb0, __r2_f1b]
__r2_f2:
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 17, rd25, 0x0002000000000000
	ret	rd0, 0
__r2_f1b:
	ret	rd0, 0
__r2_ck:

	@@ R3：满栈（RACNT = 63）+ MRPTR ≠ 0 再 call ⇒ C3b 把最旧条目写入 MemRAS、
	@@   MRPTR −= 8，RACNT 保持 63（ra63 栈顶返回地址 ≠ 本 call 的返回地址 ⇒ 不走 C2）
	set.rd	rd5, 0x0001CCCC00000000
	rd2ra	{ra63}, {rd5}
	set.rd	rd5, (0x003F000000000000 + MEMRAS + 0x80)
	rd2ra	{ra0}, {rd5}
	call	[rb0, __r3_f]
	jump	[rb0, __r3_ck]
__r3_f:
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 18, rd25, (0x003F000000000000 + MEMRAS + 0x78)
	ret	rd0, 0
__r3_ck:

	@@ R4：RACNT = 0、MRPTR = MEMRAS + 0x78、条目递归计数 = 1 ⇒ `ret` 走 D4b 消费该条目
	@@   ⇒ MRPTR += 8、RACNT 仍 0；落点由 `.org 0x1000` 钉住（返回地址写绝对常量）
	set.rd	rd5, (0x0001000000000000 + ENTRY + 0x1000)
	LOAD_ADDR rb5, (MEMRAS + 0x78)
	st.o	rd5, [rb5, 0]                @@ MemRAS[MRPTR] = {计数 1, 返回地址 = 落点}
	set.rd	rd5, (MEMRAS + 0x78)         @@ ra0 = {RACNT = 0, MRPTR = MEMRAS + 0x78}
	rd2ra	{ra0}, {rd5}
	ret	rd0, 0
	__EXIT	19                           @@ 未弹出/未跳转 ⇒ 按该点号判红
	.org	0x1000
__r4_land:
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 19, rd25, (MEMRAS + 0x80)

	@@ ---- ra0 写：`[63:54]` 的 SBZ 10 位写无效（`spec/SimRISC-00 §2.4`）----
	@@ 源值用 `st.o`（rd 银行）就地预置到 TEST_DATA 的空闲 beat，被测指令 = `ld.o ra0`；
	@@ 读回用 `ra2rd`（全 64 位块赋值，含 RA 高 16 位）；期望 = 源值的低 54 位。
	@@ **三平台分歧点**：chipyard 写入丢弃 `[63:54]`（读回 0）；QEMU/gem5 全 64 位可写
	@@   （读回保留写入位）⇒ 这三点在 QEMU/gem5 记红并登记 issue（候选号见任务书「遗留问题」）；
@@   期望**不放宽**。
	LOAD_ADDR rb5, TEST_DATA
	set.rd	rd5, 0xFFFF000000000000      @@ [63:54] = 0x3FF（SBZ 全置）、RACNT = 63、MRPTR = 0
	st.o	rd5, [rb5, 0x040]
	ld.o	ra0, [rb5, 0x040]
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 20, rd25, 0x003F000000000000      @@ SBZ 位读回 0、RACNT 生效

	set.rd	rd5, 0xFFC0000001234568      @@ SBZ 仍全置、RACNT = 0、MRPTR = 0x1234568
	st.o	rd5, [rb5, 0x048]
	ld.o	ra0, [rb5, 0x048]
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 21, rd25, 0x0000000001234568      @@ MRPTR 生效

	set.rd	rd5, 0xFFEAA5A55A5A1230      @@ SBZ 仍全置、RACNT = 42、MRPTR = 0xA5A55A5A1230
	st.o	rd5, [rb5, 0x050]
	ld.o	ra0, [rb5, 0x050]
	ra2rd	{rd25}, {ra0}
	__CHECK_RD 22, rd25, 0x002AA5A55A5A1230      @@ 两字段同时生效

	rd2ra	{ra0}, {rd0}                 @@ 复位 RA 状态（RACNT = 0、MRPTR = 0）

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        23, ld.o,   ra1,   MALIGN, rb3,                TEST_DATA, 0x004  @@ EA 未按 8 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        24, ld.o,   ra1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
