@@ dadao_test.inc — DADAO 裸机测试框架的汇编辅助宏（m13-integ-004）。
@@
@@ 对应 riscv-tests 的 env/p/riscv_test.h 中的 RVTEST_* 与 test_macros.h：
@@   * 启动：生成的测试把 `_start` 放在 profile 的 RAM 入口；Tiny BootROM /
@@     链接器负责设置 SP，测试体不建栈、不依赖 C 运行时。
@@   * 退出：semihosting SYS_EXIT（trap cfx0, 0x3FF00），参数块
@@     {ADP_Stopped_ApplicationExit, code}；code 0 = PASS，0x40|n = 第 n 条
@@     检查失败（spec/Machine-v5 §7.1；ADR-0020 D8）。
@@   * 签名区：固定 RAM 区（SIG_BASE），每条检查把观测值写成一个 octa；
@@     测试结束把签名区按 16 进制逐行打印到 semihosting 控制台，供宿主比对
@@     （riscv-tests `begin_signature`/`end_signature` + `tohost` 的等价物）。
@@
@@ 常量由生成器通过 `--defsym` 注入：ENTRY / SIG_BASE / BUF_BASE /
@@ TBL_BASE / STR_BASE / EXIT_BLOCK。本文件只定义指令宏，不写机器地址。
@@
@@ 编译：llvm-mc --triple=dadao-unknown-elf -I tests/shared/asm \
@@        -I tests/riscv-tests/framework --defsym ... -filetype=obj

	.include "machine.inc"

@@ LOAD_RD rd, imm64 —— 用 4 条 wyde 位置指令把 64 位常量装入 RD。
.macro LOAD_RD rd, val
  set.zw  \rd, wp0, ((\val) & 0xFFFF)
  or.w    \rd, wp1, (((\val) >> 16) & 0xFFFF)
  or.w    \rd, wp2, (((\val) >> 32) & 0xFFFF)
  or.w    \rd, wp3, (((\val) >> 48) & 0xFFFF)
.endm
