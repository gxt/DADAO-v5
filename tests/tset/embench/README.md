# `tests/tset/embench/` — Embench-IoT（外部套件，user 成品系统）

上游语料 **不入库**：由 `manifests/components.lock.toml` 锁定，`make fetch` 后位于
`.work/source/embench-iot/`。本目录放**套件独有 glue**（`Process-09 §6`）：

- `embench_user_boardsupport.c` — user-mode 板级 shim（`initialise_board` /
  `start_trigger` / `stop_trigger` 打点；上游 semihosting shim 在 user 模式不可用）。
- `embench_runtime.c` — 最小运行时（`str*` / `ctype` / `sqrt` / `abort`，不引 libc）。
- `embench_include/` — freestanding 头（`assert.h` / `stdio.h` / …）。

`TESTCASES-075t` 从旧共享区迁入；迁移期符号链接已在 `TESTCASES-076t`（P6）删除。`tests/shared/runtime/dadao_mem_runtime.ll` 是**共享**运行时，未随本
套件移动。

## 入口

| 用途 | 命令 |
|---|---|
| L2 smoke（全量 benchmark × `-O0/-O2`） | `make check-tset-embench-smoke` |
| 驱动（按需） | `python3 tools/testcases/tset/embench/run_embench_user_suite.py --link-mode static --json-out /tmp/.../embench.json` |

- 驱动实现：`tools/testcases/tset/embench/run_embench_user_suite.py`
  （`TESTCASES-075t` 从 `tools/testcases/` 迁入；旧路径 = 薄 wrapper，命令行等价）。
- 运行目录 / 三件套：`<test-artifacts>/embench-user/<UTC>-embench-user-<档>/`
  （`docs/Process-08`；目录名**未改**）。
- `test-m6` 的 Embench E2E（`tools/testcases/tset/embench/run_embench_e2e.py`）共用本目录 glue，
  路径已同步。

## 口径

- 期望值 = 上游 `support/main.c` 返回 `!correct`（即 guest exit 0）+ 三个板级
  打点均出现；没有从 QEMU/LLVM 反推的期望。
- 全量 benchmark 数、`pass/fail/blocked` 计数均现场派生，不写死。
