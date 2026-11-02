# SPEC-160t: `ftmin`/`fomin`/`ftmax`/`fomax` 解除 `excluded`（`scope → fp`，族 `minmax`）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-159t`（记录已立）、`QEMU-071t`（trans 已落）、`LLVM-124t`（`.td` 已落）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么必须等三册

- `scope: fp` 记录必须有 `.td`（`validate_instrinfo.py` 的 coverage 覆盖 `fp`）⇒ 等 `LLVM-124t`；
- `check_qemu_trans --strict` 属 **L2**，缺 trans 时翻转会让 L2 红 ⇒ 等 `QEMU-071t`；
- 两者到位后本册**不制造任何新红**（与 `SPEC-155t`/`SPEC-158t` 同一纪律）。

### 现场事实（2026-10-21 核，执行前须复核）

- `check_fp_contract.py`：现场 **13 族 / 60 条**；本册新增 **`minmax`: 4** ⇒ **14 族 / 64 条**（FMA 链另加 `fma`:2 ⇒ 15 族 / 66 条，本册不含）；
- `EXPECTED_TOTAL` 常量与 `check_scope.py` 的 `fp` 计数均需同步；
- `contracts/fp_semantics.yaml` 只收 `scope == "fp"`；每条需 `family`、`spec_cite`（`^SimRISC-0[0-7]`）、`semantics_ref = contract-fp.md#<anchor>`、`legality_refs`；
- `contract-fp.md` 的 `minmax` 段与 `<a id="minmax">` 由 `SPEC-159t` 提供。

## 目标

1. 4 条由 `excluded` 转 **`fp`**（删 `decode: ILLI`），`dst_rf0` 仍生效；
2. 新增族 `minmax`（4 条），`fp` 计数 +4；
3. 生成物/计数/只读锁同步。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/check_fp_contract.py`、`tools/spec/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_isa_coverage.py`、`spec/SimRISC-07`（追加 1 行）、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（`fp` +4）、`fp_semantics.yaml`（+4 条 `family: minmax`）、`check_fp_contract` 族表/计数、`check_scope` 计数与 changelog、速查/合法性/矩阵/`contract-asm-list` 重生成、只读锁。
- **约束**：只改 4 条记录与本册必需的计数/族表；其它记录逐字节不变；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 族与契约

- `fp_semantics.yaml` 每条：`family: minmax`、`spec_cite: "SimRISC-07 §最小最大值"`（以实际章节名为准）、`semantics_ref: "contract-fp.md#minmax"`、`legality_refs: [dst_rf0]`；
- `check_fp_contract.py`：`FAMILY_COUNTS["minmax"] = 4`、`EXPECTED_TOTAL` = 现场派生（**64**）、族集合断言同步；
- 锚点可达性由 `check_fp_contract` 校验（`contract-fp.md` 须含 `<a id="minmax">`）。

### B. 计数与生成物（逐项现场跑）

`generate_opcodes` → `check_scope` → `validate-encoding` → `check-rule-refs` → `check_fp_contract` → `gen_asm_list --embed-spec/--drift` → `gen_legality_list --apply` → `gen_isa_coverage` → `contract-asm-list` → `SimRISC-07` 变更记录 1 行 → 只读锁。

## 验收标准

1. `fp` 计数 = 现场派生（+4）；`excluded` 相应 −4；`total` 不变；`fp_semantics.yaml` 含 4 条 `family: minmax`。
2. `check_scope` / `check_fp_contract`（**14 族**）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo` / `check-isa-coverage` 全绿。
3. `check_qemu_trans --strict` 全绿（`QEMU-071t` 已落）。
4. `check-spec-*` / `check-asm-list*` 全绿；`git diff --stat` 显示非本 4 条记录零改动。
5. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
6. **可达 FAIL ≥ 2**：① 漏加 `minmax` 族 ⇒ `check-fp-contract` 红；② 不重算只读锁 ⇒ 红。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（族表、计数、锚点）。
2. 生成器 `scope="fp"` + 族映射 → 重生成 → 门控。
3. 计数/族表/变更记录/只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 不改 `check_fp_contract` 的族表 ⇒ 红；还原 ⇒ 绿。
- 不更新只读锁 ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露**）

