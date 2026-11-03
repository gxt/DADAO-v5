# RTL-009t: RD 整数执行与寄存器堆

**模块**：rtl
**项目里程碑**：RTL-M2
**依赖**：`RTL-008t`（待审阅，本地提交 `f29b178`）
**状态**：待验收

**目标**：在 RTL-008t 的取指/译码框架上建立 RD、RB、RA 三组
64×64-bit 寄存器堆和组合整数执行路径，完成 M1 中 106 条不访问内存、
不执行控制流/RAS 的整数与寄存器指令，并建立可重复的 ALU、
寄存器写回和独立 Python oracle（独立期望值来源）验证。

## 冻结输入

| 项目 | 冻结值 |
|---|---|
| 规范 | SimRISC 0.5.5 |
| Chipyard | `1.14.0` |
| Chipyard commit | `0acc1e1de2d3284bcd4d876956932a013ffe1949` |
| Chisel | `6.7.0` |
| 前置提交 | `f29b1785616bfe8b371aa3ad7be88a01b71169cb` |
| M1 编码 | `contracts/opcodes.yaml`，156 条 |
| 合法性 | `contracts/legality_rules.yaml` |
| 寄存器 | RD/RB/RA 各 64 个 64-bit 寄存器 |
| 执行模型 | 单发射、架构单周期、组合执行、时钟沿提交 |
| 验证后端 | ChiselTest + Treadle |

## M1 任务归属

| 任务 | 指令数 | 范围 |
|---|---:|---|
| `RTL-008t` | 1 | `swym` no-op |
| `RTL-009t` | 106 | 整数 ALU、立即数设置、条件赋值、寄存器块复制、`aip.si` |
| `RTL-010t` | 30 | `ld`/`st`/`ldm`/`stm` |
| `RTL-011t` | 15 | branch/jump/call/ret/RAS |
| `RTL-011t` | 4 | `cfx2rd`/`cfx2rc`/`escape`/`trap` 系统路径 |
| 合计 | 156 | M1 全量 |

## 范围

### 包含

1. 三组寄存器堆及特殊寄存器读语义：
   - `rd0` 恒为零；
   - `rb0` 读出当前指令地址 `pc`；
   - RA 寄存器在 RTL-009t 中按 64-bit 位型存取；`ra0[63:54]`
     SBZ 写无效，`[53:48]` RACNT 和 `[47:0]` MRPTR 保持位级
     存储。push/pop、递归折叠、RASOF/RASUF 等运行语义留给
     RTL-011t。
2. 6 条寄存器块复制：
   - `rd2rd`、`rb2rb`；
   - `rb2rd`、`rd2rb`；
   - `ra2rd`、`rd2ra`。
3. 7 条 16-bit 立即数设置：
   - `set.ow` 1 条、`set.zw` 2 条、`or.w` 2 条、`andn.w` 2 条。
4. 64/32/16/8-bit 加减、乘、除、余和加减双目的 128-bit 结果。
5. 64/32/16/8-bit 有符号/无符号比较。
6. 64-bit `and`/`or`/`xor`/`xnor`。
7. 64/32/16/8-bit 左移、逻辑右移、算术右移和 64-bit 扩展。
8. RB 加减、RB 立即数加减和 RB 无符号比较。
9. 5 条条件赋值 `cs.*`。
10. 每条指令的寄存器写向量、目标 bank 和提交规则。
11. 独立执行元数据生成器、ALU/RegFile 单元测试和 Python oracle。

### 不包含

1. load/store、块访存和大端 byte lane，归 RTL-010t。
2. branch/jump/call/ret/RAS，归 RTL-011t。
3. `cfx2rd`/`cfx2rc`/`escape`/`trap`，归 RTL-011t 系统路径。
4. FP/RF 指令语义。
5. 中断、异常 handler、流水线、cache 和 MMU。
6. `imm_range`（立即数超字段宽度）由汇编器/validator 静态拒绝。

## Decision 提案

### D1：寄存器堆结构

**提案**：

- 新增独立 `DADAORegFile`，内部含 RD/RB/RA 三个 bank，每个
  `Vec(64, UInt(64.W))`。
- 读端口为组合异步读；RTL-009t 暴露足够的固定读端口以覆盖：
  - RD 的 `rdha`、`rdhb`、`rdhc`、`rdhd`；
  - RB 的 `rbha`、`rbhb`、`rbhc`、`rbhd`；
  - RA 的 `raha`、`rahb` 等块复制字段。
