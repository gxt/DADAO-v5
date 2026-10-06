# 项目里程碑路线图

项目级里程碑（跨模块），由各模块的里程碑支撑（模块里程碑见 `.tao/tasks/<module>/` 的 `m` 文件）。主会话在依赖的模块里程碑均达成为 `里程碑` 后，将本项目里程碑置为 `达成`。路线参考 DADAO-0628（`.cache/refs/DADAO-0628`）。

| 项目里程碑 | infra | spec | testcases | golden | llvm | qemu | integ | gem5 | sail | 状态 |
> **M4 达成（2026-10-07，主会话实测核验）**：门槛 `make test-elf` **5/5**；6 个模块 `m`（`SPEC-108m`/`INFRA-044m`/`LLVM-057m`/`QEMU-043m`/`TESTCASES-031m`/`INTEG-017m`）全部置 `里程碑`；`make check`/`check-lit`(60/60)/`test-codegen`(15/15)/`test-elf`/`check-no-residue`/`check-patch-tree`(89)/`check-qemu-semantics` 全 EXIT=0（`.work/log/integ/m4-closure/`）。前置 `SPEC-105t` 补置已验证；`SPEC-111t` 归档收口。M4 任务书归档待立归档任务（`Process-04 §3`，同 M1–M3 体例）。

| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | **`INFRA-014m` ✅ 里程碑** | **`SPEC-011m` ✅ 里程碑** | **`TESTCASES-012m` ✅ 里程碑** | — | **`LLVM-015m` ✅ 里程碑** | **`QEMU-021m` ✅ 里程碑** | **`INTEG-004m` ✅ 里程碑** | — | — | **✅ 达成** |
| M2 | **`INFRA-034m` ✅ 里程碑** | **`SPEC-095m` ✅ 里程碑** | **`TESTCASES-025m` ✅ 里程碑** | — | **`LLVM-032m` ✅ 里程碑** | **`QEMU-039m` ✅ 里程碑** | **`INTEG-011m` ✅ 里程碑** | — | — | **✅ 达成** |
| M3 | **`INFRA-036m` ✅ 里程碑** | **`SPEC-099m` ✅ 里程碑** | **`TESTCASES-027m` ✅ 里程碑** | — | **`LLVM-042m` ✅ 里程碑** | — | **`INTEG-013m` ✅ 里程碑** | — | — | **✅ 达成** |
| M4 | **`INFRA-044m` ✅ 里程碑** | **`SPEC-108m` ✅ 里程碑** | **`TESTCASES-031m` ✅ 里程碑** | — | **`LLVM-057m` ✅ 里程碑** | **`QEMU-043m` ✅ 里程碑** | **`INTEG-017m` ✅ 里程碑** | — | — | **✅ 达成** |

