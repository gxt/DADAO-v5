@@ sc.b.nn_orrr_rd.S — sc.b.nn（orrr，opc 0x47，mask 0xFFFC0000）
@@ 大类：12-misc（其它指令 · 原子 `spec/SimRISC-12 §1`）；册目录 `tests/inst/12-misc/`
@@ id：sc.b.nn_orrr_rd　形式：orrr　opc：0x47　mask：0xFFFC0000　value：0x474c0000
@@ 语义：sc 的条件写宽度 = 1 B；地址须按 1 B 自然对齐（否则 MALIGN；.b 无对齐要求）
@@ 合法性：sc 的 rdHB 是成功/失败结果（目的）⇒ rdHB = rd0 时 ILLI（dst_rd0）
@@ 存储序：.nn（无）；单 hart 链例下只约束访存顺序，不改变数值结果
@@ 保留机制（contract-isa §14.2）：粒度 = 精确地址 + 访问宽度；另一条 lr / 每次 sc（成败）/
@@   异常或中断进入 清本 hart 全部标记；sc 失败不写内存并返回 1、成功返回 0（本文件一律内联期望）
@@ 保留粒度（点 17-21，`spec/SimRISC-12 §1`「保留机制」+ 用户裁定 2026-11-14「ISS-435 严格按 spec」）：
@@   键 = lr 的**精确地址 + 访问宽度**；同 hart 对同字另一字节 / 同址异宽 / 同址同宽的普通 store
@@   **都不清标记**（清除侧只列「另一 hart 同址同宽 store」）⇒ 这些点上的 sc 必须成功（0）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA 零区；每例独立 8 B 拍（运行时置初值）
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 用例：encoding 2 / semantic 12 / boundary 5 / overlap 2 / exception 4 / 粒度 1
@@   （链例 26 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 期望来自 spec/SimRISC-12 §1 + contract-isa §14.2 + ADR-0034 D6（不从实现反推）
@@ 配对：链例里设置/消费标记用同宽度 nn 形式的 lr/sc（存储序提示不改变数值结果）
@@ 异常进入（点 22-25，`spec/SimRISC-12 §1`「保留机制」）：`lr` 后分别经 MALIGN / CFXMEM /
@@   ILLI / CFXTRAP 进入 hmon 向量，返回后 `sc` **必须失败（1）**；四条路径的期望全来自
@@   spec（「异常或中断进入」是清除事件），不取任一平台输出（`ISS-443`）。
@@ GAP（不可测，见 MIGRATION §6/028）：多 hart 同址写清标记 / 存储序强度 / sc 偶发失败
@@   —— 均不写用例、不伪造；多 hart 清除事件见 `ISS-440`（上多 hart 前必须补）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/12-misc/12-misc.inc"

@@ 数据区（TEST_DATA 零区；每例独立 8 B 拍，例间不共享可写字节）：
@@   A0..A17 / B0..B17 / L / SCR 在册宏层 `tests/inst/12-misc/12-misc.inc`（单源）；
@@   本文件只补**宽度专属**的「故意不对齐」地址 LMAL（.w/.t/.o 的 MALIGN 例）。
	.equ LMAL, TEST_DATA + 0x7f1     @@ 故意不对齐（.w/.t/.o 的 MALIGN 例）

