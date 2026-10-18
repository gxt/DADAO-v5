;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-105t (ISS-267 ①): a vector load whose type must be widened.
;
; clang's SROA rewrites a 24-byte aggregate copy (`struct S { int a..f; }`) into
; `load <6 x i32>` / `store <6 x i32>` even for a scalar-only target.  DADAO
; has no vector register class, so the type legalizer widens/splits the vector
; and asks the target for the SETCC result type of the widened type
; (DAGTypeLegalizer::WidenVecRes_LOAD -> TargetLowering::getSetCCResultType).
; The generic implementation asserts "No default SetCC type for vectors!";
; DADAOTargetLowering::getSetCCResultType now answers with the lane integer
; type (0/-1 per lane), so the vector is split into six scalar i32 accesses.
;
; This is the minimal IR form of the crashers (lencod explicit_gop.c: v6i32,
; obsequi negamax.c: v3i32); the expected instructions follow the ISA
; (`ld.ut` = unsigned tetra load, `st.t` = tetra store; contract-isa.md §3.1.1).

; CHECK-LABEL: copy6:
; CHECK-COUNT-6: ld.ut rd
; CHECK-COUNT-6: st.t rd
define void @copy6(ptr %dst, ptr %src) {
  %v = load <6 x i32>, ptr %src, align 4
  store <6 x i32> %v, ptr %dst, align 4
  ret void
}

; Same shape for a 12-byte aggregate (obsequi's `v3i32`).
; CHECK-LABEL: copy3:
; CHECK-COUNT-3: ld.ut rd
; CHECK-COUNT-3: st.t rd
define void @copy3(ptr %dst, ptr %src) {
  %v = load <3 x i32>, ptr %src, align 4
  store <3 x i32> %v, ptr %dst, align 4
  ret void
}
