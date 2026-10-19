# LLVM-099t: `i64 = rotl`/`rotr` 的 ISel 展开（解 `P2` 阶段 A1 的 `C` 刷表后残留 2 源）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-097t`（`i64 = bswap` 已 `Expand`；本册 = 同一 `setOperationAction` 块的**紧邻缺口**）、`INFRA-085t`（**登记源 + 消费方**：阶段 A1 的 `C` 类清单「刷表后仍剩 2 源」）、`ISS-222`（③ 条）/`SPEC-141t`（`rotl`/`rotr` 预研：ISA **无** 旋转指令，属「组合 ≥3 条」候选）；纪律 = `ISS-229`（禁并发）、`ISS-210`（改 `components/**` ⇒ 单跑 `install-host`）、`docs/Process-01`（组件补丁树）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（**先读**）

- 来源 = `INFRA-085t` 完成区「阶段 A(C1 本体) + C + E」的 `C` 类结论：`arch/dadao/arch.mak` 排除表 **13→2** 后，11 源已可编，**仅剩 2 源** `Cannot select: … = rotl`（`src/crypt/crypt_sha512.c`、`src/signal/sigdelset.c`）⇒ 这两个成员（`__crypt_sha512`、`sigdelset`）仍不进 `libc.so`；`ISS-222 ③` 的 `bswap` 半边已由 `LLVM-097t` 收口，`rotl`/`rotr` 半边**未做**。
- **现场签名（本笔独立复现，2026-10-17，安装根 `.dadao/cross-toolchain/bin`）**：

```
$ TC=.dadao/cross-toolchain/bin; M=.work/source/musl
$ INC="-I$M/arch/dadao -I$M/arch/generic -I$M/obj/src/internal -I$M/src/include \
       -I$M/src/internal -I$M/obj/include -I$M/include"
$ $TC/clang --target=dadao-unknown-elf -ffreestanding -nostdinc $INC \
    -fno-stack-protector -fPIC -fno-unwind-tables -fno-asynchronous-unwind-tables \
    -ffunction-sections -fdata-sections -w -O2 -c -o /tmp/opencode/LLVM-099t/x.lo <src>
```

| 源 | rc | 首行（逐字） | 函数 |
| --- | --- | --- | --- |
| `src/crypt/crypt_sha512.c` | **1** | `fatal error: error in backend: Cannot select: t14: i64 = rotl t12, Constant:i64<45>` | `processblock` |
| `src/signal/sigdelset.c` | **1** | `fatal error: error in backend: Cannot select: t21: i64 = rotl Constant:i64<-2>, t2` | `sigdelset` |

- **DAG 形态**：`t12: i64,ch = load<(load (s64) from …)>`（crypt）/ `t2: i64,ch = CopyFromReg … %0`（sigdelset）⇒ 两条都不是常量折叠残渣，而是**真实运行期旋转**。`crypt_sha512.c:25` 的 `static uint64_t ror(uint64_t n,int k){return (n>>k)|(n<<(64-k));}` 被 DAG 组合成 `ROTL`（`rotr(k)` 规范化为 `rotl(64-k)`）；`sigdelset.c:12` 的掩码式旋转同样归到 `ROTL`。
- **根因（本笔读源码，`file:line` = LLVM 23.1.3 检出）**：DADAO `DADAOISelLowering.cpp` 只注册 `MVT::i64` 的寄存器类，**未给 `ISD::ROTL`/`ROTR` 设 action ⇒ 默认 `Legal`** ⇒ node 原样落到 ISel，而目标**无** `ROTL`/`ROTR` pattern（`DADAOInstrInfo.td` 无 `rev`-类旋转；`grep` 现场 0 命中）⇒ `Cannot select`。同一函数内 `setOperationAction(ISD::BSWAP, MVT::i64, Expand)`（`LLVM-097t` 落点）就在邻近，本册是**同一机制的未做半边**。
- **参照实现（现场读源码）**：AArch64 `setOperationAction(ISD::ROTL/ROTR, MVT::i32|i64, Expand)`（`AArch64ISelLowering.cpp:716-720`；有 `extr` 也仍对 i64 标 `Expand`）；RISCV **无 Zbb** 时 `setOperationAction({ISD::ROTL, ISD::ROTR}, XLenVT, Expand)`（`RISCVISelLowering.cpp:441-443`；有 Zbb 才 `Legal`/`Custom`）。展开体 = `TargetLowering::expandROT`（`TargetLowering.cpp:8777`），由 `LegalizeDAG.cpp:4205` 在 `Expand` 时调用 ⇒ 落成 `shl`/`srl`/`or` 组合，全部已在后端可选。
- **ISA 侧（本册不扩）**：`SPEC-141t` 把 `rotl`/`rotr`（含 `fshl`/`fshr` 漏斗移位）列为**最强候选**，但现状 = 「**组合 ≥3 条** ✗」⇒ ISA **无**旋转指令；本册只修「**能不能选中**」，**不做 ISA 扩展**、**不改** `spec/`/`contracts/`。

