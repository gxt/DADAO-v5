# TESTCASES-075t: tset 迁移（libc-test/llvm-ts/embench）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：待开始

## 目标（P5）
1. 驱动：`tools/testcases/{run_libc_test_user_suite.py,run_llvm_ts_user.py,run_embench_user_suite.py}` → `tools/testcases/tset/<suite>/`；套件独有 glue → `tests/tset/<suite>/`（共享才进 `shared`）。
2. 新门控 `check-tset-<suite>-smoke`（L2）；旧目标保留别名；`ansibench` 不纳入。
3. 更新 `tests/tset.yaml`、Makefile/文档；`check-run-artifacts` 目录名仍按 Process-08。

## 验收
- 三套 smoke 绿；旧入口等价；`make check`/`check-modules` 绿；无期望/驱动语义改动。

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
