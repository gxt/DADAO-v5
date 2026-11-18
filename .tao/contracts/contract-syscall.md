# Linux syscall 映射合约（M8 用户态映射 + M14 内核侧接口）

> **版本：0.9.2**（随 ABI 册 `DADAO-21` 版本线；M14 的**内核侧扩展** §8–§11 属 v5 自定内容，见下方「v5 扩展」注记，不计入本版本号）[DADAO-21 §4. 系统调用规范]
>
> **v5 扩展（M14）**：§8–§11（`umon`/`jmon`/`smon` 入口与分工、errno 边界、`rb3=rbtp`、`lr/sc` 原子性前提）**不在 `DADAO-21` 正文内**，按 `DADAO-12/13/23`、`SimRISC-00/12`、`Kaiwu` 与 `ADR-0025` 归一化；其变更记录见 §12，版本号不随之变动（`check-spec-drift` 要求合约版本 == 上游册版本）。
>
> **来源**：`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）§4 系统调用规范、§1 寄存器规范、§3.2 传参、§3.4 返回值；`spec/DADAO-22-SBI-主管系统二进制接口.md`（0.7.1）§1 调用约定、§2 用户态异常处理（umon / jmon）；**M14 内核侧**另引 `spec/DADAO-12-SEE-主管系统运行环境.md`（§3.1 / §3.2 / §3.3 / §3.4 / §3.6 / §3.7 / §5.1 / §5.2 / §5.3 / §2.2.6）、`spec/DADAO-23-HBI-超管系统二进制接口.md §1–§3`、`spec/SimRISC-00-指令系统设计.md §3.1`、`spec/SimRISC-12-其它指令.md §1`、`spec/Kaiwu-测试机运行环境.md §1.2`；决策 `.tao/adr/adr-0025-m8-scope-linux-compat.md`（`ADR-0025`，Accepted，`D1`/`D2`/`D6`/`D7`）；端序与 ELF machine id 引用 `.tao/contracts/contract-abi.md`（§1.7）、`.tao/contracts/contract-elf.md`；TLS 模型分工引用 `.tao/contracts/contract-dynlink.md`（§2.4 / §7）。号表口径之**上游参照** = Linux 内核 `7.2.10`（**内容溯源，非执行依赖**，锁定见 §1.2）。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）][ADR-0025]
>
> **版本基准**：版本头取 **ABI 册（0.9.2）** 为投影基准（syscall 的**寄存器约定本体**在 `DADAO-21 §4`）；SBI 册（0.7.1）为**入口 / 分发**参照；M14 内核侧接口以 SEE / HEE / HBI 三册的寄存器与异常路由为**唯一真源**（本合约只归一化、不重定义）。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）][DADAO-12 §5. 异常进入与异常退出]
>
> **范围**：M8 P0 契约①——**Linux 语义映射**：号表口径与来源锁定（§1）、入口（§2）、参数与返回（§3）、errno 约定（§4）、独立 oracle 口径（§5）、QEMU user-mode 角色与范围外边界（§6）、裁定 / 锁定清单（§7）；**M14 起**增内核侧接口：内核侧入口与 `umon`/`smon`/`hmon` 分工（§8）、errno 表示与边界（§9）、TLS（`rb3 = rbtp`）维护责任（§10）、原子性前提（§11）。syscall 的**寄存器约定**不在本合约重复定义，一律**指针**到 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2`；动态链接 ABI 见 `SPEC-139t`（`contract-dynlink.md`）。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）]
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]` 标注 spec/ 来源；ADR 决策补足者标 `[ADR-NNNN DN]`；**用户逐条裁定**者标 `[用户裁定 YYYY-MM-DD]`（写明原话 / 选项标签 + 渠道）；spec/ 与 ADR 均未定者标 `[spec-decision]` 并写明「待用户裁定」。不写行号。
>
> **说明**：本合约**不复制**上游 `spec/` 正文（只**指针**）；与 `spec/` 冲突时阻断实现，走变更流程（`docs/Process-02-合约编写规范.md`）。[DADAO-21 §4. 系统调用规范]
>
> **落点**：本合约位于 `.tao/contracts/`（`INFRA-071t` Phase B 迁移落点；`check-contracts-dir` 白名单允许 `contract-*.md`）。引用方按文件名 `contract-syscall.md` 解析，不硬编码目录。[INFRA-071t]

---

## §1 号表口径与来源锁定

### §1.1 口径

- syscall 号存放在 **`rd15`**，**沿用 RISC-V Linux 编号**。[DADAO-21 §4. 系统调用规范][ADR-0025 D1]
- `rd15` 属**软件调用约定层**；它与指令编码层的硬件事务编号 `trap cfxha, immu18` 的 `immu18` 是**两个独立层次**、互不覆盖——`immu18` 决定「是什么调用」（硬件异常分发），`rd15` 给具体子功能（Linux 号）。[DADAO-21 §4. 系统调用规范]
- **本合约不重抄号表正文**：具体号值以 §1.2 的锁定来源为准（避免与上游正文重复、亦避免凭空写号）。[ADR-0025 D1]

### §1.2 来源锁定（号表真源）

- **权威来源（upstream）**：Linux 内核 **`7.2.10`**——uapi `include/uapi/asm-generic/unistd.h`（64 位通用号）+ `arch/riscv/include/uapi/asm/unistd.h`（RISC-V 增补）+ **完整号表载体 `scripts/syscall.tbl`**（含自 244 起的 arch-specific 区内的 `riscv_*`）。**版本身份 = git commit**（annotated tag `v7.2.10` 的 **peel commit**）：`7b20d05fd38de8e0be168956f6fd241d750c7d69`（tag object 自身 `57eee103859fa039a1f2bf343c4453ef40661be8` **不是** commit）；pin 由 `INFRA-075t` 承载于 `manifests/components.lock.toml` 的 `linux` 条目（`repository` = TUNA `linux-stable.git` + `commit` + `shallow`/`shallow_ref = "v7.2.10"` + `patchless = true`；**组件源一律 git 基线**）。已验签 tarball `.cache/linux-<版本>.tar.xz`（sha256 `2feaa704…cff2ebf3` + `.tar.sign`）**只作校验物 / 下载原件，不作组件源**。[ADR-0025 D1]
- **本仓已锁定快照（可核 / 可复算）= `qemu` 组件 vendored 的同一号表**：`qemu`（`manifests/components.lock.toml`，commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943` = `v11.1.1`）随源码携带：

  | 组件内路径（相对 qemu 树） | sha256 |
  |---|---|
  | `linux-user/riscv/syscall.tbl` | `8872daa692005172eccfee147ee38591ce2c005103026ea33a049f044418d41d` |
  | `linux-headers/asm-riscv/unistd.h` | `0134f2d3cec62a5be0028498ae86408a513b734036afd2d845e239a2079f59e3` |
  | `linux-headers/asm-generic/unistd.h` | `9ec1faddab5c363614b166ee7eed3f7723529e3a32312aad14fc6d0df5204354` |
  | `linux-headers/asm-riscv/unistd_64.h`（**QEMU 侧展开派生**；内核树内无此文件） | `5845303aba2752c38a3694b7377d7c09fe5e1854d6d5210e155e6000491c2abe` |

  复算方式 = 按 `manifests/` 锁 checkout 各组件（本地物化于 `.work/source/<组件>/`，`.work/` 属可重建构建区）后重算上列 sha256；不等即快照已漂移。[ADR-0025 D1]
