/*
 * prevcfx.lds — `tools/chipyard/excp/prevcfx.S` 的链接布局（`m16-chipyard-005`）。
 *
 * 与 `tests/ee-tiny/inst_tiny.lds` 同一套固定地址（同一宏层
 * `tests/inst/macros/inst_test.inc` 的 `.equ`：TEST_BUF / TEST_EXITB）。
 * 本文件只加一条 ASSERT：被 CFXESC 拦下的 `escape` 地址必须等于运行期
 * `aip.si` 取到的地址 + 8（`aip` 4 B + `add.si` 4 B ⇒ `escape` 在 aip+8），
 * 立即数是手写常量，由链接器**回读校验**，错一位即链接失败。
 *
 *   ENTRY + 0x0000  .text        主体（链例）
 *   ENTRY + 0x1B00  自建 hmon 入口
 *   ENTRY + 0x1C40  自建 cfx_power 入口
 *   ENTRY + 0x1E00  落点
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

  ASSERT(SIZEOF(.text) <= 0x4000, "prevcfx: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

ASSERT(prevcfx_escape == pad_aip + 8, "prevcfx: escape must be aip + 8")
