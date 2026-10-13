; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
; RUN: echo 'add.si rd8, 131072'            | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RANGE
; RUN: echo 'cmp.ui rd8, rd9, 4096'         | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-UI
; RUN: echo 'shl.uo rd8, rd0, 64'           | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-U6
; RUN: echo 'set.zw rd8, wp0, 65536'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-U16
; RUN: echo 'swym 262144'                   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-U18
; RUN: echo 'add.si rd8, -131073'           | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'cmp.si rd8, rd9, 2048'         | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'cmp.si rd8, rd9, -2049'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'cmp.ui rd8, rd9, -1'           | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'ld.ub rd8, [rb2, 2048]'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'ld.ub rd8, [rb2, -2049]'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'ret rd8, 131072'               | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'shl.uo rd8, rd0, -1'           | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'set.zw rd8, wp0, -1'           | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'fence 262144'                  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'swym -1'                       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'jump [rb0, 6]'                 | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ALIGN
; RUN: echo 'br.eq {rd8, rd0}?, [rb0, 6]'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ALIGN

; Assembly immediate field range validation (LLVM-054t;
; contract-asm.md §2.4/§9/§11, ADR-0013 D3/D10, contract-asm-list.md
; 「立即数范围速查」).
;
; Every immediate maps to a fixed-width encoding field; the code emitter masks
; by width, so an out-of-range value would silently wrap (contract-asm §11:
; `add.si rd8, 131072` -> -131072; `cmp.ui …, 4096` -> 0).  The assembler MUST
; hard-error instead (Error level, non-zero exit), and the diagnostic MUST
; name the operand position and the expected range.
;
; Boundary values below MUST be accepted and encoded exactly (no false
; rejection); the OK directives are the independent-oracle encodings.

; --- min/max legal boundaries for every immediate field ---
; OK: encoding: [0x59,0x21,0xff,0xff]
add.si rd8, 131071
; OK: encoding: [0x59,0x22,0x00,0x00]
add.si rd8, -131072
; OK: encoding: [0x5c,0x20,0x9f,0xff]
cmp.ui rd8, rd9, 4095
; OK: encoding: [0x5c,0x20,0x90,0x00]
cmp.ui rd8, rd9, 0
; OK: encoding: [0x5d,0x20,0x98,0x00]
cmp.si rd8, rd9, -2048
; OK: encoding: [0x5d,0x20,0x97,0xff]
cmp.si rd8, rd9, 2047
; OK: encoding: [0x10,0x20,0x28,0x00]
ld.ub rd8, [rb2, -2048]
; OK: encoding: [0x10,0x20,0x27,0xff]
ld.ub rd8, [rb2, 2047]
; OK: encoding: [0x76,0x22,0x00,0x00]
ret rd8, -131072
; OK: encoding: [0x76,0x21,0xff,0xff]
ret rd8, 131071
; OK: encoding: [0x40,0x70,0x80,0x3f]
shl.uo rd8, rd0, 63
; OK: encoding: [0x40,0x60,0x80,0x00]
ext.uo rd8, rd0, 0
; OK: encoding: [0x4c,0x20,0xff,0xff]
set.zw rd8, wp0, 0xffff
; OK: encoding: [0x77,0x88,0x00,0x00]
swym 0
; OK: encoding: [0x77,0x8b,0xff,0xff]
swym 262143

; Address-class boundaries (%4==0 + byte range); `ret` is NOT an address and
; is not subject to the %4 constraint.
; OK: encoding: [0x68,0x21,0xff,0xff]
br.n {rd8}?, [rb0, 524284]
; OK: encoding: [0x68,0x22,0x00,0x00]
br.n {rd8}?, [rb0, -524288]
; OK: encoding: [0x6e,0x20,0x07,0xff]
br.eq {rd8, rd0}?, [rb0, 8188]
; OK: encoding: [0x6e,0x20,0x08,0x00]
br.eq {rd8, rd0}?, [rb0, -8192]
; OK: encoding: [0x70,0x7f,0xff,0xff]
jump [rb0, 33554428]
; OK: encoding: [0x70,0x80,0x00,0x00]
jump [rb0, -33554432]
; OK: encoding: [0x71,0x0c,0x07,0xff]
jump [rb3, rd0, 8188]
; OK: encoding: [0x76,0x20,0x00,0x06]
ret rd8, 6

; --- rejection diagnostics (position + expected range) ---
; ERR-RANGE: error: immediate out of range for 'add.si': 131072 is outside the imms18 (signed 18-bit) range [-131072, 131071]
; ERR-UI: error: immediate out of range for 'cmp.ui': 4096 is outside the immu12 (unsigned 12-bit) range [0, 4095]
; ERR-U6: error: immediate out of range for 'shl.uo': 64 is outside the immu6 (unsigned 6-bit) range [0, 63]
; ERR-U16: error: immediate out of range for 'set.zw': 65536 is outside the immu16 (unsigned 16-bit) range [0, 65535]
; ERR-U18: error: immediate out of range for 'swym': 262144 is outside the immu18 (unsigned 18-bit) range [0, 262143]
; ERR: error: immediate out of range
; ALIGN: must be a multiple of 4 bytes
