# GEM5-001k: gem5 启动与实施路线

**模块**：gem5
**项目里程碑**：M8（与 M7 并行实施）
**依赖**：gem5 实现可与 M7 并行；M7 验收范围不变
**状态**：已验证

## 问题根源

当前 `manifests/components.lock.toml` 中 gem5 disabled、commit 为空，`make build-gem5` 仍是占位拒绝；仓库只有 LLVM→ELF→QEMU 的执行闭环，没有 gem5 ISA、测试机、运行脚本或验收门控。课程项目需要一个可执行且可核验的 gem5 开发顺序，避免先做性能配置却尚无正确的 DADAO 执行语义。

## 目的与边界

M8 首版以单核 `AtomicSimpleCPU` 的**全系统裸机**配置运行现有 DADAO ELF。必须对齐 `spec/Machine-01`：复位 ROM、ELF `PT_LOAD`、唯一 16 MiB RAM、`hypv→user`、异常、`trap` 和 25 项 semihosting；覆盖当前 QEMU 已支持的 ISA 范围。交付第二个功能实现与可重复的端到端测试。性能评估、SE 模式、Linux/pk、MMU、动态链接和多核不进入 M8 验收。

## 架构与接口

```
LLVM/LLD → DADAO ELF ───────────────┐
现有 boot ROM ──────────────────────┤
spec/ + contracts/ → 独立向量 ───────┤→ gem5 DADAO ISA + Machine-01 平台 → 退出/状态/输出
                                     └→ QEMU 差分诊断（不产生期望值）
```

- gem5 上游基线采用官方 `v25.1.0.1`，完整 commit `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`；`ADR-0035` D1–D3 已逐条确认并 Accepted，组件启用仍须通过 `GEM5-002t` 的基线实核。源码只在 `.work/source/gem5`，定制以 `components/gem5/` 树形补丁集入库。
- 测试机接口以 `spec/Machine-01`、`.tao/knowledge/contract-elf.md`、`contract-isa.md`、`contract-fp.md` 和 `contract-semihosting.md` 为真源；`ADR-0036` D1–D4 已逐条确认并 Accepted。
- 指令字与数据大端、32 位定长取指、RD/RB/RA/RF 各 64×64 位及 `rb0` 当前 PC、RA 栈语义均按合约实现。`contracts/opcodes.yaml` 的当前有效范围是覆盖清单；`scope: excluded` 维持规定的非法指令行为。
- 使用 gem5 ISA 描述生成译码；单核 `AtomicSimpleCPU`、全系统裸机配置。`make build-gem5` 构建 `build/DADAO/gem5.opt`；`test-gem5` 跑代表集，`check-gem5-full` 跑完整适用集。运行产物经 `manifests/install-dirs.lock.toml` 与 `tools/infra/paths.py` 落测试产物目录。

## 对照关系

现有 QEMU 的 boot ROM、ELF 装载、semihosting 程序与端到端测试可作为**输入资产**，语义期望仍从规范独立派生；QEMU 输出只用于差分定位。旧 DADAO/gem5 loader 属历史溯源，当前无本地只读参考树，**内容溯源，非执行必需**；实施不得依赖其源码或假定其接口适用于现行 gem5。

## 任务分解与依赖

| 顺序 | 任务 | 交付物 | 阶段门槛 |
| --- | --- | --- | --- |
| 1 | `GEM5-002t` 基线与构建准备 | 精确组件锁、补丁骨架、上游构建环境 | `ADR-0035` Accepted；锁/取源码/上游构建检查通过 |
| 2 | `GEM5-003t` 向量入口与 ISA 骨架 | 独立向量映射、最小执行 fixture、DADAO 构建目标、寄存器/PC、取指译码、`build-gem5` | DADAO 二进制可启动；编码、状态、非法编码代表集能失败且通过 |
| 3 | `GEM5-004t` 标量语义 | 整数、地址、访存、控制流、RegRAS/MemRAS | 适用标量向量和调用程序通过 |
| 4 | `GEM5-005t` 测试机 | ELF/ROM/RAM、模式、异常、trap、semihosting | `ADR-0036` Accepted；boot ROM 与 25 服务通过 |
| 5 | `GEM5-006t` FP 与剩余 ISA | RF/FCSR、浮点、其余已支持 opcode 与 excluded 处置 | 对应独立向量通过、无静默错码 |
| 6 | `GEM5-007t` 集成收口 | 代表/全量门控、ELF/Embench 回归、能力矩阵 | 适用现有程序正确退出且结果一致 |
| 7 | `GEM5-008m` M8 核验 | 逐任务状态与整套证据 | 前置任务均已验证，L1/L2/L3 门控通过 |

`GEM5-002t` 在 ADR Accepted 后即可与 M7 并行启动；同改 gem5 补丁集的任务顺序执行。每个实现任务先立对应向量及可达 FAIL 的门控，再写组件实现；一能力一向量，期望值不从 gem5/QEMU 运行结果生成。任务收尾跑 L2，里程碑跑 L3。

## 总体验收

1. `make build-gem5` 产出可启动的 DADAO `gem5.opt`，组件锁和树形补丁门控全绿。
2. 编码/译码、寄存器状态、标量、FP、异常和 `scope: excluded` 的适用规范向量全部通过；每组门控至少演示一次反例注入导致非零退出。
3. 同一 boot ROM 与 DADAO ELF 在 gem5 按 `Machine-01` 启动，semihosting 全部 25 服务、退出状态、可观测结果符合合约。
4. 适用的现有端到端与 Embench 程序通过；差分分歧须追到规范/实现原因，不以 QEMU 输出覆盖独立期望。
5. `docs/Machine-00` gem5 能力列逐格附实测或文档依据；未验证项保留待定，不填推测值。

## 说明

用户于 2026-10-12 明确裁定「现在并行启动 gem5。记住，你只能负责gem5 部分代码和对应的文档/spec/adr/task等，其余部分你无权修改」。因此 M7 不是 gem5 实施前置，工作范围限 gem5 代码及直接相关文档、规范、ADR、任务和构建配置，M7 验收范围不变。`ADR-0035` 与 `ADR-0036` 均已 Accepted；任务书是待执行交付清单，不能把计划内容记为已实现。官方资料：<https://github.com/gem5/gem5/releases/tag/v25.1.0.1>、<https://www.gem5.org/documentation/general_docs/building>、<https://www.gem5.org/documentation/general_docs/architecture_support/isa_parser/>。

规划复核（2026-10-12）：独立审查发现并修正空补丁集门控、最小执行 fixture、ADR 状态标题、里程碑对 `k` 状态的核验和构建目标任务归属；修订后无剩余 finding。此处的 `已验证` 只表示路线和分解经过复核，不表示 `GEM5-002t`–`008m` 已执行。

## 2026-10-19 实施快照

- `GEM5-002t`–`007t` 已验证；下一项为 `GEM5-008m` 裸机闭环核验。
- 当前门控：ISA current 517/517、Machine-01 47/47、remaining 548/548、FP 329/329、opcode 覆盖 235/235；程序集代表 9/9、完整 58/58。
- gem5 组件保持官方基线 `c8222cc...` 上 base+1 单提交 `a5cfbfd...`，40 份逐文件补丁可重放。
- 余下路线仅 `GEM5-008m`（M8 核验）。
