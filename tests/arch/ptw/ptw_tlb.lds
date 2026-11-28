/*
 * ptw_tlb.lds — `tests/arch/ptw/ptw_tlb.S` 的链接布局（`m16-chipyard-008`）。
 *
 * 两套地址：
 *   * 探针自身在核内 SRAM（`0xffffff002000`，`addr[47:42] ≠ 0`，不经翻译）；
 *   * 页表与映射目标按 **PA** 落在 PA RAM（`+loadmem=` 按 `p_paddr` 装入）：
 *       L1 表 0 / L2 表 0x1_0000 / 普通页 0x10_0000.. / 新目标 0x20_0000.. /
 *       OR 页 0x40_0000 / PX 0x50_0000 / PI 0x60_0000 / PD 0x70_0000 /
 *       超页数据 0x4000_0000 / 新超页目标 0x6000_0000。
 *     段地址 = 生成器（`gen_ptw_tlb_tables.py`）里的常量，二者由本文件与生成器
 *     的常量互校（证据脚本做）。
 *
 * 末尾 ASSERT 把 clean 故障回落的偏移（`aip + 20`）与各段起始地址由链接器
 * 回读校验 —— 手写立即数错一位即链接失败。
 */

ENTRY(_start)

PHDRS
{
  text   PT_LOAD FLAGS(7);
  ptl1   PT_LOAD FLAGS(6);
  ptl2   PT_LOAD FLAGS(6);
  pages  PT_LOAD FLAGS(7);
  ordata PT_LOAD FLAGS(7);
  px     PT_LOAD FLAGS(7);
  pi     PT_LOAD FLAGS(7);
  pinew  PT_LOAD FLAGS(7);
  pd     PT_LOAD FLAGS(7);
  pdnew  PT_LOAD FLAGS(7);
  gdata  PT_LOAD FLAGS(7);
  ngdata PT_LOAD FLAGS(7);
  sup    PT_LOAD FLAGS(7);
  supnew PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0xffffff002000;
  .text : {
    *(.text)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000, "ptw_tlb: .text 越过 16 KiB 窗口")

  /* 宏层固定地址（`inst_test.inc`：TEST_PAD / TEST_DATA）——都落在核内 SRAM 窗口。 */
  . = 0xffffff006000;
  .faultpad : { *(.faultpad) } : text

  . = 0xffffff007800;
  .testdata : { *(.testdata) } : text

  . = 0x0;
  .pt_l1 : { *(.pt_l1) } : ptl1

  . = 0x10000;
  .pt_l2 : { *(.pt_l2) } : ptl2

  . = 0x100000;
  .pages : { *(.pages) } : pages

  . = 0x400000;
  .ordata : { *(.ordata) } : ordata

  . = 0x500000;
  .px : { *(.px) } : px

  . = 0x600000;
  .pi : { *(.pi) } : pi

  . = 0x610000;
  .pi_new : { *(.pi_new) } : pinew

  . = 0x700000;
  .pd : { *(.pd) } : pd

  . = 0x710000;
  .pd_new : { *(.pd_new) } : pdnew

  . = 0x800000;
  .gdata : { *(.gdata) } : gdata

  . = 0x900000;
  .ngdata : { *(.ngdata) } : ngdata

  . = 0x40000000;
  .super : { *(.super) } : sup

  . = 0x60000000;
  .super_new : { *(.super_new) } : supnew

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* clean 故障例：aip → add.si → st.o → set.rd → cfx2rc，回落点 = aip + 20 */
ASSERT(tl_or_res1 == tl_or_aip1 + 20, "ptw_tlb: OR clean #1 resume must be aip + 20")
ASSERT(tl_or_res2 == tl_or_aip2 + 20, "ptw_tlb: OR clean #2 resume must be aip + 20")

/* 段地址与生成器常量一致（由证据脚本另行互校） */
ASSERT(ADDR(.pt_l1) == 0x0, "ptw_tlb: L1 table must be at PA 0")
ASSERT(ADDR(.pt_l2) == 0x10000, "ptw_tlb: L2 table must be at PA 0x1_0000")
ASSERT(ADDR(.pages) == 0x100000, "ptw_tlb: page data must start at PA 0x10_0000")
ASSERT(ADDR(.ordata) == 0x400000, "ptw_tlb: OR page must be at PA 0x40_0000")
ASSERT(ADDR(.px) == 0x500000, "ptw_tlb: PX page must be at PA 0x50_0000")
ASSERT(ADDR(.pi) == 0x600000, "ptw_tlb: PI page must be at PA 0x60_0000")
ASSERT(ADDR(.pd) == 0x700000, "ptw_tlb: PD page must be at PA 0x70_0000")
ASSERT(ADDR(.gdata) == 0x800000, "ptw_tlb: G page must be at PA 0x80_0000")
ASSERT(ADDR(.ngdata) == 0x900000, "ptw_tlb: G=0 page must be at PA 0x90_0000")
ASSERT(ADDR(.super) == 0x40000000, "ptw_tlb: superpage data must be at PA 0x4000_0000")
ASSERT(ADDR(.super_new) == 0x60000000, "ptw_tlb: new superpage data must be at PA 0x6000_0000")
