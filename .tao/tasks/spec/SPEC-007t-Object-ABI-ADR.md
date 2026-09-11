# SPEC-007t: Object ABI ADR（ELF/重定位决策）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-002t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-isa.md`（0.5.3，指令格式/字段宽度/重定位公式的唯一 oracle）
  - `.tao/knowledge/contract-abi.md`（SPEC-006t，指针/地址模型）
- 输出：`.tao/knowledge/adr-0003-object-abi.md`
- 约束：
  - Greenfield 原则：不 cherry-pick 遗留实现，遗留只读参考，结论须独立给出
  - Spec-first：所有 S/A/P 公式和字段宽度从 0.5.3 `contract-isa.md` 推导，引用章节号（§N），不用行号
  - M1 scope：只定义 M1 实际需要的重定位类型；未用类型不列入
  - ELF 内容 `spec/` 无依据 → 本 ADR 即原始决策，须标「无 spec 依据，架构自定义」并给出理由
  - 格式：Context / Decision / Consequences 三段；决策表可被 SPEC-009t 直接引用
  - 完成后不自行 commit

## 背景（完整）

### 目标

产出 `.tao/knowledge/adr-0003-object-abi.md`（ADR-0003），冻结 DADAO-v5 SimRISC M1 所需的
ELF object ABI 字段。本 ADR 是 SPEC-009t（ELF 合约）的**唯一决策依据**。

### 设计理由

- `spec/` 的 SimRISC/ABI/AEE 文档均不含任何 ELF 内容，ELF 头字段与重定位语义必须由架构决策给出。
- 重定位字段宽度/公式必须从 0.5.3 ISA 编码独立推导，不能照搬遗留 `Dadao.def` 的编号或公式。
- 编号/命名空间必须与遗留 toolchain 明确区分（或显式兼容），否则同一 `e_machine` 下会静默误解释 object。
- M1 单翻译单元、freestanding，无动态链接、无 TLS、无跨 object 链接需求，重定位集应最小化。

### 关键概念 / 数据

**D1 ELF 文件头固定字段**：`EI_CLASS`、`EI_DATA`、`e_machine`、`e_flags`、`EI_OSABI` 的冻结值及理由。
须明确 `EM_DADAO = 0x0DA0` 是沿用、修改还是重新申请；若沿用须说明理由与注册状态。

**D2 M1 重定位类型表**：每条给出名称、编号、字段宽度/位范围、S/A/P 公式、溢出策略、适用指令格式。
须覆盖 M1 场景（从 0.5.3 `contract-isa.md` 推导）：

| 场景 | 0.5.3 指令格式 | 字段约束 |
|------|---------------|----------|
| 绝对 64-bit 数据地址 | 数据节 | 全 64 位 |
| 绝对 64-bit 地址构造 | `set.zw` + `or.w`（rwii，wyde 位置选择） | 每次 16 位，`ww` 位置选择器 |
| PC 相对短程分支 | `br.n/br.nn/br.z/br.nz/br.p/br.np`（riii，imms18） | 18-bit 有符号字偏移 |
| PC 相对双寄存器分支 | `br.eq/br.ne`（rrii，imms12） | 12-bit 有符号字偏移 |
| PC 相对 call/jump（中程） | `call imms24`/`jump imms24`（iiii） | 24-bit 有符号字偏移 |
| PC 相对地址加载 | `rela.si`（riii，imms18 << 12） | 30-bit 有效偏移，页号差 |

**D3 溢出策略**：有界重定位溢出时报错（link-time error）还是截断/wrap；各类型分别说明。

**D4 重定位松弛策略**：M1 是否支持 relaxation；若不支持，明确写「M1 禁止 relaxation」。

**D5 段对齐与加载协议**：`.text`/`.data`/`.rodata`/`.bss` 最小对齐（0.5.3 指令对齐 4B、数据对齐）；
freestanding 无 MMU 时 VA=PA；以及 M1 端到端 artifact pipeline（与 ADR-0004 的加载模型统一）。

### 上游引用

- `.tao/knowledge/contract-isa.md` §2（编码）、附录 A（mask/value/格式）、§4.6/§4.8（RB rwii/rela.si）、
  §5（分支/call/jump）— 主要 oracle
- DADAO-0628：`code-agent/tasks/DL-003a-elf-object-abi-adr.md`（完整转述；含 3 轮 Architecture Review）
- DADAO-0628：`docs/adr/0003-object-abi.md`（内容溯源：最终 Accepted 决策；ADR 格式见 v5 `.tao/knowledge/adr-authoring.md`）
- DADAO-0628：`contracts/elf/spec.md`（下游 SPEC-009t 的规范化目标）、`contracts/elf/README.md`
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Architecture Decisions 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/adr-0003-object-abi.md` | ELF object ABI 架构决策记录，覆盖 D1–D5，Status 先 Candidate，review 通过后 Accepted |

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
   并删除「test machine jumps to e_entry」表述。v5 须与 ADR-0004（SPEC-008t）统一端到端路径。
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

1. `.tao/knowledge/adr-0003-object-abi.md` 存在，采用 Context / Decision / Consequences 结构，
   初始 Status = Candidate（review 通过后改 Accepted）
2. D1 冻结 `EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`，含理由与 `EM_DADAO` 注册状态说明
3. D2 每条重定位含：名称、编号、字段宽度/位置、S/A/P 公式、适用指令、溢出策略；覆盖绝对地址、
   wyde 构造、PCREL18、PCREL12（`br.eq`/`br.ne`）、PCREL24、RELA（`rela.si`）
4. 所有 S/A/P 公式与字段宽度可从 0.5.3 `contract-isa.md` 独立验证；不引用行号
5. D3 溢出策略明确（有界类型 link-time error），D4 明确 M1 是否禁止 relaxation
6. D5 给出段对齐、VA=PA 及唯一端到端 artifact pipeline，与 ADR-0004（SPEC-008t）一致
7. 重定位编号/命名空间策略明确且无静默冲突（版本位或兼容策略已冻结）
8. 不依赖遗留 `Dadao.def` 的数字/公式；遗留仅作对比且已在文档中说明
9. 无未决的「待定」字段；未用重定位类型不列入（后续 ADR 追加）

## 完成区

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
