@@ RUN: echo 'cfx2rd cfx_umon_space_desc[16], rd1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
@@ RUN: echo 'cfx2rd cfx_umon_space_desc, rd1'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SUBSCRIPT
@@ RUN: echo 'cfx2rd cfx_umon_space_size[16], rd1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE

@@ LLVM-141t 反例：cg7 stride 数组（format=2）的下标 MUST 落在
@@ [0, count-1] = [0, 15]；无下标 MUST 硬报错（single subscript required）。
@@ `count` 判定与 stride 无关（越界按元素个数，不按 rc 跨度）。

@@ RANGE: out of range [0, 15]
@@ SUBSCRIPT: single subscript is required
