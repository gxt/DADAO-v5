# SPEC-004t: ABI 合约（M1 最小 ABI 事实）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-002t`
**状态**：已验证

## 范围（2026-09-12 变更）

- **M1 = 最小 ABI 事实**：寄存器角色 + `SP=rb1` + 栈向下增长 / `call` 时 8B 对齐 + `call`/`ret` 与 RegRAS 的关系。供 test machine（`SPEC-006t`）与 M1 集成使用。
- **完整调用约定**（参数寄存器分配、返回值、栈帧布局、三 bank 共享溢出区、prologue/epilogue）服务 **M2 BasicCodeGen**，标 `Deferred to M2`（见 `.tao/knowledge/deferred.md`）；本任务**不提取**，下方 §2–§6 内容仅作 M2 参考。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）
  - `spec/DADAO-11-AEE-应用程序运行环境.md`（0.9.2）
  - `.tao/knowledge/contract-isa.md`（0.5.3，指令语义/寄存器模型基础）
- 输出：
  - `.tao/knowledge/contract-abi.md`（版本 0.9.2）
  - `contracts/abi.yaml`（机器可读 ABI 事实）
- 约束：
  - Spec-first：每条规范性断言标注 `spec/` 章节来源，无来源的推论标 `[OPEN]`
  - 版本号 0.9.2，与 `spec/DADAO-21-ABI` 一致
  - **不照抄 0.4.1 的数据/编码**（寄存器编号/编码必须来自 0.5.3 `contract-isa.md`）
  - 完整调用约定（参数寄存器/返回值/栈帧/溢出区/prologue-epilogue）标 `Deferred to M2`；高级 ABI（varargs / HFA / HPA / 聚合传参 / 多返回值）标 `Excluded from M1`；均不得混入 M1 事实
  - 指令助记符用 0.5.3 命名（见「关键概念」映射表），不得沿用 0.4.1 的 `addi`/`sto`/`setzw` 等
  - 完成后不自行 commit

## 背景（完整）

### 目标

从 DADAO-v5 `spec/` 的 ABI/AEE 文档提取 **M1 所需的最小 ABI 事实**：寄存器角色（`rd0`=zero、`rb0`=PC、`rb1`=SP、`rb2`=FP、`ra`=RegRAS/MemRAS、`rf0`=FCSR 等）、`SP=rb1`、栈向下增长、`call` 时 SP 8B 对齐、`call`/`ret` 与 RegRAS 的关系。供 test machine（`SPEC-006t`）与 M1 集成使用。

`contracts/abi.yaml` 提供机器可读的 **M1 ABI 事实**（寄存器角色、SP、栈对齐）。完整调用约定标 `Deferred to M2`（见「范围」）。

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
- M1 可分配集与 non-allocatable 集合须明确（rd1/rb3/rb4 在 spec 中 callee-saved 栏为 `-`，
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
- 多返回值：spec 声明顺序与示例存在内部冲突，M1 标 Excluded/Informative

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

**`contracts/abi.yaml` 关键字段（示例，值以 `spec/` 为准）**：`format`、`version: "0.9.2"`、
`data_layout`、`stack_alignment`、`parameter_registers`（rd/rb/rf 各 [16,31]）、
`return_registers`（rd/rb/rf 各 31）、`callee_saved`（各 [32,63]）、`reserved_registers`。

### 上游引用

- `spec/DADAO-21-ABI-应用程序二进制接口.md` §寄存器规范 / §数据表示 / §函数调用规范 /
  §传参 / §栈溢出规则 / §可变参数 / §返回值 / §系统调用规范
- `spec/DADAO-11-AEE-应用程序运行环境.md`（RegRAS、不同宽度数据运算处理）
- `.tao/knowledge/contract-isa.md` §1（寄存器模型）、§4（地址/内存）、§5（控制流：call/ret/RegRAS）
- DADAO-0628：`code-agent/tasks/DL-002a-abi-contract.md`（完整转述；含 6 轮 Architecture Review
  的全部 P0/P1/结论）
- DADAO-0628：`contracts/abi/spec.md`（内容溯源，注意其 Version 仍写 0.1.0；合约格式见 v5 `.tao/knowledge/contract-authoring.md`）、
  `contracts/abi/README.md`
