@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

@@ oiii format: opx + immediate instructions (swym)
@@ Encoding: word = (op<<24)|(ha<<18)|(imm18 & 0x3FFFF)

@@ swym 0
@@ op=0x47, ha=0x22(swym), imm18=0
@@ word = (0x47<<24)|(0x22<<18)|0 = 0x47880000
@@ OBJ: {{[0-9a-f]+:}} 47 88 00 00{{.*}}swym{{.*}}0
@@ ASM: swym 0
swym 0

@@ swym 42
@@ op=0x47, ha=0x22(swym), imm18=42=0x2A
@@ word = (0x47<<24)|(0x22<<18)|0x2A = 0x4788002A
@@ OBJ: {{[0-9a-f]+:}} 47 88 00 2a{{.*}}swym{{.*}}42
@@ ASM: swym 42
swym 42
