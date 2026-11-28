/*
 * mode_entry.lds — `tests/arch/umon/mode_entry.S` 的链接布局（`m16-chipyard-020`）。
 *
 * 与 019 的 `cfx02_regs.lds` 同一套地址：探针从 Tiny 固定应用入口
 * `ENTRY = 0xffff_ff00_2000` 开始（`spec/Kaiwu §6.2` 的 power 段直接跳到这里），
 * 代码 + 私有数据槽装进前 16 KiB。签名缓冲与 SYS_EXIT 参数块是主 SRAM 头区的
 * 固定区（`SIGNATURE` / `EXIT_BLOCK`），运行期写入（不进镜像）。
 *
 *   ENTRY + 0x0000  .text   探针代码（≤ 16 KiB）
 *   ENTRY + 0x4000  .data   mode_word / exp_ip / phase（24 B）
 *   SIGNATURE       签名缓冲（`MAIN_SRAM_BASE + 0x1000`，32 槽 = 256 B）
 *   EXIT_BLOCK      SYS_EXIT 参数块（`MAIN_SRAM_BASE + 0x0030`）
 *
 * `--defsym TMODE=<0|2|3>` 在链接期给定目标运行模式（0 = umon/U、2 = smon/S、
 * 3 = hmon/H）；同一份 `.S` 链接出三个镜像，case 定义只有一份。
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

  . = 0xffffff006000;
  .data : {
    *(.data)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "mode_entry: .text 越过 16 KiB 窗口")
  ASSERT(SIZEOF(.data) <= 0x1000, "mode_entry: .data 越过 4 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
