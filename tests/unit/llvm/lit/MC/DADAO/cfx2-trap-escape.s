@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
@@ RUN: cmp %t %t2

@@ LLVM-060t L1 向量：trap / escape（ciii）+ cfx2rd / cfx2rc（crrr）。
@@
@@ 编码**独立派生**自 contracts/opcodes.yaml（禁从 llvm-mc 反推；见同目录
@@ validate_cfx_vectors.py）：trap op=0x7F、escape op=0x7E、cfx2rd op=0x7A、
@@ cfx2rc op=0x7B，均 mask=0xFF000000。字段：
@@   crrr  : cfxha[23:18] cghb[17:12] rchc[11:6] rdhd[5:0]
@@   ciii  : cfxha[23:18] imm18[17:0]
@@ cfx 写法 `cfx<ha>`（0..63）与 `cfx_<cfxname>`（contract-cfx-aliases）等价；
@@ cfx2rd/cfx2rc 的 `cfx_<cfxname>_<regname>` 简写展开为 `cfxHA, cgHB, rcHC`；
@@ 反汇编优先打印**名字**（运行时表 contracts/cfx-aliases.txt；LLVM-135t），
@@ 无名字（reserved cfx / 未知 cg-rc 组合）回退 `cfx<HA>, cgN, rcN`。
@@ `escape` 汇编格式为 `escape cfxHA`（m18-spec-007）：只提供 cfxha，
@@ 机器码 `imms18` 是 SBZ 必须为 0（contracts/opcodes.yaml
@@ `escape_ciii_cfx` legality `imms18 == 0`）；反汇编只回显 cfxHA，
@@ 不再打印偏移/帧选择（旧的 0/4/8 偏移与 cg9 帧选择位已作废）。
@@
@@ `@enc` 为独立派生的期望编码；同目录 oracle 从 opcodes.yaml + 别名表重算并比对。

@@ --- trap（ciii）：cfxha + immu18 ---
@@ trap cfx_smon, 1 : cfxha=2, imm18=1 -> 7f 08 00 01
@@ OBJ: {{[0-9a-f]+:}} 7f 08 00 01{{.*}}trap cfx_smon, 1
@@ ASM: trap cfx_smon, 1
trap cfx_smon, 1                        @@ @enc 7f080001

@@ trap cfx63, 0 : cfxha=63, imm18=0 -> 7f fc 00 00
@@ OBJ: {{[0-9a-f]+:}} 7f fc 00 00{{.*}}trap cfx_power, 0
@@ ASM: trap cfx_power, 0
trap cfx63, 0                           @@ @enc 7ffc0000

@@ --- escape（ciii）：cfxha（imms18 = 0，SBZ） ---
@@ escape cfx_umon : cfxha=0, imms18=0 -> 7e 00 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 00{{.*}}escape cfx_umon
@@ ASM: escape cfx_umon
escape cfx_umon                         @@ @enc 7e000000

@@ escape cfx0 : 数字形等价（imms18 = 0）
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 00{{.*}}escape cfx_umon
@@ ASM: escape cfx_umon
escape cfx0                             @@ @enc 7e000000

@@ escape cfx_power : cfxha=63, imms18=0 -> 7e fc 00 00
@@ OBJ: {{[0-9a-f]+:}} 7e fc 00 00{{.*}}escape cfx_power
@@ ASM: escape cfx_power
escape cfx_power                        @@ @enc 7efc0000

@@ --- escape imms18 != 0：手工编码是架构 ILLI，解码为 <unknown> ---
@@ SimRISC-11 §3 / DADAO-12 §5.1：imms18 是 SBZ，非 0 ⇒ ILLI
@@ （contracts/legality_rules.yaml `encode_sbz`）。汇编器无法生成该形态
@@ （见 cfx2-escape-frame-err.s），这里用原始字钉住 MC 解码判据。
@@ word = 0x7E000000 | imms18
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 01{{.*}}<unknown>
	.dd.t32 0x7E000001
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 02{{.*}}<unknown>
	.dd.t32 0x7E000002
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 03{{.*}}<unknown>
	.dd.t32 0x7E000003
@@ OBJ: {{[0-9a-f]+:}} 7e 00 00 04{{.*}}<unknown>
	.dd.t32 0x7E000004
