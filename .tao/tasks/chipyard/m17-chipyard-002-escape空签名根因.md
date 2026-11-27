# m17-chipyard-002: `escape_ciii_cfx` 在 Tiny 上空签名（rc=0）根因定位

**模块**：chipyard
**项目里程碑**：M17
**依赖**：`m18-chipyard-002/003`（cg15/出口帧）、`m18-testcases-004/005`（向量迁移）、`m16-chipyard-033`（RegRAS 环形）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（诊断为主；复核 ≤20 min）
**状态**：待开始

## 背景（M17 收口唯一红，2026-11-27 实测）

`make check-idl-full`：**273/274**，唯一红 `escape_ciii_cfx`：

- 四方退出码全 0：`{idl:0,qemu:0,gem5:0,chipyard:0}`；
- **chipyard 签名字节流为空**（`.chipyard.out` 0 字节），IDL/QEMU/gem5 三份**逐字节相同**（md5 `25f3d355…`）；
- chipyard 日志末行：`SYS_EXIT op=0x18 arg=0xffffff017900 … reason=0x20026 code=0x0`，`pc=0xffffff014170`。

该 pc 反汇编为 `.faultpad::__pad_fail` 的 `trap cfx_umon, SYS_EXIT` 处。`__pad` 逻辑（`tests/inst/macros/inst_test.inc` §`__TEST_SECTIONS`）：`cause_id[15:0]` 与 `TEST_FAULTV[0]` 不等 ⇒ `__pad_fail`，退出码 = `TEST_FAULTV[8]`（点号）。实测退出码 **0** ⇒ 进入 pad 时点号槽仍为 0，即**在任何故障例武装之前出现了非预期异常**（或 `TEST_FAULTV` 数据在 Tiny 上读回 0）。

对照：11-27 03:20/03:50 的 `m18-chipyard-003` 证据里同一用例的 `.chipyard.out` **也是 0 字节**；11-25 之前该例是 `rc=13`（ILLI）。即形态已从「ILLI」变为「未武装即入 pad，静默 rc=0」。

## 要做（只定位，不修）

1. 复现：用既有 harness 只跑该例（`idl_four_way.py --only escape_ciii_cfx` 或 `run_inst_tiny.py --id escape_ciii_cfx --platforms chipyard`），固定证据目录；
2. **找出第一个非预期异常的指令与 cause_id**：用 Tiny sim 的 trace/日志（或分段裁剪 ELF、或在 handler 记录槽加临时观测）定位到 `.S` 的具体检查点，给出：pc、指令字、cause_id/子原因、当时的 run mode / cfx；
3. **判定归属**（三选一并给证据）：
   - RTL（cg15/出口帧/RegRAS 改动引入）——给出与哪个任务/改动相关、注入/回退哪一段可复现；
   - 测试载体（`m18-testcases-004/005` 迁移后不适用于 Tiny，如 `cg4 rc5`/`cg15 rc3` 访问或固件向量）——给出应改的点；
   - harness/固件（`run_inst_tiny`、Tiny hmon/power 入口）——给出证据；
4. 结论写入完成区，**不改 RTL/测试/固件**；若发现一行级测试载体修复即可验证归属，可在**独立 worktree** 内临时试验证，但只在完成区给 diff 建议，不提交。
5. 走查 `git log` 对应改动时间线（11-26 10:04 / 17:55 测试迁移；11-27 03:20 证据；04:44 RTL cg15；07:48 RegRAS），指出形态变化（rc=13 → 空签名）首次出现的 commit 附近。

## 不做

- 不改 RTL/测试/固件/契约；不登记/修改 `expected-divergences.yaml`；
- 不动其它用例。

## 约束

- 独立 `git worktree`；不提交 git；证据（日志、trace、反汇编片段）落运行期证据目录内 `run.sh` 可复跑；完成区 ≤30 行。

## 验证

1. `run.sh` 能复现「chipyard 0 字节 + rc=0」并输出第一个非预期异常的 pc/指令/cause；
2. 给出归属结论与「下一步应立什么任务（模块 + 一句话范围）」；
3. `git status -uall` 仅本任务书（诊断不改代码）。

## 完成区

（待填：测试结果 / 定位证据 / 归属结论 / 建议任务 / 遗留问题）
