; RUN: %llc -march=dadao -O2 %s -o - | %FileCheck %s --check-prefix=BATCH
; RUN: %llc -march=dadao -O2 -dadao-disable-ldm-stm %s -o - | %FileCheck %s --check-prefix=NOBATCH
;
; LLVM-129t: a function that keeps 8 values live across calls needs 8+ callee
; saved registers; the consecutive run is saved with ONE `stm.o` in the prologue
; and restored with ONE `ldm.o` in the epilogue (DADAOFrameLowering, ADR-0018
; C7 D4 form 4).  `-dadao-disable-ldm-stm` turns every multi-register transfer
; off, so the same function falls back to per-register `st.o`/`ld.o` -- that is
; the reachable FAIL path for the BATCH assertions.

define i64 @f(i64 %n) {
entry:
  %cmp = icmp sgt i64 %n, 0
  br i1 %cmp, label %for.body, label %for.cleanup

for.body:
  %k = phi i64 [ 0, %entry ], [ %inc, %for.body ]
  %a = phi i64 [ 1, %entry ], [ %ca, %for.body ]
  %b = phi i64 [ 2, %entry ], [ %cb, %for.body ]
  %c = phi i64 [ 3, %entry ], [ %cc, %for.body ]
  %d = phi i64 [ 4, %entry ], [ %cd, %for.body ]
  %e = phi i64 [ 5, %entry ], [ %ce, %for.body ]
  %g = phi i64 [ 6, %entry ], [ %cg, %for.body ]
  %h = phi i64 [ 7, %entry ], [ %ch, %for.body ]
  %i = phi i64 [ 8, %entry ], [ %ci, %for.body ]
  %ca = call i64 @g(i64 %a)
  %cb = call i64 @g(i64 %b)
  %cc = call i64 @g(i64 %c)
  %cd = call i64 @g(i64 %d)
  %ce = call i64 @g(i64 %e)
  %cg = call i64 @g(i64 %g)
  %ch = call i64 @g(i64 %h)
  %ci = call i64 @g(i64 %i)
  %inc = add nuw nsw i64 %k, 1
  %done = icmp eq i64 %inc, %n
  br i1 %done, label %for.cleanup, label %for.body

for.cleanup:
  %ra = phi i64 [ 1, %entry ], [ %ca, %for.body ]
  %rb = phi i64 [ 2, %entry ], [ %cb, %for.body ]
  %rc = phi i64 [ 3, %entry ], [ %cc, %for.body ]
  %rd = phi i64 [ 4, %entry ], [ %cd, %for.body ]
  %re = phi i64 [ 5, %entry ], [ %ce, %for.body ]
  %rg = phi i64 [ 6, %entry ], [ %cg, %for.body ]
  %rh = phi i64 [ 7, %entry ], [ %ch, %for.body ]
  %ri = phi i64 [ 8, %entry ], [ %ci, %for.body ]
  %s0 = add i64 %ra, %rb
  %s1 = add i64 %s0, %rc
  %s2 = add i64 %s1, %rd
  %s3 = add i64 %s2, %re
  %s4 = add i64 %s3, %rg
  %s5 = add i64 %s4, %rh
  %s6 = add i64 %s5, %ri
  ret i64 %s6
}

declare i64 @g(i64)

; BATCH-LABEL: f:
; BATCH: stm.o
; BATCH: ldm.o
; NOBATCH-LABEL: f:
; NOBATCH-NOT: stm.o
; NOBATCH-NOT: ldm.o
; NOBATCH: st.o
; NOBATCH: ld.o
