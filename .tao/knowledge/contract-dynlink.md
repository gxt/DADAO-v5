# 动态链接 ABI 合约（M8：无内核的 Linux 用户态栈）

> **来源**：决策 `.tao/adr/adr-0025-m8-scope-linux-compat.md`（`ADR-0025`，Accepted，`D1`–`D7`）、`.tao/adr/adr-0019-dadao-relocation-types.md`（`ADR-0019`，Accepted，`D1`–`D9`）、`.tao/adr/adr-0021-ldst-symbol-reloc.md`（`ADR-0021`，Accepted，`D1`–`D3`）、`.tao/adr/adr-0003-object-abi.md`（`ADR-0003`，Accepted，`D1`/`D5`）；上游 spec **只作指针**：`spec/DADAO-21-ABI-应用程序二进制接口.md`（§寄存器规范 / §函数调用规范 / §数据表示）；v5 合约：`.tao/knowledge/contract-elf.md`（§1 头字段、§2–§4 重定位、§5–§6 加载）、`.tao/knowledge/contract-abi.md`（§1 寄存器角色与基础数据布局、§2 栈与调用）、`.tao/knowledge/contract-isa.md`（§1.3.2 `rb0`、§1.5 地址模型）；并列契约 `.tao/knowledge/contract-syscall.md`（M8 P0 契约①）。
>
> **范围**：M8 P0 契约②——动态链接 ABI 的 v5 口径：角色与口径（§1）、PIC/PIE 与地址无关模型（§2）、GOT/PLT（§3）、动态重定位（§4）、动态段与符号表（§5）、`PT_INTERP` 与启动 auxv（§6）、TLS 占位（§7）、独立 oracle 口径（§8）、待确认清单（§9）。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]` 标注 spec/ 来源（spec/ 未定者不标）；ADR 决策补足者标 `[ADR-NNNN DN]`；**ELF 动态链接通用语义**（`PT_INTERP`/`PT_DYNAMIC`/`AT_*`/GOT/PLT/`DT_*` 等，非 v5 规范正文）标 `[外部权威 …]` 并在 §1.3 给**可核出处**；spec/、ADR 均未定者标 `[spec-decision]` 并写明「待用户逐条确认」。不写行号。
>
> **说明**：本合约**不复制**上游 `spec/` 正文（只**指针**）；**外部权威**（System V ABI / ELF gABI、musl、QEMU 上游）只提供**通用语义**与**行为参照**，**不构成本项目规范正文**；与本合约或既有 ADR 冲突时阻断实现，走变更流程（`docs/Process-02-合约编写规范.md`）。**不属于本合约**：具体号值/编号正文（待 §9 确认后落笔）、TLS 模型（§7 占位）、syscall 语义映射（`contract-syscall.md`）。
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
4. **未定项**——标 `[spec-decision]`，并在 §9 汇总「待用户逐条确认」。

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
- `ET_DYN` = 位置无关的可执行 / 共享对象形态；`.so` = 共享对象；PIE = `-pie` 产生的 `ET_DYN` 可执行文件。[外部权威 ELF gABI 第 5 章]

---

## §2 PIC/PIE 口径与地址无关模型

### §2.1 地址无关的寄存器基础（事实）

下表中「角色」列为 spec 原文口径，「v5 处置」列为 v5 承接口径：[DADAO-21 §寄存器规范 §RB寄存器][ADR-0018 C6]

| 寄存器 | ABI 名 | 角色（spec 定义） | v5 处置 |
|--------|--------|-------------------|---------|
| `rb0` | `rbip` | instruction pointer（**读出为当前指令的地址**，只读） | 保留（PC） |
| `rb2` | `rbgp` | **global pointer（GP）** | 保留不分配 |
| `rb3` | `rbtp` | **thread pointer（TP）** | 保留不分配 |

- 上表角色为 spec 原文口径；v5 的「保留不分配」口径见 `contract-abi.md §1.6`。[DADAO-21 §寄存器规范 §RB寄存器][ADR-0018 C6]
- `rb0` 读出为**当前指令地址**（非 PC+4），且 `rb0` 作目的操作数触发 ILLI。[SimRISC-00 §基址寄存器][ADR-0015 D1]
- v5 有效虚拟地址 = **48 位**，地址计算时高 16 位被硬件忽略。[contract-isa.md §1.5]

### §2.2 位置无关的两条寻址通路（承接既有重定位体系）

- **通路①：PC 相对**。`R_DADAO_REL26` / `REL20` / `REL14`（字偏移，`(S + A − P) >> 2`）服务 `call`/`jump`/分支；`R_DADAO_REL12`（**字节**偏移、`rb0` 基址）服务 `ld/st` 符号偏移。v5 **无 `−4`** 修正（`rb0` 读出即 `P`）。[ADR-0019 D3][ADR-0021 D1]
- **通路②：绝对 / 基址相对**。`R_DADAO_ABS48`（指令 3 片 `immu16` **或**数据 8 字节字段、高 16 位 = 0）、`R_DADAO_ABS12`（`rb1–rb63` 基址、字节偏移、`S + A`）。[ADR-0019 D2][ADR-0021 D1]
- **推导（非决策）**：PIC/PIE 的**指令域**无须新增重定位类型——GOT 槽相对 GOT 基址的偏移在**链接期**即为常量，可直接编码进既有访存立即数（`imms12`；超出范围时的具体形态由 LLVM 依 `ADR-0018 C7 D4` 的形态选择机制决定）；需要动态装配的是 **GOT 槽内容**（§4）。此推导的最终归属（类型集/编号）仍待 §9 #1 确认。[ADR-0019 D2][ADR-0021 D3][ADR-0018 C7 D4][spec-decision]

### §2.3 `-fPIC` / `-pie` / `-shared` 的对象形态

- 三种形态均产 **`ET_DYN`**；代码与数据**不得**含链接期确定的绝对地址（除经 GOT / 动态重定位装配），因为加载偏置在链接期未知。[ADR-0025 D6][外部权威 ELF gABI 第 5 章]
- `-pie` 的入口取 `e_entry`（相对加载偏置解释）；`-shared` 无入口语义。[外部权威 ELF gABI 第 5 章]
- **与 M4 裸机路径并存不冲突**：M4 ELF 路径为 `ET_EXEC` + **VA=PA**、加载期不做地址重定位；动态路径要求「链接期 VMA ≠ 运行期地址」，该偏置由 QEMU user-mode 承担（§6）。[ADR-0003 D5][contract-elf.md §5.2][ADR-0025 D2]
- **重定位记录型态承接**：动态重定位表沿用 `SHT_RELA`（显式 addend）口径——与 `ADR-0019 D1` 同型，不改记录型态。[ADR-0019 D1]

### §2.4 GOT 基址寄存器的持有者与初始化（**待用户逐条确认**）

- 事实：spec 已把 `rb2`/`rbgp` 定义为 global pointer、`rb3`/`rbtp` 为 thread pointer，v5 M3 起二者**保留不分配**。[DADAO-21 §寄存器规范 §RB寄存器][ADR-0018 C6]
- **未定（待确认）**：① PIC 代码以**哪个寄存器**承载 GOT 基址（候选：`rb2`/`rbgp`，spec 已给 GP 角色）；② 该寄存器由**谁、在何时**设置（候选：musl ldso 在跳入被测程序前设置，与其它 psABI 的 `gp` 初始化同类）；③ `rbtp` 的初值（与 §7 联动）。本合约**不预设**，实现前须先确认。[spec-decision][ADR-0025 D3]

---

## §3 GOT/PLT 结构与访问约定

- **GOT**：条目为 **8 字节指针槽**（v5 指针宽度 8 字节）；数据符号地址槽与 PLT 槽分属 `.got` / `.got.plt` 是 psABI 惯例，**节名与布局待确认**（gABI 不强制节名）。[contract-abi.md §1.7][外部权威 ELF gABI 第 5 章][spec-decision]
- **PLT**：两条绑定路径——**延迟绑定**（经 `DT_JMPREL` / `DT_PLTRELSZ` / `DT_PLTREL`）与**立即绑定**（`DT_BIND_NOW` / `DF_BIND_NOW`）；musl ldso **两条都实现**（源码事实）。DADAO 默认取哪条（或允许两者）**待确认**。[外部权威 musl `ldso/dynlink.c`][spec-decision]
- **PLT 槽的填充**：由 `JUMP_SLOT` 类动态重定位（§4）在绑定时刻写入 GOT 槽；PLT stub 只负责「取 GOT 槽并跳转」，其指令序列与生成方（LLD DADAO 后端）**待确认**，规范只钉**接口**（槽由动态重定位填充）。[外部权威 ELF gABI 第 5 章][ADR-0019 D2][spec-decision]
- **访问路径（PIC；事实 + §2.2 推导）**：取 GOT 槽地址 = GOT 基址 + 链接期常量偏移（`imms12` 字节偏移，约 ±2 KiB；**超出**范围的形态由 LLVM 依 `ADR-0018 C7 D4` 的形态选择机制决定），再以 `ld.o`/`st.o` 做 8 字节访存；**不需要**为「访问 GOT」本身新增重定位类型。[ADR-0021 D3][ADR-0018 C7 D4]
- **不得**把 GOT 槽地址的链接期常量偏移当作动态重定位（二者分工：**偏移**链接期定、**内容**运行期定）。[ADR-0019 D2][spec-decision]

---

## §4 动态重定位

### §4.1 记录型态（承接既有口径）

- 动态重定位表（`.rela.dyn` 之类）与 PLT 表（`.rela.plt` 之类）均用 **`SHT_RELA`**（显式 addend），与 `ADR-0019 D1` 同型；节名**待确认**。[ADR-0019 D1][spec-decision]
- 记录布局按 gABI：`Elf64_Rela` = `r_offset`(8B) + `r_info`(8B) + `r_addend`(8B)；64 位 ELF 的 `r_info` 中**类型占低位、符号索引占高位**（musl 取**低 31 位**为类型，源码事实）。[外部权威 ELF gABI 第 4 章][外部权威 musl `src/internal/dynlink.h`]

### §4.2 musl ldso 要求架构映射的**类别集**（事实）

- musl 在架构无关层定义**重定位类别**枚举，默认值为**不可命中的负值**（未映射 ⇒ 该类别不被使用）；各目标须在 `arch/<arch>/reloc.h` 把用到的类别映射到本架构的类型编号。[外部权威 musl `src/internal/dynlink.h`][外部权威 musl `arch/riscv64/reloc.h`]
- `ldso/dynlink.c` 实际消费的类别：`REL_SYMBOLIC`、`REL_GOT`、`REL_PLT`、`REL_RELATIVE`、`REL_COPY`、`REL_DTPMOD` / `REL_DTPOFF` / `REL_TPOFF`（+ 可选 `REL_TLSDESC`）。[外部权威 musl `ldso/dynlink.c`]
- ⇒ **DADAO 至少须为「符号地址 / PLT / 相对 / COPY」四类各给一个类型**（否则 ldso 无法处理对应重定位）；**类型名/编号待 §9 #1 逐条确认**；TLS 三类与 `TLSDESC` **是否纳入取决于 §7**。[ADR-0025 D3][spec-decision]

### §4.3 候选 DADAO 动态重定位类型（**候选，待用户逐条确认**）

下表**名与公式**来自 gABI 通用语义（外部权威）；左侧类型名为「**待定的架构前缀** + gABI 惯用后缀」的**占位**，**不是已定名**：

| 候选类型（名待定） | gABI 通用语义（公式） | 对应 musl 类别 |
|--------------------|----------------------|----------------|
| `…_RELATIVE` | `B + A`（写入 8 字节字段） | `REL_RELATIVE` |
| `…_GLOB_DAT` | `S + A`（写入 8 字节字段） | `REL_SYMBOLIC` / `REL_GOT` |
| `…_JUMP_SLOT` | `S + A`（写入 PLT 的 GOT 槽） | `REL_PLT` |
| `…_COPY` | 运行期自符号定义处拷贝 `st_size` 字节 | `REL_COPY` |
| `…_TLS_DTPMOD64` / `…_TLS_DTPREL64` / `…_TLS_TPREL64` | 模块 id / 模块内偏置 / TP 相对偏置（确切公式随 TLS 模型，见 §7） | `REL_DTPMOD` / `REL_DTPOFF` / `REL_TPOFF`（**与 §7 联动；未定**） |

- 落点字段：gABI 通用语义为 8 字节字；v5 有效虚拟地址 48 位 ⇒ 「8 字节字段、高 16 位为 0」（与 `R_DADAO_ABS48` 数据形式同型）**是否**为本合约口径**待确认**。[contract-elf.md §3.1][contract-isa.md §1.5][spec-decision]
- `REL_COPY` / COPY 重定位**是否**纳入 M8 **待确认**（gABI 允许、musl 需要其类别映射；不纳入即该类别不使用）。[外部权威 musl][spec-decision]
- **命名前缀（事实）**：既有静态类型一律以 `R_DADAO_` 为前缀；动态类型**是否**沿用同前缀随 §9 #1 确认（本合约不预先写成 `R_DADAO_<后缀>` 形式）。[contract-elf.md §2.2][spec-decision]

### §4.4 编号方案（**待用户逐条确认；本合约不代decide**）

- **事实（既有占用）**：`e_flags[7:0] = 1` namespace 内既有 `R_DADAO_*` 占用 `0–5`：`ABS48`=0、`REL26`=1、`REL20`=2、`REL14`=3、`REL12`=4、`ABS12`=5；`R_DADAO_NUM`=6 为**类型计数**（非实际重定位）。[contract-elf.md §2.2][ADR-0019 D2][ADR-0021 D2]
- **约束**：新编号须落在**同一** `e_flags[7:0] = 1` namespace 内**独立编号**，且**不得**复用 legacy `Dadao.def` 的编号 / 公式。[contract-elf.md §2.2][ADR-0019 D2]
- **候选载体（逐条确认，二选一或并列）**：
  - **(a) 就地扩 `ADR-0019`**：追加 `D10…` 决策 + 就地修订其 `D2` 编号表，再落本合约正文；
  - **(b) 另立新 ADR**：以新 ADR 承载「动态重定位类型」，`ADR-0019` 文件**不动**。
  本合约**两案并存、不预设**；未逐条确认前**不得**写编号正文。[ADR-0025][spec-decision]
- **是否沿用第三方（如 RISC-V psABI）编号**：**待确认**（可核参照 = musl `include/elf.h` 的 `R_RISCV_*` 条目、RISC-V psABI 文档；与 `ADR-0025 D1`「沿用 RISC-V 编号」同理可类推，但**不自动**成立）。[ADR-0025 D1][spec-decision]
- **禁止**：**不得**自拟编号或公式（无用户确认即写入编号 = 违规）。[spec-decision]

### §4.5 溢出与未解析策略（**待确认**）

- 动态场景下需定：重定位值越界、未定义符号、缺失目标等如何处理（候选：link-time error / 运行期由 ldso 报错/终止），以及与 `ADR-0019 D6`（静态越界 = link-time error）的关系。**待用户逐条确认**。[ADR-0019 D6][spec-decision]

---

## §5 动态段与符号表

- **动态段**：`PT_DYNAMIC` + `.dynamic`（`SHT_DYNAMIC`）承载 `DT_*` 标签；必备子集受**两条**约束：①「musl ldso 实际消费的标签」（源码事实：`DT_SYMTAB` / `DT_STRTAB` / `DT_HASH` / `DT_GNU_HASH` / `DT_RELA` / `DT_RELASZ` / `DT_REL` / `DT_RELSZ` / `DT_JMPREL` / `DT_PLTRELSZ` / `DT_PLTREL` / `DT_PLTGOT` / `DT_NEEDED` / `DT_INIT` / `DT_INIT_ARRAY` / `DT_INIT_ARRAYSZ` / `DT_FINI` / `DT_FINI_ARRAY` / `DT_FINI_ARRAYSZ` / `DT_RPATH` / `DT_RUNPATH` / `DT_TEXTREL` / `DT_FLAGS` / `DT_FLAGS_1` / `DT_BIND_NOW` / `DT_RELR` / `DT_RELRSZ` / `DT_VERSYM` / `DT_DEBUG`）；② gABI 的标签通用语义（含 `DT_STRSZ` 等 strtab 尺寸类标签——其**是否/如何**落入 v5 待 §9 确认）。[外部权威 ELF gABI 第 5 章][外部权威 musl `ldso/dynlink.c`][spec-decision]
- **符号表 / 字符串表**：`.dynsym`（`DT_SYMTAB`）与 `.dynstr`（`DT_STRTAB`，尺寸标签 `DT_STRSZ`）为**必备**（gABI 要求；musl ldso 据此解析符号名）。[外部权威 ELF gABI 第 5 章][外部权威 musl `ldso/dynlink.c`]
- **哈希表口径（待确认）**：musl ldso **同时**支持 SysV Hash（`DT_HASH`）与 GNU Hash（`DT_GNU_HASH`），但**至少须存在其一**（`count_syms` 要求，源码事实）；DADAO 取哪种 / 是否双发**待用户逐条确认**。[外部权威 musl `ldso/dynlink.c`][spec-decision]
- **符号版本（待确认）**：musl 对 `DT_VERSYM` 有支持；DADAO 是否纳入**待确认**（若纳入，须一并定 `.gnu.version*` / `DT_VERNEED` / `DT_VERDEF` 的完整约定）。[外部权威 musl `ldso/dynlink.c`][spec-decision]
- **`DT_RELR`（紧凑相对重定位；待确认）**：musl 支持；DADAO 是否启用**待确认**（与 §4.4 编号方案联动）。[外部权威 musl `ldso/dynlink.c`][spec-decision]
- **不得静默兼容**：本节未定的标签 / 节，实现方**不得**自行约定；须先走 §9 确认。[spec-decision]

---

## §6 `PT_INTERP` 与启动 auxv（无内核下的注入者）

### §6.1 `PT_INTERP` 与 `ld.so` 路径约定（**路径待确认**）

- `PT_INTERP` 承载解释器**字符串路径**（gABI 第 5 章）；本项目的解释器 = musl ldso。[ADR-0025 D3][外部权威 ELF gABI 第 5 章]
- **事实（musl 命名规则）**：musl 的安装名规则为 `<syslibdir>/ld-musl-<arch><subarch>.so.1`（`Makefile` 中 `LDSO_PATHNAME`），且各目标以 `LDSO_ARCH` 标识（如 riscv64 为 `"riscv64"`）。[外部权威 musl `Makefile`][外部权威 musl `arch/riscv64/reloc.h`]
- **方案（待用户逐条确认）**：按上述规则，DADAO 侧**建议**取 `LDSO_ARCH = "dadao"` ⇒ 安装名形如 **`ld-musl-dadao.so.1`**，`PT_INTERP` 写其**绝对路径**；`syslibdir` 前缀（如 `/lib/`）与是否带 ABI 后缀具体取值**待确认**，**不得**自行拍定。[外部权威 musl `Makefile`][spec-decision]

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
- **待确认**：进入 ldso 与进入被测程序时的 `rbgp`（GP）/ `rbtp`（TP）初值由谁在何时设置（§2.4 同批确认）。[spec-decision][ADR-0018 C6]

### §6.6 边界

- QEMU user-mode 属 **P3**；其实现**须**遵循本合约（§6.2–§6.5），且**不得**充当 §8 的期望值来源。[ADR-0025 D6][ADR-0025 D7]
- 「谁扮演内核 / 加载器侧」的**唯一**承担者是 QEMU user-mode；本合约**不**引入内核目标、**不**定义内核侧接口。[ADR-0025 D2]

---

## §7 TLS 占位（与 `ADR-0025 D5` 联动；**本合约不在本任务定 TLS 模型**）

- **事实（musl 类别层）**：musl ldso **在类别层**需要 `REL_DTPMOD` / `REL_DTPOFF` / `REL_TPOFF`（+ 可选 `REL_TLSDESC`）；各目标须在 `arch/<arch>/reloc.h` 逐项映射（未映射即该类别不可命中）。[外部权威 musl `src/internal/dynlink.h`][外部权威 musl `arch/riscv64/reloc.h`][spec-decision]
- **事实（v5 寄存器）**：spec 已定义 `rb3` = `rbtp`（thread pointer）；v5 M3 起保留不分配。[DADAO-21 §寄存器规范 §RB寄存器][ADR-0018 C6]
- **归属未定**：musl 是否**硬依赖** TLS / 线程 = `ADR-0025 D5` 的**查证待办**（**尚未查证**）⇒ TLS 是否纳入 M8 **未定**。[ADR-0025 D5]
- **触发条件**：若 `D5` 查证结论为「musl 硬依赖」⇒ TLS **自动纳入 M8**（`D5` 原文口径），届时本合约须补：① TLS 模型（`TPOFF_K` / 是否 `TLS_ABOVE_TP` / TP 的建立者与时机）；② TLS 重定位类型与编号（并入 §4.3 / §4.4 的**逐条确认**流程）；③ `rb3`/`rbtp` 的初值与维护约定（§2.4 / §6.5）。**在此之前**，本合约**只留占位**。[ADR-0025 D5][spec-decision]
- **禁止**：在 `D5` 查证前**不得**先定 TLS 模型 / TLS 类型编号（无依据编号或模型 = 违规）。[spec-decision]

---

## §8 独立 oracle 口径（不从实现反推）

- **期望值来源（判据顺序）**：① **ELF gABI / System V ABI** 的通用语义（记录布局、公式、`DT_*` / `AT_*` 标签、Hash 结构）；② **musl `ldso` 行为**（版本锁定 v1.2.6，见 §1.3；只读参照）；③ **RISC-V + musl golden 对照**（同一程序跑对照面，`ADR-0025 D7`）。[ADR-0025 D7][外部权威 ELF gABI 第 4/5 章][外部权威 musl `ldso/dynlink.c`]
- **禁止**：**不得**从 v5 自身实现反推期望值——`llvm-project` 的 DADAO 后端/补丁、LLD、`qemu` 的 DADAO 端口/补丁、`linux-user`（§6.6）、本仓工具的输出**均不得**作期望值来源；期望值须独立派生自 ①/②/③。[ADR-0025 D7][spec-decision]
- **对照边界项**（端序、`long double`、`fenv`、UB、实现定义项等）按既有 `[spec-decision]` 登记为「**非判据真源**」，不据此判红。[ADR-0025 D7]
- **归属**：具体对照 harness / 判据 / 回归门控 = **P4**（`D6` 顺序之末）；本合约只钉口径与禁止项。[ADR-0025 D6]

---

## §9 待确认清单（**未经用户逐条确认前不得实现**）

| # | 项 | 状态 | 选项 / 指针 |
|---|----|------|-------------|
| 1 | 动态重定位**类型集**（名 / 编号 / 公式 / 落点字段） | **待用户逐条确认** | §4.3–§4.4；载体 **(a) 就地扩 `ADR-0019`（`D10…`）** vs **(b) 另立新 ADR** |
| 2 | `R_DADAO_*` 编号分配 / `R_DADAO_NUM` 顺延 | **待用户逐条确认** | §4.4（既有占用 0–5；不得复用 legacy 编号） |
| 3 | 是否沿用第三方（如 RISC-V psABI）编号 | **待用户逐条确认** | §4.4 |
| 4 | `PT_INTERP` 路径与命名（`ld-musl-dadao.so.1` 之类） | **待用户逐条确认** | §6.1 |
| 5 | 哈希表口径（SysV / GNU / 双发） | **待用户逐条确认** | §5 |
| 6 | 符号版本 / `DT_RELR` 是否纳入 | **待用户逐条确认** | §5 |
| 7 | GOT 基址寄存器（`rbgp`）与 `rbtp` 的初值 / 设置者 | **待用户逐条确认** | §2.4、§6.5 |
| 8 | TLS / 线程归属 ⇒ TLS 模型与类型 | **待用户逐条确认**（**前置：`ADR-0025 D5` 查证**） | §7 |
| 9 | 延迟绑定 vs 立即绑定（默认口径） | **待用户逐条确认** | §3 |
| 10 | 动态重定位的越界 / 未解析策略 | **待用户逐条确认** | §4.5 |

- 本清单**不是**决策；每项确认后按 `docs/Process-03-ADR编写规范.md` 与 `AGENTS.md`「ADR decision 逐条确认」流程落纸（就地修订 / 新 ADR / 落本合约正文）。[ADR-0025][spec-decision]
- **落纸规则**：编号 / 公式 / 命名类确认后，若属「就地修订 `ADR-0019`」则须用户逐条确认后方可改该 ADR；**本任务不改**任何既有 ADR 文件。[ADR-0025][spec-decision]

---

## 附录 A：来源对照

| 本合约 § | 内容 | 来源 |
|----------|------|------|
| §1.1 | 无内核目标；只覆盖用户态可见语义 | `ADR-0025 D2` |
| §1.2 | 角色分工（musl ldso / QEMU user-mode = 内核·加载器侧）；边界 | `ADR-0025 D2`/`D3`/`D6`/`D7` |
| §1.3 | 来源四分层；外部权威出处（gABI / musl / qemu，可核） | 外部权威（gABI 第4/5章、musl v1.2.6、qemu `c3d48b7d…`）；`ADR-0025 D3` |
| §1.4 | 术语与公式符号（`S`/`A`/`P`/`B`） | `ADR-0019 D3`；gABI 第 5 章 |
| §2.1 | `rb0`/`rbgp`/`rbtp` 角色；48 位地址 | `DADAO-21 §寄存器规范 §RB寄存器`；`SimRISC-00 §基址寄存器`；`contract-isa.md §1.5`；`ADR-0018 C6`；`ADR-0015 D1` |
| §2.2 | 两条寻址通路（PC 相对 / 绝对·基址相对）；PIC 指令域无须新类型的推导 | `ADR-0019 D2`/`D3`；`ADR-0021 D1`/`D3`；`ADR-0018 C7 D4` |
| §2.3 | `ET_DYN`（`-fPIC`/`-pie`/`-shared`）；与 M4 VA=PA 路径并存 | gABI 第 5 章；`ADR-0003 D5`；`contract-elf.md §5.2` |
| §2.4 | GOT 基址寄存器与初始化（待确认） | `DADAO-21 §寄存器规范 §RB寄存器`；`ADR-0018 C6`；`ADR-0025 D3`；`[spec-decision]` |
| §3 | GOT 槽 8 字节；PLT 绑定两路径；PLT 槽由动态重定位填充；访问路径 | `contract-abi.md §1.7`；gABI 第 5 章；musl `ldso/dynlink.c`；`ADR-0021 D3`；`ADR-0018 C7 D4` |
| §4.1 | `SHT_RELA` 记录型态；`Elf64_Rela` 布局与 `r_info` 位宽 | `ADR-0019 D1`；gABI 第 4 章；musl `src/internal/dynlink.h` |
| §4.2 | musl 类别集与默认不可命中；须映射的四类 | musl `src/internal/dynlink.h` / `ldso/dynlink.c` / `arch/riscv64/reloc.h`；`ADR-0025 D3` |
| §4.3 | 候选类型（`RELATIVE`/`GLOB_DAT`/`JUMP_SLOT`/`COPY`/`TLS_*`）与 gABI 公式（**待确认**） | gABI 第 4 章；musl；`contract-elf.md §3.1`；`[spec-decision]` |
| §4.4 | 既有编号占用 0–5 / `NUM`=6；不得复用 legacy；载体 (a)/(b)（**待确认**） | `contract-elf.md §2.2`；`ADR-0019 D2`；`ADR-0021 D2`；`ADR-0025`；`[spec-decision]` |
| §4.5 | 越界 / 未解析策略（**待确认**） | `ADR-0019 D6`；`[spec-decision]` |
| §5 | 动态段 `DT_*` 消费集；`dynsym`/`dynstr`；Hash 两型（**待确认**）；版本 / `DT_RELR`（**待确认**） | gABI 第 5 章；musl `ldso/dynlink.c`；`[spec-decision]` |
| §6.1 | `PT_INTERP` 字符串；musl 安装名规则；建议命名（**待确认**） | `ADR-0025 D3`；gABI 第 5 章；musl `Makefile` / `arch/riscv64/reloc.h`；`[spec-decision]` |
| §6.2 | musl 消费的 `AT_*` 集合 | musl `ldso/dynlink.c` / `ldso/dlstart.c`；gABI 第 5 章 |
| §6.3 | 注入者 = QEMU user-mode；`create_elf_tables` / `load_elf_interp` / `AT_BASE` | `ADR-0025 D2`/`D6`；qemu `linux-user/elfload.c` |
| §6.4 | 解释器路径解析（guest-root 前缀） | `ADR-0025 D2`/`D6`；qemu `linux-user/main.c` / `elfload.c` |
| §6.5 | 入口栈向量；SP/8B 对齐；`rbgp`/`rbtp` 初值（**待确认**） | musl `ldso/dlstart.c`；qemu `linux-user/elfload.c`；`contract-abi.md §2.1`；`DADAO-21 §函数调用规范 §The Stack Frame`；`[spec-decision]` |
| §6.6 | P3 边界；不得作 oracle；不引入内核目标 | `ADR-0025 D2`/`D6`/`D7` |
| §7 | TLS 占位与 `D5` 触发条件；不得先定模型 | `ADR-0025 D5`；musl `reloc.h`；`DADAO-21 §寄存器规范 §RB寄存器`；`ADR-0018 C6`；`[spec-decision]` |
| §8 | oracle 口径与禁止项；P4 归属 | `ADR-0025 D6`/`D7`；gABI；musl |
| §9 | 待确认清单与落纸规则 | `ADR-0025`；`[spec-decision]` |
