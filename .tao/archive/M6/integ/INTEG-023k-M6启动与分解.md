# INTEG-023k: M6 启动与分解（用户逐条裁定落纸 + 任务分解草案）
**模块**：integ　**项目里程碑**：M6　**状态**：已验证
**依赖**：`INTEG-021m`（M5 integ 里程碑，`里程碑`）、`INTEG-022t`（M5 归档，`已验证`）；无硬前置
> 用户 **2026-10-08 逐条裁定** M6 的 **20 项内涵 + 12 条 LLVM 欠账**（§A/§B）；本 `k` 只**落纸 + 出分解草案（§C/§D）**，**不建 `t`/`m`、不改 `spec/`**。长叙述见 `.work/log/integ/INTEG-023k-detail.md`。

## A. M6 内涵逐项裁定（#1–#20，**用户 2026-10-08 逐条裁定**）

| # | 内涵项 | 裁定 |
|---|---|---|
| 1 | 整数完整调用约定（变参/聚合/`sret`/多返回/间接调用） | **纳入**（M6 核心） |
| 2 | FP/RF codegen | **纳入**，**排整数之后** |
| 3 | `mem*`/内建/运行时 | M6 **不引 libc**：`mem*`/`str*` 自写最小实现 + 后端 **`MaxStoresPerMem*=16`**；真实程序留 M7；compiler-rt 与 libc 正交，取舍随 #2 软浮点 |
| 4 | LLVM 欠账收口 | **纳入**（逐条见 §B） |
| 5 | clang 前端 | **纳入**（= 钉子①，**只用于 freestanding**） |
| 6 | 最小 libc | **不纳入** |
| 7 | OS/syscall | **不纳入** |
| 8 | `REL12` | **纳入**（与 #9 合并为「`ld/st` 符号偏移 reloc 体系」；**须 ADR 逐条确认**） |
| 9 | `ISS-151` | **纳入**（**新增专用 reloc 类型，不复用 `REL20`**；**必须覆盖超出 `REL12` 的情形**） |
| 10 | `ISS-154` | **纳入**；`ABS48` 数据 8 字节字段表示 = **48 位地址、大端存储、高 16 位填 0** |
| 11 | `ADR-0019 D7` | **留后** |
| 12–14 | QEMU ELF 直载 | **改走 `load_elf()`**（取消自建 `dadao_load_regions[]` 白名单；多段 `PT_LOAD`/RELA/`e_entry`/栈由 `load_elf()` 提供 ⇒ 作**验证项**）；**`-bios`+ELF 组合不需要** |
| 15 | RAM@0 尺寸 | **维持 16 MiB** |
| 16 | `ISS-165` step2 | **纳入**（随 M6） |
| 17 | oracle | **采纳 `lli` 作值级 oracle**；构建 = **一次构建**（`LLVM_TARGETS_TO_BUILD="DADAO;X86"`，产出 `clang`/`llc`/`ld.lld`/`lli`）+ **两处落点**（交叉工具链 → `.dadao/cross-toolchain/bin/`；host `lli` → `.dadao/host-tools/bin/`〔可选〕），**随 M6 clang 构建一并做**；边界 = **只做值级**（端序/内存布局类排除）、**IR 需兼容**、**同源性质 = 证「IR 语义被保持」** |
| 18 | 上游 IR 素材 | **纳入**（编译/编码层 + 有 `lli` 时值级对拍；**不寄望其提供执行语义判据**） |
| 19 | lit 量产 | **纳入**（骨架 agent 生成 + 期望值**从 `spec`/`contracts` 机械派生**、**禁从 `llc`/QEMU 结果反填**；对拍类**运行期比对**；目标**数百**〔对齐 0628：lit 81 + 差分 200〕；分层 = **快档入 `make check`、全量档 opt-in**） |
| 20 | fuzz | **后置 M7** |

## B. LLVM 欠账 12 条裁定（#4 展开，**用户 2026-10-08 逐条裁定**）

- **逐条**：`ISS-043` 纳入 / `ISS-045` 纳入 / `ISS-047` 纳入 / `ISS-108` 纳入（**拆分文件**）/ **`ISS-110` 全留后** / `ISS-148` 纳入（**做法 = 消除硬编码计数**，非改数字）/ `ISS-151` 纳入（= #9）/ `ISS-156` 纳入 / `ISS-159` 纳入 / `ISS-161` 纳入（含 `REL12`；另修 `FK_Data_1/2/4` **静默出 0**）/ `ISS-162` 纳入。
- `ISS-138` 纳入：大帧寻址 = **四形态**（①`[sp,disp12]` ②`rb2rb`+`add.si` ③`add.o tmprb,sp,tmp`+`[tmprb,disp]` ④`ldm/stm [sp,tmp]`〔`immu6`=1 单次、>1 批量〕），**由编译器按代价（指令数 × 访存条数/复用次数）选择**；**须修订 `ADR-0018 C7 D4`**〔逐条确认〕。
- `ISS-156`：**用户已授权改 `spec/Toolchain-01 §6.1`**，口径 = `rd2rf rfx, rd0` + **仅非零 `wp` 的 `set.w`**（`set.fo rf,0` ⇒ 1 条）；**并同步该册 `sha256` 锁**。
> **用户新规范口径**：文档/注释/任务书/验收**不得硬编码计数**（需要时由脚本/门控现场统计，或写「不下降/逐项相等」；门控计数须**派生自单一真源**）。
## C. M6 任务分解草案（体例照 `INTEG-019k`；**只出编号/范围，不建文件**）

