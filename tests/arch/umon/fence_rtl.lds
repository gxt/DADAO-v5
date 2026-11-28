/*
 * tests/arch/umon/fence_rtl.lds — fence RTL 探针（chipyard WumingVastConfig）的
 * 链接布局（m16-testcases-012）。
 *
 * 与 `tests/inst` / `tests/arch/umon/cfx02_regs.lds` 同一套固定地址：
 * `tests/inst/macros/inst_test.inc` 的 `ENTRY` / `TEST_BUF` / `TEST_EXITB`
 * 都按新 Tiny 几何（`spec/Kaiwu §6.2`：`ENTRY = MAIN_SRAM_BASE + 0x2000`、
 * `TEST_BUF = SIGNATURE`、`TEST_EXITB = EXIT_BLOCK`）展开；`+loadmem` 只把
 * PT_LOAD 段装进 RAM 窗口。
 *
 *   ENTRY + 0x0000  .text        探针主体（生成为 `gen_fence_rtl.py` 的输出）
 *   SIGNATURE       签名区（`MAIN_SRAM_BASE + 0x1000`，运行期写，不进镜像）
 *   EXIT_BLOCK      SYS_EXIT 参数块（`MAIN_SRAM_BASE + 0x0030`，运行期写）
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
    *(.text)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "fence_rtl: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
