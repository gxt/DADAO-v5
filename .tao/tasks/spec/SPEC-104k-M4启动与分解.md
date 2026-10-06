# SPEC-104k: M4（ELF 文件支持 + LLD 链接 + 汇编器遗留收口）启动与分解

**模块**：spec
**项目里程碑**：M4
**依赖**：无
**状态**：已验证

## 问题根源

M3（Basic CodeGen，纯整数）已达成（2026-10-05，见 `milestones.md`）。当前 v5 工具链止于一条**捷径**：

- **产物**：`.o → objcopy --only-section=.text -O binary → flat binary`（`ADR-0003 §D5`）；**无 LLD、无 `ET_EXEC`、无 `e_entry`**（`ADR-0004` 双镜像 + trampoline）。
- **重定位**：仅**段内 PCRel 就地解析**（`LLVM-041t` 的 `evaluateFixup`）；**无 relocation 类型/编号**（`contract-elf §2–§4` 仍 `Deferred`）；跨段/外部符号**静默留 0**（`ISS-142`）。ELF writer 仍是**返回 0 的桩**，`HasRelocationAddend_=false`（REL）。
- **汇编器遗留**（`contract-asm §6/§7/§8/§11`，实测全未实现）：**伪指令 18 条**、`.dd.{b08,w16,t32,o64}` 指导符、`-multiple-to-single` 选项、越界立即数**静默环绕**（缺陷）、ABI 寄存器别名。
- **全局数据**：`llc` **不发射** `.data`/`.rodata`（M3 程序仅 `i64 @main()` freestanding）。
- **QEMU**：**无 ELF 加载器**（走 trampoline + raw bin，不解 `Ehdr`/不读 `e_entry`）。

结果：工具链**产出不了可链接/可加载的规范 ELF**、**汇编器功能不全**，无法承载真实（多 TU / 全局数据 / 后续 C）程序。

## 目的

把工具链从「**raw-bin 单 TU 捷径**」升级为「**规范 ELF 产出 + LLD 链接 + QEMU ELF 加载**」：

```
llc → llvm-mc → ld.lld → ET_EXEC → qemu-system-dadao 直接加载执行
```

同时清掉 M1/M2 遗留的**汇编层欠账**。**门槛 = `make test-elf` 绿**（多 TU + 多段端到端）。

## 已锁定边界（用户裁定 2026-10-05/06）

- **M4 范围（四块）**：① 汇编器遗留；② ELF 产出规范（含全局数据段）；③ **LLD 链接器**（含链接脚本）；④ **QEMU ELF 加载**。
- **参考基线**：**主对标 RISC-V 64**（工具链/软件系统总纲）；次要 **x86-64/AArch64**（LLD/ELF 基础设施）；**端序参考 PPC64 BE（+ s390x）**；**双 bank 历史参考 M68K**。
- **重定位**（`ADR-0019`，`Accepted`）：RELA；`ABS48=0` / `REL26=1` / `REL20=2` / `REL14=3`；公式 v5 **无 −4**；`ABS48` ≤3 片 + **一律 max 3 片**；逐指令挂 reloc；溢出=**link-time error**；**禁用 relaxation**；不做 ABS32。
- **伪指令集收缩**（`ADR-0013 D11`）：只留**合成型** 8 条（`set.rd`/`set.rb`/`set.ft`/`set.fo` × imm/reg）；**删** `nop`/`return`/`not.*`/`neg.*`；`ret` 不加无参形态；**反汇编只显真实指令**。
- **链接脚本**（`dadao.lds`）：地址布局依 **`ADR-0004`**（RAM 基址 `0xffff_0000_0000` 作 `.text`/entry；段序 `.text→.rodata→.data→.bss`）；对齐依 `contract-elf §5`；`FILEHDR PHDRS` 使 `.text` file-offset 0。**可能需调整 `ADR-0004`**（ELF `e_entry`/段布局/加载约定）。
- **测试策略**（`spec/Process-05` TDD）：L1（MC）+ L3（执行）为主、**L2（CodeGen 结构）极简**；「一能力一向量」；移植**只借结构**、期望值**独立派生自 `spec/`**。
- **不做（→ M5+）**：完整调用约定（变参/聚合/sret/多返回/间接）、**FP/RF**、clang 前端、libc/OS/syscall、**semihosting 字符输出**、golden model。

## reloc/fixup 坑预防（M4 硬约束，源自 `DADAO-0628` 实录）

① fixup **必须尊重 `IsResolved`**（禁写预链接原始值）；② same-section「快速路径」不可靠则**删掉、退回真重定位**；③ **`rb0`（= 当前 PC）禁作基址/零**；④ 跳转表/间接跳转目标标签**必须显式发射**；⑤ 大常量**不得折入**受限立即数/relocation 字段（先材料化）。

## 对照关系

- **RISC-V 64**（`.work/source/llvm-project/llvm/lib/Target/RISCV/`、`lld/ELF/Arch/RISCV.cpp`，**LLVM 内只读参考**）：ELF/reloc/LLD 的**主流范式**（`PCREL_HI/LO`、`getRelExpr`/`relocate`、链接脚本/`e_entry`）。
- **PPC64 BE**（`llvm/lib/Target/PPC/`、`lld/ELF/Arch/PPC64.cpp`）：**大端** ELF/编码/reloc 对照。
- **M68K**（`M68k*`）：双 bank（地址/数据分离）+ 大端的基本教训（32 位，历史对照）。
- **DADAO-0628**（`.cache/refs/DADAO-0628/`，**只读、不复制**）：`DL-061c`（globals 经标准 `ld.lld` + `dadao.ld` 链接脚本）、`ML-003e`（MC 重定位缺口：跨 section call / 数据段函数指针）、`ML-030a`（大常量折入 relocation 越界）、`DL-056b`（call 符号重定位）；经验/坑见上「坑预防」与 `docs/development-roadmap.md`。

## 任务分解

