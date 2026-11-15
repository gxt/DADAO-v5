# m16-testcases-001: 跑批进度看板 + 增量 JSONL（可见性）

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（`run_embench_e2e.py` / `picolibc_tests.py` 均已在仓）
**可并行分片**：否
**预估**：1–1.5 h
**状态**：已验证

## 背景（用户 2026-11-15 直接提出）

> 「我问的不是为什么这么慢，而是为什么看不见中间状态？」

现场三个具体缺陷（都有证据）：

1. **JSON 只在批次末尾写一次**：`run_embench_e2e.py` 的 `write_json()` 在 `run_suite()` **之后**调用 ⇒ 报表与 `engine_parity_pending.py` 读到的永远是**上一批**；跑到一半时"看不见"是结构性的，不是偶然。
2. **主控机看不到节点实时日志**：跑批的逐例完成行（`PASS bench (-O0) cycles=… 秒`，每例 `flush`）只在**节点**的日志里；主控机那份副本长期 0 字节 ⇒ 主会话据此误报过"还要等 6 例"（实际当时已完成 34/38）。
3. **单例内部无进度**：chipyard sim 只在退出时打印 `cycles=`，跑到一半既无周期数也无 ETA；`ics170` 曾有 6 个 picolibc sim 跑满 **11 h 25 m** 却毫无进度可观测。

## 目标

**A. 进度看板（`tools/testcases/tset/embench/progress.py`，共享工具，入仓并登记索引）**

- 输入：`--hosts <csv>`、每节点 `<repo>`、日志名（embench / picolibc 两套自动识别）；
- 解析节点日志的逐例完成行（`status bench (-opt) cycles=… Ns` / picolibc 的 `PASS/FAIL/BLOCKED`），**并从 `ps -eo etime` + `/proc/<pid>/cmdline` 的 `+loadmem=` 识别正在跑的用例**；
- 输出一张表：**已完成（含 cycles 与墙钟）/ 在跑（已跑时长 + 按历史 cycles 估 ETA）/ 未开始**，并给汇总（`done/total`、吞吐 cycles/s）；
- **只读**：不写节点、不 kill、不改仓库。

**B. 增量落盘（改 `run_embench_e2e.py`，加 `--jsonl-out`）**

- 每完成一例**立即追加一行 JSON 并 `flush`**（字段与末尾 JSON 的 `cases[]` 一致 + `ts`）；
- 末尾的 `--json-out` 保持不变（向后兼容）；
- 报表侧（`engine_parity_report.py`）可选读 JSONL 做增量 union —— **若改动会破坏 `--check` 逐字节复现，则本项只加 JSONL、不改报表**（在完成区写明选择）。

**C. 纪律（写进 `docs/Process-07` 或对应跑批文档 1–2 行）**

- 跑批日志**必须定期从节点取回**再报进度；报进度**禁止引用入库报告的旧值**（本任务背景里的误报就是反例）。

## 验收（逐条贴真实 rc/现场值）

1. `progress.py --hosts …` 在**当前**在跑的批次上给出：已完成的例名 + cycles、在跑的例名 + 已跑时长 + ETA 估算、未开始例数；**与节点日志/`ps` 现场逐条对得上**（贴两侧证据）；
2. `--jsonl-out`：跑一个**小用例**（如 `crc32-O2`，禁止动正在跑的批次）验证每完成一例即出现一行、且与最终 JSON 的对应条目一致；
3. **可达 FAIL 注入 ≥2 路**（`cp`+md5 还原）：① 看板把"已完成"少算一例 ⇒ 汇总与日志不符时报红；② JSONL 写入失败（路径不可写）⇒ 非零退出且不静默；
4. `check-knowledge-refs`、`check-no-residue`、`check-dirs`、`check-tools-index`（若已存在）、`py_compile`、`bash -n` 全 rc=0；
5. `tools/testcases/README.md` 按新规则登记（路径/用途/入口/调用者四要素）；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`issues.yaml`。

## 硬约束

- **不动正在跑的批次**：`server208` 上 4 个 `-O0` 例、`ics170` 上 6 个 picolibc 例正在跑（100% CPU 各占一核），**禁 kill、禁重建 sim、禁 sync/reset 节点仓库**；
- 只改 `tools/testcases/tset/embench/**`、`tools/testcases/parity/engine_parity_report.py`（**仅当**不破坏 `--check`）、`tools/testcases/README.md`、`docs/Process-07*`、本任务书；
- 禁 `install-host`/`check-modules`/`build-*`；不提交 git；注入还原用 `cp`+md5。

## 待裁定

- 无（实现未产生需用户语义裁定的分叉；「不改报表」的选择见完成区）。

