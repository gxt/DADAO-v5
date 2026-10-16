# LLVM-094t: LLVM/LLD 的 PIC 与动态链接支持（`P2` 的前置 / 生产者侧）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-091t`（llvm-project = **23.1.3**，`已验证` 2026-10-14；本册基线）；**口径真源** = `.tao/contracts/contract-dynlink.md`（`§1`–`§10`，用户 **2026-10-14 逐条确认**）、`ADR-0019 D10`（类型号 / 公式 / 值类规则）、`ADR-0026 D1–D8`（行为类口径：`PT_INTERP`、**仅 GNU hash**、不做版本段 / `DT_RELR`、eager、不固定 GOT 基址、超 ±2 KiB 两段式、§10 越界 5 条）；`ADR-0003`（Object ABI）、`ADR-0021`（`ld/st` 符号偏移重定位）、`ADR-0018 C6`/`C7 D4`；`ISS-206`（本册**阶段 E** 的执行落点）；`docs/Process-01`（组件补丁组织与构建编排）
**状态**：待验收
**阶段进度**：**A CodeGen PIC ✅ 已验证（2026-10-16，reviewer `Accepted`）**；**B LLD 动态产出 ✅ 已验证（2026-10-16，reviewer `Accepted`〔缩范围重试〕）**；**C ⚠️ 部分交付（2026-10-16，待验收）**＝ ② 主动拒绝（`COPY`/IFUNC/`TLSDESC`/TLS 遇即报错）✅ + ③ A7 基线重定 ✅ + 证据/门控 ✅（`run-c.sh` 48/0、`--inject` 60/0、`run-a.sh` 87/0、`--inject` 97/0、`run-b.sh` 103/0、L1 rc=0；**reviewer 两轮验收，第 2 轮 `Accepted`**（F1/F2/F3 已修））；**① 两段式（`ABS48`+`ldm.o`）阻塞、待用户解法**（三候选清单见「遗留 ①」+ 已登记 `ISS-230`）；**D ⏳ 待做**（与契约逐条对齐）；**E ✅ 已落地、待阶段级验收（2026-10-16，architect 收口 `ISS-206②`）**＝ `.tao/contracts/contract-elf.md §2.2` 按 `ADR-0019 D10` 同步（15 行终表 `NONE`=0 / 静态 `1`–`5` / `ABS48`=**6** / 动态 `7`–`13` / `NUM`=**14**）+ `spec/Toolchain-01:349` 的 `NUM` = 6 字面量按**用户授权原话**（「**授权，但建议删除 `NUM = 6`**」，经主会话问答 2026-10-16）删除 + 册 `sha256` 同变更重算（`bad4bc10…`）；`ISS-206` **保持 `open`**（①③ 随阶段 B 已落地、② 本次收口 ⇒ 待任务级 `已验证` 后回填 `closed`）；门控 **L1 rc=0** + 各单项 rc=0（详见下「阶段 E 记录」）

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

**阶段进度**：**A CodeGen PIC ✅ 已验证（2026-10-16，reviewer `Accepted`）**；**B LLD 动态产出 ✅ 已验证（2026-10-16，reviewer `Accepted`〔缩范围重试〕）**；**C ⚠️ 部分交付（2026-10-16，待验收）**＝ ② 主动拒绝（`COPY`/IFUNC/`TLSDESC`/TLS 遇即报错）✅ + ③ A7 基线重定 ✅ + 证据/门控 ✅（`run-c.sh` 48/0、`--inject` 60/0、`run-a.sh` 87/0、`--inject` 97/0、`run-b.sh` 103/0、L1 rc=0；**reviewer 两轮验收，第 2 轮 `Accepted`**（F1/F2/F3 已修））；**① 两段式（`ABS48`+`ldm.o`）阻塞、待用户解法**（三候选清单见「遗留 ①」+ 已登记 `ISS-230`）；**D ⏳ 待做**（与契约逐条对齐）；**E ✅ 已落地、待阶段级验收（2026-10-16，architect 收口 `ISS-206②`）**＝ `.tao/contracts/contract-elf.md §2.2` 按 `ADR-0019 D10` 同步（15 行终表 `NONE`=0 / 静态 `1`–`5` / `ABS48`=**6** / 动态 `7`–`13` / `NUM`=**14**）+ `spec/Toolchain-01:349` 的 `NUM` = 6 字面量按**用户授权原话**（「**授权，但建议删除 `NUM = 6`**」，经主会话问答 2026-10-16）删除 + 册 `sha256` 同变更重算（`bad4bc10…`）；`ISS-206` **保持 `open`**（①③ 随阶段 B 已落地、② 本次收口 ⇒ 待任务级 `已验证` 后回填 `closed`）；门控 **L1 rc=0** + 各单项 rc=0（详见下「阶段 E 记录」）

**验收结果**（阶段 A 出口，真实输出摘录）：**`-fPIC`/`-fPIE` 目标文件**：`.rela.text` **零**条 `R_DADAO_ABS48`（`P1[pic]/[pie].no-ABS48-in-.text` expect=0 actual=0）、仅 `R_DADAO_REL12`→`.got`；`.got` **4 槽 × 8 B**，槽内容 **4** 条 `R_DADAO_ABS48` 数据重定位（`P2.got-slot-ABS48-relocs` expect=4 actual=4）；指令域 **6** 处 `ld.o rb, [rb0, <slot>]` + **6** 条 `R_DADAO_REL12 .got`（P3，`-dr` 可见）⇒ **偏移为链接期常量**；**无 `rb2`/GP 操作数**（P4 expect=0 actual=0）⇒ 满足「不固定 GOT 基址、不安排专用寄存器」。**生效性**：`-fPIC`/`-fPIE` 与 static 产物 md5 **不同**（A2）⇒ 不再静默压平。**`-S`**：含 `.got` 段 + `[rb0, .Lgot.N]`，`llvm-mc` **可再汇编**（A5 rc=0）；`llc -relocation-model=pic` 同判据。**跳表**：含 2 个 switch 的模块两块表各得**独立**槽 `.LJTI0_0`(+0)/`.LJTI1_0`(+0x10)（A6b）。**大端**：`dataenc=2`（`ELFDATA2MSB`）+ `.data` 常量 `0x01020304` 字节序 = `01 02 03 04`（A8，大端敏感）。**不回归**：静态路径 6 例（`t`/`sw` × O0/O1/O2）剥 `.comment` 后 md5 与**改动前**逐字节相同（A7；`NOTE` 记录原 md5 差异 = 内嵌组件 commit `152cfb15`→`93af153b`）；`-fno-pic` 仍无 `.got`、`.text` 仍 3 片 `ABS48`。**重建/安装**：`build-mc` 单写者 **200 s PASS**（此前 241/210 s 亦 PASS）、`install-host` **PASS**（312 s；前次 129 s）；构建树与安装根 **7 个二进制 md5 全同**（`clang`/`llc`/`llvm-mc`/`llvm-objdump`/`llvm-readobj`/`llvm-objcopy`/`ld.lld`），`clang --version` 报组件 HEAD `93af153b` ⇒ 无 `ISS-210` 假绿。**编号静态核（记录，本次不动）**：`DADAO.def` 现 `R_DADAO_ABS48=0`、`R_DADAO_REL12=4`；`ADR-0019 D10` 期望 `ABS48=6` ⇒ **未同步 = 阶段 E（`ISS-206`）**（A9 NOTE）。

**新发现/坑**：① **「PIC 不支持」的真相 = 驱动静默压平**：`clang/lib/Driver/ToolChains/DADAO.h` 的 `isPICDefaultForced()` 原为 `true` ⇒ `-fPIC` 被**静默**忽略（cc1 实收 `-mrelocation-model static`），产出非 PIC 代码且 **exit 0、无任何报错** —— **不是**「报错不支持」；修前 `-fPIC` 与 static 产物**逐字节相同**。② LLVM **23 无 `Reloc::PIE`**（`Reloc::Model = {Static, PIC_, DynamicNoPIC, ROPI, RWPI, ROPI_RWPI}`）：`-fPIC`/`-fPIE` **均落 `Reloc::PIC_`**（PIE-ness 走 clang `PIELevel`）⇒ 任务书「`Reloc::PIC_`/`PIE`」写法应按此校正；`ROPI`/`RWPI`/`DynamicNoPIC` 在本后端**显式报错**（不静默降 static）。③ **通用 PIC 会改跳表编码**：`TargetLowering::getJumpTableEncoding()` 在 `isPositionIndependent()` 时返 `EK_LabelDifference32`（4 B label difference）⇒ DADAO 无 32 位数据重定位，汇编期硬错 9 条（「cannot carry a 48-bit DADAO address」）⇒ 覆写恒返 `EK_BlockAddress`（8 B 绝对表项 = 契约 §4.3「数据」形态）。④ **MC 文本路径两处缺陷**（仅 `-S` 暴露）：`DADAOMCInstPrinter` 的 `ld./st.` 无条件 `getImm()`（遇符号表达式操作数即断言）；`MCContext::getELFSection(..., EntrySize=8)` 触发 `MCAsmInfoELF::printSwitchToSection` 断言（非 `SHF_MERGE` 不得带 entsize）⇒ 去 `EntrySize` 并改用 `emitValueToAlignment(Align(8))`。⑤ **设计取舍（跨阶段披露）**：契约**禁新增重定位类型**（`ADR-0026 D5`/`contract-dynlink §3`）且 ISA 无「`rb0`+符号偏移 → 寄存器」形态 ⇒ **GOT 槽由编译器自出**（`.got`：每引用符号/跳表一 8 B `R_DADAO_ABS48` 数据槽），指令域用**既有** `R_DADAO_REL12`（`rb0` PC 相对）寻址 ⇒ **阶段 B/C** 的 lld 须**保留/合并输入 `.got`**、把槽 ABS48 转为动态重定位（`REL_GOT`/`RELATIVE`）、并按 `D5` 保证槽「就近 ±2 KiB」。⑥ **并发坑（本次自犯，已修复留证）**：`make check-modules` 经 `check-picolibc-tests → build-picolibc → install-host → build-mc` **会自行重建**；我同时手动 `make build-mc` ⇒ **两个 ninja 写同一构建树**，`bin/clang-23` 被写坏（4.29 GB、`--version` segfault）并被 `install-host` 装入安装根 ⇒ `ISS-229` 的同类风险**不止安装根、构建树同样**（「手动重建」须与 L2 串行）；已单写者重建 + 重装 + 复验（`--version` rc=0、md5 7/7 同）并于终态重跑 L1/L2。⑦ 既有派生投影 `llvm-isa-backend-matrix` 会因后端源码**行号/证据计数**变化而 drift ⇒ 改后端须连带重生成（本次由 L1 现场暴露并修复）。

**遗留问题**（阶段 A 视角；阶段 B 完成后见下行「遗留问题（阶段 B）」）：① **阶段 B–E 未做**（LLD `ET_DYN`/`.dynamic`/GNU hash/`GOT`·`PLT`/动态重定位；`ADR-0019 D10` 新编号；契约逐条；`ISS-206`）——本册其余阶段承接。② **PIC 下外部函数调用仍为直接 `REL26`**（PC 相对）：未走 PLT（`JUMP_SLOT`/`.plt` = 阶段 B/C）⇒ `.so` 场景该调用点须链接器改写。③ **PIC 跳表内容仍为绝对地址**（8 B 数据 `ABS48`，契约 §4.3 允许）：共享对象需装载期 `RELATIVE` 修正（阶段 B/C）。④ **未新增 lit / PIC 回归用例**（本阶段判据由 `run-a.sh` 覆盖）；`tests/llvm/codegen/m6/README.md` 现仍写「`REL12`/`ABS12` 仅汇编层、CodeGen 未发射」，PIC 后该口径已过时（建议后续并入 `check-lit`/`expected-elf`）。⑤ `milestones.md` 流水行交 `/complete` 收尾（本册按规则**未**写 `milestones.md`；组件 changelog 已按维护规则在同一变更内追加）。⑥ **未撞** `ISS-222`（无 inline asm / `dynamic_stackalloc`）/ `ISS-223`。

**测试结果**（阶段 B）：`.work/evidence/LLVM-094t/run-b.sh` **103 PASS / 0 FAIL（rc=0）**；`--inject` **113 PASS / 0 FAIL（rc=0）**（8 项注入：`e_type`/`DT_HASH`/eager 位/`.rela.plt` 类型号/PLT 内嵌常量/`DT_PLTGOT`/`.interp` 串/`PT_INTERP.p_filesz`，逐项证明「该点有可达 FAIL 路径」）；**第三个独立解析面 = GNU `readelf`**（binutils 2.42 不认识 DADAO ⇒ 重定位类型列打印 `unrecognized: N`，取 `r_info` 低 32 位独立确认 `ABS48=6`/`JUMP_SLOT=7`，并独立确认 `ET_DYN`/大端/`GNU_HASH` 且无 `HASH`/解释器串）。`make check`（**L1**）**rc=0**；`make check-modules`（**L2**，单独跑）**rc=0**；`check-patch-tree`（5 component / **146 patches**）/`check-index-blobs`（108 new + 38 modification）/`check-instrinfo`/`check-source-state`/`check-no-residue`/`check-tasks`/`python3 tools/infra/check_issues.py`/`check-component-changelog` 各 **rc=0**。**终态复验**（L2 自行 `install-host` 重建后重跑）：`run-b.sh` **103 PASS / 0 FAIL**、`--inject` **113 PASS / 0 FAIL**、`make check`（L1）**rc=0**（日志 `.work/log/llvm/LLVM-094t-B-*-final.log`）。全文 `.work/log/llvm/LLVM-094t-B-*.log`。

