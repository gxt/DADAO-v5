/*
 * cfx_hmon_tiny.lds — Kaiwu-Tiny 最小 cfx_hmon 段（m12-chipyard-007；
 * M19 数据页迁移见 m19-testcases-005）
 *
 * 规范：spec/Kaiwu §6.2「镜像布局」。hmon 段链接在 hmon SRAM 起始
 * 0x0fff_0000_0000（镜像偏移 0x0800），段首即 hmon 入口 = 异常向量初值
 * （DADAO-13 §1）。hmon SRAM 的 8 KiB 分区：代码 0x0000–0x0BFF（≤3 KiB，
 * = power 复制的源段）、数据 0x0C00–0x0CFF、栈 0x0D00–0x1FFF；本段只是
 * 代码区，上限 3 KiB（校验阈值，超限即构建失败）。
 */

ENTRY(_start)

MEMORY
{
  /* 代码区（spec/Kaiwu §6.2）：3 KiB。数据/栈不在本段内（SRAM 初值 0）。 */
  HMON (rx) : ORIGIN = 0x0fff00000000, LENGTH = 3K
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

  ASSERT(SIZEOF(.text) <= LENGTH(HMON), "tiny hmon segment exceeds its 3 KiB code region")
  /* 数据页从 hmon SRAM + 0x0C00 起（spec/Kaiwu §6.2）；power 只复制代码区
   * （表项 size），数据页必须保持在源段之外、由 SRAM 初值 0 提供。 */
  ASSERT(SIZEOF(.text) <= 0xC00,
         "tiny hmon: code must stay below the 0x0C00 data page")
}
