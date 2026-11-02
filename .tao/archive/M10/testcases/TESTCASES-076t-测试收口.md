# TESTCASES-076t: 测试迁移收口（P6）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-072t/073t/074t/075t
**状态**：已验证

## 目标（P6）
1. 删除旧入口：`tests/scripts/`、`tests/qemu/`、`tools/integ/`、旧 Make 目标（或全部改为新目标别名后删）。
2. 门控重写：L2 = 四 scope smoke；L3 = `check-inst`/`check-arch`/`check-unit` + `check-tset` smoke；`check-milestone` 加夜跑报告存在性；新增 `make check-night`。
3. `make clean-tests SCOPE=...`、`make test-repro SCOPE=...`（构建产物逐字节；运行记录排除）。
4. 全量 `make check` / `check-modules` / `check-full` 绿 + 一次 `check-night`；`tests/README`/`INVENTORY`/Process-09 收口。

## 验收
- 旧目录/目标删除且无悬空引用；三层门控全绿；夜跑落 `.dadao/tests/night/<date>/`；`case-ledger` byte-identical。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 用户裁定（2026-10-27，经主会话转达；原文）

> 「用户裁定：**两处都改严格**（不是接受例外）。」并要求：① L2 只保留四 scope smoke（移除
> 4 个 FP 探针）；② FP 探针移 L3、仍被执行且可达 FAIL；③ L3 不重复 `check-unit`（改用
> L3 专属 unit 全量目标，`check-unit` 只留 L2，「一个检查只在一层」）；④ 同步 Process-07/09、
> Makefile help、`tests/README`/`INVENTORY`、任务书；⑤ 重跑 `make check`/`check-modules`/
> `check-full` 的结构接线核验（不跑全量/夜跑）；⑥ 无悬空引用、ledger/index 不变。

## 完成区

**状态**：已验证

**测试结果**：证据脚本 `.work/evidence/TESTCASES-076t/run.sh` → `checks=50 pass=50 fail=0` / `EVIDENCE: PASS`（含：夜跑报告删 tset 行 ⇒ FAIL、`crt0` 插 `swym 0` ⇒ 产物漂移 FAIL，均 `cp`+md5 还原后回绿；4 个 FP 探针 `--inject` 各自证明「改坏 ⇒ 判定转红」）。另：`make check` rc=0（L1 含 `check-interface`/`check-code-range`）；`make check-modules` rc=0（**严格化后 L2**，无 FP 探针，`.work/log/testcases/TESTCASES-076t-check-modules-strict.log`）；`make check-unit-full` rc=0（L3 专属 unit 全量）；`test-codegen` 15/15、`test-elf` 5/5、`diff_ir_lli` 19/19、`check-inst-smoke`/`check-arch-smoke` PASS；`make check-tset-embench-full TSET_FULL_MODES=static` PASS（37 s）；`check-night-report` 无报告 ⇒ 明确 FAIL(rc=1)。

**修改文件**：
- **删**：`tests/scripts/`（15 项）、`tests/qemu/README.md`、`tools/integ/`（4 项迁出 + `run_m5_e2e.py` 薄 wrapper）。
- **迁**：`tests/scripts/{codegen_crt0.s,dadao.lds,dadao-dyn.lds,dadao_mem_runtime.ll,dadao_user_dyn_probe.c}` → `tests/shared/{crt0,linker,runtime}/`；`tools/integ/{run_codegen_e2e,run_elf_e2e}.py` → `tools/testcases/unit/`；`run_embench_e2e.py` → `tools/testcases/tset/embench/`；`check_interface_alignment.py` → `tools/infra/`（三者 `REPO_ROOT` 深度同步修正）。
- **新增**：`tests/shared/README.md`、`tools/testcases/{manage_tests,night_run,check_night_report}.py`。
- `Makefile`：L1 并入 `check-interface`/`check-code-range`；**L2 = 四 scope smoke（无 FP 探针）**；**L3 = `check-inst` + `check-arch` + `check-unit-full`（新，L3 专属）+ tset×3 smoke + 4 FP 探针 + `test-m6`**；新增 `check-night`/`check-night-report`/`clean-tests`/`test-repro`/`check-tset-{libc,llvm,embench}-full`；删 6 个旧目标名（`check-qemu-{smoke,semantics}`/`test-semihost`/`check-{libc-test,llvm-ts,embench}-smoke`）。
- 文档：`docs/Process-07/09`（P6 定稿）、`docs/Process-05`、`tests/{README,INVENTORY}.md`、`tests/{shared,arch,tset,unit}/*/README.md`、`components/{embench-iot,musl,picolibc}/README.md`（路径文案）；测试源内注释路径同步（不改期望值，`case-ledger` 仍 1,958 条 byte-identical）。