**修改文件**（阶段 B）：① 组件补丁树 **3 改 + 1 新增**（`components/llvm-project/patches/**`，一文件一补丁、`series` **71→72**）= `llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def`（改）、`lld/ELF/Arch/DADAO.cpp`（改）、`lld/ELF/Driver.cpp`（**新增补丁**）；源树 `.work/source/llvm-project` HEAD `d40e1bb6e` = base+1 且干净（`check-patch-tree`/`--source-state` rc=0）；② `components/llvm-project/changelog.md`（M8 追加「阶段 B」一条）；③ **既有向量编号注记同步 4 处**（`tests/llvm/lit/MC/DADAO/{dd-symbol,rela-addend,m6-callconv}.s` 的类型号数字 + `rela.s` 注释）——即 `ISS-206③`「产物/向量写死类型号」排查面**首次命中**；④ **新增 `tests/scripts/dadao-dyn.lds`**（ET_DYN 链接布局：`.got` 紧随 `.text`，满足 `ld.o [rb0, slot]` 的 ±2 KiB；理由见该文件头与「新发现 ④」）；⑤ `.work/evidence/LLVM-094t/{run-b.sh,dyncheck.py,inject.py,objdiff.py}` 与 `.work/log/llvm/LLVM-094t-B-*.log`（**披露**：`.work/**` 被 `.gitignore` ⇒ 证据/日志**不入 git**、留工作区，沿用阶段 A 先例）；⑥ 本任务书（完成区 + 自审）。

**验收结果**（阶段 B 出口，真实输出摘录）：
- **共享库**（`-shared -soname libtest.so.1 -T tests/scripts/dadao-dyn.lds`）：`e_type=3`（`ET_DYN`）、`EI_DATA=2`（大端）、`e_flags=0x1`；必备段 **10/10** = `.dynamic .dynsym .dynstr .gnu.hash .rela.dyn .rela.plt .got .got.plt .plt .text`；`DT_SONAME=libtest.so.1`、`DT_GNU_HASH` 有、**无** `DT_HASH`/`.hash`、**无** `DT_RELR`/`DT_RELRSZ`/`.relr.dyn`、**无** `DT_VERSYM`/`DT_VERNEED`/`DT_VERDEF`/`.gnu.version*`；`DT_FLAGS=BIND_NOW` + `DT_FLAGS_1=NOW`（eager）、`DT_PLTGOT=0x258`（**= `.got.plt` 地址**）、`DT_JMPREL`/`DT_PLTRELSZ`/`DT_PLTREL=RELA`、`.rela.dyn`/`.rela.plt` 均 `SHT_RELA`；`.rela.dyn` 类型集 **{6}**（`ABS48`）、`.rela.plt` 类型集 **{7}**（`JUMP_SLOT`，符号 `ext_fn`）；PLT 入口自洽（`ld.o rd5,[rb0,16]` + `ldm.o {rb4},[rb0,rd5]` + `jump [rb4,rd0,0]` + 8 B 常量 = `槽地址 − (入口+4)`）且 `llvm-mc` 独立汇编同序列**逐字相同**（`20140010,3a100141,71100000`）。
- **动态可执行**（`-pie -dynamic-linker /lib/ld-musl-dadao.so.1`）：`ET_DYN` + `e_entry≠0` + `PT_INTERP`（`p_filesz=24`、字节**逐字** `/lib/ld-musl-dadao.so.1\0`）+ `DT_NEEDED=libtest.so.1` + eager + `PT_GNU_RELRO`（eager ⇒ full RELRO 可行）；**未传** `-dynamic-linker` ⇒ 解释器串为空（**不改 lld 默认**）。
- **静态不回归**：6 例（`t`/`sw` × O0/O1/O2）对象 `.text`/`.data` **逐字节相同**、20–21 条重定位**仅类型字段 0→6**、无其它差异（`objdiff.py`）；静态链接 `ET_EXEC` 且无 `.dynamic`；`--defsym ext=0xABCD12345678` ⇒ `.data` = `0000abcd12345678`（48 位 / 大端 / 高 16 位 0）；`-z rel` 显式拒绝；**默认布局**（无脚本）⇒ `R_DADAO_REL12 out of range` **链接期报错**（§10④，不静默截断）。
- **重建/安装**：`build-mc` ≈ 5 min（PASS）、`build-lld` ≈ 40 s（PASS）、`install-host` 43 s（PASS）；安装根与构建树 **clang / ld.lld md5 全同**（`run-b.sh` 0 组断言）⇒ 无 `ISS-210` 假绿。

**新发现/坑**（**阶段 B**）：① **旧编号下动态产出不可实现**：lld 把类型 `0` 当 `R_NONE`（`processAux` 的 `rel != 0` 门控 + `iRelSymbolicRel` 哨兵）⇒ `ABS48=0` 时**任何**动态重定位都发不出（实测 `ld.lld -shared` 报 `relocation R_DADAO_ABS48 cannot be used against symbol 'gv'; recompile with -fPIC`；同 `.tao/archive/M4/llvm/LLVM-056t` ① 已记的同类坑）⇒ 阶段 B **被迫**含 `DADAO.def` 改号（编号**全部**取自用户已确认的 `ADR-0019 D10`，**无自拟**）——与派单「重定位新编号归 C」的边界冲突，见遗留 ①。② **`getIsRela` 是按机器白名单**：`EM_DADAO` 不在册 ⇒ 动态表默认发 **`SHT_REL`** 并走 `getImplicitAddend`（未实现 ⇒ `internal linker error: cannot read addend`）；必须显式加入（契约 §4.1 要求 `SHT_RELA`）。③ **两个 lld 缺省须按契约改**：非 MIPS 目标默认 **双发** SysV+GNU hash 且 `zNow=false` ⇒ 不改缺省就会产出 `DT_HASH`、且本阶段 PLT 是 **eager-only**（`pltHeaderSize=0`，无 lazy resolver）⇒ 对 `EM_DADAO` 分别改缺省（`ADR-0026 D3`/`D6`）。④ **GOT 可及性 = 布局义务**：`-fPIC` 用单指令 `ld.o [rb0, slot]`（`imms12`，±2 KiB）访 GOT，而 lld 默认布局把 RW 段按 `max-page-size`（DADAO 64 KiB）对齐 ⇒ `.got` 距 `.text` **实测 65592 B**（`--print-map` 实证），单指令不可及；**压页**（`-z max-page-size=0x100`）虽能让距离达标，但会产生**跨段同页**的非法 ELF（实测两 PT_LOAD 落在同一 4 KiB 页 ⇒ 弃用）。⇒ 现阶段 ET_DYN 产出须用「**单一 RWX PT_LOAD** + `.got` 紧随 `.text`」的布局（`tests/scripts/dadao-dyn.lds`，沿用 M4 `RAM (rwx)` 模型）；通用解法 = 阶段 C 的两段式路径。⑤ **`PHDRS` 与段全集**：脚本一旦给 `PHDRS`，未列出的段不进任何程序头（实测漏列合成段 ⇒ `PT_INTERP.p_filesz` 被撑成 232）⇒ 段必须全列。⑥ **PLT 设计要点**：入口内嵌**链接期常量**（槽地址 − 入口地址）经 `ldm.o {rb4},[rb0,rd5]` 装载 ⇒ 与 `.plt`/`.got.plt` 的实际距离**无关**、无需 textrel（`.plt` 无重定位）；stub 只用 `rb4`/`rd5`（caller-saved temporary），不动 RB/RegRAS/SP ⇒ 调用者 `call` 压的返回址仍由被调者 `ret` 弹出。⑧ **工具链二进制内嵌组件 VCS revision**：`VCSRevision.h`/`VCSVersion.inc` 由 `.work/source/<组件>` 的 git 状态生成 ⇒ 组件源树每新增一笔本地 commit（本次 = 编号同步那笔）都会改变 `clang`/`llvm-mc`/`ld.lld` 等二进制字节与对象 `.comment`，并触发 20 个目标的重新编译/链接（实测 L2 内的 `install-host` 因此重建）；故「`install==build` md5」与「剥 `.comment` 后比对」两个口径必须成对使用（阶段 A 已如此，本阶段沿用）。⑦ 阶段 A `run-a.sh` 的 **A7 对象级 md5 基线过期**（编号同步改了对象字节；差异已证明**仅限重定位类型字段**）：**本阶段末实跑 `run-a.sh` = 78 PASS / 6 FAIL，6 条全部是 A7 的 md5 基线**，其余（含 `A9` 按 `ADR-0019 D10` 的 `ABS48=6 REL12=4` 断言）全 PASS——即失败面**只有**已过期的对象级基线，无功能回归（日志 `.work/log/llvm/LLVM-094t-B-runa-after-B.log`）——见遗留 ②。

**遗留问题**（**阶段 B**）：① **与派单边界的冲突（需主会话/用户裁定）**：阶段 B 的实现被迫包含 `DADAO.def` 编号同步（+4 处既有向量数字注记），而派单写明「重定位新编号归阶段 C」；数值均取自 `ADR-0019 D10`（用户已确认）⇒ 未自拟编号。阶段 C/E 的**剩余面** = `ABS48` 两种编码与 `JUMP_SLOT`/`RELATIVE` 公式的逐条 oracle、`COPY`/`TLSDESC` 注入报错、`lld` 头注释同步、`ISS-206③` 的全仓产物/向量排查（本阶段首次命中 4 处）。② **阶段 A `run-a.sh` 的 A7 基线是否重定（建议重定，但需授权）**：现 78 PASS / 6 FAIL（全为 A7 md5），差异性质已由 `run-b.sh` 的 `objdiff` 断言证明为「仅重定位类型字段」；按「不擅自改已验收证据」本阶段**未动** `baseline-pre*/`，请主会话/用户裁定（重定即 6 条回绿）。③ **`COPY` 类型的主动拒绝未实现**：`getDynRel(ABS12)==0` 的「非 PIC 可执行引用 DSO 数据符号」路径仍可能发 `R_DADAO_COPY`(9)（编号正确、musl 支持 `REL_COPY` ⇒ **非静默**；是否按「首版不发射 ⇒ 遇即报错」收紧归阶段 C）。④ **IFUNC/`.iplt` 未支持**（`ipltEntrySize=0`、`iRelativeRel=0`）：遇 GNU IFUNC 会静默产出无效 PLT；本阶段**未构造实例**，建议 C/D 补显式拒绝。⑤ `-z lazy` 未拒绝（本项目 PLT 不支持 lazy）；`gotPltHeaderEntriesNum=2` 中 `GOT[1]` 无用途（无 lazy）。⑥ 未新增 lit/`expected-elf` 用例（判据由 `run-b.sh` 承载）；`tests/llvm/codegen/m4|m6/README.md` 的「`REL12`/`ABS12` 仅汇编层」等旧口径未随 PIC/动态更新。⑦ 未撞 `ISS-222`/`ISS-223`、未新增 `issues.yaml` 条目。


**测试结果**（阶段 C）：`.work/evidence/LLVM-094t/run-c.sh` **48 PASS / 0 FAIL（rc=0）**；`--inject` **60 PASS / 0 FAIL（rc=0）**（12 项注入：`COPY`/IFUNC/类型号 9·13·10–12 的**因果性**反例〔类型号或符号类型改回 ⇒ 链接成功〕+ oracle 判别性〔`.rela.dyn` 类型 6→7、`S+A` 字段篡改 ⇒ 检查失败〕+ 原件 md5 前后对账）；`run-a.sh`（**A7 基线按阶段 C 重定** + **源内联自包含**〔第 4 轮 F1〕）**87 PASS / 0 FAIL（rc=0）**、其 `--inject` **97 PASS / 0 FAIL（rc=0）**、`run-b.sh` **103 PASS / 0 FAIL（rc=0）**；独立 oracle `oracle_c.py`（自写 ELF64-BE 解析 + `ADR-0019 D10` 公式）**20/20**（`O5` ABS48×2 + `O6` RELATIVE×2 **均实际执行、非空转**〔第 4 轮 F2〕）；`make check`（L1）**rc=0**；`check-patch-tree`（5 component / **147 patches**）/`check-index-blobs`/`check-instrinfo`/`check-source-state`/`check-no-residue`/`check-tasks`/`python3 tools/infra/check_issues.py`/`check-component-changelog` 各 **rc=0**；`make check-modules`（L2，单独跑）**rc=0**（与阶段 B 同口径：`picolibc-tests: stage=fast … blocked=20` 为既有 `ISS-193` 状态、`fail=0`）；**终态复验**（**第 4 轮返工后重跑**：`/tmp` 现场清空 ⇒ 脚本自包含）：`run-a.sh`/`run-b.sh`/`run-c.sh`/`run-c.sh --inject` 各 **rc=0**（87/0、103/0、48/0、60/0）——**取代**返工前「L2 内 `install-host` 重建后重跑（44/0、56/0）」的记录（L2/L3 归任务整体收尾，本轮**未跑**）；L1 `make check` + `check-patch-tree`/`check-no-residue`/`check-tasks`/`check-component-changelog` 复跑各 rc=0。日志 `.work/log/llvm/LLVM-094t-C-*.log`。

