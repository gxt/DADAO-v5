# SPEC-007t: ELF 合约（归一化自 ADR-0003）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-005t`、`SPEC-002t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/adr-0003-object-abi.md`（SPEC-005t，**唯一决策来源**）
  - `.tao/knowledge/contract-isa.md`（0.5.3，指令格式/字段宽度的 oracle）
- 输出：`.tao/knowledge/contract-elf.md`
- 约束：
  - ADR-0003 是唯一来源：所有值直接从 ADR 复制，不重新推导；ADR 与 ISA 冲突时暂停并报告，不自行解决
  - 与现有合约（`contract-isa.md`）风格一致；每条规则在段落内写明约束和例外
  - 不与 ISA 合约重复：指令格式/编码细节引用 `contract-isa.md §N`，不粘贴复制
  - 不引用行号：只用章节号（§N）或 ADR 决策点（§DN）
  - 合约完备：每条重定位有完整 S/A/P 公式与溢出策略，不留「见 ADR」内联空引用
  - 完成后不自行 commit

## 背景（完整）

### 目标

产出 `.tao/knowledge/contract-elf.md`，将 `.tao/knowledge/adr-0003-object-abi.md`（ADR-0003）的
ELF 架构决策规范化为与 `contract-isa.md`、`contract-abi.md` 风格一致的合约文件。本合约成为
后续 LLVM MC ELF emitter 与 QEMU loader 的唯一 oracle。

### 设计理由

- ADR 是决策记录（Context/Decision/Consequences），合约是可供实现直接消费的规范化投影；
  二者分离避免实现从 ADR 叙述反推。
- 合约必须可独立阅读：字段宽度/位置、S/A/P 公式、溢出策略须完整，不能靠跳转 ADR 补全。
- 来源字段引用 ADR-0003（`spec/` 无 ELF 内容），不引用 spec commit。

### 关键概念 / 数据

**§1 ELF Header Fields**：`EI_CLASS`、`EI_DATA`、`e_machine`、`e_flags`、`EI_OSABI` 的冻结值及含义
（来源 ADR-0003 §D1）。

**§2 Relocation Types**：完整重定位表（编号、名称、字段宽度/位置、S/A/P 公式、适用指令、溢出策略）
+ 每类型推导说明（来源 ADR-0003 §D2）。0.5.3 下的适用指令映射：

| 重定位 | 0.5.3 适用指令 | 字段 |
|--------|---------------|------|
| `R_DADAO_64` | `.quad`/指针数据 | 8 字节 @ P |
| `R_DADAO_ABS_W3/W2/W1/W0` | `set.zw`/`or.w`（RD/RB，rwii） | bits[15:0]，`ww` 由类型隐式决定 |
| `R_DADAO_PCREL18` | `br.n/br.nn/br.z/br.nz/br.p/br.np`（riii） | imms18 @ bits[17:0] |
| `R_DADAO_PCREL12` | `br.eq`/`br.ne`（rrii） | imms12 @ bits[11:0] |
| `R_DADAO_PCREL24` | `call imms24`/`jump imms24`（iiii） | imms24 @ bits[23:0] |
| `R_DADAO_RELA` | `rela.si`（riii） | imms18 @ bits[17:0] |

**§3 Overflow Policy**：两级策略表（`R_DADAO_64`/`ABS_W*` 无溢出；有界类型 link-time error）。

**§4 Relaxation**：M1 禁止 relaxation 的正式声明及约束。

**§5 Section Alignment**：`.text`/`.rodata`/`.data`/`.bss` 最小对齐、VA=PA 规则。

**§6 Artifact Pipeline**：M1 端到端 artifact 路径（ET_REL → ET_EXEC → flat binary → QEMU），
与 ADR-0004（SPEC-006t）的加载模型一致。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-004a-elf-contract.md`（完整转述；含 3 轮 Architecture Review）
- DADAO-0628：`contracts/elf/spec.md`（内容溯源：最终 Accepted 内容；合约格式见 v5 `.tao/knowledge/contract-authoring.md`）
- DADAO-0628：`contracts/elf/README.md`
- DADAO-0628：`docs/adr/0003-object-abi.md`（归一化来源）
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/contract-elf.md` | ELF/对象 ABI 合约，归一化自 ADR-0003，覆盖 §1–§6，Status 先 Candidate（review 通过后 Accepted） |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **来源版本**：ADR-0003 从 0.4.1 决策改为 v5（SPEC-005t）的 0.5.3 决策；合约版本应与 v5 一致。
2. **指令助记符**：`setzw`/`orw` → `set.zw`/`or.w`；`brn/brz/…` → `br.n/br.z/…`；
   `breq/brne` → `br.eq`/`br.ne`；`rela` → `rela.si`；`call`/`jump` iiii 形式不变。
