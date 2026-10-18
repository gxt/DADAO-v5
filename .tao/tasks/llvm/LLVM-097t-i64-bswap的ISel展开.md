# LLVM-097t: `i64 = bswap` 的 ISel 展开（解 `P2` 阶段 A1 的 `-O1` 以上出口判据）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-096t`（`P2` 阶段 A1 的 4 项阻塞已解；其完成区「新发现/坑 1」+「遗留问题 ①」= **本册来源**）、`INFRA-085t`（**登记源 + 消费方**：阶段 A1 出口判据）、`ISS-222`（③ 条）/`ISS-193`（(c) 条）（`.tao/knowledge/issues.yaml` 现场证据真源）；`SPEC-142t`（`rev.{o,t,w,b}` 已落地 = `ADR-0012 D10`；语义真源 `contract-isa.md §6.4.3`、编码 A.8）；`ADR-0019 D10`/`D12`（类型集冻结，**不改**）；纪律 = `ISS-229`（禁并发）、`ISS-210`（改 `components/**` ⇒ 单跑 `install-host`）、`docs/Process-01`（组件补丁树）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（**先读**）

- 来源 = `LLVM-096t` 完成区「新发现/坑 1」+「遗留问题 ①」：④（VLA）修好后，`ldso/dynlink.c` 的 `-O2` 编译停在**另一个既存缺口**；architect 2026-10-17 立项（主会话裁定：该缺口**阻断** `INFRA-085t` 阶段 A1 的 `-O1` 以上出口判据 ⇒ 从 `INFRA-079t` 大排期中**提前抽册**）。
- **现场签名（本笔独立复现，2026-10-17）**：`fatal error: error in backend: Cannot select: t26: i64 = bswap t20`，DAG 片段 `t20: i64,ch = load<(load (s32) from %ir.scevgep582, !tbaa !112), anyext from i32> t0, t11, undef:i64`，`In function: map_library`。
- **档位（本笔实测，四档同签名）**：`-O1` / `-Og` / `-Os` / `-O2` **均 rc=1**；`-O0` rc=0（`LLVM-096t` 证据 S4.1）。⇒ 「`-O1` 以下可过」**不成立**，只有 `-O0` 过。（musl 构建档 = `config.mak` 的 `CFLAGS_AUTO` = `-O2 …`；`tools/infra/build_musl.py` 的编译探针 = `-O1` ⇒ **两档都被本缺口挡住**。）
- **非 `LLVM-096t` 引入**：`-emit-llvm` 前后 **diff 0 行**（其完成区已留证）⇒ 既存缺口。
- **根因（本笔读源码定位到机制，`file:line` 为 LLVM 23.1.3 检出）**：DADAO 只注册 `i64`（`DADAOISelLowering.cpp` 的 `addRegisterClass(MVT::i64, …)`）⇒ **i32 `bswap` 由类型 legalizer 提升**；`DAGTypeLegalizer::PromoteIntRes_BSWAP`（`llvm/lib/CodeGen/SelectionDAG/LegalizeIntegerTypes.cpp:665-691`）**仅当** `!isOperationLegalOrCustomOrPromote(ISD::BSWAP, i64)` 时才提前调 `TLI.expandBSWAP`，否则走 `SRL(BSWAP i64(Op), 32)` 回退；DADAO **未给 `BSWAP` 设 action ⇒ 默认 `Legal`** ⇒ 回退分支留下 `i64 = bswap`，而 DADAO **没有** i64 BSWAP 的 ISel pattern ⇒ `Cannot select`。
- **故语义 = `bswap32`（不是 `bswap64`）**：该节点是 i32 `bswap` 提升后的形态，且下游是 `SRL 32` ⇒ 对外可观测结果 = `(u64)bswap32(x)`（低 32 位 = 4 字节反转、高位 0）；提升中间值的 `i64` 高 32 位由 `anyext` 未定义 ⇒ **oracle 必须按 4 字节反转算**（只断言低 32 位，或断言 `SRL 32` 之后的值），按 8 字节算会假绿/假红（见「做 ③」）。
- **参照实现（现场读源码，同为「目标无该指令 ⇒ Expand」）**：Mips `setOperationAction(ISD::BSWAP, MVT::i32/i64, Expand)`（`MipsISelLowering.cpp:399-401`）；RISCV `setOperationAction(ISD::BSWAP, XLenVT, hasREV8Like() ? Legal : Expand)`（`RISCVISelLowering.cpp:449-450`）；AArch64 标量 `Expand`（`AArch64ISelLowering.cpp:1476-1478`）；展开体 = `TargetLowering::expandBSWAP`（`TargetLowering.cpp:11510`，i32 = 4×移位/与/或；i64 = 8×）。
- **ISA 侧能力已在（但本册不一定用）**：`rev.o rdHB, rdHC, immu6`，`k=8` ⇒ `bswap64`（`contract-isa.md §6.4.3`；编码 A.8 = `op 0x40` / `opx 001-100` / `value 0x40300000` / `mask 0xFFFC0000`）。

