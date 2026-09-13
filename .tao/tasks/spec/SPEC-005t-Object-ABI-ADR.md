# SPEC-005t: Object ABI ADR（M1 ELF 头 + 段/流水线）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-002t`、`SPEC-004t`
**状态**：已验证

## 范围（2026-09-12 变更）

- **M1 = D1 + D5**：ELF object 文件头字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`）+ 段对齐/VA=PA/端到端 artifact pipeline（`.o → objcopy .text → flat → QEMU`）。M1 单 TU、freestanding、自包含、无 LLD、无跨 object 链接。
- **D2/D3/D4（重定位类型表/溢出/relaxation）标 `Deferred to M2`**：M1 的 `.s` 标签在同段内由汇编器就地解析、**不产生重定位**；M1 LLVM 任务明确「不实现 ELF relocation」（`LLVM-006t`），完整 relocation 另立 `LLVM-012t`（M2）。见 `.tao/knowledge/deferred.md`。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-isa.md`（0.5.3，指令格式/字段宽度/重定位公式的唯一 oracle）
  - `.tao/knowledge/contract-abi.md`（SPEC-004t，指针/地址模型）
- 输出：`.tao/knowledge/adr-0003-object-abi.md`
- 约束：
  - Greenfield 原则：不 cherry-pick 遗留实现，遗留只读参考，结论须独立给出
  - Spec-first：所有 S/A/P 公式和字段宽度从 0.5.3 `contract-isa.md` 推导，引用章节号（§N），不用行号
  - M1 scope：只定义 M1 实际需要的重定位类型；未用类型不列入
  - ELF 内容 `spec/` 无依据 → 本 ADR 即原始决策，须标「无 spec 依据，架构自定义」并给出理由
  - 格式：Context / Decision / Consequences 三段；决策表可被 SPEC-007t 直接引用
  - 完成后不自行 commit

## 背景（完整）

### 目标

产出 `.tao/knowledge/adr-0003-object-abi.md`（ADR-0003），冻结 DADAO-v5 SimRISC **M1 所需的 ELF object ABI**：**D1 文件头字段 + D5 段对齐/流水线**（D2/D3/D4 重定位标 `Deferred to M2`）。本 ADR 是 SPEC-007t（ELF 合约）的**唯一决策依据**。

### 设计理由

- `spec/` 的 SimRISC/ABI/AEE 文档均不含任何 ELF 内容，ELF 头字段与重定位语义必须由架构决策给出。
- 重定位字段宽度/公式必须从 0.5.3 ISA 编码独立推导，不能照搬遗留 `Dadao.def` 的编号或公式。
- 编号/命名空间必须与遗留 toolchain 明确区分（或显式兼容），否则同一 `e_machine` 下会静默误解释 object。
- M1 单翻译单元、freestanding，无动态链接、无 TLS、无跨 object 链接需求，重定位集应最小化。

### 关键概念 / 数据

**D1 ELF 文件头固定字段**：`EI_CLASS`、`EI_DATA`、`e_machine`、`e_flags`、`EI_OSABI` 的冻结值及理由。
须明确 `EM_DADAO = 0x0DA0` 是沿用、修改还是重新申请；若沿用须说明理由与注册状态。

**D2（`Deferred to M2`）重定位类型表**：M1 单 TU 自包含、无跨 object，汇编器就地解析、**不产生重定位**；下表为**重定位类型定义**（M2 CodeGen 需要时启用，本任务仅作登记，不冻结）。

| 场景 | 0.5.3 指令格式 | 字段约束 |
|------|---------------|----------|
| 绝对 64-bit 数据地址 | 数据节 | 全 64 位 |
| 绝对 64-bit 地址构造 | `set.zw` + `or.w`（rwii，wyde 位置选择） | 每次 16 位，`ww` 位置选择器 |
| PC 相对短程分支 | `br.n/br.nn/br.z/br.nz/br.p/br.np`（riii，imms18） | 18-bit 有符号字偏移 |
| PC 相对双寄存器分支 | `br.eq/br.ne`（rrii，imms12） | 12-bit 有符号字偏移 |
| PC 相对 call/jump（中程） | `call imms24`/`jump imms24`（iiii） | 24-bit 有符号字偏移 |
| PC 相对地址加载 | `rela.si`（riii，imms18 << 12） | 30-bit 有效偏移，页号差 |

**D3（`Deferred to M2`）溢出策略**：有界重定位溢出时报错（link-time error）还是截断/wrap；各类型分别说明。

**D4（`Deferred to M2`）重定位松弛策略**：M1 是否支持 relaxation；若不支持，明确写「M1 禁止 relaxation」。

**D5 段对齐与加载协议**：`.text`/`.data`/`.rodata`/`.bss` 最小对齐（0.5.3 指令对齐 4B、数据对齐）；
freestanding 无 MMU 时 VA=PA；以及 M1 端到端 artifact pipeline（与 ADR-0004 的加载模型统一）。

### 上游引用

