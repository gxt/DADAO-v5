# SPEC-179t: 启动链/BootROM/权限口径清理

**模块**：spec
**项目里程碑**：M10
**依赖**：`INTEG-046t`（已验证，Step5 启动链落地）、`INTEG-047t`（已验证，SBI DMA 契约）、`INTEG-045t`（已验证，cfxld/cfxst 删除）；决策源 **ADR-0043 D1–D15**（启动/BootROM/hmon/smon）、**ADR-0045 D1–D10**（两轴权限）、**ADR-0046 D1**（cg0–cg7 继续在 spec 完整定义；D6 的「cg7 例外删除」不再适用于 cg7，见约束 3）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景

Step5 启动链（`INTEG-046t`）与 cfx 指令清理（`INTEG-045t`）已落地/验证，但 `spec/` 正文仍停留在旧口径：

1. `spec/DADAO-12-SEE-主管系统运行环境.md` §2.1 的核内地址空间表没有 smon SRAM 行；cfx63 的 BootROM 仍记 64 KiB（`0xffff_ffff_0000`）。ADR-0043 D1/D4/D5 已确认：BootROM 256 KiB（`0xffff_fffc_0000`–`0xffff_ffff_ffff`，复位向量仍 `0xffff_ffff_0000`）、hmon/smon SRAM 各 64 KiB（`0x0fff_0000_0000` / `0x0bff_0000_0000`）、power 无 SRAM。
2. `DADAO-12` 仍保留 `cfxld`/`cfxst` 的指令行为说明（§5.1）、异常进入分支与伪代码（§5.2）、cg7 内部存储控制寄存器组（§3.8），以及附录中「cg7 按预留设计、cfxld/cfxst 未启用」的旧条目；reserved 列表在 §5.2/§5.3 伪代码与附录仍写作 `7–14`。**注**：`cg7` 不是 `cfxld/cfxst` 的附属控制，而是描述各 cfx 内部空间（§2.1 的起始/大小/性质）的共有寄存器组；首轮把它当「保留/删除」处理是错的，本返工改为**空间描述数组**（每 4 个 rc 一块、数组命名，见「用户返工裁定原话」与 A 方案裁定）。
3. `spec/Machine-01-测试机运行环境.md` 仍写「只启用 hypv 与 user、不启用 supv、不涉及 smon、bootrom 直接跳到 user」，与 Step5 的 power→hmon→smon 启动链不一致；BootROM 几何、hmon/smon SRAM、RAM 的 PA 0 别名也未写入。
4. `.tao/knowledge/MEMORY.md` 的测试机地址映射行仍用旧 RAM `0xffff_0000_0000`、BootROM 64 KiB、exit port；M1/M2 排除口径仍把 `cfxld`/`cfxst` 记为 `scope: excluded` 2 条。

本任务只做**口径清理 + 生成器机械支持**：把已实现/已确认的启动链、BootROM、SRAM、PA 0 别名、cfx 指令删除与 reserved 编号写入规范正文，并同步锁、台账、生成物；**不引入新架构决策**（cg7 空间描述的布局与**数组命名 + stride 4** 由用户 2026-10-31 裁定给定，本任务只落纸，并允许改投影器 `tools/spec/gen_cfx_aliases.py` 展开数组；不实现 QEMU/LLVM 消费端）。

## 目标（范围）

1. **DADAO-12 §2.1**：补 smon SRAM 行（`0x0bff_0000_0000`，64 KiB）；BootROM 改为 256 KiB、范围 `0xffff_fffc_0000`–`0xffff_ffff_ffff`；复位向量仍 `0xffff_ffff_0000`（镜像内偏移 `0x3_0000`）；说明 hmon/smon SRAM 与 power 无 SRAM；补「各 cfx 的内部空间由该 cfx 的 cg7（§3.8）描述，表内 start/size/类型必须与 cg7 一致」。
2. **DADAO-12 cg7（返工重点）**：把 §3.8 由「保留/内部存储控制」改为**内部空间描述寄存器**——每 4 个 rc 描述一个空间、`i=0..15` 共 16 块、正好用完 rc0–rc63；字段（存在+类型 one-hot / 42 位起始偏移 / 字节大小 / 属性位）见「接口/口径规范 §2」。表内**只用 4 行数组行**表达（`cfx_⟨cfxname⟩_space_{desc,start,size,attr}[i]`，`i=0..15`），**不再要求 64 行 `space0_*` 显式表**；`tools/spec/gen_cfx_aliases.py` 增加 stride 4 数组解析并展开为 12 cfxname × 4 字段 × 16 块 = 768 条别名。`cg7` 全部只读、写任意 rc ⇒ `CFXREG`；不再有 `space_count`/`space_index`/`block_sel`/`sram_addr`。同时删除 `cfxld`/`cfxst` 旧正文/异常流（该删除**保持**）；reserved 统一 `6–14、19–61`（修 §5.2/§5.3 伪代码、附录等旧 `7–14`）。
3. **Machine-01**：§1/§1.1/§2/§3/§6 与 Step5 一致——启用 hmon/smon、BootROM 256 KiB、启动链 power→hmon→smon、RAM/PA 0 别名口径；保留 legacy `-bios` 按 64 KiB 复位窗口装载的语义说明；§3 恢复 `cg0–cg7` 并说明 cg7 为内部空间描述（未实现空间以 `exists=0` 表示）。
4. **MEMORY.md**：旧 RAM `0xffff_0000_0000` → 当前 `0xFC00_0000_0000`（16 MiB，另有 PA 0 别名）；BootROM 64 KiB → 256 KiB；`cfxld`/`cfxst` 已删除，不再作为 `scope: excluded` 指令。
5. **锁/版本/附录/索引**：`manifests/spec-readonly.lock.toml` 的 DADAO-12、Machine-01 两册 sha256 同笔重算；版本与附录按现有互锁规则处理；**两份 cfx 别名生成物按生成器重生成**（`tools/spec/gen_cfx_aliases.py` 先支持 stride 4；cg7 别名由 0 条增至 12 cfxname × 4 字段 × 16 块 = **768 条**，`contracts/cfx-aliases.txt` 的 `regs` 由 662 增至 **1430**、行数 683 → **1451**）；不改 ADR（见「约束 3」）。

## 用户授权原话（原样落纸）

> **用户授权原话（逐字）**：
>
> > 可以，授权

> **主会话派单原话（原样落纸，授权范围以此为准）**：
>
> > 在 /mnt/tao/DADAO-v5，master 已含 INTEG-048t 任务书（仅任务书，未实现），工作树干净。创建 `SPEC-179t` 任务书：**启动链/BootROM/权限口径清理**。文件名放 `.tao/tasks/spec/`；先确认 179 未占用，若占用顺延。
> >
> > 用户已明确授权修改 spec：
> > > 可以，授权
> >
> > 授权范围（按此落纸，不要扩大）：
> > - `spec/DADAO-12-SEE-主管系统运行环境.md`
> > - `spec/Machine-01-测试机运行环境.md`
> > - `manifests/spec-readonly.lock.toml`
> > - `.tao/knowledge/MEMORY.md`（台账口径同步）
> > - 必要的 `spec/README.md`/索引/版本记录（仅当互锁/索引要求）
> >
> > 必须解决的口径缺口（以 ADR-0043、INTEG-046t/047t 实测为准）：
> > 1. `DADAO-12 §2.1`：补 smon SRAM 行（`0x0bff_0000_0000`，64 KiB）；BootROM 改为 256 KiB、范围 `0xffff_fffc_0000`–`0xffff_ffff_ffff`，复位向量仍 `0xffff_ffff_0000`；如需说明 hmon/smon SRAM。
> > 2. `DADAO-12`：删除 `cfxld/cfxst` 旧正文/异常流/`cg7` 内部存储控制描述（INTEG-045t 已删除指令）；reserved 统一 `6–14、19–61`（修 §955 等旧 `7–14`）。
> > 3. `Machine-01`：从“不启用 supv、不涉及 smon、bootrom 直接 user”改为与 Step5 一致（启用 hmon/smon；BootROM 256 KiB；启动链 power→hmon→smon；RAM/PA 0 别名口径；保留 legacy `-bios` 语义说明）。
> > 4. `MEMORY.md`：旧 RAM `0xffff_0000_0000` → 当前 `0xFC00_0000_0000`；BootROM 64 KiB → 256 KiB；`cfxld/cfxst` 已删除，不再作为 excluded 指令。
> > 5. 锁文件 sha256 同步；版本/附录/索引按现有互锁规则处理；**不引入新架构决策**，只把已实现/已确认口径写入正文。

> **授权边界**：以上原话只授权上列文件与**互锁/索引要求的机械同步**；不得据此修改 QEMU/LLVM/测试/契约语义，不得新增指令/寄存器，不得改 ADR 决策（A 方案另授权改投影器；`validate_cfx_vectors.py` 只扩展格式解析，不改期望值）。

