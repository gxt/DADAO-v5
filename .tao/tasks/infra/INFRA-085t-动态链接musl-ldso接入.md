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

> **面** 列 = 该行工作归属：`infra` = 本册（musl / 构建）；`llvm` = 生产者侧（若「待确认项 ①」裁定 (a)，则该列项移入 `LLVM-094t`）。〔**收尾注记（2026-10-16）**：裁定**已定 (a)** ⇒ 该列项**已移入** `LLVM-094t`（阶段 A/B/E 已落地、C 部分交付、D 待做）〕

| 阶段 | 名称 | 内容 | 出口判据 |
|---|---|---|---|
| **A** | **共享库与 PIC** | **A1**（`infra`）musl 以 **`-fPIC` / `-shared`** 构建出 **`libc.so`**（`ET_DYN`）+ **`.so` 命名与符号链接** `ld-musl-dadao.so.1 → libc.so`（安装落点按 `ADR-0016`；`build_musl.py` / `Makefile` 接线）；**A2**（`llvm`）生产者侧 `-shared` 能力：`ET_DYN` 输出 + `.dynsym`/`.dynstr`/`.dynamic` + **仅 GNU hash**（`--hash-style=gnu`）+ `DT_SONAME` + `DADAO.def` 改号（`ISS-206`①） | `readelf -h libc.so` = **`ET_DYN` + 大端**；`readelf -d` 有 **`DT_SONAME`**、**`DT_GNU_HASH`**，**无** `DT_HASH`、**无** `DT_RELR`/`DT_RELRSZ`、**无**版本段（`contract-dynlink §5` 裁定 5/6/7）；符号链接指向正确 |
| **B** | **动态可执行** | **B1**（`infra`）构建侧**显式**传 `-dynamic-linker /lib/ld-musl-dadao.so.1`（**不改 lld 默认值**，`ADR-0026 D2`）；**B2**（`llvm`）生产者侧支持 `PT_INTERP` + `DT_NEEDED`（动态可执行链接） | `readelf -l` 的 **`PT_INTERP` 字符串逐字节 = `/lib/ld-musl-dadao.so.1`**；`readelf -d` 含 **`DT_NEEDED`** |
| **C** | **`ldso` 接入** | **C1**（`infra`）`ldso/dlstart.c` / `ldso/dynlink.c` **真接入**（`GETFUNCSYM` **改基址相关**〔P1 遗留 ⑤〕、`CRTJMP` 复核、`arch/dadao/reloc.h` 类别映射复核）；**C2**（`llvm`）**`PT_DYNAMIC` / hash（仅 GNU） / `DT_*` 必备子集** + **eager 绑定**（`DT_BIND_NOW` / `DF_BIND_NOW`，`ADR-0026 D6`） | `libc.so` 内 `_dlstart` / `_dlstart_c` 存在（`nm` / `readelf -s`）；`.dynamic` 必备标签到场（`DT_SYMTAB`/`DT_STRTAB`/`DT_STRSZ`/`DT_GNU_HASH`/`DT_RELA`/`DT_RELASZ`/`DT_PLTGOT`/`DT_BIND_NOW`）；**静态度量**（不跑） |
| **D** | **TLS 动态** | **D1**（`infra`）**`PT_TLS`** + `TP = rb3`（`contract-abi §1.2`）+ `TLS_ABOVE_TP`（`GAP_ABOVE_TP` / `DTP_OFFSET`，逐 arch 定值归 musl 宏）+ `DTPMOD`/`DTPOFF`/`TPOFF` 类型与公式（`ADR-0019 D10`）+ **静态 `__thread`**（P1 遗留 ⑦：crt 侧 auxv 注入之需）；**D2**（`llvm`）TLS 类动态重定位**发射** | 有 TLS 变量时 `readelf -l` 有 **`PT_TLS`**；`readelf -r` 出现的 TLS 类**编号与 `§4.3` 一致**；`__thread` 变量可编译并落 TLS 重定位 |
| **E** | **重定位与越界** | **`ABS48` 两段式**（超 `R_DADAO_REL12` 的 ±2 KiB ⇒ `ABS48` 序列把偏移算进 `rd` + **`ldm.o_rrri_rb`** 落 **`rb`**、随后 `jump rbX, rd0, 0`；**跳转用途必须落 `rb`**）+ **`JUMP_SLOT`** / **`RELATIVE`**；**`COPY` / `TLSDESC` 不发射、遇即报错**；**§10 越界 5 条**〔**⛔ 阻塞（2026-10-16）**：其中 **`ABS48` 两段式 / GOT 可及性**部分**阻塞于 `ISS-230`**、**待用户解法**（见文首「⛔ 阻塞 / 前置」）；`JUMP_SLOT`/`RELATIVE`/`COPY`·`TLSDESC` 部分不受阻〕 | 重定位表含 `ABS48`/`JUMP_SLOT`/`RELATIVE`，且**公式与 `ADR-0019 D10` 逐条一致**（**独立 oracle** 核，见验收 3）；`COPY`/`TLSDESC` 注入例 ⇒ **显式报错**（非静默）；越界例 ⇒ 链接期 / 装载期报错 |

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

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
