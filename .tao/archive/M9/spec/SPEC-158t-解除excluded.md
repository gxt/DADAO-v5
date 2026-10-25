# SPEC-158t: `ftfma`/`fofma` 解除 `excluded`（`scope → fp`，族表/计数/锁同步）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-157t`（记录已立）、`QEMU-070t`（trans 已落 ⇒ 翻转后 L2 仍绿）、`LLVM-123t`（`.td` 已落 ⇒ `check-instrinfo` 绿）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么必须等三册落地才能翻

- `scope: fp` 的记录必须有 `.td`（`validate_instrinfo.py` 文件头：`m1/m3/m8/m9` 与 `fp` 均参与 coverage）⇒ 等 `LLVM-123t`；
- `check_qemu_trans --strict` 是 **L2** 成员，缺 trans 时翻转会让 L2 红 ⇒ 等 `QEMU-070t`；
- 两条都到位后，本册翻转**不会再制造任何新红**（与 `SPEC-155t` 同一纪律，顺序已在 clmul 链上修正）。

### 现场事实（2026-10-21 核，执行前须复核）

- `scope` 真源在生成器：`tools/spec/generate_opcodes.py` 的 `rec("ftfma-...", ..., scope="excluded")` / `fofma`。
- `check_fp_contract.py`：族与计数由现场派生（`INFRA-102t` 后无写死常量）；现场 **14 族 / 64 条**；翻转后必须 **15 族 / 66 条**（新族 `fma` = 2）。
- `contracts/fp_semantics.yaml` 由生成器产出、只收 `scope == "fp"` 的记录；每条需 `family`、`spec_cite`（`^SimRISC-0[0-7]`）、`semantics_ref = contract-fp.md#<anchor>`、`legality_refs`。
- `.tao/contracts/contract-fp.md` 的 `fma` 段与 `<a id="fma">` 锚点由 `SPEC-157t` 提供（本册只引用，不新建）。
- `check_scope.py` 的分区计数为**写死断言**（`excluded`、`fp`、`total` 均需同步）+ changelog 段。

## 目标

1. `ftfma`/`fofma` 由 `excluded` 转 **`fp`**（移除 `decode: ILLI`），`dst_rf0` 仍生效；
2. FP 族表新增 `fma`（2 条），`fp` 计数 **64→66**、`excluded` **4→2**；
3. 全部派生生成物与门控计数现场派生后一致；只读锁重算。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/check_fp_contract.py`、`tools/spec/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_isa_coverage.py`、`spec/SimRISC-07`（追加 1 行变更记录）、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（`fp 66`、`excluded 2`、total 266 不变）、`fp_semantics.yaml`（+2 条 `family: fma`）、`check_fp_contract` 族集合现场派生（14→15，不写死）、`check_scope`（无写死常量，现场派生）与 changelog、速查表/合法性清单/ISA 矩阵/`contract-asm-list` 重生成、只读锁 sha。
- **约束**：**只**改 `ftfma`/`fofma` 相关记录与本册必需的计数/族表；其它记录**逐字节不变**；不改判定语义（只改计数常量与族枚举）；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 族与契约

- `fp_semantics.yaml` 新增两条：`family: fma`、`spec_cite: "SimRISC-07 §无符号乘法加法"`（以实际章节名为准）、`semantics_ref: "contract-fp.md#fma"`、`legality_refs: [dst_rf0]`；
- `check_fp_contract.py` 的 `families` 段新增 `fma` 的 `required_keys`（与既有族同构），族计数 12→13、`fp` 60→62；
- 锚点可达性：`contract-fp.md` 必须含 `<a id="fma">`（`SPEC-157t` 已建，本册校验）。

### B. 计数与生成物（**逐项现场跑**）

- `generate_opcodes` → `check_scope` → `validate-encoding` → `check-rule-refs` → `check_fp_contract` → `gen_asm_list --embed-spec/--drift` → `gen_legality_list --apply` → `gen_isa_coverage` → `contract-asm-list`；
- `SimRISC-07` 变更记录**追加** 1 行（不改写历史）；只读锁重算。

### C. 不改面

- `opcodes.yaml` 中 `ftfma`/`fofma` 的 `op`/`ha`/`format`/`legality` 逐字节不变（只改 `scope`、删 `decode`）；
- 其它 260 条记录零改动（`git diff` 自查并粘输出）。

## 验收标准

1. `fp` = **62**、`excluded` = 现场派生（本册应减 1）、`total` = **262**；`fp_semantics.yaml` 含 2 条 `family: fma`。
2. `check_scope` / `check_fp_contract`（**13 族 / 62**）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo` / `check-isa-coverage` 全绿。
3. `check_qemu_trans --strict` = **262/262**（`QEMU-070t` 已落）。
4. `check-spec-changelog` / `check-spec-readonly` / `check-spec-drift` / `check-asm-list*` 全绿；`git diff --stat` 显示非 `fma` 记录零改动。
5. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
6. **可达 FAIL ≥ 2**：① 漏改 `check_fp_contract` 的族计数 ⇒ 红；② 不重算只读锁 ⇒ `check-spec-readonly` 红。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（生成器 `scope` 位置、族枚举、计数、锚点）。
2. 生成器改 `scope="fp"` + 族映射 → 重生成 → 逐项门控。
3. `check_fp_contract` 族/计数；`check_scope` 计数；变更记录 1 行；只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时不改 `check_fp_contract.py` 的族计数（仍 12/60）⇒ `check-fp-contract` 红；还原 ⇒ 绿。
- 临时不更新 `spec-readonly.lock.toml` ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不实现语义/选择（已由 `QEMU-070t`/`LLVM-123t` 完成）；不做测试（`TESTCASES-058t`）。
- 不顺手清理其它 `excluded` 记录或既有族划分。

