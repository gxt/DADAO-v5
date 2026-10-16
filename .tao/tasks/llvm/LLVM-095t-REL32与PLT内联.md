# LLVM-095t: `aip.si` 恢复（原 `rela.si`；用户 2026-10-16 裁定改名）+ GOT/PLT 远距离取址（**原 `R_DADAO_REL32` 路线已改线；本册 = `ADR-0029`（`Accepted`）的实现落点，阶段 ①–⑤ 已定**）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ADR-0029`（**`Accepted`**，2026-10-16 用户逐条确认 —— 本册 = `D2`/`D3`/`D4`/`D5`/`D6`/`D7②` 的执行落点）、**`SPEC-145t`**（**前置**：`aip.si` 编码 / 语义**冻结**后才可发 MC / reloc ⇒ 本册在前置 `已验证` 前**不得开工**）、`LLVM-094t`（阶段 A/B/C 产出：PIC / `ET_DYN` 动态产出 / 重定位基线；`Superseded` 的 `REL32` 实现已 `git revert`）、`ADR-0019 D5`（逐指令挂 reloc）/ `D6`（越界报错）/ `D7`（禁 relaxation）/ `D10`（类型集·编号·密集无空档；`D11` **已撤**）/ `D12`（**新增** `R_DADAO_PCREL_HI` = `14` / `R_DADAO_PCREL_LO` = `15` / `R_DADAO_NUM` = `16`；用户 2026-10-16 确认）、`ADR-0026 D5`/`D7`（GOT·TP 访问 / 失败与越界；已挂「本次改线」注记）、`ADR-0028`（**`Superseded`**；其 `REL32` 路线已废）、`ADR-0021 D3`（`REL12`/`ABS12`）；契约真源 = `.tao/contracts/contract-elf.md §2.2`/`§3.1`/`§3.2`、`.tao/contracts/contract-dynlink.md §2.2`/`§3`/`§4.3`（**现状**：GOT 远距离通道 / PLT 形态标「待后继 ADR 定」⇒ 本册随实现同步）；现场来源 = `LLVM-094t`、`ISS-230`；纪律 = `ISS-229`（重建串行）、`ISS-210`（改 MC/`.td` 必 `install-host`）、`docs/Process-01`（组件补丁树）、`docs/Process-05`（L1/L2/L3）
**状态**：待开始

> **改名注记（2026-10-16，追加）**：用户 2026-10-16 裁定「**改为：aip.si，在正文中，避免使用pc，应该用ip；而且，在SimRISC中，ip明确是当前正在执行的指令的地址，而非主流ISA的下一条指令地址**」⇒ 本册**正文**已同步 `rela.si` → **`aip.si`**、`PC` → **`IP`**（用户原话引录 / 现场复核的代码与注释原文**不改** ✓）；**完成区 / 审阅记录 = 历史记录，不改写** ✗。真源 = `ADR-0029` §修订注记、`spec/SimRISC-05 §3.4`、`spec/Toolchain-01 §3.2`/`§5`。

## 执行环境
**执行环境**：本地

## ⚠️ 改线说明（2026-10-16，用户裁定；**先读**）

**原 `R_DADAO_REL32` 路线已改线**：`ADR-0028` → **`Superseded`**；**后继 ADR = `ADR-0029`，已于 2026-10-16 逐条确认转 `Accepted`** ✓ ⇒ **本册阶段 = 已定，不再是提案**。

用户**原话（逐字引录）**：

> 「**我还是觉得rela.si应该恢复，这样就可以完全复用risc-v的方案，仅用一个rb寄存器就可以解决全部问题，且该rb正好可以复用想要取出来的地址所用的寄存器**」
> 「**现在就换！rela.si rbHA, imms18，含义参照risc-v的auipc，编码0x5A；刚才所作的任务回退**」

**已落地的回退（供追溯、勿重复做** ✗**）**：

