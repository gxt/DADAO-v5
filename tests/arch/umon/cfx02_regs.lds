/*
 * cfx02_regs.lds — `tests/arch/umon/cfx02_regs.S` 的链接布局（`m16-chipyard-019`）。
 *
 * 与 `tests/ee-tiny/tests_inst_tiny.lds` 同一套固定地址（宏层
 * `tests/inst/macros/inst_test.inc` 的 `.equ`：TEST_BUF / TEST_EXITB）。末尾的
 * ASSERT 把每个故障例的「回落点相对 `aip.si` 的偏移」由**链接器回读校验**：
 * `aip.si`(4) + `add.si`(4) + `st.o`(4) + 故障指令(4) = 回落点 +16，手写 16 错
 * 一位即链接失败。
 *
 *   ENTRY + 0x0000  .text        探针主体
 *   ENTRY + 0x4000  .faultpad    `abort` 之外不使用（宏层预留）
 *   ENTRY + 0x7000  结果缓冲（运行时写，不进镜像）
 *   ENTRY + 0x7800  SYS_EXIT 参数块（运行时写，不进镜像）
 */

ENTRY(_start)

PHDRS
{
  image PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0xffffff010100;

  .text : {
    *(.text)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "cfx02_regs: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* 五个故障例：aip -> add.si -> st.o -> 故障指令 -> 回落点 = aip + 16；故障
 * 指令本身在 aip + 12。 */
ASSERT(f1_fault  == f1_aip + 12, "cfx02_regs: f1 fault instruction must be aip + 12")
ASSERT(f1_resume == f1_aip + 16, "cfx02_regs: f1 resume must be aip + 16")
ASSERT(f2_fault  == f2_aip + 12, "cfx02_regs: f2 fault instruction must be aip + 12")
ASSERT(f2_resume == f2_aip + 16, "cfx02_regs: f2 resume must be aip + 16")
ASSERT(f3_fault  == f3_aip + 12, "cfx02_regs: f3 fault instruction must be aip + 12")
ASSERT(f3_resume == f3_aip + 16, "cfx02_regs: f3 resume must be aip + 16")
ASSERT(f4_fault  == f4_aip + 12, "cfx02_regs: f4 fault instruction must be aip + 12")
ASSERT(f4_resume == f4_aip + 16, "cfx02_regs: f4 resume must be aip + 16")
ASSERT(f5_fault  == f5_aip + 12, "cfx02_regs: f5 fault instruction must be aip + 12")
ASSERT(f5_resume == f5_aip + 16, "cfx02_regs: f5 resume must be aip + 16")