- 不实现（已由 `QEMU-071t`/`LLVM-124t` 完成）；不做测试（`TESTCASES-059t`）。
- 不清理其它 `excluded` 记录。

## 完成区

**测试结果**：一键证据 `bash .work/evidence/SPEC-160t/run.sh --inject` = **146/146 PASS（rc=0）**（`=== Summary: PASS=146 FAIL=0 ===`；含 L1 `make check` rc=0，日志 `.work/evidence/SPEC-160t/log/L1_make_check.log`）。L2 `make check-modules` **rc=0**（`module checks (L2): PASS`，日志同目录 `L2_make_check_modules.engineer.log`，末行 `RC=0`）。注入 3 例均「注入→红→`cp`+md5 还原→回绿」：① `EXPECTED_TOTAL` 回 60 ⇒ `check-fp-contract` rc=1（id 计数 60≠64）；② `fomax` scope 回 `excluded` ⇒ `check-fp-contract` rc=1（`fp_semantics 多出 fomax_orrr_rf`）+ `check-scope` rc=1（fp 64→63）；③ 删 `FAMILY_COUNTS["minmax"]` ⇒ `check-fp-contract` rc=1（非法族/families 段族集合）。
**修改文件**：`tools/spec/generate_opcodes.py`（4 条 `scope: fp` + 头部/docstring 计数）；`contracts/opcodes.yaml`（重生成：仅 4 条 scope/decode/rule_refs + 头部计数，其余 260 条逐字段相同）；`contracts/fp_semantics.yaml`（`minmax` 族 + 4 条、count 64）；`contracts/legality_rules.yaml`（`dst_rf0` 35→39 + minmax 明细）；`tools/spec/check_fp_contract.py`（`EXPECTED_TOTAL=64`、`FAMILY_COUNTS["minmax"]=4`、`FP_RULE_EXACT["dst_rf0"]=39`、14 族）；`tools/spec/check_scope.py`（fp 64 / excluded 27 + changelog）；生成物 `.tao/contracts/contract-asm-list.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`；`.tao/contracts/contract-fp.md`（64 条/§14/§15 39 条/minmax 族/§18–§19 范围）；`spec/SimRISC-00-指令系统设计.md`、`spec/SimRISC-07-浮点运算.md`（生成区 + 册头/总账计数 + 范围注 + 附录 1 行）；`manifests/spec-readonly.lock.toml`（00/07 sha256 + 注记）；`.tao/knowledge/milestones.md`（1 行）、本任务书。**越界披露（2 处，均非本册输入清单）**：`spec/SimRISC-00` 3 hunk 与 `contract-fp.md` 的计数/范围订正——任务书 §接口规范只列 `spec/SimRISC-07`；但 4 条翻转后 00 §4/§4.6 与 contract-fp §14/§15 的「60 条 / 46+4 excluded / 35 条」必假，且生成区（§1.1/§2）由 `--embed-spec`/`gen_legality_list --apply` 机械重写 ⇒ 不改则 `check-asm-list`/`check-legality-drift` 红；语义正文未改，只改现行陈述数字/范围（同 `SPEC-162t` 先例）。§4.4 语义条款（六边界）逐字未动。
**验收结果**：现场 `total 264 / fp 64 / excluded 27 / m1 156 / m3 1 / m8 7 / m9 9`；`check_fp_contract` PASS（**14 族 / 64 条**、`minmax: 4`、`dst_rf0` 39、锚点 + 双源一致）；`check_qemu_trans --strict` **264/264**；`check_lit_gen` 64/64（positives/negatives 集合不变——4 条早有 `.td`，原即正例）；`check_isa_coverage --check` accept 262/reject 2；`check_scope`/`check_instrinfo`/`validate-encoding`（264）/`check-rule-refs`（16 规则/341 引用）/`check_tables`/`check-spec-codeblocks`/`check-asm-list{,-drift}`/`check-legality-{drift,invariants}`/`gen_legality_list --verify`/`check-spec-{refs,drift,numbering,changelog,archive,readonly}`/`check-contracts-pending`/`check-milestones-fresh`/`check_issues` 全 rc=0。零改动面（独立脚本对基线 `a869e75f`）：`same=260 flipped=4 other_changed=0 bad=0`。
**新发现/坑**：① 任务书 §可达 FAIL ②「不重算只读锁 ⇒ 红」不适用于本册前提（本册必须改 spec 生成区 ⇒ 锁必重算），改用 3 例（计数/scope 回退/族表）；② 族表与 `FP_RULE_EXACT["dst_rf0"]` 均为写死条数，增 FP 记录须同步（本册 35→39）——`FAMILY_COUNTS`/`dst_rf0` 宜在 M9 收尾改为现场派生；③ 同工作树出现 3 个**非本册**并发改动（`adr-0035-clmul.md`、`issues.yaml`、`docs/Process-07`，内容为 ADR 修订/issues 清理/计数同步时点注记），已在证据 `external-changed.txt` 登记并从「本册改动集」剔除，未认领、未修改。
**遗留问题**：无未完成项（不实现 = `QEMU-071t`/`LLVM-124t` 已落；不做测试 = `TESTCASES-059t`）。低优建议：`check_fp_contract.py` 的 `FAMILY_COUNTS`/`FP_RULE_EXACT` 写死计数与 `gen_asm_list.py` 注释示例，宜随 M9 收尾统一派生。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：15 个改动文件 + 生成器/门控逻辑 + 证据脚本（含 3 例注入的可达 FAIL 路径与还原对账）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `contract-fp.md §18` 仍写「计入 `scope: fp` 60 条」（§18 是 roundint 的现行范围陈述，翻转后必假） | ✅已修 | 60 → 64 | `check_fp_contract` rc=0；证据 E 段「contract-fp 64 条」PASS |
| F2 证据 I1 断言「覆盖（fp_semantics 多）=4」不可达：该注入只改 `EXPECTED_TOTAL`，覆盖用的是 opcodes 侧 fp 集合 ⇒ 实际只红「id 计数」 | ✅已修 | I1 断言改为命中 `check-fp-contract: FAILED` 汇总（id 计数行另行断言） | `--inject` 146/146 PASS（I1 两条全绿） |
| F3 `milestones.md` 行改 22:40 触发 A4 逆序 + 与任务书状态不一致（L1 红） | ✅已修 | 时间回退为登记时间 `2026-10-21 23:50（登记）`、状态 `待验收`，任务书同步 `待验收` | `check-milestones-fresh` PASS（52 行）；L1 rc=0 |
| F4 证据 A0 直接比 `git diff --name-only master`，混入 3 个并发外部改动 ⇒ 误判 18≠15 | ✅已修 | 新增 `external-changed.txt`（逐项登记）+ `comm` 派生本册集合，另断言外部集不触及本册产出面 | A0 两条 PASS；`actual-mine.txt` = 15 项 |
| F5 `fp_semantics.yaml` 头部「来源」列表缺 `§最小最大值` | ✅已修 | 补该章节引用 | YAML 解析 + `check_fp_contract` rc=0 |
| F6 证据脚本用 `make check-tables`（Makefile 无该目标，ISS-325 已知） | ✅已修 | 改为直跑 `python3 tools/spec/check_tables.py` | `--inject` 全跑中 `check_tables` rc=0 |

