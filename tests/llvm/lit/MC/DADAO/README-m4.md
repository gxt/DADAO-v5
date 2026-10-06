# M4 L1 MC 向量（`tests/llvm/lit/MC/DADAO/`）— 对照表

> 任务：`TESTCASES-029t`（L1 向量 + 独立 oracle，**暂不接入门控**）。
> 规范：`spec/Process-05-里程碑TDD规范.md §2`（L1 期望值来自 ISA 编码表）、
> `§4`（期望值独立派生）、`§5`（反例门控）、`§6`（落点）。
> 权威源：`spec/Toolchain-01-汇编语言.md §6–§10`、`.tao/knowledge/contract-asm.md
> §6–§10`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-elf.md §1.1/§2.2`。

## 门控时序（用户裁定 2026-10-06；INTEG-016t 接入）

本任务**只产出向量 + 独立 oracle**，产出时**暂不接入** `make check`/`make check-lit`/
`make test-elf`，每个 `m4-*.s` 向量首行带

```
; UNSUPPORTED: true
```

使 `llvm-lit` 将其记为 **unsupported**（不阻断、也不误报 PASS）。用户原话：
「向量+独立 oracle，暂不接入门控（推荐）」。

**`INTEG-016t` 已移除全部 `m4-*.s` 的标记并接入 `make check-lit`**（`m4-*` 与既有
`LLVM-051t`~`054t` 实现向量并存、同目录运行）。其中 4 个向量（`m4-pseudo-set.s`/
`m4-directive-dd.s`/`m4-option-mts.s`/`m4-roundtrip.s`）在移除标记时发现其 RUN 行
引用的 FileCheck 前缀缺少对应 check 行，已补齐（内容与各向量 `@exp`/`@dir`/`@mts`/
`@norm` 的独立派生期望一致；见 `INTEG-016t` 完成区「越界披露」）。

## 向量 ↔ 能力 ↔ 期望值来源

| 向量文件 | 类别 | 能力 | 期望值来源（独立派生） |
|---|---|---|---|
| `m4-pseudo-set.s` | pseudo | `set.rd`/`set.rb`/`set.ft`/`set.fo` 的 imm/reg 展开 | `spec/Toolchain-01 §6.1`（展开规则）+ `contracts/opcodes.yaml`（各真实指令编码身份） |
| `m4-pseudo-removed.s` | pseudo | 被删伪指令 `nop`/`return`/`not.*`/`neg.*` → `unrecognized` | `spec/Toolchain-01 §6.2`（删除集）+ `contracts/opcodes.yaml`（不在表中） |
| `m4-directive-dd.s` | directive | `.dd.b08/w16/t32/o64` 宽度/大端、表达式、符号 | `spec/Toolchain-01 §7` + `contract-elf §1.1`（大端）+ `contract-elf §2.2`（`ABS48`） |
| `m4-directive-reject.s` | directive | GAS `.word`/`.octa` 拒绝、超宽、窄字段重定位拒绝 | `spec/Toolchain-01 §7/§9` |
| `m4-option-mts.s` | option | `-multiple-to-single` 开/关对照（助记符不变、单寄存器序列） | `spec/Toolchain-01 §8` + `§4.2` + `contracts/opcodes.yaml`（默认形态编码） |
| `m4-diagnostic.s` | diagnostic | 越界立即数、`%4!=0`、`ret rd0, 非0`、`#` 非法 | `spec/Toolchain-01 §9/§2.4/§2.2` + `contracts/opcodes.yaml`（字段位宽/legality） |
| `m4-roundtrip.s` | roundtrip | 汇编↔反汇编；等价书写规范化 | `spec/Toolchain-01 §10` + `contracts/opcodes.yaml` |
| `m4-not-neg.s` | roundtrip | `not`/`neg` 功能的**底层真实指令**：`not`→`xnor.o rd, rc, rd0`（仅 64 位）、`neg`→`sub.sb/sw/st rd, rd0, rc`（8/16/32 位）与 `sub.so {rd0, rd}, rd0, rc`（64 位）的编码/往返 | `contracts/opcodes.yaml`（`xnor.o_orrr_rd`=0x402C0000 / `sub.sb_orrr_rd`=0x43A40000 / `sub.sw_orrr_rd`=0x42A40000 / `sub.st_orrr_rd`=0x41A40000 / `sub.so_rrrr_rd`=0x53000000）+ `contract-isa §6.3/§6.6/§10.6/§11.6/§12.6`（`ADR-0013 D11`） |

