/*
 * inst-tiny.lds — `tests/inst/01-load-store/*.S`（单元素 ld/st）的链接布局
 *
 * 固定地址（与 `tests/inst/macros/inst_test.inc` 顶部 `.equ` 逐项对应；
 * 偏移错位由本脚本的 ASSERT 直接报错，不靠人记）：
 *
 *   ENTRY + 0x0000  .text           链例 + 故障例体（≤ 0x1E00）
 *   ENTRY + 0x1E00  .hmon_stub      测试自有 hmon 处理器（≤ 0x100）
 *   ENTRY + 0x1F00  .faultpad       故障落点（≤ 0x80）
 *   ENTRY + 0x1F80  （TEST_FAULTV，落点段内，无独立段）
 *   ENTRY + 0x2000  .testdata       数据块：前 0x800 B 负偏移区 + 192 B 模式 + 尾部零
 *   ENTRY + 0x3000  结果字节缓冲（运行时写，不进镜像）
 *   ENTRY + 0x4000  SYS_EXIT 参数块（运行时写，不进镜像）
 *
 * 单 PT_LOAD、RWX：chipyard `+loadmem=`、QEMU `-kernel <ELF>`、gem5 FS
 * `--kernel <ELF>` 三方装载同一份镜像（`spec/Machine-v5 §6`）。
 */

ENTRY(_start)

PHDRS
{
  image PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0xffffff010100;

  .text : {
    *(.text)
  } : image

  ASSERT(SIZEOF(.text) <= 0x1E00, "inst-tiny: .text 越过 handler 窗口（0x1E00）")

  . = 0xffffff010100 + 0x1E00;
  .hmon_stub : {
    *(.hmon_stub)
  } : image

  ASSERT(SIZEOF(.hmon_stub) <= 0x100, "inst-tiny: hmon 处理器超过 256 B")

  . = 0xffffff010100 + 0x1F00;
  .faultpad : {
    *(.faultpad)
  } : image

  ASSERT(SIZEOF(.faultpad) <= 0x80, "inst-tiny: 故障落点超过 128 B")

  . = 0xffffff010100 + 0x2000;
  .testdata : {
    *(.testdata)
  } : image

  ASSERT(SIZEOF(.testdata) == 0x1000, "inst-tiny: 数据块必须恰为 0x1000 B")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
