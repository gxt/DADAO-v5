# m16-testcases-013: cfx15 timer 中断（R2 捕获缓冲，源 cfxha 15）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m18-spec-005`（R2 规格）；`m16-chipyard-026`（RTL 捕获缓冲）合入后升三方
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（R2）

`cfx_hart cg9` 是**进入瞬间的捕获缓冲**：每次进入整体覆盖，无"帧活动期"；软件搬走 `cg9`+GPR 后 handoff 到 `cfx_smon`，返回走 smon/umon；`escape imms18=2` **不用于异步返回**（`CFXESC`）。TIMER 源 = `cfx_hart`（15），pending/捕获位 = `1<<15`，掩码在当前模式 monitor 的 `cg8 rc1`。本任务只测 cfx15 单源；多源与 DMA 由 `m16-testcases-014`。

## 要做

1. **放行**：写当前模式 monitor 的 `cg8 rc1` 清 bit15；断言其它位仍 1。
2. **进入**：到期 ⇒ 投 `cfx_hart` supv 单向量（`cg9 rc5 excp_vector`、`rc6=2`）。
3. **捕获快照**：`rc0 prev_run_mode`、`rc1 prev_cfx`、`rc2 cause_ip`（= 提交后的 `rb0`）、`rc3 src_frame = 1<<15`、`rc4 src_pending`（投递后为 0）。
4. **RO**：`rc3`/`rc4` 写忽略、读回不变、不报异常。
5. **覆盖语义**：第一次进入后**不搬走**、再次到期 ⇒ 整体覆盖（`cause_ip`/计数变化）；**断言不是"只置 pending、不进入"**。
6. **屏蔽/pending/ack**：mask bit15=1 时只置 pending；放行后投递；ack（重装 `timer_cmp`）后 pending 落。
7. **无异步返回**：`escape cfx_hart, [async_cause_ip, 8]`（`imms18=2`）⇒ `CFXESC`，`cg9` 不变、cfx/mode 不变；`3`/`[17:2]≠0` ⇒ `ILLI`。
8. **精确点**：补"跳转后到期"用例（`jump` 目标处到期），断言 `cause_ip` = 目标（`SimRISC-06` 的 `jump`）。
9. **H/S/U 三模式**：同一 body，`TMODE=3/2/0`，各写自己 monitor 掩码。
10. **三方**：QEMU + gem5 先跑；`m16-chipyard-026` 合入后升 RTL 三方。

## 不做

- 不做软件 handoff 到 `cfx_smon`（内核任务 `m18-linux-022`）；
- 不做 monitor-first、跨 cfx 仲裁、uart、多核；
- 不做 DMA（014）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 进入/捕获/RO/覆盖/屏蔽→pending→放行/ack/`escape` 拒绝/`ILLI` 逐项；
2. `cause_ip` = 提交后 `rb0`（含跳转后到期）；
3. 三方签名逐槽一致（RTL 未合入时两方并登记）；
4. **可达 FAIL ≥2**：注入"帧门控只置 pending"、"`escape imms18=2` 返回" ⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
