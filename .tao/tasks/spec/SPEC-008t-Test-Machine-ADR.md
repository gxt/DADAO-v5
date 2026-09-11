# SPEC-008t: Test Machine ADR（复位/内存图/exit port/MALIGN 可观测）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-002t`、`SPEC-006t`、`VERIF-002t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-isa.md`（0.5.3，MALIGN/ILLI/UNDI/IALIGN/RASOF/RASUF 语义、复位值、对齐要求）
  - `verif/legality_rules.yaml`、`verif/opcodes.yaml`（SPEC-003t/VERIF-002t，异常触发条件）
  - `.tao/knowledge/contract-abi.md`（SPEC-006t，SP=rb1、栈/帧约定）
- 输出：`.tao/knowledge/adr-0004-test-machine.md`
- 约束：
  - **零 host 依赖**：所有可观测结果来自 QEMU exit code 或 guest 寄存器状态，不依赖 host log/stderr/超时
  - **可实现性**：决策须能在标准 QEMU `hw/dadao/` 机器实现，不需 out-of-tree patch
  - **精确异常承诺**：MALIGN/ILLI/UNDI 等为精确异常，须明确「无 commit = 哪些状态不变」
  - 对齐约束：exit port 写用 `st.o`（8B 对齐）；exit port 地址 8B 对齐
  - 复位值/exit port/内存映射 `spec/` 无依据 → 标「无 spec 依据，架构自定义」并给理由
  - 指令助记符用 0.5.3 命名；格式遵循 `adr-0001` 风格
  - 完成后不自行 commit

## 背景（完整）

### 目标

产出 `.tao/knowledge/adr-0004-test-machine.md`（ADR-0004），冻结后续 QEMU 裸机测试环境的
**所有可观测行为**，使测试断言完全依赖 guest-visible 状态，不依赖 host 日志、QEMU 输出或超时。

### 设计理由

- 后续 QEMU 实现必须在裸机（bare-metal）环境运行语义/合法性/边界向量测试，需要可编程报告
  pass/fail（exit port），以及对 MALIGN/ILLI/UNDI 等异常的 guest-visible 状态断言。
- `spec/` 提供部分异常语义，但未定义测试机器的内存映射、exit 协议或完整硬件复位值全集；
  本 ADR 作为原始决策填补这些空白。
- 直接 exit（而非安装 handler）避免预设未来异常模型，符合 M1 最小化原则。

### 关键概念 / 数据

**D1 内存映射**：ROM / boot ROM（起始、大小，须容纳最小 trampoline）、RAM（起始、大小，
须容纳测试程序+栈+数据）、Exit port（MMIO 地址，与 ROM/RAM 不重叠，8B 对齐）、保留区
（非 mapped 访问行为）。所有地址须为 48-bit 有效地址（0.5.3 有效地址低 48 位）。
参考布局：ROM `0x0010_0000`(64KB) / Exit port `0x1000_0000`(8B) / RAM `0x8000_0000`(128MB)。

**D2 复位向量与入口点**：硬件复位后 PC（rb0）初值（`spec/` 为 `cfx_power_hypv_excp_vector`，
M1 bare-metal 下的等价值？）、测试程序加载地址、加载方法（flat binary 还是 ELF）、
RD/RB/RA/RF 硬件复位值（须从 0.5.3 `SimRISC-00` 推导 rf0/FCSR 位布局）。

**D3 Exit Port 协议**：字节宽度（建议 8B，与 `st.o` 对齐）、写入值语义（0=PASS，非零=FAIL）、
是否多字段编码、QEMU 行为（读 8B 值→取低字节→传播到 host `$?`）。须冻结带退出码的 QEMU API/机制。

**D4 MALIGN 可观测行为**：异常类型（guest 看到什么）、faulting PC（rb0？）、寄存器/内存提交
（精确异常：目标寄存器/内存**不写**，所有对齐异常同一规则）、测试断言方式。

**D5 ILLI/UNDI 可观测行为**：ILLI、UNDI、SBZ 非零（决策 ILLI 还是 UNDI）、IALIGN、RASOF/RASUF
的 guest 可观测状态、faulting PC、寄存器不提交；无 SEE 时 test harness 如何区分 fault 与正常 exit。

**D6 测试签名规范**：整合 D3/D4/D5 为测试程序可用的 API 规范（语义测试 pattern + 异常测试 pattern +
ROM trampoline），说明无 OS 下如何安装最小异常 handler 或 QEMU 直接映射 fault→exit code。

**0.5.3 助记符（示例/伪码必须使用）**：`set.zw`（原 `setzw`）、`st.o`（原 `sto`）、
`jump rbha, rdhb, imms12`（rrii 绝对跳转）、`add.si`、`br.nz`（原 `brnz`）、`ld.o`（原 `ldo`）、
`illi`（原 `unimp`）。

### 上游引用

- `.tao/knowledge/contract-isa.md` §2.6（合法性规则）、§2.7（异常）、§3–§6（load/store 对齐、
  ILLI/UNDI/MALIGN）、§5.6（RegRAS RASOF/RASUF）、§1.3（rb0 复位值、rf0）
