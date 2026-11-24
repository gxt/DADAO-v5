# ADR-0063: `contracts/opcodes.yaml` 单一写者与生成一致性（L1 门控）

**状态**：Accepted
**日期**：2026-11-24
**接受日期**：2026-11-25（D1–D5 经用户逐条确认）
**关联**：`m17-spec-003`（生成器与 yaml 漂移收口，`ISS-416`；本 ADR 的直接触发者）、`m17-spec-004`（本 ADR）；`ADR-0019`（重定位类型）、`ADR-0032`（ISA 编码再分配）——关系见「与既有 ADR 的关系」，本 ADR **不重复**其决策；`docs/Process-07`（门控分层表）、`contracts/README.md`；`spec/SimRISC-00`、`.tao/contracts/contract-isa.md`、`.tao/contracts/contract-fp.md`（语义真源，仅引用）

> 本 ADR 只记**决策 / 理由 / 被否 / 影响面**，不承载规范正文（`docs/Process-03`）。编码语义仍归 `spec/` 与 `.tao/contracts/contract-*.md`；本 ADR 只定「机器可读编码数据的维护方式」。

## Context（背景）

`contracts/opcodes.yaml` 是 263 条指令的机器可读编码表（`id`/`mnemonic`/`format`/`opc`/`mask`/`value`/`fields`/`scope`/`decode`/`spec_cite`/`legality`/`rule_refs`），由 `tools/spec/generate_opcodes.py` 从 `spec/SimRISC-00` 主表与 `contract-isa.md` 派生。它被大量门控与工具直接消费（现场统计：`tools/`+`tests/`+`idl/` 下 `*.py`/`*.sh` 命中 98 个文件；`Makefile` 22 处），且 `contracts/*.yaml` **无 sha256 锁**（`docs/Process-07` §7.1 缺口分析），防漂移此前只靠多路一致性门控间接兜住。

`ISS-416` 暴露的失效模式是「**只改 yaml、不重跑生成器**」：自 `SPEC-194t` 起若干次改动落在 yaml 侧，`m17-spec-003` 复现出两个历史快照的漂移（`d89810f7` 91 行、`c5cbcbf2` 28 行，**编码字段差异均为 0**，差异只落 `legality`/`rule_refs`），说明漂移来自维护流程而非编码语义。`m17-spec-003` 的处置是：**yaml 为准、修生成器**，并新增 `--check` 与 L1 门控 `check-opcodes-repro`（重渲染 == 入库，逐字节）。收口后 HEAD 上二者零 diff（263 条，md5 `3d0535fffdfc9d09afe4c80f7a702557`，`--check` rc=0）。

该结论命中 `docs/Process-03` 判据：**跨模块需一致**（多门控/多工具消费同一份数据）、**多方案取舍**（yaml 为准 vs 生成器为准、逐字节 vs 字段级、门控 vs 哈希锁）、**结论固化**（长期维护约束）⇒ reviewer 建议立轻量 ADR，由用户确认。

## Decision（决策）

### D1 `contracts/opcodes.yaml` 是**机器可读编码数据真源**（不是语义真源）

- 所有工具/门控读取指令编码时**以该文件为准**，不得各自内嵌第二份编码表。
- 其**语义来源**仍是 `spec/SimRISC-00` 与 `.tao/contracts/contract-isa.md`/`contract-fp.md`：yaml 是这些人读真源的机械投影，**不得**用「yaml 里这么写」反推/替代规范语义（Spec-first 不变）。
- 新增或修改编码时，先定 `spec/`/契约（`Process-06` 保护、需用户授权），**再**落到生成器；yaml 自身不接受直接编辑（见 D2/D4）。

### D2 `tools/spec/generate_opcodes.py` 是**唯一写者**

- `opcodes.yaml` 是**生成物**（含文件头注释、记录顺序、格式）：只由该脚本的写模式产出；**禁手改**（含用 `sed`/`yq`/编辑器局部改、只改注释、只调顺序）。
- 生成器**不读**入库 yaml（`build_records()` 现场派生，`render()` 只做文本渲染）⇒ 不存在「yaml → 生成器」的反向回路。
- 生成器对 yaml 的**全部**文本负责：手改任何字节都会被 D3 判红；`--output` 仅用于把渲染结果写到临时路径做评审，不改「唯一写者」地位。

### D3 L1 `check-opcodes-repro` 是机械判据（渲染 == 入库，逐字节）

