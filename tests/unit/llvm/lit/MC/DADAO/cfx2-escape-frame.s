@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
@@ RUN: cmp %t %t2

@@ M18（m18-llvm-001 / m18-spec-003）：escape 的帧选择位（imms18 bit1）。
@@
@@ 汇编层 `imms20`（字节）合法集 = {0, 4, 8}（Toolchain-01 §2.4/§5；
@@ SimRISC-11 §3）；编码 `imms18 = imms20 >> 2` ∈ {0, 1, 2}：
@@   imms18[0] = cg5 字节偏移 bit2（0 = +0、1 = +4）；
@@   imms18[1] = 帧选择位（0 = cg5 同步异常帧、1 = cg9 异步现场，偏移恒 0）。
@@ 故汇编 `8` ⇔ `imms18 = 2`（cg9）；反汇编按规范长形回显 `<<2`，
@@ cg5 输出 0/4、cg9 输出 8，两侧可区分且字节级往返一致。
@@ `imms18 = 3`（cg9 + 偏移 +4）与 `imms18[17:2] != 0` 是**架构 ILLI**，
@@ 汇编器不生成（负向见同目录 `cfx2-escape-frame-err.s`）。
@@
@@ 编码独立派生自 contracts/opcodes.yaml（0x7E | cfxha<<18 | imms18），
@@ 由同目录 `validate_cfx_vectors.py` 从契约重算并比对 `@enc`/`OBJ`。

@@ --- cfx_cache（5）: cg5 同步帧，偏移 0 / +4 ---
@@ escape cfx_cache, [excp_cause_ip, 0] : imms18=0 -> 7e 14 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 14 00 00{{.*}}escape cfx_cache, [excp_cause_ip, 0]
@@ ASM: escape cfx_cache, [excp_cause_ip, 0]
escape cfx_cache, [excp_cause_ip, 0]          @@ @enc 7e140000

@@ escape cfx_cache, [excp_cause_ip, 4] : imms18=1 -> 7e 14 00 01
@@ OBJ: {{[0-9a-f]+:}} 7e 14 00 01{{.*}}escape cfx_cache, [excp_cause_ip, 4]
@@ ASM: escape cfx_cache, [excp_cause_ip, 4]
escape cfx_cache, [excp_cause_ip, 4]          @@ @enc 7e140001

@@ --- cfx_smon（2）: cg5 0/+4 与 cg9 0 ---
@@ escape cfx_smon, [excp_cause_ip, 0] : imms18=0 -> 7e 08 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 08 00 00{{.*}}escape cfx_smon, [excp_cause_ip, 0]
@@ ASM: escape cfx_smon, [excp_cause_ip, 0]
escape cfx_smon, [excp_cause_ip, 0]      @@ @enc 7e080000

@@ escape cfx_smon, [excp_cause_ip, 4] : imms18=1 -> 7e 08 00 01
@@ OBJ: {{[0-9a-f]+:}} 7e 08 00 01{{.*}}escape cfx_smon, [excp_cause_ip, 4]
@@ ASM: escape cfx_smon, [excp_cause_ip, 4]
escape cfx_smon, [excp_cause_ip, 4]      @@ @enc 7e080001

@@ escape cfx_smon, [excp_cause_ip, 8] : imms18=2（bit1=1）-> 7e 08 00 02
@@ OBJ: {{[0-9a-f]+:}} 7e 08 00 02{{.*}}escape cfx_smon, [excp_cause_ip, 8]
@@ ASM: escape cfx_smon, [excp_cause_ip, 8]
escape cfx_smon, [excp_cause_ip, 8]      @@ @enc 7e080002

@@ --- cfx_hart（15）: cg9 异步现场（imms20 = 8，偏移恒 0） ---
@@ escape cfx_hart, [excp_cause_ip, 8] : cfxha=15, imms18=2 -> 7e 3c 00 02
@@ OBJ: {{[0-9a-f]+:}} 7e 3c 00 02{{.*}}escape cfx_hart, [excp_cause_ip, 8]
@@ ASM: escape cfx_hart, [excp_cause_ip, 8]
escape cfx_hart, [excp_cause_ip, 8]      @@ @enc 7e3c0002

@@ 同一 cfx 的 cg5 帧（0/4）与 cg9 现场（8）并存，编码只差 bit1/bit0：
@@ OBJ: {{[0-9a-f]+:}} 7e 3c 00 00{{.*}}escape cfx_hart, [excp_cause_ip, 0]
@@ ASM: escape cfx_hart, [excp_cause_ip, 0]
escape cfx_hart, [excp_cause_ip, 0]      @@ @enc 7e3c0000
@@ OBJ: {{[0-9a-f]+:}} 7e 3c 00 01{{.*}}escape cfx_hart, [excp_cause_ip, 4]
@@ ASM: escape cfx_hart, [excp_cause_ip, 4]
escape cfx_hart, [excp_cause_ip, 4]      @@ @enc 7e3c0001

@@ --- cfx_umon（0）: 偏移 8 仍按帧选择位编码（汇编层只管 imms20） ---
@@ escape cfx_umon, [excp_cause_ip, 8] : imms18=2 -> 7e 00 00 02
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 02{{.*}}escape cfx_umon, [excp_cause_ip, 8]
@@ ASM: escape cfx_umon, [excp_cause_ip, 8]
escape cfx_umon, [excp_cause_ip, 8]      @@ @enc 7e000002

@@ 数字形 cfxHA 与标量别名等价（cfx15 ≡ cfx_hart）
@@ ASM: escape cfx_hart, [excp_cause_ip, 8]
escape cfx15, [excp_cause_ip, 8]         @@ @enc 7e3c0002
