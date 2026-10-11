# INTEG-028t: 7 条「待收敛」issue 逐条核实与回填关闭

**模块**：integ
**项目里程碑**：M6（收尾遗留收口）
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范
- 输入：`.work/log/integ/ISS-reconcile.md`（7 条独立核实证据，285 行）；`.tao/knowledge/issues.yaml` 中 7 条 `open` 条目。
- 输出：`issues.yaml` 7 条回填 `resolved_by` + `status: closed`；归档快照与 `milestones.md` 追加收敛说明（只追加）。
- 约束：仅改 7 条的 `status`/`resolved_by` 字段；不改描述、不改其它条目；只追加不改历史；不 push。

## 验收标准
1. 7 条 `status: closed` + `resolved_by` 正确（043/045/148/159/162→`LLVM-062t`、138→`LLVM-064t`、156→`SPEC-123t`）。
2. `python3 tools/infra/check_issues.py` **rc=0**，计数 17 open / 7 closed。
3. 归档快照 `issues-closed.md`、台账 `milestones.md` 追加收敛说明；历史段未改写。

## 完成区

**测试结果**：`python3 tools/infra/check_issues.py` → `check_issues: 17 open, 7 closed (0 blocking M1-gate: 0)`，**RC=0**。

**7 条判定表**（依据 `.work/log/integ/ISS-reconcile.md`，逐条独立核实）：

| id | 判定 | 关键证据 | resolved_by |
|----|------|----------|-------------|
| ISS-043 | ✅ 已修（可关） | `llvm-mc` 越界分支 rc=1（显式 `error:`）；范围内 rc=0 | LLVM-062t |
| ISS-045 | ✅ 已修（可关） | `getFixupKindForInstr` `default: report_fatal_error`（白名单枚举） | LLVM-062t |
| ISS-138 | ✅ 已修（可关） | `llc` 200KB 帧 rc=0；form3 `set.zw+or.w+add.o` | LLVM-064t |
| ISS-148 | ✅ 已修（可关） | 两脚本 `grep -c '177'` = 0（消除硬编码计数） | LLVM-062t |
| ISS-156 | ✅ 已修（可关） | `Toolchain-01 §6.1` 已修订；实现 `V==0→rd2rf` 一致 | SPEC-123t |
| ISS-159 | ✅ 已修（可关） | `llc` rc=0；`not→xnor.o`、`neg→sub.so/sb/sw/st` | LLVM-062t |
| ISS-162 | ✅ 已修（可关） | `Match_Dummy=FIRST_TARGET_MATCH_RESULT_TY` + `static_assert` | LLVM-062t |

**修改文件**：
- `.tao/knowledge/issues.yaml`（7 条回填 + 头部追加收敛说明）
- `.tao/archive/M6/issues-closed.md`（追加「已收敛」段）
- `.tao/knowledge/milestones.md`（追加「已收敛」指针）
- `.tao/tasks/integ/INTEG-028t-待收敛issue核实回填.md`（本任务书）

**验收结果**：1 ✓（7 条字段正确）；2 ✓（`check_issues` rc=0，17/7）；3 ✓（追加、未改历史）。

**新发现/坑**：`.tao/tasks/` 已于 M6 归档（INTEG-026m `git mv`）不复存在，本任务书按约定新建 `.tao/tasks/integ/`。

**遗留问题**：无。

## 审阅记录

#### 第 1 轮 用户裁定（原话）
> 用户：「7条待收敛的issues，请先逐条核实」。
（核实由 reviewer 独立执行，证据 `.work/log/integ/ISS-reconcile.md`：7 条全部「已修（可关）」；本任务据其回填。）
