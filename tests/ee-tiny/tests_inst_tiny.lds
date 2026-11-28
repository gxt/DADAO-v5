/*
 * inst-tiny.lds — `tests/inst/**\/*.S`（**全部册**：`00-isa-design` + `01`–`12`）统一的链接布局
 * （`m15-testcases-006`：原 `01-load-store/inst-tiny.lds`(0x1E00 窗口) 与
 *   `07-floating-point/inst-tiny-fp.lds`(0x4000 窗口) 两份布局合并为这一份）。
 *
 * 固定地址（与 `tests/inst/macros/inst_test.inc` 顶部 `.equ` 逐项对应；
 * 偏移错位由下面的 ASSERT 直接报错，不靠人记）：
 *
 *   ENTRY + 0x0000  .text           链例 + 故障例体 + 收尾（≤ 0x4000 = 16 KiB）
 *   ENTRY + 0x4000  .faultpad       故障落点 `__pad`（≤ 0x200）
 *   ENTRY + 0x4200  （TEST_FAULTV，落点段之后，无独立段：+0 one-hot、+8 失败码）
 *   ENTRY + 0x4300  .faulttab       后继表（点号 × 8 B + 表尾哨兵，≤ 0x480；
 *                                   `m15-testcases-007`）
 *   ENTRY + 0x5000  .testdata       数据块：0x800 负偏移区 + 单元素 24 个数据单元模式 +
 *                                   多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE）
 *                                   （TEST_DATA = +0x5800；恒 0x2000 B）
 *
 * 结果缓冲与 SYS_EXIT 参数块**不在镜像窗口内**（`m19-testcases-002`，spec/Kaiwu
 * §6.2.1 的固定主 SRAM 布局）：结果缓冲 = `SIGNATURE`（`MAIN_SRAM_BASE + 0x1000`，
 * 0x800）、SYS_EXIT 参数块 = `EXIT_BLOCK`（`+0x0030`，16 B），二者都在运行期写、
 * 不进镜像。旧布局的 `ENTRY+0x7000`/`ENTRY+0x7800` 已删除。
 *
 * `ENTRY` = `0xffff_ff00_2000`（`MAIN_SRAM_BASE + 0x2000`；spec/Kaiwu §6.2，
 * `kernel_reserved = 0`）。本脚本的地址**写成字面量**：生成侧
 * `tools/testcases/lib/inst_expected.py::_lds_section_base` 按
 * `. = 0x… [+ 0x…];` 形式取段址，符号形式会让数据派生 fail-closed。
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
  . = 0xffffff002000;

  .text : {
    *(.text)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "inst-tiny: .text 越过故障落点窗口（0x4000）")
  ASSERT(_start == 0xffffff002000, "inst-tiny: _start 必须等于固定入口 0xffff_ff00_2000")

  . = 0xffffff002000 + 0x4000;
  .faultpad : {
    *(.faultpad)
  } : image

  ASSERT(SIZEOF(.faultpad) <= 0x200, "inst-tiny: 故障落点超过 512 B（TEST_FAULTV 在 0x4200）")

  . = 0xffffff002000 + 0x4300;
  .faulttab : {
    *(.faulttab)
  } : image

  ASSERT(SIZEOF(.faulttab) <= 0x480, "inst-tiny: 后继表超过 0x480（点号 ≤ 127 × 8 B + 哨兵）")

  . = 0xffffff002000 + 0x5000;
  .testdata : {
    *(.testdata)
  } : image

  ASSERT(SIZEOF(.testdata) == 0x2000, "inst-tiny: 数据块必须恰为 0x2000 B")
  /* 镜像窗口（spec/Kaiwu §6.2.1：entry 起 0x2_0000）上界；`.` = 镜像末地址 */
  ASSERT(. <= 0xffffff002000 + 0x20000, "inst-tiny: 镜像越过 image_window")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
