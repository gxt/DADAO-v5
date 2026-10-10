# LLVM-072t: 跳转表 `br_jt` lowering【G3】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

> **覆盖缺口**：**G3（`ISS-177`）**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象**：`Cannot select: t4: ch = br_jt t2:1, JumpTable:i64<0>, t2>`（`llc` rc=134）——**`-O0` 即触发**（非优化级专属）。
- **最小复现**：`switch(x)` 含 16 个 case（含 fallthrough 全分支）→ `clang`/`llc` rc=134。
- **定性**：DADAO 后端**无 `ISD::BR_JT` / `JumpTable` 的 lowering**（跳转表未实现）⇒ 密集 `switch` 分发不可编译。
- **命中基准**：picojpeg / qrduino。
- **性质 = 缺能力（编译期显式失败，非静默）**。

**证据指针**：`.work/log/testcases/TESTCASES-039t-stage1-gaps.md §G3`；issue `ISS-177`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）。
  - `.tao/knowledge/contract-isa.md`（间接跳转 / 相对寻址相关指令，如 `br`/`jump` 族；如有 `jump` 表基址+偏移形态）；`.tao/knowledge/contract-elf.md`（数据段/重定位，跳转表落在数据段的方式）——**以 `spec/`/`contracts/` 为准，不从实现反推**。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **`br_jt` lowering**：为 `ISD::BR_JT` 实现 lowering（跳转表落数据段 + 间接跳转；参考既有目标的做法，按 DADAO ISA 能力选择实现），使密集 `switch` 可编译。
  2. 如需新增 `DADAOISD` 节点/模式或改 `DADAOISelDAGToDAG`/`DADAOCodeGen.td`/`DADAOISelLowering.{h,cpp}`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `spec/`/`contracts/`（**不从实现反推**，Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯后端能力补全 ⇒ 无新决策、无需 ADR（若实现引入**新的 reloc/段语义**，须停下报告、提请 ADR）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-072t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-072t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-072t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`br_jt` 可编译**：最小复现（`switch` 含 16 个 case，`-O0`）经 `clang`/`llc` **rc=0**（给真实命令 + rc）。
2. **`switch` 语义正确（E2E）**：至少覆盖「命中各 case / `default` / fallthrough」的 `switch` 程序经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
3. **真实基准**：picojpeg / qrduino **至少一个**经 `-O0` 编译 **rc=0**（给真实命令 + rc）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
5. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-072t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（改跳转表基址/偏移 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：门控全绿——`make build-mc`/`check-patch-tree`/`check-lit`/`check` 均 EXIT=0（`check-lit` **81/81**＝基线 80＋本任务 1；`check-source-state` HEAD `6049aa15e` count=1 clean；`check-instrinfo` 157 defs）。证据脚本 `.work/evidence/LLVM-072t/run.sh` 默认 `RUN_EXIT=0`（checks=10 failed=0）；`--inject` `RUN_EXIT=0`（注入⇒2 项 FAIL⇒`cp`+md5 还原⇒重建⇒回绿）。

**修改文件**（`series` 仍 71；组件源树 HEAD `6049aa15e`=base+1 clean）：7 份补丁 `components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.h,DADAOISelLowering.cpp,DADAOCodeGen.td,DADAOISelDAGToDAG.cpp,DADAOInstrInfo.td,DADAOInstrInfo.cpp,DADAOMCInstLower.cpp}.patch`、`components/llvm-project/changelog.md`、`tests/llvm/lit/CodeGen/DADAO/br-jt.ll`(A)、`tests/e2e/switch_jt_e2e.c`(A)、本任务书；证据（gitignored）`.work/evidence/LLVM-072t/run.sh`。

