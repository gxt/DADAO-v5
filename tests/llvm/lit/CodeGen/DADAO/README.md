# DADAO CodeGen lit suite (L2 structural)

lit test location for **CodeGen L2 structural** tests (`llc` output checked
with `FileCheck`), following the upstream LLVM `llvm/test/CodeGen/`
component-first layout.

- **Status**: placeholder — no tests yet.  It is **not** wired into
  `make check-lit` (that gate runs `tests/llvm/lit/MC/DADAO` and
  `tests/e2e/lit`).
- **Driver**: `lit.cfg.py` in this directory (`ShTest`, `.ll` suffix).
- **First test**: add tool substitutions (`%llc`, `%FileCheck`, ...) and a
  build-tree `test_exec_root` to `lit.cfg.py`, mirroring
  `tests/llvm/lit/MC/DADAO/lit.cfg.py`, then wire the suite into the relevant
  gate.
