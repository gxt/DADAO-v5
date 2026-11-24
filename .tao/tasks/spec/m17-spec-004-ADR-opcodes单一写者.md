# m17-spec-004: ADR——`opcodes.yaml` 单一写者与生成一致性

**模块**：spec
**项目里程碑**：M17
**依赖**：`m17-spec-003`（门控已落）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景

`m17-spec-003` 收口了 `generate_opcodes.py` 与 `contracts/opcodes.yaml` 的漂移，并新增 L1 `check-opcodes-repro`（重渲染 == 入库 yaml 逐字节）。reviewer 按 `Process-03` 判据（跨模块一致、多方案取舍、结论固化）建议立轻量 ADR，记录「yaml 为机器数据真源、生成器为唯一写者」的长期约束。

## 要做

1. 新增 `.tao/adr/adr-0063-*.md`（编号 0063；状态 `Candidate`）：
   - D1 `contracts/opcodes.yaml` 是机器可读**真源**；
   - D2 `tools/spec/generate_opcodes.py` 是**唯一写者**（禁手改 yaml）；
   - D3 L1 `check-opcodes-repro` 是机械判据（渲染 == 入库）；
   - D4 修改流程：改生成器 → 重跑 → 评审 diff；`--check` 失败即红；
   - D5 影响面：`validate-encoding`/`check-instrinfo`/`check-qemu-forms`/`check-isa-coverage` 等消费方；
2. 在 `ADR` 中注明与 `ADR-0019`（重定位）/`ADR-0032`（编码重分配）等既有 ADR 的关系（不重复其决策）。

## 不做

- 不改 yaml/生成器/spec 正文；不升版本号；
- 不批量改消费方门控。

## 约束

- 独立 `git worktree`；不提交 git；只新增 ADR + 本任务书；完成区 ≤30 行。

## 验证

1. ADR 存在、`Candidate`、D1–D5 完整；
2. 文中引用的门控/文件现场 `grep` 存在；
3. 不产生 yaml/生成器改动（`git status` 仅 ADR + 任务书）。

## 待裁定（用户）

- D1–D5 逐条确认后转 `Accepted`（唯一待裁定项；「是否并入 `ADR-0032`」已按 reviewer 2026-11-25 结论定为**独立新开 0063**，见 ADR「与既有 ADR 的关系」）；
- 「生成物单一写者」通用范式**不另立 ADR**（reviewer 2026-11-25 结论），需要时只在 `contracts/README.md` 与 `docs/Process-07` 各加一行指针（本任务不改 README）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-24）

改动 = 新增 ADR + 本任务书；逐行审查 ADR 的事实性/边界后处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书 D5 点名 `check-qemu-forms`，但现场核 `semantics_gate.py` 0 处读 yaml（是形态哨兵） | ✅已修 | D5 把它改标「间接影响面」，并列 QEMU 侧直接消费者（`validate_decodetree.py`/`check_qemu_trans.py`） | `grep -c opcodes tools/qemu/semantics_gate.py` = 0；上述两脚本命中 7/6 |
| F2 `ADR-0032` 背景「`check_scope.py` 计数硬编码」已被 `check-scope` 去计数取代（`INFRA-102t`） | ✅已修 | 「与既有 ADR 的关系」注明现状态、不改 ADR-0032 原文 | `check_scope.py` docstring 明写「无写死计数（INFRA-102t）」 |
| F3 ADR 内 md5/行号会随 HEAD 变化 | ✅已修 | 附录 A 标注 HEAD `c79207e5` + 「现场核实」口径；证据脚本 C17 动态比对 md5、C16 实跑 `--check` | `run.sh` C16/C17 PASS；`--check` rc=0（263 条） |
| F4 ADR 若含 assembly 代码块会被 `check-asm-prose` 扫 | ✅已修 | 全文不用 fenced 代码块（只行内 backtick + 列表） | `check_asm_prose.py --strict` rc=0；本文件命中 0 |
| F5 完成区若写具体 `.work/**` 路径会触 `check-knowledge-refs` | ✅已修 | 统一写「运行期证据目录内的 `run.sh`」 | 全文 `grep '\.work/'` 0 命中 |
| F6 任务书改 `待验收` 与台账表位置映射（本 worktree 台账快照仍在「待开始」表） | ❌不修（非本代理职责） | 不改台账 | 主工作树 `milestones-m17.md` L37 已在「进行中」（派单 2026-11-24 23:48），合入后映射一致 |
| F7 附录 A1 把生成器 docstring 单一写者段写成 L46–50（实为 L35–39） | ✅已修 | 改 L35–39 | `grep -n '单一写者（ISS-416 收口）'` 命中 L35 |
| F8 `Process-07 §7` 实为 `§7.1`；且把 `check-decodetree-repro` 误述为内容一致性哨兵 | ✅已修 | 改 `§7.1`；D5/A3 改写为「`validate_decodetree` 按需 / `check_qemu_trans` 由 `check-interface` 调 `--strict` / 两个哨兵均不读 yaml」 | `check_decodetree_repro.py` 0 处 opcodes；`check_interface_alignment.py` L788 调 `check_qemu_trans --strict` |

