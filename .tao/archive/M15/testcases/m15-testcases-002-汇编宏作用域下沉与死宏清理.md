# m15-testcases-002: 汇编宏作用域下沉（共享层 → 册/文件）+ 死宏清理 + 门控

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-001`（已验证：把 10 个 FP 宏下沉到共享层——**本任务按新口径回退其中单册部分**）；`m14-infra-004`（在跑的改名任务）**必须先合入**（两者都改 `tests/inst/**`）
**可并行分片**：否（`tests/inst/**` 单写者）
**预估**：3–4 h（机械搬运 + 字节级对账 + 新门控）
**档位**：中改（多文件搬定义 + 新增门控；复核 ≥2 路注入 + md5 对账）
**状态**：已验证

## 背景（用户 2026-11-15/16 口径）

> 「如果某个宏就只用于某个汇编测试程序，则应该把这个宏移动到该汇编测试中」

即**方向与 `m15-testcases-001` 相反**：`m15-testcases-001` 把 8 个 FP 文件里重复的宏**上抬**到共享层；按本口径，凡**只在一个册（更别说一个文件）里用**的宏都应**下沉**到册/文件，共享层只保留**跨册**宏。

## 现场统计（主会话实测，2026-11-16，`tests/inst/macros/inst_test.inc` = 132 宏 / 2,135 行）

按「反向闭包」统计真实使用者（宏被别的宏调用时继承调用者的使用者）：

- **死宏（使用者 0）**：**14 个 / 166 行** —— `TEST_FAULT_BR1`、`__CHECK_FP_RF`、`__VERIFY_FP_RF`、`__VERIFY_FP_RF_MEM`、`__CHECK_FP_RF_MEM`、`TEST_FPCOPY1..4`、`TEST_FPCOPY_ENC2`、`TEST_FPCOPY_TOP1`、`TEST_FPCOPY_TOP4`、`TEST_FPCOPY_31`、`TEST_FPCOPY_ADJ`；
- **只用 1 个 `.S`**：**18 个 / ≈170 行** —— 如 `TEST_LD_RA`→`01-load-store/ld.o_rrii_ra.S`、`TEST_LD_RB`→`ld.o_rrii_rb.S`、`TEST_LD_RF`→`ld.o_rrii_rf.S`、`TEST_LD_RF_LO32`→`ld.t_rrii_rf.S`、`TEST_ST_RA/RB`→`st.o_rrii_ra/rb.S`、`__CHECK_MEM_RB`→`st.o_rrii_rb.S`、`__VERIFY_MEM_RF`/`__CHECK_MEM_RF`→`02-reg-copy/rf2rf_orri_rf.S`、`TEST_WI_*`(4)→`03-wyde-imm/set.w_rwii_rf.S`、`TEST_AR_SI`/`TEST_FAULT_ALU_SI`→`04-arith-logic-octa/add.si_riii_rd.S`、`TEST_AR_RB_SI`→`05-arith-add/add.si_riii_rb.S`、`TEST_FAULT_RASUF_MEM`→`06-control-flow/ret_riii_ra.S`、`TEST_FPCOPY_RF0`→`00-isa-design/pseudo_set.fx_reg.S`；
- **只用 1 个册（多文件）**：**74 个 / ≈902 行** —— `01-load-store` 9、`02-reg-copy` 7、`03-wyde-imm` 5、`04-arith-logic-octa` 4、`05-arith-add` 5、`06-control-flow` 8、**`07-floating-point` 36**（含 `m15-testcases-001` 上抬的 10 个 FP 宏）；
- **跨册共享（应留共享层）**：**26 个 / 372 行**；
- 合计可下沉 **1,000 行（47%）** + 死宏 166 行。

## 目标

1. **死宏删除**：14 个死宏（166 行）确认无人使用后删除（若有注释指向已退役用例，一并清理）；
2. **单文件宏下沉**：18 个宏从共享层移到其使用文件内（定义放在该文件 `.include` 之后、首个用例之前）；
3. **单册宏下沉**：74 个宏移到**册级 include**（新建 `tests/inst/<册>/<册短名>.inc`，由该册各 `.S` 在共享层之后 `.include`）；`07-floating-point` 的 36 个按此落；
4. **共享层收窄**：`inst_test.inc` 只保留 26 个跨册宏（+ 必要的公共 helper），并在文件头写明「本层只放**跨册**宏；册专用 → 册 `.inc`；单文件 → 该文件内」；
5. **新增门控 `check-inst-macro-scope`（L1）**：机械判三条 —— ① 共享层宏的**跨册使用者数 ≥2**；② 册 `.inc` 里每个宏的使用者**只在该册**；③ `.S` 内定义的宏**只被该文件使用**；任一违反即红（含失败样例自检，证明可 FAIL）。

## 验收（真实 rc + 输出）

1. **零语义变化（核心）**：全部 272 个 `.S` 在全部形态（链例 + 各故障点，形态数从 `run_asm_suite.scan_source` 现场取）下组装，改前/改后 `.o` **md5 逐一相等**（贴 `N/N`）；`make check-inst-asm` **904/904** 且镜像数不变；
2. 静态计数：共享层宏数 132 → **26（±必要的公共 helper，逐条列出）**；死宏 0；单文件/单册宏各自归位（贴脚本现场统计，不写死）；
3. 新门控 `check-inst-macro-scope` 进 L1 且**自检可翻转**（注入一条违规宏 ⇒ 红）；
4. **≥2 路注入**（`cp`+md5 还原）：① 把某册宏挪回共享层 ⇒ 新门控红；② 删掉某册的 `.inc` include ⇒ 组装失败/门控红；
5. 其它门控：`check-tests-index`（`NON_ID_CARRIERS` 等登记不变）、`check-dirs`、`check-no-residue`、`make check` 全绿；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只搬定义、不改任何用例行/宏体语义**（宏体逐字搬运，禁顺手优化）；
- 不新增/删除用例；不改 `inst_test.inc` 之外的共享工具；
- 不提交 git；注入还原 `cp`+md5；临时文件放运行期临时目录；与本任务无关的 `tests/inst/12-misc` 结构去重归 `m15-testcases-003`（勿越界）。


> **收尾订正（2026-11-16，按 reviewer F1–F4）**：① 改动 `.S` 实为 **168**（167 含新增行 + `pseudo_set.fx_reg.S` 仅 2 行注释）；② 「905/905 镜像」应写「**904 镜像 + 1 个非镜像对象**（`undi_reserved.S` CASE_N=0，该文件无链例）」；③ `TEST_FPCOPY_RF0` **不是** `m14-infra-004` 改名所致（`e96f0f19` 未动这两个名字）——真因是任务书把 **1 处 `@@` 注释提及**当成了使用者；旧名在基线即 0 使用者；④ 证据脚本 D 项基线取 `git archive HEAD` ⇒ **提交后重跑会变成自比假绿**；基线须钉死 commit（本轮以 `8da8c985` 独立补证）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`tests/inst/macros/inst_test.inc`、7 个册 `.inc`、167 个 `.S` 的插入行、
`tools/testcases/check_inst_macro_scope.py`、`tools/testcases/inst/run_asm_suite.py`、
`tools/infra/check_case_ledger.py`、`Makefile`、`tests/inst/README.md`。

findings：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `.S` 内的文件宏体含 `\t__CHECK_* \pt, ...` 行（42 行宏体命中用例行正则，其中 5 行属单文件宏）⇒ `scan_source`/case-ledger 会把宏体当用例行，检查点数与用例身份被污染 | ✅已修 | `run_asm_suite.iter_code_lines`（跳过 `.macro`..`.endm`），`scan_source` 与 `check_case_ledger._asm_rows` 同源复用 | 旧/新扫描器逐文件比对 272 `.S` 检查点/故障数漂移 0；`check-case-ledger` 5438 行 PASS |
| 2 | 门控 `--selfcheck` 干净基线判据写错（`expect==""` 时仍要求命中 needle ⇒ 基线误红） | ✅已修 | `good = (rc==want_rc) and (not bad if not expect else hit)` | selfcheck 6 行全 PASS（基线 rc=0 + 5 类注入 rc=1 且命中对应判据） |
| 3 | 门控未禁 `.S` include 别册 `.inc`（S5 只查本册 include 存在） | ✅已修 | S5 增 `allowed = {共享层, 本册 .inc}`，其它 `tests/inst/**.inc` 即红 | 默认树 PASS；selfcheck 5 类注入仍各自红 |
| 4 | 自检/证据临时树建在 `/tmp` 根（违反「临时目录统一 `/tmp/opencode/<任务ID>/`」） | ✅已修 | 门控 `TMP_ROOT`、证据 `TMP` 改到 `opencode/m15-testcases-002/` 下并清理 | 运行后目录已删；`check-temp-dirs` PASS |
| 5 | 死宏删除后仍有注释指向已退役宏（共享层控制流 banner、06/07 册 `.inc`、`pseudo_set.fx_reg.S` 各 1 处） | ✅已修 | 4 处注释改写（仅注释，无代码行） | `.S` diff：除 1 个文件 2 行注释改写外全为插入；905/905 `.o` md5 仍相等 |
| 6 | 任务书统计（14 死宏 / 74 单册 / 26 跨册）与实测（15 / 75 / 24）不符 | ❌不修（记录） | 无代码改动 | 原因见完成区「新发现/坑」：旧名 `TEST_FPCOPY_RF0` 已被 m14-infra-004 改名 `TEST_MOV_RF0`，任务书清单用的是改名前的名字 |

判决：findings 1–5 已修并有证据；#6 为任务书快照差异（记录，不改判据）。→ `待验收`。

### 第 1 轮 reviewer 验收（2026-11-16，中改档）

**扫描器等价（自写 2×2，`scan_equiv.py`，非采信工程师漂移 0）**：旧扫描器@旧树 vs 新扫描器@旧树 = 4284 检查点/633 故障点/**0 文件漂移**；新扫描器@旧树 vs @新树 = 0；**交付口径（旧@旧 vs 新@新）= 4284/633、0 漂移**。必要性实证：旧扫描器@新树 = **4289** 检查点、5 文件 `pts_ok=False`（`scan_source` 会 rc=2）、ledger **5443** 行 ⇒ 不改必红；旧扫描器@旧树 0 漂移 ⇒ 改动不影响改前行为。ledger 2×2：旧@旧 = 新@新 = 新@旧 = **5438 行 md5 `6fb901fc…`**（旧@新 5443）。
**零语义（自建基线 `git archive 8da8c985`，`obj_md5.py`）**：llvm-mc 全形态 **904/904 `.o` md5 相等、0 不等**（链例 271 + 故障 633）；完成区第 905 个对象（`undi_reserved.S` CASE_N=0，无链例）亦相等。`make check-inst-asm` 我方重跑 **904/904 PASS、EXIT=0**。
**归位（自写反向闭包 `closure_check.py`，不复用门控实现）**：共享层 **24 宏全部跨 ≥2 册**（最少 `TEST_FAULT_CF1`/`__SET_MEM` = 2 册，最多 `__CHECK_RD` 13 册）；7 个册 `.inc` 75 宏**册外使用者 0**；`.S` 内 21 宏/13 文件**他文件使用者 0**；**死宏 0**。同口径跑基线：**15 个死宏**（任务书 14 + `TEST_FPCOPY_RF0`），与完成区一致。
**2 路自设计注入（临时树，`git archive d3b0cd23` 导出后注入，cp+md5 还原）**：① 01 册宏 `TEST_LD` 在 `02-reg-copy/rf2rf_orri_rf.S` 加调用 ⇒ **rc=1 `[S2] 被册外使用`**；② `ld.o_rrii_ra.S` 宏定义改名一字 ⇒ **rc=1 `[S4] 死宏`** 且 `llvm-mc` 报错（未定义 `TEST_LD_RA`）；两次均还原回 **rc=0**、md5 与备份一致。`--selfcheck` 我方重跑 **6/6 PASS（基线 + 5 类注入）**。
**门控（我方重跑）**：`run.sh` → **ALL PASS、EXIT=0**；`make check` → **EXIT=2，唯一红 = `check-milestones-fresh` R1 `m15-spec-002` 有 worktree 未入表**（并发任务台账缺口，归因非本任务）；其余含 `check-inst-macro-scope`(PASS)、`check-tests-index`(total=476、载体 272/索引 272)、`check-case-ledger`(5438 PASS)、`check-dirs`、`check-no-residue` 全 PASS。
**越界**：diff 182 文件 = `tests/inst` 174 + `Makefile` + `tools/` 3 + 本任务书；`spec/`/`contracts/`/`components/` **0 改动**；`12-misc` 0 改动；`.S` 删除行**仅 2 条注释**（+389/−2）；两处扫描器各 1 行、必要且最小（`iter_code_lines` 单一真源，两处同源复用）。
**findings（非阻断，交 architect 收尾改）**：① 完成区「167 个 `.S`」实为 **168**（167 含新增行 + `pseudo_set.fx_reg.S` 仅 2 注释行；+389/−2 覆盖 168 文件）；② 「905/905 **镜像**」中 905 = 272×CASE_N=0 + 633，**真实镜像 904**（`undi_reserved` 无链例），对象 md5 确全等；③ `TEST_FPCOPY_RF0` **非**被 `m14-infra-004` 改名（该 commit 未动这两个名字，基线中两者并存、旧名 0 使用者即死宏、`TEST_MOV_RF0` 另存且活）——任务书「→`pseudo_set.fx_reg.S`」是把 `@@` 注释提及当成使用者；④ 证据脚本 D 项基线取 `git archive HEAD`，**提交后重跑会变成自比**（原 run.log 10:36:04 早于 commit 10:36:24，当时有效）⇒ 建议钉死基线 commit。
**判决：Accepted** —— 验收 1–6 全部由 reviewer 亲自重跑通过、约束无违反；工作区快照：主工作树 HEAD `20c3f77d` 与 `git status` 空、`Makefile` md5 `19caef53…` 未变；任务树 `git status` 干净、HEAD `d3b0cd23` 未被本轮改动。

## 完成区

**测试结果**：6/6 组检查通过 —— ① 零语义变化 905/905（272 `.S` × 全形态 `.o` md5 相等）；`make check-inst-asm` 904/904（272 id；链例 271/故障例 633，与改前现场扫描一致）。② 门控正例 rc=0、`--selfcheck` 6/6 PASS、3 路注入各自红且 cp+md5 还原后回绿。③ `check-tests-index` 476 条 / `check-case-ledger` 5438 行 / `check-dirs` / `check-no-residue` PASS。④ L1 除 `check-milestones-fresh`（遗留 1，非本任务）外全绿（其余 14 个后置目标单独跑 rc=0；`compileall`/`check_issues` rc=0）。
**修改文件**：`inst_test.inc`（132 宏/2134 行 → **24 宏/661 行**，头写三层规则）；新建 7 个册 `.inc`（75 宏：01:9 02:7 03:5 04:4 05:5 06:8 07:37）；167 个 `.S`（+389/−2 行：册 include + 18 个单文件宏下沉，−2 为注释改写）；新 `tools/testcases/check_inst_macro_scope.py`；`run_asm_suite.py`（`iter_code_lines`）+ `check_case_ledger.py`（同源复用）；`Makefile`（目标 + L1 前置 + help）；`tests/inst/README.md`。
**验收结果**：死宏 15 个 / 191 行（含注释）已删，死宏 0；`.S` 内宏 21 个 / 13 文件（18 下沉 + 3 原有）；门控现场打印 `共享层 24 / 册 .inc 7（75）/ .S 内 21（13 文件）/ .S 272 / 死宏 0`。证据脚本逐项：A 静态计数 / B 正例 / C 自检 / D md5 905 形态 / E 注入 3 路（S1；S5+组装失败；S4）/ F 5 个门控 —— 全 PASS（运行期证据目录，未入库）。
**新发现/坑**：(1) `.S` 宏体会被用例行扫描误读（42 行命中，5 行属单文件宏）⇒ 扫描器必须跳过 `.macro`..`.endm`，否则检查点数/用例身份被污染。(2) 任务书统计快照偏旧：实测 **15 死宏/18 单文件/75 单册/24 跨册**（任务书 14/18/74/26）——旧名 `TEST_FPCOPY_RF0` 已被 m14-infra-004 改名 `TEST_MOV_RF0`（旧名成死宏、新名落到单文件），任务书清单仍写旧名；册名 `05-arith-add` 实为 `05-arith-addr`。(3) 共享层严格只留跨册（≥2 册）的 24 宏，不开「公共 helper」例外。
**遗留问题**：(1) `make check` 唯一红 = `check-milestones-fresh`：`VIOLATION: R1: m15-spec-002: 有 worktree 但未列入「进行中」/「已验证」表`（他人台账缺口；该门控只读 `.tao/` 台账 + `git worktree list`，本 diff 不触碰），其余 L1 目标全 rc=0。(2) `tests/inst/MIGRATION.md` 历史行仍提已删宏（历史迁移台账，非现行口径，未改）。(3) `TEST_FPCOPY_RF0` 不在任务书 14 死宏清单内但使用者为 0（旧名）⇒ 按「死宏=0」删除并记录。
