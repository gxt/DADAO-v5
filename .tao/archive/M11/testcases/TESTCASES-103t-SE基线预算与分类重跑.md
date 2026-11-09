# TESTCASES-103t: gem5 SE 基线预算与分类重跑（120s → 600s）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`GEM5-023t`（文件 I/O 与时钟；基线需在当前引擎上重跑）
**状态**：已验证

## 背景与事实

- `GEM5-021t` 基线使用 **120 s/例**；其中大量 `blocked` 实为 `timeout after 120s (SE, not a verdict)`，不是能力缺口
- 超预算重测（600 s）显示：7 例转 PASS、22 例仍 blocked（纯计算量）、1 例转 fail（`Misc/pi`，后由 `INTEG-058t` 修复）
- 当前基线把 `time budget` 与真实能力缺口混在同一张 `blocked` 表里，后续任务判断（例如「文件 I/O 还差几例」）会被超时干扰
- 驱动 `run_gem5_se_baseline.py` 已有 `--timeout`，但默认值与报告口径未按套件区分

## 目标

1. 把 gem5 SE 基线的默认预算改为**按套件可配**（建议 `libc-test` 300 s、`llvm-ts` 600 s、`embench` 300 s，命令写入任务书），并在报告里把 `timeout` 单列，不算能力缺口。
2. 重跑 static 基线（`GEM5-021t` 驱动），产出新的 JSON + 摘要（覆盖 `gap_inventory` 与 `timeout_recheck`），库内快照更新到 `.tao/knowledge/refs/`。
3. 对每个 `timeout` 案例做「预算倍数」实验（600 s / 1200 s）并记录：转 PASS / 仍超时 / 真失败，给出每例结论。
4. 不改 `tests/tset/**` 用例与期望，不改 gem5/QEMU 实现。

## 范围 / 非范围

**在范围内**：`tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`、`tools/testcases/lib/gem5_se_engine.py`（仅预算/分类）、`.tao/knowledge/refs/GEM5-021t-baseline-*`（更新快照）、本任务书、`milestones.md`。

**不在范围**：gem5/QEMU 实现、测试用例与期望、`docs/TestReports/M11-三平台一致矩阵.md`（G3 统一重生成）。

## 验收标准

1. 新基线报告：`blocked` 只含真实能力缺口；`timeout` 单列并标注「非能力」。
2. 每例 `timeout` 有 **≥600 s** 结果（libc 套件从 300 s 直接到 1200 s，无 600 s 中间点；按 ≥600 s 口径满足）；仍超时的给「需要 >1200 s / 纯计算量」结论。
3. `qemu_only_fail` 0；`gem5_only_fail` 与前一版差异逐条解释（不得把超时改写成 PASS）。
4. `make check`（L1）rc=0；驱动 `--self-test`（如有）rc=0。
5. 反例：把预算改回 120 s ⇒ 报告里 timeout 数回升，验证分类不受手写影响；`cp`+`md5sum -c` 还原。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 该任务**不实现任何能力**，只校准口径；它必须在一个没有 gem5 构建在跑的窗口执行，否则结果不可复现。
- 全量 589 例在 600 s 预算下耗时较长（小时级），按套件分批跑并落日志/PID/EXIT。

## 完成区

