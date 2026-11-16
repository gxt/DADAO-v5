@@ fence_ciii_cfx.S — fence cfxHA, immu18（ciii, opc 0x79）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §5`）；册目录 `tests/inst/11-cfx/`
@@ id：fence_ciii_cfx　形式：ciii　opc：0x79　mask：0xFF000000　value：0x79000000
@@ 语义：约束本 hart 对所选 cfx 资源域的访问顺序；`cfx0` = all cfx（不是只作用 umon），
@@   `cfx1`–`cfx63` = 指定 cfx；`immu18 = hb[17:12] | pred[11:6] | succ[5:0]`，
@@   `pred = succ = 0` 是合法 no-op。异常规则：`hb ≠ 0` ⇒ ILLI；cfxha 为 reserved
@@   （6–14、16–31、35–61）⇒ ILLI；正常屏障不产生异常（`spec/SimRISC-11 §5`）。
@@ 编码：ciii = opc[31:24] | cfxha[23:18] | immu18[17:0]；合法 immu18 ⇒ `hb = 0` ⇒ ≤ 0x0FFF
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 12（链例 14 + 故障例 7；boundary = immu18 上界与 reserved 集）
@@   链例 13/14 并入原 YAML 的 cfx63 与混合位用例（同一 id 的旧载体）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：合法的 fence 不得改架构状态 ⇒ 每例预置 rd5 并核其不变；屏障的**排序/可见性**在
@@   Tiny 上不可观测（单 hart、无 DMA/异步观测点）⇒ 只覆盖编码/合法性/无副作用（GAP）
@@ GAP（不计入链例，见任务书完成区）：QEMU 的 fence 路径按 reserved 集 `6–14, 19–61`
@@   （局部实现），与 spec/gem5/chipyard 的 `6–14, 16–31, 35–61` 不一致。实测（探针，
@@   非本文件交付物）：`fence cfx16/17/18` spec 判 ILLI，QEMU 放行（落回 `__EXIT pt`）、
@@   chipyard/gem5 报 ILLI；`fence cfx32/33/34` spec 判合法，QEMU 报异常、
@@   chipyard/gem5 合法。故链例只用三方一致的 cfx（0/15/62/63）与保留编号（6/7/14/19/61）

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE
	LOAD_ADDR rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]              @@ 任何意外异常 ⇒ 故障落点（fail-fast）

	@@ ---- encoding：规范编码字 0x79000000（cfx0 = all cfx，pred = succ = 0 = no-op）----
	set.rd	rd5, 0x0123456789ABCDEF
	.dd.t32	0x79000000
	__CHECK_RD   1, rd5, 0x0123456789ABCDEF

	@@ ---- encoding：0x79FC0FFF（cfx63 = power，immu18 = 0x0FFF 上界，hb = 0）----
	set.rd	rd5, 0x0123456789ABCDEF
	.dd.t32	0x79FC0FFF
	__CHECK_RD   2, rd5, 0x0123456789ABCDEF

	@@ ---- semantic：pred/succ 六类访问掩码的各组合（cfx0 = all cfx）----
	set.rd	rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x041                     @@ cr → cr
	__CHECK_RD   3, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x082                     @@ cw → cw
	__CHECK_RD   4, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x108                     @@ ci → co
	__CHECK_RD   5, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x420                     @@ mr → mw
	__CHECK_RD   6, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x810                     @@ mw → mr
	__CHECK_RD   7, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x430                     @@ acquire（mr → mr|mw）
	__CHECK_RD   8, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0xC20                     @@ release（mr|mw → mw）
	__CHECK_RD   9, rd5, 0x0123456789ABCDEF
	fence	cfx0, 0xFFF                     @@ 全六位 pred|succ
	__CHECK_RD  10, rd5, 0x0123456789ABCDEF

	@@ ---- semantic：指定资源域（cfx15 = hart、cfx62 = uart；均为已分配编号）----
	set.rd	rd5, 0x0123456789ABCDEF
	fence	cfx_hart, 0x082
	__CHECK_RD  11, rd5, 0x0123456789ABCDEF
	fence	cfx_uart, 0x430
	__CHECK_RD  12, rd5, 0x0123456789ABCDEF

	@@ ---- semantic：cfx63（power）的 cfx memory W→W（同一 immu18 在不同资源域）----
	set.rd	rd5, 0x0123456789ABCDEF
	fence	cfx_power, 0x082
	__CHECK_RD  13, rd5, 0x0123456789ABCDEF

	@@ ---- semantic：cfx + 系统内存混合（cr|mr → cw|mw，pred/succ 同时跨两轴）----
	set.rd	rd5, 0x0123456789ABCDEF
	fence	cfx0, 0x462
	__CHECK_RD  14, rd5, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- 故障例：hb ≠ 0（immu18[17:12] SBZ）⇒ ILLI ----
	TEST_FAULT_ENC  15, ILLI, 0x79001000, rb12, TEST_DATA, rd11, 0   @@ hb = 1
	TEST_FAULT_ENC  16, ILLI, 0x7903F000, rb12, TEST_DATA, rd11, 0   @@ hb = 63（上界）

	@@ ---- 故障例：reserved cfxha（6 / 7 / 14 / 19 / 61）⇒ ILLI ----
	TEST_FAULT_ENC  17, ILLI, 0x79180000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  18, ILLI, 0x791C0000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  19, ILLI, 0x79380000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  20, ILLI, 0x794C0000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  21, ILLI, 0x79F40000, rb12, TEST_DATA, rd11, 0

	__TEST_SECTIONS
