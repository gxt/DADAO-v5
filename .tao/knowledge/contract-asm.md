# DADAO 汇编语言合约（Toolchain-01 归一化）

> **版本：1.1** [Toolchain-01 §附：与上游 spec/ 的关系]

本合约把 v5 自定规范 `spec/Toolchain-01-汇编语言.md`（v1.1，语法已定稿；实现待安排）归一化为可精确消费的断言；规范叙述与理由留在该规范正文，本合约只提取可机械/agent 消费的约束。

- **投影关系**：本合约为投影类型①（叙述合约）；②机器数据 = `contracts/opcodes.yaml`（`format`/汇编形式列）；③机械门控 = `tools/spec/check_asm_prose.py`、`check_asm_list_consistency.py`、`check_asm_list_drift.py`；④可执行 = `tests/llvm/lit/MC/DADAO`。[Toolchain-01 §12]
- **指令全表**：227 条指令表为生成投影 `.tao/knowledge/contract-asm-list.md`，本合约不重抄；指令编码身份以 `contracts/opcodes.yaml` 为准，指令语义见 `contract-isa.md`（M1）/`contract-fp.md`（`scope: fp`）。[Toolchain-01 §1]
- **来源标注**：每条规范性断言以 `[Toolchain-01 §x]` 标注主来源；凡书写形式决策并标其冻结依据 `ADR-0013`（cfx 记法见 `ADR-0013 D8`），cfx 别名约定并标 `ADR-0017`，上游可溯源者并标 `SimRISC-0x`/`DADAO-11` 的对应章节。
- **冲突处理**：本合约与 `spec/` 冲突时阻断实现，走变更流程（`spec/Process-02-合约编写规范.md`），由规范而非实现裁定。[Toolchain-01 §附：与上游 spec/ 的关系]

---

## §1 范围与术语

- 适用范围：DADAO M1 汇编语言——词法、记号、指令书写、指导符、选项、诊断、往返。[Toolchain-01 §1]
- 指令集权威：编码与身份以 `contracts/opcodes.yaml` 为准，语义以 `contract-isa.md` 为准；本合约只规定书写形式。[Toolchain-01 §1]
- 9 种 M1 格式类：`rrrr`、`rrri`、`rrii`、`riii`、`iiii`、`rwii`、`orrr`、`orri`、`oiii`。[Toolchain-01 §1]
- `crrr`/`crii`/`ciii` 属特权 cfx，`scope: excluded`。[Toolchain-01 §1]
- 术语：地址表达式、寄存器组、条件寄存器、地址立即数（字节）。[Toolchain-01 §1]

---

## §2 词法与记号

### §2.1 空白与大小写

- 空白（空格、制表）MAY 出现在记号之间任意位置，MUST NOT 改变记号序列。[Toolchain-01 §2.1][ADR-0013]
- 助记符与寄存器名大小写不敏感（`ADD.SI` ≡ `add.si`）。[Toolchain-01 §2.1]

### §2.2 注释

- `;` 起至行尾为注释（`CommentString = ";"`）。[Toolchain-01 §2.2][ADR-0013 D9]
- `#` 不是注释，保留给 C 预处理器（`#include`/`#define`/`#if` 等）。[Toolchain-01 §2.2][ADR-0013 D9]
- `//` 与 `/* … */` 不采用。[Toolchain-01 §2.2][ADR-0013 D9]

### §2.3 标识符与标签

- 标识符字符集：`[A-Za-z0-9_$.?]`；`.` 与 `?` 亦属标识符字符。[Toolchain-01 §2.3][ADR-0013 D2]
- 标签 MAY 使用 `name:`、数字标签 `1:`、局部标签 `.Lname:`。[Toolchain-01 §2.3]

### §2.4 数字与立即数单位

