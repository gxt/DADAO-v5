# RTL-007k: RTL-M2 启动与任务分解

**模块**：rtl
**项目里程碑**：RTL-M2
**依赖**：`RTL-006m`（`里程碑`）、ADR-0012、ADR-0014
**状态**：已验证
**审阅状态**：原始版本 Accepted（2026-10-13，独立 reviewer）；
D4 修订待复验

**目标**：规划并冻结 RTL-M2 的范围、接口、任务依赖和验证方法，使单周期
DADAO Core 能在 testbench FSM（测试程序台有限状态机）注入的存储器模型
上执行 M1 标量程序，并通过定向回归和独立 oracle（独立期望值来源）验证。

**关联任务**：`RTL-001k`、`RTL-002t`、`RTL-003t`、`RTL-004t`、
`RTL-005t`、`RTL-006m`

## 背景

RTL-M1 已完成：

- `rtl/dadao` 权威源码可独立编译；
- Chipyard overlay 和树形补丁集可回放；
- `DADAOTile`、`DADAOConfig` 和最小 elaborator 可生成 CHIRRTL；
- firtool `1.75.0` 已验证可生成 SystemVerilog，但 RTL-M2 的
  ChiselTest（Chisel 测试框架）/Treadle（软件仿真后端）单元验证
  不依赖它；
- 23 类 Verilog 结构和反例门控通过。

但当前 `DADAOCore` 仍只暴露 PC 和通用内存端口，取指、译码、执行、
寄存器堆、访存和控制流尚未实现。

本任务只做 RTL-M2 的启动规划，不实现 Core 指令语义。具体实现由后续
`RTL-008t` 到 `RTL-012t` 任务承担。

## 冻结输入

| 项目 | 冻结值 |
|---|---|
| 规范 | SimRISC 0.5.5 |
| M1 指令范围 | `contracts/opcodes.yaml` 中 `scope: m1` 的 156 条 |
| M1 向量 | `tests/vectors/isa/` 的 15 个 YAML 文件；当前 747 个顶层 case（739 active、8 deferred） |
| Chipyard | `1.14.0` |
| Chipyard commit | `0acc1e1de2d3284bcd4d876956932a013ffe1949` |
| Chisel | `6.7.0` |
| Scala | `2.13.16` |
| chiseltest | `6.0.0` |
| firtool（RTL-M2 可选，后续 Verilator/Chipyard 阶段必需） | `1.75.0` |
| RTL 权威源码 | `rtl/dadao/` |
| RTL-M2 测试后端 | testbench FSM（有限状态机）存储器模型和向量注入 |
| 架构依据 | ADR-0012、ADR-0004、`.tao/knowledge/contract-isa.md` |
| 前置里程碑 | RTL-M1，`里程碑` |

**术语说明**

- **testbench FSM**：测试程序台中的有限状态机，按周期响应 Core 内存请求并注入
  指令/数据，不作为最终硬件设备。
- **oracle**：独立期望值来源。RTL 的结果不能反过来生成自己的期望值。
- **directed regression**：按指令族和边界条件手工设计的定向回归，不是只跑随机程序。
- **stall**：内存请求尚未返回时暂停 Core 进展。
- **RAS**：Return Address Stack，返回地址栈，用于 call/ret 语义。
- **M1 vector**：`tests/vectors/isa/*.yaml` 中独立于 LLVM/QEMU 推导的测试条目。
- **negative gate**：故意注入错误，确认验证脚本真的会失败。

## 范围

### 包含

1. 冻结单周期 Core 的执行模型、端口、PC 更新和内存等待语义。
2. 规划取指、译码、寄存器堆、整数执行、访存、控制流和 RAS 的实现顺序。
3. 规划 testbench FSM 存储器模型、向量注入和测试停止机制。
4. 规划 RD、RB、RA 寄存器组的读写和非法条件处理。
5. 规划大端序、访存宽度、对齐和异常结果的实现检查。
6. 规划 M1 向量的定向回放、独立 oracle 和反例门控。
7. 把 RTL-M2 拆成 `RTL-008t` 到 `RTL-013m` 并按依赖排序。

### 不包含

1. 不实现 TileLink、外部 RAM、BootROM、UART 或架构 Exit 设备。
2. 不实现 cache、MMU、多核、外部中断、浮点或特权 cfx。
3. 不实现 LR/SC 原子操作和 TileLink 原子操作。
4. 不实现流水线、branch predictor（分支预测器）或性能优化。
5. 不修改 `tests/vectors/isa/` 的既有期望值。
6. 不把 QEMU 或旧 DADAO 实现当作 ISA 规范来源。

## Decision 提案

### D1：RTL-M2 的执行与存储边界

**提案**：Core 采用单发射、架构单周期执行；同一内存端口同时服务取指和
load/store，内存未响应时 `stall`。RTL-M2 只接 testbench FSM
（有限状态机）存储器模型，不接 TileLink。

