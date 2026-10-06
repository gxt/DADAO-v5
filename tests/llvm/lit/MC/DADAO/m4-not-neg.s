; UNSUPPORTED: true
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
; RUN: cmp %t %t2

; M4 L1 向量：`not`/`neg` 功能的**底层真实指令**（TESTCASES-032t）。
; 决策源 = `ADR-0013 D11`（2026-10-06）：`not.{b,w,t,o}`/`neg.{b,w,t,o}` 已删，
; 需要功能时直接书写真实指令：
;   * `not`（64 位按位取反）  → `xnor.o rd, rc, rd0`
;       （`contract-isa §6.3`：`xnor` 相同为一、相异为零；当一源为 `rd0` 时实现另一源取反）
;   * `neg`（8/16/32 位取负） → `sub.sb/sw/st rd, rd0, rc`（源 `rd0` 减 `rc`，结果符号扩展）
;       （`contract-isa §10.6/§11.6/§12.6`）
;   * `neg`（64 位取负）      → `sub.so {rd0, rd}, rd0, rc`（双目的 `rdha:rdhb = rdhc − rdhd`）
;       （`contract-isa §6.6`）
; 已删的窄位宽逻辑 `xnor.b/w/t`（`SPEC-069t`）**无**对应用户指令，故 `not` **仅** 64 位。
;
; 下方 `OBJ` 字节行的 4 字节（大端）由 `tools/testcases/validate_mc_vectors.py`
; **独立派生自** `contracts/opcodes.yaml`（`xnor.o_orrr_rd`=0x402C0000 /
; `sub.sb_orrr_rd`=0x43A40000 / `sub.sw_orrr_rd`=0x42A40000 /
; `sub.st_orrr_rd`=0x41A40000 / `sub.so_rrrr_rd`=0x53000000），**不调用** `llvm-mc`。
; 本向量暂不接入门控（首行标记）；由 INTEG-016t 移除。
;
; @category roundtrip

; --- not（仅 64 位）：xnor.o rd, rc, rd0 ---
; op=0x40, ha=0x0B(xnor.o), hb=rd8=8, hc=rd9=9, hd=rd0=0
; OBJ: {{[0-9a-f]+:}} 40 2c 82 40{{.*}}xnor.o{{.*}}rd8, rd9, rd0
; ASM: xnor.o rd8, rd9, rd0
xnor.o rd8, rd9, rd0                 ; @enc 402c8240

; --- neg（8/16/32 位）：sub.sb/sw/st rd, rd0, rc ---
; op=0x43/0x42/0x41, ha=0x29, hb=rd8=8, hc=rd0=0, hd=rd9=9
; OBJ: {{[0-9a-f]+:}} 43 a4 80 09{{.*}}sub.sb{{.*}}rd8, rd0, rd9
; ASM: sub.sb rd8, rd0, rd9
sub.sb rd8, rd0, rd9                 ; @enc 43a48009
; OBJ: {{[0-9a-f]+:}} 42 a4 80 09{{.*}}sub.sw{{.*}}rd8, rd0, rd9
; ASM: sub.sw rd8, rd0, rd9
sub.sw rd8, rd0, rd9                 ; @enc 42a48009
; OBJ: {{[0-9a-f]+:}} 41 a4 80 09{{.*}}sub.st{{.*}}rd8, rd0, rd9
; ASM: sub.st rd8, rd0, rd9
sub.st rd8, rd0, rd9                 ; @enc 41a48009

; --- neg（64 位双目的）：sub.so {rd0, rd}, rd0, rc ---
; op=0x53, rdha=rd0=0, rdhb=rd8=8, rdhc=rd0=0, rdhd=rd9=9
; OBJ: {{[0-9a-f]+:}} 53 00 80 09{{.*}}sub.so{{.*}}{rd0, rd8}, rd0, rd9
; ASM: sub.so {rd0, rd8}, rd0, rd9
sub.so {rd0, rd8}, rd0, rd9          ; @enc 53008009

; --- 往返规范化（§10）：等价书写必派生出同一编码 ---
xnor.o rd8, rd9, rd0                 ; @norm xnor.o  rd8,rd9,rd0
sub.sb rd8, rd0, rd9                 ; @norm sub.sb rd8,rd0,rd9
sub.so {rd0, rd8}, rd0, rd9          ; @norm sub.so {rd0,rd8},rd0,rd9