- 立即数 MAY 写为十进制、`0x…`（十六进制）、`0b…`（二进制）、负数（前导 `-`）；下划线分隔符 MUST NOT 使用。[Toolchain-01 §2.4][ADR-0013 D3]
- 立即数位置接受完整常量表达式（`+ - * / % & | ^ << >> == != < <= > >= && ||` 与一元 `! ~ - +`、括号分组）。[Toolchain-01 §2.4]
- **地址立即数**：跳转/分支目标偏移与 escape 偏移单位为**字节**，不含任何单位标记；装配器将其右移 2 位写入编码字段，并校验 `%4==0` 与范围。[Toolchain-01 §2.4][ADR-0013 D3]
- 各立即数字段的位宽与取值范围见 `contract-asm-list.md` 的「立即数范围速查」；越界 MUST 报错。[Toolchain-01 §2.4][ADR-0013 D3]

### §2.5 寄存器名

- 四组：`rd0`–`rd63`（RD）、`rb0`–`rb63`（RB）、`ra0`–`ra63`（RA）、`rf0`–`rf63`（RF，属 `scope: fp`）。[Toolchain-01 §2.5][SimRISC-00 §寄存器]
- 寄存器名 MUST 为「组前缀 + 十进制序号」，序号 MUST 在 0–63。[Toolchain-01 §2.5][SimRISC-00 §寄存器]
- ABI 别名（`rdzero`/`rderrno`/`rdt0`–`rdt7`/`rda0`–`rda15` 及 RB/RA/RF 对应，见 `contract-abi.md`）MAY 在后续版本支持；当前版本不接受（未实现，见 §11）。[Toolchain-01 §2.5]

---

## §3 地址表达式 `[...]`

地址表达式用于**访存**与**跳转/分支目标**，两者共用同一记法。[Toolchain-01 §3][ADR-0013 D4]

### §3.1 语法

```text
地址表达式   ::= "[" 基址 ["," 寄存器偏移] ["," 立即数偏移] "]"
基址         ::= rb寄存器 | 异常现场基址
异常现场基址 ::= "excp_cause_ip"
寄存器偏移   ::= rd寄存器
立即数偏移   ::= 立即数 | 符号
```

- 异常现场基址 `excp_cause_ip` 仅 escape 使用（异常进入时保存的地址）。[Toolchain-01 §3.1][ADR-0013 D4]
- 寄存器偏移（rd 寄存器）仅用于 `jump`/`call` 的 rrii 形式。[Toolchain-01 §3.1][ADR-0013 D4]

### §3.2 语义（三类，公式不同）

- **访存**（`ld.*`/`st.*`/`ldm.*`/`stm.*`/`cfxld`/`cfxst`）：有效地址 = `基址 + 立即数`（偏移单位为字节，`imms12`）。[Toolchain-01 §3.2][ADR-0013 D4]
- **iiii 跳转/分支**（`jump`/`call` 的 iiii 形式、`br.*`）：目标 = `基址 + 立即数`（字节，`imms26`/`imms20`/`imms14`）。[Toolchain-01 §3.2][ADR-0013 D4]
- **rrii 跳转**（`jump`/`call` 的 rrii 形式）：目标 = `基址 + 寄存器偏移 + 立即数`（字节，`imms14`）。[Toolchain-01 §3.2][ADR-0013 D4]
- **相对跳转的基址**：iiii 形式的基址 MUST 为 `rb0`（当前指令地址）；基址非 `rb0` 而指令为 iiii 形式时 MUST 报错；rrii 形式的基址 MAY 为任意 RB 寄存器。[Toolchain-01 §3.2][ADR-0013 D4]
- **字段名映射**：`imms14`（汇编，字节）⇔ 编码 `imms12`（`field = bytes >> 2`）、`imms20` ⇔ `imms18`、`imms26` ⇔ `imms24`；访存的 `imms12` 与 `ret` 的 `imms18` 不在映射范围内（值非地址）。[Toolchain-01 §3.2][ADR-0013 D10]

### §3.3 示例

| 场景 | 写法 |
|---|---|
| 访存（RD） | `ld.ub rd8, [rb2, 1]`、`st.b rd0, [rb1, 1]` |
| 访存（RA/RB） | `ld.o ra1, [rb2, 0]`、`st.o rb1, [rb2, 8]` |
| 多寄存器访存 | `ldm.ub {rd8:rd10}, [rb0, rd1]` |
| 相对跳转 | `jump [rb0, 8]`、`call [rb0, 12]` |
| 绝对跳转 | `jump [rb3, rd0, 96]` |
| 条件分支 | `br.eq {rd8, rd0}?, [rb0, 16]` |
| 访存（符号偏移） | `ld.st rd2, [rb1, x_offset]`、`st.t rd4, [rb1, z_offset]` |
| 条件分支（标签） | `br.nz {rd2}?, [rb0, overflow_handler]` |