1. **组件补丁回退**：`git revert` 提交 `f98f1d5`（回退 `609c44b` = 阶段 A 的 `R_DADAO_REL32` / `NUM` = `15`）⇒ `components/llvm-project/patches/{lld/ELF/Arch/DADAO.cpp.patch, llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def.patch}` 已回**阶段 A 之前**（`DADAO.def` 无 `REL32`、**`NUM` = `14`**；`pltEntrySize` = **`24`**）；`.work/source/llvm-project` 按 `docs/Process-01 §7` **重放补丁集**收敛回 E1。
2. **阶段 B 未提交产出留档**：`.work/log/llvm/LLVM-095t-B-reverted.diff` + `...md5`（PLT 内联去槽的阶段 B 改动；**已回退、不再生效**）。
3. **ADR / 契约**：`ADR-0028` = `Superseded`；`ADR-0019 D11` = 「已撤」注记（`NUM` 回 `14`）；`ADR-0026 D5`/`D7` = 「本次改线」注记；`.tao/contracts/contract-elf.md` 回 `NUM` = `14`、无 `REL32`；`contract-dynlink.md` 的通道 / PLT 形态标**待后继 ADR 定**（⇒ **本册随实现同步为 `ADR-0029` 口径**）。
4. **本册原文**：原 `REL32` 路线全文见 git 历史（`609c44b`；回退 = `f98f1d5`）——**以本册现文为准**。**本册文件名中的 `REL32` 为历史命名**（沿用既有路径，**未改名** ✗）。

## 立项来源 / 路线位置

- **路线 = `ADR-0025 D6` 的 `P2` 段的前置（生产者侧）**；本册 = 「GOT/PLT 远距离取址」的**实现落点**（设计载体 = **`ADR-0029`**，取代原 `ADR-0028`）。
- **依赖单向 `llvm → infra`**：本册产出被 `INFRA-085t`（`P2` 消费侧 + 构建）**消费**；`INFRA-085t` 侧「GOT 可及性」阻塞面（`ISS-230`，保持 `open`）**待本册实现验收后**解除并回填 `closed` + `resolved_by: LLVM-095t`。
- **判据边界 = 能编 + 静态可核**（`readelf` / `llvm-readobj` + **独立解析**）：**不跑**（运行验证 = `P3`；`aip.si` 的**执行侧**支持归 `qemu` 模块 = `QEMU-061t`）。本册**不可**有任何「运行通过 / E2E 通过」叙述 ✗。

## 目标（交付物）（**方向层；编码/语义真源 = `ADR-0029` `D1`–`D6`**）

1. **重定位类型**：新增**两个静态**类型 **`R_DADAO_PCREL_HI`（`14`）/ `R_DADAO_PCREL_LO`（`15`）**、**`R_DADAO_NUM` `14 → 16`**（`ADR-0029 D2`；命名 / 编号**已定** ✓）。
2. **工具链（发射侧）**：MC fixup / 记录发射；汇编语法接受 `aip.si`（与 `SPEC-145t` 冻结的语法一致）；CodeGen **GOT 取址 2 条形态**。
3. **工具链（消费侧）**：lld `relocate` 消费两类型（**含配对信息**）+ `writePlt` **12 B**（去数据槽）+ `DADAO.def` 编号。
4. **无布局义务**：`.got` 与访问点距离**不受 ±2 KiB 约束**（治 `ISS-230` 根因）；`tests/scripts/dadao-dyn.lds` 的「`.got` 紧跟 `.text`（±2 KiB 内）」义务**取消**（消费侧 `INFRA-085t`）。
5. **向量 / 证据**：与「一能力一向量」一致（`docs/Process-05`）；独立 oracle（**不从** LLVM/LLD/QEMU/本仓工具反推）；一键证据**可达 FAIL**。

## 编码 / 语义真源（`ADR-0029`；**不得从实现反推**）

| 项 | 值 |
|---|---|
| 高段类型 | `R_DADAO_PCREL_HI` = **`14`**；落点 = **`aip.si` 的 `imms18` 字段**；`value = ((S + A − P) + 0x800) >> 12`（**`+0x800` 后下移 = 舍入到最近 4 KB 倍数**、**非截断**） |
| 低段类型 | `R_DADAO_PCREL_LO` = **`15`**；落点 = **配对 `ld.o rbX, [rbX, imms12]` 的 `imms12` 字段**；`value = (S + A − P) − (高段值 << 12)`（**有符号**；由高段舍入保证余量 ∈ `[−2048, +2047]`） |
| `P` | **`aip.si` 站点地址**（= `rb0` 读出值）；**两段共用同一个 `P`**（**不是**各自指令地址 ✗） |
| 配对信息 | 低段记录**携带「配对信息」指回 `aip.si` 站点**（= RISC-V `%pcrel_lo(label)` 形态：站点标签 / addend 指回 hi 指令）⇒ 链接器据此取回 / 重算该站点**已定的高段值**（`ADR-0029 D2`，**(甲) 显式配对** ✓） |
| 计数 | `R_DADAO_NUM` = **`16`**（`ADR-0019 D10`(e) 密集无空档） |
| 范围 / 失败 | 可达 **±512 MiB**；越界（`S + A − P` 超范围 / 高段或低段落不进各自字段 / 低段越出 12 位有符号域）**与**落点形态不符（高段不在 `aip.si` 的 `imms18` / 低段不在配对 `ld.o` 的 `imms12` / 配对信息悬空或指错站点）⇒ **link-time error**（`ADR-0019 D6`：**不截断、不 wrap、不静默**） |

