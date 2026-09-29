# DADAO SimRISC 0.5.3（v5 M1）—— Golden 模型设计说明

本文是 `dadao_interp_v5.py`（golden 参考模型）与 `validate_interp_v5.py`
（测试向量运行器）的配套文档，回答三个问题：

1. **比较两个 ISA**——0628 的 SimRISC **0.4.1** 与 v5 的 **0.5.3**（§1）。
2. **用文字解释全部设计决策**——凡规范文本存在歧义之处，本 golden
   所采取的每一种解释（`D-v5-*` 决策，§2）。
3. **完整的 golden 代码**——`dadao_interp_v5.py`，验证情况见 §3。

资料来源：v5 ISA 合约 `.tao/knowledge/contract-isa.md`（golden 中每个处理函数
都引用了对应章节）、其背后的规范正文 `spec/SimRISC-0*.md`、
`contracts/opcodes.yaml`（译码真值）、ADR-0004（ISA 未明确、留给测试机绑定的
部分）、`tests/vectors/schema.md`（向量语义）。下文 0.4.1 一栏来自 0628 仓库的
`contracts/isa/spec.md` + `tools/dadao_interp.py`（即 SimRISC-00..04 v0.4.1 版
wiki，已证明与 0628 的 Source 提交完全一致）。

---

## §1 ISA 对比：0.4.1（0628）vs 0.5.3（v5）

### §1.1 牵一发而动全身的变化：`rb0`

| | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| `rb0` 读出值 | **下一条**指令地址（PC+4） | **当前**指令地址（ADR-0004 D6.5） |
| `rb0[63:48]` | 恒为零 | 可读出完整 64 位值 |
| 顺序执行 `pc_next` | `rb0`（fall through） | `X+4` |
| `call` 压栈 | `rb0`（= PC+4） | `X+4` |
| `rela` 基址 | `(rb0)&~0xFFF` = 下一条指令所在页 | `(rb0)&~0xFFF` = 当前指令所在页 |
| 分支/跳转目标 | `rb0 + imm<<2` | `rb0 + imm<<2`（公式相同，基址平移了一条指令） |

所有 PC 相对寻址的*公式*不变，但整体平移了一条指令：v5 中一条
`imm=2` 且命中的分支落到 `X+8`（`rb0+8`），而 0.4.1 中同一编码落到
`X+4+8`。因此向量的 `expected_pc` 只能与退役时刻的 `rb0`/`pc_next`
比较（§2.9）。

### §1.2 整数运算：单 signed 语义 → uo/so 分裂，除法退出 `rrrr`

| 方面 | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| `rrrr` 加减 | `add`/`sub`：**符号扩展**到 128 位，只有一种 | `add.uo`/`sub.uo`**零扩展**到 128 位（进位/借位在 `rdha`）；`add.so`/`sub.so`**符号扩展**到 128 位 |
| `rrrr` 乘法 | `muls`/`mulu` 双目标 | `mul.uo`/`mul.so` 双目标（形态相同，改用点分命名） |
| `rrrr` 除法 | `divs`/`divu` 双目标：**余数 → rdha，商 → rdhb** | **已删除**——不再有双目标除法 |
| 定宽除法/求余 | 无 | `div.s/u` + `rem.s/u` × byte/wyde/tetra/octa，单目标 `orrr`，按位宽独立语义：向零截断、除零 → ILLI、INT_MIN/−1 → ILLI（**按各宽度判定**） |
| 定宽加减乘 | 无 | `add/sub/mul.s/u` × b/w/t/o，单目标 `orrr`，全覆盖写回（§2.5） |
| `addi` | `op 0x19`：`rdha = rdhb + imms12`（双源、12 位立即数） | `add.si`：**原地** `rdha += sext18`（`riii`，18 位立即数） |

双目标合法性规则不变（`rdha==rdhb==rd0` → ILLI；`rdha==rdhb≠rd0` →
ILLI）；变化的只是数值语义多了 uo/so 分裂。

