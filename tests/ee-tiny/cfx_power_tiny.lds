/*
 * cfx_power_tiny.lds — Kaiwu-Tiny BootROM cfx_power 启动 stub（m12-chipyard-007；
 * M19 8 KiB 几何见 m19-testcases-005）
 *
 * 规范：spec/Kaiwu §6.2「镜像布局」。power 段链接在复位向量
 * 0xffff_ffff_0000（镜像偏移 0x0000），上限 2 KiB（0x800）；超限是链接期
 * 错误（§6.2「构建器须以链接断言/构建期检查强制上述上限」）。8 KiB BootROM 的
 * 其余部分（hmon 源段 0x0800 / 保留区 / 表 0x1F00）由
 * `tools/testcases/arch/build_tiny_bootrom.py` 拼装，不在本脚本内。
 */

ENTRY(_start)

MEMORY
{
  ROM (rx) : ORIGIN = 0xffffffff0000, LENGTH = 2K
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

  ASSERT(SIZEOF(.text) <= LENGTH(ROM), "tiny power stub exceeds its 2 KiB segment")
}
