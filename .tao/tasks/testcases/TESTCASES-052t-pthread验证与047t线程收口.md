# TESTCASES-052t: pthread 验证与 047t 线程用例收口（线程链 T3）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`INFRA-095t`（T1：musl `__clone` + TP）、`QEMU-065t`（T2：qemu-user 线程语义）、`TESTCASES-047t`（libc-test 两档驱动与基线）、`TESTCASES-049t`（动态档 `-fPIC` 口径）、`INFRA-093t`（`--json-out` / `--work-dir` 运行产物规矩）
**状态**：待开始

> **编号（现场取号，2026-10-19）**：`testcases` 现存最大 = `TESTCASES-051t`（M8 已归档）⇒ 取 **`052`**（`grep -rn 'TESTCASES-052' .tao/` 0 命中）。
> **线程链位置（T3）**：串行链 **T1 `INFRA-095t` → T2 `QEMU-065t` → T3 `TESTCASES-052t` → T4 `LLVM-100t` → T5 `LLVM-117t`**。本册只做 **验证/计数/证据**；不改语料、不改期望值、不放宽分类。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（先读，勿重复查证）

- **基线（权威跑，2026-10-19）**：
  - 静态档 = `.work/tests/authoritative/20261019T063001Z-libc-test-user-static/run.json`：discovered **367** / total **337** / pass **309** / fail **0** / known-fail **4** / blocked **24**；
  - 动态档 = `.work/tests/authoritative/20261019T063847Z-libc-test-user-dynamic/run.json`：total **337** / pass **312** / fail **0** / known-fail **4** / blocked **21**。
- **19 条 `__clone` 目标用例（动态档现场派生；本册必须现场重算并与下表逐条对账）**：
  `functional/popen`、`functional/spawn`、`functional/pthread_cancel`、`functional/pthread_cancel-points`、`functional/pthread_cond`、`functional/pthread_mutex`、`functional/pthread_mutex_pi`、`functional/pthread_robust`、`functional/pthread_tsd`、`functional/sem_init`、`regression/pthread-robust-detach`、`regression/pthread_cancel-sem_wait`、`regression/pthread_cond-smasher`、`regression/pthread_cond_wait-cancel_ignored`、`regression/pthread_exit-cancel`、`regression/pthread_exit-dtor`、`regression/pthread_once-deadlock`、`regression/pthread_rwlock-ebusy`、`regression/raise-race`。
- **静态档多 1 条**：`regression/pthread_create-oom`（现场根因 = `setrlimit(RLIMIT_AS)` 直通宿主 ⇒ qemu `SIGTRAP`，`ISS-257`；**不是** `__clone` 缺口）。本册**不计入 19 条目标**；其 pass/blocked 抖动按 flake 如实披露。
- **驱动能力**：`tools/testcases/run_libc_test_user_suite.py` 支持 `--link-mode {static,dynamic}`、`--filter <regex>`、必填 `--json-out`、`--work-dir`（`INFRA-093t`）；DSo/extra TU 由 `EXTRA_CASE_SOURCES` 与 `.mk` 派生；当前 4 条 `dlopen` 用例在动态档按 `DYNAMIC_EXCLUSION_REASONS` 为 `excluded`（归 T5）。
- **关闭对象**：`ISS-252`（musl 无 `__clone` ⇒ 线程/`posix_spawn`/`popen` 全不可用）⇒ 本册验收后 `closed` + `resolved_by: TESTCASES-052t`；`ISS-257`（`pthread_create-oom` 的 `RLIMIT_AS` 直通）**不在**本册关闭面（T2 未修则保持 open）。

## 接口规范

- **输入**：
  - T1/T2 完成后的安装根（`qemu-dadao`、`libc.a`/`crt1.o`/`libc.so`/`ld-musl-dadao.so.1`）；
  - `.work/source/libc-test`（`patchless`，**只读**；不改语料、不改 `.mk`、不改期望值）；
  - 上述两份基线 `run.json`（逐例 `case`/`klass`/`reason`）。