| 编号 | 任务 | 模块 | 交付物 | 依赖 |
|------|------|------|--------|------|
| `SPEC-109t` | **删 `illi` / `fence`→`0x00` / `swym`→`0x22`（MISC-AMO 编码调整，跨组件原子；M4 链首）** | spec | `spec/SimRISC-00/11` + `contract-isa §13` + `contract-asm §6` + `contracts/opcodes.yaml` + LLVM MC + QEMU（`insn.decode`/`trans_ctrl`）+ `tests/vectors` + `adr-0004` 注 + crt0（**同一落地波/提交**） | 无 |
| `SPEC-105t` | `contract-elf §2–§4` 重定位正文（按 `ADR-0019`） | spec | `contract-elf.md` §2–§4 正文（类型/公式/溢出）+ 门控对齐 | 无 |
| `SPEC-106t` | 伪指令集收缩 spec 修订（按 `ADR-0013 D11`；**只做 spec 文本**——权威源迁 `Toolchain-01 §6` + 全 `spec/` 功能说明/定义删除 + `contract-asm §6`/`MEMORY` 台账/`README` 投影；**不产向量**） | spec | `spec/Toolchain-01 §6`（权威伪指令）+ `spec/SimRISC-00/…`（功能说明）+ `contract-asm §6` + `MEMORY.md` 偏离台账 + `spec/README` 投影 | `SPEC-109t`、`INFRA-045t`、`SPEC-110t` |
| `SPEC-107t` | `ADR-0004` 调整（ELF `e_entry`/段布局/加载约定）〔若需〕 | spec | `adr-0004` 就地修订 + `contract-elf §5/§6` 同步 | `SPEC-105t` |
| `SPEC-110t` | **`Process-05 §6` 落点路径同步**（`INFRA-045t` 组件先行重排后示例路径过期） | spec | `spec/Process-05-里程碑TDD规范.md §6`（路径示例） | `INFRA-045t` |
| `INFRA-043t` | LLD 入构建目标 | infra | `Makefile`（`build-mc`/新目标产出 `ld.lld`）+ 构建证据 | 无 |
| `INFRA-045t` | **`tests/` 组件先行重排**（对齐上游 `llvm/test/{MC,CodeGen,tools}`） | infra | `tests/llvm/{lit/{MC,CodeGen,tools}/DADAO, codegen}` + `tests/qemu/` + `tests/e2e/lit/`；`Makefile`/工具路径同步 | 无 |
| `INFRA-046t` | **测试产物落点与留存统一**（`test-codegen` 落 `.work/log/integ/codegen-e2e` → 模块固定路径 `tests/llvm/codegen-e2e/`；依 `Process-05 §6` + `ADR-0016 D6`） | infra | `Makefile`（`CODEGEN_E2E_WORK`）+ `tools/integ/run_codegen_e2e.py`（`DEFAULT_WORK_DIR`）+ `.gitignore` + 运行/负例证据 | `INFRA-045t` |
| `LLVM-050t` | ELF writer → **RELA** + `e_flags=1` + `e_machine`→dadao + `getRelocType`（4 类） | llvm | `DADAOELFObjectWriter`/`MCCodeEmitter`/`AsmBackend` + lit/`readelf` 证据 | `SPEC-105t`、`SPEC-109t`、`INFRA-045t` |
| `LLVM-051t` | 伪指令展开（`set.rd/set.rb/set.ft/set.fo`；常量/符号分派） | llvm | AsmParser 展开 + lit MC 证据 | `SPEC-106t`、`LLVM-050t` |
| `LLVM-052t` | `.dd.{b08,w16,t32,o64}` 指导符发射 | llvm | MC 指导符 + lit 证据 | `LLVM-050t` |
| `LLVM-053t` | `-multiple-to-single` 汇编器选项 | llvm | MC 选项 + lit 证据 | `LLVM-051t` |
| `LLVM-054t` | 越界立即数诊断（禁静默环绕） | llvm | AsmParser 报错 + lit 反例 | `LLVM-051t` |
| `LLVM-055t` | 全局数据 lower（`.data`/`.rodata`）+ `ABS48`/RELA fixup | llvm | CodeGen 全局 lower + MIR/`.s` 证据 | `LLVM-050t` |
| `LLVM-056t` | **DADAO LLD target** + 链接脚本 `dadao.lds` | llvm | `lld/ELF/Arch/DADAO.cpp` + `Target.{cpp,h}` + `dadao.lds` + 链接证据 | `INFRA-043t`、`LLVM-050t`、`SPEC-107t` |
| `QEMU-042t` | **QEMU ELF 加载器**（`Ehdr`/`Phdr`/装载/`e_entry`；加载期 over-size 守卫） | qemu | `hw/dadao/` ELF 加载 + 负例（畸形 ELF / over-size 拒绝） | `SPEC-107t`、`SPEC-109t` |
| `TESTCASES-029t` | L1 MC 向量（伪指令/指导符/选项/诊断/往返） | testcases | `tests/llvm/lit/MC/DADAO/`（`UNSUPPORTED:` 标记）+ 独立 oracle | `SPEC-106t`、`INFRA-045t` |
| `TESTCASES-030t` | L3 执行向量（多 TU/多段/ELF 链路；独立 oracle） | testcases | `tests/llvm/codegen/m4/`（独立 m4 清单）+ 期望值 | `SPEC-105t`、`INFRA-045t` |
| `TESTCASES-032t` | **`not`/`neg` 功能向量（L1 编码 + L3 执行；测底层真实指令 `xnor.o`/`sub.sb/sw/st/so`）** | testcases | `tests/llvm/lit/MC/DADAO/`（`UNSUPPORTED:` 标记）+ `tests/llvm/codegen/m4/`（独立 m4 清单）+ 独立 oracle | `SPEC-106t`、`INFRA-045t`、`TESTCASES-029t`、`TESTCASES-030t` |
| `INTEG-016t` | 多 TU/多段 E2E + `make test-elf` | integ | `tools/integ/` 驱动 + `Makefile` 目标 | `LLVM-056t`、`QEMU-042t`、`TESTCASES-029t`、`TESTCASES-030t`、`TESTCASES-032t` |
| `SPEC-108m` | M4 spec 里程碑 | spec | `m` 文件 | `SPEC-105t`/`106t`/`107t`/`109t`/`110t` |
| `INFRA-044m` | M4 infra 里程碑 | infra | `m` 文件 | `INFRA-043t`/`045t`/`046t` |
| `LLVM-057m` | M4 llvm 里程碑 | llvm | `m` 文件 | `LLVM-050t`~`056t` |
| `QEMU-043m` | M4 qemu 里程碑 | qemu | `m` 文件 | `QEMU-042t` |
| `TESTCASES-031m` | M4 testcases 里程碑 | testcases | `m` 文件 | `TESTCASES-029t`/`030t`/`032t` |
| `INTEG-017m` | M4 integ 里程碑 | integ | `m` 文件 | `INTEG-016t` |

### 依赖关系与串行纪律

- **M4 链首（用户裁定 2026-10-06）**：**`SPEC-109t`**（删 `illi`/`fence`→`0x00`/`swym`→`0x22`，跨组件原子，**同一落地波/提交**）→ **`INFRA-045t`**（`tests/` 组件先行重排）；二者**先于 `LLVM-050t`** 及一切按新路径落向量的任务。
- **`SPEC-109t` 为编码前提**：`contracts/opcodes.yaml` ↔ LLVM MC ↔ QEMU `trans_*` 计数须一致（`check-interface`/`check_qemu_trans`）⇒ 必须一次改完；`LLVM-050t`、`QEMU-042t` 依赖之。
- **`spec` 正文先行**：`SPEC-105t`（reloc 正文）→ `LLVM-050t`（ELF writer/reloc）；`SPEC-110t`（`Process-05 §6` 落点路径，依赖 `INFRA-045t`）→ `SPEC-106t`（伪指令，依赖 `SPEC-109t`/`SPEC-110t`）→ `LLVM-051t`。
- **`INFRA-045t` 为测试落点前提**：`LLVM-050t`~`054t`（新增 lit 向量）、`SPEC-110t`（`Process-05 §6` 路径同步）与 `TESTCASES-029t`/`030t`/`032t`（L1/L3/`not`·`neg` 向量）依赖其重排后的路径。
- **`INFRA-046t` 依 `INFRA-045t`**（同改 `tools/integ/run_codegen_e2e.py`/`Makefile`；`tests/llvm/` 结构须先建立）：把 `test-codegen` 运行产物由 `.work/log/integ/codegen-e2e` 改到**模块固定路径** `tests/llvm/codegen-e2e/`（依 `Process-05 §6` 新增「测试产物落点与留存」规则 + `ADR-0016 D6`）。
- **LLVM 链严格串行**（同改 `components/llvm-project/patches/llvm/lib/Target/DADAO/**` 与 `lld/**`、同一 `.work/source/llvm-project`）：`LLVM-050t → 051t → 052t → 053t → 054t → 055t → 056t`（`050t` 先行；`051t` 依赖 `050t` 的 ELF/reloc 基础；`056t` 最后）。
- **`INFRA-043t`**（LLD 入构建）与 `LLVM-050t` 无共享文件，可先于 `LLVM-056t` 任意时机，但 `LLVM-056t` 依赖其产物。
- **`QEMU-042t`**（不同仓库；但与 `SPEC-109t` 同改 QEMU 补丁树 ⇒ 依赖 `SPEC-109t`）可与 LLVM 链**并行**。
- **`TESTCASES-029t`/`030t`/`032t`** 按 `Process-05` **先于**对应实现（TDD），但为串行便利，先于 `INTEG-016t`；`032t` 共享 `029t`/`030t` 的落点与 validator，**串行于二者**（在其后扩展脚本）。
- **`INTEG-016t` 最后**（依赖 LLD + QEMU loader + `TESTCASES-029t`/`030t`/`032t` 向量）；`make test-elf` 与 `make test-codegen` 并存（差分对照）。
- **`Makefile`/`contracts/`/`spec/`/`tests/` 改动串行**（`AGENTS.md`「同改共享文件一律串行」）。
- `k ↔ m`：本 `k` 对应 M4；各模块 `m` 在模块任务收敛时核验，M4 由主会话在依赖模块 `m` 均达成后置 `达成`。

### 分解理由

- 按「**契约 → 产物层 → 链接 → 加载 → E2E**」分层，每步以「真实产物（`.o`/`.s`/`.rela`/ELF/链接）+ 重 build + 不回归」为独立验收点。
- `ADR-0019`（reloc）与 `ADR-0013 D11`（伪指令）已固化，`SPEC-105t`/`106t` 只做**正文落地**（不重新决策）。
- 测试（`TESTCASES-029t`/`030t`/`032t` 独立 oracle）与 E2E（`INTEG-016t`）分离，满足 **Independent oracle**；按 `Process-05` **TDD 先立向量**。

## 说明

- 本 `k` 只做规划，不实现；门槛核验在 `INTEG-017m`（及 M4 项目里程碑）前完成。
- **ADR 提醒**：`ADR-0019`（reloc）与 `ADR-0013 D11`（伪指令）已 `Accepted`；`SPEC-107t` 若调整 `ADR-0004` **仍须用户逐条确认**（已 `Accepted` 的 ADR 改动）。
- 任务书自包含：执行所需事实写入各任务书或引用 v5 自身知识；RISC-V64/PPC64BE/M68K/0628 仅作**只读对照**（内容溯源，非执行依赖）。
- **假设**：M4 内不改 `contract-elf` 之外的 spec 正文（`SPEC-105t` 改 `contract-elf §2–§4`；`SPEC-106t` 改 `SimRISC-00/03/06` + `contract-asm §6`）。（**注**：`SPEC-106t` 的文件范围经用户 2026-10-06 裁定改为**全 `spec/`**，见完成区「新发现 1」，本假设作废。）
- **修订（2026-10-06，用户逐条确认）**：新增 **`SPEC-109t`**（MISC-AMO 编码原子，M4 链首）与 **`INFRA-045t`**（`tests/` 组件先行重排）；修订 5 份任务书（`SPEC-106t` 伪指令范围改写、`TESTCASES-029t`/`030t` 落点、`LLVM-056t` 段溢出检查、`QEMU-042t` over-size 守卫），并同步全部受影响任务书的路径引用。详见「修订记录（2026-10-06）」。
- **修订（2026-10-06·2，用户二次裁定）**：新增 **`TESTCASES-032t`**（`not`/`neg` 功能向量，L1+L3）与 **`SPEC-110t`**（`Process-05 §6` 落点路径同步）；**`SPEC-106t` 移除向量、只做 spec 文本**（依赖 += `SPEC-110t`）。详见「修订记录（2026-10-06·2）」。

