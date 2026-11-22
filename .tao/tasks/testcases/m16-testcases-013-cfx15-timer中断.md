# m16-testcases-013: cfx15 timer 中断（单独测试）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-chipyard-021`（RTL cfx15）合入后升三方；QEMU/gem5 侧可先做
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22）

中断源纳入 M16，**两个 cfx 分开测试**：本任务只测 **cfx15 的 timer 中断**；cfx32 的 pmem DMA 完成中断由 `m16-testcases-014` 单独测。不测跨 cfx 仲裁、uart、多核、嵌套。

## 要做

1. **触发与进入**：`timer_cmp` 到期 + `timer_ctrl` 使能 ⇒ `TIMER`（`cfx_hart bit10`）进入当前运行模式 monitor；进入后现场（cause/info/ip/run_mode）按契约。
2. **mask / pending / 补投**：`cfx_intr_mask` 屏蔽时 pending 保留；解除屏蔽后补投（与 QEMU `integ051t` 的口径一致）。
3. **清除**：W1C / 重装 `timer_cmp`；清除后不重复进入。
4. **单 hart**：只测单 hart；hart_id 按平台约定。
5. **三方**：QEMU + gem5 先跑；`m16-chipyard-021` 合入后升 RTL 三方，签名逐槽一致。
6. **未覆盖登记**：跨 cfx 仲裁（timer vs pmem）、uart、多核、嵌套中断不测，写入清单。

**H/S/U 三模式**（用户 2026-11-22）：timer 中断的触发/进入/清除应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（`run_arch.py --mode`），验证中断进入“当前模式 monitor”；权限不允许的模式显式标注 `modes` 排除原因。

## 不做

- 不做 cfx32 pmem（014）；
- 不做跨 cfx 仲裁/优先级；
- 不改实现。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 触发/进入：timer 到期进入 monitor，现场字段逐项；
2. 屏蔽时 pending 保留、解除后补投；清除后不再进入；
3. 三方签名逐槽一致（RTL 未合入时两方，登记“RTL 待 021”）；
4. **可达 FAIL**：注入「timer 不触发」/「屏蔽仍投递」⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
