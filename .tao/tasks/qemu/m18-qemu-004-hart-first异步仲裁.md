# m18-qemu-004: QEMU hart-first 异步仲裁（cfx_hart cg9）

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-spec-002`（spec/契约 hart-first）合入；`m16-qemu-003` 已合入
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`ADR-0060` 取代 `ADR-0059`：异步投递统一 **hart-first**——所有异步源（TIMER=`1<<17`、PMEM_DMA=`1<<18`）投 **`cfx_hart`（cfxha 15）** 的 supv 单向量；现场/mask/pending 在新增 **`cfx_hart cg9`**（16 rc）。`m18-qemu-002`（monitor-first）**不合入**、留参考分支；本任务对照它的仲裁/补投骨架，改目标为 `cfx_hart cg9`。

## 要做

1. **仲裁目标**：`dadao_async_arbitrate()` 投递目标 = `cfx_hart`（cfxha 15），入口 = supv 单向量（`cg9 rc6 async_excp_vector`、`rc7=2`）；不再按当前模式 monitor。
2. **cg9 现场**：进入时写 `async_prev_run_mode`/`prev_cfx_code`/`cause_ip`/`cause_id`；保存 `async_global_intr_mask` 到 `saved_global_intr_mask` 并置全 1。
3. **mask/pending**：五个 mask 在 `cg9 rc8–rc12`（位=源 cfxha 15/32）；`async_pending` 在 `rc5`（位=**cause id** `1<<17`/`1<<18`）；屏蔽时置 pending、不进入；同源 OR；写 0 清位。
4. **无嵌套/释放/重建**：`async_cause_id != 0` 时新事件只置 pending；软件写 0 释放帧、清 pending；可快照/重建。
5. **escape frame selector**：`imms18` 合法集 `{0,1,2}`（0/1=cg5 0/+4，2=cg9 0，3⇒ILLI）；`imms18[17:2]` SBZ；`cfxha`=当前 cfx；cg9 恢复 `prev_*` 与 `saved_global_intr_mask`。
6. **cause 常量**：`DADAO_CAUSE_TIMER=1<<17`、`DADAO_CAUSE_PMEM_DMA=1<<18`；`dadao_cause_check` 的 `[31:16]` 放行 17/18。
7. **探针/归档**：`min_rom_probe_integ051t`、K2/K5 异步探针、`tests/arch/vast-arch-inventory.md` 改 hart-first（cause 17/18、pending cg9、mask 位源 cfxha）。
8. **不回归**：M16 cfx5/cache 代表集；`check-patch-tree` qemu 段 0 problem。

## 不做

- 不改 `spec/`/契约（由 `m18-spec-002`）；
- 不做 monitor-first（ADR-0059 作废）；
- 不改 kernel/RTL/gem5；
- 不改版本号。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py qemu` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. TIMER/PMEM_DMA 都投 `cfx_hart` supv；`cg9 rc0–rc4` 现场逐项；mask 位 15/32；pending 位 `1<<17`/`1<<18`；
2. 屏蔽→pending 保留→解除补投；`cause_id != 0` 不嵌套；写 0 释放后不再进入；
3. `escape imms18=2` 恢复 cg9；`3` ⇒ `ILLI`；`imms18[17:2]≠0` ⇒ `ILLI`；
4. **可达 FAIL ≥3 路**（`cp`+md5 还原 + 重建）：① 投 monitor；② pending 记 cfxha 位；③ escape 选错帧；
5. 不回归：M16 cfx5/cache 代表集、`check-patch-tree` qemu 段 0 problem、`check-component-changelog`、`check-knowledge-refs`；
6. `--inject` ≥3 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