- 4 个读端口是实现选择，不是 ISA 固定要求；其下限由单条指令
  最多读取的同类字段数决定。
- 写回使用 per-register write vector（逐寄存器写向量）：
  - RD/RB/RA 各 `Vec(64, Valid(UInt(64.W)))`；
  - 单目的指令只置一个 write；
  - 块复制可在同一个时钟沿写多个连续寄存器；
  - `rd0` 写被硬门控为零，`rb0` 写由静态合法性阻止；
  - `ra0[63:54]` 写入强制保持为零，`ra0[53:0]` 按指令结果保存。
- 四个组合读端口只用于普通标量指令。块复制不在外部逐寄存器读取，
  而使用 RegFile 内建的 bulk-copy（批量复制）路径：
  - 输入源 bank、目的 bank、源起始、目的起始、数量和 valid；
  - 组合读取内部源寄存器形成 snapshot；
  - 同一时钟沿生成多个目的 write；
  - 同 bank 重叠由 RTL-008t 静态合法性拒绝。
- 复位值：
  - RD 全部为 0；
  - RB `rb1`–`rb63` 为 0，`rb0` 不存储，组合读为当前 `pc`；
  - RA 全部为 0；`ra0[63:54]` 恒为 0。

**规范依据与实现选择**：

| 内容 | 性质 |
|---|---|
| RD/RB/RA 各 64 个 64-bit 寄存器 | SimRISC 规范 |
| `rd0` 恒零、目的写非法 | SimRISC 规范 |
| `rb0` 读出当前指令地址 | SimRISC 规范 |
| `ra0[63:54]` SBZ、`[53:48]` RACNT、`[47:0]` MRPTR | SimRISC 规范 |
| 四组寄存器包含 RF | SimRISC 规范，但 RF 不在 RTL-009t |
| RD/RB/RA 复位全 0，`rb0` 初始为 reset vector | ADR-0004 测试机约定，不是 SimRISC ISA |
| 4 个组合读端口 | 实现选择 |
| per-register write vector | 实现选择 |
| 单周期多写块复制 | 本 SoC 架构选择，满足 ISA 快照语义 |

**用户确认（2026-10-20）**：D1 通过。采用三 bank、每组 4 个标量
组合读端口、逐寄存器写向量和 RegFile 内部 bulk-copy 路径；
`rd0`、`rb0`、`ra0[63:54]` 写保护按上述规则实现。

### D2：执行元数据生成

**提案**：

- 新增 `tools/rtl/generate_dadao_exec_table.py`，从 `opcodes.yaml`
  和固定助记符/格式映射生成 `DADAOExecTable.scala`。
- 每条 RTL-009t 指令描述：
  - opcode id；
  - 目的 bank；
  - 源 bank；
  - 结果宽度 8/16/32/64；
  - signed/unsigned；
  - ALU 操作类型；
  - 立即数模式；
  - 单/双目的；
  - 条件赋值特殊模式。
- 生成器必须证明 M1 的 156 条被精确分成 1/106/30/15/4，
  不允许遗漏、重叠或静默归入“其他”。
- `DADAOExecTable` 只保存执行描述，不复制语义 oracle。

**用户确认（2026-10-20）**：D2 通过。执行描述符采用
operation/width/signedness、显式 source/destination bank 与字段偏移、
`destRead`、立即数模式、双目的和特殊模式；`rwii` 使用
`IMMU16_WYDE`，六个块复制使用 `COPY_BLOCK`；生成器必须严格验证
`1/106/30/15/4` 分区并由独立 Python checker 反向核对。

### D3：ALU 语义

**提案**：

- 新增 `DADAOALU`，纯组合逻辑，输入操作数、宽度、signedness
  （符号性）和操作类型，输出：
  - 低 64-bit 结果 `resultLo`；
  - 双目的指令的高 64-bit 结果 `resultHi`；
  - `resultValid` 和内部 fault 指示。
- 加法、减法、乘法和窄位宽结果按 contracted 符号/零扩展写满 64-bit。
- `add.uo/so`、`sub.uo/so` 计算 128-bit 和/差；`mul.uo/so`
  计算 128-bit 积，`resultHi` 写第一目的，`resultLo` 写第二目的。
- 除法/余数采用 truncate-toward-zero；除零和 `INT_MIN / -1`
  使用规范定值表，不产生运行时 fault。
