# m13-testcases-047: `.S` 向量对齐 `rf2rf`（删 2 加 1）+ 补「`.S` id 必须在 opcodes 里」门控

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-010`（spec 侧已合 `cb8ca30d`：删 `ft2ft`/`fo2fo`、加 `rf2rf`；id 264→263）
**可并行分片**：否
**预估**：1.5–2 h
**档位**：中改（看 diff + ≥2 路注入 + 相关门控）
**状态**：已验证

## 背景

`m13-spec-010` 只改了 spec 侧。现场仍有一处**仓库自相矛盾**：`contracts/opcodes.yaml` 已无 `ft2ft`/`fo2fo`，但 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 仍在且被 `tests/inst.yaml` 索引（2 条），**没有任何门控能发现**。本任务把该组件面与 spec 对齐。

## 任务

1. 删 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S`；新增 `rf2rf_orri_rf.S`（或与既有块复制族同形）；
2. `tests/inst.yaml` 删 2 条加 1 条；`tests/case-ledger.tsv` 重生成；`tests/inst/{MIGRATION.md,README.md,inventory.md}` 同步（263 id → 现场值）；
3. **补门控**：让 `validate-vectors` 或 `check-tests-index` 校验「每个 `.S` 载体 stem 必须能在 `contracts/opcodes.yaml` 找到 id」（现在缺失 ⇒ 这次才漏过去）；新断言必须**可红**（注入一个不存在 id 的 `.S` 应报错）。

## 验收（逐条贴真实 rc）

1. 旧指令在**本组件面**归零：`grep -rn "ft2ft\|fo2fo"` 在 `tests/inst/` = 0（历史归档/ADB/任务书豁免）；
2. 新指令 `rf2rf` 在本组件面落地：载体存在、索引 1 条、`check-inst-asm` 现场计数与 `case-ledger` 一致；
3. 门控：`check-inst-asm`、`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue`、`check-knowledge-refs` 全 rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 新增一个 stem 不在 opcodes 的 `.S` ⇒ 新门控应红；② 把 `rf2rf` 载体点号改断号 ⇒ `check-inst-asm` 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束

- 只改 `tests/inst/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/{validate_vectors.py,check_tests_index.py}`（仅新门控）、`tests/inst/{MIGRATION.md,README.md}`、本任务书；
- 不改 `spec/`、`contracts/`（已由 `m13-spec-010` 定稿；如需改，停下写「待裁定」）；
- 禁 `install-host`/`check-modules`/`build-*`（组件重建除外，按需并在完成区申报耗时）；不 sync/reset 节点；
- 不提交 git；注入还原用 `cp`+md5。

---

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查面：`tests/inst/02-reg-copy/rf2rf_orri_rf.S`（新增 165 行）、`tests/inst/macros/inst_test.inc`（+38 行）、`tests/inst.yaml`（−2/+1）、`tests/case-ledger.tsv`（重生成）、`tests/inst/{README.md,MIGRATION.md}`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① 任务书前提「无门控能发现」不成立：`validate_vectors.scan_asm_carriers` 自 `m13-testcases-030` 已断言 stem ∈ opcodes id（改前仓库正被它判红 2 条 `ASM CARRIER ORPHAN`） | ❌不修（复用优先） | 未新增门控代码；只在 README 写明该断言位置与红形态 | 改前 `validate_vectors.py` rc=1（2 条 ORPHAN）；注入①（新 stem）rc=1、撤注入 rc=0 |
| ② 自造宏名 `__CHECK_RF_MEM` 不被链例计数正则识别（`__CHECK_(?:RD|MEM)\w*`）⇒ 点号统计少 1，scan 报「点号不连续」 | ✅已修 | 改名 `__VERIFY_MEM_RF`/`__CHECK_MEM_RF`（与 `__CHECK_MEM_RB` 同形） | `scan_source` 11 链例 + 6 故障 = 1..17 连续 |
| ③ 用例 11 用 `__REC` 收点同样不被计数（`__REC`/`__VERIFY_*` 不计点） | ✅已修 | 新增 `TEST_MOV_RF0` 宏包住「源 rf0」例（`TEST_MOV\w*` 可识别） | 同上；同构复核该例 PASS |
| ④ 故障例仅覆盖 5 条 legality，缺 opcodes 的 `rfhc + immu6 <= 64`（源侧溢出） | ✅已修 | 增故障例 17（源起始 60 + 8 ⇒ ILLI），点号 12..17 | 同构复核 7/7 镜像绿（rc=248 = 0xF8） |
| ⑤ 编码字手写易错：fault 17 初值 0x40F11F08 错一位 | ✅已修 | 改 0x40F01F08，并加独立反算脚本（bits[17:12]/[11:6]/[5:0] 反解）核全部 8 个编码字 | 反算脚本 mismatch=0；同构复核该例 PASS |
| ⑥ 册归属：`rf2rf` 属 `SimRISC-02` 寄存器复制（与 `rd2rd`/`rb2rb` 同册），非 07 浮点册 | ✅已按 spec-first 定 | 落 `tests/inst/02-reg-copy/`，07 册不再有同组复制载体 | `validate-vectors`/`check-tests-index` rc=0；spec §1 分类行与 opcodes `opc 0x40/ha 0x3C` 对齐 |
| ⑦ `make check`（L1）另有 4 处红与本改动无关（instrinfo/interface = sibling 未合；run-artifacts = 基线非法日志名；patch-tree = sibling 在途未导出） | ⏸延后（文件集外） | 未改；逐条定位归属写进遗留 1/5 | 红项报文只点 `rf2rf/ft2ft/fo2fo` 的 .td/trans/patches，无 tests/ 文件 |

