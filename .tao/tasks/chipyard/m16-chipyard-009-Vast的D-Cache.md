# m16-chipyard-009: Kaiwu-Vast 的 D-Cache（8 路 × 128 组，64 KiB）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-008`（I/D TLB）、`m16-chipyard-007`（PTW 两级步查）
**可并行分片**：否（改 `dadao-wuming` 核）
**预估**：2–3 天
**档位**：大改
**状态**：待开始

## 用户已定口径（2026-11-20，不得自决）

- **I/D 各 128 组**（8 路 × 128 组 × 64 B = **每侧 64 KiB**，合计 128 KiB）；
- **设计参照 TLB**：参数化类 + 每核一个实例（I/D 各一），Tiny 不实例化；
- **暂不做 stack cache / PTE cache**（前者等 VA 区间与一致性规则，后者另议）。

## 参数与硬约束

- **line 64 B**（8 个 64 位 beat）、**8 路**、**128 组**；
- **索引位必须在 64 KiB 页内**：line offset 6 位 + 组索引 7 位 = 13 位 < 16 位 ⇒ **VIPT 无别名**（每路 8 KiB）；
- **D-Cache：写回 + 写分配**，每行一个 dirty 位；
- **PTW 的页表读走 D-Cache 端口**（与 BOOM/rocket 同构，`m16-chipyard-008` 已有 PTW）；
- 阻塞式（单未决缺失）作为首版；非阻塞另立任务；
- 资源：每侧 **16 块 RAMB36**（64 位宽折算 4 KiB/块），合计 32 块。

## 目标

1. `WumingCache.scala`：参数化类（`sets`/`ways`/`lineBytes`/`writeBack`/`withDirty`），**参照 `WumingTlb.scala` 的写法**（`m16-chipyard-008`）；
2. 在核内实例化 D-Cache（`withDirty=true`），接 PTW 的 PTE 读端口；
3. **命中/缺失**：命中不访存；缺失按 8 beat 填充；
4. **写回**：脏行在淘汰或 clean 时写回；写命中只改 cache；
5. **clean/flush 操作**（内部接口先行，`cfx5` 接线另立任务）：按 PA 单行 clean/invalidate、全表 flush；
6. **Tiny 零增益**：Tiny 不实例化（FIRRTL 里 0 命中）。

## 验收（逐条贴真实 rc）

1. **命中/缺失**：同址重复访问 1 miss + N hit；探针记录（`WumingDcache` 计数）；
2. **8 路**：同组 8 行共存、第 9 行按 LRU 淘汰（给替换序列）；
3. **写回**：写后读命中不回内存；淘汰后才见写回（记录内存值变化时机）；
4. **PTW 端口**：PTE 读经 D-Cache；核内改 PTE（经 D-Cache 写）后 PTW 立即读到新值；
5. **Tiny 零增益**：Tiny 的 FIRRTL/SV 里 `WumingDcache` = 0；首册 38 镜像不回归；
6. **可达 FAIL ≥3 路**：① 把 8 路改成全相联 ⇒ 替换序列红；② 去掉 dirty 位（写穿）⇒ 写回时机红；③ 索引改用 PA 或改 6 位 ⇒ 同组/容量断言红（`cp`+md5 还原 + 强制重建）；
7. `check-patch-tree` chipyard 段 0 问题；`check-component-changelog` rc=0。

## 约束

独立 `git worktree`；不提交 git；只动 `dadao-wuming` 与组件补丁树；不改 `spec/`/契约/`manifests/`；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
