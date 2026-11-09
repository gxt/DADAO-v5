# m13-testcases-002: dynamic 长尾 93 例 × 3600s + QEMU/gem5 运行时间比率

**模块**：testcases
**项目里程碑**：M13
**依赖**：`TESTCASES-104t`（dynamic 基线，93 例 timeout）
**可并行分片**：否（单机 48 并发跑批；测时间要求进程独占核）
**状态**：已验证

## 用户裁定（原话）

「M13准备专门进行多方测试的差分对比，可以先从gem5的超时问题做起，放到208节点机上，48并行（甚至60并行，你觉得呢）；建立专门的任务，跑3600s，甚至7200s，我们测试一下qemu和gem5的运行时间的比率，对不同的任务是否具有可比性。该任务（或者你可以分解多个任务）不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」

## 背景（事实）

- `TESTCASES-103t`：dynamic 档 600/300s 下 **93 例 timeout**（无更长预算复测）。
- 现有 `run_seconds` 只记录被测引擎自身耗时，**没有 QEMU 侧同例计时**，无法判断「gem5 慢多少倍」。
- 208 有 64 vCPU；48 并发为推荐值（留 16 核给内核/IO），**不宜 60**（时间测量会被调度/带宽争用污染）。

## 目标

1. **只记录，不修改**：对那 93 例（名单来自 104t 的 dynamic 基线 timeout）用 **gem5 SE 3600s** 预算重跑；**同例 QEMU 也计时**。
2. 输出每例：`case` / `gem5_seconds` / `qemu_seconds` / `ratio = gem5/qemu` / `gem5_klass` / `exit`。
3. 统计：比值的分布（min/median/max/P90）、异常离群、与用例类别的相关性（如纯浮点 vs 字符串）。
4. 判定「QEMU/gem5 时间比率是否可作为跨用例的可比指标」——**只给数据与观察，不做裁定**。

## 验收标准

1. 93 例全部有 `gem5_seconds` 与 `qemu_seconds`（缺一即 FAIL，不得静默跳过）
2. 输出 JSON + Markdown 落 `.tao/knowledge/refs/m13-002-dynamic-longtail.json/.md`
3. 报告含：逐例表、比值分布、离群说明、**执行环境指纹**（节点、并发数、gem5/qemu 二进制 md5、musl HEAD、CPU 型号）
4. 重复性：抽 3 例各跑 2 次，方差 < 5%（否则报告标注「时间不可比」）
5. **不改** gem5/QEMU/测试资产/用例与期望；`git status` 只含本任务书与 `refs/` 新文件
6. 完成区 ≤30 行、无运行期路径

## 执行方式（长任务）

- **48 并发**、`server207` 或 `server208`（按 `remote.py status` 选空闲者；同一时段该机不得有构建负载）
- 跑批由**主会话**启动 background，落 PID/日志/`*_EXIT`；engineer 只准备脚本与配置
- 预计：93 例 × 3600s ÷ 48 ≈ **1.5 h**（加 QEMU 计时约 1.5–2 h）

## 非范围

- 不分析根因、不调试、不改任何源码
- 不修改 `PICOLIBC_KNOWN_BLOCKED` 或任何门控
- 不跑 static（`m13-testcases-001`）

## 完成区

**测试结果**：runner 自测 63/63；证据脚本 28/28（注入 rc=1→干净重聚合 rc=0）；pilot 3 例×2 次、4 个引擎轮 rc=0、missing=0；L1 rc=2（4 项外因，见遗留）。

**修改文件**：`tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py`（加 `--selection timeout-inventory` / `--link-mode` / `--task-id`；static 默认行为不变；未改驱动/引擎/用例/期望/门控）；本任务书；运行期证据脚本（不入 git）。

**验收结果**：
- 选例 `timeout_inventory` = 93（libc-test 4 + llvm-ts 89），逐 id 唯一。
- 动态加载：gem5 命令行含 `--interp-dir`、`--redirect /lib=…/dynamic/root/lib`；ELF 含 `PT_INTERP → /lib/ld-musl-dadao.so.1`；qemu 同例 pass。
- pilot（server207、jobs=3、3600s、3 例×2 次）：qemu 1.62/2.22/2.92 s；gem5 1774.2/2374.3/2473.9 s；ratio 1095.2/1069.5/819.2；gem5 相对极差 0.76–2.4%（<5%），qemu 0–6.62%（2–3 s 级抖动）⇒ 汇总按最差 6.62% 标「时间不可比」。
- 指纹：server207、Xeon E7-4820、nproc=64、jobs=3；gem5 md5 `53466b…`（25.1.0.1）；qemu md5 `3c4660…`（11.1.1）；musl HEAD `61bd50e`；节点仓库 HEAD `c157dda1`（clean）；loadavg [1.17,1.77,2.32]。
- 全量命令（主会话启动）：节点 `REPO` 同步到含本任务脚本的 master 后，`python3 tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py --repo-root "$REPO" --case-list .tao/knowledge/refs/TESTCASES-104t-dynamic-summary.json --selection timeout-inventory --link-mode dynamic --suites libc-test,llvm-ts --jobs 48 --repeats 1 --gem5-timeout 3600 --qemu-timeout 3600 --work-dir <运行期目录>/work --json-out <运行期目录>/m13-002-dynamic-longtail.json --md-out <运行期目录>/m13-002-dynamic-longtail.md --resume`，`setsid nohup` + PID/日志/`*_EXIT`；结果回传后落 `refs/m13-002-dynamic-longtail.{json,md}`（避免写脏节点仓库）。
- 预计耗时：套件串行 ⇒ qemu 轮 10–15 min；gem5 libc 4 例最坏 1 h + gem5 llvm 2 波 ≤2 h；预计 2–2.5 h、最坏 ≈3.5 h（节点 gem5 已建好，无需再建）。

