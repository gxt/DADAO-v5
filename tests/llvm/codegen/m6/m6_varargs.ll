; LLVM-062t / M6 CodeGen vector: variadic function (va_start + save area).
; Per spec DADAO-21 §可变参数, a variadic call writes every argument into a
; contiguous 8-byte-slot save area at the call-site SP (slot i at SP + i*8, in
; declaration order) in addition to the register assignment; `va_start` points
; just past the named arguments, i.e. entry_SP + N_named*8.  DADAO's va_list is
; a plain pointer, so the callee reads the slots with ordinary loads.
;
; IR semantics:
;   vsum(n=3, ...) reads 3 slots starting at va_start (skip the named `n`):
;     slots = {10, 20, 12}; sum = 42 -> &127 = 42
; Expected guest exit code: 42
declare void @llvm.va_start.p0(ptr)

define i64 @vsum(i64 %n, ...) noinline {
entry:
  %ap = alloca ptr, align 8
  call void @llvm.va_start.p0(ptr %ap)
  %base = load ptr, ptr %ap, align 8
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %i1, %loop ]
  %acc = phi i64 [ 0, %entry ], [ %acc1, %loop ]
  %off = mul i64 %i, 8
  %p = getelementptr i8, ptr %base, i64 %off
  %v = load i64, ptr %p, align 8
  %acc1 = add i64 %acc, %v
  %i1 = add i64 %i, 1
  %c = icmp ult i64 %i1, %n
  br i1 %c, label %loop, label %done

done:
  %r = and i64 %acc1, 127
  ret i64 %r
}

define i64 @main() {
entry:
  %a = call i64 (i64, ...) @vsum(i64 3, i64 10, i64 20, i64 12)
  ret i64 %a
}
