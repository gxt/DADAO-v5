# RTL-010t: 访存、端序与异常

**模块**：rtl
**项目里程碑**：RTL-M2
**依赖**：`RTL-009t`（本地提交 `10de59f`）
**状态**：D1–D7 与 SimRISC 0.5.5 适配完成；本地 merge commit `a2dc1f6a`

**目标**：在 RTL-009t 的单周期整数 Core（处理器核）和 testbench
FSM（测试台有限状态机）上，完成 M1 的 30 条单寄存器/多寄存器
load（取数）/store（存数）指令；实现 DADAO 大端序（big-endian）、
64-bit 通用内存端口、数据请求等待、自然对齐检查、数据
`UNMAPPED`（未映射）和 `MALIGN`（未对齐）异常，并保证 fault
（故障）时寄存器与存储器不发生部分提交。

## 版本基线

| 项目 | 当前版本 |
|---|---|
| SimRISC | `0.5.5` |
| Chipyard | `1.14.0` |
| Chipyard commit | `0acc1e1de2d3284bcd4d876956932a013ffe1949` |
| Chisel | `6.7.0` |
| 前置提交 | `10de59f6eec2f49d9cc23fce553ff9bce0a75424` |

## 冻结输入

| 项目 | 冻结值 |
|---|---|
| M1 编码 | `contracts/opcodes.yaml`，156 条 |
| 本任务范围 | 30 条 `ld.*`/`st.*`/`ldm.*`/`stm.*` |
| 合法性 | `contracts/legality_rules.yaml` |
| 端序 | 大端序：最低地址存放多字节数据的最高有效字节 |
| 寄存器 | RD/RB/RA 各 64 个 64-bit 寄存器 |
| 数据宽度 | byte=8、wyde=16、tetra=32、octa=64 bit |
| 地址宽度 | 48-bit 核内有效地址；Core 端口保留 64-bit 地址 |
| RAM | `0xFC00_0000_0000` 起 16 MiB；以 `spec/Machine-01` 现行口径为准 |
| BootROM | `0xffff_ffff_0000` 起 64 KiB，只读 |
| 执行模型 | 单发射、单周期整数路径、一次一个未完成内存请求 |
| 验证后端 | ChiselTest + Treadle |

## 30 条指令

### 单寄存器 RD（11 条）

```text
ld.sb  ld.ub  ld.sw  ld.uw  ld.st  ld.ut  ld.o
st.b   st.w   st.t   st.o
```

地址公式：

```text
effective_address = RB[rbhb] + sign_extend(imms12)
```

### 单寄存器 RB/RA（4 条）

```text
ld.o  RB
st.o  RB
ld.o  RA
st.o  RA
```

### 多寄存器 RD（11 条）

```text
ldm.sb ldm.ub ldm.sw ldm.uw ldm.st ldm.ut ldm.o
stm.b  stm.w  stm.t  stm.o
```

### 多寄存器 RB/RA（4 条）

```text
ldm.o RB   stm.o RB
ldm.o RA   stm.o RA
```

多寄存器地址公式：

```text
effective_address = RB[rbhb] + RD[rdhc]
count = zero_extend(immu6)
```

第 `i` 个元素（`i = 0..count-1`）的地址为：

```text
effective_address + i * access_width_bytes
```

## 包含

1. 1/2/4/8-byte load/store。
2. RD/RB/RA 三 bank 的单寄存器与多寄存器访存。
3. 大端序字节选择、符号扩展和零扩展。
4. 64-bit 通用请求/响应端口上的数据访问。
5. 请求端 `ACK`（接收确认）和响应端 `VALID/READY`（有效/就绪）
   握手。
6. 单寄存器访问的精确异常。
7. 多寄存器访问在首个请求前完成全部地址映射与对齐预检。
8. `ldm` 的结果缓冲与原子写回。
9. RAM、BootROM 和未映射区域的访问种类/宽度检查。
10. testbench sparse memory（稀疏测试存储器）的逐字节读写。
11. 独立 Python oracle（独立期望值）、YAML 向量和 negative gate
    （负例门控）。

## 不包含