- **与内核 `7.2.10` 的一致性（本任务现场复核，均可复算）**：① 内核 **git 工作树**（`.work/source/<组件>/`，按 §1.2 锁 checkout）与其**校验物** tarball `diff -rq` **0 差异**（`INFRA-075t` 现场；42 s、两侧各 94775 文件），且 `.cache/linux-<版本>.tar.xz` 的 `sha256` **重算一致**；② 内核 `include/uapi/asm-generic/unistd.h`（sha256 `9ec1fadd…`）与快照**逐字节相同**；③ 内核 `arch/riscv/include/uapi/asm/unistd.h`（sha256 `0134f2d3…`）与快照**逐字节相同**；④ 内核 `scripts/syscall.tbl` ↔ 快照 `linux-user/riscv/syscall.tbl` 在**共同名集（322 名）上号值 0 冲突**（内核多 9 条更新号）；⑤ 内核 `scripts/syscall.tbl` ↔ 快照展开头 `unistd_64.h` 共同名集（328 名）**0 冲突**。[ADR-0025 D1]
- **交叉核验（环境相关，非锁定真源）**：宿主 `linux-libc-dev` 6.8.0-147 的 RISC-V uapi（`/usr/riscv64-linux-gnu/include/asm/unistd.h`，`riscv64-linux-gnu-cpp -D__LP64__ -dM` 取值）与快照在**共同名集上号值逐条一致**；**以独立复算为准 = 共同名集 315 名、号值 0 冲突**（两侧**名集**差异项随宿主 libc 版本与 `__NR3264_*` 别名归一方式而变，**非稳定量、不据其下判断**）。[ADR-0025 D1]
- **上游版本已锁定**：内核 `7.2.10`（版本身份 = **git commit `7b20d05f…`**〔annotated tag `v7.2.10` peel〕，tarball `sha256` 仅作校验物）；本契约**不重抄号表正文**，取号以本节锁定来源为准。[ADR-0025 D1]

### §1.3 号段边界（`rd15` / arch-specific / audit）

- **arch-specific 号段**：Linux 内核 uapi 预留「各架构自有 syscall **自 244 起、至多 16 个**」（`__NR_arch_specific_syscall` = 244 起）；RISC-V 占用其中两个（`riscv_hwprobe` / `riscv_flush_icache`）。本合约沿用 RISC-V 号表 ⇒ 该段**随表一并沿用**。[ADR-0025 D1]
- **DADAO 是否另设 arch-specific 私有号**：**已裁定（2026-10-14，经主会话问答；用户原话/选项标签「沿用 RISC-V arch-specific（推荐）」）** ⇒ DADAO **不另设**私有号段，直接沿用 RISC-V 的 arch-specific 号（`riscv_hwprobe` / `riscv_flush_icache`）。[ADR-0025 D1][用户裁定 2026-10-14]
- **audit 号段 ≠ syscall 号段**：`AUDIT_ARCH_*`（`include/uapi/linux/audit.h`）是 **audit 子系统的架构标识**，由 ELF `e_machine` 派生（DADAO = `EM_DADAO` `0x0DA0`），与 `rd15` 的 syscall 号空间**无关**，二者不得混用。[ADR-0003 D1]
- **audit 取值形态（已裁定）**：**已裁定（2026-10-14，经主会话问答；用户原话「定义 `AUDIT_ARCH_DADAO`，BE，64 位」）** ⇒ `AUDIT_ARCH_DADAO` = `EM_DADAO`（`0x0DA0`）`| AUDIT_ARCH_64BIT`，**不带** `AUDIT_ARCH_LE`；与 v5 大端（`EI_DATA = ELFDATA2MSB`）一致。参考实现（内容溯源，非执行依赖）在其 Linux 端口取 `__AUDIT_ARCH_LE`，**本项目不采用**。[ADR-0003 D1][用户裁定 2026-10-14]