**用户确认（2026-10-13）**：D1 通过，保持本提案。

内存端口时序冻结如下：

1. Core 同一时刻只允许一个 outstanding request（未完成请求）；
2. 同一周期不并发发出取指请求和数据访问请求；
3. 当前指令需要数据访问时，先完成该指令取指，再发出数据请求；
4. 请求通道：`req.valid && req.ready` 完成握手；在 `req.valid &&
   !req.ready` 期间，`req.bits` 必须保持不变；
5. 响应通道：只有 `resp.valid && resp.ready` 才表示内存操作完成；
   PC、寄存器堆和内存写提交必须等待该响应握手；
6. 请求握手后 Core 等待响应，期间不得发出第二个请求；在
   `resp.valid && resp.ready` 完成前不得提交架构状态；该响应握手
   当拍允许提交一次，且同一次请求只能提交一次；
7. testbench FSM 存储器模型可配置为零等待或固定等待；测试必须覆盖
   `req.ready` 延迟、`resp.valid` 延迟和请求保持不变的场景；
8. `kind` 明确区分取指与数据访问，但不得改变 guest 可见地址、
   访问宽度或 DADAO 语义。

### D2：M1 指令范围

**提案**：实现 `contracts/opcodes.yaml` 中全部 `scope: m1` 身份（156 条），
包括 RD/RB/RA、load/store、块访存、算术/逻辑/移位/扩展/比较、分支、
jump、call/ret、RAS 和 `swym` no-op。RTL-M2 不实现 `scope: fp`（66 条）、
`scope: excluded`（2 条）和 `scope: m3`（1 条）；这些编码按 ILLI
处理。全零字 `0x00000000` 属于 QFC 空白单元格，按 UNDI 处理。

**用户确认（2026-10-13）**：D2 通过，保持本提案。

### D3：架构状态和非法条件

**提案**：

- RD、RB、RA、PC 使用冻结宽度；复位时从冻结复位向量开始；
- 指令先完成合法性检查，再写架构状态；
- 非法指令、非法寄存器组合、非法对齐和 RAS 上下溢必须返回
  ADR-0004 规定的 fault 码；
- 精确异常优先于目标寄存器或内存写入；
- `swym` 作为 no-op；`fence` 属 `scope: excluded`，按 ILLI 处理。

**用户确认（2026-10-13）**：D3 通过，保持本提案。

### D4：testbench FSM 向量注入模型

**提案**：RTL-M2 使用 testbench FSM（测试程序台有限状态机）驱动的
memory model（存储器模型）和测试专用停止机制，无需实现硬件 Scratchpad
（临时片上存储器），只用于验证 Core 指令语义；后续 RTL-M3/RTL-M4
再接 BootROM、TileLink、外部 RAM 和 Exit。

测试地址模型冻结如下：

1. 架构复位向量仍为 `0xffff_ffff_0000`，Core 不允许因测试模式而改变
   复位语义；
2. testbench FSM 使用两个独立地址窗口，而不是要求 4 GiB 连续内存：
   - `reset_window`：从 `0xffff_ffff_0000` 起 64 KiB，与架构 BootROM
     窗口一致；
   - `ram_window`：从 `0xffff_0000_0000` 起 16 MiB，与架构 RAM 图和
     `DADAOParams.ramSize` 一致。
   两个窗口由 FSM 按地址译码并返回指令或数据，不改变架构地址图；
3. end-to-end（端到端）模式在复位前把程序向量装入 FSM 的
   `reset_window`，从冻结复位向量启动；如需进入 RAM entry，使用
   test-only trampoline（仅测试跳板），
   不得改写向量的 `expected_pc`；
4. instruction-mode（单指令模式）不复用复位向量启动。`DADAOCore`
   设置 `testMode`（测试模式）参数；仅当 `testMode=true` 时暴露
   test-only `pc_init_valid/pc_init` 端口，testbench 在复位期间注入
   `0xffff_0000_0000`。正式 Core 配置不暴露该端口，不改变架构复位
   语义；该值来自当前向量的 PC 约定和 `expected_pc` 基准，不是新增
   YAML 字段；
5. 现有 YAML schema 不新增 `entry` 或 `input_state.pc` 字段；RTL-012t
   如需内部 fixture 结构，必须从 YAML 的既有字段和上面的固定 PC 规则
   派生；
6. testbench 在复位前初始化 RD/RB/RA 和 FSM 的 memory model；
   Core 架构端口不提供后门加载接口；
7. 验证停止由 testbench 观测 sentinel（哨兵值）、PC 或 test-complete
   信号，不把额外设备写入 DADAO 架构；
8. 不得为了适配 FSM 存储器模型而修改向量的 `expected_pc`、期望寄存器、
   期望内存或 fault 码。

