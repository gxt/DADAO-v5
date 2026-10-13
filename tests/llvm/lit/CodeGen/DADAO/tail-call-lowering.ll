;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-074t (M6): real tail call.  DADAO has no tail-call *instruction* -- every
; `call` computes a return address and pushes it on the RegRAS (`ra63`;
; contract-abi.md §2.3, contract-isa.md §8.4) -- but it does have a plain
; `jump`, which pushes *nothing* on the RegRAS (contract-isa.md §8.3).  A tail
; call is therefore lowered to a tail-jump: the caller tears its frame down
; (the tail-jump pseudo is isReturn, so PEI emits the standard epilogue right
; before it) and JUMPS to the callee, so the callee's `ret` pops the *caller's*
; RegRAS entry.  A tail call must compile to an epilogue + `jump`, never a
; `call` followed by a `ret`.
;
; The return-value convention is unchanged: the callee returns in rd8 (integer)
; / rb8 (pointer) (contract-abi.md §4.4), and the epilogue does not touch those
; registers, so a returned value is forwarded implicitly by the jump.
;
; Only tail calls whose arguments all fit the register banks and that are
; non-variadic are eligible (a tail-jump leaves SP at the caller's frame, so it
; cannot provide an outgoing stack-argument area); the rest are demoted to an
; ordinary call + return.
;
target triple = "dadao-unknown-elf"

declare void @body(i32)

; CHECK-LABEL: warm:
; The frame is restored and the callee is JUMPED to (no return-address push).
; CHECK-NOT: call {{.*}}body
; CHECK: jump {{.*}}body
define void @warm(i32 %heat) {
entry:
  tail call void @body(i32 1)
  ret void
}

declare i64 @g()

; CHECK-LABEL: f:
; A non-void tail call likewise jumps; the value is forwarded in rd8.
; CHECK-NOT: call {{.*}}g
; CHECK: jump {{.*}}g
define i64 @f() {
entry:
  %r = tail call i64 @g()
  ret i64 %r
}

declare void @vbody(i32, ...)

; CHECK-LABEL: vwarm:
; A variadic tail call is not eligible (its varargs save area lives in this
; frame): it is demoted to an ordinary call followed by a return.
; CHECK: call {{.*}}vbody
; CHECK: ret
define void @vwarm(i32 %x) {
entry:
  tail call void (i32, ...) @vbody(i32 1, i32 %x)
  ret void
}

; CHECK-LABEL: bar:
; An indirect tail call is also a jump (through the function-pointer register):
; `jump [rbTarget, rd0, 0]`.
; CHECK: jump [{{rb[0-9]+}}, rd0, 0]
define i64 @bar(i64 (i64)* %fp, i64 %x) {
entry:
  %r = tail call i64 %fp(i64 %x)
  ret i64 %r
}

declare i64 @g2(i64)

; CHECK-LABEL: mt:
; A `musttail` call that satisfies the tail-jump constraints is honoured.
; CHECK: jump {{.*}}g2
define i64 @mt(i64 %x) {
entry:
  %r = musttail call i64 @g2(i64 %x)
  ret i64 %r
}

%Big = type [80 x i8]
declare i64 @take_big(ptr byval(%Big) align 8)

; CHECK-LABEL: fwd_big:
; A byval argument is a pointer to a caller-local copy: tearing the frame down
; would leave it dangling, so such a tail call is demoted to an ordinary
; call + return (guard shared with RISCV/AArch64).
; CHECK: call {{.*}}take_big
; CHECK: ret
define i64 @fwd_big(ptr byval(%Big) align 8 %p) {
entry:
  %r = tail call i64 @take_big(ptr byval(%Big) align 8 %p)
  ret i64 %r
}