- DADAO-0628：`code-agent/tasks/DL-069a-rb-bank-pointer-calling-convention.md`（RB bank 指针
  调用约定的演进说明）

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/contract-abi.md` | M1 最小 ABI 事实（寄存器角色 + SP/栈对齐 + call/ret 引用），版本 0.9.2；完整调用约定标 `Deferred to M2` |
| `contracts/abi.yaml` | 机器可读 M1 ABI 事实：寄存器角色、SP、栈对齐（M1 部分） |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **版本与来源**：合约版本 0.1.0（Source: Wiki commit `13a414d`，SimRISC 0.4.1）→ **0.9.2**
   （Source: `spec/DADAO-21-ABI` 0.9.2，版本表见 `README.md`）。
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
5. **P1 rd1/rb3/rb4 的 `-` 不能生成保存掩码**：spec 未分类，须冻结 M1 的 fixed/allocatable 属性
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
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Spec Normalization 段）
- 本项目：`spec/DADAO-21-ABI-应用程序二进制接口.md`、`spec/DADAO-11-AEE-应用程序运行环境.md`
- DADAO-0628：`code-agent/tasks/DL-002a-abi-contract.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/contract-authoring.md`、`.tao/knowledge/contract-isa.md`

## 验收标准

1. `.tao/knowledge/contract-abi.md` 存在，头部版本标注 **0.9.2**，来源指向 `spec/DADAO-21-ABI`（0.9.2）
2. 覆盖 **M1 最小 ABI 事实**：寄存器角色（`rd0`/`rb0`/`rb1`/`rb2`/`ra`/`rf0`）、`SP=rb1`、栈向下增长、`call` 时 SP 8B 对齐、`call`/`ret` 与 RegRAS 的关系
3. 每条规范性断言标注 `spec/` 章节来源；无来源的推论标 `[OPEN]`，不猜测
4. **完整调用约定**（参数寄存器/返回值/栈帧/三 bank 共享溢出区/prologue-epilogue）明确标 `Deferred to M2`，不与 M1 事实混排
5. `contracts/abi.yaml` 可被 `python3` 解析（YAML 合法），含 M1 ABI 事实
6. 无 0.4.1 的指令编码/数据被照抄（助记符、字段、编码值均来自 0.5.3）

## 完成区

> **本区为 SPEC-004t 返工（第 2 轮）完成记录。** 初版（第 1 轮）的完整验收输出见「审阅记录 → 第 1 轮 reviewer 验收」。

**测试结果**：通过 4/4 核对脚本（退出码均 0）——
- `/tmp/opencode/SPEC-004t/check_callee_saved.py`（**本次返工新增**：`callee_saved` 索引与 `registers` 表自洽性，ALL PASS）
- `/tmp/opencode/SPEC-004t/check_abi.py`（abi.yaml YAML 解析 + M1 事实 + 边界，ALL PASS，回归）
- `/tmp/opencode/SPEC-004t/check_contract.py`（contract-abi.md 版本/来源/M1/边界/来源标注/无旧助记符，ALL PASS，回归）
- `/tmp/opencode/SPEC-004t/crosscheck_spec.py`（M1 事实逐项在 `spec/DADAO-21-ABI` 原文可查，ALL PASS，回归）
日志：`.tao/logs/SPEC-004t-rework-{check-callee-saved,check-abi,check-contract,crosscheck-spec}.log`。

**修改文件**：
- 修改 `contracts/abi.yaml`（`callee_saved` 索引语义注释：改为「各 bank 通用 callee-saved 块 32–63，不含 SP/FP」，删除 `mirror of registers` 声称）
- 修改 `.tao/knowledge/contract-abi.md` §3（措辞：`registers` 为逐寄存器权威来源；`callee_saved` 为派生索引、仅通用块 32–63；删除「一一对应」）
- 修改 `.tao/tasks/spec/SPEC-004t-ABI合约.md`（状态 + 完成区 + 第 2 轮自审）
- 初版交付物（第 1 轮）：新增 `.tao/knowledge/contract-abi.md`、`contracts/abi.yaml`

**验收结果**（关键命令与真实输出/退出码）：

```
$ python3 /tmp/opencode/SPEC-004t/check_callee_saved.py
registers.rd 标 callee_saved:true = [32..63]
registers.rb 标 callee_saved:true = [1, 2, 32..63]
registers.rf 标 callee_saved:true = [32..63]
PASS  callee_saved.rd 索引 == registers.rd 的 callee_saved:true 集合（精确镜像）
PASS  callee_saved.rf 索引 == registers.rf 的 callee_saved:true 集合（精确镜像）
PASS  callee_saved.rb 相对 registers.rb 的差集 == {rb1, rb2}（实际 [1, 2]）
PASS  callee_saved.rb 索引 == 通用块 [32, 63]
PASS  registers.rb1(rbsp) 仍标 callee_saved: true（spec: Yes）
PASS  registers.rb2(rbfp) 仍标 callee_saved: true（spec: Yes）
PASS  allocatable.rd 含通用 callee-saved 块 [32, 63]
PASS  allocatable.rb 含通用 callee-saved 块 [32, 63]
PASS  定位 callee_saved 索引块
PASS  abi.yaml 注释已文档化：callee_saved 不含 rb1/rb2，权威分类见 registers 表
PASS  contract-abi.md §3 不再声称索引与 §1「一一对应」
PASS  contract-abi.md §3 说明 callee_saved 为派生索引、仅通用块 32–63
PASS  abi.yaml YAML 合法且 version == 0.9.2
RESULT: ALL PASS            # EXIT=0

$ python3 /tmp/opencode/SPEC-004t/check_abi.py
abi.yaml 解析成功：顶层键 = ['allocatable','call_ret','callee_saved','contract',
  'data_layout','deferred_to_m2','excluded_from_m1','format','non_allocatable',
  'registers','reserved_registers','source','stack','version']
PASS version == "0.9.2" / format == dadao-abi
PASS stack.stack_pointer == rb1 / frame_pointer == rb2 / growth_direction == downward
PASS stack.stack_alignment == 8
PASS rd0=rdzero / rb0=rbip / rb1=rbsp / rb2=rbfp / rf0=fp_status / ra63=rasp / ra0=ras_control
PASS call/ret 与 RegRAS / RASOF/RASUF
PASS deferred_to_m2.{parameter_registers,return_registers,stack_frame_layout,shared_overflow_area,prologue_epilogue}
PASS excluded_from_m1 含 rf_all/varargs/hfa/hpa/aggregate_arguments/aggregate_return_sret/multiple_return_values
RESULT: ALL PASS            # EXIT=0