**判决**：finding 已全部处置（F6 属主会话职责），置 `待验收`。

### 第 2 轮 engineer 自审（2026-11-25，返工）

**reviewer 阻断（唯一）**：D5/附录 A2「直接读 yaml 的 L1 门控」漏 4 个、`check-asm-list` 误标「间接」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 A2/D5 漏 `validate-vectors`/`check-asm-prose`/`check-interface`，`check-asm-list` 误标间接 | ✅已修 | A2 改为 **16 项**（每项一 bullet，带脚本与读点行号）；D5 首条同步 16；新增 A2b 说明 `check-asm-list-drift`（子进程读）与 `check-opcodes-repro`（被测主体）不计入 | 运行期证据目录内 `scan_l1_yaml_readers.py`：L1 脚本 57、直接读点 **16**、与 A2 逐项一致（rc=0） |
| R2 归属/范式未落 reviewer 结论 | ✅已修 | 「与既有 ADR 的关系」增「归属（2026-11-25 已定）：独立新开 0063、不并入 0032」；新增「范式落点」段（不另立通用 ADR，需要时 README/Process-07 各一行，本任务不改 README）；待裁定收敛为 D1–D5 确认 | `grep -n "归属（2026-11-25"` 命中；待裁定仅 1 项 |
| R3 证据脚本未覆盖 16 项计数与集合比对 | ✅已修 | `run.sh` C13 扩到 25 个脚本；新增 C22（调扫描器比对 ADR 集合）与 P11 反例（删 A2 一条 ⇒ FAIL） | `run.sh` 26/26 PASS；`--inject` 15 条探针全按预期 FAIL 后回绿 |

**判决**：阻断项已修、证据可复算；状态保持 `待验收`。

### 第 1 轮 reviewer 复核（2026-11-25）

- **重跑**（仓库根执行运行期证据目录内的 `run.sh`）：正检 PASS 25 / FAIL 0（rc=0）；`--inject` = 正检 25 + 14 探针 + 回绿 25，PASS 64 / FAIL 0（rc=0），14 条探针逐条 `rc=1` 按预期失败。
- **独立注入**（改被测产物、同一脚本重跑）：① ADR 状态 `Candidate→Accepted` → C02 FAIL（rc=1，汇总 FAIL=1）→ `cp`+md5 还原（`073cfb85…` 相等）→ 回绿 25/25 rc=0；② `opcodes.yaml` 注入 1 字节漂移 → `--check` rc=1、`make check-opcodes-repro` rc=2（diff `-` 行在入库侧）→ 还原 md5 `3d0535ff…` 回绿 rc=0；③ 移走 yaml → `--check` rc=2 → 还原 rc=0。
- `python3 tools/spec/generate_opcodes.py --check` rc=0（263 条，md5 与 ADR 一致）。
- **交付物零改动**：`git diff -- contracts/opcodes.yaml tools/spec/generate_opcodes.py` 空；`git status -uall` 仅 ADR + 本任务书，与注入前快照逐行一致。
- **约束核验**：状态 `Candidate` ✓；D1 明确「不是语义真源」✓；D2–D4 与 `m17-spec-003` 实现一致（生成器 docstring L35–39、`build_records` L1006/`render` L1021/`main` L1047、Makefile L1885–1886 与 `_locked-check` L1150、Process-07 L315、`contracts/README.md` L9 现场均命中）✓；ADR-0019（`e_flags[7:0]=1` 重定位）/ADR-0032（ext/shl/rol；其背景 6「`check_scope.py` 计数硬编码」现为 `INFRA-102t` 无写死计数）关系表述准确、不重复决策，ADR-0034/0044 存在 ✓。
- **面量复验**：全仓 `*.py`/`*.sh` 命中 `opcodes.yaml` = 98 文件 ✓、Makefile 22 处 ✓；A2 已列 12 条的命中数（2/8/6/6/18/5/3/7/1/11/7+9/5）逐条与现场一致 ✓。
- **阻断项**：D5/附录 A2「直接读 yaml 的 L1 门控」**漏列 4 个**——`validate-vectors`（`tools/testcases/validate_vectors.py` L192 加载）、`check-asm-prose`（`tools/spec/check_asm_prose.py` L105/L355 `safe_load`）、`check-interface`（`tools/infra/check_interface_alignment.py` L713 `safe_load`）、`check-asm-list`（`tools/spec/check_asm_list_consistency.py` L47 直接 `safe_load(OPCODES.read_text())`，ADR 误标「间接」，`OPCODES` 常量仅定位路径）；四者均在 `_locked-check`（L1150）。现场直接读 yaml 的 L1 门控 = **16 个**（ADR 写 12）。修法：A2 补 3 条 + 改标 `check-asm-list`、D5 首条同步、计数改 16。
- 其余无阻断：证据脚本每类断言均有可达 FAIL 路径、无恒真/两支同果；ADR 无 `.work` 引用、无 fenced 代码块。
- **建议（不实施）**：① **新开 0063 正确**——ADR-0032 决策对象是具体编码再分配，「单一写者」是跨数据文件的维护约束，并入会混决策对象、且被 ADR 决策版本稀释；② 「生成物单一写者 + `--check`」**值得提炼但暂不立 ADR**：现仅 `opcodes.yaml`/`wuming-cycles.yaml` 两例、无多方案分歧（不满足 `Process-03` 结论固化判据），先在 `contracts/README`/`Process-07` 加一行约束，第三例出现再立。
- **判决：Needs Revision**（唯一阻断 = A2/D5 直接消费者漏列，见上；其余全部核验通过）。

