;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-125t (M9): f32 counterpart of p1-fp-rounding.ll.  The f32 rounding
; intrinsics select `ftrnd` (tetra float, p = 24) with the same one-hot immu6
; mode encoding as `fornd` (contract-fp.md §roundint = SimRISC-07 §2.3):
;
;   0x01 TiesToEven      -> llvm.roundeven
;   0x02 TiesToAway      -> llvm.round
;   0x04 TowardZero      -> llvm.trunc
;   0x08 TowardPositive  -> llvm.ceil
;   0x10 TowardNegative  -> llvm.floor
;   0x20 Exact (dynamic) -> llvm.rint / llvm.nearbyint   (reads rf0[33:32])
;
; Exactly one instruction per intrinsic, no libcall (the previous lowering
; called floorf/ceilf/truncf/roundf/rintf/nearbyintf).  Same known deviation
; as the f64 test: nearbyint uses 0x20 and may set NX; the imm-only checks
; below do not assert NX.  `ftrnd` is still `scope: excluded` (ILLI at run
; time) until SPEC-162t.

declare float @llvm.floor.f32(float)
declare float @llvm.ceil.f32(float)
declare float @llvm.trunc.f32(float)
declare float @llvm.round.f32(float)
declare float @llvm.roundeven.f32(float)
declare float @llvm.rint.f32(float)
declare float @llvm.nearbyint.f32(float)

define float @f_floor_neg2p5(float %x) {
; CHECK-LABEL: f_floor_neg2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 16
; CHECK-NOT: call
  %r = call float @llvm.floor.f32(float %x)
  ret float %r
}

define float @f_ceil_pos2p5(float %x) {
; CHECK-LABEL: f_ceil_pos2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 8
; CHECK-NOT: call
  %r = call float @llvm.ceil.f32(float %x)
  ret float %r
}

define float @f_trunc_pos2p5(float %x) {
; CHECK-LABEL: f_trunc_pos2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 4
; CHECK-NOT: call
  %r = call float @llvm.trunc.f32(float %x)
  ret float %r
}

define float @f_round_pos2p5(float %x) {
; CHECK-LABEL: f_round_pos2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 2
; CHECK-NOT: call
  %r = call float @llvm.round.f32(float %x)
  ret float %r
}

define float @f_roundeven_pos2p5(float %x) {
; CHECK-LABEL: f_roundeven_pos2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 1
; CHECK-NOT: call
  %r = call float @llvm.roundeven.f32(float %x)
  ret float %r
}

define float @f_rint_pos2p5(float %x) {
; CHECK-LABEL: f_rint_pos2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 32
; CHECK-NOT: call
  %r = call float @llvm.rint.f32(float %x)
  ret float %r
}

define float @f_nearbyint_pos2p5(float %x) {
; CHECK-LABEL: f_nearbyint_pos2p5:
; CHECK-COUNT-1: ftrnd rf{{[0-9]+}}, rf16, 32
; CHECK-NOT: call
  %r = call float @llvm.nearbyint.f32(float %x)
  ret float %r
}
