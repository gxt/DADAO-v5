# INFRA-033t: issues.yaml 内容清理与校正（A–E）

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 背景

`.tao/knowledge/issues.yaml`（119 条）经 M1 归档、台账合并（`INFRA-032t`）、**M2 重定义**（2026-10-04：M2=规范与接口冻结、M3=Basic CodeGen、取消过渡任务）以及本轮 M2 任务（`SPEC-091t`~`094t`、`INTEG-009t` 等）后，**头部与若干条目已与实际状态不符**。主会话通读后列出 A–E 五类问题，用户裁定**整体作为一个清理任务**（本任务）。

## 目标与交付物

对 `.tao/knowledge/issues.yaml` 做**内容清理与校正**。**schema 不变**（`status ∈ {open,closed}`、`scope` 非空列表、`blocks` 可空列表、`closed` 必有 `resolved_by`）。

### A. 头部段（L3–13）
`M1-gate 定义` + `当前 M1 里程碑状态` 已过时——**M1 已于 2026-09-22 达成**（6/6 模块 `m` 全置），而头部仍写 `INFRA-014m`/`QEMU-021m`/`INTEG-004m 待开始`。应更新为 **M1=达成 / M2=进行中 / M3=待开始**；「M1-gate」判据改为**历史注**（或按现状重述）。§字段约束的 `scope` 值列表同步（含 `M3`；`post-M1` 明确含义）。

### B. 已消解但仍 `open` → 关闭/改写
- **`ISS-086`**（`check-spec-refs` 76 条历史违规）→ 本轮 **`SPEC-094t` 已消解（76→0）** ⇒ **`closed`**（`resolved_by: "SPEC-094t（2026-10-04）：check-spec-refs 76→0（含返工收窄 rule b/c 假阴性）"`）。
- **`ISS-004`**（「浮点以 **soft-float libcall** 接入」）→ **已否决**（用户 2026-10-03 裁定 **原生浮点**；FP 60/60 已实现）⇒ **`closed`/改写**，写明否决理由与去向。

### C. `scope: M2` 陈旧 → 校正为 M3（或相应）
M2 已重定义为「规范与接口冻结」，**非 codegen**；以下实为 **M3** 前置：`ISS-005`（ABI 完整调用约定）、`ISS-008`（重定位）、`ISS-040`（`hasFPImpl` 阻塞 codegen）、`ISS-110`（cfx 实现；cfx 属 `scope: excluded`）。逐条校正 `scope` 并说明。

### D. FP 衔接点更新
`ISS-081`：notes 需含本轮 **`INTEG-009t`**（最小 FP smoke，已验证）；余下（`GOLDEN` 独立 oracle / `TESTCASES-024t` FP 向量 / 完整 E2E）**显式归 M3**。

### E. 结构性清理（**逐条判定，可追溯**）
1. **实为「教训/过程记录」的条目 → 移入 `.tao/knowledge/lessons.md`**：`ISS-024`（validator 变更历史）、`ISS-032`（F7 守卫基线）、`ISS-035`（分层验收教训）、`ISS-055`/`ISS-066`（子代理异常事件）、`ISS-072`（`LLVM-010t` 关闭理由）——**须逐条核实**确属「记录/教训」而非「待办 issue」；移出后在 issues.yaml 删除（**id 不复用**，如实说明）或留极简指针。
2. **M1 期 `open` 项逐条判定**（close / 保留 / 归 M3）：至少含 `ISS-002`、`ISS-006`、`ISS-007`、`ISS-009`、`ISS-010`、`ISS-017`、`ISS-018`、`ISS-019`、`ISS-020`、`ISS-021`、`ISS-022`、`ISS-025`、`ISS-026`、`ISS-027`、`ISS-028`、`ISS-029`、`ISS-031`、`ISS-060`、`ISS-061`、`ISS-062`、`ISS-063`、`ISS-070`、`ISS-071`、`ISS-073`、`ISS-074`。**判据**：已被后续任务消解 / M1 已达成故 M1 最小覆盖项可关 / 仍有效则保留或改归 M3。**每条须给实测依据**（`grep`/`git log`/读文件），不得凭印象。

## 约束

