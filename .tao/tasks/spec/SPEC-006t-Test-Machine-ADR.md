# SPEC-006t: Test Machine ADR（复位/内存图/exit port/MALIGN 可观测）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-002t`、`SPEC-004t`、`SPEC-008t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-isa.md`（0.5.3，MALIGN/ILLI/UNDI/IALIGN/RASOF/RASUF 语义、复位值、对齐要求）
  - `contracts/legality_rules.yaml`、`contracts/opcodes.yaml`（SPEC-003t/SPEC-008t，异常触发条件）
  - `.tao/knowledge/contract-abi.md`（SPEC-004t，SP=rb1、栈/帧约定）
- 输出：`.tao/knowledge/adr-0004-test-machine.md`
- 约束：
  - **零 host 依赖**：所有可观测结果来自 QEMU exit code 或 guest 寄存器状态，不依赖 host log/stderr/超时
  - **可实现性**：决策须能在标准 QEMU `hw/dadao/` 机器实现，不需 out-of-tree patch
  - **精确异常承诺**：MALIGN/ILLI/UNDI 等为精确异常，须明确「无 commit = 哪些状态不变」
  - 对齐约束：exit port 写用 `st.o`（8B 对齐）；exit port 地址 8B 对齐
  - 复位值/exit port/内存映射 `spec/` 无依据 → 标「无 spec 依据，架构自定义」并给理由
  - 指令助记符用 0.5.3 命名；格式遵循 `.tao/knowledge/adr-authoring.md`
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
RD/RB/RA/RF 硬件复位值（须从 0.5.3 `SimRISC-00` 推导 rf0/FCSR 位布局）。**RF 边界**：M1 排除 RF 指令，但测试机须确定性复位 `rf0`（按 spec 位布局）；**不实现任何 RF 指令语义**（RF 指令走 ILLI/UNDI 桩）。

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
- DADAO-0628：`docs/adr/0004-test-machine.md`（内容溯源：最终 Accepted 决策；ADR 格式见 v5 `.tao/knowledge/adr-authoring.md`）
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）
- 本项目：`.tao/knowledge/contract-abi.md`（SP=rb1）、`contracts/legality_rules.yaml`

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
   ADR-0003（SPEC-005t）的 artifact pipeline 统一为唯一路径。

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
4. **P1 rf0 常量不匹配位布局**：须从 spec 推导并给位段推导，不能声称错误常量「matching the spec layout」。
5. **P1 MMIO/fault 矩阵未定义**：须为每个 memory-region × access-kind/width 组合给出确定结果；
   非 8-byte exit port 访问归 ILLI（合法 opcode + 非法操作数），不归 UNDI；为所有保留 fault code
   给出精确状态规则，或从 M1 表中删除未定义 fault。
6. **最终结论**：第三轮 Accepted，P0/P1 全部关闭（机制级 exit code、重写示例、冻结双镜像启动协议、
   修正 rf0、非 8B 访问归 ILLI）。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-003b-test-machine-adr.md`（完整转述）
- DADAO-0628：`.dadao/DADAO-0628/docs/adr/0004-test-machine.md`
- v5：`.tao/knowledge/adr-authoring.md`（ADR 格式与模板）
- DADAO-0628：`.dadao/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-003a-elf-object-abi-adr.md`（加载协议需统一）
- 本项目：`.tao/knowledge/contract-isa.md`、`contracts/legality_rules.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.tao/knowledge/adr-0004-test-machine.md` 存在，Status 先 Candidate（review 通过后 Accepted）
2. D1–D6 全部覆盖，无「待定」；D1 内存映射含地址/大小/属性且地址为 48-bit 有效地址
3. exit port 协议完整：地址 + 宽度 + 编码 + QEMU 行为（含带退出码 API/机制说明）
4. MALIGN 可观测行为给出完整 guest-visible 状态清单（异常类型、faulting PC、不提交的寄存器/内存）
5. ILLI/UNDI/SBZ/IALIGN/RASOF/RASUF 行为给出完整决策；SBZ 选 ILLI 或 UNDI 须有理由
6. 所有硬件复位值（RD/RB/RA/RF）给出完整冻结值；rf0 常量从 0.5.3 `SimRISC-00` 位布局推导
7. D6 示例使用 0.5.3 助记符且逐条手算地址；入口状态区分 power-on reset / ROM / `_start`
8. 唯一端到端启动协议（命令行、镜像格式、ROM 布局、RAM entry）与 ADR-0003（SPEC-005t）一致
9. MMIO × access-width 组合行为有确定结果；非 8B exit port 访问归 ILLI 并说明理由
10. 零 host 依赖约束可满足：所有 pass/fail/fault 均可由 `$?` 或 guest 寄存器断言（harness 墙钟超时仅作兜底，不作为 pass/fail 判定）

## 返工要求（2026-09-13，用户决定）

ADR-0004 在本任务验收后经用户逐条重判修订（详见 ADR `## 修订`）：

