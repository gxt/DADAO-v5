# m13-testcases-001: static 长尾 72 例 × 3600s + QEMU/gem5 运行时间比率

**模块**：testcases
**项目里程碑**：M13
**依赖**：`TESTCASES-103t`（static 基线 + 1200s 复测，已给出「72 例仍 timeout」名单）
**可并行分片**：否（单机 48 并发跑批；测时间要求进程独占核）
**状态**：已验证

## 用户裁定（原话）

「M13准备专门进行多方测试的差分对比，可以先从gem5的超时问题做起，放到208节点机上，48并行（甚至60并行，你觉得呢）；建立专门的任务，跑3600s，甚至7200s，我们测试一下qemu和gem5的运行时间的比率，对不同的任务是否具有可比性。该任务（或者你可以分解多个任务）不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」

## 背景（事实）

- `TESTCASES-103t`：static 档 300/600s 下 **97 例 timeout**；1200s 复测后 **72 例仍 timeout**（23 例转 PASS）。
- 现有 `run_seconds` 只记录被测引擎自身耗时，**没有 QEMU 侧同例计时**，无法判断「gem5 慢多少倍」。
- 208 有 64 vCPU；48 并发为推荐值（留 16 核给内核/IO），**不宜 60**（时间测量会被调度/带宽争用污染）。

## 目标

1. **只记录，不修改**：对那 72 例（名单来自 103t 的 1200s 复测）用 **gem5 SE 3600s** 预算重跑；**同例 QEMU 也计时**。
2. 输出每例：`case` / `gem5_seconds` / `qemu_seconds` / `ratio = gem5/qemu` / `gem5_klass` / `exit`。
3. 统计：比值的分布（min/median/max/P90）、异常离群、与用例类别的相关性（如纯浮点 vs 字符串）。
4. 判定「QEMU/gem5 时间比率是否可作为跨用例的可比指标」——**只给数据与观察，不做裁定**。

## 验收标准

1. 72 例全部有 `gem5_seconds` 与 `qemu_seconds`（缺一即 FAIL，不得静默跳过）
2. 输出 JSON + Markdown 落 `.tao/knowledge/refs/m13-001-static-longtail.json/.md`
3. 报告含：逐例表、比值分布、离群说明、**执行环境指纹**（节点、并发数、gem5/qemu 二进制 md5、musl HEAD、CPU 型号）
4. 重复性：抽 3 例各跑 2 次，方差 < 5%（否则报告标注「时间不可比」）
5. **不改** gem5/QEMU/测试资产/用例与期望；`git status` 只含本任务书与 `refs/` 新文件
6. 完成区 ≤30 行、无运行期路径

## 执行方式（长任务）

- **48 并发**、`server207` 或 `server208`（按 `remote.py status` 选空闲者；同一时段该机不得有构建负载）
- 跑批由**主会话**启动 background，落 PID/日志/`*_EXIT`；engineer 只准备脚本与配置
- 预计：72 例 × 3600s ÷ 48 ≈ **1.5 h**（加 QEMU 计时约 1.5–2 h）

## 非范围

- 不分析根因、不调试、不改任何源码
- 不修改 `PICOLIBC_KNOWN_BLOCKED` 或任何门控
- 不跑 dynamic（`m13-testcases-002`）

## 完成区

**测试结果**：自测 46/46；证据脚本 PASS（16 项；注入 rc=1→还原 rc=0）；pilot 3 例×2 次全完成、最大相对极差 **2.55%<5%（可比）**；`make check`（L1）4 红（2 条为本任务台账行、2 条为环境缺安装根；合并 master 后台账 2 条自消）；`compileall tools`/check-run-artifacts/check-temp-dirs/check-tasks/check-knowledge-refs 绿。

**修改文件**：新增 `tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py`（只编排+聚合，复用三个 tset 驱动与其 `--filter`/`--only`，无引擎代码；未改驱动/源码/用例/期望/门控）；本任务书。

