# m13-testcases-005: case 级批量测试池（多节点、即产即落、可续跑）

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（协议见 `docs/Process-09 §16`、`docs/Process-08 §1.9`，已生效）
**可并行分片**：否（工具实现）
**状态**：待开始

## 背景

`m13-testcases-003` 在 207/208 跑 150 例长尾时暴露三类等待放大：

1. **套件级波次**：`run_engine_ratio.py` 先跑完某套件的全部 qemu 才跑 gem5；一个 1103 s 的 qemu 挡住 35 例 gem5 约 18 min。
2. **结果攒批**：驱动在套件结束才写 JSON ⇒ 中途零可读结果，节点无法按「剩余量」调度。
3. **节点写死**：分片在脚本里固定，新增节点要改代码。

`docs/Process-09 §16` 已定五条原则与队列协议，本任务把它落成工具。

## 目标

实现 `tools/testcases/tset/gem5-se-baseline/run_pool.py`（命令 + 模块）：

1. **输入** `cases.jsonl`：一行一例 `{case, suite, link_mode, budget_s, class}`（`class ∈ short|normal|long|xlong`）。
2. **调度**：主控机侧按 `remote.py status` 的 `loadavg`/`disk_alert`/`running` 决定每个节点并发数（`--jobs-per-node`，默认取 `min(空闲核, 48)`）；**节点列表来自 `--hosts`，不写死**。
3. **执行**：每例一个独立命令，调用**既有驱动**（`run_llvm_ts_user.py` / `run_libc_test_user_suite.py` 的 `--only <case>`），**不重写构建/比对逻辑**；每例独立 `--work-dir`、独立超时（`budget_s`）。
4. **即产即落**：每例结束立刻向 `progress.jsonl` 追加一行（`Process-08 §1.9` 字段），并写 `state.jsonl` 状态变更（含 `attempt`、`node`、UTC）。
5. **幂等续跑**：`--resume` 读 `progress.jsonl` 的 `done` 集合跳过；`failed/timeout` 按 `--retry N` 重排，**重试次数记录**。
6. **xlong 隔离**：`class=xlong` 只派给 `--xlong-hosts` 指定的节点（默认 = 全部），且可设独立预算；**不得**占用主队列节点配额。
7. **指标**：结束时输出吞吐（例/h）、等待放大系数（Σ单例耗时 / (墙钟 × 节点数)）、每节点空转率、屏障次数（应 0）。

## 非范围

- 不改驱动/引擎/用例/期望（只调用）
- 不改 `run_engine_ratio.py`（它是套件级门控工具，保持现状）
- 不做结果归因/矩阵（`m13-integ-001` 的生成器负责）

## 验收标准

1. **功能**：在 207/208 上跑一个 **20 例** 混合样本（含 pass / fail / timeout 各若干），全部落 `progress.jsonl`，逐行字段完整、时间递增、无覆盖。
2. **续跑**：跑到一半强杀（SIGTERM），`--resume` 重跑 ⇒ 已 `done` 的例**不重跑**（用 `attempt` 计数与日志证明），未完成的补跑。
3. **等待放大系数 ≤1.5**（20 例样本，2 节点；给出实测值与算法）。
4. **新节点加入**：`--hosts` 增加一个节点后无需改代码即可接活（可用同一节点重复写两次模拟，或用 `--dry-run` 证明派单逻辑）。
5. **xlong 隔离**：构造一个 `xlong` 例，验证它只派给 `--xlong-hosts`、且不减少主队列在其他节点的并发。
6. **失败处置**：某例返回非零/超时 ⇒ 记 `failed`/`timeout` 并继续下一例，不中断整池；`--retry` 生效且次数可查。
7. 门控：`check-tasks` / `check-no-residue` / `check-run-artifacts` / L1 / L2 rc=0（外部红逐条核实）
8. 一键证据脚本（含可达 FAIL 注入：例如让 progress 写入失败 ⇒ 应显式报错）
9. 完成区 ≤30 行、无运行期路径

## 说明

- 协议真源：`docs/Process-09 §16`（不在任务书里另立一套）。
- 节点交互：主控机侧中转文件放 `.work/`，**禁 `/tmp`**；节点操作后 `make sync-node-repo`。
- 构建/调试在主控机；**不要占用 207/208 的长跑时段**（先查 `remote.py status` 的 `running`，有长跑时用 `--dry-run` 或等空闲）。
- 若发现需要改驱动才能按 case 调度，**停下登记并返回主会话**（可能需要先给驱动加 `--only` 支持）。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
