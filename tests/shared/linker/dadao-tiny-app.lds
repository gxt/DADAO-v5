/* dadao-tiny-app.lds — Machine-v5-Tiny contract application ELF (m13-qemu-002).
 *
 * Spec: spec/Machine-v5 §6 "装载语义 — Machine-v5-Tiny" (0.4.4-rc): the crt is
 * linked together with the test program, the whole application lives in SRAM,
 * and the entry (raw and ELF) is the fixed 0xffff_ff01_0100.  The fixed 64 KiB
 * BootROM firmware is supplied separately (bootrom-image); the host loader
 * never places a PT_LOAD in the BootROM or in hmon SRAM.
 *
 * Geometry comes from tests/shared/machine-profiles.yaml (profile `tiny`):
 *   RAM : 0xffff_ff00_0000 .. 0xffff_ff7f_ffff  (8 MiB, rwx)
 *
 * `dadao-tiny.lds` is kept as the pre-contract (crt-in-ROM) layout for the
 * legacy harness; new ELF applications must use this script.
 */

ENTRY(_start)

MEMORY
{
  RAM (rwx) : ORIGIN = 0xffffff000000, LENGTH = 0x800000
}

PHDRS
{
  image PT_LOAD FLAGS(7);
  data  PT_LOAD FLAGS(7);
}

__stack_top = 0xffffff7eff00;
__exit_block = 0xffffff7e0000;
__heap_end = 0xffffff7eef00;

SECTIONS
{
  /* Explicit address: lld's MEMORY regions pin un-addressed output sections
   * to the region origin, so the fixed entry is spelled on the section. */
  .text.start 0xffffff010100 : ALIGN(4) {
    *(.text.start .text.start.*)
  } > RAM :image

  .text : ALIGN(4) {
    *(.text .text.*)
  } > RAM :image

  INCLUDE dadao-common.lds

  ASSERT(SIZEOF(.text.start) == 0 || _start == 0xffffff010100,
         "tiny app: _start must be the fixed entry")
  ASSERT(SIZEOF(.text.start) + SIZEOF(.text) + SIZEOF(.rodata) +
         SIZEOF(.data) + SIZEOF(.bss) <= LENGTH(RAM) - 0x10100,
         "tiny app: sections exceed the SRAM window")
}