| 编号 | 任务 | 模块 | 范围（草案） | 依赖 |
|---|---|---|---|---|
| `INTEG-023k` | M6 启动与分解（本文件） | integ | 本 `k` + 分解草案 + `milestones.md` M6 定义（待 `/plan` 后） | 无 |
| `INFRA-050t` | LLVM 一次构建 + 双落点 | infra | `LLVM_TARGETS_TO_BUILD="DADAO;X86"` 产出 `clang`/`llc`/`ld.lld`/`lli`；落 `.dadao/cross-toolchain/bin/`（交叉）+ `.dadao/host-tools/bin/`（host `lli`，可选）；`Makefile`/`install-dirs` 同步 | 无 |
| `INFRA-051t` | Embench 组件接入 | infra | ADR 记录上游+commit ⇒ `manifests` 翻 `enabled=true`；建 `components/embench-iot/{patches,series,changelog}` 骨架 + `make fetch` 落 `.work/source/embench-iot` | `SPEC-122t` |
| `INFRA-052m` | M6 infra 里程碑 | infra | `m` 文件 | `INFRA-050t`/`051t` |
| `SPEC-122t` | ADR 决策落地（逐条用户确认） | spec | ①`ADR-0018 C7 D4` 修订（大帧四形态/代价驱动）②新 ADR「`ld/st` 符号偏移 reloc 体系」③Embench 上游选择 ADR ④组合加载语义 ADR（判断见 §D） | 无 |
| `SPEC-123t` | reloc 正文 + `Toolchain-01 §6.1` | spec | `contract-elf §2–§4`（`REL12`/新类型/`ABS48` 数据 8B 字段〔`ISS-154`〕）+ `spec/Toolchain-01 §6.1` 修订（`ISS-156`）+ 该册 `sha256` 锁同步 | `SPEC-122t` |
| `SPEC-124t` | 调用约定契约收口 | spec | `contract-abi §6` 3 项 `[OPEN]`（多返回值声明顺序/red zone/`i128`）消解 | `SPEC-122t` |
| `SPEC-125m` | M6 spec 里程碑 | spec | `m` 文件 | `SPEC-122t`~`124t` |
| `SPEC-126t` | 系统调用/半托管返回 `rd8` | spec | 系统调用（`DADAO-22`/`DADAO-23`/`DADAO-21 §系统调用规范`）与半托管（`Machine-01 §5`）服务返回寄存器 `rd31 → rd8` + `contract-see §5`/`contract-semihosting` 同步 + 锁同步；**逐条分类、不改 `rd15 = nr`**；**不含实现** | `SPEC-124t` |
| `SPEC-127t` | 聚合传参/HFA/HPA 约定收口 + HFA/HPA 槽位上限 8 | spec | `spec/DADAO-21 §传参 §聚合类型参数`（**HFA/HPA 槽位上限 `4→8`〔64 B〕**）+ 锁同步 + `contract-abi.md`（HFA/HPA/聚合传参 由 `Excluded from M3` 升 **M6 口径**）+ `contracts/abi.yaml` 派生投影；**通用聚合 4 vs 8 待用户裁定、本轮不改**；**不含实现**（整数聚合→`LLVM-062t`、HFA/RF→`LLVM-066t`） | `SPEC-124t`、`SPEC-126t` |
| `SPEC-128t` | ABI 寄存器布局重排（spec/契约侧） | spec | **RD**：`rd2–rd3` reserved（调试/测试保留）、`rd4–rd7` temporary（caller-saved）；**RB**：`rb2`=GP、`rb3`=TP、`rb4–rb7` temporary、`rb32–rb62` callee saved、**`rb63`=FP 条件占用（callee-saved）**；**RF 不改册**（实现侧放开归 `LLVM-066t`）。改 `spec/DADAO-21 §寄存器规范` + 锁 + `contract-abi §1.2/§1.3/§1.6`（+ §2.1/§3/§4.5/§4.7 最小同步）+ `contracts/abi.yaml`；**就地修订 `ADR-0018 C7 D6`**（`rb2` 始终保留 → `rb63` 条件保留；**不立新 ADR**）；**不含实现** | `SPEC-127t` |
| `SPEC-129t` | `Toolchain-01` 旧口径消除 + §11/§12 移位（`ISS-163` 收口） | spec | 改 `§5`/`§11`/`§13` 三处旧口径（`crrr`/`ciii`→`m1`、仅 `crii` 仍 `excluded`）+ **消除写死**（计数指向 `contracts/opcodes.yaml`/生成投影 `contract-asm-list.md`）+ **§11→既有投影** `contract-asm.md §11`、**§12→既有门控说明**（门控名）+ `ADR-0013` **只加指向** + 只读册 `Toolchain-01` 锁 `sha256` 同步；**不改实现** | `SPEC-128t` |
| `LLVM-062t` | 整数完整调用约定 + 小欠账 | llvm | 变参/聚合/`sret`/多返回/间接调用（`ISS-005/006`）+ `ISS-043/045/047/148/159/162`；**`ISS-110` 留后** | `INFRA-050t`、`SPEC-124t` |
| `LLVM-063t` | DADAO clang target（钉子①） | llvm | `TargetInfo`/DataLayout/ABI/driver/sysroot；**只用于 freestanding**；模板 = RISC-V64 形状 + PPC64BE 端序/DL + AArch64 CC | `INFRA-050t`、`SPEC-124t`、`LLVM-068t` |
| `LLVM-064t` | 大帧寻址 + `mem*` 内建 | llvm | `ISS-138` 四形态（按代价选择；落 `ADR-0018 C7 D4` 修订）+ `mem*` 内建 + 后端 `MaxStoresPerMem*=16` | `LLVM-062t`、`SPEC-122t` |
| `LLVM-065t` | lld reloc 完善 | llvm | `REL12` + 新专用类型（`ISS-151/161`）+ `FK_Data_1/2/4` 静默出 0；`ISS-108` 拆分文件 | `SPEC-123t`、`INFRA-050t` |
| `LLVM-066t` | FP/RF codegen | llvm | FP/RF（**排整数之后**；`ISS-081/126/078`；含 compiler-rt 软浮点取舍随 #2） | `LLVM-062t`、`SPEC-122t` |
| `LLVM-067m` | M6 llvm 里程碑 | llvm | `m` 文件 | `LLVM-062t`~`066t`、`LLVM-068t` |
| `LLVM-068t` | ABI 寄存器布局重排（后端实现） | llvm | 寄存器类（`rd4–rd7`/`rb4–rb7` caller-saved）+ `getReservedRegs`（`rd2–rd3`、`rb2`=GP、`rb3`=TP 保留；**`rb63` 条件保留**）+ `getFrameRegister = hasFP ? rb63 : rb1` + `FrameLowering`（FP=`rb63`、批量保存排除 FP）+ **`LLVM-062t` RegMask 同步** + lit/CodeGen 期望；**重建**（`setsid` 脱离）；**不改 `spec/`/`contracts/`** | `SPEC-128t`、`LLVM-062t`、`INFRA-050t`；**排 `LLVM-063t` 之前**；与 `LLVM-064t` **串行** |
| `QEMU-052t` | 改走 `load_elf()`（钉子②） | qemu | 复用 `hw/core/loader.c`；**取消**自建 `dadao_load_regions[]` 白名单；多段 `PT_LOAD`/RELA/`e_entry`/栈初始化作**验证项** | 无（M5 已验证态） |
| `QEMU-053t` | RAM@0 step2（`ISS-165`）+ `ISS-169` | qemu | 旧向量/harness/`crt0`/e2e 迁 `0` + 删旧 RAM 段（`0xffff_0000_0000`）+ 收紧 `check-interface` 断言；**另含 `ISS-169`**（6 个 M1/M2 手写探针退出通道改写为 `SYS_EXIT`，含按新字长重算分支偏移） | `QEMU-052t`、`TESTCASES-034t`（已验） |
| `QEMU-054m` | M6 qemu 里程碑 | qemu | `m` 文件 | `QEMU-052t/053t` |
| `QEMU-055t` | 半托管返回 `rd8` | qemu | `common-semi-target.c.patch` `DADAO_SEMI_RET_REG 31 → 8` + `tools/qemu/min_rom_probe_046t.py` 等服务返回期望值重派生重验 | `SPEC-126t` |
| `TESTCASES-036t` | 新能力向量（L1+L3） | testcases | 调用约定/reloc/大帧/FP-RF 的 L1 编码 + L3 执行向量；**独立 oracle**（禁从 LLVM/QEMU 反填） | `LLVM-062t`~`066t`、`QEMU-052t` |
| `TESTCASES-037t` | lit 量产 | testcases | 骨架 agent 生成 + 期望值**从 `spec`/`contracts` 机械派生**（禁反填）；目标数百；分层：**快档入 `make check`、全量档 opt-in** | `LLVM-062t`、`QEMU-052t` |
| `TESTCASES-038t` | 上游 IR + `lli` 值级对拍 | testcases | 上游 `.ll` 当输入（编译/编码层）+ 有 `lli` 时值级对拍（证「IR 语义被保持」）；**不作执行语义判据** | `LLVM-063t`、`INFRA-050t` |
| `TESTCASES-039t` | Embench 接入（钉子③） | testcases | board shim 3 函数（`initialise_board`/`start_trigger`/`stop_trigger`）+ 最小运行时（`mem*/str*/ctype/sqrt`）+ `md5sum` 大端适配；**首验收 = 最小基准 QEMU 正确退出码** | `INFRA-051t`、`LLVM-062t/063t`、`QEMU-052t` |
| `TESTCASES-040m` | M6 testcases 里程碑 | testcases | `m` 文件 | `TESTCASES-036t`~`039t` |
| `TESTCASES-041t` | 返回 `rd8` 向量收口 | testcases | `tests/**` 受影响向量/期望值重派生重验——**域A 函数返回**（`SPEC-124t`）/ **域B 半托管返回**（`SPEC-126t`），**分别验收** | `SPEC-124t`、`SPEC-126t` |
| `INTEG-025t` | E2E + `make test-m6` 门控收口 | integ | 驱动 `lli` 对拍/Embench/lit 全量档；新 target `test-m6`（**opt-in，不进 `make check`**）；`check` 收口 | `TESTCASES-036t`~`039t`、`LLVM-065t`、`QEMU-053t` |
| `INTEG-026m` | M6 integ 里程碑（整体收敛） | integ | `m` 文件 | `INTEG-025t` |

