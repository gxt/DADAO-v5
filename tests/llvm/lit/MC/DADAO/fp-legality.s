; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
; RUN: echo 'ftadd rf0, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-DST
; RUN: echo 'it2ft {rf0}, {rd2}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-DST
; RUN: echo 'cs.n {rd1}?, rf0, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-DST
; RUN: echo 'cs.eq {rd1, rd2}?, rf0, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-DST
; RUN: echo 'ft2fo {rf3:rf4}, {rf2:rf3}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVL
; RUN: echo 'ft2ft {rf3:rf3}, {rf3:rf3}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVL
; RUN: echo 'fo2fo {rf2:rf3}, {rf3:rf4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVL
; RUN: echo 'ftroot rf1, rf2, 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-ROOT
; RUN: echo 'foroot rf1, rf2, 0' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-ROOT
; RUN: echo 'ft2fo {rf0:rf63}, {rf1:rf62}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF
; RUN: echo 'ldm.t {rf0:rf63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF

; FP assemble-time static legality checks (SPEC-088t; contracts/legality_rules.yaml):
;   dst_rf0              -- rf0 is the FCSR and cannot be an FP destination
;                           (rf0 as a *source* is legal).  35 instructions
;                           (16 scalar orrr + 14 orri convert/root + 5 cs_rf).
;   mreg_range_overlap   -- the two same-bank RF `{start:end}` groups of a
;                           convert_ff instruction must be disjoint (any
;                           intersection, including complete coincidence, is
;                           illegal).
;   mreg_range_overflow  -- the shared immu6 element count is 6 bits (0..63);
;                           `{rf0:rf63}` (count 64) would silently truncate to 0,
;                           so any FP group with count > 63 is rejected.
;   encode_fp_root_n     -- ftroot/foroot only support the constant n == 2.
; All are hard errors (Error level, never a warning): `llvm-mc` exits non-zero.

; Positive cases (assembled as a whole below): the file MUST assemble cleanly.
;   rf0 as a source is always legal; rf0 as a destination is legal for rd2rf,
;   the RF loads (ld.t/ldm.t) and set.w (FCSR write-mask exceptions).
;   Non-overlapping convert_ff groups and `{rf0:rf62}` (count 63) are legal.
;
; OK: encoding: [0x44,0x40,0x10,0x83]
; OK: encoding: [0x44,0x40,0x10,0x03]
; OK: encoding: [0x44,0x5c,0x10,0x03]
; OK: encoding: [0x40,0xf8,0x31,0x01]
; OK: encoding: [0x40,0xf8,0x30,0x01]
; OK: encoding: [0x40,0xf4,0x01,0x41]
; OK: encoding: [0x40,0xf4,0x01,0x03]
; OK: encoding: [0x16,0x00,0x10,0x00]
; OK: encoding: [0x2e,0x00,0x10,0x04]
; OK: encoding: [0x2e,0x00,0x10,0x3f]
; OK: encoding: [0x2f,0x10,0x10,0x03]
; OK: encoding: [0x4f,0x00,0x00,0x01]
; OK: encoding: [0x44,0x18,0x10,0x82]
; OK: encoding: [0x44,0x38,0x10,0x82]
; OK: encoding: [0x44,0x04,0x42,0x03]
; OK: encoding: [0x44,0x04,0x10,0x01]
; OK: encoding: [0x44,0xd0,0x42,0x03]
; OK: encoding: [0x44,0xc0,0x42,0x03]
; OK: encoding: [0x44,0x00,0x42,0x03]
; OK: encoding: [0x44,0x80,0x40,0x83]
; OK: encoding: [0x61,0x04,0x40,0x08]
; OK: encoding: [0x5e,0x04,0x21,0x03]
; OK-NOT: error
ftadd rf1, rf2, rf3
ftadd rf1, rf0, rf3
ftsgnj rf1, rf0, rf3
rf2rd {rd3}, {rf4}
rf2rd {rd3}, {rf0}
rd2rf {rf0}, {rd5}
rd2rf {rf0:rf2}, {rd4:rd6}
ld.t rf0, [rb1, 0]
ldm.t {rf0:rf3}, [rb1, rd0]
ldm.t {rf0:rf62}, [rb1, rd0]
stm.t {rf4:rf6}, [rb1, rd0]
set.w rf0, wp0, 1
ftroot rf1, rf2, 2
foroot rf1, rf2, 2
ft2fo {rf4:rf6}, {rf8:rf10}
ft2fo {rf1}, {rf0}
it2ft {rf4:rf6}, {rd8:rd10}
ft2it {rd4:rd6}, {rf8:rf10}
ftcls {rd4:rd6}, {rf8:rf10}
ftqcmp rd4, rf2, rf3
cs.n {rd1}?, rf4, rf0, rf8
cs.eq {rd1, rd2}?, rf4, rf3

; Negative cases (checked independently via the echo-piped RUN lines above).
; dst_rf0: FT op / convert_i2f / cs.n / cs.eq with rf0 as the destination.
; ERR-DST: error: invalid '{{[a-z0-9.]+}}': rf0 is the FCSR and cannot be a floating-point destination (dst_rf0)
;
; mreg_range_overlap: partial, complete-coincidence and destination-first overlap.
; ERR-OVL: error: invalid '{{[a-z0-9.]+}}': source and destination register ranges overlap (mreg_range_overlap)
;
; encode_fp_root_n: n != 2 (both ftroot and foroot).
; ERR-ROOT: error: invalid '{{[a-z0-9.]+}}': root order n must be the constant 2 (encode_fp_root_n)
;
; mreg_range_overflow: `{rf0:rf63}` (count 64) in a convert_ff and an RF ldm.
; ERR-OVF: error: invalid '{{[a-z0-9.]+}}': register range too long (mreg_range_overflow)
