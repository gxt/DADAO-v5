# RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

# Verify that non-wp identifier is rejected as invalid wydepos.
set.zw rb1, foo, 0xffff

# CHECK: error: invalid operand for instruction
