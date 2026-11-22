# m16-chipyard-021: RTL cfx15 hart（寄存器 + timer 中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-020` 合入（cfx0/2 模式路由已就位）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

004 盘点：RTL 缺 cfx15 hart（QEMU/gem5 已有）。用户 2026-11-22 定：三个 cfx（15/32/34）都补、每个 cfx 一件；**中断源只有 cfx15 的 timer 与 cfx32 的 pmem DMA 完成；cfx34/63 没有中断**。

## 要做

1. **寄存器面**：cfx15 的 `hart_id`、`cycle`、`insn`、`timer_cmp`、`timer_ctrl`（`DADAO-12 §4.7`；位域/读写属性按 `contract-see` 现场解析）。
2. **计数**：`cycle`/`insn` 按实现时钟计数；`hart_id` 单 hart 下为 0（或平台约定，写清）。
3. **timer 中断**：`timer_cmp` 到期按 `timer_ctrl` 触发 **TIMER**（`cfx_hart bit10`，按 `DADAO-12 §4.7`），进入当前运行模式 monitor；清除/重装语义按契约。
4. **探针**：RTL 探针读 hart_id/cycle/insn、写/读 timer_cmp/timer_ctrl、触发一次 timer 中断并观察进入 monitor。
5. **不回归**：Tiny 无 cfx15（保持现状）；cfx3/4/5 既有语义不变。

6. **三方用例（B）**：cfx15 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

## 不做

- 不做 cfx32/34（另两件）；
- 不改 cfx0/2 的模式路由（020）；
- 不加多核/IPI。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：hart_id/cycle/insn 读回合理（cycle/insn 单调）、timer_cmp/timer_ctrl 写读回、timer 到期进入 monitor；
2. Tiny 代表例不回归；cfx3/4/5 探针不回归；
3. **可达 FAIL**：注入「timer_cmp 不触发」⇒ 中断用例红；注入「cycle 不递增」⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
