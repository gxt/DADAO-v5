/*
 * vasticache.lds — `tools/chipyard/icache/vasticache.S` 的链接布局（`m16-chipyard-010`）。
 *
 * 两套地址：
 *   * 探针自身、结果缓冲与栈在核内 SRAM（`0xffffff010100` 起，`addr[47:42] ≠ 0`，
 *     不经翻译、**不进 I-Cache**）；
 *   * 页表与十段被缓存代码按 **PA** 落在 PA RAM（`+loadmem=` 按 `p_paddr` 装入）：
 *       L1 表项 0x8000 / L2 表 0x1_0000 / A1..A8 页 2..9 偏移 0x1000 /
 *       A9 页 10 偏移 0x1000 / C1 页 11 偏移 0（组 0）。
 *     段地址 = 生成器（`gen_vasticache_tables.py`）里的常量；本文件用 ASSERT
 *     与生成器常量互校（生成器另有 `--check-geometry` 核组索引）。
 *
 * 每个代码块 = 16 条指令 = 64 B = **恰好一行**；块起始必须 64 B 对齐，
 * 否则一次跳转会填两行、命中计数失真。
 */

ENTRY(_start)

PHDRS
{
  text    PT_LOAD FLAGS(7);
  ptl1    PT_LOAD FLAGS(6);
  ptl2    PT_LOAD FLAGS(6);
  ca1     PT_LOAD FLAGS(6);
  ca2     PT_LOAD FLAGS(6);
  ca3     PT_LOAD FLAGS(6);
  ca4     PT_LOAD FLAGS(6);
  ca5     PT_LOAD FLAGS(6);
  ca6     PT_LOAD FLAGS(6);
  ca7     PT_LOAD FLAGS(6);
  ca8     PT_LOAD FLAGS(6);
  ca9     PT_LOAD FLAGS(6);
  cc      PT_LOAD FLAGS(6);
}

SECTIONS
{
  . = 0xffffff010100;
  .text : {
    *(.text)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000, "vasticache: .text 越过 16 KiB 窗口")

  /* 宏层固定地址（`inst_test.inc`：TEST_PAD / TEST_DATA / TEST_BUF / TEST_FAULTV） */
  . = 0xffffff014100;
  .faultpad : { *(.faultpad) } : text

  . = 0xffffff015800;
  .testdata : { *(.testdata) } : text

  . = 0x8000;
  .pt_l1 : { *(.pt_l1) } : ptl1

  . = 0x10000;
  .pt_l2 : { *(.pt_l2) } : ptl2

  . = 0x21000;
  .code_a1 : { *(.code_a1) } : ca1

  . = 0x31000;
  .code_a2 : { *(.code_a2) } : ca2

  . = 0x41000;
  .code_a3 : { *(.code_a3) } : ca3

  . = 0x51000;
  .code_a4 : { *(.code_a4) } : ca4

  . = 0x61000;
  .code_a5 : { *(.code_a5) } : ca5

  . = 0x71000;
  .code_a6 : { *(.code_a6) } : ca6

  . = 0x81000;
  .code_a7 : { *(.code_a7) } : ca7

  . = 0x91000;
  .code_a8 : { *(.code_a8) } : ca8

  . = 0xA1000;
  .code_a9 : { *(.code_a9) } : ca9

  . = 0xB0000;
  .code_c : { *(.code_c) } : cc

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* 段地址与生成器常量一致 */
ASSERT(ADDR(.pt_l1) == 0x8000, "vasticache: L1 entry must be at PA 0x8000")
ASSERT(ADDR(.pt_l2) == 0x10000, "vasticache: L2 table must be at PA 0x1_0000")
ASSERT(ADDR(.code_a1) == 0x21000, "vasticache: A1 must be at PA 0x2_1000")
ASSERT(ADDR(.code_a2) == 0x31000, "vasticache: A2 must be at PA 0x3_1000")
ASSERT(ADDR(.code_a3) == 0x41000, "vasticache: A3 must be at PA 0x4_1000")
ASSERT(ADDR(.code_a4) == 0x51000, "vasticache: A4 must be at PA 0x5_1000")
ASSERT(ADDR(.code_a5) == 0x61000, "vasticache: A5 must be at PA 0x6_1000")
ASSERT(ADDR(.code_a6) == 0x71000, "vasticache: A6 must be at PA 0x7_1000")
ASSERT(ADDR(.code_a7) == 0x81000, "vasticache: A7 must be at PA 0x8_1000")
ASSERT(ADDR(.code_a8) == 0x91000, "vasticache: A8 must be at PA 0x9_1000")
ASSERT(ADDR(.code_a9) == 0xA1000, "vasticache: A9 must be at PA 0xA_1000")
ASSERT(ADDR(.code_c) == 0xB0000, "vasticache: C1 must be at PA 0xB_0000")

/* 每个块恰好一行（64 B）：16 条指令 */
ASSERT(SIZEOF(.code_a1) == 64, "vasticache: block A1 must be exactly 64 B")
ASSERT(SIZEOF(.code_a2) == 64, "vasticache: block A2 must be exactly 64 B")
ASSERT(SIZEOF(.code_a3) == 64, "vasticache: block A3 must be exactly 64 B")
ASSERT(SIZEOF(.code_a4) == 64, "vasticache: block A4 must be exactly 64 B")
ASSERT(SIZEOF(.code_a5) == 64, "vasticache: block A5 must be exactly 64 B")
ASSERT(SIZEOF(.code_a6) == 64, "vasticache: block A6 must be exactly 64 B")
ASSERT(SIZEOF(.code_a7) == 64, "vasticache: block A7 must be exactly 64 B")
ASSERT(SIZEOF(.code_a8) == 64, "vasticache: block A8 must be exactly 64 B")
ASSERT(SIZEOF(.code_a9) == 64, "vasticache: block A9 must be exactly 64 B")
ASSERT(SIZEOF(.code_c) == 64, "vasticache: block C1 must be exactly 64 B")