- DADAO-0628：`code-agent/tasks/DL-003b-test-machine-adr.md`（完整转述；含 3 轮 Architecture Review）
- DADAO-0628：`docs/adr/0004-test-machine.md`（ADR 模板与最终 Accepted 决策）
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）
- 本项目：`.tao/knowledge/contract-abi.md`（SP=rb1）、`verif/legality_rules.yaml`

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/adr-0004-test-machine.md` | M1 裸机测试机架构决策记录，覆盖 D1–D6，Status 先 Candidate，review 通过后 Accepted |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **ISA 来源版本**：0.4.1 → 0.5.3。异常条件/复位值/对齐要求以 v5 `contract-isa.md` 为准。
2. **指令助记符**：示例与伪码用 0.5.3 命名——`setzw`→`set.zw`、`sto`→`st.o`、`ldo`→`ld.o`、
   `brnz`→`br.nz`、`addi`→`add.si`、`unimp`→`illi`。
3. **rf0 复位常量**：0.4.1 ADR 初版写成 `0x07F87F8000000000`（字段位置错误），第二轮改为
   `0x7FF800007FC00000`。v5 必须从 **0.5.3 `SimRISC-00 §浮点状态寄存器`** 的位布局**独立推导**，
   不得照抄 0.4.1 常量；若 RF 完全 Excluded，可只实现 spec 规定的只读位、其余状态归零。
4. **RB 全 64 位语义**：0.5.3 RB `add.si` 为全 64 位运算，trampoline 构造地址/设栈指针的伪码
   应按 0.5.3 语义书写（`set.zw rb1, wpN, immu16` 写 wyde 并清其余 48 位）。
5. **有效地址 48 位**：0.5.3 有效地址为低 48 位、高 16 位在地址计算时被忽略；内存图地址与
   地址构造伪码须与此一致。
6. **异常命名/编号**：`unimp` 在 0.5.3 为 `illi`；exit code 数值 `spec/` 无依据，属机器约定。
7. **启动模型**：0.4.1 最终冻结「`-bios` trampoline + `-kernel` test binary 双镜像」；v5 须与
   ADR-0003（SPEC-007t）的 artifact pipeline 统一为唯一路径。

## 已知坑 / 结论

摘自 DL-003b 三轮 Architecture Review：

1. **P0 exit code API 失效**：普通 `qemu_system_shutdown_request()` 不传播 guest exit code；
   须冻结带退出码的 API/设备机制，并增加进程级验收测试（guest 写 0/1/0x7F/0x81/0x8F 后
   host 观察到完全相同的 8-bit status）。
2. **P0 D6 示例 ISA/ABI 错误**：SP 是 `rb1/rbsp`（不是 rb63）；`set.zw` 的 wyde 位算；
   `cmp` 目的不能用 rd0（触发 ILLI）；ROM→RAM 的 PCREL24 跨 128MB 需先构造绝对 RB 地址并用
   rrii 跳转；入口状态须区分 power-on reset / ROM 第一条 / RAM `_start` 三个时刻。
3. **P0 启动模型未冻结**：必须冻结唯一可自动化的启动协议（ROM 是内建 `-bios` blob 还是 loader
   直接设 PC 到 RAM），给出唯一命令行、镜像格式、ROM blob 布局、oversize/error 行为与 RAM entry。
4. **P1 rf0 常量不匹配位布局**：须从 spec 推导并给位段推导，不能声称错误常量「matching the wiki layout」。
5. **P1 MMIO/fault 矩阵未定义**：须为每个 memory-region × access-kind/width 组合给出确定结果；
   非 8-byte exit port 访问归 ILLI（合法 opcode + 非法操作数），不归 UNDI；为所有保留 fault code
   给出精确状态规则，或从 M1 表中删除未定义 fault。
6. **最终结论**：第三轮 Accepted，P0/P1 全部关闭（机制级 exit code、重写示例、冻结双镜像启动协议、
   修正 rf0、非 8B 访问归 ILLI）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-003b-test-machine-adr.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/docs/adr/0004-test-machine.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0001-greenfield-rebuild.md`（ADR 格式模板）
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-003a-elf-object-abi-adr.md`（加载协议需统一）
- 本项目：`.tao/knowledge/contract-isa.md`、`verif/legality_rules.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.tao/knowledge/adr-0004-test-machine.md` 存在，Status 先 Candidate（review 通过后 Accepted）
2. D1–D6 全部覆盖，无「待定」；D1 内存映射含地址/大小/属性且地址为 48-bit 有效地址
3. exit port 协议完整：地址 + 宽度 + 编码 + QEMU 行为（含带退出码 API/机制说明）
4. MALIGN 可观测行为给出完整 guest-visible 状态清单（异常类型、faulting PC、不提交的寄存器/内存）
5. ILLI/UNDI/SBZ/IALIGN/RASOF/RASUF 行为给出完整决策；SBZ 选 ILLI 或 UNDI 须有理由
6. 所有硬件复位值（RD/RB/RA/RF）给出完整冻结值；rf0 常量从 0.5.3 `SimRISC-00` 位布局推导
7. D6 示例使用 0.5.3 助记符且逐条手算地址；入口状态区分 power-on reset / ROM / `_start`
8. 唯一端到端启动协议（命令行、镜像格式、ROM 布局、RAM entry）与 ADR-0003（SPEC-007t）一致
9. MMIO × access-width 组合行为有确定结果；非 8B exit port 访问归 ILLI 并说明理由
10. 零 host 依赖约束可满足：所有 pass/fail/fault 均可由 `$?` 或 guest 寄存器断言

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
