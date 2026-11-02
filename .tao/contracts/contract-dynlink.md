# 动态链接 ABI 合约（M8：无内核的 Linux 用户态栈）

> **来源**：决策 `.tao/adr/adr-0025-m8-scope-linux-compat.md`（`ADR-0025`，Accepted，`D1`–`D7`）、`.tao/adr/adr-0019-dadao-relocation-types.md`（`ADR-0019`，Accepted，`D1`–`D10`）、`.tao/adr/adr-0021-ldst-symbol-reloc.md`（`ADR-0021`，Accepted，`D1`–`D3`）、`.tao/adr/adr-0003-object-abi.md`（`ADR-0003`，Accepted，`D1`/`D5`）；上游 spec **只作指针**：`spec/DADAO-21-ABI-应用程序二进制接口.md`（§寄存器规范 / §函数调用规范 / §数据表示）；v5 合约：`.tao/contracts/contract-elf.md`（§1 头字段、§2–§4 重定位、§5–§6 加载）、`.tao/contracts/contract-abi.md`（§1 寄存器角色与基础数据布局、§2 栈与调用）、`.tao/contracts/contract-isa.md`（§1.3.2 `rb0`、§1.5 地址模型）；并列契约 `.tao/contracts/contract-syscall.md`（M8 P0 契约①）。**类型集/公式/语义、`PT_INTERP` 命名、Hash、版本·`DT_RELR`、GOT·TP、绑定时机、越界策略** 已由**用户 2026-10-14 逐条确认**（渠道 = 经主会话问答；见 §9 裁定清单）；**2026-10-16 曾增补的 `R_DADAO_REL32`（`14`）/`R_DADAO_NUM`（`15`）与 GOT·PLT 形态（源 = `ADR-0028`）已随用户同日改线裁定撤回**——`ADR-0028` 转 `Superseded`，本册 GOT 远距离取址通道 / PLT 条目形态**当时标「待后继 ADR 定」**（`NUM` 回 `14`；见 §2.2 / §3 / §4.3 / §4.4 / §10④）——**后继 ADR = `ADR-0029`（`Accepted`）已定** ✓：通道 = `R_DADAO_PCREL_HI`/`PCREL_LO` 配对（`aip.si` + `ld.o`）、PLT = **3 条 / 12 B**（§2.2 / §3 / §10④ 已同步订正）。
>
> **范围**：M8 P0 契约②——动态链接 ABI 的 v5 口径：角色与口径（§1）、PIC/PIE 与地址无关模型（§2）、GOT/PLT（§3）、动态重定位（§4）、动态段与符号表（§5）、`PT_INTERP` 与启动 auxv（§6）、TLS（§7）、独立 oracle 口径（§8）、裁定清单（§9，已定）、失败与越界策略（§10）。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]` 标注 spec/ 来源（spec/ 未定者不标）；ADR 决策补足者标 `[ADR-NNNN DN]`；**ELF 动态链接通用语义**（`PT_INTERP`/`PT_DYNAMIC`/`AT_*`/GOT/PLT/`DT_*` 等，非 v5 规范正文）标 `[外部权威 …]` 并在 §1.3 给**可核出处**；spec/、ADR 均未定者标 `[spec-decision]`。**2026-10-14 用户逐条确认**的动态链接口径（类型号 / 公式 / 语义等）标 `[spec-decision]（用户 2026-10-14 逐条确认）`，其**规范正文已落地**：**类型号 / 公式 / 语义** ⇒ `[ADR-0019 D10]`；**行为类口径**（`ld.so` 用法 / `PT_INTERP` / `DT_*` / 绑定时机 / 越界）⇒ `[ADR-0026 D1–D8]`（二者均 **`Accepted`**，2026-10-14 由 architect 落地）。**2026-10-16 曾同步的 `D11`（`REL32`/`NUM`）与 `ADR-0026 D5`/`D7` 的 `REL32` 就地修订已随用户同日改线裁定撤回**（`ADR-0028` → `Superseded`；`ADR-0019 D11` 已加「已撤」注记）。不写行号。
>
> **说明**：本合约**不复制**上游 `spec/` 正文（只**指针**）；**外部权威**（System V ABI / ELF gABI、musl、QEMU 上游）只提供**通用语义**与**行为参照**，**不构成本项目规范正文**；与本合约或既有 ADR 冲突时阻断实现，走变更流程（`docs/Process-02-合约编写规范.md`）。**不属于本合约**：`ADR-0019 D10` / `ADR-0026` 的**决策正文**（本合约只承载契约口径）、TLS 模型的**逐 arch 定值**（§7，归 musl 移植任务）、syscall 语义映射（`contract-syscall.md`）。
>
> **落点**：本合约暂落 `.tao/knowledge/`（`check-knowledge-dir` 白名单允许 `contract-*.md`）。若 `INFRA-071t`（`contract-*.md` → `contracts/`，**待用户授权**）获批，本合约随之**整体迁移**；引用方按文件名 `contract-dynlink.md` 解析，不硬编码目录。[ADR-0025]

---

## §1 范围、角色与口径

### §1.1 无内核目标

- M8 只做 Linux **用户态**栈，**不引入内核**（VFS / MM / 调度 / 信号）；本合约只覆盖**用户态可见**的动态链接语义。[ADR-0025 D2]
- 内核层语义（页表建立、`mmap` 落盘、`open` 语义等）**不在**本合约范围；其用户态可见部分归 `contract-syscall.md`。[ADR-0025 D2]

### §1.2 角色分工（无内核下「内核 / 加载器侧」由谁扮演）

| 角色 | 承担者 | 来源 |
|------|--------|------|
| 动态链接器 `ld.so` | **musl 自带 ldso** | [ADR-0025 D3] |
| 「内核 / 加载器侧」（auxv 注入、`PT_INTERP` 解释器装载、加载偏置分配、路径解析） | **QEMU user-mode**（`linux-user`，P3） | [ADR-0025 D2][ADR-0025 D6] |
| 重定位**记录与公式**（静态） | 已冻结 | [ADR-0019 D1]–[ADR-0019 D9][ADR-0021 D1] |

- `ld.so` **不得**自写（`D3` 已否「自写 `ld.so`」）；实现侧**不得**以自写 loader 替代 musl ldso。[ADR-0025 D3]
- QEMU user-mode 属 **P3**（`D6` 顺序「契约 → musl → 动态 → linux-user」之第三步），其实现**须遵循本合约**。[ADR-0025 D6]
- **边界**：P3 实现（`linux-user` 转发/装载）**不得**充当 §8 的期望值来源。[ADR-0025 D7]

### §1.3 来源分层与外部权威出处（可核）

本合约把断言按**四类**分列，**事实**与**推测 / 待确认**分开写：

1. **外部权威**（ELF 通用语义 / 上游行为，**非 v5 规范正文**）——标 `[外部权威 …]`；
2. **上游 spec/**（只指针，不复制正文）——标 `[DADAO-NN §章节名]`；
3. **v5 既有决策**（已 `Accepted`）——标 `[ADR-NNNN DN]`；
4. **v5 契约口径**（本合约承载的动态链接口径）——标 `[spec-decision]`；其中**2026-10-14 用户逐条确认**者标 `[spec-decision]（用户 2026-10-14 逐条确认）`，规范正文**已落地**（`ADR-0019 D10` / `ADR-0026`）；§9 为**裁定清单（已定）**。

| 主题 | 权威 | 可核出处（2026-10-14 现场取回；路径为上游树内路径） |
|------|------|------------------------------------------------------|
| ELF 对象结构 / 符号表 / 重定位记录（`Elf64_Rela`、`r_info`） | **System V ABI（ELF gABI）第 4 章 Object Files**（含 `Symbol Table` / `Relocation` 节） | `https://www.sco.com/developers/gabi/latest/ch4.reloc.html`（HTTP 200） |
| 程序装载 / 动态链接（`PT_INTERP`/`PT_DYNAMIC`/`DT_*`/Hash Table/GOT/PLT） | **ELF gABI 第 5 章 Program Loading and Dynamic Linking** | `https://www.sco.com/developers/gabi/latest/ch5.dynamic.html`（HTTP 200） |
| musl `ldso` **行为**（重定位类别集 / auxv / Hash / 入口栈 / 安装名规则） | musl **v1.2.6**（tag = commit `9fa28ece75d8a2191de7c5bb53bed224c5947417`） | `ldso/dynlink.c` blob `715948f4f8b3e9b6aff8303b0d0bef6d5fe63cf8`；`https://git.musl-libc.org/cgit/musl/tree/ldso/dynlink.c?h=v1.2.6` |
| QEMU user-mode **行为**（auxv 注入 / `PT_INTERP` 装载 / guest-root 路径解析） | qemu commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（= `v11.1.1`，`manifests` 锁定） | qemu 树内 `linux-user/elfload.c`、`linux-user/main.c` |

