/*
 * cfx15.lds — `tests/arch/hart/cfx15.S` 的链接布局（`m16-chipyard-021`）。
 *
 *   ENTRY + 0x0000  .text   探针代码（≤ 16 KiB）
 *   ENTRY + 0x4000  .data   phase / sig_bytes
 *   ENTRY + 0x5000  签名缓冲（SIG_BUF；64 槽 = 512 B）
 *   ENTRY + 0x5800  SYS_EXIT 参数块（EXITB）
 *
 * `--defsym TMODE=<0|2|3>` 在链接期选目标运行模式（0 = umon/U、2 = smon/S、
 * 3 = hmon/H）；同一份 `.S` 链接出三个镜像，case 定义只有一份。
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

  . = 0xffffff014000;
  .data : {
    *(.data)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "cfx15: .text 越过 16 KiB 窗口")
  ASSERT(SIZEOF(.data) <= 0x1000, "cfx15: .data 越过 4 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
