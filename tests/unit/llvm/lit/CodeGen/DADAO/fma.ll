;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-123t: fused multiply-add (contract-fp.md §fma = SimRISC-07 §2.5).
;   `fofma rfHA, rfHB, rfHC, rfHD` = rfHA <- rfHB * rfHC + rfHD   (f64, op 0x5F)
;   `ftfma ...`                                                    (f32, op 0x5E)
; One destination + three sources, ONE rounding.  ISD::FMA is exactly that, so
; the pattern maps 1:1 and there is no 2-address tie: neither the independent
; `llvm.fma(a,b,c)` form nor the loop accumulator form needs a copy.
;
; `llvm.fmuladd` reaches the same node through
; DADAOTargetLowering::isFMAFasterThanFMulAndFAdd (returning true); with the
; default false it would be split into fmul+fadd -- i.e. two roundings.  The
; loop cases below assert the fused form AND the absence of any `rf2rf`.
;
; `llvm.fma` must never be expanded into fmul+fadd: that double-rounds and is
; not `fma` semantics.  If a future subtarget switch turns the native FMA off,
; `llvm.fma` has to become a libm `fma` call instead.

declare double @llvm.fma.f64(double, double, double)
declare float @llvm.fma.f32(float, float, float)
declare double @llvm.fmuladd.f64(double, double, double)
declare float @llvm.fmuladd.f32(float, float, float)

; --- llvm.fma.f64: one fofma, three-address (no copy) ------------------------
; CHECK-LABEL: fma_f64:
; CHECK: fofma rf8, rf16, rf17, rf18
; CHECK-NOT: fofma
; CHECK-NOT: fomul
; CHECK-NOT: foadd
; CHECK-NOT: rf2rf
define double @fma_f64(double %a, double %b, double %c) {
  %r = call double @llvm.fma.f64(double %a, double %b, double %c)
  ret double %r
}

; --- llvm.fma.f32: one ftfma ------------------------------------------------
; CHECK-LABEL: fma_f32:
; CHECK: ftfma rf8, rf16, rf17, rf18
; CHECK-NOT: ftfma
; CHECK-NOT: ftmul
; CHECK-NOT: ftadd
; CHECK-NOT: rf2rf
define float @fma_f32(float %a, float %b, float %c) {
  %r = call float @llvm.fma.f32(float %a, float %b, float %c)
  ret float %r
}

; --- llvm.fmuladd.f64 in a phi-accumulator loop -----------------------------
; The addend is the accumulator itself, so the destination register IS the
; accumulator (`fofma rf8, rf16, rf17, rf8`): zero copies in the loop body.
; CHECK-LABEL: fmuladd_loop_f64:
; CHECK: rd2rf
; CHECK: fofma rf8, rf16, rf17, rf8
; CHECK-NOT: fofma
; CHECK-NOT: fomul
; CHECK-NOT: foadd
; CHECK-NOT: rf2rf
; CHECK-NOT: rb2rb
; CHECK-NOT: rd2rd
define double @fmuladd_loop_f64(double %a, double %b, i32 %n) {
entry:
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %i1, %loop ]
  %acc = phi double [ 0.0, %entry ], [ %m, %loop ]
  %m = call double @llvm.fmuladd.f64(double %a, double %b, double %acc)
  %i1 = add i32 %i, 1
  %c = icmp slt i32 %i1, %n
  br i1 %c, label %loop, label %exit
exit:
  ret double %m
}

; --- llvm.fmuladd.f32 in a phi-accumulator loop -----------------------------
; CHECK-LABEL: fmuladd_loop_f32:
; CHECK: ftfma rf8, rf16, rf17, rf8
; CHECK-NOT: ftfma
; CHECK-NOT: ftmul
; CHECK-NOT: ftadd
; CHECK-NOT: rf2rf
; CHECK-NOT: rb2rb
; CHECK-NOT: rd2rd
define float @fmuladd_loop_f32(float %a, float %b, i32 %n) {
entry:
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %i1, %loop ]
  %acc = phi float [ 0.0, %entry ], [ %m, %loop ]
  %m = call float @llvm.fmuladd.f32(float %a, float %b, float %acc)
  %i1 = add i32 %i, 1
  %c = icmp slt i32 %i1, %n
  br i1 %c, label %loop, label %exit
exit:
  ret float %m
}

; --- non-fused path stays available ------------------------------------------
; A plain `fmul` feeding a `fadd` without the `contract` fast-math flag must
; NOT be turned into an fma (no licence to fuse): the two instructions remain.
; CHECK-LABEL: mul_add_no_contract:
; CHECK: fomul
; CHECK: foadd
; CHECK-NOT: fofma
define double @mul_add_no_contract(double %a, double %b, double %c) {
  %m = fmul double %a, %b
  %s = fadd double %m, %c
  ret double %s
}
