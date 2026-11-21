# m14-spec-002: 内核侧 syscall / errno / TLS / 原子性契约（扩 `contract-syscall`）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-spec-001`（**串行**：同改 `.tao/contracts/README.md` 版本表；`m14-spec-001` 另改 spec 版本锁，两者不得并行）
**可并行分片**：否（单册单写者）
**预估**：3–4 h
**状态**：已验证

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
- **smon（supv 异常）**：内核运行期同步异常（页表/对齐/非法指令/cfx 权限等）进 `cfx_smon_supv_excp_vector`（**内核提供**）；内核按 `excp_cause_id`/`excp_cause_info` 分派；PTW 的异常归因（未映射/权限）沿用 `DADAO-12 §2.2.6` 与 `Kaiwu §1.2`，本合约不重定义。
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

（主会话**未在派单前填入原话**；本任务新增条款一律按 `[spec-decision]` 处理并列入 §7 #5–#8，**未编造**用户裁定或原话。）

## 待裁定

1. **固件放行 `supv` 对 `cfx_umon` / `cfx_jmon` 的配置权**：问题 = 内核（`supv`）能否写 `cfx_umon_user_*` / `cfx_umon_supv_*`；事实 = 源位默认屏蔽（`0xFFFF…F7`：smon 位 = 1）且 `hypv_cg_reg_deleg` 另设一道门。选项 = A（hmon HBI 初始化放行 umon/jmon 对 smon 的 `cfxreg`/`cfxtrap` 源位，内核自配置）/ B（hmon 代配入口寄存器，内核只读）。**建议 A**（责任在内核、固件只放行）。**自决临时处置**：合约只写「责任 + 前提」，不假定内核总能自配置。
2. **`excp_cause_info` 与 `immu18` 的关系**：`DADAO-12 §3.6` 只写「指令编码」，本合约据 `SimRISC-00 §3.1` 位段推得 `immu18 = cause_info & 0x3FFFF`。建议上游补一句明文（「`CFXTRAP` 的 `cause_info` = 触发指令编码」）；**自决临时处置** = 按位段推导使用，不改 `spec/`。
3. **`clone` 双返回 / `execve` 清零 `rbtp` 的上游落点**：`DADAO-21 §4` 未规定二者；本合约按 Linux 语义冻结（`[spec-decision]`）。建议在上游 ABI 补一小节，或在 `contract-dynlink`/musl 移植任务中承载；**自决临时处置** = 留本合约 §10。

## 完成区

