# ADR-0020: SEE/HEE 运行环境与 semihosting

**状态**：Accepted
**日期**：2026-10-07
**关联**：ADR-0004（测试机；本 ADR `D8` 取代其 `D3` 作为停机协议，`D15` 修订其核内地址空间划分口径）、ADR-0011（exit-port 可靠 halt）、ADR-0003（object ABI：大端 / ELF 头）、`INTEG-019k`（M5 规划）、`SPEC-113t`（本 ADR）、`SPEC-114t`（规范正文落点）、`QEMU-044t`/`045t`/`046t`/`047t`/`049t`、`LLVM-060t`、`TESTCASES-033t`/`034t`、`INTEG-020t`；`spec/DADAO-12`、`spec/DADAO-22-SBI-主管系统二进制接口.md`、`spec/SimRISC-11-其它.md`、`.tao/knowledge/contract-abi.md`

## Context（背景）

M1–M4 的 v5 工具链是**裸机、无 OS、无 syscall**：无 SEE（无四运行模式、无 cfx 寄存器/掩码/权限、无 `switch_run_mode`、无异常进入/退出流程），无 semihosting；停机协议依赖 **exit-port**（`ADR-0004 D3`，MMIO `0xffff_8000_0000`，8 B 只写）——这是 v5 自定、**非 spec 语义**。LLVM 不实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`（`spec/SimRISC-11-其它.md §其它`），4 条均在 `contracts/*` 中 `scope: excluded`，故任何依赖 cfx 的代码（含 bootrom/固件）都编不出、跑不了。

M5 要把 QEMU 从「裸机、无 syscall、exit-port 停机」升级为「**SEE/HEE 运行环境 + semihosting**」：自有工具链编 bootrom（LLVM 新指令首个真实用户）→ QEMU 启动 bootrom（初始权限/向量配置）→ guest 经 `trap`（semihosting tag）→ 复用 QEMU 共享层 `do_common_semihosting`（ARM 号值）→ `SYS_EXIT`/控制台输出**替代** exit-port。

本 ADR 命中 `spec/Process-03-ADR编写规范.md` 的 ADR 判据：**跨组件 / 需一致**（LLVM、QEMU、testcases、integ 多模块）、**有多方案且需记录取舍**（复用 vs 自建 responder；走向量 vs 译码短路）、**外部依赖 / 契约**（复用 QEMU 上游共享层）、**把结论固化为约束**（决策先行）。

**承载位置（`D13`）**：本 ADR **只记决策/理由/被否方案/指向规范章节的引用**；semihosting 服务号值↔入参/出参表、SEE/semihosting 调用约定、`switch_run_mode` 语义、`CFXMEM`/`NUPERM` 等异常语义的正文**入 `spec/`**（归 `SPEC-114t`；新建 `spec/Machine-01-测试机运行环境.md` 为正文落点）。ADR **不承载规范正文**（`spec/Process-03-ADR编写规范.md`「ADR 不承载规范正文」）。

**上游对照（只读、非执行依赖）**：QEMU 共享层 `semihosting/arm-compat-semi.c` 提供 `do_common_semihosting(cs)`（声明于 `include/semihosting/common-semi.h`）；target 钩子范式 `target/riscv/common-semi-target.c`；接入点 `target/riscv/tcg/insn_trans/trans_privileged.c.inc` 抛 `RISCV_EXCP_SEMIHOST` → `target/riscv/tcg/cpu_helper.c`：`do_common_semihosting(cs); env->pc += 4;`。v5 照搬此范式。

## Decision（决策）

- **D1**（入口判定）：`trap cfxHA, immu18` 中 **`immu18[17:16] == 2'b11`** ⇒ semihosting（**与 `cfxha` 无关**）。本 tag 属**架构自定义**——`spec/DADAO-22-SBI-主管系统二进制接口.md:7`（`trap cfxha, immu18`：`cfxha` 为服务提供者、`immu18` 为功能编号）与 `spec/SimRISC-11-其它.md:89`（`immu18` 功能编号）**均无 semihosting 语义**；其语义/理由说明落 `spec/Machine-01-*`（归 `SPEC-114t`），本 ADR 只留决策。

- **D2**（传参/返回寄存器）：号（标量）→ **`rd16`（=`rda0`）**；参数块指针（地址）→ **`rb16`**；返回值 → **`rd31`**（指针返回才用 `rb31`，semihosting 不用）。对齐共享层 `common_semi_arg(cs,0)` = 号、`common_semi_arg(cs,1)` = 参数块指针。**不另设 `rd15`**（`rd15` 是 umon/jmon 系统调用号）。依据 `.tao/knowledge/contract-abi.md §4.1`（`rd16–rd31` 数据参数、`rb16–rb31` 地址参数）、`§4.4`（`rd31` 标量返回、`rb31` 指针返回）、`spec/DADAO-22-SBI-主管系统二进制接口.md:13`（参数传递与 ABI 一致）。

- **D3**（号值 / 服务集）：号值采用 **ARM semihosting 号值**；**服务集 = 完整 25 个**（含文件档 `OPEN`/`CLOSE`/`READ`/`SEEK`/`FLEN`/`TMPNAM`/`REMOVE`/`RENAME`；`SYSTEM`、`HEAPINFO` 均做）。`SYSTEM`（执行宿主命令）为**已登记的已知安全风险**（见 Consequences），不因此拒服务。服务号值↔入参/出参的**权威表**属规范正文，落 `spec/`（`SPEC-114t`）。

- **D4**（返回机制）：**无 `escape` 指令**——semihosting 服务完成后由 QEMU 直接**前移 PC**（`env->pc += 4`）并写回返回寄存器（`D2`）；guest 侧不需 `escape` 返回。

- **D5**（复用范式）：**复用 QEMU 共享入口 `do_common_semihosting(cs)`**；DADAO 只提供 `common-semi-target.c` 式钩子；接入方式 = **trap 译码后抛 semihost 内部异常**（类比 RISC-V `RISCV_EXCP_SEMIHOST`）。**不自建 responder。**

- **D6**（位宽/端序）：由共享层 `is_64bit_semihosting()` 决定；v5 **恒 64 位**；参数块 = 64 位字段 + target 端序（v5 **大端**，同 `ADR-0003 D1`）。

- **D7**（host 侧安全）：`-semihosting-config` 的默认值由 harness/Makefile 提供；共享层 `auto` 语义 = **有 GDB ⇒ `gdb`、无 GDB ⇒ `native`**（首次调用判定并记忆）。**建议默认 `gdb`/沙箱**，`native` 需显式开启。

- **D8**（停机协议）：semihosting **`SYS_EXIT` 取代 exit-port**（`ADR-0004 D3`）作为停机协议；既有 M1–M4 依赖 exit-port 的向量/harness **迁移范围 = 全部**（实施归 `TESTCASES-034t`）。

- **D9**（QEMU 权限实现粒度）：**完整**——`cfx_⟨cfxname⟩_<mode>_global_cfx_mask` + 指令类型 mask（`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`/`trap`/`escape` 各自 cfx mask）+ `switch_run_mode`/`switch_cfx_mask` + 权限异常；**运行模式与 cfx 正交**（`spec/SimRISC-11-其它.md:80`：trap/escape/cfx2* 可在任意运行模式执行，是否允许由 cfx mask 与指令类型 cfx mask 控制）。**权限范围 = 只做 `cfx0/1/2/3/63`**（`umon`/`jmon`/`smon`/`hmon`/`power`，`spec/DADAO-12-SEE-主管系统运行环境.md §1`）；**访问未实现 cfx ⇒ `CFXREG` 异常**（出处 `spec/DADAO-22-SBI-主管系统二进制接口.md:58`）。
  - **依据归属（订正）**：`NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 出自 **`spec/DADAO-12 §2.2`（PTBR 权限检查，`:92`/`:133`）与 cfx_ptw 异常原因表（`:449`–`:452`）**，**非 `§5`**；`§5` 异常进入流程对未授权 cfx 触发的是 **`ILLI`**（`:684`、`:692`–`:693`）。二者层次不同（PTBR 权限 vs cfx 访问权限），语义详述落 `spec/`（`SPEC-114t`）。

- **D10**（流程两条路）：(a) **一般 `trap cfxHA, immu18`**（`immu18[17:16] ≠ 2'b11`）：先过权限，允许则**走 spec 异常进入流程**（`spec/DADAO-12 §5`，含步骤 10「跳转至异常向量」`:703`）——**进入该 cfx 的向量**；(b) **semihosting**（`immu18[17:16] == 2'b11`）：**QEMU 译码层短路**（与 `RISCV_EXCP_SEMIHOST` 同构）——**不进入向量**、直接服务并按 PC 步进返回（`D4`）。`switch_run_mode` 语义详述落 `spec/`（`SPEC-114t`）。

- **D11**（cfxha 白名单）：**不设** cfxha 白名单——是否允许调用由 cfx mask/权限控制（reserved cfxha `7–14`/`19–61` 按 spec 规则触发 `ILLI`，`spec/DADAO-12 §5:684`）。

- **D12**（新 bootrom）：M5 的 QEMU 提供**新 bootrom**（固件），用于**初始权限/向量配置**；bootrom 用**自有工具链**编译（LLVM 新指令首个真实用户）。加载模型：**用 `-bios`**、**复位向量不变**（`0xffff_ffff_0000`，`spec/DADAO-12 §2.1:68` = `cfx_power_hypv_excp_vector`，64 KiB）；bootrom **hypv → user 直跳、本版不启用 supv**（`smon` 不参与）。

- **D13**（承载位置）：测试机/SEE/semihosting 的**规范正文入 `spec/`**（`SPEC-114t`）；**ADR 只记决策/理由/被否方案/指向规范章节的引用**，不承载规范正文（`spec/Process-03-ADR编写规范.md`）。

- **D14**（共享层适配点）：共享层 `common_semi_arg(cs, n)` 假定「同一组 `a0 + n`」（RISC-V 实测 `target/riscv/common-semi-target.c`：`gpr[xA0 + argno]`），而 v5 三组（`rd`/`rb`/`rf`）**各自独立计数、从 16 起递增**（`.tao/knowledge/contract-abi.md §4.1`）⇒ DADAO 钩子**按 `n` 选 bank**（`n=0`→`rd16`、`n=1`→`rb16`）、`common_semi_set_ret`→`rd31`。属**小适配（非重写）**，仅写 `target/dadao/common-semi-target.c`。

- **D15**（核内地址空间划分 + 越界报异常）：M5 测试机使用的核内地址空间划分如下（均为 48 位核内有效地址；地址区间为**测试机约定**，`spec/` 只规定 `cfxha 63` 的复位向量）：

  | 区域 | 起始 | 大小 | cfxha / cfxname | 说明 |
  |------|------|------|-----------------|------|
  | **RAM@0（新）** | `0x0000_0000_0000` | 【待 `QEMU-049t` 定】 | 0 / `umon` | 供 bootrom/SEE（C1 step1 双映射引入） |
  | **旧 RAM 段（过渡保留）** | `0xffff_0000_0000` | 16 MiB | 63 / `power` | 供既有 M1–M4 测试（step2 迁移后删除） |
  | **exit port（过渡保留）** | `0xffff_8000_0000` | 8 B | 63 / `power` | 见 `ADR-0004 D3`（`D8` 后由 `SYS_EXIT` 取代） |
  | **boot ROM** | `0xffff_ffff_0000` | 64 KiB | 63 / `power` | 复位向量 = `cfx_power_hypv_excp_vector`；`-bios` 加载 |

  - **越界访问与越界取指均须报异常（含取指路径）**：访问或取指落入上述映射之外的核内地址 ⇒ 触发异常；**取指路径与数据访问路径同等对待**（不得只覆盖数据访问）。不得静默继续/静默丢弃。
  - **异常语义（spec 层 vs 测试机层）**：
    - **`CFXMEM`（spec 语义）**：核内地址空间/内部存储块**非法访问**，`spec/DADAO-12 §2.1:73`（及 `§3:385`）；异常原因表 `1 << 1`（`spec/DADAO-12` cfx_umon 异常原因表 `:406`）。
    - **测试机约定 `unmapped 0x87`**：`ADR-0004 D5.8` 的测试机约定退出码（**无 spec cause**，用于无 cfx 归属的 unmapped 访问）。
  - **层次与适用**：
    1. spec 层只定义**异常原因**（`CFXMEM = 1<<1`）；测试机退出码按 `ADR-0004 D5.8` 规则 **`0x80 | cause_bit`** 派生 ⇒ **`CFXMEM` ⇒ `0x81`（`0x80 | 1`）**。
    2. `CFXMEM`（`0x81`）适用于**核内地址空间模型内的非法访问/取指**（cfxha 段内的非法子区间、越界访问/取指）；`0x87`（unmapped）保留为**测试机历史约定**（`ADR-0004 D5.8`），用于既有 M1–M4 语义；C1 **step2** 迁移完成前两者并存。
    3. **码表冻结、不得重排**：`ADR-0004 D5.8` fault 码表**已冻结**；`CFXMEM`（`1<<1`）落在表中**已保留的 `0x81`–`0x86`**（对应 spec cause 位 1–6，M1 未用）区间内，**无需新码 / 无需重排**；若确需新码须另说明依据。
    4. 精确路由（哪一类越界取 `0x81`、哪一类取 `0x87`）与 RAM@0 容量，由 `QEMU-049t` 按上述层次落地并写 `check-interface` 断言。

## Rationale（理由）

- **复用 QEMU 共享层而非自建 responder（D5）**：共享层 `do_common_semihosting` 已实现完整 semihosting 语义（号值分发、文件/控制台/退出、参数块解析、host 侧安全）；照 RISC-V 范式只写 target 钩子即可，**最小改动、可复用、可随上游升级**。自建 responder 需自行定义取参/返回/推进 PC，风险与成本高。
- **采用 ARM 号值（D3）**：共享层与 ARM 兼容层一致，号值直接复用实测常量，避免自定义号值与分发层冲突；「DADAO 有就做」。
- **PC 步进而非 `escape`（D4）**：semihosting 走**译码短路**、不进入向量，因此不适用 `spec/DADAO-22:11` 的通用 `escape cfxha, [excp_cause_ip, 4]` 返回约定；直接前移 PC 与 RISC-V 同构，最简且确定。
- **ABI 传参寄存器（D2）**：`spec/DADAO-22:13` 明示参数传递「与 ABI 传参规范一致」；semihosting 复用 ABI 的 `rd16`（号）/`rb16`（参数块指针）/`rd31`（返回），与共享层 `common_semi_arg(cs,0/1)` 语义对齐。不另设 `rd15`（其属 umon/jmon 系统调用号）。
- **三组分离的 bank 适配（D14）**：v5 `rd`/`rb`/`rf` 各自独立计数，共享层「`a0+n` 同组」假设不成立；按 `n` 选 bank 是**局部小适配**，不破坏 ABI、不改共享层。
- **权限完整实现但 cfx 子集（D9）**：完整 mask/`switch_run_mode`/权限异常是 spec 的核心机制，须实现；首版范围限定 `cfx0/1/2/3/63` 控制成本，未实现 cfx 依 spec 触发 `CFXREG`。
- **两条路分离（D10）**：一般 trap 依 spec `§5` 进入 cfx 向量；semihosting 与向量无关，属实现层短路（`RISCV_EXCP_SEMIHOST` 同构）。两者混为一路会导致实现者误让 semihosting 进入向量。
- **bootrom 用自有工具链、`-bios` 加载（D12）**：bootrom 是 LLVM 新指令（`trap`/`escape`/`cfx2*`）的**首个真实用户**，同时验证工具链与机器模型；`-bios` + 复位向量不变可最小化对既有启动模型的影响。
- **`SYS_EXIT` 取代 exit-port（D8）**：exit-port 是 v5 自定、非 spec 语义；semihosting `SYS_EXIT` 是标准停机协议，且 `ADR-0011` 已保证 halt 确定性——迁移后可回归上游语义。
- **默认 `gdb`/沙箱（D7）**：CI 无 GDB 时 `auto` 会退化为 `native`，行为不确定且暴露 `SYSTEM` 宿主命令风险；显式默认 `gdb`/沙箱更安全。
- **D15 越界必须报异常（含取指）**：核内地址空间模型要求非法访问/取指**显式 fault**，而非静默；`CFXMEM` 是 spec 的对应 cause，测试机据 `0x80|cause_bit` 映射为 `0x81`，且落在已冻结码表的保留区间，无需新码。

### 被否方案

- **自建 responder**（`DADAO-0628` 的 `trap cfx_smon` + Linux syscall 号路线）：否决——改用共享层 `do_common_semihosting` + ARM 号值。
- **另设 `rd15` 作 semihosting 号寄存器**：否决——`rd15` 是 umon/jmon 系统调用号，semihosting 不用。
- **只做「必做档」服务集**（console/退出/错误/系统信息，不含文件档）：否决——服务集 = 完整 25 个。
- **`SYSTEM` 拒 `ENOSYS`**：否决——`SYSTEM` 都做，风险登记为已知风险。
- **用 `escape` 指令返回**：否决——semihosting 不进入向量，不适用。
- **所有 trap 统一走向量**（由向量内分发 semihosting）：否决——semihosting 走译码层短路。
- **硬编码 `cfxha` 白名单**：否决——是否允许由权限/mask 控制。
- **QEMU 内建 bootrom / 用 `-kernel` 加载 bootrom**：否决——用 `-bios`。
- **保留 exit-port 兼容并存**：否决——迁移范围 = 全部。
- **默认 `native`**（host 侧安全）：否决——建议默认 `gdb`/沙箱。
- **规范正文写入 ADR**：否决——正文归 `spec/`（`D13`）。

## Consequences（影响）

- **正面**：semihosting 复用上游、随上游升级而受益；`SYS_EXIT` 提供标准且确定的停机协议（`ADR-0011`）；M5 建立 SEE/HEE 运行环境与 cfx 权限机制；bootrom 验证自有工具链新指令。
- **负面 / 后续约束**：
  - **上游依赖**：复用共享层 API（`do_common_semihosting`、`common-semi-target.c` 钩子、`is_64bit_semihosting` 等）与 QEMU baseline 绑定；升级 QEMU baseline（`ADR-0002`/`ADR-0008`）时须复核其语义。
  - **`SYSTEM` 安全风险**：`SYSTEM`（执行宿主命令）为**已登记已知风险**；默认 `gdb`/沙箱（`D7`）为缓解手段，`native` 须显式开启。
  - **迁移成本**：exit-port → `SYS_EXIT` **范围 = 全部**（M1–M4 全部依赖 exit-port 的向量/harness 须迁移，`D8`），由 `TESTCASES-034t` 承接；`ISS-147`（exit 码与 fault 区重叠）随迁处置。
  - **`D1` tag 无 spec 依据**：`immu18[17:16]==2'b11` 属架构自定义，须在 `spec/Machine-01-*` 明示（`SPEC-114t`）。
  - **`D9` 权限语义层次**：PTBR 权限（`NUPERM/NJPERM/NSPERM/NHPERM`，`§2.2`）与 cfx 访问权限（`§5` 的 cfx mask → `ILLI`）为两个层次，须在 `SPEC-114t`/`QEMU-044t` 讲清。
  - **`D15` 双映射过渡**：`QEMU-049t`（step1，M5）= 机器模型同时映射 RAM@0 + 保留旧 RAM 段 + `check-interface` **新增** RAM@0 断言（旧断言保留）⇒ 每任务门控保持全绿；**step2**（旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧断言）= **另立、M5 之外**。
  - **下游约束**：`SPEC-114t`（正文：服务表 / 调用约定 / 权限 / `CFXMEM` 语义）、`LLVM-060t`（`trap`/`escape`/`cfx2rc`/`cfx2rd`）、`QEMU-044t`–`QEMU-047t`/`QEMU-049t`、`TESTCASES-033t`/`034t`、`INTEG-020t`（`make test-semihost`）均以本 ADR 的决策为前提。

## 状态说明

**Accepted（2026-10-07）**：`D1`–`D15` 已由用户于 **2026-10-07 逐条判定**（保留 / 修改 / 新增），**无否决未处置**，故由 `Candidate` 置 `Accepted`。

- **判定方式**：用户 2026-10-07 以**总述 + 后续两问回答**给出裁定（原话见 `.tao/tasks/spec/SPEC-113t-ADR决策落地.md` 完成区与 §四「用户逐条裁定结果」）。
- **本轮被特别指出的条目**：**`D1`**（决策保留；其语义说明移 `spec/Machine-01-*`，归 `SPEC-114t`）、**`D15`**（新增 decision）、以及 `ADR-0004` 的 `R1`/`R2`/`R3`。
- **推定保留 + 用户明确确认**：`D2`–`D14` 未在总述中特别指出，按主会话声明「**未特别指出者视为保留**」推定保留，并**经用户明确确认**；该推定为默认推定，若用户对某条另有意见，按 `spec/Process-03` 处置（新增 ADR / 标 `Superseded` / 经授权就地修订）。
- **决策变更**：**新增 ADR 或标注 `Superseded`**，不直接改写已 `Accepted` 的决策（`spec/Process-03`）。