- 判定归 `make check-opcodes-repro` → `python3 tools/spec/generate_opcodes.py --check`：重新渲染并与入库文件**逐字节**比较；一致 rc=0，漂移 rc=1（`make` 下 rc=2），读不到对照文件 rc=2（`FAIL`，不静默跳过）。
- **双向哨兵**：① 手改 yaml 不重跑 ⇒ 红（diff 的 `-` 行在入库侧）；② 改生成器表不重跑 ⇒ 红（diff 的 `+` 行在渲染侧）。两条路径在 `m17-spec-003` 均有注入实测（`cp`+md5 还原）。
- 该目标进 L1（`_locked-check` 成员，与 `validate-encoding` 同批），**只防漂移、不证语义**：编码合法性/唯一性/与 `.td`/覆盖矩阵/QEMU 的一致性由 `validate-encoding`/`check-scope`/`check-rule-refs`/`check-fp-contract`/`check-instrinfo`/`check-isa-coverage` 等承担（D5）。
- 门控**不得**被改成「字段级等价」「只比编码字段」「漂移时自动重写 yaml」：后者会把未评审的生成结果直接入库，破坏 D4 的评审步骤。

### D4 修改流程（编码/legality 变更的唯一合法路径）

1. **语义定稿**：在 `spec/`/契约正文定稿（受 `Process-06` 保护；版本号升级须用户认可）；本 ADR 不授权任何 spec 改动。
2. **改生成器**：只改 `generate_opcodes.py` 的表/字段/legality 构造；**不碰**入库 yaml。
3. **重跑生成**：`python3 tools/spec/generate_opcodes.py`（写模式）覆盖 yaml；需要先看结果时用 `--output <临时路径>` 渲染再评审。
4. **评审 diff**：yaml 的每一条差异须能归因到第 1 步的语义变更；**纯格式/顺序/注释差异不接受**（说明渲染逻辑被动过而未说明）；`validate-encoding` 等语义门控与 `check-opcodes-repro` 同批转绿。
5. **同笔提交**：生成器改动与 yaml 重生成必须在同一提交/同一评审单元内；`--check` 红即视为不可提交。
6. **例外处置**：若发现 yaml 与生成器不一致且**无**语义变更需求（历史漏重跑）⇒ 按「生成器为准」重渲染，diff 必须能逐条归因为「上次漏重跑」，不得夹带新编码。

### D5 影响面与消费方边界

- **直接读 yaml 的 L1 门控（16 个，现场派生；扫描脚本见附录 A2）**：`validate-vectors`、`check-asm-list`、`check-asm-prose`、`check-spec-codeblocks`、`check-legality-invariants`、`validate-encoding`、`check-scope`、`check-rule-refs`、`check-fp-contract`、`check-instrinfo`、`check-isa-coverage`、`check-cfx-vectors`、`check-idl-sync`、`check-idl-parse`、`check-spec-cite-targets`、`check-interface`。`check-asm-list-drift`（子进程读取）与 `check-opcodes-repro`（被测主体）**不计入这 16 项**，但同样受 D1–D4 约束。
- **任务书点名的 `check-qemu-forms`**：现场核实为**形态哨兵**（`tools/qemu/semantics_gate.py --form-check`，不读 yaml）⇒ 属**间接**影响面。QEMU 侧直接消费者是 `tools/qemu/validate_decodetree.py`（insn.decode ↔ yaml，当前未单独接线，按需跑）、`check_qemu_trans.py`（由 L1 `check-interface` 调 `--strict`）、`generate_decodetree.py`（派生 decoded 表）；`check-decodetree-repro` 只锁 Makefile recipe + 两 seed 可复现，`check-qemu-forms` 只作形态哨兵——三者均**不读 yaml**。
- **派生/间接消费**（不逐条列全）：`check-asm-list-drift`（子进程跑 `gen_asm_list.py`）、LLVM（`gen_asm_list.py`/`gen_m1_asm.py`/`generate_instrinfo.py`，其中生成器还 import `gen_asm_list.classify` 作「册归属单一真源」）、gem5（`gen_decode_table.py`/`gen_wuming_cycles.py`/`check_b1`–`b7`）、IDL（`idl_exec.py`）、测试与向量生成器（`tests/arch/*`、`tools/qemu/generate_*_vectors.py`、`tools/chipyard/inst_sweep.py`）。
- **字段/schema 变更 = 跨模块变更**：新增/改名/删除 `id`/`opc`/`mask`/`value`/`fields`/`scope`/`decode`/`spec_cite`/`legality`/`rule_refs` 中任一键，须在同一任务内审完全部现场消费者（附录 A3 为准），不得只改生成器；该判定沿用既有 `Process-03` 跨模块判据。
- **不改**：本 ADR 不动 yaml、生成器、`spec/`/契约正文、消费方门控与任何版本号；消费方的历史行为不因本 ADR 改变。