- 比较结果写 `-1/0/1`；`-1` 统一写成 64 位全 1。源操作数仍按
  指令宽度截断，signedness 只影响源值比较。
- 移位结果按值语义写满 64-bit；register shamt 只取对应低位，
  immediate shamt 的字段合法性继续由 RTL-008t 静态检查。
- 64-bit `ext` 从 `hd/immu6` 指定起始位扩展。

**用户确认（2026-10-20）**：D3 通过。ALU 采用组合多操作数接口；
窄位宽比较先生成宽度内 less/equal/greater 码再按 signedness 扩展；
无符号减法双目的高位为 0/1 borrow；乘加减双目的产生 128-bit
high/low；除法使用 truncate-toward-zero 和定值表，不产生异常；
`cs.eq/ne` 通过条件写使能提交。

**SimRISC 0.5.5 修订（2026-10-27）**：上述窄位宽比较结果扩展规则
由 0.5.5 取代。`cmp.ub/uw/ut` 的 `-1` 必须写 64 位全 1，不再按
窄位宽零扩展；`.sb/.sw/.st` 同值。源操作数仍先截断后比较。

### D4：单周期提交和块复制快照

**提案**：

- 取指成功、译码无 fault 后，组合读寄存器、执行 ALU、生成写向量，
  在同一个时钟沿提交。
- 同一条指令的所有源操作数必须在任何寄存器写之前读取。块复制按递增
  顺序处理，但硬件语义等价于 source snapshot（源快照）。
- `rd2rd`/`rb2rb` 的源/目的范围重叠已由 RTL-008t 静态检查拒绝。
- 双目的指令允许一个目的为 `rd0`，对应结果丢弃；两个都能写时同时提交。
- `swym`、非法指令和 fault 不产生任何写向量。
- `rb0` 始终读当前指令地址，不因同一周期其他写回改变。

**用户确认（2026-10-20）**：D4 通过。所有 RD/RB/RA 写由
`archCommit` 总门控；成功指令在同一个时钟沿提交寄存器和 PC；
块复制使用 RegFile 内部 source snapshot；`rb0` 在块复制源中读当前
PC；`rd0`、`rb0`、`ra0[63:54]` 写保护不变；fault/reset/test-init
不产生部分写。

### D5：验证

**提案**：

1. RegFile 单测：
   - 64 个寄存器读写；
   - `rd0` 恒零；
   - `rb0` 等于当前 pc；
   - reset；
   - 单写、多写和块复制 snapshot。
2. ALU 单测覆盖：
   - 8/16/32/64-bit signed/unsigned 边界；
   - carry/borrow/high-half；
   - multiply high/low；
   - divide/remainder 定值与符号规则；
   - compare 的 −1/0/1；
   - shift 和 ext 的全部边界；
   - 条件赋值两个条件类。
3. 执行元数据覆盖：
   - 106/106 指令各有唯一执行描述；
   - M1 分区 1/106/30/15/4；
   - 生成结果逐字节可复现。
4. 独立 Python ALU oracle：
   - 为每个操作/宽度/signedness 生成定向与边界向量；
   - 不从 Chisel ALU 或 decoder 导入实现。
5. 负例门控：
   - 错 op、错宽度、错 signedness、错 high/low、错写 bank、
     错 rd0、错 fault 提交均必须真实失败。
6. 运行前后生成输入向量 SHA-256 清单；任何修改判定失败。

**用户确认（2026-10-20）**：D5 通过。采用 RegFile、ALU、
IntExec、106-descriptor 四层 Chisel 测试；独立 Python oracle 生成
YAML 审计向量和 Scala 期望表；测试前后逐文件 SHA-256 门控；每个
checker 均必须具有可达的非零 negative gate。

### D6：实施分段

**提案**：

| 阶段 | 内容 | 出口条件 |
|---|---|---|
| `009t.1` | RegFile、特殊寄存器、写向量 | 单测通过 |
| `009t.2` | 执行元数据生成器和 106 条覆盖 | 分区与生成器门控通过 |
| `009t.3` | 基础 ALU：add/sub/logic/compare/shift/ext | 定向回归通过 |
| `009t.4` | mul/div/rem 和 128-bit 双目的 | 边界与定值测试通过 |
| `009t.5` | set/blocks/cs/RB 运算和 Core 集成 | 106 条执行路径可追踪 |
| `009t.6` | Python oracle、反例、全测试和日志 | 提交前审阅 |

