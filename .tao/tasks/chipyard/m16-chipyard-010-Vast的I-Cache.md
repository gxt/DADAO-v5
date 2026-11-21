# m16-chipyard-010: Kaiwu-Vast 的 I-Cache（8 路 × 128 组，64 KiB，无 dirty）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-009`（D-Cache，复用 `WumingCache` 参数化类）
**可并行分片**：否（改 `dadao-wuming` 核）
**预估**：1–2 天
**档位**：中改
**状态**：待开始

## 用户已定口径（2026-11-20）

- **I/D 各 128 组**（8 路 × 128 组 × 64 B = 每侧 **64 KiB**）；
- **设计参照 TLB**：与 D-Cache 共用 `WumingCache` 类，I 侧 `withDirty=false`（**I 表无 dirty 位**，与 `m16-chipyard-008` 的 I-TLB 无 D 位同构）；
- **暂不做 stack/PTE cache**。

## 目标

1. 在核内实例化 I-Cache（`withDirty=false`、只读）；
2. 取指命中不访存；缺失按 8 beat 填充；
3. 与 D-Cache **共用同一个类**（不得复制第二份实现）；
4. **Tiny 零增益**：Tiny 不实例化。

## 验收（逐条贴真实 rc）

1. **命中/缺失**：顺序取指 1 miss + 同 line 后续 hit；探针记录；
2. **8 路 × 128 组**：同组 8 行共存、第 9 行按 LRU；
3. **无 dirty**：I 侧无写回路径（结构断言：dirty 寄存器数 = 0）；
4. **与 D 共用类**：`WumingCache` 只有一份实现（grep 计数现场派生）；
5. **Tiny 零增益**：Tiny 的 FIRRTL/SV 里 `WumingIcache` = 0；38 镜像不回归；
6. **可达 FAIL ≥2 路**：① 把 I 侧改成带 dirty ⇒ 结构断言红；② 索引位改 6 ⇒ 组冲突断言红；
7. `check-patch-tree` chipyard 段 0 问题。

## 约束

独立 `git worktree`；不提交 git；不改 `spec/`/契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
