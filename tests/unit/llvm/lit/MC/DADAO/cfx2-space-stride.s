@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
@@ RUN: cmp %t %t2
@@ RUN: echo '# format=1' > %t.v1
@@ RUN: echo 'scalar cfx_umon 0 canonical' >> %t.v1
@@ RUN: echo 'reg cfx_bar 0 7 0 16 canonical' >> %t.v1
@@ RUN: echo 'cfx2rd cfx_bar[5], rd1' | env DADAO_CFX_ALIAS_FILE=%t.v1 %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.v1.o
@@ RUN: env DADAO_CFX_ALIAS_FILE=%t.v1 %llvm_objdump -d --triple=dadao-unknown-elf %t.v1.o | %FileCheck %s --check-prefix=V1-OBJ
@@ RUN: echo '# format=2' > %t.v2
@@ RUN: echo 'scalar cfx_umon 0 canonical' >> %t.v2
@@ RUN: echo 'array cfx_foo_bar 0 7 0 16 4 canonical' >> %t.v2
@@ RUN: echo 'cfx2rd cfx_foo_bar[5], rd1' | env DADAO_CFX_ALIAS_FILE=%t.v2 %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.v2.o
@@ RUN: env DADAO_CFX_ALIAS_FILE=%t.v2 %llvm_objdump -d --triple=dadao-unknown-elf %t.v2.o | %FileCheck %s --check-prefix=V2-OBJ

@@ LLVM-141t：cfx 别名表 `format=2` 的 **stride 数组**（cg7 §3.8）：
@@   `array <name-base> <cfxha> <cg> <rc-base> <count> <stride>`，
@@   元素 N 的 rc = rc-base + N*stride。cg7 每 4 个 rc 一个空间块
@@   （i = 0..15，rc = 4i + K，K = 0..3 -> desc/start/size/attr）。
@@
@@ 本用例证四件事（**数据驱动**，同一二进制只换表文件）：
@@   1. 默认表：`cfx_<name>_space_*[N]` 可汇编，rc 按 stride 落值
@@      （[5] -> rc20、[15] -> rc60/61/62/63）；objdump 打印同名 +
@@      同一下标（说明 printer 用 (rc-rcBase)/stride 反算，而非 rc 原值）；
@@   2. 连续数组（`reg`，stride 1）不回归；
@@   3. 旧 `format=1` 表（`reg` 连续数组）仍可汇编/反汇编；
@@   4. `format=2` 改名 `array` 表立即可用（证明 stride 是表数据，非硬编码）。
@@
@@ `@enc` 由同目录 oracle（validate_cfx_vectors.py）从 opcodes.yaml +
@@ .tao/contracts/contract-cfx-aliases.md 独立派生：cfx2rd op=0x7A，
@@   crrr: cfxha[23:18] cghb[17:12] rchc[11:6] rdhd[5:0]。

@@ --- cg7 stride 数组：desc/start/size/attr，N=0/5/15 ---
@@ cfx2rd cfx_umon_space_desc[0] : (0, 7, 4*0+0), rd1 -> 7a 00 70 01
@@ OBJ: {{[0-9a-f]+:}} 7a 00 70 01{{.*}}cfx2rd cfx_umon_space_desc[0], rd1
@@ ASM: cfx2rd cfx_umon_space_desc[0], rd1
cfx2rd cfx_umon_space_desc[0], rd1      @@ @enc 7a007001

@@ cfx2rd cfx_umon_space_desc[5] : (0, 7, 4*5+0=20), rd1 -> 7a 00 75 01
@@ OBJ: {{[0-9a-f]+:}} 7a 00 75 01{{.*}}cfx2rd cfx_umon_space_desc[5], rd1
@@ ASM: cfx2rd cfx_umon_space_desc[5], rd1
cfx2rd cfx_umon_space_desc[5], rd1      @@ @enc 7a007501

@@ cfx2rd cfx_umon_space_size[15] : (0, 7, 4*15+2=62), rd1 -> 7a 00 7f 81
@@ OBJ: {{[0-9a-f]+:}} 7a 00 7f 81{{.*}}cfx2rd cfx_umon_space_size[15], rd1
@@ ASM: cfx2rd cfx_umon_space_size[15], rd1
cfx2rd cfx_umon_space_size[15], rd1     @@ @enc 7a007f81

@@ cfx2rd cfx_umon_space_attr[15] : (0, 7, 4*15+3=63), rd1 -> 7a 00 7f c1
@@ OBJ: {{[0-9a-f]+:}} 7a 00 7f c1{{.*}}cfx2rd cfx_umon_space_attr[15], rd1
@@ ASM: cfx2rd cfx_umon_space_attr[15], rd1
cfx2rd cfx_umon_space_attr[15], rd1     @@ @enc 7a007fc1

@@ --- 连续数组（`reg`，stride 1）不回归 ---
@@ cfx_umon_scratch_regs[3] : (0, 6, 3), rd1 -> 7a 00 60 c1
@@ OBJ: {{[0-9a-f]+:}} 7a 00 60 c1{{.*}}cfx2rd cfx_umon_scratch_regs[3], rd1
@@ ASM: cfx2rd cfx_umon_scratch_regs[3], rd1
cfx2rd cfx_umon_scratch_regs[3], rd1    @@ @enc 7a0060c1

@@ cfx_pmem_start[3] : cfxha=17, cg=12, rc=3 -> 7a 44 c0 c1
@@ OBJ: {{[0-9a-f]+:}} 7a 44 c0 c1{{.*}}cfx2rd cfx_pmem_start[3], rd1
@@ ASM: cfx2rd cfx_pmem_start[3], rd1
cfx2rd cfx_pmem_start[3], rd1           @@ @enc 7a44c0c1

@@ --- format=1 兼容：临时 `reg` 表（stride 1），[5] -> rc5 ---
@@ V1-OBJ: cfx2rd cfx_bar[5], rd1

@@ --- format=2 数据驱动：临时 `array` 表，[5] -> rc20 ---
@@ V2-OBJ: cfx2rd cfx_foo_bar[5], rd1
