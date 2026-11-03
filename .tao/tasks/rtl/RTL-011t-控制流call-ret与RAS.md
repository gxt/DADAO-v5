# RTL-011t: 控制流、call/ret 与 RAS

**模块**：rtl
**项目里程碑**：RTL-M2
**依赖**：`RTL-010t`（本地 merge commit `a2dc1f6a`）
**状态**：D5–D7 完成；审阅通过，待用户确认提交 PR
**最后更新**：2026-11-02

**目标**：在 RTL-010t 的单周期整数 Core（处理器核）上实现 M1 的
15 条控制流指令和 4 条系统 CFX（core function extension，核芯功能
扩展）指令入口；按 DADAO 的 IP（instruction pointer，当前指令地址）
语义完成 branch、jump、call、ret、RegRAS/MemRAS（寄存器/内存返回
地址栈）、精确异常和独立 oracle（独立期望值）验证。

## 版本基线

| 项目 | 当前版本 |
|---|---|
| 上游 DADAO-v5 | `8f669181` |
| SimRISC 规范正文 | `0.5.6-rc` |
| SimRISC 冻结机器契约 | `0.5.5` |
| Chipyard | `1.14.0` |
| Chipyard commit | `0acc1e1de2d3284bcd4d876956932a013ffe1949` |
| Chisel | `6.7.0` |
| 前置提交 | `a2dc1f6a` |

## 冻结输入

| 项目 | 冻结值 |
|---|---|
| M1 编码 | `contracts/opcodes.yaml`，156 条 |
| 本任务控制流范围 | 15 条 `br.*`/`jump`/`call`/`ret` |
| 本任务系统范围 | 4 条 `trap`/`escape`/`cfx2rd`/`cfx2rc` |
| IP | 当前正在执行的指令地址，不是下一条指令地址 |
| 顺序下一条指令 | `currentIp + 4` |
| 控制流计算 | 64-bit 全宽；取指使用结果低 48 bit |
| 地址宽度 | 48-bit 核内有效地址 |
| call 返回地址 | `(currentIp + 4)[47:0]`，依据 `ADR-0009` |
| ret 后 rb0 | `zero_extend48(poppedReturnAddress[47:0])`，依据 `ADR-0040` |
| 执行模型 | 单发射、单周期整数路径；内存/RAS 未就绪时 stall |
| 验证后端 | ChiselTest + Treadle |

## 包含

1. 10 条 `br.*`：
   - RD 形态：`br.n`、`br.nn`、`br.z`、`br.nz`、`br.p`、`br.np`；
   - RD 比较：`br.eq`、`br.ne`；
   - RB 形态：`br.z`、`br.nz`。
2. 2 条 `jump`：`iiii` 相对形式、`rrii` 基址加变址形式。
3. 2 条 `call`：`iiii`、`rrii`，包括返回地址计算和 RAS 压栈。
4. 1 条 `ret`：RAS 弹栈、可选 RD 返回值写回、完整 `rb0` 更新。
5. RegRAS 的 C1/C2/C3a/C3b 压栈路径和 D1/D2/D3/D4a/D4b 弹栈路径。
6. MemRAS 精确读写、RASOF/RASUF 和无部分提交。
7. `trap`/`escape`/`cfx2rd`/`cfx2rc` 的最小系统 CFX 语义入口。
8. 控制流目标与当前 IP 的 64-bit 计算、48-bit 取指、IALIGN。
9. 独立 Python oracle、控制流向量和 negative gate（负例门控）。
10. Core/testbench 集成测试和 Chipyard elaboration 回归。

## 不包含

1. `cfxld`/`cfxst`；二者仍为 `scope: excluded`。
2. 完整异常处理程序、可恢复中断、PTBR 和 MMU。
3. TileLink（片上总线协议）、UART、RAM、BootROM 正式 SoC 接入。
4. 浮点指令、RF 数据通路、LR/SC 和 cache。
5. 流水线、分支预测和推测执行。
6. 修改 `spec/` 或冻结机器契约。

## 控制流语义

### 条件跳转

条件成立时：

```text
br.eq/br.ne:
  target64 = rb0 + (sign_extend(imms12) << 2)

br.n/nn/z/nz/p/np:
  target64 = rb0 + (sign_extend(imms18) << 2)
```

