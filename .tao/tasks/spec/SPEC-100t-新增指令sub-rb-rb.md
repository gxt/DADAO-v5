# SPEC-100t: 新增指令 `sub.o_orrr_dbb`（RB − RB → RD）规范与编码

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

> **决策依据（已定）**：用户 2026-10-04 逐条确认，decision 记入 **`.tao/adr/adr-0012-simrisc-0.5.4-update.md` 的 D9**（`Accepted`，见 `## 状态说明`）。本任务书按 D9 落地，**无待确认提案**（唯一例外见下方 ⚠️ 算术修正）。
>
> ⚠️ **待用户确认的算术修正**：D9.1 原裁定写 `ha=0x33` 但 `value=0x40C00000`；`0x40C00000` 的 `ha` 实为 **`0x30`**（= `SPEC-101t` 的 `add.o_orrr_bbd`），二者冲突。按 orrr 编码式 `value = op<<24 | ha<<18`、mask `0xFFFC0000`，取 **`ha=0x33 ⇒ value=0x40CC0000`**。本任务书按 `0x40CC0000` 写；若用户判定应为其它值，须先改 `adr-0012 D9` 再执行。
>
> **原子落地集**：本任务 + `QEMU-040t` 必须**同一集成波/同一提交**落地——`make check` 的 `check-interface` 要求 `contracts/opcodes.yaml` 每条 ↔ QEMU `trans_*` 一一对应；**单独提交本任务会红**（`check_qemu_trans --strict` / `QEMU trans_* 定义数`）。
>
> **串行**：本任务与 `SPEC-101t`（三条既有指令改名+改编码）**同改 `contracts/opcodes.yaml` 与 `tests/vectors/**`**，按 `AGENTS.md`「同改共享文件串行」**不得并行**。

## 执行环境
**执行环境**：本地

## 接口规范

### 输入

- **`adr-0012 D9`**（权威决策）；`ADR-0018（C14 D4）`、`ISS-130`、`.tao/knowledge/project_M3-codegen-choices.md §5`（C14）。
- `spec/SimRISC-00-指令系统设计.md`（QFC 主表 + `MISC-octa` 子表，编码权威）。
- `spec/SimRISC-05-64位地址运算.md`（`§加减操作` 正文 + 生成块 `ASSEMBLY_LIST`/`LEGALITY`）。
- `.tao/knowledge/contract-isa.md §7`（RB 地址运算归一化）、`§15`（legality 汇总）。
- `contracts/opcodes.yaml`（227 条：m1 152 / fp 60 / excluded 15）、`contracts/legality_rules.yaml`（含 `dst_rd0`）。
- 生成器/门控（v5 自身）：`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/spec/check_asm_list_drift.py` + `tools/llvm/gen_asm_list.py`、`tools/spec/check_legality_drift.py`、`tools/spec/check_qfc_coverage.py`、`tools/spec/check_scope.py`、`tools/spec/validate_encoding.py`、`tools/integ/check_interface_alignment.py`、`tools/testcases/validate_vectors.py`。

### 输出（按 D9.1）

1. `spec/SimRISC-00-指令系统设计.md`：`MISC-octa` 子表（行 `110`，列 `x011`）新增 `sub.o_orrr_dbb`。
2. `spec/SimRISC-05-64位地址运算.md`：分类头计数（`4 条` → `5 条`）、`§加减操作` 新增 `sub.o` 正文（`rd = rb − rb`，64 位补码、全 64 位、单条无 `.s`/`.u`）；生成的 `ASSEMBLY_LIST`/`LEGALITY` 块经生成器刷新。
3. `.tao/knowledge/contract-isa.md §7.1` 新增行（语义 + 来源标注）。
4. `contracts/opcodes.yaml` 新条目（**由 `tools/spec/generate_opcodes.py` 生成，须同步生成器**）：
   - `id: sub.o_orrr_dbb`；`mnemonic: sub.o`；`format: orrr`；`op: '0x40'`；`ha: '0x33'`；`mask: '0xFFFC0000'`；`value: '0x40CC0000'`；
   - 字段 `rdhb`(dst,rd)[17:12]、`rbhc`(src,rb)[11:6]、`rbhd`(src,rb)[5:0]；`legality: [rdhb != rd0]`；`rule_refs: [dst_rd0]`；`scope: m3`；`spec_cite: SimRISC-05 §加减操作`。
