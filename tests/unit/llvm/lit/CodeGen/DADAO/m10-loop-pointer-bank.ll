; RUN: %llc -mtriple=dadao -O2 -verify-machineinstrs -stop-after=dadao-pointer-phi-bank -o - %s | %FileCheck %s --check-prefix=MIR
; RUN: %llc -mtriple=dadao -O2 -verify-machineinstrs -o - %s | %FileCheck %s --check-prefix=ASM
;
; LLVM-139t: `DADAOPointerPHIBank` (post-ISel, pre-RA) rebuilds the exact
; loop-carried pointer-induction shape in the address bank.  The i64 PHI and
; both adds start in GPRD because SelectionDAG types a `phi ptr` as i64, which
; puts a `rd2rb` bridge (and an `rd2rd` + `add.si` for the update) inside the
; loop.  After the rewrite the PHI, `%sum` and `%next` are GPRB and the two
; updates are `add.o rb, rb, rd` (contract-isa.md §7.1, ADR-0018 C14), so the
; loop body keeps no bank bridge.
;
; The metric here is assembly-level: it removes `rd2rb`/`rd2rd` bridges, it is
; not a whole-program performance claim.
;
; Both run lines verify machine instructions: after `-stop-after=` for the
; rewritten MIR (operand classes, PHI operand classes, def/use consistency) and
; on the final assembly (register allocation, kill flags, liveness).
;
; The positives are the direct PHI (bridge and adds in the loop block) and a
; cross-block COPY (the only address use sits in a dominated exit block, which
; pins the dominance proof rather than "a COPY exists somewhere").  Every other
; case below is a deliberate fallback: the old GPRD path and its rd2rb bridge
; must stay.

target triple = "dadao-unknown-elf"

declare void @m10_sink(ptr)

; Positive: the bridge COPY and both adds are in the loop block.  The rebuilt
; PHI keeps the GPRB entry value and the GPRB backedge value; the element
; offset constant is hoisted to the preheader (`CONST_WYDE 8`).
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

; Positive: the only use of the pointer PHI as an address is in a block that
; the loop header dominates, so the bridge COPY lives in the exit block.  The
; rebuild is still valid (the new PHI dominates every former use of COPY %p).
define void @m10_cross_block_copy(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %loop ]
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  ret void
}

; Positive: two independent pointer chains in the same loop block.  Both are
; rebuilt (the scan restarts after each accepted candidate); the first one uses
; a negative element offset, so the hoisted constant exercises CONST_WYDE's
; negative materialization as well.
define void @m10_two_chains(ptr %a, ptr %b, ptr %o1, ptr %o2, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %ni, %loop ]
  %p = phi ptr [ %a, %entry ], [ %np, %loop ]
  %q = phi ptr [ %b, %entry ], [ %nq, %loop ]
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %o1, align 8
  %w = load i64, ptr %q, align 8
  store i64 %w, ptr %o2, align 8
  %g1 = getelementptr i64, ptr %p, i64 -2
  %np = getelementptr i64, ptr %g1, i64 %i
  %g2 = getelementptr i64, ptr %q, i64 1
  %nq = getelementptr i64, ptr %g2, i64 %i
  %ni = add i64 %i, 1
  %c = icmp ult i64 %ni, %n
  br i1 %c, label %loop, label %exit
exit:
  ret void
}

; Positive: the pointer loop is nested inside another loop.  The rebuilt PHI is
; in the inner header and the hoisted element-offset constant goes to the inner
; preheader (a block inside the outer loop), not to the function entry.
define void @m10_nested_loop(ptr %base, ptr %out, i64 %n, i64 %m) {
entry:
  br label %outer
outer:
  %j = phi i64 [ 0, %entry ], [ %nj, %done ]
  br label %inner
inner:
  %i = phi i64 [ 0, %outer ], [ %nexti, %inner ]
  %p = phi ptr [ %base, %outer ], [ %nextp, %inner ]
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %c = icmp ult i64 %nexti, %m
  br i1 %c, label %inner, label %done
done:
  %nj = add i64 %j, 1
  %c2 = icmp ult i64 %nj, %n
  br i1 %c2, label %outer, label %exit
exit:
  ret void
}

