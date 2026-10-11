# INTEG-025t: M6 E2E + 门控收口（`test-m6`）

**模块**：integ
**项目里程碑**：M6
**依赖**：`TESTCASES-036t`~`039t`、`LLVM-065t`、`QEMU-053t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `tools/integ/**`（既有 E2E 驱动，如 `run_codegen_e2e.py`/`run_elf_e2e.py`；**优先复用、不重复造**）。
  - `Makefile`（既有目标 `check`/`check-lit`/`test-codegen`/`test-elf`/`test-semihost`）。
  - `TESTCASES-036t`~`039t` 的向量/驱动/对拍/Embench 产物；`LLVM-065t` 的 reloc；`QEMU-053t` 的 RAM@0 收口。
  - `spec/Process-04 §1`（里程碑开闭）、`spec/Process-05 §6`（落点规则）。
- **输出**：
  1. **M6 E2E 驱动**（落 `tools/integ/`；**优先复用**既有驱动，必要时扩展）：驱动 `lli` 值级对拍 / Embench / lit **全量档**。
  2. `Makefile`：新 target **`test-m6`**——**opt-in，不进 `make check`**。
  3. **`make check` 收口**（不回归）：既有门槛全绿。
- **约束**：
  - **`test-m6` 不进 `make check`**（opt-in；快档已在 `make check` 内）。
  - **不回归**既有门槛（`test-codegen`/`test-elf`/`test-semihost`/`check`/`check-lit`）。
  - **`spec/` 交集为空**。
  - 生成物落点遵循 `.dadao/tests/`（`INFRA-048t`/`Process-05 §6`）。

## 硬约束

- **临时目录** `/tmp/opencode/INTEG-025t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/INTEG-025t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：如需重建 ⇒ 开工前写明「重建 X，预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/integ/INTEG-025t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`test-m6` 定义正确**：`Makefile` 有 `test-m6` 目标；`grep` 证明其**不在** `make check` 依赖链内（opt-in）。
2. **E2E 跑通**：`make test-m6` EXIT=0（驱动 `lli` 对拍 / Embench / lit 全量档；给真实输出）。
3. **不回归**：`make test-codegen`/`test-elf`/`test-semihost`/`check`/`check-lit` EXIT=0，通过数与改前**逐项相等 / 不下降**（给真实输出）。
4. **落点合规**：生成物落 `.dadao/tests/`（`Process-05 §6`），`.work/log`/`.work/evidence` 不动。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/INTEG-025t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `test-m6` 误挂入 `check` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`tools/integ/**`、`Makefile`、必要时 `tests/e2e/lit/**` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**耗时**：开工申报 30–60 min；实际 ~55 min（无重建：install-host 增量 `no work to do`）。
**用户裁定**：无新增用户裁定（本任务无问答）。

**测试结果**（计数**现场统计**，不写死）：
- `make test-m6` **EXIT=0**；构成：① `check-lit-full` **12/12**；② `diff_ir_lli` **19/19 matched**（hits 19/19）；③ Embench **38/38**（= `src/*/` 现场发现 19 基准 × `-O0`/`-O2`，判据 guest exit 0）。
- 不回归（**一次一个 `make`**，均 **EXIT=0** 且逐项相等/不下降）：`test-codegen` **15/15**、`test-elf` **5/5**、`check-lit` **89/89**、`test-semihost` **25-svc PASS**、`check` **`repository checks: PASS`**。
- 一键证据脚本 **`EVIDENCE: PASS` / `RUN_EXIT=0`**（C1–C6）；驱动 `run_embench_e2e.py --inject` ⇒ **`INJECT: PASS`**。

**修改文件**（仅任务书范围；`.work/`/`.dadao/` 均 gitignored）：
- `Makefile`（新增 `test-m6` 目标 620 行 + `.PHONY` + help，各一处；**未进 `check` 依赖链**）
- 新增 `tools/integ/run_embench_e2e.py`
- 本任务书；工作产物 `.work/evidence/INTEG-025t/run.sh`、`.work/log/integ/INTEG-025t-*`。

**验收结果**（逐条对齐）：
1 **定义正确**：`grep -nE '^test-m6:' Makefile`→620；`sed -n '/^check:/p' Makefile | grep test-m6`→空；`make -n check | grep -c test-m6`→**0**（opt-in）。
2 **E2E 跑通**：`make test-m6` **TEST_M6_EXIT=0**（真实输出 `.work/log/integ/INTEG-025t-test-m6.log`）。
3 **不回归**：5 门控各 EXIT=0（`.work/log/integ/INTEG-025t-nonreg-*.log`），通过数与改前逐项相等。
4 **落点合规**：工作目录 `EMBENCH_E2E_WORK=$(TEST_ARTIFACTS_DIR)/m6-embench`、`IR_LLI_WORK=…/ir-lli-diff`（经 `paths.py` 解析）；`grep '\.dadao/tests' Makefile tools/integ/run_embench_e2e.py` 无literal；`.work/log`/`.work/evidence` 语义未动。
5 **`spec/` 交集空**：`git diff --name-only | grep '^spec/'`→空。
6 **证据脚本**：`run.sh` 全绿 `RUN_EXIT=0`；C2 注入（`check:` 追加 `test-m6`）⇒ C1 **FAIL** ⇒ `cp`+md5 还原（`dc6adf1a…`==）⇒ **回绿**（真实输出 `.work/log/integ/INTEG-025t-evidence-run.out`）。
7 **无残留**：`git status --porcelain -uall` 仅 `M Makefile` + `?? tools/integ/run_embench_e2e.py`；无 `*_tmp*`/`*.orig`/`*.rej`。

**新发现/坑**：
- ① `check-spec-refs`（可选）**保持登记**：仅补 `Toolchain-01` 前缀映射**不能闭**——会把 1 违规变 **91**（`contract-asm.md` 91 条 `[Toolchain-01 §N]` 全为**裸数字**节号，而 `resolve_section` 的 `_TEXT_LEAD_IN` 不含空格/`.`，`## 7.2 …` 无法匹配；另有 `§x` 占位符与 `## 附：与上游 \`spec/\` 的关系` 反引号不匹配）。真闭需改匹配器（数值节号解析）**越出**「补前缀映射」口径 ⇒ 未硬做（实测已存 `.work/log/integ/`）。
- ② Embench 属**manifest 锁定组件**（`INFRA-051t`），故驱动以 `src/*/` 为语料即**结构闭包**；执行集须 == 发现集（防驱动静默跳）。