1. TileLink（片上总线协议）适配层和正式 SoC 总线。
2. UART、semihosting、BootROM 固件和完整 Chipyard SoC。
3. cache、MMU、页表、PTBR 和 cfx 权限。
4. RF 浮点寄存器访存。
5. branch/jump/call/ret/RAS 和系统 cfx 指令。
6. LR/SC 原子指令。
7. 中断和可恢复异常处理程序。

## Decision 提案

### D1：共享寄存器状态、单一内存所有者和提交时序

**提案**：

- 把 `DADAORegFile` 从 `DADAOIntExec` 内部提升到 `DADAOCore`，
  或封装为一个由 Core 统一拥有的执行状态模块。
- 整数执行和访存执行读写同一个 RD/RB/RA 寄存器堆；不得复制第二份
  架构寄存器状态。
- Core 保持同一时刻只有一个未完成内存请求（single outstanding）：
  - `FETCH`：取指请求；
  - `DATA`：load/store 请求；
  - `IDLE`：无未完成请求。
- 取指响应成功后，先锁存当前指令的 PC、32-bit 指令字、译码结果和
  fault 状态。
- 整数指令在无 fault 时沿用现有提交路径；load/store 不得在数据响应
  前更新目的寄存器或推进 `PC+4`。
- load/store 完成且无 fault 后，在同一时钟沿提交寄存器和
  `PC := current_pc + 4`。
- fault 时保持 `PC=current_pc`，不写目的寄存器、不产生 store 内存
  写，不推进到下一指令。
- 取指和数据访问共用 `io.mem`；由 Core 明确选择 `kind`
  （`Fetch`/`Data`）并保存当前请求，禁止两个请求同时占用端口。
- `DADAOParams.ramBase` 从旧值 `0xffff_0000_0000` 修正为
  `spec/Machine-01` 现行值 `0xFC00_0000_0000`；BootROM 地址不变。

**实现选择**：

| 内容 | 性质 |
|---|---|
| RD/RB/RA 共享同一架构寄存器堆 | ISA 与实现正确性要求 |
| 单 outstanding 内存请求 | 本 SoC 首版实现选择 |
| 取指/数据显式所有权状态 | 实现选择 |
| `PC+4` 仅在成功提交时生效 | 精确异常要求 |
| RAM 基址 `0xFC00_0000_0000` | `spec/Machine-01` 现行规范 |

**备选**：

- B1：在 `DADAOIntExec` 外再建一份访存专用寄存器堆。该方案会产生
  两份架构状态，否决。
- B2：保持取指和访存各自独立的请求 FSM，再在 `io.mem` 前做仲裁。
  该方案可在后续接入流水线，但首版增加状态交互，暂不采用。

**待用户确认**：是否采用“寄存器堆提升到 Core + 单一
`FETCH/DATA/IDLE` 状态机 + RAM 基址同步修正”。

**用户确认（2026-10-25）**：D1 通过。`DADAORegFile` 由
`DADAOCore` 持有并通过显式端口与 `DADAOIntExec` 共享；
`DADAOMemOwner` 使用 `IDLE/FETCH/DATA` 三状态，其中 `DATA`
为 RTL-010t 后续 load/store 路径保留；`DADAOParams.ramBase`
统一为 `0xFC00_0000_0000`。

### D2：大端 byte lane 与内存请求格式

**提案**：

- 为 `DADAOMemReq` 增加 `wstrb`（write strobe，写字节使能）：

```text
wstrb[7:0]
```

- `wstrb[j]` 对应以 `addr & ~7` 为基准的第 `j` 个 guest
  byte（客户机字节）。
- 单次自然对齐访问不会跨越 8-byte beat（总线拍）。
- 请求中的 `wdata` 按访问宽度右对齐：

```text
N-byte store: wdata[8*N-1:0] = value
wdata[63:8*N] = 0
```

- `addr[2:0]` 决定 guest byte 在 8-byte beat 内的起始偏移：

```text
offset = addr[2:0]
wstrb = ((1 << N) - 1) << offset
```

- 大端映射规则：
  - `value` 的最高有效字节写到最低 guest 地址；
  - `value` 的最低有效字节写到最高 guest 地址；
  - load 响应中的 `rdata` 将选中字节按同一规则归一化为右对齐
    value，Core 再做符号/零扩展。
- 示例：在 RAM 中存储 `0x11223344`：