; Negative: a call in the loop is an ABI boundary; the address keeps the old
; rd2rb bridge (the loop body must still register-bridge for the load).
define void @m10_loop_call(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %loop ]
  call void @m10_sink(ptr %p)
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Negative: two backedges (two latches) — the exact single-entry/single-backedge
; shape is required, so both the PHI (7 operands) and the two update chains stay
; GPRD.
define void @m10_multi_backedge(ptr %base, ptr %out, i1 %choose, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %ni1, %left ], [ %ni2, %right ]
  %p = phi ptr [ %base, %entry ], [ %np1, %left ], [ %np2, %right ]
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  br i1 %choose, label %left, label %right
left:
  %q1 = getelementptr i64, ptr %p, i64 1
  %np1 = getelementptr i64, ptr %q1, i64 %i
  %ni1 = add i64 %i, 1
  br label %loop
right:
  %q2 = getelementptr i64, ptr %p, i64 1
  %np2 = getelementptr i64, ptr %q2, i64 %i
  %ni2 = add i64 %i, 2
  br label %loop
}

; Negative: a switch splits the loop, so the header is not the latch and the
; update chain is not in the PHI's block.  (The switch itself becomes a jump
; table; none of that may be rewritten.)
define void @m10_switch_loop(ptr %base, ptr %out, i64 %n, i32 %sel) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %next ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %next ]
  %v = load i64, ptr %p, align 8
  switch i32 %sel, label %next [ i32 0, label %case0
                                 i32 1, label %case1 ]
case0:
  store i64 %v, ptr %out, align 8
  br label %next
case1:
  store i64 1, ptr %out, align 8
  br label %next
next:
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Negative: a select-derived backedge value has no pointer provenance the pass
; can vouch for (the backedge def is a conditional assignment, not ADD_IMM).
define void @m10_select_backedge(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %loop ]
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  %q = getelementptr i64, ptr %p, i64 1
  %g = getelementptr i64, ptr %q, i64 %i
  %use = icmp ult i64 %i, 4
  %nextp = select i1 %use, ptr %g, ptr %base
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Negative: inline asm in the loop is an opaque boundary; the old path remains.
define void @m10_inline_asm_loop(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %loop ]
  call void asm sideeffect "", "~{memory}"()
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Negative: the pointer PHI has a third use (a null comparison), so the value
; stays observable as an i64/GPRD value; rewriting only the address uses would
; drop that use, hence the whole chain keeps the old path.
define void @m10_extra_use(ptr %base, ptr %out, i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %p = phi ptr [ %base, %entry ], [ %nextp, %loop ]
  %v = load i64, ptr %p, align 8
  %isnull = icmp eq ptr %p, null
  %z = zext i1 %isnull to i64
  %w = add i64 %v, %z
  store i64 %w, ptr %out, align 8
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Negative: the induction value is an integer that only becomes a pointer via
; inttoptr; its entry value is in GPRD, so there is no address-bank provenance
; to preserve and the old bridge stays.
define void @m10_ptrint_phi(ptr %base, ptr %out, i64 %n) {
entry:
  %raw0 = ptrtoint ptr %base to i64
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %nexti, %loop ]
  %raw = phi i64 [ %raw0, %entry ], [ %nextraw, %loop ]
  %p = inttoptr i64 %raw to ptr
  %v = load i64, ptr %p, align 8
  store i64 %v, ptr %out, align 8
  %q = getelementptr i64, ptr %p, i64 1
  %nextp = getelementptr i64, ptr %q, i64 %i
  %nextraw = ptrtoint ptr %nextp to i64
  %nexti = add i64 %i, 1
  %cond = icmp ult i64 %nexti, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret void
}

; Negative: a plain i64 induction variable with the same two-add shape.  Its
; entry value is a data value, so no rewrite may happen (the pass must not
; change the global i64 register class).
define i64 @m10_i64_phi(i64 %seed, i64 %n, i64 %step) {
entry:
  br label %loop
loop:
  %x = phi i64 [ %seed, %entry ], [ %next, %loop ]
  %sum = add i64 %x, %step
  %next = add i64 %sum, 8
  %cond = icmp ult i64 %next, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret i64 %next
}

