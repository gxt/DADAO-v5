@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'fornd rf0, rf1, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RF0
@@ RUN: echo 'ftrnd rf0, rf1, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RF0
@@ RUN: echo 'fornd rf1, rf2, 0' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OH
@@ RUN: echo 'fornd rf1, rf2, 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OH
@@ RUN: echo 'ftrnd rf1, rf2, 5' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OH
@@ RUN: echo 'ftrnd rf1, rf2, 63' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OH
@@ RUN: echo 'fornd rf1, rf2, 0x40' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OH

@@ roundToIntegral (`ftrnd`/`fornd`, orri) encoding round-trip: all six one-hot
@@ modes, both widths (LLVM-125t; SPEC-161t; contract-fp.md §roundint).
@@ Bytes are hand-computed from contracts/opcodes.yaml (NOT read back):
@@   word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|immu6, op = 0x44
@@   ftrnd ha = 0x03 (word base 0x440C0000)
@@   fornd ha = 0x0B (word base 0x442C0000)
@@ The immu6 one-hot mode values are 0x01/0x02/0x04/0x08/0x10/0x20; `immu6` and
@@ the register fields print in decimal, the byte dump in a byte-per-`0x` dump.
@@
@@ Assemble-time static legality (both hard errors, `llvm-mc` exits non-zero):
@@   dst_rf0      -- rf0 is the FCSR, never a destination; rf0 as source is OK
@@   encode_onehot -- immu6 must be exactly one of the six one-hot modes

@@ fornd rf1, rf2, 1        (0x01 ties-to-even)
@@ OBJ: {{[0-9a-f]+:}} 44 2c 10 81{{.*}}fornd{{.*}}rf1, rf2, 1
@@ ASM: fornd rf1, rf2, 1
fornd rf1, rf2, 1

@@ fornd rf3, rf4, 2        (0x02 ties-to-away)
@@ OBJ: {{[0-9a-f]+:}} 44 2c 31 02{{.*}}fornd{{.*}}rf3, rf4, 2
@@ ASM: fornd rf3, rf4, 2
fornd rf3, rf4, 2

@@ fornd rf5, rf6, 4        (0x04 toward zero)
@@ OBJ: {{[0-9a-f]+:}} 44 2c 51 84{{.*}}fornd{{.*}}rf5, rf6, 4
@@ ASM: fornd rf5, rf6, 4
fornd rf5, rf6, 4

@@ fornd rf7, rf8, 8        (0x08 toward +inf)
@@ OBJ: {{[0-9a-f]+:}} 44 2c 72 08{{.*}}fornd{{.*}}rf7, rf8, 8
@@ ASM: fornd rf7, rf8, 8
fornd rf7, rf8, 8

@@ fornd rf9, rf10, 16      (0x10 toward -inf)
@@ OBJ: {{[0-9a-f]+:}} 44 2c 92 90{{.*}}fornd{{.*}}rf9, rf10, 16
@@ ASM: fornd rf9, rf10, 16
fornd rf9, rf10, 16

@@ fornd rf11, rf12, 32     (0x20 dynamic, reads rf0[33:32])
@@ OBJ: {{[0-9a-f]+:}} 44 2c b3 20{{.*}}fornd{{.*}}rf11, rf12, 32
@@ ASM: fornd rf11, rf12, 32
fornd rf11, rf12, 32

@@ ftrnd rf1, rf2, 1
@@ OBJ: {{[0-9a-f]+:}} 44 0c 10 81{{.*}}ftrnd{{.*}}rf1, rf2, 1
@@ ASM: ftrnd rf1, rf2, 1
ftrnd rf1, rf2, 1

@@ ftrnd rf3, rf4, 2
@@ OBJ: {{[0-9a-f]+:}} 44 0c 31 02{{.*}}ftrnd{{.*}}rf3, rf4, 2
@@ ASM: ftrnd rf3, rf4, 2
ftrnd rf3, rf4, 2

@@ ftrnd rf5, rf6, 4
@@ OBJ: {{[0-9a-f]+:}} 44 0c 51 84{{.*}}ftrnd{{.*}}rf5, rf6, 4
@@ ASM: ftrnd rf5, rf6, 4
ftrnd rf5, rf6, 4

@@ ftrnd rf7, rf8, 8
@@ OBJ: {{[0-9a-f]+:}} 44 0c 72 08{{.*}}ftrnd{{.*}}rf7, rf8, 8
@@ ASM: ftrnd rf7, rf8, 8
ftrnd rf7, rf8, 8

@@ ftrnd rf9, rf10, 16
@@ OBJ: {{[0-9a-f]+:}} 44 0c 92 90{{.*}}ftrnd{{.*}}rf9, rf10, 16
@@ ASM: ftrnd rf9, rf10, 16
ftrnd rf9, rf10, 16

@@ ftrnd rf11, rf12, 32
@@ OBJ: {{[0-9a-f]+:}} 44 0c b3 20{{.*}}ftrnd{{.*}}rf11, rf12, 32
@@ ASM: ftrnd rf11, rf12, 32
ftrnd rf11, rf12, 32

@@ Negative cases (checked independently via the echo-piped RUN lines above).
@@ ERR-RF0: error: invalid '{{[a-z0-9.]+}}': rf0 is the FCSR and cannot be a floating-point destination (dst_rf0)
@@ ERR-OH: error: invalid '{{[a-z0-9.]+}}': rounding mode must be one of the one-hot constants 0x01/0x02/0x04/0x08/0x10/0x20 (encode_onehot)
