# Machine-01：测试机运行环境（v5 自定）

> **状态**：生效（2026-10-07，`SPEC-114t`）
>
> **定位**：本册是 v5 自定规范，定义 **DADAO-v5 测试机（`dadao-m1`）运行环境与 semihosting** 的规范正文——面向 QEMU 机器模型、bootrom 固件、harness 与测试向量。上游 `spec/DADAO-*` 与 `spec/SimRISC-*` 仍为**上游基线**；本册不改其架构语义。
>
> **来源（决策层）**：`ADR-0020`（`.tao/adr/adr-0020-see-semihosting.md`，`D1`–`D15`）与 `ADR-0004`（`.tao/adr/adr-0004-test-machine.md`，含 rev. 2026-10-07 的 `R1`/`R2`/`R3`）。ADR 只记决策/理由/被否方案，本册承载规范正文（`ADR-0020 D13`）。semihosting 服务号值语义取自 Arm Semihosting（`Semihosting for AArch32 and AArch64`）。
>
> **标注约定**：正文中「**测试机约定**」项**无上游 spec 依据**，属 v5 架构自定义（附决策出处）；有上游出处的语义给出 `[DADAO-NN §x]`/`[SimRISC-NN §x]` 引用。`cfx0/1/2/3/63` 等实现范围一律为**测试机约定**，不构成对上游 `DADAO-12`/`DADAO-13` 的架构限制。

---

## 1. 内存映射与复位

CPU 内部地址总线固定为 48 位；48 位核内地址的高 6 位 `bits[47:42]` 指定核芯功能扩展编号（cfxha）。[DADAO-12 §2.1 核内地址空间]

硬件复位后的启动地址为 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`，64 KiB），该地址空间可由 CPU 直接取指并执行。[DADAO-12 §2.1 核内地址空间]

### 1.1 核内地址空间划分（测试机约定）

v5 测试机使用的核内地址空间划分如下（均为 48 位核内有效地址；地址区间为**测试机约定**，上游 `spec/` 只规定 `cfxha 63` 的复位向量）。[ADR-0020 D15]

| 区域 | 起始 | 大小 | cfxha / cfxname | 说明 |
|------|------|------|-----------------|------|
| **RAM@0（新）** | `0x0000_0000_0000` | 【待 `QEMU-049t` 定】 | 0 / `umon` | 供 bootrom/SEE（C1 step1 双映射引入） |
| **旧 RAM 段（过渡保留）** | `0xffff_0000_0000` | 16 MiB | 63 / `power` | 供既有 M1–M4 测试（step2 迁移后删除） |
| **exit port（过渡保留）** | `0xffff_8000_0000` | 8 B | 63 / `power` | `ADR-0004 D3` 协议；`D8` 后由 `SYS_EXIT` 取代 |
| **boot ROM** | `0xffff_ffff_0000` | 64 KiB | 63 / `power` | 复位向量 = `cfx_power_hypv_excp_vector`；`-bios` 加载 |

- **RAM 基址口径**：M5 起 RAM 基址改为全 0（`0x0000_0000_0000`）；复位向量/ROM（`0xffff_ffff_0000`，64 KiB）与 exit port（`0xffff_8000_0000`）不变。[ADR-0004 R3]
- **C1 双映射过渡**：**step1（M5，`QEMU-049t`）** 机器模型**同时映射 RAM@0（新，供 bootrom/SEE）与旧 RAM 段（`0xffff_0000_0000`，供既有测试）**；**step2（另立，M5 之外）** 把既有向量/harness/`crt0`/e2e 迁到 `0` 并删旧 RAM 段、收紧断言。[ADR-0020 D15][ADR-0004 R3]
- 上述划分**存续期**为 C1 step2 迁移完成前：旧 RAM 段与 RAM@0 并存，exit port 与 `SYS_EXIT` 并存。[ADR-0020 D15]

### 1.2 越界访问与越界取指异常（含取指路径）

- **spec 层语义（`CFXMEM`）**：对核内地址空间进行非法访问时，触发对应核芯功能扩展的 `CFXMEM` 异常；目标 cfx 由地址高 6 位 `addr[47:42]`（cfxha）确定。[DADAO-12 §2.1 核内地址空间] `CFXMEM` 的异常原因编号为 `1 << 1`。[DADAO-12 §4. 专有寄存器设计规范]
- **测试机退出码**：机器 fault 退出码 = `0x80 | spec_cause_bit_index`（`ADR-0004 D5.8` 规则）⇒ `CFXMEM`（`1<<1`）对应 **`0x81`**。[ADR-0004 D5.8][ADR-0020 D15]
- **测试机历史约定（`unmapped`）**：`0x87` 为**测试机约定**退出码，**无 spec cause**，用于无 cfx 归属的 unmapped 访问；`0x87` 与 spec cause 位无关。[ADR-0004 D5.8]
- **层次与适用**：`CFXMEM`（`0x81`）适用于核内地址空间模型内的非法访问/取指（cfxha 段内的非法子区间、越界访问/取指）；`0x87`（unmapped）保留为测试机历史约定，用于既有 M1–M4 语义；C1 step2 迁移完成前两者并存。[ADR-0020 D15]
- **取指路径同等对待**：越界**取指**与越界**数据访问**同属非法核内地址访问，**均须报异常**，不得只覆盖数据访问路径；不得静默继续或静默丢弃。[ADR-0020 D15]
- **码表冻结、不得重排**：`ADR-0004 D5.8` 的 fault 码表已冻结；`CFXMEM` 落在表中已保留的 `0x81`–`0x86` 区间（对应 spec cause 位 1–6），**无需新码、无需重排**；`0x87`–`0x8D` 一经冻结不得重排。[ADR-0004 D5.8][ADR-0020 D15]
- 精确路由（哪一类越界取 `0x81`、哪一类取 `0x87`）与 RAM@0 容量，由 `QEMU-049t` 按上述层次落地并写 `check-interface` 断言。[ADR-0020 D15]

---

## 2. 运行模式

DADAO 定义四种运行模式（两位编码）：`user`（`0b00`）、`jail`（`0b01`）、`supv`（`0b10`）、`hypv`（`0b11`）；`user`/`jail` 为普通用户态，`supv`/`hypv` 为特权态。[DADAO-12 §1. 运行模式与核芯功能扩展]

`hypv`（超管模式）的 cg3 寄存器（含 `cfx_⟨cfxname⟩_hypv_global_cfx_mask`、`cfx_⟨cfxname⟩_hypv_switch_run_mode`、`cfx_⟨cfxname⟩_hypv_excp_vector`）定义见 HEE。[DADAO-13 §1. cg3 - hypv mode 寄存器]

`trap`/`escape`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst` 可在**任意运行模式**下执行；是否允许由各核芯功能扩展的 cfx mask 与指令类型 cfx mask 控制。[SimRISC-11 §特权指令]

