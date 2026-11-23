@@ tests/arch/umon/mode_regs.body.S — `arch-umon-011` 的测试 body（m16-testcases-015）
@@
@@ **代表迁移**：本文件只放「测什么」，运行模式环境在
@@ `tests/arch/common/env/{hmon,smon,umon}/env.S`（进入模式、栈、异常向量、退出、
@@ 签名区）。同一份 body 在三种模式下各跑一次，签名流（除无模式相关槽外）必须
@@ 逐槽一致；实际运行模式由驱动从 QEMU `-d cpu` 的 `MODE:` 现场核对，不由 body
@@ 自述。
@@
@@ 观测面（只读 cfx_umon 自身寄存器，两轴权限的 cfx 轴被「自身」绕过，
@@ 因此与运行模式无关；期望值由驱动现场从 `spec/` + `.tao/contracts/` 派生）：
@@
@@   槽 0 `cfx_umon.cg6.rc0` 写 0x0123456789ABCDEF 后回读（暂存寄存器 RW，
@@         `DADAO-12 §3.7`）
@@   槽 1 `cfx_umon.cg8.rc1` global_cfx_intr_mask 初值全 1
@@         （`contract-see` §3：`cfx_intr_mask`/`global_cfx_intr_mask` 初值全 1）
@@   槽 2 `cfx_umon.cg4.rc0` cfx_id（= cfxha，`DADAO-12 §3.5` 通用寄存器 + §1
@@         cfxha 表：cfx_umon = 0）——与交付方式（是否经 trap 进入）无关
@@   槽 3 `cfx_umon.cg6.rc1` 第二个暂存寄存器写后回读（`§3.5`：暂存寄存器至少 2）
@@         —— m16-testcases-017 起替换原来读入口 trap 现场的两槽（交付改为
@@         hmon 直接跳转后没有 trap，那两个值是交付相关量）
@@   槽 4..7 `cfx_umon.cg7.rc0..3` space[0] 的 desc/start/size/attr
@@         （`cfx0` 没有内部空间 ⇒ 全 0；`spec/Kaiwu §1`、`DADAO-12 §3.8`）
@@
@@ body 结束时跳到环境给的退出例程（`rb6`）；签名区由环境定义
@@ （`ENV_SIG_BUF` / `ENV_SIG_SLOTS`，驱动按 profile 传入）。

	.include "signature.inc"

	.section .bodycode,"ax",@progbits
	.globl	test_body
test_body:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS

	@@ 槽 0：暂存寄存器写后回读
	set.rd	rd6, 0x0123456789ABCDEF
	cfx2rc	cfx_umon, cg6, rc0, rd6
	cfx2rd	cfx_umon, cg6, rc0, rd5
	SIGUPD	rd5

	@@ 槽 1：global_cfx_intr_mask（初值全 1）
	cfx2rd	cfx_umon, cg8, rc1, rd5
	SIGUPD	rd5

	@@ 槽 2：cfx_id（cg4 rc0，= cfxha；`DADAO-12 §3.5`/§1 的 cfxha 表）
	cfx2rd	cfx_umon, cg4, rc0, rd5
	SIGUPD	rd5

	@@ 槽 3：第二个暂存寄存器 rc1 写后回读（cg6；个数至少 2，`DADAO-12 §3.5`）
	set.rd	rd6, 0xFEDCBA9876543210
	cfx2rc	cfx_umon, cg6, rc1, rd6
	cfx2rd	cfx_umon, cg6, rc1, rd5
	SIGUPD	rd5

	@@ 槽 4..7：cg7 space[0]（cfx0 无内部空间）
	cfx2rd	cfx_umon, cg7, rc0, rd5
	SIGUPD	rd5
	cfx2rd	cfx_umon, cg7, rc1, rd5
	SIGUPD	rd5
	cfx2rd	cfx_umon, cg7, rc2, rd5
	SIGUPD	rd5
	cfx2rd	cfx_umon, cg7, rc3, rd5
	SIGUPD	rd5

	@@ 收尾交给环境（rb6 = env_finish；签名输出与 SYS_EXIT 在 .envtail）
	jump	[rb6, rd0, 0]
