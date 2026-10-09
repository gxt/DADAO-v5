; M6 L1 MC vector (TESTCASES-036t): ld/st symbol-offset relocations.
;
; `ld.*` / `st.*` (rrii) with a *symbol* offset is the reloc surface for
; global-variable access with a single in-place displacement.  Per
; contract-elf.md §2.2/§3.1 the assembler picks the type from the base
; register:
;   * base rb0        -> R_DADAO_REL12  (PC-relative, field = S + A - P)
;   * base rb1..rb63  -> R_DADAO_ABS12  (base-relative, field = S + A)
; Both use the same imms12 field (byte offset, signed 12-bit, -2048..+2047).
;
; DEFERRED (spec/Process-05 §3, the deferred-vector rule): the assembler does
; not yet emit a relocation kind for `ld/st [rbN, symbol]` (it aborts with
; "no PC-relative fixup kind for this symbol-operand instruction"); the fixup
; kind + linker support (R_DADAO_REL12 / R_DADAO_ABS12) is LLVM-065t, which is
; not yet done.  The vector is written down now so downstream has the intended
; contract, and is skipped via a REQUIRES feature that is deliberately never
; enabled in lit.cfg.py.  When LLVM-065t lands, drop the REQUIRES line and this
; becomes a normal lit test.  The expectations below are still re-derived from
; contracts/opcodes.yaml (encoding) and contract-elf.md §2.2 (reloc type) by
; tools/testcases/validate_m6_vectors.py.
;
; REQUIRES: dadao-ldst-symbol-reloc
;
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s --check-prefix=REL
;
; REL: Offset: 0x0
; REL: Type: R_DADAO_REL12 (4)
; REL: Symbol: target
; REL: Offset: 0x4
; REL: Type: R_DADAO_ABS12 (5)

	.text
	.globl	_start
_start:
	ld.o	rd8, [rb0, target]             ; @enc 20200000 @reloc R_DADAO_REL12
	st.o	rd8, [rb9, target]             ; @enc 21209000 @reloc R_DADAO_ABS12

	.section	.data
	.globl	target
target:
	.quad	0
