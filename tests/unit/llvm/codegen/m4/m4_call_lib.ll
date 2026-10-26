; TESTCASES-030t / M4 L3 vector -- program "multi_tu_call", translation unit A (library).
;
; Coverage:
;   * `.text`  : @lib_mix is an exported function (no internal linkage), called
;                from the other TU -> an undefined external symbol in that TU ->
;                link-time R_DADAO_REL26 on the `call`.
;   * `.rodata`: @seed is a `constant` global -> read-only section.
;   * `.bss`   : @acc is a non-constant zero-initialised global -> NOBITS, and
;                it is read/written at run time.
;   * ABS48    : addresses of @seed / @acc live in other sections than .text, so
;                each materialisation is an R_DADAO_ABS48 (3 wyde pieces); @acc
;                additionally has external linkage and is addressed from TU B.
;
; IR semantics (host independent oracle):
;   lib_mix(a, b) = a + b + seed        with seed = 11 (read-only global)
;   it also stores the result into acc  (run-time write to .bss)
;
; Host-side value:  lib_mix(20, 11) = 20 + 11 + 11 = 42.

@seed = constant i64 11, align 8
@acc  = global i64 0, align 8

define i64 @lib_mix(i64 %a, i64 %b) noinline {
entry:
  %s = load i64, i64* @seed, align 8
  %t = add i64 %a, %b
  %r = add i64 %t, %s
  store i64 %r, i64* @acc, align 8
  ret i64 %r
}
