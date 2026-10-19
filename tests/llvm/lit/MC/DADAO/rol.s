@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'ror.o rd8, rd9, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OLD
@@ RUN: echo 'ror.b rd8, rd9, 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OLD
@@ RUN: echo 'shl.uo rd8, rd9, 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OLD
@@ RUN: echo 'shl.ut rd8, rd9, 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OLD
@@ RUN: echo 'shl.uw rd8, rd9, 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OLD
@@ RUN: echo 'shl.ub rd8, rd9, 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-OLD

@@ `rol.o/t/w/b` (ADR-0032 D4 as amended 2026-10-19: ror -> rol; encoding
@@ slots unchanged at 010-001 orrr / 011-001 orri): logical rotate left.
@@ The register form takes rdHD[log2(W)-1:0] (amount modulo W); the immediate
@@ form takes immu6, and amounts outside 0..W-1 are an execution-time ILLI
@@ (SimRISC-04/08/09/10 §2), so the MC layer only enforces the generic immu6
@@ field range [0, 63].
@@
@@ `shl.o/t/w/b` (ADR-0032 D2/D3) no longer accept the removed `shl.u*`
@@ spelling (D3 rejected an alias), and `ror.*` is not kept as an alias of
@@ `rol.*`: the old mnemonics are unrecognized.

@@ rol.o rd8, rd9, rd10
@@ op=0x40, ha=0x11(rol.o), hb=rd8=8, hc=rd9=9, hd=rd10=10
@@ word = (0x40<<24)|(0x11<<18)|(8<<12)|(9<<6)|10 = 0x4044824A
@@ OBJ: {{[0-9a-f]+:}} 40 44 82 4a{{.*}}rol.o{{.*}}rd8, rd9, rd10
@@ ASM: rol.o rd8, rd9, rd10
rol.o rd8, rd9, rd10

@@ rol.o rd8, rd9, 7
@@ op=0x40, ha=0x19(rol.o orri), hb=rd8=8, hc=rd9=9, hd=immu6=7
@@ word = (0x40<<24)|(0x19<<18)|(8<<12)|(9<<6)|7 = 0x40648247
@@ OBJ: {{[0-9a-f]+:}} 40 64 82 47{{.*}}rol.o{{.*}}rd8, rd9, 7
@@ ASM: rol.o rd8, rd9, 7
rol.o rd8, rd9, 7

@@ rol.t rd8, rd9, rd10
@@ op=0x41, ha=0x11(rol.t), hb=rd8=8, hc=rd9=9, hd=rd10=10
@@ word = (0x41<<24)|(0x11<<18)|(8<<12)|(9<<6)|10 = 0x4144824A
@@ OBJ: {{[0-9a-f]+:}} 41 44 82 4a{{.*}}rol.t{{.*}}rd8, rd9, rd10
@@ ASM: rol.t rd8, rd9, rd10
rol.t rd8, rd9, rd10

@@ rol.w rd8, rd9, rd10
@@ op=0x42, ha=0x11(rol.w), hb=rd8=8, hc=rd9=9, hd=rd10=10
@@ word = (0x42<<24)|(0x11<<18)|(8<<12)|(9<<6)|10 = 0x4244824A
@@ OBJ: {{[0-9a-f]+:}} 42 44 82 4a{{.*}}rol.w{{.*}}rd8, rd9, rd10
@@ ASM: rol.w rd8, rd9, rd10
rol.w rd8, rd9, rd10

@@ rol.b rd8, rd9, rd10 (register amount 10; rol.b consumes it modulo 8)
@@ op=0x43, ha=0x11(rol.b), hb=rd8=8, hc=rd9=9, hd=rd10=10
@@ word = (0x43<<24)|(0x11<<18)|(8<<12)|(9<<6)|10 = 0x4344824A
@@ OBJ: {{[0-9a-f]+:}} 43 44 82 4a{{.*}}rol.b{{.*}}rd8, rd9, rd10
@@ ASM: rol.b rd8, rd9, rd10
rol.b rd8, rd9, rd10

@@ rol.b rd8, rd9, 7 (immediate boundary within rol.b's 0..7 range)
@@ op=0x43, ha=0x19(rol.b orri), hb=rd8=8, hc=rd9=9, hd=immu6=7
@@ word = (0x43<<24)|(0x19<<18)|(8<<12)|(9<<6)|7 = 0x43648247
@@ OBJ: {{[0-9a-f]+:}} 43 64 82 47{{.*}}rol.b{{.*}}rd8, rd9, 7
@@ ASM: rol.b rd8, rd9, 7
rol.b rd8, rd9, 7

@@ rol.b rd8, rd9, 8 is still encodable (immu6 = 8); rol.b's width check is an
@@ execution-time ILLI (SimRISC-10 §2), not an assembler error.
rol.b rd8, rd9, 8

@@ ERR-OLD: error: unrecognized instruction mnemonic
