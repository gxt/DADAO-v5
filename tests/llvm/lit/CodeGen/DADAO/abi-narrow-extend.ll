; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-127t (M9) + ISS-310: the ABI canonical extension of narrow (<8B)
; integer values, in the backend.
;
; contract-abi.md §4.2 (C4 D2): the *caller* promotes a narrow argument to 8
; bytes, preserving the sign bit -- sign extension for a signed type, zero
; extension for an unsigned one.  The frontend requests it with the IR
; `signext`/`zeroext` attributes; CC_DADAO turns them into a SExt/ZExt location
; info and LowerCall/LowerReturn emit the explicit SIGN_EXTEND/ZERO_EXTEND,
; which select one `ext.so`/`ext.uo` (contract-isa.md §6.4.2).
;
; ISS-310 was the missing frontend half: `int` (i32) arguments carried no
; `signext`, so a signed value reached the callee zero-extended.  The clang half
; is verified end-to-end by tests/e2e/lit/narrow_int_e2e.test (assembly check +
; the `ext_reg` runtime probe); the backend half is pinned here.
;
; Every call site below is exactly the extension plus the call; a return is the
; extension into rd8.

target triple = "dadao-unknown-elf"

declare void @callee_s(i32 signext)
declare void @callee_u(i32 zeroext)

; CHECK-LABEL: pass_s:
; CHECK:         ext.so rd16, rd{{[0-9]+}}, 31
; CHECK-NEXT:    call [rb0, callee_s]
; CHECK-NOT:     call [rb0, callee_u]
define void @pass_s(i32 %x) {
  call void @callee_s(i32 signext %x)
  ret void
}

; CHECK-LABEL: pass_u:
; CHECK:         ext.uo rd16, rd{{[0-9]+}}, 31
; CHECK-NEXT:    call [rb0, callee_u]
define void @pass_u(i32 %x) {
  call void @callee_u(i32 zeroext %x)
  ret void
}

; The callee canonicalises its own narrow return value (C5 D2).
; CHECK-LABEL: ret_s:
; CHECK:         ext.so rd8, rd16, 31
define signext i32 @ret_s(i32 %x) {
  ret i32 %x
}

; CHECK-LABEL: ret_u:
; CHECK:         ext.uo rd8, rd16, 31
define zeroext i32 @ret_u(i32 %x) {
  ret i32 %x
}

; The ISS-310 shape: a live-across-call `int` that is also passed on.  The
; argument extension must be present right before the call, and the returned
; value must be re-extended once.
; CHECK-LABEL: iss310:
; CHECK:         ext.so [[A:rd[0-9]+]], {{rd[0-9]+}}, 31
; CHECK-NEXT:    call [rb0, callee_s]
; CHECK:         ext.uo rd8, {{rd[0-9]+}}, 31
define i32 @iss310(i32 %x) {
  call void @callee_s(i32 signext %x)
  ret i32 %x
}
