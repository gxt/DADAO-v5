/*
 * cfx5_maint.lds — `tests/arch/cache/cfx5_maint.S` 的链接布局（`m16-chipyard-017`）。
 *
 * 两套地址：
 *   * 探针自身在核内 SRAM（`ENTRY` 起，`addr[47:42] ≠ 0`：不经翻译、不进
 *     I/D Cache）——所以维护命令可以清空/失效整个缓存而不打断探针本身；
 *   * 页表、数据行与代码行按 **PA** 落在 PA RAM（`+loadmem=` 按 `p_paddr`
 *     装入）：L1 表项 0x8000 / L2 表 0x10000 / 区间两行 0x41200、0x41240 /
 *     all 数据行 0x45000 / 代码行 0x81000。地址常量在
 *     `gen_cfx5_maint_tables.py`，与本节由证据脚本的 `--check-layout` 互校。
 *
 * `__CHECK_RD` 失败以点号退出；地址越界/回落点错位由末尾 ASSERT 在链接期报错。
 */

ENTRY(_start)

PHDRS
{
  text     PT_LOAD FLAGS(7);
  faultpad PT_LOAD FLAGS(7);
  testdata PT_LOAD FLAGS(7);
  ptl1     PT_LOAD FLAGS(6);
  ptl2     PT_LOAD FLAGS(6);
  l_r0     PT_LOAD FLAGS(6);
  l_r1     PT_LOAD FLAGS(6);
  l_d      PT_LOAD FLAGS(6);
  l_code   PT_LOAD FLAGS(6);
}

SECTIONS
{
  . = 0xffffff002000;
  .text : {
    *(.text)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000, "cfx5_maint: .text 越过 16 KiB 窗口")

  . = 0xffffff002000 + 0x4000;
  .faultpad : {
    *(.faultpad)
  } : faultpad

  ASSERT(SIZEOF(.faultpad) <= 0x200, "cfx5_maint: 故障落点超过 512 B")

  . = 0xffffff002000 + 0x5000;
  .testdata : {
    *(.testdata)
  } : testdata

  . = 0x8000;
  .pt_l1 : { *(.pt_l1) } : ptl1

  . = 0x10000;
  .pt_l2 : { *(.pt_l2) } : ptl2

  . = 0x41200;
  .l_r0 : { *(.l_r0) } : l_r0

  . = 0x41240;
  .l_r1 : { *(.l_r1) } : l_r1

  . = 0x45000;
  .l_d : { *(.l_d) } : l_d

  . = 0x81000;
  .l_code : { *(.l_code) } : l_code

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* 三个故障例：故障指令后紧跟一条 nop 垫片，回落点 = 故障指令 + 8（直接由
 * `st.o` 写进 hmon 的返回槽，不依赖 aip 相对计算）；错一位即链接失败。 */
ASSERT(f1_resume == f1_fault + 8, "cfx5_maint: f1 resume must be fault + 8")
ASSERT(f2_resume == f2_fault + 8, "cfx5_maint: f2 resume must be fault + 8")
ASSERT(f3_resume == f3_fault + 8, "cfx5_maint: f3 resume must be fault + 8")
