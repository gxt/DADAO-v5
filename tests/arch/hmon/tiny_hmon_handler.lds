/*
 * tiny_hmon_handler.lds — Machine-v5-Tiny 分派 hmon 段（m13-gem5-005）
 *
 * 规范：spec/Machine-v5 §6.2「镜像布局」。hmon 段链接在 hmon SRAM 起始
 * 0x0fff_0000_0000（镜像偏移 0x2000），段首即 hmon 入口 = 异常向量初值
 * （DADAO-13 §1）；上限 8 KiB（校验阈值，超限即构建失败）。
 */

ENTRY(hmon_entry)

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

  ASSERT(SIZEOF(.text) <= LENGTH(HMON), "tiny hmon dispatch segment exceeds its 8 KiB budget")
}
