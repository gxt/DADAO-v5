/*
 * inst-tiny.lds — `tests/inst/**\/*.S`（**全部册**：`00-isa-design` + `01`–`12`）统一的链接布局
 * （`m15-testcases-006`：原 `01-load-store/inst-tiny.lds`(0x1E00 窗口) 与
 *   `07-floating-point/inst-tiny-fp.lds`(0x4000 窗口) 两份布局合并为这一份）。
 *
 * 固定地址（与 `tests/inst/macros/inst_test.inc` 顶部 `.equ` 逐项对应；
 * 偏移错位由下面的 ASSERT 直接报错，不靠人记）：
 *
 *   ENTRY + 0x0000  .text           链例 + 故障例体（≤ 0x4000 = 16 KiB）
 *   ENTRY + 0x4000  .faultpad       故障落点（≤ 0x80）
 *   ENTRY + 0x4080  （TEST_FAULTV，落点段之后，无独立段）
 *   ENTRY + 0x5000  .testdata       数据块：0x800 负偏移区 + 单元素 24 拍模式 +
 *                                   多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE）
 *                                   （TEST_DATA = +0x5800；恒 0x2000 B）
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

  ASSERT(SIZEOF(.text) <= 0x4000, "inst-tiny: .text 越过故障落点窗口（0x4000）")

  . = 0xffffff010100 + 0x4000;
  .faultpad : {
    *(.faultpad)
  } : image

  ASSERT(SIZEOF(.faultpad) <= 0x80, "inst-tiny: 故障落点超过 128 B")

  . = 0xffffff010100 + 0x5000;
  .testdata : {
    *(.testdata)
  } : image

  ASSERT(SIZEOF(.testdata) == 0x2000, "inst-tiny: 数据块必须恰为 0x2000 B")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