判决：无未修 finding（⑦ 属文件集外，已登记）⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-15，中改：diff + 3 路注入 + 门控 + 越界）

- **门控存在性核实（主会话错判的纠正成立）**：`validate_vectors.scan_asm_carriers` L113-119 断言「stem ∈ `contracts/opcodes.yaml`，否则 `ASM CARRIER ORPHAN`」；`git diff 903bdaf7 d49f6571 -- tools/` = **0 行**（断言非本任务新增）。临时树补回 `ft2ft/fo2fo_orri_rf.S` 模拟改前态 ⇒ `validate_vectors` **rc=1、2 条 ORPHAN**；删除后 **rc=0** ⇒ 改前 master 正是红的，本任务**无需新增门控**（复用优先）✓。
- **门控重跑（我自己的 rc）**：`validate-vectors` 0（264 载体/1 非 id）、`check-tests-index` 0（inst=273、载体↔索引 264/264）、`check-case-ledger` 0（5314 = asm 4791 + lit 523）、`check-no-residue` 0、`check-knowledge-refs` 0；`check-inst-asm` **rc=2（脚本 1）：264 id / 896 镜像 / 889 过**，FAIL 恰 7 条且全为 `rf2rf_orri_rf.S`、全是 `build: Command '[…llvm-mc…]' returned non-zero exit status 1`；我独立跑 `llvm-mc … rf2rf_orri_rf.S` 报 `unrecognized instruction mnemonic`（对照同册 `rd2rf_orri_rf.S` rc=0）⇒ 归因「llvm 未合助记符」成立、非向量错 ✓。
- **证据脚本**：审 <运行期证据目录>/run.sh（每条断言均有可达 FAIL 路径，计数现场派生；非 strict 分支为「红仅限 rf2rf 的 build 失败」），**原样重跑 20/20 PASS、`EVIDENCE_RC=0`**（含其 2 路注入的 cp+md5 还原对账）。
- **我方 3 路注入（均临时树 + `cp`/`md5` 还原，未动真文件）**：① 删 rf2rf 链例点 6 ⇒ `validate-vectors` rc=1 `ASM CARRIER POINTS` + `check-case-ledger` rc=1（`check-tests-index` 仍 0）⇒ 还原 md5 `721b723c…` 后两门控回绿；② 同册可汇编载体 `rd2rf` 期望改 1 bit ⇒ `run_asm_suite --id rd2rf_orri_rf` 链例 **FAIL**（`rc={'qemu': 2}` = 点 2）⇒ 还原 md5 `b88950f4…` 后 4/4 绿；③ 改前态模拟（见上）。⇒ 执行门控与结构门控的 FAIL 路径均可达、非恒真。
- **编码与期望独立复算**：8 个编码字全部满足 `(w & 0xFFFC0000) == 0x40F00000`，字段反解与注释逐条一致（`40F14A02`=20/40/2、`40F3FF81`=63/62/1、`40F00A01` dst=0、`40F14A00` immu6=0、`40F3CA08` 60+8=68、`40F14502`/`40F15504` 源目的交叠、`40F01F08` src60+8=68）；抽点 1/7/9/11 按 `SimRISC-02 §1` 推：整 64 位逐位复制、`2n≤63 ⇒ n≤31`（`{rf1:rf31}←{rf32:rf62}` 逐 beat 对 MSTORE）、`immu6=0`/源或目的越界/交叠/目的含 `rf0` ⇒ `ILLI=0xF8`、源 `rf0` 读完整 64 位、不置标志（FCSR 前后 `__VERIFY_EQ_RD`）—— 与载体逐条相符，期望全由 spec 派生。
- **册归属**：`SimRISC-02 §1` 分类行 = 寄存器复制（列 `rf2rf`），`opcodes.yaml` `scope: fp` 是寄存器银行口径（`check-scope`：fp ⇒ id 以 `_rf` 结尾）⇒ 落 `02-reg-copy` 与 spec 分类一致（该册现 17 个载体 = 块复制 9 + `cs.*` 8，README 计数 ✓）。
- **计数现场核**：`inst.yaml` 273、载体 264 = opcodes 263 id + 1 非 id、`case-ledger` 5314 = 4791+523、父态 asm 4806 → 4791（−32 旧载体行 +17 rf2rf 行）、镜像 901 → 896、载体 265 → 264 —— 与 MIGRATION §047 一致。
- **越界核**：`git show d49f6571 --numstat` = 9 路径，全在任务书允许集内（`tests/inst/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、本任务书）；`spec/`、`contracts/`、`components/`、`tools/` **0 改动**；审查后 `git status --porcelain -uall` 干净、6 个目标文件 md5 与审查前快照逐字相同；未跑 `install-host`/`check-modules`/`build-*`、未提交。
- **判决：Accepted（附 1 项验收字面未达成，请 architect 终审口径）**：验收 3 的 `check-inst-asm rc=0` 当前 **BLOCKED-DEP** —— `m13-llvm-001`/`m13-qemu-016` 均 `待开始`，装机 `qemu-system-dadao`（11-14 19:02）早于 qemu 源码 rf2rf 提交（11-15 13:44），`components/qemu/patches` 无 rf2rf 补丁 ⇒ 须两者合入并 `install-host` 后以 `--strict-l2` 复跑收口；非本交付物缺陷，且已如实披露于完成区/遗留 1。
- **文档级 finding（不阻断，收尾提交顺手改）**：① README 07 册「共 42 个」实为 **50**（漏 `fornd/ftrnd/fosclb/ftsclb/fosgnj/fosgnn/ftsgnj/ftsgnn` 8 个；44→42 系在既有错数上减 2）；② 完成区「lit 段 6 行残留」实为 **7 行**；③ 交付摘要「asm 4790→4791」实为 **4806→4791**；④ 证据脚本非 strict 分支断言「必须有红」，依赖合入转绿后须改用 `--strict-l2`（脚本内已注释）。

## 完成区

**测试结果**：证据脚本 20/20（含 L2）/ 19/19（`--no-l2`）；`rf2rf` 语义等价旧编码的**同构复核** 7/7 镜像绿；唯一未绿 = `check-inst-asm` 对 `rf2rf` 的 7 镜像（汇编器尚无该助记符 ⇒ 见遗留 1）。
**修改文件**（9 路径 = 6 改 + 2 删 + 1 增）：删 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S`；新增 `tests/inst/02-reg-copy/rf2rf_orri_rf.S`（17 点 = 链例 11 + 故障例 6）；`tests/inst/macros/inst_test.inc`（+`__VERIFY_MEM_RF`/`__CHECK_MEM_RF`/`TEST_MOV_RF0`，`TEST_MOV1` 增 `rf2rf` 分支）；`tests/inst.yaml`（删 2 加 1 ⇒ 273 条）；`tests/case-ledger.tsv`（`--write` 重生成）；`tests/inst/README.md`（44→42 / 16→17 + 身份断言说明）；`tests/inst/MIGRATION.md`（历史条目去悬空 id + 新增 §047）；本任务书。**未改** `validate_vectors.py`/`check_tests_index.py`（门控已存在，见验收 3）。
**验收结果**（真实 rc）：
1. 旧 id 归零：`grep -rn "ft2ft\|fo2fo" tests/inst tests/inst.yaml` = 0；`tests/case-ledger.tsv` 的 **asm 段** 0 行（lit 段 6 行残留属 llvm 侧，见遗留 2）；`rf2rf` 载体存在、`inst.yaml` 索引恰好 1 条。
2. `check-inst-asm` = 264 id / 896 镜像（链例 263 + 故障例 633）；889/896 通过，7 个 FAIL **全部**属 `rf2rf` 且都是 `llvm-mc` build 失败（非 rf2rf = 0）；`rf2rf` 载体现场 17 点、点号 1..17 连续。
3. 门控 rc：`validate-vectors` 0（264 载体 / 1 非 id）、`check-tests-index` 0（273 条、载体↔索引 264/264）、`check-case-ledger` 0（5314 = asm 4791 + lit 523）、`check-no-residue` 0、`check-knowledge-refs` 0（0 具体 `.work/**`、悬空 0）。
4. 注入①（新建 stem 不在 opcodes 的 `.S`）：`validate_vectors` rc=1 报 `ASM CARRIER ORPHAN`（命中 1）、`check_tests_index` rc=1 报「载体未入索引（缺）」；撤注入两门控 rc=0。
5. 注入②（`rf2rf` 点号 11→12）：`check-inst-asm` rc=2 报「检查点号不是 1..N 连续」→ `cp` 还原后 md5 与注入前逐字相同（脚本 F0/F2 两处对账）→ 回绿（`run_asm_suite` 扫描 rc=0）。
6. 依赖现场：`llvm-mc` 对 `rf2rf` 载体报 `unrecognized instruction mnemonic`；L1 的 `check-instrinfo`/`check-interface` 红只点 `.td`/`trans_*`（sibling 任务未合）。
7. 期望来源：`SimRISC-02 §1`（块传输保持 64 位二进制、源 `rf0` 读完整 64 位、`rf2rf` 目的含 `rf0` 判 ILLI、不置标志、精确性/无交集/`immu6` 1..63）—— 期望全为「目的 == 源位型」，不引模型、不从 qemu/llvm 反推。
**新发现/坑**：① 任务书前提不成立：`validate_vectors.scan_asm_carriers` 早已守护「stem ∈ opcodes id」（改前正是它红 2 条 ORPHAN）⇒ 无需新门控，只需注入复核（复用优先）。② `run_asm_suite` 链例计数只认 `TEST_*\w*` / `__CHECK_(RD|MEM)\w*`：宏名不合形（如 `__CHECK_RF_MEM`）⇒ 点号统计少 1、scan 假红；`__REC`/`__VERIFY_*` 不计点 ⇒ 独立用例须包进 `TEST_MOV*` 宏。③ 编码字必须现场反算（手写错一位即静默测错指令）。④ 跨任务前置（LLVM 助记符 / QEMU 译码）未到位时，可用「语义等价的旧编码」做同构复核，否则向量本身无法自证。
**遗留问题**：
1. `check-inst-asm` 对 `rf2rf` 7 镜像红（汇编器缺助记符 + QEMU 缺 `trans_rf2rf_orri_rf`）⇒ `m13-llvm-001`/`m13-qemu-016` 合入并 `install-host` 后复跑应 rc=0（届时 `make check-inst-asm` 用 `--strict-l2` 判）。
2. `tests/case-ledger.tsv` lit 段仍有 6 行旧 mnemonic，源在 `tests/unit/llvm/lit/**`（`m13-llvm-001` 文件集）；该任务删除后 `--write` 重生成即归零。
3. `Makefile` 注释「`.S` 载体全量 265 id」为硬编码（文件集外）⇒ 建议改「263 opcode id + 1 非 id 载体 = 264」。
4. `docs/TestReports/M13-FP-IEEE对齐审计.md` 仍提旧 id（文档面，文件集外）。
5. L1 另有 3 处红与本次无关：`check-instrinfo`/`check-interface`（sibling 未合）、`check-run-artifacts`（基线 2 个非法日志名）；`check-patch-tree` 红来自 sibling 在途改动未导出补丁。
