# arch scope — cfx 资源管理与权限控制用例（`tests/arch/`）

本目录是 **arch scope**（`docs/Process-09` §3/§5）：测 **cfx 资源管理与权限控制**
（trap/escape/cfx2rd/cfx2rc、inner/global/switch/instruction 掩码、异常 cause、
per-hart/per-system、TIMER/IPI/UART/power），只跑 **`system`** 平台
（`qemu-system-dadao` + SEE bootrom）。

> `TESTCASES-073t`（2026-10-27）落第一批用例（P3 arch 迁移）：`tests/unit/llvm/codegen/m5/`
> → `arch/umon/`。执行驱动在 `tools/testcases/arch/`（`run_m5_e2e.py` +
> `min_rom_probe_*.py`，由集成驱动目录与 `tools/qemu/` 在 P3 迁入）。

## 目录（按 cfx 划分，`<cfx>` 取自 `spec/DADAO-12 §3` 的 cfx 名）

| 目录 | cfx | 内容 |
|------|-----|------|
| `umon/` | `cfx_umon`（user monitor） | SEE/semihosting 执行向量 + cfx 级权限反例（`m5_*.s`，10 条）+ `expected.yaml` 清单 |

其余 cfx（`jmon`/`smon`/`hmon`/`ptw`/`tlb`/`cache`/`hart`/`llc`/`pmem`/`time`/`uart`/`power`）
按需增建；**不建** `arch/isa`、空壳子目录。

## 根级清单

`tests/arch.yaml`（`id` = `arch-<cfx>-nnn`、`file`、`platforms: [system]`、`level`、`requires`），
由 `make check-tests-index`（L1，静态）守护。`level: smoke` = 由 L2 `check-arch-smoke` 覆盖。

## 门控

```sh
make check-arch-smoke   # L2：arch 代表集（SEE/semihosting + cfx 权限 + 25 服务覆盖）
make check-arch         # L3：check-arch-smoke + cfx min-ROM 场景探针（044/045/049）
make test-semihost      # 旧名别名 → check-arch-smoke（判据未改；TESTCASES-076t 删除）
```

前置：`make install-host`（工具链 + QEMU 取自安装根，ADR-0016 D9）与
`make build-bootrom`（bootrom 源在 `tests/shared/bootrom/`）。