**用户确认（2026-10-20）**：D6 通过。按 `009t.1` 至 `009t.6`
串行执行，每阶段完成后汇报并停下等待确认；检查点 A（RegFile +
执行描述符）、B（基础/乘除 ALU）和 C（集成 + 最终验证）分别
请求 Git 提交确认，未确认前不得提交。

## 交付物

```text
rtl/dadao/src/main/scala/dadao/
├── DADAORegFile.scala
├── DADAOALU.scala
├── DADAOIntExec.scala
└── DADAOExecTable.scala

rtl/dadao/src/test/scala/dadao/
├── DADAORegFileSpec.scala
├── DADAOALUSpec.scala
├── DADAOIntExecSpec.scala
└── DADAOExecOracleTable.scala

tools/rtl/
├── generate_dadao_exec_table.py
├── check_dadao_exec_coverage.py
├── check_dadao_alu_oracle.py
└── check_dadao_alu_oracle_negative.sh

20260929report/verification-logs/
├── RTL-009t-regfile-sbt-test.log
├── RTL-009t-alu-sbt-test.log
├── RTL-009t-exec-coverage.log
├── RTL-009t-alu-oracle-check.log
├── RTL-009t-negative-gate.log
└── RTL-009t-summary.log
```

实际文件名如需调整，在执行前更新任务书。

## 验收标准

1. RTL-008t 的 33 个现有测试无回归。
2. M1 分区严格为 `swym=1`、RTL-009t `=106`、memory `=30`、
   control `=15`、system `=4`。
3. RTL-009t 的 106 条身份均有唯一执行描述和至少一条语义测试。
4. `rd0`、`rb0`、RA 和 RF 的读写边界正确。
5. 128-bit 双目的结果、写回顺序和单周期提交正确。
6. 8/16/32/64-bit signed/unsigned 扩展正确。
7. 除法/余数定值表、符号和 truncate-toward-zero 正确。
8. 所有 fault 路径不产生部分写回。
9. Python oracle 与 RTL 分离，全部验证脚本存在可达 FAIL 路径。
10. 正式 Chipyard 工作树和 RTL-008t 已提交片段不被修改。
11. 保存真实命令、退出码、覆盖计数和 SHA-256。
12. Git 提交前再次请求用户确认。

## 风险

1. DADAO 不是 RISC-V；寄存器 bank、双目的和 `rb0` 语义必须按本规范，
   不得照搬 RISC-V 单寄存器堆模型。
2. 106 条执行身份若依赖手写表，容易遗漏；必须机械生成并反向覆盖。
3. 块复制多写和源快照容易产生顺序相关错误。
4. 窄位宽 signed/unsigned 扩展和 compare 值语义容易混淆。
5. 乘除高位、除零和 `INT_MIN / -1` 定值容易误用主机语言语义。
6. 多写端口可能增大 Elaboration/仿真开销，需要监控 Clab 内存。

## 参考

## 实施进度

- `009t.1` RegFile：已完成，6 个单测通过，完整回归 39 个测试通过；
- `009t.2` execution descriptor：已完成，106/106 覆盖，
  `1/106/30/15/4` 分区通过，独立 checker、negative gate、生成器
  逐字节复现和完整回归 45 个测试通过；
- `009t.3` 基础 ALU：已完成，add/sub、compare、logic、shift、ext
  和条件提交测试通过；negative gate 返回非零；完整回归 52 个测试通过；
- `009t.4` mul/div/rem：已完成，128-bit 高/低半、除零、
  `INT_MIN / -1` 和 truncate-toward-zero 测试通过；完整回归 55 个测试通过；
- `009t.5` IntExec/Core 集成：已完成，descriptor、RMW、set、
  块复制、条件写和同沿 PC/寄存器提交通过；完整回归 63 个测试通过；
- `009t.6` 最终验证：已完成，128 条独立 ALU oracle、106 条
  execution descriptor、17 个 YAML SHA-256 一致、四个 negative gate
  和完整回归 66 个测试通过；
- 检查点 A 已提交为 `a856023`，检查点 B 已提交为 `d39130b`；
  检查点 C 等待用户确认提交。

- `.tao/tasks/rtl/RTL-007k-RTL-M2启动与任务分解.md`
- `.tao/tasks/rtl/RTL-008t-单周期取指与译码框架.md`
- `.tao/knowledge/contract-isa.md`
- `.tao/adr/adr-0004-test-machine.md`
- `contracts/opcodes.yaml`
- `contracts/legality_rules.yaml`