- `.tao/knowledge/contract-isa.md` §2（编码）、附录 A（mask/value/格式）、§4.6/§4.8（RB rwii/rela.si）、
  §5（分支/call/jump）— 主要 oracle
- DADAO-0628：`code-agent/tasks/DL-003a-elf-object-abi-adr.md`（完整转述；含 3 轮 Architecture Review）
- DADAO-0628：`docs/adr/0003-object-abi.md`（内容溯源：最终 Accepted 决策；ADR 格式见 v5 `.tao/knowledge/adr-authoring.md`）
- DADAO-0628：`contracts/elf/spec.md`（下游 SPEC-007t 的规范化目标）、`contracts/elf/README.md`
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/adr-0003-object-abi.md` | M1 ELF object ABI 架构决策记录：**D1（ELF 头）+ D5（段/流水线）**；D2/D3/D4 重定位标 `Deferred to M2`。Status 先 Candidate，review 通过后 Accepted |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **ISA 来源版本**：0.4.1 → 0.5.3。重定位字段宽度/公式必须从 v5 `contract-isa.md` 推导，
   不照抄 0.4.1 的 `Dadao.def` 编号或 0.4.1 ISA 章节。
2. **指令助记符/格式**：
   - `setzw`/`orw` → `set.zw`/`or.w`（rwii）
   - `brn/brnn/brz/brnz/brp/brnp`（riii imms18）→ `br.n/br.nn/br.z/br.nz/br.p/br.np`
   - `breq/brne`（rrii imms12）→ **`br.eq`/`br.ne`**（0.5.3 的双寄存器条件分支命名）
   - `rela`（riii）→ `rela.si`（riii，imms18 << 12）
   - `call`/`jump` 的 iiii 与 rrii 形式：PCREL24 适用于 `call imms24`/`jump imms24`
3. **PCREL12 类型**：0.4.1 ADR 初版漏了 `br.eq/br.ne` 的 12-bit 重定位，第二轮 review 才补
   `R_DADAO_PCREL12`（编号 9）。v5 应从一开始就把 `br.eq`/`br.ne` 的 PCREL12 纳入 D2/D3。
4. **重定位编号/命名空间**：0.4.1 第二轮 P0 指出「同一 `e_machine`+`e_flags=0` 下重排编号会静默误解释」，
   最终以 `e_flags = 0x1`（M1 ABI version）区分。v5 须冻结同一 `EM_DADAO=0x0DA0` 下的命名空间策略，
   并说明 `EM_DADAO` 的注册状态（project-custom，非 IANA/SysV/upstream LLVM 注册）。
5. **artifact pipeline**：0.4.1 第三轮冻结 `ET_REL → static link → ET_EXEC → objcopy flat → QEMU -kernel`，
   并删除「test machine jumps to e_entry」表述。v5 须与 ADR-0004（SPEC-006t）统一端到端路径。
6. **LLD scope**：0.4.1 DL-004a 曾把 Post-M2 的 LLD 变成 M1 必需依赖。v5 须明确 M1 是否需要
   target linker，或采用 raw/section extraction 路径；不得默认 M1 已获得 DADAO LLD backend。
7. **地址模型**：0.5.3 有效地址为 48 位（高 16 位在地址计算时被忽略）；RB `add.si` 为全 64 位运算。
   推导 PC 相对范围时须以 0.5.3 `contract-isa.md` 的 48 位地址/溢出规则为准。

## 已知坑 / 结论

摘自 DL-003a 三轮 Architecture Review：

1. **P0 重定位编号静默冲突**：沿用 `EM_DADAO=0x0DA0` 且 `e_flags=0` 时重排 legacy 编号，
   会让新/旧 consumer 对同一 type 号做不同解释。必须二选一并记录：保持 namespace 兼容，
   或 clean break（非零 `e_flags` 版本位 + linker 拒绝版本不匹配）。最终决策：`e_flags = 0x1`。
2. **P0 `EM_DADAO` 注册状态声明不实**：LLVM 主线 ELF.h 并无 `EM_DADAO`，只存在于 legacy fork；
   不得声称「已注册 upstream」。
3. **P0 缺 `breq/brne` 的 12-bit PC-relative relocation**：须新增 `R_DADAO_PCREL12`（0.5.3 下对应
   `br.eq`/`br.ne`），冻结编号、bits[11:0]、公式、4 字节整除、signed-12 范围 `[-2048,2047]`
   （字节位移 `[-8192,8188]`）与 link-time overflow。
4. **P0 ADR-0003 与 ADR-0004 加载协议互斥**：必须冻结**唯一**端到端 artifact pipeline，
   说明 ELF 到 flat binary 的转换步骤及由哪个冻结工具完成。
5. **RELA 页号截断**：`((S+A)>>12)-((P+4)>>12)` 使用向下取整，低 12 位由后续 `or.w + ABS_W0` 设置，
   须在 Consequences 说明。
6. **最终结论**：第三轮 Accepted，P0 全部关闭（`e_flags=1`、补 PCREL12、删除 e_entry 加载表述）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-003a-elf-object-abi-adr.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/docs/adr/0003-object-abi.md`
- DADAO-0628：`.work/DADAO-0628/contracts/elf/spec.md`
- DADAO-0628：`.work/DADAO-0628/contracts/elf/README.md`
- v5：`.tao/knowledge/adr-authoring.md`（ADR 格式与模板）
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）
- 本项目：`.tao/knowledge/contract-isa.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.tao/knowledge/adr-0003-object-abi.md` 存在，采用 Context / Decision / Consequences 结构，初始 Status = Candidate（review 通过后改 Accepted）
2. **D1** 冻结 `EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`，含理由与 `EM_DADAO` 注册状态说明
3. **D5** 给出段对齐、VA=PA 及唯一端到端 artifact pipeline（`.o → objcopy .text → flat → QEMU`），与 ADR-0004（SPEC-006t）一致
4. **D2/D3/D4（重定位类型/溢出/relaxation）明确标 `Deferred to M2`**，不与 M1 内容混排（可作登记/参考）
5. 所有取值可从 0.5.3 `contract-isa.md` 独立验证；不引用行号
6. 不依赖遗留 `Dadao.def` 的数字/公式；遗留仅作对比且已在文档中说明
7. 无未决的「待定」字段

