/* dadao-node.lds — DADAO-v5 Machine-v5-Node ELF link script (TESTCASES-091t).
 *
 * Geometry comes from tests/shared/machine-profiles.yaml (profile `node`):
 *   RAM : 0x0000_0000_0000 .. 0x7fff_ffff  (2 GiB, rwx; VA=PA identity, PTW on)
 *   ROM : 0xffff_ffc0_0000 .. 0xffff_ffff_ffff (4 MiB, rx)
 *
 * Layout:
 *   * .text.start (minimal_crt0 `_start`) is linked at the profile entry
 *     (RAM + 1 MiB); .text follows it.  Node has no separate ROM stub.
 *   * common .rodata/.data/.bss + __bss_start/__bss_end symbols live in
 *     dadao-common.lds (INCLUDE below).
 */

ENTRY(_start)

MEMORY
{
  RAM (rwx) : ORIGIN = 0x000000000000, LENGTH = 0x80000000
  ROM (rx)  : ORIGIN = 0xffffffc00000, LENGTH = 0x400000
}

PHDRS
{
  start PT_LOAD;
  text  PT_LOAD;
  data  PT_LOAD;
  rom   PT_LOAD;
}

__stack_top = 0x7fff0000;
__exit_block = 0x7ffd0000;
__heap_end = 0x7ffef000;

SECTIONS
{
  .text.start ORIGIN(RAM) + 0x100000 : ALIGN(4) {
    *(.text.start .text.start.*)
  } > RAM :start

  .text : ALIGN(4) {
    *(.text .text.*)
  } > RAM :text

  INCLUDE dadao-common.lds

  .rom : ALIGN(4) {
    *(.rom .rom.*)
  } > ROM :rom

  ASSERT(_start == ORIGIN(RAM) + 0x100000,
         "node: _start must be the profile entry (RAM + 1 MiB)")
  ASSERT(SIZEOF(.text) + SIZEOF(.rodata) + SIZEOF(.data) + SIZEOF(.bss)
         <= LENGTH(RAM), "RAM sections exceed 2 GiB")
  ASSERT(SIZEOF(.rom) <= LENGTH(ROM), "ROM section exceeds 4 MiB")
}
