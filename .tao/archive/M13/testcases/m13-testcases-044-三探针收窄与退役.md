# m13-testcases-044: FMA/minmax/roundint 三个 C 探针收窄（先核 llvm 覆盖，再抽点进 `.S`，最后退役）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-043`（同改 `tests/inst.yaml` 与 `check-case-ledger`，须串行）
**可并行分片**：否
**预估**：3–5 h（阶段 A 审计 ~1 h；阶段 B 补点 ~1–2 h；阶段 C 退役 ~1 h）
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「是不是应该考虑 tests/unit/llvm/ 下面是否有匹配？」

→ 即：先核 `tests/unit/llvm/`（lit CodeGen + e2e）与 picolibc 是否已覆盖这三个 C 探针的能力；有覆盖的退役，没覆盖的按「≤127 + 边界/异常优先」抽点补进 `.S`，再退役。

## 三个探针现状（现场）

| 目录 | 文件 | 入口门控（L3） | 覆盖什么 |
|---|---|---|---|
| `tests/inst/fma/` | `fma_common.h`、`fma_edges.c`、`fma_dot.c`、`fma_horner.c` | `make check-fma-probe` | C 层 FMA **单次舍入**（点积/GEMM/Horner），`-O0/-O2`，与 `oracle_fma.py`（`fractions` 精确+一次舍入）比对 |
| `tests/inst/minmax/` | `minmax_common.h`、`minmax_matrix.c`、`minmax_clamp.c`、`minmax_c23.c` | `make check-minmax-probe` | C23 `fmin/fmax`（NaN/±0/clamp），与 `oracle_minmax.py` 比对 |
| `tests/inst/roundint/` | `rnd_common.h`、`rnd_matrix.c`、`rnd_mode.c`、`rnd_flags.c` | `make check-rnd-probe` | `ftrnd/fornd` 六种舍入 × 标志矩阵，与 `oracle_rnd.py` 比对 |

9 条 `.c` 同时登记在 `tests/inst.yaml`（`inst-fma-001..003`、`inst-minmax-001..003`、`inst-roundint-001..003`）。

## 阶段 A：覆盖核对（只读，先做）

逐项核 `tests/unit/llvm/` 与 picolibc 的**真实执行**（不是"文件存在"）：

1. `lit/CodeGen/DADAO/fma.ll`、`p1-fp-minmax.ll`、`p1-fp-rounding.ll`、`p1-fp-rounding-f32.ll`、`fp-rounding-mode.ll` —— 断言的是什么（指令选择 / 结构）；
2. `e2e/fma_e2e.c` + `lit/fma_e2e.test` —— 是否**运行**并验证单次舍入（读源码确认构造了两步舍入会得 0 的输入）；
3. `e2e/p1_fp_e2e.c` —— 注释称 floor/ceil/trunc/round/rint/nearbyint、fmin/fmax 的 libcall 类由 picolibc 证据 runner 承担 ⇒ **实跑 `make check-picolibc-tests`（或对应目标）**，核实 `test-floor/test-ceil/test-round/test-minmax/test-fma` 是否真的在跑、是否比数值（不是只比退出码）。

**输出**：`<运行期证据目录>/coverage-matrix.tsv`（能力 × `.S` × lit × e2e × picolibc × 结论），缺口列明。

## 阶段 B：按缺口抽点补进 `.S`（只在阶段 A 判定「没覆盖」处做）

- 候选载体：`ftfma_rrrr_rf.S`/`fofma_rrrr_rf.S`、`ftmin/ftmax/fomin/fomax_orrr_rf.S`、`ftrnd/fornd_orri_rf.S`；
- 每个缺口 **补 3–5 条**（遵守 `docs/Process-05 §3.1`：特定值 + 随机固定种子；**边界/异常优先**，不许全量补格）；
- 每条在 `.S` 注释写 spec 依据 + 手算过程；期望值**不得**抄 `oracle_*.py` 输出（须由 spec 独立推导；`oracle_*` 只作交叉检查）。

## 阶段 C：退役（阶段 A/B 完成后）

1. 删 `tools/testcases/run_{fma,minmax,rnd}_probe.py` 与 `oracle_{fma,minmax,rnd}.py`；
2. `Makefile` 摘除 `check-{fma,minmax,rnd}-probe`（L3 成员、`.PHONY`、`help` 行），`docs/Process-07` 组合表同步；
3. 删 `tests/inst/{fma,minmax,roundint}/` 三个目录（9 个 `.c` + 3 个 `.h`）与 `tests/inst.yaml` 对应 9 条（现场核计数：`inst` 305 → 296）；
4. `check-case-ledger` 重生成；`grep -rn "run_fma_probe\|oracle_fma\|check-fma-probe"` 在 `Makefile`/`tools/` = 0（历史归档除外）。

