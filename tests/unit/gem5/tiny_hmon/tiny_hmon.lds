/*
 * tiny_hmon.lds — Kaiwu-Tiny cfx_power + hmon execution case
 * (m13-gem5-001; m19-gem5-003 migrates it to the 8 KiB Tiny geometry).
 *
 * One PT_LOAD, all of it inside the Tiny application image window
 * (spec/Kaiwu §6.1/§6.2.1, M19 geometry):
 *   SRAM   0xffff_ff00_2000  (application body/data, R-W-X; fixed entry,
 *                            `MAIN_SRAM_BASE + 0x2000`, `kernel_reserved = 0`;
 *                            image_window = 128 KiB, +0x2000..+0x21FFF)
 *
 * The BootROM (8 KiB at 0xffff_ffff_0000) and the hmon SRAM
 * (0x0fff_0000_0000) are *not* part of this ELF: the host loader only
 * installs the fixed BootROM firmware image and this SRAM-only application
 * (spec/Kaiwu §6.2).  Adding empty BootROM/hmon segments would make the
 * loader reject an empty PT_LOAD, so they are deliberately absent.
 *
 * The SRAM data area is fixed at `ENTRY + 0x3100` and the result table at
 * `ENTRY + 0x4000`; `tiny_hmon.S` mirrors those offsets with `.equ` so the
 * program never hardcodes a runtime path or a host address.
 */
ENTRY(_start)

PHDRS
{
  app PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0xffffff002000;
  .text : {
    *(.text .text.*)
  } :app

  . = 0xffffff004000;   /* ENTRY + 0x2000 */
  .rcheck : {
    *(.rcheck)
  } :app

  . = 0xffffff005100;   /* ENTRY + 0x3100 */
  .data : {
    *(.data .data.*)
  } :app

  . = 0xffffff006000;   /* ENTRY + 0x4000 */
  .results (NOLOAD) : {
    *(.results)
  } :app

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
