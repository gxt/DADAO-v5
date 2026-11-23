# m18-qemu-003: 旧异步探针（094t/050t）迁 monitor-first

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-qemu-002`（monitor-first 仲裁与 pending 迁移）
**可并行分片**：否
**预估**：1–2 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为两个旧探针的期望迁移，取 1–1.5× 中位）
**档位**：中改（探针/期望）
**状态**：待开始
**执行环境**：本地（`qemu-system-dadao`）

## 背景

`m18-qemu-002` 完成时发现：`tools/testcases/arch/min_rom_probe_async_094t.py` 与 `min_rom_probe_integ050t.py` 仍按 **target-first** 写期望（`TIMER=1<<10`、pending 在 `cfx_hart`）；它们不在 L2/L3 调用路径，所以本次未改，但会误导后续人工复跑。需迁到 monitor-first + cause 17/18。

## 目标

把两个探针的期望改为：

- 投递目标 = 当前运行模式 monitor（`cfx_umon`/`cfx_smon`）；
- pending = monitor 的 `cg5 rc5`，位 = `1<<17`（TIMER）/`1<<18`（PMEM_DMA）；
- mask 位索引仍 = 来源 cfxha（15/32）；
- **不改 QEMU 实现**，只改探针期望/读取逻辑。

## 验收（逐条贴真实 rc）

1. 两个探针在新 QEMU 上 rc=0；对旧 QEMU（target-first）应判红（可用构建树旧二进制或保存的基线证明）。
2. 探针仍覆盖：投递目标、pending 位置、两级 mask、同源 OR、escape 补投、单层投递。
3. **可达 FAIL ≥1 路**：把期望临时改回 target-first ⇒ 探针判红；`cp`+md5 还原后回绿。
4. 不回归：`check-qemu-forms`、`check-patch-tree` qemu 段 0 problem、`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tools/testcases/arch/min_rom_probe_async_094t.py`、`min_rom_probe_integ050t.py`、本任务书；不改 `components/**`、`spec/`、`.tao/contracts/`、`Makefile`。
3. 不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