**测试结果**：`check_syscall_contract.py` rc=0（§8/§9/§10/§11 规范句现场统计 = 11/6/6/5，合计 28）；`--self-test` rc=0（5 类注入各自 FAIL 且失败原因 = 该项断言，还原回绿 5/5）；一键证据脚本 rc=0（**PASS=42 / FAIL=0**，含 3 路真实文件注入；变更集断言改用 `8352b41b..HEAD` ∪ 工作树，`BASE=HEAD` 重放判红）。
**修改文件**：
- `.tao/contracts/contract-syscall.md`（0.9.2→0.10.0；§6 加 M14 注记；§7 补 #5–#8；新增 §8–§11；附录 A 补 §8–§11；版本头「暂落」旧句就地修正）
- `tools/linux/check_syscall_contract.py`（新建；含 `--self-test` 5 类注入）
- 本任务书（状态 / 用户依据 / 待裁定 / 完成区 / 自审）
**验收结果**：
- §1 与派单基线 `174298eb` **逐字节一致**：检查器 `cur_sha == base_sha`（`6eda79ae…`）；证据脚本独立复算 §1 sha 一致（`7b3e0ec3…`）、§1 内 `rd15` 出现 4==4；§4 亦逐字节一致；§6 基线原文缺失行 0。
- 门控 rc=0：`check-contracts-pending` / `check-syscall-abi` / `check-contracts-dir` / `check-knowledge-refs`。
- 范围：`git diff 174298eb..HEAD -- spec/ contracts/ manifests/` 与工作树同名域均为空（号表正文 / `contracts/*.yaml` / `manifests/` 未动）；未进入 linux 组件树（内核 `scripts/syscall.tbl` 未动）；变更集 = `8352b41b..HEAD` ∪ 工作树 = 契约 + 任务书 + 检查器（WIP 提交 `61e41247` 后仍成立）。
**新发现/坑**：
1. `.tao/contracts/README.md` 的 `contract-syscall` 行**没有版本号**（只写一句话）⇒ 任务书「README 版本行 0.9.2→0.10.0」无对应内容，未改（派单提示亦限定只改契约 + 检查器）。建议后续给 README 补版本列或删该项。
2. 版本头「来源」行仍写 `DADAO-22`（0.7.1）、实际册为 `0.7.3-rc`：既有陈旧，按最小修改未动。
3. 上游口径：`cfx_umon_supv_*` 的 smon 源位默认屏蔽，且 `supv` 自配置还受 `*_supv_cfxreg` + `hypv_cg_reg_deleg` 门控 ⇒ 合约只写责任与前提，不写「内核总能自配置」。
4. 检查器自检注入串必须在全文件唯一：`[-4095, -1]` 在 §7/§9 各一处，需带上下文（`取值范围 **…**`）才能唯一命中。
5. **台账现场事实**：本分支基线 `8352b41b` 的 `milestones-m14.md` 仍把本任务列在「待开始」⇒ `check-milestones-fresh --file milestones-m14.md` 报 A1/R1 红；`master` 的 `174298eb` 已移入「进行中」（含派单时间），合并后自愈。另 `m13-testcases-016` 红属他任务。本任务未改台账。
6. **审阅记录也会撞 `.work/**` 门控**：审阅记录里写具体 `.work/**` 路径即被 `check-knowledge-refs` 判红（本次 2 处已改为「运行期证据目录的 `run.sh`」，结论/数字未改）。
**遗留问题**：无（3 项口径问题已入「待裁定」，不阻塞 K0 实现）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 初稿把「`escape cfx_umon` 受 `cfx_umon_supv_*` 源位约束」写成返回路径条件，与 `DADAO-12 §5.3`（`escape` 的 `cfxha` 必须等于当前 cfx，源 = 目标 ⇒ 自身位忽略）冲突 | ✅已修 | §8 改写为「源 = 目标 ⇒ 自身位忽略；被拒只可能是帧/目标错误 ⇒ `CFXESC`」，另立「`supv` 期跨 cfx 转移掩码」与「自配置前提」两条 | 检查器 §8 要点 PASS；`check-contracts-pending` rc=0 |
| `excp_cause_info & 0x3FFFF` 需先证明 `ciii` 立即数占指令位 `[17:0]` | ✅已核并补标注 | 核对 `SimRISC-00 §3.1`（`opc[31:24]` + `ha/hb/hc/hd` ⇒ 立即数 `[17:0]`）；数值不变，补 `[SimRISC-00 §3.1]` | 检查器 `§8 点名 excp_cause_info & 0x3FFFF` PASS |
| `--self-test` errno 注入串 `[-4095, -1]` 命中 2 处（§7 + §9）⇒ 自检报「注入点不唯一」，自检红 | ✅已修 | 注入串改唯一上下文 `取值范围 **\`[-4095, -1]\`**` | `--self-test` rc=0；5/5 注入各自命中预期 FAIL 标签 |
| 证据脚本「改动文件集」期望串未按 `sort` 序（写成 契约/检查器/任务书） | ✅已修 | 期望串改 契约/任务书/检查器（按路径序） | 一键证据 `改动文件集 == 任务书范围` PASS |
| 任务书「范围」第 2 项（README 版本行）在文件中无对应内容 | ⏸延后 | 未改 README（派单限定只改契约 + 检查器；且 README 与 `m14-spec-001` 共享） | 已记「新发现/坑」#1 |
| 检查器把「不定义」类 bullet 也要求来源标注 | ❌不修 | 这是有意的（判据一致、避免以「不定义」逃标注）；§11 该类条已标 `[spec-decision][ADR-0025 D6]` | 检查器 §11 5/5 标注 PASS |
| 新增条款用了 `[外部权威 …]` / `[Kaiwu §1.2]`（不在任务书列举的 6 类） | ❌不修 | 沿用 `contract-dynlink` 既有「外部权威」体例；`Kaiwu` 是 v5 自定 spec 册 | 检查器 `TAG_SOURCES` 覆盖这些前缀；`check-contracts-pending` rc=0 |