> **注意**：`[` `]` 不是表达式运算符，也不是内存「间接跳转」——`jump [..]` 是直接跳到该地址（非 x86 间接跳转语义）。[Toolchain-01 §3.3]

---

## §4 寄存器组 `{...}` 与条件标记 `?`

### §4.1 语法

```text
寄存器组       ::= "{" 寄存器列表 "}" | "{" 起 ":" 止 "}"
寄存器列表     ::= 单寄存器 ("," 单寄存器)*
条件寄存器组   ::= 寄存器组 "?"
双目的寄存器对 ::= "{" 单寄存器 "," 单寄存器 "}"
单寄存器       ::= rd寄存器 | rb寄存器 | ra寄存器
```

`{rd3}` 匹配单元素寄存器列表；`{rd8, rd0}` 匹配双元素寄存器列表；`{rd8, rd0}?` 匹配条件寄存器组。[Toolchain-01 §4.1][ADR-0013 D1]

### §4.2 规则

- **单寄存器**：`{rd3}`——不带冒号。[Toolchain-01 §4.2][ADR-0013 D1]
- **范围**：`{rd3:rd8}` 表示 `rd3` 到 `rd8` 的连续寄存器；分隔符 MUST 为 `:`（不是 `-`）。[Toolchain-01 §4.2][ADR-0013 D1]
- **条件寄存器**：`?` MUST 紧跟 `}` 之后，标记「该组寄存器用于条件判断」；MUST NOT 写在寄存器名之后（`rd3?` 被词法解析为单个标识符）。[Toolchain-01 §4.2][ADR-0013 D2]
- **双目的指令**：`rrrr` 格式中 6 条指令（`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`）的 `rdha` 与 `rdhb` 均为 dst；书写为 `助记符 {rdHA, rdHB}, rdHC, rdHD`（花括号内逗号后加空格）。[Toolchain-01 §4.2][ADR-0013 D1][ADR-0013 D6]
- **多寄存器指令**（`ldm.*`/`stm.*`）：目的寄存器与个数合并为寄存器组，个数 MUST NOT 显式书写（由组推出）。[Toolchain-01 §4.2][ADR-0013 D5]
  - MUST 校验：`{}` 不得为空；起点+个数 MUST NOT 越出 `rd63`；个数为 0 MUST 报错。[Toolchain-01 §4.2][ADR-0013 D5]
  - `ldm` 的组是**目的**（内存→寄存器），`stm` 的组是**源**（寄存器→内存）。[Toolchain-01 §4.2][ADR-0013 D5]
- **多寄存器组记法扩展**：当 `immu6` 表示连续寄存器个数时，源与目的都用 `{start:end}` 范围记法；适用于 8 条寄存器复制指令（`ra2rd`/`rb2rb`/`rb2rd`/`rd2ra`/`rd2rb`/`rd2rd`/`rd2rf`/`rf2rd`，orri 格式）与 20 条浮点格式转换指令（`ft2fo`/`fo2ft`/…/`ut2fo`，orri 格式）。[Toolchain-01 §4.2][ADR-0013 D5]

### §4.3 示例

| 场景 | 写法 |
|---|---|
| 单寄存器条件（`br.n`） | `br.n {rd0}?, [rb0, 16]` |
| 双寄存器条件（`br.eq`） | `br.eq {rd8, rd0}?, [rb0, 16]` |
| RB 条件（`br.z-rb`） | `br.z {rb2}?, [rb0, 16]` |
| 条件赋值（`cs.n`） | `cs.n {rd1}?, rd2, rd3, rd4` |
| 条件赋值（`cs.eq`） | `cs.eq {rd1, rd2}?, rd3, rd4` |
| 多寄存器访存 | `ldm.o {rd8:rd11}, [rb0, rd1]` |
| 双目的（`add.uo`） | `add.uo {rd8, rd9}, rd10, rd11` |
| 多寄存器块赋值 | `ra2rd {rd8:rd10}, {ra1:ra3}` |
| 多寄存器格式转换 | `ft2fo {rf4:rf6}, {rf8:rf10}` |