异常进入后，硬件把运行模式与核芯功能扩展掩码改为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 与 `cfx_⟨cfxname⟩_<mode>_switch_cfx_mask` 的值（异常进入流程步骤 8）。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3. 共有寄存器设计规范]

- **测试机范围**：v5 测试机只启用 `hypv` 与 `user`；**本版不启用 `supv`**、不涉及 `smon`。[ADR-0020 D12][ADR-0004 R1][Machine-01 §6]
- **bootrom 移交**：bootrom 由 `hypv` **直接跳到 `user`** 运行应用。[ADR-0020 D12][ADR-0004 R1]

---

## 3. cfx 与权限

每个核芯功能扩展提供 cg0–cg7 共有寄存器，规范相同；其中 cg0–cg3 为 `user`/`jail`/`supv`/`hypv` 各自的 12 个模式寄存器，cg4–cg7 为配置/现场/暂存/内部存储寄存器。[DADAO-12 §3. 共有寄存器设计规范]

- `global_cfx_mask` 与指令类型 mask（`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`/`trap`/`escape` 各自一位）语义：**0=可触发，1=屏蔽**；自身 cfxha 对应位由硬件忽略。[DADAO-12 §3. 共有寄存器设计规范]
- `switch_cfx_mask` 为陷入时采用的异常掩码（0=可触发，1=屏蔽）；`switch_run_mode` 为陷入时切换的运行模式。[DADAO-12 §3. 共有寄存器设计规范]
- reserved cfxha（`7`–`14`、`19`–`61`）触发 `ILLI`；cfxha 合法但指令 cfx mask 禁止，同样触发 `ILLI`。[DADAO-12 §5. 异常进入与异常退出]
- `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 是 **PTBR 模式权限**异常：地址转换第一步检查当前运行模式是否允许访问 `VA[47:42]` 对应的 PTBR（`cfx_ptw_user/jail/supv/hypv_perm`），不允许则触发对应 PERM 异常。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.2 普通页的地址转换]
- **两个权限层次**：**PTBR 权限**（`NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`，出自 cfx_ptw 异常原因表）与 **cfx 访问权限**（cfx mask 不允许 ⇒ `ILLI`，见 `§5` 异常进入流程）是**不同层次**，不可混同。[ADR-0020 D9][DADAO-12 §4. 专有寄存器设计规范]

- **测试机 cfx 实现范围**：v5 测试机只实现 **`cfx0`/`cfx1`/`cfx2`/`cfx3`/`cfx63`**（`umon`/`jmon`/`smon`/`hmon`/`power`，`DADAO-12 §1` 的 cfxha 表）。该范围为**测试机约定**（控制首版成本），**不构成对上游 `DADAO-12`/`DADAO-13` 架构的 cfx 数量/编号限制**。[ADR-0020 D9][DADAO-12 §1. 运行模式与核芯功能扩展]
- 对**不存在**的核芯功能扩展（其 cfx 寄存器）的访问触发 **`CFXREG`**；reserved cfxha（`7`–`14`/`19`–`61`）仍按 `§5` 触发 `ILLI`。[ADR-0020 D9][DADAO-22 §3. 系统信息（smon）][DADAO-12 §5. 异常进入与异常退出]

---

## 4. `trap`/`escape` 与异常进入流程

### 4.1 一般 `trap` → 异常进入流程 → cfx 向量

`trap cfxha, immu18` 的 `cfxha` 指定服务提供者（目标核芯功能扩展），`immu18` 为功能编号。[DADAO-22 §1. 调用约定]

当 `immu18[17:16] ≠ 2'b11` 时，为**一般 trap**：先过权限检查，允许后**走 `DADAO-12 §5` 异常进入流程**（步骤 1–10，含步骤 10「跳转至异常向量」`inner_inst_pointer <= cfx_⟨cfxname⟩_<mode>_excp_vector`）——即**进入该 cfx 的异常向量**。[DADAO-12 §5. 异常进入与异常退出][ADR-0020 D10]

