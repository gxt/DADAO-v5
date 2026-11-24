# m16-chipyard-026: RTL 异步捕获缓冲（ADR-0061 R2）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-024` 已合入（在其上改）；`m18-spec-005`（R2 规格）已合入
**可并行分片**：否（同改 `components/chipyard`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（R2，`spec/DADAO-12 §5.4`）

`m18-spec-005` 把 `cfx_hart cg9` 改为**进入瞬间的捕获缓冲**：每次异步进入都整体覆盖（`prev_*`/`cause_ip`/`src_frame`），**没有"帧活动期"、没有 `frame_valid`，硬件不因 `src_frame != 0` 拒绝进入或只置 pending**；软件在关中断窗口把 `cg9` 与 GPR 搬到任务现场，再 handoff 到 `cfx_smon`；返回走 smon/umon，`escape` **不以 `cg9` 为返回帧**（`imms18 = 2` ⇒ 当前 cfx 的 `CFXESC`，不改 cfx/mode/cg9）。来源掩码仍在当前运行模式 monitor 的 `cg8 rc1`，pending 跟随源、投递即清。

`m16-chipyard-024` 实现的是 pre-R2（`src_frame != 0` 防重入、`escape` 释放帧），本任务改到 R2。

## 要做

1. **仲裁去帧门控**：删除 `src_frame != 0` 的"只置 pending/不进入"分支；同一指令边界把 `pending & ~mask` 一次投递、整体覆盖 `cg9`；`pending` 扣除、`excp_async_num` 每次进入 +1。
2. **`escape`**：`imms18[1] = 1`（`imms20 = 8`）**不再异步返回**——按"所选帧无效"报当前 cfx 的 `CFXESC`，不改变 cfx/运行模式/`cg9`；`imms18 = 3` ⇒ `ILLI` 保持；同步 `cg5` 帧语义不变。
3. **探针**（`tests/arch/hart/cfx15.S` + `check_cfx15.py`）：
   - `cg9` 七槽与 RO（写忽略、读回不变、无异常）；捕获快照 `prev_*`/`cause_ip`/`src_frame` 位 = 15；
   - **覆盖语义**：第一次进入后不搬走，再次到期 ⇒ 整体覆盖（`cause_ip`/计数变化），**不是**只置 pending；
   - 掩码屏蔽时只置 pending、放行后投递；ack 源（重装 `timer_cmp`）后 pending 落；
   - `escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；`3`/`[17:2]≠0` ⇒ `ILLI`；
   - H/S/U 三模式（各写自己 monitor 的 `cg8 rc1`）。
4. **不回归**：同步 cg5 帧（020 的 U/S 路由、同步 `escape`）、Tiny（无 cfx15）、cfx5/cfx02 探针。

## 不做

- 不做软件侧 handoff 到 `cfx_smon`（内核任务 `m18-linux-022`）；
- 不改 QEMU/gem5/spec；
- 不引入 `frame_valid`/软件清 `src_frame`。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 覆盖语义（不搬走再到期 ⇒ 整体覆盖，不是只置 pending）；
2. `escape imms18=2` ⇒ `CFXESC` 且 `cg9` 不变；`3`/SBZ 非零 ⇒ `ILLI`；
3. 掩码/pending/ack、RO、三模式；
4. **可达 FAIL ≥2**：注入"恢复 `src_frame != 0` 门控"、"`escape imms18=2` 返回" ⇒ 红；`cp`+md5 还原并强制重建后回绿；
5. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`、`run_arch.py --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