### `{...}` 用途速查表

| 用途 | 语法 | 示例 | 区分标记 |
|------|------|------|---------|
| 条件寄存器组 | `{reg, …}?` | `{rd3}?`、`{rd8, rd0}?` | `?` 紧跟 `}` |
| 双目的寄存器对 | `{reg, reg}` | `{rd8, rd9}` | 无 `?`，恰好 2 个 |
| 多寄存器组（范围） | `{start:end}` | `{rd8:rd11}` | `:` 分隔 |
| 多寄存器组（单寄存器） | `{reg}` | `{rd8}` | count=1 |

---

## §5 指令语法（按格式类）

**不变量**：只增加标点、不重排操作数——各格式类的操作数相对顺序保持不变（dst 在前、base 在 offset 前、count 原在末位）。[Toolchain-01 §5]

| 格式类 | 语法（记法） | 示例 | 单位说明 |
|---|---|---|---|
| `rrrr`（双目的） | `助记符 {dst1, dst2}, src1, src2` | `add.uo {rd8, rd9}, rd10, rd11` | — |
| `rrrr`（cs.n/z/p） | `助记符 {cond}?, dst, src1, src2` | `cs.n {rd1}?, rd2, rd3, rd4` | — |
| `rrrr`（cs.eq/ne） | `助记符 {cond1, cond2}?, dst, src` | `cs.eq {rd8, rd0}?, rd9, rd10` | — |
| `rrri` | `助记符 {dst:…}, [base, offset]` | `ldm.ub {rd8:rd10}, [rb0, rd1]` | count 省略 |
| `rrii` | `助记符 dst, [base, offset]`；`jump`/`call` 为 `助记符 [base, reg, offset]` | `ld.ub rd8, [rb2, 1]`；`jump [rb3, rd0, 96]` | 访存偏移 = 字节；跳转偏移 = 字节 |
| `riii` | `助记符 dst, imm` / `助记符 {dst}?, [rb0, off]`（分支） | `add.si rd8, 1`；`br.n {rd0}?, [rb0, 16]` | 分支偏移 = 字节 |
| `iiii` | `助记符 [rb0, off]`（`jump`/`call`） | `jump [rb0, 8]` | 偏移 = 字节 |
| `rwii` | `助记符 dst, wpN, immu16` | `set.zw rd8, wp2, 0x1234` | wyde 位置保持 `wpN` |
| `orrr` | `助记符 dst, src1, src2` | `or.o rd8, rd9, rd10` | — |
| `orri` | `助记符 dst, src, immu6` | `ext.uo rd8, rd0, 1` | — |
| `orri`（块赋值/格式转换） | `助记符 {dst:…}, {src:…}` | `ra2rd {rd8:rd10}, {ra1:ra3}` | `immu6` = 连续寄存器个数 |
| `oiii` | `助记符 immu18` | `fence 0`、`swym 0` | 纯立即数，不加 `[]` |

**`scope: excluded` 的格式（`crrr`/`crii`/`ciii`）与 LR-SC 的书写规则**（同规则、供对照）[Toolchain-01 §5][ADR-0013 D8]：

- `cfxld cfx63, [rb2, 1]`、`cfxst cfx63, [rb2, 1]`——`cfxha` 写作 `cfxHA`（测试机为 `cfx63` = power）；末两操作数为地址。[Toolchain-01 §5][ADR-0013 D8]
- `cfx2rd cfx63, cg8, rc1, rd8`、`cfx2rc …`——字段占位为 `cfxHA, cgHB, rcHC, rdHD`；中间两操作数分别是 `cg` 寄存器与 `rc` 寄存器。[Toolchain-01 §5][ADR-0013 D8]
- `lr_nn.o rd9, [rb1]`——两个操作数：`rdHB` 固定为 `rd0`（不在汇编中出现；手工编码 `hb ≠ 0` → ILLI）。[Toolchain-01 §5][ADR-0013 D8]
- `sc_nn.o rd8, rd9, [rb1]`——三个操作数：`rdHB`（成功/失败结果）、`rdHC`（源）、地址 `rbHD`。[Toolchain-01 §5][ADR-0013 D8]
- `escape cfx63, [excp_cause_ip, 4]`——第二参数为字节偏移（汇编层 `imms20`，须 `%4==0`），基址为异常进入时保存的地址 `excp_cause_ip`（不在编码中，故显式写出）。[Toolchain-01 §5][ADR-0013 D8]
- `trap cfx63, 1`——立即数与地址无关，不加 `[]`。[Toolchain-01 §5][ADR-0013 D8]

