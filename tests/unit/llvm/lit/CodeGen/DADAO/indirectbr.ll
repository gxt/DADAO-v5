;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-102t (ISS-267 ②): indirect branch (`indirectbr`, C `goto *p`).
; SelectionDAGBuilder turns `indirectbr` into ISD::BRIND; the backend had no
; action, no pattern and no selector case, so any computed goto died with
; "Cannot select: ... brind" (llvm-test-suite SingleSource/Benchmarks/Misc/
; evalloop).  DADAO has no absolute jump other than the rrii form
;   Addr = rbha + rdhb + (imms12 << 2)          (contract-isa.md §8.3)
; whose base must be an RB register (rb0 is the IP and cannot be the base), so
; LowerBRIND copies the target -- a C data value, i.e. RD bank -- into a GPRB
; virtual register (CopyToReg -> rd2rb) and the selector emits
;   jump rbtarget, rd0, 0
; (rd0 is the hardwired zero).  The two checks below are exactly that shape.
;

; An i64 target arrives in the data bank (GPRD): crossing to RB is a `rd2rb`.
define i32 @indirectbr_data(i64 %addr) {
; CHECK-LABEL: indirectbr_data:
; CHECK: rd2rb {rb[[TGT:[0-9]+]]}, {rd{{[0-9]+}}}
; CHECK-NEXT: jump [rb[[TGT]], rd0, 0]
entry:
  %p = inttoptr i64 %addr to ptr
  indirectbr ptr %p, [label %L1]
L1:
  ret i32 1
}

; A pointer target is already in the base bank (GPRB): no bank move, the
; `jump` uses it directly.
define i32 @indirectbr_ptr(ptr %p) {
; CHECK-LABEL: indirectbr_ptr:
; CHECK-NOT: rd2rb
; CHECK: jump [rb{{[0-9]+}}, rd0, 0]
entry:
  indirectbr ptr %p, [label %L1]
L1:
  ret i32 2
}
