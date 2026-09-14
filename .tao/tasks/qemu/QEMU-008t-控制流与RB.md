# QEMU-008t: 控制流 + RB 指令

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-007t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-007t` 产出的 `translate.c`（RD 语义与 load/store 已实现）
  - `.tao/knowledge/contract-isa.md` §1.3.2/§1.3.4（rb0=PC、ra0–ra63 RegRAS）、§4.2/§4.5/§4.7/§4.8/§4.9/§4.10/§4.11（RB 存取/块赋值/立即数/算术/自增/比较/PC 相对）、§5（控制流：条件跳转/无条件跳转/函数调用/返回/压弹栈流程）
  - `.tao/knowledge/adr-0004-test-machine.md`（fault/exit 可观测、RASOF/RASUF）
  - `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`
  - `tests/vectors/isa/control-flow.yaml`、`tests/vectors/isa/rb-ops.yaml`（TDD 向量，先于实现）
- 输出：`components/qemu/patches/0005-dadao-ctrl-flow.patch`、`components/qemu/patches/series`、控制流/RB 向量补充
- 约束：
  - **TDD：先写/补向量，再写 `trans_*` 实现**（两个独立 commit）
  - branch/jump/call 地址公式以 §5 为准（`PC = rb0 + (imm << 2)`，48 位、不溢出）
  - RegRAS 按 §5.3/§5.4 完整实现（引用计数、移位压栈/弹栈、RASOF/RASUF）
  - RB 目的为 rb0 → ILLI（branch/call/ret 明确写 PC 者除外）
  - RB 算术为**全 64 位**运算（bits[63:48] 为结果，不截断）
  - 完成后不自行 commit

## 背景（完整）

### 目标

实现控制流（条件跳转、jump、call、ret、rela、swym）与 RB 指令（存取、块赋值、立即数、算术、自增、比较）的 TCG 语义，并按 TDD 先补向量。0628 对应任务 `DL-018a`（27 个 trans 函数）经评审 Accepted，但存在 RegRAS 简化（N1）与 branch rd0 未显式区分（N2）两处 M1 可接受简化。

### 设计理由

- TDD：向量先于实现提交，期望值手推自 §5 与 `opcodes.yaml`，不从实现反推。
- 控制流与 RB 同批：RB 指令（`ld.o-rb`/`st.o-rb`/`rd2rb` 等）与控制流同属「非 RD 整数」的标量核心，且 `call`/`ret` 依赖 RegRAS。
- RegRAS 完整性：0628 简化为 `ra[63]` 单槽，M1 调用深度 < 63 时可工作；v5 应按 §5.3/§5.4 实现完整引用计数与移位，避免后续返工。

### 关键概念 / 数据

**控制流（§5）**：
| 助记符 | 格式 | 语义 |
|--------|------|------|
| `br.eq`/`br.ne` | rrii | `if (rdha ==/!= rdhb) PC = rb0 + (imms12 << 2)` |
| `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np` | riii | 单寄存器条件跳转，`PC = rb0 + (imms18 << 2)` |
| `br.z-rb`/`br.nz-rb` | riii | RB 条件跳转 |
| `jump-iiii` | iiii | `PC = rb0 + (imms24 << 2)` |
| `jump-rrii` | rrii | `PC = rbha + rdhb + (imms12 << 2)`（48 位） |
| `call-iiii` | iiii | 计算返回地址压入 ra63，`PC = rb0 + (imms24 << 2)` |
| `call-rrii` | rrii | 同上，`PC = rbha + rdhb + (imms12 << 2)` |
| `ret` | riii | `rdha = sign_extend(imms18)`，`PC = ra63 低 48 位`，弹栈 |
| `rela.si` | riii | `rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)`，高 16 位保持 |
| `swym` | iiii | NOP（`swym 0`） |

- 条件判断按附录 B.1（N/NN/Z/NZ/P/NP/EQ/NE）；`br.z`/`br.nz` 的 rd0 特例见 §5.1.2。
- **RegRAS**：ra1–ra63 构成栈，ra63 为栈顶，高 16 位为引用计数；压栈/弹栈流程见 §5.3.3/§5.4.1，含首次压栈、递归递增、移位压栈、MemRAS、RASOF/RASUF。
- `call` 返回地址：按 §5.3 压入 ra63（引用计数 + 返回地址），具体地址公式以 §5 与向量为准。

**RB 指令（§4）**：
| 助记符 | 格式 | 语义 |
|--------|------|------|
| `ld.o-rb`/`st.o-rb` | rrii | `rbha = mem64[rbhb+imms12]` / `mem64[...] = rbha` |
| `ldm.o-rb`/`stm.o-rb` | rrri | RB 多寄存器存取（`QEMU-010t` 补 `ldm.o-rb`） |
| `rb2rd`/`rd2rb`/`rb2rb`/`ra2rd`/`rd2ra` | orri | 寄存器组块复制 |
| `set.zw-rb`/`or.w-rb`/`andn.w-rb` | rwii | RB 立即数设置（无 `set.ow-rb`） |
| `add.so-rb`/`sub.so-rb` | orrr | RB 加减，**全 64 位** |
| `add.si-rb` | riii | `rbha += sign_extend(imms18)`，全 64 位 |
| `cmp.uo-rb` | orrr | 无符号 64 位比较，结果写 RD |

**ILLI**：RB 目的为 rb0 → ILLI；块赋值 `immu6 == 0`/起始+immu6>64 → ILLI；RB 存取对齐 8B、未对齐 → MALIGN；`immu6 == 0`/`rbha+immu6>64` → ILLI。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-018a-qemu-ctrl-flow.md`（完整转述：TDD 原则、指令范围、向量补充、trans 实现、lit 测试、约束、完成区与两轮 Architecture Review，含 N1/N2）。
- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（call/ret 语义与返回地址修正，v5 对应 `QEMU-012t` 的一部分）。
- DADAO-0628：`code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（控制流向量 TDD 设计，v5 对应 `TESTCASES-008t`）。

## 交付物

- 控制流/RB 向量补充（`tests/vectors/isa/control-flow.yaml`、`rb-ops.yaml`，commit A，先于实现）。
- `components/qemu/patches/0005-dadao-ctrl-flow.patch`（commit B）：`target/dadao/translate.c` 中控制流与 RB `trans_*`。
- `components/qemu/patches/series`：加入 `0005`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn/brnn/brz/brnz/brp/brnp/breq/brne` → `br.n/br.nn/br.z/br.nz/br.p/br.np/br.eq/br.ne`；新增 `br.z-rb`/`br.nz-rb`；`unimp`→`illi`；`setzw`→`set.zw`；`sto`→`st.o`；`ldo`→`ld.o`。
2. **地址公式**：v5 §5 为 `PC = rb0 + (imm << 2)`；0628 经验取「PC+4 基准」（`pc_next+4`），v5 须以 §5 与 `TESTCASES-008t` 向量为准，不照抄 0628 公式（详见 `QEMU-012t`）。
3. **RB 全 64 位**：0628 对 RB 运算结果 `& 0x0000FFFFFFFFFFFF`；v5 的 `add.so-rb`/`sub.so-rb`/`add.si-rb` 为全 64 位，bits[63:48] 为运算结果，**不得截断**。
4. **RegRAS 完整性**：0628 N1 仅用 `ra[63]` 单槽；v5 按 §5.3/§5.4 实现引用计数与移位压弹栈、RASOF/RASUF。
5. **rela 语义**：v5 `rela.si rbha, imms18` 为 `(PC & ~0xFFF) + (imms18<<12)`，高 16 位保持；0628 的 rela 公式不同（见 `QEMU-009t`）。
6. **不复制补丁正文**：0628 `0006-dadao-ctrl-flow.patch` 属 0.4.1。