## Rationale（理由）

- **为什么 yaml 为准而不是生成器为准**：yaml 是评审对象与消费接口（现场 98 个 `*.py`/`*.sh` 命中，含直接读取与派生），把编码写进 Python 表会让人工评审退化为审代码常量；但必须能「机器复现 yaml」才能避免两份真相——`m17-spec-003` 两个漂移快照的编码字段差异为 0，证明历史漂移是维护漏跑、不是语义分歧，故修生成器、保留 yaml 为真源，**未改任何编码语义**。
- **为什么逐字节而不是字段级**：实现最小（复用同一 `render()`，无第二套比较器），且能同时锁住字段顺序/注释/格式，避免「字段等价、文本漂移」的双渲染器；与 `check-idl-sync`、`check-asm-list`、`check-asm-list-drift` 的既有「逐字节重生成比对」范式同构（DRY）。
- **为什么进 L1**：门控 hermetic（只读仓库内文件、无 `.work`/安装根依赖）、耗时亚秒级，可每次提交跑；放到 L2/L3 才会让漂移存活到合并前。
- **为什么不用哈希锁文件**：`contracts/*.yaml` 无 sha256 锁是 `Process-07` 已记录的缺口；加锁会引入「改 yaml 还要改锁」的第二个写者与一次人工更新，漂移只是换个地方发生；`--check` 直接由生成器判定，无锁值可漂。
- **为什么 L1 只判漂移**：`validate-encoding` 等已覆盖编码合法性、唯一性、与 `.td`/覆盖矩阵/QEMU 的一致性；重复判定违背单一职责，也让门控更难失败归因。

**被否方案**：

1. **生成器为准、构建时自动重写 yaml**：未评审的生成结果直接入库，评审 diff 消失；构建还会弄脏工作树。
2. **字段级等价（只比 `opc`/`mask`/`value`）**：放过 `legality`/`rule_refs` 与格式漂移，正是 `ISS-416` 两个快照的差异键。
3. **sha256 锁 + 更新脚本**：见上，漂移换位置，且锁值本身无评审语义。
4. **不立 ADR、只留 README/Process-07/docstring 三处散落说明**：`ISS-416` 复发成本已实测（91/28 行、跨 2 个快照），维护约束需要单一可引用落点。

## Consequences（影响）

- **正面**：`opcodes.yaml` 的维护路径唯一；「改表不重跑」「手改 yaml」在 L1 即红；新消费者按 D1 直接读同一份数据，不再产生第二份编码表。
- **约束**：改生成器必须重跑并评审 yaml diff；yaml 的注释/顺序也属生成物，不得手调；`spec/` 语义变更与生成器表改动须同批。
- **风险/边界**：① 门控只证「yaml == 生成器」，**不证生成器表正确**——语义正确性仍由 `spec/` 评审与 `validate-encoding`/`check-fp-contract`/`check-spec-codeblocks` 等承担；② 生成器 import `tools/llvm/gen_asm_list.py` 的 `classify`/`CLASS_TO_SPEC` 作册归属来源，改该模块会连带改 yaml（属 D5 的跨模块变更）；③ `check-scope` 已去计数（`INFRA-102t`），新增记录只受分区不变量约束，不再需要同步常量（`ADR-0032` 背景里的「计数硬编码」已不成立）。
- **后续**：`contracts/wuming-cycles.yaml` 已有同构门控 `check-wuming-cycles`（生成器 + 漂移门控；按需，需 gem5 源树，不入 L1）；通用范式是否落成「一行指针」见「范式落点」段（本 ADR 不改 README/Process-07）。

## 与既有 ADR 的关系

