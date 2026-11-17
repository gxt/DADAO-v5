@@ swym_oiii_imm.S — swym immu18（oiii, opc 0x47／ha 0x22）
@@ 大类：12-misc（其它指令 · 空转指令 `spec/SimRISC-12 §2`）；册目录 `tests/inst/12-misc/`
@@ id：swym_oiii_imm　形式：oiii　opc：0x47／ha 0x22　mask：0xFFFC0000　value：0x47880000　操作数：immu18
@@ 语义：`swym N` 除 IP 自增（+4）外**无任何架构副作用**；后 18 位立即数 N 是硬件时延提示
@@   （具体时延由实现确定，约 `swym 0` 的 N+1 倍；实现可设上限）⇒ 功能测试只断言
@@   「IP 前进 4」与「寄存器/内存不变」，**不断言耗时**（时延不可在功能层观测，见下 GAP）
@@ 合法性：`legality: []`（`contracts/opcodes.yaml`）——无 rd0/rb0、无保留编码、无非法 immu18
@@   ⇒ 本文件**无故障例**（immu18 全 18 位取值合法）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：oiii = opc | ha[23:18] | immu18[17:0]（imm 字段无 mask 位）
@@ IP 观测：`aip.si rb, 0` 取该指令**自身**地址（`spec/SimRISC-05 §2`，低位不清零）⇒ 两次
@@   `aip.si` 之差 = 中间指令总字节数；`sub.o rdHB, rbHC, rbHD` = rbHC − rbHD（`spec/SimRISC-05 §1`）。
@@   两条 `aip.si` 之间只放被测 swym（或 `.dd.t32` 原始编码字），差值里再减 4 B（后一条 aip 自身）
@@   ⇒ 期望一律写成字面量（不依赖链接布局，不用标签算术）
@@ 数据块：`tests/inst/macros/inst_test.inc` 零区（S0/S1 = TEST_DATA+0x500/0x508，例间不共享）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / legality 0（无规则）/ overlap 1（oiii 无寄存器操作数
@@   ⇒ 以「插入访存序列中间」与「rb 银行哨兵」两类等价观测替代）（链例 13，无故障例）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 期望来自 spec/SimRISC-12 §2 + contracts/opcodes.yaml（不从实现反推）
@@ GAP（不可测，如实记录不伪造）：① `swym N` 的**时延倍数**（N+1 倍与上限）属性能语义，
@@   功能级无观测点；② 「不占用额外指令带宽」只能由「IP 每次 +4」间接反映（本文件已覆盖）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/12-misc/12-misc.inc"

@@ 数据区（TEST_DATA 零区；每例独立 8 B 拍）
	.equ S0, TEST_DATA + 0x500
	.equ S1, TEST_DATA + 0x508

	__TEST_BEGIN

	@@ ---- encoding：规范编码字 0x47880000（swym 0）直接执行 ⇒ IP 前进 4（差值 8）----
	@@! inputs: kind=enc word=0x47880000 imm=0
	aip.si	rb18, 0
	.dd.t32	0x47880000
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	1, rd2, 0x0000000000000008

	@@ ---- semantic：`swym 0` 无架构副作用（寄存器与内存均不变）----
	@@! inputs: kind=swym imm=0
	__PREP_LI_ADDR	rd6, 0x0123456789ABCDEF, rb3, S0
	st.o	rd6, [rb3, 0]
	swym	0
	__CHECK_RD	2, rd6, 0x0123456789ABCDEF
	__VERIFY_MEM	2, S0, 0, 0x0123456789ABCDEF

	@@ ---- semantic：`swym 1` ⇒ IP 前进 4 且寄存器不变 ----
	@@! inputs: kind=swym imm=1
	set.rd	rd6, 0xFEDCBA9876543210
	aip.si	rb18, 0
	swym	1
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	3, rd2, 0x0000000000000008
	__VERIFY_RD	3, rd6, 0xFEDCBA9876543210

	@@ ---- semantic：`swym 42` 无架构副作用 ----
	@@! inputs: kind=swym imm=42
	set.rd	rd9, 0x0F1E2D3C4B5A6978
	swym	42
	__CHECK_RD	4, rd9, 0x0F1E2D3C4B5A6978

	@@ ---- semantic/overlap 替代：`swym 7` 插在 store 与 load 之间 ⇒ 存储值不变 ----
	@@! inputs: kind=swym imm=7
	__PREP_LI_ADDR	rd6, 0xA5A5A5A55A5A5A5A, rb3, S1
	st.o	rd6, [rb3, 0]
	swym	7
	ld.o	rd7, [rb3, 0]
	__CHECK_RD	5, rd7, 0xA5A5A5A55A5A5A5A
	__VERIFY_MEM	5, S1, 0, 0xA5A5A5A55A5A5A5A

	@@ ---- encoding：规范编码字 0x4788002A（swym 42，immu18 非零）⇒ IP 前进 4 ----
	@@! inputs: kind=enc word=0x4788002A imm=42
	aip.si	rb18, 0
	.dd.t32	0x4788002A
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	6, rd2, 0x0000000000000008

	@@ ---- boundary：immu18 上界（0x3FFFF）原始编码字 ⇒ 单条 4 B、寄存器不变 ----
	@@! inputs: kind=enc word=0x478BFFFF imm=0x3FFFF
	set.rd	rd6, 0x1111222233334444
	aip.si	rb18, 0
	.dd.t32	0x478BFFFF
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	7, rd2, 0x0000000000000008
	__VERIFY_RD	7, rd6, 0x1111222233334444

	@@ ---- boundary：助记符形式 `swym 0x3FFFF`（immu18 上界）⇒ 单条 4 B ----
	@@! inputs: kind=swym imm=0x3FFFF
	aip.si	rb18, 0
	swym	0x3FFFF
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	8, rd2, 0x0000000000000008

	@@ ---- boundary：连续 4 条 swym ⇒ IP 前进 16（每条单条 4 B，不展开为多字）----
	@@! inputs: kind=swym imm=0,1,2,3
	aip.si	rb18, 0
	swym	0
	swym	1
	swym	2
	swym	3
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	9, rd2, 0x0000000000000014

	@@ ---- boundary：immu18 的 bit17 置位（0x20000）⇒ 仍为单条 4 B ----
	@@! inputs: kind=enc word=0x478A0000 imm=0x20000
	aip.si	rb18, 0
	.dd.t32	0x478A0000
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	10, rd2, 0x0000000000000008

	@@ ---- boundary：immu18 低 17 位全 1（0x1FFFF）⇒ 仍为单条 4 B ----
	@@! inputs: kind=enc word=0x4789FFFF imm=0x1FFFF
	aip.si	rb18, 0
	.dd.t32	0x4789FFFF
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	11, rd2, 0x0000000000000008

	@@ ---- overlap 替代：rb 银行哨兵（rb23）经 rb2rd 观测 ⇒ swym 不写任何寄存器银行 ----
	@@! inputs: kind=swym imm=9
	set.rb	rb23, 0x00FF00FF00FF00FF
	swym	9
	rb2rd	{rd8:rd8}, {rb23:rb23}
	__CHECK_RD	12, rd8, 0x00FF00FF00FF00FF

	@@ ---- semantic：rd0 是零寄存器 ⇒ swym 前后读出恒 0 ----
	@@! inputs: kind=swym imm=0
	swym	0
	__CHECK_RD	13, rd0, 0x0000000000000000

	__TEST_END

	__TEST_SECTIONS
