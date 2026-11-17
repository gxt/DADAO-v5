# `tests/shared/` — 共享测试基础设施（非用例）

> `docs/Process-09 §3/§6`：本目录只放**非用例**的共享件（被 ≥2 个 scope/套件复用，或基础
> harness 的固定数据）。判据与三类 glue 的定义见 `Process-09 §6`。

| 子目录 / 文件 | 内容 | 谁用 |
|---|---|---|
| `bootrom/` | `bootrom.lds`、`tiny_crt.S`、`tiny_smoke.S`、`semihost_msg.inc` 与 Vast power→hmon BootROM（`step5/`）（Tiny 的 `.S`/`lds` 已迁 `tests/ee-tiny/`，`m15-testcases-011`） | `make build-bootrom` → `check-arch{,-smoke}` |
| `linker/` | `kaiwu-vast.lds`（Vast 2 GiB、entry 1 MiB）（Tiny 的 `kaiwu-tiny{,-app}.lds`/`picolibc-tiny.ld` 已迁 `tests/ee-tiny/`，`m15-testcases-011`；`dadao-common.lds`/`dadao-dyn.lds` 已迁 `tests/ee-user/`，`m15-testcases-012`） | `check-interface` / `run_parity`（vast） |
| `machine-profiles.yaml` | Tiny/Vast 的 BootROM/RAM/entry/SP/装载/PTW **唯一几何真源**（TESTCASES-091t） | 所有测试驱动 + 生成器 + `check-tests-index` |
| `asm/` | `machine.inc`（`LOAD_ADDR` 宏）+ 由 profile 生成的 `machine-{tiny,vast}.inc` | bootrom / crt0 / arch 向量 |

> **2026-11-17（`m15-testcases-011` / `m15-testcases-012`）**：Tiny 专属 bootrom 与
> `kaiwu-tiny{,-app}.lds`/`picolibc-tiny.ld` 集中到 `tests/ee-tiny/`；qemu-user / gem5 SE 的
> `crt0/minimal_crt0.s`、`runtime/*`、`linker/dadao-common.lds`、`linker/dadao-dyn.lds` 集中到
> `tests/ee-user/`（均平铺）；本目录只留共用 BootROM 与 Vast 布局脚本。

## 纪律

- **不放用例**：用例本体在 `tests/{inst,arch,unit,tset}/`；驱动在 `tools/testcases/`。
- **不放套件独有 glue**：只被一个套件用的 glue 放 `tests/tset/<suite>/`（如
  `embench_runtime.c` / `embench_include/`）。
- **不改上游**：本目录的文件都是我们自己的；要改上游组件源码 ⇒ `components/<name>/patches/`。
- 旧入口 `tests/scripts/` 已于 `TESTCASES-076t`（P6 收口）删除；迁移去向见
  `tests/INVENTORY.md §3.4`。