**验收结果**（真实命令 + rc；缺口原话 `ISS-177`：`Cannot select: t4: ch = br_jt t2:1, JumpTable:i64<0>, t2`，-O0 即触发）：
- ① 最小复现（switch 16 case，-O0）：`clang -target dadao-unknown-elf -O0 -c` **rc=0**（改前 rc=1 / backend 70，同一 `Cannot select … br_jt`）；`llc -march=dadao -O0` rc=0。
- ② 语义 E2E：`tests/e2e/switch_jt_e2e.c` clang→ld.lld→QEMU **exit=255 == 手算 255 == 宿主 cc oracle 255**（命中各 case／越界与低于范围 default／fallthrough 链 0→1→2、3→4）。
- ③ 真实基准 `-O0`：`qrduino/qrencode.c` **rc=0**、`picojpeg/libpicojpeg.c` **rc=0**（跳转表**张数口径** = 数 `.LJTI*` **标签**：`grep -c '^\.LJTI[0-9_]*:' <obj>.s`；注意 `grep -c '\.LJTI'` 计的是**行**（1 标签 + 3 片基址引用 = 4 行），**行数≠表数**）：qrduino **1** 张、picojpeg **14** 张；`-O2` 亦 rc=0）。
- ④ 实现：`ISD::BR_JT`=Custom → `LowerBR_JT` → `DADAOISD::BR_JT`；`Select` 发 `JT_ADDR`(表基址, ABS48 3 片) / `shl.uo rd,rd,3` / `add.o rb,rb,rd` / `ld.o rb,[rb,0]` / `jump [rb,rd0,0]`；表落 **.rodata**（`.quad .LBB`→`R_DADAO_ABS48`）；`jump_rrii` 加 terminator/indirect；`MCInstLower` 处理 `MO_JumpTableIndex`。
- ⑤ `git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
- ⑥ 证据脚本注入（`DADAOISelDAGToDAG.cpp` 条目偏移 `3`→`2`）⇒ `lit_brjt`/`switch_e2e` FAIL（guest=140）⇒ `cp`+md5 还原（`3c76a24…`相等）⇒ 重建 ⇒ 回绿。
- ⑦ `git status --porcelain -uall` 仅本任务改动（7 补丁 + `changelog.md` + 任务书 + 2 新增测试）；无 `_tmp/_orig/_rej`。

**新发现/坑**：① 非 PIC（Reloc::Static）下 `getJumpTableEncoding()` 默认 `EK_BlockAddress`（8B 绝对地址）⇒ `.quad`→`ABS48`，正好复用 LLVM-065t 的 ABS48（数据 8B 字段），**无新 reloc/段语义、无需 ADR**。② `TargetLoweringObjectFileELF::shouldPutJumpTableInFunctionSection` 默认 **false** ⇒ 表落 `.rodata`（`.p2align` 不进可执行段），**避开 `ISS-182`**，本实现不需要在代码段对齐。③ 表基址须物化入 GPRB 且符号为跳转表局部标签 ⇒ 新增 `JT_ADDR` 伪指令（同 `GLOBAL_ADDR` 的 ABS48 3 片）+ `MCInstLower` 加 `MO_JumpTableIndex`→`GetJTISymbol`。④ `jump_rrii` 直接加 terminator/indirect 属性（CodeGen 唯一用途即此间接跳转），MC/汇编路径（`jump [rbN,rdM,imm]`）字节不变（lit 81/81 绿）。

**遗留问题**：返工处置（reviewer 第 1 轮 Needs Revision，仅完成区③笔误，免重建/免改码）**✅已修**：原「4/14」的 `4` 系把 `.LJTI` **行数**（1 标签 + 3 片基址引用 = 4 行）当**表数**；实测 qrduino **1** 张 / picojpeg **14** 张（口径 `grep -c '^\.LJTI[0-9_]*:' <obj>.s`，现场统计）。已自查其它计数（`check-lit` 81/81、157 defs、`series` 71、7 补丁、ABS48 3 片、16 `.quad`），均非「行数当表数」，无同类误。`ISS-177` 实现面收口；台账归主会话。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：`DADAOISelLowering.{h,cpp}`、`DADAOCodeGen.td`、`DADAOISelDAGToDAG.cpp`、`DADAOInstrInfo.{td,cpp}`、`DADAOMCInstLower.cpp`、`br-jt.ll`、`switch_jt_e2e.c`、`run.sh`。**核对**：Spec-first（`contract-isa.md §8.3` `jump rb,rd,imm12`＝`rb+rd+(imm<<2)`；跳转表项＝指针大小 8B 绝对地址，`EK_BlockAddress`）、防造假（真实命令+rc、注入可达 FAIL 且 `cp`+md5 还原、无 `tee`）、边界（仅动 `components/llvm-project/**`+`tests/**`+本任务书）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `getMachineNode` 无 4-操作数重载（jump_rrii 需 rb/rd/imm/chain） | ✅已修 | 改用 `SmallVector<SDValue,4>` + `ArrayRef` 重载 | 首次构建报 `no matching function`；改用后 build rc=0 |
| F2 `jump_rrii` 作 MBB 终止子须 `isTerminator/isBarrier/isIndirectBranch`（否则 BranchRelaxation 后 RA 视作 fall-through） | ✅已修 | `.td` 加 `isBranch=1,isTerminator=1,isBarrier=1,isIndirectBranch=1`（`isUnconditionalBranch` 因 `isIndirectBranch=1` 恒 false ⇒ 不会误入 `getBranchDestBlock`） | E2E 255；lit `branch-fold-two-way.mir` 绿；MC `jump [rb8,rd9,96]` 仍绿 |
| F3 表基址符号是跳转表局部标签、非 Global | ✅已修 | 新增 `JT_ADDR` 伪指令（`unknown:$sym`）+ `MO_JumpTableIndex` 处理 | `llvm-readobj -r` 显示 `.rela.text` 3 条 `R_DADAO_ABS48 .LJTI0_0` |
| F4 `.p2align` 落可执行段会崩（`ISS-182`） | ✅已证无 | 依赖 ELF TLOF 默认把表放 `.rodata`，未在代码段对齐 | `check_table_in_rodata`：`.rodata` 前无 `.p2align`；16 `.quad` |
| F5 证据脚本基线 bench 缺 `-I embench_include` | ✅已修 | `EB_CF` 加 `-I $INC` | 修前 qrduino `fatal error: 'string.h'`；修后 10/10 PASS |
| F6 `check-instrinfo` 读 `.td` patch 的 def 解析（`let … in`） | ✅已证无 | 未新增 def、仅加属性；`def jump_rrii :` 仍在行首 | `make check` 的 `check-instrinfo`：157 defs、orphan/format PASS |

**判决**：finding 全部处置，无未修项 ⇒ 状态置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**快照**（开工对账基准）：`git status --porcelain -uall` = 任务书 + 7 补丁 + `changelog.md` + `tests/e2e/switch_jt_e2e.c`(??) + `tests/llvm/lit/CodeGen/DADAO/br-jt.ll`(??)，与完成区「修改文件」声明**一致**；`changelog.md` md5 `9460fa35…`、`run.sh` md5 `354406c1…`。源树 `.work/source/llvm-project` HEAD `6049aa15e`（base `6dfe1677a`+1）status 0 dirty。

**文件分析**：逐行读 7 份补丁 delta（`/tmp/opencode/LLVM-072t-review/delta-patches.txt`）——`LowerBR_JT` 操作数序 (chain, JumpTable, Index) 与 ISD 约定一致；`Select` 展开 JT_ADDR→`shl.uo …,3`→`add.o`→`ld.o …,0`→`jump [rb,rd0,0]`；`jump_rrii` 语义 `Addr = rbha+rdhb+(imms12<<2)` 对 `contract-isa.md §8.3`（762-763 行）核对**一致**；表项 `.quad`→`R_DADAO_ABS48` 数据 8B 字段对 `contract-elf.md` §2–§4（76/109/117/144 行）**一致** ⇒ 无新 reloc/段语义、无需 ADR ✓。`series`=71。

**① 最小复现（独立，`/tmp/opencode/LLVM-072t-review/r-min.c`，16 case 200..215）**：
`clang -target dadao-unknown-elf -O0 -ffreestanding -c r-min.c` **rc=0**（改前 rc=134 `Cannot select … br_jt`，ISS-177）。结构（自算核对）：
- 分发序列：`shl.uo rd4, rd4, 3`（索引 **×8** ✓）；`set.zw rb4, wp0, .LJTI0_0` + `or.w rb4, wp1/2, .LJTI0_0`（表基址 3 片 ABS48 ✓）；`add.o rb4, rb4, rd4`；`ld.o rb4, [rb4, 0]`（取 **8B** 表项 ✓）；`jump [rb4, rd0, 0]`（末端**间接跳转**，`§8.3` Addr=rb+0+0 ✓）。
- 表落**数据段**：`.section .rodata,"a",@progbits` + `.p2align 3` + 16×`.quad .LBB0_x`；`llvm-readobj -S`：`.rodata` Size=**128**=16×8、Align=8 ✓；`llvm-readobj -r`：`.rela.rodata` 16×`R_DADAO_ABS48` @0x0,0x8,…,0x78（步长 8 ✓）+`.rela.text` 3×（基址 3 片）✓。可执行段无 `.p2align`（ISS-182 规避 ✓）。

**② 语义（独立重点，`r-sem.c`，与工程师向量不同取值/不同 min-case）**：`clang→ld.lld→QEMU`，手算：f(x) case 5..20 = x²+7（f(5)=32/f(13)=176/f(20)=407）、**低于最小 case** f(4)=-1、f(-100)=-1、f(21)=-1、内边界 f(6)=43/f(19)=368、fallthrough g(0)=7(0→1→2)/g(1)=6/g(3)=24(3→4)/g(2)=4、g(4)=16（不落 case5）/g(15)=32768/g(16)=1000 ⇒ 8 位全置 ⇒ **手算 exit=255**。
真实输出：`QEMU r-sem exit=255`（== 手算 ✓）；加权 probe（1+3+5）`QEMU probe exit=9`（== 手算 9 ✓，排除恒定输出）。`r-sem.s` 含 `.LJTI0_0`/`.LJTI1_0` 两表 + 2 条间接跳转 ⇒ f/g 均走跳转表路径 ✓。

**③ 真实基准（独立）**：`clang -target dadao-unknown-elf -O0 … -c embench-iot/src/qrduino/qrencode.c` **rc=0**、`… -c src/picojpeg/libpicojpeg.c` **rc=0**（均 `-O0`，真实 rc，err 为空）。两目标确实走了跳转表：qrduino 1×`.LJTI3_0`、picojpeg 14×`.LJTI*`（`llvm-objdump -t` 计符号数）。
⚠ **数字不符（非判据项）**：完成区③「各含 **4**/14 张跳转表」中 qrduino 的 **4 不实**——实测 qrencode.c 跳转表 **1 张**（`grep -c '^\.LJTI' qrduino.s` = 1；`grep -c '\.LJTI' qrduino.s` = **4 行**=1 表×(标签+3 片基址引用)，疑为把行数当表数）；picojpeg **14 张**属实。判据 3 本身（rc=0）通过，但完成区数字须更正为「1/14」（或注明计数口径）。

