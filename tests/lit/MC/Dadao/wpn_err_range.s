# RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

# Verify that numeric wyde-position out of range (4) is rejected.
set.zw rb1, 4, 0xffff

# CHECK: error: invalid operand for instruction
