; LLVM-137t / CodeGen runtime vector: i64 constant shifts use immu6 forms.
;
; IR semantics (independent host-side oracle: Python u64 truncation for shl /
; lshr and a signed 64-bit arithmetic shift for ashr):
;   a = 0x0123456789ABCDEF, b = 0xFEDCBA9876543210 (negative), n = 37
;   shl  a, k  for k in 0, 1, 31, 32, 63
;   lshr b, k  for k in 0, 1, 31, 32, 63
;   ashr b, k  for k in 0, 1, 31, 32, 63
;   shl a, n ; lshr b, n ; ashr b, n
; Every result is compared against the oracle constant; @main returns the count
; of mismatches (0 iff all 18 results match).  The volatile loads keep the
; shifts from being folded before instruction selection.
;
; Expected guest exit code: 0  (in 0x00..0x7F)
define i64 @main() {
entry:
  %a_s = alloca i64, align 8
  %b_s = alloca i64, align 8
  %n_s = alloca i64, align 8
  store volatile i64 u0x0123456789ABCDEF, i64* %a_s, align 8
  store volatile i64 u0xFEDCBA9876543210, i64* %b_s, align 8
  store volatile i64 37, i64* %n_s, align 8
  %a = load volatile i64, i64* %a_s, align 8
  %b = load volatile i64, i64* %b_s, align 8
  %n = load volatile i64, i64* %n_s, align 8

  ; --- shl a, {0,1,31,32,63} -------------------------------------------------
  %shl0 = shl i64 %a, 0
  %shl1 = shl i64 %a, 1
  %shl31 = shl i64 %a, 31
  %shl32 = shl i64 %a, 32
  %shl63 = shl i64 %a, 63
  %c_shl0 = icmp eq i64 %shl0, u0x0123456789ABCDEF
  %c_shl1 = icmp eq i64 %shl1, u0x02468ACF13579BDE
  %c_shl31 = icmp eq i64 %shl31, u0xC4D5E6F780000000
  %c_shl32 = icmp eq i64 %shl32, u0x89ABCDEF00000000
  %c_shl63 = icmp eq i64 %shl63, u0x8000000000000000
  %e_shl0 = zext i1 %c_shl0 to i64
  %e_shl1 = zext i1 %c_shl1 to i64
  %e_shl31 = zext i1 %c_shl31 to i64
  %e_shl32 = zext i1 %c_shl32 to i64
  %e_shl63 = zext i1 %c_shl63 to i64
  %ok_shl01 = add i64 %e_shl0, %e_shl1
  %ok_shl31 = add i64 %ok_shl01, %e_shl31
  %ok_shl32 = add i64 %ok_shl31, %e_shl32
  %ok_shl = add i64 %ok_shl32, %e_shl63

  ; --- lshr b, {0,1,31,32,63} ------------------------------------------------
  %lshr0 = lshr i64 %b, 0
  %lshr1 = lshr i64 %b, 1
  %lshr31 = lshr i64 %b, 31
  %lshr32 = lshr i64 %b, 32
  %lshr63 = lshr i64 %b, 63
  %c_lshr0 = icmp eq i64 %lshr0, u0xFEDCBA9876543210
  %c_lshr1 = icmp eq i64 %lshr1, u0x7F6E5D4C3B2A1908
  %c_lshr31 = icmp eq i64 %lshr31, u0x00000001FDB97530
  %c_lshr32 = icmp eq i64 %lshr32, u0x00000000FEDCBA98
  %c_lshr63 = icmp eq i64 %lshr63, u0x0000000000000001
  %e_lshr0 = zext i1 %c_lshr0 to i64
  %e_lshr1 = zext i1 %c_lshr1 to i64
  %e_lshr31 = zext i1 %c_lshr31 to i64
  %e_lshr32 = zext i1 %c_lshr32 to i64
  %e_lshr63 = zext i1 %c_lshr63 to i64
  %ok_lshr01 = add i64 %e_lshr0, %e_lshr1
  %ok_lshr31 = add i64 %ok_lshr01, %e_lshr31
  %ok_lshr32 = add i64 %ok_lshr31, %e_lshr32
  %ok_lshr = add i64 %ok_lshr32, %e_lshr63

  ; --- ashr b, {0,1,31,32,63} (signed oracle) --------------------------------
  %ashr0 = ashr i64 %b, 0
  %ashr1 = ashr i64 %b, 1
  %ashr31 = ashr i64 %b, 31
  %ashr32 = ashr i64 %b, 32
  %ashr63 = ashr i64 %b, 63
  %c_ashr0 = icmp eq i64 %ashr0, u0xFEDCBA9876543210
  %c_ashr1 = icmp eq i64 %ashr1, u0xFF6E5D4C3B2A1908
  %c_ashr31 = icmp eq i64 %ashr31, u0xFFFFFFFFFDB97530
  %c_ashr32 = icmp eq i64 %ashr32, u0xFFFFFFFFFEDCBA98
  %c_ashr63 = icmp eq i64 %ashr63, u0xFFFFFFFFFFFFFFFF
  %e_ashr0 = zext i1 %c_ashr0 to i64
  %e_ashr1 = zext i1 %c_ashr1 to i64
  %e_ashr31 = zext i1 %c_ashr31 to i64
  %e_ashr32 = zext i1 %c_ashr32 to i64
  %e_ashr63 = zext i1 %c_ashr63 to i64
  %ok_ashr01 = add i64 %e_ashr0, %e_ashr1
  %ok_ashr31 = add i64 %ok_ashr01, %e_ashr31
  %ok_ashr32 = add i64 %ok_ashr31, %e_ashr32
  %ok_ashr = add i64 %ok_ashr32, %e_ashr63

  ; --- variable amount (n = 37): the register form must compute identically ---
  %vshl = shl i64 %a, %n
  %vlshr = lshr i64 %b, %n
  %vashr = ashr i64 %b, %n
  %c_vshl = icmp eq i64 %vshl, u0x3579BDE000000000
  %c_vlshr = icmp eq i64 %vlshr, u0x000000007F6E5D4
  %c_vashr = icmp eq i64 %vashr, u0xFFFFFFFFFFF6E5D4
  %e_vshl = zext i1 %c_vshl to i64
  %e_vlshr = zext i1 %c_vlshr to i64
  %e_vashr = zext i1 %c_vashr to i64
  %ok_var0 = add i64 %e_vshl, %e_vlshr
  %ok_var = add i64 %ok_var0, %e_vashr

  ; --- count mismatches (0 iff every comparison matched) ---------------------
  %ok0 = add i64 %ok_shl, %ok_lshr
  %ok1 = add i64 %ok0, %ok_ashr
  %ok = add i64 %ok1, %ok_var
  %bad = sub i64 18, %ok
  ret i64 %bad
}