### 4.2 `escape` → 异常退出流程

`escape` 指令完成异常退出：恢复 `excp_prev_cfx_mask`/`excp_prev_run_mode`、递增 `escape_num`，并以 `escape` 的 `imms18`（指令字偏移）计算返回地址并跳转——`Addr = excp_cause_ip + (imms18 << 2)`。[DADAO-12 §异常退出流程] 汇编层写 `escape cfxha, [excp_cause_ip, imms20]`，`imms20` 以字节为单位且须 `%4==0`。[SimRISC-11 §退出指令]

被调方通过 `escape cfxha, [excp_cause_ip, 4]` 返回 trap 指令的下一条指令（`excp_cause_ip + 4`）。[DADAO-22 §1. 调用约定]

### 4.3 两条路对照

| 路径 | 触发条件 | 处理 | 返回 |
|------|----------|------|------|
| **一般 trap** | `immu18[17:16] ≠ 2'b11` | 走 `DADAO-12 §5` 异常进入流程，**进入 cfx 向量** | 由被调方 `escape` 返回 |
| **semihosting** | `immu18[17:16] == 2'b11` | 实现层**译码短路**，**不进入向量**（同构 RISC-V `RISCV_EXCP_SEMIHOST`） | 直接 **PC 步进**返回（见 `§5`） |

两条路由由 `ADR-0020 D10` 冻结：一般 trap 与 semihosting 分离，**不得把 semihosting 混入向量路径**（否则实现者会误让 semihosting 进入向量）。[ADR-0020 D10]

---

## 5. semihosting

semihosting 是 v5 测试机提供的「guest 经 `trap` 请求宿主 I/O」机制；本节为其**规范正文**（服务号值语义取自 Arm Semihosting；v5 特有部分标测试机约定）。

### 5.1 判定（入口 tag）

- **判定**：`trap cfxHA, immu18` 中 **`immu18[17:16] == 2'b11`** ⇒ 该 `trap` 为 **semihosting 调用**（**与 `cfxha` 无关**）。[ADR-0020 D1]
- **`D1` 语义/理由说明（架构自定义）**：该 tag 判定**无上游 spec 依据、属 v5 架构自定义**——`spec/DADAO-22` 只规定 `cfxha` 为服务提供者、`immu18` 为功能编号；`spec/SimRISC-11 §陷入指令` 只规定 `immu18` 为功能编号；二者**均无 semihosting 语义**。故本机制在 v5 中由测试机定义，guest/实现共同遵守此 tag。[ADR-0020 D1][DADAO-22 §1. 调用约定][SimRISC-11 §陷入指令]
- **两条路**：`immu18[17:16] == 2'b11` 走 semihosting 短路（本节）；`≠ 2'b11` 走一般 trap 进入向量（见 `§4.1`）。[ADR-0020 D10]

### 5.2 调用约定（传参/返回寄存器）

