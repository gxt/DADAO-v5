# m14-spec-002: 内核侧 syscall / errno / TLS / 原子性契约（扩 `contract-syscall`）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-spec-001`（**串行**：同改 `.tao/contracts/README.md` 版本表；`m14-spec-001` 另改 spec 版本锁，两者不得并行）
**可并行分片**：否（单册单写者）
**预估**：3–4 h
**状态**：待开始

## 背景

`.tao/contracts/contract-syscall.md`（0.9.2）是 M8「无内核」时代的用户态映射合约：号表（`rd15` + 内核 `7.2.10` 锁定来源）、入口（`umon`/`jmon`）、传参/返回（`rd8`）、errno 载体（`rd8` 负值）都已冻结。M14 引入内核后，同一套用户态 ABI 还需要**内核侧**的接口定义，否则 `arch/dadao` 与内核实现会各自猜：

- 内核在哪个 cfx/向量接收用户 syscall、进入什么运行模式、硬件保存了什么、如何返回；
- `rd8` 的 errno 编码边界与内核内部重启码的处理；
- `rb3 = rbtp` 在 `clone`/`execve`/syscall 路径上的保存与设置责任；`initial-exec` / `local-exec` 的分工；
- `clone` / `futex` / 用户 `lr`+`sc` 依赖的原子性前提（`sc` 偶发失败、异常清保留标记）。

**号表本身不改**：`rd15` + `7.2.10` pin（`contract-syscall §1.2`）一字不动。

## 目标

在 `contract-syscall.md` 新增 §8–§11，并把 §6「无内核目标」改为历史范围注记（保留原文、加 M14 指针），版本 `0.9.2` → **`0.10.0`**。

### §8 内核侧入口（umon / smon / hmon 的分工）

- **用户 syscall**：用户态 `trap cfx_umon, 0` ⇒ `immu18 = 0`（`SBI_UMON_SYSCALL`）；入口配置取 **user 模式**寄存器 `cfx_umon_user_switch_run_mode`（默认 `2 = supv`）与 `cfx_umon_user_excp_vector`（**内核提供**）⇒ 内核向量运行在 `supv`；返回 = `escape cfx_umon, [excp_cause_ip, 4]`（落回 `trap` 下一条）。`jmon` 同构（受限上下文，`immu18` 独立编号）。
- **返回路径的掩码**：`escape cfx_umon` 由内核（`supv`）执行，受 `cfx_umon_supv_*`（源 cfx = 当前 monitor `smon`）约束；内核须配置允许，否则按 `CFXPERM`/`CFXESC` 失败。user→umon 的进入路径则受 `cfx_umon_user_cfxtrap` 约束。
- **硬件现场只有 cg5 的异常现场字段**（`excp_prev_run_mode` / `excp_cause_id` / `excp_cause_ip` / `excp_cause_info` 等，`DADAO-12 §3.6`）：**不保存通用寄存器**。内核向量必须在使用任何寄存器前自行保存，返回前恢复；不得把 cg5 当 `pt_regs`。
- **入口可见状态**：`rd15` = nr、参数按 §3（`rd16–rd31`/`rb16–rb31`/`rf16–rf31`）、`excp_cause_ip` = `trap` 指令地址、`excp_cause_id` = `CFXTRAP`（`1<<0`）、`excp_cause_info & 0x3FFFF` = `immu18`；返回时写 `rd8` 再 `escape +4`。
- **smon（supv 异常）**：内核运行期同步异常（页表/对齐/非法指令/cfx 权限等）进 `cfx_smon_supv_excp_vector`（**内核提供**）；内核按 `excp_cause_id`/`excp_cause_info` 分派；PTW 的异常归因（未映射/权限）沿用 `DADAO-12 §2.2.6` 与 `Machine-v5 §1.2`，本合约不重定义。
- **hmon / HBI**：内核→hypv 的服务调用走 `trap cfx_hmon, immu18`，返回 `escape cfx_hmon, …`；**函数号与语义不在此重抄**，指针到 `spec/DADAO-23`（HBI）。hmon 为固件，不是内核的一部分。
- **掩码配置责任**：内核启动时配置 `cfx_umon_user_cfxtrap`（user→umon 进入）与 `cfx_umon_supv_*`/`cfx_smon_supv_*`（supv 返回/异常）使上述路径可用（位定义见 `DADAO-12 §3` / `DADAO-13 §1`）；不得靠 hmon 的默认值长期放行宽于需要的来源。
- **嵌套**：不同 cfx 的 cg5 相互独立（A→B 无需保存）；同 cfx 递归（如 `umon` 内再进 `umon`）前必须把 cg5 保存到 `cg6` 暂存、退出恢复（`DADAO-22 §1`）。