## 完成区

**测试结果**：`bash .work/evidence/SPEC-158t/run.sh` = **20/20 PASS（rc=0）**；`--inject` = **27/27 PASS（rc=0）**（2 例「注入→红→`cp`+md5 还原→回绿」：① `fofma` scope 回 `excluded` ⇒ `check-fp-contract` rc=1（`fp_semantics 多出 fofma_rrrr_rf`）→ 还原 md5 `f5c5a0ad…` 命中 → rc=0；② 只读册追加字节 ⇒ `check-spec-readonly` rc=1 → 还原 md5 `15873da9…` 命中 → rc=0）。按用户 2026-10-23 口径**未跑全量 L1/L2**。
**修改文件**：`tools/spec/generate_opcodes.py`（2 条 `scope: fp`、`EXPR_TO_RULE` +`rfha != rf0`、头部/docstring 计数）；`tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` 删 2 条）；`contracts/opcodes.yaml`（重生成）；`contracts/fp_semantics.yaml`（`fma` 族 + 2 条、count 66）；`contracts/legality_rules.yaml`（`dst_rf0` 39→41 + fma 明细）；`.tao/contracts/contract-fp.md`（66 条/§15 41 条/§20 范围）；`.tao/contracts/contract-asm-list.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（重生成）；`spec/SimRISC-07`（附录 B 生成区）；`manifests/spec-readonly.lock.toml`（07 sha256 + 注记）；`.tao/knowledge/milestones.md`（1 行）、本任务书。
**验收结果**：现场 `total 266 / fp 66 / excluded 2 / m1 156 / m3 1 / m8 7 / m9 34`；`check_fp_contract` PASS（**15 族 / 66 条**、`fma: 2`）；2 条记录 `scope=fp`、无 `decode`、`rule_refs=['dst_rf0']`、`op 0x5E/0x5F`、`legality=['rfha != rf0']`；零改动脚本对基线：`same=264 flipped=2 other_changed=0`。门控 rc=0：`check_scope`/`check_fp_contract`/`check_qemu_trans --strict`（**266/266**）/`check_tables`/`check_asm_list_consistency`/`check_asm_list_drift`/`validate_encoding`（266）/`check_rule_refs`（16 规则/344 引用）/`check_legality_drift`/`check_legality_invariants`/`check_instrinfo`（0 errors）/`check_isa_coverage --check`/`check_spec_readonly`/`check_spec_cite_targets`/`check_spec_purity`/`check_spec_changelog`/`check_spec_drift`。
**新发现/坑**：① `rfha != rf0` **不在** `EXPR_TO_RULE`（`SPEC-157t` 预判的翻转前置）⇒ 已补 `dst_rf0`，否则生成器 `RuntimeError`；② `validate_instrinfo.py::MC_ONLY_EXCLUDED_IDS` 仍列 `ftfma/fofma` 并断言「必须在 .td 且为 excluded」⇒ 翻转后 `missing_mc_only` 报 2 errors；已移除（FP 覆盖 66/66 承接）；③ `gen_asm_list --embed-spec` **非幂等**（把附录 A 移到文末、12 册全员 churn）⇒ 仅用 `gen_legality_list --apply` 重写附录 B，11 册与 07 用 `cp` 备份还原（md5 对账）；④ 任务书 §验收标准 1/2 仍写旧口径（62/262/13 族），按派发口径 66/15/2/266 执行；⑤ 用户口径「不做注入」与 engineer 证据脚本硬规则冲突 ⇒ 默认无注入，`--inject` 可选并已跑通。
**遗留问题**：无未完成项（语义/后端已由 `QEMU-070t`/`LLVM-123t` 落，测试归 `TESTCASES-058t`）。低优：`.tao/knowledge/MEMORY.md` 第 6 项仍写「fp 64 条」，建议 `/complete` 同步为 66（engineer 不改知识库）；`spec/SimRISC-00` 附录未追加「fma 实现生效」条目（本册口径未列，避免扩面）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：11 个改动文件 + 证据脚本（含 2 例注入的可达 FAIL 路径与 `cp`+md5 还原对账）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `EXPR_TO_RULE` 缺 `rfha != rf0`，翻转后生成器必 `RuntimeError` | ✅已修 | +`("rfha != rf0","dst_rf0")` | `generate_opcodes` rc=0；`rule_refs=['dst_rf0']` |
| F2 `validate_instrinfo` allow-list 断言 2 条仍 excluded | ✅已修 | 删 `ftfma/fofma` 两 id + 注释 | `check_instrinfo` rc=0（`Result: 0 errors`） |
| F3 `gen_asm_list --embed-spec` 移动附录 A、污染 12 册 | ✅已修 | `cp` 备份还原 12 册（md5 `2ddf1adf…` 命中），改跑 `gen_legality_list --apply` | `git status` 仅 07 变动；`check_asm_list_consistency`/`drift` rc=0 |
| F4 注入 1 断言 `check_scope` 可红不成立（计数已现场派生，分区不变量仍成立） | ✅已修 | 断言改 `check-fp-contract`（fp_semantics 多出 id） | `--inject` 27/27，rc=1 → 还原 rc=0 |
| F5 任务书「SimRISC-07 追加 1 行变更记录」与 `check_spec_changelog`（01–12 禁附录）冲突 | ⏸延后（披露） | 不改 07 变更记录；仅在 00 中留待后续册 | `check_spec_changelog` rc=0 |

审查确认（无 finding）：① 2 条记录仅 `scope/decode/rule_refs` 变动，`op/ha/mask/value/format/legality/fields/spec_cite` 逐字节不变；其余 264 条逐字段相同（脚本全量，非抽样）；② `generate_opcodes`/`gen_legality_list`/`gen_isa_coverage` 重跑幂等；③ 只读锁 07 sha256 由独立 `sha256sum` 重算命中；④ 未用 `git checkout/restore/stash/show` 还原，注入前断言 `git diff` 非空防「空注入」。

### 第 1 轮 reviewer 验收（2026-10-23｜轻量：纯账面迁移，只跑受影响门控）

**重跑记录（rc=命令自身退出码，无管道；workdir=仓库根）**
- `python3 tools/spec/check_scope.py` → rc=0，现场 `m1=156 fp=66 excluded=2 m3=1 m8=7 m9=34 total=266`（基线 fp 64 / excluded 4）。
- `check_fp_contract` rc=0（现场族 `fma=2`，**15 族 / 66 条**）｜`check_qemu_trans --strict` rc=0 → **266/266**、orphan 0｜`check_tables` rc=0（6 表 177 记录 0 格不符）｜`check_asm_list_consistency` rc=0（12 册）｜`check_spec_readonly` rc=0（21 册）。
- `check-instrinfo` rc=0（`coverage 66/66`、`Result: 0 errors`）｜`check_spec_cite_targets` rc=0（unresolved=0）｜`check_spec_purity` rc=0（hits=0）｜`validate_encoding` rc=0（266 OK）——**必核 10 项门控全 rc=0**。
- 证据脚本重跑 `bash .work/evidence/SPEC-158t/run.sh` → **20/20 PASS，rc=0**，与完成区逐项一致（`counts/records/zero-change` 子日志全 PASS）。
- 记录核验（我独立解析，非采信完成区）：`ftfma_rrrr_rf`/`fofma_rrrr_rf` 均 `scope=fp`、无 `decode`、`rule_refs=['dst_rf0']`、`op 0x5E/0x5F`、`legality=['rfha != rf0']`；`fp_semantics` 两条 `family=fma`、`semantics_ref=contract-fp.md#fma`、`legality_refs=[dst_rf0]`。
- **264 条零改动**：`git show 69071716~1:contracts/opcodes.yaml` 对现场全量字段比对（非抽样）→ id 集合相同、`changed_ids` 仅上述 2 条、变更字段仅 `scope/decode/rule_refs`，其余 264 条逐字段相同（`op/mask/value/format/legality/fields/spec_cite` 逐字节同）。
- `git diff --stat 69071716~1..69071716` = 13 文件逐一看过：仅 2 条记录 + 生成物（fp_semantics、legality_rules `dst_rf0` 39→41、contract-fp、contract-asm-list、isa-matrix md+tsv、SimRISC-07、只读锁、milestones 1 行、本任务书）+ `generate_opcodes.py`（scope 翻转、`EXPR_TO_RULE` +`rfha != rf0`、头部计数口径）+ `validate_instrinfo.py`，**无其它语义改动**；`spec/SimRISC-07` 改动仅 `<!-- LEGALITY_END -->` 生成区（`dst_rf0` 36→38、删 decode ILLI 块），未碰正文与变更记录。
- 快照对账：验收前后 `git status --porcelain -uall` 均 **0 行**（干净），本轮我未修改任何文件。

