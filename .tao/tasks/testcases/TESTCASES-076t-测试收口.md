# TESTCASES-076t: 测试迁移收口（P6）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-072t/073t/074t/075t
**状态**：待开始

## 目标（P6）
1. 删除旧入口：`tests/scripts/`、`tests/qemu/`、`tools/integ/`、旧 Make 目标（或全部改为新目标别名后删）。
2. 门控重写：L2 = 四 scope smoke；L3 = `check-inst`/`check-arch`/`check-unit` + `check-tset` smoke；`check-milestone` 加夜跑报告存在性；新增 `make check-night`。
3. `make clean-tests SCOPE=...`、`make test-repro SCOPE=...`（构建产物逐字节；运行记录排除）。
4. 全量 `make check` / `check-modules` / `check-full` 绿 + 一次 `check-night`；`tests/README`/`INVENTORY`/Process-09 收口。

## 验收
- 旧目录/目标删除且无悬空引用；三层门控全绿；夜跑落 `.dadao/tests/night/<date>/`；`case-ledger` byte-identical。

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
