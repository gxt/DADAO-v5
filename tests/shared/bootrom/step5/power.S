@@ power.S — DADAO-v5 step5 BootROM power stage + shared boot helpers
@@ (INTEG-046t; ADR-0043 D1/D2/D3/D8/D14).
@@
@@ This file is linked at the reset window 0xffff_ffff_0000 (the last 64 KiB of
@@ the 256 KiB BootROM at 0xffff_fffc_0000) and is the only code the CPU runs
@@ at reset (cfx_power / cfxha 63 / hypv).  It contains:
@@
@@   * the power stage proper (offset 0): initialise rbsp, validate the image
@@     index table, load the hmon ELF into hmon SRAM, program hmon's H-mode
@@     vector/switch mode and trap into it; park on return (poison + self loop);
@@   * rom_validate_table (fixed offset 0x2000): shared table validator/lookup;
@@   * elf_loader         (fixed offset 0x2400): shared ELF validator/loader.
@@
@@ hmon calls the two shared routines at their absolute ROM addresses
@@ (0xffff_fffc_2000 / 0xffff_fffc_2400), so the loader exists exactly once
@@ even though both power and hmon use it.
@@
@@ Register convention of the shared routines (documented in README.md):
@@   rom_validate_table: rd1 = requested type
@@                       -> rd8 = 0 / 0xB1 / 0xB2 / 0xB6,
@@                          rd2 = offset, rd3 = size, rd4 = flags
@@   elf_loader:         rd2 = file offset, rd3 = size, rb2 = target base,
@@                       rd4 = flags
@@                       -> rd8 = 0 / 0xB3 / 0xB4 / 0xB5, rd5 = e_entry
@@
@@ The image index table format is the task's interface spec (§1): big-endian
@@ 16-byte header + 32-byte entries.  ELF checks are §2.  Failure codes are §5.

	.macro	LD64 rd, w0, w1, w2, w3
	set.zw	\rd, wp0, \w0
	.if \w1 != 0
	or.w	\rd, wp1, \w1
	.endif
	.if \w2 != 0
	or.w	\rd, wp2, \w2
	.endif
	.if \w3 != 0
	or.w	\rd, wp3, \w3
	.endif
	.endm

	.text
	.globl	_start

_start:
	@@ power has no stack requirement, but the handoff contract sets rbsp.
	LD64	rb1, 0xfff0, 0x00ff, 0xfc00, 0x0000	@@ RAM top - 16

	@@ RAM marker (PA 0x10000, outside the first page table) so the probe can
	@@ prove the power stage ran.  "POWE" = 0x504f5745.
	LD64	rb4, 0x0000, 0x0001, 0xfc00, 0x0000
	LD64	rd6, 0x5745, 0x504f, 0x0000, 0x0000
	st.o	rd6, [rb4, 0]

	@@ Validate the table and look up the hmon entry (type 1).
	LD64	rd1, 0x0001, 0x0000, 0x0000, 0x0000
	LD64	rb9, 0x2000, 0xffff, 0xffff, 0x0000	@@ rom_validate_table
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, power_exit_code]

	@@ Load the hmon ELF into hmon SRAM (0x0fff_0000_0000).
	LD64	rb2, 0x0000, 0x0000, 0x0fff, 0x0000
	LD64	rb9, 0x2400, 0xffff, 0xffff, 0x0000	@@ elf_loader
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, power_exit_code]

	@@ cfx_hmon.hypv.excp_vector = hmon e_entry; switch_run_mode = hypv.
	cfx2rc	cfx_hmon, cg3, rc10, rd5
	LD64	rd6, 0x0003, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_hmon, cg3, rc8, rd6

	@@ power -> hmon handoff (ADR-0043 D8).  The immediate is <boot_magic>;
	@@ the builder keeps it equal to the image table's boot_magic field and
	@@ patches this instruction when --boot-magic overrides it.
	.globl	boot_magic_trap
boot_magic_trap:
	trap	cfx_hmon, 0x30001

