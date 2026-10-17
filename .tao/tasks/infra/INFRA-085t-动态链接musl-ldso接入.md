# INFRA-085t: 动态链接（musl `ldso` 接入 ⇒ 能编出动态 ELF）（`P2`）

**模块**：infra（**判定与理由见「§模块判定」**）
**项目里程碑**：M8
**依赖**：`ADR-0025`（`D6` = `P0 契约 → P1 musl 静态 → **P2 动态链接** → P3 qemu-linux-user → P4 对照/回归`；`D2` 无内核 / `D3` `ld.so` = **musl 自带 ldso** / `D4` musl 与 picolibc 并存 / `D7` golden 对照〔P4〕）；`ADR-0019 D10`（**动态重定位类型集与最终编号**：`NONE=0`/`REL26`=1…`ABS12`=5/**`ABS48`=6**/`JUMP_SLOT`=7/`RELATIVE`=8/`COPY`=9/`TLS_DTPMOD`=10/`TLS_DTPREL`=11/`TLS_TPREL`=12/`TLSDESC`=13/`NUM`=14；值类规则 / 公式）；`ADR-0026 D1–D8`（**动态链接行为口径**：ldso / `PT_INTERP`·`-dynamic-linker` / **仅 GNU hash** / 版本段·`DT_RELR` 都不做 / GOT·TP / eager（`BIND_NOW`）/ 越界 5 条 / 独立 oracle）；`ADR-0027 D5`（compiler-rt builtins = 独立库，picolibc/musl 共用）；**契约真源** = `.tao/contracts/contract-dynlink.md`（`§1`–`§10`；用户 **2026-10-14 逐条确认**，§9 = 裁定清单已定）；`INFRA-082t`（**`P1`**，`已验证` 2026-10-15：musl 补丁集 16 + `make build-musl` + 静态 ELF 可编出；**其 A2+A3 遗留 ⑤⑦⑧ 由本册承接**）；`INFRA-076t`（musl 1.2.6 取源与锁定，`已验证`）；`SPEC-140t`（musl TLS/TP 硬依赖查证，`已验证`）；`ISS-206`（`DADAO.def` 随 `D10` 改号 = **P2 必做**）〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 B/E）**：**「P2 必做」已不成立** ✗ —— ①②③ **三条均已落地**：① `DADAO.def` 改号〔+ `ELF.h`〕/③ 既有产物·向量排查随**阶段 B**；② `.tao/contracts/contract-elf.md §2.2` 同步随**阶段 E**（用户 2026-10-16 授权原话「**授权，但建议删除 `NUM = 6`**」，渠道 = 经主会话问答）；`ISS-206` 保持 `open`（待 `LLVM-094t` 任务级 `已验证` 回填 `closed`）；**生产者侧前置 = `LLVM-094t`**（2026-10-16 已立；阶段 A/B/E 已落地、C 部分交付、D 待做）〕、`ISS-222`（LLVM 后端缺口 4 类）、`ISS-223`（13 源排除）、`ISS-229`（L2/L3 并发假 FAIL ⇒ 验收须**串行**）；`docs/Process-01`（组件补丁组织与构建编排）；`ADR-0016`（install 落点）
**状态**：待开始
**阶段进度**：A ⏳ ／ B ⏳ ／ C ⏳ ／ D ⏳ ／ E ⏳

> **`**状态**` 口径**：本任务 = **一个任务书、多阶段验收**（照 `SPEC-142t`/`SPEC-143t`/`INFRA-082t` 先例）⇒ `**状态**` 表**任务级**（**阶段全部验收通过**才置 `已验证`）；**阶段级**进度见上行 `**阶段进度**`。

> **⛔ 阻塞 / 前置（2026-10-16 追加，**必读**）**：本册**动态链接 / GOT 取址**相关工作**当前被阻塞** —— **`ISS-230`**（`ADR-0026`「超 ±2 KiB 用 `ABS48` 序列 + `ldm.o_rrri_rb`」在现有 ABI 下**不可实现**：链接器无可用 `rd`、ISA 侧无宽 PC 相对重定位类型）**待用户给方案**（用户 2026-10-16 原话「**你不用试了，过会儿我告诉你解决方法**」）⇒ **用户给出解法前，与 `.got` 可及性（GOT 取址机制）相关的工作不得开工**。三条候选（**(a)** 编译器发两段式 / **(b)** 让出链接器临时寄存器或新增宽相对重定位类型〔触及 ISA·ABI ⇒ 须 `ADR` + `spec/` 授权〕/ **(c)** 接受布局约束）**均须用户裁定**。依据指针 = `.tao/knowledge/issues.yaml` `ISS-230` + `.tao/tasks/llvm/LLVM-094t-llvm-PIC与动态链接支持.md`「遗留问题（阶段 C）①」。
>
> **✅ 解除注记（2026-10-16）**：`ADR-0028`（GOT/PLT 远距离取址）已由用户 2026-10-16 **逐条确认** ⇒ **`Accepted`**（设计定案 = 新类型 **`R_DADAO_REL32`=`14`**、**`R_DADAO_NUM`=`15`**；GOT 取址 **3 条/次**；PLT **内联去槽**、`pltEntrySize` `24`→`16`；**取消「`.got` 必须贴访问点 ±2 KiB」的布局义务**，可达 ±2 GiB）⇒ **与 `.got` 可及性（GOT 取址）相关的工作不再被阻塞**；上文「三条候选均须用户裁定」「用户给出解法前…不得开工」**由该 ADR 取代**（**原文保留为历史** ✗）。实现落点 = **`LLVM-095t`**（`.tao/tasks/llvm/LLVM-095t-REL32与PLT内联.md`，2026-10-16 立、`待开始`）⇒ 本册**消费**其产出。**本册 `**状态**` 不改**（仍 `待开始`）、本册其余范围不变 ✓。
>
> **⚠️ 通道口径订正（2026-10-17 追加）**：上条「✅ 解除注记（2026-10-16）」的通道口径**已被 `ADR-0029`（`Accepted`；用户逐条确认）取代** ✗ ⇒ 新类型 = **`R_DADAO_PCREL_HI`=`14` / `R_DADAO_PCREL_LO`=`15`**（`R_DADAO_NUM` `14 → 16` ✓）；GOT 取址 = **`aip.si` + `ld.o [rbX, %pcrel_lo]`** ✓；PLT = **3 条 / 12 B**（`pltEntrySize` `24 → 12`）✓；实现落点 = **`LLVM-095t`（已完成 ✓）**。上文（`REL32`=`14` / `NUM`=`15` / GOT 3 条 / PLT 16 B）**原文保留为历史** ✗。
>
> **✅ 阻塞解除（2026-10-17）**：`ISS-230` 由 `ADR-0029` 解决（GOT 取址改 `aip.si` 通道）；**`P2`（musl `ldso` 接入）重新排入**，按 `ADR-0025 D6` 原序应在 **`P3` 之前**。**依据指针** = `.tao/adr/adr-0029-rela-si-auipc-pairing.md`（**`Accepted`**，用户逐条确认；`ADR-0028` 已转 **`Superseded`**）+ `.tao/knowledge/issues.yaml` `ISS-230`（仍 `open`、`resolved_by` 仍 `null`：**设计层阻塞已解**，待 `LLVM-095t` 实现验收后回填 `closed`）。上文「⛔ 阻塞 / 前置（2026-10-16 追加）」与「✅ 解除注记（2026-10-16，`ADR-0028`）」**均保留为历史** ✗；**本册 `**状态**` 不改**（仍 `待开始`）✗。

> **编号留痕（现场取号，2026-10-16）**：`INFRA-085` 经 `.tao/tasks/**` + `.tao/archive/**` + `git log --all --name-only`（全历史）复核**从未被占用** ⇒ 取 **`INFRA-085t`**（`lessons §3.21`「编号须全仓〔含历史〕唯一」）。

## 立项来源 / 路线位置

- **路线 = `ADR-0025 D6` 的第 2 步（`P2`）**；`milestones.md`「M8 任务链」第 2 条即本项（原文「**新立任务**（**任务书待落盘**）」）⇒ **本册即为该「待落盘」任务书**。
- **用户裁定（2026-10-15，渠道 = 经主会话问答，原话原样引录，源 = `milestones.md`「M8 任务链」）**：「**不用改D6，就按原来的顺序进行，然后增加embench和两个新的test suite的测试；测试的时候区分静态链接和动态链接，先测静态链接，再测动态链接**」⇒ ① `ADR-0025 D6` **正文零改动** ✗；② 推论（由该裁定得出）：**`P1`/`P2` 只交付「能编」**（静态 ELF / **动态 ELF**），**「跑 + 测」统一在 `P3`（`qemu-user`）** ⇒ **本册只到「能编出 + 静态可核」**，**不含运行验证**。
- **测试面（用户 2026-10-15 要求）**：三套 = `embench-iot` + `libc-test` + `llvm-test-suite`，**每套分静态/动态两轮、先静态后动态** ⇒ **动态档的「跑」在 `P3`**（本册**不**跑）。
- **`P1` 遗留承接（`INFRA-082t §阶段 A2+A3 遗留`，逐条）**：⑤ `GETFUNCSYM` 给**链接期绝对地址** ⇒ **P2 须改为基址相关**（随 `ldso` 真重定位）；⑦ 无 `AT_PHDR`/`PHNUM`/`PHENT` ⇒ **静态 `__thread` 未打通** ⇒ P2 处理；⑧ `sigsetjmp` 未实现（**视需要**，见「待确认项 ③」）。

## 目标（判据 = 「**能编出动态 ELF**」）

- **交付**：musl 以**动态**方式构建出 **`libc.so`**（`ET_DYN`，内含 `ldso`），并经 **`-dynamic-linker /lib/ld-musl-dadao.so.1`** **链接出动态可执行**（带 `PT_INTERP` + `DT_NEEDED`）；重定位表与 `ADR-0019 D10` / `contract-dynlink.md §4.3` **逐条一致**。
- **判据边界**：**能编出 + 静态可核**（`readelf`/`llvm-readobj`/`nm` + 独立 oracle）——**不跑**（跑 = `P3`）。

### 静态与动态两条线（**用户要求**，2026-10-17）

> **用户原话（逐字引录，渠道 = 经主会话问答，2026-10-17）**：「**可以进行INFRA-085t，注意：静态和动态都需要支持**」

- **静态线（不回归，硬要求）** ✓：`P1`（`INFRA-082t`）的**静态全链（阶段 A/B/C）必须保持绿** —— 静态档构建 / 静态 ELF 产出与既有门控**逐字节 / 逐条对照不回归** ✗ 漂移；**显式验收**见「验收标准 8」。
- **动态线（本册目标）** ✓：= **能编出动态 ELF** + **`PT_INTERP` = `/lib/ld-musl-dadao.so.1`**（该路径为**符号链接 → `libc.so`**），按 `contract-dynlink §6.1`（构建侧**显式**传 `-dynamic-linker /lib/ld-musl-dadao.so.1`）。
- ⇒ **两条线同册**：动态线的任何改动**不得**以牺牲静态线为代价；静态线证据与动态线证据**分开留存**（`.work/evidence/<任务ID>/`）。

