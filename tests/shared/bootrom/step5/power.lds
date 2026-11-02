/*
 * power.lds — INTEG-046t step5 BootROM power flat segment
 *
 * TESTCASES-091t: Node profile (tests/shared/machine-profiles.yaml).
 * The power stage is the last 64 KiB of the 4 MiB BootROM; it is linked at the
 * reset vector (RESET_PC = 0xffff_ffff_0000).  The image builder packs the flat
 * bytes at image offset bootrom_size - 64 KiB (0x3f_0000).
 *
 * Shared routines are placed at fixed offsets so hmon can call them by
 * absolute address (RESET_PC + 0x2000 / + 0x2400).
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
