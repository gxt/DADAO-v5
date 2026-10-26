;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-114t (ISS-283 remainder): the f128 math intrinsics used by the 12
; remaining picolibc libm/ld TUs lower to out-of-line libm calls.  LLVM-106t
; registered the arithmetic/comparison/convert libcalls; the math face was
; missing, so makeLibCall aborted with "unsupported library call operation".
;
; The seven symbols below are libm entry points (musl/picolibc `libc.a`), NOT
; compiler-rt builtins (ADR-0027 does not apply).  floor/rint/round/trunc/log
; are required by the observed TUs; sqrt/fma are latent (same unregistered
; RTLIB entries, proven with minimal IR).

define fp128 @f128_floor(fp128 %x) {
; CHECK-LABEL: f128_floor:
; CHECK: call [rb0, floorl]
  %r = call fp128 @llvm.floor.f128(fp128 %x)
  ret fp128 %r
}

define fp128 @f128_rint(fp128 %x) {
; CHECK-LABEL: f128_rint:
; CHECK: call [rb0, rintl]
  %r = call fp128 @llvm.rint.f128(fp128 %x)
  ret fp128 %r
}

define fp128 @f128_round(fp128 %x) {
; CHECK-LABEL: f128_round:
; CHECK: call [rb0, roundl]
  %r = call fp128 @llvm.round.f128(fp128 %x)
  ret fp128 %r
}

define fp128 @f128_trunc(fp128 %x) {
; CHECK-LABEL: f128_trunc:
; CHECK: call [rb0, truncl]
  %r = call fp128 @llvm.trunc.f128(fp128 %x)
  ret fp128 %r
}

define fp128 @f128_log(fp128 %x) {
; CHECK-LABEL: f128_log:
; CHECK: call [rb0, logl]
  %r = call fp128 @llvm.log.f128(fp128 %x)
  ret fp128 %r
}

define fp128 @f128_sqrt(fp128 %x) {
; CHECK-LABEL: f128_sqrt:
; CHECK: call [rb0, sqrtl]
  %r = call fp128 @llvm.sqrt.f128(fp128 %x)
  ret fp128 %r
}

define fp128 @f128_fma(fp128 %a, fp128 %b, fp128 %c) {
; CHECK-LABEL: f128_fma:
; CHECK: call [rb0, fmal]
  %r = call fp128 @llvm.fma.f128(fp128 %a, fp128 %b, fp128 %c)
  ret fp128 %r
}

declare fp128 @llvm.floor.f128(fp128)
declare fp128 @llvm.rint.f128(fp128)
declare fp128 @llvm.round.f128(fp128)
declare fp128 @llvm.trunc.f128(fp128)
declare fp128 @llvm.log.f128(fp128)
declare fp128 @llvm.sqrt.f128(fp128)
declare fp128 @llvm.fma.f128(fp128, fp128, fp128)
