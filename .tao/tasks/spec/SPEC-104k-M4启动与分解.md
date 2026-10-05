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
| `SPEC-105t` | `contract-elf §2–§4` 重定位正文（按 `ADR-0019`） | spec | `contract-elf.md` §2–§4 正文（类型/公式/溢出）+ 门控对齐 | 无 |
| `SPEC-106t` | 伪指令集收缩 spec 修订（按 `ADR-0013 D11`） | spec | `spec/SimRISC-00/03/06` + `contract-asm §6` + `MEMORY.md` 偏离台账 | 无 |
| `SPEC-107t` | `ADR-0004` 调整（ELF `e_entry`/段布局/加载约定）〔若需〕 | spec | `adr-0004` 就地修订 + `contract-elf §5/§6` 同步 | `SPEC-105t` |
| `INFRA-043t` | LLD 入构建目标 | infra | `Makefile`（`build-mc`/新目标产出 `ld.lld`）+ 构建证据 | 无 |
| `LLVM-050t` | ELF writer → **RELA** + `e_flags=1` + `e_machine`→dadao + `getRelocType`（4 类） | llvm | `DADAOELFObjectWriter`/`MCCodeEmitter`/`AsmBackend` + lit/`readelf` 证据 | `SPEC-105t` |
| `LLVM-051t` | 伪指令展开（`set.rd/set.rb/set.ft/set.fo`；常量/符号分派） | llvm | AsmParser 展开 + lit MC 证据 | `SPEC-106t`、`LLVM-050t` |
| `LLVM-052t` | `.dd.{b08,w16,t32,o64}` 指导符发射 | llvm | MC 指导符 + lit 证据 | `LLVM-050t` |
| `LLVM-053t` | `-multiple-to-single` 汇编器选项 | llvm | MC 选项 + lit 证据 | `LLVM-051t` |
| `LLVM-054t` | 越界立即数诊断（禁静默环绕） | llvm | AsmParser 报错 + lit 反例 | `LLVM-051t` |
| `LLVM-055t` | 全局数据 lower（`.data`/`.rodata`）+ `ABS48`/RELA fixup | llvm | CodeGen 全局 lower + MIR/`.s` 证据 | `LLVM-050t` |
| `LLVM-056t` | **DADAO LLD target** + 链接脚本 `dadao.lds` | llvm | `lld/ELF/Arch/DADAO.cpp` + `Target.{cpp,h}` + `dadao.lds` + 链接证据 | `INFRA-043t`、`LLVM-050t`、`SPEC-107t` |
| `QEMU-042t` | **QEMU ELF 加载器**（`Ehdr`/`Phdr`/装载/`e_entry`） | qemu | `hw/dadao/` ELF 加载 + 负例（畸形 ELF 拒绝） | `SPEC-107t` |
| `TESTCASES-029t` | L1 MC 向量（伪指令/指导符/选项/诊断/往返） | testcases | `tests/lit/MC/Dadao/` 扩展 + 独立 oracle | `SPEC-106t` |
| `TESTCASES-030t` | L3 执行向量（多 TU/多段/ELF 链路；独立 oracle） | testcases | `tests/codegen/` 扩展 + 期望值 | `SPEC-105t` |
| `INTEG-016t` | 多 TU/多段 E2E + `make test-elf` | integ | `tools/integ/` 驱动 + `Makefile` 目标 | `LLVM-056t`、`QEMU-042t`、`TESTCASES-029t`、`TESTCASES-030t` |
| `SPEC-108m` | M4 spec 里程碑 | spec | `m` 文件 | `SPEC-105t`/`106t`/`107t` |
| `INFRA-044m` | M4 infra 里程碑 | infra | `m` 文件 | `INFRA-043t` |
| `LLVM-057m` | M4 llvm 里程碑 | llvm | `m` 文件 | `LLVM-050t`~`056t` |
| `QEMU-043m` | M4 qemu 里程碑 | qemu | `m` 文件 | `QEMU-042t` |
| `TESTCASES-031m` | M4 testcases 里程碑 | testcases | `m` 文件 | `TESTCASES-029t`/`030t` |
| `INTEG-017m` | M4 integ 里程碑 | integ | `m` 文件 | `INTEG-016t` |

### 依赖关系与串行纪律

- **`spec` 正文先行**：`SPEC-105t`（reloc 正文）→ `LLVM-050t`（ELF writer/reloc）；`SPEC-106t`（伪指令）→ `LLVM-051t`。
- **LLVM 链严格串行**（同改 `components/llvm-project/patches/llvm/lib/Target/DADAO/**` 与 `lld/**`、同一 `.work/source/llvm-project`）：`LLVM-050t → 051t → 052t → 053t → 054t → 055t → 056t`（`050t` 先行；`051t` 依赖 `050t` 的 ELF/reloc 基础；`056t` 最后）。
- **`INFRA-043t`**（LLD 入构建）与 `LLVM-050t` 无共享文件，可**先于** `LLVM-056t` 任意时机，但 `LLVM-056t` 依赖其产物。
- **`QEMU-042t`**（不同仓库）可与 LLVM 链**并行**。
- **`TESTCASES-029t`/`030t`** 按 `Process-05` **先于**对应实现（TDD），但为串行便利，先于 `INTEG-016t`。
- **`INTEG-016t` 最后**（依赖 LLD + QEMU loader + 向量）；`make test-elf` 与 `make test-codegen` 并存（差分对照）。
- **`Makefile`/`contracts/`/`spec/` 改动串行**（`AGENTS.md`「同改共享文件一律串行」）。
- `k ↔ m`：本 `k` 对应 M4；各模块 `m` 在模块任务收敛时核验，M4 由主会话在依赖模块 `m` 均达成后置 `达成`。

### 分解理由

- 按「**契约 → 产物层 → 链接 → 加载 → E2E**」分层，每步以「真实产物（`.o`/`.s`/`.rela`/ELF/链接）+ 重 build + 不回归」为独立验收点。
- `ADR-0019`（reloc）与 `ADR-0013 D11`（伪指令）已固化，`SPEC-105t`/`106t` 只做**正文落地**（不重新决策）。
- 测试（`TESTCASES-029t`/`030t` 独立 oracle）与 E2E（`INTEG-016t`）分离，满足 **Independent oracle**；按 `Process-05` **TDD 先立向量**。

## 说明

- 本 `k` 只做规划，不实现；门槛核验在 `INTEG-017m`（及 M4 项目里程碑）前完成。
- **ADR 提醒**：`ADR-0019`（reloc）与 `ADR-0013 D11`（伪指令）已 `Accepted`；`SPEC-107t` 若调整 `ADR-0004` **仍须用户逐条确认**（已 `Accepted` 的 ADR 改动）。
- 任务书自包含：执行所需事实写入各任务书或引用 v5 自身知识；RISC-V64/PPC64BE/M68K/0628 仅作**只读对照**（内容溯源，非执行依赖）。
- **假设**：M4 内不改 `contract-elf` 之外的 spec 正文（`SPEC-105t` 改 `contract-elf §2–§4`；`SPEC-106t` 改 `SimRISC-00/03/06` + `contract-asm §6`）。（**注**：`SPEC-106t` 的文件范围经用户 2026-10-06 裁定改为**全 `spec/`**，见完成区「新发现 1」，本假设作废。）

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