power_park:
	@@ D14: power never resumes.  Poison word in RAM (0x...0f00) then
	@@ self-loop; the probe asserts the poison word stays 0.
	LD64	rb4, 0x0100, 0x0001, 0xfc00, 0x0000
	LD64	rd6, 0xbeef, 0xdead, 0x0000, 0x0000
	st.o	rd6, [rb4, 0]
power_spin:
	jump	[rb0, power_spin]

power_exit_code:
	@@ rd8 already holds the failure code; report it via SYS_EXIT.
	rd2rd	rd1, rd8, 1
	jump	[rb0, power_exit]

power_exit:
	@@ SYS_EXIT(rd1): argument block in RAM (power may access RAM: cfx63 self).
	LD64	rb16, 0x0d00, 0x0000, 0xfc00, 0x0000
	LD64	rd16, 0x0026, 0x0002, 0x0000, 0x0000
	st.o	rd16, [rb16, 0]
	st.o	rd1, [rb16, 8]
	LD64	rd16, 0x0018, 0x0000, 0x0000, 0x0000
	trap	cfx_umon, 0x3FF00
	swym	0

@@ ===================================================================
@@ rom_validate_table — validate the BootROM image index table and find one
@@ entry by type (fixed ROM offset 0x2000).
@@
@@ Header: magic 0x44424F54, version 1, count 2, reserved 0.  Every entry:
@@ type in {1,2}, flags bits[31:3] all zero.  The boot_magic field is not
@@ validated here: it is the handoff magic and is checked by the target stage
@@ (0xB7/0xB8), which is what makes a mismatched magic observable.
@@ ===================================================================
	.org	0x2000
	.globl	rom_validate_table
rom_validate_table:
	LD64	rb3, 0x0000, 0xfffc, 0xffff, 0x0000	@@ ROM base 0xffff_fffc_0000
	@@ header.magic
	ld.ut	rd6, [rb3, 0]
	LD64	rd7, 0x4f54, 0x4442, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, vt_b1]
	@@ header.version
	ld.uw	rd6, [rb3, 4]
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, vt_b1]
	@@ header.count == 2
	ld.uw	rd6, [rb3, 6]
	LD64	rd7, 0x0002, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, vt_b1]
	@@ header.reserved == 0
	ld.ut	rd6, [rb3, 12]
	br.nz	{rd6}?, [rb0, vt_b1]

	@@ entry pointer = ROM base + 16
	LD64	rd6, 0x0010, 0x0000, 0x0000, 0x0000
	add.o	rb9, rb3, rd6
	LD64	rd5, 0x0002, 0x0000, 0x0000, 0x0000	@@ count
	LD64	rd13, 0x0000, 0x0000, 0x0000, 0x0000	@@ found flag = 0
vt_loop:
	ld.ut	rd10, [rb9, 4]			@@ flags
	shr.uo	rd11, rd10, 3			@@ bits [31:3] must be 0
	br.nz	{rd11}?, [rb0, vt_b2]
	ld.ut	rd11, [rb9, 0]			@@ type
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd14, rd11, rd7
	br.z	{rd14}?, [rb0, vt_type_ok]
	LD64	rd7, 0x0002, 0x0000, 0x0000, 0x0000
	cmp.uo	rd14, rd11, rd7
	br.nz	{rd14}?, [rb0, vt_b2]		@@ reserved type
vt_type_ok:
	cmp.uo	rd14, rd11, rd1
	br.nz	{rd14}?, [rb0, vt_next]
	ld.o	rd2, [rb9, 8]			@@ offset
	ld.o	rd3, [rb9, 16]			@@ size
	rd2rd	rd4, rd10, 1			@@ flags
	LD64	rd13, 0x0001, 0x0000, 0x0000, 0x0000
vt_next:
	add.si	rb9, 32
	add.si	rd5, -1
	br.nz	{rd5}?, [rb0, vt_loop]
	br.z	{rd13}?, [rb0, vt_b6]
	LD64	rd8, 0x0000, 0x0000, 0x0000, 0x0000
	ret	rd0, 0

