@@ br.eq_rrii_rd.S — br.eq {rdHA, rdHB}?, [rb0, imms14]（rrii/rd, opc 0x6E）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §1`）；册目录 `tests/inst/06-control-flow/`
@@ id：br.eq_rrii_rd　形式：rrii（rd）　opc：0x6E　mask：0xFF000000　value：0x6E000000
@@ 语义：rdHA == rdHB（**整 64 位**相等）⇒ 跳转；目标 = rb0 + (SX(imms12) << 2)
@@   （64 位计算，结果写回 rb0，取低 48 位为下一条地址）；不成立 ⇒ 顺序执行 rb0 + 4
@@ 合法性：`contracts/legality_rules.yaml` 对 br.eq 无 active 静态规则；源可为 rd0
@@   （硬连零、读出 0）；目标恒 4 字节对齐（`imms12 << 2`）⇒ 不会触发 IALIGN；
@@   imms12 = ±8 KiB 上限 ⇒ **够不到** Tiny（8 MiB）的 SRAM 边界，故不可取指的目标
@@   只能落在 SRAM 内的非代码区（零字 ⇒ UNDI，见故障例）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrii = opc | rdha[23:18] | rdhb[17:12] | imms12[11:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd`/`set.rb` 拼条件寄存器；**不使用数据区**）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / overlap 2 / boundary 3（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：条件寄存器用 `set.rd` 拼常量（被测分支不参与造初值）、期望内联；跳转/不跳由
@@   rd24 的 1/0 标记判（`TEST_BR2`）；跳转**距离与落点地址**用 `.org` 钉住的槽位 +
@@   `__LAND_IP`（`aip.si` 取 IP）核，期望写 `ENTRY + <字面偏移>`

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x6E042002（rd1 == rd2 == 0）⇒ 条件成立 ⇒ 跳过紧随的 4 B
	set.rd	rd1, 0
	set.rd	rd2, 0
	set.rd	rd24, 0
	.dd.t32	0x6E042002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ 点 2：字段边界（rdha = rdhb = rd63，最大寄存器号）+ 同等成立
	set.rd	rd63, 0x42
	set.rd	rd24, 0
	.dd.t32	0x6EFFF002
	add.si	rd24, 1
	__CHECK_RD          2, rd24, 0

	@@ ---- semantic ----
	@@ 相等 ⇒ 跳转（标记 1）
	TEST_BR2            3, br.eq, rd5, 0x0000000000000042, rd6, 0x0000000000000042, 1

	@@ 不等 ⇒ 不跳（标记 0）
	TEST_BR2            4, br.eq, rd5, 0x0000000000000042, rd6, 0x0000000000000099, 0

	@@ 两源都是 rd0（硬连零）⇒ 0 == 0 成立 ⇒ 跳转
	TEST_BR2            5, br.eq, rd0, 0x0000000000000000, rd0, 0x0000000000000000, 1

	@@ rd0 与非零 ⇒ 不成立
	TEST_BR2            6, br.eq, rd0, 0x0000000000000000, rd6, 0xDEADBEEFCAFEF00D, 0

	@@ 整 64 位比较：低 32 位相同、高 32 位不同 ⇒ 不等（只比低半会误判「相等」）
	TEST_BR2            7, br.eq, rd5, 0x0000000000000042, rd6, 0x8000000000000042, 0

	@@ ---- overlap ----
	@@ 两源同名（同一寄存器与自己比）⇒ 恒成立
	TEST_BR2            8, br.eq, rd5, 0x0123456789ABCDEF, rd5, 0x0000000000000000, 1

	@@ 两源都是 rd0：另点复核（rd0 只读、读出恒 0）
	TEST_BR2            9, br.eq, rd0, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 1

	@@ ---- boundary：跳转距离（`.org` 钉住槽位；零填充只被 jump/分支跨过）----
	set.rd	rd5, 0x42
	set.rd	rd6, 0x42
	set.rd	rd24, 0
	jump	[rb0, __d_f1]
	.org	0x800
__d_b1:                                  @@ 0x800：后向字面量分支的落点
	__PREP_LAND_JUMP	__d_ck_b
	.org	0xC00
__d_f1:                                  @@ 0xC00：+0x800 ⇒ 落点 0x1400
	br.eq	{rd5, rd6}?, [rb0, 0x800]
	add.si	rd24, 1
	.org	0xC20
__d_b2:                                  @@ 0xC20：-0x420 ⇒ 落点 0x800
	br.eq	{rd5, rd6}?, [rb0, -0x420]
	add.si	rd24, 1
	.org	0xC40
__d_f3:                                  @@ 0xC40：+0xEC0 ⇒ 落点 0x1B00（.text 近尾）
	br.eq	{rd5, rd6}?, [rb0, 0xEC0]
	add.si	rd24, 1
	.org	0x1400
__d_l1:                                  @@ 0x1400：第一例落点
	__PREP_LAND_JUMP	__d_ck_f
__d_ck_f:
	__CHECK_RD         10, rd24, (ENTRY + 0x1400)
	jump	[rb0, __d_b2]
__d_ck_b:
	__CHECK_RD         11, rd24, (ENTRY + 0x800)
	jump	[rb0, __d_f3]
	.org	0x1B00
__d_l3:                                  @@ 0x1B00：大距离落点
	__PREP_LAND_JUMP	__d_ck_l
	.org	0x1B20
__d_ck_l:
	__CHECK_RD         12, rd24, (ENTRY + 0x1B00)

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ 目标落在紧随的保留编码字（零字，非代码）⇒ 取指读到保留编码 ⇒ UNDI
	TEST_FAULT_BR2      13, br.eq, rd5, 0x42, rd6, 0x42, UNDI, __rsvd13
__rsvd13:
	.dd.t32	0

	__TEST_SECTIONS
