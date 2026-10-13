; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
; RUN: cmp %t %t2

; LLVM-060t L1 向量：trap / escape（ciii）+ cfx2rd / cfx2rc（crrr）。
;
; 编码**独立派生**自 contracts/opcodes.yaml（禁从 llvm-mc 反推；见同目录
; validate_cfx_vectors.py）：trap op=0x7F、escape op=0x7E、cfx2rd op=0x7A、
; cfx2rc op=0x7B，均 mask=0xFF000000。字段：
;   crrr  : cfxha[23:18] cghb[17:12] rchc[11:6] rdhd[5:0]
;   ciii  : cfxha[23:18] imm18[17:0]
; cfx 写法 `cfx<ha>`（0..63）与 `cfx_<cfxname>`（contract-cfx-aliases）等价；
; cfx2rd/cfx2rc 的 `cfx_<cfxname>_<regname>` 简写展开为 `cfxHA, cgHB, rcHC`。
; escape 汇编层 `imms20`（字节，须 %4==0）⇔ 编码 `imms18 = bytes >> 2`
; （Toolchain-01 §3.2；反汇编还原 `<<2`）。
;
; `@enc` 为独立派生的期望编码；同目录 oracle 从 opcodes.yaml + 别名表重算并比对。

; --- trap（ciii）：cfxha + immu18 ---
; trap cfx_smon, 1 : cfxha=2, imm18=1 -> 7f 08 00 01
; OBJ: {{[0-9a-f]+:}} 7f 08 00 01{{.*}}trap{{.*}}1
; ASM: trap cfx2, 1
trap cfx_smon, 1                        ; @enc 7f080001

; trap cfx63, 0 : cfxha=63, imm18=0 -> 7f fc 00 00
; OBJ: {{[0-9a-f]+:}} 7f fc 00 00{{.*}}trap{{.*}}0
; ASM: trap cfx63, 0
trap cfx63, 0                           ; @enc 7ffc0000

; --- escape（ciii）：cfxha + [excp_cause_ip, imms20]（字节偏移 >>2） ---
; escape cfx_umon, [excp_cause_ip, 4] : cfxha=0, imms18=1 -> 7e 00 00 01
; OBJ: {{[0-9a-f]+:}} 7e 00 00 01{{.*}}escape{{.*}}4
; ASM: escape cfx0, [excp_cause_ip, 4]
escape cfx_umon, [excp_cause_ip, 4]     ; @enc 7e000001

; escape cfx0, [excp_cause_ip, 8] : imms18=2 -> 7e 00 00 02
; OBJ: {{[0-9a-f]+:}} 7e 00 00 02{{.*}}escape{{.*}}8
; ASM: escape cfx0, [excp_cause_ip, 8]
escape cfx0, [excp_cause_ip, 8]         ; @enc 7e000002

; escape cfx0, [excp_cause_ip, -8] : 负偏移 -8>>2=-2 -> imms18=0x3FFFE -> 7e 03 ff fe
; OBJ: {{[0-9a-f]+:}} 7e 03 ff fe{{.*}}escape{{.*}}-8
; ASM: escape cfx0, [excp_cause_ip, -8]
escape cfx0, [excp_cause_ip, -8]        ; @enc 7e03fffe

; --- cfx2rd（crrr）：cfx_<cfxname>_<regname> 简写 ---
; cfx2rd cfx_umon_excp_cause_ip, rd2 : (cfxha=0, cg=5, rc=3), rd=2
;   -> 0x7A | 0<<18 | 5<<12 | 3<<6 | 2 = 7a 00 50 c2
; OBJ: {{[0-9a-f]+:}} 7a 00 50 c2{{.*}}cfx2rd{{.*}}cfx0
; ASM: cfx2rd cfx0, cg5, rc3, rd2
cfx2rd cfx_umon_excp_cause_ip, rd2      ; @enc 7a0050c2

; 等价规范长形（cfx_umon, cg5, rc3 -> 同一元组）
cfx2rd cfx_umon, cg5, rc3, rd2          ; @enc 7a0050c2

; --- cfx2rc（crrr）：cfx_<cfxname>_<regname> 简写 ---
; cfx2rc cfx_power_ctrl, rd2 : (cfxha=63, cg=8, rc=1), rd=2
;   -> 0x7B | 63<<18 | 8<<12 | 1<<6 | 2 = 7b fc 80 42
; OBJ: {{[0-9a-f]+:}} 7b fc 80 42{{.*}}cfx2rc{{.*}}cfx63
; ASM: cfx2rc cfx63, cg8, rc1, rd2
cfx2rc cfx_power_ctrl, rd2              ; @enc 7bfc8042

; 等价规范长形
cfx2rc cfx_power, cg8, rc1, rd2         ; @enc 7bfc8042

; --- 数组寄存器单下标（ADR-0017 D10） ---
; cfx2rd cfx_ptw_ptbr[3], rd2 : (cfxha=4, cg=9, rc=0+3), rd=2 -> 7a 10 90 c2
; OBJ: {{[0-9a-f]+:}} 7a 10 90 c2{{.*}}cfx2rd{{.*}}cfx4
; ASM: cfx2rd cfx4, cg9, rc3, rd2
cfx2rd cfx_ptw_ptbr[3], rd2             ; @enc 7a1090c2

; cfx2rd cfx_timer_regs[2], rd2 : (cfxha=18, cg=10, rc=8+2), rd=2 -> 7a 48 a2 82
; OBJ: {{[0-9a-f]+:}} 7a 48 a2 82{{.*}}cfx2rd{{.*}}cfx18
; ASM: cfx2rd cfx18, cg10, rc10, rd2
cfx2rd cfx_timer_regs[2], rd2           ; @enc 7a48a282

; --- 标量别名等价（`cfx_<name>` ⇔ `cfx<ha>`；acceptance 3）---
; cfx_power ≡ cfx63 (cfxha=63)
trap cfx_power, 0                       ; @enc 7ffc0000
; cfx_umon ≡ cfx0 (cfxha=0)
trap cfx_umon, 0                        ; @enc 7f000000
trap cfx0, 0                            ; @enc 7f000000