v5 semihosting 为**恒 64 位**、**大端**（`ADR-0003 D1`）[ADR-0020 D6]。寄存器映射如下：

| 角色 | v5 寄存器 | 说明 |
|------|-----------|------|
| **操作号（标量）** | `rd16`（= `rda0`） | 服务号（见 `§5.3`） |
| **参数块指针（地址）** | `rb16`（= `rba0`） | 指向 64 位字段组成的参数块 |
| **返回值** | `rd31` | 标量返回；指针返回才用 `rb31`，semihosting 不用 |

- 号 → `rd16`、参数块指针 → `rb16`、返回 → `rd31`；对齐共享层 `common_semi_arg(cs,0)`=号、`common_semi_arg(cs,1)`=参数块指针。[ADR-0020 D2][ADR-0020 D14]
- **不另设 `rd15`**：`rd15` 是 `umon`/`jmon` 系统调用号，semihosting 不使用。[ADR-0020 D2][DADAO-21 §系统调用规范]
- 传参复用 ABI 约定（数据参数 `rd16–rd31`、地址参数 `rb16–rb31`）；三组寄存器各自独立计数。[DADAO-22 §1. 调用约定][DADAO-21 §参数寄存器：Parameter registers]
- 参数块字段为 **64 位**，按 target 端序读取（v5 **大端**）。[ADR-0020 D6]

### 5.3 服务表（完整 25 个）

v5 semihosting **服务集 = 完整 25 个**，号值采用 **Arm Semihosting 号值**；服务号值↔入参/出参的权威表即下表。[ADR-0020 D3]

- 表中「参数块」= `rb16` 指向的 64 位字段块；「无参数」= 参数寄存器须为 0。
- 各服务的语义与字段布局遵循 Arm Semihosting（`Semihosting for AArch32 and AArch64`，`Release 2.0`）。[ADR-0020 D3]
- `SYS_SYNCCACHE (0x19)` 在 Arm Semihosting `Release 2.0` 中列为保留号；v5 沿用共享层既有号值并纳入服务集。[ADR-0020 D3]

| 号值 | 名称 | 功能 | 入参 / 返回 |
|------|------|------|-------------|
| `0x01` | `SYS_OPEN` | 打开宿主文件 | 参数块〔文件名指针, 打开模式, 文件名长度〕；返回句柄，失败 `−1` |
| `0x02` | `SYS_CLOSE` | 关闭文件 | 参数块〔句柄〕；返回 `0` 成功 / `−1` 失败 |
| `0x03` | `SYS_WRITEC` | 写单个字符 | 参数寄存器 = 字符指针；无返回 |
| `0x04` | `SYS_WRITE0` | 写以 0 结尾字符串 | 参数寄存器 = 字符串指针；无返回 |
| `0x05` | `SYS_WRITE` | 写缓冲区到文件 | 参数块〔句柄, 缓冲区指针, 字节数〕；返回未写字节数 |
| `0x06` | `SYS_READ` | 从文件读入缓冲区 | 参数块〔句柄, 缓冲区指针, 字节数〕；返回未填字节数 |
| `0x07` | `SYS_READC` | 读控制台字符 | 无参数；返回读到的字节 |
| `0x08` | `SYS_ISERROR` | 判断错误状态 | 参数块〔状态字〕；返回 `0`（非错误）/ 非 `0` |
| `0x09` | `SYS_ISTTY` | 判断交互设备 | 参数块〔句柄〕；返回 `1`/`0` |
| `0x0a` | `SYS_SEEK` | 文件定位 | 参数块〔句柄, 绝对字节位置〕；返回 `0` / 负值 |
| `0x0c` | `SYS_FLEN` | 文件长度 | 参数块〔句柄〕；返回长度 / `−1` |
| `0x0d` | `SYS_TMPNAM` | 取临时文件名 | 参数块〔缓冲区指针, 标识符, 缓冲区长度〕；返回 `0` / `−1` |
| `0x0e` | `SYS_REMOVE` | 删除文件 | 参数块〔路径名指针, 长度〕；返回 `0` / 非 `0` |
| `0x0f` | `SYS_RENAME` | 重命名文件 | 参数块〔旧名指针, 旧名长度, 新名指针, 新名长度〕；返回 `0` / 非 `0` |
| `0x10` | `SYS_CLOCK` | 自启动起百分秒 | 无参数；返回百分秒数 / `−1` |
| `0x11` | `SYS_TIME` | 自 1970-01-01 起的秒 | 无参数；返回秒数（按无符号解释） |
| `0x12` | `SYS_SYSTEM` | 执行宿主命令 | 参数块〔命令串指针, 长度〕；返回状态（见 `§5.6` 风险） |
| `0x13` | `SYS_ERRNO` | 取宿主 errno | 无参数；返回宿主 `errno` |
| `0x15` | `SYS_GET_CMDLINE` | 取命令行 | 参数块〔缓冲区指针, 缓冲区长度〕；返回 `0` / `−1` |
| `0x16` | `SYS_HEAPINFO` | 取堆/栈参数 | 参数块〔heap_base, heap_limit, stack_base, stack_limit〕 |
| `0x18` | `SYS_EXIT` | 报告退出 | 64 位：参数块〔原因码, 子码〕；不返回（见 `§5.5`） |
| `0x19` | `SYS_SYNCCACHE` | 同步 Cache | 无参数；Cache 一致性同步 |
| `0x20` | `SYS_EXIT_EXTENDED` | 报告退出（带退出码） | 参数块〔原因码, 退出码〕；不返回（见 `§5.5`） |
| `0x30` | `SYS_ELAPSED` | 已流逝的 target ticks | 64 位：参数块〔64 位 ticks〕；返回 `0` / `−1` |
| `0x31` | `SYS_TICKFREQ` | tick 频率 | 无参数；返回 ticks/秒 / `−1` |

