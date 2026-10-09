;
; dadao_mem_runtime.ll — minimal freestanding mem* runtime for the M6 CodeGen
; E2E gate (LLVM-064t, INTEG-023k §A #3: no libc).
;
; The DADAO backend leaves an out-of-line `llvm.memcpy`/`memset`/`memmove`
; (i.e. one larger than MaxStoresPerMem* = 16 store slots) as a plain libcall
; (`call memcpy` / `memset` / `memmove`); `memcmp` is an ordinary external C
; call.  These byte-loop implementations provide the symbols, so a single-TU
; E2E (llc -> llvm-mc -> objcopy -> qemu) links and runs without any libc.
;
; Compile with `llc -march=dadao -O0` and concatenate the resulting .s ahead of
; (or after) the crt0 + program TU, exactly like tests/scripts/codegen_crt0.s.
;
; Signatures match the C library / libcall ABI: pointer arguments land in the
; RB bank (rb16..), scalars in the RD bank (rd16..), and memcmp returns i32.

target triple = "dadao-unknown-elf"

define ptr @memcpy(ptr %dst, ptr %src, i64 %n) {
entry:
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %i.next, %body ]
  %done = icmp eq i64 %i, %n
  br i1 %done, label %end, label %body

body:
  %sp = getelementptr i8, ptr %src, i64 %i
  %b = load i8, ptr %sp, align 1
  %dp = getelementptr i8, ptr %dst, i64 %i
  store i8 %b, ptr %dp, align 1
  %i.next = add i64 %i, 1
  br label %loop

end:
  ret ptr %dst
}

define ptr @memset(ptr %dst, i8 %value, i64 %n) {
entry:
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %i.next, %body ]
  %done = icmp eq i64 %i, %n
  br i1 %done, label %end, label %body

body:
  %dp = getelementptr i8, ptr %dst, i64 %i
  store i8 %value, ptr %dp, align 1
  %i.next = add i64 %i, 1
  br label %loop

end:
  ret ptr %dst
}

define ptr @memmove(ptr %dst, ptr %src, i64 %n) {
entry:
  %d = ptrtoint ptr %dst to i64
  %s = ptrtoint ptr %src to i64
  %forward = icmp ult i64 %d, %s
  br i1 %forward, label %fwd.loop, label %bwd.loop

fwd.loop:
  %fi = phi i64 [ 0, %entry ], [ %fi.next, %fwd.body ]
  %fdone = icmp eq i64 %fi, %n
  br i1 %fdone, label %end, label %fwd.body

fwd.body:
  %fsp = getelementptr i8, ptr %src, i64 %fi
  %fb = load i8, ptr %fsp, align 1
  %fdp = getelementptr i8, ptr %dst, i64 %fi
  store i8 %fb, ptr %fdp, align 1
  %fi.next = add i64 %fi, 1
  br label %fwd.loop

bwd.loop:
  %bi = phi i64 [ %n, %entry ], [ %bi.next, %bwd.body ]
  %bdone = icmp eq i64 %bi, 0
  br i1 %bdone, label %end, label %bwd.body

bwd.body:
  %bi.next = sub i64 %bi, 1
  %bsp = getelementptr i8, ptr %src, i64 %bi.next
  %bb = load i8, ptr %bsp, align 1
  %bdp = getelementptr i8, ptr %dst, i64 %bi.next
  store i8 %bb, ptr %bdp, align 1
  br label %bwd.loop

end:
  ret ptr %dst
}

define i32 @memcmp(ptr %a, ptr %b, i64 %n) {
entry:
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %i.next, %next ]
  %done = icmp eq i64 %i, %n
  br i1 %done, label %equal, label %body

body:
  %ap = getelementptr i8, ptr %a, i64 %i
  %av = load i8, ptr %ap, align 1
  %bp = getelementptr i8, ptr %b, i64 %i
  %bv = load i8, ptr %bp, align 1
  %neq = icmp ne i8 %av, %bv
  br i1 %neq, label %diff, label %next

next:
  %i.next = add i64 %i, 1
  br label %loop

diff:
  %av.ext = zext i8 %av to i32
  %bv.ext = zext i8 %bv to i32
  %r = sub i32 %av.ext, %bv.ext
  ret i32 %r

equal:
  ret i32 0
}
