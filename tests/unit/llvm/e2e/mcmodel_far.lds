/* mcmodel_far.lds -- far code-layout link script (LLVM-131t; ADR-0036 D1/D5).
 *
 * Geometry follows the tiny profile (tests/shared/machine-profiles.yaml).
 * `.text.start` (crt stub) sits at the Tiny ROM base; app `.text` starts at the
 * profile entry.  The `.far` output section is 64 MiB below `.text` (outside the
 * 8 MiB RAM window and beyond the ±32 MiB REL26 reach).
 *
 * Used only for link tests; the image is not runnable (`.far` is outside RAM).
 */

ENTRY(_start)

MEMORY
{
  ROM (rx)  : ORIGIN = 0xffffffff0000, LENGTH = 64K
  RAM (rwx) : ORIGIN = 0xffffff000000, LENGTH = 0x800000
}

PHDRS
{
  start PT_LOAD;
  text  PT_LOAD;
  data  PT_LOAD;
  far   PT_LOAD;
}

/* Runtime symbols used by minimal_crt0. */
__stack_top = 0xffffff7eff00;
__exit_block = 0xffffff7e0000;

SECTIONS
{
  .text.start : ALIGN(4) {
    *(.text.start .text.start.*)
  } > ROM :start

  .text ORIGIN(RAM) + 0x10100 : ALIGN(4) {
    *(.text .text.*)
  } > RAM :text

  .rodata : ALIGN(8) {
    *(.rodata .rodata.*)
    *(.srodata .srodata.*)
  } > RAM :data

  .data : ALIGN(8) {
    *(.data .data.*)
    *(.sdata .sdata.*)
  } > RAM :data

  .bss : ALIGN(8) {
    __bss_start = .;
    *(.bss .bss.*)
    *(.sbss .sbss.*)
    *(COMMON)
    __bss_end = .;
  } > RAM :data

  /* Second code region: 64 MiB below .text (outside RAM and REL26 reach). */
  . = 0xFFFFFB000000;
  .far : ALIGN(4) {
    *(.far .far.*)
  } :far

  /DISCARD/ : {
    *(.note.GNU-stack)
  }
}
