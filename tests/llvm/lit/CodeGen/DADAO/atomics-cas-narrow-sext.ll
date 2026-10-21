;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-121t rework (ISS-313): a 1/2/4-byte compare-exchange must compare the
; W bytes of memory, not the whole 64-bit register.
;
; `lr.b/.w/.t` zero-extends the loaded bytes into the 64-bit result register
; (SimRISC-12 §3.2 as implemented for this batch), while the expected value is
; promoted from i8/i16/i32 by the type legalizer and may be sign-extended.  A
; raw 64-bit `br.ne` therefore never matched a top-bit-set expected value:
;
;   WRONG: lr.t.an rd, [rb] ; br.ne {rd, rd_arg}?      (arg high bits = all 1s)
;   RIGHT: and.o cmp, rd_arg, 0xFFFFFFFF ; lr.t.an ... ; br.ne {rd, cmp}?
;
; The lowering normalises the expected value to the access width once
; (DADAOTargetLowering::LowerATOMIC_CMP_SWAP_WITH_SUCCESS); that single value
; feeds both the `br.ne` inside the machine loop and the SETCC that computes
; the success flag, so the two comparisons cannot drift apart again.
;
; Every check below fails with the defective lowering: the runtime case has no
; `and.o` (it compares the raw sign-extended argument), and the constant cases
; materialise the compare word with the all-ones high pattern (`set.ow` /
; `andn.w`) instead of the width-width zero-extended form.
;

; i32, expected value arrives at run time: the mask must be applied explicitly.
define i32 @cas32_runtime_expected(ptr %p, i32 %c, i32 %n) {
; CHECK-LABEL: cas32_runtime_expected:
; CHECK: set.zw [[M:rd[0-9]+]], wp0, 0xffff
; CHECK: or.w [[M]], wp1, 0xffff
; CHECK: and.o [[CMP:rd[0-9]+]], rd{{[0-9]+}}, [[M]]
; CHECK: lr.t.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], [[CMP]]}?, [rb0,
; CHECK: sc.t.ar
; CHECK: ret
  %r = cmpxchg ptr %p, i32 %c, i32 %n monotonic monotonic
  %v = extractvalue { i32, i1 } %r, 0
  ret i32 %v
}

; i32, expected = 0x80000000 (INT_MIN): the compare word must be zero-extended
; (0x0000_0000_8000_0000), not sign-extended (0xFFFF_FFFF_8000_0000).
define i32 @cas32_top_bit(ptr %p, i32 %n) {
; CHECK-LABEL: cas32_top_bit:
; CHECK-NOT: set.ow
; CHECK: set.zw [[CMP:rd[0-9]+]], wp{{[0-9]+}}, 0x8000
; CHECK: lr.t.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], [[CMP]]}?, [rb0,
; CHECK-NOT: andn.w
; CHECK: sc.t.ar
; CHECK: ret
  %r = cmpxchg ptr %p, i32 -2147483648, i32 %n monotonic monotonic
  %v = extractvalue { i32, i1 } %r, 0
  ret i32 %v
}

; i16, expected = 0x8000: same rule on the wyde window.
define i16 @cas16_top_bit(ptr %p, i16 %n) {
; CHECK-LABEL: cas16_top_bit:
; CHECK-NOT: set.ow
; CHECK: set.zw [[CMP:rd[0-9]+]], wp0, 0x8000
; CHECK: lr.w.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], [[CMP]]}?, [rb0,
; CHECK: sc.w.ar
; CHECK: ret
  %r = cmpxchg ptr %p, i16 -32768, i16 %n monotonic monotonic
  %v = extractvalue { i16, i1 } %r, 0
  ret i16 %v
}

; i8, expected = 0x80: same rule on the byte window.
define i8 @cas8_top_bit(ptr %p, i8 %n) {
; CHECK-LABEL: cas8_top_bit:
; CHECK-NOT: set.ow
; CHECK: set.zw [[CMP:rd[0-9]+]], wp0, 0x80
; CHECK: lr.b.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], [[CMP]]}?, [rb0,
; CHECK: sc.b.ar
; CHECK: ret
  %r = cmpxchg ptr %p, i8 -128, i8 %n monotonic monotonic
  %v = extractvalue { i8, i1 } %r, 0
  ret i8 %v
}

; The success flag is computed from the *same* normalised operand: `cmp.so`
; must compare the lr result against the register the loop compared against.
define i1 @cas32_flag_uses_mask(ptr %p, i32 %c, i32 %n) {
; CHECK-LABEL: cas32_flag_uses_mask:
; CHECK: and.o [[CMP:rd[0-9]+]], rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: lr.t.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], [[CMP]]}?, [rb0,
; CHECK: sc.t.ar
; CHECK: cmp.so {{rd[0-9]+}}, [[OLD]], [[CMP]]
; CHECK: ret
  %r = cmpxchg ptr %p, i32 %c, i32 %n monotonic monotonic
  %s = extractvalue { i32, i1 } %r, 1
  ret i1 %s
}

; The 8-byte width is unaffected: no mask (the full register is the value).
define i64 @cas64_no_mask(ptr %p, i64 %c, i64 %n) {
; CHECK-LABEL: cas64_no_mask:
; CHECK-NOT: and.o
; CHECK: lr.o.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], rd{{[0-9]+}}}?, [rb0,
; CHECK: sc.o.ar
; CHECK: ret
  %r = cmpxchg ptr %p, i64 %c, i64 %n monotonic monotonic
  %v = extractvalue { i64, i1 } %r, 0
  ret i64 %v
}
