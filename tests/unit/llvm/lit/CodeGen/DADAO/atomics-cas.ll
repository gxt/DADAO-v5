;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-121t (ADR-0034 D3-D6; ISS-294): cmpxchg / atomicrmw -> lr/sc retry loop.
;
; The ISA has no AMO and no `__atomic_*` runtime, so every read-modify-write is
; a `lr`/`sc` loop built by DADAOTargetLowering::EmitInstrWithCustomInserter:
;
;   loop:  lr.<w>.an  old, [ptr]
;          br.ne {old, cmp}?, [rb0, done]   ; value changed -> CAS failed
;          sc.<w>.ar  ok, new, [ptr]
;          br.nz {ok}?, [rb0, loop]         ; reservation lost -> retry
;   done:
;
; The width follows the *memory* width of the cmpxchg (b/w/t/o = 1/2/4/8 B).
; That is the whole sub-word story on this ISA: lr.b/lr.w access exactly one
; byte/wyde, and ADR-0034 D6 (as revised 2026-10-21) only requires alignment
; to that width, so a byte CAS can never touch the neighbouring bytes of the
; containing word -- asserted below with CHECK-NOT for the wider forms.
;

; i64 CAS: 8-byte window, acquire on the load and release on the store.
define i64 @cas64(ptr %p, i64 %c, i64 %n) {
; CHECK-LABEL: cas64:
; CHECK: fence cfx_umon, 4095
; CHECK: lr.o.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], rd{{[0-9]+}}}?, [rb0,
; CHECK: sc.o.ar [[OK:rd[0-9]+]], rd{{[0-9]+}}, [rb{{[0-9]+}}]
; CHECK-NEXT: br.nz {[[OK]]}?, [rb0,
; CHECK: fence cfx_umon, 4095
  %r = cmpxchg ptr %p, i64 %c, i64 %n seq_cst seq_cst
  %v = extractvalue { i64, i1 } %r, 0
  ret i64 %v
}

; i32 CAS with acquire ordering: tetra window, only a trailing acquire fence.
define i32 @cas32_acq(ptr %p, i32 %c, i32 %n) {
; CHECK-LABEL: cas32_acq:
; CHECK-NOT: fence cfx_umon, 4095
; CHECK: lr.t.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], rd{{[0-9]+}}}?, [rb0,
; CHECK: sc.t.ar [[OK:rd[0-9]+]], rd{{[0-9]+}}, [rb{{[0-9]+}}]
; CHECK-NEXT: br.nz {[[OK]]}?, [rb0,
; CHECK: fence cfx_umon, 1072
; CHECK-NOT: fence cfx_umon, 4095
  %r = cmpxchg ptr %p, i32 %c, i32 %n acquire monotonic
  %v = extractvalue { i32, i1 } %r, 0
  ret i32 %v
}

; i16 CAS: wyde window only (no word read-modify-write of the 4-byte neighbour).
define i16 @cas16(ptr %p, i16 %c, i16 %n) {
; CHECK-LABEL: cas16:
; CHECK: fence cfx_umon, 4095
; CHECK: lr.w.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT: lr.o
; CHECK-NOT: lr.t
; CHECK: sc.w.ar [[OK:rd[0-9]+]], rd{{[0-9]+}}, [rb{{[0-9]+}}]
; CHECK-NEXT: br.nz {[[OK]]}?, [rb0,
; CHECK-NOT: sc.o
; CHECK-NOT: sc.t
; CHECK: fence cfx_umon, 4095
  %r = cmpxchg ptr %p, i16 %c, i16 %n seq_cst seq_cst
  %v = extractvalue { i16, i1 } %r, 0
  ret i16 %v
}

; i8 CAS: byte window only, so the three neighbouring bytes are never touched.
define i8 @cas8(ptr %p, i8 %c, i8 %n) {
; CHECK-LABEL: cas8:
; CHECK: lr.b.an [[OLD:rd[0-9]+]], [rb{{[0-9]+}}]
; CHECK-NEXT: br.ne {[[OLD]], rd{{[0-9]+}}}?, [rb0,
; CHECK-NOT: lr.o
; CHECK-NOT: lr.t
; CHECK-NOT: lr.w
; CHECK: sc.b.ar [[OK:rd[0-9]+]], rd{{[0-9]+}}, [rb{{[0-9]+}}]
; CHECK-NEXT: br.nz {[[OK]]}?, [rb0,
; CHECK-NOT: sc.o
; CHECK-NOT: sc.t
; CHECK-NOT: sc.w
  %r = cmpxchg ptr %p, i8 %c, i8 %n monotonic monotonic
  %v = extractvalue { i8, i1 } %r, 0
  ret i8 %v
}

; The success flag is `old == cmp`, computed after the loop (cmp.so + cs.z);
; a CAS whose result is unused must still contain the loop.
define void @cas_discard(ptr %p, i64 %c, i64 %n) {
; CHECK-LABEL: cas_discard:
; CHECK: lr.o.an
; CHECK: sc.o.ar
  %r = cmpxchg ptr %p, i64 %c, i64 %n seq_cst seq_cst
  ret void
}

; The success value: `cmp.so` (old vs cmp) feeding `cs.z` with 1/0 arms.
define i1 @cas_ok(ptr %p, i32 %c, i32 %n) {
; CHECK-LABEL: cas_ok:
; CHECK: lr.t.an
; CHECK: sc.t.ar
; CHECK: cmp.so {{rd[0-9]+}}, {{rd[0-9]+}}, rd{{[0-9]+}}
; CHECK: cs.z {rd{{[0-9]+}}}?, rd{{[0-9]+}}, rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: ret
  %r = cmpxchg ptr %p, i32 %c, i32 %n seq_cst seq_cst
  %s = extractvalue { i32, i1 } %r, 1
  ret i1 %s
}

; atomicrmw is expanded to a cmpxchg loop in IR (shouldExpandAtomicRMWInIR ->
; CmpXChg) and must therefore also contain lr/sc, never a `__atomic_*` call.
define i32 @rmw_add(ptr %p, i32 %v) {
; CHECK-LABEL: rmw_add:
; CHECK: lr.t.an
; CHECK: sc.t.ar
; CHECK-NOT: __atomic
  %r = atomicrmw add ptr %p, i32 %v seq_cst
  ret i32 %r
}

define i64 @rmw_xchg(ptr %p, i64 %v) {
; CHECK-LABEL: rmw_xchg:
; CHECK: lr.o.an
; CHECK: sc.o.ar
  %r = atomicrmw xchg ptr %p, i64 %v acq_rel
  ret i64 %r
}