判决：无未修 finding ⇒ 状态置 **待验收**。

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（1 项阻断 = 证据脚本提交后 rc=1；其余全部通过）

**重跑记录（本人独立执行，workdir = 任务树）**
- `python3 tools/linux/check_syscall_contract.py` → **rc=0**；§8/§9/§10/§11 bullet 现场统计 11/6/6/5。
- `python3 tools/linux/check_syscall_contract.py --self-test` → **rc=0**；5 类注入各自 `rc=1` 且 FAIL 标签逐条命中（`contract-abi rb3 行`／`§9 区间`／`§8 来源标注`／`§1 逐字节`／`版本=0.10.0`），还原回绿 5/5（自检日志 1321 行逐项核过）。
- `bash` 运行期证据目录的 `run.sh` → **rc=1，汇总 PASS=40 FAIL=1**（完成区称 rc=0 / PASS=41 / FAIL=0 ⇒ 数字不符）。
  - 唯一失败：`[FAIL] 改动文件集 == 任务书范围 | expected=<契约 任务书 检查器> actual=`（run.sh L140 用裸 `git status --porcelain -uall`；WIP `61e41247` 于 19:59:21 落盘后工作树干净 ⇒ 该断言恒空）。
  - 其余全绿：A 检查器、B self-test、C 3 路真实注入（注入→FAIL→`cp`+md5 一致→回绿）、D 4 门控、F §1 独立复算（`7b3e0ec3…`==`7b3e0ec3…`、`rd15` 4==4）。
- `make -s check-contracts-pending` / `check-syscall-abi`（80/80）/ `check-contracts-dir` / `check-knowledge-refs` → **全 rc=0**。
- `make -s check-milestones-fresh` → rc≠0，红项 = `m13-testcases-016`（他任务，m14 段未跑到）⇒ 移交主会话，非本任务。

**§1 硬判据（不采信检查器，自写脚本独立算）** 临时树的独立脚本 `extract_sec1.py`（`git show <base>:<path>` 切 `## §1`→`## §2` + sha256）：
- 基线 `8352b41b` = 5561 B `7b3e0ec32af7a31f68e832efa773758c02e0cc1816eccdf5094da850fe6cbe17`；基线 `174298eb` 同；当前同 ⇒ **逐字节一致（exit=0）**；两基线仅差 `milestones-m14.md` 一行，契约内容等价。

**独立注入 1 路（自设计，不复用 5 类自检 / 3 路脚本）**：删 §6「M14 注记」整行 → 检查器 **rc=1** 且唯一 FAIL = `§6 含 M14 注记指针（§8）` → `cp` 还原 + md5 `32b32ff300e7b6d45c05d29fd9aa033a` 前后相等 → **rc=0 回绿**；`git status -uall` 还原后干净。

**约束核验**
- 越界：`git diff 8352b41b -- spec/ contracts/ manifests/` 与 `git diff 174298eb -- spec/ contracts/ manifests/` 均为空（exit=0）；改动集 = 契约 + 任务书 + 检查器 3 件 = 完成区声明；完成区 19 行 ≤30；未重建组件、未改 `spec/`/`Makefile`/`contracts/*.yaml`。
- §8–§11 逐条抽核可定位：DADAO-12 §3.1/§3.3/§3.6/§3.7/§5.1/§5.2/§5.3（cg0 复位 2、cg5 字段、`escape` 帧错误⇒`CFXESC`）、DADAO-13 §1 `hypv_cg_reg_deleg`、DADAO-22 §1（同 cfx 递归须存 cg6、A→B 免保存）与 §2（`immu18=0`/`rd15`/`rd8`/独立编号）、DADAO-23 §1–§3、SimRISC-00 §3.1（`hb‖hc‖hd` = 指令位 `[17:0]`）、SimRISC-12 §1（spurious failure／异常清保留标记／对齐／序变体）、Kaiwu §1.2（PTW 未映射⇒CFXMEM、权限⇒CFXPERM）、contract-abi §1.3/§4.5、contract-dynlink §2.4/§7；`immu18 = cause_info & 0x3FFFF` 另有 DADAO-22 §7.2/§12.2 `set.rd rd3, 0x3FFFF @@ 掩码提取 immu18` 佐证。
- `[spec-decision]` 均落 §7 #5–#8 + 任务书「待裁定」#1–#3；契约内无编造的 `[用户裁定 2026-11-13]`（仅既有 2026-10-14）。

