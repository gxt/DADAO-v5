# TESTCASES-104t: gem5 SE 动态档驱动与 QEMU 动态基线

**模块**：testcases
**项目里程碑**：M11
**依赖**：`GEM5-027t`（装载器 + auxv）、`GEM5-028t`（文件映射 + ldso）、`INTEG-058t`（转换编码迁移后的 QEMU 基线）
**状态**：已验证

## 背景与事实

- 现有 `tools/testcases/lib/gem5_se_engine.py` 的 `static_gate()` 对 `ET_DYN`/`PT_INTERP` 一律判 BLOCKED；三个 tset 驱动的 `--engine gem5-se` 只跑过 static
- `GEM5-027t` 放行 `ET_EXEC + PT_INTERP`，`GEM5-028t` 让 ldso 映射 DSO；驱动需支持 `--interp-dir`/`--redirect` 透传与 `--engine gem5-se --link-mode dynamic` 组合
- 仓库里 `.work/tests/authoritative/libc-*.json` 仍是 2026-10-19（LLVM-117t 之前）的旧数据，**不可作动态验收基线**；须重跑 QEMU dynamic 全量
- `ADR-0048 D4`：SE 最终覆盖完整 tset（static 先行、dynamic 后补但不得降级）

## 目标

1. **驱动**：`gem5_se_engine.py` 的 `static_gate()` 改为「`ET_EXEC`（含 `PT_INTERP`）放行、`ET_DYN` 主程序仍 BLOCKED」；透传 `--interp-dir`/`--redirect`；三个 tset 驱动支持 `--engine gem5-se --link-mode dynamic`。
2. **QEMU 动态基线刷新**：用当前工具链/QEMU 重跑 `libc-test` / `llvm-ts` / `embench` 的 dynamic 全量，落新 JSON（非易失），作为 gem5 对照基线。
3. **gem5 SE 动态全量**：`GEM5-028t` 合并后，跑三套件 dynamic 全量，与 QEMU 基线逐 case 对照；产出报告（`qemu_only_fail` 逐条列名、`gem5_only_fail` 逐条归因、超时单列）。
4. 不改测试用例与期望；不改 gem5/QEMU 实现。

## 范围 / 非范围

**在范围内**：`tools/testcases/lib/gem5_se_engine.py`、`tools/testcases/tset/{libc-test,llvm-ts,embench}/*.py`（仅 engine/参数）、`.tao/knowledge/refs/TESTCASES-104t-*`（报告）、本任务书、`milestones.md`。

**不在范围**：gem5 SE 实现（前序任务）、`mprotect` 真权限、主程序 PIE、测试用例与期望、`docs/TestReports/M11-三平台一致矩阵.md`（`INTEG-059t` 统一重生成）。

## 执行方式：按套件跨机分片（用户 2026-11-09 同意）

- **分片维度 = 套件**（不按用例切）：三套件互不依赖，天然可并行。
- 建议分配：`server208` 跑 `llvm-ts` + `embench`，主控机跑 `libc-test`（208 当前空闲；207 只用于 chipyard）。
- **三条前提**（缺一不可）：两机 `git rev-parse HEAD` 一致、组件源树 **tree hash** 一致（不比 commit id）、gem5/QEMU 二进制 md5 或 build-id 一致。
- **汇总与判据**：主控机收两机 JSON，校验「分片不重叠、不遗漏（并集 = 全集）」「engine_banner/二进制一致」；任一条不满足 ⇒ 结果作废重跑。
- **禁止的是「进程生命周期重叠」**：基线运行时段内，该机器不得有构建/编译/Verilator/sbt/大拷贝等 CPU 或 IO 密集进程；构建结束后再跑基线不受限。原因：用例 runtime 贴预算边界（`Quicksort` 128.9 s 对 120 s），负载会把「通过」推成 `timeout` 并误记为能力缺口。
- 若驱动需加参数（如 `--suites` 组合已够用则不加；确需 `--shard i/N` 再加），在任务书完成区说明。

## 耗时构成与并行（2026-11-09 修正）

