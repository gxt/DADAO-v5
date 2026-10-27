# TESTCASES-083t: L3 结果报告与 check-milestone 机检

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t、TESTCASES-082t
**状态**：待验收

## 背景
`TESTCASES-076t` 只加了夜跑报告存在性；`check-milestone` 的「L3 结果」仍无机检载体（076 遗留⑥），无法审计 `check-full` 是否真的全绿。

## 目标
1. `check-full` 外层（或新包装目标）在运行时写机器可读报告：
   - `.dadao/tests/l3/<UTC>/manifest.tsv`：`scope<TAB>suite<TAB>rc<TAB>log`，逐成员一行；
   - `meta.json`（命令/时间/commit/工具链摘要）；
   - `run.log`（汇总 + `[exit marker] rc=N`）。
   复用 `night_run.py` 的 manifest 语义，避免两套格式。
2. 新增 `check-l3-report`（里程碑收尾专项，不入 L1/L2/L3 日常）：
   - 最新 L3 报告存在、结构完整、至少覆盖四 scope、任一 rc≠0 ⇒ FAIL；
   - 未跑 L3 ⇒ 明确 FAIL（不是 SKIP）；
   - `--self-test` 覆盖：缺文件、空 manifest、rc 非零、缺 scope、伪造全绿等可达 FAIL。
3. `check-milestone` 增加对 `check-l3-report` 的依赖（与 `check-night-report` 并列）。
4. 文档：`docs/Process-07`/`Process-09`、`tests/README` 说明报告落点/格式/触发点。

