# TESTCASES-105t: 回归运行（原「夜跑」）加 gem5 SE + FS 成员

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-103t` + `TESTCASES-104t`（static/dynamic 基线驱动与结果已就绪）；gem5 FS 的 inst/arch 驱动已有。**不依赖** `INTEG-059t`（该任务是「对照工具 + 矩阵」，不是驱动）。
**可并行分片**：按套件（libc-test / llvm-ts / embench / arch）
**状态**：已验证

## 背景

用户 2026-11-08 裁定：「夜跑应该加 gem5，包括 se 和 fs；夜跑这个词有歧义，你不要误解」。

**口径澄清**：本仓库的「夜跑」= **全量回归成员集**（`tools/testcases/night_run.py` 的 `DEFAULT_MEMBERS`），不是「只在夜里跑」；触发时间不限。

现状（实测）：`DEFAULT_MEMBERS` 4 个成员全部走 QEMU——`tset:libc-test` / `tset:llvm-ts` / `tset:embench` / `arch:cfx`；gem5 没有任何长期回归成员，只在 `INTEG-059t` 里做一次性对照。

## 目标

1. **gem5 SE 成员**：把 `INTEG-059t` 的 gem5 SE tset 驱动固化为 Make 目标（`check-tset-*-gem5-se` 或等价），按 `static` + `dynamic` 两档全量跑 libc-test / llvm-ts / embench；结果 JSON 落 `TSET_GATE_JSON_DIR` 同构位置。
2. **gem5 FS 成员**：把 gem5 FS 的 `inst` + `arch`（裸机 E2E）驱动固化为成员；与 QEMU system 同一 case 集、比架构结果/退出码，不比时序。
3. **`DEFAULT_MEMBERS` 追加**：`tset:gem5-se-libc`、`tset:gem5-se-llvm`、`tset:gem5-se-embench`、`arch:gem5-fs`（命名可调整，须自解释）。
4. **报告**：`check_night_report.py` 的成员结构性检查同时覆盖新成员（缺成员/空结果/构建失败必须 FAIL，禁 vacuous）。
5. **预算**：给每个新成员独立超时；任一成员超时单列 `timeout`，不吞并成「失败」。

## 验收标准

1. `make night-run` 的 dry-run 列表含 gem5 SE 与 gem5 FS 成员（逐条打印，名称自解释）。
2. **复用 `103t`/`104t` 的落盘结果作为「成员可用」证据**，不重复全量跑：把其 JSON 路径登记进成员定义/文档，并说明「该成员跑什么、产物在哪」。
3. **只跑一个最快成员**（建议 `embench`，实测秒级）做端到端接入验证：rc=0、结果 JSON 落盘、报告能识别。
4. `check-night-report` 对新报告 rc=0；人为删一个成员结果 ⇒ rc=1（可达 FAIL）。
5. 不改变 QEMU 四个成员的既有语义与预算。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- **不阻塞 M11 收口**（用户 2026-11-08）：收口判据是「已知功能实现 + 已知 bug 解决 + 该做的验证做完」。
- **不重复全量**（用户 2026-11-09）：`103t`/`104t` 已跑过全量，本任务只做成员登记与报告接入；全量由常驻成员平时跑。
- gem5 SE 全量比 QEMU 慢一个量级，若单次回归跑不完，在报告中如实记录耗时，不缩减 case 集（除非用户另定）。
- 不改 `INTEG-059t` 的对照逻辑；本任务只做「固化为常驻成员 + 报告接入」。

## 完成区

**测试结果**：一键证据脚本 **30/30 PASS**（含反例：删成员行 ⇒ rc=1、`cp`+md5 还原回绿；默认成员 guard 对缺失/交叉失败结果 JSON ⇒ rc≠0）；`night_run --self-test` 9/9、`check_night_report --self-test` 13/13 均 rc=0。`make check`（L1）rc=2，红项全为他人/流程：`check-patch-tree`（共享 chipyard 源树被在途任务推进，本工作树 `components/` 干净）、`check-temp-dirs`（5 个其它任务陈旧临时目录，未删）、`check-milestones-fresh`（派单台账未把本任务移入「进行中」；本任务禁改 `milestones*.md`）。
**修改文件**：`tools/testcases/night_run.py`、`tools/testcases/check_night_report.py`、`Makefile`（help 与成员说明文本）、`docs/Process-09-测试组织规范.md`、`README.md`、本任务书。
**验收结果**：
- dry-run：8 成员逐条打印，新增 `tset:gem5-se-libc/-llvm/-embench`、`arch:gem5-fs`；QEMU 4 条命令逐字节未变、无新超时预算。
- 成员登记：gem5 SE static 复用 103t 驱动；103t/104t 落盘证据路径写入 `night_run.py` 注释（static `refs/GEM5-021t-baseline-summary.json`、dynamic `refs/TESTCASES-104t-dynamic-summary.json`）；FS 证据 `docs/TestReports/M11-三平台一致矩阵.md`。
- 端到端：`tset:gem5-se-embench` 声明式 pilot（1 例）经 `make night-run` 实跑 rc=0，结果 JSON 落盘（`both_pass=1, gem5_only_fail=0`），`check-night-report --members` 识别 rc=0；同一报告默认全集口径 rc=1（缺 7 成员，证明非 vacuous）。
- 报告门控：8 成员完整报告 rc=0；删 `gem5-se-llvm` 行 ⇒ rc=1 并点名；缺成员/空成员日志/超时 rc=124（单列 "超时"）均 FAIL；历史报告按默认口径 FAIL（缺 gem5 成员，已注明）。
- 防 vacuous：103t 基线 driver 写完报告恒 rc=0，故三个 SE 成员命令尾部追加 guard，读 `totals.gem5_only_fail+qemu_only_fail`，交叉失败/结果缺失时成员 rc≠0（证据脚本按真实 guard 复验 rc≠0）；FS 复用 `run_parity` 自身非零判定。
- 成员独立超时：仅 gem5 四成员登记（3600/10800/3600/14400 s），QEMU 保持无超时。
**新发现/坑**：① 103t/104t 基线编排 driver 写完报告即 rc=0，交叉失败不会让成员红 ⇒ 成员命令必须自带结果 guard，否则 vacuous。② 并发任务重链 `gem5.opt` 会让 pilot 瞬间 rc=2；证据脚本先等待可执行并对该瞬时态有限重试（本轮 attempts=1，上限 3）。③ 通过 `make night-run NIGHT_MEMBERS=...` 覆盖含双引号的命令会被 `/bin/sh` 拆坏（guard 的 python 内含 `"`）⇒ **覆盖成员时不要内嵌双引号**；失败方向为红、非假绿，默认路径不经 `NIGHT_MEMBERS` 不受影响。④ 证据脚本 scratch 初次误落工作树根已清，现固定仓库外、日志落运行期证据目录。
**遗留问题**：① 105t 之前的旧回归报告不含 gem5 成员，默认口径会 FAIL，待下一轮完整成员集运行转绿（按用户裁定本任务不重跑全量）。② gem5 SE/FS 全量成员的首次真实运行尚未发生（本轮仅登记 + 最快成员接入），耗时与 timeout 预算需首轮实测校准。③ 台账行未移入「进行中」，属派单侧，本任务不改。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`night_run.py`（成员/guard/独立超时/自测）、`check_night_report.py`（成员覆盖/超时单列）、Makefile 文本、Process-09、README。
**方法**：逐行审 diff；真跑 dry-run / pilot / 报告门控 / 两个 self-test / L1；反例现场注入并 `cp`+md5 还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| gem5 基线 driver 写完报告恒 rc=0，交叉失败会被当绿 | ✅已修 | 三个 SE 成员命令尾部追加 guard：结果缺失/交叉失败 ⇒ rc≠0 | 证据脚本按真实 guard 注入缺失 JSON ⇒ rc=1、`gem5_only_fail=1` ⇒ rc=1；pilot 干净结果 rc=0 |
| 历史报告缺 gem5 成员后变红，易被误当回归 | ✅已确认 | docstring 注明「105t 前报告默认口径 FAIL，需按新成员集重跑」 | 旧报告按默认口径 rc=1（缺成员行） |
| `--members` 收窄覆盖可能放走半量报告 | ✅已确认 | 仅显式 opt-in，默认仍全集；未知成员 rc=2 | 单成员报告默认 rc=1；`--members` rc=0；非法成员 rc=2 |
| QEMU 成员语义/预算被超时改动 | ✅已确认 | `MEMBER_TIMEOUTS` 只含 gem5 四个键；QEMU 走原 `subprocess.call` 无超时 | dry-run 四条命令逐字节相等；timeouts 交叉集为空 |
| 超时只杀直接子进程会留孤儿 | ✅已修 | `start_new_session` + `killpg`，rc=124 落 manifest | self-test `sleep 5`/1 s ⇒ rc=124，报告单列 "超时" |
| `meta.json` 顶层非对象会抛异常 | ✅已修 | 加载后 `isinstance(meta, dict)` 校验 | self-test「meta.json not an object ⇒ FAIL」 |
| `--members` 覆盖命令含双引号会经 make/sh 拆坏 | ✅已修 | 成员 guard 统一单引号；pilot 覆盖命令不含内嵌双引号 | `make night-run` dry-run rc=0；pilot 实跑 rc=0 |
| 证据脚本 scratch 落进工作树，污染仓库 | ✅已修 | scratch 移到仓库外；日志落 gitignored 运行期证据目录 | `git status --porcelain -uall` 仅 6 个任务文件（含本任务书） |
| 并发重链 gem5.opt 使 pilot 瞬时 rc=2 | ✅已修 | 等可执行 + 仅对该瞬时态重试（≤3，记录 attempts） | 本轮 attempts=1、pilot rc=0；前几轮现场已记录 |
| L1 外部红（chipyard/temp-dirs/台账） | ⏸延后 | 非本任务改动，禁改共享树与其它任务临时目录 | `components/chipyard` 本工作树 diff=0；证据脚本列红项并放行 |