**返工要求（仅此 1 项）**：运行期证据目录的 `run.sh` L140「改动文件集」断言改用**钉常量基线**（分支基线 `8352b41b`：`git diff --name-only 8352b41b`；或 `<base>..HEAD` ∪ `git status`），使提交前后均成立——禁裸 `git status`（提交后恒空 ⇒ 假 FAIL）；改后重跑至 rc=0（PASS=41 FAIL=0）并同步完成区数字。

**非阻断 finding（交 architect 收尾改）**：① §8 第 3 条「supv 期 `escape` 走 cg2 掩码行」与第 4 条「`escape` 不查掩码、不因掩码被拒」措辞张力（DADAO-12 §5.3 无掩码检查），建议第 3 条去掉 `escape`；② §8「`cfx_hmon` 放行责任在固件（HBI 初始化）侧」与 DADAO-23 §3「hmon 除外、由 hypv/HEE 保留」略有出入；③ 完成区 #5 对 `check-milestones-fresh` 红项归因不准（实为 `m13-testcases-016`；`174298eb` 已把本任务行移入「进行中」，合并后自愈）。

### 第 2 轮 engineer 自审（返工；对应 reviewer Needs Revision 1 项阻断 + 3 项非阻断）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 【阻断】证据脚本用裸 `git status --porcelain -uall` 断言改动集：WIP `61e41247` 提交后工作树干净 ⇒ 断言恒空、rc=1 | ✅已修 | 拆两基线：`CONTRACT_BASE=174298eb`（§1/§4/§6 与 spec/contracts 范围，钉常量、不可覆盖）+ `BASE=${BASE:-8352b41b}`（变更集，可覆盖）；改动集 = `$BASE..HEAD` ∪ 工作树（`core.quotepath=false`，`sort -u`）；脚本开头打印解析后 base sha | `bash run.sh` rc=0 `PASS=42 FAIL=0`；`BASE=HEAD bash run.sh` rc=1，唯一 FAIL = 「改动文件集 == 任务书范围」（`actual` 只剩工作树 2 件、缺已提交的检查器） |
| 自证「断言可失败」 | ✅已加 | 新增 G 段：以 `BASE=HEAD` 重放同一判据、期望 mismatch；若仍相等则判 FAIL（防恒真） | `[PASS] 反例：BASE=HEAD 时「改动文件集 == 任务书范围」判红 | expected=mismatch actual=mismatch` |
| 【非阻断①】§8 第 3 条把 `escape` 归入「走 cg2 掩码行」，与第 4 条「`escape` 不因掩码被拒」张力 | ✅已修 | 第 3 条删 `escape`，改为「`supv` 期 `trap` 与 `supv` 期同步异常」，并指向下条帧/目标判据 | 检查器 rc=0（§8 要点 13/13 PASS）；`--self-test` rc=0 |
| 【非阻断②】「`cfx_hmon` 放行责任在固件（HBI 初始化）侧」与 `DADAO-23 §3`（hmon 不参与逐 cfx HBI 初始化）不符 | ✅已修 | 改为「固件（hypv / HEE 引导）侧（`hmon` 不参与逐 cfx 的 HBI 初始化）」 | 同上；§8 来源标注仍齐 |
| 【连带】审阅记录含具体 `.work/**` 路径 ⇒ `check-knowledge-refs` 判红（2 处，非本任务正文） | ✅已修（仅改路径措辞，结论/数字不动） | 2 处改为「运行期证据目录的 `run.sh`」 | `make -s check-knowledge-refs` rc=0（0 具体引用） |
| 完成区数字与门槛同步 | ✅已修 | PASS 41→42；范围句改「`..HEAD` ∪ 工作树」；#5 台账归因改现场事实、新增 #6 | 见完成区 |