$ python3 /tmp/opencode/SPEC-004t/check_contract.py
PASS 头部版本标注 0.9.2 / 来源含 spec/DADAO-21-ABI / spec/DADAO-11-AEE
PASS M1 寄存器角色（rd0/rb0/rb1/rb2/ra63/rf0…）/ SP=rb1 / 栈向下增长 / call 8B 对齐
PASS Deferred to M2 覆盖 参数寄存器分配/返回值/栈帧布局/共享溢出区/prologue-epilogue
PASS Excluded from M1 覆盖 可变参数/HFA/HPA/聚合/多返回值
PASS 含 spec/ 章节来源标注（55 处）/ 含 [OPEN] / 来源标注无行号
PASS 无 0.4.1 旧助记符（addi/sto/ldo/setzw/orw/cmps/brnz/unimp 均未出现）
RESULT: ALL PASS            # EXIT=0

$ python3 /tmp/opencode/SPEC-004t/crosscheck_spec.py
PASS 寄存器角色 17 项（rdzero/rderrno/rdt0-rdt7/rda0-rda15/rbip/rbsp/rbfp/rbgp/rbtp/
     rbt0-rbt7/rba0-rba15/rft0-rft7/rfa0-rfa15/rasp/fp status regs/reserved/callee saved regs）
PASS 栈方向（"栈从高地址向下增长"）/ call 对齐（"call 指令执行时 sp 必须 8 字节对齐"）
PASS RASOF/RASUF / 大端序 / size_t
PASS Deferred/Excluded 章节出处全部在 spec 中
RESULT: ALL PASS            # EXIT=0

$ python3 -c "import yaml; yaml.safe_load(open('contracts/abi.yaml'))"
abi.yaml YAML OK, keys= 14  # EXIT=0

$ python3 -c "import yaml; d=yaml.safe_load(open('contracts/abi.yaml')); print(d['callee_saved'], d['allocatable']['rb'], d['version'])"
{'rd': [32, 63], 'rb': [32, 63], 'rf': [32, 63]} [[8, 15], [16, 31], [32, 63]] 0.9.2   # EXIT=0
```

**返工项处置**（architect 交叉复核 finding：`callee_saved.rb` 漏 rb1/rb2）：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `callee_saved.rb: [32,63]` 漏 `rb1`/`rb2`，与注释「mirror of registers」及 `contract-abi.md §3`「一一对应」不符 | ✅已修（选 **b：澄清语义**） | `abi.yaml`：索引注释改为「各 bank 通用 callee-saved 块（32–63），不含 SP/FP 等帧管理专用寄存器；逐寄存器权威分类见 `registers` 表」；`contract-abi.md §3`：改述为「`registers` 为权威来源，`callee_saved` 为派生索引、仅通用块 32–63」，删除「一一对应」 | `check_callee_saved.py` 13 项 ALL PASS（含差集恰为 {rb1,rb2}、rb1/rb2 仍标 callee_saved:true、注释已文档化、§3 无「一一对应」）；`check_abi`/`check_contract`/`crosscheck_spec` 回归 ALL PASS |

**选择 (b) 的理由**：
1. **最小修改（KISS）**：保持索引既有 schema（`bank: [lo,hi]`），无需改为 list-of-ranges，不破坏现有消费者契约。
2. **与既有事实一致**：`allocatable.{rd,rb}` 的通用可分配块即为 `[32,63]`，索引与之一致；SP/FP 已在 `non_allocatable` 单独登记。
3. **不丢 spec 事实**：`registers` 表仍按 spec `DADAO-21 §RB寄存器` 标 `rb1`/`rb2` 为 `callee_saved: true`，逐寄存器权威分类完整保留；索引仅作派生快速过滤视图。
4. **与 0628 先例一致**：DADAO-0628 `tools/abi.yaml` 的 `callee_saved.rb` 亦为 `rb32-rb63`（通用块），(b) 与其语义对齐。

**新发现/坑**：
1. **v5 spec 无 "red zone 128B"**：任务背景 §4 提到 red zone 128B，但 `spec/DADAO-21-ABI` / `DADAO-11-AEE` 全文均无 "red zone"/128B 相关文字（该说法源自 DADAO-0628 的 0.4.1 合约）。已在 `contract-abi.md §6` 标 `[OPEN]`（无 spec 来源），未混入 M1 事实。建议 M2 前确认是否引入。
2. **`abi.yaml` 的 `parameter_registers`/`return_registers` 放置**：任务 §「关键字段（示例）」列出这些字段，但「约束」要求参数寄存器/返回值属完整调用约定、标 `Deferred to M2` 且不得混入 M1。故本产出将其放在 `deferred_to_m2` 下（保留字段与值，明确非 M1 规范性），M1 事实只保留寄存器角色/SP/栈。
3. **rd1/rb3/rb4**：spec Callee-saved 栏为 `-`（未分类），M1 冻结保守策略=不分配，保存语义未冻结，已在 `contract-abi.md §1.6/§6` 与 `abi.yaml non_allocatable[status: OPEN]` 双处标 `[OPEN]`。
4. **数据布局**：`data_layout`（大端序 + 指针 8B）非任务「M1 范围」逐字列出，但为 `contracts/abi.yaml` 示例字段且是 `DADAO-21 §数据表示` 事实；已最小化提取（不含完整标量类型表）。
5. **（返工新增）分类索引是派生视图，非逐寄存器镜像**：`contracts/abi.yaml` 的 `callee_saved`/`reserved_registers` 是便于消费者读取的派生索引；`callee_saved` 只给「通用可分配 callee-saved 块 32–63」（与 `allocatable` 一致），不含 SP/FP 等帧管理专用寄存器。后续消费者做逐寄存器判定应以 `registers` 表为准，索引仅作快速过滤。

**遗留问题**：无（4 个核对脚本 ALL PASS；architect 交叉复核的 1 处 finding 已处置）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查者**：engineer（自主逐行审查；全局 `subagent_depth=1`，无法嵌套独立子代理）
**审查日期**：2026-09-13

**审查范围**：`contract-abi.md`（209 行）、`contracts/abi.yaml` 全文逐行；对照 `spec/DADAO-21-ABI`、`spec/DADAO-11-AEE`、`contract-isa.md`。

**检查项与结论**：
- 逻辑/事实正确性：寄存器角色表逐条与 `spec/DADAO-21 §寄存器规范` 一致（RD/RB/RF/RA 四表，含 ABI 名与 Callee-saved 栏）；SP=rb1、栈向下增长、`call` 8B 对齐均有 spec 原文；call/ret 与 RegRAS 仅作引用、未重复定义（指向 `contract-isa.md §5.4–§5.6`）。✅
- 边界分离：完整调用约定（参数寄存器/返回值/栈帧/共享溢出区/prologue-epilogue/系统调用）全部列于 §4 `Deferred to M2` 且未提取规范细节；高级 ABI 列于 §5 `Excluded from M1`；M1 事实（§1–§2）与二者无混排。✅
- 防造假：三个核对脚本均真实执行并留存日志（`.tao/logs/SPEC-004t-*.log`）；YAML 由 `python3 yaml.safe_load` 实解析。✅
- 来源标注：55 处 spec/ 章节引用，均无行号；无来源推论（rd1/rb3/rb4、窄返回值、多返回值冲突、red zone、帧指针省略）标 `[OPEN]`。✅
- 0.4.1 污染：未出现 `addi`/`sto`/`ldo`/`setzw`/`orw`/`cmps`/`brnz`/`unimp`；未照抄 0.4.1 prologue/epilogue（本合约不含该内容）。✅

**自审发现与处置**：

| finding | 严重度 | 处置 | 改了什么 | 复验证据 |
|---------|--------|------|---------|---------|
| §1.5 来源引用误加反引号 `` `[DADAO-11 §返回地址栈]` ``，与全文引用格式不一致 | 低危 | ✅已修 | 去反引号 | `check_contract.py` ALL PASS |
| §6 项 2「窄返回值扩展」标「标 Excluded」，与 §4「返回值 Deferred to M2」表述不一致 | 低危 | ✅已修 | 改为「返回值整体 `Deferred to M2`」 | 重跑 check_contract.py ALL PASS |
| §3 称 abi.yaml 的 deferred/excluded 节「仅为占位与索引」，实含 M2 参考值 | 低危 | ✅已修 | 改为「仅为 M2 参考与边界索引」 | 重跑 check_contract.py ALL PASS |
| 附录 A §2.1 第二来源缺 `DADAO-21-ABI` 前缀 | 低危 | ✅已修 | 补前缀 | 重跑 check_contract.py ALL PASS |

**判决**：**通过（无未修 finding）**，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立验证子代理）
**审查日期**：2026-09-13

**审查方法**：独立重跑全部验收命令 + 自编交叉验证脚本（69 项检查） + 手工对照 spec/ 原文。

---

##### 一、重跑记录

**1. 工程师核对脚本（独立重跑）**

```bash
$ python3 /tmp/opencode/SPEC-004t/check_abi.py
# 全文见上方独立执行结果
RESULT: ALL PASS
EXIT=0