- **输出**：
  - 目标子集两档跑 + 全量两档跑（均显式 `--json-out` + `--work-dir`，落 `/tmp/opencode/TESTCASES-052t/`；**禁**写 `.work/tests/authoritative/` 或 `.work/log/testcases/` 作权威）；
  - 逐例 diff 报告（基线 vs 本轮）：19 条 `blocked→pass`、其余 `case→klass` 不变；
  - `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject`）+ 日志 `.work/log/testcases/TESTCASES-052t-*.log`；
  - 本册完成区（≤30 行）。
- **约束（硬）**：
  - **前置安装根**：T1/T2 的 `build-musl` / `build-musl-shared` 已完成；若 T2 改过 `components/qemu/**`，其 `make install-host` 必须已跑且安装根新鲜（贴时间戳/`--version`）；本册**不跑** `install-host`、不改 `components/**`；
  - **判据不得放宽**：不改 `known-fail` 依据、不改 `excluded`、不改超时表、不改 `GAP_SIGNATURES` 去「洗掉」失败；19 条必须有真实 `pass`；
  - 失败**保留现场并继续**；若某条失败根因落在 T1/T2（clone/TP/信号/futex），**停止本册**、把现场回填 T1/T2，不得在本册用分类掩盖；
  - 全量两档按长任务纪律：预计每档 **10–30 min**（现场申报）；>10 min 用 `setsid nohup` + `XXX_EXIT=$rc` 标记，**子代理不空等**，由主会话按盘上事实续链；
  - 不与其它测试集并发（`ISS-229`）；不改 `tools/testcases/**`（除本册证据脚本，且 `.work/` 不入 git）。

## 做

### 阶段 0：现场派生与前置

- 从两份基线 JSON **现场派生**「`klass=blocked` 且 `reason` 命中 `no __clone`/`__clone`/`posix_spawn`/`popen`」的用例集；打印 **ID 清单 + 计数**。
- 断言：动态档 = **19**；静态档 = **20**（多 `pthread_create-oom`）。若计数不符 ⇒ 打印差异并**停下报告**（基线或驱动已漂移）。
- 断言 T1/T2 产物在位（`__clone` 来自 arch 对象、C1/C2 探针通过）；安装根时间戳新鲜。

### 阶段 A：目标子集两档（快跑）

- 用**精确 regex**（19 条 ID 的 alternation，锚定 `^...$`）跑：
  ```
  python3 tools/testcases/run_libc_test_user_suite.py --link-mode static \
    --filter '<19 条 exact regex>' --work-dir /tmp/opencode/TESTCASES-052t/sub-static \
    --json-out /tmp/opencode/TESTCASES-052t/sub-static.json
  ```
  动态档同法（`--work-dir .../sub-dynamic`）。
- 期望：静态 19/19 `pass`（`pthread_create-oom` 不在 filter 内）；动态 19/19 `pass`；`fail=0`、`excluded=0`（子集内）、无 `timeout`。
- 若任一条失败：保留 stdout/stderr/exit，按首错定位；根因属 T1/T2 ⇒ 回填并停止；根因是新缺口 ⇒ 登记 `issues.yaml`（P2/P3 按影响）+ 本册如实留白，**不得**改标签。

### 阶段 B：全量两档（无回归硬判据）

- 两档全量（不带 `--filter`），`--work-dir /tmp/opencode/TESTCASES-052t/full-<mode>`、`--json-out /tmp/opencode/TESTCASES-052t/full-<mode>.json`；`setsid nohup` + `EXIT` 标记（按现场耗时）。
- 用脚本逐例对账基线：
  - **必须**：19 条目标全部 `blocked→pass`；
  - **必须**：其余用例 `klass` **逐例不变**；`excluded` 集合不变（30 条）；`known-fail` 4 条不变（TLS 3 + `strptime` 1）；
  - 静态 `pthread_create-oom`：保持 blocked 或偶然 pass 均记录（`ISS-257` flake）；若 pass，不计入 19 条增益、不得据此改基线；
  - 计数（以逐例对账为准，现场派生）：静态期望 pass **328** / blocked **5**（24−19；含 `pthread_create-oom`）/ known-fail 4；动态期望 pass **331** / blocked **2**（`musl/pleval`、`regression/flockfile-list`）/ known-fail 4。若 OOM flake 变动，按实际逐例解释。
