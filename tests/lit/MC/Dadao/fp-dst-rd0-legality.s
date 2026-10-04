; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
; RUN: echo 'ft2it {rd0}, {rf4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'fo2uo {rd0}, {rf4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'ftcls {rd0}, {rf4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'focls {rd0}, {rf4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'ftqcmp rd0, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'ftscmp rd0, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'foqcmp rd0, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'foscmp rd0, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'rf2rd {rd0}, {rf4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'ft2it {rd0:rd2}, {rf4:rf6}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0
; RUN: echo 'rf2rd {rd0:rd2}, {rf4:rf6}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RD0

; FP assemble-time static legality check for `dst_rd0` (SPEC-089t;
; contracts/legality_rules.yaml, contracts/fp_semantics.yaml):
;   dst_rd0 -- the FP instructions whose destination is an RD register must not
;             write rd0 (the hard-wired zero register).  The 15 forms are:
;             convert_f2i 8 (ft2it/ft2io/ft2ut/ft2uo/fo2it/fo2io/fo2ut/fo2uo),
;             classify 2 (ftcls/focls), compare 4 (ftqcmp/ftscmp/foqcmp/foscmp)
;             and rf_move 1 (rf2rd).  rf0 as a *source* is always legal; the
;             rf-destination FP forms (rd2rf, ...) are unaffected.
; This is a hard error (Error level, never a warning): `llvm-mc` exits non-zero.

; Positive cases (assembled as a whole below): the file MUST assemble cleanly.
;   Non-rd0 destinations for all four families, multi-register groups whose
;   first register is non-zero, and rf0 used as a source.
;
; OK: encoding: [0x44,0xc0,0x11,0x01]
; OK: encoding: [0x44,0xc4,0x51,0x01]
; OK: encoding: [0x44,0xc8,0x21,0x01]
; OK: encoding: [0x44,0xcc,0x31,0x01]
; OK: encoding: [0x44,0xe0,0x61,0x01]
; OK: encoding: [0x44,0xe4,0x71,0x01]
; OK: encoding: [0x44,0xe8,0x81,0x01]
; OK: encoding: [0x44,0xec,0x91,0x01]
; OK: encoding: [0x44,0x00,0x11,0x01]
; OK: encoding: [0x44,0x20,0x21,0x01]
; OK: encoding: [0x44,0x80,0x10,0x83]
; OK: encoding: [0x44,0x84,0x40,0x83]
; OK: encoding: [0x44,0xa0,0x50,0x83]
; OK: encoding: [0x44,0xa4,0x60,0x83]
; OK: encoding: [0x40,0xf8,0x11,0x01]
; OK: encoding: [0x44,0xc0,0x42,0x03]
; OK: encoding: [0x40,0xf8,0x22,0x03]
; OK: encoding: [0x44,0xc0,0x10,0x01]
; OK-NOT: error
ft2it {rd1}, {rf4}
ft2io {rd5}, {rf4}
ft2ut {rd2}, {rf4}
ft2uo {rd3}, {rf4}
fo2it {rd6}, {rf4}
fo2io {rd7}, {rf4}
fo2ut {rd8}, {rf4}
fo2uo {rd9}, {rf4}
ftcls {rd1}, {rf4}
focls {rd2}, {rf4}
ftqcmp rd1, rf2, rf3
ftscmp rd4, rf2, rf3
foqcmp rd5, rf2, rf3
foscmp rd6, rf2, rf3
rf2rd {rd1}, {rf4}
ft2it {rd4:rd6}, {rf8:rf10}
rf2rd {rd2:rd4}, {rf8:rf10}
ft2it {rd1}, {rf0}

; Negative cases (checked independently via the echo-piped RUN lines above).
; dst_rd0: rd0 as the destination of any of the 15 FP rd-destination forms,
; including a multi-register group whose first register is rd0 (`{rd0:rd2}`).
; ERR-RD0: error: invalid '{{[a-z0-9.]+}}': rd0 is the hard-wired zero register and cannot be a destination (dst_rd0)