### 第 1 轮 reviewer 验收

**重跑记录（全部本人执行，workdir=任务 worktree，均取真实退出码）**
- `python3 tools/testcases/night_run.py --self-test` ⇒ **rc=0**，`PASS (9/9)`（含 `sleep 5`/1s ⇒ manifest rc=124、报告单列「超时」）
- `python3 tools/testcases/check_night_report.py --self-test` ⇒ **rc=0**，`PASS (13/13)`
- `make night-run NIGHT_DRY_RUN=1` ⇒ **rc=0**、`members=8`；QEMU 4 条与 `495ef679` 版 AST 字面量比对 **4/4 True**（逐字节），`MEMBER_TIMEOUTS` ∩ QEMU = ∅
- guard 独立注入（自造结果 JSON，不走证据脚本）：clean rc=0 / `gem5_only_fail=1` **rc=1** / `qemu_only_fail=3` **rc=1** / 无 `totals` rc=1 / 文件缺失 rc=1（driver 成功路径恒 `return 0`，`run_gem5_se_baseline.py:936`）
- 报告门控自建 fixture：8/8 **rc=0**；缺 `tset:gem5-se-embench` **rc=1** 并点名；空 `arch:gem5-fs` 日志 **rc=1**；`rc=124` **rc=1** 且只报「超时」（不并入普通失败）；`--members` 子集 rc=0 / 默认口径 rc=1 / 未知成员 rc=2
- `make -k check` ⇒ **rc=2**，红项恰为 `check-patch-tree`、`check-milestones-fresh`、`check-temp-dirs`；逐个复核均外部：chipyard 断言⑨在 master 同样红、本 worktree `components/` diff=0；台账红因本 worktree HEAD=`fc9e8a7b`=`495ef679^`（缺派单提交），master 上 `check-milestones-fresh` rc=0；5 个陈旧临时目录全属他任务
- 运行期证据目录下的 `run.sh`：第 1 轮 **PASS=30 FAIL=0 / exit=0**；**独立注入**（guard `sys.exit(0 if bad==0 else 1)`→`sys.exit(0)`，md5 `c07accc…`→`39c81c8…`）⇒ **PASS=28 FAIL=2**，含 `[FAIL] cross-failure result … actual=rc=0`；`cp` 还原 md5 回 `c07accc…` ⇒ **PASS=29 FAIL=1**，唯一 FAIL 为外部 `check-run-artifacts`（在途 `GEM5-032t` 所写的 `runsh-{final,inject}.log`，内容 check-b7/gem5-decode，非本任务）
- 范围/卫生：`git diff --cached` 恰 6 文件、`git diff` 空、`git status -uall` 无未跟踪、无 `scratch/`/`*_tmp*`/`*.orig` 残留（staging 覆盖面 = 6 文件，无多余条目）；完成区 13 行、全文无运行期路径；引用的 `refs/GEM5-021t-baseline-summary.json`、`refs/TESTCASES-104t-dynamic-summary.json`、`docs/TestReports/M11-三平台一致矩阵.md` 均 git 跟踪；无全量落盘产物（运行期测试目录仅 pilot）