**用户确认（2026-10-13）**：D4 通过，保持本提案。

### D4 修订：以 FSM 向量注入替代硬件 Scratchpad

**用户授权（2026-10-13）**：RTL-M2 不要求实现硬件 Scratchpad；
testbench FSM 负责响应 Core 内存请求并注入指令/数据。该修订不改变
Core 架构端口、复位语义和地址图。

**firtool 延期**：RTL-M2 的 ChiselTest/Treadle 仿真不依赖 firtool；
firtool 的 Verilog/SystemVerilog 生成验证延后到 Verilator
（高速仿真器）或 Chipyard（芯片生成框架）集成阶段。

### D5：验证方法

**提案**：

1. 先做 Chisel 单模块测试；
2. 再做按指令族的定向回归；
3. 回放 `tests/vectors/isa/` 的 M1 active 向量；
4. 使用独立 Python oracle 计算期望状态；若增加 Chisel 参考模型，必须
   与 DUT（被测设计）分离实现，不得 import、实例化或复用 `DADAODecoder`、
   ALU、寄存器堆等实现；
5. 运行前生成 `tests/vectors/isa/*.yaml` 的排序文件清单
   `vectors.before.sha256` 和文件数量（必须为 15），运行后生成
   `vectors.after.sha256`；两次清单必须逐字节一致，否则验证失败；
6. 最后使用 QEMU 做差分佐证，但不从 QEMU 反推规范；
7. 每个验证脚本必须通过反例注入证明可失败。

**用户确认（2026-10-13）**：D5 通过，保持本提案。

### D6：任务分解

**提案**：

| 编号 | 任务 | 主要交付物 | 依赖 |
|---|---|---|---|
| `RTL-008t` | 单周期取指与译码框架 | PC、取指、decoder、控制信号、testbench FSM 最小循环 | `RTL-007k` |
| `RTL-009t` | RD 整数执行与寄存器堆 | RD/RB/RA 寄存器堆、ALU、立即数、扩展、比较、寄存器组块赋值 | `RTL-008t` |
| `RTL-010t` | 访存、端序与异常 | load/store、`ldm.*`/`stm.*` 块访存、testbench FSM memory model、大端 byte lane、MALIGN/ILLI | `RTL-009t` |
| `RTL-011t` | 控制流、call/ret 与 RAS | branch、jump、call、ret、RegRAS/MemRAS、精确异常 | `RTL-010t` |
| `RTL-012t` | M1 向量回放与独立 oracle | 向量导入、期望状态比较、定向回归、反例门控 | `RTL-011t` |
| `RTL-013m` | RTL-M2 里程碑核验 | 全量 M1 active 指令验证结论和证据 | `RTL-008t`~`RTL-012t` |

任务可拆分，但不得改变依赖顺序和 M1 语义边界。

异常与合法性路径的任务归属：

| 路径 | 归属任务 |
|---|---|
| UNDI、保留编码、SBZ 非零、IALIGN、全零字 | `RTL-008t` |
| `rd0`/`rb0` 目的或源、双目的同寄存器、双 `rd0`、取指-unmapped | `RTL-008t` |
| 非法移位/扩展、除零、`INT_MIN / -1`、寄存器组块范围和 `immu6=0` | `RTL-009t` |
| 非法 load/store、RD store 的 `rd0` 源、`ldm.*`/`stm.*` 访问范围、MALIGN、数据-unmapped、端序 | `RTL-010t` |
| 分支/跳转对齐、call/ret、RA 块规则、RASOF/RASUF | `RTL-011t` |
| no-commit、异常优先级、fault 码和反例门控 | `RTL-012t` |
| `swym` no-op 和 `fence` excluded→ILLI | `RTL-008t`/`RTL-012t` |
| `imm_range`（立即数超字段宽度） | 不属于 Core 运行时路径；由 assembler/validator 静态拒绝，RTL-012t 只做交叉审计 |

**用户确认（2026-10-13）**：D6 通过，保持本提案。

## 交付物

```text
.tao/tasks/rtl/
├── RTL-007k-RTL-M2启动与任务分解.md
├── RTL-008t-单周期取指与译码框架.md
├── RTL-009t-RD整数执行与寄存器堆.md
├── RTL-010t-访存端序与异常.md
├── RTL-011t-控制流call-ret与RAS.md
├── RTL-012t-M1向量回放与独立oracle.md
└── RTL-013m-RTL-M2里程碑核验.md

rtl/dadao/src/main/scala/dadao/
├── DADAOCore.scala
├── DADAODecoder.scala
├── DADAORegFile.scala
├── DADAOALU.scala
└── ...

tests/rtl/
├── core/
├── vectors/
└── smoke/

tools/rtl/
└── vector replay、oracle、negative-gate 脚本
```

