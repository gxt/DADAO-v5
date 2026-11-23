/*
 * ptw_sig.lds — `tests/arch/ptw/ptw_sig.S` 的链接布局（`m16-chipyard-018`）。
 *
 * 两套地址：
 *   * 探针代码/签名区在测试 RAM 窗口（`ENTRY = 0xffffff010100`，
 *     VA[47:42] ≠ 0 ⇒ 不经 PTW；`+loadmem` 装入）；
 *   * 页表按 **PA** 预置（`p_paddr`）：L1 0x7FF0_0000、L1B 0x7FF4_0000、
 *     L2 0x7FF2_0000 —— 与 `ptw_carrier_tlb.py`（QEMU/gem5）的 QEMU 场景同一组
 *     值。数据页由探针在运行期经 VA = PA + 2 TiB 写入（超页 L1[0x1003]）。
 *
 * 末尾 ASSERT 回读校验每段的起始地址（与 `gen_ptw_sig_tables.py` 的常量
 * 互校；手写错一位即链接失败）。
 */

ENTRY(_start)

PHDRS
{
  text  PT_LOAD FLAGS(7);
  ptl1  PT_LOAD FLAGS(6);
  ptl1b PT_LOAD FLAGS(6);
  ptl2b PT_LOAD FLAGS(6);
  ptl2  PT_LOAD FLAGS(6);
}

SECTIONS
{
  . = 0xffffff010100;
  .text : {
    *(.text)
  } : text

  ASSERT(SIZEOF(.text) <= 0x4000, "ptw_sig: .text 越过 16 KiB 窗口")

  . = 0x7ff00000;
  .ptl1 : { *(.ptl1) } : ptl1

  . = 0x7ff40000;
  .ptl1b : { *(.ptl1b) } : ptl1b

  . = 0x7ff60000;
  .ptl2b : { *(.ptl2b) } : ptl2b

  . = 0x7ff20000;
  .ptl2 : { *(.ptl2) } : ptl2

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

ASSERT(ADDR(.ptl1) == 0x7ff00000, "ptw_sig: L1 must be at 0x7ff00000")
ASSERT(ADDR(.ptl1b) == 0x7ff40000, "ptw_sig: L1B must be at 0x7ff40000")
ASSERT(ADDR(.ptl2b) == 0x7ff60000, "ptw_sig: L2B must be at 0x7ff60000")
ASSERT(ADDR(.ptl2) == 0x7ff20000, "ptw_sig: L2 must be at 0x7ff20000")