- **schema 不变**；`closed` 必有 `resolved_by`；`open` 则 `resolved_by: null`。
- **不改已 `closed` 的历史条目正文**（除 B 明确指出者）；**不臆造**：所有判定须有证据。
- 只动 `.tao/knowledge/issues.yaml`（+ E-1 的 `.tao/knowledge/lessons.md`）；**不改** `contracts/`、`spec/`、`tools/`、`tests/`、`.tao/archive/**`、历史任务书。
- 临时目录 `/tmp/opencode/INFRA-033t/`；**不提交 git**；失败即停、禁自动重试。
- 完成区与真实输出逐条对齐；复杂命令输出留存 `.work/log/infra/INFRA-033t-<命令名>.log`。

## 验收标准

1. A–E 全部处置；**逐条判定表**（id → 动作〔closed / scope 校正 / 移出 lessons / 保留〕+ 依据）可追溯，供 reviewer 抽查。
2. `python3 tools/infra/check_issues.py` **EXIT=0**；条目计数前后差异如实说明。
3. E-1 移出的条目**在 `lessons.md` 可定位**；issues.yaml 中不再作为 issue（或留指针）。
4. `make check` **EXIT=0**。
5. **一键证据脚本**（`.work/evidence/INFRA-033t/`）：非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + 退出码」；内置「注入反例→预期 FAIL→还原→回绿」自检；结尾不得 `tee` 吞退出码。

## 风险

- **E-2 逐条判定易漏/误判**（M1 期 open 项多）→ 完成区逐条给依据 + reviewer 抽查「随机抽 5 条追依据」。
- **移出条目改变 id 连续性** → 如实说明，**id 不复用**。
- **B/C/D 属事实性校正** → 须与 `milestones.md`/`SPEC-090k`/本轮 M2 任务成书一致。

## 完成区

**测试结果**：通过。`python3 tools/infra/check_issues.py` **EXIT=0**；一键证据脚本 `.work/evidence/INFRA-033t/run.sh` **默认 31/31 PASS / EXIT=0**、注入反例 **rc=1（6 项 FAIL）**、还原+重跑 **31/31 / EXIT=0**；`make check` **EXIT=0**（lit 31/31、`repository checks: PASS`）。失败原因：无。

**修改文件**：
- `.tao/knowledge/issues.yaml`（唯一内容变更源文件；A–E 全部处置）
- `.tao/knowledge/lessons.md`（E-1：新增 §1.2/§3.2/§3.3/§5.4/§5.5/§6.5，承接 6 条移出条目）
- `.work/evidence/INFRA-033t/{run.sh,check_issues_checks.py}`（任务专用一键证据脚本，gitignored）
- 日志：`.work/log/infra/INFRA-033t-{evidence,make_check}.log`
- 本任务书（状态 + 完成区）
- **未触碰** `contracts/`、`spec/`、`tools/`、`tests/`、`.tao/archive/**`、历史任务书。`git status` 仅上列 2 个受版控文件 + 本任务书（untracked）。

**验收结果（真实命令/输出）**：

1) **A 头部校正**（`.tao/knowledge/issues.yaml` L3–30）：头部改为
   `M1 = ✅ 达成（2026-09-22，用户确认；6/6 模块 m 全置：SPEC-011m/TESTCASES-012m/INFRA-014m/LLVM-015m/QEMU-021m/INTEG-004m）`、
   `M2 = 进行中（规范与接口冻结，2026-10-04 重定义；原 Basic CodeGen 顺延 M3）`、`M3 = 待开始（Basic CodeGen）`；
   `M1-gate` 定义改为**历史注**（门控已随 M1 达成退役，`check_issues.py` 保留字段检查）；
   §字段约束 `scope` 值列表**补入 `M3`**，并明确 `M1/M2/M3` 与 `post-M1` 含义。
   依据：`milestones.md`（M1 ✅ 达成 / M2 重定义注）、`.tao/archive/M1/README.md` L24（M1 达成 2026-09-22，6/6 `m`）、`SPEC-090k`。

2) **B 关闭**：
   - `ISS-086` → `closed`，`resolved_by: "SPEC-094t（2026-10-04）：check-spec-refs 76→0（含返工收窄 rule b/c 假阴性）"`。依据：`SPEC-094t` 任务状态 `已验证`、完成区「Check1/Check2=0、EXIT=0、总引用 680」。
   - `ISS-004` → `closed` 且 title 改写为「路线已由用户 2026-10-03 裁定为原生浮点，soft-float libcall 方案被否决」，`resolved_by` 记否决理由与去向。依据：`SPEC-086t` §裁定「原生浮点（全工具链）；否决 soft-float libcall」、`SPEC-087t`；FP 60/60（`QEMU-034t~037t`）。

