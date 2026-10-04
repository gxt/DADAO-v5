# INFRA-038t: 补丁 index blob hash 卫生（new file mode 补丁）

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（**无需**组件重建：仅补丁文件元数据）

## 目标与 resolved_by

处理 1 条无依赖的补丁卫生 issue（低优先级）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-119 | `new file mode` 补丁的 `index 0000000..<hash>` blob hash 与实际内容失配（pre-existing，不影响 `git apply`） |

`resolved_by`：本任务 `INFRA-038t`。

## 接口规范

- **输入**（主会话初筛：LLVM 7 项 + QEMU 2 项 = 9；本架构核实以任务执行时的**机械重算**为准）：
  - `components/llvm-project/patches/**/*.patch`、`components/qemu/patches/**/*.patch`。
  - 现状：`make check-patch-tree` **EXIT=0**（断言⑥只比对 scratch index 内容 vs `.work/source`，**不校验 patch 内 `index` 行字面 hash**）。
  - 架构快速抽检发现失配项与初筛数量可能不同（如 `DADAOInstrFormats.td`、`DADAOFixupKinds.h`、`DADAOMCAsmInfo.cpp`、`DADAODisassembler.cpp`、`trans_{arith,compare,extend,shift,block,logic}.c.inc` 等），**须以正式检查脚本的机械输出为准**。
- **输出**：修正后的 patch `index` 行（或经 `make_patch.py` / `series` 重生成），以及新增的**可复用检查器** `tools/infra/check_index_blobs.py`。
- **约束**：
  - 只改 `new file mode`（`index 0000000..<hash>`）补丁的字面 hash；**修改类**补丁（有 old hash）不能用此法判定，**不得**误改。
  - 修正后 `git apply` 行为**逐字节不变**（内容不变，仅 hash 元数据）。
  - 不得改补丁的**内容行**；禁止顺手重排 series。
  - 检查器须接入或提供 `make` 目标（若接入 `make check`，须可失败且不误报）。

## 验收标准

1. **机械重算**：`tools/infra/check_index_blobs.py` 对每个 `new file mode` 补丁按「diff 头 + `@@` 后 `+` 行内容」用 `git hash-object --stdin` 计算，与 `index` 行的新 hash 比对；修复后 **失配数 = 0**（给出逐条 before/after 输出；修复前先记录真实失配清单，替换初筛的 9 项）。
2. **不破坏应用**：修复后 `git apply --check`（在 scratch/worktree 上）对全部补丁 EXIT=0；`make check-patch-tree` EXIT=0（2 components、77 patches OK）。
3. **反例门控**：在临时副本把某 `new file mode` 补丁的 hash 改错 → 检查器 **EXIT≠0**；还原（或重新生成）→ EXIT=0。给出真实输出。
4. **修改类补丁不误判**：检查器对非 `new file mode` 补丁不产生断言（给出说明）。
5. `make check` EXIT=0。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-038t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
- 复杂命令输出留存 `.work/log/infra/INFRA-038t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-038t/`，**可复用检查器落 `tools/infra/check_index_blobs.py` 并随产物入库**。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
