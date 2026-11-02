@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'fence 0'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OLD
@@ RUN: echo 'fence cfx0, 0x1000' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=HB
@@ RUN: echo 'fence cfx0, 0x3F000' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=HB
@@ RUN: echo 'fence cfx0, 262144' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
@@ RUN: echo 'fence cfx0, -1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE

@@ fence ciii（ADR-0044 D1/D3/D4；SimRISC-11）。
@@ 编码 word = (opc<<24) | (cfxha<<18) | (hb<<12) | (pred<<6) | succ。
@@ hb = immu18[17:12] 必须为 0；pred/succ 位：cr=1<<0 cw=1<<1 ci=1<<2
@@ co=1<<3 mr=1<<4 mw=1<<5。汇编常量 PRED_*/SUCC_* 按位或组合。
@@ `cfx0` 与 `cfx_umon` 都是 all cfx；`fence 0` 不是合法语法。

@@ OLD: error:
@@ HB: fence: reserved encoding
@@ RANGE: immediate out of range

.text

@@ no-op：cfx0（all cfx），pred = succ = 0
@@ word = (0x79<<24)|(0<<18)|0 = 0x79000000
@@ OBJ: {{[0-9a-f]+:}} 79 00 00 00{{.*}}fence{{.*}}cfx_umon{{.*}}0
@@ ASM: fence cfx_umon, 0
fence cfx0, 0

@@ cfx_umon 与 cfx0 编码相同
fence cfx_umon, 0

@@ cr -> cr|cw：PRED_CR=1<<6、SUCC_CR=1<<0、SUCC_CW=1<<1 ⇒ immu18=0x043
@@ OBJ: {{[0-9a-f]+:}} 79 00 00 43{{.*}}fence{{.*}}cfx_umon{{.*}}67
@@ ASM: fence cfx_umon, 67
fence cfx0, PRED_CR|SUCC_CR|SUCC_CW

@@ 系统内存 acquire：mr -> mr|mw ⇒ immu18 = 0x430
@@ OBJ: {{[0-9a-f]+:}} 79 00 04 30{{.*}}fence{{.*}}cfx_umon{{.*}}1072
@@ ASM: fence cfx_umon, 1072
fence cfx0, PRED_MR|SUCC_MR|SUCC_MW

@@ 全屏障：所有六位 ⇒ immu18 = 0xFFF；cfx63 编码 ha=0x3F ⇒ 0x79FC0FFF
@@ OBJ: {{[0-9a-f]+:}} 79 fc 0f ff{{.*}}fence{{.*}}cfx_power{{.*}}4095
@@ ASM: fence cfx_power, 4095
fence cfx63, PRED_CR|PRED_CW|PRED_CI|PRED_CO|PRED_MR|PRED_MW|SUCC_CR|SUCC_CW|SUCC_CI|SUCC_CO|SUCC_MR|SUCC_MW

@@ 符号常量与同值数字编码一致
@@ OBJ: {{[0-9a-f]+:}} 79 00 00 43{{.*}}fence{{.*}}cfx_umon{{.*}}67
@@ ASM: fence cfx_umon, 67
fence cfx0, 0x043
