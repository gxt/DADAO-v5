# m16-chipyard-023: RTL cfx34 time（全局时间，无中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-022` 合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

004 盘点：RTL 缺 cfx34 time（QEMU/gem5 已有）。用户 2026-11-22 说明：**cfx34（time）与 cfx63（power）没有中断**；中断源只有 cfx15 的 timer 与 cfx32 的 pmem DMA 完成。

## 要做

1. **寄存器面**：cfx34 的全局时间计数器（`DADAO-12 §4.10`；位宽/单位按 `contract-see` 现场解析），只读。
2. **语义**：与 cfx15 的 `cycle`/`timer_cmp` 区分——cfx34 是**全局时间**，无中断、无 `timer_cmp`/`timer_ctrl`；单调递增，复位/epoch 按契约。
3. **探针**：RTL 探针读 time、隔一段指令再读、断言单调且增量合理；**不测中断**（cfx34 没有中断，写进探针注释）。
4. **不回归**：Tiny 无 cfx34；cfx3/4/5/15/32 既有语义不变。

5. **三方用例（B）**：cfx34 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

**H/S/U 三模式**（用户 2026-11-22）：cfx34 的时间计数器应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（复用 `tests/arch/common/env-{hmon,smon,umon}/`）；权限不允许的模式显式标注 `modes` 排除原因。

## 不做

- 不做 cfx15/32（前两件）；
- 不给 cfx34 加中断（用户明确没有）；
- 不改 cfx0/2 的模式路由。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：time 单调递增、增量合理；无中断路径（探针不配置/不等待中断）；
2. Tiny 代表例不回归；cfx3/4/5/15/32 探针不回归；
3. **可达 FAIL**：注入「time 不递增」⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
