;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-102t (B) / ADR-0031: the seven-field three-cursor va_list.  A variadic
; callee snapshots the argument banks in its own frame with one stm.o per bank
; (D2) and va_start initialises the cursors/counters/stack pointer; the caller
; writes **no** save area (D2) and only the usual shared overflow stack area.
;
declare void @llvm.va_start.p0(ptr)

; vsum has one named i64 (rd16), so the RD save range starts at rd17; RB and RF
; are untouched by named arguments and are saved from rb16 / rf16.
; CHECK-LABEL: vsum:
; CHECK:       stm.o {rd17:rd31}, [{{rb[0-9]+}}, rd0]
; CHECK:       stm.o {rb16:rb31}, [{{rb[0-9]+}}, rd0]
; CHECK:       stm.o {rf16:rf31}, [{{rb[0-9]+}}, rd0]
; rd_left = 32 - 17 = 15 is materialised for the va_list field.
; CHECK-DAG:   set.zw {{rd[0-9]+}}, wp0, 0xf
define i64 @vsum(i64 %n, ...) noinline {
entry:
  %ap = alloca [7 x i64], align 16
  call void @llvm.va_start.p0(ptr %ap)
  %nextp = getelementptr i64, ptr %ap, i64 0
  %next = load i64, ptr %nextp, align 8
  %leftp = getelementptr i64, ptr %ap, i64 3
  %left = load i64, ptr %leftp, align 8
  %r = add i64 %next, %left
  ret i64 %r
}

; The caller no longer stores the argument block at the call-site SP.
; CHECK-LABEL: main:
; CHECK-NOT:   st.o r{{[db][0-9]+}}, {{\[}}rb1,
; CHECK:       call [rb0, vsum]
define i64 @main() {
entry:
  %a = call i64 (i64, ...) @vsum(i64 3, i64 10, i64 20, i64 12)
  ret i64 %a
}