```text
address + 0 = 0x11
address + 1 = 0x22
address + 2 = 0x33
address + 3 = 0x44
```

- Core 不通过“交换整个 64-bit 字”实现端序转换。端序由 guest
  byte 与 lane（字节通道）的映射明确表达。
- testbench memory 是首个适配器实现；后续 TileLink 适配层必须保持
  同一 guest 语义，并把 `wstrb` 映射为 TileLink 的 byte enable。

**说明**：

- byte lane（字节通道）是 64-bit 数据字段中某个 byte 的位置。
- byte enable/write strobe（字节使能）表示一次写操作中哪些 byte
  允许写入；未使能 byte 必须保持原值。

**待用户确认**：是否采用“`addr` 保留精确有效地址、`wdata` 右对齐、
`wstrb` 按 guest byte 偏移编码、响应 `rdata` 右对齐选中值”的接口。

**用户确认（2026-10-25）**：D2 通过。64-bit memory data 表示一个
自然对齐的 8-byte big-endian beat（大端总线拍），`wstrb[j]`
对应 beat 内 guest byte `j`，`wdata` 仍按访问宽度右对齐；
load response（读响应）的 `rdata` 输出右对齐选中值。

### D3：load 扩展语义

**提案**：

| 指令 | 宽度 | 扩展 |
|---|---:|---|
| `ld.sb` | 8 | sign-extend（符号扩展）到 64 bit |
| `ld.ub` | 8 | zero-extend（零扩展）到 64 bit |
| `ld.sw` | 16 | sign-extend |
| `ld.uw` | 16 | zero-extend |
| `ld.st` | 32 | sign-extend |
| `ld.ut` | 32 | zero-extend |
| `ld.o` | 64 | 原样 64 bit，无扩展 |

- 扩展只发生在成功 load 响应之后。
- `ld` 的目的为 `rd0` 或 `ld.o`/`ldm.o` 的 RB 目的为 `rb0` 时，
  由译码静态检查产生 `ILLI`，不得发起数据请求。
- `ld.o` 到 RA 时写入完整 64-bit 位型；`ra0[63:54]` 仍按 RTL-009t
  的 SBZ（应为零）规则屏蔽。

**待用户确认**：采用上表扩展规则，并保持 RD/RB/RA 零号寄存器
写保护不变。

**用户确认（2026-10-25）**：D3 通过。实现 9 条单寄存器 load
（RD 七条、RB/RA `ld.o` 各一条）；数据响应按宽度做 signed
（有符号）或 unsigned（无符号）扩展后写目的 bank，等待响应期间
PC 保持，response fault 时不写寄存器。

### D4：store 数据准备与写掩码

**提案**：

- `st.b/w/t/o` 从 RD、RB 或 RA 读取 64-bit 源值。
- 仅低 `8*N` bit 进入 `wdata`；高 bit 清零。
- `wstrb` 由有效地址和访问宽度生成，Core 不做
  read-modify-write（读改写）。
- testbench memory 与后续 TileLink 适配器负责按 lane mask 合并
  未写 byte。
- `st.*` 的 RD 源为 `rd0` 时读 0，合法。
- `st.o`/`stm.o` 的 RB 源为 `rb0` 时读当前指令 PC，合法。
- 写 BootROM 及非法的区域/宽度组合按 D5
  返回 fault，不产生部分写。

**待用户确认**：采用 Core 生成右对齐 `wdata + wstrb`、存储器负责
byte merge（字节合并）的分工。

**实现与审阅（2026-10-26）**：实现 M1 的 6 条单寄存器 store
变体：`st.b/st.w/st.t/st.o` 的 RD 源，以及 `st.o` 的 RB、RA
源；FP 范围的 `st.t-rf/st.o-rf` 不进入本阶段路径。Core 生成
右对齐 `wdata` 与按 guest byte 偏移编码的 `wstrb`，存储器负责
byte merge。RD、RB、RA 三种源均通过 Core 的 store-load 回读闭环，
覆盖 `rb0=PC` 和 RA 源语义。D4 实现已提交于
`1eadc69f3fe0da1973a6ac29f4f2fa314cf7a6ad`。

**时序前提**：本阶段 Core 要求 response（响应）最早在 request
（请求）握手后的下一 clock（时钟周期）有效；test memory 的
`memRespLatency=0` 表示没有额外等待周期，而不是与 request 在同一
周期返回。该前提在后续 TileLink（片上总线协议）适配时必须保持。