## 完成区

**测试结果**：返工自检 **通过 49/49**（`bash /tmp/opencode/SPEC-005t/check-adr0003-rework.sh`，退出码 0）；失败原因：无。完整输出存 `.tao/logs/SPEC-005t-rework-verify.log`，`git diff` 存 `.tao/logs/SPEC-005t-rework-diff.log`。

**修改文件**：
- `.tao/knowledge/adr-0003-object-abi.md`（D1 `e_flags` 由 1 位标志改为 8 位版本字段；加 `## 修订` 与状态 rev 标注；共 +30/-10 行，见 diff）
- `.tao/tasks/spec/SPEC-005t-Object-ABI-ADR.md`（状态 `待返工`→`待验收`；更新完成区、追加第 2 轮自审）

**验收结果**（返工项逐条核对）：
- **`e_flags` = bits 0–7 版本号（M1 = 1）、bits 8–31 保留**：D1 表含义列与逐项理由均改为「对象/ABI 格式版本 = 1（bits 0–7）；bits 8–31 保留为 0」；位表为 `0–7 = 对象/ABI 格式版本号（M1 = 1）`、`8–31 = Reserved（必须为 0）`；并写明「后续每当对象/ABI 格式发生不兼容变化时递增」。
- **consumer 拒绝规则齐全**：新增 4 行判定表——版本 `0`（legacy）拒绝、版本 `1`（M1）接受、版本 `2–255`（未知/未来）拒绝、bits 8–31 ≠ 0（保留位）拒绝；正文明确「只接受 `e_machine = 0x0DA0` 且 `e_flags = 0x00000001`；遇到版本不匹配、未知版本或保留位非 0 一律报错」。
- **保持与 legacy 区分**：legacy `e_flags = 0` = 版本 0 → 拒绝，规则保留。
- **修订标注存在**：`**状态**：Accepted（rev. 2026-09-13: e_flags 版本字段，见 ## 修订）` + 独立 `## 修订` 小节（记录 1 位标志 → 8 位版本字段、动机、变更范围、consumer 规则、兼容性、流程说明）。
- **其它 D1 字段与 D5 未变**：`EI_CLASS=ELFCLASS64(2)`、`EI_DATA=ELFDATA2MSB(2)`、`e_machine=EM_DADAO(0x0DA0)`、`EI_OSABI=ELFOSABI_NONE(0)` 与 D5（段对齐/VA=PA/pipeline）在 `git diff` 中**无改动**；D2/D3/D4 仍标 `Deferred to M2`。
- **ADR 格式合规**：标题 + `**状态**`/`**日期**`/`**关联**` + Context/Decision/Rationale/Consequences/状态说明/修订，符合 `.tao/knowledge/adr-authoring.md`。
- 引用同步：D2 namespace 注、Rationale、Consequences 中的 `e_flags = 0x1` 均改为 `e_flags[7:0] = 1`（8 位版本字段语义）；新增 Rationale 条目说明「8 位版本字段而非 1 位标志」的理由（参照 ARM EABI/LoongArch）。

**新发现/坑**：
1. **`e_flags` 数值不变、语义变宽**：M1 仍为 `0x00000001`，故按原 ADR 产出的 M1 object 不受影响；但 consumer 实现（LLVM/QEMU 侧）应按「bits 0–7 版本号 == 1 且 bits 8–31 == 0」校验，而非仅比较 `e_flags == 1`。
2. **下游 `SPEC-007t` 需同步**：`SPEC-007t` 任务书多处写 `e_flags=0x1`（§2/§4/已知坑 #4/#6），执行时应规范化为「bits 0–7 版本号 = 1（M1），bits 8–31 保留为 0；consumer 拒绝未知版本/保留位非 0」，以 ADR-0003 修订版为准。
3. **`LLVM-003t` 常量来源**：其任务书写「不照抄 0628 的 `e_flags=0x1` 数值表述」，与本修订一致——应从 `contract-elf.md`（由 SPEC-007t 归一化自本 ADR）取版本字段定义，不硬编码。
4. **修订流程例外已记录**：`adr-authoring.md` 一般规则为「不直接改写已 Accepted 的决策」；本次因 Accepted 不久且无实现依赖、经用户明确决定，就地修订并在 `## 修订` 中说明例外。

