# DADAO LLVM-tool lit suite

lit test location for **LLVM tool** tests (assembler / disassembler /
verification tooling), following the upstream LLVM `llvm/test/tools/`
component-first layout.

- **Status**: placeholder — no tests yet.  It is **not** wired into
  `make check-lit`.
- **Driver**: `lit.cfg.py` in this directory (`ShTest`, `.ll` suffix).
- **First test**: add tool substitutions (`%llvm_mc`, `%llvm_objdump`,
  `%FileCheck`, ...) and a build-tree `test_exec_root` to `lit.cfg.py`,
  mirroring `tests/llvm/lit/MC/DADAO/lit.cfg.py`.
