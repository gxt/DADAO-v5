@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: echo 'ra2rd {rd63:rf61}, {ra63:rb61}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-BANK
@@ RUN: echo 'ldm.o {rd63:rf61}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-BANK
@@ RUN: echo 'ldm.o {ra63:rb61}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-BANK
@@ RUN: echo 'ldm.o {rb63:ra61}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-BANK
@@ RUN: echo 'ldm.t {rf63:ra0}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-BANK
@@ RUN: echo 'ldm.o {rd0:rd63}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
@@ RUN: echo 'rd2rd {rd0:rd63}, {rd8:rd12}' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-CNT
@@ RUN: echo 'ldm.o {rd5:rd3}, [rb1, rd0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-ORDER

@@ 汇编期的寄存器组 bank 判据（ISS-m20-001；m20-llvm-002）。
@@
@@ contract-isa.md §15.1 / contract-fp.md §15 的 `mreg_range_overflow`：多寄存器组的
@@ `{start:end}` 必须是**同一寄存器组**内的连续寄存器，且 `起始 + 个数 > 64` 即
@@ ILLI（不环绕、不截断）。汇编器的 `parseRegGroup` 旧实现用**寄存器枚举 id 差值**
@@ 推个数：枚举里 RD 的 64 个寄存器之后紧跟 RF，`{rd63:rf61}` 因此被算成 63 个元素、
@@ 绕过 `mreg_range_overflow`，`ra2rd {rd63:rf61}, {ra63:rb61}` 被汇编成
@@ `0x40BBFFFF`（起始 63 + 63 = 126 > 64）。现在改按**组文本所在 bank** 判：起始与
@@ 结束寄存器必须同 bank、个数由 bank 内的硬件编码（每 bank 0..63）计算。
@@
@@ 本用例钉住：
@@  （1）RD→RF、RA→RB 两类**修复前会被接受**的跨 bank 组（`ra2rd` 两侧、`ldm.o`
@@      单侧）现在硬报错，诊断含 `mreg_range_overflow`；
@@  （2）RB/RF 起始的跨 bank 组（修复前即报 `end < start`/`range too large`，
@@      但不是 bank 判据）现在同样给出统一诊断；
@@  （3）同 bank 的起始 + 个数越界（count 64 的 `{rd0:rd63}`）仍被拒
@@      （`mreg_range_overflow`，6 位 immu6 装不下 64）；
@@  （4）`end < start` 的组仍按原诊断报错；
@@  （5）合法边界组（`{rf63}`、`{rf1:rf63}`、`{rf32:rf47}`、`{rd0:rd62}`、
@@      `ra2rd {rd1:rd3}, {ra2:ra4}`）逐字节编码不变——修的是非法组，不是合法组。
@@
@@ --- 合法边界：单寄存器组（打印形态无 `:`） ---
@@ OBJ: {{[0-9a-f]+:}} 3e fc 34 c1{{.*}}ldm.o{{.*}}{rf63}, [rb3, rd19]
	ldm.o {rf63:rf63}, [rb3, rd19]

@@ --- 合法边界：{rf1:rf63}（1 + 63 = 64，正好触到上界） ---
@@ OBJ: {{[0-9a-f]+:}} 3e 04 34 ff{{.*}}ldm.o{{.*}}{rf1:rf63}, [rb3, rd19]
	ldm.o {rf1:rf63}, [rb3, rd19]

@@ --- 合法边界：{rf32:rf47}（count=16） ---
@@ OBJ: {{[0-9a-f]+:}} 3e 80 34 d0{{.*}}ldm.o{{.*}}{rf32:rf47}, [rb3, rd19]
	ldm.o {rf32:rf47}, [rb3, rd19]

@@ --- 合法边界：{rd0:rd62}（count=63，6 位 immu6 的最大合法值） ---
@@ OBJ: {{[0-9a-f]+:}} 38 00 10 3f{{.*}}ldm.o{{.*}}{rd0:rd62}, [rb1, rd0]
	ldm.o {rd0:rd62}, [rb1, rd0]

@@ --- 合法边界：同 bank 组复制 ra2rd（两侧各 3 个） ---
@@ OBJ: {{[0-9a-f]+:}} 40 b8 10 83{{.*}}ra2rd{{.*}}{rd1:rd3}, {ra2:ra4}
	ra2rd {rd1:rd3}, {ra2:ra4}

@@ 跨 bank 负例（上面 5 条 echo-piped RUN 共用本前缀；每条输入恰好一条诊断，
@@ 因为 parseRegGroup 在第一个非法组处即报错返回）：
@@   ra2rd {rd63:rf61}, {ra63:rb61}  -> 目的组 RD→RF（修复前被接受，0x40BBFFFF）
@@   ldm.o {rd63:rf61}, [rb1, rd0]   -> RD→RF（修复前被接受，0x38FC103F）
@@   ldm.o {ra63:rb61}, [rb1, rd0]   -> RA→RB（修复前被接受，0x3CFC103F）
@@   ldm.o {rb63:ra61}, [rb1, rd0]   -> RB→RA（修复前报 end < start）
@@   ldm.t {rf63:ra0}, [rb1, rd0]    -> RF→RA（修复前报 range too large）
@@ ERR-BANK: error: invalid register range (mreg_range_overflow): the start and end registers are in different register banks; a register group must stay within one bank

@@ 同 bank 起始 + 个数越界（count 64 > 6 位 immu6 上界 63；两条 RUN 共用本前缀）：
@@   ldm.o {rd0:rd63}, [rb1, rd0]    -> 多寄存器存取的组
@@   rd2rd {rd0:rd63}, {rd8:rd12}    -> 块复制（两侧共享 immu6）
@@ ERR-CNT: error: invalid '{{[a-z0-9.]+}}': register range too long (mreg_range_overflow); element count must be 1..63

@@ 非法：end < start（个数不可为 0 或负；文本无法表达 mreg_zero） ---
@@ ERR-ORDER: error: invalid register range: end < start