条件不成立时：

```text
nextIp = currentIp + 4
```

predicate（判断条件）：

```text
br.n  : signed(value) <  0
br.nn : signed(value) >= 0
br.z  : value == 0
br.nz : value != 0
br.p  : signed(value) >  0
br.np : signed(value) <= 0
br.eq : rdHA == rdHB
br.ne : rdHA != rdHB
```

`br.z(rd0)` 恒真，`br.nz(rd0)` 恒假。RB 的 `br.z`/`br.nz` 按整
64-bit 判零。

### jump/call

```text
iiii:
  target64 = rb0 + (sign_extend(imms24) << 2)

rrii:
  target64 = rbHA + rdHB + (sign_extend(imms12) << 2)
```

`target64` 写回完整 `rb0`，取指使用低 48 bit。rrii 的 `rbHA` 只读。

### call/ret 提交

```text
call:
  returnAddress48 = (currentIp + 4)[47:0]
  RAS push
  rb0 = target64

ret:
  poppedReturnAddress48 = RAS pop low-48 result
  rb0 = zero_extend48(poppedReturnAddress48)
  optional rd = sign_extend64(imms18)
```

`call` 的压栈 fault、`ret` 的弹栈 fault 和 MemRAS fault 都不得提交
`rb0`、RA、RD 或内存的部分状态。

## RAS 语义

### 压栈

| 分支 | 条件 | 状态变化 |
|---|---|---|
| C1 | `RACNT == 0` | 新栈顶，计数 1，写返回地址，`RACNT=1` |
| C2 | `RACNT>0`、返回地址等于 `ra63[47:0]`、计数 `<0xFFFF` | 栈顶递归计数加 1，`RACNT` 不变 |
| C3a | 其余且 `RACNT<63` | 新栈顶，计数 1，`RACNT += 1` |
| C3b-RASOF | 其余且 `RACNT==63`、`MRPTR==0` | RASOF，零提交 |
| C3b-MemRAS | 其余且 `RACNT==63`、`MRPTR!=0` | `MRPTR-=8`，最旧条目写 MemRAS，再压入新栈顶 |

### 弹栈

| 分支 | 条件 | 结果 |
|---|---|---|
| D1 | `RACNT>0`、栈顶计数 0 | RASUF，零提交 |
| D2 | `RACNT>0`、栈顶计数大于 1 | 取得返回地址，计数减 1 |
| D3 | `RACNT>0`、栈顶计数等于 1 | 取得返回地址，弹出并减 `RACNT` |
| D4a | `RACNT==0`、`MRPTR==0` | RASUF，零提交 |
| D4b-count0 | MemRAS 条目计数 0 | RASUF，`MRPTR` 不变 |
| D4b-count1 | MemRAS 条目计数 1 | 取得返回地址，`MRPTR+=8`，`RACNT` 保持 0 |
| D4b-countN | MemRAS 条目计数大于 1 | 取得返回地址，条目计数减 1 后压栈，`MRPTR+=8`，`RACNT=1` |

## Decision 提案

### D1：复用 64-bit `pcReg` 作为完整 `rb0`

**已确认语义**：

- `rb0` 是完整 64-bit 架构寄存器；`rb0[63:48]` 不是恒零字段。
- branch/jump/call 写回完整 64-bit 结果。
- 顺序路径使用 `rb0 + 4`。
- call 返回地址为 `(currentIp + 4)[47:0]`。
- ret 后将弹出的 48-bit 返回地址零扩展到完整 64-bit `rb0`。
- 取指只使用 `rb0[47:0]`，并检查低两位对齐。

**用户确认（2026-10-31）的实现方案**：

- 直接复用 Core 现有 `pcReg[63:0]` 作为完整架构 `rb0`，不新增第二个
  `rb0Full` 存储寄存器。
- `DADAORegFile` 的 `rb0` 继续读取 Core 传入的 `io.pc`；写 `rb0`
  继续忽略。
- 新增组合信号 `fetchIp = pcReg[47:0]`，取指请求、取指访问检查和
  IALIGN 检查只使用该 48-bit 值。
- `pcReg` 必须保持 64-bit；若参数化宽度小于 64，则不得采用本方案。
- 顺序提交执行 64-bit `pcReg + 4`；branch/jump/call 提交完整
  `target64`；ret 提交 `zero_extend48(poppedReturnAddress[47:0])`。
