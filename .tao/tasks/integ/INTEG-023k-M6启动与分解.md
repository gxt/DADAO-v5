# INTEG-023k: M6 启动与分解（用户逐条裁定落纸 + 任务分解草案）
**模块**：integ　**项目里程碑**：M6　**状态**：待开始
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
| `INFRA-051t` | Embench 组件接入 | infra | ADR 记录上游+commit ⇒ `manifests` 翻 `enabled=true`；建 `components/embench-iot/{patches,series}` 骨架 + `make fetch` 落 `.work/source/embench-iot` | `SPEC-122t` |
| `SPEC-122t` | ADR 决策落地（逐条用户确认） | spec | ①`ADR-0018 C7 D4` 修订（大帧四形态/代价驱动）②新 ADR「`ld/st` 符号偏移 reloc 体系」③Embench 上游选择 ADR ④组合加载语义 ADR（判断见 §D） | 无 |
| `SPEC-123t` | reloc 正文 + `Toolchain-01 §6.1` | spec | `contract-elf §2–§4`（`REL12`/新类型/`ABS48` 数据 8B 字段〔`ISS-154`〕）+ `spec/Toolchain-01 §6.1` 修订（`ISS-156`）+ 该册 `sha256` 锁同步 | `SPEC-122t` |
| `SPEC-124t` | 调用约定契约收口 | spec | `contract-abi §6` 3 项 `[OPEN]`（多返回值声明顺序/red zone/`i128`）消解 | `SPEC-122t` |
| `SPEC-125m` | M6 spec 里程碑 | spec | `m` 文件 | `SPEC-122t`~`124t` |
| `LLVM-062t` | 整数完整调用约定 + 小欠账 | llvm | 变参/聚合/`sret`/多返回/间接调用（`ISS-005/006`）+ `ISS-043/045/047/148/159/162`；**`ISS-110` 留后** | `INFRA-050t`、`SPEC-124t` |
| `LLVM-063t` | DADAO clang target（钉子①） | llvm | `TargetInfo`/DataLayout/ABI/driver/sysroot；**只用于 freestanding**；模板 = RISC-V64 形状 + PPC64BE 端序/DL + AArch64 CC | `INFRA-050t`、`SPEC-124t` |
| `LLVM-064t` | 大帧寻址 + `mem*` 内建 | llvm | `ISS-138` 四形态（按代价选择；落 `ADR-0018 C7 D4` 修订）+ `mem*` 内建 + 后端 `MaxStoresPerMem*=16` | `LLVM-062t`、`SPEC-122t` |
| `LLVM-065t` | lld reloc 完善 | llvm | `REL12` + 新专用类型（`ISS-151/161`）+ `FK_Data_1/2/4` 静默出 0；`ISS-108` 拆分文件 | `SPEC-123t`、`INFRA-050t` |
| `LLVM-066t` | FP/RF codegen | llvm | FP/RF（**排整数之后**；`ISS-081/126/078`；含 compiler-rt 软浮点取舍随 #2） | `LLVM-062t`、`SPEC-122t` |
| `LLVM-067m` | M6 llvm 里程碑 | llvm | `m` 文件 | `LLVM-062t`~`066t` |
| `QEMU-050t` | 改走 `load_elf()`（钉子②） | qemu | 复用 `hw/core/loader.c`；**取消**自建 `dadao_load_regions[]` 白名单；多段 `PT_LOAD`/RELA/`e_entry`/栈初始化作**验证项** | 无（M5 已验证态） |
| `QEMU-051t` | RAM@0 step2（`ISS-165`） | qemu | 旧向量/harness/`crt0`/e2e 迁 `0` + 删旧 RAM 段（`0xffff_0000_0000`）+ 收紧 `check-interface` 断言 | `QEMU-050t`、`TESTCASES-034t`（已验） |
| `QEMU-052m` | M6 qemu 里程碑 | qemu | `m` 文件 | `QEMU-050t/051t` |
| `TESTCASES-036t` | 新能力向量（L1+L3） | testcases | 调用约定/reloc/大帧/FP-RF 的 L1 编码 + L3 执行向量；**独立 oracle**（禁从 LLVM/QEMU 反填） | `LLVM-062t`~`066t`、`QEMU-050t` |
| `TESTCASES-037t` | lit 量产 | testcases | 骨架 agent 生成 + 期望值**从 `spec`/`contracts` 机械派生**（禁反填）；目标数百；分层：**快档入 `make check`、全量档 opt-in** | `LLVM-062t`、`QEMU-050t` |
| `TESTCASES-038t` | 上游 IR + `lli` 值级对拍 | testcases | 上游 `.ll` 当输入（编译/编码层）+ 有 `lli` 时值级对拍（证「IR 语义被保持」）；**不作执行语义判据** | `LLVM-063t`、`INFRA-050t` |
| `TESTCASES-039t` | Embench 接入（钉子③） | testcases | board shim 3 函数（`initialise_board`/`start_trigger`/`stop_trigger`）+ 最小运行时（`mem*/str*/ctype/sqrt`）+ `md5sum` 大端适配；**首验收 = 最小基准 QEMU 正确退出码** | `INFRA-051t`、`LLVM-062t/063t`、`QEMU-050t` |
| `TESTCASES-040m` | M6 testcases 里程碑 | testcases | `m` 文件 | `TESTCASES-036t`~`039t` |
| `INTEG-025t` | E2E + `make test-m6` 门控收口 | integ | 驱动 `lli` 对拍/Embench/lit 全量档；新 target `test-m6`（**opt-in，不进 `make check`**）；`check` 收口 | `TESTCASES-036t`~`039t`、`LLVM-065t`、`QEMU-051t` |
| `INTEG-026m` | M6 integ 里程碑（整体收敛） | integ | `m` 文件 | `INTEG-025t` |

