# arch scope — cfx 资源管理与权限控制用例（`tests/arch/`）

本目录是 **arch scope**（`docs/Process-09` §3/§5）：测 **cfx 资源管理与权限控制**
（trap/escape/cfx2rd/cfx2rc、inner/global/switch/instruction 掩码、异常 cause、
per-hart/per-system、TIMER/IPI/UART/power），只跑 **`system`** 平台
（`qemu-system-dadao` + SEE bootrom）。

> `TESTCASES-073t`（2026-10-27）落第一批用例（P3 arch 迁移）：`tests/unit/llvm/codegen/m5/`
> → `arch/umon/`。执行驱动在 `tools/testcases/arch/`（`run_m5_e2e.py` +
> `min_rom_probe_*.py`，由集成驱动目录在 P3 迁入）。

## 目录（按 cfx 划分，`<cfx>` 取自 `spec/DADAO-12 §3` 的 cfx 名）

| 目录 | cfx | 内容 |
|------|-----|------|
| `umon/` | `cfx_umon`（user monitor） | SEE/semihosting 执行向量 + cfx 级权限反例（`m5_*.s`，10 条）+ `expected.yaml` 清单 |
| `hmon/` | `cfx3 hmon` + `cfx_power`（Tiny） | `tiny_hmon.S`（gem5 Tiny FS 应用：power→hmon 移交帧、五类同步异常、IALIGN IP 停留、`trap` 两路、`cfx2rd`/`cfx2rc`、Tiny 恒 `hypv` 与 `cg3` 仅 hypv 可读、`cg3 rc10` 掩低 2 位）+ `tiny_hmon_handler.S`（分派 hmon 段，编入 BootROM 镜像）+ `tiny_hmon_layout.inc`（共享 SRAM 布局）+ `expected.yaml`；装载按 `Machine-v5 §6.2` 两件（固定 64 KiB BootROM + 仅 SRAM 的应用 ELF） |

其余 cfx（`jmon`/`smon`/`ptw`/`cache`/`hart`/`llc`/`pmem`/`time`/`uart`）按需增建；**不建** `arch/isa`、空壳子目录。`hmon/` 的 Tiny 用例由 gem5 运行（`python3 tools/gem5/check_tiny_hmon.py`），不进 QEMU 探针门控。

## 根级清单

`tests/arch.yaml`（`id` = `arch-<cfx>-nnn`、`file`、`platforms: [system]`、`level`、`requires`），
由 `make check-tests-index`（L1，静态）守护。`level: smoke` = 由 L2 `check-arch-smoke` 覆盖。

## 门控

```sh
make check-arch-smoke   # L2：arch 代表集（SEE/semihosting + cfx 权限 + 25 服务覆盖）
make check-arch         # L3：check-arch-smoke + cfx min-ROM 场景探针（044/045/049）
make test-semihost      # 旧名别名 → check-arch-smoke（判据未改；TESTCASES-076t 删除）
python3 tools/gem5/check_tiny_hmon.py   # Tiny 两件装载契约 + cfx_power/cfx3 hmon（gem5 FS；m13-gem5-005）
```

前置：`make install-host`（工具链 + QEMU 取自安装根，ADR-0016 D9）与
`make build-bootrom`（bootrom 源在 `tests/shared/bootrom/`）。