3. **重定位集**：0.4.1 初版 9 型、后补 PCREL12 为 10 型；v5 应从一开始就含 `R_DADAO_PCREL12`
   （对应 0.5.3 `br.eq`/`br.ne`）。
4. **e_flags**：0.4.1 曾出现 contract `e_flags=1` 与 ADR `e_flags=0` 的冲突，须先改 ADR 再改合约；
   v5 以 SPEC-005t 冻结值为准（`e_flags=0x1`）。
5. **e_machine 说明**：不得声称 `EM_DADAO` 已注册 upstream LLVM；应为 project-custom。
6. **LLD scope**：0.4.1 曾把 Post-M2 的 LLD 写成 M1 必需依赖；v5 须区分 object ABI 与
   test-machine load contract，明确 M1 是否使用 target linker。
7. **artifact pipeline**：`QEMU -kernel flat.bin` 不得被称为「ELF loader」；须与 ADR-0004 冻结的
   双镜像（`-bios trampoline.bin` + `-kernel flat.bin`）命令一致。

## 已知坑 / 结论

摘自 DL-004a 三轮 Architecture Review：

1. **P0 e_flags 值与 ADR 冲突**：合约不得在 ADR 之外单向改变决策；若需修订，先更新 ADR 再同步合约。
2. **P0 前置 ADR 未 Accepted**：004a 不能把 Candidate 且内部不一致的 ADR 规范化为唯一 oracle；
   须先完成 SPEC-005t/SPEC-006t review 并升级 ADR 状态。
3. **P0 §6 把 Post-M2 LLD 变成 M1 必需依赖**：须二选一——保持 roadmap（raw/section extraction）
   或扩展 M1 scope 新增 DADAO LLD backend 任务；不能只改合约。
4. **P0 §6 与 ADR-0004 启动命令不一致**：须引用唯一完整命令/镜像对，并区分 object ABI 与
   test-machine load contract。
5. **P1 PCREL12 的 §3 来源不成立**：合约 §3 自行补的 PCREL12 overflow 行须先在 ADR §D3 补齐，
   保持合约 §3 为机械规范化结果。
6. **P1 e_machine 错误声明传播**：`e_flags=1` 只供更新的 consumer 区分 namespace，不保证旧
   consumer 检查并拒绝。
7. **最终结论**：第三轮 Accepted（ADR-0003/0004 Status 升级、e_machine 说明修正、补 PCREL12
   overflow 行、§6 补 `-bios`、PCREL12 标 ADR extension）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-004a-elf-contract.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/contracts/elf/spec.md`
- DADAO-0628：`.work/DADAO-0628/contracts/elf/README.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0003-object-abi.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）
- 本项目：`.tao/knowledge/adr-0003-object-abi.md`（SPEC-005t 产出）、`.tao/knowledge/contract-isa.md`
- DADAO-0628：`code-agent/tasks/DL-004a-elf-contract.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.tao/knowledge/contract-elf.md` 存在，Status 先 Candidate，来源指向 ADR-0003（SPEC-005t 产出）（前提：SPEC-005t/SPEC-006t review 已通过、ADR-0003/0004 Status=Accepted）
2. §1–§6 全部覆盖，无空白或「见 ADR」占位；§1 冻结 5 个 ELF 头字段
3. §2 每条重定位含完整：编号、名称、字段宽度/位置、S/A/P 公式、适用 0.5.3 指令、溢出策略
4. §2 含 `R_DADAO_PCREL12`（`br.eq`/`br.ne`）且 §3 溢出策略同步覆盖
5. §4 明确 M1 禁止 relaxation；§5 给出各段最小对齐与 VA=PA
6. §6 artifact pipeline 与 ADR-0004（SPEC-006t）冻结的启动命令/镜像对一致；不把 QEMU flat
   loader 称为 ELF loader（前提：SPEC-006t review 已通过、ADR-0004 Status=Accepted）
7. 每章节有 `[ADR-0003 §DN]` 来源标注；不引用行号
8. 合约可独立阅读：不出现「见 ADR」式的内联空引用
9. 不声明 `EM_DADAO` 已注册 upstream；命名空间/版本策略与 ADR 一致

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
