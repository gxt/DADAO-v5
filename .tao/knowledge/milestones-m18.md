# 项目里程碑

> **项目里程碑 = M18**（M18 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12–M17 各另有分册）

> **本页只维护 M18 任务台账**：历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **派单归属（用户 2026-11-23）**：**M18 任务只在 M18 会话派发**；M16 会话只派 M16 任务，不在此册派单。待 M18 会话派发：`m18-qemu-005`「QEMU 异步模型修订（掩码归 monitor、源位图、cg9 七槽）」（依赖 `m18-spec-004` 合入）、`m18-testcases-003`「旧异步探针迁新模型 + `escape` cg9 向量」（依赖 qemu-005）、`m18-linux-022`「内核异步新模型（掩码归 monitor、源位图、一帧多源）」（依赖 qemu-005）、`m18-spec-005`「活文档旧口径残留收尾（ISS-527）」（待立册）。`m18-spec-004`「异步模型修订（掩码归 monitor、源索引统一 cfxha、cg9 七槽）」在 M16 会话已收口并合入。

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
| m18-llvm-002 | 2–3 h | **链①** LLVM/opcodes `escape cfxHA`（汇编/反汇编/legality/生成物；等 `m20-llvm-003` 释放 LLVM 写者） |
| m18-testcases-004 | 3–4 h | **链②** 异步 escape 出口帧向量与探针（cg5/cg9 新布局、escape 五类判据；依赖 ①） |
| m18-chipyard-002 | 4–6 h | **链④** RTL 异步 escape 出口（依赖 ①②；等 M16 chipyard 写者窗口） |
| m18-gem5-004 | 3–4 h | **链⑤** gem5 异步 escape 出口（依赖 ①②） |
| m18-idl-003 | 3–4 h | **链⑥** IDL 执行器/IDL-ISA 迁移（依赖 ②；补 spec-007 的 F3） |
| m18-linux-026 | 4–6 h | 内核迁移到异步 escape（去 jmon、`cg5 rc8–rc11` 出口、`escape cfx_hart`）；等 `m18-qemu-008` 合入 |
| m18-linux-025 | 3–5 h | 用户态异步投递在 LTP 负载下自旋（≈70%，`ISS-m18-001` 族）；**等 026 内核移植后在新模型上修**（用户裁定 B） |
| m18-qemu-007 | 2–3 h | QEMU system 移除 `cfx_jmon`（cfx1）实现（无设计、RTL 亦无）；`trap/访问` ⇒ CFXREG；**须等「异步 escape」规范与内核换帧都落地后再合入** |
| m18-linux-007 | 2–3 h | pthread create/join 闭环（K6 缺口；静态优先，动态待 002） |
| m18-linux-009 | 2–3 h | K4 探针稳定性（ISS-493 F5 改 `task_pt_regs(current)` / ISS-494 有界等待；连跑 20 次） |
| m18-spec-001 | 2–4 h | cg4 `scratch_regs_num` 缺省值：每个非 reserved cfx = 2（QEMU/gem5/RTL 由 4 改 2）；spec/契约 + 探针 |
| m18-linux-016 | 2–3 h | `futex_waitv` 返回 EINVAL（多等待接口缺失；KERNEL_BUG） |
| m18-linux-018 | 2–3 h | 套件环境补齐（TMPFS/MEMFD、非 root uid、`/proc/iomem`；SUITE_ENV） |

