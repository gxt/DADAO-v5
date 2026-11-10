/*
 * hmon.lds — Machine-v5-Tiny 最小 hmon 段（m12-chipyard-007）
 *
 * 规范：spec/Machine-v5 §6.2「镜像布局」。hmon 段链接在 hmon SRAM 起始
 * 0x0fff_0000_0000（镜像偏移 0x2000），段首即 hmon 入口 = 异常向量初值
 * （DADAO-13 §1）；上限 8 KiB（校验阈值，超限即构建失败）。
 */

ENTRY(_start)

MEMORY
{
  HMON (rx) : ORIGIN = 0x0fff00000000, LENGTH = 8K
}

SECTIONS
{
  . = ORIGIN(HMON);

  .text : ALIGN(4) {
    *(.text .text.*)
    *(.rodata .rodata.*)
  } > HMON

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(SIZEOF(.text) <= LENGTH(HMON), "tiny hmon segment exceeds its 8 KiB budget")
  /* m13-integ-007: code starts at 0x00 and the data area starts at 0xD8;
   * power copies only the code region (table size), so the code must not
   * reach into the data slots. */
  ASSERT(SIZEOF(.text) <= 0xD8,
         "tiny hmon: code must fit below the 0xD8 data area")
}