- 新增统一 `nextRb0`/提交信号，保证 `rb0`、RA、RD、内存和 fault
  状态在同一提交边界生效。

寄存器堆现状不变：

```text
rd0       = 读取时硬连 0
rd1–rd63  = rdRegs[64]
rb0       = Core pcReg[63:0]
rb1–rb63  = rbRegs[64]，其中索引 0 为不可写保留槽
ra0       = raRegs[0][53:0]，高 10 位读取时清零
ra1–ra63  = raRegs[64]
```

### D2：branch/jump 重定向

**提案**：新增 `DADAOControlExec`，只负责 predicate、目标计算和
`branchTaken`；Core 在成功提交时选择 `rb0+4` 或 `target64`。

**用户确认（2026-10-31）**：进入 D2，并采用独立
`DADAOControlExec` + 统一 `nextRb0` 提交。

**实现结果**：已新增控制执行模块，覆盖 10 条 `br.*` 和 2 条
`jump`；call/ret 暂不进入该路径。

### D3：RegRAS

**提案**：新增 `DADAORas`，保存 63 个 RA 槽、`RACNT`、`MRPTR` 和
递归计数；C1–C3b、D1–D4b 使用唯一优先级状态机。

**用户确认（2026-10-31）**：进入 D3。

**实现结果**：新增 `DADAORas` 并成为 RA bank 的唯一存储。
RegRAS 的 C1/C2/C3a、RASOF 和 D1/D2/D3/D4a、RASUF 已实现。
C3b 的 MemRAS spill 与 D4b 的 MemRAS restore 暂 fail-closed，归 D4。

### D4：MemRAS

**用户确认（2026-10-31）**：采用 MemRAS 访问复用统一内存端口的方案。

**实现结果**：

- `DADAORas` 增加 `WaitAccept/WaitResponse` 状态，分别等待统一内存
  端口接收请求和返回响应。
- Core 增加 `Ras` 内存所有者；MemRAS 请求与 fetch/load/store 使用同一
  单未完成事务端口。
- C3b 在 `RACNT==63` 且 `MRPTR!=0` 时先写最旧条目，写成功后提交
  `MRPTR-=8`、寄存器栈前移和新栈顶。
- D4b 先读 `MRPTR` 指向条目，再按递归计数 0/1/N 选择
  `RASUF`、单条弹出或压入栈顶。
- MemRAS 地址按 8 字节对齐并以 `Octa` 数据访问；写请求设置全 8 字节
  byte-enable（`wstrb=FF`）。
- 地址映射、对齐或响应 fault 均不提交 `MRPTR`、RA、RD 或 `rb0`。

### D5：系统 CFX

**已确认并落地**：实现 `trap`、`escape`、`cfx2rd`、`cfx2rc` 的最小
系统 CFX（core function extension，核芯功能扩展）语义。

1. CFX profile（实现子集）为 `cfx0`/`cfx1`/`cfx2`/`cfx3`/`cfx63`。
2. 实现 `cg0`–`cg6` 共有寄存器，以及 `cfx0`–`cfx3` 的
   `cg8/rc1 global_cfx_intr_mask`（全局中断来源掩码）。
3. 权限由运行模式对应的来源 mask（掩码）和源 CFX 位共同决定；
   访问自身 CFX 只绕过 CFX 轴，不绕过运行模式轴。
4. 权限拒绝产生 `CFXPERM`（CFX 权限异常）并进入当前模式
   monitor（监控域）；保留 CFX 编号产生 `ILLI`（非法指令异常）。
5. 不存在、只读或非法组合产生 `CFXREG`（CFX 寄存器异常）；
   `escape` 帧/目标错误产生 `CFXESC`（CFX 返回异常）。
6. `cfx2rd`/`cfx2rc` 只连接 RD（结果寄存器组）。成功时
   `cfx2rd` 写 RD，`cfx2rc` 写 CFX；失败时 RD 与 CFX 均不部分提交。
7. `trap` 保存当前 IP（instruction pointer，指令指针）、运行模式和
   CFX mask，进入目标向量，并保存、屏蔽当前 monitor 的全局中断 mask。
