@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'clmul.o {rd7, rd7}, rd2, rd3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-SAME
@@ RUN: echo 'clmul.o {rd0, rd0}, rd2, rd3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-ZERO
@@ RUN: echo 'clmul.o rd8, rd9, rd10, rd11' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-SYNTAX

@@ `clmul.o` (ADR-0035; LLVM-122t): rrrr, op 0x56, rdHA = high 64 bits,
@@ rdHB = low 64 bits.  Word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd.
@@
@@ Legal forms (assembled below):
@@   clmul.o {rd8, rd9}, rd10, rd11   -> 0x56_20_92_8B  (both halves)
@@   clmul.o {rd0, rd9}, rd10, rd11   -> 0x56_00_92_8B  (low half only, D6)
@@   clmul.o {rd8, rd0}, rd10, rd11   -> 0x56_20_02_8B  (high half only, D6)
@@
@@ Illegal forms (checked independently via echo-piped RUN lines above), rule
@@ `dst_dual_same` (ADR-0035 D6; SimRISC-04 §1.1): the two destination fields
@@ may not name the same register and may not both be rd0.

@@ OBJ: {{[0-9a-f]+:}} 56 20 92 8b{{.*}}clmul.o{{.*}}{rd8, rd9}, rd10, rd11
@@ ASM: clmul.o {rd8, rd9}, rd10, rd11
clmul.o {rd8, rd9}, rd10, rd11

@@ OBJ: {{[0-9a-f]+:}} 56 00 92 8b{{.*}}clmul.o{{.*}}{rd0, rd9}, rd10, rd11
@@ ASM: clmul.o {rd0, rd9}, rd10, rd11
clmul.o {rd0, rd9}, rd10, rd11

@@ OBJ: {{[0-9a-f]+:}} 56 20 02 8b{{.*}}clmul.o{{.*}}{rd8, rd0}, rd10, rd11
@@ ASM: clmul.o {rd8, rd0}, rd10, rd11
clmul.o {rd8, rd0}, rd10, rd11

@@ ERR-SAME: error: invalid 'clmul.o': both destinations are the same register (dst_dual_same)
@@ ERR-ZERO: error: invalid 'clmul.o': both destination registers are rd0 (dst_dual_same)
@@ ERR-SYNTAX: error: old syntax not accepted; use '{}' for dual-purpose destination registers
