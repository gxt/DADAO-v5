# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# Wyde-position operand tests (LLVM-013t):
# wp0/wp1/wp2/wp3 tokens accepted as alias for numeric 0-3.
# Numeric 0-3 still works (no regression).
# wp4 and other invalid tokens → error.
# wp in hb[5:4]; immu16 in hb[3:0]:hc:hd.
# rwii format: word = (op<<24)|(ra<<18)|((wp<<4)|(imm16>>12))<<12|((imm16>>6)&0x3F)<<6|(imm16&0x3F)

# --- wp0-wp3 with imm16=0xFFFF ---

# OBJ: {{[0-9a-f]+:}} 4e 04 ff ff{{.*}}set.zw{{.*}}rb1, 0, 65535
# ASM: set.zw rb1, 0, 65535
set.zw rb1, wp0, 0xffff

# OBJ: {{[0-9a-f]+:}} 4e 05 ff ff{{.*}}set.zw{{.*}}rb1, 1, 65535
# ASM: set.zw rb1, 1, 65535
set.zw rb1, wp1, 0xffff

# OBJ: {{[0-9a-f]+:}} 4e 06 ff ff{{.*}}set.zw{{.*}}rb1, 2, 65535
# ASM: set.zw rb1, 2, 65535
set.zw rb1, wp2, 0xffff

# OBJ: {{[0-9a-f]+:}} 4e 07 ff ff{{.*}}set.zw{{.*}}rb1, 3, 65535
# ASM: set.zw rb1, 3, 65535
set.zw rb1, wp3, 0xffff

# --- Numeric 0-3 with imm16=0xFFFF (regression guard) ---

# OBJ: {{[0-9a-f]+:}} 4e 04 ff ff{{.*}}set.zw{{.*}}rb1, 0, 65535
# ASM: set.zw rb1, 0, 65535
set.zw rb1, 0, 0xffff

# OBJ: {{[0-9a-f]+:}} 4e 05 ff ff{{.*}}set.zw{{.*}}rb1, 1, 65535
# ASM: set.zw rb1, 1, 65535
set.zw rb1, 1, 0xffff

# OBJ: {{[0-9a-f]+:}} 4e 06 ff ff{{.*}}set.zw{{.*}}rb1, 2, 65535
# ASM: set.zw rb1, 2, 65535
set.zw rb1, 2, 0xffff

# OBJ: {{[0-9a-f]+:}} 4e 07 ff ff{{.*}}set.zw{{.*}}rb1, 3, 65535
# ASM: set.zw rb1, 3, 65535
set.zw rb1, 3, 0xffff

# --- wp0-wp3 with different imm16 (0x00FF = 255) ---

# OBJ: {{[0-9a-f]+:}} 4e 04 00 ff{{.*}}set.zw{{.*}}rb1, 0, 255
# ASM: set.zw rb1, 0, 255
set.zw rb1, wp0, 0x00ff

# OBJ: {{[0-9a-f]+:}} 4e 05 00 ff{{.*}}set.zw{{.*}}rb1, 1, 255
# ASM: set.zw rb1, 1, 255
set.zw rb1, wp1, 0x00ff

# OBJ: {{[0-9a-f]+:}} 4e 06 00 ff{{.*}}set.zw{{.*}}rb1, 2, 255
# ASM: set.zw rb1, 2, 255
set.zw rb1, wp2, 0x00ff

# OBJ: {{[0-9a-f]+:}} 4e 07 00 ff{{.*}}set.zw{{.*}}rb1, 3, 255
# ASM: set.zw rb1, 3, 255
set.zw rb1, wp3, 0x00ff