@@ OBJ: {{[0-9a-f]+:}} 7e ff ff ff{{.*}}<unknown>
	.dd.t32 0x7EFFFFFF

@@ --- cfx2rd（crrr）：cfx_<cfxname>_<regname> 简写 ---
@@ cfx2rd cfx_umon_excp_cause_ip, rd2 : (cfxha=0, cg=5, rc=2), rd=2
@@   -> 0x7A | 0<<18 | 5<<12 | 2<<6 | 2 = 7a 00 50 82
@@ OBJ: {{[0-9a-f]+:}} 7a 00 50 82{{.*}}cfx2rd cfx_umon_excp_cause_ip, rd2
@@ ASM: cfx2rd cfx_umon_excp_cause_ip, rd2
cfx2rd cfx_umon_excp_cause_ip, rd2      @@ @enc 7a005082

@@ 等价规范长形（cfx_umon, cg5, rc2 -> 同一元组）
cfx2rd cfx_umon, cg5, rc2, rd2          @@ @enc 7a005082

@@ --- cfx2rc（crrr）：cfx_<cfxname>_<regname> 简写 ---
@@ cfx2rc cfx_power_ctrl, rd2 : (cfxha=63, cg=8, rc=1), rd=2
@@   -> 0x7B | 63<<18 | 8<<12 | 1<<6 | 2 = 7b fc 80 42
@@ OBJ: {{[0-9a-f]+:}} 7b fc 80 42{{.*}}cfx2rc cfx_power_ctrl, rd2
@@ ASM: cfx2rc cfx_power_ctrl, rd2
cfx2rc cfx_power_ctrl, rd2              @@ @enc 7bfc8042

@@ 等价规范长形
cfx2rc cfx_power, cg8, rc1, rd2         @@ @enc 7bfc8042

@@ --- 数组寄存器单下标（ADR-0017 D10） ---
@@ cfx2rd cfx_ptw_ptbr, rd2 : (cfxha=4, cg=9, rc=0), rd=2 -> 7a 10 90 02
@@ OBJ: {{[0-9a-f]+:}} 7a 10 90 02{{.*}}cfx2rd cfx_ptw_ptbr, rd2
@@ ASM: cfx2rd cfx_ptw_ptbr, rd2
cfx2rd cfx_ptw_ptbr, rd2                @@ @enc 7a109002

@@ cfx2rd cfx_time_value, rd2 : (cfxha=34, cg=10, rc=1), rd=2 -> 7a 88 a0 42
@@ OBJ: {{[0-9a-f]+:}} 7a 88 a0 42{{.*}}cfx2rd cfx_time_value, rd2
@@ ASM: cfx2rd cfx_time_value, rd2
cfx2rd cfx_time_value, rd2             @@ @enc 7a88a042

@@ --- 标量别名等价（`cfx_<name>` ⇔ `cfx<ha>`；acceptance 3）---
@@ cfx_power ≡ cfx63 (cfxha=63)
trap cfx_power, 0                       @@ @enc 7ffc0000
@@ cfx_umon ≡ cfx0 (cfxha=0)
trap cfx_umon, 0                        @@ @enc 7f000000
trap cfx0, 0                            @@ @enc 7f000000

@@ --- reserved / 未知组合：反汇编裸回退 `cfx<HA>, cgN, rcN`（LLVM-135t）---
@@ trap cfx20, 0 : cfxha=20（16-31 reserved，无名字）-> 0x7F | 20<<18 = 7f 50 00 00
@@ OBJ: {{[0-9a-f]+:}} 7f 50 00 00{{.*}}trap cfx20, 0
@@ ASM: trap cfx20, 0
trap cfx20, 0                           @@ @enc 7f500000

@@ cfx2rd cfx_umon, cg8, rc0, rd2 : (0, 8, 0) 无名字（cfx0-3 只定义 cg8 rc1）
@@   -> 0x7A | 0<<18 | 8<<12 | 0<<6 | 2 = 7a 00 80 02
@@ OBJ: {{[0-9a-f]+:}} 7a 00 80 02{{.*}}cfx2rd cfx0, cg8, rc0, rd2
@@ ASM: cfx2rd cfx0, cg8, rc0, rd2
cfx2rd cfx_umon, cg8, rc0, rd2          @@ @enc 7a008002