- **D1**：内存映射改为**核内地址空间模型**（cfxcode 63/power）——boot ROM `0xffff_ffff_0000`(64KiB) / RAM `0xffff_0000_0000`(16MiB) / Exit port `0xffff_8000_0000`(8B)；`rb0` 复位 `0xffff_ffff_0000`（= spec 的 `cfx_power_hypv_excp_vector`）。
- **D3**：新增 harness **墙钟超时兜底**（默认 9s、可环境变量覆盖；超时记 harness 错误，不参与 pass/fail）。
- **D5**：机器 fault 退出码改为 **`0x80 | spec_cause_bit`**——ILLI `0x88`、UNDI `0x89`、RASOF `0x8A`、RASUF `0x8B`、MALIGN `0x8C`、IALIGN `0x8D`；unmapped `0x87`（测试机约定）。
- **D6**：示例地址/助记符修正（`set.zw rbha, wp2, 0xffff` 构造高位地址、`cmp.so` 寄存器比较消费 `rd17`、`st.o rd0` 写 PASS）。

**engineer 返工内容**：

1. **不得修改 ADR-0004 的决策内容**（已由用户决定）。
2. **更新验收脚本** `/tmp/opencode/SPEC-006t/check-adr0004.sh`：改为校验**修订后**的 ADR——新地址、新 fault 码（`0x87`–`0x8D`）、`Status=Accepted（rev…）`、超时兜底条款、`set.zw wp2`/`cmp.so`/`st.o rd0` 等；删除/替换所有旧值检查。
3. 重跑脚本至全 PASS（`EXIT=0`），记录输出。
4. 更新**完成区**（修改文件、验收结果、新发现）以反映修订后 ADR 与脚本。
5. 在**审阅记录**追加「返工轮」engineer 自审。
6. 不自行 commit。

## 完成区

> **返工更新（2026-09-13）**：ADR-0004 经用户逐条重判修订后，本完成区已整体刷新为**修订后**的验证结果；首次完成区的历史值（旧地址 / 旧 fault 码 / `Status=Candidate`）已被下方内容取代。ADR 决策内容由用户决定，本次返工仅更新验收脚本与任务文件，**未改动 ADR 任何决策内容**。

**测试结果**：通过 **109/109**（`bash /tmp/opencode/SPEC-006t/check-adr0004.sh`，`EXIT_CODE=0`）；失败原因：无。完整输出存 `.tao/logs/SPEC-006t-rework-verify.log`（138 行）。脚本覆盖：ADR 格式/状态（`Accepted（rev. 2026-09-13…）` + `## 修订` 段）、D1–D6 覆盖、**修订后内存映射**（boot ROM `0xffff_ffff_0000`/64 KiB、RAM `0xffff_0000_0000`/16 MiB、Exit `0xffff_8000_0000`/8 B、cfxcode 63、48-bit 核内有效地址）、exit 协议（地址/宽度/编码/带码 API/进程级验收）、复位值（含 rf0 位段推导、`rb0=0xffff_ffff_0000`）、**新 fault 码 `0x87`–`0x8D`**（unmapped/ILLI/UNDI/RASOF/RASUF/MALIGN/IALIGN）与 `0x80 | spec_cause_bit_index` 派生规则、旧映射（`0x81.*MALIGN`/`0x86.*RASUF`）已消失、MMIO×宽度矩阵、0.5.3 助记符（`set.zw`/`st.o`/`ld.o`/`br.nz`/`add.si`/`cmp.so`/`or.w`/`jump`/`illi`，含禁用旧助记符与 `wp3` 扫描）、**harness 墙钟超时兜底**（默认 `9 s`、环境变量覆盖、harness 错误、不参与 pass/fail）、无未决占位、ADR-0003 一致性、三入口时刻、零 host 依赖、地址算术独立复算（python，含 `set.zw wp2` 地址构造）。

**修改文件**：
- `/tmp/opencode/SPEC-006t/check-adr0004.sh`（验收脚本更新为校验修订后 ADR；旧地址/旧 fault 码/`Status=Candidate` 检查全部删除或替换，新增旧映射消失负向断言与 `set.zw wp2`/`cmp.so`/`st.o rd0` 校验）
- `.tao/tasks/spec/SPEC-006t-Test-Machine-ADR.md`（状态 `待返工`→`待验收`；完成区刷新；追加返工轮自审）
- `.tao/logs/SPEC-006t-rework-verify.log`（新增，脚本完整输出 + `EXIT_CODE=0`）
- **未改动**：`.tao/knowledge/adr-0004-test-machine.md`（用户既定决策；engineer 返工期间 `git diff` 为空；其后主会话修正 D6.4 距离与 `## 状态说明` 两处，见审阅记录）

