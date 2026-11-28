/*
 * swym.lds — `tools/chipyard/swym/swym.S` 的链接布局（`m19-chipyard-003`）。
 *
 * 与 `tools/chipyard/excp/app.lds` 同一套 Kaiwu-Tiny 约定：ELF 只有一个
 * PT_LOAD 段，`e_entry` = 固定应用入口，BootROM/hmon 固件来自固定镜像。
 * `.text` 必须避开 `SYS_EXIT` 参数块（`ENTRY + 0x6000`）。
 *
 * ILLI 例的返回槽由 `aip.si → add.si(+16) → st.o(+0xF8) → 原始编码字 → 回落点`
 * 现场写入；回落点必须是 `aip` 指令 + 16 B，手写立即数由链接器回读校验。
 */

ENTRY_ADDR = 0xffffff010100;

ENTRY(_start)

SECTIONS
{
  . = ENTRY_ADDR;

  .text : {
    *(.text .text.*)
    *(.rodata .rodata.*)
  }

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(_start == ENTRY_ADDR, "swym: entry must be the fixed Tiny entry")
  ASSERT(sw_resume0 == sw_aip0 + 16, "swym: ILLI 1 resume must be aip + 16")
  ASSERT(sw_resume1 == sw_aip1 + 16, "swym: ILLI 2 resume must be aip + 16")
  ASSERT(sw_resume2 == sw_aip2 + 16, "swym: ILLI 3 resume must be aip + 16")
  ASSERT(sw_illi0 == sw_aip0 + 12, "swym: ILLI 1 word must be 4 B at aip + 12")
  ASSERT(sw_illi1 == sw_aip1 + 12, "swym: ILLI 2 word must be 4 B at aip + 12")
  ASSERT(sw_illi2 == sw_aip2 + 12, "swym: ILLI 3 word must be 4 B at aip + 12")
}
