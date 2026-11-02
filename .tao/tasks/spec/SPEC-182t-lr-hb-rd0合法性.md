# SPEC-182t: lr 的 hb(rdHB)≠rd0 合法性契约补齐（F1）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-181t`（已验证，F1 以「需用户裁定」登记）、`GEM5-002t`（已验证，矩阵 12 条 lr 行 `exceptions` 已写 `hb != rd0 ⇒ ILLI`）
**状态**：待验收

## 执行环境
**执行环境**：本地

## 用户授权

> 用户 2026-11-02 原话（经主会话转达）：「先补 F1 `lr.hb != rd0 ⇒ ILLI` 契约，再继续 B6。」

覆盖：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tools/spec/generate_opcodes.py`、`contract-isa.md` 正文。**派生**改动（`spec/SimRISC-12` 附录 B 生成区 + 只读锁 sha256）另见 §未决 1，派单前须主会话确认。

## 背景与现状（现场核对）

- 规范早已规定：`spec/SimRISC-12-其它指令.md` §1.1（L12）「lr 指令的 hb（rdHB）固定为 rd0…若手工编码时 hb ≠ 0，触发 ILLI 异常」。
- 契约缺口：`contracts/opcodes.yaml` 12 条 `lr.*`（`lr.{o,t,w,b}.{nn,an,ar}`）的 `legality: []`、`rule_refs: []`；`.tao/contracts/contract-isa.md §14.2` 写「`lr` 的 `rdHB` 固定为 rd0（编码约束，见 `encode_sbz`）」，但该指向**当前不可定位**（`encode_sbz` 的生成列表无任何 lr）。
- 字段现状：`rdhb[17:12] role=dst bank=rd`、`rdhc[11:6] role=src`、`rbhd[5:0] role=src`；**真实数据目的是 `rdhc`**，`rdhb` 是固定零的 SBZ 位域（`ADR-0034 D5`）。`role=dst` 来自 `f_orrr` 的位域默认值，不表示写回。
- 实现侧已按规范执行（**非 oracle，仅判影响面**）：QEMU `target/dadao/translate.c.patch` 注释/代码 `hb (rdHB) must be rd0 => ILLI`；`tests/inst/atomics/atomics-lrsc.yaml` 已有 `rdHB = rd2 != rd0 -> ILLI` 用例（`tools/qemu/generate_atomics_vectors.py` 生成）。故本任务只补契约/生成物，**不动实现、不动向量**。

## 目标（范围）

1. **机器可读合法性（核心）**：12 条 `lr.*` 的 `legality` 增 `rdhb == rd0`，`rule_refs` 增 `encode_sbz`。
   - 方向：`opcodes.yaml` 的 `legality` 是「必须成立的条件」（对照 `sc` 的 `rdhb != rd0`）；`lr` 要求该域为零 ⇒ `rdhb == rd0`，违反即 ILLI。
   - 规则复用：不新增 rule id；`encode_sbz`（`fault: ILLI` / `kind: static` / `status: active`）已覆盖「固定 0 位域非零」。
2. **生成器同步**：`tools/spec/generate_opcodes.py::build_misc_amo` 中 lr 分支 `leg` 由 `[]` 改为 `["rdhb == rd0"]`；`EXPR_TO_RULE` 的 SBZ 组增 `("rdhb == rd0", "encode_sbz")`（未映射表达式会 `RuntimeError`）。随后**重生成** `contracts/opcodes.yaml`，不手改生成物。
3. **规则正文（role/取名取舍落地）**：`contracts/legality_rules.yaml` 两条 description：
   - `encode_sbz`：`lr` 条改为「`lr` 的 `hb`（`rdhb`）是 SBZ 固定零字段（数据目的为 `rdhc`），手工编码 `hb != rd0` ⇒ ILLI」；删过期句「LR-SC 属 M1 范围外，M1 不提取其语义」（现 `scope: m9` 已实现）。
   - `dst_rd0`：把「`lr` 的 `rdhb` …不是目的字段、不触发本规则」改写为「`rdhb` 的 `role: dst` 是 `orrr` 位域默认分类，**不表示写回**；`lr` 的数据目的是 `rdhc`，`rdhb` 由 `encode_sbz` 承接、不触发本规则」。
4. **人读契约**：`.tao/contracts/contract-isa.md §14.2` 合法性 bullet 改为「`lr` 的 `hb(rdHB)` 为 SBZ 固定零字段，`hb != rd0` ⇒ ILLI（`encode_sbz`，12 条）；数据目的为 `rdHC`」，保留 `[SimRISC-12 §LR-SC指令]` 引用。
5. **生成区（派生，禁手改）**：`python3 tools/spec/gen_legality_list.py --apply` ⇒ `spec/SimRISC-12-其它指令.md` 附录 B 新增 `encode_sbz` 行（恰 12 个 lr id）；该册为只读锁册 ⇒ 同笔更新 `manifests/spec-readonly.lock.toml` sha256 + 授权注记（Process-06 §5）。预测行（以当前数据只读模拟）：`* encode_sbz：SBZ 非零 → ILLI — lr.b.an…lr.w.nn（12 条）`，以 `--apply` 实际输出为准。
6. **编码/字段/id 不变**：`opc/ha/mask/value/fields/format/id` 全部不动；F1 只补合法性口径。不改 LLVM/QEMU/gem5/tests 实现。

### 已否方案（取舍依据）

- **不改 `rdhb` 的名字/role/bank**：`_get_id` 用 `_infer_feature(fields)` 以首字段 bank 派生 id（现 `..._orrr_rd`）；改名或换 bank 会改 12 个 id，牵连矩阵、向量、LLVM/QEMU 引用，代价远大于收益；`role` 无 schema 校验但被 testcase 生成/校验器当语义使用，改值会改变预置期望。
- **不新增 rule id**（如 `lr_hb_sbz`）：`encode_sbz` 已覆盖同一判据，新增只会多一条生成列表/孤儿，无收益。
- **不用 `rdhb != rd0`**：会映射到 `dst_rd0`，语义反向。

## 文件范围

- `contracts/opcodes.yaml`（生成物，生成器重生成）
- `contracts/legality_rules.yaml`
- `tools/spec/generate_opcodes.py`
- `.tao/contracts/contract-isa.md`（§14.2；**人读契约正文，手改**——现场核对无生成器/生成标记，勿当生成物等重生成）
- `spec/SimRISC-12-其它指令.md`（**仅 LEGALITY 生成区**，经 `gen_legality_list.py --apply`）
- `manifests/spec-readonly.lock.toml`（仅 SimRISC-12 sha256 + 注记）
- 本任务书、`.tao/knowledge/milestones.md`

**不改**：`tests/**`、`components/**`、`Makefile`、门控脚本；`.tao/knowledge/refs/GEM5-002t-*`、`GEM5-011t` 任务书（跨模块，见 §验收 6）。

## 未决（派单前须主会话确认）

1. **SimRISC-12 生成区 + 只读锁**：本任务**必然**改 `spec/` 只读册（附录 B 生成块），按 Process-06 §2/§3 需用户**事先**明确允许；现有授权原话只提「契约」。建议主会话确认的原话：「批准 SPEC-182t 同步 SimRISC-12 附录 B 生成区并更新只读锁 sha256」。**未确认 ⇒ BLOCKED，不派单**（只改 contracts 会让 `check-legality-drift` 恒红）。
2. 若用户拒绝改 spec 册：唯一替代是「不补 `rule_refs`」，与「避免只写散文不可机器判」相悖，需重新裁定。

## 验收标准

1. **12/12 可定位**：现场断言 12 条 `lr.*` 均 `legality == ["rdhb == rd0"]` 且 `rule_refs == ["encode_sbz"]`；`encode_sbz` 存在且 `status: active`/`fault: ILLI`；`spec/SimRISC-12` 附录 B 的 `encode_sbz` 行恰列这 12 个 id（脚本计数现场派生，不写死）。
2. **门控**（每条贴真实命令 + rc）：`make check-legality-invariants`、`make check-isa-coverage`、`make check-spec-readonly`、`make check-instrinfo`、`make validate-encoding`、`make check-milestones-fresh`；因改动必然受影响、须一并绿的：`make check-legality-drift`、`make check-rule-refs`、`make check-contracts-pending`。任一红按现场处置并记录。
3. **编码未变**：重生成前后 12 条 lr 的 `opc/ha/mask/value/fields/id` 逐字段相等；用脚本现场比对并给结论（不贴死值）。
4. **反例可达 FAIL**：至少一次注入（如把某条 lr 的 `rdhb == rd0` 改为 `rdhb != rd0`，或删一条）⇒ 门控 FAIL；`cp` 备份 + md5 对账还原 ⇒ 回绿。禁 `git checkout/restore/stash`。一键证据脚本落 `.work/evidence/SPEC-182t/`。
5. **不越界**：`git status --porcelain -uall` 只列 §文件范围；`spec/SimRISC-12` 的 diff **只有** LEGALITY 块（`git diff -U0` 可证）。
6. **跨模块影响清单**（写入完成区，不在本任务修）：
   - gem5 `GEM5-011t-B6`（未提交任务书）：`check_b6` 现断言「`encode_sbz` = 2」「12 条 lr `legality`/`rule_refs` 为空」「缺口提示行存在」及「未决问题 1」——本任务后全部过期，B6 派单前须改为 `encode_sbz` = 14、lr 带 `rdhb == rd0`/`encode_sbz`、删缺口提示与未决项。
   - `.tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv` 的 12 条 lr `g1_note` 仍写「contracts 缺规则（F1）」——gem5 侧补注或另立小修（非本任务文件范围）。
   - LLVM：无需改（`DADAOLROrrr` 两操作数、hb 恒 0；`check-instrinfo`/`check-isa-coverage` 不读 legality）；QEMU：已实现 `hb != rd0 ⇒ ILLI`；tests：`atomics-lrsc.yaml` 已含 ILLI 用例。三者均不改。
7. 完成区 ≤30 行；状态 `待验收`。

## 完成区
**测试结果**：通过 15/15（11 门控 + 2 契约/编码检查 + 2 注入自检）；`./.work/evidence/SPEC-182t/run.sh --inject` rc=0。
**修改文件**：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tools/spec/generate_opcodes.py`、`.tao/contracts/contract-isa.md`、`spec/SimRISC-12-其它指令.md`（仅附录 B 生成区 +1 行）、`manifests/spec-readonly.lock.toml`、本任务书、`.tao/knowledge/milestones.md`；证据 `.work/evidence/SPEC-182t/`。
**验收结果**：
- 12/12：lr 记录数 12（现场派生），全部 `legality == ["rdhb == rd0"]`、`rule_refs == ["encode_sbz"]`；`encode_sbz` active/ILLI/static；附录 B 行 id 数 12 且集合一致、标注（12 条）一致。
- 编码未变：基线 `git show HEAD:contracts/opcodes.yaml` vs 当前，12 条 lr 的 `id/opc/ha/mask/value/fields` 0 diff（`check_encoding.py` PASS）。
- 门控 rc=0：check-legality-invariants、check-isa-coverage、check-spec-readonly、check-instrinfo、validate-encoding、check-legality-drift、check-rule-refs、check-contracts-pending、check-contracts-dir、check-contract-relocs、check-milestones-fresh。
- 注入：A 把 `lr.o.nn` 的 `rdhb == rd0` 改 `!=` ⇒ `check_contract` rc=1；B 删 SimRISC-12 附录 `encode_sbz` 行 ⇒ `check-legality-drift` rc=2（1 violation）；均 `cp` 备份 + md5 相等还原后回绿。
- `git status --porcelain -uall` 仅列上述 8 个范围文件；SimRISC-12 `git diff -U0` 仅 +1 行 LEGALITY。
**新发现/坑**：
- 只读锁改 sha256 曾按哈希值锚点误改到 `SimRISC-04` 条目（两文件新旧哈希交错），已按 `path` 块上下文改回；改锁必须按 path 定位、改后跑 `check-spec-readonly`。
- `make` 门控失败退出码可为 2，注入断言须判 non-zero 而非 `==1`。
- 证据脚本读 `legality_rules.yaml` 须取顶层 `rules` 键（原地误当列表，已修）。
- `.tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv` 12 条 lr 的 `g1_note` 仍写「contracts 缺规则（F1）」。
**遗留问题**：跨模块（不在本任务修）——① gem5 `GEM5-011t-B6` 的 `check_b6` 断言过期（encode_sbz 数 2→14、lr legality/rule_refs 非空、删缺口/未决提示）；② matrix tsv 12 行补注；③ LLVM/QEMU/tests 无需改（已实现/已覆盖）。

## 审阅记录

#### 第 1 轮 engineer 自审
- 逐行核对 `generate_opcodes.py`：lr 分支仅改 `leg`；`EXPR_TO_RULE` 新增 `rdhb == rd0 → encode_sbz` 与既有 `rdhb != rd0 → dst_rd0` 无键冲突；重生成仅 12 条 lr 记录 + rule_refs 计数头变化。
- 核对 `legality_rules.yaml`：`encode_sbz` 删「M1 范围外」过期句；`dst_rd0` 明确 `role: dst` 为位域默认分类、不表示写回（与 `ADR-0034 D5` 一致）。
- 核对 `contract-isa.md §14.2`：保留 `[SimRISC-12 §LR-SC指令]` 引用，补 `rdHC` 数据目的。
- 核对 lock：diff 仅 SimRISC-12 块 sha256 + 授权注记；`check-spec-readonly` 21 册 OK。
- 核对证据脚本：两处注入均可 FAIL、md5 还原、禁 git restore。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 只读锁 sha256 误命中 SimRISC-04 条目 | ✅已修 | 按 `path` 块上下文恢复 SimRISC-04、重设 SimRISC-12 | `git diff manifests/...` 仅 SimRISC-12 块；check-spec-readonly rc=0 |
| check_contract.py 把 rules 顶层当列表 | ✅已修 | 取 `["rules"]` | run.sh rc=0 |
| 注入断言用 `==1`，make 实际 rc=2 | ✅已修 | 新增 `report_nonzero` | `--inject` 中 drift rc=2 判 PASS |

#### 第 1 轮 reviewer 验收（2026-11-02，独立重跑）
**现场**：分支 SPEC-182t / HEAD `82e914df`（WIP），审前审后 `git status --porcelain -uall` 均空；`git diff --name-only 8e7f26e6..HEAD` = 恰 8 文件（任务书、milestones、contract-isa、legality_rules、opcodes.yaml、generate_opcodes.py、SimRISC-12、只读锁），无 tests/components/LLVM/QEMU/Makefile 改动。
**门控重跑（我自己的 rc）**：check-legality-invariants / check-isa-coverage / check-spec-readonly / check-instrinfo / validate-encoding / check-legality-drift / check-rule-refs / check-milestones-fresh **8/8 rc=0**（另 check-contracts-pending rc=0）；注入还原后终检复跑仍 8/8 rc=0。证据脚本 `./.work/evidence/SPEC-182t/run.sh` rc=0、`run.sh --inject` rc=0（inject-A check_contract rc=1、inject-B drift rc=2，与完成区一致）。
**12/12**：现场派生 lr 记录 12，全部 `legality==["rdhb == rd0"]`、`rule_refs==["encode_sbz"]`；`encode_sbz` status=active/fault=ILLI/kind=static；附录 B `encode_sbz` 行恰 12 个 id、集合与 lr id 集合相等、标注（12 条）；`gen_legality_list.py --verify` 12 册全 OK。
**编码 0 diff**：`git show 8e7f26e6:contracts/opcodes.yaml` vs 当前，12 条 lr 的 `id/opc/ha/mask/value/fields` 0 diff，lr 无其它字段变化，非 lr 记录 0 变化（仅头注 `有 rule_refs 231→243`）；重跑 `generate_opcodes.py` 后 md5 `da91e56e…` 不变 ⇒ 生成物非手改。
**只读锁**：`sha256sum spec/SimRISC-12` = `a1224b92…51d77` 与锁值逐字相等；锁 diff 仅 SimRISC-12 块（4+/1-，含授权注记），未误改其它册条目；check-spec-readonly 21 册 OK。
**独立注入（cp+md5，未用 git checkout/restore/stash）**：A 改 `contracts/opcodes.yaml` 首条 lr `rdhb == rd0`→`!=`（md5 `da91e5…`→`e7c615…`）⇒ 证据 `check_contract` rc=1 FAIL，还原 md5 相等后 rc=0；B 删 SimRISC-12 附录 `encode_sbz` 行（`762117…`→`441ffc…`）⇒ `check-legality-drift` rc=2（1 violation）+ `check-spec-readonly` rc=2（MISMATCH），还原后两者 rc=0。审后对账：status 空、8 文件 md5 与审前快照逐一相等。
**约束核验**：状态 `待验收`、完成区 15 行；`rdhb role=dst` 已写明「orrr 位域默认分类、不表示写回、数据目的 rdhc」（实测字段 rdhb=dst/rdhc=src 一致）；跨模块遗留（B6 断言 L38/L240 过期、矩阵 g1_note）本任务未改、已披露，未伪称完成；LLVM/QEMU/tests 不改有据（check-instrinfo/check-isa-coverage 绿；QEMU patch `a->hb != 0 ⇒ ILLI`；`atomics-lrsc.yaml` 已有 `rdHB = rd2 != rd0 -> ILLI` 用例）。
**findings（不阻断，交 architect 收尾）**：① 无 repo 门控校验 legality↔rule_refs 一致性——注入 A 后 validate-encoding / check-legality-drift / check-rule-refs / check-legality-invariants 全 rc=0，仅证据脚本捕获（门控脚本不在本任务范围，建议另立遗留补进 check-legality-invariants）；② 任务书 §未决 1 仍写「未确认 ⇒ BLOCKED」，spec 册授权原话只落在只读锁注记，收尾请回填任务书；③ 完成区遗留②写「12 条 lr g1_note」，现场为 **24 行**（12 lr + 12 sc）同文注记，收尾更正；④ 任务书称 B6 任务书「未提交」，实际已在 `8e7f26e6` 提交（过期断言属实、未改）。
**判决：Accepted** —— 验收标准 1–7 全部由我本人重跑证实（命令/输出/退出码见上），范围 8 文件无越界、无凑绿、无改门控/测试；上述 4 条 finding 为文档级/遗留登记，不改本轮判决。
