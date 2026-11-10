@@ tiny_crt.S — Machine-v5-Tiny 应用启动代码（crt，m12-chipyard-007）
@@
@@ 规范：spec/Machine-v5 §6「装载语义 — Machine-v5-Tiny」：
@@   * `crt`（启动代码）与测试程序一起链接成同一个应用 ELF，整体落在 SRAM；
@@   * 入口 raw 与 ELF 统一 0xffff_ff01_0100（即 crt 入口）；
@@   * `SP = 0xffff_ff7e_ff00` 由 crt 在入口设置。
@@
@@ BootROM 侧的 power stub 在 hmon 移交返回后直接跳到该固定入口（§6.2 第 8 步），
@@ 不再替应用设 SP；SP 的唯一设置点是这里。
@@
@@ 链接约定：crt.o 必须排在应用目标文件之前（同一条 ld.lld 命令行），
@@ 应用代码紧随 crt 的 `.text` 之后顺序落位；crt 设置 SP 后顺序落入应用。
@@ 入口 `_start` 即 ELF `e_entry`，也是固定入口 `ENTRY`。

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	.text
	.globl	_start

_start:
	LOAD_ADDR rb1, SP		@@ rb1 = SP（应用栈顶）
	@@ 顺序落入随后链接的应用代码（同段、4 字节对齐、无填充）
