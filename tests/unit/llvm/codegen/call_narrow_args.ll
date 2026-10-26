; TESTCASES-026t / CodeGen vector: call (C4 narrow argument promotion by caller)
; Sub-8-byte scalar parameters (i8/i16/i32) are canonically extended to 8 bytes by
; the caller before being placed in rd16.. (C4).  The callee re-extends per its IR
; type (zero-extension for unsigned; the signed `sext` form lowers to
; `sign_extend_inreg`, which the M3 backend does not select yet -- see the task's
; "新发现/坑").  Operands come from volatile loads so the call is not folded.
;
; IR semantics:
;   narrow(x, y, z, w) = zext(x) + zext(y) + zext(z) + w
;   main: x=200, y=300, z=400, w=5  ->  905
;   r = 905 & 127 = 9
; The mask is 127 (not 255) so the guest exit code stays in 0x00..0x7F (ISS-147).
; Expected guest exit code: 9
define i64 @narrow(i8 %x, i16 %y, i32 %z, i64 %w) noinline {
entry:
  %xz = zext i8 %x to i64
  %yz = zext i16 %y to i64
  %zz = zext i32 %z to i64
  %t = add i64 %xz, %yz
  %t2 = add i64 %t, %zz
  %r = add i64 %t2, %w
  ret i64 %r
}

define i64 @main() {
entry:
  %sx = alloca i8, align 1
  %sy = alloca i16, align 2
  %sz = alloca i32, align 4
  %sw = alloca i64, align 8
  store volatile i8 -56, i8* %sx, align 1   ; -56 = 0xC8 = 200 (i8)
  store volatile i16 300, i16* %sy, align 2
  store volatile i32 400, i32* %sz, align 4
  store volatile i64 5, i64* %sw, align 8
  %x = load volatile i8, i8* %sx, align 1
  %y = load volatile i16, i16* %sy, align 2
  %z = load volatile i32, i32* %sz, align 4
  %w = load volatile i64, i64* %sw, align 8
  %s = call i64 @narrow(i8 %x, i16 %y, i32 %z, i64 %w)
  %r = and i64 %s, 127
  ret i64 %r
}