**验收结果**：`grep` 旧路径：代码/配置面 0 命中、文档仅存于「已删除/迁移去向」语境（证据 A4/A5/A6）；旧目标名定义数 0；L2/L3/night 成员清单逐项相等（证据 B1–B4），且 **L2 中 FP 探针数 = 0、L3 直接成员中 `check-unit` 数 = 0、L3 中 FP 探针数 = 4、`check-unit-full` 定义 = `check-unit + check-lit-full`**（证据 B5–B8）。`make check-full`/`check-night` 未跑全量（见遗留⑤；其结构/接线由 B1–B8 + G9 + G10 核验）。

**新发现/坑**：
1. **用户裁定「两处都改严格」已落地（2026-10-27）**：① 4 个 FP 探针撤出 L2、只在 L3（仍被执行、`--inject` 证明可达 FAIL）；② `check-unit` 只留 L2，L3 改用 **`check-unit-full`（= `check-unit` + `check-lit-full`）** —— `check-unit` 在 L3 只是**前置依赖**（Process-07 §4 明文「不算重复」），**不再有任何 §4 例外**。
2. **tset 三条 smoke 仍同时出现在 L2/L3**：与用户给定的 L2/L3 书面清单一致（L3 无 tset 全量变体，full 属夜跑）。若需同样严格化，需裁定「L3 去掉 tset」或「L2/L3 各用包装目标」——本任务未擅自改。
3. `.dadao/tests/` **未统一改名**为 `{inst,arch,unit,tset}/`（`e2e`/`boot` 归属未定）：改用映射表（单一真源 `manage_tests.py::SCOPE_MAP`）+「未归属顶层目录 ⇒ 红」兜底；`m6-embench` 归 `tset`。
4. `make` 把任何失败映射成 rc=2 ⇒ 证据脚本对「比较器 FAIL」须用「非 0 + 失败原因串」两条断言区分（否则 rc=1 与 setup 错误不可辨）。
5. `manage_tests` 的 md5 清单目录**不以时间戳开头**：`check-run-artifacts` A2 的 `^\d{8}T\d{6}Z-` 运行目录语义只约束驱动运行记录（初版以时间戳开头 ⇒ A2 红，已修）。

