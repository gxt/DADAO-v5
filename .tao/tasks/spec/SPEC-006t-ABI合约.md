# SPEC-006t: ABI 合约（非变参标量调用约定）

**模块**：spec
**阶段**：4（对应 DADAO-0628 的 Phase 0.5A）
**依赖**：`SPEC-002t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）
  - `spec/DADAO-11-AEE-应用程序运行环境.md`（0.9.2）
  - `.tao/knowledge/contract-isa.md`（0.5.3，指令语义/寄存器模型基础）
- 输出：
  - `.tao/knowledge/contract-abi.md`（版本 0.9.2）
  - `verif/abi.yaml`（机器可读 ABI 事实）
- 约束：
  - Spec-first：每条规范性断言标注 `spec/` 章节来源，无来源的推论标 `[OPEN]`
  - 版本号 0.9.2，与 `spec/DADAO-21-ABI` 一致
  - **不照抄 0.4.1 的数据/编码**（寄存器编号/编码必须来自 0.5.3 `contract-isa.md`）
  - 高级 ABI（varargs / HFA / HPA / 聚合传参 / 多返回值）标 `Excluded from M1` 或 `Informative`，不得混入 M1 规范性内容
  - 指令助记符用 0.5.3 命名（见「关键概念」映射表），不得沿用 0.4.1 的 `addi`/`sto`/`setzw` 等
  - 完成后不自行 commit

## 背景（完整）

### 目标

从 DADAO-v5 `spec/` 的 ABI/AEE 文档撰写 `.tao/knowledge/contract-abi.md`，覆盖 M1 BasicCodeGen
所需的**非变参标量调用约定**：寄存器角色与调用者/被调用者分类、参数传递、返回值、栈帧布局、
调用序列（prologue/epilogue）、未决问题。ABI 合约须足以让后续 LLVM CodeGen 实现正确的参数传递、
返回值处理和栈帧布局，不需要涵盖浮点 HFA/HPA 或复杂聚合的 M1 实现。

M1 scope 限定：**非变参函数**（no varargs）、**标量整数/指针参数和返回值**。
`verif/abi.yaml` 提供机器可读的参数/返回/保留寄存器集合，供 LLVM CallingConv/RegisterInfo 消费。

> DADAO-0628 对应任务 DL-002a 的原始目标即为此。v5 的差异是：规范版本从 SimRISC 0.4.1
> 升级到 0.5.3、ABI 从 0.1.0 升到 0.9.2，且 **RB bank 指针调用约定在 0.9.2 中已原生规定**
> （0.4.1 时代合约初版只把标量/指针统一放 RD bank，直到 DL-069a 才补 RB bank）。

### 设计理由

- 合约是 LLVM CodeGen 的唯一 ABI oracle，必须独立于实现（不能从 LLVM 后端反推）。
- 三组参数寄存器（RD/RB/RF）各自独立计数是 DADAO ABI 的非显然核心约定，必须显式冻结，
  否则 caller/callee 会就参数落点产生分歧（0.4.1 的 DL-069a 正是这类分歧的实证）。
- M1 只做标量，但合约需为高级特性留出明确边界（标 Excluded），避免未冻结语义进入规范性内容。
- 每条断言可追溯到 `spec/` 章节，便于 spec 变更时做影响分析。

### 关键概念 / 数据

**§1 寄存器角色（来源 `spec/DADAO-21-ABI §寄存器规范`）**

- RD（rd0–rd63）：rd0=rdzero（硬连零）、rd1=rderrno、rd2–rd7=reserved（编译器不得分配）、
  rd8–rd15=临时、rd16–rd31=参数/临时、rd32–rd63=callee-saved
- RB（rb0–rb63）：rb0=rbip（PC）、rb1=rbsp（SP）、rb2=rbfp（FP）、rb3=rbgp、rb4=rbtp、
  rb5–rb7=reserved、rb8–rb15=临时、rb16–rb31=参数/临时、rb32–rb63=callee-saved
- RF（rf0–rf63）：rf0=FCSR；M1 **Excluded**（不使用）
- RA（ra0–ra63）：由 `call`/`ret` 自动压/弹（ra63=RegRAS 栈顶），不属 caller/callee-saved 框架；
  压栈溢出 RASOF、弹栈下溢 RASUF（详见 AEE）
- M1 可分配集与 non-allocatable 集合须明确（rd1/rb3/rb4 在 wiki 中 callee-saved 栏为 `-`，
  须冻结 M1 的保守策略并标 `[OPEN]`）

**§2 参数传递（来源 `spec/DADAO-21-ABI §传参`）**

- 三 bank 独立计数、从 16 开始、不共享槽位。类型→bank：整数/标量→RD（rd16–rd31）、
  指针/地址→RB（rb16–rb31）、浮点→RF（Excluded）
- 标量提升：<8B 类型提升到 8B，按源类型决定符号/零扩展（`char`/`short`/`int`/enum 符号扩展；
  `unsigned`/`_Bool` 零扩展；64 位类型无需扩展）
- 寄存器溢出：三 bank **共享同一溢出区**，按全局声明顺序排列，每槽 8B，call 时 `sp+0` 起
- 规范示例（0.9.2 原文）：`read(int fd, void *buf, size_t count)` → fd=rd16、buf=rb16、count=rd17

**§3 返回值（来源 `spec/DADAO-21-ABI §返回值`）**

- 标量整数→rd31；指针/地址→rb31；浮点→rf31（Excluded）
- 窄返回值扩展规则须冻结（callee 扩展 / caller 不截断，或明确 OPEN），不得含糊
- 聚合 >64B → hidden sret，指针经 **rb16** 传入（M1 可标 Excluded/Informative）
- 多返回值：wiki 声明顺序与示例存在内部冲突，M1 标 Excluded/Informative

**§4 栈帧布局（来源 `spec/DADAO-21-ABI §函数调用规范 §The Stack Frame`）**

- SP=rb1，向下增长；FP=rb2（可选）；red zone 128B；`call` 时 SP 8B 对齐
- 帧布局：`rbfp+8n+8`=memory argument octa n、`rbfp+8`=memory argument octa 0、
  `rbfp`=previous rbfp、`rbfp-8` 及以下=saved regs/local vars 直到 `rbsp`
- 需给出 `incoming_sp`/CFA、首个溢出槽、saved-FP 槽的精确偏移，以及 SP-only 与 FP 两套
  对称、可汇编的 prologue/epilogue

**§5 调用序列**：caller/callee 职责、prologue/epilogue、`call`/`ret` 与 RegRAS 的关系
（指令编码引用 `contract-isa.md §5`，不重复定义）

**§6 未决问题**：varargs、HFA/HPA、聚合、多返回值、动态链接 TLS、帧指针省略等，逐项标 Excluded/OPEN

**0.5.3 指令助记符映射（撰写 prologue/epilogue 时必须使用右列）**

| 0.4.1 旧名 | 0.5.3 名称 | 说明 |
|-----------|-----------|------|
| `addi` | `add.si` | riii，立即数自增/减；0.5.3 为**全 64 位**运算 |
| `sto` | `st.o` | 8 字节存储 |
| `ldo` | `ld.o` | 8 字节加载 |
| `setzw` | `set.zw` | rwii，写 16 位 wyde 并清其余 48 位 |
| `orw` | `or.w` | rwii，wyde 或合并 |
| `cmps` | `cmp.so` / `cmp.si` | 64 位/立即数有符号比较 |
| `brnz` | `br.nz` | riii，条件跳转 |
| `brz` | `br.z` | riii，条件跳转 |
| `unimp` | `illi` | 非法指令 |

**`verif/abi.yaml` 关键字段（示例，值以 `spec/` 为准）**：`format`、`version: "0.9.2"`、
`data_layout`、`stack_alignment`、`parameter_registers`（rd/rb/rf 各 [16,31]）、
`return_registers`（rd/rb/rf 各 31）、`callee_saved`（各 [32,63]）、`reserved_registers`。

### 上游引用

- `spec/DADAO-21-ABI-应用程序二进制接口.md` §寄存器规范 / §数据表示 / §函数调用规范 /
  §传参 / §栈溢出规则 / §可变参数 / §返回值 / §系统调用规范
- `spec/DADAO-11-AEE-应用程序运行环境.md`（RegRAS、不同宽度数据运算处理）
- `.tao/knowledge/contract-isa.md` §1（寄存器模型）、§4（地址/内存）、§5（控制流：call/ret/RegRAS）
- DADAO-0628：`code-agent/tasks/DL-002a-abi-contract.md`（完整转述；含 6 轮 Architecture Review
  的全部 P0/P1/结论）
- DADAO-0628：`contracts/abi/spec.md`（ABI 合约模板，注意其 Version 仍写 0.1.0）、
  `contracts/abi/README.md`
- DADAO-0628：`code-agent/tasks/DL-069a-rb-bank-pointer-calling-convention.md`（RB bank 指针
  调用约定的演进说明）

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/contract-abi.md` | 非变参标量 ABI 合约，版本 0.9.2；§1–§6 + 附录（spec 引用表） |
| `verif/abi.yaml` | 机器可读 ABI 事实：参数/返回/callee-saved/reserved 寄存器集合、数据布局、栈对齐 |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **版本与来源**：合约版本 0.1.0（Source: Wiki commit `13a414d`，SimRISC 0.4.1）→ **0.9.2**
   （Source: `spec/DADAO-21-ABI` 0.9.2，`spec.lock.toml` 锁定 `9e69b55d…`）。