**测试结果**：`--self-test` 20/20；证据脚本 20/20（含注入反例→FAIL→`cp`+md5 还原→回绿）；小规模试点 libc-test 8 例 `blocked=3`（SysV IPC）/`timeout=1` 分列、llvm-ts 2 例 600 s→120 s `timeout` 0→2。全量两轮：默认预算（300/600 s）`gem5_pass=474 blocked=8 timeout=97 gem5_only_fail=9`；1200 s `gem5_pass=497 blocked=8 timeout=72 gem5_only_fail=11`。
**修改文件**：`tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`；`.tao/knowledge/refs/GEM5-021t-baseline-summary.{json,md}`（含 `timeout_recheck` 的新快照）；新增 `.tao/knowledge/refs/TESTCASES-103t-timeout-recheck.md`；`.tao/knowledge/issues.yaml`（ISS-357）；本任务书。未改 `gem5_se_engine.py`、`tests/tset/**`、gem5/QEMU、`milestones*.md`。
**验收结果**：
- `--help`：默认预算 libc-test=300、llvm-ts=600、embench=300；`--gem5-timeout` 全局覆盖，`--gem5-timeout-by-suite` 单套件覆盖；`--driver-arg` 仅试点转发。
- 报告：`totals.blocked` 只含真实能力缺口（timeout 剔除）；`totals.timeout` 单列并标「非能力缺口」，新增 `timeout_inventory`；`gap_inventory`/`timeout_recheck` 结构不变（只少 time budget 桶）。
- 反例（真实重跑）：同 2 例 llvm-ts，600 s → `pass=2/timeout=0`；改 120 s → `timeout=2/blocked=0`，分类不受手写影响。
- `make check`（`-k` 全量）rc=2，红项均为环境/台账：`check-patch-tree`（chipyard patch 集与 HEAD 不一致；主仓库 master 同命令亦红，条数随并行 chipyard 工作变化）、`check-milestones-fresh`（worktree 已建但台账行仍「待开始」，按分工不改台账）、`check-temp-dirs`（其它任务陈旧临时目录）；`check-knowledge-refs`、`check-run-artifacts` 及其余门控 PASS。
**新发现/坑**：`--filter`/`--only` 仅部分驱动支持，试点用 `--driver-arg` 转发（全量禁用）；timeout 判据取驱动 JSON 的 `gap.kind`（回退 `capability`），不靠理由字符串；worktree 内 `.work`/`.dadao` 软链主仓库共享构建根才能跑真实 gem5（不入库）；1200 s 复测须先做**子集驱动 JSON** 再 `--aggregate-only --recheck`，否则 `timeout_recheck` 会混入全量 pass；主会话留下的两个全量运行标记 `.EXIT` 不符合 `check-run-artifacts` A3 命名，已原内容改名为 `*-exit.txt`（`check-run-artifacts` 转 PASS）。
**遗留问题**：72 例 1200 s 仍 timeout（计算量/引擎速度，非缺口，需更大预算或提速）；ISS-357（2 例 FreeBench 为 SE stdout/stderr 顺序缺陷，待专任务在驱动层修，修复前按平台捕获问题记 fail）；主口径保持默认预算，1200 s 仅作复测证据。

### 全量复测（1200 s）：97 → 23 转 PASS / 72 仍 timeout / 2 转 fail
- **复核**（脚本按套件逐例比对两份驱动 JSON）：23+72+2=97；`gem5_pass 474→497`（+23）、`gem5_only_fail 9→11`（+2），真实 `blocked=8` 两轮不变。
- **仍 timeout**：libc-test 2（clocale_mbfuncs、raise-race）、llvm-ts 70；结论「纯计算量/引擎速度」，不计能力缺口。
- **2 例转 fail**：llvm-ts FreeBench `mason`/`neural`，`gem5_exit=0`、`oracle mismatch`，长度相同（233/233、358/358 B），是 9→11 的全部差值。
- **性质核定（实测）**：`stderr+stdout+"exit 0\n"` 与参考逐字节相等（sha 与参考一致）；`stdout+stderr+exit` 的 sha 正是驱动报告的 `0719653c…`/`03d6202a…` ⇒ **SE 输出捕获的 stdout/stderr 顺序**问题，**不是 FP 数值差异**（任务分派初判据此更正），已登记 ISS-357。
- **落盘**：`timeout_recheck` 仅含原 timeout 例（libc 5 / llvm 92），快照与逐类名单见 `refs/GEM5-021t-baseline-summary.*`、`refs/TESTCASES-103t-timeout-recheck.md`。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `run_gem5_se_baseline.py`：预算解析优先级、timeout 判据（kind 优先/capability 回退）、gap 桶剔除、totals 双口径、markdown 分列、自测注入可达 FAIL、`--aggregate-only` 复用路径。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| blocked 行「其中 QEMU 通过」把 timeout 也算进去，数字自相矛盾 | ✅已修 | 拆 `blocked_real_but_qemu_pass`/`timeout_but_qemu_pass`，报告分别显示 | libc 试点渲染 3(QEMU 3) / 1(QEMU 1) |
| 首版注入改常量、与判定同源，反例无法变红（假绿） | ✅已修 | 注入改为在副本里让 `is_timeout_case` 恒 False | 证据脚本 C3：注入 rc≠0、FAIL 可见、还原后回绿 |
| 试点目录误落在 worktree 根（仓库内临时文件） | ✅已修 | 全部移出运行期临时根；worktree 仅剩源码改动 | `git status --porcelain -uall` 仅 1 个 M |
| `--gem5-timeout` 默认改 None 后 summary 字段类型可能漂移 | ✅已修 | 单预算 `gem5_timeout_seconds` 保持 int，多预算为映射，另加 `gem5_timeout_by_suite` | 试点=300（int）；默认三套件为映射 |
| 长预算下驱动有 fail 时 rc=1，编排可能被当失败 | ✅已确认 | 编排不转抛 rc，写 `.driver.rc`，计数照常 | 试点 gem5 驱动 rc=1，baseline 正常生成 |

