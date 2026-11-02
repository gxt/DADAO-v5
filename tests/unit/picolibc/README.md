# `tests/unit/picolibc/` — picolibc 上游自测（unit scope）

picolibc 自测**仍在 picolibc 自己的 Meson 构建下运行**（`TESTCASES-042t` 口径未改）：
测试集合由上游 `meson-info/intro-tests.json` / `intro-targets.json` **现场派生**，
本目录**不复制**测试源码或测试清单（避免与上游漂移）。

- 驱动：`tools/testcases/picolibc_tests.py`（编译/链接/QEMU 运行 + 独立判据：
  测试自身退出码；`fail=0` 且 `blocked=0` 才 PASS）。
- 构建/运行树：`.work/build/picolibc`（被测库）+ `.work/build/picolibc-tests-run`
  （自测构建，`--stage fast` 与 `full` 共用）。
- 门控：
  - `make check-picolibc-tests`（L2 代表集；`check-unit` 成员）
  - `make check-picolibc-tests-full`（opt-in/L3-like 全量）
  - `make test-picolibc-smoke`（最小 `printf` 端到端）
- 本目录只承载 unit scope 的**入口说明**；用例身份见根级 `tests/unit.yaml`
  （`unit-picolibc-001`，`make check-tests-index` 守护）。
