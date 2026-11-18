/*
 * semihost_pa_probe.lds — K1 gate probe: semihosting pointers are PAs
 * (ISS-450), built and run by `tools/linux/check_k1.py` (group K14).
 *
 * One PT_LOAD at the §6.3 kernel image region base (VA 0x0200_0010_0000),
 * 64 KiB aligned — the same shape as the K1 probe kernel
 * (`tests/ee-vast/probe_kernel_k0_vast.lds`).  The gate re-writes p_paddr to
 * `p_vaddr - BIAS` before handing the image to QEMU (the K1 ELF-VA-TO-PA
 * relation), so this script only fixes the VA and the footprint.
 *
 * The base is a literal because a linker script cannot take it from
 * `--defsym`; the gate therefore asserts `e_entry == contract kernel.start` on
 * the linked ELF, so a drift between this literal and the contract is a FAIL,
 * not a silently misplaced probe.
 */

ENTRY(_start)

MEMORY
{
  KVA (rwx) : ORIGIN = 0x020000100000, LENGTH = 63M
}

SECTIONS
{
  . = ORIGIN(KVA);

  .text : ALIGN(16) {
    *(.text .text.*)
    *(.rodata .rodata.*)
  } > KVA

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }

  ASSERT(SIZEOF(.text) <= 0x10000, "semihost PA probe exceeds one 64 KiB page")
}
