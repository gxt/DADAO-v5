# 项目里程碑

> **项目里程碑 = M18**（M18 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12–M17 各另有分册）

> **本页只维护 M18 任务台账**：历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M18 定位（用户 2026-11-20）**：**Linux 测试集（选择与修复）**；**K6 从 M14 移入**作为入口批次（原 `m14-linux-032/033/034` → `m18-linux-001/002/003`）。M14 的收口判据相应收到 **K5（`m14-linux-029`）+ K3 退役**，M14 不再声称「能当 Linux 用」。
> **测试集部分待拆**：套件选型（LTP 子集 / kselftest / 两者分工）、运行环境（先 QEMU system）、失败分诊口径、按子系统分片——见 `discussing.md`「Linux 测试集（选择与修复）」。
> **已知缺口（不立行，待后续批次）**：`pthread` create/join（`m14-linux-029` 判为 K6 范围）尚无任务书；用户 2026-11-20 定「建册时再定」⇒ 本册先不立行。
>
> **测试集口径（用户 2026-11-22）**：
> - **两套件都跑**：`kselftest` 先（与内核同源、粒度细、回归快），`LTP` 子集后（系统调用/ABI 广度、对外可用性证据）；两者共用同一运行骨架。
> - **不以开发阶段现状为边界**：缺 `ldso` 就补（`m18-infra-002`）；4 KiB 页假设的用例**改成 64 KiB 页**；因客观原因无法完成的用例必须记录（原因/证据/影响/复评条件），**禁静默跳过**。
> - **运行环境**：先 QEMU system `kaiwu-vast`（`ADR-0052 D2`）；chipyard RTL 无 MMU/TLB，节点 RTL Linux 不在本册。
> - **分诊四分类**：`KERNEL_BUG` / `TEST_ADAPT` / `UNSUPPORTED` / `SUITE_ENV`；每条非 PASS 必须有一条在库记录。
> - **首轮目标不是通过率**，而是「每个失败都有归类和证据」；收口门控 `check-linux-suite` 留到收口任务。
> - **批次授权 M18-A（2026-11-22）**：清单 `m18-linux-005`（套件骨架 + kselftest 试点）、`m18-infra-002`（musl ldso 动态链接闭环）；停止点按 `AGENTS.md §1`。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m18-linux-007 | 2–3 h | pthread create/join 闭环（K6 缺口；静态优先，动态待 002） |
| m18-linux-008 | 2–3 h | K1–K4 门控断言补强（ISS-444/457/487/488；可达 FAIL + §4a 退役） |
| m18-linux-009 | 2–3 h | K4 探针稳定性（ISS-493 F5 改 `task_pt_regs(current)` / ISS-494 有界等待；连跑 20 次） |
| m18-linux-010 | 30 min | ISS-486 措辞订正（libc 侧检查；3 处注释/文档，产物不变） |
| m18-linux-011 | 30 min | ISS-496 applet 计数改按白名单/符号表派生（去 `enabled - infra` 抵消假设） |
| m18-linux-012 | 1–2 h | ISS-503 K6 门控五条 finding（恒真断言并入 region、计数/标签/符号名订正） |
| m18-qemu-001 | 2–3 h | ISS-501 `lr`/`sc` 窄宽度条件写丢失（`gen_sc` + 同址窄 CAS 向量） |
| m18-spec-001 | 2–4 h | cg4 `scratch_regs_num` 缺省值：每个非 reserved cfx = 2（QEMU/gem5/RTL 由 4 改 2）；spec/契约 + 探针 |
| m18-llvm-001 | 2–3 h | LLVM `escape` frame selector 汇编/反汇编 + lit |
| m18-qemu-004 | 4–6 h | QEMU hart-first 异步仲裁（`cfx_hart cg9`、cause 17/18、escape bit1；对照 qemu-002 骨架） |
| m18-testcases-001 | 1–2 h | 旧异步探针 094t/050t 迁 hart-first（投 cfx_hart、pending cg9、mask 位源 cfxha） |
| m18-linux-015 | 2–3 h | `mlock2`/`MLOCK_ONFAULT` 路径 SIGSEGV（KERNEL_BUG） |
| m18-linux-016 | 2–3 h | `futex_waitv` 返回 EINVAL（多等待接口缺失；KERNEL_BUG） |
| m18-linux-017 | 3–4 h | `clock_nanosleep(TIMER_ABSTIME)` 整机停摆（KERNEL_BUG） |
| m18-linux-018 | 2–3 h | 套件环境补齐（TMPFS/MEMFD、非 root uid、`/proc/iomem`；SUITE_ENV） |
| m18-linux-019 | 1–2 h | `k5_syscall_selftest` 锁外 `find_vma` 触发 rwsem 警告（014 复核发现） |
| m18-infra-003 | 2–3 h | musl 补丁集同步（ISS-507）与信号帧复核（纠正 006 的「无信号帧 ABI」误判；`p_raise3` 反证内核帧可用） |

