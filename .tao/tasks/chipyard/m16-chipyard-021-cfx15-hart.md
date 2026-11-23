# m16-chipyard-021: RTL cfx15 hart（cg8 管理 + cg9 异步现场 + timer 中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-020` 合入（同步路由已就位）；`ADR-0060`（hart-first，Accepted）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`ADR-0060` 取代 `ADR-0059`：异步投递统一 **hart-first**——TIMER（`1<<17`）与 PMEM_DMA（`1<<18`）都投 **`cfx_hart`（cfxha 15）** 的 supv 单向量，现场/mask/pending 全在新增 **`cfx_hart cg9`**。本任务补 RTL 的 `cfx_hart`：cg8 原有管理寄存器 + 新增 cg9。

## 要做

1. **cg8（原 hart 管理）**：`hart_id`/`cycle`/`insn`/`timer_cmp`/`timer_ctrl`（`DADAO-12 §4.7`）；`cycle`/`insn` 按时钟计数；`hart_id` 单 hart 为 0。
2. **新增 cg9（16 rc，ADR-0060 D2）**：`async_prev_run_mode`(2b)、`async_prev_cfx_code`(6b)、`async_cause_ip`(48b)、`async_cause_id`(64b，非 0=有效帧)、`async_saved_global_intr_mask`、`async_pending`(位=**cause id** `1<<17`/`1<<18`)、`async_excp_vector`(48b)、`async_switch_run_mode`(2b，固定 supv=2)、`async_global_intr_mask`/`async_user_intr_mask`/`async_jail_intr_mask`/`async_supv_intr_mask`/`async_hypv_intr_mask`(位索引=**源 cfxha** 15/32)；rc13–15 reserved。
3. **TIMER 投递（hart-first）**：`timer_cmp` 到期 ⇒ `async_cause_id=1<<17`；投 `cfx_hart` 的 **supv 单向量**（`cg9 rc6`/`rc7=2`），写 `cg9 rc0–rc4`；mask 查 `cg9 rc8–rc12`（位=15）；pending 置 `cg9 rc5`（位=`1<<17`）。
4. **无嵌套/释放/重建**：`async_cause_id != 0` 时新事件只置 pending；软件写 0 释放帧、清 pending；可快照/重建。
5. **escape frame selector（bit1）**：`imms18=2` 选 `cg9` 偏移 0；`imms18=3` ⇒ `ILLI`；`imms18[17:2]` SBZ；`cfxha` = 当前 cfx。
6. **探针**：cg8/cg9 寄存器读写；timer 到期投 cfx_hart/supv、cg9 现场/pending/mask；`escape imms18=2` 返回；`3` ⇒ `ILLI`。
7. **H/S/U 三模式**：timer 在 hmon/smon/umon 下都投 `cfx_hart` supv（目标固定，不随当前模式变）；权限不允许的模式显式标注。
8. **三方用例（B）**：case 定义/期望只写一份；RTL 探针与 QEMU/gem5 复用同一 case；由 `check-arch-vast` 按需跑。
9. **不回归**：Tiny 无 cfx15；cfx3/4/5 既有语义不变。

## 不做

- 不做 cfx32/34（另两件）；
- 不改 cfx0/2 的同步路由（020）；
- 不做 monitor-first（ADR-0059 作废）；
- 不加多核/IPI。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. cg8/cg9 寄存器读写/保留；`cg9 rc13–15` ⇒ `CFXREG`；
2. timer 到期：`async_cause_id=1<<17`、投 cfx_hart supv、`cg9` 现场逐项、pending 位 `1<<17`、mask 位 15；
3. `escape imms18=2` 返回；`3` ⇒ `ILLI`；`imms18[17:2]≠0` ⇒ `ILLI`；
4. H/S/U 三模式下投递目标均为 cfx_hart/supv；
5. **可达 FAIL**：注入「timer 投 monitor」/「pending 记 cfxha 位」⇒ 红；`cp`+md5 还原并强制重建后回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
