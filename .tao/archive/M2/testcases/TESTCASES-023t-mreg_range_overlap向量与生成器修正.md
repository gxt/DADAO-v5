# TESTCASES-023t: `mreg_range_overlap` 向量与生成器修正（同组重叠 ⇒ ILLI）

**模块**：testcases
**项目里程碑**：M2
**依赖**：`SPEC-088t`（规范/合约层修复，**须先 `已验证`**）。相关：`contracts/legality_rules.yaml`（`mreg_range_overlap`）、`.tao/knowledge/contract-isa.md`（`SPEC-088t` 修正后的块赋值重叠条）、`tests/vectors/isa/reg-imm-block.yaml`、`tools/testcases/{generate_isa_vectors.py,009t-audit.py,validate_vectors.py}`、`tests/vectors/inventory.md`。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景

- 用户裁定：`mreg_range_overlap`（`active`/`static`）当前是「纸面规则」；同组块赋值 `rd2rd`/`rb2rb` 的源/目的范围有交集（含完全重合）⇒ ILLI。
- **架构师实测发现（本任务直接动因）**：`tests/vectors/isa/reg-imm-block.yaml` 现存同组重叠用例是 **`class: overlap` + `expected_fault: null` + 顺序语义期望值**，与规则**直接相违**：
  - `rd2rd_orri_rd`，word `0x40B03082`（`rd2..3 → rd3..4`，count=2，部分重叠），notes「sequential semantics: dst overlaps src → dst[1] reads dst[0]'s new value」；
  - `rb2rb_orri_rb`，word `0x40D03082`，同型。
- 生成器 `tools/testcases/generate_isa_vectors.py::gen_block_overlap`（L1121–1199）对同组分支同样产出「顺序语义」期望值。跨组四例（`rd2ra`/`ra2rd`/`rd2rb`/`rb2rd`）结构性不重叠，**保持不变**。
- 本任务修正数据与生成器；QEMU/LLVM 实现归 `QEMU-033t`/`LLVM-028t`。

---

## 1. 事实核实（本轮 architect 实测；执行时以重跑为准）

1. `tests/vectors/isa/reg-imm-block.yaml` 六条块赋值各有 1 条 `class: overlap`：`rd2rd`(L397)、`rd2ra`(L469)、`ra2rd`(L555)、`rb2rb`(L627)、`rd2rb`(L699)、`rb2rd`(L771)。其中同组两条（`rd2rd`/`rb2rb`）为**顺序语义**、`expected_fault: null`。
2. `tools/testcases/validate_vectors.py` L425–434：`class: overlap` 允许 `expected_fault ∈ {null, "ILLI"}` ⇒ 改成 `ILLI` **通过 schema**；`inventory.md` L108–113 的 `overlap ✓` 仍由该 `overlap` 类用例满足（无需改 inventory）。
3. 生成器写全量文件（L1469–1478 遍历 `FILE_MAP`）⇒ 重跑须确保 **仅 `reg-imm-block.yaml` 有 diff**。
4. `tools/testcases/009t-audit.py`：L1150–1151 只重算「active semantic/boundary/overlap **且无 fault**」的用例 ⇒ 改成 `expected_fault: "ILLI"` 后应被跳过，不参与重算（须实测确认）。
5. `tests/vectors/README.md` 未记载同组重叠的顺序语义，无需改。

---

## 2. 设计

### 2.1 生成器修正（`tools/testcases/generate_isa_vectors.py::gen_block_overlap`）

- **同组分支**（`mnem in ("rd2rd","rb2rb")`）：改为产出**非法**用例——
  - `class: overlap`，`expected_fault: "ILLI"`，`expected_state: null`，`expected_pc: null`；
  - notes 改为 `overlap <mnem>: <dst>… ↔ <src>… 范围有交集（含部分/完全重合）→ ILLI (mreg_range_overlap)`；
  - 保留 word（如 `0x40B03082`/`0x40D03082`）与 `input_state`（便于固定身份）；不再计算 `final_vals` 顺序语义。