- **`ADR-0019`（重定位类型）**：其决策对象是 ELF 重定位编号/公式（`e_flags[7:0]=1` namespace），**不在** `contracts/opcodes.yaml` 内，本 ADR 不重复、不修订、不扩展到重定位数据；若将来重定位表也做成机器可读 yaml，可复用 D1–D4 的维护范式，但须另立 ADR 决定其真源与门控。
- **`ADR-0032`（`ext` 迁出/`shl` 迁入/新增 `rol`）**：其 D1–D6 的**编码决定原样有效**，本 ADR 不复述、不改写；本 ADR 只固定「这类编码再分配（及 `ADR-0034`/`ADR-0044` 等编码决定）落地时**必须走 D4 流程**：改生成器表 → 重跑 → 评审 yaml diff → L1 同批转绿」。`ADR-0032` 背景事实 6 提到的 `check_scope.py` 计数硬编码属当时状态，现由 `check-scope` 去计数（`INFRA-102t`）取代，本 ADR 不追溯修改该 ADR 原文。
- 本 ADR **不产生**任何 `Superseded`/`Revised`：两份 ADR 的决策均继续有效。
- **归属（2026-11-25 已定，reviewer 结论）**：本主题**独立新开 ADR-0063**，**不并入** `ADR-0032`；两者决策互不覆盖（0032 定编码值，0063 定机器数据的维护路径）。

## 范式落点（2026-11-25 已定，reviewer 结论）

「生成物单一写者 + `--check` 逐字节」**暂不另立通用 ADR**：现仅 `opcodes.yaml`（L1）与 `wuming-cycles.yaml`（按需）两例，通用化收益未到 ADR 门槛。若需通用化，只在 `contracts/README.md` 与 `docs/Process-07` 的表/原则各加**一行指针**（指向本 ADR 的 D1–D4），不新增门控、不改现有消费方；该一行改动留给后续任务，本 ADR 不改 README。

## 待裁定（用户）

1. **D1–D5 逐条确认**后由主会话置 `Accepted`；未确认前保持 `Candidate`，实施任务不得据此开工。

## 附录 A：影响清单（2026-11-24 起草、2026-11-25 复核；HEAD `c79207e5`）

> 计数为现场 `grep`/实跑所得，只作面量参考；消费方清单以现场为准，不写死。行号对应本 ADR 起草时的 HEAD。

**A1 生成器与门控落点**

- `tools/spec/generate_opcodes.py`（1082 行）：`build_records()` L1006（现场派生，注释明写「不读 opcodes.yaml」）、`render()` L1021（写盘与 `--check` 共用，注释「禁两套渲染」）、`main()` L1047（`--check` 逐字节比较；漂移 rc=1、读不到对照文件 rc=2）；docstring L35–39 记「单一写者」。
- `Makefile`：目标 `check-opcodes-repro` L1885–1886（调 `--check`）；L1150 `_locked-check` 成员（= L1）；L311 help 行。
- `docs/Process-07-门控分层规范.md`：门控表 L315 行（判据/来源/边界「只防 yaml 手改/漏重跑」）；L340 记 `contracts/*.yaml` 无 sha256 锁、靠一致性门控兜底（本 ADR 的 D3 补上逐字节锁）。
- `contracts/README.md` L9：`opcodes.yaml` 行注明「生成物：只由 `tools/spec/generate_opcodes.py` 产出；`make check-opcodes-repro` 逐字节守漂移，禁手改」。
- 现场实跑：`generate_opcodes.py --check` rc=0，263 条（M1 156 / fp 65 / excluded 0 / m3 1 / m8 7 / m9 34；有 `rule_refs` 246），md5 `3d0535fffdfc9d09afe4c80f7a702557`。

**A2 直接读取 yaml 的 L1 门控（16 项，现场派生）**

> 判据：L1（`_locked-check`）目标的 recipe 脚本中，**进程内**出现 `opcodes.yaml`/`OPCODES` 引用且含 `safe_load`/`yaml.load`/`read_text` 读取。现场扫描脚本：运行期证据目录内的 `scan_l1_yaml_readers.py`（输出 16 项并与本清单逐项比对，多/少均 FAIL）。

