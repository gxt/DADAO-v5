# Linux syscall 映射合约（M8：无内核的 Linux 用户态栈）

> **版本：0.9.2** [DADAO-21 §4. 系统调用规范]
>
> **来源**：`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）§4 系统调用规范、§1 寄存器规范、§3.2 传参、§3.4 返回值；`spec/DADAO-22-SBI-主管系统二进制接口.md`（0.7.1）§1 调用约定、§2 用户态异常处理（umon / jmon）；决策 `.tao/adr/adr-0025-m8-scope-linux-compat.md`（`ADR-0025`，Accepted，`D1`/`D2`/`D6`/`D7`）；端序与 ELF machine id 引用 `.tao/contracts/contract-abi.md`（§1.7）、`.tao/contracts/contract-elf.md`。号表口径之**上游参照** = Linux 内核 `7.2.10`（**内容溯源，非执行依赖**，锁定见 §1.2）。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）][ADR-0025]
>
> **版本基准**：版本头取 **ABI 册（0.9.2）** 为投影基准（syscall 的**寄存器约定本体**在 `DADAO-21 §4`）；SBI 册（0.7.1）为**入口 / 分发**参照。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）]
>
> **范围**：M8 P0 契约①——**Linux 语义映射**：号表口径与来源锁定（§1）、入口（§2）、参数与返回（§3）、errno 约定（§4）、独立 oracle 口径（§5）、QEMU user-mode 角色与范围外边界（§6）、裁定 / 锁定清单（§7）。syscall 的**寄存器约定**不在本合约重复定义，一律**指针**到 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2`；动态链接 ABI 见 `SPEC-139t`（`contract-dynlink.md`）。[DADAO-21 §4. 系统调用规范][DADAO-22 §2. 用户态异常处理（umon / jmon）]
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]` 标注 spec/ 来源；ADR 决策补足者标 `[ADR-NNNN DN]`；**用户逐条裁定**者标 `[用户裁定 YYYY-MM-DD]`（写明原话 / 选项标签 + 渠道）；spec/ 与 ADR 均未定者标 `[spec-decision]` 并写明「待用户裁定」。不写行号。
>
> **说明**：本合约**不复制**上游 `spec/` 正文（只**指针**）；与 `spec/` 冲突时阻断实现，走变更流程（`docs/Process-02-合约编写规范.md`）。[DADAO-21 §4. 系统调用规范]
>
> **落点**：本合约暂落 `.tao/knowledge/`（`check-knowledge-dir` 白名单允许 `contract-*.md`）。若 `INFRA-071t`（`contract-*.md` → `contracts/`，**待用户授权**）获批，本合约随之**整体迁移**；引用方按文件名 `contract-syscall.md` 解析，不硬编码目录。[ADR-0025]

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
- **边界**：`linux-user` 属 **P3**；其转发实现**须遵循本合约**（入口 §2 / 传参·返回 §3 / errno §4），且**不得**充当 §5 的期望值来源。v5 现状仅有 system 模式（`qemu-system-dadao -M dadao-m1`）；`linux-user` 的 DADAO 目标是**新增工作**（非改造既有）。[ADR-0025 D6][ADR-0025 D2]
- **停机协议不混用**：用户态进程退出由 syscall `exit` / `exit_group` 承载；测试机侧 **exit port**（`ADR-0004 D3`）与 semihosting **`SYS_EXIT`**（`ADR-0020 D8`）是**另外的**停机协议，不得与本 syscall 路径混用。[ADR-0004 D3][ADR-0020 D8]
- **范围外（指针）**：动态链接 ABI / PIC·GOT·PLT / `PT_INTERP`·`AT_*`（→ `SPEC-139t`）；TLS/线程（`ADR-0025 D5` 先查证再定）；具体号值正文（→ §1.2 锁定来源）；内核语义本体（→ §6 首条）。[ADR-0025 D6][ADR-0025 D5]

## §7 裁定 / 锁定清单（原「待裁定」；#1–#3 已于 2026-10-14 裁定）

| # | 项 | 状态 | 归属 / 指针 |
|---|----|------|------------|
| 1 | errno 载体（`rd8` 负值 / `rd1` rderrno / 双写） | **已裁定**：A（`rd8` 负值）〔2026-10-14〕 | §4；`ADR-0025 D7` [ADR-0025 D7] |
| 2 | DADAO 是否另设 arch-specific 私有号 | **已裁定**：不另设，沿用 RISC-V arch-specific〔2026-10-14〕 | §1.3；`ADR-0025 D1` [ADR-0025 D1] |
| 3 | `AUDIT_ARCH_*` 取值端序位（`__AUDIT_ARCH_LE` vs 大端） | **已裁定**：`AUDIT_ARCH_DADAO` = `EM_DADAO`\|`AUDIT_ARCH_64BIT`（BE，64 位），不带 `__AUDIT_ARCH_LE`〔2026-10-14〕 | §1.3；`ADR-0003 D1` [ADR-0003 D1] |
| 4 | 号表快照对应的**上游内核版本** | **已锁定**：内核 `7.2.10`（身份 = git commit `7b20d05f…`；与快照 uapi 逐字节相同 / 号表 0 冲突，见 §1.2） | 本合约 §1.2；pin 承载 `INFRA-075t` [ADR-0025 D1] |

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
| §6 | QEMU user-mode 角色 / 边界；停机协议不混用；范围外 | `ADR-0025 D2`/`D6`；`ADR-0004 D3`；`ADR-0020 D8` |
