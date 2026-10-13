; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: echo 'ldm.o {rd8:rd10}, [rb0, rd1]' | %not %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RB0
; RUN: echo 'ldm.o {rd8:rd10}, [rb2, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RD0
; RUN: echo 'ldm.o {rd8:rd10}, [rb2, rd9]' | %not %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=INRANGE
; RUN: echo 'ldm.o {rb8:rb10}, [rb9, rd1]' | %not %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=BASEINRANGE

; `-multiple-to-single` cannot safely expand three kinds of ldm.*/stm.*:
;   * rb0 base (PC-relative; the expansion changes the instruction address),
;   * rd0 as the offset register (add.si cannot change rd0),
;   * an offset register inside the accessed register range,
;   * an ldm.* base inside the written destination range (the group is written
;     element by element, so the base would be overwritten).
; All are valid without the option (the RUN above assembles %s), and must be
; rejected with a hard error when it is enabled.
;
; RB0: '-multiple-to-single' cannot expand 'ldm.o': base register rb0
; RD0: '-multiple-to-single' cannot expand 'ldm.o': the offset register rd0 cannot be advanced
; INRANGE: '-multiple-to-single' cannot expand 'ldm.o': the offset register is inside the accessed register range
; BASEINRANGE: '-multiple-to-single' cannot expand 'ldm.o': the base register is inside the written destination register range

	.text
	ldm.o {rd8:rd10}, [rb0, rd1]
	ldm.o {rd8:rd10}, [rb2, rd0]
	ldm.o {rd8:rd10}, [rb2, rd9]
	ldm.o {rb8:rb10}, [rb9, rd1]
