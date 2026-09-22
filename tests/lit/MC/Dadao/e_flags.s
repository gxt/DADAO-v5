# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
# RUN: %llvm_readobj -h %t.o | %FileCheck %s

# Verify ADR-0003 §D1: e_flags = 0x00000001 (M1 object/ABI format version).
# bits 0–7 = version (M1 = 1); bits 8–31 = reserved (0).

# CHECK:      ElfHeader {
# CHECK:        Ident {
# CHECK:          Class:    64-bit (0x2)
# CHECK:          DataEncoding: BigEndian (0x2)
# CHECK:          OS/ABI:   SystemV (0x0)
# CHECK:        }
# CHECK:        Machine: 0xDA0
# CHECK:        Flags [ (0x1)
# CHECK-NEXT:     0x1
# CHECK-NEXT:   ]

jump 0
