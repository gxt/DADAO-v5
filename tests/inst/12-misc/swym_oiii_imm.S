@@ swym_oiii_imm.S — swym immu18（oiii, opc 0x47／ha 0x22）
@@ 大类：12-misc（其它指令 · 空转指令 `spec/SimRISC-12 §2`）；册目录 `tests/inst/12-misc/`
@@ id：swym_oiii_imm　形式：oiii　opc：0x47／ha 0x22　mask：0xFFFC0000　value：0x47880000　操作数：immu18
@@ 语义（`m19-spec-001` 定稿，用户 2026-11-27；真源 `spec/SimRISC-12 §2`）：
@@   * `N = immu18[11:0]`（12 位时延参数，`0 ≤ N ≤ 4095`，无上限）；
@@   * `swym N` 总时延 = **1 + N 拍**（`swym 0` = 1 拍 NOP）；
@@   * `immu18[17:12]` 为 **SBZ**，非 0 ⇒ **ILLI**；
@@   * **原子**：执行期间不取中断（pending 保持），完成后在下一个指令边界取。
@@ 功能层（本文件）：`swym` 除 IP 自增（+4）外**无任何架构副作用**；QEMU 不建模时延（按 NOP 执行）。
@@   时延/原子性属实现时序，功能层无观测点（GAP）：1/2/4096 拍由引擎 trace 断言——
@@   gem5 `tools/gem5/check_swym.py`（周期模型 1+N）与 `check_swym_atomic.py`（guest 实测差
@@   d(1)−d(0)=1、d(4095)−d(0)=4095）、chipyard `tools/chipyard/swym/`（`swym-done` − `swym` + 1
@@   = 1/2/4096）；原子性在 Tiny 无中断源的披露口径见 `m19-chipyard-003`（RTL 静态检查）。
@@ 合法性：`encode_sbz`（`contracts/opcodes.yaml`：`legality: immu18[17:12] == 0`）——
@@   `immu18[17:12] != 0` ⇒ ILLI。低位 N 全 12 位取值均合法（含 0 与 4095）。
@@ 编码：oiii = opc | ha[23:18] | immu18[17:0]（imm 字段无 mask 位）；
@@   高位段 H = immu18[17:12]、低位 N = immu18[11:0] ⇒ word = 0x47880000 | (H << 12) | N。
@@ IP 观测：`aip.si rb, 0` 取该指令**自身**地址（`spec/SimRISC-05 §2`，低位不清零）⇒ 两次
@@   `aip.si` 之差 = 中间指令总字节数；`sub.o rdHB, rbHC, rbHD` = rbHC − rbHD（`spec/SimRISC-05 §1`）。
@@   两条 `aip.si` 之间只放被测 swym（或 `.dd.t32` 原始编码字），差值里再减 4 B（后一条 aip 自身）
@@   ⇒ 期望一律写成字面量（不依赖链接布局，不用标签算术）
@@ 数据块：`tests/inst/macros/inst_test.inc` 零区（S0/S1 = TEST_DATA+0x500/0x508，例间不共享）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 4 / boundary 4 / legality 0（链例）/ overlap 2（oiii 无寄存器
@@   操作数 ⇒ 以「插入访存序列中间」与「rb 银行哨兵」两类等价观测替代）（链例 11）；
@@   故障例 4 = immu18[17:12] 高位段 H = 0x1 / 0x20 / 0x3F / 0x20（末条低 12 位合法）⇒ ILLI
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 期望来自 spec/SimRISC-12 §2 + contracts/opcodes.yaml（不从实现反推）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/12-misc/12-misc.inc"

@@ 数据区（TEST_DATA 零区；每例独立 8 字节数据单元）
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

	@@ ---- boundary：N 上界 4095（immu18 = 0x0FFF）原始编码字 ⇒ 单条 4 B、寄存器不变 ----
	@@! inputs: kind=enc word=0x47880FFF imm=0x0FFF
	set.rd	rd6, 0x1111222233334444
	aip.si	rb18, 0
	.dd.t32	0x47880FFF
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	7, rd2, 0x0000000000000008
	__VERIFY_RD	7, rd6, 0x1111222233334444

	@@ ---- boundary：助记符形式 `swym 4095`（N 上界）⇒ 单条 4 B ----
	@@! inputs: kind=swym imm=4095
	aip.si	rb18, 0
	swym	4095
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	8, rd2, 0x0000000000000008

	@@ ---- boundary：连续 4 条 swym（N = 0,1,2,3）⇒ IP 前进 16（每条单条 4 B，不展开为多字）----
	@@! inputs: kind=swym imm=0,1,2,3
	aip.si	rb18, 0
	swym	0
	swym	1
	swym	2
	swym	3
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	9, rd2, 0x0000000000000014

	@@ ---- boundary：N = 4095 与 N = 0 相邻 ⇒ 每条仍单条 4 B（时延不占指令带宽）----
	@@! inputs: kind=swym imm=4095,0
	aip.si	rb18, 0
	swym	4095
	swym	0
	aip.si	rb19, 0
	sub.o	rd2, rb19, rb18
	__CHECK_RD	10, rd2, 0x000000000000000C

	@@ ---- overlap 替代：rb 银行哨兵（rb23）经 rb2rd 观测 ⇒ swym 不写任何寄存器银行 ----
	@@! inputs: kind=swym imm=9
	set.rb	rb23, 0x00FF00FF00FF00FF
	swym	9
	rb2rd	{rd8:rd8}, {rb23:rb23}
	__CHECK_RD	11, rd8, 0x00FF00FF00FF00FF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 合法性 `encode_sbz`（`spec/SimRISC-12 §2` / `contracts/opcodes.yaml`）：
	@@   `immu18[17:12] != 0` ⇒ ILLI。汇编器对高位非零的助记符可能放行，故一律用原始编码字；
	@@   四个高位段 H = 0x1 / 0x20 / 0x3F / 0x20（最后一条低 12 位合法 ⇒ 高位优先判 ILLI）。

	@@ H = 0x1（immu18 = 0x1000；低 12 位 N = 0）
	TEST_FAULT_ENC	12, ILLI, 0x47881000, rb3, TEST_DATA, rd6, 0x000

	@@ H = 0x20（immu18 = 0x20000；低 12 位 N = 0）
	TEST_FAULT_ENC	13, ILLI, 0x478A0000, rb3, TEST_DATA, rd6, 0x000

	@@ H = 0x3F（immu18 = 0x3FFFF；低 12 位 N = 4095）
	TEST_FAULT_ENC	14, ILLI, 0x478BFFFF, rb3, TEST_DATA, rd6, 0x000

	@@ H = 0x20 且低 12 位合法（immu18 = 0x20007，N = 7）⇒ 高位仍判 ILLI
	TEST_FAULT_ENC	15, ILLI, 0x478A0007, rb3, TEST_DATA, rd6, 0x000

	__TEST_SECTIONS