2. **RB bank 指针调用约定**：0.4.1 合约初版只定义「整数/标量统一走 RD bank」，指针参数/返回值
   未走 RB；后端实现与文档分歧直到 DL-069a 才修复（指针参数 rb16–rb31、指针返回 rb31）。
   v5 的 0.9.2 `spec/DADAO-21-ABI §参数寄存器` **已原生**规定指针走 RB bank（并给出
   `read(fd,buf,count)` 示例），故 v5 合约应**从第一版起**就规范 RB bank 指针约定，无需 DL-069a 式补丁。
3. **指令助记符**：0.4.1 的 `addi`/`sto`/`ldo`/`setzw`/`orw`/`cmps`/`brnz` → 0.5.3 的
   `add.si`/`st.o`/`ld.o`/`set.zw`/`or.w`/`cmp.so`/`br.nz`（见映射表）；不得照抄 0.4.1 写法。
4. **RB 算术语义**：0.5.3 RB `add.si` 为**全 64 位**运算（0.4.1 存在 `addi` 高位保留问题，
   曾导致 DL-002a 第五轮 P0）。撰写 FP prologue/epilogue 时按 0.5.3 语义，不得沿用
   「高位保留」的旧规避写法（如 `rb2rb`+`addi` 拆分）而不加说明。
