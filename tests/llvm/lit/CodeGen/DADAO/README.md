# DADAO CodeGen lit suite (L2 structural)

lit test location for **CodeGen L2 structural** tests (`llc` output checked
with `FileCheck`), following the upstream LLVM `llvm/test/CodeGen/`
component-first layout.

- **Status**: wired into `make check-lit` (INTEG-016t, which also resolves
  ISS-152). The suite holds the LLVM-059t branch-analysis vectors.
- **Vectors**: `branch-fold-insert.ll` (IR -> `llc -stop-after=branch-folder`)
  and `branch-fold-two-way.mir` (MIR -> `llc -run-pass=branch-folder`); both
  cover `DADAOInstrInfo::{analyzeBranch,insertBranch,removeBranch}`
  (`ISS-158`).
- **Driver**: `lit.cfg.py` in this directory (`ShTest`, suffixes `.ll`/`.mir`,
  `%llc`/`%FileCheck`/`%not` substitutions, build-tree `test_exec_root`),
  mirroring `tests/llvm/lit/MC/DADAO/lit.cfg.py`.