**约束核验**：QEMU 四成员语义/预算未变 ✅｜只登记 + 只跑 embench pilot（`--filter=aha-mont64` 1 例）✅｜103t/104t JSON 路径登记进 `night_run.py` 注释/docstring ✅｜未改 `INTEG-059t`/`milestones*`/`contracts` ✅｜两个 self-test 与证据脚本均重跑 ✅

**findings（非阻断，交 architect 收尾处理）**：① 完成区「修改文件」漏列本任务书（103t/104t 均列「本任务书」）；② 完成区坑③「guard 统一用单引号」不准确——guard python 内含 `"`，经 `make night-run NIGHT_MEMBERS=<默认 gem5-se 成员>` 会被 `/bin/sh` 剥掉（模拟实测 argv 丢引号、成员报错）；失败方向为红、非假绿，且默认路径不经 shell 不受影响；③ `make check-night-report` 未透传 `--members`（完成区写法易误读为 make 目标支持）；④ 本 worktree 缺基线提交 `495ef679`，故 worktree 内 `check-milestones-fresh` 红；⑤ gem5-fs 外层 14400s = `run_parity` 单 scope 内层预算且外层计时覆盖两 scope，首轮很可能 rc=124（遗留②已声明待实测校准）；⑥ 证据脚本 L1 白名单固定 3 项，并发任务新增外部红即红（方向偏严、非凑绿）。

**判决：Accepted**（验收标准 1–6 在本人重跑下全部达成；唯一残留 FAIL 为已核实外部红）

#### 收尾（architect，2026-11-09 16:12）

- 判决 **Accepted**（reviewer 16:12 完成；通知未送达，主会话按盘上事实收口）。
- 关键复核：`night-run --self-test` 9/9、`check_night_report --self-test` 13/13；QEMU 四成员 AST 字面量与 `495ef679` **4/4 逐字节相同**；guard 独立注入（`gem5_only_fail=1` ⇒ rc=1）；报告门控缺成员/空日志/rc=124 各 rc=1。
- 6 条 finding：① 完成区漏列任务书、② guard 引号表述 **已修**；③ `make check-night-report` 未透传 `--members`、④ worktree 缺基线提交、⑤ `gem5-fs` 外层 14400s 可能首轮 rc=124、⑥ 证据脚本 L1 白名单偏严 —— **记录不改**（③④ 属工具/基线，⑤ 待首轮实测校准，⑥ 方向偏严非凑绿）。