### 5.4 返回机制

semihosting **无 `escape` 指令**：服务完成后由实现层直接**前移 PC**（`pc += 4`，跳过 `trap`）并写回返回寄存器（`rd31`）；guest 侧不需 `escape` 返回。[ADR-0020 D4]

- 该机制与一般 trap 的 `escape cfxha, [excp_cause_ip, 4]` 返回（`§4.2`）不同：semihosting 不进入向量，故不适用通用 `escape` 返回约定（`ADR-0020 D4`）。[ADR-0020 D4][DADAO-22 §1. 调用约定]

### 5.5 停机（`SYS_EXIT` 取代 exit port）

- semihosting **`SYS_EXIT`（`0x18`）/`SYS_EXIT_EXTENDED`（`0x20`）取代 exit port**（`ADR-0004 D3`）作为停机协议。[ADR-0020 D8][ADR-0004 R2]
- 常规应用退出使用原因码 `ADP_Stopped_ApplicationExit`（`0x20026`）；`SYS_EXIT_EXTENDED` 的第二个字段为退出状态码。退出码须忠实传播到 host `$?`，沿用 `ADR-0011` 的确定性 halt 机制（写入后即锁定退出码）。[ADR-0020 D8]
- **迁移范围 = 全部**：M1–M4 所有依赖 exit port 的向量/harness 全迁 `SYS_EXIT`（实施归 `TESTCASES-034t`）；迁移完成前 exit port 过渡保留。[ADR-0020 D8][ADR-0020 D15]

### 5.6 已知风险（`SYS_SYSTEM`）

`SYS_SYSTEM`（`0x12`，执行宿主命令）为**已登记的已知安全风险**：命令在宿主上执行，可能产生非预期后果；v5 **不因此拒绝该服务**（服务集 = 完整 25 个），而以默认 `gdb`/沙箱、`native` 显式开启作为缓解手段。[ADR-0020 D3][ADR-0020 D7]

---

## 6. 加载与 bootrom

M5 的 QEMU 提供**新 bootrom**（固件），用于**初始权限/向量配置**；bootrom 用**自有工具链**编译（LLVM 新指令的首个真实用户）。[ADR-0020 D12]

- **加载模型**：用 **`-bios`** 加载 bootrom；**复位向量不变**（`0xffff_ffff_0000` = `cfx_power_hypv_excp_vector`，64 KiB）。[ADR-0020 D12][ADR-0004 R1][DADAO-12 §2.1 核内地址空间]
- **模式移交**：bootrom 在 `hypv` 完成初始权限/向量配置后，**直接跳到 `user`** 运行应用；本版不启用 `supv`。[ADR-0020 D12][ADR-0004 R1]
- **并存关系**：`-bios` bootrom 启动路径与 M4 的 ELF 单镜像路径（`ADR-0004 D2.2/D2.3` 路径 A）**并存、非替代**——两条启动路径各自可自动化。[ADR-0004 R1]

---

## 7. 退出

- v5 测试机的程序停机协议为 semihosting **`SYS_EXIT`/`SYS_EXIT_EXTENDED`**（见 `§5.5`），**取代** exit port（`ADR-0004 D3`）。[ADR-0020 D8][ADR-0004 R2]
- exit port 在迁移完成前**过渡保留**；C1 step2 迁移完成后删除。[ADR-0020 D8][ADR-0020 D15][ADR-0004 R2]
