# INFRA-102t: 门控补强与"去写死计数"（跨模块安全网）

**模块**：infra
**项目里程碑**：M9（收尾前，先于 SPEC-164t / LLVM-126t / LLVM-127t）
**依赖**：`SPEC-165t`/`SPEC-166t`（已验证，`master df46f0f1`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源（用户 2026-10-22）

「减少交叉链接很关键，减少各种计数和比较很关键；不然，时间都浪费在这些无谓的修订中了」

**现状痛点（实测）**：
- `tools/spec/check_fp_contract.py`：`EXPECTED_TOTAL = 64` + `FAMILY_COUNTS`（14 族写死）⇒ 每加/翻一条 FP 记录要同步改 3 处
- `tools/spec/check_scope.py`：`m1=156 / fp=64 / excluded=27 / m3=1 / m8=7 / m9=9 / total=264` 全写死
- `tools/spec/check_rule_refs.py`：`EXPECTED_ORPHAN_EXEMPTIONS` 写死
- 文档侧：`contract-isa.md` 3 处、`MEMORY.md` 1 处境写死条数

⇒ 每新增/翻转一条指令，平均要改 **4–6 个地方**（opcodes、spec 生成区、门控常量、契约计数、文档计数），这是"无谓修订"的主因。

## 目标

### 1. 计数一律现场派生（不写死）
- `check_scope.py`：删除全部期望常量；改为断言**不变量**：
  - `total == len(opcodes)`（自身）；
  - 分区集合 = `m1/fp/excluded/m3/m8/m9` 且**并集 == 全量**、**两两不交**；
  - `excluded ⇒ decode == ILLI`、非 `excluded` ⇒ 无 `decode`（既有规则保留）；
- `check_fp_contract.py`：删除 `EXPECTED_TOTAL`/`FAMILY_COUNTS`；改为
  - `fp_semantics` 的 id 集合 == `opcodes.yaml` 中 `scope == fp` 的 id 集合（**双向相等**，缺/多都红）；
  - 族集合 == 记录中出现的 `family` 值集合（现场收集）；
  - 每条记录的 `family`/`spec_cite`/`semantics_ref` 非空且格式合法；
- `check_rule_refs.py`：豁免集合从**数据文件/注释**读取（或改为"孤儿必须出现在显式 allowlist 文件"），不写在代码里。

### 2. 生成物用"幂等"代替"两处比对"
- `gen_asm_list` / `gen_legality_list` 已是单源生成：门控改为**重生成 + byte 比对**（生成结果与盘上一致即 PASS），不再维护第二份期望文本；
- 相关门控（`check_asm_list_consistency` / `check_asm_prose` / `check_tables` / `check_spec_codeblocks`）里凡是"期望字符串/期望条数"的常量，全部改为现场派生或删除。

### 3. 补 7 个覆盖缺口（原计划）
- `ISS-320`：`validate_instrinfo.py` 覆盖 FP `.td`（`DADAOInstrInfoFP.td.patch`）
- `ISS-321`：`check_qemu_trans --strict` 增加 orphan（trans 残留）方向
- `ISS-325`：`check_tables.py` 覆盖 MISC-RF（`op 0x44`）
- `ISS-327`：`gen_isa_coverage` 的 `L2_isel` 识别伪指令/同义名/`BuildMI` 三类来源
- `ISS-225`：`check-qemu-semantics` 增"`helper.c.patch` 不得出现 umon 接管分支"形态断言
- `ISS-102`+`ISS-118`（合并）：覆盖断言粒度 —— 删单条用例/删同族多 pattern 之一必须红
- `ISS-058`：`decodetree` 输出 bit-reproducible（固定 `PYTHONHASHSEED`）

## 验收

1. `grep -nE 'EXPECTED_TOTAL|FAMILY_COUNTS|== (264|156|64|31|27|60)\b' tools/**/*.py` ⇒ **0 命中**（除注释说明）。
2. 对每个改动过的门控：**注入 → FAIL → 还原 → PASS**（`cp`+md5），至少 8 条注入，逐条贴真实输出。
3. 新增 7 项缺口各有**可达 FAIL**（真实注入）。
4. `make check`(L1) + `make check-modules`(L2) 绿；`check_patch_tree` 绿。
5. 删除两条 issue 记录（`ISS-102`/`118` 合并后按合并条处理）。

## 接口规范

- **输入**：`tools/spec/**`、`tools/qemu/**`、`tools/llvm/**`、`tools/infra/**`、`contracts/**`（只读）。
- **输出**：去常量的门控 + 7 项覆盖补强 + 各自的 `--self-test`。
- **约束**：不改 `spec/**`、不改指令语义；不 commit/push；临时目录 `/tmp/opencode/INFRA-102t/`。

## 风险与纪律

