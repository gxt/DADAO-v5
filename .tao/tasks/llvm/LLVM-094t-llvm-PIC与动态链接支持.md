# LLVM-094t: LLVM/LLD 的 PIC 与动态链接支持（`P2` 的前置 / 生产者侧）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-091t`（llvm-project = **23.1.3**，`已验证` 2026-10-14；本册基线）；**口径真源** = `.tao/contracts/contract-dynlink.md`（`§1`–`§10`，用户 **2026-10-14 逐条确认**）、`ADR-0019 D10`（类型号 / 公式 / 值类规则）、`ADR-0026 D1–D8`（行为类口径：`PT_INTERP`、**仅 GNU hash**、不做版本段 / `DT_RELR`、eager、不固定 GOT 基址、超 ±2 KiB 两段式、§10 越界 5 条）；`ADR-0003`（Object ABI）、`ADR-0021`（`ld/st` 符号偏移重定位）、`ADR-0018 C6`/`C7 D4`；`ISS-206`（本册**阶段 E** 的执行落点）；`docs/Process-01`（组件补丁组织与构建编排）
**状态**：待验收
**阶段进度**：**A ✅（待验收）** ／ B ⏳ ／ C ⏳ ／ D ⏳ ／ E ⏳

> **`**状态**` 口径**：本任务 = **一个任务书、多阶段验收**（照 `INFRA-082t`/`SPEC-142t`/`INFRA-085t` 先例）⇒ `**状态**` 表**任务级**（**阶段全部验收通过**才置 `已验证`）；**阶段级**进度见上行 `**阶段进度**`。

> **编号留痕（现场取号，2026-10-16）**：`LLVM-094` 经 `.tao/tasks/llvm/**` + `.tao/archive/M1..M7/**` + `git log --all --name-only`（全历史）复核**从未被占用**（现存最大 = `LLVM-093t`；仅 `milestones.md` / `INFRA-085t` 有**前瞻引用**、非占用）⇒ 取 **`LLVM-094t`**（`lessons §3.21`「编号须全仓〔含历史〕唯一」）。

## 立项来源 / 路线位置

- **路线 = `ADR-0025 D6` 的第 2 步（`P2`）的前置**：`P2`（动态链接 / musl `ldso`）= **`INFRA-085t`**（任务书 2026-10-16 落盘）；其**「待确认项 ①」** = 生产者侧（`llvm` 面）跨模块切分 ⇒ **主会话 2026-10-16 裁定取 (a)：拆 `LLVM-094t` 先行**，`INFRA-085t`（消费侧 + 构建）**串行**接后。
  - **裁定理由（原样引录要点）**：**按模块做工**；LLVM 侧 PIC/GOT/PLT/动态重定位本身是**大活** ⇒ 单册过大；拆开后**可独立验收**（满足「每任务可独立验收、可被单个 engineer 完成」）。
  - **依赖方向**：**单向 `llvm → infra`**（本册产出被 `INFRA-085t` **消费**，反向不成立）。
- **`P2` 只交付「能编」**（用户 2026-10-15 裁定「不用改 `D6`，就按原来的顺序进行……**先测静态链接，再测动态链接**」）⇒ 本册判据 = **能编 + 静态可核**，**「跑」统一归 `P3`（`qemu-user`）**。

## 目标（判据 = 「**能编出动态 ELF**」）

- **交付**：LLVM/LLD 的 DADAO 后端**能产出动态 ELF**——
  1. **`ET_DYN` 共享库**（`-fPIC`/`-shared`）：`.dynamic` / `.dynsym` / `.dynstr` / **仅 `.gnu.hash`** / `.rela.dyn` / `.rela.plt` / `.got` / `.got.plt` / `.plt` / `DT_SONAME`；
  2. **带 `PT_INTERP` 的动态可执行**（`-dynamic-linker <path>` ⇒ `PT_INTERP` + `DT_NEEDED`）；
  3. **动态重定位类型与公式**与 `ADR-0019 D10` / `contract-dynlink §4.3` **逐条一致**。
- **判据边界**：**能编出 + 静态可核**（`readelf` / `llvm-readobj` / `nm` + **独立 oracle**）——**不跑**（跑 = `P3`）。
- **不自己定义口径**：类型号 / 公式 / 语义 = `ADR-0019 D10` + `contract-dynlink §4.3`；行为 = `ADR-0026 D1–D8`（**均 `Accepted`**）⇒ **不得**自拟编号 / 公式 / 行为 ✗。

## 执行环境
**执行环境**：本地

## 做（分阶段 A–E；**每阶段各自验收**）

