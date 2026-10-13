; TESTCASES-026t / CodeGen vector: branch (C17 p==NULL via br.z/nz{rb}; C14 p==q via cmp.uo(dbb))
; Pointer comparisons live in a helper whose pointer operands are formal parameters
; (GPRB virtual registers), which is what the bank-aware ISel matches (C1/C5/C14).
;
; IR semantics (all comparisons are on absolute addresses):
;   @ptr_checks(p, q):
;     if (p == null) r = 1 else r = 2
;     if (p == q)    r = r + 4 else r = r + 8
;   @main:
;     p = &buf (non-null)
;     a = ptr_checks(p, p)    -> p != null -> 2 ; p == q -> 2+4 = 6
;     b = ptr_checks(p, null) -> p != null -> 2 ; p != q -> 2+8 = 10
;     c = ptr_checks(null, p) -> p == null -> 1 ; p != q -> 1+8 = 9
;     r = (a + b + c) & 255 = 25
; Expected guest exit code: 25
define i64 @ptr_checks(i8* %p, i8* %q) noinline {
entry:
  %c1 = icmp eq i8* %p, null
  br i1 %c1, label %isnull, label %notnull

isnull:
  %r1a = add i64 0, 1
  br label %join1

notnull:
  %r1b = add i64 0, 2
  br label %join1

join1:
  %r1 = phi i64 [ %r1a, %isnull ], [ %r1b, %notnull ]
  %c2 = icmp eq i8* %p, %q
  br i1 %c2, label %eq, label %ne

eq:
  %r2a = add i64 %r1, 4
  br label %join2

ne:
  %r2b = add i64 %r1, 8
  br label %join2

join2:
  %r2 = phi i64 [ %r2a, %eq ], [ %r2b, %ne ]
  ret i64 %r2
}

define i64 @main() {
entry:
  %buf = alloca [8 x i8], align 8
  %p = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 0
  %a = call i64 @ptr_checks(i8* %p, i8* %p)
  %b = call i64 @ptr_checks(i8* %p, i8* null)
  %c = call i64 @ptr_checks(i8* null, i8* %p)
  %s1 = add i64 %a, %b
  %s2 = add i64 %s1, %c
  %r = and i64 %s2, 255
  ret i64 %r
}
