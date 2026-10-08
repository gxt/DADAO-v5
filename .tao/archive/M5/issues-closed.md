# M5 阶段已关闭 Issue（≤ 2026-10-08）

> **来源**：`INTEG-022t`（2026-10-08）从 `.tao/knowledge/issues.yaml` 提取——**M5 阶段已 `closed` 的 issue**。
>
> **判据**：M5 达成 = **2026-10-08**（`milestones.md` M5 置「✅ 达成」）。`resolved_by` 对应任务提交日 ≤ 2026-10-08（实测 `git log --grep <taskID>`；边界「≤ 达成日」）。
>
> **未提取**：M1 阶段（≤ 2026-09-22）的 8 条见 `.tao/archive/M1/issues-closed.md`；M2 阶段（2026-09-23 ~ 2026-10-04）的 41 条见 `.tao/archive/M2/issues-closed.md`；M3 阶段（≤ 2026-10-05）的 56 条见 `.tao/archive/M3/issues-closed.md`；M4 阶段（2026-10-06 ~ 2026-10-07）的 12 条见 `.tao/archive/M4/issues-closed.md`；本次提取后活台账 `.tao/knowledge/issues.yaml` 仅保留 open 项。
>
> **注**：`ISS-170`/`ISS-171` 为 `INTEG-022t`（`Process-04 §3` 步骤 4「**里程碑边界项拆分**」）**本轮新增**的 `closed` 条目——由边界项 `ISS-003`/`ISS-110` 的**已交付部分**拆出、单独建档（原 id 保留给未交付的 open 余项、不复用）；其 `resolved_by` 提交日 ≤ 达成日 ⇒ 计入 M5 阶段。

**共 5 条**（按原 `issues.yaml` 顺序）。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-147` | INTEG-012t E2E 期望值落入 fault 区 0x80–0xFF（137==0x89==UNDI）→ false-PASS 风险 | [testcases] | TESTCASES-034t |
| `ISS-157` | 汇编助记符大小写不敏感（spec 要求）当前未实现且未测——→ SPEC-116t 以「条款撤销」结案 | [llvm, spec] | SPEC-116t |
| `ISS-166` | Machine-01 §1 未完全覆盖越界路由口径与 RAM@0 容量（QEMU-049t 已落地三条）→ 已由 SPEC-121t 承接（用户授权 2026-10-08） | [spec, qemu, M5] | SPEC-121t |
| `ISS-170` | 【边界交付项】ISS-003 的「特权 cfx 系统指令」部分已由 M5 交付（trap/escape/cfx2rc/cfx2rd MC+编码+执行） | [spec, llvm, qemu, M5] | LLVM-060t + SPEC-115t |
| `ISS-171` | 【边界交付项】ISS-110 的「trap/escape/cfx2rc/cfx2rd」部分已由 M5 交付（MC+编码+re-scope） | [llvm, spec, qemu, M5] | LLVM-060t + SPEC-115t |

## 判定表（逐条：`resolved_by` → 提交日 ≤ 2026-10-08）

| id | resolved_by（提交） | 提交日（`git log --grep`） | 判定 |
| --- | --- | --- | --- |
| `ISS-147` | TESTCASES-034t（`b26f426`） | 2026-10-08 | ✅ 提取 |
| `ISS-157` | SPEC-116t（`fb11470`） | 2026-10-08 | ✅ 提取 |
| `ISS-166` | SPEC-121t（`e056f52`） | 2026-10-08 | ✅ 提取 |
| `ISS-170` | LLVM-060t（`ebb9ef2`，2026-10-07）+ SPEC-115t（`7529ed2`，2026-10-08） | ≤ 2026-10-08 | ✅ 提取（边界交付项，本轮新增） |
| `ISS-171` | LLVM-060t（`ebb9ef2`，2026-10-07）+ SPEC-115t（`7529ed2`，2026-10-08） | ≤ 2026-10-08 | ✅ 提取（边界交付项，本轮新增） |
