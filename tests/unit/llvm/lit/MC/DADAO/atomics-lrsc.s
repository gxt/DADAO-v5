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
@@ 汇编书写形态亦为规范形态：lr 两个操作数（SimRISC-12 原子指令）、sc 三个。

@@ NOCOMBO: unrecognized instruction mnemonic
@@ FORM: invalid operand for instruction
@@ BASE: invalid operand for instruction

.text

@@ @src lr.o.nn_orrr_rd  ha=0x00  word=0x47000241
@@ OBJ: {{[0-9a-f]+:}} 47 00 02 41{{.*}}lr.o.nn
@@ ASM: lr.o.nn rd9, [rb1]
lr.o.nn rd9, [rb1]

@@ @src lr.t.nn_orrr_rd  ha=0x01  word=0x47040241
@@ OBJ: {{[0-9a-f]+:}} 47 04 02 41{{.*}}lr.t.nn
@@ ASM: lr.t.nn rd9, [rb1]
lr.t.nn rd9, [rb1]

@@ @src lr.w.nn_orrr_rd  ha=0x02  word=0x47080241
@@ OBJ: {{[0-9a-f]+:}} 47 08 02 41{{.*}}lr.w.nn
@@ ASM: lr.w.nn rd9, [rb1]
lr.w.nn rd9, [rb1]

@@ @src lr.b.nn_orrr_rd  ha=0x03  word=0x470C0241
@@ OBJ: {{[0-9a-f]+:}} 47 0c 02 41{{.*}}lr.b.nn
@@ ASM: lr.b.nn rd9, [rb1]
lr.b.nn rd9, [rb1]

@@ @src lr.o.an_orrr_rd  ha=0x04  word=0x47100241
@@ OBJ: {{[0-9a-f]+:}} 47 10 02 41{{.*}}lr.o.an
@@ ASM: lr.o.an rd9, [rb1]
lr.o.an rd9, [rb1]

@@ @src lr.t.an_orrr_rd  ha=0x05  word=0x47140241
@@ OBJ: {{[0-9a-f]+:}} 47 14 02 41{{.*}}lr.t.an
@@ ASM: lr.t.an rd9, [rb1]
lr.t.an rd9, [rb1]

@@ @src lr.w.an_orrr_rd  ha=0x06  word=0x47180241
@@ OBJ: {{[0-9a-f]+:}} 47 18 02 41{{.*}}lr.w.an
@@ ASM: lr.w.an rd9, [rb1]
lr.w.an rd9, [rb1]

@@ @src lr.b.an_orrr_rd  ha=0x07  word=0x471C0241
@@ OBJ: {{[0-9a-f]+:}} 47 1c 02 41{{.*}}lr.b.an
@@ ASM: lr.b.an rd9, [rb1]
lr.b.an rd9, [rb1]

@@ @src lr.o.ar_orrr_rd  ha=0x08  word=0x47200241
@@ OBJ: {{[0-9a-f]+:}} 47 20 02 41{{.*}}lr.o.ar
@@ ASM: lr.o.ar rd9, [rb1]
lr.o.ar rd9, [rb1]

@@ @src lr.t.ar_orrr_rd  ha=0x09  word=0x47240241
@@ OBJ: {{[0-9a-f]+:}} 47 24 02 41{{.*}}lr.t.ar
@@ ASM: lr.t.ar rd9, [rb1]
lr.t.ar rd9, [rb1]

@@ @src lr.w.ar_orrr_rd  ha=0x0A  word=0x47280241
@@ OBJ: {{[0-9a-f]+:}} 47 28 02 41{{.*}}lr.w.ar
@@ ASM: lr.w.ar rd9, [rb1]
lr.w.ar rd9, [rb1]

@@ @src lr.b.ar_orrr_rd  ha=0x0B  word=0x472C0241
@@ OBJ: {{[0-9a-f]+:}} 47 2c 02 41{{.*}}lr.b.ar
@@ ASM: lr.b.ar rd9, [rb1]
lr.b.ar rd9, [rb1]