> `not` 仅 64 位：窄位宽逻辑指令 `xnor.b/w/t` 已随 `SPEC-069t` 删除，`not.b/w/t`
> **无**等宽底层指令（本向量**不**测试已删助记符；其「unrecognized」反例见
> `TESTCASES-029t` 的 `m4-pseudo-removed.s`）。`neg` 的 `sub.sb/sw/st` 结果
> **符号扩展**、`sub.so` 为**双目的**（`rdha:rdhb = rdhc − rdhd`），期望编码均按
> 字段位域独立派生（见下）。

## 与既有实现向量的关系

`LLVM-051t`~`054t` 落地时已各自附带**已接入门控**的向量（`set-rd-imm.s`、
`dd-width.s`、`multiple-to-single-*.s`、`imm-range.s` 等）。本任务的
`m4-*.s` 是 **testcases 模块** 的 L1 向量集：内联期望（`; @<kind> …`）可由
独立 oracle **从 `contracts/opcodes.yaml` + `spec/` 重算**，是「一能力一向量」
的少量可审计集合；`INTEG-016t` 起两者**同目录并行**进 `make check-lit`。

## 内联期望注解格式

每个向量的**输入**是代码部分，**期望值**是同行末尾 `; @<kind> <expect>` 注释：

| kind | 含义 | 独立派生 |
|---|---|---|
| `enc` | 单条真实指令 → 4 字节大端 hex | `opcodes.yaml` `value`/`fields` 位域 |
| `exp` | 伪指令 → 展开指令序列（` ; ` 分隔） | `spec §6.1` 展开规则 |
| `dir` | 数据指导符常量/表达式 → 大端字节（符号 → `ABS48`/`reject:reloc-narrow`） | `spec §7` 宽度 + 大端 |
| `dirrej` | 指导符拒绝（`unknown`/`unsupported`/`range`/`reloc-narrow`） | `spec §7` |
| `rej` | 被删伪指令 → `unrecognized` | `spec §6.2` |
| `err` | 诊断 token（`imms18`/`immu12`/`align4`/`rd0-nonzero`/`illegal-token`） | `opcodes.yaml` 字段位宽/legality + `spec §9` |
| `mts` | `-multiple-to-single` 展开序列 | `spec §8` + `§4.2` |
| `norm` | 两种等价书写 → 必须同编码（往返规范化） | `opcodes.yaml`（两次派生相等） |

`; OBJ: {{[0-9a-f]+:}} <b0> <b1> <b2> <b3>{{.*}}<mnemonic>{{.*}}<operands>` 是 lit
的**对象字节 FileCheck 模式**（`m4-not-neg.s` 用于编码向量；由 `llvm-objdump -d`
比对）。该 4 字节由 `validate_mc_vectors.py` 与 `tools/llvm/check_lit_bytes.py`
**各自独立从 `contracts/opcodes.yaml` 派生**；`validate_mc_vectors.py` 另要求
`; OBJ:` 字节与同一指令的 `@enc` 独立派生值相等（改任一即失败）。

## 反例门控（可失败性）

`tools/testcases/validate_mc_vectors.py` 可对以下注入**失败**（见
`.work/evidence/TESTCASES-029t/run.sh` 自检与 `.work/log/testcases/`）：

1. 改一条 `@enc`/`@exp` 期望值 → `FAIL`；
2. 改一条向量的代码操作数 → `FAIL`；
3. 少一类 `@category` 覆盖 → `FAIL`；
4. 改一条 `; OBJ:` 期望字节 → `FAIL`（与 `@enc` 独立派生值不一致）；
5. 向量缺失 / 源文件被删 → `FAIL`（schema/覆盖）。

> `INTEG-016t` 接入门控后，`validate_mc_vectors.py` 不再要求首行门控占位标记
> （原 TESTCASES-029t 的「删标记 → FAIL」自检随之退役）；上列其余可失败性保留。