- 上表引用的组件源码以 `manifests/` 锁为准；本地物化为组件源码检出（`.work/source/<组件>/`），其身份按锁中 `commit` 复核；上游 URL 仅作**可核出处**。[ADR-0025 D3]
- musl 的 pin 承载：`INFRA-076t`（musl `1.2.6` 取源与锁定）落 `manifests/`；本合约按 tag / commit 引用，**不**按 tag 名判版本。[ADR-0025 D3]

### §1.4 术语与公式符号

- `S` = 符号值、`A` = addend（`r_addend`，显式）、`P` = 重定位处地址、`B` = 加载偏置（base address）；定义与 `contract-elf.md §3.1` 同口径。[ADR-0019 D3]
- `tls_id` = 模块 TLS id（**加载器分配、≥1**）；`DTPOFF(sym)` = 符号的**模块内**偏置、`TPOFF(sym)` = 符号的 **TP 相对**偏置；`*slot` = **8 字节**动态重定位落点槽（§4.3）。[外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- `ET_DYN` = 位置无关的可执行 / 共享对象形态；`.so` = 共享对象；PIE = `-pie` 产生的 `ET_DYN` 可执行文件。[外部权威 ELF gABI 第 5 章]

---

## §2 PIC/PIE 口径与地址无关模型

### §2.1 地址无关的寄存器基础（事实）

下表中「角色」列为 spec 原文口径，「v5 处置」列为 v5 承接口径：[DADAO-21 §寄存器规范 §RB寄存器][contract-abi.md §4.5]

| 寄存器 | ABI 名 | 角色（spec 定义） | v5 处置 |
|--------|--------|-------------------|---------|
| `rb0` | `rbip` | instruction pointer（**读出为当前指令的地址**，只读） | 保留（IP） |
| `rb2` | — | **frame pointer（无条件保留）** | 保留不分配 |
| `rb3` | `rbtp` | **thread pointer（TP）** | 保留不分配 |

- 上表角色为 spec 原文口径；v5 的「保留不分配」口径见 `contract-abi.md §1.6`。[DADAO-21 §寄存器规范 §RB寄存器][contract-abi.md §4.5]
- `rb0`（`rbip`）即 **`IP`**：读出为**当前正在执行的指令的地址**（**非**「下一条」口径；本 ISA **无 `±4` 流水偏移**——v5 无 `−4`/`+4` 修正），且 `rb0` 作目的操作数触发 ILLI。[SimRISC-00 §基址寄存器][ADR-0015 D1]
- v5 有效虚拟地址 = **48 位**，地址计算时高 16 位被硬件忽略。[contract-isa.md §1.5]

### §2.2 位置无关的两条寻址通路（承接既有重定位体系）

- **通路①：IP 相对**。`R_DADAO_REL26` / `REL20` / `REL14`（字偏移，`(S + A − P) >> 2`）服务 `call`/`jump`/分支；`R_DADAO_REL12`（**字节**偏移、`rb0` 基址）服务 `ld/st` 符号偏移。v5 **无 `−4`/`+4`** 修正（`rb0` 读出即 `P`，即 `IP` 语义）。[ADR-0019 D3][ADR-0021 D1]
- **通路②：绝对 / 基址相对**。`R_DADAO_ABS48`（指令 3 片 `immu16` **或**数据 8 字节字段、高 16 位 = 0）、`R_DADAO_ABS12`（`rb1–rb63` 基址、字节偏移、`S + A`）。[ADR-0019 D2][ADR-0021 D1]
- **推导（**通道已定：`ADR-0029`**，2026-10-16）**：PIC/PIE 的 GOT 取址在 v5 现状下**不能**只靠单条访存的 `imms12`（±2 KiB；`ISS-230` 已证在任何分段布局下 `-shared` 默认布局的 `.got` 距离均不可达）⇒ **宽范围取址通道 = `R_DADAO_PCREL_HI`（`14`）+ `R_DADAO_PCREL_LO`（`15`）配对** ✓：`aip.si rbX, hi`（高段、4 KB 块、**舍入**）+ `ld.o rbX, [rbX, lo]`（低段、有符号 12 位）⇒ **2 条 / 次、零额外寄存器**，可达 **±512 MiB**，越界 ⇒ **link-time error**（`ADR-0029 D2`–`D4`；编号见 §4.3–§4.4）。**历史注记（保留）**：2026-10-16 曾定案 `R_DADAO_REL32`（3 条/次），**同日随用户改线裁定撤回** ✗（`ADR-0028` → `Superseded`，见文首「来源」行）。需要动态装配的仍是 **GOT 槽内容**（§4）。[ADR-0029 D2][ADR-0029 D3][ADR-0029 D4][ADR-0019 D2][ADR-0019 D10][ADR-0019 D12][ADR-0021 D3][ADR-0018 C7 D4][spec-decision]

### §2.3 `-fPIC` / `-pie` / `-shared` 的对象形态

- 三种形态均产 **`ET_DYN`**；代码与数据**不得**含链接期确定的绝对地址（除经 GOT / 动态重定位装配），因为加载偏置在链接期未知。[ADR-0025 D6][外部权威 ELF gABI 第 5 章]
- `-pie` 的入口取 `e_entry`（相对加载偏置解释）；`-shared` 无入口语义。[外部权威 ELF gABI 第 5 章]
- **与 M4 裸机路径并存不冲突**：M4 ELF 路径为 `ET_EXEC` + **VA=PA**、加载期不做地址重定位；动态路径要求「链接期 VMA ≠ 运行期地址」，该偏置由 QEMU user-mode 承担（§6）。[ADR-0003 D5][contract-elf.md §5.2][ADR-0025 D2]
- **重定位记录型态承接**：动态重定位表沿用 `SHT_RELA`（显式 addend）口径——与 `ADR-0019 D1` 同型，不改记录型态。[ADR-0019 D1]

### §2.4 GOT 基址寄存器与 TP：口径（**已定：2026-10-14 用户逐条确认**）

- **事实**：spec 定义 `rb2` 为 **frame pointer（无条件保留）**、`rb3`/`rbtp` 为 thread pointer，v5 M3 起二者**保留不分配**；**无 GP 寄存器**。[DADAO-21 §寄存器规范 §RB寄存器][contract-abi.md §4.5]
- **已定（裁定 8）**：**不引入 GOT 固定基址寄存器**——PIC 取 GOT 槽地址**不经**专用 GP（**无 GP 寄存器**，GOT 基址不由固定寄存器承载），改由 **IP 相对（`rb0`）+ 链接期常量偏移**定位槽地址，再以 `ld.o`/`st.o` 做 8 字节访存（§3）；**`DT_PLTGOT` 必须提供**（musl `ldso` 读 `dso->got`）。[ADR-0021 D3][外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- **已定（裁定 8）**：TP（`rbtp`）的**方向与偏置**归 **musl arch 宏**（`TLS_ABOVE_TP` / `TP_OFFSET` / `DTP_OFFSET` / `__get_tp`），**逐 arch 定值归 musl 移植任务**；本合约**只记录该依赖**、不写死值。[外部权威 musl `arch/riscv64/reloc.h`][ADR-0025 D5][spec-decision]（用户 2026-10-14 逐条确认）

---

## §3 GOT/PLT 结构与访问约定

- **GOT**：条目为 **8 字节指针槽**（v5 指针宽度 8 字节）；数据符号地址槽与 PLT 槽分属 `.got` / `.got.plt` 是 psABI 惯例，**节名与布局由 LLVM 侧定**，本合约只钉**槽宽 8 字节**与**访问路径**。[contract-abi.md §1.7][外部权威 ELF gABI 第 5 章][spec-decision]
- **PLT 绑定时机（已定，裁定 9）**：**首版取 eager（立即绑定 / `BIND_NOW`）**——经 `DT_BIND_NOW` / `DF_BIND_NOW` 在**装载期**完成全部 PLT 绑定；**lazy（延迟绑定，经 `DT_JMPREL` / `DT_PLTRELSZ` / `DT_PLTREL`）留后续**（musl `ldso` 两条都实现，本合约只钉**首版口径**为 eager）。[外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- **PLT 槽的填充**：由 `JUMP_SLOT` 类动态重定位（§4.3）在绑定时刻写入 GOT 槽；PLT stub 只负责「取 GOT 槽并跳转」，规范只钉**接口**（槽由动态重定位填充）。**PLT 条目形态 = 已定** ✓（`ADR-0029 D5`）：`aip.si rb4, hi` + `ld.o rb4, [rb4, lo]` + `jump [rb4, rd0, 0]` = **3 条指令 / 12 B**、条目内**无 8 字节数据槽**（`pltEntrySize` **24 → 12**、`pltDataOffset` 取消），**由链接器（LLD DADAO 后端）合成**（自身算 hi/lo、不经重定位记录；实现归 `LLVM-095t`）。**历史注记（保留）**：曾定案的「内联去槽」形态（`pltEntrySize` `24 → 16`、`pltDataOffset` 取消）**已随用户 2026-10-16 裁定撤回** ✗；后继形态以 `ADR-0029 D5` 为准。[外部权威 ELF gABI 第 5 章][ADR-0029 D5][ADR-0019 D2][spec-decision]
- **访问路径（PIC；裁定 8：不经 GP）**：取 GOT 槽地址 = **IP 相对（`aip.si`；`rb0` 读出 = 当前指令地址）+ 配对 `ld.o` 的 `imms12` 余量**，再以 `ld.o`/`st.o` 做 8 字节访存；**不需要** GOT 固定基址寄存器、**也不引入任何固定寄存器**（同一个 `rb` 既承载高段、又作基址、又收结果）；**relaxation 维持禁用**。单条 `imms12`（±2 KiB）**不足**（`ISS-230`）⇒ 宽范围取址 = **`R_DADAO_PCREL_HI`/`PCREL_LO` 配对**（可达 **±512 MiB**；`ADR-0029 D2`–`D4`）。**历史注记（保留）**：曾定案的 `R_DADAO_REL32` 3 条/次**已撤回** ✗。[ADR-0029 D4][ADR-0021 D3][ADR-0019 D7][ADR-0018 C7 D4][spec-decision]
- **`DT_PLTGOT` 必须提供**：musl `ldso` 读 `dso->got`，构造 PLT/GOT 时必须发出 `DT_PLTGOT`。[外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- **不得**把 GOT 槽地址的链接期常量偏移当作动态重定位（二者分工：**偏移**链接期定、**内容**运行期定）。[ADR-0019 D2]
- **GOT 语义（已定）**：GOT 的**模块内偏移固定**（= `DT_PLTGOT` 记的值；musl `ldso` 装载期读 `dso->got`），**绝对地址不固定**（= **装载基址 `B`** + 模块内偏移）——即「槽地址 = 链接期常量偏移 + 运行期装载基址」。[ADR-0019 D10][ADR-0026 D5][外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- **超 ±2 KiB 的通道（**已定：`ADR-0029`**，2026-10-16）**：**现行形态** ✓ = **`aip.si` + 配对 `ld.o` 的 `R_DADAO_PCREL_HI`/`PCREL_LO`**（高段 4 KB 块**舍入** + 低段**有符号** 12 位；可达 **±512 MiB**；GOT 取址 **2 条/次**、零额外寄存器；越界 / 落点不符 ⇒ **link-time error**）〔`ADR-0029 D2`–`D4`〕。**历史（保留）**：① 原「**两段式**（`R_DADAO_ABS48` 序列 + `ldm.o_rrri_rb` 落 `rb`）」**已废弃** ✗ —— 该路径在现有 ABI 下**不可实现**（链接器无可用 `rd`、ISA 无宽相对重定位类型；`ISS-230`）；② 2026-10-16 曾定案的 **`R_DADAO_REL32`（3 条/次）**方案亦**已随用户同日改线裁定撤回** ✗（`ADR-0028` → `Superseded`）。**不变** ✓：**不新增 ISA 指令**（通道只复用 `aip.si` 与既有 `ld.o`）、**只加长不缩短**、**禁 relaxation**（`ADR-0019 D7`）、`R_DADAO_REL12` 直接形式仍限 **±2 KiB**（越界 ⇒ 链接期报错）。[ADR-0029 D1][ADR-0029 D3][ADR-0019 D7][ADR-0026 D5][spec-decision]
  - **历史记录（2026-10-14，已废弃 ✗）**：原路径 = 由 `R_DADAO_ABS48` 序列把地址 / 偏移**算进 `rd`**，再以 `ldm.o_rrri_rb`（**目的 bank = `rb`**，`immu6 = 1` 当单寄存器用）**把值直接落 `rb`**，随后 `jump rbX, rd0, 0` 跳转；**跳转用途必须落 `rb`**——`jump-rrii` 基址只能取 `rb`、且**无「零 `rb`」**（`rb0` 不可作目的）。[ADR-0019 D7][ADR-0019 D10][ADR-0021 D1][ADR-0026 D5][contract-isa.md §3.2]
- **PLT 只读（eager 收益，已定）**：首版 **eager**（`BIND_NOW`）下 PLT / `.got.plt` **装载后即可只读** ⇒ 可做 **full `RELRO`**；`JUMP_SLOT` 槽内容在装载后固定。[ADR-0026 D6][spec-decision]（用户 2026-10-14 逐条确认）
- **icache 与绑定时机无关（已定）**：`JUMP_SLOT` 槽是**数据**（非代码）⇒ eager / lazy **均不**因绑定而需刷新 icache；只有「**写入或新映射代码**」的场景（`ifunc` resolver、`dlopen` 新映射段、JIT）才需刷新 icache。[ADR-0026 D5][外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）

---

## §4 动态重定位

### §4.1 记录型态（承接既有口径）

- 动态重定位表（`.rela.dyn` 之类）与 PLT 表（`.rela.plt` 之类）均用 **`SHT_RELA`**（显式 addend），与 `ADR-0019 D1` 同型；节名由 LLVM 侧定（gABI 不强制节名）。[ADR-0019 D1][外部权威 ELF gABI 第 5 章]
- 记录布局按 gABI：`Elf64_Rela` = `r_offset`(8B) + `r_info`(8B) + `r_addend`(8B)；64 位 ELF 的 `r_info` 中**类型占低位、符号索引占高位**（musl 取**低 31 位**为类型，源码事实）。[外部权威 ELF gABI 第 4 章][外部权威 musl `src/internal/dynlink.h`]

### §4.2 musl ldso 要求架构映射的**类别集**（事实）

- musl 在架构无关层定义**重定位类别**枚举，默认值为**不可命中的负值**（未映射 ⇒ 该类别不被使用）；各目标须在 `arch/<arch>/reloc.h` 把用到的类别映射到本架构的类型编号。[外部权威 musl `src/internal/dynlink.h`][外部权威 musl `arch/riscv64/reloc.h`]
- `ldso/dynlink.c` 实际消费的类别：`REL_SYMBOLIC`、`REL_GOT`、`REL_PLT`、`REL_RELATIVE`、`REL_COPY`、`REL_DTPMOD` / `REL_DTPOFF` / `REL_TPOFF`（+ 可选 `REL_TLSDESC`）。[外部权威 musl `ldso/dynlink.c`]
- ⇒ **DADAO 至少须为「符号地址 / PLT / 相对 / COPY」四类各给一个类型**（否则 ldso 无法处理对应重定位）；**类型集 / 编号已定**（§4.3–§4.4，用户 2026-10-14 逐条确认）；TLS 三类与 `TLSDESC` **纳入**（§7）。[ADR-0025 D3][spec-decision]（用户 2026-10-14 逐条确认）

### §4.3 DADAO 重定位类型总表（**最终编号，全密无空档；2026-10-14 用户逐条确认**）

名与公式 = gABI 通用语义（外部权威）+ v5 裁定；类型名以既有静态类型前缀 **`R_DADAO_`** 承接。**下表为最终编号总表**（编号 **全密无空档**）：编号 `1`–`5` = 既有**静态**类型（规范正文归 `contract-elf.md §2.2`，此处仅列示占位）、`6` 起为**动态 / TLS** 类型（正文 = `ADR-0019 D10`）、`0` 为 **no-op 占位**、`14`–`15` = 新增**静态配对**类型（`PCREL_HI` / `PCREL_LO`，源 = `ADR-0029`〔`Accepted`〕`D2`–`D4`，正文 = `ADR-0019 D12`）、`16` 为**类型计数**。**（2026-10-16）** 曾追加的 `R_DADAO_REL32`（`14`）/ `NUM` `14 → 15` **已随用户同日改线裁定撤回** ✗（`ADR-0028` → `Superseded`）；**同日 `ADR-0029` 定案（用户逐条确认）** ⇒ `R_DADAO_PCREL_HI` = **`14`** / `R_DADAO_PCREL_LO` = **`15`** / `R_DADAO_NUM` = **`16`**（`ADR-0019 D12` 就地修订）⇒ **现行 = 本表** ✓（与 `contract-elf.md §2.2` 逐行一致）。[ADR-0019 D2][ADR-0019 D10][ADR-0019 D12][ADR-0021 D2][contract-elf.md §2.2][外部权威 ELF gABI 第 4 章][spec-decision]（用户 2026-10-14 逐条确认）

| 编号 | 名 | 场景（落点） | musl 类别 | 公式 |
|------|----|-------------|-----------|------|
| 0 | `R_DADAO_NONE` | **no-op**（占位，**不参与动态段语义**） | `REL_NONE`（加载期跳过） | 无（ldso `continue`） |
| 1 | `R_DADAO_REL26` | **静态**：`call` / `jump`（iiii） | — | `(S + A − P) >> 2` |
| 2 | `R_DADAO_REL20` | **静态**：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii） | — | `(S + A − P) >> 2` |
| 3 | `R_DADAO_REL14` | **静态**：`br.eq` / `br.ne`（rrii） | — | `(S + A − P) >> 2` |
| 4 | `R_DADAO_REL12` | **静态**：`ld/st [rb0, sym]`（IP 相对、字节） | — | `S + A − P`（字节） |
| 5 | `R_DADAO_ABS12` | **静态**：`ld/st [rbN, sym]`（`rb1–rb63` 基址相对、字节） | — | `S + A`（字节） |
| 6 | `R_DADAO_ABS48` | **数据 / GOT 槽**（8 字节字段）**或**地址构造序列（3 片 wyde） | `REL_SYMBOLIC` / `REL_GOT` | `S + A`（**无符号 48 位**） |
| 7 | `R_DADAO_JUMP_SLOT` | PLT 的 GOT 槽（8 字节字段） | `REL_PLT` | `S + A`（**无符号 48 位**） |
| 8 | `R_DADAO_RELATIVE` | 相对重定位（8 字节字段） | `REL_RELATIVE` | `B + A`（**无符号 48 位**） |
| 9 | `R_DADAO_COPY` | 运行期副本 | `REL_COPY` | `memcpy(副本, S, st_size)` |
| 10 | `R_DADAO_TLS_DTPMOD` | 模块 TLS id（8 字节槽） | `REL_DTPMOD` | **定义该符号的模块**的 `tls_id`（加载器分配、**≥1**、容纳于 8 字节槽） |
| 11 | `R_DADAO_TLS_DTPREL` | 模块内偏置 | `REL_DTPOFF` | `DTPOFF(sym) + A`（**补码**） |
| 12 | `R_DADAO_TLS_TPREL` | TP 相对偏置 | `REL_TPOFF` | `TPOFF(sym) + A`（**补码，可负**） |
| 13 | `R_DADAO_TLSDESC` | TLS 描述符（**两格**） | `REL_TLSDESC` | 格① = resolver 地址（**基址**）；格② = `arg`（**由 resolver 约定**） |
| 14 | `R_DADAO_PCREL_HI` | **配对 hi 段**（静态）：`aip.si`（`riii`）的 **IP 相对**高段（4 KB 块、**舍入**） | — | `((S + A − P) + 0x800) >> 12`（**有符号**；`P` = `aip.si` 站点地址） |
| 15 | `R_DADAO_PCREL_LO` | **配对 lo 段**（静态）：配对 `ld.o`（`rrii`）的余量（携配对信息指回 `aip.si` 站点） | — | `(S + A − P) − (高段 << 12)` ∈ `[−2048, +2047]`（**补码**） |
| 16 | `R_DADAO_NUM` | 类型计数（**非实际重定位**） | — | —（**冻结值 = 16**） |

- **动态类型 = 8 项**：`R_DADAO_ABS48`（编号 `6`，数据 / GOT 槽**复用**）+ `JUMP_SLOT`=7 / `RELATIVE`=8 / `COPY`=9 / `TLS_DTPMOD`=10 / `TLS_DTPREL`=11 / `TLS_TPREL`=12 / `TLSDESC`=13；`R_DADAO_NONE`=0 为 **no-op 占位**（**不参与动态段语义**，musl `ldso` 遇即跳过）、`R_DADAO_NUM`=**16** 为**类型计数**（**非实际重定位**）；`14`/`15` = **静态配对**类型 `R_DADAO_PCREL_HI` / `R_DADAO_PCREL_LO`（非动态类型，`ADR-0019 D12`）。[ADR-0019 D10][ADR-0019 D12][spec-decision]（用户 2026-10-14 逐条确认）
- **值类规则（裁定 2）**：**偏移**类（`REL26`/`REL20`/`REL14`/`REL12`/`PCREL_HI`/`PCREL_LO`/`TLS_DTPREL`/`TLS_TPREL`）**不带位宽后缀**、按**补码（有符号）加法**计算；**基址 / 绝对地址**类（`ABS48` / `JUMP_SLOT` / `RELATIVE` 的 `S` / `B` 及其结果）按**无符号 48 位**解释。**命名后缀与值类解耦**：带 `48` 后缀者**仅**既有项 `ABS48` 一名（同类中 `JUMP_SLOT` / `RELATIVE` 的**名不含** `48`），偏移类名**一律不带**位宽后缀。[ADR-0019 D10][spec-decision]（用户 2026-10-14 逐条确认）
- **公式符号**：`B` = 装载基址、`S` = 符号运行时地址、`A` = `r_addend`（显式）；`*slot` = **8 字节**槽（§1.4）。[ADR-0019 D3][contract-elf.md §3.1]
- **数据 / GOT 槽形态**：复用既有 `R_DADAO_ABS48` 的**数据形式**（8 字节字段、大端、高 16 位 = 0）；**不新增**独立 `GLOB_DAT` 类型——数据符号地址与 GOT 槽**一律经 `ABS48`**。[contract-elf.md §3.1][spec-decision]（用户 2026-10-14 逐条确认）
- **落点字段**：动态重定位值落 **8 字节槽**（v5 有效虚拟地址 48 位 ⇒ 高 16 位 = 0，与 `R_DADAO_ABS48` 数据形式同型）。[contract-elf.md §3.1][contract-isa.md §1.5][spec-decision]
- **`COPY` / `TLSDESC` 纳入**：二者均纳入类型集（`9` / `13`）；`COPY` 由 ldso 运行期自符号定义处拷贝 `st_size` 字节；`TLSDESC` 为两格描述符（见上表）。**首版 `COPY` / `TLSDESC` 不发射**——lld 遇即**报错**（§10②）。[外部权威 ELF gABI 第 4 章][外部权威 musl `ldso/dynlink.c`][ADR-0019 D10][ADR-0026 D7][spec-decision]（用户 2026-10-14 逐条确认）

### §4.4 编号方案（**已定：2026-10-14 用户逐条确认**）

- **事实（本裁定前的既有占用）**：本裁定**前**，`e_flags[7:0] = 1` namespace 内的静态 `R_DADAO_*` 占用 `0`–`5`：`ABS48`=0、`REL26`=1、`REL20`=2、`REL14`=3、`REL12`=4、`ABS12`=5；另有 `R_DADAO_NUM`=6（**类型计数**、非实际重定位）。[contract-elf.md §2.2][ADR-0019 D2][ADR-0021 D2]
- **已定（裁定 1，最终编号）**：动态重定位类型固定在**同一** `e_flags[7:0] = 1` namespace 内编号——`R_DADAO_NONE`=**0**（**no-op 占位**、不参与动态段语义）、`R_DADAO_ABS48` **由 `0` 改为 `6`**（**改号**；数据 / GOT 槽**复用**）、其余动态 7 项编号 `7`–`13`（逐项号值见 §4.3 总表）；`R_DADAO_NUM` 冻结为 **`16`**〔**就地订正（2026-10-16，`ADR-0019 D12`）**：原 `14` 顺延为 `16`，`14`/`15` 由静态配对类型 `R_DADAO_PCREL_HI`/`R_DADAO_PCREL_LO` 占用（源 = `ADR-0029` `D2`–`D4`）〕；**不复用** legacy `Dadao.def` 的编号 / 公式。[ADR-0019 D10][ADR-0019 D12][contract-elf.md §2.2][spec-decision]（用户 2026-10-14 逐条确认）
- **改号影响面（已定）**：`ABS48` `0→6` 属**改号** ⇒ 须同步 `llvm/…/BinaryFormat/ELFRelocs/DADAO.def`（lld 生产者侧）、`contract-elf.md §2.2`、本合约 §4.3；并**排查既有 ELF 产物 / 测试向量**里写死的类型字段。**实际代码改动 = P2 工作**（登记 issue 跟踪）。[ADR-0019 D10][spec-decision]（用户 2026-10-14 逐条确认）
- **`R_DADAO_NUM`（类型计数）**：保持「类型计数」语义，其**冻结值 = `16`**（= 类型总数 ⇒ 类型号必须**密集无空档**；**就地订正（2026-10-16，`ADR-0019 D12`）**，原 `14` 值随 `PCREL_HI`/`PCREL_LO` 占用 `14`/`15` 顺延）。[ADR-0019 D10][ADR-0019 D12][contract-elf.md §2.2][spec-decision]（用户 2026-10-14 逐条确认）
- **【撤回注记（2026-10-16，用户裁定改线）】**：原 **`D11`** 就地修订注记（`R_DADAO_NUM` 由 `14` **顺延为 `15`** + 新增**静态**类型 **`R_DADAO_REL32`**=**`14`**）**已随用户 2026-10-16 改线裁定撤回** ✗（源 = `ADR-0028` 转 **`Superseded`**；`ADR-0019 D11` 已加「已撤」就地修订注记）⇒ **「新类型 / 编号待后继 ADR 定」已落实** ✓ —— 后继 ADR = **`ADR-0029`**（`Accepted`）⇒ `14` = `R_DADAO_PCREL_HI` / `15` = `R_DADAO_PCREL_LO` / `NUM` = **`16`**（`ADR-0019 D12`）。
- **不沿用第三方编号**：编号取值由本裁定直接给定，**不**取自第三方 psABI（如 RISC-V）编号表。[spec-decision]（用户 2026-10-14 逐条确认）
- **载体（已定，裁定 4 = 混合 (c)）**：**类型号 / 公式 / 语义** ⇒ **就地扩 `ADR-0019`（追加 `D10`）**承载**决策正文**；**行为类口径**（`ld.so` 用法 / `PT_INTERP` / `DT_*` / 绑定时机 / 越界）⇒ **新 ADR `ADR-0026`**。二者**均已由 architect 落地（2026-10-14，均 `Accepted`）**；本合约只承载**契约正文**并标注来源。[ADR-0019 D10][ADR-0026 D1–D8][ADR-0025][spec-decision]（用户 2026-10-14 逐条确认）
- **落地状态**：上列编号 / 公式 / 行为口径**已落地**——`ADR-0019 D10`（类型号 / 公式 / 语义）+ `ADR-0026 D1–D8`（行为类口径）。[ADR-0019 D10][ADR-0026 D1–D8][spec-decision]（用户 2026-10-14 逐条确认）
- **禁止**：**不得**自拟编号或公式（无用户确认即写入编号 = 违规）。[spec-decision]

### §4.5 越界与未解析策略

- 动态重定位的**越界 / 未支持类型 / 未解析**策略见 **§10 失败与越界策略**（裁定 10，2026-10-14 用户逐条确认）。[ADR-0019 D6][spec-decision]（用户 2026-10-14 逐条确认）

---

## §5 动态段与符号表

- **动态段**：`PT_DYNAMIC` + `.dynamic`（`SHT_DYNAMIC`）承载 `DT_*` 标签；必备子集受**两条**约束：①「musl ldso 实际消费的标签」（源码事实：`DT_SYMTAB` / `DT_STRTAB` / `DT_HASH` / `DT_GNU_HASH` / `DT_RELA` / `DT_RELASZ` / `DT_REL` / `DT_RELSZ` / `DT_JMPREL` / `DT_PLTRELSZ` / `DT_PLTREL` / `DT_PLTGOT` / `DT_NEEDED` / `DT_INIT` / `DT_INIT_ARRAY` / `DT_INIT_ARRAYSZ` / `DT_FINI` / `DT_FINI_ARRAY` / `DT_FINI_ARRAYSZ` / `DT_RPATH` / `DT_RUNPATH` / `DT_TEXTREL` / `DT_FLAGS` / `DT_FLAGS_1` / `DT_BIND_NOW` / `DT_RELR` / `DT_RELRSZ` / `DT_VERSYM` / `DT_DEBUG`）；② gABI 的标签通用语义（含 `DT_STRSZ` 等 strtab 尺寸类标签——其是否为 v5 必备项由 LLVM 侧定）。[外部权威 ELF gABI 第 5 章][外部权威 musl `ldso/dynlink.c`][spec-decision]
- **符号表 / 字符串表**：`.dynsym`（`DT_SYMTAB`）与 `.dynstr`（`DT_STRTAB`，尺寸标签 `DT_STRSZ`）为**必备**（gABI 要求；musl ldso 据此解析符号名）。[外部权威 ELF gABI 第 5 章][外部权威 musl `ldso/dynlink.c`]
- **哈希表口径（已定，裁定 6；修订）**：**只发射 GNU Hash（`DT_GNU_HASH`）**（≡ `--hash-style=gnu`）；**不**双发 SysV Hash（`DT_HASH`）。musl `ldso` 两套 hash 均支持 ⇒ **只发 GNU 侧即可**。**用户原话**：「只支持 GNU hash，无需提供 both」。【修订（2026-10-14）】本条**修订**早前记录的「双发（SysV + GNU，≡ `--hash-style=both`）」口径（同次会话由用户重新裁定为「仅 GNU」）。[ADR-0026 D3][外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- **符号版本 / `DT_RELR`（已定，裁定 7：都不做）**：
  - **不发射版本段**（不做符号版本化）；契约**留位**并写明**启用条件**（若将来启用，须一并定 `.gnu.version*` / `DT_VERNEED` / `DT_VERDEF` 完整约定）。[外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
  - **`DT_RELR` 默认关**（= `--pack-dyn-relocs=none`）；契约**留位**并写明**启用条件**（与 §4.4 编号方案联动，启用时另定紧凑相对重定位编码）。[外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
  - **登记（已知限制）**：musl **不支持** glibc 式**版本化符号解析**（ldso 只读 `DT_VERSYM` 用于 **time64 映射**）；第三方库带版本段时，**以 musl 行为为准**（非 glibc 语义）。[外部权威 musl `ldso/dynlink.c`][spec-decision]（用户 2026-10-14 逐条确认）
- **不得静默兼容**：本节未列的标签 / 节，实现方**不得**自行约定；遇未支持者按 §10 显式报错。[spec-decision]（用户 2026-10-14 逐条确认）

---

## §6 `PT_INTERP` 与启动 auxv（无内核下的注入者）

### §6.1 `PT_INTERP` 与 `ld.so` 路径约定（**已定：2026-10-14 用户逐条确认**）

- `PT_INTERP` 承载解释器**字符串路径**（gABI 第 5 章）；本项目的解释器 = musl ldso。[ADR-0025 D3][外部权威 ELF gABI 第 5 章]
- **事实（musl 命名规则）**：musl 的安装名规则为 `<syslibdir>/ld-musl-<arch><subarch>.so.1`（`Makefile` 中 `LDSO_PATHNAME`），各目标以 `LDSO_ARCH` 标识（如 riscv64 为 `"riscv64"`）。[外部权威 musl `Makefile`][外部权威 musl `arch/riscv64/reloc.h`]
- **已定（裁定 5）**：`PT_INTERP` = **`/lib/ld-musl-dadao.so.1`**，该路径为**符号链接 → `libc.so`**（主流 musl 做法）；写的是 **guest 视角路径**（由 QEMU user-mode + guest root 解析，§6.4）。[外部权威 musl `Makefile`][ADR-0025 D3][ADR-0026 D2][spec-decision]（用户 2026-10-14 逐条确认）
- **构建侧（裁定 5）**：须**显式传 `-dynamic-linker /lib/ld-musl-dadao.so.1`**（lld 无默认值）；**建议不改** lld 默认（由构建调用处显式给出）。[ADR-0026 D2][spec-decision]（用户 2026-10-14 逐条确认）

### §6.2 启动 auxv：musl ldso 消费的 `AT_*` 集合（事实）

- musl ldso 在启动期读取：`AT_BASE`（解释器自身加载基址；缺省时以 `AT_PHDR & -page` 推断）、`AT_PHDR` / `AT_PHNUM` / `AT_PHENT`（被测程序的程序头与基址推断）、`AT_ENTRY`、`AT_PAGESZ`、`AT_EXECFN`、`AT_SECURE`、`AT_UID` / `AT_EUID` / `AT_GID` / `AT_EGID`（安全模式 `libc.secure` 判定另与 `aux[]` 首槽掩码配合，见源码），外加各 psABI 经 `ARCH_DLINFO` 追加的项。[外部权威 musl `ldso/dynlink.c`][外部权威 musl `ldso/dlstart.c`]
- `AT_*` 的**通用语义**（含 `AT_PHDR`/`AT_ENTRY`/`AT_BASE`/`AT_PAGESZ` 等）见 gABI；本合约只钉「注入者与边界」（§6.3–§6.6）。[外部权威 ELF gABI 第 5 章]

### §6.3 注入者 = QEMU user-mode（无内核 ⇒ 无内核 auxv 构造者）

- **无内核目标**（`D2`）下**没有**内核 ELF 装载器 / `binfmt_elf`：auxv 的构造者是 **QEMU user-mode**。[ADR-0025 D2]
- **事实（qemu 行为）**：qemu `linux-user/elfload.c::create_elf_tables` 现场构造 auxv，写入 `AT_PHDR` / `AT_PHENT` / `AT_PHNUM` / `AT_PAGESZ` / `AT_BASE`（= 解释器装载基址 `interp_info->load_addr`，无解释器时为 0）/ `AT_FLAGS` / `AT_ENTRY` / `AT_UID` / `AT_EUID` / `AT_GID` / `AT_EGID` / `AT_HWCAP` / `AT_CLKTCK` / `AT_RANDOM` / `AT_SECURE` / `AT_EXECFN`（+ 可选 `AT_HWCAP2` / `AT_BASE_PLATFORM` / `AT_PLATFORM` / `AT_SYSINFO_EHDR`）/ `AT_NULL`。[外部权威 qemu `linux-user/elfload.c`]
- **解释器装载**：qemu 读 `PT_INTERP` 字符串后按访客路径打开并装载解释器（`load_elf_interp`），把其加载基址作为 `AT_BASE` 传出。[外部权威 qemu `linux-user/elfload.c`]
- **契约口径**：P3 的 qemu 实现**须**注入上列 musl 消费项（§6.2）且 `AT_BASE` 指向实际解释器基址；`e_entry` 的跳转对象为**解释器入口**（由 `AT_ENTRY` 回指被测程序入口）。[ADR-0025 D2][ADR-0025 D6][外部权威 musl `ldso/dynlink.c`]

### §6.4 解释器路径的解析语义

- **事实（qemu 行为）**：qemu user-mode 以**宿主侧 guest-root 前缀**（`-L` / `QEMU_LD_PREFIX`，经 `init_paths()`）解析访客路径，`PT_INTERP` 的 `open()` 走该前缀映射。[外部权威 qemu `linux-user/main.c`][外部权威 qemu `linux-user/elfload.c`]
- ⇒ 「无内核」下 `PT_INTERP` 路径语义的**提供者是 QEMU user-mode**（而非内核挂载 / 内核 `open` 语义）；该语义细节归 P3，本合约只钉「由谁提供」。[ADR-0025 D2][ADR-0025 D6]

### §6.5 入口栈与寄存器初值

- **事实（musl 入口约定）**：ldso 的 C 入口形如 `_dlstart_c(size_t *sp, size_t *dynv)`，**直接解析 SysV 初始栈向量**（`argc` / `argv` / `envp` / auxv）；该向量由 qemu 的 `create_elf_tables` 构造。[外部权威 musl `ldso/dlstart.c`][外部权威 qemu `linux-user/elfload.c`]
- **栈与寄存器约定承既有合约**：`SP` = `rb1`（栈向下增长）；`call` 执行时 SP 须 **8 字节对齐**。[contract-abi.md §2.1][DADAO-21 §函数调用规范 §The Stack Frame]
- **已定（裁定 8）**：不引入 GOT 固定基址寄存器（**无 GP 寄存器**）⇒ 进入被测程序时**无** GP 初值约定；TP（`rbtp`）的初值与维护归 **musl arch 宏 / `__get_tp`**（逐 arch 定值在 musl 移植任务；本合约只记录依赖，§2.4 / §7）。[contract-abi.md §4.5][spec-decision]（用户 2026-10-14 逐条确认）

### §6.6 边界

- QEMU user-mode 属 **P3**；其实现**须**遵循本合约（§6.2–§6.5），且**不得**充当 §8 的期望值来源。[ADR-0025 D6][ADR-0025 D7]
- 「谁扮演内核 / 加载器侧」的**唯一**承担者是 QEMU user-mode；本合约**不**引入内核目标、**不**定义内核侧接口。[ADR-0025 D2]

---

## §7 TLS（**已定：纳入 M8；2026-10-14 用户逐条确认**）

- **事实（musl 类别层）**：musl ldso **在类别层**需要 `REL_DTPMOD` / `REL_DTPOFF` / `REL_TPOFF`（+ 可选 `REL_TLSDESC`）；各目标须在 `arch/<arch>/reloc.h` 逐项映射（未映射即该类别不可命中）。[外部权威 musl `src/internal/dynlink.h`][外部权威 musl `arch/riscv64/reloc.h`][spec-decision]
- **事实（v5 寄存器 + `D5` 查证）**：spec 已定义 `rb3` = `rbtp`（thread pointer），v5 M3 起保留不分配；`ADR-0025 D5` 查证结论 = musl **硬依赖** TP（含 `struct pthread` 的 TCB/TLS 区**无条件**、静态单线程亦不可省）⇒ **TLS 自动纳入 M8**。[DADAO-21 §寄存器规范 §RB寄存器][contract-abi.md §4.5][ADR-0025 D5]
- **已定（裁定 1 / 8）**：TLS **纳入 M8**，类型集含 4 个 TLS 类（`R_DADAO_TLS_DTPMOD` / `R_DADAO_TLS_DTPREL` / `R_DADAO_TLS_TPREL` / `R_DADAO_TLSDESC`，编号见 §4.3 表）。[spec-decision]（用户 2026-10-14 逐条确认）
- **依赖记录（裁定 8）**：TP 的**方向与偏置**（`TLS_ABOVE_TP` / `TP_OFFSET` / `DTP_OFFSET` / `__get_tp`）归 **musl arch 宏**，**逐 arch 定值在 musl 移植任务**；本合约**只记录该依赖**、不写死值。[外部权威 musl `arch/riscv64/reloc.h`][ADR-0025 D5][spec-decision]（用户 2026-10-14 逐条确认）
- **禁止**：**不得**自拟 TLS 类型编号 / 模型（类型号已由 `ADR-0019 D10` 落定、用户 2026-10-14 确认，**不得增改**）。[ADR-0019 D10][spec-decision]（用户 2026-10-14 逐条确认）

---

## §8 独立 oracle 口径（不从实现反推）

- **期望值来源（判据顺序）**：① **ELF gABI / System V ABI** 的通用语义（记录布局、公式、`DT_*` / `AT_*` 标签、Hash 结构）；② **musl `ldso` 行为**（版本锁定 v1.2.6，见 §1.3；只读参照）；③ **RISC-V + musl golden 对照**（同一程序跑对照面，`ADR-0025 D7`）。[ADR-0025 D7][外部权威 ELF gABI 第 4/5 章][外部权威 musl `ldso/dynlink.c`]
- **禁止**：**不得**从 v5 自身实现反推期望值——`llvm-project` 的 DADAO 后端/补丁、LLD、`qemu` 的 DADAO 端口/补丁、`linux-user`（§6.6）、本仓工具的输出**均不得**作期望值来源；期望值须独立派生自 ①/②/③。[ADR-0025 D7][spec-decision]
- **对照边界项**（端序、`long double`、`fenv`、UB、实现定义项等）按既有 `[spec-decision]` 登记为「**非判据真源**」，不据此判红。[ADR-0025 D7]
- **归属**：具体对照 harness / 判据 / 回归门控 = **P4**（`D6` 顺序之末）；本合约只钉口径与禁止项。[ADR-0025 D6]

---

## §9 裁定清单（**已定：2026-10-14 用户逐条确认，渠道 = 经主会话问答**）

> 原「待确认清单」十项**已由用户 2026-10-14 逐条确认**，全部转为「**已定**」；原候选与选项标签见 §9.1「历史」。**规范正文已落地**：类型号 / 公式 / 语义 ⇒ `[ADR-0019 D10]`；行为类口径 ⇒ `[ADR-0026 D1–D8]`（§4.4）。**修订（2026-10-14）**：裁定 5（哈希表）由「**双发**」改为「**仅 GNU hash**」（用户原话「只支持 GNU hash，无需提供 both」；`ADR-0026 D3`）；其余 9 项不变。**撤回（2026-10-16）**：曾按 `ADR-0028`（同日转 `Superseded`）把裁定 1 / 2 的 `R_DADAO_NUM` **顺延为 `15`** 并新增**静态**类型 **`R_DADAO_REL32`= `14`**（`ADR-0019 D11`）——**该增补已随用户同日改线裁定撤回** ✗ ⇒ **现行以 §4.3 / §4.4 为准**；**订正（2026-10-16，`ADR-0019 D12`）**：现行编号 = `14` = `R_DADAO_PCREL_HI` / `15` = `R_DADAO_PCREL_LO` / `R_DADAO_NUM` = **`16`**（`ADR-0029` `Accepted`）⇒ **下表 #1 / #2 已同步订正** ✓。[ADR-0019 D10][ADR-0019 D12][ADR-0026 D1–D8][spec-decision]

| # | 项 | 状态 | 裁定（用户 2026-10-14 逐条确认；选项标签见 §9.1） |
|---|----|------|--------------------------------------------------|
| 1 | 动态重定位**类型集**（名 / 编号 / 公式 / 落点字段） | **已定** | **动态 8 项**：`R_DADAO_ABS48`=**6**（数据 / GOT 槽；**由 `0` 改号**）+ `JUMP_SLOT`=7 / `RELATIVE`=8 / `COPY`=9 / `TLS_DTPMOD`=10 / `TLS_DTPREL`=11 / `TLS_TPREL`=12 / `TLSDESC`=13；`R_DADAO_NONE`=**0**（no-op 占位）、`R_DADAO_PCREL_HI`=**14** / `R_DADAO_PCREL_LO`=**15**（静态配对；`ADR-0019 D12`）、`R_DADAO_NUM`=**16**（计数）（§4.3）；值类：**偏移**按补码加法、**基址 / 绝对地址**按无符号 48 位（§4.3） |
| 2 | `R_DADAO_*` 编号分配 / `R_DADAO_NUM` 冻结值 | **已定** | 编号分配见 #1；`R_DADAO_NUM` 保持**类型计数**，**冻结值 = `16`**（= 类型总数；§4.4；`ADR-0019 D12`） |
| 3 | 是否沿用第三方（如 RISC-V psABI）编号 | **已定** | **不沿用**——编号取值由 #1 直接给定 |
| 4 | `PT_INTERP` 路径与命名 | **已定** | **`/lib/ld-musl-dadao.so.1`**（符号链接 → `libc.so`，guest 视角路径）；构建须**显式传** `-dynamic-linker`（§6.1） |
| 5 | 哈希表口径（SysV / GNU / 双发） | **已定**（**修订**） | **仅 GNU hash**（`--hash-style=gnu`）——**不**双发 SysV；musl `ldso` 两套均支持，只发 GNU 侧即可（§5）。**修订 2026-10-14：原「双发」→「仅 GNU」** |
| 6 | 符号版本 / `DT_RELR` 是否纳入 | **已定** | **都不做**（不发射版本段；`DT_RELR` 默认关 = `--pack-dyn-relocs=none`）；契约留位并写明启用条件；登记 musl 不支持 glibc 式版本化解析（§5） |
| 7 | GOT 固定基址寄存器（**无 GP 寄存器**）与 `rbtp` 的初值 / 设置者 | **已定** | **不引入** GOT 固定基址寄存器（IP 相对访问槽）；`DT_PLTGOT` 必须提供；TP 方向 / 偏置归 musl arch 宏（§2.4 / §3 / §6.5 / §7） |
| 8 | TLS / 线程归属 ⇒ TLS 模型与类型 | **已定** | TLS **纳入 M8**（类型含 4 个 TLS 类）；TP 方向 / 偏置**逐 arch 定值**归 musl 移植任务（§7） |
| 9 | 延迟绑定 vs 立即绑定（默认口径） | **已定** | **首版 eager（`BIND_NOW`）**；lazy 留后续（§3） |
| 10 | 动态重定位的越界 / 未解析策略 | **已定** | 见 **§10 失败与越界策略** |

### §9.1 历史（原候选 / 选项标签；保留备查）

- 原「待确认清单」（用户 2026-10-14 逐条确认**前**）的候选类型名（**占位**，以 `…_<后缀>` 表示）：`…_RELATIVE` / `…_GLOB_DAT` / `…_JUMP_SLOT` / `…_COPY` / `…_TLS_DTPMOD64` / `…_TLS_DTPREL64` / `…_TLS_TPREL64`——**已被裁定取代**（数据 / GOT 槽复用 `ABS48`、**无**独立 `GLOB_DAT`、偏移类名**不带**位宽后缀）。[spec-decision]
- 原载体候选：**(a) 就地扩 `ADR-0019`（`D10`）** vs **(b) 另立新 ADR**（二选一或并列）——**裁定为混合 (c)**：类型号 / 公式 / 语义就地扩 `ADR-0019`（`D10`），行为类另立新 ADR（= **`ADR-0026`**）（§4.4）。[ADR-0019 D10][ADR-0026][spec-decision]
- **哈希口径修订（2026-10-14）**：裁定 5 原「双发（SysV + GNU，≡ `--hash-style=both`）」由用户**重新裁定**为「**仅 GNU hash**」——原「双发」作为历史记录保留于此；正文以 §5 为准。[ADR-0026 D3][spec-decision]（用户 2026-10-14 逐条确认）
- 原「未定项」现全部转为「已定」（上表）；每项已按 `docs/Process-03-ADR编写规范.md` 与 `AGENTS.md`「ADR decision 逐条确认」流程归属载体（就地修订 / 新 ADR / 落本合约正文）。[ADR-0025][spec-decision]
- **落纸规则**：编号 / 公式 / 命名类确认后，若属「就地修订 `ADR-0019`」则须用户逐条确认后方可改该 ADR。**本批次已由 architect 落地（2026-10-14）**：`ADR-0019` **就地追加 `D10`**（含 `D2` 就地修订注记）+ **新建 `ADR-0026`**（行为类口径）。[ADR-0019 D10][ADR-0026][ADR-0025][spec-decision]

---

## §10 失败与越界策略（**已定：2026-10-14 用户逐条确认，裁定 10**）

- **总则（裁定 10 ⑤）**：下述失败形态**只要求「必须报错、不得继续」**，**不改 musl 行为**；错误文案不作约束。本节 = `ADR-0026 D7`。[ADR-0026 D7][spec-decision]（用户 2026-10-14 逐条确认）
- **① 48 位约束**：`S`（符号运行时地址）/ `B`（装载基址）/ 重定位**结果**若越出 **48 位**有效虚拟地址范围 ⇒ **装载期（ld.so / 加载器）报错**——**不截断、不 wrap**。[contract-isa.md §1.5][spec-decision]（用户 2026-10-14 逐条确认）
- **② 未支持 / 未定义类型或结构**：遇**未支持或未定义**的重定位类型 / 结构（含某实现尚未实现的 `COPY` / `TLSDESC`，以及**未启用**的版本段 / `DT_RELR`）⇒ **显式报错，不静默**（不得静默跳过 / 静默出 0）。[ADR-0019 D6][spec-decision]（用户 2026-10-14 逐条确认）
- **③ 偏移与 TP 越界**：偏移类（`R_DADAO_TLS_DTPREL` / `R_DADAO_TLS_TPREL`）按**补码**（有符号）计算；`TP + TPOFF` 越界 ⇒ **报错**。[spec-decision]（用户 2026-10-14 逐条确认）
- **④ lld 侧（链接期）**：**经 GOT 间接访问解决远处符号**（**无需 relaxation**）——**通道 = `aip.si` + `R_DADAO_PCREL_HI`/`PCREL_LO` 配对** ✓（`ADR-0029 D2`–`D4`；可达 **±512 MiB**，越界 / 落点不符 ⇒ link-time error）。**历史注记（保留）**：2026-10-16 曾定案 `R_DADAO_REL32`（3 条/次），**已随用户同日改线裁定撤回** ✗（`ADR-0028` → `Superseded`）。`R_DADAO_REL12`（IP 相对**访存**）**直接形式**仍限 **±2 KiB** ⇒ 越界 ⇒ **链接期报错**（**不变** ✓）；**relaxation 维持 `ADR-0019 D7` 禁用** ✓。[ADR-0029 D2][ADR-0029 D3][ADR-0029 D4][ADR-0019 D6][ADR-0019 D7][ADR-0021 D3][spec-decision]（用户 2026-10-14 逐条确认；`REL32` 通道增补 = 2026-10-16 撤回）
- **与既有静态策略的关系**：静态越界 = link-time error（`ADR-0019 D6`）；动态越界按本条走**装载期报错**——分层不同、**不互相放宽**。[ADR-0019 D6][spec-decision]（用户 2026-10-14 逐条确认）

---

## 附录 A：来源对照

| 本合约 § | 内容 | 来源 |
|----------|------|------|
| §1.1 | 无内核目标；只覆盖用户态可见语义 | `ADR-0025 D2` |
| §1.2 | 角色分工（musl ldso / QEMU user-mode = 内核·加载器侧）；边界 | `ADR-0025 D2`/`D3`/`D6`/`D7` |
| §1.3 | 来源四分层；外部权威出处（gABI / musl / qemu，可核） | 外部权威（gABI 第4/5章、musl v1.2.6、qemu `c3d48b7d…`）；`ADR-0025 D3` |
| §1.4 | 术语与公式符号（`S`/`A`/`P`/`B`） | `ADR-0019 D3`；gABI 第 5 章 |
| §2.1 | `rb0`/`rb2`/`rbtp` 角色；48 位地址 | `DADAO-21 §寄存器规范 §RB寄存器`；`SimRISC-00 §基址寄存器`；`contract-isa.md §1.5`；`contract-abi.md §4.5`；`ADR-0015 D1` |
| §2.2 | 两条寻址通路（IP 相对 / 绝对·基址相对）；GOT 远距离取址通道 = **`R_DADAO_PCREL_HI`/`PCREL_LO` 配对**（`aip.si` + `ld.o`；`ADR-0029`；2026-10-16 曾定案的 `R_DADAO_REL32` 已撤回） | `ADR-0029 D2`–`D4`；`ADR-0019 D2`/`D3`/`D10`/`D12`；`ADR-0021 D1`/`D3`；`ADR-0018 C7 D4` |
| §2.3 | `ET_DYN`（`-fPIC`/`-pie`/`-shared`）；与 M4 VA=PA 路径并存 | gABI 第 5 章；`ADR-0003 D5`；`contract-elf.md §5.2` |
| §2.4 | GOT 基址寄存器与 TP 口径（**已定**：不引入 GOT 基址寄存器；TP 归 arch 宏） | `DADAO-21 §寄存器规范 §RB寄存器`；`contract-abi.md §4.5`；`ADR-0021 D3`；`ADR-0026 D5`；musl `ldso/dynlink.c`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §3 | GOT 槽 8 字节；GOT 语义（偏移固定 / 绝对不固定）；PLT 绑定时机（**已定**：eager / `BIND_NOW`、full `RELRO`）；`DT_PLTGOT`；访问路径（不经 GP；远距离通道 = `PCREL_HI`/`PCREL_LO` 配对，`ADR-0029`）；PLT 形态（**已定**：3 条 / 12 B、无数据槽，`ADR-0029 D5`；2026-10-16 曾定案的内联去槽已撤回）；icache 澄清 | `contract-abi.md §1.7`；gABI 第 5 章；musl `ldso/dynlink.c`；`ADR-0029 D4`/`D5`；`ADR-0021 D3`；`ADR-0018 C7 D4`；`ADR-0019 D10`/`D12`；`ADR-0026 D5`/`D6`；`[spec-decision]` |
| §4.1 | `SHT_RELA` 记录型态；`Elf64_Rela` 布局与 `r_info` 位宽 | `ADR-0019 D1`；gABI 第 4 章；musl `src/internal/dynlink.h` |
| §4.2 | musl 类别集与默认不可命中；须映射的四类 | musl `src/internal/dynlink.h` / `ldso/dynlink.c` / `arch/riscv64/reloc.h`；`ADR-0025 D3` |
| §4.3 | **已定**重定位总表（`0`=`NONE` 占位 / `1`–`5` 静态 / `6`=`ABS48` / `7`–`13` 动态 / `14`–`15` = 静态配对 `PCREL_HI`/`PCREL_LO` / `16`=`NUM`）与公式（无符号 48 位 / 补码）**——2026-10-16 曾追加的 `REL32`=14 / `NUM`=15 已撤回；`14`/`15` 现由 `ADR-0029` 的 `PCREL_HI`/`PCREL_LO` 占用、`NUM`=`16`（`ADR-0019 D12`）** | gABI 第 4 章；musl；`contract-elf.md §3.1`；`ADR-0019 D10`/`D12`；`ADR-0029`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §4.4 | 编号方案（`NONE`=0 / `ABS48` **0→6 改号** / 动态 7–13 / 静态配对 14–15 / `NUM`=16）；载体 (c) 混合（就地扩 `ADR-0019 D10` + 新 ADR `ADR-0026`）；**2026-10-16 曾修订（新增 `REL32`=14、`NUM` `14→15`）已撤回，现按 `ADR-0019 D12` 订正** | `contract-elf.md §2.2`；`ADR-0019 D2`/`D10`/`D12`；`ADR-0021 D2`；`ADR-0025`；`ADR-0026`；`ADR-0029`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §4.5 | 越界 / 未解析策略（指针 → §10） | `ADR-0019 D6`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §5 | 动态段 `DT_*` 消费集；`dynsym`/`dynstr`；Hash **已定**（**修订：仅 GNU hash**）；版本 / `DT_RELR` **已定**（都不做） | gABI 第 5 章；musl `ldso/dynlink.c`；`ADR-0026 D3`/`D4`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §6.1 | `PT_INTERP` 字符串；musl 安装名规则；**已定**命名 `/lib/ld-musl-dadao.so.1`（符号链接 → `libc.so`；构建显式传 `-dynamic-linker`） | `ADR-0025 D3`；gABI 第 5 章；musl `Makefile` / `arch/riscv64/reloc.h`；`ADR-0026 D2`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §6.2 | musl 消费的 `AT_*` 集合 | musl `ldso/dynlink.c` / `ldso/dlstart.c`；gABI 第 5 章 |
| §6.3 | 注入者 = QEMU user-mode；`create_elf_tables` / `load_elf_interp` / `AT_BASE` | `ADR-0025 D2`/`D6`；qemu `linux-user/elfload.c` |
| §6.4 | 解释器路径解析（guest-root 前缀） | `ADR-0025 D2`/`D6`；qemu `linux-user/main.c` / `elfload.c` |
| §6.5 | 入口栈向量；SP/8B 对齐；`rb2`(FP)/`rbtp` 初值（**已定**：无 GP；TP 归 arch 宏） | musl `ldso/dlstart.c`；qemu `linux-user/elfload.c`；`contract-abi.md §2.1`；`DADAO-21 §函数调用规范 §The Stack Frame`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §6.6 | P3 边界；不得作 oracle；不引入内核目标 | `ADR-0025 D2`/`D6`/`D7` |
| §7 | TLS **已定纳入 M8**（4 个 TLS 类）；TP 方向 / 偏置归 musl arch 宏（依赖记录） | `ADR-0025 D5`；musl `reloc.h`；`DADAO-21 §寄存器规范 §RB寄存器`；`contract-abi.md §4.5`；`ADR-0019 D10`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §8 | oracle 口径与禁止项；P4 归属 | `ADR-0025 D6`/`D7`；`ADR-0026 D8`；gABI；musl |
| §9 | **裁定清单（已定）**与历史 / 落纸规则（裁定 5 修订为仅 GNU hash） | `ADR-0025`；`ADR-0026 D3`；`ADR-0019 D10`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
| §10 | **失败与越界策略**（48 位约束 / 未支持类型 / 补码越界 / lld 侧 / 分层；`REL32` 通道增补 2026-10-16 **已撤回**） | `ADR-0026 D7`；`ADR-0019 D6`/`D7`；`ADR-0021 D3`；`contract-isa.md §1.5`；`[spec-decision]`（用户 2026-10-14 逐条确认） |
