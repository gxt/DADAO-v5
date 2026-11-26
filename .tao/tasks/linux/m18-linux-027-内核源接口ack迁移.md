# m18-linux-027: 内核迁移到每源 pending/mask/ack（cg15/cg16）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-spec-008`、`m18-qemu-009`、`m18-linux-026`（R3 出口帧基线）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改（异步入口/ack）
**状态**：待开始

## 背景

026 把出口帧迁到 R3（`escape cfx_hart`、`cg5 rc8–rc11`），但 ack 仍用旧路径：timer 读 `cg8 rc4/rc5`、检查 `ISTATUS`、靠写 `cmp` 当 ack。`m18-spec-008` 改为 `cg15` 捕获、`cg15 rc3` mask、`cg16` 源接口、pending ack 才清。

## 目标

1. 入口桩：`cg9` → `cg15`（`rc0`–`rc5`）；monitor mask 读写 `cg8 rc1` → `cg15 rc3`（`irqflags.h`、`init_IRQ`）。
2. ack 路径：按 `cg15 rc4` 逐源写 `cg16 rc18`（timer hart、DMA pmem）；**删除** `ISTATUS` 前置检查与 `die`；timer 重装 `cg16 rc1`（cmp）与 `rc0`（ENABLE）。
3. timer：`cg8 rc4/rc5` 访问全改 `cg16`；mask 通过 `cg16 rc16` 初始化（放开两个源）。
4. DMA：`dma_ctrl.IRQ_EN` 删除后不再写；ack 只清 pending，`dma_status` 另行 W1C（若有消费者）。
5. 探针/自检：K2/K5/K6 与 `tests/unit/linux/**` 中旧槽位全部迁移；`amb_window_probe` 适配 `cg15`。
6. 不回归：K2 170/170、K5 285/285、K6 82/82；`m18-linux-026` 的 R3 出口行为不变；kselftest 两轮一致。

## 验收

1. 旧槽 grep 0；ack 幂等；timer 使能即检；DMA 合并；`cg15 rc4/rc5` 聚合；`escape rc11` 目标行。
2. 可达 FAIL ≥2（ack 缺失 ⇒ 立即重入；pending 进入即清 ⇒ 事件丢失），`cp`+md5 还原重建回绿。
3. `check-patch-tree` linux 105/0；kselftest 两轮逐例一致（`ISS-m18-001` 命中单独计数、归 025）。
4. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

独立 worktree；不提交 git；只动 `components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、本任务书；不改 QEMU/spec/契约/Makefile；`make_patch.py linux`；`cp`+md5。
