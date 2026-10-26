# TESTCASES-071t: 测试骨架与根级索引（P1，不动文件）

**模块**：testcases
**项目里程碑**：M10
**依赖**：Process-09（草案）
**状态**：待开始

## 目标（P1）
1. 建 `tests/{inst,arch,unit,tset,shared}/`（空目录可留 `.gitkeep`）。
2. 落根级索引 `tests/{inst,arch,unit,tset}.yaml`（字段：`id/file/platforms/level/requires`）+ `tests/README.md` 更新。
3. 新增 L1 门控 `check-tests-index`：ID 唯一、文件存在、字段/平台合法、计数现场派生；`--self-test` 注入→FAIL→还原→PASS。
4. **不移动任何现有文件**；旧门控全部保留。

## 验收
- `make check` rc=0；`check-tests-index` rc=0 且自检可达 FAIL。
- 目录/索引存在；`git status` 证明无测试文件移动。

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