具体文件名在 `RTL-008t` 到 `RTL-012t` 下发前确定；不得复制参考实现代码。

## 验证步骤

1. 编译 `rtl/dadao`，运行现有 Chisel 单模块测试。
2. 对 RTL-M2 的取指、寄存器写入、ALU、访存、分支、call/ret 和异常路径
   执行定向测试。
3. 从 `tests/vectors/isa/` 读取 active 向量，生成测试程序或指令级激励。
4. 使用独立 oracle 计算 PC、RD、RB、RA、内存和 fault 期望值。
5. 将 Core 的实际结果与 oracle 比较，任何 mismatch 都必须保留最小复现。
6. 运行前后分别生成 `vectors.before.sha256` 和
   `vectors.after.sha256`，逐字节比较清单；文件数必须为 15，任何差异
   都判定失败。
7. 对 decoder、ALU、load/store、控制流和异常分别注入反例，确认验证脚本
   返回非零。
8. 恢复反例并重新运行正向验收，确认工作区和二进制还原。
9. 保存命令、真实退出码、SHA-256、覆盖报告和未通过项分类。

## 验收标准

1. `RTL-008t` 到 `RTL-012t` 均有自包含任务书且依赖顺序正确。
2. `scope: m1` 身份 155/155 被实现或明确标记为异常路径；`fp`/`excluded`/`m3`
   均按 ILLI 或明确范围外处理。
3. 每条 M1 active 指令至少有一条可追溯期望值的语义验证。
4. `tests/vectors/isa/` 的 active 语义向量回放无未解释 mismatch。
5. testbench FSM memory model、大端序、对齐、RD/RB/RA 和 RAS 有独立边界测试。
6. 反例门控全部真实失败，恢复后正向验证通过。
7. 向量文件数量和排序 SHA-256 清单运行前后逐字节一致，或验证任务
   明确失败。
8. QEMU 差分只作为佐证，不作为 ISA 规范来源。
9. 正式 Chipyard 工作树不被 testbench FSM 测试修改。
10. 资源占用遵守 ADR-0013：JVM heap 上限、构建并行度和磁盘警戒线。

## 下发前预检（待执行）

1. **任务书内部一致性**：待检查目标、D1-D6、交付物和验收是否互不矛盾。
2. **依赖链实际可用性**：待检查 RTL-M1 产物、testbench FSM 需求、Chisel
   API 和向量读取工具。
3. **验收可执行性**：待标明每条验收是现在可跑、依赖后续任务还是 BLOCKED，
   并给出替代证据。
4. **与 spec/vectors 一致**：待检查指令范围、编码、异常和向量期望值来源。

## 已知风险

1. 单周期设计仍需处理 64 位运算、块访存和精确异常，不能把“单周期”误解为
   “所有指令都无等待”。
2. M1 向量原本服务 QEMU harness，RTL 复用时必须明确输入/输出契约，
   不得直接假定现有脚本可原样消费。
3. testbench FSM 是临时测试后端，不能把其地址或停止机制写进 DADAO 架构。
4. 大端序、byte lane、对齐和异常优先级容易被实现细节掩盖，必须有逐字节测试。
5. RAS 有跨指令状态，必须测试溢出、下溢、嵌套 call/ret 和精确异常。
6. 当前 Clab 内存和磁盘有限，验证任务不得下载完整历史或复制多份 Chipyard。

## 完成区

### 审阅结论

- 独立 reviewer 三轮审阅：
  - 第一轮识别 testbench FSM/reset/vector PC、单端口时序、oracle 独立性、
    向量哈希、异常归属和块操作边界问题；
  - 第二轮识别 test-only PC 注入机制、RAM 窗口与 16 MiB 地址图和
    `imm_range` 归属问题；
  - 第三轮仅剩响应握手后的提交时序文字矛盾；
- 上述问题已修正；最终 reviewer 结论为 `Accepted`。
- D4（决策四）已于同日按用户授权改为 testbench FSM 向量注入，
  该修订需重新审阅后才能维持 `Accepted` 状态。

### 待确认

D1-D6 已于 2026-10-13 逐条确认，`RTL-007k` 置为 `已验证`。
后续可以创建 `RTL-008t` 的具体实现任务书，但必须再次经过任务书确认后
才能下发执行。

## 参考

- `.tao/tasks/rtl/RTL-006m-RTL-M1里程碑核验.md`
- `.tao/knowledge/adr-0012-chipyard-single-cycle-soc.md`
- `.tao/knowledge/adr-0013-clab-rtl-environment.md`
- `.tao/knowledge/adr-0014-chipyard-1.14-upgrade.md`
- `.tao/knowledge/contract-isa.md`
- `contracts/opcodes.yaml`
- `contracts/legality_rules.yaml`
- `tests/vectors/schema.md`
- `tests/vectors/README.md`
- `tests/scripts/README.md`