## 模块判定（architect 现场判定，含理由）

- **判定**：归 **`infra`**。
- **理由**：① **`musl` 的模块归属已有用户裁定**——2026-10-14 原话「**musl归infra**」（源 = `milestones.md`「新组件模块归属裁定落纸」②）；② 本册的**门面 / 交付面** = **musl 侧（`ldso` 接入、`arch/dadao` 宏）+ 构建侧（`tools/infra/build_musl.py` / `Makefile` / 安装落点）**，与 `INFRA-082t`（`P1`）**同族**；③ 产出命名（`ld-musl-dadao.so.1 → libc.so`）与安装落点属「组件 + 构建」面。
- **⚠ 跨模块面（显式披露，供用户复核）**：**「能编出动态 ELF」的生产者侧**（把 `ET_DYN` / `.dynamic` / `GOT`·`PLT` / 动态重定位**发出来**的那一半）属 **`llvm` 模块**：
  - `llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def` + `ELF.h` 类型枚举（**`ISS-206`①**）；
  - CodeGen 的 **PIC / GOT** 寻址（现无私）；
  - `lld/ELF/Arch/DADAO.cpp` 的 **`ET_DYN` / `.dynamic` / GNU hash / `GOT`·`PLT` / 动态重定位**（现**只有静态** `relocate` + `getRelExpr`——现场已核，见「已知事实 4」）。
  - 〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 A/B/C）**：上列「**现无私** / **现只有静态**」**均已不成立** ✗ —— 生产者侧已落地：**阶段 A** CodeGen PIC/GOT（GOT 槽走 `rb0` PC 相对、`-fPIC`/`-fPIE`）；**阶段 B** `DADAO.def` 改号 + LLD `ET_DYN`/`.dynamic`/`.dynsym`/`.dynstr`/仅 `.gnu.hash`/`.rela.dyn`/`.rela.plt`/`.got`·`.got.plt`·`.plt` + `DT_SONAME`；**阶段 E** 编号同步（`contract-elf §2.2`）；**阶段 C** ② 主动拒绝 + ③ A7 基线重定（⚠ 阶段 C ①「两段式」**阻塞于 `ISS-230`**、**阶段 D** 待做）⇒ 本册**消费**上述产出（依赖单向 `llvm → infra`）〕
- **处置 = 见「待确认项 ①」**：**(a) 拆 `LLVM-094t`（生产者侧）先行 + 本册（消费侧 + 构建）串行**（**推荐**：模块归属真源 / 依赖单向 `llvm → infra` / 满足「每任务可独立验收、可被单个 engineer 完成」）｜**(b) 单册跨模块执行**（先例 = `INFRA-082t` 含 QEMU 侧 `SYS_UMON_SYSCALL` 服务，**范围扩大已在册内显式标注**）。**未裁定前按 (a) 口径理解本册**（= 只做 `infra` 面），**不自行扩大**。〔**收尾注记（2026-10-16）**：裁定**已定 (a)**（用户 2026-10-16「**3、可以**」追认，渠道 = 经主会话转达）⇒ `LLVM-094t` 已立、本册按 (a) 口径（只做 `infra` 面）；**(a) 裁定内容本身不改** ✗〕

## 做（分阶段 A–E；**每阶段各自验收**）

> **面** 列 = 该行工作归属：`infra` = 本册（musl / 构建）；`llvm` = 生产者侧（若「待确认项 ①」裁定 (a)，则该列项移入 `LLVM-094t`）。〔**收尾注记（2026-10-16）**：裁定**已定 (a)** ⇒ 该列项**已移入** `LLVM-094t`（阶段 A/B/E 已落地、C 部分交付、D 待做）〕〔**2026-10-17 追加**：生产者侧实为 **`LLVM-095t`（已完成 ✓）**；`LLVM-094t` **已收束** ✓（其 ① 由 `ADR-0029` 取代、阶段 `D` 已结）〕

| 阶段 | 名称 | 内容 | 出口判据 |
|---|---|---|---|
| **A** | **共享库与 PIC** | **A1**（`infra`）musl 以 **`-fPIC` / `-shared`** 构建出 **`libc.so`**（`ET_DYN`）+ **`.so` 命名与符号链接** `ld-musl-dadao.so.1 → libc.so`（安装落点按 `ADR-0016`；`build_musl.py` / `Makefile` 接线）；**A2**（`llvm`）生产者侧 `-shared` 能力：`ET_DYN` 输出 + `.dynsym`/`.dynstr`/`.dynamic` + **仅 GNU hash**（`--hash-style=gnu`）+ `DT_SONAME` + `DADAO.def` 改号（`ISS-206`①） | `readelf -h libc.so` = **`ET_DYN` + 大端**；`readelf -d` 有 **`DT_SONAME`**、**`DT_GNU_HASH`**，**无** `DT_HASH`、**无** `DT_RELR`/`DT_RELRSZ`、**无**版本段（`contract-dynlink §5` 裁定 5/6/7）；符号链接指向正确 |
| **B** | **动态可执行** | **B1**（`infra`）构建侧**显式**传 `-dynamic-linker /lib/ld-musl-dadao.so.1`（**不改 lld 默认值**，`ADR-0026 D2`）；**B2**（`llvm`）生产者侧支持 `PT_INTERP` + `DT_NEEDED`（动态可执行链接） | `readelf -l` 的 **`PT_INTERP` 字符串逐字节 = `/lib/ld-musl-dadao.so.1`**；`readelf -d` 含 **`DT_NEEDED`** |
| **C** | **`ldso` 接入** | **C1**（`infra`）`ldso/dlstart.c` / `ldso/dynlink.c` **真接入**（`GETFUNCSYM` **改基址相关**〔P1 遗留 ⑤〕、`CRTJMP` 复核、`arch/dadao/reloc.h` 类别映射复核）；**C2**（`llvm`）**`PT_DYNAMIC` / hash（仅 GNU） / `DT_*` 必备子集** + **eager 绑定**（`DT_BIND_NOW` / `DF_BIND_NOW`，`ADR-0026 D6`） | `libc.so` 内 `_dlstart` / `_dlstart_c` 存在（`nm` / `readelf -s`）；`.dynamic` 必备标签到场（`DT_SYMTAB`/`DT_STRTAB`/`DT_STRSZ`/`DT_GNU_HASH`/`DT_RELA`/`DT_RELASZ`/`DT_PLTGOT`/`DT_BIND_NOW`）；**静态度量**（不跑） |
| **D** | **TLS 动态** | **D1**（`infra`）**`PT_TLS`** + `TP = rb3`（`contract-abi §1.2`）+ `TLS_ABOVE_TP`（`GAP_ABOVE_TP` / `DTP_OFFSET`，逐 arch 定值归 musl 宏）+ `DTPMOD`/`DTPOFF`/`TPOFF` 类型与公式（`ADR-0019 D10`）+ **静态 `__thread`**（P1 遗留 ⑦：crt 侧 auxv 注入之需）；**D2**（`llvm`）TLS 类动态重定位**发射** | 有 TLS 变量时 `readelf -l` 有 **`PT_TLS`**；`readelf -r` 出现的 TLS 类**编号与 `§4.3` 一致**；`__thread` 变量可编译并落 TLS 重定位 |
| **E** | **重定位与越界** | **`ABS48` 两段式**（超 `R_DADAO_REL12` 的 ±2 KiB ⇒ `ABS48` 序列把偏移算进 `rd` + **`ldm.o_rrri_rb`** 落 **`rb`**、随后 `jump rbX, rd0, 0`；**跳转用途必须落 `rb`**）+ **`JUMP_SLOT`** / **`RELATIVE`**；**`COPY` / `TLSDESC` 不发射、遇即报错**；**§10 越界 5 条**〔**⛔ 阻塞（2026-10-16）**：其中 **`ABS48` 两段式 / GOT 可及性**部分**阻塞于 `ISS-230`**、**待用户解法**（见文首「⛔ 阻塞 / 前置」）；`JUMP_SLOT`/`RELATIVE`/`COPY`·`TLSDESC` 部分不受阻〕 | 重定位表含 `ABS48`/`JUMP_SLOT`/`RELATIVE`，且**公式与 `ADR-0019 D10` 逐条一致**（**独立 oracle** 核，见验收 3）；`COPY`/`TLSDESC` 注入例 ⇒ **显式报错**（非静默）；越界例 ⇒ 链接期 / 装载期报错〔**2026-10-17**：通道已定为 **`aip.si` + `ld.o rbX,[rbX,%pcrel_lo(<站点>)]`**（`ADR-0029`；**`ABS48` 两段式已废弃** ✗）；**阻塞已解除** ✓ —— `ISS-230` 由 `ADR-0029` 解决，`LLVM-095t` 已实现并验证（默认布局 `-shared` rc=0、PLT 12 B ✓）；本行上文（`ABS48` 两段式 / `ISS-230` 阻塞）**原文保留为历史** ✗〕 |

## 依据（口径真源；**引用，不复制正文**）

- **契约**：`.tao/contracts/contract-dynlink.md` —— `§1`（范围/角色/术语）、`§2`（PIC/PIE 与 `rb0`/`rbgp`/`rbtp` 口径）、`§3`（GOT/PLT、eager、`DT_PLTGOT`、两段式）、`§4.3`–`§4.4`（**类型总表与编号**）、`§5`（动态段 / `dynsym` / **仅 GNU hash** / 版本段·`DT_RELR` 都不做）、`§6.1`（**`PT_INTERP` = `/lib/ld-musl-dadao.so.1`**，符号链接 → `libc.so`，构建显式传 `-dynamic-linker`）、`§7`（TLS 纳入；TP 定值归 musl 宏）、`§8`（**独立 oracle 口径与禁止项**）、`§9`（裁定清单）、`§10`（失败与越界 5 条）。
- **决策**：`ADR-0019 D10`（类型号 / 公式 / 语义）、`ADR-0026 D1–D8`（行为类口径）、`ADR-0025 D6`（路线，**不改**）、`ADR-0027 D5`（builtins 归属）。
- **P1 承接**：`INFRA-082t`（`§阶段 A2+A3 遗留` ⑤⑦⑧ / `§实现约束与阶段 A1 遗留`）；`test-set 触发条件`（`LLVM-093t` 锁条目 `role`「baseline run deferred until musl static/dynamic works」）。
- **参考仓库（`DADAO-0628`）**：**内容溯源，非执行必需** —— 只读 `.cache/refs/**`、**不写回、不复制代码**；`SPEC-144t` 结论可借鉴者仅 **工程流程/教训**，其寄存器约定（`rd16`/`tp=rb4`）、`interp`/`gem5` 四方差分**不借鉴**（`milestones.md`「`DADAO-0628` 对照（结论层）」）。
- **补丁 / 构建形态先例**：`INFRA-057t`（picolibc）、`INFRA-082t`（musl `P1`），**只读**。

