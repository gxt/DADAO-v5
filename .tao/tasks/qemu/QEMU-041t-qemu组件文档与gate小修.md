# QEMU-041t: QEMU 组件文档与 gate 小修（semantics gate 目录前置校验、changelog 补记）

**模块**：qemu
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 2 条无依赖的 qemu 文档/gate issue（无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-089 | `check-qemu-semantics` 的 gate 目录为瞬态，`ln -sf` 静默失败致假失败 |
| ISS-090 | `components/qemu/changelog.md` 缺任务级记录（自 2026-09-23 起未按任务追加） |

`resolved_by`：本任务 `QEMU-041t`。

## 接口规范

- **输入**（已核实）：
  - `Makefile:337-351`（`check-qemu-semantics`）：`ln -sf ... 2>/dev/null` 掩盖失败；gate 目录 `$(TEST_ARTIFACTS_DIR)/harness/gate` 为瞬态，失败时 `rm -rf` 后无显式诊断。
  - `components/qemu/changelog.md`：末条为 `QEMU-038t`（2026-10-04）；缺 `QEMU-040t`（`sub.o_orrr_dbb` trans，`.tao/tasks/qemu/QEMU-040t-sub-rb-rb-trans.md`）等 2026-10-04 之后的条目。规范依据 `spec/Process-01 §10`（按任务一条）。
- **输出**：`Makefile`（gate 前置校验）+ `components/qemu/changelog.md`（补记）。
- **约束**：
  - ISS-089：在 `check-qemu-semantics` 中**显式校验** gate 目录存在与两个 symlink 指向正确（`ln -sf` 去掉 `2>/dev/null` 或改为先 `test -e` 再建）；symlink 失败须**非零退出并打印明确原因**，不得静默。
  - ISS-090：补记须**逐任务一条**、日期/任务号/变更摘要真实；只补**尚未记录**的 qemu 任务（先 `git log --grep QEMU-` 对照现有条目，避免重复）。历史条目不改写。

## 验收标准

1. **ISS-089**：在 gate 目录/symlink 被人为破坏（如预先占用同名路径）时，`make check-qemu-semantics` **非零退出**且打印明确诊断（非静默）；正常时 EXIT=0 并保留原日志行为（`.work/log/qemu/check-qemu-semantics.log`）。给出注入→FAIL→还原→PASS 的真实输出。
2. **ISS-090**：`git log --oneline --grep 'QEMU-0' -- components/qemu/patches`（或按任务提交）列出的 2026-10-04 后 qemu 任务，在 `changelog.md` 中**逐条有记录**；给出「任务清单 ↔ changelog 行」逐条对照。当前至少需补 `QEMU-040t`。
3. **反例门控**：删除 changelog 中刚补的 `QEMU-040t` 行（临时副本）⇒ 验收 2 的对照 FAIL；还原。gate 目录注入见验收 1。
4. `make check-qemu-semantics` 正常路径 EXIT=0；`Makefile` 改动后 `make check` 的相关门控不回归（文档改动豁免）。

## 硬约束

- 临时目录 `/tmp/opencode/QEMU-041t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/qemu/QEMU-041t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/QEMU-041t/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
