@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: echo 'lr.o.nr rd1, [rb2]'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NOCOMBO
@@ RUN: echo 'sc.o.an rd1, rd2, [rb2]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NOCOMBO
@@ RUN: echo 'lr.o.nn rd1, rd2, [rb2]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=FORM
@@ RUN: echo 'lr.o.nn rd1, [rd2]'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=BASE

@@ lr/sc 24 条 MC 编码（ADR-0034 D3/D4/D5；LLVM-121t）。
@@ 期望值独立派生自 ADR-0034 D5 落位表，**不从 llvm-mc 反填**：
@@   word = (op<<24) | (ha<<18) | (hb<<12) | (hc<<6) | hd
@@   lr.*: hb = 0（rd0 固定），hc = rd9 = 9，hd = rb1 = 1
@@   sc.*: hb = rd8 = 8，hc = rd9 = 9，hd = rb1 = 1
@@ 汇编书写形态亦为规范形态：lr 两个操作数（SimRISC-11 §4.2）、sc 三个。

@@ NOCOMBO: unrecognized instruction mnemonic
@@ FORM: invalid operand for instruction
@@ BASE: invalid operand for instruction

.text

@@ @src lr.o.nn_orrr_rd  ha=0x00  word=0x77000241
@@ OBJ: {{[0-9a-f]+:}} 77 00 02 41{{.*}}lr.o.nn
@@ ASM: lr.o.nn rd9, [rb1]
lr.o.nn rd9, [rb1]

@@ @src lr.t.nn_orrr_rd  ha=0x01  word=0x77040241
@@ OBJ: {{[0-9a-f]+:}} 77 04 02 41{{.*}}lr.t.nn
@@ ASM: lr.t.nn rd9, [rb1]
lr.t.nn rd9, [rb1]

@@ @src lr.w.nn_orrr_rd  ha=0x02  word=0x77080241
@@ OBJ: {{[0-9a-f]+:}} 77 08 02 41{{.*}}lr.w.nn
@@ ASM: lr.w.nn rd9, [rb1]
lr.w.nn rd9, [rb1]

@@ @src lr.b.nn_orrr_rd  ha=0x03  word=0x770C0241
@@ OBJ: {{[0-9a-f]+:}} 77 0c 02 41{{.*}}lr.b.nn
@@ ASM: lr.b.nn rd9, [rb1]
lr.b.nn rd9, [rb1]

@@ @src lr.o.an_orrr_rd  ha=0x04  word=0x77100241
@@ OBJ: {{[0-9a-f]+:}} 77 10 02 41{{.*}}lr.o.an
@@ ASM: lr.o.an rd9, [rb1]
lr.o.an rd9, [rb1]

@@ @src lr.t.an_orrr_rd  ha=0x05  word=0x77140241
@@ OBJ: {{[0-9a-f]+:}} 77 14 02 41{{.*}}lr.t.an
@@ ASM: lr.t.an rd9, [rb1]
lr.t.an rd9, [rb1]

@@ @src lr.w.an_orrr_rd  ha=0x06  word=0x77180241
@@ OBJ: {{[0-9a-f]+:}} 77 18 02 41{{.*}}lr.w.an
@@ ASM: lr.w.an rd9, [rb1]
lr.w.an rd9, [rb1]

@@ @src lr.b.an_orrr_rd  ha=0x07  word=0x771C0241
@@ OBJ: {{[0-9a-f]+:}} 77 1c 02 41{{.*}}lr.b.an
@@ ASM: lr.b.an rd9, [rb1]
lr.b.an rd9, [rb1]

@@ @src lr.o.ar_orrr_rd  ha=0x08  word=0x77200241
@@ OBJ: {{[0-9a-f]+:}} 77 20 02 41{{.*}}lr.o.ar
@@ ASM: lr.o.ar rd9, [rb1]
lr.o.ar rd9, [rb1]

@@ @src lr.t.ar_orrr_rd  ha=0x09  word=0x77240241
@@ OBJ: {{[0-9a-f]+:}} 77 24 02 41{{.*}}lr.t.ar
@@ ASM: lr.t.ar rd9, [rb1]
lr.t.ar rd9, [rb1]

@@ @src lr.w.ar_orrr_rd  ha=0x0A  word=0x77280241
@@ OBJ: {{[0-9a-f]+:}} 77 28 02 41{{.*}}lr.w.ar
@@ ASM: lr.w.ar rd9, [rb1]
lr.w.ar rd9, [rb1]

