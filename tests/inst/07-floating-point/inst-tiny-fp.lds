/*
 * inst-tiny-fp.lds — `tests/inst/07-floating-point/*.S` 的链接布局
 *
 * 为什么另起一份：浮点册每个 id 的用例体较长（每条 = 清 FCSR + 装 2–3 个 rf
 * 初值 + 被测指令 + 标志/结果核对），同册 18 个 id 各自的 `.text` 会超过
 * `01-load-store/inst-tiny.lds` 的 0x1E00 窗口 ⇒ 本册把各段整体上移。
 * 地址与 `tests/inst/macros/inst_test.inc` 顶部 `__FP_LAYOUT` 分支逐项对应；
 * 偏移错位由下面的 ASSERT 直接报错，不靠人记。
 *
 *   ENTRY + 0x0000  .text           链例 + 故障例体（≤ 0x4000）
 *   ENTRY + 0x4000  .faultpad       故障落点（≤ 0x80）
 *   ENTRY + 0x4080  （TEST_FAULTV，落点段之后，无独立段）
 *   ENTRY + 0x5000  .testdata       数据块（TEST_DATA = +0x5800；0x800 负偏移区在前）
 *   ENTRY + 0x7000  结果字节缓冲（运行时写，不进镜像；≤ 127 × 8 B）
 *   ENTRY + 0x7800  SYS_EXIT 参数块（运行时写，不进镜像）
 *
 * 单 PT_LOAD、RWX：chipyard `+loadmem=`、QEMU `-kernel <ELF>`、gem5 FS
 * `--kernel <ELF>` 三方装载同一份镜像（`spec/Kaiwu §6`）。
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

  ASSERT(SIZEOF(.text) <= 0x4000, "inst-tiny-fp: .text 越过故障落点窗口（0x4000）")

  . = 0xffffff010100 + 0x4000;
  .faultpad : {
    *(.faultpad)
  } : image

  ASSERT(SIZEOF(.faultpad) <= 0x80, "inst-tiny-fp: 故障落点超过 128 B")

  . = 0xffffff010100 + 0x5000;
  .testdata : {
    *(.testdata)
  } : image

  ASSERT(SIZEOF(.testdata) == 0x2000, "inst-tiny-fp: 数据块必须恰为 0x2000 B")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
