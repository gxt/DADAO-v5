; RUN: %llc -mtriple=dadao -O2 -stop-after=dadao-pointer-phi-bank -o - %s | %FileCheck %s --check-prefix=MIR
; RUN: %llc -mtriple=dadao -O2 -o - %s | %FileCheck %s --check-prefix=ASM

; Positive prototype: direct pointer PHI plus two GEPs is the only shape
; rewritten by DADAOPointerPHIBank.  The loop-carried PHI and both GEP results
; must remain GPRB, with no loop bank bridge or spill/reload.
define void @m10_direct_loop(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %loop ]
  %v = load i64, ptr %p, align 8
  %q = getelementptr i64, ptr %p, i64 1
  store i64 %v, ptr %out, align 8
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; ptr-int provenance is not a candidate for the pass.
define void @m10_ptrint_fallback(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %raw = ptrtoint ptr %base to i64
  %sum = add i64 %raw, %i
  %p = inttoptr i64 %sum to ptr
  %v = load volatile i64, ptr %p, align 8
  store volatile i64 %v, ptr %out, align 8
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

declare void @m10_sink(ptr)

; Ordinary i64 PHI has a GPRD entry and must not be treated as a pointer.
define i64 @m10_integer_phi_fallback(i64 %seed, i64 %n) {
entry:
  br label %loop
loop:
  %x = phi i64 [ %seed, %entry ], [ %next, %loop ]
  %y = add i64 %x, 1
  %next = add i64 %y, 2
  %cond = icmp ult i64 %next, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret i64 %next
}

; Calls are an ABI boundary and must retain the old fallback path.
define void @m10_cross_call(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  call void @m10_sink(ptr %base)
  %p = getelementptr i64, ptr %base, i64 %i
  %v = load volatile i64, ptr %p, align 8
  store volatile i64 %v, ptr %out, align 8
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; select-derived bases are not rewritten by the exact direct-PHI prototype.
define void @m10_select_fallback(ptr %a, ptr %b, ptr %out, i1 %sel, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %base = select i1 %sel, ptr %a, ptr %b
  %p = getelementptr i64, ptr %base, i64 %i
  %v = load volatile i64, ptr %p, align 8
  store volatile i64 %v, ptr %out, align 8
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Multiple incoming edges are not rewritten.
define void @m10_multi_phi(ptr %base, ptr %out, i1 %choose, i64 %n) {
entry:
  br i1 %choose, label %left, label %right
left:
  br label %loop
right:
  br label %loop
loop:
  %i = phi i64 [ 0, %left ], [ 0, %right ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %left ], [ %base, %right ], [ %nextp, %loop ]
  %v = load volatile i64, ptr %p, align 8
  store volatile i64 %v, ptr %out, align 8
  %nextp = getelementptr i64, ptr %p, i64 1
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; inline asm "r" remains ordinary data-bank input.
define i64 @m10_inline_asm_r(ptr %p) {
  %raw = ptrtoint ptr %p to i64
  %out = call i64 asm sideeffect "", "=r,r"(i64 %raw)
  ret i64 %out
}

; MIR-LABEL: name: m10_direct_loop
; MIR: {{%[0-9]+}}:gprb = PHI
; MIR: {{%[0-9]+}}:gprd = PHI
; ASM-LABEL: m10_direct_loop:
; ASM-NOT: rd2rb
; ASM-NOT: Folded Spill
; ASM-NOT: Folded Reload
; ASM: add.o
