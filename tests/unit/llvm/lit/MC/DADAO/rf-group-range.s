@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ

@@ rf 寄存器组（`{start:end}`）越界编码的 MC 解码判据（ISS-468）。
@@
@@ contract-isa.md §15.1 / contract-fp.md §15 的 `mreg_zero` 与
@@ `mreg_range_overflow`：组内元素个数 `immu6 == 0`、或 `起始 + immu6 > 64`，都是
@@ ILLI（不环绕、不截断，源与目的起始寄存器都查）。`immu6` 是 6 位字段，因此这两种
@@ 就是全部可表达的非法组合。
@@
@@ 本用例钉住三件事：
@@  （1）9 个 `_rf.S` 镜像里触发崩溃的原始字 `0x3EDC304A`（`rf55 + 10 = rf64`）
@@      现在解码为 `<unknown>`，`llvm-objdump` 不再断言退出；
@@  （2）RD/RB/RA 组的同类越界（修复前静默打印成跨 bank 的
@@      `{rd61:rf0}` / `{rb61:rd0}` / `{ra61:rb0}`）一并被拒；
@@  （3）合法组（`{rf63}`、`{rf1:rf63}`、`{rf60:rf63}`、`{rf32:rf47}`）逐字不变，
@@      且同一字段位、count=9 的字仍解码为 `{rf55:rf63}`——拒绝的是越界组，不是
@@      整条指令；非组窗口的 orri（`ext.so`，第三操作数是移位量）不受影响。

@@ --- 合法：rf 组顶端，count=1（打印形态无 `:`） ---
@@ OBJ: {{[0-9a-f]+:}} 3e fc 34 c1{{.*}}ldm.o{{.*}}{rf63}, [rb3, rd19]
	ldm.o {rf63:rf63}, [rb3, rd19]

@@ --- 合法：整 bank 宽 {rf1:rf63}（1 + 63 = 64） ---
@@ OBJ: {{[0-9a-f]+:}} 3e 04 34 ff{{.*}}ldm.o{{.*}}{rf1:rf63}, [rb3, rd19]
	ldm.o {rf1:rf63}, [rb3, rd19]

@@ --- 合法：{rf60:rf63}（60 + 4 = 64，正好触到上界） ---
@@ OBJ: {{[0-9a-f]+:}} 3e f0 34 c4{{.*}}ldm.o{{.*}}{rf60:rf63}, [rb3, rd19]
	ldm.o {rf60:rf63}, [rb3, rd19]

@@ --- 合法：{rf32:rf47}（count=16） ---
@@ OBJ: {{[0-9a-f]+:}} 3e 80 34 d0{{.*}}ldm.o{{.*}}{rf32:rf47}, [rb3, rd19]
	ldm.o {rf32:rf47}, [rb3, rd19]

@@ --- 非法：rf55 + 10 = 65 > 64（ISS-468 触发字；tests/inst/01-load-store/
@@     ldm.o_rrri_rf.S 第 116 行的 TEST_FAULT_ENC 原始字） ---
@@ OBJ: {{[0-9a-f]+:}} 3e dc 30 4a{{.*}}<unknown>
	.dd.t32	0x3EDC304A

@@ --- 对照：同一字段位、count=9（55 + 9 = 64）是合法组 ---
@@ OBJ: {{[0-9a-f]+:}} 3e dc 34 c9{{.*}}ldm.o{{.*}}{rf55:rf63}, [rb3, rd19]
	.dd.t32	0x3EDC34C9

@@ --- 非法：rf63 + 2 = 65（顶端不环绕；同文件第 118 行） ---
@@ OBJ: {{[0-9a-f]+:}} 3e fc 30 42{{.*}}<unknown>
	.dd.t32	0x3EFC3042

@@ --- 非法：immu6 = 0（mreg_zero；同文件第 114 行） ---
@@ OBJ: {{[0-9a-f]+:}} 3e 14 30 40{{.*}}<unknown>
	.dd.t32	0x3E143040

@@ --- 非法：RD 组 61 + 4 > 64（修复前静默打印成 `{rd61:rf0}`） ---
@@ OBJ: {{[0-9a-f]+:}} 38 f4 34 c4{{.*}}<unknown>
	.dd.t32	0x38F434C4

@@ --- 非法：RB 组 61 + 4 > 64（修复前 `{rb61:rd0}`） ---
@@ OBJ: {{[0-9a-f]+:}} 3a f4 34 c4{{.*}}<unknown>
	.dd.t32	0x3AF434C4

@@ --- 非法：RA 组 61 + 4 > 64（修复前 `{ra61:rb0}`） ---
@@ OBJ: {{[0-9a-f]+:}} 3c f4 34 c4{{.*}}<unknown>
	.dd.t32	0x3CF434C4

@@ --- 合法：orri 同组块复制 rf2rf（两个窗口共享 immu6） ---
@@ OBJ: {{[0-9a-f]+:}} 40 f0 a3 83{{.*}}rf2rf{{.*}}{rf10:rf12}, {rf14:rf16}
	rf2rf {rf10:rf12}, {rf14:rf16}

@@ --- 合法：orri classify 双侧窗口（RD 目的 + RF 源） ---
@@ OBJ: {{[0-9a-f]+:}} 44 00 42 03{{.*}}ftcls{{.*}}{rd4:rd6}, {rf8:rf10}
	ftcls {rd4:rd6}, {rf8:rf10}

@@ --- 非法：orri classify 源窗口 rf61 + 4（tests/inst/07-floating-point/
@@     ftcls_orri_rf.S 第 61 行） ---
@@ OBJ: {{[0-9a-f]+:}} 44 01 4f 44{{.*}}<unknown>
	.dd.t32	0x44014F44

@@ --- 非法：orri classify 目的窗口 rd61 + 4（同文件第 60 行；修复前 `{rd61:rf0}`） ---
@@ OBJ: {{[0-9a-f]+:}} 44 03 da 04{{.*}}<unknown>
	.dd.t32	0x4403DA04

@@ --- 非组窗口的 orri 不受影响：ext.so 的第三操作数是移位量，不是元素个数 ---
@@ OBJ: {{[0-9a-f]+:}} 40 a7 df 4a{{.*}}ext.so{{.*}}rd61, rd61, 10
	ext.so rd61, rd61, 10
