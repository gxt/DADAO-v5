# RTL-008t: 单周期取指与译码框架

**模块**：rtl
**项目里程碑**：RTL-M2
**依赖**：`RTL-007k`（`已验证`）
**状态**：待审阅

**目标**：在 RTL-M2 中建立单周期 Core 的取指、译码、控制信号和最小
testbench FSM（测试程序台有限状态机）执行循环；本任务不实现完整整数
执行、load/store、控制流或 RAS，只为后续任务建立稳定的指令进入和解码
边界。

**关联任务**：`RTL-007k`、`RTL-009t`、`RTL-010t`、`RTL-011t`、
`RTL-012t`、`RTL-013m`

## 背景

RTL-M1 已完成 `DADAOCore` 的接口骨架。当前 Core 只保留 PC 寄存器并
固定将内存请求设为无效，尚未取指、译码或推进 PC。

RTL-007k 已冻结 RTL-M2 的执行模型、testbench FSM 向量注入、内存握手和后续任务
边界。本任务只实现第一层：

```text
PC
    -> fetch request
    -> FSM memory response
    -> instruction word
    -> decoder/control
    -> next-PC/exception decision
```

## 冻结输入

| 项目 | 冻结值 |
|---|---|
| 规范 | SimRISC 0.5.5 |
| Chipyard | `1.14.0` |
| Chipyard commit | `0acc1e1de2d3284bcd4d876956932a013ffe1949` |
| Chisel | `6.7.0` |
| 指令编码 | `contracts/opcodes.yaml`，SimRISC 0.5.5；`scope: m1` 156 条，`fp` 66 条，`excluded` 2 条，`m3` 1 条 |
| 合法性规则 | `contracts/legality_rules.yaml` |
| 测试机 | ADR-0004 |
| RTL-M2 规划 | `.tao/tasks/rtl/RTL-007k-RTL-M2启动与任务分解.md` |
| 前置任务 | `RTL-007k`，`已验证` |

**术语说明**

- **fetch**：取指，从内存读取当前 PC 对应的指令字。
- **decode**：译码，从 32-bit 指令字提取格式、操作码和字段。
- **control signal**：控制信号，告诉后续执行模块该指令需要做什么。
- **testbench FSM**：测试程序台有限状态机，按周期响应内存请求并注入
  指令或数据，不作为硬件设备。
- **Decoupled**：带 `valid/ready` 的握手接口。
- **stall**：请求未完成时暂停状态推进。
- **ILLI**：非法指令异常。
- **UNDI**：未定义编码异常。
- **IALIGN**：指令地址未对齐异常。
- **SBZ**：应为零字段被写入非零值的约束。

## 范围

### 包含

1. 建立单周期取指状态机和 PC 更新规则。
2. 建立取指内存请求、响应等待和请求保持逻辑。
3. 建立 32-bit 指令字译码器。
4. 建立格式、opcode、寄存器字段、立即数字段和控制信号结构。
5. 识别 `UNDI`、`ILLI`、`IALIGN`、保留编码和取指 `UNMAPPED`。
6. 支持 `swym` 的 no-op 控制路径和顺序 PC 推进；`fence` 按 excluded→ILLI。
7. 建立最小 testbench FSM 向量注入和测试停止观测。
8. 建立解码覆盖、握手反例和异常反例门控。

### 不包含

1. 不实现 ALU、寄存器堆写入、立即数执行或完整 RD 语义。
2. 不实现 load/store、`ldm.*`、`stm.*` 或数据访存。
3. 不实现 branch、jump、call、ret、RAS 或控制流副作用。
4. Core 不实现 TileLink、外部 RAM、BootROM、UART 或 Exit；UART 仅允许
   作为 testbench 的测试向量传输通道，不进入 Core 端口或正式配置。
5. 不实现 cache、MMU、多核、中断、浮点、LR/SC 或特权 cfx。
6. 不修改 M1 向量期望值或现有 QEMU harness。

## Decision 提案

### D1：取指循环和状态推进

**提案**：Core 使用单 outstanding request 的取指循环：

```text
FETCH
    -> WAIT_REQUEST
    -> WAIT_RESPONSE
    -> DECODE
    -> NEXT_PC
```

