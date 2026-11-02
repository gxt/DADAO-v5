/* dadao-common.lds — shared section/symbol fragment for dadao-{tiny,node}.lds.
 *
 * Included from inside the wrapper's SECTIONS block (lld: pass
 * `-L tests/shared/linker`).  The wrapper must provide:
 *   MEMORY: RAM (rwx)
 *   PHDRS : data PT_LOAD
 *   symbols: __stack_top, __exit_block, __heap_end
 * and the profile-specific `.text.start` / `.text` sections before the INCLUDE.
 *
 * Keeping .rodata/.data/.bss + __bss_start/__bss_end + heap symbols here stops
 * the Tiny and Node scripts from drifting.
 */

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

  PROVIDE(__end = .);
  PROVIDE(__heap_start = __end);
  PROVIDE(__heap_size = __heap_end - __heap_start);

  /DISCARD/ : {
    *(.note.GNU-stack)
  }