**验收结果**：
- 选例 `timeout_recheck.<suite>.still_blocked` = 72（libc 2 + llvm 70），逐例 `gem5_capability="time budget"`。
- pilot（jobs=3、3600s、3 例×2 次）：gem5 2370.7/1267.0/1782.3 s，qemu 4.92/3.02/1.97 s，ratio 481.9/419.5/904.7；极差 ≤2.55%。
- 节点 qemu 侧（server208、jobs=48）：72/72 pass，矩阵 `run_seconds` 中位 **40.59 s**（去 0 后 41.42）、max 1081.2 s；2 例 0.00 s（`ratio` 记未定义，不计缺失）。
- 指纹：节点/并发/CPU/gem5-qemu md5+版本/musl HEAD/驱动 md5/loadavg。

**新发现/坑**：
- 72 例全为预算耗尽，与 103t 一致。
- 比值强依赖用例：pilot（qemu 2–5 s 的例）ratio 419–905；103t 的 1200 s 全量驱动 JSON（运行期产物）135 个未超时 llvm 例 ratio 25–811、中位 228 ⇒ 不能当常数。
- 绝对时间随主机/并发变：`matrix` 节点 jobs=48 为 5.2 s、主控机 jobs=3 为 1.97 s ⇒ 只有同一次运行内的比值可比。
- 两节点均无 gem5.opt（`.work/source/gem5` 未构建）；节点仓库落后且有 13 个未提交改动（submodule patch WIP）⇒ 同步/重置须属主裁定。
- 本 worktree 的 L1 无法全绿：缺 `.dadao` 安装根（`check-width-sizes`/`check-components` 2 红）。

**遗留问题**：
- 全量 72 例未跑（由主会话启动）；节点缺 gem5，须先 `make build-gem5 JOBS=32`（20–40 min，只写构建树）。
- 启动：`run_engine_ratio.py --repo-root <节点仓库> --case-list <运行期目录>/case-list.json --work-dir <运行期目录>/work --json-out <运行期目录>/result.json --md-out <运行期目录>/result.md --jobs 48 --gem5-timeout 3600 --qemu-timeout 3600 --resume`，`setsid nohup` + `*_EXIT`；`--resume` 复用已测 qemu 轮；预计 gem5 轮≈2 h、含构建≈2.5–3 h。
- 结果落 `.tao/knowledge/refs/m13-001-static-longtail.json/.md`。
- pilot 在主控机（节点无 gem5）⇒ 只证逐主机可重复性；需时可对 3 个未截断例在节点补做 2 次。
- L1 余 3 红：INTEG-061t 台账行（其属主处置）+ 本 worktree 缺安装根 ×2（需 `make install-host`）。

## 审阅记录

### 第 1 轮 engineer 自审（逐行）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 两引擎都测到但某侧时间四舍五入为 0.00 s 时，`ok` 被判 false ⇒ 全量会因 2 个 libc 例误 FAIL | ✅已修 | 以「两侧 `*_seconds` 均非 None」为验收口径；比值未定义时写 `ratio_undefined` 并保留行 | 自测新增 3 项（`zero-qemu leaves ratio null / is flagged / still ok`），46/46 |
| F2 Markdown「两引擎都有测量」用 rows−len(missing) 计数（missing 是条目数不是行数） | ✅已修 | 改为现场统计两侧均有值的行数 | 自测 46/46；pilot.md 显示 3/3、缺失条目 0 |
| F3 `gem5.opt --version` 不支持，指纹 `gem5_version` 取到 "Usage" | ✅已修 | 从 per-case `sim.log` banner 解析 `gem5 version/compiled` | 自测 3 项 banner 检查；pilot 指纹得 `25.1.0.1`、编译时间 |
| F4 证据脚本把「期望非零 rc」也交给要求 rc=0 的判定函数 | ✅已修 | 新增 `expect_rc`；注入检查用 `expect_rc … 1` | `run.sh` 14 项全绿、注入 rc=1 被记录为通过 |
| F5 证据脚本自测计数写死 40 | ✅已修 | 改为「FAIL 行数=0 且 passed==total 且 total>0」现场统计 | 46/46 时脚本通过；改代码后无需改脚本 |
| F6 `--work-dir` 为相对路径时按 `--repo-root` 解析，曾写进共享仓库 | ✅已修（文档化） | 保持「相对 = 相对 repo-root」语义并在 `--repo-root` 帮助中说明；运行一律传绝对路径 | 复跑 pilot 两次均落运行期目录 |
| F7 pilot 指纹误记 `jobs=48`（actual 3） | ✅已修 | 用 `--jobs 3 --repeats 2 --aggregate-only` 重聚合 | pilot.md「并发：3」、JSON `jobs: 3` |
| F8 全量一轮中断会丢失整轮（驱动只在轮末写 JSON） | ⏸延后 | 未改驱动（任务禁改源码）；`--resume` 以「(suite,engine,rep) 轮」为粒度 | 已实测 `[skip] llvm-ts/qemu rep=1: complete JSON reused` |

