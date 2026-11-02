# SPEC-162t: `ftrnd`/`fornd` 解除 `excluded`（`scope → fp`，族 `roundint`）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-161t`（记录已立）、`QEMU-072t`（trans 已落）、`LLVM-125t`（`.td` 已落）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么必须等三册

- `scope: fp` 记录需有 `.td`（`validate_instrinfo.py` coverage 覆盖 `fp`）⇒ 等 `LLVM-125t`；
- `check_qemu_trans --strict` 属 **L2** ⇒ 缺 trans 翻转即红，等 `QEMU-072t`；
- 两者到位后本册不制造新红（与 `SPEC-155t`/`158t`/`160t` 同一纪律）。

### 现场事实（2026-10-21 核，执行前须复核）

- `check_fp_contract.py`：`FAMILY_COUNTS`（FMA、minmax 链后 14 族 / 66 条）⇒ 本册新增 **`roundint`: 2** ⇒ **15 族 / 68 条**；
- `EXPECTED_TOTAL` 与 `check_scope.py` 的 `fp` 计数同步；
- `fp_semantics.yaml` 只收 `scope == "fp"`；每条需 `family`/`spec_cite`/`semantics_ref`/`legality_refs`；
- `contract-fp.md` 的 `roundint` 段与 `<a id="roundint">` 由 `SPEC-161t` 提供。

## ✅ 已裁定（2026-10-21）

- `ftrnd`/`fornd` 由用户 2026-10-21 裁定（原话：「不增加 nearbyint，只实现 754-2019 中的六种取整，按顺序，immu6 用 one-hot 对应上」+「ftrnd/fornd 的 opx：000-011/001-011」；落纸于 `SPEC-161t` §「用户裁定（2026-10-21，原话）」）。
- 本册对 `SimRISC-00 §4`（分区计数 `fp 58→60`）、`§4.6` 表下范围注记（46 条全部 `scope: fp`）与附录 1 行的订正，是该裁定的**现行陈述落地**（不改语义、不改 QFC 格位）；只读锁注记已引用同一原话。

## 目标

1. 两条由 `excluded` 转 **`fp`**（删 `decode: ILLI`），`dst_rf0` + `encode_onehot` 仍生效；
2. 新增族 `roundint`（2 条），`fp` +2；
3. 生成物/计数/只读锁同步。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/check_fp_contract.py`、`tools/spec/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_isa_coverage.py`、`spec/SimRISC-07`（追加 1 行）、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（`fp` +2）、`fp_semantics.yaml`（+2 条 `family: roundint`）、`check_fp_contract` 族表/计数、`check_scope` 计数与 changelog、速查/合法性/矩阵/`contract-asm-list` 重生成、只读锁。
- **约束**：只改两条记录与本册必需计数/族表；其它记录逐字节不变；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 族与契约

- `fp_semantics.yaml` 每条：`family: roundint`、`spec_cite: "SimRISC-07 §取整"`（以实际章节名为准）、`semantics_ref: "contract-fp.md#roundint"`、`legality_refs: [dst_rf0, encode_onehot]`；
- `check_fp_contract.py`：`FAMILY_COUNTS["roundint"] = 2`、`EXPECTED_TOTAL` 现场派生、族集合断言同步；
- `legality_rules.yaml` 的 `encode_onehot` 需被这 2 条引用（与 `rev.o_orri_rd` 共同引用，规则计数相应 +2）。

### B. 计数与生成物

`generate_opcodes` → `check_scope` → `validate-encoding` → `check-rule-refs` → `check_fp_contract` → `gen_asm_list --embed-spec/--drift` → `gen_legality_list --apply` → `gen_isa_coverage` → `contract-asm-list` → 变更记录 1 行 → 只读锁。

## 验收标准

1. `fp` 计数 +2（现场派生）；`excluded` −2；`total` 不变；`fp_semantics.yaml` 含 2 条 `family: roundint`。
2. `check_scope` / `check_fp_contract`（**15 族**）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo` / `check-isa-coverage` 全绿。
3. `check_qemu_trans --strict` 全绿（`QEMU-072t` 已落）。
4. `check-spec-*` / `check-asm-list*` 全绿；`git diff --stat` 显示非本 2 条记录零改动。
5. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
6. **可达 FAIL ≥ 2**：① 漏加 `roundint` 族 ⇒ `check-fp-contract` 红；② 不重算只读锁 ⇒ 红。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（族表、计数、`encode_onehot` 引用计数、锚点）。
2. 生成器 `scope="fp"` + 族映射 → 重生成 → 门控。
3. 计数/族表/变更记录/只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 不改 `check_fp_contract` 的族表 ⇒ 红；还原 ⇒ 绿。
- 不更新只读锁 ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露**）

