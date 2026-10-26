;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-062t / ISS-159: the backend must lower IR `not`/`neg` through the real
; instructions rather than `xor.o` + a materialized constant or `sub.uo` +
; `ext.so`:
;   * `xor x, -1` (i64)   -> `xnor.o rd, rc, rd0`        (contract-isa.md §6.3)
;   * `sub 0, x`   (i64)  -> `sub.so {rd0, rd}, rd0, rc` (§6.6)
;   * `neg iN` (narrow)   -> `sub.sb/sw/st rd, rd0, rc`  (§10.6/§11.6/§12.6)
;
; Since LLVM-127t the narrow i8/i16/i32 types are legal, so `neg iN` is a real
; iN subtraction (selected as the one-instruction `sub.s*`) and the following
; `sext iN to i64` is a separate `ext.so` -- the two instructions together are
; exactly the sign-extended i64 result.
;
; CHECK-LABEL: fnot:
; CHECK:         xnor.o rd8, rd16, rd0
define i64 @fnot(i64 %x) {
  %r = xor i64 %x, -1
  ret i64 %r
}

; CHECK-LABEL: fneg:
; CHECK:         sub.so {rd0, rd8}, rd0, rd16
define i64 @fneg(i64 %x) {
  %r = sub i64 0, %x
  ret i64 %r
}

; CHECK-LABEL: n8:
; CHECK:         sub.sb rd{{[0-9]+}}, rd0, rd16
; CHECK-NEXT:    ext.so rd8, rd{{[0-9]+}}, 7
define i64 @n8(i8 %x) {
  %n = sub i8 0, %x
  %e = sext i8 %n to i64
  ret i64 %e
}

; CHECK-LABEL: n16:
; CHECK:         sub.sw rd{{[0-9]+}}, rd0, rd16
; CHECK-NEXT:    ext.so rd8, rd{{[0-9]+}}, 15
define i64 @n16(i16 %x) {
  %n = sub i16 0, %x
  %e = sext i16 %n to i64
  ret i64 %e
}

; CHECK-LABEL: n32:
; CHECK:         sub.st rd{{[0-9]+}}, rd0, rd16
; CHECK-NEXT:    ext.so rd8, rd{{[0-9]+}}, 31
define i64 @n32(i32 %x) {
  %n = sub i32 0, %x
  %e = sext i32 %n to i64
  ret i64 %e
}