> **追加（2026-10-09，用户裁定「**统一为 `rd8`**」）**：新增 **3 份 `t`** —— `SPEC-126t`（系统调用/半托管返回寄存器 `rd31 → rd8`，spec+contracts+锁）、`QEMU-055t`（半托管返回 `rd8` 实现 + 探针重派生）、`TESTCASES-041t`（向量/期望值重派生，域A 函数返回/域B 半托管返回**分别验收**）；**不立 ADR**。M6 任务书总数由 17 `t` + 6 `m` 增为 **20 `t` + 6 `m` = 26 份**。§D 各 Wave 已同步（`SPEC-126t` 入 Wave 1、`QEMU-055t` 入 Wave 3、`TESTCASES-041t` 入 Wave 4）。

> **追加（2026-10-09，用户裁定「**hfa/hpa也调整为：最多消耗 8个寄存器槽位（64字节）**」）**：新增 **1 份 `t`** —— `SPEC-127t`（聚合传参/HFA/HPA 约定收口 + HFA/HPA 槽位上限 `4→8`〔64 B〕；`spec/DADAO-21 §传参 §聚合类型参数` + 锁同步 + `contract-abi.md`/`contracts/abi.yaml` 升 M6 口径）；**通用聚合 4 vs 8 待用户裁定**、本轮不改；**不含实现**（整数聚合→`LLVM-062t`、HFA/RF→`LLVM-066t`）；**不立 ADR**。M6 任务书总数由 20 `t` + 6 `m` 增为 **21 `t` + 6 `m` = 27 份**。§D Wave 1 已同步（`SPEC-127t` 串于 `SPEC-126t` 之后）。

> **追加（2026-10-09，用户裁定「**M6 ABI 寄存器布局重排**；**不立 ADR**；**放 M6、排 clang target 之前**」）**：新增 **2 份 `t`** —— `SPEC-128t`（ABI 寄存器布局重排 spec/契约侧：RD `rd2–rd3` reserved〔调试/测试保留〕/`rd4–rd7` caller-saved；RB `rb2`=GP/`rb3`=TP/`rb4–rb7` caller-saved/`rb32–rb62` callee saved/`rb63`=FP 条件占用〔callee-saved〕；RF 不改册；就地修订 `ADR-0018 C7 D6`；**不含实现**）+ `LLVM-068t`（后端实现：寄存器类/`getReservedRegs`〔`rb63` 条件保留〕/`getFrameRegister = hasFP ? rb63 : rb1`/`FrameLowering`〔FP=`rb63`、批量保存排除 FP〕/`LLVM-062t` RegMask 同步/lit 期望；**重建**）；**连带** `LLVM-066t` 追加「RF 实现侧放开（`rf1–rf7` caller-saved；`rf0`=FCSR 保留）」。依赖/串行：**`SPEC-128t` → `LLVM-068t` → `LLVM-063t`**；`LLVM-068t` 与 `LLVM-064t` **串行**。§C 表已加两行、§D Wave 1/2 已同步；`LLVM-063t`/`LLVM-067m` 依赖已加 `LLVM-068t`。

