# m13-004 riscv-tests 移植摘要

- **上游**：`riscv-software-src/riscv-tests` commit `0494f954a3d8d2ca9e4972da7a01e94b6a909bce`（RV64 六套件 114 文件）。
- **分类**：移植 35 / 需改 57 / 不适用 22；逐条名字与理由见 `tests/riscv-tests/inventory.yaml`。
- **移植语料**：35 文件 / 474 条值用例，存 `tests/riscv-tests/cases/`。
- **差分**：QEMU system 与 gem5 FS 均 `AGREE_PASS` 35/35，逐例签名一致；`DIFF` 0。
- **chipyard 列**：`N/A`；核实现 `m12-chipyard-008/009/010/011–015` 仍待开始。
- **详细报告**：`docs/TestReports/M13-riscv-tests移植与差分.md`。
- **逐例摘要**：`refs/m13-004-riscv-tests.json`（原始逐例 JSON 不入库）。
