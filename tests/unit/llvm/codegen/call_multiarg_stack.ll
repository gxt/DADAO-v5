; TESTCASES-026t / CodeGen vector: call (C4 multi-argument -> stack spill, global declaration order)
; 18 scalar (i64) parameters: rd16..rd31 take the first 16, the last two
; (x16, x17) spill to the contiguous outgoing stack area (8 bytes each, in
; declaration order).  All arguments are derived from one volatile-loaded base
; (base + i), so neither the call nor the sum is constant-folded.
;
; IR semantics:
;   base = 1 ; x_i = base + i for i = 0..17
;   sum18 = x0 + x1 + ... + x17 = 18*base + (0+1+...+17) = 18 + 153 = 171
;   main masks the call result with 127 -> 171 & 127 = 43
; The mask keeps the guest exit code in 0x00..0x7F (ISS-147).
; Expected guest exit code: 43
define i64 @sum18(i64 %x0, i64 %x1, i64 %x2, i64 %x3, i64 %x4, i64 %x5, i64 %x6,
                  i64 %x7, i64 %x8, i64 %x9, i64 %x10, i64 %x11, i64 %x12, i64 %x13,
                  i64 %x14, i64 %x15, i64 %x16, i64 %x17) noinline {
entry:
  %s01 = add i64 %x0, %x1
  %s02 = add i64 %s01, %x2
  %s03 = add i64 %s02, %x3
  %s04 = add i64 %s03, %x4
  %s05 = add i64 %s04, %x5
  %s06 = add i64 %s05, %x6
  %s07 = add i64 %s06, %x7
  %s08 = add i64 %s07, %x8
  %s09 = add i64 %s08, %x9
  %s10 = add i64 %s09, %x10
  %s11 = add i64 %s10, %x11
  %s12 = add i64 %s11, %x12
  %s13 = add i64 %s12, %x13
  %s14 = add i64 %s13, %x14
  %s15 = add i64 %s14, %x15
  %s16 = add i64 %s15, %x16
  %s17 = add i64 %s16, %x17
  ret i64 %s17
}

define i64 @main() {
entry:
  %sbase = alloca i64, align 8
  store volatile i64 1, i64* %sbase, align 8
  %base = load volatile i64, i64* %sbase, align 8
  %a0 = add i64 %base, 0
  %a1 = add i64 %base, 1
  %a2 = add i64 %base, 2
  %a3 = add i64 %base, 3
  %a4 = add i64 %base, 4
  %a5 = add i64 %base, 5
  %a6 = add i64 %base, 6
  %a7 = add i64 %base, 7
  %a8 = add i64 %base, 8
  %a9 = add i64 %base, 9
  %a10 = add i64 %base, 10
  %a11 = add i64 %base, 11
  %a12 = add i64 %base, 12
  %a13 = add i64 %base, 13
  %a14 = add i64 %base, 14
  %a15 = add i64 %base, 15
  %a16 = add i64 %base, 16
  %a17 = add i64 %base, 17
  %r = call i64 @sum18(i64 %a0, i64 %a1, i64 %a2, i64 %a3, i64 %a4, i64 %a5, i64 %a6,
                      i64 %a7, i64 %a8, i64 %a9, i64 %a10, i64 %a11, i64 %a12, i64 %a13,
                      i64 %a14, i64 %a15, i64 %a16, i64 %a17)
  %m = and i64 %r, 127
  ret i64 %m
}