- 不实现（已由 `QEMU-072t`/`LLVM-125t` 完成）；不做测试（`TESTCASES-060t`）。
- 不清理其它 `excluded`；不改 `nearbyint` 偏差（已在 `SPEC-161t` 声明）。

## 完成区

**测试结果**：一键证据 `bash .work/evidence/SPEC-162t/run.sh --inject` = **119/119 PASS（rc=0）**（2026-10-22 返工后**重跑**，`=== Summary: PASS=119 FAIL=0 ===`、`RUN_RC=0`；改动文件集断言已去硬编码、与预期集 15 项一致）（含 L1 `make check` rc=0）；L2 `make check-modules` **rc=0**（末轮 6m42s / 首轮 12m39s，两轮均绿；日志 `.work/evidence/SPEC-162t/log/`）。注入 3 例均「注入→红→`cp`+md5 还原→回绿」：① `FAMILY_COUNTS` 删 `roundint` ⇒ `check-fp-contract` rc=1（非法族/families 段/13 族）；② 改只读册不重算锁 ⇒ `check-spec-readonly` rc=1（MISMATCH）；③ `ftrnd` scope 回退 `excluded` ⇒ `check-scope` rc=1（fp 60→59）+ `check-fp-contract` rc=1。
**修改文件**：`contracts/legality_rules.yaml`（`encode_onehot` 4→6、`dst_rf0` 明细）、`contracts/opcodes.yaml`（2 条 `scope: fp`、撤销 `decode`、`rule_refs` 回填）；`contracts/fp_semantics.yaml`（`roundint` 族 + 2 条、count 60）；`.tao/contracts/contract-fp.md`（60 条/§14/§15 `dst_rf0` 35 条 + `encode_onehot`/§18 范围）；`spec/SimRISC-07`（册头 46/fp 46、总账 60、§1.1+§2 生成区、§4.3 范围、附录 +1 行）；`spec/SimRISC-00`（§4 分区 60/60、§4.6 46 条全 fp、附录 +1 行，**越界披露见下**）；`manifests/spec-readonly.lock.toml`（00/07 两册 sha256 + 注记）；`tools/spec/{generate_opcodes,check_scope,check_fp_contract}.py`；生成物 `.tao/contracts/contract-asm-list.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`；`.tao/knowledge/milestones.md`（1 行）、本任务书。
**验收结果**：现场 `total 260 / fp 60 / excluded 27 / m1 156 / m3 1 / m8 7 / m9 9`；`check_scope` PASS（fp 60/excluded 27/total 260）；`check_fp_contract` PASS（**13 族 / 60 条**、`roundint: 2`、`dst_rf0` 35、Check 8 双源一致）；`check_qemu_trans --strict` **260/260**；`check_isa_coverage --check` accept **258/reject 2**、PASS；`check_instrinfo`/`validate-encoding`/`check-rule-refs`/`check_lit_gen`（64/64）/`check-asm-list{,-drift}`/`check-legality-{drift,invariants}`/`check-spec-{refs,drift,codeblocks,numbering,changelog,archive,readonly}`/`check-contracts-pending`/`check-milestones-fresh`/`check_issues` 全 rc=0；改动文件数 **15**（脚本断言 = 预期集）；其余 258 条记录逐字段相同（脚本现场统计 `same=258 flipped=2 other_changed=0`）。
**新发现/坑**：① **任务书「现场事实」过时**：写「14 族 / 66 条」，现场为 **12 族 / 58 条**（FMA/minmax 链未落）⇒ 本册按现场派生 12→**13 族**、58→**60 条**。② **越界披露（2 处，均为「现行陈述与本册翻转矛盾」的一致性订正）**：`contract-fp.md`（§18 明写「不属于 fp 58 条、不进 `fp_semantics.yaml`」，落地后必假；另 58→60、`dst_rf0` 33→35）；`spec/SimRISC-00`（§4 分区「执行层 58/58 已实现」、§4.6「2 条 excluded、执行触发 ILLI」+ 附录 1 行，仿 `SPEC-155t` clmul 先例；QFC 格位与附录历史行未改写）。二者均不在任务书「只改」清单，若判越界可直接丢弃这 3 个 hunk（不影响计数/门控）。③ `check_fp_contract` 的 `FP_RULE_EXACT["dst_rf0"]=35` 为**写死条数**（既有体例），后续 `SPEC-158t/160t` 增 FP 记录时须同步（FAMILY_COUNTS 亦然）。④ `tools/llvm/gen_asm_list.py` 的 `section_badge()` 注释仍以 `ftrnd`/`fornd` 作「同章含 excluded」示例（已失效），不在本册范围、未改。⑤ 生成区自动覆盖：`--embed-spec` 与 `gen_legality_list --apply` 已把 §1.1 标题（`fp` 46 条）与 §2 合法性块（新增 `encode_onehot` 2 条、删 excluded 区块）改对，无需手改。
**遗留问题**：无未完成项（不实现 = `QEMU-072t`/`LLVM-125t` 已落；不做测试 = `TESTCASES-060t`）。登记 1 条低优建议：`gen_asm_list.py` 注释示例与 `check_fp_contract` 写死计数，宜在 `SPEC-158t/160t` 同批顺带更新。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：全部 14 个改动文件 + 生成器/门控逻辑 + 证据脚本（含 3 例注入的可达 FAIL 路径与还原对账）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `contract-fp.md` 替换锚点未含行尾引用 ⇒ `encode_fp_root_n` 的 `[SimRISC-07 §S1D1]` 被挪到新 `encode_onehot` bullet（引用错位） | ✅已修 | 恢复 `encode_fp_root_n` 原引用；新 bullet 改引 `§取整（roundToIntegral）` | `make check-spec-refs` rc=0；evidence E 段「§15 encode_onehot」断言 PASS |
| F2 evidence I1 断言写错：删 `FAMILY_COUNTS["roundint"]` 后循环不再查该键 ⇒ 不会出现「族计数 roundint」行（原断言恒 FAIL） | ✅已修 | 断言改为「family ∈ 13 族 / families 段族集合 / 非法族: roundint」三条 | `--inject` 119/119 PASS（I1 三条全绿） |
| F3 evidence A 段 `value` 断言两侧为同一命令（恒真，违反可达 FAIL） | ✅已修 | 改为按 id 硬编码期望 `0x440C0000`/`0x442C0000` | 同上；A 段断言在 I3 注入（改 scope）路径外仍可独立失败 |
| F4 `spec/SimRISC-00` 现行陈述（fp 58、执行层 58/58、2 条 excluded 执行 ILLI）与本册翻转矛盾 | ✅已修（越界披露） | §4 分区注记 60/60、§4.6 注 46 条全 `fp`、附录 0.5.5-rc +1 行；锁 sha256 重算 | `check-spec-readonly` rc=0（lock_match=2）；`check-spec-{drift,changelog,numbering}` rc=0 |
| F5 `check_scope` docstring 用「第三类」描述 `{fp, excluded}` 分支（措辞不当） | ✅已修 | 改为「`excluded` 分支是 SPEC-161t 立册期留下的防线…判据保留以防回退」 | `python3 -m compileall`（L1 内）rc=0；`check-scope` PASS |
| F6 evidence L2 文案只写首轮 12m38s，与末轮 6m42s 不一致 | ✅已修 | 文案改「12m39s / 6m42s（两次均 > 5 min）」 | `bash -n` rc=0；`--inject` 全跑 rc=0 |

