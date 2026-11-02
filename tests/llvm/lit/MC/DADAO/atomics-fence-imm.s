@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'fence 4096'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=FM
@@ RUN: echo 'fence 2048'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SBZ
@@ RUN: echo 'fence 16'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SBZ
@@ RUN: echo 'fence 262144' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
@@ RUN: echo 'fence -1'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE

@@ fence 立即数（ADR-0034 D2 / SimRISC-12 原子指令；LLVM-121t）。
@@ 18 位立即数 = fm[17:12] | pred[11:6] | succ[5:0]，汇编层写一个无符号立即数；
@@ PRED_R/W/I/O = 1<<6..1<<9，SUCC_R/W/I/O = 1<<0..1<<3，按 | 组合。
@@ 合法编码的期望值独立派生自 ADR-0034 D2 的常量表（不从 llvm-mc 反填）：
@@   fm = 0 唯一已定义；pred[11:10] / succ[5:4] = SBZ（非零 ⇒ 保留 ⇒ ILLI）。

@@ FM: fence: reserved encoding
@@ SBZ: fence: reserved encoding
@@ RANGE: immediate out of range

.text

@@ fence 0 —— fm = 0，pred = succ = 0（最弱形态）
@@ word = (0x47<<24)|(0x20<<18)|0 = 0x47800000
@@ OBJ: {{[0-9a-f]+:}} 47 80 00 00{{.*}}fence{{.*}}0
@@ ASM: fence 0
fence 0

@@ acquire：PRED_R | SUCC_R | SUCC_W = 0x040|0x001|0x002 = 0x043
@@ OBJ: {{[0-9a-f]+:}} 47 80 00 43{{.*}}fence{{.*}}67
@@ ASM: fence 67
fence PRED_R|SUCC_R|SUCC_W

@@ release：PRED_R | PRED_W | SUCC_W = 0x040|0x080|0x002 = 0x0C2
@@ OBJ: {{[0-9a-f]+:}} 47 80 00 c2{{.*}}fence{{.*}}194
@@ ASM: fence 194
fence PRED_R|PRED_W|SUCC_W

@@ 全屏障：PRED_R|PRED_W|PRED_I|PRED_O|SUCC_R|SUCC_W|SUCC_I|SUCC_O = 0x3CF
@@ OBJ: {{[0-9a-f]+:}} 47 80 03 cf{{.*}}fence{{.*}}975
@@ ASM: fence 975
fence PRED_R|PRED_W|PRED_I|PRED_O|SUCC_R|SUCC_W|SUCC_I|SUCC_O

@@ 符号常量与同值数字必须编码一致（0x00C3 = PRED_R|PRED_W|SUCC_R|SUCC_W）
@@ OBJ: {{[0-9a-f]+:}} 47 80 00 c3{{.*}}fence{{.*}}195
@@ ASM: fence 195
fence PRED_R|PRED_W|SUCC_R|SUCC_W
fence 0x00C3
