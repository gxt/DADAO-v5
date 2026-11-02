/*
 * power.lds — INTEG-046t step5 BootROM power flat segment
 *
 * ADR-0043 D1/D2: the power stage is the last 64 KiB of the 256 KiB BootROM;
 * it is linked at the reset vector 0xffff_ffff_0000.  The image builder packs
 * the flat bytes at ROM offset 0x3_0000.
 *
 * Shared routines are placed at fixed offsets so hmon can call them by
 * absolute ROM address (0xffff_fffc_2000 / 0xffff_fffc_2400).
 */

ENTRY(_start)

MEMORY
{
  ROM (rx) : ORIGIN = 0xffffffff0000, LENGTH = 64K
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

  ASSERT(rom_validate_table == ORIGIN(ROM) + 0x2000,
         "step5: rom_validate_table must be at ROM offset 0x2000")
  ASSERT(elf_loader == ORIGIN(ROM) + 0x2400,
         "step5: elf_loader must be at ROM offset 0x2400")
  ASSERT(SIZEOF(.text) <= LENGTH(ROM), "step5 power exceeds the 64 KiB window")
}