## 完成区

**测试结果**：N/A（`k` 规划任务，不实现、无代码；产出为 **21 份任务书**）。门控影响：仅新增/修改 `.tao/tasks/**`（纯文档，不在 `make check` 门控覆盖内，`AGENTS.md` 收尾检查 1）。

**创建的任务文件清单（21 个，编号/依赖严格按本 `k` §任务分解表）**：

- **spec（4）**：
  - `.tao/tasks/spec/SPEC-105t-contract-elf重定位正文.md`
  - `.tao/tasks/spec/SPEC-106t-伪指令集收缩spec修订.md`
  - `.tao/tasks/spec/SPEC-107t-ADR-0004调整.md`
  - `.tao/tasks/spec/SPEC-108m-M4-spec里程碑.md`
- **infra（2）**：
  - `.tao/tasks/infra/INFRA-043t-LLD入构建.md`
  - `.tao/tasks/infra/INFRA-044m-M4-infra里程碑.md`
- **llvm（8）**：
  - `.tao/tasks/llvm/LLVM-050t-ELF-writer-RELA与reloc类型.md`
  - `.tao/tasks/llvm/LLVM-051t-伪指令展开.md`
  - `.tao/tasks/llvm/LLVM-052t-dd指导符发射.md`
  - `.tao/tasks/llvm/LLVM-053t-multiple-to-single选项.md`
  - `.tao/tasks/llvm/LLVM-054t-越界立即数诊断.md`
  - `.tao/tasks/llvm/LLVM-055t-全局数据lower与ABS48.md`
  - `.tao/tasks/llvm/LLVM-056t-DADAO-LLD-target与链接脚本.md`
  - `.tao/tasks/llvm/LLVM-057m-M4-llvm里程碑.md`
- **qemu（2）**：
  - `.tao/tasks/qemu/QEMU-042t-ELF加载器.md`
  - `.tao/tasks/qemu/QEMU-043m-M4-qemu里程碑.md`
- **testcases（3）**：
  - `.tao/tasks/testcases/TESTCASES-029t-L1-MC向量.md`
  - `.tao/tasks/testcases/TESTCASES-030t-L3执行向量.md`
  - `.tao/tasks/testcases/TESTCASES-031m-M4-testcases里程碑.md`
- **integ（2）**：
  - `.tao/tasks/integ/INTEG-016t-多TU多段E2E与test-elf.md`
  - `.tao/tasks/integ/INTEG-017m-M4-integ里程碑.md`

**依赖 / 串行链**：

- **spec 正文先行**：`SPEC-105t`（reloc 正文）→ `LLVM-050t`；`SPEC-106t`（伪指令）→ `LLVM-051t`；`SPEC-107t` 依赖 `SPEC-105t`。
- **LLVM 链严格串行**（同改 `components/llvm-project/patches/llvm/lib/Target/DADAO/**` 与 `lld/**`、同一 `.work/source/llvm-project`）：`LLVM-050t → 051t → 052t → 053t → 054t → 055t → 056t`。
- **`INFRA-043t`**（LLD 入构建）与 `LLVM-050t` 无共享文件，可先于 `LLVM-056t` 任意时机；`LLVM-056t` 依赖其产物 `ld.lld`。
- **`QEMU-042t`**（不同仓库）可与 LLVM 链**并行**，依赖 `SPEC-107t`。
- **`TESTCASES-029t`/`030t`** 按 `Process-05` 先于对应实现（TDD），先于 `INTEG-016t`。
- **`INTEG-016t` 最后**（依赖 LLD + QEMU loader + 向量）；`make test-elf` 与 `make test-codegen` 并存（差分对照）。
- **`Makefile`/`contracts/`/`spec/` 改动串行**（`AGENTS.md`「同改共享文件一律串行」）。
- 反向依赖（实现 ← 契约）：`LLVM-050t`←`SPEC-105t`；`LLVM-051t`←`SPEC-106t`；`LLVM-056t`/`QEMU-042t`←`SPEC-107t`。

**与 M3 的差异**：

1. 产物从「raw-bin 单 TU + 同段就地解析（`ADR-0003 §D5`）」→「**规范 ELF（`ET_EXEC`）+ LLD 链接 + QEMU ELF 加载**」。
2. 新增**重定位层**（RELA，`ABS48/REL26/REL20/REL14`，`ADR-0019`）与 **DADAO LLD target**（`lld/ELF/Arch/DADAO.cpp` + `dadao.lds`）。
3. **汇编器遗留收口**：伪指令收缩、`.dd.*` 指导符、`-multiple-to-single`、越界立即数**报错**。
4. **全局数据**：`llc` 发射 `.data`/`.rodata`（M3 仅 freestanding `i64 @main()`）。
5. **测试策略改为 TDD**（`Process-05`）：**L1（MC）+ L3（执行）为主、L2 极简**；向量**先立**、期望值独立派生、反例门控。
6. **模块列**：新增 **qemu 模块里程碑**（M3 的 qemu 列为 `—`，执行层已由 M1 冻结）；本轮 qemu 有独立 ELF 加载任务。

**新发现/坑（规划阶段实测）**：

1. **`SPEC-106t` 文件范围与 `k` 假设不符**：实测被删伪指令（`nop`/`return`/`not.*`/`neg.*`）的详细定义散布在 `spec/SimRISC-04 §not/§neg`、`SimRISC-06 §return`、`SimRISC-08/09/10 §neg`、`SimRISC-11 §nop`，**非仅** `SimRISC-00/03/06`。**用户裁定（2026-10-06）**：「全 spec 范围删除被删伪指令定义（推荐）」；已按此写 `SPEC-106t`（并注明原 `k` 假设 00/03/06 作废）。
2. **TESTCASES 向量与门控时序冲突**：`Process-05` TDD「先立向量」与「向量任务收尾时 `make check` 必绿」（`AGENTS.md` 门控全绿）矛盾——L1 落 `tests/lit/MC/Dadao/`（在 `check-lit` 覆盖内）、L3 落 `tests/codegen/`（被 `make test-codegen` 消费）。**用户裁定（2026-10-06）**：「向量+独立 oracle，暂不接入门控（推荐）」。故：`TESTCASES-029t` 向量暂存 `tests/lit/MC/Dadao-m4/`（不在 `check-lit` 路径内）、`TESTCASES-030t` 向量暂存 `tests/codegen-elf/`（独立于 M3 `tests/codegen/`）；由实现任务 / `INTEG-016t` 接入并转绿（对齐 M3 `TESTCASES-026t` 先例）。
3. **落点相对 `k` 表的调整**：`TESTCASES-029t` 交付物由「`tests/lit/MC/Dadao/` 扩展」定为「`tests/lit/MC/Dadao-m4/` + 独立 oracle（待接入）」；`TESTCASES-030t` 由「`tests/codegen/` 扩展」定为「`tests/codegen-elf/` + 独立 oracle（待接入）」。理由见上 2；编号/依赖不变。
4. **`INFRA-043t` 构建细节**：启用 lld 需改 `LLVM_ENABLE_PROJECTS`（现为 `""`）并重跑 cmake（`build-mc` 在 `build.ninja` 存在时跳过 cmake）；`build-mc` 不回归为硬约束。
5. **`LLVM-050t` 实测现状**：`e_machine=0x0DA0` 与 `e_flags=0x1` 已在 M1/M3 落地（`DADAOELFObjectWriter`/`DADAOTargetStreamer`），本任务实际核心为 `HasRelocationAddend_`→true、`getRelocType` 4 类、`ABS48` fixup 与 `ELF.h` 枚举；任务书已按实测写（含回归确认项）。

**遗留问题 / 待用户确认**：

- **`SPEC-107t`〔若需〕**：是否调整 `ADR-0004`、调整哪些 decision，须**用户逐条确认**（任务书已含该硬约束；`Accepted` ADR 的改动不得擅自定稿）。
- **TESTCASES 落点长期性**：`tests/lit/MC/Dadao-m4/`、`tests/codegen-elf/` 是否长期作为独立目录（或接入后并入 `Dadao/`/`codegen/`），待接入任务（`INTEG-016t`）时确认。
- **`SPEC-106t` 投影表**：若 `spec/README.md` 含伪指令相关投影行，需同步（任务书已列为门控对齐项）。

## 审阅记录

#### 第 1 轮 architect 规划自审