## 做（**阶段 ①–⑤ 已定**；每阶段可独立验收）

| 阶段 | 范围 | 备注 |
|---|---|---|
| **① 重定位类型 + lld 消费侧**（**已解锁 ✓**：编号 = `PCREL_HI` = `14` / `PCREL_LO` = `15` / `NUM` = `16`，用户 2026-10-16 确认 + `ADR-0019 D12` 已落纸） | `DADAO.def` 加 `PCREL_HI` = `14` / `PCREL_LO` = `15` / `NUM` = `16`；`lld/ELF/Arch/DADAO.cpp` 的 `relocate` / `relocTypeToRelExpr` 等消费两类型（**含配对信息取回 hi 站点已定值**；高段**舍入**；越界 / 落点不符 / 配对悬空 ⇒ **报错**） | 契约同步：`.tao/contracts/contract-elf.md §2.2`/`§3.1`/`§3.2`（**本册开工时已是 `PCREL_HI`=14/`PCREL_LO`=15/`NUM`=16 终表** ✓）；改 `components/**` ⇒ 见「前置申报」 |
| **② MC / 发射侧** | `MCCodeEmitter` / `AsmBackend` / `FixupKinds` / `ELFObjectWriter` / `MCInstLower` / `DADAOAsmParser` / `Disassembler`：接受 `aip.si`（`riii` / `0x5A`）+ 发射 `PCREL_HI` / `PCREL_LO` 记录（**一指令一条记录**，`SHT_RELA` 显式 addend） | 改 MC / `.td` ⇒ **必 `install-host`**（`ISS-210`）；语法真源 = `SPEC-145t` 冻结的 `Toolchain-01` |
| **③ CodeGen（GOT 取址 2 条）** | GOT 取址 = **`aip.si rbX, hi` + `ld.o rbX, [rbX, lo]`** = **2 条 / 次**（现状 **1 条**、`REL32` 提案 **3 条**）；**零额外寄存器** —— 同一 `rb` 既承载 `aip.si` 结果、又作 `ld.o` 基址、又收结果（`rbX` 由分配器挑；`rb0` 不可作目的 ⇒ 不涉 `rb0`）；`st.o` 同法复用；**不固定 / 不保留任何寄存器**（`ADR-0026 D5`、`ADR-0018 C6`） | `DADAOISelLowering` / `DADAOISelDAGToDAG` / `.td`；**静态路径逐字节不回归**（`LLVM-094t` 阶段 A 基线） |
| **④ PLT（3 条 / 12 B，去数据槽）** | PLT 条目 = **`aip.si rb4, hi` + `ld.o rb4, [rb4, lo]` + `jump [rb4, rd0, 0]`** ⇒ **3 条 / 12 B**；**取消条目内 8 字节数据槽**（`pltEntrySize` **`24 → 12`**、`pltDataOffset` 取消；**去 padding**）；**由链接器合成**（`writePlt` 直接产字节编码）⇒ 链接器**自己**算 hi/lo、**不经重定位记录**；`rb4` 沿用现状选择 | 契约同步：`.tao/contracts/contract-dynlink.md §3`（PLT 形态 + **布局义务取消** + 通道由「待后继 ADR 定」改为 **`ADR-0029`**） |
| **⑤ 向量 / 证据** | L1（`tests/llvm/lit/MC/DADAO/**`：`aip.si` 编码往返 + 两个 fixup / 记录）+ L2（`tests/llvm/lit/CodeGen/DADAO/**`：GOT 2 条形态 / PLT 12 B 的**结构断言**，仅锁回归）+ **静态可核**（`readelf` / `llvm-readobj` **独立解析**：`.rela.*` 类型号 / 落点 / 配对 / 越界报错；PLT **逐字节 12 B**）+ 一键证据 `.work/evidence/<任务ID>/run.sh`（**反例注入 ⇒ 可达 FAIL**）+ `tools/llvm/llvm-isa-backend-matrix.{md,tsv}` 重生成（如受影响） | 独立 oracle（**不反推**）；`tests/vectors/**` 与 `SPEC-145t` **共用载体** ⇒ **串行**（本册在后） |