5. `.tao/knowledge/contract-asm-list.md`（生成物）刷新。
6. **`tools/spec/check_scope.py`**：`ALLOWED_SCOPES` 纳入 `m3`、新增 `m3` 计数（=1）、`EXPECTED_TOTAL` 227→**228**、`scope∈{m1,fp,m3}` ⇒ 无 `decode/旧字段`、docstring 同步；`tools/testcases/validate_vectors.py` docstring「227 条」→「228 条」。
7. 组件向量（**可选**，`scope: m3` 不在 M1 身份集、不强制）：如需，加 `tests/vectors/isa/reg-arith.yaml` encoding/semantic 一条，`inventory.md` **不加 M1 行**（m3 不参与 M1 交叉校验）；若添加须同步 `tools/testcases/generate_isa_vectors.py`。

### 约束

- **Spec-first**：编码/语义以 `adr-0012 D9` + `spec/` 为准，**不得**从 LLVM/QEMU 实现反推；外部参考仓库（0628/TCH）仅只读溯源，不作执行依赖。
- **原子**：spec 正文 + 编码 + 生成物 + `check_scope.py` 一次改完；`make check` 在 `QEMU-040t` 同集落地后全绿。
- **生成器随产物**：`generate_opcodes.py`/`gen_asm_list.py`/`gen_legality_list.py` 重跑与交付**逐字节一致**（零漂移）。
- **不改既有指令**语义/编码/id；仅向空槽 `ha=0x33` 新增一条（原 reserved/UNDI）。
- **不新增 legality 规则**（复用 `dst_rd0`）。
- **`scope: m3`**：新增范围取值须同步 `check_scope.py`；不得置 `m1`。
- 临时目录 `/tmp/opencode/SPEC-100t/`；复杂命令输出留存 `.work/log/spec/`（禁 `tee` 吞退出码：`cmd > log 2>&1; rc=$?`）；**不提交 git**。

## 验收标准

1. **无冲突核对**：给出 QFC `MISC-octa` 子表逐槽核对表（`ha` 已用集合 + 新槽 `0x33`），证明唯一、不与 `SPEC-101t` 的新 `0x30`–`0x32` 及既有条目冲突；`check_qfc_coverage.py` EXIT=0。
2. **正文/归一化一致**：`spec/SimRISC-00` 子表、`spec/SimRISC-05 §加减操作`、`.tao/knowledge/contract-isa.md §7.1` 三处语义/id/编码一致（给 grep/对照）。
3. **编码一致**：`contracts/opcodes.yaml` 新条目字段/`op`/`ha`/`mask`/`value`/`scope` 与 D9.1 一致；`validate_encoding.py` EXIT=0；`generate_opcodes.py` 重跑与交付逐字节一致。
4. **scope 门控**：`check_scope.py` EXIT=0（`m3=1`、`total=228`、`m1=152`）。
5. **生成物同步**：`check-asm-list-drift` EXIT=0、`check-legality-drift` EXIT=0。
6. **门控**：`make check` EXIT=0（**在 `QEMU-040t` 同集落地后**）；`check-interface` 跨载体一致（总计 **228**、M1 **152**）；`check-spec-refs` 不新增违规。
7. **反例门控**：注入（改 `ha`/`value`/`scope`）→ 对应检查器非零退出；复原 → 回绿；真实输出留存 `.work/log/spec/`。
8. **一键证据脚本** `.work/evidence/SPEC-100t/run.sh`（规格同 `LLVM-033t`：非交互、任一失败即非零退出、逐项打印「检查名+期望/实际+退出码」、内置「注入反例→预期 FAIL→还原→回绿」自检、结尾不 `tee` 吞退出码）。
9. **未越界**：仅改本任务列出的文件；`git status --untracked-files=all` 干净（除本任务应有改动）。
10. **确认**：上述 ⚠️ 算术修正（`ha=0x33 ⇒ value=0x40CC0000`）获用户确认，或按用户修正值落地。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