### D5：地址映射、对齐和 fault 优先级

**提案**：

1. 首先完成译码和静态合法性检查；已判 `ILLI` 的指令不发起访存。
2. 动态访存按 ADR-0004 D5.6 的优先级判定：
   - 有效地址不在 RAM/BootROM 映射内：`UNMAPPED=0x87`；
   - 已映射但未自然对齐：`MALIGN=0x8C`；
   - 已映射且对齐，但违反区域访问种类/宽度：`ILLI=0x88`；
   - 否则发起请求。
3. 多寄存器访问对每个元素先做同样的完整预检；任一元素失败则在
   首个数据请求前产生该 fault。
4. 同一指令同时满足多个动态错误时，严格按
   `UNMAPPED > MALIGN > ILLI` 返回，不按检查代码书写顺序决定。
5. 自然对齐宽度：

```text
byte: 1
wyde: 2
tetra: 4
octa: 8
```

6. 区域约束：

```text
RAM:     对齐 1/2/4/8-byte load/store 均允许
BootROM: load 允许；store -> ILLI
其余:    UNMAPPED
```

7. response（响应）带 `fault/faultCode` 时，Core 传播该 fault，
   保持 `PC` 为本指令地址，不提交本指令架构状态。
8. 地址映射检查由一个独立、可单测的
   `DADAOAddressMap`/`DADAOAccessCheck` 模块提供；Core、
   testbench 和 Python oracle 不得各写一套不一致规则。

**用户确认（2026-10-26，选择 A）**：以最新 `Machine-01` 为准。
Exit-port MMIO 已删除，旧 Exit 地址和 UART 地址均按 `UNMAPPED`
处理；`DADAOParams` 删除 `exitBase/exitSize`。

**实现（2026-10-26）**：新增 `DADAOAddressMap.scala` 中的
`DADAOAccessCheck`，同时被 Core 和 test memory 使用。Core 在发出
fetch request 前检查取指地址，在进入 `DATA` owner 前检查 load/store
地址；fault 时 PC 保持、寄存器不写、数据请求不发出。test memory
复用同一模块，地址 fault 优先于 sparse entry（稀疏条目）缺失。
取指请求宽度必须是 tetra（4 字节），否则在映射和对齐检查后返回
ILLI。

### D6：`ldm/stm` 循环与精确提交

**提案**：

- `count` 取自 `immu6`，合法范围 `1..63`。
- 地址在指令开始时只计算一次：

```text
base = RB[rbhb] + RD[rdhc]
```

- 后续元素使用 `base + i*N`；即使寄存器范围包含 `rdhc`，也不能在
  中途改变基址。
- 所有元素在发起首个请求前完成范围、映射、对齐和访问种类预检：
  - `start + count > 64` -> `ILLI`；
  - `count=0` -> `ILLI`；
  - 任一地址未映射 -> `UNMAPPED`；
  - 基址未对齐 -> `MALIGN`；
  - 只读/非法访问 -> `ILLI`。
- `ldm` 使用结果缓冲 `Vec(63, UInt(64.W))`：
  - 全部元素成功后才在同一提交周期写连续目的寄存器；
  - 任一响应 fault 时丢弃整个缓冲，不产生部分寄存器写。
- `stm` 在预检通过后串行发起写请求：
  - 所有架构可判定的 fault 已在首个写请求前排除；
  - 已映射 RAM 的合法请求不会因地址种类再次触发 fault；
  - testbench 如注入非地址类内部错误，必须将其视为测试机错误，
    不得伪装成可精确回滚的 guest 异常。
- `rb0` 在当前指令中作为源时始终读出当前指令 PC。
- `rd0` 作为 store 源读出 0；`ldm` 目的不得越过 `rd63`。
- 多寄存器访问保持 instruction-atomic（指令级原子）的架构可观测
  结果：成功时全部提交，fault 时全部不提交。

**待用户确认**：采用“全部预检后执行 + load 结果全缓冲 + store
只在确定无架构 fault 后发出”的方案。

**用户确认（2026-10-27）**：采用全部预检后执行、load 结果全缓冲、
store 仅在无架构 fault 后发出的方案。

