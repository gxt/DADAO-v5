;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-106t: `long double` = IEEE binary128 (ADR-0030 D1).  The target has no
; 128-bit floating-point register and no binary128 ALU, so:
;   * every value travels as two 64-bit halves in an EVEN/ODD RF slot pair with
;     the HIGH half in the even slot (rf16/rf17 for arguments, rf8/rf9 for
;     returns, ADR-0030 D2 as revised by ADR-0031 D6);
;   * every arithmetic / comparison / conversion is lowered by the type
;     legalizer to the compiler-rt TF libcall named here.
;
; The expected symbols are the compiler-rt entry points (`GENERIC_TF_SOURCES`,
; RTLIB addtf3/subtf3/multf3/divtf3, extenddftf2/trunctfdf2, fixtfdi/floatditf,
; lttf2/unordtf2/eqtf2) -- they are NOT read back from the backend.

declare fp128 @llvm.fabs.f128(fp128)

; --- arithmetic: one libcall each, arguments already in rf16..rf19 and the
; result in rf8/rf9, so a one-line pass-through needs no register moves.
define fp128 @f128_add(fp128 %a, fp128 %b) {
; CHECK-LABEL: f128_add:
; CHECK-NEXT: %bb.0:
; CHECK-NEXT: call [rb0, __addtf3]
; CHECK-NEXT: ret rd0, 0
  %r = fadd fp128 %a, %b
  ret fp128 %r
}

define fp128 @f128_math(fp128 %a, fp128 %b) {
; CHECK-LABEL: f128_math:
; CHECK-DAG: call [rb0, __subtf3]
; CHECK-DAG: call [rb0, __multf3]
; CHECK-DAG: call [rb0, __divtf3]
  %s = fsub fp128 %a, %b
  %m = fmul fp128 %s, %b
  %d = fdiv fp128 %m, %a
  ret fp128 %d
}

; --- memory image: high half at the LOWER address (big endian).  The value
; arrives in rf16 (high) / rf17 (low); `st.o` must write rf16 first.
define void @f128_store(fp128 %a, ptr %p) {
; CHECK-LABEL: f128_store:
; CHECK: rf2rd {rd{{[0-9]+}}}, {rf17}
; CHECK: rf2rd {rd{{[0-9]+}}}, {rf16}
; CHECK: st.o {{rd[0-9]+}}, [rb16, 8]
; CHECK: st.o {{rd[0-9]+}}, [rb16, 0]
  store fp128 %a, ptr %p, align 16
  ret void
}

; ... and a load feeds rf8 (high, offset 0) then rf9 (low, offset 8).
define fp128 @f128_load(ptr %p) {
; CHECK-LABEL: f128_load:
; CHECK: ld.o {{rd[0-9]+}}, [rb16, 0]
; CHECK: ld.o {{rd[0-9]+}}, [rb16, 8]
; CHECK: rd2rf {rf8}, {rd4}
; CHECK: rd2rf {rf9}, {rd5}
  %a = load fp128, ptr %p, align 16
  ret fp128 %a
}

; --- conversions (binary128 <-> binary64 / integer).
define double @f128_to_double(fp128 %a) {
; CHECK-LABEL: f128_to_double:
; CHECK: call [rb0, __trunctfdf2]
  %d = fptrunc fp128 %a to double
  ret double %d
}

define fp128 @double_to_f128(double %d) {
; CHECK-LABEL: double_to_f128:
; CHECK: call [rb0, __extenddftf2]
  %r = fpext double %d to fp128
  ret fp128 %r
}

define i64 @f128_to_i64(fp128 %a) {
; CHECK-LABEL: f128_to_i64:
; CHECK: call [rb0, __fixtfdi]
  %i = fptosi fp128 %a to i64
  ret i64 %i
}

define i64 @f128_to_u64(fp128 %a) {
; CHECK-LABEL: f128_to_u64:
; CHECK: call [rb0, __fixunstfdi]
  %i = fptoui fp128 %a to i64
  ret i64 %i
}

define fp128 @i64_to_f128(i64 %i) {
; CHECK-LABEL: i64_to_f128:
; CHECK: call [rb0, __floatditf]
  %r = sitofp i64 %i to fp128
  ret fp128 %r
}

define fp128 @u64_to_f128(i64 %i) {
; CHECK-LABEL: u64_to_f128:
; CHECK: call [rb0, __floatunditf]
  %r = uitofp i64 %i to fp128
  ret fp128 %r
}

; --- comparisons (`softenSetCCOperands`): ordered LT uses __lttf2; an
; unordered-equal predicate needs __unordtf2 followed by __eqtf2.
define i1 @f128_lt(fp128 %a, fp128 %b) {
; CHECK-LABEL: f128_lt:
; CHECK: call [rb0, __lttf2]
  %r = fcmp olt fp128 %a, %b
  ret i1 %r
}

define i1 @f128_ueq(fp128 %a, fp128 %b) {
; CHECK-LABEL: f128_ueq:
; CHECK-DAG: call [rb0, __unordtf2]
; CHECK-DAG: call [rb0, __eqtf2]
  %r = fcmp ueq fp128 %a, %b
  ret i1 %r
}

; --- constants: materialised as two 64-bit halves in the data bank and moved
; into the return pair (rf8 = 0x3fff000000000000 = high half of 1.0L,
; rf9 = 0x0000000000000000 = low half).
define fp128 @f128_const() {
; CHECK-LABEL: f128_const:
; CHECK: set.zw rd{{[0-9]+}}, wp3, 0x3fff
; CHECK: rd2rf {rf8}, {rd4}
; CHECK: rd2rf {rf9}, {rd5}
  ret fp128 0xL00000000000000003FFF000000000000
}