## §2 入口（`umon` / `jmon` 两条路径）

- **发起 / 返回**：`trap cfxha, immu18` 发起；被调方以 `escape cfxha, [excp_cause_ip, 4]` 返回（落到 `trap` 下一条）。**指针**，不复制正文。[DADAO-21 §4. 系统调用规范][DADAO-22 §1. 调用约定]
- **分发入口 = SBI 的 syscall 功能号**：`umon`（`cfx0`，user 模式异常入口）以 `immu18 = 0`（`SBI_UMON_SYSCALL`）分发用户态 syscall（入参 `rd15 = nr`、出参 `rd8 = result`）；`jmon`（`cfx1`，jail 模式入口）以 `immu18 = 0`（`SBI_JMON_SYSCALL`）分发受限用户态 syscall。[DADAO-22 §2. 用户态异常处理（umon / jmon）]
- 两条入口的 `immu18` **各自独立编号、互不冲突**（`umon` 与 `jmon` 为独立上下文）。[DADAO-22 §2. 用户态异常处理（umon / jmon）]
- **两条路径与 §4 的关系**：`DADAO-21 §4` 定义**发起方式 / 传参 / 返回**（与 `cfxha` 取值无关）；`DADAO-22 §2` 定义 **`cfx0`/`cfx1` 的 `immu18=0` 分发入口**。同一次 `trap` 的**两层**：`immu18` 选入口（`umon`/`jmon`），`rd15` 给 Linux 号。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）]
- **M8 口径**：M8 用户态栈的主入口取 **`umon`（`cfx0`）**；`jmon` 为受限上下文的**对等入口**，其号表 / 传参 / 返回 / errno 口径与本合约**相同**（差异仅在权限上下文）。改选入口属 P1/P3 实现选择，如需变更由用户裁定。[DADAO-22 §2. 用户态异常处理（umon / jmon）][ADR-0025 D2]

## §3 参数与返回

- **参数寄存器**：数据 `rd16–rd31`、地址 `rb16–rb31`、浮点 `rf16–rf31`；三组**各自独立计数、自 16 起**，参数按类型分配到对应组、**不共享槽位**。**指针**，不复制正文。[DADAO-21 §3.2.1 参数寄存器：Parameter registers][DADAO-21 §4. 系统调用规范]
- **寄存器序与类型提升与 `contract-abi.md §4.1/§4.2` 同口径**（同一份 ABI 传参规则）：窄标量（`<8B`，如 `_Bool`/`char`/`short`/`int`）传递前提升为 8B canonical 且保持符号位，扩展由 **caller** 负责；指针类参数走 RB 组。**「扩展由 caller 负责」的出处 = `ADR-0018 C4`**（`contract-abi.md §4.2` 的同一口径）。[DADAO-21 §3.2.2 标量参数：Scalar type parameter][ADR-0018 C4]
- **溢出仍按 ABI 栈规则**：某 bank 槽位用尽后该 bank 后续参数入栈，8B 对齐；M3/ABI 口径为**全局声明序单栈区**、每槽 8B。[DADAO-21 §3.2.4 栈溢出规则]
- **示例（与 ABI 正文同例）**：`read(int fd, void *buf, size_t count)` ⇒ `fd → rd16`、`buf → rb16`、`count → rd17`。[DADAO-21 §3.2.1 参数寄存器：Parameter registers]
- **返回值 = `rd8`**：syscall 返回值统一放 `rd8`；`DADAO-22 §2` 表内出参 `rd8 = result` 与之一致。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）]
- `rf16–rf31` 属 RF bank；浮点 syscall 参数随 RF 后端能力而定，本合约不新增口径（RF 机制见 `contract-abi.md §1.4` / `contract-fp.md`）。[DADAO-21 §3.2.1 参数寄存器：Parameter registers]

## §4 errno 约定（**已裁定**）

- **用户裁定（2026-10-14，经主会话问答；用户原话 / 选项标签「A：`rd8` 负值（推荐）」）** ⇒ 错误以 **`rd8` 负值（`-errno`）** 承载（Linux 原生约定）；`rd1`/`rderrno` **不参与** syscall 错误路径；musl `__syscall_ret()` **零改**；与 §5 golden 对照同口径。候选 B（`rd1`）/ C（双写）**不采用**（下条保留作记录）。[ADR-0025 D7][用户裁定 2026-10-14]
- **上游 spec 的现状（事实）**：`DADAO-21 §4` 只规定返回值放 `rd8`，**未**规定错误码承载寄存器；`DADAO-21 §1` 定义 `rd1` = `rderrno`（`error number`），但 spec **未**把它与 syscall 错误路径关联。[DADAO-21 §4. 系统调用规范][DADAO-21 §1. 寄存器规范]
- **对照侧的约定（事实，外部独立证据）**：Linux 的错误约定是**返回寄存器承载 `-errno`**——musl 的 `__syscall_ret()` 判 `r > -4096UL ⇒ errno = -r, return -1`（来源：musl 上游 `src/internal/syscall_ret.c`，`https://git.musl-libc.org/cgit/musl/plain/src/internal/syscall_ret.c`，2026-10-14 取回）；QEMU 的 RISC-V 用户态亦把负值写回参数 0 寄存器（证据：`qemu` 组件 `linux-user/riscv/cpu_loop.c` 内 `env->gpr[xA0] = ret`，`ret` 取自 `do_syscall()` 的负 errno）。[ADR-0025 D7]
- **候选口径（三选一；2026-10-14 已定取 **A**，B/C 记录备查）**：[ADR-0025][用户裁定 2026-10-14]
  - **A（Linux 原生）＝ 已裁定采用**：错误以 `rd8` **负值（`-errno`）** 承载；`rd1`/`rderrno` 不参与 syscall 错误路径。代价最小：musl `__syscall_ret` 零改；与 §5 golden 对照同口径。
  - **B（DADAO 原生）**：错误码写 `rd1`（`rderrno`），`rd8` 语义另定（如成功值 / `-1`）。需改 musl 侧错误检查（读 `rd1`），并与 golden 对照产生**结构性差异**。
  - **C（双写）**：同时写 `rd8`（负值）与 `rd1`。冗余但两套消费者皆可读；需在契约冻结后逐处同步。
