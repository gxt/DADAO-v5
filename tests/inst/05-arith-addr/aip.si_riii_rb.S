@@ aip.si_riii_rb.S — aip.si rbHA, imms30（riii/rb, opc 0x5A）
@@ 大类：05-arith-addr（64 位地址运算，`spec/SimRISC-05 §4`）；册目录 `tests/inst/05-arith-addr/`
@@ id：aip.si_riii_rb　形式：riii（rb）　opc：0x5A　mask：0xFF000000　value：0x5A000000　目的银行：RB
@@ 语义：rbHA ← IP + (SX(imms18) << 12)；**IP = 该指令自身地址**（`rb0` 读出值，非下一条、
@@   无 ±4 流水偏移、低位不清零）；立即数单位为 4 KiB 块、有符号 ⇒ 可达 ±512 MiB
@@   汇编层操作数按**字节**书写（`imms30`，须为 4096 整数倍；编码层 imms18 = 字节 >> 12）；
@@   全 64 位结果（不截断；仅当以结果访存时取 [47:0]）
@@ 合法性：目的 rbHA 为 rb0 ⇒ ILLI（`dst_rb0`）；rb0 作源读出 IP（本指令的基址即 rb0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：riii = opc | rbha[23:18] | imms18[17:0]
@@ 定位：本 id 的期望值含**链接期地址**（IP）⇒ aip.si 指令用 `.org` 钉在 ENTRY+0x200 起的
@@   连续 4 字节槽（`jump` 跳过对齐填充的零字，零字不执行）；期望一律写成 `ENTRY + <字面偏移>`
@@   —— llvm-mc 只折装**绝对常量**表达式，标签差（`. - _start`）在指令立即数里会被折成 0
@@   （现场实测，见 `MIGRATION §6/019`），故本文件不用标签算术
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rb` 拼初值；本册复用 04 的数据块）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 2 / semantic 4 / boundary 3 / overlap 2（链例 11 + 故障例 1；无「源=目」类
@@   ——目的只写、基址 rb0 只读）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：目的在 RB ⇒ 实测经同组 `st.o` 落到 SCRATCH（rb29 指）再 `__CHECK_MEM`

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/05-arith-addr/05-arith-addr.inc"

	__TEST_BEGIN

	@@ 目的旧值（overlap 例：aip.si 只写不读，旧值必须被完整覆盖）
	set.rb	rb14, 0xDEADBEEFCAFEF00D

	@@ aip.si 槽位区（ENTRY+0x200 起，每槽 4 B）：jump 跳过 `.org` 填充的零字
	jump	[rb0, __aip_block]
	.org	0x200
__aip_block:
	.dd.t32	0x5A140000        @@ 槽 0 → 点 1：编码字，rb5 / imms18 = 0
	aip.si	rb63, 536866816   @@ 槽 1 → 点 2：字段边界 rb63 + s18 上界（+131071 块）
	aip.si	rb6, 0            @@ 槽 2 → 点 3：IP = 自身地址（非下一条）
	aip.si	rb7, 4096         @@ 槽 3 → 点 4：+1 块（<<12，不是 <<2）
	aip.si	rb8, -4096        @@ 槽 4 → 点 5：-1 块（有符号）
	aip.si	rb9, 8192         @@ 槽 5 → 点 6：+2 块
	aip.si	rb10, 536866816   @@ 槽 6 → 点 7：s18 上界
	aip.si	rb11, -536870912  @@ 槽 7 → 点 8：s18 下界
	aip.si	rb13, 4096        @@ 槽 8 → 点 9：IP 低位不清零（段内偏移 0x220 ⇒ IP 低 12 位 = 0x320）
	aip.si	rb12, 0           @@ 槽 9（同目的连写：前值被覆盖）
	aip.si	rb12, 4096        @@ 槽 10 → 点 10：最终值
	aip.si	rb14, -4096       @@ 槽 11 → 点 11：覆盖槽外装载的旧值

	@@ ---- encoding ----
	st.o	rb5, [rb29, 0]
	__CHECK_MEM         1, SCRATCH, 0, (ENTRY + 0x200)
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, (ENTRY + 0x204 + 0x1FFFF000)

	@@ ---- semantic ----
	@@ imms18 = 0 ⇒ 结果 = 该指令自身地址（若按「下一条 = IP+4」或「页对齐」口径 ⇒ 点号非零）
	st.o	rb6, [rb29, 0]
	__CHECK_MEM         3, SCRATCH, 0, (ENTRY + 0x208)

	@@ +1 个 4 KiB 块（若误作 <<2 得 ENTRY+0x20C+0x4 ⇒ 点号非零）
	st.o	rb7, [rb29, 0]
	__CHECK_MEM         4, SCRATCH, 0, (ENTRY + 0x20C + 0x1000)

	@@ -1 个 4 KiB 块（imms18 有符号、符号扩展后 <<12）
	st.o	rb8, [rb29, 0]
	__CHECK_MEM         5, SCRATCH, 0, (ENTRY + 0x210 - 0x1000)

	@@ +2 个块：偏移随立即数线性增长
	st.o	rb9, [rb29, 0]
	__CHECK_MEM         6, SCRATCH, 0, (ENTRY + 0x214 + 0x2000)

	@@ ---- boundary ----
	@@ imms18 上界 +131071（= +0x1FFFF000，±512 MiB 上界方向）
	st.o	rb10, [rb29, 0]
	__CHECK_MEM         7, SCRATCH, 0, (ENTRY + 0x218 + 0x1FFFF000)

	@@ imms18 下界 -131072（= -0x20000000，±512 MiB 下界方向）
	st.o	rb11, [rb29, 0]
	__CHECK_MEM         8, SCRATCH, 0, (ENTRY + 0x21C - 0x20000000)

	@@ IP 低位**不清零**（auipc 式）：本槽段内偏移 = 0x220（IP 低 12 位 = 0x320），结果保留该低位
	st.o	rb13, [rb29, 0]
	__CHECK_MEM         9, SCRATCH, 0, (ENTRY + 0x220 + 0x1000)

	@@ ---- overlap ----
	@@ 同目的连写：槽 9/10 都写 rb12，最终值 = 槽 10 的结果（后者覆盖前者）
	st.o	rb12, [rb29, 0]
	__CHECK_MEM        10, SCRATCH, 0, (ENTRY + 0x228 + 0x1000)

	@@ 目的只写：装载的旧值（0xDEADBEEFCAFEF00D）被完整覆盖
	st.o	rb14, [rb29, 0]
	__CHECK_MEM        11, SCRATCH, 0, (ENTRY + 0x22C - 0x1000)

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rb0：目的 rb0 ⇒ ILLI（rb0 读出为当前 IP、只读）
	TEST_FAULT_RB_SI    12, aip.si, ILLI, rb0, 0

	__TEST_SECTIONS