### §1.3 RB 模型：48 位（高 16 位保留）→ 完整 64 位

这是影响面最大但最"静默"的一次语义迁移：0.4.1 中所有写 RB 的算术指令都只
计算**低 48 位**并保留 `rb[63:48]`；0.5.3 中 RB 算术是**完整 64 位**（结果的
高 16 位可用，例如用于溢出检测——`add.so-rb`/`sub.so-rb` 向量的 `full64`
注释即指此）。

| 指令 | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| RB 加减（`orrr`） | `(rbhc[47:0] ± rdhc[47:0]) & MASK48`，高 16 位**保留** | **完整 64 位** `(rbhc ± rdhd) & MASK64`（D-v5-1） |
| RB 加立即数 | `addi`（`op 0x49`）：`rbha = rbhb + imms12`，低 48 位，高位保留 | `add.si-rb`（`riii`）：**原地** `rbha += sext18`，完整 64 位 |
| RB 比较 | `cmp`（ha 0x2D）：无符号**低 48 位**比较 → RD | `cmp.uo-rb`：无符号**低 48 位**比较 → RD——*语义不变*（D-v5-4） |
| `rela` | 基址 `(rb0=PC+4)&~0xFFF`，高 16 位保留 | 基址 `(rb0=当前地址)&~0xFFF`，高 16 位保留（D-v5-10） |
| 块拷贝（RB 作源） | 源截断到 **48 位**（`rb2rd`、`rb2rb`） | **完整 64 位**，双向无转换（D-v5-2） |
| 块拷贝（RB 作目标） | 完整 64 位写（`rd2rb`） | 完整 64 位（形态不变） |
| 块拷贝 RA | 无 | 新增 `ra2rd`、`rd2ra`（完整 64 位，`ra0` 可作源） |
| RB wyde 立即数 | 只有 `orw`/`andnw`/`setzw`（RB 没有 `setow`） | RD 和 RB 都有 `set.ow`/`set.zw`/`or.w`/`andnw` |

### §1.4 逻辑/移位/扩展：仅 64 位 → 按位宽 RMW

| 指令 | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| 逻辑运算 | `and/orr/xor/xnor` 完整 64 位按位运算，**全覆盖写回** | `and/or/xor/xnor` × b/w/t/o：只算低位，**目标寄存器的高位保留**（读-改-写，D-v5-7） |
| 移位 | `shlu/shrs/shru` 完整 64 位，位移量 `rdhd[5:0]`/`immu6`，无越界检查，全覆盖写回 | `shl/shr.s/u` × b/w/t/o：带越界检查（`shamt > N` 则 **ILLI**），RMW |
| 扩展 | `exts/extz` 完整 64 位 | `ext.s/u` × b/w/t/o：`hd > N` 则 **ILLI**，RMW（§3.4.2 填充规则） |
| 移位/扩展位移量 | `orrr`：`rdhd[5:0]`（64 位下不可能越界，无检查）；`orri`：`immu6`（无检查） | `orrr`：`rdhd[5:0]`，**动态**检查 `> N` → ILLI；`orri`：`immu6`，**静态**检查 `> N` → ILLI（D-v5-5） |
| 寄存器-寄存器比较 | `cmps`/`cmpu` 完整 64 位 → −1/0/1 | `cmp.s/u` × b/w/t/o：源截断到位宽，结果为完整 64 位 −1/0/1（全覆盖） |
| 立即数比较 | `cmps`/`cmpu`（`rrii`，sext12/zext12） | `cmp.si`/`cmp.ui`（语义相同，改点分命名） |

### §1.5 控制流：骨架相同、`rb0` 换基址、新增 RB 分支