- **消解**：本节裁定**消解 §7 #1**（errno 载体）；实现侧（`musl` 端口 / `linux-user`）按 **A（`rd8` 负值）** 实现，**不得**自选 B/C。[ADR-0025 D7][用户裁定 2026-10-14]

## §5 独立 oracle 口径（不从实现反推）

- **期望值来源（判据顺序）**：① 上游 spec（`DADAO-21 §4` / `DADAO-22 §2`）与 Linux 语义（号表按 §1.2 锁定来源；errno 按 §4 裁定后口径）；② **RISC-V + musl 的 golden 对照**（同程序跑对照面）；③ 对照边界项（端序 / `long double` / `fenv` / UB / 实现定义）按既有 `[spec-decision]` 登记为「非判据真源」。[ADR-0025 D7]
- **禁止**：**不得**从 v5 自身实现反推期望值——`qemu` 的 DADAO 端口/补丁、`musl` 的 DADAO 端口、本仓工具的输出均不得作期望值来源；期望值须独立派生自 ①/②。[ADR-0025 D7][spec-decision]
- **口径与对照面的关系**：号表沿用 RISC-V 编号（§1.1）正是为让 golden 对照**逐号可比**——对照面与 DADAO 同号，差异可归因到实现而非号表。[ADR-0025 D1][ADR-0025 D7]
- **归属**：具体对照 harness / 判据 / 回归门控 = **P4**（`ADR-0025 D6` 顺序「契约 → musl → 动态 → linux-user」之末）；本合约只钉口径与禁止项。[ADR-0025 D6]

## §6 QEMU user-mode 角色与范围外边界

- **无内核目标**：M8 不引入内核（VFS / MM / 调度 / 信号）；本合约只覆盖**用户态可见**的 syscall 语义映射。[ADR-0025 D2]
- **QEMU user-mode 的角色**：`linux-user`（qemu-user）在 M8 中充当**宿主侧 syscall 转发层**（「无内核」下的语义提供方）——把 guest 的 `trap`（syscall）翻译为宿主 syscall，并按 §3 写回返回寄存器。[ADR-0025 D2][ADR-0025 D6]
- **边界**：`linux-user` 属 **P3**；其转发实现**须遵循本合约**（入口 §2 / 传参·返回 §3 / errno §4），且**不得**充当 §5 的期望值来源。v5 现状仅有 system 模式（`qemu-system-dadao -M kaiwu-tiny` / `-M kaiwu-vast`）；`linux-user` 的 DADAO 目标是**新增工作**（非改造既有）。[ADR-0025 D6][ADR-0025 D2]
- **停机协议不混用**：用户态进程退出由 syscall `exit` / `exit_group` 承载；测试机侧 **exit port**（`ADR-0004 D3`）与 semihosting **`SYS_EXIT`**（`ADR-0020 D8`）是**另外的**停机协议，不得与本 syscall 路径混用。[ADR-0004 D3][ADR-0020 D8]
- **范围外（指针）**：动态链接 ABI / PIC·GOT·PLT / `PT_INTERP`·`AT_*`（→ `SPEC-139t`）；TLS/线程（`ADR-0025 D5` 先查证再定）；具体号值正文（→ §1.2 锁定来源）；内核语义本体（→ §6 首条）。[ADR-0025 D6][ADR-0025 D5]

> **M14 注记**：本节「无内核目标」是 **M8 的历史范围**（`ADR-0025 D2`），原文与 M8 结论**不改写**；M14 引入内核后，**内核侧**入口 / errno 边界 / TLS / 原子性见 **§8–§11**。[ADR-0025 D2][DADAO-12 §5. 异常进入与异常退出]

## §7 裁定 / 锁定清单（原「待裁定」；#1–#4 已裁定 / 锁定，#5–#8 = M14 内核侧自决项）

