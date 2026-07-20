# Phase 1：ISA 规范合约与编码表

> 对应 DADAO-0628 的 Phase 0.5A（Spec Normalization）+ DL-001a/b 系列

## 目标

从 DADAO-v5/wiki 的 SimRISC 四份规范文档和 AEE（寄存器模型部分）中提取核心 ISA 规范，创建机器可读的编码表（opcodes.yaml）和合法性规则（legality_rules.yaml）。这是所有后续实现（golden model、LLVM、QEMU）的单一事实来源。

## 输入文件（DADAO-v5/wiki）

| 文件 | 用途 | 关键内容 |
|------|------|---------|
| `SimRISC-00-指令系统设计.md` | 指令编码设计、指令格式、QFC 编码表 | 所有 12 种操作数格式、opcode 布局、MISC-AMO/MISC-octa/MISC-tetra/MISC-wyde/MISC-byte/MISC-RF 子编码表、标识位定义 |
| `SimRISC-01-数据类指令.md` | RD 寄存器组的所有指令语义 | 存取（单/多）、赋值（块/立即数/条件）、算术（add/sub/mul/div/cmp）、逻辑（and/or/xor/xnor）、移位（shl/shr/ext）、wyde 块操作 |
| `SimRISC-02-地址类指令.md` | RB/RA 寄存器组指令、控制流 | RB 存取、RA 存取、块赋值（rb2rd/rd2rb/rb2rb/ra2rd/rd2ra）、RB 算术（add/sub/add.si/rela.si/cmp）、控制流（br/jump/call/ret）、48 位地址语义 |
| `SimRISC-03-浮点类指令.md` | RF 寄存器组指令 | RF 存取（单精/双精）、块赋值、转换指令、浮点运算（ftadd/ftsub/ftmul/ftdiv...）、IEEE 754 支持 |
| `SimRISC-04-系统类指令.md` | 系统指令 | swym、illi、fence、lr/sc（原子操作）、cfx 特权指令（trap/escape/cfx2rd/cfx2rc/cfxld/cfxst） |
| `DADAO-11-AEE-应用程序运行环境.md` | 寄存器模型 | rd0 硬连线零、rb0=PC、rf0=FCSR、RA 栈（RegRAS + MemRAS）、RASOF/RASUF |
| `AGENTS.md` | 命名约定 | /wpN/pmem/illi 等命名规则、指令格式后缀 |

## 参考文件（DADAO-0628）

| 文件 | 用途 |
|------|------|
| `contracts/isa/spec.md` | ISA 规范合约模板（SimRISC 0.5.3） |
| `verif/opcodes.yaml` | 编码表模板（1288 行，87 条指令） |
| `verif/legality_rules.yaml` | 合法性规则模板 |
| `code-agent/knowledge/02-isa-encoding-rules.md` | ISA 编码规则知识 |

## 输出文件

```
DADAO-v5/
├── contracts/
│   └── isa/
│       ├── spec.md              # ISA 规范合约（从 wiki 提取 + 归一化）
│       └── README.md            # 更新（版本号、来源声明）
├── verif/
│   ├── opcodes.yaml             # 机器可读编码表
│   ├── legality_rules.yaml      # 合法性规则目录
│   ├── validate_encoding.py     # 编码验证器

```

## 子代理分解

### P1-1：ISA 规范合约提取

**职责**：从 6 份 wiki 文档创建 `contracts/isa/spec.md`

