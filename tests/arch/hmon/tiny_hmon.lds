/*
 * tiny_hmon.lds — Machine-v5-Tiny cfx_power + hmon execution case
 * (m13-gem5-001).
 *
 * Three PT_LOAD segments (spec/Machine-v5 §1.1):
 *   BootROM 0xffff_ffff_0000, 64 KiB (power stub, R-X)
 *   hmon    0x0fff_0000_0000, 64 KiB (hmon vector, R-W-X)
 *   SRAM    0xffff_ff01_0100  (application body/data, R-W-X)
 *
 * The SRAM data area is fixed at `ENTRY + 0x3100` and the result table at
 * `ENTRY + 0x4000`; `tiny_hmon.S` mirrors those offsets with `.equ` so the
 * program never hardcodes a runtime path or a host address.
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

  . = 0xffffff010100;
  .text : {
    *(.text .text.*)
  } :app

  . = 0xffffff012100;
  .rcheck : {
    *(.rcheck)
  } :app

  . = 0xffffff013200;
  .data : {
    *(.data .data.*)
  } :app

  . = 0xffffff014100;
  .results (NOLOAD) : {
    *(.results)
  } :app

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