**遗留问题**：无未修 finding。① `test-m6` 为 opt-in（不进 `check`），与既有快档互补；② `check-spec-refs` 1 违规保持登记（见上，须另立 `tools/infra` 任务修匹配器）；③ Embench 判据为 guest exit 0（`support/main.c` 返回 `!correct`），非执行语义 oracle（另由 M6 L1/L3 向量承担）。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-10-11；有代码改动 ⇒ 自主逐行审查）

**范围**：`tools/integ/run_embench_e2e.py`（发现/流水线/判据/结构闭包/`--inject`）、`Makefile`（`test-m6`）、`.work/evidence/INTEG-025t/run.sh`。

**核对**：Spec-first（判据 = `support/main.c` 返回 `!correct` ⇒ exit 0，溯源 `.work/log/integ/embench-analysis.md`；落点 = `Process-05 §6`/`ADR-0016 D6/D7`）；防造假（真实执行、逐项打印、结尾 `rc=$?` 无 `tee`、注入 FAIL 可达 + `cp`+md5 还原）；边界（仅 `tools/integ/**`+`Makefile`+本任务书；未触 `spec/`/`contracts/`/`components/`/`.opencode/`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `--inject` 复写判据表达式（`actual==expected`）→ 与 `build_and_run` 非同一代码路径 | ✅已修 | 抽出 `verdict(rc,expected)` 单一真源，`build_and_run` 与 `--inject` 共用 | `--inject` INJECT: PASS；`--opt O0` 19/19 rc=0 |
| F2 结构闭包仅查非空，未防「发现≠执行」静默跳 | ✅已修 | 加 `executed set == discovered set` 断言（§8.35） | 38/38 rc=0（未触发） |
| F3 证据脚本 C1 `.PHONY` 检测用 `\|\|/&&` 混排（可读性/易错） | ✅已修 | 改显式 `if`；C5 改整文件 `.dadao/tests` 字面检查 | `run.sh` EVIDENCE: PASS |

#### 第 1 轮 reviewer 验收

**快照**（预/后一致；md5 未变）：
- Makefile `dc6adf1a`、`run_embench_e2e.py` `944551eb`、任务书 `cf2a8793`、run.sh `ea8259b3`
- `git status --porcelain -uall` 预/后 diff 为空；变更：`M Makefile`、`M 任务书`、`?? tools/integ/run_embench_e2e.py`（+ `.work/` gitignored 产物）

**边界**：`git -c core.quotepath=false diff --name-only` → 仅 `Makefile` + `任务书`（无 spec/contracts/components）；untracked 仅 `tools/integ/run_embench_e2e.py`；无 `_tmp`/`_orig`/`_rej`/`~`/`.bak`。

**opt-in 核实**：
- `grep -qE '^check:.*test-m6' Makefile` → 未命中（opt-in）
- `make -n check | grep -c test-m6` → **0**
- `.PHONY` 确认含 `test-m6`

**`make test-m6` 独立重跑（EXIT=0）**：
- [1/3] check-lit-full：Total Discovered Tests: 12，PASS 12/12
- [2/3] lli value-level diff：hits 19/19 matched 19/19，diff_ir_lli: PASS
- [3/3] Embench：**19 benchmark(s) x 2 opt** (O0,O2)，PASS **38/38**，0 FAIL，live hits 38/38
- 现场统计（未写死）：src/ 下 19 基准目录（aha-mont64…xgboost），O0/O2 各 19 目录，均存在