**判决**：F1–F7 全部修复并有复验（自测 46/46、证据脚本 16/16 含注入）；F8 属驱动限制，按任务「不改源码」显式延后并已实测 `--resume` 粒度。改动仅新增一个工具脚本，未触碰驱动/源码/用例/门控 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，命令在本任务树内、相对路径；输出/退出码为原文）**

1. **未改源码**：`git status --porcelain -uall` ⇒ 仅 ` M .tao/tasks/testcases/m13-testcases-001-static长尾3600s.md` 与 `?? tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py`；`git diff --stat -- components/ 'tools/testcases/tset/*/run_*.py' tests/ spec/ contracts/ Makefile .tao/knowledge/` ⇒ **0 行**；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。脚本 1014 行只 import 标准库，`subprocess` 仅用于三个 tset 驱动 / `git` / 版本探针，写入只落 `--work-dir`/`--json-out`/`--md-out`，不 import `gem5_se_engine`、不碰 `components/` ⇒ **① 真的没改源码（只编排+聚合）**。
2. **选例**：独立解析 `refs/GEM5-021t-baseline-summary.json` 的 `timeout_recheck` ⇒ libc 2 + llvm 70 = **72**，逐 id 与脚本 `load_selection()` 返回**完全相等**（id 串 md5 `b56f01d92454e9bc18759760a8fb5d97`）；72 例 `gem5_capability="time budget"` 且 `gem5_reason` 以 `timeout after` 开头 ⇒ **72/72**；节点 `case-list.json` 的 id 串 md5 同为 `b56f01d9…` ⇒ **② 72 例选例正确**。
3. **pilot 数据**（复算 `pilot.json`）：gem5 2370.70/1267.02/1782.34 s、qemu 4.92/3.02/1.97 s、ratio 481.85/419.543/904.741；相对极差 gem5 1.68/1.29/**2.55 %**、qemu 0.20/0/0 ⇒ 与完成区逐个一致。
4. **我另跑 1 例 × 2 次**（`MultiSource/Benchmarks/Trimaran/netbench-url`，两路并行、各 `--repeats 1 --jobs 1`，`EXIT_A=0 EXIT_B=0`）：gem5 **1251.41 / 1246.57** ⇒ 相对极差 **0.39 %**；qemu 3.02/3.02 ⇒ 0 %；ratio 414.374/412.772 ⇒ 0.39 %；与 engineer 同例（1267.02 / 419.543）同量级 ⇒ **③ pilot 方差 <5 % 成立**。
5. **脚本健壮性**：`--resume` 实跑 4 轮全部 `[skip] llvm-ts/{qemu,gem5-se} r{1,2}: complete JSON reused`、rc=0、未起引擎；`missing` 两侧均可 FAIL —— 我把 `pilot/llvm-ts-gem5-se-r1.json` 删掉 1 例后 `--aggregate-only` ⇒ `missing=[{gem5-se, case absent}] ok=False` **rc=1**；`--inject-missing-qemu-seconds` ⇒ **rc=1**（可达）。
6. **证据脚本**：`sh .work/evidence/m13-testcases-001/run.sh` ⇒ `checks failed: 0` / `evidence: PASS` / **rc=0**，16 项逐条在案；**独立注入**（`cp` 备份 + md5 `1d7ef329da4b23b92df4a746918bb0be`，把该例 qemu `run_seconds` 置空）⇒ `reaggregate-rc 0→1`、`restore-rc 0→1`、**rc=1 FAIL**；`cp` 还原 md5 相等 ⇒ 复跑 `evidence: PASS` **rc=0**（回绿）。
7. **门控**：`make check` ⇒ **rc=2**；`make -k check` ⇒ **4 红**：① `check-isa-coverage`（本树无 llvm-mc；补 `DADAO_ROOT` 后 `make check-isa-coverage` **rc=0 PASS**，与 engineer 日志同源）② `check-milestones-fresh` **2 条均指本任务**（A1 表=待开始 vs 书=待验收；R1 有 worktree 但台账在待开始）③ `check-width-sizes` ④ `check-components`（缺 `.dadao` 安装根，已披露）。`check-tasks` rc=0、`python3 -m compileall -q tools` rc=0、`check-run-artifacts`/`check-temp-dirs`/`check-knowledge-refs`/`check-no-residue` 均 PASS。
8. **可比性证据**：独立复算 103t r1200 驱动 JSON（`gem5 klass=pass` 未截断例）⇒ **n=135、min 25.2、median 228.3、max 810.9**，与「135 例 25–811、中位 228」**逐字吻合**；节点 `qemu-phase.json`（server208、jobs=48）⇒ 72 行、`qemu_klass` 全 pass（72/72）、max **1081.23**、2 例 0.00 均 ✓，但 **matrix `run_seconds=4.95`**（完成区写 5.2，5.2 是驱动进度行 `(5.2s)`）、中位 40.59（去 0 为 41.42，完成区写 41.3）。

**约束核验**：只准备、不改源码/用例/期望/门控 ✓；`git status` 只含本任务书 + 新脚本 ✓；完成区 **25 行 ≤30** ✓；无运行期路径（宿主绝对路径 / 家目录 / 临时目录 三类关键字均无命中）✓；「修改文件」与 `git status` 一致 ✓；未 commit/push、未改共享台账 ✓（注入前后 md5 对账、工作区快照前后逐行一致）。

**判决：Accepted**（engineer 本轮达标；主会话仍须跑全量 72 例并落 `refs/` 后再 `/complete`）。

**findings（文档级，不阻断，architect 收尾时改）**：F1 完成区「`make check` 3 红＝INTEG-061t＋安装根×2」与我重跑不符 —— 实为 4 红，且 `check-milestones-fresh` 的 2 条**指本任务**（INTEG-061t 红因其 worktree 已被清理而不再复现）；F2 节点数字口径混用（进度行 5.2 s vs `run_seconds` 4.95；中位 41.3 vs 40.59/41.42），建议统一按 `run_seconds` 改写。

**阻断提示（供 architect 定夺，非 engineer 责任）**：任务分支 reflog 仅 1 条 `Created from master @ 9fd128d0`，**落后 master 13 个提交**、不含 `981f897a 台账：m13-testcases-001 移入进行中`（与派单所述基线 `981f897a` 不符）⇒ 本树 L1 的 `check-milestones-fresh` 红源于**陈旧基线**，合并 master 后自愈；请 architect 决定先 rebase/merge 再跑全量。

#### 收尾（architect，2026-11-09 18:26）

- 判决 **Accepted**：reviewer 独立复跑 pilot（`netbench-url` 2 次：gem5 1251.41/1246.57 ⇒ 0.39%）、独立解析 72 例选例（id 串 md5 `b56f01d9…` 与脚本相等）、独立注入（qemu `run_seconds` 置空 ⇒ rc=1）并还原回绿。
- 确认**未改源码**：`git diff` 对 `components/`、`tset/*/run_*.py`、`tests/`、`spec/`、`contracts/`、`Makefile` **0 行**；脚本只 import 标准库。
- F1/F2 已修（4 红口径、节点 `run_seconds` 中位 40.59）；分支已 `merge master`（含 `981f897a` 派单提交，台账 2 条自消）。
- 全量 72 例 × 3600s 由主会话在节点启动（先 `build-gem5`）。