- **跨组分支**（`rd2ra`/`ra2rd`/`rd2rb`/`rb2rd`）：保持 `expected_fault: null` + 语义期望（结构性不重叠），仅按 §2.3 收紧 notes。
- 建议同时为同组分支补一条**完全重合**用例（如 `rd2rd {rd3:rd3}, {rd3:rd3}`，count=1 → ILLI；`rb2rb` 同型），使「含完全重合」在数据层可见（可选，若加入须同步 inventory/覆盖语义）。

### 2.2 向量重生成
- 重跑生成器，产出 `tests/vectors/isa/reg-imm-block.yaml` 新内容；**核对其余文件零 diff**。
- 同组两条的 `expected_fault` 由 `null` 变 `ILLI`、`expected_state` 由字典变 `null`、notes 更新；跨组四条**逐字节不变**。

### 2.3 溯源与注释同步
- `gen_block_overlap` 的 docstring/注释（L1121–1127）删除「Sequential semantics (contract-isa.md:467)」的错误引用（`SPEC-088t` 已修正 contract-isa 的块赋值重叠条；同组重叠**不可**用顺序语义）。
- 视需要更新 `reg-imm-block.yaml` 相关 `spec_cite` 指向 `SimRISC-02 §寄存器组之间块赋值; SimRISC-07 …`（仅当原先缺失）。

### 2.4 审计脚本
- 确认 `009t-audit.py` 对含 `expected_fault` 的 `overlap` 用例**跳过重算**；若仍尝试重算/报 mismatch，须最小修正其过滤条件（只碰本任务相关分支，勿改其它逻辑）。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `tools/testcases/generate_isa_vectors.py` | `gen_block_overlap` 同组分支出 ILLI（+ 注释/引用修正） |
| 2 | `tests/vectors/isa/reg-imm-block.yaml` | 重生成（同组两条 → ILLI；跨组不变） |
| 3 | `tools/testcases/009t-audit.py` | 必要时过滤 `overlap`+fault 用例 |
| 4 | `.work/evidence/TESTCASES-023t/run.sh` | 一键证据脚本（含注入自检） |
| 5 | `.work/log/testcases/TESTCASES-023t-*.log` | 验证留证 |