$ python3 /tmp/opencode/SPEC-004t/check_contract.py
RESULT: ALL PASS
EXIT=0

$ python3 /tmp/opencode/SPEC-004t/crosscheck_spec.py
RESULT: ALL PASS
EXIT=0
```

日志已保存：`.tao/logs/SPEC-004t-review-{check-abi,check-contract,crosscheck-spec}.log`

**2. reviewer 独立交叉验证脚本（69 项）**

```bash
$ python3 /tmp/opencode/SPEC-004t-review/reviewer_crosscheck.py
# 覆盖：YAML 结构/栈/call-ret/寄存器角色(逐条)/allocatable/non-allocatable(OPEN)/
#        deferred(7项)/excluded(7项)/contract↔YAML 一致性/来源标注/无行号/无旧助记符/
#        Deferred 未混入 M1/data_layout
RESULT: ALL PASS (69/69)
EXIT=0
```

日志：`.tao/logs/SPEC-004t-review-crosscheck.log`

**3. YAML 独立解析**

```bash
$ python3 -c "import yaml; d=yaml.safe_load(open('contracts/abi.yaml')); print('keys:', sorted(d.keys())); print('version:', d['version'])"
YAML OK
keys: ['allocatable', 'call_ret', 'callee_saved', 'contract', 'data_layout', 'deferred_to_m2', 'excluded_from_m1', 'format', 'non_allocatable', 'registers', 'reserved_registers', 'source', 'stack', 'version']
version: 0.9.2
EXIT=0
```

**4. git status 核对**

```
Untracked:
  .tao/knowledge/contract-abi.md   ← 新增（交付物 ✓）
  contracts/abi.yaml                   ← 新增（交付物 ✓）
Modified:
  .tao/tasks/spec/SPEC-004t-ABI合约.md  ← 状态+完成区+审阅记录（预期修改 ✓）
