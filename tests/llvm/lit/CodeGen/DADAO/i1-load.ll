;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-077t (M6, ISS-186): boolean (i1) loads.
;
; An i1 in memory occupies a whole byte.  The load-extension action for the i1
; memory type defaults to Legal, but the DADAO byte/wyde/tetra load patterns
; (DADAOCodeGen.td) have no i1 form, so a surviving `zextloadi1` / `sextloadi1`
; used to fail ISel with
;   LLVM ERROR: Cannot select: ... load<..., zext from i1>
; This is exactly the shape GlobalOpt's shrink-to-bool produces for
; aha-mont64 at -O2 (an `i1` global read through `load i1` + `zext`).  The
; i1 memory type is now promoted to i8, so the byte load `ld.ub` matches
; (contract-isa.md §3.1.1: `ld.ub rdha, rbhb, imms12` =
; zero_extend(mem8[rbhb + imms12])).  The expected instruction is derived from
; the ISA, not from the emitted text.
;
; Structure mirrored after the real crasher: an internal i1 global (the result
; of GlobalOpt's TryToShrinkGlobalToBoolean) read back and zero-extended.

; --- zext: the ISS-186 minimal reproduction (load i1 + zext) -----------------
; CHECK-LABEL: zext_bool_global:
; CHECK: ld.ub rd{{[0-9]+}}, [rb{{[0-9]+}}, {{[0-9]+}}]
define i64 @zext_bool_global() {
  %.b = load i1, ptr @g, align 8
  %r = select i1 %.b, i64 1, i64 0
  ret i64 %r
}

; --- zext from a pointer argument (same node, no global materialisation) -----
; CHECK-LABEL: zext_bool_ptr:
; CHECK: ld.ub rd{{[0-9]+}}, [rb{{[0-9]+}}, {{[0-9]+}}]
define i64 @zext_bool_ptr(ptr %p) {
  %.b = load i1, ptr %p, align 4
  %r = zext i1 %.b to i64
  ret i64 %r
}

; --- sext: the promoted `sextload i1` legalises to a byte load + a signed
;     bit-0 extension.  `ext.so rdhb, rdhc, hd` copies the low hd+1 bits and
;     sign-extends from bit hd (contract-isa.md §6.4.2); hd = 0 therefore
;     yields 0 / -1 from bit 0, i.e. a signed boolean.
; CHECK-LABEL: sext_bool:
; CHECK: ld.ub rd{{[0-9]+}}, [rb{{[0-9]+}}, {{[0-9]+}}]
; CHECK: ext.so rd{{[0-9]+}}, rd{{[0-9]+}}, 0
define i64 @sext_bool(ptr %p) {
  %.b = load i1, ptr %p
  %r = sext i1 %.b to i64
  ret i64 %r
}

; The internal i1 global that GlobalOpt creates for a shrink-to-bool variable.
@g = internal global i1 false, align 8
