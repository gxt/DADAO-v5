;
; RUN: %not --crash %llc -march=dadao -O2 -filetype=asm %s -o /dev/null 2>&1 | %FileCheck --check-prefix=REJECT %s
;
; LLVM-074t (M6): a `musttail` call cannot be demoted -- it *promises* the
; tail-call ABI (the callee reuses the caller's return address and frame).  If
; the tail-jump constraints are not met (here: a byval argument, a pointer to a
; caller-local copy that would dangle once the frame is torn down) the backend
; must fail loudly rather than silently emit a frame-allocating call.
; `report_fatal_error` gives an explicit diagnostic (not a silent miscompile).
;
target triple = "dadao-unknown-elf"
%Big = type [80 x i8]
declare i64 @take_big(ptr byval(%Big) align 8)

; REJECT: DADAO: 'musttail' call cannot be lowered
define i64 @fwd_big(ptr byval(%Big) align 8 %p) {
entry:
  %r = musttail call i64 @take_big(ptr byval(%Big) align 8 %p)
  ret i64 %r
}