@@ 本文件专用宏（只 sc.b.nn 用）：保留键的宽度维 —— `lr` 与 `sc` 同**精确地址**、
@@   **不同访问宽度** ⇒ 键不匹配 ⇒ `sc` 失败（1）且不写内存。
.macro __PT_SC_LR_WIDTH pt, scmnem, lrmnem, srcreg, ea, init, src
	__PT_ST_INIT	\ea, \init
	set.rb	rb3, \ea
	\lrmnem	rd2, [rb3]
	set.rd	\srcreg, \src
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \ea, 0, \init
.endm

	__TEST_BEGIN

	@@ ---- encoding：规范编码字直接执行（opc 0x47 + ha + hb=rd5 位域） ----
	@@! inputs: kind=sc-enc sym=A17 k=0 init=0x0123456789ABCDEF enc=0x474c5083
	__PT_SC_ENC	1, lr.b.nn, rd2, 0x474c5083, A17, 0x0123456789ABCDEF, 0xDEADBEEFCAFEF00D, 0x0D23456789ABCDEF

	@@ ---- encoding：无保留标记 ⇒ rdHB=1 且不写内存 ----
	@@! inputs: kind=sc sym=A0 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D resv=none
	@@ 清保留标记：lr SCR 后 sc SCR（成功消费，SCR 写 0）
	__PT_SC_NORESV	2, sc.b.nn, lr.b.nn, rd2, A0, 0x0123456789ABCDEF, 0xDEADBEEFCAFEF00D, 0x0123456789ABCDEF

	@@ ---- semantic：命中标记 ⇒ rdHB=0，仅宽度窗口被写 ----
	@@! inputs: kind=sc sym=A1 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D resv=same
	__PT_SC_LD	3, sc.b.nn, lr.b.nn, rd2, A1, 0x0123456789ABCDEF, 0xDEADBEEFCAFEF00D, 0x0000000000000000, 0x0D23456789ABCDEF

	@@ ---- semantic：sc 写回同值 ⇒ 成功且字节不变 ----
	@@! inputs: kind=sc sym=A2 k=0 init=0xFEDCBA9876543210 src=load resv=same
	__PT_SC_LOADED	4, sc.b.nn, lr.b.nn, rd2, A2, 0xFEDCBA9876543210, 0xFEDCBA9876543210

	@@ ---- semantic：标记在 A、sc 指向 B（不同 8 B 字）⇒ 失败且都不写 ----
	@@! inputs: kind=sc@B sym=A3/B3 k=0 init=0x0123456789ABCDEF/0x0F1E2D3C4B5A6978 resv=A
	__PT_SC_LD2	5, sc.b.nn, lr.b.nn, rd2, A3, B3, 0x0123456789ABCDEF, 0x0F1E2D3C4B5A6978, 0xDEADBEEFCAFEF00D, 0x0123456789ABCDEF, 0x0F1E2D3C4B5A6978

	@@ ---- semantic：lr A 后 lr B ⇒ A 的标记被清，sc A 失败 ----
	@@! inputs: kind=sc@A sym=A4/B4 k=0 init=0x0123456789ABCDEF resv=other
	__PT_SC_LD2L	6, sc.b.nn, lr.b.nn, rd2, A4, B4, rb3, 0x0123456789ABCDEF, 0xFEDCBA9876543210, 0xDEADBEEFCAFEF00D, 0x0123456789ABCDEF

	@@ ---- semantic：sc 成功后标记已消费 ⇒ 第二次 sc 失败，保留首次写 ----
	@@! inputs: kind=sc;sc sym=A5 k=0 init=0x0123456789ABCDEF src=0x5A5A5A5A5A5A5A5A,0xDEADBEEFCAFEF00D
	__PT_SC_2SC	7, 6, sc.b.nn, lr.b.nn, rd2, A5, 0x0123456789ABCDEF, 0x5A5A5A5A5A5A5A5A, 0xDEADBEEFCAFEF00D, 0x5A23456789ABCDEF

	@@ ---- semantic：失败的 sc 清全部标记 ⇒ 随后 sc 原地址仍失败 ----
	@@! inputs: kind=sc@B(fail);sc@A sym=A6/B6 k=0 init=0x0123456789ABCDEF
	__PT_SC_LD2_FAIL	8, sc.b.nn, lr.b.nn, rd2, A6, B6, 0x0123456789ABCDEF, 0x0F1E2D3C4B5A6978, 0xDEADBEEFCAFEF00D, 0x0123456789ABCDEF

	@@ ---- boundary：全 1 源/拍 ⇒ 成功且仍全 1 ----
	@@! inputs: kind=sc sym=A7 k=0 init=all1 src=all1
	__PT_SC_LD	9, sc.b.nn, lr.b.nn, rd2, A7, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ ---- boundary：零源 ⇒ 仅宽度窗口清零 ----
	@@! inputs: kind=sc sym=A8 k=0 init=0x0123456789ABCDEF src=0
	__PT_SC_LD	10, sc.b.nn, lr.b.nn, rd2, A8, 0x0123456789ABCDEF, 0, 0x0000000000000000, 0x0023456789ABCDEF

	@@ ---- boundary：源高位在宽度外 ⇒ 只并低 8w 位 ----
	@@! inputs: kind=sc sym=A9 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D
	__PT_SC_LD	11, sc.b.nn, lr.b.nn, rd2, A9, 0x0123456789ABCDEF, 0xDEADBEEFCAFEF00D, 0x0000000000000000, 0x0D23456789ABCDEF

	@@ ---- boundary：窗口贴 8 B 字尾的合并写入 ----
	@@! inputs: kind=sc sym=A10 k=7 init=0xFEDCBA9876543210 src=0x5A5A5A5A5A5A5A5A
	__PT_SC_LD	12, sc.b.nn, lr.b.nn, rd2, A10, 0xFEDCBA9876543210, 0x5A5A5A5A5A5A5A5A, 0x0000000000000000, 0xFEDCBA987654325A, 7

	@@ ---- boundary：数据区末拍的 sc（地址上界） ----
	@@! inputs: kind=sc sym=L k=0 init=0x0F1E2D3C4B5A6978 src=0xDEADBEEFCAFEF00D
	__PT_SC_LD	13, sc.b.nn, lr.b.nn, rd2, L, 0x0F1E2D3C4B5A6978, 0xDEADBEEFCAFEF00D, 0x0000000000000000, 0x0D1E2D3C4B5A6978

	@@ ---- overlap：rdHB == rdHC（源=结果）⇒ 源先读、结果后写 ----
	@@! inputs: kind=sc(rd5,rd5) sym=A11 k=0 init=0x0123456789ABCDEF src=0x5A5A5A5A5A5A5A5A
	__PT_SC_LD	14, sc.b.nn, lr.b.nn, rd5, A11, 0x0123456789ABCDEF, 0x5A5A5A5A5A5A5A5A, 0x0000000000000000, 0x5A23456789ABCDEF

	@@ ---- overlap：rdHB == rdHC 且无标记 ⇒ 失败且不写 ----
	@@! inputs: kind=sc(rd5,rd5) sym=A12 k=0 init=0x0123456789ABCDEF resv=none
	@@ 清保留标记：lr SCR 后 sc SCR（成功消费，SCR 写 0）
	__PT_SC_NORESV	15, sc.b.nn, lr.b.nn, rd5, A12, 0x0123456789ABCDEF, 0xDEADBEEFCAFEF00D, 0x0123456789ABCDEF

	@@ ---- semantic：另一对齐偏移的 sc 合并位置 ----
	@@! inputs: kind=sc sym=A13 k=1 init=0xFEDCBA9876543210 src=0xDEADBEEFCAFEF00D
	__PT_SC_LD	16, sc.b.nn, lr.b.nn, rd2, A13, 0xFEDCBA9876543210, 0xDEADBEEFCAFEF00D, 0x0000000000000000, 0xFE0DBA9876543210, 1

	@@ ---- 保留粒度（用户裁定 2026-11-14）：键 = 精确地址 + 访问宽度 ----
	@@ spec/SimRISC-12 §1「保留机制」：清除事件只列「另一 hart 对同一精确地址、相同访问宽度的
	@@   store」「本 hart 另一条 lr」「异常或中断进入」「sc 自身」⇒ 同 hart 的普通 store 不清；
	@@   不同地址 / 不同宽度不匹配。点 17-19 因此**必须成功（0）**。

	@@ ---- 粒度：同字异址 —— lr.b[A14] 后写 [A14+1]（同 8 B 字、不同精确地址）⇒ 标记仍在 ----
	@@! inputs: kind=lr.b;st.b@A14+1;sc.b@A14 sym=A14 k=0 init=0x0123456789ABCDEF src=0x5A
	@@ reload=0：rb3 仍指向该拍（中间是普通 store 例）
	@@ 只改 A14+1（byte1）：01 AA 45 67 89 AB CD EF
	__PT_SC_STORE_PREP	17, sc.b.nn, lr.b.nn, rd2, A14, 0x0123456789ABCDEF, st.b, 0xAA, 1, 0x5A5A5A5A5A5A5A5A, 0x5AAA456789ABCDEF

	@@ ---- 粒度：同址异宽 —— lr.b[A15] 后 st.t[A15]（同地址、宽度 4 ≠ 1）⇒ 标记仍在 ----
	@@! inputs: kind=lr.b;st.t@A15;sc.b@A15 sym=A15 k=0 init=0x0123456789ABCDEF src=0x5A
	@@ reload=0：rb3 仍指向该拍（中间是普通 store 例）
	@@ .t 覆写 byte0-3：DE AD BE EF 89 AB CD EF
	__PT_SC_STORE_PREP	18, sc.b.nn, lr.b.nn, rd2, A15, 0x0123456789ABCDEF, st.t, 0xDEADBEEF, 0, 0x5A5A5A5A5A5A5A5A, 0x5AADBEEF89ABCDEF

	@@ ---- 粒度：同址同宽同 hart 写 —— lr.b[A16] 后 st.b[A16]（仅「另一 hart」才清）⇒ 标记仍在 ----
	@@! inputs: kind=lr.b;st.b@A16;sc.b@A16 sym=A16 k=0 init=0x0123456789ABCDEF src=0x5A
	@@ reload=0：rb3 仍指向该拍（中间是普通 store 例）
	@@ 同 hart、同精确地址、同宽度：77 23 45 67 89 AB CD EF
	__PT_SC_STORE_PREP	19, sc.b.nn, lr.b.nn, rd2, A16, 0x0123456789ABCDEF, st.b, 0x77, 0, 0x5A5A5A5A5A5A5A5A, 0x5A23456789ABCDEF

	@@ ---- 粒度：本 hart 另一条 lr 清旧标记 —— lr[B0] → lr[B1] → sc[B0] ⇒ 失败 ----
	@@! inputs: kind=lr.b@B0;lr.b@B1;sc.b@B0 sym=B0/B1 k=0 init=0x1122334455667788/0xFEDCBA9876543210
	__PT_SC_LD2L	20, sc.b.nn, lr.b.nn, rd2, B0, B1, rb4, 0x1122334455667788, 0xFEDCBA9876543210, 0x5A5A5A5A5A5A5A5A, 0x1122334455667788

	@@ ---- 粒度：sc 自身消费标记 —— lr[B2] → sc（0）→ 再 sc（1），内存保留首次写 ----
	@@! inputs: kind=lr.b;sc.b;sc.b sym=B2 k=0 init=0x0F1E2D3C4B5A6978 src=0x5A,0x99
	@@ reload=0：rb3 仍指向该拍（中间是普通 store 例）
	__PT_SC_2SC_SELF	21, sc.b.nn, lr.b.nn, rd2, B2, 0x0F1E2D3C4B5A6978, 0x5A5A5A5A5A5A5A5A, 0x9999999999999999, 0x5A1E2D3C4B5A6978

	@@ ---- 异常进入（`ISS-443`）：四路径后 sc 必失败（spec/SimRISC-12 §1）----
	@@ 落点由 `.org` 钉在 .text 的 0x3000/0x3100/0x3200/0x3300；hmon 返回槽指向落点。
	@@ 期望全为 1（清除事件），拍保持初值（失败不写内存）。

	@@ 点 22：MALIGN —— lr.b[B7] → ld.o @TEST_DATA+0x7f1（未按 8 B 对齐）→ sc.b[B7]
	@@! inputs: kind=lr.b;ld.o@LMAL;sc.b sym=B7 k=0 init=0x0F1E2D3C4B5A6978 src=0x5A
	__PT_SC_EXC_ENTRY	22, sc.b.nn, lr.b.nn, rd2, B7, 0x0F1E2D3C4B5A6978, 0x5A, malign, 0x3000, LMAL, 0

	@@ 点 23：CFXMEM —— lr.b[B8] → ld.o @0 → sc.b[B8]
	@@! inputs: kind=lr.b;ld.o@0;sc.b sym=B8 k=0 init=0x1122334455667788 src=0x5B
	__PT_SC_EXC_ENTRY	23, sc.b.nn, lr.b.nn, rd2, B8, 0x1122334455667788, 0x5B, mem, 0x3100, 0, 0

	@@ 点 24：ILLI —— lr.b[B9] → 原始编码 sc.b 且 rdHB=rd0 → sc.b[B9]
	@@! inputs: kind=lr.b;sc.b(rd0);sc.b sym=B9 k=0 init=0xFEDCBA9876543210 src=0x5C
	__PT_SC_EXC_ENTRY	24, sc.b.nn, lr.b.nn, rd2, B9, 0xFEDCBA9876543210, 0x5C, illi, 0x3200, 0, 0x474C0083

	@@ 点 25：CFXTRAP —— lr.b[B10] → trap cfx_hmon,0 → sc.b[B10]
	@@! inputs: kind=lr.b;trap;sc.b sym=B10 k=0 init=0x0123456789ABCDEF src=0x5D
	__PT_SC_EXC_ENTRY	25, sc.b.nn, lr.b.nn, rd2, B10, 0x0123456789ABCDEF, 0x5D, trap, 0x3300, 0, 0

	@@ ---- 粒度：键的宽度维（同址异宽）—— lr.b[B11] 后 sc.t[B11] ⇒ 键不匹配、失败 ----
	@@! inputs: kind=lr.b;sc.t sym=B11 k=0 init=0x0F1E2D3C4B5A6978 src=0xDEADBEEF
	__PT_SC_LR_WIDTH	26, sc.t.nn, lr.b.nn, rd2, B11, 0x0F1E2D3C4B5A6978, 0xDEADBEEF

	__TEST_END

	@@ ---- fault（同镜像故障链；原始编码）----
	@@ fault 27：sc 的 rdHB = rd0 ⇒ ILLI（成功/失败结果不可丢弃，原始编码）
	TEST_FAULT_CF1 27, rb3, A0, ILLI, 0x474C0083

	__TEST_SECTIONS
