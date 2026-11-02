;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (ISS-188): `fptosi.sat` / `fptoui.sat` use the saturating hardware
; conversions.  contract-fp.md §3: NaN/Inf/out-of-range return the saturated
; extreme and raise NV -- which is the intrinsic's semantics except that
; LangRef requires NaN -> 0, so the lowering adds one NaN test + cs.* select.
;
;   i64: fo2io (signed) / fo2uo (unsigned)
;   i32: fo2it / fo2ut (+ the i32 truncation)
;   f32: ft2io / ft2uo / ...
; Each conversion is exactly one instruction; the NaN fixup is the standard
; FP-compare result handling (foqcmp + cmp.si + cs.p -> 0), no libcall.
;
; i8/i16 results have no hardware saturation width and keep the generic
; (libcall-free) expansion -- nothing is silently truncated.

declare i64 @llvm.fptosi.sat.i64.f64(double)
declare i64 @llvm.fptoui.sat.i64.f64(double)
declare i32 @llvm.fptosi.sat.i32.f64(double)
declare i32 @llvm.fptoui.sat.i32.f64(double)
declare i64 @llvm.fptosi.sat.i64.f32(float)
declare i8 @llvm.fptosi.sat.i8.f64(double)

define i64 @sat_signed64(double %x) {
; CHECK-LABEL: sat_signed64:
; CHECK-COUNT-1: fo2io
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %r = call i64 @llvm.fptosi.sat.i64.f64(double %x)
  ret i64 %r
}

define i64 @sat_unsigned64(double %x) {
; CHECK-LABEL: sat_unsigned64:
; CHECK-COUNT-1: fo2uo
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %r = call i64 @llvm.fptoui.sat.i64.f64(double %x)
  ret i64 %r
}

define i32 @sat_signed32(double %x) {
; CHECK-LABEL: sat_signed32:
; CHECK-COUNT-1: fo2it
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %r = call i32 @llvm.fptosi.sat.i32.f64(double %x)
  ret i32 %r
}

define i32 @sat_unsigned32(double %x) {
; CHECK-LABEL: sat_unsigned32:
; CHECK-COUNT-1: fo2ut
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %r = call i32 @llvm.fptoui.sat.i32.f64(double %x)
  ret i32 %r
}

define i64 @sat_signed64_f32(float %x) {
; CHECK-LABEL: sat_signed64_f32:
; CHECK-COUNT-1: ft2io
; CHECK-COUNT-1: ftqcmp
; CHECK-NOT:     call
  %r = call i64 @llvm.fptosi.sat.i64.f32(float %x)
  ret i64 %r
}

; No 8-bit saturating instruction: the generic expansion is used and stays
; libcall-free.
define i8 @sat_signed8(double %x) {
; CHECK-LABEL: sat_signed8:
; CHECK-NOT:     call
  %r = call i8 @llvm.fptosi.sat.i8.f64(double %x)
  ret i8 %r
}
