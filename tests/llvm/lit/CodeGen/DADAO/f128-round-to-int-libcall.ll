;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; Picolibc implements the long-double integer-rounding family in source files
; that Clang lowers to these intrinsics.  DADAO has no native f128 operations,
; so each must become the matching long-double libcall instead of aborting in
; the type legalizer with "unsupported library call operation".

declare i64 @llvm.lround.i64.f128(fp128)
declare i64 @llvm.llround.i64.f128(fp128)
declare i64 @llvm.lrint.i64.f128(fp128)
declare i64 @llvm.llrint.i64.f128(fp128)

define i64 @round_to_int(fp128 %x) {
; CHECK-LABEL: round_to_int:
; CHECK-DAG: call [rb0, lroundl]
; CHECK-DAG: call [rb0, llroundl]
; CHECK-DAG: call [rb0, lrintl]
; CHECK-DAG: call [rb0, llrintl]
  %a = call i64 @llvm.lround.i64.f128(fp128 %x)
  %b = call i64 @llvm.llround.i64.f128(fp128 %x)
  %c = call i64 @llvm.lrint.i64.f128(fp128 %x)
  %d = call i64 @llvm.llrint.i64.f128(fp128 %x)
  %ab = add i64 %a, %b
  %cd = add i64 %c, %d
  %sum = add i64 %ab, %cd
  ret i64 %sum
}
