# SPEC-163t: 删除 `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf`（原子删除册：spec + LLVM + QEMU + tests）

**模块**：spec（**跨模块原子删除**：`spec` + `llvm` + `qemu` + `testcases` 同一提交）
**项目里程碑**：M9（ISA 精简）
**依赖**：无；**必须早于 `SPEC-157t`（FMA 立册）** —— FMA 将占用腾出的 `0x5E`/`0x5F`。
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-22，原话）

> 「删除cs.eq/ne-rrrr-rf，两条指令；然后把ftfma/fofma的编码移动到这两条指令的位置」

### 删除依据（能力面）

- 这两条的语义 = **条件复制**（`if (rdHA == rdHB) rfHB = rfHC else rfHB = rfHD`），能力仅为 `select`；
- **无独特表达力**：等价写法 = `sub rd, a, b` + `cs.z`（2 条）；"判 `qcmp` 结果 == 1"还需先把常量 1 物化（同为 2 条）⇒ **不省指令**；
- 后端 `LowerCmpSelect` 只发射 `CS_N`/`CS_Z`/`CS_P`，**从不生成**这两条（`DADAOISD` 里也没有对应的 CS 节点）；
- ⇒ 死指令 + 占用 `0x5E`/`0x5F`；删掉后该两格交给 FMA（`ftfma`/`fofma`）。

### 现场事实（2026-10-22 核，执行前须复核）

- 记录：`cs.eq_rrrr_rf`（`op=0x5E`）、`cs.ne_rrrr_rf`（`op=0x5F`），`format = rrrr`、**`scope: fp`**、`rule_refs: [dst_rf0]`。
- **计数耦合（写死断言）**：
  - `check_scope.py`：`fp 60 → 58`、`total 260 → 258`（+ changelog 一行）
  - `check_fp_contract.py`：`EXPECTED_TOTAL 60 → 58`；`FAMILY_COUNTS["cs_rf"] 5 → 3`；`dst_rf0` 的 FP 引用条数 `35 → 33`
  - `fp_semantics.yaml`：删 2 条（`family: cs_rf`）
- **原子性硬约束**：`check_instrinfo`（`fp` 记录必须有 `.td` def）与 `check_qemu_trans`（每条记录必须有 `trans_*`）双向校验 ⇒ **records / `.td` / `trans` / lit 必须同一提交**，否则中间态必红。
- 其他触点（现场核）：`DADAOInstrInfoFP.td` 的 `cs_eq_rrrr_rf`/`cs_ne_rrrr_rf`；QEMU `trans_fp.c.inc.patch` 的 2 条 `trans_*`；lit `tests/llvm/lit/MC/DADAO-gen/gen-rrrr.s`、`tests/llvm/lit/MC/DADAO/{fp-encoding.s,fp-legality.s}`；`tests/vectors/isa/reserved.yaml`；`SimRISC-02 §1.1` 2 行 + `§3.3` 正文（含"用 `cs.eq` 判 ==1"的说明）；`contract-fp.md`（若提及）；`contract-isa.md`（**计数类，按用户裁定留到 M9 收尾**，本册只改行为描述）。

## 目标

1. 彻底删除 `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf`（记录 / `.td` / QEMU trans / lit / 向量）；
2. 计数与族表同步（现场派生，不写死猜测）；
3. 规范正文改写：§3.3 删掉"用 `cs.eq` 判 ==1"的指引，改为 `sub`+`cs.z`（或说明仅 `cs.n/z/p` 用于 FP 条件复制）；
4. `0x5E`/`0x5F` 变为**空**（供 `SPEC-157t` 的 FMA 使用），不得在本册占位。

## 接口规范

- **输入**：`contracts/opcodes.yaml`、`tools/spec/{generate_opcodes,check_scope}.py`、`tools/spec/check_fp_contract.py`、`contracts/fp_semantics.yaml`、`spec/SimRISC-02`、`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfoFP.td.patch`、`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`、`tests/llvm/lit/**`、`tests/vectors/**`、`manifests/spec-readonly.lock.toml`。
- **输出**：删除后的 `opcodes.yaml`（`fp 58`/`total 258`）、`fp_semantics.yaml`（删 2 条）、`check_scope` 计数与 changelog、`check_fp_contract` 计数、`.td` 删除、QEMU trans 删除、lit/向量重生成、`SimRISC-02` 正文与变更记录、只读锁重算、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：**不得**顺手删 `cs.eq/ne_rrrr_rd`（`0x66/0x67`，用户只定删 rf 两条）；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 删除面（逐项，缺一即红）

1. `generate_opcodes.py`：删两条 `rec(...)` + 文件头计数说明；
2. `opcodes.yaml` 重生成（260→258）；
3. `check_scope.py`：`fp 60→58`、`total 260→258` + changelog；
4. `check_fp_contract.py`：`EXPECTED_TOTAL`、`cs_rf`、`dst_rf0` 引用数；
5. `fp_semantics.yaml` 重生成（−2）；
6. `DADAOInstrInfoFP.td.patch`：删 2 def；
7. QEMU `trans_fp.c.inc.patch`：删 2 个 `trans_*`（并清理其 check 调用点）；
8. lit：`gen-rrrr.s`（生成物重生成）、`fp-encoding.s`/`fp-legality.s` 中的对应用例删除；
9. `tests/vectors/isa/reserved.yaml`（若引用）；
10. `SimRISC-02 §1.1` 2 行 + `§3.3` 指引改写 + 变更记录 1 行（标注**破坏性**）；
11. 只读锁 `sha256` 重算。

### B. 不改的边界

- 保留 `cs.n/z/p_rrrr_rf`（FP 条件复制主力）与 `cs.eq/ne_rrrr_rd`；
- `contract-isa.md` 的计数按用户裁定**留到 M9 收尾**，本册只改行为描述（若提及这两条则删句）。

## 验收标准

1. `opcodes.yaml` = **258** 条；`fp` = **58**；两条记录消失（`grep` 零命中）。
2. `check_scope` / `check_fp_contract`（`cs_rf=3`、`dst_rf0` 33）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo`（0 errors）/ `check_isa_coverage` / `check_qemu_trans --strict`（**258/258**）全绿。
3. `check-spec-*` / `check-asm-list*` / `check_lit_gen` 全绿；`0x5E`/`0x5F` 在 `opcodes.yaml` 中**无记录**（留空）。
4. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥2**：① 只删记录不删 `.td` ⇒ `check-instrinfo` 红；② 不删 QEMU trans ⇒ `check_qemu_trans` 258/258 红（或残留 trans 报错）。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（记录/`.td`/trans/lit/计数/锁）。
2. 生成器删两条 → 重生成 → `.td`/trans/lit 同步删 → 计数。
3. `SimRISC-02` 正文 + 变更记录 + 只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 临时保留 `.td` def（不删）⇒ `check-instrinfo` 报 orphan / 覆盖率不符 ⇒ 红；补删 ⇒ 绿。
- 临时保留一条 QEMU `trans_*` ⇒ `check_qemu_trans` 计数/残留检查红；删 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不删 `cs.eq/ne_rrrr_rd`；不动 `cs.n/z/p`。
- `contract-isa.md` 计数留 M9 收尾。
- FMA 的 `0x5E`/`0x5F` 编码在 `SPEC-157t` 落地，本册只腾格。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
