; TESTCASES-030t / M4 L3 vector -- program "multi_tu_call", translation unit B (main).
;
; Coverage:
;   * cross-TU direct call : `call i64 @lib_mix(...)` reaches a symbol defined in
;                            a different translation unit -> R_DADAO_REL26.
;   * cross-TU global      : @acc (defined in TU A) is addressed here -> the
;                            address materialisation is R_DADAO_ABS48.
;   * conditional branch   : the eq/ne guard is the rrii compare-branch form
;                            (R_DADAO_REL14 field), taken / not-taken both exist.
;
; IR semantics (host independent oracle):
;   r = lib_mix(20, 11)              -> 42
;   v = load acc (run-time read of the .bss global written by lib_mix) -> 42
;   if (r == v) return r else return 1
;   -> returns 42.

@acc = external global i64, align 8

declare i64 @lib_mix(i64, i64)

define i64 @main() noinline {
entry:
  %r = call i64 @lib_mix(i64 20, i64 11)
  %v = load i64, i64* @acc, align 8
  %c = icmp eq i64 %r, %v
  br i1 %c, label %ok, label %bad

ok:
  ret i64 %r

bad:
  ret i64 1
}