**验收结果**（逐条对照验收标准，均针对修订后 ADR）：
1. 文件存在、`**状态**：Accepted（rev. 2026-09-13: …）`（review 通过后由主会话置 Accepted；本次为用户授权就地修订）：✅
2. D1–D6 全覆盖、无未决项；D1 含地址/大小/属性且为 48-bit 核内有效地址：✅（RAM `0xffff_0000_0000`–`0xffff_00ff_ffff` 16 MiB / Exit `0xffff_8000_0000`–`0xffff_8000_0007` 8 B / boot ROM `0xffff_ffff_0000`–`0xffff_ffff_ffff` 64 KiB，均 `bits[63:48]=0`）
3. exit port 协议完整：地址 `0xffff_8000_0000` + 8 B 宽度 + 编码（0=PASS、`0x01`–`0x7F`=FAIL、`0x80`–`0xFF`=Reserved）+ QEMU 行为（读 8 B→取低字节→`$?`；带退出码 API + 进程级验收测试）：✅
4. MALIGN 完整 guest-visible 状态：异常类型（退出码 `0x8C`）、faulting PC（`rb0`=faulting 指令地址）、不提交（目的寄存器/内存）：✅
5. ILLI/UNDI/SBZ/IALIGN/RASOF/RASUF 完整决策；SBZ→ILLI 给出理由；退出码 ILLI `0x88`/UNDI `0x89`/RASOF `0x8A`/RASUF `0x8B`/IALIGN `0x8D`：✅
6. 全部复位值（RD/RB/RA/RF）冻结；rf0 `0x7FF8_0000_7FC0_0000` 从 0.5.3 `SimRISC-00 §浮点状态寄存器` 位段独立推导；`rb0=0xffff_ffff_0000`：✅
7. D6 示例用 0.5.3 助记符（`set.zw rb16, wp2, 0xffff`/`or.w`/`add.si`/`cmp.so`/`br.nz`/`st.o rd0`/`ld.o`/`jump rrii`/`illi`）且逐条手算地址；三入口时刻（power-on reset / ROM 第一条 / RAM `_start`）区分：✅
8. 唯一端到端启动协议（命令行、flat 镜像、ROM blob 布局、oversize/error、RAM entry）与 ADR-0003 一致：✅
9. MMIO×access-width 矩阵对每个组合给出确定结果；非 8B exit port 访问归 ILLI（`0x88`）并说明理由：✅
10. 零 host 依赖：pass/fail/fault 由 `$?`；精确异常状态由 GDB/QMP guest 寄存器读取路径；**harness 墙钟超时（默认 9 s，可环境变量覆盖）仅作兜底、记 harness 错误、不参与 pass/fail**：✅

**新发现/坑**：
1. **验收脚本须随 ADR 修订同步**：原脚本硬编码旧值（旧地址、旧 fault 码 `0x81`–`0x86`/`0x8F`、`Status=Candidate`），ADR 修订后为 72/89、17 FAIL（`EXIT=1`）。本次把全部旧值检查删除/替换为修订后值，并新增「旧映射已消失」负向断言（`0x81.*MALIGN`/`0x86.*RASUF`）。
2. **`set.zw` wyde 编号**：地址构造用 `set.zw wp2`（wyde2 = `bits[47:32]`），非 `wp3`；脚本新增 `\bwp3\b` 负向扫描防回归，并独立复算 `setzw(2,0xffff)=0xffff_0000_0000`。
3. **`0x81`–`0x86` 仍以 Reserved 行保留**：ADR D5.8 表保留 `0x81`–`0x86` 为 Reserved（对应 spec cause 位 1–6，M1 未用），故脚本不能整体禁用这些字符串，只能负向断言「不再映射到 MALIGN/RASUF」等。
4. **ADR D6.4 ROM→RAM 距离注释与算术不符（超范围观察，未改）**：D6.4 注释写「ROM→RAM 相距 `0x00ff_0000_0000`（≈1 TiB）」，独立复算 `0xffff_ffff_0000 − 0xffff_0000_0000 = 0x0000_ffff_0000`（≈4 GiB）。**结论不受影响**（两者均远超 `jump imms24` 的 ±32 MiB，仍须用 rrii 绝对跳转）。该值属 ADR 决策内容、本次返工硬约束禁改，已记入「遗留问题」待用户决定。
5. **ADR `## 状态说明` 仍为 `Candidate：待评审…` 模板措辞**，与状态行 `Accepted` 不一致；`## 修订` 已说明「用户授权就地修订」。属超范围观察，未改。