## 验收（逐条贴真实 rc / 现场值）

1. 阶段 A 的 `coverage-matrix.tsv` 完整；**若某项"看起来有覆盖"但实际只比退出码 ⇒ 记为缺口**并进入阶段 B。
2. 阶段 B 补的条目：每 id ≤127（门控核）、边界/异常类先行、seed 注明；`check-inst-asm` id 数 264 不变、镜像数按现场 +N。
3. 阶段 C 后：`check-case-ledger` rc=0（计数现场值）、`check-tests-index` rc=0（296 现场核）、`validate-vectors` rc=0；`make check-picolibc-tests` 仍 rc=0。
4. **不许**把这三个探针的 oracle 结果当新向量的期望值（Independent oracle 判据）；`fp_ref.py` 保持"生成期工具"定位。
5. 可达 FAIL 注入 ≥2 路（删一条新 `.S` 点 ⇒ `check-inst-asm` 红；改 `Makefile` 留一处 probe 引用 ⇒ `grep` 断言红）。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 节点仓库**。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/inst/**`（`.S` 与三个目录）、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/**`、`Makefile`、`docs/Process-07`、任务书；**不改** `spec/`、`contracts/`、`components/**`。
5. 测试派节点、有空位就发；`--jobs` = 核数−2 减占用。

## 待裁定

**R1（oracle 三件未删，需裁定）**：`tools/testcases/oracle_{fma,minmax,rnd}.py` **保留**——`tools/gem5/b7_ref.py`（GEM5-012t 差分参考模型）在 import 期硬依赖 `oracle_fma` 的 `classify`/`floor_log2`/`encode`，并在 `--selftest` 里与三个 oracle 交叉检查（行 68-70/111/136/171/358/1113/1122/1130）。删文件会打断 gem5 B7 工具（无门控覆盖，故不会变红，属静默破坏）。
- 选项 A（建议）：另立小任务把三个 oracle 迁到 `tools/gem5/`（或 `tools/testcases/lib/`）作共享的 spec 精确算术库，`b7_ref` 改引用后本任务即可删。
- 选项 B：本任务扩围改 `tools/gem5/b7_ref.py`，把三个原语内联进去（约 3 处函数）后删 oracle。
- 选项 C：维持现状（oracle 留作共享库），仅在 `tools/testcases/README.md` 注明其消费者。

**R2（退役同步的文档越界）**：`tests/README.md`（15、157-159 行）、`tests/INVENTORY.md`（69-71、197-199 行）、`docs/Process-09-测试组织规范.md`（68、82、291 行）仍列三个探针与已删目标，**不在本任务可改文件集**。
- 选项 A（建议）：授权本任务补这三处（纯删除/改写，无判据变更）。
- 选项 B：另立一条文档同步小任务。

## 审阅记录

### 第 1 轮 engineer 自审（实现方，逐行）

自审范围：8 个 `.S` 的 34 条新点（期望值来源 = 自写 Fraction 模型按 `spec/SimRISC-07 §2.3/§2.4/§2.5` 推导，未读 `oracle_*.py`；已回读校验操作数常量：`0x3FF4000000000000`=1.25、`0x7C80000000000000`=2^969、`0x72800000`=2^102、`0x3FA00000`=1.25f）、`tests/inst.yaml`、`Makefile`、`l3_run.py`/`check_l3_report.py`、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 minmax 新点从 18 起编，漏算原 fault 占 17 ⇒ `run_asm_suite` 报「点号不是 1..N 连续」 | ✅已修 | minmax 四载体新点改 17-20、fault 改 21 | 扫描 + QEMU 170 镜像 PASS |
| F2 fornd/ftrnd 同类（新点应 25-28，fault 29-32）；批量重编号脚本二次替换把 fault 也压到 25-28 与链例撞号 | ✅已修 | 按文件顺序重排为链例 25-28 / fault 29-32 | 同上；`check-inst-asm` 901/901 |
| F3 证据脚本 `inject_one` 用 stdout 回传备份路径，与 `ok()` 输出串行 ⇒ 还原失败，现场一度留在注入态 | ✅已修 | 备份路径/原始 md5 改全局变量；还原判据改「md5 == 注入前」（不对账 git status） | `--inject` 8/8 PASS；现场核对 `TEST_FP4 24` 行与 Makefile 尾部均复原 |
| F4 判定删 `oracle_*.py` 会打断 `tools/gem5/b7_ref.py` | ✅按裁定处理 | 保留三件，写 R1（不静默删） | `b7_ref.py` 行号证据见 R1 |
| F5 删 runner 后 `check_writer_guards.READER_ENTRIES` 指向不存在文件 ⇒ L1 崩溃 | ✅已修（越界披露） | 去掉三条登记 + 一行注释 | `make check-writer-guards` 27/27 PASS |
| F6 文档残留（README/INVENTORY/Process-09）不可改 | ⏸延后 | 登记 R2 | 残留清单见 R2 |
| F7 补点是否越过 ≤127 / 与既有段落重复 | ✅不修（无问题） | 每 id 24/24/20/20/20/20/28/28 点；新点均为原载体未覆盖的边界 | `check-tests-index`（含 ≤127 判据）rc=0 |

**判决**：F1/F2/F3/F5 已修并复验；F6 待裁定（R2）；F4 按 R1 处置；无未修的自审缺陷 ⇒ 交付 `待验收`。

### 第 1 轮 reviewer 验收（独立重跑，2026-11-15）

**重跑（本人执行，全部真实 rc）**：① `make check-tests-index` rc=0，`每 id 用例上限（≤127）: 265 个 id，最大 ft2it_orri_rf=34`、`结果: PASS（474 条）`；② `make validate-vectors` rc=0（156/156，265 载体+1 非 id）、`check-case-ledger` rc=0（5292=asm 4769/lit 523）、`check-no-residue` rc=0、`check-knowledge-refs` rc=0（悬空 0）、`check-writer-guards` rc=0（27/27）；③ `make check-inst-asm` rc=0：`265 个 id / 901 个镜像`、`901/901`，现场扫描 265 载体检查点合计 **4132**（基线 4098，+34 = fofma/ftfma 各 5、四 minmax 各 4、fornd/ftrnd 各 4）；④ 退役：`make -n check-{fma,minmax,rnd}-probe` 三者 `No rule`，`grep -rn "run_*_probe|check-*_probe" Makefile tools docs tests/inst tests/inst.yaml` **0 命中**，`tests/inst.yaml` 现场 **274** 条、probe id 0；⑤ 证据脚本（审+重跑）：默认 `PASS（23/23）` rc=0、`--inject` `PASS（8/8）` rc=0 且两路 md5 还原。

**picolibc 覆盖复核**：`--stage fast` rc=0 `total=20 pass=18 fail=0 excluded=2 blocked=0`，实跑清单 = 每 suite 首个代表（源码 `representative_names()`：`One representative per suite, first in Meson order`），math 档仅 `test-acos`、**不含** test-floor/round/fma，另有 `math_test(newlib.math)` pass ⇒ 「fast 不跑那四条」成立；`--only test-floor,test-round,test-fma,test-fenv,test-rounding-mode` rc=0 **5/5 PASS**（缺口确可由 `--only` 复核）；`--only test-math-funcs,test-ceil,test-math-errhandling` rc=1 → `blocked ISS-193 / blocked ISS-193 / fail exit 3` ⇒ 三条判定成立；`test-math-funcs.c` 仅赋值无断言（恒真）、`newlib.math` 含 `ceil/floor/trunc_vec.c` 向量 ⇒ 矩阵这两条成立。

**6 点期望独立推导（按 `spec/SimRISC-07`，不读 oracle 输出）**：① fofma/ftfma **20 轻微溢出只 NX**：精确和 = max+¼ulp（fo C=2^969/ulp 2^971；ft C=2^102/ulp 2^104）< §2.5 分界 max+½ulp（fo 2^970、ft 2^103）⇒ 无限指数 RNE 舍回 max ⇒ 「不构成溢出」⇒ 结果 max、`0x10`；② **21 RUP 溢出**：向 +∞ 舍到 2^1024/2^128 > max ⇒ §2.5 表 RUP 正溢出 = +Inf、恒 `OF|NX=0x14`；③ **22/23 次正规+inexact**：1.25 单位 → RNE 1 单位（`…0001`）/ RUP 2 单位（`…0002`），舍入后仍 <2^emin ⇒ tiny 且 inexact ⇒ `UF|NX=0x18`（§1.4 tininess=舍入后）；④ minmax **17 −qNaN 单 NaN**：§2.4 第 4 条返回「那个数」、qNaN 不置标志、与符号无关 ⇒ `1.0`/`0x00`；⑤ minmax **19 minsub vs +0**：§2.4 第 1 条按数值序（次正规 > 0）⇒ fomin=`+0`、fomax=`minsub`；⑥ fornd/ftrnd **25/26 −2.5**：§2.3 静态 `0x02` 平局远离 0 ⇒ −3、`0x01` 取偶 ⇒ −2，静态档不置 NX；**27/28** 动态 `0x20` 读 rf0=RDN/RUP ⇒ +2/−2 且结果≠输入 ⇒ `0x10`。注释手算（ulp/分界/1.25 单位）与 spec 逐条自洽；三 oracle selftest 现场 32/153/284 全绿，未用作判据。

**R1 依赖（独立核）**：`tools/gem5/b7_ref.py:68-70` 在**模块顶层** `_load("oracle_fma|minmax|rnd", …)`；临时树删 `oracle_fma.py` 后 import 即 `FileNotFoundError` ⇒ import 期硬依赖**成立**；唯一 consumer = `check_b7.py:447`，`grep b7 Makefile` 0 命中 ⇒ 「无门控覆盖」成立。**建议选项 A**（迁 `tools/testcases/lib/` 作共享 spec 精确算术，`b7_ref` 改引用）；**B 不可取**：`b7_ref --selftest` 与三 oracle 的交叉（1113/1122/1130）是**第三实现互证**，内联即自比（恒真，违「禁同源自比」）；C 的风险是依赖仍无门控、后人清理必踩；无论选哪项，建议补一条 L1 静态断言（`b7_ref` 三个被载文件存在）。

**越界核**：`READER_ENTRIES` 删 3 条**必要**（三条正是被删 probe runner，保留则 S1 判红，实测注入该条目 → `FAIL S1 guarded-reader-wiring`）；但完成区「否则 L1 **崩溃**」不准确 —— `_read()` 吞 `OSError` 返回 `""` ⇒ 是 **S1 FAIL 而非崩溃**。W1 可失败性未削弱（W1a rc=75 拒绝 / W1b override / W1c 回绿 均在，27/27）。

**R2 现状**：master `c87f1323` 已改三处（本分支未含）；现场仍留**现行口径**残留 `tests/README.md:55`、`tests/INVENTORY.md:223`、本册 `tests/inst.yaml:9,14`（`check-{rnd,minmax,fma,clmul}-probe` 已删目标）；`README:15`/`INVENTORY:12` 属迁移史叙述可留 ⇒ 文档级 finding。

**findings（均文档级/不阻断，交 architect 收尾处理）**：F1 「崩溃」措辞；F2 矩阵「picolibc 无 minmax 自测」不准确 —— `test/test-math/test-math-errhandling-tests.c:3241-3256` 有 12 条 fmin/fmax 值+异常断言（但该套件现 `FAIL exit 3` 既有、且不覆盖次正规/±Inf/±0 序 ⇒ 补点仍成立，措辞应改）；F3 矩阵「18 行」含表头（capability 行 17）、`GAP-记账` 严格为 1；F4 **未披露的活引用**：`tools/gem5/check_b7.py:320-321 asset_check` 断言三个被删目录（现场 4 条 missing，其中 `tests/inst/fp/scaleb.yaml` 派单基线即缺 ⇒ 该检查基线已红、且无门控）⇒ 建议立 **R3** 由 gem5 侧任务改 `tools/gem5/`；F5 `tests/inst.yaml` 头注释仍指已删目标（本册可改未改）。

**本人独立注入（与脚本不同路，`cp`+md5）**：改 `fofma id20` 期望 `0x7FEFFFFFFFFFFFFF`→`0x7FEFFFFFFFFFFFFE` ⇒ `make check-inst-asm` **rc=2**、`900/901`、日志 `[FAIL] fofma_rrrr_rf.S chain 检查点 24 / rc 20`（退出码 20 = 点号 20，证明新点在 QEMU 运行期被真断言）⇒ 还原 `md5 e3aa10b6… == 注入前` ⇒ `make check-inst-asm` rc=0 `901/901`。

**约束核验**：独立 worktree、分支=任务号、toplevel 自证 ✓；**未提交**（HEAD 仍 `3f6995fe`）✓；未跑 `install-host`/`check-modules`/`build-*`（picolibc 按 harness recipe 直跑以绕开 build 前置，已在此披露）✓；未 sync/reset 节点 ✓；注入还原只用 `cp`+md5（未用 checkout/restore/stash）✓；改动 **33 文件**与完成区「修改文件」逐项对账一致、`git status -uall` 验收前后均 **0 行** ✓；台账/`discussing.md` 未动 ✓；完成区 12 行 ≤30、全册无运行期路径 ✓。

**判决：Accepted** —— 验收命令块在本人重跑下全绿、硬约束无违反；F1–F5 由 architect 在收尾提交里改/登记（F4 建议立 R3，R1 仍待用户裁定）。

## 完成区

**测试结果**：证据脚本默认 23/23、`--full` 24/24 PASS；注入自检 `--inject` 8/8 PASS。
**修改文件**：8 个 `.S`（`07-floating-point/{fofma,ftfma,ftmin,ftmax,fomin,fomax,fornd,ftrnd}_*.S`，+34 点）；`tests/inst.yaml`（-9 条）、`tests/case-ledger.tsv`（重生成）、`Makefile`、`tools/testcases/{l3_run,check_l3_report}.py`、`docs/Process-07`、`tests/inst/{README,MIGRATION}.md`；删除 `tools/testcases/run_{fma,minmax,rnd}_probe.py` 与 `tests/inst/{fma,minmax,roundint}/`（12 文件）。**越界披露**：`tools/infra/check_writer_guards.py`（删三条 READER_ENTRIES，否则 L1 该门控崩溃）。
**验收结果**：
1. 覆盖矩阵 18 行（COVERED 6 / GAP->已补 6 / GAP-记账 2）：lit 7/7 PASS（含 `fma_e2e.test` 真跑 guest）；picolibc fast 20 例 pass=18/excluded=2/fail=0/blocked=0；数学子集 test-floor/test-round/test-fma/test-fenv/test-rounding-mode PASS、test-ceil 与 test-math-funcs BLOCKED(ISS-193)、test-math-errhandling FAIL(exit 3，既有)。
2. 补点 34，边界/异常优先、每条注释带 spec 依据与手算：fofma/ftfma id20-24（轻微溢出 RNE 只 NX、RUP 溢 OF|NX、次正规结果 UF|NX ×RNE/RUP、Inf 作加数）；fomin/fomax/ftmin/ftmax id17-20（−qNaN 单 NaN、次正规次序、minsub vs +0、±Inf 对）；fornd/ftrnd id25-28（−2.5 RNA/RNE、动态 RDN/RUP 置 NX）。每 id 检查点 24/24/20/20/20/20/28/28（≤127）；无随机抽样（全为特定边界值，故无 seed）。
3. `make check-inst-asm`：901/901 镜像、265 id、链例 264、故障例 637，检查点合计 4132（改前 4098，+34）。
4. 退役后 rc=0：`tests/inst.yaml` 283→274 条（现场，非预估 305→296）；`check-tests-index`（474 条）、`validate-vectors`（156/156，265 载体 + 1 非 id）、`check-case-ledger`（5292 身份：asm 4769/lit 523）、`check-no-residue`、`check-knowledge-refs`；`make -n check-{fma,minmax,rnd}-probe` 三目标均 "No rule"；picolibc fast 仍 rc=0。
5. 注入 2 路（`cp`+md5 还原）：删 fofma id24 行 ⇒ `run_asm_suite` rc=2（点号不变式）⇒ 还原 md5 一致 ⇒ rc=0；Makefile 留一行 `check-fma-probe` ⇒ 残留检查器 rc=1 ⇒ 还原 ⇒ rc=0。
**新发现/坑**：`check-picolibc-tests`（fast）每 suite 只跑**首个**代表用例（math 档 = `test-acos`）⇒ **并不跑** test-floor/ceil/round/fma；它们只在 `--stage full` 或 `--only` 下真跑，lit 注释里"由 picolibc runner 承担"的说法须用 `--only` 复核。`math_test`（newlib.math，在 fast 档内）覆盖 ceil/floor/trunc 数值向量，补上 test-ceil BLOCKED 的缺口。`test-math-errhandling` 既有 FAIL。lit `p1-fp-rounding*.ll` 头注释仍称 fornd/ftrnd "scope: excluded ⇒ 运行期 ILLI"，与 `contracts/opcodes.yaml`(`scope: fp`) 及 `.S` 实跑矛盾（stale，未改：越界）。`run_asm_suite` 的点号不变式是很好的注入点（删行即 rc=2）。
**遗留问题**：① oracle 三件未删（R1，`tools/gem5/b7_ref.py` 硬依赖）；② 三处文档仍列退役探针（R2，不在可改集）；③ L1 现场 4 项既有红，均非本任务：`check-patch-tree`（linux/chipyard 在途改动）、`check-musl-freshness`（ISS-437）、`check-run-artifacts`（m12-chipyard-016 日志命名 912 条）、`check-temp-dirs`（早前任务残目录 4 个）；④ C 层 rint/nearbyint 无 libm 数值自测（矩阵已记账，建议并入 picolibc 侧任务）。