**实现（2026-10-27）**：新增 `DADAOBlockMemExec`，覆盖 15 条
M1 `ldm/stm`。Core 先逐元素扫描地址并累计
`UNMAPPED > MALIGN > ILLI`，全部通过后串行访存。`ldm` 使用
63 项结果缓冲，最后一次成功响应时通过寄存器堆块写端口一次提交；
`stm` 预检失败时零数据请求。基址和偏移在指令开始时快照。

### D7：验证方案

**提案**：

1. `DADAOAddressMap` 单测：
   - RAM 起止边界、BootROM 起止边界；
   - 映射+未对齐组合返回 `UNMAPPED`；
   - ROM store、非法宽度返回 `ILLI`。
2. `DADAOByteLane` 单测：
   - 1/2/4/8-byte 在 8 个 lane 偏移上的大端映射；
   - `wstrb` 每一位；
   - byte merge 后未写 lane 保持原值。
3. `DADAOLoadStore` 单测：
   - 所有 30 条指令身份；
   - 每个宽度 signed/unsigned load；
   - RD/RB/RA 单寄存器 store/load；
   - `ldm/stm` 的 count=1、2、63、越界和基址快照。
4. Core/FSM 集成：
   - `reqReadyDelay=0/1/4`；
   - `memRespLatency=0/1/4`；
   - fetch 与 data 不重叠；
   - load/store 后正确 `PC+4`；
   - fault 时 PC 保持。
5. 独立 Python memory oracle：
   - 只从 `opcodes.yaml`、`legality_rules.yaml` 和公开地址图生成；
   - 逐 byte 计算期望存储器内容；
   - 不复用 Chisel/FSM 实现。
6. YAML 测试向量：
   - 每条指令至少一个正向向量；
   - 对齐、未映射、只读、零号寄存器、范围边界和端序反例；
   - 生成阶段结束后固定 SHA-256，测试阶段不得修改。
7. Negative gate（负例门控）：
   - 错端序、错 `wstrb`、错符号扩展、错 fault 优先级、错部分提交、
     错多寄存器步长均必须使检查真实失败；
   - 每次强制失败前后向量 SHA-256 必须不变。
8. 完整回归：
   - 保留 RTL-008t/RTL-009t 的 72 个测试；
   - 新增测试全部通过；
   - 保存真实命令、退出码、覆盖计数和日志。

**待用户确认**：采用上述七层验证和逐 byte oracle。

**用户确认（2026-10-27）**：进入 D7，采用独立 Python memory oracle、
YAML 向量、SHA-256 固定和 negative gate。

**实现与验证（2026-10-27）**：新增
`tools/rtl/check_dadao_memory_oracle.py`，生成
`tests/rtl/core/RTL-010t-memory-vectors.yaml` 和
`DADAOMemoryOracleTable.scala`。向量共 38 条，其中 30 条覆盖
M1 全部访存指令身份，8 条覆盖 UNMAPPED、MALIGN、ILLI、
优先级、块访问后段异常和部分提交边界。

验证分为两层：

- 30 条正向向量及静态/fault 元数据通过执行模块、byte lane 和
  address check 的独立组合探针验证；
- `stm` 后段 UNMAPPED 与 `ldm` 后段 response fault 继续通过
  Core/testbench FSM 验证原子提交。

完整 Chisel 回归为 20 suites / 101 tests / 101 passed / 0 failed；
35 个 YAML 的统一 SHA-256 清单一致，清单文件自身
SHA-256 为
`a91850ccb26f6337d741958e887ce07358347244ce5812d9dfb1e0cc702e2a5b`。
Python 端错端序、错 `wstrb`、错符号扩展、错 fault 优先级、
部分提交和块步长六类注入全部返回非零；Scala memory compare
negative gate 也真实失败。RTL 树检查与 19-patch Chipyard 树哈希
`9665eba976e214604582d7b810e7895d0383ce0d` 均通过。

## 实施分段