| 方面 | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| 单寄存器分支 | `brn/brnn/brz/brnz/brp/brnp`（`riii`，imms18） | `br.n/nn/z/nz/p/np`（条件相同，附录 B） |
| 双寄存器分支 | `breq/brne`（`rrii`，imms12） | `br.eq/ne`（相同） |
| RB 分支 | 无 | **新增 `br.z-rb`/`br.nz-rb`**（`riii`，imms18）：对 RB 作完整 64 位判零（D-v5-6） |
| `jump`/`call` | 相对（`imms24`）+ 绝对（`rbha+rdhb+imm<<2`） | 同样的两种形式 |
| `call` 返回地址 | 压栈 `rb0`（=PC+4） | 压栈 `X+4`（值相等，推导不同） |
| `ret` | 弹 RAS；`rdha = imms18`（`rd0` 丢弃，**合法**） | 完全相同 |
| RAS | M1 只有 **RegRAS**（`ra0` 低 48 位必须为 0；`ra1` 有效 → RASOF；MemRAS 被排除） | **完整 RegRAS+MemRAS**，经 `ra0` 溢出/回填，递归压缩，精确 RASOF/RASUF（合约 §5.6） |

### §1.6 访存：RA 加入 load/store 家族

| 方面 | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| RD ld/st | 单个 + 多个，sb/ub/sw/uw/st/ut/o | 完全相同的集合 |
| RB ld/st | `ldo/sto/ldmo/stmo`（仅 octa） | `ld.o/st.o/ldm.o/stm.o`（相同，点分命名） |
| RA ld/st | **只有多个**（`ldmo-ra`/`stmo-ra`），无单个 | **单个 + 多个**（`ld.o/st.o/ldm.o/stm.o`）；`ra0` 可作目标，合法 |
| 有效地址 EA | `(rb + imm) & MASK48` / base+idx+i·w | `(rb[47:0] + imm) & MASK48`——模加法下两者恒等（D-v5-9） |
| 多个访问快照 | base + `rdhc[47:0]` 快照，精确预检全部 EA | 完全相同 |
| 对齐 | byte 不检查；w/t/o 自然对齐否则 MALIGN | 完全相同 |
| RA 传输 | 不透明 64 位，引用计数不动（KL-107a） | 完全相同（合约 §4.9） |

### §1.7 系统/杂项：`unimp` 消亡、`swym` 搬家、`fence` 登场

| 方面 | 0.4.1（0628） | 0.5.3（v5） |
|---|---|---|
| `unimp` | `oiii` ha=0x3F → ILLI | **已删除** |
| `illi` | 无 | `oiii` op 0x00/ha 0x00：**全零指令字 → ILLI**（合约 §2.9/§7.2） |
| `swym` | `oiii` ha=0x00 NOP | **`iiii`**：`swym 0` 为 NOP，`swym N` 为时延提示（golden 中一律 NOP） |
| `fence` | 无 | `oiii` 屏障，低 4 位为屏障类型，**SBZ bits[17:4]**（非零 → ILLI；golden 中检查后 NOP） |
| RF/cfx/LR-SC | M1 排除 RF | M1 排除 RF + cfx + LR-SC → ILLI（ADR-0004 D5.1） |
| 保留编码 | UNDI | UNDI（不变，合约 §2.9） |

### §1.8 异常分类：名字不变，新增两种触发者

`ILLI / UNDI / MALIGN / IALIGN / RASOF / RASUF` 两边都有。v5 新增的*触发*
情形：按位宽 `div/rem` 异常、移位/扩展越界（`shamt/hd > N`）、`fence` SBZ、
MemRAS 溢出/回填异常。测试机 `UNMAPPED` 在两边的向量集中都存在，且两边的
golden 都不建模（验证器判 `SKIP-machine`）。

---

## §2 设计决策

每条 `D-v5-*` 都是规范文本允许多种解读、而本 golden 必须固定一种之处。
全部 747 条 `tests/vectors/isa/*.yaml` 向量已用于交叉核对：向量能钉住的
行为，决策服从向量；向量沉默的（只有小数值探针），决策取规范字面解读，
并明确标出。