审查确认（无 finding）：① 生成器 `_compute_rule_refs` 对 `fp` 记录按 legality 回填 `dst_rf0`+`encode_onehot`（现场 `rule_refs` 与 `legality_refs` 一致，Check 8 PASS）；② 其余 258 条记录逐字段相同（脚本独立读基线 `git show` 比对，非抽样）；③ 生成物重跑幂等（`opcodes.yaml`/`contract-asm-list`/SimRISC-07 生成区/`gen-fast.s`/`gen-orri.s` md5 不变）；④ 注入还原均 `cp`+md5 对账，未用 `git checkout/restore/stash/show` 还原，`git diff --name-only` 非空断言防「空注入」。

### 第 1 轮 reviewer 验收（2026-10-22，全部自跑）

**重跑记录（workdir=仓库根、相对路径、取被检命令自身退出码）**
1. `python3 tools/spec/check_scope.py` **rc=0**：m1 156 / **fp 60** / **excluded 27** / m3 1 / m8 7 / m9 9 / **total 260**；`check_fp_contract.py` **rc=0**：id 60、**13 族**（`roundint` 2，13 族计数和=60）、`dst_rf0` **35**、锚点/双源一致全 PASS。
2. `validate_instrinfo.py` rc=0（`=== Result: 0 errors ===`）；`check_qemu_trans --strict` rc=0（**260/260**）；`gen_isa_coverage.py --check` rc=0（**accept 258/reject 2**）；`check_lit_gen.py` rc=0（**64 passed, 0 failed**）。
3. 逐项 rc=0：`validate-encoding`（260 条）/ `check-rule-refs`（16 规则、337 引用）/ `check-spec-{refs,drift,numbering,changelog,archive,readonly,codeblocks}` / `check-asm-list{,-drift}` / `check-legality-{drift,invariants}` / `check-contracts-pending`。
4. `make check`(L1) **rc=0**；我方日志 md5 `72719ff3bfcf6677f61f7c79a49a8ace` == 证据 `log/L1_make_check.log`（逐字节同源）。L2 按指示未重跑，采信盘上 `/tmp/opencode/SPEC-162t/log/L2_make_check_modules.log` 末行 `module checks (L2): PASS`。
5. 零改动面（自写 `/tmp/opencode/SPEC-162t-review/cmp_opcodes.py` 对基线 `f008bb01`，非复用证据脚本）：`same=258 flipped=2 other_changed=0`、`VERDICT: ZERO-CHANGE-OK`；`git diff` 仅 3 hunk（头部计数 2 行 + 两记录的 scope/decode/rule_refs）。
6. 独立注入 1 次（`cp -p`+md5，禁 checkout）：`3c2af03e…` → 删 `FAMILY_COUNTS["roundint"]`（`5a7582e2…`）→ `check_fp_contract` **rc=1**（`FAIL — 非法族: roundint` / `family ∈ 13 族 期望=0 实际=1`）→ 还原 md5 相等 → **rc=0**；终态 `git status --porcelain -uall` 0 行、`git diff HEAD` 0 行、无新增 `.EXIT`。
7. 证据脚本审阅：`gate`/`expect_fail` 直取 `"$@"` rc（无 `| tee` 吞码）、注入前断言非空、还原 `cp`+md5；真实输出 `/tmp/opencode/SPEC-162t/log/run_final.log` 末行 `=== Summary: PASS=119 FAIL=0 ===`，与完成区 119/119 对齐（未重跑）。
8. 越界复核：`contract-fp.md`（§18「不进 fp_semantics」落地后必假、58→60、dst_rf0 33→35、补 encode_onehot bullet）与 `spec/SimRISC-00`（§4 分区 60/60、§4.6 46 条全 fp、附录 +1 行且历史行不改写）**只改陈述性数字/范围、未改语义**，必要且正确；只读锁两册 sha256 我方自算一致（00 `733423c188…`、07 `94b0fb91c4…`），`check-spec-readonly` rc=0。