> **用户返工裁定原话（2026-10-31，逐字落纸）**：
>
> > 用户已纠正：`cg7` 不能删除/保留；它描述当前 cfx 的内部空间（DADAO-12 §2.1 的起始、大小、性质）。
> >
> > 已确认 `cg7` 布局（写入任务书，作为返工目标）：
> > - 每 4 个 rc 描述一个空间，`i=0..15`，共 16 块；
> > - `rc4i+0`：bit0=`exists`；bit1=SRAM、bit2=ROM、bit3=MMIO、bit4=DRAM、bit5=OTHER（one-hot）；其余保留；
> > - `rc4i+1`：`start`，42 位内部偏移；完整地址=`(cfxha<<42)|start`；
> > - `rc4i+2`：`size`，字节数；
> > - `rc4i+3`：`attr`：bit0=R、bit1=W、bit2=X、bit3=cacheable、bit4=shareable、bit5=volatile/device；其余保留；
> > - `exists=0` 时 start/size/attr 读 0；`exists=1` 时类型位恰好一个为 1；
> > - `cg7` 全部只读，写任意 `cg7` rc ⇒ `CFXREG`；
> > - 16 块正好用完 rc0–rc63；不再使用 `space_count/index/block_sel/sram_addr`；
> > - `cfxld/cfxst` 仍然删除；`cg7` 只描述空间，不做传输控制。
>
> **裁定范围**：重写 cg7 的 spec 口径、本任务书，并允许投影器支持 stride 4；QEMU/`min_rom_probe_044t/045t` 的旧 cg7 语义为**后续任务**，不在本 spec 任务修（见「约束 3」）。本裁定不改 `cfxld/cfxst` 删除、不改 ADR、不改 §2.1 已确认的地址行。

> **用户 A 方案裁定（2026-10-31，主会话转述用户选择，逐字落纸）**：
>
> > 用户已选 **A 方案**：cg7 使用数组命名，允许修改生成器支持 stride 4：
> > - `cfx_<name>_space_desc[i]`
> > - `cfx_<name>_space_start[i]`
> > - `cfx_<name>_space_size[i]`
> > - `cfx_<name>_space_attr[i]`
> > - `i=0..15`，字段分别位于 `rc=4i+0/1/2/3`；
> > - 16×4×12 cfx = 768 条别名；
> > - `gen_cfx_aliases.py` 需支持 stride 4 数组解析；`contracts/cfx-aliases.txt` 与 `.tao/contracts/contract-cfx-aliases.md` 由生成器重生成；
> > - 不再要求 64 行 `space0_*` 显式表；接受表内数组写法，生成器负责展开；
> > - `cg7` 全部只读、写任意 rc ⇒ `CFXREG`；`exists=0` 时 start/size/attr 读 0；one-hot 类型；`cfxld/cfxst` 仍删除。
>
> **A 方案边界**：生成器只改投影器 `tools/spec/gen_cfx_aliases.py`（stride 4 解析 + 展开）；`tools/llvm/gen_cfx_alias_table.py` **不改**（复用投影器，展开后按 `count=1` 输出）。L1 门控 `check-cfx-vectors` 的消费者 `tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py` 必须同步支持 stride（否则新 rc 列 `4i+K` 解析即 FAIL），属**门控机械同步**。运行时表 `format=1` 无 stride 字段，768 条按 `count=1` + 字面下标登记，**LLVM 汇编端暂不可拼写**；QEMU/`min_rom_probe_044t/045t` 旧 cg7 与 LLVM 消费端 stride 支持均为**后续任务**（见约束 3）。

## 接口/口径规范（本任务真源）

### 1. DADAO-12 §2.1 地址表目标形态

`cfx num / cfx name / 起始地址 / 地址大小 / 空间类型` 表在现有 hmon、pmem、power 三行基础上改为：

| cfx num | cfx name | 起始地址 | 地址大小 | 空间类型 |
|:---:|------|------|------|------|
| 2 | smon | `0x0bff_0000_0000` | 64 KiB | SRAM |
| 3 | hmon | `0x0fff_0000_0000` | 64 KiB | SRAM |
| 17 | pmem | `0x47ff_0000_0000` | 64 KiB | SRAM |
| 63 | power | `0xffff_fffc_0000` | 256 KiB | BootROM |

说明段必须写清：

- `cfx_power_hypv_excp_vector = 0xffff_ffff_0000` 为硬件复位后的启动地址，位于 BootROM 内偏移 `0x3_0000`；BootROM 范围 `0xffff_fffc_0000`–`0xffff_ffff_ffff`（256 KiB），可由 CPU 直接取指执行；复位向量不变。
- `cfx2`（smon）/`cfx3`（hmon）的 SRAM 各 64 KiB；对应 S-mode/H-mode 异常向量默认等于各自起始地址；`cfx63`（power）不设 SRAM。
- 现有 `cfx_pmem` 64 KiB SRAM（内部偏移 `0x3ff_0000_0000`）与越界 `CFXMEM` 说明保持不变。
- 补一句与 cg7 的互锁：**各 cfx 的内部空间（起始偏移、字节大小、空间类型）由该 cfx 自身的 cg7（§3.8）描述**；本表每行必须与对应 cfx 的 cg7 某个空间块一致（`start = 起始地址 − (cfxha << 42)`、`size` 相等、类型对应）。校验示例：smon/hmon/pmem 的 `start` 均为 `0x3ff_0000_0000`；power 的 `start = 0x3ff_fffc_0000`（`0xffff_fffc_0000 − 0xfc00_0000_0000`）、`size = 0x4_0000`（256 KiB），`start + size = 2^42` 边界合法。
- **保留 `cfx_power` BootROM 的 `X=1` 说明**：power 的 BootROM 空间块 `attr` 必须含 `X=1`（复位向量位于该块内，CPU 直接取指执行）；smon/hmon/pmem 的 SRAM 块按各自异常向量取指需求给出 `X`。

### 2. DADAO-12 cg7 目标形态（返工重点）

**§3 开头**：恢复为 `cg0-cg7 为共有寄存器设计，不同的核芯功能扩展设计规范相同。`（cg7 不是保留组）。

**§3.8 标题**：`### 3.8 cg7 - 内部空间描述寄存器`。

**§3.8 正文（必须逐条写清）**：

- 每个核芯功能扩展用 cg7 描述自身的核内空间（§2.1 的 42 位内部地址空间）。每 **4 个 rc 描述一个空间**，空间块编号 `i = 0..15`，共 **16 块**，正好用完 `rc0–rc63`（`rc = 4i + 0..3`）。
- `rc4i+0`（描述字）：`bit0 = exists`；`bit1 = SRAM`、`bit2 = ROM`、`bit3 = MMIO`、`bit4 = DRAM`、`bit5 = OTHER`（存在时 one-hot）；其余位保留、读 0。
- `rc4i+1`（start）：42 位内部起始偏移；该空间的完整核内地址 = `(cfxha << 42) | start`。
- `rc4i+2`（size）：空间字节数；须满足 `start + size ≤ 2^42`。
- `rc4i+3`（attr）：`bit0 = R`、`bit1 = W`、`bit2 = X`、`bit3 = cacheable`、`bit4 = shareable`、`bit5 = volatile/device`；其余位保留、读 0。
- `exists = 0` 时 `start`/`size`/`attr` 读 0；`exists = 1` 时类型位恰好一个为 1（实现须静态保证，不存在软件可写的非法编码）。
- 未实现的空间填 `exists = 0`；实现须静态给出 16 块表。
- cg7 **全部只读**；对任意 cg7 rc 的写访问触发 `CFXREG`。
- 不设 `space_count`/`space_index`/`block_sel`/`sram_addr` 之类辅助寄存器；cg7 只描述空间，**不做传输控制**（`cfxld`/`cfxst` 仍为已删除指令）。

**§3.8 寄存器表（数组行 + 生成器 stride 4，硬约束）**：

- 表头沿用本文其它寄存器表：`| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |`；表前、表后留空行（生成器按空行断表）。
- **只用 4 行数组行**（不得展开成 64 行、不得用 `0-63` 区间行）：
  - `| 7 | 4i+0 | space desc | cfx_⟨cfxname⟩_space_desc[i] | HW | RO | ... |`
  - `| 7 | 4i+1 | space start | cfx_⟨cfxname⟩_space_start[i] | HW | RO | ... |`
  - `| 7 | 4i+2 | space size | cfx_⟨cfxname⟩_space_size[i] | HW | RO | ... |`
  - `| 7 | 4i+3 | space attr | cfx_⟨cfxname⟩_space_attr[i] | HW | RO | ... |`
- rc 列必须字面写 `4i+0`…`4i+3`（生成器按「`Ni+K` + regname 以 `[i]` 结尾」识别 stride 4），`i=0..15` 在说明列与正文写清；regname 后缀必须是 `[i]`。
- 初始值统一 `HW`、访问统一 `RO`（不得出现 `RW`）。
- 单元格内**不得出现 `|`**（会截断生成器解析），位域用「bit0=…；bit1=…」表述。
- 可另附「字段定义表」（4 行，表头不以 `cg`/`rc` 开头，且与寄存器表之间留空行），说明位域含义；该表不会被别名生成器解析。
- **生成器契约（`tools/spec/gen_cfx_aliases.py`）**：识别 rc=`m*i+k`、regname 以 `[i]` 结尾的行，展开为 `64/m` 条（本例 m=4、k=0..3 ⇒ 16 条/字段）：别名 `<base>[n]`、rc=`m*n+k`（n=0..15）。`parse_register_tables` 记录 stride/count，`build_register_aliases` 对通用数组输出**具体数字 rc**（供 `gen_cfx_alias_table.py` 原样复用），md 侧仍按模板行（rc 列 `4i+K`）呈现。既有 `[0..63]`/`[0..N−1]` 数组行为不得回退。

**§5.1 / §5.2 / §5.3（保持首轮结论）**：