**修改文件**（阶段 C）：① 组件补丁树 **2 改 + 1 新增**（一文件一补丁、`series` **72→73**）= `lld/ELF/Arch/DADAO.cpp`（改）、`lld/ELF/Relocations.cpp`（**新增补丁**）；源树 `.work/source/llvm-project` HEAD `fb1ad9b1b` = base+1 且干净（`check-patch-tree`/`--source-state` rc=0）；② `components/llvm-project/changelog.md`（M8 追加阶段 C 一条）；③ `.work/evidence/LLVM-094t/{run-a.sh,run-c.sh,mutate.py,oracle_c.py,baseline-pre-nocomment.md5,baseline-pre-raw.md5,baseline-pre-preC/}`（**第 4 轮**：`run-a.sh` 源内联自包含〔F1〕、`run-c.sh` 交付场景补 `RELATIVE` 槽 + oracle 非空转断言〔F2〕；**A7 重定后的新基线** + 旧基线留档；`.work/**` 被 `.gitignore` ⇒ 证据不入 git，沿用阶段 A/B 先例）；④ 本任务书（完成区 + 自审）；⑤ `.tao/knowledge/milestones.md`（`LLVM-094t` 流水行：括号笔误订正〔F3〕+ C 段计数同步）。

**验收结果**（阶段 C 出口，真实输出摘录）：
- **主动拒绝（`ADR-0026 D7②` / `contract-dynlink §10②`；真实错误文本）**：① **`COPY`**：非 PIC 可执行引用 DSO 数据符号（`ld.o rd5,[rb16,gv]` ⇒ `R_DADAO_ABS12`，无动态形态）⇒ rc=1 + `cannot create a copy relocation for symbol 'gv': R_DADAO_COPY is not emitted by this implementation (ADR-0026 D7②, contract-dynlink.md §10②); recompile with -fPIC`；**同场景 PIC 版本（`-fPIC` 走 GOT 槽）rc=0** ⇒ 拒绝键在「需副本」而非「引用 DSO」；② **GNU IFUNC**：把 `res` 的符号类型改为 `STT_GNU_IFUNC(10)`（副本注入）⇒ rc=1 + `GNU IFUNC symbol 'res' is not supported (no .iplt/IRELATIVE; ADR-0026 D7②)`；③ **类型号注入**（`.rela.data` 首条 6→9/13/10/11/12）⇒ 逐条 rc=1：`relocation type R_DADAO_COPY is not emitted by the DADAO linker (ADR-0026 D7②)`、`… R_DADAO_TLSDESC …`、`TLS dynamic relocation R_DADAO_TLS_DTPMOD|DTPREL|TPREL is not supported yet (contract-dynlink.md §7)`；④ 正常 DSO **无** `.iplt` 段、`.rela.dyn` 无 9/13/10–12。
- **独立 oracle**（`oracle_c.py`；`ADR-0019 D10` 公式）：**交付场景**（`lib.c` 含 `static int sv` + `int *psv = &sv`）的 `libtest.so` `.rela.dyn` **4 条**、类型集 **{6,8}**，oracle **20/20**（`O5` ABS48×2 + `O6` RELATIVE×2 **均实际执行**，非空转）：**type 6**（`gv`@`0x190`、`psv`@`0x1A0` ⇒ 均为 GOT 槽）⇒ `r_addend = 0`（`S + A`，A 由记录给出）且符号名可在 `.dynsym` 解析；**type 8**（`0x198`（`.data` 内的 `psv` 初值槽）、`0x2F8`（`sv` 的 GOT 槽））⇒ `r_addend` = **已定义符号 `sv` 的 `st_value`（`0x2F4`）**（`B + A`，`≠0`）；槽地址（`r_offset`）8 字节对齐、落在 `SHF_WRITE|SHF_ALLOC` 段内。`readelf -r`（binutils，第三方面）逐条复现：`type 8`×2（addend `2f4`）+ `type 6`×2（`gv`/`psv`）+ `.rela.plt` `type 7`（`ext_fn`）。
- **大端**：`EI_DATA = ELFDATA2MSB(2)`；`--defsym ext=0xABCD12345678` ⇒ `.data` = `0000abcd12345678`（48 位 / 大端 / 高 16 位 = 0）。
- **A7 基线重定（授权来源 = 主会话 2026-10-16 裁定 3）**：`run-a.sh` **rc=0**；`objdiff` 独立复核「重定前（`baseline-pre-preC/`，阶段 A 对象）vs 重定后」＝ `code_identical=yes`、`nonrela_diffs=-`、`abs48_renumbered=20/20`·`21/21`、`type_mismatch=0` ⇒ **差异仅重定位类型字段 0→6**（属预期编号同步；`baseline-pre/` 的**对象**保持阶段 A 原件〔`run-b.sh` 的 4.static 以它作「重编号前」参照〕，仅 **md5 清单**按阶段 C 重定）。
- **不回归**：`run-b.sh` 全绿（静态 6 例经 `objdiff` 判「仅重编号」、动态面全绿）；静态对象 `.text`/`.data` **逐字节不变**。
- **重建/安装**：`make install-host` **≈6 min**（申报 5–6 min；组件 commit 变化触发 20 目标重编）⇒ 安装根与构建树 `ld.lld`/`clang` md5 相同（`run-c.sh` 断言 0 组）。
- **①/②「两段式」未交付（披露）**：`-shared` 默认布局 rc=1：`R_DADAO_REL12 out of range: 65620 is not in [-2048, 2047]; references section '.got'`；`-z max-page-size=0x1000` 仍 **4180 B** > ±2 KiB（**本轮交付场景**的值；随源/布局而变——architect 独立复现为 65552/4112 ⇒ 量级一致；`run-c.sh §5` 现取**首条**越界引用）⇒ **任何分段布局**下 `ld.o [rb0, slot]` 单指令访问均不可达；`ADR-0026 D5` 的 `ABS48` 序列 + `ldm.o_rrri_rb` 两段式**未实现**（当前越界行为仍按 `D7④` 显式报错，非静默）；原因与候选方案见「遗留问题」。

**新发现/坑**（**阶段 C**）：① **两段式的可行性缺口（现场核）**：`ABS48` 序列须把**偏移**算进 `rd`，而 `rd` 侧无一可用寄存器——`rd0` 硬连零、`rd1`=`rderrno`（ABI 定义）、`rd2–rd3`=「调试/测试保留，编译器不得分配」、`rd4+` 归编译器；链接器亦无「零 `rb`」可用（`ADR-0026 D5` 原文），且 `ldm.o {rbX}, [rbH, rdC]` 的偏移域**只能是 `rd`**（`ld.o` 只有 `imms12` 立即数形式）。⇒ 该序列**只能由编译器在对象内发射**（则须改阶段 A 已验收的 PIC 对象形态与 `run-a.sh` 的 P1/P3 断言），或由链接器引入**保留寄存器 / 可执行数据段 / TEXTREL** 等新约定 ⇒ 三者皆属**新决策**，本阶段**未擅自实施**。② **`add.si rbHA, imms18` 是 ISA 中唯一的宽范围（±128 KiB）PC 相对加法**，但**无匹配重定位类型**（`REL14/20/26` 为字偏移、`REL12`/`ABS12` 仅 `imms12`）⇒ 亦须新类型/新编码。③ **`getDynRel()==0` 才走副本路径**：`R_DADAO_ABS48` 有动态形态，但**在只读段（`.text`）**的 ABS48 引用（非 PIC 绝对地址构造）**同样命中副本路径**（`canWrite=false`）⇒ 阶段 B 遗留 ③ 的现场范围确认（`ABS12` 为典型触发者）。④ **`--apply-dynamic-relocs` 不可用**：lld 报 `internal linker error: cannot read addend for relocation R_DADAO_ABS48|JUMP_SLOT`（DADAO 未实现 `getImplicitAddend`）⇒ 槽的**落地值**只能在静态 `S + A` 形态（`--defsym` 数据字段）上核，运行期槽内容按 ELF 语义由装载器填。⑤ **组件 commit 与安装根的内嵌 revision**：本次两次 amend（`b550364f3`→`fb1ad9b1b`）都会改二进制内嵌的 `VCSRevision`；`install == build` md5 与「剥 `.comment` 比对」两个口径必须成对使用（沿用阶段 A/B 口径）。

**遗留问题**（**阶段 C**）：① **【未交付·待裁定】 两段式（`ADR-0026 D5`，本阶段「核心」①）**：现场证据表明其在现有 ABI/重定位集内**不可实现**（见「新发现 ①②」）⇒ 三条候选（均须裁定）：**(a)** 编译器发射两段式（`set.zw/or.w/or.w` 三片 **rd 目的** + `ldm.o_rrri_rb`），链接器把 `ABS48` 的 **rd 目的** 片视为 **PC 相对偏移**（`S + A − P`，即 `REL12` 公式的宽字段版本）——**最贴 `ADR-0026 D5` 原文**，但须改阶段 A 已验收的 `run-a.sh` P1/P3 断言，并把「单指令访问」降级为「一律两段式」（`ADR-0019 D7` 禁 relaxation ⇒ 不能在链接期缩回单指令）；**(b)** 让出/新增一个**链接器临时寄存器**（或新增宽 PC 相对重定位类型），由**链接器**就地展开/合成（无对象形态改动、P1/P3 保留），但属 ABI/契约扩展；**(c)** 接受现状（越界即 `D7④` 报错）并把「.got 就近布局」的责任交给**构建侧脚本**（阶段 B 的 `dadao-dyn.lds` 单段 RWX 布局；`INFRA-085t` 消费侧）。② **`ISS-206②`**（`.tao/contracts/contract-elf.md §2.2` 旧号 + `spec/Toolchain-01:349` 的 `NUM=6`）**仍须用户授权**（阶段 C 未动）。③ 未新增 lit / `expected-elf` 用例（阶段 C 判据由 `run-c.sh` 承载）；`tests/llvm/codegen/m6/README.md` 的旧口径（「`REL12`/`ABS12` 仅汇编层」）仍未随 PIC/动态更新。④ `-z lazy` 未拒绝（阶段 B 遗留 ⑤ 顺延）；`gotPltHeaderEntriesNum=2` 中 `GOT[1]` 无用途。⑤ 未撞 `ISS-222`/`ISS-223`；未新增 `issues.yaml` 条目。

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

#### 第 1 轮 reviewer 验收（2026-10-16）

**重跑记录**：`run-a.sh` **84 PASS / 0 FAIL / rc=0**；`--inject` **10/10 PASS / rc=0**；`make check`（L1）**rc=0**；`check-patch-tree` **rc=0**（5 component, 145 patches）；`check-instrinfo` **rc=0**；`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check_issues.py` 各 **rc=0**。7 个二进制 build/install md5 **全同**。

**独立验证**（reviewer 自行编译 + elfinfo.py）：
- ⭐**破静默压平**：`-fPIC` 与 `-fno-pic` 产物 md5 **不同**（9a87… vs d3c6…）✓
- PIC `.text`：0 条 `ABS48`、3 条 `REL12`→`.got`；`.got`：3 槽×8B、3 条 `ABS48` 数据重定位
- 反汇编：`ld.o rb4, [rb0, ...]` + `R_DADAO_REL12 .got`（PC 相对）；**无** `rb2`/`rbgp` 操作数
- `-fPIE`：同判据，rc=0、`.got` 存在、`REL12`→`.got`、产物与 static 不同 ✓
- **不回归**：6 例静态对象剥 `.comment` 后 md5 **逐字节同** baseline ✓
- **大端**：`dataenc=2`、`.data` 偏移 4 处 `01 02 03 04`（BE 敏感）✓
- `-fPIC -S`：含 `.got` 段 + `[rb0, .Lgot.N]`；`llvm-mc` rc=0（可再汇编）✓
- **旧编号未误改**：`DADAO.def.patch` 仍 `ABS48=0/NUM=6`；`d92927e` 未改 `DADAO.def`/`ELF.h`/`lld` ✓
- **契约符合**：`selectRelocModel` 仅接受 `Static`/`PIC_`；`isPICDefaultForced()=false`；无 `rbgp` GOT 访问 ✓
- **新反例注入**（临时树）：篡改 `DADAO.def.patch` REL12 编号 4→7 ⇒ 6 FAIL → 还原 md5=444f… ⇒ 0 FAIL / rc=0 ✓

