# ADR-0027: compiler-rt builtins 支持口径（范围 / 形态 / 策略 / 验证 / 归属）

**状态**：Accepted
**日期**：2026-10-14
**关联**：`ADR-0025`（M8 范围与 Linux 兼容路线；`D4` musl/picolibc 并存、`D6` `P0…P4` 顺序）、`ADR-0026`（动态链接行为口径）、`ADR-0016`（DADAO 安装根与产物布局：`D3` host 工具链 prefix、`D5` target sysroot 根、`D11` install 范围）、`ADR-0005`（组件锁多源：`components/llvm-project` 版本锁）、`ADR-0012 D4`（`spec/` 只读策略：只有 spec 模块任务可改）、任务 `INFRA-078t`（compiler-rt 支持预研；本 ADR 的 `D1`–`D5` **来源** = 该任务书 `§5` 草案）

> **本 ADR 已 `Accepted`（2026-10-14）**：`D1`–`D5` = 用户在 `INFRA-078t §5` 预研草案之上**逐条选择**，经**主会话问答**取得并**逐条确认**（`AGENTS.md`「ADR decision 逐条确认」；`docs/Process-03`）。预研案的「建议」**只是提案**，未经确认的内容**不写入**本 ADR。
> **ADR 不承载规范正文**（`docs/Process-03`）：本文件只记**决策 / 理由 / 被否方案**；`builtins` 的符号语义 / ABI / 编译口径**内容层真源 = `compiler-rt` 上游源码**，不在本 ADR 重述。
> **载体分工**：「**ISA 指令扩展**」（是否 / 哪些新指令值得进 `SimRISC` ISA）**不在本 ADR**，另立预研任务（`SPEC-141t`）；其结论**不由本 ADR 预设**。

## Context（背景）

- M8 主线 = 「**无内核的 Linux 用户态栈**」（`ADR-0025`）；`D4` 裁定 **musl 与 picolibc 并存** ⇒ 同一架构的编译器内建（builtins）会被**两条 libc 路线共用**。
- 现状（事实，源 `INFRA-078t §2`/`§4`）：我们的工具链**不提供 libgcc / compiler-rt builtins**；sysroot 里**只有**手工 vendor 的 `__mulsc3`/`__muldc3`（落 `components/picolibc/patches/libm/common/**`，`INFRA-067t`）⇒ **其余编译器内建符号全无**。正向缺口实测 = `__divsc3`/`__divdc3`（编译器已发出、sysroot 缺）+ **i128 除法 · FP↔i128 · `bswap` · `*_PARTS` · 原子 · f16**（后端连调用都发不出 / 前端拒绝）；反向 = 上游 core scope **146** 源中 **13** 编不过（`bswap` 2 / `shl_parts` 9 / i128 除法 2）。
- 约束：**不改** `spec/`（`ADR-0012 D4` / `docs/Process-06`：须用户**事先**明确允许）、**不改** `contracts/` 机器数据；组件源一律以 `manifests/components.lock.toml` 锁定的 commit 为准（`ADR-0005`）。
- 命中 ADR 判据（`docs/Process-03`）：**高代价**（定工具链 / 库形态）、**跨模块 / 需一致**（infra / llvm / testcases；musl 与 picolibc 两路线共用）、**有多方案且需记录取舍**（范围 / 形态 / 策略 / 验证 / 归属各有多案）、**外部依赖 / 契约**（`compiler-rt` 上游、`llvm-project` 版本）、**把调研结论固化为约束**（`INFRA-078t` 为 spike）。

## Decision（决策）— 逐条（**用户已逐条确认，2026-10-14，经主会话问答**）

**D1 — 范围 = 只 `builtins`**
纳入范围**仅** `compiler-rt` 的 **`builtins`**；**sanitizer / profiling / unwind / `libatomic` 暂不做**，**按需单独立项**。**被否**：全 `compiler-rt` ✗（超需、验证面爆炸）；只补 7 类缺口 ✗（不给库，缺可持续载体）。
（`builtins` 内部的具体源集 = `GENERIC_SOURCES ∪ GENERIC_TF_SOURCES` + arch `fp_mode`，由**接入任务现场**从上游 `CMakeLists.txt` 解析，**不写死**。）

