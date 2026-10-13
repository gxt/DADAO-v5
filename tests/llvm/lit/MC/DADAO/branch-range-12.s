; RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

; LLVM-062t / ISS-043: an out-of-range PC-relative branch target must be
; rejected with a diagnostic, not silently truncated to the immediate field.
; The rrii branch (br.eq) has a 12-bit signed word displacement (+/-2047 words
; = +/-8188 bytes); a target 12000 bytes away does not fit.
	.text
	br.eq {rd8, rd9}?, [rb0, L]
	.space 12000
	.globl L
L:

; CHECK: error: branch/jump target out of range for a 12-bit PC-relative immediate
