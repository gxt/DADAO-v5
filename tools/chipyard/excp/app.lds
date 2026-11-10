/*
 * app.lds — m12-chipyard-019 RTL case layout (Machine-v5-Tiny).
 *
 * The ELF is the *application* only (spec/Machine-v5 §6 装载语义): the single
 * PT_LOAD segment sits in SRAM, `e_entry` is the fixed entry, and the BootROM /
 * hmon firmware comes from the fixed image.  The program is one object with
 * `_start` at the entry, so every `.equ ENTRY + off` in the source is the real
 * address; the ASSERTs below turn a layout slip into a link failure.
 */

ENTRY_ADDR = 0xffffff010100;

ENTRY(_start)

SECTIONS
{
  . = ENTRY_ADDR;

  .text : {
    *(.text .text.*)
    *(.rodata .rodata.*)
  }

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(_start == ENTRY_ADDR, "app entry must be the fixed Tiny entry")
  ASSERT(ialign_go0 == ENTRY_ADDR + 0x4000, "IALIGN site 0 layout")
  ASSERT(ialign_go1 == ENTRY_ADDR + 0x4100, "IALIGN site 1 layout")
  ASSERT(ialign_go2 == ENTRY_ADDR + 0x4200, "IALIGN site 2 layout")
  ASSERT(land_supv == ENTRY_ADDR + 0x4300, "cg3-permission landing layout")
  ASSERT(forge_site == ENTRY_ADDR + 0x4400, "forged-frame layout")
  ASSERT(ialign_tgt0 == ENTRY_ADDR + 0x5000, "IALIGN target 0 layout")
  ASSERT(ialign_tgt1 == ENTRY_ADDR + 0x5100, "IALIGN target 1 layout")
  ASSERT(ialign_tgt2 == ENTRY_ADDR + 0x5200, "IALIGN target 2 layout")
}