- §5.1：指令清单改为 `trap`/`escape`/`cfx2rd`/`cfx2rc`；删除 `cfxld`/`cfxst` 及「当前未启用」括注；reserved 保持 `6–14、19–61`。
- §5.2 步骤 1：删除「`cfxld/cfxst` 访问 cfx 内部存储块（待启用），仅触发 CFXMEM」子条；保留 `trap`/`cfx2rd`/`cfx2rc` 与 reserved/CFXPERM 判定。
- §5.2 伪代码：指令集合改为 `{TRAP, ESCAPE, CFX2RD, CFX2RC}`；reserved 集合改为 `{6..14, 19..61}`；删除 `elif instruction ∈ {CFXLD, CFXST}` 分支及其注释。
- §5.3 伪代码：reserved 集合改为 `{6..14, 19..61}`。
- 附录 `0.7.3-rc`：把 `7–14` 改为 `6–14`；cg7 条目改为「cg7 改为内部空间描述寄存器：每 4 个 rc 描述一个内部空间（存在+类型 one-hot / 42 位起始偏移 / 字节大小 / R-W-X-cacheable-shareable-volatile 属性），16 块用完 rc0–rc63；寄存器按数组 `space_{desc,start,size,attr}[i]` 命名（`i=0..15`，`rc=4i+0..3`），全部只读、写触发 CFXREG；不再使用块选择与块内地址寄存器」，**不得再写「cg7 保留」**；保留「核内存储块批量传输指令的行为说明与异常进入分支/伪代码已删除」条目（用「核内存储块批量传输指令」表述，不写指令助记符，以与验收 2 的 0 命中一致）；保留 §2.1 地址空间/BootROM 变更条目。**附录条目不得出现任务号/ADR/ISS 号、不得用表格。**

### 3. Machine-01 目标形态

**§1（复位行）**：