vt_b1:
	LD64	rd8, 0x00b1, 0x0000, 0x0000, 0x0000
	ret	rd0, 0
vt_b2:
	LD64	rd8, 0x00b2, 0x0000, 0x0000, 0x0000
	ret	rd0, 0
vt_b6:
	LD64	rd8, 0x00b6, 0x0000, 0x0000, 0x0000
	ret	rd0, 0

@@ ===================================================================
@@ elf_loader — validate and load one ELF image from the BootROM
@@ (fixed ROM offset 0x2400; shared by power and hmon).
@@
@@ Inputs : rd2 file offset (relative to the 256 KiB ROM base)
@@          rd3 file size, rb2 target SRAM base, rd4 flags
@@ Outputs: rd8 0 or 0xB3..0xB5, rd5 e_entry
@@
@@ flags: bit1 LOAD (must be 1; =0 is a table error at the caller level),
@@ bit2 VERIFY.  With VERIFY=0 only the magic, the 64 KiB size limit and the
@@ target-window bounds are enforced; the structural phdr parse (phentsize /
@@ phnum / table-in-file) is always required because the copy needs it.
@@ ===================================================================
	.org	0x2400
	.globl	elf_loader
elf_loader:
	LD64	rb3, 0x0000, 0xfffc, 0xffff, 0x0000	@@ ROM base
	LD64	rd1, 0x0000, 0x0000, 0x0000, 0x0000	@@ entry-found = 0

	@@ size must be <= 64 KiB (0xB3)
	LD64	rd7, 0x0000, 0x0001, 0x0000, 0x0000	@@ 0x0001_0000
	cmp.uo	rd9, rd3, rd7
	br.p	{rd9}?, [rb0, elf_b3]

	@@ rb4 = ELF file address = ROM base + offset
	add.o	rb4, rb3, rd2

	@@ EI_MAG (always)
	ld.ut	rd6, [rb4, 0]
	LD64	rd7, 0x4c46, 0x7f45, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]

	@@ LOAD flag (flags bit1).  0 means "validate only, do not copy".
	LD64	rb14, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd6, 0x0002, 0x0000, 0x0000, 0x0000
	and.o	rd7, rd4, rd6
	br.z	{rd7}?, [rb0, elf_load_flag_done]
	add.si	rb14, 1
elf_load_flag_done:

	@@ VERIFY flag -> rb13
	LD64	rd6, 0x0004, 0x0000, 0x0000, 0x0000
	and.o	rd7, rd4, rd6
	LD64	rb13, 0x0000, 0x0000, 0x0000, 0x0000
	br.z	{rd7}?, [rb0, elf_header_struct]
	add.si	rb13, 1

	@@ Full ELF header checks (EI_CLASS/EI_DATA/EI_VERSION/e_type/
	@@ e_machine/e_flags/e_ehsize/e_phentsize).
	ld.ub	rd6, [rb4, 4]
	LD64	rd7, 0x0002, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.ub	rd6, [rb4, 5]
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.ub	rd6, [rb4, 6]
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.uw	rd6, [rb4, 16]			@@ e_type == ET_EXEC
	LD64	rd7, 0x0002, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.uw	rd6, [rb4, 18]			@@ e_machine == 0x0DA0
	LD64	rd7, 0x0da0, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.ut	rd6, [rb4, 48]			@@ e_flags == 1
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.uw	rd6, [rb4, 52]			@@ e_ehsize == 64
	LD64	rd7, 0x0040, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]

