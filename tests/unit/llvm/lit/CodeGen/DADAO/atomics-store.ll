;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-121t rework (ISS-312): an atomic store must store the *value*, never the
; address of the object.  `ATOMIC_STORE` operands are (chain, value, ptr), so
; the lowering must read `getVal()` (operand 1) and `getBasePtr()` (operand 2)
; -- reading operand 2 as the value stores the address instead.
;
; The probes below keep the stored value alive by computing it (`add`), so the
; value and the address cannot be the same register by accident and a dead-code
; copy of the address cannot satisfy the assertion:
;
;   WRONG (stored the address):   <materialise &g> ; rb2rd rd, {rb} ; st.t rd, [rb]
;   RIGHT (stored the value):     rd2rd rd, {rd arg} ; add.si rd, N ; st.t rd, [rb]
;
; The "add <V>" + "st.* <V>" pair is what makes this reachable: with the
; defective lowering the `add` is dead, so the instruction is gone and the first
; CHECK fails (see .work/evidence/LLVM-121t-rework2/run.sh, check A*).
;
; Since LLVM-127t i8/i16/i32 are legal types, the value of a narrow atomic store
; is computed at its own width (`add.sb/sw/st`) instead of being promoted to an
; i64 `add.si`; the store itself is the same width-specific st.b/w/t.
;
@g8  = global i8 0
@g16 = global i16 0
@g32 = global i32 0
@g64 = global i64 0

; 1-byte truncating store (the getTruncStore() branch of the lowering).
define void @store_atomic_i8(i8 %v) {
; CHECK-LABEL: store_atomic_i8:
; CHECK: add.sb [[V:rd[0-9]+]], rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: st.b [[V]], [rb{{[0-9]+}}, {{-?[0-9]+}}]
; CHECK-NOT: rb2rd
  %x = add i8 %v, 3
  store atomic i8 %x, ptr @g8 monotonic, align 1
  ret void
}

; 2-byte store (the value stays at its own width).
define void @store_atomic_i16(i16 %v) {
; CHECK-LABEL: store_atomic_i16:
; CHECK: add.sw [[V:rd[0-9]+]], rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: fence cfx_umon, 4095
; CHECK: st.w [[V]], [rb{{[0-9]+}}, {{-?[0-9]+}}]
; CHECK: fence cfx_umon, 4095
; CHECK-NOT: rb2rd
  %x = add i16 %v, 5
  store atomic i16 %x, ptr @g16 seq_cst, align 2
  ret void
}

; 4-byte store: the same width the ISS-312 probe caught on a shared object.
define void @store_atomic_i32(i32 %v) {
; CHECK-LABEL: store_atomic_i32:
; CHECK: add.st [[V:rd[0-9]+]], rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: fence cfx_umon, 4095
; CHECK: st.t [[V]], [rb{{[0-9]+}}, {{-?[0-9]+}}]
; CHECK: fence cfx_umon, 4095
; CHECK-NOT: rb2rd
  %x = add i32 %v, 7
  store atomic i32 %x, ptr @g32 seq_cst, align 4
  ret void
}

; 8-byte store (release: trailing fence only).
define void @store_atomic_i64(i64 %v) {
; CHECK-LABEL: store_atomic_i64:
; CHECK: fence cfx_umon, 3104
; CHECK: add.si [[V:rd[0-9]+]], 9
; CHECK: st.o [[V]], [rb{{[0-9]+}}, {{-?[0-9]+}}]
; CHECK-NOT: fence
; CHECK-NOT: rb2rd
  %x = add i64 %v, 9
  store atomic i64 %x, ptr @g64 release, align 8
  ret void
}
