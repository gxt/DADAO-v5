; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
; RUN: echo 'rd2rd {rd3:rd4}, {rd2:rd3}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'rd2rd {rd2:rd3}, {rd3:rd4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'rd2rd {rd3:rd3}, {rd3:rd3}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'rb2rb {rb3:rb4}, {rb2:rb3}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RB
; RUN: echo 'rb2rb {rb2:rb3}, {rb3:rb4}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RB
; RUN: echo 'rb2rb {rb3:rb3}, {rb3:rb3}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RB

; Static legality rule `mreg_range_overlap` (SPEC-088t;
; SimRISC-02 §寄存器组之间块赋值):
;   Within-bank block assignments `rd2rd {rdha:rdha+immu6-1},
;   {rdhc:rdhc+immu6-1}` and `rb2rb {rbhb:...}, {rbhc:...}` are illegal
;   whenever the source range and the destination range intersect at all,
;   including complete coincidence.  The assembler MUST hard-error (Error
;   level, never a warning); cross-bank moves (ra2rd/rd2ra/rd2rb/rb2rd) are
;   structurally disjoint and not affected.
;
; Positive cases (below, assembled as a whole): the file MUST assemble cleanly.
;   rd2rd {rd4:rd5}, {rd2:rd3}   -> disjoint
;   rd2rd {rd8}, {rd1}           -> single-register groups, disjoint
;   rb2rb {rb4:rb5}, {rb2:rb3}   -> disjoint
;   rb2rb {rb8}, {rb1}           -> single-register groups, disjoint
;   rd2rd {rd2:rd3}, {rd4:rd5}   -> destination before source, disjoint
;
; OK: encoding: [0x40,0xb0,0x40,0x82]
; OK: encoding: [0x40,0xb0,0x80,0x41]
; OK: encoding: [0x40,0xd0,0x40,0x82]
; OK: encoding: [0x40,0xd0,0x80,0x41]
; OK: encoding: [0x40,0xb0,0x21,0x02]
; OK-NOT: error
rd2rd {rd4:rd5}, {rd2:rd3}
rd2rd {rd8}, {rd1}
rb2rb {rb4:rb5}, {rb2:rb3}
rb2rb {rb8}, {rb1}
rd2rd {rd2:rd3}, {rd4:rd5}

; Negative cases (checked independently via echo-piped RUN lines above):
;   rd2rd {rd3:rd4}, {rd2:rd3}   -> partial overlap (rd3)
;   rd2rd {rd2:rd3}, {rd3:rd4}   -> partial overlap (rd3), destination first
;   rd2rd {rd3:rd3}, {rd3:rd3}   -> complete coincidence
;   rb2rb {rb3:rb4}, {rb2:rb3}   -> partial overlap (rb3)
;   rb2rb {rb2:rb3}, {rb3:rb4}   -> partial overlap (rb3), destination first
;   rb2rb {rb3:rb3}, {rb3:rb3}   -> complete coincidence
;
; ERR: error: invalid 'rd2rd': source and destination register ranges overlap
; ERR-RB: error: invalid 'rb2rb': source and destination register ranges overlap
