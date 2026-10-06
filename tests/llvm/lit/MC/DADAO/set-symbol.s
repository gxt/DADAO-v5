; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_readobj --sections %t | %FileCheck %s --check-prefix=SEC
; RUN: %llvm_readobj -r %t | %FileCheck %s --check-prefix=REL
; RUN: %llvm_readobj -r %t | %FileCheck %s --check-prefix=NOSYM
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ

; `set.rd`/`set.rb` symbol / relocatable operands (ADR-0013 D11;
; ADR-0019 D4/D5).  A symbol is materialized as a fixed 3-wyde slice sequence
; (wp2/wp1/wp0) carrying one R_DADAO_ABS48 relocation per instruction; an
; assemble-time-constant expression (here a `.set` symbolic constant) takes
; the minimal-instruction path and produces no relocation.
;
; NOSYM-NOT: localimm

; SEC: Name: .rela.text
; SEC: Type: SHT_RELA (0x4)

; REL: R_DADAO_ABS48 ext 0x0
; REL: R_DADAO_ABS48 ext 0x0
; REL: R_DADAO_ABS48 ext 0x0
; REL: R_DADAO_ABS48 ext2 0x0
; REL: R_DADAO_ABS48 ext2 0x0
; REL: R_DADAO_ABS48 ext2 0x0

	.text
	.globl	_start
_start:
	.set	localimm, 0x1234ABCD
	set.rd	rd1, ext
	set.rb	rb1, ext2
	set.rd	rd2, localimm
	set.rd	rd3, 0x1234ABCD

	.section	.data
	.globl	ext
ext:
	.quad	0
	.globl	ext2
ext2:
	.quad	0

; set.rd rd1, ext -> set.zw rd1, wp2, 0x0 ; or.w rd1, wp1, 0x0 ; or.w rd1, wp0, 0x0
; (0x4C060000, 0x48050000, 0x48040000); the immediates are relocated.
; OBJ: {{[0-9a-f]+:}} 4c 06 00 00{{.*}}set.zw{{.*}}rd1, wp2, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 48 05 00 00{{.*}}or.w{{.*}}rd1, wp1, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 48 04 00 00{{.*}}or.w{{.*}}rd1, wp0, 0x0
; set.rb rb1, ext2 -> set.zw rb1, wp2 ; or.w rb1, wp1 ; or.w rb1, wp0
; (0x4E060000, 0x4A050000, 0x4A040000)
; OBJ-NEXT: {{[0-9a-f]+:}} 4e 06 00 00{{.*}}set.zw{{.*}}rb1, wp2, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 05 00 00{{.*}}or.w{{.*}}rb1, wp1, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 04 00 00{{.*}}or.w{{.*}}rb1, wp0, 0x0
; set.rd rd2, localimm -> minimal: set.zw rd2, wp1, 0x1234 ; or.w rd2, wp0, 0xabcd
; (0x4C091234, 0x4808ABCD)
; OBJ-NEXT: {{[0-9a-f]+:}} 4c 09 12 34{{.*}}set.zw{{.*}}rd2, wp1, 0x1234
; OBJ-NEXT: {{[0-9a-f]+:}} 48 08 ab cd{{.*}}or.w{{.*}}rd2, wp0, 0xabcd
; set.rd rd3, 0x1234ABCD -> minimal (0x4C0D1234, 0x480CABCD)
; OBJ-NEXT: {{[0-9a-f]+:}} 4c 0d 12 34{{.*}}set.zw{{.*}}rd3, wp1, 0x1234
; OBJ-NEXT: {{[0-9a-f]+:}} 48 0c ab cd{{.*}}or.w{{.*}}rd3, wp0, 0xabcd
