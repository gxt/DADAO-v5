; LLVM-139t / CodeGen runtime vector: loop-carried pointer induction kept in
; the address bank (DADAOPointerPHIBank, post-ISel/pre-RA).
;
; @walk_sum walks `p = (p + 2 elements) + i elements` over the caller's
; buffer and sums `buf[offset] = 3*offset + 1` with volatile loads, so the
; pointer PHI chain survives to instruction selection.  Its pointer argument
; arrives in the address bank (rb16), which is exactly the shape the pass
; rewrites: no `rd2rb` bridge in the loop body.  `noinline` keeps the loop
; in its own function (the argument is the only address-bank source, the
; caller's alloca would reach the PHI as a data-bank copy) and the trip
; count comes from a volatile slot so the loop cannot be unrolled away.
;
; Visited offsets for n = 5: 0,2,5,9,14 -> 1+7+16+28+43 = 95;
; for n = 3:                  0,2,5      -> 1+7+16      = 24.
; Both sums are derived here from LLVM IR semantics, not from llc or QEMU.
; @main returns the number of mismatching sums (0 when both are exact), so a
; wrong element offset, a wrong scaled-index shift or a wrong backedge makes
; the guest exit code non-zero.  Expected guest exit code: 0.
target triple = "dadao-unknown-elf"

define i64 @walk_sum(ptr %p, i64 %n) noinline {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %ptr = phi ptr [ %p, %entry ], [ %nextp, %loop ]
  %acc = phi i64 [ 0, %entry ], [ %accn, %loop ]
  %v = load volatile i64, ptr %ptr, align 8
  %accn = add i64 %acc, %v
  %q = getelementptr i64, ptr %ptr, i64 2
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret i64 %accn
}

define i64 @main() {
entry:
  %buf = alloca [16 x i64], align 8
  %n5_slot = alloca i64, align 8
  %n3_slot = alloca i64, align 8
  store volatile i64 1, ptr %buf, align 8
  %e1 = getelementptr [16 x i64], ptr %buf, i64 0, i64 1
  store volatile i64 4, ptr %e1, align 8
  %e2 = getelementptr [16 x i64], ptr %buf, i64 0, i64 2
  store volatile i64 7, ptr %e2, align 8
  %e3 = getelementptr [16 x i64], ptr %buf, i64 0, i64 3
  store volatile i64 10, ptr %e3, align 8
  %e4 = getelementptr [16 x i64], ptr %buf, i64 0, i64 4
  store volatile i64 13, ptr %e4, align 8
  %e5 = getelementptr [16 x i64], ptr %buf, i64 0, i64 5
  store volatile i64 16, ptr %e5, align 8
  %e6 = getelementptr [16 x i64], ptr %buf, i64 0, i64 6
  store volatile i64 19, ptr %e6, align 8
  %e7 = getelementptr [16 x i64], ptr %buf, i64 0, i64 7
  store volatile i64 22, ptr %e7, align 8
  %e8 = getelementptr [16 x i64], ptr %buf, i64 0, i64 8
  store volatile i64 25, ptr %e8, align 8
  %e9 = getelementptr [16 x i64], ptr %buf, i64 0, i64 9
  store volatile i64 28, ptr %e9, align 8
  %e10 = getelementptr [16 x i64], ptr %buf, i64 0, i64 10
  store volatile i64 31, ptr %e10, align 8
  %e11 = getelementptr [16 x i64], ptr %buf, i64 0, i64 11
  store volatile i64 34, ptr %e11, align 8
  %e12 = getelementptr [16 x i64], ptr %buf, i64 0, i64 12
  store volatile i64 37, ptr %e12, align 8
  %e13 = getelementptr [16 x i64], ptr %buf, i64 0, i64 13
  store volatile i64 40, ptr %e13, align 8
  %e14 = getelementptr [16 x i64], ptr %buf, i64 0, i64 14
  store volatile i64 43, ptr %e14, align 8
  %e15 = getelementptr [16 x i64], ptr %buf, i64 0, i64 15
  store volatile i64 46, ptr %e15, align 8
  store volatile i64 5, ptr %n5_slot, align 8
  store volatile i64 3, ptr %n3_slot, align 8
  %n5 = load volatile i64, ptr %n5_slot, align 8
  %n3 = load volatile i64, ptr %n3_slot, align 8
  %s5 = call i64 @walk_sum(ptr %buf, i64 %n5)
  %s3 = call i64 @walk_sum(ptr %buf, i64 %n3)
  %ok5 = icmp eq i64 %s5, 95
  %z5 = zext i1 %ok5 to i64
  %m5 = sub i64 1, %z5
  %ok3 = icmp eq i64 %s3, 24
  %z3 = zext i1 %ok3 to i64
  %m3 = sub i64 1, %z3
  %bad = add i64 %m5, %m3
  ret i64 %bad
}
