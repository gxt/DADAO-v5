# TESTCASES-074t: unit 迁移（LLVM/lld/qemu/picolibc）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：待开始

## 目标（P4）
1. `tests/llvm/lit/MC|CodeGen`、`llvm/codegen/m3/m4/m6`、`llvm/ir-lli`、picolibc 自测 → `tests/unit/{llvm,picolibc}/`。
2. 新门控 `check-unit`（lit + codegen + ir-lli + picolibc smoke）；旧 `check-lit`/`test-codegen`/`test-elf`/`test-m6`/`check-picolibc-tests` 保留别名。
3. 更新 `tests/unit.yaml`、ledger、Makefile/文档。

## 验收
- `check-unit` 绿；旧目标别名等价；`make check`/`check-modules` 绿；picolibc 仍在 unit。

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
