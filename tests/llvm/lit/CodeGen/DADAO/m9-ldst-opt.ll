; RUN: %llc -march=dadao -O2 %s -o - | %FileCheck %s --check-prefix=MERGE
; RUN: %llc -march=dadao -O2 -dadao-disable-ldm-stm %s -o - | %FileCheck %s --check-prefix=NOMERGE
;
; LLVM-129t: the post-RA DADAO load/store optimizer turns a run of adjacent
; 8-byte accesses with consecutive registers and ascending +8 offsets into one
; `stm.o`/`ldm.o`.  Here the four arguments arrive in rd16..rd19 and are stored
; to [rb16, 0..24], so the whole body collapses to a single `stm.o` whose
; offset register is the hardwired-zero `rd0` (first offset 0).
;
; `sum8` is the negative counterpart: the two loads are emitted in descending
; address order ([rb16, 8] then [rb16, 0]) -- `ldm.o` can only walk addresses
; upwards -- so they must stay two separate `ld.o`s.
;
; -dadao-disable-ldm-stm is the reachable FAIL path: the same function then
; keeps four separate `st.o`s.

define void @copy4(ptr %d, i64 %a, i64 %b, i64 %c, i64 %e) {
entry:
  %p0 = getelementptr i64, ptr %d, i64 0
  %p1 = getelementptr i64, ptr %d, i64 1
  %p2 = getelementptr i64, ptr %d, i64 2
  %p3 = getelementptr i64, ptr %d, i64 3
  store i64 %a, ptr %p0, align 8
  store i64 %b, ptr %p1, align 8
  store i64 %c, ptr %p2, align 8
  store i64 %e, ptr %p3, align 8
  ret void
}

define i64 @sum8(ptr %s) {
entry:
  %p0 = getelementptr i64, ptr %s, i64 0
  %p1 = getelementptr i64, ptr %s, i64 1
  %v0 = load i64, ptr %p0, align 8
  %v1 = load i64, ptr %p1, align 8
  %r = add i64 %v0, %v1
  ret i64 %r
}

; MERGE-LABEL: copy4:
; MERGE: stm.o {rd16:rd19}, [rb16, rd0]
; MERGE-NOT: st.o
; MERGE-LABEL: sum8:
; MERGE: ld.o
; MERGE-NEXT: ld.o
; MERGE-NOT: ldm.o
;
; NOMERGE-LABEL: copy4:
; NOMERGE-NOT: stm.o
; NOMERGE: st.o rd16
; NOMERGE-NEXT: st.o rd17
; NOMERGE-NEXT: st.o rd18
; NOMERGE-NEXT: st.o rd19
