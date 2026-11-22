# m16-testcases-008: `unit` 允许 `system` 并登记 Tiny hmon

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（Tiny hmon 已迁 `tests/unit/gem5/`）已合入
**可并行分片**：否（共享 `tests/unit.yaml`/索引校验器）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

Tiny hmon 从 `tests/arch/` 迁到 **`tests/unit/gem5/`**（选 A）。`unit` scope 的 `platforms` 目前只允许 `host`/`toolchain`，导致该测试无法登记进 `tests/unit.yaml`，迁出后没有 L1/L2 覆盖。本任务放开 `unit` 的 `system` 平台并登记。

## 要做

1. **平台放开**：`tools/testcases/check_tests_index.py` 的 `SCOPE_PLATFORMS["unit"]` 增加 `"system"`；同步脚本内注释与 `--self-test` 用例。
2. **登记**：`tests/unit.yaml` 增加 `unit-gem5-hmon-001`：
   - `file: unit/gem5/check_tiny_hmon.py`；
   - `platforms: [system]`；
   - `level: full`（依赖 gem5 构建，不进 L2 `check-unit`）；
   - `requires: [gem5-fs]`（或现有合法依赖名，现场核 `check_tests_index` 允许集）。
3. **文件类型**：索引校验原本按 `.s`/`.ll` 等；允许 `unit` 的 `.py` 驱动（与 `arch` 的 driver 型一致），只校验文件存在、字段合法。
4. **文档**：`tests/unit/README.md`（或 `tests/unit/gem5/README.md`）写明 Tiny hmon 的运行方式、依赖 gem5 FS、不进 L2；`tests/arch/README.md` 已由 006 改，不再重复。
5. **门控**：`check-unit` 不因新增条目改变（level=full 不进 L2）；`check-unit-full` 是否纳入该测试由现有 full 规则决定；若 full 会跑 gem5，必须在任务书完成区说明耗时与前置。

## 不做

- 不改 Tiny hmon 测试本身；
- 不改 gem5 源码；
- 不改 arch 的 `machine: vast` 规则。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/unit.yaml`、`tools/testcases/check_tests_index.py`、`tests/unit/**/README.md`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-tests-index` rc=0；现场统计 `unit` 条数 = yaml 条数，`unit-gem5-hmon-001` 被识别；
2. 注入 3 路：① `platforms: [system]` 之外的非法值 ⇒ FAIL；② `file` 不存在 ⇒ FAIL；③ 重复 id ⇒ FAIL；`cp`+md5 还原后回绿；
3. `check-unit` rc=0 且**不因新条目多跑 gem5**（日志/成员数可比）；
4. `check_tests_index.py --self-test` rc=0；
5. `make check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
