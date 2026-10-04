# INFRA-040t: 历史/归档类 issue 核实与关闭（moot 判定）

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（核实 + 台账收口；**禁止改动 `.tao/archive/**`**）

## 目标与 resolved_by

下列 issue 或涉及**已归档/已验证**的历史任务，或已因后续任务消解。本任务独立复核后**关闭为 moot/resolved**（或在可动范围内处置）。预期关闭：

| ISS | 架构初判（须独立复核） |
| --- | --- |
| ISS-051 | `v11.x` 目录变更（`target/riscv/translate.c`→`tcg/`）与本仓 DADAO 无补丁交集（补丁树仅 `target/dadao/**`）⇒ moot |
| ISS-052 | harness 跨任务依赖：`QEMU-005t/006t/008t` 均 `已验证`，`ADR-0010 D1 修法 a` 已落地 ⇒ resolved |
| ISS-053 | `andn.w-rb` 归属：architect 裁定保留在 `006t` 且已登记（`006t` `已验证`）⇒ resolved |
| ISS-068 | mem-rd 窄 load 归因：由 `QEMU-023t`（`build_loader()` 按宽度写）修复、`已验证` ⇒ resolved |
| ISS-080 | `SPEC-066t/067t` 完成区「修改文件」回填：两任务书**已归档**（`.tao/archive/M2/spec/`），archive 只读 ⇒ moot（回填不可行） |
| ISS-111 | `QEMU-033t` 任务书措辞订正：任务书**已归档**（`.tao/archive/M2/qemu/`），改 archive 不可行 ⇒ 措辞部分 moot；探针保留问题按现状评估处置 |

`resolved_by`：历史类填**实际修复任务**（如 `QEMU-023t`）；moot 类填本任务 `INFRA-040t`，`notes` 注明「moot：归档只读/无交集」。

## 接口规范

- **输入**：
  - `.tao/archive/M1/qemu/QEMU-005t/006t/008t/023t*.md`（只读）；
  - `.tao/archive/M2/qemu/QEMU-033t-mreg_range_overlap运行期ILLI.md`（只读）；
  - `.tao/archive/M2/spec/SPEC-066t*.md`、`SPEC-067t*.md`（只读）；
  - `tools/qemu/min_rom_probe_033t.py`、`.work/build/qemu/qemu-system-dadao`（若可用）。
- **输出**：`issues.yaml` 中对应条目 `status: closed` + `resolved_by` + `notes`（moot 理由）。
- **约束**：
  - **禁止修改 `.tao/archive/**`**（已归档 = 只读）。ISS-080/111 的「订正归档任务书」诉求**不可执行**，只能按 moot 关闭或转「遗留问题」。
  - ISS-111 的**探针保留**部分：运行 `min_rom_probe_033t.py` 记录现状；若失败项与本改动无关且无价值，可提出退役/保留建议（**不改探针代码**，仅建议；如需改另立任务）。
  - 只改 `issues.yaml` 的 `status`/`resolved_by`/`notes`，不删条目、不改 title/scope。
  - 关闭后 `check_issues.py` 无 INVALID STATUS。

## 验收标准

1. 逐条给出**可复现证据**：
   - ISS-051：`find components/qemu/patches -path '*riscv*'` 为空；补丁树仅 `target/dadao/**`。
   - ISS-052/053：对应归档任务书 `**状态**：已验证` + `ADR-0010` 落地条目。
   - ISS-068：`QEMU-023t` 完成区「24 条窄 load FAIL→PASS」证据行 + 现状 harness 宽度逻辑（若有改动须说明）。
   - ISS-080/111：确认对应任务书位于 `.tao/archive/` 且 M2 已归档。
2. **探针现状**（ISS-111）：若 `.work/build/qemu/qemu-system-dadao` 可用，运行 `python3 tools/qemu/min_rom_probe_033t.py` 记录真实结果与退出码；不可用则标注 BLOCKED（原因 + 替代证据）。
3. 反例思路：对 ISS-051，证明「若补丁树含 riscv 路径则本结论不成立」——给出 `grep -rl riscv components/qemu/patches` 实测；对 ISS-068，给出 QEMU-023t 的改前/改后对比行。
4. `python3 tools/infra/check_issues.py` **EXIT=0**；open 数减少至下界。
5. `git diff .tao/knowledge/issues.yaml` 仅含上述字段变更。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-040t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件（含 `issues.yaml`），越界须披露；**不触碰 `.tao/archive/**`**。
- 复杂命令输出留存 `.work/log/infra/INFRA-040t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-040t/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