@@ @src lr.b.ar_orrr_rd  ha=0x0B  word=0x772C0241
@@ OBJ: {{[0-9a-f]+:}} 77 2c 02 41{{.*}}lr.b.ar
@@ ASM: lr.b.ar rd9, [rb1]
lr.b.ar rd9, [rb1]

@@ @src sc.o.nn_orrr_rd  ha=0x10  word=0x77408241
@@ OBJ: {{[0-9a-f]+:}} 77 40 82 41{{.*}}sc.o.nn
@@ ASM: sc.o.nn rd8, rd9, [rb1]
sc.o.nn rd8, rd9, [rb1]

@@ @src sc.t.nn_orrr_rd  ha=0x11  word=0x77448241
@@ OBJ: {{[0-9a-f]+:}} 77 44 82 41{{.*}}sc.t.nn
@@ ASM: sc.t.nn rd8, rd9, [rb1]
sc.t.nn rd8, rd9, [rb1]

@@ @src sc.w.nn_orrr_rd  ha=0x12  word=0x77488241
@@ OBJ: {{[0-9a-f]+:}} 77 48 82 41{{.*}}sc.w.nn
@@ ASM: sc.w.nn rd8, rd9, [rb1]
sc.w.nn rd8, rd9, [rb1]

@@ @src sc.b.nn_orrr_rd  ha=0x13  word=0x774C8241
@@ OBJ: {{[0-9a-f]+:}} 77 4c 82 41{{.*}}sc.b.nn
@@ ASM: sc.b.nn rd8, rd9, [rb1]
sc.b.nn rd8, rd9, [rb1]

@@ @src sc.o.nr_orrr_rd  ha=0x14  word=0x77508241
@@ OBJ: {{[0-9a-f]+:}} 77 50 82 41{{.*}}sc.o.nr
@@ ASM: sc.o.nr rd8, rd9, [rb1]
sc.o.nr rd8, rd9, [rb1]

@@ @src sc.t.nr_orrr_rd  ha=0x15  word=0x77548241
@@ OBJ: {{[0-9a-f]+:}} 77 54 82 41{{.*}}sc.t.nr
@@ ASM: sc.t.nr rd8, rd9, [rb1]
sc.t.nr rd8, rd9, [rb1]

@@ @src sc.w.nr_orrr_rd  ha=0x16  word=0x77588241
@@ OBJ: {{[0-9a-f]+:}} 77 58 82 41{{.*}}sc.w.nr
@@ ASM: sc.w.nr rd8, rd9, [rb1]
sc.w.nr rd8, rd9, [rb1]

@@ @src sc.b.nr_orrr_rd  ha=0x17  word=0x775C8241
@@ OBJ: {{[0-9a-f]+:}} 77 5c 82 41{{.*}}sc.b.nr
@@ ASM: sc.b.nr rd8, rd9, [rb1]
sc.b.nr rd8, rd9, [rb1]

@@ @src sc.o.ar_orrr_rd  ha=0x18  word=0x77608241
@@ OBJ: {{[0-9a-f]+:}} 77 60 82 41{{.*}}sc.o.ar
@@ ASM: sc.o.ar rd8, rd9, [rb1]
sc.o.ar rd8, rd9, [rb1]

@@ @src sc.t.ar_orrr_rd  ha=0x19  word=0x77648241
@@ OBJ: {{[0-9a-f]+:}} 77 64 82 41{{.*}}sc.t.ar
@@ ASM: sc.t.ar rd8, rd9, [rb1]
sc.t.ar rd8, rd9, [rb1]

@@ @src sc.w.ar_orrr_rd  ha=0x1A  word=0x77688241
@@ OBJ: {{[0-9a-f]+:}} 77 68 82 41{{.*}}sc.w.ar
@@ ASM: sc.w.ar rd8, rd9, [rb1]
sc.w.ar rd8, rd9, [rb1]

@@ @src sc.b.ar_orrr_rd  ha=0x1B  word=0x776C8241
@@ OBJ: {{[0-9a-f]+:}} 77 6c 82 41{{.*}}sc.b.ar
@@ ASM: sc.b.ar rd8, rd9, [rb1]
sc.b.ar rd8, rd9, [rb1]