### §9 errno 表示（扩 §4，不改变已裁定 A 口径）

- `rd8` 为 **64 位有符号**；成功 = `>= 0`；错误 = `-errno`，取值范围 **`[-4095, -1]`**；`-4096` 及以下不是 errno（与 musl `__syscall_ret` 判据一致，musl **零改**）。
- 内核内部返回值（如 `ERESTARTSYS`/`ERESTARTNOINTR` 等重启码）**不得**直接暴露给用户；内核必须在返回用户态前转成 `-errno` 或重新执行。
- 不支持的系统调用返回 **`-ENOSYS`**；参数错误返回对应 `-EINVAL` 等；不得用 `rd1`/`rderrno` 承载 syscall 错误（§4 已裁定）。
- 用户态看到的返回寄存器只有 `rd8`；指针返回值仍按 `rb8` 的既有 ABI 规则（`DADAO-21 §返回值`），但 syscall 的标量结果不放 `rb8`。

### §10 TLS（`rb3 = rbtp`）

- **事实**：`rb3` = `rbtp`（thread pointer），`DADAO-21 §寄存器规范 §RB寄存器`、`contract-abi §1`；v5 编译器保留不分配（`contract-abi §4.5`）。
- **syscall 路径**：`rbtp` 属被调用者保存/保留寄存器 ⇒ 内核入口保存、返回恢复；**不得**用 `rb3` 传参或作临时寄存器。
- **`clone`（含 `CLONE_SETTLS`）**：子线程的 `rbtp` = `tls` 参数；父线程不变；子线程从 syscall 返回处以 `rd8 = 0` 开始（双返回语义），寄存器现场 = 父现场副本（除返回寄存器与架构约定的差异）。
- **`execve`**：新映像的 `rbtp` 清 `0`；由 libc 在进入 `main` 前自行初始化（musl `__init_tls`/`__set_thread_area` 路径），内核不代设 TCB 布局。
- **initial-exec / local-exec**：两者都是**用户态链接/TLS 模型**，内核只保证「`rbtp` 的保存/恢复 + `clone`/`execve` 的设置语义」；TP 的方向（`TLS_ABOVE_TP` 等）与偏置（`TP_OFFSET`/`DTP_OFFSET`）**不在本合约决定**，归 musl arch 宏（指针到 `contract-dynlink §2.4/§7`，2026-10-14 裁定 8），不得在此写死数值。
- **单线程静态 init**：允许只用 `initial-exec`；内核仍须正确初始化/清零 `rbtp`，不得因「单线程」跳过保存。

### §11 原子性（`clone` / `futex` / `lr`+`sc`）

- **基线语义**：`lr`/`sc` 的保留标记、成功/失败、宽度、对齐、清标记条件**一律**按 `SimRISC-12 §1`（不重抄）；`sc` 可能**偶发失败**，软件必须在循环中重试；异常或中断进入会清除保留标记 ⇒ **`lr`…`sc` 不能跨任何 syscall/异常**。
- **用户原子操作**：Linux `atomic_*` / `cmpxchg` 由 `lr`/`sc` 循环实现（可按宽度选 `.b/.w/.t/.o`）；`sc` 的 acquire/release 变体（`.an/.ar/.nr`）用于 `smp_mb`/`smp_rmb` 等；单核 K0 下仍不得把「单核」当作免内存序假设，生成的序须与多核一致。
- **`futex`**：`FUTEX_WAIT` 的「检查用户字 → 睡眠」必须是原子的：内核在持锁下用 `lr` 语义复核用户字（或等价的单核原子读）后再入队；`FUTEX_WAKE` 不得丢唤醒；`futex` 不改变用户 `lr/sc` 的语义。
- **`clone`**：线程创建对用户可见的状态切换必须原子（子线程现场 = 父现场副本，`rd8 = 0`）；子线程的 `rbtp` 按 §10 设置；不得让子线程看到半初始化的 TCB 指针。
- **不定义**：TLB 填充/失效/ASID（K3）、cache/LLC 一致性、跨 hart 的保留标记仲裁（K0 单核；多核另立契约）。

## 范围（改哪些文件）

- `.tao/contracts/contract-syscall.md`（§6 范围注记、§7 裁定表、新增 §8–§11、版本头、附录 A 来源对照）
- `.tao/contracts/README.md`（`contract-syscall` 版本行 0.9.2 → 0.10.0）
- `tools/linux/check_syscall_contract.py`（新建；含 `--self-test`）
- 本任务书