**特例**：

- `ret rd0, 0`：`imms18` 为返回值，不是地址，不加 `[]`。[Toolchain-01 §5]
- `jump`/`call` 的 rrii 形式 `jump [rb3, rd0, 96]`：基址可为任意 RB；仅 iiii 形式要求基址为 `rb0`。[Toolchain-01 §5][ADR-0013 D4]

---

## §6 伪指令

- **权威源 = `spec/Toolchain-01-汇编语言.md §6`**（决策 `ADR-0013 D11`）。伪指令**不是**硬件指令，由汇编器在前端展开为真实硬件指令；**反汇编只输出真实硬件指令**。[Toolchain-01 §6][ADR-0013 D11]
- **保留 8 条合成型**：`set.rd rd, imm64`（常量 → 最少指令数 `set.zw`/`set.ow` + `or.w`/`andn.w`；符号/可重定位 → 固定 3 片 + `R_DADAO_ABS48`）、`set.rd rd, rs`（`rb2rd`/`rf2rd`/`ra2rd`/`rd2rd`）、`set.rb rb, imm64`（`set.zw-rb` + `or.w-rb`）、`set.rb rb, rs`（`rd2rb`/`rb2rb`）、`set.ft rf, imm32`（2 条 `set.w`）/ `set.ft rf, rs`（`rd2rf`/`ft2ft`）、`set.fo rf, imm64`（4 条 `set.w`）/ `set.fo rf, rs`（`rd2rf`/`fo2fo`）。[Toolchain-01 §6][ADR-0013 D11]
- **`set.rb` 细节**：允许 `wp0–wp3`；其为地址时 MUST ≤48 位；不补 `set.ow-rb`（rb 无 `set.ow` 变体）。[Toolchain-01 §6][ADR-0013 D11]
- **`ret` 语法**：保持 `ret rdha, imms18` 显式两操作数；不加无参形态。[Toolchain-01 §6][ADR-0013 D11]
- **删除（不实现，10 条）**：`nop`（用 `swym 0`）、`return`（用 `ret rd0, 0`）、`not.{b,w,t,o}`（用 `xnor.o rd, rs, rd0`；窄位宽 `not.b/w/t` 无等宽替代）、`neg.{b,w,t,o}`（用 `sub.sX`）。[Toolchain-01 §6][ADR-0013 D11]
- 当前状态：v5 汇编器**尚未实现**伪指令展开（8 条合成型报 `unrecognized instruction mnemonic`），属**待实现缺口**（见 §11）。[Toolchain-01 §6]

---

## §7 指导符（directives）

- 上游 `DADAO-11 §汇编兼容性` 规定 4 条数据指导符（Knuth/MMIX 的数据长度定义）：`.dd.b08`（8 位/1 字节）、`.dd.w16`（16 位/2 字节）、`.dd.t32`（32 位/4 字节）、`.dd.o64`（64 位/8 字节）。[Toolchain-01 §7][DADAO-11 §指导符（directives）]
- DADAO 的 octa = 8 字节，与 GAS 的 `.octa`（16 字节）不同，MUST NOT 使用 GAS 的 `.word`/`.octa` 语义。[Toolchain-01 §7][DADAO-11 §指导符（directives）]
- 当前状态：v5 汇编器尚未实现（报 `unknown directive`）；`.word` 被拒（与上述意图一致）。[Toolchain-01 §7]

---

## §8 汇编器选项