审查确认（无 finding）：① 4 条记录 `op/ha/mask/value/format/legality/fields/spec_cite` 逐字节不变，仅 `scope/decode/rule_refs` 变动（独立脚本对基线统计）；② `generate_opcodes` / `gen_asm_list{,-embed-spec}` / `generate_lit_vectors` 重跑幂等（md5 不变），`gen_legality_list --verify` rc=0；③ 只读锁 00/07 sha256 由独立脚本重算命中，未用 `git checkout/restore/stash/show` 还原；④ 注入前均断言 `git diff --name-only` 非空（防「空注入」假绿），还原 md5 对账。

### 第 1 轮 reviewer 验收（独立重跑，判决基于本人输出/退出码）

**计数**：`check_scope` rc=0 → `total 264 / fp 64 / excluded 27 / m1 156 / m3 1 / m8 7 / m9 9`；`check_fp_contract` rc=0 → `id 计数 64`、`family ∈ 14 族`、`族计数 minmax: 4`、`dst_rf0: 39`。（与完成区逐条一致）

**4 条记录**：独立 yaml 读 `ftmin/ftmax/fomin/fomax` 均 `scope: fp`、`decode` ABSENT、`rule_refs ['dst_rf0']`、`legality ['rfhb != rf0']`。其余 260 条逐字段 diff（对基线 `a869e75f=fdf895d4~1`）：`same=260 flipped=4 other_changed=0 bad=0`。

