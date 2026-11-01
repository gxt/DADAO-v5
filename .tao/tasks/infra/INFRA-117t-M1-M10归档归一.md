# INFRA-117t: M1–M10 归档归一（流水冻结、状态修正、M7 notes）

**模块**：infra
**项目里程碑**：M10 后（维护）
**依赖**：`INFRA-116t`（Process-04 规则与 `check_archive`；本任务完成后移除 M7 notes 临时例外）
**状态**：待开始

## 用户授权与背景

用户 2026-11-01 确认：任务流水搬入各归档 README 并从 `milestones.md` 清理；归档目录只三文件 + 模块任务；任务书必须与 README 流水对应且已验收；m 不强制；缺状态补状态；非精确状态规范化；模板统一；M7 notes 全部并入 `m7-retrospective.md` 附录并删除 `notes/`。

扫描事实（2026-11-01）：
- M1–M10 均有 README/retro/issues；任务数：M1 76、M2 150、M3 41、M4 32、M5 27、M6 47、M7 41+5 notes、M8 68、M9 68、M10 70+m。
- M9/M10 README 无任务流水；M9/M10 历史行仍在 `milestones.md`。
- M6 `INTEG-023k` 无 `**状态**`；M2 `TESTCASES-019t`/`SPEC-064t` 状态为 `已验证（…`，非精确。
- M7 `notes/` 5 份；`INTEG-027t-report.md` 内含 `待验收`。
- M8–M10 仅 INTEG m、M3 缺 qemu m、M7 多 archive m：按用户裁定不补、不删、不改；m 可选。

## 目标

1. **M9/M10 流水冻结**：
   - 把 `milestones.md` 中 M9/M10 历史行原样搬入对应 `archive/M9/README.md` / `M10/README.md` 的 `## 2 任务流水（冻结）`（状态/日期/一句改动），并补 `## 4 MEMORY 摘录`（0 行/指针）与 `## 5 指针`，按 Process-04 模板。
   - 从 `milestones.md` 删除 M9/M10 历史行；保留 M10 后/维护任务行（INFRA-113/116/117 等）与 M10 归档指针。
   - 更新 M10 README 中「保留活表」旧句为「已冻结在本 README §2」。
2. **门控适配**：
   - `check_milestones_fresh` A2：m 册任务号允许在归档任务文件名中命中，不强制活流水表有行；M9/M10 归档 m 不再导致假红。
   - `check_milestone_tasks`：按 Process-04「m 可选」处理无活 m（当前 M10 m 已归档）；不得因 M10 已归档而误报。
   - `check_archive` 去掉 M7 notes 临时例外，跑严格模式。
3. **状态修正**：
   - M6 `INTEG-023k` 补 `**状态**：已验证`（历史内容不改）。
   - M2 `TESTCASES-019t`、`SPEC-064t` 的 `**状态**` 规范为 `已验证`，括号内容移到审阅/注记。
4. **M7 notes 合并**：
   - 将 `M7/notes/` 5 份按主题并入 `M7/m7-retrospective.md` 附录：agent/规则重构、LLVM 误编译根因、写死计数判定表、门控分层设计、Embench 接入分析。
   - 删除 `M7/notes/` 目录；M7 README 指针更新；`INTEG-027t-report` 的 `待验收` 随之消失/改为历史报告。
5. **模板**：M9/M10 按统一五节；M1–M8 未缺失的保持原文，不重写大段内容；README 声明任务书与流水一一对应。
6. **验证**：`check_archive` 严格 rc=0；`check_milestones_fresh` rc=0；`make check` L1 rc=0；`milestones.md` 不再有 M1–M10 历史行；M7 notes 0；M6/M2 状态精确；M9/M10 流水条目数 = 归档任务数（排除 m/notes 口径按实际）。

## 文件范围

- `.tao/archive/M9/README.md`、`M10/README.md`（流水/模板）
- `.tao/archive/M7/m7-retrospective.md`、`.tao/archive/M7/README.md`、删除 `.tao/archive/M7/notes/**`
- `.tao/archive/M6/integ/INTEG-023k-M6启动与分解.md`
- `.tao/archive/M2/testcases/TESTCASES-019t-st源为0号寄存器用例修正.md`、`.tao/archive/M2/spec/SPEC-064t-adr0004-L49复位行对齐D7.md`
- `.tao/knowledge/milestones.md`
- `tools/infra/check_milestones_fresh.py`、`tools/infra/check_milestone_tasks.py`、`tools/infra/check_archive.py`（117 的例外移除）
- 本任务书

**不改**：M1–M10 任务内容（除上述状态入口）、M8–M10 m 数量、M3 qemu m、M7 额外 m、spec/contracts/代码。

## 验收

1. M9/M10 README 有冻结流水，行数与归档任务（去除 m）一致；`milestones.md` 无 M9/M10 历史行，只有 M10 后任务与指针。
2. `check_milestones_fresh`/`check_milestone_tasks`/`check_archive` 严格 rc=0；`check_archive --self-test` rc=0。
3. M6 `INTEG-023k` 状态精确；M2 两个状态精确。
4. `M7/notes` 不存在；5 份内容全部出现在 `m7-retrospective.md` 附录（可用 grep 标题/关键词核对）。
5. `make check` L1 rc=0；无 archive 任务内容/代码越界。
6. 证据脚本；不跑夜跑；完成区 ≤30 行。

## 5 项预检（待执行前复核）

1. 依赖 116 已完成（规则/checker）；2. 归档任务 ID/状态可机械清点；3. 验收可跑；4. 与 `milestones.md` 现场一致；5. 不触 spec/contracts/代码。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
