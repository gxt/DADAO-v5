# m12-testcases-001: 测试与 profile 迁移到 `tiny` / `vast`

**模块**：testcases
**项目里程碑**：M12
**类型**：task
**状态**：待开始

## 目标

把测试侧全部从 `dadao-m1` / `profile=node` 迁到新命名：

1. `tests/shared/machine-profiles.yaml`：profile 键 `node` → `vast`（几何不变），注释与字段说明同步
2. 生成物：`tests/shared/asm/machine-node.inc` → `machine-vast.inc`；`tests/shared/bootrom/step5/{power,smon,hmon}.S` 的 include 同步
3. `tools/testcases/**`（约 46 个文件）：`-M dadao-m1` → `-M dadao-tiny`；`dadao-m1,profile=vast` → `-M dadao-vast`；`DADAO_TEST_PROFILE=node` → `=vast`
4. `Makefile` 中机器名/参数同步
5. `tools/qemu/semantics_gate.py` 散文改 `dadao-v5`（历史裁定引用保留原意）

## 验收标准

1. `grep -rn 'dadao-m1\|profile=node\|DADAO_TEST_PROFILE=node' tools/ tests/ Makefile` 为 0（历史任务书/ADR/changelog 除外）
2. `make check`（L1）rc=0；`make check-modules`（L2）rc=0
3. `check-arch` / `check-arch-smoke` / `check-inst` rc=0（Tiny 与 Vast 各至少一个代表用例）
4. `machine-profiles.yaml` 与派生 `.inc` 一致（派生脚本 rc=0）
5. 完成区 ≤30 行、无运行期路径

## 说明

- 只改测试/工具侧；QEMU 代码与 gem5 配置不动
- 若某用例依赖 `profile=` 的默认值，逐条改为显式机器名并记录
