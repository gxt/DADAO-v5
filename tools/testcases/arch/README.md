# `tools/testcases/arch/` — arch scope 执行驱动（TESTCASES-073t）

`docs/Process-09 §6`：**runner/driver 全部收拢到 `tools/testcases/`**，`tests/` 只放用例与
`shared/`。本目录是 arch scope 的驱动与 min-ROM 场景（原 `tools/integ/` /
`tools/qemu/`）：

| 文件 | 作用 | 旧路径（薄 wrapper，`TESTCASES-076t` 删除） |
|------|------|------|
| `run_m5_e2e.py` | SEE/semihosting + cfx 权限端到端驱动（llvm-mc → objcopy → qemu + bootrom；`--inject` 自检） | `tools/integ/run_m5_e2e.py` |
| `min_rom_probe_*.py` / `.sh` | min-ROM 场景探针（各自内嵌 ROM 程序 + `-d cpu` 观测；期望值手推自 `spec/`+`contracts/`） | `tools/qemu/min_rom_probe_*` |

- 用例**资产**（`.s` 向量 + `expected.yaml`）在 `tests/arch/<cfx>/`；本目录只放驱动，
  不放用例数据。
- 门控：`make check-arch-smoke`（L2）/ `make check-arch`（L3）。
- 旧路径的 wrapper 一律 `runpy` / `exec` 转发，命令行与退出码等价；**不含实现**。
- 探针的 QEMU 默认值是 `.work/build/qemu/qemu-system-dadao`（历史约定，M1–M6 期）；
  `044t/045t/046t/047t/049t/061t` 接受 `--qemu`，门控 `check-arch` 从安装根传入
  （ADR-0016 D9）。其余探针（005t…042t、070t…074t）无 `--qemu`，且未纳入门控
  （部分期望值已与现行 spec 漂移，见 `TESTCASES-073t` 遗留）。