| 阶段 | 内容 | 出口条件 |
|---|---|---|
| `010t.1` | 地址图修正、共享 RegFile、Core 内存所有权 FSM | 原 67 测试无回归 |
| `010t.2` | 大端 byte lane、`wdata`/`wstrb`、sparse memory byte merge | lane 与存储器单测通过 |
| `010t.3` | 9 条单寄存器 load 与 6 条单寄存器 store | 15 条路径可追踪 |
| `010t.4` | 地址映射、对齐、fault 优先级和精确提交 | fault 反例通过 |
| `010t.5` | `ldm/stm`、结果缓冲、range 和基址快照 | 15 条路径可追踪 |
| `010t.6` | Python oracle、30 条覆盖、negative gate、完整回归 | 提交前审阅 |

每一阶段完成后汇报并停下等待确认；检查点 A（接口 + 单寄存器）、
B（多寄存器 + fault）、C（最终验证）分别请求 Git 提交确认。
未经用户明确确认，不执行 Git 提交或 push（推送）。

## 预计交付物

```text
rtl/dadao/src/main/scala/dadao/
├── DADAOCore.scala
├── DADAOIntExec.scala
├── DADAORegFile.scala
├── DADAOMemPort.scala
├── DADAOAddressMap.scala
├── DADAOByteLane.scala
├── DADAOLoadStore.scala
└── DADAOMemExecTable.scala

rtl/dadao/src/test/scala/dadao/
├── DADAOAddressMapSpec.scala
├── DADAOByteLaneSpec.scala
├── DADAOLoadStoreSpec.scala
└── DADAOMemoryIntegrationSpec.scala

tools/rtl/
├── generate_dadao_mem_exec_table.py
├── check_dadao_mem_coverage.py
├── check_dadao_memory_oracle.py
└── check_dadao_memory_oracle_negative.sh
```

实际文件名如调整，执行前更新任务书。

## 验收标准

1. 30/30 条 M1 访存指令有唯一执行描述和至少一条正向测试。
2. `1/106/30/15/4` 的 M1 分区保持不变。
3. 大端序在 1/2/4/8-byte、全部对齐偏移上逐 byte 正确。
4. 所有 store 只修改 `wstrb` 指定的 byte。
5. load 的 signed/unsigned 扩展正确。
6. `ldm/stm` 的 count、范围、步长和基址快照正确。
7. `UNMAPPED > MALIGN > ILLI` 的动态优先级正确。
8. `ILLI`、`MALIGN`、`UNMAPPED` 时 PC、寄存器和内存无部分提交。
9. fetch 与 data 请求不会同时占用内存端口。
10. request-ready 和 response-latency 参数化测试通过。
11. Python oracle 与 RTL 实现独立，所有 checker 有可达负例。
12. 测试向量生成后 SHA-256 固定，测试和 negative gate 前后一致。
13. RTL-008t/RTL-009t 无回归。
14. 未经确认不提交 Git，不修改 Chipyard 正式工作树。

## 风险

1. RAM 基址不一致已由 D1 修正为 `0xFC00_0000_0000`；后续地址检查
   仍须直接引用统一参数，禁止重新硬编码旧地址。
2. 把 RegFile 提升到 Core 会触及 RTL-009t 已验证路径，必须先做
   纯结构重构并跑完整回归。
3. 大端窄访存最容易把 guest byte 偏移与总线 lane 混淆；必须逐
   byte 验证。
4. `ldm` 多写和同周期范围写回容易产生部分提交，必须使用结果缓冲。
5. `stm` 的精确异常依赖完整预检；不能依赖“写到一半再尝试回滚”。
6. test memory 已在 D2 改为按 `wstrb` 逐 byte merge/store；D4 的
   store 路径复用该模型。
7. 多寄存器结果缓冲会增加寄存器数量和仿真开销，需要监控 Clab
   （云实验平台）内存。

## 决策确认

已确认：

1. D1：Core 共享 `RegFile`、`FETCH/DATA/IDLE` 状态机和 RAM
   基址修正。
2. D2：`addr + size + wdata + wstrb` 请求与大端 byte lane 映射。
3. D3：9 条单寄存器 load 和 signed/unsigned 扩展。
4. D4：6 条单寄存器 store、右对齐 `wdata` 和写字节使能。
5. D5：RAM/BootROM 地址检查、自然对齐和
   `UNMAPPED > MALIGN > ILLI` 优先级。
6. D6：全部预检、load 缓冲和块写原子提交。
7. D7：独立 memory oracle、YAML 向量、SHA-256 和 negative gate。

