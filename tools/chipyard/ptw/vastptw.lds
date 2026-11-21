/*
 * vastptw.lds — `tools/chipyard/ptw/vastptw.S` 的链接布局（`m16-chipyard-006`）。
 *
 * 与 `tests/ee-tiny/tests_inst_tiny.lds` 同一套固定地址（同一宏层
 * `tests/inst/macros/inst_test.inc` 的 `.equ`：TEST_BUF / TEST_EXITB）。本文件末尾的
 * ASSERT 把每个故障用例的「回落点相对 `aip.si` 的偏移」与「jump 相对 sub.o 的偏移」
 * 由**链接器回读校验**——手写立即数（4/16/24）错一位即链接失败。
 *
 *   ENTRY + 0x0000  .text        探针主体
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

  ASSERT(SIZEOF(.text) <= 0x4000, "vastptw: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* 数据类故障用例：aip → add.si → st.o → 故障 ld → 回落点 = aip + 16 */
ASSERT(d1_resume == d1_aip + 16, "vastptw: d1 resume must be aip + 16")
ASSERT(d3_resume == d3_aip + 16, "vastptw: d3 resume must be aip + 16")

/* 取指类故障用例：aip → add.si → st.o → sub.o → add.si → jump → 回落点 = aip + 24 */
ASSERT(d2_resume == d2_aip + 24, "vastptw: d2 resume must be aip + 24")
ASSERT(d4_resume == d4_aip + 24, "vastptw: d4 resume must be aip + 24")
ASSERT(d2_jump == d2_fault + 8, "vastptw: d2 jump must be the sub.o + 8 B")
ASSERT(d4_jump == d4_fault + 8, "vastptw: d4 jump must be the sub.o + 8 B")
