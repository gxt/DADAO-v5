; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-133t (M10) -- pin the *consumer* side of ADR-0037 D1.
;
; ADR-0037 D1: `cmp.{ut,uw,ub}` write -1 as 64-bit all-ones (0xFFFF_FFFF_FFFF_FFFF),
; 0 as 0 and +1 as 1 -- exactly the i64 {-1,0,1} value the backend already assumes
; (DADAOCodeGen.td: "The result is still the i64 {-1,0,1} value consumed by
; br.*/cs.*").  The ISA has no condition flags: `br.n`/`br.nn` test bit 63 and
; `cs.n`/`cs.p` test the sign / positivity of that value (contract-isa.md
; §6.5/§8.4).  So an unsigned `<` must be branched on with the *sign* family
; (br.n when the true block is reached by the branch, br.nn when the false block
; is) -- never with the zero/equality family (br.z/br.nz/br.eq/br.ne), which
; cannot distinguish -1 from +1.
;
; Before ADR-0037 the same text said the narrow `.u*` result was zero-extended by
; its width, i.e. "less" read as +0xFFFFFFFF, which would make `cmp.ut` followed
; by `br.n` take the wrong edge.  The backend used to compensate by
; sign-extending the compare result from bit W-1 (`ext.so`).  ADR-0037 D1 makes
; that compensation obsolete: `cmp.{ut,uw,ub}` already produce the 64-bit
; {-1,0,1}, so LLVM-134t removed the `ext.so` -- the checks below pin that no
; extension is emitted between the compare and its consumer.
;
; Selection is width-specific: i32 -> cmp.ut, i16 -> cmp.uw, i8 -> cmp.ub,
; i64 -> cmp.uo / cmp.ui (12-bit immediate).  A regression that widened a
; narrow compare to the 64-bit form (cmp.uo) would compare the undefined upper
; halves, so the width-specific opcodes are pinned with CHECK-NOT as well.

target triple = "dadao-unknown-elf"

; --- i32 unsigned `<`, true block reached by the branch: cmp.ut + br.n --------
; CHECK-LABEL: ult32_brn:
; CHECK:         cmp.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK-NOT:     cmp.st
; CHECK-NOT:     cmp.so
; CHECK-NOT:     cmp.ui
; CHECK-NOT:     cmp.uo
; CHECK:         br.n {rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT:     br.nz
; CHECK-NOT:     br.z
; CHECK-NOT:     br.eq
; CHECK-NOT:     br.ne
define i32 @ult32_brn(i32 %a, i32 %b) {
  %c = icmp ult i32 %a, %b
  br i1 %c, label %t, label %f
f:
  ret i32 0
t:
  ret i32 1
}

; --- same compare, false block laid out first: the inverted sign test br.nn ---
; (br.nn is `rc >= 0`; still the sign family, not br.nz, and the polarity is not
;  the plain br.n -- the CHECK-NOT sits between the cmp and the branch so a stray
;  opposite-polarity branch between them is caught too.)
; CHECK-LABEL: ult32_brnn:
; CHECK:         cmp.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK-NOT:     br.n {
; CHECK:         br.nn {rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT:     br.nz
; CHECK-NOT:     br.z
; CHECK-NOT:     br.eq
define i32 @ult32_brnn(i32 %a, i32 %b) {
  %c = icmp ult i32 %a, %b
  br i1 %c, label %t, label %f
t:
  ret i32 1
f:
  ret i32 0
}

; --- value form (icmp as a value): cs.n picks the true arm, not cs.z ---------
; CHECK-LABEL: ult32_val:
; CHECK:         cmp.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK:         cs.n {rd{{[0-9]+}}}?, rd{{[0-9]+}},
; CHECK-NOT:     cs.z
define i32 @ult32_val(i32 %a, i32 %b) {
  %c = icmp ult i32 %a, %b
  %r = zext i1 %c to i32
  ret i32 %r
}

; --- i16: cmp.uw (not cmp.ut / cmp.uo) + br.n --------------------------------
; CHECK-LABEL: ult16_brn:
; CHECK:         cmp.uw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK-NOT:     cmp.ut
; CHECK-NOT:     cmp.uo
; CHECK:         br.n {rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT:     br.nz
define i32 @ult16_brn(i16 %a, i16 %b) {
  %c = icmp ult i16 %a, %b
  br i1 %c, label %t, label %f
f:
  ret i32 0
t:
  ret i32 1
}

; --- i8: cmp.ub (not cmp.uw / cmp.uo) + br.n ---------------------------------
; CHECK-LABEL: ult8_brn:
; CHECK:         cmp.ub rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK-NOT:     cmp.uw
; CHECK-NOT:     cmp.uo
; CHECK:         br.n {rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT:     br.nz
define i32 @ult8_brn(i8 %a, i8 %b) {
  %c = icmp ult i8 %a, %b
  br i1 %c, label %t, label %f
f:
  ret i32 0
t:
  ret i32 1
}

; --- i64 unsigned `<`: cmp.uo + br.n (the 64-bit form never needs ext.so) -----
; CHECK-LABEL: ult64_brn:
; CHECK:         cmp.uo rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     cmp.ui
; CHECK:         br.n {rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT:     br.nz
; CHECK-NOT:     br.z
; CHECK-NOT:     br.eq
define i32 @ult64_brn(i64 %a, i64 %b) {
  %c = icmp ult i64 %a, %b
  br i1 %c, label %t, label %f
f:
  ret i32 0
t:
  ret i32 1
}

; --- i64 unsigned `<` against a 12-bit constant: cmp.ui + br.n ----------------
; CHECK-LABEL: ult64_imm_brn:
; CHECK:         cmp.ui rd{{[0-9]+}}, rd16, 5
; CHECK-NOT:     cmp.si
; CHECK-NOT:     cmp.uo
; CHECK:         br.n {rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT:     br.nz
define i32 @ult64_imm_brn(i64 %a) {
  %c = icmp ult i64 %a, 5
  br i1 %c, label %t, label %f
f:
  ret i32 0
t:
  ret i32 1
}

; --- control: the signed `<` of the same width must NOT pick cmp.ut ----------
; It is cmp.st + br.n as well; the compare opcode is what tells them apart.
; CHECK-LABEL: slt32_brn:
; CHECK:         cmp.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     cmp.ut
; CHECK-NOT:     cmp.uw
; CHECK:         br.n {rd{{[0-9]+}}}?, [rb0,
define i32 @slt32_brn(i32 %a, i32 %b) {
  %c = icmp slt i32 %a, %b
  br i1 %c, label %t, label %f
f:
  ret i32 0
t:
  ret i32 1
}
