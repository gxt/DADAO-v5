/* dadao-tiny.lds — DADAO-v5 Machine-v5-Tiny ELF link script (TESTCASES-091t).
 *
 * Geometry comes from tests/shared/machine-profiles.yaml (profile `tiny`):
 *   ROM : 0xffff_ffff_0000 .. 0xffff_ffff_ffff  (64 KiB, rx; crt startup stub)
 *   RAM : 0xffff_ff00_0000 .. 0xffff_ff7f_ffff  (8 MiB, rwx)
 *
 * Layout:
 *   * .text.start (minimal_crt0 `_start`) is linked at the ROM base, so
 *     e_entry == 0xffff_ffff_0000; the stub sets SP and jumps to the profile
 *     application entry.
 *   * .text/.rodata/.data/.bss start at the profile entry
 *     (RAM + 0x10100); the first 0x100 bytes of the raw -kernel window are
 *     reserved/zero, not part of the ELF sections.
 *   * __bss_start/__bss_end bracket .bss (minimal_crt0 clears it itself).
 *   * common sections/symbols live in dadao-common.lds (INCLUDE below).
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
}

__stack_top = 0xffffff7eff00;
__exit_block = 0xffffff7e0000;
__heap_end = 0xffffff7eef00;

SECTIONS
{
  .text.start : ALIGN(4) {
    *(.text.start .text.start.*)
  } > ROM :start

  .text ORIGIN(RAM) + 0x10100 : ALIGN(4) {
    *(.text .text.*)
  } > RAM :text

  INCLUDE dadao-common.lds

  /* Test assets (minimal_crt0/picolibc) put _start in .text.start at ROM.
   * Legacy musl crt1.o keeps _start in .text at the application entry; it is
   * intentionally not migrated (user ruling: musl crt1 untouched). */
  ASSERT(_start == ORIGIN(ROM) || _start == ORIGIN(RAM) + 0x10100,
         "tiny: _start must be the ROM crt stub or the application entry")
  ASSERT(SIZEOF(.text.start) <= LENGTH(ROM), "crt stub exceeds 64 KiB ROM")
  ASSERT(SIZEOF(.text) + SIZEOF(.rodata) + SIZEOF(.data) + SIZEOF(.bss)
         <= LENGTH(RAM) - 0x10100, "RAM sections exceed tiny RAM")
}
