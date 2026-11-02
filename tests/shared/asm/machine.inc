@@ machine.inc — DADAO-v5 assembly helper for profile-selected test geometry.
@@
@@ TESTCASES-091t: test/bootrom sources must not embed Machine-v5 addresses.
@@ Callers either include a generated machine-<profile>.inc (bootrom sources,
@@ built directly by the Makefile) or pass the symbols with llvm-mc --defsym
@@ (arch vectors, driven by run_m5_e2e.py).  Values are plain integers without
@@ hex underscores because the DADAO assembler rejects them.

.macro LOAD_ADDR rb, addr
  set.zw  \rb, wp0, ((\addr) & 0xFFFF)
  or.w    \rb, wp1, (((\addr) >> 16) & 0xFFFF)
  or.w    \rb, wp2, (((\addr) >> 32) & 0xFFFF)
  or.w    \rb, wp3, (((\addr) >> 48) & 0xFFFF)
.endm
