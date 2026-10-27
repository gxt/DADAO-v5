# TESTCASES-077t: llvm-ts 架构专用用例与超时/编译门控

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t
**状态**：待验收

## 背景（2026-10-27 全量实测，自包含）
`check-tset-llvm-full`（static）在 `TESTCASES-076t` 全量中失败，除语料 UB 外还有三类**非 DADAO 语义问题**：

1. `SingleSource/Benchmarks/Misc/aarch64-init-cpu-features`：
   - 源码 `.work/source/llvm-test-suite/SingleSource/Benchmarks/Misc/aarch64-init-cpu-features.c:5` 引用 `__aarch64_cpu_features`，`:8/:10/:13` 用 `RUNTIME_INIT`（AArch64 的 `__init_cpu_features*`）；
   - DADAO 无此符号 ⇒ `ld.lld: undefined symbol: RUNTIME_INIT`，被记 `BLOCKED`。
2. `MultiSource/Applications/Burg`：
   - `be.c:335` `parameter 'to' was not declared, defaults to 'int'`（ISO C99 起为 error）⇒ `BLOCKED`（compile error）。
3. `MultiSource/Benchmarks/mafft`：
   - 超时 `1620s`（27 min）⇒ `BLOCKED`（timeout）。

这三项**不是** DADAO 编译器/后端缺陷；但当前驱动按「有 main 就收」把它们收进全量，导致全量/夜跑无法全绿。

## 目标
1. **架构专用排除**：在 `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py` 增加**逐例、带源码依据**的「架构专用/不适用」排除表，至少含 `aarch64-init-cpu-features`；扫描同目录/同套件其它 aarch64/riscv/x86 专用用例，按同口径处理。排除必须是 `excluded`（不是 pass/fail/known-fail），理由含源码文件:行与符号证据；不得用宽泛通配。
2. **Burg 编译口径**：用**最小 per-case 编译参数**修复（如 `-Wno-error=implicit-int` 或该例 `-std=gnu89`，二选一以实测为准），不得全局放宽所有套件；确认不改变其它用例命令。
3. **mafft 超时**：先实测单例真实耗时；**同时在宿主机跑同一输入作参照**，判断是「纯慢」还是另有 bug（死循环/阻塞）；先提高**该例** timeout（如 3600s 起）复测；不得把全局 `DEFAULT_TIMEOUT` 无据放大；夜跑总时长须记录。
4. 不改测试期望/断言，不把「适用用例」降级为 known-fail/blocked。

