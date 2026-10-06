; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
; RUN: echo 'rd2rd {rd4:rd6}, {rd8:rd12}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
; RUN: echo 'rb2rb {rb1:rb2}, {rb3:rb5}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
; RUN: echo 'rd2rb {rb8:rb12}, {rd4:rd6}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
; RUN: echo 'rb2rd {rd8:rd12}, {rb4:rb6}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
; RUN: echo 'rd2ra {ra8:ra12}, {rd4:rd6}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
; RUN: echo 'ra2rd {rd4:rd6}, {ra8:ra12}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
; RUN: echo 'ldm.o {rd0:rd63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF
; RUN: echo 'stm.o {rd0:rd63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF
; RUN: echo 'ldm.o {rb0:rb63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF
; RUN: echo 'ldm.o {ra0:ra63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF
; RUN: echo 'ldm.ub {rd0:rd63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF
; RUN: echo 'rd2rd {rd0:rd63}, {rd8:rd12}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OVF

; Static legality rules for M1 multi-register groups (ISS-104 / ISS-106;
; contract-isa.md §3.1.2 §3.3.2 §3.3.3; contracts/legality_rules.yaml):
;
;   mreg_range_overflow  — a `{start:end}` group names a register count stored
;     in the 6-bit immu6 field (valid 1..63).  A count-64 group such as
;     `{rd0:rd63}` (or the RB/RA analogues) would silently truncate to 0, so the
;     assembler MUST hard-error (Error level, never a warning).  Covers the M1
;     ldm.*/stm.* loads/stores (RD/RB/RA destinations) and the orri block moves.
;
;   (shared count)       — rd2rd/rb2rb (same-bank) and rd2rb/rb2rd/rd2ra/ra2rd
;     (cross-bank) carry TWO `{start:end}` groups whose sizes are encoded by a
;     SINGLE immu6.  If the two written groups differ in size the instruction is
;     ill-formed and MUST hard-error instead of silently using one of the two
;     counts (previously the last group won).
;
; Negative cases (checked independently via the echo-piped RUN lines above):
;   count-differ: rd2rd {rd4:rd6}, {rd8:rd12}   -> 3 vs 5
;   count-differ: rb2rb {rb1:rb2}, {rb3:rb5}    -> 2 vs 3
;   count-differ: rd2rb {rb8:rb12}, {rd4:rd6}   -> 5 vs 3 (cross-bank)
;   count-differ: rb2rd {rd8:rd12}, {rb4:rb6}   -> 5 vs 3 (cross-bank)
;   count-differ: rd2ra {ra8:ra12}, {rd4:rd6}   -> 5 vs 3 (cross-bank)
;   count-differ: ra2rd {rd4:rd6}, {ra8:ra12}   -> 3 vs 5 (cross-bank)
;   overflow: ldm.o {rd0:rd63}, [rb1, rd0]  -> count 64 (RD)
;   overflow: stm.o {rd0:rd63}, [rb1, rd0]  -> count 64 (RD)
;   overflow: ldm.o {rb0:rb63}, [rb1, rd0]  -> count 64 (RB)
;   overflow: ldm.o {ra0:ra63}, [rb1, rd0]  -> count 64 (RA)
;   overflow: ldm.ub {rd0:rd63}, [rb1, rd0] -> count 64 (RD)
;   overflow: rd2rd {rd0:rd63}, {rd8:rd12}  -> count 64 (overflow checked first)
;
; Positive cases (assembled as a whole below): the file MUST assemble cleanly.
;   equal-size block groups and a count-63 (rd0:rd62) multi-register load are
;   legal.

; OK: encoding: [0x40,0xb0,0x42,0x02]
rd2rd {rd4:rd5}, {rd8:rd9}

; OK: encoding: [0x40,0xd0,0x10,0xc2]
rb2rb {rb1:rb2}, {rb3:rb4}

; OK: encoding: [0x40,0xd4,0x81,0x02]
rd2rb {rb8:rb9}, {rd4:rd5}

; OK: encoding: [0x40,0xd8,0x81,0x02]
rb2rd {rd8:rd9}, {rb4:rb5}

; OK: encoding: [0x40,0xb4,0x81,0x02]
rd2ra {ra8:ra9}, {rd4:rd5}

; OK: encoding: [0x40,0xb8,0x42,0x02]
ra2rd {rd4:rd5}, {ra8:ra9}

; OK: encoding: [0x38,0x00,0x10,0x3f]
ldm.o {rd0:rd62}, [rb1, rd0]

; OK: encoding: [0x28,0x20,0x10,0x37]
ldm.ub {rd8:rd62}, [rb1, rd0]

; OK: encoding: [0x3d,0x00,0x10,0x3f]
stm.o {ra0:ra62}, [rb1, rd0]

; OK-NOT: error

; ERR-CNT: error: invalid '{{[a-z0-9.]+}}': source and destination register group counts differ (they share a single immu6 element count)
; ERR-OVF: error: invalid '{{[a-z0-9.]+}}': register range too long (mreg_range_overflow); element count must be 1..63