5. **参数寄存器示例**：0.9.2 明确给出 `read(int fd, void *buf, size_t count)` 的三 bank 独立计数
   示例（fd=rd16/buf=rb16/count=rd17），应写入合约。
6. **栈溢出示例**：0.9.2 给出 `foo(int a1..a17, double* p1..p17)` 的三 bank 共享溢出区示例
   （a17→sp+0、p17→sp+8），与 0.4.1 后期的跨 bank 交错示例一致，可直接采用。
7. **变参/聚合/HFA/HPA**：0.9.2 已完整定义（`§可变参数`、`§聚合类型参数`、`§返回值 §聚合类型返回值`）；
   DL-002a 当时按 M1 标 Excluded。v5 合约应把 M1 规范性范围限定在非变参标量，把这些标为
   `Excluded from M1` / `Informative`，并注明可后续扩展。
8. **浮点状态寄存器**：rf0/FCSR 字段定义来自 0.5.3 `SimRISC-00 §浮点状态寄存器`，不得照抄 0.4.1
   的 rf0 常量或位布局。

## 已知坑 / 结论

摘自 DL-002a 六轮 Architecture Review（0.4.1 时代）及其最终 Accepted 结论：

1. **P0 聚合参数与返回规则混淆**：`rd31`/`sret` 是**返回值**机制，不能用来描述普通参数；
   聚合参数规则是 HFA/HPA→对应 bank、≤32B 拆 RD 块、>32B 间接指针。M1 应直接标 Excluded，
   不给错误的规范性摘要。
