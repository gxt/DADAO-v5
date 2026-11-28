/*
 * tiny_hmon.lds — Kaiwu-Tiny cfx_power + hmon execution case
 * (m13-gem5-001).
 *
 * Three PT_LOAD segments (spec/Kaiwu §1.1, M19 tiny geometry):
 *   BootROM 0xffff_ffff_0000, 8 KiB (power stub, R-X)
 *   hmon    0x0fff_0000_0000, 8 KiB (hmon vector, R-W-X)
 *   SRAM    0xffff_ff00_2000  (application body/data, R-W-X; fixed entry,
 *                              `MAIN_SRAM_BASE + 0x2000`, `kernel_reserved = 0`)
 *
 * The SRAM data area is fixed at `ENTRY + 0x3100` and the result table at
 * `ENTRY + 0x4000`; `tiny_hmon.S` mirrors those offsets with `.equ` so the
 * program never hardcodes a runtime path or a host address.
 *
 * The BootROM/hmon content is still the old firmware (64 KiB image layout); the
 * image layout is migrated here only so `machine-tiny.inc`'s ENTRY stays
 * consistent with the linked address.  Full migration belongs to the
 * BootROM/gem5 Tiny tasks.
 */
ENTRY(_start)

PHDRS
{
  boot PT_LOAD FLAGS(5);
  hmon PT_LOAD FLAGS(7);
  app  PT_LOAD FLAGS(7);
}

SECTIONS
{
  .bootrom 0xffffffff0000 : {
    *(.bootrom)
  } :boot

  .hmon 0x0fff00000000 : {
    *(.hmon)
  } :hmon

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