| # | 项 | 状态 | 归属 / 指针 |
|---|----|------|------------|
| 1 | errno 载体（`rd8` 负值 / `rd1` rderrno / 双写） | **已裁定**：A（`rd8` 负值）〔2026-10-14〕 | §4；`ADR-0025 D7` [ADR-0025 D7] |
| 2 | DADAO 是否另设 arch-specific 私有号 | **已裁定**：不另设，沿用 RISC-V arch-specific〔2026-10-14〕 | §1.3；`ADR-0025 D1` [ADR-0025 D1] |
| 3 | `AUDIT_ARCH_*` 取值端序位（`__AUDIT_ARCH_LE` vs 大端） | **已裁定**：`AUDIT_ARCH_DADAO` = `EM_DADAO`\|`AUDIT_ARCH_64BIT`（BE，64 位），不带 `__AUDIT_ARCH_LE`〔2026-10-14〕 | §1.3；`ADR-0003 D1` [ADR-0003 D1] |
| 4 | 号表快照对应的**上游内核版本** | **已锁定**：内核 `7.2.10`（身份 = git commit `7b20d05f…`；与快照 uapi 逐字节相同 / 号表 0 冲突，见 §1.2） | 本合约 §1.2；pin 承载 `INFRA-075t` [ADR-0025 D1] |
| 5 | 内核侧入口与三方分工（`umon` 承载 / `smon` 异常 / `hmon` 服务；cg0 进入 vs cg2 返回与异常） | **已冻结（自决，`[spec-decision]`）**：`umon` 入口 + `escape cfx_umon` 自帧返回；cg0 与 cg2 不得混用 | §8 [spec-decision] |
| 6 | errno 边界与内核内部码（`[-4095, -1]`；重启码不外泄；`-ENOSYS`；不用 `rd1`） | **已冻结（自决，`[spec-decision]`）**：边界取 musl `__syscall_ret()` 判据，§4 的 A 口径不变 | §9 [spec-decision] |
| 7 | TLS 内核侧责任（`rb3` 保存 / 恢复；`clone` SETTLS；`execve` 清零；`initial-exec` / `local-exec` 分工） | **已冻结（自决，`[spec-decision]`）**；`clone` 双返回归 musl wrapper、内核只保证子入口 `rd8 = 0`，`execve` 清零实现点由 musl 移植校准（用户裁定 2026-11-13）；TP 方向 / 偏置仍归 musl arch 宏（§10） | §10 [spec-decision] |
| 8 | 原子性前提（`lr` / `sc` 沿用 `SimRISC-12 §1`；`futex` 无丢唤醒；`clone` 原子可见） | **已冻结（自决，`[spec-decision]`）**；不定义 TLB / cache / 多核保留标记仲裁 | §11 [spec-decision] |

## §8 内核侧入口（`umon` / `smon` / `hmon` 的分工）