**不改**：`spec/`（含 `DADAO-21`/`DADAO-22` 上游册，一字不动）、号表正文、`contracts/` 下的 `*.yaml`、`manifests/`。

## 验收标准

1. 版本 `0.10.0`；新增 §8–§11 内容覆盖上文四组要点，每条规范句带来源标注（`[DADAO-21 §4]`/`[DADAO-22 §1/§2]`/`[DADAO-12 §3.6]`/`[DADAO-23 §3]`/`[SimRISC-12 §1]`/`[contract-dynlink §2.4]`/`[用户裁定 2026-11-13]`；无上游依据的冻结项标 `[spec-decision]` 并列入 §7）。
2. **号表零改动**：§1 全文与派单基线 commit 的版本**逐字一致**（`git show <派单基线>:<path>` 比对；基线钉常量，**不得取 `HEAD`**）；`rd15` / `7.2.10` pin / 号段边界不变；`scripts/syscall.tbl` 未改。
3. §6「无内核目标」保留原文并加「M14 起内核侧入口见 §8」注记，**不得**删历史或改写 M8 结论；§4 的 A 口径（`rd8` 负值）不变。§8 的 cg0/cg2 分工写清：进入用 `cfx_umon_user_switch_run_mode`/`cfx_umon_user_excp_vector`，返回/异常用 `cfx_umon_supv_*`/`cfx_smon_supv_*`，不得混用同名 `_supv_` 当作 user 入口。
4. errno：正文含 `[-4095,-1]`、内部重启码不得外泄、`-ENOSYS`、不用 `rd1`；与 `contract-syscall §4` 无矛盾。
5. TLS：`rb3` 保存/恢复、`clone` SETTLS、`execve` 清零、initial/local-exec 分工、不写死 TP 方向/偏置（只指针到 `contract-dynlink`）。
6. 原子性：引用 `SimRISC-12 §1` 不重抄；写明 `sc` 偶发失败/异常清标记/不可跨 syscall/`futex` 无丢唤醒/`clone` 原子可见；不定义 TLB/cache。
7. `tools/linux/check_syscall_contract.py` rc=0，断言至少覆盖：`rb3` 三处（本合约/`contract-abi`/`contract-dynlink`）一致；errno 区间串存在；新增 §8–§11 无「待…定/TODO/TBD」裸词；每条新增规范句有来源标注；§1 与基线逐字一致。`--self-test` 四类注入（改 `rb3`、改 errno 区间、删来源标注、改 §1 号表）各自 FAIL。
8. 门控：`make check-contracts-pending`、`check-syscall-abi`、`check-contracts-dir`、`check-knowledge-refs` rc=0；一键证据脚本含注入→FAIL→`cp`+md5 还原→回绿。
9. 完成区 ≤30 行、无运行期路径。

## 说明

- **授权/依据**：本任务只改 `.tao/contracts/`（不在 `spec-readonly` 锁内），但内容属 M14 K0 契约冻结；派单前提由主会话转达（用户 2026-11-13：K0 需内核侧 syscall/errno/TLS 契约）。**用户原话由主会话落到本任务书「用户依据」段**；子代理不得编造或代填；无原话时相应条款标 `[spec-decision]` 并列入 §7「待裁定」。
- **上游只读册**：`DADAO-21`/`DADAO-22`/`DADAO-23` 只引用 `§`，不改一字；若发现上游语义不足（如 cg5 现场字段不够），**不得自改**，登记「待裁定」返回主会话。
- 与 `contract-dynlink` 的分工：TLS 模型/TP 偏置归 dynlink/musl 宏，本合约只写内核侧责任。
- 与 `m14-spec-001` 的分工：入口**地址/寄存器/内存**归 boot ABI；本任务只写「入口之后的 syscall/异常/TLS/原子性」语义。
- `tools/linux/check_syscall_contract.py` 本任务只作为**验收期一致性检查器**（直接调用，不新增 `make` 目标，避免本批 Makefile 多写者）；是否常驻 L1 由主会话在 K0 收口后决定，登记在完成区。
- 版本头现有一句「本合约暂落 `.tao/knowledge/`」已过期（文件实际在 `.tao/contracts/`）；本任务改版本头时同笔修正该句，**不得**顺带改其它口径。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/依据原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本的对照基线钉**派单前 commit 常量**，不得取 `HEAD`。

## 用户依据

（由主会话在派单前填入用户原话/问答摘要；未填 ⇒ 新增条款标 `[spec-decision]` 并列 §7 待裁定。）

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审（待填）

### 第 1 轮 reviewer 验收（待填）