- 取指请求的 `kind` 固定为取指类型；
- 请求地址为当前 PC；
- `req.valid && req.ready` 完成请求握手；
- 请求等待期间 `req.bits` 保持不变；
- 只有 `resp.valid && resp.ready` 后才解码；
- `resp.fault` 为非零时，不推进 PC，进入 fault 处理；
- 普通顺序指令在下一条指令地址可用后 PC 加 4；
- 本任务不执行分支和跳转侧效，只保留译码控制信号。

**用户确认（2026-10-13）**：D1 通过，保持本提案。

### D2：译码器和控制信号

**提案**：新增独立 `DADAODecoder` 和可测试的解码结果结构，至少包含：

- 原始 32-bit `word`；
- 格式 `format`；
- 主操作码和次操作码；
- RD/RB/RA/立即数字段；
- 操作类型和控制信号；
- `legal`、`fault` 和 `faultCode`；
- 是否为 no-op、是否未实现。

所有 QFC 主表、MISC 子表和保留单元格都必须机械枚举并分类：

- `scope: m1` 编码进入对应控制路径；
- `scope: fp`、`scope: excluded` 和 `scope: m3` 编码返回 `ILLI`；
- QFC/子表空白单元格返回 `UNDI`；
- 全零字 `0x00000000` 属于空白单元格，返回 `UNDI`，不再存在名为 `illi`
  的可执行指令；
- SBZ、非法操作数和当前任务未实现语义返回明确 fault，不得静默当 no-op。

**用户确认（2026-10-13）**：D2 通过，保持本提案。

### D3：PC、异常和提交规则

**提案**：

- `testMode=false` 时，复位 PC 为 `DADAOParams.resetVector`；
- `testMode=true` 时，允许 testbench 通过 `pc_init_valid/pc_init` 注入
  instruction-mode 初始 PC `0xffff_0000_0000`；
- 在发出取指请求前检查 PC 对齐；`PC[1:0] != 0` 直接产生 `IALIGN`，
  不发出内存请求；
- 取指响应 fault 原样传播；
- 解码失败或 fault 发生时，不写任何架构状态；
- 顺序指令只有在取指和译码均成功后才提交 PC+4；
- 本任务不写目标寄存器、不写数据内存、不更新 RA/RAS。

**用户确认（2026-10-19）**：D3 通过，保持本提案。

### D4：testbench FSM 向量注入

**提案**：

- `reset_window`：从 `0xffff_ffff_0000` 起 64 KiB，与架构 BootROM
  窗口一致；
- `ram_window`：从 `0xffff_0000_0000` 起 16 MiB；
- testbench FSM 根据 Core 的 `req.addr`（请求地址）返回对应指令或数据；
- FSM 支持可配置的 `req.ready`（请求可接受）、`resp.valid`（响应有效）
  延迟和 fault（故障）响应；
- FSM 配置增加参数 `memRespLatency`（内存响应延迟周期数），类型为非负
  `Int`，默认值为 `0`；测试至少覆盖 `0/1/2/4` 个周期；
- 响应延迟只属于 testbench FSM，不进入 `DADAOParams` 或正式 Core
  架构端口；
- Core 必须在 `resp.valid && resp.ready` 完成前保持 stall，不得提前
  提交 PC、寄存器或内存写；
- FSM 在复位前加载指令字和测试数据到内部向量表；
- Core 不提供后门内存加载端口；
- testbench 通过 sentinel、PC 或 test-complete 信号判断测试结束；
- test-only 端口不得出现在正式 Chipyard 集成配置中。

**用户确认（2026-10-19）**：D4 通过；确认使用 testbench FSM 和 UART
测试传输，不引入 Core UART 外设，并增加 `memRespLatency` 测试参数。

UART 测试帧（2026-10-19 用户确认，仅 testbench 使用）采用大端序：

```text
MAGIC(4)="DDAO" | VERSION(1) | TYPE(1) | SEQ(2) |
ADDRESS(8) | LENGTH(4) | PAYLOAD(N) | CRC32(4)
```

`CRC32` 覆盖 `VERSION` 至 `PAYLOAD`，不使用 `SOF`/`EOF`。首版类型为
`load`、`run`、`result`、`error`。本任务完成字节帧编解码和测试台闭环，
不实现 start/stop bit、baud 或 UART 位级串行时序。

### D5：验证和反例门控

**提案**：

1. Chisel 单元测试覆盖复位、PC 初始化、请求握手、响应延迟和 fault；
2. 解码器机械覆盖 QFC 主表、MISC 子表、全部 227 条已定义记录和
   保留单元格；覆盖清单必须给出枚举来源和计数；