> **已作废（2026-11-23，ADR-0060）**：`m18-qemu-002`（monitor-first QEMU）reviewer Accepted 但**不合入 master**，分支留参考；`m18-qemu-003`（旧探针迁 monitor-first）未开工、被 hart-first 取代。

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m18-qemu-008 | 2026-11-26 06:33 | 3–5 h | QEMU 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局、`escape cfxHA`；进入自动填、rc11 整字恢复掩码） |
| m18-infra-004 | 2026-11-25 09:05 | 2–3 h | `issues.yaml` 按里程碑分册（left + m16…m19）；存量旧号冻结、新增 `ISS-<file>-NNN`；多文件读取器与消费方改造 |
| m18-linux-006 | 2026-11-23 02:40 | 3–5 h | LTP 子集接入（源 tag `20260930`，commit `2279d708…`；组件锁 + 静态构建 + 分诊）；复用 005 骨架 |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m18-spec-007 | 2026-11-26 01:09 | 异步 escape 规范（cg5 rc8–rc11 出口、cg9 新布局、`escape cfxHA`；DADAO 0.8.0 定版、SimRISC 0.5.8-rc、ADR-0061 R3） |
| m18-linux-017 | 2026-11-25 18:12 | **作废**（已不复现）：5/5 PASS、契约 10/10、024 后 27 次 PASS；归因待定 |
| m18-linux-015 | 2026-11-25 16:53 | `mlock2`/`MLOCK_ONFAULT` 复核：无内核缺陷；5/5 绿（15/15）、`timers-nanosleep` 亦转 PASS；基线 SIGNAL→PASS；hole⇒ENOMEM 实测 3/3 |
| m18-linux-024 | 2026-11-25 15:18 | 异步返程改 `cfx_jmon` 帧（窗口 0/4800、K2 170/K5 285/K6 82；3 例非窗口红登记 `ISS-m18-001`） |
| m18-chipyard-001 | 2026-11-25 12:29 | **作废**（ADR-0061 R2 取代）：`imms18[1]=1` ⇒ 当前 cfx `CFXESC`；RTL 语义由 `m16-chipyard-021/024/026` 交付，rc6 残余另立 `m16-chipyard-028` |
| m18-spec-006 | 2026-11-25 12:02 | `cg9 rc6` 口径统一（复位 2、进入取 rc6；用户裁定①）+ `check_cfx15` 兼容新旧措辞；27/27、注入 49/49 |
| m18-idl-002 | 2026-11-25 09:06 | IDL 执行器 cg9 新模型（七槽/源位 cfxha/monitor mask/整体覆盖/escape cg9 ⇒ CFXESC）；`check-idl` 274/274、self-test 68/68 |
| m18-linux-023 | 2026-11-25 07:05 | Linux 侧异常解码适配扁平位图（K1 113/113、K2 170/170、K5 5/5；删 NCFXPERM/NONPTW；K6 残余红归 024/ISS-539） |
| m18-linux-022 | 2026-11-25 03:40 | 内核异步新模型 R2（mask 归 monitor、src 位 cfxha、一帧多源；m45 静默死循环根因修复）；K2 170/170、K5 282/282、K6 71/71 |
| m18-gem5-003 | 2026-11-25 02:52 | `check_tiny_hmon` 的 `CFXESC` oracle 改「当前 cfx（cfx63）」+ monitor 无写入反向断言；29 FAIL→0（213 checks） |
| m18-linux-012 | 2026-11-25 02:16 | ISS-503 K6 门控五条 finding（C 组 11 条恒真断言上移为真判据；`check-linux-k6` 82/82） |
| m18-gem5-002 | 2026-11-25 01:12 | gem5 `CFXESC` 投当前 cfx（cg9/无帧路径；`currentCfx()`+`machineFaultToCfx`）；Tiny/Vast 探针与 QEMU 64 B 见证一致 |
| m18-qemu-001 | 2026-11-25 00:40 | ISS-501 复核（不复现，`gen_sc`/`lrsc_memop` 未改、180 矩阵 0 bad）+ 同址窄 CAS 回归向量（`atomic_rmw` 点14/15）；QEMU 补丁零改动 |
| m18-linux-008 | 2026-11-25 00:28 | K1–K4 门控断言补强（ISS-487 调用形态/白名单锚源码；ISS-457 绝对锚点补 0==0 漏洞；ISS-488 现场派生） |
| m18-gem5-001 | 2026-11-25 00:02 | gem5 `escape` frame selector（R2：cg9 捕获缓冲 ⇒ 合法编码恒 `CFXESC`；`[17:2]`/`=3`/reserved 先判 ILLI）；263/263+391/391 |
| m18-linux-011 | 2026-11-24 23:55 | applet 期望数改为 `config.min` 白名单 ∩ `applets.h` 现场派生（去 `enabled - infra` 抵消；items 57→59） |
| m18-linux-010 | 2026-11-24 23:42 | ISS-486 措辞订正为 libc 侧口径（musl sigaltstack 先拦）；判据订正为 crt1.o 不变 + 成员级除 version.o 外相同 |
| m18-testcases-003 | 2026-11-24 11:49 | 异步探针迁 R2（每次覆盖/monitor mask/一次捕获）+ escape cg9 ⇒ CFXESC 向量（43/44 + 7 注入） |
| m18-infra-003 | 2026-11-24 11:18 | musl 源树重放（26 patches、musl 0 problem）+ 信号帧复核（sigaction01/open01 PASS；旧 QEMU 配对） |
| m18-qemu-006 | 2026-11-24 00:31 | QEMU 捕获缓冲修订（去 gating、每次覆盖、escape cg9 ⇒ CFXESC；13+33 证据） |
| m18-linux-019 | 2026-11-23 22:41 | `k5_syscall_selftest` 锁内 `find_vma`（K5 282/282、S 组 rwsem 0；源码锁断言+注入） |
| m18-spec-005 | 2026-11-23 22:36 | ADR-0061 R2 规格/活文档（cg9 捕获缓冲、smon handoff、escape 不异步返回；14 文件；63+20 证据） |
| m18-qemu-005 | 2026-11-23 20:12 | QEMU 异步模型修订（ADR-0061：mask 归 monitor、src 位 cfxha、cg9 七槽、一帧多源；13+33 证据） |
| m18-spec-004 | 2026-11-23 18:33 | 异步模型修订（掩码归 monitor、源索引 cfxha、`cg9` 七槽只读、§5.4 专节；ADR-0061；版本仍 0.8.0-rc） |
| m18-linux-021 | 2026-11-23 17:57 | **作废**（ADR-0061）：内核 hart-first 掩码/cause 口径，未完工；替代 `m18-linux-022` |
| m18-testcases-001 | 2026-11-23 17:57 | **作废**（ADR-0061）：旧异步探针迁 hart-first 口径，未完工；替代 `m18-testcases-003` |
| m18-testcases-002 | 2026-11-23 17:57 | **作废**（ADR-0061）：`escape` cg9 向量，口径并入 `m18-testcases-003` |
| m18-qemu-004 | 2026-11-23 17:26 | QEMU hart-first 异步仲裁（`cfx_hart cg9`、mask 15/32、pending 17/18、escape bit1；16+12 证据） |
| m18-llvm-001 | 2026-11-23 16:05 | `escape` 汇编/反汇编支持 0/4/8（imms18 bit1；lit 182/182；`case-ledger` 生成物） |
| m18-idl-001 | 2026-11-23 15:53 | `escape` 帧选择位 IDL/语义库/向量（cg9 自检 14 条；11-cfx case13/14/19/20；cg9 向量延至 testcases-002） |
| m18-spec-003 | 2026-11-23 15:01 | `escape` frame selector 编码真源（SimRISC-11/IDL/Toolchain-01/contract-asm/Kaiwu/opcodes/legality；19 路径） |
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
