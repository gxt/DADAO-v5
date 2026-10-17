# TESTCASES-049t: libc-test 动态档用户 TU 改 `-fPIC`（`ISS-259` 执行落点）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（两档 runner + 第 5 轮动态档真值 `298 / 0 / 8 / 31`；任务级 `状态` 仍 `待开始`）；`ISS-259`（用户裁定 ②，`open`）；`ADR-0026 D7②` / `contract-dynlink §10②`（COPY 不发射的**契约依据不变**，本册只在**测试侧**规避）；`ISS-247`（基址 = lld 默认 `0x10000`，禁 `-T dadao.lds`）；`ISS-248`（`blocked>0 ⇒ rc=1` 口径）、`ISS-250`/`ADR-0030`（`math/lgammal` 归 `known-fail`）、`ISS-229`（同时只跑一个测试集）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

> **用户原话（逐字；渠道 = 经主会话问答，2026-10-17 深夜）**：「**ISS-262: 1；ISS-259：2；ISS**」
> 主会话据此复述请其确认的两条之一：`ISS-259` = ② **动态档用户 TU 改 `-fPIC`** ✓

- **现象（`TESTCASES-047t` 动态档第 5 轮现场）**：动态档 `blocked 31` 中 **9** 例属链接期缺口 —— **COPY 8**：`functional/env`（`environ`）、`math/{lgamma,lgammaf}`（`signgam`）、`regression/{fflush-exit,fgetwc-buffering,rewind-clear-error,setvbuf-unget}`（`stdin`/`stdout`）、`math/lgammal`（`signgam`）⇒ `ld.lld: error: cannot create a copy relocation for symbol …`；**`musl/pleval` 1** = `undefined symbol: __pleval`（上游 `src/musl/pleval.mk` 明写动态档不构建）。
- **裁定 = 候选 ②**：**动态档**用户 TU 编译加 `-fPIC`（同例 `functional/env` 实测 link rc=0 / guest exit 0，证据脚本已固化）。
- **边界**：`lld`/`contract-dynlink`/`ADR-0026` 均**不动**（COPY 拒绝仍是已声明行为）；`pleval` 属上游口径 ⇒ 仍 `blocked`；静态档**不**加 `-fPIC`。

## 接口规范

- **输入**：`tools/testcases/run_libc_test_user_suite.py`（现 `BASE_CFLAGS`/`API_CFLAGS`/`PER_CASE_CFLAGS` 与 mode 判定）；`TESTCASES-047t` 第 5 轮的真值与分类表（作为**基线**比对，不重算）。
- **输出**：
  1. 驱动改动：**仅动态档**用户 TU 的编译命令行追加 `-fPIC`（静态档命令行**逐字节不变**，用 `-###`/日志留证）；其它口径（`-O`、`-I`、`-c`、链接参数）不变。
  2. 动态档复跑：`.work/log/testcases/libc-test-user-dynamic*.{log,json}` + 与基线的逐例 diff（转移只允许下述 8 条）。
  3. 静态档复跑（不受影响证明）：`303 / 0 / 9 / 25` 逐例零变化。
  4. 证据：`.work/evidence/<任务ID>/run.sh`（default + `--inject`）+ `.work/log/<模块>/**`。
  5. 本册完成区 + `milestones.md` 行 + `ISS-259` 处置（验收后 `closed` + `resolved_by: TESTCASES-049t`）。
- **约束**：
  - **不改**测试集内容（`patchless`）、**不改**期望值、**不改** `known-fail` 依据表准入（`ISS-246`/`ISS-251`/`ADR-0030` 之外不得新增条目）；
  - **不改** lld / `contracts/` / `.tao/contracts/**` / `components/**`；
  - 同改共享文件的任务**串行**（`ISS-229`）；跑测期间不并发其它测试集。

## 验收标准

1. **驱动面**：动态档编译行含 `-fPIC`（逐例日志/`-###` 留证）；静态档编译行**逐字节不变**（同次对照）。
2. **转移（逐例记账，禁止只报总数）**：COPY 8 例中 **7 例 `blocked→pass`**（`functional/env`、`math/{lgamma,lgammaf}`、`regression/{fflush-exit,fgetwc-buffering,rewind-clear-error,setvbuf-unget}`）；**`math/lgammal` `blocked→known-fail`**（依据 `ISS-250` + `ADR-0030` `D1`(binary128)/`D7`(→`M9`)，须带 `known_fail_basis`）；**`musl/pleval` 仍 `blocked`**（reason = 上游 `pleval.mk` 动态档不构建）。
3. **计数（预期，须现场派生核对）**：动态档 `pass 298→305`、`known-fail 8→9`、`blocked 31→23`、`fail=0`、`total 337`（`discovered 367 / excluded 30`）；静态档 `303 / 0 / 9 / 25` **不变**；两档 `fail=0` 与 `total == discovered − excluded` 由脚本断言。
4. **判定口径不变**：`blocked>0 ⇒ rc=1`（`ISS-248`，预期 driver rc=1）；分类闭包/逐例依据反向校验通过（`pass` 例不得带 `known_fail_basis`）。
5. **可达 FAIL**：≥2 注入 —— ① 去掉动态档 `-fPIC` ⇒ 8 例重回 `blocked` 且「转移集合」断言 FAIL；② 把预期计数写死为错值（或改 `pass` 期望）⇒ FAIL；`cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
6. **门控（各留自身 rc）**：`make check`(L1)、`check-tasks`、`check-knowledge-refs`、`check-no-residue`、`python3 tools/infra/check_issues.py`。
7. 完成区（**≤30 行**）与真实输出**逐条对齐**；`ISS-259` 处置落纸。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-049t/`；workdir = 仓库根、相对路径；禁 `cd` 出界；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；长输出落 `.work/log/testcases/`；**禁** `cmd | tee` 吞码。
4. **只动任务范围**（驱动 + 本册），越界须披露。
5. **失败保留现场并继续推进**；**只在需用户语义裁定**时留问（如「某例 `-fPIC` 后仍 `blocked` 且非 `pleval`」⇒ 保留分类 `blocked` 并如实记账，不得改判 `pass`）。
6. **计数不写死**：转移条数与分类一律**运行期派生**并与基线逐例 diff。
7. 证据脚本非交互、任一失败非零退出、含可达 FAIL 自检。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立重跑、约束核验、判决）