**自审范围**：本 `k` §任务分解表 21 条 → 21 份任务书的落成；编号/依赖/串行链一致性；任务书自包含性与验收可执行性。

**要点**：
- 21 份任务书 ID / 依赖与 `k` 表**逐条一致**（编号未改）。
- 每份含 `# <ID>: <标题>`、`**模块**/**项目里程碑**：M4/**依赖**/**状态**：待开始`、`## 执行环境`、`## 接口规范`（输入/输出/约束，自包含）、`## 验收标准`（机械可判，引用 `Process-05` L1/L2/L3 与独立 oracle）、`## 完成区`、`## 审阅记录`。
- 两处与 `k` 假设的偏离已显式记录并由用户裁定（新发现 1/2/3）。
- 验收含反例门控（可失败脚本）、独立 oracle、真实输出/退出码、重建与还原。

**判决**：规划完成，状态置 **待验收**，交主会话 `/plan` 级交叉审查。

#### 第 1 轮 reviewer 规划审查

**审查范围**：22 个新文件（`SPEC-104k` + 21 份任务书）的存在性、结构完整性、依赖链、ADR/规范引用、自包含性、无残留。

**重跑记录**：

1. **存在性**：`git status --untracked-files=all --porcelain .tao/tasks/` → 22 个 `??` 文件。逐条对照 `SPEC-104k` §任务分解表：spec 4 / infra 2 / llvm 8 / qemu 2 / testcases 3 / integ 2 = 21 份任务书 + 1 份 `k` = 22。**无缺、无多、编号无碰撞**。EXIT=0。

2. **结构完整性**（脚本化 grep）：
   - 16 份 `*t` 任务书：全部含 `模块`/`项目里程碑`/`依赖`/`状态`/`执行环境`/`接口规范`/`验收标准`/`完成区`/`审阅记录`（两轮），M4 ✓。
   - 6 份 `*m` 里程碑文件（`SPEC-108m`/`INFRA-044m`/`LLVM-057m`/`QEMU-043m`/`TESTCASES-031m`/`INTEG-017m`）：用 `核验`/`核验记录` 代替标准任务字段，结构一致（含 `模块`/`项目里程碑`/`状态`/`目标`/`关联任务`/`核验`/`核验记录`）。
   - 全部22份含 `M4` ✓。

3. **状态**：`SPEC-104k` = `待验收`；其余21份 = `待开始`。✓

4. **依赖链核对**（逐条比对 `SPEC-104k` §任务分解表）：

| 任务 | 任务书实际依赖 | 表中依赖 | 一致？ |
|------|--------------|---------|--------|
| SPEC-105t | 无 | 无 | ✓ |
| SPEC-106t | 无 | 无 | ✓ |
| SPEC-107t | SPEC-105t | SPEC-105t | ✓ |
| INFRA-043t | 无 | 无 | ✓ |
| LLVM-050t | SPEC-105t | SPEC-105t | ✓ |
| LLVM-051t | SPEC-106t、LLVM-050t | SPEC-106t、LLVM-050t | ✓ |
| LLVM-052t | LLVM-050t | LLVM-050t | ✓ |
| LLVM-053t | LLVM-051t | LLVM-051t | ✓ |
| LLVM-054t | LLVM-051t | LLVM-051t | ✓ |
| LLVM-055t | LLVM-050t | LLVM-050t | ✓ |
| LLVM-056t | INFRA-043t、LLVM-050t、SPEC-107t | INFRA-043t、LLVM-050t、SPEC-107t | ✓ |
| QEMU-042t | SPEC-107t | SPEC-107t | ✓ |
| TESTCASES-029t | SPEC-106t | SPEC-106t | ✓ |
| TESTCASES-030t | SPEC-105t | SPEC-105t | ✓ |
| INTEG-016t | LLVM-056t、QEMU-042t、TESTCASES-029t、TESTCASES-030t | 同左 | ✓ |

   - LLVM 链严格串行：`050t→051t→053t`（经051t）/`050t→051t→054t`（经051t）/`050t→052t`（直接）/`050t→055t`（直接）/`056t`（末尾，依赖 INFRA-043t + LLVM-050t + SPEC-107t）。✓
   - `QEMU-042t` 可与 LLVM 链并行（不同仓库）。✓
   - `INTEG-016t` 最后。✓

5. **ADR/规范引用核对**：
   - `ADR-0019`（reloc）：`SPEC-105t`/`LLVM-050t`/`LLVM-055t`/`LLVM-056t` 均引用，编号 `ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`、RELA、公式无−4、溢出=link-time error、禁用 relaxation。✓
   - `ADR-0013 D11`（伪指令）：`SPEC-106t`/`LLVM-051t` 引用，8 条合成型留/10 条别名删/`ret`不加无参/反汇编只显真实指令。✓
   - `Process-05`（TDD）：`TESTCASES-029t`（9 处引用）/`TESTCASES-030t`（8 处引用），L1/L2/L3 + 独立 oracle + 反例门控。✓
   - `ADR-0004`：`SPEC-107t`/`LLVM-056t`/`QEMU-042t`/`INTEG-016t` 引用，RAM 基址/段布局/`e_entry`。✓
   - 所有引用文件均存在（`.tao/adr/adr-0019*.md`/`adr-0013*.md`/`adr-0004*.md`/`contract-elf.md`/`contract-asm.md`/`contract-isa.md`/`MEMORY.md`/`Process-01~05`/`contracts/opcodes.yaml`）。✓

6. **reloc/fixup 坑预防 5 条**：
   - `LLVM-050t` 约束段：完整 5 条（①IsResolved ②same-section ③rb0 ④跳转表 ⑤大常量），含 `ML-003e`/`ML-030a` 溯源。✓
   - `LLVM-051t`/`052t`/`053t`/`054t`：均引用「5 条，同 `LLVM-050t`」。✓
   - `LLVM-055t`：完整 5 条展开，尤其②（`ML-003e`）和⑤（`ML-030a`）。✓
   - `LLVM-056t`：引用「5 条，同 `LLVM-050t`」+ 尤其②⑤。✓

7. **自包含性**：
   - 所有任务书的执行依赖指向 v5 自身知识（`contract-*`/`ADR-*`/`Process-*`/`contracts/opcodes.yaml`）。
   - `DADAO-0628`/`RISC-V64`/`PPC64BE`/`M68K` 均标注「只读对照」/「内容溯源，非执行依赖」。✓

8. **`make check-no-residue`**：`check-no-residue: PASS`，EXIT=0。✓

9. **无残留**：`git status --porcelain -- . ':!.tao/tasks/'` → 空（无已跟踪文件改动）。✓

10. **两条用户裁定**：
    - **SPEC-106t 全 spec 范围**：任务书约束段明确「文件范围 = 全 `spec/`（用户裁定 2026-10-06）」+ 用户原话记录。✓
    - **TESTCASES 暂不接门控**：`TESTCASES-029t`/`030t` 输出段/约束段均含「用户裁定 2026-10-06：暂不接入门控」+ 用户原话。✓

11. **三个待裁定点标注**：
    - **`SPEC-107t` ADR-0004 调整**：任务书标题含「〔若需〕」、约束段含「凡改动 ADR-0004 的任一 decision，必须逐条经用户确认」；`SPEC-104k` 遗留问题明确标注。✓
    - **TESTCASES 落点长期性**：`SPEC-104k` 遗留问题标注「待接入任务（INTEG-016t）时确认」。✓
    - **`SPEC-106t` 投影表**：`SPEC-104k` 遗留问题标注「若 `spec/README.md` 含伪指令相关投影行，需同步」；`SPEC-106t` 验收标准含 `check-spec-refs` 门控（隐式覆盖）。✓

12. **`SPEC-104k` 完成区一致性**：任务清单21个 ID 逐条匹配、依赖/串行链一致、M3 差异6点正确、新发现5点均有据。✓

**判决**：**Accepted**

- 22 个新文件全部存在且 ID/路径正确，无缺无多无碰撞。
- 16 份 `*t` 任务书结构完整（含两轮审阅记录）；6 份 `*m` 里程碑用既有 `核验`/`核验记录` 结构，一致。
- 依赖链逐条与 `SPEC-104k` 表一致；LLVM 链严格串行；`QEMU-042t` 可并行；`INTEG-016t` 最后。
- ADR/规范引用全部可定位、内容准确；reloc/fixup 坑预防 5 条在 LLVM 链完整覆盖。
- 自包含性合格（外部仓库仅只读对照）。
- 两条用户裁定已在对应任务书正确体现；三个待裁定点已标注。
- `make check-no-residue` EXIT=0；无已跟踪文件改动。
- 状态 `待验收`，交主会话 `/complete` 收尾。

## 修订记录（2026-10-06，用户逐条确认）

**背景**：`SPEC-109k`→M4 规划（本 `k`）已 `Accepted` 并 `/complete` 收尾后，用户于 2026-10-06 逐条确认一组改动：新增 2 份任务书、修订 5 份既有任务书。本记录**追加**，不改写前述正文与审阅记录。

