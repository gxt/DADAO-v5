# `tests/shared/` — 共享测试基础设施（非用例）

> `docs/Process-09 §3/§6`：本目录只放**非用例**的共享件（被 ≥2 个 scope/套件复用，或基础
> harness 的固定数据）。判据与三类 glue 的定义见 `Process-09 §6`。

| 子目录 / 文件 | 内容 | 谁用 |
|---|---|---|
| `bootrom/` | Tiny trampoline（`bootrom.S`）与 Vast power→hmon BootROM（`step5/`）+ 链接脚本 | `make build-bootrom` → `check-arch{,-smoke}` |
| `crt0/` | `minimal_crt0.s`（`_start` → `@main` → `SYS_EXIT` 的最小启动桩） | `test-codegen` / `test-elf` / `tests/unit/llvm/e2e`（lit）/ embench 系统态 E2E |
| `linker/` | `dadao-common.lds`（公共段/符号）/ `dadao-tiny.lds`（Tiny）/ `dadao-vast.lds`（Vast 2 GiB、entry 1 MiB）/ `picolibc-tiny.ld` / `dadao-dyn.lds`（ET_DYN） | 同上 + `build_musl.py` / `run_suite.py` / tset 驱动 |
| `machine-profiles.yaml` | Tiny/Vast 的 BootROM/RAM/entry/SP/装载/PTW **唯一几何真源**（TESTCASES-091t） | 所有测试驱动 + 生成器 + `check-tests-index` |
| `asm/` | `machine.inc`（`LOAD_ADDR` 宏）+ 由 profile 生成的 `machine-{tiny,vast}.inc` | bootrom / crt0 / arch 向量 |
| `runtime/` | `dadao_mem_runtime.ll`（freestanding `mem*` 运行时）/ `dadao_user_dyn_probe.c`（动态装载 auxv 探针程序） | `test-m6` / Embench / 手工探针 |

## 纪律

- **不放用例**：用例本体在 `tests/{inst,arch,unit,tset}/`；驱动在 `tools/testcases/`。
- **不放套件独有 glue**：只被一个套件用的 glue 放 `tests/tset/<suite>/`（如
  `embench_runtime.c` / `embench_include/`）。
- **不改上游**：本目录的文件都是我们自己的；要改上游组件源码 ⇒ `components/<name>/patches/`。
- 旧入口 `tests/scripts/` 已于 `TESTCASES-076t`（P6 收口）删除；迁移去向见
  `tests/INVENTORY.md §3.4`。
