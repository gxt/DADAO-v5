# TESTCASES-049t: libc-test 动态档用户 TU 改 `-fPIC`（`ISS-259` 执行落点）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（两档 runner + 第 5 轮动态档真值 `298 / 0 / 8 / 31`；任务级 `状态` 仍 `待开始`）；`ISS-259`（用户裁定 ②，`open`）；`ADR-0026 D7②` / `contract-dynlink §10②`（COPY 不发射的**契约依据不变**，本册只在**测试侧**规避）；`ISS-247`（基址 = lld 默认 `0x10000`，禁 `-T dadao.lds`）；`ISS-248`（`blocked>0 ⇒ rc=1` 口径）、`ISS-250`/`ADR-0030`（`math/lgammal` 归 `known-fail`）、`ISS-229`（同时只跑一个测试集）
**状态**：待验收

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
**测试结果**：动态档用户 TU 编译加 `-fPIC`（静态档不动）后按派单**只跑测**（未改 `musl`/LLVM/QEMU 源码、未动 `Makefile`、未 `install-host`，产物未重建）：**动态 discovered 367 / excluded 30 / total 337：pass 305、fail 0、known-fail 9、blocked 23**（driver rc=1 仅 `blocked>0`，`ISS-248`；**571 s**）；**静态档对照 303 / 0 / 9 / 25，337 例分类与 guest exit 逐例零变化**（**509 s**）。对照基线（动态 298/0/8/31）转移**恰 8 条**、无其它变动：
- `blocked→pass` **7**：`functional/env`、`math/{lgamma,lgammaf}`、`regression/{fflush-exit,fgetwc-buffering,rewind-clear-error,setvbuf-unget}`（guest exit 0；证据脚本独立 qemu 重放逐例 0）。
- `blocked→known-fail` **1**：`math/lgammal`（basis=`ADR-0030`；现场 `ulperr -10.465` + target `LDBL_MANT_DIG=53`）。
- `musl/pleval` **仍 `blocked`**：`ld.lld: error: undefined symbol: __pleval`（上游 `src/musl/pleval.mk` 动态档不构建，不改判）。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（`DYNAMIC_USER_CFLAGS = ("-fPIC",)`；`build_and_run` 仅 `cfg["mode"]=="dynamic"` 追加；逐例 `compile_cmd` 入 JSON/report 供审计）；本任务书；`TESTCASES-047t`（追加一节 + `阶段进度`）；`.tao/knowledge/issues.yaml`（`ISS-259`）；gitignored：`.work/evidence/TESTCASES-049t/{run.sh,baseline-{static,dynamic}.json}`、`.work/log/testcases/{libc-test-user-{static,dynamic}.{json,log,stdout,stderr},049t-{static,dynamic}.EXIT,049t-evidence-{default,inject}.log}`。
**验收结果**：① 驱动面：动态档 337 例 / 416 TU 的编译行**各含恰好 1 个** `-fPIC` 且在 `-c` 前；静态档 **0** 个，且 `BASE/API/PER_CASE/MUSL_USER_INCLUDE_DIRS` 与 `git show HEAD:` 版 AST 逐项相等、命令行构造仅 `... + extra + mode_cflags + PER_CASE ...`（`mode_cflags` 由 dynamic 判定）⇒ 静态行逐字节不变。② 独立审计（`.work/evidence/TESTCASES-049t/run.sh` default **62 PASS / rc=0**）：转移集**从基线 JSON 现场派生**（含 `copy relocation` 的 `blocked` 行）而非写死，计数由基线+转移推导（305/9/23）；`fail=0`、`total == discovered − excluded`、`closure_ok`/`classification_ok`；`lgammal` 依据现场重算；8 张新链镜像 `PT_INTERP=/lib/ld-musl-dadao.so.1`、base `0x10000`、无 `-T`。③ `--inject` **rc=0**（3 处可达 FAIL，`cp`+md5 还原，driver md5 `4e2fc691…`）：I1 清空 `DYNAMIC_USER_CFLAGS` ⇒ 8 例真跑复核重回 `blocked`（`copy relocation`）且 `-fPIC` 审计拒；I2 `functional/env` 记录改回 `blocked` ⇒ 转移审计拒；I3 给 `BASE_CFLAGS` 注入 `-fPIC` ⇒ 静态真跑记录含 `-fPIC`、静态不变量审计拒。④ 门控各留自身 rc：`check-musl-freshness` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-no-residue` 0、`check_issues.py` 0、`make check`(L1) 0。⑤ 判据未放宽：`known-fail` 仍走逐例依据表，`-fPIC` 只改编译选项、未改任何期望值/分类准入。
**新发现/坑**：① `-fPIC` 只需给**用户 TU**：harness `libtest.a` 只用 `write(1,…)`（`src/common/print.c`），不引用 libc 数据对象 ⇒ harness 无需 PIC，COPY 缺口全部来自用例 TU。② 动态档"两档分类对齐"：`math/lgammal` 静态 `known-fail`、动态曾 `blocked`，加 `-fPIC` 后回 `known-fail`（`ADR-0030`）⇒ 两档 9 条 `known-fail` 集合一致。③ 单档耗时主要来自 `timeout after 60s`（动态 8 / 静态 7 例线程用例，`__clone` 缺口）——8×60 s 已占动态档 571 s 的 84%，与基线同形，非本轮引入。④ 计数不写死落地方式：证据脚本以基线 JSON 的 COPY 行派生期望转移集与三档计数，注入"去掉 `-fPIC`"即从 8 例真跑回到 8 条 `blocked` 触发 FAIL。
**遗留问题**：`musl/pleval` 动态档仍 `blocked`（上游 `.mk` 本不构建，非缺陷）；`blocked 23` 其余（`ISS-252/253/254/255` + OOM flake）与 `-fPIC` 无关，沿用 `TESTCASES-047t` 第 5 轮归属；`P4` golden 对照、`ISS-246` 修复不在本册；`ISS-259` 已按现场置 `closed`（待 reviewer 验收复核）。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查驱动改动（`DYNAMIC_USER_CFLAGS` 常量、`build_and_run` 的 `mode_cflags` 插入点、`Case.compile_cmds` 记账与 JSON/report 落盘）与证据脚本（两档计数/转移派生、`git show HEAD:` AST 常量比对、3 处注入），并以**两档真跑**（动态 571 s / 静态 509 s）与 default/`--inject` 现场闭合对齐，未抽样。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 证据脚本把新增 `DYNAMIC_USER_CFLAGS` 一并纳入「flag 表与 HEAD 相等」比对 ⇒ 首跑必假红 | ✅已修 | 四个既有常量与新增常量分开校验 | default 首跑该行为 `[FAIL]`（实见），修后 64 PASS / rc=0 |
| F2 | 「静态零变化」可能来自**未重跑的旧 JSON**（旧驱动无 `compile_cmd` 字段）⇒ 假绿风险 | ✅已修 | 两档各增「每条记录都带 `compile_cmd`」反陈检查 | 337+337 条全带；I3 用**静态真跑**产物触发该分支 |
| F3 | 并发守卫把「同一 shell 命令行里提到驱动路径」误判为并发驱动（我方 `md5sum tools/…` 所致，非脚本缺陷） | ✅已处置（改跑法） | 未改守卫（与 `TESTCASES-047t-dyn` 同款、真并发时有据） | 分离命令后 `--inject` **87 PASS / rc=0**；守卫行为已披露 |
| F4 | `-fPIC` 是否会把静态档或期望值带偏 | ✅已核（不改） | 只加编译选项；`BASE/API/PER_CASE` 与 HEAD 相等，静态 0 个 `-fPIC` | 静态 303/0/9/25、337 例 class/exit 零 diff；`known-fail` 依据表未动 |
| F5 | 动态档 `math/lgammal` 是否被「顺手改判」 | ✅已核 | 仍走 `ADR-0030` 逐例依据（`ulperr` + ADR Accepted/D1/D7 + 目标 `LDBL_MANT_DIG=53`），无新准入 | 行内 `known_fail_basis=ADR-0030` + `known_fail_evidence` 现场重算；审计复算 PASS |
| F6 | 注入 1 后 8 例是否**真**回到 blocked（而非仅记录被改） | ✅已核 | 注入用驱动**真编译/真链接**跑 8 例 | driver rc=1、blocked=8、pass=0、行内 `copy relocation`；`cp`+md5 复原后回绿 |

判决：本笔 finding 全部处置完毕（F3 为跑法说明、非代码缺陷）；两档真值、逐例记账、证据脚本与门控均完成。按本次派单**不改**本册 `**状态**`（保持 `待开始`，由主会话收尾时更新）。

#### 第 1 轮 reviewer 验收
（审查者独立重跑、约束核验、判决）