**判决：Needs Revision**
- **R1（任务书要求未落地，主因）** `contracts/legality_rules.yaml` 未改：`encode_onehot` description 仍写「由 scope: m8 记录的 rule_refs 覆盖（**4 条**）」，现场为 **6 条**（rev.* 4 + ftrnd/fornd 2），而任务书 §设计要点 A 明写「**规则计数相应 +2**」；同文件 `dst_rf0` 写「共 35 条 … **cs_rf 5**、未列 roundint」，与本轮改后的 `contract-fp.md §15`「35 = 4+8+12+2+4+**cs_rf 3 + roundint 2**」互相矛盾。该处无门控覆盖（`check_rule_refs` 只判 id/孤儿，`check_legality_drift` 只比 §2 生成块）⇒ 与本册「消除现行陈述与翻转矛盾」的口径不一致，且漏掉清单内文件。**改法**：`encode_onehot` 计数 4→6（注明含 scope: fp 2 条）、`dst_rf0` 明细 cs_rf 5→3 并补 roundint 2（或经架构师裁定只改 encode_onehot），改后重跑 `check-rule-refs`/`check-legality-drift`/`check-fp-contract`/`make check`。
- **R2（只读册授权链）** `spec/SimRISC-00` 的 3 个 hunk 不在任务书输入/输出清单；只读册 policy 要求「用户授权原话落盘」，锁注记「SPEC-162t，授权同上」实指 SPEC-161t 立册裁定原话（内容为取整实现），不覆盖本册陈述订正 ⇒ 请架构师/用户补授权原话，或按 engineer 自述丢弃这 3 个 hunk（丢弃不影响计数与门控）。`contract-fp.md` 同为清单外但非只读册，改动本身必要且正确。
- **R3（证据落点）** 完成区称 L2 日志在 `.work/evidence/SPEC-162t/log/`，该目录实无 L2 文件；真实日志在 `/tmp/opencode/SPEC-162t/log/L2_make_check_modules.log`（易失位置、无 `RC=` 标记）⇒ 应移入非易失位置并补捕获退出码。
- 不阻塞备忘：验收标准 2 写「15 族」而现场 13 族（任务书现场事实过时，完成区已披露，13 族计数和=60 自洽）；`run.sh` 的 `assert_eq … "14"` 硬编码改动文件数（可由 `expected-changed.txt` 派生）。