**新发现/坑**：
- 节点无 gem5.opt；`make build-gem5 JOBS=32` 首次 rc=2 但二进制已产出：`build_gem5.py` 在 `.work/build/gem5` 不存在时对 `(source/build).relative_to(link.parent)` 抛 ValueError；先 `mkdir -p .work/build/gem5` 再跑即 PASS（构建 ≈17 min，749 MB）。
- 4 个 libc dynamic 超时例 qemu 均 <5 ms ⇒ ratio 未定义；试点改选 llvm 可测例。
- `--engines` 传子集仍按两引擎验收（`collect_rows` 固定遍历两引擎）会报 missing；全量用默认两引擎不受影响（未改）。
- 不同主机 qemu/gem5 二进制不同，比值只在同机同一次运行内可比。

**遗留问题**：
- 全量 93 例未跑（按裁定由主会话启动）；须先让节点仓库含本任务脚本（当前节点 HEAD 无该脚本）。
- L1 未绿（均非本任务）：worktree 无 `.dadao` 安装根（`check-isa-coverage` 缺 llvm-mc）；主工作树 `check-patch-tree` chipyard assertion ⑨（在途 m12）；5 个他任务临时目录；m13-001 任务书 1 处 `.work` 具体引用。`compileall`/`check-run-artifacts`/`check-tasks` 绿。
- pilot 仅 server207 单机、jobs=3；全量 jobs=48 的逐例时间与比值以全量结果为准。

## 审阅记录

### 第 1 轮 engineer 自审（逐行）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 证据脚本聚合时未传 `--only/--repeats`，把 3 例试点按 93 例选例聚合 ⇒ rc=2 | ✅已修 | 从 pilot.json 读 jobs/repeats/rows 生成 `pilot_args` | 注入与干净重聚合均 rc=1/rc=0，28/28 |
| F2 「错误选例字段」检查用了 static 摘要（它也含 `timeout_inventory`）⇒ 假绿 | ✅已修 | 改用一个仅含 `timeout_recheck` 的临时记录 | `wrong-field=rejected`，28/28 |
| F3 首次 `build-gem5` rc=2 但二进制已产出（`build_gem5.py` symlink 逻辑在目录缺失时抛 ValueError） | ⏸延后（非本任务） | 未改源码；运行期 `mkdir -p .work/build/gem5` 后重跑得 rc=0 | `build-gem5: PASS`、md5 `53466b…` |
| F4 `--engines` 子集仍按两引擎判定 missing（预存在） | ❌不修（显式记录） | 全量用默认两引擎；`--engines` 只在 qemu 冒烟时使用 | 冒烟 rc=1 的 missing 条目为未运行的 gem5 引擎，行为已记录 |
| F5 试点目录最初落在 worktree 根（本任务的临时目录与 worktree 同路径） | ✅已修 | 运行期目录移到同级 `<worktree>-runtime`；证据脚本默认值同步 | `git status -uall` 仅剩脚本改动 |
| F6 汇总重复性把 qemu 2–3 s 级抖动（6.62%）计入 ⇒ 标「时间不可比」 | ❌不修（口径如此） | 未改阈值；报告按 acceptance 自动标注 | pilot.md「最大相对极差 6.62%；时间不可比」，gem5 侧 0.76–2.4% |

**判决**：F1/F2/F5 已修并有复验（自测 63/63、证据 28/28 含注入回环）；F3 属节点仓库既有脚本缺陷（未改源码，运行时绕过）；F4/F6 为既有口径/行为并如实记录。改动仅一个工具脚本 + 本任务书，未触碰驱动/引擎/用例/门控 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（本人重跑，2026-11-09）

