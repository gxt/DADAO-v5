;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-062t / M6: a variadic call writes every argument into a contiguous
; 8-byte-slot save area at the call-site SP (slot i at SP + i*8, declaration
; order -- spec DADAO-21 §可变参数), and `llvm.va_start` in the callee points
; just past the named arguments (entry_SP + N_named*8).
;
declare void @llvm.va_start.p0(ptr)

; CHECK-LABEL: vsum:
; va_start = entry_SP + 1*8: the callee materialises the save-area base from SP
; (rb1) and adds the named-argument offset.
; CHECK:         rb2rb {rb{{[0-9]+}}}, {rb1}
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

; CHECK-LABEL: main:
; The 4 argument slots (n, 10, 20, 12) are written at SP+0, SP+8, SP+16, SP+24
; in addition to the register assignment.
; CHECK-DAG:     st.o r{{d[0-9]+}}, {{\[}}rb1, 0{{\]}}
; CHECK-DAG:     st.o r{{d[0-9]+}}, {{\[}}rb1, 8{{\]}}
; CHECK-DAG:     st.o r{{d[0-9]+}}, {{\[}}rb1, 16{{\]}}
; CHECK-DAG:     st.o r{{d[0-9]+}}, {{\[}}rb1, 24{{\]}}
; CHECK:         call [rb0, vsum]
define i64 @main() {
entry:
  %a = call i64 (i64, ...) @vsum(i64 3, i64 10, i64 20, i64 12)
  ret i64 %a
}
