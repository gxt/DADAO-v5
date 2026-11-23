# m16-testcases-013: cfx15 timer 中断（源 cfxha 15、一帧一源）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m18-spec-004`（ADR-0061 落地）；`m16-chipyard-024`（RTL 新 cg9）合入后升三方
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（ADR-0061）

异步源以**源 cfxha**标识：TIMER = `cfx_hart`（15），pending/帧内位都是 `1<<15`；来源掩码在各运行模式的 monitor（`cfx0–3 cg8 rc1`，复位全 1）；`cg9` 七槽、两个位图 HW/RO；帧由 `escape` 结束。本任务只测 **cfx15 的 TIMER**；PMEM_DMA（32）与"同帧多源"由 `m16-testcases-014`。

## 要做

1. **放行**：写当前模式 monitor 的 `cg8 rc1` 清 bit15（`0=允许`）；断言其它位仍为 1。
2. **触发与进入**：`timer_cmp` 到期 + `timer_ctrl.ENABLE=1` ⇒ 投 `cfx_hart` 的 supv 单向量（`cg9 rc5 excp_vector`、`rc6 switch_run_mode=2`）。
3. **现场**：`cg9 rc0 prev_run_mode`、`rc1 prev_cfx`、`rc2 cause_ip`（= 提交后的 `rb0`）、`rc3 src_frame` = `1<<15`、`rc4 src_pending` = 0（投递即清）。
4. **只读**：对 `rc3`/`rc4` 写入不应改变读数（具体写行为按 spec：忽略或 `CFXREG`）。
5. **屏蔽与 pending**：monitor 掩码 bit15=1 时只置 `src_pending`（`1<<15`）、不投递；清掩码后下一指令边界投递。
6. **源 ack 决定 pending**：帧活动期重装 `timer_cmp`（清 `ISTATUS`）⇒ pending 落、不产生遗留投递；不重装 ⇒ `escape` 后立即再次投递（电平语义）。
7. **无嵌套**：帧活动期再触发 ⇒ 只置 pending，`src_frame` 不变。
8. **返回**：`escape cfx_hart, [async_cause_ip, 8]`（`imms18=2`）恢复 mode/cfx/IP 并释放帧（`src_frame` 回 0）；`3`/`[17:2]≠0` ⇒ `ILLI`。
9. **精确点**：补一条"跳转后到期"用例——`jump` 目标处到期，断言 `cause_ip` = 目标、`escape` 从目标继续（`SimRISC-06` 的 `jump`，不是 RISC-V `jal`）。
10. **H/S/U 三模式**：同一份 body，`TMODE=3/2/0`；每模式写自己 monitor 的掩码。
11. **三方**：QEMU + gem5 先跑；`m16-chipyard-024` 合入后升 RTL 三方，签名逐槽一致。

## 不做

- 不做 monitor-first、跨 cfx 仲裁、uart、多核、嵌套帧；
- 不做 PMEM_DMA 与同帧多源（014）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 进入/现场/只读/屏蔽→pending→放行/无嵌套/ack 语义/返回释放 逐项；
2. `cause_ip` = 提交后 `rb0`（含 `br.*`/`jump` 后到期一条）；
3. 三方签名逐槽一致（RTL 未合入时两方，显式登记"RTL 待 024"）；
4. **可达 FAIL ≥2**：注入"掩码留 cfx_hart"、"pending 位记 17" ⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
