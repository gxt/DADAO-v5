# SPEC-068t: `MISC-AMO` 类编码 `0000-0000` → `0111-0111`

**模块**：spec（含 `contracts/`）；**影响**：QEMU `insn.decode`、**LLVM MC + lit**、向量（**原子同步 + 全量重建**）
**项目里程碑**：M2
**依赖**：用户裁定（2026-10-01；**范围 = 全部重建**）
**状态**：待开始（**已下发**）

## 背景

`MISC-AMO` 子表当前位于 QFC 主表 `0000-0xxx`（`contract-isa`：`op = 0000-0000`），承载 `illi`/`swym`/`fence` 与 LR-SC。用户裁定将其**改为 `0111-0111`**。
（**理由用户未说明**——任务书不得编造依据，如实写"用户裁定"。）

## 修改内容（原子）

1. **`spec/SimRISC-00-指令系统设计.md`**：QFC 主表（`0000-0xxx` 行）、§MISC-AMO 指令编码 及其子表选择位 → `0111-0111`；检查是否与其它 MISC 子表编码冲突（**必须逐条核对全表**）。
2. **`.tao/knowledge/contract-isa.md`**：§2.7/§2.8 主表、附录 A.6/A.7、以及所有 `op = 0000-0000` / `0000-0xxx` 的引用。
3. **`contracts/opcodes.yaml`**：`illi`/`swym`/`fence`（M1）+ LR-SC（excluded）的 `op`/`mask`/`value` 同步；M1 身份与 excluded 计数**不应变化**（仅编码变化）。
4. **QEMU**：`components/qemu/patches/target/dadao/insn.decode.patch`（AMO 子表选择位）及受影响的 `trans_*` 分派；补/改探针（`swym`/`illi`/`fence` 的编码与执行）。
5. **LLVM MC**：`DADAOInstrInfo.td`（`illi`/`swym`/`fence` 的编码位）+ 相关 `AsmParser`/`Disassembler` → `0111-0111`；`tests/lit/MC/Dadao/**` 的期望字节同步。
6. **向量**：AMO 相关 `encoding` 用例的期望字节。

## 约束
- **原子**：1–6 一次改完（否则 `check_lit_bytes`/`check_patch_tree`/向量必红）。
- **构建**：QEMU `make build-qemu`（5–20 分钟）+ **LLVM 重建（预计 30–90 分钟）**——**开始长构建前先在完成区/回复写明预计耗时**；失败即停下报告，不得换方案。
- 反例注入须可复原（**含重建**）；命令缺失/失败 → 停下报告。
- 不改历史文件。

## 验收标准
1. **编码一致性**：`grep -rn "0000-0000\|0000-0xxx" spec/ .tao/knowledge/contract-isa.md contracts/` 中与 AMO 相关者 0 命中（历史文件除外，逐条说明）；新编码 `0111-0111` 在四处（spec / contract-isa / opcodes / QEMU decode）一致。
2. **无冲突**：QFC 主表全表逐条核对，`0111-0111` 与既有条目**不冲突**（给出核对表）。
3. **M1 身份/计数不变**：253 / 176（`check_interface_alignment` 的"条目数"项应仍 PASS）。
4. **LLVM**：`llvm-mc` 实测 `illi 0`/`swym 0`/`fence 0` 的新编码字节 = 契约值；`check_lit_bytes` PASS（lit 期望值已同步）。
5. **QEMU**：`make build-qemu` PASS；探针新编码可执行（或按 M1 语义 ILLI）、`check_qemu_trans --strict` 253/253。
6. **反例门控**：注入（如把某个 `op` 改回旧值 / 改坏 decode 选择位）→ `check_lit_bytes` 或探针 **FAIL**；复原（含重建）后 PASS。
7. `make check` EXIT=0；`check_interface_alignment` 80/80；`validate_vectors.py` EXIT=0（真实退出码）。
8. `git diff --name-only` 与清单对齐。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