**遗留问题**：
1. **ADR D6.4 ROM→RAM 距离数值待用户裁定**：注释 `0x00ff_0000_0000（≈1 TiB）` 与独立复算 `0x0000_ffff_0000`（≈4 GiB）不一致。因 ADR 为既定输入、本次硬约束禁改，未修改；不影响「须用 rrii 绝对跳转」的结论。建议用户决定是否在后续 ADR 修订中更正。
2. **ADR `## 状态说明` 模板措辞**（`Candidate：待评审…`）与状态行 `Accepted` 不一致，同样属超范围、待用户决定是否刷新。
3. 除上述两项超范围观察外无遗留：返工内容 1–6 全部完成，D1–D6 均给出冻结决策，无未决项。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可交付（`待验收`）。自检 **89/89** 通过，退出码 0；改动仅新增 ADR + 更新任务文件。逐行审查 + 独立复算未发现未处置的逻辑/设计缺陷。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：自检脚本「no e_entry load」误报（regex 命中否定句「无 `e_entry` 加载语义」） | ✅已修 | 脚本收紧为正向「跳/从 `e_entry` 进入」匹配 | 复跑 [11] `no jump-to-e_entry claim` PASS；总 89/89 |
| F2：D6 语义示例未使用任务要求的 `add.si`，且无 `illi` 示例 | ✅已修 | 语义示例改为 `set.zw rd16,wp0,42` + `add.si rd16,7` + `cmp.si rd18,rd16,49`；新增 ILLI 测试 pattern（`illi 0`，退出码 `0x82`） | 复跑 [9] `mnemonic add.si`/`illi` PASS；89/89 |
| F3：状态说明含「待定」字样，触发「无待定」自检 | ✅已修 | 改为「D1–D6 全覆盖且无未决项」 | 复跑 [10] `no 待定` PASS |
| F4：D3 bringup 验收写 `0x81`/`0x8F` 与「测试程序不得写 `0x80`–`0xFF`」表面冲突 | ✅已修 | 补说明：bringup 测试在已知写入来源下单独验证机制对任意 8 位值的忠实传播，约定约束常规测试 | 复跑 [5] PASS |
| F5：D5.1 末条「对非可执行区域的取指以外的非法访问种类」含混（可能被读成 fetch→ILLI） | ✅已修 | 删除该从句，只保留 exit port 非 8B/multi store 与任何 load、ROM store，并指向 D5.6 矩阵 | 复跑 [8] 矩阵 PASS |
| F6：D5.3 将 `ext` 的 `hd>N`（属 ILLI）误列为 SBZ，且 `hd[5:N]` 记法不准 | ✅已修 | 改为 `fence immu18 bits[17:4]` 与移位 shamt 之外高位（`shl.ub` `hd[5:3]`、`shl.uw` `hd[5:4]`） | 复跑 [7] SBZ→ILLI PASS |
| F7：D5.7 harness 判定「`$? ≥ 0x80` 为 fault」与 `0x80` 保留不够精确 | ✅已修 | 改为 `$?==0` pass / `0x01`–`0x7F` fail / `≥0x80` fault/协议外 | 复跑 [7]/[10] PASS |
| F8：rf0 常量/地址构造/jump 范围/区域边界对齐是否独立复算（防照抄） | ✅不修（已满足） | 用独立 python 从 spec 位段复算 rf0=`0x7FF800007FC00000`、`set.zw` 地址、`ld.o` 有效地址、jump 范围、区域边界 8B 对齐 | [14] 地址算术 7/7 PASS；推导表见 ADR D2.1 |

**边界/防造假核对**：ADR 内所有 `spec/` 事实均回链 `contract-isa`/`contract-abi`/`SimRISC-00` 章节号（无行号）；「无 spec 依据」项（内存映射/exit/复位/退出码/SBZ/MMIO 矩阵）均显式标注；未引用 0628 作为执行依赖（仅内容溯源，见 Context）。自检脚本与日志可复现（`.tao/logs/SPEC-006t-verify.log`）。

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**。验收标准 1–10 全部通过，无阻断问题。

##### 重跑记录

独立执行 `bash /tmp/opencode/SPEC-006t/check-adr0004.sh`（完整输出存 `.tao/logs/SPEC-006t-review-check.log`）：

```
RESULT: PASS=89 FAIL=0
EXIT_CODE=0
```

所有 89 项检查通过，退出码 0。脚本覆盖：ADR 格式/状态、D1–D6 覆盖、内存映射值与 48-bit、exit 协议、复位值（含 rf0 位段推导）、fault 码 `0x81`–`0x86`/`0x8F`、MMIO×宽度矩阵、0.5.3 助记符（含禁用旧助记符扫描）、无未决占位、ADR-0003 一致性、三入口时刻、零 host 依赖、地址算术独立复算。

##### 独立复算验证（reviewer 自行执行）

1. **rf0 常量独立推导**：从 `spec/SimRISC-00-指令系统设计.md` §浮点状态寄存器原始位布局推导：
   - `[63:51]` = `0111 1111 1111 1`（13 位只读 fo QNaN）→ `0xFFF << 51` = `0x7FF8_0000_0000_0000`
   - `[31:22]` = `0111 1111 11`（10 位只读 ft QNaN）→ `0x1FF << 22` = `0x0000_0000_7FC0_0000`
   - R/W 位复位为 0，SBZ 位为 0
   - **结果**：`0x7FF8_0000_7FC0_0000` ✓，与 ADR 一致
2. **地址算术独立复算**（Python）：
   - `set.zw rb16, wp1, 0x1000` → `0x1000_0000` ✓
   - `set.zw rb1, wp1, 0x87FF` → `0x87FF_0000` ✓
   - `jump rb2, rd0, 0` → `0x8000_0000` ✓
   - `ld.o rd16, rb17, 1` → `0x8000_0001`（未对齐）✓
3. **48-bit 地址验证**：ROM/Exit/RAM 全部 `bits[63:48]=0` ✓
4. **spec 事实交叉核对**：
   - rf0 位布局与 `spec/SimRISC-00-指令系统设计.md` §浮点状态寄存器 一致 ✓
   - `cfx_power_hypv_excp_vector = 0xffff_ffff_0000` 与 `spec/DADAO-12` §68 / `spec/DADAO-23` §27 一致 ✓
   - MALIGN/ILLI/UNDI/IALIGN/RASOF/RASUF 触发条件与 `contract-isa §9` 一致 ✓
   - `SP = rb1` 与 `contract-abi §1` 一致 ✓
   - `rb0[63:48]` 恒为 0 与 `contract-isa §1.3.2` 一致 ✓

##### 逐条验收标准核验