8. `escape` 只允许当前 CFX，返回地址为
   `excp_cause_ip + {0, 4}`；成功时恢复运行模式、CFX mask 和
   `global_cfx_intr_mask`。
9. D5 不包含 semihosting（半主机调用）、异步中断仲裁和设备专有
   CFX 寄存器；这些不得据此任务宣称完成。

源码落点：

- `rtl/dadao/src/main/scala/dadao/DADAOCfx.scala`
- `rtl/dadao/src/main/scala/dadao/DADAOCore.scala`
- `rtl/dadao/src/test/scala/dadao/DADAOCfxSpec.scala`
- `rtl/dadao/src/test/scala/dadao/DADAOTestMemoryIntegrationSpec.scala`

### D6：验证

**提案**：

1. predicate、立即数正负和边界全部覆盖。
2. taken/not-taken、iiii/rrii、`rbHA=rb0` 特例覆盖。
3. C1–C3b、D1–D4b 每个分支至少一条正向和一条反例。
4. call 返回地址为 `(IP+4)[47:0]`。
5. ret 后完整 64-bit `rb0[63:48]==0` 有直接断言。
6. RASOF/RASUF/MemRAS fault 精确且零部分提交。
7. 独立 Python oracle 不从 RTL/RAS 实现导入。
8. 测试前后 SHA-256 清单一致，checker 有可达 FAIL 路径。

**执行结果（2026-11-02）**：

- 新增独立 oracle（基准模型）：
  `tools/rtl/check_dadao_control_oracle.py`；
- 新增 YAML（结构化向量）：
  `tests/rtl/core/RTL-011t-control-vectors.yaml`；
- 40 条控制流向量覆盖全部 15 条控制指令，包含 predicate、
  `rb0` 特例、`iiii`/`rrii`、立即数正负边界、call 返回地址和
  ret 零扩展；
- 8 类 CFX（core function extension，核芯功能扩展）向量覆盖
  `cfx2rd`/`cfx2rc`/`trap`/`escape`、权限与三类异常；
- 12 个 RAS（返回地址栈）向量覆盖 C1–C3b、D1–D4b、零计数和
  内存 fault；
- `DADAOControlOracleSpec`：41/41 通过；
- `DADAOCfxOracleSpec`：8/8 通过；
- `DADAORasOracleSpec`：12/12 通过；
- oracle negative gate：5 种注入错误和 1 种强制失败均真实返回
  非零，`VECTORS_UNCHANGED_DURING_NEGATIVE_GATE=1`；
- 全量 `sbt test`：27 suites / 192 tests / 192 passed / 0 failed；
- 全量测试前后 36 个 YAML 的 SHA-256 清单一致；
- RTL tree 检查与 22-patch Chipyard 树检查通过，tree hash（树哈希）
  为 `3ab8d8608235c9d758b373f480e645b8acded3ea`；
- 经用户确认后，四个 submodule 使用 `--depth 1` 浅初始化，
  工作树与 Git 元数据合计新增约 9.6 MiB；均检出固定 commit；
- Chipyard elaboration PASS：编译 322 个 Rocket Chip Scala 源文件和
  21 个 DADAO Scala 源文件；
- CHIRRTL 为 3,883,368 bytes，SHA-256
  `895c833c3dc17f154072dc151080ece881a4da1d3e7b6a4efb6b2171dfdf32b6`；
- SystemVerilog 为 6,909,337 bytes，SHA-256
  `b6ae740f4556b574f04d89996da7e2d761c0b4530b157e14f4d25c1cb343e199`；
- `check_dadao_verilog.py` PASS，`DADAOTop`/`DADAOTile`/`DADAOCore`
  层级和 firtool 版本均正确；
- D6 完成；D7 仍待审阅。

### D7：实施分段

| 阶段 | 内容 | 出口条件 |
|---|---|---|
| `011t.1` | 复用 64-bit `pcReg` 作为 `rb0` 并统一提交 | 完整 `rb0` 与 48-bit `fetchIp` 测试通过 |
| `011t.2` | branch/jump | taken/not-taken 和两种 jump 通过 |
| `011t.3` | RegRAS/call/ret | C1/C2/C3a/RASOF、D1/D2/D3/D4a/RASUF 通过 |
| `011t.4` | MemRAS | C3b/D4b、读写 fault 和零部分提交通过 |
| `011t.5` | 系统 CFX | 4 条系统指令正向/反例通过 |
| `011t.6` | 全量回归 | Chisel、oracle、elaboration 和 negative gate 通过 |

