;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-103t (ISS-267 ④): the f64 `log` libcall, the counterpart of the
; LLVM-089t f32 entry.  The DADAO ISA has no `flog` instruction
; (`contracts/opcodes.yaml`, scope `fp`), so the `flog` DAG node on f64 is
; `Expand`ed to an out-of-line call to the standard C `log`
; (RTLIB::LOG_F64 -> RTLIB::impl_log, DADAOSubtarget::initLibcallLoweringInfo).
; Without that registration llvm-test-suite CoMD (`random.c`) and
; consumer-lame (`psymodel.c`) abort codegen with "no libcall available for
; flog".
;
; `LOG10_F64` is registered in the same task: once `flog` went away,
; consumer-lame's `quantize.c` reported "no libcall available for flog10".  A
; live compile of every TU of both cases shows these two as the only missing
; libcalls (no `exp`/`pow` is needed by any source), so this test deliberately
; covers just `log` and `log10`.
;
; The expected symbol name is the C library name mandated by the RTLIB enum,
; NOT read back from the backend.  The addend keeps the call out of tail
; position (a bare `return log(x)` would be a `jump log`).
;

declare double @llvm.log.f64(double)
declare double @llvm.log10.f64(double)

define double @d_log(double %x) {
; CHECK-LABEL: d_log:
; CHECK: call [rb0, log]
  %r = call double @llvm.log.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @d_log10(double %x) {
; CHECK-LABEL: d_log10:
; CHECK: call [rb0, log10]
  %r = call double @llvm.log10.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}
