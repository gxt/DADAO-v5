;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-086t / ISS-193(e): a lone "r" inline-asm constraint has to name a
; register class.  DADAO maps it to the data bank (GPRD RegClass, i.e. the rd
; registers), the canonical i64 class registered with
; `addRegisterClass(MVT::i64, GPRDRegClass)` (DADAOISelLowering.cpp).  Before
; this override every such operand failed with
;   error: could not allocate output register for constraint 'r'
;   error: could not allocate input reg for constraint 'r'
; so the picolibc compiler-barrier idiom (libc/string/memset_s.c and
; memset_explicit.c: `__asm__ __volatile__("" ::"r"(p) : "memory")`) could not
; be compiled at all.
;
; The checks pin the *bank*, not just "it compiles": an i64 argument is already
; in the data bank (GPRD, rd16+) and a pointer argument in the base bank
; (GPRB, rb16+), and the two banks are only bridged by the explicit rd2rb /
; rb2rd copies.  So a "r" operand that receives a *pointer* forces exactly one
; GPRB->GPRD copy (rb2rd), while an i64 operand forces no cross-bank copy at
; all (a GPRB mapping of "r" would produce rd2rb / rb2rd here instead).

; Integer output + integer inputs: both operands and the result are already in
; the data bank, so no cross-bank copy may appear.
define i64 @int_in_out(i64 %a, i64 %b) {
; CHECK-LABEL: int_in_out:
; CHECK-NOT:   rb2rd
; CHECK-NOT:   rd2rb
; CHECK:       ret
entry:
  %o = call i64 asm sideeffect "", "=r,r,r"(i64 %a, i64 %b)
  ret i64 %o
}

; The exact picolibc compiler-barrier shape: a pointer input plus a "memory"
; clobber, empty asm body.  The pointer arrives in GPRB and must reach the
; "r" operand in GPRD through the explicit rb2rd.
define void @ptr_in_barrier(ptr %p) {
; CHECK-LABEL: ptr_in_barrier:
; CHECK:       rb2rd
entry:
  call void asm sideeffect "", "r,~{memory}"(ptr %p)
  ret void
}

; Integer output + pointer input + "memory" clobber (also gets the compiler
; barrier on the output; the pointer again crosses the bank via rb2rd).
define i64 @ptr_in_int_out(ptr %p) {
; CHECK-LABEL: ptr_in_int_out:
; CHECK:       rb2rd
entry:
  %o = call i64 asm sideeffect "", "=r,r,~{memory}"(ptr %p)
  ret i64 %o
}
