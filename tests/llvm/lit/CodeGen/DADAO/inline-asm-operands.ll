;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-118t / ISS-222 ①: `$N` (C source: `%N`) operand references.
;
; AsmPrinter's base PrintAsmOperand only knows the generic operand modifiers
; (`c`/`n`/`s`/`a`) and returns "unsupported" for a plain operand reference, so
; before this change every `$0` was substituted as the *empty string*:
;   rb2rd %0, rb3, 1  ->  rb2rd , rb3, 1
; and `llc` failed with `error: invalid operand in inline asm: '...'` followed by
; an assembler error on the empty operand (`unknown token in expression`).
;
; The checks below pin the substituted text: a register prints with its assembly
; name (the `rd`/`rb`/`rf` spelling the MC printer uses) and an immediate prints
; as a decimal literal.  If the operand were substituted empty, the register
; patterns below (`rd{{[0-9]+}}, 5`) could not match.
;
; Memory operands are covered separately in inline-asm-m.ll (LLVM-119t): they are
; selected into a (base register, simm12 offset) pair and printed `[rb, off]`.

; A register operand tied to the output: `add.si rdN, 5`.
define i64 @reg_operand(i64 %a) {
; CHECK-LABEL: reg_operand:
; CHECK:       add.si rd{{[0-9]+}}, 5
entry:
  %r = call i64 asm "add.si $0, 5", "=r,0"(i64 %a)
  ret i64 %r
}

; An immediate operand ("i"): the literal reaches the text, not an empty slot.
define void @imm_operand() {
; CHECK-LABEL: imm_operand:
; CHECK:       swym 3
entry:
  call void asm sideeffect "swym $0", "i"(i64 3)
  ret void
}

; Two operand references in one asm block, each naming its own register.
define i64 @two_operands(i64 %a, i64 %b) {
; CHECK-LABEL: two_operands:
; CHECK:       add.si rd{{[0-9]+}}, 7
; CHECK:       add.si rd{{[0-9]+}}, 9
entry:
  %r = call i64 asm "add.si $0, 7\0A\09add.si $1, 9", "=r,r,0"(i64 %a, i64 %b)
  ret i64 %r
}

; A global-address operand prints through the normal symbol printer.
@g = external global i64
define void @global_operand() {
; CHECK-LABEL: global_operand:
; CHECK:       set.zw rd5, wp0, g
entry:
  call void asm sideeffect "set.zw rd5, wp0, $0", "i"(ptr @g)
  ret void
}

; The pre-LLVM-118t output was exactly the empty form `add.si , N`; no operand
; reference may ever print that way again.
; CHECK-NOT: add.si ,
