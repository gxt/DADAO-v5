/*
 * smon.lds — m14-qemu-001 K1 smon firmware
 * smon SRAM: 0x0bff_0000_0000, 64 KiB; e_entry is the smon S-mode vector.
 */

ENTRY(_start)

MEMORY
{
  SMON (rx) : ORIGIN = 0x0bff00000000, LENGTH = 64K
}

SECTIONS
{
  . = ORIGIN(SMON);

  .text : ALIGN(4) {
    *(.text .text.*)
    *(.rodata .rodata.*)
  } > SMON

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(SIZEOF(.text) <= LENGTH(SMON), "k0 smon exceeds 64 KiB")
}