## 审阅记录

### 第 1 轮 engineer 自审（实现后）

- 逐行审查 `progress.py`、`run_embench_e2e.py` 改动与证据脚本：只读边界（ssh 仅 `cat/ps`）、SSH 有界且单节点失败不中断、线程下 JSONL 与 stdout 同锁、错误路径非零。
- 自主证据：`run.sh` 0 失败；以下 finding 均当场修复并复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ssh 传参把 `bash -c` 的脚本拆成多参数，节点返回空表 | ✅已修 | 合并为单个 `bash -c <quoted>` 参数 | live 表出现 16+1 done、9 run |
| 孤儿 picolibc sim 被挂到已停的 0 用例旧日志 | ✅已修 | 归属须有 `--only` 点名或该批已有完成行，否则 `(unlogged)` | 5 个 `(unlogged)` + memmem 归 1/1 批 |
| ETA 未减 elapsed，超时例仍显示未来时刻 | ✅已修 | 剩余 = 目标/吞吐 − elapsed；≤0 打 `overdue` | matmult 11h57m → `overdue` |
| `_pico_only_for` 对短名取 `n[5:]` 得空串，匹配所有批 | ✅已修 | 仅 `test-` 前缀才截断 | memmem 只归其批 |
| 批次起始头未 flush，启动阶段 total 不可见 | ✅已修 | 打印 benchmarks 后 `sys.stdout.flush()` | 首例完成前批头（1 benchmark / `['O2']`）已在日志中可见 |
| 证据脚本把历史已完成批计入 live 对账 | ✅已修 | 快照带 mtime、仅活跃批计数；结果文件改覆盖写 | live 4 项 0 missing/invented/ghost/lost |
| 超时历史秒数可能被当 ETA | ✅已修 | 仅 `PASS` 历史秒数可用 | 无 timeout 值进 ETA |

### 第 1 轮 reviewer 验收（2026-11-15，全部本人重跑，不采信完成区）

- **看板**：`progress.py --hosts server208,ics170` ⇒ rc=0；`--expect-done 19` rc=0、`--expect-done 18` rc=1（`ERROR: --expect-done 18 but parsed done=19`）。
- **三侧对账**（同刻节点 `grep` 日志 + `ps -eo etime,args` ↔ 看板，01:01Z）：server208 18 条 done 的 status/cycles/wall 逐条比对 **0 不符**（`edn 74052687 39833.92s`、`matmult-int FAIL 43200.01s`…）；`ps etime 08:00:47` ↔ `run xgboost (-O0) 8h00m`；ics170 `ps 13:11:49`/`13:14:41` ↔ `test-memmem 13h11m`/5 孤儿 `13h14m`；5 个无驱动孤儿如实标 `batch (unlogged) done=0/n/a pending=n/a`（不臆造 total）；`xgboost PASS 117335858 42007.12s` 与节点日志一致；汇总 `done=19 total=21 running=7`。
- **失败处理**：`--hosts server208,no-such-host.invalid --timeout 8` ⇒ 打 `UNREACHABLE` 且 server208 表照出、rc=1（1 s）；两台全死 ⇒ rc=2；黑洞 IP `--timeout 6` ⇒ 5 s 内返回 rc=2（在时限内）。
- **`--jsonl-out` 独立小批**（`--only crc32 --opt O2 --jobs 1`，产物落运行期临时目录、未动在跑批次）：轮询 295×0.05 s 时首行已存在且 `kill -0` 驱动仍活 ⇒ 真增量；`verify.py jsonl --expect 1` rc=0（该行与 `--json-out` 唯一 case 除 `ts` 全等）。
- **独立注入（不复用 engineer 三路）**：把 `parse_ps` 改成 `return [], drivers`（丢掉全部在跑行）⇒ 同一脚本 `run.sh` rc=1、`[FAIL] live: every ps case is shown running or completed … lost 6`；`cp`+md5 还原（`db104f8d5ed60cdb9044e87bda1fdf89` 不变）后重跑 rc=0、39 PASS。
- **证据脚本重跑**：`bash <运行期证据目录>/run.sh` ⇒ rc=0（39 PASS / 0 FAIL，含其自带 2 路注入、死节点不吞表、门控）。
- **只读性**：`grep -nE "kill|pkill|sync|reset|>>|open\("` 在 `progress.py` 仅命中注释；远端脚本只有 `cd/ps/find/stat/tail/echo`；`run.sh` 的 `kill -0` 只打本地驱动 PID。
- **门控（本人跑）**：`check-knowledge-refs`/`check-no-residue`/`check-dirs` rc=0；`py_compile` rc=0；`bash -n` rc=0；`check-tools-index` 在 Makefile 无目标（与完成区一致）；README 四要素齐。
- **快照对账**：`git status --porcelain -uall` 0 行；两交付文件 md5 与开工一致；commit 仅 5 个允许文件，台账/`discussing.md`/`issues.yaml` 未动；完成区 26 行、无运行期路径、状态 `待验收`。

