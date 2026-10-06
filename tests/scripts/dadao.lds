/* dadao.lds — DADAO M4 ELF link script (contract-elf.md §5, ADR-0004 §D1/§D2).
 *
 * Memory geometry (ADR-0004 §D1):
 *   RAM : 0xffff_0000_0000 .. 0xffff_00ff_ffff  (16 MiB, rwx)
 *   ROM : 0xffff_ffff_0000 .. 0xffff_ffff_ffff  (64 KiB, rx)
 *
 * Layout:
 *   * .text starts at the RAM base; section order .text -> .rodata -> .data
 *     -> .bss (contract-elf.md §5.1).
 *   * minimum alignment: .text 4 B, .rodata/.data/.bss 8 B (contract-elf.md §5.1).
 *   * entry symbol _start.
 *   * FILEHDR PHDRS: the ELF header + program headers are included in the
 *     first PT_LOAD so that the loadable text image starts at file offset 0
 *     (contract-elf.md §6.1.2).
 *   * segment permissions: .text RX, .rodata/.data/.bss RW, .rom RX.
 *
 * Over-size is a link-time error (contract-elf.md §3.2 / §6.1.2,
 * ADR-0004 §D2.3): the MEMORY regions reject an output section that does not
 * fit, and the ASSERTs below make the constraints explicit (no silent wrap /
 * truncation / spill outside a region).
 */

ENTRY(_start)

MEMORY
{
  RAM (rwx) : ORIGIN = 0xffff00000000, LENGTH = 16M
  ROM (rx)  : ORIGIN = 0xffffffff0000, LENGTH = 64K
}

PHDRS
{
  text PT_LOAD FILEHDR PHDRS;
  data PT_LOAD;
  rom  PT_LOAD;
}

SECTIONS
{
  . = ORIGIN(RAM);

  .text : ALIGN(4) {
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
    *(.bss .bss.*)
    *(.sbss .sbss.*)
    *(COMMON)
  } > RAM :data

  .rom : ALIGN(4) {
    *(.rom .rom.*)
  } > ROM :rom

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(SIZEOF(.text) + SIZEOF(.rodata) + SIZEOF(.data) + SIZEOF(.bss)
         <= LENGTH(RAM), "RAM sections exceed 16 MiB")
  ASSERT(SIZEOF(.rom) <= LENGTH(ROM), "ROM section exceeds 64 KiB")
}
