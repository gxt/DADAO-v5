; LLVM-062t / M6 runtime vector: indirect call through a function pointer.
;
; Unlike the raw-binary M3 vectors (tests/llvm/codegen/*.ll, run by
; tools/integ/run_codegen_e2e.py), this program is compiled and *linked with
; ld.lld* before running on QEMU.  Taking the address of a function needs the
; absolute 48-bit address of a text symbol, which is an R_DADAO_ABS48
; relocation (absolute; never resolved in place) and therefore only resolvable
; by the linker -- the flat-binary flow has no link step.  The ELF flow is the
; M4 mechanism (tools/integ/run_elf_e2e.py); LLVM-062t's evidence script drives
; it directly for this one program (its expected exit code is the low byte of
; @main's return value, 42).
;
; IR semantics (host independent oracle):
;   add3(x, y, z) = x + y + z
;   fp = &add3 (volatile load); main: fp(10, 20, 12) = 42 -> &127 = 42
; Expected guest exit code: 42

define i64 @add3(i64 %x, i64 %y, i64 %z) noinline {
entry:
  %t = add i64 %x, %y
  %r = add i64 %t, %z
  ret i64 %r
}

define i64 @main() {
entry:
  %fp = alloca ptr, align 8
  store volatile ptr @add3, ptr %fp, align 8
  %f = load volatile ptr, ptr %fp, align 8
  %v = call i64 %f(i64 10, i64 20, i64 12)
  %m = and i64 %v, 127
  ret i64 %m
}
