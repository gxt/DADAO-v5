# ADR-0009: QEMU Harness Methodology

**状态**：Accepted（用户确认 2026-09-19；头行于 2026-09-22 订正——原误留 `Candidate`，各 decision 小节自始为 `Accepted`）
**日期**：2026-09-19
**关联**：ADR-0004（Test Machine）、QEMU-014t（harness 实现）

## Context

M1 的 QEMU 语义测试需要一个 harness 来构建测试二进制、运行 QEMU、并报告 PASS/FAIL。harness 必须满足：

1. **独立于 LLVM**：QEMU 测试路径与 LLVM 路径完全独立
2. **零 host 依赖**：pass/fail 判定只依赖 `$?`，不依赖日志/stderr/超时
3. **可诊断**：FAIL 时能导出 guest 寄存器状态
4. **可扩展**：支持 semantic/encoding/legality/boundary/overlap 等多种向量类型

## Decision

### D1 raw-encoding

测试 binary 全部由 `struct.pack('>I', word)` 直接生成，不依赖 `llvm-mc`。

**理由**：QEMU 测试路径必须与 LLVM 路径完全独立，否则单一实现 bug 会穿透。直接用向量里的 raw encoding word 构 binary，绕开汇编器。

**状态**：Accepted（用户确认 2026-09-19）

### D2 guest 内比较为主

`emit_state_compare()` 在 guest 内用 XOR+ORR 累加器比较实际值与嵌入 guest 的期望值，结果映射退出码（`0`=PASS/`1`=FAIL）。**pass/fail 判定只依赖 `$?`**（ADR-0004 D3 零 host 依赖）。state-dump（dumper 段）**保留但仅作 FAIL 时的诊断**，host 不参与判定。

**理由**：host 不参与判定，满足零 host 依赖约束。state-dump 仅用于 FAIL 时的诊断，不参与 pass/fail 判定。

**状态**：Accepted（用户确认 2026-09-19）

### D3 ROM trampoline 布局

`-bios` 加载 ROM trampoline → 设栈（`rb1=0xffff_00ff_0000`）→ 用 `jump rbX, rd0, 0` 绝对跳转到 `BINARY_BASE=0xffff_0000_0000`。

**注意**：`jump imms24` 是相对跳转（`Addr=rb0+(imms24<<2)`），ROM→RAM 跨距约 `-4G` 超出其范围，不可用；`jump rbha, rdhb, imms12` 为 48 位绝对地址，可用（contract-isa §5.3）。

**状态**：Accepted（用户确认 2026-09-19）

### D4 保留寄存器约定

- RD scratch = `rd60`–`rd63`
- RB scratch = `rb60`–`rb63`
- **RA 不作 scratch**（`ra1`–`ra63` 全被 RA 向量占用，`ra0` 为当前 RA）
- `rb0`/`rb1`/`rb2` 按 ADR-0004 D6.5 保留

该范围写入 README 并作为向量 convention。

**状态**：Accepted（用户确认 2026-09-19）

### D5 退出码协议对齐 ADR-0004

- `0x00` = PASS
- `0x01`–`0x7F` = FAIL（细分码见 QEMU-015t）
- `0x80`–`0xFF` = 机器 fault

判定只看 `$?`。

**状态**：Accepted（用户确认 2026-09-19）

### D6 `expected_pc`·`expected_state.ra`·`encoding.reserved` 的消费契约

harness 消费 `tests/vectors/isa/*.yaml` 中以下字段：

- `expected_pc`：分支/跳转/调用/返回指令 retire 后 `rb0` 的期望值（48-bit hex），由 `QEMU-017t`/`018t` 的 poison pattern 消费——不直接比对 `rb0`，而是用 taken/not-taken 的 poison `illi` 路径间接断言 PC 落点。
- `expected_state.ra`：RA 寄存器执行后期望值，由 `QEMU-018t` 的 call/ret 组合 pattern 消费——通过 `call→ret→landing` 完整往返隐式验证 RA 压栈/弹栈正确性；必要时用 `ra2rd` 导出 RA 到 RD 后做 XOR 比对。
- `encoding.reserved: true`：保留编码 case（`class: legality`、`expected_fault: UNDI`）无 `(insn, format)` 身份，harness 解析向量时须跳过 identity/mask-value 校验，`expected_fault` 恒 `UNDI`；详见 `QEMU-015t`。

**补注（2026-09-21，用户确认）——`expected_pc` 按「相对 `BINARY_BASE` 的位移（delta）」消费**：

