/*
 * tests/arch/cache/cache_rtl.lds — cfx5 RTL 承载（chipyard WumingVastConfig）
 * 的链接布局（m16-testcases-009）。
 *
 *   ENTRY + 0x0000  .text     探针主体（hmon SRAM，64 KiB 窗口）
 *   ENTRY + 0x5000  签名区（运行时写，不进镜像；SIG_BUF）
 *   ENTRY + 0x5800  SYS_EXIT 参数块（运行时写，不进镜像；EXITB）
 *   PA 0x8000       L1 表 0x1000 号项（PTBR = 0；VA[41:29] = 0x1000）
 *   PA 0x10000      L2 表（16 项；L2[4] = 页 0x4_0000、L2[8] = 页 0x8_0000）
 *
 * 数据/代码行由探针在运行时写并 `D|flush`，所以不需要 +loadmem 数据段；
 * 只有页表由 +loadmem 装入。
 */

ENTRY(_start)

PHDRS
{
  text PT_LOAD FLAGS(7);
  ptl1 PT_LOAD FLAGS(6);
  ptl2 PT_LOAD FLAGS(6);
}

SECTIONS
{
  . = 0xffffff010100;

  .text : {
    *(.text*)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000,
         "cache_rtl: .text 越过 16 KiB 窗口（SIG_BUF 在 +0x5000）")

  . = 0x8000;
  .pt_l1 : {
    *(.pt_l1)
  } : ptl1

  ASSERT(SIZEOF(.pt_l1) == 8, "cache_rtl: L1 项必须是 8 字节")

  . = 0x10000;
  .pt_l2 : {
    *(.pt_l2)
  } : ptl2

  ASSERT(SIZEOF(.pt_l2) == 128, "cache_rtl: L2 表必须是 16 × 8 字节")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
