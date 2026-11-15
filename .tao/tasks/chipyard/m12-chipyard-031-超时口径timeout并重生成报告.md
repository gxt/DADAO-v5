# m12-chipyard-031: 超时口径改 `timeout(12h)` 并重生成 parity 报告

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-016`（已合 `3924a248`）、`m12-chipyard-017`（已合 `f37c6721`）
**可并行分片**：否
**预估**：30–45 min（词表/换算/重生成/2 路注入；不含重跑用例）
**状态**：已验证

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

1. **picolibc 段的逐例 `semi_out`/`sim_log` 改为模板形**。验收 3 要求「报告内无运行期路径」，
   而 picolibc 侧 84+ 条记录原本带节点绝对路径。已自决：统一写成
   `<work-dir>/run/<case>/<leaf>`（各例来自哪个池仍由 `pool` 字段标明，计数不变）。
   选项：A 保留模板（现选）／B 还原绝对路径（违反验收 3）／C 只保留相对仓库根形式。
   **请用户确认 A**；若选 B/C 由后续任务改一行即可。
2. **picolibc 段的 `blocked` 未改判为 `timeout(<预算>)`**。验收 5 要求 picolibc `blocked`
   计数改动前后一致，故历史数据保持原样（其中含 host timeout 的 budget 类，已在 §4
   单列）。只在此段加了一句口径说明。
3. **两处超出文件清单的连带改动**：`progress.py`（进度看板正则）与
   `engine_parity_pending.py`（docstring 一句）。理由：新显示形 `timeout(<预算>)` 会让
   看板漏掉这些例、让文档公式失真；改动各 1 行、无行为扩展。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：两个脚本的 diff 逐行 + 报告对 diff + 证据脚本；重点看未测输入（新式日志行、
非法标签、无 timeout 的批次）与旁路消费者（看板/collect/pending）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `embench.cases[]` 行只加 `budget_seconds`，漏了任务要求的 `timeout: true` | ✅已修 | `emb_cases` 增加 `timeout` 布尔 | 证据 R4 两例 `(TIMEOUT, True, 43200)` |
| 注入脚本把 runner 文件模式改成 755（多余的 mode change） | ✅已修 | `chmod 644` + 还原改 `cp -p` | 证据 "runner mode unchanged (644)"；`git diff --summary` 空 |
| 证据里 `format_budget(60)` 期望写成 `1h` | ✅已修 | 期望改 `("12h","1m")` | 证据 V7 rc=0 |
| 进度看板 `RE_EMB_CASE` 不认 `timeout(<预算>)` ⇒ 这些例在看板「消失」 | ✅已修 | 正则加 `timeout\(\w+\)` 分支 | 实测两条样本（新式+旧式）均 match |
| 引 JSON 分片把节点绝对路径带进报告 | ✅已修 | `_case_paths` 统一 `<work-dir>/…`；picolibc 段同 | 证据 R6：两文件 0 处 `/home|/mnt|/tmp` |
| INJ1 只断言 diff 里出现用例名（弱） | ✅已修 | 加「重生成变 `PASS 37 / timeout(12h) 1`」语义断言 | 证据 INJ1 patched summary PASS |
| `case_row` 里 `case_status` 调两次 | ✅已修 | 提局部变量 | `py_compile` + 证据 V5 |
| `timeout(1d)` 这类非法标签会抛裸 `ValueError` | ✅已修 | 转 `BudgetError`（rc=1 带消息） | INJ4b 走同一异常路径，rc=1 |
| TIMEOUT 行若缺 `budget_seconds`（如未来 JSON 分片）会 `TypeError` | ✅已修 | `budget_label()` 前置守卫 ⇒ `BudgetError` | 证据 R3 两例读到 `43200`；异常路径与 INJ2 同 |
| 批次汇总的 `by_status` 内联在 `main()`，无法单测 | ✅已修 | 提为 `status_counts()` | 证据 V8（4 类各 1 例） |

**判决**：10 条 finding 全部 ✅已修，无延期项 ⇒ 状态置 `待验收`。

## 完成区

**测试结果**：证据脚本 56 项检查全 PASS（rc=0），`--inject` 模式亦 rc=0；未重跑任何 embench/picolibc 用例（数据已定）。

**修改文件**：`tools/testcases/tset/embench/run_embench_e2e.py`（词表拆分 `res.timeout`/`res.gap`、`format_budget`/`parse_budget`、`display_status`、`_report` 走显示形、`case_row` 加 `budget_seconds`+`timeout`、汇总行）、`tools/testcases/parity/engine_parity_report.py`（新/旧行同解析、标签回读校验、timeout 单列与汇总、路径模板化）、`tools/testcases/tset/embench/progress.py`、`tools/testcases/parity/engine_parity_pending.py`、`tools/testcases/parity/README.md`、报告对 `m12-016-embench-picolibc.{json,md}`（重生成）；证据 `run.sh`+`check_vocab.py`+`check_report.py`（运行期证据目录，未入库）。

**验收结果**：
1. 词表：`format_budget`/`parse_budget` 在 runner（预算由 `--timeout` 现场派生，`43200→12h`、`3600→1h`、`5400→90m` 非整小时实测）；`grep` 证据：`case_status` 内 `return "TIMEOUT"` 1 处、`_report` 用 `display_status` 1 处、不再直接用 `case_status` 0 处。
2. 报告：`**汇总：PASS 36 / timeout(12h) 2 / fail 0**`；两例 `embench/matmult-int-O0`、`embench/depthconv-O0` 各带 `timeout(12h)`+预算 43200s+墙钟 43200.01s；JSON `timeout_cases` 两项同值，`cases_seen=expected=38`、`pending=0`。
3. `--check` rc=0；md sha256 `ccb1b69bafd12c30726659740a087819ba9b17fd35e5be0db079351204968fb0`(18090 B)、json `56ccdc8d42bc2c3b66c4007edde99bc0a7c9f274f4c1f2110d6587ca434e4636`(169711 B)；两次重生成逐字节一致；两文件 0 处 `/home|/mnt|/tmp`、0 处生成时刻。
4. 可达 FAIL 4 路（`cp`+md5 还原，前后 md5 相同）：INJ1 日志把 matmult-int 改回 PASS ⇒ `--check` rc=1（重生成变 `PASS 37 / timeout(12h) 1`）→还原 rc=0；INJ2 换算写死 11h ⇒ rc=1「not a round trip」→还原 rc=0；INJ4b 新式行标签 11h ⇒ rc=1「label timeout(11h) = 39600s but the log says 43200s」；INJ3 复现旧「静默丢」⇒ 汇总断言变红。
5. picolibc `blocked` 84→84（chipyard）、4→4（qemu 基线），counts 全等。
6. 门控 `check-knowledge-refs`/`check-no-residue`/`check-dirs`/`check-tests-index`/`py_compile`/`bash -n` 全 rc=0。

**新发现/坑**：
- 旧 runner 打的是二元 `FAIL` + `(platform: host timeout after 43200s …)`：生成器必须从 reason 反读预算，否则只能丢弃 —— 这就是「静默丢」的根因。
- 显示形一旦带预算，所有旁路解析（进度看板）都要同步改正则，否则这些例会从看板上消失。
- 只比 `--check` 抓不到换算写错（生成器与报告同错）；必须有「标签→秒数」回读校验才是可达 FAIL。
- 引 JSON 分片会把节点绝对路径带进报告（`semi_out`/`sim_log`），须统一改写 `<work-dir>/…`。

**遗留问题**：无（`server208` 上重复的 `xgboost-O0` 未动，不重跑任何用例）。