- **用户 syscall 的路径（M14 K0 口径）**：用户态执行 `trap cfx_umon, 0`（`SBI_UMON_SYSCALL`）⇒ 目标 `cfx_umon` 收到 `excp_cause_id = CFXTRAP`（`1 << 0`）；模式切换取 **user 行（cg0）** 的 `cfx_umon_user_switch_run_mode`（复位值 `2 = supv`），向量取 `cfx_umon_user_excp_vector`（复位值 `0`，内核须改写）⇒ 内核向量**在 `supv` 模式、`cfx_umon` 上下文内**开始执行；返回 = `escape cfx_umon, [excp_cause_ip, 4]`，落回 `trap` 下一条。[DADAO-12 §3.1 cg0 - user mode 寄存器][DADAO-12 §5.2 异常进入流程][DADAO-22 §2 用户态异常处理（umon / jmon）]
- **`jmon` 同构**：`trap cfx_jmon, 0`（`SBI_JMON_SYSCALL`）走 **jail 行（cg1）** 的 `cfx_jmon_jail_switch_run_mode` / `cfx_jmon_jail_excp_vector`；`immu18` 与 `umon` **各自独立编号**，号表 / 传参 / 返回 / errno 口径与本合约相同（§2）。[DADAO-22 §2 用户态异常处理（umon / jmon）][DADAO-12 §3.2 cg1 - jail mode 寄存器]
- **cg0 与 cg2 的分工（不得混用）**：**进入** user→monitor 一律走 **cg0（`cfx_umon_user_switch_run_mode` / `cfx_umon_user_excp_vector`）** 行；**`supv` 期**发起的 `trap` / `escape` 与 `supv` 期同步异常走 **cg2（`cfx_umon_supv_*` / `cfx_smon_supv_*`）** 行与 `cfx_smon_supv_excp_vector`（内核提供）。`_supv_` 行**不是** user 入口配置，不得把同名 `_supv_` 当作 user 入口。[DADAO-12 §3.1 cg0 - user mode 寄存器][DADAO-12 §3.3 cg2 - supv mode 寄存器]
- **返回路径的帧与目标**：`escape` 的 `cfxha` 必须等于当前 cfx（本路径 = `cfx_umon`），返回的 cfx / 运行模式 / `IP` 全取自当前 cfx 的异常帧；因源 cfx = 目标 cfx，来源掩码的**自身位**被硬件忽略 ⇒ 该路径不因掩码被拒，被拒只可能是帧 / 目标错误（`cfxha` 非当前 cfx 或 `excp_cause_id = 0`）⇒ `CFXESC`，不得与 `CFXPERM` 混同。[DADAO-12 §3.3 cg2 - supv mode 寄存器][DADAO-12 §5.1 指令行为说明][DADAO-12 §5.3 异常退出流程]
- **`supv` 期跨 cfx 转移的掩码**：内核在 `supv` 下向其它 cfx `trap`（如 `cfx_hmon`）或访问其寄存器，受**目标 cfx** 的 `*_supv_cfxtrap` / `*_supv_cfxreg` 第「源 cfx = 当前 `inner_cfx_code`」位约束（`0=允许`、`1=屏蔽`；自身 cfx 位硬件忽略）；被掩码拒绝 ⇒ `CFXPERM`。内核须在启动时把所需来源位清 `0`，**不得**依赖固件默认掩码长期放行宽于需要的来源。[DADAO-12 §3.3 cg2 - supv mode 寄存器][DADAO-12 §5.2 异常进入流程]
- **放行与自配的责任切分（K0 口径）**：固件侧（`hmon` / HBI 初始化）**只放行**——① 清 `cfx_umon`（cg0）/ `cfx_jmon`（cg1）的 `*_supv_cfxtrap` / `*_supv_cfxreg` 中「源 cfx = 内核所属 `inner_cfx_code`」位（`0=允许`），使内核可在 `supv` 下 `trap` 到 / 访问对应 cfx；② 置 hypv 侧 `hypv_cg_reg_deleg`，允许 `supv` 访问相应 cg 行 / 寄存器；`cfx_hmon` 等 hypv 保留扩展的放行责任在固件侧。**入口寄存器由内核自配**——`cfx_umon_user_switch_run_mode` / `cfx_umon_user_excp_vector`（`jmon` 同构；向量复位值 `0` ⇒ 内核须改写，`switch_run_mode` 复位 `2 = supv` 可沿用）由内核在启动时按需写入，**固件不代写入口寄存器**（`DADAO-23 §3` 初始化清单亦列 `<mode>_switch_run_mode` / `<mode>_excp_vector`；本合约按用户 2026-11-13 裁定收窄为「固件只放行、入口寄存器内核自配」，不要求上游改文）。两侧责任不得互推：内核**不得**假定「总能自配置」（放行未给即 `CFXPERM`），固件也**不得**替内核配置入口。[DADAO-12 §3.3 cg2 - supv mode 寄存器][DADAO-12 §3.4 cg3 - hypv mode 寄存器][DADAO-23 §3 启动与引导移交约定][用户裁定 2026-11-13]
- **硬件现场只有 cg5 异常现场字段**（`excp_prev_run_mode` / `excp_prev_cfx_code` / `excp_cause_id` / `excp_cause_ip` / `excp_cause_info` / `excp_pending`）：**不保存通用寄存器**。内核向量必须在使用任何寄存器前自行保存、返回前恢复，**不得**把 cg5 当 `pt_regs`；少量暂存用 cg6（`scratch_regs_num ≥ 2`），其余落栈。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §3.7 cg6 - 暂存寄存器]
- **入口可见状态**：`rd15 = nr`；参数按 §3（`rd16–rd31` / `rb16–rb31` / `rf16–rf31`）；`excp_cause_ip` = `trap` 指令地址；`excp_cause_id = 1 << 0`（`CFXTRAP`）；`excp_cause_info` = 触发指令编码，`immu18 = excp_cause_info & 0x3FFFF`（`ciii` 的 18 位立即数占指令位 `[17:0]` = `hb‖hc‖hd`，`hb` 高 / `hd` 低）。该等式是**本合约内的推导**（`excp_cause_info` 存放触发指令编码、`immu18` 取其中 `[17:0]`），**上游 `DADAO-12` / `DADAO-22` 未明文写出**，按 `SimRISC-00 §3.1` 的指令位段推导；不要求上游补正。[DADAO-12 §3.6 cg5 - 异常现场寄存器][SimRISC-00 §3.1 指令域说明][用户裁定 2026-11-13]
- **`smon`（`supv` 同步异常）**：内核运行期同步异常（页表 / 对齐 / 非法指令 / cfx 权限等）按 `excp_cause_id` / `excp_cause_info` 分派，入口 = `cfx_smon_supv_excp_vector`（内核提供）；PTW 的异常归因（未映射 / 权限）沿用 `DADAO-12 §2.2.6` 与 `Kaiwu §1.2`，本合约**不重定义**。[DADAO-12 §5.2 异常进入流程][DADAO-12 §2.2.6 异常检查优先级][Kaiwu §1.2 越界访问与越界取指异常]
- **`hmon` / HBI**：内核→hypv 的服务调用走 `trap cfx_hmon, immu18`，返回 `escape cfx_hmon, …`；`hmon` 为**固件**、不是内核的一部分；函数号与语义不在此重抄，指针到 `spec/DADAO-23`（HBI）。[DADAO-23 §1 调用约定][DADAO-23 §2 系统信息（cfx_hmon）]
- **嵌套**：不同 cfx 的 cg5 相互独立（A→B 无需保存）；**同 cfx 递归**（如 `umon` 内再进 `umon`）前必须把 cg5 现场保存到 cg6 暂存、退出恢复。[DADAO-22 §1 调用约定][DADAO-12 §5. 异常进入与异常退出]

## §9 errno 表示（扩 §4；不改变 A 口径）

- **载体与符号**：`rd8` 按 **64 位有符号**解释；成功 = `>= 0`；错误 = `-errno`，取值范围 **`[-4095, -1]`**；`-4096` 及以下**不是** errno。判据与 musl `__syscall_ret()` 的 `r > -4096UL` 一致 ⇒ musl **零改**。[contract-syscall §4][外部权威 musl `src/internal/syscall_ret.c`]
- **内核内部码不外泄**：`ERESTARTSYS` / `ERESTARTNOINTR` 等 Linux **内核内部重启码**不得出现在用户可见的 `rd8` 上；内核必须在返回用户态前转成 `-errno` 或重新执行该系统调用。[spec-decision]（Linux 内核内部重启码语义的 v5 归一化；外部依据 = Linux `include/linux/errno.h`，非 DADAO 规范）
- **未支持 / 参数错**：不支持的系统调用返回 **`-ENOSYS`**，参数错误返回对应 **`-EINVAL`** 等负值；两者都是 `-errno` 形态、走 `rd8`。[contract-syscall §4][DADAO-21 §4. 系统调用规范]
- **不用 `rd1`**：不得用 `rd1`（`rderrno`）承载 syscall 错误，也不得与 `rd8` 双写；`rd1` 的 spec 语义与 syscall 错误路径无关（§4 已裁定 A）。[contract-syscall §4][DADAO-21 §1. 寄存器规范]
- **可见返回寄存器**：用户态只从 `rd8` 取 syscall 结果；指针返回值仍按 `rb8` 的既有 ABI 规则（`DADAO-21 §返回值`），但 **syscall 的标量结果不放 `rb8`**。[DADAO-21 §返回值][contract-syscall §3]
- **与 §4 的关系**：本节只补边界与内核侧责任，§4 的 A 口径（错误 = `rd8` 负值；`rd1` 不参与）**不变**。[contract-syscall §4][ADR-0025 D7]