**约束核验**
- 豁免合规：`MC_ONLY_EXCLUDED_IDS` 删 2 条**必要**——内存内探针把 2 条加回（不写盘、`__file__` 不变）⇒ `ERROR: allow-list 中的 MC-only excluded 记录 ftfma_rrrr_rf/fofma_rrrr_rf 未在 .td 中定义`、`Result: 2 errors`、rc=1；**未掩盖缺口**——其余 26 条守卫原样，`excluded` 现仅 `cfxld/cfxst`（均无 .td），fp 侧由逐条 `coverage 66/66` 承接。
- 计数与族表现场派生（`check_fp_contract`/`check_scope` 无写死常量），未改契约/spec 测试凑绿，未 commit/push；`legality` 表达式未变，只改 `scope`/计数与族枚举 ⇒ 判定语义未动。

**未做与提示（非阻断）**：按派发口径未跑 L1/L2、未复跑 `--inject`（engineer 自称 27/27）；证据脚本 `zero-change` 以运行时 `HEAD` 为基线、提交后退化为自比 ⇒ 264 零改动以我改对 `69071716~1` 的独立比对为准；任务书 §验收标准 1/2/5/6 仍写旧口径（62/262/13 族），按派发 66/15/2/266 执行；`MEMORY.md` 第 6 项仍写「fp 64 条」；07 未追加变更记录系 `check_spec_changelog` 断言 1（01–12 禁变更记录附录）所致，engineer 已披露。

**判决：Accepted**（计数 / 2 条字段 / 264 零改动 / 门控 rc / 豁免 5 项均在我自跑下达标）