**发现（非阻断）**：
① 完成区写「11 份补丁」但 `git show` 统计 d92927e 含 12 份 `.patch` 文件（漏计 1 份）；
② 证据脚本 A9 为常真断言（两支均 `PASS`），不符合「禁恒真」规则——但 A9 声明为「record only」且不影响阶段 A 出口判据（`REL12`/`GOT` 槽等核心断言均有可达 FAIL 路径）；建议后续阶段修正 A9 结构（else 分支仅 NOTE、不 PASS）。

**判决**：**Accepted** —— 阶段 A 出口判据全部满足（`-fPIC` 破静默压平、GOT 槽+PC 相对 `REL12`、无 `rbgp`/专用寄存器、静态不回归、大端、旧编号未动、门控全绿）；遗留项（B–E / PLT / 跳表 / lit）已如实登记。

#### architect 提交 / 文件集审核留痕（2026-10-16）

- **分支现场勘误**：主会话交办称分支 `LLVM-094t-A` **已建** ⇒ 现场核 `git branch -vv` / `git worktree list` / `.git/HEAD` / reflog（`fe26263 HEAD@{0}: merge llvm-094t-taskbook`）**均无该分支**（仅 `master` = `fe26263` = `origin/master`）；**未用 `switch -c`**，以 `git branch LLVM-094t-A` + `git symbolic-ref HEAD refs/heads/LLVM-094t-A` 建于 `fe26263`（**工作树 / 索引零改动**：`git diff --cached` 仍 15 项）⇒ 两笔提交落该分支，`master` 未动。
- **文件集对账**（显式 staging、**未用** `git add -A`）：`git status --porcelain -uall` **15 项 / 0 untracked**、无 `spec/` / `contracts/` / `.tao/contracts/` 越界；与完成区「修改文件」逐条对齐 —— 11 补丁 + `tools/llvm/llvm-isa-backend-matrix.{md,tsv}` + `components/llvm-project/changelog.md` + 本任务书 = **15** ✓（④ `.work/**` 被 `.gitignore` 排除、不入 git）⇒ **无漏提 / 多提 / 越界**。
- **笔 1** = `d92927e`（15 文件、`M`×15、+380/−85）；**笔 2** = `5ba6547`（`ISS-229` notes 追加，仅 1 行变更）。**档位披露**：阶段 A = `待验收`、reviewer 未验收 ⇒ 按 `architect.md` 常规应为 `WIP:` 前缀；**主会话本次明确指令「笔 1 不带 `WIP:`」** ⇒ 从指令执行并在此披露。
- **只读核对（真实 rc）**：`make check`(L1) **rc=0**（尾行 `repository checks (L1): PASS`；内含 `check_issues: 39 open, 13 closed`）、`make check-patch-tree` **rc=0**（`5 component(s), 145 patches OK`；`components/llvm-project/series` = **71** 行）、`make check-index-blobs` **rc=0**（`108 new-file / 37 modification`）、`make check-source-state` **rc=0**（`musl HEAD=d31bf832… clean=True`）、`check_issues.py` **rc=0**。日志 `.work/log/llvm/LLVM-094t-architect-*.log`。
- **未** `merge`、**未** `push`（`git ls-remote origin refs/heads/master` = `fe26263`；无 `LLVM-094t-A` 远端分支）；收尾后工作树 `git status --porcelain -uall` = 空。

#### architect 阶段级收尾 / 提交 / merge 留痕（2026-10-16，阶段 A）

- **阶段级收尾**（照 `INFRA-082t`/`SPEC-142t` 先例；阶段 A 已 `Accepted`、**B–E 待做** ⇒ 任务级 `**状态**` **保持 `待验收`** ✓，**不置 `已验证`**）：L1 `make check` **rc=0**（尾行 `repository checks (L1): PASS`；内含 `check_issues: 39 open, 13 closed`）+ `check-patch-tree`（`5 component(s), 145 patches OK`）/`check-index-blobs`/`check-instrinfo`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-knowledge-dir` + `python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身** rc；日志 `.work/log/llvm/LLVM-094t-architect-stageA-*.log`）；**L2/L3 归任务整体收尾**（阶段 B–E 完成后跑）；临时残留 = 无（`check-no-residue` rc=0）；证据在 `.work/evidence/LLVM-094t/`（`run-a.sh`/`elfinfo.py`/`baseline-pre*`；`.work/**` 被 `.gitignore` ⇒ 不入 git，沿用既有先例）。
- **补丁计数复核（reviewer 发现 ① 的处置）**：reviewer 记「`git show` 统计 `d92927e` 含 **12** 份 `.patch`」⇒ architect **独立复核**：`git diff-tree -r --no-commit-id --name-status d92927e` = **15 项**（**11** `.patch` + `llvm-isa-backend-matrix.{md,tsv}` + `changelog.md` + 本任务书）、`git diff --name-only fe26263..HEAD | grep -c '\.patch$'` = **11**、`git status --porcelain --ignored -uall components/llvm-project/patches` = **0**（无 ignored / untracked 第 12 份）⇒ 完成区「**11 份补丁**」**与 `--name-status` 一致**，reviewer ①「12 / 漏计 1 份」**无法复现、不成立** ⇒ **保持 11、不改写为 12**（改写即与 diff 矛盾）；本条**留痕待主会话裁定**。
- **reviewer 发现 ②**（证据脚本 A9 常真断言）**非阻断** ⇒ 转 **B–E 阶段遗留**（后续阶段改 A9 结构：else 分支仅 `NOTE` 不 `PASS`）；本次**未动** `run-a.sh`（不触碰已验收证据）。
- **提交**：显式 staging（本任务书 + `.tao/knowledge/milestones.md`）、**未** `git add -A`；档位 = **正常提交**（reviewer 判决 `Accepted`）；**只 `commit`、未 `push`**。
- **随后（同次收尾）**：`git switch master` → `git merge --ff-only LLVM-094t-A` → `git branch -D LLVM-094t-A`；**不 push** ✗。


#### 第 2 轮 engineer 自审（阶段 B）

**逐行审查范围**（自主）：4 份补丁逐文件复核 —— `DADAO.def` 编号表与 `ADR-0019 D10` 逐行对齐；`DADAO.cpp` 的 `symbolicRel/gotRel/pltRel/relativeRel/copyRel`、`getDynRel`、`getRelExpr(REL26)=R_PLT_PC`、`undefBranch` 的 `rel.expr==R_PC` 守卫、`writePlt` 的 4 段字节编码与自洽性、`writeGotPlt*`、`relocate` 的动态类型分派（含 `COPY`/`TLSDESC`/TLS 显式报错）；`Driver.cpp` 的 `isRela` 白名单 + `-z rel` 拒绝、`--hash-style`/`-z now` 缺省；并核对「判据独立」（`dyncheck.py` 自解 ELF64-BE、不调用 LLVM 读取器；PLT 编码另用 `llvm-mc` 独立汇编对账）、每条断言的**可达 FAIL 路径**（`--inject` 8 项）、期望值来源（`ADR-0019 D10` 编号 / gABI 标签 / 契约条款）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `getRelExpr(REL26)` 改 `R_PLT_PC` 后，未定义**函数**的动态调用会命中阶段 A 的「未定义弱 → 自循环」特例（`val` 被 `addend` 覆盖，PLT 地址丢失） | ✅已修 | `undefBranch` 加 `rel.expr == R_PC` 守卫（仅静态直接分支走自循环） | `run-b.sh` 1 组（`.rela.plt` 含 `ext_fn` + `.text` 调 PLT 入口）；静态 6 例不回归 |
| F2 阶段 A 遗留的 `iRelSymbolicRel = R_DADAO_NUM` 在改号后仍安全？（`NUM` 14 与任何真实类型都不撞） | ✅已核 | 保留哨兵并加注释（`R_DADAO_NUM = 14`） | 静态路径全绿；`-shared` 不再触发 "recompile with -fPIC" |
| F3 `getIsRela` 无 `EM_DADAO` ⇒ 动态表落 `SHT_REL` + `getImplicitAddend` 内部错 | ✅已修 | `Driver.cpp` 白名单加 `EM_DADAO`；`-z rel` 显式拒绝 | `run-b.sh` 1 组（`.rela.dyn`/`.rela.plt` 均 `SHT_RELA`）+ 4 组（`-z rel` rc≠0 且含 `SHT_RELA`） |
| F4 缺省 `--hash-style`（非 MIPS = 双发）与缺省 `-z lazy` 与契约（仅 GNU / eager）相悖 | ✅已修 | `Driver.cpp` 对 `EM_DADAO` 分别取 GNU-only / `zNow=true`（显式 `-z lazy` 仍可传，遗留 ⑤） | `run-b.sh` 1 组（无 `--hash-style` 也只得 GNU hash）+ 2 组（eager 位） |
| F5 PLT stub 若用单指令 PC 相对访存（±2 KiB）在默认布局下不可及 | ✅已修（设计） | 入口内嵌 8 B 链接期常量 + `ldm.o`（不经 GP、与 `.plt`/`.got.plt` 距离无关） | `run-b.sh` 1.组 `pltconsistent`（逐入口自洽）+ 3 组（`llvm-mc` 逐字对账） |
| F6 证据脚本首版 4 处误报（`grep 'HASH '` 命中 `GNU_HASH`；`SHT_RELA` 期望写成 `0x4`；「无 `-dynamic-linker`」断言被脚本自带的空 `.interp` 段干扰） | ✅已修 | 改 `awk` 取标签列比对；期望改 `SHT_RELA`；该断言改为「解释器串为空 + `p_filesz=0`」 | `run-b.sh` **103 PASS / 0 FAIL**（修前 4 FAIL） |
| F7 `objdiff.py` 把 NOBITS 段当有载荷比较、且未剥 `.comment` ⇒ 6 条假 FAIL | ✅已修 | NOBITS 只比 `sh_size`；`run-b.sh` 先 `--remove-section=.comment` 再对账 | 修后 6 例 `code/data identical=yes`、`abs48_renumbered=20/21`、`type_mismatch=0` |
| F8 缺「`.rela.*` 之外是否也变」的断言 ⇒ 无法区分「仅编号变化」与真回归 | ✅已修 | 新增 `objdiff.py`（逐段对账 + 类型字段 0↔6 映射校验） | 6 例均 `nonrela_diffs=-`（除 `.comment` 已剥） |
| F9 `--inject` 首版 `dthash` 期望值写错（把标签号当值） | ✅已修 | 期望改 `0x0` | `--inject` **113 PASS / 0 FAIL** |
| F10 并发风险（`ISS-229`）：L2 会自行 `install-host→build-mc` 重建构建树 | ✅已防 | 全程单写者：先 `build-lld`/`build-mc`/`install-host` 串行，再跑证据，最后单独跑 L2（期间无其它写 `.work/build/**`） | 构建日志连续无交叉；安装根/构建树 md5 全同 |

**判决**：F1–F10 **全部 ✅已修**（无 ⏸延后、无 ❌不修）；每条断言/用例均有**可达 FAIL 路径**（`--inject` 8 项现场证明：注入只作用于**副本**，原件 md5 前后对账一致 ⇒ 无需 `git checkout`/`restore`）；无猜测填值、`[OPEN]` 未新增。**自审结论 ⇒ 状态置 `待验收`**（阶段 B 完成；C–E 由后续阶段承接）。

#### 主会话裁定（2026-10-16，阶段 B）

**裁定 1 —— `DADAO.def` 编号同步并入阶段 B**：**接受**。原话要点：「**"阶段 B 被迫含 `DADAO.def` 编号同步" ⇒ 接受**（理由：旧编号下 `ABS48=0` = `R_NONE` ⇒ **任何动态重定位都发不出**（实测 `-shared` 报 `recompile with -fPIC`）⇒ **逻辑必然**；且值**全取自用户已确认的 `ADR-0019 D10`**，无自拟）⇒ ⇒ **阶段 E 范围收窄** 为 `ISS-206` 的**其余部分**（②契约正文**须用户授权**；③既有 ELF 产物·向量排查 ✓ —— **现场核对 E 还剩什么并写明**）」。⇒ 与遗留 ① 闭合（不再构成边界冲突）。

**裁定 2 —— GOT 可及性归属**：**归阶段 C**。原话要点：「**GOT 可及性 = 布局义务**（默认 `.got` 距 `.text` **65592 B** > ±2 KB）⇒ **归阶段 C**（两段式 `ABS48` 序列 + `ldm.o_rrri_rb` 落 `rb`）」。

**裁定 3 —— 阶段 A 证据基线重定**：**授权**。原话要点：「**阶段 A 证据基线重定 = 授权**（`run-a.sh` 现 78 PASS/6 FAIL，6 条为 A7 对象级 md5 **因预期编号同步而过期** 且差异**已证"仅类型字段"**）⇒ **授权**在 `LLVM-094t` 的**后续阶段**（C 或 D）**重定 A7 基线**；**记录**"属预期变化、已证仅类型字段"（**待用户追认**）」。⇒ 遗留 ② 处置已定（**本次不动** `baseline-pre*/`）。