## §10 TLS（`rb3 = rbtp`）

| 寄存器 | ABI 名 | 角色 | 内核侧责任 |
|--------|--------|------|------------|
| `rb3` | `rbtp` | thread pointer（TP） | 入口保存、返回恢复；不作传参 / 临时寄存器 |

- **事实**：`rb3` = `rbtp`（thread pointer）；v5 编译器**保留不分配**。[DADAO-21 §1.2 RB寄存器（Base registers）][contract-abi §1.3 RB 寄存器角色][contract-abi §4.5 callee-saved / caller-saved 与 CSR]
- **syscall 路径**：`rbtp` 属保留（编译器不分配）且跨 syscall 必须保持 ⇒ 内核入口保存、返回恢复；**不得**用 `rb3` 传参或作临时寄存器。[contract-abi §4.5 callee-saved / caller-saved 与 CSR][spec-decision]
- **`clone`（含 `CLONE_SETTLS`）**：子线程的 `rbtp` = `tls` 参数；父线程不变。**「双返回」属用户态 wrapper（musl `clone` / `pthread_create` 包装）语义**，内核侧只保证「子线程从 syscall 返回处开始执行时 `rd8 = 0`、其余寄存器现场 = 父现场副本（除返回寄存器与架构约定的差异）」，父线程返回子 tid；子进程栈切换 / 启动例程等编排由 wrapper 完成，**内核不实现两次返回**。[外部权威 Linux `clone(2)`][DADAO-21 §4. 系统调用规范][用户裁定 2026-11-13]
- **`execve`**：新映像的 `rbtp` **须清 `0`**（本合约只写约束）；清零的**实现点由 musl 移植任务校准**（内核 `execve` 路径 / musl 启动代码二者择一，本合约不指定）；TCB 由 libc 在进入 `main` 前自行初始化（musl `__init_tls` / `__set_thread_area` 路径），**内核不代设 TCB 布局**。[外部权威 musl `ldso/dynlink.c`][用户裁定 2026-11-13]
- **`initial-exec` / `local-exec` 的分工**：两者都是**用户态**链接 / TLS 模型；内核只保证「`rbtp` 的保存 / 恢复」+「`clone` / `execve` 的 `rbtp` 约束（上两条，实现点由 musl 校准）」。TP 方向（`TLS_ABOVE_TP` 等）与偏置（`TP_OFFSET` / `DTP_OFFSET`）**不在本合约决定**，归 musl arch 宏。[contract-dynlink §2.4 GOT 基址寄存器与 TP：口径][contract-dynlink §7 TLS][ADR-0025 D5]
- **单线程静态 init**：允许只用 `initial-exec`；`rbtp` 的保存 / 恢复与「进入用户态前有确定值（清 `0`，实现点由 musl 校准）」不得因「单线程」跳过。[spec-decision]

## §11 原子性（`clone` / `futex` / 用户 `lr`+`sc`）

- **基线语义不重抄**：`lr` / `sc` 的保留标记、成功 / 失败、宽度、对齐与清标记条件**一律**按 `SimRISC-12 §1`；`sc` 可能**偶发失败**（spurious failure），软件须循环重试；**异常或中断进入清除保留标记** ⇒ `lr`…`sc` **不能跨任何 syscall / 异常**。[SimRISC-12 §1 原子指令]
- **用户原子操作**：Linux `atomic_*` / `cmpxchg` 由 `lr` / `sc` 循环实现（可按宽度选 `.b` / `.w` / `.t` / `.o`）；acquire / release 变体（`lr.*.an` / `lr.*.ar` / `sc.*.ar` / `sc.*.nr`）用于 `smp_mb` / `smp_rmb` 等；单核 K0 下**不得**把「单核」当作免内存序假设，生成的序须与多核一致。[SimRISC-12 §1 原子指令][spec-decision]
- **`futex`**：`FUTEX_WAIT` 的「检查用户字 → 睡眠」必须原子：内核在持锁下用 `lr` 语义复核用户字（或等价的单核原子读）后再入队；`FUTEX_WAKE` 不得丢唤醒；`futex` 不改变用户 `lr` / `sc` 的语义。[外部权威 Linux `futex(2)`][spec-decision]
- **`clone`**：线程创建对用户可见的状态切换必须原子（子现场 = 父现场副本、`rd8 = 0`）；子线程 `rbtp` 按 §10 设置；不得让子线程看到半初始化的 TCB 指针。[contract-syscall §10][spec-decision]
- **不定义**：TLB 填充 / 失效 / ASID（K3）、cache / LLC 一致性、**跨 hart** 的保留标记仲裁（K0 单核，多核另立契约）。[spec-decision][ADR-0025 D6]

## §12 变更记录（v5 扩展；不改版本号）

