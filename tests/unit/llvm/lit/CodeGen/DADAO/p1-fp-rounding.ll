;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-125t (M9; contract-fp.md §roundint = SimRISC-07 §2.3): roundToIntegral.
; Every rounding intrinsic lowers to exactly ONE `fornd rfHB, rfHC, immu6` --
; no libcall and no compare sequence.  `immu6` is the six-way one-hot rounding
; mode (NOT an element count):
;
;   0x01 TiesToEven      -> llvm.roundeven   ties to the even neighbour
;   0x02 TiesToAway      -> llvm.round       ties away from zero
;   0x04 TowardZero      -> llvm.trunc
;   0x08 TowardPositive  -> llvm.ceil
;   0x10 TowardNegative  -> llvm.floor
;   0x20 Exact (dynamic) -> llvm.rint / llvm.nearbyint   (reads rf0[33:32])
;
; The tie cases pin the TiesToEven vs TiesToAway split: 2.5 -> 2.0 (roundeven)
; but 2.5 -> 3.0 (round), and -2.5 -> -2.0 (roundeven) but -2.5 -> -3.0
; (round).  Each function is named after the input it is read with, so a swap
; of the 0x01/0x02 patterns makes the corresponding imm check fail.
;
; KNOWN DEVIATION (SPEC-161t; contract-fp.md §roundint): the ISA has no
; nearbyint variant that suppresses the inexact status bit, so llvm.nearbyint
; takes the dynamic mode 0x20 exactly like llvm.rint: the value is identical,
; but NX (rf0[4]) may be set.  Non-strict LLVM marks both intrinsics
; IntrNoMem+IntrSpeculatable, so the flag is not observable, and these tests
; pin the instruction + imm only -- they deliberately do NOT assert NX.
;
; `fornd` is still `scope: excluded` in contracts/opcodes.yaml, so it traps
; with ILLI at run time until SPEC-162t flips it; these are CodeGen tests.

declare double @llvm.floor.f64(double)
declare double @llvm.ceil.f64(double)
declare double @llvm.trunc.f64(double)
declare double @llvm.round.f64(double)
declare double @llvm.roundeven.f64(double)
declare double @llvm.rint.f64(double)
declare double @llvm.nearbyint.f64(double)

define double @f_floor_neg2p5(double %x) {
; CHECK-LABEL: f_floor_neg2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 16
; CHECK-NOT: call
  %r = call double @llvm.floor.f64(double %x)
  ret double %r
}

define double @f_ceil_pos2p5(double %x) {
; CHECK-LABEL: f_ceil_pos2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 8
; CHECK-NOT: call
  %r = call double @llvm.ceil.f64(double %x)
  ret double %r
}

define double @f_trunc_pos2p5(double %x) {
; CHECK-LABEL: f_trunc_pos2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 4
; CHECK-NOT: call
  %r = call double @llvm.trunc.f64(double %x)
  ret double %r
}

define double @f_round_pos2p5(double %x) {
; CHECK-LABEL: f_round_pos2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 2
; CHECK-NOT: call
  %r = call double @llvm.round.f64(double %x)
  ret double %r
}

define double @f_roundeven_pos2p5(double %x) {
; CHECK-LABEL: f_roundeven_pos2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 1
; CHECK-NOT: call
  %r = call double @llvm.roundeven.f64(double %x)
  ret double %r
}

define double @f_rint_pos2p5(double %x) {
; CHECK-LABEL: f_rint_pos2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 32
; CHECK-NOT: call
  %r = call double @llvm.rint.f64(double %x)
  ret double %r
}

define double @f_nearbyint_pos2p5(double %x) {
; CHECK-LABEL: f_nearbyint_pos2p5:
; CHECK-COUNT-1: fornd rf{{[0-9]+}}, rf16, 32
; CHECK-NOT: call
  %r = call double @llvm.nearbyint.f64(double %x)
  ret double %r
}
