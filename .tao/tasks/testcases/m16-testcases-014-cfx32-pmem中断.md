# m16-testcases-014: cfx32 pmem DMA 完成中断 + 同帧多源（源 cfxha 32/15）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m18-spec-004`（ADR-0061 落地）；`m16-chipyard-022` 合入后升三方；同源用例 `013` 可并行复核
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（ADR-0061）

PMEM_DMA 的源是 `cfx_pmem`（32）：pending/帧内位 = `1<<32`，掩码位 = bit32（在**当前模式 monitor** 的 `cg8 rc1`）；DMA 完成细节（DONE/ERROR/ERR_CODE）回源 cfx 读 `cg15 rc4 dma_status`（W1C），**不走 `cause_info`**。同一界面上 timer（15）与 DMA（32）同时 pending 时**一帧承载两个源**（`src_frame` 位图），不串行开两帧。

## 要做

1. **DMA 搬运**：`dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`；完成后 `dma_status` DONE/错误；数据逐字节回读。
2. **放行**：写当前模式 monitor `cg8 rc1` 清 bit32（DMA）与 bit15（timer，供多源用例）。
3. **进入**：完成 ⇒ 投 `cfx_hart` supv 单向量；`src_frame` = `1<<32`；`source` 细节从 `cfx_pmem cg15 rc4` 读（DONE/ERROR + ERR_CODE）。
4. **屏蔽 / pending**：mask bit32=1 ⇒ 只置 `src_pending`（`1<<32`）；放行后投递；ack（W1C `dma_status`）后 pending 落。
5. **同帧多源**：同一界面上 timer 与 DMA 都 pending 且都放行 ⇒ **一次进入**、`src_frame = (1<<15)|(1<<32)`、`src_pending` 两位都清、`excp_async_num` +1；**断言只有一次进入**（不是两次）。
6. **一个源被屏蔽**：两个源中一个被 mask 时，帧只承载另一个，被屏蔽的留在 pending（`src_frame` 单 bit）。
7. **无嵌套 / 只读 / 返回释放 / `escape` 编码**：同 013（`rc3`/`rc4` 只读、`imms18=2` 返回、`3`/`[17:2]≠0` ⇒ `ILLI`）。
8. **H/S/U 三模式**各跑一次；每模式写自己 monitor 的掩码。
9. **三方**：QEMU + gem5 先跑；`m16-chipyard-022` 合入后升 RTL 三方。

## 不做

- 不做 monitor-first、嵌套帧、uart、多核；
- 不做 cfx15 单源的基础项（013 已覆盖）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 搬运逐字节、`dma_status` DONE/ERROR/ERR_CODE；
2. 进入现场 `src_frame=1<<32`、pending 位、mask 位、ack 后 pending 落；
3. **同帧多源**：一次进入、两位并集、`excp_async_num` 只 +1（与"拆成两次进入"的可达 FAIL 对照）；
4. 屏蔽单源时帧只承载另一源；
5. 三方签名逐槽一致（RTL 未合入时两方并登记）；
6. **可达 FAIL ≥2**：注入"多源串行开两帧"、"pending 记 17/18" ⇒ 红；`cp`+md5 还原回绿；
7. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
