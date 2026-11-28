# m18-testcases-001: 旧异步探针迁 hart-first

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-qemu-004`（QEMU hart-first）合入
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证
**作废**：2026-11-23，`ADR-0061` 改写异步模型：掩码归 monitor、源索引 cfxha、`cg9` 七槽只读、一帧多源；本任务不再验收，替代任务 `m18-testcases-003`


## 背景

`m18-qemu-002`（monitor-first）被 `ADR-0060` 取代；它的遗留发现：`min_rom_probe_async_094t.py`、`min_rom_probe_integ050t.py`、`min_rom_probe_integ042t.py`（pmem DMA 异步断言）仍按旧口径（target-first/monitor-first）写期望；`tools/testcases/arch/README.md` 的 integ051t 摘要也仍旧。`m18-qemu-003`（迁 monitor-first）已作废；本任务把三个探针直接迁到 **hart-first**。

## 要做

把两个探针的期望改为：

- 投递目标 = **`cfx_hart`（cfxha 15）** 的 supv 单向量（`cg9 rc6`），不再投 monitor/源 cfx；
- 现场 = `cfx_hart cg9 rc0–rc4`；`async_cause_id` = `1<<17`（TIMER）/`1<<18`（PMEM_DMA）；
- pending = `cg9 rc5`，位 = **cause id**（`1<<17`/`1<<18`）；
- mask = `cg9 rc8–rc12`，位 = **源 cfxha**（15/32）；
- `escape` 选 cg9 用 `imms18=2`；`3` ⇒ `ILLI`；
- `min_rom_probe_integ042t.py` 的 `pmem_dma_irq_delivered`/`pmem_dma_masked_pending` 改为 hart-first（`cfx_hart cg9`、pending `1<<18`），并更新 `tools/testcases/arch/README.md` 摘要。
- **不改 QEMU 实现**，只改探针期望/读取逻辑。

## 不做

- 不改 `components/**`、`spec/`/契约、`Makefile`；
- 不迁其它 M16 用例（013/014 由各自任务）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `min_rom_probe_async_094t.py`、`min_rom_probe_integ050t.py`、`min_rom_probe_integ042t.py`、`tools/testcases/arch/README.md` 与本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 三个探针在 hart-first QEMU 上 rc=0；对旧 QEMU（target-first/monitor-first）应判红；
2. 覆盖：投递目标、pending 位置、mask 位、同源 OR、escape 补投、单层投递；
3. **可达 FAIL**：把期望临时改回 monitor-first ⇒ 红；`cp`+md5 还原回绿；
4. `check-qemu-forms`、`check-patch-tree` qemu 段 0 problem、`check-component-changelog` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