**findings（不阻断，交 architect 收尾改）**
1. 完成区「`engine_parity_report.py --check` 仍 PASS」当前实跑 **rc=1**（入库报告 `pending 6` vs 重生成 `pending 2`）：`--check` 读**运行期**日志副本（mtime 08:48:42/43，晚于提交 08:47:55、早于本人 08:52 开审 ⇒ 非本人写入），生成器两次重生成 sha 相同（`e1999fe1…`/`68667ecd…`）确定性正常，本任务未改 generator 与入库报告 ⇒ 运行期输入推进所致、非本任务引入；建议该句加时点。
2. 证据脚本只对 done/run 的**名字**做三侧对账，`cycles/wall/elapsed/eta` 无数值断言（`grep -E "cycles|wall|elapsed|eta"` 在 `run.sh`/`verify.py` 零命中）——本轮已由本人逐条比对 0 不符；建议后续补数值比对。

**判定：Accepted**（验收 1–6 在本人重跑下全部通过、硬约束无违反；上述 2 条属文档/断言覆盖层面，按「文档级小错」记录不返工）。

## 完成区

**测试结果**：证据脚本 0 失败（live 对账 4 项、快照 `done=16` 对 grep、2 路注入+还原、single/multi JSONL、门控 5 项）；`engine_parity_report.py --check` 仍 PASS（未改报表，选择理由见下）。

**修改文件**：
- `tools/testcases/tset/embench/progress.py`（新增，只读看板）
- `tools/testcases/tset/embench/run_embench_e2e.py`（`--jsonl-out`、`case_row()` 复用、起始头 flush）
- `tools/testcases/README.md`（四要素登记）
- `docs/Process-07-门控分层规范.md`（§2.2 两行纪律）

**验收结果**：
1. 现场对账（`--hosts server208,ics170` 与同时刻日志/ps）：日志 `PASS  edn (-O0) ... cycles=74052687 39833.92s` ↔ 表 `PASS edn (-O0) 74052687 39833.92s`；ps `+loadmem=.../O0/matmult-int.elf`（etime 11:57:06）↔ 表 `run matmult-int (-O0) 11h57m`，depthconv/xgboost 同；ics170 `+loadmem=.../test-iconv.elf` 等 6 个 ↔ 表 `run test-iconv ...`（5 个无驱动日志者标 `(unlogged)`，memmem 归 1/1 批）。程序化交叉校验 0 缺失/0 臆造。
2. JSONL：单例 `crc32-O2` → 1 行，与 `--json-out` 唯一 `case` 逐字段相同（除 `ts`）；3 例批次轮询到「首行出现时驱动仍存活」，3 行与最终 JSON 全等、每行带 UTC `ts`。
3. 注入：① 解析器 `PASS`→`PASSX`（cp+md5）⇒ `--expect-done 16` 报 `done=0`、rc=1；还原后 md5 相同、rc=0。② `--jsonl-out /dev/null/x.jsonl` ⇒ rc=2 且打印 `cannot open --jsonl-out`。另：死节点不吞表（rc=1 仍打印 server208 批）。
4. 门控 rc：`check-knowledge-refs` / `check-no-residue` / `check-dirs` / `py_compile` / `bash -n` 全 0；`check-tools-index` 不存在（Makefile 无此目标）。

**新发现/坑**：
- picolibc 驱动只在**首例完成**时 flush，全量批启动到首例之间日志 0 字节 ⇒ 看板只能靠 `ps` 报在跑、`total=n/a`；`picolibc_tests.py` 不在本任务允许范围，未改。
- ics170 5 个 picolibc sim 无对应驱动/日志（孤儿），看板归 `(unlogged)`，不臆造批归属与 total。
- ETA 超历史估算时打 `overdue`（不猜 0）；无历史/同类数据打 `n/a`；`known-total` 与 `unknown-total-batch` 分开报。
- 报表不改的选择：JSONL 是过程证据；`engine_parity_report.py --check` 现为 PASS，改报表须重生成入库报告、且可能破坏逐字节复现，收益不抵风险 ⇒ 本项只加 JSONL。

**遗留问题**：
- 若要让 picolibc 批「启动即可见 total」，应在 `picolibc_tests.py` 起始头加 flush（越界，建议另立任务）。
- 看板以「未完成 或 180 min 内有更新」判活跃批，跨日中止批默认不显示（`--window` 可调）。