- **engineer 部分**：驱动改造 + 试点 = **1–2 h**
- **全量部分**：按套件分片（208 跑 llvm-ts+embench、主控机跑 libc-test）= **2–3 h**
- **QEMU dynamic 基线不依赖 gem5 驱动改造**，可与 engineer 的改造**同时**在节点上跑（QEMU 侧行为不变）；不必等驱动定稿。

## 验收标准

1. 三套件 × dynamic 在 gem5 SE 上跑完（预算按 `TESTCASES-103t`）；报告存在且可复算。
2. `qemu_only_fail` 逐条列名（须为 0 或给出 QEMU 侧任务）；`gem5_only_fail` 逐条归因；`timeout` 单列不计 PASS。
3. QEMU dynamic 新基线 JSON 覆盖三套件；`docs/TestReports/M11-三平台一致矩阵.md` 是 QEMU-system↔gem5-FS 矩阵、**无 dynamic/tset 行**，故本项以「三套件 JSON 计数自洽 + `refs/TESTCASES-104t-dynamic-summary` 为准」判定。
4. `make check`（L1）、`make check-modules`（L2）rc=0；驱动 `--self-test`（如有）rc=0。
5. 反例：把 `ET_EXEC+PT_INTERP` 改回 BLOCKED ⇒ 动态用例回 blocked；`cp`+`md5sum -c` 还原回绿。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 该任务只改**测试驱动/基线**，不改实现；gem5 侧能力缺口按 BLOCKED 记录并回给实现任务，不得在驱动里绕过。
- 动态档 gem5 慢 5–20×，预算与并发（`JOBS=32`）须按套件设置，避免把超时误判为能力失败。

## 完成区

