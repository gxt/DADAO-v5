@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s --check-prefix=ENC
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
@@ RUN: cmp %t %t2

@@ M18（m18-llvm-002 / m18-spec-007）：`escape` 的汇编/反汇编形态改为
@@ **`escape cfxHA`**（只提供 cfxHA 操作数）。
@@
@@ 机器码布局不变：op=0x7E、cfxha[23:18]、imms18[17:0]；但 imms18 是
@@ SBZ，必须为 0（contracts/opcodes.yaml `escape_ciii_cfx` legality
@@ `imms18 == 0`）。旧的 `escape cfxHA, [excp_cause_ip, 0/4/8]` 偏移 /
@@ 帧选择位写法已作废（见 cfx2-escape-frame-err.s）；返回点由软件写
@@ `cg5 rc10`（escape ip，SimRISC-11 §3 / DADAO-12 §5.1）。
@@
@@ 编码独立派生自 contracts/opcodes.yaml（0x7E | cfxha<<18 | imms18，
@@ imms18 = 0），由同目录 validate_cfx_vectors.py 从契约重算并比对
@@ `@enc`/`OBJ`。反汇编只回显 `escape cfxHA`，不含偏移/帧选择。

@@ --- cfx_umon（0）：`cfx0` 与标量名等价 ---
@@ escape cfx_umon : cfxha=0, imms18=0 -> 7e 00 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 00{{.*}}escape cfx_umon
@@ ASM: escape cfx_umon
@@ ENC: escape cfx_umon {{.*}}encoding: [0x7e,0x00,0x00,0x00]
escape cfx_umon                         @@ @enc 7e000000

@@ escape cfx0 : 数字形与别名等价（同一元组，回显标量名）
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 00{{.*}}escape cfx_umon
@@ ASM: escape cfx_umon
escape cfx0                             @@ @enc 7e000000

@@ --- 其余已分配 cfx：imms18 恒 0，编码只差 cfxha ---
@@ escape cfx_jmon : cfxha=1 -> 7e 04 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 04 00 00{{.*}}escape cfx_jmon
@@ ASM: escape cfx_jmon
escape cfx_jmon                         @@ @enc 7e040000

@@ escape cfx_smon : cfxha=2 -> 7e 08 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 08 00 00{{.*}}escape cfx_smon
@@ ASM: escape cfx_smon
escape cfx_smon                         @@ @enc 7e080000

@@ escape cfx_hmon : cfxha=3 -> 7e 0c 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 0c 00 00{{.*}}escape cfx_hmon
@@ ASM: escape cfx_hmon
escape cfx_hmon                         @@ @enc 7e0c0000

@@ escape cfx_ptw : cfxha=4 -> 7e 10 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 10 00 00{{.*}}escape cfx_ptw
@@ ASM: escape cfx_ptw
escape cfx_ptw                          @@ @enc 7e100000

@@ escape cfx_cache : cfxha=5 -> 7e 14 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 14 00 00{{.*}}escape cfx_cache
@@ ASM: escape cfx_cache
escape cfx_cache                        @@ @enc 7e140000

@@ escape cfx_hart : cfxha=15 -> 7e 3c 00 00（异步进入的出口意图也在 hart cg5 rc8–rc11）
@@ OBJ: {{[0-9a-f]+:}} 7e 3c 00 00{{.*}}escape cfx_hart
@@ ASM: escape cfx_hart
@@ ENC: escape cfx_hart {{.*}}encoding: [0x7e,0x3c,0x00,0x00]
escape cfx_hart                         @@ @enc 7e3c0000

@@ escape cfx15 : 数字形等价
@@ OBJ: {{[0-9a-f]+:}} 7e 3c 00 00{{.*}}escape cfx_hart
@@ ASM: escape cfx_hart
escape cfx15                            @@ @enc 7e3c0000

@@ escape cfx_pmem : cfxha=32 -> 7e 80 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 80 00 00{{.*}}escape cfx_pmem
@@ ASM: escape cfx_pmem
escape cfx_pmem                         @@ @enc 7e800000

@@ escape cfx_llc : cfxha=33 -> 7e 84 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 84 00 00{{.*}}escape cfx_llc
@@ ASM: escape cfx_llc
escape cfx_llc                          @@ @enc 7e840000

@@ escape cfx_time : cfxha=34 -> 7e 88 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 88 00 00{{.*}}escape cfx_time
@@ ASM: escape cfx_time
escape cfx_time                         @@ @enc 7e880000

@@ escape cfx_uart : cfxha=62 -> 7e f8 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e f8 00 00{{.*}}escape cfx_uart
@@ ASM: escape cfx_uart
escape cfx_uart                         @@ @enc 7ef80000

@@ escape cfx_power : cfxha=63 -> 7e fc 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e fc 00 00{{.*}}escape cfx_power
@@ ASM: escape cfx_power
escape cfx_power                        @@ @enc 7efc0000
