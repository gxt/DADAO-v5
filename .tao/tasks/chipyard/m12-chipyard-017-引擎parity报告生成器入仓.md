# m12-chipyard-017: 引擎 parity 报告生成器入仓（可复现）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-016`（已合 `3924a248`）
**可并行分片**：否
**预估**：1–1.5 h
**状态**：待验收

## 背景（AGENTS 硬规则缺口）

`m12-chipyard-016` 把**报告产物**入库（`.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}`），但**生成器没入库**：`make_report.py` / `pending.py` / `collect.sh` / `run.sh` 只存在于 016 的运行期证据树（未入库，见其完成区）。

违反 AGENTS「生成器/脚本随产物保留：凡产出**被提交（入 git）**的生成器/脚本，必须随产物留**非易失位置**（优先 `tools/<module>/`）」⇒ 现在 fresh clone 上**无法复现**已提交的报告，`m12-integ-002` 的「证据可复跑」判据也就落不了地。

## 范围

1. **搬家不改逻辑**：把四个脚本落到 `tools/testcases/parity/`（与 `fp_diff.py` 同族，具备 `--check` 可复现约定的目录），保持文件名语义：
   - `make_report.py` → `tools/testcases/parity/engine_parity_report.py`
   - `pending.py` → `tools/testcases/parity/engine_parity_pending.py`
   - `collect.sh` → `tools/testcases/parity/engine_parity_collect.sh`
   - `run.sh` → `tools/testcases/parity/engine_parity_run.sh`
2. **接口去运行期耦合**：默认输入目录从「脚本自身所在的 `../..`」改为 `--repo <根>`（默认 = 该脚本相对仓库根）+ `--log-dir`（默认 = 仓库内 chipyard 模块的运行期日志目录）；节点名保留但可 `--node-map` 覆盖（保持原有默认值，行为不变）。
3. **可复现校核**：`python3 tools/testcases/parity/engine_parity_report.py --check` 在**当前**数据上重生成，与已提交的 `.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}` **逐字节一致**（打印 sha256 对账）；不一致就说明有未入库的输入，必须查清再报。
4. **不重复造轮子**：报告口径（`CRITERION`/`QEMU_BASELINE_GAPS`/union 规则/budget 单列/`cases_seen`）一律**照搬 016**，不得改写判据；只允许改路径解析与入口形态。

## 验收（逐条贴真实 rc/现场值）

1. 四个文件已入 git（`git ls-files` 现场），`grep` 证明运行期证据目录不再是唯一副本；
2. `engine_parity_report.py --check` ⇒ **rc=0**、逐字节一致（贴两个 sha256）；**重跑两次**结果相同（确定性）；
3. `engine_parity_pending.py` 能列出当前 pending（现场值：embench `cases_seen` 与 pending 数）；
4. **1 路可达 FAIL 注入**（`cp`+md5 还原）：把报告里 `parity.differing` 的一条状态改坏 ⇒ `--check` rc≠0 且指出差异位置；
5. `check-knowledge-refs` rc=0（脚本内注释/文档里**不得**出现具体 `.work/**` 路径）；`check-no-residue` rc=0；`check-dirs` rc=0；
6. `python3 tools/infra/check_script_hygiene.py`（若存在该门控）或等价 `py_compile` + `bash -n` 全通过；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；只在本任务 worktree 内改动。

## 明确的「不做」

- **不动**报告数值与判据（32/38、budget 81 等是数据未收完，属 `m12-integ-002` 前的数据补齐，不归本任务）；
- 不改 `tools/testcases/lib/chipyard_engine.py`、`picolibc_tests.py`、`run_embench_e2e.py`；
- 不重建、不重跑 embench/picolibc 全量（节点上 `-O0` 夜跑仍在进行，**禁抢节点**）；
- 不改 016 的任务书与审阅记录（其「遗留问题」里的旧路径由 `m12-integ-002` 报告指认新位置）。

## 待裁定

1. **报告 JSON 里的宿主绝对路径**：`picolibc_chipyard.cases[].sim_log` / `semi_out` 是 runner
   写入的宿主绝对路径（`/home/ubuntu/…`），**不是**本生成器产生的。清洗它们会破坏与已入库
   报告的逐字节一致（本任务的 `--check` 判据），且属 016 的 runner 口径 ⇒ 本任务不动。
   建议由 `m12-integ-002` 决定是否让 runner 改写相对路径后重生成一次报告。
2. **两条 L1 门控在基线上就是红的**（与本任务改动无关，均非我写入）：
   `check-knowledge-refs`（1 命中：`m13-chipyard-002` 任务书第 78 行的具体运行期路径）；
   `check-run-artifacts`（7 命中：并发会话留下的 `.work/log/linux/review-*.log`）。
   按「他册残留先判归属，不代删、不凑绿」保留现场，见完成区验收 5。

