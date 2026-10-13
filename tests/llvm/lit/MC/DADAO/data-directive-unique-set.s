; RUN: echo '.dd.b08 1'            | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.w16 1'            | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.t32 1'            | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.o64 1'            | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.b08 1, 2, 0xff'   | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.w16 1+2, 0x1234'  | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.t32 (1<<24)|7'    | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.o64 ext'          | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null

; Data-directive unique set (spec/Toolchain-01 §7.1; ISS-189).
;
; §7.1 fixes the ONLY data directives of the DADAO assembly language to the
; Knuth/MMIX data-length names `.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`;
; "GAS 数据指示符一律禁用 … 亦 MUST NOT 被受理".  The set of *rejected* names
; below is NOT hand-picked: it is every directive that LLVM's generic MC parser
; dispatches to a fixed-width data emitter (AsmParser.cpp:
; parseDirectiveValue / parseDirectiveOctaValue / parseDirectiveRealValue /
; parseDirectiveLEB128 / parseDirectiveDCB / parseDirectiveRealDCB) minus the
; four `.dd.*` names; the reproducible derivation script is kept with the task
; evidence (`.work/evidence/<task>/derive_directive_sets.sh`).
;
; The generic directive table is matched case-insensitively
; (`DirectiveKindMap.find(IDVal.lower())`), so the rejection lower-cases too:
; `.BYTE` / `.QUAD` / `.Octa` are NOT DADAO spellings (directives are
; case-sensitive, §2.1) and MUST be rejected as well.
;
; 1-byte family
; RUN: echo '.byte 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.byte
; RUN: echo '.dc.b 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc.b
; RUN: echo '.dcb.b 2, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dcb.b
; 2-byte family
; RUN: echo '.short 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.short
; RUN: echo '.value 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.value
; RUN: echo '.2byte 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.2byte
; RUN: echo '.dc 1'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc
; RUN: echo '.dc.w 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc.w
; RUN: echo '.dcb 2, 1'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dcb
; RUN: echo '.dcb.w 2, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dcb.w
; 4-byte family
; RUN: echo '.long 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.long
; RUN: echo '.int 1'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.int
; RUN: echo '.4byte 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.4byte
; RUN: echo '.dc.l 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc.l
; RUN: echo '.dcb.l 2, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dcb.l
; 8-byte family
; RUN: echo '.quad 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.quad
; RUN: echo '.8byte 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.8byte
; RUN: echo '.dcb.d 2, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dcb.d
; RUN: echo '.dc.a 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc.a
; floating-point / LEB128 family (no `.dd.*` equivalent: the DADAO directives
; take integer expressions)
; RUN: echo '.single 1'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.single
; RUN: echo '.float 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.float
; RUN: echo '.dc.s 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc.s
; RUN: echo '.dcb.s 2, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dcb.s
; RUN: echo '.double 1'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.double
; RUN: echo '.dc.d 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.dc.d
; RUN: echo '.sleb128 1'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.sleb128
; RUN: echo '.uleb128 1'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.uleb128
; GAS `.octa` is a 16-byte octa while the DADAO octa is 8 bytes -> its semantics
; MUST NOT be used (§7.1); it has its own diagnostic pointing at `.dd.o64`.
; RUN: echo '.octa 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OCTA -DNAME=.octa
; §7.1 also names `.word`; LLVM has no such built-in directive, so it is an
; unknown directive (rc != 0), which is the same rejection outcome.
; RUN: echo '.word 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=WORD
; `.dc.x` / `.dcb.x` are rejected by the generic parser itself (unchanged).
; RUN: echo '.dc.x 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NOTSUP -DNAME=.dc.x
; RUN: echo '.dcb.x 2, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NOTSUP -DNAME=.dcb.x
; Case: the four accepted `.dd.*` spellings are lower-case only (§2.1), and the
; generic table is matched case-insensitively -> upper/mixed case MUST NOT be
; accepted by either path.
; RUN: echo '.BYTE 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.BYTE
; RUN: echo '.QUAD 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.QUAD
; RUN: echo '.Octa 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OCTA -DNAME=.Octa
; RUN: echo '.VALUE 1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.VALUE
; RUN: echo '.DC.B 1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJ -DNAME=.DC.B
; RUN: echo '.DD.B08 1'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNKNOWN
; RUN: echo '.Dd.o64 1'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNKNOWN
;
; Boundary of the closure: directives that only RESERVE space or emit a STRING
; are not part of the §7.1 MMIX "data length" family and are used by generated
; code (llc emits `.asciz` / `.zero`), so they MUST stay accepted.
; RUN: echo '.ascii "A"'      | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.asciz "A"'      | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.string "A"'     | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.zero 4'         | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.space 4'        | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.skip 4'         | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.fill 4, 1, 0'   | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.org 4'          | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.ds.b 4'         | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.p2align 3'      | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null

; REJ: unsupported directive '[[NAME]]' (data directive outside the DADAO unique set
; REJ-SAME: spec/Toolchain-01
; OCTA: unsupported directive '[[NAME]]' (GAS 16-byte octa)
; WORD: unknown directive
; NOTSUP: [[NAME]] not currently supported for this target
; UNKNOWN: unknown directive