```

与完成区「修改文件」声明一致。

---

##### 二、约束逐条核验

| # | 约束 | 判定 | 证据 |
|---|------|------|------|
| 1 | contract-abi.md 存在，版本 0.9.2，来源指向 spec/DADAO-21-ABI | ✅ | 文件第 3 行 `版本：0.9.2`，第 5 行来源含 `spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2） |
| 2 | 覆盖 M1 最小 ABI 事实：寄存器角色（rd0/rb0/rb1/rb2/ra/rf0）、SP=rb1、栈向下增长、call 8B 对齐、call/ret 与 RegRAS | ✅ | §1.1–§1.5 寄存器角色全覆盖；§2.1 SP=rb1/栈向下增长；§2.2 call 8B 对齐；§2.3 call/ret 与 RegRAS；YAML 全部对应 |
| 3 | 每条规范性断言标注 spec/ 章节来源；无来源推论标 [OPEN] | ✅ | 55 处 `[DADAO-21 §…]`/`[DADAO-11 §…]`/`[SimRISC-0X §…]` 引用，均无行号；5 处 `[OPEN]`（rd1/rb3/rb4 分类、窄返回值、多返回值冲突、red zone、帧指针省略） |
| 4 | 完整调用约定（参数寄存器/返回值/栈帧/溢出区/prologue-epilogue）标 Deferred to M2，不与 M1 混排 | ✅ | §4 列 7 项 Deferred 主题（含系统调用），仅登记主题+spec出处，**不提取规范内容**；M1 节（§1–§2）不含参数分配/返回值/栈帧布局/prologue-epilogue 详情 |
| 5 | contracts/abi.yaml 可被 python3 解析，含 M1 ABI 事实 | ✅ | `yaml.safe_load` 成功，14 个顶层键；M1 事实（stack/call_ret/registers/allocatable/non_allocatable）均存在且正确 |
| 6 | 无 0.4.1 旧助记符（addi/sto/ldo/setzw/orw/cmps/brnz/unimp） | ✅ | check_contract.py 扫描确认 0 个匹配；contract-abi.md 不含 prologue/epilogue 代码（M1 范围不含），无照抄风险 |

**额外核验项**：

| # | 项 | 判定 | 证据 |
|---|----|------|------|
| 7 | 高级 ABI 标 Excluded from M1（varargs/HFA/HPA/聚合/多返回值） | ✅ | §5 列 7 项 Excluded；YAML `excluded_from_m1` 含 7 项 |
| 8 | abi.yaml 的 parameter_registers/return_registers 放在 deferred_to_m2 下（不混入 M1 事实） | ✅ | YAML 结构确认：`deferred_to_m2.parameter_registers` / `deferred_to_m2.return_registers` 存在；M1 事实节不含这些字段 |
| 9 | rd1/rb3/rb4 在 YAML non_allocatable 中标 status: OPEN | ✅ | 3 条 OPEN 记录，与 contract-abi.md §1.6/§6 一致 |
| 10 | 版本号 0.9.2 与 spec/DADAO-21-ABI 一致 | ✅ | spec 第 4 行 `版本：0.9.2`，contract/YAML 均为 0.9.2 |
| 11 | data_layout（大端序/指针8B）正确 | ✅ | spec §数据表示 确认：`DADAO 采用大端序`、`any-type * sizeof=8`；YAML `endianness: big`, `pointer_size: 8` |
| 12 | "red zone 128B" 不在 v5 spec 中（工程师 [OPEN] 判断正确） | ✅ | `rg -i "red.?zone" spec/` 返回 0 匹配（exit=1）；该概念源自 DADAO-0628 的 0.4.1 合约，v5 spec 无此定义。工程师正确标 `[OPEN]` 并注明「无 spec 来源」 |

---

##### 三、事实正确性抽查（对照 spec/ 原文）

| 抽查项 | contract-abi.md | spec/DADAO-21-ABI 原文 | 一致？ |
|--------|----------------|----------------------|--------|
| rd0 = rdzero, Immutable | §1.2 表 | 第 18 行 `rd0 \| rdzero \| Zero \| Immutable` | ✅ |
| rb1 = rbsp, SP, Yes | §1.3 表 | 第 32 行 `rb1 \| rbsp \| stack pointer \| Yes` | ✅ |
| rb2 = rbfp, FP, Yes | §1.3 表 | 第 33 行 `rb2 \| rbfp \| frame pointer \| Yes` | ✅ |
| rf0 = FCSR | §1.4 表 | 第 47 行 `rf0 \| \| fp status regs \| -` | ✅ |
| ra0 = RAS control | §1.5 表 | 第 59 行 `ra0 \| \| RAS control（低48位=0 时仅 RegRAS；≠0 时同时启用 MemRAS） \| —` | ✅ |
| ra63 = rasp, RegRAS 栈顶 | §1.5 表 | 第 61 行 `ra63 \| rasp \| RegRAS 栈顶（call/ret 操作的寄存器） \| —` | ✅ |
| 栈向下增长 | §2.1 | 第 125 行 `栈从高地址向下增长` | ✅ |
| call 时 SP 8B 对齐 | §2.2 | 第 236 行 `call 指令执行时 sp 必须 8 字节对齐` | ✅ |
| RASOF/RASUF | §1.5 | 第 63 行 `压栈溢出触发 RASOF 异常，弹栈下溢触发 RASUF 异常` | ✅ |
| 大端序 | §1.7 | 第 71 行 `DADAO 采用大端序（big-endian）` | ✅ |
| size_t = unsigned long long | §1.7 | 第 101 行 `size_t类型的定义为unsigned long long` | ✅ |

---

##### 四、red zone 128B 核实