## 审阅记录

### 第 1 轮 engineer 自审

自审范围：本任务新增的 4 个脚本 + README 节 + 本任务书。逐行核对「行为与 016 一致」：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 原 `make_report.py` 把 `json.dump` 直接写文件，无法在 `--check` 里复用序列化结果 | ✅已修 | `build()` 先出 `payload` 串再落盘 | 输出 sha256 与 016 产物相等（167599 B） |
| F2 原 `run.sh` D 段 `mapfile -t W` 覆盖 B 段 `W`（探针目录）变量 | ✅已修 | 改名 `W2` | `bash -n` + 实跑 A/B/D/E 全绿 |
| F3 原脚本用 `TASK_WT` 环境变量定向输出，属运行期耦合 | ✅已修 | 改 `--repo/--log-dir/--out-dir/--node-map` | R4c（cwd=`tools/`）与 R4a/b 逐字节同 |
| F4 `pending` 缺输入时会抛 traceback（原脚本行为） | ✅已修 | 缺 qemu 清单 ⇒ 打印 SETUP 并 rc=2 | 现场跑缺输入目录 rc=2 |
| F5 `collect` 落点原在 `.work/log/<TASK>-cases/`（嵌套命名，违 L1 A3 平铺约束） | ✅已修 | 默认改 `.work/evidence/<TASK>/cases/`，注释写明理由；README 同步 | R8d/R8e/R8f + `make check-run-artifacts` 归因（本任务 0 命中） |
| F6 自审期误跑一次原 `make_report.py`（未设 `TASK_WT`）写入了主工作树的已入库报告 | ✅已核 | 无代码改动 | 报告 sha256 与入库值相同、`git status` 该路径为空 |
| F7 证据脚本 R1b/R9c 依赖「未入库」状态，WIP 提交后会假红 | ✅已修 | 改 `git ls-files --cached --others` 兼容两态 | 提交后重跑 45/45 PASS |
| F8 `--node-map` 若只解析不使用 ⇒ 静默无效参数 | ✅已修 | 增 R4g/R4h：改一档分片节点，用例数随之迁移、其余档为 0 | 15↔15、0 |
| F9 注释/文档里出现具体运行期路径会被 `check-knowledge-refs` 判红 | ✅已修 | py 文档串改「仓库内 chipyard 运行期日志目录」，collect 用 `<TASK>` 占位 | R8c 本任务 0 命中 |

判决：F1–F9 全部已修/已核，无未修 finding ⇒ 状态置 `待验收`。

### 第 2 轮 engineer 自审（第二次接手，独立复核）

接手时本树已有未提交的完成区，且接手期间仍有另一写者向本树落盘（任务书 mtime 06:40:01、证据日志 06:40:09 均非本人产出）。为免两个写者在同一 worktree 竞争，本轮**不改代码**，只独立复核既有产物与结论。

- **接口齐备**：report `--repo/--log-dir/--out-dir/--node-map/--check [PATH]`；pending `--repo/--log-dir`；collect `--repo/--dest/--remote-repo/--node-map`；run `--repo/--log-dir/--work-dir/--full/--inject`。四个文件 `TODO|FIXME|占位` grep = 0 ⇒ 无半成品。
- **逐字节复现**：`--check` 连跑两次 rc=0 且两次输出完全相同；json `ada3c375…`、md `31af0c75…`，与 `sha256sum` 独立值相等。
- **与 016 行为差异（对账法）**：同一输入下，016 原 `make_report.py`（`TASK_WT` 定向到临时树）与本生成器 `--out-dir` 的产出**两份文件 `cmp` 全等**（md5 `83de056a…`/`915cbce9…`）；`pending` 与原脚本输出 `diff` 为空；`run.sh` 检查项 ID 集合 = 原集合 + E4（新增 `--check` 项），判据未动。
- **可达 FAIL**：复制报告并改坏 `parity.differing` 一条（`asctime` pass→fail 并入 differing）⇒ `--check <副本>` rc=1、`first differing line 532`（与第 1 轮同位置）；入库文件未动，`--check` 随后 rc=0。真文件那一路（`cp`+md5 还原）由证据脚本 R6 覆盖，本轮亲手重跑亦为红→绿。
- **一键证据**：亲手重跑证据脚本 ⇒ `45 passed, 0 failed`、rc=0；报告复原 `ada3c375…`。
- **门控**：`check-no-residue`/`check-dirs` rc=0；`check-run-artifacts` 7 命中全为并发会话留下的 `.work/log/linux/review-*.log`；`check-knowledge-refs` 1 命中在 `m13-chipyard-002` 任务书 ⇒ 本任务 0 命中。