3) **C 校正 `scope: M2 → M3`**（4 条）：`ISS-005`（完整调用约定）、`ISS-008`（重定位）、`ISS-040`（`hasFPImpl` 阻塞 codegen）、`ISS-110`（cfx 实现，`scope: excluded`）；各补 `notes` 说明。依据：`SPEC-090k`（M2=规范与接口冻结）。
   > 说明：`ISS-042` 亦含 `scope: [llvm, M2]`，但已 `closed`（历史条目）——按约束「不改已 closed 条目正文」**保留不动**。

4) **D 更新 `ISS-081`**：`notes` 补入 **`INTEG-009t`（最小 FP E2E smoke，2026-10-04 已验证）**，并写明余下 4 项（`GOLDEN` 独立 oracle / harness RF 支持 / `TESTCASES-024t` FP 向量 / 完整 FP E2E）**显式归 M3**；`scope` 追加 `M3`。依据：`INTEG-009t` 任务状态 `已验证`、E2E 4/4。

5) **E-1 移出 6 条至 `lessons.md`**（`id` 不复用）：
   | id | 移入位置 | 判定 |
   |----|----------|------|
   | `ISS-024` | `lessons.md §5.4` | 审计记录（validator 变更历史） |
   | `ISS-032` | `lessons.md §5.5` | 基线记录（F7 守卫基线） |
   | `ISS-035` | `lessons.md §1.2` | 教训（工具/数据分层验收） |
   | `ISS-055` | `lessons.md §3.2` | 过程记录（子代理空返回事件） |
   | `ISS-066` | `lessons.md §3.3` | 过程记录（子代理异常汇总） |
   | `ISS-072` | `lessons.md §6.5` | 关闭记录（`llvm-objcopy` 可选项已落实） |
   `issues.yaml` 内已删除这 6 条，头部加迁移说明（id 不复用）。`grep` 实测 6 个 id 在 `issues.yaml` 均 0 命中、在 `lessons.md` 均命中（证据脚本 `E1_moved[*]`）。

6) **E-2 逐条判定表**（供 reviewer 抽查；依据均为实测）：

   | id | 动作 | 依据（实测） |
   |----|------|--------------|
   | `ISS-002` | **closed** | `contract-isa.md`/`contracts/opcodes.yaml` 已重排重生成（SPEC-016t/018t 2026-09-28、SPEC-019t 2026-09-28；opcodes 227 条） |
   | `ISS-006` | **scope M1→M3** | `contract-abi.md` L191–195 仍 5 项 `[OPEN]`（grep `[OPEN]`） |
   | `ISS-007` | **closed** | e_flags=`0x1`（ADR-0003 + LLVM-014t 2026-09-22）；EM_DADAO 未注册已文档化（contract-elf.md §1.3）；M1 无 link 步骤 |
   | `ISS-009` | **closed** | `docs/impact-matrix.md` L3/L27 明确「实现目标标签（仅 M1）」by design |
   | `ISS-010` | **closed** | `scope` 分区（SPEC-086t）+ `check_scope.py` 断言 `scope!=m1 ⇔ decode:ILLI`；legality_rules scope-aware |
   | `ISS-017` | **closed** | `tests/vectors/schema.md` L40–72 + `tests/vectors/isa/reserved.yaml` 存在（TESTCASES-008t 2026-09-16） |
   | `ISS-018` | **closed** | `schema.md` L167+「encoding 类对恒 fault 指令的豁免（F6）」（TESTCASES-002t，commit 1e3903b） |
   | `ISS-019` | **scope→[golden, M3]** | milestones.md 划 FP 独立 oracle / 完整语义 E2E 归 M3 |
   | `ISS-020` | **closed** | `validate_vectors.py` L730–754 数据级门控（`DATA COVERAGE GAP`→`exit(1)`） |
   | `ISS-021` | **closed** | M1 期并行前提；M1 达成、003t~007t 收敛、`validate_vectors` 机械校核 inventory |
   | `ISS-022` | **closed** | `tests/vectors/isa/` 15 个 yaml；M1 152/152、gap 0 |
   | `ISS-025` | **保留 open** | 结构性守卫仍缺（`grep taken/not-taken tools/testcases/validate_vectors.py` 仅错误文案，无守卫） |
   | `ISS-026` | **scope 追加 M3** | imm 语义由 golden model 守卫（golden 归 M3） |
   | `ISS-027` | **closed** | 题面自述「属 M1 最小覆盖」；M1 达成、mem-rd 22 项 boundary |
   | `ISS-028` | **closed** | `ctrl-br.yaml` 10 项 boundary（无 legality，br 不 fault）；009t 兜底 |
   | `ISS-029` | **closed** | `validate_vectors.py` L222–292 消费 `encoding.reserved` |
   | `ISS-031` | **closed** | `ctrl-call.yaml` C3a shift-push、`ctrl-ret.yaml` D2/D3/D4b 多级/MemRAS |
   | `ISS-060` | **closed** | `reg-imm-block.yaml` 含 `rd2ra_orri_ra`/`ra2rd_orri_ra`（encoding/semantic/legality/overlap） |
   | `ISS-061` | **closed** | TB 续接缺陷由 QEMU-022t（2026-09-21）根治；语义 149/149 |
   | `ISS-062` | **closed** | QEMU-022t 后 `--dump` rb/pc 正确 |
   | `ISS-063` | **closed** | 补丁 0008（QEMU-022t，2026-09-21）已在补丁集 |
   | `ISS-070` | **closed** | 实测 `len(TESTS)=121`、`unique=121`；`git show` 证 dedup 于 LLVM-022t（commit 9a7ea95，68→61） |
   | `ISS-071` | **closed** | fence 已 `scope: excluded`（ADR-0014/SPEC-039t）；excluded 无 M1 lit 要求（cfx/LR-SC 同） |
   | `ISS-073` | **closed** | `check_lit_bytes.py` 有 `--lit-dir`（L61–65）/`--min-obj`（L66–71、L137–141）；`git show 9a7ea95` 提交说明含之 |
   | `ISS-074` | **scope M1→M3** | `reg-cond-assign.yaml` 5 条 `deferred_reason: C-27` + `expected_state: null` 仍在（未消解） |