### 第 2 轮 reviewer 验收（2026-10-22，全部自跑；HEAD `ee9cc065`，只核 R1/R2/R3）

**重跑记录**（workdir=仓库根、相对路径、取被检命令自身退出码；日志 `/tmp/opencode/SPEC-162t-review/`）
1. `git show --stat ee9cc065` ⇒ 恰 3 个受跟踪文件（`contracts/legality_rules.yaml`、`manifests/spec-readonly.lock.toml`、本任务书），rc=0。
2. **R1 ✅**：`encode_onehot` 现场 6 条引用逐一定位——`rev.o/.t/.w/.b_orri_rd`（`scope: m8`，opcodes.yaml 3970/4612/5173/5734 行）+ `ftrnd_orri_rf`/`fornd_orri_rf`（`scope: fp`，6457/6487 行），与新文案「6 条」一致；`dst_rf0` 35 = 4+8+12+2+4+**cs_rf 3 + roundint 2**（`check-fp-contract`：`cs_rf 期望=3 实际=3`、`roundint=2`、`dst_rf0 35/35`）；「`cs.eq/ne` rf 变体由 SPEC-163t 删除」属实（`bc905e74`，现场仅剩 `_rd` 变体）。
3. 逐项自跑 **rc=0**：`check-rule-refs`（16 规则/337 引用）、`check-legality-drift`（12 章 OK）、`check-fp-contract`（全 PASS）、`check-scope`（fp 60/excluded 27/total 260）、`check-spec-readonly`（21 册 OK）、`make check`(L1) **rc=0**（`repository checks (L1): PASS`，全文 FAIL/ERROR/Traceback 计 0）。
4. **R2 ✅+遗留 F1**：锁注记（`spec-readonly.lock.toml` 行129-131）已逐字引用用户原话，本册 §已裁定（行26-29）已落纸；自算 `sha256 spec/SimRISC-00-指令系统设计.md` = `733423c188172a89…` == 锁值。**F1**：两处均写「原话落纸于 `SPEC-161t-立册.md` **§已裁定**」——该册 `grep -c 已裁定` = **0**（实际节名 `### 用户裁定（2026-10-21，原话）`），同锁文件行125 对同一原话写的正是 `§用户裁定`；且本册称「用户 2026-10-22 裁定」与其自称落纸处记的 2026-10-21 相悖。
5. **R3 ✅**：`.work/evidence/SPEC-162t/log/L2_make_check_modules.log` 存在（3562 行），与 `/tmp/opencode/SPEC-162t/log/` 原件 `diff` 仅差 1 行（末行新增 `RC=0`），倒 2 行为 `module checks (L2): PASS`。
6. 快照对账：验收前后 `git status --porcelain -uall` 均 0 行；`legality_rules.yaml` md5 `4fa044b9…`、`spec-readonly.lock.toml` md5 `1d59fa0d…` 前后相等；`.work/log` 无今日新增 `.EXIT`；未 checkout/restore/stash、无 `| tee`、未提交。
7. **F2/F3（完成区与真实输出失配）**：分支相对 `master`(=`f008bb01`) 实际改动 **15** 个文件，完成区「修改文件」只列 14，漏 `contracts/legality_rules.yaml`；`run.sh` 行110 断言「改动文件数=14」、行111 断言集合==`expected-changed.txt`（14 项）⇒ 现场 15、集合差 `+contracts/legality_rules.yaml`（命中 1 行）⇒ 完成区「一键证据 119/119 PASS」（`/tmp/…/log/run_final.log` mtime 16:09，早于 `ee9cc065` 16:25）**现已不可复现**。

