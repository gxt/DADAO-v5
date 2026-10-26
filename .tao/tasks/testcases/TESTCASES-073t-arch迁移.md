# TESTCASES-073t: arch 迁移（cfx/权限）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：待开始

## 目标（P3）
1. `tests/llvm/codegen/m5`（semihosting/CFX 权限）+ `tools/qemu/min_rom_probe_*` + bootrom → `tests/arch/<cfx>/`（bootrom/lds 进 `tests/shared` 或就近）。
2. 新门控 `check-arch-smoke`（L2，代表集）、`check-arch`（L3）；旧 `test-semihost`/min-ROM 入口保留别名。
3. 更新 `tests/arch.yaml`、ledger、Makefile/文档。

## 验收
- arch 代表集绿；旧 `test-semihost` 仍绿；无期望改动；`make check` 绿。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