判决：1 项阻断 + 3 项非阻断全部处置，无未修 finding ⇒ 状态保持 **待验收**。

### 第 2 轮 reviewer 验收

**判决：Accepted**（第 1 轮唯一阻断已修，回归全绿；本记录为独立重跑结果）

**1. 阻断项复核（证据脚本）**
- `bash 运行期证据目录的 run.sh` → **rc=0，`== 汇总：PASS=42 FAIL=0 ==`**（与完成区 42/0 一致）。
- 改动集断言已改「钉常量基线 + `$BASE..HEAD` ∪ 工作树」：`CONTRACT_BASE=174298eb`（§1/§4/§6 与 spec/contracts 范围，不可覆盖）+ `BASE=${BASE:-8352b41b}`（默认钉常量、非 `HEAD`）；E 段现场变更集 = 契约 + 任务书 + 检查器 3 件。
- 可达 FAIL 自证（本人重放，不采信自审）：`BASE=HEAD bash …run.sh` → **rc=1，`PASS=41 FAIL=1`**，计数 FAIL 仅 `改动文件集 == 任务书范围`（`actual` 只剩工作树 2 件、缺已提交的检查器）；G 段 `[PASS] BASE=HEAD 判红 | expected=mismatch actual=mismatch` ⇒ 非恒真。
- 覆盖方向核：`BASE` 只会让变更集变大 ⇒ 无「凑绿」路径；§1/§4/§6 走不可覆盖的 `CONTRACT_BASE`。

**2. §1 硬判据（自写脚本独立算，不采信被审脚本）**：`extract_sec1.py 8352b41b` → 5561 B `7b3e0ec32af7a31f68e832efa773758c02e0cc1816eccdf5094da850fe6cbe17` == 当前，`byte_identical=True`，exit=0。

**3. 回归（全部本人重跑）**
- `python3 tools/linux/check_syscall_contract.py` → **rc=0**、FAIL 0；§8/§9/§10/§11 = **11/6/6/5**（合计 28，与完成区一致）。
- `… --self-test` → **rc=0**；`5 类注入，失败 0 项`；注入后非零 5 / 还原回绿 5。
- `make -s check-contracts-pending`、`check-syscall-abi`（`80/80 checks passed`）、`check-contracts-dir`、`check-knowledge-refs`（`0 具体 .work/** 引用`）→ **全 rc=0**。
- 独立注入回归：删 §6「M14 注记」→ rc=1、唯一 FAIL `§6 含 M14 注记指针（§8）` → `cp`+md5 `be9cf9fc6ae5fc50d…` 前后相等 → rc=0。

**4. 越界与对账**：`git diff 8352b41b -- spec/ contracts/ manifests/` 空（exit=0）、`git diff 174298eb..HEAD -- …` 空；改动集 3 件 = 完成区声明；完成区 20 行 ≤30；第 1 轮记录 27 行 ≤40；`git status -uall` 仅契约 + 任务书两处改动。

**5. 返工范围核**：契约改动仅 §8 第 3 条（删 `escape`、指向下条帧/目标判据）与第 6 条（`固件（hypv / HEE 引导）侧`、`hmon 不参与逐 cfx 的 HBI 初始化`），与 `DADAO-12 §5.2/§5.3`、`DADAO-23 §3` 一致，均在任务书范围内；未改 `spec/`、`Makefile`、`contracts/*.yaml`、`manifests/`。

**自查修正**：第 1 轮记录中我方所写的临时目录绝对路径改为措辞（结论/数字不动）；具体 `.work/**` 2 处已由返工改措辞且 `check-knowledge-refs` PASS。

**未决（移交主会话，不阻断）**：台账行移位（`174298eb` 已移入「进行中」，合并后自愈）；`m13-testcases-016` 红属他任务；证据脚本是否常驻 L1 待 K0 收口裁定。