7) **条目计数**：
   - 改前：`check_issues: 100 open, 19 closed`（total 119；`main` 基线）。
   - 改后：`check_issues: 72 open, 41 closed`（total 113）。
   - 差异：total **−6**（E-1 移出 6 条）；closed **+22**（B 2 + E-2 20）；open **−6**（移出）−22（关闭）= **−28**。

8) **一键证据脚本**（`.work/evidence/INFRA-033t/run.sh`，完整输出见 `.work/log/infra/INFRA-033t-evidence.log`）：
   - 非交互；逐项打印「检查名 + 期望/实际 + 退出码」；无 `tee`。
   - **默认运行**：`SUMMARY: pass=31 fail=0` / `default_run_exit=0`。
   - **反例自检**：向**真实文件**注入（`ISS-086` 改回 open+清空 `resolved_by`；`lessons.md` 中 `ISS-024`→`ISS-024-REMOVED`）→ `SUMMARY: pass=25 fail=6` / `injected_run_exit=1`（`B_ISS086`、3×`A_header`、`count_open/closed` FAIL）。
   - **还原→回绿**：`restore_sha_match | sha_equal` → `SUMMARY: pass=31 fail=0` / `restored_run_exit=0`（`trap` 保证异常也还原）。
   - **`make check`**：`make_check_exit=0` / `RESULT: PASS`。

9) **`make check`**（`.work/log/infra/INFRA-033t-make_check.log`）：`lit 31/31 Passed`、`check_issues: 72 open, 41 closed`、`repository checks: PASS`、`make_check_exit=0`。

**新发现/坑**：
1. **`issues.yaml` 头部未随里程碑同步**：M1 于 2026-09-22 达成、`milestones.md` 全置，但头部仍写 `INFRA-014m/QEMU-021m/INTEG-004m 待开始`——`INFRA-032t` 合并台账时未校正（本任务补）。教训：里程碑状态变化时须同步 `issues.yaml` 头部。
2. **`resolved_by` 归属必须用 `git log -S` 实证**：初判 `ISS-070/073` 归 `LLVM-029t`/`LLVM-012t 后续`，`git show 9a7ea95` 证实实际由 **LLVM-022t**（oracle 去重 68→61；`check_lit_bytes --lit-dir/--min-obj`）落地——不得凭印象填 `resolved_by`。
3. **`make check` 已含 `check-issues`**：`repository checks` 输出 `72 open, 41 closed`，故状态变更会体现在 `make check` 输出中。
4. **注入须改真实文件 + `trap` 还原 + sha 核对**：`yaml.safe_dump` 重写会丢注释（仅用于临时注入态），还原以 `cp` 备份 + sha256 相等为准。
5. **closed `ISS-042` 保留 `scope: [llvm, M2]`** 系约束「不改 closed 历史条目正文」所致（非疏漏）；如需统一另立任务。