## 依赖与待定事项（**开工前核对**）

- **前置已满足** ✓：`ADR-0029` = `Accepted`（逐条确认 ✓）；`SPEC-145t` 的 `aip.si` 编码 / 语义**冻结**（本册开工条件）；`LLVM-094t` 阶段 A/B/C 产出在盘。
- **待确认项（不得自行裁定）** ✗：① **编号（落 `ADR-0019 D12`）—— 已确认 ✓（2026-10-16）**：`ADR-0029 Consequences ③` 的「`ADR-0019` **就地新增一条**（新类型集与编号、`NUM` `14 → 16`）」**已由用户逐条确认并就地落纸** ✓ —— **用户原话（逐字引录，渠道 = 经主会话问答，2026-10-16）**：「**1、复用RISC-V方案；2、PCREL_HI/LO**」+（对编号提案）「**可以**」⇒ `ADR-0019 D12` 已新增（`R_DADAO_PCREL_HI` = `14` / `R_DADAO_PCREL_LO` = `15` / `R_DADAO_NUM` = `16`）；② `ADR-0026 D5`/`D7` 的**通道指向补注**仍**待用户逐条确认** ✗（**未确认前不擅自改其正文** ✗；本册实现照 `ADR-0029` + `ADR-0019 D12` 走）；③ **汇编层单位 = 字节（`imms30`）+ 低 12 位 / 范围检查 + 反汇编按字节打印** —— 规范侧已落纸（`aip.si` 与 `auipc` 的三点差异，用户 2026-10-16 裁定；`SimRISC-05 §3.4` / `Toolchain-01 §3.2`/`§5` / `contract-isa.md §7.4` / `contract-elf.md §2.2`），**实现在本册**：`imms30` 须为 4 KiB 整数倍（低 12 位为 0）、越界（±512 MiB）报错、反汇编按**字节**打印；`imms18 = imms30 >> 12`（4 KiB 块）。
- **变更面预估**：`components/llvm-project/patches/**`（`DADAO.def` / `lld/ELF/Arch/DADAO.cpp` / `MCTargetDesc/**` / `DADAOISel*/`.td` / `AsmParser` / `Disassembler`）+ `components/llvm-project/{series,changelog.md}`、`.tao/contracts/contract-elf.md` / `contract-dynlink.md`、`components/llvm-project/changelog.md`、`tests/llvm/lit/**`、`tests/scripts/dadao-dyn.lds`（**取消布局义务**）、`.work/evidence/LLVM-095t/**`。
- **下发前预检（5 项）**：**已可按定阶段逐条标「现在可跑 / BLOCKED」**（编码 / 公式 / 编号 / 落点 / 失败面均已在 `ADR-0029` 定）⇒ `/dispatch` 前由主会话复核「拟改文件 × `spec/` 清单」（本册**不拟改 `spec/`** ⇒ 该项应**无命中**；命中即 BLOCKED）。

## 验收标准（**命令 + 期望 + 现在可跑**）

1. **类型号 / 计数（静态可核）**：`components/llvm-project/patches/llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def.patch` 中 `PCREL_HI` = `14` / `PCREL_LO` = `15` / `NUM` = `16`，且与 `contract-elf.md §2.2` 终表**逐行一致**（**现在可跑**：`grep` + 独立解析）。
2. **MC 发射**：`llvm-mc` 汇编 `aip.si rbX, <sym@…>` ⇒ 目标文件含 `PCREL_HI`；配对 `ld.o` ⇒ 含 `PCREL_LO` 且**配对信息指回 hi 站点**（**现在可跑**：`llvm-readobj -r` 独立解析 + 断言）。
3. **GOT 取址 2 条**：`-fPIC` 编译取全局地址 ⇒ `.s` / MIR 结构断言 = `aip.si` + `ld.o` **两条**、**同一 `rb`**、**无额外 `rd` 临时**（**现在可跑**：lit L2 + 手工核）。
4. **PLT 12 B**：`-shared` 链接后有 `.plt` ⇒ **每条目 12 B**、无数据槽、`pltEntrySize` = `12`（**现在可跑**：`llvm-readobj` / `objdump` **逐字节**核 + `readelf -S` 尺寸）。
5. **零布局义务（正面证据）**：**默认布局**（不用 `tests/scripts/dadao-dyn.lds`）下 `-shared` **链接成功**（现状 rc=1 + `R_DADAO_REL12 out of range: 65596`，`ISS-230`）（**现在可跑**：`ld.lld` rc=0 + 产物结构校验）。
6. **越界 / 落点不符 ⇒ link-time error**（禁静默）：构造超 ±512 MiB、低段越出 12 位有符号域、高段不在 `aip.si` 落点、配对信息悬空各 ≥1 例 ⇒ 非零 rc + 明确文案（**现在可跑**：`--inject` 类反例脚本）。
7. **大端**：产物 `ELFDATA2MSB`；≥1 个**端序敏感**用例（**现在可跑**）。
8. **静态路径不回归**：`LLVM-094t` 阶段 A 的静态场景断言不变（**现在可跑**：重跑基线脚本）。
9. **L1/L2 门控**：`make check`(L1) rc=0；`check-lit`(L2) rc=0；`check-patch-tree`（改组件补丁树）/ `check-instrinfo`（改 `.td` ⇒ **先 `install-host`**）/ `check-index-blobs` rc=0（**现在可跑**；与其它会话的重建 / L3 **串行**，`ISS-229`）。
10. **证据**：`.work/evidence/<任务ID>/run.sh` 跑通 + **反例注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿**（`cp` 备份 + md5 对账；**禁** `git checkout`/`restore`/`stash`、**禁** `git show <commit>:<path>` 还原）。

## 前置申报（**必读**）

- **本册必改 `components/**`**（`ADR-0029 D5`/`D4` 的实现面：`DADAO.def` / `lld/ELF/Arch/DADAO.cpp` / MC / CodeGen `.td`）⇒ **须重建 + 安装**：
  - 改 **MC / `.td`** 后**必须** `make install-host`（否则门控 / lit 读**旧安装根** ⇒ **假绿**；`ISS-210`；同类纪律见 `AGENTS.md`「构建与注入测试的成本控制」）；
  - **单跑**、**`JOBS=8`**、**禁全核** `-j$(nproc)`；**申报预计耗时**后再启动（`LLVM-094t` 阶段 A/B 实测：`build-mc` 约 **72 min**、`install-host` 约 **5 min** —— 本册按实际增量申报）；
  - **不得**与 `build-*` / L2 / L3 / 其它会话的重建**并发**（`ISS-229`）。
- **长任务（>10 min）**由**主会话** `setsid nohup` 脱离 + 落 `XXX_EXIT=$rc`、日志落 `.work/log/llvm/`；**子代理不得在会话内等待长任务**。
- **补丁纪律**：`docs/Process-01`（树形补丁集 / 一文件一补丁 / `git apply`）+ `check-patch-tree` 机械校验；补丁导出写 `/tmp`、非空 blob。
- **`tests/vectors/**` 与 `SPEC-145t` 共用** ⇒ 本册**须在 `SPEC-145t` 之后**开工（`AGENTS.md`「同改共享文件一律串行」）。

## 不做项（显式）

1. **`qemu-user` / 动态链接的「运行」验证**（`P3`）✗；本册**不可**有「运行通过 / E2E」叙述。
2. **改 `spec/`** ✗（归 `SPEC-145t`）；**QEMU 解码 / 语义** ✗（归 `QEMU-061t`）。
3. **不得**把已回退的 `R_DADAO_REL32` 路线当实现依据 ✗（`ADR-0028` = `Superseded`）；**不得**保留 `NUM` = `15` / 类型 `14` = `REL32` 的表述。
4. **relaxation**（`ADR-0019 D7`）✗；**自写 `ld.so`** ✗；**`ABS48` 两段式**（`ABS48` 序列 + `ldm.o_rrri_rb` 落 `rb`）✗（现有 ABI 下不可实现，`ISS-230`）。
5. **`COPY` / `TLSDESC` / TLS / IFUNC** 的首版支持 ✗（维持 `LLVM-094t` 阶段 C 的**主动拒绝**）。
6. **`ADR-0019` / `ADR-0026` 正文改动** ✗（须用户逐条确认后另落，见「待确认项」）。
7. `ISS-222` / `ISS-223` 收口 ✗（撞上即登记 + 转出，**不得**静默跳过）。

## 完成区

> **改线重置**：本册原 `REL32` 路线（阶段 A 已完成、阶段 B 已实现）**已整体回退**（见文首「改线说明」）⇒ 完成区**重置为空**；其历史见 git（`609c44b` / 回退 `f98f1d5`）与 `.work/log/llvm/LLVM-095t-B-reverted.diff`。

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