## 已知事实（供执行，**勿重复查证**；源已现场标注）

1. **`P1` 已达成**（`INFRA-082t`，`已验证` 2026-10-15）：musl 补丁集 **16** 补丁（`components/musl/{README.md,changelog.md,patches/**,series}`）+ `make build-musl`（`--disable-shared` **静态**）+ 静态 ELF 可编出（`ELF64` / **大端** / `ET_EXEC` / **无 `PT_INTERP`**）。
2. **`ldso` 源在位**（现场核）：`.work/source/musl/ldso/{dlstart.c,dynlink.c}`；musl 1.2.6 的 `ldso/` 目录**只有这两个文件**（per-arch 差异走 `arch/<arch>/reloc.h` 宏，**无** per-arch `ldso/arch/**` 目录）。
3. **`arch/dadao/reloc.h` 已就位**（`P1` 产出；**本册基线**）：`LDSO_ARCH "dadao"`、`TPOFF_K 0`、八类 `REL_*` 映射到 `R_DADAO_ABS48`/`JUMP_SLOT`/`RELATIVE`/`COPY`/`TLS_*`/`TLSDESC`（号值 = `D10` 最终号）、`CRTJMP`（`rd2rb` + `jump`）、`GETFUNCSYM`（**注释已自标**：现给**链接期绝对地址**、**P2 须改基址相关**）⇒ **P2 的 arch 宏层基线已在**，改点 = `GETFUNCSYM` 基址相关化 + TLS 宏复核（`pthread_arch.h` 的 `GAP_ABOVE_TP` / `DTP_OFFSET`）。
4. **生产者侧现状（现场核 `components/llvm-project/patches/**`；`ADR-0026 §Consequences 1/3` 的「P2」项）**：
   - `llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def` = `ABS48`**=0** … `ABS12`=5、`NUM`**=6** ⇒ **与 `ADR-0019 D10` 不一致**（`ISS-206`① **必改**；改后须同步 `ELF.h` 枚举与既有产物/向量排查 = `ISS-206`③）。
   - `DADAOTargetMachine.cpp` 默认 **`Reloc::Static`** ⇒ **无 PIC**；`DADAOISelDAGToDAG` 对 `GlobalAddress` 走**绝对地址 materialize**（`set.zw`/`or.w` + `R_DADAO_ABS48`），**非 GOT 间接**。
   - `lld/ELF/Arch/DADAO.cpp` **只有静态** `relocate` + `getRelExpr`；`Target.{cpp,h}` 仅注册目标 ⇒ **无** `GOT`/`PLT`/`.dynamic`/hash/动态重定位发射。
   - 〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 A/B）**：本条第 1–3 子项**均已不成立** ✗ —— ① `DADAO.def` 已改号（`NONE`=0 / 静态 `1`–`5` / `ABS48`=**6** / 动态 `7`–`13` / `NUM`=**14**，逐行 = `ADR-0019 D10`；现场核 `.work/source/llvm-project/llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def`）随**阶段 B**；② CodeGen 已支持 `-fPIC`/`-fPIE`、GOT 槽走 `rb0` PC 相对（**阶段 A**）；③ LLD 已可产 `ET_DYN` + `.dynamic`/`.dynsym`/`.dynstr`/仅 `.gnu.hash`/`.rela.dyn`/`.rela.plt`/`.got`·`.got.plt`·`.plt` + `DT_SONAME`（**阶段 B**）；⇒ 本册**消费**之、**不重复实现**〕
5. **`contract-elf.md §2.2` 仍是旧号**（`ABS48=0` / `NUM=6`）⇒ `ISS-206`②；**契约正文改动须用户授权**（见「待确认项 ⑥」）。〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 E）**：**本条已不成立** ✗ —— `.tao/contracts/contract-elf.md §2.2` 已按 `ADR-0019 D10` 同步（15 行终表：`NONE`=0 / 静态 `1`–`5` / `ABS48`=**6** / 动态 `7`–`13` / `NUM`=**14**）；**已获用户授权**（原话「**授权，但建议删除 `NUM = 6`**」，2026-10-16，渠道 = 经主会话问答）+ 同变更删除 `spec/Toolchain-01` 旧 `NUM`=6 字面量并重算该册 `sha256`〕
6. **既有产物 / 向量排查（`ISS-206`③）尚未完成**：现场 `grep` `R_DADAO_*` 在 `tests/**` **只命中注释 / 文档字符串**，**未**见写死的类型号字段 ⇒ **仍须在本册逐条排查并留证**（**不得**据此写成「已确认无命中」）。〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 B）**：**本条已不成立** ✗ —— `ISS-206`③ 已随**阶段 B** 落地：现场命中 **4 处** lit 向量注记（`dd-symbol`/`m6-callconv`/`rela-addend`/`rela.s`）并同步；全仓复核 `tests/vectors/**` / `contracts/**` **旧号 0 命中**，旧号仅存 `.tao/archive/**` 历史层 ⇒ 本册**无需**再行排查〕
7. **端序 = 大端（BE）**：`ADR-0003 D1`（`EI_DATA = ELFDATA2MSB`）；`AUDIT_ARCH_DADAO` = BE64（`contract-syscall §1.3`）；上游测试多在 LE 跑 ⇒ **BE 敏感用例须自成一面**。
8. **验证面现状**：**无 `qemu-user`**（`P3`）⇒ 本册**不可**有任何「运行通过」叙述；**L2/L3 不得并发**（`ISS-229`：共享安装根竞争 ⇒ 假 FAIL）；`JOBS=8`、**禁全核** `-j$(nproc)`。
9. **口径不可自拟**：类型号 / 公式 / 语义 = `ADR-0019 D10` + `contract-dynlink §4.3`；行为 = `ADR-0026 D1–D8`；**均 `Accepted`（用户 2026-10-14 逐条确认）** ⇒ **不得**自拟编号 / 公式 / 行为、**不得**自写 loader 替代 musl `ldso`（`ADR-0025 D3`）。

## 接口规范

