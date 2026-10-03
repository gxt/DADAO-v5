# QEMU-033t: `mreg_range_overlap` M1 运行期实现（QEMU translate 期 ILLI）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`SPEC-088t`（规范/合约层修复，**须先 `已验证`**）。相关：`contracts/legality_rules.yaml`（`mreg_range_overlap`，`active`）、`contracts/opcodes.yaml`（`rd2rd_orri_rd`/`rb2rb_orri_rb`）、`components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`、`tools/qemu/min_rom_probe_*.py`。
**状态**：待开始

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与用户裁定

- 用户裁定（唯一真源）：`mreg_range_overlap`（`active`/`static`）当前是「**纸面规则**」——LLVM 无静态检查、**QEMU 无运行期检查**、无探针/门控；M1 现状与 spec 相违。
- 本任务只做 **QEMU 侧 M1 运行期实现**：`rd2rd`/`rb2rb` 的源/目的范围有交集（含完全重合）⇒ `gen_exception_illegal`（测试机退出码 `0x88`）。
- LLVM 侧静态检查归 `LLVM-028t`；向量/生成器修正归 `TESTCASES-023t`。

---

## 1. 事实核实（本轮 architect 实测；执行时以重跑为准）

1. `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`：
   - `trans_rd2rd_orri_rd`（L12–28）与 `trans_rb2rb_orri_rb`（L75–90）均只查 `hd==0`、`hb==0`、`hb+hd>64 || hc+hd>64`（**源、目的都查范围**），随后按升序 `load → store`。注释明写 **「Overlap handled by ascending order read-before-write」**（L11、L74）——与 spec 相违。
   - 跨组指令 `rd2ra`/`ra2rd`/`rd2rb`/`rb2rd` 不受 `mreg_range_overlap` 约束（结构性不重叠），**不改**。
2. `contracts/legality_rules.yaml` 的 `mreg_range_overlap`（SPEC-070t 新增、`active`）：同组块赋值源/目的范围有交集 ⇒ ILLI；当前仅 `rd2rd`/`rb2rb`（FP 由 `SPEC-088t` 扩到 `convert_ff`，本任务不做 FP）。
3. `tools/qemu/` 下**无** `rd2rd`/`rb2rb` 重叠 ILLI 探针；`min_rom_probe_008t.py` 仅测 `rb2rb` 非重叠往返；`min_rom_probe_013t.py` 的 B9 明确注释「同组重叠规则对 M1 的 rd2ra/ra2rd 是 vacuous」。
4. `make check-qemu-semantics` 仅跑 `reg-shift-extend`+`reg-compare`（不含 `reg-imm-block`），故本改动**不改变其覆盖**；`reg-imm-block.yaml` 中现存的同组重叠 `class: overlap` **语义**用例由 `TESTCASES-023t` 修正。

---

## 2. 设计

### 2.1 代码改动（`trans_block.c.inc.patch`）

在 `trans_rd2rd_orri_rd` 与 `trans_rb2rb_orri_rb` 的范围检查之后、复制循环之前，插入重叠检查：

```c
    if (!(a->hb + a->hd <= a->hc || a->hc + a->hd <= a->hb)) {
        gen_exception_illegal(ctx);
        return true;
    }
```

- 语义：源区间 `[hc, hc+hd)` 与目的区间 `[hb, hb+hd)` 有交集（含 `hb==hc` 完全重合）⇒ ILLI；`hd` 为 `immu6`。等价于 `overlap ⇔ !(dst_end<=src_start || src_end<=dst_start)`。
- 同时把两处注释从「Overlap handled by ascending order read-before-write」改为「Overlap ⇒ ILLI (mreg_range_overlap)」。
- **不改**另外四条 block trans（跨组）与任何其它文件。

### 2.2 探针（新建 `tools/qemu/min_rom_probe_033t.py`）

用例（沿用既有 min_rom 探针体例，`rb/rd` 初值可回读校验）：

| # | 用例 | 期望 |
|---|---|---|
| T1 | `rd2rd {rd4:rd5}, {rd2:rd3}`（目的[4,6) ∩ 源[2,4)=∅） | PASS（正常复制） |
| T2 | `rd2rd {rd3:rd4}, {rd2:rd3}`（目的[3,5) ∩ 源[2,4)={3} 部分重叠） | **ILLI 0x88** |
| T3 | `rd2rd {rd3:rd3}, {rd3:rd3}`（完全重合，count=1） | **ILLI 0x88** |
| T4 | `rd2rd {rd2:rd3}, {rd3:rd4}`（目的在源之前，部分重叠） | **ILLI 0x88** |
| T5 | `rb2rb {rb4:rb5}, {rb2:rb3}`（非重叠） | PASS |
| T6 | `rb2rb {rb3:rb4}, {rb2:rb3}`（部分重叠） | **ILLI 0x88** |
| T7 | `rb2rb {rb3:rb3}, {rb3:rb3}`（完全重合） | **ILLI 0x88** |
| T8 | 对照：`rd2ra {ra3:ra4}, {rd3:rd4}`（跨组"同索引"，不属本规则） | PASS |

