; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; m14-llvm-003: `-fpatchable-function-entry=N[,M]` slot emission, structural
; level.  The frontend turns the driver option into the function attributes
; "patchable-function-entry" (= N-M) and "patchable-function-prefix" (= M); the
; generic `PatchableFunction` pass then inserts one PATCHABLE_FUNCTION_ENTER at
; the top of the entry block, and DADAO lowers it to N-M `swym 0` words.
;
; Contract (task m14-llvm-003 接口规范 1/2):
;   * a slot is exactly one 4-byte word `swym 0` (= 0x47880000, the same word
;     DADAOAsmBackend::writeNopData pads with; contract-isa.md §13.1/§13.3);
;   * the N-M slots sit *after* the function symbol and before the first real
;     instruction (frame setup included);
;   * the M prefix slots sit *before* the function symbol, so `&f` still names
;     the first slot after the prefix (the generic AsmPrinter emits them);
;   * no attribute => no slot at all.
;
; Both optimization levels are checked: PatchableFunction runs *before* the
; DADAO pre-emit passes (`DADAOLoadStoreOptimizer`, `BranchRelaxation`), so
; those must tolerate the pseudo (risk 1 in the task book).
;
; The object/relocation side of the contract is pinned by
; tests/unit/llvm/e2e/lit/patchable_function_entry.test.

target triple = "dadao-unknown-elf"

; Two slots after the symbol, then the real body.  CHECK-NEXT between the two
; `swym 0` lines is what makes this a *contiguity* assertion rather than "some
; nop appears in the file".
; CHECK-LABEL: two:
; CHECK:         swym 0
; CHECK-NEXT:    swym 0
; CHECK-NEXT:    set.zw
define i64 @two() #0 {
  ret i64 42
}

; Same shape without the attribute: the anchoring label plus CHECK-NOT scopes
; the absence to this function's body, so the slots of `two:` above cannot
; satisfy it.
; CHECK-LABEL: plain:
; CHECK-NOT:     swym 0
; CHECK:         set.zw
; CHECK:         ret
define i64 @plain() {
  ret i64 42
}

; N=1, M=1: exactly one slot before the symbol and one after it.
; CHECK:         swym 0
; CHECK-NEXT:    prefixed:
; CHECK:         swym 0
; CHECK-NEXT:    set.zw
define i64 @prefixed() #1 {
  ret i64 42
}

; N=2 (M=0) on a body that keeps the pre-emit passes busy (a loop, a call and
; enough stores for the load/store optimizer to inspect a run).
; CHECK-LABEL: busy:
; CHECK:         swym 0
; CHECK-NEXT:    swym 0
define void @busy(ptr %p, i64 %n) #0 {
entry:
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %i.next, %loop ]
  %slot = getelementptr i64, ptr %p, i64 %i
  store i64 %i, ptr %slot
  %i.next = add nuw nsw i64 %i, 1
  %done = icmp eq i64 %i.next, %n
  br i1 %done, label %exit, label %loop

exit:
  call void @observe(ptr %p)
  ret void
}

declare void @observe(ptr)

attributes #0 = { "patchable-function-entry"="2" }
attributes #1 = { "patchable-function-entry"="1" "patchable-function-prefix"="1" }