3. 使用独立 Python oracle 逐字段比对解码结果；
4. 验证 `fp`/`excluded`/`m3`→ILLI、UNDI、IALIGN、SBZ 和取指
   UNMAPPED；架构 `faultCode` 保持 `ILLI`，test-only
   `debugFaultReason` 细分为 `ILLI_OPERAND`、`ILLI_FIELD`、
   `ILLI_SCOPE_FP`、`ILLI_SCOPE_EXCLUDED`、`ILLI_SCOPE_M3`；
5. 注入请求未保持、响应未握手、错误 PC、错误 fault 和错误 decoder 结果，
   确认验证脚本真实失败；
6. 生成解码覆盖清单、异常统计和真实 `EXIT=0` 日志；
7. 向量 YAML 如需读取，运行前后生成 SHA-256 清单并逐字节比较。

**用户确认（2026-10-19）**：D5 通过；架构 faultCode 保持 ILLI，
testMode 下增加 debugFaultReason 细分；YAML expected_fault 仍使用
ILLI，其余验证要求保持。

## 交付物

```text
rtl/dadao/src/main/scala/dadao/
├── DADAOCore.scala
├── DADAODecoder.scala
└── DADAOControl.scala

rtl/dadao/src/test/scala/dadao/
├── DADAODecoderSpec.scala
├── DADAOFetchSpec.scala
├── DADAOTestMemory.scala
├── DADAOTestMemoryHarness.scala
├── DADAOTestMemorySpec.scala
├── DADAOTestMemoryIntegrationSpec.scala
├── DADAOTestUartFrame.scala
├── DADAOTestUartFrameSpec.scala
├── DADAODecoderOracleTable.scala
├── DADAOReservedCoverageTable.scala
└── DADAOReservedCellCoverageSpec.scala

tests/rtl/core/
└── RTL-008t-fetch-decode-vectors.yaml

tools/rtl/
├── check_dadao_decoder.py
├── check_dadao_decoder_negative.sh
├── check_dadao_static_legality.py
├── check_dadao_static_legality_negative.sh
├── check_dadao_cell_coverage.py
├── check_dadao_cell_coverage_negative.sh
├── check_dadao_decoder_oracle.py
├── check_dadao_decoder_oracle_negative.sh
├── dadao_uart_frame.py
└── check_dadao_uart_frame_negative.sh

20260929report/verification-logs/
├── RTL-008t-decoder-check.log
├── RTL-008t-fetch-smoke.log
├── RTL-008t-uart-frame-check.log
├── RTL-008t-uart-frame-negative.log
├── RTL-008t-static-legality-check.log
├── RTL-008t-static-legality-generator.log
├── RTL-008t-static-legality-negative.log
├── RTL-008t-cell-coverage-check.log
├── RTL-008t-cell-coverage-negative.log
├── RTL-008t-cell-coverage-sbt-test.log
├── RTL-008t-decoder-oracle-check.log
├── RTL-008t-decoder-oracle-negative.log
├── RTL-008t-decoder-oracle-sbt-test.log
└── RTL-008t-summary.log
```

实际文件名如需调整，必须在执行前说明并更新任务书。

## 验收标准

1. `rtl/dadao` 编译通过，现有测试不回归。
2. 请求/响应握手符合 RTL-007k D1，单 outstanding 和请求保持可验证。
3. QFC 主表、MISC 子表和保留单元格全部被分类，无静默丢弃或假绿。
4. `scope: m1` 编码可译码；`fp`/`excluded`/`m3` 和保留编码行为符合
   最新契约。
5. `IALIGN`、`ILLI`、`UNDI`、取指 `UNMAPPED` 有可达测试和负例。
6. `swym` no-op 路径不写 RD/RB/RA 或内存但 PC 正常推进；`fence` 返回
   ILLI。
7. PC 只在成功取指和译码后推进。
8. test-only PC 初始化和停止机制不影响正式配置。
9. 解码 oracle 与 DUT 分离，且不读取实现内部状态产生期望值。
10. 所有验证脚本均有可达 FAIL 路径，恢复后重新通过。
11. 保存真实命令、退出码、覆盖计数和 SHA-256。
12. 正式 Chipyard 工作树未被修改。

## 下发前预检（待执行）