### D-v5-1 · RB 加减 / add.si 取完整 64 位
合约 §4.5，对应 0.4.1 的"低 48 位 + 高 16 位保留"（§1.3）。`add.so-rb` /
`sub.so-rb` 向量带有明确的 `full64` 注释（高 16 位 = 结果位，可用于溢出
检测）。`add.si-rb` 继承完整 64 位原地语义。没有任何向量探测到冲突的高位
情形。*结论：完整 64 位。*

### D-v5-2 · 块拷贝双向均为完整 64 位
合约 §3.7/§4.3/§4.9.3。0.4.1 把 RB 源截到 48 位；v5 的传输是不透明 64 位，
双向都不做转换，包括新增的 `ra2rd`/`rd2ra`。迭代顺序为递增 `i`、每对先读
后写（与 0.4.1 相同）。*结论：完整 64 位，不截断。*

### D-v5-3 · div/rem 的零检查针对截断后的除数
合约 §3.1.5 规定源先截断到位宽再运算；因此零检查看到的是截断后的值
（64 位下非零、位宽内为零的除数同样触发异常）。商/余数向零截断（C99）；
`INT_MIN/−1` **按各宽度**触发异常（例如 `.sb` 下 `0x80/0xFF` 触发）。
结果为全覆盖写回（符号/零扩展到 64 位）。*结论：先截断再检查，与规范的
运算顺序一致。*

### D-v5-4 · `cmp.uo-rb` 比较低 48 位、无符号
合约 §4.6 保持 0.4.1 `cmp` 的形态：`rbhc[47:0]` 对 `rbhd[47:0]` 作无符号
比较，完整 64 位 −1/0/1 写入 `rdhb`。即使 RB 算术已改为完整 64 位
（D-v5-1），比较仍忽略高 16 位——因为它是 `.uo`（无符号、地址型）。
*结论：低 48 位无符号比较（规范字面解读）。*

### D-v5-5 · orrr 移位/扩展位移量取 `rdhd[5:0]`；`> N` → ILLI（动态检查）
合约 §3.4 要求位移量不超过位宽（`N` = 7/15/31/63），但 `orrr` 的位移量在
寄存器里，只能动态检查：golden 取 `rdhd & 0x3F`，超过 `N` 则报 ILLI。
`orri` 形式（`immu6`）在 `check_legality` 中静态检查。没有任何向量探测
非零位移量的 orrr 情形（全是小数值），故为规范字面解读。
*结论：`rdhd[5:0]` + 动态越界检查。*

### D-v5-6 · `br.z/nz-rb` 检测 RB 完整 64 位是否为零
合约 §5.2.3 只写"判零"，不限定位宽；与 `cmp.uo-rb`（D-v5-4）不同，这里没有
`.uo`/地址型暗示，且 RB 值已是完整 64 位量（D-v5-1）。向量只探测 0/1。
*结论：完整 64 位 `== 0`（规范字面解读）。*

### D-v5-7 · 定宽写回规则：算术/除法/比较全覆盖，逻辑/移位/扩展 RMW
合约 §3.1.2/§3.1.5/§3.2.2 产生完整 64 位结果（符号/零扩展，比较为 −1/0/1），
**覆盖**目标寄存器；§3.3/§3.4 只计算低 `bits` 位，**保留**目标寄存器的高位
（读-改-写，取指令执行前目标寄存器的旧值）。*结论：照规范执行；golden 对
RMW 类先读 `old_dst` 再写。*

### D-v5-8 · 多个 ld/st：快照下标、精确预检、递增提交
合约 §4.1.2（与 0.4.1 相同）：`idx = rdhc[47:0]` 只快照一次（不受目标与
`rdhc` 重叠影响），**所有**元素 EA 先做对齐预检，全部通过后才有任何写
（精确 MALIGN——无部分更新），元素按递增 `i` 提交。
*结论：快照 + 全部预检 + 递增 i。*

