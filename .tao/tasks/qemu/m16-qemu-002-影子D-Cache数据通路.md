# m16-qemu-002: 影子 D-Cache 数据通路

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-001`（`cache-model` 属性 + cfx5 寄存器面）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

用户 2026-11-22 选 B：QEMU 用完整影子写回 D-Cache，`cache-model=on` 时只给 arch 测试，`off` 保持直通。`m16-qemu-001` 已落属性与寄存器面；本任务实现**影子 D-Cache 的存储与访存通路**，不含 cfx5 命令（下一件 `m16-qemu-003`）。

## 要做

1. **影子存储**：per-hart（当前单 hart）`tag/valid/dirty` + 行数据，几何与 RTL 一致：8 路 × 128 组 × 64 B = 64 KiB。
2. **访存代理**：`cache-model=on` 时在 PA RAM 前加一层 `MemoryRegionOps`；guest `ld/st`：
   - 读命中：读影子；
   - 读缺失：从底层 RAM 填充整行（64 B），再返回；
   - 写命中：只改影子并置 dirty；
   - 写缺失：写分配（先填充再合并）；
   - 淘汰：脏行整行写回底层 RAM。
3. **直连通道**：DMA（`cfx_pmem`）与镜像装载直连底层 RAM，绕过影子；`off` 时不建代理，行为与现状完全一致。
4. **取指**：本任务只做数据侧；I 侧仍走现有取指路径（命令语义在 `m16-qemu-003`）。
5. **不实现 cfx5 命令**：`cache_ctrl` 的 clean/invalidate/flush 留到下一件；本任务只保证数据通路正确。

## 不做

- 不实现 cfx5 命令、不做 I-Cache 语义；
- 不改 Linux/K0 路径（`off` 默认）；
- 不改 `src/cpu/simple/**`。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `off`：现有 QEMU 代表例（`check-arch-smoke`、K0/inst 一条）rc=0，行为与改前一致；
2. `on`：最小程序（读→写→再读）命中/缺失统计符合几何；同一程序 `on`/`off` 签名一致（功能不因 cache 改变）；
3. **可达 FAIL**：注入「写命中不置 dirty」⇒ 淘汰时不写回，后续 DMA 读到旧值 ⇒ 红；注入「行宽 32 B」⇒ 几何/命中统计红；`cp`+md5 还原后回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-index-blobs`、`make check-tasks` 记录 rc；
5. `--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