- 上游 `DADAO-11 §汇编兼容性` 规定 `-multiple-to-single`——将多寄存器指令转换为一系列单寄存器指令，转换过程保持助记符不变。[Toolchain-01 §8][DADAO-11 §汇编器选项]
- 当前状态：v5 汇编器尚未实现（`Unknown command line argument`）。[Toolchain-01 §8]

---

## §9 诊断

- 汇编器对以下情形报错（而非静默接受）[Toolchain-01 §9]：
  - 未知助记符 / 未知指导符 / 非法选项；
  - 寄存器序号越界（如 `rd64`）、寄存器组为空、范围越出 `rd63`；
  - 立即数越界（当前为静默环绕，属缺陷，见 §11）；
  - 需要 `rb0` 而基址非 `rb0` 的相对跳转 [ADR-0013 D4]；
  - 非法记号（如 `#`、`wp4`）——`#` 为 C 预处理器指令符（`#include`/`#define` 等），纯汇编中无条件非法（`AllowAdditionalComments = false`）[ADR-0013 D9]。
- 诊断文本 SHOULD 包含位置（文件:行:列）与「期望值」提示。[Toolchain-01 §9]
- 错误级别与进程退出码约定：`Toolchain-01` 未规定（UNSPECIFIED），本合约不臆造。[Toolchain-01 §9]

---

## §10 汇编 ↔ 反汇编往返

- 对任一合法指令，`汇编 → 反汇编` MUST 得到语义等价的文本（允许规范化，如空白的统一、`{}` 内单寄存器不带冒号）。[Toolchain-01 §10][ADR-0013 D3]
- `反汇编 → 汇编` MUST 产生逐字节相同的编码。[Toolchain-01 §10][ADR-0013 D3]

---

## §11 实现状态与缺口（截至 2026-09-23）

| 项 | 状态 |
|---|---|
| 9 个 M1 格式类与 151 条 M1 指令 | 已实现（旧语法） |
| 本规范的新记法（`[]`/`{}`/`?`/`:`） | 待实现（parser/printer/disassembler） |
| 双目的/多寄存器新记法（`{rdHA,rdHB}`/`{start:end}`） | 待实现 |
| 伪指令 8 条（合成型） | 待实现 |
| `.dd.*` 指导符 4 条 | 未实现 |
| `-multiple-to-single` | 未实现 |
| ABI 寄存器别名 | 未实现（`DwarfRegAlias` 不可用于汇编） |
| 越界立即数静默环绕 | 缺陷——MUST 报错 [Toolchain-01 §11][ADR-0013 D3] |

- 缺陷实例：`add.si rd8, 131072` → 编码为 −131072；`cmp.ui …, 4096` → 0；两者均须报错。[Toolchain-01 §11][ADR-0013 D3]

---

## §12 机器检查

- 本规范的检查（待建）[Toolchain-01 §12]：
  1. **三方一致性**：本规范指令语法表 ↔ `DADAOInstrInfo.td` 的 `AsmString` ↔ `contracts/opcodes.yaml` 的 `format`/`insn`；[Toolchain-01 §12]
  2. **示例可汇编**：本规范每条示例须能被汇编器接受（新语法实现后启用）；[Toolchain-01 §12]
  3. **往返一致**：§10 的两条断言；[Toolchain-01 §12]
  4. **缺口登记**：§11 缺口项须在 `.tao/knowledge/issues.yaml` 中有对应条目。[Toolchain-01 §12]
- `tools/infra/check_patch_tree.py`：组件补丁集九断言（与本文档无关，列出以说明仓库门控现状）。[Toolchain-01 §12]

---

## §13 cfx 别名约定

本节承载 cfx 系列别名的**书写约定**（规范正文「怎么写」）；决策与理由见 `ADR-0017`。**别名表**为机械生成投影 `.tao/knowledge/contract-cfx-aliases.md`（生成器 `tools/spec/gen_cfx_aliases.py`；门控 `tools/spec/check_cfx_aliases.py`），不属于规范正文。cfx 属 `scope: excluded`，本节约定随 M2 落地。[Toolchain-01 §13][ADR-0017]

### §13.1 归属与形态（D1/D2）