**遗留问题**：
- 无未完成项；A–E 全部处置。
- 范围外（建议主会话/后续任务）：closed `ISS-042` 的 `scope: M2` 历史值未动（约束所限）。
- `git status` 除本任务 2 个受版控文件 + 本任务书外无残留；**未提交 git**。

## 审阅记录
（reviewer 填）

### 第 1 轮 engineer 自审

**审查范围**：`.tao/knowledge/issues.yaml`（全文件 diff）、`.tao/knowledge/lessons.md`（全文件 diff）、`.work/evidence/INFRA-033t/{run.sh,check_issues_checks.py}`（全文件）。

**逐行审查发现**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `ISS-070` 初判 `resolved_by` 归 `LLVM-029t` 不实 | ✅已修 | 改为 `LLVM-022t（2026-09-29，oracle 去重 68→61）` | `git show 9a7ea95` 提交说明「oracle 去重 68->61」；`git log -L`/逐版本实测 68/61→61/61 |
| F2 `ISS-073` 初判 `resolved_by` 归「LLVM-012t 后续」不实 | ✅已修 | 改为 `LLVM-022t（... check_lit_bytes 加 --lit-dir/--min-obj）` | `git show 9a7ea95` 提交说明；脚本 L61–71/L137–141 实测存在 |
| F3 `ISS-060` 的 `resolved_by` 初版列 `TESTCASES-016t/020t` 无据 | ✅已修 | 改为「TESTCASES 侧已覆盖（reg-imm-block.yaml ...；TESTCASES-003t 起）」，`notes` 列实测用例 | `git show f710968:tests/vectors/isa/reg-imm-block.yaml` 证 003t 起已有 rd2ra encoding/semantic；现行 4 类用例 |
| F4 证据脚本注入若改真实文件可能残留 | ✅已核 | `cp` 备份 + `trap restore EXIT INT TERM` + sha256 相等核对 | `restore_sha_match | sha_equal`；`git diff` 仅 2 文件 |
| F5 每项判定须有实测依据 | ✅已核 | E-2 全部 25 条均附 `grep`/读文件/`git log` 依据（完成区表） | 见完成区 E-2 表；`make check` 绿 |
| F6 `scope: [M2]` 是否全部清除 | ✅已核 | 4 条按 C 校正；closed `ISS-042` 依约束保留 | Python 实测：仅 `ISS-042`(closed) 含 M2；open 无 M1/M2 |
| F7 schema 不变量 | ✅已核 | 仅补 `notes`（既有字段），未增删字段 | 证据脚本 `schema_valid=none`；checker 全绿 |
| F8 closed 历史条目未被动 | ✅已核 | 仅 B 明确指出的 `ISS-004/086` 被改 | `git diff` 逐条核对，其余 closed 条目零改动 |

**自审判决**：F1–F3 已修并复验；F4–F8 已核；无未决项。逻辑/边界/防造假/惯用法/范围均通过 ⇒ 状态置 `待验收`。

### 第 2 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查时间**：2026-10-04
**审查范围**：`.tao/knowledge/issues.yaml`（全文）、`.tao/knowledge/lessons.md`（§1.2/§3.2/§3.3/§5.4/§5.5/§6.5）、`.work/evidence/INFRA-033t/{run.sh,check_issues_checks.py}`（全文）。

#### 重跑记录

**1) `check_issues.py` 独立重跑**
```
$ python3 tools/infra/check_issues.py
check_issues: 72 open, 41 closed (0 blocking M1-gate: 0)
EXIT=0
```