任务背景 §4 提到 `red zone 128B`，工程师发现 v5 spec 中不存在此概念并标 `[OPEN]`。

独立核实：
```bash
$ rg -i "red.?zone" spec/    # 0 匹配
$ rg "128.*byte|128B" spec/  # 仅匹配 128-bit 运算结果（无关）
```

结论：**工程师判断正确**。`red zone 128B` 源自 DADAO-0628 的 0.4.1 合约（`contracts/abi/spec.md`），v5 的 `spec/DADAO-21-ABI`（0.9.2）中确实未定义此概念。工程师将其标为 `[OPEN]` 并注明「不属 M1 事实，留 M2 确认」，处理恰当。

---

##### 五、与完成区自审结论的差异

| 项 | 工程师自审 | reviewer 独立验证 | 差异 |
|----|-----------|------------------|------|
| 核对脚本结果 | 3/3 ALL PASS | 重跑确认 3/3 ALL PASS | **一致** |
| YAML 解析 | OK, 14 keys | 独立确认 OK, 14 keys | **一致** |
| M1 事实齐全 | 全部覆盖 | 独立脚本 69 项 + 手工抽查 11 项，全部 PASS | **一致** |
| Deferred/Excluded 边界 | 已分离 | 确认 §4 不含规范内容提取、M1 节不含调用约定详情 | **一致** |
| 来源标注 | 55 处，无行号 | 确认 55+ 处引用，无行号 | **一致** |
| red zone [OPEN] | 判断正确 | 独立 rg 确认 spec 无此概念 | **一致** |
| 0.4.1 旧助记符 | 未出现 | 确认未出现 | **一致** |
| 修改文件 | 3 个 | git status 确认 3 个 | **一致** |

**无差异**。工程师自审结论准确、完整。

---

##### 六、判决

**Accepted**

全部验收标准通过，无阻塞缺陷。交付物 `contract-abi.md`（209 行）与 `contracts/abi.yaml`（134 行）正确覆盖 M1 最小 ABI 事实，边界分离清晰（Deferred/Excluded），来源标注规范，无 0.4.1 污染。red zone `[OPEN]` 判断正确。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：**Needs Revision**——M1 事实实质正确、范围落实、事实准确、red zone `[OPEN]` 处置正确；但发现 1 处 reviewer 未覆盖的低危**自洽性缺陷**。

**缺陷（低危）：`contracts/abi.yaml` 的 `callee_saved` 索引与 `registers` 表在 RB bank 上不一致**

- `registers.rb` 标 `rb1`(rbsp)/`rb2`(rbfp) 为 `callee_saved: true`（与 spec `DADAO-21 §RB寄存器` 及 `contract-abi.md §1.3` 一致）；
- 但分类索引 `callee_saved.rb: [32, 63]` **漏 rb1/rb2**，与注释「mirror of registers」及 `contract-abi.md §3`「与 §1 一一对应」的声称不符（`rd`/`rf` 两列确为精确镜像）。
- 影响：只读索引的消费者会漏掉 SP/FP 的保存语义；对 M1 test machine 无影响（其只用 `SP=rb1`/栈事实）。

**建议处置**：(a) 修正索引为真镜像（`callee_saved.rb` 含 rb1/rb2，并统一表示形式）；或 (b) 澄清索引语义为「各 bank 通用块（32–63），不含 SP/FP 等专用帧寄存器」。

**统一判决**：**Needs Revision**（返工项 = 上述索引不一致）。

#### 第 2 轮 engineer 自审（返工）

**审查者**：engineer（自主逐行审查；全局 `subagent_depth=1`，无法嵌套独立子代理）
**审查日期**：2026-09-13
**返工项**：architect 交叉复核 finding——`callee_saved.rb` 索引漏 rb1/rb2，与 `registers` 表及「mirror/一一对应」声称不符。
**处置选择**：**（b）澄清索引语义**（理由见完成区「选择 (b) 的理由」）。

**改动逐行审查**：
- `contracts/abi.yaml`（§分类索引）：新增 5 行注释，明确 `callee_saved` = 各 bank 通用 callee-saved 块（32–63），与 `allocatable` 一致；显式声明「不含 SP(rb1)/FP(rb2)」并指向 `non_allocatable` 与 `registers` 表；`rb` 行内注释再点明。索引值未变（`rd/rb/rf: [32,63]`），不改变消费者 schema。✅
- `.tao/knowledge/contract-abi.md §3`：将「其 M1 字段与本节 / §1 **一一对应**」改为「**一致**」，并补「`registers` 表为逐寄存器权威来源（rb1/rb2 依 spec 标 `callee_saved: true`）；`callee_saved`/`reserved_registers` 为派生分类索引，`callee_saved` 仅通用块 32–63」。无其他断言受影响。✅
- 逻辑/事实正确性：`registers.rb` 的 rb1/rb2 仍为 `callee_saved: true`（未动，spec-faithful）；索引与 `registers` 的差集恰为 `{rb1,rb2}`（帧管理专用，已文档化）；`allocatable.rb` 含 `[32,63]`，索引与之一致。✅
- 防造假：`check_callee_saved.py` 真实执行、日志留存 `.tao/logs/SPEC-004t-rework-check-callee-saved.log`；`check_abi/check_contract/crosscheck_spec` 回归日志同目录。✅
- 边界：未改动 M1 事实、Deferred/Excluded 边界、来源标注；无 0.4.1 污染。✅

**自审发现与处置**：