### 第 2 轮 engineer 自审（全量复测落盘）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 初判「2 例疑似 FP 数值差异」与证据不符：输出长度相同但内容不同 | ✅更正 | 复测结论与 ISS-357 标题改为实测根因（SE stdout/stderr 顺序） | `stderr+stdout+exit` 与参考逐字节相等；`stdout+stderr+exit` 的 sha 命中驱动报告值 |
| 直接把 1200 s 全量 JSON 当 `--recheck` 会把全量 pass 计入复测 | ✅已修 | 先按第一轮 timeout 集生成子集驱动 JSON（libc 5 / llvm 92） | 快照 `timeout_recheck.total` = 5/92，23/72/2 合计 97 |
| `check-run-artifacts` 红：全量运行标记 `.EXIT` 命名不合规 | ✅已修 | 运行期日志目录中两标记改名 `*-exit.txt`（内容不变） | `make -k check` 中 `check-run-artifacts: PASS` |
| 报告「其中 QEMU 通过」仍可能把 timeout 计入 blocked | ✅已修（第 1 轮遗留核对） | `blocked_real_but_qemu_pass`/`timeout_but_qemu_pass` 分列 | 快照总览 7 / 97 分别显示 |

### 第 1 轮 reviewer 验收

**判决：Accepted**（3 条 finding 均为文档级，按 reviewer 规则 §6.5 不阻断，收尾由 architect 改）。以下命令全部由 reviewer 在本 worktree 亲跑。

**重跑记录（命令 → 真实输出/退出码）**
- `python3 tools/.../run_gem5_se_baseline.py --self-test` → `self-test: 20/20 checks passed`，`rc=0`。
- `bash .work/evidence/<任务ID>/run.sh`（任务证据脚本）→ 20 条 `PASS`、`evidence: all checks PASSED`，`rc=0`。
- 两份全量 JSON 现场重算：第一轮 `pass=474 / blocked(真)=8 / timeout=97 / fail=9`（474+105+9+1=589）；1200 s `497 / 8 / 72 / 11`（497+80+11+1=589）；与完成区数字逐项一致。
- 97 例去向逐例比对（第一轮 timeout 集 ↔ 1200 s 状态，589 键全等）→ `{'pass':23,'blocked':72,'fail':2}`；`timeout_recheck` 的 passed/still/other 三集合与两份驱动 JSON、子集 JSON **三方相等**（libc 3+2=5、llvm 20+70+2=92=97），2 个 other 即 `FreeBench/mason`、`neural`。
- 2 例根因字节级复核：`guest.stderr` 40 B = `Compile date…`/`Compiler switches…`（源码 `mason.c:248`/`neural.c:107` 就是 `fprintf(stderr,…)`）；`stderr+stdout+"exit 0\n"` sha == 参考 sha（mason `9f67c2cc…`、neural `9c8fb4d5…`，**逐字节相等**）；`stdout+stderr+exit` sha = `0719653c859e3ea5` / `03d6202ad104bc54`，正是驱动 reason 报的值；QEMU 轮同两例 `byte-exact pass`。
- 反例注入（reviewer 独立，非采信 engineer 自检）：`DEFAULT_GEM5_TIMEOUT`→120 后同脚本 `rc=1`（4 FAIL：C1 帮助文案 / C2 self-test `16/20` / C3 还原自测）；同时**真实重跑** 1 例 llvm → `totals: blocked=0 timeout=1`、`gap_inventory=[]`、`timeout_inventory budget=120`，对照 600 s 试点同例 `pass=1 timeout=0`；`cp` 还原后 md5 `a760383967bedf48ca2943c7bfa9c22e` 与注入前相等、`run.sh` 回绿 `rc=0`。
- `make -k check` → `rc=2`，红项仅 3 个：`check-patch-tree`（chipyard，主仓 master 同命令亦 `rc=2`/13 项，只读复跑证实与本任务无关）、`check-milestones-fresh`（`TESTCASES-103t` 行仍在「待开始」，属主会话派单未移行）、`check-temp-dirs`（4 个**其它**任务陈旧目录）；`check-knowledge-refs: PASS`、`check-run-artifacts: PASS`，其余 8 项 `结果: PASS`。

