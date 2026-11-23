/*
 * tests/arch/power/power_rtl.lds — cfx_power RTL 探针（chipyard WumingVastConfig）
 * 的链接布局（m16-testcases-016）。
 *
 * 与 `tests/inst` / `tests/arch/umon/fence_rtl.lds` 同一套固定地址：
 * `tests/inst/macros/inst_test.inc` 的 `ENTRY` / `TEST_BUF` / `TEST_EXITB`
 * 都按 `0xffffff010100` 基址展开；`+loadmem` 只把 PT_LOAD 段装进 RAM 窗口。
 *
 *   ENTRY + 0x0000  .text        探针主体（`gen_power_rtl.py` 生成，禁止手改）
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

  ASSERT(SIZEOF(.text) <= 0x4000, "power_rtl: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
