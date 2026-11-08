# m12-gem5-001: gem5 FS profile `node` → `vast`

**模块**：gem5
**项目里程碑**：M12
**类型**：task
**状态**：待开始

## 背景

`configs/dadao/fs.py` 现用 `--profile {tiny,node}`，并有多处 `"node"` / `args.profile == "node"` 判断。用户裁定 profile 概念改名 `Tiny`/`Vast`。

## 目标

1. `components/gem5/patches/configs/dadao/fs.py.patch`：
   - profile 键与 choices 改为 `tiny` / `vast`，注释与帮助文本同步
   - **过渡期同时接受 `node`**（映射到 `vast` 并打印 deprecated 提示），保证测试迁移期间 L1 绿
2. `components/gem5/{README,changelog}.md` 记录改名与别名移除计划
3. 冒烟：`fs.py --profile vast` 用 Vast bootrom/镜像跑通一次；`--profile node` 输出 deprecated 但行为一致

## 验收标准

1. `--profile vast` 与 `--profile node` 同一镜像/参数下退出码与输出一致
2. `build-gem5`、`check-gem5-decode`、`check-source-state`、`check-patch-tree`、L1、L2 rc=0（测试尚未迁移，靠 `node` 别名不红）
3. 完成区 ≤30 行、无运行期路径

## 说明

- 别名的最终移除在 `m12-integ-001`（与 qemu 的 `dadao-m1` 别名一起删）
- 不改 `configs/dadao/se.py`（SE 无 profile）
