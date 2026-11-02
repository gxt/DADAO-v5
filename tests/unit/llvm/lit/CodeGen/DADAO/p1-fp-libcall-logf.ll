;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-089t (ISS-193 (b) residual): the f32 `log` libcall.  The DADAO ISA has no
; `flog` instruction (`contracts/opcodes.yaml`, scope `fp` carries only
; convert/arith/root/sign/compare/classify), so the `flog` DAG node on f32 is
; `Expand`ed to an out-of-line call to the standard C `logf`
; (RTLIB::LOG_F32 -> RTLIB::impl_logf, DADAOSubtarget::initLibcallLoweringInfo).
; This is what lets picolibc's `libm/math/sf_log10.c` -- whose fdlibm body
; computes `log10f` in terms of the public `logf` -- compile, which in turn puts
; `log10f` into the target libc.
;
; Only `LOG_F32` is registered: a live compile scan of every `libm/**/*.c`
; reports `flog` as the sole missing f32 math libcall (no `flog2`/`fexp`/`fpow`
; is needed by any source), so this test deliberately covers just `log`.
;
; The expected symbol name is the C library name mandated by the RTLIB enum,
; NOT read back from the backend.  The addend keeps the call out of tail
; position (a bare `return logf(x)` would be a `jump logf`).
;

declare float @llvm.log.f32(float)

define float @f_log(float %x) {
; CHECK-LABEL: f_log:
; CHECK: call [rb0, logf]
  %r = call float @llvm.log.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}