每阶段完成后汇报并等待用户确认，不自动进入下一阶段。

## 交付物

```text
rtl/dadao/src/main/scala/dadao/
├── DADAOControlExec.scala
├── DADAORas.scala
└── DADAOCore.scala

rtl/dadao/src/test/scala/dadao/
├── DADAOControlExecSpec.scala
├── DADAORasSpec.scala
└── DADAOControlIntegrationSpec.scala

tools/rtl/
├── check_dadao_control_oracle.py
└── check_dadao_control_oracle_negative.sh

tests/rtl/core/
└── RTL-011t-control-vectors.yaml
```

实际文件名如调整，执行前更新任务书。

## 验收标准

1. M1 分区保持 `1/106/30/15/4`，控制流 15/15 有执行路径。
2. `rb0` 保存完整 64-bit 值，取指只使用低 48-bit。
3. 顺序路径、branch、jump、call、ret 的 next-IP 选择唯一。
4. `call` 返回地址严格为 `(currentIp + 4)[47:0]`。
5. `ret` 后完整 `rb0` 严格等于零扩展的弹出返回地址。
6. C1–C3b、D1–D4b 全部状态变化与独立 oracle 一致。
7. RASOF/RASUF/MemRAS fault 无 `rb0`、RA、RD、内存部分提交。
8. IALIGN 在错误取指地址处精确触发。
9. 4 条系统 CFX 有正向、权限和 fault 反例。
10. Python oracle、YAML 向量和 negative gate 独立且可失败。
11. 测试前后向量及 oracle 哈希一致。
12. RTL-008t/009t/010t 无回归；Chipyard elaboration 通过。
13. 未经用户确认不提交 Git，不修改正式 Chipyard 工作树。

## 风险

1. 当前参数要求 `addrBits >= 48`；复用 `pcReg` 承载 `rb0` 时必须把
   该路径限制为 64-bit，禁止以 48-bit 配置进入控制流实现。
2. 顺序路径对 `rb0+4` 的高位进位行为必须与完整 64-bit 模型一致。
3. RAS 压栈/弹栈有多个优先级分支，错误优先级会产生静默状态错误。
4. MemRAS 访存需要多周期等待，必须保持当前 IP 不提前推进。
5. 系统 CFX 涉及运行模式、异常现场和权限，不能与普通提交混写。
6. 多状态模块可能增加 Elaboration 和仿真开销，需要监控 Clab 资源。

## 决策确认

1. 用户于 2026-10-29 确认 `ret` 后 `rb0[63:48]=0`，依据
   `ADR-0040`。
2. 用户于 2026-10-29 授权创建本任务书和 `ADR-0040`。
3. D1 的组合逻辑目标计算、顺序 IP 和控制流公式已按正文核对。
4. 用户于 2026-10-31 确认复用 64-bit `pcReg` 作为完整 `rb0`，
   取指使用 `pcReg[47:0]`，不新增 `rb0Full` 寄存器。
5. 用户于 2026-10-31 确认 D4。
6. 用户于 2026-11-02 确认 D5 的系统 CFX 范围与异常语义。
7. 用户于 2026-11-02 确认进入 D6，并授权四个 Chipyard submodule
   使用固定 commit 浅初始化；D6 已完成。

## 实施进度

- `011t.1` D1 上下文与取指地址：已完成。
  - `DADAOCore` 要求 `params.addrBits == 64`，并复用 `pcReg[63:0]`
    作为完整 `rb0`。
  - 新增组合信号 `fetchIp = pcReg[47:0]` 和零扩展
    `fetchAddress`；取指请求、取指访问检查和 IALIGN 只使用低 48 位。
  - 新增统一 64-bit `nextRb0`；现有顺序、load/store 和块访存
    成功路径均通过它提交 `pcReg`。