## 目标

让 `i64 = rotl`/`rotr`（含由 `(x>>k)|(x<<(64-k))` 组合出的形态）**有合法 lowering** ⇒ 上述 2 源 `-O2`（含 `-fPIC`）**rc=0**、`Cannot select` **0 处**，从而解 `INFRA-085t` 阶段 A1 的 `C` 类尾项（`libc.so` 的 LOBJS 不再缺这 2 个成员）。

**默认路线 = `Expand`**（与 AArch64/RISCV-无-Zbb 同款；语义由 `expandROT` 通用展开保证）。**可选 = Custom → 组合 `shl/srl/or` 手写**，仅在 `Expand` 语义有误时考虑；选它须在完成区写明理由并走同一 oracle。

## 接口规范

- **输入**：本册「立项来源」的现场签名与根因；`contract-isa.md`（**无**旋转指令的现状）；只读：`.work/source/llvm-project/**`（源码检出）、`.work/source/musl/**`（消费侧复现源）。
- **输出**：
  1. **组件补丁**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（**一文件一补丁**、`docs/Process-01`；`check-patch-tree` 机械校验）+ `components/llvm-project/changelog.md`（`Process-01 §10` 体例）；**预期不改 `series` 计数**（只改既有补丁）。
  2. **证据**：`.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项打印「检查名 + 期望/实际 + rc」、任一失败非零退出、含 `--inject` 可达 FAIL）+ 原始输出落 `.work/log/llvm/<任务ID>/`。
  3. 本册完成区（≤30 行）+ `.tao/knowledge/milestones.md` 流水行（收尾归 `/complete`）。
- **约束**：**最小改动**；**不得**改 `spec/`、`contracts/`、`.tao/contracts/**`；**不得**新增 ISA 指令 / 改重定位类型（`ADR-0019 D10` 冻结）；**不得**改 musl 源（锁条目 `patchless` 保持；本缺口是**生产者侧**）；组件源一律 **git 基线**（只经 `patches/**` 交付）；期望值**独立**、**不从 LLVM/本仓工具反推**。

## 做

### ① 复现（现状 2 源 rc=1）

用「立项来源」表中的命令编译两源，断言首行分别含 `Cannot select: … i64 = rotl`（rc=1）。**对照**：同命令编译 `-O0`（或不含旋转的源，如 `src/string/strlen.c`）⇒ rc=0，证明断言非恒真。

### ② 修法（默认 `Expand`，两行 action）

在 `DADAOISelLowering::DADAOISelLowering` 的既有 `BSWAP → Expand` 语句**紧邻处**加：

```cpp
  // `rotl`/`rotr` (ISS-222 ③ 的未做半边; SPEC-141t 预研结论 = ISA 无旋转
  // 指令).  Without an explicit action they default to `Legal`, so the DAG
  // reaches ISel as `i64 = rotl` and aborts with "Cannot select".  Expanding
  // is what AArch64 (AArch64ISelLowering.cpp:716-720) and RISCV-without-Zbb
  // (RISCVISelLowering.cpp:441-443) do; TargetLowering::expandROT lowers it
  // to shl/srl/or, all of which this backend selects.
  setOperationAction({ISD::ROTL, ISD::ROTR}, MVT::i64, Expand);
```

- **导出**：只改 `.work/source/llvm-project` 的**工作树**、`git diff` 导出为补丁（`docs/Process-01 §6.3/§6.4` 收敛 base+1 单 commit）；**重 build + `install-host` 由本任务单跑一次**（申报预计 **≈10 min**：`ninja -C .work/build/llvm -j8 clang lld` ≈4 min〔`LLVM-097t` 实测 3m59s〕+ `install-host` ≈5 min〔`LLVM-091t` 实测〕；`JOBS=8`、**禁**全核、**禁**与任何 L2/L3 并发 —— `ISS-229`；改后端 ⇒ 安装根必须新鲜 —— `ISS-210`）。
- **若 `Expand` 后暴露 `fshl`/`fshr`**（同族漏斗移位，`SPEC-141t` 已登记为候选但**非**本册目标）：**停下报告**、在完成区登记现场签名，**不擅自扩范围**（与 `LLVM-097t`「现场发现新触发面 ⇒ 登记后转出」同口径）。

### ③ 验收

1. **2 源 rc=0**：两源在 `-O2` **与** `-O2 -fPIC` 两档均 rc=0，日志 **0** 处 `Cannot select`；`-O0` 保持 rc=0。
2. **真实构建档**：`make build-musl-shared JOBS=8` 的这两个目标可编（`obj/src/crypt/crypt_sha512.{o,lo}`、`obj/src/signal/sigdelset.{o,lo}` rc=0）；**不要求** `libc.so` 整体可链（仍有 B/D 以外登记项，归 `INFRA-085t`）。
3. **独立 oracle（位序敏感，必做）**：
   - 语义 = 64 位循环左移 = `((v << k) | (v >> (64-k))) & 0xFFFF_FFFF_FFFF_FFFF`（`k=0` ⇒ `v`）、循环右移 = 同式反向。**期望值在 `run.sh` 内以手写十六进制常量表固定**（**不**现算、**不**调用 LLVM/本仓工具、**不**复用被测展开式）。
   - **取值必须端序敏感**（大端）：`0x0102030405060708`、`0x00000000000000FF`、`0xFF00000000000000`、`0x00FF00FF00FF00FF`、`0x8000000000000001`、`0xFFFFFFFFFFFFFFFF`、`0xA5A5A5A5A5A5A5A5`；**断言对象 `ELFDATA2MSB`**，`.dd.o64` 立即数按大端解释。
   - **旋转量边界**：`0`、`1`、`31`、`32`、`63` **逐值断言**（正确性）；**`64` 不作值断言** —— C 层 `(x<<64)|(x>>0)` 是 **UB**、IR `fshl` 移位量 `≥` 位宽为 **poison**，故 `64` 只作为「不得崩溃、不得残留 `rotl` 节点」的稳健性项，完成区须写明该口径（**禁**伪造一个期望值去比对）。
   - 实现方式：对**同一探针源**（`uint64_t rotl64(uint64_t x, unsigned k)` + 常量/运行期两版）编译出对象，用 `llvm-objdump -d` 取该函数中 `shl/srl/or/and` 链，按**自写指令级模型**逐条求值；断言链长 > 0（防空转绿）+ 结构断言「`rotl` 已展开为移位组合」。
4. **不回归**：① `install-host` 后 `make check`（L1）rc=0；② `LLVM-097t` 的三例探针（`strlen`/`memcpy`/`atoi`，`-O2 -fPIC`）剥离 `.comment` 后与 `LLVM-097t` 基线**逐字节相同**；③ `check-patch-tree`（**仍 152**，本册只改既有补丁）、`check-instrinfo`、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身**真实 rc；禁 `cmd | tee` 吞码）。
5. **可达 FAIL**：`--inject` 至少 2 条 —— (i) 把两行 action 注释掉（或改 `Legal`）⇒ 断言「2 源 rc=0」**FAIL**（`Cannot select: … = rotl` 复现）⇒ `cp` 备份 + md5 对账还原（`cp -p` 后 `touch` 源文件，`LLVM-097t` 坑③）⇒ 回绿；(ii) 把指令级模型的移位量/期望值改错一处 ⇒ oracle **FAIL** ⇒ 还原 ⇒ 回绿。**禁恒真断言**；**禁** `git checkout`/`restore`/`stash` 还原（`cp` + md5 或临时树）。

## 不做项（显式）

1. **ISA 扩展 / 新增旋转指令** ✗（`SPEC-141t` 候选未立项；本册只修选中）。
2. **`fshl`/`fshr` 漏斗移位的完整支持** ✗（同族但独立；触发即登记转出）。
3. **`INFRA-079t` 其余接入点（i128/原子/f16/compiler-rt）** ✗。
4. **`libc.so` 整体可链 / `build-musl-shared` rc=0** ✗（归 `INFRA-085t`；本册只解 2 源）。
5. **运行验证 / `qemu-user` / 三套测试集**（`P3`/`P4`）✗ —— 判据 = **能编 + 静态可核**，完成区**不得**出现「运行通过」叙述。
6. **改 `spec/`、`contracts/`、`.tao/contracts/**`、musl 源/锁条目** ✗。
7. **`L2`/`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 验收标准

1. 「做 ①」2 源 `-O2`/`-O2 -fPIC` 四档全 rc=0、`Cannot select` 0 处。
2. 独立 oracle（位序敏感、大端、边界 `0/1/31/32/63` 逐值；`64` 按 UB 口径）全绿；**可达 FAIL** 每条断言可证。
3. 构建纪律：改 `components/**` ⇒ **单跑一次** `install-host`（申报 ≈10 min、`JOBS=8`、不并发、`ISS-210`）；组件源 base+1 单 commit、`check-source-state` rc=0。
4. 不回归（「做 ③ 4」逐条）；门控各留自身 rc=0。
5. 完成区与真实输出逐条对齐（≤30 行）；`milestones.md` 流水行更新（收尾归 `/complete`）。

## 完成区

**测试结果**：`.work/evidence/LLVM-099t/run.sh` **50/50 PASS / 0 FAIL**（默认档）；`--inject no-action` **13/13**（注掉 action ⇒ 复现矩阵 6/6 rc=1 ⇒ `cp`+md5+`touch` 还原 ⇒ 回绿，同一次前台执行内闭合）；模型注入 3 条（默认档内）`shiftbias` **12/147**、`wpflip` **53/147**、`swapdir` **75/147**（均 RED ⇒ 清洁模型回绿）。
**修改文件**：（组件检出，E1 base+1 `bda2544d4e98`）`llvm/lib/Target/DADAO/DADAOISelLowering.cpp`（+13 行：11 行注释 + 1 行 action + 空行）；`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（重导出，hunk `+1,1288`→`+1,1301`，唯一 hunk）；`components/llvm-project/changelog.md`（+1 条）；证据 `.work/evidence/LLVM-099t/{run.sh,rot_model.py,rotl_probe.c}`。`series` 未改（仍 **76**）。
**验收结果**：`ninja -C .work/build/llvm -j8 clang lld` **rc=0**（3m20s，5 步：1 TU + 静态库 + lld + clang-23 + symlink）。2 源复现矩阵（构建树 clang）：`crypt_sha512`/`sigdelset` × **-O0 / -O2 / -O2 -fPIC** 全 **rc=0、`Cannot select` 0 处**（修前同 6 例全 rc=1：`rotl Constant:i64<45>`/`rotr (runtime)`/`rotl Constant:i64<-2>`）；对照 `strlen.c -O2 -fPIC` rc=0（非恒真）。真实 musl 配方 `make obj/src/{crypt/crypt_sha512,signal/sigdelset}.{o,lo}` **rc=0**、4 目标非空、`-O2` 配方计数 **4**。oracle：对象 `ELFCLASS64/ELFDATA2MSB` 断言 + 指令级模型，**-O2/-O1/-O0 各 147/147**（`rotl64`/`rotr64`/`idiom_rotl64`/`musl_ror` × 7 值 × k∈{0,1,31,32,63} + `rotl64_c45` × 7）；`k=64` 仅稳健性（`__builtin_rotateleft64(x,64)` 折叠为 `rd2rd` 拷贝、rc=0、无残留 rotl），**不作值断言**。不回归：strlen/memcpy/atoi `-O2 -fPIC` 剥 `.comment` 后与 `LLVM-097t` 基线**逐字节相同**。门控各留自身 rc=0：`check-instrinfo`（0 errors）/`check_lit_gen`（64 passed, 0 failed）/`check-patch-tree`（**152 patches OK**，5 组件现场统计）/`check-index-blobs`/`check-source-state`（`HEAD=bda2544d4e98 count=1 clean=True`）/`check-no-residue`/`check-tasks`（① 漏收尾 0）/`check-knowledge-refs`/`check-component-changelog`（5 文件×4 断言）/`check_issues`（50 open/18 closed）/`make check`(L1) rc=0；证据脚本 rc=0（内部 `; rc=$?`，无 `tee`）。
**新发现/坑**：① 册内「`-O0` 保持 rc=0」与实测不符——修前两源 `-O0` **也** rc=1（crypt 为运行期 `rotr`、sigdelset 为 `rotl`）⇒ 非恒真对照改用 `strlen.c`，`-O0` 反向并入修复后矩阵（如实记录，不改任务书口径）。② 全程未见 `.dd.o64`（后端无常量池，i64 常量经 `set.zw` 逐 wyde 材质化）⇒ 端序断言落在 **ELF `EI_DATA=2`** + **`wpN` 位置解码（`wp0`=bits[15:0]）**，并以 `--inject wpflip` 证明该解码可达 FAIL（不伪造 `.dd.o64` 路径）。③ `-O0` 探针把参数溢出到栈（`st.o`/`st.t`/`ld.o`/`ld.ut`）⇒ 模型必须建小栈模型；已加「读未初始化寄存器 / 读未写槽位 ⇒ 硬报错」，防静默取 0 假绿。④ 期望值表为 `rot_model.py` 内**冻结字面量**（非 run.sh 内，非现算）：一次性由**位置换定义**生成（输入位 i → 输出位 (i±k)%64），**不**采用被测 `(x<<k)|(x>>(64-k))` 展开式、不调用 LLVM/本仓工具。
**遗留问题**：① 按主会话指令**未跑** `install-host` / `build-musl-shared` 全量 / L2 / L3 —— 2 源验收用**构建树 clang**（与本任务增量编译同源二进制；`ISS-210` 安装根新鲜性归落地面任务）；② `libc.so` 整体可链与 `build-musl-shared` 其余登记项（B 类）仍归 `INFRA-085t`；③ 任务 `**状态**` 按指令**未改**，由协调者推进；④ 未 commit/push（提交权归 architect）。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审阅 `DADAOISelLowering.cpp` 新增 13 行、`rot_model.py`、`run.sh` 与 changelog 摘要，逐条与真实输出对齐：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `setOperationAction({…}, MVT, …)` 重载合法、`ISD::ROTL/ROTR` 可达 | ✅已核 | 无 | 同文件 L250 既有同形用法；`ninja clang lld` rc=0 |
| F2 注释坐标真伪（AArch64/RISCV/contract-isa §6.4） | ✅已核 | 无 | AArch64:716 ROTL-i32 / 717 i64；RISCV:441 ROTL-Expand、443 ROTL\|ROTR-Expand；`grep rotl\|rotr contract-isa.md` ⇒ 0 命中（§6.4 位操作只含移位/ext/rev/ctlz/cttz/ctpop） |
| F3 模型读未初始化寄存器/未写槽位静默取 0 ⇒ 建模缺口假绿 | ✅已修 | `rd()` 对非 `rd0` 未写寄存器抛错；`ld.o`/`ld.ut` 读未写槽位抛错；`rb1`/`rb63` 仅作基址预置 0 | 改后 `-O2/-O1/-O0` 仍各 147/147 |
| F4 期望值列数错位会静默错判 | ✅已修 | 断言 `len(row) == len(SHIFTS)` | 三档 147/147；`swapdir` 仍 RED（72 失败） |
| F5 注入是否真空（未真改到源） | ✅已核 | 无 | `live-actions=0` + `git diff --name-only` 非空 |
| F6 还原是否真回原状（禁 git restore） | ✅已核 | 无 | `cp -p`+`touch` 后 md5 `634f4ae79c8f2c91080cd0ef3a0f550a` 前后相等、`git status` 空、再构建后回绿 |
| F7 `-O2` 与 `-O2 -fPIC` 若都无条件带 `-fPIC` ⇒ 同一条用例（假覆盖） | ✅已修 | `run_repro` 去掉基线 `-fPIC`，按档传入 | 矩阵逐档打印 7 例 rc=0 |
| F8 完成区是否出现「运行通过」越界叙述 | ✅已核 | 无 | 仅「能编 + 静态可核」；`k=64` 明示不作值断言 |

判决：finding 全部已修或已核，无未修项 ⇒ 自审通过，返回主会话待独立验收。

#### 第 1 轮 reviewer 验收

**重跑**：`.work/evidence/LLVM-099t/run.sh` default **49 PASS / 1 FAIL**。
- 预检：组件工作树 clean + base+1 + `DADAOISelLowering.cpp:420` 有且仅有 1 条 `setOperationAction({ISD::ROTL, ISD::ROTR}, MVT::i64, Expand);` ✓。
- 复现矩阵：`crypt_sha512`/`sigdelset` × {-O0, -O2, -O2 -fPIC} + 控制 `strlen` 全 **rc=0、Cannot select=0** ✓。
- musl 配方：`obj/src/{crypt/crypt_sha512,signal/sigdelset}.{o,lo}` rc=0、4 目标非空 ✓。
- oracle（`rot_model.py`）：-O2/-O1/-O0 各 **147/147**（`rotl64`/`rotr64`/`idiom_rotl64`/`musl_ror` × 7 值 × k∈{0,1,31,32,63} + `rotl64_c45` × 7）；`k=64` 仅稳健性、不作值断言 ✓。
- 097t 回归：strlen/memcpy/atoi `-O2 -fPIC` 剥 `.comment` 后与 LLVM-097t 基线**逐字节相同** ✓。
- 注入：`shiftbias`(12/147)、`wpflip`(53/147)、`swapdir`(75/147) 均 RED → 还原 → GREEN ✓。
- 门控全绿：`check-patch-tree`(180)、`check-index-blobs`、`check-source-state`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`check_issues`(68 open/27 closed) 全 rc=0 ✓。
- **L1 FAIL**：`check-musl-freshness` 报 installed libc.so sha256 ≠ build-tree libc.so（`LLVM-106t` 重建 builtins 后安装根与构建树短暂不一致）。**非本册缺陷**。
**独立注入**：`rot_model.py` 期望表 `0x0102030405060708→0xDEADBEEFCAFEBABE`（k=0 首列）→ 4 FAIL（rotl64/rotr64/idiom_rotl64/musl_ror）= RED；还原 md5 `af3d74ae…` → 147/147 = GREEN。**证明 oracle 非恒真**。
**约束核验**：① 改动 = `DADAOISelLowering.cpp` +13 行（11 注释 + 1 action + 空行）✓；② `check-source-state` `HEAD=bda2544d count=1 clean=True` ✓；③ `check-patch-tree` 180（增量，仅改既有补丁）✓；④ 不回归（097t 三探针逐字节）✓；⑤ 大端敏感（ELF `EI_DATA=2` + wp 位置解码 + `--inject wpflip` 可达 FAIL）✓。
**判决**：**Accepted**。L1 唯一 FAIL 为 `check-musl-freshness`（已知环境原因），非产品缺陷。ROTL/ROTR Expand 实现正确、oracle 147/147 全档全绿、注入 3/3 可达 FAIL。

#### 第 1 轮 architect 提交留痕（2026-10-17）

- **档位**：按主会话指令**正常提交**（非 `WIP:`）；⚠ **如实披露** = 本册第 1 轮 reviewer 块**为空**（无 `Accepted` 判决落盘），任务级 `**状态**` **未改**（保持 `待开始`，验收由主会话推进）。
- **提交**：`df6add4`（分支 `LLVM-099t`；提交信息 = `LLVM-099t：{ROTL,ROTR} i64 改 Expand … check-patch-tree 152；L1 rc=0`）。
- **文件集对账**（`git diff --cached --name-only`，3/3 与本册完成区「修改文件」一致，无漏提 / 多提 / 越界）：① 本册（完成区 + 自审）；② `components/llvm-project/changelog.md`（+1 条）；③ `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（重导出，唯一 hunk `+1,1288`→`+1,1301`）。
- **完成区如实性核对（不改内容）**：证据脚本 `50/50 PASS`、`check-patch-tree` **152**、`gate.L1.log` 尾行 `repository checks (L1): PASS`、组件检出 `HEAD=bda2544d4e98 count=1 clean=True`、组件工作树 `git diff` 为空（改动已入组件基线 `bda2544d4`）——逐条对上。
- **门控（本笔实跑，各留自身 rc）**：`check-patch-tree` **rc=0**（**152**）/ `check-index-blobs` rc=0 / `check-source-state` rc=0 / `check-no-residue` rc=0 / `check-tasks` rc=0 / `check-knowledge-refs` rc=0 / `check-component-changelog` rc=0 / `python3 tools/infra/check_issues.py` rc=0（**49 open / 19 closed**）/ `make check`(L1) **rc=0**；日志 `.work/log/llvm/ISS-241/gate.*.log`。**未跑** `install-host` / `build-*` / L2 / L3（`ISS-229` 并发禁令；`ISS-210` 新鲜性归落地面任务）。