elf_header_struct:
	@@ e_phentsize == 56, e_phnum >= 1, e_phoff + phnum*56 <= size
	ld.uw	rd6, [rb4, 54]
	LD64	rd7, 0x0038, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_b4]
	ld.uw	rd15, [rb4, 56]
	br.z	{rd15}?, [rb0, elf_b4]
	ld.o	rd9, [rb4, 32]			@@ e_phoff
	rd2rd	rd11, rd9, 1			@@ keep phoff (rd9 is reused below)
	rd2rb	rb10, rd9, 1
	@@ rb9 = phnum * 56 = n*8 + n*16 + n*32
	LD64	rb9, 0x0000, 0x0000, 0x0000, 0x0000
	shl.o	rd12, rd15, 3
	shl.o	rd13, rd15, 4
	shl.o	rd14, rd15, 5
	add.o	rb9, rb9, rd12
	add.o	rb9, rb9, rd13
	add.o	rb9, rb9, rd14
	rb2rd	rd12, rb9, 1
	add.o	rb10, rb10, rd12	@@ phoff + table size
	rb2rd	rd14, rb10, 1
	cmp.uo	rd9, rd14, rd3
	br.p	{rd9}?, [rb0, elf_b4]

	@@ rb5 = ELF base + phoff; rd5 = e_entry
	ld.o	rd5, [rb4, 24]
	add.o	rb5, rb4, rd11

	@@ Full path: e_entry % 4 == 0
	rb2rd	rd7, rb13, 1
	br.z	{rd7}?, [rb0, elf_ph_loop_entry]
	LD64	rd6, 0x0003, 0x0000, 0x0000, 0x0000
	and.o	rd7, rd5, rd6
	br.nz	{rd7}?, [rb0, elf_b5]

elf_ph_loop_entry:
	br.z	{rd15}?, [rb0, elf_ph_done]

elf_ph_loop:
	ld.ut	rd6, [rb5, 0]			@@ p_type
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, elf_ph_next]

	@@ reload the segment fields (also used by the copy below)
	ld.o	rd9, [rb5, 8]			@@ p_offset
	ld.o	rd10, [rb5, 16]			@@ p_vaddr
	ld.o	rd11, [rb5, 24]			@@ p_paddr
	ld.o	rd12, [rb5, 32]			@@ p_filesz
	ld.o	rd13, [rb5, 40]			@@ p_memsz

	@@ VERIFY=0 -> minimal checks only
	rb2rd	rd7, rb13, 1
	br.z	{rd7}?, [rb0, elf_min_checks]

	@@ p_filesz <= p_memsz
	cmp.uo	rd14, rd13, rd12
	br.n	{rd14}?, [rb0, elf_b5]
	@@ p_vaddr == p_paddr
	cmp.uo	rd14, rd10, rd11
	br.nz	{rd14}?, [rb0, elf_b5]
	@@ p_offset <= size and p_filesz <= size
	cmp.uo	rd14, rd9, rd3
	br.p	{rd14}?, [rb0, elf_b5]
	cmp.uo	rd14, rd12, rd3
	br.p	{rd14}?, [rb0, elf_b5]
	@@ p_offset + p_filesz <= size
	rd2rb	rb9, rd9, 1
	add.o	rb9, rb9, rd12
	rb2rd	rd14, rb9, 1
	cmp.uo	rd14, rd14, rd3
	br.p	{rd14}?, [rb0, elf_b5]
	@@ p_vaddr % 4 == 0
	LD64	rd6, 0x0003, 0x0000, 0x0000, 0x0000
	and.o	rd14, rd11, rd6
	br.nz	{rd14}?, [rb0, elf_b5]
	@@ p_memsz != 0
	br.z	{rd13}?, [rb0, elf_b5]