**依据（原样引用）**：
- `ADR-0012 D3 第 5 项`（2026-10-06 就地增补，用户逐条确认，`Accepted`）——删 `illi`（ILLI 异常保留）、`fence ha 0x01→0x00`（`value 0x77040000→0x77000000`）、`swym ha 0x02→0x22`（`value 0x77080000→0x77880000`），`op=0x77` 不变。
- `ADR-0013 D11`（2026-10-06 增补，`Accepted`）——伪指令集收缩（留 8 条合成型 / 删 10 条 1:1 别名；`ret` 不加无参；反汇编只显真实指令）。

**A. 新建（2 份）**：
- `.tao/tasks/spec/SPEC-109t-illi删除与fence-swym编码调整.md`（spec / M4）——**M4 链首**、跨组件原子（`spec/SimRISC-00/11` + `contract-isa §13` + `contract-asm §6` + `contracts/opcodes.yaml` + LLVM MC + QEMU + `tests/vectors` + `adr-0004` 注 + crt0），**同一落地波/提交**。
- `.tao/tasks/infra/INFRA-045t-tests组件先行重排.md`（infra / M4）——`tests/{llvm/lit/{MC,CodeGen,tools}/DADAO, llvm/codegen, qemu, vectors/isa, e2e}`；含 `tests/lit/MC/Dadao→tests/llvm/lit/MC/DADAO`、`tests/codegen→tests/llvm/codegen`、`tests/lit/E2E→tests/e2e/lit` 迁移 + `tests/qemu/` 新增。