> **追加（2026-10-09，用户裁定「**消除写死**」+「**台账 + 门控清单，ADR 只指向（推荐）**」）**：新增 **1 份 `t`** —— `SPEC-129t`（`Toolchain-01` 旧口径消除 + §11/§12 移位：改 `§5`/`§11`/`§13` 三处旧口径〔`crrr`/`ciii`→`m1`、仅 `crii` 仍 `excluded`〕+ **消除写死**〔计数指向 `contracts/opcodes.yaml`/生成投影 `contract-asm-list.md`〕+ **§11→既有投影** `contract-asm.md §11`、**§12→既有门控说明**〔门控名〕+ `ADR-0013` **只加指向** + 只读册 `Toolchain-01` 锁 `sha256` 同步；**不改实现**）。`ISS-163` 据此收口；`ISS-167` **挂账**（用户裁定「现在和异常退出流程没有关系，需要的时候，提出问题，我来判定」，**本任务不处理**）。§C 表已加该行、§D Wave 1 已同步（`SPEC-129t` 串于 `SPEC-128t` 之后）。**不立 ADR**（`ADR-0013` 只加指向）。

> **追加（2026-10-09，`QEMU-053t` 复验发现缺陷）**：新增 **1 份 `t`** —— `INFRA-053t`（修 `install-host` 幂等性：`ISS-172`——`cp` 间歇 `File exists`、`make test-elf`/`test-semihost` 首跑 `rc=2`/重跑 `rc=0`、`test-codegen` 通过；目标 = **连续两次 `make install-host` 与 `make test-semihost` 均 `rc=0`**，含证据脚本 + 注入自检）。**属修类型小任务**，与 `QEMU-053t` **无共享文件**（仅 `Makefile`）⇒ **不阻断**其落地；**入 Wave 0**（`INFRA-050t` → `051t` → `053t`，同改 `Makefile` ⇒ 串行）。`milestones.md` 已同步（新增 `INFRA-053t` 行）。

> **追加（2026-10-09，用户裁定「域 B 并入 `QEMU-055t`」）**：半托管服务返回 `rd31 → rd8` 的**向量侧**（`tests/llvm/codegen/m5/**`）由 `QEMU-055t` **随实现同批收口**（实现与向量耦合，拆分落地即红门控）；`TESTCASES-041t` **收窄为域 A（函数返回）+ 其余**。

> **追加（2026-10-10，`TESTCASES-039t` 停工登记 ⇒ 立 2 修复任务；主会话 2026-10-10 已独立复核）**：`TESTCASES-039t`（Embench）engineer **诚实停工**（判据未降级 = 退出码 0）——交付工具链**无一基准可编译**。两条真缺口各立一 `t`：
> - **`LLVM-069t`**（llvm；**入 Wave 2**〔llvm 串行〕）：**整数 `setcc` / `select_cc` lowering**——DADAO 后端仅设 `ISD::BR_CC`/`BRCOND=Custom`，无整数 `SETCC`/`SELECT_CC` action/模式 ⇒ 比较取值即 ISel 崩溃（`Cannot select: ... setcc`）。范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`；依赖 `INFRA-050t`/`LLVM-062t`/`LLVM-066t`/`LLVM-063t`（均已 `已验证`）。查 `ISS-173`。
> - **`INFRA-054t`**（infra；**入 Wave 0/infra**〔同改 `Makefile` ⇒ 串行〕）：**clang 内置头（resource-dir）安装**——`clang -print-resource-dir` 指向的 `lib/clang/<ver>/include` 未随 `install-host` 安装 ⇒ `#include <stddef.h>` `file not found`。范围 `Makefile`/`tools/infra/**`；依赖 `INFRA-050t`。查 `ISS-174`。
> - **`TESTCASES-039t` 依赖改为 = 原依赖 + `LLVM-069t` + `INFRA-054t`**（二者就绪后**重新下发**）；本 `k` 表 §C 中该行原文保留（历史原文），依赖扩充以本追加为准。M6 任务书总数由 21 `t` + 6 `m` 增为 **23 `t` + 6 `m` = 29 份**。

> **追加（2026-10-10，`TESTCASES-039t` 首验收达标后暴露 6 类后端缺口 ⇒ 立 5 修复/补能力任务；主会话 2026-10-10 已独立复核 reviewer Accepted）**：`TESTCASES-039t` 首验收**已达标**（`-O0` 10/19 基准退出码 0），但编译矩阵暴露 **6 类 DADAO 后端缺口**（逐条见 `issues.yaml` `ISS-175`–`ISS-180`；证据 `.work/log/testcases/TESTCASES-039t-stage1-gaps.md`），**M6「完整编译正确性」目标尚未达成**。据此立 **5 份 LLVM `t`**（均入 **Wave 2/llvm 串行**，同改 `components/llvm-project/patches` ⇒ 串行；依赖 `INFRA-050t`/`INFRA-051t`/`LLVM-062t`/`063t`/`069t`/`QEMU-052t`，均已就绪）：
> - **`LLVM-070t`**（= **G6**，`ISS-180`；**缺陷·静默错码，优先执行**）：`-O2` 运行期误编译致死循环（huffbench/matmult-int/nettle-sha256/statemate；`-O0`/`-O1` 正常）；**先诊断根因再修**；E2E = 4 基准 `-O2` 退出码 0。
> - **`LLVM-071t`**（= **G1 + G5**，`ISS-175` + `ISS-179`）：12 位立即数/分支范围溢出（大常量比较**常量物化** + 分支目标**放宽**；同属「12 位字段溢出」类）。
> - **`LLVM-072t`**（= **G3**，`ISS-177`）：跳转表 `br_jt` lowering（`-O0` 即触发；picojpeg/qrduino）。
> - **`LLVM-073t`**（= **G2**，`ISS-176`）：128 位乘高半 `umul_lohi`/`mulhu`（aha-mont64/wikisort）。
> - **`LLVM-074t`**（= **G4**，`ISS-178`）：尾调用 `LowerCall` 断言（仅 `-O2`；crc32/md5sum/tarfind/ud/xgboost）。
> 性质区分：**G6 = 缺陷（编译成功但运行期静默错码）**；**G1–G5 = 缺能力（均显式失败，非静默）**。M6 任务书总数由 23 `t` + 6 `m` 增为 **28 `t` + 6 `m` = 34 份**。`milestones.md` 已同步（新增 5 行 + M6 范围注记）。

