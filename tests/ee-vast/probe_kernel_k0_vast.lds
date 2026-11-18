/*
 * probe_kernel.lds — m14-qemu-001 K1 minimal kernel probe
 *
 * One PT_LOAD at the §6.3 kernel image region base (VA
 * 0x0200_0010_0000), 64 KiB aligned.  The loader re-writes p_paddr to
 * p_vaddr - 2 TiB (the K1 ELF-VA-TO-PA relation) before handing the image to
 * QEMU, so the link script only fixes the VA and the footprint.
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

  ASSERT(SIZEOF(.text) <= 0x10000, "k0 probe kernel exceeds one 64 KiB page")
}