| 阶段 | 名称 | 内容 | 出口判据 |
|---|---|---|---|
| **A** | **CodeGen PIC** | `DADAOTargetMachine.cpp` 现为 `RM.value_or(Reloc::Static)`（现场核 L74）⇒ 支持 **`-fPIC`/`-fPIE`**（`Reloc::PIC_` / `PIE`；`ROPI`/`RWPI` **视需要**，见「待确认项 ①」）；`GlobalAddress` **改走 GOT 间接**（现为绝对地址 materialize：`set.zw`/`or.w` + `R_DADAO_ABS48`，现场核 `DADAOISelDAGToDAG.cpp`）；GOT 槽地址 = **`rb0`（PC）相对 + 链接期常量偏移**（`imms12`）⇒ **不固定 GOT 基址、不安排专用寄存器**（`rbgp` 不承载 GOT，`ADR-0026 D5` / `ADR-0018 C6`）；超 **±2 KiB** 时按 `ADR-0026 D5` 两段式（见阶段 C） | `-fPIC` 目标文件**不含**链接期绝对地址 materialize（`llvm-readobj -r` 的 `R_DADAO_ABS48` 仅出现在**数据 / GOT 槽**语义处，不出现在指令域「绝对地址构造」用途）；GOT 槽经 `rb0` 相对访存（**静态可核**：反汇编可见 `ld.o [rb0, <gotslot-offset>]` 形态、且偏移是链接期常量、无 GP 约定） |
| **B** | **LLD 动态产出** | `lld/ELF/Arch/DADAO.cpp`（现**只有静态** `relocate` + `getRelExpr`，现场核）扩展为可产出 **`ET_DYN`**：`.dynamic`（`SHT_DYNAMIC`）/ `.dynsym` / `.dynstr` / **仅 `.gnu.hash`**（`--hash-style=gnu`，**无** `.hash`）/ `.rela.dyn` / `.rela.plt` / `.got` / `.got.plt` / `.plt` / `DT_SONAME`；`-shared` / `-dynamic-linker` 走通；`Target.{cpp,h}` 注册面同步 | `readelf -h` = **`ET_DYN`**；`readelf -d` 有 **`DT_SONAME`** + **`DT_GNU_HASH`**，**无** `DT_HASH`、**无** `DT_RELR`/`DT_RELRSZ`、**无**版本段（`DT_VERSYM`/`DT_VERNEED`/`DT_VERDEF`）（`contract-dynlink §5` 裁定 5/6/7） |
| **C** | **重定位类型（新编号）** | 按 **`ADR-0019 D10`** 实现（**新编号**）：`ABS48`=**6**（**两种编码**：指令 3×`immu16` 分片 / 数据 8 字节字段）、`JUMP_SLOT`=7、`RELATIVE`=8、`COPY`=9、`TLS_DTPMOD`=10、`TLS_DTPREL`=11、`TLS_TPREL`=12、`TLSDESC`=13；**`COPY` / `TLSDESC` 首版不发射、遇即报错**（`ADR-0026 D7②`，**非静默**）；超 **±2 KiB** ⇒ `ABS48` 序列把偏移算进 `rd` + **`ldm.o_rrri_rb`** 落 **`rb`**、随后 `jump rbX, rd0, 0`（**跳转用途必须落 `rb`**） | 重定位表含 `ABS48`(6) / `JUMP_SLOT`(7) / `RELATIVE`(8)，**公式与 `ADR-0019 D10` 逐条一致**（**独立 oracle** 核，见验收 3）；`COPY`/`TLSDESC` 注入例 ⇒ **显式报错**；**不做** relaxation（`ADR-0019 D7`） |
| **D** | **与契约逐条对齐** | `PT_INTERP` 值**仅由 `-dynamic-linker` 决定**（本册只保证**可指定**、**不改 lld 默认值**；值 `…/ld-musl-dadao.so.1` 由 `INFRA-085t` 显式传，`ADR-0026 D2`）；**eager 绑定**（`DT_BIND_NOW` / `DF_BIND_NOW` + full `RELRO` 可行，`ADR-0026 D6`）；`DT_PLTGOT` **必须提供**（musl `ldso` 读 `dso->got`）；**不做**版本段、**不做** `DT_RELR`（`ADR-0026 D4`）；**§10 越界 5 条**（48 位约束 / 未支持类型显式报错 / 偏移与 TP 越界 / lld 侧 ±2 KiB 链接期报错 / 分层不互放宽） | `readelf -l`：动态可执行有 **`PT_INTERP`**（字符串 = 传入的 `-dynamic-linker` 参数）；`readelf -d` 含 **`DT_NEEDED`** / **`DT_BIND_NOW`** / **`DT_PLTGOT`**；**未传** `-dynamic-linker` 时 **不**凭空产生 `PT_INTERP`（**不改 lld 默认**）；`COPY`/`TLSDESC`/版本段/`DT_RELR` 相关注入例 ⇒ 显式报错 |
| **E** | **`ISS-206` 编号同步** | 把 `llvm` 侧**旧编号**同步为 `ADR-0019 D10` **新编号**：`llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def`（现 `ABS48=0`…`NUM=6`，现场核）+ `llvm/include/llvm/BinaryFormat/ELF.h` 枚举 + `lld/ELF/Arch/DADAO.cpp` **头注释**（其现写 `R_DADAO_ABS48 (0)`，现场核 —— 即 `ISS-206` 的**现场载体**）；并排查 **既有 ELF 产物 / 测试向量**（`tests/vectors/**`、`tools/testcases/*`）里写死的类型号字段（`ISS-206③`） | `DADAO.def` = `NONE=0` / `ABS48=6` / 动态 `7`–`13` / `NUM=14`；`lld/ELF/Arch/DADAO.cpp` 头注释与实现**同号**；`ELF.h` 枚举同步；**产物 / 向量排查留证**（逐条 `grep` + 结论，**不得**据先前「只见注释」的现场写成「已确认无命中」——须**独立复核并留证**） |