**2) 证据脚本独立重跑**（`bash .work/evidence/INFRA-033t/run.sh`）
```
=== 1. default run ===
SUMMARY: pass=31 fail=0
default_run_exit=0

=== 2. inject counterexample ===
injection_effective: both changed
B_ISS086: FAIL (open+False)
A_header[M1/M2/M3]: FAIL (MISSING — yaml.safe_dump drops comments)
count_open: FAIL (73≠72)
count_closed: FAIL (40≠41)
SUMMARY: pass=25 fail=6
injected_run_exit=1

=== 3. restore + re-run ===
restore_sha_match: sha_equal
SUMMARY: pass=31 fail=0
restored_run_exit=0

=== 4. make check ===
Passed: 31 (100.00%)
check_issues: 72 open, 41 closed
repository checks: PASS
make_check_exit=0

RESULT: PASS (OVERALL_EXIT=0)
```

**3) 独立 `make check`**
```
$ make check
Passed: 31 (100.00%)
check_issues: 72 open, 41 closed (0 blocking M1-gate: 0)
repository checks: PASS
MAKE_CHECK_EXIT=0
```

#### 独立反例注入与还原

- **注入**：`python3` 改 `ISS-086` status→open、resolved_by→None（yaml.safe_dump）
- **注入有效**：`yaml.safe_load` 确认 ISS-086 status=open
- **检测结果**：25/31 PASS、6 FAIL（B_ISS086 + 3×A_header + count_open/closed）、exit=1
- **还原**：`cp` 备份还原
- **SHA 核对**：issues.yaml `f0e5024…` == backup `f0e5024…` ✓；lessons.md `1f4ae24…` == backup `1f4ae24…` ✓
- **还原后回绿**：31/31 PASS、exit=0
- **`git status`**：仅 `issues.yaml` + `lessons.md` 受版控修改，无残留

> 注：注入后 A_header 3 项 FAIL 是因为 `yaml.safe_dump` 重写丢弃 YAML 注释（头部在 comment 中），属于脚本已知行为，非产品缺陷。注入真正要验证的 B_ISS086 + count 检测均正确触发。

#### 约束核验

| 约束 | 结果 |
|------|------|
| 只动 `issues.yaml` + `lessons.md` | ✅ `git diff --name-only` 仅 2 文件 |
| 未触碰禁改区（contracts/spec/tools/tests/.tao/archive） | ✅ |
| 不提交 git | ✅ |
| schema 不变（status/scope/blocks/resolved_by） | ✅ schema_valid=none |
| closed 均有 resolved_by | ✅ check_issues 未报错 |
| 条目计数 119→113（-6 = E-1 移出） | ✅ total=113、open=72、closed=41 |

#### 逐项核验

| # | 核验项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | A 头部：M1=达成/M2=进行中/M3=待开始；M1-gate 历史注；scope 含 M3、post-M1 | ✅ | L3-23 逐行确认 |
| 2 | B ISS-004：closed、title 改写、resolved_by 含「原生浮点」 | ✅ | L52-58 |
| 3 | B ISS-086：closed、resolved_by 指向 SPEC-094t | ✅ | L585-591 |
| 4 | C ISS-005/008/040/110：scope 含 M3、不含 M2 | ✅ | 证据脚本 C_scope_M3 全 PASS |
| 5 | D ISS-081：notes 含 INTEG-009t、scope 含 M3、余归 M3 | ✅ | L548-554 + 证据脚本 D 检查 |
| 6 | E-1 6 条移出：issues.yaml 中 0 命中、lessons.md 中可定位 | ✅ | grep 逐条确认；§1.2/§3.2/§3.3/§5.4/§5.5/§6.5 |
| 7 | E-2 抽查 7 条（ISS-002/006/009/020/025/070/074） | ✅ | git show 9a7ea95、grep impact-matrix.md、grep validate_vectors.py、grep reg-cond-assign.yaml |
| 8 | 证据脚本 FAIL 路径存在、非恒真 | ✅ | 注入后 6 FAIL；31 个检查均有 FAIL 条件 |
| 9 | 证据脚本注入可还原 | ✅ | trap + cp + sha256 |
| 10 | `make check` exit=0 | ✅ | 31/31 lit、72/41、PASS |

#### 披露项

- **M2 状态不一致**：`milestones.md` L8 表格 M2=待开始 vs `issues.yaml` 头部 M2=进行中。`milestones.md` L13 注说明 M2 已重定义，但表格未同步。本任务未动 `milestones.md`，此不一致属范围外。

#### 判决

**Accepted**。