2. **P0 FP prologue/epilogue 偏移不可实现**：必须定义 `incoming_sp`/CFA、首个 overflow slot、
   saved-FP slot 的精确偏移，并给出**成对**（入口/出口对称）的可汇编序列；`rbsp` 只需返回时
   恢复为 incoming value，不必额外 spill。
3. **P1 窄标量参数/返回扩展规则不完整**：须按源类型逐类冻结（signed/unsigned/`_Bool`/`char`/enum）；
   窄返回值扩展规则不得同时是 `[OPEN]` 又是规范性要求，必须二选一冻结。
4. **P1 三 bank 共享溢出区**：所有已溢出 RD/RB/RF 参数共享同一区域、按全局声明顺序排列，
   不是每 bank 各自排序；须给出 call 时 `sp+0` 基址公式与交错溢出示例。
5. **P1 rd1/rb3/rb4 的 `-` 不能生成保存掩码**：wiki 未分类，须冻结 M1 的 fixed/allocatable 属性
   （保守做法：不分配，保存语义标 OPEN），不能自行假定 caller-saved。
6. **P1 M1 scope 矛盾**：multiple-return 与 aggregate 必须明确移入 Post-M1/Informative 并标 Excluded，
   不能让未冻结语义进入规范性 contract。
7. **P0 FP prologue `addi rb2, rbsp, -8` 高位问题**（0.4.1）：已由 0.5.3 全 64 位语义消解，
   但 v5 撰写时仍须以 `contract-isa.md` 的 0.5.3 语义为准并自查。
8. **最终结论**：DL-002a 经六轮 review 后 Accepted；v5 应直接继承其已收敛的结论（三 bank 独立计数、
   共享溢出区、rd1/rb3/rb4 不分配、窄返回值冻结），避免重蹈返工。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-002a-abi-contract.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-069a-rb-bank-pointer-calling-convention.md`
- DADAO-0628：`.work/DADAO-0628/contracts/abi/spec.md`
- DADAO-0628：`.work/DADAO-0628/contracts/abi/README.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Phase 0.5A 段）
- 本项目：`spec/DADAO-21-ABI-应用程序二进制接口.md`、`spec/DADAO-11-AEE-应用程序运行环境.md`
- 本项目：`docs/phases/Phase4-ABI合约与架构决策.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/contract-authoring.md`、`.tao/knowledge/contract-isa.md`

## 验收标准

1. `.tao/knowledge/contract-abi.md` 存在，头部版本标注 **0.9.2**，来源指向 `spec/DADAO-21-ABI`（0.9.2）
2. 覆盖 §1 寄存器角色、§2 参数传递、§3 返回值、§4 栈帧布局、§5 调用序列、§6 未决问题
3. §2 明确三 bank 独立计数、指针参数走 **rb16–rb31**；§3 明确指针返回 **rb31**
4. 每条规范性断言标注 `spec/` 章节来源；无来源的推论标 `[OPEN]`，不猜测
5. 窄标量参数/返回扩展规则按源类型逐类冻结（或明确决策/OPEN），无自相矛盾
6. 三 bank 共享溢出区规则与至少一个跨 bank 交错示例齐全
7. prologue/epilogue 使用 0.5.3 助记符（`add.si`/`st.o`/`ld.o`/`set.zw` 等），给出 SP-only 与 FP
   两套对称序列，且偏移公式可汇编
8. varargs / HFA / HPA / 聚合 / 多返回值明确标 `Excluded from M1`（或 Informative），不与 M1 规范性内容混排
9. `verif/abi.yaml` 可被 `python3` 解析（YAML 合法），且与合约的寄存器集合一致
10. 无 0.4.1 的指令编码/数据被照抄（助记符、字段、编码值均来自 0.5.3）

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

（待填写）

#### 第 1 轮 reviewer 验收

（待填写）
