# ADR-0004: SimRISC M1 裸机测试机（Test Machine）

**状态**：Accepted（rev. 2026-09-13: D1 内存映射改为核内地址空间模型，见 `## 修订`）
**日期**：2026-09-13
**关联**：ADR-0001（greenfield 重建）、ADR-0003（object ABI / artifact pipeline，`SPEC-005t`）、任务 `SPEC-006t`、`.tao/knowledge/contract-isa.md`（SimRISC 0.5.3）、`.tao/knowledge/contract-abi.md`（AEE·ABI 0.9.2）、`verif/legality_rules.yaml`、`verif/opcodes.yaml`

## Context（背景）

M1 的 QEMU 实现必须在**裸机**（bare-metal）环境执行 ISA 语义/合法性/边界向量：无 OS、无 SEE、无异常向量。测试断言必须完全依赖 **QEMU 进程退出码**或 **guest 可见寄存器状态**，不得依赖 host 日志、QEMU stderr 或超时判定 pass/fail（零 host 依赖约束）。

`spec/`（SimRISC 0.5.3）只定义了部分 ISA 语义：`rb0` 复位值为 `cfx_power_hypv_excp_vector`（SEE 概念，M1 无 SEE）[SimRISC-00 §基址寄存器]、`rf0`（FCSR）位布局 [SimRISC-00 §浮点状态寄存器]、RA 进程入口初值 [SimRISC-00 §返回地址栈]、以及 MALIGN/ILLI/UNDI/IALIGN/RASOF/RASUF 的触发条件与精确异常承诺 [contract-isa §9]。`spec/` **不定义**测试机的内存映射、exit 协议、硬件复位值全集、fault 退出码或启动协议——这些属本 ADR 的**原始架构决策**，均标注「无 spec 依据，架构自定义」。

本 ADR 与 ADR-0003（object ABI / artifact pipeline）配合：ADR-0003 冻结 `.o → objcopy --only-section=.text -O binary → flat binary`，本 ADR 冻结该 flat binary 如何被 QEMU 加载并进入，以及 guest 可见的全部可观测行为。测试机地址图采用 spec 的**核内地址空间模型**（cfxcode），整体占用最高段 cfxcode 63（power）——见 D1。遗留 `dadao-virt` 内存布局（ROM `0x0010_0000` / UART `0x1000_0000` / RAM `0x8000_0000`）仅作**只读对照**，本 ADR 不沿用。

依赖 oracle：`.tao/knowledge/contract-isa.md`（0.5.3，异常/对齐/地址模型）、`.tao/knowledge/contract-abi.md`（`SP = rb1`、栈向下增长）、`verif/legality_rules.yaml`（异常触发条件）。指令助记符一律使用 0.5.3 命名。

## Decision（决策）

### D1 内存映射

M1 测试机（`dadao-m1`）地址图采用 spec 的**核内地址空间模型**（`spec/DADAO-12 §2.1`）：48 位核内地址的高 6 位 `bits[47:42]` 为核芯功能扩展编号（cfxcode）。M1 无 cfx、无 MMU，测试机整体占用**最高段 cfxcode 63（power）**的核内地址空间 `[0xFC00_0000_0000, 2^48)`——因为硬件复位向量 `cfx_power_hypv_excp_vector` 正位于该段。

| 区域 | 起始 | 结束 | 大小 | 属性 | 说明 |
|------|------|------|------|------|------|
| RAM | `0xffff_0000_0000` | `0xffff_00ff_ffff` | 16 MiB | 读写、可执行 | 测试程序、栈、数据 |
| Exit port | `0xffff_8000_0000` | `0xffff_8000_0007` | 8 B | MMIO，只写 | exit 协议（D3） |
| boot ROM | `0xffff_ffff_0000` | `0xffff_ffff_ffff` | 64 KiB | 只读、可执行 | 复位 trampoline、常量数据；= `cfx_power_hypv_excp_vector` |
| 其余全部地址 | — | — | — | unmapped | 访问 → 退出码 `0x87`（D5） |

- 所有区域地址均为 48-bit 核内有效地址：`bits[63:48] = 0`，高 16 位在地址计算时被硬件忽略 [contract-isa §1.5]。三个区域与 unmapped 判定均按有效地址低 48 位进行。
- **boot ROM 起址 `0xffff_ffff_0000` 即 spec 的 `cfx_power_hypv_excp_vector`**（cfxcode 63 / power，64 KiB）[DADAO-12 §2.1][DADAO-23 §3]。M1 **仅借用该复位地址**作为 boot ROM，**不复现** spec 的复位运行模式（`inner_run_mode=hypv`、`inner_cfx_code=cfx_power`、`inner_cfx_mask=全 1`）等 HBI/SEE 语义（M1 无 SEE/HBI/hypv）。
- RAM 与 Exit port 亦位于 cfxcode 63 段内（`bits[47:42]=63`）。`spec/` 的核内地址空间属 cfx 访问域，而 RAM 属 64-bit 物理地址空间；M1 无 MMU（VA=PA）、无 cfx，故测试机把这些地址统一作裸机地址使用——属**测试机约定**，非 spec 的 cfx 语义。
- boot ROM 64 KiB 足以容纳最小 trampoline（D6，实际约 5 条指令）；未使用 ROM 读为零（全零字若被执行即 `illi 0`，触发 ILLI，但 trampoline 会在越过有效代码前跳转离开，见 D6）。
- RAM 16 MiB 提供测试程序 + 栈 + scratch 空间；栈位于 RAM 高地址端、向下增长（`SP = rb1`）[contract-abi §2.1]。
- 所有区域边界均 8 B 对齐，因此**任何自然对齐的访问都不会跨越区域边界**（跨边界只可能发生在未对齐访问上，按 D4 归 MALIGN）。
- 「无 spec 依据，架构自定义」：RAM/Exit port 的具体地址、以及「测试机整体占用 cfxcode 63 段」均为测试机约定；`spec/` 只规定 cfxcode 63 的复位向量 `0xffff_ffff_0000`。

