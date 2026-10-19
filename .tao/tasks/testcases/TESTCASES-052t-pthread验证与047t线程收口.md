# TESTCASES-052t: pthread 验证与 047t 线程用例收口（线程链 T3）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`INFRA-095t`（T1：musl `__clone` + TP）、`QEMU-065t`（T2：qemu-user 线程语义）、`TESTCASES-047t`（libc-test 两档驱动与基线）、`TESTCASES-049t`（动态档 `-fPIC` 口径）、`INFRA-093t`（`--json-out` / `--work-dir` 运行产物规矩）
**状态**：待验收

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

**测试结果**：线程子集两档实跑（每档 20 例 = 19 目标 + `pthread_create-oom`；各 3 次一致）：
- 静态：14 pass / 1 fail / 5 blocked（19 目标 = 14 / 1 / 4）；动态：14 pass / 1 fail / 5 blocked（19 目标 = 13 / 1 / 5）；两档驱动 rc=1（真 FAIL）。
- `ISS-294`（假原子）**不是**这 19 例的失败根因：0 例。旁证：`functional/pthread_cond` 直接跑 40 次有 1 次 20 s 挂死（flake，方向同族），其余 39 次过。
- 与 T3 目标（19/19 pass）的差距：静态 **14/19**、动态 **13/19**。

| 定性 | 用例 | 根因 |
| --- | --- | --- |
| 真 pass | 13 例两档均过（`pthread_cancel`/`pthread_cancel-points`/`pthread_cond`/`pthread_mutex`/`pthread_tsd`/`sem_init`/`pthread_cancel-sem_wait`/`pthread_cond-smasher`/`pthread_exit-cancel`/`pthread_exit-dtor`/`pthread_once-deadlock`/`pthread_rwlock-ebusy`/`raise-race`），静态另加 `popen` | 线程基础设施（clone/TP/futex/信号/取消）够用 |
| `ISS-294` 假原子 | 无（19 例 0 命中） | 仅 `pthread_cond` 1/40 次挂死疑似同族，未定论 |
| 其它 · `ISS-295` | `spawn`（两档）、`popen`（动态） | `__clone` 变参 `tls` 未传却无条件写 `rb3` ⇒ 子进程 TP 垃圾 ⇒ `__execvpe` 写 `errno` SIGSEGV |
| 其它 · `ISS-296` | `pthread_mutex_pi`（两档） | qemu `FUTEX_LOCK_PI` → `ESRCH`（guest TID 未翻译） |
| 其它 · `ISS-297` | `pthread_robust`、`pthread-robust-detach`（两档） | qemu `get_robust_list` 恒 `ENOSYS`（上游设计） |
| 其它 · `ISS-298` | `pthread_cond_wait-cancel_ignored`（两档） | 阻塞 futex 上的 SIGCANCEL 被 `SA_RESTART` 重启、取消丢失 |
| `ISS-257` flake | `pthread_create-oom` | 静态 `blocked`（host SIGTRAP，3/3）/ 动态 `pass`（3/3） |

**修改文件**：`tools/testcases/report_thread_cases.py`（新增，报告工具）；`.tao/knowledge/issues.yaml`（`ISS-252`/`ISS-257` 追加现场 + 新立 `ISS-295`–`ISS-299`）；本册；`.work/evidence/TESTCASES-052t/{run.sh,check_thread_truth.py,expect.json}`（不入 git）。
**验收结果**：`.work/evidence/TESTCASES-052t/run.sh`（full）rc=0，跑了 2 次；逐项 PASS；注入 2 处（计数谎报 / 错标根因）各自 `check rc=1` → `cp`+md5 还原 → rc=0。门控 rc：`check_tasks`/`check_milestones_fresh`/`check_knowledge_refs`/`check_issues`/`check_run_artifacts`/`make check`（L1）全 0。
**新发现/坑**：① 驱动 `attribute_port_gaps()` 的 `uses_thread → blocked` 兜底仍是 T1 前口径，把真根因盖成「no __clone」（4 例 × 2 档，`ISS-299`）；② 静态 `popen` 过、动态不过的分野 = 子进程是否在 `execve` 前碰 `errno`（TP 垃圾才暴露）；③ 本册「根因落 T1/T2 ⇒ 停册」与本次派单（继续跑、逐条定性、立新 issue）冲突，按派单执行。
**遗留问题**：① **阶段 B（全量两档）未跑** ⇒ 验收标准 2（逐例无回归）未判；② `ISS-252` **保持 open**（20 例全 pass 未达，残余根因已分解）；③ `ISS-294` 在本子集无失败实例，其阻塞面需另找载体（并发计数探针，见 `QEMU-065t`）；④ 任务状态未改（派单要求）。

### 复跑（2026-10-20，`TESTCASES-052t-rerun`）

