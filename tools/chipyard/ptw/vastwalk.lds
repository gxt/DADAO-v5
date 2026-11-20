/*
 * vastwalk.lds — `tools/chipyard/ptw/vastwalk.S` 的链接布局（`m16-chipyard-007`）。
 *
 * 两套地址：
 *   * 探针自身在核内 SRAM（`0xffffff010100`，`addr[47:42] ≠ 0`，不经翻译）；
 *   * 页表与映射目标按 **PA** 落在 PA RAM（`+loadmem=` 按 `p_paddr` 装入）：
 *       L1 表 0x0 / L2 表 0x1_0000 / 数据页 0x1_1000 / 故障表 0x3_0000 /
 *       可执行桩 0x5_0000 / 超页 0x4000_0000 与 0x4400_0000。
 *     段地址 = 生成器（`gen_vastwalk_tables.py`）里的常量，二者由本文件与生成器
 *     的常量互校（`--check-layout` 由证据脚本做）。
 *
 * 末尾的 ASSERT 把每个故障用例的「回落点相对 `aip.si` 的偏移」与「jump 相对
 * sub.o 的偏移」由链接器回读校验 —— 手写立即数（16/24）错一位即链接失败。
 */

ENTRY(_start)

PHDRS
{
  text   PT_LOAD FLAGS(7);
  ptl1   PT_LOAD FLAGS(6);
  ptl2   PT_LOAD FLAGS(6);
  page   PT_LOAD FLAGS(6);
  fresh  PT_LOAD FLAGS(6);
  ptl2b  PT_LOAD FLAGS(6);
  stub   PT_LOAD FLAGS(4);
  super0 PT_LOAD FLAGS(6);
  super1 PT_LOAD FLAGS(6);
}

SECTIONS
{
  . = 0xffffff010100;
  .text : {
    *(.text)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000, "vastwalk: .text 越过 16 KiB 窗口")

  /* 宏层固定地址（`inst_test.inc`：TEST_PAD / TEST_DATA）——都落在核内 SRAM 窗口，
     不参与翻译；不显式放置的话链接器会把它们丢到 PA 段之后，`__pad` 的相对跳转
     就够不着 `.text`。 */
  . = 0xffffff014000;
  .faultpad : { *(.faultpad) } : text

  . = 0xffffff015800;
  .testdata : { *(.testdata) } : text

  . = 0x0;
  .pt_l1 : { *(.pt_l1) } : ptl1

  . = 0x10000;
  .pt_l2 : { *(.pt_l2) } : ptl2

  . = 0x10700;
  .pagedata : { *(.pagedata) } : page

  . = 0x30000;
  .pt_l2b : { *(.pt_l2b) } : ptl2b

  . = 0x50000;
  .stub : { *(.stub) } : stub

  . = 0x60000;
  .fresh : { *(.fresh) } : fresh

  . = 0x40000000;
  .super0 : { *(.super0) } : super0

  . = 0x44000000;
  .super1 : { *(.super1) } : super1

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

/* 数据类故障例：aip → add.si → st.o → 故障访问，回落点 = aip + 16 */
ASSERT(f1_resume == f1_aip + 16, "vastwalk: f1 resume must be aip + 16")
ASSERT(f2_resume == f2_aip + 16, "vastwalk: f2 resume must be aip + 16")
ASSERT(f3_resume == f3_aip + 16, "vastwalk: f3 resume must be aip + 16")
ASSERT(f4_resume == f4_aip + 16, "vastwalk: f4 resume must be aip + 16")
ASSERT(f5_resume == f5_aip + 16, "vastwalk: f5 resume must be aip + 16")
ASSERT(f6_resume == f6_aip + 16, "vastwalk: f6 resume must be aip + 16")
ASSERT(f7_resume == f7_aip + 16, "vastwalk: f7 resume must be aip + 16")
ASSERT(f9_resume == f9_aip + 16, "vastwalk: f9 resume must be aip + 16")
ASSERT(f20_after == f20_aip + 20, "vastwalk: f20 resume must be aip + 20")

/* 取指类故障例：aip → add.si → st.o → sub.o → add.si → jump，回落点 = aip + 24 */
ASSERT(f8_resume == f8_aip + 24, "vastwalk: f8 resume must be aip + 24")
ASSERT(f8_jump == f8_fault + 8, "vastwalk: f8 jump must be the sub.o + 8 B")

/* 取指用例的返回地址：`aip.si` + `add.si` + `jump` 三条 ⇒ +12 */
ASSERT(vw_back == vw_jump_site + 12, "vastwalk: vw_back must be jump_site + 12")

/* 数据页的 payload 与 store 落点：都落在 L2 表所在页的 +0x1000 起 */
ASSERT(ADDR(.pagedata) == 0x10700, "vastwalk: pagedata must be at PA 0x1_0700")
ASSERT(ADDR(.pt_l2) == 0x10000, "vastwalk: L2 table must be at PA 0x1_0000")
ASSERT(ADDR(.stub) == 0x50000, "vastwalk: stub must be at PA 0x5_0000")
ASSERT(ADDR(.fresh) == 0x60000, "vastwalk: fresh page must be at PA 0x6_0000")
