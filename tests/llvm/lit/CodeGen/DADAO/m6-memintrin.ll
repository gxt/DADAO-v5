;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-064t / M6 (INTEG-023k §A #3, no libc): the DADAO backend exposes the C
; mem* libcalls (DADAOSubtarget::initLibcallLoweringInfo).  A constant-size
; memcpy/memset whose octa-store count fits MaxStoresPerMem* = 16 is inlined;
; anything larger (and any variable size) lowers to a plain libcall that the
; freestanding runtime (tests/scripts/dadao_mem_runtime.ll) resolves.

@g = global [1024 x i8] zeroinitializer, align 8

declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1)
declare void @llvm.memset.p0.i64(ptr, i8, i64, i1)

; 128 bytes = 16 stores -> inlined (the MaxStoresPerMem* boundary).
define void @inline128(ptr align 8 %d) {
; CHECK-LABEL: inline128:
; CHECK-NOT:   call [rb0, memcpy]
; CHECK:       ret rd0, 0
entry:
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %d, ptr align 8 @g, i64 128, i1 false)
  ret void
}

; 136 bytes = 17 stores > 16 -> out-of-line libcall.
define void @libcall136(ptr align 8 %d) {
; CHECK-LABEL: libcall136:
; CHECK:       call [rb0, memcpy]
entry:
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %d, ptr align 8 @g, i64 136, i1 false)
  ret void
}

; A variable size always lowers to a libcall.
define void @libcall_memset(ptr %d, i64 %n) {
; CHECK-LABEL: libcall_memset:
; CHECK:       call [rb0, memset]
entry:
  call void @llvm.memset.p0.i64(ptr %d, i8 0, i64 %n, i1 false)
  ret void
}