| finding | 严重度 | 处置 | 改了什么 | 复验证据 |
|---------|--------|------|---------|---------|
| 首次运行 `check_callee_saved.py` 注释检查 FAIL——脚本用 `raw.split("callee_saved:", 1)`，而 `callee_saved:` 首次出现在 `registers` 条目的键（`callee_saved: true`），取错区段 | 低危（测试脚本 bug，非交付物缺陷） | ✅已修 | 改用 `raw.rfind("\ncallee_saved:\n")` 定位索引块 | 重跑 `check_callee_saved.py` 13 项 ALL PASS，EXIT=0 |

**判决**：**通过（无未修 finding）**，状态置 `待验收`。

#### 第 2 轮 reviewer 验收

**审查者**：reviewer（独立验证子代理）
**审查日期**：2026-09-13
**审查范围**：返工项（`callee_saved` 索引语义澄清）+ 全量回归

---

##### 一、重跑记录

**1. 核对脚本（独立重跑，4 个）**

```bash
$ python3 /tmp/opencode/SPEC-004t/check_callee_saved.py
registers.rd 标 callee_saved:true = [32..63]
registers.rb 标 callee_saved:true = [1, 2, 32..63]
registers.rf 标 callee_saved:true = [32..63]
PASS  callee_saved.rd 索引 == registers.rd 的 callee_saved:true 集合（精确镜像）
PASS  callee_saved.rf 索引 == registers.rf 的 callee_saved:true 集合（精确镜像）
PASS  callee_saved.rb 相对 registers.rb 的差集 == {rb1, rb2}（实际 [1, 2]）
PASS  callee_saved.rb 索引 == 通用块 [32, 63]
PASS  registers.rb1(rbsp) 仍标 callee_saved: true（spec: Yes）
PASS  registers.rb2(rbfp) 仍标 callee_saved: true（spec: Yes）
PASS  allocatable.rd 含通用 callee-saved 块 [32, 63]
PASS  allocatable.rb 含通用 callee-saved 块 [32, 63]
PASS  定位 callee_saved 索引块
PASS  abi.yaml 注释已文档化：callee_saved 不含 rb1/rb2，权威分类见 registers 表
PASS  contract-abi.md §3 不再声称索引与 §1「一一对应」
PASS  contract-abi.md §3 说明 callee_saved 为派生索引、仅通用块 32–63
PASS  abi.yaml YAML 合法且 version == 0.9.2
RESULT: ALL PASS            # EXIT=0

$ python3 /tmp/opencode/SPEC-004t/check_abi.py
PASS  version == "0.9.2" / format == dadao-abi
PASS  stack.stack_pointer == rb1 / frame_pointer == rb2 / growth_direction == downward
PASS  stack.stack_alignment == 8
PASS  rd0=rdzero / rb0=rbip / rb1=rbsp / rb2=rbfp / rf0=FCSR / ra63=rasp / ra0=ras_control
PASS  call/ret 与 RegRAS / RASOF/RASUF
PASS  deferred_to_m2.{parameter_registers,return_registers,stack_frame_layout,shared_overflow_area,prologue_epilogue}
PASS  excluded_from_m1 含 rf_all/varargs/hfa/hpa/aggregate_arguments/aggregate_return_sret/multiple_return_values
RESULT: ALL PASS            # EXIT=0

$ python3 /tmp/opencode/SPEC-004t/check_contract.py
PASS  头部版本标注 0.9.2 / 来源含 spec/DADAO-21-ABI / spec/DADAO-11-AEE
PASS  M1 寄存器角色（rd0/rb0/rb1/rb2/ra63/rf0…）/ SP=rb1 / 栈向下增长 / call 8B 对齐
PASS  Deferred to M2 覆盖 参数寄存器分配/返回值/栈帧布局/共享溢出区/prologue-epilogue
PASS  Excluded from M1 覆盖 可变参数/HFA/HPA/聚合/多返回值
PASS  含 spec/ 章节来源标注（55 处）/ 含 [OPEN] / 来源标注无行号
PASS  无 0.4.1 旧助记符（addi/sto/ldo/setzw/orw/cmps/brnz/unimp 均未出现）
RESULT: ALL PASS            # EXIT=0

$ python3 /tmp/opencode/SPEC-004t/crosscheck_spec.py
PASS  寄存器角色 17 项（rdzero/rderrno/rdt0-rdt7/rda0-rda15/rbip/rbsp/rbfp/rbgp/rbtp/
     rbt0-rbt7/rba0-rba15/rft0-rft7/rfa0-rfa15/rasp/fp status regs/reserved/callee saved regs）
PASS  栈方向 / call 对齐
PASS  RASOF/RASUF / 大端序 / size_t
PASS  Deferred/Excluded 章节出处全部在 spec 中
RESULT: ALL PASS            # EXIT=0
```

日志已保存：`.tao/logs/SPEC-004t-review2-{check-callee-saved,check-abi,check-contract,crosscheck-spec}.log`

**2. YAML 独立解析**

```bash
$ python3 -c "import yaml; d=yaml.safe_load(open('contracts/abi.yaml')); print('callee_saved:', d['callee_saved']); print('allocatable.rb:', d['allocatable']['rb']); print('registers.rb callee_saved:true:', [r['range'] for r in d['registers']['rb'] if r.get('callee_saved') == True]); print('version:', d['version'])"
callee_saved: {'rd': [32, 63], 'rb': [32, 63], 'rf': [32, 63]}
allocatable.rb: [[8, 15], [16, 31], [32, 63]]
registers.rb callee_saved:true: [[1, 1], [2, 2], [32, 63]]
version: 0.9.2
EXIT=0
```