; MIR is printed with the register class only on definitions, so a rebuilt
; chain is an `:gprb` PHI plus two `add_o_bbd` whose destination is `:gprb`;
; every fallback keeps a `:gprb = COPY` bridge and no `add_o_bbd` at all.
; MIR-LABEL: name: m10_direct_loop
; MIR:         %{{[0-9]+}}:gprd = CONST_WYDE 8
; MIR:         %[[DPHI:[0-9]+]]:gprb = PHI %{{[0-9]+}}, %bb.0, %{{[0-9]+}}, %bb.1
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd %[[DPHI]],
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR-LABEL: name: m10_cross_block_copy
; MIR:         %[[CPHI:[0-9]+]]:gprb = PHI %{{[0-9]+}}, %bb.0, %{{[0-9]+}}, %bb.1
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd %[[CPHI]],
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR-LABEL: name: m10_two_chains
; MIR:         %[[TP:[0-9]+]]:gprd = CONST_WYDE -16
; MIR:         %[[TP2:[0-9]+]]:gprb = PHI %{{[0-9]+}}, %bb.0, %{{[0-9]+}}, %bb.1
; MIR:         %{{[0-9]+}}:gprb = PHI %{{[0-9]+}}, %bb.0, %{{[0-9]+}}, %bb.1
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR-LABEL: name: m10_nested_loop
; MIR:         %{{[0-9]+}}:gprd = CONST_WYDE 8
; MIR:         %[[NPHI:[0-9]+]]:gprb = PHI %{{[0-9]+}}, %bb.1, %{{[0-9]+}}, %bb.2
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd %[[NPHI]],
; MIR:         %{{[0-9]+}}:gprb = add_o_bbd
; MIR-LABEL: name: m10_loop_call
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR:         %{{[0-9]+}}:gprd = ADD_IMM_PSEUDO
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_multi_backedge
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_switch_loop
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_select_backedge
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_inline_asm_loop
; MIR:         INLINEASM
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_extra_use
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_ptrint_phi
; MIR:         %{{[0-9]+}}:gprb = COPY %
; MIR-NOT:     add_o_bbd
; MIR-LABEL: name: m10_i64_phi
; MIR-NOT:     add_o_bbd
; MIR-NOT:     :gprb = PHI
;
; The loop body of each positive has no bank bridge at all; every fallback
; function keeps the `rd2rb` that feeds its address use.
; ASM-LABEL: m10_direct_loop:
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM-NOT:     Folded Spill
; ASM-NOT:     Folded Reload
; ASM:         add.o rb{{[0-9]+}}, rb{{[0-9]+}}, rd{{[0-9]+}}
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM-LABEL: m10_cross_block_copy:
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM:         add.o rb{{[0-9]+}}, rb{{[0-9]+}}, rd{{[0-9]+}}
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM-LABEL: m10_two_chains:
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM:         add.o rb{{[0-9]+}}, rb{{[0-9]+}}, rd{{[0-9]+}}
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM-LABEL: m10_nested_loop:
; ASM-NOT:     rd2rb
; ASM-NOT:     rd2rd
; ASM:         add.o rb{{[0-9]+}}, rb{{[0-9]+}}, rd{{[0-9]+}}
; ASM-NOT:     rd2rb
; ASM-LABEL: m10_loop_call:
; ASM:         call
; ASM:         rd2rb
; ASM-LABEL: m10_multi_backedge:
; ASM-NOT:     add.o
; ASM:         rd2rb
; ASM-LABEL: m10_switch_loop:
; ASM:         rd2rb
; ASM-LABEL: m10_select_backedge:
; ASM:         rd2rb
; ASM-NOT:     add.o
; ASM-LABEL: m10_inline_asm_loop:
; ASM:         @@APP
; ASM:         rd2rb
; ASM-LABEL: m10_extra_use:
; ASM:         rd2rb
; ASM-NOT:     add.o
; ASM-LABEL: m10_ptrint_phi:
; ASM:         rd2rb
; ASM-NOT:     add.o
; ASM-LABEL: m10_i64_phi:
; ASM-NOT:     add.o