**Embench 抽样核实**（直接 QEMU 跑已构建 ELF，不经过脚本）：
- `aha-mont64 -O0 guest_exit=0`、`aha-mont64 -O2 guest_exit=0`
- `crc32 -O0 guest_exit=0`、`crc32 -O2 guest_exit=0`
- `wikisort -O0 guest_exit=0`、`wikisort -O2 guest_exit=0`
- 3 基准 × 2 优化级抽样全 0（≥2 要求满足）

**不回归独立重跑**（逐条一次 `make`，工程师口径对齐）：

| target | rc | 通过数 | 工程师口径 | 一致 |
|---|---|---|---|---|
| `test-codegen` | 0 | 15/15 | 15/15 | ✓ |
| `test-elf` | 0 | 5/5 | 5/5 | ✓ |
| `test-semihost` | 0 | 25-svc PASS | 25-svc | ✓ |
| `check` | 0 | `repository checks: PASS` | 同 | ✓ |
| `check-lit` | 0 | 89/89 | 89/89 | ✓ |

**落点合规**：`paths.py test_artifacts_dir` → `/mnt/tao/DADAO-v5/.dadao/tests`；Embench 产物 `.dadao/tests/m6-embench/{O0,O2}/`；lli diff 产物 `.dadao/tests/ir-lli-diff/`；Makefile/run_embench_e2e.py 无 `.dadao/tests` 字面量（用 `$(TEST_ARTIFACTS_DIR)` / `paths.py`）。

**证据脚本审计 + 重跑**：
- `run.sh` 有可达 FAIL 路径：C1 grep 检查、C2 注入（python 追加 check: + c1_wiring FAIL 检测）、C3–C4 make rc 捕获、C5 目录存在性 + 字面量检查、C6 spec/ grep + residue grep
- 注入非空（python heredoc 改写文件）、`cp`+md5 还原、`rc=$?` 无 `tee`
- SKIP_GATES=1 重跑：C1/C2/C5/C6 全 PASS → **EVIDENCE: PASS**
- 完整重跑（含 C3/C4 所有门控）：**EVIDENCE: PASS / RUN_EXIT=0**

**独立注入（reviewer 自行注入→FAIL→还原→回绿）**：
- 备份 Makefile → `dc6adf1a`
- python 注入 ` test-m6` 追加至 `check:` 行 → `grep '^check:.*test-m6'` 确认
- `SKIP_GATES=1 bash run.sh` → C1 **FAIL**（`test-m6 IS in check: prerequisites`）、C2 PASS（注入→检测 FAIL→还原 md5 dc6adf1a==dc6adf1a→回绿）→ **EVIDENCE: FAIL (2 checks)**
- `cp Makefile.preinject Makefile` → md5 `dc6adf1a` == 备份 → `make -n check | grep -c test-m6` = 0 → 回绿
- `SKIP_GATES=1 bash run.sh` → **EVIDENCE: PASS / RUN_EXIT=0**

**C2 观察（非阻断）**：脚本 C2 的 `$O/Makefile.preinject` 取自执行时 Makefile 的当前状态。若在 pre-injected 状态运行 C2，restore 会回到 pre-injected 状态（而非 clean），md5 仍一致但 C1 红。正常 clean 状态下 C2 完整闭合。不影响本任务验收（脚本设计假设 clean baseline 运行）。

**约束核验**：
1. `test-m6` opt-in 不在 check 链 ✓
2. `make test-m6` EXIT=0 ✓（lit-full 12/12 + lli 19/19 + Embench 38/38）
3. 不回归 5 门控 EXIT=0 通过数不下降 ✓
4. 落点 `.dadao/tests/` 经 `paths.py` ✓
5. `spec/` 交集空 ✓
6. 证据脚本 `RUN_EXIT=0` + 独立注入 FAIL→还原→回绿 ✓
7. 无残留（`git status` 干净，无 `_tmp/_orig/_rej`）✓

**判决**：**Accepted**。全部 7 条验收标准独立验证通过，约束无违反。

#### architect 提交（2026-10-11；档位=**正常提交**，reviewer 判 Accepted）

- **提交号** `3434c58`（本任务分支 `INTEG-025t`，单条）；**文件集对账**：staged = `Makefile` + `tools/integ/run_embench_e2e.py`(新) + 本任务书，与完成区「修改文件」**逐条一致**（无漏提 / 多提 / 越界）；`md5` `Makefile=dc6adf1a`、`run_embench_e2e.py=944551eb` 与 reviewer 快照相符。
- **禁 push**（仅 `commit`）；**收尾**：`**状态**` → `已验证`；`milestones.md`（该行）+ `lessons.md §8.51` 随**落地提交**。
