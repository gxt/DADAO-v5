; Stack protector (SSP) guard lowering (m14-llvm-002).
;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s --check-prefix=SP
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s --check-prefix=SP
;
; The DADAO backend has no IR stack guard: getIRStackGuard() is null, so
; StackProtector inserts `llvm.stackguard` and SelectionDAG lowers it through
; getSDagStackGuard(), i.e. RTLIB::STACK_CHECK_GUARD ->
; __stack_chk_guard.  The fail block is RTLIB::STACKPROTECTOR_CHECK_FAIL ->
; __stack_chk_fail.  Both are registered in
; DADAOSubtarget::initLibcallLoweringInfo; without them codegen reported
; "unable to lower stackguard" / "no libcall available for stack protector".
;
; What a protected function must look like (checked per function below):
;   1. prologue: the address of the external __stack_chk_guard is formed and
;      the guard is loaded from it (one 8-byte load -- the canary is
;      pointer-wide), then stored into the frame canary slot;
;   2. epilogue: the guard is re-loaded and the frame slot compared against it
;      with a conditional branch to the fail block;
;   3. fail block: a call to __stack_chk_fail (void(void), noreturn).
;
; The second function here has exactly the same shape but no ssp attribute, and
; the CHECK-NOT lines are anchored between its label and the next one, so a
; stray canary in an unprotected function is caught without turning the check
; into a whole-file grep.
;
; The 16-byte buffer is written volatile-ly so neither the array nor the loop
; can be folded away at -O2 -- the protection decision must be visible in the
; -O2 output too, not only at -O0.

target datalayout = "E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128"
target triple = "dadao-unknown-elf"

; SP-LABEL: sp_protected:
; SP: set.zw {{rb[0-9]+}}, wp0, __stack_chk_guard
; SP-NEXT: or.w {{rb[0-9]+}}, wp1, __stack_chk_guard
; SP-NEXT: or.w {{rb[0-9]+}}, wp2, __stack_chk_guard
; SP-NEXT: ld.o [[CANARY:rd[0-9]+]], [{{rb[0-9]+}}, 0]
; SP-NEXT: st.o [[CANARY]], [{{rb[0-9]+}}, {{-?[0-9]+}}]
; SP: ld.o [[CMP0:rd[0-9]+]], [{{rb[0-9]+}}, 0]
; SP-NEXT: ld.o [[CMP1:rd[0-9]+]], [{{rb[0-9]+}}, {{-?[0-9]+}}]
; SP-NEXT: br.ne {[[CMP0]], [[CMP1]]}?, [rb0, {{.+}}]
; SP: call [rb0, __stack_chk_fail]
define i8 @sp_protected(i32 %n) #0 {
entry:
  %buf = alloca [16 x i8], align 1
  %p = getelementptr [16 x i8], ptr %buf, i64 0, i64 0
  store volatile i8 1, ptr %p
  %v = load volatile i8, ptr %p
  ret i8 %v
}

; SP-LABEL: sp_unprotected:
; SP-NOT: __stack_chk_guard
; SP-NOT: __stack_chk_fail
; SP-LABEL: .Lfunc_end{{[0-9]+}}:
define i8 @sp_unprotected(i32 %n) #1 {
entry:
  %buf = alloca [16 x i8], align 1
  %p = getelementptr [16 x i8], ptr %buf, i64 0, i64 0
  store volatile i8 1, ptr %p
  %v = load volatile i8, ptr %p
  ret i8 %v
}

attributes #0 = { noinline sspstrong }
attributes #1 = { noinline }