**测试结果**：一键脚本全量轮 **50 PASS / 1 FAIL**，唯一失败为 **L1 的外部项**：`make check` 停在 `check-patch-tree`（共享 chipyard 源树被在途 m12 任务推进，本任务 `components/chipyard` diff=0；`check-temp-dirs` 另报 5 个其它任务的非活动临时目录，未删除）；`--inject-only` 30/30、`check-knowledge-refs`/`check-run-artifacts`/`check-runner-reap`、编排器 `--self-test` 22/22 全 rc=0。
**修改文件**：`tools/testcases/lib/gem5_se_engine.py`、`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`、`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`、`tools/testcases/tset/embench/run_embench_user_suite.py`、`tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`、`.tao/knowledge/refs/TESTCASES-104t-dynamic-driver.md`、`.tao/knowledge/refs/TESTCASES-104t-dynamic-summary.{json,md}`、本任务书。未改 `milestones*.md`。
**验收结果**：
- **驱动放行（验收 1/2）**：`ET_EXEC+PT_INTERP` 给定 guest root 即放行；`ET_DYN` 主程序仍 BLOCKED（`evaluate` 返回 `status=BLOCKED, gap.kind=elf-modality, cmd=[]`，gem5 未启动）；缺 guest root 或解释器不存在同样在启动前 BLOCKED。
- **redirect 语义（本轮返工）**：只映射 `("/lib", <root>/lib)`，其余 guest 绝对路径（guest 的 `/dev/*`、`/tmp/*`）落回宿主，与 QEMU `-L` 对齐；`run_cmd` 不含 `("/", ...)`。
- **11 例假失败修复（前后计数）**：首版 `("/", root)` ⇒ 11 例 `ENOENT` fail（`functional/{fcntl,fdopen,fscanf,fwscanf,stat,ungetc,utime}`、`regression/{daemon-failure,fflush-exit,ftello-unflushed-append,syscall-sign-extend}`）；改 `/lib` 后 **11/11 pass**，libc-test dynamic 全量 `gem5_only_fail` **15 → 0**（340 例：gem5 `pass=301/fail=0/known-fail=1/blocked=38`，其中 timeout 4；QEMU `pass=338/known-fail=2`；交叉 `both_pass=301`、`qemu_only_fail=0`）。
- **环境缺口**：`popen`/`spawn`/`vfork`/`execle-env` 动态档为 `BLOCKED`（`gem5-fatal`：宿主无 DADAO `/bin/echo`），不再计 `fail`；`functional/tls_align` 仍 `ldso-abort`（`/proc/self/exe`）。
- **每套件试点（gem5 SE dynamic）**：libc-test 3/3 pass（2.1–2.4 s/例）、11 例（guest `/dev`/`/tmp` 依赖）11/11 pass；llvm-ts 4/4 pass（2.2–2.4 s/例）；embench 4/4 pass（9.4–15.3 s/例，`-O0`）；QEMU 同例同数 pass。
- **auxv / 解释器**：两侧 `AT_PAGESZ=65536` 相等；gem5 `AT_BASE=0x200000000`、QEMU 非零，均页对齐且为 ELF 魔数；guest root 的 `ld-musl-dadao.so.1` 为 ET_DYN，每条 gem5 `run_cmd` 含 `--interp-dir` 与 `--redirect /lib=…`。
- **反例（验收 4/5）**：`--interp-dir` 指错 ⇒ 驱动 BLOCKED（未启动），裸 gem5 rc=1 明确报缺失；gate 注入回 static-only ⇒ 3/3 blocked；redirect 注入回 `("/", root)` ⇒ **11/11 fail（ENOENT）**；两次均 `cp`+`md5sum -c` 还原后回绿。
- **门控**：`check-knowledge-refs`、`check-run-artifacts`、`check-runner-reap`、`--self-test` 全 rc=0；L1 仅两项**外部**红（chipyard 在途改动、其它任务陈旧临时目录），其余成员全 PASS。
**新发现/坑**：① 动态每例 gem5 固定开销≈2.2 s；重负载例≈1.1 M inst/s（five11 动态 280 M 指令/265 s，同 ELF 的 static 实测亦 >2 min），预算沿用 300/600/300。② `authoritative/{llvmts,embench}-*.json` 的 `run_seconds` 是 **QEMU** 数据，不能当 gem5 预算依据。③ musl 对 bare-name `dlopen` 不走 cwd；`$ORIGIN` 失败只落到 `functional/tls_align`（`regression/tls_get_new-dtv` 先撞 membarrier）。④ **gem5 redirect 是「补尾 `/` + 表序纯前缀」匹配**：只映射 `("/lib", root/lib)`，全局 `("/", root)` 会把 `/dev`、`/tmp` 劫持进 guest root（本次 11 例假失败的根因；QEMU `-L` 无此语义）。⑤ 试点期间同机有在途 m12-chipyard 的 L2（单核）与 `install-host` 收尾，per-case 秒数是该负载下的上界。
**遗留问题**：① ISS-357（4 例写序）回 gem5/驱动实现任务，修复前按 `fail` 不计能力缺口；② `$ORIGIN` 需 `/proc/self/exe` 的缺口回 gem5 实现任务；③ 宿主无 DADAO `/bin/echo` 的 4 例环境缺口；④ server208 的 QEMU 数据因工具链不一致不可比，需同步重建后重跑；⑤ L1 三项外部红项（chipyard 在途、`m12-chipyard-004` 台账行、其它任务陈旧目录）须主会话收口后复跑；⑥ `mprotect`/RELRO 真权限沿用 GEM5-030t。