**遗留问题**：无（D2/D3/D4 属任务明确的 `Deferred to M2`，非本任务遗留；下游 `SPEC-007t` 的 `e_flags` 措辞对齐见「新发现/坑」#2，属下游任务范围）。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可交付（`待验收`）。自审脚本 39/39 通过，退出码 0。

逐行审查要点与 finding 处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：D2 登记表缺 `contract-isa` 来源标注，与「取值可从 0.5.3 独立验证」要求有落差 | ✅已修 | D2 行补 `[contract-isa §2.3–§2.4]`（格式/字段位置）与 `[contract-isa §4.7][§5.2–§5.4]`（分支/call/jump/rela 语义） | 自检 [6] `引用 contract-isa §` PASS；总 39/39 |
| F2：确认未照抄 0628 的 `Dadao.def` 编号/公式（greenfield 约束） | ✅不修（已满足） | 全文无 `R_DADAO_*` 名、无重定位编号/公式；`Dadao.def` 仅作「只读对照、不采用」说明 | 自检 [7] `无 R_DADAO_* 名` PASS、`Dadao.def 仅作对照说明` PASS |
| F3：`.rodata/.data/.bss` 8B 对齐是否可从 0.5.3 独立推导 | ✅不修（已满足） | 依据 `contract-isa §4.1.1`（`ld.o`/`st.o` 8B 对齐）+ `contract-abi §1.7`（指针 8B）；8B 为满足性最小值（更严但安全） | 自检 [4] 各段 PASS |
| F4：pipeline 是否与任务给定 `.o → objcopy --only-section=.text → flat → QEMU` 及 ADR-0004 分工一致 | ✅不修（已满足） | 三步 pipeline 逐字对齐；object→flat 归 ADR-0003，flat→QEMU 入口归 ADR-0004；无 `ET_EXEC`/LLD/`e_entry` 加载语义 | 自检 [4] pipeline 各项 PASS |
| F5：是否存在未决「待定」字段（验收 #7） | ✅不修（已满足） | D2/D3/D4 为任务明确 `Deferred to M2`（确定状态，非待定） | 自检 [8] 无未决占位 PASS |

**边界/防造假核对**：`spec/` 无 ELF 依据已用 `grep`（退出码 1）实测；D1/D5 数值逐条回链 `contract-isa`/`contract-abi` 章节号；无行号引用。审查未发现逻辑/设计缺陷。

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**。所有验收标准通过，无阻塞缺陷。

##### 重跑记录

```bash
# 1. 文件存在性与行数
$ wc -l .tao/knowledge/adr-0003-object-abi.md
117 .tao/knowledge/adr-0003-object-abi.md
# 退出码 0

# 2. ADR 格式结构
$ grep -n '# ADR-0003\|^\*\*状态\*\*\|^\*\*日期\*\*\|^\*\*关联\*\*\|^## Context\|^## Decision\|^## Rationale\|^## Consequences\|^## 状态说明' .tao/knowledge/adr-0003-object-abi.md
1:# ADR-0003: SimRISC M1 Object ABI（ELF 头字段与段/流水线）
3:**状态**：Candidate
4:**日期**：2026-09-13
5:**关联**：ADR-0001（greenfield 重建）、ADR-0002（构建编排）、ADR-0004（test machine，`SPEC-006t`）、`SPEC-005t`（本 ADR 任务）、`SPEC-007t`（ELF 合约，下游规范化）、`.tao/knowledge/contract-isa.md`（SimRISC 0.5.3）、`.tao/knowledge/contract-abi.md`（0.9.2）
7:## Context（背景）
20:## Decision（决策）
98:## Rationale（理由）
106:## Consequences（影响）
115:## 状态说明
# 退出码 0 — 格式完整

# 3. spec/ 无 ELF 依据
$ grep -ril 'elf\|e_machine\|EI_CLASS\|e_flags\|EI_OSABI\|EM_DADAO' spec/
# 无输出，退出码 1 — 确认 spec/ 无 ELF 内容

# 4. 无 R_DADAO_* 名
$ grep -c 'R_DADAO_' .tao/knowledge/adr-0003-object-abi.md
0
# 退出码 0

# 5. Dadao.def 仅作对照说明
$ grep -n 'Dadao\.def' .tao/knowledge/adr-0003-object-abi.md
18:遗留 DADAO toolchain（`Dadao.def`/`ELF.h`）仅作**只读对照**，本 ADR **不采用**其重定位编号或公式
94:> M2 冻结重定位编号时，须在 `e_flags = 0x1` 的 M1 namespace 内独立编号，不得沿用 legacy `Dadao.def` 的编号或公式。
113:遗留 `Dadao.def`/`ELF.h` 仅作只读对照，不作为编号/公式来源
# 全部为「不采用/只读对照」语境

# 6. Deferred to M2 标注
$ grep -n 'Deferred to M2' .tao/knowledge/adr-0003-object-abi.md
16:**`Deferred to M2`**：重定位类型表（D2）、重定位溢出策略（D3）、重定位松弛策略（D4）
79:### D2/D3/D4 — `Deferred to M2`（登记，不冻结）
83:- **D2 重定位类型表（`Deferred to M2`）**
95:- **D3 重定位溢出策略（`Deferred to M2`）**
96:- **D4 重定位松弛策略（`Deferred to M2`）**
112:- **下游**：...D2/D3/D4 在合约中标 `Deferred to M2`...
# D2/D3/D4 独立小节，不与 M1 混排

# 7. 无 ET_EXEC/LLD 作为 M1 依赖
$ grep -n 'ET_EXEC\|LLD' .tao/knowledge/adr-0003-object-abi.md
11:M1 范围为单翻译单元（single TU）、freestanding、自包含：无跨 object 链接、无动态链接、无 TLS、无 target linker（LLD）
66:M1 采用 **raw / section extraction** 路径，**不引入 target linker（LLD）**、不产生 `ET_EXEC**、不做跨 object 链接
75:...不经过静态链接；这是 M1 不依赖 LLD 的关键
103:...也不产生 M1 无法解析的 `ET_EXEC`/重定位残留
109:不引入 LLD：M1 pipeline 不依赖 target linker
# 全部为「不引入/不产生」语境 — M1 pipeline 不含 ET_EXEC/LLD

