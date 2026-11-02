;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-113t (ISS-283): the four 128-bit integer <-> binary128 conversions are
; out-of-line compiler-rt TF libcalls.  LLVM-106t registered the i32/i64 forms
; only; picolibc's strtold.c reaches `uitofp i128 -> fp128` and aborts with
; "unsupported library call operation".  The entry points checked here are the
; compiler-rt `GENERIC_TF_SOURCES` names (NOT read back from the backend):
;   RTLIB::SINTTOFP_I128_F128 -> __floattitf
;   RTLIB::UINTTOFP_I128_F128 -> __floatuntitf
;   RTLIB::FPTOSINT_F128_I128 -> __fixtfti
;   RTLIB::FPTOUINT_F128_I128 -> __fixunstfti
;
; The i128 value travels as two 64-bit halves (ADR-0030/ADR-0031); each
; conversion is therefore one call taking/returning the pair.

define fp128 @i128_to_f128(i128 %i) {
; CHECK-LABEL: i128_to_f128:
; CHECK: call [rb0, __floattitf]
  %r = sitofp i128 %i to fp128
  ret fp128 %r
}

define fp128 @u128_to_f128(i128 %i) {
; CHECK-LABEL: u128_to_f128:
; CHECK: call [rb0, __floatuntitf]
  %r = uitofp i128 %i to fp128
  ret fp128 %r
}

define i128 @f128_to_i128(fp128 %f) {
; CHECK-LABEL: f128_to_i128:
; CHECK: call [rb0, __fixtfti]
  %r = fptosi fp128 %f to i128
  ret i128 %r
}

define i128 @f128_to_u128(fp128 %f) {
; CHECK-LABEL: f128_to_u128:
; CHECK: call [rb0, __fixunstfti]
  %r = fptoui fp128 %f to i128
  ret i128 %r
}