### D2 复位向量与入口点

#### D2.1 硬件复位值（power-on reset）

| 寄存器组 | 复位值 | 依据 |
|----------|--------|------|
| RD `rd0` | `0` | spec：`rd0` 硬连零、只读 [contract-isa §1.3.1] |
| RD `rd1`–`rd63` | `0` | 无 spec 依据，架构自定义（消除未初始化状态的非确定性） |
| RB `rb0` | `0xffff_ffff_0000`（ROM 基址 = `cfx_power_hypv_excp_vector`） | spec：`rb0` 复位初值 = `cfx_power_hypv_excp_vector` [SimRISC-00 §基址寄存器][DADAO-12 §2.1] |
| RB `rb0[63:48]` | `0` | spec：`rb0[63:48]` 恒为 0 [contract-isa §1.3.2] |
| RB `rb1`–`rb63` | `0` | 无 spec 依据，架构自定义 |
| RA `ra0`–`ra63` | `0`（`ra[63:48] = 0`，全部条目无效；`ra0=0` → 仅 RegRAS） | 架构自定义：RegRAS 在进程入口须全零 [contract-isa §1.3.4]；`ra0=0` 表示无 MemRAS，M1 调用深度 ≤ 63（RegRAS 容量）故无需 MemRAS |
| RF `rf0` | `0x7FF8_0000_7FC0_0000` | 位布局来自 spec [SimRISC-00 §浮点状态寄存器]；R/W 位复位为 0 属架构自定义 |
| RF `rf1`–`rf63` | `0` | 无 spec 依据，架构自定义 |

