# ADR-0057: gem5 Timing 的数据侧两阶段（`initiateAcc`/`completeAcc`）与周期表边界

**状态**：Candidate
**日期**：2026-11-16
**关联**：`m16-gem5-001`（钩子）/`-005`（块传送）/`-006`（访存时序，本 ADR 的直接触发者）/`-007`（对标）/`m16-chipyard-001`（周期模型权威复测）；`docs/core-wuming-cycle-model.md`；`M16 定位`（`milestones-m16.md` 头部）

## Context（背景）

M16 的定位是「gem5 时序模型对齐 chipyard-wuming，范围只做 Timing」。`m16-gem5-006` 落地时遇到一条硬事实：

- gem5 v25.1 **没有 ISA 级 `readMem`**；`initiateAcc`/`completeAcc` 是 `StaticInst` 的**ISA 级接口**（`src/cpu/static_inst.hh`，默认实现 `panic`），由 **`TimingSimpleCPU` / `MinorCPU` / `O3CPU`** 使用；**`AtomicSimpleCPU` 不用**（它直接 `StaticInst::execute()`，同步完成）。
- DADAO 当前只实现 `execute()`；**每条 32 位指令 = 一个 `StaticInst`**（`ExtMachInst = uint32_t`、PC 步进 `+4`），指令内的访存走 `ExecContext::readMem` ⇒ 在 Timing 下落到 `BaseSimpleCPU::readMem` 的 `panic`。
- `ldm`/`stm` 是**一条指令搬 N 个元素**（`execute()` 里的 "batch"），而框架对一条 `StaticInst` **只允许一次 `initiateAcc`/一次 `completeAcc`**（`timing.cc` 在 `completeAcc` 后立刻 `advanceInst()` 退休该指令）。
- 因此 `m16-gem5-006` 的现行实现把 Timing 的数据访问改成 **`SETranslatingPortProxy` 功能访问**：数据正确但**不计时**（实测 `system.mem` 数据侧 0 包），取指仍走真实 `NoncoherentXBar` + `SimpleMemory`。

用户 2026-11-16 裁定：**不把「数据访问不计时」长期化**，改为二期把执行核改成两阶段（本 ADR 的 D1–D7）。ADR 判据四条全中（高代价 / 跨模块 / 多方案 / 结论固化）。

## Decision（决策）

- **D1 接口与落点**：DADAO 实现 `StaticInst::initiateAcc`/`completeAcc`；**不改 `src/cpu/simple/**`**（CPU 框架边界）。两阶段**只在 Timing 下生效**；`AtomicSimpleCPU` 保持同步 `execute()`、行为逐字节不变；`MinorCPU`/`O3CPU` 的流水线结构（fetch/decode/issue/ROB/LSQ）**不在本期**。
  - 依据：周期表的钩子 `ISA::extraExecLatency` **唯一调用点是 `src/cpu/simple/timing.cc`**（`atomic.cc` 无调用）⇒ 周期表是 Timing 专属特性，Atomic 只作零成本基线（M16 定位原文）。
- **D2 粒度与两阶段落点**：**每条 32 位指令 = 一个 `StaticInst`**；单元素访存指令（`ld`/`st` 各宽度）在 `initiateAcc` 发请求、`completeAcc` 收响应，**不需要续跑机制**；`AtomicSimpleCPU` 仍走同步 `execute()`、逐字节不变。
- **D3 块传送（`ldm`/`stm`）= 宏操作展开（与 ARM 同构，一次做完）**：`ldm`/`stm` 在解码时产出**宏操作**对象，N 个元素各为**一个微操作**（`microPC` 记元素序号），每个微操作走自己的 `initiateAcc`/`completeAcc` ⇒ N 次真实往返；`fetchMicroop` 复用同一次取指（`src/cpu/simple/base.cc:393/399`），**不增加取指次数**。参照实现：gem5 ARM 的 `LdmStm`（`MacroMemOp : PredMacroOp`）与 `LdpStp`（`PairMemOp : PredMacroOp`，**连 2 元素都展开**）、x86 的 `X86Macroop`；RISC-V 基础 ISA 无多元素访存指令，故无此机制。
  - **stats 口径**：微操作会改变 `numInsts` 等计数（一条 `ldm` 变 N 个微操作）⇒ 验收须显式定义口径（用宏指令计数或接受 N 倍并注明），不得让同一指标前后不可比。