## D. Wave/串行链 · 前置 ADR · 说明

- **Wave 0（infra；同改 `Makefile`/`manifests` ⇒ 串行）**：`INFRA-050t` → `INFRA-051t`。
- **Wave 1（spec 决策先行；同改 `spec/`/锁 ⇒ 串行）**：`SPEC-122t` → `SPEC-123t`／`SPEC-124t`。**ADR 未 `Accepted` 前不进实现**（`Process-03`）。
- **Wave 2（llvm；同改 `components/llvm-project/patches` ⇒ 串行）**：`LLVM-062t` → `063t` → `064t` → `065t` → `066t`（FP 最后）。
- **Wave 3（qemu；同改 `components/qemu/patches` ⇒ 串行）**：`QEMU-050t` → `QEMU-051t`。
- **Wave 4（testcases）**：`TESTCASES-036t`／`037t`／`038t`／`039t`；**Wave 5（integ）**：`INTEG-025t` → `INTEG-026m`。
- **前置 ADR 清单（逐条待用户确认，勿预标 `Accepted`）**：① `ADR-0018 C7 D4` 修订（大帧四形态/代价驱动）；② 新 ADR「`ld/st` 符号偏移 reloc 体系」（`REL12` + 新专用类型）；③ Embench 上游选择 + commit；④ 组合加载语义——**判断：不再需要独立 ADR**（已被「改走 `load_elf()`」取代，自建 loader/组合路径**取消**；仅在 `SPEC-122t` 落「不立 + 理由」）；⑤ 判断无需其它（`ADR-0019 D7` 记为**留后**、不启用）。
- **`k↔m`**：本 `k` 对应 M6；各模块 `m` 就近核验，M6 由主会话在模块 `m` 均 `里程碑` 后置 `达成`（`Process-04 §1`）。
- **说明**：本 `k` 只落纸 + 出草案，**不建 `t`/`m`、不占编号**（编号按各模块现有最大号 +1，已按 M5 归档后顺延）；另有 `INTEG-024t`（台账搬迁，M6，**并行且互不占号**）。

## 审阅记录

#### 第 1 轮 architect 口径更正（2026-10-08）
- 「三根钉子」= M6 前三项具体交付（clang target〔#5〕/ QEMU `load_elf()`〔#12–14〕/ Embench 接入〔`TESTCASES-039t`〕）；原文误读为「先钉死三项」已更正（详见 git 历史与 `.work/log/integ/`）。

#### 第 2 轮 architect 裁定落纸（2026-10-08）
- 用户对 **20 项内涵（§A）+ 12 条 LLVM 欠账（§B）逐条裁定**已落纸；M6 分解草案落 **§C/§D**。**待 `/plan` 交叉审查**，通过后再建 `t`/`m` 任务书。