- `011t.1` 定向验证：PASS。
  - 命令：
    `sbt -batch 'testOnly dadao.DADAOFetchSpec dadao.DADAORegFileSpec'`
  - 结果：2 suites / 13 tests / 13 passed / 0 failed。
  - 退出码：`0`。
  - 日志：Clab
    `/home/ubuntu/user_doc/chipyard/1.14.0/.work/log/rtl/RTL-011t-011t.1-targeted-test.log`
- 完整回归：未完成，不能宣称 PASS。
  - `sbt -batch test` 在 Clab 上运行超过 20 分钟，仍处于
    `DADAOTestMemoryIntegrationSpec` 的 Treadle 周期仿真；为释放
    资源人工中止。
  - 中止前日志已经记录 `DADAOFetchSpec` 全部 5 个测试运行，且没有
    编译错误。
  - 日志：Clab
    `/home/ubuntu/user_doc/chipyard/1.14.0/.work/log/rtl/RTL-011t-011t.1-sbt-test.log`
  - 待后续夜间门控或更大规模 Clab 资源上补跑。
- `011t.2` branch/jump：已完成。
  - 新增 `DADAOControlExec`，解析 10 条条件分支和 2 条 `jump`。
  - 条件判断覆盖 N/NN/Z/NZ/P/NP/EQ/NE，并区分 RD/RB 源 bank。
  - branch 和 jump 均计算完整 64-bit 目标；branch 不跳转时提交
    `currentRb0 + 4`。
  - Core 通过两个外部寄存器读口取得源值，并统一用 `nextRb0`
    提交 IP 重定向。
  - call/ret 仍保持 fail-closed 的 `ILLI`，留到 D3。
- `011t.2` 定向验证：PASS。
  - 命令：
    `sbt -batch 'testOnly dadao.DADAOControlExecSpec dadao.DADAOFetchSpec dadao.DADAORegFileSpec'`
  - 结果：3 suites / 17 tests / 17 passed / 0 failed。
  - 退出码：`0`。
  - 覆盖：每个 branch predicate 的 taken/not-taken、两种 jump、
    full-64-bit 目标和 Core 中的实际 branch 重定向。
  - 日志：Clab
    `/home/ubuntu/user_doc/chipyard/1.14.0/.work/log/rtl/RTL-011t-011t.2-targeted-test.log`
- `011t.3` RegRAS/call/ret：已完成 D3 范围。
  - `DADAORas` 成为 RA bank 的唯一存储；RegFile 的 RA 读写、
    block/bulk copy 与 call/ret 共享同一状态。
  - call 在成功提交周期压入 `(currentIp + 4)[47:0]`。
  - ret 弹出 48-bit 返回地址，零扩展到完整 `rb0`，并支持可选 RD
    返回立即数。
  - 实现 C1、C2、C3a、RASOF、D1、D2、D3、D4a、RASUF。
  - C3b-MemRAS 和 D4b-MemRAS 在 D3 中明确 fault，留到 D4。
- `011t.3` 串行定向验证：PASS。
  - 命令：
    `sbt -batch 'set Test / parallelExecution := false' 'testOnly dadao.DADAORasSpec dadao.DADAOControlExecSpec dadao.DADAOFetchSpec dadao.DADAORegFileSpec'`
  - 结果：4 suites / 21 tests / 21 passed / 0 failed。
  - 退出码：`0`。
  - 日志：Clab
    `/home/ubuntu/user_doc/chipyard/1.14.0/.work/log/rtl/RTL-011t-011t.3-targeted-serial-test.log`
- `011t.4` MemRAS：已完成并定向验证。
  - `DADAORas` 实现 C3b spill 和 D4b restore，Core 新增 `Ras`
    内存所有者及 `memStart/memReqValid/memResp` 时序。
  - 修复 RegRAS 压栈时架构可见槽位前移的边界：
    `ra1..ra62` 均随最旧项退出而前移，避免 `ra1` 残留已溢出值。
  - `DADAORasSpec` 覆盖写回、单条恢复、多个递归条目恢复、
    `RASUF`、写 fault、读 fault 和未对齐零提交。
  - `DADAOCoreMemRasSpec` 覆盖 call 溢出后才跳转、ret 恢复后才返回、
    MemRAS 读 fault 时 IP 与 RA 保持原值。
  - 定向回归：4 suites / 24 tests / 24 passed / 0 failed；
    退出码 `0`。命令：
    `sbt -batch 'testOnly dadao.DADAORasSpec dadao.DADAOCoreMemRasSpec dadao.DADAORegFileSpec dadao.DADAOFetchSpec'`
  - D4 完成当时尚未执行全量 `sbt test`、negative gate 和
    Chipyard elaboration；这些项目由后续 D6 补足。