# 8. 无未决占位（TBD/FIXME/TODO/待定）
$ grep -c '待定\|TBD\|FIXME\|TODO' .tao/knowledge/adr-0003-object-abi.md
0
# 退出码 1（grep 无匹配）— 无未决字段

# 9. git status
$ git status --short
 M .tao/tasks/spec/SPEC-005t-Object-ABI-ADR.md
?? .tao/knowledge/adr-0003-object-abi.md
# 与完成区声称的修改文件一致

# 10. 无行号引用
$ grep -n '行\|line [0-9]\|Line [0-9]' .tao/knowledge/adr-0003-object-abi.md
76:...因此本 ADR 不出现「test machine 跳到 `e_entry`」的表述
# 仅 line 76 包含「表述」一词，非行号引用
```

##### 约束核验

| 约束 | 结果 | 证据 |
|------|------|------|
| ADR 格式合规（`# ADR-0003` + 状态/日期/关联 + Context/Decision/Rationale/Consequences/状态说明） | ✅ | 标题、状态=Candidate、日期、关联、5 个 section 全部存在 |
| **D1** 冻结 5 字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`） | ✅ | 逐项有值、有理由、有 `contract-isa`/`contract-abi` 章节引用 |
| `EM_DADAO` 注册状态（未注册 upstream） | ✅ | 明标「project-custom」「未注册于 IANA/SysV 公共 ELF registry」「不存在于 LLVM 主线」 |
| D1 取值可从 `contract-isa.md`/`contract-abi.md` 独立验证 | ✅ | §1.1→ELFCLASS64, §1.6→ELFDATA2MSB, §1.5→48-bit addr, §2.1→4B align, §4.1.1→8B align, contract-abi §1.7→8B ptr |
| **D5** 段对齐 + VA=PA + pipeline（`.o → objcopy .text → flat → QEMU`） | ✅ | .text=4B, .rodata/.data/.bss=8B; VA=PA (freestanding no-MMU); 三步 pipeline 明确 |
| D5 pipeline 无 ET_EXEC / 无 LLD | ✅ | 明标「raw / section extraction」「不引入 target linker（LLD）」「不产生 ET_EXEC」 |
| **D2/D3/D4 标 `Deferred to M2`**，不与 M1 混排 | ✅ | 独立小节 `### D2/D3/D4 — Deferred to M2（登记，不冻结）`，M1 内容不混入重定位编号 |
| 未照抄 0628（无 `R_DADAO_*` 编号/公式） | ✅ | `grep -c 'R_DADAO_'` = 0；`Dadao.def` 仅作「只读对照、不采用」说明 |
| 无行号引用 | ✅ | 无 `line N` 或 `行N` 格式引用 |
| 无未决「待定」字段 | ✅ | `grep` 无匹配 |

##### 与工程师自审结论的差异

**无差异**。工程师自审 39/39 通过、5 个 finding 均为已满足或已修复；独立重跑全部通过，结论一致。

##### 关于 SPEC-007t §6 措辞冲突的判断

工程师在完成区发现的问题 **准确但不构成 ADR-0003 的阻塞缺陷**：

