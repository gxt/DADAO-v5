/*
 * power.lds — Machine-v5-Tiny BootROM power 启动 stub（m12-chipyard-007）
 *
 * 规范：spec/Machine-v5 §6.2「镜像布局」。power 段链接在复位向量
 * 0xffff_ffff_0000（镜像偏移 0x0000），上限 8 KiB（0x2000）；超限是链接期
 * 错误（§6.2「构建器须以链接断言/构建期检查强制上述上限」）。
 */

ENTRY(_start)

MEMORY
{
  ROM (rx) : ORIGIN = 0xffffffff0000, LENGTH = 8K
}

SECTIONS
{
  . = ORIGIN(ROM);

  .text : ALIGN(4) {
    *(.text .text.*)
    *(.rodata .rodata.*)
  } > ROM

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(SIZEOF(.text) <= LENGTH(ROM), "tiny power stub exceeds its 8 KiB segment")
}