- `011t.5` 系统 CFX：已完成 D5 范围并定向验证。
  - 新增 `DADAOCfx`，集中保存运行模式、CFX 编号、CFX mask、
    异常现场、计数、scratch（暂存）寄存器和中断 mask。
  - 实现 `cfx0`/`cfx1`/`cfx2`/`cfx3`/`cfx63` 的 D5 寄存器子集。
  - 实现 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的权限、异常路由和
    RD 写回；失败路径保持精确、无部分提交。
  - 区分 reserved（保留）CFX 的 `ILLI` 与合法但未实现 CFX 的
    `CFXREG`。
  - 模块级 `DADAOCfxSpec`：1 suite / 6 tests / 6 passed / 0 failed。
  - Core 级 D5 过滤回归：1 suite / 5 tests / 5 passed / 0 failed。
  - 验证命令：
    `sbt -batch 'testOnly dadao.DADAOCfxSpec'`
    `sbt -batch 'testOnly dadao.DADAOTestMemoryIntegrationSpec -- -z D5'`
  - 日志：Clab
    `/home/ubuntu/user_doc/chipyard/1.14.0/.work/log/rtl/RTL-011t-D5-targeted.log`
  - D5 完成当时 D6 仍待执行；全量测试、negative gate 和哈希检查
    已在后续 `011t.6` 补足。
- `011t.6` D6：完成。
  - 独立 oracle、YAML、RTL 消费测试和 negative gate 已落地。
  - 全量 `sbt test`：27 suites / 192 tests / 192 passed / 0 failed，
    用时 1 小时 8 分 6 秒。
  - 测试前后 36 个 YAML 哈希清单完全一致。
  - RTL tree PASS；Chipyard 22-patch 结构检查 PASS，tree hash
    `3ab8d8608235c9d758b373f480e645b8acded3ea`。
  - 四个 submodule 已按固定 commit 浅初始化，合计新增约 9.6 MiB。
  - Chipyard elaboration PASS，CHIRRTL 3,883,368 bytes，
    SHA-256
    `895c833c3dc17f154072dc151080ece881a4da1d3e7b6a4efb6b2171dfdf32b6`。
  - SystemVerilog 6,909,337 bytes，SHA-256
    `b6ae740f4556b574f04d89996da7e2d761c0b4530b157e14f4d25c1cb343e199`。
  - `check_dadao_verilog.py` PASS；D6 完成。
- `011t.7` D7 审阅：完成。
  - 修复非 trap 异常 escape 错误恢复全局中断 mask 的问题；
  - 未实现 semihosting 的 trap 范围改为 fail-closed `ILLI`；
  - CFX 8/8、RAS 12/12 YAML 场景增加 RTL 自动回放；
  - 补 12/18/24-bit 和 full-64-bit 边界；
  - 最终全量、negative gate、哈希、RTL tree、22-patch 和
    elaboration 全部通过；
  - PR 文件范围仍需在提交前按用户确认整理。

## 参考

- `spec/SimRISC-00-指令系统设计.md`
- `spec/SimRISC-06-控制流.md`
- `spec/DADAO-12-SEE-主管系统运行环境.md`
- `spec/DADAO-13-HEE-超管系统运行环境.md`
- `.tao/contracts/contract-isa.md`
- `.tao/adr/adr-0004-test-machine.md`
- `.tao/adr/adr-0009-qemu-harness-methodology.md`
- `.tao/adr/adr-0012-simrisc-0.5.4-update.md`
- `.tao/adr/adr-0040-ret-rb0-high16-zero.md`
- `.tao/tasks/rtl/RTL-007k-RTL-M2启动与任务分解.md`
- `contracts/opcodes.yaml`
- `contracts/legality_rules.yaml`
- `tests/inst/base/ctrl-br.yaml`
- `tests/inst/base/ctrl-jump.yaml`
- `tests/inst/base/ctrl-call.yaml`
- `tests/inst/base/ctrl-ret.yaml`