**语义未变**：`check_qemu_trans --strict` rc=0 → `264/264`；`make check-lit` rc=0 → `131/131`；`check_lit_gen` rc=0 → `64 passed, 0 failed`。

**生成物一致性**：`make check-asm-list{,-drift,-prose}`、`make check-legality-{drift,invariants}`、`check_tables`、`gen_legality_list --verify` 均 rc=0；只读锁独立重算 `SimRISC-00/07 sha256 MATCH 2/2`。

**门控**：L1 `make check` 本人重跑 rc=0（`repository checks (L1): PASS`）；L2 `make check-modules` 本人后台重跑 rc=0（`module checks (L2): PASS` / `L2_EXIT=0`，非仅采信日志）。

**独立注入（本人，cp+md5 还原，禁 git checkout）**：① `fomax` scope→`excluded` ⇒ `check_fp_contract` rc=1（`fp_semantics 多出 fomax_orrr_rf`）+ `check_scope` rc=1（`fp 64→63`）；`cp`+md5 还原（`0c014d4f…` 命中）⇒ 双绿 rc=0。② `EXPECTED_TOTAL` 64→60 ⇒ rc=1（`id 计数 60≠64`）；还原（`b035dcdc…` 命中）⇒ rc=0。两次注入前后 `git status` 均 0 行（干净）。

**spec 语义正文**：逐段 diff `SimRISC-00`/`SimRISC-07` — 仅计数陈述（60→64/46→50/32→36）、scope 状态句、生成区（速查/合法性）、变更记录 1 行、`§4.4` 末「范围」注；`§4.4` 语义条款（六边界/目的 rf0/源可 rf0 等）逐字未动。**未改语义正文**。

**证据脚本审读**：`run.sh` 无 `tee`；`gate/expect_fail` 直取 `rc=$?` 落盘日志（非管道吞码）；还原仅 `cp`+md5（`git show` 命中仅第 7 行禁令注释）；断言均「期望常量 vs 真实输出」，无恒真/两支同果；注入含非空断言 + 可达 FAIL。

**约束核验**：范围限 4 条记录 + 必需计数/族表 ✓；其余逐字节不变 ✓；不改判定语义 ✓；越界 2 处（`SimRISC-00` 3 hunk、`contract-fp.md` 计数/范围）已披露且仅计数/范围陈述、门控必需，非语义正文 — 记 finding，不阻断。

**判决：Accepted**（阻断项：代码行为/门控退出码/断言计数/语义 均无违反；本人重跑全绿，L1/L2 均本人重跑 rc=0）。