**明确不改**：`contracts/opcodes.yaml`、`tests/vectors/inventory.md`（若加完全重合用例而影响覆盖，须单独说明并最小更新）、`tools/{spec,llvm,qemu}/**`、`components/**`、其它 `isa/*.yaml`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `.tao/knowledge/contract-isa.md`（`SPEC-088t` 修正后的块赋值重叠条）、`contracts/legality_rules.yaml`（`mreg_range_overlap`）
- `tests/vectors/isa/reg-imm-block.yaml`、`tools/testcases/{generate_isa_vectors.py,009t-audit.py,validate_vectors.py}`、`tests/vectors/inventory.md`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围；**失败即停，禁自动重试**。
- 临时目录 `/tmp/opencode/TESTCASES-023t/`；日志 `.work/log/testcases/`；证据 `.work/evidence/TESTCASES-023t/`。
- **数据级独立重算**：同组重叠判定须按 `[hb, hb+immu6) ∩ [hc, hc+immu6) ≠ ∅` **逐条独立重算**（不抽样），不得以 validator 绿灯为唯一判据。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **数据修正**：`reg-imm-block.yaml` 中 `rd2rd`/`rb2rb` 的 `class: overlap` 用例 `expected_fault == "ILLI"`、`expected_state == null`；跨组四例仍 `null` + 语义期望；逐条独立重算重叠判定，**0 mismatch**。
2. **覆盖不变**：`validate-vectors` → `152/152`、gaps 0、EXIT 0；`inventory.md` 的 6 条块赋值 `overlap ✓` 仍成立（数据级覆盖门控无新缺口）。
3. **生成器幂等/可复现**：重跑生成器后 `git diff` **仅** `reg-imm-block.yaml`；再次重跑逐字节不变（幂等）。
4. **审计不回归**：`python3 tools/testcases/009t-audit.py` 对同组重叠用例**不计为错值**（跳过或匹配），0 mismatch（留证）。
5. **反例可失败**：注入「把 `rd2rd` 重叠用例改回顺序语义（fault=null）」⇒ 证据脚本的语义断言 FAIL；还原 ⇒ 回绿。注入用 `git diff --name-only` 证非空。
6. **与实现一致**（若 `QEMU-033t` 已落地）：同组重叠编码经 QEMU 执行得 ILLI 0x88（可由 `QEMU-033t` 探针证据呼应；本任务不用 QEMU 生成期望值）。
7. **`make check` 全绿**：`repository checks: PASS`。
8. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书）；`check-no-residue` PASS。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-023t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律（本任务不改补丁，不适用）。
7. 复杂命令输出留存 `.work/log/testcases/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/TESTCASES-023t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

- 同组重叠的「顺序语义」用例是 `TESTCASES-011t` 遗留（早于/同期于 `mreg_range_overlap` 生效），本任务将其中「合法语义」改为「非法」——属**修正错值**（AGENTS：错值当场修）。
- 是否额外补「完全重合」用例（§2.1）为可选，加入后须同步覆盖语义；建议加入（裁定 5 明确「含完全重合」）。
- 若用户裁定 `QEMU-033t` 或 `LLVM-028t` 不做，本任务数据仍应修正（合约已禁重叠），但其端到端证据相应减弱。

## 完成区

**测试结果**：全部通过。
- 生成器（scoped）`python3 tools/testcases/generate_isa_vectors.py reg-imm-block.yaml` EXIT=0（48 cases / 13 identities）；连跑两次 sha256 `2336e6b1…` 逐字节不变（幂等），且 `git diff --name-only -- tests/vectors/isa` 仅 `reg-imm-block.yaml`。
- `validate_vectors.py` EXIT=0：`152/152 M1 identities covered OK (inventory sync OK; 15 data files, 694 cases; data coverage gaps: 0)`（694 = 原 692 + 2 条完全重合用例）。
- 独立重算（`.work/evidence/TESTCASES-023t/check_overlap.py`，逐条按 `[hb,hb+immu6) ∩ [hc,hc+immu6) ≠ ∅` 从编码字段派生）：**14 条块赋值 semantic/overlap 用例全部重算，0 mismatch**；C1（部分重叠）、C2（完全重合）、C3（跨组不重叠对照）全 PASS。
- `009t-audit.py`：最终 mismatch 集与 HEAD **逐行相同**（18 条 pre-existing，见「遗留问题」），**0 条 `reg-imm-block` mismatch**；同组重叠用例（fault=ILLI）按 L142 被跳过、不计为错值。

**修改文件**：
- `tools/testcases/generate_isa_vectors.py`：重写 `gen_block_overlap`（同组 ⇒ ILLI、删顺序语义期望值、订正 docstring 误引 `contract-isa.md:467`）；新增 `gen_block_overlap_complete`（完全重合用例）；`generate_file` 追加调用；为消除**预存漂移**使生成器忠实复现已提交 reg-imm-block（RA 两条 `spec_cite`）并新增可选文件名过滤（scoped 重生成）。diff +67/−29
- `tests/vectors/isa/reg-imm-block.yaml`：重生成。`rd2rd`/`rb2rb` 部分重叠两条 `expected_fault: null→ILLI`、`expected_state: 字典→null`、notes 更新；各新增 1 条完全重合用例（`0x40B030C1`/`0x40D030C1`）；跨组四条（`rd2ra`/`ra2rd`/`rd2rb`/`rb2rd`）**逐字节不变**。
- `tools/testcases/009t-audit.py`：块赋值重算分支的过滤判据由 `insn`（完整 id）改为 `mnemonic`（原判据因 TESTCASES-017t 的 `insn→id` 改名恒不命中、为死代码），并同步 `bank_map` 键与过时注释。
- `.work/evidence/TESTCASES-023t/run.sh`、`check_overlap.py`（证据脚本，`.work/` 已 gitignore）。
- `.work/log/testcases/TESTCASES-023t-*.log`（留证）。

**验收结果**（真实命令 + 退出码；每项「期望/实际」）：
1. 生成器 EXIT=0 且幂等 / 仅 reg-imm-block diff —— `run.sh` E1 PASS。
2. 重叠用例字段：`rd2rd 0x40B03082`、`rb2rb 0x40D03082` → `expected_fault=ILLI`、`expected_state=null`；完全重合 `0x40B030C1`/`0x40D030C1` → ILLI —— `check_overlap.py` C1/C2 PASS。
3. 跨组四条仍 `fault=null` + 语义期望 —— C3 PASS（4/4）。
4. 独立重算逐条 0 mismatch —— C4 PASS（14/14）。
5. `validate_vectors.py` EXIT=0（152/152，gaps 0）—— E2 PASS。
6. 反例注入（`--inject`：把 `rd2rd` 部分重叠改回「顺序语义」= `fault=null` + 旧 `expected_state` 字典）⇒ 语义断言 FAIL（C1/C4），还原 sha 一致后回绿 —— E3 `--inject` PASS。
   - 附实测：该反例**变体 A**（fault=null、state=null）validator EXIT=0（仅结构校验）、audit 判出 2 条 reg-imm-block mismatch；**变体 B**（fault=null + 旧顺序 state）validator EXIT=0、audit **也判不出（0 mismatch）**，仅本任务独立重算判出 —— 故 `--inject` 采变体 B，验证独立 oracle 的必要性（「覆盖≠语义」）。
7. `make check` EXIT=0（`repository checks: PASS`；`check_issues 0 blocking`）—— E5 PASS。
8. 残留：`git status --untracked-files=all` 仅 3 个应改文件；无 `*.bak/*.orig/*.rej`；`check-no-residue` 随 make check 通过。

**新发现/坑**：
1. **生成器↔向量预存漂移使「全量重跑」不安全**（`deferred.md` 已登记）：`generate_isa_vectors.py` 全量跑会改 5 文件——`reg-arith.yaml` 删 834 行（SPEC-066t div/rem 定值块）、`reg-compare/logic/shift-extend` 多处、`reg-imm-block` 3 行 `spec_cite`。任务书 §1.3 假设「其余文件零 diff」不成立。处置：修生成器使 reg-imm-block 忠实复现已提交文本 + 新增文件名过滤，按 scoped 重生成（`... reg-imm-block.yaml`）。建议后续专任务清偿该债务（先修生成器再全量重生成）。
2. **`009t-audit.py` 块赋值重算分支为死代码**：判据 `insn in ("rd2rd",…)` 拿完整 id（`rd2rd_orri_rd`）比裸助记符，TESTCASES-017t 的 `insn→id` 改名后恒不命中。修复后 reg-imm-block 重算用例由 0 升至 14，且 0 mismatch（向量语义经独立重算坐实）。
3. validator 对 `class: overlap` 只校验 `expected_fault ∈ {null, ILLI}`，**不校验语义**：`fault=null` + 旧顺序 state 可静默通过（变体 B），须靠独立 oracle（本任务 `check_overlap.py`）。
4. `009t-audit.py` 现存 18 条 pre-existing mismatch（ctrl-br/mem-ra/mem-rb/reg-compare/reg-shift-extend），与 HEAD 逐行相同，非本任务引入（`deferred.md` L199/L209 已登记）。

**遗留问题**：
- 生成器↔向量预存漂移（其余 5 文件的 reg-arith/reg-compare/reg-logic/reg-shift-extend 差异 + reg-imm-block 的 3 行 spec_cite 已在本任务修复）**仍未清偿**：全量重生成仍会破坏已提交向量。建议后续 testcases 专任务处理（沿用 `deferred.md` L209）。
- `009t-audit.py` 18 条 pre-existing mismatch 与 `min_rom_probe_*` 群失败为既有漂移，未在本任务处置（`deferred.md` L199）。
- 端到端 QEMU/LLVM 证据由 `QEMU-033t`/`LLVM-028t` 承担；本任务未生成/未调用 QEMU/LLVM 期望值。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查**（改动源码，不依赖 reviewer）：
- `gen_block_overlap`：同组分支提前 `return`，不再构造 `final_vals`/`out`；word/input_state 保留；notes 模板符合 §2.1（`↔` + 「范围有交集（含部分/完全重合）→ ILLI (mreg_range_overlap)」）。跨组分支逻辑与原实现等价（`final_vals=list(src_vals)`），diff 证明跨组四条逐字节不变。✅
- `gen_block_overlap_complete`：非 rd2rd/rb2rb 返回 None；`_build_word_orri(rec,3,3,1)` 生成 `0x40B030C1`/`0x40D030C1`（手算核对）；仅 reg-imm-block 调用。✅
- spec_cite 漂移修复：`gen_block_legality_mreg_zero` 对 ra2rd/rd2ra、`gen_ra2rd_legality_dest_rd0` 复现已提交文本；生成器全量输出与已提交 reg-imm-block 逐字节一致（除预期的重叠改动）。✅
- CLI 过滤：`sys` 已导入；默认（无参）行为不变；scoped 运行只写目标文件。✅
- `009t-audit.py`：`mnemonic` 在 L123 已定义；`bank_map` 键为裸助记符，与 `mnemonic` 一致；改后 audit 最终 mismatch 集与 HEAD 逐行相同（无回归），reg-imm-block 重算式 14/0。✅
- 防造假：证据脚本逐项打印期望/实际/退出码；注入用 `git diff --name-only` 证非空、还原用 sha256 校验；`run.sh` 不用 `tee`、直接 `$?` 捕获各命令退出码。✅
- 边界：`validate_vectors` 数据级覆盖门控对 overlap 类仍满足（每个 id 至少 1 条 active overlap；本任务新增 2 条）。✅

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 生成器全量重跑破坏 5 个文件（预存漂移） | ✅已修（限本任务范围） | 修生成器使 reg-imm-block 忠实复现 + 新增文件名过滤 | 全量 temp 重生成 reg-imm-block 与 repo 逐字节同；scoped 重跑仅 reg-imm-block diff（run.sh E1） |
| `009t-audit` 块赋值重算死代码 | ✅已修 | `insn`→`mnemonic`（含 bank_map 键） | audit 最终 mismatch 集与 HEAD 相同；reg-imm-block 重算 14/0 |
| 反例变体 B 无法被 validator/audit 判出 | ✅已证并给替代证据 | `--inject` 采变体 B + 独立 `check_overlap.py` | E3 `--inject` FAIL→还原 sha 一致→回绿 |
| `009t-audit` 18 条 pre-existing mismatch | ⏸延后 | 未动（非本任务引入） | HEAD vs 当前 mismatch 集逐行 diff 相同 |
| 其余 5 文件生成器漂移未清偿 | ⏸延后 | 未动（越界；仅登记） | 建议后续 testcases 专任务 |

**判决**：所有本任务范围内 finding 已修/已证；无未修 finding。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查方法**：独立重跑所有验收命令 + 独立重算14条用例 + 独立注入反例 + 覆盖≠语义复现。

---

##### A. 重跑记录（逐项真实命令 + 退出码）

**A1. check_overlap.py 正常运行**
```
C1: same-bank partial-overlap ⇒ ILLI
  [PASS] rd2rd word=0x40B03082 fault=ILLI state=null
  [PASS] rb2rb word=0x40D03082 fault=ILLI state=null
C2: same-bank complete-overlap ⇒ ILLI
  [PASS] rd2rd word=0x40B030C1 fault=ILLI state=null
  [PASS] rb2rb word=0x40D030C1 fault=ILLI state=null
C3: cross-bank overlap stays legal (fault null + semantic state)
  [PASS] rd2ra word=0x40B430C2 fault=null state present
  [PASS] ra2rd word=0x40B830C2 fault=null state present
  [PASS] rd2rb word=0x40D430C2 fault=null state present
  [PASS] rb2rd word=0x40D830C2 fault=null state present
C4: recompute overlap verdict for every block semantic/overlap case
  [PASS] recomputed 14 block cases, 0 mismatch
check_overlap: PASS
EXIT=0
```

**A2. check_overlap.py --inject（工程师自带注入）**
```
=== injection self-test: flip rd2rd partial overlap to fault=null ===
injected; git diff --name-only => 'tests/vectors/isa/reg-imm-block.yaml'
C1: [FAIL] rd2rd word=0x40B03082 expected_fault=None (want ILLI)
C4: [FAIL] rd2rd word=0x40B03082 hb=3 hc=2 immu6=2 recomputed='ILLI' recorded=None
[PASS] injection caused 3 check failure(s) as expected
restored; sha256=2336e6b14aadf0f23feaedd0914c783cc7f2b8eb7a6e8abf6a49c3785211bc36
[PASS] restore verified, checks green again
EXIT=0
```

**A3. run.sh --inject（完整证据脚本）**
```
E1 generator run1 EXIT=0
E1 only reg-imm-block.yaml differs: tests/vectors/isa/reg-imm-block.yaml
E1 idempotent: sha256=2336e6b14aadf0f23feaedd0914c783cc7f2b8eb7a6e8abf6a49c3785211bc36
E2 validate_vectors EXIT=0
E3 injection self-test (FAIL->restore PASS) EXIT=0
E3 overlap recompute EXIT=0
E4 mismatch set identical to HEAD (18 pre-existing entries)
E4 current audit reports zero reg-imm-block mismatch
E5 make check EXIT=0
ALL CHECKS PASS
EXIT=0
```

**A4. validate_vectors.py**
```
validate_vectors: 152/152 M1 identities covered OK (inventory sync OK; 15 data files, 694 cases; data coverage gaps: 0)
EXIT=0
```

**A5. 009t-audit.py**
```
EXIT=1 (pre-existing，18 条 mismatch 与 HEAD 逐行相同)
零条 reg-imm-block mismatch
```

**A6. make check**
```
EXIT=0 (repository checks: PASS)
```

**A7. git diff --stat HEAD**
```
tests/vectors/isa/reg-imm-block.yaml               | 56 +++++++++----
tools/testcases/009t-audit.py                      | 14 ++--
tools/testcases/generate_isa_vectors.py            | 96 +++++++++++++++-------
(任务书 .md 的变更不计入)
```

**A8. git status --untracked-files=all**
```
仅 4 个 modified 文件（任务书 + 3 个应改文件），无 untracked，无 *.bak/*.orig/*.rej
```

---

##### B. 脚本审计结论

**run.sh**：
- 5 项检查（E1–E5）均有独立 FAIL 路径，非恒真
- 退出码直接 `$?` 捕获，未用 `tee` 吞退出码 ✓
- `--inject` 模式调用 `check_overlap.py --inject`，非自行实现 ✓
- 审计 HEAD 版本的 mismatch 集（`git show HEAD:009t-audit.py`），与当前版 diff 确认一致 ✓

**check_overlap.py**：
- C1/C2/C3/C4 四项检查均有明确 FAIL 条件（`!=` 比较），非恒真 ✓
- `--inject`：修改 word=0x40B03082 的 expected_fault 为 None + 旧 expected_state 字典，`git diff --name-only` 非空校验 ✓
- 还原后 sha256 校验 ✓
- 注入后 run_checks() 必须 >0 才报 PASS（敏感性校验） ✓
- 注入目标可复原（`shutil.move(backup, YAML_PATH)` + `finally` 块） ✓

**结论**：两个脚本结构合格，FAIL 路径可达，注入非空可还原。

---

##### C. 独立重算（14 条块赋值 semantic/overlap 用例，逐条）

reviewer 独立从编码字段派生重叠判定（不依赖 check_overlap.py），逐条比对：

| # | mnemonic | word | hb | hc | immu6 | 重叠? | 期望 fault | 记录 fault | 结果 |
|---|----------|------|----|----|-------|-------|-----------|-----------|------|
| 1 | rd2rd | 0x40B010C1 | 1 | 3 | 1 | [1,2)∩[3,4)=∅ | null | null | OK |
| 2 | rd2rd | 0x40B03082 | 3 | 2 | 2 | [3,5)∩[2,4)=[3,4)≠∅ | ILLI | ILLI | OK |
| 3 | rd2rd | 0x40B030C1 | 3 | 3 | 1 | [3,4)∩[3,4)=[3,4)≠∅ | ILLI | ILLI | OK |
| 4 | rd2ra | 0x40B410C1 | 1 | 3 | 1 | 跨组 | null | null | OK |
| 5 | rd2ra | 0x40B430C2 | 3 | 3 | 2 | 跨组 | null | null | OK |
| 6 | ra2rd | 0x40B810C1 | 1 | 3 | 1 | 跨组 | null | null | OK |
| 7 | ra2rd | 0x40B830C2 | 3 | 3 | 2 | 跨组 | null | null | OK |
| 8 | rb2rb | 0x40D010C1 | 1 | 3 | 1 | [1,2)∩[3,4)=∅ | null | null | OK |
| 9 | rb2rb | 0x40D03082 | 3 | 2 | 2 | [3,5)∩[2,4)=[3,4)≠∅ | ILLI | ILLI | OK |
| 10 | rb2rb | 0x40D030C1 | 3 | 3 | 1 | [3,4)∩[3,4)=[3,4)≠∅ | ILLI | ILLI | OK |
| 11 | rd2rb | 0x40D410C1 | 1 | 3 | 1 | 跨组 | null | null | OK |
| 12 | rd2rb | 0x40D430C2 | 3 | 3 | 2 | 跨组 | null | null | OK |
| 13 | rb2rd | 0x40D810C1 | 1 | 3 | 1 | 跨组 | null | null | OK |
| 14 | rb2rd | 0x40D830C2 | 3 | 3 | 2 | 跨组 | null | null | OK |

**mismatch = 0/14**。逐条编码字段手算核对一致。

---

##### D. 独立注入（reviewer 自选，不用脚本自带 --inject）

**注入方式**：python3 直接修改 YAML，将 rd2rd 部分重叠用例（word=0x40B03082）改为 fault=null + 旧顺序语义 expected_state 字典（变体 B）。

**注入证据**：
```
$ git diff --name-only -- tests/vectors/isa/reg-imm-block.yaml
tests/vectors/isa/reg-imm-block.yaml
（非空 ✓）
```

**注入后 check_overlap.py 输出**：
```
C1: [FAIL] rd2rd word=0x40B03082 expected_fault=None (want ILLI)
C4: [FAIL] rd2rd word=0x40B03082 hb=3 hc=2 immu6=2 recomputed='ILLI' recorded=None
check_overlap: FAILED (3)
EXIT=1
```

**还原**：
```
$ cp /tmp/opencode/TESTCASES-023t-review/reg-imm-block.yaml.bak tests/vectors/isa/reg-imm-block.yaml
$ sha256sum tests/vectors/isa/reg-imm-block.yaml
2336e6b14aadf0f23feaedd0914c783cc7f2b8eb7a6e8abf6a49c3785211bc36
（与工程师一致 ✓）
$ python3 .work/evidence/TESTCASES-023t/check_overlap.py
check_overlap: PASS
EXIT=0
```

**结论**：独立注入确认脚本敏感性——注入后 EXIT=1（3 FAIL），还原后 EXIT=0。

---

##### E. "覆盖≠语义"判定

reviewer 独立复现工程师声明：

| 变体 | 注入内容 | validate_vectors | 009t-audit | check_overlap.py C4 |
|------|---------|-----------------|-----------|---------------------|
| A: fault=null, state=null | expected_fault=None, expected_state=None | EXIT=0 ✓ | EXIT=1, 检出 2 条 reg-imm-block mismatch | FAIL |
| B: fault=null + 旧顺序 state | expected_fault=None, expected_state={旧顺序字典} | EXIT=0 ✓ | EXIT=1, 但 **0 条 reg-imm-block mismatch** | FAIL |

**结论**：validate_vectors 只校验结构（`expected_fault ∈ {null, ILLI}`），不校验语义。变体 B 的顺序语义字典可静默通过 validator 和 audit。**语义正确性证据必须落在独立重算**（check_overlap.py C4，从编码字段派生重叠判定）。本任务的独立 oracle 设计正确。

---

##### F. 009t-audit.py 修复核实

- HEAD 版本 L894: `insn in ("rd2rd",...)"`，其中 `insn = case["id"] = "rd2rd_orri_rd"`，恒不命中 → 死代码 ✓
- 当前版本 L894: `mnemonic in ("rd2rd",...)"`，`mnemonic = case.get("mnemonic","") = "rd2rd"`，正确匹配 ✓
- HEAD 版本 L913: `bank_map[insn]` 同样死代码；当前版改为 `bank_map[mnemonic]` ✓
- 修复后块赋值重算 14/0 mismatch ✓
- 18 条 pre-existing mismatch（HEAD vs 当前 diff EXIT=0，逐行相同）非本任务引入 ✓

---

##### G. 越界与最小性

| 越界项 | 必要性 | 最小性 |
|--------|--------|--------|
| CLI 文件名过滤 | 必要：全量重跑破坏 5 文件（预存漂移），scoped 运行是唯一安全方式 | 最小：`sys.argv` 过滤 + 3 行代码 |
|3 行 spec_cite 订正 | 必要：生成器忠实复现已提交 reg-imm-block 的前提 | 最小：仅 ra2rd/rd2ra 和 dst_rd0 三处 |
| 009t-audit.py insn→mnemonic | 必要：原判据为死代码，块赋值重算从 0 升至 14 | 最小：2 行改动（L894 + L913） |

**未披露越界**：无。`git status` 仅 4 个 modified 文件，无 untracked。

---

##### H. 完成区一致性

逐条核对完成区声明 vs 真实输出：
- 生成器 EXIT=0、幂等 sha256=2336e6b1… — **一致** ✓
- validate_vectors 152/152、694 cases、gaps 0 — **一致** ✓
- check_overlap 14/0 — **一致** ✓
- 009t-audit 18 条 pre-existing、0 条 reg-imm-block — **一致** ✓
- make check EXIT=0 — **一致** ✓
- git status 干净 — **一致** ✓
- 反例注入 3 FAIL→还原回绿 — **一致** ✓
- 覆盖≠语义（变体 B validator/audit 均判不出）— **一致** ✓

**无夸大或不实。**

---

**判决：Accepted**

全部验收标准通过：
1. 数据修正：rd2rd/rb2rb 重叠用例 expected_fault=ILLI、expected_state=null ✓；跨组四条逐字节不变 ✓
2. 覆盖不变：validate_vectors 152/152、gaps 0 ✓
3. 生成器幂等：scoped 重跑仅 reg-imm-block diff、sha 不变 ✓
4. 审计不回归：009t-audit mismatch 集与 HEAD 逐行相同、零 reg-imm-block mismatch ✓
5. 反例可失败：独立注入 → EXIT=1 (3 FAIL) → 还原 → EXIT=0 ✓
6. make check 全绿 ✓
7. 残留干净、越界已披露且必要最小 ✓

