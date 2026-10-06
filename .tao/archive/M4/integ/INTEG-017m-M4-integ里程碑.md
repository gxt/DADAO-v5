# INTEG-017m: M4 integ 里程碑

**模块**：integ
**项目里程碑**：M4
**状态**：里程碑
**目标**：M4 端到端闭环——多 TU/多段经 `llc → llvm-mc → ld.lld → ET_EXEC → qemu 直接加载` 跑对；ELF 结构断言（`readobj`/`readelf`）；L1 MC 向量接入门控转绿；M3 15 向量/多段/多文件经新链通过并与 `test-codegen`（raw-bin）差分一致；负例（畸形 ELF 拒绝、reloc 溢出 link-time error）。`make test-elf` 与 `make test-codegen` 并存。
**关联任务**：`INTEG-016t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tools/integ/run_elf_e2e.py`、`Makefile::test-elf`、`tests/llvm/lit/MC/DADAO`（M4 向量去 `UNSUPPORTED:` 接入 `check-lit`）、`tests/scripts/dadao.lds`（`LLVM-056t`）
- `make test-elf` EXIT=0（多 TU + 多段各 ≥1）；`make test-codegen`（M3 15/15）仍 EXIT=0（并存）
- 链路每步 EXIT=0（`llc`/`ld.lld`/`qemu`）；`readobj` 结构断言通过（`e_machine`/`e_flags`/`ET_EXEC`/`e_entry`/RELA）
- 差分：M3 15 向量新链 vs raw-bin 结果 0 分歧（差分表）
- `make check`/`make check-lit` EXIT=0（含 L1 `MC/DADAO` M4 向量）；`check-no-residue` 干净
- 负例：畸形 ELF 拒绝、reloc 溢出 link-time error（真实输出）
- 反例门控：`--inject` 改期望值 → FAIL → 还原+重跑全链 → 回绿
- 跨模块影响：`LLVM-056t`/`QEMU-042t`/`TESTCASES-029t`/`030t`/`032t` 均 `已验证`；`SPEC-107t` 的加载约定与实现一致；无未处置跨模块项

## 核验记录（主会话）

**M4 里程碑核验（主会话，2026-10-07）**：关联任务**全部 `已验证`**；产出存在（8 项抽检通过）；make check / check-lit / test-codegen / test-elf / check-no-residue / check-patch-tree / check-qemu-semantics 全部 EXIT=0（`.work/log/integ/m4-closure/`）；差异：`M3 15 向量经新 ELF 链 == raw-bin（0 分歧）`；负例（畸形 ELF / reloc 溢出）非零；跨模块影响已处置（issues 核查：6 结案 + 8 rescale M5 + 3 moot；`ISS-047` 改归 M5）。**结论：满足，置 `里程碑`**。
（核验命令、输出与退出码；结论）
