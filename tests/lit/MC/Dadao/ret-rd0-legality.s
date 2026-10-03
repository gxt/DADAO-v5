; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
; RUN: echo 'ret rd0, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'ret rd0, -1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: echo 'ret rd0, foo' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR

; Static legality rule `dst_rd0_nonzero` (SPEC-083t; SimRISC-06 §函数返回):
;   `ret rdHA, imms18` with rdHA == rd0 requires imms18 == 0; otherwise the
;   instruction is illegal and the assembler must hard-error (Error level,
;   never a warning).  Applies to `ret` only.
;
; Positive cases (below, assembled as a whole): the file must assemble cleanly.
;   ret rd0, 0   -> allowed (rd0 with imms18 == 0)
;   ret rd1, 0   -> allowed (rdHA != rd0, no constraint)
;   ret rd1, 42  -> allowed (rdHA != rd0, no constraint)
;
; OK: encoding: [0x76,0x00,0x00,0x00]
; OK: encoding: [0x76,0x04,0x00,0x00]
; OK: encoding: [0x76,0x04,0x00,0x2a]
; OK-NOT: error
ret rd0, 0
ret rd1, 0
ret rd1, 42

; Negative cases (checked independently via echo-piped RUN lines above):
;   ret rd0, 1    -> illegal: rdHA == rd0 and imms18 != 0
;   ret rd0, -1   -> illegal: rdHA == rd0 and imms18 != 0
;   ret rd0, foo  -> illegal: non-constant imms18 cannot be proven to be 0
;
; ERR: error: invalid 'ret': rdHA is rd0, so imms18 must be