**重跑记录（命令 / 真实输出 / 退出码）**
1. 快照对账：开工与收尾 `git status --porcelain -uall` 均为 ` M …002-dynamic长尾3600s.md` + ` M tools/…/run_engine_ratio.py`（无其它行、无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`）；脚本注入前/还原后 md5 同为 `108857ebf4c6be595a3c0196677dee2f`。
2. `git diff c157dda1 -- components/ tests/ spec/ contracts/ Makefile tools/testcases/tset/{libc-test,llvm-ts,embench} tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py` ⇒ **0 行**；全仓唯一额外差异 `milestones-m13.md` 1 行＝worktree 落后台账 commit（非本任务）。驱动/引擎/用例/期望/门控未动。
3. 独立解析 `TESTCASES-104t-dynamic-summary.json` 的 `timeout_inventory` ⇒ llvm-ts 89 + libc-test 4 = **93**；与脚本 `load_selection(...,"timeout-inventory")` 输出**逐 id 顺序完全相等**、id 唯一。
4. `bash .work/evidence/m13-testcases-002/run.sh` ⇒ `evidence: 28/28 checks passed`、`EVIDENCE_EXIT=0`（内含 `self-test: 63/63`）。
5. **独立反例注入**（改 `timeout-inventory` 分支为 `out[suite] = ids[:-1]`，`cp` 备份+md5）⇒ `evidence: 23/28`、5 项 FAIL（self-test 60/63、libc=3、llvm=88、total=91）、`INJECT_EVIDENCE_EXIT=1`；`cp` 还原 md5 复等后重跑回 `28/28`、`EXIT=0`。
6. `make check` ⇒ `EXIT=2`，唯一红 `check-isa-coverage`（本 worktree `.dadao/` 仅 `gate.lock`、缺 `llvm-mc`；主仓库有该二进制 ⇒ 外因）；另跑 `check-tasks=0`、`check-run-artifacts=0`、`check-knowledge-refs=2`（红点＝m13-001 任务书:99 `.work/evidence/…`）、`check-temp-dirs=2`（红点＝他任务目录，与 engineer 当时 5 项日志一致）⇒ **L1 红全部外因，无本任务红**。
7. **pilot 独立复跑**（server207、`--selection timeout-inventory --link-mode dynamic --only MultiSource/Benchmarks/Trimaran/enc-md5 --jobs 1 --repeats 2`，4 个引擎轮 rc 全 0）⇒ `[done] cases=1 missing=0 ratio=1098.13 repeatable=False`、`EXIT=0`；`gem5_seconds=1778.97`（engineer 1774.18，+0.27%）、`qemu_seconds=1.62`（＝engineer）、`ratio=1098.13`（1095.173，+0.27%）；`gem5 极差 6.09%`（1724.78/1833.16）、`qemu 0.00%`（1.62/1.62）⇒ 自动标「时间不可比」。
8. dynamic 加载（复跑现场亲验）：gem5 `run_cmd` 含 `--interp-dir …/dynamic/root` 与 `--redirect /lib=…/dynamic/root/lib`；qemu 侧 `-L …/root`；`readelf -l` ⇒ `EXEC` + `[Requesting program interpreter: /lib/ld-musl-dadao.so.1]`，驱动记 `pt_interp=/lib/ld-musl-dadao.so.1`，两引擎 `pass / exit 0`。
9. `6.62%` 复算：pilot adpcm qemu `[2.92,3.12]` ⇒ `(3.12-2.92)/3.02×100 = 6.6225 → 6.62` ✓；`819.169 = 2473.89/3.02` ✓（三例 gem5 1774.18/2374.28/2473.89、ratio 1095.173/1069.495/819.169 与完成区一致）。
10. static 不变 + 无副本：新旧脚本对 `GEM5-021t` 默认 `recheck` 选例结果完全相同（libc 2 / llvm 70）；全树仅 1 份 `run_engine_ratio.py`；`--selection` 默认 `recheck`。

**约束核验**：未改源码 ✅｜93 例正确 ✅｜未改门控/用例/期望 ✅｜完成区 25 行（≤30）✅、无运行期路径 ✅｜「修改文件」与 `git status` 一致 ✅｜证据可失败（注入→FAIL→还原→回绿）✅｜全量 93 例未跑＝按裁定归主会话（遗留已写明）✅。

**发现（文档级，不阻断，交 architect 收尾订正）**
- D1 完成区「qemu 1.62/2.22/**2.92** s」第三值应为 **3.02**（`pilot.json` 的 `qemu_seconds`；2.92 是该例 r1 单次值，其自身 `ratio 819.2 = 2473.89/3.02` 亦证）。
- D2 「时间不可比」仅出现在 repeats=2 的 pilot 报告（`--repeats 1` 全量报告不产重复性行，无假标注）；标注由最差样本触发，复跑证明 gem5 侧也能到 6.09%，非只 qemu 小基数造成。

**判决**：**Accepted** —— 上列验收项全部由本人重跑取证，退出码与数字逐条对齐；D1/D2 为文档级笔误/口径说明，不构成阻断。

#### 收尾（architect，2026-11-09 23:46）

- 判决 **Accepted**（reviewer 21:34 完成；完成通知未送达，主会话按盘上事实收口）。
- **未改源码**：`git diff` 对 `components/`、`tests/`、`spec/`、`contracts/`、`Makefile`、tset 驱动 0 行；全树只有 1 份 `run_engine_ratio.py`（复用未复制）。
- **93 例**逐 id 与 `timeout_inventory` 相等；dynamic 加载证据（`--interp-dir`、`--redirect /lib=`、`PT_INTERP`）。
- D1 笔误已修（qemu 第三值 3.02）；D2 口径已记（「时间不可比」只在 `--repeats 2` 的 pilot 报告出现，全量 `--repeats 1` 不产该行）。
- 全量 93 例 × 3600s 待 207 空闲后启动（001 正在跑）。