验收命令块（`check_issues.py`、证据脚本、`make check`）在独立重跑下全部通过（EXIT=0）；约束无违反；反例注入→FAIL→还原→回绿完整闭环；逐项核验 A–E 全部确认。工程师产出达标。

#### 架构师交叉复核（第 2 轮，双模型互验）

**复核者**：architect（deepseek-flash）
**复核时间**：2026-10-04
**复核目的**：对照任务书目标/约束/验收，独立核验 reviewer（mimo-v2.5-pro）判决有无遗漏关键项、约束违反、过严/过松。
**硬约束遵守**：临时目录 `/tmp/opencode/INFRA-033t-xcheck/`；**未改被复核产物**（`issues.yaml` sha `f0e5024…`、`lessons.md` sha `1f4ae24…` 复核前后一致）；**未提交 git**。

##### 独立核验（真实命令 + 输出）

**1) A 头部**（`.tao/knowledge/issues.yaml` L3–23）——✅
- L4 `M1 = ✅ 达成（2026-09-22…6/6 模块 m 全置）`；L7 `M2 = 进行中（规范与接口冻结…）`；L9 `M3 = 待开始（Basic CodeGen）`。
- L11–15 `M1-gate 定义（历史注）`，注明门控随 M1 达成退役、仅保留字段检查。
- L19 `scope` 值列表含 `M3`；L21 明确 `post-M1` 含义。

**2) B 事实性**——✅
- `ISS-086`：`status=closed`、`resolved_by` 含 `SPEC-094t`；`SPEC-094t` 任务书 `**状态**：已验证`；独立实跑 `check-spec-refs` 得 `结果: PASS (0 violations)`（Check1=0、Check2=0）。
- `ISS-004`：`status=closed`、title 改写为「路线已由用户 2026-10-03 裁定为原生浮点，soft-float libcall 方案被否决」，依据来自 `SPEC-086t` L16「**路线**：原生浮点指令（全工具链）；**否决** soft-float libcall」；`SPEC-087t` 存在、`QEMU-034t~038t` 均 `已验证`。

**3) C scope→M3**——✅（4 条，非 5）
- 实测 `ISS-005/008` `scope=['M3']`；`ISS-040/110` `scope=['llvm','M3']`——均含 `M3`、不含 `M2`。

**4) D `ISS-081`**——✅
- `scope=['spec','golden','testcases','llvm','qemu','integ','M3']`；`notes` 含 `INTEG-009t`；`INTEG-009t` 任务书 `**状态**：已验证`。余下 4 项显式归 M3 已写明。

**5) E-1 移出 6 条**——✅
- `ISS-024/032/035/055/066/072` 在 `issues.yaml` 均 0 命中、在 `lessons.md` 均命中（§1.2/§3.2/§3.3/§5.4/§5.5/§6.5 逐条含来源注）。base vs 现行 diff 显示这 6 条为**删除**、**无新增 id** ⇒ id 不复用。

**6) E-2 逐条依据（独立抽查 8 条，非抽样）**——✅
| id | 判定 | 独立实测 |
|----|------|---------|
| `ISS-002` | closed | `contracts/opcodes.yaml` `len=227`；`SPEC-016t/018t`（8fe4976）、`SPEC-019t`（0847713）提交在案 |
| `ISS-006` | scope M1→M3 | `grep '\[OPEN\]' contract-abi.md` = §6 汇总 5 项（L191–195）仍在 |
| `ISS-009` | closed | `docs/impact-matrix.md` L17「实现目标标签（仅 M1）」by design |
| `ISS-020` | closed | `validate_vectors.py` L743 `DATA COVERAGE GAP`（数据级门控）在 |
| `ISS-025` | 保留 open | `grep taken/not-taken validate_vectors.py` 仅命中错误文案（L387–388），**无结构性守卫** |
| `ISS-060` | closed | `reg-imm-block.yaml` 含 `rd2ra_orri_ra`/`ra2rd_orri_ra`（encoding/semantic/legality×/overlap） |
| `ISS-070` | closed | 实跑 `len(TESTS)=121`、`unique=121`；`git show 9a7ea95` 提交说明「oracle 去重 68->61」 |
| `ISS-073` | closed | `check_lit_bytes.py` `--lit-dir`（L62）/`--min-obj`（L67、L140）在；同属 9a7ea95 |
| `ISS-074` | scope M1→M3 | `reg-cond-assign.yaml` 实测 `class=overlap`+`deferred_reason: C-27`+`expected_state: null` **5 条**（cs.n/z/p/eq/ne）仍在 |
- 另核：baseline（HEAD）open 且 scope 含 `M1` 的项 = `ISS-002/006/007/009/010/074`，**全部在 E-2 覆盖内**，无遗漏。

