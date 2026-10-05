; TESTCASES-026t / CodeGen vector: call (C1 pointer argument bank / C5 pointer return bank)
; @advance takes a pointer (rb16) and returns a pointer (rb31); @deref takes a
; pointer (rb16) and returns an integer (rd31).  The pointer offset is loaded
; from a volatile slot so the GEP is a genuine pointer+offset computation.
;
; IR semantics:
;   buf[3] = 42
;   q = advance(buf, 3) = buf + 3
;   r = deref(q) = 42
; Expected guest exit code: 42
define i8* @advance(i8* %p, i64 %off) noinline {
entry:
  %q = getelementptr i8, i8* %p, i64 %off
  ret i8* %q
}

define i64 @deref(i8* %p) noinline {
entry:
  %v = load volatile i8, i8* %p, align 1
  %z = zext i8 %v to i64
  ret i64 %z
}

define i64 @main() {
entry:
  %buf = alloca [8 x i8], align 8
  %soff = alloca i64, align 8
  store volatile i64 3, i64* %soff, align 8
  %p3 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 3
  store volatile i8 42, i8* %p3, align 1
  %off = load volatile i64, i64* %soff, align 8
  %q = call i8* @advance(i8* %buf, i64 %off)
  %r = call i64 @deref(i8* %q)
  ret i64 %r
}