## 验收
- `check-l3-report --self-test` rc=0（每个反例可达 FAIL）；无报告时 rc=1 且报错明确。
- 用**临时 fixture**（不跑全量）构造全绿/红报告，验证 PASS/FAIL 与 `check-milestone` 依赖接线。
- `make check` rc=0；`make check-milestone` 的报告项在 fixture 下可验证（真实 L3 未跑时按设计红）。
- 证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-083t/`。

## 约束
- 只改 `tools/testcases/`、`Makefile`、`docs/Process-07`/`09`、`tests/README`、任务书/milestones；不改测试期望。
- **不跑全量 `check-full`/夜跑**（用户 2026-10-27：全量+夜跑不下发）；fixture/自检即可。
- 不提交、不 push。

## 完成区

**状态**：待验收

### 修改文件
- `tools/testcases/l3_run.py`（新）：`make check-full` 包装，逐成员执行 + 写 `l3/<UTC>/` 三件套（复用 `report_io`）
- `tools/testcases/check_l3_report.py`（新）：L3 报告门控（存在/结构/四 scope/全绿/exit marker 一致 + `--self-test` 十二类）
- `tools/testcases/report_io.py`（新）：night/L3 manifest/meta 格式单一真源（`night_run.py` 改用）
- `tools/testcases/night_run.py`、`manage_tests.py`：复用 `report_io`；`SCOPE_MAP` 登记 `l3`、`test-repro SCOPE=l3` 显式拒绝
- `Makefile`：`_locked-check-full` 改调 `l3_run.py`；新增 `check-l3-report`；`check-milestone` 加依赖 + help/注释
- `docs/Process-07`、`docs/Process-09`、`tests/README.md`：报告落点/格式/触发点与门控登记
- `.tao/knowledge/milestones.md`、本任务书：状态同步

### 验收命令与结果
- `check_l3_report --self-test` → rc=0，**12/12**（缺 l3/、空 l3/、无三件套、空 manifest、rc 非零、缺 tset scope、缺 fp-clmul、伪造全绿×2、缺 meta、绿、指定戳不存在）
- `l3_run --self-test` → rc=0，**9/9**；`night_run --self-test` 6/6、`manage_tests --self-test` 8/8（回归）
- 无报告：脚本 rc=**1**（明确「L3 报告目录不存在…先跑 make check-full」），`make check-l3-report` rc=2
- fixture（`/tmp/opencode/TESTCASES-083t/`）：绿报告 `make check-l3-report TESTS_ROOT=…` rc=0；红成员/缺 scope/伪造全绿/缺 commit 均 rc=1；`make -n check-milestone` 含 `check_l3_report.py`；fixture（夜跑+L3 双绿）跑 `make check-milestone` 两个报告门控均 PASS，真实无 L3 报告 ⇒ 按设计红
- 证据 `./.work/evidence/TESTCASES-083t/run.sh` → **30/30 PASS** rc=0；`--inject` → **7/7 PASS**（注入后门控错放行→`cp`+md5 还原→回红；md5 `13fe2f12…` 前后一致）
- `make check` → rc=0；`l3_run --dry-run` 0 条 `check-tset-*`、保留 `test-m6`（082t 不变量）

### 新发现/坑
- L3 成员清单真源迁到 `l3_run.DEFAULT_MEMBERS`（Makefile 不再列 `_locked-check-full` 前置）；082t 证据的 `make -n _locked-check-full` 盘点法失效，改用 `l3_run --dry-run`。
- `.dadao/tests/l3/` 必须在 `manage_tests.SCOPE_MAP` 登记，否则 `clean-tests`/`test-repro`「未归属即红」误伤；报告不可逐字节复现 ⇒ repro 显式拒绝。
- 报告门控要求 `log` 列文件真实非空：self-test 假成员必须用 `echo`（裸 `true` 日志为 0 字节 ⇒ 假红）；L3 目录名不带 `Z-`（避 `check-run-artifacts` A2 运行目录语义）。
- 工具链摘要只强制 `clang`/`qemu` content id：L3 的 inst/arch/unit 不依赖 musl，`libc` 缺失不应把合法全绿报告判红。

### 遗留
- 无。未跑 `check-full`/`check-night`（用户 2026-10-27 裁定不下发）；真实 L3 报告未生成，`check-milestone` 的 L3 项按设计红。

## 审阅记录

### 第 1 轮 engineer 自审

- 逐行核对 `l3_run.run_l3`：目录建/拒覆盖、逐成员 rc、manifest/meta/run.log 落盘、exit marker；成员清单与 082t 后 L3 一致（无 tset smoke/full）。
- 逐条核对 `check_l3_report.check`：存在性→三件套→meta→结构/日志存在→四 scope+成员→rc→marker 一致性；每步均可达 FAIL（self-test 12 例）。
- 包装链路核对：`check-full` 经 gate_lock 重入 `_locked-check-full` → `l3_run` → 嵌套 `make <member>`；gate_lock 以「持有者 pid 是祖先」放行，链条成立。
- 证据脚本核对：每条断言有可达 FAIL（无恒真）；注入用 md5+grep 证明非空，`cp` 还原后 md5 对账，未用 `git checkout/restore`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 门控原要求 toolchain.libc 非空，但 L3 不依赖 musl ⇒ 全绿报告可被误判红 | ✅已修 | `REQUIRED_TOOLS=("clang","qemu")`，libc/lld 仅记录 | self-test 绿例 rc=0；文档同步 |
| 成员日志名只含 suite，跨 scope 同名 suite 会撞名 | ✅已修 | 日志名改 `check-l3-<stamp>-<scope>-<suite>.log` | self-test 9/9；证据 28/28 |
| 证据脚本 `cp -a` 到已存在目录会嵌套；manifest 日志绝对路径仍指原 fixture | ✅已修 | 复制前 `rm -rf` + sed repoint 日志列 | 证据 28/28（forged-log 可达红） |
| 注入文件尚未提交（untracked），`git diff --name-only` 恒空 ⇒ 「空注入」假绿 | ✅已修 | 改以 md5 变化 + grep 双证注入非空；还原 md5 对账 | `--inject` 7/7；md5 `13fe2f12…` 前后一致 |

- 判决：无未修 finding ⇒ 状态 `待验收`。