**全量结果与归因（三套件 dynamic，2026-11-09）**：
- 总计数：QEMU pass=590、gem5 pass=451、both_pass=451、gem5 blocked=43（不含 timeout）+ timeout=93、gem5_only_fail=4、qemu_only_fail=0；分套件 libc 338/301、llvm 214/112、embench 38/38（落 `refs/TESTCASES-104t-dynamic-summary.{json,md}`）。
- 4 例 gem5_only_fail 全为 **ISS-357**（写序）：analyzer/pifft 的 `stderr+stdout+exit` 与参考逐字节相等；distray 的 `md5(stderr+stdout+exit)` 与参考同值；bison 去掉参考中段 stderr 行后与 stdout 逐字节相等（任何串接顺序都不匹配）。**无新缺陷**，不立新 issue。
- `malloc-brk-fail` 的 QEMU fail 只见于 server208 对照：208 构建的 ELF+libc 在本机 qemu 复现 rc=1，本机构建的 ELF+libc 在本机与 208 两个 qemu 均 pass ⇒ 根因是 208 的 musl/libc.so 构建不同，**非 ISS-343**（台账原文亦否定）；故不登记 known-fail。
- 建议：208 先 `sync-node-repo` + `install-host`/`build-musl` 并核 md5 后重跑；ISS-357 修复须保留 fd1/fd2 写出顺序。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-09）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 只放行 `ET_EXEC` 会把「动态 ET_EXEC」与「静态 ET_EXEC」混为一谈；缺 guest root 时落到 gem5 fatal | ✅已修 | `static_gate(..., interp_dir=)`：PT_INTERP 需 guest root 且解释器存在，否则启动前 BLOCKED | 单元 6 条 + 驱动 BLOCKED + 裸 gem5 rc=1 明确失败 |
| redirect 若只给 `/=<root>`，相对路径（cwd 不在 root 下）会被吞 | ✅已修 | `loader_args` 先 cwd 自映射再 `/`→root；驱动传 run_cwd | llvm-ts（每例 run 目录）与 libc helper cwd 均 pass |
| 把 ldso 报错一律判 BLOCKED 会误伤「程序自己处理 dlopen 失败」 | ✅已修 | `_ldso_main_abort` 仅认 parent/object==主 ELF；加负例断言 | `ldso-abort-other-object-negative` PASS |
| embench 试点子集可能被 closure 判成遗漏或掩盖未执行项 | ✅已修 | `--filter` 声明子集，closure 对 selected 集；record 记 `filtered/selected` | 4/4 pass；空匹配 `--filter` rc=2 明确报错 |
| 编排器加 dynamic 会覆盖 static 摘要 | ✅已修 | 非 static 用 `-dynamic` 后缀；summary 记 `link_mode` | `--self-test` 新增 2 条 PASS；static 文件名不变 |
| 注释仍写「executed == discovered set」 | ✅已修 | 改为 selected 集表述 | `py_compile` + `check-tests-index` PASS |
| 全量三套件 dynamic 未跑 | ⏸延后 | 按分片归主会话（本任务只试点） | 完成区给出命令/耗时/日志约定 |
| L1 三项外部红项 | ⏸延后 | 非本任务改动，未删除 | `git diff HEAD -- components/chipyard`=0；`make -k check` 全量日志 |

### 第 2 轮 engineer 自审（2026-11-09，返工：redirect 作用域）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 首版 `("/", root)` 把 `/dev/null`、`/dev/zero`、`/tmp/...` 劫持进 guest root ⇒ 11 例动态假失败（ENOENT） | ✅已修 | `loader_args()` 改为 `redirect=[("/lib", <root>/lib)]`；把 gem5「补尾 `/` + 表序纯前缀」规则写入 docstring | 11 例 gem5 dynamic 11/11 pass；全量 `gem5_only_fail` 15→0 |
| 反例只覆盖 static gate，没覆盖 redirect 作用域 | ✅已修 | 证据脚本新增 `injection_root_redirect()`：注入回 `("/", root)` ⇒ 11/11 fail（ENOENT）→ 还原 ⇒ 11/11 pass | `run.sh --inject-only` 两组回环 rc=0 |
| 单元/试点 JSON 断言仍按 `("/",root)` 写 | ✅已修 | `redirect == [("/lib", <root>/lib)]`、无 `("/",...)`、`run_cmd` 前缀改 `/lib=` | 单元 7 条 + 4 个 pilot JSON 断言全 PASS |
| 4 例环境缺口（popen/spawn/vfork/execle-env）动态档由 fail 变 blocked | ✅已修（口径） | 不特判：`gem5-fatal`（`--interp-dir` 下找不到 x86 解释器）按平台缺口记 BLOCKED，完成区/报告写明 | 全量 4 例均 blocked、`fail=0`；QEMU 侧 pass |
| `refs` 的缺口与全量命令一节仍是修复前口径 | ✅已修 | 报告增 §2.1（根因/修复/前后计数），§3/§5 同步 | `check-knowledge-refs` PASS |
| llvm-ts/embench 全量未跑 | ⏸延后 | 主会话分片（本轮只补 libc-test 全量） | 完成区给出命令/耗时 |
| L1 两项外部红项 | ⏸延后 | 非本任务改动，未删除 | `make -k check` 全量日志 |



