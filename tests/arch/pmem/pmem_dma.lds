/*
 * pmem_dma.lds — `tests/arch/pmem/pmem_dma.S` 的 RTL 链接布局
 * （`m16-testcases-014`，chipyard `WumingVastConfig`）。
 *
 * 与 `tests/arch/hart/cfx15.lds` 同型（固定 BootROM 跳到 cfx63 SRAM 的
 * `0xffff_ff00_2000`（`spec/Kaiwu §6.2` 新几何），`+loadmem` 只装 PT_LOAD 段）：
 *
 *   ENTRY + 0x0000  .text   探针代码（≤ 16 KiB）
 *   ENTRY + 0x4000  .data   phase / sig_bytes
 *   SIGNATURE       签名缓冲（`MAIN_SRAM_BASE + 0x1000`；SIG_BUF；96 槽 = 768 B）
 *   EXIT_BLOCK      SYS_EXIT 参数块（`MAIN_SRAM_BASE + 0x0030`；EXITB）
 *   PA 0x0          首张页表（4 × 512 MiB 超页；VA = PA，HSJU = 0xC）
 *
 * PA 测试窗（0x20_0000 起）不用链接布局：CPU 经首张页表的 PTE0（VA = PA）
 * 运行期读写；DMA 直接以 PA 访问。RTL 的固定 BootROM 不建页表 ⇒ 探针在
 * `_start` 里写 PTBR/ptw_enable（与 QEMU/gem5 的 step5 BootROM 幂等对齐）。
 */

ENTRY(_start)

PHDRS
{
  image PT_LOAD FLAGS(7);
  ptl1 PT_LOAD FLAGS(6);
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

  ASSERT(SIZEOF(.text) <= 0x4000, "pmem_dma: .text 越过 16 KiB 窗口")

  . = 0x0;
  .pt_l1 : {
    *(.pt_l1)
  } : ptl1

  ASSERT(SIZEOF(.pt_l1) == 32, "pmem_dma: 首张页表必须是 4 × 8 字节")
  ASSERT(SIZEOF(.data) <= 0x1000, "pmem_dma: .data 越过 4 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