- **事实**：SPEC-007t §6（line67）写「ET_REL → ET_EXEC → flat binary → QEMU」，包含 ET_EXEC（静态链接产出的可执行文件）；ADR-0003 §D5 冻结的 M1 pipeline 为「`.o → objcopy --only-section=.text -O binary → flat binary → QEMU`」，**无 ET_EXEC、无 LLD**。
- **根因**：SPEC-007t 的已知坑 #3（line106）已将此标注为 P0：「§6 把 Post-M2 LLD 变成 M1 必需依赖：须二选一——保持 roadmap（raw/section extraction）或扩展 M1 scope」。
- **判断**：ADR-0003 §D5 正确冻结了 M1 的唯一 pipeline（raw/section extraction），SPEC-007t 的 §6 措辞是**下游任务需修正的内容**，不是 ADR-0003 的缺陷。执行 SPEC-007t 时应以 ADR-0003 §D5 为准。
- **建议**：SPEC-007t 任务书 §6 应预先修正为「`.o → objcopy --only-section=.text → flat → QEMU`」，与 ADR-0003 对齐后再开始执行。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**；D1/D5 事实经独立回溯 0.5.3 合约可验证，D2/D3/D4 确标 `Deferred to M2`，格式合规、无照抄。

**独立核对**：D1 5 字段逐项回链 `contract-isa`/`contract-abi`；`.text` 4B、`.rodata/.data/.bss` 8B 对齐有据（`§2.1`/`§4.1.1`）；`EM_DADAO` 注册状态经抓取 LLVM 主线 `ELF.h`（无 `EM_DADAO`）与 legacy fork（`EM_DADAO=0x0DA0`）独立证实；D5 pipeline 无 ET_EXEC/LLD；无 `R_DADAO_*`、无行号、无 `Dadao.def` 数字。

**补充发现（非阻塞，已处置）**：

- **F1**：`SPEC-007t §6` 的「ET_REL → ET_EXEC → flat」与本 ADR 冲突 → 已在 `SPEC-007t` 预修正为「`.o → objcopy .text → flat → QEMU`（无 ET_EXEC/LLD）」。
- **F2**：`SPEC-007t §2` 预列 legacy `R_DADAO_*` 名称 → 已加注「legacy 对照、M1 不冻结，完整命名留 `LLVM-012t`（M2）」。
- F3/F4：reviewer 转录笔误、措辞小瑕（不影响判决）。

**统一判决**：**Accepted**。

### 后续修订（2026-09-13，用户决定）

**问题**：`e_flags` 原设计「bit0 = M1 ABI version」是**1 位标志**，只能区分 M1 vs legacy，**无法编码后续 milestone/ABI 版本**（前瞻性不足）。

**修订**：改为**多位版本字段**——`e_flags` **bits 0–7 = 对象/ABI 格式版本号**（M1 = 1；后续在对象/ABI 格式变化时递增），**bits 8–31 保留（必须 0）**；consumer 拒绝未知版本或不匹配。参照 ARM（EABI 版本 8 位）/LoongArch（ABI 版本 3 位 + 对象 ABI 2 位）。

**处置**：**返工修订 ADR-0003**（标注为 revision；因其 Accepted 不久且未实现，就地修订并加修订说明）。

#### 第 2 轮 engineer 自审（返工）

**判决**：可交付（`待验收`）。返工自检 49/49 通过，退出码 0。

**返工项 → 处置**：

| 返工要求 | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `e_flags` bits 0–7 = 对象/ABI 格式版本号（M1 = 1），后续变化时递增 | ✅已修 | D1 表含义列、逐项理由、位表（`0–7` 版本号 / `8–31` Reserved） | 自检 [4] 6 项全 PASS |
| bits 8–31 保留（必须为 0） | ✅已修 | 逐项理由 + 位表 + consumer 判定表 | 自检 [4] `bits 8–31 保留必须为 0` PASS |
| consumer 遇未知版本/不匹配必须拒绝 | ✅已修 | 新增判定表：版本 0 拒绝 / 1 接受 / 2–255 拒绝 / 保留位非 0 拒绝；正文补「一律报错」 | 自检 [5] 5 项全 PASS |
| 保持与 legacy 区分（`e_flags = 0` = 版本 0 → 拒绝） | ✅已修 | 判定表首行「legacy DADAO object（无版本字段）→ 拒绝」 | 自检 [5] `版本 0 = legacy 拒绝` PASS |
| 同步更新 D1 表格/理由、Rationale、Consequences | ✅已修 | D1 表/理由、D2 namespace 注、Rationale（含新增「8 位版本字段」条目）、Consequences 均同步 | 自检 [4][6] PASS；diff 显示相关行全改 |
| 标注为 revision（加修订说明，记录 1 位标志 → 8 位版本字段） | ✅已修 | `**状态**：Accepted（rev. 2026-09-13: ...）` + 独立 `## 修订` 小节 | 自检 [2] `状态 Accepted + rev 标注`、`## 修订` PASS；[6] 4 项 PASS |
| 不改其它 D1 字段与 D5 | ✅不修（已满足） | `EI_CLASS`/`EI_DATA`/`e_machine`/`EI_OSABI` 与 D5 全文未动 | 自检 [3][7] PASS；`git diff` 确认这些行零改动 |