## 依据（口径真源；**引用，不复制正文**）

- **契约**：`.tao/contracts/contract-dynlink.md` —— `§1`（范围 / 角色 / 术语）、`§2`（PIC/PIE 与 `rb0`/`rbgp`/`rbtp` 口径）、`§3`（GOT/PLT、eager、`DT_PLTGOT`、两段式）、`§4.3`–`§4.4`（**类型总表与编号**）、`§5`（动态段 / `dynsym` / **仅 GNU hash** / 版本段·`DT_RELR` 都不做）、`§6.1`（`PT_INTERP` 与 `-dynamic-linker`）、`§8`（**独立 oracle 口径与禁止项**）、`§9`（裁定清单）、`§10`（失败与越界 5 条）。
- **决策**：`ADR-0019 D10`（类型号 / 公式 / 语义 / 值类规则）、`ADR-0026 D1–D8`（行为类口径）、`ADR-0025 D6`（路线，**不改**）、`ADR-0018 C6`/`C7 D4`、`ADR-0003`、`ADR-0021`。
- **参考仓库（`DADAO-0628`）**：**内容溯源，非执行必需** —— 只读 `.cache/refs/**`、**不写回、不复制代码**；`SPEC-144t` 结论 = 0628 **无 `pk`**、其寄存器约定（`rd16`/`tp=rb4`）与 `interp`/`gem5` 四方差分**不借鉴** ⇒ **仅工程流程 / 教训可借鉴**（`milestones.md`「`DADAO-0628` 对照（结论层）」）。

## 已知事实（供执行，**勿重复查证**；源已现场标注）

1. `lld/ELF/Arch/DADAO.cpp` **只有静态** `relocate` + `getRelExpr`；其**头注释**写 `R_DADAO_ABS48 (0)`（**旧编号**）⇒ **`ISS-206` 现场载体**。
2. `llvm/lib/Target/DADAO/DADAOTargetMachine.cpp:74` = `RM.value_or(Reloc::Static)` ⇒ **默认静态**、现**无 PIC**；`DADAOISelDAGToDAG` 对 `GlobalAddress` 走**绝对地址 materialize**（`set.zw`/`or.w` + `R_DADAO_ABS48`）、**非 GOT 间接**。
3. `llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def` = `ABS48=0` … `ABS12=5`、`NUM=6` ⇒ 与 `ADR-0019 D10` **不一致**（`ISS-206①` **必改**）；`lld/ELF/Arch/DADAO.cpp` 头注释的 `ABS48 (0)` 同源须同步。
4. 补丁集形态 = `components/llvm-project/patches/**`（树形 + 一文件一补丁 + `series`；`check-patch-tree` 机械校验）；**改 MC/InstrInfo（`.td`）后必须 `make install-host`**（`AGENTS.md`；`ISS-210`）。
5. 端序 = **大端**（`ADR-0003 D1`：`EI_DATA = ELFDATA2MSB`）⇒ BE 敏感用例须自成一面。
6. 验证面现状：**无 `qemu-user`**（`P3`）⇒ 本册**不可**有任何「运行通过」叙述；**L2/L3 不得并发**（`ISS-229`：共享安装根竞争 ⇒ 假 FAIL）；`JOBS=8`、**禁全核** `-j$(nproc)`。
7. `contract-elf.md §2.2` **仍是旧号**（`ABS48=0`/`NUM=6`）= `ISS-206②` ⇒ **契约正文改动须用户授权**（见「待确认项 ③」；不在本册默认范围）。

## 接口规范

