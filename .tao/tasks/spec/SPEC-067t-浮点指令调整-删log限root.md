# SPEC-067t: 浮点指令调整——删除 `ftlog`/`folog`、`ftroot`/`foroot` 仅支持 n=2

**模块**：spec（含 `contracts/`）；**影响**：向量/工具（浮点整体属 M1 外 ⇒ QEMU/LLVM 影响有限，须核实）
**项目里程碑**：M2
**依赖**：用户裁定（2026-10-01）
**状态**：待开始（**已下发**）

## 用户裁定（唯一真源）

1. **删除 `ftlog`/`folog`**（及其规则 `fp_log_invalid_base`）。
2. **`ftroot`/`foroot` 仅支持 `n = 2`**（`encode_fp_root_n` 定稿；后续指令系统会再调整）。

## 修改内容（原子）

1. **`contracts/opcodes.yaml`**：删除 `ftlog_orri_rf`、`folog_orri_rf` 两条记录（含 `excluded_m1` 计数变化：253 → 251，excluded 77 → 75）；`ftroot_orri_rf`/`foroot_orri_rf` 的 `legality` 若表达 n 的约束，改为仅允许 n=2。
2. **`contracts/legality_rules.yaml`**：删除 `fp_log_invalid_base`；`fp_root_invalid_n` 的 description 改为"仅支持 n=2"（id 拟改 `encode_fp_root_n`——**改名是否在本任务内做，见「待定」**）。
3. **`spec/SimRISC-07-浮点运算.md`**：删除 `ftlog`/`folog` 的指令条目、编码表项与说明；`ftroot`/`foroot` 说明改为仅支持 n=2。
4. **`.tao/knowledge/contract-isa.md`**：§9/附录中浮点条目同步。
5. **向量/工具**：`tests/vectors/**` 与生成器中若含 `ftlog`/`folog` 条目 → 删除；`ftroot`/`foroot` 用例同步 n=2。
6. **QEMU/LLVM**：浮点属 M1 外（`excluded_m1`，decode ILLI）⇒ 须核实是否有显式条目需同步（给出 grep 证据）。

## 待定（engineer 须先停下询问，不得自行决定）
- **`fp_root_invalid_n` → `encode_fp_root_n` 的改名**是否在本任务内做？（合法性清单的统一改名尚未启动；若不在本任务做，须在完成区登记为待办。）

## 约束
- **原子**：contracts + spec + 向量/工具一次改完。
- 反例注入须可复原；命令缺失/失败 → 停下报告。
- 不改历史文件。

## 验收标准
1. `grep -rn "ftlog\|folog" contracts/ spec/ tests/ tools/` → **0 命中**（历史文件除外，须逐条说明）。
2. `opcodes.yaml` 总数 **251**（含 excluded 75）——**与 `inventory.md`/`check_interface_alignment` 一致**（注意：`check_interface_alignment.py` 的计数断言已于 `INTEG-007t` 改为跨载体推导，须能反映本次变化 ✓）；`validate_vectors.py` **EXIT=0**。
3. `ftroot`/`foroot` 说明 = 仅 n=2；`fp_root_invalid_n` description 同步。
4. **反例门控**：注入（如把 `ftlog` 加回 / 把 root 的 n 允许值写回 {2,3}）→ 相应检查 **FAIL**；复原 PASS。
5. `make check` EXIT=0；`check_interface_alignment` 80/80；`check_qemu_trans --strict`（若 253→251，须说明其计数口径如何随契约变化，**不得**直接改数字凑绿）。
6. `git diff --name-only` 与清单对齐。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