## 验收
- 定向（static+dynamic）：`aarch64-init-cpu-features` 为 `excluded`（理由指向源码）；`Burg` 编译并运行到自身判定；`mafft` 在设定 timeout 内完成并 pass。
- `make check-tset-llvm-full`（static+dynamic）**rc=0**，且 **`fail=0`、`blocked=0`**；`known-fail` 只允许剩 `obsequi`/`ft`/`8b10b` 三条（由 `TESTCASES-080t` 消除，用户 2026-10-27 裁定全绿 = 零 known-fail）。本任务不得新增 known-fail。
- `make check` rc=0；`check-case-ledger` rc=0；证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-077t/`。

## 约束
- 只改本任务范围内的 `tools/testcases/tset/llvm-ts/`、`tests/tset/llvm-ts/`、`Makefile`、索引/ledger、任务书/milestones；不改 spec/qemu/LLVM 语义。
- **不提交、不 push**；不跑无关全量；长跑（mafft）申报预计耗时。
- 排除项必须可审计：`excluded` 行含 `id + reason + 源码指针`，不得静默跳过。

## 完成区

**状态**：待验收

**测试结果**：`.work/evidence/TESTCASES-077t/run.sh --slow` → `checks=55 pass=55 fail=0`；反例均可达 FAIL 且 `cp`+md5 还原：C1 aarch64 排除行改名 ⇒ A4 判据 + `census_ok` 转红 ⇒ 回绿；C2 Burg 方言行删除 ⇒ `BLOCKED (implicit-int)` ⇒ 回绿；C3 mafft timeout 1800→400 ⇒ `timeout after 400s` ⇒ 回绿。定向两档 6/6 pass（Burg/cdecl/OptimizerEval）；aarch64 不执行、`--only` 报 declared exclusion（rc=2）；mafft pass 1587.7 s（jobs=1）/1604.3 s（dynamic）/1611.5 s（static）；宿主对照 `mafft_host_compare.sh` → gcc 构建 17.2 s、stdout+exit md5 `46e32283…` == 上游参考（记录 `mafft-host-reference.txt`）⇒ 纯慢非死锁。

**修改文件**：`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`（`STRUCTURAL_EXCLUSIONS` + aarch64；新增 `CASE_CFLAGS`：Burg/cdecl/OptimizerEval；`CASE_TIMEOUTS` mafft 1620→1800；docstring/CASE_TIMEOUT_BASIS）；`tests/tset/llvm-ts/README.md`（口径三条）；`.work/evidence/TESTCASES-077t/run.sh`；本任务书；`.tao/knowledge/milestones.md`。

**验收结果**：`make check-tset-llvm-full`（jobs=8）static 219 例 → pass=207 fail=2 known-fail=4 blocked=6 excluded=3 **rc=1**（WALL 2086 s）；dynamic 同数 **rc=1**（WALL 2071 s）；两档 `closure_ok`/`census_ok`=True。09:01 基线 static：pass=203 fail=2 known-fail=4 blocked=11 excluded=2。⇒ 任务书「rc=0 / blocked=0」**未达成**（原因见遗留①）。`make check` rc=0；`check-case-ledger` rc=0；「其它用例编译命令逐字节不变、run_timeout 仅 mafft + 3 方言例变化」由 D1d/D1e 机检。`run.sh --fast --expect-green` → D2 六条 FAIL（fail=2/blocked=6/known-fail 多出 ClamAV）⇒ 全绿判据的可达 FAIL 路径已证。

**新发现/坑**：
1. 任务书「三类」低估了全量现状：blocked 实为 11 项，另有 gawk/make/p2c（C89 语料 + glibc-only `sys_nerr`、`logf` 与 musl `math.h` 冲突 —— **编译参数无解**，须语料胶水 patch）与 archie-client/plot2fig（缺 BSD `re_comp`/`re_exec`，上游 `check_function_exists(re_comp)` 守卫 ⇒ 上游本就不为该 libc 构建此 target）。
2. Burg 根因不是「clang 太严」，而是驱动未评估 CMake `C_STANDARD`（`Burg/CMakeLists.txt:7` = C90，`C_EXTENSIONS` 默认 ON ⇒ `-std=gnu90`）；cdecl 同因，一并按上游声明修复。
3. mafft 旧基准 1452.82 s 已漂移（现 1588/1604/1612 s），1620 s 在 09:01 的 jobs=4 负载下本就不够；宿主 gcc 同输入 18.1 s、输出 md5 与上游参考一致 ⇒ 纯慢（约 90×），非死锁。
4. gawk 补 `-std=gnu89` 后编译通过，但 guest NULL 解引用后跑自身 SIGSEGV handler → `tkill(SIGIOT)` → 宿主 SIGABRT；驱动 `SIG_DELIVERY_RE` 不识别 `si_addr=NULL` 形态，误判「no `--- SIG` line」而记 blocked（判据缺口，未改）。

**遗留问题**：
① **`make check-tset-llvm-full` 未 rc=0**：blocked=6（lemon→078；gawk/make/p2c/archie-client/plot2fig **无任务书归属**）、fail=2（SPASS→078、typeset→079）、known-fail=4（obsequi/ft/8b10b→080；**ClamAV 无归属**）。建议立 081t（语料胶水 patch + `re_comp` 适用性裁定）或并入 078；ClamAV 归属需裁定。
② dynamic 门控跑在临时表值 4200 s（≥ 最终 1800 s，结论不受影响），static 用最终值 1800 s。
③ 证据脚本 C3（mafft 超时注入实跑）需 `--slow`（≈7 min）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-27）

**判决**：待验收（任务范围内 finding 全修；2 条越界项延后并已登记遗留）。审阅方式：自主逐行审 diff（`git diff` 三文件）+ 逐条跑证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1 `CASE_CFLAGS` 追加在 cmake CFLAGS 之后，可能与上游 `-std=` 冲突 | ❌不修 | 无（全 scope 无第二个 `-std` 来源） | D1d：其它用例编译命令逐字节不变 |
| 2 排除项新增后枚举自洽性可能被破坏 | ❌不修 | 无（`a_census_ok` 已覆盖） | A3：222 = 219 executed + 3 excluded；`--list` census_ok=True |
| 3 证据脚本 D1d/D1e 期望值漏了排序与「基线 blocked 无 run_timeout」 | ✅已修 | 期望集改为排序后 3 例；D1e 改 mafft + 3 方言例 | `run.sh --slow` D1d/D1e PASS |
| 4 被 kill 的 mafft 测量留下空 run 目录 ⇒ `check-run-artifacts` 红 | ✅已修 | `rmdir .dadao/tests/llvm-ts-user/20261027T065900Z-llvm-ts-user-static` | `make check` rc=0（L1 PASS） |
| 5 任务书/milestones 状态不一致 ⇒ `check-milestones-fresh` 红 | ✅已修 | 表行保留 `（登记）` + 状态 `待验收`；任务书状态同步 | `make check` rc=0 |
| 6 任务书称「三类」非语义问题，实测 blocked=11 | ⏸延后 | 无（越界，需裁定） | 遗留①：gawk/make/p2c/archie/plot2fig 实测原因 |
| 7 驱动 `SIG_DELIVERY_RE` 不识别 `si_addr=NULL` ⇒ gawk 误记 blocked | ⏸延后 | 无（越界） | `.dadao/.../gawk/qemu-strace.log` 有 `--- SIGSEGV ... si_addr=NULL ---` |