**④ 不回归（一次一个 `make`，各自独立 rc）**：
- `make check-patch-tree` rc=**0**：`3 component(s), 109 patches OK`。
- `make check-lit` rc=**0**：`Total Discovered Tests: 81`、`Passed: 81 (100.00%)`、Unsupported/Unresolved **0**；`PASS: DADAO-CodeGen :: br-jt.ll (36 of 81)`（本任务新向量确在内）。
- `make check` rc=**0**：`repository checks: PASS`（内含 `check-instrinfo`：`.td instr defs: 157`，与完成区 157 一致；`check-index-blobs: 82 new-file patch(es) OK`）。
- `make build-mc` rc=**0**：`ninja: no work to do.` + `build-mc: PASS`（增量、无重建）。
- `check-source-state`：`llvm-project: OK HEAD=6049aa15eb80 count=1 clean=True`（base+1 clean，与声明一致）。

**⑥ 补丁纪律**：`series`=**71** 行；`check-patch-tree`（109 OK）= 一文件一补丁 + 断言全绿；`check-index-blobs` 82 new-file 补丁 hash 重算 OK（非空 blob 卫生）；`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → **无输出**（rc=1）✓；`git status --porcelain -uall` 仅本任务 11 项（7 补丁+changelog+任务书+2 新增测试）✓；`_tmp/_orig/_rej` 扫描（排除 .work）**无残留** ✓。

**⑤ 证据脚本 + 独立注入**：
- **脚本审核**：10 项检查逐条有可达 FAIL 路径（`bad()` 分支），计数现场统计（`n/4`、`nq .quad`、`grep -c`）非写死，无恒真/两支同果；无 `tee`，rc 直取；注入用 `cp`+md5，未用 `git checkout/restore/stash`。合格。
- **重跑（基线）**：`bash .work/evidence/LLVM-072t/run.sh` **rc=0 / RUN_EXIT=0，checks=10 failed=0**（含 `switch_e2e guest=255 == hand 255 == host oracle=255`、19 ABS48、16 .quad）。
- **独立注入（与工程师「Scale 3→2」不同锚点、不同缺陷类：`DADAOISelDAGToDAG.cpp` 表项**读取偏移 0→4**，破坏 8B 表项步长）**：`cp` 备份 + md5 `3c76a24c9808c4a705afd150c6885e02` → 注入（assert 唯一锚点）→ `git diff --name-only` 非空（1 文件）→ `setsid nohup ninja … llc clang` 重建 **EXIT=0** → 重跑**同一脚本**：**rc=1 / RUN_EXIT=1，failed=3**——`lit_brjt FAIL (FileCheck rc=1)`、`switch_e2e FAIL (guest=140 != 255)`、`source_tree_clean FAIL`（注入痕迹本身）⇒ FAIL 路径真实可达、fail-closed。
- **还原**：`cp` 回 + md5 对账 `3c76a24c…` == 注入前快照（相等）；`git -C .work/source/llvm-project status|wc -l` = 0（clean）→ 再重建 **EXIT=0** → 重跑同一脚本：**rc=0 / RUN_EXIT=0，failed=0（回绿）** ✓。

**收尾快照对账**：`git status --porcelain -uall` 与开工快照**逐行相等**（唯一变化 = 任务书本审阅记录写入，预期）；`changelog.md` md5 `9460fa35…`、`run.sh` md5 `354406c1…`、7 补丁 + 2 测试 md5 全部与开工相等（未越界改动）；注入全程 `cp`+md5，未动 git 索引。

**约束核验**：临时目录 `/tmp/opencode/LLVM-072t-review/` ✓；只审不改（改动仅限本审阅记录 + 临时注入已还原）✓；未切分支（`LLVM-072t`）✓；未用 `git checkout/restore/stash`/`git show>` ✓；无 `tee`/`| tail` 接管退出码 ✓；构建 `setsid` 脱离 + 完成标记 ✓；`spec|contracts` 交集空 ✓；无 `.p2align` 进可执行段（ISS-182 规避）✓；语义/期望值独立派生（手算 oracle，非实现反填）✓。

#### 判决（第 1 轮 reviewer）

**Needs Revision（仅 1 处文档数字，无需重建、无需改代码）**。

- **通过项（自跑全绿）**：验收 1（r-min.c 16 case `-O0` rc=0 + 表落 `.rodata`/8B/×8/间接跳转全中）、验收 2（独立语义 `exit=255==手算 255`、probe `9==手算 9`，含**低于最小 case**/越界/±1/fallthrough）、验收 3（picojpeg **rc=0**、qrduino **rc=0**）、验收 4（`check-patch-tree`/`check-lit` 81/81/`check`/`build-mc` 全 rc=0）、验收 5（交集空）、验收 6（`RUN_EXIT=0` + 独立注入 FAIL→还原→重建→回绿）、验收 7（无残留）。
- **唯一失败项（硬约束「完成区与真实输出逐条对齐」）**：完成区③「各含 **4**/14 张跳转表」**与真实输出不符**——`grep -c '^\.LJTI…:' qrduino.s` = **1 张**（`llvm-objdump -t` 亦 1；`-O2` 同为 1），而 `grep -c '\.LJTI' qrduino.s` = **4 行**（1 表 × 标签+3 片基址引用）⇒「4」系**行数误作表数**；picojpeg 14 张属实。同一括注内两种口径混用，属未对齐真实输出的数字。
- **返工要求（一行）**：把完成区③括注更正为实测口径，如「qrduino 1 张 / picojpeg 14 张（`grep -c '^\.LJTI' *.s`）」；不涉及代码/补丁/门控，无需重建。
- **采信未独立复核**：「改前 rc=1/backend 70」（历史态，须回滚重建才能复现，成本高）；run.sh `--inject` 模式自身的「2 项 FAIL」声明（我以独立注入替代，同两检查 FAIL 已实证）。设计层无阻断问题。

#### 第 2 轮 reviewer 验收（极轻量，只核打回项）

**① 独立计数（自编自数，`/tmp/opencode/LLVM-072t-review2/`）**：`clang -target dadao-unknown-elf -O0 -ffreestanding … -S` 重编 qrduino/picojpeg 均 **rc=0**（err 空）。两种口径各数一次：`grep -c '^\.LJTI[0-9_]*:'`（**标签**）qrduino=**1**（`.LJTI3_0`）、picojpeg=**14**（14 个互异标签各 ×1）；`grep -c '\.LJTI'`（**行**）qrduino=**4**、picojpeg=**56**（=14×(1 标签+3 片基址引用)）⇒ 完成区③「qrduino 1 张 / picojpeg 14 张」+ 口径括注（`'^\.LJTI…:'`=表数、`'\.LJTI'`=行数、1 表=4 行）**属实**，「4 系行数误作表数」的更正成立。

**② 只改了任务书**：`git status --porcelain -uall` 与第 1 轮结束快照（`/tmp/opencode/LLVM-072t-review/snap-post.txt`）`diff` **rc=0 逐行相等**（11 项不变）；7 补丁 `git diff` 与第 1 轮 `delta-patches.txt` `cmp` **rc=0**（md5 `dda1c6c3…` 双等）；`changelog.md` md5 `9460fa35…`、`run.sh` md5 `354406c1…` 与快照**相等**；mtime：产物/补丁/测试均 ≤16:32、第 1 轮结束 17:27（`snap-post.txt`），仅任务书 17:29（返工）⇒ 返工只动任务书 ✓。

**③ 无同类（抽 4 个计数）**：`series`=**71** 行 ✓；7 补丁文件齐（ls 计 **7**）✓；16-case 复现重编 `r-min.s`：`.quad\t.LBB0_x` **16** 条 ✓；`llvm-readobj -r r-min.o`：`R_DADAO_ABS48 .LJTI*` **3** 条（表基址 3 片；全表 19=16+3 ✓）⇒ 均非「行数当表数」类误，其余计数无同类失实。

**④ 边界**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → **无输出**（rc=1）✓；`_tmp/_orig/_rej` 扫描（排除 `.work`）+ `git status` grep 均**无命中**（rc=1）✓。

**约束核验**：临时目录 `/tmp/opencode/LLVM-072t-review2/` ✓；只审不改（唯一改动=本审阅记录）✓；未切分支（`LLVM-072t`）✓；无 `git checkout/restore/stash`/`git show>`/`tee`/`| tail` 接管 ✓。第 1 轮全量验收（验收 1–7 + 独立注入 FAIL→还原→回绿）通过项继续采信，本轮未重跑（按主会话「极轻量」指令，仅核打回项与同类风险）。

#### 判决（第 2 轮 reviewer）

**Accepted**——打回项（完成区③「4/14」）已更正为实测「1 张 / 14 张」并注明口径，独立计数核属实；返工仅动任务书、无产物被改、无同类计数失实、边界干净。设计层无阻断问题。
