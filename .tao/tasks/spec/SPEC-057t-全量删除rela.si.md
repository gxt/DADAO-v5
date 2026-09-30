# SPEC-057t: 全量删除 `rela.si`（跨 spec/qemu/llvm/testcases 原子变更）

**模块**：spec（**跨模块**：`spec/`+`contracts/`+`tools/`+`components/qemu`+`components/llvm-project`+`tests/`）
**项目里程碑**：M1→M2
**依赖**：`SPEC-056t`（`ADR-0012 D5` Accepted）
**状态**：待开始

## 为什么是一个原子任务

`opcodes.yaml` 是**单一真源**：`check_qemu_trans`、`validate_vectors`、`check_lit_bytes`、`check_interface_alignment` 都以它为准。**删 `rela.si` 必然同时改动契约与全部消费者**，任何拆分会留下「红门控」中间态（架构师预检结论，用户裁定「甲」）。故本任务**必须一次性把契约与所有消费者同步**，结束 `make check` **绿**。

## 目标（`ADR-0012 D5`）

从 SimRISC 0.5.4 **删除 `rela.si`**（`riii`，`rbha, imms18`，op **`0x5A`**）；`0x5A` → **UNDI**。指令总数 **254 → 253**，M1 身份 **177 → 176**。**不预设替代方案**（遇具体问题再问用户）。

## 修改内容（逐项）

### A. 契约与生成源

1. `tools/spec/generate_opcodes.py`：移除 `rela.si_riii_rb` 条目；`0x5A` 单元 → 空/保留（解码 **UNDI**）
2. 重生成 `contracts/opcodes.yaml`
3. 重生成 `docs/assembly-list.md` + 12 个 `spec/SimRISC-*.md` 内嵌速查表（`tools/llvm/gen_asm_list.py`）
4. `tools/llvm/gen_asm_list.py`：若 `classify()`/`SECTION_ORDER` 有针对 `rela` 的规则，同步清理

### B. spec/

5. `spec/SimRISC-12-待定.md`：删除 §PC相对寻址（`rela.si`）整节
6. `spec/SimRISC-00-指令系统设计.md`：QFC 表 / 格式表（`0x5A` 行）与
7. `spec/SimRISC-06-控制流.md`：如引用 `rela.si` 则清理
8. `docs/spec/assembly-language.md`：§特例中的 `rela.si` 行

### C. QEMU

9. `components/qemu/patches/target/dadao/insn.decode`：删 `rela_si_riii_rb`
10. `.../insn_trans/trans_ctrl.c.inc`：删 `trans_rela_si_riii_rb`
11. 重建（`make prepare` + `make build-qemu`）→ `check_qemu_trans` **253/253（M1 176/176）**

### D. LLVM MC

12. `components/llvm-project/patches/.../DADAOInstrFormats.td`、`DADAOInstrInfo.td`、`MCTargetDesc/DADAOAsmBackend.cpp`、`MCTargetDesc/DADAOFixupKinds.h`、`MCTargetDesc/DADAOMCInstPrinter.cpp`：移除 `rela.si`
13. 重建 `make build-mc`；`llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` 计数更新且全绿

### E. 向量与工具

14. `tests/vectors/isa/reg-arith.yaml`：删 `rela.si` 用例（encoding/legality/semantic/boundary）
15. `tests/vectors/inventory.md`：**177 → 176**
16. `tests/vectors/isa/reserved.yaml`（或等价）：补 `0x5A` → **UNDI** 的保留编码用例
17. `tools/testcases/generate_isa_vectors.py`、`tools/testcases/009t-audit.py`、`tools/qemu/check_005t_coverage.py`、`tools/qemu/min_rom_probe_008t.py`、`min_rom_probe_009t.py`：同步
18. `docs/impact-matrix.md`：同步

### F. 不得改

`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`、已完成 `.tao/tasks/**`、`deferred.md` 历史条目。

## 约束

- 补丁集组织以 `docs/spec/component-patching.md` 为准（树形 + 一文件一补丁 + `git apply`）
- **期望值独立推导**；不得从 LLVM/QEMU 输出反填
- 反例注入须**可复原且须重建**
- 命令缺失/构建失败 → 停下报告，禁止自行安装

## 验收标准

1. `rela.si` 在 spec/`opcodes.yaml`/`assembly-list`/12 内嵌表/QEMU/LLVM MC/向量/工具中**全部消失**；`0x5A` → **UNDI**（保留编码用例存在）
2. 计数：指令 **253**、M1 身份 **176**、`check_qemu_trans` **253/253（M1 176/176）**、`validate_vectors` **176/176**
3. `make check` **EXIT=0**；`llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` 全绿（计数如实更新）
4. 全量 grep：`grep -rn "rela\.si\|rela_si"` 仅命中**历史不变量**文件（逐个列明）
5. 反例注入：把 `rela.si` 加回任一处 → 相应门控**报错**；复原+重建后全绿
6. 无未终态的半成品（本任务结束即 `make check` 绿）

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