**3. git status 核对**

```
Untracked:
  .tao/knowledge/contract-abi.md   ← 新增（交付物 ✓）
  contracts/abi.yaml                   ← 新增（交付物 ✓）
Modified:
  .tao/tasks/spec/SPEC-004t-ABI合约.md  ← 状态+完成区+审阅记录（预期修改 ✓）
```

与完成区「修改文件」声明一致。

---

##### 二、返工项逐条核验

| # | 核验项 | 判定 | 证据 |
|---|--------|------|------|
| 1 | `callee_saved` 索引注释不再声称「mirror of registers」 | ✅ | `grep -n "mirror\|镜像" contracts/abi.yaml` 返回 0 匹配；注释（L99–104）改为「派生视图」「通用 callee-saved 块（32–63）」 |
| 2 | `registers.rb` 仍按 spec 标 rb1/rb2 `callee_saved: true` | ✅ | YAML L61-62：`{range: [1,1], abi_name: rbsp, callee_saved: true}` / `{range: [2,2], abi_name: rbfp, callee_saved: true}` |
| 3 | `callee_saved.rb` 索引语义 = 通用块 [32,63]，与 `allocatable` 一致 | ✅ | `callee_saved.rb: [32,63]`；`allocatable.rb` 含 `[32,63]`；差集 `{rb1,rb2}` 恰为帧管理专用 |
| 4 | `contract-abi.md §3` 不再声称「与 §1 一一对应」 | ✅ | L151：改为「其 M1 字段与本节 / §1 **一致**」；无「一一对应」 |
| 5 | `contract-abi.md §3` 说明 `callee_saved` 为派生索引 | ✅ | L151：「`callee_saved` / `reserved_registers` 为便于消费者读取的**派生分类索引**——`callee_saved` 索引只给出各 bank 的**通用 callee-saved 块（32–63）**」 |
| 6 | `contracts/abi.yaml` 可被 python3 解析 | ✅ | `yaml.safe_load` 成功，14 个顶层键，version=0.9.2 |
| 7 | 回归：原 4 个核对脚本 ALL PASS | ✅ | 4/4 ALL PASS，EXIT=0（上方重跑记录） |
| 8 | `git status` 与修改文件声明一致 | ✅ | 3 个文件：2 untracked + 1 modified，与完成区声明一致 |

---

##### 三、事实正确性抽查

| 抽查项 | abi.yaml | spec 原文 | 一致？ |
|--------|----------|----------|--------|
| rb1(rbsp) callee_saved: true | L61 `{range: [1,1], callee_saved: true}` | §RB寄存器 `rb1 \| rbsp \| stack pointer \| Yes` | ✅ |
| rb2(rbfp) callee_saved: true | L62 `{range: [2,2], callee_saved: true}` | §RB寄存器 `rb2 \| rbfp \| frame pointer \| Yes` | ✅ |
| callee_saved.rb 索引 = 通用块 | L107 `[32, 63]` | §RB寄存器 `rb32–rb63 \| callee saved regs \| Yes` | ✅ |
| 注释语义（派生视图） | L99-104「派生视图」「不含 SP/FP」 | — | ✅ 与 §3 一致 |

---

##### 四、与完成区自审结论的差异

| 项 | 工程师自审 | reviewer 独立验证 | 差异 |
|----|-----------|------------------|------|
| 核对脚本结果 | 4/4 ALL PASS | 重跑确认 4/4 ALL PASS | **一致** |
| callee_saved 索引语义 | 通用块 32-63，不含 rb1/rb2 | 独立确认：差集={1,2}，注释已文档化 | **一致** |
| §3 措辞 | 删除「一一对应」，改「一致」+派生说明 | 独立确认 L151：「一致」「权威来源」「派生分类索引」 | **一致** |
| registers.rb rb1/rb2 | 仍标 callee_saved: true | 独立确认 L61-62 | **一致** |
| YAML 解析 | OK, 14 keys | 独立确认 OK, 14 keys | **一致** |
| git status | 3 个文件 | 独立确认 3 个 | **一致** |

**无差异**。

---

##### 五、判决

**Accepted**

architect 交叉复核的 1 处返工 finding（`callee_saved.rb` 索引语义不一致）已通过方案 (b) 澄清语义修复：`abi.yaml` 注释明确索引为「派生视图、通用块 32–63、不含 SP/FP」；`contract-abi.md §3` 删除「一一对应」改为「一致」+ 派生索引说明。索引值未变，消费者 schema 不受影响。4 个核对脚本全部 ALL PASS（EXIT=0），回归无退化。

### 交叉复核（architect，返工后）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 第 2 轮的 **Accepted**（核心返工闭环）；另发现 1 处低危措辞问题，**已修正**。

**独立核对**：自建 25 项脚本 + 重跑 4 脚本均 ALL PASS；`callee_saved` 索引与 `registers` 表自洽（差集恰 `{rb1,rb2}`）、`registers` 仍权威、注释不再误称「mirror」、`non_allocatable` 兜底、`reserved_registers` 自洽。

**补充发现（低危，已修）**：返工新注释把「与 `allocatable` 一致」泛化到**各 bank**，对 **RF 不成立**（`allocatable.rf: []`、RF 整体 Excluded）。已限定为 `rd`/`rb`，并注明 RF 的 32–63 仅作 spec 事实登记、M1 不可分配（`abi.yaml` 注释 + `contract-abi.md §3`）。

**统一判决**：**Accepted**。
