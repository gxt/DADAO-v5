/*
 * tests/arch/time/time_rtl.lds — cfx_time RTL 探针（chipyard WumingVastConfig）
 * 的链接布局（m16-chipyard-023）。
 *
 * 与 `tests/arch/hart/cfx15.lds` 同型，固定地址 + `+loadmem` 只装 PT_LOAD 段：
 *
 *   ENTRY + 0x0000  .text        探针主体（`time_rtl.S`）
 *   SIGNATURE      签名区（`MAIN_SRAM_BASE + 0x1000`，运行期写，不进镜像；SIG_BUF）
 *   EXIT_BLOCK     SYS_EXIT 参数块（`MAIN_SRAM_BASE + 0x0030`，运行期写；EXITB）
 */

ENTRY(_start)

PHDRS
{
  image PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0xffffff002000;

  .text : {
    *(.text*)
  } : image

  .data : {
    *(.data*)
  } : image

  ASSERT(SIZEOF(.text) + SIZEOF(.data) <= 0x3000,
         "time_rtl: .text+.data 越过 12 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
