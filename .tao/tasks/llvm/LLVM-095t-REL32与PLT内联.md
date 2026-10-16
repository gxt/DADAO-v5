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

**测试结果**：`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **14 PASS / 0 FAIL，`RUN_EXIT=0`**（`check_mc` A1–A12 12/0 + 13 条定点反例注入 + 5 项分类断言；日志 `.work/evidence/LLVM-095t/run-inject.log`、`.work/log/llvm/LLVM-095t-*.log`）。
**验收锚**：`check-instrinfo` **rc=0，156/156 M1**（关掉 `SPEC-145t` 的已知红）；`check_lit_gen` **rc=0，64 passed/0 failed**（`gen-riii.s` 由既有生成器重生成，+1 条 `rela.si rb8, 8`；`gen-fast.s` 未变）。
**修改文件**（11；`git diff --stat` = +302/−29）：组件补丁 **9 份**（一文件一补丁；`components/llvm-project/series` 仍 **73**，无新文件）——`llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def.patch`(+23/−6)、`llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`(+18/−3)、`.../MCTargetDesc/{DADAOFixupKinds.h(+24/−3),DADAOAsmBackend.cpp(+52/−5),DADAOMCCodeEmitter.cpp(+53/−2),DADAOELFObjectWriter.cpp(+16/−2),DADAOMCAsmInfo.h(+30/−2),DADAOMCAsmInfo.cpp(+36/−2)}.patch`、`.../AsmParser/DADAOAsmParser.cpp.patch`(+41/−4)；`components/llvm-project/changelog.md`(+4)；`tests/llvm/lit/MC/DADAO-gen/gen-riii.s`(+5，**生成器产物、非手改**）。组件源树 `.work/source/llvm-project` 按 `docs/Process-01 §6.4` 就地 `.td`+MC 改动收敛为 **base+1**（`0d261d1ca+1`、clean；本地组件 commit，E1/`check-source-state` 所需、永不推送）；**v5 仓库未提交**。
**阶段进度**：**① ✅**（`DADAO.def`：`PCREL_HI`=14 / `PCREL_LO`=15 / `NUM`=16、0–16 **密集无空档**，与 `contract-elf.md §2.2` **双向 17/17** 一致）；**② ✅**（`.td` 恢复 `rela_si_rb` + MC 四件套 fixup/类型映射 + 说明符管线 `%pcrel_hi`/`%pcrel_lo`）。**③④⑤ 未做**（CodeGen 2 条取址 / PLT 12 B / lld `relocate`；本笔范围外）。**未构建**（`ISS-229`：构建 + L2/L3 由主会话统一跑）。
**验收结果**（各留自身 rc，日志同名）：`check-patch-tree` **rc=0（147 patches）**、`check-index-blobs` rc=0（108 new-file/39 modification）、`check-source-state` rc=0（llvm-project `HEAD=961e380ee`、count=1、clean=True）、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0、`check-component-changelog` rc=0、`check-issues` rc=0。**`make check`(L1) rc=2、唯一红 = `check-isa-coverage`**（归因见「遗留」①）。
**新发现/坑**：① **接口约定（阶段 ③/④ 必读）**：**HI** 记录 = 目标符号 + `r_addend`；**LO** 记录 = **配对信息**（`%pcrel_lo(<hi 站点标签>)`）——本笔使 `PCREL_LO` **不**走符号式重定位 ⇒ 通用 writer 把该局部标签折成 **section symbol + addend = 站点地址**（契约 §3.1「以站点标签 / addend 指回 hi 指令」），链接器据此回查该站点已定的 hi 记录；两段**共用同一 `P`**。② 两段**汇编期一律不就地解析**（`evaluateFixup ⇒ false`），并加**符号操作数守卫**（常量操作数 ⇒ 显式报错，避免「空符号重定位」）。③ 目的 `rb0` ⇒ ILLI 属**执行层**规则 ⇒ MC 层不查（`lessons §1.47`）。④ **改 `.td` ⇒ 矩阵投影必变**：`check-isa-coverage` 第①层须**新** `llvm-mc`（`ISS-210`）——**不得**用旧安装根重生成（「与旧安装根自洽」即假绿）。⑤ `lld/ELF/Arch/DADAO.cpp:95` 注释「`R_DADAO_NUM = 14`」已陈旧（值本身仍安全：`NUM`=16 非实际类型，`getRelExpr` 默认分支对 14/15 显式报错）——归阶段 ③/④ 同笔更新。
**遗留问题**：① **`make check` 唯一红 `check-isa-coverage`**（rc=1；差异恰 **2 行** = `rela.si_riii_rb` 行的 `td_def` 列 `"" → rela_si_rb`，「第①层 `L1_assembler` 仍 `reject`」是**旧安装根**的度量）⇒ **`make install-host` 后跑 `python3 tools/llvm/gen_isa_coverage.py` 重生成 `.tsv/.md`**（本笔不构建 ⇒ 不能以新鲜工具度量，**不做**假绿重生成）。② 阶段 ③（CodeGen GOT 2 条 / `DADAOISel*` + `.td` 打印）、④（PLT 3 条 12 B / `writePlt`）、lld 消费两类型（含配对回查 / 舍入 / 越界与落点不符报错）**未做**——现链接期对类型 14/15 由 `getRelExpr` **显式报错**（非静默）。③ L2/L3（`check-lit`、`check-lit-full`、`check-interface`）**未跑**（`ISS-229` 并发禁令）。④ 未跑 `install-host` ⇒ 新 `llvm-mc` 的真实行为（`rela.si` 汇编/反汇编、两条 `SHT_RELA` 记录、`llvm-readobj -r` 类型号）**尚无实测证据**，归主会话构建后补跑。

### 阶段 ③④ 完成记录（本笔；阶段 ①② 的完成区记录见上）

**测试结果（阶段 ③④）**：**未构建 ⇒ 无运行验证**（`ISS-229` 禁并发；`install-host`/L2/L3 归主会话）。静态门控（各留自身 rc；日志 `.work/log/llvm/LLVM-095t-cd34-*.log`）：`check-instrinfo` **rc=0（156/156 M1）**、`check_lit_gen` **rc=0（64 passed/0 failed）**、`check-patch-tree` **rc=0（147 patches OK）**、`check-index-blobs` rc=0（108 new-file / 39 modification）、`check-source-state` **rc=0（llvm-project clean=True、count=1；musl OK）**、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 悬空）、`check-component-changelog` rc=0（5 文件 × 4 断言；llvm-project 101 条）、`check-issues` rc=0（41 open / 13 closed）、`python3 -m compileall -q tools` rc=0；**`make check`(L1) rc=2、唯一红 = `check-isa-coverage`**（make 运行到该目标即停 ⇒ 其后的 L1 前置由本笔**单独复跑**、逐条 rc=0：`check-cfx-aliases` / `check-dirs` / `check-spec-readonly` / `check-spec-refs` / `check-knowledge-dir` / `check-contracts-dir` / `check-spec-numbering` / `check-spec-changelog` / `check-components`；其前的 `manifest-check`/`validate-vectors`/`check-spec-drift`/`check-patch-tree`/`check-index-blobs`/`check-asm-list*`/`check-spec-codeblocks`/`check-legality*`/`validate-encoding`/`check-scope`/`check-rule-refs`/`check-fp-contract`/`check-instrinfo` 已在同一次 `make check` 内通过）。
**修改文件（阶段 ③④）**：组件源树 **7 份**（`git -C .work/source/llvm-project diff --stat 961e380ee 370ba9afe` = **+381/−84**；一文件一补丁）——`lld/ELF/Arch/DADAO.cpp`（**+244/−43**：`getRelExpr` 支持 14/15 + `relocateInSection` 的 hi 舍入 / lo 残差 / 落点检查 + `relocateAlloc` 配对回查 + `findPcrelHi` + `pltEntrySize` **24→12** + `writePlt` 三条 + 订正 `R_DADAO_NUM = 14` 陈旧注释）、`llvm/lib/Target/DADAO/DADAOCodeGen.td`（+25/−0：伪指令 `PCREL_LOAD`）、`.../DADAOInstrInfo.cpp`（+39/−0：post-RA 展开 + 配对站点标签）、`.../DADAOISelDAGToDAG.cpp`（+30/−24：两处 PIC 取址改配对 + `isPointerBankValue`）、`.../DADAOMCInstLower.cpp`（+19/−4：`%pcrel_lo(...)`）、`.../DADAO.h`（+15/−6：`MO_PCREL_LO`）、`.../DADAOAsmPrinter.cpp`（+9/−7：订正 `.got` 陈旧注释）。⇒ 导出 `components/llvm-project/patches/**` **7 份改**（`make-patch: 1 written, 72 unchanged (skipped)`〔二次导出；首轮 7 written/66 unchanged〕；`series` 仍 **73**、无新增/删除文件）；v5 侧另改 `components/llvm-project/changelog.md`（+1 条「阶段 ③+④」）。**组件源树本地 commit** = `370ba9afe`（= base `0d261d1ca` **+1**、clean）：`Process-01 §6.3/§6.4` 的 E1/E3 硬要求（`make_patch.py` 会**拒绝**从脏树导出）与 `check-patch-tree` 断言⑦⑧⑨/`check-source-state` 同要求 ⇒ 本笔执行了**组件树**的收敛提交（`git add` 逐文件显式 + `commit --amend --no-edit`，**永不推送**）；**v5 仓库零 `git add`/`commit`/`push`** ✓（披露项）。
**验收结果（阶段 ③④）**：真值 = 上列日志的现场输出。**`make check` 现场**（`.work/log/llvm/LLVM-095t-cd34-z-make-check.log`）：唯一 FAIL = `check-isa-coverage`（`gen_isa_coverage --check: FAIL（2 项）` = `.tsv` + `.md`），工具打印的差异经 `difflib.unified_diff(…)[:12]` **截断**，可见两项 = **证据行号位移**（`add.o_orrr_bbd` 的 `isel-cpp:DADAOISelDAGToDAG.cpp.patch:{144,170,371}` → `{145,177,377}`；`add.si_riii_rd` 的 `DADAOInstrInfo.cpp.patch:266` → `269`）与 **`isel-cpp` 计数 18 → 16**（ISel 不再直接生成 `ld.o rb, [rb0, slot]`，改由 `PCREL_LOAD` 伪指令 + post-RA 展开承担，而 `DADAOInstrInfo.cpp` 不在 isel-cpp 扫描面内）；完整差异另含阶段 ①② 遗留的 `rela.si_riii_rb` 行（见其完成区「遗留①」）。**本笔不重生成矩阵**：该门控第①层由**安装根**的 `llvm-mc` 度量（`ISS-210`），本轮不做构建 ⇒ 无与补丁树同代的新鲜根，用旧根写出即「自洽假绿」；重生成归 `install-host` 之后（+ 阶段 ⑤）。
**新发现/坑（阶段 ③④）**：① **配对标签只能在 MachineInstr 层产生**（`setPreInstrSymbol` + 通用 `AsmPrinter::emitFunctionBody` 的 pre-instr label 路径；`DADAOAsmPrinter` 只覆盖了 `emitInstruction`，标签由框架循环出 ⇒ 不受影响）；SelectionDAG 没有「本指令地址」符号 ⇒ 取址落**伪指令 + `expandPostRAPseudo` 展开**（与 RISC-V `expandAuipcInstPair` 同形，但**零暂存寄存器**、**同一个 `rbX`** 载体/基址/目的）。② `MachineInstr::getMF()` 返回 **`const MachineFunction *`** ⇒ 取非 const MF 须 `*MBB.getParent()`（自审 F1 捕获）。③ lld 侧低段用 **`R_PC`** 表达（`R_PC` 属 `isRelExpr` ⇒ PIC 下仍是链接期常量、**不产动态重定位**），**值**由 `findPcrelHi` 回查 hi 记录复用同一 `P`；配对查找用**线性扫描**（不依赖 `sec.relocs()` 有序）。④ 站点标签名 = `.Lpcrel_hi<N>`（`MCAsmInfoELF` 的 `InternalSymbolPrefix = ".L"` + STB_LOCAL）⇒ 通用 writer 折成 **section symbol + addend = 站点地址**，与阶段 ①② 的接口约定**逐条吻合**。⑤ 原 `ld_o_rb` 在 `isPointerBankValue` 的条目**保留**（现由 GPRB 溢出的 reload 承担），只**新增** `PCREL_LOAD` ⇒ 静态/溢出路径不回归。⑥ **配对不要求相邻**：标签随 `rela.si` 走（LO 以符号引用），post-RA 调度/重排不会破坏配对，硬件语义亦不变（`P` = 站点自身）。
**遗留问题（阶段 ③④）**：① **落点检查偏严**（hi 须 `op == 0x5A`；lo 须 `op ∈ {0x22, 0x23}`）——只覆盖 ADR 约定形态；若将来允许 `ld.o rdX` / 别的基址形态须同步放宽（现状失败响亮、非静默 ✓）。② **待构建后补验（主会话；`make install-host` 后）**：(a) `llvm-mc` 汇编 `rela.si rbX, <sym>` + 配对 `ld.o rbX, [rbX, %pcrel_lo(<站点>)]` ⇒ `llvm-readobj -r` 见**两条** `SHT_RELA`（14/15）且 LO 的 symbol+addend = 站点地址；(b) `-fPIC` 取全局地址 ⇒ `.s`/MIR **2 条**、同一 `rb`、无额外 `rd`，且**静态路径逐字节不回归**（`LLVM-094t` 阶段 A 基线）；(c) `-shared` **默认布局**（不用 `tests/scripts/dadao-dyn.lds`）⇒ 链接成功（`ISS-230` 正面证据）+ `.plt` 每条目 **12 B**、无数据槽（`readelf -S` + 逐字节）；(d) 4 类反例（越界 / 高段落点不符 / 配对悬空 / 低段落点不符）⇒ 非零 rc + 明确文案；(e) `check-isa-coverage` **重生成**矩阵后回绿（`python3 tools/llvm/gen_isa_coverage.py`，须新安装根 ⇒ `ISS-210`）。③ L2/L3（`check-lit` / `check-lit-full` / `check-interface`）未跑（`ISS-229`）。④ `.work/evidence/LLVM-095t/run.sh` 仍只覆盖阶段 ①②（本笔按指令不构建 ⇒ 未扩证据脚本）⇒ ③④ 的可执行证据（含反例注入）须在 `install-host` 后补。

### 阶段 ② 补 完成记录（本笔：跟名 `aip.si` + 汇编层单位=字节）

**测试结果**：`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **17 PASS / 0 FAIL，`RUN_EXIT=0`**（`check_mc` A1–A17 **17/0**；`inject.py` **25/0** = 基线副本 17/0 + **24 条定点反例**全命中且目标检查真红；日志 `.work/log/llvm/LLVM-095t-{check_mc,inject,check-*}*.log`）。**未构建**（`ISS-229` 并发禁令）⇒ `llvm-mc` 运行期行为（字节受理 / 两条负例诊断 / 反汇编字节打印）**待 `install-host` 后由 L2 复核**。
**修改文件（20 项；组件源树本轮 16 份，`git -C .work/source/llvm-project diff --stat 370ba9afe 59ae0ac2f` = **+118/−60**）**：① 组件补丁 **16 份改**（一文件一补丁；`series` 仍 **73**、无增删）——`DADAOInstrInfo.td`（def/common 改 `aip_si_rb`/`"aip.si"` + 字节口径注释）、`MCTargetDesc/{DADAOMCCodeEmitter.cpp,DADAOMCInstPrinter.cpp,DADAOAsmBackend.cpp,DADAOFixupKinds.h,DADAOELFObjectWriter.cpp,DADAOMCAsmInfo.h}`、`AsmParser/DADAOAsmParser.cpp`（字节→块换算 + 两条检查）、`DADAOInstrInfo.cpp`（`get(DADAO::aip_si_rb)`）、`DADAO.h`/`DADAOAsmPrinter.cpp`/`DADAOISelDAGToDAG.cpp`/`DADAOCodeGen.td`/`DADAOMCInstLower.cpp`（注释跟名 + `IP`）、`llvm/include/.../ELFRelocs/DADAO.def`、`lld/ELF/Arch/DADAO.cpp`（注释 + `not at an \`aip.si\` site`）。② v5 侧：`components/llvm-project/changelog.md`（+1 条）、`tools/testcases/generate_lit_vectors.py`（`aip.si rb8, 32768`）、`tests/llvm/lit/MC/DADAO-gen/gen-riii.s`（**生成器重生成**）、`tests/vectors/isa/aip-si.yaml`（**新**，由 `rela-si.yaml` 改名）、`tests/vectors/isa/rela-si.yaml`（**删**）、`tests/vectors/inventory.md`、`tests/vectors/isa/reserved.yaml`（notes 内 id 跟名）、`tests/llvm/lit/MC/DADAO/aip-si-imm.s`（**新**，边界正例 5 + 负例 4 条 RUN）、`.work/evidence/LLVM-095t/{check_mc.py,inject.py,run.sh}`、本任务书。
**验收结果**（各留自身 rc；日志同名 `.work/log/llvm/LLVM-095t-*.log`）：`check-instrinfo` **rc=0（156/156 M1，`0 errors`）**——**关掉 `SPEC-145t` 的已知红**；`check_lit_gen` rc=0（64 passed/0 failed）；`validate-vectors` rc=0（**156/156**、0 gap）；`check-patch-tree` **rc=0（147 patches OK）**；`check-index-blobs` rc=0（108 new-file/39 modification）；`check-source-state` rc=0（llvm-project `HEAD=59ae0ac2fa77`、count=1、clean=True）；`check-asm-list` rc=0（12 spec files OK）/`check-asm-list-drift` rc=0（byte-identical）；`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`（41 open/13 closed）均 rc=0。**`make check`(L1) rc=2、唯一失败目标 = `check-isa-coverage`**（`Error 1` @ `Makefile:845`；其后 L1 前置由本笔**单独复跑**逐条 rc=0：`check-cfx-aliases`/`check-dirs`/`check-spec-readonly`/`check-spec-refs`/`check-knowledge-dir`/`check-contracts-dir`/`check-spec-numbering`/`check-spec-changelog`/`check-components`）。**`check-isa-coverage` 如实红**（`--check` rc=1；**真源重派生**到 `/tmp` 后：`aip.si_riii_rb` 行已带 `td_def=aip_si_rb`、`L1_assembler=reject`（= **旧安装根**度量）、`rela.si_riii_rb` 行 **0**）⇒ **不用旧根重生成仓库内 `.tsv/.md`**（那才是假绿）。
**新发现/坑**：① **单点换算**优于两处：把 `bytes >> 12` 落在 `DADAOAsmParser::matchAndEmitInstruction`（**与既有 ×4 组 `jump`/`br.*` 的字节→字偏移同形**）⇒ `MCCodeEmitter` 的 imm 路径**不必**再移位，避免「parser 查范围 + emitter 移位」两处漂移（自审 F1 起于首版两处实现）。② **归 `getImmediateFieldKind::None`**（同 `br.*` 处理）⇒ 不对"已换算值"再报 `imms18` 误导文案；18 位有符号域检查由本处单点完成（等价）。③ **C++ 负值语义**：`%` 截断除法 + `>>` 算术右移 ⇒ `-4097 % 4096 = -1`（判非倍数 ✓）、`-536870912 >> 12 = -131072`（下界 ✓）；与 `lld` 的 `disp >> 12` 同口径。④ **负例的两种"可达 FAIL"分工**：lit（`not %llvm_mc` + `FileCheck`，`tests/llvm/lit/MC/DADAO/aip-si-imm.s`）证**汇编器输入级**可达 FAIL；`check_mc.py` A14 + `inject.py` 3 条变异证**实现级**（检查被删⇒断言真红）。⑤ **改名会连带打断既有证据**：`check_mc.py` 的 A12 契约串（文档侧已改 `aip.si`）与 `inject.py` 的注入目标名陈旧 ⇒ 不同步即「基线假红 / 注入假绿」（本笔已修，见自审 F3）。⑥ 文档侧 `ADR-0029 D2` / `contract-elf.md §3.1` 的 `aip.si rbX, hi` 是**重定位方案记号**（`hi`/`lo` = 链接器写入的字段值），非汇编层字面（字面按 `imms30` 字节）——**建议文档侧加一句注明**（只报不改）。
**遗留问题**：① `check-isa-coverage` 仍红 ⇒ **`make install-host` 后** `python3 tools/llvm/gen_isa_coverage.py` 重生成 `.tsv/.md` 回绿（`ISS-210`；不得以旧根重生成）。② 运行期证据（`aip.si rb2, 4096` 编码 `5a080001`、两条负例文案、反汇编打 `4096`、`gen-riii.s` ASM 往返、`aip-si-imm.s` 全绿）**待 `install-host` 后由 L2（`check-lit`）复核**。③ 阶段 ③④ 的构建后补验清单（两条 `SHT_RELA`、PLT 12 B、GOT 2 条）**仍待**（同批）。④ **v5 暂存态**：`tests/vectors/isa/rela-si.yaml` 为 **` D`（删除）**、`aip-si.yaml` 为 **`??`（新）** ⇒ 收尾 staging 须**同时**纳入二者（逐路径显式 `git add`，禁 `-A`）。⑤ 组件源树按 `docs/Process-01 §6.3/§6.4`（E1/E3 硬要求）收敛为 **base+1** 本地 commit（`amended`、永不推送）——**披露项**：本笔在组件检出内执行了 `git add`（逐文件）+ `commit --amend`；**v5 仓库零 `git add`/`commit`/`push`** ✓。⑥ 跟名波及**本册范围外**的旧名残留（只报不改）：`tools/qemu/min_rom_probe_009t.py`（`rela_si_rb()` 函数名/注释 ⇒ 归 `QEMU-061t`）、`.work/evidence/SPEC-145t/run.sh`（历史证据脚本引用 `tests/vectors/isa/rela-si.yaml`，重跑会红 ⇒ 历史留证不追改）、`.tao/knowledge/milestones.md` 等台账（架构师域）。**文档侧待改示例（只报不改）**：无「块单位」示例残留（`Toolchain-01 §5` 已是 `aip.si rb2, 4096`；`SimRISC-05 §3.4` 为 `aip.si rbHA, imms30`）；唯一建议 = 给 `aip.si rbX, hi` 这类**重定位方案记号**加「非汇编字面」注（位置：`.tao/contracts/contract-elf.md §3.1`/`§3.2` 两处 + `ADR-0029 D2`）。

### 阶段 ② 补（编译修复）完成记录（本笔：修 3 组编译错；只修编译、**不改语义**）

> 现场：`make install-host` ⇒ `build-mc` Error 1、`INSTALL_EXIT=2`（`.work/log/llvm/LLVM-095t-CD-install.log`，15:53:56→16:17:48，2 处 `FAILED`）。本笔 = 修这些编译错 + **编译级自检直到通过**（不跑 `install-host`/`build-*`/L2/L3，归主会话）。

**测试结果（编译级自检）**：① **增量构建** `ninja -j8 -C .work/build/llvm llvm-mc llvm-readobj llvm-objdump llvm-objcopy LLVMDADAOCodeGen llc lld` ⇒ **355/355、`NINJA_EXIT=0`**（日志 `.work/log/llvm/LLVM-095t-cdfix-ninja.log`；覆盖 DADAO `MCTargetDesc`/`AsmParser`/`Disassembler`/CodeGen + `lld/ELF/Arch/DADAO.cpp` + `bin/lld` 链接）；组件提交 amend 改 `HEAD` ⇒ `VCSRevision.h` 重派生 ⇒ 追加一轮 **19/19、`NINJA_FINAL_EXIT=0`**，随后 `ninja -n <同目标集>` ⇒ **`no work to do`**。② **定点 TU 语法检查**（12 个本笔新写/改动的 TU；命令 = `ninja -t commands <obj>` 的原命令 + `-fsyntax-only`）⇒ **failed=0**（逐条 rc 见 `.work/log/llvm/LLVM-095t-cdfix-syntax-only.log`）；**可达 FAIL**：注入 `#error` ⇒ 该 TU **rc=1** ⇒ `cp -p` 还原 ⇒ md5 三值一致且 **rc=0**（3 例：MC emitter / MCAsmInfo / lld DADAO；`.work/log/llvm/LLVM-095t-cdfix-inject-probe.log`）。③ 既有证据脚本不回退：`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **17 PASS / 0 FAIL、`RUN_EXIT=0`**（`check_mc` 17/0 + `inject` 25/0）。
**修改文件**：组件源树 **2 份**（`git -C .work/source/llvm-project diff --stat 59ae0ac2f 2b17fa335` = **+9/−2**）——`llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp`（**+1**：补 `#include "llvm/Support/raw_ostream.h"`）、`.../DADAOMCCodeEmitter.cpp`（**+8/−2**：补 `#include "llvm/Support/Casting.h"`、`MCOp.getLoc()` → `Expr->getLoc()` ×2 + 5 行注释说明位置来源）。⇒ 重导出 `components/llvm-project/patches/**`（`make-patch: 2 written, 71 unchanged (skipped)`；`series` 仍 **73**、无增删）；`check-patch-tree` rc=0（147）。组件源树本地 commit = `2b17fa335`（= base `0d261d1ca` **+1**、clean；`Process-01` E1/E3 与断言⑦⑧⑨ 硬要求、**永不推送**）。**v5 仓库零 `git add`/`commit`/`push`**；v5 文件集与开工时一致（26 项，无新增；`.work/**` 被 gitignore）。
**验收结果**（各留自身 rc；日志 `.work/log/llvm/LLVM-095t-cdfix-*.log`）：`check-instrinfo` **rc=0（156/156 M1、`0 errors`）**、`check_lit_gen` rc=0（64 passed/0 failed）、`validate-vectors` rc=0（156/156、0 gap）、`check-patch-tree` **rc=0（147 patches OK）**、`check-index-blobs` rc=0（108 new-file/39 modification）、`check-source-state` rc=0（llvm-project `HEAD=2b17fa3355a8`、count=1、clean=True）、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 悬空）、`check-component-changelog` rc=0、`check-issues` rc=0（41 open/13 closed）；**`make check`(L1) rc=2、唯一失败目标 = `check-isa-coverage`**（`make: *** [Makefile:845: check-isa-coverage] Error 1`；已知红：第①层由**旧安装根**的 `llvm-mc` 度量 ⇒ 待 `install-host` 后重生成）——该目标之后的 L1 前置本笔**单独复跑**、逐条 rc=0：`check-cfx-aliases`/`check-dirs`/`check-spec-readonly`/`check-spec-refs`/`check-knowledge-dir`/`check-contracts-dir`/`check-spec-numbering`/`check-spec-changelog`/`check-components`（日志 `.work/log/llvm/LLVM-095t-cdfix-post-*.log`）。
**新发现/坑**：① `OS << '%'` 报「`raw_ostream` 打不了 `char`」的**真根因是缺 include**：该 TU 里 `raw_ostream` 只有前置声明（`MCAsmInfo.h:41` / `MCExpr.h:28`）⇒ 成员 `operator<<(char)` 不在候选集，诊断只列 `VersionTuple` 的 free operator（自建最小探针复现出**逐字相同**的诊断）；改法 = 补 `llvm/Support/raw_ostream.h`（先例 `Xtensa/MCTargetDesc/XtensaMCAsmInfo.cpp:16`），**不**改打印写法。② `dyn_cast` 在本树**未**弃用（`llvm/Support/Casting.h:643`），补 include 即可（先例 `Mips/MCTargetDesc/MipsMCAsmInfo.cpp:16`）。③ `MCOperand` **没有**位置 API；换用 `MCExpr::getLoc()`，**依据** = `MCFixup::getLoc()` 的实现即 `getValue()->getLoc()`（`MCAssembler.cpp:1178`）⇒ 与 `DADAOAsmBackend` 的 `Fixup.getLoc()` **同源**，且 AsmParser 给 `%pcrel_hi(...)`（`Loc` = `%` 记号，`DADAOAsmParser.cpp:564/579`）与裸符号（`MCSymbolRefExpr::create(..., FirstTokenLoc)`，`MCParser/AsmParser.cpp:1252`）都带真实位置；文案与硬失败（`MCContext::reportError` ⇒ `HadError=true`）不变。④ **组件 amend 提交会改 `HEAD`** ⇒ `VCSRevision.h` 重派生 ⇒ 构建需**再跑一轮**才回 `no work to do`（本次 19 作业）——`install-host` 前若有组件提交，预算该增量。
**遗留问题**：① **未跑** `make install-host` / `make build-*` / L2 / L3（按指令，归主会话）⇒ 运行期行为（汇编/反汇编/负例诊断/两条 `SHT_RELA`/PLT 12 B/GOT 2 条/矩阵重生成）**仍待** `install-host` 后补验（阶段 ② 补「遗留②」清单不变）。② `check-isa-coverage` 仍红（`ISS-210`：须新安装根重生成）。③ 本笔已把 `.work/build/llvm/bin/{llvm-mc,lld,llc}` 编译到**构建目录**（**未 install**）⇒ 安装根仍为旧产物（故 ① 的补验不可提前）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查 9 份补丁（`.def` / `.td` / fixup / backend / emitter / writer / AsmInfo ×2 / AsmParser）+ 证据脚本；真值全部取自当次真实输出。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现）`%pcrel_hi(4)` 这类**常量**操作数 ⇒ `evaluateFixup` 返回未解析 ⇒ 走到 `recordRelocation` 时 `SymA == nullptr`（ELF 重定位无符号索引 ⇒ 潜在崩溃/坏记录） | ✅已修 | `DADAOAsmBackend::evaluateFixup` 的 hi/lo 分支加**符号操作数守卫**（`!Target.getAddSym()` ⇒ `reportError`，显式失败不静默） | `check_mc` A7 PASS（含守卫断言）；`inject.py` 新增「守卫变异」定向反例 ⇒ A7 真红 |
| F2（自审发现·证据侧）`check_mc` A7 用 `body_of` 取分支体，遇**嵌套 `}`** 提前截断 ⇒ 基线**假红** | ✅已修 | 改为按标记切片（`if (Kind == …PCREL_HI \|\|` → 下一小节注释），并纳入「守卫」两字符串 | `inject.py` 的 **BASE 基线副本**由红转绿（`checks: 12 passed, 0 failed`）——正是该自检捕获的 |
| F3（核过·非 finding）`%pcrel_lo(<标签>)` 的**悬空/指错站点**不在汇编期校验 | ⏸按契约留 link-time | 不校验（契约 §3.2 明列「配对悬空 / 指错站点 ⇒ **link-time error**」）；LO 记录已带站点地址供 lld 回查，阶段 ③/④ 落报错 | 代码注释 + 完成区「新发现①」；`check_mc` A11（`needsRelocateWithSymbol` 仅 ABS48） |
| F4（核过·非 finding）`NUM` 14→16 是否影响 `lld` 的 `iRelSymbolicRel = R_DADAO_NUM` 哨兵 | ❌不修（非缺陷） | 不动：16 仍**不是**实际类型（0–15 全密）⇒ 哨兵语义不变；仅**注释**陈旧 → 登记归阶段 ③/④ | `check_mc` A2/A3（0–16 密集 + 契约一致）；`grep` 现场核 `DADAO.cpp:94-96` |
| F5（核过·非 finding）`%pcrel_hi`/`%pcrel_lo` 用错位置（非 `rela.si` / 非配对 `ld.o`·`st.o`） | ✅已覆盖 | 发射器按 `Opcode`/`isLoadStoreInstr` 分派，越位即 `Ctx.reportError`（源定位报错） | `check_mc` A8（含 `if (!isLoadStoreInstr(Opcode))` 守卫）；`inject.py` A8 定向反例真红 |
| F6（核过·非 finding）目的 `rb0` ⇒ ILLI 是否需 MC 层拒绝 | ❌不修（分层口径） | 不加汇编期检查（`lessons §1.47`：静态可判合法性落**执行层**；`SPEC-145t` 已落契约/合法性数据，`QEMU-061t` 落译码） | `.td` 注释明写分层依据；`check_mc` A4（def 与既有 `add_si_rb` 同形） |
| F7（真值对齐自审）完成区数字是否逐字来自真实输出 | ✅已核 | 每项均可回溯：`run-inject.log` / `.work/log/llvm/LLVM-095t-*.log` / `git diff --stat`；未构建、未 commit（v5）、未 push、未改 `spec/`·`.tao/contracts/`·`contracts/` | `bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **14/0，RUN_EXIT=0** |

**判决**：F1/F2 已修并复验；F3–F6 为「核过·非缺陷」（附契约/教训依据）；**无未修 finding**。⇒ 阶段 ①② 交付面自审通过（状态由主会话处置，本笔按指令**不改 `**状态**`**）。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 第 2 轮 engineer 自审（阶段 ③④）

**自审方式**：纳入阶段 ② 已定接口后，逐行审查 7 份补丁的全量新增/改动行（`.td` / ISel / `InstrInfo` / `DADAO.h` / `MCInstLower` / `AsmPrinter` / `lld DADAO.cpp`）+ 全量 `git diff`；真值取自当次真实输出（`git` 现场 + 门控日志）。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·编译级）`MachineInstr::getMF()` 返回 **`const MachineFunction *`**，无法绑定到 `setPreInstrSymbol(MachineFunction&, …)` 所需的非 const 引用 ⇒ 展开处**编不过** | ✅已修 | `expandPostRAPseudo` 的 `PCREL_LOAD` 分支改用 `MachineFunction &MF = *MBB.getParent();`（`MachineBasicBlock::getParent()` 非 const 重载） | `grep` 现场：`MachineInstr.h:385` 仅 const 版 / `MachineBasicBlock.h:326` 非 const 版；文中再无 `getMF()` |
| F2（自审发现·误写）首轮 edit 误添第二个伪指令 `PCREL_LOAD_MMO`（多余 def） | ✅已修 | 删去，只留 `let mayLoad = 1 in def PCREL_LOAD`（`mayLoad` 理由写进注释：展开的第二条是真访存） | `.td` 现场仅 **1** 处 `PCREL_LOAD`；`git diff --numstat` DADAOCodeGen.td = +25/−0 |
| F3（核过·非 finding）lld 对低段返回 **`R_PC`**（其「值」却由 hi 回查得）是否误导/漏动态重定位 | ❌不修（附依据） | `R_PC` 属 `isRelExpr` ⇒ `isStaticLinkTimeConstant` 在 PIC/PIE 下为 true ⇒ **不产**动态记录（文本内补丁型 reloc 只能链接期定）；专用 `RelExpr` 须改 lld 核心（`Relocations.h`/`Relocations.cpp`/`InputSection.cpp`）——本笔文件面之外；语义在代码注释 + 完成区明写 | `isRelExpr` 名单含 `R_PC`（`Relocations.cpp:150`）；`undefBranch` 自循环改写按 `rel.expr == R_PC && type ∈ {REL26,REL20,REL14}` 判 ⇒ 本两类型**不受**影响 |
| F4（核过·非 finding）`getRelExpr` 对 14/15 的 **preemptible 守卫**是否误伤既有用法 | ✅已核（无假阳） | 加守卫（preemptible ⇒ 显式报错，不静默发动态记录）；本 backend 两处调用点的符号都是 `getGOTSlotSymbol*` 出的 `.Lgot.<n>`（**STB_LOCAL**，非 preemptible） | `DADAOAsmPrinter.cpp:createGOTSlot`（`getOrCreateSymbol(".Lgot."+N)`）；现场核 `DADAO.def`/`lld DADAO.cpp` 仅此两处消费 14/15 |
| F5（核过·非 finding）配对查找若依赖 `sec.relocs()` 有序会脆（RISC-V 靠 `scanSection` 里的 `stable_sort`） | ❌不修（选更稳做法） | 用**线性扫描**按 `offset == site` 找 hi 记录（不依赖排序；单 section 内 reloc 数小） | `findPcrelHi` 现场实现；未新增排序/预扫面 |
| F6（核过·补强）「落点不符」若只看类型号，站点标签落在数据/指令中间仍会补错字段 | ✅已覆盖 | 额外读**指令字**校验：hi 站点 `op8 == 0x5A`（`rela.si`）、lo 站点 `op8 ∈ {0x22, 0x23}`（`ld.o`/`st.o` rb 形式） | 完成区「遗留①」记其偏严面；契约 §3.2 第 2 类（落点不符）逐条对上 |
| F7（核过·非 finding）伪指令带 `mayLoad` 但**无** `MachineMemOperand` 是否会触发验证器/语义问题 | ✅已核（安全） | 不改：与原 DAG 直出的 `ld_o_rb` 同（也无 MMO）；验证器只有「有 MMO ⇒ 必须 mayLoad」方向（`MachineVerifier.cpp:2382`），反方向无检查 ⇒ 保守 but 合法 | `grep MachineVerifier.cpp`：无「mayLoad ⇒ 必须有 MMO」断言 |
| F8（核过·关键机制）站点标签能否被 ELF writer 折成「section symbol + addend = 站点地址」（阶段 ①② 的接口约定） | ✅已核（成立） | 不改：`createNamedTempSymbol("pcrel_hi")` ⇒ 名字带 `MCAsmInfoELF` 的 `InternalSymbolPrefix = ".L"`、binding 默认 **STB_LOCAL** ⇒ `UseSectionSym` 分支命中 + `useSectionSymbol()`（非 ifunc/非 merge/`needsRelocateWithSymbol` 仅 ABS48）⇒ 折成 section symbol + `addend += getSymbolOffset(site)` | `MCAsmInfoELF.cpp:48`（`.L`）、`ELFObjectWriter.cpp:1360-1373`（折叠链）；lld 侧 `findPcrelHi` 用 `d->value + addend`（**两种形态都**得输入段内偏移） |
| F9（核过·非 finding）配对是否依赖「两条指令相邻」 | ❌不修（设计上不需要） | 不改：标签随 `rela.si` 走、LO 以符号引用站点 ⇒ 调度/重排/分离都不改变配对与硬件语义（`P` 恒为站点自身） | 代码注释（`InstrInfo.cpp` PCREL_LOAD 分支）+ 完成区「新发现⑥」 |
| F10（核过·非 finding）静态（非 PIC）路径是否回归 | ✅已核（按构造不回归） | 只改 `Reloc::PIC_` 两个分支与 `isPointerBankValue` 的**新增**条目；`GLOBAL_ADDR`/`JT_ADDR`/`SelectAddr` 等文本未动 | 全量 `git diff` 现场（ISel 仅 PIC 臂 + 注释 + 新增 case）；待构建后以字节级基线复核（遗留②(b)） |
| F11（核过·非 finding）本笔是否该改 `DADAOInstrInfo.td` / `gen-riii.s` | ❌不改（ISel 无 ISA 变更） | 只改 `DADAOCodeGen.td`（CodeGen-only 伪指令）⇒ ISA 面零变更 | `check-instrinfo` 156/156、`check_lit_gen` 64/0（`gen-riii.s` 未动） |
| F12（真值对齐自审）完成区/本表数字是否逐字来自真实输出 | ✅已核 | 每项可回溯：`.work/log/llvm/LLVM-095t-cd34-*.log`、`git -C .work/source/llvm-project diff --stat/--numstat 961e380ee 370ba9afe`、`make-patch` stdout；未构建、**未改 v5 `**状态**`**、未动 `spec/`·`.tao/contracts/`·`contracts/`·`tests/vectors/**`；组件树提交为 E1/E3 硬要求（披露于完成区「修改文件」） | 现场命令输出（日志同名）；`git status --porcelain` 复核 v5 改动面 = 组件补丁 9+7 份 + changelog + 任务书 + `gen-riii.s`（阶段 ①② 产物） |
| F13（自审发现·风格卫生）新注释引入 `±`（lld 该文件无先例）与 4 处超 110 列的注释行；PLT 报错文案混用 `` ` ``/`'` | ✅已修 | lld 注释统一为 `±`（与 DADAO 目标源一致：`DADAORegisterInfo.cpp` 既有先例）+ 重排至 ≤80 列；报错文案改 `<< &sym`（与文件既有 `<< rel.sym` 同形）；契约失败类别术语加引号标明出处（`"落点不符"`/`"越界"` + `contract-elf.md §3.2`） | 现场：`awk length>82` 空；`git diff` 复核仅注释/文案变化（语义零改动）⇒ 重导出后 `check-patch-tree` **rc=0**、组件树 `370ba9afe` clean |

**判决**：F1/F2/F13 已修；F3–F12 为「核过·非 finding」（附依据）；**无未修 finding**。阶段 ③④ 交付面（源码 + 补丁导出 + 门控）自审通过；**构建相关面（装配/反汇编、两条 `SHT_RELA`、PLT 12 B、GOT 2 条形态、矩阵重生成）须 `install-host` 后补验**（完成区「遗留②」清单）。按指令**不改 `**状态**`**。

#### 第 3 轮 engineer 自审（阶段 ② 补：跟名 `aip.si` + 单位=字节）

**自审方式**：自主逐行审查本轮 16 份补丁的全部新增/改动行（`.td` / AsmParser 换算与两条检查 / MCInstPrinter 打印 / MCCodeEmitter 名串与 imm 注释 / lld 文案 / 其余注释跟名）+ v5 侧 6 个文件（生成器、`gen-riii.s`、`aip-si.yaml`、`inventory.md`、`reserved.yaml`、新 lit 负例）+ 证据脚本 3 件；真值全部取自当次真实输出（门控日志、`run.sh --inject`、`check_mc.py` 输出、独立 oracle 脚本）。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·设计）首版把 `bytes >> 12` 放 `MCCodeEmitter`、范围检查放 AsmParser ⇒ **两处换算**，与既有 ×4 组（`jump`/`br.*` 在 parser 换算）不一致，且两处须永远同步 | ✅已修 | 改为 **parser 单点换算**（`matchAndEmitInstruction` 查 `%4096`/±512 MiB 后就地写回 `Encoded = bytes >> 12`），`MCCodeEmitter` 恢复原样（只加注释） | `check_mc` A14（断言换算串在 parser 段、emitter 无 `getImm() >> 12`）；`inject` 3 条 parser 变异真红 |
| F2（自审发现·卫生）改名后 3 处**注释列对齐**错位（`DADAOCodeGen.td`、`MCCodeEmitter` 的 `;`/`->` 列）+ lld 文案 `a \`aip.si\`` 语法错 | ✅已修 | 对齐补 1 空格；`a` → `an`（两处：`DADAO.cpp:196`、`:599`） | `python3` 列位核对（`aip.si`/`ld.o` 两行 marker 同列）；全量 `git diff` 复核 |
| F3（自审发现·证据侧）文档侧已把契约串改为 `aip.si` ⇒ `check_mc.py` A12 **基线假红**；`inject.py` 的 `("A4 td-rela-si")` 目标名陈旧 ⇒ 该注入「目标未命中」**假绿风险** | ✅已修 | A12 契约串改 `携配对信息指回 \`aip.si\` 站点`；A4/A8/A13 断言与注入目标名跟改；新增 A13–A17 与对应 10 条变异；基线期望 17/0 | 修前现场：`A12 FAIL`、`A4 td-rela-si` 注入 `目标命中=False`；修后 `check_mc --root .` ⇒ **17 passed, 0 failed**、`inject.py` ⇒ **25 passed, 0 failed** |
| F4（核过·非 finding）负值数学：`%`（截断除法）与 `>>`（算术右移）在 C++ 下对负数的行为是否与契约口径一致 | ✅已核 | 不改：`-4097 % 4096 = -1`（⇒ 判非 4096 倍数 ✓）；`-536870912 >> 12 = -131072`（下界 ✓）；与 `lld` 既有 `disp >> 12`、`br.*` 的 `ByteOff >> 2` 同口径 | 独立 python oracle：4 个负例的分支归属逐条核对（`1`/`4097`→ALIGN、`536870912`/`-537395200`→RANGE）；lit 负例 RUN 与之一致 |
| F5（核过·非 finding）符号路径是否被字节换算误伤（`%pcrel_hi(sym)` / 裸符号 / `%pcrel_lo(site)`） | ✅已核（未触碰） | 不加旁路：符号操作数为 `kImmediate` + 非空 `ImmExpr` ⇒ 本块**整体跳过**（`if (!DOp->getImmExpr())`），emitter 仍按 opcode/specifier 发 HI/LO | `check_mc` A14（含 `if (!DOp->getImmExpr())` 断言）；阶段 ② 的 A8/A9/A11 仍绿；`m6-ldst-symbol.s`/`rela-addend.s` 未改、字节未变 |
| F6（核过·非 finding）`getImmediateFieldKind` 对 `aip.si` 归 `None` 是否会漏掉 18 位域检查 | ❌不修（单点即可） | 本处已按 `Encoded ∈ [-131072, 131071]` 查（与 18 位有符号域**等价**）；归 `None` 避免对已换算值再报 `imms18` 误导文案（与 `br.*`/`jump`/`call` 同形） | `check_mc` A14（两条检查串 + `归类None`）；`inject` 变异 `Encoded > 131071 → > 999999999` 真红 |
| F7（核过·非 finding）仓内是否还有「块单位」正例未被跟改（会与字节受理冲突） | ✅已核（无残留） | 全仓 `grep` `aip.si`/`rela.si`（`tests/`+`tools/`+`contracts/`+`spec/`）⇒ 仅 `gen-riii.s`（已重生成 `aip.si rb8, 32768`，期望编码仍 `5a200008`）+ 新 lit 文件；`tools/qemu/min_rom_probe_009t.py` 的 `rela_si_rb()`（**qemu 模块**）已在完成区「遗留⑥」登记 | 门控 `check_lit_gen` rc=0；独立 oracle 核 `aip.si rb8, 32768` → `5a 20 00 08`（= 旧 `8` 块写法**逐字节相同**） |
| F8（真值对齐自审）完成区/本表数字是否逐字来自真实输出 | ✅已核 | 每项可回溯：`.work/log/llvm/LLVM-095t-*.log`、`run.sh --inject` 的 17 行、`check_mc.py`/`inject.py` 现场输出、`git diff --stat`；**未构建**、**未改 v5 `**状态**`**、未动 `spec/`·`.tao/contracts/`·`contracts/`；组件树本地 commit 为 E1/E3 硬要求（披露） | `bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **checks: 17 passed, 0 failed**、`RUN_EXIT=0` |

**判决**：F1/F2/F3 已修并复验；F4–F7 为「核过·非 finding」（附依据/等价性论证）；F8 真值对齐；**无未修 finding**。阶段 ② 补交付面（源码 + 补丁导出 + v5 生成物/向量/负例 + 证据脚本 + 门控）自审通过；运行期面（汇编/反汇编/负例诊断/矩阵重生成）**须 `install-host` 后补验**（完成区「遗留②」）。按指令**不改 `**状态**`**。

#### 第 4 轮 engineer 自审（阶段 ② 补：编译修复）

**自审方式**：自主逐行审查本笔 2 份改动（全部新增/改动行）+ 三组编译错的**根因**（用最小复现探针核对诊断语义）+ 全 DADAO 目标树（MC / CodeGen / AsmParser / Disassembler）与 `lld` 的「同类错」全量排查；真值取自当次真实输出（`ninja` 退出码、`-fsyntax-only` 逐 TU rc、注入探针、`make_patch` stdout、门控日志）。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·编译）`DADAOMCAsmInfo.cpp:80/82` 的 `OS << '%'`：**根因不是「char 打印写法」**，而是该 TU 未包含 `raw_ostream.h`（只有前置声明 ⇒ 成员 `operator<<(char)` 缺席；GCC 只列 `VersionTuple` 的 free operator）——自建最小探针（前置声明 + free `operator<<`）复现出**逐字相同**的诊断 | ✅已修 | 补 `#include "llvm/Support/raw_ostream.h"`（**不动**打印写法） | 该 TU `ninja` 编译 rc=0；注入 `#error` ⇒ rc=1 ⇒ `cp -p` 还原 ⇒ rc=0 + md5 三值一致 |
| F2（自审发现·编译）`dyn_cast<MCSpecifierExpr>`（`:174`）缺 include | ✅已修 | 补 `#include "llvm/Support/Casting.h"`（本树 `dyn_cast` 未弃用：`Casting.h:643`；先例 `MipsMCAsmInfo.cpp:16`） | 同上（TU rc=0；`check_mc` A8 仍断言到 `dyn_cast<MCSpecifierExpr>` + `getExprSpecifier` ×3） |
| F3（自审发现·编译）`MCOperand::getLoc()`（`:215/:227`）**该 API 不存在** | ✅已修 | 两处 → `Ctx.reportError(Expr->getLoc(), …)`（`MCExpr::getLoc()`，`MCExpr.h:86`）；**依据** = `MCFixup::getLoc()` 的实现即 `getValue()->getLoc()`（`MCAssembler.cpp:1178`）⇒ 与 `DADAOAsmBackend` 的 `Fixup.getLoc()` **同源**；文案与硬失败行为（`MCContext::reportError` ⇒ `HadError`）**未变** | TU rc=0；`inject.py` 24/24 目标命中；`run.sh --inject` ⇒ 17/0 |
| F4（核过·同类错排查）全树是否还有同类错（MCOperand 位置 API / 缺 include 的 `dyn_cast`·`raw_ostream` 用点） | ✅已核（无） | 不改 | `grep -rn "MCOp.getLoc" MCTargetDesc/{MC*,CodeGen,AsmParser,Disassembler}` 空；`dyn_cast` 另两处用户（`DADAOISelLowering.cpp`/`DADAOISelDAGToDAG.cpp`）经 CodeGen 头传递包含、编译已绿；12 个 TU `-fsyntax-only` 全 rc=0（含 `lld/ELF/Arch/DADAO.cpp`） |
| F5（核过·证据侧）既有证据脚本/注入目标是否因本笔改动失效（第 3 轮 F3 同类坑） | ✅已核（未失效） | 不改 | `bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **17 passed / 0 failed、`RUN_EXIT=0`**；`inject.py` 24 条目标全命中（`inject: 25 passed`，无一引用 `getLoc`/`reportError`） |
| F6（核过·测试手段可达 FAIL）本笔新造的检查手段（TU 语法检查）是否真能失败 | ✅已核 | 不改（检查脚本在 `/tmp/opencode/LLVM-095t/`，为一次性探针，不入仓） | 3 例注入：`#error` ⇒ 对应 TU rc=1（期望 1）；还原后 rc=0；`cp -p` mtime 保留 ⇒ `ninja -n` 不产生假脏（`.work/log/llvm/LLVM-095t-cdfix-inject-probe.log`） |
| F7（真值对齐自审）完成区/本表数字是否逐字来自真实输出 | ✅已核 | 每项可回溯：`.work/log/llvm/LLVM-095t-cdfix-{tu,ninja,syntax-only,inject-probe,check_*,make-check-L1}.log`、`make_patch` stdout、`git diff --stat 59ae0ac2f 2b17fa335`；**未跑** `install-host`/`build-*`/L2/L3、**未** commit/push v5、**未改** v5 `**状态**`/`spec/`/契约/`tests/**`；组件树本地 commit 为 E1/E3 硬要求（披露于完成区「修改文件」） | 上述日志现场输出 |

**判决**：F1/F2/F3 已修并复验（含注入可达 FAIL + 还原对账）；F4/F5/F6 为「核过·非缺陷」；F7 真值对齐；**无未修 finding**。阶段 ② 补（编译修复）交付面自审通过；**运行期面仍须 `install-host` 后补验**（完成区「遗留①」）。按指令**不改 `**状态**`**。

#### 第 5 轮 engineer 自审（阶段 ③④ 构建后验证）

**自审方式**：自主逐行审查本笔新增/改动的 5 件（`post_build.py` 新 700 行、`dadaoelf.py` 新 250 行、`run.sh` 全量重写、`README.md`、矩阵重生成 diff）+ 对**每条断言的恒真性**逐条反查 + 全量 `git diff`；真值取自当次输出（`run.sh`/`run.sh --inject`/`--inject-battery`/门控日志）。**发现 9 条 finding 全部当场修复并复验**，其中 4 条正是被 `--inject` 电池与「可达 FAIL」纪律捕获的**假绿**。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·**恒真断言**）`P5` 旧形态检测器 `range(len(pw)-3)` 在 3 字 `.plt` 上**永不进循环** ⇒ 断言恒真（禁恒真纪律） | ✅已修 | `range(len(pw) - 2)`；注入旧形态（`jump` + 0 字 + 8 字节常量）后须真红 | 修前：注入 P5 后 `P5` **未红**（`全部 FAIL=['P4…','P7…']`，假绿）；修后 `P5-plt-no-dataslot` **真红** ✓ |
| F2（自审发现·证据侧）`dadaoelf.py` 的 `patch-bytes`/`patch-reloc`/`drop-reloc`/`set-sec*` 的 CLI 参数序与 `sys.argv` **错位**（`KeyError`/写错对象） | ✅已修 | 四个命令的 `rest[]` 取值改为 `<in> <out> <sec> …` 顺序 | 逐命令实测：`relocs`/`syments`/`words`/`patch-bytes`/`patch-reloc` 全 rc=0 且产物可解析；N1/N2/N5 三例由「rc=0 假绿」转为 **rc=1 + 目标文案** |
| F3（自审发现·证据侧）`parse_bits` 把 `[hi:lo]` **读反**（`lo, hi = split`）⇒ `field_width` 负位移 `ValueError` | ✅已修 | 改为 `hi, lo = spec.split(':')`（与 ISA 表写法一致） | `signed_range` 得 `[-131072, 131071]`；E1/E4 的边界与文案随之成立 |
| F4（自审发现·证据侧）`-show-encoding` 的字节序：首版对字节列表做 `reversed` ⇒ 期望值错（`0x0800205a`） | ✅已修 | 大端 = 字节**顺序**拼接（`[0x5a,0x20,0x00,0x08] ⇒ 0x5a200008`） | E1 三例 `0x5a200008`/`0x5a21ffff`/`0x5a220000` 与规范派生值**逐例相等** |
| F5（自审发现·证据侧）`N1/N2` 注入改的是**记录 0（HI）**而非记录 1（LO）⇒ 对 LO 的畸形无效、`rc=0` **假绿** | ✅已修 | 按类别分索引：`lo-addend`⇒记录 1、`hi-addend`⇒记录 0、`opcode`⇒改指令字 | N1/N2 由 `rc=0` 转 **rc=1 + 悬空/指错文案**；`inject-battery` 目标命中=True |
| F6（自审发现·崩）`run_checks` 内 `Elf(str(work / …))` 引用未定义的 `work`（E11 抛 `NameError`） | ✅已修 | 改 `ctx["work"]` | 基线 `checks: 24 passed, 0 failed`（修前 rc≠0 崩溃） |
| F7（自审发现·**注入名不一致**）`build_subject` 判 `X1-DEFECT-pcrel-specifier`、检查名却是 `X1-DEFECT-specifier` ⇒ 注入**未生效**（假绿） | ✅已修 | 两处名称统一为 `X1-DEFECT-specifier` | 注入后 `X1` **真红**（`rc=0` ⇒ 断言不成立），`inject-battery` 目标命中=True |
| F8（自审发现·健壮性）`E7`/`E5` 未断言编译·剥节 rc；md5 读缺失文件会**崩**而非 FAIL | ✅已修 | 记录 `clang`/`objcopy` rc 并纳入断言；缺失即 `"缺失"` 参与比对；`E5` 纳入 `pic_o_rc==0` | E7 现断言「6/6 rc=0 且逐字节相同」；E5 现含编译 rc |
| F9（自审发现·孤儿/未测路径）`dadaoelf.py` 的 `drop_reloc` 本笔**无用户** + 未用常量 `SHT_SYMTAB/SHT_DYNSYM/SHN_UNDEF` | ✅已修（删） | 删 `drop_reloc` + CLI 分支 + 文档行 + 未用常量 | `py_compile` OK；全量 `run.sh` 仍 17/17 |
| F10（核过·补强）`E5`「无额外 `rd`」若只看自写解码，是否会被「`rd` 暂存」漏过 | ✅补第二视角 | 加 `llvm-objdump -d` 结构断言：`aip.si rbX, …` 后**紧跟** `ld.o rbX, [rbX, …]`、同行内无 `rd` | 实况 `'aip.si rb4, 0'`/`'ld.o rb4, [rb4, 0]'`（同 `rb4`、无 `rd`）；注入改 `rb` 后真红 |
| F14（自审发现·**静默跳过**风险）`P2–P8` 全在 `if so.exists():` 内 ⇒ 产物缺失时**整组静默消失**（假绿面） | ✅已修 | 新增显式守卫 `P0-elf-present`（产物存在 + `.plt`/`.got` 可解析）；`P7` 纳入第二次链接 rc | `P1` 注入现场：`FAIL P1-default-shared-rc` + `FAIL P0-elf-present`（`exists=False 链接 rc=1`）⇒ 跳过不再静默 |
| F11（核过·披露）`E1/E2` 的注入只能改**观测量**（编码/打印结果），不能改编码器（须重建） | ⏸不修（披露） | 脚本头 + 完成区「新发现④」明写：其余 22 条均为**被检对象侧**注入 | `E1/E2` 注入 rc=1 且目标真红；`E3/E4/E5/E7/E8–E11/P*/N*/X1` 全为对象侧 |
| F12（真值对齐自审）完成区/本表数字是否逐字来自当次真实输出 | ✅已核 | 每项可回溯：`.work/log/llvm/LLVM-095t-{post-build,inject-post,check-*,make-check}.log`、`run.log`/`run-inject.log`；**未** commit/push、**未** 重建、**未** 改 `spec/`·契约·`components/**`·`**状态**`（v5 跟踪面仅 2 份矩阵文件 = 重生成） | 上述日志现场输出 + `git status --porcelain -uall` = 28 项（其中本笔新增仅矩阵 2 份） |

**判决**：F1–F9、F14 已修并复验（F1/F5/F7/F14 均为**假绿面**，全部被「可达 FAIL」纪律当场捕获）；F10 已补强；F11 为**披露项**（不修）；F12 真值对齐。**无未修 finding**（`X1` 是**实现侧缺陷**、已登记为「遗留①」并说明须重建才能修——不在本笔授权内）。⇒ 阶段 ③④ 构建后验证面自审通过；按指令**不改 `**状态**`**。

### 构建后验证完成记录（本笔：`install-host` 后补验「遗留②」清单 (a)–(e) + 阶段 ③④ 证据扩面）

**测试结果**：`bash .work/evidence/LLVM-095t/run.sh` ⇒ **17/17，`RUN_EXIT=0`**；`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **19/19，`RUN_EXIT=0`**（两套注入均回绿）。其中：`check_mc`（阶段 ①②）17/0 不变、`inject.py` 25/0 不变；**新 `post_build.py`（阶段 ③④ 构建后）25/25**（含自审加固新增的 `P0-elf-present` 前置守卫）；`post_build.py --inject-battery` **27/27**（基线绿 → **24 条**逐条注入目标检查真红 → 还原回绿 + `RESTORE watched-md5` 9 项零改动）。日志：`.work/log/llvm/LLVM-095t-{check_mc,post-build,inject,inject-post,check-*,make-check}.log`。（自审 F1/F6 行的 `24 passed` 为**当时时点**真值；加 `P0` 后终值 25。）

**逐条实测**（真值 = 当次现场输出；（a）–（e) = 前笔「遗留②」清单）：**(a) 装配/反汇编**：`echo 'aip.si rb8, 32768' | llvm-mc --triple=dadao-unknown-elf -show-encoding` ⇒ `encoding: [0x5a,0x20,0x00,0x08]`（=`5a200008`，`field = 32768>>12 = 8`）、`-filetype=asm` ⇒ `aip.si rb8, 32768`（**按字节打印**，往返一致）rc=0；边界 `536866816`/`-536870912` ⇒ `5a21ffff`/`5a220000` 且 rc=0（**无误拒**）；负例两条 **rc=1** 且文案**逐字**为 `error: aip.si offset must be a multiple of 4096 bytes: the operand is a byte count (imms30) and the encoded field is a 4 KiB block (field = bytes >> 12)` / `error: aip.si byte offset out of range: expected [-536870912, 536866816] (imms30, %4096==0, +-512 MiB)`。**(b) 两条 `SHT_RELA`**：`-fPIC -c`（`extern int extg; int f(void){return extg;}`）⇒ `.rela.text` **两条**、类型 **`R_DADAO_PCREL_HI (14)` @0x10** + **`R_DADAO_PCREL_LO (15)` @0x14**；**独立核算**（自写 `dadaoelf.py` 解析符号表/节偏移/指令字，非从 lld 读回）：LO 的 symbol = `.text` 节符号（`index 2`、`value 0`）+ `addend 16` ⇒ **站点 = 0x10 = HI 记录的 `r_offset`**，站点字节 `op8 = 0x5a`（`aip.si`）、LO 站点 `op8 = 0x22`（`ld.o`）⇒ 配对成立。**(c) `-fPIC` 取址 2 条**：反汇编（`llvm-objdump`）为 `aip.si rb4, 0` + `ld.o rb4, [rb4, 0]` **共 2 条**、**同一个 `rb4`**（字节级复核 `rbha=4`/`rbha=rbhb=4`、两条相邻）、**无额外 `rd`**；**静态路径逐字节不回归**：6 例（`t.c`/`sw.c` × `-O0/1/2`，剥 `.comment`）md5 与改动前基线**全等**（`cdb0bcde…`/`beda13fc…`/`beda13fc…`/`cfb8b3a2…`/`513f7747…`/`513f7747…`）；**负对照**：改动前的单条 `REL12` 形态（`ld.o rb4, [rb0, .Lgot.0]`）在默认布局**必然越界**（`rc=1`、`R_DADAO_REL12 out of range: 65544 is not in [-2048, 2047]`，= `ISS-230` 根因）。**(d) 默认布局可链接（正面证据）**：`ld.lld -shared -soname lib1.so.1 lib1.o`（**不用** `tests/scripts/dadao-dyn.lds`）⇒ **rc=0**；`.got`=0x20310 对引用点 0x102e4 ⇒ **距离 +65580 > 2048**，且**解码落点 == `.got`**（`0x102e4 + 0x10000 + 44 = 0x20310`）。**(e) 4 类反例 + PLT + 不发射**：反例 5 例全 **rc=1**、文案逐字 —— 配对悬空 `R_DADAO_PCREL_LO points at offset 0x8 without an associated R_DADAO_PCREL_HI relocation`／指错站点 `pairs with relocation R_DADAO_PCREL_LO at the site; expected R_DADAO_PCREL_HI`／落点不符(hi) `R_DADAO_PCREL_HI is not at an \`aip.si\` site (opcode 0x5B)`／落点不符(lo) `R_DADAO_PCREL_LO is not at a paired \`ld.o\`/\`st.o\` site (opcode 0x21)`／越界 `relocation R_DADAO_PCREL_HI out of range: 196624 is not in [-131072, 131071]`（**手段**：以 `-fPIC` 产物为基、用自写解析器**手工改写** ①LO 配对 addend ②指令字 opcode ③HI addend，逐类构造）；`.plt` = `5a100010` `22104128` `71100000` ⇒ **3 条 / 12 B**、`size == 12 × n(.rela.plt) == 12`、**无数据槽**（旧形态 `jump` + 0 字 + 8 字节常量 0 命中）、`.rela.plt` 唯一类型 **7 `JUMP_SLOT`**；**幂等**两次链接 md5 相同（`1116157e54f8`）；**不发射**输出重定位表仅 `ABS48`/`JUMP_SLOT`（**无** 14/15 ⇒ 配对是链接期就地补丁）。

**修改文件**（v5 跟踪面 **2 份**：`tools/llvm/llvm-isa-backend-matrix.{tsv,md}` **重生成**，+212/−212 与 +188/−188；其余证据器在 `.work/**`、`git status` 不显示）：`.work/evidence/LLVM-095t/{post_build.py（新）,dadaoelf.py（新）,run.sh（扩到 17 个环节）,README.md（新）,baseline-static-nocomment.md5（新；= 改动前基线留档，md5 `ae8bbea3…`，与 `stage-A/stage-B` 两份**逐字节相同**）}`；本任务书。**未改** `spec/`/`contracts/`/`.tao/contracts/`/`components/**`/`**状态**`；**未** commit/push；**未** 重建（`ISS-229`）。

**验收结果**（各留自身 rc；日志同名）：**`check-isa-coverage` rc=0**（`gen_isa_coverage --check: PASS`；第①层 accept 225/reject 10、第②层 yes 86/no 149）——**已按新安装根重生成**，矩阵 `aip.si_riii_rb` 行现为 `accept`/`ok`/`aip.si rb8, 32768`（旧根不可能给出该度量 ⇒ **非**「旧根自洽假绿」），旧 `rela.si_riii_rb` 行消失；**`make check`(L1) rc=0**（末行 `repository checks (L1): PASS`，0 处 `Error`）；`check-patch-tree` rc=0（147 patches）/`check-index-blobs` rc=0（108+39）/`check-source-state` rc=0/`check-no-residue` rc=0/`check-tasks` rc=0/`check-knowledge-refs` rc=0/`check-component-changelog` rc=0/`check-issues` rc=0/`check-asm-list(-drift)` rc=0/`check-instrinfo` rc=0（156/156 M1）/`check_lit_gen` rc=0（64/0）/`validate-vectors` rc=0（156/156、0 gap）。**L2/L3 未跑**（按指令归主会话；`ISS-229`）。

**新发现/坑**：① **已在册缺陷（本笔发现，未修）**：`%pcrel_hi(...)`/`%pcrel_lo(...)` **汇编器解析不了**（`echo 'aip.si rb4, %pcrel_hi(extg)' | llvm-mc --triple=dadao-unknown-elf -filetype=obj` ⇒ `error: expected ')'`，**rc=1**；`ld.o rb4, [rb4, %pcrel_lo(.Lsite)]` 同）——根因 = `DADAOAsmParser::parseExprWithSpecifier`（`:566-578`）**检查** `(` 却**不消耗**，`parseParenExpression` 内的表达式解析遂把整个 `(...)` 吃掉、`parseRParen()` 在**下一个** token 上报错；后果 = ①手写 `%pcrel_lo` 不可汇编（**LO 记录无其它书写形式** ⇒ 手写 GOT/PLT 取址落不到 LO）②`clang -S` 的 `.s` **无法再汇编**（`t.s` 实测 rc=1）。② **改 MC / `.td` 后必须 `install-host`**：本笔全部运行期数字（含矩阵第①层）都只在**新安装根**上成立（`ISS-210`）。③ **判据面提醒**：本册 `post_build.py` 的 `N*` 反例是**按契约 §3.2 的四类失败面**构造、断言 `rc!=0` + **类别识别串**；识别串取自 lld 文案（逐字记录），**不是**行为 oracle —— 行为 oracle 是契约的「link-time error，禁静默」。④ **证据纪律**：`E1/E2` 的注入只能作用于**观测量**（编码/打印结果）—— 编码器行为须重建才能扰动，故其余 22 条均为**被检对象侧**注入（已在脚本头注明）。

**遗留问题**：① **`X1` 缺陷未修**（见「新发现①」）：修法 = 在 `parseExprWithSpecifier` 里 `getParser().Lex()` **消耗掉 `(`** 后再调 `parseParenExpression`（或直接改调 `parsePrimaryExpr`）⇒ 归**下一笔**（须 `install-host` 才能验证，本笔按指令**不重建**）；`post_build.py` 的 `X1-DEFECT-specifier` 把当前行为钉住，修复后该检查**翻红**以强制同步。② **L2/L3 未跑**（`check-lit`/`check-lit-full`/`check-interface`）：归主会话收尾（`ISS-229`）。③ 本册 `遗留问题（阶段 ③④）②` 的 (a)–(e) **全部补验完成** ✓（见上「逐条实测」）；`遗留①`（落点检查偏严，只认 `op ∈ {0x22,0x23}` 与 `0x5A`）**仍然**（现状失败响亮、非静默）。④ **`ISS-230`** 的 `resolved_by: LLVM-095t` 回填 + 消费侧（`INFRA-085t`）归主会话。

#### architect 提交留痕（LLVM-095t，分支 `llvm-095t-commit`；**只追加**）

- **档位**：按下发指令取 **正常提交**（无 `WIP:` 前缀）——**披露**：`#### 第 1 轮 reviewer 验收` 仍为占位（无 reviewer `Accepted` 判决），严格按角色规则应为 `WIP:`；本笔依主会话明确指令执行，**不改任务 `**状态**`** ✗（仍 `待开始`）。
- **提交**：① `4c92239` = 代码侧全链（**29 文件**：组件补丁 **17** + `components/llvm-project/changelog.md` + lit **2**〔`aip-si-imm.s` 新〕+ 向量 **3**〔`rela-si.yaml` 删 / `aip-si.yaml` 增 / `inventory.md` / `reserved.yaml`〕+ 矩阵 **2** + `tools/testcases/generate_lit_vectors.py` + 本任务书 + `milestones.md` 流水行）；② `586f791` = `ADR-0012` 更新（`adr-0012` / `adr-0003` / `adr-0028`）；③ 本留痕（1 文件）。`master` 由 `merge --ff-only` 落地、分支已删；`origin/master` 仍 `3fba2e4`（**未 push** ✗）。
- **文件集对账**（`git diff --cached --name-status` vs 完成区「修改文件」声明）：**逐项一致、0 漏提 / 0 多提 / 0 越界**；`rela-si.yaml` 的**删除**与 `aip-si.yaml` 的**新增**同时入 ✓；`spec/` / `.tao/contracts/` / `contracts/` / 任务 `**状态**` **0 命中** ✓；补丁 **17 份**（完成区分段声明 9+7+16 去重后 = 17；`series` 仍 **73**、无增删）。
- **门控（本笔重跑，真值 = 自身 rc）**：`make check`(L1) **rc=0**（末行 `repository checks (L1): PASS`、`Error` **0** 处 ⇒ **已回绿** ✓）、`check-patch-tree` rc=0（147）/`check-index-blobs` rc=0/`check-source-state` rc=0/`check-no-residue` rc=0/`check-tasks` rc=0/`check-knowledge-refs` rc=0/`check-knowledge-dir` rc=0/`check-component-changelog` rc=0/`check-isa-coverage` rc=0/`check_issues.py` rc=0（41 open/13 closed）；日志 `.work/log/llvm/LLVM-095t-{commit,final}-*.log`。
- **完成区如实性核对**：逐项与现场证据一致 ✓（矩阵 `git diff --stat` = `.md` **188** / `.tsv` **212** 行变更，与完成区数字同源；`make check` 现场日志末行 PASS 与完成区一致）；**遗留①**（`%pcrel_hi`/`%pcrel_lo` 汇编器不可解析）**如实登记** ✓；未做项（L2/L3）明标 ✓ ⇒ **未改完成区内容** ✓。
- **`ADR-0012` 更新**（用户明示）：`D5` 就地修订注记（含用户原话逐字）+ 术语附注（`PC` ⇒ `IP`；`IP` = 当前正在执行指令的地址）+ 陈旧指针（`ADR-0003` **3 处**、`ADR-0028` **1 处**，只加指针、原文不删）；**未新立 ADR** ✓；`spec/` / `contracts/` / `components/**` 未动 ✓。

### 遗留① 修复 完成记录（本笔：`%pcrel_hi(...)` / `%pcrel_lo(...)` 可解析 + `clang -S` **文本往返**）

**测试结果**：`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **22 PASS / 0 FAIL、`RUN_EXIT=0`**（新增 `x1_roundtrip.py` R1–R7 **7/0** + 其注入电池 **10/0**；既有 `inject.py` 25/0、`post_build.py` **25/0**〔X1 由「缺陷留档」翻为「已修」断言〕、`post_build.py --inject-battery` **27/0**；门控 / 矩阵 / L1 全绿。日志 `.work/log/llvm/LLVM-095t-x1-{run,run-inject,roundtrip,installroot,lit-pcrel-specifier,lit-inject,lit-restored}.log`）。
**往返锚（硬要求）**：`clang --target=dadao-unknown-elf -fPIC {-O0（load/store）,-O2（load）} -S` ⇒ `llvm-mc -filetype=obj` 再汇编 ⇒ 与直接 `clang -c` 比较：`.text` **逐字节相同**（3 例 md5 = `48d3678b6fd35fff3c5bfcbd16051e46`/`b079505c1df083092a8c0f5961b60dbd`/`48d3678b…`）、`.rela.text` **记录逐条相同**（`R_DADAO_PCREL_HI`(14) @`0x10` + `R_DADAO_PCREL_LO`(15) @`0x14`；LO symbol = `.text` 节符号、addend =站点 `0x10`）；`clang -S` 原文第 13 行 `ld.o rb4, [rb4, %pcrel_lo(.Lpcrel_hi0)]`（**修前该文本 rc=1**）。两半负例（缺 `)` / 缺 `(`）仍 rc=1 + 逐字文案。
**修改文件**（v5 跟踪面 **3 份**）：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（**1 份改**，`git diff --stat` = **+7/−2**，含 hunk 头与 index 行；`series` 仍 **73**、无增删）、`components/llvm-project/changelog.md`（+1 条）、`tests/llvm/lit/MC/DADAO/pcrel-specifier.s`（**新**，5 条 RUN = obj + readobj 结构断言 + `--show-encoding` 高半 + 2 条 `%not` 负例）。**`.work/**` 侧**（`git status` 不显示）：`x1_roundtrip.py`（新）、`post_build.py`（X1 翻转 + `--tc` 解析）、`run.sh`（`--tc`/工具目录解析 + `x1_roundtrip`/lit 两环节 + 第三套注入）、`README.md`。组件源树 **1 份改**（`DADAOAsmParser.cpp` = **+5 行**），按 `Process-01 §6.3/§6.4`（E1/E3 硬要求）收敛为 **base+1** 本地 commit（`ad9298251`、clean、**永不推送**）——**披露**：组件检出内执行了 `git add` + `commit --amend`；**v5 仓库零 `git add`/`commit`/`push`** ✓。
**验收结果**（各留自身 rc；日志同名）：`check-instrinfo` **rc=0（156/156 M1）**、`check_lit_gen` rc=0（64/0）、`validate-vectors` rc=0、`check-patch-tree` **rc=0（147 patches OK）**、`check-index-blobs` rc=0（108+39）、`check-source-state` rc=0、`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues` 均 rc=0、`check-isa-coverage` rc=0（**未动 `.td` ⇒ 矩阵不变**，与 `ISS-210` 无关）、**`make check`(L1) rc=0**（末行 `repository checks (L1): PASS`）；lit 单例（`LLVM_TOOLS_DIR` = 构建树）`PASS: DADAO-MC :: pcrel-specifier.s`，**可达 FAIL** = 删掉那行 `Lex()` ⇒ 重编译 ⇒ lit 红（`error: expected ')'`，RUN 行 1）⇒ `cp` 还原 + md5 三值一致 ⇒ 重编译 ⇒ 回绿。
**新发现/坑**：① **根因原文**：`parseExprWithSpecifier` 检查 `(` 却**未消耗**就调 `getParser().parseParenExpression()`，而该 API 契约原文 = 「Parse an arbitrary expression, **assuming that an initial `(` has already been consumed**」（`llvm/include/llvm/MC/MCParser/MCAsmParser.h:320`）⇒ 其内 `parseExpression` 把整段 `(...)` 当**带括号的主表达式**吃掉，`parseRParen()` 便在下**一个** token 上失败（`error: expected ')'`）；改法 = 检查通过后补 `getParser().Lex(); // consume '('`（与文件既有 `Lex()` 用法同形）。② **相邻缺陷（本笔发现，未修，已登记）**：`llvm-mc --show-encoding` 对**低半** `ld.o rbX, [rbX, %pcrel_lo(...)]`（`rbha ≥ 4`，即 `clang` 默认的 `rb4`）命中上游断言 `assert(Bit == 0 && "Encoder wrote into fixed up bit!")`（`MCAsmStreamer.cpp:134`）⇒ **SIGABRT**；根因 = `MCFixupKindInfo` 的 `{Offset 0, TargetSize 12}` 在**大端**下与该 streamer 的 **MSB-first** `FixupMap` 位序不符（映射落到 opcode/`rbha` 位）；**只影响该显示模式**（`-filetype=obj`/往返不受影响，已由 R6/R7 证明）；修法须动 `DADAOAsmBackend.cpp` 的 fixup 元数据表，而 `check_mc.py` A7（「字段宽 18/12」）与契约 `§2.2` 引用把它钉住 ⇒ 归下一笔 / 架构师裁定。③ **`cp -p` 还原会骗过 ninja**：注入后 `cp -p` 还原保留 mtime ⇒ 源文件比 `.o` **旧** ⇒ `ninja` 报 `no work to do`（**假绿**；实测 lit 仍红）⇒ 须 `touch` 源文件或清目标后再编译。④ **相对 `--tc` 会静默炸**（工具一律以 `cwd=<work>` 调用 ⇒ `FileNotFoundError`）⇒ 两脚本均 `.resolve()`。⑤ **lit 的 `%` 替换**：RUN 行里的字面 `%pcrel_hi` 会被 lit 的 `%p`（源目录）替换而**静默变形**⇒ RUN 行内须写 `%%pcrel_hi`（CHECK 行不受影响）。⑥ 证据口径：`run.sh` 工具目录按「**与补丁树同代**」优先**构建树**并**响亮打印**与安装根的 md5 差异（`ISS-210` 的镜像面：旧根度量 ⇒ 自洽假绿/假红）。
**遗留问题**：① **本项标记「待 `install-host` 后复核」**（本笔按指令**不**跑 `install-host`）：安装根 `llvm-mc`（md5 `873cfc591d7126b161d805e1b2584bf2`）仍是**修前**二进制 ⇒ 对安装根跑 `x1_roundtrip.py --tc .dadao/cross-toolchain/bin` **如实红**（R1/R2/R6/R7 = `expected ')'`；日志 `.work/log/llvm/LLVM-095t-x1-installroot.log`）——主会话 `install-host` 后应转绿（届时 `run.sh` 默认路径两者一致 ⇒ 直接全绿）。② 上述「`--show-encoding` 低半断言崩」**未修**（新发现②）⇒ 归下一笔或架构师裁定。③ L2/L3（`check-lit`/`check-lit-full`/`check-interface`）**未跑**（归主会话；`ISS-229`）。④ `ISS-230` 的 `resolved_by: LLVM-095t` 回填 + 消费侧 `INFRA-085t` **不变**（归主会话）。

#### 第 6 轮 engineer 自审（遗留① 修复：`%pcrel_*` 解析 + 文本往返）

**自审方式**：自主逐行审查本笔**全部**新增/改动（组件源 1 文件 5 行 + 新 lit 1 份 + 证据器 4 件〔`x1_roundtrip.py` 新写 ~330 行、`post_build.py` 的 X1 段与 `--tc`、`run.sh` 的参数/工具目录/两个新环节、`README.md`〕）+ 对照 `MCAsmParser.h` 的 API 契约原文与上游 `AsmParser::parseParenExpr` 实现；真值全部取自当次真实输出（`ninja` rc、lit rc、`x1_roundtrip`/`post_build` 的 PASS/FAIL 行、门控日志、`git diff --stat`）。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·**还原纪律**）注入后 `cp -p` 还原保留 mtime ⇒ 源文件比 `.o` 旧 ⇒ `ninja` 报 `no work to do`，lit 仍红而**误判为「还原失败」**（真因是没重编译） | ✅已修 | 还原后 `touch` 源文件再 `ninja`（并把这个坑写进证据 README） | 还原后 `ninja` **3 作业**（非 `no work to do`）⇒ lit **PASS**（`lit-restored.log`）；源文件 md5 三值 = `f9209f72…` |
| F2（自审发现·证据侧）`--tc` 传**相对路径**时工具以 `cwd=<work>` 调用 ⇒ `FileNotFoundError`（`post_build.py` 实测炸） | ✅已修 | 两脚本 `--tc` 一律 `Path(...).resolve()` | `post_build --tc .work/build/llvm/bin` ⇒ 25/0；`--tc /nonexistent` ⇒ fail-fast **rc=2** |
| F3（自审发现·lit）RUN 行内字面 `%pcrel_hi` 被 lit 的 `%p`（源目录）替换 ⇒ 文本变形、用例红 | ✅已修 | RUN 行内改 `%%pcrel_hi`（CHECK 行不动） | 误写时现场：`aip.si rb4, /mnt/…/DADAOcrel_hi(extg)`；修正后 lit **PASS** |
| F4（自审发现·**恒真风险**）若 `clang -S` 文本不再含 `%pcrel_lo(`，R6/R7 会退化为「两个从未用过说明符的对象互比」⇒ 假绿 | ✅已加（补强） | 新增 `R5-text-exercises-specifier`（不看语法即 FAIL）+ 对应注入 | 注入 R5（去掉说明符）⇒ R5 **真红**（`全部 FAIL=['R5…','R7…']`） |
| F5（自审发现·检查独立性）首版 R7 的注入与 R5 是**同一变异**（都不独立指向重定位记录） | ✅已修 | R7 注入改用**独立 ELF 改写器**（`dadaoelf.py`）只改 LO 配对 addend ⇒ `.text` 不变 | 注入 R7 ⇒ **仅** `R7-roundtrip-relocs` 真红（R6 保持绿） |
| F6（同步·非 finding）修好解析后，`post_build.py` 的 `X1-DEFECT-specifier`（钉住缺陷）会**假红** | ✅已修 | 翻为 `X1-specifier-readback`（断言两半均可汇编 + 记录 == 契约），注入名同步 | `post_build` 25/0；`--inject-battery` 27/0（`INJ X1…` 目标真红） |
| F7（核过·非 finding）`--show-encoding` 对低半（`rbha ≥ 4`）命中上游断言 `Bit == 0 && "Encoder wrote into fixed up bit!"` | ❌不修（登记） | 不动 `DADAOAsmBackend.cpp`（元数据被 `check_mc.py` A7「字段宽 18/12」与契约 §2.2 引用钉住 ⇒ 须裁定）；lit/证据脚本对低半改走 `-filetype=obj` + `readobj`，并在两处注明原因 | 触发条件实测：`rb1/2/3` 打印正常、`rb4/16` SIGABRT；`-filetype=obj` 产物与往返**不受影响**（R6/R7 绿） |
| F8（核过·非 finding）`_relocs()` 的 `Symbol:\s*(\S+)` 会把 `extg (2)` 截成 `extg`（节符号同理 `.text`） | ✅已核（正是所需） | 不改 | 现场 `llvm-readobj` 输出与 X1 断言逐项对照（`extg`/`.text`/addend `0x0`） |
| F9（核过·非 finding）是否须全量重建 / `install-host`？改动仅 AsmParser（无 `.td`） | ✅已核（不需要） | 只跑 `ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump LLVMDADAODesc LLVMDADAOCodeGen` ⇒ **rc=0**（3 作业：1 编译 + 2 链接；警告与既有同） | `check-instrinfo` 156/156、`check-isa-coverage` rc=0（未动 ISA 面） |
| F10（真值对齐自审）完成区/本表数字是否逐字来自真实输出 | ✅已核 | 每项可回溯：`.work/log/llvm/LLVM-095t-x1-*.log`、`run.sh --inject` 的 22 行、`git diff --stat`、`ninja` 日志；**未跑** `install-host`/`build-*`/L2/L3、**未** commit/push v5、**未改** v5 `**状态**`/`spec/`·`.tao/contracts/`·`contracts/`；组件树本地 commit 为 E1/E3 硬要求（披露于完成区「修改文件」） | 上述日志现场输出；`git status --porcelain -uall` = 3 项（补丁 1 + changelog 1 + 新 lit 1） |

**判决**：F1（还原纪律，**假绿面**）/F2/F3/F5/F6 已修并复验；F4 已补强（含可达 FAIL）；F7 为「核过·非 finding」的**新登记缺陷**（附触发条件 / 影响面 / 修法须裁定）；F8–F10 核过。**无未修 finding**。⇒ 遗留① 交付面（源码 + 补丁导出 + lit 回归锁 + 证据脚本 + 门控）自审通过；**安装根复核须 `make install-host` 后**（完成区「遗留问题①」，本笔按指令不跑）。按指令**不改 `**状态**`**。

### 新安装根复核 完成记录（2026-10-16；**只读**复核；**未**重建 / **未**改代码 / **未**改 `**状态**`）

**背景**：工具链已由主会话重建 —— `install-host` **PASS**、`INSTALL_EXIT=0`（`.work/log/llvm/QEMU-061t-install.log`：`start=2026-10-16 18:37:06` → `end=18:43:18`；`build-mc`/`build-lld`/`build-qemu`/`manifest validation` 均 PASS）。本块 = 对新安装根复核本册交付（QEMU 侧见 `QEMU-061t` 册同名块）。

**① 安装根新鲜度**（`ISS-210`；判据 = 安装根 mtime > max(组件补丁 mtime) **且** md5(安装根) == md5(同代构建树产物)）：

| 安装根产物 | mtime | md5 | 构建树同代产物 md5 |
|---|---|---|---|
| `clang` | 18:41:11 | `457f62b0…` | 相同（`457f62b0…`） |
| `llvm-mc` | 18:37:16 | `59f5b7f2…` | 相同（`59f5b7f2…`） |
| `lld`（`ld.lld`→`lld`） | 18:42:37 | `7413f669…` | 相同（`7413f669…`） |
| `qemu-system-dadao` | 18:35:19 | `a11b2a4e…` | 相同（`a11b2a4e…`） |

组件补丁 mtime：`DADAOAsmParser.cpp.patch` **18:08:32**（md5 `048ad8ad…`）、`insn.decode.patch` / `insn_trans/trans_arith.c.inc.patch` **18:21:27**（md5 `3418721f…` / `13fca19d…`）⇒ **四件安装根产物均晚于两批补丁** ✓ 且逐件与构建树产物 **md5 相等**（= 同代，非旧根度量）。**旧根对照**：18:12 同器对**旧根**记录 `llvm-mc md5 = 873cfc591d7126b161d805e1b2584bf2`（`.work/log/llvm/LLVM-095t-x1-installroot.log`）、旧 `qemu-system-dadao` 尺寸 `35062136`@10-15 21:59 ⇒ 现根为**新**二进制。

**② `%pcrel_*` 往返（新安装根）**：`bash .work/evidence/LLVM-095t/run.sh --tc .dadao/cross-toolchain/bin` ⇒ **20 PASS / 2 FAIL**（`.work/log/llvm/LLVM-095t-installroot-recheck.log`；`工具目录=.dadao/cross-toolchain/bin`、`llvm-mc md5=59f5b7f2…`）。**安装根相关检查全绿**：`x1_roundtrip` R1–R7 **7/0 rc=0**（对照 = 同器 18:12 对**旧根** **3 passed / 4 failed**：R1/R2/R6/R7 = `error: expected ')'` ⇒ 本笔**回绿**）、`post_build`（E1–E11/P0–P8/N1–N5/X1）**25/0 rc=0**、`lit pcrel-specifier.s` **PASS**、`check-isa-coverage` **rc=0**（新根度量：矩阵 `aip.si_riii_rb … accept ok aip.si rb8, 32768`、旧 `rela.si` 行 0）、`make check`(L1) **rc=0**（末行 `repository checks (L1): PASS`）。**唯一红 = `check_mc` A16**（静态期望、**与安装根无关**——该脚本只吃 `--root`，不读工具根）：A16 硬编码 6 个 `encoding.word`（含 `0x5A04FFFF`/`0x5AFCFFFF`），而 `QEMU-061t` 已按「word ↔ notes 声明的 `imms18` 不符」**订正**为 `0x5A07FFFF`/`0x5AFDFFFF`（`tests/vectors/isa/aip-si.yaml` Case 2/3 的「word 订正记（QEMU-061t）」）⇒ 期望**陈旧**。同因使 `inject.py` 的 `BASE baseline-copy` 1 条红（24 条定点注入**全命中**，其 `全部 FAIL` 列表均含 A16）。

**③ 独立复核（不复用既有判定）**：`bash .work/evidence/recheck-061t/run.sh` ⇒ **37/37 rc=0（`RUN_EXIT=0`）**、`--inject` ⇒ **45/45 rc=0**（`.work/log/recheck-061t/run.log` / `run-inject.log`；注入 = `/tmp` 临时副本变异 ⇒ 被检出 ⇒ 还原 ⇒ 回绿）。其中 `clang -fPIC {-O0,-O1,-O2} -S` ⇒ `llvm-mc -filetype=obj` vs `clang -c`：`.text` **逐字节相同**（`t_load` = `48d3678b6fd35fff3c5bfcbd16051e46` ×3；`t_ldst` = `e44b2f96434671bdc655146fdb8e8e4d`/`f2194f58fa7c514581a4c29e5708e89c`×2）且 `.rela.text` **逐条相同**（`R_DADAO_PCREL_HI(14)@0x10` + `R_DADAO_PCREL_LO(15)@0x14`；LO.symbol=`.text`、addend=`0x10` = 站点地址）。`aip.si` 端到端（新根）：汇编/反汇编**按字节往返**（`rb1,0`→`5a040000`、`rb8,32768`→`5a200008`、`rb63,536866816`→`5afdffff`、`rb1,-536870912`→`5a060000`，`llvm-objdump` 回原文）；`-fPIC` 取址 = `aip.si rb4, …` + `ld.o rb4, [rb4, …]` **2 条 / 同一 `rb4` / 无额外 `rd`**；**默认布局** `ld.lld -shared -soname lib1.so.1`（不用 `tests/scripts/dadao-dyn.lds`）**rc=0**；`.plt` **12 B** = 3 条（`aip.si rb4, 65536` / `ld.o rb4, [rb4, 296]` / `jump [rb4, rd0, 0]`），且 `0x10300 + 65536 + 296 = 0x20428` **==** `.rela.plt`（`JUMP_SLOT`）槽地址 ✓。

**④ `--show-encoding` 显示模式缺陷（如实复现，**不修**）**：低半 `ld.o rb4, [rb4, %pcrel_lo(.Lhi0)]`（`rbha ≥ 4`）⇒ `llvm-mc --show-encoding` **SIGABRT**（signal=6 / rc=134），文案逐字 = `MCAsmStreamer.cpp:134: … Assertion \`Bit == 0 && "Encoder wrote into fixed up bit!"' failed.`；`rb1` 同文本 **rc=0** 正常打印（含 `fixup … kind: DADAO_FK_PCREL_LO`）；`-filetype=obj` **不受影响**（产出 HI+LO 两条）⇒ 缺陷**只影响该显示模式**，判据未变（`check_mc.py` A7「字段宽 18/12」钉住元数据）⇒ 按裁定**不修** ✓（登记）。

**测试结果**：run.sh **20/2**（唯一类红 = A16 陈旧期望）、`recheck-061t` **37/37** 与 `--inject` **45/45**、`make check`(L1) rc=0。**修改文件**：**无**（本册交付文件一字未改；本笔只**追加**本块，并新增**只读**复核证据器 `.work/evidence/recheck-061t/run.sh` + `.work/evidence/recheck-061t/recheck.py`；日志 `.work/log/recheck-061t/run.log`、`.work/log/recheck-061t/run-inject.log`、`.work/log/llvm/LLVM-095t-installroot-recheck.log`、`.work/log/llvm/LLVM-095t-installroot-recheck-inject.log`）。
**新发现/坑**：**跨笔共享载体**（`tests/vectors/isa/aip-si.yaml`）上的「硬编码 6 个 `encoding.word`」会随另一笔的**合法订正**（field 派生）转红 ⇒ 该类期望值应改由 **field 派生**（如 `oracle_aip.py`）生成而非字面量，否则每次订正都须手改；**本笔不动他笔证据脚本**（越界）。
**遗留问题**：① `check_mc` A16 + `inject.py` `BASE baseline-copy` 陈旧（建议：A16 改 field 派生，或按订正更新那 2 个字面量并注明出处）⇒ 归**主会话 / 架构师裁定**，本笔**未改**（越界，附现场证据）；② `--show-encoding` 低半断言崩（同上，已登记，未修）；③ L2/L3 全卷（`check-lit`/`check-lit-full`/`check-interface`）本笔**未跑**（按指令只跑 QEMU 侧 L2/L3，见 `QEMU-061t` 册块）；④ **旧根不可重跑**（二进制已被 `install-host` 覆盖）⇒ 旧根红仅存留档日志（`LLVM-095t-x1-installroot.log`，`llvm-mc md5=873cfc59…`）。

#### 第 7 轮 engineer 自审（新安装根复核）

**自审方式**：自主逐行审查本笔新增的只读复核器（`.work/evidence/recheck-061t/recheck.py` ~380 行 + `run.sh`）与两册追加真值块；真值全部取自当次输出（`.work/log/recheck-061t/run.log`、`run-inject.log`、`.work/log/llvm/LLVM-095t-installroot-recheck.log`、门控日志）。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·**假红**）`plt_numbers` 用单条跨行正则匹配 `llvm-readobj -S` 的 `.plt` 段，而段头与 `Address:` 之间夹多行 `Flags` 块 ⇒ `size=-1/addr=0` ⇒ C10 假红 | ✅已修 | 改为「段头后逐行扫 Address/Size，遇 `}` 止」 | 修前 `C10 FAIL size=-1`；修后 `size=12 insns=3 hi=65536 lo=296 站点=0x10300 算出=0x20428 槽=0x20428` **PASS** |
| F2（自审发现·**假绿面**）`inj_c2` 注入后仍走 `rt_compare`，其内部**重跑 `clang -S`** ⇒ 注入被覆盖 ⇒ `same=True` 且**不报红**（首轮 `--inject` 43/1 即此） | ✅已修 | 注入后**直接** `llvm-mc` 汇编（不重生成），并 `assert 注入文本 != 原文`（防空注入）；基线/注入/还原三段各自独立比对 | `INJ C2`：未注入 same=True ⇒ 注入 same=**False** 且 relocs 不同 ⇒ 还原 same=True ✓ |
| F3（自审发现·**写死计数**）C6 期望条数原为字面量 | ✅已修 | 改 `count_cases(<向量文件>)` **现场统计**（`- class:` 条数，禁写死） | `total=12 passed=12 (文件 case 数=12)`、`reserved 3/3 (文件 case 数=3)` ✓ |
| F4（自审发现·**门控抓到的自伤**）真值块初稿用 `{,-inject}` / `{run.sh,…}` 花括号缩写引用 `.work/**` ⇒ `check-knowledge-refs` **rc=1** | ✅已修 | 全部改为显式路径 | 修前 rc=1（悬空 1 = `…-installroot-recheck`）；修后 rc=0；`make check`(L1) **rc=0**（末行 PASS、`Error` 0 处） |
| F5（核过·非 finding）独立复核的**判定不依赖既有脚本**（自写 `.text` 字节比对 + 自写 `.rela.text` 解析 + PLT 三条落点算式），旧根/新根差异由 md5/mtime 双条件判别 | ✅已核 | 不改 | C2/C3/C7/C8/C9/C10 全绿；`--inject` 三条注入实测可达 FAIL（C2/C7/C10） |
| F6（真值对齐）块内数字逐字取自当次输出：`20/2`、R1–R7 `7/0`、旧根 `3/4`、recheck `37/37` 与 `--inject` `45/45`、md5 全值 | ✅已核 | 不改 | 上述日志现场输出；`git status -uall` = 12 项（与开工同） |

**判决**：F1–F4 已修并复验（F2/F4 为**假绿/自伤面**，分别被「可达 FAIL」与「门控」当场捕获）；F5/F6 核过。**无未修 finding**（`check_mc` A16 = 他笔陈旧期望，已登记为遗留①，非本笔授权面）。⇒ 复核结论：**安装根新鲜度成立**（mtime + md5 双证）、`%pcrel_*` 往返对**新根回绿**（旧根 3/4 如实红）、`aip.si` 端到端四项通过、`--show-encoding` 缺陷**如实复现未修**、门控全绿。按指令**不改 `**状态**`**。

### 收尾遗留处置 完成记录（2026-10-16；按主会话裁定处置四条遗留；本册 = ① 的**实现面**）

**背景**：主会话裁定 —— ① 修 `check_mc` **A16**（改**按 field 派生**，**不**放宽断言）② `--show-encoding` **不动**（登记保持）③ `aip-si.yaml` 纳入 L2 代表集（`QEMU-061t` 面）④ **补跑全卷 L2/L3**。本册 = ①（证据侧实现）+ 全卷门控。⚠️ 全程**未重建**、**未** commit/push、**未改**任务 `**状态**`。（QEMU 侧详录见 `QEMU-061t` 册同名块。）

**① A16 改「field 派生」（**禁**字面量期望值）**：
- **改前现场红**：`check_mc.py` A16 硬编码 **6 个 `encoding.word`**（含已订正的 `0x5A04FFFF`/`0x5AFCFFFF`）**且**写死 `id/mnemonic == 6`（`QEMU-061t` 后 `aip-si.yaml` 实为 **12** 例）⇒ `check_mc --root .` = **16 passed / 1 failed**（`FAIL A16 vectors … id=12 mnem=12 words=[]`）。
- **改后四面（期望全部现场派生）**：`A16` 跟名（条数按 `len(cases)`）；`A16b` 编码 field 派生 —— 表级（`opcodes.yaml` **字段位域+掩码覆盖 32 位**、`encode(全零字段) == value`）+ 逐例（`encoding` 类 notes 的等价**汇编层字节**写法按 `Toolchain-01 §3.2/§5` 派生：须 4 KiB 倍数、域 `[-536870912, 536866816]`、`imms18 = bytes >> 12`，再经 `opcodes.yaml` 位域重算 word）；`A16c` `SimRISC-05 §3.4` 语义重算（`rb<rbha> = IP + (sext18(imms18) << 12)`，`IP = BINARY_BASE + 4*loader_words` 由 harness `build_test_binary.build_loader` **现场派生**，与 `expected_state` 比对）；`A16d` **位宽派生**极值覆盖（6 位 ⇒ `rbha{0,63}`、18 位 ⇒ `imms18{-131072,+131071}`）+ `dst_rb0` 规则（仅 legality 类可用 `rb0` 且须 ILLI）。**复用** = `post_build.py::{load_isa,encode,parse_bits}`（不另造表解析）。
- **结果**：`check_mc.py --root .` = **20 passed / 0 failed rc=0**；`inject.py` = **31/31 rc=0** = 基线（`checks: 20 passed, 0 failed`）+ **30 条**定点反例（原 24 + 新增 **6** 条：①Case 3 word 还原 `0x5AFDFFFF→0x5AFCFFFF` ⇒ `A16b` 红 ②Case 2 同法（多行 needle 去歧）⇒ `A16b` 红 ③Case 8 `expected_state` 扰动 ⇒ `A16c` 红 ④移走 `rbha=63` ⇒ `A16d` 红 ⑤Case 0 改用 `rb0` 作目的 ⇒ `A16d` 红 ⑥`opcodes.yaml` 的 `rbha` 位域缩窄 ⇒ `A16b` 表级红）。
- **可达 FAIL 演示（真实仓库，`cp` 备份 + md5 对账；**未**用 `git checkout`/`restore`/`stash`）**：Case 3 word `0x5AFDFFFF → 0x5AFCFFFF` ⇒ `check_mc` **rc=1**、`FAIL A16b vectors-decode … ['case[3] notes「aip.si rb63, 536866816」派生 word=0x5AFDFFFF ≠ 实际 0x5AFCFFFF']`；`cp` 还原 ⇒ `cmp` 逐字节一致 + md5 三态 `8249984794c2ad04b01f48a11b7f79de` ⇒ **rc=0、20/0**（日志 `.work/log/llvm/QEMU-061t-A16-inject-rerun.log` / `-restore-rerun.log`）。**旁证探针**（临时树，仓库零改动）：缺 `contracts/opcodes.yaml` ⇒ 显式异常 rc=1；缺 `tests/scripts/build_test_binary.py` ⇒ `A16c` 响亮 FAIL（19/1）——**不**静默跳过（`.work/log/llvm/QEMU-061t-A16-selfcheck.log`）。
- **连带同步**：`inject.py` 的 `REL` 补 `contracts/opcodes.yaml` + `tests/scripts/build_test_binary.py`（派生真源须在临时树副本内，否则基线假红）；`inject.py` 基线**去掉写死 `17 passed`**（改 `re.fullmatch(r"checks: \d+ passed, 0 failed")`）；`run.sh`/`README.md` 的注入标签改为**条数现场统计**（不再写「24 条」）。

**② `--show-encoding`（只复核登记、**不修**）**：登记文本与现状**逐条一致** —— ① 低半 `rb4`（`rbha ≥ 4`）`--show-encoding` ⇒ **SIGABRT rc=134**、文案逐字 `Assertion \`Bit == 0 && "Encoder wrote into fixed up bit!"' failed.`（`MCAsmStreamer.cpp:134`）；② `rb1` 同文本 ⇒ **rc=0** 且打印 `fixup … kind: DADAO_FK_PCREL_HI/LO`；③ `-filetype=obj` ⇒ **rc=0**、两条记录（`R_DADAO_PCREL_HI extg 0x0` + `R_DADAO_PCREL_LO .text 0x4`）⇒ 缺陷**只影响该显示模式**、判据未变（`A7`「字段宽 18/12」仍钉住元数据）⇒ **按裁定不修**、登记保持（日志 `.work/log/llvm/QEMU-061t-show-encoding-recheck.log`；install root `llvm-mc` md5 `59f5b7f2…`）。

**③ 全卷门控（真 rc/计数；本册面 = LLVM 侧 L2/L3 补齐）**：**L1** `make check` **rc=0**（31 s；末行 `repository checks (L1): PASS`）；**L2** `make check-modules` **rc=0**（94 s）—— 本册相关的 `check-lit` **109/109**（含 `pcrel-specifier.s` #27、`aip-si-imm.s` #108）、`check-interface`(INTEG-003t) 全 PASS、`check-qemu-smoke` 90/90；**L3** `make check-full` **rc=0**（64 s）—— `check-lit-full` **12/12**、`diff_ir_lli` **19/19**、`check-qemu-semantics` 149/149、`run_embench_e2e` 38/38。⇒ 本册原**遗留③（L2/L3 未跑）已消除**；`check-isa-coverage` 亦 **rc=0**（矩阵由新安装根度量，见 `run.sh` 环节 ④）。日志 `.work/log/qemu/QEMU-061t-L1-make-check.log`、`.work/log/qemu/QEMU-061t-L2-make-check-modules.log`、`.work/log/qemu/QEMU-061t-L3-make-check-full.log`、`.work/log/llvm/LLVM-095t-check-isa-coverage.log`。⚠️ 披露：`test-m6` 前置含 `install-host` ⇒ 顺带 `ninja: no work to do`（mc/lld 零编译）、`build-qemu` 仅 `qemu-version.h` ⇒ **零重编译**、安装根 md5/mtime 未变（**未重建**）。

**测试结果**：`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **22/22 rc=0**（`checks: 22 passed, 0 failed`；203 s；`check_mc` **20/0**、`x1_roundtrip` 7/0、`post_build` **25/0**、lit PASS、三套注入 `31/0`·`27/0`·`10/0`、`make check`(L1) rc=0、`check-isa-coverage` rc=0）。日志 `.work/log/qemu/QEMU-061t-runsh-final.log` / `-final2.log`、`.work/log/llvm/LLVM-095t-{check_mc,inject}.log`。失败原因：无。
**修改文件**：`.work/evidence/LLVM-095t/{check_mc.py,inject.py,run.sh,README.md}`（证据侧；`git status` 不显示）；本任务书 + `QEMU-061t` 册（**追加**本块与自审轮；**未改** `**状态**`）；`tests/scripts/run_qemu_smoke.py`（L2 载体，归 `QEMU-061t` 面）。**未改** `spec/`·`contracts/`·`.tao/contracts/`·`components/**`·`Makefile`·`tests/vectors/**`（后者仅他笔既有改动）。⚠ `git status -uall` = 13 项（开工 12 + `run_qemu_smoke.py`），无残留。
**验收结果**（门控；写块前/后各复跑一次，rc 与计数一致；日志 `.work/log/qemu/QEMU-061t-final-<gate>.log`）：`check-patch-tree` **rc=0（5 comp / 147 patches）**、`check-index-blobs` rc=0（108 new + 39 modification）、`check-source-state` rc=0（llvm-project clean）、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 悬空）、`check-component-changelog` rc=0、`check-issues` rc=0（41 open / 13 closed）。
**新发现/坑**：① **「同一笔的合法订正」会打红他笔的字面期望**：`QEMU-061t` 按 notes 订正 2 个 word 后，A16 的 6 个字面量与 `== 6` 计数**双双**陈旧 ⇒ 跨笔共享载体（`tests/vectors/**`）上的期望值一律**现场派生**（位域/notes/YAML 计数），并让派生新真源进注入器的复制清单。② **恒真面自查**：首版 A16b 的「位域重算 == word」在字段覆盖全 32 位时**恒真** ⇒ 改「表级（字段划分 == 掩码、`encode(全零)==value`）+ 逐例独立真源（notes 字节写法）」，并以注入 ⑥ 证明表级断言可红。③ **`make check-full` 的 `install-host` 前置**：源码未变 ⇒ `ninja: no work to do`；「未重建」须以 `ninja` 输出 + 安装根 md5/mtime 对账取证（不能只看目标名）。④ 原「`inject.py` 基线 `17 passed`」属**跨笔易碎期望**（补一条检查即假红）⇒ 已改为结构匹配。⑤ **任务书内 `.work/**` 引用须写显式完整路径**：本块初稿的「花括号 + 通配」缩写（`L{1,2,3}-*.log`）被 `check-knowledge-refs` 当场打红（rc=1 / 1 悬空）⇒ **同类坑 `QEMU-061t` 册已记过一次**（其第 2 轮 F4）；已全部改显式路径（rc=0）。
**遗留问题**：① `--show-encoding` 低半缺陷**保持不修**（登记；须动 `DADAOAsmBackend` 元数据，且被 `A7`/契约 §2.2 钉住）⇒ 归下一笔/架构师裁定；② L3 载体（`Makefile` `for v in …`）未含 `aip-si.yaml` ⇒ 登记待裁定（本笔按指令只扩 L2）；③ 本册原**遗留②（阶段 ③④ 构建后补验清单）已在「构建后验证完成记录」全部完成** ✓，`遗留①/③` 由本块处置（①=已修；③=已跑）；④ 按下发指令**未改任务 `**状态**`**（仍 `待开始`）。

#### 第 8 轮 engineer 自审（A16 派生化 + 全卷门控）

**自审方式**：自主逐行审查本笔证据侧改动（`check_mc.py` 的 A16/A16b/A16c/A16d 全量新增行 + 新增 helper `bits_of`/`sext`/`load_harness`；`inject.py` 的 `REL` 两项 + 6 条注入 + 基线判定；`run.sh`/`README.md` 标签）+ 对每条新断言的**恒真性/可达 FAIL** 逐条反查 + 临时树缺真源探针 + 全卷日志对账；真值取自当次输出（本卷 `subagent_depth=1` ⇒ 不另起子代理）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·**同源陈旧**）A16 除 word 字面量外还有 `id/mnemonic == 6` **写死计数**（实为 12 例）⇒ 只改字面量仍会红 | ✅已修 | 条数改 `len(cases)`（YAML 现场统计）；`inject.py` 基线改 `re.fullmatch(r"checks: \d+ passed, 0 failed")`；`run.sh`/`README.md` 标签去写死 | 修前 `id=12 mnem=12` ⇒ `FAIL`；修后 `check_mc` **20/0**、`inject` **31/0** |
| F2（自审发现·**恒真断言**）首版 A16b 的逐例「位域重算 == word」（字段覆盖 32 位时**恒真**） | ✅已修 | 拆为**表级**（字段划分 == 掩码 / `encode(全零)==value`）+ **逐例独立真源**（notes 汇编字节派生） | 注入 ⑥（`opcodes.yaml` `rbha` 位域 `[23:18]→[23:19]`）⇒ `FAIL A16b` **真红**（证表级面非恒真） |
| F3（自审发现·**静默弱化**）若 notes 里解析不到等价汇编写法就跳过 ⇒ 派生面悄悄失效 | ✅已修 | `encoding` 类**逐条必须**解析到（缺 ⇒ 记入 `dec_errs` ⇒ FAIL），并断言 `n_asm == n_enc > 0` | 现场 `encoding=5 解析到汇编写法=5`；注入 ①② 均 ⇒ `A16b` 真红 |
| F4（自审发现·**自包含面**）A16 新读 `opcodes.yaml`/harness ⇒ 临时树副本缺文件会假红或静默 | ✅已修（复制清单）+ ✅显式失败 | `inject.py` `REL` 补两项；缺 harness ⇒ `A16c` FAIL（**非** skip）；缺表 ⇒ 显式异常 | 基线副本 `checks: 20 passed, 0 failed`；缺 harness 探针 ⇒ `FAIL A16c … 缺 build_test_binary.py`、19/1 rc=1 |
| F5（自审发现·**还原纪律**）可达 FAIL 演示须在真实仓库做**注入→红→还原→绿**且不得用 `git checkout/restore/stash` | ✅已核 | 用 `cp` 备份 + `sed` 注入 + `cp` 还原 + `cmp`/md5 三态对账 | 注入 ⇒ rc=1 且 `A16b` 真红（诊断含 notes 派生 word 对照）；还原 ⇒ md5 `8249984794c2ad04b01f48a11b7f79de` 三态一致、rc=0；`git status -uall` = 13 项（无残留） |
| F6（核过·非 finding）A16c 用 harness `build_loader` 派生 IP 是否算「从实现反推」 | ✅已核（判据合规） | 不改：harness 布局 = **spec 侧**真源（`ADR-0004 R3` 内存图；向量文件头亦如此声明），`aip.si` 语义仍来自 `SimRISC-05 §3.4`；**不**读 QEMU/LLVM | 与 `QEMU-061t` 的 `oracle_aip.py` 同法（该册 reviewer/recheck 已接受）；A16c 对 6 条 semantic/boundary 逐条重算 == `expected_state` |
| F7（核过·非 finding）A16d 的极值集合是否「手工清单」 | ✅已核（位宽派生） | 不改：`{0, 2^w-1}` 由 `opcodes.yaml` 位宽算出（6/18 位），非人挑 | 现场 `rbha ⊇ {0,63}`、`imms18 ⊇ {-131072,131071}`；注入 ④/⑤ 分别使覆盖/`dst_rb0` 面真红 |
| F8（真值对齐自审）块内数字是否逐字来自真实输出 | ✅已核 | 不改：`16 passed / 1 failed`（修前）、`20/0`、`31/0`、`22/22`、`109/109`、`149/149`、`12/12`、`19/19`、`38/38`、rc/耗时/`ninja: no work to do` 均可回溯至同名日志；**未** commit/push、**未**重建、**未改** `spec/`·契约·`**状态**` | 上述日志现场输出 |
| F9（自审发现·**门控抓到的自伤**）本块初稿用 `QEMU-061t-L{1,2,3}-*.log` 花括号+通配缩写引用 `.work/**` ⇒ `check-knowledge-refs` **rc=1（1 悬空）** | ✅已修 | 改为**显式三条路径**（`QEMU-061t` 册同处同步改） | 修前 `结果: FAIL (1 悬空 .work/** 引用)`（落点本册 `:344`）；修后 **rc=0**（0 悬空） |

**判决**：F1–F5、F9 已修/已核并复验（F1/F2/F3/F4 均为「写死 / 恒真 / 静默弱化 / 假红」面，逐条被可达 FAIL 与临时树探针捕获；F9 为**门控当场捕获的自伤**）；F6–F8 核过。**无未修 finding**。⇒ 四条遗留本册面**处置完成**：A16 **field 派生**（`20/0`，含「注入 ⇒ 红 ⇒ 还原 ⇒ 绿」）、`--show-encoding` 登记复核一致且**不修**、L2 载体（`QEMU-061t` 面）、全卷 L1/L2/L3 **真 rc=0**。按指令**不改 `**状态**`**。
