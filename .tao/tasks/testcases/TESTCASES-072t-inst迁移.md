# TESTCASES-072t: inst 迁移（vectors/isa + 探针 + harness）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：待开始

## 目标（P2）
1. `tests/vectors/isa/*` + `atomics/clmul/fma/minmax/roundint` 探针 → `tests/inst/<ext>/`。
2. harness：`tests/scripts/{build_test_binary.py,run_qemu_test.py,run_qemu_smoke.py,...}` → `tools/testcases/{lib,inst}/`；`tests/scripts` 留薄 wrapper。
3. 新门控：`check-inst-smoke`（L2，代表集）、`check-inst`（L3，全量）；旧 `check-qemu-smoke`/`check-qemu-semantics` 保持别名。
4. 更新 `tests/inst.yaml`、`case-ledger.tsv`、Makefile/文档引用。

## 验收
- 新路径可跑；旧入口仍可跑（等价结果）；`check-inst-smoke` 绿；`make check` 绿；无期望改动。

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