> **已作废（2026-11-23，ADR-0060）**：`m18-qemu-002`（monitor-first QEMU）reviewer Accepted 但**不合入 master**，分支留参考；`m18-qemu-003`（旧探针迁 monitor-first）未开工、被 hart-first 取代。

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m18-spec-003 | 2026-11-23 13:46 | 2–3 h | `escape` frame selector 编码真源（SimRISC-11/IDL/Toolchain-01/contract-asm/Kaiwu/opcodes/legality） |
| m18-linux-006 | 2026-11-23 02:40 | 3–5 h | LTP 子集接入（源 tag `20260930`，commit `2279d708…`；组件锁 + 静态构建 + 分诊）；复用 005 骨架 |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m18-linux-013 | 2026-11-23 13:45 | **作废**（ADR-0060）：monitor-first 内核异步方案，未开工 |
| m18-qemu-002 | 2026-11-23 13:45 | **作废**（ADR-0060）：monitor-first QEMU，reviewer Accepted 但未合入，分支留参考 |
| m18-qemu-003 | 2026-11-23 13:45 | **作废**（ADR-0060）：旧探针迁 monitor-first，未开工 |
| m18-spec-002 | 2026-11-23 13:45 | hart-first/cg9 规格与契约同步（`§5.2`/cg9/`§4.7`/`§4.9`/`escape` frame selector；DADAO-23 同步；版本仍 0.8.0-rc） |
| m18-infra-002 | 2026-11-23 02:40 | musl ldso 动态链接运行闭环（P3；system/qemu-user rc=42、pthread/dlopen/TLS/errno 实测；libc.a 不变；零内核/musl 补丁） |
| m18-linux-014 | 2026-11-23 01:23 | COW 共享文件页 `VM_FAULT_COMPLETED` 双重解锁修复（`fault.c`；5/5 PASS，无 rwsem 警告/停摆；53+14/15 证据项） |
| m18-linux-005 | 2026-11-22 19:37 | 测试集运行骨架 + kselftest 试点（8 例：PASS1/FAIL2/SKIP2/SIGNAL1/TIMEOUT2；套件校验 23/23；补丁 manifest 双向+逐补丁增量校验） |
| m18-linux-003 | 2026-11-22 10:34 | K6 收口门控 `check-linux-k6`（71/71；§4a.3 退役审计；L2） |
| m18-infra-001 | 2026-11-22 09:32 | musl mallocng 根因修复（`a_cas` 改 8 字节字 CAS；ISS-497/499 关闭；K6 长脚本单次跑通） |
| m18-linux-004 | 2026-11-22 08:33 | K6 用户入口异步投递修复（ISS-498）+ 控制台行缓冲；200/200 启动、长脚本 27 条 |
| m18-linux-002 | 2026-11-22 05:31 | K6 基础命令回归（sh 内 5 条 + mkdir/ls/rm 组合；50/50；长脚本崩溃登记 ISS-497） |
| m18-linux-001 | 2026-11-22 04:32 | K6 shell 启动（busybox sh + semihosting 控制台 + 前台执行，无作业控制；28/28） |