### 第 3 轮 engineer 自审（2026-11-09，全量汇总与归因）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 主会话给出的 libc 汇总文件是修复前快照（289/15），与消息里的 301/0 不一致 | ✅已修（取数） | 汇总改用 redirect 修复后的 libc 驱动 JSON（主控机同机），并在报告 provenance 注明 | 汇总 totals `gem5_pass=451`、`gem5_only_fail=4`；libc 分项 301/0 |
| `distray`/`bison` 被怀疑是 FP/内容差异 | ✅已查清 | 逐字节复核：`distray` 的 `md5(stderr+stdout+exit)` 与参考同值；`bison` 去掉参考中段 stderr 行后与 stdout 逐字节相等 | 两者均归 `ISS-357`，不立新 issue |
| `malloc-brk-fail` 的 ISS-343 归因 | ❌不采纳（附证据） | 台账原文否定；隔离实验定位到 208 的 musl/libc.so 构建差异；不登记 known-fail | 208 产物在本机 qemu 复现 fail、本机产物在两个 qemu 均 pass |
| 208 的 QEMU 数据是否并入 | ✅已排除 | 校验 qemu/libc.so md5 与源 HEAD 均不同，provenance 与 §5 写明不可比 | `415c…`/`466b…` vs `77ec…`/`4f9a…` |
| A3 日志名红项 | ✅已消 | 主会话清理后现场 0 illegal | `check-run-artifacts` PASS |
| L1 红项 | ⏸延后（外部） | chipyard 在途源码 + 5 个其它任务陈旧临时目录，未改未删 | `make check` 失败点现场 |

### 第 1 轮 reviewer 验收（2026-11-09，独立重跑）

**重跑记录（全部 reviewer 亲跑，命令在 worktree 根，退出码原样记录）**
- 一键证据脚本（运行期证据目录的 `run.sh`）→ `rc=1`，`== SUMMARY passes=50 fails=1`，唯一 `FAIL make-check-l1 expected=0 actual=2`；跑后 `md5sum -c` → `gem5_se_engine.py: OK`（`d8590c97…`）。
- **redirect 正例（自跑 13 例，含 11 个 `/dev`/`tmpfile` 例 + `functional/argv`/`api/main`）**：`run_libc_test_user_suite.py --link-mode dynamic --engine gem5-se --filter '<上述>'` → `rc=0`，`counts {'pass':13,'fail':0,'known-fail':0,'blocked':0}`；`run_cmd` 含 `--interp-dir` 与 `--redirect /lib=`，无 `/=`。
- **redirect 反例（reviewer 独立注入）**：`loader_args` 改回 `redirect=[("/", root)]`（md5 `d8590c97…`→`803af7cc…`）→ 同 13 例 `rc=1`、`fail=11`（逐例 `No such file or directory`/`errno = 2`/`failed to make temp file`），`/=` 进入 `run_cmd`；`cp`+`md5sum -c` 还原（`OK`）→ 重跑 `rc=0`、`pass=13`。
- **汇总重算**：`run_gem5_se_baseline.py --aggregate-only --link-mode dynamic --suites libc-test,llvm-ts,embench --work-dir <6 份驱动 JSON 所在目录> --json-out <tmp>` → `rc=0`，`totals: qemu_pass=590 gem5_pass=451 both_pass=451 blocked=43 timeout=93 gem5_only_fail=4 qemu_only_fail=0`；另从 6 份 JSON 直接数 `klass`：qemu `338+214+38=590`、gem5 `301+112+38=451`、`blocked_real 34+9+0=43`、`timeout 4+89+0=93`，与报告逐项相同。
- **4 例归因（reviewer 逐字节复核 guest.stdout/stderr vs 参考）**：analyzer `stderr+stdout+"exit 0\n"` == 参考（462 B，sha256 `d6f203b3…`）；pifft 同（82339 B，`4e999ac3…`）；distray `md5(stderr+stdout+exit)=78a70b660bcdf47a8dc16ba0db75ba2a` == 参考（驱动侧 `stdout+stderr` 得 `6f7dd863…`）；bison 参考第 **1092** 行即 stderr 行（byte 40056），去该行后 = `stdout+"exit 0\n"`，`sha256(stdout)=3c3b6bef…`（85349 B），`stdout+stderr`/`stderr+stdout` 两种串接均不等于参考。
- **malloc-brk-fail 交叉实验（reviewer 重做 2 qemu × 2 ELF × 2 libc）**：主控机 qemu：main ELF+main libc `rc=0`、+208 libc `rc=1`（line 73 同报错）；208 ELF+main libc `rc=0`、+208 libc `rc=1`；208 的 qemu 上四格结果相同 ⇒ **只随 `libc.so` 变，与 ELF、与 qemu 二进制无关**。md5/HEAD 现场：qemu `77ec79d5…`/`415c0d35…`、libc.so `4f9a5322…`/`466b3486…`、musl HEAD `24c1fd2`/`0fbef28`（`0fbef28` 在主控机 musl 仓非有效对象）。208 侧 JSON 现场：`libc pass=337 fail=1`，唯一 fail 即 `malloc-brk-fail`。
- **门控**：`check-knowledge-refs rc=0`（0 具体 `.work/**` 引用）、`check-run-artifacts rc=0`（A3 `0 illegal`）、编排器 `--self-test rc=0`（**22/22**）、`make check-modules rc=0`（`module checks (L2): PASS`）、`make check rc=2` → `make -k check` 共 **3 红且全外部**：`check-patch-tree`（13 项，chipyard 在途）、`check-milestones-fresh`（`m12-chipyard-004` 有 worktree 而台账行仍在「待开始」）、`check-temp-dirs`（5 个他任务陈旧目录）；本任务 `git diff HEAD -- components/chipyard`=0、未改 `milestones*.md`、本任务目录不在违规清单。
- **快照对账**：验收前后 `git status --porcelain -uall` 逐行相同（9 项），与「修改文件」9 项一一对应；6 个改动文件 md5 前后一致（注入已还原）。

