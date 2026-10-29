;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-140t: the "extend of narrow `sub 0, x`" ISel special case (LLVM-127t,
; reshaped by LLVM-138t) used to build the canonical `ext.*` node with result
; type i64 unconditionally and then ReplaceNode() it into an extend node whose
; own result type is *narrow* (e.g. `sext i16 -> i32`).  SelectionDAG::
; ReplaceAllUsesWith asserts on the type mismatch ("Cannot use this version of
; ReplaceAllUsesWith!"), so -O2 compilation aborted (McCat/18-imp L_canny.c,
; function dfilter).  The replacement must carry the extend node's own type,
; exactly like the TableGen patterns `(i32 (sext (i16 GPRD)))` -> ext_so_orri.
;
; Every function below has a narrow extend result (i32 or i16) and a live use,
; i.e. it would abort before the fix.  The instruction sequence is checked too:
; `sub.s* rd, rd0, rd` followed by the extend in the requested direction.
;
; The i64-result form (pre-existing path, m6-not-neg.ll) is kept as a control.

; CHECK-LABEL: sext_neg16_i32:
; CHECK:         ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 15
; CHECK-NEXT:    sub.sw {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.so {{rd[0-9]+}}, {{rd[0-9]+}}, 15
define i32 @sext_neg16_i32(i32 %div) {
  %t = trunc i32 %div to i16
  %n = sub i16 0, %t
  %e = sext i16 %n to i32
  %c = icmp slt i32 %div, %e
  %r = zext i1 %c to i32
  ret i32 %r
}

; CHECK-LABEL: zext_neg16_i32:
; CHECK:         ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 15
; CHECK-NEXT:    sub.sw {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 15
define i32 @zext_neg16_i32(i32 %div) {
  %t = trunc i32 %div to i16
  %n = sub i16 0, %t
  %e = zext i16 %n to i32
  %c = icmp slt i32 %div, %e
  %r = zext i1 %c to i32
  ret i32 %r
}

; CHECK-LABEL: sext_neg16_i32_ret:
; CHECK:         sub.sw {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.so {{rd[0-9]+}}, {{rd[0-9]+}}, 15
define i32 @sext_neg16_i32_ret(i16 %x) {
  %n = sub i16 0, %x
  %e = sext i16 %n to i32
  ret i32 %e
}

; CHECK-LABEL: sext_neg8_i16:
; CHECK:         ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 7
; CHECK-NEXT:    sub.sb {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.so {{rd[0-9]+}}, {{rd[0-9]+}}, 7
define i16 @sext_neg8_i16(i16 %div) {
  %t = trunc i16 %div to i8
  %n = sub i8 0, %t
  %e = sext i8 %n to i16
  ret i16 %e
}

; CHECK-LABEL: sext_neg8_i32:
; CHECK:         ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 7
; CHECK-NEXT:    sub.sb {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.so {{rd[0-9]+}}, {{rd[0-9]+}}, 7
define i32 @sext_neg8_i32(i32 %div) {
  %t = trunc i32 %div to i8
  %n = sub i8 0, %t
  %e = sext i8 %n to i32
  %c = icmp slt i32 %div, %e
  %r = zext i1 %c to i32
  ret i32 %r
}

; CHECK-LABEL: zext_neg8_i32:
; CHECK:         ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 7
; CHECK-NEXT:    sub.sb {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.uo {{rd[0-9]+}}, {{rd[0-9]+}}, 7
define i32 @zext_neg8_i32(i32 %div) {
  %t = trunc i32 %div to i8
  %n = sub i8 0, %t
  %e = zext i8 %n to i32
  %c = icmp ult i32 %div, %e
  %r = zext i1 %c to i32
  ret i32 %r
}

; Control: i64 result (the pre-existing, already-covered path).
; CHECK-LABEL: sext_neg16_i64:
; CHECK:         sub.sw {{rd[0-9]+}}, rd0, {{rd[0-9]+}}
; CHECK-NEXT:    ext.so {{rd[0-9]+}}, {{rd[0-9]+}}, 15
define i64 @sext_neg16_i64(i16 %x) {
  %n = sub i16 0, %x
  %e = sext i16 %n to i64
  ret i64 %e
}