**提示词**：
```
你是 DADAO-v5 的 ISA 规范工程师。从 DADAO-v5/wiki 下的 wiki 规范文档提取并创建合约文件。

请读取以下输入文件并创建 `contracts/isa/spec.md`：

输入文件：
- DADAO-v5/wiki/SimRISC-00-指令系统设计.md（编码设计、QFC 表）
- DADAO-v5/wiki/SimRISC-01-数据类指令.md（RD 指令语义）
- DADAO-v5/wiki/SimRISC-02-地址类指令.md（RB/RA/控制流）
- DADAO-v5/wiki/SimRISC-03-浮点类指令.md（RF 指令语义）
- DADAO-v5/wiki/SimRISC-04-系统类指令.md（系统指令）
- DADAO-v5/wiki/DADAO-11-AEE-应用程序运行环境.md（寄存器模型）
- DADAO-v5/AGENTS.md（命名约定）

spec.md 的要求：
1. **版本号**：SimRISC 0.5.3（与 wiki 一致）
2. **结构**：参照 DADAO-0628/contracts/isa/spec.md 的格式，但基于 SimRISC 0.5.3 内容重写
3. **必须包含的章节**：
   - §1 寄存器模型（rd/rb/rf/ra 四组 + rd0/rb0/rf0/ra0 特殊行为）
   - §2 指令编码（8/6/6/6/6 布局、12 种格式、QFC 编码表）
   - §3 标量整数指令（RD 加载/存储、算术、逻辑、移位、条件赋值、块复制）
   - §4 地址/内存指令（RB 加载/存储、RB 算术、RB 比较、RB wyde、块复制、PC 相对）
   - §5 控制流（条件分支、无条件跳转、调用/返回 + RAS 压栈弹栈）
   - §6 浮点指令（RF 加载/存储、块复制、转换、算术运算）
   - §7 系统指令（swym/illi/fence/lr/sc/cfx 特权指令）
   - §8 NOP 与保留编码
   - §9 异常总结（ILLI/UNDI/MALIGN/IALIGN/RASOF/RASUF/FPEXCP/CFXREG）
   - 附录 A：完整编码清单（与 QFC 表一致）
   - 附录 B：条件标志参考
   - 附录 C：未解决/开放问题
4. **规范基础**：基于 SimRISC 0.5.3 规范，包含完整的指令集定义
5. **每条规范性断言** 必须标注来源 wiki 章节（如 `[SimRISC-01 §3.5]`）
6. **附录 A 编码清单** 必须直接从 SimRISC-00 §QFC 编码表提取，每条指令标注 mask/value

注意：这是纯文本规范，不包含任何实现代码。规范是"什么"，不是"怎么做"。
```

### P1-2：机器可读编码表

**职责**：创建 `verif/opcodes.yaml`

**提示词**：

你是 DADAO-v5 的编码表工程师。从 SimRISC-00 的 QFC 编码表和 SimRISC-01~04 的指令定义创建机器可读编码表。

读取输入文件：
- DADAO-v5/wiki/SimRISC-00-指令系统设计.md（QFC 表、MISC-AMO/MISC-octa/MISC-tetra/MISC-wyde/MISC-byte/MISC-RF 编码）
- DADAO-v5/wiki/SimRISC-01-数据类指令.md
- DADAO-v5/wiki/SimRISC-02-地址类指令.md
- DADAO-v5/wiki/SimRISC-03-浮点类指令.md
- DADAO-v5/wiki/SimRISC-04-系统类指令.md
- DADAO-v5/AGENTS.md（命名约定）

输出 `verif/opcodes.yaml`，格式示例：

```yaml
# 编码表格式
- mnemonic: ld.o-rd        # 指令助记符，按格式后缀区分
  format: rrii              # 指令格式类型
  op: "0x20"                # 编码（0010-0xxx）
  mask: "0xFC000000"        # 编码 mask（1=相关位）
  value: "0x20000000"       # 编码 value
  fields: ["rdha", "rbhb", "imms12"]  # 操作数字段
  legality:                 # 合法性约束
    - rule: rd_dest_rd0
      msg: "rdha cannot be rd0"
  wiki_cite: "SimRISC-01 §存取RD寄存器"
```

关键要求：
1. **完整覆盖所有指令**：从 QFC 表逐行提取
   - MISC-AMO/MISC-octa/MISC-tetra/MISC-wyde/MISC-byte 子编码表所有非空条目
   - MISC-RF 子编码表所有非空条目
   - 主 QFC 表所有非空条目
2. **指令命名**：用 `-rd`/`-rb`/`-rf`/`-ra` 后缀区分同一助记符不同 bank 版本（如 `add.uo-rd-orrr`、`add.so-rb-orrr`、`add.si-rd-riii`、`add.si-rb-riii`）
3. **格式后缀**：遵循 AGENTS.md 的指令格式后缀规范
4. **mask/value 计算**：严格按照指令的 op 位和 ha/hb 固定值计算，参考 DADAO-0628/opcodes.yaml 的格式
5. **legality 清单**：每条指令标注适用的合法性规则
6. **field 描述**：按 ha/hb/hc/hd 的顺序标注字段类型

注意：基于 SimRISC 0.5.3 规范，包含完整的指令集定义。

估算总指令数：约 200+（对比 0.4.1 的 87 条，增加约 120+ 条）

完成后进行自检：随机抽取 50 条指令的编码与 QFC 表交叉核对。

### P1-3：合法性规则与验证器

**职责**：创建 `verif/legality_rules.yaml` + `verif/validate_encoding.py`

