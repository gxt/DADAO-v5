/*
 * tests/arch/umon/fence_rtl.lds — fence RTL 探针（chipyard WumingVastConfig）的
 * 链接布局（m16-testcases-012）。
 *
 * 与 `tests/inst` / `tests/arch/umon/cfx02_regs.lds` 同一套固定地址：
 * `tests/inst/macros/inst_test.inc` 的 `ENTRY` / `TEST_BUF` / `TEST_EXITB`
 * 都按 `0xffffff010100` 基址展开；`+loadmem` 只把 PT_LOAD 段装进 RAM 窗口。
 *
 *   ENTRY + 0x0000  .text        探针主体（生成为 `gen_fence_rtl.py` 的输出）
 *   ENTRY + 0x7000  签名区（运行时写，不进镜像）
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

  ASSERT(SIZEOF(.text) <= 0x4000, "fence_rtl: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
