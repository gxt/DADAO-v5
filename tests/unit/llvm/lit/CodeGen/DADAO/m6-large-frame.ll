;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-064t / ADR-0018 C7 D4 (rev. 2026-10-08): large-frame addressing is
; cost-driven.  The compiler picks among
;   1. [sp, disp12]        -- |disp| <= 2047
;   2. rb2rb tmp, sp; add.si tmp, N -- |N| <= 128K
;   3. set.zw/or.w tmpRD, N; add.o tmpRB, sp, tmpRD -- any N
; based on the instruction count, so ISS-138 (>128K frames) no longer
; explicitly fails.  (Form 4, the ldm/stm batch callee-saved save, is covered
; by m6-csr-batch.mir.)

; Small frame: the whole offset folds into the load/store immediate (form 1).
define i64 @small_frame() {
; CHECK-LABEL: small_frame:
; CHECK:       st.o {{rd[0-9]+}}, [rb1, {{[0-9]+}}]
; CHECK-NOT:   add.o
; CHECK:       ret rd0, 0
entry:
  %s = alloca i64, align 8
  store volatile i64 7, ptr %s, align 8
  %v = load volatile i64, ptr %s, align 8
  ret i64 %v
}

; ~60 KiB frame: an object ~60000 bytes below SP needs a scratch register
; (form 2: rb2rb + add.si, in the 18-bit add.si range).
define i64 @medium_frame() {
; CHECK-LABEL: medium_frame:
; CHECK:       rb2rb {{.*}}, {rb1}
; CHECK:       add.si {{.*}}, {{[0-9]+}}
; CHECK:       st.o {{.*}}, [{{.*}}, 0]
entry:
  %s = alloca i64, align 8
  %mid = alloca [60000 x i8], align 8
  store volatile i8 1, ptr %mid, align 1
  store volatile i64 7, ptr %s, align 8
  %v = load volatile i64, ptr %s, align 8
  ret i64 %v
}

; ~200 KB frame: the object offset exceeds the 18-bit add.si range, so the
; constant is materialized with set.zw/or.w and folded with add.o (form 3).
; Before LLVM-064t this aborted with "scheme 1 not implemented" (ISS-138).
define i64 @large_frame() {
; CHECK-LABEL: large_frame:
; CHECK:       set.zw {{rd[0-9]+}}, {{wp[0-9]}}
; CHECK:       add.o {{rb[0-9]+}}, rb1, {{rd[0-9]+}}
; CHECK:       st.o {{.*}}, [{{.*}}, 0]
entry:
  %s = alloca i64, align 8
  %big = alloca [200000 x i8], align 8
  store volatile i8 1, ptr %big, align 1
  store volatile i64 7, ptr %s, align 8
  %v = load volatile i64, ptr %s, align 8
  ret i64 %v
}
