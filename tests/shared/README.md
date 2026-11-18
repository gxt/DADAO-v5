# `tests/shared/` — 共享测试基础设施（非用例）

> `docs/Process-09 §3/§6`：本目录只放**非用例**的共享件（被 ≥2 个 scope/套件复用，或基础
> harness 的固定数据）。判据与三类 glue 的定义见 `Process-09 §6`。

| 子目录 / 文件 | 内容 | 谁用 |
|---|---|---|
| `asm/` | `machine.inc`（`LOAD_ADDR` 宏）+ 由 `contracts/machine.yaml` + `tests/ee-<env>/runtime.yaml` 生成的 `machine-{tiny,vast}.inc` | bootrom / crt0 / arch 向量 |

> **机器几何真源已迁出本目录**（`m15-infra-001`）：几何/能力在 `contracts/machine.yaml`，
> 执行环境在 `contracts/exec-envs.yaml`，套件开关在 `contracts/tests-matrix.yaml`，
> 测试侧运行布局在 `tests/ee-{tiny,vast}/runtime.yaml`；读取统一走
> `tools/testcases/lib/machine_profile.py`。本目录不再有测试侧 profile 表。

> **2026-11-17（`m15-testcases-011` / `m15-testcases-012`）**：Tiny 专属 bootrom 与
> `kaiwu-tiny{,-app}.lds`/`picolibc-tiny.ld` 集中到 `tests/ee-tiny/`；qemu-user / gem5 SE 的
> `crt0/minimal_crt0.s`、`runtime/*`、`linker/dadao-common.lds`、`linker/dadao-dyn.lds` 集中到
> `tests/ee-user/`（均平铺）；本目录只留共用 BootROM 与 Vast 布局脚本。
> **2026-11-18（`m15-testcases-013`）**：Vast 的 step5 BootROM 固件与 `linker/kaiwu-vast.lds`
> 集中到 `tests/ee-vast/`（平铺）；`linker/` 子目录随之消失。
> **2026-11-18（`m15-testcases-015`）**：`bootrom/` 下的 Tiny 残留（`bootrom.lds`、`tiny_crt.S`、
> `tiny_smoke.S`、`semihost_msg.inc`）→ `tests/ee-tiny/`；K1 boot 链固件（原 `bootrom/k0/`，
> 实为 Kaiwu-Vast，加 `k0_` 前缀以免与 step5 的 `hmon.S`/`smon.S` 同名）→ `tests/ee-vast/`
> （均平铺）；`bootrom/` 子目录随之消失，本目录只剩 `asm/`、`init/`。

## 纪律

- **不放用例**：用例本体在 `tests/{inst,arch,unit,tset}/`；驱动在 `tools/testcases/`。
- **不放套件独有 glue**：只被一个套件用的 glue 放 `tests/tset/<suite>/`（如
  `embench_runtime.c` / `embench_include/`）。
- **不改上游**：本目录的文件都是我们自己的；要改上游组件源码 ⇒ `components/<name>/patches/`。
- 旧入口 `tests/scripts/` 已于 `TESTCASES-076t`（P6 收口）删除；迁移去向见
  `tests/INVENTORY.md §3.4`。
