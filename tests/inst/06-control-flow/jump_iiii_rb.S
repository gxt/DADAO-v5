@@ jump_iiii_rb.S — jump [rb0, imms26]（iiii/rb, opc 0x70）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §2`）；册目录 `tests/inst/06-control-flow/`
@@ id：jump_iiii_rb　形式：iiii（rb）　opc：0x70　mask：0xFF000000　value：0x70000000
@@ 语义：无条件跳转；目标 = rb0 + (SX(imms24) << 2)（64 位计算，结果写回 rb0，取低 48 位
@@   为下一条地址）；iiii 形式的基址**必须**是 rb0（汇编期校验），故 `[rb0, off]` 即相对跳转
@@   立即数在汇编层按**字节**书写（`imms26`），编码层 `imms24 = 字节 >> 2`；±32 MiB
@@ 合法性：`contracts/legality_rules.yaml` 对 jump 无 active 静态规则；目标恒 4 字节对齐
@@   （`imms24 << 2`）⇒ 不会触发 IALIGN；±32 MiB 远超 Tiny（8 MiB）SRAM ⇒ 越界目标
@@   取指 ⇒ CFXMEM（边界/故障例）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：iiii = opc | imms24[23:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（本文件不需要数据区）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 1 / semantic 1 / overlap 1 / boundary 3（链例 6 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：跳转**距离与落点地址**用 `.org` 钉住的槽位 + `__LAND_IP`（`aip.si` 取 IP）核，
@@   期望写 `ENTRY + <字面偏移>`（llvm-mc 只折装绝对常量，标签差不进立即数）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x70000002（imms24 = 2 ⇒ +8）⇒ 跳过紧随的 4 B
	set.rd	rd24, 0
	.dd.t32	0x70000002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ ---- semantic ----
	@@ 跳到标号：落点置标记 1，再跳回检查点（无条件跳转必生效）
	set.rd	rd24, 0
	jump	[rb0, __s_t]
	jump	[rb0, __s_never]
__s_t:
	set.rd	rd24, 1
	jump	[rb0, __s_ck]
__s_never:
	set.rd	rd24, 0xBAD
__s_ck:
	__CHECK_RD          2, rd24, 1

	@@ ---- overlap ----
	@@ 目标 = 顺序路径的下一条（+4）：跳转目标与「不跳的落点」重合 ⇒ 后续指令恰好执行一次
	set.rd	rd24, 0
	jump	[rb0, 4]
	add.si	rd24, 1
	__CHECK_RD          3, rd24, 1

	@@ ---- boundary：跳转距离（`.org` 钉住槽位；零填充只被 jump 跨过）----
	set.rd	rd24, 0
	jump	[rb0, __slot_fwd]
	.org	0x800
__l_back:                                @@ 0x800：后向 -0x420 的落点（槽 0xC20）
	__PREP_LAND_JUMP	__ck5
	.org	0xC00
__slot_fwd:                              @@ 0xC00：+0x800 ⇒ 落点 0x1400
	jump	[rb0, 0x800]
	.org	0xC20
__slot_back:                             @@ 0xC20：-0x420 ⇒ 落点 0x800
	jump	[rb0, -0x420]
	.org	0xC40
__slot_big:                              @@ 0xC40：+0xC60 ⇒ 落点 0x18A0（.text 近尾）
	jump	[rb0, 0xC60]
	.org	0x1400
__l_fwd:                                 @@ 0x1400：前向落点
	__PREP_LAND_JUMP	__ck4
	.org	0x18A0
__l_big:                                 @@ 0x18A0：大距离落点
	__PREP_LAND_JUMP	__ck6
	.org	0x1A00
__ck4:
	__CHECK_RD          4, rd24, (ENTRY + 0x1400)
	jump	[rb0, __slot_back]
__ck5:
	__CHECK_RD          5, rd24, (ENTRY + 0x800)
	jump	[rb0, __slot_big]
__ck6:
	__CHECK_RD          6, rd24, (ENTRY + 0x18A0)

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ 目标落在 SRAM 之下（imms24 = -0x40000 ⇒ rb0 - 0x100000）⇒ 取指 CFXMEM
	TEST_FAULT_CF       7, CFXMEM, 0x70FC0000

	__TEST_SECTIONS