- 每条分支出/退出码须**双向验证**（目标=分支指令+偏移指向预期分支）；写操作数/期望值须在关键用例回读校验（`set.zw`+`or.w`，避免立即数位宽截断）。
- 产物落点：探针脚本入 `tools/qemu/`（可复用/审计）；ROM 等中间产物落 `TEST_ARTIFACTS_DIR`（`INFRA-025t` D6）。

### 2.3 测试机退出码约定
ILLI = `0x88`（`ADR-0004` 测试机约定）；PASS 走既有 exit port 约定。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch` | 两条 trans 加重叠 ILLI + 注释修正 |
| 2 | `tools/qemu/min_rom_probe_033t.py` | 新建探针（T1–T8） |
| 3 | `.work/evidence/QEMU-033t/run.sh` | 一键证据脚本（不含 `tee` 吞码；含注入自检） |
| 4 | `.work/log/qemu/QEMU-033t-*.log` | 构建/探针完整输出（非易失） |

**明确不改**：`contracts/opcodes.yaml`、`spec/**`、`tests/**`、`tools/{spec,llvm,testcases}/**`、`components/llvm-project/**`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`
- `contracts/legality_rules.yaml`（`mreg_range_overlap`）、`contracts/opcodes.yaml`（`rd2rd_orri_rd`/`rb2rb_orri_rb` 字段与编码）
- 既有探针体例 `tools/qemu/min_rom_probe_008t.py`/`_013t.py`、`tools/qemu/check_qemu_trans.py`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare`（重应用补丁集、`.work/source/qemu` 保持 base+1 commit 不变量）+ `make build-qemu`（增量，预计 **2–5 分钟**；若触发 reconfigure 则更久，须先申报）。
- 临时目录 `/tmp/opencode/QEMU-033t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-033t/`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留 `.work/log/qemu/QEMU-033t-build.log`）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_033t.py`：T1/T5/T8 PASS、T2/T3/T4/T6/T7 = ILLI 0x88；每例打印「检查名 + 期望/实际 + 退出码」，进程退出码 0 仅当全部符合。
3. **反例可失败（承重证明）**：注入「移除重叠检查」的 QEMU 构建 ⇒ T2/T3/T4/T6/T7 变 FAIL（尤其 T3 完全重合）⇒ 还原源码**并重建** ⇒ 回绿。注入用 `git diff --name-only` 证明非空；还原用 `git status`/`git diff` + 重建后重跑证明。
4. **不误伤**：既有 `tools/qemu/min_rom_probe_008t.py`（含 `rb2rb` 非重叠往返）与 `_013t.py`（跨组）保持 PASS。
5. **编码门控不回归**：`python3 tools/qemu/check_qemu_trans.py` → `227/227 (M1 152/152)`、EXIT 0。
6. **`make check` 全绿**：`repository checks: PASS`（重点：`check-qemu-semantics` PASS、lit 26/26、`validate-encoding` 227 OK）。
7. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书）；`check-no-residue` PASS；`git diff --name-only` 与 §3 对齐。

### 6.1 反例注入
- (a) 删除 T2/T3/T4/T6/T7 的重叠检查（还原为「升序先读后写」）⇒ 探针 FAIL。
- (b) 只查部分重叠、不查完全重合（如用 `hb+hd==hc` 之类错误条件）⇒ T3 仍 PASS 但 T2/T4 应 FAIL（证明「含完全重合」断言承重）。
- 注入后须**重建**再跑，还原后亦须**重建**（源码还原 ≠ 二进制还原）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-033t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-033t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

- 本任务依赖 `SPEC-088t` 先落地（至少 `contract-isa`/`SimRISC-07` 的禁则）；若 `SPEC-088t` 未完成，本任务不应下发（避免实现与合约打架）。
- `min_rom_probe_033t.py` 的寄存器/立即数构造须防位宽截断；分支须双向核对（见 AGENTS「探针的寄存器/内存值构造须回读校验」「探针分支须双向验证」）。
- 不改 `check-qemu-semantics` 覆盖范围（避免引入 `reg-imm-block` 全量用例的不确定性）；重叠 ILLI 的端到端证据由本探针 + `TESTCASES-023t` 的 `legality` 向量承担。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