| # | 标准 | 判定 | 依据 |
|---|------|------|------|
| 1 | 文件存在，Status=Candidate | ✅ | `adr-0004-test-machine.md` 存在，`**状态**：Candidate` |
| 2 | D1–D6 全覆盖，无待定；D1 地址 48-bit 有效 | ✅ | 6 个 section 标题均在；无「待定」/「TBD」/「OPEN」；ROM `0x0010_0000` / Exit `0x1000_0000` / RAM `0x8000_0000` 均 `bits[63:48]=0` |
| 3 | exit port 协议完整 | ✅ | 地址 `0x1000_0000`、宽度 8B `st.o`、编码 0=PASS/`0x01`–`0x7F`=FAIL/`0x80`–`0xFF`=Reserved、带退出码 API `qemu_system_shutdown_request_with_code`、进程级验收测试 |
| 4 | MALIGN 可观测行为完整 | ✅ | 退出码 `0x81`、faulting PC = `rb0`（触发异常指令地址）、目的寄存器不提交、内存不提交 |
| 5 | ILLI/UNDI/SBZ/IALIGN/RASOF/RASUF 完整决策 | ✅ | ILLI `0x82`、UNDI `0x83`、SBZ→ILLI `0x82`（理由：已识别 opcode 内字段约束，类比非法操作数）、IALIGN `0x84`、RASOF `0x85`、RASUF `0x86` |
| 6 | 硬件复位值完整；rf0 从 spec 推导 | ✅ | RD=0、RB rb0=`0x0010_0000`/rb1–63=0、RA=0、RF rf0=`0x7FF8_0000_7FC0_0000`（独立推导验证）、rf1–63=0 |
| 7 | D6 用 0.5.3 助记符且逐条手算地址；三入口时刻区分 | ✅ | `set.zw`/`st.o`/`ld.o`/`add.si`/`cmp.si`/`br.nz`/`jump`/`illi` 全在；无旧助记符；三入口时刻（power-on reset / ROM 第一条 / RAM `_start`）明确区分 |
| 8 | 唯一启动协议与 ADR-0003 一致 | ✅ | 双镜像 `-bios rom.bin -kernel test.bin`、flat binary、`e_entry` 不参与、`objcopy --only-section=.text` 流水线与 ADR-0003 §D5 一致 |
| 9 | MMIO×宽度矩阵确定；非 8B exit port 访问归 ILLI | ✅ | D5.6 矩阵覆盖 ROM/Exit/RAM/unmapped × 取指/对齐 load/对齐 store/未对齐 四类；非 8B exit port 归 ILLI `0x82`（理由：opcode 合法，违反 MMIO 宽度约束属非法操作数） |
| 10 | 零 host 依赖可满足 | ✅ | pass/fail/fault 由 `$?` 判定；精确状态验证用 GDB/QMP guest 寄存器读取路径（非 host 日志/stderr/超时） |

##### 约束核验

| 约束 | 判定 | 说明 |
|------|------|------|
| 零 host 依赖 | ✅ | `$?` + GDB/QMP 寄存器路径，无日志解析/超时/stderr |
| 可实现性（QEMU `hw/dadao/`） | ✅ | 内存映射/复位值/exit port/fault→退出码/双镜像加载均在标准 QEMU 机器模型内 |
| 精确异常承诺 | ✅ | MALIGN/ILLI/UNDI/IALIGN/RASOF/RASUF 均明确「目的寄存器不提交、内存不提交、rb0=faulting PC」 |
| exit port 写用 `st.o`（8B 对齐） | ✅ | D3 明确「由一条 st.o（rrii，RD store，op 0x21）写入」 |
| exit port 地址 8B 对齐 | ✅ | `0x1000_0000`，8B 对齐 |
| 复位值/exit port/内存映射标「无 spec 依据」 | ✅ | D1/D2/D3/D5 均显式标注「无 spec 依据，架构自定义」 |
| 指令助记符用 0.5.3 命名 | ✅ | 全文用 `set.zw`/`st.o`/`ld.o` 等，无旧助记符 |
| 格式遵循 `adr-authoring.md` | ✅ | Context/Decision/Rationale/Consequences/状态说明 五段完整 |
| 完成后不自行 commit | ✅ | 未发现 commit 记录 |

##### 观察（非阻断）

1. **`cfx_power_hypv_excp_vector` 描述精确度**：ADR D2.1 称其为「SEE §2.1 的核内地址空间概念」，spec（DADAO-12 §68）实际描述为「DDR 未初始化前硬件可直接执行指令的一段地址空间」（`0xffff_ffff_0000`，64KiB）。两者语义等价（均为 pre-DDR boot region），不影响决策。决策本身正确：M1 无 SEE，不复用该向量，取 ROM 基址 `0x0010_0000`，已标「架构自定义」。
2. **0628 内部不一致已修正**：ADR 明确记录 DADAO-0628 ADR-0004 中 RASOF/RASUF exit code 的正文与 Summary 表不一致问题，v5 统一采用 Summary 口径（IALIGN=`0x84`、RASOF=`0x85`、RASUF=`0x86`），正文一致化。属正确的修正。

##### 边界/防造假核对