> 硬件复位后的启动地址为 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`，位于 256 KiB BootROM 内，镜像偏移 `0x3_0000`），该地址可由 CPU 直接取指并执行。[DADAO-12 §2.1 核内地址空间]

**§1.1（测试机约定）**：

- 引言改为「上游 `DADAO-12` 给出核内地址空间模型；下列为测试机约定的具体划分与用途」，删除「上游 `spec/` 只规定 `cfxha 63` 的复位向量」的旧前提。
- 表：RAM 行保持 `0xFC00_0000_0000` / 16 MiB / cfxha 63；BootROM 行改为 `0xffff_fffc_0000` / 256 KiB / cfxha 63，说明含复位向量 `0xffff_ffff_0000`（镜像内偏移 `0x3_0000`）与 legacy `-bios` 64 KiB 复位窗口；新增 hmon SRAM（`0x0fff_0000_0000`，64 KiB，cfxha 3）、smon SRAM（`0x0bff_0000_0000`，64 KiB，cfxha 2）两行；cfx_pmem SRAM 行不变。
- 新增 **PA 0 别名（测试机约定）** 条目：现有 16 MiB DRAM 在物理地址 `[0, 16 MiB)` 另设别名，与 `0xFC00_0000_0000` 的 16 MiB DRAM 指向同一存储；供 PTBR=0 的第一张页表使用；PTW 页表读与 `cfx_pmem` DMA 的 PA 合法性检查同时接受 `[0, 16 MiB)` 与 `[0xFC00_0000_0000, 0xFC00_0000_0000 + 16 MiB)`；BootROM 仍只读，其余 PA 仍按 `PA_FAULT`/未映射处理；CPU 地址侧 `addr[47:42] = 0` 的内存窗口仍由 `ptw_enable` 控制。
- 现有「RAM 基址口径」「C1 两步过渡 + 基址迁移」要点保留；把 §1.1 历史句中的旧 RAM 数字 `0xffff_0000_0000` 改为「旧 RAM 段（已删）」，避免旧口径残留；BootROM 尺寸统一写 256 KiB。

**§2（运行模式）**：

> v5 测试机启用 `hypv`、`supv` 与 `user`；`jail` 不启用。`hmon`（cfx3）承载 hypv 异常，`smon`（cfx2）承载 supv 异常。
>
> 启动链为 power（hypv/cfx63）→ hmon（hypv/cfx3）→ smon（supv/cfx2）：power 从 BootROM 装载 hmon 并 `trap` 移交；hmon 配置 smon 的 S-mode 向量/权限后 `trap` 移交；smon 建立第一张页表、开启 PTW 并接管运行期。legacy `-bios` 路径的 64 KiB 复位窗口语义不变。

删除「只启用 hypv 与 user」「不启用 supv」「不涉及 smon」「bootrom 直接跳到 user」旧句。

**§3（cfx 与权限）**：

- 恢复为 `cg0–cg7` 与 `cg4–cg7`（删除 `cg0–cg6`/`cg4–cg6` 与「cg7 保留」）；补一句「`cg7` 为内部空间描述寄存器（DADAO-12 §3.8）：每 4 个 rc 描述一个内部空间，字段按**数组** `space_{desc,start,size,attr}[i]`（`i=0..15`）定义，未实现空间以 `exists=0` 表示，全部只读」。
- 现有 cfx 实现范围、两轴权限、CFXPERM/CFXESC、reserved `6–14`/`19–61` 说明保持不变。

**§6（加载与 bootrom）**：

- BootROM 几何：唯一非易失 BootROM 256 KiB（`0xffff_fffc_0000`–`0xffff_ffff_ffff`）；复位向量不变 `0xffff_ffff_0000`（镜像内偏移 `0x3_0000`）。
- 装载语义：256 KiB BootROM 经 bootrom 镜像装载路径（机器属性 `bootrom-image`）装入；legacy `-bios` 仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载，既有探针/e2e 语义不变。
- 模式移交：power→hmon→smon（同 §2），smon 在 supv/cfx2 建立页表/PTW 并接管运行期。
- 并存关系：`-bios` bootrom 路径与 M4 ELF 单镜像路径并存、非替代，保持不变。

**附录 `0.3.2-rc`**：补启动链/BootROM 256 KiB/hmon-smon SRAM、PA 0 别名、cg7 内部空间描述（cg0–cg7 共有、16 块数组 `space_{desc,start,size,attr}[i]`、未实现空间 `exists=0`）、legacy `-bios` 语义四条；不得出现任务号/ADR/ISS 号。

### 4. MEMORY.md 目标形态

- 第 3 行「测试机地址映射 / 复位值」：BootROM `0xffff_fffc_0000`（256 KiB；复位向量 `0xffff_ffff_0000`，镜像内偏移 `0x3_0000`）、RAM `0xFC00_0000_0000`（16 MiB，另有 PA 0 别名）、exit port 已删；复位 PC=`rb0`=复位向量；其余复位值说明不变。
- 第 6 行「M1/M2 排除口径」：`excluded` 由 **2 条**改为 **0 条**（`cfxld`/`cfxst` 已删除；`crii` 格式撤销）；`m1`/`fp`/`m9` 口径不变；可补 `INTEG-045t` 作为删除依据。
- 第 44 行订正说明：改为「现行口径为浮点已实现、`fence`/LR-SC 已实现、`scope: excluded` 现为 0 条（`cfxld`/`cfxst` 已删除）」。
- 不新增 `.work/` 具体路径引用；不改 MEMORY 的 ADR 指针结构。

### 5. 版本、附录、锁与生成物

- **版本不动**：`DADAO-12` 册头保持 `0.7.3-rc`（`check-spec-changelog` 的 `see-sbi` 互锁组要求与 `DADAO-22` 一致，当前 `DADAO-22` 为 `0.7.3-rc`）；`Machine-01` 保持 `0.3.2-rc`（独立组）。**不得只给 DADAO-12 升版**。
- **附录**：在各自现有顶部 `-rc` 段追加条目，不新开空段；条目禁止任务号/ADR/ISS 号、禁止表格。
- **锁**：改完两册后 `sha256sum` 重算，更新 `manifests/spec-readonly.lock.toml` 对应 `[[spec]]` 的 `sha256`；在同文件注释区追加 1 条日期/任务/授权原话摘要/改动范围说明（沿用现有注释体例）。
- **生成物（互锁索引，非语义改写）**：cg7 空间描述数组写入后，以下两份自动生成投影必须同笔重生成，禁止手改：
  - `.tao/contracts/contract-cfx-aliases.md`（`python3 tools/spec/gen_cfx_aliases.py`）
  - `contracts/cfx-aliases.txt`（`python3 tools/llvm/gen_cfx_alias_table.py`）
  预期变化：cg7 由 0 条增至 **12 cfxname × 4 字段 × 16 块 = 768 条**寄存器别名；`contracts/cfx-aliases.txt` 头注释 `regs=` 由 `662` 增至 **1430**，行数由 683 增至 **1451**（以实测为准）；`.tao/contracts/contract-cfx-aliases.md` 的 §2.1 模板表**只增加 4 行数组模板**（不得出现 64 行 `space0_*`），统计改为展开后实际条数（通用 1392 + 专有 38 = 1430，须与 txt `regs=` 相等）；其余条目（其它 cg 与专有表）逐字不变，仅 `DADAO-12:<行号>` 引用随正文增删整体位移。
- **允许修改的生成器（唯一）**：`tools/spec/gen_cfx_aliases.py` 增加 stride 4 数组解析与展开（识别 rc=`4i+K`、regname 以 `[i]` 结尾；展开 16 条/字段，别名 `<base>[n]`、rc=`4n+K`；md 侧保留 4 行模板行并修正统计）。`tools/llvm/gen_cfx_alias_table.py` **不改**（其 `build_register_aliases` 调用方看到的是展开后的具体 rc）。
- **运行时表格式不变（format=1）与已知下游缺口**：`contracts/cfx-aliases.txt` 只有连续 `rc-base/rc-count`，stride 4 只能按 **16 条 `count=1`** 展开、名称保留字面下标（如 `reg cfx_umon_space_desc[3] 0 7 12 1 canonical`）。LLVM 汇编端目前仅在 `rc-count>1` 时接受 `name[N]` 下标 ⇒ 这 768 个名字**暂不可在汇编中拼写**（打印端 `getCfxRegName` 输出与登记名一致）。该缺口属**后续任务**，本任务不改 `components/**`、不重建、不为此扩表格式。
- **L1 门控机械同步**：`tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py` 的 `parse_rc`/`resolve_reg` 必须支持 `m*i+k`（返回 `lo/count/stride`，下标解析 `rc=lo+n*stride`；非数组 stride=1），否则 md 新 rc 列 `4i+K` 使其 `check-cfx-vectors` 直接 FAIL。该文件仅做格式解析扩展，不改任何向量期望值。
- **spec/README.md**：版本号不变、分册职责不变 ⇒ 预期**不改**；仅当 `check-spec-refs`/索引表因节号/引用互锁要求时必须改，并在完成区写明理由。

## 修改文件范围

**用户授权范围内（必须改）**：

- `spec/DADAO-12-SEE-主管系统运行环境.md`
- `spec/Machine-01-测试机运行环境.md`
- `manifests/spec-readonly.lock.toml`
- `.tao/knowledge/MEMORY.md`

**A 方案授权的生成器（唯一允许修改的脚本）**：

- `tools/spec/gen_cfx_aliases.py`（stride 4 数组解析 + 展开 + md 统计）

**互锁/索引要求的机械同步（非语义改写）**：

- `.tao/contracts/contract-cfx-aliases.md`（生成器重生成）
- `contracts/cfx-aliases.txt`（生成器重生成）
- `tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`（`check-cfx-vectors` 消费者，仅扩展 `m*i+k` 解析；不改向量期望值）

**流程文件（按任务状态机）**：

- 本任务书（完成区 + 状态）
- `.tao/knowledge/milestones.md`（本任务流水行状态）

**明确不动**：`components/qemu/**`、`components/llvm-project/**`、`tools/testcases/**`、`tests/inst/**`、`tests/shared/bootrom/**`（含 `min_rom_probe_044t/045t`）、`contracts/opcodes.yaml`、`.tao/adr/**`、`.tao/contracts/contract-see.md`（已含 `cg0–cg7`，本任务不改）、`spec/README.md`（除非互锁要求）、`tools/llvm/gen_cfx_alias_table.py`（**不改**）、`tools/spec/check_cfx_aliases.py`（不改）。`INTEG-048t` 任务书不碰、不实现。文件集 = 首轮 8 项 + 投影器 + 门控校验器 = **10 项**。

## 约束

1. **只做口径清理 + 生成器机械支持**：不改 QEMU/测试/契约**语义**，不新增指令；cg7 的 rc0–rc63 由用户 2026-10-31 裁定重新定义为**内部空间描述**（复用既有 cg7，不是新增寄存器组），表内用 **4 行数组行**（数组命名 + stride 4）表达；不改 ADR 决策；`cfxld/cfxst` 只删残留，不讨论替代指令。
2. **授权边界**：只改上列文件；`spec/` 改动必须与授权原话同笔落锁；生成器只允许改 `tools/spec/gen_cfx_aliases.py`，校验器只允许扩展格式解析；超出范围的文件一律不动，发现必须改时停下报告，不自行扩大。
3. **cg7 的已知滞后（后续任务，不在本任务修）**：QEMU 仍按旧语义实现 cg7（`sram_block_sel`/`sram_addr`）、`min_rom_probe_044t/045t` 仍测试旧 cg7、`contract-see.md` 仍只写 `cg0–cg7`（无空间块）；运行时别名表 `format=1` 无 stride 字段，768 条 cg7 别名按 `count=1` + 字面下标登记，**LLVM 汇编端暂不可拼写**（消费端 stride 支持为后续任务）。本任务按用户裁定**只改 spec 口径 + 生成器 + 生成物**，这些实现/测试/契约投影**不跟改**，在完成区「遗留问题」逐条登记，不得顺手改。
   - 但 **spec 与生成物必须自洽**：`.tao/contracts/contract-cfx-aliases.md`、`contracts/cfx-aliases.txt` 必须由生成器从新 spec 表重生成且 `--verify`/`--check` 通过；不得出现「spec 有 4 行数组、别名表仍 0 条 cg7」之类的中间态。
   - ADR 关系：本布局与 ADR-0046 **D1**（cg0–cg7 继续在 spec 完整定义）一致；D6「cg7 SRAM 控制例外删除」不再适用。**不新建/不修改 ADR**；若需 ADR，由主会话先与用户逐条确认后另立。
4. **生成物纪律**：两份 cfx 别名投影只由生成器写入；生成后 `make check-cfx-aliases check-cfx-alias-table check-cfx-vectors` 必须 rc=0；不得为过门控手改生成物，也不得靠手写 64 行绕过生成器。
5. **版本互锁**：DADAO-12 不单独升版；附录条目禁止任务号/ADR/ISS 号；新条目追加在现有 `-rc` 段。
6. **门控**：`make check` 必须 rc=0；另跑 `check-spec-readonly`/`check-spec-changelog`/`check-contracts-dir`/`check-knowledge-refs`/`check-milestones-fresh`/`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-vectors`，以及 `check-spec-refs`/`check-asm-prose`（若适用）。不跑长构建/夜跑；`check-cfx-alias-install` 非 L1，若跑 L2 需先 `make install-cfx-aliases`（数据复制，非重建）。
7. **证据**：`.work/evidence/<任务ID>/run.sh` 一键复跑；至少含「注入旧口径 token → FAIL → 删除/还原 → PASS」一项可达 FAIL 自检，还原用 `cp`+md5，**禁用** `git checkout/restore/stash/show`。长日志落 `.work/log/spec/`，任务书只放结论 + 通配路径。
8. **临时目录**：`/tmp/opencode/SPEC-179t/`；仓库内不得留 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`.bak`。
9. **提交**：本任务实现完成由 engineer 填完成区并置 `待验收`；提交由 architect 执行（本任务分支内，显式 staging，禁 `push`）。

## 验收标准

1. **改动文件集精确**：`git diff --name-only master...HEAD`（返工提交后；工作树阶段用 `git status --porcelain -uall`）仅含 **10 项**：两册 spec、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/MEMORY.md`、两份生成物、`tools/spec/gen_cfx_aliases.py`、`tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`、本任务书、`.tao/knowledge/milestones.md`；无 `components/**`、`tests/inst/**`、`tools/testcases/**`、`tests/shared/bootrom/**`、`contracts/opcodes.yaml`、`.tao/adr/**`、`tools/llvm/gen_cfx_alias_table.py` 改动；`contract-see.md`、`spec/README.md` 零改动（除非互锁）。
2. **DADAO-12 旧口径零残留 + cg7 数组表到位**：
   - `grep -nE 'cfxld|cfxst|CFXLD|CFXST' spec/DADAO-12-*.md` ⇒ 0；
   - `grep -nE '7[–.]14|\{7\.\.14|(^|[^0-9])7-14' spec/DADAO-12-*.md` ⇒ 0（「非数字前导」变体：排除附录历史日期 `2026-07-14` 的假阳性；旧编号 `7–14`/`7.14`/`{7..14}` 仍可达 FAIL）；
   - `grep -nE 'sram_block_sel|sram_addr|内部存储控制|space_count|space_index|block_sel' spec/DADAO-12-*.md` ⇒ 0；
   - `grep -nE 'cg0-cg6|cg7 保留|cg7 - 保留' spec/DADAO-12-*.md` ⇒ 0；`grep -n 'cg0-cg7 为共有寄存器设计'` ⇒ =1；
   - `§3.8` 表：`grep -cE '^\| 7 \| 4i\+[0-3] \|' spec/DADAO-12-*.md` ⇒ **4**，rc 恰为 `4i+0/1/2/3` 各一次；`grep -cE '^\| 7 \| [0-9]+ \|'` ⇒ **0**（无 64 行展开）、`grep -cE 'space[0-9]+_(desc|start|size|attr)'` ⇒ **0**（无 `space0_*` 显式名）；4 行 regname 分别含 `space_desc[i]`/`space_start[i]`/`space_size[i]`/`space_attr[i]`；全部 `| 7 |` 行 `访问` 列 `RO`（`grep -E '^\| 7 \|' | grep -c 'RW'` ⇒ 0）；
   - `grep -nE 'exists|one-hot|volatile|shareable|cacheable|\(cfxha << 42\)' spec/DADAO-12-*.md` ⇒ 各 ≥1；`grep -n 'CFXREG'` 在 §3.8 段内 ⇒ ≥1（写 cg7 ⇒ CFXREG）；`grep -nE 'i ?= ?0\.\.15'` ⇒ ≥1；`grep -n 'X=1'` ⇒ ≥1（power BootROM 可执行说明保留）；
   - `grep -n '0x0bff_0000_0000' spec/DADAO-12-*.md` ⇒ ≥1；`grep -n '0xffff_fffc_0000' spec/DADAO-12-*.md` ⇒ ≥1；`grep -n '0xffff_ffff_0000'` ⇒ ≥1（复位向量）。
3. **Machine-01 旧口径零残留 + cg7 口径**：
   - `grep -nE '不启用.*supv|不涉及.*smon|直接跳到.*user' spec/Machine-01-*.md` ⇒ 0；
   - `grep -n '0xffff_0000_0000' spec/Machine-01-*.md` ⇒ 0；
   - `grep -nE 'boot ROM.*64 KiB|BootROM.*64 KiB|bootrom.*64 KiB' spec/Machine-01-*.md` ⇒ 0（legacy `-bios` 的 64 KiB 复位窗口说明允许保留，但不得与 BootROM 尺寸混淆）；
   - `grep -n 'cg0–cg7' spec/Machine-01-*.md` ⇒ ≥1，`grep -nE 'cg0–cg6|cg7 保留' spec/Machine-01-*.md` ⇒ 0；`grep -nE 'exists=0|内部空间描述' spec/Machine-01-*.md` ⇒ ≥1；`grep -nE 'space_(desc|start|size|attr)\[i\]|数组' spec/Machine-01-*.md` ⇒ ≥1；
   - `grep -n '0x0bff_0000_0000'`/`0x0fff_0000_0000`/`0xffff_fffc_0000`/`PA 0 别名` ⇒ 均 ≥1。
4. **MEMORY 口径**：第 3/6/44 行与目标形态一致；`grep -n '0xffff_0000_0000' .tao/knowledge/MEMORY.md` ⇒ 0；`grep -nE 'excluded.*2 条|cfxld.*ILLI|cfxst.*ILLI' .tao/knowledge/MEMORY.md` ⇒ 0。
5. **锁与版本**：`sha256sum` 两册值 == `manifests/spec-readonly.lock.toml` 对应值；`make check-spec-readonly` rc=0；DADAO-12 册头/附录顶部仍 `0.7.3-rc`，Machine-01 仍 `0.3.2-rc`；`make check-spec-changelog` rc=0（互锁、逆序、无任务号/表格）。
6. **生成器 stride 4 自检 + 生成物一致**：
   - `python3 tools/spec/gen_cfx_aliases.py --verify` rc=0；`python3 tools/llvm/gen_cfx_alias_table.py --check` rc=0；`make check-cfx-aliases check-cfx-alias-table check-cfx-vectors` rc=0；
   - `contracts/cfx-aliases.txt`：`reg .*_space_(desc|start|size|attr)\[[0-9]+\] ` 每字段 12×16=192、合计 **768**；`regs=` == **1430**；行数 == **1451**（以实测为准，不符须写明原因）；
   - **rc 映射逐条断言**（脚本，全 768 条）：`space_desc[i]` ⇒ rc=`4i`、`space_start[i]` ⇒ `4i+1`、`space_size[i]` ⇒ `4i+2`、`space_attr[i]` ⇒ `4i+3`，`i=0..15`、全部 `count=1`；旧 cg7（`sram_block_sel`/`sram_addr`）0 条；
   - `.tao/contracts/contract-cfx-aliases.md`：§2.1 恰有 4 行 `space_*[i]` 模板（无 64 行 `space0_*`）；统计条数 == **1430**（通用 1392 + 专有 38）；其余条目与 master 逐字一致（除新增 4 行、统计、`DADAO-12:<行号>` 位移）；
   - **生成器幂等**：连跑两次生成器，两份生成物 `md5sum` 不变；
   - **生成器可达 FAIL**：临时把 §3.8 某行 `4i+1` 改成 `4i+2`（`cp` 备份）⇒ `--verify` 或 rc 映射断言 FAIL；还原（md5 一致）后回绿；
   - `tools/llvm/gen_cfx_alias_table.py` **零改动**；两份生成物**不得手改**（`git diff` 中出现非生成器产出的行 ⇒ FAIL）。
   - `validate_cfx_vectors.py` 自检：直接调用其 `load_aliases()/resolve_reg()`，断言 `cfx_umon_space_desc[5]` ⇒ `(0,7,20)`、`cfx_power_space_attr[15]` ⇒ `(63,7,63)`、旧连续数组（`cfx_pmem_start[63]` ⇒ rc 63）不回归；注入错误 stride 后断言 FAIL。
7. **全量 L1**：`make check` rc=0；`check-spec-readonly`、`check-spec-changelog`、`check-contracts-dir`、`check-knowledge-refs`、`check-milestones-fresh`、`check-spec-refs`、`check-asm-prose`、`check-cfx-vectors` 各自 rc=0。
8. **证据脚本**：`bash .work/evidence/<任务ID>/run.sh` rc=0，含至少 1 项注入→FAIL→还原→PASS（首选验收 6 的 stride 注入）；输出与完成区逐条一致。
9. **完成区**：≤30 行；状态 `待验收`；`milestones.md` 流水行状态同步；无临时残留。

## 下发前预检（5 项）

1. **任务书内部一致**：目标/接口规范/验收/修改文件范围逐条对应；依赖 `INTEG-045t`/`046t`/`047t` 均 `已验证`；cg7 空间描述布局（16 块 × 4 rc）与 **A 方案数组命名 + stride 4** 由用户 2026-10-31 裁定、已逐字落纸；生成器只改投影器、validator 仅扩展解析；QEMU/测试/contract-see/LLVM 汇编端的旧 cg7 与 stride 缺口在约束 3 与「遗留问题」显式登记为后续任务，不作为本任务验收失败。结论：**PASS**。
2. **验证手段前置实际可用（本轮实测）**：`make check` 基线 rc=0（日志 `.work/log/spec/SPEC-179t-precheck-*.log`）；`make check-spec-readonly check-spec-changelog check-cfx-aliases check-cfx-alias-table check-cfx-vectors check-knowledge-refs check-contracts-dir check-milestones-fresh check-spec-refs` 基线 rc=0；`tools/spec/gen_cfx_aliases.py`、`tools/llvm/gen_cfx_alias_table.py`、`tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`、`tools/infra/check_spec_readonly.py` 均存在；`gen_cfx_alias_table.py` 通过 `from tools.spec.gen_cfx_aliases import ...` 复用投影器（改投影器即生效，脚本本身无需改）。结论：**PASS**。
3. **验收逐条可跑性**：
   - 验收 1/2/3/4/5/6/7 **现在可跑**（spec 改完后在同任务内闭环；基线命令已绿；验收 6 的 `768`/`regs=1430`/行数 1451 为预估值，以生成器实测为准，不符须写明原因；stride 自检须先生成器实现）；
   - 验收 8 的 `.work/evidence/<任务ID>/run.sh` **随任务产物落地后可跑**（不是外部阻塞）；
   - 无 BLOCKED 项；cg7 旧实现/测试滞后与 LLVM 汇编端不可拼写属**已知遗留**，不影响本任务 spec 门控。结论：**PASS（无 BLOCKED）**。
4. **与 contracts/、tests/inst/ 一致**：`contract-see.md` 已含 256 KiB BootROM / hmon-smon SRAM / PA 0 别名与 `cg0–cg7`（未描述空间块，遗留）；`contract-elf.md` 已含 256 KiB BootROM 几何；`tests/inst/**` 无 `cfxld`/`cfxst`（INTEG-045t 已删）；`contracts/cfx-aliases.txt` 与 `.tao/contracts/contract-cfx-aliases.md` 需按新 cg7 数组重生成（互锁要求，预计 768 条新增）；`tests/inst` 向量不引用 cg7 别名（已 grep 确认），validator 扩展不改变任何期望值。结论：**PASS**；QEMU/044t/045t 旧 cg7、`contract-see.md` 块级缺失、LLVM 汇编端 stride 登记为遗留，不在本任务改。
5. **拟改文件 × `spec/` 清单**：命中 2 册 = `spec/DADAO-12-…`、`spec/Machine-01-…`；用户授权原话「可以，授权」+ 派单范围 + 本次返工裁定（cg7 空间描述）+ **A 方案裁定（数组命名/stride 4/允许改生成器）** 已逐字落纸于上节 ⇒ **不构成 BLOCKED**。`manifests/spec-readonly.lock.toml`、`.tao/knowledge/MEMORY.md`、`.tao/contracts/contract-cfx-aliases.md`、`contracts/cfx-aliases.txt`、`tools/spec/gen_cfx_aliases.py`、`tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py` 均不在 `spec/` 清单；`spec/README.md` 预期不改；`tools/llvm/gen_cfx_alias_table.py` 不改。结论：**PASS**。

## 完成区

**测试结果**：通过 72/72（`bash .work/evidence/SPEC-179t/run.sh` rc=0）；`make check` rc=0（`repository checks (L1): PASS`）；`check-spec-readonly`/`check-spec-changelog`/`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-vectors`/`check-spec-refs`/`check-contracts-dir`/`check-knowledge-refs`/`check-milestones-fresh`/`check-asm-prose` 逐个 rc=0；`check-lit` 159/159 PASS（前置 `make install-cfx-aliases` rc=0、`check-cfx-alias-install` rc=0）。
**修改文件**：10 项——`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/Machine-01-测试机运行环境.md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/MEMORY.md`、`.tao/contracts/contract-cfx-aliases.md`（生成）、`contracts/cfx-aliases.txt`（生成）、`tools/spec/gen_cfx_aliases.py`、`tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`、本任务书、`.tao/knowledge/milestones.md`。
**验收结果**（真实输出）：
- §3.8 数组行 `grep -cE '^\| 7 \| 4i\+[0-3] \|'` = 4；数字 rc 行、`space0_*`、行内 `RW` 均 0；旧 token（`cfxld|cfxst`、`7–14`、`sram_block_sel|sram_addr|内部存储控制|space_count|space_index|block_sel`、`cg0-cg6|cg7 保留`）均 0；`cg0-cg7 为共有寄存器设计` = 1。
- 生成物：cg7 空间别名 768 条（desc/start/size/attr 各 192），rc=4i+0..3 全 768 条逐条断言 errors=0；`contracts/cfx-aliases.txt` `scalars=12 regs=1430`、1451 行；md 统计 1430（通用 1392 + 专有 38）、§2.1 恰 4 行模板；两份生成器连跑两次 md5 不变。
- validator：`cfx_umon_space_desc[5]`→(0,7,20)、`cfx_power_space_attr[15]`→(63,7,63)、`cfx_pmem_start[63]`→(17,12,63)；越界/缺下标抛 `ValueError`。
- 锁：两册 sha256 实测 == 锁值（`d55fff18…48fa05` / `8a3c56ac…cb48febf`）；版本未动（`0.7.3-rc` / `0.3.2-rc`）。
- 反例：§3.8 `4i+1`→`4i+2` 注入后 `gen_cfx_aliases.py --verify` rc=1，`cp` 还原 md5 一致后 rc=0；md 注入 `5i+0` 后 validator 抛 `bad rc stride`。
**新发现/坑**：cg7 数组行不得展开成 `space0_*` 64 行；生成器按「`Ni+K` + regname `[i]` 后缀」识别 stride，md 侧保留模板行但统计须按 `expand_count` 求和（模板 56 ≠ 展开 116 名/字段组）。
**遗留问题**：
1. QEMU 仍按旧语义实现 cg7（块选择/块内地址）；`min_rom_probe_044t/045t` 仍测旧 cg7；`contract-see.md` 仍只写 `cg0–cg7`（无空间块）——后续任务。
2. 运行时表 `format=1` 无 stride 字段：768 条按 `count=1` + 字面下标登记，LLVM 汇编端暂不可拼写（消费端支持需改 `components/llvm-project/**` 并重建）——后续任务。
3. §2.1「S/H-mode 异常向量默认等于 SRAM 起始地址」与 `cg2`/`cg3` 的 `rc10 excp_vector` 初值 0 仍不一致（本轮未改寄存器初值表）。
4. 各 cfx 异常表 CFXMEM 措辞「访问核内地址空间或内部存储块故障」跨册统一未在本次范围。

## 审阅记录

> 轮次口径：按「实现轮」编号（第 1 轮初版、第 2 轮 cg7 空间描述返工、第 3 轮 A 方案数组返工）；reviewer 标题注明第几次验收（当前第 2 次 = 第 3 轮）。以下按时间先后排列。

#### 第 1 轮 engineer 自审

逐行核对了 `git diff -- spec/`（DADAO-12 / Machine-01 全文）与两个生成物差分、锁注释、MEMORY 三行；判决：**可交付**（findings 见下表，1 项登记遗留）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 验收 2 的 `7[–.-]14` 正则命中附录历史日期「2026-07-14」 | ❌不修（不改无关历史日期；属任务书验收式与史实冲突） | 证据脚本用 `7[–.]14\|{7\.\.14}\|(^|[^0-9])7-14` | C2 PASS；C14a 注入 `7–14` 后 FAIL、还原回绿 |
| F2 附录需写 `cfxld`/`cfxst` 字样与验收 2「全文 0 命中」冲突 | ✅已修（按验收执行） | 附录 0.7.3-rc 与 0.7.2 条目改述为「核内存储块批量传输指令」 | C1 残留 0；C14a 注入后 FAIL |
| F3 `BootROM` 与 legacy `64 KiB` 同句命中验收 3 混淆正则 | ✅已修 | Machine-01 §2/§6/附录分行或分条 | C5c 残留 0 |
| F4 §2.1 新句「S/H-mode 向量默认等于起始地址」与 cg2/cg3 `rc10` 初值 0 不一致 | ⏸延后（任务书要求写入，修寄存器初值表越界） | —（登记「遗留问题 2」） | 任务书遗留 2 |
| F5 生成物 md 行号引用随删行位移，易被误判为语义漂移 | ✅已修（生成器重生成） | `gen_cfx_aliases.py` / `gen_cfx_alias_table.py` 重跑 | C10a/C10b 一致；C11a/C11b 差分仅 cg7/计数/行号 |
| F6 证据脚本自身假绿风险（`grep -c` 多文件 rc、还原后 rc 判定） | ✅已修 | C10c 改 `wc -l`、C14c/d 按计数判 rc | 首轮 run.sh rc=1（4 项 FAIL）→ 修后 rc=0；`--inject` rc=0 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（可进入 `/complete`）。以下均为 reviewer 独立重跑的真实输出，不采信 engineer 叙述。

**重跑记录（repo 根，相对路径；`git status --porcelain -uall` 前后快照一致）**
- 分支 `SPEC-179t`，HEAD `ec55939d`，工作树干净；`git diff master...HEAD --stat` = **8 文件**（+343/−114），与完成区「修改文件」8 项逐一对上；`master..HEAD` 仅 `ec55939d` + `4965de90` 两个提交。
- `make check` ⇒ rc=0（`repository checks (L1): PASS`）。
- `check-spec-readonly` / `check-spec-changelog` / `check-cfx-aliases` / `check-cfx-alias-table` / `check-spec-refs` / `check-contracts-dir` / `check-knowledge-refs` / `check-milestones-fresh` / `check-asm-prose` ⇒ **逐个 rc=0**。
- **`make check-lit` ⇒ rc=0，159/159 PASS**（别名减少无回归）。前置 `make install-cfx-aliases` rc=0（安装根旧表含 12 条 cg7 → 同步后 0 条），`make check-cfx-alias-install` rc=0（6 checks）。功能确认：`llvm-mc` 存活别名 rc=0，`cfx_umon_sram_block_sel`/`sram_addr` rc=1（报错）——别名删除确已到达消费端。
- `bash .work/evidence/SPEC-179t/run.sh` rc=0（C1–C14 全 PASS）；`--inject` rc=0。
- **reviewer 独立注入 4 次（均非 engineer 注入点，`cp` 备份 + md5 对账还原）**：① MEMORY 恢复 `0xffff_0000_0000` → rc=1（C7a FAIL）→ 还原 md5 一致 → rc=0；② 生成物 `cfx-aliases.txt` 加回 cg7 别名 → rc=1（C10b DRIFT + C10c FAIL）→ 还原 → rc=0；③ DADAO-12 全局把 `0xffff_fffc_0000`/`256 KiB` 改回旧值 → rc=1（C4b + C9 锁 sha MISMATCH）→ 还原 → rc=0；④ Machine-01 恢复旧 RAM 口径 → rc=1（C5b + C9）→ 还原 → rc=0。未用 `git checkout/restore/stash`。
- 锁 sha 实算 == 锁值（`037540af…59b7ae` / `cf14284c…273c2c`）；两份生成物重跑生成器后 md5 逐字节不变（无手改）；`cfx-aliases.txt` 相对 master 仅 **24 行 cg7 删除 + 1 行计数**，md 仅 cg7/计数/`DADAO-12:<行号>`。

**约束核验**：文件集精确、零越界（`components/**`、`tests/**`、`tools/testcases/**`、`.tao/adr/**`、`contracts/opcodes.yaml`、`contract-see.md`、`spec/README.md` 均 **零改动**）；版本未动（0.7.3-rc / 0.3.2-rc）；附录无任务号/ADR 号/表格；MEMORY 第 3/6/44 行与目标形态一致；仓库无临时残留；完成区 20 行 ≤30、本审阅记录每轮 ≤40；`milestones.md` 状态 `待验收` 与任务书一致；spec 全目录 `7–14` 除历史日期外零残留。**F2 冲突处置认可**：附录改述「核内存储块批量传输指令」，语义等价且保留史实。

**findings（不阻断，交 architect 收尾处置）**
1. 验收 2 的 `grep -nE '7[–.-]14'` 实跑 **rc=0 但命中 1 行** —— line 973 历史日期「导入日 2026-07-14」（假阳性，不应改史实）。实质判据（reserved 统一 `6–14`）已独立核验成立：正文 §2.1/§5.1/§5.2/§5.3/附录全部 `6–14、19–61`。建议 architect 修订验收 2 措辞为「非数字前导」变体（证据脚本 C2 已如此并经注入验证可达 FAIL）。
2. 证据脚本 C11a/C11b/C12 用**工作树** `git diff`/`git status`，提交后对已提交差分恒真（当前树干净 ⇒ 恒 PASS，仅脏树可达 FAIL）。建议改比 `git diff master...HEAD`。实质（改动范围）已由 reviewer 对 master 独立核验成立。
3. DADAO-12 附录 **0.7.2 历史条目**被改写（`cfxld`/`cfxst` → 「核内存储块批量传输指令」）。已查：`lessons.md`/`docs/Process-03`/`check_spec_changelog.py` **无禁止改历史段的规则**，git 保留原话可回溯，语义等价。属 architect 已登记的观察项，本 reviewer 裁定**可接受**；如需恢复原文，宜同时把验收 2 的 grep 限定在附录之前的正文段。
4. 留痕笔误：审阅记录「提交留痕」写 commit `ce464fed`，实际 HEAD 为 `ec55939d`（应为 rebase 前旧 sha）。文档级，收尾时顺手订正。

#### 提交留痕（architect，2026-10-31）
- 档位：**WIP**（reviewer 未验收，状态 `待验收`）→ 按派单指定信息提交；commit 落本分支 `SPEC-179t`，未 push。
- commit：`ec55939d` `feat(spec): SPEC-179t 启动链/BootROM/权限口径清理`（8 files, +127/−119）；rebase 前旧 sha `ce464fed` 已失效。
- 文件集对账：staged 8 项 == 完成区「修改文件」8 项（两册 spec + 锁 + MEMORY + 两份生成物 + 本任务书 + `milestones.md`）；无漏提/多提/越界；无 `components/**`、`tests/**`、`.tao/adr/**`、`contract-see.md`、`opcodes.yaml`、`spec/README.md`。
- 机械核验：锁 sha256 实测 == 锁值（DADAO-12 `037540af…59b7ae`、Machine-01 `cf14284c…273c2c`）；两份生成物重跑生成器后 `md5sum -c` 逐字节一致（无手改）；`git diff --check` rc=0；仓库内无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak`；`check-spec-readonly`/`check-spec-changelog`/`check-cfx-aliases`/`check-cfx-alias-table` rc=0。
- 观察项（交 reviewer 裁定，不影响本次提交）：`spec/DADAO-12` 附录 **0.7.2 历史条目**被改写为「核内存储块批量传输指令」——为使验收 2「全文 0 命中 `cfxld|cfxst`」成立；是否允许改写历史段需 reviewer 判断（自审 F2 已记录该任务书内部冲突）。

#### 收尾交叉复核（architect，2026-10-31）

**判决：确认 Accepted**（reviewer 判决不过松、无遗漏阻断项），可进入主会话 squash 落地 + push。

**独立重跑（本轮实测，repo 根、相对路径）**
- `git diff --name-only master...HEAD` = 8 项，与完成区「修改文件」逐项一致；`components/**`、`tests/**`、`tools/testcases/**`、`tests/shared/bootrom/**`、`contracts/opcodes.yaml`、`.tao/adr/**`、`.tao/contracts/contract-see.md`、`spec/README.md` 零改动。
- `make check` ⇒ rc=0（`repository checks (L1): PASS`）；`check-spec-readonly`/`check-spec-changelog`/`check-cfx-aliases`/`check-cfx-alias-table` ⇒ 逐个 rc=0。
- `make check-lit` ⇒ rc=0，**159/159 PASS**（cg7 别名删除无回归；reviewer 关键结论复核成立）。
- `sha256sum` 两册 == 锁值（`037540af…59b7ae` / `cf14284c…273c2c`）；`git status --porcelain -uall` 仅本任务书 1 项（本记录）。
- `bash .work/evidence/SPEC-179t/run.sh` ⇒ rc=0（C1–C14 全 PASS）。
- 语义抽查：DADAO-12 §2.1 表/说明、§3/§3.8、§5.1/§5.2/§5.3 与附录统一 `6–14、19–61`；Machine-01 §1.1 hmon/smon 内部偏移 `0x3ff_0000_0000` 与各 cfxha 段基址自洽（`2<<42+0x3ff…=0x0bff…`、`3<<42+0x3ff…=0x0fff…`）；MEMORY 第 3/6/44 行与目标形态一致。

**历史附录改写裁定**：`0.7.2` 已发布段 cg7 条目改述「核内存储块批量传输指令」——语义等价、git 可回溯原话、无禁止规则；认可 reviewer「可接受」。**遗留观察**：后续再动已发布段宜在现有 `-rc` 段追加墓碑条目，不再改写历史段。

**reviewer findings 处置**
1. 验收 2 `7[–.-]14` 假阳性 ⇒ ✅已处置：验收 2 与「新发现 1」改为「非数字前导」变体（不改历史日期），C2/C14 注入可达 FAIL。
2. 证据脚本 C11a/C11b/C12 用工作树 `git diff/status`（提交后恒真）⇒ ⏸记录不阻塞：脚本在 `.work/`（`.gitignore` 排除、不入库）；实质范围已由本复核对 `master...HEAD` 独立核验（8 项、零越界）；不另造断言。
3. 留痕笔误 `ce464fed` ⇒ ✅已订正为 `ec55939d`（同步 8 files, +127/−119）。

**最终判决**：reviewer Accepted 成立，无补充阻断发现；任务书 `**状态**` 由主会话置 `已验证` 后 squash 落地 + push。

#### 主会话重开（待返工）

用户指出 `cg7` 不能被删除：它描述当前 cfx 的内部空间（`DADAO-12 §2.1` 的起始地址、大小、性质），不是 `cfxld/cfxst` 的附属控制。主会话据此把本任务重开为 `待返工`，待补 `cg7` 空间描述表后重新验收。

#### 第 2 轮返工要求（architect，2026-10-31）

- **触发**：用户纠正 cg7 语义 + 给定 16 块 × 4 rc 布局（原话见「用户返工裁定原话」）；首轮「cg7 保留/删除」结论作废。
- **返工范围（仅口径，不实现）**：`DADAO-12` §3 开头/§3.8（64 行寄存器表 + 位域说明）/§2.1 互锁句/附录 `0.7.3-rc` 条目；`Machine-01` §3 与附录 `0.3.2-rc`；两份生成物按生成器重生成（预计 +768 条 cg7 别名、`regs=1430`）；锁 sha256 重算。
- **不变**：`cfxld/cfxst` 删除、reserved `6–14、19–61`、§2.1 地址行/BootROM/PA 0 别名/MEMORY 口径、文件集 8 项。
- **不修（后续任务）**：QEMU cg7 旧语义、`min_rom_probe_044t/045t` 旧用例、`contract-see.md` 块级描述缺失（约束 3 / 遗留问题 1）。
- **任务书本轮改动**：背景 2、目标 2/3/5、用户返工裁定原话、接口规范 §1 尾条与 §2 全重写、§3 的 Machine-01 §3/附录、§5 生成物预期、修改文件范围注、约束 1/3、验收 1/2/6、预检 1/3/4/5、完成区重置。
- **判决**：`待返工`；engineer 按本任务书实现后置 `待验收`。

**返工提交留痕（architect，2026-10-31）**：档位 **WIP**（状态 `待返工`，无实现）；显式 staging 2 项 = 本任务书 + `.tao/knowledge/milestones.md`，与「修改文件」声明对账一致（无漏提/多提/越界）；**未 `push`**；commit sha 见 `git log -1`（提交信息 `docs: SPEC-179t 返工（cg7 空间描述）`）。

#### 第 3 轮返工要求（architect，2026-10-31，A 方案：数组命名 + stride 4）

- **触发**：用户选定 **A 方案**（原话见「用户 A 方案裁定」）：cg7 用数组命名 `cfx_<name>_space_{desc,start,size,attr}[i]`（`i=0..15`，rc=4i+0..3），**允许改 `tools/spec/gen_cfx_aliases.py` 支持 stride 4**；不再要求 64 行 `space0_*` 显式表。
- **任务书本轮改动**：背景 2、总述、目标 2/5、新增 A 方案裁定段、接口规范 §2 寄存器表（4 行数组 + 生成器契约）、§5 生成物/生成器/运行时表缺口/validator 同步、修改文件范围（+投影器 +validator，共 10 项）、约束 1/2/3/4/6、验收 1/2/6/7、预检 1–5、完成区与遗留问题。
- **关键约束落点**：表内只 4 行数组；生成器展开 16 条/字段（768 条、`regs=1430`、行数 1451）；md 统计须等于 txt `regs=`；`tools/llvm/gen_cfx_alias_table.py` 不改；`format=1` 无 stride ⇒ 运行时表按 16×`count=1` 登记、汇编端暂不可拼写（遗留 2）；validator 仅扩展 `m*i+k` 解析（不改向量期望值）。
- **不变**：`cfxld/cfxst` 删除、reserved `6–14、19–61`、§2.1 地址行/BootROM/PA 0 别名/MEMORY 口径、`cfx_power` BootROM `X=1` 说明。
- **判决**：`待返工`；engineer 按本任务书实现后置 `待验收`。

**A 方案任务书提交留痕（architect，2026-10-31）**：档位 **WIP**（状态 `待返工`，无实现）；显式 staging 2 项 = 本任务书 + `.tao/knowledge/milestones.md`，与「修改文件」声明对账一致（无漏提/多提/越界）；**未 `push`**；提交信息按派单指定 `docs: SPEC-179t 采用 cg7 数组方案`（sha 见 `git log -1`）。

#### 第 3 轮 engineer 自审

逐行核对两册 spec 差分、生成器/validator 差分、两份生成物差分（仅 4 行模板 + 统计 + `DADAO-12:<行号>` 位移）、锁注释与 MEMORY 三行；判决：**可交付**（findings 全部处置，其余登记遗留）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 数组行 `array_base` 取 regname 全名，别名误成 `cfx_umon_cfx_⟨cfxname⟩_space_desc[3]` | ✅已修 | `gen_cfx_aliases.py` 改用 `tail[:-3]` | C10c=768、C11 errors=0 |
| F2 validator 只支持连续数组（`lo+N`），新 rc `4i+K` 无法解析 | ✅已修 | `parse_rc` 返回 `(lo,count,stride)`；`resolve_reg` 用 `lo+N*stride` | C13 三条断言、C16 check-cfx-vectors rc=0 |
| F3 md 统计用模板数乘 cfxname，数组展开后偏小 | ✅已修 | 按 `expand_count` 求和 → 1392 + 38 = 1430 | C12c |
| F4 §3.8 若写「不设 `space_count`/`sram_addr`…」会自命中验收 2 的零残留 grep | ✅已修 | 改述「cg7 只描述空间，不做传输控制」 | C3、C6 |
| F5 证据脚本 C7e 用 `space_desc[i]`，Machine-01 实际写 `space_{desc,…}[i]`（--inject 首跑 1 FAIL） | ✅已修 | 改 token；首跑 rc=1 → 修后 rc=0 | `.work/log/spec/SPEC-179t-evidence.log` |
| F6 QEMU/044t/045t/contract-see/LLVM 汇编端 stride 缺口 | ⏸延后（任务书约束 3 明确不在本任务修） | — | 完成区「遗留问题」1/2 |

**第 3 轮实现提交留痕（architect，2026-10-31）**：档位按派单指定 `feat(spec)`（状态 `待验收`，待 reviewer 第 2 轮验收）；显式 staging **9 项**（两册 spec、锁、两份生成物、`tools/spec/gen_cfx_aliases.py`、`validate_cfx_vectors.py`、本任务书、`milestones.md`），与完成区「修改文件」10 项对账：`MEMORY.md` 无本轮新改动，已含于首轮提交 `ec55939d` ⇒ 无漏提/多提/越界；`master...HEAD` 提交后应为 10 项。机械核验（本轮实测）：两生成器重跑后两份生成物 `md5` 逐字节不变（无手改）；锁 `sha256` 实测 == 锁值（`d55fff18…48fa05` / `8a3c56ac…cb48febf`）；`cfx-aliases.txt` `regs=1430`、1451 行、cg7 空间别名 768 条（rc 映射 768/768 断言 0 错）；`make check` rc=0（49s）与 8 个专项门控逐个 rc=0；`gen_cfx_aliases.py --verify`、`gen_cfx_alias_table.py --check` rc=0；`spec/`、两份生成物中旧 cg7 token 0 命中；`cfx_power` BootROM `X=1` 保留。**未 `push`**。

#### 第 3 轮 reviewer 验收（reviewer 第 2 次验收；原文标题「第 2 轮 reviewer 验收」，2026-10-31）

**判决：Accepted**（可进入 `/complete`）。以下均为 reviewer 独立重跑的真实输出/退出码，不采信 engineer/architect 叙述。

**重跑记录（repo 根、相对路径；注入前后 `git status --porcelain -uall` 均干净）**
- 分支 `SPEC-179t`、HEAD `db1a1051`、树干净；`git diff master...HEAD --stat` = **10 项**（+1388/−142），与完成区「修改文件」10 项逐一对上；`master..HEAD` 6 个提交。
- `make check` ⇒ rc=0（`repository checks (L1): PASS`）；`check-spec-readonly`/`check-spec-changelog`/`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-vectors`/`check-spec-refs`/`check-contracts-dir`/`check-knowledge-refs`/`check-milestones-fresh`/`check-asm-prose` ⇒ **逐个 rc=0**。
- `make install-cfx-aliases` rc=0；`make check-cfx-alias-install` rc=0（6 checks，安装副本 sha==源）；`make check-lit` ⇒ rc=0，**159/159 PASS**。
- cg7：§3.8 恰 **4 行** `4i+0..3` 数组行、数字 rc 行/`space0_*`/`RW` 均 0、`cf*xld/st`/`7–14`/`sram_*`/`cg0-cg6|cg7 保留` 全 0、`cg0-cg7 为共有寄存器设计`=1、`X=1`/`exists`/one-hot/volatile/shareable/cacheable/(cfxha<<42)/CFXREG/i=0..15 均 ≥1；§2.1 smon/hmon/pmem/power 四行与互锁示例自洽（`2<<42+0x3ff…=0x0bff…`、`63<<42+0x3ff_fffc_0000=0xffff_fffc_0000`、`start+size=2^42` 逐个实算成立）。Machine-01 旧口径 0 残留、新口径 token 全 ≥1；MEMORY 旧 RAM/`excluded 2 条` 0 命中。
- 生成物：cg7 空间别名 **768**（desc/start/size/attr 各 192、12 cfxname 各 16）；rc 映射全 768 条独立重算 **errors=0**（`rc=4i+K`、cg=7、count=1、cfxha 正确）；`regs=1430`、1451 行；`--verify`/`--check` rc=0；两生成器连跑两次 `md5` 不变、重生成后树仍干净（无手改）；md §2.1 恰 4 行模板、统计 1430=1392+38；`[0..63]` 旧数组不回归（`cfx_pmem_start[63]`→(17,12,63)）。
- validator：`cfx_umon_space_desc[5]`→(0,7,20)、`cfx_power_space_attr[15]`→(63,7,63)、`cfx_power_space_size[15]`→(63,7,62)、`cfx_smon_space_desc[15]`→(2,7,60)；越界/缺下标抛 `ValueError`。
- 证据：`run.sh` rc=0（**72/72 PASS**）、`--inject` rc=0（60 PASS）；脚本逐条审过，断言均有可达 FAIL 路径，无恒真。
- **reviewer 独立注入 2 次（均非 engineer 注入点，`cp` 备份 + md5 对账还原，未用 git checkout/restore）**：① `contracts/cfx-aliases.txt` `cfx_umon_space_desc[5]` rc 20→21 ⇒ `--check` rc=1（DRIFT）、run.sh rc=1（C10b+C11 errors=1+C14）→ 还原 md5 一致 → rc=0；② DADAO-12 §2.1 互锁示例 `start = 0x3ff_fffc_0000`→`0x3ff_fff8_0000` ⇒ run.sh rc=1（C9b 锁 sha MISMATCH）→ 还原 md5 一致 → rc=0。

**约束核验**：`components/**`、`tests/inst/**`、`tools/testcases/**`、`tests/shared/bootrom/**`、`.tao/adr/**`、`contracts/opcodes.yaml`、`contract-see.md`、`spec/README.md`、`tools/llvm/gen_cfx_alias_table.py` **零改动**（对 master diff 为空）；QEMU/044t/045t/contract-see/LLVM 汇编端 stride 缺口**如实登记**（遗留 1/2，且 `components/qemu/patches` 内 `sram_block_sel/sram_addr` 实存，未被顺手改）；版本未动；锁 sha 实测==锁值；完成区 14 行 ≤30、各轮审阅记录 ≤40 行；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`.bak` 残留。

**findings（不阻断，交 architect 收尾）**：任务书出现**两个 `## 审阅记录` 标题**（第 3 轮自审挂在前一个、第 1 轮/返工记录在后一个，且「第 3 轮」排在「第 1 轮」之前）——体例/排序混乱，属文档级，不影响任何门控与内容；建议收尾合并为一个标题并按轮次排序。

#### 第 3 轮 architect 交叉复核（`/complete`，2026-10-31）

**判决：确认 Accepted**（reviewer 第 2 次验收判决不过松、无遗漏阻断项；其唯一非阻断 finding 已按体例整理处置）。

**独立重跑（本轮实测，repo 根、相对路径）**
- `git diff --stat master...HEAD` = **10 项**（+1388/−142），与完成区「修改文件」逐项一致；`components/**`、`tests/**`、`tools/testcases/**`、`tests/shared/bootrom/**`、`.tao/adr/**`、`contracts/opcodes.yaml`、`contract-see.md`、`spec/README.md`、`tools/llvm/gen_cfx_alias_table.py` **对 master 零改动**。
- `make check` rc=0（`repository checks (L1): PASS`）；`make install-cfx-aliases` rc=0、`make check-cfx-alias-install` rc=0（6 checks，安装副本 sha==源）、`make check-lit` rc=0 **159/159 PASS**；`bash .work/evidence/SPEC-179t/run.sh` rc=0（**72/72 PASS**）。
- 生成物：cg7 空间别名 **768** 条（desc/start/size/attr 各 192、12 cfxha × 16 块），逐条重算 `rc=4i+K`、`cg=7`、`count=1` ⇒ **errors=0**；`regs=1430`、**1451 行**；两生成器连跑两次 md5 不变（`98cfc41b…` / `a1a96689…`）、`--verify`/`--check` rc=0、树保持仅本任务书 1 项改动。
- 锁：两册 sha256 实测 == 锁值（`d55fff18…48fa05` / `8a3c56ac…cb48febf`）；validator：`cfx_umon_space_desc[5]`→(0,7,20)、`cfx_power_space_attr[15]`→(63,7,63)、`cfx_power_space_size[15]`→(63,7,62)、`cfx_pmem_start[63]`→(17,12,63)；越界/缺下标抛 `ValueError`。
- `cfx_power` BootROM：§2.1 表 256 KiB / `0xffff_fffc_0000`、复位向量 `0xffff_ffff_0000`、`start=0x3ff_fffc_0000`、`size=0x4_0000`、`start+size=2^42` 逐一实算成立；`X=1` 要求与「各 cfx 空间由自身 cg7 描述」互锁句均在。

**reviewer finding 处置（体例整理）**：两处 `## 审阅记录` 合并为一处；块按时间/轮次重排（第 1 轮自审/验收 → 返工 → 第 3 轮自审 → reviewer 第 2 次验收）；标题折为「第 3 轮 reviewer 验收（reviewer 第 2 次验收；原文标题…）」并加 1 行轮次口径说明。**未删除任何记录内容**（全文行多重集仅差：合并 1 个标题、标题改写、新增 1 行说明），`spec/` 零改动。

**复核结论**：无阻断项；可交主会话将 `**状态**` 置 `已验证` 后 `merge --squash` 落地并 `push`。

#### 主会话统一收尾

reviewer 与 architect 两份独立复核均为 **Accepted**，无分歧；主会话采信并置任务 `已验证`。本任务完成 spec/生成物/validator 的 cg7 空间描述数组化，未改 QEMU/测试/ADR。已知遗留：QEMU 与 `min_rom_probe_044t/045t` 仍为旧 cg7 语义；运行时别名表 `format=1` 无 stride，LLVM 汇编端暂不可拼写；这些另立任务处理。
