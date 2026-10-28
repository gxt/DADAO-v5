# `tests/unit/llvm/` — LLVM 模块自身用例（unit scope）

> `TESTCASES-074t`（2026-10-27）由旧顶层 `llvm/` 迁入（P4 unit 迁移）；迁移期符号链接与
> 旧薄 wrapper 已由 `TESTCASES-084t` 删除。`e2e/`（工具链编译→链接→运行）于 `TESTCASES-084t`
> 由顶层 `e2e/` 归入本目录。

目录与门控（判据未改，只搬家 + 接线）：

| 目录 | 是什么 | 自动入口 |
|---|---|---|
| `lit/MC/DADAO/` | 汇编器编码 lit 用例（含受控子集 `gen-fast.s`） | `make check-lit`（L2；`check-unit` 成员） |
| `lit/MC/DADAO-gen/` | 由 `contracts/opcodes.yaml` 机械生成的全量 lit MC | `make check-lit-full`（L3；经 `test-m6`） |
| `lit/CodeGen/DADAO/` | IR→汇编/MIR 结构断言（`.ll` + `.mir`） | `make check-lit`（L2） |
| `lit/tools/DADAO/` | 占位（无测试） | — |
| `e2e/lit/` | 工具链 E2E：编译/汇编→链接→`qemu-system-dadao` 运行（14 个 `.test`） | `make check-lit`（L2；`check-unit` 成员） |
| `codegen/`（M3） | 单 TU IR→运行程序（15） | `make test-codegen`（L2；`check-unit` 成员） |
| `codegen/m4/` | 多 TU/多段 ELF（5 程序） | `make test-elf`（L2；`check-unit` 成员） |
| `codegen/m6/` | 调用约定/大帧/FP（8 程序） | **手工**（见 `codegen/m6/README.md`） |
| `ir-lli/` | host `lli` vs DADAO 值级差分清单 | `make check-unit`（L2）/ `make test-m6`（L3） |

- 全部用例的身份清单见根级 `tests/unit.yaml`（`make check-tests-index` 守护）。
- 驱动/校验脚本在 `tools/testcases/`（P4 只搬用例资产；集成驱动已由 P6 并入 `tools/testcases/`）。
