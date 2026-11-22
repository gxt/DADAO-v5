# m16-testcases-014: cfx32 pmem DMA 完成中断（单独测试）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-chipyard-022`（RTL cfx32）合入后升三方；QEMU/gem5 侧可先做
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22）

中断源纳入 M16，**两个 cfx 分开测试**：本任务只测 **cfx32 的 pmem DMA 完成中断**；cfx15 timer 中断由 `m16-testcases-013` 单独测。不测跨 cfx 仲裁、uart、多核、嵌套。

## 要做

1. **DMA 完成**：配置 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`，搬运完成后 `dma_status` 的 DONE/错误按契约；搬运结果逐字节回读。
2. **中断进入**：DMA 完成 ⇒ `PMEM_DMA`（`cfx_pmem bit8`）进入当前运行模式 monitor；现场（cause/info/ip/run_mode）按契约。
3. **mask / pending / 补投**：`cfx_intr_mask` 屏蔽时 pending 保留；解除后补投。
4. **清除**：W1C / 清除 `dma_status`；清除后不重复进入。
5. **单 hart**：只测单 hart。
6. **三方**：QEMU + gem5 先跑；`m16-chipyard-022` 合入后升 RTL 三方，签名逐槽一致。
7. **未覆盖登记**：跨 cfx 仲裁（timer vs pmem）、uart、多核、嵌套不测。

## 不做

- 不做 cfx15 timer（013）；
- 不做跨 cfx 仲裁/优先级；
- 不改实现。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. DMA 搬运结果逐字节一致；`dma_status` DONE/错误；
2. 完成中断进入 monitor，现场字段逐项；屏蔽时 pending 保留、解除后补投；清除后不再进入；
3. 三方签名逐槽一致（RTL 未合入时两方，登记“RTL 待 022”）；
4. **可达 FAIL**：注入「DMA 不搬运」/「完成不触发中断」⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
