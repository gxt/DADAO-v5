# m12-chipyard-031: 超时口径改 `timeout(12h)` 并重生成 parity 报告

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-016`（已合 `3924a248`）、`m12-chipyard-017`（已合 `f37c6721`）
**可并行分片**：否
**预估**：1–1.5 h
**状态**：待开始

> 编号说明：`m12-chipyard-018` 已被「核心结构改造：双 TL 端口 + 8-beat 取指 + FSM 骨架」（已验证）占用，本任务取 **031**。

## 用户裁定（2026-11-15，原话）

> 「blocked 容易让人误解，timeout（12h）如何？」

⇒ 预算耗尽的用例，状态标签一律用 **`timeout(<预算>)`**（如 `timeout(12h)`），**不再用 `blocked` 表示预算类**。`blocked` 只保留给"构建/环境缺口"（如 `ISS-193` long-double、CFX6 缺载体）。

## 背景（现场）

`-O0` 夜跑（12 h 窗口，`--timeout 43200`）结束后：

- **36/38 PASS**；`matmult-int-O0`、`depthconv-O0` **打满 43200 s 无 guest 判决**；
- 日志显示 `FAIL … (platform: host timeout after 43200s (no guest verdict))`（`server208` 上跑的是旧版 runner：`_report` 只做 `PASS/FAIL` 二元显示），但 `write_json` 走 `case_status` ⇒ JSON 记 `BLOCKED`；
- 报告生成器 `engine_parity_report.py` 从日志解析时**直接丢弃超时行**（只收有 `cycles` 的行）⇒ 报表 `cases_seen=36`、`pending 2`，**没有把这两例作为一类列出** ⇒ 属"静默丢"。

## 任务

1. **状态词表加 `TIMEOUT`**（机器值）与显示形 **`timeout(<预算>)`**：
   - `run_embench_e2e.py`：`case_status()` 中"host timeout（无 guest 判决）"⇒ `TIMEOUT`（不再与 `platform:` 一起归 `BLOCKED`）；`_report()` 用 `case_status` 而非二元 `PASS/FAIL`；JSON 每例带 `budget_seconds`（从 `--timeout` 现场取，**不写死 43200**）与 `timeout: true`；
   - **预算时长必须现场派生**：`43200s → 12h`、`3600s → 1h`；非整小时用 `timeout(90m)` 形式（给换算规则并测一例）；
   - `blocked` 语义收窄为"构建/环境缺口"，文档与报告各配一句区分说明。
2. **报告生成器**：`tools/testcases/parity/engine_parity_report.py` 的 embench 段必须把超时例**作为一类列出**（`timeout(12h)`），不得丢弃；汇总行形如 `PASS 36 / timeout(12h) 2 / fail 0`。
3. **parity 判据不变但要说清**：`timeout` 属**无判决**，不参与"逐例状态一致"比较（与 `blocked(budget)` 同口径），**不计入 chipyard 独有失败**；报告里必须显式写明。
4. **重生成入库报告**：`.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}` 按最终数据重生成；`engine_parity_report.py --check` 必须 **rc=0**（当前 rc=1，因运行期日志在 08:48 被刷新、入库报告停在 01:01 的 32 例版本）。

## 验收（逐条贴真实 rc/现场值）

1. 词表改动：`grep` 证明 `TIMEOUT` 在 `case_status` 与 `_report` 生效；`timeout(12h)` 由预算现场换算（贴换算位置 + 一例非整小时测试）；
2. 报告重生成：embench 段现场计数 `PASS 36 / timeout(12h) 2 / fail 0`，两例逐条列名（`matmult-int-O0`、`depthconv-O0`）且带预算与墙钟；
3. `engine_parity_report.py --check` **rc=0**、两次重生成逐字节一致（贴 sha256）；报告内**无生成时刻、无运行期路径**；
4. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 把某例 `timeout` 改回 `PASS` ⇒ 报告与日志不符应报红；② 预算换算写错（12h→11h）⇒ 标签与现场不符应报红；
5. `blocked` 语义收窄未影响既有 picolibc 统计：picolibc 段 `blocked` 现场值与改动前一致（贴前后值）；
6. 门控：`check-knowledge-refs`、`check-no-residue`、`check-dirs`、`py_compile`、`bash -n`、`check-tests-index` rc=0；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`issues.yaml`。

## 硬约束

- 只改 `tools/testcases/tset/embench/run_embench_e2e.py`、`tools/testcases/parity/engine_parity_report.py`、`.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}`（重生成）、相关 README/文档、本任务书；
- **不重跑任何 embench/picolibc 用例**（数据已定：36 PASS + 2 timeout）；`server208` 上仍有 1 个重复的 `xgboost-O0` 在跑，**禁 kill**；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原用 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