**E 范围收窄后的现场核对结论（architect 现场核，2026-10-16；只读）**：

- **`DADAO.def` 改号 = 已在阶段 B 落地**（`DADAO.def.patch`：`NONE`=0 / 静态 1–5 / `ABS48`=**6** / `JUMP_SLOT`=7 / `RELATIVE`=8 / `COPY`=9 / TLS 10–12 / `TLSDESC`=13 / `NUM`=**14**，与 `ADR-0019 D10` 逐条一致）⇒ **E 无待办**。
- **`lld/ELF/Arch/DADAO.cpp` 头注释同号 = 已随阶段 B 的 `DADAO.cpp.patch` 同步**（现 `R_DADAO_ABS48 (6)`；`grep` 旧串 `ABS48 (0)` 于 `components/llvm-project/patches/` **0 命中**）⇒ **E 无待办**。
- **`ELF.h` 枚举**：`ELF.h.patch` 的 DADAO 枚举体 = `#include "ELFRelocs/DADAO.def"`（另 `EM_DADAO = 0x0DA0`）——**不含写死类型号** ⇒ 随 `DADAO.def` **自动同步**（该 patch 本阶段**未改**即正确）⇒ **E 无独立待办**。
- **`ISS-206③`（既有 ELF 产物·向量排查）= 阶段 B 首次命中 4 处 lit 向量注记**（`dd-symbol`/`m6-callconv`/`rela-addend`/`rela.s`）**已同步**；全仓复核：`tests/vectors/**` **0 命中**、`contracts/**` **0 命中**、`tools/testcases/*` 仅 5 处**类型名**非数字（`R_DADAO_REL26` 报错串 / `@reloc` 正则）⇒ **无写死旧号残留**；旧号仅存 **`.tao/archive/M4|M6/**`（历史层，**不得改**）** + `ADR-0019` D2 正文（`D10` **就地修订注记**已在）。
- ⇒ **E 剩余实际待办 = `ISS-206②`**（`.tao/contracts/contract-elf.md §2.2` 契约正文，现场仍 `| 0 | R_DADAO_ABS48 |` / `NUM=6`）——**须用户授权**；**未授权 ⇒ `ISS-206` 保持 `open`（部分收口）**、完成区已显式声明，**不得**写成已关。

#### architect 提交 / 文件集审核留痕（2026-10-16，阶段 B）

- **开工前现场（核）**：分支 `LLVM-094t-B`；`master` = `da20a09`；`git status --porcelain -uall` = **9 `M` + 2 `??`**（`?? ` = `lld/ELF/Driver.cpp.patch`、`tests/scripts/dadao-dyn.lds`）；`spec/` / `contracts/` / `.tao/contracts/` 越界 = **0**。
- **文件集对账**（逐路径显式 staging、**未用** `git add -A`）：`git diff --cached --name-status` = **11**（9 `M` + 2 `A`），与完成区「修改文件（阶段 B）」逐条对齐（④ `.work/**` 被 `.gitignore` ⇒ 证据不入 git）⇒ **无漏提 / 多提 / 越界**。
- **笔 1** = `36eebcd`（11 文件、+384/−30）。**档位披露**：阶段 B = `待验收`、reviewer 未验收 ⇒ 常规应为 `WIP:` 前缀；**主会话本次明确指令「笔 1 不带 `WIP:`」** ⇒ 从指令执行并在此披露（同阶段 A 先例）。
- **只读核对（真实 rc）**：`make check`（L1）**rc=0**（尾行 `repository checks (L1): PASS`；内含 `check_issues: 39 open, 13 closed`）；`check-patch-tree` **rc=0**（`5 component(s), 146 patches`）；`check-index-blobs` **rc=0**（`108 new-file / 38 modification`）；`check-source-state` **rc=0**（`musl HEAD=d31bf832… clean=True`）；`python3 tools/infra/check_issues.py` **rc=0**（日志 `.work/log/llvm/LLVM-094t-architect-stageB-*.log`）。
- **未** `merge`、**未** `push`（详见主会话回报）。

#### 第 1 轮 reviewer 验收（阶段 B，缩范围重试，2026-10-16）

**重跑记录**（reviewer 自行执行，非采信 engineer 输出）：
- `ET_DYN`：`ld.lld -shared` rc=0；`readelf -h` = `Type: SharedObject (0x3)`，`DataEncoding: BigEndian (0x2)` ✓；`llvm-readobj -d` 有 `DT_SONAME`/`GNU_HASH`/`BIND_NOW`/`PLTGOT`，无 `DT_HASH`/`RELR`/`VERSYM`/`VERNEED`/`VERDEF` ✓；`.rela.dyn` 类型号 = **6**（`readelf -r` 打印 `unrecognized: 6`）、`.rela.plt` 类型号 = **7**（`unrecognized: 7`）✓；两段均 `SHT_RELA` ✓；必备段 10/10 全在 ✓。
- `PT_INTERP`：`-dynamic-linker /lib/ld-musl-dadao.so.1` ⇒ `readelf -l` 打印 `Requesting program interpreter: /lib/ld-musl-dadao.so.1`；`llvm-readobj -x .interp` 逐字节 = `2f6c6962 2f6c642d 6d75736c 2d646164 616f2e73 6f2e3100`（24 B = 23 字符 + `\0`）✓；`DT_NEEDED=libtest.so.1` ✓；不传 `-dynamic-linker` ⇒ `p_filesz=0`，无解释器串 ✓。
- 编号同步：`DADAO.def` 逐行 = `NONE=0/REL26=1/REL20=2/REL14=3/REL12=4/ABS12=5/ABS48=6/JUMP_SLOT=7/RELATIVE=8/COPY=9/TLS_DTPMOD=10/TLS_DTPREL=11/TLS_TPREL=12/TLSDESC=13/NUM=14`，与 `ADR-0019 D10` 逐条一致 ✓；`lld DADAO.cpp` 头注释 `ABS48 (6)` ✓；`git grep` 旧号 `ABS48.*(0)` 在 `tests/vectors|contracts|tools|spec` = **0 命中**；`spec/Toolchain-01:349` 仍写 `NUM=6`（上游只读册，ISS-206② 范围）；`.tao/contracts/contract-elf.md:76/82` 仍旧号（须授权，已知）。
- 门控：`make check`(L1) **rc=0**（`repository checks (L1): PASS`）；`check-patch-tree` **rc=0**（5 component, 146 patches）；`check-index-blobs` **rc=0**（108 new + 38 modification）；`check-source-state` **rc=0**；`check_issues.py` **rc=0**。
- 反例注入：篡改 `run-b.sh` 行 140 期望值 `6→5` ⇒ `102 PASS / 1 FAIL`（`SCRIPT_EXIT=1`）；`cp`+md5 还原（`724e459…` 相等）⇒ `103 PASS / 0 FAIL`（`SCRIPT_EXIT=0`）回绿 ✓。
- `git status --porcelain -uall` = 空（未改任何受审文件；`.work/**` 被 `.gitignore`）。

**判决**：**Accepted** —— 4 项核心全部满足（`ET_DYN`+动态段逐条 ✓、`PT_INTERP` 逐字节 ✓、编号同步逐条+旧号复核 ✓、门控 rc=0+反例 FAIL→还原回绿 ✓）。遗留项（`spec/Toolchain-01` 旧 `NUM=6`、`contract-elf.md §2.2` 旧号、`ISS-206②` 须授权）已如实登记，不阻断阶段 B 验收。

#### architect 阶段级收尾 / 提交 / merge 留痕（2026-10-16，阶段 B）

- **阶段级收尾**（照 `INFRA-082t`/`SPEC-142t`/阶段 A 先例；阶段 B 已 `Accepted`、**C–E 待做** ⇒ 任务级 `**状态**` **保持 `待验收`** ✓，**不置** `已验证`）：L1 `make check` **rc=0**（尾行 `repository checks (L1): PASS`；内含 `check_issues: 39 open, 13 closed`）+ `check-patch-tree`（`5 component(s), 146 patches OK`）/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身** rc；日志 `.work/log/llvm/LLVM-094t-architect-stageBfin-*.log`）；**L2/L3 归任务整体收尾**（阶段 C–E 完成后跑，`ISS-229` ⇒ 串行、不并发）；临时残留 = 无（`check-no-residue` rc=0）；证据在 `.work/evidence/LLVM-094t/`（`run-a.sh`/`run-b.sh`/`elfinfo.py`/`dyncheck.py`/`inject.py`/`objdiff.py`；`.work/**` 被 `.gitignore` ⇒ 不入 git，沿用阶段 A 先例）。
- **文件集对账**（逐路径显式 staging、**未用** `git add -A`）：`git diff --cached --name-status` = **3 `M`**（+16/−4 = `issues.yaml` 1 行 / `milestones.md` 1 行 / 本任务书）⇒ 与交办范围逐条对齐（`ISS-228` **仅追加 notes**、`status` 仍 `open`〔`check_issues.py` rc=0 复核〕；`milestones.md` 仅改 `LLVM-094t` 流水行的「阶段 B 已验证」；本任务书 = `**阶段进度**`×2〔含 `ISS-206②` 现场范围〕+ 本轮留痕）⇒ **无漏提 / 多提 / 越界**（`spec/` / `contracts/` / `.tao/contracts/` 越界 = 0）。档位 = **正常提交**（reviewer 判决 `Accepted`）。
- **笔 1** = `84c4ee5`（阶段级收尾：`阶段进度` + `ISS-206②` 现场范围 + `milestones.md` + `ISS-228` notes 追加）；**笔 2** = 本留痕块（1 文件）。
- **随后（同次收尾）**：`git switch master` → 核干净 → `git merge --ff-only LLVM-094t-B` → `git branch -D LLVM-094t-B`；**不 push** ✗。
- **下一件（队列）**：**阶段 C** —— 两段式 `ABS48` 序列（`immu16` ×3 / `ldm.o_rrri_rb` 落 `rb`）解决 `GOT` 距 `.text` **65592 B** > ±2 KiB 的可及性 + `COPY`/IFUNC **主动拒绝** + A7 基线重定（主会话裁定 2／裁定 3）；**交主会话派发**。

#### 第 3 轮 engineer 自审（阶段 C）

**逐行审查范围**（自主）：2 份补丁逐文件复核 —— `lld/ELF/Arch/DADAO.cpp` 的 `getRelExpr`（IFUNC 检查、保留类型 9/13/10–12 的扫描期报错、`ABS48`/`REL*`/`ABS12` 分派未改）、`lld/ELF/Relocations.cpp` 的副本路径检查（`EM_DADAO` 守卫 + `printLocation` + `return`（不置 `NEEDS_COPY`、不改既有 `-z nocopyreloc` 分支语义））；并核对「判据独立」（`oracle_c.py` 自写 ELF64-BE 解析 + 按 `ADR-0019 D10` 公式核算，`mutate.py` 只改**副本**）、每条断言的**可达 FAIL 路径**（`--inject` 12 项：因果性反例 + oracle 判别 + 原件 md5 对账）、A7 重定的**差异性质**（`objdiff` 独立复核）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `COPY` 检查若放在 `getRelExpr`（`!shared && isShared && isObject`）会**误伤 PIC**：`-pie` 下 GOT 槽的 `ABS48`（可写段）本应走**动态重定位**而非副本 ⇒ 会阻断合法 PIE 链接 | ✅已修 | 把检查移到 lld **真正决定副本之处**（`Relocations.cpp` 的 `NEEDS_COPY` 分支，`EM_DADAO` 守卫） | `run-c.sh` 2b：同场景 **PIC 版本 rc=0** 且 `.rela.dyn` 含 type 6（`gv`）；`run-b.sh` 的 `-pie` 用例 rc=0 |
| F2 保留类型（9/13/10–12）若只靠 `relocate` 兜底，扫描期 `getRelExpr` 的 `default` 会先报通用 `unknown relocation(N)` ⇒ 信息量低 | ✅已修 | `getRelExpr` 增 `COPY`/`TLSDESC`/TLS 分支，报**类型专有**文案（与 `relocate` 一致，双保险） | `run-c.sh` 2d：注入 9/13/10/11/12 逐条 rc=1 + 类型专有文案（5×2 断言） |
| F3 第一轮 `run-c.sh` 里 `abs12.s` 用 C 风格注释、`call res, rd0, 0` 语法错、`use.o` 未生成 ⇒ `2c.IFUNC` 断言**假绿**（rc≠0 实为「文件缺失」） | ✅已修 | 注释改 `;`、`call [rb0, res]`（照 `tests/llvm/lit/MC/DADAO/rela-addend.s`）、并把「前提」拆成独立断言 | `run-c.sh` 0.*/2c：`llvm-mc` rc=0、`R_DADAO_ABS12 gv` 前提成立；`--inject` 的 IFUNC 因果性反例（改回 `FUNC` ⇒ rc=0） |
| F4 A7 重定若把 `baseline-pre/*.o`（对象本体）一并换成新对象 ⇒ `run-b.sh` 的 4.static（以它为「重编号前」参照）**假 FAIL** | ✅已修 | 只重定 **md5 清单**（`baseline-pre-nocomment.md5`/`-raw.md5`）；`baseline-pre/*.o` 的**对象**恢复为阶段 A 原件（`cp` 还原 + md5 对账，未用 `git checkout`） | `run-b.sh` rc=0（4.static 6 例 `code_identical=yes` + `abs48_renumbered=20/20`·`21/21`）；`run-a.sh` rc=0 |
| F5 `--apply-dynamic-relocs` 在 DADAO 上不可用（`cannot read addend`）⇒ 原计划的「槽落地值」断言会把 oracle 变成恒 FAIL | ✅已修 | 去掉该口径：槽的**落地值**改由静态 `S + A` 字段（`--defsym`，48 位 / 大端 / 高 16 位 0）核；运行期槽内容按 ELF 语义由装载器填 | `run-c.sh` 4.ABS48 `S+A resolved` = `0000abcd12345678`；`oracle_c.py` 8/8 |
| F6 **两段式（本阶段核心 ①）未实现** | ⏸延后 | 未改代码；在完成区 + 本表 + 「遗留 ①」给出**现场证据**与三条候选方案（含各自须授权的点） | `run-c.sh` NOTE + 完成区 ①/② 披露；`.work/log/llvm/LLVM-094t-C-run-c.log` |

