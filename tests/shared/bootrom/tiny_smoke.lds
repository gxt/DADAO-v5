/*
 * tiny_smoke.lds — Machine-v5-Tiny loadmem smoke application (m12-chipyard-003).
 *
 * The image is an ELF (not a flat binary) because the harness `+loadmem=`
 * loader consumes PT_LOAD segments; the BootROM trampoline jumps to the
 * profile's fixed application entry, so ORIGIN must equal `ENTRY` from
 * tests/shared/asm/machine-tiny.inc (0xffff_ff01_0100).  A single PT_LOAD
 * carries .text/.rodata/.data and the .bss tail (p_memsz > p_filesz), so the
 * loader's zero fill of the tail is exercised by the same load.
 *
 * No address literal is invented here: the value is the `tiny` profile entry
 * (tests/shared/machine-profiles.yaml).
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
    *(.text .text.*)
  } : image

  ASSERT(SIZEOF(.text) <= 0x100, "tiny_smoke: .text no longer fits below APP_DATA")

  . = 0xffffff010100 + 0x100;
  .rodata : {
    *(.rodata .rodata.*)
  } : image

  . = 0xffffff010100 + 0x108;
  .bss : {
    *(.bss .bss.*)
    *(COMMON)
  } : image

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
