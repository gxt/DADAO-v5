# `tests/unit/llvm/` — LLVM 模块自身用例（unit scope）

> `TESTCASES-074t`（2026-10-27）从 `tests/unit/llvm/` 迁入（P4 unit 迁移）。
> 旧路径 `tests/unit/llvm/{lit,codegen,ir-lli}` 保留为**符号链接**（删除见 `TESTCASES-076t`）。

目录与门控（判据未改，只搬家 + 接线）：

| 目录 | 是什么 | 自动入口 |
|---|---|---|
| `lit/MC/DADAO/` | 汇编器编码 lit 用例（含受控子集 `gen-fast.s`） | `make check-lit`（L2；`check-unit` 成员） |
| `lit/MC/DADAO-gen/` | 由 `contracts/opcodes.yaml` 机械生成的全量 lit MC | `make check-lit-full`（L3；经 `test-m6`） |
| `lit/CodeGen/DADAO/` | IR→汇编/MIR 结构断言（`.ll` + `.mir`） | `make check-lit`（L2） |
| `lit/tools/DADAO/` | 占位（无测试） | — |
| `codegen/`（M3） | 单 TU IR→运行程序（15） | `make test-codegen`（L2；`check-unit` 成员） |
| `codegen/m4/` | 多 TU/多段 ELF（5 程序） | `make test-elf`（L2；`check-unit` 成员） |
| `codegen/m6/` | 调用约定/大帧/FP（8 程序） | **手工**（见 `codegen/m6/README.md`） |
| `ir-lli/` | host `lli` vs DADAO 值级差分清单 | `make check-unit`（L2）/ `make test-m6`（L3） |

- 全部用例的身份清单见根级 `tests/unit.yaml`（`make check-tests-index` 守护）。
- 驱动/校验脚本仍在 `tools/testcases/`、`tools/integ/`（本任务只搬家用例资产）。
