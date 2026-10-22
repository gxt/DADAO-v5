@@ RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=OK
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s 2>&1 | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'aip.si rb2, 1'          | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-ALIGN
@@ RUN: echo 'aip.si rb2, 4097'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-ALIGN
@@ RUN: echo 'aip.si rb2, 536870912'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RANGE
@@ RUN: echo 'aip.si rb2, -537395200' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-RANGE

@@ `aip.si` operand units (ADR-0029 §修订注记 ④; Toolchain-01 §3.2/§5;
@@ SimRISC-05 §1.4): the assembler-level operand is a BYTE count (field name
@@ `imms30`) while the encoded 18-bit field is the 4 KiB block count
@@ (`imms18 = imms30 >> 12`, the x4096 group of the x4 jump/branch fields).
@@ Therefore:
@@   * the operand MUST be a multiple of 4096 (low 12 bits zero) -- otherwise the
@@     block field cannot represent it and the assembler MUST hard-error (Error
@@     level, non-zero exit; no truncation, no silent round-down);
@@   * it MUST fit the reachable +-512 MiB of the signed 18-bit block field, i.e.
@@     [-536870912, 536866816] (= -131072/131071 << 12);
@@   * the printer prints the byte value back (field << 12) so the assembly
@@     round trip is exact.
@@
@@ The encodings below are the independent oracle: bytes derive from
@@ contracts/opcodes.yaml (op=0x5A, rbha at bits[23:18], imms18 at bits[17:0]);
@@ rb2 => 2 << 18 = 0x00080000.

@@ --- boundaries accepted and encoded exactly (no false rejection) ---
@@ OK: encoding: [0x5a,0x08,0x00,0x00]
@@ ASM: aip.si rb2, 0
aip.si rb2, 0
@@ OK: encoding: [0x5a,0x08,0x00,0x01]
@@ ASM: aip.si rb2, 4096
aip.si rb2, 4096
@@ OK: encoding: [0x5a,0x0b,0xff,0xff]
@@ ASM: aip.si rb2, -4096
aip.si rb2, -4096
@@ OK: encoding: [0x5a,0x09,0xff,0xff]
@@ ASM: aip.si rb2, 536866816
aip.si rb2, 536866816
@@ OK: encoding: [0x5a,0x0a,0x00,0x00]
@@ ASM: aip.si rb2, -536870912
aip.si rb2, -536870912

@@ --- rejection diagnostics (low 12 bits non-zero / +-512 MiB) ---
@@ ERR-ALIGN: error: aip.si offset must be a multiple of 4096 bytes
@@ ERR-RANGE: error: aip.si byte offset out of range: expected [-536870912, 536866816] (imms30, %4096==0, +-512 MiB)