elf_min_checks:
	@@ p_filesz <= p_memsz (needed by the copy even in minimal mode)
	cmp.uo	rd14, rd13, rd12
	br.n	{rd14}?, [rb0, elf_b5]
	@@ p_offset/p_filesz inside the file
	cmp.uo	rd14, rd9, rd3
	br.p	{rd14}?, [rb0, elf_b5]
	cmp.uo	rd14, rd12, rd3
	br.p	{rd14}?, [rb0, elf_b5]
	rd2rb	rb9, rd9, 1
	add.o	rb9, rb9, rd12
	rb2rd	rd14, rb9, 1
	cmp.uo	rd14, rd14, rd3
	br.p	{rd14}?, [rb0, elf_b5]
	@@ p_memsz itself must fit the 64 KiB window (no 64-bit wrap)
	LD64	rd6, 0x0000, 0x0001, 0x0000, 0x0000
	cmp.uo	rd14, rd13, rd6
	br.p	{rd14}?, [rb0, elf_b5]
	@@ target window: base <= paddr && paddr + memsz <= base + 64 KiB
	rb2rd	rd6, rb2, 1		@@ base
	rd2rb	rb9, rd6, 1
	add.si	rb9, 0x10000
	rb2rd	rd6, rb9, 1		@@ limit
	cmp.uo	rd14, rd11, rd6
	br.p	{rd14}?, [rb0, elf_b5]	@@ paddr > limit
	rd2rb	rb9, rd11, 1
	add.o	rb9, rb9, rd13
	rb2rd	rd7, rb9, 1		@@ end
	cmp.uo	rd14, rd6, rd7
	br.n	{rd14}?, [rb0, elf_b5]	@@ limit < end

	@@ Full path: record whether e_entry lies in [paddr, paddr+p_memsz).
	@@ Use rd6 for the VERIFY flag: rd7 still holds the segment end.
	rb2rd	rd6, rb13, 1
	br.z	{rd6}?, [rb0, elf_load_seg]
	cmp.uo	rd14, rd5, rd11
	br.n	{rd14}?, [rb0, elf_load_seg]
	cmp.uo	rd14, rd7, rd5
	br.np	{rd14}?, [rb0, elf_load_seg]
	LD64	rd1, 0x0001, 0x0000, 0x0000, 0x0000

elf_load_seg:
	@@ LOAD=0: validate but do not copy (task §接口规范 1 flags).
	rb2rd	rd7, rb14, 1
	br.z	{rd7}?, [rb0, elf_ph_next]
	@@ src = ELF base + p_offset; src_end = src + p_filesz
	add.o	rb9, rb4, rd9
	add.o	rb10, rb9, rd12
	@@ dst = p_paddr; dst_end = dst + p_memsz
	rd2rb	rb11, rd11, 1
	add.o	rb12, rb11, rd13

elf_copy:
	rb2rd	rd14, rb10, 1
	rb2rd	rd7, rb9, 1
	cmp.uo	rd6, rd14, rd7
	br.z	{rd6}?, [rb0, elf_zero]
	ld.ub	rd6, [rb9, 0]
	st.b	rd6, [rb11, 0]
	add.si	rb9, 1
	add.si	rb11, 1
	jump	[rb0, elf_copy]

elf_zero:
	rb2rd	rd14, rb12, 1
	rb2rd	rd7, rb11, 1
	cmp.uo	rd6, rd14, rd7
	br.z	{rd6}?, [rb0, elf_ph_next]
	st.b	rd0, [rb11, 0]
	add.si	rb11, 1
	jump	[rb0, elf_zero]

elf_ph_next:
	add.si	rb5, 56
	add.si	rd15, -1
	br.nz	{rd15}?, [rb0, elf_ph_loop]

elf_ph_done:
	@@ With VERIFY=0 there is no entry-range requirement, but e_entry is
	@@ still returned for the caller's vector.
	rb2rd	rd7, rb13, 1
	br.z	{rd7}?, [rb0, elf_ok]
	br.z	{rd1}?, [rb0, elf_b5]
elf_ok:
	LD64	rd8, 0x0000, 0x0000, 0x0000, 0x0000
	ret	rd0, 0

elf_b3:
	LD64	rd8, 0x00b3, 0x0000, 0x0000, 0x0000
	ret	rd0, 0
elf_b4:
	LD64	rd8, 0x00b4, 0x0000, 0x0000, 0x0000
	ret	rd0, 0
elf_b5:
	LD64	rd8, 0x00b5, 0x0000, 0x0000, 0x0000
	ret	rd0, 0

@@ Power flat image ends here; the linker script asserts <= 64 KiB.