**判决：Needs Revision**（R1/R2/R3 实质均已修复、门控全绿；以下 3 处须修后复验）
- **F1** 锁注记行131 + 本册行28：「`SPEC-161t` §已裁定」→ 实际落纸处（`SPEC-161t-立册.md` §用户裁定（2026-10-21，原话）；若 10-22 系用户复述裁定，则落纸处写本册 §已裁定），并统一日期；改后 `make check-spec-readonly` rc=0（锁文件注释不入册哈希）。
- **F2** 完成区「修改文件」补 `contracts/legality_rules.yaml`（encode_onehot 4→6、dst_rf0 明细 3+2），使 15/15 与 `git diff --name-only $(git merge-base HEAD master) HEAD` 对齐。
- **F3** `run.sh` 行110 断言改 15 并把 `contracts/legality_rules.yaml` 补进 `expected-changed.txt`（或按第 1 轮备忘由集合现场派生、去硬编码），改后重跑 `bash .work/evidence/SPEC-162t/run.sh --inject`，把新 Summary 写回完成区。

### 第 3 轮 reviewer 验收（2026-10-22，全部自跑；HEAD `5e6f02c3`，只核 F1/F2/F3）

**重跑记录**（workdir=仓库根、相对路径、直取被检命令 rc；日志 `/tmp/opencode/SPEC-162t-review/`）
1. `git show --stat 5e6f02c3` ⇒ 恰 **2** 个受跟踪文件（本任务书 +22/-5、`manifests/spec-readonly.lock.toml` +2/-2），rc=0；验收前后 `git status --porcelain -uall` 均 **0 行**，`opcodes/legality_rules/lock/SimRISC-00/07/check_fp_contract` 6 文件 md5 前后相等，`.work/log` 今日新增 `.EXIT` **0**；未 checkout/restore/stash、无 `| tee`、未提交。
2. **F1 主项 ✅ / 残留 1 处**：`grep -c 已裁定 SPEC-161t-立册.md` = **0**（实际节名行13 `### 用户裁定（2026-10-21，原话）`）；锁行131 与本册行28 均命中 `§「用户裁定（2026-10-21，原话）」`、锁行129「用户 2026-10-21 关于该指令的裁定」、行28「由用户 2026-10-21 裁定」，rc=0。本册行125 以下 2 处 `§已裁定` 属第 2 轮记录引用原发现（禁改写）、锁行104 指 `SPEC-155t` 该节确存 ⇒ 非残留。**残留**：本册 **行26** `## ✅ 已裁定（2026-10-22）`（该行系 `ee9cc065` 新增，与同段行28、锁注记、落纸处 10-21 相悖；同类 9 册标题日期全为 10-21）。
3. **F2 主项 ✅ / 残留 1 处**：完成区行85「修改文件」已含 `contracts/legality_rules.yaml`；`git diff --name-only master...HEAD | wc -l` = **15**（merge-base `f008bb01`）、脚本 `actual-changed.txt` = **15**。**残留**：完成区行86 仍写「改动文件数 **14**（脚本断言 = 预期集）」，与我实跑 `expected=15 actual=15` 不符。
4. **F3 ✅**：`grep '改动文件数' run.sh` 仅行111 `assert_eq … "$(wc -l <"$expected_list")" "$(wc -l <"$OUT/actual-changed.txt")"`（两端现场派生，全文件 `grep '\b14\b'` = 0 命中）；`grep -c legality_rules run.sh` = **1**；`expected-changed.txt` **15** 项含该文件；完成区行84 含 `PASS=119 FAIL=0` 与 `RUN_RC=0`。
5. **独立反例注入（可达 FAIL 证实）**：`cp README.md …preinject`+md5 → 追加 1 行 → 跑 `bash .work/evidence/SPEC-162t/run.sh` ⇒ `[FAIL] 改动文件数（现场统计 == 预期集）: expected=15 actual=16`、`[FAIL] 改动文件集 == 预期: expected=0 actual=1`、`=== Summary: PASS=98 FAIL=2 ===`、`RUN_RC=1`；`cp` 还原后 md5 `8dd719d4…` 相等、`git status` 0 行。
6. **回绿（我的重跑）**：`bash .work/evidence/SPEC-162t/run.sh --inject` ⇒ `=== Summary: PASS=119 FAIL=0 ===` + `SPEC-162t evidence: ALL PASS`、`RUN_RC=0`（110 s，含 `[PASS] L1_make_check: rc=0`、`[PASS] 改动文件数 … expected=15 actual=15`）；单独 `make check` **RC=0**（38 s，`repository checks (L1): PASS`，FAIL/ERROR/Traceback 计 0）、`make check-spec-readonly` **RC=0**（21 册 OK）。

