/* tests_freestanding_tiny.lds — Kaiwu-Tiny contract application ELF (m13-qemu-002;
 * M19 Tiny geometry m19-testcases-002).
 *
 * Spec: spec/Kaiwu §6 "装载语义 — Kaiwu-Tiny" (0.4.7-rc): the crt is linked
 * together with the test program, the whole application lives in SRAM, and the
 * entry (raw and ELF) is the fixed 0xffff_ff00_2000 (`MAIN_SRAM_BASE + 0x2000`,
 * `kernel_reserved = 0`).  The fixed 8 KiB BootROM firmware is supplied
 * separately (bootrom-image); the host loader never places a PT_LOAD in the
 * BootROM or in hmon SRAM.
 *
 * Geometry comes from contracts/machine.yaml + tests/ee-tiny/runtime.yaml
 * (profile `tiny`):
 *   RAM : 0xffff_ff00_0000 .. 0xffff_ff03_ffff  (256 KiB, rwx)
 *
 * Fixed main-SRAM slots (spec/Kaiwu §6.2.1; runtime-written, not in the image):
 *   EXIT_BLOCK  = MAIN_SRAM_BASE + 0x0030  (16 B, code at +0x38)
 *   SIGNATURE   = MAIN_SRAM_BASE + 0x1000  (0x800; tests/inst result buffer)
 *   ENTRY       = MAIN_SRAM_BASE + 0x2000  (image_window = 0x2_0000)
 *   STACK       = MAIN_SRAM_BASE + 0x39000 (24 KiB, SP = +0x3F000)
 *   MemRAS      = MAIN_SRAM_BASE + 0x3F000 (4 KiB, MRPTR = +0x40000)
 *
 * The crt and the application share this one SRAM image; e_entry is the fixed
 * entry.  (The old crt-in-ROM variant `kernel_tiny.lds` was retired once all
 * its consumers — static-musl smoke, picolibc smoke, ELF e2e — were verified
 * against this script.)
 *
 * __heap_end = SP - 0x1000 is pinned by `tools/testcases/check_tests_index.py`.
 * With the 24 KiB stack reservation below SP that ceiling sits inside the
 * stack area; these images are static (no malloc/sbrk), so heap growth never
 * reaches it.  A dynamic-heap Tiny application needs its own layout decision.
 * Enabling MemRAS is left to the test harness: `ra0` (MRPTR) stays 0 =
 * disabled here.
 */

ENTRY(_start)

MEMORY
{
  RAM (rwx) : ORIGIN = 0xffffff000000, LENGTH = 0x40000
}

PHDRS
{
  image PT_LOAD FLAGS(7);
  data  PT_LOAD FLAGS(7);
}

__stack_top = 0xffffff03f000;
__exit_block = 0xffffff000030;
__heap_end = 0xffffff03e000;

SECTIONS
{
  /* Explicit address: lld's MEMORY regions pin un-addressed output sections
   * to the region origin, so the fixed entry is spelled on the section. */
  .text.start 0xffffff002000 : ALIGN(4) {
    *(.text.start .text.start.*)
  } > RAM :image

  .text : ALIGN(4) {
    *(.text .text.*)
  } > RAM :image

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

  ASSERT(SIZEOF(.text.start) == 0 || _start == 0xffffff002000,
         "tiny app: _start must be the fixed entry 0xffff_ff00_2000")
  /* The image window (spec/Kaiwu §6.2.1) caps the whole application. */
  ASSERT(SIZEOF(.text.start) + SIZEOF(.text) + SIZEOF(.rodata) +
         SIZEOF(.data) + SIZEOF(.bss) <= 0x20000,
         "tiny app: sections exceed the 128 KiB image window")
}
