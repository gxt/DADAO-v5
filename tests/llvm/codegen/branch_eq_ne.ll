; TESTCASES-026t / CodeGen vector: branch (C17 == / != compare-branch, taken + not-taken)
; Two independent equality tests; the operands come from volatile loads.
; LLVM lowers == / != to br.eq / br.ne (no flag register; C17).
;
; IR semantics:
;   a = 7 ; b = 7 ; c = 3 ; d = 9
;   if (a == b) r = 1 else r = 100      -> r = 1   (true edge taken)
;   if (c != d) r = r + 10 else r = r + 200 -> r = 11 (true edge taken)
;   r = r + 5                            -> 16
; Expected guest exit code: 16
define i64 @main() {
entry:
  %sa = alloca i64, align 8
  %sb = alloca i64, align 8
  %sc = alloca i64, align 8
  %sd = alloca i64, align 8
  store volatile i64 7, i64* %sa, align 8
  store volatile i64 7, i64* %sb, align 8
  store volatile i64 3, i64* %sc, align 8
  store volatile i64 9, i64* %sd, align 8
  %a = load volatile i64, i64* %sa, align 8
  %b = load volatile i64, i64* %sb, align 8
  %c = load volatile i64, i64* %sc, align 8
  %d = load volatile i64, i64* %sd, align 8
  %c1 = icmp eq i64 %a, %b
  br i1 %c1, label %eq_t, label %eq_f

eq_t:
  %r1t = add i64 0, 1
  br label %join1

eq_f:
  %r1f = add i64 0, 100
  br label %join1

join1:
  %r1 = phi i64 [ %r1t, %eq_t ], [ %r1f, %eq_f ]
  %c2 = icmp ne i64 %c, %d
  br i1 %c2, label %ne_t, label %ne_f

ne_t:
  %r2t = add i64 %r1, 10
  br label %join2

ne_f:
  %r2f = add i64 %r1, 200
  br label %join2

join2:
  %r2 = phi i64 [ %r2t, %ne_t ], [ %r2f, %ne_f ]
  %r = add i64 %r2, 5
  ret i64 %r
}
