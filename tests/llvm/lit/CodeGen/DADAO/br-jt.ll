;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-072t (M6, ISS-177 / G3): a dense `switch` is lowered to a jump table.
; Before this task the backend had no ISD::BR_JT lowering, so any program with a
; dense switch failed to compile ("Cannot select: ... br_jt ...").
;
; The DADAO jump table lives in a read-only data section and holds one 8-byte
; absolute case address per entry (EK_BlockAddress; each `.dd.o64 LBB` becomes an
; R_DADAO_ABS48 field, contract-elf.md §2-§4).  The dispatch
;   * materializes the table base into an address register (GPRB) with the fixed
;     3-slice set.zw/or.w/or.w sequence (same mechanism as GLOBAL_ADDR, ABS48),
;   * scales the (x - mincase) index by the 8-byte entry size,
;   * adds it to the table base, loads the 8-byte case address, and
;   * jumps through it with the rrii indirect jump
;       `jump rb, rd, imm12`  (Addr = rb + rd + (imm << 2); rd0 = 0)
;     (contract-isa.md §8.3).
;
target triple = "dadao-unknown-elf"

define i64 @jt(i64 %x) {
entry:
  switch i64 %x, label %default [
    i64 0, label %c0
    i64 1, label %c1
    i64 2, label %c2
    i64 3, label %c3
    i64 4, label %c4
    i64 5, label %c5
    i64 6, label %c6
    i64 7, label %c7
    i64 8, label %c8
    i64 9, label %c9
    i64 10, label %c10
    i64 11, label %c11
    i64 12, label %c12
    i64 13, label %c13
    i64 14, label %c14
    i64 15, label %c15
  ]
c0:  ret i64 10
c1:  ret i64 11
c2:  ret i64 12
c3:  ret i64 13
c4:  ret i64 14
c5:  ret i64 15
c6:  ret i64 16
c7:  ret i64 17
c8:  ret i64 18
c9:  ret i64 19
c10: ret i64 20
c11: ret i64 21
c12: ret i64 22
c13: ret i64 23
c14: ret i64 24
c15: ret i64 25
default: ret i64 0
}

; The dispatch: table base materialization (one set.zw + two or.w, all against
; the jump-table label), index scaling, base+index add, the 8-byte load and the
; indirect jump through the loaded address (rd0 supplies the zero offset).
; CHECK-LABEL: jt:
; CHECK-DAG: shl.uo rd{{[0-9]+}}, rd{{[0-9]+}}, 3
; CHECK-DAG: set.zw rb{{[0-9]+}}, wp0, [[JTI:\.LJTI[0-9]+_[0-9]+]]
; CHECK-DAG: or.w rb{{[0-9]+}}, wp1, [[JTI]]
; CHECK-DAG: or.w rb{{[0-9]+}}, wp2, [[JTI]]
; CHECK: add.o rb{{[0-9]+}}, rb{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: ld.o rb{{[0-9]+}}, [rb{{[0-9]+}}, 0]
; CHECK: jump [rb{{[0-9]+}}, rd0, 0]

; The table is emitted in the read-only data section (not .text), 8-byte aligned,
; one `.dd.o64 LBB` absolute case address per entry (the DADAO 8-byte
; data directive; contract-asm.md §7.1).
; CHECK: .section .rodata
; CHECK: .p2align 3
; CHECK: [[JTI]]:
; CHECK-NEXT: .dd.o64 .LBB