### 第 2 轮 reviewer 复核（2026-11-25）

- **阻断项复验**：D5 首条与附录 A2 均为 **16 项**，含 `validate-vectors`/`check-asm-prose`/`check-interface`，`check-asm-list` 已由「间接」改「直接读」（`check_asm_list_consistency.py` L47 `safe_load(OPCODES.read_text())`）；我自跑扫描脚本（从 Makefile `_locked-check` 现场取目标、现场判读点）= 16，与 ADR A2 逐项一致 rc=0。
- **A2b 排除合理**：`check_asm_list_drift.py` 进程内只有 `OPCODES.exists()`、无 `safe_load`/`read_text`（内容读在子进程 `gen_asm_list.py`）；`check-opcodes-repro` 是被测主体——两者仍受 D1–D4 约束并列在 A2b，非漏列。
- **重跑**：运行期证据目录内 `run.sh` = **PASS 26 / FAIL 0（rc=0）**；`--inject` = 正检 26 + **15 条探针**（P01–P11、P03×5，含新增 P11 扫描器反例）逐条按预期 FAIL + 回绿 26 → **PASS 67 / FAIL 0（rc=0）**。
- **独立注入**（改被测产物、同一脚本）：删 A2 中 `check-interface` 一条 → C22 FAIL（rc=1，汇总 FAIL=1）→ `cp`+md5 还原（`855fce8a…` 相等）→ 回绿 26/26 rc=0。
- **行号抽核 4 条**：`validate-vectors` L106–111 `load_opcodes` + L192 路径 ✓；`check-asm-list` L47 ✓；`check-asm-prose` L105/L112、L355/L359 ✓；`check-interface` L713 ✓（另核 `check-spec-cite-targets` L147 glob + L161 `read_text` 真读）。
- **零改动**：`git diff -- contracts/opcodes.yaml tools/spec/generate_opcodes.py` 空（rc=0），yaml md5 `3d0535ff…`；`git status -uall` 仅 ADR + 任务书；ADR 仍 `Candidate`。
- **归属段已写**：「与既有 ADR 的关系」含归属（独立新开 0063、不并入 ADR-0032）；新增「范式落点」段写明通用范式**暂不另立 ADR**、只留一行指针、本任务不改 README。
- **判决：Accepted**（唯一阻断项已修复；其余核验无新问题）。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` = **PASS 26 / FAIL 0（rc=0）**；`--inject` = 正检 PASS → **15** 条逐类探针全按预期 FAIL → 回绿 PASS（rc=0，合计 67 PASS）；扫描器 `scan_l1_yaml_readers.py` rc=0。
**修改文件**：`.tao/adr/adr-0063-opcodes-single-writer.md`（A2 12→16 + A2b + D5 同步 + 归属/范式 + 状态说明）；本任务书（返工审阅 / 完成区）。运行期证据脚本在运行期证据目录内，不入库。
**验收结果（16 现场证据）**：`python3 <运行期证据目录>/scan_l1_yaml_readers.py` → `直接读 opcodes.yaml 的 L1 门控（现场派生）: 16` / `ADR A2 列出的脚本数: 16` / `PASS: 16 个直接读点，与 ADR-0063 A2 完全一致`；16 项 = `idl_parser`、`idl_render`、`validate_cfx_vectors`、`check_interface_alignment`、`gen_isa_coverage`、`validate_instrinfo`、`check_asm_list_consistency`、`check_asm_prose`、`check_fp_contract`、`check_legality_invariants`、`check_rule_refs`、`check_scope`、`check_spec_cite_targets`、`check_spec_codeblocks`、`validate_encoding`、`validate_vectors`。`git status` 仍仅 ADR + 任务书；yaml/生成器零改动（C16–C19）。
**新发现/坑**：① 「直接读」口径须区分进程内读取、子进程（`check-asm-list-drift`）与被测主体（`check-opcodes-repro`），否则计数会在 16/17/18 间摇摆——ADR A2b 已单列；② `check-spec-cite-targets` 以 `contracts/*.yaml` glob + 文本扫描读取 opcodes.yaml，单纯 `safe_load/OPCODES` grep 会漏，扫描器用「引用 + 读取调用」双条件兜住；③ 本 worktree 台账快照早于派单记账（主树 HEAD `4d7a0d30` 已把本任务移入「进行中」），`check-milestones-fresh` 在本树唯一 VIOLATION 是该快照 A1，主树同门控 PASS（已实测），合入后台账取自主树。
**遗留问题**：仅 D1–D5 待用户逐条确认（归属与范式已按 reviewer 2026-11-25 结论固化）；无实现/门控缺口。