> **追加（2026-10-10，`LLVM-074t` 收尾 + 用户裁定 4 缺口全入 M6 ⇒ 立 5 份 `t`）**：`LLVM-074t` reviewer 判 **Accepted**（**真尾跳**：`tailjmp` 与 `jump` 同编码 `0x70`/`0x71`、`PCRel_24`；非法形态优雅降级〔varargs/byval/sret ⇒ `call`+`ret`〕、`musttail` 显式失败；`check-lit` 83/83）。`LLVM-074t` 遗留**两个新缺口**（`ISS-182`/`ISS-185`/`ISS-186`）与**待裁决项 `ISS-181`** 一并齐备。用户 **2026-10-10 裁定：`ISS-182`/`ISS-185`/`ISS-186`/`ISS-181` 四缺口全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）⇒ 立 **5 份 `t`**（`LLVM-075t`~`078t` 入 **Wave 2/llvm 串行**〔同改 `components/llvm-project/patches` ⇒ 串行〕；`SPEC-130t` 入 **Wave 1/spec 串行**）：
> - **`LLVM-075t`**（= **`ISS-182`**，**缺陷，优先**）：`.p2align`（可执行段）使 `llvm-mc` **abort**（`MCAssembler.cpp:588`）；可疑根因 `DADAOAsmBackend::writeNopData`；验收 `.text` 内 `.p2align 1..4` **字节数正确** + `.rodata` 不回归 + E2E。
> - **`LLVM-076t`**（= **`ISS-185`**）：**有符号乘高半 `MULHS`/`SMUL_LOHI`**（照 `LLVM-073t` 套路，用 ISA `mul.so`；含负数/边界 **host 大整数 oracle**；断言须能区分半字序〔`lessons §8.46`〕）。
> - **`LLVM-077t`**（= **`ISS-186`**）：`-O2` `Cannot select: … load<…, zext from i1>`（**先诊断根因**再修；`aha-mont64 -O2`）。
> - **`SPEC-130t`**（= **`ISS-181`** 拆分-①，spec）：数据指示符口径**正文**（`spec/Toolchain-01 §7` + `.tao/knowledge/contract-asm.md`）+ **锁 `sha256` 同步**（**用户授权改只读册**；**不立 ADR**；**不动上游 `DADAO-11`**）。
> - **`LLVM-078t`**（= **`ISS-181`** 拆分-②，llvm）：**工具链生成侧**（`llc` 只发 `.dd.*`）+ **受理侧评估**（`llvm-mc` 拒 GAS 名；**确不可行 ⇒ 退回「只禁生成侧」并登记**）+ 删 `.align` 只留 `.p2align` + **用例跟改**（`tests/**` lit/e2e/scripts + `DADAOMCAsmInfo` directive 串）；**依赖 `SPEC-130t`**。
> **拆分说明**：`ISS-181` 跨 spec（只读册正文 + 锁）与 llvm（生成/受理 + 用例），体量大且须 **Spec-first** ⇒ 拆 `SPEC-130t` + `LLVM-078t`（后者依赖前者）。M6 任务书总数由 28 `t` + 6 `m` 增为 **33 `t` + 6 `m` = 39 份**。`milestones.md` 已同步（新增 5 行）。

## D. Wave/串行链 · 前置 ADR · 说明

- **Wave 0（infra；同改 `Makefile`/`manifests` ⇒ 串行）**：`INFRA-050t` → `INFRA-051t` → `INFRA-053t`（`ISS-172` `install-host` 幂等性修复；同改 `Makefile` ⇒ 串行）。
- **Wave 1（spec 决策先行；同改 `spec/`/锁 ⇒ 串行）**：`SPEC-122t` → `SPEC-123t`／`SPEC-124t` → `SPEC-126t` → `SPEC-127t` → `SPEC-128t` → `SPEC-129t`。**ADR 未 `Accepted` 前不进实现**（`Process-03`）。
- **Wave 2（llvm；同改 `components/llvm-project/patches` ⇒ 串行）**：`LLVM-062t` → `LLVM-068t`（ABI 寄存器重排）→ `063t` → `064t` → `065t` → `066t`（FP 最后）。**`LLVM-068t` 与 `LLVM-064t` 串行**（同改 `DADAOFrameLowering`，且 `064t` 大帧四形态含 `ldm/stm` 批量保存）；**`LLVM-068t` 排 `063t` 之前**。
- **Wave 3（qemu；同改 `components/qemu/patches` ⇒ 串行）**：`QEMU-052t` → `QEMU-053t` → `QEMU-055t`。
- **Wave 4（testcases）**：`TESTCASES-036t`／`037t`／`038t`／`039t`／`041t`；**Wave 5（integ）**：`INTEG-025t` → `INTEG-026m`。
- **前置 ADR 清单（逐条待用户确认，勿预标 `Accepted`）**：① `ADR-0018 C7 D4` 修订（大帧四形态/代价驱动）；② 新 ADR「`ld/st` 符号偏移 reloc 体系」（`REL12` + 新专用类型）；③ Embench 上游选择 + commit；④ 组合加载语义——**判断：不再需要独立 ADR**（已被「改走 `load_elf()`」取代，自建 loader/组合路径**取消**；仅在 `SPEC-122t` 落「不立 + 理由」）；⑤ 判断无需其它（`ADR-0019 D7` 记为**留后**、不启用）。
- **`k↔m`**：本 `k` 对应 M6；各模块 `m` 就近核验，M6 由主会话在模块 `m` 均 `里程碑` 后置 `达成`（`Process-04 §1`）。
- **说明**：本 `k` 为规划/分解；**`/plan` 通过后已建 17 `t` + 6 `m` = 23 份任务书**（见 §C，落 `.tao/tasks/<module>/`；编号按各模块 M5 归档后最大号顺延，QEMU 因跨模块重号消除再顺延，见 §E）；另有 `INTEG-024t`（台账搬迁，M6，**并行且互不占号**）。

