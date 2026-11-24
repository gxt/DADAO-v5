/*
 * pmem_dma_qemu.lds — `pmem_dma.S` 的 QEMU/gem5（kaiwu-vast）链接布局
 * （`m16-testcases-014`）。
 *
 * QEMU `-kernel` 的 flat bin 从 `ENTRY = 0x0010_0000` 装入 PA RAM；同一份
 * `pmem_dma.S` 用 `--defsym ENTRY/SIG_BUF/EXITB` 覆盖 RTL 的 SRAM 地址：
 *
 *   ENTRY + 0x0000  .text   探针代码（≤ 16 KiB）
 *   ENTRY + 0x4000  .data   phase / sig_bytes
 *   ENTRY + 0x5000  SIG_BUF（96 槽 = 768 B）
 *   ENTRY + 0x5800  EXITB
 *
 * PA 测试窗（0x20_0000 起）不与镜像重叠；step5 页表 PTE0 覆盖 PA [0, 512 MiB)
 * 且 VA = PA。
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

  ASSERT(SIZEOF(.text) <= 0x4000, "pmem_dma qemu: .text 越过 16 KiB 窗口")
  ASSERT(SIZEOF(.data) <= 0x1000, "pmem_dma qemu: .data 越过 4 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