- **0.9.2 + M14 扩展（2026-11-13）**：新增 §8–§11 内核侧接口（入口与三方分工 / errno 边界 / `rb3 = rbtp` / 原子性前提）；版本号仍随 ABI 册 `DADAO-21` 为 **0.9.2**（`check-spec-drift` 不变量：spec-sourced 合约版本 == 上游册版本）。[DADAO-21 §4. 系统调用规范][ISS-423]
- **同笔口径补写（2026-11-13，用户裁定）**：① §8 明确「`hmon` / HBI **只放行**源位与 `hypv_cg_reg_deleg`，**入口寄存器由内核自配**」；② §8 的 `immu18 = excp_cause_info & 0x3FFFF` 记为**合约内推导**（上游未明文）；③ §10 明确 `clone` 双返回属 musl wrapper、内核只保证子进程入口 `rd8 = 0`，`execve` 的 `rbtp` 清零由 musl 移植校准。以上均不改上游 `spec/`。[用户裁定 2026-11-13][ISS-423]
- **0.9.2 + §8 现场字段补 `excp_prev_cfx_code`（2026-11-18，`m14-spec-009`，用户裁定 B）**：`DADAO-12` 把 `cg5 rc1` 由 `reserved` 改为 `excp prev cfx code`（硬件陷入保存 `inner_cfx_code`、`escape` 恢复），故 §8 的「cg5 现场字段」清单由 5 项改为 6 项；内核侧用法不变（仍不得把 cg5 当 `pt_regs`）。版本号仍随 ABI 册 `DADAO-21` 为 **0.9.2**。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.3 异常退出流程]
- **追加方式**：此后按「日期 + 改动摘要 + 落点（§）/ 关联 ADR / ISS」追加；上游 spec 正文变更仍走 `docs/Process-02` 的同步流程，本记录只记 v5 扩展口径。[ISS-423]

---

## 附录 A：来源对照

| 本合约 § | 内容 | 来源 |
|----------|------|------|
| §1.1 | 号在 `rd15`、沿用 RISC-V 编号；`immu18` 与 `rd15` 双层 | `DADAO-21-ABI §4`；`ADR-0025 D1` |
| §1.2 | 号表真源与锁定快照（内核 `7.2.10` git commit / qemu `c3d48b7d…` / sha256） | `ADR-0025 D1`；`manifests/components.lock.toml`（`linux` / `qemu`）|
| §1.3 | arch-specific 号段（沿用 RISC-V，不另设）；audit 标识 ≠ syscall 号段；`AUDIT_ARCH_DADAO` = BE64 | `ADR-0025 D1`；`ADR-0003 D1`；用户裁定 2026-10-14；Linux 内核 uapi（内容溯源） |
| §2 | 入口 `trap cfxha, immu18` / `escape`；`umon`/`jmon` 分发 | `DADAO-21-ABI §4`；`DADAO-22-SBI §1`/`§2` |
| §3 | 参数 `rd16–31`/`rb16–31`/`rf16–31`、返回 `rd8`、提升与溢出（caller 扩展 = `ADR-0018 C4`） | `DADAO-21-ABI §3.2.1`/`§3.2.2`/`§3.2.4`/`§4`；`DADAO-22-SBI §2`；`ADR-0018 C4` |
| §4 | errno 载体 = `rd8` 负值（A，2026-10-14 已裁定）；musl/Linux 负值约定（对照证据） | `DADAO-21-ABI §4`/`§1`；musl 上游 `syscall_ret.c`；`ADR-0025 D7`；用户裁定 2026-10-14 |
| §5 | 独立 oracle：期望值来源与禁止项；golden = RISC-V+musl | `ADR-0025 D1`/`D6`/`D7` |
| §6 | QEMU user-mode 角色 / 边界；停机协议不混用；范围外；M14 注记指针 | `DADAO-12 §5`；`ADR-0025 D2`/`D6`；`ADR-0004 D3`；`ADR-0020 D8` |
| §8 | 内核侧入口：`umon` 入口 / 自帧返回、cg0 与 cg2 分工、cg5 现场、`smon` 同步异常、`hmon`/HBI 指针、同 cfx 嵌套、固件放行 vs 内核自配、`immu18` 合约内推导 | `DADAO-12 §3.1`/`§3.2`/`§3.3`/`§3.4`/`§3.6`/`§3.7`/`§5.1`/`§5.2`/`§5.3`/`§2.2.6`；`DADAO-22 §1`/`§2`；`DADAO-23 §1`/`§2`/`§3`；`SimRISC-00 §3.1`；`Kaiwu §1.2`；用户裁定 2026-11-13 |
| §9 | errno `[-4095, -1]`、内部重启码不外泄、`-ENOSYS`、不用 `rd1`、结果只走 `rd8` | `contract-syscall §3`/`§4`；`DADAO-21 §1`/`§4`/`§返回值`；musl `syscall_ret.c`；Linux `errno.h`；`ADR-0025 D7` |
| §10 | `rb3 = rbtp` 的内核侧责任；`clone` SETTLS / 双返回归 musl wrapper / 子入口 `rd8 = 0`；`execve` 清零由 musl 校准；`initial-exec` / `local-exec` 分工 | `DADAO-21 §1.2`；`contract-abi §1.3`/`§4.5`；`contract-dynlink §2.4`/`§7`；Linux `clone(2)`；musl `ldso/dynlink.c`；`ADR-0025 D5`；用户裁定 2026-11-13 |
| §11 | 原子性：`lr`/`sc` 基线不重抄、`futex` 无丢唤醒、`clone` 原子可见、不定义 TLB / cache / 多 hart | `SimRISC-12 §1`；Linux `futex(2)`；`contract-syscall §10`；`ADR-0025 D6` |
| §12 | 变更记录（M14 v5 扩展口径；版本号随 ABI 册不动） | `DADAO-21 §4`；`ISS-423`；用户裁定 2026-11-13 |