- ADR 内所有 `spec/` 事实均回链 `contract-isa`/`contract-abi`/`SimRISC-00` 章节号（无行号） ✓
- 「无 spec 依据」项均显式标注 ✓
- rf0 常量从 spec 位段独立推导（reviewer 用 Python 复算确认），非照抄 0628 ✓
- 未引用 DADAO-0628 作为执行依赖（仅内容溯源，见 Context） ✓
- 工程师自审输出与 reviewer 独立重跑结果一致（89/89, exit=0） ✓

#### 第 1 轮 architect 交叉复核

**判决**：**确认 reviewer 的 Accepted**，无阻断性遗漏或误判。

**依据**（独立复现）：
- 独立重跑 `check-adr0004.sh` → `PASS=89 FAIL=0, EXIT=0`；`diff` 自审日志与 reviewer 日志完全相同；`git status` 无 commit；任务状态未被提前置 `已验证`。
- 逐条标准 1–10 经 `spec/` 与合约原文 + 独立复算核对通过；重点项（48-bit 地址、带码 API + 进程级验收、rf0 独立推导、0.5.3 助记符与地址手算、ADR-0003 一致性、MMIO 矩阵/非 8B→ILLI、零 host 依赖）全部成立。
- exit port API `qemu_system_shutdown_request_with_code` 在 `.dadao/DADAO-0628/components/qemu/patches/` 中被实际使用（非杜撰）；因 QEMU baseline 尚未锁定，采「机制级冻结 + 最终 API 以锁定 baseline 为准」。

**补充发现（均非阻断，不影响 Accepted）**：
1. reviewer「约束核验」表称 D3 正文显式标注「无 spec 依据」略有夸大——exit port 的「无依据」标注落在 Context/Rationale，聚合层面已满足。
2. D2.1 RA 复位行括注「与 spec 进程入口初值一致」偏弱：`contract-isa §1.3.4` 只规定 RegRAS 入口全零，`ra0=0` 属裸机自定义（该行已标「无 spec 依据」）。
3. D6.2 示例 `set.zw rd17, wp0, 49` 后 `cmp.si` 直接用立即数，`rd17` 未被消费（示例冗余，不影响 pattern 正确性）。
4. 保留 fault 码 `0x80`/`0x87`–`0x8E` 无逐码状态规则，但 D5.7 已定义 harness 对 `≥0x80` 的统一处置，与已 Accepted 的 0628 口径一致，非缺口。
5. reviewer 观察 #1 对 spec 的转述不准确：`spec/DADAO-12 §2.1` 本就写「cfx_power_hypv_excp_vector 为硬件复位后启动地址，可由 CPU 直接取指」，ADR 表述准确，reviewer 的「描述精确度」观察本身略偏。

**统一验收报告**：reviewer 与 architect 独立意见**一致判 Accepted**，无分歧；上述 5 条为非阻断观察，留待后续 ADR 修订时可选处理。

#### 返工轮 engineer 自审（2026-09-13）

**判决**：可交付（`待验收`）。返工内容 1–6 全部完成；脚本 **109/109 PASS、`EXIT_CODE=0`**；改动仅限验证脚本 + 任务文件 + 日志，未触碰 ADR 决策内容（`git diff -- .tao/knowledge/adr-0004-test-machine.md` 为空）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1：脚本校验旧值（旧地址、旧 fault 码 `0x81`–`0x86`/`0x8F`、`Status=Candidate`），ADR 修订后 72/89、17 FAIL、`EXIT=1` | ✅已修 | 重写 `check-adr0004.sh` 全部旧值检查为修订后值（新地址/新 fault 码/`Accepted（rev…）`/超时兜底/`set.zw wp2`/`cmp.so`/`st.o rd0`），并加旧映射消失负向断言 | 复跑 `RESULT: PASS=109 FAIL=0`、`EXIT_CODE=0`；见 `.tao/logs/SPEC-006t-rework-verify.log`（138 行） |
| R2：地址构造须用 `set.zw wp2`（wyde2=`bits[47:32]`）而非 `wp3` | ✅已修 | 新增 `set\.zw +rb16, wp2, 0xffff` 正向断言 + `\bwp3\b` 负向扫描；[14] 独立复算 `setzw(2,0xffff)==0xffff_0000_0000` | [9]/[14] PASS；`rg wp3` 全文无命中 |
| R3：D3 新增 harness 超时兜底（默认 9 s、不参与 pass/fail） | ✅已修 | [13] 删除原「no timeout」检查，改为校验 `墙钟超时兜底`/`9 s`/`环境变量`/`harness 错误`/`不.*参与 guest pass/fail` | [13] 7/7 PASS |
| R4：D5 fault 码改 spec cause 派生（`0x87`–`0x8D`） | ✅已修 | [7] 逐码映射校验（`0x87.*Unmapped`…`0x8D.*IALIGN`）+ 派生规则 `spec_cause_bit_index`；删除旧码检查 | [7] 16/16 PASS |
| R5：D6 示例修正（`set.zw wp2` 构造高位地址、`cmp.so` 消费 `rd17`、`st.o rd0` 写 PASS） | ✅已修 | [9]/[15] 校验 `cmp\.so`、`st\.o +rd0, rb16, 0`、`set\.zw +rb16, wp2, 0xffff`；删除旧 `cmp.si` 检查 | [9]/[15] PASS |