1. **任务书内部一致性**：检查 D1-D5、交付物和验收是否矛盾。
2. **依赖链实际可用性**：检查 `RTL-007k`、`DADAOCore`、`DADAOMemPort`、
   `opcodes.yaml`、`legality_rules.yaml` 和 Chisel 测试环境。
3. **验收可执行性**：标明每项验收在当前环境是否可跑，不能跑的写明原因
   和替代证据。
4. **与 spec/vectors 一致**：检查编码、格式、fault、PC 和 testbench FSM
   规则是否与 contract/spec/ADR 一致。

## 风险

1. 单周期取指与内存 stall 的组合容易产生重复提交或请求改变。
2. QFC 主表、MISC 子表和保留单元格的机械分类若依赖手工列表，容易出现
   遗漏或重复。
3. 解码器输出接口如果过早绑定执行实现，会阻塞后续 ALU/访存任务。
4. test-only PC 注入端口必须与正式 Core 配置严格隔离。
5. 取指异常和响应 fault 的优先级必须与 ADR-0004 一致。

## 完成区

D1-D5 已于 2026-10-19 逐条确认。当前已落地：

- 机械生成的 227 条编码表及 mask/value 译码器；
- 单 outstanding 取指、请求保持、响应等待、PC 提交和 fault 路径；
- testMode PC 注入、非法对齐和 test-only `debugFaultReason`；
- 稀疏 test memory model，支持请求就绪延迟、响应延迟
  `0/1/2/4`、store 更新、只读/未映射/注入 fault；
- Core 与 test memory 的集成 harness 和定向测试；
- testMode 下 `pcInitValid` 有效期间取指请求严格门控。
- test-only UART 字节帧编解码器、独立 Python CRC32 校验器、7 类负例和
  `LOAD -> Core -> RESULT` 帧闭环测试。
- 从 `opcodes.yaml` 机械生成 180 条 M1 静态合法性检查，覆盖目的寄存器
  非零、双目的冲突、`ret rd0` 限制、多寄存器零数量/范围/重叠和字段上限。
- 独立 Python static-legality oracle 逐条比较生成表；强制失败门控返回
  非零；重新生成表与仓库版本 SHA-256 完全一致；动态 `aligned(...)`
  规则保持留给地址计算路径，不进入译码器。
- QFC 主表 256 个 `op` 单元格、6 个 MISC dispatcher 和 6×64 个
  MISC 子单元格完成机械覆盖：主表定义 93、reserved 163；子表定义
  140、reserved 244；共 407 个 reserved 代表字均由真实 decoder
  验证为 `UNDI`。
- 独立 Python full-field decoder oracle 生成 227 条期望记录，逐项
  比较 word、id、format、scope、slot0–slot3、imm12/18/24、
  no-op、fault、faultCode、debug reason 和 unimplemented。

2026-10-19 覆盖与 oracle 收口后的完整 Chisel 测试结果：7 个测试套件、
33 个测试全部通过，
日志为 `20260929report/verification-logs/` 下的
`RTL-008t-decoder-oracle-sbt-test.log`、
`RTL-008t-cell-coverage-check.log`、
`RTL-008t-cell-coverage-negative.log`、
`RTL-008t-decoder-oracle-check.log` 和
`RTL-008t-decoder-oracle-negative.log`。

最终 summary 日志已落盘。执行级复审结论：

- 覆盖计数闭合：主表 `93 + 163 = 256`，MISC 子表
  `140 + 244 = 384`；
- 407 个 reserved 代表字均不匹配任何已定义 mask/value；
- 227 条 full-field oracle 与真实 decoder 输出一致；
- static-legality 重新生成结果逐字节一致；
- 所有脚本具有强制失败门控；
- 未发现阻断性 finding。

残余边界：M1 当前没有 fixed-bits-zero 静态规则；动态 `aligned(...)`
规则由后续地址计算路径实现；UART 位级串行接口不在 RTL-008t 内。
等待用户审阅并确认是否进入本地 Git 提交。

## 参考

- `.tao/tasks/rtl/RTL-007k-RTL-M2启动与任务分解.md`
- `.tao/tasks/rtl/RTL-002t-RTL源码与独立Chisel骨架.md`
- `.tao/knowledge/adr-0004-test-machine.md`
- `.tao/knowledge/adr-0012-chipyard-single-cycle-soc.md`
- `.tao/knowledge/contract-isa.md`
- `contracts/opcodes.yaml`
- `contracts/legality_rules.yaml`
