; TESTCASES-032t / M4 L3 vector -- program "notneg_neg", translation unit A (library).
;
; The `neg` (arithmetic negation) functionality of the deleted `neg.{b,w,t,o}`
; pseudo is expressed with the real signed subtract instructions:
;   * 8/16/32-bit -> `sub.sb`/`sub.sw`/`sub.st rd, rd0, rc` (result sign-extended)
;   * 64-bit      -> `sub.so {rd0, rd}, rd0, rc`
; i.e. IR-level `0 - x` computed at each width (`sub iN 0, %x`) then widened to
; i64 by sign extension, so the width-specific wraparound and the sign
; extension are both exercised.
;
; Coverage:
;   * `.text`       : exported helpers called from the other TU.
;   * cross-TU call : `neg8`/`neg16`/`neg32`/`neg64` are undefined in TU B
;                     -> R_DADAO_REL26.
;
; IR semantics (host independent oracle): neg_w(x) = sext_w(0 - trunc_w(x)).

define i64 @neg8(i64 %x) noinline {
entry:
  %t = trunc i64 %x to i8
  %n = sub i8 0, %t
  %e = sext i8 %n to i64
  ret i64 %e
}

define i64 @neg16(i64 %x) noinline {
entry:
  %t = trunc i64 %x to i16
  %n = sub i16 0, %t
  %e = sext i16 %n to i64
  ret i64 %e
}

define i64 @neg32(i64 %x) noinline {
entry:
  %t = trunc i64 %x to i32
  %n = sub i32 0, %t
  %e = sext i32 %n to i64
  ret i64 %e
}

define i64 @neg64(i64 %x) noinline {
entry:
  %n = sub i64 0, %x
  ret i64 %n
}