**逐行审查要点**：
- 版本字段与保留位的位宽自洽：`0–7`（8 位，覆盖 0–255）+ `8–31`（24 位）恰好覆盖 32 位 `e_flags`，无重叠/空洞。
- consumer 判定表四行穷尽所有输入：版本 0 / 1 / 2–255（8 位全域）与保留位非 0，无未覆盖分支；与正文「只接受 `0x00000001`」一致。
- 兼容性：M1 数值仍为 `0x00000001`，未破坏已产出 object；改动仅为语义放宽 + 校验规则细化。
- 未引入新的外部依赖、未改函数签名（本任务为文档）、无 `[OPEN]`/待定占位、无行号引用。
- 引用一致性：全文旧表述 `e_flags = 0x1` 已全部改为 `e_flags[7:0] = 1`（D2 namespace 注、Rationale、Consequences），无残留不一致。

**边界/防造假核对**：自检脚本真实执行（49 项 PASS、退出码 0，日志落盘）；`git diff` 真实显示 40 行变更且仅限 `e_flags` 相关；未执行任何 git commit。

**自审结论**：返工项全部处置，无未修 finding；状态置 `待验收`。

#### 第 2 轮 reviewer 验收

**判决**：**Accepted**。返工项全部通过独立验证，无阻塞缺陷。

##### 重跑记录

```bash
# 综合验证脚本（58/59 PASS，1 项为脚本 grep 模式缺陷非内容缺陷）
$ bash /tmp/opencode/SPEC-005t-review2/verify.sh 2>&1
# ... (58 PASS, 1 FAIL — FAIL 原因为脚本 grep 未匹配 backtick 包裹的 `ET_EXEC`，手动确认内容正确)
# SCRIPT_EXIT: 0

# 手动确认 ET_EXEC 出现（修正脚本 backtick 问题）
$ grep -c '不产生.*ET_EXEC' .tao/knowledge/adr-0003-object-abi.md
2
# 退出码 0 — D5 明确「不产生 ET_EXEC」，内容正确

# git status
$ git status --short .tao/knowledge/adr-0003-object-abi.md .tao/tasks/spec/SPEC-005t-Object-ABI-ADR.md
   M .tao/knowledge/adr-0003-object-abi.md
 M .tao/tasks/spec/SPEC-005t-Object-ABI-ADR.md
# 退出码 0 — 与完成区声称的修改文件一致

# git diff --numstat（精确行数）
$ git diff --numstat .tao/knowledge/adr-0003-object-abi.md
30	10	.tao/knowledge/adr-0003-object-abi.md
# 实际 +30/-10 行（完成区声称 +40/-11，40 为 stat 总变更行数 30+10=40 的误读）

# D1 非 e_flags 字段 diff（确认无变更）
$ git diff .tao/knowledge/adr-0003-object-abi.md | grep '^[-+]' | grep -v '^[-+][-+][-+]' | grep -E 'EI_CLASS.*=.*[0-9]|EI_DATA.*=.*[0-9]|EI_OSABI.*=.*[0-9]|e_machine.*0x0DA0' | grep -v 'e_flags'
# 无输出 — EI_CLASS/EI_DATA/e_machine/EI_OSABI 冻结值未变

# D5 diff（确认无变更）
$ git diff .tao/knowledge/adr-0003-object-abi.md | grep '^[-+]' | grep -v '^[-+][-+][-+]' | grep -E '段对齐|VA=PA|pipeline|\.text.*4B|\.rodata|objcopy|flat.*binary'
# 无输出 — D5 内容未变

# spec/ 无 ELF 依据
$ grep -ril 'elf\|e_machine\|EI_CLASS\|e_flags\|EI_OSABI\|EM_DADAO' spec/
# 无输出，退出码 1 — 确认 spec/ 无 ELF 内容

# 无残留 e_flags = 0x1 旧表述（排除 e_flags = 0x00000001）
$ grep -c 'e_flags = 0x1[^0]' .tao/knowledge/adr-0003-object-abi.md; grep -c 'e_flags = 0x1$' .tao/knowledge/adr-0003-object-abi.md
0
0
# 退出码 0 — 无残留旧表述

# 无行号引用
$ grep -cE 'line [0-9]|行[0-9]' .tao/knowledge/adr-0003-object-abi.md
0
# 退出码 1（grep 无匹配）— 无行号引用

# 无未决占位
$ grep -c '待定\|TBD\|FIXME\|TODO' .tao/knowledge/adr-0003-object-abi.md
0
# 退出码 1 — 无未决字段
```

##### 约束核验