- **输入**：`ADR-0019 D10` / `ADR-0026 D1–D8` / `ADR-0025`（`D2`/`D3`/`D6`/`D7`）/ `ADR-0003` / `ADR-0021`；`.tao/contracts/contract-dynlink.md`（**只读**）；`components/llvm-project/patches/**`（现状，**只读**）；`.work/source/llvm-project/**`（**只读**：源码检出，现状取证）；`.dadao/cross-toolchain/**`（工具链 + sysroot，**只读**）。
- **输出**：
  1. **生产者侧补丁**：`components/llvm-project/patches/llvm/**`（CodeGen PIC / GOT）+ `components/llvm-project/patches/lld/ELF/**`（`Arch/DADAO.cpp`、`Target.{cpp,h}` 等动态产出）+ `components/llvm-project/patches/llvm/include/llvm/BinaryFormat/**`（`DADAO.def` / `ELF.h` 改号）——**树形补丁 + 一文件一补丁**（`docs/Process-01`；`check-patch-tree` 机械校验）。
  2. **构建接线**：`Makefile` 既有 `build-mc` / `build-lld` / `install-host` 路径（**不新增**构建体系；`JOBS=8`）。
  3. **验证 / 证据**：`.work/evidence/<任务ID>/run.sh`（**一键证据**，含「注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿」）+ 原始输出落 `.work/log/llvm/**`；本任务书完成区 + `milestones.md` 流水行。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`（上游只读册，须用户事先授权）、`contracts/`（机器数据）、`.tao/contracts/**`（正文，须授权）；**组件源一律 git 基线**（改 llvm-project 只经 `patches/**`，**不得**直接改 `.work/source/**`）；**禁** `git add -A`、**禁** `git checkout/restore/stash`；**计数不写死**（现场派生）；**期望值独立**（`contract-dynlink §8`：不从 LLVM / LLD / QEMU / 本仓工具反推）。

## 依赖与先后

- **已满足**：`LLVM-091t`（llvm-project **23.1.3**，`已验证`）、`ADR-0019 D10` / `ADR-0026`（均 `Accepted`）、`contract-dynlink.md`（用户 2026-10-14 逐条确认）。
- **后继（串行）**：**`INFRA-085t`（`P2` 消费侧 + 构建）接本册之后**（依赖单向 `llvm → infra`）；`INFRA-085t` 的「待确认项 ①」已由主会话 2026-10-16 裁定 (a) 闭合。
- **串行约束**：与任何同改 `components/llvm-project/**`、`Makefile`、`tools/**`、`manifests/**` 的任务**一律串行**（不得并行）；**同一工作树同一时间只允许一个写工作树**的子代理。

## 验收标准

1. **`ET_DYN` 产出**：`-fPIC` / `-shared` 编出 `ET_DYN`；`readelf -d` 有 **`DT_SONAME`** + **`DT_GNU_HASH`**；**无** `DT_HASH`、**无** `DT_RELR`/`DT_RELRSZ`、**无**版本段（`DT_VERSYM`/`DT_VERNEED`/`DT_VERDEF`）（`contract-dynlink §5` 裁定 5/6/7）。
2. **动态可执行**：带 **`PT_INTERP`**（字符串 = 传入的 `-dynamic-linker` 参数）+ **`DT_NEEDED`**；**未传** `-dynamic-linker` 时**不**凭空产生 `PT_INTERP`（**不改 lld 默认值**，`ADR-0026 D2`）。
3. **重定位（契约逐条）**：含 `R_DADAO_ABS48`(**6**) / `R_DADAO_JUMP_SLOT`(7) / `R_DADAO_RELATIVE`(8)，**公式与 `ADR-0019 D10` 逐条一致**（`ABS48`/`JUMP_SLOT` = `S+A` 无符号 48 位；`RELATIVE` = `B+A` 无符号 48 位；偏移类 = 补码）。**独立 oracle**：期望值用 `readelf`/`llvm-readobj` 的**独立解析**（**非** v5 工具链输出）+ 依公式**独立计算**核对；**不从 v5 自身实现（LLVM/LLD/QEMU/本仓工具）反推**（`contract-dynlink §8`）。
4. **端序 = 大端**：`EI_DATA = ELFDATA2MSB`；至少 **1 例 BE 敏感**证据（多字节字段字节序，如 `ABS48` 数据槽 `00 00 A5 A4 A3 A2 A1 A0` 形态）。
5. **门控**（各留**自身**真实 rc，**禁** `cmd | tee` 吞码）：`make check`（**L1**）、**`make check-modules`（L2，任务收尾；串行、禁与 L3 并发——`ISS-229`）**、`make check-patch-tree`、`make check-index-blobs`、`make check-instrinfo`（**若改 `.td` ⇒ 先 `make install-host`**）、`make check-source-state`、`check-knowledge-refs`（`make check-knowledge-refs`）、`check-knowledge-dir`、`check-no-residue`、`make check-tasks`、`python3 tools/infra/check_issues.py`、`check-component-changelog` 各 **rc=0**；`make check-full`（L3）在里程碑 / `/complete` 跑。
6. **可达 FAIL 证据**：`.work/evidence/<任务ID>/run.sh` 可跑通，**每条断言有可达 FAIL 路径**（注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿；还原用 `cp` + md5 对账，**禁** `git checkout/restore/stash`）；**禁恒真断言**、**计数不写死**。

## 不做项（显式）

1. **`qemu-user` / `linux-user`**（`P3` ✗）与**动态链接的「运行」验证**（`P2`/`P3` ✗）——本册只保证**能编**（`INFRA-085t` 承接消费 + 构建，运行归 `P3`）。
2. **改 `spec/`**（上游只读册；须用户事先授权）✗、**改 `contracts/` 机器数据** ✗；**`.tao/contracts/**` 正文**默认不改（含 `contract-elf.md §2.2` 同步 = `ISS-206②`，须授权——见「待确认项 ③」）✗。
3. **relaxation**（`ADR-0019 D7` ✗）；**新增 ISA 指令**（`ADR-0026 D5` ✗）；**自写 `ld.so`**（`ADR-0025 D3` ✗）。
4. **`ISS-222`（后端缺口 4 类）/ `ISS-223`（13 源排除）** 的收口 ✗（撞上即**当场登记 `issues.yaml` + 转出**，**不得** silently 跳过）。
5. **`compiler-rt` builtins**（`INFRA-079t`）✗（**撞缺口才引入**，沿用既有口径）。

## 待确认项

| # | 项 | 我的默认（**待用户确认**） | 备选 / 影响 |
|---|---|---|---|
| ① | **CodeGen PIC 的模型选择**：`Reloc::PIC_` vs `PIE` vs `ROPI`/`RWPI` 是否符合契约「**不固定 GOT 基址、PC 相对**」（`ADR-0026 D5`） | **现场判 + 依据**：默认取 **`PIC_`（`-fPIC`）/ `PIE`（`-fPIE`）**；`ROPI`/`RWPI` **仅在契约确需时**引入（契约**未**要求只读 / 只写段分离基线）+ 论证 `ROPI`/`RWPI` 与 PC 相对 GOT 访问**不冲突且不引入专用寄存器** | **`ROPI`/`RWPI` 会改变数据寻址模型**（可能触动 `contract-abi` / 既有 CodeGen 约定）⇒ 若采用须**先请裁定**，并评估对既有 lit / `check-interface` 的影响；**未确认前不引入** ✗ |
| ② | **是否需新增 `.td` / MC 侧改动**（视实现） | **现场判**：若 PIC 仅需 `DADAOTargetMachine.cpp` + `DADAOISelDAGToDAG.cpp`（GOT 间接 + 重定位类型选择），则**不动 `.td`**；若 GOT 间接 / PLT 序列**必须**新增伪指令或 `ComplexPattern` ⇒ 才动 `.td`，并**必须 `make install-host`**（`ISS-210`） | 动 `.td` ⇒ 门控面扩大（`check-instrinfo`）+ 重建成本上升；**改动前须申报**重建耗时 |
| ③ | **`ISS-206` 是否在本册一并收口** | **默认 = 一并收口**（阶段 E 覆盖 `ISS-206①③`：`DADAO.def` 改号 + 产物/向量排查）；**②（`contract-elf.md §2.2` 契约正文同步）须用户授权**——若授权 ⇒ 一并收口（`ISS-206` 转 `closed`，`resolved_by: LLVM-094t`）；**未授权 ⇒ `ISS-206` 保持 `open`（部分收口）**、完成区**显式声明**，**不得**写成已关 | 若要**分开**（②另立 `spec` 模块任务）⇒ 说明后本册只做 ①③；**未授权不得改** ✗ |

## 完成区

**测试结果**（阶段 A）：`.work/evidence/<任务ID>/run-a.sh` **84 PASS / 0 FAIL（rc=0）**；`--inject` **10/10（rc=0）**；`make check`（**L1**）**rc=0**；`make check-modules`（**L2**，单独跑）**rc=0**（90 s；`check-lit`/`check-interface`/`test-codegen`/`test-elf`/`test-semihost`/`check-qemu-smoke`/`picolibc-tests` 均 PASS）；`check-patch-tree`/`check-index-blobs`/`check-instrinfo`/`check-source-state`/`check-no-residue`/`check-tasks`/`check_issues.py` 各 **rc=0**。全文 `.work/log/llvm/LLVM-094t-*.log`；证据脚本 + 独立 ELF 解析器 `.work/evidence/<任务ID>/{run-a.sh,elfinfo.py}`（解析用 `struct` 自解 ELF64-BE，**不经** LLVM 读取器）。

**修改文件**：① **组件补丁树 11 份**（`components/llvm-project/patches/**`，**一文件一补丁**、`series` 仍 71）＝ `clang/lib/Driver/ToolChains/DADAO.h`、`llvm/lib/Target/DADAO/{DADAO.h,DADAOTargetMachine.cpp,DADAOISelDAGToDAG.cpp,DADAOISelLowering.{cpp,h},DADAOInstrInfo.cpp,DADAOMCInstLower.cpp,DADAOAsmPrinter.{cpp,h},MCTargetDesc/DADAOMCInstPrinter.cpp}`（源树 `.work/source/llvm-project` HEAD `93af153b` = base+1 且干净，`check-patch-tree`/`--source-state` rc=0）；② `tools/llvm/llvm-isa-backend-matrix.{md,tsv}` 重生成（`gen_isa_coverage.py`；仅行号引用与 `isel-cpp` 证据计数 15→18，**判据 yes/no 未变、86 条不变**）；③ `components/llvm-project/changelog.md` 追加 M8 一条（changelog 维护规则要求）；④ `.work/evidence/<任务ID>/{run-a.sh,elfinfo.py,baseline-pre/,baseline-pre-raw.md5,baseline-pre-nocomment.md5,toolchain-pre.md5}` 与 `.work/log/llvm/LLVM-094t-*.log`（**披露**：`.work/**` 为 `.gitignore` ⇒ 证据**不入 git**、留在工作区，沿用既有 `.work/evidence/` 先例）；⑤ 本任务书（完成区 + 自审）。

**阶段进度**：**A ✅（待验收）** ／ B ⏳ ／ C ⏳ ／ D ⏳ ／ E ⏳

**验收结果**（阶段 A 出口，真实输出摘录）：**`-fPIC`/`-fPIE` 目标文件**：`.rela.text` **零**条 `R_DADAO_ABS48`（`P1[pic]/[pie].no-ABS48-in-.text` expect=0 actual=0）、仅 `R_DADAO_REL12`→`.got`；`.got` **4 槽 × 8 B**，槽内容 **4** 条 `R_DADAO_ABS48` 数据重定位（`P2.got-slot-ABS48-relocs` expect=4 actual=4）；指令域 **6** 处 `ld.o rb, [rb0, <slot>]` + **6** 条 `R_DADAO_REL12 .got`（P3，`-dr` 可见）⇒ **偏移为链接期常量**；**无 `rb2`/GP 操作数**（P4 expect=0 actual=0）⇒ 满足「不固定 GOT 基址、不安排专用寄存器」。**生效性**：`-fPIC`/`-fPIE` 与 static 产物 md5 **不同**（A2）⇒ 不再静默压平。**`-S`**：含 `.got` 段 + `[rb0, .Lgot.N]`，`llvm-mc` **可再汇编**（A5 rc=0）；`llc -relocation-model=pic` 同判据。**跳表**：含 2 个 switch 的模块两块表各得**独立**槽 `.LJTI0_0`(+0)/`.LJTI1_0`(+0x10)（A6b）。**大端**：`dataenc=2`（`ELFDATA2MSB`）+ `.data` 常量 `0x01020304` 字节序 = `01 02 03 04`（A8，大端敏感）。**不回归**：静态路径 6 例（`t`/`sw` × O0/O1/O2）剥 `.comment` 后 md5 与**改动前**逐字节相同（A7；`NOTE` 记录原 md5 差异 = 内嵌组件 commit `152cfb15`→`93af153b`）；`-fno-pic` 仍无 `.got`、`.text` 仍 3 片 `ABS48`。**重建/安装**：`build-mc` 单写者 **200 s PASS**（此前 241/210 s 亦 PASS）、`install-host` **PASS**（312 s；前次 129 s）；构建树与安装根 **7 个二进制 md5 全同**（`clang`/`llc`/`llvm-mc`/`llvm-objdump`/`llvm-readobj`/`llvm-objcopy`/`ld.lld`），`clang --version` 报组件 HEAD `93af153b` ⇒ 无 `ISS-210` 假绿。**编号静态核（记录，本次不动）**：`DADAO.def` 现 `R_DADAO_ABS48=0`、`R_DADAO_REL12=4`；`ADR-0019 D10` 期望 `ABS48=6` ⇒ **未同步 = 阶段 E（`ISS-206`）**（A9 NOTE）。

**新发现/坑**：① **「PIC 不支持」的真相 = 驱动静默压平**：`clang/lib/Driver/ToolChains/DADAO.h` 的 `isPICDefaultForced()` 原为 `true` ⇒ `-fPIC` 被**静默**忽略（cc1 实收 `-mrelocation-model static`），产出非 PIC 代码且 **exit 0、无任何报错** —— **不是**「报错不支持」；修前 `-fPIC` 与 static 产物**逐字节相同**。② LLVM **23 无 `Reloc::PIE`**（`Reloc::Model = {Static, PIC_, DynamicNoPIC, ROPI, RWPI, ROPI_RWPI}`）：`-fPIC`/`-fPIE` **均落 `Reloc::PIC_`**（PIE-ness 走 clang `PIELevel`）⇒ 任务书「`Reloc::PIC_`/`PIE`」写法应按此校正；`ROPI`/`RWPI`/`DynamicNoPIC` 在本后端**显式报错**（不静默降 static）。③ **通用 PIC 会改跳表编码**：`TargetLowering::getJumpTableEncoding()` 在 `isPositionIndependent()` 时返 `EK_LabelDifference32`（4 B label difference）⇒ DADAO 无 32 位数据重定位，汇编期硬错 9 条（「cannot carry a 48-bit DADAO address」）⇒ 覆写恒返 `EK_BlockAddress`（8 B 绝对表项 = 契约 §4.3「数据」形态）。④ **MC 文本路径两处缺陷**（仅 `-S` 暴露）：`DADAOMCInstPrinter` 的 `ld./st.` 无条件 `getImm()`（遇符号表达式操作数即断言）；`MCContext::getELFSection(..., EntrySize=8)` 触发 `MCAsmInfoELF::printSwitchToSection` 断言（非 `SHF_MERGE` 不得带 entsize）⇒ 去 `EntrySize` 并改用 `emitValueToAlignment(Align(8))`。⑤ **设计取舍（跨阶段披露）**：契约**禁新增重定位类型**（`ADR-0026 D5`/`contract-dynlink §3`）且 ISA 无「`rb0`+符号偏移 → 寄存器」形态 ⇒ **GOT 槽由编译器自出**（`.got`：每引用符号/跳表一 8 B `R_DADAO_ABS48` 数据槽），指令域用**既有** `R_DADAO_REL12`（`rb0` PC 相对）寻址 ⇒ **阶段 B/C** 的 lld 须**保留/合并输入 `.got`**、把槽 ABS48 转为动态重定位（`REL_GOT`/`RELATIVE`）、并按 `D5` 保证槽「就近 ±2 KiB」。⑥ **并发坑（本次自犯，已修复留证）**：`make check-modules` 经 `check-picolibc-tests → build-picolibc → install-host → build-mc` **会自行重建**；我同时手动 `make build-mc` ⇒ **两个 ninja 写同一构建树**，`bin/clang-23` 被写坏（4.29 GB、`--version` segfault）并被 `install-host` 装入安装根 ⇒ `ISS-229` 的同类风险**不止安装根、构建树同样**（「手动重建」须与 L2 串行）；已单写者重建 + 重装 + 复验（`--version` rc=0、md5 7/7 同）并于终态重跑 L1/L2。⑦ 既有派生投影 `llvm-isa-backend-matrix` 会因后端源码**行号/证据计数**变化而 drift ⇒ 改后端须连带重生成（本次由 L1 现场暴露并修复）。

**遗留问题**：① **阶段 B–E 未做**（LLD `ET_DYN`/`.dynamic`/GNU hash/`GOT`·`PLT`/动态重定位；`ADR-0019 D10` 新编号；契约逐条；`ISS-206`）——本册其余阶段承接。② **PIC 下外部函数调用仍为直接 `REL26`**（PC 相对）：未走 PLT（`JUMP_SLOT`/`.plt` = 阶段 B/C）⇒ `.so` 场景该调用点须链接器改写。③ **PIC 跳表内容仍为绝对地址**（8 B 数据 `ABS48`，契约 §4.3 允许）：共享对象需装载期 `RELATIVE` 修正（阶段 B/C）。④ **未新增 lit / PIC 回归用例**（本阶段判据由 `run-a.sh` 覆盖）；`tests/llvm/codegen/m6/README.md` 现仍写「`REL12`/`ABS12` 仅汇编层、CodeGen 未发射」，PIC 后该口径已过时（建议后续并入 `check-lit`/`expected-elf`）。⑤ `milestones.md` 流水行交 `/complete` 收尾（本册按规则**未**写 `milestones.md`；组件 changelog 已按维护规则在同一变更内追加）。⑥ **未撞** `ISS-222`（无 inline asm / `dynamic_stackalloc`）/ `ISS-223`。

## 审阅记录

#### 第 1 轮 engineer 自审

**逐行审查范围**（自主）：11 份补丁逐文件复核 —— ISel（`Select` 的 `GlobalAddress` PIC 分支、`isPointerBankValue`、`BR_JT` 跳表基址）、`MCInstLower` 目标标志分派、`AsmPrinter` 槽生成/`.got` 发射/跨模块状态、`DADAOTargetMachine` reloc 模型选取、驱动 `isPICDefaultForced`、`InstPrinter` 表达式打印、`getJumpTableEncoding` 覆写；并核对「判据独立」（自写 ELF64-BE 解析器，**不走 LLVM 读取器**）、每条断言的**可达 FAIL 路径**、期望值来源（`DADAO.def` + ELF gABI，**不**从本实现反推）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 跳表 GOT 槽按 **index** 键 —— `MachineJumpTableInfo` index **逐函数归零** ⇒ 同模块两 switch 时**第二个函数静默拿到第一张表地址** | ✅已修 | `GOTJumpTableSlots` 改按 `GetJTISymbol(index)` 的 `MCSymbol *` 键 | 新增 `src/two.c`（两 switch）+ A6b；实测 `.rela.got` = `.LJTI0_0`(+0) 与 `.LJTI1_0`(+0x10) **两槽**（修前同槽）；`A6b.distinct-jt-slots >=2` PASS |
| F2 槽名计数取 `GOTSlotOrder.size()`，`emitEndOfAsmFile` 清表后**归零** ⇒ 同 `MCContext` 多模块（LTO）**重名 ⇒ 重定义** | ✅已修 | 独立计数 `GOTSlotNextId`（**不随模块重置**；只清槽表不清计数） | 代码级审查 + 全量重建；`run-a.sh` P1–P4/A5–A8 全绿；`-S` 标签 `.Lgot.0..3` 唯一。**披露**：多模块/LTO 场景**未现场构造**（按代码路径判定，非实测） |
| F3 `-fPIC -S` 崩：`DADAOMCInstPrinter` 的 `ld./st.` 无条件 `getImm()`（操作数为符号表达式） | ✅已修 | 打印改 `isImm()/isExpr()` 分支（与 `br.*`/`jump`/`call` 既有写法一致） | `A5.clang-fPIC-S rc=0`；`asm-has-gotslot-operand`、`reassemble-S-output rc=0`、`P3[asm-rt]` 全绿 |
| F4 `getELFSection(".got",…,EntrySize=8)` 触发 `MCAsmInfoELF::printSwitchToSection` 断言（非 `SHF_MERGE` 不得带 entsize） | ✅已修 | 去 `EntrySize`；改 `emitValueToAlignment(Align(8))` 显式对齐 | 同上 A5 三项；`P2[asm-rt].got-slots`；对象侧 `.got` 无 `sh_entsize` |
| F5 `sw.c -fPIC` 汇编期 9 错（4 B 数据域承载 48 位地址）—— 通用 PIC 换 `EK_LabelDifference32` | ✅已修 | 覆写 `getJumpTableEncoding()` 恒返 `EK_BlockAddress`（保持 8 B 绝对表项 = 数据形态） | `A6.sw-pic.compile rc=0`；`P1[sw-pic].no-ABS48-in-.text=0` |
| F6 证据脚本缺陷：A7 以**原 md5** 比静态基线 ⇒ **误报 6 条 FAIL**（真实差异仅 `.comment` 内嵌组件 commit） | ✅已修 | A7 改「剥 `.comment` 后比 md5」+ `NOTE` 记录原 md5 差异原因；基线对象入库 `baseline-pre/`（自包含） | 修后 A7 6/6 PASS；`--inject.A7-strip-compare-discriminates=differ`（证明该比较**可失败**） |
| F7 证据脚本缺陷：`check` 传字面量 `>=1` 当期望值；`grep 'R_DADAO_REL12 .*got'` 空格模式**不匹配制表符**；`-static` tag 名带前导 `-` | ✅已修 | 改 `if [ n -ge 1 ]`；模式改 `R_DADAO_REL12[[:space:]]+.*got`；tag 修 `static` | `run-a.sh` **84 PASS/0 FAIL**；`--inject` **10/10**（含静态对象被 PIC 判据逐项拒收） |
| F8 并发写入（**自犯**）：手动 `make build-mc` 与 L2 内触发的 `install-host→build-mc` 并发 ⇒ 构建树两写者，`clang-23` 写坏（4.29 GB/segfault）并被装机 | ✅已修 | `rm` 坏 `clang-23` → 单写者 `build-mc`（200 s PASS）→ `install-host`（312 s PASS）；复验版本串/`--version`/两处 md5 | 「SAME clang/llc/llvm-mc/llvm-objdump/llvm-readobj/llvm-objcopy/ld.lld」7/7；`.work/log/llvm/LLVM-094t-{build-mc,install-host}.log`；L1、L2 于**终态**重跑均 rc=0 |

**判决**：F1–F8 **全部 ✅已修**（无 ⏸延后、无 ❌不修）；每条断言/用例均有**可达 FAIL 路径**（`--inject` 10 项现场证明：静态对象被 PIC 判据逐项拒收 + 副本注入 `ABS48` 被检出 + `cp` 还原后 md5 对账 + 剥注释比较可失败）；无猜测填值、`[OPEN]` 无新增。**自审结论 ⇒ 状态置 `待验收`**（阶段 A 完成；B–E 由后续阶段承接）。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
