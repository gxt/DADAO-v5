# m12-chipyard-017: 引擎 parity 报告生成器入仓（可复现）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-016`（已合 `3924a248`）
**可并行分片**：否
**预估**：1–1.5 h
**状态**：已验证

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

### 第 1 轮 reviewer 验收（2026-11-15，以 master `f37c6721` 为准；命令均在仓库根独立重跑）

**重跑记录（reviewer 自己的真实输出 / 退出码）**
- `python3 tools/testcases/parity/engine_parity_report.py --check` ×3（根目录 ×2、cwd=`tools/`）⇒ **rc=0**、三次输出 `cmp`=0；json `ada3c375…`、md `31af0c75…`，与 `sha256sum` 入库值相等；报告内**无生成时刻**（仅静态 code-freeze 日期）。
- 确定性：`--out-dir` 连跑 2 次、并与 016 原 `make_report.py`（`TASK_WT`=临时树）产物 `cmp` **全等**（md5 `83de056a…` / `915cbce9…`）。
- `pending`：与 016 原 `pending.py` 输出 `diff` **rc=0**；现场 `79`、`known=234 terminal=155 pending=79 inventory=235`；报告 `embench.cases_seen=32` ⇒ pending 6。
- `run.sh` 检查项 ID 集合 diff = 原集合 **+ `E4`（唯一新增）**；逐行 diff 只剩路径插桩 / `W`→`W2` / 注释，判据与 expected 值未动。
- `engine_parity_run.sh --work-dir <临时>` 实跑 ⇒ **20 PASS / 3 FAIL、rc=1**（C1 38→32、C2 38→32、D6 0→80，E4 rc=0）＝完成区口径。
- 注入（副本路）：`parity.differing` 加 1 条 ⇒ `--check <副本>` **rc=1**、`first differing line 532`；真文件 md5 `83de056a…` 未变、随后 rc=0。
- 证据脚本重跑 <运行期证据目录>/run.sh ⇒ **45 passed / 0 failed、rc=0**（含 R6 注入 rc=1 → `cp`+md5 还原 → 回绿）。
- 门控：`make check-knowledge-refs` **rc=0**、`check-no-residue` **rc=0**、`check-dirs` **rc=0**、`check-run-artifacts` **rc=2**（7 命中全为运行期日志目录里并发会话的 `review-*.log` 残留，本任务 **0 命中**）、`py_compile` 2/2、`bash -n` 2/2 全 rc=0。
- `collect` 落点 = 证据目录下的 `cases/`（非运行期日志目录），日志目录下无 `*-cases`。
- 对账：`f37c6721` = 4 新脚本 + README + 本任务书；4 脚本 md5 分支 `8e88f3f0`↔master 全等；README 差异仅 master 侧 `int_diff` 内容（017 内容无丢失）；`m12-integ-002` 承接 3 条与现场一致（`engine_parity_run.sh:240` 两处 `work/probe`，016 原 `:215` 同形）。
- 快照：验收前后 `git status -uall` 均 0 行、8 个目标文件 md5 未变；未跑 `install-host`/`check-modules`/`build-*`，未动节点、未重跑 embench/picolibc。

**约束核验**：验收 1–7 逐条过（sha、行 532、79/32/6/budget 80 与现场一致）；「不做」面未触碰。报告 json 内宿主绝对路径属「待裁定 1」（`check-knowledge-refs` 只扫 `.md` 故不红），已移交 `m12-integ-002`。

**判决：Needs Revision**（仅 1 条阻断，返工面 = 1 条断言 + 计数回填）
- **R5c 恒真**：`.work/evidence/m12-chipyard-017/run.sh:107` `chk "R5c …" "$PPEND" "$((38 - SEEN))"`，而 `:105` `PPEND=$((38 - SEEN))` —— 两支同一表达式，**指不出任何"改哪里会让它红"的注入点**（DD-Y003 §7「指不出来的断言一律重写」/ 禁恒真），使 45/45 多计 1 条装饰断言。**改法**：改成可红断言（如报告内 `cases_seen` 对 `len(embench.cases)` 交叉，注入点=临时副本增删一例）或直接删除并把完成区计数改 44，随后重跑证据脚本回填。
- **规则层待裁定（阻断面交架构师，不由 reviewer 单判）**：AGENTS「临时目录」段在本轮验收期间被用户改为「**脚本入仓判据 = 会不会再跑**」——共享工具入 `tools/` 且 README 登记一行；**批次一次性编排（`run.sh`/`collect.sh`/注入脚本）⇒ 不入仓**，留运行期证据目录；一次性专用变换代码就近放 `.tao/knowledge/refs/<task>/`。本任务按**旧口径**把 4 个脚本全入了 `tools/testcases/parity/`（README 已登记一行）。须裁定：① `engine_parity_run.sh`/`engine_parity_collect.sh` 是否按新口径迁回运行期证据目录；② `engine_parity_report.py`（`m12-integ-002` 要调用重算）算共享工具还是批次编排；③ README 登记行是否补齐「路径/用途/入口/调用者」四要素。
- 非阻断 finding（记档，收尾顺手改）：① 完成区第 2 条「连跑 3 次（含 …`--node-map` 覆盖那份）逐字节相同」措辞易误读（`--node-map` 那份按设计不同，R4g 正断言其不同）；② `tools/testcases/parity/README.md` `int_diff` 节与 `## engine parity` 节之间缺一空行。
- 其余（可复现、行为差异 0、落点、门控、注入、移交、对账）全部达标。`**状态**` 由主会话置 `待返工`。