**复位 PC（`rb0`）**：M1 直接取 spec 的 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000` 作为复位值（即 boot ROM 基址，D1）[SimRISC-00 §基址寄存器][DADAO-12 §2.1]。M1 **仅借用该地址**，不复现 spec 的复位运行模式（`inner_run_mode=hypv`、`inner_cfx_code=cfx_power`、`inner_cfx_mask=全 1`）等 HBI/SEE 语义（M1 无 SEE/HBI/hypv）。

**`rf0` 复位常量推导**（从 0.5.3 `SimRISC-00 §浮点状态寄存器` 位布局**独立推导**，不照抄任何旧实现）：

| 位域 | 属性 | spec 规定值 | 复位取值 |
|------|------|------------|---------|
| `[63:51]` | 只读 | `0111 1111 1111 1`（13 位）= `0xFFF`，fo 格式 Quiet NaN（符号位 0，E 全 1，尾数最高位 1） | `0xFFF` |
| `[50:32]` | SBZ | 应为零 | `0` |
| `[31:22]` | 只读 | `0111 1111 11`（10 位）= `0x1FF`，ft 格式 Quiet NaN | `0x1FF` |
| `[21:18]` | SBZ | 应为零 | `0` |
| `[17:16]` | R/W | 舍入模式 | `0`（复位） |
| `[15:5]` | SBZ | 应为零 | `0` |
| `[4:0]` | R/W | 异常状态（NV/DZ/OF/UF/NX） | `0`（复位） |

组合：`rf0 = (0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_0000_0000 | 0x0000_0000_7FC0_0000 = 0x7FF8_0000_7FC0_0000`。
校验：`bits[62:52]` 全 1（fo 指数）、`bit51=1`（fo 尾数最高位）；`bits[30:23]` 全 1（ft 指数）、`bit22=1`（ft 尾数最高位）；其余为 0。

**RF 边界**：M1 **不实现任何 RF 指令语义**（RF 存取/运算、`set.w`、`set.ft`/`set.fo` 等）；执行 RF 编码指令按 D5 触发 **ILLI**。M1 只按上表**确定性复位** `rf0`/`rf1`–`rf63`，保证无浮点状态引发不确定行为。

#### D2.2 加载方法与入口

- **镜像格式：flat binary（不使用 ELF）**。测试程序以 flat binary 提供，QEMU 不做 ELF 解析、不读取 `e_entry`；入口固定为加载基址。与 ADR-0003 一致：`.o → objcopy --only-section=.text -O binary → flat binary`，无 LLD、无 `ET_EXEC`、无 `e_entry` 加载语义。
- **加载地址：RAM 基址 `0xffff_0000_0000`**。

#### D2.3 唯一启动协议（冻结）

采用**双镜像**：ROM trampoline blob 由 `-bios` 加载，测试 flat binary 由 `-kernel` 加载，**两者必须同时提供**。

- **唯一命令行**：`qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin`
- **ROM blob 布局**：flat binary，链接基址 `0xffff_ffff_0000`，trampoline 代码位于 blob 偏移 0；加载到 ROM 区域起点。blob 大小上限 64 KiB。
- **RAM entry**：`0xffff_0000_0000`（固定；trampoline 跳转目标，D6）。
- **oversize / error 行为**：ROM blob > 64 KiB、或 test binary > 16 MiB、或缺少 `-bios`/`-kernel` 时，QEMU 机器在**启动加载阶段报错并以非零状态退出**，不得静默截断、部分加载或继续执行。此类为**工具/加载错误**，与 guest fault（D4/D5）分属不同层，不参与 `$?` 的 guest 协议。
- 该协议是 M1 唯一可自动化启动路径；ADR-0003 冻结 flat binary 的生成，本 ADR 冻结其加载与入口。

### D3 Exit Port 协议

- **地址**：`0xffff_8000_0000`，区域 `[0xffff_8000_0000, 0xffff_8000_0007]`，8 B 对齐。
- **宽度**：**恰好 8 字节**，由一条 `st.o`（rrii，RD store，op `0x21`）写入，有效地址须为 `0xffff_8000_0000`。
- **编码**：

  | 写入值低字节 `bits[7:0]` | 含义 |
  |--------------------------|------|
  | `0x00` | PASS——测试成功 |
  | `0x01`–`0x7F` | FAIL——测试自定义错误码 |
  | `0x80`–`0xFF` | Reserved——测试程序**不得**写入（该段保留给机器产生的 fault 码，D5） |

  高 56 位（`bits[63:8]`）可用于编码测试编号/调试信息，harness **只检查低字节**。
- **QEMU 行为**（机制级冻结）：
  1. 检测到对 exit port 的 8 B 对齐 store，读出被写入的 8 B 值；
  2. 取低字节 `value & 0xFF` 作为 QEMU 进程退出状态；
  3. 以 clean shutdown 请求退出，并把该退出码传播到 host `$?`。
  实现使用**带退出码**的 API/设备机制（如 `qemu_system_shutdown_request_with_code(reason, code)` 或等价机制），**不使用**不携带退出码的 `qemu_system_shutdown_request()`。最终 API 以锁定的 QEMU baseline 为准（ADR-0002/组件锁）；Phase 3 bringup 必须增加**进程级验收测试**，对 guest 经 exit port 写入 `0x00`/`0x01`/`0x7F`/`0x87`/`0x88` 分别验证 host 观察到**完全相同**的 8-bit status。该 bringup 测试直接验证「读 8 B → 取低字节 → 传播到 `$?`」机制对**任意 8 位值**的忠实传播；它与下述「测试程序不得写 `0x80`–`0xFF`」的**约定**不冲突——约定用于保证常规测试的 `$?` 分区无歧义，bringup 测试在已知写入来源的前提下单独验证机制。
- **非 8B 访问**：对 exit port 的 `st.b`/`st.w`/`st.t`、多寄存器 store（`stm.*`）、以及任何 load（`ld.*`）→ **ILLI（`0x88`）**。理由：opcode 合法（非保留编码），违反的是 MMIO 区域的访问种类/宽度约束，属**非法操作数/非法访问**（ILLI），而非未识别编码（UNDI 仅用于 ISA 表空白单元格）。
- **零 host 依赖**：harness 运行 `qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin` 并检查 `$?`；`0x00` = pass，非零 = fail/fault。pass/fail 判定**只依赖 `$?`**，不做日志解析、不读 stderr。harness 另设**墙钟超时兜底**（默认 **9 s**，可经环境变量覆盖）：超时即杀掉 QEMU 并记为 **harness 错误（inconclusive）**，**不**参与 guest pass/fail 判定。该超时仅用于防止死循环/不终止的测试永久挂起 harness，不违反零 host 依赖原则。

### D4 MALIGN 可观测行为

MALIGN 为精确异常 [contract-isa §9.2][contract-isa §4.1.1]。M1 无 OS 异常向量，本 ADR 选择 **QEMU 直接把 fault 映射为退出码**（不安装 handler，D6）。

- **退出码**：**`0x8C`**（= `0x80 | 12`，对应 spec 的 MALIGN cause 位 `1 << 12` [DADAO-12 §cfx_umon 异常原因表][DADAO-13 §HEE 异常原因表]）。所有 M1 对齐异常（16/32/64 位；byte 天然对齐不触发）统一为 `0x8C`：`ld.sw`/`st.w`/`ld.uw`/`ldm.sw`/`ldm.uw`/`stm.w`（2 B）、`ld.st`/`st.t`/`ld.ut`/`ldm.st`/`ldm.ut`/`stm.t`（4 B）、`ld.o`/`st.o`（RD/RB/RA）、`ldm.o`/`stm.o`（8 B）[contract-isa §4.1.1][contract-isa §4.1.2][contract-isa §4.2][contract-isa §4.9]。
- **退出时 guest 可见状态**（精确异常承诺）：
  - **faulting PC**：`rb0` = 触发异常的指令地址（PC 未前进到下一指令）。
  - **目标寄存器不提交**：目的寄存器（RD/RB/RA）**不被写入**；源操作数可能已被读取，但无任何架构状态提交。
  - **内存不提交**：store 类指令不产生内存写。
  - 其余 RD/RB/RA/RF 状态与异常前一致。
- **测试断言方式**：常规 pass/fail 由 `$? == 0x8C` 判定；如需验证精确状态（faulting PC / 不提交），使用**机器可读的 guest 寄存器读取路径**：QEMU GDB stub（`-S -gdb tcp::<port>` + GDB batch `info registers`）或 QMP（`human-monitor-command {"command-line":"info registers"}`），由 harness 解析寄存器值。该路径读取的是 guest 寄存器状态，**不是** host 日志/stderr/超时，满足零 host 依赖约束。

### D5 ILLI / UNDI / SBZ / IALIGN / RASOF / RASUF 可观测行为

与 D4 同构：QEMU 直接把 fault 映射为退出码，无 handler，目的寄存器不提交，`rb0` = faulting PC，无内存提交。

#### D5.1 ILLI（非法指令，退出码 `0x88`）

触发集合（`spec/` 语义见 [contract-isa §9.1]；机器层附加项标注「架构自定义」）：

- `rd0` 作为目的（除 rrrr 双目的允许一个为 rd0、`ret rd0, 0` 外）；`rb0` 作为目的 [contract-isa §1.3.1][contract-isa §1.3.2]。
- 多寄存器指令 `immu6 = 0`、或起始寄存器 + `immu6 > 64`（超出 rd63/rb63/ra63）[contract-isa §4.1.2][contract-isa §4.2][contract-isa §4.3][contract-isa §4.9]。
- `ld`/`st`（RD）目的 `rdha` 为 `rd0`；`ld.o`/`st.o`/`ldm.o`/`stm.o`（RB）`rbha` 为 `rb0` [contract-isa §4.1.1][contract-isa §4.2]。
- 移位量 `shamt > N`；扩展起始位 `hd > N` [contract-isa §3.4.1][contract-isa §3.4.2]。
- 除法除数为零；`div.s` 的 `INT_MIN ÷ −1` [contract-isa §3.1.5]。
- `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 双目的同时为 `rd0`，或为同一非 `rd0` 寄存器 [contract-isa §3.1.1][contract-isa §3.1.4]。
- 固定位宽算术/比较/乘除余指令 `rdhb` 为 `rd0` [contract-isa §3.1.2][contract-isa §3.2.2][contract-isa §3.1.5]。
- `illi` 指令本身（含 32 位全零指令字 `0x00000000`）[contract-isa §7.2][contract-isa §8.3]。
- **SBZ 字段非零**（见 D5.3）。
- **M1 排除但 0.5.3 已定义的编码**（架构自定义）：RF 指令（RF 存取/运算、`set.w`、`set.ft`/`set.fo`）、LR-SC 原子指令（`lr_*.o`/`sc_*.o`）、特权 cfx 指令（`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`/`escape`/`trap`）[contract-isa §6][contract-isa §7.4][contract-isa §7.5]。理由：这些编码在 0.5.3 中**已定义**（非保留单元格），但 M1 机器不实现，执行即非法指令（ILLI）；UNDI 专用于架构显式留空的编码。
- **机器访问约束违反**（架构自定义）：对 exit port 的非 8 B/多寄存器 store 与任何 load、对 ROM 的 store（只读区域）；完整判定见 D5.6 矩阵。

#### D5.2 UNDI（未定义指令，退出码 `0x89`）

- 执行 QFC 主表或 MISC 子表中**空白单元格**（reserved 编码）[contract-isa §2.7][contract-isa §2.9][contract-isa §8.2]。
- UNDI 与 ILLI 的边界：**编码未定义** → UNDI；**编码已定义但操作数/访问非法** → ILLI [contract-isa §8.3]。

#### D5.3 SBZ 字段非零 → ILLI（退出码 `0x88`）

**无 spec 依据，架构自定义**（`spec/` 未规定 SBZ 非零的异常类型）。理由：

- SBZ 出现在**已知合法 opcode** 内部：指令格式已被识别，只是「应为零」的字段非零。
- 这类比**非法操作数**（ILLI），而非未识别编码（UNDI）。汇编器可静态拒绝 SBZ 违例（如同拒绝 `rd0` 目的）。
- UNDI 保留给架构**显式留空**的 opcode/minor-opcode 单元格；SBZ 是已定义单元格上的字段约束。

M1 范围内的 SBZ 字段示例：`fence` 的 `immu18 bits[17:4]` [contract-isa §7.3]、移位指令中 shamt 位域之外的高位（如 `shl.ub` 的 `hd[5:3]`、`shl.uw` 的 `hd[5:4]`）[contract-isa §3.4.1]。

#### D5.4 IALIGN（取指未对齐，退出码 `0x8D`）

- 取指时 `PC[1:0] ≠ 00` → IALIGN [contract-isa §2.1]。
- 精确异常：不提交任何架构状态，`rb0` = 未对齐的取指地址。

#### D5.5 RASOF / RASUF（退出码 `0x8A` / `0x8B`）

- **RASOF（`0x8A`）**：RegRAS 压栈溢出（调用深度超过 63），或 MemRAS 引用计数溢出 [contract-isa §5.6.1]。
- **RASUF（`0x8B`）**：RegRAS 弹栈下溢（栈空时 `ret`），或 MemRAS 引用计数/内容无效 [contract-isa §5.6.2]。
- 二者均为精确异常：RA 寄存器保持异常前状态（push/pop 未提交），`rb0` = 触发异常的 `call`/`ret` 指令地址 [contract-isa §1.3.4][contract-isa §9.2]。
- 退出码由 spec 的 cause 位派生（`0x80 | 10` / `0x80 | 11`，见 D5.8）。

#### D5.6 内存区域 × 访问种类/宽度 矩阵（含 fault 优先级）

**判定优先级**（依次判定，先命中先返回）：
1. **地址映射**：有效地址不在 ROM/Exit/RAM 任一区域 → **`0x87`（unmapped）**；取指仅 ROM/RAM 有效，其余（含 exit port）→ `0x87`。
2. **对齐**：映射内且访问宽度未自然对齐 → **`0x8C`（MALIGN）**。
3. **访问种类/宽度约束**：映射内、对齐，但违反该区域约束 → **`0x88`（ILLI）**。
4. 否则执行访问。

| 区域 \ 访问 | 取指 | 对齐 load | 对齐 store | 未对齐 load/store |
|------------|------|----------|-----------|------------------|
| boot ROM `0xffff_ffff_0000`–`0xffff_ffff_ffff`（64 KiB，只读） | 允许（`PC[1:0]≠0` → IALIGN `0x8D`） | 允许（任意宽度） | **ILLI `0x88`**（只读区域） | **MALIGN `0x8C`** |
| Exit port `0xffff_8000_0000`–`0xffff_8000_0007`（8 B，只写） | 不允许 → `0x87` | **ILLI `0x88`**（只写区域） | 仅 8 B 对齐 `st.o` → 正常退出（D3）；非 8 B `st.b/w/t` 或 `stm.*` → **ILLI `0x88`** | **MALIGN `0x8C`** |
| RAM `0xffff_0000_0000`–`0xffff_00ff_ffff`（16 MiB，读写） | 允许（`PC[1:0]≠0` → IALIGN `0x8D`） | 允许（任意宽度） | 允许（任意宽度） | **MALIGN `0x8C`** |
| 其余（unmapped） | `0x87` | `0x87` | `0x87` | `0x87` |

- 因所有区域边界 8 B 对齐，**对齐访问永不跨区域边界**；跨边界只可能由未对齐访问触发，按优先级 2 归 MALIGN。
- 「ROM store → ILLI」「Exit port load → ILLI」「Exit port 非 8 B/multi → ILLI」「取指到 exit port/unmapped → `0x87`」均为**无 spec 依据，架构自定义**（`spec/` 不定义物理区域访问种类）。

#### D5.7 区分 fault 与正常 exit

退出码分区（见 D5.8 汇总表）：`0x00` = PASS，`0x01`–`0x7F` = FAIL（均来自 exit port），`0x80`–`0xFF` = 机器 fault 段（具体码见 D5.8）。harness 判定：`$? == 0x00` 为 pass；`0x01`–`0x7F` 为 fail；`$? ≥ 0x80` 视为 fault/协议外。期望 fault 但得到 `0x00`/`0x01`–`0x7F` 则报失败。测试程序**不得**向 exit port 写入 `0x80`–`0xFF`，以保持该分区无歧义。

#### D5.8 Exit code 汇总

**映射规则**：机器 fault 退出码 = **`0x80 | spec_cause_bit_index`**（cause 位见 [DADAO-12 §cfx_umon 异常原因表][DADAO-13 §HEE 异常原因表]）。

| 范围 | 来源 | 含义 | spec cause |
|------|------|------|-----------|
| `0x00` | Exit port | PASS | — |
| `0x01`–`0x7F` | Exit port | FAIL（测试自定义码） | — |
| `0x80` | — | Reserved | — |
| `0x81`–`0x86` | 机器 fault | Reserved（对应 spec cause 位 1–6，M1 未用） | `1<<1`–`1<<6` |
| `0x87` | 机器 fault | Unmapped access（测试机约定） | — |
| `0x88` | 机器 fault | ILLI | `1 << 8` |
| `0x89` | 机器 fault | UNDI | `1 << 9` |
| `0x8A` | 机器 fault | RASOF | `1 << 10` |
| `0x8B` | 机器 fault | RASUF | `1 << 11` |
| `0x8C` | 机器 fault | MALIGN | `1 << 12` |
| `0x8D` | 机器 fault | IALIGN | `1 << 13` |
| `0x8E`–`0xFF` | 机器 fault | Reserved | — |

> `0x88`–`0x8D` 由 spec 的异常原因位派生（可回溯）；`0x87`（unmapped）为测试机约定，与 spec cause 位无关。`0x87`–`0x8D` 一经冻结不得重排（下游 QEMU/harness/向量依赖）。

### D6 测试签名规范

#### D6.1 fault 如何 surface：QEMU 直接映射 fault → exit code

M1 **不安装、也不支持 guest 异常 handler**：无 SEE 异常向量、无异常 ABI（异常入口/返回/保存恢复属 M2+）。本 ADR 冻结「QEMU 检测到 fault 即以对应退出码直接退出」。理由：避免预设未来异常模型，符合 M1 最小化；且 handler 方案需要定义 handler 地址、fault info 结构、返回机制，均依赖 M1 不具备的异常 ABI。注意：spec 的 `trap`/`escape` 是**特权 cfx 陷入/退出指令**，与本 ADR 的异常 handler 机制无关；M1 不实现 cfx，执行它们按 D5.1 归 **ILLI（`0x88`）**，不构成任何陷入/处理路径。

#### D6.2 语义测试 pattern

寄存器约定：`rb16` = exit port 地址，`rd16`/`rd17`/`rd18` = 被测/期望/比较结果（目的绝不用 `rd0`，否则 ILLI）。逐条地址手算：

```asm
; 入口 _start（0xffff_0000_0000）：rb0=0xffff_0000_0000，rb1=0xffff_00ff_0000（trampoline 设栈），
;   rb2=0xffff_0000_0000，其余 RD/RB/RA=0，rf0=0x7FF8_0000_7FC0_0000（D2）。

; 1. 构造 exit port 地址 rb16 = 0xffff_8000_0000
;    set.zw rb16, wp2, 0xffff：写 wyde2（bits[47:32]）=0xffff，其余 48 位清 0 → 0xffff_0000_0000
;    or.w  rb16, wp1, 0x8000：wyde1（bits[31:16]）|= 0x8000 → 0xffff_8000_0000
set.zw  rb16, wp2, 0xffff      ; rb16 = 0xffff_0000_0000
or.w    rb16, wp1, 0x8000      ; rb16 = 0xffff_8000_0000

; 2. 被测：rd16 = 42，再就地加 7 → 49
set.zw  rd16, wp0, 42          ; rd16 = 0x2A（set.zw 写 wyde0，其余清 0）
add.si  rd16, 7                ; rd16 = 42 + 7 = 49（riii 就地全 64 位加）

; 3. 期望值 rd17 = 49
set.zw  rd17, wp0, 49          ; rd17 = 0x31

; 4. 比较：cmp.so rd18, rd16, rd17 → rd18 = cmp(rd16, rd17)（-1/0/1，orrr）
cmp.so  rd18, rd16, rd17       ; 相等时为 0；目的 rd18≠rd0
br.nz   rd18, fail             ; rd18 != 0 → 跳 fail

; 5. PASS：写 0 到 exit port（rd0 恒为 0，直接作源）
st.o    rd0, rb16, 0           ; mem64[0xffff_8000_0000] = 0 → host $? = 0x00

fail:
set.zw  rd16, wp0, 1           ; rd16 = 1
st.o    rd16, rb16, 0          ; mem64[0xffff_8000_0000] = 1 → host $? = 0x01
```

#### D6.3 异常测试 pattern

```asm
; 1. 构造 exit port 地址 rb16 = 0xffff_8000_0000
set.zw  rb16, wp2, 0xffff
or.w    rb16, wp1, 0x8000      ; rb16 = 0xffff_8000_0000

; 2. 构造 RAM 基址 rb17 = 0xffff_0000_0000
set.zw  rb17, wp2, 0xffff      ; rb17 = 0xffff_0000_0000

; 3. 触发 MALIGN：8B load 到 0xffff_0000_0001（非 8B 对齐）
ld.o    rd16, rb17, 1          ; 有效地址 = 0xffff_0000_0000 + 1 = 0xffff_0000_0001 → MALIGN → host $? = 0x8C

; 4. 若执行到此，说明 fault 未发生 → FAIL
set.zw  rd16, wp0, 1           ; rd16 = 1
st.o    rd16, rb16, 0          ; host $? = 0x01
```

harness 期望 `$? = 0x8C`；得到 `0x00` 或 `0x01`–`0x7F` 表示 fault 未发生。若需验证 `rb0` = faulting PC 与目的寄存器未提交，使用 D4 的 GDB/QMP 寄存器读取路径。

ILLI 测试 pattern（以 `illi` 指令为例）：

```asm
; 1. 构造 exit port 地址 rb16 = 0xffff_8000_0000
set.zw  rb16, wp2, 0xffff
or.w    rb16, wp1, 0x8000      ; rb16 = 0xffff_8000_0000

; 2. 触发 ILLI：illi 0（op=0x00、minor-opcode=0、immu18=0，即 32 位全零字）
illi    0                      ; → ILLI → host $? = 0x88

; 3. 若执行到此，说明 fault 未发生 → FAIL
set.zw  rd16, wp0, 1
st.o    rd16, rb16, 0          ; host $? = 0x01
```

harness 期望 `$? = 0x88`。RASOF/RASUF（`0x8A`/`0x8B`）、UNDI（`0x89`）、IALIGN（`0x8D`）的测试同构：构造触发条件后断言对应退出码。

#### D6.4 ROM trampoline

```asm
; ROM trampoline — flat blob 链接于 0xffff_ffff_0000，由 QEMU -bios 加载。
; 入口：rb0=0xffff_ffff_0000（reset vector = cfx_power_hypv_excp_vector），其余寄存器=0（D2）。

; 1. 设栈指针 rb1（SP/rbsp）到 RAM 高地址端附近
;    set.zw rb1, wp2, 0xffff → 0xffff_0000_0000；or.w rb1, wp1, 0x00ff → 0xffff_00ff_0000
set.zw  rb1, wp2, 0xffff       ; rb1 = 0xffff_0000_0000
or.w    rb1, wp1, 0x00ff       ; rb1 = 0xffff_00ff_0000（RAM 顶部 0xffff_00ff_ffff 附近）

; 2. 构造 RAM 入口地址 rb2 = 0xffff_0000_0000
set.zw  rb2, wp2, 0xffff       ; rb2 = 0xffff_0000_0000

; 3. 绝对跳转（rrii）：Addr = rbha + rdhb + (imms12<<2) = rb2 + rd0 + 0 = 0xffff_0000_0000
;    ROM→RAM 相距 0x00ff_0000_0000（≈1 TiB），远超 jump imms24（PC 相对 ±32 MiB）范围，
;    故必须先构造绝对 RB 地址再用 rrii jump。
jump    rb2, rd0, 0            ; PC ← 0xffff_0000_0000
```

#### D6.5 三个入口时刻的状态（冻结）

| 时刻 | `rb0` | 其他寄存器 |
|------|-------|-----------|
| power-on reset（执行任何指令前） | `0xffff_ffff_0000` | `rd0`–`rd63`=0；`rb1`–`rb63`=0；`ra0`–`ra63`=0；`rf0=0x7FF8_0000_7FC0_0000`；`rf1`–`rf63`=0（D2） |
| ROM 第一条指令（在 `0xffff_ffff_0000` 执行时） | `0xffff_ffff_0000` | 同 power-on reset |
| RAM `_start` 第一条指令（在 `0xffff_0000_0000` 执行时） | `0xffff_0000_0000` | `rb1=0xffff_00ff_0000`（SP）、`rb2=0xffff_0000_0000`，其余 RB=0；RD/RA/RF 同 power-on reset |

- `rb0` 在指令执行时等于**当前指令地址**（PC 语义）[contract-isa §1.3.2]；`_start` 第一条指令 retire 后 `rb0` 变为 `0xffff_0000_0004`。
- trampoline 修改过的 `rb1`/`rb2` 使「`_start` 时除 `rb1`/`rb2` 外其余 RB 为 0」成立；测试程序可依赖 D6.5 冻结状态。

## Rationale（理由）

- **内存映射采用核内地址空间模型**：M1 无 cfx、无 MMU，测试机整体占用最高段 cfxcode 63（power）的核内地址空间，使 boot ROM 正好落在 spec 的硬件复位向量 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`，从而 `rb0` 复位值**直接符合 spec**、无需偏离。RAM/Exit port 作为测试机约定放在同一段内的独立地址（`0xffff_0000_0000` / `0xffff_8000_0000`），三者互不重叠且 8 B 对齐。遗留 `dadao-virt`（ROM `0x0010_0000`/UART `0x1000_0000`/RAM `0x8000_0000`）仅作只读对照，v5 不沿用。
- **双镜像启动而非单镜像**：D1 要求 ROM 容纳最小 trampoline、D6 需要 ROM trampoline；由 `-bios` 提供外部 ROM blob 使 QEMU 机器保持简单，且不必把 ISA 二进制内建进 QEMU 源码。与 ADR-0003 一致：测试产物仍是 `.o → objcopy .text → flat`，由 `-kernel` 加载到 RAM 基址、从该基址进入；`e_entry` 不参与。
- **直接 exit 而非 handler**：无 OS 时 handler 方案需要 handler 地址、fault info 布局与返回机制，依赖 M1 没有的异常 ABI；直接退出更简单、可自动化，且不预设未来异常模型。M1 中 `trap`/`escape` 等特权 cfx 指令**不提供陷入/退出机制**，按 D5.1 归 **ILLI（`0x88`）**，同样走直接退出路径。
- **fault 码与 guest 码分区**：`0x00`–`0x7F` 为 guest（pass/fail），`0x80`–`0xFF` 为机器 fault；fault 码由 **spec cause 位派生**（`0x80 | cause_bit` → `0x88`–`0x8D`）或测试机约定（`0x87` unmapped），使 `$?` 单值即可无歧义区分 pass/fail/fault，满足零 host 依赖，且可回溯到 spec 的异常原因编码。
- **fault 码由 spec cause 位派生（`0x80 | cause_bit`）**：`spec/` 定义异常原因 `excp cause id = 1<<n`（ILLI=8、UNDI=9、RASOF=10、RASUF=11、MALIGN=12、IALIGN=13）[DADAO-12 §cfx_umon 异常原因表][DADAO-13 §HEE 异常原因表]。退出码取 `0x80 | n`，使测试机 fault 码**可回溯到 spec**，而非任意编号；unmapped 无对应 spec cause，退出码 `0x87` 为**测试机约定**（与 spec cause 位无关）。
- **SBZ → ILLI 而非 UNDI**：SBZ 是已识别 opcode 内的字段约束，类比非法操作数；UNDI 专用于架构留空编码。
- **M1 排除但已定义的编码 → ILLI**：编码在 0.5.3 中已定义（非留空），机器不实现即非法指令；与「UNDI = 空白单元格」的契约定义一致。
- **非 8B exit port 访问 → ILLI**：opcode 合法，违反 MMIO 宽度/种类约束属非法操作数，不是未识别编码；修正了将 MMIO 宽度违规误归 UNDI 的旧做法。
- **RF 仅复位不实现**：M1 排除 RF 指令语义；按 spec 位布局确定性复位 `rf0`，避免未初始化浮点状态导致不确定行为，同时不引入 RF 指令实现。
- **`rf0` 常量独立推导**：从 0.5.3 `SimRISC-00 §浮点状态寄存器` 的位段直接组合（只读 QNaN 位固定、SBZ 与 R/W 位复位为 0），得到 `0x7FF8_0000_7FC0_0000`，不照抄任何旧实现的常量。
- **保留区显式 fault**：unmapped 访问给出确定退出码 `0x87`，而非静默 no-op/host abort/超时。

## Consequences（影响）

- **零 host 依赖成立**：所有 pass/fail/fault 分类均可由 `$?` 判定；精确异常状态（faulting PC、不提交）由机器可读的 guest 寄存器读取路径（GDB/QMP）验证，不依赖日志/stderr/超时。
- **下游约束**：QEMU `hw/dadao/` 机器须实现本 ADR 的内存映射、复位值、exit port、fault→退出码映射与双镜像加载；test harness/向量须按 `0x00`/`0x01`–`0x7F`/`0x80`–`0xFF` 分区断言（具体 fault 码见 D5.8）；测试程序不得向 exit port 写 `0x80`–`0xFF`。
- **诊断局限**：退出码只编码 fault 类别，不编码 faulting 地址/操作数；需要精确 PC/状态验证的测试须使用 D4 冻结的寄存器读取路径。
- **`rb0` 复位符合 spec**：`rb0` 复位取 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（= boot ROM 基址），与 spec 一致；M1 仅借用该地址，不复现 hypv 复位运行模式等 HBI/SEE 语义。
- **架构自定义项**：RAM/Exit port 的具体地址、「测试机整体占用 cfxcode 63 段」、复位值（`rd1`–`rd63`/`rb1`–`rb63`/`ra*`/`rf0` 的 R/W 位/`rf1`–`rf63`）、退出码、SBZ→ILLI、MMIO 访问矩阵均无 `spec/` 依据；若未来 `spec/` 给出规定，须修订本 ADR。
- **SBZ = ILLI 为前瞻性决策**：若 `spec/` 后续规定 SBZ → UNDI，须修订。
- **与 ADR-0003 一致**：ADR-0003 冻结 object → flat 的转换（无 LLD/`ET_EXEC`/`e_entry` 加载），本 ADR 冻结 flat → QEMU 的加载/入口；两者共同构成唯一端到端路径。
- **RF 指令不可用**：M1 测试程序不得执行 RF 指令（执行即 ILLI）；RF 支持留后续阶段。

## 状态说明

Candidate：待评审。评审通过后由主会话置 `Accepted`；决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策。评审须确认：D1–D6 全覆盖且无未决项、fault/exit 码分区无歧义、rf0 常量位段推导可独立复核、双镜像启动协议与 ADR-0003 一致、MMIO × 访问矩阵对每个组合给出确定结果。

## 修订

**rev. 2026-09-13（用户决定）**：D1 内存映射由「遗留 `dadao-virt` 布局（ROM `0x0010_0000` / Exit `0x1000_0000` / RAM `0x8000_0000`）」改为「**核内地址空间模型**：测试机整体占用最高段 cfxcode 63（power），RAM `0xffff_0000_0000`（16 MiB）、Exit port `0xffff_8000_0000`（8 B）、boot ROM `0xffff_ffff_0000`（64 KiB，= `cfx_power_hypv_excp_vector`）」。

- **动机**：与 spec 的核内地址空间模型（`DADAO-12 §2.1`，`bits[47:42]` = cfxcode）一致，并让 boot ROM 落在 spec 的硬件复位向量 `cfx_power_hypv_excp_vector` 上——`rb0` 复位值随之**符合 spec**，消除原「偏离 spec」的架构自定义。
- **变更范围**：D1 地址图；D2.1 `rb0` 复位值（`0x0010_0000`→`0xffff_ffff_0000`）及其依据；D2.2 加载地址、D2.3 ROM blob 链接基址/RAM entry；D3 exit port 地址；D5.6 矩阵地址；D6.2–D6.5 示例与入口状态；Rationale/Consequences 相关表述。**D2 其余复位值、D3 协议语义、D4/D5 fault 语义、D6 测试 pattern 结构均不变。**
- **RAM 容量**：128 MiB → **16 MiB**（M1 单 TU 测试足够）。
- **exit port 宽度**：仍为**恰好 8 字节**（`st.o`），不变。
- **地址构造**：新地址高 wyde 全为 `0xffff`，示例用 `set.zw rbha, wp2, 0xffff` + `or.w rbha, wp1, immu16` 逐 wyde 构造（`0xffff` 在 wyde2）。
- **流程说明**：本 ADR 于 2026-09-13 刚 `Accepted` 且尚无实现依赖，按用户明确决定**就地修订并加本修订说明**（`adr-authoring.md` 一般规则为「不直接改写已 `Accepted` 的决策」，此处为经授权的例外；`**状态**` 行已标 `rev. 2026-09-13`）。

**rev. 2026-09-13（用户决定）：D3 零 host 依赖补充「harness 墙钟超时兜底」**：pass/fail 仍只由 `$?` 判定；harness 另设默认 **9 s**（可经环境变量覆盖）的墙钟超时，超时即杀掉 QEMU 并记为 **harness 错误（inconclusive）**，**不**参与 guest pass/fail。原 D3「无超时」措辞改为上述机制（与 Context「不得用超时判定 pass/fail」一致）。

**rev. 2026-09-13（用户决定）：D4/D5 机器 fault 退出码改为由 spec cause 位派生**：机器 fault 退出码改为 **`0x80 | spec_cause_bit_index`**——ILLI=`0x88`、UNDI=`0x89`、RASOF=`0x8A`、RASUF=`0x8B`、MALIGN=`0x8C`、IALIGN=`0x8D`（原为 `0x81`–`0x86`，与 spec 位序无对应）；unmapped=`0x87`（测试机约定，与 spec cause 位无关）。依据 `spec/DADAO-12:408-413`（cfx_umon 异常原因表）/`spec/DADAO-13:38-43`（HEE 表）的 `excp cause id = 1<<n`。D4、D5.1–D5.6、D5.8 码表与 D6 示例同步更新。