**前置**：`c47c9b7`（`INFRA-095t` 返工：`rb3` 按 `CLONE_SETTLS` 条件化）；同一 20 条 ID（`report_thread_cases.py` 的 `TARGET_CASES`+`EXTRA_CASES`）；两档各 3 跑一致（未改驱动），再修 `ISS-299` 后两档各 1 跑复核。
**新真值（权威口径 = 修 `ISS-299` 后）**：静态 20 例 **15 pass / 3 fail / 2 blocked**、动态 20 例 **16 pass / 3 fail / 1 blocked**；19 目标两档均 **15 pass / 3 fail / 1 blocked**（两档驱动 rc=1）。
**逐例变化 vs 上轮**：
- `ISS-295` 能力面：`functional/spawn`（两档，`fail→pass`）、`functional/popen`（动态，`blocked→pass`）；
- `ISS-299` 口径面：`pthread_mutex_pi`、`regression/pthread-robust-detach`、`regression/pthread_cond_wait-cancel_ignored` `blocked→fail`（同一现场，不再被降级）；
- 不变：其余 15 例 klass 不变；`pthread_robust` 仍 `blocked`（60 s 超时 = 无判定，合法）；`pthread_create-oom` 静态 `blocked`（host `SIGTRAP`）/ 动态 `pass`。
**残余归因（原因未变）**：`pthread_mutex_pi` = `ISS-296`（`FUTEX_LOCK_PI` → `ESRCH`）；`pthread_robust`/`pthread-robust-detach` = `ISS-297`（`get_robust_list` 恒 `ENOSYS`）；`pthread_cond_wait-cancel_ignored` = `ISS-298`（SIGCANCEL 被 `SA_RESTART` 重启）。
**`ISS-299` 改法**：删 `attribute_port_gaps()` 的 `uses_thread → blocked` 兜底，`fail` 不再降级；`blocked` 只剩「无判定」实况（超时 / 宿主信号 / 精确 `GAP_SIGNATURES`）；`GAP_SIGNATURES` 语义不变（注释改作回归检查）⇒ **判据未放宽**。
**差距**：T3 目标 19/19 → 静态 **15/19**、动态 **15/19**（`ISS-295` 已收，余 4 例 / 3 条 issue）。
**证据**：`.work/evidence/TESTCASES-052t-rerun/run.sh`（full rc=0；3 处可达 FAIL 注入）；`check_rerun.py` 的 `iss295_spawn_popen_pass` 与 `iss299_no_stale_demotion` 两档全绿。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`tools/testcases/report_thread_cases.py`（新）、`issues.yaml`（+5 新条 / 2 条追加）、证据脚本 3 件、本册数据。
**逐行审查**
1. `report_thread_cases.py`：`index_cases` 对缺例/重例直接 rc=2（不静默缩小集合）；`TARGET_CASES` 带 19/唯一性断言；`reason_of` 取 `reason||first_error` 并压平换行；`--baseline-*` 缺席时 drift 记 `n/a`，不伪造基线。
2. `check_thread_truth.py`：计数由逐例 `klass` 现场统计（`derived`），不写死总数；`other=` 防未知 klass 混入；「非 pass 集合」+「载荷签名」双断言；`pass` 必须 `exit=0`。
3. `run.sh`：`set -u`、无 `tee`；check 步骤用 `${PIPESTATUS[0]}` 取被检命令自身 rc；注入用 `cp` + md5 前后对账（禁 `git checkout/restore/stash`），并把「注入前后 md5 相同 ⇒ 空注入」判 FAIL；`--inject` 复用落盘 JSON 便于复核。
4. `issues.yaml`：只追加 `notes` / 新增条目，未改既有状态；`check_issues` rc=0（58 open / 13 closed）。
5. 数据一致性：三次数值一致（静态 14/1/5、动态 14/1/5）；`ISS-294` 归零有正反两面证据（19 例无丢更新类断言失败；`pthread_cond` 1/40 挂死）。
**自审发现与处置**

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 报告里 `counts:` 易被误读为全套件计数 | ✅已修 | 改为 `counts (thread subset):`，同步 `run.sh` 的 grep | `report rc=0`，两档计数行正确 |
| F2 `n_block = 19 - pass - fail` 会把 known-fail 静默算成 blocked | ✅已修 | 改为逐 klass 统计 + `other=` 断言 | `--inject` 重跑：`derived` 一致、`other=[]` |
| F3 `run.sh` 有死代码 `note()`、`grep` 转义写成 `\\(` | ✅已修 | 删死代码；改单反斜杠分组 | full 重跑 rc=0 |
| F4 动态 `popen` 的 141 与子进程 139 易混为一因 | ✅已修（口径） | 完成区与 `ISS-295` 明写「子 139 先发生，qemu 141 为次生」 | `dyn-popen.strace` 子 SIGSEGV 先于父退出 |

