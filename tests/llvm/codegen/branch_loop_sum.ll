; TESTCASES-026t / CodeGen vector: branch (C17 signed predicate + loop, taken / not-taken)
; A while loop with a signed predicate (icmp slt) and a final signed if.
; n comes from a volatile load, so the loop trip count is not a compile-time constant.
;
; IR semantics:
;   n = 10
;   sum = 0 ; i = 0 ; while (i < n) { sum += i ; i += 1 }  -> 0+1+...+9 = 45
;   if (sum > 40) r = sum else r = 0                        -> 45
; Expected guest exit code: 45
define i64 @main() {
entry:
  %sn = alloca i64, align 8
  store volatile i64 10, i64* %sn, align 8
  %n = load volatile i64, i64* %sn, align 8
  br label %cond

cond:
  %i = phi i64 [ 0, %entry ], [ %i1, %body ]
  %sum = phi i64 [ 0, %entry ], [ %sum1, %body ]
  %c = icmp slt i64 %i, %n
  br i1 %c, label %body, label %done

body:
  %sum1 = add i64 %sum, %i
  %i1 = add i64 %i, 1
  br label %cond

done:
  %g = icmp sgt i64 %sum, 40
  br i1 %g, label %gt, label %le

gt:
  br label %exit

le:
  br label %exit

exit:
  %r = phi i64 [ %sum, %gt ], [ 0, %le ]
  ret i64 %r
}