- **D4 周期表边界**：**清零全部访存类拍数**——单元素 `ld/st`（C 类 `ld.o` 7–16 / `st.o` 10–21 中对应单元素的部分、`ld.o rf` 13）**与块传送（D 类）**，cycles 一律由真实内存系统给出，避免双重计费；**非访存指令**的拍数仍由周期表 + 钩子记账（`TimingSimpleCPU` 本身不含流水/旁路/多发射成本）。`docs/core-wuming-cycle-model.md` 的对应口径由 `m16-chipyard-001` 回填。
- **D5 取指不变**：取指已走真实 `NoncoherentXBar` + `SimpleMemory`；「`TimingSimpleCPU` 无 icache ⇒ 每指令约 8 拍取指」是**实测事实**，不在本 ADR 内改动。
- **D6 验收口径**：① `system.mem` 的**数据侧包数 > 0**（单元素与块传送都确实走了内存系统）；② 同一 ELF 的 `numCycles` 在改前/改后**方向与量级自洽**（记录两值）；③ 与 chipyard 的比值**只记录、不设阈值**（`SimpleMemory` 无背压/队列模型，`st.o` 的 10–21 拍与 `ldm/stm` 的总线字节拍不可复现）；④ **stats 口径**（`numInsts`/`numMacroInsts`）显式定义并写进完成区；⑤ `AtomicSimpleCPU` 路径行为逐字节不变（它不查周期表，宏操作在 Atomic 下必须与展开前等价）；⑥ Atomic 的 `dcache_latency` 估计与 Timing 的真实排队**不是同一口径**，报告须分开表述（改前 Atomic 亦无表值，故无双重计费）。
- **D7 表述边界**：报告与门控统一写「M16 时序 = **取指与数据（单元素 `ld/st` 与块传送 `ldm/stm`）均走真实内存系统**（`TimingSimpleCPU`；无 icache；**无 back-pressure/队列模型**）；`Minor`/`O3` 不在本期」。

## Rationale（理由）

- **为什么必须做两阶段**：两阶段是 gem5 的 **ISA 级契约**，不是某个 CPU 的私有机制；不做它，DADAO 在 Timing 上永远只能功能访问（数据侧零周期），"时序模型"就只剩取指一半。
- **为什么并发度只能 1**：`TimingSimpleCPU` 是 in-order、非流水，`_status` 里只有一个 `DcacheWaitResponse` ⇒ 结构性一次只能一个请求。要并发必须换 `Minor`/`O3`，那是另一个里程碑。
- **为什么块传送用微操作展开**：与 M16 定位「块传送用微操作展开」一致；也让每个元素各自有请求/完成，天然满足 D2。
- **为什么周期表 `ld/st` 必须清零**：不清零就是"真内存往返 + 表里的 9/10 拍"重复计费，`numCycles` 会系统性偏大且无法解释。
- **为什么与 chipyard 的比值不设阈值**：chipyard 的 `st.o` 10–21 拍**含背压**，`SimpleMemory` 没有队列/背压模型 ⇒ 该差异是**结构性**的，设阈值只会逼出"调常数凑数"。

**被否方案**：

- ① 长期保留 functional 数据访问（等于承认"时序"只有取指一半）；
- ③ 只对单元素 `ld/st` 做两阶段、块传送仍按模型（两套口径并存，bundle 仍需可续跑，收益不足）；
- ④ 在 `src/cpu/simple/**` 里给 DADAO 加私有 hook（改 CPU 框架边界，跨模块且升级成本高）。

## Consequences（影响）

- **正面**：Timing 下数据访问获得真实往返周期；`numCycles` 的构成可解释（取指 + 数据 + 周期表记账的非访存部分）；
- **负面/约束**：`DadaoInst::execute()` 需重构为可续跑（结构性改动）；周期表与 `docs/core-wuming-cycle-model.md` 的 `ld/st` 口径要同步清零/回填；`m16-chipyard-001` 的权威复测须在新口径下重跑并重记比值；块传送的 gem5 周期会**低于** chipyard（无背压），报告中必须写明；
- **不变**：`AtomicSimpleCPU` 路径（同步 `execute`）与其既有基线；取指侧实现；
- **后续**：`Minor`/`O3` 若要接入，需另立 ADR（流水线结构 + LSQ/ROB）；`M17`（可执行参考模型）不再需要承担"数据侧时序"。

## 状态说明

2026-11-16 由主会话起草（触发：用户裁定「② 重构 bundle 两阶段」）。**D1–D7 为提案，须逐条与用户确认后方可置 `Accepted`**；未确认前保持 `Candidate`，实施任务不得据此开工。
