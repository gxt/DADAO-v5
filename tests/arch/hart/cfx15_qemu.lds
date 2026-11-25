/*
 * cfx15_qemu.lds — `cfx15.S` 的 QEMU（kaiwu-vast）链接布局
 * （`m16-testcases-013`）。
 *
 * QEMU `-kernel` 的 flat bin 从 `ENTRY = 0x0010_0000` 装入 PA RAM；同一份
 * `cfx15.S` 用 `--defsym ENTRY/SIG_BUF/EXITB` 覆盖 RTL 的内部 SRAM 地址：
 *
 *   ENTRY + 0x0000  .text   探针代码（≤ 16 KiB）
 *   ENTRY + 0x4000  .data   sig_bytes
 *   ENTRY + 0x5000  SIG_BUF（001 = 89 槽 / 002 = 40 槽；缓冲 96 槽 = 768 B）
 *   ENTRY + 0x5800  EXITB
 */

ENTRY(_start)

PHDRS
{
  image PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0x00100000;

  .text : {
    *(.text)
  } : image

  . = 0x00104000;
  .data : {
    *(.data)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "cfx15 qemu: .text 越过 16 KiB 窗口")
  ASSERT(SIZEOF(.data) <= 0x1000, "cfx15 qemu: .data 越过 4 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
