/*
 * bootrom.lds — DADAO-v5 SEE bootrom link script (QEMU-047t, M5).
 *
 * Geometry (ADR-0004 D1 / D2.3 path B):
 *   boot ROM : 0xffff_ffff_0000 .. 0xffff_ffff_ffff  (64 KiB, rx)
 *              = cfx_power_hypv_excp_vector (spec/DADAO-12 §2.1) and the
 *              QEMU `-bios` load base of the bootrom (ADR-0004 R1).
 *
 * Layout:
 *   * .text starts at the ROM base, so the ELF entry (_start) is the ROM base
 *     — the same address the CPU resets to (rb0 = reset vector, ADR-0004 D2.1),
 *     and the same address `-bios` loads the flat image to.
 *   * minimum alignment .text 4 B (one 32-bit instruction, contract-elf §5.1).
 *   * the ELF header / program headers stay in the file only; the flat
 *     `-bios` image is the extracted ROM bytes at offset 0 (contract-elf
 *     §6.1.1-style objcopy of the linked ELF).
 *   * over-size is a link-time error: the MEMORY region and the ASSERT below
 *     reject a bootrom that does not fit the 64 KiB ROM (ADR-0004 D2.3 —
 *     ROM blob > 64 KiB is a load-stage error).
 */

ENTRY(_start)

MEMORY
{
  ROM (rx) : ORIGIN = 0xffffffff0000, LENGTH = 64K
}

SECTIONS
{
  . = ORIGIN(ROM);

  .text : ALIGN(4) {
    *(.text .text.*)
    *(.rodata .rodata.*)
  } > ROM

  /DISCARD/ : {
    *(.note.GNU-stack)
  }

  ASSERT(SIZEOF(.text) <= LENGTH(ROM), "bootrom exceeds the 64 KiB boot ROM")
}