### D-v5-9 · EA 取 `rb[47:0]`，结果截到 48 位
`ea = (rb[47:0] + imm/idx) mod 2^48`。注意它与 0.4.1 的
`(完整rb + imm) & MASK48` 在数学上恒等——模加法使"先截断"不可观测。
*结论：显式低 48 位形式（合约 §4.1.1）。*

### D-v5-10 · `rela` 保留 `rbha[63:48]`，基址为当前指令所在页
合约 §4.7：`base = (rb0)&~0xFFF`，其中 v5 的 `rb0` = 当前地址，加上
`(imms18<<12)` 后截到 48 位；目标寄存器的高 16 位保留旧值（与 0.4.1 的保留
形态相同，仅换了基址）。*结论：照规范执行。*

### D-v5-11 · `ret` 以 `rd0` 为目标合法，静默丢弃
合约 §5.5（与 0.4.1 相同）：`ret` 把 `imms18` 写到 `rdha`，`rdha == rd0`
合法——写操作被静默丢弃。golden 经 `rd_write` 处理，它对 `rd0` 本来就是
no-op。*结论：合法丢弃。*

### D-v5-12 · RAS 精确：异常不留任何 RA 副作用
合约 §5.6/§9.2：RASOF/RASUF 是精确异常。golden 把所有 RAS 检查排在修改
之前（MemRAS 计数上溢/下溢、非法表项检查都在任何 RA 或内存写之前执行），
且 `run()` 在任何异常时额外丢弃工作副本。
*结论：先检查后修改 + 工作副本丢弃。*

### D-v5-13 · `fence` 的 SBZ bits[17:4] 非零 → ILLI，否则 NOP
合约 §7.3：低 4 位为屏障类型；bits[17:4] SBZ（"应为零"，非零保留）。
ADR-0004 D5.3 把 SBZ 违例绑定到 ILLI。作为单步 golden，没有内存序模型，
`fence` 无进一步效果。*结论：SBZ 检查后 NOP。*

### D-v5-14 · `swym N` 对一切 N 均为 NOP（时延不建模）
合约 §7.1：`swym 0` 为 nop，`swym N` 为硬件延时提示。时延对架构级 golden
不可观测。*结论：一切 N 均为 NOP。*

### D-v5-15 · M1 排除的编码（RF/cfx/LR-SC）→ ILLI，而非 UNDI
这些编码是*已定义*的（能命中 `opcodes.yaml` 中带 `excluded_m1` 标记的记录），
所以 UNDI（保留编码，§2.9）是错的；ADR-0004 D5.1 把执行 M1 排除指令绑定到
ILLI。*结论：译码成功，执行 → ILLI。*

### D-v5-16 · 入口 PC 先做 IALIGN 预检
合约 §2.1：指令 4 字节对齐。`run()` 在译码前检查 `pc & 0x3`，违例返回
`IALIGN`，不碰任何状态。（尚无向量探测此项；测试机 planted 的 PC 恒对齐。）
*结论：译码前检查。*

---

## §3 Golden/验证器结构与验证报告

### §3.1 结构（沿用 0628 模式，按 v5 适配）

```
tools/golden/
  dadao_interp_v5.py    golden：译码 ← opcodes.yaml；语义 ← contract-isa
  validate_interp_v5.py 向量运行器：PASS / FAIL / SKIP-deferred / SKIP-machine
  DESIGN.md             本文件（对比 + 决策 + 验证报告）
  README.md             快速上手
```

`dadao_interp_v5.py` 导出 `decode(word)`、`check_legality(rec, fields)`、
`run(word, input_state, pc, state)`。关键结构点：

- **译码数据驱动**：掩码/值 + 字段位域在 import 时来自 `contracts/opcodes.yaml`；
  拆分立即数（`imms12_hi/lo`、`imms24_b23_18` 等）按高位到低位重组并符号扩展。