**约束核验**：验收 1 ✅ / 2 ✅ / 3 ⚠（`docs/TestReports/M11-三平台一致矩阵.md` 是 QEMU-system↔gem5-FS 矩阵，**无 dynamic/tset 行**，该比对无对象）/ 4 ⚠（L1 非 0，但 3 红均外部已核实；L2、`--self-test` ✅）/ 5 ✅ / 6 ✅（完成区 21 行、状态 `待验收`）。不改用例与期望 ✅、不改 gem5/QEMU 实现 ✅、范围外未动 ✅。

**findings（文档级，不阻断）**：① 完成区/refs §7「L1 仅两项外部红」在 reviewer 现场为 **3 项**（`check-milestones-fresh` 系 engineer 收工后 m12-chipyard-004 建 worktree 所致，其 09:25 keep-going 日志中该项 PASS）；② `gem5_se_engine.py` 模块 docstring 仍写 `--redirect / <root>`，与实现 `("/lib", <root>/lib)` 相反；③ refs §5 汇总命令漏必需的 `--json-out`（照抄会 usage rc=2）；④ 验收 3 的 matrix-M11 比对无对应行，建议架构师澄清口径。

**判决：Accepted**。三个专答：① 4 例 `gem5_only_fail` **全部属 ISS-357**（写序，逐字节/md5 证据齐，无内容差异）；② `malloc-brk-fail` 归因**成立**（交叉实验定死为 208 的 `libc.so` 构建，且与 qemu/ELF 无关 ⇒ 非 ISS-343，ISS-343 台账原文亦否定且已 closed）；③ **208 数据不并入是正确的**（qemu/libc.so md5 与 musl HEAD 三项前提均不成立，分片前提「同二进制」被破坏）。

#### 收尾（architect，2026-11-09 12:06）

- 判决 **Accepted**：reviewer 重做 redirect 反例（`("/", root)` ⇒ 13 例 11 fail，还原回绿）、独立重算 590/451/451/43/93/4/0、**四例 fail 逐字节复核全属 `ISS-357`**（`bison` 的 stderr 在参考第 1092 行，两种串接顺序均不匹配 ⇒ 修复必须保留 fd1/fd2 写序）、`malloc-brk-fail` 交叉实验定死在 `libc.so` 构建（与 ELF/qemu 无关）。
- 4 条文档 finding 已修：L1 改「三项外部红」、`gem5_se_engine.py` docstring 改 `--redirect /lib=<root>/lib`、refs 汇总命令补 `--json-out`、验收 3 改「以三套件 JSON 自洽为准」（`matrix-M11` 无 dynamic 行）。
- 208 数据不并入（qemu md5 / libc.so md5 / musl HEAD 三项均不同）。
