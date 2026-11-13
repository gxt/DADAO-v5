/*
 * hmon.lds — m14-qemu-001 K1 boot hmon
 * hmon SRAM: 0x0fff_0000_0000, 64 KiB; e_entry is the hmon H-mode vector.
 */

ENTRY(_start)

MEMORY
{
  HMON (rx) : ORIGIN = 0x0fff00000000, LENGTH = 64K
}

SECTIONS
{
  . = ORIGIN(HMON);

  .text : ALIGN(4) {
    *(.text .text.*)
    *(.rodata .rodata.*)
  } > HMON

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(SIZEOF(.text) <= LENGTH(HMON), "k0 hmon exceeds 64 KiB")
}
