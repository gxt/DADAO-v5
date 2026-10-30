/*
 * hmon.lds — INTEG-046t step5 hmon image (ADR-0043 D4)
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

  ASSERT(SIZEOF(.text) <= LENGTH(HMON), "step5 hmon exceeds 64 KiB")
}
