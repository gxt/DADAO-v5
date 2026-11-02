;
; TESTCASES-057t: the three compiler-visible spellings of `clmul.o`, at IR level.
;
; The C probes reach the instruction through `__builtin_dadao_clmul` (the
; `llvm.dadao.clmul.wide` i128 form).  The generic LLVM intrinsic
; `llvm.clmul` and the private half-form `llvm.dadao.clmul` / `.hi` have no C
; spelling, so the task requires at least one example of each at IR level
; (TESTCASES-057t 已裁定): they live here and are linked into `clmul_edges.c`,
; which then judges all three exits (low half / high half / i128 composite)
; against the independent oracle.
;
; Half binding is the point of the exercise (ADR-0035 D2: rdhA = high,
; rdhB = low), so the selectors are asserted structurally by the driver
; (`clmul_generic_lo` must be `clmul.o {rd0, ...}` -- the high half is
; discarded; `clmul_intr_hi` must be `clmul.o {..., rd0}`).
;
; LLVM-122t is the source of the intrinsic signatures (IntrinsicsDADAO.td).
target triple = "dadao-unknown-unknown-elf"

declare i64 @llvm.clmul.i64(i64, i64)
declare i64 @llvm.dadao.clmul.hi(i64, i64)
declare {i64, i64} @llvm.dadao.clmul(i64, i64)

; Generic intrinsic: low 64 bits only.
define i64 @clmul_generic_lo(i64 %a, i64 %b) {
  %r = call i64 @llvm.clmul.i64(i64 %a, i64 %b)
  ret i64 %r
}

; Private intrinsic: high 64 bits only (`clmul.o dst, rd0, a, b`).
define i64 @clmul_intr_hi(i64 %a, i64 %b) {
  %r = call i64 @llvm.dadao.clmul.hi(i64 %a, i64 %b)
  ret i64 %r
}

; Private intrinsic, both halves: {low, high} in the intrinsic's return order.
define i64 @clmul_pair_lo(i64 %a, i64 %b) {
  %p = call {i64, i64} @llvm.dadao.clmul(i64 %a, i64 %b)
  %lo = extractvalue {i64, i64} %p, 0
  ret i64 %lo
}

define i64 @clmul_pair_hi(i64 %a, i64 %b) {
  %p = call {i64, i64} @llvm.dadao.clmul(i64 %a, i64 %b)
  %hi = extractvalue {i64, i64} %p, 1
  ret i64 %hi
}