> **归档（2026-10-03）**：M1 的 76 个任务书已归档至 `.tao/archive/M1/`（按模块子目录）；M1 时期 changelog/MEMORY 内容见 `.tao/archive/M1/README.md`；**M1 回顾见 `.tao/archive/M1/m1-retrospective.md`**（由 `docs/` 移入）。
>
> **M2 重定义（2026-10-04，用户裁定）**：M2 定为「**规范与接口冻结（Normative Freeze）**」，原「Basic CodeGen」顺延为 **M3**；并**取消「过渡期任务 `M<i>→M<i+1>`」类别**——原 `M1→M2` 任务一律提升为 `M2`（**推翻** 2026-09-25 决议；不立 ADR）。
>
> **归档前置（MUST）**：任何里程碑达成后、**归档前**，须先按 `spec/Process-04 §3`（原 §2，2026-10-06 因新增 §1「里程碑生命周期」顺延）对遗留台账（`.tao/knowledge/issues.yaml` / `lessons.md`）做一次**梳理**（关闭已消解项、校正 `scope`、移出教训类、判定 moot 项、头部同步）；未完成不得归档。
>
> **状态口径**：本表 `状态` 列只有 **`待开始`/`达成`** 两态（模块 `m` 未置则显 `待开始`）；`issues.yaml` 头部的「M2=进行中」是**进度叙述**，二者不矛盾。
>
> **M2 达成（2026-10-04，architect 实测核验）**：M2 门槛 5 条全部满足、各模块 M2 任务均终态 ⇒ 6 个模块 `m` 置 `里程碑`、M2 置 `达成`。核验记录见下「M2 达成核验记录」。
>
> **M3 达成（2026-10-05，主会话实测核验）**：门槛 `make test-codegen` **15/15**；5 个模块 `m`（`INFRA-036m`/`SPEC-099m`/`TESTCASES-027m`/`LLVM-042m`/`INTEG-013m`）全部置 `里程碑` ⇒ M3 置 `达成`。核验命令与退出码见各 `m` 文件「核验记录」及 `.work/log/m3-closure/`（`llc --version`=0、`check-patch-tree`=0/80、`check`=0/34、`check-lit`=0/34、`test-codegen`=0/15、`check-no-residue`=0）。**归档前置**（`spec/Process-04 §3` 完整台账梳理，步骤 3–6；原 §2，2026-10-06 顺延）由 `INFRA-042t` 执行（`已验证`）；归档见下。
>
> **归档（2026-10-04）**：M2 的 150 个任务书已归档至 `.tao/archive/M2/`（按模块子目录）；M2 时期 changelog（61 条）/MEMORY（45 行 + 2 段落）内容见 `.tao/archive/M2/README.md`；**M2 回顾见 `.tao/archive/M2/m2-retrospective.md`**；`issues.yaml` 的 41 条 M2 阶段 closed 项见 `.tao/archive/M2/issues-closed.md`。
>
> **归档（2026-10-05）**：M3 的 41 个任务书已归档至 `.tao/archive/M3/`（按模块子目录）；M3 时期 changelog（35 条）/MEMORY（1 行）内容见 `.tao/archive/M3/README.md`；**M3 回顾见 `.tao/archive/M3/m3-retrospective.md`**；`issues.yaml` 的 56 条 M3 阶段 closed 项见 `.tao/archive/M3/issues-closed.md`。
>
> **M3 重定义（2026-10-04，用户裁定）**：M3 定为 **「Basic CodeGen（纯整数）」**——`llc` 编译标量整数/指针函数 → MC → 单 TU obj/raw binary → QEMU 执行正确；门槛 `make test-codegen` 全绿。bank 只 `GPRD`+`GPRB`；`RA`/`RF` 仅「保留不分配」；无需链接器（ADR-0003 §D5 单 TU + 最小重定位）。**M4（后续，未规划）**顺延：FP/RF codegen、完整调用约定（`ISS-005`，含变参/聚合/多返回/sret）、完整重定位（`ISS-008`）、clang targetinfo/driver。M3 任务分解见 `.tao/tasks/spec/SPEC-096k-M3启动与分解.md`；M3 的 `qemu` 列原填 `—`（执行层已由 M1 冻结、无独立 qemu 模块里程碑）——**2026-10-04 追加**：新增指令 `sub.o rd,rb,rb` 的 QEMU 语义翻译 `QEMU-040t`（M3 前置，与 `SPEC-100t` 同原子落地集，由 `INTEG-012t`/`INTEG-013m` 门控），本列仍填 `—`。
>
> **M4 重定义（2026-10-05，用户裁定）**：M4 定为 **「ELF 文件支持 + LLD 链接 + 汇编器遗留收口」**——把工具链从 M3 的「raw-bin 单 TU 捷径」升级为**规范 ELF 产出 + 真实链接**，并清掉 M1/M2 遗留的汇编层欠账。**四块范围**：① **汇编器遗留**（伪指令〔**重定后**〕/`.dd.{b08,w16,t32,o64}` 指导符/`-multiple-to-single`/越界立即数**报错**/ABI 寄存器别名，见 `contract-asm §6/§7/§8/§11`）；② **ELF 产出规范**（`ELFObjectWriter` 注册/`e_flags=1`/`e_machine`→dadao/段布局对齐/**全局数据 `.data`/`.rodata`**，`ISS-038/039/047/117`）；③ **LLD 链接器**（新增 DADAO LLD target：`lld/ELF/Arch/DADAO.cpp`+`Target.{cpp,h}`+`EM_DADAO`/reloc，产 `ET_EXEC`；`ISS-008`；0628 先例）；④ **QEMU ELF 加载**（解析 `Ehdr`/`Phdr`、按 `VA=PA` 装载 LOAD 段、跳 `e_entry`，替代 `objcopy`+trampoline；`ADR-0004` 扩展）。**门槛**：多 TU `ld.lld → ET_EXEC → qemu` 跑对 + ELF 结构断言（`readelf`/`readobj`）+ 汇编层 MC 用例 + M3 15 向量/多段/多文件经新链路 + 差分 + 负例（畸形 ELF 拒绝、reloc 溢出 link-time error）。**参考基线（2026-10-05 用户裁定）**：**主对标 RISC-V 64**（完整工具链/软件系统总纲）；**次要 x86-64/AArch64**（LLD/ELF 基础设施与测试组织）；**端序参考 PPC64 BE（+ s390x）**（64 位大端完整栈）；**双 bank 历史参考 M68K**（BE、32 位，退居次要）。**TDD**：本里程碑起采用**测试驱动开发**（先测试向量/门控、再实现），并需**完善测试向量**（MC 向量 + CodeGen 向量 + 执行向量；**移植对象 = 上述参考**：借鉴其测试**结构**，编码/期望值按 DADAO spec **独立派生**）。**前置（待判）**：重定位类型（`contract-elf §2–§4`）→ **ADR**；伪指令重定 → **spec 修订**；测试向量范围 → **待细化**。**明确不含（留后）**：完整调用约定（变参/聚合/sret/多返回/间接）、**FP/RF**、clang 前端、libc/OS/syscall、semihosting 字符输出、golden model。分解待立（`SPEC-1xxk` 规划任务）。

## M2 达成核验记录

**日期**：2026-10-04　**执行**：architect 实测（命令原样 + 退出码；完整输出见 `.work/log/integ/M2-milestone-make-check.log`、`.work/log/spec/M2-milestone-check-spec-refs.log`、`.work/log/qemu/M2-milestone-probe-03{4..8}t.log`）

| # | 门槛 | 命令 / 证据 | 结果 |
|---|------|-------------|------|
| ① | `make check` 全绿（所有 checker + 反例门控） | `make check` | **EXIT=0**；`repository checks: PASS`；lit 31/31 |
| ② | 投影表「缺口」清零或显式 deferred | `contract-asm.md` 已补齐（`SPEC-091t`）；`DADAO-12/13/22/23` ①列 = `deferred`（`SPEC-092t`）；`Process-02` 三者 = `deferred` | **满足**（4 项） |
| ③ | `spec_cite` / 引用 / 计数全对齐 | `make check-spec-refs` | **EXIT=0**；Check1 680 引用 / 0 失败、Check2 0（76→0，`SPEC-094t`） |
| ④ | FP = 执行层 60/60 + `dst_rd0@FP` + 最小 smoke | `min_rom_probe_03{4..7}t` = 59/77/113/91 全 PASS；`_038t` = 42/42；`smoke_fp.test` PASS | **满足** |
| ⑤ | 偏离台账 6 项 | `.tao/knowledge/MEMORY.md` `## 上游 ↔ v5 偏离台账` | **恰好 6 行**（`SPEC-093t`） |

**各模块 M2 `m`**：`INFRA-034m`、`SPEC-095m`、`TESTCASES-025m`、`LLVM-032m`、`QEMU-039m`、`INTEG-011m`。

**M2 任务终态**：wave 1/2 全部 `已验证`；唯一非终态 M2 任务 = `INTEG-010t`（M2 达成**后**执行的归档收尾，非达成分解）。

**归档前置**：`INFRA-033t`（`Process-04 §3` 台账梳理；原 §2，2026-10-06 顺延）`已验证`；M2 任务书归档由 `INTEG-010t` 在 M2 达成后执行。

> **caveat（非阻断，交主会话复核）**：投影表仍存 3 处字面 `缺口`——`SimRISC-07` 行 ④列 `缺口`（FP oracle/向量待建，2026-10-04 M3 重定义后属 **M4**，未加 `deferred` 字样）、`DADAO-12` 行 ②④列 `缺口（据实）`（据实、无需独立投影）。按 `SPEC-090k` 对门槛②的 4 项界定为满足；若要字面清零，建议将 `SimRISC-07 ④` 改标 `deferred（M3）`（需改 `spec/README.md`，超出本次核验写范围）。

## 里程碑说明

**M1 — MC + QEMU 标量核心 + MC↔QEMU 集成**

目的：`llvm-mc` 能汇编/反汇编全部 M1 指令；`qemu-system-dadao` 能在 MMU-off 裸机模式执行标量程序；独立测试向量经「MC 汇编 → QEMU 执行 → 结果比对」一致，形成 MC↔QEMU 集成闭环。门槛：`make build-mc` / `build-qemu` / `test-interface` 全绿。

**M2 — 规范与接口冻结（Normative Freeze）**

目的：`spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层**机械一致**；FP **实现侧**收口（执行层 + 合法性）；偏离台账成型。为 M3 codegen 提供稳定契约。

门槛：① `make check` 全绿（所有 checker + 反例门控）；② 投影表「缺口」清零或显式 deferred；③ `spec_cite`/引用/计数全对齐；④ FP = 执行层 60/60 + `dst_rd0@FP` + **最小 FP smoke**；⑤ 偏离台账（6 项，见 `MEMORY.md`）。

**范围外（2026-10-04 M3 重定义后改归 M4）**：FP 独立 oracle（`GOLDEN`）、FP 向量（`TESTCASES-024t`）、完整语义 E2E。

**M3 — Basic CodeGen（纯整数）**

目的：`llc` 将**标量整数/指针**函数（LLVM IR）编译为 DADAO 汇编，经 MC → **单 TU** obj/raw binary → `qemu-system-dadao` 执行结果正确（freestanding、same-TU、无链接器）。门槛：**`make test-codegen` 全绿**，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。**范围**（用户裁定 2026-10-04）：bank 只用 `GPRD`+`GPRB`；`RA`/`RF` 仅「保留不分配」；无需链接器（单 TU 自包含 + 最小重定位）。分解见 `.tao/tasks/spec/SPEC-096k-M3启动与分解.md`。

> **M3 CodeGen 取舍点（C1–C17）已定（2026-10-04，用户逐条判定，32 条 decision 经逐一审核通过）**：判定结果见 `.tao/knowledge/project_M3-codegen-choices.md §5`；架构决策固化于单一 **`ADR-0018`**（分组：C1 硬双类、C2 指针 i64 通吃、C4 栈溢出区全局声明序、C5 返回 rb31 + callee 扩展、C7 帧策略条件式/SP-only 默认、C9 DataLayout、C11 SelectionDAG 为主、C13 无 subreg + 大端窄访存、C14 RB 算术落 GPRB、C16 call Defs/RegMask）；C17（无标志位 compare-branch）只落 `LLVM-037t` 任务书约束，不立 ADR。C6（CSR）归 ABI（`SPEC-097t`）。**新增指令 `sub.o_orrr_dbb`（C14 D4 的 `ptr−ptr` 终态）与三条既有 RB 算术指令改名/改编码（`add.o_orrr_bbd`/`sub.o_orrr_bbd`/`cmp.uo_orrr_dbb`）记入 `adr-0012 D9`**（`Accepted`，用户 2026-10-04 逐条确认追加），落地 `SPEC-101t`→`SPEC-100t`→`LLVM-043t`/`QEMU-040t`→`LLVM-035t`。

> **M2 定义变更留下的旧文本已在 2026-10-04 M3 重定义时移除**：M2 曾把「FP 独立 oracle / FP 向量 / 完整语义 E2E」顺延至 M3；用户 2026-10-04 重划边界后，FP/RF 及完整调用约定/完整重定位归 **M4**（见下「M3 重定义」）。

**M4 — ELF 文件支持 + LLD 链接 + 汇编器遗留收口**（规划中）

目的：把工具链从 M3 的「**raw-bin 单 TU 捷径**」升级为「**规范 ELF 产出 + 真实链接**」：`llc → llvm-mc → ld.lld → ET_EXEC → qemu 直接加载执行`；同时清掉 M1/M2 遗留的**汇编层欠账**（伪指令/指导符/汇编器选项/诊断）。

范围：① 汇编器遗留；② ELF 产出规范（含全局数据段）；③ LLD 链接器（**含链接脚本 `dadao.lds`**：地址布局依 **`ADR-0004`**〔RAM 基址 `0xffff_0000_0000` 作 `.text`/entry；段序 `.text→.rodata→.data→.bss`〕、段对齐依 `contract-elf §5`、M4 路径 `dadao.lds` **不使用 `FILEHDR PHDRS`**（头/程序头表只在文件中，不进 guest 内存）、`p_align` **目标默认 64 KiB（可被 `-z max-page-size` 覆写）**）；④ QEMU ELF 加载。**参考**：主对标 **RISC-V 64**；端序参考 **PPC64 BE（+ s390x）**；双 bank 历史参考 **M68K**。

门槛：多 TU `ld.lld → ET_EXEC → qemu` 跑对；ELF 结构断言；汇编层 MC 用例；M3 向量 + 多段 + 多文件经新链路通过 + 差分；负例（畸形 ELF / reloc 溢出）。

**范围外（留 M5+）**：完整调用约定（变参/聚合/sret/多返回/间接）、FP/RF codegen、clang 前端、libc/OS/syscall、semihosting 字符输出、golden model（结果级独立 oracle）。

**前置 ADR**：重定位类型（`contract-elf §2–§4`，`e_flags[7:0]=1` namespace）。**可能需调整 `ADR-0004`**（ELF 的 `e_entry` / 段布局 / 加载约定；当前为 flat-binary 双镜像）。

**reloc/fixup 坑预防（M4 硬约束，源自 `DADAO-0628` 实录）**：① fixup **必须尊重 `IsResolved`**（禁写预链接原始值）；② same-section「快速路径」不可靠则**删掉、退回真重定位**；③ **`rb0`（= 当前 PC）禁作基址/零**；④ 跳转表/间接跳转目标标签**必须显式发射**；⑤ 大常量**不得折入**受限立即数/relocation 字段（先材料化）。

**测试策略（`spec/Process-05` TDD）**：**L1（MC）+ L3（执行）为主、L2（CodeGen 结构）极简**；「**一能力一向量**」（规模 ∝ 能力）；移植**只借结构**、期望值**独立派生自 `spec/`**、**手写少量不批量迁移**；每条向量须能对反例失败。**已定前置**：重定位类型 = `ADR-0019`（Accepted；RELA，`ABS48/REL26/REL20/REL14`，v5 无 −4，一律 max 3 片，禁用 relaxation）；伪指令集收缩 = `ADR-0013 D11`（只留合成型 8 条，删 10 条别名）。

> **M5 起步待办（2026-10-06，用户裁定）**：**M5 阶段开始先处理 install 问题**——落地 `ADR-0016 D1–D11`：host 工具链 → `.dadao/cross-toolchain`（D3/D4/D11）、target sysroot → `.dadao/dadao-unknown-elf`（D5）、`manifests/` 单一真源定位（D7，禁硬编码）、**门控/执行器改从 install 根取可执行**、`.work/` **仅**作 build 区（D9）；并保留「从源码可重建」（D9）。**M4 阶段不强制**；落地任务编号待 M5 规划时再定（不预建任务书）。

> **生成物落点口径（2026-10-06，用户明确）**：运行产物**默认为 `.dadao/tests/`**；**只有"难以放进 `.dadao/`"时**才退到**当前模块对应目录**；判据 = **"能否用配置选项解决"——能配置解决的一律不算"难"，必须放 `.dadao/`**。规范正文落 `spec/Process-05 §6`（M5 补正）。

> **落点规则生效时点（2026-10-06，用户裁定）**：**M4 已完成/在做的测试落点一律不动**；**自 M5 起按新规则**。M5 起步须迁移（判据 = 能配置解决 ⇒ 必进 `.dadao/`）：① `test-codegen` 运行产物 `tests/llvm/codegen-e2e` → `.dadao/tests/codegen-e2e`；② `test-elf` 运行产物（`run_elf_e2e.py` 的 `DEFAULT_WORK_DIR` / `Makefile`）→ `.dadao/tests/elf-e2e`；③ lit 的 `test_exec_root`（现 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）→ `.dadao/tests/lit-output/<name>`。**`.work/log`（日志）与 `.work/evidence`（证据）不算"生成物"、不动**（2026-10-06 用户裁定）。

## M1 模块依赖关系

```
infra ───────────────┐
                     ├──→ llvm ───┐
spec ──→ testcases ──┤           ├──→ integ ──→ M1
                     └──→ qemu ───┘
```

| 依赖边 | 内容 |
| --- | --- |
| `infra` → `llvm`、`qemu` | `build-mc` / `build-qemu` 依赖 infra 的 Makefile、fetch/apply、组件锁、容器 |
| `spec` → `testcases`、`llvm`、`qemu` | ISA 合约、编码表、ABI/ELF 合约、ADR-0003/0004（Test Machine） |
| `testcases` → `llvm`、`qemu`、`integ` | 独立测试向量（encoding/legality/semantic/boundary/overlap）供 MC/QEMU/集成验证 |
| `llvm` ∥ `qemu` | 两者仅依赖 `infra`+`spec`，**可并行**（MC 与 CPU 核心无相互依赖） |
| `llvm` + `qemu` + `testcases` → `integ` | 集成验证（E2E 套件与回归 + 跨模块接口对齐） |
| `integ` → `M1` | 集成闭环达成，M1 置为 `达成` |

关键路径：`infra` + `spec` → `qemu`（或 `llvm`）→ `integ` → M1。

## M1 建议执行顺序

按依赖分层，同层可并行：

**第 1 层 — 基础设施 + 规范基线**（无前置或已部分完成）
- `infra`：`INFRA-002t` → `003t` → {`004t`、`005t`} → `006t` → `007t` → {`010t`、`011t`、`012t`}
- `spec`：`SPEC-002t` → `003t` → `SPEC-004t` → {`005t`、`006t`} → `007t` → {`008t`、`009t`} → `010t`
- 说明：先建 `Makefile`/fetch/锁（infra）与 `ADR-0004`/ELF 合约（spec），解除对下游的阻塞。

**第 2 层 — 测试向量 + 组件基线/骨架**（依赖第 1 层）
- `testcases`（2026-09-15 最终重排）：`TESTCASES-002t`（**返工**：schema 新增 `expected_pc` + inventory + validator；F2/F3/F6/F9）→ `003t`（寄存器间传输与运算，含 F1）→ `004t`（load/store 三 bank）→ `005t`（`br.*` taken/not-taken）→ `006t`（`jump`/`call`/`ret`）→ `007t`（misc）→ `008t`（保留编码 → UNDI，F5）→ `009t`（全量再审计兜底）→ `010t`（缺口消解第一批：reg-arith/logic/shift-extend/compare）→ `011t`（缺口消解第二批：cond-assign/imm-block/ctrl + 门控转严）→ `012m`。F10 分摊到 `003t`~`007t`（各修本任务文件 encoding，不单列任务）；F7 用 `expected_pc` 方案全部转 active。**共享源文件**（`rb-ops`/`ra-ops` 被 `003t`/`004t`；`control-flow` 被 `005t`/`006t`/`007t`）与 `inventory.md` 决定以串行最稳；`{003t→004t}` 与 `{005t→006t→007t}` 目标文件集不相交，**若** inventory 由生成器统一重生成则可并行。旧 `004t`/`005t`/`006t`（覆盖率修复/身份唯一性/地址迁移）已关闭，编号已复用为新任务（见 `.tao/knowledge/issues.yaml`）
- `llvm`：`LLVM-002t` → `003t`（Triple + 最小 build）
- `qemu`：`QEMU-002t` → `003t`（骨架 + `hw/dadao/`）
- 说明：向量层尽早建立，供第 3 层验证；`llvm`/`qemu` 各自先打通「能 build」。

**第 3 层 — MC 后端 + QEMU 核心（+ 各自自测）**（依赖第 2 层，两条线并行）
- `llvm`：`LLVM-004t` → `005t` → `006t` → `007t`（反汇编器）→ `008t`（全量 lit）→ `011t` → `012t`（lit 字节 oracle）（`010t` 已于 2026-09-21 关闭）
- `qemu`：`QEMU-004t` → `005t` → `006t`(合并) → `007t`(拆分) → `008t` → `009t` → `010t` → `011t` → `012t` → `013t` → {`014t`~`019t` 自测/trans lint}（`020t` 已于 2026-09-21 关闭）；`022t`（TB 缺陷修复，依赖 `007t`，可与 `008t`~`020t` 并行）；`023t`（harness `input_state.memory` 按宽度写入，依赖 `016t`）

**第 4 层 — 集成验证**（依赖第 3 层）
- `integ`：`INTEG-002t`（E2E 套件与回归）、`INTEG-003t`（接口对齐）→ `INTEG-004m`

**第 5 层 — 里程碑收敛**
- 各模块 `m` 核验通过后置 `里程碑` → `M1` 置 `达成`

> 建议：第 1、2 层先行（打通构建与向量），第 3 层的 `llvm` 与 `qemu` 并行推进，第 4 层紧随其后。