| finding | 处置 | 说明 | 复验证据 |
|---------|------|------|---------|
| F10 `engine_parity_run.sh` H8 用相对仓库根的 `work/probe/t.elf`，而探针实际落在 `$WORK/probe` ⇒ 可选 `--inject` 模式的 H8 无可达 PASS 路径。**与 016 原脚本同一行同缺陷，非本次移植引入** | ⏸延后 | 只影响 `--inject`；修法 = 该行两处改 `$WORK/probe/…`；须在节点/语料空闲时用 `--inject` 验证，本轮禁跑 | 仓库根无 `work/` 目录；016 原脚本第 215 行同形 |
| F11 本分支基线落后 master 35 个提交（领先 1 个 WIP）；`check-knowledge-refs` 的红正是基线陈旧所致（master 已把该行改为「运行期证据目录」措辞） | ⏸延后 | 收尾前须先把分支同步到 master 再 squash；**按现状直接 squash 会连带回退 master 近 35 个提交（157 个文件）** | `git rev-list --count HEAD..master`=35；`git diff --name-status master..HEAD \| wc -l`=157 |

判决：F10 属继承缺陷（超出本任务验收面，建议转 `m12-integ-002`）；F11 是收尾路径问题（归架构师）。本轮未改代码 ⇒ 不改变第 1 轮判决与 `**状态**`。

## 完成区

**测试结果**：一键证据 `run.sh` **45/45 PASS、rc=0**；移植后的 `engine_parity_run.sh` A/B/E 全绿，C1/C2/D6 因数据未收完（`cases_seen` 32/38、budget 80）按 016 原判据报 FAIL（数据态，非回归）。
**修改文件**：新增 `tools/testcases/parity/engine_parity_{report.py,pending.py,collect.sh,run.sh}`；改 `tools/testcases/parity/README.md`（脚本清单 + 「engine parity 报告」节）；本任务书（背景措辞、待裁定、完成区、审阅记录、状态）。
**验收结果**：
1. `git ls-files tools/testcases/parity/ | grep engine_parity` ⇒ 4 行（report.py / pending.py / collect.sh / run.sh）。
2. `engine_parity_report.py --check` **rc=0**：json `ada3c375c904bd06b4af842b63248fc7f9f365b6b70b54775e58e37f5970e1ee`、md `31af0c752c8109f027dc1f3d6e4516cab39c3419e0483e5f4882cc77dd5d5672`（入库 = 重生成）；连跑 3 次（含 cwd=`tools/`、`--node-map` 覆盖默认那份）逐字节相同。
3. `engine_parity_pending.py` 现场：`79`；`known=234 terminal=155 pending=79 inventory=235`；embench `cases_seen=32`、pending 6（=38−32）。
4. 注入 A（报告侧：`asctime` pass→fail 并入 `parity.differing`）⇒ `--check` **rc=1**、`first differing line 532`；`cp`+md5 还原（`83de056a…`）⇒ **rc=0**。注入 B（输入侧临时日志树）⇒ 派生 `parity.differing` 现场变 `asctime`、`--check` rc=1。
5. 门控：`check-no-residue` rc=0、`check-dirs` rc=0；`check-run-artifacts` 本任务 **0 命中**（整体 rc=2 系并发会话留的 7 个 linux review 日志）；`check-knowledge-refs` 本任务 **0 命中**（整体 rc=1 系 m13 任务书 1 处具体路径）；`py_compile` 2/2、`bash -n` 2/2 全过。
6. **与 016 行为差异 = 0**：报告两份 sha256 与 016 产物相等（对账法 = 逐字节 `--check`）；`pending` 与原脚本输出 `diff` 为空；`collect`/`run` 与原脚本逐行 `diff` 只剩路径插桩（`--repo`/`--dest`/`--work-dir`/`--node-map`），检查项名字与判据未动。
**新发现/坑**：L1 `check-run-artifacts` A3 的平铺命名会把任何 `<log-dir>/<TASK>-cases/<node>/…` 判红 ⇒ 逐例证据树一律落 `.work/evidence/<TASK>/cases/`；脚本入仓时路径推导只走 `--repo`，别用环境变量或 `git rev-parse` 当主路径（否则 fresh clone 上飘）。
**遗留问题**：① 报告 JSON 的 `sim_log`/`semi_out` 仍是 runner 写入的宿主绝对路径（「待裁定 1」，留 `m12-integ-002` 决定是否改相对路径后重生成）；② 两条 L1 门控的基线红命中归他任务/并发会话（「待裁定 2」），本任务未代改、未凑绿。

