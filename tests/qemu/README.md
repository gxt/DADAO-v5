# QEMU component tests / fixtures

Location for QEMU-component tests and fixtures (e.g. unit/probe harnesses and
their input binaries), following the component-first `tests/` layout.

- **Status**: placeholder — no contents yet.
- Grep-based ISA semantic vectors live in `tests/inst/base/`; the shared
  QEMU harness lives in `tools/testcases/lib/` (`run_qemu_test.py`,
  `build_test_binary.py`; `tests/scripts/` 留薄 wrapper).
- min-ROM 场景探针（`min_rom_probe_*`）已迁 `tools/testcases/arch/`（`TESTCASES-073t`）。