## 参考

- `spec/SimRISC-01-取数存数.md`
- `spec/SimRISC-00-指令系统设计.md`
- `spec/DADAO-21-ABI-应用程序二进制接口.md`
- `spec/Machine-01-测试机运行环境.md`
- `.tao/adr/adr-0004-test-machine.md`
- `.tao/adr/adr-0012-simrisc-0.5.4-update.md`
- `.tao/adr/adr-0015-zero-register-as-source.md`
- `.tao/tasks/rtl/RTL-007k-RTL-M2启动与任务分解.md`
- `.tao/tasks/rtl/RTL-009t-RD整数执行与寄存器堆.md`
- `contracts/opcodes.yaml`
- `contracts/legality_rules.yaml`

## 实施进度

- `010t.1` D1：已完成。新增 Core 共享 `DADAORegFile`、
  `DADAOMemOwner` 状态机、RAM 基址修正和相关测试地址更新；
  RTL-010t D1 定向测试通过。
- `010t.2` D2：已完成。新增 `DADAOByteLane`，扩展
  `DADAOMemReq.wstrb`，test memory 改为按 byte merge/store；
  mask、merge、extract 和偏移读取定向测试通过。
- `010t.3` D3：已完成。新增 `DADAOLoadExec`，Core 在 `DATA`
  状态下完成单寄存器 load 请求、响应和写回；9 条 load 单元测试、
  Core/FSM 成功与 fault 集成测试通过。
- `010t.4` D4：已完成。新增 `DADAOStoreExec`；寄存器堆增加两个
  外部读口供 store 同时读取基址和源值，并保留独立 debug 读口。
  6 条 M1 store 生成右对齐 `wdata + wstrb`，经共享 `DATA` owner
  发出写请求；成功响应后 `PC+4`，fault 时 PC 保持且不写内存。
  定向测试覆盖六种变体、负立即数、RD/RB/RA 源 store-load 回读、
  `rb0=PC`、RA 源与 fault 无提交。
  最终完整 Chisel 回归为 16 suites / 81 tests / 81 passed /
  0 failed；Chipyard 1.14.0 编译与 CHIRRTL elaboration 通过，
  17 个 patch 的应用树哈希为
  `bf0772a9b90debd2519ffbc1d3c58a243d2219e2`。
- D4 验证工具：`check_rtl_tree_negative.sh` 使用 `flock` 互斥、
  `mktemp -d` 唯一工作目录和最小 RTL 复制；并发实例 fail-fast，
  临时目录与进程正常清理。
- `010t.4` D5：已完成地址检查模块、Core 发送前预检和 test memory
  共用规则；覆盖 RAM/BootROM 边界、完整访问区间、旧 Exit/UART
  未映射、自然对齐、区域权限和 fault 优先级。最终完整回归为
  17 suites / 88 tests / 88 passed / 0 failed；Chipyard 编译器与
  CHIRRTL elaboration 通过，18 个 patch 的应用树哈希为
  `fdd5ca44ddf2a95fa7c36fb34033903d329797cc`。
- `010t.5` D6：已完成 15 条 `ldm/stm`、全量地址预检、基址快照、
  63 项 load 缓冲和 RD/RB/RA 连续块写。覆盖 signed/unsigned
  narrow load、count=63 元数据、`stm` 写入后 `ldm` 回读、后续
  response fault 丢弃全部 load 缓冲，以及 `stm` 后段地址
  UNMAPPED 时零写请求。
  最终完整回归为 18 suites / 97 tests / 97 passed / 0 failed；
  Chipyard 编译与 CHIRRTL elaboration 通过，19 个 patch 的应用
  树哈希为 `4b29354fb71de718a6a86db44955bc2c95e57c75`。
- `010t.6` D7：已完成独立 memory oracle、38 条 YAML 向量、
  30/30 访存指令身份覆盖、逐 byte store 结果比较、8 条 fault 向量、
  SHA-256 固定和 negative gate。
  最终完整回归为 20 suites / 101 tests / 101 passed / 0 failed；
  35 个 YAML 的统一哈希清单一致；RTL 树检查和 Chipyard
  19-patch 检查通过。D6、D7 已分别完成本地提交，尚未 push
  （推送），当前等待上游作者审阅。
