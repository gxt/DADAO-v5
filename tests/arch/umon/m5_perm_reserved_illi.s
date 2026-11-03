@@ m5_perm_reserved_illi.s — M5 L3 execution vector: reserved cfxha => ILLI (TESTCASES-033t).
@@
@@ Capability / permission counter-example: a general `trap` whose cfxha is a
@@ reserved code (6-14, 19-61) must fail with ILLI, redirected to the current-mode
@@ monitor (contract-see.md §3 "reserved cfxha (6-14, 19-61) 触发 ILLI";
@@ DADAO-12 §5; SimRISC-11 指令域与执行条件).  cfxha 7 is reserved (contract-cfx-aliases
@@ §1 lists only umon/jmon/smon/hmon/ptw/cache/hart/llc/pmem/time/uart/power).
@@
@@ TESTCASES-092t (§3/§4): the test body runs in hypv, whose current-mode
@@ monitor is cfx_hmon.  The fault is delivered to hmon, which records the cause
@@ in the profile's fault-record slot (FAULT_RECORD: +0 cause id, +8 cause ip;
@@ both are VAs under the identity page table, so the body can `ld.o` them) and
@@ then *resumes* at the instruction after the faulting one.  The vector reads
@@ the recorded cause and requires ILLI (1<<8).  No cross-cfx register read and
@@ no bootrom-installed user vector is assumed any more.
@@
@@ Expected: cause = ILLI (0x100); host $? = 0x50 (SYS_EXIT pass token).

@@ @m5 name=m5_perm_reserved_illi
@@ @m5 kind=permission
@@ @m5 rule=reserved_cfxha
@@ @m5 cause=ILLI
@@ @m5 op=trap cfx7, 0
@@ @m5 exit=0x50
@@ @m5 fail_exit=0xE1

	.include "machine.inc"

	.text
	.globl	_start
_start:
	@@ reserved cfxha (7) -> ILLI, delivered to cfx_hmon (current-mode monitor)
	trap	cfx7, 0
	@@ read back the cause the monitor recorded before resuming us
	LOAD_ADDR rb4, FAULT_RECORD
	ld.o	rd10, [rb4, 0]			@@ fault-record[0] = cause id
	set.zw	rd12, wp0, 0x0100		@@ ILLI = 1 << 8
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x50)
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0050
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0

fail:
	@@ wrong cause -> SYS_EXIT(0xE1)
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E1
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
