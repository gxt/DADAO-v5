# RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

# Verify that wp4 is rejected as invalid wyde-position.
set.zw rb1, wp4, 0xffff

# CHECK: error: invalid wyde-position; expected wp0, wp1, wp2, or wp3