**D2 — 形态 = 以 `llvm-project` 补丁接入**
`builtins` 的构建接线（`dadao` arch 分支、必要的头文件分支）**以 `components/llvm-project/patches/compiler-rt/**` 的补丁承载**；**版本随 `llvm-project 23.1.3` 天然同步**（同一锁定 commit，**无独立版本轴**）。**被否**：作为**独立组件**接入 ✗（须新锁源 + 独立版本轴，与 `llvm-project` 版本**易漂移**）。

**D3 — 策略 = 通用 C 优先**
实现**先走通用 C**（上游 `builtins` 本身即纯 C / freestanding，正确性优先）；**硬件特化（`bswap` / `clz` 等）后置**，且**须有数据支撑**方可立项。**「ISA 指令扩展」另立预研**（`SPEC-141t`），本 ADR **不预设**其结论。**用户原话要点**：「分析主流 ISA 已有专门支持，**可以增加部分指令**」。

**D4 — 验证 = 代表集 + 独立 oracle（另补端序敏感用例）**
- **代表性源集 + 独立 oracle**：上游 **`compiler-rt/test/builtins`** 作**现成 oracle**；**算法定义 / Python 大整数独立算期望**（期望值**不得**从 v5 自身实现反推）。
- **额外补「端序敏感」用例**：**我们是大端（BE）**，上游测试**多在 LE 上跑** ⇒ 须**专门覆盖**。
- 验收接 `tests/vectors/` / lit 既有向量与门控模式。
- **被否**：只跑上游测试 ✗（无端序覆盖、不足以判）；**全量手测** ✗（成本不可接受）。

**D5 — 归属 = 独立「DADAO compiler-rt builtins」库、picolibc / musl 共用**
`builtins` 构建、安装为**一个独立库**，**不属任何 libc**（不属 picolibc、不属 musl）；**picolibc 与 musl 共用同一份**。**被否**：各 libc **各自 vendored** ✗（重复且漂移——正是 `INFRA-067t` 手工 vendor 不可持续的反面）。

## Rationale（理由）

- **范围只 `builtins`（`D1`）**：编译器内建是本轮实际撞点；sanitizer / profiling / unwind / `libatomic` 各自独立、当前**无消费方** ⇒ 纳入只会使验证面爆炸。
- **补丁形态（`D2`）**：与既有 A 类补丁面（`INFRA-067t` 的移植来源、`LLVM-091t` 刚验证可控的补丁面）**同源同版本锁**；`compiler-rt` 与 `clang`/`lld`/`llvm` **同仓同版本** ⇒ 不新增版本漂移轴。
- **通用 C 优先（`D3`）**：上游实现即 freestanding 纯 C、**正确性优先**；hw 收益**未量化** ⇒ 直接上 hw 特化属**先付出验证成本而无数据支撑**（过度设计）；ISA 扩展另立预研并交用户裁定（改 `spec/` 须用户授权，`ADR-0012 D4` / `Process-06`）。
- **代表集 + 独立 oracle（`D4`）**：与 `ADR-0025 D7`（golden 对照）/ 项目 `Independent oracle` 原则同口径；**端序**是本项目与上游测试环境的**实质差异**，不补则覆盖有洞。
- **独立共用库（`D5`）**：`builtins` 为**编译器内建**、语义与 libc 无关；musl（M8 主线）与 picolibc（`ADR-0025 D4` 并存）共用同一份可消除重复与漂移。

## Consequences（影响）

