# m16-testcases-013: cfx15 timer 中断（hart-first）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`ADR-0060`（hart-first、Accepted）；`m16-chipyard-021`（RTL cg9）合入后升三方
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（ADR-0060 取代 ADR-0059）

异步投递统一为 **hart-first**：TIMER（`1<<17`，源 cfx_hart）与 PMEM_DMA（`1<<18`，源 cfx_pmem）都投 **`cfx_hart`（cfxha 15）** 的 **supv 单向量**；现场/mask/pending 全在新增 `cfx_hart cg9`。本任务只测 **cfx15 的 TIMER**；cfx32 的 PMEM_DMA 由 `m16-testcases-014` 单独测。

## 要做

1. **触发与进入**：`timer_cmp` 到期 + `timer_ctrl` 使能 ⇒ `async_cause_id = 1<<17`；投 `cfx_hart` 的 supv 单向量（`cg9 rc6 async_excp_vector`、`rc7 async_switch_run_mode=2`）。
2. **现场**：硬件写 `cg9 rc0 prev_run_mode`、`rc1 prev_cfx_code`、`rc2 cause_ip`、`rc3 cause_id`；保存 `async_global_intr_mask` 到 `rc4` 并置全 1。
3. **mask / pending**：五个 mask 在 `cg9 rc8–rc12`，**位索引 = 源 cfxha（15）**；pending 在 `cg9 rc5`，**位 = cause id（1<<17）**；屏蔽时置 pending、不进入。
4. **无嵌套**：`async_cause_id != 0` 时新事件只置 pending，不再次进入。
5. **释放/重建**：软件写 `async_cause_id=0` 释放帧、写 pending 0 清位；可快照/重建现场。
6. **返回**：`escape cfx_hart, [async_cause_ip, imms18]`，`imms18=2` 选 cg9 偏移 0；`imms18=3` ⇒ `ILLI`；`imms18[17:2]` SBZ。
7. **清除**：清 pending/cause 后不再重复进入。
8. **三方**：QEMU + gem5 先跑；`m16-chipyard-021` 合入后升 RTL 三方，签名逐槽一致。

## 不做

- 不做 monitor-first（ADR-0059 作废）、不做跨 cfx 仲裁、uart、多核、嵌套。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. TIMER 进入 `cfx_hart` supv 向量，`cg9` 现场字段逐项；`async_pending` 位 = `1<<17`；mask 位 = 15；
2. 屏蔽时 pending 保留、解除后补投；`cause_id != 0` 时不嵌套；写 0 释放后不再进入；
3. `escape` `imms18=2` 恢复 cg9；`imms18=3` ⇒ `ILLI`；
4. 三方签名逐槽一致（RTL 未合入时两方，登记“RTL 待 021”）；
5. **可达 FAIL**：注入「投递到 monitor」/「pending 记 cause 位」⇒ 红；`cp`+md5 还原回绿；
6. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