**判决**：F1–F5 **全部 ✅已修**（每条有可达 FAIL 路径与独立复验）；**F6 ⏸延后 = 阶段 C 的「核心 ①」未交付**（须用户/主会话在三条候选方案中裁定；本阶段**未擅自**改阶段 A 已验收的 PIC 对象形态与断言，也未引入保留寄存器/可执行数据段/TEXTREL 等新约定）；无猜测填值、`[OPEN]` 未新增。**自审结论 ⇒ 阶段 C 的交付面（②③ + A7 重定 + 证据/门控）可验收，① 待裁定 ⇒ 任务**状态**按规则保持 `待验收`（阶段级；见完成区 ①/② 披露），不置 `已验证`。**

#### architect 阶段级收尾 / 提交 / 阻塞登记留痕（2026-10-16，阶段 C）

- **阶段级收尾**（照 `INFRA-082t`/`SPEC-142t`/阶段 A·B 先例；阶段 C = **部分交付**〔②③ + 证据/门控〕、**核心 ① 未交付** ⇒ 任务级 `**状态**` **保持 `待验收`** ✓、**不置** `已验证`）：`make check`（**L1**）**rc=0**（尾行 `repository checks (L1): PASS`；内含 `check_issues: 40 open, 13 closed`）+ `check-patch-tree` **rc=0**（`5 component(s), 147 patches OK`；`series` = **73** 行）/ `check-index-blobs` **rc=0**（`108 new-file / 39 modification`）/ `check-source-state` **rc=0**（`musl: OK HEAD=d31bf832260d clean=True`）/ `python3 tools/infra/check_issues.py` **rc=0**（各留**自身** rc；日志 `.work/log/llvm/LLVM-094t-architect-stageC-*.log`）；**L2/L3 归任务整体收尾**（阶段 D/E 完成后跑；`ISS-229` ⇒ 串行、不并发 ⇒ 本阶段**未跑** L2/L3）。
- **文件集对账**（逐路径显式 staging、**未用** `git add -A`）：开工前 `git status --porcelain -uall` = **4 `M` + 1 `??`**（`??` = `patches/lld/ELF/Relocations.cpp.patch`）、**范围外**（`spec/` / `contracts/` / `.tao/contracts/`）= **0**；`git diff --cached --name-status` = **5**（4 `M` + 1 `A`），与完成区「修改文件（阶段 C）」逐条对齐（③ `.work/**` 被 `.gitignore` ⇒ 证据不入 git）⇒ **无漏提 / 多提 / 越界**。
- **分支现场**：交办称「分支 `LLVM-094t-C`（在 `1afa66b`）」，但现场 `git branch --show-current` = **`master`**（`.git/HEAD` = `ref: refs/heads/master`；`LLVM-094t-C` = `1afa66b` = `master` = `origin/master`、无提交）⇒ **未用** `git switch`/`checkout`/`restore`，以 `git symbolic-ref HEAD refs/heads/LLVM-094t-C` 移 HEAD（**工作树 / 索引零改动**：`git status --porcelain -uall` 仍 4 `M` + 1 `??`）⇒ 两笔提交落 `LLVM-094t-C`、`master` 未动（同阶段 A 先例）。
- **笔 1** = `36ea1a0`（5 文件、+96/−3）；**笔 2** = 本留痕块（`阶段进度`×2 + 本阻塞登记 + `ISS-230` + `milestones.md` 流水行）。**档位披露**：阶段 C = `待验收`、reviewer 未验收 ⇒ 常规应为 `WIP:` 前缀；**主会话本次明确指令「笔 1 不带 `WIP:`」** ⇒ 从指令执行并在此披露（同阶段 A/B 先例）。
- **① 两段式 `ABS48` 前置不可满足（技术裁定项，须用户定）** ✗：`ADR-0026 D5` 的「超 ±2 KiB 两段式」（`ABS48` 序列 + `ldm.o_rrri_rb`）需「**链接器可用的临时 `rd`**」承载偏移 —— 现场核（`spec/DADAO-21-ABI:18-20`/`:402`）：**`rd0` = 零（immutable）／`rd1` = `rderrno`〔ABI 定义〕／`rd2–rd3` = 「调试/测试保留，编译器不得分配」／`rd4+` 归编译器** ⇒ **无可用**（且 `ldm.o {rbX}, [rbH, rdC]` 的偏移域**只能是 `rd`**；`ld.o` 只有 `imms12` 立即数形式）。ISA 侧**唯一**宽范围 PC 相对通道（`REL26` 字偏移／`add.si` 的 `imms18`）**无匹配重定位类型**（`REL14/20/26` 为字偏移、`REL12`/`ABS12` 仅 `imms12`）⇒ 默认布局 `-shared` 链接期报 **`R_DADAO_REL12 out of range`**（`-z max-page-size`／`noseparate-code` **无改善**）。**三候选（须用户裁定）**：**(a)** 编译器发射两段式（须改阶段 A 已验收的 `P1`/`P3` 断言）；**(b)** 让出链接器临时寄存器 **或** 新增宽相对重定位类型（**触及 ISA/ABI ⇒ 须 `ADR` + `spec/` 授权** ✗）；**(c)** 接受布局约束（`.got` 保持在 ±2 KiB 内、由构建脚本/链接脚本负责；**不新增 ISA** ✓）。
- **主会话初步分析（原样登记）**：契约「**不固定 GOT 基址**」（`ADR-0026 D5`）+「**±2 KiB 相对 + 超范围用 `ABS48` 序列**」⇒ 后者**需要链接器可用寄存器** ⇒ **契约与可用通道不闭合**（对照：RISC-V 靠 **`gp` 固定基址 + ±2 KiB** 才成立，而本契约**禁止**固定基址/专用寄存器）⇒ 属**技术裁定项**、**待用户裁定**（**不擅自选** ✗）⇒ 已登记 `ISS-230`。
- **architect 独立复现（只读，2026-10-16；`/tmp/opencode/LLVM-094t-C-arch`）**：`clang -target dadao-unknown-elf -fPIC -c`（`gv.c`：DSO 数据符号取址）**rc=0**；`ld.lld -shared` **rc=1** ⇒ `R_DADAO_REL12 out of range: **65552**`、`-z max-page-size=0x1000` ⇒ **4112**、`-z noseparate-code` ⇒ **65552**（阶段 C 证据脚本记录值 = **65596**／**4156**，随源/布局而变、量级一致）⇒ **任何分段布局**下单指令 GOT 访问均不可达（与「新发现 ①②」一致）。
- **未** `merge`、**未** `push` ✗（`LLVM-094t-C` 仅本地分支）；收尾后 `git status --porcelain -uall` = **干净**（笔 2 落地后）。
- **下一件（队列）**：① 待**用户裁定**（三候选）⇒ 裁定后阶段 D（与契约逐条对齐）/ 阶段 E（`ISS-206②` **须授权**）收尾；本册 `merge --squash` 由主会话在 `/complete` 后执行（阶段 C 未整体验收 ⇒ **不**预先 merge）。

#### 第 1 轮 reviewer 验收（阶段 C 部分：②③，2026-10-16）