- `expected_pc` 的**绝对值不作比对**（与本 D6 首条「不直接比对 `rb0`」一致）。令 `delta = expected_pc - BINARY_BASE`（`BINARY_BASE = 0xFFFF_0000_0000`）：
  - `delta == 8`（2 words）→ **taken** → 用 taken poison pattern
  - `delta == 4`（1 word）→ **not-taken** → 用 not-taken poison pattern
- **理由**：harness 前置 **loader**（`input_state` 非空时 1–4 words），测试指令实际地址 = `BINARY_BASE + loader_words*4` ≠ `BINARY_BASE`。实测 `ctrl-br[1]`（`br.n` taken）loader=4 words → 测试指令在 `0xffff00000010`，而向量 `expected_pc = 0xFFFF00000008` → 绝对比对必然错。
- **配套语义**：v5 分支/跳转基址 = **分支指令自身地址**（`Addr = rb0 + (imm<<2)`；`translate.c` 的 `pc_next += 4` 发生在 `decode_insn` **之后**）。故 poison pattern 的 not-taken 偏移为 **`+2`**（0628 的 `pc_next` 基准下为 `+1`，**不得沿用**）。
- **影响**：`QEMU-017t`（`ctrl-br`/`ctrl-jump`）与 `QEMU-018t`（`ctrl-call`/`ctrl-ret`）的 `build_branch_test_binary()` 按本补注实现；向量数据**无需修改**。

**补注续（2026-09-21，用户确认）——`expected_state.ra` 同构重定位**：

- `expected_state.ra` 的**低 48 位**须加 `loader_bytes`（= 测试指令实际地址 − `BINARY_BASE`）后再与实测比对；**高 16 位 count 不变**。`loader_bytes == 0` 时退化为原值。
- **理由同上**：向量按 test@`BINARY_BASE` 填 RA 值；harness 前置 loader 使 test 实际地址 ≠ `BINARY_BASE`。RA 语义为 `ra63 = <count:16><返回地址:48>`，返回地址 = **call 自身地址 + 4**（`trans_ctrl.c.inc` 的 `pc_next + 4`），故实测 RA 随 test 地址平移。
- **实测证据**：`ctrl-call[2]`/`[6]`（loader=4w，test@`0xFFFF00000010`）向量写 `<2>…0004`、实测 `<2>…0014` → FAIL；`ctrl-call[1]`/`[5]`（loader=0）→ PASS。
- **`ret` 的往返验证**：`ret` 无独立语义测试（依赖 RA 栈有值）。`QEMU-018t` 由 harness **合成** `call→ret→landing` 往返（`[call imm=2][landing=exit 段][ret]`），ret 用例**不加载 `input_state.ra`**（ra63 由合成 call 真实压栈）⇒ `loader_bytes == 0` ⇒ 无需重定位。

**补注续二（2026-09-21，用户确认）——`input_state.memory` 的写入契约**：

- `tests/vectors/isa/*.yaml` 的 `input_state.memory[].value` 表示「**`address` 处存放的 N 字节值**」，N = 被测向量的**访存宽度**（由 mnemonic 推导：`b`→1、`w`→2、`t`→4、`o`→8；`stm.*`/`ldm.*` 按元素宽度）。
- harness 的 loader **须以宽度 N 的 store**（`st.b`/`st.w`/`st.t`/`st.o`）把 `value` 的低 N 字节写到 `address`；**不得**无条件用 `st.o`（8 字节）。
- **理由**：DADAO 为大端；把 `value=0x42` 作为 8 字节值写到 A 会得到字节序列 `00 00 00 00 00 00 00 42`——`0x42` 落在 `A+7`，而窄 load 从 A 读得 `0x00`。真实大端机器（MIPS/SPARC/PowerPC）下类型化数据按**自然宽度**存放（`char` 占 1 字节）；`spec/DADAO-21-ABI §数据表示` 亦为「多字节数据最高有效字节在最低地址」，其「右对齐」仅适用于 **8 字节参数/varargs slot**，非通用内存。
- **对称性**：与本 ADR 中 `QEMU-016t` 引入的「按宽度**读**做 memory 比对」互为读写对称（同一 `derive_width_from_mnemonic()`）。
- **影响**：由 `QEMU-023t` 实现；**向量数据零改动**（使用 `input_state.memory` 的 48 条）。修复后 24 条窄 load 由 FAIL 转 PASS。

**状态**：Accepted（用户确认 2026-09-19）；D6 补注经用户确认 2026-09-21

### D7 state-dump 读取机制

正常运行不需要 dump（D2）。**诊断模式**（`--dump`）下 guest 在 dumper 段后**自旋**（`jump rb0, rd0, 0`，不写 exit port），host 用 QMP `human-monitor-command` 的 `pmemsave` 导出 state-dump region 到文件后终止 QEMU。

