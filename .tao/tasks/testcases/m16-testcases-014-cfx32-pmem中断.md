# m16-testcases-014: cfx32 pmem DMA 完成中断（hart-first）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`ADR-0060`（hart-first、Accepted）；`m16-chipyard-022`（RTL pmem + cg9）合入后升三方
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（ADR-0060 取代 ADR-0059）

异步投递统一为 **hart-first**：PMEM_DMA（`1<<18`，源 cfx_pmem）与 TIMER（`1<<17`，源 cfx_hart）都投 **`cfx_hart`（cfxha 15）** 的 **supv 单向量**；现场/mask/pending 全在 `cfx_hart cg9`。本任务只测 **cfx32 的 PMEM_DMA 完成中断**；cfx15 的 TIMER 由 `m16-testcases-013` 单独测。

## 要做

1. **DMA 完成**：配置 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`，搬运完成后 `dma_status` DONE/错误按契约；逐字节回读。
2. **进入**：DMA 完成 ⇒ `async_cause_id = 1<<18`；投 `cfx_hart` 的 supv 单向量（`cg9 rc6`、`rc7=2`）。
3. **现场**：`cg9 rc0–rc3`（prev_run_mode/prev_cfx_code/cause_ip/cause_id）；保存 `async_global_intr_mask` 到 `rc4` 并置全 1。
4. **mask / pending**：`cg9 rc8–rc12`，**位索引 = 源 cfxha（32）**；pending `cg9 rc5`，**位 = cause id（1<<18）**；屏蔽时置 pending、不进入。
5. **无嵌套/释放/重建/清除**：同 013（`cause_id != 0` 只置 pending；写 0 释放；清 pending 后不再进入）。
6. **返回**：`escape cfx_hart, [async_cause_ip, imms18]`，`imms18=2` 选 cg9；`3` ⇒ `ILLI`。
7. **三方**：QEMU + gem5 先跑；`m16-chipyard-022` 合入后升 RTL 三方。

## 不做

- 不做 monitor-first、跨 cfx 仲裁、uart、多核、嵌套。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. DMA 搬运结果逐字节一致；`async_cause_id=1<<18`；`cg9` 现场逐项；pending 位 `1<<18`；mask 位 32；
2. 屏蔽时 pending 保留、解除后补投；不嵌套；写 0 释放后不再进入；
3. `escape imms18=2` 恢复 cg9；`3` ⇒ `ILLI`；
4. 三方签名逐槽一致（RTL 未合入时两方，登记“RTL 待 022”）；
5. **可达 FAIL**：注入「DMA 完成投 monitor」/「pending 记 cfxha 位」⇒ 红；`cp`+md5 还原回绿；
6. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