**B. 修订（5 份）**：
1. **`SPEC-106t`**：范围改写——权威伪指令集迁 **`spec/Toolchain-01 §6`**；`SimRISC-00 §伪指令` 删定义、改留「功能说明 + 如何实现」（`not`→`xnor.o`、`neg`→`sub.sX`），不再作为指令；新增 `not`/`neg` 替代功能（`xnor`/`sub.sX`）**L1 编码 + L3 执行**专门向量；同步 `contract-asm §6` + `spec/README` 投影表指针；依赖 += `SPEC-109t`、`INFRA-045t`。
2. **`TESTCASES-029t`**：落点改 **`tests/llvm/lit/MC/DADAO/`（单一）**；「暂不接门控」用 lit **`UNSUPPORTED:`** 标记（不并排 `Dadao-m4/`）；依赖 += `INFRA-045t`。
3. **`TESTCASES-030t`**：落点改 **`tests/llvm/codegen/m4/`（并入 + 独立 m4 清单，M3 驱动不读）**，不另起 `tests/codegen-elf/`；依赖 += `INFRA-045t`。
4. **`LLVM-056t`**：补 **段溢出检查**——`dadao.lds` 定义 `MEMORY`（RAM 16 MiB `0xffff_0000_0000`–`0xffff_00ff_ffff`、ROM 64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`）+ `ASSERT`；验收含「段超出区域 ⇒ LLD link-time error」及边界不误杀。
5. **`QEMU-042t`**：补 **加载期 over-size 守卫**——ROM blob >64 KiB / 镜像（含 `.bss`）>RAM ⇒ 显式报错、非零退出（参 `ADR-0004` D1/D2.3）；验收含 over-size 负例与边界不误杀。

**C. 路径引用同步（用户裁定「一并更新全部引用」）**：
- `LLVM-050t`（依赖 += `SPEC-109t`、`INFRA-045t`）、`LLVM-051t`、`LLVM-052t`、`LLVM-053t`、`LLVM-054t`：lit 落点 → `tests/llvm/lit/MC/DADAO/`。
- `INTEG-016t`：入参/输出/验收 → `tests/llvm/codegen/m4/`、`tests/llvm/lit/MC/DADAO/`（去 `UNSUPPORTED:` 接入）、`tests/llvm/codegen/`。
- `INTEG-017m`、`TESTCASES-031m`：产出清单路径同步。
- 里程碑关联任务：`SPEC-108m` 关联任务 3→4（+`SPEC-109t`，目标加 ④ 编码调整）；`INFRA-044m` 关联任务 1→2（+`INFRA-045t`，目标加 ② tests 重排）。
- 跨模块核验注记：`QEMU-043m`（+`SPEC-109t` 编码、over-size 守卫与链接期互兜底）；`LLVM-057m`（+前置 `SPEC-109t`/`INFRA-045t`）。

**D. 依赖/串行链更新**：见本 `k` §任务分解表与 §依赖关系与串行纪律（新增 `SPEC-109t`/`INFRA-045t` 行；调整 `SPEC-106t`/`LLVM-050t`/`QEMU-042t`/`TESTCASES-029t`/`030t` 依赖）。

**本次 3 处澄清（用户答复摘要）**：① 路径引用**全部一并更新**（超出原列 5 份）；② `tests/lit/E2E`/`tests/scripts` 去向由架构师裁定——**`tests/lit/E2E`→`tests/e2e/lit/`**（在用户列出的 `e2e` 桶内）、`tests/scripts` 保持原位；③ L3「暂不接门控」= **单独 m4 清单（M3 驱动不读）**。

**待裁定点**：
1. **本 `k` 状态**：修订后是否需将 `SPEC-104k` 回退 `待验收` 并请 reviewer **重新交叉审查**（新增/修订任务书尚未经 reviewer 审查）；当前保持 `已验证` 未改。建议由主会话在 `/plan` 级复核后确定。
2. **`INFRA-045t` 的 E2E 落点**：架构师裁定 `tests/lit/E2E → tests/e2e/lit`（用户原结构未列 `llvm/lit/E2E`）；若用户希望全部 lit 套件集中于 `tests/llvm/lit/`，可改为 `tests/llvm/lit/E2E/DADAO`。
3. **`SPEC-106t` 承载 `not`/`neg` 向量的边界**：`not`/`neg` 替代功能（`xnor`/`sub.sX`）向量归 `SPEC-106t`（用户指示），而 `set.*` 展开等归 `TESTCASES-029t`/`030t`；若希望测试统一归 testcases 模块，需再调整。
4. **`adr-0004` 注记同步**：`SPEC-109t` 含 `ADR-0004`「全零字 UNDI」**注记**同步（依据 `ADR-0012 D3.5` 明确的落地项）；若其中涉及 **decision 语义**，须**用户逐条确认**后方可改（任务书已写明「停下报告」边界）。
5. **`spec/Process-05 §6` 落点文档过期**：该节现行文为「L1：`tests/lit/MC/Dadao/`……L3：`tests/codegen/`」，`INFRA-045t` 重排后应为 `tests/llvm/lit/MC/DADAO/`、`tests/llvm/codegen/`。因 `ADR-0012 D4`（仅 spec 模块任务可改 `spec/`），`INFRA-045t` 不得改之 ⇒ 需**另立 spec 模块同步任务**（或在既有 spec 任务中并入），否则 `Process-05 §6` 与实现落点不符。建议主会话裁定。

**取代声明（追加，不改写）**：本修订记录**取代**完成区「新发现 2/3」（TESTCASES 暂存 `tests/lit/MC/Dadao-m4/`/`tests/codegen-elf/` 的落点决定）与「遗留问题」中「TESTCASES 落点长期性」一项——新落点分别为 `tests/llvm/lit/MC/DADAO/`（`UNSUPPORTED:` 标记）与 `tests/llvm/codegen/m4/`（独立 m4 清单）；旧文保留为历史记录。

## 修订记录（2026-10-06·2，用户逐条确认）

**背景**：承接上一条「修订记录（2026-10-06）」后，用户 2026-10-06 **二次裁定**。**用户原话（原文引用）**：「**`not`/`neg` 功能向量单独一个 `TESTCASES`；`Process-05 §6` 落点同步单独一个 `SPEC`**」。本记录**追加**，不改写前述正文与审阅记录。

**依据（原样引用）**：
- `ADR-0013 D11`（2026-10-06 增补，`Accepted`）——删 `not.{b,w,t,o}`（用 `xnor.o`/`xnor.X`）、`neg.{b,w,t,o}`（用 `sub.sX`）。
- `ADR-0012 D4`（`Accepted`）——「只有 spec 模块的任务才能修改 `spec/` 下的文件」（`SPEC-110t` 的模块依据）。
- `ADR-0012 D3 第 5 项`（`Accepted`）——落地项含 `ADR-0004`「全零字 UNDI」注（`SPEC-109t` 的注记依据）。

**A. 新建（2 份）**：
- `.tao/tasks/testcases/TESTCASES-032t-not-neg功能向量.md`（testcases / M4）——**`not`/`neg` 功能向量**（测**底层真实指令**：`not`→`xnor.o`（仅 64 位；窄位宽 `xnor.b/w/t` 已由 `SPEC-069t` 删除，`.b/.w/.t` **不适用**）；`neg`→`sub.sb/sw/st/so`）；**L1** 编码/往返落 `tests/llvm/lit/MC/DADAO/`（`UNSUPPORTED:` 标记）、**L3** 执行落 `tests/llvm/codegen/m4/`（独立 m4 清单）；期望值**独立派生自 `spec/`/`contracts/opcodes.yaml`**；扩展 `029t`/`030t` 的共享 validator；**暂不接门控**。
- `.tao/tasks/spec/SPEC-110t-Process-05落点路径同步.md`（spec / M4）——`spec/Process-05-里程碑TDD规范.md §6` 的**示例路径**随 `INFRA-045t` 重排同步为 `tests/llvm/lit/MC/DADAO/`、`tests/llvm/lit/CodeGen/DADAO/`、`tests/llvm/codegen/`（+`m4/`）、`tests/qemu/`、`tests/e2e/lit/` 等；只改 §6 路径、不改规范语义；`make check`（`check-spec-refs`）EXIT=0。

**B. 调整 `SPEC-106t`（只做 spec 文本，移除向量）**：
- **移除**原输出项 4「新增 `not`/`neg` 底层功能专门测试」与验收标准 3「替代功能向量」；新增约束「**不产向量**：专门向量归 `TESTCASES-032t`」。
- 依赖 `SPEC-109t`、`INFRA-045t` **+= `SPEC-110t`**（体例：`Process-05 §6` 落点先行确定，`spec/README` 投影路径与之对齐）；**不** += `TESTCASES-032t`（见下 E）。
- 反例门控中的「`not` 替代向量期望字节」反例改为 spec 文本反例（删去 `Toolchain-01 §6` 某被删项替代写法）；完成区用户裁定注记补 ③「本任务不产向量」。

**C. 采纳前一条 3 项裁定**（对应上一条「待裁定点」2/3/4）：
1. **`SPEC-106t` 不产向量**（归 `TESTCASES-032t`）——待裁定点 3 定案。
2. **`INFRA-045t` 的 E2E 落点 = `tests/e2e/`**（跨组件，**不塞** `llvm/`）——待裁定点 2 定案；与 `INFRA-045t` 现状（`tests/lit/E2E → tests/e2e/lit`）一致，**无需改** `INFRA-045t`。
3. **`adr-0004`「全零字 UNDI」注记随 `SPEC-109t`**（**非** decision 变更）——待裁定点 4 定案；与 `SPEC-109t` 输出项 10（注记同步，边界「若涉 decision 语义则停下报告」）一致。

**D. 一致性联动（超出字面清单，供复核／可回退）**：
- `TESTCASES-031m`：关联任务 2→3（+`TESTCASES-032t`），目标加 ③、核验产出与覆盖矩阵补 `not`/`neg`。
- `SPEC-108m`：关联任务 4→5（+`SPEC-110t`），目标加 ⑤、核验补 `Process-05 §6` 路径同步。
- `INTEG-016t`：依赖 += `TESTCASES-032t`；入参/接入 L1 向量/`m4` 用例说明补 `TESTCASES-032t`。
- `INTEG-017m`：跨模块核验补 `TESTCASES-032t`。
- `TESTCASES-029t`：边界指针由「专门向量归 `SPEC-106t`」改为「归 `TESTCASES-032t`」（被删伪指令 unrecognized 反例仍留本任务）。

**E. 依赖决策（"（如需）"答复，按实际定）**：
- **`TESTCASES-032t` 依赖**：`SPEC-106t`、`INFRA-045t`、`TESTCASES-029t`、`TESTCASES-030t`——复用/扩展二者建立的落点与 validator（`validate_mc_vectors.py`/`validate_elf_vectors.py`），故**串行于 `029t`/`030t`**。
- **`SPEC-106t` 不 += `TESTCASES-032t`**：向量移出后无依赖，且 `032t` 依赖 `106t`（职能/落点），若反向加入会**成环**；**+= `SPEC-110t`**（体例：落点路径先定）。

**F. 路径引用同步**：`SPEC-104k` §任务分解表、§依赖关系与串行纪律、§分解理由已加入 `SPEC-110t`/`TESTCASES-032t`；`SPEC-108m`/`TESTCASES-031m`/`INTEG-016t`/`INTEG-017m` 产出/关联路径同步（见 D）。

**取代声明（追加，不改写）**：本记录**取代**上一条「修订记录（2026-10-06）」中 **B.1「`SPEC-106t` … 新增 `not`/`neg` 替代功能专门向量」**与 **待裁定点 3「`not`/`neg` 向量归 `SPEC-106t`」**——新归属为 `TESTCASES-032t`；旧文保留为历史记录。

**待裁定点（本记录）**：
1. **本 `k` 状态**：修订后是否回退 `待验收` 并请 reviewer **重新交叉审查**（新增/调整任务书尚未经 reviewer 审查）；当前保持 `已验证` 未改（同前一条待裁定点 1）。
2. **`TESTCASES-032t` 与 `029t`/`030t` 的 validator 复用 vs 独立**：本记录采取「**复用并扩展**共享 validator（串行）」。若用户希望 `not`/`neg` 向量**独立 oracle 脚本**（不耦合 `029t`/`030t`），需再调整依赖与产出。
3. **`not.b/w/t` 无底层替代**：窄位宽 `xnor.b/w/t` 已由 `SPEC-069t` 删除 ⇒ `not.b/w/t` **无**对应真实指令，`TESTCASES-032t` 仅测 64 位 `not`（`xnor.o`）。若需覆盖 `not.b/w/t` 语义，须另议（超出 `ADR-0013 D11` 的「用 `xnor.X`」措辞）。

## 审阅记录（续）

#### 第 2 轮 reviewer 规划审查（增量，2026-10-06）

**审查范围**：修订记录（2026-10-06 / ·2）的增量——新增 4 份任务书（`SPEC-109t`、`SPEC-110t`、`INFRA-045t`、`TESTCASES-032t`）、修订 18 份已有任务书/里程碑、`ADR-0012 D3.5` 增补。

**重跑记录**：

1. **任务书集合（25 份 M4 任务书 + 1 份 k）**：
   ```bash
   find .tao/tasks/ -name '*.md' | grep -E '(SPEC-10[5-9]|SPEC-110|INFRA-04[3-5]|LLVM-05[0-7]|QEMU-04[2-3]|TESTCASES-0(29|30|31|32)|INTEG-01[6-7])' | sort | wc -l
   # → 26（含 SPEC-104k）
   ```
   逐条核对：
   - spec（6t + 1m）：SPEC-105t/106t/107t/109t/110t + SPEC-108m ✓
   - infra（2t + 1m）：INFRA-043t/045t + INFRA-044m ✓
   - llvm（7t + 1m）：LLVM-050t~056t + LLVM-057m ✓
   - qemu（1t + 1m）：QEMU-042t + QEMU-043m ✓
   - testcases（3t + 1m）：TESTCASES-029t/030t/032t + TESTCASES-031m ✓
   - integ（1t + 1m）：INTEG-016t + INTEG-017m ✓
   - **合计 25 份任务书（19t + 6m）+ 1 份 k = 26 文件。无缺无多，编号无碰撞**。EXIT=0。
   - 注：完成区旧文写「21 份任务书」为修订前历史记录（修订记录取代声明已标注），实际 25 份。

2. **依赖链无环**：
   - `TESTCASES-032t` → `SPEC-106t`（单向）：032t 依赖 106t，106t **不**依赖 032t。**无环** ✓
   - `INFRA-045t` → `SPEC-110t` → `SPEC-106t`：链正确（SPEC-110t 依赖 INFRA-045t；SPEC-106t 依赖 SPEC-110t）。✓
   - LLVM 链 `050t→051t→052t/053t/054t/055t→056t` 严格串行。✓
   - `SPEC-109t` 无依赖（M4 链首）；`LLVM-050t`/`QEMU-042t` 依赖之。✓
   - `INTEG-016t` 依赖 5 项（含 `TESTCASES-032t`），最后。✓
   - 任务文件实际依赖与表逐条一致（抽查 SPEC-106t=`109t/045t/110t`、TESTCASES-032t=`106t/045t/029t/030t`、INTEG-016t=`056t/042t/029t/030t/032t`、TESTCASES-029t=`106t/045t`、TESTCASES-030t=`105t/045t`）。✓

3. **落点一致**：
   - LLVM 050t~054t 验收/lit 落点均为 `tests/llvm/lit/MC/DADAO/`（新路径）。✓
   - TESTCASES-029t/030t/032t 落点为 `tests/llvm/lit/MC/DADAO/` + `tests/llvm/codegen/m4/`（`UNSUPPORTED:` + 独立 m4 清单）。✓
   - INFRA-044m 提到旧路径在「无残留」检查语境中（应被清除的旧路径）。✓
   - **SPEC-109t** 输出段使用 `tests/lit/MC/Dadao/`——**预期**（109t 在 INFRA-045t 之前执行，改迁移前文件）。✓
   - **INTEG-016t** line 18 引用 `tests/codegen/` 为 Process-05 §6 当前文（SPEC-110t 执行前）。SPEC-110t 先于 INTEG-016t 执行（经 032t→106t→110t），届时已同步。**非阻塞**。✓
   - **无残留旧路径在执行后任务书的输出/验收段中**。✓

4. **`ADR-0012 D3.5` 与 `SPEC-109t` 逐字一致**：
   - ADR-0012 D3.5（line 47）：①删 `illi`（ILLI 保留）、②`fence ha 0x01→0x00`（`0x77040000→0x77000000`）、③`swym ha 0x02→0x22`（`0x77080000→0x77880000`）；`op=0x77` 不变。✓
   - SPEC-109t line 15 逐字段对齐 ✓
   - `swym` 算术：`0x77<<24 | 0x22<<18 = 0x77880000`（`python3` 确认）✓
   - `fence` 算术：`0x77<<24 | 0x00<<18 = 0x77000000`（确认）✓

5. **`SPEC-106t` 不产向量**：
   - line 13：「不重新决策、不产向量」✓
   - line 28：「不产向量（用户裁定）…专门向量归 `TESTCASES-032t`」✓
   - line 54：「本任务不产向量…移出本任务，归 `TESTCASES-032t`」✓
   - `TESTCASES-032t` 承担 `not`/`neg` 的 L1+L3 且期望值独立派生（引用 `contract-isa`/`contracts/opcodes.yaml`）。✓

6. **`SPEC-104k` 修订记录完整性**：
   - 修订记录（2026-10-06）：A（2 份新建）/B（5 份修订）/C（路径同步）/D（依赖更新）+ 取代声明 + 5 项待裁定点。✓
   - 修订记录（2026-10-06·2）：A（2 份新建）/B（SPEC-106t 调整）/C（3 项裁定采纳）/D（联动）/E（依赖决策）/F（路径同步）+ 取代声明 + 3 项待裁定点。✓
   - **未改写**既有完成区/审阅记录（旧文保留，取代声明明确标注）。✓

7. **无残留**：
   ```
   $ make check-no-residue 2>&1
   check-no-residue: PASS
   EXIT=0
   ```
   ```
   $ git status --short
   M  .tao/adr/adr-0012-simrisc-0.5.4-update.md
   M  .tao/tasks/infra/INFRA-044m-*.md
   M  .tao/tasks/integ/INTEG-016t-*.md
   M  .tao/tasks/integ/INTEG-017m-*.md
   M  .tao/tasks/llvm/LLVM-050t-*.md ... LLVM-057m-*.md（8 份）
   M  .tao/tasks/qemu/QEMU-042t-*.md / QEMU-043m-*.md
   M  .tao/tasks/spec/SPEC-104k-*.md / SPEC-106t-*.md / SPEC-108m-*.md
   M  .tao/tasks/testcases/TESTCASES-029t-*.md ... TESTCASES-031m-*.md（3 份）
   ?? .tao/tasks/infra/INFRA-045t-*.md
   ?? .tao/tasks/spec/SPEC-109t-*.md
   ?? .tao/tasks/spec/SPEC-110t-*.md
   ?? .tao/tasks/testcases/TESTCASES-032t-*.md
   ```
   改动仅 `.tao/tasks/**`（18 M + 4 ??）+ `.tao/adr/adr-0012-*.md`（1 M）。**无其它改动**。✓

8. **里程碑联动**：
   - `SPEC-108m`：关联任务 5 个（含 `SPEC-109t`/`SPEC-110t`），目标含 ④编码调整 + ⑤路径同步。✓
   - `TESTCASES-031m`：关联任务 3 个（含 `TESTCASES-032t`），目标含 ③`not`/`neg`。✓
   - `INFRA-044m`：关联任务 2 个（含 `INFRA-045t`）。✓
   - `QEMU-043m`：跨模块注记含 `SPEC-109t` 编码 + over-size 守卫。✓
   - `LLVM-057m`：注记含前置 `SPEC-109t`/`INFRA-045t`。✓
   - `INTEG-017m`：跨模块注记含 `TESTCASES-032t`。✓

**判决**：**Accepted**

- 25 份 M4 任务书全部存在且编号无碰撞（完成区旧「21」为修订前历史记录，取代声明已标注，非阻塞）。
- 依赖链无环：`TESTCASES-032t→SPEC-106t` 单向；`INFRA-045t→SPEC-110t→SPEC-106t` 链正确；LLVM 链严格串行；`INTEG-016t` 最后（含 032t）。
- 落点全部统一为新路径；SPEC-109t 的旧路径描述为迁移前输入（M4 链首）；INTEG-016t 的 Process-05 引用将在 SPEC-110t 执行后同步。非阻塞。
- ADR-0012 D3.5 与 SPEC-109t 逐字段一致（`fence`→`0x77000000`、`swym`→`0x77880000`、删 `illi`、ILLI 保留）。
- SPEC-106t 明确「不产向量」（3 处）；TESTCASES-032t 承担 `not`/`neg` L1+L3 且独立派生。
- 修订记录完整（A/B/C/D 清单 + 取代声明 + 待裁定点）；未改写既有内容。
- `make check-no-residue` EXIT=0；git 无非预期改动。
- 里程碑联动全部到位。

**待裁定点 reviewer 意见**（供用户裁）：

1. **本 `k` 状态**：当前 `待验收`，建议直接 `/complete` 收尾置 `已验证`——本次审查已覆盖全部增量，无需再等。
2. **`TESTCASES-032t` validator 复用 vs 独立**：建议**保持复用并扩展**（当前设计）——共享 validator 减少维护面，032t 串行于 029t/030t 已保证时序；独立 oracle 仅在 validator 接口不稳定时才有必要。
3. **`not.b/w/t` 无底层替代**：建议**接受当前设计**（仅测 64 位 `xnor.o`）——窄位宽 `xnor.b/w/t` 已删是既定事实，`ADR-0013 D11` 的「用 `xnor.X`」措辞可覆盖 `.o`；若需覆盖 `.b/.w/.t` 语义属新能力，超出 M4 范围。
4. **`SPEC-106t` 依赖判定**：当前 `SPEC-106t` 依赖 `SPEC-109t`/`INFRA-045t`/`SPEC-110t`，**不**依赖 `TESTCASES-032t`（032t 依赖 106t，单向）。设计正确，无环。

## 修订记录（2026-10-06·3，用户逐条确认）

**背景**：承接「修订记录（2026-10-06·2）」后，用户 2026-10-06 **三次裁定**：① 测试产物落点与留存规则；② 里程碑「INTEG 开启 / INTEG 结束」闭环（**M5 起**）；③ **M1–M4** 由 SPEC 模块 `SPEC-*k` 开启（历史保留）。本记录**追加**，不改写前述正文与审阅记录。

**依据（原样引用用户裁定）**：

- **① 测试产物落点与留存**：「测试产物落点**按测试本身定，不强制**；**若某模块的测试路径固定 → 放该模块目录下**（如 `tests/llvm/...`、`tests/qemu/...`）；**否则统一放 `.dadao/tests/`**（`ADR-0016 D6`）。**不强制留存**。」
- **② 里程碑生命周期**：「里程碑采用 **「INTEG 开启 / INTEG 结束」闭环**：**开启** = INTEG 模块的规划 `k` 任务（产出里程碑定义 `milestones.md` + 前置 ADR + 任务分解 + 串行链）；**执行** = 各模块任务串行链（同改共享文件串行；模块内 `m` 就近核验）；**结束** = INTEG 模块的 `m` 任务（集成门槛），依赖的模块 `m` 均 `里程碑` ⇒ 主会话置项目里程碑 `达成`；**归档** = `Process-04 §2` 台账梳理 → §3 判据 → 归档（用户确认提交）。其它模块（spec/llvm/qemu/testcases/infra）各放一个 `m` 结束点。**历史说明**：**M1–M4 由 SPEC 模块 `SPEC-*k` 开启**（历史做法，保留不改）；**M5 起**采用 INTEG 闭环。」（其中 §2/§3 为 `Process-04` **调整前**编号；调整后对应 §3/§4。）

**A. 新建（1 份）**：

- `.tao/tasks/infra/INFRA-046t-测试产物落点与留存统一.md`（infra / M4）——修正现状偏差：`test-codegen` 运行产物由 `.work/log/integ/codegen-e2e`（既非模块下、也非 `.dadao/tests/`）改到**模块固定路径** `tests/llvm/codegen-e2e/`（依规则「模块测试路径固定 ⇒ 落该模块目录下」；被否方案 `.dadao/tests/codegen-e2e/` 为**无固定模块路径**时的兜底）；同步 `Makefile`（`CODEGEN_E2E_WORK`）+ `tools/integ/run_codegen_e2e.py`（`DEFAULT_WORK_DIR`）+ `.gitignore`；保留探针/harness 自清行为（不强制留存）。

**B. 规范修订（2 份，`spec/`；用户裁定落地）**：

1. `spec/Process-04-里程碑归档规范.md`：正文**前部**新增 **§1「里程碑生命周期（开启 → 执行 → 收敛 → 归档）」**（INTEG 闭环约定 + M1–M4 历史说明），原 §1..§8 **顺延为 §2..§9**，全篇内部 `§` 引用同步。
2. `spec/Process-05-里程碑TDD规范.md §6`：增补「**测试产物落点与留存**」规则（落点按测试定、模块固定则落模块下、否则 `.dadao/tests/`；不强制留存），保留原 L1/L2/L3 落点说明。

**C. 联动（超出字面清单，供复核／可回退）**：

- `INFRA-044m`：关联任务 2→3（+`INFRA-046t`），目标加 ③（测试产物落点统一）、核验补该项。
- `Process-04` 外部引用同步（非归档、非历史记录）：`.tao/knowledge/{lessons.md,issues.yaml,milestones.md}` 的 `Process-04 §2` → `§3`（附顺延说明）。
- `.tao/archive/**`（历史归档）**不改写**（`AGENTS.md`：历史记录不改写）——其 `Process-04 §N` 引用保留旧编号，属冻结历史。

**D. 依赖/串行链更新**：本 `k` §任务分解表新增 `INFRA-046t` 行；§依赖关系与串行纪律补「`INFRA-046t` 依 `INFRA-045t`」；`INFRA-044m` 依赖列 += `046t`。

**E. 执行与验证（engineer，2026-10-06·3）**：

- **改动清单（7 改 + 1 新）**：① `spec/Process-04-里程碑归档规范.md`（新增 §1 + 原 §1..§8 顺延为 §2..§9 + 内部 `§` 引用同步）；② `spec/Process-05-里程碑TDD规范.md §6`（增补「测试产物落点与留存」）；③ `.tao/tasks/infra/INFRA-046t-测试产物落点与留存统一.md`（**新建**）；④ `.tao/tasks/infra/INFRA-044m-M4-infra里程碑.md`（关联/目标/核验）；⑤ 本 `k`（任务表 + 串行链 + 本记录）；⑥ `.tao/knowledge/milestones.md`、⑦ `.tao/knowledge/lessons.md`、⑧ `.tao/knowledge/issues.yaml`（`Process-04 §2` → `§3` 引用同步，附顺延说明）。
- **门控真实输出**：`make check` **EXIT=0**（`lit` 34/34，`repository checks: PASS`）；`make check-spec-refs` **EXIT=0**（`Check 1`/`Check 2` 均 0 violations）；`make check-no-residue` **EXIT=0**；`git status` 仅上述 8 文件。
- **engineer 自审（自主逐行）**：修 2 处笔误（「产出**租**里程碑定义」→「产出里程碑定义」；「上**表** INTEG 闭环」→「上述」）；补漏 2 处 `Process-04 §2`→`§3`（`milestones.md` M3 达成行 / M2 归档前置行）；确认 `Process-04` 全部内部 `§` 引用顺延一致（正文头 §8、新 §1 的 §3/§4、§4 的 §5/§7、§5 落点树的 §6/§6/§8/§4.4/§7、§9 的 §8）；`.tao/archive/**` 引用**按历史不改写保留**。

**待裁定点（本记录）**：

1. **`INFRA-046t` 落点选择**：任务书**明确选择 `tests/llvm/codegen-e2e/`**（模块固定路径，理由见任务书）；若用户更倾向 `ADR-0016 D6` 的兜底根 `.dadao/tests/codegen-e2e/`（gitignored、无需 `.gitignore` 改动），请裁定。
2. **`Process-04` 编号顺延 vs 不改编号**：本记录按用户指示「顺延原 §1..§8」执行；`.tao/archive/**` 旧引用保留（历史冻结）。若希望归档引用也回溯更新，需另立任务（会改动历史文件）。
3. **`Process-05 §6` 与 `SPEC-110t` 的关系**：本记录在 §6 增补「落点与留存」规则；`SPEC-110t` 仍按原计划同步 §6 的**示例路径**（旧路径 `tests/lit/MC/Dadao/`/`tests/codegen/` → 新路径）——两者不冲突，示例路径留待 `SPEC-110t`。

## 修订记录（2026-10-06·4，用户逐条确认）

**背景**：`LLVM-056t`（DADAO LLD target + `tests/scripts/dadao.lds`）**已验收、已提交**后，事后发现 `dadao.lds` 的 `FILEHDR PHDRS` 使 LLD 把 ELF 头放在最低 section（`.text` = RAM 基址 `0xffff_0000_0000`）**下方一页**，首个 `PT_LOAD` 落 `0xFFFEFFFFF000`（**越出 RAM**），与 `ADR-0004 §D2.3`「任一 `PT_LOAD` 装载区间越出映射区域 ⇒ 报错非零退出」冲突（`ISS-155`）。用户 2026-10-06 逐条确认处置方案。本记录**追加**，不改写前述正文、任务分解表与审阅记录。

**用户原话（原样引用）**：

1. 「B1」= 采用方案 B1：**去掉 `FILEHDR PHDRS`**（不采用 A「加载器放行头部页」、不采用 B2「`.text`/`e_entry` 抬 64 KiB 占位」）。
2. 「1」= 页大小问题**并入本波一起做**（选项①）：`DADAO` target 设 `defaultMaxPageSize = 0x10000`（DADAO 页 = 64 KiB，依据 `spec/DADAO-12 §2.2.1`、`spec/DADAO-22 §SBI_PTW_HANDLE_FAULT` 的 64 KiB page_mask）。
3. 「ADR落点不重要，重要的是，这些decision不应该影响后面的完整linker的实现」← **硬约束**。ADR 落点由主会话定为 **`ADR-0003 §D5`**。

**A. 新建（2 份）**：

- `.tao/tasks/spec/SPEC-112t-去FILEHDR-PHDRS与64KiB页大小决策.md`（spec / M4）——**决策/正文文本**：`ADR-0003 §D5` 就地修订（`## 修订` 加 `rev. 2026-10-06`：三条 decision + 被否方案 A/B2 + scope 限定）、`contract-elf §6.1.2` 删除「`FILEHDR PHDRS` 使 `.text` file-offset 0」并改写、`contract-elf §5` 补 `p_align` = 64 KiB（目标默认、可覆写）、`milestones.md:78` 同措辞修正、`ISS-155` 结案。
- `.tao/tasks/llvm/LLVM-058t-dadao.lds去FILEHDR与页大小默认.md`（llvm / M4）——**实现 + 证据**：`tests/scripts/dadao.lds` 去 `FILEHDR PHDRS`；`DADAO.cpp` ctor 加一行 `defaultMaxPageSize = 0x10000;`；重建 `lld` + 重导出补丁 + `changelog`；重跑并更新链接证据（含反向证明：启用 `FILEHDR PHDRS` 仍可链接、`-z max-page-size` 仍可覆写）。

**B. 依赖**：`LLVM-058t` **依赖 `SPEC-112t`**（spec-first；`SPEC-112t` 无依赖）。

**C. 硬约束（中性/不约束完整 linker；用户原话「这些decision不应该影响后面的完整linker的实现」）**：两份任务书均须表述为「**M4 裸机路径 `dadao.lds` 不使用 `FILEHDR PHDRS`**」（**LLD 的 `FILEHDR PHDRS` 能力原样保留**，不得写成「DADAO ELF 头永不进内存」）；`p_offset`「**不要求**为 0、**不禁止**为 0」；`p_align`「**目标默认** = 64 KiB、**可被 `-z max-page-size` 覆写**」（非硬编码不变式）；只加 `defaultMaxPageSize` 一行、**不动** `DADAO.cpp` 其它函数；`ADR-0019` 的「本期禁用 relaxation / 4 类 reloc」保持原样。

**D. 跨模块提示**：去 `FILEHDR PHDRS` 后首段回到 RAM 内（`0xFFFF00000000`），`ISS-155` 原「头部页落在 RAM 之下」问题根除；新布局（`p_align = 64 KiB` / 首段 `p_offset = 0x10000`）为 `QEMU-042t` ELF 加载器 / `INTEG-016t` 的**输入**，其任务书按需对齐（不改 decision 语义）。

**待裁定点（本记录）**：

1. **本 `k` 状态**：修订后是否回退 `待验收` 并请 reviewer **重新交叉审查**（新增 2 份任务书尚未经 reviewer 审查）；当前保持 `已验证` 未改（同前各条待裁定点）。
2. **`ISS-155` 结案口径**：本记录按「去 `FILEHDR PHDRS` 后根除」结案；若要求保留「记录新布局供 QEMU/integ 对齐」的开放项，可另立 issue（不阻塞）。

#### reviewer 追加确认（修订记录2026-10-06·4）

**审查范围**：本轮追加登记（修订记录2026-10-06·4）——新建 `SPEC-112t`/`LLVM-058t` 两份任务书。

**确认项**：
- 追加登记只新增修订记录，未改写正文/任务表（任务表仍27行，不含 SPEC-112t/LLVM-058t）✓
- 用户原话逐字落盘（B1/1/ADR落点三条）✓
- 与前几轮修订记录（·1/·2/·3）的追加模式一致 ✓
- 待裁定点2项已标注 ✓
- 两份新建任务书的下发前预检结论：**Accepted**（详见各自任务书审阅记录）