### 第 3 轮 engineer 自审（返工第 1 轮）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1（reviewer 阻断）R5c 两支同一表达式 ⇒ 恒真、无可达 FAIL | ✅已修 | 换成「`cases_seen` vs `len(cases)`」交叉校验（声明字段与明细数组两路独立取值）；`38 - cases_seen` 仅留作显示 | 注入删 1 条明细 ⇒ `[FAIL] R5c expected=31 actual=32`、整体 rc=1；`cp` 还原 md5 `83de056a…` ⇒ `[PASS]`、rc=0、`45 passed, 0 failed` |
| P1（排版）`int_diff` 节与 `## engine parity` 节之间缺空行 | ✅已修 | 补 1 个空行 | `git diff` 仅 +1 行 |
| P2（新规则）`engine_parity_run.sh`/`collect.sh` 属批次一次性编排、不该入仓 | ⏸延后 | 按指示本轮不动；完成区「返工（第 1 轮）」第 4 条标注「按 2026-11-15 新规则待迁出」 | `discussing.md` 已有 tools 清理待办（不改，仅引用） |
| P3（返工中发现的移植回归）`MODE` 未初始化 ⇒ `--inject`/`--full` 进参数解析即 `unbound variable`（016 原脚本无此变量） | ✅已修 | 初始化 `MODE=` | `bash -n` rc=0；`--inject` 实跑到 H8（H1–H7 全绿），默认态不受影响 |

判决：阻断项与两条顺手项已处置，P2 按指示延后；本分支已重置到 master，工作树仅剩两处产物改动 + 本任务书 ⇒ 状态 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-15，只核返工面；HEAD `958ad77b`）

**重跑（reviewer 自己的真实输出 / 退出码）**
1. **R5c 可红**：临时 worktree `rv2`@`958ad77b`（`.work` 软链主树）连跑同一证据脚本三态 —— 基线 **42/45、rc=1**（红仅 R3/R6c/R6e，系 08:48 输入刷新致 `--check` rc=1，属 031；R5c `[PASS] 32/32`）；注入（`cp`+md5 `83de056a…`，删 1 条 `embench.cases` 明细、`cases_seen` 仍 32）⇒ **`[FAIL] R5c expected=31 actual=32`**、38/45（新增红 R3b/R9b/R9c = 「入库报告被改」的完整性/范围断言正确报警，非误报）；`cp` 还原 md5 复等、`git status` 干净 ⇒ 回 **42/45 且 FAIL 集合与基线逐条相同**。
2. **`MODE=`**：命中 `engine_parity_run.sh:28`；`bash -n` rc=0、`py_compile` 2/2 rc=0；实跑 `--inject --work-dir <临时>` **无 `unbound variable`**、进 `== H.` 段，**H1–H7 全 PASS**、H8 FAIL（继承缺陷，归 `m12-integ-002`）；其余红 = C1/C2/D6（数据态）+ E4（`--check` rc=1，031 范围）。
3. **合入干净**：`git show 958ad77b --stat` = 本任务书(+18) + `README.md`(+1 空行，`201→203` 交界已有空行) + `engine_parity_run.sh`(+1 `MODE=`)，无夹带、无台账改动；逐文件 diff 即此 3 处；`make check-knowledge-refs` **rc=0**。
4. 主工作树 `git status -uall` 0 行、未提交、未动节点/sim；`rv2` 已 `git worktree remove`（目录已删）。

**判决：Accepted** —— 3 处返工全部核实可达；`--check` rc=1（`m12-chipyard-031` 范围）与 `run.sh`/`collect.sh` 按 2026-11-15 新规则迁出（`discussing.md` 待办）按指示不在本轮范围。

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

**返工（第 1 轮）**：
1. **阻断项（R5c 恒真）已换真断言**：期望 = 报告 `embench.cases` 明细条数、实际 = 报告 `embench.cases_seen`（两路独立取值，不再用 `38 - cases_seen` 定义式）。注入（`cp`+md5）：删 1 条 cases 明细而 `cases_seen` 仍 32 ⇒ `[FAIL] R5c expected=31 actual=32`、整体 **rc=1**；`cp` 还原（md5 `83de056a…`）⇒ `[PASS] expected=32 actual=32`、**rc=0**、`45 passed, 0 failed`。
2. **真实 rc**：证据脚本 `run.sh` **rc=0（45/45）**；`engine_parity_run.sh` 默认态 **rc=1**（仅 C1=32/38、C2=32、D6=budget 80 三处数据未收完而红，A/B/D1–D5/E 全绿、E4 `--check` 通过）；`--inject` **rc=1**（H1–H7 全绿，H8 因继承缺陷 F10 红）。`--check` 两处 sha256 不变（json `ada3c375…`、md `31af0c75…`），两次输出逐字节相同。
3. **移植回归（一行，随返工修）**：`engine_parity_run.sh` 的 `MODE` 未初始化 ⇒ `--inject`/`--full` 进参数解析即 `unbound variable` 退出（016 原脚本用 `$1` 直判、无此变量）；补 `MODE=` 后 `--inject` 可跑。
4. **顺手项①（新规则待迁出）**：`engine_parity_run.sh`/`engine_parity_collect.sh` 属**批次一次性编排**，按 `AGENTS.md`（2026-11-15）新判据**不再入仓、待迁回运行期证据目录**；本轮不动，避免误读为定稿。`engine_parity_report.py`/`engine_parity_pending.py` 属共享工具，留 `tools/testcases/parity/` 并在该目录 README 登记。
5. **顺手项② + 门控**：README 的 int_diff 节与 `## engine parity` 节之间补空行；`check-knowledge-refs`/`check-no-residue`/`check-dirs`/`check-run-artifacts` 全 **rc=0**、`py_compile` 2/2、`bash -n` 2/2。本分支已重置到 master（原两个提交内容已随 squash 合入），工作树仅剩本任务两处改动、无残留。