- 任何 `pass→non-pass` / `known-fail→fail` / `excluded` 漂移 ⇒ **FAIL**，停下定位（不得重跑掩盖）。

### 阶段 C：证据、issue 与门控

- `.work/evidence/<任务ID>/run.sh`：default 与 `--inject`；**≥2 条可达 FAIL**：
  1. 注入「目标 regex 少一条」（临时脚本副本）⇒ 目标计数 19 断言 FAIL；还原 ⇒ 回绿；
  2. 注入「把一个已知 blocked 的非目标用例（如 `functional/setenv-oom`）混入目标集」⇒ 「目标全 pass」断言 FAIL；还原 ⇒ 回绿；
  3. 可选：把基线对账期望改成 `blocked 24→23` ⇒ 逐例 diff 断言 FAIL。
- 关闭 `ISS-252`（`resolved_by: TESTCASES-052t`；`notes` 追加「19 条转 pass + 两档逐例对账」）；`ISS-257` 保持 `open` 并在 notes 追加本册现场（若 flake 仍在）。
- 门控各留 rc：`make check`（L1）、`check-tasks`、`check-issues`、`check-knowledge-refs`、`check-no-residue`、`check-run-artifacts`；任务收尾 `make check-modules`（L2，串行）。

## 验收标准

1. **目标 19/19 转 `pass`**：静态档（19 条 filter）与动态档（19 条 filter）均 **19/19 pass**、`fail=0`；贴 ID 清单、真实 JSON 计数与退出码。
2. **无回归（硬）**：全量两档逐例对账 — 除 19 条 `blocked→pass` 外，**0 条 `pass→non-pass`**、**0 条 `known-fail`/`excluded` 漂移**；`excluded` 仍 30 条；`fail` 仍 0；计数按现场派生并解释 `pthread_create-oom` flake。
3. **`ISS-252` 关闭**：`issues.yaml` 回填 `resolved_by: TESTCASES-052t`，notes 含证据指针；`check_issues.py` rc=0。`ISS-257` 若未修保持 open，并在 notes 记录本册现场。
4. **证据与可达 FAIL ≥2**：`run.sh` 非交互、逐项 rc；两条注入各自「FAIL → `cp`+md5 还原 → 回绿」真实输出；禁恒真、禁 `git checkout/restore/stash`。
5. **运行产物规矩**：所有调用带 `--json-out` + `--work-dir`；未写 `authoritative/`/固定名日志；日志命名 `TESTCASES-052t-<用途>.log`。
6. **边界**：不改语料（`libc-test` patchless）、不改 `.mk`、不改驱动判定逻辑、不改 `spec/`/`contracts/`/`.tao/contracts/**`/`components/**`；不提交 git、不 push；完成区 ≤30 行。
7. 长任务按纪律：`setsid nohup` + `EXIT` 标记；`timeout` 的 `124` 判 FAIL，不空等。

## 不做项（显式）

1. **修 `__clone` / qemu 线程语义** ✗ —— T1 `INFRA-095t` / T2 `QEMU-065t`（本册只验证）。
2. **`__thread` TLS 3 例** ✗ —— T4 `LLVM-100t`（本册 `known-fail` 依据不变）。
3. **`dlopen` 4 例 / 动态 TLS** ✗ —— T5 `LLVM-117t`（本册动态档仍 `excluded` 30 条含 4 条）。
4. **`ISS-257`/`ISS-255` 的 `RLIMIT_AS` 虚拟化** ✗ —— qemu 面独立项，不因线程链顺手改。
5. **改期望值 / 把 fail 归入 `known-fail` / 扩 `excluded`** ✗（严格禁止）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
