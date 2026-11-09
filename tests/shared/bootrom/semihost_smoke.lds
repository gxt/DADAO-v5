/*
 * semihost_smoke.lds — Machine-v5-Tiny semihosting probe (m12-chipyard-004).
 *
 * Single PT_LOAD image in the Tiny SRAM window.  The layout is *fixed by
 * absolute address* so the program can materialise every pointer with
 * `set.zw`/`or.w` (the temporary WumingCoreStub has no PC-relative load):
 *
 *   0x...010100  .text    (<= 0x400)
 *   0x...010400  .rodata  BUF (64 B), EXCL (1 B), MSG (long message)
 *   0x...012000  .bss     BLOCK (SYS_WRITE block), EXITBLK (SYS_EXIT block)
 *
 * The ASSERTs keep the source-side EQU addresses and the linked layout from
 * drifting apart; the evidence script also checks the ELF program headers.
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

  ASSERT(SIZEOF(.text) <= 0x400, "semihost_smoke: .text overruns the rodata window")

  . = 0xffffff010100 + 0x400;
  .rodata : {
    *(.rodata .rodata.*)
  } : image

  ASSERT(SIZEOF(.rodata) < 0x1c00, "semihost_smoke: .rodata overruns the bss window")

  . = 0xffffff010100 + 0x2000;
  .bss : {
    *(.bss .bss.*)
    *(COMMON)
  } : image

  ASSERT(SIZEOF(.bss) <= 0x200, "semihost_smoke: .bss overruns its reserved window")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