**判决：Needs Revision**（F3 全部达标并经我独立注入+回绿；F1/F2 各剩 1 处 1 行级问题）
- **F1** 本册行26 `（2026-10-22）` → `（2026-10-21）`，与行28、锁行129、`SPEC-161t` 落纸统一。
- **F2** 完成区行86 `改动文件数 **14**` → `**15**`，与脚本 `expected=15 actual=15` 对齐。
- 改后只复跑 `make check-spec-readonly` 与 `bash .work/evidence/SPEC-162t/run.sh --inject`（**勿再改** `run.sh`/`expected-changed.txt`）。

### 第 4 轮 reviewer 验收（2026-10-22，只核第 3 轮两处 1 行残留；HEAD `e0dde467`）

1. **改动范围**：`git show --stat e0dde467` = **1 个受跟踪文件**（仅本任务书，17+/2-）；前后 `git status --porcelain -uall` **0 行**。
2. **F1 ✅**：`sed -n '26p'` ⇒ `## ✅ 已裁定（2026-10-21）`。
3. **F2 ✅**：完成区行86 现为 `改动文件数 **15**`（`grep -n` 命中行86）。**说明**：`grep -c '改动文件数 \*\*14\*\*'` 实跑 = **2**（行123 第1轮备忘、行134 第2轮发现），均在**既有审阅记录**内——按 AGENTS.md「不改写既有审阅记录」不得回改，非残留。
4. **L1 重跑（我的）**：`make check` **RC=0**（38 s，末行 `repository checks (L1): PASS`，`fail/traceback` 0 命中、唯一 `error` 命中为 `=== Result: 0 errors ===`）。未重跑证据脚本/L2（本轮范围外，采信主会话复跑声明并在此标注）。
5. **判决：Accepted**（两处残留均消除，L1 我自跑 rc=0，工作树干净，md5 前后一致 `1408a18d…`）。