- **输入**：`ADR-0019 D10` / `ADR-0026 D1–D8` / `ADR-0025`（`D2`/`D3`/`D4`/`D6`/`D7`）、`.tao/contracts/contract-dynlink.md`、`contract-elf.md`（只读；`§2.2` **已于 2026-10-16 随 `LLVM-094t` 阶段 E 同步**，用户授权原话「**授权，但建议删除 `NUM = 6`**」⇒ 原「同步须授权」**已不成立** ✗）、`INFRA-082t`（`P1` 产出与遗留）、`.work/source/musl/**`（**只读**：源码检出）、`components/llvm-project/patches/**`（**只读**：现状）、`.dadao/cross-toolchain/**`（工具链 + sysroot，**只读**）。
- **输出**：
  1. **musl 侧补丁**：`components/musl/patches/**` + `series`（**树形补丁 + 一文件一补丁**，`docs/Process-01`；`check-patch-tree` 机械校验）——`ldso` 接入所需改动（含 `GETFUNCSYM` 基址相关化）与 `arch/dadao/**` 复核改点。
  2. **构建 / 安装接线**：`tools/infra/build_musl.py`（`-shared` / PIC 档 + `.so` 命名 + 符号链接 `ld-musl-dadao.so.1 → libc.so`）+ `Makefile`（同型 target；`JOBS=8`）+ 安装落点按 `ADR-0016`（**不硬编码路径**，走 `manifests/` 定位机制）；**动态可执行链接命令显式带 `-dynamic-linker /lib/ld-musl-dadao.so.1`**。
  3. **（若裁定 (b) 跨模块）生产者侧补丁**：`components/llvm-project/patches/**`（`DADAO.def` 改号 + CodeGen PIC/GOT + MC/`ELF.h` 枚举 + LLD `ET_DYN`/`.dynamic`/GNU hash/`GOT`·`PLT`/动态重定位）；**若裁定 (a)** ⇒ 移入 `LLVM-094t`，本册只**消费**。〔**收尾注记（2026-10-16）**：裁定**已定 (a)** ⇒ 生产者侧补丁**归 `LLVM-094t`**（阶段 A/B 已落地），本册只**消费**；本册**不产** `components/llvm-project/**` 改动〕
  4. **验证 / 证据**：`.work/evidence/<任务ID>/run.sh`（**一键证据**，含「注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿」）+ 原始输出落 `.work/log/infra/**`；本任务书完成区 + `milestones.md` 流水行。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`（上游只读册，须用户事先授权）、`contracts/`（机器数据）、`.tao/contracts/**`（正文，须授权）；**不改测试集内容**（`libc-test`/`llvm-test-suite`/`embench-iot` 均 `patchless`）；**组件源一律 git 基线**（改 musl / llvm-project 只经 `patches/**`，**不得**直接改 `.work/source/**`）；**禁** `git add -A`、**禁** `git checkout/restore/stash`；**计数不写死**（现场派生）；**期望值独立**（`contract-dynlink §8`：不从 LLVM / LLD / QEMU / 本仓工具反推）。

## 依赖与先后

- **已满足**：`P0` 契约（`SPEC-138t`/`SPEC-139t` 均 `已验证`）、`P1`（`INFRA-082t` `已验证`）、`ADR-0019 D10`/`ADR-0026`（均 `Accepted`）。
- **生产者侧（待定）**：见「待确认项 ①」——(a) 需 **`LLVM-094t`（待立）先行**〔含 `ISS-206`①〕；(b) 本册内跨模块执行（范围扩大，须显式标注供用户复核）。〔**收尾注记（2026-10-16）**：本条「**待定** / **待立**」**已不成立** ✗ —— 裁定 **(a)**（用户「**3、可以**」追认，渠道 = 经主会话转达）；`LLVM-094t` **已立**（`.tao/tasks/llvm/LLVM-094t-llvm-PIC与动态链接支持.md`）：阶段 A/B/E 已落地、C 部分交付（① 阻塞 `ISS-230`）、D 待做 ⇒ 本册的前置**已具备**（消费其产出）〕
- **串行约束**：与任何同改 `components/musl/**`、`components/llvm-project/**`、`manifests/components.lock.toml`、`Makefile`、`tools/infra/**` 的任务**一律串行**（不得并行）；**同一工作树同一时间只允许一个写工作树**的子代理。
- **后续（不在本册范围）**：`P3`（`qemu-user`；**含三套测试集的静态档 + 动态档运行**）、`P4`（对照 / 回归 + RISC-V musl golden）；`INFRA-079t`（builtins，**撞缺口才引入**）、`ISS-222`/`ISS-223`（`llvm` 模块面）。

## 验收标准

1. **`libc.so` 产出**：`ET_DYN`；`readelf -d` 有 **`DT_SONAME`** + **`DT_GNU_HASH`**；**无** `DT_HASH`、**无** `DT_RELR`/`DT_RELRSZ`、**无**版本段（`DT_VERSYM`/`DT_VERNEED`/`DT_VERDEF`）（`contract-dynlink §5` 裁定 5/6/7）；`.so` 命名 + 符号链接 `ld-musl-dadao.so.1 → libc.so` 正确。
2. **动态可执行**：`ET_EXEC` 或 PIE（`-pie` ⇒ `ET_DYN` + `e_entry`）；**`PT_INTERP` 字符串逐字节 = `/lib/ld-musl-dadao.so.1`**；`DT_NEEDED` 存在。
3. **重定位表（契约逐条）**：含 `R_DADAO_ABS48`(6) / `R_DADAO_JUMP_SLOT`(7) / `R_DADAO_RELATIVE`(8)，**公式与 `ADR-0019 D10` 逐条一致**（`ABS48`/`JUMP_SLOT` = `S+A` 无符号 48 位；`RELATIVE` = `B+A` 无符号 48 位）。**独立 oracle**：期望值用 `readelf`/`llvm-readobj` 的**独立解析** + 依公式**独立计算**核对，**不从 v5 自身实现（LLVM/LLD/QEMU/本仓工具）反推**（`contract-dynlink §8`）。
4. **端序 = 大端**：`EI_DATA = ELFDATA2MSB`；至少 **1 例 BE 敏感**证据（多字节字段字节序，如 `ABS48` 数据槽 `00 00 A5 A4 A3 A2 A1 A0` 形态）。
5. **门控**（各留**自身**真实 rc，**禁** `cmd | tee` 吞码）：`make check`（**L1**）、**`make check-modules`（L2，任务收尾；串行、禁与 L3 并发——`ISS-229`）**、`make check-patch-tree`、`make check-source-state`、`check-knowledge-refs`、`check-knowledge-dir`、`check-no-residue`、`make check-tasks`、`python3 tools/infra/check_issues.py`、`check-component-changelog` 各 **rc=0**；`make check-full`（L3）在里程碑 / `/complete` 跑。
6. **可达 FAIL 证据**：`.work/evidence/<任务ID>/run.sh` 可跑通，**每条断言有可达 FAIL 路径**（注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿；还原用 `cp` + md5 对账，**禁** `git checkout/restore/stash`）；**禁恒真断言**、**计数不写死**。
7. **不做运行验证（显式声明）**：本册**不跑**动态 ELF（无 `qemu-user`）⇒ 若完成区出现任何「运行通过 / E2E 通过」叙述，**视为越界**；「跑」= `P3`（用户 2026-10-15「先静态、再动态」的落地位置）。
8. **静态不回归（显式验收，2026-10-17 追加；对应用户「静态和动态都需要支持」）**：静态档判据**全部保持 rc=0**，且与刷新前基线**逐字节对照一致** —— ① **构建**：静态档（`make build-musl`，`--disable-shared`）**rc=0**（留**自身**真实 rc，禁 `tee` 吞码）；② **静态产物 4 项事实逐条复现**（`readelf -h` / `-l` / `-d` 现场输出）：`ELF64` / **`EI_DATA = ELFDATA2MSB`** / **`ET_EXEC`** / **无 `PT_INTERP`**、**无 `DT_NEEDED`**；③ **逐字节对照（判据）**：静态侧产物（`libc.a` + 至少 1 例静态 ELF）的 **`sha256`** 与**刷新前基线**（`INFRA-082t` 证据）逐条比对 ⇒ **不一致即 FAIL**；若确因本册**预期改动**而变化，须**逐条列出差异 + 依据**（改动点 / 契约条款），**不得**默许漂移；④ 证据脚本（`.work/evidence/<任务ID>/run.sh`）含**可达 FAIL** 路径（改坏任一项 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。

## 不做项（显式）

1. **`qemu-user` / `linux-user`**（`P3` ✗）与**运行**验证（含三套测试集的动态档）✗。
2. **RISC-V musl golden 对照 / 对照 harness / 回归门控**（`P4` ✗）。
3. **改 `spec/`**（上游只读册；须用户事先授权）✗、**改 `contracts/` 机器数据** ✗；**`.tao/contracts/**` 正文**默认不改（含 `contract-elf.md §2.2` 同步，须授权——见「待确认项 ⑥」）✗。〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 E）**：`contract-elf.md §2.2` 同步**已授权并落地**（用户原话「**授权，但建议删除 `NUM = 6`**」；落点 = **`LLVM-094t` 阶段 E**，**非**本册）⇒ 本条对**本册**仍成立（本册**不**改 `.tao/contracts/**`），仅「须授权」所指事项**已完成** ✗〕
4. **改测试集内容**（`libc-test` / `llvm-test-suite` / `embench-iot`，均 `patchless`）✗。
5. **自写 `ld.so`**（`ADR-0025 D3` / `ADR-0026 D1` ✗）；**新增 ISA 指令**（`ADR-0026 D5` ✗）；**relaxation**（`ADR-0019 D7` ✗）。
6. **`ISS-222` 后端缺口 4 类 / `ISS-223` 13 源排除**的本册收口 ✗（`llvm` 模块面；撞上即登记 + 转出——见「待确认项 ④」）。

## 待确认项

| # | 项 | 我的默认（**待用户确认**） | 备选 / 影响 |
|---|---|---|---|
| ① | **跨模块切分**：生产者侧（`DADAO.def` 改号 / CodeGen PIC·GOT / MC 枚举 / LLD `ET_DYN`·`.dynamic`·GNU hash·`GOT`·`PLT`）属 `llvm` 面 | **(a) 拆 `LLVM-094t`（待立）先行 + 本册（`infra` 面）串行**（理由 = 模块归属真源 / 依赖单向 `llvm→infra` / 任务粒度「可独立验收、单人可完成」）〔**收尾注记（2026-10-16）**：本行**已裁定取 (a)**（用户「**3、可以**」追认）；`LLVM-094t` **已立**（阶段 A/B/E 已落地、C 部分交付、D 待做）〕〔**用户原话落纸（2026-10-16，逐字，渠道 = 经主会话问答）**：「**3、可以**」= 对 (a) 的追认（即「拆 `LLVM-094t`（PIC/动态）先行、`P2` 随后」）；原裁定文字与裁定内容**不改** ✗；整轮 5 条原话见 `milestones.md`「M8 规划区」〕 | **(b) 单册跨模块执行**（先例 = `INFRA-082t` 含 QEMU 侧服务；**范围扩大须在册内显式标注供用户复核**）；**(c) 其它**。⇒ **未裁定前本册按 (a) 口径**（只做 `infra` 面）〔**收尾注记（2026-10-16）**：**已裁定取 (a)** ⇒ 本册只做 `infra` 面、`LLVM-094t` 已立（阶段 A/B/E 已落地）〕 |
| ② | **动态档的运行验证落 `P3`** | **确认落 `P3`**（与用户 2026-10-15「先静态、再动态」+ 不改 `D6` 一致）⇒ 本册只到「**能编出 + 静态可核**」 | 若要求在 `P2` 内跑 ⇒ 须先有 `linux-user`（**与 `D6` 顺序冲突**）⇒ 须用户改序（另立裁定） |
| ③ | **`sigsetjmp`（P1 遗留 ⑧）是否 `P2` 内必要** | **现场判**：若 `libc.so` 构建 / 链接**撞上**则补；否则登记不扩范围（用之即**链接失败**，**非静默**） | 补 = 扩范围（信号帧语义缺口，`mcontext_t` 仍 `[OPEN]`）；不补 = 保持现状 |
| ④ | **`ISS-222`（后端缺口 4 类）+ `ISS-223`（13 源排除）是否 `P2` 内收口** | **否**（`llvm` 模块面）；撞上即 **当场登记 `issues.yaml` + 转出**（`INFRA-079t` 或 LLVM 模块），**不得** silently 跳过 | 若要求 `libc.so` 覆盖全部 13 源 ⇒ 须先收口 `ISS-222`（另一任务），或按 `ISS-223` 建议②**显式声明不支持** |
| ⑤ | **是否需 `compiler-rt` builtins（`INFRA-079t`）** | 沿用 `INFRA-082t` 前置结论 1 口径：**撞缺口才引入**（i128 除法 / FP↔i128 / `bswap` / `*_PARTS`）；未触发须**显式声明** | 若触发 ⇒ 先落 `INFRA-079t`（独立库，`ADR-0027 D5`）再回本册 |
| ⑥ | **`.tao/contracts/contract-elf.md §2.2` 同步（`ISS-206`②）** | **不改**（契约正文，**须用户授权**）⇒ `ISS-206`② 保持 `open`、随 `ISS-206` 跟踪 | 若授权 ⇒ 该同步并入本册（或另立 `spec` 模块任务）；**未授权不得改**。〔**收尾注记（2026-10-16，`LLVM-094t` 阶段 E）**：**已授权并落地** ✗ —— 用户授权原话「**授权，但建议删除 `NUM = 6`**」（渠道 = 经主会话问答）；`.tao/contracts/contract-elf.md §2.2` 已按 `ADR-0019 D10` 同步（15 行终表）+ `spec/Toolchain-01` 旧 `NUM`=6 删除、锁 `sha256` 同变更重算；落点 = **`LLVM-094t` 阶段 E**（**非**本册）⇒ 本册「不改 `.tao/contracts/**`」的范围**不变** ✓〕 |

## 完成区

**测试结果**：
**修改文件**：
**阶段进度**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 完成区（阶段 A1）

**测试结果**：`make build-musl`（静态档）**rc=0**、10/10 检查通过；`.work/evidence/INFRA-085t/run.sh` = **70 PASS / 0 FAIL**（末尾 `A1 ACCEPTANCE: BLOCKED` ⇒ **rc=1**，见「遗留问题」）。
**修改文件**：① `tools/infra/build_musl.py`（新增 `--shared` 档：去掉 `--disable-shared` 的 configure + `SHARED_LDFLAGS` + `parse_elf` 扩到节表/`PT_DYNAMIC` + `check_shared_elf`/`install_ldso`/`check_ldso_symlink` + `config_records` 模式守卫 + `report_checks`；静态档语义不变）② `Makefile`（新 target `build-musl-shared` + help/注释；`build-musl` 语义**不变**）③ `.tao/knowledge/issues.yaml`（+`ISS-239`/`240`/`241`/`242` + `ISS-222` 追加 P2 复确认）④ 本册（本区 + 自审）。**musl 侧改动 = 0**（无需补丁，见「验收结果」④）。证据（`.work/`，不入库）：`.work/evidence/INFRA-085t/{run.sh,probe_checks.py,baseline/**}` + `.work/log/infra/INFRA-085t-*`。
**阶段进度**：**A1 = 接线完成、出口判据 BLOCKED**（生产侧 4 项阻塞）；B/C/D/E 未动。
**验收结果**：① **静态不回归（硬要求）**：`ELF64`/`ELFDATA2MSB`/`ET_EXEC`/无 `PT_INTERP`/无 `DT_NEEDED` 逐条复现（现场 `readelf`）；**控制组** = 同一工具链下「静态配置 vs 共享配置」的 `libc.a`/`crt1.o` **sha256 逐字节相同**（`1c794e6e…`/`2a23630f…`）⇒ 本笔改动**未触碰**静态产物；与 `INFRA-082t` 基线差异**逐条归因**：静态 ELF **仅 `.comment` 152 字节**不同（clang/LLD 修订串 `152cfb15…`→`ad929825…`；机器核「差异偏移 ⊆ `.comment`」+ 尺寸/节表/符号/反汇编全同），`libc.a`/`crt1.o` 差异 = **`ISS-206①` 号表改号（`ABS48` `0→6`）+ `.comment`**（`.o` 级基线未留存 ⇒ 以「linked ELF 逐字节等价」+「控制组逐字节等价」证语义不变，**不默许漂移**）。② **接线**：`SHARED_LDFLAGS` = `-Wl,-shared -Wl,--hash-style=gnu -Wl,-soname,libc.so`；模式守卫实测（静态↔共享各自重 configure，`config.mak` 如实记录，`run.sh S6` 断言收尾态 = 静态）。③ **接线探针**（合成 PIC DSO 走**同一** LDFLAGS + `configure` 生成的 `LDFLAGS_AUTO`）：`readelf -h` = `ELF64 / 大端 / DYN`；`readelf -d` = **有 `SONAME[libc.so]` + `GNU_HASH`**，**无 `HASH`/`RELR`/`RELRSZ`/`VERSYM`/`VERNEED`/`VERDEF`**，无 `.gnu.version*`；符号链接 `ld-musl-dadao.so.1 → libc.so` 指向与解析（sha256）正确 ⇒ **判据 1 的机制逐条实测**。④ **真实 `musl libc.so` 未产出** ⇒ 判据 1 整体 = **BLOCKED**（被生产侧挡住，非「未做」）；**musl 侧补丁 = 0**（现场判：`-shared` 所需之物 musl 侧齐备——`LOBJS` 自动 `-fPIC`、`Scrt1/rcrt1`、`dlstart.lo`、1335/1338 源对象均编过；剩余失败全在编译器/后端）。
**新发现/坑**：① 驱动**静默丢** bare `-shared`（`ISS-239`：`ET_EXEC` + 无 `.dynamic`，仅一条 warning）⇒ 构建侧须传 `-Wl,-shared`；② `-fPIC` 相对查找表发 `.dd.t32`（`ISS-240`：`fmtmsg.c`/`regcomp.c`，TTI `shouldBuildRelLookupTables()` 缺 opt-out）；③ `-shared` 拒 `ABS48` 打**局部标签**于 `.rodata`（`ISS-241`，`recompile with -fPIC` 而对象本就 `-fPIC`）；④ 缺 `src/thread/dadao/syscall_cp.s` ⇒ 共享库必拉的 `pthread_cancel.o` 有 4 个未定义 hidden 符号（`ISS-242`；**静态档潜伏**）；⑤ `ldso/dynlink.c` 的 VLA（`ISS-222 ④`）**加不加 `-fPIC` 都编不过** ⇒ 同挡 C1；⑥ 安装集**无 `llvm-nm`**（改 `llvm-readobj --symbols`；`ADR-0016 D11` 最小集，**非**缺口）。建议沉淀：目标侧「pass 开关（TTI）vs 跳转表编码」两条独立路径、驱动 `-shared` 转发口径、`-fPIC` 常量节（`.rodata` vs `.data.rel.ro`）。
**遗留问题**：**A1 出口判据被 4 项生产侧阻塞** —— `ISS-240`／`ISS-222 ④`／`ISS-241`（**llvm**，需新任务：TTI opt-out、`.data.rel.ro` 常量放置或局部 `ABS48`→`RELATIVE`、VLA/alloca、驱动转发 `-shared`）+ `ISS-242`（**musl 移植面**，但属**语义实现**而非接线 ⇒ 需用户裁定：实现取消语义 asm **或**显式声明不支持）。在役绕行（本笔已落地、可随时回退）：`-Wl,-shared`。**本笔未做**（按指令）：B1/C1/D1/E、`install-host`、L2/L3、commit/push、`components/**`、`spec/`、`contracts/`、`.tao/contracts/**`、不改本册 `**状态**`。

#### `ISS-242` 处置（2026-10-17）——取消语义 asm（用户裁定 (a)）
- **用户裁定**：取 **(a)**（实现取消语义 asm，**非**「显式声明不支持」）；选项标签由主会话下发为「照主流 ISA 模式新增 `src/thread/dadao/syscall_cp.s`」（渠道 = 经主会话问答；原话见主会话问答，本笔只落标签）。
- **测试结果**：`.work/evidence/INFRA-085t/iss242/run.sh` = **17/17 PASS、rc=0**（含注入反例）；新文件单文件汇编 **rc=0**（plain 与 `-O2 -fPIC -ffreestanding -nostdinc -std=c99` 两档）；`ld.lld -r pthread_cancel.lo + syscall_cp.o` **rc=0** ⇒ 4 个 hidden 符号全部有定义（对照组：去掉新对象 ⇒ 同 4 个仍 `Undefined`）。
- **修改文件**：① `.work/source/musl/src/thread/dadao/syscall_cp.s`（**新增**，154 行；组件树收敛为 base+1 且干净）② `components/musl/patches/src/thread/dadao/syscall_cp.s.patch`（**新增**，一文件一补丁）③ `components/musl/series`（+1 行，字典序）④ `components/musl/changelog.md`（+1 条）⑤ 本册（本块 + `第 2 轮 engineer 自审`）。**未动**：`Makefile`/`build_musl.py`/`issues.yaml`（A1 未提交项）、`components/musl/README.md`。
- **验收结果**：`check-patch-tree` **rc=0（151 补丁，原 150）**、`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues.py` 各 **rc=0**、`make check`(L1) **rc=0**（日志 `.work/log/infra/ISS-242/`）。**未跑**（按指令）：`install-host`、`build-musl*`、L2/L3、commit/push。
- **实现口径**：`__cp_begin` 起首 `ld.st rd8, [rb16, 0]` 读 `cancel` 标志 → `br.nz` 命中即 `jump [rb0, __cancel]`（尾跳、不压 RAS）；否则 `rd2rd {rd15}, {rd16}` 置号 + 按 `contract-syscall.md §3` **按类型压实**参数（指针槽位由号恢复，与 `arch/dadao/syscall_arch.h` 的 `__dadao_argmask()` **逐项一致**：12 项/3 组，同一不变量）→ `trap cfx_umon, 0` 紧接 `__cp_end` → `ret rd0, 0`（`rd8` 不动）。**无栈帧**：7 个 data 参数全落 `rd16–rd22`（RISC-V 模板第 7 参取 `0(sp)` 的写法在 DADAO 无对应）。
- **新发现/坑**：① **asm 侧必须自带「号→指针槽位」派发表**——`__syscall_cp_c` 交给它的是 7 个 `long`（指针性只剩号），故 `syscall_cp.s` 的 3 组号表与 `__dadao_argmask()` 是**同一不变量的两处载体**（加号须同改）；本笔已加**机械交叉校验**（`iss242/check_syscall_cp.py` 断言 asm 链 == 头文件表，注入 1 处移动即 FAIL）⇒ 建议后续进 L1 门控。② **A1 证据脚本需同步翻面**：`.work/evidence/INFRA-085t/run.sh` 的 `S4c` 现断言「dadao 源**无**定义」「`syscall_cp.s` **absent**」⇒ 本笔后必然 FAIL，重跑 A1 前须改成「存在且 4 符号有定义」。③ 取消**重定向**依赖信号/ucontext 路径；`arch/dadao/bits/signal.h` 仍 `[OPEN]` ⇒ asm 可达且正确，但取消语义**当前不会真正触发**（`__syscall_cp_c()` 的 `-EINTR` 路径仍会调 `__cancel()`）——**不夸大**。
- **遗留问题**：`ISS-242` 的**符号缺口**已消（A1 的 4 项阻塞变 3 项）；**取消语义的可观测性**随信号路径未打通而悬空（建议随信号帧任务一并收口）；`components/musl/README.md` 未更新（越界，未改）。

## 完成区（2026-10-17，工具链戳记守卫 + clean 共享构建阻塞清单）

**测试结果**：`make build-musl-shared JOBS=8`（clean，安装根工具链）**rc=2**（脚本 rc=1：链接失败，清单见下）；`make build-musl`（静态回验，模式切换）**rc=0**、10/10 检查、**4 s / 0 重编**。证据 `.work/evidence/INFRA-085t/stamp/run.sh` = default **26 PASS/0 FAIL（rc=0）**、`--inject` **22 条期望翻面全红（rc=0，"INJECT OK"）**；日志 `.work/log/infra/INFRA-085t-stamp/`。
**修改文件**：① `tools/infra/build_musl.py`（新增戳记守卫 `STAMP_TOOLS`/`STAMP_REL`/`toolchain_stamp`/`read_stamp`/`write_stamp`/`stamp_decision` + `build_musl()` 接线；静态/共享档共用）② `Makefile`（`build-musl` 注释 4 行，**行为 0 改动**）③ 本册（本块 + `第 3 轮 engineer 自审`）。**未动**：`issues.yaml`／`components/**`（行内 A1 与 `ISS-242` 的既有未提交改动原样保留）、`spec/`、`contracts/`、`.tao/contracts/**`。
**阶段进度**：A1 出口判据仍 **BLOCKED**（阻塞项已从"含假红"收敛为下列 5 类真阻塞）；B/C/D/E 未动。
**验收结果（① 陈旧依赖修复）**：musl `Makefile` 不以编译器二进制为依赖 ⇒ 戳记 = `clang`/`ld.lld` 的「解析路径 + size + mtime + ctime + `--version`」写 `obj/.dadao-toolchain-stamp`（musl `.gitignore` 覆盖 `/obj/` ⇒ `check-source-state` 仍干净）；不一致或缺失 ⇒ 日志 `=> 'make clean' (full rebuild)` + `make clean` + **先写戳记再编**（失败后续编不重复 clean）；一致 ⇒ `=> incremental build`。
- **自动 clean**（手段：`touch .dadao/cross-toolchain/bin/lld`，**只改 mtime/ctime，sha256 前后同为 `39cfcb68…`**）⇒ 判定 `changed`、**1338/1338 `.lo` 重编**、17 s；首建（无戳记）同样 clean + 1338。
- **幂等**：无变化时 **0 编译**（两次复跑均 1 s）。
- **可达 FAIL**：真改戳记 1 字节 ⇒ `changed`；`cp`+md5 还原 ⇒ `unchanged`（md5 `58b41313…` 前后一致）；`--inject` 22 条期望翻面全部转红。
- 不复用 sha256 的理由：`clang` 4.0 GB + `lld` 2.1 GB ⇒ 每次构建 >6 GB I/O（ctime 不可回退，`cp -p` 仍变 ctime；version 行补上游 revision）。

**clean 共享构建最终阻塞清单**（`--error-limit=0` 全量 **22** 条 = **6** ABS48 + **16** undefined；默认 `--error-limit=20` 会截断成 20 条）：

| 类别 | 命中（条数 / 对象） | 代表源（真源行） | 属 `P2`？ |
|---|---|---|---|
| **A** 绝对地址进 PIC 目标 | 6× `ABS48`（`_DYNAMIC`×3、`__dls2`×3），**仅** `obj/ldso/dlstart.lo:.text*` | `arch/dadao/crt_arch.h:69`（`set.rb rb17,_DYNAMIC`）+ `arch/dadao/reloc.h:109`（`GETFUNCSYM`→`set.rd rd8,__dls2`） | **是** —— 阶段 **C1 本体**（`GETFUNCSYM` 基址相关化） |
| **B** compiler-rt builtins | 2× undefined `__muldc3`/`__mulsc3`（`cpow.lo`/`cpowf.lo`） | `src/complex/cpow.c`/`cpowf.c` | **是**（「待确认项⑤」已触发 ⇒ 须先落 `INFRA-079t`，`ADR-0027 D5`） |
| **C** `arch.mak` 排除表**过期** | 13× undefined（来自 11 个 `.lo`：`__crypt_sha512`/`__mo_lookup`/`dgettext`/`dngettext`/`__res_msend`/`__res_msend_rc`/`__getgr_a`/`getgrouplist`/`__nscd_query`/`execl`/`__execvpe`/`sigdelset`/`getcwd`） | `arch/dadao/arch.mak:44-56`（13 源；**实测 11/13 已可编**，仅 2 源 `rotl` 失败 ⇒ 见 D） | **是** —— musl 面刷表即可消 13 条 |
| **D** backend `rotl`（C 的子集，刷表后仍剩） | 2 源 `Cannot select: i64 = rotl …`（`crypt_sha512.c`、`sigdelset.c`） | 同上 2 源 | **是**，但归 **`llvm`** 面（`ISS-222` 类）：不修则 `__crypt_sha512`/`sigdelset` 仍缺 |
| **E** VDSO 口径不一致 | 1× undefined `__vdsosym`（`obj/src/linux/cache.lo`） | `arch/dadao/bits/syscall.h.in:335`（`__NR_riscv_flush_icache` 泄漏）vs `arch/dadao/syscall_arch.h` **无** `VDSO_USEFUL`（`src/internal/vdso.c:8` 定义被编译掉） | **是** —— musl 面小修（去该号 或 补 VDSO） |

- **计数口径**：`dlstart.lo` 实际有 **8** 条 `ABS48`，另 **2** 条在 `.data`（`__dadao_progname`，可写节 ⇒ lld 不报错）⇒ 统计须限定 `.text*`，否则误算 8（`run.sh S5c/S6a` 即按此交叉核对）。
- **每类最小复现**（`TC=.dadao/cross-toolchain/bin`，源在 `.work/evidence/INFRA-085t/stamp/repro/`）：
  - **A**：`$TC/clang --target=dadao-unknown-elf -fPIC -O2 -c …/r1_abs48_dlstart.c -o /tmp/a.o && $TC/ld.lld -shared /tmp/a.o` ⇒ 6 条同文案。
  - **B**：`… -O0 -fPIC -c …/r2_builtins.c -o /tmp/b.o && $TC/ld.lld -shared --no-undefined /tmp/b.o` ⇒ `undefined symbol: __muldc3/__mulsc3`。
  - **C**：`sh .work/evidence/INFRA-085t/stamp/probe_excl_sources.sh` ⇒ `OK ×11 / FAIL ×2`。
  - **D**：`$TC/clang --target=dadao-unknown-elf -O2 -c …/r3_rotl.c` ⇒ `Cannot select: t4: i64 = rotl …`。
  - **E**：`grep -c 'define SYS_riscv_flush_icache' .work/source/musl/obj/include/bits/syscall.h` = **1**、`$TC/llvm-readobj --symbols .work/source/musl/obj/src/internal/vdso.lo | grep -c __vdsosym` = **0**（而 `cache.lo` 引用它）。
- **本笔改动引入的阻塞 = 0**：本笔只改 `build_musl.py`+`Makefile` 注释；clean 重编后的 22 条与 `LLVM-098t` 存档 `P2-A1-rebuild.log`（同 6+16）**逐条一致**。
- **门控（各留自身真实 rc）**：`check-patch-tree`（**151**）、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`check_issues.py`、`make check`(L1) 全 **rc=0**。
**新发现/坑**：① 只要不 clean，`make` 就会把「旧编译器产物」当新产物 ⇒ 换工具链后任何「同文案重现」先怀疑陈旧对象（本笔已机械化，不再靠人记）。② 直接进 musl 树 `make` **必须**带 `PATH=<toolchain>/bin`，否则用 `/usr/bin/clang` 报 `unknown target triple`（假 FAIL；本笔复现命令均带 PATH）。③ lld 默认 `--error-limit=20`：现场 20 条 → 全量 22 条，`-Wl,--error-limit=0` 才能看全。④ 可写节里的 `ABS48` lld 不报错（运行期 `RELATIVE`），计数口径必须限定节。⑤ `arch.mak` 排除表 13 源中 11 源已可编（`bswap`/VLA 缺口已被 `LLVM-096t/097t` 补齐），13 个 undefined 由 11 源贡献（`execle.c`/`execlp.c` 无引用者 ⇒ 不产生未定义）。⑥ `SYS_riscv_flush_icache` 随 riscv 号表泄漏进 dadao，触发 `cache.c` 的 VDSO 路径而 `VDSO_USEFUL` 未定义 —— 这类「号表比 port 能力宽」的缺口不会自曝，只有 `--no-undefined` 才现形。建议沉淀：换工具链 ⇒ 必须使对象失效（`lessons §2`）；`--no-undefined` 是发现「排除表/号表过期」的有效探针。
**遗留问题**：① **清单内 5 类一律只报不修**（按派单）⇒ 主会话按 A/B/C/D/E 排任务（建议：C+E 一批 musl 面、A 一批（C1）、D 归 `llvm`、B 归 `INFRA-079t`）；② 新发现**未登记 issue**（`issues.yaml` 含 A1 未提交改动，按派单不碰）——建议登记 C/E 两条（`arch.mak` 刷表、`__vdsosym`/`SYS_riscv_flush_icache`）；③ `llvm-ar`/`ar` 不在戳记内（只影响归档，不影响代码生成，显式说明）；④ 按派单**未改**本册 `**状态**`、未 commit/push、未跑 `install-host`/L2/L3、未做 `P2` 以外的 B/C/D/E。

## 完成区（2026-10-17，阶段 A(C1 本体) + C + E）

**测试结果**：`make build-musl-shared JOBS=8` **rc=2**（仅链接失败，全量未定义 **4** 条 = B(2)+D(2)，见「验收结果」⑤ —— **本笔目标不是 rc=0**）；`make build-musl JOBS=8` **rc=0**（10/10 检查）。证据 `.work/evidence/INFRA-085t/ace/run.sh`：default **23 PASS / 0 FAIL（rc=0）**；`--inject` **23 条期望翻面全红 + 2 条真注入**（I1 旧 `set.rb` 体重编 ⇒ `ABS48` **3** 条、真对象 0；I2 号表回填 ⇒ 命中 **2**、真头文件 0）**rc=0（"INJECT OK"）**。日志 `.work/log/infra/INFRA-085t-ACE/`（`run-static.log`/`run-shared.log`/`gate-*.log`）。
**修改文件**：① `arch/dadao/crt_arch.h`（SHARED 入口 dynv = `rd2rb {rb17},{rd0}`，保留 rcrt1 形态，新增 `DADAO_DYNV_ASM` + 注释）② `ldso/dlstart.c`（**新补丁**；`#ifndef START` 处定义 `DL_DYNAMIC_FROM_LOAD_BASE`，aux 解析后据 `AT_BASE`/`AT_PHDR&-4096` 走自身 `Ehdr/phdr` 找 `PT_DYNAMIC`）③ `arch/dadao/reloc.h`（`GETFUNCSYM`：`.got` 8 字节槽 + `aip.si`/`ld.o %pcrel_lo`）④ `arch/dadao/arch.mak`（排除表 13→2）⑤ `arch/dadao/bits/syscall.h.in`（删 `sysriscv`/`riscv_flush_icache`/`riscv_hwprobe`）⑥ `components/musl/patches/**`（4 改 + 1 新）+ `series`（17→18）+ `changelog.md`（+1 条）⑦ 本册（本块 + 第 4 轮自审）。**未动**：`Makefile`/`tools/infra/build_musl.py`/`.tao/knowledge/issues.yaml`（行内 A1 未提交项原样保留）、`spec/`、`contracts/`、`.tao/contracts/**`、本册 `**状态**`。
**阶段进度**：**C1 的 ldso 自举部分 + C + E = 完成**；**A1 出口判据仍 BLOCKED**（只差 **B(2)+D(2)**：`libc.so` 仍链不出）；B/D 未做（B 归 `INFRA-079t`、D 归 `llvm`）。
**验收结果**：① **A 类 0 条**：`llvm-readobj -r obj/ldso/dlstart.lo` ⇒ `.rela.text` 仅 1×`REL26 _dlstart_c`、`.rela.text._dlstart_c` 仅 `PCREL_HI(.got)`+`PCREL_LO(.text._dlstart_c)`、`.rela.got` 1×`ABS48 __dls2`、`.rela.data` 2×`ABS48 __dadao_progname`（**可写节，允许**）；全树 **1349** 个 `.lo` 的 `SHF_EXECINSTR` 节 `ABS48` = **0**（现场扫描）。② **语义 oracle（独立：只用 llvm-readobj/objdump，不读 LLVM 内部）**：`_DYNAMIC` st_value `0xED770` **==** `PT_DYNAMIC.p_vaddr` `0xED770`（⇒ 由 base+p_vaddr 推出者即 `&_DYNAMIC`）；`_dlstart`（16 B）= `rb2rb {rb16},{rb1}` / `rd2rb {rb17},{rd0}` / `call` / `swym`（dynv=NULL、无 `set.rb rb17`）；`_dlstart_c` 内 `aip.si rb18,98304` + `ld.o rb18,[rb18,588]` ⇒ 站点 `0xD1BFC`+`0x18000`+`0x24C` = `0xE9E48`，`.rela.dyn` 在**该址**有 `R_DADAO_RELATIVE` addend `0xD2138` **==** `__dls2` st_value，紧随 `call [rb18, rd0, 0]`（槽值即被调者 ⇒ 调到的确是 `__dls2`）。③ **C**：`arch.mak` 13→**2**；11 源**逐条现场编译** OK 11/11、`libc.a` 成员 +11（0 删）、2 源仍 `Cannot select: … rotl`。④ **E**：生成头 `SYS_riscv_flush_icache`/`hwprobe`/`sysriscv` **0** 命中（`SYS_arch_specific_syscall` 保留）；`cache.lo` 无 `__vdsosym`；`libc.a`/`libc.so` 无 `__vdsosym`/`riscv_flush_icache`。⑤ **剩余错误**（`--no-undefined` 全量）：`__muldc3`、`__mulsc3`（B）+ `__crypt_sha512`、`sigdelset`（D）= **4 条，无其它**。⑥ **静态不回归**：`ELF64`/`MSB`/`ET_EXEC`/无 `PT_INTERP`/无 `PT_DYNAMIC`；**同工具链控制组**（`git archive HEAD` = 改动前补丁集建树）⇒ `lib/crt1.o` 与链出静态 ELF **逐字节相同**（`60811d20…`/`2d2c68dd…`）；`libc.a` 成员差 = 恰 11 新增 0 删，同成员差异仅 `cache.o`（E）+ `version.o`（归档树无 `.git` ⇒ `1.2.6` vs `1.2.6-git-1-g…`）；对 `INFRA-085t` 10-15 基线 ELF：同尺寸、**151 B 差异全在 `.comment`**（工具链 revision `152cfb15…`→`e6097030…`）⇒ 工具链换代所致，非本笔。⑦ **补丁/门控**：`check-patch-tree` **rc=0（152 补丁，原 151；musl 18，新增 `ldso/dlstart.c.patch`）**；`check-index-blobs`/`check-source-state`（`musl: HEAD=32d2e17 count=1 clean=True`）/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`python3 tools/infra/check_issues.py`/`make check`(L1) 各 **rc=0**。
**新发现/坑**：① **musl `bits/syscall.h.in` 的生成规则**是 `cp` + `sed -n s/__NR_/SYS_/p`（**只重发含该宏的行**）⇒ 注释里**不得**出现 `__NR_`，否则注释被重发成裸行、生成头语法错（本笔踩过一次假 FAIL，已在文件内注明）。② inline asm 里 `%pcrel_lo` 必须写 `%%pcrel_lo`。③ **ldso 自举不能靠装载期重定位**：`.got` 槽（RELATIVE）要等 `_dlstart_c` 的 RELATIVE 循环，而该循环正需要 dynv ⇒ 循环依赖；`&_DYNAMIC` 在 PIC 下只能由 `AT_BASE`+自身 phdr 推出（合同 §6.2/§6.3 已给 `AT_BASE` 语义，**未改 ABI/契约**）。④ **注入必须防「空注入」**：首版把 `#undef/#define` 追加在 `crt_arch.h` 末尾（asm 已在其前）⇒ injected=0 却"看起来通过"；已改 anchor 替换 + 「anchor 不存在即报错」+ I1 断言 injected>0。⑤ 证据脚本解析 `make -n` 时须跳过 `$(info)` 行（否则命令里混入 `(`）。⑥ 跨工具链 `sha256` 不可比（`ar` 成员 mtime + `.comment` revision）⇒ 静态不回归必须用**同工具链控制组**。
**遗留问题**：① **A1 出口判据仍未达成** —— 只差 B(2)+D(2)，`libc.so` 链不出（B 归 `INFRA-079t`、D 归 `llvm`）。② **静态 PIE（`crt/rcrt1.c`）的 `_DYNAMIC` 仍是链接期绝对地址**（本笔按门控保留原形态，`crt1.o` 逐字节未变）——属**既有边界、非本笔回归**，`-static-pie` 未纳入 P2/P3 范围；建议随 `P3` 或另立任务登记。③ `riscv_flush_icache` 公共符号随号删除而**消失**（显式：全仓无调用者、`cache.c` 的 vDSO 快路径本就无 vDSO 可用）。④ 按派单**未改**本册 `**状态**`、未 commit/push、未跑 `install-host`/L2/L3、未做 B/D。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（无嵌套子代理）；判决 = **接线可交付、出口判据 BLOCKED**（未修项见末行）。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_shared_elf`「ELF type」行注入分支返回 `e_type == ET_DYN` ⇒ **注入时恒 PASS（假绿）** | ✅已修 | 改为统一比较 `exp_type`（注入 = `ET_EXEC`） | `run.sh S5.1`：`--inject` ⇒ **14 FAIL** |
| F2 `run.sh S4c` 用 `llvm-nm`（**安装集无此工具**）⇒ 现场 `No such file or directory`、该项 FAIL | ✅已修 | 改 `llvm-readobj --symbols` + 四名精确匹配 | 重跑 `S4c` 3/3 PASS（4 命中）；工具缺口记入「新发现/坑⑥」 |
| F3 `run.sh` 初版把 `--inject` 的期望 FAIL 经 `check()` 计入**真 FAIL** ⇒ 自检污染 rc | ✅已修 | inject 段仅统计 FAIL 数，不并入 `check()` | 重跑：`70 PASS / 0 FAIL`，注入计数 14 |
| F4 `probe_checks.py` `elfdiff` 曾把「0 差异字节」当期望（与「差异 ⊆ `.comment`」自相矛盾 ⇒ 恒 FAIL） | ✅已修 | 改为单一可判谓词 `covering ⊆ {'.comment'}` + 尺寸比对 | `S1: differing bytes confined to .comment` = `152 bytes in ['.comment']` PASS |
| F5 `probe_checks.py` 残留占位生成器（`section_of`，含死代码/伪 yield） | ✅已修 | 重写为 `sections_covering`，**跳 `SHT_NOBITS`**（否则 `.bss` 假命中） | `elfdiff` 输出仅 `.comment`（无 `.bss`） |
| F6 `parse_elf` 原仅解程序头 ⇒ 判据 1 的动态段/版本段断言**无处落** | ✅已修 | 扩到节表名 + `PT_DYNAMIC` tag/val，异常仍归 `parse_error`（**不抛栈**） | `S4` 的 13 项 + `S5.3` 腐坏副本 ⇒ 7 FAIL 后复原回绿 |
| F7 无模式守卫时，`make build-musl` 会在**共享配置**下静默通过（`libc.a` 字节相同）⇒ 静态档不再证明 `--disable-shared` | ✅已修 | `config_records()`：模式不符即重 configure | `S1`（静态）/`S3`（共享）交替实测；`S6` 断言收尾 = `--disable-shared` |
| F8（判据层，**未修**）A1 出口判据被 4 项生产侧阻塞 ⇒ 无真实 `libc.so` | ⏸延后 | 未改（**不属**本册接线范围；已登记 `ISS-239`/`240`/`241`/`242` + `ISS-222` 追加） | `.work/evidence/INFRA-085t/run.sh` 末段 `A1 ACCEPTANCE: BLOCKED`（rc=1）+ 各阻塞项现场签名 |

**判决与状态对账**：F1–F7 全修（复验证据列见上）；**F8 未修** ⇒ 出口判据未达成 ⇒ **本册 `**状态**` 保持 `待开始`**（并按本笔指令不改该字段）✗，返主会话裁定（建议：先立 `llvm` 模块任务解 `ISS-240`/`ISS-241`/`ISS-222 ④`/`ISS-239`，再回本册重跑 `run.sh` 换得判据 1 绿）+ 用户裁定 `ISS-242`。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### architect 提交留痕（2026-10-17，`INFRA-085t` 刷新笔）
- **档位**：正常提交（**非 WIP** —— 本笔 = 文档刷新 + issue 登记，无实现面、无 engineer 交付）。
- **提交号**：`5104f6f`（分支 `infra-085t-refresh`；落 `master` 走 `merge --ff-only`）。
- **文件集对账**：显式 staging（逐路径，**未**用 `git add -A`）= ① `.tao/tasks/infra/INFRA-085t-动态链接musl-ldso接入.md`（+13/−2）② `.tao/knowledge/milestones.md`（+1/−1）③ `.tao/knowledge/issues.yaml`（+1/−1）⇒ 与「修改文件」声明**逐条一致**：**漏提 0 / 多提 0 / 越界 0**（**未触** `spec/`·`contracts/`·`.tao/contracts/**`·`components/**`·`Makefile`）。
- **门控（各留自身真实 rc）**：`make check`(L1) **rc=0**、`check-patch-tree` **rc=0**、`check-index-blobs` **rc=0**、`check-source-state` **rc=0**、`check-tasks` **rc=0**、`check-knowledge-refs` **rc=0**、`check-knowledge-dir` **rc=0**、`check-no-residue` **rc=0**、`check-component-changelog` **rc=0**、`python3 tools/infra/check_issues.py` **rc=0**（日志 = `.work/log/architect/INFRA-085t-refresh-*.log`）。**未跑** `install-host` / `build-*` / L2 / L3（`ISS-229` 并发禁令；本笔纯文档）。
- **边界**：本笔**未改**本册 `**状态**`（仍 `待开始`）✗、**未 push** ✗；3 处过期口径均**追加注记**（原文保留为历史 ✗）。

#### 第 2 轮 engineer 自审（`ISS-242` 笔，2026-10-17）
自主逐行审查（无嵌套子代理）；判决 = **可交付**（`ISS-242` 的符号缺口消除；取消语义的可观测性按「遗留问题」悬空，未修项见末行）。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 参数**位置**不是原地搬运：syscall 要 `rd16+`/`rb16+` **按类型压实**（`contract-syscall.md §3` 的 read 例），RISC-V 模板的「shift 6 个」在 DADAO 会把 `write` 的 `buf` 留在 `rd17` ⇒ 服务方读到非法地址 | ✅已修 | 加 `nr→mask` 派发（12 号/3 组）+ 四个路由块；`rb` 侧拷贝插在其源被覆盖**之前** | `check_syscall_cp.py` D 四项全 PASS；注入 1 处错移动 ⇒ `D .Lmask2` FAIL（`rd17: w→x`） |
| F2 asm 号表与 `__dadao_argmask()` 是**两处载体** ⇒ 漂移风险（读到垃圾而非显式失败） | ✅已修（靠校验，非门控） | 两表逐项一致 + 头注释写「同一不变量」；`check_syscall_cp.py` C 断言 `asm chain == header table` | `C table non-empty: 12 entries` / `C asm chain == header table: identical`；改一侧即 FAIL |
| F3 分支目标是否都指向预期块（12 个 `br.eq` + 3 个 `jump`） | ✅已核 | 未改；逐条手核「指令地址 + 立即数 = 目标标签」（`0x10+120=0x88=.Lmask2` 等 15 条） | 反汇编逐行 + 注入反例证明 D 类断言可失败 |
| F4 `__cp_end` 若误放在 `ret` 之后 ⇒ 区间含 `ret`，重定向会跳过返回值 | ✅已核 | `__cp_end` 紧接 `trap`（`B trap in [begin, end)`） | `B begin=77 trap=146 end=147` PASS |
| F5 取消分支若用 `call` 会压 RAS / 若有栈帧需在 `__cp_cancel` 恢复 `sp` | ✅已核 | 采**无栈帧 + 尾跳** `jump [rb0, __cancel]`（REL26，可 `-shared`）⇒ `__cancel` 的 `ret` 直接回调用者 | `E tail jump (no RAS push)` PASS；`ld.lld -r` 后仅 `__cancel` 需外部解析（同一链接内由 `pthread_cancel.o` 定义） |
| F6 检查脚本自身两处**假红**（`__cp_begin` 下标差 1；`jump` 用 tab 与空格比较） | ✅已修 | 索引 +1；比较改 `re.fullmatch(r"jump\s+\[rb0, __cancel\]")` | 修前 15/3 FAIL → 修后 18/0 PASS，`run.sh` 17/17 |
| F7 `ld.st` 对齐/宽度：`cancel` 是 `volatile int`，前序字段全 4/8 对齐；`ld.st` 需 4 字节对齐 | ✅已核 | 未改 | `pthread_impl.h:38` 字段序 + `SimRISC-01` 对齐表 |
| F8 **未修**：取消**重定向**需信号/ucontext（`bits/signal.h` 仍 `[OPEN]`）⇒ 取消语义不会被真正触发 | ⏸延后 | 未改（信号帧不属本笔范围） | 完成区「`ISS-242` 处置·遗留问题」如实登记，未夸大为「取消已可用」 |

**判决与状态对账**：F1–F7 已修/已核（证据列见上）；**F8 未修**（能力缺口，非本笔交付缺陷）⇒ 本笔按指令**不改**本册 `**状态**`、不 commit/push，返主会话走 `/complete`。

#### 第 3 轮 engineer 自审（工具链戳记笔，2026-10-17）
自主逐行审查（无嵌套子代理）；判决 = **可交付**（本笔范围 = 戳记守卫 + 清单；清单内缺陷按派单不修）。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `toolchain_stamp` 取 `stdout.splitlines()[0]`，`--version` 成功但无输出时 `IndexError`（非受控崩溃） | ✅已修 | 改 `(… or [""])[0]` | 重跑 evidence default 26/26；`py_compile` rc=0 |
| F2 统计口径错：`dlstart.lo` 有 8 条 `ABS48`，其中 2 条在 `.data`（lld 不报错）⇒ 原断言「错误数 == 对象内全部 ABS48」**恒 FAIL** | ✅已修 | 新增 `text_abs48()`（只数 `.text*` 节），S5c/S6a 用它 | S5c `6 == 6`、S6a `6 == 6` |
| F3 证据脚本 `grep -qS`（`-S` 非法选项）⇒ S6g 假 FAIL | ✅已修 | 改 `grep -q` | S6g `expected=present actual=present` |
| F4 我在 musl 树里直接 `make` 未带 toolchain `PATH` ⇒ 用 `/usr/bin/clang` 报 `unknown target triple`，白跑一轮 | ✅已修（口径） | 复现命令统一 `PATH=<toolchain>/bin`；本笔日志 `full-errors.log` 为带 PATH 的正式结果 | `full-errors.log` 22 条 lld 错误、无 `unknown target triple` |
| F5 戳记在 `make` **之前**写入 ⇒ 构建中途失败不再重复 clean；是否会掩盖失败？ | ❌不改（设计取舍） | 注释写明：obj/ 刚被清空，之后产物必属该工具链；失败属链接阶段，不改变「对象是新的」这一事实 | build1 失败后 build2 = `unchanged`、0 编译（1 s），未重复 17 s clean |
| F6 是否该用 sha256 而非 stat+version？ | ❌不改（有据） | 4.0 GB+2.1 GB ⇒ 每次 >6 GB I/O；ctime 不可回退，`cp -p` 仍变 ctime | 戳记计算实测 **0.11 s** |
| F7 模式切换是否需要 clean？ | ❌不需要（已核） | `.o`（静态、非 PIC）与 `.lo`（共享、`-fPIC`）对象集**不相交**，故不把 mode 纳入戳记 | 共享→静态切换 `make build-musl` rc=0、**0 重编**、10/10 检查 |
| F8 本笔是否引入清单里的阻塞？ | ❌无 | 未改 musl/LLVM 产品源 | clean 重编 22 条与 `LLVM-098t` 存档逐条一致（6+16） |
| F9 清单 5 类要不要修？ | ⏸延后（按派单） | 不修；各类最小复现 + 归类已入完成区 | 证据脚本 S6a–S6g 逐类现场复现 |

**判决与状态对账**：F1–F4 已修、F5–F8 为判定项（附证据）、F9 按派单**只报不修** ⇒ 本笔无未处置缺陷；按派单**不改**本册 `**状态**`、不 commit/push，返主会话走 `/complete`。

#### 第 4 轮 engineer 自审（阶段 A(C1)+C+E 笔，2026-10-17）
自主逐行审查（无嵌套子代理，`subagent_depth=1`）；判决 = **本笔范围可交付、A1 出口仍 BLOCKED（B/D）**。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `crt/rcrt1.c` 也 `#include "../ldso/dlstart.c"` ⇒ 改 SHARED 入口会波及静态 PIE | ✅已核/已隔离 | 门控键在 `#ifndef START`（只有 ldso 自身入口才缺省为 `_dlstart`）；rcrt1 定义 `START` ⇒ 走原 `set.rb` 分支 | `lib/crt1.o` 与控制组**逐字节相同**（`60811d20…`）；`rcrt1.o` 编译 rc=0 |
| F2 首版 dynv 推导只看 `AT_BASE`；`AT_BASE==0`（ldso 当命令跑）时 dynv 留空 ⇒ `dyn[]` 全零、`base` 变垃圾（**静默**） | ✅已修 | 加 `base0 ? AT_BASE : (AT_PHDR & -4096)`（musl 在同函数 `!base` 分支用的同一启发式）+ `if (!eh) return;` | `evidence` A5/A6/A8 复跑仍绿；`dlstart.lo` 重编 rc=0 |
| F3 `"%pcrel_lo(...)"` 未转义 ⇒ `invalid % escape in inline assembly string` | ✅已修 | `%%pcrel_lo` | 编译 rc=0（`obj/ldso/dlstart.lo` 重建） |
| F4 `bits/syscall.h.in` 注释含 `__NR_` ⇒ 生成规则 `sed -n s/__NR_/SYS_/p` 把注释行重发成裸行，生成头语法错 | ✅已修 + 注明规则 | 注释改写为不含该宏，并在文件内写明生成规则 | 重生成 `obj/include/bits/syscall.h` 后 1338 源重编 rc=0；E1/E2 绿 |
| F5 **注入空转**：首版 I1 把 `#undef/#define` 追加在 `crt_arch.h` 尾部（asm 使用点之前已展开）⇒ injected=0 但脚本仍"跑完" | ✅已修（防假绿） | I1 改为 anchor 正则替换 + anchor 缺失即 `RuntimeError` + 断言 injected>0（`set.rb` 必须在注入源里） | `--inject`：I1 `injected=3, real=0`（= 3 片 wyde，与「6 条/2 处」自洽） |
| F6 `make -n lib/libc.so` 输出含 `$(info dadao: excluding …)` ⇒ 拼出的命令 `sh` 语法错 | ✅已修 | 从 `clang --target=` 起截取；无该段时改用已存在的 `lib/libc.so` | oracle DSO link rc=0；A5–A8 绿 |
| F7 `A6` 只断言 `rd2rb {rb17},{rd0}` 存在（弱：旧体里也可能有其他 `rd2rb`） | ✅已修 | 加 `has_abs`（`set.rb rb17` 必须不存在）+ 新增 `A8`（配对值必须是 `dls2` 的 `call [rb18,…]` 目标） | A6 `has_zero=True, has_abs=False`；A8 `call [rb18, rd0, 0]` |
| F8 静态 `libc.a`/`crt1.o`/ELF 与 10-15 基线 sha256 **全不同** ⇒ 初判"回归" | ✅判定修正（非缺陷） | 差异 = `.comment` revision（工具链 `152cfb15…`→`e6097030…`，ELF 同尺寸、151 B 全在 `.comment`）+ 归档成员 mtime；改以**同工具链控制组**作判据 | 控制组（`git archive HEAD`）`crt1.o`/ELF **逐字节相同**；`libc.a` 差异仅 +11 成员 + `cache.o`(E) + `version.o`(归档无 `.git`) |
| F9 `.got` 槽若落在 GNU_RELRO 段，装载期写入是否被 mprotect 挡住？ | ✅已核（无需改） | 写入发生在 `_dlstart_c` 的 RELATIVE 循环，早于任何 RELRO 处理；槽只写一次 | `obj/ldso/dlstart.lo` 的 `.rela.got` + `.rela.dyn` 的 `RELATIVE@0xE9E48` 均在 `DT_RELA` 路径（`_dlstart_c` 自身扫描的正是它） |
| F10 `--gc-sections` 会不会把 `.got` 槽丢掉（槽"无人引用"） | ✅已核 | 槽被 `aip.si` 的 `PCREL_HI` 引用 ⇒ 保留 | oracle DSO `.rela.dyn` 里该址 RELATIVE 在场（A7） |
| F11 `arch.mak` 表名与任务表 `getgr_a` 是否一致 | ✅已核 | 表内为 `src/passwd/getgr_a.c`（文件存在、`__getgr_a` 出处） | C1/C2/C4 逐条现场核 |

**判决与状态对账**：F1/F9/F10/F11 为「已核无需改」、F2–F8 已修 ⇒ **无未处置 finding**；按派单**不改**本册 `**状态**`、不 commit/push，返主会话走 `/complete`。

#### architect 提交留痕（2026-10-17，A1 批 + 台账批）
- **档位**：本册**无 reviewer `Accepted` 判决**（A1 出口判据仍 BLOCKED）⇒ 流程档位应为 **WIP**；**本笔按派单给定文案逐字提交**（无 `WIP:` 前缀）⇒ **如实披露** ✗。
- **提交（本任务分支 `INFRA-085t`，未 push）**：① `452294b` **A1 批**（11 文件 = `Makefile`、`tools/infra/build_musl.py`、`components/musl/{changelog.md,series,patches/**}`×6、本册）② `b7900cb` **台账批**（`issues.yaml`〔`ISS-239/240/241` 登记 + `ISS-244` 关 + `ISS-245` 新登记〕、`milestones.md`、`LLVM-099t` 册）③ `d697c00` **`LLVM-098t` 册完成区补录**（**批外遗留**：开工时已在工作树、非 A1 内容 ⇒ 单独一笔）。
- **文件集对账（`git diff --cached --name-only` × 完成区「修改文件」）**：A1 批 **漏提 0 / 多提 0 / 越界 0**（对应「阶段 A(C1 本体)+C+E」块⑥的 `patches/**` 4 改 + 2 新 + `series` + `changelog`，及前两块声明的 `Makefile`/`build_musl.py`/本册）。**拆分说明**：`issues.yaml` 在 A1 块声明为「+`ISS-239/240/241`」、其后各块声明「未动」，本笔把该文件**整体**并入台账批（同一文件的 6 处改动无法按 hunk 拆分；`ISS-244` 关 / `ISS-245` 亦在其中）。
- **门控（各留自身真实 rc）**：`make check`(L1) **rc=0**；`check-patch-tree` **rc=0（152 补丁）**、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**（日志 `.work/log/architect/INFRA-085t-commit-A1/`）。**未跑**（`ISS-229` 并发禁令；本笔纯提交/文档）：`install-host` / `build-*` / L2 / L3。
- **边界**：**未改**本册 `**状态**`（仍 `待开始`）✗、**未 push** ✗；A1/A(C1)+C+E 完成区内容**未改** ✗。