## 目标

让 `i64 = bswap`（及其来源的 `bswap32` 提升路径）**有合法 lowering** ⇒ `ldso/dynlink.c` 在 **`-O1` 以上四档 rc=0** + 真实 musl 构建档 `dynlink.lo` rc=0，从而解 `INFRA-085t` 阶段 A1 的 `-O1` 以上出口判据。

**默认路线 = `Expand`**（最小改动、与 Mips/RISCV/「无 rev8」同款，语义由 LLVM 通用 `expandBSWAP` 保证）；**可选 = Custom → `rev.o`(k=8)**（代码更优；若选，须按「做 ③ 路径 B」加独立指令面 oracle 并显式 zero-extend，完成区须写明理由）。**两者皆可交付**，但验收口径不同、不得混写。

## 接口规范

- **输入**：本册「立项来源」的现场签名与根因；`contract-isa.md §6.4.3`（`rev.o` = bswap64 的语义与 `k=8`）；`DADAOISelLowering.cpp.patch` 现状（`CTTZ`/`CTLZ`/`CTPOP` 的 `Expand` 块紧邻处）；只读：`.work/source/llvm-project/**`（源码检出）、`.work/source/musl/**`（消费侧复现源）。
- **输出**：
  1. **组件补丁**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（**一文件一补丁**、`docs/Process-01`；`check-patch-tree` 机械校验）+ `series`（若新增文件则同步，**本册预期不改 series 计数**：只改既有补丁）+ `components/llvm-project/changelog.md`（`Process-01 §10` 体例）；
  2. **证据**：`.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项打印「检查名 + 期望/实际 + rc」、任一失败非零退出、含 `--inject` 可达 FAIL）+ 原始输出落 `.work/log/llvm/<任务ID>/`；
  3. 本册完成区（≤30 行）+ `.tao/knowledge/milestones.md` 流水行（收尾归 `/complete`）。
- **约束**：**最小改动**；**不得**改 `spec/`、`contracts/`、`.tao/contracts/**`；**不得**新增/改重定位类型（`ADR-0019 D10` 冻结）；**不得**改 musl 源（锁条目 `patchless` 保持；本缺口是**生产者侧**）；组件源一律 **git 基线**（只经 `patches/**` 交付，**不得**直接改 `.work/source/**` 作为交付）；期望值**独立**、**不从 LLVM/本仓工具反推**。

## 做

### ① 复现（现状 rc=1；四档同签名）

```sh
# workdir = 仓库根；<TC> = 安装根 cross-toolchain/bin（本笔用 .work/build/llvm/bin，同一二进制来源）
M=.work/source/musl
INC="-I$M/arch/dadao -I$M/arch/generic -I$M/obj/src/internal -I$M/src/include \
     -I$M/src/internal -I$M/obj/include -I$M/include"
for O in -O1 -Og -Os -O2; do
  <TC>/clang --target=dadao-unknown-elf -ffreestanding -nostdinc $INC \
    -fno-stack-protector -fPIC -fno-unwind-tables -fno-asynchronous-unwind-tables \
    -ffunction-sections -fdata-sections -w $O -c \
    -o /tmp/opencode/LLVM-097t/dynlink$O.lo $M/ldso/dynlink.c
done
```

- **现状**：四档均 **rc=1**，首行 `fatal error: error in backend: Cannot select: t26: i64 = bswap t20`、`In function: map_library`。
- **对照**：`-O0` **rc=0**（`LLVM-096t` 证据 S4.1/S4.2b）⇒ 断言非恒真。

### ② 修法（默认 `Expand`，一处 action）

在 `DADAOISelLowering.cpp` 的 `DADAOISelLowering::DADAOISelLowering` 内、既有 `CTTZ/CTLZ/CTPOP → Expand` 块**紧邻处**加：

```cpp
  // `bswap` (ISS-222 ③ / ISS-193(c)).  The ISA implements a 64-bit swap as
  // `rev.o rd, rs, 8` (ADR-0012 D10 / SimRISC-04 §6.4.3), but the generic
  // expansion (Mips/RISCV-without-rev8 style) already bottoms out in the
  // shift/and/or ops this backend selects, so mark i64 BSWAP `Expand`:
  // without an explicit action it defaults to `Legal`, DAGTypeLegalizer then
  // promotes i32 bswap to `SRL(bswap i64, 32)` (LegalizeIntegerTypes.cpp
  // PromoteIntRes_BSWAP) and ISel aborts with "Cannot select: i64 = bswap".
  setOperationAction(ISD::BSWAP, MVT::i64, Expand);
```

- **可选（Custom → `rev.o` k=8）**：须在 `DADAOTargetLowering::LowerOperation`/`ReplaceNodeResults` 里 Custom 化，并**显式 zero-extend** 后发 `rev.o`（k=8）；选它必须在完成区说明，且走「做 ③ 路径 B」的 oracle。
- **导出**：只改 `.work/source/llvm-project` 的**工作树**、`git diff` 导出为补丁（`docs/Process-01 §6.3/§6.4` 收敛 base+1 单 commit）；**重 build + `install-host` 由本任务单跑一次**（申报预计 **≈5–10 min**，参照 `LLVM-091t` 实测 `install-host` 5 min；`JOBS=8`、**禁**全核、**禁**与任何 L2/L3 并发 —— `ISS-229`；改后端 ⇒ 安装根必须新鲜 —— `ISS-210`）。

### ③ 验收

1. **四档 rc=0**：`-O1` / `-Og` / `-Os` / `-O2` 编译 `dynlink.c` **均 rc=0**、日志中 **0** 处 `Cannot select`；`-O0` 保持 rc=0。
2. **真实构建档**：`make build-musl-shared`（或等价：musl `CFLAGS_AUTO` = `-O2`）中 `obj/ldso/dynlink.{o,lo}` **rc=0**（修前 rc≠0；**只核该目标**，全量共享库仍有 `ISS-242`/`ISS-240`/`ISS-241` 之外的登记项 ⇒ **不要求** `libc.so` 整体可链，见「不做项」）。
3. **独立 oracle（端序敏感，必做；期望值独立算）**：
   - **路径 A（Expand，默认）**：语义 = `bswap32`（4 字节反转；来源 = i32 提升 + `SRL 32`；`i64` 中间值高 32 位 `anyext` 未定义 ⇒ **只断言低 32 位**，或断言 `SRL 32` 后的值）。写法二选一（自证独立即可）：
     a. 对 `.ll`/DAG 不可得时，用**自写 Python 指令级模型**：从 `llvm-objdump -d` 取该函数中 bswap 展开出的 `and/or/shl/srl` 链，按指令语义逐条求值；
     b. 或对**同一探针源**（`unsigned f(unsigned x){return __builtin_bswap32(x);}`）断言展开后的指令链结构 + 值级模型。
     期望值 = **独立手写** `bswap32`（`int.from_bytes(v.to_bytes(4,'big'),'little')`，**不调用 LLVM**）。**输入集必须覆盖端序敏感值**：`0x01020304`、`0x000000FF`、`0xFF000000`、`0x00FF00FF`、`0x80000000`、`0xFFFFFFFF`、`0xA5A5A5A5`（大端/小端结果不同 ⇒ 误用 LE 语义或块序错必红）。
   - **路径 B（Custom → `rev.o`）**：`llvm-objdump` 断言**恰一条** `rev.o rd, rs, 8`（k=8 = bswap64，`contract-isa §6.4.3`），且其操作数已 zero-extend；期望值 = **64 位**反转（高 32 位 = 0），输入集同上（按 8 字节扩展）。
   - **禁**：期望值取自 LLVM/LLD/QEMU/本仓工具；用 8 字节口径断言路径 A（会假红/假绿）。
4. **不回归**：① `install-host` 后 `make check`（L1）rc=0；② 既有 `LLVM-096t` 证据的「非 VLA、非 bswap」探针对象 md5 不变（`strlen`/`memcpy`/`atoi` 三例，值见 `.work/log/llvm/LLVM-096t/evidence-run.log`）；③ `check-patch-tree`（**仍 150**，本册只改既有补丁）、`check-instrinfo`、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身**真实 rc；禁 `cmd | tee` 吞码）。
5. **可达 FAIL**：`--inject` 至少 2 条 —— (i) 把该 `setOperationAction(BSWAP, i64, Expand)` 注释掉（或改 `Legal`）⇒ 断言「四档 rc=0」**FAIL**（`Cannot select: i64 = bswap` 复现）⇒ `cp` 备份 + md5 对账还原 ⇒ 回绿；(ii) 路径 A：把指令级模型里的移位量改成 8 的错块序（或把期望值换成 8 字节口径）⇒ oracle FAIL ⇒ 还原 ⇒ 回绿；路径 B：(ii') 把 `k=8` 改 `k=4` ⇒ oracle FAIL ⇒ 还原 ⇒ 回绿。**禁恒真断言**；**禁** `git checkout`/`restore`/`stash` 还原（`cp` + md5 或临时树）。

## 不做项（显式）

1. **`INFRA-079t` 的其余 6 类接入点**（i128 除法·FP↔i128·`*_PARTS`·原子·f16·compiler-rt 库）✗ —— **排期仍在整个动态链接测试之后**，本册**不改该排期**。
2. **`rotl`/`rotr` 的 ISel 选择** ✗（`ISS-222 ③` 的另外半边；现场不阻断 `dynlink.c` ⇒ **不并入**本册；若本册现场发现新触发面，**登记后转出**，不顺手扩范围）。
3. **`ISS-242`/`ISS-240`/`ISS-241`/`ISS-222 ④` 的后续面** ✗（`INFRA-085t` 范围）；**`libc.so` 整体可链** 不作为本册判据。
4. **运行验证 / `qemu-user` / 三套测试集**（`P3`/`P4`）✗ —— 本册判据 = **能编 + 静态可核**，完成区**不得**出现「运行通过」叙述。
5. **改 `spec/`、`contracts/`、`.tao/contracts/**`** ✗；**新增/改重定位类型** ✗（`ADR-0019 D10` 冻结）；**改 musl 源/锁条目** ✗。
6. **`L2`/`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 验收标准

1. 「做 ①」四档 rc=0 + 「做 ③ 2」真实构建档 `dynlink.{o,lo}` rc=0。
2. 独立 oracle（**端序敏感**、按所选路径的**正确字节宽度**）全绿；**可达 FAIL** 每条断言可证。
3. 构建纪律：改 `components/**` ⇒ **单跑一次** `install-host`（申报耗时、`JOBS=8`、不并发、`ISS-210`）；组件源 base+1 单 commit、`check-source-state` rc=0。
4. 不回归（「做 ③ 4」逐条）；门控各留自身 rc=0。
5. 完成区与真实输出逐条对齐（≤30 行）；`milestones.md` 流水行更新（收尾归 `/complete`）。

## 完成区

**测试结果**：`.work/evidence/LLVM-097t/run.sh` **28/28 PASS / 0 FAIL**（默认档）；`--inject no-action` **9/9**、`--inject model-shift8` **3/3**、`--inject expect8byte` **3/3**（三条注入均「预期 FAIL → `cp`+md5 还原 → 回绿」，同一次前台执行内闭合）。
**修改文件**：组件检出 `llvm/lib/Target/DADAO/DADAOISelLowering.cpp`（base+1 amend，md5 `d22dbbb3…`）；`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（重导出，1 份；hunk `+1,1276`→`+1,1288`）；`components/llvm-project/changelog.md`（+1 条）；证据 `.work/evidence/LLVM-097t/{run.sh,bswap_model.py,bswap32.c,regress-096t/*.o}`。`series` 未改（仍 76）。**未碰** A1 的 4 项。
**验收结果**：`ninja -C .work/build/llvm -j8 clang lld` **rc=0**（3m59s）。四档 `dynlink.c` rc：**-O0 0 / -O1 0 / -Og 0 / -Os 0 / -O2 0**，`Cannot select` **0** 处（修前 -O1/-Og/-Os/-O2 全 rc=1 + `Cannot select: t26: i64 = bswap t20`；-O0 rc=0）。musl 真实配方 `make obj/ldso/dynlink.{o,lo}`（`CFLAGS_AUTO=-O2`，CC=构建树 clang）**rc=0**。端序 oracle（期望=手写 4 字节反转，输入集取册内 7 值）`-O2`/`-O1` 各 **7/7**：`01020304→04030201`、`000000FF→FF000000`、`FF000000→000000FF`、`00FF00FF→FF00FF00`、`80000000→00000080`、`FFFFFFFF→FFFFFFFF`、`A5A5A5A5→A5A5A5A5`（low32）。回归：strlen/memcpy/atoi `-O2 -fPIC` 对象剥离 `.comment` 后与 `LLVM-096t` 基线**逐字节相同**（整对象 md5 变化仅因 `.comment` 内嵌组件 commit hash）。门控各留自身 rc=0：`check-instrinfo`（0 errors）/ `check_lit_gen`（64 passed, 0 failed）/ `check-patch-tree`（**150 patches OK**，5 组件现场统计）/ `check-index-blobs`（111 new-file OK）/ `check-source-state`（llvm-project `HEAD=e60970302e57 count=1 clean=True`）/ `check-no-residue` / `check-tasks`（33 册，① 0 漏收尾）/ `check-knowledge-refs`（0 悬空）/ `check-component-changelog`（5 文件×4 断言）/ `check_issues`（49 open/16 closed）/ `make check`(L1) **rc=0**。
**新发现/坑**：① **窄返回 canonical 化缺口（既存，非本册引入）**：`unsigned addu(unsigned,unsigned)` 在 `-O2` 下直接 `add.uo {rd0,rd8},rd17,rd16` 返回、无 32 位 mask，`rd8[63:32]` 可为溢出高位 ⇒ 与 `contract-abi.md §4.4` C5「callee 扩展为 canonical 64 位」不符；bswap 只是暴露面之一（`x<<24`、`AND/SHR` 链同样把位留在 32–55），**建议另册/ISS**。② 路径 A 的 `anyext` 后果实测：`bswap32` 返回 `rd8` 高位含 `x<<24` 溢出位（如 `0x01020304` ⇒ full `0x0001020304030201`）⇒ oracle **只断言低 32 位**（册内已定，禁 8 字节口径）。③ 注入还原踩坑：`cp -p` 保留**旧 mtime**，ninja 认为注入产物 up-to-date ⇒ 首轮 `--inject no-action` 出现「还原后仍红」**假红**；修法 = 还原后 `touch` 源文件强制重建（已固化进 `run.sh` 注释与断言）。④ 整对象 md5 会随组件 base+1 commit hash（`.comment` ident）变化 ⇒ 回归断言必须剥离 `.comment` 后比较。⑤ `150 patches` 是 5 组件合计；llvm-project `series` 仍 **76**（本册只改既有补丁）。
**遗留问题**：① 按主会话指令**未跑** `install-host` / L2 / L3（`ISS-210` 的安装根新鲜性归落地面任务；四档验收用构建树 clang，与 `install-host` 同源二进制）；② `libc.so` 整体可链、`build-musl-shared` 全量仍受其它登记项限制（本册不判）；③ 任务 `**状态**` 按主会话指令**未改**（保持「待开始」），由协调者推进。

### 台账迁入（2026-10-18，`INFRA-091t`；原只在 `milestones.md` 流水行）

- `ISS-243`：i32 窄返回值未按 `contract-abi §4.4 C5` 做 callee canonical 化（现场：`unsigned addu()` 以 `add.uo {rd0,rd8}` 直接 `ret`）⇒ 独立于本册 `bswap` 的遗留。

## 审阅记录

#### 第 1 轮 engineer 自审
**审查范围**：`DADAOISelLowering.cpp` 新增 3 行 action + 9 行注释（对应 `expandBSWAP` 机制的注释与源码逐条核对 `LegalizeIntegerTypes.cpp:665-691`、`TargetLowering.cpp::expandBSWAP`）；`run.sh`（28 项断言逐条可达 FAIL 性）；`bswap_model.py`（解析/语义/注入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 模型初版断言 `rd8[63:32]==0`，与 `anyext` 语义冲突（会假红） | ✅已修 | 删该断言，改为注释说明「只断言低 32 位」；注入 `expect8byte` 提供可达 FAIL | `run.sh` oracle 7/7；`--inject expect8byte` 0/7 FAIL |
| F2 初版 `--inject no-action` 首轮「还原后仍红」：`cp -p` 旧 mtime ⇒ ninja 跳过重编译 | ✅已修 | 还原后 `touch "$SRCFILE"` 强制重建（含注释） | 重跑 `--inject no-action` **9/9 PASS**（injected 四档 4 FAIL + `Cannot select`×4；restored 五档 rc=0） |
| F3 `LLVM-096t` 三例整对象 md5 与基线不等（疑回归） | ✅已定位并改断言 | 实为 `.comment` 内嵌组件 commit hash（本册 amend 改变 HEAD）；`run.sh` 改为「剥离 `.comment` 后逐字节比较」+ 基线对象 provenance 校验 | strlen/memcpy/atoi 剥离后 md5 全等；`.comment` hexdump 现场对比 |
| F4 窄返回 canonical 化（C5）缺口（`addu`/`bswap32` 高位脏） | ❌不修（超出册范围） | 无（最小改动；属既存类型提升行为，非 bswap 特有） | `-O2 -S` 现场：`add.uo {rd0,rd8}` 无 mask；`bswap32` full=`0x0001020304030201`；已写完成区「新发现 ①」 |
| F5 `check-patch-tree` 计数与册内预期「150 → 变化」不符 | ❌不修（口径） | 无 | 实跑 `150 patches OK`（5 组件合计）；llvm-project `series` 现场 `wc -l`=76，未增文件 |
| F6 `run.sh` 是否吞退出码（`tee`/管道） | ✅已核 | 无 `tee`；`make`/`ninja`/`clang` 均直接重定向后取 `$?`；`check-patch-tree` 计数用 `grep -oE` 现场提取 | `grep -n "tee"` 仅注释命中；28/28 PASS 与各 gate log 自身 rc 一致 |
**判决**：F1/F2/F3/F6 已修并复验；F4/F5 为范围外/口径说明（不动代码）。无未修且在范围内的 finding ⇒ 实现完成，交 reviewer。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