**约束核验**：改动 6 文件与「修改文件」逐项对齐（`git status` 审前=审后：5 M + 1 ??，非任务书文件 md5 逐一相等）；未碰 `tests/`、`spec/`、`contracts/`、`Makefile`、`milestones*.md`、`gem5_se_engine.py`；完成区 19 行 ≤30、无运行期路径；两轮 `qemu_only_fail=0`；`timeout_recheck` 只统计原 timeout 例（子集驱动 JSON 5/92，非全量 214/335），主计数未被复测改写。

**finding（文档级，不阻断；请 architect 收尾一并改）**
1. `refs/TESTCASES-103t-timeout-recheck.md:133`「589 例中仅这 2 例…」与现场统计不符：实测**至少 4 例**（`FreeBench/analyzer`、`pifft`、`mason`、`neural` 的 `stderr+stdout+"exit 0\n"` 均与参考逐字节相等，前两例 sha 即驱动报告值，且已在第一轮 9 个 fail 内）⇒ 改数字并同步 ISS-357 影响面；修复不可全局交换顺序（另有 1 例 `stdout+stderr` 才对、31 例 pass 走非逐字节比对）。
2. `refs/GEM5-021t-baseline-summary.md` 总览「超预算重测另计：通过 23、非通过 2」漏掉 72 仍 timeout（`extra_fail` 只累加 `other`）⇒ 改为「通过 23、转 fail 2、仍 timeout 72」。
3. （观察）libc 5 例无 600 s 中间点（300 s → 1200 s）；按「≥600 s 结果」读法已满足（1200 s 复测覆盖全部 97 例并给出逐例结论），按验收标准 2 字面「600 s」请收尾确认口径。

#### 收尾（architect，2026-11-09 09:02）

- 判决 **Accepted**：reviewer 自跑 20/20 self-test、20 条证据、两份 JSON 重算（474/8/97/9 与 497/8/72/11，均 589）、97 例去向 23/72/2 三方集合相等；独立反例（预算改 120s）真实重跑 1 例 llvm ⇒ `timeout=1 pass=0`，还原回绿。
- **2 例 fail 根因确认**：不是 FP，是 SE 输出捕获的 stdout/stderr 顺序（`stderr+stdout` 与参考逐字节相等）。reviewer 复核把影响面从「2 例」修正为**至少 4 例**，并明确**不可全局交换顺序**（另有 1 例需 `stdout+stderr`、31 例走非逐字节比对）；`ISS-357` 已同步。
- **3 条文档级 finding 已修**：① recheck 报告影响面改为至少 4 例 + 不可全局交换；② summary 总览改为「通过 23、转 fail 2、仍超时 72」；③ 验收 2 改为「≥600 s」（libc 从 300 直接到 1200，无 600 中间点）。
- 主口径不变（第一轮 300/600s）：`blocked=8`、`timeout=97`；1200s 复测单列于 `timeout_recheck`。
