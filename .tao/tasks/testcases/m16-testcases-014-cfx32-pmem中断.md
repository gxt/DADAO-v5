# m16-testcases-014: cfx32 pmem DMA 完成中断 + 同界多源（R2 捕获缓冲）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m18-spec-005`（R2）；`m16-chipyard-022` 合入后升三方；同源用例 `013` 可并行复核
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（R2）

PMEM_DMA 源 = `cfx_pmem`（32）：pending/捕获位 = `1<<32`，掩码在当前模式 monitor `cg8 rc1` 的 bit32；DMA 细节回 `cfx_pmem cg15 rc4 dma_status`（W1C），无 `cause_info`。`cg9` 是捕获缓冲（每次进入覆盖、无帧活动期），软件搬走后 handoff `cfx_smon`；`escape imms18=2` ⇒ `CFXESC`（不异步返回）。同一界面 timer(15)+DMA(32) 都放行时**一次进入、一份捕获**（`src_frame` 位图并集）。

## 要做

1. **DMA**：配置/搬运/完成状态；数据逐字节回读；`DONE`/`ERROR` + `ERR_CODE`。
2. **放行**：写当前模式 monitor `cg8 rc1` 清 bit32（与 bit15）。
3. **捕获**：完成 ⇒ `src_frame = 1<<32`、`src_pending` 投递后清；细节读源 cfx。
4. **屏蔽/pending/ack**：mask bit32=1 只置 pending；放行后投递；W1C `dma_status` 后 pending 落。
5. **同界多源**：timer+DMA 同时 pending 且放行 ⇒ **一次进入**、`src_frame = (1<<15)|(1<<32)`、两位都清、`excp_async_num` +1；对照"拆成两次进入"应 FAIL。
6. **覆盖语义**：不搬走再到期 ⇒ 整体覆盖（不是只置 pending）。
7. **无异步返回**：`escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；`3`/SBZ 非零 ⇒ `ILLI`。
8. **H/S/U 三模式**各跑一次，各写自己 monitor 掩码。
9. **三方**：QEMU + gem5 先跑；`m16-chipyard-022` 合入后升 RTL 三方。

## 不做

- 不做软件 handoff 到 `cfx_smon`（`m18-linux-022`）；
- 不做 cfx15 单源基础项（013 已覆盖）；
- 不做 monitor-first、嵌套帧、uart、多核。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 搬运逐字节、DMA 状态/错误码；
2. 捕获 `src_frame=1<<32`、mask 位 32、ack 后 pending 落；
3. **同界多源**：一次进入、两位并集、计数 +1（与"串行两帧"可达 FAIL 对照）；
4. **覆盖语义**：不搬走再到期整体覆盖；
5. `escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；
6. 三方签名逐槽一致（RTL 未合入时两方并登记）；
7. **可达 FAIL ≥2**：注入"多源串行开两帧"、"`escape` 返回" ⇒ 红；`cp`+md5 还原回绿；
8. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