## 已知坑 / 结论

摘自 0628 `DL-018a` 完成区与两轮 Architecture Review：

1. **RegRAS 简化（N1）**：0628 未实现引用计数/移位/RASOF/RASUF；v5 须完整实现，否则递归/深调用行为错误。
2. **branch rd0 源（N2）**：`br.z rd0` 必真、`br.nz rd0` 必假（§5.1.2），合法行为不触发 ILLI；须显式覆盖。
3. **TDD 顺序**：向量 commit 必须早于 trans 实现 commit，`git log` 可见两个独立 commit。
4. **`encoding.word` 手推**：不从 QEMU/LLVM 输出复制。
5. **分支 target 的 PC 基准**：not-taken 必须推进到下一指令（否则重复执行）；taken 公式以 §5 为准。
6. **RB 48 位掩码**：0628 的 `& 0x0000FFFFFFFFFFFF` 是 0.4.1 语义，v5 不可照搬（见差异 3）。
7. **rela 基址**：初版误用 `rb[ha]` 作基址（见 `QEMU-009t`），实现时须直接以 `rb[0]`（PC）为基址。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-018a-qemu-ctrl-flow.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`
- 本项目：`.tao/knowledge/contract-isa.md` §1.3、§4.2–§4.11、§5、附录 B；`contracts/opcodes.yaml`；`.tao/knowledge/adr-0004-test-machine.md`
- 本项目：`.tao/tasks/testcases/TESTCASES-008t-控制流向量TDD.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 控制流/RB 向量补充 commit 早于 `trans_*` 实现 commit（`git log` 证据）
2. `components/qemu/patches/0005-dadao-ctrl-flow.patch` 存在且干净 apply；`series` 已加入
3. 控制流全部指令（含 `br.*-rb`、`jump`/`call` 两形式、`ret`、`rela`、`swym`）实现；RegRAS 按 §5.3/§5.4 完整
4. RB 指令全部实现；RB 算术为全 64 位（无 48 位截断）；rb0 目的 ILLI
5. 分支地址公式与 §5 及 `TESTCASES-008t` 向量一致；not-taken 推进到下一指令
6. `make build-qemu` PASS；控制流/RB 向量经「MC 汇编 → QEMU 执行 → 结果比对」与 oracle 一致（若 harness 未就绪，记录依赖并保留可复现命令）
7. 完成区含真实构建/运行输出；未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