## E. `/plan` 4 项修正落实（architect，2026-10-08）

> 依 reviewer 交叉审查（判决：**通过**）的 4 项非阻塞建议，**建 `t`/`m` 任务书时一并修正**：

1. **消除跨模块重号**：**实测**各模块 M5 归档后最大号 = `INFRA-049`/`SPEC-121`/`LLVM-061`/`QEMU-049`/`TESTCASES-035`/`INTEG-022` ⇒ 自然顺延下 `INFRA` 与 `QEMU` 均落到 `050t/051t/052m`，**跨模块重号**。处置：`INFRA` 保持 `050t/051t + 052m`；**`QEMU` 顺延两位为 `QEMU-052t/053t/054m`**（使 M6 二十余份任务书的**完整编号**〔含前缀〕全局唯一；跨模块引用一律显式带模块前缀）。§C/§D 已同步；reviewer 审查记录中出现的 `QEMU-050t/051t/052m` 为**审查时点的旧草案编号**，属历史原文、保留不改。
2. **`ISS-003`（LR-SC 原子）**：**M6 排除**（显式声明）。理由：`ISS-003` 余项 = `SimRISC-12` 的 `lr_*`/`sc_*`（ISA 扩展，现 `scope: excluded`/decode ILLI），**与 M6 主题**（整数完整调用约定 / 12 条 LLVM 欠账收口 / ELF 加载）**无关**，且 `SimRISC-12` 整体 deferred ⇒ **M6 不引入新 ISA**；其 scope 待后续（ISA 扩展）里程碑重定。已同步 `.tao/knowledge/issues.yaml`（`ISS-003` notes **仅追加**说明，**id 不变**）。
3. **`ISS-169`（6 探针保留 exit-port）**：归 **`QEMU-053t`**（RAM@0 step2）范围——step2 本涉旧向量/探针迁移，一并把 6 个 M1/M2 手写探针（`006t/008t/009t/010t/012t/013t`）的退出通道改写为 `SYS_EXIT`（**含按新字长重算手算分支偏移**）。
4. **「计数不写死」**：作为**硬约束**写入**全部** M6 任务书（尤其 `TESTCASES-*`/`SPEC-*`/`LLVM-*`）——文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。

## 审阅记录

#### 第 1 轮 architect 口径更正（2026-10-08）
- 「三根钉子」= M6 前三项具体交付（clang target〔#5〕/ QEMU `load_elf()`〔#12–14〕/ Embench 接入〔`TESTCASES-039t`〕）；原文误读为「先钉死三项」已更正（详见 git 历史与 `.work/log/integ/`）。

#### 第 2 轮 architect 裁定落纸（2026-10-08）
- 用户对 **20 项内涵（§A）+ 12 条 LLVM 欠账（§B）逐条裁定**已落纸；M6 分解草案落 **§C/§D**。**待 `/plan` 交叉审查**，通过后再建 `t`/`m` 任务书。

#### 第 1 轮 reviewer 交叉审查（2026-10-08）

**审查范围**：§A（20 项内涵裁定）、§B（12 条 LLVM 欠账裁定）、§C（任务分解草案）、§D（Wave/串行链/ADR 前置）。核验依据 = `issues.yaml` 实查 + `adr-0018`/`adr-0019` + 归档任务编号 + `AGENTS.md` 规则。

##### 1. 裁定落纸完整性

**§A 20 项内涵**：逐条核对 §A 表与 detail 文件 §D.1 表，20 项裁定**全部落纸**且与 detail §D.1 建议一致。重点核：
- **#3 不引 libc**：§A L12 明确「M6 **不引 libc**」+ `MaxStoresPerMem*=16` → 归 `LLVM-064t`（§C L48）✓
- **#8/#9 reloc**：§A L17-18 明确「新增专用 reloc 类型，不复用 REL20」「须 ADR」→ 归 `SPEC-122t`（ADR）+ `SPEC-123t`（正文）+ `LLVM-065t`（实现）✓
- **#10 ABS48 数据 8B**：§A L19 明确「48 位地址、大端存储、高 16 位填 0」，与 `ADR-0019 D2`（L26：`3×immu16 或 8 字节数据字段`）一致 ✓
- **#12–14 load_elf()**：§A L21 明确「改走 load_elf()」「取消自建白名单」→ 归 `QEMU-050t` ✓
- **#15 维持 16 MiB**：§A L22 明确 ✓（但见下文 §6 风险 #1）
- **#17 lli oracle**：§A L24 明确「一次构建 DADAO;X86 + 两处落点」→ 归 `INFRA-050t` ✓
- **#19 期望值禁反填**：§A L26 明确「禁从 llc/QEMU 结果反填」→ 归 `TESTCASES-037t` ✓

**§B 12 条 LLVM 欠账**：逐条核对 `issues.yaml` 实查（行号附后），**全部12条落纸**且与台账一致：
| ISS | issues.yaml 行 | status | §B 裁定 | 一致？ |
|---|---|---|---|---|
| ISS-043 | L140 | open | 纳入 | ✓ |
| ISS-045 | L147 | open | 纳入 | ✓ |
| ISS-047 | L154 | open [llvm,M5] | 纳入 | ✓ |
| ISS-108 | L243 | open | 纳入（拆分文件） | ✓ |
| ISS-110 | L251 | open [llvm,M6] | 全留后 | ✓（notes 确认「scope M5→M6」，§B 裁定为留后 = 不实现但跟踪） |
| ISS-138 | L291 | open | 纳入（四形态） | ✓ |
| ISS-148 | L299 | open | 纳入（消除硬编码计数） | ✓ |
| ISS-151 | L323 | open | 纳入 | ✓ |
| ISS-156 | L339 | open [llvm,spec] | 纳入 | ✓ |
| ISS-159 | L347 | open | 纳入 | ✓ |
| ISS-161 | L315 | open | 纳入（含 REL12 + FK_Data_1/2/4） | ✓ |
| ISS-162 | L355 | open | 纳入 | ✓ |

