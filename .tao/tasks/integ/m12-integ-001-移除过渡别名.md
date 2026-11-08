# m12-integ-001: 移除过渡别名（`dadao-m1`、`profile=node`）

**模块**：integ
**项目里程碑**：M12
**类型**：task
**状态**：待开始

## 前置

`m12-qemu-001`（拆机器 + 别名）、`m12-gem5-001`（profile vast + node 别名）、`m12-testcases-001`（测试迁移）全部合并后执行。

## 目标

1. `components/qemu`：删除 `dadao-m1` 别名与 `profile=node` 兼容分支
2. `components/gem5`：删除 `--profile node` 别名映射
3. 文档：两个组件的 README/changelog 记录别名移除
4. 全仓复扫：活文件（排除 ADR/归档/旧任务书/changelog）`dadao-m1`、`profile=node` 命中 0

## 验收标准

1. `-M help` 只剩 `dadao-tiny` / `dadao-vast`；`-M dadao-m1` ⇒ 明确「machine not found」
2. `--profile node` ⇒ 明确报错（不再映射）
3. `build-qemu`、`install-host`、`build-gem5`、L1、L2、`check-arch`、`check-inst` rc=0
4. `grep -rn 'dadao-m1\|profile=node'` 活文件 0 命中
5. 完成区 ≤30 行、无运行期路径