1. **移除 picolibc 的 vendored 副本**（属**接入任务**，非本 ADR）：`components/picolibc/patches/libm/common/{muldc3.c,mulsc3.c,compiler_rt_builtins.h}` ⇒ 改链接**独立 builtins 库**。**连带（现场判）**：同目录 `meson.build.patch` 只含 `srcs_common` 两源插入 ⇒ 随源移除**须同步撤回**，`components/picolibc/series` 相应删行。
2. **install 落点按 `ADR-0016`**：host 工具链 prefix = `.dadao/cross-toolchain/**`（`ADR-0016 D3`）、target sysroot 根（`D5`）、install 范围只装所需（`D11`）；**不新增**安装根。
3. **与 `ADR-0025`（M8 路线）/ `ADR-0026`（动态链接）的关系**：本 ADR 只定 `builtins` 的**支持口径**；「动态链接行为类口径」归 `ADR-0026`，「M8 范围 / 顺序（`P0…P4`）」归 `ADR-0025`——**三层互不覆盖**。`builtins` 属 **P1（musl 静态）之前 / 并行**的可编译性前置，**不改变** `P0…P4` 顺序。
4. **不改 `spec/` / `contracts/`**：`builtins` 内容层真源 = `compiler-rt` 上游源码，**无 v5 规范正文可改**；`contracts/` 机器数据不动。
5. **登记（未决 / 已知）**：i128 除法·FP↔i128 的**后端 libcall 注册**、`ISD::SHL_PARTS`/`SRL_PARTS`/`SRA_PARTS`、`bswap`、原子、f16 属**后端改动点**（源 `INFRA-078t §4.4`），由**接入任务逐条处理**；`_Float16`/`__bf16` 当前**前端拒绝** ⇒ f16 是否可达**待现场判定**。

## 风险 / 未决项

- **`D3` 的「hw 特化」与「ISA 指令扩展」**：收益未量化；是否加指令须 `SPEC-141t` 的**代价 / 收益分析** + **用户裁定**，**本 ADR 不预设**。
- **原子（`INFRA-078t §4.4 #5`）**：超出 `builtins` 库本身（属后端 lowering），是否在本轮后端改动内一并做，由**接入任务现场判定 / 提请用户**。
- **`ISS-206`**（`DADAO.def` 随 `ADR-0019 D10` 重编号）：若重编号**涉及** `builtins` 的 libcall 名 ⇒ **现场判**；二者**无强耦合**。

## 状态说明

**Accepted（2026-10-14）**：`D1`–`D5` = 用户逐条选择，已成立、无否决未处置。

**逐条确认记录**（2026-10-14，**经主会话问答**）：

| 项 | 用户选择（**原话 / 选项标签**） | 落为 |
|---|---|---|
| D1 | **范围 = 只 `builtins`**（sanitizer / profiling / unwind / `libatomic` **暂不做**、按需单独立项） | `D1` |
| D2 | **形态 = 以 `llvm-project` 补丁接入**（`components/llvm-project/patches/compiler-rt/**`；版本随 `llvm-project 23.1.3` 天然同步） | `D2` |
| D3 | **策略 = 通用 C 优先**（hw 特化后置、需数据支撑）+「ISA 指令扩展」**另立预研**（**原话要点**：「分析主流 ISA 已有专门支持，**可以增加部分指令**」） | `D3`（ISA 侧 → `SPEC-141t`） |
| D4 | **验证 = 代表集 + 独立 oracle**（上游 `compiler-rt/test/builtins` 作现成 oracle + 算法定义 / Python 大整数独立算期望）+ **额外补端序敏感用例**（**我们是大端**，上游测试多在 LE 跑）+ 接 `tests/vectors/` / lit | `D4` |
| D5 | **归属 = 独立「DADAO compiler-rt builtins」库、picolibc / musl 共用**（不属任何 libc） | `D5` |

**被否方案（同次逐条确认中明确否决）**：`D1` 全 `compiler-rt` ✗ / 只补 7 类缺口 ✗；`D2` 独立组件（§版本易漂）✗；`D4` 只跑上游测试 ✗ / 全量手测 ✗；`D5` 各自 vendored（§重复 / 漂移）✗。

**变更流程**：决策变更时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认（`docs/Process-03`）。