**7) 门控**——✅
- `python3 tools/infra/check_issues.py` → `check_issues: 72 open, 41 closed (0 blocking M1-gate: 0)`、`EXIT=0`。
- 独立 `make check` → `Total Discovered Tests: 31 / Passed: 31 (100.00%)`、`repository checks: PASS`、`MAKE_CHECK_EXIT=0`。

**8) 证据脚本独立重跑 + 独立注入**——✅
- 重跑 `.work/evidence/INFRA-033t/run.sh`：默认 `SUMMARY: pass=31 fail=0 / default_run_exit=0`；注入态 `pass=25 fail=6 / injected_run_exit=1`；还原 `restore_sha_match`、`SUMMARY: pass=31 fail=0`；`make_check_exit=0`；`RESULT: PASS (OVERALL_EXIT=0)`。
- **独立注入**（与 engineer 不同点，由架构师自行选择）：`sed` 改 `ISS-005` `scope: [M3]→[M2]`（`git diff --name-only` 确认改动生效）→ 重跑**同一脚本** `check_issues_checks.py` 得 `[FAIL] C_scope_M3[ISS-005]`、`SUMMARY: pass=30 fail=1`、`RESTORED_RC=1`；`cp` 还原后 sha 与改前一致 → 重跑 `SUMMARY: pass=31 fail=0`、`RESTORED_RC=0`。证伪闭环成立。

**9) diff 范围审计**——✅
- `git diff --name-only` 仅 `issues.yaml` + `lessons.md`（+ 本任务书 untracked）；未触碰 `contracts/`、`spec/`、`tools/`、`tests/`、`.tao/archive/**`。
- base→现行：删除 6（E-1）、关闭 22（B 2 + E-2 20）、scope 变更 9（C 4 + E-2 4 + D 1）；**逐字段比对确认无任何「改前已 closed」的历史条目被改动**，符合约束。

##### 披露项处置建议（`milestones.md` M2 行 vs `issues.yaml` 头部）

- 事实：`milestones.md` L8 M2 行（含 `状态` 列）仍为 `待开始`；`issues.yaml` L7 头部为 `M2 = 进行中`。
- 判定：**属范围外**（本任务约束仅许动 `issues.yaml` + `lessons.md`，reviewer 已披露，处置正确）。两者并非硬矛盾——`milestones.md` 的 `状态` 列按架构师规则只有 `待开始/达成` 两态（由依赖模块里程碑是否 `里程碑` 决定），M2 模块里程碑尚未置，故列 `待开始` 合规；`issues.yaml` 的「进行中」是工作进展叙述，属另一维度。
- 建议（择一，交后续任务/主会话）：
  1. **推荐**：在 `milestones.md` M2 重定义注（L13）处补一句，说明表列 `状态` 为正式两态、工作进度见 `issues.yaml` 头部/`MEMORY.md`；不动表格单元。
  2. 纳入 `milestones.md` L15「归档前置 MUST」的台账梳理（M2 收敛/归档时自然同步）。
  3. 归属：新增 infra/spec 文档小任务，或在 M2 归档前置梳理任务中一并处置；**不在本任务范围**。

##### 交叉复核判决

**确认 Accepted（与 reviewer 一致）**。A–E 全部处置正确；独立抽查 8 条 E-2 判定均有真实依据、无误关/凭印象；门控 `check_issues.py`/`make check` EXIT=0；证据脚本可失败性经**架构师独立注入**证伪；diff 范围合规、未改已 closed 历史条目。披露项 `milestones.md` M2 行不一致属范围外，处置建议如上。

> 补充说明（非缺陷）：本次下发提示将 E-2 概括为「closed 20 + scope 校正 5 + 保留 1」，经 base→现行逐字段实测，E-2 实为 **closed 20 + scope 校正 4（`ISS-006/019/026/074`）+ 保留 1（`ISS-025`）= 25**；C 段另有 4 条（`ISS-005/008/040/110`）。任务书 E-2 判定表与实测一致，无缺漏。