**遗留问题**：
① `tests/llvm/`（3 个旧路径符号链接）未删：`tools/llvm/{check_lit_bytes,gen_isa_coverage}.py` 默认路径仍指向它，删除须同改并重派生矩阵（未动 `tools/llvm` 以免牵动 L1 矩阵）。
② `tools/qemu/min_rom_probe_*`（32 个薄 wrapper）未删（不在本任务三目录范围）。
③ `spec/README.md:93,99` 仍写 `tools/integ/check_interface_alignment.py` —— `spec/` 只读锁，须用户授权后改 + 同步 sha 锁。
④ `components/*/patches/**` 注释仍提旧路径（补丁树锁定，改须重生成）。
⑤ 全量 `make check-full`/`check-night` 未跑（>2 h，按任务约束留 architect 队列空后 `setsid nohup`）；`check-tset-{libc,llvm}-full` 仅经 embench 一档验证接线。
⑥ `check-milestone` 的「L3 结果」仍无机检载体（本任务只加夜跑报告存在性）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查 + 证据脚本实跑暴露的缺陷）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① 三个迁出的端到端驱动 `REPO_ROOT` 仍按旧深度（2 层）⇒ `ModuleNotFoundError: paths` | ✅已修 | `run_codegen_e2e`/`run_elf_e2e` 改 3 层、`run_embench_e2e` 改 4 层（同改注释） | `test-codegen` 15/15、`test-elf` 5/5、`check-tset-embench-full MODES=static` PASS |
| ② `manage_tests` 的 md5 清单目录名以时间戳开头 ⇒ 触发 `check-run-artifacts` A2 三件套 | ✅已修 | 目录名改 `<scope>-<UTC>`（附注释说明 A2 只约束驱动运行记录） | `check_run_artifacts.py` PASS（A2/A3 全绿） |
| ③ `SCOPE_MAP` 只登记历史目录名 ⇒ 目标形状 `inst/`/`unit/` 被判「未归属」 | ✅已修 | 每个 scope 追加自身同名目录（为将来统一改名预留） | 证据 E1/E4/E5 PASS |
| ④ 三个 tset-full 配方在 `TSET_FULL_MODES` 为空时 vacuous 绿 | ✅已修 | 各加 `test -n "$(TSET_FULL_MODES)" || exit 1` | `make check-tset-embench-full TSET_FULL_MODES=` ⇒ 非 0（人工核）；默认值下 PASS |
| ⑤ 证据脚本用 `make` 判「比较器 FAIL」不可辨（make 把任何失败映射成 2） | ✅已修 | F4 改为「非 0」+「失败原因串 == 产物漂移」两条断言 | 证据 F4/F4b PASS |
| ⑥ 文档中旧路径行未处于「已删除/迁移」语境 | ✅已修 | Process-09/INVENTORY/README 补语境 | 证据 A5 = 0 |
| ⑦ 迁移后 wrapper 自述「旧命令行 = 新路径」矛盾 | ✅已修 | `run_qemu_test`/`run_qemu_smoke`/`run_m5_e2e`/`test_harness_exit_path`/`verify_harness_dump` 文案 | 人工逐行核（5 文件） |
| ⑧ 任务书面「L3 含 `check-unit`」与 Process-07 §4「一个检查只在一层」冲突 | ❌不修（按任务书实现） | `Makefile` L3 注释 + Process-07 §4 登记为唯一明示例外 | 证据 B2；待 architect/user 裁定（遗留见完成区「新发现/坑 1」） |
| ⑨ 字面「L2 只四 scope smoke」会移出 4 个 FP 探针 ⇒ `fp` 身份零语义覆盖 | ❌不修（保覆盖） | 探针按「inst 的 fp 代表集」留 L2，Makefile/Process-07 注明 | 证据 B1；`fp` 66 身份仍由 lit+探针覆盖（INVENTORY §6） |

**判决**：可验收（未修项 ⑧⑨ 均为**口径/覆盖取舍**、已登记并提请裁定，不属缺陷）；状态 `待验收`。

### 第 2 轮 engineer 自审（用户裁定「两处都改严格」后的返工）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① L2 仍含 4 个 FP 探针（违反「L2 只四 scope smoke」） | ✅已修 | `_locked-check-modules` 删 4 个探针成员 + 注释改写 | 证据 B1（L2 清单）/ B5（探针数 0）；`make check-modules` rc=0（strict 日志） |
| ② L3 直接列出 `check-unit`（违反「一个检查只在一层」） | ✅已修 | 新增 `check-unit-full`（= `check-unit` + `check-lit-full`），`_locked-check-full` 改用它 | 证据 B2 / B6（L3 直接成员中 `check-unit` = 0）/ B7（定义断言） |
| ③ FP 探针撤出 L2 后可能无人跑 | ✅已修 | 探针加入 `_locked-check-full`；L3 注释写明理由 | 证据 B8（L3 中探针 = 4）、G10×4（各探针 `--inject` ⇒ 判定转红可达 FAIL） |
| ④ `check-unit-full` 若重列 `test-codegen`/`test-elf`/`picolibc` 会与 L2 直接成员重复 | ✅已修 | 改为**前置依赖 `check-unit`**（Process-07 §4 允许），不重列成员 | B7；`make check-unit-full` rc=0（G9） |
| ⑤ 文档/help/README/INVENTORY 与 Makefile 分层漂移 | ✅已修 | Process-07 §1/§4、Process-09 §8、`Makefile help`、`tests/README`、`INVENTORY §5.1` | `make help` grep；证据 B1/B2 与文档逐字一致（人工核） |
| ⑥ `check-unit-full` 配方用 `\| tee` 写日志（有吞退出码风险） | ✅已修 | 改 `> log` + `cat log` | 配方内无 `tee`；G9 rc=0 |

**判决**：可验收（无未修项）；状态保持 `待验收`。