**超范围观察（非本次返工 finding；ADR 为用户既定输入、硬约束禁改，转用户/主会话裁定）**：

1. **ADR D6.4 ROM→RAM 距离数值**：注释写 `0x00ff_0000_0000（≈1 TiB）`，独立复算 `0xffff_ffff_0000 − 0xffff_0000_0000 = 0x0000_ffff_0000`（≈4 GiB）。两者均远超 `jump imms24` 的 ±32 MiB，**结论（须用 rrii 绝对跳转）不受影响**。已在完成区「遗留问题」记录，未改 ADR。
2. **ADR `## 状态说明` 仍为 `Candidate：待评审…` 模板措辞**，与状态行 `Accepted（rev…）` 不一致；`## 修订` 已说明用户授权就地修订。未改 ADR。

**边界/防造假核对**：
- `git status --short` 仅 `.tao/tasks/spec/SPEC-006t-Test-Machine-ADR.md` 变更；ADR 文件 `git diff` 为空 → 未触碰既定输入。（注：主会话在本记录之后修正 ADR 两处——D6.4 距离、`## 状态说明`；见审阅记录）
- 脚本非文本存在性堆砌：`[14]` 用 python 独立复算地址构造（`set.zw wp2`）、复位值、区域起始/大小 8 B 对齐、48-bit（`bits[63:48]=0`）；`[7]`/`[9]` 含旧映射与 `wp3` 负向断言。
- 脚本真实执行，`EXIT_CODE=0` 由 `PIPESTATUS[0]` 捕获并写入日志，避免 `tee` 掩盖退出码。

#### 返工轮 reviewer 验收（2026-09-13）

**判决**：**Accepted**。验收标准 1–10 全部通过，无阻断问题。

##### 重跑记录

独立执行 `bash /tmp/opencode/SPEC-006t/check-adr0004.sh`（完整输出存 `.tao/logs/SPEC-006t-review-r2-check.log`）：

```
== [1] file & status ==
PASS: ADR-0004 exists
PASS: Status = Accepted (rev. 2026-09-13)
...
== [15] stated values / example fixes appear in text ==
PASS: D6.2 set.zw rb16, wp2, 0xffff
PASS: D6.2 cmp.so consumes rd17
PASS: D6.2 st.o rd0 writes PASS

RESULT: PASS=109 FAIL=0
EXIT_CODE=0
```

全部 109 项检查通过，退出码 0。

##### 独立复算验证（reviewer 自行执行）

1. **ROM/RAM/Exit 地址**：
   - ROM `0xffff_ffff_0000`–`0xffff_ffff_ffff` = 64 KiB ✓
   - RAM `0xffff_0000_0000`–`0xffff_00ff_ffff` = 16 MiB ✓
   - Exit `0xffff_8000_0000`–`0xffff_8000_0007` = 8 B ✓
   - 三者均位于 cfxcode 63（`bits[47:42]=63`）、48-bit 有效（`bits[63:48]=0`）、8B 对齐 ✓

2. **ROM→RAM 距离**：`0xffff_ffff_0000 − 0xffff_0000_0000 = 0x0000_ffff_0000` = 4,294,901,760 ≈ 4 GiB ✓（主会话修正后的值，正确；远超 `jump imms24` ±32 MiB，须用 rrii 绝对跳转）

3. **fault 码 `0x80 | spec_cause_bit_index`**（从 `spec/DADAO-12` §cfx_umon 异常原因表 lines 403-413 独立核对）：
   - ILLI: `1<<8` → `0x80|8=0x88` ✓
   - UNDI: `1<<9` → `0x80|9=0x89` ✓
   - RASOF: `1<<10` → `0x80|10=0x8A` ✓
   - RASUF: `1<<11` → `0x80|11=0x8B` ✓
   - MALIGN: `1<<12` → `0x80|12=0x8C` ✓
   - IALIGN: `1<<13` → `0x80|13=0x8D` ✓
   - unmapped: `0x87`（测试机约定，非 spec cause 派生）✓

4. **rf0 常量**：`(0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000` ✓（与 ADR 一致）

5. **`set.zw wp2` 地址构造**：`setzw(2, 0xffff) = 0xffff << 32 = 0xffff_0000_0000` → `or.w wp1, 0x8000` → `0xffff_8000_0000` ✓（若误用 wp3 则超出 48-bit）

6. **`0xffff_ffff_0000 − 0xffff_0000_0000` 独立计算**：`0x0000_ffff_0000` = 4 GiB ✓（与 ADR D6.4 修正后一致）

##### 逐条验收标准核验

