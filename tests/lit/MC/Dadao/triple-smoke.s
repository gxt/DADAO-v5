# RUN: %llvm_mc --version > %t.out
# RUN: %FileCheck --check-prefix=CHECK-VERSION --input-file=%t.out %s

# Verify that the DADAO target is registered in llvm-mc --version.
# This is the degraded-path smoke test (AsmParser not yet implemented).
# Full assembly tests will be added when LLVM-006t introduces the AsmParser.

# CHECK-VERSION: dadao - DADAO SimRISC
