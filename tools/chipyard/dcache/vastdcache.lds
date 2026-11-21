/*
 * vastdcache.lds — `tools/chipyard/dcache/vastdcache.S` 的链接布局（`m16-chipyard-009`）。
 *
 * 两套地址：
 *   * 探针自身与指令字在核内 SRAM（`0xffffff010100` 起，`addr[47:42] ≠ 0`，
 *     不经翻译、不进 D-Cache）；
 *   * 页表与数据按 **PA** 落在 PA RAM（`+loadmem=` 按 `p_paddr` 装入）：
 *       L1 表项 0x8000 / L2 表 0x1_0000 / A 行 0x4_1000 / B0..B7 0x4_3000.. /
 *       L9/L10/fresh 0x5_3000.. / fresh 0x6_1000.. / PTW 新旧目标 0x7_8000、
 *       0x7_C000 / 代码页 0x8_1000（内存初值为 0，无需装入）。
 *     段地址 = 生成器（`gen_vastdcache_tables.py`）里的常量，二者由本文件与
 *     生成器的常量互校（证据脚本 `--check-layout` 做）。
 */

ENTRY(_start)

PHDRS
{
  text    PT_LOAD FLAGS(7);
  stub    PT_LOAD FLAGS(7);
  ptl1    PT_LOAD FLAGS(6);
  ptl2    PT_LOAD FLAGS(6);
  l_a     PT_LOAD FLAGS(6);
  l_b     PT_LOAD FLAGS(6);
  l9      PT_LOAD FLAGS(6);
  l10     PT_LOAD FLAGS(6);
  page    PT_LOAD FLAGS(6);
  code    PT_LOAD FLAGS(6);
  ev0     PT_LOAD FLAGS(6);
  ev1     PT_LOAD FLAGS(6);
  ev2     PT_LOAD FLAGS(6);
  ev3     PT_LOAD FLAGS(6);
  ev4     PT_LOAD FLAGS(6);
  ev5     PT_LOAD FLAGS(6);
  ev6     PT_LOAD FLAGS(6);
  ev7     PT_LOAD FLAGS(6);
}

SECTIONS
{
  . = 0xffffff010100;
  .text : {
    *(.text)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000, "vastdcache: .text 越过 16 KiB 窗口")

  /* 宏层固定地址（`inst_test.inc`：TEST_PAD / TEST_DATA / TEST_BUF） */
  . = 0xffffff014100;
  .faultpad : { *(.faultpad) } : text

  . = 0xffffff015800;
  .testdata : { *(.testdata) } : text

  . = 0xffffff018000;
  .stubdata : { *(.stubdata) } : stub

  . = 0x8000;
  .pt_l1 : { *(.pt_l1) } : ptl1

  . = 0x10000;
  .pt_l2 : { *(.pt_l2) } : ptl2

  . = 0x41000;
  .l_a : { *(.l_a) } : l_a

  . = 0x43000;
  .l_b : { *(.l_b) } : l_b

  . = 0x53000;
  .l9 : { *(.l9) } : l9

  . = 0x61000;
  .l10 : { *(.l10) } : l10

  . = 0x70000;
  .page_old : { *(.page_old) } : page

  . = 0x90000;
  .page_new : { *(.page_new) } : page

  . = 0x81000;
  .code_old : { *(.code_old) } : code

  /* m16-chipyard-010：I-Cache 淘汰块（页 2、3、10..15 偏移 0x1000，组 64） */
  . = 0x21000;
  .ev_ev0 : { *(.ev_EV0) } : ev0

  . = 0x31000;
  .ev_ev1 : { *(.ev_EV1) } : ev1

  . = 0xA1000;
  .ev_ev2 : { *(.ev_EV2) } : ev2

  . = 0xB1000;
  .ev_ev3 : { *(.ev_EV3) } : ev3

  . = 0xC1000;
  .ev_ev4 : { *(.ev_EV4) } : ev4

  . = 0xD1000;
  .ev_ev5 : { *(.ev_EV5) } : ev5

  . = 0xE1000;
  .ev_ev6 : { *(.ev_EV6) } : ev6

  . = 0xF1000;
  .ev_ev7 : { *(.ev_EV7) } : ev7

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* 段地址与生成器常量一致（生成器的 `--check-geometry` 另核组索引） */
ASSERT(ADDR(.pt_l1) == 0x8000, "vastdcache: L1 entry must be at PA 0x8000")
ASSERT(ADDR(.pt_l2) == 0x10000, "vastdcache: L2 table must be at PA 0x1_0000")
ASSERT(ADDR(.l_a) == 0x41000, "vastdcache: A line must be at PA 0x4_1000")
ASSERT(ADDR(.l_b) == 0x43000, "vastdcache: B lines must start at PA 0x4_3000")
ASSERT(ADDR(.l9) == 0x53000, "vastdcache: L9 lines must start at PA 0x5_3000")
ASSERT(ADDR(.l10) == 0x61000, "vastdcache: fresh lines must start at PA 0x6_1000")
ASSERT(ADDR(.page_old) == 0x70000, "vastdcache: old page must be at PA 0x7_0000")
ASSERT(ADDR(.page_new) == 0x90000, "vastdcache: new page must be at PA 0x9_0000")
ASSERT(ADDR(.code_old) == 0x81000, "vastdcache: old code word must be at PA 0x8_1000")
ASSERT(ADDR(.ev_ev0) == 0x21000, "vastdcache: evictor 0 must be at PA 0x2_1000")
ASSERT(ADDR(.ev_ev1) == 0x31000, "vastdcache: evictor 1 must be at PA 0x3_1000")
ASSERT(ADDR(.ev_ev2) == 0xA1000, "vastdcache: evictor 2 must be at PA 0xA_1000")
ASSERT(ADDR(.ev_ev3) == 0xB1000, "vastdcache: evictor 3 must be at PA 0xB_1000")
ASSERT(ADDR(.ev_ev4) == 0xC1000, "vastdcache: evictor 4 must be at PA 0xC_1000")
ASSERT(ADDR(.ev_ev5) == 0xD1000, "vastdcache: evictor 5 must be at PA 0xD_1000")
ASSERT(ADDR(.ev_ev6) == 0xE1000, "vastdcache: evictor 6 must be at PA 0xE_1000")
ASSERT(ADDR(.ev_ev7) == 0xF1000, "vastdcache: evictor 7 must be at PA 0xF_1000")
ASSERT(SIZEOF(.ev_ev0) == 4, "vastdcache: evictor block must be one instruction")