- **不许为了"绿"放宽断言**：删常量不等于删校验，必须保留"集合相等/双向覆盖/不交"这类不变量；
- 每条注入都要真实红→还原→绿，禁恒真；
- 若某门控依赖的常量无法派生（如历史豁免清单），改为**显式数据文件**并加"数据文件本身被引用"断言。

## 完成区

**测试结果**：`.work/evidence/INFRA-102t/run.sh` **70 checks / 0 fails, rc=0**；`make check`(L1) rc=0（41.1 s）；`make check-modules`(L2) rc=0（259 s）；各改动门控 `--self-test` 全 PASS。
**修改文件**：`tools/spec/{check_scope,check_fp_contract,check_rule_refs,check_tables}.py`、`tools/spec/data/rule_ref_exemptions.yaml`(新)、`tools/llvm/{validate_instrinfo,gen_isa_coverage}.py` + `llvm-isa-backend-matrix.{tsv,md}`(重生成)、`tools/qemu/{check_qemu_trans,semantics_gate}.py`、`tools/qemu/check_decodetree_repro.py`(新)、`tools/infra/check_case_ledger.py`(新) + `tests/case-ledger.tsv`(新，生成物)、`Makefile`、`.tao/knowledge/issues.yaml`(删 ISS-102/118)。
**验收结果**：去常量 grep `EXPECTED_TOTAL|FAMILY_COUNTS|== (264|156|64|31|27|60)` ⇒ **0 命中**（含注释）；check_scope 改为并集=全量/两两不交/每分区非空/id 唯一；check_fp_contract 改为 id 集合双向 + 族集合现场双向 + **规则引用由 legality 表达式逐条派生**（原 39/2/28/28/4/15 常量删除）；check_rule_refs 豁免改数据文件（缺/空/过期/新孤儿均红）；`check-instrinfo` 覆盖 FP `.td`（64/64，262 defs）；`check_qemu_trans --strict` 双向（orphan 0）；`check_tables` 覆盖 OPC-RF（50 条/64 格，5 表 151 条）；`gen_isa_coverage` 新增 pseudo/buildmi/synonym 三类证据（L2 yes 107→126，`--check` PASS）；新增 L1：`check-case-ledger`（删单条 vector 用例 / 单条 lit pattern 均红）、`check-decodetree-repro`（seed 敏感实测 ⇒ 构建固定 `PYTHONHASHSEED=0`）、`check-qemu-forms`（umon 接管符号 0 命中，209 文件）。**16 条独立注入**全部「红→cp+md5 还原→绿」（I01–I16，见证据脚本输出）；耗时：新增 3 门控 L1 增量 ≈1.4 s（ledger 0.89 s / repro 0.35 s / forms 0.18 s）。
**新发现/坑**：① `validate_instrinfo` 旧 `[^}]*` 解析被 FP 注释里的 `{rfN}` 截断（`ft2fo` 丢 `let op`，旧门控不覆盖 FP 故从未暴露）⇒ 改按整行 `}` 收尾；② decodetree 实测 seed 0/1/2/12345 md5 全不同（字段赋值顺序依赖集合迭代）⇒ 只能靠构建固定 seed，非上游脚本可改（组件补丁集受 `check-patch-tree` 锁）；③ pseudo 展开体共享（ADD/SUB/MUL 同一 body + 三元选 opcode）静态无法逐条区分 ⇒ 证据保守多认，已在矩阵文档披露；④ 分支 `INFRA-102t` 在改动后创建（开工时工作树干净、但未先建分支即改文件；全程未 commit）。
**遗留问题**：① `check_tables` 仍不含 OPC-MISC（`op 0x77`，本任务只要求 RF；原有缺口，未越界补）；② `synonym` 路径当前现场 0 组（机制有单测正/反例，真实数据无改名）；③ 证据脚本全跑约 7 min（含 L2 259 s）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| check_fp_contract 规则条数常量删除后，“两条源同时漏填”是否仍可判 | ✅已修 | 用 `legality` 表达式逐条派生规则集合，与 `rule_refs` 双向相等；未知表达式直接红 | `--self-test` case7 + 证据 I05（双源同删 ⇒ FAIL） |
| check_scope 删计数后是否出现“删记录仍全绿”的放宽 | ❌不修（设计） | 计数本就不应作为判据；单条删除由 `check-instrinfo`（orphan def）/`check_qemu_trans`（orphan trans）/`check_isa_coverage`（行数漂移）/`check_case_ledger` 覆盖 | L1 全绿 + 各门控注入（I08/I09/I11/I12） |
| `validate_instrinfo --td` 单文件模式会因新增 FP 覆盖而假红 | ✅已修 | `--td` 时自动并入 FP 补丁；若覆盖的正是 FP 文件则不重复 | 手动 `--td` 重建主 `.td` ⇒ rc=0 |
| `gen_isa_coverage` 新增三类证据是否有不可达分支/静默空集 | ✅已修 | 增 `--self-test`：pseudo/synonym/buildmi 各一正一反例 | `C10` self-test PASS |
| 证据脚本被 timeout 打断会留下注入改动 | ✅已修 | 台账式 `trap cleanup EXIT TERM INT`（cp 还原）；本轮首次超时后即用 `cp`+md5 复原并验证 | 全量证据 rc=0；`git status` 仅 16 个预期文件 |

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，2026-10-23，判决只依据本人 rc）**：
- 去常量 grep：`grep -rEn 'EXPECTED_TOTAL|FAMILY_COUNTS|== (264|156|64|31|27|60)\b' tools --include=*.py` ⇒ **0 命中**（放宽空格限制后仅 `check_scope.py:8` 文档注释，代码 0）。
- 临时树注入 8/8 红（不动仓库）：删唯一 m3 记录 ⇒ check_scope rc=1（每 scope 非空）；重复 id ⇒ rc=1；删 1 条 fp_semantics 记录 ⇒ check_fp_contract rc=1（覆盖双向）；改 family ⇒ rc=1；删 1 条豁免 ⇒ check_rule_refs rc=1（未登记孤儿）；删 OPC-RF 一格 ⇒ check_tables rc=1（ISS-325）；去 seed 固定 ⇒ check_decodetree_repro rc=1（ISS-058）。
- 真实文件注入（cp+md5，逐条还原后 md5 相等、还原后 rc=0）：**B1** 删 1 条 m1 记录（`ld.ub_rrii_rd`）⇒ check_scope rc=0（按设计）但 validate_instrinfo rc=1（orphan def）/ check_qemu_trans --strict rc=1（orphan trans）/ gen_isa_coverage --check rc=1 / validate_vectors rc=1 ⇒ **单条删除由 4 个 L1 门控兜底，网未变弱**；**B2** 删 FP def `ftmin_orrr_rf` ⇒ rc=1「FP 记录 def 数=0」（ISS-320）；**B3** 注入 `trans_zzz_reviewer_orphan` ⇒ rc=1 ORPHAN（ISS-321）；**B4** helper.c.patch 注入 `umon_host_` 符号 ⇒ check-qemu-forms rc=1（ISS-225）；**B5a/B5b** 删 1 条 vector 用例 / 1 条 lit `@@ OBJ:` pattern ⇒ check-case-ledger rc=1 且定位到具体行（ISS-102+118）。
- 7 项缺口：6 项 reviewer 真实注入红（320/321/325/225/102+118/058），ISS-327 读自测（pseudo/synonym/buildmi 各正+反例、反例判空可 FAIL）；9 个门控 `--self-test` 全 rc=0。
- 产物确定性：`tests/case-ledger.tsv` 无时间戳/绝对路径（grep 0）；连续两次 `--write` byte-identical 且与入库一致（md5 `dacd55f0…`）。
- 门控：`make check`(L1) **rc=0，40.4 s**（基线 ~41 s ⇒ 增量 <1 s，远低于 20 s）；`make check-modules`(L2) **rc=0，264 s**；`git show 731a1ca5:Makefile | grep -c` 三新门控各 2 命中且均在 `_locked-check`，L1 输出可见三者 PASS。
- issues：`git diff 731a1ca5~1..731a1ca5` 仅删 ISS-102/118（任务书验收⑤「合并处理」口径），未动其它、无误关；无 `resolved_by: INFRA-102t` 条目。证据脚本审读：结构合格（manifest cp+md5 还原 + trap、16 注入各带红/绿、mutate.py 逐例核为真实改动）；按本轮指令未整脚本重跑（~7 min）。
- 快照对账：验收前后 `git status --porcelain -uall` 均为空且逐行 diff 一致；注入文件全部 cp+md5 还原、无残留。

**约束核验**：不改 `spec/**` ✓（diff 无 spec 正文）；断言未削弱 ✓（excluded⇔ILLI 双向、`_rf` 约束、旧字段消失、spec_cite 格式、dst_rf0/encode_fp_root_n 专属规则、三方交叉断言均在，注入证实）；临时目录合规 ✓。

**非阻断观察**：① 单条 m1 记录删除不再由 check_scope 自身判红（改由 4 门控兜底，B1 实证；与任务书「计数不作判据」设计一致，engineer 已披露）；② ISS-320/321/325/327/225/058 修好但仍 open，ISS-102/118 用删除而非 `resolved_by=INFRA-102t`（删除系任务书验收⑤明示口径）——建议 `/complete` 时 architect 统一以 resolved_by 收口留痕；③ milestones.md 本任务状态行已改但未列入「修改文件」（披露瑕疵）。

**判决：Accepted**（阻断口径逐项核过：无门控变弱/假绿、无误关 issues、无产物不确定、L1/L2 rc=0；主会话可将状态改为 `已验证`，architect 终审。）

