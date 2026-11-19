# `idl/` — ISA 语义源（IDL v0）

> **状态**：v0（第一版**可解析**形态；语义的**执行**不在本版范围）
> **基线**：以 `riscv-unified-db`（UDB）的 ISA Description Language 为准——`doc/idl.adoc` 是语言说明书，`tools/ruby-gems/idlc/lib/idlc/idl.treetop` 是语法真源；只在 UDB 不合适处用**现有语法 + 新函数**扩展，不改语言。
> **方向**：本目录的 `.idl` 是**机器可读语义源**；`spec/SimRISC-*` 里围栏语言标记为 `idl` 的代码块是它的**渲染结果**（`render.py` 生成，禁手改）。

| 文件 | 内容 |
|------|------|
| `SimRISC-NN.idl` | 该册每条指令的一段 operation（`# id:` 开头，id 与 `contracts/opcodes.yaml` 一致） |
| `lib/fp.idl` | 浮点语义库（ft/binary32 族，移植 UDB `fp.idl`；适配见 §4.7） |
| `render.py` | 渲染器 + 门控：按 `# id:` 切分 → 填 `spec/` 的 `<!-- IDL:<id> BEGIN/END -->` 标记 → `--check` 逐字节比对 |
| `.manifests.toml` | 本目录文件集清单（双向集合断言；`sha256` 待 M15 收口统一补） |

```text
python3 idl/render.py            # 生成/更新 spec 册内的块
python3 idl/render.py --check    # 逐字节校验（漂移 ⇒ 非零）；make check-idl-sync 调它
python3 idl/render.py --self-test # 临时树内 5 类注入自检（改 spec 块 / 改源不重渲染 / 删一条 id / 调用未声明函数 / 解码变量当内容用）
```

## 1. 语法基线（UDB IDL 子集）

按 `doc/idl.adoc` 的章节引用规则（不复制其全文），下表只列本版**实际用到**的构造：