| # | 标准 | 判定 | 依据 |
|---|------|------|------|
| 1 | 文件存在，Status=Accepted | ✅ | `adr-0004-test-machine.md` 存在，`**状态**：Accepted（rev. 2026-09-13: D1 内存映射改为核内地址空间模型…）`；`## 状态说明` 已改为 Accepted（主会话修正 #2） |
| 2 | D1–D6 全覆盖，无待定；D1 地址 48-bit 有效 | ✅ | 6 个 section 标题均在；无「待定」/「TBD」/「OPEN」；ROM/RAM/Exit 均 `bits[63:48]=0` |
| 3 | exit port 协议完整 | ✅ | 地址 `0xffff_8000_0000`、宽度 8B `st.o`、编码 0=PASS/`0x01`–`0x7F`=FAIL/`0x80`–`0xFF`=Reserved、带退出码 API + 进程级验收测试 |
| 4 | MALIGN 可观测行为完整 | ✅ | 退出码 `0x8C`（`0x80|12`）、faulting PC = `rb0`、目的寄存器不提交、内存不提交 |
| 5 | ILLI/UNDI/SBZ/IALIGN/RASOF/RASUF 完整决策 | ✅ | ILLI `0x88`、UNDI `0x89`、SBZ→ILLI `0x88`（理由：已识别 opcode 内字段约束）、IALIGN `0x8D`、RASOF `0x8A`、RASUF `0x8B`；全部由 spec cause 位派生 |
| 6 | 硬件复位值完整；rf0 从 spec 推导 | ✅ | RD=0、RB rb0=`0xffff_ffff_0000`/rb1–63=0、RA=0、RF rf0=`0x7FF8_0000_7FC0_0000`（独立推导验证）、rf1–63=0 |
| 7 | D6 用 0.5.3 助记符且逐条手算地址；三入口时刻区分 | ✅ | `set.zw wp2`/`st.o`/`ld.o`/`add.si`/`cmp.so`/`br.nz`/`jump`/`illi`/`or.w` 全在；`cmp.so rd18,rd16,rd17` 消费 rd17；`st.o rd0` 写 PASS；三入口时刻明确 |
| 8 | 唯一启动协议与 ADR-0003 一致 | ✅ | 双镜像 `-bios rom.bin -kernel test.bin`、flat binary、`e_entry` 不参与、`objcopy --only-section=.text` |
| 9 | MMIO×宽度矩阵确定；非 8B exit port 访问归 ILLI | ✅ | D5.6 矩阵覆盖 ROM/Exit/RAM/unmapped × 四类访问；非 8B exit port 归 ILLI `0x88` |
| 10 | 零 host 依赖可满足 | ✅ | pass/fail/fault 由 `$?` 判定；精确状态验证用 GDB/QMP；harness 墙钟超时兜底（默认 9s、环境变量覆盖、记 harness 错误、不参与 pass/fail） |

##### 主会话两处修正核验

| 修正 | git diff 行号 | reviewer 独立验证 | 判定 |
|------|-------------|------------------|------|
| D6.4 ROM→RAM 距离 `0x00ff_0000_0000`→`0x0000_ffff_0000`（≈1 TiB→≈4 GiB） | L301 | `0xffff_ffff_0000 − 0xffff_0000_0000 = 0x0000_ffff_0000` = 4,294,901,760 ≈ 4 GiB ✓ | ✅ 正确 |
| `## 状态说明` Candidate→Accepted | L344 | 状态行 `Accepted（rev. 2026-09-13…）` 与状态说明 `Accepted（2026-09-13…）` 一致 ✓ | ✅ 正确 |

##### ADR 未被 engineer 改动验证

`git diff -- .tao/knowledge/adr-0004-test-machine.md` 显示 2 insertions / 2 deletions，均为上述主会话修正。engineer 返工内容仅涉及验收脚本（`/tmp/opencode/SPEC-006t/check-adr0004.sh`）和任务文件，**未触碰 ADR 决策内容**。✅

##### 约束核验

| 约束 | 判定 | 说明 |
|------|------|------|
| 零 host 依赖 | ✅ | `$?` + GDB/QMP 寄存器路径；harness 超时仅兜底不参与 pass/fail |
| 可实现性 | ✅ | 内存映射/复位值/exit port/fault→退出码/双镜像加载均在标准 QEMU 机器模型内 |
| 精确异常承诺 | ✅ | 所有 fault 均明确「目的寄存器不提交、内存不提交、rb0=faulting PC」 |
| exit port 写用 `st.o`（8B 对齐） | ✅ | D3 明确「由一条 st.o 写入」 |
| exit port 地址 8B 对齐 | ✅ | `0xffff_8000_0000`，8B 对齐 |
| 复位值/exit port/内存映射标「无 spec 依据」 | ✅ | D1/D2/D3/D5 均显式标注「无 spec 依据，架构自定义」 |
| 指令助记符用 0.5.3 命名 | ✅ | 全文用 `set.zw`/`st.o`/`ld.o`/`cmp.so` 等，无旧助记符（脚本负向扫描均 PASS） |
| 格式遵循 `adr-authoring.md` | ✅ | Context/Decision/Rationale/Consequences/状态说明 五段完整 + 修订段 |
| 完成后不自行 commit | ✅ | `git diff` 仅含主会话修正，无 engineer 新 commit |

##### ADR 自洽性核验

- 地址图（D1）与示例（D6）地址一致 ✓
- fault 码（D5.8）与示例（D6）中的退出码一致 ✓
- 修订段（`## 修订`）完整记录了 D1/D3/D4-D5 三次修订及其变更范围 ✓
- 状态行 `Accepted（rev. 2026-09-13…）` 与状态说明 `**Accepted**（2026-09-13…）` 一致 ✓（主会话修正 #2）
- D6.4 ROM→RAM 距离 `0x0000_ffff_0000（≈4 GiB）` 与独立复算一致 ✓（主会话修正 #1）