| 约束 | 结果 | 证据 |
|------|------|------|
| `e_flags` = bits 0–7 版本号（M1 = 1）、bits 8–31 保留（必须 0） | ✅ | D1 表「对象/ABI 格式版本 = 1（bits 0–7）；bits 8–31 保留为 0」；位表 `0–7` / `8–31`；逐项理由含 `bits 0–7 为对象/ABI 格式版本号` + `bits 8–31 保留` |
| 位宽自洽（8+24=32） | ✅ | bits 0–7（8 位）+ bits 8–31（24 位）= 32 位，覆盖 e_flags 全域 |
| consumer 判定：版本 0 拒绝 / 1 接受 / 未知版本拒绝 / 保留位非 0 拒绝 | ✅ | 判定表 4 行穷尽；正文「只接受 `e_flags = 0x00000001`；遇到版本不匹配、未知版本或保留位非 0 一律报错」 |
| 修订标注存在（状态行 rev + `## 修订` 小节） | ✅ | 状态行 `Accepted（rev. 2026-09-13: ...）`；`## 修订` 含动机/变更范围/consumer 规则/兼容性/流程说明 |
| 其它 D1 字段未变 | ✅ | diff 无 `EI_CLASS`/`EI_DATA`/`e_machine`/`EI_OSABI` 冻结值变更 |
| D5 未变 | ✅ | diff 无段对齐/VA=PA/pipeline 内容变更 |
| D2/D3/D4 仍标 `Deferred to M2` | ✅ | `D2 重定位类型表（Deferred to M2）`、`D3 重定位溢出策略（Deferred to M2）`、`D4 重定位松弛策略（Deferred to M2）` 全部存在 |
| ADR 格式合规 | ✅ | 标题 + 状态/日期/关联 + Context/Decision/Rationale/Consequences/状态说明/修订 |
| 无行号引用 | ✅ | `grep` 无匹配 |
| 无外部依赖 | ✅ | `spec/` 无 ELF 内容（`grep` 退出码 1）；`R_DADAO_*` 计数为 0；`Dadao.def` 仅作只读对照 |
| 引用同步（`e_flags = 0x1` → `e_flags[7:0] = 1`） | ✅ | 旧表述计数 0；新表述存在于 D2 namespace 注、Rationale、Consequences |
| git status 与修改文件一致 | ✅ | `adr-0003-object-abi.md` + `SPEC-005t-Object-ABI-ADR.md` 均为已修改状态 |

##### 小瑕疵（非阻塞）

1. **diff 行数计数偏差**：完成区声称「+40/-11 行」，实际 `git diff --numstat` 为 `+30/-10`。40 是 `git diff --stat` 的总变更行数（30+10=40），非净新增行数。不影响内容正确性。

##### 下游同步建议（非阻塞，供架构师参考）

- **`SPEC-007t` 任务书**：多处仍写 `e_flags=0x1`（§2 line93、已知坑 #4/#6 line104/113），执行时应以 ADR-0003 修订版为准，规范化为「bits 0–7 版本号 = 1（M1），bits 8–31 保留为 0；consumer 拒绝未知版本/保留位非 0」。**建议在 SPEC-007t 开始前预先修正任务书措辞**，避免实现者照抄旧表述。
- **`LLVM-003t` 任务书**：已正确说明「不照抄 0628 的 `e_flags=0x1` 数值表述，从 `contract-elf.md`（SPEC-007t，归一化自 ADR-0003）取版本字段定义」，无需修正。但 SPEC-007t 的 `contract-elf.md` 产出时须确保 `e_flags` 版本字段语义已归一化。

##### 与工程师自审结论的差异

**无实质性差异**。工程师自审 49/49 通过；独立重跑 59 项中 58 项 PASS、1 项为脚本 grep 模式缺陷（backtick 包裹 `ET_EXEC` 导致模式不匹配），手动确认内容正确。结论一致。

### 交叉复核（architect，返工后）

**复核者**：architect
**时间**：2026-09-13
**结论**：确认 reviewer 第 2 轮的 **Accepted**；返工要求全部落实、自洽、格式合规。

**独立核对**：bits 0–7 版本号（M1=1，三处一致）+ bits 8–31 保留；consumer 判定穷尽（0 拒 / 1 收 / 2–255 拒 / 保留位非 0 拒）；位宽自洽（8+24=32）；其它 D1 字段与 D5 `git diff` 零改动；D2/D3/D4 仍 Deferred；无行号、无残留旧表述（`e_flags = 0x1` 计数 0）。

**就地修订的合理性**：用户明确决定 + ADR 刚 Accepted 且无实现依赖 + `## 修订` 完整留痕 + 数值兼容（仍 `0x00000001`）→ 属经授权的就地修订，未抹除历史，与 `adr-authoring.md` 相容。

**补充观察（非阻塞，已处置）**：

- O1：完成区 diff 计数 `+40/-11` → 已订正为 `+30/-10`。
- O2：`## 状态说明` 模板句与就地修订的字面张力（`## 修订` 已声明例外，可接受）。
- 下游归一化：`SPEC-007t`（L93/L113）的 `e_flags=0x1` 已归一化为 `e_flags[7:0]=1`（bits 8–31 保留）；`LLVM-003t` 无需改（依赖 `contract-elf.md`）。

**统一判决**：**Accepted**。

