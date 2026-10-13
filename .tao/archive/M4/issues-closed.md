# M4 阶段已关闭 Issue（≤ 2026-10-07）

> **来源**：`INTEG-018t`（2026-10-07）从 `.tao/knowledge/issues.yaml` 提取——**M4 阶段已 `closed` 的 issue**。
>
> **判据**：M4 达成 = **2026-10-07**（commit `cfcb64d`，`milestones.md` M4 置达成）。`resolved_by` 对应任务提交日 ≤ 2026-10-07（实测 `git log --grep <taskID>`；边界「≤ 达成日」）。
>
> **未提取**：M1 阶段（≤ 2026-09-22）的 8 条见 `.tao/archive/M1/issues-closed.md`；M2 阶段（2026-09-23 ~ 2026-10-04）的 41 条见 `.tao/archive/M2/issues-closed.md`；M3 阶段（≤ 2026-10-05）的 56 条见 `.tao/archive/M3/issues-closed.md`；本次提取后活台账 `.tao/knowledge/issues.yaml` 仅保留 open 项。

**共 12 条**（按原 `issues.yaml` 顺序）。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-008` | Object ABI / ELF 合约重定位（D2/D3/D4）Deferred to M2——M1 单 TU 自包含不产生重定位 | [M4] | LLVM-050t/056t + ADR-0019 (SPEC-105t) |
| `ISS-011` | 编码知识：0.5.4 MISC 子表 ha=RRR-CCC 拼为 6 位；旧 tools/opcodes.yaml（0628）不可作编码权威 | [spec] | moot（2026-10-06 用户裁定） |
| `ISS-014` | ADR-0005 Consequences C2 表述可更精确——select_source() 完成解析、sync_mirror 只接收 source_url | [infra] | moot（2026-10-06 用户裁定） |
| `ISS-038` | F3 — ELF writer 存根是死代码：DADAOMCTargetDesc.cpp 未注册 ELFObjectWriter | [llvm] | LLVM-006t + LLVM-050t |
| `ISS-044` | 未定义符号静默为 0（LLVM-006t reviewer ③）：call ext_sym 立即数保持 0、无错误 | [llvm] | LLVM-050t |
| `ISS-050` | dadao_cpu_tlb_fill 未用 access_type / 未做 48 位屏蔽——skeleton 无访存指令故不可达 | [qemu] | moot（2026-10-06 用户裁定） |
| `ISS-117` | check_interface_alignment.py 的 e_flags 检测行尾/块注释误命中（假绿，本产物无触发） | [integ] | INTEG-006t |
| `ISS-142` | 未定义外部符号 / 跨 section 引用静默留 0 且不落 relocation（完整重定位→M4） | [llvm] | LLVM-050t |
| `ISS-152` | LLVM-055t 遗留：未加 .ll codegen lit 向量（CodeGen/DADAO 占位 suite 未接 make check-lit） | [llvm] | INTEG-016t |
| `ISS-153` | 自定义 reloc 类型编号含 0（R_DADAO_ABS48=0）与 LLD 默认 0 值哨兵冲突，须显式设 TargetInfo 哨兵字段 | [llvm] | LLVM-056t |
| `ISS-155` | FILEHDR PHDRS 使 ELF 头落在 RAM 下方一页 + .text 字面 sh_offset≠0；QEMU ELF 加载器/集成须对齐 | [qemu, integ] | SPEC-112t |
| `ISS-158` | DADAOInstrInfo::insertBranch 未实现 → llc SIGABRT(134)（loop + 跨 TU call + 后置等值守卫） | [llvm] | LLVM-059t |

## 判定表（逐条：resolved_by → 提交日 ≤ 2026-10-07）

| id | resolved_by（提交） | 提交日（`git log --grep`） | 判定 |
| --- | --- | --- | --- |
| `ISS-008` | LLVM-050t / LLVM-056t / SPEC-105t | 2026-10-06 | ✅ 提取 |
| `ISS-011` | moot（2026-10-06 用户裁定；核查提交 bdbcfd2） | 2026-10-07 | ✅ 提取 |
| `ISS-014` | moot（2026-10-06 用户裁定；核查提交 bdbcfd2） | 2026-10-07 | ✅ 提取 |
| `ISS-038` | LLVM-006t（2026-09-18）/ LLVM-050t | 2026-10-06 | ✅ 提取 |
| `ISS-044` | LLVM-050t | 2026-10-06 | ✅ 提取 |
| `ISS-050` | moot（2026-10-06 用户裁定；核查提交 bdbcfd2） | 2026-10-07 | ✅ 提取 |
| `ISS-117` | INTEG-006t | 2026-09-29 | ✅ 提取 |
| `ISS-142` | LLVM-050t | 2026-10-06 | ✅ 提取 |
| `ISS-152` | INTEG-016t | 2026-10-06 | ✅ 提取 |
| `ISS-153` | LLVM-056t | 2026-10-06 | ✅ 提取 |
| `ISS-155` | SPEC-112t | 2026-10-06 | ✅ 提取 |
| `ISS-158` | LLVM-059t | 2026-10-06 | ✅ 提取 |