**提示词**：

你是 DADAO-v5 的合法性工程师。创建合法性规则目录和编码验证器。

1. 创建 `verif/legality_rules.yaml`：

从 SimRISC-01~04 和 AEE 文档中提取每条 ILLI/UNDI/MALIGN/IALIGN 规则。格式示例：

```yaml
rules:
  - id: rd_dest_rd0
    fault: ILLI
    kind: static
    spec_cite: "SimRISC-01 §存取类指令"
    wiki_cite: "SimRISC-01 §rd0 为目的寄存器约定"
    status: active
    check2: yes   # 是否在 opcodes.yaml 中有记录
    description: "写 rd0 为目的寄存器时触发 ILLI（单目的指令不允许，双目的 add/sub/mul 的 rrrr 格式允许其中一个为 rd0）"
```

必须包含的规则类别：
- rd0 写检查（单目的 vs 双目的区别）
- rb0 写检查（所有指令）
- rf0 操作检查（作为操作数参与运算）
- store_src_rd0 检查
- dual_dest 检查（同时为 rd0 或同一非零寄存器）
- rb_base_rb0_store 检查
- multi_immu6_zero 检查
- multi_range_overflow 检查（first + count > 64）
- data_malign（各宽度对齐要求）
- imm_range 检查（各格式立即数范围）
- shamt_overflow（shamt > N）
- ext_bit_overflow（hd > N）
- div_by_zero（除法/取余除数为零）
- div_overflow（INT64_MIN / -1）
- reserved_undi（保留编码）
- instruction_align（IALIGN）
- sbz_nonzero（SBZ 域非零，deferred）
- ras_of（RAS 上溢）
- ras_uf（RAS 下溢）
- lr_hb_not_zero（lr 指令 hb ≠ rd0）
- cfx_reserved（reserved cfxcode 7-14, 19-61）

每条规则标注 status: active 或 deferred（参考 wiki 文档中的说明）。

2. 创建 `verif/validate_encoding.py`：

验证器脚本功能：
- 读取 `opcodes.yaml`
- 检查每条指令的 mask/value 是否合法（无重叠冲突）
- 检查保留编码是否被意外分配
- 检查没有两条指令共享相同的 mask/value
- 输出检查结果（PASS/FAIL + 详情）

参考 DADAO-0628/tools/validate_encoding.py 的实现风格。

## 阶段验证

- `opcodes.yaml` 中每条指令的编码与 QFC 表手动交叉核对 20 条
- `validate_encoding.py` 对 opcodes.yaml 运行无冲突
- `legality_rules.yaml` 中每条 active 规则对应 opcodes.yaml 中至少一条指令的 legality 标注
- `contracts/isa/spec.md` 通过 Wiki 引用检查：每条 `[SimRISC-XX §N]` 引用在 wiki 源文件中可定位

## 审核流程

**重要**：审查者必须使用与任务执行子代理不同的 model，以确保独立性。

### 子代理自审

1. 运行 `validate_encoding.py`，确认无冲突
2. 随机抽取 20 条指令与 QFC 表交叉核对
3. 填写任务文件的"完成区"

### 审查者验证

**文件正确性分析**：
1. 检查 `opcodes.yaml`：
   - mask/value 计算是否正确（对照 QFC 表）
   - 指令命名是否符合 SimRISC 0.5.3 规范
   - 格式后缀是否正确（rrrr/orrr/rrii 等）
   - legality 约束是否完整
2. 检查 `legality_rules.yaml`：
   - 是否覆盖所有 ILLI/UNDI/MALIGN/IALIGN 条件
   - 规则描述是否准确
   - status 标注是否合理（active/deferred）
3. 检查 `validate_encoding.py`：
   - 实现逻辑是否正确
   - 是否检查 mask/value 冲突
   - 是否检查保留编码
4. 检查 `contracts/isa/spec.md`：
   - Wiki 引用是否可定位
   - 指令语义描述是否准确

**运行验证**：
1. 运行 `validate_encoding.py`，检查输出
2. 随机抽取 20 条指令与 QFC 表手动核对

**填写审阅记录**：
1. 记录分析发现的问题
2. 记录运行结果
3. 给出判决（Accepted/Needs Revision）

### 架构师验收

1. 确认审查者的 Accepted 判决
2. 确认所有 finding 已处置
3. 提交到仓库

## 依赖关系

- 依赖 Phase 0（目录结构、Makefile）
- 是 Phase 2（测试向量）和 Phase 3（Golden Model）的前提
