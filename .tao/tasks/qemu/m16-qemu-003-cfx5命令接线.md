# m16-qemu-003: cfx5 命令接线（clean/invalidate/flush）

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-002`（影子 D-Cache 数据通路）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`m16-qemu-001` 已落 cfx5 寄存器面，`m16-qemu-002` 已落影子 D-Cache 数据通路。本任务把 `cache_ctrl` 命令接到影子 cache，语义按 `m16-spec-001`/`spec/Kaiwu §3.2`。

## 要做

1. **命令解码**：`cache_ctrl` 的 `[1:0]` 操作（none/clean/invalidate/flush）、`[3:2]` 范围（all/PA 单行/PA 区间/reserved）、`[15:14]` 选择（I/D）；`cache_addr_start`/`cache_addr_size` 按 56 位 PA。
2. **D 侧效果**：
   - clean：脏行写回，保留行；
   - invalidate：丢弃脏数据（不写回）、删除行；
   - flush：写回 + 删除；
   - 范围匹配、使能位为 0 时不维护、不可缓存/MMIO 无效果不报异常。
3. **I 侧**：clean 为 no-op；invalidate/flush 调 `tb_invalidate_phys_range`（复用 ARM `IC_IVAU` 的写法），保证后续取指重取；不做 I 阵列。
4. **异常**：保留编码/`size=0` 等按契约报 `CFXREG`；不得 panic。
5. **off 模式**：cfx5 命令仍按 `CFXREG`（`m16-qemu-001` 口径）。

## 不做

- 不改影子数据通路（qemu-002）；
- 不改 RTL/gem5；不写新用例（`m16-testcases-009`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. D 侧：脏行 `invalidate` 后底层 RAM 仍旧值（DMA 读可见）；`clean` 后底层 RAM 新值；`flush` 后行不存在但内存新值；
2. I 侧：改写代码后 `invalidate`，取指执行新代码；
3. 范围：all / 单行 / 区间 / reserved 的编码与异常逐条；
4. **可达 FAIL**：注入「invalidate 先写回」⇒ 旧值判据红；注入「I 侧不调 tb invalidate」⇒ 旧指令判据红；`cp`+md5 还原后回绿；
5. `check-patch-tree` qemu 段 0 problem、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