**结论**：裁定落纸完整性 **通过**。

##### 2. 内部一致性

**① 跨模块重号**：`INFRA-050t`（§C L40）与 `QEMU-050t`（§C L52）编号均为 `050`。任务书§D（L72）说明「编号按各模块现有最大号 +1」——归档实查确认 INFRA 最大=049、QEMU 最大=049，两模块独立递增确实都会到050。**风险**：跨模块引用时（如「050t 已完成」）易混淆；§C L54 `QEMU-052m` 依赖写 `QEMU-050t/051t` 即可能被误读为 INFRA-050t。**建议**：QEMU 模块从052起编（052t/053t/054m），或在所有跨模块引用处显式加模块前缀。**非阻塞**，但建议修订。

**② M5 归档后现状一致**：`INTEG-022t` 已归档（`.tao/archive/M5/integ/INTEG-022t-M5归档与回顾.md` 存在）、`INTEG-024t` 存在（`.tao/tasks/integ/INTEG-024t-issues台账搬迁.md`）、`milestones.md` L6 已标 M6 ✓。§C/§D 编号顺延与归档一致 ✓。

**③ 与 AGENTS.md 规则一致**：
- 「并行任务上限 ≤8」：Wave 0–4 最多同时有 `INFRA-050t` + `SPEC-122t` + `QEMU-050t` = 3 个并行，未超限 ✓
- 「同改共享文件串行」：§D 正确声明 `Makefile/manifests`（Wave 0 串行）、`spec/`（Wave 1 串行）、`components/llvm-project/patches`（Wave 2 串行）、`components/qemu/patches`（Wave 3 串行）✓
- 「模块里程碑与跨模块交互」：各 `m` 文件依赖对应 `t` 全部完成 ✓

**结论**：内部一致性 **通过**（跨模块重号为非阻塞建议）。

##### 3. 依赖与串行

**Wave DAG 无环验证**：
```
INFRA-050t ──┬──→ INFRA-051t ──→ TESTCASES-039t ──→ INTEG-025t → INTEG-026m
              │
SPEC-122t ──┬──→ SPEC-123t ──→ LLVM-065t ──→ INTEG-025t
             ├──→ SPEC-124t ──→ LLVM-062t ──┬──→ LLVM-064t ──→ TESTCASES-036t
             │                              ├──→ LLVM-066t ──→ TESTCASES-036t
             │                              └──→ TESTCASES-037t/039t
             └──→ LLVM-063t ──┬──→ TESTCASES-038t
                              └──→ TESTCASES-039t
QEMU-050t ──→ QEMU-051t ──→ INTEG-025t
             └──→ TESTCASES-036t/037t/039t
```
**无环** ✓。关键路径 = `SPEC-122t` → `SPEC-124t` → `LLVM-062t` → `LLVM-064t`/`066t` → `TESTCASES-036t` → `INTEG-025t`。

**共享文件声明串行**：§D 各 Wave 正确声明 ✓。

**QEMU-050t 与 INFRA-050t 同 Wave 是否真无关**：INFRA-050t 改 `Makefile`/`install-dirs`；QEMU-050t 改 `components/qemu/patches`。**无共享文件**，可并行 ✓。

**结论**：依赖与串行 **通过**。

##### 4. ADR 前置

**① ADR 只作提案**：§D L70「前置 ADR 清单（逐条待用户确认，勿预标 Accepted）」✓。`SPEC-122t` 范围（§C L42）列4项 ADR 决策，均为提案 ✓。

**② 组合加载 ADR 不必立**：§D L70 判断「已被改走 load_elf() 取代」。`ISS-168` notes（issues.yaml L401）原定义的3项中①组合加载/②ELF loader 扩展被 `load_elf()` 取代（复用 QEMU 上游 `hw/core/loader.c`）⇒ 无新加载模型需固化 ✓。**成立**。

**③ 是否遗漏必需 ADR**：`QEMU-050t` 走 `load_elf()` 是复用上游标准 API，不改变外部接口契约（用户仍通过 `-kernel <elf>` 加载），**不需 ADR** ✓。`ADR-0018 C7 D4` 修订（大帧四形态）已在 `SPEC-122t` 范围内 ✓。新 reloc 体系 ADR 也在 `SPEC-122t` 范围内 ✓。**无遗漏**。

**结论**：ADR 前置 **通过**。

##### 5. 可执行性

- **`LLVM-063t`（clang target）**：依赖 `INFRA-050t`（一次构建 DADAO;X86）+ `SPEC-124t`（调用约定契约）。`SPEC-124t` 依赖 `SPEC-122t`（ADR 先行）。**前置链完整** ✓
- **`TESTCASES-038t`（上游 IR + lli 对拍）**：依赖 `LLVM-063t`（clang target）+ `INFRA-050t`（lli 产出）。**前置链完整** ✓
- **`TESTCASES-039t`（Embench）**：依赖 `INFRA-051t`（组件接入）+ `LLVM-062t/063t`（编译能力）+ `QEMU-050t`（ELF 加载）。`INFRA-051t` 依赖 `SPEC-122t`（Embench ADR）。**前置链完整** ✓
- **所有任务的验证手段**：§C 各任务范围描述隐含验证方式（如 `QEMU-050t` = 多段 PT_LOAD/RELA/e_entry 作验证项；`TESTCASES-036t` = 独立 oracle）。§D L301-302 明确「快档入 make check + 全量档 opt-in」。**可执行** ✓

**结论**：可执行性 **通过**。

##### 6. 风险/遗漏

**#1 `MaxStoresPerMem*=16` 归属**：§A #3（L12）提及 → §C `LLVM-064t`（L48）明确包含 ✓。无遗漏。