- **静态/动态分离**：`check_legality` 只看指令字（寄存器号、`immu6`、`fence`
  SBZ）；动态检查（除零、`orrr` 位移量/扩展位、MALIGN、RASOF/RASUF）在 `_exec` 中。
- **精确异常**：`_exec` 在深拷贝上运行；任何 `Fault` 都丢弃副本，调用者看到的
  永远是执行前状态（§9.2）。
- **内存是稀疏字节表**，多字节大端访问（合约 §1.6）；`mem_width_for` 按助记符
  解出访问位宽，使输入内存按 schema 合约 planted（见 §3.2）。

### §3.2 验证器遵守的向量合约（`tests/vectors/schema.md`）

- **内存值合约**：`input_state`/`expected_state` 中内存条目的 `value` 是地址处
  *N 字节*大端值，N = 该向量的访问位宽（b→1、w→2、t→4、o→8；多个访问每个元素
  一条）。验证器先从指令解出位宽，再 planted/比较内存。
- **`expected_pc` = 退役时刻的下一 PC**（`pc_next`，即分支后的 `rb0`），只与
  `st.pc_next` 比较，绝不用公式重新推导。
- **`encoding` 类向量只做译码**：比较 golden 的"译码 + 静态合法性"结果与向量的
  `expected_fault`；绝不执行（执行会在零状态寄存器上凭空制造向量本意的动态
  异常，例如除零）。
- **`UNMAPPED` → `SKIP-machine`**：地址映射结果属于测试机层（ADR-0004 D5.6），
  不属于 ISA；golden 弃权，与 0628 验证器对 harness 专有结果弃权完全一致。
- **`deferred` → `SKIP-deferred`**：规范尚未提取；不是 golden 的裁决。

### §3.3 验证报告（2026-09-28）

`python3 validate_interp_v5.py` 全量运行 `tests/vectors/isa/*.yaml`：

```
TOTAL 747: PASS=696 FAIL=0 SKIP-deferred=8 SKIP-machine=43
```

分文件：每个文件 0 FAIL（ctrl-br 30/0/10、ctrl-call 8/0/1、ctrl-jump 4/0/2、
ctrl-ret 2/0/0、mem-ra 18/0/4、mem-rb 20/0/4、mem-rd 104/0/22、misc 3/0/3、
reg-arith 187/0/0、reg-compare 33/0/0、reg-cond-assign 15/0/5、reg-imm-block
46/0/0、reg-logic 64/0/0、reg-shift-extend 160/0/0、reserved 2/0/0）。

- 8 个 `SKIP-deferred` 是 `misc.yaml` 的 RF 向量 + `reg-cond-assign.yaml` 的
  overlap 向量，等规范提取——本来也不在 M1 范围内。
- 43 个 `SKIP-machine` 是期望 `UNMAPPED` 的 legality/boundary 向量（控制流目标
  越界 + 内存映射探针）。
- **首次全量运行即零 FAIL**：全部 696 条可裁决向量与 golden 一致，包括所有
  legality/overlap 异常向量、所有分支/调用/返回/RAS 向量、所有多个 ld/st
  向量，以及 `reserved.yaml` 的两条 UNDI 向量。

### §3.4 已知边界（不是缺口——是刻意划定的范围边）

1. 对于有歧义的位宽，向量只探测了**小数值**（D-v5-1…D-v5-6 已注明向量沉默之处）；
   未来与 QEMU 的差分测试将是这些解读的第一次完整 64 位交叉检验。
2. 尚无非零 `ra0`（MemRAS 激活）向量——`_ras_push/_ras_pop` 的溢出/回填路径已实现
   但无向量覆盖；它们是合约 §5.6.1/§5.6.2 的逐字转写。
3. 尚无 `IALIGN` / `branch_behavior` 向量；IALIGN 已按 D-v5-16 实现，未被探测。
4. `fence` 的序效果与 `swym` 的时延对单步 golden 在构造上就不可观测
   （D-v5-13/D-v5-14）。