@@ @src sc.o.nn_orrr_rd  ha=0x10  word=0x47408241
@@ OBJ: {{[0-9a-f]+:}} 47 40 82 41{{.*}}sc.o.nn
@@ ASM: sc.o.nn rd8, rd9, [rb1]
sc.o.nn rd8, rd9, [rb1]

@@ @src sc.t.nn_orrr_rd  ha=0x11  word=0x47448241
@@ OBJ: {{[0-9a-f]+:}} 47 44 82 41{{.*}}sc.t.nn
@@ ASM: sc.t.nn rd8, rd9, [rb1]
sc.t.nn rd8, rd9, [rb1]

@@ @src sc.w.nn_orrr_rd  ha=0x12  word=0x47488241
@@ OBJ: {{[0-9a-f]+:}} 47 48 82 41{{.*}}sc.w.nn
@@ ASM: sc.w.nn rd8, rd9, [rb1]
sc.w.nn rd8, rd9, [rb1]

@@ @src sc.b.nn_orrr_rd  ha=0x13  word=0x474C8241
@@ OBJ: {{[0-9a-f]+:}} 47 4c 82 41{{.*}}sc.b.nn
@@ ASM: sc.b.nn rd8, rd9, [rb1]
sc.b.nn rd8, rd9, [rb1]

@@ @src sc.o.nr_orrr_rd  ha=0x14  word=0x47508241
@@ OBJ: {{[0-9a-f]+:}} 47 50 82 41{{.*}}sc.o.nr
@@ ASM: sc.o.nr rd8, rd9, [rb1]
sc.o.nr rd8, rd9, [rb1]

@@ @src sc.t.nr_orrr_rd  ha=0x15  word=0x47548241
@@ OBJ: {{[0-9a-f]+:}} 47 54 82 41{{.*}}sc.t.nr
@@ ASM: sc.t.nr rd8, rd9, [rb1]
sc.t.nr rd8, rd9, [rb1]

@@ @src sc.w.nr_orrr_rd  ha=0x16  word=0x47588241
@@ OBJ: {{[0-9a-f]+:}} 47 58 82 41{{.*}}sc.w.nr
@@ ASM: sc.w.nr rd8, rd9, [rb1]
sc.w.nr rd8, rd9, [rb1]

@@ @src sc.b.nr_orrr_rd  ha=0x17  word=0x475C8241
@@ OBJ: {{[0-9a-f]+:}} 47 5c 82 41{{.*}}sc.b.nr
@@ ASM: sc.b.nr rd8, rd9, [rb1]
sc.b.nr rd8, rd9, [rb1]

@@ @src sc.o.ar_orrr_rd  ha=0x18  word=0x47608241
@@ OBJ: {{[0-9a-f]+:}} 47 60 82 41{{.*}}sc.o.ar
@@ ASM: sc.o.ar rd8, rd9, [rb1]
sc.o.ar rd8, rd9, [rb1]

@@ @src sc.t.ar_orrr_rd  ha=0x19  word=0x47648241
@@ OBJ: {{[0-9a-f]+:}} 47 64 82 41{{.*}}sc.t.ar
@@ ASM: sc.t.ar rd8, rd9, [rb1]
sc.t.ar rd8, rd9, [rb1]

@@ @src sc.w.ar_orrr_rd  ha=0x1A  word=0x47688241
@@ OBJ: {{[0-9a-f]+:}} 47 68 82 41{{.*}}sc.w.ar
@@ ASM: sc.w.ar rd8, rd9, [rb1]
sc.w.ar rd8, rd9, [rb1]

@@ @src sc.b.ar_orrr_rd  ha=0x1B  word=0x476C8241
@@ OBJ: {{[0-9a-f]+:}} 47 6c 82 41{{.*}}sc.b.ar
@@ ASM: sc.b.ar rd8, rd9, [rb1]
sc.b.ar rd8, rd9, [rb1]
