/* mcmodel_far.lds -- far code-layout link script (LLVM-131t; ADR-0036 D1/D5).
 *
 * Same RAM base as tests/shared/linker/dadao.lds, but the `.far` output section is
 * placed 64 MiB above `.text` instead of in the 16 MiB RAM window.  The two
 * code regions are therefore 64 MiB apart: far beyond the +/-32 MiB reach of a
 * direct `call`/`jump` (R_DADAO_REL26, 24-bit word offset), so
 *
 *   * a `default` code-model image cannot encode the call at all (link error),
 *   * a `large` code-model image reaches it through a 48-bit absolute address
 *     materialization plus an indirect call.
 *
 * Used only for the link test; the image is not runnable (`.far` is outside
 * RAM by construction).
 */

ENTRY(_start)

PHDRS
{
  text PT_LOAD;
  data PT_LOAD;
  far  PT_LOAD;
}

SECTIONS
{
  . = 0xFC0000000000;

  .text : ALIGN(4) {
    *(.text .text.*)
  } :text

  .rodata : ALIGN(8) {
    *(.rodata .rodata.*)
    *(.srodata .srodata.*)
  } :data

  .data : ALIGN(8) {
    *(.data .data.*)
    *(.sdata .sdata.*)
  } :data

  .bss : ALIGN(8) {
    *(.bss .bss.*)
    *(.sbss .sbss.*)
    *(COMMON)
  } :data

  /* Second code region: 64 MiB above .text (beyond a REL26 reach). */
  . = 0xFC0004000000;
  .far : ALIGN(4) {
    *(.far .far.*)
  } :far

  /DISCARD/ : {
    *(.note.GNU-stack)
  }
}