**依据**：`dadao-m1` 无串口/UART（serial-hex 不可行），且 exit port 写即 `qemu_system_shutdown_request_with_code` 使进程退出、RAM 消失（退出后读文件不可行）。

**状态**：Accepted（用户确认 2026-09-19）

## Binary Layout

```
BINARY_BASE = 0xffff_0000_0000

[section 1] loader
  - Load input_state rd registers (set.zw + or.w)
  - Load input_state rb registers (set.zw-rb + or.w-rb)
  - Load input_state ra registers (via rd2ra)
  - Write input_state memory (st.o)

[section 2] test
  - Raw encoding word (4 bytes)

[section 3] dumper
  - Dump rd[1..63] to DUMP_BASE + 0x008..+0x1F8 (rd[i] @ i*8)
  - Dump rb[1..63] to DUMP_BASE + 0x208..+0x3F8 (rb[i] @ 0x200+i*8)
  - Dump rb0 (PC) to DUMP_BASE + 0x0400 via rb2rd→st.o-rd (st.o-rb requires rbha!=rb0)
  - rd[0] slot @ +0x000 and rb[0] slot @ +0x200 are reserved (not written)

[section 4] exit
  - Semantic/boundary: compare expected vs actual, write PASS/FAIL
  - Encoding: write 0x00 (PASS)
  - Legality: safety-net FAIL (if fault doesn't happen)
```

## Register Conventions

| Register | Purpose | Notes |
|----------|---------|-------|
| `rd0` | Zero | Hardwired, read-only |
| `rd1`–`rd59` | Test registers | Used by test vectors |
| `rd60` | Temp | Load expected values |
| `rd61` | Accumulator | XOR+ORR comparison result |
| `rd62` | Exit code | Value to write to exit port |
| `rd63` | Dump temp | Used by dumper |
| `rb0` | PC | Hardwired, read-only |
| `rb1` | SP | Set by trampoline |
| `rb2` | RAM entry | Set by trampoline |
| `rb3`–`rb59` | Test registers | Used by test vectors |
| `rb60` | Exit port addr | 0xffff_8000_0000 |
| `rb61` | Memory temp | For memory input_state |
| `rb62` | Dump pointer | State-dump region base |
| `rb63` | (unused) | Reserved |
| `ra0`–`ra63` | Return address stack | Not used as scratch |

## State-Dump Region

Located at `0xffff_00fe_0000` (128 KiB below RAM top):

| Offset | Content | Size |
|--------|---------|------|
| `0x0000` | `rd[0]` slot (reserved, not written) | 8 bytes |
| `0x0008`–`0x01F8` | `rd[1..63]` (rd[i] @ i×8) | 504 bytes |
| `0x0200` | `rb[0]` slot (reserved, not written) | 8 bytes |
| `0x0208`–`0x03F8` | `rb[1..63]` (rb[i] @ 0x200+i×8) | 504 bytes |
| `0x0400` | `pc` (rb0 via rb2rd→st.o-rd) | 8 bytes |

Total: 1032 bytes (0x408).

## Fault Codes (ADR-0004 D5.8)

| Code | Fault | Description |
|------|-------|-------------|
| `0x87` | UNMAPPED | Access to unmapped memory |
| `0x88` | ILLI | Illegal instruction |
| `0x89` | UNDI | Undefined instruction |
| `0x8A` | RASOF | RAS overflow |
| `0x8B` | RASUF | RAS underflow |
| `0x8C` | MALIGN | Memory alignment error |
| `0x8D` | IALIGN | Instruction alignment error |

## Rationale

- **raw-encoding**：绕开汇编器，确保 QEMU 测试路径与 LLVM 路径完全独立
- **guest 内比较**：满足零 host 依赖约束，pass/fail 判定只依赖 `$?`
- **ROM trampoline**：利用绝对跳转跨越 ROM→RAM 地址差距
- **保留寄存器**：避免与测试向量冲突，明确 scratch 范围
- **state-dump 诊断**：FAIL 时可导出 guest 状态，但不参与 pass/fail 判定
- **QMP pmemsave**：`dadao-m1` 无 UART，exit port 写即退出（RAM 消失），只能在退出前通过 QMP dump

## Consequences

- harness 不依赖 LLVM，可独立构建和运行
- pass/fail 判定完全由 guest 内部逻辑决定，host 只检查 `$?`
- FAIL 时可通过 `--dump` 模式导出 guest 寄存器状态进行诊断
- 保留寄存器范围（rd60-63, rb60-63）必须写入 README 和向量 convention
- QEMU 必须实现 exit port 设备和 fault→退出码映射