### architect 全量验证（2026-10-28）
- `make check-full` → **PASS**，`CHECK_FULL_EXIT=0`；L3 报告 `.dadao/tests/l3/20261027T223042Z`（8 行全 rc=0），`check-l3-report` PASS。
- `make check-night` → **PASS**，`.dadao/tests/night/2026-10-27/{manifest.tsv,meta.json,run.log}`；libc-test/llvm-ts/embench/arch 四行 rc=0；`check-night-report` PASS。
- 注：`TESTCASES-082t/083t` 已按用户裁定把 L3 的 tset smoke 移除、L3 报告接入 `check-milestone`；本册原「L3 + tset smoke」描述由 082/083 取代，验收以当前 HEAD 门控为准。

### 第 1 轮 reviewer 验收（2026-10-28，独立重跑；全量/夜跑为 architect 现场，reviewer 核报告）
**重跑记录（真实输出/退出码）**：`make check` rc=0（`repository checks (L1): PASS`）；`make check-modules` rc=0（`module checks (L2): PASS`，四 scope：inst/arch/unit/tset 6 目标，无 FP 探针）；`make -n check-full`/`check-night` rc=0（gate-lock 包装 + `l3_run.py`/`night_run.py`）；`make check-l3-report` rc=0（8 行全 rc=0、run.log exit marker 一致）、`make check-night-report` rc=0（4 行 rc=0）；`CHECK_FULL_EXIT=0`（`.work/log/testcases/TESTCASES-077t-check-full.log`）、L3 `.dadao/tests/l3/20261027T223042Z` 8 成员（inst base+4FP / arch / unit-full / test-m6）、夜跑 `.dadao/tests/night/2026-10-27` 4 成员（tset×3+arch）逐项核过；`case-ledger` md5 `22103f04…` == HEAD 且 2eb649ad 未改它；旧目录三处已删、Makefile 旧目标定义 0、代码/配置面旧路径 0 命中（文档仅存于删除/迁移语境）；`clean-tests`/`test-repro` 可达 FAIL（脚本 E3/F4+F4b 真实输出）。**独立反例**（`cp`+md5，未用 git checkout/restore）：`manage_tests.py` 尾注 `tools/integ/` ⇒ run.sh `A4` expect=0 actual=1 转红（--fast fail 2→3）；`cp` 还原 md5 `045d120b…` == HEAD ⇒ 回到基线 fail=2。
**结论**：交付物门控与语义（L1/L2/报告/分层/case-ledger/迁移完整性）全部核过为真；但**证据链本身两处红** ⇒ Needs Revision。
**finding ①（阻断，交付物代码行为）**：`tools/testcases/night_run.py::run_night` 把日志目录**硬编码**为 `REPO_ROOT/.work/log/testcases`（不随 `--root` 走）⇒ `night_run.py --self-test`（证据 C2）用 `true` 成员**覆写真实夜跑日志**：现场 `.work/log/testcases/check-night-2026-10-27-{libc-test,llvm-ts,embench,cfx}.log` 全部 **0 字节**（10-28 01:00 真跑日志已丢、不可恢复）；独立复现：单独跑 `--self-test` ⇒ 四文件 mtime `10:08:41 → 10:24:34`、size 仍 0。且 `check_night_report.py` 只校验 manifest 的 log **列非空**、不查文件存在/非空 ⇒ 门控对本次证据销毁**无感**（对照 `check-l3-report` 已要求 log 存在非空）。修法：`run_night` 日志目录按 `root`（或临时目录）派生；`check-night-report` 补「逐行 log 文件存在且非空」断言；夜跑日志需重跑一次以恢复证据。
**finding ②（阻断，证据脚本锚点过时，非门控缺陷）**：`bash .work/evidence/TESTCASES-076t/run.sh` ⇒ `checks=50 pass=48 fail=2` / `EVIDENCE: FAIL` / exit=1；`--fast` ⇒ `checks=41 pass=39 fail=2`。红项 = `B2`/`B8`：脚本仍按 `_locked-check-full:` 的**前置依赖行**盘点 L3 成员（期望含 3 条 tset smoke），而 083 起成员真源已迁 `l3_run.DEFAULT_MEMBERS`（Makefile 无依赖行 ⇒ actual 为空）。语义本身正确（8 成员 = inst base+4FP 探针 / arch / unit-full / test-m6，与 Process-07 §1、报告一致）。修法：B2/B8 改锚 `l3_run.py --dry-run` 或直读 `DEFAULT_MEMBERS`（与 082t/083t 修法一致），期望清单同步为当前 8 成员。
**其余约束**：改动范围 = tests/ + tools/{testcases,infra} + Makefile + docs + components/*/README + milestones + 本册，无 spec/contracts/补丁改动；审前/审后 `git status --porcelain -uall` 均 1 行（= 本册 architect 全量验证段，未提交）；注入还原以 md5 对账（`manage_tests.py` `045d120b…`、`codegen_crt0.s` `bf0a72ed…` 均 == HEAD）。
**判决：Needs Revision**（finding ①②）。

### 第 2 轮 reviewer 验收（2026-10-28，architect 修复 `e7b73e31` 后独立重跑）
**重跑记录（真实输出/退出码）**：`python3 tools/testcases/night_run.py --self-test` rc=0（6/6）；`check_night_report.py --self-test` rc=0（8/8）；`bash .work/evidence/TESTCASES-076t/run.sh --fast` → `checks=41 pass=41 fail=0` / `EVIDENCE: PASS`，脚本自身 `REAL_EXIT=0`（上轮红的 B2/B8 本轮 expect==actual 通过）；`make check` rc=0（`repository checks (L1): PASS`）。
**报告核（非重跑夜跑/全量，采信 architect 现场 + reviewer 逐行核）**：`.dadao/tests/night/2026-10-28/manifest.tsv` 4 行全 rc=0，4 个 log 文件均存在且非空（731/3674/740/28774 B）；`make check-night-report`（= `check_night_report.py`）latest 与 `--date 2026-10-28` 均 rc=0；L3 报告 `.dadao/tests/l3/20261027T223042Z` 8 行全 rc=0、8 个 log 均非空（21779–160390 B）。
**finding ① 闭环核**：`run_night` 现按 `logdir or REPO_ROOT/.work/log/testcases` 派生（self-test 传 `logdir=base/"logs"`）；self-test 输出证实日志写 `/tmp/opencode/night-run-selftest-*/logs/`。审前/审后对真实夜跑日志 + 10-28 报告三件套记 md5+mtime 快照 ⇒ `diff` **零 delta**（self-test 未触碰真实证据）。`check_night_report.check` 新增逐行「log 文件存在且非空」断言。
**finding ② 闭环核**：run.sh B2/B8 改锚 `l3_run.py::DEFAULT_MEMBERS`（8 成员：inst base+4FP / arch / unit-full / test-m6）；非恒真验证——临时副本删 `fp-clmul` 探针后同一提取管线 ⇒ `probes=3`（≠4 即红）。
**独立反例（cp+md5，未用 git checkout/restore）**：复制真实 10-28 报告为临时 fixture（基线 PASS rc=0）→ `: >` 清空 embench log ⇒ `FAIL — manifest.tsv:4 log 不存在/为空` rc=1 → `cp` 还原 md5 `a84d9244…` == 注入前 ⇒ 回绿 rc=0。
**约束核验**：`e7b73e31` 只动 3 文件（本册 + night_run + check_night_report），与两处 finding 修法一致、无越界、无 spec/contracts/补丁改动；`case-ledger` 工作树 md5 `22103f04…` == HEAD；审前/审后 `git status --porcelain -uall` 均空，仓库内无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 新增残留（find 命中项全在 `.work/` 第三方源码与历史任务目录，非本册范围）；注入全在 `/tmp/opencode/TESTCASES-076t-review/`。
**剩余风险（非阻断，登记）**：① `night/2026-10-27` 报告已失效（其 4 个 log 被上轮 self-test 清空、10-28 已重跑替代）——新断言现会对其 `--date 2026-10-27` 判 FAIL rc=1，建议收尾时删该目录或加注记；② `/tmp/opencode/night-run-selftest-{84ca5tmu,uetxnmfp}` 两个历史遗留临时目录（非本册产生）；③ 完成区「L3 + tset smoke」等描述已被 082t/083t 取代（册内已注明「以当前 HEAD 门控为准」，文档级不阻断）。
**判决：Accepted**（两处 finding 均闭环、证据链回绿、约束无违反；全量/夜跑采信 architect 现场报告，reviewer 逐行核报告与门控）。

### architect 收尾（2026-10-28）
- reviewer 第 2 轮 Accepted；夜跑重跑 `2026-10-28` 4/4 rc=0、日志非空；自检 6/6、8/8；证据 `--fast` 41/41。
- 已删除失效的旧夜跑报告 `.dadao/tests/night/2026-10-27`（上轮 self-test 清零，不可恢复），以 `2026-10-28` 为权威报告。
