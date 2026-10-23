@@ Fused multiply-add MC layer (LLVM-123t; contract-fp.md §fma = SimRISC-07 §2.5)
@@
@@ Encoding source of truth: contracts/opcodes.yaml
@@   ftfma_rrrr_rf  op 0x5E  mask 0xFF000000  (rrrr, 1 dst + 3 src)
@@   fofma_rrrr_rf  op 0x5F  mask 0xFF000000
@@ With rf8/rf9/rf10/rf11 in the four 6-bit fields:
@@   value | 8<<18 | 9<<12 | 10<<6 | 11 = 0x5E20928B / 0x5F20928B
@@ (same operand-assignment rule as the generated gen-rrrr.s vectors).
@@
@@ `dst_rf0` (contracts/opcodes.yaml legality: rfha != rf0): rf0 is the FCSR and
@@ cannot be an FP destination.  The `.td` destination class is GPRF_NoRF0, so the
@@ MC assembler refuses it and the disassembler renders such a word as unknown
@@ (the runtime form is ILLI).  rf0 as a *source* stays legal.

@@ RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=DIS
@@ RUN: echo 'fofma rf0, rf1, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
@@ RUN: echo 'ftfma rf0, rf1, rf2, rf3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
@@ RUN: echo '.dd.t32 0x5f00928b' | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.rf0.o
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.rf0.o | %FileCheck %s --check-prefix=DEC

.text
fofma rf8, rf9, rf10, rf11
ftfma rf8, rf9, rf10, rf11
@@ rf0 is a legal source (only the destination is constrained).
fofma rf8, rf0, rf9, rf10
ftfma rf8, rf0, rf9, rf10

@@ OK: fofma rf8, rf9, rf10, rf11  @@ encoding: [0x5f,0x20,0x92,0x8b]
@@ OK: ftfma rf8, rf9, rf10, rf11  @@ encoding: [0x5e,0x20,0x92,0x8b]

@@ DIS: fofma rf8, rf9, rf10, rf11
@@ DIS: ftfma rf8, rf9, rf10, rf11
@@ DIS: fofma rf8, rf0, rf9, rf10
@@ DIS: ftfma rf8, rf0, rf9, rf10

@@ ERR: error: invalid operand for instruction

@@ The rf0-destination word is not a valid instruction: no `fofma` here.
@@ DEC-NOT: fofma
@@ DEC: <unknown>