- **注释**：`#` 到行尾（无多行注释）。
- **类型**：`Bits<N>`（无符号，`N` 编译期可知）、`Boolean`、`U32`（= `Bits<32>` 别名）；枚举 `enum`（成员写作 `Enum::Member`）。
- **字面量**：C 风格（`13`、`0xd`）与 Verilog 风格（`6'd0`、`2'b00`、`4'b1101`，允许下划线分组）。
- **运算符**（优先级同 Verilog）：`+ - * / %`、`<< >> >>>`、`& | ^ ~ !`、比较 `== != < <= > >=`、`&& ||`、`? :`、位切片 `i[msb:lsb]`、拼接 `{a, b}`、复制 `{N{a}}`。
- **加宽运算**：`` i `+ j ``（加宽加，结果宽 = 两操作数最大宽 + 1，精确保留进位）、`` i `<< j ``（加宽左移，`j` 为编译期常量）。**写法是「反引号 + 运算符」**——运算符前跟一个反引号（加宽加写作 `` `+ ``）；UDB 说明书正文经 AsciiDoc 转义后看着像 `+` 加反引号，**以语法文件为准**。
- **语句**：带类型声明 + 可选初始化、赋值、`if`/`else if`/`else`、`for`、`return`；条件必须是 `Boolean`（整数不隐式转布尔）。
- **类型转换**：`$signed(x)`（无符号 → 有符号视图）；赋值/二元运算的宽度扩展 = 有符号符号扩展、无符号零扩展。
- **函数**：`function NAME { returns T arguments ... description { … } body { … } }`；`builtin function` 无 `body`（由实现提供）；不支持递归。
- **不使用**（本版不需要，用到再引）：`tuple` 多返回值、`struct`、`bitfield`、`include`、`fetch` 块、CSR 作用域、`$encoding`、`implemented?`、RISC-V 的 `X[]`/`CSR[]`/`$pc`。

## 2. 命名约定（编码字段 ↔ 解码变量）

- operation 内直接用**编码字段名**作解码变量（大小写不敏感于 `contracts/opcodes.yaml` 的 `fields[].name`）：`rdHA`/`rdHB`/`rdHC`/`rdHD`、`rbHA`/`rbHB`/`rbHD`、`cfxHA`、`imms12`（12 位有符号）、`immu18`（18 位无符号）、`immu6`（6 位无符号）。
- **散文的 `rdHC` 指内容、`.idl` 的 `rdHC` 是寄存器号**：散文（`SimRISC-04 §2.2`、`SimRISC-10 §2`）里 `rdHC`/`rdHD` 表示**该寄存器的内容**；`.idl` 里同名标识符是 **6 位解码变量（寄存器号）**，取内容须写 `rd[rdHC]`。`rdHC[i]` 取到的是**寄存器号的位**（`idlc` 不校验位宽、静默通过），故 `render.py --check` 断言「解码变量不得紧跟 `[`」（docstring 的 F 类）。
- **汇编层的立即数名比编码层宽 2 位**（字节偏移带 `<< 2`，是命名约定、不是语言扩展）：

  | 指令族 | 汇编层写法 | 编码层字段 | 换算 |
  |--------|-----------|-----------|------|
  | `br.eq`/`br.ne` 等 `rrii` | `imms14` | `imms12` | `imms14 = imms12 << 2` |
  | `br.*` 的 `riii` | `imms20` | `imms18` | `imms20 = imms18 << 2` |
  | `jump [rb0, imms26]` | `imms26` | `imms24` | `imms26 = imms24 << 2` |
  | `escape` | `imms20` | `imms18` | `imms20 = imms18 << 2` |
  | `aip.si` | `imms30` | `imms18` | `imms30 = imms18 << 12`（4 KiB 页粒度） |

- **`IP`** = **当前正在执行的指令的地址**（不是「下一条」，无 `±4` 偏移）；写成 `ip()`，不写 `PC`。
- operation 只描述**单条指令**对架构状态的作用；未写到的状态保持不变。不描述取指、流水、实现时序。

## 3. 寄存器模型

四组寄存器各 64 个 64 位，按**数组**访问（`rd[rdHA]` 这类写法）；`fo`/`ft` 是 `rf` 的**数据视图**（同一存储的三种读法），声明见 §4.2。

| 组 | 声明 | 用途 | 0 号语义 |
|----|------|------|----------|
| `rd[]` | `Bits<64> rd[64]` | 数据寄存器 | 读出恒 0；写入丢弃（**该指令是否把目的 `rd0` 判为非法，由各指令自己写**，如 `ld.o` 判 ILLI） |
| `rb[]` | `Bits<64> rb[64]` | 基址寄存器 | 读出 = `IP`（整 64 位，低 48 位为有效地址）；**指令正文不得把 `rb0` 当普通目的写**——控制转移一律经 `jump()`（其函数体是唯一允许写 `rb0` 的地方） |
| `rf[]` | `Bits<64> rf[64]` | 浮点/状态寄存器（整 64 位视图） | `rf[0]` = FCSR（舍入模式 + 异常状态位） |
| `fo[]` | `Bits<64> fo[64]` | `rf` 的 64 位数据视图 | 同 `rf[0]` |
| `ft[]` | `Bits<32> ft[64]` | `rf` 的低 32 位数据视图 | `ft[0]` 只覆盖 FCSR **可写位 `[4:0]`** |
| `ra[]` | `Bits<64> ra[64]` | 返回地址栈（**逻辑栈序**，`ra63` = 栈顶） | `ra[0]` = `{RACNT, MRPTR}` 元数据（栈深 + 物理环指针）；物理环状缓冲**不暴露**，由 `ras_*` 函数承担 |

**写宽度**：`rd`/`rb`/`ra`/`rf` 整 64 位；`ft` 只写低 32 位（`ld.t`/`ldm.t` 走 `ft[]`）；`fo` 整 64 位。`rf` 只用于**整 64 位搬移**（`rf2rf`/`rf2rd`/`rd2rf`）与 FCSR 访问。

**按 wyde 写 = 切片赋值**：`set.w`/`or.w`/`andn.w`/`set.ow`/`set.zw` 只改 `wpN` 选中的那**一个** wyde ⇒ 写成切片赋值 `rf[d][wpN*16+15 : wpN*16] = …`（`rd`/`rb` 同理，换组名即可），其余位保持；`set.ow`/`set.zw` 的「其余 48 位全 1 / 全 0」按整寄存器赋值表达。**不为此新增库函数**。

**零号语义是模型不变量**（与 UDB 把 `X[0]` 硬编 0 同构）：存储视图是数组，0 号的特殊行为由模型保证；operation 只额外写「本条指令对 0 号的非法判定」。

## 4. 语义库

四个寄存器组、当前指令地址、访存、异常（进入与退出）、保留标记、返回地址栈、核芯功能扩展的分发/寄存器访问/屏障，全部用「现有语法 + 本库函数」表达：带 `body` 的给参考定义，`builtin function` 由实现（golden model / ISS / RTL）提供。**本节代码块按 §4.1→§4.6 顺序拼接、再接 `idl/lib/*.idl`（§4.7）即一份可编译的 `.idl` 库**（与各册 operation 拼接后交 `idlc` 类型检查）。

### 4.1 类型与常量

```idl
%version: 0.1

enum ExceptionCode {
  CfxTrap     0x0001
  CfxMem      0x0002
  CfxReg      0x0004
  CfxEsc      0x0008
  CfxPerm     0x0080
  Illegal     0x0100
  Undefined   0x0200
  RasOverflow 0x0400
  RasUnderflow 0x0800
  Malign      0x1000
  Ialign      0x2000
}

enum RunMode {
  User 0
  Jail 1
  Supv 2
  Hypv 3
}
```

- `ExceptionCode` 成员值 = SEE 的异常位索引对应的 one-hot 值（`excp_cause_id` 口径）。
- `RunMode` 的四个成员与四个 monitor 一一对应（`user`/`jail`/`supv`/`hypv`）。

### 4.2 寄存器模型

```idl
# 四组寄存器各 64×64；0 号语义见 README §3（模型不变量）
Bits<64> rd[64];
Bits<64> rb[64];
Bits<64> rf[64];
Bits<64> ra[64];

# rf 的两个数据视图（同一存储的 64 位 / 低 32 位读法）
Bits<64> fo[64];
Bits<32> ft[64];
```

### 4.3 控制与异常

```idl
builtin function ip {
  returns Bits<64>
  description {
    当前正在执行的指令的地址（= `rb0` 读出）。64 位宽，但**高 16 位恒 0**（48 位地址零扩展）。
    `IP` 不是「下一条」，也没有 `±4` 偏移。
  }
}

builtin function mode {
  returns RunMode
  description {
    当前运行模式。
  }
}

function jump {
  arguments Bits<64> target
  description {
    置下一个待执行指令的地址：`target` 的**低 48 位**（`target[47:0]`）写回 `rb0`，其余 16 位恒 0；
    取指时用其低 48 位。这是唯一允许写 `rb0` 的通道（指令正文不得把 `rb0` 当普通目的）。
  }
  body {
    rb[6'd0] = target[47:0];
  }
}

builtin function raise {
  arguments ExceptionCode code, RunMode from_mode, Bits<64> addr
  description {
    进入**同步异常**流程：`code` 为异常码，`from_mode` 为发生时的运行模式，`addr` 写入异常帧的
    `excp_cause_ip`（非法类填该指令地址、地址类填故障地址）。
    **进入目标由 `code` 按 spec 路由**：一般同步异常进**当前运行模式 monitor**（`DADAO-12 §5.2`）；
    `CFXESC` 进**当前 cfx**（`§5.3` 步骤 0）。`CFXTRAP` 不走本函数，走 `cfx_trap_enter`。
  }
}
```

### 4.4 访存与对齐

```idl
builtin function fetch_memory {
  returns Bits<64>
  arguments U32 width_bits, Bits<48> ea
  description {
    从有效地址 `ea` **取指**，返回指令字（低 `width_bits` 位有效）。取指故障由存储系统决定。
  }
}

builtin function read_memory {
  returns Bits<64>
  arguments U32 width_bits, Bits<48> ea
  description {
    按**大端**从有效地址 `ea` 读 `width_bits` 位（`8`/`16`/`32`/`64`），结果零扩展至 64 位：
    最低地址的字节是最高有效字节。符号扩展由各指令自己做。访存故障（`CFXMEM`/`CFXPERM`）
    与核内/虚拟路由由存储系统决定。
  }
}

builtin function write_memory {
  arguments U32 width_bits, Bits<48> ea, Bits<64> value
  description {
    按**大端**把 `value` 的低 `width_bits` 位写到有效地址 `ea`；故障语义同 `read_memory`。
  }
}

function is_naturally_aligned {
  returns Boolean
  arguments U32 width_bits, Bits<48> value
  description {
    `value` 是否按 `width_bits` 位自然对齐（对齐判定与 UDB 同名同义；异常由 operation 显式 `raise`）。
  }
  body {
    return true if width_bits == 8;        # 一切地址都按字节对齐

    Bits<48> mask = (width_bits / 8) - 1;
    return (value & ~mask) == value;
  }
}
```

### 4.5 保留标记与返回地址栈

```idl
builtin function reservation_set {
  arguments Bits<48> ea, U32 width_bits
  description {
    为本 hart 设置保留标记；**键 = 精确地址 + 访问宽度**（不按 cache line 扩大）。
  }
}

builtin function reservation_clear_all {
  description {
    清除本 hart 的全部保留标记。
  }
}

builtin function store_conditional {
  returns Bits<64>
  arguments Bits<48> ea, U32 width_bits, Bits<64> value
  description {
    原子地完成「检查本 hart 保留标记 → 条件写入 → 清标记」，返回 **0 = 成功、1 = 失败**。
    保留标记键 = 精确地址 + 访问宽度（同 `reservation_set`）；失败时不写内存，但**同样清除标记**。
    跨 hart 原子性与「他 hart 对同址的写使标记失效」作为模型不变量，不在此展开。
    （照 UDB `store_conditional` 先例：判定与写入合成一个原子动作，避免「先查再写」的中间态。）
  }
}

builtin function ras_push {
  arguments Bits<48> ret_addr
  description {
    压入返回地址（逻辑栈顶 = `ra63`）；溢出触发 `RASOF`。
  }
}

builtin function ras_pop {
  returns Bits<48>
  description {
    弹出返回地址（逻辑栈顶 = `ra63`）；下溢触发 `RASUF`。
  }
}

builtin function ras_cnt {
  returns Bits<6>
  description {
    当前逻辑栈深（= `ra[0]` 的 `RACNT`）。
  }
}
```

### 4.6 核芯功能扩展

```idl
builtin function cfx_is_reserved {
  returns Boolean
  arguments Bits<6> cfxha
  description {
    该编号是否为保留核芯功能扩展（保留编号的分配见 SEE）。
  }
}

builtin function cfx_trap_denied {
  returns Boolean
  arguments Bits<6> cfxha
  description {
    目标核芯功能扩展当前运行模式的 `cfxtrap` 掩码是否拒绝源核芯功能扩展。
  }
}

builtin function cfx_trap_enter {
  arguments Bits<6> cfxha, Bits<18> immu18
  description {
    合法且被允许的 `trap`：计数、保存现场、切换运行模式与当前核芯功能扩展、跳转到目标核芯
    功能扩展的异常向量；`immu18` 为服务号，写入异常帧的 cause 信息。细节以 SEE 的异常进入
    流程为准（本版按「服务号写入 `excp_cause_info`」落，见 §5 的搁置项）。
  }
}

builtin function inner_cfx_code {
  returns Bits<6>
  description {
    当前正在执行的核芯功能扩展编号（与 SEE 的 `inner_cfx_code` 同名同义）。
  }
}

builtin function cfx_frame_valid {
  returns Boolean
  arguments Bits<6> cfxha
  description {
    该核芯功能扩展当前是否持有**有效异常帧**（`cfx_⟨cfxname⟩_excp_cause_id != 0`）。
    帧无效时 `escape` 触发当前核芯功能扩展的 `CFXESC`。
  }
}

builtin function cfx_escape_enter {
  arguments Bits<6> cfxha, Bits<64> imm
  description {
    异常退出（`escape`）：按 SEE 的异常退出流程恢复中断屏蔽、运行模式（`inner_run_mode`）与
    当前核芯功能扩展（`inner_cfx_code`），`escape_num` 递增，控制转到
    `excp_cause_ip + imm`（`imm` 为**字节**偏移，合法值 0 或 4）。
    目标是否为保留编号、`cfxha == inner_cfx_code`、帧是否有效、SBZ 是否为零，均由 operation
    先判定再调用本函数。
  }
}

builtin function cfx_read {
  returns Bits<64>
  arguments Bits<6> cfxha, Bits<6> cg, Bits<6> rc
  description {
    读核芯功能扩展寄存器 `cfx_⟨cfxname⟩_cg⟨cg⟩_rc⟨rc⟩`，返回其 64 位值。
    **本函数只做访问**：寄存器是否存在、读写权限（RW/HW/RO/保留）由 SEE 的寄存器表描述
    （`DADAO-12 §3`–`§4`），IDL 不在 operation 里判定权限；`CFXREG` 由实现按该表给出。
  }
}

builtin function cfx_write {
  arguments Bits<6> cfxha, Bits<6> cg, Bits<6> rc, Bits<64> value
  description {
    写核芯功能扩展寄存器（`value` 整 64 位）。存在性与权限语义同 `cfx_read`（见 SEE 寄存器表）。
  }
}

builtin function cfx_fence {
  arguments Bits<6> cfxha, Bits<6> pred, Bits<6> succ
  description {
    核芯功能扩展屏障：约束本 hart 对资源域 `cfxha`（`cfx0` = all cfx）上 `pred` → `succ`
    所列访问类型的顺序与可见性；`pred`/`succ` 为 6 位访问类型掩码（位含义见 SimRISC-11 §5），
    零掩码是合法 no-op。
    照 UDB `fence` 的做法**只给声明、无 body**：顺序语义由实现提供，IDL v0 不建模。
  }
}
```

### 4.7 浮点原语（`idl/lib/fp.idl`）

浮点原语见 `idl/lib/fp.idl`，语义按 IEEE 754-2019（标志/舍入口径见 `SimRISC-00 §2.3.1`、
`SimRISC-07 §1.3`）。移植自 UDB `spec/std/isa/isa/fp.idl`，**三处适配**：① 异常标志写
`rf0[4:0]`（sticky）、舍入模式读 `rf0[33:32]`（不是 `CSR[fcsr]`/`CSR[frm]`）；② **删掉
NaN-boxing**——DADAO 的 ft 结果「只写目的低 32 位、高 32 位保持」（`SimRISC-00 §2.3`），
`nan_box`/`check_f_ok` 及其高半检查一并删除；③ 函数名指令级统一 `ft_*`
（`ft_to_i32`/`i32_to_ft`…），`softfloat_*` 原语保留原名。`render.py` 的「已声明函数」
扫描面 = 本节代码块 **+ `idl/lib/*.idl`**。

覆盖范围：分类（`is_sp_*`）、转换（`ft_to_i32`/`ft_to_ui32`/`i32_to_ft`/`ui32_to_ft`）、
算术（`ft_add`/`ft_sub`/`ft_mul`/`ft_div`/`ft_muladd`/`ft_sqrt`）、取整
（`round_ft_to_integral`）与 softfloat 位操作原语。**两处实现口径差异**（语义仍按
IEEE 754-2019）：① `ft_sqrt` 用精确整数平方根（`ft_isqrt64`）而非 softfloat 的
32 位倒数平方根近似宏（该近似在 C 里依赖 `uint_fast32_t` 的平台宽度）；② `ft_muladd`
的 `op` 取反口径也贯穿「加数为 ±Inf / 乘积为 ±0」两条早退路径（UDB 只服务 RISC-V 的 addC）。
UDB 本身若干转写错误（溢出判据、无符号比较、qNaN 置 NV、负次正规相加丢符号等）未照抄，
逐条记在 `idl/lib/fp.idl` 文件头。

## 5. 语法扩展提案

三态：**采纳** / **搁置** / **否决**。判定口径：能用「现有语法 + §4 的新函数」表达 ⇒ 不进本表。

- **采纳：0 条**——本版没有任何语言层扩展（不改 `idlc` 语法/类型系统）。
- **搁置：1 条**——`trap` 的服务号 `immu18` 落到哪个 cfx 寄存器（`excp_cause_info` vs handler 回读指令字）。SEE 只规定 `excp_cause_info` 是「辅助信息」；本版按「写入 `excp_cause_info`（cg5 rc4）」落 `cfx_trap_enter` 的描述，**以 SEE 为准**。这是语义口径、不是语法扩展，故不阻断本版。
- **否决：4 条**（记下以免重复讨论）：
  1. **把 `X[]` 赋成四组寄存器**——`X` 是 RISC-V 的 32 个 `x` 寄存器模型（`x0` 硬编 0）；DADAO 需要 4×64 且 0 号语义各异 ⇒ 改内建等于改语言。
  2. **加 `@endian(big)` 之类属性**——字节序是**访存函数**的语义，写进 `read_memory`/`write_memory` 即可。
  3. **把 `raise`/`jump` 做成关键字**——UDB 已把它们定义为（内建）函数，DADAO 只需提供自己的库，无需新语法。
  4. **为 48 位地址新增 `Addr48` 类型**——`Bits<48>` + 位切片已够；新增类型要同步 `idlc` 类型系统。

## 6. `idlc` 复用评估

**结论：只借语法，并在编写期用 `idlc` 做类型检查的 oracle；`idlc` 不进任何门控**（门控是纯 Python，不引入 Ruby 运行期依赖）。

| 评估项 | 结论 | 证据 |
| --- | --- | --- |
| 许可证 | `BSD-3-Clause-Clear`（UDB 根 `LICENSE-BSD-3-Clause-Clear.txt` + idlc gem 自带 `LICENSE`）：可复用/修改/再分发（保留版权与免责声明） | 文件头 `SPDX-License-Identifier: BSD-3-Clause-Clear` |
| 版本 | `idlc` 0.1.8（`Idl::Compiler.version`），来自 UDB 只读参考检出 | `idlc -v` |
| 能否离线 | **能**：运行期无网络系统调用，退出码正常 | `strace -f -e trace=%network` 下 `socket`/`connect` 计数 = 0 |
| 是否绑定 RISC-V CSR / `X[]` | **不绑定**：`X[]` 只是 CLI 在无架构配置时塞的 mock 寄存器组（32 个）；`CSR[]` 仅在 arch 传表时存在；本仓用自己声明的 `rd[]`/`rb[]`/`rf[]`/`ra[]` 数组（§4.2） | 空符号表下 `X[40]` 报 `out of range (< 32)`；本仓库 + operation 拼接后类型检查通过 |
| 语义库是否内含 | **不含**：`raise`/`jump`/`read_memory`/`is_naturally_aligned` 都不在 `idlc` 里，须由本仓 §4 提供 | 空符号表下 `raise(...)` 报 `No symbol raise`；补 §4 后通过 |
| 只借语法/解析器 | 可行：`idl.treetop` + `IdlParser` 只依赖 `treetop`，与 `udb` gem 无耦合。但门控保持纯 Python ⇒ 渲染器只做逐字节搬运，`idlc` 只作编写期 oracle | `render.py`；`idlc compile --root isa` |
| 直接复用 `idlc` 作门控 | **不采纳**：需 Ruby 运行时 + gem 集合，L1 门控成本高；若后续要生成可执行参考模型，再把它作为独立工具（非门控）评估 | 本表 |

### 6.1 实测命令与退出码（编写期 oracle，不进 `Makefile`）

> 「§4 库」= 把 §4.1–§4.6 的 idl 代码块按序拼成一个文件。

| # | 命令 | 实测 rc | 说明 |
| --- | --- | --- | --- |
| 1 | `idlc -v` | 0 | 打印 `IDL Compiler 0.1.8` |
| 2 | `printf 'X[2] = 15;\n' \| idlc tc inst /dev/stdin` | 0 | 类型检查基线 |
| 3 | `printf 'X[2] = 15\n' \| idlc tc inst /dev/stdin` | 1 | 缺分号 ⇒ `SyntaxError` |
| 4 | `printf 'X[40] = 1;\n' \| idlc tc inst /dev/stdin` | 1 | `Array index out of range (< 32)` ⇒ 内建 `X` 只有 32 个 |
| 5 | `printf 'raise(ExceptionCode::Illegal);\n' \| idlc tc inst /dev/stdin` | 1 | `No symbol raise` ⇒ 语义库不在 `idlc` 内 |
| 6 | §4 库 → `idlc compile --root isa` | 0 | 枚举 / 数组声明 / `function` / `builtin function` |
| 7 | §4 库 **+ 各册 `.idl`** 直接拼接 → `idlc compile --root isa` | **1** | `isa` 根**只接受声明**：首个 operation 处 `SyntaxError`（`all.idl:166`）。⇒ 「库进 `isa`、operation 逐条进 `instruction_operation`」才是这套语法的正确拼法（第 8 条），**不是**本仓写法问题 |
| 8 | 逐条 operation → `idlc compile --root instruction_operation` | 0（5/5） | 单条 operation 可独立解析 |
| 9 | Ruby 驱动：§4 库 `compile_file` + `add_global_symbols` → 逐条 operation 注入解码变量 → `type_check` | 0 | 库函数 **16/16**、operation **5/5** 通过（含 `rd[rdHA]` 数组访问、`Bits<128>` 拼接、`raise` 三参） |
| 10 | 负向：把 `read_memory(64, ea)` 改成单参后重跑第 9 条 | 1 | `Wrong number of arguments to 'read_memory'`（期望 2、实得 1）⇒ oracle 可达 FAIL |
| 11 | `strace -f -e trace=%network idlc tc inst …` | 0 | `socket`/`connect` 计数 = **0** ⇒ 离线可跑 |

> 具体命令输出与临时文件属编写期证据，不入库；结论记在本任务的完成区。

## 7. 变更记录

- **v0（初版）**：确立「`.idl` 为源、spec 块为渲染结果」的方向；语法基线（§1）、命名约定（§2）、寄存器模型（§3，数组式 + `fo`/`ft` 视图）、语义库（§4，UDB 同名 `read_memory`/`write_memory`/`fetch_memory`/`is_naturally_aligned`、三参 `raise`、`ras_*`、`reservation_*`）、扩展提案（§5，采纳 0 条）与 `idlc` 评估（§6）。
- **v0.1（语义库 v1）**：`ip()` 改 `Bits<64>`（高 16 位恒 0），`jump` 只写回 `target[47:0]`；§3 补「按 wyde 写 = 切片赋值」；§4.6 补 `inner_cfx_code`/`cfx_frame_valid`/`cfx_escape_enter`（异常退出）、`cfx_read`/`cfx_write`（cfx 寄存器访问，权限由 SEE 寄存器表描述）与 `cfx_fence`（无 body）。
- **（未定版）浮点库**：新增 `idl/lib/fp.idl`（ft/binary32 族，§4.7）；`render.py` 的「已声明函数」扫描面加 `idl/lib/*.idl`（含 `?` 后缀的函数名）。
- 待 M15 收口：`idl/.manifests.toml` 统一补 `sha256`。