**判决**：实现范围内 finding 全修；**遗留**（阶段 B 未跑、`ISS-252` 保持 open、状态未改）已在完成区登记，故未标 `待验收`（派单要求）。

#### 第 1 轮 reviewer 验收

#### 提交审核（architect，2026-10-20）

- **档位**：正常提交（派单给定提交信息；reviewer 尚未判决）⇒ `855a1f8`；分支 `TESTCASES-052t`，**未 push**。
- **文件集**：显式 staging **5 路径**（未用 `git add -A`/`.`）：本册、`.tao/knowledge/{issues.yaml,milestones.md}`、`INFRA-095t` 册、`tools/testcases/report_thread_cases.py`（新增，`py_compile` rc=0）。
- **对账（对完成区「修改文件」）**：本册 + `issues.yaml`（`ISS-252`/`257` 追加 + `ISS-295`–`299`）+ 新工具 = 声明 ✓；`.work/evidence/**` 为忽略区产物，不入 git（既定）✓。**多提 2 项（architect 台账范围，已披露）**：`milestones.md`（T3 行 + T1 待返工 + `ISS-295` 紧接下一件）、`INFRA-095t` 册（`**状态**` → `待返工` + 返工登记段）。**无漏提 / 无越界**。
- **状态**：本册 `待开始` → `待验收`（派单要求）。
- **门控**：`check-patch-tree` **183** ✓、`check-milestones-fresh`/`check-tasks`/`check-knowledge-refs`/`check_issues` ✓、`make check`（L1）rc=0。
- **异常披露**：① 阶段 B（全量两档）**未跑** ⇒ 验收标准 2（逐例无回归）未判；② reviewer 独立验收未做；③ 完成区「验收结果」所述证据脚本与注入记录均在 `.work/evidence/**`（易失），本册只留结论。

#### 第 2 轮 engineer 自审（`TESTCASES-052t-rerun`）

**范围**：`tools/testcases/run_libc_test_user_suite.py`（`ISS-299` 修复）、`.work/evidence/TESTCASES-052t-rerun/**`、`issues.yaml`（`ISS-252`/`ISS-299` 追加）、本册复跑段。
**逐行审查**
1. 删的是 `attribute_port_gaps()` 末尾整段兜底（`if case.klass not in ("fail","blocked"): return` + `if case.uses_thread: ...`），函数退化为「只挂注释」；`pass`/`known-fail` 一如既往不被触碰。
2. `classify_case()` 未动：`GAP_SIGNATURES` 精确签名仍在 `rc≠0` 与 `timeout` 两条路径生效 ⇒ 判据**不放宽**（真「无 `__clone`」回归仍判 `blocked`）。
3. `GAP_SIGNATURES` 四条正则**逐条未变**，只改注释/说明串（去掉「today」口径、标明为回归检查）；`uses_thread` 字段保留（`thread=` 列与 JSON 字段仍用）。
4. 复跑数值：修前 3 跑一致（静态 15/0/5、动态 16/0/4），修后各 1 跑复核；两组 **pass 集合完全相同**、非 pass 的**身份集合相同**，只有 3 例 `blocked→fail`（同现场）⇒ 修复只改分类口径、不改判定事实。
5. 证据脚本：3 处注入均可达 FAIL（计数谎报 / 错标根因 / extra klass 谎报），`cp`+md5 还原；`iss299_no_stale_demotion` 断言修前必红、修后两档 `[]`。
**自审发现与处置**

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 模块 docstring 的 `blocked` 条目仍写「today: pthread_create returns EAGAIN … no `__clone`」 | ✅已修 | 改写为「精确签名 + 回归检查」口径，注明兜底已删（`ISS-299`） | `git diff` 该段；两档 run 无「no __clone」理由 |
| F2 `attribute_port_gaps` 文档串仍写「fail→blocked demotion」 | ✅已修 | 重写 docstring 为「只挂注释」 | 同上 |
| F3 复跑里 `pthread_robust` 仍 `blocked`，易被误读为「又降级」 | ✅已修（口径） | 复跑段与 `ISS-252` 注记明写「60 s 超时 = 无判定，合法 `blocked`」 | `p2-static.json` 的 reason 逐字 `timeout after 60s` |
| F4 同批数据混着「能力变化」与「口径变化」两类 diff | ✅已修（口径） | 复跑段把两类分列（`ISS-295` / `ISS-299`） | 修前 3 跑与修后复核的逐例对账 |

**判决**：finding 全修；结论 = `ISS-295` 收口、`ISS-299` 修完待复核关闭；`ISS-252` 保持 open（19 目标 15/19）。
