# TESTCASES-023t: `mreg_range_overlap` 向量与生成器修正（同组重叠 ⇒ ILLI）

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：`SPEC-088t`（规范/合约层修复，**须先 `已验证`**）。相关：`contracts/legality_rules.yaml`（`mreg_range_overlap`）、`.tao/knowledge/contract-isa.md`（`SPEC-088t` 修正后的块赋值重叠条）、`tests/vectors/isa/reg-imm-block.yaml`、`tools/testcases/{generate_isa_vectors.py,009t-audit.py,validate_vectors.py}`、`tests/vectors/inventory.md`。
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