- cfx 别名属**汇编规范**：由汇编器内置**符号表**解析，不引入 cpp 头文件/宏。[Toolchain-01 §13.1][ADR-0017 D1]
- 不引入花括号：别名靠**符号前缀**（`cfx_`）区分，不新增 `{...}` 的第 5 种用途。[Toolchain-01 §13.1][ADR-0017 D2]

### §13.2 标量别名（D3）

- `cfx_<cfxname>` ⇔ `cfxHA`（如 `cfx_power` ⇔ `cfx63`）。[Toolchain-01 §13.2][ADR-0017 D3]

### §13.3 寄存器别名（D4）

- `cfx_<cfxname>_<regname>` ⇔ 三元组 `(cfxha, cg, rc)`。[Toolchain-01 §13.3][ADR-0017 D4]
- 无固定 `<mode>` 段：`supv`/`hypv`/`umon` 等只是某些 `regname` 的一部分（如 `..._supv_excp_vector`）。[Toolchain-01 §13.3][ADR-0017 D4]
- 映射查 spec 寄存器表的 `cg`/`rc` 列得到，MUST NOT 从名字字符串解析推断。[Toolchain-01 §13.3][ADR-0017 D4]

### §13.4 两种拼写（D5）

`cfx2rd`/`cfx2rc` 允许两种等价拼写，解析到**同一操作元组** `(cfxha, cg, rc, rdhd)`：[Toolchain-01 §13.4][ADR-0017 D5]

- **规范长形**：`cfx2rc cfxHA, cgHB, rcHC, rdHD`（如 `cfx2rc cfx_smon, cg2, rc0, rd2`）；
- **别名形**：`cfx2rc <cfxreg>, rdHD`（如 `cfx2rc cfx_smon_supv_excp_vector, rd2`）。

操作数个数（4↔2）与逗号数（3↔1）的差异在**指令级 parse** 中处理。[Toolchain-01 §13.4][ADR-0017 D5]

### §13.5 往返（D6）

- 反汇编器 MUST 输出**规范长形**（保证往返一致）；别名仅作**输入糖**。[Toolchain-01 §13.5][ADR-0017 D6]

### §13.6 文档示例（D7）

- 文档示例 SHOULD 优先使用**别名形**（人读友好，且与既有 `DADAO-11/22/23` 一致）。[Toolchain-01 §13.6][ADR-0017 D7]

### §13.7 数组寄存器单下标（D10）

- 数组 cfx 寄存器支持**单下标** `cfx_<cfxname>_<regname>[N]` ⇔ `(cfxha, cg, rc = rc_base + N)`。[Toolchain-01 §13.7][ADR-0017 D10]
- `N` MUST 落在别名表中该寄存器名称列范围 `[lo..hi]`（如 `0..63`、`0..7`）内；`rc_base` 为该行 `rc` 列的下界。[Toolchain-01 §13.7][ADR-0017 D10]
- 汇编器/检测器 MUST 接受该形（不视为违规）；`N` 越界 MUST 报错。[Toolchain-01 §13.7][ADR-0017 D10]

### §13.8 示例

```asm
cfx2rc cfx_smon_supv_excp_vector, rd2        ; 别名形
cfx2rc cfx_smon, cg2, rc0, rd2               ; 规范长形（与上行等价）
cfx2rd cfx_timer_regs[0], rd2                ; 数组单下标
escape cfx_smon, [excp_cause_ip, 4]          ; cfxha 写作标量别名
```

> 别名表投影（`.tao/knowledge/contract-cfx-aliases.md`）随 spec 寄存器表机械重算，禁止手工维护；上述示例均由该表展开所得。[Toolchain-01 §13.8][ADR-0017 D8]

---

## 附：与上游 `spec/` 的关系

本合约的规范真源是 v5 自定规范 `Toolchain-01`；上游 `spec/`（SimRISC 系列）可由 spec 模块任务按 `ADR-0012 D4` 修改。在两者并存期间，**指令语义与编码**以 `contract-isa.md`/`contracts/opcodes.yaml` 为准，**书写形式**以本合约/[`Toolchain-01`] 为准。[Toolchain-01 §附：与上游 spec/ 的关系]
