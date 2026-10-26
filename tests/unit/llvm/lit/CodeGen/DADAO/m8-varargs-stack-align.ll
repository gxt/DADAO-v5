;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-111t: ADR-0031 D7 stack alignment for 16-byte values.
; There are 16 RD and 16 RF slots.  With both banks filled by named arguments
; the following 8-byte value goes to [rb1, 0]; the f128 behind it must skip the
; odd 8-byte slot and land at [rb1, 16]/[rb1, 24] (high half first, D6), and
; the next 8-byte value at [rb1, 32].  The callee reads the same offsets.
;
; CHECK-LABEL: caller_spill:
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 0]
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 16]
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 24]
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 32]
; CHECK-NOT: st.o {{rd[0-9]+}}, [rb1, 8]
define void @caller_spill() {
entry:
  call i64 (i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64,
             double, double, double, double, double, double, double, double,
             double, double, double, double, double, double, double, double,
             i64, fp128, i64) @callee_spill(
      i64 0, i64 1, i64 2, i64 3, i64 4, i64 5, i64 6, i64 7,
      i64 8, i64 9, i64 10, i64 11, i64 12, i64 13, i64 14, i64 15,
      double 0.0, double 1.0, double 2.0, double 3.0, double 4.0, double 5.0,
      double 6.0, double 7.0, double 8.0, double 9.0, double 10.0,
      double 11.0, double 12.0, double 13.0, double 14.0, double 15.0,
      i64 66, fp128 0xL0000000000000000C000A00000000000, i64 77)
  ret void
}

; The callee reconstructs the same three values from the incoming stack area.
; CHECK-LABEL: callee_spill:
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 0]
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 16]
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 24]
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 32]
; CHECK-NOT: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 8]
define i64 @callee_spill(
    i64 %i0, i64 %i1, i64 %i2, i64 %i3, i64 %i4, i64 %i5, i64 %i6, i64 %i7,
    i64 %i8, i64 %i9, i64 %i10, i64 %i11, i64 %i12, i64 %i13, i64 %i14,
    i64 %i15,
    double %d0, double %d1, double %d2, double %d3, double %d4, double %d5,
    double %d6, double %d7, double %d8, double %d9, double %d10, double %d11,
    double %d12, double %d13, double %d14, double %d15,
    i64 %x, fp128 %ld, i64 %y) {
entry:
  %h = bitcast fp128 %ld to i128
  %lo = trunc i128 %h to i64
  %sh = lshr i128 %h, 64
  %hi = trunc i128 %sh to i64
  %a = add i64 %x, %y
  %b = add i64 %a, %lo
  %r = add i64 %b, %hi
  ret i64 %r
}

; Already aligned: no extra padding slot.  The f128 is the first stack value
; (offset 0) and an 8-byte value follows at 16; no 16-byte skip is inserted.
; CHECK-LABEL: caller_aligned:
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 0]
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 8]
; CHECK-DAG: st.o {{rd[0-9]+}}, [rb1, 16]
; CHECK-NOT: st.o {{rd[0-9]+}}, [rb1, 24]
define void @caller_aligned() {
entry:
  call i64 (i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64,
             double, double, double, double, double, double, double, double,
             double, double, double, double, double, double, double, double,
             fp128, i64) @callee_aligned(
      i64 0, i64 1, i64 2, i64 3, i64 4, i64 5, i64 6, i64 7,
      i64 8, i64 9, i64 10, i64 11, i64 12, i64 13, i64 14, i64 15,
      double 0.0, double 1.0, double 2.0, double 3.0, double 4.0, double 5.0,
      double 6.0, double 7.0, double 8.0, double 9.0, double 10.0,
      double 11.0, double 12.0, double 13.0, double 14.0, double 15.0,
      fp128 0xL0000000000000000C000A00000000000, i64 77)
  ret void
}

; CHECK-LABEL: callee_aligned:
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 0]
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 8]
; CHECK-DAG: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 16]
; CHECK-NOT: ld.o {{rd[0-9]+}}, [{{rb[0-9]+}}, 24]
define i64 @callee_aligned(
    i64 %i0, i64 %i1, i64 %i2, i64 %i3, i64 %i4, i64 %i5, i64 %i6, i64 %i7,
    i64 %i8, i64 %i9, i64 %i10, i64 %i11, i64 %i12, i64 %i13, i64 %i14,
    i64 %i15,
    double %d0, double %d1, double %d2, double %d3, double %d4, double %d5,
    double %d6, double %d7, double %d8, double %d9, double %d10, double %d11,
    double %d12, double %d13, double %d14, double %d15,
    fp128 %ld, i64 %y) {
entry:
  %h = bitcast fp128 %ld to i128
  %lo = trunc i128 %h to i64
  %sh = lshr i128 %h, 64
  %hi = trunc i128 %sh to i64
  %a = add i64 %lo, %y
  %r = add i64 %a, %hi
  ret i64 %r
}