- `validate-vectors` → `tools/testcases/validate_vectors.py`（L106–L111 `load_opcodes`（`safe_load`）、L192 路径）
- `check-asm-list` → `tools/spec/check_asm_list_consistency.py`（L47 `yaml.safe_load(OPCODES.read_text())`）
- `check-asm-prose` → `tools/spec/check_asm_prose.py`（L105/L112、L355/L359 两处 `safe_load`）
- `check-spec-codeblocks` → `tools/spec/check_spec_codeblocks.py`（`_load_opcode_formats()` 经 `check_asm_prose` 进程内读取；L238 读不到即 fail-closed）
- `check-legality-invariants` → `tools/spec/check_legality_invariants.py`（11）
- `validate-encoding` → `tools/spec/validate_encoding.py`（2）
- `check-scope` → `tools/spec/check_scope.py`（8）
- `check-rule-refs` → `tools/spec/check_rule_refs.py`（6）
- `check-fp-contract` → `tools/spec/check_fp_contract.py`（6）
- `check-instrinfo` → `tools/llvm/validate_instrinfo.py`（18）
- `check-isa-coverage` → `tools/llvm/gen_isa_coverage.py`（5）
- `check-cfx-vectors` → `tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`（5）
- `check-idl-sync` → `idl/tools/idl_render.py`（7）
- `check-idl-parse` → `idl/tools/idl_parser.py`（9；`OPCODES_REL` + `read_text` 文本对账）
- `check-spec-cite-targets` → `tools/spec/check_spec_cite_targets.py`（glob `contracts/*.yaml` 后逐行读 `spec_cite`，含 `opcodes.yaml`）
- `check-interface` → `tools/infra/check_interface_alignment.py`（L713 读 `opcodes.yaml`；并调 `check_lit_bytes`/`check_qemu_trans --strict`）

**A2b 不计入 16 项但受同一约束的读点**

- `check-asm-list-drift`：子进程调用 `tools/llvm/gen_asm_list.py` 读取（非进程内读点），yaml 漂移同样会使其红。
- `check-opcodes-repro`：被测主体本身（读入库 yaml 做逐字节比对），不是消费方。

**A3 派生/间接消费（面量，不逐条列全）**

- QEMU：`tools/qemu/validate_decodetree.py`（7，按需）、`check_qemu_trans.py`（6，经 `check-interface` 调 `--strict`）、`generate_decodetree.py`（10，派生）；`semantics_gate.py --form-check` **0** 处读 yaml（形态哨兵），`check_decodetree_repro.py` 也不读 yaml（只锁 recipe + seed）。
- LLVM：`tools/llvm/gen_asm_list.py`（6；生成器 import 其 `classify`/`CLASS_TO_SPEC`）、`gen_m1_asm.py`（7）、`generate_instrinfo.py`。
- gem5：`tools/gem5/gen_decode_table.py`（22）、`gen_wuming_cycles.py`（7）、`check_b1`–`b7`/`check_converge`/`refresh_matrix_notes.py`。
- IDL：`idl/tools/idl_exec.py`（9）等。
- 测试/向量：`tools/qemu/generate_{atomics,rol}_vectors.py`、`tools/chipyard/inst_sweep.py`、`tests/arch/**/check_*.py`。
- 全仓面量：`tools/`+`tests/`+`idl/` 的 `*.py`/`*.sh` 命中 `opcodes.yaml` 共 **98** 个文件；`Makefile` 命中 **22** 处。

**A4 明确不改**

- 本 ADR 不改 `contracts/opcodes.yaml`、`tools/spec/generate_opcodes.py`、`spec/`、`.tao/contracts/` 正文、消费方门控与任何版本号；不改 `adr-0019`/`adr-0032` 原文；不改 `.tao/knowledge/` 台账与 `contracts/README.md`（既有说明保留为规范正文引用）。

## 状态说明

2026-11-24 由 `m17-spec-004` 起草为 `Candidate`（触发：`m17-spec-003` reviewer 按 `docs/Process-03` 判据——跨模块一致、多方案取舍、结论固化——建议立轻量 ADR）。本 ADR 只固化五条长期约束：D1 yaml 为机器数据真源（非语义真源）、D2 生成器唯一写者、D3 L1 逐字节门控、D4 修改流程、D5 影响面。

2026-11-25 返工（reviewer Needs Revision）：D5/附录 A2 的直接消费者漏列 4 个（`validate-vectors`/`check-asm-prose`/`check-interface`，且 `check-asm-list` 误标「间接」）⇒ 已按现场扫描改为 **16 项**（`check-asm-list` 直接 `safe_load`；`check-asm-list-drift`/`check-opcodes-repro` 移入 A2b 说明不计入），并新增扫描脚本与 ADR 集合的逐项比对（多/少均 FAIL）。同日按 reviewer 结论固化：**独立新开 0063、不并入 `ADR-0032`**；通用范式**不另立 ADR**，需要时只在 `contracts/README.md`/`docs/Process-07` 各加一行指针（本任务不改 README）。

D1–D5 **未经用户逐条确认前保持 `Candidate`**；确认后由主会话置 `Accepted`，实施类任务不得据此开工。本 ADR 不承载规范正文，不改任何 yaml/生成器/`spec/` 内容与版本号。
