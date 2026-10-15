# LLVM-094t: LLVM/LLD 的 PIC 与动态链接支持（`P2` 的前置 / 生产者侧）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-091t`（llvm-project = **23.1.3**，`已验证` 2026-10-14；本册基线）；**口径真源** = `.tao/contracts/contract-dynlink.md`（`§1`–`§10`，用户 **2026-10-14 逐条确认**）、`ADR-0019 D10`（类型号 / 公式 / 值类规则）、`ADR-0026 D1–D8`（行为类口径：`PT_INTERP`、**仅 GNU hash**、不做版本段 / `DT_RELR`、eager、不固定 GOT 基址、超 ±2 KiB 两段式、§10 越界 5 条）；`ADR-0003`（Object ABI）、`ADR-0021`（`ld/st` 符号偏移重定位）、`ADR-0018 C6`/`C7 D4`；`ISS-206`（本册**阶段 E** 的执行落点）；`docs/Process-01`（组件补丁组织与构建编排）
**状态**：待开始
**阶段进度**：A ⏳ ／ B ⏳ ／ C ⏳ ／ D ⏳ ／ E ⏳

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
