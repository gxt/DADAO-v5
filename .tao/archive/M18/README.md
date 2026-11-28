# M18 归档（Archive）

> **归档日期**：2026-11-28 ｜ **范围**：M18 里程碑（**2026-11-28 达成**）的全部任务书与相关记录 —— **Linux 测试集（选择与修复）+ K6**
> **归档判据**：任务书字段 `**项目里程碑**：M18` 且状态 ∈ {`已验证`,`里程碑`}（**73** 册 = linux 30 / qemu 10 / spec 8 / gem5 5 / testcases 5 / idl 4 / infra 4 / chipyard 3 / llvm 2 / integ 2；72 册 `已验证` + 本归档册 `里程碑`）；任务流水冻结 **73** 条；`issues-*.yaml` 中 `closed_in: M18` 关闭项 **21** 条（`issues-m18.yaml` 20 + `issues-left.yaml` 的 `ISS-left-013`，见 `issues-closed.md`，`tools/infra/archive_issues.py --verify` 可复核）；`MEMORY.md` 纯 M18 行移除、摘要见 §4。
> **自归档说明**：`m18-integ-002`（本归档任务自身）按 `docs/Process-04 §4.1` 迁入 `integ/`；§1 `integ` 计数（2）与 §2 流水（73 行）均已含它。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m18-retrospective.md`，后续路线见 `.tao/knowledge/milestones-m19.md`–`milestones-m20.md`。

## 1 任务清单（73 个，按模块）

| 模块 | 数量 |
|---|---|
| linux | 30 |
| qemu | 10 |
| spec | 8 |
| gem5 | 5 |
| testcases | 5 |
| idl | 4 |
| infra | 4 |
| chipyard | 3 |
| llvm | 2 |
| integ | 2 |

> 任务书位于同目录下模块子目录（`git mv` 保留 `R` rename 历史，逐册 md5 搬前/搬后相等）。模块目录按 M18 实际出现者建。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-28。72 条「已验证」行按活台账 `.tao/knowledge/milestones-m18.md`「已验证」表**原值**搬入（状态按任务书规范化 `已验证`；次序 = 完成时间倒序，与台账一致），另加本归档任务（`里程碑`）一行；台账文件随本归档删除。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| m18-integ-002 | 里程碑 | 2026-11-28 17:33 | M18 归档（73 册迁 `.tao/archive/M18/`；台账/MEMORY/README/issue 快照收口） |
| m18-integ-001 | 已验证 | 2026-11-28 16:35 | M18 收口：K6 82/82 + kselftest 两轮一致 + LTP 两轮 14/14 + 分诊闭环；`issues-m18` open=0、18 条迁 `issues-left` |
| m18-linux-031 | 已验证 | 2026-11-28 14:10 | supv 返回四字出口意图（`ISS-m18-014` 闭合）；五路注入唯一签名、K2 170/K5 285/K6 82/LTP 两轮一致 |
| m18-linux-029 | 已验证 | 2026-11-28 13:40 | umon 返回四字出口意图（`ISS-m18-011` 闭合，判定=内核假设错）；修前 7–13/20 → 修后 0/20；+ 注释订正重导 |
| m18-linux-030 | 已验证 | 2026-11-28 11:05 | `trap_busy` 改任务级 + supv 帧落任务栈（`ISS-m18-012` 闭合）；修前 2/124 → 修后 140 启 0；真递归仍 `code=0xe` |
| m18-linux-016 | 已验证 | 2026-11-28 04:30 | `futex_waitv` 参数路由：四载体 `argmask` 449=0x09；`--only futex-wait-timeout` 5/5、LTP 两轮 PASS=14、`check-syscall-abi` 86/86 |
| m18-linux-009 | 已验证 | 2026-11-28 04:10 | K4 探针稳定性（`ISS-493` F5 入口帧/停靠帧/代码页、`ISS-494` 事件+有界等待）；两探针各 20/20 |
| m18-linux-028 | 已验证 | 2026-11-27 21:40 | 异步返回主因修（user 异步交接 smon 后不 escape ⇒ `CFXESC`）；`CFXESC` 0/100、LTP 3 clean、soak 0/1000；残余 `ISS-m18-011`、`ISS-m18-012` |
| m18-linux-007 | 已验证 | 2026-11-27 19:52 | pthread create/join 闭环（`create×4`/join 双路径/TLS/detach/负向 `EAGAIN`）；5/5 连过、`run.sh` 40/0；忙等复现器 8/8 归 `ISS-m18-009` |
| m18-linux-018 | 已验证 | 2026-11-27 18:05 | 套件环境补齐（TMPFS/MEMFD、iomem、非 root、`PATH`/`passwd`）；LTP 14/14 |
| m18-linux-006 | 已验证 | 2026-11-27 15:48 | LTP 子集接入 + 两轮逐例一致（`PASS=12/TBROK=2`，flake 8/13 归 `ISS-m18-005`）；`run.sh` 47/47；新增 `ISS-m18-007` |
| m18-linux-025 | 已验证 | 2026-11-27 12:58 | umon 返回路径 restore 用户 SP 前关 supv 异步门（`ISS-m18-001` 闭合）；修前 30/200 → 修后 0/1000、0/2000 窗口、6600 启绿；K2 170/K5 285/K6 82 |
| m18-linux-026 | 已验证 | 2026-11-27 10:05 | 内核迁 0.8.1-rc（cg15/cg16 + ack + 模式上限 + 出口帧；027 并入；jmon 清理）；run.sh 26/26、K2 170/K5 285/K6 82、soak 0/2000、kselftest 两轮一致 |
| m18-linux-027 | 已验证 | 2026-11-27 10:05 | **作废（并入 026）**：出口帧与源接口一起在重启的 026 内完成，不再单独派 |
| m18-qemu-007 | 已验证 | 2026-11-27 10:05 | 移除 QEMU system `cfx_jmon`（`NUM_CFX` 9、map 去 1；trap/访问 ⇒ `CFXREG`）；探针 20/164、证据 26/26 |
| m18-chipyard-002 | 已验证 | 2026-11-27 04:44 | RTL R3 出口帧 + 模式上限（cg5 rc8–rc11、cg9、escape cfxHA）；32/32 + 向量 |
| m18-chipyard-003 | 已验证 | 2026-11-27 04:44 | RTL 源接口 cg15/cg16 + asyncKick；38/38、14/14、hart 124/38×2、pmem 48/10×2 |
| m18-idl-004 | 已验证 | 2026-11-26 22:06 | IDL 源接口 cg15/cg16 + 模式上限；self-test 190/190、check-idl 274/274；证据 27/27 |
| m18-gem5-005 | 已验证 | 2026-11-26 20:31 | gem5 源接口 cg15/cg16 + 模式上限；QEMU 同 ELF 六例签名一致；42/42；DIV-16 关闭 |
| m18-qemu-010 | 已验证 | 2026-11-26 18:44 | QEMU 异步进入模式上限（`当前模式 ≤ cg15 rc14`）；探针 19/157、证据 20/20 |
| m18-spec-009 | 已验证 | 2026-11-26 18:16 | 异步进入模式上限（`当前模式 ≤ cg15 rc14`；默认 supv 不打断 hypv）；ADR-0064 D9；49/49 |
| m18-testcases-005 | 已验证 | 2026-11-26 17:55 | 源接口向量与载体迁移（cg15/cg16；m18qemu009 17/134、m18qemu008 21/150、inst 274/274；async 旧探针 KNOWN-RED） |
| m18-gem5-004 | 已验证 | 2026-11-26 17:12 | gem5 R3 出口帧（cg5 rc8–rc11、cg9、escape cfxHA；hart 124/38、pmem 48/10；DIV-16 留给 005） |
| m18-qemu-009 | 已验证 | 2026-11-26 14:31 | QEMU 源接口（cg15 捕获、cg15 rc3 mask、cg16 mask/pending/ack、IRQ_EN 删除、ack 才清）；探针 10/91、证据 20/20 |
| m18-spec-008 | 已验证 | 2026-11-26 13:44 | 每源 pending/mask/ack（cg15 捕获、cg15 rc3 mask、cg16 源接口、ack 才清、ADR-0064、0.8.1-rc）；22/22、38 文件/132 断言 |
| m18-idl-003 | 已验证 | 2026-11-26 10:47 | IDL 迁 R3（cg5/cg9 新布局、`escape cfxHA`、`rc11` 整字）；`check-idl` 274/274、self-test 119/119；补 spec-007 F3 |
| m18-testcases-004 | 已验证 | 2026-11-26 10:04 | 异步 escape 出口向量 + R3 载体迁移（inst 274/274、smoke 10/10、证据 38/38；`pmem` 48 槽、进入自证） |
| m18-qemu-008 | 已验证 | 2026-11-26 07:38 | 异步 escape 出口（cg5 rc8–rc11、cg9 rc14/rc15、`escape cfxHA`、rc11 整字恢复；探针 21/150、证据 29/29） |
| m18-infra-004 | 已验证 | 2026-11-26 07:28 | `issues` 按里程碑分册（left+m16…m19，多重集相等）+ 收尾清理 55 条 closed（missing=0）；船后补验 Accepted |
| m18-llvm-002 | 已验证 | 2026-11-26 07:27 | LLVM/opcodes `escape cfxHA`（imms18 SBZ、反汇编、legality；lit 186/186、`check-cfx-vectors` 回绿） |
| m18-spec-007 | 已验证 | 2026-11-26 01:09 | 异步 escape 规范（cg5 rc8–rc11 出口、cg9 新布局、`escape cfxHA`；DADAO 0.8.0 定版、SimRISC 0.5.8-rc、ADR-0061 R3） |
| m18-linux-017 | 已验证 | 2026-11-25 18:12 | **作废**（已不复现）：5/5 PASS、契约 10/10、024 后 27 次 PASS；归因待定 |
| m18-linux-015 | 已验证 | 2026-11-25 16:53 | `mlock2`/`MLOCK_ONFAULT` 复核：无内核缺陷；5/5 绿（15/15）、`timers-nanosleep` 亦转 PASS；基线 SIGNAL→PASS；hole⇒ENOMEM 实测 3/3 |
| m18-linux-024 | 已验证 | 2026-11-25 15:18 | 异步返程改 `cfx_jmon` 帧（窗口 0/4800、K2 170/K5 285/K6 82；3 例非窗口红登记 `ISS-m18-001`） |
| m18-chipyard-001 | 已验证 | 2026-11-25 12:29 | **作废**（ADR-0061 R2 取代）：`imms18[1]=1` ⇒ 当前 cfx `CFXESC`；RTL 语义由 `m16-chipyard-021/024/026` 交付，rc6 残余另立 `m16-chipyard-028` |
| m18-spec-006 | 已验证 | 2026-11-25 12:02 | `cg9 rc6` 口径统一（复位 2、进入取 rc6；用户裁定①）+ `check_cfx15` 兼容新旧措辞；27/27、注入 49/49 |
| m18-idl-002 | 已验证 | 2026-11-25 09:06 | IDL 执行器 cg9 新模型（七槽/源位 cfxha/monitor mask/整体覆盖/escape cg9 ⇒ CFXESC）；`check-idl` 274/274、self-test 68/68 |
| m18-linux-023 | 已验证 | 2026-11-25 07:05 | Linux 侧异常解码适配扁平位图（K1 113/113、K2 170/170、K5 5/5；删 NCFXPERM/NONPTW；K6 残余红归 024/ISS-539） |
| m18-linux-022 | 已验证 | 2026-11-25 03:40 | 内核异步新模型 R2（mask 归 monitor、src 位 cfxha、一帧多源；m45 静默死循环根因修复）；K2 170/170、K5 282/282、K6 71/71 |
| m18-gem5-003 | 已验证 | 2026-11-25 02:52 | `check_tiny_hmon` 的 `CFXESC` oracle 改「当前 cfx（cfx63）」+ monitor 无写入反向断言；29 FAIL→0（213 checks） |
| m18-linux-012 | 已验证 | 2026-11-25 02:16 | ISS-503 K6 门控五条 finding（C 组 11 条恒真断言上移为真判据；`check-linux-k6` 82/82） |
| m18-gem5-002 | 已验证 | 2026-11-25 01:12 | gem5 `CFXESC` 投当前 cfx（cg9/无帧路径；`currentCfx()`+`machineFaultToCfx`）；Tiny/Vast 探针与 QEMU 64 B 见证一致 |
| m18-qemu-001 | 已验证 | 2026-11-25 00:40 | ISS-501 复核（不复现，`gen_sc`/`lrsc_memop` 未改、180 矩阵 0 bad）+ 同址窄 CAS 回归向量（`atomic_rmw` 点14/15）；QEMU 补丁零改动 |
| m18-linux-008 | 已验证 | 2026-11-25 00:28 | K1–K4 门控断言补强（ISS-487 调用形态/白名单锚源码；ISS-457 绝对锚点补 0==0 漏洞；ISS-488 现场派生） |
| m18-gem5-001 | 已验证 | 2026-11-25 00:02 | gem5 `escape` frame selector（R2：cg9 捕获缓冲 ⇒ 合法编码恒 `CFXESC`；`[17:2]`/`=3`/reserved 先判 ILLI）；263/263+391/391 |
| m18-linux-011 | 已验证 | 2026-11-24 23:55 | applet 期望数改为 `config.min` 白名单 ∩ `applets.h` 现场派生（去 `enabled - infra` 抵消；items 57→59） |
| m18-linux-010 | 已验证 | 2026-11-24 23:42 | ISS-486 措辞订正为 libc 侧口径（musl sigaltstack 先拦）；判据订正为 crt1.o 不变 + 成员级除 version.o 外相同 |
| m18-testcases-003 | 已验证 | 2026-11-24 11:49 | 异步探针迁 R2（每次覆盖/monitor mask/一次捕获）+ escape cg9 ⇒ CFXESC 向量（43/44 + 7 注入） |
| m18-infra-003 | 已验证 | 2026-11-24 11:18 | musl 源树重放（26 patches、musl 0 problem）+ 信号帧复核（sigaction01/open01 PASS；旧 QEMU 配对） |
| m18-qemu-006 | 已验证 | 2026-11-24 00:31 | QEMU 捕获缓冲修订（去 gating、每次覆盖、escape cg9 ⇒ CFXESC；13+33 证据） |
| m18-linux-019 | 已验证 | 2026-11-23 22:41 | `k5_syscall_selftest` 锁内 `find_vma`（K5 282/282、S 组 rwsem 0；源码锁断言+注入） |
| m18-spec-005 | 已验证 | 2026-11-23 22:36 | ADR-0061 R2 规格/活文档（cg9 捕获缓冲、smon handoff、escape 不异步返回；14 文件；63+20 证据） |
| m18-qemu-005 | 已验证 | 2026-11-23 20:12 | QEMU 异步模型修订（ADR-0061：mask 归 monitor、src 位 cfxha、cg9 七槽、一帧多源；13+33 证据） |
| m18-spec-004 | 已验证 | 2026-11-23 18:33 | 异步模型修订（掩码归 monitor、源索引 cfxha、`cg9` 七槽只读、§5.4 专节；ADR-0061；版本仍 0.8.0-rc） |
| m18-linux-021 | 已验证 | 2026-11-23 17:57 | **作废**（ADR-0061）：内核 hart-first 掩码/cause 口径，未完工；替代 `m18-linux-022` |
| m18-testcases-001 | 已验证 | 2026-11-23 17:57 | **作废**（ADR-0061）：旧异步探针迁 hart-first 口径，未完工；替代 `m18-testcases-003` |
| m18-testcases-002 | 已验证 | 2026-11-23 17:57 | **作废**（ADR-0061）：`escape` cg9 向量，口径并入 `m18-testcases-003` |
| m18-qemu-004 | 已验证 | 2026-11-23 17:26 | QEMU hart-first 异步仲裁（`cfx_hart cg9`、mask 15/32、pending 17/18、escape bit1；16+12 证据） |
| m18-llvm-001 | 已验证 | 2026-11-23 16:05 | `escape` 汇编/反汇编支持 0/4/8（imms18 bit1；lit 182/182；`case-ledger` 生成物） |
| m18-idl-001 | 已验证 | 2026-11-23 15:53 | `escape` 帧选择位 IDL/语义库/向量（cg9 自检 14 条；11-cfx case13/14/19/20；cg9 向量延至 testcases-002） |
| m18-spec-003 | 已验证 | 2026-11-23 15:01 | `escape` frame selector 编码真源（SimRISC-11/IDL/Toolchain-01/contract-asm/Kaiwu/opcodes/legality；19 路径） |
| m18-linux-013 | 已验证 | 2026-11-23 13:45 | **作废**（ADR-0060）：monitor-first 内核异步方案，未开工 |
| m18-qemu-002 | 已验证 | 2026-11-23 13:45 | **作废**（ADR-0060）：monitor-first QEMU，reviewer Accepted 但未合入，分支留参考 |
| m18-qemu-003 | 已验证 | 2026-11-23 13:45 | **作废**（ADR-0060）：旧探针迁 monitor-first，未开工 |
| m18-spec-002 | 已验证 | 2026-11-23 13:45 | hart-first/cg9 规格与契约同步（`§5.2`/cg9/`§4.7`/`§4.9`/`escape` frame selector；DADAO-23 同步；版本仍 0.8.0-rc） |
| m18-infra-002 | 已验证 | 2026-11-23 02:40 | musl ldso 动态链接运行闭环（P3；system/qemu-user rc=42、pthread/dlopen/TLS/errno 实测；libc.a 不变；零内核/musl 补丁） |
| m18-linux-014 | 已验证 | 2026-11-23 01:23 | COW 共享文件页 `VM_FAULT_COMPLETED` 双重解锁修复（`fault.c`；5/5 PASS，无 rwsem 警告/停摆；53+14/15 证据项） |
| m18-linux-005 | 已验证 | 2026-11-22 19:37 | 测试集运行骨架 + kselftest 试点（8 例：PASS1/FAIL2/SKIP2/SIGNAL1/TIMEOUT2；套件校验 23/23；补丁 manifest 双向+逐补丁增量校验） |
| m18-linux-003 | 已验证 | 2026-11-22 10:34 | K6 收口门控 `check-linux-k6`（71/71；§4a.3 退役审计；L2） |
| m18-infra-001 | 已验证 | 2026-11-22 09:32 | musl mallocng 根因修复（`a_cas` 改 8 字节字 CAS；ISS-497/499 关闭；K6 长脚本单次跑通） |
| m18-linux-004 | 已验证 | 2026-11-22 08:33 | K6 用户入口异步投递修复（ISS-498）+ 控制台行缓冲；200/200 启动、长脚本 27 条 |
| m18-linux-002 | 已验证 | 2026-11-22 05:31 | K6 基础命令回归（sh 内 5 条 + mkdir/ls/rm 组合；50/50；长脚本崩溃登记 ISS-497） |
| m18-linux-001 | 已验证 | 2026-11-22 04:32 | K6 shell 启动（busybox sh + semihosting 控制台 + 前台执行，无作业控制；28/28） |

## 3 终局证据

| 套件 | 结果 |
| --- | --- |
| `check-linux-k6`（busybox/K6） | **82/82 rc=0**（`m18-integ-001` 收口，2026-11-28） |
| kselftest | **两轮逐例一致**（7 PASS + `mm-pfnmap` SKIP=SUITE_ENV）；`check_suite` 24/24 |
| LTP 子集 | **两轮 14/14**（`check_suite` 20/20） |
| `check-syscall-abi` | **86/86**（`m18-linux-016`） |
| `check-patch-tree` | **12 patch set / 464 patches、0 problem、无 skipped**（linux/musl/busybox 私有树 + 其余共享只读；`m18-integ-001`） |
| 收尾门控（本任务现跑） | `make check-archive` **rc=0**（M18 册 73 / 流水 73）；`check_issues` **rc=0**（68 open / 17 closed / 85 entries / 3 ledgers）；`check-knowledge-refs` **rc=0**（0 具体 `.work/**`、0 悬空）；`check-milestones-fresh` **rc=0**（活册只剩 M19/M20）；`check-tasks` **rc=0** |
| 基线红（非 M18 面，归档不修） | L1 `check-patch-tree` **52 problem**（linux 51/musl 1，`ISS-left-004`）；L3 `unit:full`/`tset:m6` 的 `stack-protector*.ll` 未归类（`ISS-left-005`）；`check-index-blobs` **rc=2**（4 条 chipyard 补丁 index 不符，`ISS-left-026`，m19 面）；`check-manifests-guard` 已 rc=0（M16 遗留登记随归档清理） |

## 4 MEMORY 摘录（M18 时期）

| 项目 | 状态 |
|---|---|
| 定位 | M18 = **Linux 测试集（选择与修复）+ K6**（K6 从 M14 移入作入口批次）；运行环境 QEMU system `kaiwu-vast` |
| 测试集口径 | 两套件都跑（`kselftest` 先、`LTP` 子集后，共用运行骨架）；分诊四分类 `KERNEL_BUG`/`TEST_ADAPT`/`UNSUPPORTED`/`SUITE_ENV`；每条非 PASS 在库记录、禁静默跳过 |
| 交付 | busybox/K6 **82/82**；kselftest 两轮逐例一致；LTP 两轮 **14/14**；`check-syscall-abi` 86/86；musl `mallocng` 根因（`a_cas` 8 字节字 CAS）+ `ldso` 动态链接闭环 |
| 关键修复链 | `025` 自旋 → `028` `CFXESC` 主因 → `029` 精确点 → `030` `trap_busy` → `031` smon 对称（异步出口意图四字重写） |
| 关键裁定 | 异步模型 ADR-0061 R2/R3（mask 归 monitor、源索引 `cfxha`、cg9 七槽、一帧多源）；`cg9 rc6` 迁 `cg15 rc14`（ADR-0064 D5/D9） |
| 基线红 | L1 `check-patch-tree` 52 problem（`ISS-left-004`）；L3 `stack-protector*.ll` 未归类（`ISS-left-005`）；`check-index-blobs` 4 条 chipyard 补丁（`ISS-left-026`） |
| 归档 | `.tao/archive/M18/`（2026-11-28，`m18-integ-002`） |

## 5 指针

- 里程碑定义/达成：`.tao/knowledge/milestones-m19.md`–`milestones-m20.md`（活台账；M18 台账已随本归档删除）
- 里程碑回顾：本目录 `m18-retrospective.md`
- 关闭 issue 快照：本目录 `issues-closed.md`（21 条；`tools/infra/archive_issues.py --verify` 可复核）
- 遗留台账：`.tao/knowledge/issues-left.yaml`（含 `ISS-left-004/005/007/009/016/020–028`）、`discussing.md`
- 归档规范：`docs/Process-04-里程碑归档规范.md`；门控：`tools/infra/check_archive.py`