**#2 `#16 step2` 与 `#12–14 load_elf()` 先后/耦合**：§C `QEMU-051t`（L53）依赖 `QEMU-050t` ✓。step2 在 load_elf() 之后执行（先有 ELF 加载能力，再迁移旧向量）。**顺序正确**。

**#3 「计数不写死」落点**：§B L34 声明为**跨任务通用规范**（「文档/注释/任务书/验收不得硬编码计数」）。§C/§D 未将其分配到单个任务——**合理**（它是约束而非任务），但应在建 `t`/`m` 时作为**每个任务书的硬约束**显式写入。**非阻塞**，提醒 architect 建任务书时带入。

**#4 `ISS-003`（LR-SC 原子）遗漏**：`issues.yaml` 实查确认 `ISS-003` scope `[M6]`（L94-100），但 §A/§B/§C **均未提及**。LR-SC 是新 ISA 指令（非 LLVM 欠账），不在「完整 LLVM」20 项内——**推测有意排除**（M6 聚焦编译正确性，非 ISA 扩展），但**未显式说明**。建议 §A 或 §D 追加一条「`ISS-003` LR-SC 原子：**不纳入 M6**（ISA 扩展，非编译正确性范畴），scope 待后续里程碑重定」。**非阻塞**但建议补说明。

**#5 `ISS-169`（exit-port 迁移）遗漏**：`issues.yaml` 实查确认 `ISS-169` scope `[qemu, testcases, M6]`（L403-409），§C/§D **未提及**。6 个旧探针的 exit-port → SYS_EXIT 迁移可归入 `QEMU-051t`（RAM@0 step2 也涉及旧向量迁移）或另立小任务。**建议**在 §C 补入（随 `QEMU-051t` 或独立）。**非阻塞**但建议补。

**#6 `INTEG-024t` 冲突**：`INTEG-024t` 改 `issues.yaml`（移出规划/阻塞/待裁定项），`INTEG-023k` 只规划不改文件。**无冲突** ✓。但若 `INTEG-024t` 先执行，`issues.yaml` 结构变化后 §B 引用的行号会失效——**不影响正确性**（§B 引用的是 ISS id 非行号），仅影响 reviewer 重查效率。**无风险**。

**#7 `INTEG-024t` 建议分类与 §B 的一致性**：`INTEG-024t` 建议 `ISS-043/045/108/138/148/151/154/156/159/161/162` 为「④ 真 issue（保留）」（L89），与 §B「纳入 M6」一致（纳入 = 作为 M6 欠账收口，完成后 close；保留 = 留在 issues.yaml 直到 close）✓。

**结论**：风险/遗漏 **基本通过**，有3项非阻塞建议（#1 跨模块重号、#4 ISS-003 说明、#5 ISS-169 补入）。

##### 判决

**通过**（附非阻塞建议）。

**最小建议清单**（非阻塞，可在建 `t`/`m` 时一并处理）：
1. **跨模块重号**：QEMU 模块编号从052起（052t/053t/054m），或所有跨模块引用显式加模块前缀。
2. **ISS-003 说明**：§A 或 §D 追加「ISS-003 LR-SC 不纳入 M6」的显式说明。
3. **ISS-169 补入**：§C 补 `ISS-169` exit-port 迁移（随 `QEMU-051t` 或独立小任务）。
4. **「计数不写死」约束传播**：建 `t`/`m` 时作为每个任务书的硬约束带入。

**据此建17份 t + 6份 m 任务书是否安全**：**是**，上述3项建议为非阻塞，可在建任务书时一并修正。核心依赖链、ADR 前置、串行约束均完备。

#### 第 3 轮 architect `/plan` 通过 + 4 项修正落实（2026-10-08）

- **`/plan` 交叉审查判决 = 通过**（见上「第 1 轮 reviewer 交叉审查」）；本 `k` `**状态**` 置 **`已验证`**。
- **4 项修正已落实**（详见 §E）：
  1. **跨模块重号消除**：实测各模块最大号（`INFRA-049`/`SPEC-121`/`LLVM-061`/`QEMU-049`/`TESTCASES-035`/`INTEG-022`）后，`QEMU` 顺延两位 ⇒ **`QEMU-052t/053t/054m`**；§C/§D 已同步（reviewer 记录中旧编号保留为历史原文）。
  2. **`ISS-003`（LR-SC）M6 排除**（显式声明 + 理由，§E-2）；已同步 `issues.yaml`（仅追加 notes，id 不变）。
  3. **`ISS-169` 归 `QEMU-053t` 范围**（§C/§E-3）。
  4. **「计数不写死」**作为硬约束写入全部 M6 任务书（§E-4）。
- **任务书已建**：**17 `t` + 6 `m` = 23 份**（§C 表；较 `k` 草案新增 `INFRA-052m`），落 `.tao/tasks/<module>/`。
- **边界**：本次仅改本 `k` + `milestones.md` + `issues.yaml`（+ 新建任务书）；**`spec/` 交集为空**；未触 `contracts/**`/`components/**`/`Makefile`/`tools/**`。

#### 提交留痕（architect，2026-10-09）

- **档位**：architect 规划产出（立项新任务 + 联动台账），内容完整、无未决 ⇒ **正常提交**（无 `WIP:` 前缀）。
- **提交号**：`2d5cc4f`（`M6: 立项 ABI 寄存器重排（rb2=GP/rb3=TP/rb4-7 与 rd4-7 caller-saved/rd2-3 调试测试保留/rb63=FP 条件保留；不立 ADR；排 clang target 前）`）；**只 commit、未 push**。
- **文件集对账**（显式 staging，逐个路径，**禁** `git add -A`）：`git diff --cached --name-only` = `.tao/knowledge/milestones.md` / `.tao/tasks/integ/INTEG-023k-M6启动与分解.md` / `.tao/tasks/llvm/LLVM-063t-clang-target与driver.md` / `.tao/tasks/llvm/LLVM-066t-FP-RF-codegen.md` / `.tao/tasks/llvm/LLVM-068t-ABI寄存器重排后端实现.md`（新） / `.tao/tasks/spec/SPEC-128t-ABI寄存器布局重排.md`（新）——与本轮立项范围**逐条相等**（**无漏提 / 无多提 / 无越界**；`LLVM-062t` 在跑改动**未混入**）。