**重跑记录**（reviewer 自行执行，非采信 engineer）：
- `run-c.sh` **43 PASS / 1 FAIL、rc=1**（自报 44/0 rc=0）；`--inject` **55 PASS / 1 FAIL、rc=1**（自报 56/0）——唯一 FAIL = `6.run-a.sh rc`：`run-a.sh` 自 `A1.compile` 起 61 项连锁 FAIL，根因 `clang: error: no such file or directory: '/tmp/opencode/LLVM-094t/src/t.c'`（见 F1）。
- `make check`(L1) **rc=0**；`check-patch-tree` **rc=0**（5 component / **147 patches**、`series`=**73**）/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check_issues.py`/`check-component-changelog` 各 **rc=0**（**未跑** L2/L3）。

**独立验证**（自造场景 + 自写 ELF64-BE 解析，不复用其脚本）：
- ② **COPY**：非 PIC exe（`ABS12`→DSO 数据符号 `gv`）⇒ rc=1 + `cannot create a copy relocation for symbol 'gv' … recompile with -fPIC`；**同场景 `-fPIC`** ⇒ rc=0 且 `.rela.dyn` 有 type 6 `gv` ⇒ 拒绝键在「需副本」✓；**IFUNC**（自改 `st_info`=10）⇒ rc=1 + `GNU IFUNC symbol 'res' is not supported (no .iplt/IRELATIVE)`，FUNC 对照 rc=0 ✓；类型注入 9/13/10/11/12 逐条 rc=1 + 类型专有文案（`R_DADAO_COPY|TLSDESC is not emitted`、`TLS … DTPMOD|DTPREL|TPREL is not supported yet`）、type 6 对照 rc=0 ⇒ 报错**显式**（含类型名/符号名）、**非静默** ✓。
- ③ **差异仅类型字段**（3 例自比，`baseline-pre/` 阶段 A 原件 vs 现产物）：`.text`/`.data` **逐字节同**（t.O0 292/24 B、t.O1 260/24 B、sw.O1 316/16 B）；重定位 offset/sym/addend 全同、**仅类型 0→6**（18+2 / 18+2 / 12 条）✓；新清单 `baseline-pre-nocomment.md5` 与现产物 md5 逐条吻合、`baseline-pre/`≡`baseline-pre-preC/`（对象留档为阶段 A 原件）✓；**授权来源**任务书写明「主会话 2026-10-16 裁定 3」（原文含「待用户追认」）✓；`run-a.sh` 84/0 **无法复现**（F1）。
- **oracle 独立性 ✓**（自写 `struct` 解析、不经 LLVM 读取器；期望值取 gABI/`ADR-0019 D10`/对象输入 symtab ⇒ 独立于被测实现）；我方按公式重算 **3 例**：`ABS48`=`S+A`（`--defsym ext=0xABCD12345678` ⇒ `.data`=`0000abcd12345678`、高 16 位 0）✓；`RELATIVE`=`B+A`（自造 `static sv` 取址 ⇒ type 8、A=0x150 == `sv.st_value`）✓；`JUMP_SLOT` type 7 / A=0 / 符号 `ext_fn` ✓。
- **我方新反例**（不在其 12 项内；改 `oracle_c.py` 期望值、**非编译输入**）：`O1 expect 2→1` ⇒ **7 PASS/1 FAIL、rc=1** → `cp`+md5 还原（`ac3fa2…` 相等）⇒ **8/0、rc=0** 回绿 ✓；审前/审后 `git status --porcelain -uall`=**0**、5 份证据 md5 与快照一致、`check-no-residue` 复跑 rc=0（快照对账通过）。
- **如实性 ✓**：`**状态**`=`待验收`、阶段进度写「C ⚠️ 部分交付（待验收）」、**无**「已验证」；`ISS-230`（open，三候选 a/b/c + 根因 + 错误文案）与阻塞块**一致** ✓。**越界 0** ✓（`git diff 1afa66b..HEAD --name-only` = 任务书/`changelog`/2 补丁/`series`/`issues.yaml`/`milestones.md`；`spec/`/`contracts/`/`.tao/contracts/` = 0；后两笔 = `ISS-230` 登记 + 流水行〔登记类，披露〕）。① 两段式**不在本次范围**、未判（`run-c.sh` §5 的 `REL12 out of range` 65596/4156 B 仅作现场记录）。

**发现（一次性列全）**：
- **F1（阻断）** `run-a.sh` **不自包含**：依赖 `/tmp/opencode/LLVM-094t/src/{t.c,sw.c,two.c}`，**无任何脚本生成**、现已不存在 ⇒ 干净状态下 `run-c.sh` §6 与 `--inject` 必 FAIL，完成区「44/0、56/0、`run-a.sh` rc=0」不可复现。**修**：src 生成内联进 `run-a.sh`（heredoc，照 `run-b.sh` 先例）或随证据留存 `src/` 且缺失时 fail-fast；修后重跑三脚本留真实输出。
- **F2** 完成区「独立 oracle」写「type 8（`sv` 的 RELATIVE 槽）…`B+A`」与真实输出不符：`libtest.so` `.rela.dyn` 仅 **1** 条 type 6、**无** type 8 ⇒ `oracle_c.py` 的 O6 分支**空转**（8/8 中无 O6 行）。**修**：换含 RELATIVE 槽的场景（如 `static` 取址）或把描述改为「代码具备、本场景未覆盖」。
- **F3（非阻断）** `milestones.md` 流水行「[`ISS-230` 三候选」括号未闭合（笔误）。

**判决**：**Needs Revision** —— F1（验收命令块在干净状态不可复现：`run-c.sh` 43/1 rc=1、`--inject` 55/1 rc=1、`run-a.sh` rc=1）+ F2（完成区与真实输出不符）；②③ 功能面、A7 重定差异性质、oracle 独立性、门控 8 项、注入还原纪律均经独立验证通过 ⇒ 修 F1/F2 后重审（F3 顺手）。

#### 第 4 轮 engineer 返工（阶段 C：F1/F2/F3）

**范围**：处置第 3 轮 reviewer 的 `Needs Revision`（F1 阻断 / F2 阻断 / F3 非阻断）；**只改证据脚本 + 文档**，**未重建**（无编译输入变化；`ISS-229` ⇒ 不并发 `install-host`/`build-*`/L2/L3）。

| finding | 处置 | 改了什么 | 复验证据（当次真实输出） |
|---|---|---|---|
| **F1（阻断）** `run-a.sh` 不自包含：依赖 `/tmp/opencode/LLVM-094t/src/{t.c,sw.c,two.c}`（无脚本生成、已被清空）⇒ 干净状态 rc=1 | ✅已修 | `run-a.sh`：`SRC=$WORK/src`（脚本自建）+ 三个探针源**内联为 heredoc**（`t.c`/`sw.c` 与 `run-b.sh` 逐字同源；`two.c` = 同模块两个 dense switch ⇒ 两块跳表）+ 新增 `S0.source-materialised[*.c]` 断言（**须非空**，否则 `FAIL-FAST` + `exit 1`，**不静默跳过**） | **先整体清空 `/tmp/opencode/LLVM-094t/ev`**：`run-a.sh` **87 PASS / 0 FAIL / rc=0**、其 `--inject` **97 PASS / 0 FAIL / rc=0**；`run-c.sh` **48 PASS / 0 FAIL / rc=0**（返工前 reviewer 实测 **43/1** ⇒ 唯一 FAIL `6.run-a.sh rc` 消失）、`--inject` **60 PASS / 0 FAIL / rc=0**（返工前 **55/1**）；`run-b.sh` **103 PASS / 0 FAIL / rc=0**；`A7` 6/6 md5 逐条吻合（`t.O0/O1/O2`=`cdb0bcde…/beda13fc…/beda13fc…`、`sw.O0/O1/O2`=`cfb8b3a2…/513f7747…/513f7747…`）⇒ 内联 `t.c`/`sw.c` 与基线**同源**；`A6b.distinct-jt-slots`=**2** |
| **F2（阻断）** 完成区「独立 oracle」称覆盖 `RELATIVE`，但交付场景 `.rela.dyn` 仅 1 条 type 6 ⇒ `O6` 分支**空转** | ✅已修（**换场景**，非改述） | `run-c.sh` 的 `lib.c` 增 `int *psv = &sv;`（局部数据指针 ⇒ `.data` 内静态取址 ⇒ `RELATIVE`），`pub_a` 用 `*psv`；`2e` 断言改 `{6,8}` + 新增「`RELATIVE`(8) 真的在」；§3 新增**非空转**断言（oracle 的 `O5`/`O6` 行都须 ≥1）；§5 的 NOTE 取**首条**越界引用（原多符号时打印多条）；完成区 oracle 段 + ①/② 越界数值按真值改写 | `readelf -r libtest.so`（binutils，第三方面）：`.rela.dyn` **4 条** = `type 8`×2（addend `0x2f4`）+ `type 6`×2（`gv`/`psv`）、`.rela.plt` `type 7`（`ext_fn`）；`oracle_c.py` **20/20 rc=0**（`O6`×2：`r_addend` = 已定义符号 `sv` 的 `st_value` = `0x2F4`）；`run-c.sh`：`NOTE | 3.oracle rows: ABS48(O5)=2 RELATIVE(O6)=2`、`2e.DSO .rela.dyn type set = {ABS48(6),RELATIVE(8)}` = PASS |
| **F3（非阻断）** `milestones.md` `LLVM-094t` 行的「[`ISS-230` 三候选」括号未闭合 | ✅已修 | 删多余 `[`（同会话内一处误改已**即时回退**；该行最终 diff = **1 行**）+ 同行 C 段计数同步（44/0、56/0 ⇒ 48/0、60/0 + `RELATIVE` 覆盖） | `git diff --stat .tao/knowledge/milestones.md` = `1 insertion(+), 1 deletion(-)`；该处现为「；`ISS-230` 三候选）；」 |

**判决**：F1/F2/F3 **全部 ✅已修**（无 ⏸/❌）；**可达 FAIL 路径**均已现场证明——F1：把 `S0` 检查前的 `sw.c` 删除 ⇒ `FAIL | S0.source-materialised[sw.c]` + `FAIL-FAST` + `RESULT: FAIL`（`rc=1`，于临时副本 `/tmp/opencode/LLVM-094t/f1-inject/` 运行，**未动**证据脚本）；F2：`O6` 计数断言在「无 8 的场景」下必 FAIL（旧场景旧值 43/1 即为反例来源）；无猜测填值、`[OPEN]` 未新增。⇒ 阶段 C 的**证据可复现性**与**完成区↔真实输出**已对齐；**① 两段式仍待用户裁定**（`ISS-230`，本轮**未动**）⇒ `**状态**` 保持 `待验收`、阶段进度措辞保持「C ⚠️ 部分交付（待验收）」。

**第 4 轮 engineer 自审**（自主逐行审查：`run-a.sh` 的 S0 块 + A6b/A7 路径、`run-c.sh` 的 §2b/2e/§3/§5 与内联 `lib.c`）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1-a `SRC=$WORK/src` 的求值顺序（须在 `WORK` 定义之后、`mkdir -p $WORK` 之后使用） | ✅已核 | 无需改（`WORK` 定义在前、S0 块在 `mkdir -p "$WORK"` 之后） | `run-a.sh` rc=0 全绿；`$SRC` 下 3 源现场存在 |
| F1-b 内联源若与原源不同源 ⇒ `A7` 基线**假 FAIL** | ✅已核 | 无需改 | `A7` 6/6 md5 与 `baseline-pre-nocomment.md5` **逐条相等**（`t`/`sw` × O0–O2） |
| F1-c `two.c` 为**重写**（原件随 `/tmp` 清空、未随证据留存） | ⚠️披露 | 重写为「同模块两个 dense switch」；A6b 判据 = 「≥2 个**不同** `.LJTI` 槽」→ **不依赖**旧对象基线 | `A6b.distinct-jt-slots`=2；`.rela.got` = `.LJTI0_0`/`gv`/`.LJTI1_0`/`ext`（4 槽 = `got size/8` ⇒ `pic_check` 全绿） |
| F1-d S0 断言的**可达 FAIL 路径**须真能失败 | ✅已核 | 不在证据脚本内自注入（避免自我破坏）；用**临时副本**（`/tmp/opencode/LLVM-094t/f1-inject/`，`cp` 出）删 `sw.c` 演示 | `FAIL | S0.source-materialised[sw.c]` + `FAIL-FAST` + `RESULT: FAIL`，`rc=1`（证据脚本本身**未改**） |
| F2-a §3 `chk` 前的 `$?` 是否仍指 oracle 的 rc（stdout 改落盘后） | ✅已核 | 无需改（重定向属同一简单命令） | `3.oracle_c(.rela.dyn) rc` expect=0 actual=0 |
| F2-b `grep -c` 无匹配时 rc=1 会不会中断脚本（`set -u`、无 `set -e`） | ✅已核 | 无需改（计数仅喂给 `chk_yes`，**可** FAIL） | `3.oracle exercised RELATIVE rows` 现 PASS；旧场景下必为 `no` ⇒ FAIL |
| F2-c `psv` 进入 DSO 是否扰动**其它**断言 | ✅已核 | 无需改 | 全量重跑 48/0：`2b` 仍仅 `6`、`2d`/`2e`/`4`/`5` 全 PASS |
| F2-d §5 NOTE 多符号越界时打印多行（数值歧义） | ✅已修 | 两处 `sed` 加 `| head -1`（取首条越界引用） | `5.two-stage … 65620 B` / `5.4KiB … 4180 B`（各一行）；完成区 ①/② 数值同步改写 |
| 流程 误改 `milestones.md` 一处（把 `无宽相对重定位类型` 误替换为含 `relocation-model` 的串） | ✅已修（**当场回退**） | 立即回改原文案 | `git diff --stat .tao/knowledge/milestones.md` = `1 insertion(+), 1 deletion(-)`（仅目标行） |
| 门控 `make check-issues` 不是 target（`No rule to make target`，rc=2） | ⚠️披露（非阻断） | 不改 Makefile（越界） | 正确门控 = `python3 tools/infra/check_issues.py` **rc=0**（`40 open, 13 closed`）；`make check`（L1）内部已含该脚本且 rc=0 |

**判决**：F1/F2/F3 全部 ✅已修、自审 finding 全部 ✅已核/已修（`two.c` 重写与 `make check-issues` 无 target 两项 **⚠️披露**、非阻断）；每条断言有可达 FAIL 路径；无猜测填值、`[OPEN]` 未新增 ⇒ 状态保持 `待验收`（阶段级；**① 两段式仍待用户裁定**）。

#### 第 2 轮 reviewer 验收（阶段 C 返工复验：F1/F2/F3，2026-10-16）

**范围**：只判 F1/F2/F3 是否真修好；① 两段式 `ABS48` **不在范围**（用户已明示待其给解法）⇒ 不判、不选候选。**未跑** L2/L3/`install-host`/`build-*`（`ISS-229`）；全程前台。

**重跑记录**（先 `rm -rf /tmp/opencode/LLVM-094t` 断 `/tmp` 依赖；rc = 命令自身退出码）：
- `run-a.sh` **87 PASS/0 FAIL rc=0**；`run-a.sh --inject` **97/0 rc=0**；`run-c.sh` **48/0 rc=0**（`3.oracle rows: ABS48(O5)=2 RELATIVE(O6)=2`、NOTE **65620/4180 B**、§6 内 `run-b.sh` **103/0**）；`run-c.sh --inject` **60/0 rc=0**（INJ 12 项含原件 md5 对账）⇒ 与自报 87/0·97/0·48/0·60/0·103/0 **逐项相符**（返工前 43/1·55/1 已消失）。
- **F1 独立注入**（临时副本 `/tmp/opencode/LLVM-094t-review/f1-inject/` 删内联生成的 `sw.c`）⇒ `FAIL | S0.source-materialised[sw.c] | …missing/empty` + `FAIL-FAST` + `RESULT: FAIL`、**rc=1** ✓；原件 md5 `8a794ced…` 注入前后相等、`cp` 还原对账相等 ⇒ 重跑 `run-a.sh` 回绿 **87/0 rc=0** ✓。
- **F2 独立实读**（GNU `readelf -r/-s` 第三方面）：`libtest.so` `.rela.dyn` **4 条** = `type 8`×2（addend `2f4`）+ `type 6`×2（`gv`/`psv` +0）、`.rela.plt` **type 7**（`ext_fn`）；`sv`（LOCAL）`st_value=0x2f4` ⇒ **type 8 addend 与 `st_value` 我方复核相符**（`B+A`）✓；`oracle_c.py` 直跑 **20/20 rc=0**（`O5`×2+`O6`×2 真执行、非空转）✓。
- **F2 非空转断言注入**（临时树改场景去掉全部 `RELATIVE`）⇒ `3.oracle exercised RELATIVE rows (non-vacuous)` **FAIL**（`O6=0`）+ `2e`×2 FAIL、**rc=1** ✓；原件 md5 `65c024e7…` 不变、临时副本已删 ⇒ 重跑 `run-c.sh` 回绿 **48/0 rc=0** ✓。
- **F3**：`git diff --stat .tao/knowledge/milestones.md` = **1 insertion(+), 1 deletion(-)**；「[`ISS-230` 三候选」括号笔误已除 + C 段计数同步 ✓。

**门控**（各留自身 rc）：`make check`(L1) **rc=0**；`check-patch-tree`（**5 component / 147 patches**）/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-component-changelog`/`python3 tools/infra/check_issues.py`（40 open/13 closed）各 **rc=0**；`make check-issues` **rc=2 = 非 target**（`No rule to make target`）——我自核属实，其披露口径正确（正解 = `check_issues.py`）✓（未跑 L2/L3 ✗）。

**约束核验**：如实性 ✓（第 4 轮块 **28 行** ≤40；`**状态**`=`待验收`；C 段措辞无「已验证」〔A/B 系既往 Accepted 既成事实〕；完成区 87/0·97/0·48/0·60/0·103/0·20/20·O5=2/O6=2·65620/4180·A7 6 条 md5 与我方真实输出一致；`ISS-230` open+三候选 = 「待用户解法」口径一致）；不越界 ✓（`git diff 1afa66b..HEAD --name-only` = issues.yaml/milestones/任务书/changelog/2 补丁/series 共 **7**；工作树 2 `M`；`spec/`/`contracts/`/`.tao/contracts/` = **0**）；快照对账 ✓（9 份证据 md5 审前审后 `md5sum -c` 全 OK、注入均在副本、未用 `git checkout/restore/stash`）；`run-a`/`run-b` 内联 `t.c`/`sw.c` 逐字同源（`diff` 空）+ A7 基线 6 条 md5 相符 ⇒ F1 自包含非「换源凑绿」。

**判决**：**Accepted** —— F1/F2/F3 全部真修好（自包含 + 可达 FAIL 独立注入证明、`RELATIVE` 覆盖为真且非空转断言可失败、笔误已除），验收命令块在独立重跑下全绿、约束无违反。① 两段式 `ABS48` **不在本轮范围**（`ISS-230` open、待用户解法），未判、未选候选。

#### architect 阶段 E 落纸 / 收口 `ISS-206②`（2026-10-16；**只追加**）

**范围**：`ISS-206②`（旧重定位编号残留）= **只碰两处** —— `spec/Toolchain-01-汇编语言.md`（旧号）+ `.tao/contracts/contract-elf.md §2.2`（旧号）；**未**重建、**未**跑 `install-host`/`build-*`/L2/L3（`ISS-229`；本次无编译输入变化）。

**本阶段改动文件（**5 个**，即文件集对账基线）**：① `spec/Toolchain-01-汇编语言.md`（1 行）、② `manifests/spec-readonly.lock.toml`（该册 `sha256` + 注释）、③ `.tao/contracts/contract-elf.md`（§2.2）、④ `.tao/knowledge/issues.yaml`（`ISS-206` notes 追加）、⑤ 本任务书（阶段进度 ×2 + 本记录）；均在派单范围内，**无越界**。

**用户授权（原话，逐字落纸；`docs/Process-06 §2`）**：**渠道 = 经主会话问答（2026-10-16）**；主会话提问「授权改 `spec/Toolchain-01` 一处旧编号」，**用户答**：「**授权，但建议删除 `NUM = 6`**」⇒ **授权成立**（命中 `spec/` 授权范围）+ 用户**具体建议 = 删掉该字面量**（⇒ **不**写 `14`、**不**写任何自推数字）。

**改动 1 —— `spec/Toolchain-01-汇编语言.md`（文末「附录：版本与变更记录」0.3.2 段；逐字前后）**：
- 改前：「`` - 重定位正文（`REL12` = rb0 PC 相对 S+A−P、`ABS12` = rb1–rb63 S+A、`NUM` = 6）；`ABS48` 数据按 8 字节；§6.1 `set.fo` 口径。 ``」
- 改后：「`` - 重定位正文（`REL12` = rb0 PC 相对 S+A−P、`ABS12` = rb1–rb63 S+A）；`ABS48` 数据按 8 字节；§6.1 `set.fo` 口径。 ``」
- **为何这样改（依据 = `ADR-0019 D10`）**：`D10`（`Accepted`，用户 2026-10-14 逐条确认）之（a）表把编号冻结为 `0=NONE` / 静态 `1`–`5` / **`6=ABS48`** / 动态 `7`–`13` / **`14=NUM`**；`D2` 时代的 `NUM` = 6 属**旧号残留**（`ADR-0019` 明示「**不改写 `D1`/`D2` 历史文字**，修订以 `D10` 就地修订注记承载」）。
- **句删后仍成立**（该句只列重定位正文的公式项）⇒ **不用指针式措辞**：现场核准 `tools/spec/check_spec_changelog.py` 断言 6（`L178`）**明令附录段内不得出现 `ADR-` 号** ⇒ 「编号见 `ADR-0019 D10`」在**本段内会被门控判红**。
- **规模**：`git diff --stat` = **1 行改（+1/−1）**；规范正文（§1–§14）**未改**、册版本**不变**。
- **变更记录段是否补**：**不补**（依该册 + `spec/README.md` 册维护惯例）——① 条例「**"加记录"动作本身不引发 `-rc`**」，而本改动**就是**文末附录**记录本身的订正**（非规范正文改动；同 `SPEC-134t` 返工「补条目不加 `-rc`」先例）；② 若补 `-rc` 须**同时**改册头版本行（门控断言 4「册头一致」）⇒ 属**版本 / 发布动作**，**超出本次授权**（派单亦明令「不擅自发布版本」）。⇒ 改动记录落 **`manifests/spec-readonly.lock.toml` 该册注释**（该文件既有惯例 = 按册记「日期 / 任务 / 授权 / 改了什么」）+ 本记录。
- **锁同步（`Process-06 §5`，同一变更内）**：`spec/Toolchain-01` 册 `sha256` `cd90beed…` → **`bad4bc10…`**；锁注释补 2026-10-16 一行（含授权原话）。

**改动 2 —— `.tao/contracts/contract-elf.md §2.2`**（**`spec/` 之外** ⇒ 不涉 spec 授权；内容 = `ADR-0019 D10` **已 `Accepted` 决策的既定同步**，**不引入新决策**）：
- 改前 = `D2` 旧号 **7 行**表（`0=ABS48` / `1`–`5` 静态 / `6=NUM`）；改后 = `D10` 终表 **15 行**（`0=NONE` / `1`–`5` 静态**不变** / **`6=ABS48`** / `7`–`13` 动态·TLS / **`14=NUM`（冻结值 = 14）**）+「`D10` 就地修订 `D2`」注记 + `[ADR-0019 §D10]` 来源标注 + 动态类型正文指针（`contract-dynlink.md §4.3–§4.4`）。
- **逐条机械核**（非目测）：脚本现场解析 `ADR-0019 D10`（a）表 vs 本表 ⇒ **15/15 逐条一致 ✓、编号连续 `0..14` ✓、两表条数相等 ✓**。
- **未动（披露）**：册头「来源」行仍述「`§2–§4` 由 `ADR-0019`…`D1–D8`」（未含 `D10`）——在 **§2.2 之外**，派单限「只碰 §2.2」⇒ 未动（可后续按册头惯例补 `rev.`）。

**引用排查（`git grep`，逐条）**：① 该 spec 句 / 该编号：`spec/` 内 **0**（除本行自身）；全仓仅 **`.tao/archive/M4|M6/**`（历史层，不得改）** + `ADR-0019` `D2` 历史正文（不得改）+ 台账之**旧状态描述**（本次同步：`ISS-206` notes、本册阶段进度）⇒ **无他处需同步**。② `contract-elf.md §2.2` 的引用处（**多为「见 §2.2」指针、不含号值**）：`tests/llvm/lit/MC/DADAO/{README-m4.md,m4-directive-dd.s,m6-callconv.s,m6-ldst-symbol.s,rela.s,rela-addend.s}`、`tests/llvm/codegen/m6/{README.md,expected-elf.yaml}`、`docs/Process-02`、`Makefile`、`.tao/contracts/contract-dynlink.md §4.3–§4.4`（其「`1`–`5` = 静态、正文归 `contract-elf §2.2`」表述与改后**一致 ✓**）⇒ **无需同步**（`tests/`·`contracts/` 内旧**数字**已于阶段 B 同步；现场复核 `tools/testcases/*` 只有**类型名**、无号值）。
- **⚠️ 异常披露（未改；超出本派单范围）**：`SPEC-139t` 的**任务级证据脚本** `.work/evidence/SPEC-139t/run.sh` 以「**旧号未同步**」为**预期**写死 3 条断言（`C4.contract-elf-expected-stale-ABS48`=0、`…-stale-NUM`=6、`C4.ISS-206-open`=open；`L187`–`L189`），且其引用的 `.tao/knowledge/contract-elf.md` 路径已随 `INFRA-071t` 迁移失效 ⇒ 本次改动后**前两条**失效（`.work/**` 被 `.gitignore` ⇒ **不入 git**、**非门控**、不影响 L1/L2）；**未**擅改他任务已验收证据（同「不擅改已验收基线」口径）⇒ **提请主会话裁定**（改断言 / 标注失效）。

**门控（真实 rc；`ISS-229` ⇒ 未跑 `install-host`/`build-*`/L2/L3）**：`make check`（**L1**）**rc=0**（尾行 `repository checks (L1): PASS`；内含 `check_issues: 40 open, 13 closed`，本次直接相关项 `check-spec-readonly`/`check-spec-changelog`/`check-spec-numbering`/`check-contracts-dir` 均 PASS）；`check-patch-tree` **rc=0**（`5 component(s), **147** patches OK`）/ `check-index-blobs` **rc=0**（108 new-file / 39 modification）/ `check-source-state` **rc=0**（`musl: OK HEAD=d31bf832260d clean=True`）/ `check-no-residue` **rc=0** / `check-tasks` **rc=0** / `check-component-changelog` **rc=0** / `python3 tools/infra/check_issues.py` **rc=0**（40 open / 13 closed；`resolved_by` 约束 OK）——各留**自身** rc，日志 `.work/log/llvm/LLVM-094t-E-architect-*.log`。

**`ISS-206` 处置**：**只收口②**（①〔`DADAO.def` 改号〕/③〔产物·向量排查〕**状态不变** = 已随**阶段 B** 落地、reviewer `Accepted`）⇒ notes 追加「阶段 E 收口②」段（含授权原话）；`status` **保持 `open`**、`resolved_by: null`（`LLVM-094t` 任务级仍 `待验收`：阶段 D 未做、阶段 C ① 待裁定〔`ISS-230`〕）⇒ **待任务级 `已验证` 后**回填 `closed`（同 `ISS-200` 先例）。

**未动（明确）**：`contracts/`（机器可读）、`components/**`、其它 `spec/` 册、`.tao/archive/**`、`ADR-0019`/`ADR-0026` 正文、`milestones.md`（见下「披露」）。**未** `push`。

**披露（未做，供主会话裁定）**：`milestones.md` `L176` 的「已知限制/遗留」仍写「`contract-elf §2.2` 仍为旧号（`ABS48=0`/`NUM=6`）⇒ 随 `ISS-206`（P2）同步」——本次已不成立，但该文件不在本派单必做清单内 ⇒ **未动**，提请同步。

#### architect 提交 / merge 留痕（2026-10-16，阶段 E；**只追加**）

- **开工前现场（核）**：分支 `LLVM-094t-E`（`git branch --show-current` = `LLVM-094t-E`）；`HEAD` = `b43680d`（= `master`）；`git status --porcelain -uall` = **干净**。⚠️ **披露**：交办称「`master` = `origin/master` = `b43680d`」，而现场本地 `origin/master` ref = **`ae47ae5`**（`git branch -vv` 显示 `master` `[origin/master: ahead 1]`）⇒ 该 ref 系**未 fetch 的陈旧本地值**；**未** fetch、**未** 改动远端状态、**未** push。
- **文件集对账**（逐路径显式 staging、**未用** `git add -A`）：`git diff --cached --name-status` = **5 `M`**（0 `A` / 0 `D`），与上「本阶段改动文件（5 个）」声明**逐条一致** ⇒ **无漏提 / 多提 / 越界**（`spec/` 命中 **1** 册 = 已授权，证据 = 上「用户授权」段 + 锁注释）。
- **笔 1** = `c3241ad`（5 文件、+55/−7）。**档位披露**：阶段 E = **阶段级落地**、任务级 `**状态**` 仍 `待验收`（阶段级验收未走）⇒ 按 `architect.md` 常规应为 `WIP:` 前缀；**主会话本次明确指令为不带 `WIP:` 的正式提交信息** ⇒ 从指令执行并在此披露（同阶段 A/B/C 先例）。
- **只读核对（真实 rc）**：见上「阶段 E 记录」门控行（`make check` L1 + 7 项单项各 **rc=0**；记录落纸**前后各跑一轮** L1，均 **rc=0**；日志 `.work/log/llvm/LLVM-094t-E-architect-*.log`）。
- **落地**：`merge --ff-only` 入 `master` ⇒ `master` = 笔 2（含 `c3241ad`）；分支 `LLVM-094t-E` 已删。**未** `push`（`push` 只由主会话在 `/complete` 后执行）。
