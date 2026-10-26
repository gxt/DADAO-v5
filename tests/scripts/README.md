# `tests/scripts/` — 薄 wrapper 区（`TESTCASES-072t` 后）

inst 语义 harness 的**实现**已迁到 `tools/testcases/{lib,inst}/`（`Process-09` §6）：

| 旧路径（本目录） | 新位置 | 说明 |
|---|---|---|
| `build_test_binary.py` | `tools/testcases/lib/build_test_binary.py` | 向量 YAML → 测试二进制 |
| `run_qemu_test.py` | `tools/testcases/lib/run_qemu_test.py` | 单例/批量运行器 |
| `run_qemu_smoke.py` | `tools/testcases/inst/run_qemu_smoke.py` | inst 冒烟代表集（L2） |
| `gen_trampoline.py` | `tools/testcases/lib/gen_trampoline.py` | 生成 `trampoline.bin` |
| `verify_harness_dump.py` | `tools/testcases/lib/verify_harness_dump.py` | dump 通道手工校验 |
| `test_harness_exit_path.py` | `tools/testcases/lib/test_harness_exit_path.py` | harness 退出语义自检 |
| `trampoline.bin` | `tools/testcases/lib/trampoline.bin` | 本目录保留为**符号链接** |

- 上面的 `.py` 在本目录只留**薄 wrapper**：`python3 tests/scripts/<name>.py …` 仍与原实现**等价**
  （`runpy` 转发，`sys.exit` 码一致）。**删除旧入口**在 `TESTCASES-076t`。
- **未迁移**（后续 P3/P5）：`bootrom.S`/`bootrom_app.S`/`bootrom.lds`、`codegen_crt0.s`、
  `dadao.lds`/`dadao-dyn.lds`、`dadao_mem_runtime.ll`、`dadao_user_dyn_probe.c`、
  `embench_runtime.c`/`embench_user_boardsupport.c`/`embench_include/`（→ `tests/shared/` 或 `tests/tset/embench/`）。
- harness 详细文档：`tools/testcases/lib/README.md`。
